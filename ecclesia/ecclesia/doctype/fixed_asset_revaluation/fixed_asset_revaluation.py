# Copyright (c) 2026, 	kunle Oduntan and contributors
# For license information, please see license.txt

# -*- coding: utf-8 -*-
# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint, getdate, nowdate, add_days


class FixedAssetRevaluation(Document):
    def validate(self):
        """Validate revaluation document"""
        self.validate_asset()
        self.validate_dates()
        self.validate_revaluation_method()
        self.calculate_current_net_book_value()
        self.calculate_revaluation_amount()
        self.determine_revaluation_type()
    
    def before_submit(self):
        """Before submit validations"""
        if not self.revaluation_date:
            frappe.throw(_("Revaluation Date is required"))
        
        if flt(self.revaluation_amount) == 0:
            frappe.throw(_("Revaluation Amount cannot be zero. Current and New values are the same."))
        
        if not self.reason_for_revaluation:
            frappe.throw(_("Reason for Revaluation is required"))
        
        if not self.revaluation_reserve_account:
            frappe.throw(_("Revaluation Reserve Account is required"))
    
    def on_submit(self):
        """On submit operations"""
        self.update_asset_value()
        self.create_revaluation_journal_entry()
        self.update_depreciation_schedule()
    
    def on_cancel(self):
        """On cancel operations"""
        self.revert_asset_value()
        self.cancel_journal_entry()
    
    def validate_asset(self):
        """Validate asset details"""
        if not self.asset:
            frappe.throw(_("Asset is required"))
        
        if not frappe.db.exists("Fixed Asset", self.asset):
            frappe.throw(_("Invalid Asset"))
        
        asset = frappe.get_doc("Fixed Asset", self.asset)
        
        if asset.docstatus != 1:
            frappe.throw(_("Asset must be submitted before revaluation"))
        
        if hasattr(asset, 'asset_status') and asset.asset_status in ["Disposed", "Sold", "Scrapped"]:
            frappe.throw(_("Cannot revalue a {0} asset").format(asset.asset_status))
        
        # Fetch asset details
        self.asset_name = asset.asset_name
        self.asset_code = asset.asset_code
        self.asset_category = asset.asset_category
        
        if hasattr(asset, 'current_location'):
            self.current_location = asset.current_location
        
        if hasattr(asset, 'department'):
            self.department = asset.department
    
    def validate_dates(self):
        """Validate dates"""
        if not self.revaluation_date:
            return
        
        if getdate(self.revaluation_date) > getdate(nowdate()):
            frappe.throw(_("Revaluation Date cannot be in the future"))
        
        asset = frappe.get_doc("Fixed Asset", self.asset)
        
        if hasattr(asset, 'purchase_date') and asset.purchase_date:
            if getdate(self.revaluation_date) < getdate(asset.purchase_date):
                frappe.throw(_("Revaluation Date cannot be before Purchase Date ({0})").format(
                    frappe.utils.formatdate(asset.purchase_date)))
        
        # Check for existing revaluations after this date
        existing = frappe.db.exists("Fixed Asset Revaluation", {
            "asset": self.asset,
            "revaluation_date": [">", self.revaluation_date],
            "docstatus": 1,
            "name": ["!=", self.name]
        })
        
        if existing:
            frappe.throw(_("Cannot create revaluation before existing revaluation date. Please cancel future revaluations first."))
    
    def validate_revaluation_method(self):
        """Validate revaluation method and basis"""
        if not self.revaluation_method:
            frappe.throw(_("Revaluation Method is required"))
        
        if self.revaluation_method in ["Market Value", "Professional Valuation"]:
            if not self.valuer_appraiser:
                frappe.msgprint(
                    _("Valuer/Appraiser name is recommended for {0} method").format(self.revaluation_method),
                    indicator="orange"
                )
        
        if self.revaluation_method == "Professional Valuation":
            if not self.valuation_report_reference:
                frappe.msgprint(_("Please attach valuation report for Professional Valuation"), indicator="orange")
    
    def calculate_current_net_book_value(self):
        """Calculate current net book value"""
        if self.current_gross_value and self.current_accumulated_depreciation:
            self.current_net_book_value = flt(self.current_gross_value) - flt(self.current_accumulated_depreciation)
    
    def calculate_revaluation_amount(self):
        """Calculate revaluation amount"""
        if not self.new_gross_value or not self.current_gross_value:
            return
        
        # Calculate revaluation amount
        self.revaluation_amount = flt(self.new_gross_value) - flt(self.current_gross_value)
        
        # Calculate percentage change
        if flt(self.current_gross_value) > 0:
            self.percentage_change = (flt(self.revaluation_amount) / flt(self.current_gross_value)) * 100
        else:
            self.percentage_change = 0
    
    def determine_revaluation_type(self):
        """Determine revaluation type based on amount"""
        if flt(self.revaluation_amount) > 0:
            self.revaluation_type = "Upward Revaluation"
        elif flt(self.revaluation_amount) < 0:
            self.revaluation_type = "Downward Revaluation"
        else:
            self.revaluation_type = "No Change"
    
    def update_asset_value(self):
        """Update asset with revalued amount"""
        asset = frappe.get_doc("Fixed Asset", self.asset)
        
        # Store old value for reference
        old_gross_value = asset.gross_purchase_amount
        
        # Update asset gross value
        asset.gross_purchase_amount = self.new_gross_value
        
        # Update total revaluation amount
        if hasattr(asset, 'total_revaluation_amount'):
            asset.total_revaluation_amount = flt(asset.total_revaluation_amount) + flt(self.revaluation_amount)
        
        # Recalculate current values
        asset.flags.ignore_permissions = True
        asset.save()
        
        frappe.msgprint(_("Asset gross value updated from {0} to {1}").format(
            frappe.utils.fmt_money(old_gross_value),
            frappe.utils.fmt_money(self.new_gross_value)
        ), indicator="green")
    
    def update_depreciation_schedule(self):
        """Adjust future depreciation schedule after revaluation"""
        asset = frappe.get_doc("Fixed Asset", self.asset)
        
        # Only adjust if asset has depreciation
        if not hasattr(asset, 'calculate_depreciation') or not asset.calculate_depreciation:
            return
        
        # Get pending depreciation schedules
        pending_schedules = frappe.db.sql("""
            SELECT name, schedule_date, depreciation_amount
            FROM `tabDepreciation Schedule`
            WHERE parent = %s
            AND docstatus < 2
            AND journal_entry IS NULL
            AND schedule_date > %s
            ORDER BY schedule_date
        """, (asset.name, self.revaluation_date), as_dict=1)
        
        if not pending_schedules:
            return
        
        # Calculate new depreciation amount
        remaining_value = flt(self.new_gross_value) - flt(asset.residual_value or 0)
        remaining_periods = len(pending_schedules)
        
        if remaining_periods > 0 and hasattr(asset, 'depreciation_method'):
            if asset.depreciation_method == "Straight Line":
                new_depreciation = remaining_value / remaining_periods
                
                # Update each schedule
                for schedule in pending_schedules:
                    frappe.db.set_value("Depreciation Schedule", 
                        schedule.name, 
                        "depreciation_amount", 
                        new_depreciation
                    )
                
                frappe.msgprint(_("Updated {0} future depreciation schedules").format(
                    len(pending_schedules)), indicator="blue")
    
    def revert_asset_value(self):
        """Revert asset value on cancellation"""
        asset = frappe.get_doc("Fixed Asset", self.asset)
        
        # Revert gross value
        asset.gross_purchase_amount = self.current_gross_value
        
        # Revert total revaluation amount
        if hasattr(asset, 'total_revaluation_amount'):
            asset.total_revaluation_amount = flt(asset.total_revaluation_amount) - flt(self.revaluation_amount)
        
        asset.flags.ignore_permissions = True
        asset.save()
        
        frappe.msgprint(_("Asset value reverted to {0}").format(
            frappe.utils.fmt_money(self.current_gross_value)), indicator="orange")
    
    def create_revaluation_journal_entry(self):
        """Create journal entry for revaluation"""
        if flt(self.revaluation_amount) == 0:
            return
        
        asset = frappe.get_doc("Fixed Asset", self.asset)
        category = frappe.get_doc("Fixed Asset Category", self.asset_category)
        
        if not hasattr(category, 'fixed_asset_account') or not category.fixed_asset_account:
            frappe.throw(_("Fixed Asset Account not set for category {0}").format(self.asset_category))
        
        # Get cost center
        cost_center = self.cost_center if hasattr(self, 'cost_center') else (
            asset.cost_center if hasattr(asset, 'cost_center') else None
        )
        
        # Create Journal Entry
        je = frappe.new_doc("Journal Entry")
        je.voucher_type = "Journal Entry"
        je.posting_date = self.revaluation_date
        je.company = self.company
        je.user_remark = f"Asset Revaluation - {self.asset_name} ({self.revaluation_type})"
        
        if self.revaluation_type == "Upward Revaluation":
            # Debit: Fixed Asset Account (Increase)
            je.append("accounts", {
                "account": category.fixed_asset_account,
                "debit_in_account_currency": abs(flt(self.revaluation_amount)),
                "reference_type": "Fixed Asset Revaluation",
                "reference_name": self.name,
                "cost_center": cost_center
            })
            
            # Credit: Revaluation Reserve (Gain)
            je.append("accounts", {
                "account": self.revaluation_reserve_account,
                "credit_in_account_currency": abs(flt(self.revaluation_amount)),
                "reference_type": "Fixed Asset Revaluation",
                "reference_name": self.name,
                "cost_center": cost_center
            })
        
        else:  # Downward Revaluation
            # Debit: Revaluation Surplus/Loss Account
            loss_account = self.revaluation_surplus_loss_account or self.revaluation_reserve_account
            
            je.append("accounts", {
                "account": loss_account,
                "debit_in_account_currency": abs(flt(self.revaluation_amount)),
                "reference_type": "Fixed Asset Revaluation",
                "reference_name": self.name,
                "cost_center": cost_center
            })
            
            # Credit: Fixed Asset Account (Decrease)
            je.append("accounts", {
                "account": category.fixed_asset_account,
                "credit_in_account_currency": abs(flt(self.revaluation_amount)),
                "reference_type": "Fixed Asset Revaluation",
                "reference_name": self.name,
                "cost_center": cost_center
            })
        
        try:
            je.flags.ignore_permissions = True
            je.insert()
            je.submit()
            
            self.db_set("journal_entry", je.name)
            
            frappe.msgprint(_("Journal Entry {0} created successfully").format(
                frappe.utils.get_link_to_form("Journal Entry", je.name)), indicator="green")
        except Exception as e:
            frappe.log_error(
                message=frappe.get_traceback(),
                title="Revaluation Journal Entry Creation Failed"
            )
            frappe.throw(_("Failed to create journal entry: {0}").format(str(e)))
    
    def cancel_journal_entry(self):
        """Cancel associated journal entry"""
        if self.journal_entry:
            try:
                je = frappe.get_doc("Journal Entry", self.journal_entry)
                if je.docstatus == 1:
                    je.flags.ignore_permissions = True
                    je.cancel()
                self.db_set("journal_entry", None)
                frappe.msgprint(_("Journal Entry {0} cancelled").format(je.name), indicator="orange")
            except Exception as e:
                frappe.log_error(
                    message=frappe.get_traceback(),
                    title=f"Journal Entry Cancellation Failed: {self.journal_entry}"
                )


