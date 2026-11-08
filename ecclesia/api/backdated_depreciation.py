# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

"""
Backdated / Scheduled Depreciation Journal Entry Processor
============================================================

Purpose
-------
Automatically creates depreciation Journal Entries for submitted Assets
when their depreciation schedule_date is reached.

Features
--------
1. Processes depreciation rows where schedule_date <= today.
2. Creates one Journal Entry per depreciation schedule row.
3. Uses the EXACT schedule_date as the Journal Entry posting_date.
4. Prevents duplicate Journal Entries.
5. Supports ERPNext versions where depreciation schedules are stored:
   - directly on Asset
   - in Asset Depreciation Schedule
6. Resolves depreciation accounts from Asset Category Account.
7. Links the created Journal Entry back to the schedule row.
8. Can process one Asset manually.
9. Can process all Assets manually.
10. Designed to run safely from the Frappe scheduler.

Recommended hooks.py:

scheduler_events = {
    "cron": {
        "5 0 * * *": [
            "ecclesia.ecclesia.utils.backdated_depreciation.process_all_backdated_depreciation"
        ]
    }
}
"""

import frappe

from frappe import _
from frappe.utils import today, flt, getdate


# ============================================================================
# CONFIGURATION
# ============================================================================

LOG_PREFIX = "Depreciation Processor"


# ============================================================================
# PUBLIC ENTRY POINT - SINGLE ASSET
# ============================================================================

def make_backdated_depreciation_entries(doc, method=None):
    """
    Process all due depreciation schedule rows for one Asset.

    A row is processed when:

        schedule_date <= today
        journal_entry is empty
        depreciation_amount > 0

    Returns:
        list of created Journal Entry names.
    """

    created_entries = []

    try:
        # ------------------------------------------------------------------
        # Load Asset
        # ------------------------------------------------------------------

        asset = (
            frappe.get_doc("Asset", doc)
            if isinstance(doc, str)
            else doc
        )

        # ------------------------------------------------------------------
        # Asset validation
        # ------------------------------------------------------------------

        if not asset:
            return created_entries

        if asset.docstatus != 1:
            frappe.logger().info(
                f"{LOG_PREFIX} | Asset {asset.name} is not submitted."
            )
            return created_entries

        if not getattr(asset, "calculate_depreciation", 0):
            frappe.logger().info(
                f"{LOG_PREFIX} | Asset {asset.name} has calculate_depreciation disabled."
            )
            return created_entries

        if not asset.asset_category:
            frappe.log_error(
                message=f"Asset {asset.name} has no Asset Category.",
                title=f"{LOG_PREFIX} - Missing Asset Category",
            )
            return created_entries

        if not asset.company:
            frappe.log_error(
                message=f"Asset {asset.name} has no Company.",
                title=f"{LOG_PREFIX} - Missing Company",
            )
            return created_entries

        # ------------------------------------------------------------------
        # Get depreciation accounts
        # ------------------------------------------------------------------

        accounts = _get_depreciation_accounts(
            asset.asset_category,
            asset.company,
        )

        if not accounts:
            return created_entries

        # ------------------------------------------------------------------
        # Get schedule rows
        # ------------------------------------------------------------------

        schedule_pairs = _get_schedule_row_pairs(asset)

        if not schedule_pairs:
            frappe.logger().info(
                f"{LOG_PREFIX} | No depreciation schedule found for Asset {asset.name}."
            )
            return created_entries

        today_date = getdate(today())

        # ------------------------------------------------------------------
        # Process rows
        # ------------------------------------------------------------------

        for schedule_parent, row in schedule_pairs:

            try:

                schedule_date = getdate(row.get("schedule_date"))

                depreciation_amount = flt(
                    row.get("depreciation_amount")
                )

                journal_entry = row.get("journal_entry")

                # ----------------------------------------------------------
                # Diagnostic logging
                # ----------------------------------------------------------

                frappe.logger().info(
                    (
                        f"{LOG_PREFIX} | "
                        f"Asset={asset.name} | "
                        f"Row={row.get('name')} | "
                        f"Schedule Date={schedule_date} | "
                        f"Today={today_date} | "
                        f"Amount={depreciation_amount} | "
                        f"JE={journal_entry}"
                    )
                )

                # ----------------------------------------------------------
                # Invalid schedule date
                # ----------------------------------------------------------

                if not schedule_date:
                    frappe.logger().warning(
                        f"{LOG_PREFIX} | "
                        f"Asset {asset.name}, row {row.get('name')} "
                        f"has no schedule date."
                    )
                    continue

                # ----------------------------------------------------------
                # Future schedule
                # ----------------------------------------------------------

                if schedule_date > today_date:

                    frappe.logger().info(
                        f"{LOG_PREFIX} | "
                        f"Skipping future depreciation: "
                        f"Asset={asset.name}, "
                        f"Date={schedule_date}"
                    )

                    continue

                # ----------------------------------------------------------
                # Already linked
                # ----------------------------------------------------------

                if journal_entry:

                    frappe.logger().info(
                        f"{LOG_PREFIX} | "
                        f"Skipping already posted row: "
                        f"Asset={asset.name}, "
                        f"Row={row.get('name')}, "
                        f"JE={journal_entry}"
                    )

                    continue

                # ----------------------------------------------------------
                # Zero / negative depreciation
                # ----------------------------------------------------------

                if depreciation_amount <= 0:

                    frappe.logger().info(
                        f"{LOG_PREFIX} | "
                        f"Skipping zero/negative depreciation: "
                        f"Asset={asset.name}, "
                        f"Date={schedule_date}, "
                        f"Amount={depreciation_amount}"
                    )

                    continue

                # ----------------------------------------------------------
                # Duplicate protection
                # ----------------------------------------------------------

                existing_je = _find_existing_depreciation_je(
                    asset=asset,
                    schedule_date=schedule_date,
                    depreciation_amount=depreciation_amount,
                )

                if existing_je:

                    frappe.logger().warning(
                        f"{LOG_PREFIX} | "
                        f"Existing depreciation JE {existing_je} found for "
                        f"Asset={asset.name}, Date={schedule_date}. "
                        f"Linking it to schedule row."
                    )

                    _link_je_to_row(
                        row_name=row["name"],
                        je_name=existing_je,
                    )

                    continue

                # ----------------------------------------------------------
                # Create JE
                # ----------------------------------------------------------

                je = _create_depreciation_je(
                    asset=asset,
                    row=row,
                    accounts=accounts,
                )

                if je:

                    created_entries.append(je.name)

            except Exception:

                frappe.log_error(
                    message=frappe.get_traceback(),
                    title=(
                        f"{LOG_PREFIX} - "
                        f"Schedule Row Failed - "
                        f"{asset.name}"
                    ),
                )

                # Continue processing remaining rows
                continue

        # ------------------------------------------------------------------
        # Commit successful work
        # ------------------------------------------------------------------

        if created_entries:
            frappe.db.commit()

            frappe.logger().info(
                f"{LOG_PREFIX} | "
                f"Asset={asset.name} | "
                f"Created={len(created_entries)}"
            )

        return created_entries

    except Exception:

        frappe.log_error(
            message=frappe.get_traceback(),
            title=f"{LOG_PREFIX} - Asset Processing Failed",
        )

        return created_entries


