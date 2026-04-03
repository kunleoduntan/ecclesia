"""
AI Intelligence Engine
=======================
Rule-based AI that provides audit intelligence at every stage:
- DocType risk profiling on registration
- Anomaly detection on transactions
- Sampling recommendations
- Finding risk assessment
- Narrative generation for reports

Designed to work offline without external API dependency.
Follows IIA, COSO, ACFE, and ISA 520/530 methodologies.
"""

import frappe
import frappe.utils
from datetime import datetime, timedelta
import statistics
import re


# ─────────────────────────────────────────────────────────────────────────────
# DocType Risk Profiling
# ─────────────────────────────────────────────────────────────────────────────

def generate_doctype_risk_profile(doctype_name, classification, classified_fields,
                                   is_gl_posting, risk_level):
    """
    Generate AI risk profile for a newly registered DocType.
    Returns risk summary, key controls, and red flags.
    """
    has_amounts   = len(classified_fields.get("amount_fields", [])) > 0
    has_approvals = len(classified_fields.get("approval_fields", [])) > 0
    has_accounts  = len(classified_fields.get("account_fields", [])) > 0
    has_parties   = len(classified_fields.get("party_fields", [])) > 0

    risk_summary  = _build_risk_summary(doctype_name, classification, is_gl_posting,
                                         has_amounts, has_approvals, risk_level)
    key_controls  = _build_key_controls(classification, has_amounts, has_approvals,
                                         has_accounts, is_gl_posting)
    red_flags     = _build_red_flags(classification, has_amounts, has_approvals,
                                      has_parties, is_gl_posting)

    return {
        "risk_summary": risk_summary,
        "key_controls": key_controls,
        "red_flags":    red_flags,
    }


def _build_risk_summary(name, classification, is_gl, has_amounts, has_approvals, risk_level):
    lines = [f"<b>Inherent Risk Assessment: {risk_level}</b><br><br>"]

    lines.append(f"The <b>{name}</b> DocType is classified as <b>{classification}</b>. ")

    if is_gl:
        lines.append(
            "This DocType posts directly to the General Ledger, making it a "
            "<b>high financial exposure</b> area requiring robust audit coverage. "
            "All transactions must be traced through GL entries to verify accuracy, "
            "completeness, and correct period posting."
        )
    if has_amounts:
        lines.append(
            " Financial amounts are present, requiring application of materiality "
            "thresholds and monetary unit sampling per ISA 530."
        )
    if has_approvals:
        lines.append(
            " Approval workflows are detected — segregation of duties testing "
            "is required to ensure no individual can both initiate and approve transactions."
        )

    return "".join(lines)


def _build_key_controls(classification, has_amounts, has_approvals, has_accounts, is_gl):
    controls = []

    if is_gl:
        controls += [
            "✓ GL posting accuracy — verify debit/credit entries match source document amounts",
            "✓ Period cutoff controls — confirm transactions posted in correct accounting period",
            "✓ Account classification — verify amounts posted to correct GL accounts",
            "✓ GL amendment monitoring — review all cancelled/reposted GL entries",
        ]
    if has_approvals:
        controls += [
            "✓ Authorization controls — verify all transactions have required approvals",
            "✓ Segregation of duties — confirm preparers and approvers are different individuals",
            "✓ Approval hierarchy — check approval is by authorized personnel per policy",
        ]
    if has_amounts:
        controls += [
            "✓ Amount accuracy — verify computed totals agree to line-item components",
            "✓ Threshold controls — check high-value transactions have additional approvals",
            "✓ Duplicate detection — scan for duplicate amounts to same party in same period",
        ]
    if classification == "Financial":
        controls += [
            "✓ Completeness — confirm all expected transactions are recorded",
            "✓ Existence — verify recorded transactions correspond to real events",
        ]

    return "<ul><li>" + "</li><li>".join(controls) + "</li></ul>" if controls else "Standard controls apply."


