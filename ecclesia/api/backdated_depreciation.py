

# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

"""
backdated_depreciation.py
=========================
Handles backdated Journal Entry creation for the Ecclesia **Fixed Asset** DocType.

How it works
------------
When a Fixed Asset is created today but was purchased in the past (e.g. January
last year), the depreciation schedule already contains past-due rows with no
Journal Entry.  This module:

  1. Walks every un-posted schedule row on the Fixed Asset whose
     `schedule_date` <= today.
  2. Creates a Journal Entry posted on the EXACT schedule_date (backdated).
  3. Debits  → depreciation_expense_account
     Credits → accumulated_depreciation_account
  4. Links the JE name back to the schedule row (journal_entry + depreciation_posted).
  5. Updates the Fixed Asset's current_accumulated_depreciation and
     current_net_book_value to reflect all the new postings.

Child table: Fixed Asset Depreciation Schedule  (istable = 1)
  Fields used:
    schedule_date               Date
    depreciation_amount         Currency
    accumulated_depreciation_amount  Currency  (read_only, our running total)
    asset_book_value            Currency  (read_only, NBV after this row)
    journal_entry               Link → Journal Entry
    depreciation_posted         Check
    posted_date                 Date

Parent DocType: Fixed Asset
  Fields used:
    name, asset_name, asset_code, company, cost_center
    depreciation_expense_account, accumulated_depreciation_account, asset_account
    current_accumulated_depreciation, current_net_book_value
    gross_purchase_amount, salvage_value
    calculate_depreciation, docstatus
    depreciation_schedules       (Table → Fixed Asset Depreciation Schedule)
"""

import frappe
from frappe import _
from frappe.utils import today, flt, getdate, nowdate, format_date



# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT — call this from on_submit or a button
# ─────────────────────────────────────────────────────────────────────────────

def make_backdated_depreciation_entries(doc, method=None):
    """
    Creates backdated Journal Entries for every past-due, un-posted
    depreciation schedule row belonging to `doc` (a Fixed Asset document).

    Can be called:
      • directly: make_backdated_depreciation_entries(asset_doc)
      • from on_submit hook: make_backdated_depreciation_entries(doc, method)
      • by name:  make_backdated_depreciation_entries("FA-2025-00001")

    Always returns a list of created JE names — never None.
    """
    created_entries = []

    # Accept either a document or a string name
    if isinstance(doc, str):
        asset = frappe.get_doc("Fixed Asset", doc)
    else:
        asset = doc

    # Guard: only submitted Fixed Assets
    if asset.docstatus != 1:
        frappe.msgprint(
            _("Fixed Asset {0} is not submitted. Backdated depreciation skipped.").format(
                frappe.bold(asset.asset_code or asset.name)
            ),
            indicator="orange"
        )
        return created_entries

    # Guard: depreciation must be enabled
    if not asset.calculate_depreciation:
        return created_entries

    # Guard: must have the required accounts on the asset itself
    if not asset.depreciation_expense_account or not asset.accumulated_depreciation_account:
        frappe.throw(
            _("Please set Depreciation Expense Account and Accumulated Depreciation Account "
              "on Fixed Asset {0} before posting backdated depreciation.").format(
                frappe.bold(asset.asset_code or asset.name)
            )
        )

    today_date = getdate(nowdate())

    # Fetch all un-posted, past-due schedule rows ordered by date
    pending_rows = frappe.get_all(
        "Fixed Asset Depreciation Schedule",
        filters={
            "parent":              asset.name,
            "parenttype":          "Fixed Asset",
            "depreciation_posted": 0,
            "schedule_date":       ["<=", today_date],
        },
        fields=[
            "name",
            "schedule_date",
            "depreciation_amount",
            "accumulated_depreciation_amount",
            "asset_book_value",
            "journal_entry",
        ],
        order_by="schedule_date asc",
    )

    if not pending_rows:
        frappe.msgprint(
            _("No past-due unposted depreciation rows found for Fixed Asset {0}.").format(
                frappe.bold(asset.asset_code or asset.name)
            ),
            indicator="blue"
        )
        return created_entries

    for row in pending_rows:
        # Skip if already linked to a JE (safety check)
        if row.get("journal_entry"):
            continue

        dep_amount = flt(row.get("depreciation_amount"))
        if dep_amount <= 0:
            continue

        je = _create_depreciation_je(asset, row)
        if je:
            _mark_row_posted(row["name"], je.name, row["schedule_date"])
            created_entries.append(je.name)

    if created_entries:
        # Refresh asset accumulated depreciation & NBV
        _update_asset_book_values(asset)
        frappe.db.commit()

        frappe.msgprint(
            _("✅ Created <b>{0}</b> backdated depreciation Journal Entries for "
              "Fixed Asset <b>{1}</b>:<br><br>{2}").format(
                len(created_entries),
                asset.asset_code or asset.name,
                "<br>".join(
                    frappe.utils.get_link_to_form("Journal Entry", je)
                    for je in created_entries
                ),
            ),
            indicator="green",
            title=_("Backdated Depreciation Posted")
        )

    return created_entries


