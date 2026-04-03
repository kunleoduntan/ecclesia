# Copyright (c) 2026, 	kunle Oduntan and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate, get_last_day, add_months


@frappe.whitelist()
def post_depreciation_entries(asset=None, schedule_date=None):
    """Post depreciation entries for specified asset or all due assets"""
    
    filters = {
        "docstatus": 1,
        "schedule_date": ["<=", schedule_date or nowdate()],
        "journal_entry": ["is", "not set"]
    }
    
    if asset:
        filters["parent"] = asset
    
    schedules = frappe.get_all("Fixed Asset Depreciation Schedule",
        filters=filters,
        fields=["name", "parent", "schedule_date", "depreciation_amount", "parenttype"]
    )
    
    if not schedules:
        frappe.msgprint(_("No pending depreciation entries found"))
        return
    
    posted_count = 0
    failed_count = 0
    
    for schedule in schedules:
        try:
            create_depreciation_journal_entry(schedule.name)
            posted_count += 1
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"Depreciation Entry Failed - {schedule.name}")
            failed_count += 1
    
    frappe.msgprint(_("Posted {0} depreciation entries. {1} failed.").format(posted_count, failed_count))


def create_depreciation_journal_entry(schedule_name):
    """Create journal entry for a depreciation schedule"""
    
    schedule = frappe.get_doc("Fixed Asset Depreciation Schedule", schedule_name)
    
    if schedule.journal_entry:
        frappe.throw(_("Depreciation entry already posted for this schedule"))
    
    asset = frappe.get_doc("Fixed Asset", schedule.parent)
    category = frappe.get_doc("Fixed Asset Category", asset.asset_category)
    
    # Validate accounts
    if not category.accumulated_depreciation_account:
        frappe.throw(_("Accumulated Depreciation Account not set in Asset Category {0}").format(category.name))
    
    if not category.depreciation_expense_account:
        frappe.throw(_("Depreciation Expense Account not set in Asset Category {0}").format(category.name))
    
    # Create Journal Entry
    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Depreciation Entry"
    je.posting_date = schedule.schedule_date
    je.company = asset.company
    je.user_remark = f"Depreciation for {asset.asset_name} ({asset.asset_code})"
    
    # Debit: Depreciation Expense
    je.append("accounts", {
        "account": category.depreciation_expense_account,
        "debit_in_account_currency": flt(schedule.depreciation_amount),
        "reference_type": "Fixed Asset",
        "reference_name": asset.name,
        "cost_center": asset.cost_center
    })
    
    # Credit: Accumulated Depreciation
    je.append("accounts", {
        "account": category.accumulated_depreciation_account,
        "credit_in_account_currency": flt(schedule.depreciation_amount),
        "reference_type": "Fixed Asset",
        "reference_name": asset.name,
        "cost_center": asset.cost_center
    })
    
    je.insert()
    je.submit()
    
    # Update schedule with journal entry
    frappe.db.set_value("Fixed Asset Depreciation Schedule", schedule_name, "journal_entry", je.name)
    
    # Update asset current value
    asset.calculate_current_value()
    asset.db_set("current_value", asset.current_value, update_modified=False)
    asset.db_set("status", asset.status, update_modified=False)
    
    frappe.msgprint(_("Depreciation Entry {0} created successfully").format(
        frappe.utils.get_link_to_form("Journal Entry", je.name)))
    
    return je.name


@frappe.whitelist()
def cancel_depreciation_entry(schedule_name):
    """Cancel depreciation journal entry"""
    
    schedule = frappe.get_doc("Fixed Asset Depreciation Schedule", schedule_name)
    
    if not schedule.journal_entry:
        frappe.throw(_("No journal entry found for this schedule"))
    
    je = frappe.get_doc("Journal Entry", schedule.journal_entry)
    
    if je.docstatus == 1:
        je.cancel()
    
    # Clear journal entry reference
    frappe.db.set_value("Fixed Asset Depreciation Schedule", schedule_name, "journal_entry", None)
    
    # Update asset current value
    asset = frappe.get_doc("Fixed Asset", schedule.parent)
    asset.calculate_current_value()
    asset.db_set("current_value", asset.current_value, update_modified=False)
    
    frappe.msgprint(_("Depreciation Entry cancelled successfully"))


@frappe.whitelist()
def get_depreciation_summary(company=None, from_date=None, to_date=None):
    """Get depreciation summary for reporting"""
    
    filters = {"docstatus": 1}
    
    if company:
        filters["company"] = company
    
    if from_date and to_date:
        filters["schedule_date"] = ["between", [from_date, to_date]]
    
    # Get all depreciation schedules
    schedules = frappe.db.sql("""
        SELECT 
            ds.schedule_date,
            ds.parent as asset,
            fa.asset_name,
            fa.asset_category,
            ds.depreciation_amount,
            ds.accumulated_depreciation,
            ds.book_value,
            ds.journal_entry,
            fa.company
        FROM `tabFixed Asset Depreciation Schedule` ds
        INNER JOIN `tabFixed Asset` fa ON ds.parent = fa.name
        WHERE ds.docstatus = 1
        {conditions}
        ORDER BY ds.schedule_date DESC
    """.format(
        conditions=frappe.db.get_conditions(filters)
    ), filters, as_dict=1)
    
    return schedules