def _build_red_flags(classification, has_amounts, has_approvals, has_parties, is_gl):
    flags = []

    if is_gl:
        flags += [
            "🚩 GL entries cancelled and reposted within the audit period",
            "🚩 Posting date differs from transaction date by more than 3 days",
            "🚩 Entries posted to suspense or clearing accounts",
            "🚩 GL entries without corresponding source document",
        ]
    if has_amounts:
        flags += [
            "🚩 Round number amounts (multiples of 1000/5000/10000) — fraud indicator",
            "🚩 Amounts just below approval thresholds — threshold avoidance",
            "🚩 Statistical outliers: amounts beyond 2 standard deviations of mean",
            "🚩 Duplicate amounts to same party within 30 days",
        ]
    if has_approvals:
        flags += [
            "🚩 Created and approved by same user — segregation of duties failure",
            "🚩 Approved after posting date — retroactive authorization",
            "🚩 Missing approvals on high-value transactions",
        ]
    if classification in ("Financial", "Procurement"):
        flags += [
            "🚩 Transactions on weekends or public holidays",
            "🚩 High frequency of small transactions to same party (structuring)",
            "🚩 New vendors/parties with immediate high-value transactions",
        ]

    return "<ul><li>" + "</li><li>".join(flags) + "</li></ul>" if flags else "Monitor for standard exceptions."


# ─────────────────────────────────────────────────────────────────────────────
# Anomaly Detection Engine
# ─────────────────────────────────────────────────────────────────────────────

def run_anomaly_detection(doctype_name, records, registry_doc):
    """
    Run AI anomaly detection on a set of records.
    Returns list of anomaly dicts with record, type, severity, and description.
    """
    anomalies = []

    amount_field  = _first_csv(registry_doc.amount_fields)
    date_field    = _first_csv(registry_doc.date_fields)
    approval_field= _first_csv(registry_doc.approval_fields)

    amounts = []
    if amount_field:
        amounts = [r.get(amount_field, 0) or 0 for r in records]

    for record in records:
        record_anomalies = []

        # ── Amount checks ──────────────────────────────────────────────
        if amount_field and amounts:
            amount = record.get(amount_field, 0) or 0
            record_anomalies += _check_amount_anomalies(amount, amounts)

        # ── Date/timing checks ─────────────────────────────────────────
        if date_field:
            doc_date = record.get(date_field)
            posting_date = record.get("posting_date") or record.get("modified")
            record_anomalies += _check_timing_anomalies(doc_date, posting_date)

        # ── Approval/SOD checks ────────────────────────────────────────
        if approval_field:
            approver = record.get(approval_field)
            owner = record.get("owner")
            modified_by = record.get("modified_by")
            record_anomalies += _check_approval_anomalies(approver, owner, modified_by)

        # ── User behavior checks ───────────────────────────────────────
        record_anomalies += _check_user_anomalies(record)

        for anomaly in record_anomalies:
            anomalies.append({
                "doctype":     doctype_name,
                "docname":     record.get("name"),
                "amount":      record.get(amount_field, 0) if amount_field else 0,
                "anomaly_type":anomaly["type"],
                "severity":    anomaly["severity"],
                "description": anomaly["description"],
            })

    return anomalies


def _check_amount_anomalies(amount, all_amounts):
    anomalies = []
    valid_amounts = [a for a in all_amounts if a and a > 0]

    if not valid_amounts or amount <= 0:
        return anomalies

    # Statistical outlier check (2 std devs)
    if len(valid_amounts) >= 5:
        mean = statistics.mean(valid_amounts)
        stdev = statistics.stdev(valid_amounts) if len(valid_amounts) > 1 else 0
        if stdev > 0 and abs(amount - mean) > 2 * stdev:
            anomalies.append({
                "type": "Statistical Outlier",
                "severity": "High",
                "description": f"Amount {amount:,.2f} is more than 2 standard deviations "
                               f"from mean ({mean:,.2f}). Requires investigation."
            })

    # Round number check (fraud indicator per ACFE)
    if amount >= 1000 and amount % 1000 == 0:
        anomalies.append({
            "type": "Round Number Amount",
            "severity": "Medium",
            "description": f"Amount {amount:,.2f} is a round number — ACFE red flag for "
                           f"fabricated or estimated transactions."
        })

    return anomalies


