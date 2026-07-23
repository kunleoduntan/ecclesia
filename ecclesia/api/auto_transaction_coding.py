"""
Auto Transaction Coding — Enterprise Multi-Company Edition
==========================================================
App    : ecclesia
Module : Ecclesia
File   : ecclesia/ecclesia/auto_transaction_coding.py

DESIGN PRINCIPLES
-----------------
1. **Company-neutral rules** — rules store an account *name* and *number*,
   never a full ERPNext account ID (which embeds the company abbreviation).
   At runtime the engine resolves the correct account for whatever company
   the Payment belongs to.

2. **Rule precedence (two-tier)**
   - Company-specific rules are evaluated BEFORE global rules for the same
     payment, regardless of their priority number.  Within each tier, rules
     are evaluated in ascending priority order.
   - This lets you maintain one global rule set and override individual
     accounts per company without duplicating every rule.

3. **Account resolution waterfall** (per company, per rule):
   a. Name match  — account_name = rule.account_name_pattern, filtered to
                    the correct company (and root type if set).
   b. Number match — account_number = rule.account_number, filtered to
                    the correct company.
   c. Fallback name — rule.fallback_account_name, same company filter.
   d. None found  — log "Resolution Failed", skip to next rule.

4. **Account resolution cache** — resolved (rule, company) → account_id
   pairs are cached in-process for the duration of a scheduled run.
   This prevents N×R database hits for N payments against R rules.

5. **Safe for concurrent runs** — each Payment write uses update_modified=False
   and operates on individual documents; no batch SQL updates that could
   cause lost-update races.

hooks.py wiring
---------------
    scheduler_events = {
        "hourly": [
            "ecclesia.api.auto_transaction_coding.run_auto_transaction_coding"
        ],
    }
"""

import re
import frappe
from frappe import _
from frappe.utils import now_datetime


# ============================================================
# Public scheduled entry-point
# ============================================================

def run_auto_transaction_coding():
    """
    Scheduled entry-point (hourly).
    Processes all uncoded or pending-recode Payments across all companies.
    """
    rules = _load_active_rules()
    if not rules:
        frappe.logger().info("[AutoCoding] No active rules — skipping run.")
        return

    # Pre-split rules into company-specific and global for the resolution engine
    company_rules, global_rules = _partition_rules(rules)

    payments = _fetch_uncoded_payments()
    if not payments:
        frappe.logger().info("[AutoCoding] No payments require coding.")
        return

    # Account resolution cache:  (rule_name, company) -> {"account": ..., "method": ...} | None
    resolution_cache: dict = {}

    coded, unmatched, res_failed, errors = 0, 0, 0, 0

    for payment in payments:
        try:
            outcome = _process_payment(
                payment, company_rules, global_rules, resolution_cache
            )
            if outcome == "matched":
                coded += 1
            elif outcome == "resolution_failed":
                res_failed += 1
            else:
                unmatched += 1
        except Exception:
            errors += 1
            frappe.log_error(
                frappe.get_traceback(),
                f"[AutoCoding] Error processing Payment {payment['name']}"
            )

    summary = (
        f"[AutoCoding] Run complete — "
        f"Coded: {coded} | Unmatched: {unmatched} | "
        f"Resolution Failed: {res_failed} | Errors: {errors}"
    )
    frappe.logger().info(summary)
    _write_run_log(coded, unmatched, res_failed, errors, len(payments))


# ============================================================
# Public on-demand helpers (called by client script / API)
# ============================================================

@frappe.whitelist()
def code_payment_api(payment_name: str) -> dict:
    """
    Code a single Payment immediately (on-demand button).
    Returns: {"status", "account", "rule", "resolution_method"}
    """
    frappe.only_for(["Accounts User", "Accounts Manager", "System Manager"])
    return _code_payment_now(payment_name)


@frappe.whitelist()
def preview_match(description: str, company: str) -> dict:
    """
    Dry-run: given a description and company, return what would be coded
    without touching any document.
    Returns: {"status", "account", "rule", "resolution_method", "rule_scope"}
    """
    frappe.only_for(["Accounts User", "Accounts Manager", "System Manager"])

    if not company:
        frappe.throw(_("Company is required for preview."))

    rules = _load_active_rules()
    company_rules, global_rules = _partition_rules(rules)
    cache: dict = {}

    result = _match_and_resolve(description, company, company_rules, global_rules, cache)
    if result:
        return {
            "status"           : "matched",
            "account"          : result["account"],
            "rule"             : result["rule"],
            "resolution_method": result["resolution_method"],
            "rule_scope"       : result["rule_scope"],
        }
    return {"status": "unmatched", "account": None, "rule": None,
            "resolution_method": None, "rule_scope": None}