# ─────────────────────────────────────────────────────────────────────────────
# CREATE ONE JOURNAL ENTRY (backdated to schedule_date)
# ─────────────────────────────────────────────────────────────────────────────

def _create_depreciation_je(asset, row):
    """
    Builds and submits one backdated Journal Entry for a single schedule row.

    Debit:  Depreciation Expense Account
    Credit: Accumulated Depreciation Account

    The posting_date is set to row["schedule_date"] so the entry is
    backdated correctly in the general ledger.
    """
    dep_amount    = flt(row["depreciation_amount"])
    schedule_date = row["schedule_date"]

    dep_expense_account  = asset.depreciation_expense_account
    accum_dep_account    = asset.accumulated_depreciation_account

    company      = asset.company
    cost_center  = (
        asset.cost_center
        or frappe.db.get_value("Company", company, "cost_center")
    )

    remark = _(
        "Backdated Depreciation — Fixed Asset {0} ({1}) | Period: {2}"
    ).format(
        asset.asset_code or asset.name,
        asset.asset_name,
        format_date(schedule_date)
    )

    je = frappe.new_doc("Journal Entry")
    je.voucher_type  = "Depreciation Entry"
    je.posting_date  = schedule_date      # ← KEY: backdated to schedule date
    je.company       = company
    je.user_remark   = remark

    # Debit — Depreciation Expense
    je.append("accounts", {
        "account":                    dep_expense_account,
        "debit_in_account_currency":  dep_amount,
        "credit_in_account_currency": 0,
        "cost_center":                cost_center,
        "reference_type":             "Fixed Asset",
        "reference_name":             asset.name,
        "user_remark":                remark,
    })

    # Credit — Accumulated Depreciation
    je.append("accounts", {
        "account":                    accum_dep_account,
        "credit_in_account_currency": dep_amount,
        "debit_in_account_currency":  0,
        "cost_center":                cost_center,
        "reference_type":             "Fixed Asset",
        "reference_name":             asset.name,
        "user_remark":                remark,
    })

    try:
        je.flags.ignore_permissions = True
        je.insert()
        je.submit()

        frappe.logger().info(
            "Backdated Depreciation JE {0} | Fixed Asset {1} | Date {2} | Amount {3}".format(
                je.name, asset.name, schedule_date, dep_amount
            )
        )
        return je

    except Exception:
        frappe.log_error(
            message=frappe.get_traceback(),
            title=_("Backdated Depreciation JE Failed — Fixed Asset {0}").format(asset.name),
        )
        frappe.msgprint(
            _("⚠️ Failed to create JE for {0} on {1}. See Error Log.").format(
                asset.asset_code or asset.name, format_date(schedule_date)
            ),
            indicator="red"
        )
        return None


# ─────────────────────────────────────────────────────────────────────────────
# MARK SCHEDULE ROW AS POSTED
# ─────────────────────────────────────────────────────────────────────────────

def _mark_row_posted(row_name, je_name, schedule_date):
    """Update the child table row to reflect the posted JE."""
    frappe.db.set_value(
        "Fixed Asset Depreciation Schedule",
        row_name,
        {
            "journal_entry":       je_name,
            "depreciation_posted": 1,
            "posted_date":         schedule_date,
        },
        update_modified=False,
    )


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE PARENT ASSET BOOK VALUES AFTER POSTING
# ─────────────────────────────────────────────────────────────────────────────