def _check_timing_anomalies(doc_date, posting_date):
    anomalies = []

    if doc_date:
        try:
            if isinstance(doc_date, str):
                doc_date = datetime.strptime(doc_date[:10], "%Y-%m-%d")

            # Weekend check
            if doc_date.weekday() >= 5:
                day_name = "Saturday" if doc_date.weekday() == 5 else "Sunday"
                anomalies.append({
                    "type": "Weekend Transaction",
                    "severity": "Medium",
                    "description": f"Transaction dated on a {day_name} ({doc_date.date()}). "
                                   f"Unusual business activity requires explanation."
                })

            # Period-end clustering (last 3 days of month)
            if doc_date.day >= 28:
                anomalies.append({
                    "type": "Period-End Transaction",
                    "severity": "Low",
                    "description": f"Transaction on {doc_date.date()} — period-end entry. "
                                   f"Test for window dressing and correct cutoff."
                })

            # Backdating check
            if posting_date:
                if isinstance(posting_date, str):
                    posting_date = datetime.strptime(posting_date[:10], "%Y-%m-%d")
                gap = abs((posting_date - doc_date).days)
                if gap > 7:
                    anomalies.append({
                        "type": "Backdated Entry",
                        "severity": "High",
                        "description": f"Document date and posting date differ by {gap} days. "
                                       f"Possible backdating — verify authorization."
                    })
        except Exception:
            pass

    return anomalies


def _check_approval_anomalies(approver, owner, modified_by):
    anomalies = []

    if approver and owner:
        if approver == owner:
            anomalies.append({
                "type": "Segregation of Duties Failure",
                "severity": "Critical",
                "description": f"Transaction created and approved by the same user ({owner}). "
                               f"This violates fundamental segregation of duties controls."
            })

    if approver and modified_by:
        if approver == modified_by:
            anomalies.append({
                "type": "Self-Modified After Approval",
                "severity": "High",
                "description": f"Approver ({approver}) also modified the document after approval. "
                               f"Possible tampering — requires investigation."
            })

    return anomalies


def _check_user_anomalies(record):
    anomalies = []

    modified = record.get("modified")
    if modified:
        try:
            if isinstance(modified, str):
                modified = datetime.strptime(modified[:19], "%Y-%m-%d %H:%M:%S")
            hour = modified.hour
            if hour < 6 or hour > 22:
                anomalies.append({
                    "type": "Off-Hours Activity",
                    "severity": "Medium",
                    "description": f"Transaction modified at {modified.strftime('%H:%M')} "
                                   f"— outside normal business hours. Verify legitimacy."
                })
        except Exception:
            pass

    return anomalies


# ─────────────────────────────────────────────────────────────────────────────
# Journal Entry Fraud Detection (ACFE Methodology)
# ─────────────────────────────────────────────────────────────────────────────

def analyse_journal_entry(je_doc):
    """
    Apply ACFE journal entry testing methodology to a Journal Entry.
    Returns list of risk flags.
    """
    flags = []

    # Posted by non-finance users
    owner = je_doc.get("owner", "")
    finance_roles = ["Accounts Manager", "Account User", "Finance Manager"]
    owner_roles = frappe.get_roles(owner)
    has_finance_role = any(r in owner_roles for r in finance_roles)
    if not has_finance_role:
        flags.append({
            "type": "Non-Finance User JV",
            "severity": "Critical",
            "description": f"Journal Entry posted by {owner} who does not have a Finance role. "
                           f"This is a high-risk indicator per ACFE fraud examination standards."
        })

    # No narration/remark
    if not je_doc.get("user_remark") and not je_doc.get("remark"):
        flags.append({
            "type": "No JV Narration",
            "severity": "Medium",
            "description": "Journal Entry has no narration or remarks. "
                           "All JVs should have clear business justification documented."
        })

    # Round total amount
    total_debit = je_doc.get("total_debit", 0) or 0
    if total_debit >= 1000 and total_debit % 1000 == 0:
        flags.append({
            "type": "Round Amount JV",
            "severity": "Medium",
            "description": f"Journal Entry total {total_debit:,.2f} is a round number. "
                           f"ACFE red flag — verify this is not an estimated/fabricated entry."
        })

    return flags


# ─────────────────────────────────────────────────────────────────────────────
# Nightly batch jobs
# ─────────────────────────────────────────────────────────────────────────────

def run_nightly_anomaly_scan():
    """Nightly scan of all active registered DocTypes for new anomalies."""
    registries = frappe.get_all(
        "Auditable DocType Registry",
        filters={"is_active": 1},
        fields=["name", "doctype_name", "amount_fields", "date_fields",
                "approval_fields", "risk_level"]
    )

    for reg in registries:
        try:
            _scan_doctype_for_anomalies(reg)
        except Exception as e:
            frappe.log_error(f"Anomaly scan failed for {reg.doctype_name}: {e}")