# ============================================================================
# DEPRECIATION ACCOUNT RESOLVER
# ============================================================================

def _get_depreciation_accounts(asset_category, company):
    """
    Get depreciation accounts from Asset Category Account.

    Required fields:

        depreciation_expense_account
        accumulated_depreciation_account
    """

    if not asset_category or not company:
        return None

    try:

        rows = frappe.get_all(
            "Asset Category Account",
            filters={
                "parent": asset_category,
                "parenttype": "Asset Category",
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

    except Exception:

        frappe.log_error(
            message=frappe.get_traceback(),
            title=f"{LOG_PREFIX} - Account Lookup Failed",
        )

        return None

    if not rows:

        frappe.log_error(
            message=_(
                "No Asset Category Account record was found for "
                "Asset Category '{0}' and Company '{1}'."
            ).format(
                asset_category,
                company,
            ),
            title=f"{LOG_PREFIX} - Missing Accounts",
        )

        return None

    row = rows[0]

    depreciation_expense_account = row.get(
        "depreciation_expense_account"
    )

    accumulated_depreciation_account = row.get(
        "accumulated_depreciation_account"
    )

    if not depreciation_expense_account:

        frappe.log_error(
            message=_(
                "Depreciation Expense Account is missing for "
                "Asset Category '{0}', Company '{1}'."
            ).format(
                asset_category,
                company,
            ),
            title=f"{LOG_PREFIX} - Missing Depreciation Expense",
        )

        return None

    if not accumulated_depreciation_account:

        frappe.log_error(
            message=_(
                "Accumulated Depreciation Account is missing for "
                "Asset Category '{0}', Company '{1}'."
            ).format(
                asset_category,
                company,
            ),
            title=f"{LOG_PREFIX} - Missing Accumulated Depreciation",
        )

        return None

    return {
        "depreciation_expense_account":
            depreciation_expense_account,

        "accumulated_depreciation_account":
            accumulated_depreciation_account,
    }


# ============================================================================
# SCHEDULE DETECTION
# ============================================================================

def _get_schedule_row_pairs(asset):
    """
    Retrieve depreciation schedule rows.

    Supports:

    A. Standalone Asset Depreciation Schedule
       + Depreciation Schedule child table

    B. Legacy Asset Depreciation Schedule child table
       directly attached to Asset.
    """

    # ----------------------------------------------------------------------
    # Method 1 - Standalone Asset Depreciation Schedule
    # ----------------------------------------------------------------------

    if _has_standalone_asset_depreciation_schedule():

        return _get_standalone_schedule_rows(asset)

    # ----------------------------------------------------------------------
    # Method 2 - Legacy child table directly on Asset
    # ----------------------------------------------------------------------

    return _get_legacy_schedule_rows(asset)


# ============================================================================
# DETECT STANDALONE SCHEDULE
# ============================================================================

def _has_standalone_asset_depreciation_schedule():
    """
    Determine whether the installed ERPNext version has the standalone
    Asset Depreciation Schedule DocType.
    """

    try:

        if not frappe.db.exists(
            "DocType",
            "Asset Depreciation Schedule"
        ):
            return False

        meta = frappe.get_meta(
            "Asset Depreciation Schedule"
        )

        # In the standalone implementation, the document contains
        # an asset field.
        return bool(
            meta.has_field("asset")
        )

    except Exception:

        return False


# ============================================================================
# STANDALONE SCHEDULE
# ============================================================================

def _get_standalone_schedule_rows(asset):
    """
    Retrieve rows from:

        Asset Depreciation Schedule
                |
                +-- Depreciation Schedule
    """

    pairs = []

    try:

        schedules = frappe.get_all(
            "Asset Depreciation Schedule",
            filters={
                "asset": asset.name,
                "docstatus": 1,
            },
            fields=[
                "name",
                "finance_book",
            ],
        )

    except Exception:

        frappe.log_error(
            message=frappe.get_traceback(),
            title=f"{LOG_PREFIX} - Schedule Header Lookup Failed",
        )

        return pairs

    for schedule in schedules:

        try:

            rows = frappe.get_all(
                "Depreciation Schedule",
                filters={
                    "parent": schedule.name,
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

        except Exception:

            frappe.log_error(
                message=frappe.get_traceback(),
                title=(
                    f"{LOG_PREFIX} - "
                    f"Depreciation Schedule Lookup Failed"
                ),
            )

            continue

        for row in rows:

            row["finance_book"] = schedule.get(
                "finance_book"
            )

            pairs.append(
                (
                    schedule.name,
                    row,
                )
            )

    return pairs


# ============================================================================
# LEGACY SCHEDULE
# ============================================================================

def _get_legacy_schedule_rows(asset):
    """
    Retrieve depreciation rows directly from Asset.
    """

    pairs = []

    try:

        rows = frappe.get_all(
            "Asset Depreciation Schedule",
            filters={
                "parent": asset.name,
                "parenttype": "Asset",
            },
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

    except Exception:

        frappe.log_error(
            message=frappe.get_traceback(),
            title=f"{LOG_PREFIX} - Legacy Schedule Lookup Failed",
        )

        return pairs

    for row in rows:

        pairs.append(
            (
                asset.name,
                row,
            )
        )

    return pairs


# ============================================================================
# LINK JOURNAL ENTRY
# ============================================================================

def _link_je_to_row(row_name, je_name):
    """
    Write the Journal Entry name into the depreciation schedule row.
    """

    if not row_name or not je_name:
        return

    try:

        if _has_standalone_asset_depreciation_schedule():

            doctype = "Depreciation Schedule"

        else:

            doctype = "Asset Depreciation Schedule"

        if not frappe.db.exists(
            doctype,
            row_name,
        ):
            return

        frappe.db.set_value(
            doctype,
            row_name,
            "journal_entry",
            je_name,
            update_modified=False,
        )

    except Exception:

        frappe.log_error(
            message=frappe.get_traceback(),
            title=f"{LOG_PREFIX} - Failed Linking Journal Entry",
        )


# ============================================================================
# DUPLICATE DETECTION
# ============================================================================

def _find_existing_depreciation_je(
    asset,
    schedule_date,
    depreciation_amount,
):
    """
    Look for an existing submitted depreciation Journal Entry.

    This provides a second layer of protection against duplicates if
    journal_entry on the schedule row was not populated.
    """

    try:

        schedule_date = getdate(schedule_date)

        # ------------------------------------------------------------------
        # Search Journal Entries by posting date + remark/reference
        # ------------------------------------------------------------------

        rows = frappe.get_all(
            "Journal Entry",
            filters={
                "docstatus": 1,
                "posting_date": schedule_date,
                "voucher_type": "Depreciation Entry",
            },
            fields=[
                "name",
                "remark",
            ],
            order_by="creation asc",
        )

        if not rows:
            return None

        asset_marker = f"Asset {asset.name}"

        for row in rows:

            remark = row.get("remark") or ""

            if asset_marker not in remark:
                continue

            # Verify amount as an additional safeguard.
            try:

                accounts = frappe.get_all(
                    "Journal Entry Account",
                    filters={
                        "parent": row.name,
                        "parenttype": "Journal Entry",
                    },
                    fields=[
                        "debit_in_account_currency",
                        "credit_in_account_currency",
                    ],
                )

                total = 0

                for account in accounts:

                    total += flt(
                        account.get(
                            "debit_in_account_currency"
                        )
                    )

                    total += flt(
                        account.get(
                            "credit_in_account_currency"
                        )
                    )

                # A balanced JE has debit + credit = 2 * amount
                if abs(
                    total - (2 * flt(depreciation_amount))
                ) < 0.01:

                    return row.name

            except Exception:

                # If amount verification fails, do not automatically
                # assume it is a duplicate.
                continue

    except Exception:

        frappe.log_error(
            message=frappe.get_traceback(),
            title=f"{LOG_PREFIX} - Duplicate Check Failed",
        )

    return None


# ============================================================================
# CREATE JOURNAL ENTRY
# ============================================================================

def _create_depreciation_je(
    asset,
    row,
    accounts,
):
    """
    Create and submit one depreciation Journal Entry.

    Posting date = schedule_date.
    """

    dep_amount = flt(
        row.get("depreciation_amount")
    )

    schedule_date = getdate(
        row.get("schedule_date")
    )

    finance_book = row.get(
        "finance_book"
    )

    # ----------------------------------------------------------------------
    # Validate amount
    # ----------------------------------------------------------------------

    if dep_amount <= 0:
        return None

    # ----------------------------------------------------------------------
    # Accounts
    # ----------------------------------------------------------------------

    depreciation_expense_account = accounts[
        "depreciation_expense_account"
    ]

    accumulated_depreciation_account = accounts[
        "accumulated_depreciation_account"
    ]

    # ----------------------------------------------------------------------
    # Company
    # ----------------------------------------------------------------------

    company = asset.company

    # ----------------------------------------------------------------------
    # Cost Center
    # ----------------------------------------------------------------------

    cost_center = getattr(
        asset,
        "cost_center",
        None,
    )

    if not cost_center:

        cost_center = frappe.db.get_value(
            "Company",
            company,
            "cost_center",
        )

    # ----------------------------------------------------------------------
    # Create Journal Entry
    # ----------------------------------------------------------------------

    je = frappe.new_doc(
        "Journal Entry"
    )

    je.voucher_type = "Depreciation Entry"

    # Only use DEP- if the naming series exists.
    try:

        if frappe.db.exists(
            "DocType",
            "Journal Entry"
        ):

            je.naming_series = "DEP-"

    except Exception:
        pass

    # ----------------------------------------------------------------------
    # IMPORTANT:
    #
    # The Journal Entry posting date is the schedule date.
    # ----------------------------------------------------------------------

    je.posting_date = schedule_date

    je.company = company

    if finance_book:
        je.finance_book = finance_book

    je.remark = _(
        "Depreciation for Asset {0} ({1}) | Scheduled: {2}"
    ).format(
        asset.name,
        asset.asset_name,
        schedule_date,
    )

    # ----------------------------------------------------------------------
    # Debit - Depreciation Expense
    # ----------------------------------------------------------------------

    debit_row = {
        "account":
            depreciation_expense_account,

        "debit_in_account_currency":
            dep_amount,

        "credit_in_account_currency":
            0,

        "reference_type":
            "Asset",

        "reference_name":
            asset.name,

        "user_remark":
            _("Depreciation for {0}").format(
                asset.asset_name
            ),
    }

    if cost_center:
        debit_row["cost_center"] = cost_center

    je.append(
        "accounts",
        debit_row,
    )

    # ----------------------------------------------------------------------
    # Credit - Accumulated Depreciation
    # ----------------------------------------------------------------------

    credit_row = {
        "account":
            accumulated_depreciation_account,

        "debit_in_account_currency":
            0,

        "credit_in_account_currency":
            dep_amount,

        "reference_type":
            "Asset",

        "reference_name":
            asset.name,

        "user_remark":
            _("Accumulated Depreciation for {0}").format(
                asset.asset_name
            ),
    }

    if cost_center:
        credit_row["cost_center"] = cost_center

    je.append(
        "accounts",
        credit_row,
    )

    # ----------------------------------------------------------------------
    # Insert + Submit
    # ----------------------------------------------------------------------

    try:

        je.flags.ignore_permissions = True

        je.insert(
            ignore_permissions=True
        )

        je.submit()

        # ------------------------------------------------------------------
        # Link schedule row
        # ------------------------------------------------------------------

        _link_je_to_row(
            row_name=row["name"],
            je_name=je.name,
        )

        frappe.logger().info(
            (
                f"{LOG_PREFIX} | "
                f"JE CREATED | "
                f"JE={je.name} | "
                f"Asset={asset.name} | "
                f"Date={schedule_date} | "
                f"Amount={dep_amount}"
            )
        )

        return je

    except Exception:

        # Roll back failed JE creation.
        frappe.db.rollback()

        frappe.log_error(
            message=frappe.get_traceback(),
            title=(
                f"{LOG_PREFIX} - "
                f"Journal Entry Creation Failed - "
                f"{asset.name}"
            ),
        )

        return None


# ============================================================================
# MAIN SCHEDULED JOB
# ============================================================================

def process_all_backdated_depreciation():
    """
    Main scheduler function.

    Finds every submitted Asset having at least one depreciation row:

        schedule_date <= today
        journal_entry is empty
        depreciation_amount > 0

    Then processes the Asset.
    """

    today_date = getdate(
        today()
    )

    frappe.logger().info(
        f"{LOG_PREFIX} | Scheduler START | Date={today_date}"
    )

    processed_assets = 0
    total_je = 0
    errors = []

    # ----------------------------------------------------------------------
    # Get submitted Assets.
    #
    # Instead of relying completely on one SQL structure, retrieve submitted
    # assets first and let the schedule reader determine the actual schema.
    #
    # This is more tolerant of ERPNext customizations/version differences.
    # ----------------------------------------------------------------------

    try:

        assets = frappe.get_all(
            "Asset",
            filters={
                "docstatus": 1,
                "calculate_depreciation": 1,
            },
            fields=[
                "name",
            ],
            order_by="name asc",
        )

    except Exception:

        frappe.log_error(
            message=frappe.get_traceback(),
            title=f"{LOG_PREFIX} - Asset Search Failed",
        )

        return {
            "assets_processed": 0,
            "journal_entries_created": 0,
            "errors": [],
        }

    frappe.logger().info(
        f"{LOG_PREFIX} | "
        f"Submitted depreciation Assets found={len(assets)}"
    )

    # ----------------------------------------------------------------------
    # Process each Asset
    # ----------------------------------------------------------------------

    for asset_row in assets:

        asset_name = asset_row.name

        try:

            asset = frappe.get_doc(
                "Asset",
                asset_name,
            )

            # --------------------------------------------------------------
            # Check schedule before processing.
            # --------------------------------------------------------------

            schedule_pairs = _get_schedule_row_pairs(
                asset
            )

            has_due_rows = False

            for _, row in schedule_pairs:

                schedule_date = row.get(
                    "schedule_date"
                )

                if not schedule_date:
                    continue

                if getdate(schedule_date) > today_date:
                    continue

                if row.get("journal_entry"):
                    continue

                if flt(
                    row.get("depreciation_amount")
                ) <= 0:
                    continue

                has_due_rows = True
                break

            if not has_due_rows:
                continue

            # --------------------------------------------------------------
            # Process
            # --------------------------------------------------------------

            processed_assets += 1

            entries = make_backdated_depreciation_entries(
                asset
            )

            total_je += len(
                entries
            )

        except Exception:

            errors.append(
                asset_name
            )

            frappe.log_error(
                message=frappe.get_traceback(),
                title=(
                    f"{LOG_PREFIX} - "
                    f"Scheduler Error - "
                    f"{asset_name}"
                ),
            )

            continue

    # ----------------------------------------------------------------------
    # Final log
    # ----------------------------------------------------------------------

    frappe.logger().info(
        (
            f"{LOG_PREFIX} | Scheduler END | "
            f"Assets Processed={processed_assets} | "
            f"JEs Created={total_je} | "
            f"Errors={errors or 'None'}"
        )
    )

    return {
        "assets_processed":
            processed_assets,

        "journal_entries_created":
            total_je,

        "errors":
            errors,
    }


# ============================================================================
# MANUAL PROCESSING - ONE ASSET
# ============================================================================

@frappe.whitelist()
def run_for_asset(asset_name):
    """
    Manually process depreciation for one Asset.

    Example:

    frappe.call({
        method:
            "ecclesia.ecclesia.utils.backdated_depreciation.run_for_asset",

        args: {
            asset_name: frm.doc.name
        },

        callback: function(r) {
            if (!r.exc) {
                frm.reload_doc();
            }
        }
    });
    """

    if not asset_name:

        frappe.throw(
            _("Asset is required.")
        )

    asset = frappe.get_doc(
        "Asset",
        asset_name,
    )

    entries = make_backdated_depreciation_entries(
        asset
    )

    return {
        "message": _(
            "{0} depreciation Journal Entries created."
        ).format(
            len(entries)
        ),

        "journal_entries":
            entries,
    }


# ============================================================================
# MANUAL PROCESSING - ALL ASSETS
# ============================================================================

@frappe.whitelist()
def run_for_all():
    """
    Manually run depreciation processing for all Assets.
    """

    result = process_all_backdated_depreciation()

    return {
        "message": _(
            "Depreciation processing completed."
        ),

        "result":
            result,
    }


# ============================================================================
# PREVIEW
# ============================================================================

@frappe.whitelist()
def preview_backdated_entries(asset_name):
    """
    Preview all due depreciation rows for an Asset.

    Does NOT create Journal Entries.
    """

    if not asset_name:

        frappe.throw(
            _("Asset is required.")
        )

    asset = frappe.get_doc(
        "Asset",
        asset_name,
    )

    today_date = getdate(
        today()
    )

    pairs = _get_schedule_row_pairs(
        asset
    )

    pending_rows = []

    for schedule_parent, row in pairs:

        schedule_date = row.get(
            "schedule_date"
        )

        if not schedule_date:
            continue

        if getdate(schedule_date) > today_date:
            continue

        if row.get("journal_entry"):
            continue

        amount = flt(
            row.get("depreciation_amount")
        )

        if amount <= 0:
            continue

        pending_rows.append(
            row
        )

    total = sum(
        flt(
            row.get("depreciation_amount")
        )
        for row in pending_rows
    )

    return {
        "asset":
            asset.name,

        "today":
            today_date,

        "pending_rows":
            pending_rows,

        "total_count":
            len(pending_rows),

        "total_amount":
            total,
    }


# ============================================================================
# DIAGNOSTIC FUNCTION
# ============================================================================

@frappe.whitelist()
def diagnose_asset(asset_name):
    """
    Diagnostic utility.

    Returns everything needed to determine why depreciation is or isn't
    being posted.
    """

    if not asset_name:

        frappe.throw(
            _("Asset is required.")
        )

    asset = frappe.get_doc(
        "Asset",
        asset_name,
    )

    today_date = getdate(
        today()
    )

    schedule_pairs = _get_schedule_row_pairs(
        asset
    )

    schedule_data = []

    for parent, row in schedule_pairs:

        schedule_date = row.get(
            "schedule_date"
        )

        due = False

        if schedule_date:

            due = (
                getdate(schedule_date)
                <= today_date
            )

        schedule_data.append(
            {
                "parent": parent,
                "row_name": row.get("name"),
                "schedule_date": schedule_date,
                "due": due,
                "depreciation_amount":
                    flt(
                        row.get(
                            "depreciation_amount"
                        )
                    ),
                "journal_entry":
                    row.get(
                        "journal_entry"
                    ),
                "finance_book":
                    row.get(
                        "finance_book"
                    ),
            }
        )

    accounts = _get_depreciation_accounts(
        asset.asset_category,
        asset.company,
    )

    return {
        "asset": asset.name,
        "asset_name": asset.asset_name,
        "docstatus": asset.docstatus,
        "company": asset.company,
        "asset_category": asset.asset_category,
        "calculate_depreciation":
            asset.calculate_depreciation,
        "today": today_date,
        "standalone_schedule":
            _has_standalone_asset_depreciation_schedule(),
        "accounts": accounts,
        "schedule": schedule_data,
    }