def _update_asset_book_values(asset):
    """
    Recalculates current_accumulated_depreciation and current_net_book_value
    on the Fixed Asset by summing all posted depreciation rows.
    """
    total_posted = frappe.db.sql("""
        SELECT IFNULL(SUM(depreciation_amount), 0)
        FROM   `tabFixed Asset Depreciation Schedule`
        WHERE  parent             = %s
          AND  parenttype         = 'Fixed Asset'
          AND  depreciation_posted = 1
    """, asset.name)[0][0] or 0

    total_accumulated = flt(asset.opening_accumulated_depreciation or 0) + flt(total_posted)
    net_book_value    = flt(asset.current_gross_value or asset.gross_purchase_amount) - total_accumulated

    # Clamp to salvage value
    salvage = flt(asset.salvage_value or 0)
    if net_book_value < salvage:
        net_book_value = salvage

    frappe.db.set_value("Fixed Asset", asset.name, {
        "current_accumulated_depreciation": total_accumulated,
        "current_net_book_value":           net_book_value,
    }, update_modified=False)

    # Update last_depreciation_date to the most recently posted row
    last_date = frappe.db.get_value(
        "Fixed Asset Depreciation Schedule",
        {"parent": asset.name, "parenttype": "Fixed Asset", "depreciation_posted": 1},
        "schedule_date",
        order_by="schedule_date desc",
    )
    if last_date:
        frappe.db.set_value("Fixed Asset", asset.name, "last_depreciation_date", last_date,
                            update_modified=False)

    # Update next_depreciation_date to the first unposted row
    next_date = frappe.db.get_value(
        "Fixed Asset Depreciation Schedule",
        {"parent": asset.name, "parenttype": "Fixed Asset", "depreciation_posted": 0},
        "schedule_date",
        order_by="schedule_date asc",
    )
    frappe.db.set_value("Fixed Asset", asset.name, "next_depreciation_date", next_date or None,
                        update_modified=False)


# ─────────────────────────────────────────────────────────────────────────────
# SCHEDULED JOB — runs nightly to catch all assets with pending backdated rows
# ─────────────────────────────────────────────────────────────────────────────

def process_all_backdated_depreciation():
    """
    Finds ALL submitted Fixed Assets with un-posted past-due depreciation rows
    and creates Journal Entries for them.

    Register in hooks.py:
        scheduler_events = {
            "daily": [
                "ecclesia.ecclesia.utils.backdated_depreciation.process_all_backdated_depreciation"
            ]
        }
    """
    today_date = nowdate()

    pending_assets = frappe.db.sql("""
        SELECT DISTINCT ds.parent AS asset_name
        FROM   `tabFixed Asset Depreciation Schedule` ds
        INNER JOIN `tabFixed Asset` fa ON fa.name = ds.parent
        WHERE  fa.docstatus              = 1
          AND  fa.calculate_depreciation = 1
          AND  ds.schedule_date         <= %(today)s
          AND  ds.depreciation_posted    = 0
          AND  ds.depreciation_amount    > 0
          AND  (ds.journal_entry IS NULL OR ds.journal_entry = '')
    """, {"today": today_date}, as_dict=True)

    if not pending_assets:
        frappe.logger().info("Backdated Depreciation Scheduler: No pending Fixed Assets.")
        return

    frappe.logger().info(
        "Backdated Depreciation Scheduler: {0} Fixed Asset(s) to process.".format(
            len(pending_assets)
        )
    )

    total_je = 0
    errors   = []

    for record in pending_assets:
        try:
            asset   = frappe.get_doc("Fixed Asset", record.asset_name)
            entries = make_backdated_depreciation_entries(asset)
            total_je += len(entries)
        except Exception:
            errors.append(record.asset_name)
            frappe.log_error(
                message=frappe.get_traceback(),
                title=_("Backdated Depreciation Scheduler Error — {0}").format(record.asset_name),
            )

    frappe.logger().info(
        "Backdated Depreciation Scheduler: Done. {0} JEs created. Errors: {1}".format(
            total_je, errors or "None"
        )
    )


# ─────────────────────────────────────────────────────────────────────────────
# WHITELISTED API — callable from buttons or the browser
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def run_for_asset(asset_name):
    """
    Post all past-due backdated depreciation for ONE Fixed Asset.

    Call from JS button:
        frappe.call({
            method: 'ecclesia.ecclesia.utils.backdated_depreciation.run_for_asset',
            args: { asset_name: frm.doc.name },
            callback: r => { if (!r.exc) frm.reload_doc(); }
        });
    """
    asset   = frappe.get_doc("Fixed Asset", asset_name)
    entries = make_backdated_depreciation_entries(asset)
    return {
        "message":         _("{0} Journal Entries created.").format(len(entries)),
        "journal_entries": entries,
    }


