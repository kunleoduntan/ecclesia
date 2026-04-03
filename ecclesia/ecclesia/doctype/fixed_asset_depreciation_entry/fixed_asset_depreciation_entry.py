# Copyright (c) 2026, 	kunle Oduntan and contributors
# For license information, please see license.txt

# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ecclesia and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
    flt, getdate, nowdate, add_months, get_last_day, 
    date_diff, cint, today, format_date, now_datetime
)
from frappe.utils.data import get_first_day, get_last_day
import json


class FixedAssetDepreciationEntry(Document):
    def validate(self):
        """Validate depreciation entry"""
        self.validate_dates()
        self.validate_entries()
        self.calculate_totals()
    
    def before_submit(self):
        """Before submit validations"""
        if not self.depreciation_entries:
            frappe.throw(_("Please add assets for depreciation"))
        
        self.validate_duplicate_schedules()
    
    def on_submit(self):
        """On submit operations"""
        self.status = "Submitted"
        self.processed_by = frappe.session.user
        self.processed_date = now_datetime()
        
        # Create journal entry
        self.create_journal_entry()
        
        # Update asset schedules
        self.update_asset_schedules()
        
        # Update asset values
        self.update_asset_values()
        
        self.status = "Posted"
        self.db_set("status", "Posted", update_modified=False)
        self.db_set("processed_by", self.processed_by, update_modified=False)
        self.db_set("processed_date", self.processed_date, update_modified=False)
    
    def on_cancel(self):
        """On cancel operations"""
        # Cancel journal entry
        self.cancel_journal_entry()
        
        # Revert asset schedules
        self.revert_asset_schedules()
        
        # Revert asset values
        self.revert_asset_values()
        
        self.status = "Cancelled"
        self.db_set("status", "Cancelled", update_modified=False)
    
    def validate_dates(self):
        """Validate period dates"""
        if getdate(self.period_start_date) > getdate(self.period_end_date):
            frappe.throw(_("Period Start Date cannot be after Period End Date"))
        
        if getdate(self.posting_date) < getdate(self.period_end_date):
            frappe.throw(_("Posting Date should be on or after Period End Date"))
    
    def validate_entries(self):
        """Validate depreciation entries"""
        if not self.depreciation_entries:
            return
        
        seen_assets = set()
        for entry in self.depreciation_entries:
            # Check for duplicate assets
            if entry.asset in seen_assets:
                frappe.throw(_("Asset {0} appears multiple times").format(entry.asset))
            seen_assets.add(entry.asset)
            
            # Validate depreciation amount
            if flt(entry.depreciation_amount) <= 0:
                frappe.throw(_("Depreciation amount must be greater than 0 for asset {0}").format(entry.asset))
            
            # Validate accounts
            if not entry.depreciation_account:
                frappe.throw(_("Depreciation Account is required for asset {0}").format(entry.asset))
            
            if not entry.accumulated_depreciation_account:
                frappe.throw(_("Accumulated Depreciation Account is required for asset {0}").format(entry.asset))
            
            # Validate cost center
            if not entry.cost_center:
                frappe.throw(_("Cost Center is required for asset {0}").format(entry.asset))
    
    def validate_duplicate_schedules(self):
        """Check if depreciation is already posted for this period"""
        for entry in self.depreciation_entries:
            # Check if schedule is already posted
            asset_doc = frappe.get_doc("Fixed Asset", entry.asset)
            
            if not asset_doc.depreciation_schedule:
                continue
            
            for schedule in asset_doc.depreciation_schedule:
                if (schedule.schedule_date == entry.schedule_date and 
                    schedule.depreciation_posted and
                    schedule.depreciation_entry != self.name):
                    frappe.throw(
                        _("Depreciation for asset {0} on date {1} is already posted in {2}").format(
                            entry.asset,
                            format_date(entry.schedule_date),
                            schedule.depreciation_entry
                        )
                    )
    
    def calculate_totals(self):
        """Calculate summary totals"""
        if not self.depreciation_entries:
            self.total_assets = 0
            self.total_depreciation_amount = 0
            self.total_accumulated_depreciation = 0
            return
        
        self.total_assets = len(self.depreciation_entries)
        self.total_depreciation_amount = sum(flt(d.depreciation_amount) for d in self.depreciation_entries)
        self.total_accumulated_depreciation = sum(flt(d.accumulated_depreciation_after) for d in self.depreciation_entries)
    
    def create_journal_entry(self):
        """Create journal entry for depreciation"""
        if self.journal_entry:
            return
        
        # Group entries by accounts and cost center
        account_groups = {}
        
        for entry in self.depreciation_entries:
            key = (
                entry.depreciation_account,
                entry.accumulated_depreciation_account,
                entry.cost_center
            )
            
            if key not in account_groups:
                account_groups[key] = {
                    'depreciation_account': entry.depreciation_account,
                    'accumulated_depreciation_account': entry.accumulated_depreciation_account,
                    'cost_center': entry.cost_center,
                    'amount': 0
                }
            
            account_groups[key]['amount'] += flt(entry.depreciation_amount)
        
        # Create journal entry
        je = frappe.new_doc("Journal Entry")
        je.voucher_type = "Depreciation Entry"
        je.company = self.company
        je.posting_date = self.posting_date
        je.cheque_date = self.posting_date
        je.cheque_no = self.name
        je.user_remark = _("Depreciation for period {0} to {1}").format(
            format_date(self.period_start_date),
            format_date(self.period_end_date)
        )
        je.finance_book = self.finance_book
        
        total_debit = 0
        total_credit = 0
        
        # Add entries for each account group
        for group in account_groups.values():
            # Debit depreciation expense
            je.append("accounts", {
                "account": group['depreciation_account'],
                "debit_in_account_currency": flt(group['amount'], 2),
                "credit_in_account_currency": 0,
                "cost_center": group['cost_center'],
                "reference_type": "Fixed Asset Depreciation Entry",
                "reference_name": self.name
            })
            total_debit += flt(group['amount'], 2)
            
            # Credit accumulated depreciation
            je.append("accounts", {
                "account": group['accumulated_depreciation_account'],
                "debit_in_account_currency": 0,
                "credit_in_account_currency": flt(group['amount'], 2),
                "cost_center": group['cost_center'],
                "reference_type": "Fixed Asset Depreciation Entry",
                "reference_name": self.name
            })
            total_credit += flt(group['amount'], 2)
        
        # Validate balance
        if abs(total_debit - total_credit) > 0.01:
            frappe.throw(_("Journal Entry is not balanced. Debit: {0}, Credit: {1}").format(
                total_debit, total_credit
            ))
        
        je.flags.ignore_permissions = True
        je.insert()
        je.submit()
        
        # Update reference
        self.db_set("journal_entry", je.name, update_modified=False)
        self.db_set("total_debit", total_debit, update_modified=False)
        self.db_set("total_credit", total_credit, update_modified=False)
        
        frappe.msgprint(_("Journal Entry {0} created successfully").format(je.name), alert=True)
    
    def cancel_journal_entry(self):
        """Cancel related journal entry"""
        if self.journal_entry:
            je = frappe.get_doc("Journal Entry", self.journal_entry)
            if je.docstatus == 1:
                je.flags.ignore_permissions = True
                je.cancel()
                frappe.msgprint(_("Journal Entry {0} cancelled").format(self.journal_entry), alert=True)
    
    def update_asset_schedules(self):
        """Update depreciation schedules for all assets"""
        for entry in self.depreciation_entries:
            try:
                asset_doc = frappe.get_doc("Fixed Asset", entry.asset)
                
                # Find matching schedule
                schedule_found = False
                for schedule in asset_doc.depreciation_schedule:
                    if schedule.schedule_date == entry.schedule_date:
                        schedule.depreciation_posted = 1
                        schedule.posted_date = self.posting_date
                        schedule.depreciation_entry = self.name
                        schedule.journal_entry = self.journal_entry
                        schedule_found = True
                        break
                
                if not schedule_found:
                    frappe.throw(_("Schedule not found for asset {0} on date {1}").format(
                        entry.asset, format_date(entry.schedule_date)
                    ))
                
                # Save asset
                asset_doc.flags.ignore_permissions = True
                asset_doc.flags.ignore_validate_update_after_submit = True
                asset_doc.save()
                
                # Mark as posted in entry
                entry.posted = 1
                
            except Exception as e:
                entry.posted = 0
                entry.error_log = str(e)
                frappe.log_error(
                    message=frappe.get_traceback(),
                    title=_("Depreciation Schedule Update Failed for {0}").format(entry.asset)
                )
    
    def revert_asset_schedules(self):
        """Revert depreciation schedules for all assets"""
        for entry in self.depreciation_entries:
            try:
                asset_doc = frappe.get_doc("Fixed Asset", entry.asset)
                
                # Find matching schedule
                for schedule in asset_doc.depreciation_schedule:
                    if (schedule.schedule_date == entry.schedule_date and 
                        schedule.depreciation_entry == self.name):
                        schedule.depreciation_posted = 0
                        schedule.posted_date = None
                        schedule.depreciation_entry = None
                        schedule.journal_entry = None
                        break
                
                # Save asset
                asset_doc.flags.ignore_permissions = True
                asset_doc.flags.ignore_validate_update_after_submit = True
                asset_doc.save()
                
                # Mark as not posted
                entry.posted = 0
                
            except Exception as e:
                frappe.log_error(
                    message=frappe.get_traceback(),
                    title=_("Depreciation Schedule Revert Failed for {0}").format(entry.asset)
                )
    
    def update_asset_values(self):
        """Update accumulated depreciation and book values for assets"""
        for entry in self.depreciation_entries:
            try:
                asset_doc = frappe.get_doc("Fixed Asset", entry.asset)
                
                # Update accumulated depreciation
                new_accumulated = flt(asset_doc.accumulated_depreciation) + flt(entry.depreciation_amount)
                asset_doc.db_set("accumulated_depreciation", new_accumulated, update_modified=False)
                
                # Update current value
                new_value = flt(asset_doc.gross_purchase_amount) - new_accumulated
                asset_doc.db_set("current_value", new_value, update_modified=False)
                
                # Update depreciation percentage
                if flt(asset_doc.gross_purchase_amount) > 0:
                    dep_percentage = (new_accumulated / flt(asset_doc.gross_purchase_amount)) * 100
                    asset_doc.db_set("depreciation_percentage", dep_percentage, update_modified=False)
                
                # Check if fully depreciated
                if new_value <= 0:
                    asset_doc.db_set("status", "Fully Depreciated", update_modified=False)
                elif new_accumulated > 0:
                    asset_doc.db_set("status", "Partially Depreciated", update_modified=False)
                
            except Exception as e:
                frappe.log_error(
                    message=frappe.get_traceback(),
                    title=_("Asset Value Update Failed for {0}").format(entry.asset)
                )
    
    def revert_asset_values(self):
        """Revert accumulated depreciation and book values"""
        for entry in self.depreciation_entries:
            try:
                asset_doc = frappe.get_doc("Fixed Asset", entry.asset)
                
                # Revert accumulated depreciation
                new_accumulated = flt(asset_doc.accumulated_depreciation) - flt(entry.depreciation_amount)
                asset_doc.db_set("accumulated_depreciation", new_accumulated, update_modified=False)
                
                # Revert current value
                new_value = flt(asset_doc.gross_purchase_amount) - new_accumulated
                asset_doc.db_set("current_value", new_value, update_modified=False)
                
                # Update depreciation percentage
                if flt(asset_doc.gross_purchase_amount) > 0:
                    dep_percentage = (new_accumulated / flt(asset_doc.gross_purchase_amount)) * 100
                    asset_doc.db_set("depreciation_percentage", dep_percentage, update_modified=False)
                
                # Update status
                if new_accumulated > 0:
                    asset_doc.db_set("status", "Partially Depreciated", update_modified=False)
                elif asset_doc.docstatus == 1:
                    asset_doc.db_set("status", "Submitted", update_modified=False)
                
            except Exception as e:
                frappe.log_error(
                    message=frappe.get_traceback(),
                    title=_("Asset Value Revert Failed for {0}").format(entry.asset)
                )