# ============================================================
# Internal orchestration
# ============================================================

def _code_payment_now(payment_name: str) -> dict:
    """Resolve and persist coding for a single named Payment."""
    doc = frappe.get_value(
        "Payments", payment_name,
        ["name", "transaction_description", "company"],
        as_dict=True
    )
    if not doc:
        frappe.throw(_("Payment {0} not found.").format(payment_name))

    rules = _load_active_rules()
    company_rules, global_rules = _partition_rules(rules)
    cache: dict = {}

    result = _match_and_resolve(
        doc.transaction_description or "",
        doc.company or "",
        company_rules, global_rules, cache
    )
    return _persist_result(doc.name, doc.company, doc.transaction_description, result)


def _process_payment(payment: dict, company_rules, global_rules, cache) -> str:
    """Process one payment dict (name, company, transaction_description)."""
    result = _match_and_resolve(
        payment.get("transaction_description") or "",
        payment.get("company") or "",
        company_rules, global_rules, cache
    )
    outcome = _persist_result(
        payment["name"], payment["company"],
        payment["transaction_description"], result
    )
    return outcome["status_key"]


def _persist_result(payment_name, company, description, result) -> dict:
    """Write matched account (or unmatched status) back to the Payment."""
    if result and result.get("account"):
        frappe.db.set_value(
            "Payments", payment_name,
            {
                "account_to_debit"          : result["account"],
                "auto_coding_rule"          : result["rule"],
                "auto_coding_status"        : "Matched",
                "auto_coding_date"          : now_datetime(),
                "auto_coding_resolution_method": result["resolution_method"],
            },
            update_modified=False,
        )
        frappe.db.commit()
        _write_coding_log(
            payment=payment_name, company=company, description=description,
            rule=result["rule"], account=result["account"],
            rule_scope=result["rule_scope"],
            resolution_method=result["resolution_method"],
            status="Matched",
        )
        return {"status": "Matched", "status_key": "matched",
                "account": result["account"], "rule": result["rule"],
                "resolution_method": result["resolution_method"]}

    elif result and result.get("resolution_failed"):
        # Rule matched the description but account couldn't be resolved for this company
        frappe.db.set_value(
            "Payments", payment_name,
            {"auto_coding_status": "Resolution Failed", "auto_coding_date": now_datetime()},
            update_modified=False,
        )
        frappe.db.commit()
        _write_coding_log(
            payment=payment_name, company=company, description=description,
            rule=result["rule"], account=None,
            rule_scope=result.get("rule_scope"),
            resolution_method="Not Resolved",
            status="Resolution Failed",
            notes=result.get("notes"),
        )
        return {"status": "Resolution Failed", "status_key": "resolution_failed",
                "account": None, "rule": result["rule"]}

    else:
        # No rule matched at all
        frappe.db.set_value(
            "Payments", payment_name,
            {"auto_coding_status": "Unmatched", "auto_coding_date": now_datetime()},
            update_modified=False,
        )
        frappe.db.commit()
        _write_coding_log(
            payment=payment_name, company=company, description=description,
            rule=None, account=None, rule_scope=None,
            resolution_method=None, status="Unmatched",
        )
        return {"status": "Unmatched", "status_key": "unmatched", "account": None}


# ============================================================
# Matching + resolution engine
# ============================================================

