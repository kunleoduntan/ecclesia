# -*- coding: utf-8 -*-
# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint, getdate, nowdate, add_days
import qrcode
import io
import base64

# Constants
PAYMENT_TOLERANCE = 0.01
DEFAULT_QR_VERSION = 1
DEFAULT_QR_BOX_SIZE = 10
DEFAULT_QR_BORDER = 4


class FixedAssetPurchase(Document):
    def validate(self):
        """Validate purchase document"""
        self.validate_purchase_type()
        self.validate_dates()
        self.validate_items()
        self.calculate_totals()
        self.validate_payment_terms()
    
    def before_submit(self):
        """Before submit validations"""
        if not self.asset_purchase_details:
            frappe.throw(_("Please add at least one asset"))
        
        if flt(self.grand_total) <= 0:
            frappe.throw(_("Grand Total must be greater than zero"))
        
        # Check if assets have been created
        if not self.assets_created:
            frappe.throw(_("Please create Fixed Assets first using the 'Create Assets' button before submitting"))
        
        # Validate based on purchase type
        if self.purchase_type == "Cash Purchase":
            if not self.bank_account:
                frappe.throw(_("Bank Account is required for Cash Purchase"))
            self.validate_bank_account()
        elif self.purchase_type == "Supplier Purchase":
            if not self.supplier:
                frappe.throw(_("Supplier is required for Supplier Purchase"))
            if not self.item_linked_code:
                frappe.throw(_("Item Linked Code is required for Supplier Purchase to create Purchase Invoice"))
    
    def on_submit(self):
        """On submit operations - Only create accounting entries"""
        try:
            # Assets already created via button, just create accounting entries
            self.create_accounting_entries()
            
            # Update payment status
            self.update_payment_status()
            
            # Update status
            self.status = "Submitted"
            self.db_set("status", "Submitted")
            
            # Commit only if everything succeeds
            frappe.db.commit()
            
        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(
                message=frappe.get_traceback(),
                title=f"Fixed Asset Purchase Submission Failed: {self.name}"
            )
            frappe.throw(_("Failed to submit document: {0}").format(str(e)))
    
    def on_cancel(self):
        """On cancel operations"""
        try:
            self.cancel_accounting_entries()
            self.cancel_assets()
            
            self.status = "Cancelled"
            self.db_set("status", "Cancelled")
            
            frappe.db.commit()
        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(
                message=frappe.get_traceback(),
                title=f"Fixed Asset Purchase Cancellation Failed: {self.name}"
            )
            frappe.throw(_("Failed to cancel document: {0}").format(str(e)))
    
    def validate_purchase_type(self):
        """Validate purchase type specific requirements"""
        if self.purchase_type == "Cash Purchase":
            if not self.bank_account:
                frappe.throw(_("Bank Account is required for Cash Purchase"))
        
        elif self.purchase_type == "Supplier Purchase":
            if not self.supplier:
                frappe.throw(_("Supplier is required for Supplier Purchase"))
            
            # Validate supplier is active
            if frappe.db.get_value("Supplier", self.supplier, "disabled") == 1:
                frappe.throw(_("Supplier {0} is disabled").format(self.supplier))
            
            # Get supplier account if not set
            if not self.supplier_account:
                self.supplier_account = self.get_default_supplier_account()
            
            # Validate item_linked_code if set
            if self.item_linked_code:
                if not frappe.db.exists("Item", self.item_linked_code):
                    frappe.throw(_("Item Linked Code '{0}' does not exist").format(self.item_linked_code))
    
    def validate_bank_account(self):
        """Validate that the selected account is actually a bank account"""
        if not self.bank_account:
            return
        
        account_type = frappe.db.get_value("Account", self.bank_account, "account_type")
        if account_type not in ["Bank", "Cash"]:
            frappe.throw(_("Account {0} is not a Bank or Cash account").format(self.bank_account))
    
    def validate_dates(self):
        """Validate dates"""
        if getdate(self.purchase_date) > getdate(nowdate()):
            frappe.throw(_("Purchase Date cannot be in the future"))
        
        if self.expected_delivery_date and getdate(self.expected_delivery_date) < getdate(self.purchase_date):
            frappe.throw(_("Expected Delivery Date cannot be before Purchase Date"))
    
    def validate_items(self):
        """Validate purchase items"""
        if not self.asset_purchase_details:
            return
        
        for idx, item in enumerate(self.asset_purchase_details, 1):
            if not item.asset_category:
                frappe.throw(_("Row {0}: Asset Category is required").format(idx))
            
            if not frappe.db.exists("Fixed Asset Category", item.asset_category):
                frappe.throw(_("Row {0}: Invalid Asset Category").format(idx))
            
            if flt(item.qty) <= 0:
                frappe.throw(_("Row {0}: Quantity must be greater than 0").format(idx))
            
            if flt(item.rate) <= 0:
                frappe.throw(_("Row {0}: Rate must be greater than 0").format(idx))
            
            # Validate cost center if specified
            if item.cost_center and not self.is_cost_center_active(item.cost_center):
                frappe.throw(_("Row {0}: Cost Center {1} is disabled").format(idx, item.cost_center))
    
    def is_cost_center_active(self, cost_center):
        """Check if cost center is active"""
        return frappe.db.get_value("Cost Center", cost_center, "disabled") == 0
    
    def calculate_totals(self):
        """Calculate document totals"""
        self.total_qty = 0
        self.total = 0
        self.total_taxes_and_charges = 0
        self.total_additional_costs = 0
        
        # Calculate items total
        for item in self.asset_purchase_details:
            item.amount = flt(item.qty) * flt(item.rate)
            self.total += flt(item.amount)
            self.total_qty += flt(item.qty)
        
        # Calculate additional costs
        if self.additional_costs:
            for cost in self.additional_costs:
                self.total_additional_costs += flt(cost.amount)
        
        # Calculate taxes
        if self.taxes_and_charges_table:
            for tax in self.taxes_and_charges_table:
                if tax.charge_type == "On Net Total":
                    tax.tax_amount = flt(self.total) * flt(tax.rate) / 100
                elif tax.charge_type == "Actual":
                    tax.tax_amount = flt(tax.tax_amount)
                
                self.total_taxes_and_charges += flt(tax.tax_amount)
        
        # Calculate grand total
        self.grand_total = flt(self.total) + flt(self.total_additional_costs) + flt(self.total_taxes_and_charges)
        
        # Calculate outstanding amount
        self.calculate_outstanding()
    
    def calculate_outstanding(self):
        """Calculate outstanding amount"""
        total_paid = 0
        
        if self.payment_schedule:
            for payment in self.payment_schedule:
                if payment.payment_status == "Paid":
                    total_paid += flt(payment.payment_amount)
        
        self.total_paid = total_paid
        self.outstanding_amount = flt(self.grand_total) - flt(total_paid)
    
    def validate_payment_terms(self):
        """Validate payment terms"""
        if not self.payment_schedule:
            return
        
        total_payment = sum(flt(d.payment_amount) for d in self.payment_schedule)
        
        if abs(total_payment - flt(self.grand_total)) > PAYMENT_TOLERANCE:
            frappe.throw(_("Total Payment Amount ({0}) does not match Grand Total ({1})").format(
                total_payment, self.grand_total))
    
    def update_payment_status(self):
        """Update payment status based on payments"""
        if self.purchase_type == "Cash Purchase" and self.journal_entry:
            self.payment_status = "Paid"
            self.total_paid = flt(self.grand_total)
            self.outstanding_amount = 0
        elif flt(self.outstanding_amount) <= PAYMENT_TOLERANCE:
            self.payment_status = "Paid"
        elif flt(self.total_paid) > PAYMENT_TOLERANCE:
            self.payment_status = "Partially Paid"
        else:
            self.payment_status = "Unpaid"
        
        self.db_set("payment_status", self.payment_status)
        self.db_set("total_paid", self.total_paid)
        self.db_set("outstanding_amount", self.outstanding_amount)
    
    def get_default_supplier_account(self):
        """Get supplier's payable account"""
        if not self.supplier or not self.company:
            return None
        
        account = frappe.db.get_value(
            "Party Account",
            {"parenttype": "Supplier", "parent": self.supplier, "company": self.company},
            "account"
        )
        
        if not account:
            account = frappe.get_cached_value("Company", self.company, "default_payable_account")
        
        return account
    
    def cancel_assets(self):
        """Cancel created assets"""
        assets = frappe.get_all(
            "Fixed Asset",
            filters={
                "purchase_document": self.name,
                "docstatus": ["!=", 2]
            }
        )
        
        cancelled_count = 0
        deleted_count = 0
        
        for asset in assets:
            asset_doc = frappe.get_doc("Fixed Asset", asset.name)
            
            try:
                if asset_doc.docstatus == 1:
                    asset_doc.flags.ignore_permissions = True
                    asset_doc.cancel()
                    cancelled_count += 1
                else:
                    asset_doc.flags.ignore_permissions = True
                    asset_doc.delete()
                    deleted_count += 1
            except Exception as e:
                frappe.log_error(
                    message=frappe.get_traceback(),
                    title=f"Asset Cancellation Failed for {asset.name}"
                )
        
        self.db_set("assets_created", 0)
        
        if cancelled_count > 0 or deleted_count > 0:
            frappe.msgprint(
                _("Cancelled {0} and deleted {1} asset(s)").format(cancelled_count, deleted_count),
                alert=True
            )
    
    def create_accounting_entries(self):
        """Create accounting entries based on purchase type"""
        if not self.create_gl_entry:
            return
        
        if self.purchase_type == "Cash Purchase":
            self.create_journal_entry()
        elif self.purchase_type == "Supplier Purchase":
            self.create_purchase_invoice()
    
    def get_asset_account_for_category(self, category):
        """Get the appropriate asset account for a category"""
        category_doc = frappe.get_doc("Fixed Asset Category", category)
        account = category_doc.capital_work_in_progress_account or category_doc.fixed_asset_account
        
        if not account:
            frappe.throw(_("Asset Account not set for category {0}").format(category))
        
        return account
    
    def create_journal_entry(self):
        """Create journal entry for cash purchase"""
        if self.journal_entry:
            return
        
        je = frappe.new_doc("Journal Entry")
        je.voucher_type = "Journal Entry"
        je.company = self.company
        je.posting_date = self.posting_date
        je.cheque_no = self.payment_reference or ""
        je.cheque_date = self.posting_date
        je.user_remark = _("Fixed Asset Cash Purchase - {0}").format(self.name)
        
        # Get asset category wise totals
        category_totals = {}
        for item in self.asset_purchase_details:
            if item.asset_category not in category_totals:
                category_totals[item.asset_category] = 0
            category_totals[item.asset_category] += flt(item.amount)
        
        # Handle rounding differences
        allocated_total = sum(category_totals.values())
        rounding_difference = flt(self.total) - allocated_total
        if abs(rounding_difference) > PAYMENT_TOLERANCE:
            first_category = list(category_totals.keys())[0]
            category_totals[first_category] += rounding_difference
        
        # Debit: Asset/CWIP Accounts (by category)
        for category, amount in category_totals.items():
            account = self.get_asset_account_for_category(category)
            
            je.append("accounts", {
                "account": account,
                "debit_in_account_currency": amount,
                "credit_in_account_currency": 0,
                "cost_center": self.cost_center,
                "reference_type": "Fixed Asset Purchase",
                "reference_name": self.name
            })
        
        # Debit: Additional Costs
        if flt(self.total_additional_costs) > PAYMENT_TOLERANCE:
            first_category = list(category_totals.keys())[0]
            additional_cost_account = self.get_asset_account_for_category(first_category)
            
            je.append("accounts", {
                "account": additional_cost_account,
                "debit_in_account_currency": self.total_additional_costs,
                "credit_in_account_currency": 0,
                "cost_center": self.cost_center,
                "reference_type": "Fixed Asset Purchase",
                "reference_name": self.name
            })
        
        # Debit: Taxes
        if flt(self.total_taxes_and_charges) > PAYMENT_TOLERANCE:
            first_category = list(category_totals.keys())[0]
            tax_account = self.get_asset_account_for_category(first_category)
            
            je.append("accounts", {
                "account": tax_account,
                "debit_in_account_currency": self.total_taxes_and_charges,
                "credit_in_account_currency": 0,
                "cost_center": self.cost_center,
                "reference_type": "Fixed Asset Purchase",
                "reference_name": self.name
            })
        
        # Credit: Bank Account
        je.append("accounts", {
            "account": self.bank_account,
            "debit_in_account_currency": 0,
            "credit_in_account_currency": self.grand_total,
            "cost_center": self.cost_center,
            "reference_type": "Fixed Asset Purchase",
            "reference_name": self.name
        })
        
        try:
            je.flags.ignore_permissions = True
            je.insert()
            je.submit()
            
            self.db_set("journal_entry", je.name)
            
            frappe.msgprint(_("Journal Entry {0} created").format(
                frappe.utils.get_link_to_form("Journal Entry", je.name)
            ), alert=True)
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Journal Entry Creation Failed")
            frappe.throw(_("Failed to create Journal Entry: {0}").format(str(e)))
    
    def create_purchase_invoice(self):
        """Create purchase invoice for supplier purchase using item_linked_code"""
        if self.purchase_invoice:
            return
        
        # Use the item_linked_code field for the placeholder item
        if not self.item_linked_code:
            frappe.throw(_("Item Linked Code is required to create Purchase Invoice"))
        
        # Validate that the item exists
        if not frappe.db.exists("Item", self.item_linked_code):
            frappe.throw(_("Item '{0}' does not exist").format(self.item_linked_code))
        
        pi = frappe.new_doc("Purchase Invoice")
        pi.company = self.company
        pi.supplier = self.supplier
        pi.posting_date = self.posting_date
        pi.bill_no = self.supplier_invoice_number or ""
        pi.bill_date = self.supplier_invoice_date or self.posting_date
        pi.cost_center = self.cost_center
        pi.update_stock = 0
        
        if hasattr(self, 'project') and self.project:
            pi.project = self.project
        
        # Add items using the item_linked_code
        for item in self.asset_purchase_details:
            expense_account = self.get_asset_account_for_category(item.asset_category)
            
            # Build comprehensive description
            description_parts = [
                f"<b>Asset:</b> {item.asset_name or item.description}",
                f"<b>Category:</b> {item.asset_category}"
            ]
            
            if hasattr(item, 'serial_number') and item.serial_number:
                description_parts.append(f"<b>Serial Number:</b> {item.serial_number}")
            if hasattr(item, 'manufacturer') and item.manufacturer:
                description_parts.append(f"<b>Manufacturer:</b> {item.manufacturer}")
            if hasattr(item, 'model_number') and item.model_number:
                description_parts.append(f"<b>Model:</b> {item.model_number}")
            if hasattr(item, 'location') and item.location:
                description_parts.append(f"<b>Location:</b> {item.location}")
            
            item_description = "<br>".join(description_parts)
            
            pi.append("items", {
                "item_code": self.item_linked_code,
                "item_name": item.asset_name or item.description,
                "description": item_description,
                "qty": item.qty,
                "uom": "Nos",
                "rate": item.rate,
                "amount": item.amount,
                "expense_account": expense_account,
                "cost_center": item.cost_center or self.cost_center,
                "is_fixed_asset": 0
            })
        
        # Add taxes
        if self.taxes_and_charges_table:
            for tax in self.taxes_and_charges_table:
                pi.append("taxes", {
                    "charge_type": tax.charge_type,
                    "account_head": tax.account_head,
                    "description": tax.description,
                    "rate": tax.rate,
                    "tax_amount": tax.tax_amount,
                    "cost_center": tax.cost_center or self.cost_center
                })
        
        # Set payment terms
        if hasattr(self, 'payment_type') and self.payment_type == "Immediate Payment":
            pi.is_paid = 1
            if hasattr(self, 'mode_of_payment') and self.mode_of_payment:
                pi.mode_of_payment = self.mode_of_payment
            if self.bank_account:
                pi.cash_bank_account = self.bank_account
        else:
            if hasattr(self, 'payment_terms_template') and self.payment_terms_template:
                pi.payment_terms_template = self.payment_terms_template
            if hasattr(self, 'credit_days') and self.credit_days:
                pi.due_date = add_days(self.posting_date, self.credit_days or 0)
        
        try:
            pi.flags.ignore_permissions = True
            pi.insert()
            pi.submit()
            
            self.db_set("purchase_invoice", pi.name)
            self.db_set("purchase_invoice_created", 1)
            
            self.update_assets_with_invoice(pi.name)
            
            frappe.msgprint(_("Purchase Invoice {0} created successfully").format(
                frappe.utils.get_link_to_form("Purchase Invoice", pi.name)
            ), alert=True, indicator="green")
            
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Purchase Invoice Creation Failed")
            frappe.throw(_("Failed to create Purchase Invoice: {0}").format(str(e)))
    
    def update_assets_with_invoice(self, purchase_invoice):
        """Update created assets with purchase invoice reference"""
        assets = frappe.get_all(
            "Fixed Asset",
            filters={"purchase_document": self.name}
        )
        
        for asset in assets:
            frappe.db.set_value("Fixed Asset", asset.name, {
                "purchase_document_type": "Purchase Invoice",
                "purchase_document": purchase_invoice
            }, update_modified=False)
    
    def cancel_accounting_entries(self):
        """Cancel accounting entries on document cancellation"""
        if self.journal_entry:
            try:
                je = frappe.get_doc("Journal Entry", self.journal_entry)
                if je.docstatus == 1:
                    je.flags.ignore_permissions = True
                    je.cancel()
                    frappe.msgprint(_("Journal Entry {0} cancelled").format(
                        frappe.utils.get_link_to_form("Journal Entry", self.journal_entry)
                    ), alert=True)
            except Exception as e:
                frappe.log_error(
                    message=frappe.get_traceback(),
                    title=f"Journal Entry Cancellation Failed: {self.journal_entry}"
                )
        
        if self.purchase_invoice:
            try:
                pi = frappe.get_doc("Purchase Invoice", self.purchase_invoice)
                if pi.docstatus == 1:
                    pi.flags.ignore_permissions = True
                    pi.cancel()
                    frappe.msgprint(_("Purchase Invoice {0} cancelled").format(
                        frappe.utils.get_link_to_form("Purchase Invoice", self.purchase_invoice)
                    ), alert=True)
            except Exception as e:
                frappe.log_error(
                    message=frappe.get_traceback(),
                    title=f"Purchase Invoice Cancellation Failed: {self.purchase_invoice}"
                )