# Whitelisted methods for client-side calls

@frappe.whitelist()
def get_assets_for_depreciation(filters):
    """Get list of assets eligible for depreciation based on filters"""
    
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    company = filters.get("company")
    period_start_date = filters.get("period_start_date")
    period_end_date = filters.get("period_end_date")
    asset_category = filters.get("asset_category")
    location = filters.get("location")
    department = filters.get("department")
    cost_center = filters.get("cost_center")
    finance_book = filters.get("finance_book")
    
    if not company or not period_start_date or not period_end_date:
        frappe.throw(_("Company, Period Start Date and Period End Date are required"))
    
    # Build query conditions
    conditions = []
    conditions.append("asset.docstatus = 1")
    conditions.append("asset.company = %(company)s")
    conditions.append("asset.status IN ('Submitted', 'Partially Depreciated')")
    conditions.append("asset.enable_depreciation = 1")
    conditions.append("asset.purchase_date <= %(period_end_date)s")
    
    if asset_category:
        conditions.append("asset.asset_category = %(asset_category)s")
    
    if location:
        conditions.append("asset.location = %(location)s")
    
    if department:
        conditions.append("asset.department = %(department)s")
    
    if cost_center:
        conditions.append("asset.cost_center = %(cost_center)s")
    
    # Get assets with pending depreciation schedules
    query = """
        SELECT DISTINCT
            asset.name as asset,
            asset.asset_name,
            asset.asset_category,
            asset.location,
            asset.cost_center,
            asset.gross_purchase_amount,
            asset.accumulated_depreciation,
            asset.current_value,
            schedule.schedule_date,
            schedule.depreciation_amount,
            schedule.accumulated_depreciation_amount,
            schedule.asset_book_value,
            category.depreciation_expense_account as depreciation_account,
            category.accumulated_depreciation_account,
            asset.cost_center
        FROM
            `tabFixed Asset` as asset
        LEFT JOIN
            `tabFixed Asset Depreciation Schedule` as schedule
            ON schedule.parent = asset.name
        LEFT JOIN
            `tabFixed Asset Category` as category
            ON category.name = asset.asset_category
        WHERE
            {conditions}
            AND schedule.schedule_date >= %(period_start_date)s
            AND schedule.schedule_date <= %(period_end_date)s
            AND schedule.depreciation_posted = 0
        ORDER BY
            asset.name, schedule.schedule_date
    """.format(conditions=" AND ".join(conditions))
    
    assets = frappe.db.sql(query, {
        "company": company,
        "period_start_date": period_start_date,
        "period_end_date": period_end_date,
        "asset_category": asset_category,
        "location": location,
        "department": department,
        "cost_center": cost_center
    }, as_dict=1)
    
    # Calculate before/after values
    for asset in assets:
        asset.accumulated_depreciation_before = flt(asset.accumulated_depreciation)
        asset.accumulated_depreciation_after = flt(asset.accumulated_depreciation) + flt(asset.depreciation_amount)
        
        asset.book_value_before = flt(asset.current_value)
        asset.book_value_after = flt(asset.current_value) - flt(asset.depreciation_amount)
    
    return assets