def _match_and_resolve(
    description: str,
    company: str,
    company_rules: dict,   # {company_name: [rule, ...]}
    global_rules: list,
    cache: dict
) -> dict | None:
    """
    Walk rules in two tiers:
      1. Company-specific rules for this company (by priority asc)
      2. Global rules (by priority asc)

    For each matching rule, attempt account resolution.
    Returns the first fully-resolved result, or a resolution_failed sentinel
    if a rule matched but no account could be found, or None if no rule matched.
    """
    if not description or not company:
        return None

    desc_lower = description.strip().lower()

    # Build ordered rule list: company-specific first, then global
    ordered_rules = list(company_rules.get(company, [])) + list(global_rules)

    for rule in ordered_rules:
        if not _description_matches(desc_lower, rule):
            continue

        # Rule matched — try to resolve the account for this company
        resolved = _resolve_account(rule, company, cache)

        if resolved:
            return {
                "account"          : resolved["account"],
                "rule"             : rule["name"],
                "resolution_method": resolved["method"],
                "rule_scope"       : "Company-Specific" if rule.get("company") else "Global",
            }
        else:
            # Matched but unresolvable — report resolution failure so staff knows
            return {
                "resolution_failed": True,
                "rule"             : rule["name"],
                "rule_scope"       : "Company-Specific" if rule.get("company") else "Global",
                "notes": (
                    f"Rule '{rule['name']}' matched but account "
                    f"'{rule.get('account_name_pattern')}' "
                    f"(number: {rule.get('account_number') or 'N/A'}) "
                    f"could not be resolved for company '{company}'."
                ),
            }

    return None  # No rule matched


def _description_matches(desc_lower: str, rule: dict) -> bool:
    """Return True if desc_lower satisfies the rule's match_type + keywords."""
    match_type   = rule.get("match_type", "Contains (Any Keyword)")
    raw_keywords = (rule.get("keywords") or "").strip()

    if not raw_keywords:
        return False

    if match_type == "Contains (Any Keyword)":
        kws = [k.strip().lower() for k in raw_keywords.split(",") if k.strip()]
        return any(kw in desc_lower for kw in kws)

    elif match_type == "Contains All Keywords":
        kws = [k.strip().lower() for k in raw_keywords.split(",") if k.strip()]
        return all(kw in desc_lower for kw in kws)

    elif match_type == "Exact Match":
        return desc_lower == raw_keywords.lower()

    elif match_type == "Starts With":
        kws = [k.strip().lower() for k in raw_keywords.split(",") if k.strip()]
        return any(desc_lower.startswith(kw) for kw in kws)

    elif match_type == "Ends With":
        kws = [k.strip().lower() for k in raw_keywords.split(",") if k.strip()]
        return any(desc_lower.endswith(kw) for kw in kws)

    elif match_type == "Regex":
        try:
            return bool(re.search(raw_keywords, desc_lower, re.IGNORECASE))
        except re.error:
            frappe.logger().warning(
                f"[AutoCoding] Rule '{rule.get('name')}' has invalid regex: {raw_keywords}"
            )
            return False

    return False


# ============================================================
# Account resolution (company-aware, cached)
# ============================================================

def _resolve_account(rule: dict, company: str, cache: dict) -> dict | None:
    """
    Resolve a company-neutral rule to a concrete ERPNext Account ID for `company`.

    Resolution waterfall:
      a) account_name_pattern  (+ optional account_number disambiguator)
      b) account_number alone
      c) fallback_account_name (+ optional account_number disambiguator)

    Results are memoised in `cache` keyed by (rule_name, company).
    Returns {"account": "<account id>", "method": "<Name Match|Number Match|...>"}
    or None if resolution fails.
    """
    cache_key = (rule["name"], company)
    if cache_key in cache:
        return cache[cache_key]

    name_pattern  = (rule.get("account_name_pattern") or "").strip()
    number        = (rule.get("account_number") or "").strip()
    fallback_name = (rule.get("fallback_account_name") or "").strip()
    root_type     = (rule.get("account_root_type") or "").strip()

    result = None

    # ── a) Primary name + optional number ──────────────────────────────
    if name_pattern:
        result = _query_account(
            company=company,
            account_name=name_pattern,
            account_number=number or None,
            root_type=root_type or None,
        )
        if result:
            result = {"account": result, "method": "Name Match"}

    # ── b) Number alone ─────────────────────────────────────────────────
    if not result and number:
        result = _query_account(
            company=company,
            account_name=None,
            account_number=number,
            root_type=root_type or None,
        )
        if result:
            result = {"account": result, "method": "Number Match"}

    # ── c) Fallback name + optional number ──────────────────────────────
    if not result and fallback_name:
        result = _query_account(
            company=company,
            account_name=fallback_name,
            account_number=number or None,
            root_type=root_type or None,
        )
        if result:
            result = {"account": result, "method": "Fallback Name"}

    cache[cache_key] = result
    return result