# ============================================================================
# WHITELISTED METHODS FOR BUTTON CLICK
# ============================================================================

@frappe.whitelist()
def create_assets_from_purchase(purchase_name):
    """Create Fixed Assets from purchase - Called by button click"""
    
    doc = frappe.get_doc("Fixed Asset Purchase", purchase_name)
    
    # Validate document is in draft
    if doc.docstatus != 0:
        frappe.throw(_("Assets can only be created for draft documents"))
    
    # Check if already created
    if doc.assets_created:
        frappe.msgprint(_("Assets have already been created for this purchase"), indicator="orange")
        return {"success": False, "message": "Assets already created"}
    
    # Validate we have items
    if not doc.asset_purchase_details:
        frappe.throw(_("No asset purchase details found"))
    
    assets_created = []
    errors = []
    
    try:
        # Pre-load all categories
        categories = {}
        for item in doc.asset_purchase_details:
            if item.asset_category and item.asset_category not in categories:
                if not frappe.db.exists("Fixed Asset Category", item.asset_category):
                    frappe.throw(_("Asset Category '{0}' does not exist").format(item.asset_category))
                categories[item.asset_category] = frappe.get_doc("Fixed Asset Category", item.asset_category)
        
        # Process each line item
        for item_idx, item in enumerate(doc.asset_purchase_details, 1):
            try:
                qty = cint(item.qty)
                if qty <= 0:
                    errors.append(f"Row {item_idx}: Quantity must be greater than 0")
                    continue
                
                # Calculate unit cost
                base_unit_cost = flt(item.amount) / flt(qty)
                
                # Allocate additional costs and taxes proportionally
                proportional_add_costs = 0
                proportional_taxes = 0
                
                if flt(doc.total) > PAYMENT_TOLERANCE:
                    ratio = flt(item.amount) / flt(doc.total)
                    proportional_add_costs = ratio * flt(doc.total_additional_costs)
                    proportional_taxes = ratio * flt(doc.total_taxes_and_charges)
                
                unit_cost = base_unit_cost + (proportional_add_costs / flt(qty)) + (proportional_taxes / flt(qty))
                
                if unit_cost <= 0:
                    errors.append(f"Row {item_idx}: Calculated unit cost is zero")
                    continue
                
                # Get category settings
                category_doc = categories.get(item.asset_category)
                if not category_doc:
                    errors.append(f"Row {item_idx}: Category not found")
                    continue
                
                # Validate required category fields
                if not category_doc.get("fixed_asset_account"):
                    errors.append(f"Row {item_idx}: Fixed Asset Account not set in category")
                    continue
                
                # Create individual assets
                for i in range(qty):
                    try:
                        asset_name = item.asset_name or item.description or "Unnamed Asset"
                        if qty > 1:
                            asset_name = f"{asset_name} - {i + 1}"
                        
                        # MINIMAL ASSET CREATION - Only absolutely required fields
                        asset_dict = {
                            "doctype": "Fixed Asset",
                            "company": doc.company,
                            "asset_category": item.asset_category,
                            "asset_name": asset_name,
                            "purchase_date": doc.purchase_date,
                            "gross_purchase_amount": flt(unit_cost, 2),
                        }
                        
                        # Add cost center if available
                        if doc.cost_center:
                            asset_dict["cost_center"] = doc.cost_center
                        elif hasattr(item, 'cost_center') and item.cost_center:
                            asset_dict["cost_center"] = item.cost_center
                        
                        # Create asset
                        asset = frappe.get_doc(asset_dict)
                        asset.flags.ignore_permissions = True
                        asset.flags.ignore_mandatory = True
                        asset.flags.ignore_validate = True
                        asset.insert(ignore_permissions=True, ignore_mandatory=True)
                        
                        # Update with additional fields
                        update_dict = {
                            "available_for_use_date": doc.expected_delivery_date or doc.purchase_date,
                            "asset_account": category_doc.fixed_asset_account,
                            "purchase_document_type": "Fixed Asset Purchase",
                            "purchase_document": doc.name,
                        }
                        
                        # Add supplier for supplier purchases
                        if doc.purchase_type == "Supplier Purchase" and doc.supplier:
                            update_dict["supplier"] = doc.supplier
                        
                        # Add optional fields
                        if hasattr(item, 'description') and item.description:
                            update_dict["asset_description"] = item.description
                        if hasattr(item, 'department') and item.department:
                            update_dict["department"] = item.department
                        if hasattr(item, 'location') and item.location:
                            update_dict["current_location"] = item.location
                        if hasattr(item, 'manufacturer') and item.manufacturer:
                            update_dict["manufacturer"] = item.manufacturer
                        if hasattr(item, 'model_number') and item.model_number:
                            update_dict["model_number"] = item.model_number
                        if hasattr(item, 'serial_number') and item.serial_number:
                            update_dict["serial_number"] = item.serial_number
                        
                        # Add depreciation if enabled
                        if category_doc.get("enable_depreciation") == 1:
                            update_dict["calculate_depreciation"] = 1
                            update_dict["depreciation_method"] = category_doc.get("depreciation_method") or "Straight Line"
                            if category_doc.get("total_number_of_depreciations"):
                                update_dict["total_number_of_depreciations"] = category_doc.total_number_of_depreciations
                            if category_doc.get("frequency_of_depreciation"):
                                update_dict["depreciation_frequency"] = category_doc.frequency_of_depreciation
                            if category_doc.get("accumulated_depreciation_account"):
                                update_dict["accumulated_depreciation_account"] = category_doc.accumulated_depreciation_account
                            if category_doc.get("depreciation_expense_account"):
                                update_dict["depreciation_expense_account"] = category_doc.depreciation_expense_account
                        
                        # Update asset
                        frappe.db.set_value("Fixed Asset", asset.name, update_dict, update_modified=False)
                        frappe.db.commit()
                        
                        assets_created.append(asset.name)
                        
                    except Exception as e:
                        error_msg = f"Row {item_idx}, Unit {i+1}: {str(e)}"
                        errors.append(error_msg)
                        frappe.log_error(
                            message=f"{error_msg}\n\n{frappe.get_traceback()}",
                            title=f"Asset Creation Failed"
                        )
                        
            except Exception as e:
                error_msg = f"Row {item_idx}: {str(e)}"
                errors.append(error_msg)
                frappe.log_error(
                    message=f"{error_msg}\n\n{frappe.get_traceback()}",
                    title=f"Row Processing Failed"
                )
        
        # Update document status
        if assets_created:
            frappe.db.set_value("Fixed Asset Purchase", purchase_name, "assets_created", 1, update_modified=False)
            frappe.db.commit()
            
            # Build success message
            msg_lines = [f"✅ <b>Successfully created {len(assets_created)} Fixed Asset(s)</b>", ""]
            
            # Show assets
            for asset_name in assets_created[:10]:
                msg_lines.append(frappe.utils.get_link_to_form("Fixed Asset", asset_name))
            
            if len(assets_created) > 10:
                msg_lines.append(f"... and {len(assets_created) - 10} more")
            
            # Add errors if any
            if errors:
                msg_lines.extend(["", f"<b>⚠️ Warnings ({len(errors)}):</b>"])
                for err in errors[:5]:
                    msg_lines.append(f"• {err}")
                if len(errors) > 5:
                    msg_lines.append(f"... and {len(errors) - 5} more (check Error Log)")
            
            message = "<br>".join(msg_lines)
            
            return {
                "success": True,
                "assets_created": len(assets_created),
                "errors": errors,
                "message": message,
                "assets": assets_created
            }
            
        else:
            error_summary = "<br>".join([f"• {e}" for e in errors[:10]])
            if len(errors) > 10:
                error_summary += f"<br>... and {len(errors) - 10} more errors"
            
            return {
                "success": False,
                "message": f"<b>❌ Asset creation failed</b><br><br>{error_summary}",
                "errors": errors
            }
            
    except Exception as e:
        frappe.log_error(
            message=frappe.get_traceback(),
            title=f"Asset Creation Failed for {purchase_name}"
        )
        return {
            "success": False,
            "message": f"Failed to create assets: {str(e)}",
            "errors": [str(e)]
        }