@frappe.whitelist()
def run_for_all():
    """
    Post all past-due backdated depreciation for ALL Fixed Assets.

    Call from a scheduled job or an admin button.
    """
    process_all_backdated_depreciation()
    return {
        "message": _("Backdated depreciation processing complete. Check Error Log for failures.")
    }


@frappe.whitelist()
def preview_backdated_entries(asset_name):
    """
    Returns a list of pending backdated rows WITHOUT creating any JEs.
    Useful for showing a preview dialog before the user confirms.

    Returns list of dicts: schedule_date, depreciation_amount, accumulated_depreciation_amount
    """
    today_date = getdate(nowdate())

    rows = frappe.get_all(
        "Fixed Asset Depreciation Schedule",
        filters={
            "parent":              asset_name,
            "parenttype":          "Fixed Asset",
            "depreciation_posted": 0,
            "schedule_date":       ["<=", today_date],
        },
        fields=[
            "schedule_date",
            "depreciation_amount",
            "accumulated_depreciation_amount",
            "asset_book_value",
        ],
        order_by="schedule_date asc",
    )

    total = sum(flt(r["depreciation_amount"]) for r in rows)

    return {
        "pending_rows": rows,
        "total_count":  len(rows),
        "total_amount": total,
    }


#ERPNext standard Asset -- Backdated

# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def make_backdated_depreciation_entries(doc, method=None):
    """
    Creates backdated Journal Entries for every past-due, un-posted
    depreciation schedule row belonging to `doc` (an Asset document).

    Always returns a list — never None.
    """
    created_entries = []

    asset = frappe.get_doc("Asset", doc) if isinstance(doc, str) else doc

    if asset.docstatus != 1:
        frappe.msgprint(
            _("Asset {0} is not submitted. Skipping backdated depreciation.").format(asset.name)
        )
        return created_entries

    if not asset.calculate_depreciation:
        return created_entries

    # Resolve accounts once from Asset Category for this company
    accounts = _get_depreciation_accounts(asset.asset_category, asset.company)
    if not accounts:
        frappe.log_error(
            message=_(
                "No depreciation accounts found in Asset Category '{0}' "
                "for Company '{1}'. Asset: {2}"
            ).format(asset.asset_category, asset.company, asset.name),
            title="Backdated Depreciation – Missing Accounts",
        )
        return created_entries

    today_date   = getdate(today())
    schedule_pairs = _get_schedule_row_pairs(asset)

    if not schedule_pairs:
        return created_entries

    for ads_name, row in schedule_pairs:
        scheduled_date = getdate(row["schedule_date"])

        if scheduled_date > today_date:
            continue
        if row.get("journal_entry"):
            continue
        if not flt(row.get("depreciation_amount")):
            continue

        je = _create_depreciation_je(asset, row, accounts)
        if je:
            _mark_row_posted(row["name"])
            created_entries.append(je.name)

    if created_entries:
        frappe.db.commit()
        frappe.msgprint(
            _("Created {0} backdated depreciation Journal Entries for Asset {1}:<br>{2}").format(
                len(created_entries),
                asset.name,
                "<br>".join(created_entries),
            )
        )

    return created_entries


# ─────────────────────────────────────────────────────────────────────────────
# ACCOUNT RESOLVER — reads from Asset Category Account child table
# ─────────────────────────────────────────────────────────────────────────────