def _query_account(
    company: str,
    account_name: str | None,
    account_number: str | None,
    root_type: str | None,
) -> str | None:
    """
    Query the ERPNext Account table for a concrete account ID.

    ERPNext account IDs follow the pattern:
        "{account_number} - {account_name} - {company_abbr}"
    We match by account_name (exact) and/or account_number within
    the given company.  root_type is an optional narrowing filter.

    Returns the account `name` (full ID string) or None.
    """
    filters = {"company": company, "is_group": 0}

    if account_name:
        filters["account_name"] = account_name

    if account_number:
        filters["account_number"] = account_number

    if root_type:
        filters["root_type"] = root_type

    # Must have at least one account-identifying filter
    if "account_name" not in filters and "account_number" not in filters:
        return None

    results = frappe.get_all(
        "Account",
        filters=filters,
        fields=["name"],
        limit=2,   # If >1 result we log ambiguity but still use the first
    )

    if not results:
        return None

    if len(results) > 1:
        frappe.logger().warning(
            f"[AutoCoding] Ambiguous account resolution: "
            f"name='{account_name}', number='{account_number}', "
            f"company='{company}' returned {len(results)} accounts. "
            f"Using first result: {results[0]['name']}. "
            f"Add an account_number to the rule to disambiguate."
        )

    return results[0]["name"]


# ============================================================
# Data loading helpers
# ============================================================

def _load_active_rules() -> list[dict]:
    """Load all active rules ordered by priority ascending."""
    return frappe.get_all(
        "Auto Transaction Coding Rule",
        filters={"is_active": 1},
        fields=[
            "name", "priority", "company", "match_type", "keywords",
            "account_name_pattern", "account_number", "account_root_type",
            "fallback_account_name",
        ],
        order_by="priority asc",
    )


def _partition_rules(rules: list[dict]) -> tuple[dict, list]:
    """
    Split rules into:
      company_rules : {company_name: [rules sorted by priority]}
      global_rules  : [rules with no company, sorted by priority]
    """
    company_rules: dict[str, list] = {}
    global_rules:  list            = []

    for rule in rules:
        co = (rule.get("company") or "").strip()
        if co:
            company_rules.setdefault(co, []).append(rule)
        else:
            global_rules.append(rule)

    # Each bucket is already sorted by priority from the DB query
    return company_rules, global_rules


def _fetch_uncoded_payments() -> list[dict]:
    """
    Return dicts {name, company, transaction_description} for all Payments
    that need auto-coding.
    """
    fields = ["name", "company", "transaction_description"]

    uncoded = frappe.get_all(
        "Payments",
        filters=[
            ["transaction_description", "!=", ""],
            ["transaction_description", "is", "set"],
            ["docstatus", "!=", 2],
            ["account_to_debit", "in", ["", None]],
        ],
        fields=fields,
        limit=1000,
    )

    recode = frappe.get_all(
        "Payments",
        filters=[
            ["transaction_description", "!=", ""],
            ["docstatus", "!=", 2],
            ["auto_coding_status", "=", "Pending Re-code"],
        ],
        fields=fields,
        limit=1000,
    )

    # Deduplicate by name
    seen = set()
    combined = []
    for p in uncoded + recode:
        if p["name"] not in seen:
            seen.add(p["name"])
            combined.append(p)
    return combined


# ============================================================
# Audit logging
# ============================================================

def _write_coding_log(
    payment, company, description,
    rule, account, rule_scope, resolution_method, status, notes=None
):
    try:
        frappe.get_doc({
            "doctype"                : "Auto Transaction Coding Log",
            "payment"                : payment,
            "company"                : company,
            "transaction_description": description,
            "matched_rule"           : rule,
            "account_to_debit"       : account,
            "rule_scope"             : rule_scope,
            "resolution_method"      : resolution_method,
            "status"                 : status,
            "notes"                  : notes,
            "logged_on"              : now_datetime(),
        }).insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "[AutoCoding] Failed to write coding log")


def _write_run_log(coded, unmatched, res_failed, errors, total):
    try:
        frappe.get_doc({
            "doctype"  : "Auto Transaction Coding Log",
            "status"   : "Run Summary",
            "notes"    : (
                f"Total: {total} | Coded: {coded} | Unmatched: {unmatched} | "
                f"Resolution Failed: {res_failed} | Errors: {errors}"
            ),
            "logged_on": now_datetime(),
        }).insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "[AutoCoding] Failed to write run summary log")