@frappe.whitelist()
def get_payment_schedule(doc):
    """Generate payment schedule based on payment terms"""
    import json
    if isinstance(doc, str):
        doc = json.loads(doc)
    
    doc = frappe._dict(doc)
    
    if not doc.payment_terms_template:
        return []
    
    payment_terms = frappe.get_doc("Payment Terms Template", doc.payment_terms_template)
    
    schedule = []
    grand_total = flt(doc.grand_total)
    
    for term in payment_terms.terms:
        payment_amount = grand_total * flt(term.payment_amount) / 100
        due_date = add_days(doc.purchase_date, cint(term.credit_days))
        
        schedule.append({
            "payment_term": term.payment_term,
            "due_date": due_date,
            "payment_amount": payment_amount,
            "payment_status": "Unpaid"
        })
    
    return schedule


@frappe.whitelist()
def get_supplier_account(supplier, company):
    """Get default payable account for supplier"""
    if not supplier or not company:
        return None
    
    account = frappe.db.get_value(
        "Party Account",
        {"parenttype": "Supplier", "parent": supplier, "company": company},
        "account"
    )
    
    if not account:
        account = frappe.get_cached_value("Company", company, "default_payable_account")
    
    return account


@frappe.whitelist()
def get_category_defaults(category):
    """Get default settings from asset category"""
    if not category:
        return {}
    
    if not frappe.db.exists("Fixed Asset Category", category):
        return {}
    
    category_doc = frappe.get_doc("Fixed Asset Category", category)
    
    return {
        "fixed_asset_account": category_doc.fixed_asset_account,
        "accumulated_depreciation_account": category_doc.accumulated_depreciation_account,
        "depreciation_expense_account": category_doc.depreciation_expense_account,
        "capital_work_in_progress_account": category_doc.capital_work_in_progress_account,
        "total_number_of_depreciations": category_doc.total_number_of_depreciations,
        "frequency_of_depreciation": category_doc.frequency_of_depreciation,
        "depreciation_method": category_doc.depreciation_method,
        "enable_depreciation": category_doc.enable_depreciation
    }