def _get_depreciation_accounts(asset_category, company):
    """
    Fetches depreciation_expense_account and accumulated_depreciation_account
    from the Asset Category Account child table, filtered by company.

    Asset Category
      └── accounts (child table: Asset Category Account)
            ├── company_name
            ├── fixed_asset_account
            ├── accumulated_depreciation_account
            └── depreciation_expense_account

    Returns a dict or None.
    """
    if not asset_category or not company:
        return None

    rows = frappe.get_all(
        "Asset Category Account",
        filters={
            "parent":       asset_category,
            "parenttype":   "Asset Category",
            "company_name": company,
        },
        fields=[
            "depreciation_expense_account",
            "accumulated_depreciation_account",
            "fixed_asset_account",
            "capital_work_in_progress_account",
        ],
        limit=1,
    )

    if not rows:
        return None

    row = rows[0]

    if not row.get("depreciation_expense_account") or not row.get("accumulated_depreciation_account"):
        frappe.log_error(
            message=_(
                "Asset Category '{0}' has an account row for company '{1}' "
                "but depreciation accounts are not filled in."
            ).format(asset_category, company),
            title="Backdated Depreciation – Incomplete Accounts",
        )
        return None

    return {
        "depreciation_expense_account":    row["depreciation_expense_account"],
        "accumulated_depreciation_account": row["accumulated_depreciation_account"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# SCHEDULE ROW FETCHER — v13 child table  OR  v14+ separate doctype
# ─────────────────────────────────────────────────────────────────────────────

def _is_v14_plus():
    """True when Asset Depreciation Schedule is a standalone submittable doc (v14+)."""
    try:
        meta = frappe.get_meta("Asset Depreciation Schedule")
        return any(f.fieldname == "asset" for f in meta.fields)
    except Exception:
        return False


def _get_schedule_row_pairs(asset):
    """
    Returns list of (ads_name, row_dict) for all depreciation schedule rows.
    row_dict always contains: name, schedule_date, depreciation_amount, journal_entry
    """
    if _is_v14_plus():
        pairs = []
        ads_list = frappe.get_all(
            "Asset Depreciation Schedule",
            filters={"asset": asset.name, "docstatus": 1},
            fields=["name", "finance_book"],
        )
        for ads in ads_list:
            rows = frappe.get_all(
                "Depreciation Schedule",
                filters={
                    "parent":     ads["name"],
                    "parenttype": "Asset Depreciation Schedule",
                },
                fields=[
                    "name",
                    "schedule_date",
                    "depreciation_amount",
                    "accumulated_depreciation_amount",
                    "journal_entry",
                ],
                order_by="schedule_date asc",
            )
            for row in rows:
                row["finance_book"] = ads.get("finance_book")
                pairs.append((ads["name"], row))
        return pairs

    # v13 — child table directly on Asset
    rows = frappe.get_all(
        "Asset Depreciation Schedule",
        filters={"parent": asset.name, "parenttype": "Asset"},
        fields=[
            "name",
            "schedule_date",
            "depreciation_amount",
            "accumulated_depreciation_amount",
            "journal_entry",
            "finance_book",
        ],
        order_by="schedule_date asc",
    )
    return [(asset.name, row) for row in rows]


# ─────────────────────────────────────────────────────────────────────────────
# MARK ROW AS POSTED
# ─────────────────────────────────────────────────────────────────────────────

def _mark_row_posted(row_name):
    child_doctype = "Depreciation Schedule" if _is_v14_plus() else "Asset Depreciation Schedule"
    frappe.db.set_value(
        child_doctype,
        row_name,
        {"journal_entry": row_name},   # temporarily hold; overwritten below
        update_modified=False,
    )


def _link_je_to_row(row_name, je_name):
    child_doctype = "Depreciation Schedule" if _is_v14_plus() else "Asset Depreciation Schedule"
    frappe.db.set_value(
        child_doctype,
        row_name,
        {"journal_entry": je_name},
        update_modified=False,
    )


# ─────────────────────────────────────────────────────────────────────────────
# CREATE ONE JOURNAL ENTRY
# ─────────────────────────────────────────────────────────────────────────────

def _create_depreciation_je(asset, row, accounts):
    """
    Builds and submits one backdated Journal Entry for a single schedule row.

    :param asset:    Asset document
    :param row:      Normalised row dict
    :param accounts: Dict with depreciation_expense_account &
                     accumulated_depreciation_account (from Asset Category)
    :returns:        Submitted JE doc, or None on failure
    """
    dep_amount    = flt(row["depreciation_amount"])
    schedule_date = row["schedule_date"]
    finance_book  = row.get("finance_book")

    dep_expense_account = accounts["depreciation_expense_account"]
    accum_dep_account   = accounts["accumulated_depreciation_account"]

    company     = asset.company
    cost_center = (
        asset.cost_center
        or frappe.db.get_value("Company", company, "cost_center")
    )

    je = frappe.new_doc("Journal Entry")
    je.voucher_type  = "Depreciation Entry"
    je.naming_series = "DEP-"
    je.posting_date  = schedule_date       # ← backdated to the scheduled date
    je.company       = company
    je.finance_book  = finance_book
    je.remark = _(
        "Backdated Depreciation for Asset {0} ({1}) | Scheduled: {2}"
    ).format(asset.name, asset.asset_name, schedule_date)

    # Debit — Depreciation Expense Account
    je.append("accounts", {
        "account":                    dep_expense_account,
        "debit_in_account_currency":  dep_amount,
        "credit_in_account_currency": 0,
        "cost_center":                cost_center,
        "reference_type":             "Asset",
        "reference_name":             asset.name,
        "user_remark":                _("Depreciation for {0}").format(asset.asset_name),
    })

    # Credit — Accumulated Depreciation Account
    je.append("accounts", {
        "account":                    accum_dep_account,
        "credit_in_account_currency": dep_amount,
        "debit_in_account_currency":  0,
        "cost_center":                cost_center,
        "reference_type":             "Asset",
        "reference_name":             asset.name,
        "user_remark":                _("Accumulated Depreciation for {0}").format(asset.asset_name),
    })

    try:
        je.flags.ignore_permissions = True
        je.insert()
        je.submit()

        # Link JE back to the schedule row
        _link_je_to_row(row["name"], je.name)

        frappe.logger().info(
            "Backdated Depreciation JE {0} | Asset {1} | Date {2}".format(
                je.name, asset.name, schedule_date
            )
        )
        return je

    except Exception:
        frappe.log_error(
            message=frappe.get_traceback(),
            title=_("Backdated Depreciation JE Failed – Asset {0}").format(asset.name),
        )
        return None


# ─────────────────────────────────────────────────────────────────────────────
# SCHEDULED JOB
# ─────────────────────────────────────────────────────────────────────────────

def process_all_backdated_depreciation():
    """
    Finds all submitted Assets with un-posted past-due depreciation rows
    and creates Journal Entries for them.
    """
    today_date = today()

    if _is_v14_plus():
        pending = frappe.db.sql(
            """
            SELECT DISTINCT ads.asset AS asset_name
            FROM   `tabAsset Depreciation Schedule` ads
            INNER JOIN `tabDepreciation Schedule` ds
                    ON ds.parent     = ads.name
                   AND ds.parenttype = 'Asset Depreciation Schedule'
            INNER JOIN `tabAsset` a ON a.name = ads.asset
            WHERE  a.docstatus              = 1
              AND  a.calculate_depreciation = 1
              AND  ads.docstatus            = 1
              AND  ds.schedule_date        <= %(today)s
              AND  (ds.journal_entry IS NULL OR ds.journal_entry = '')
              AND  ds.depreciation_amount   > 0
            """,
            {"today": today_date},
            as_dict=True,
        )
    else:
        pending = frappe.db.sql(
            """
            SELECT DISTINCT ads.parent AS asset_name
            FROM   `tabAsset Depreciation Schedule` ads
            INNER JOIN `tabAsset` a ON a.name = ads.parent
            WHERE  a.docstatus              = 1
              AND  a.calculate_depreciation = 1
              AND  ads.schedule_date       <= %(today)s
              AND  (ads.journal_entry IS NULL OR ads.journal_entry = '')
              AND  ads.depreciation_amount  > 0
            """,
            {"today": today_date},
            as_dict=True,
        )

    if not pending:
        frappe.logger().info("Backdated Depreciation Scheduler: No pending assets.")
        return

    frappe.logger().info(
        "Backdated Depreciation Scheduler: {0} asset(s) to process.".format(len(pending))
    )

    total_je = 0
    errors   = []

    for record in pending:
        try:
            asset   = frappe.get_doc("Asset", record.asset_name)
            entries = make_backdated_depreciation_entries(asset)
            total_je += len(entries)
        except Exception:
            errors.append(record.asset_name)
            frappe.log_error(
                message=frappe.get_traceback(),
                title=_("Backdated Depreciation Scheduler Error – {0}").format(record.asset_name),
            )

    frappe.logger().info(
        "Backdated Depreciation Scheduler: Done. {0} JEs created. Errors: {1}".format(
            total_je, errors or "None"
        )
    )


# ─────────────────────────────────────────────────────────────────────────────
# WHITELISTED API
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def run_for_asset(asset_name):
    """
    POST /api/method/ecclesia.api.backdated_depreciation.run_for_asset
    Body: { "asset_name": "ACC-ASS-0001" }
    """
    asset   = frappe.get_doc("Asset", asset_name)
    entries = make_backdated_depreciation_entries(asset)
    return {
        "message":         _("{0} Journal Entries created.").format(len(entries)),
        "journal_entries": entries,
    }


@frappe.whitelist()
def run_for_all():
    """
    POST /api/method/ecclesia.api.backdated_depreciation.run_for_all
    """
    process_all_backdated_depreciation()
    return {
        "message": _("Backdated depreciation processing completed. Check Error Log for any failures.")
    }