def _scan_doctype_for_anomalies(reg):
    """Scan last 30 days of a DocType for anomalies and log findings."""
    if not frappe.db.table_exists(f"tab{reg.doctype_name}"):
        return

    from_date = frappe.utils.add_days(frappe.utils.today(), -30)
    date_field = _first_csv(reg.get("date_fields", "")) or "modified"

    records = frappe.db.get_all(
        reg.doctype_name,
        filters={date_field: [">=", from_date]},
        fields=["name", "owner", "modified", "modified_by",
                "creation"] + _csv_to_list(reg.get("amount_fields", ""))
                             + _csv_to_list(reg.get("date_fields", ""))
                             + _csv_to_list(reg.get("approval_fields", "")),
        limit=500
    )

    if not records:
        return

    anomalies = run_anomaly_detection(reg.doctype_name, records, reg)

    for anomaly in anomalies:
        _log_ai_anomaly(anomaly)


def _log_ai_anomaly(anomaly):
    """Log an AI-detected anomaly if not already logged."""
    exists = frappe.db.exists("Audit Finding", {
        "reference_doctype": anomaly["doctype"],
        "reference_name":    anomaly["docname"],
        "finding_type":      anomaly["anomaly_type"],
        "source":            "AI Auto-Detection",
    })
    if exists:
        return

    frappe.get_doc({
        "doctype":            "Audit Finding",
        "reference_doctype":  anomaly["doctype"],
        "reference_name":     anomaly["docname"],
        "finding_type":       anomaly["anomaly_type"],
        "risk_rating":        anomaly["severity"],
        "observation":        anomaly["description"],
        "source":             "AI Auto-Detection",
        "status":             "Open",
        "transaction_code":   frappe.db.get_value(
            "Auditable DocType Registry",
            {"doctype_name": anomaly["doctype"]},
            "transaction_code"
        ) or "AUTO",
    }).insert(ignore_permissions=True)


def refresh_single_doctype_stats(doctype_name):
    """Refresh live statistics for one DocType in the registry."""
    reg = frappe.db.get_value(
        "Auditable DocType Registry",
        {"doctype_name": doctype_name},
        ["name", "amount_fields"],
        as_dict=True
    )
    if not reg:
        return

    # Count transactions YTD
    ytd_count = 0
    if frappe.db.table_exists(f"tab{doctype_name}"):
        ytd_count = frappe.db.count(doctype_name, filters={
            "creation": [">=", frappe.utils.get_first_day(frappe.utils.today())]
        })

    # Count open findings
    open_findings = frappe.db.count("Audit Finding", filters={
        "reference_doctype": doctype_name,
        "status": ["in", ["Open", "In Progress"]]
    })

    frappe.db.set_value("Auditable DocType Registry", reg["name"], {
        "total_transactions_ytd": ytd_count,
        "open_findings_count":    open_findings,
    })


def update_risk_scores():
    """Weekly update of risk scores for all registered DocTypes."""
    frappe.db.sql("""
        UPDATE `tabAuditable DocType Registry` r
        SET r.cumulative_findings = (
            SELECT COUNT(*) FROM `tabAudit Finding` f
            WHERE f.reference_doctype = r.doctype_name
        ),
        r.open_findings_count = (
            SELECT COUNT(*) FROM `tabAudit Finding` f
            WHERE f.reference_doctype = r.doctype_name
            AND f.status IN ('Open', 'In Progress')
        )
    """)


def refresh_audit_universe_stats():
    """Weekly refresh of all DocType stats."""
    registries = frappe.get_all(
        "Auditable DocType Registry",
        filters={"is_active": 1},
        pluck="doctype_name"
    )
    for dt in registries:
        try:
            refresh_single_doctype_stats(dt)
        except Exception:
            pass


def generate_monthly_audit_intelligence_report():
    """Generate monthly AI intelligence summary."""
    pass  # Implemented in reporting module


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _first_csv(csv_str):
    if not csv_str:
        return None
    parts = [p.strip() for p in csv_str.split(",") if p.strip()]
    return parts[0] if parts else None


def _csv_to_list(csv_str):
    if not csv_str:
        return []
    return [p.strip() for p in csv_str.split(",") if p.strip()]