# Copyright (c) 2026, 	kunle Oduntan and contributors
# For license information, please see license.txt

# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ecclesia and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate


class FixedAssetDisposal(Document):
    def validate(self):
        """Validate disposal document"""
        self.validate_asset()
        self.validate_dates()
        self.validate_disposal_details()
        self.calculate_gain_loss()
    
    def before_submit(self):
        """Before submit validations"""
        if not self.disposal_date:
            frappe.throw(_("Disposal Date is required"))
        
        if not self.disposal_type:
            frappe.throw(_("Disposal Type is required"))
    
    def on_submit(self):
        """On submit operations"""
        self.update_asset_status()
        self.make_disposal_gl_entries()
        self.create_disposal_journal_entry()
    
    def on_cancel(self):
        """On cancel operations"""
        self.revert_asset_status()
        self.cancel_journal_entry()
    
    def validate_asset(self):
        """Validate asset details"""
        if not self.asset:
            frappe.throw(_("Asset is required"))
        
        asset = frappe.get_doc("Fixed Asset", self.asset)
        
        if asset.status == "Disposed":
            frappe.throw(_("Asset {0} is already disposed").format(self.asset))
        
        if asset.docstatus != 1:
            frappe.throw(_("Asset {0} must be submitted before disposal").format(self.asset))
        
        # Fetch asset details
        self.asset_name = asset.asset_name
        self.asset_code = asset.asset_code
        self.asset_category = asset.asset_category
        self.purchase_date = asset.purchase_date
        self.gross_purchase_amount = asset.gross_purchase_amount
        self.current_book_value = asset.current_value
        
        # Get accumulated depreciation
        self.accumulated_depreciation = flt(asset.gross_purchase_amount) - flt(asset.current_value)
    
    def validate_dates(self):
        """Validate dates"""
        if not self.disposal_date:
            return
        
        if getdate(self.disposal_date) > getdate(nowdate()):
            frappe.throw(_("Disposal Date cannot be in the future"))
        
        asset = frappe.get_doc("Fixed Asset", self.asset)
        
        if getdate(self.disposal_date) < getdate(asset.purchase_date):
            frappe.throw(_("Disposal Date cannot be before Purchase Date"))
        
        if asset.available_for_use_date and getdate(self.disposal_date) < getdate(asset.available_for_use_date):
            frappe.throw(_("Disposal Date cannot be before Available for Use Date"))
    
    def validate_disposal_details(self):
        """Validate disposal details based on disposal type"""
        if self.disposal_type == "Sale":
            if not self.selling_price:
                frappe.throw(_("Selling Price is required for Sale disposal"))
            
            if not self.buyer:
                frappe.throw(_("Buyer is required for Sale disposal"))
        
        elif self.disposal_type == "Scrap":
            if flt(self.selling_price) > flt(self.current_book_value):
                frappe.throw(_("Scrap value cannot be greater than Current Book Value"))
        
        elif self.disposal_type == "Donation":
            if flt(self.selling_price) > 0:
                frappe.msgprint(_("Warning: Donation should typically have zero selling price"))
    
    def calculate_gain_loss(self):
        """Calculate gain or loss on disposal"""
        net_proceeds = flt(self.selling_price) - flt(self.disposal_expenses)
        self.net_disposal_proceeds = net_proceeds
        
        gain_loss = net_proceeds - flt(self.current_book_value)
        
        self.gain_loss_on_disposal = gain_loss
        
        if gain_loss > 0:
            self.gain_loss_type = "Gain"
        elif gain_loss < 0:
            self.gain_loss_type = "Loss"
        else:
            self.gain_loss_type = "No Gain/Loss"
    
    def update_asset_status(self):
        """Update asset with disposal information"""
        asset = frappe.get_doc("Fixed Asset", self.asset)
        
        asset.db_set("status", "Disposed")
        asset.db_set("disposal_date", self.disposal_date)
        asset.db_set("disposal_type", self.disposal_type)
        
        # Add disposal reference
        frappe.db.set_value("Fixed Asset", self.asset, {
            "status": "Disposed",
            "disposal_date": self.disposal_date,
            "disposal_type": self.disposal_type
        }, update_modified=True)
    
    def revert_asset_status(self):
        """Revert asset status on cancellation"""
        frappe.db.set_value("Fixed Asset", self.asset, {
            "status": "Active",
            "disposal_date": None,
            "disposal_type": None
        }, update_modified=True)
    
    def make_disposal_gl_entries(self):
        """Make GL entries for asset disposal"""
        if not self.create_journal_entry:
            return
        
        # Will be created via create_disposal_journal_entry
        pass
    
    def create_disposal_journal_entry(self):
        """Create journal entry for disposal"""
        if not self.create_journal_entry or self.journal_entry:
            return
        
        asset = frappe.get_doc("Fixed Asset", self.asset)
        category = frappe.get_doc("Fixed Asset Category", self.asset_category)
        
        # Create Journal Entry
        je = frappe.new_doc("Journal Entry")
        je.voucher_type = "Journal Entry"
        je.posting_date = self.disposal_date
        je.company = self.company
        je.user_remark = f"Asset Disposal - {self.asset_name} ({self.asset_code})"
        
        # 1. Debit: Accumulated Depreciation Account
        je.append("accounts", {
            "account": category.accumulated_depreciation_account,
            "debit_in_account_currency": flt(self.accumulated_depreciation),
            "reference_type": "Fixed Asset Disposal",
            "reference_name": self.name,
            "cost_center": self.cost_center or asset.cost_center
        })
        
        # 2. Credit: Fixed Asset Account
        je.append("accounts", {
            "account": category.fixed_asset_account,
            "credit_in_account_currency": flt(self.gross_purchase_amount),
            "reference_type": "Fixed Asset Disposal",
            "reference_name": self.name,
            "cost_center": self.cost_center or asset.cost_center
        })
        
        # 3. If there's proceeds from sale
        if flt(self.selling_price) > 0:
            # Debit: Cash/Bank or Debtor Account
            proceeds_account = self.proceeds_account or frappe.db.get_value("Company", self.company, "default_cash_account")
            
            je.append("accounts", {
                "account": proceeds_account,
                "debit_in_account_currency": flt(self.selling_price),
                "reference_type": "Fixed Asset Disposal",
                "reference_name": self.name,
                "cost_center": self.cost_center or asset.cost_center
            })
        
        # 4. If there are disposal expenses
        if flt(self.disposal_expenses) > 0:
            expense_account = self.disposal_expense_account or category.depreciation_expense_account
            
            je.append("accounts", {
                "account": expense_account,
                "debit_in_account_currency": flt(self.disposal_expenses),
                "reference_type": "Fixed Asset Disposal",
                "reference_name": self.name,
                "cost_center": self.cost_center or asset.cost_center
            })
        
        # 5. Gain or Loss on Disposal
        if flt(self.gain_loss_on_disposal) != 0:
            gain_loss_account = self.gain_loss_account
            
            if not gain_loss_account:
                frappe.throw(_("Please set Gain/Loss Account"))
            
            if self.gain_loss_type == "Gain":
                # Credit: Gain on Disposal
                je.append("accounts", {
                    "account": gain_loss_account,
                    "credit_in_account_currency": abs(flt(self.gain_loss_on_disposal)),
                    "reference_type": "Fixed Asset Disposal",
                    "reference_name": self.name,
                    "cost_center": self.cost_center or asset.cost_center
                })
            else:
                # Debit: Loss on Disposal
                je.append("accounts", {
                    "account": gain_loss_account,
                    "debit_in_account_currency": abs(flt(self.gain_loss_on_disposal)),
                    "reference_type": "Fixed Asset Disposal",
                    "reference_name": self.name,
                    "cost_center": self.cost_center or asset.cost_center
                })
        
        je.insert()
        je.submit()
        
        self.db_set("journal_entry", je.name)
        
        frappe.msgprint(_("Journal Entry {0} created successfully").format(
            frappe.utils.get_link_to_form("Journal Entry", je.name)))
    
    def cancel_journal_entry(self):
        """Cancel associated journal entry"""
        if self.journal_entry:
            je = frappe.get_doc("Journal Entry", self.journal_entry)
            if je.docstatus == 1:
                je.cancel()
            self.db_set("journal_entry", None)


@frappe.whitelist()
def get_asset_disposal_details(asset):
    """Get asset details for disposal"""
    if not asset:
        return {}
    
    asset_doc = frappe.get_doc("Fixed Asset", asset)
    
    if asset_doc.status == "Disposed":
        frappe.throw(_("Asset {0} is already disposed").format(asset))
    
    accumulated_depreciation = flt(asset_doc.gross_purchase_amount) - flt(asset_doc.current_value)
    
    return {
        "asset_name": asset_doc.asset_name,
        "asset_code": asset_doc.asset_code,
        "asset_category": asset_doc.asset_category,
        "purchase_date": asset_doc.purchase_date,
        "gross_purchase_amount": asset_doc.gross_purchase_amount,
        "current_book_value": asset_doc.current_value,
        "accumulated_depreciation": accumulated_depreciation,
        "cost_center": asset_doc.cost_center
    }