@frappe.whitelist()
def preview_depreciation_entries(filters):
    """Preview depreciation entries before creating the document"""
    
    assets = get_assets_for_depreciation(filters)
    
    if not assets:
        frappe.msgprint(_("No assets found for depreciation in the selected period"))
        return []
    
    # Calculate summary
    summary = {
        "total_assets": len(assets),
        "total_depreciation": sum(flt(a.depreciation_amount) for a in assets),
        "total_accumulated": sum(flt(a.accumulated_depreciation_after) for a in assets)
    }
    
    return {
        "assets": assets,
        "summary": summary
    }


@frappe.whitelist()
def create_depreciation_entry(filters):
    """Create depreciation entry document from filters"""
    
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    assets = get_assets_for_depreciation(filters)
    
    if not assets:
        frappe.throw(_("No assets found for depreciation"))
    
    # Create new document
    doc = frappe.new_doc("Fixed Asset Depreciation Entry")
    doc.company = filters.get("company")
    doc.posting_date = filters.get("posting_date") or today()
    doc.period_start_date = filters.get("period_start_date")
    doc.period_end_date = filters.get("period_end_date")
    doc.finance_book = filters.get("finance_book")
    doc.asset_category = filters.get("asset_category")
    doc.location = filters.get("location")
    doc.department = filters.get("department")
    doc.cost_center = filters.get("cost_center")
    
    # Add depreciation entries
    for asset in assets:
        doc.append("depreciation_entries", {
            "asset": asset.asset,
            "asset_name": asset.asset_name,
            "asset_category": asset.asset_category,
            "schedule_date": asset.schedule_date,
            "depreciation_amount": asset.depreciation_amount,
            "accumulated_depreciation_before": asset.accumulated_depreciation_before,
            "accumulated_depreciation_after": asset.accumulated_depreciation_after,
            "book_value_before": asset.book_value_before,
            "book_value_after": asset.book_value_after,
            "depreciation_account": asset.depreciation_account,
            "accumulated_depreciation_account": asset.accumulated_depreciation_account,
            "cost_center": asset.cost_center
        })
    
    doc.insert()
    
    frappe.msgprint(_("Depreciation Entry {0} created with {1} assets").format(
        doc.name, len(assets)
    ), alert=True)
    
    return doc.name


@frappe.whitelist()
def get_depreciation_summary(company, period_start_date, period_end_date, asset_category=None):
    """Get depreciation summary for a period"""
    
    conditions = ["company = %(company)s"]
    
    if asset_category:
        conditions.append("asset_category = %(asset_category)s")
    
    query = """
        SELECT
            COUNT(DISTINCT name) as total_assets,
            SUM(accumulated_depreciation) as total_accumulated_depreciation,
            SUM(current_value) as total_current_value,
            SUM(gross_purchase_amount) as total_purchase_value
        FROM
            `tabFixed Asset`
        WHERE
            docstatus = 1
            AND enable_depreciation = 1
            AND {conditions}
    """.format(conditions=" AND ".join(conditions))
    
    summary = frappe.db.sql(query, {
        "company": company,
        "asset_category": asset_category
    }, as_dict=1)
    
    return summary[0] if summary else {}