# Whitelisted methods

@frappe.whitelist()
def get_asset_for_revaluation(asset):
    """Get asset details for revaluation"""
    if not asset:
        return {}
    
    if not frappe.db.exists("Fixed Asset", asset):
        frappe.throw(_("Asset not found"))
    
    asset_doc = frappe.get_doc("Fixed Asset", asset)
    
    if hasattr(asset_doc, 'asset_status') and asset_doc.asset_status in ["Disposed", "Sold", "Scrapped"]:
        frappe.throw(_("Cannot revalue a {0} asset").format(asset_doc.asset_status))
    
    # Get current accumulated depreciation
    accumulated_depreciation = 0
    if hasattr(asset_doc, 'finance_books') and asset_doc.finance_books:
        accumulated_depreciation = sum(flt(d.value_after_depreciation) for d in asset_doc.finance_books)
    
    return {
        "asset_name": asset_doc.asset_name,
        "asset_code": asset_doc.asset_code,
        "asset_category": asset_doc.asset_category,
        "current_gross_value": asset_doc.gross_purchase_amount,
        "current_accumulated_depreciation": accumulated_depreciation,
        "current_location": asset_doc.current_location if hasattr(asset_doc, 'current_location') else None,
        "department": asset_doc.department if hasattr(asset_doc, 'department') else None,
        "cost_center": asset_doc.cost_center if hasattr(asset_doc, 'cost_center') else None
    }


@frappe.whitelist()
def get_revaluation_history(asset):
    """Get revaluation history for an asset"""
    if not asset:
        return []
    
    history = frappe.get_all("Fixed Asset Revaluation",
        filters={
            "asset": asset,
            "docstatus": 1
        },
        fields=[
            "name", "revaluation_date", "revaluation_method",
            "current_gross_value", "new_gross_value", "revaluation_amount",
            "revaluation_type", "percentage_change", "valuer_appraiser"
        ],
        order_by="revaluation_date desc"
    )
    
    return history


@frappe.whitelist()
def get_revaluation_summary(company=None, from_date=None, to_date=None):
    """Get revaluation summary statistics"""
    filters = {"docstatus": 1}
    
    if company:
        filters["company"] = company
    
    if from_date:
        filters["revaluation_date"] = [">=", from_date]
    
    if to_date:
        if "revaluation_date" in filters:
            filters["revaluation_date"] = ["between", [from_date, to_date]]
        else:
            filters["revaluation_date"] = ["<=", to_date]
    
    # Get total revaluations
    total_revaluations = frappe.db.count("Fixed Asset Revaluation", filters)
    
    # Get upward vs downward
    upward = frappe.db.count("Fixed Asset Revaluation", {
        **filters,
        "revaluation_type": "Upward Revaluation"
    })
    
    downward = frappe.db.count("Fixed Asset Revaluation", {
        **filters,
        "revaluation_type": "Downward Revaluation"
    })
    
    # Get total revaluation amount
    total_amount = frappe.db.sql("""
        SELECT SUM(revaluation_amount) as total
        FROM `tabFixed Asset Revaluation`
        WHERE docstatus = 1
        {conditions}
    """.format(
        conditions=" AND company = %(company)s" if company else ""
    ), {"company": company}, as_dict=True)
    
    return {
        "total_revaluations": total_revaluations,
        "upward_revaluations": upward,
        "downward_revaluations": downward,
        "total_revaluation_amount": total_amount[0].total if total_amount else 0
    }