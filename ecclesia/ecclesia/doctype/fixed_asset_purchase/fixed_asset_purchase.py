# -*- coding: utf-8 -*-
# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint, getdate, nowdate, add_days

# Constants
PAYMENT_TOLERANCE = 0.01


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

        if not self.assets_created:
            frappe.throw(_("Please create Fixed Assets first using the 'Create Assets' button before submitting"))

        if self.purchase_type == "Cash Purchase":
            if not self.bank_account:
                frappe.throw(_("Bank Account is required for Cash Purchase"))
            if not self.cash_supplier:
                frappe.throw(_("Cash Supplier is required for Cash Purchase"))
            if not self.item_linked_code:
                frappe.throw(_("Item Linked Code is required for Cash Purchase to create Purchase Invoice"))
            self.validate_bank_account()
        elif self.purchase_type == "Supplier Purchase":
            if not self.supplier:
                frappe.throw(_("Supplier is required for Supplier Purchase"))
            if not self.item_linked_code:
                frappe.throw(_("Item Linked Code is required for Supplier Purchase to create Purchase Invoice"))

    def on_submit(self):
        """On submit operations - Only create accounting entries"""
        try:
            self.create_accounting_entries()
            self.update_payment_status()

            self.status = "Submitted"
            self.db_set("status", "Submitted")

            frappe.db.commit()

        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(
                message=frappe.get_traceback(),
                title=f"Fixed Asset Purchase Submission Failed: {self.name}"
            )
            frappe.throw(_("Failed to submit document: {0}").format(str(e)))

    def on_cancel(self):
        """
        On cancel operations.

        ORDER MATTERS:
        1. Cancel depreciation journals (they reference the assets)
        2. Unlink assets from the Purchase Invoice (so no link to a cancelled doc remains)
        3. Cancel / delete assets
        4. Cancel Journal Entry / Purchase Invoice
        """
        try:
            asset_names = self.get_linked_asset_names()

            self.cancel_depreciation_entries(asset_names)
            self.unlink_assets_from_invoice(asset_names)
            self.cancel_assets()
            self.cancel_accounting_entries()

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

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_purchase_type(self):
        """Validate purchase type specific requirements"""
        if self.purchase_type == "Cash Purchase":
            if not self.bank_account:
                frappe.throw(_("Bank Account is required for Cash Purchase"))

            if not self.cash_supplier:
                frappe.throw(_("Cash Supplier is required for Cash Purchase"))

            if frappe.db.get_value("Supplier", self.cash_supplier, "disabled") == 1:
                frappe.throw(_("Cash Supplier {0} is disabled").format(self.cash_supplier))

            if not self.supplier_account:
                self.supplier_account = self.get_default_supplier_account()

            if self.item_linked_code and not frappe.db.exists("Item", self.item_linked_code):
                frappe.throw(_("Item Linked Code '{0}' does not exist").format(self.item_linked_code))

        elif self.purchase_type == "Supplier Purchase":
            if not self.supplier:
                frappe.throw(_("Supplier is required for Supplier Purchase"))

            if frappe.db.get_value("Supplier", self.supplier, "disabled") == 1:
                frappe.throw(_("Supplier {0} is disabled").format(self.supplier))

            if not self.supplier_account:
                self.supplier_account = self.get_default_supplier_account()

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

            if item.cost_center and not self.is_cost_center_active(item.cost_center):
                frappe.throw(_("Row {0}: Cost Center {1} is disabled").format(idx, item.cost_center))

    def is_cost_center_active(self, cost_center):
        """Check if cost center is active"""
        return frappe.db.get_value("Cost Center", cost_center, "disabled") == 0

    # ------------------------------------------------------------------
    # Totals / payments
    # ------------------------------------------------------------------

    def calculate_totals(self):
        """Calculate document totals"""
        self.total_qty = 0
        self.total = 0
        self.total_taxes_and_charges = 0
        self.total_additional_costs = 0

        for item in self.asset_purchase_details:
            item.amount = flt(item.qty) * flt(item.rate)
            self.total += flt(item.amount)
            self.total_qty += flt(item.qty)

        if self.additional_costs:
            for cost in self.additional_costs:
                self.total_additional_costs += flt(cost.amount)

        if self.taxes_and_charges_table:
            for tax in self.taxes_and_charges_table:
                if tax.charge_type == "On Net Total":
                    tax.tax_amount = flt(self.total) * flt(tax.rate) / 100
                elif tax.charge_type == "Actual":
                    tax.tax_amount = flt(tax.tax_amount)

                self.total_taxes_and_charges += flt(tax.tax_amount)

        self.grand_total = flt(self.total) + flt(self.total_additional_costs) + flt(self.total_taxes_and_charges)

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
        if self.purchase_type == "Cash Purchase" and (self.payment_entry or self.journal_entry):
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

    def get_purchase_party(self):
        """Supplier the purchase is posted to: cash_supplier for cash purchases, supplier otherwise"""
        if self.purchase_type == "Cash Purchase":
            return self.cash_supplier
        return self.supplier

    def get_default_supplier_account(self):
        """Get payable account of the supplier the purchase is posted to"""
        party = self.get_purchase_party()
        if not party or not self.company:
            return None

        account = frappe.db.get_value(
            "Party Account",
            {"parenttype": "Supplier", "parent": party, "company": self.company},
            "account"
        )

        if not account:
            account = frappe.get_cached_value("Company", self.company, "default_payable_account")

        return account

    # ------------------------------------------------------------------
    # Cancellation helpers
    # ------------------------------------------------------------------

    def get_linked_asset_names(self):
        """All non-cancelled Fixed Assets tied to this purchase (directly or via its Purchase Invoice)"""
        purchase_docs = [self.name]
        if self.purchase_invoice:
            purchase_docs.append(self.purchase_invoice)

        return frappe.get_all(
            "Fixed Asset",
            filters={
                "purchase_document": ["in", purchase_docs],
                "docstatus": ["!=", 2]
            },
            pluck="name"
        )

    def cancel_depreciation_entries(self, asset_names):
        """
        Cancel every depreciation Journal Entry booked against the given assets.
        Finds them via (a) Journal Entry Account rows referencing the asset and
        (b) any journal_entry field on Fixed Asset child tables (depreciation schedule).
        Schedule links are cleared first so the asset doesn't block the JE cancel.
        """
        if not asset_names:
            return

        je_names = set()

        # (a) JEs that reference the asset directly
        for parent in frappe.get_all(
            "Journal Entry Account",
            filters={
                "reference_type": "Fixed Asset",
                "reference_name": ["in", asset_names],
                "docstatus": 1
            },
            pluck="parent"
        ):
            je_names.add(parent)

        # (b) JEs linked from child tables of Fixed Asset (e.g. depreciation schedule)
        asset_meta = frappe.get_meta("Fixed Asset")
        for table_field in asset_meta.get_table_fields():
            child_doctype = table_field.options
            if not frappe.get_meta(child_doctype).has_field("journal_entry"):
                continue

            rows = frappe.get_all(
                child_doctype,
                filters={
                    "parent": ["in", asset_names],
                    "parenttype": "Fixed Asset",
                    "journal_entry": ["is", "set"]
                },
                fields=["name", "journal_entry"]
            )
            for row in rows:
                je_names.add(row.journal_entry)
                frappe.db.set_value(
                    child_doctype, row.name, "journal_entry", None, update_modified=False
                )

        # Never touch the purchase JE here - cancel_accounting_entries handles that
        je_names.discard(self.journal_entry)

        cancelled = 0
        for je_name in je_names:
            if not je_name or not frappe.db.exists("Journal Entry", je_name):
                continue

            je = frappe.get_doc("Journal Entry", je_name)
            if je.docstatus != 1:
                continue

            je.flags.ignore_permissions = True
            je.flags.ignore_links = True
            je.cancel()
            cancelled += 1

        if cancelled:
            frappe.msgprint(
                _("Cancelled {0} depreciation journal(s)").format(cancelled),
                alert=True
            )

    def unlink_assets_from_invoice(self, asset_names):
        """Point assets back to this document so no asset links to a Purchase Invoice about to be cancelled"""
        for asset_name in asset_names:
            frappe.db.set_value("Fixed Asset", asset_name, {
                "purchase_document_type": "Fixed Asset Purchase",
                "purchase_document": self.name
            }, update_modified=False)

    def cancel_assets(self):
        """Cancel created assets. Throws if any asset cannot be cancelled."""
        assets = frappe.get_all(
            "Fixed Asset",
            filters={
                "purchase_document": self.name,
                "docstatus": ["!=", 2]
            },
            pluck="name"
        )

        cancelled_count = 0
        deleted_count = 0
        failed = []

        for asset_name in assets:
            asset_doc = frappe.get_doc("Fixed Asset", asset_name)

            try:
                asset_doc.flags.ignore_permissions = True
                asset_doc.flags.ignore_links = True

                if asset_doc.docstatus == 1:
                    asset_doc.cancel()
                    cancelled_count += 1
                else:
                    asset_doc.delete()
                    deleted_count += 1
            except Exception as e:
                failed.append(f"{asset_name}: {str(e)}")
                frappe.log_error(
                    message=frappe.get_traceback(),
                    title=f"Asset Cancellation Failed for {asset_name}"
                )

        if failed:
            frappe.throw(
                _("Could not cancel the following assets:<br>{0}").format("<br>".join(failed))
            )

        self.db_set("assets_created", 0)

        if cancelled_count > 0 or deleted_count > 0:
            frappe.msgprint(
                _("Cancelled {0} and deleted {1} asset(s)").format(cancelled_count, deleted_count),
                alert=True
            )

    def cancel_accounting_entries(self):
        """Cancel accounting entries on document cancellation.

        Order: Payment Entry -> (legacy) Journal Entry -> Purchase Invoice,
        because the Payment Entry is allocated against the Purchase Invoice.
        """
        if self.payment_entry:
            pe = frappe.get_doc("Payment Entry", self.payment_entry)
            if pe.docstatus == 1:
                pe.flags.ignore_permissions = True
                pe.cancel()
                frappe.msgprint(_("Payment Entry {0} cancelled").format(
                    frappe.utils.get_link_to_form("Payment Entry", self.payment_entry)
                ), alert=True)

        # Legacy: cash purchases submitted before this change booked a Journal Entry
        if self.journal_entry:
            je = frappe.get_doc("Journal Entry", self.journal_entry)
            if je.docstatus == 1:
                je.flags.ignore_permissions = True
                je.cancel()
                frappe.msgprint(_("Journal Entry {0} cancelled").format(
                    frappe.utils.get_link_to_form("Journal Entry", self.journal_entry)
                ), alert=True)

        if self.purchase_invoice:
            pi = frappe.get_doc("Purchase Invoice", self.purchase_invoice)
            if pi.docstatus == 1:
                pi.flags.ignore_permissions = True
                pi.cancel()
                frappe.msgprint(_("Purchase Invoice {0} cancelled").format(
                    frappe.utils.get_link_to_form("Purchase Invoice", self.purchase_invoice)
                ), alert=True)

    # ------------------------------------------------------------------
    # Accounting entries
    # ------------------------------------------------------------------

    def create_accounting_entries(self):
        """Create accounting entries based on purchase type"""
        if not self.create_gl_entry:
            return

        # Both purchase types go through a Purchase Invoice.
        # Cash Purchase: invoice is posted to cash_supplier and settled
        # immediately by a Payment Entry from the bank/cash account.
        # No Journal Entry is created any more.
        self.create_purchase_invoice()

        if self.purchase_type == "Cash Purchase":
            self.create_payment_entry()

    def get_asset_account_for_category(self, category):
        """Get the appropriate asset account for a category"""
        category_doc = frappe.get_doc("Fixed Asset Category", category)
        account = category_doc.capital_work_in_progress_account or category_doc.fixed_asset_account

        if not account:
            frappe.throw(_("Asset Account not set for category {0}").format(category))

        return account

    def create_purchase_invoice(self):
        """Create purchase invoice for supplier purchase using item_linked_code"""
        if self.purchase_invoice:
            return

        if not self.item_linked_code:
            frappe.throw(_("Item Linked Code is required to create Purchase Invoice"))

        if not frappe.db.exists("Item", self.item_linked_code):
            frappe.throw(_("Item '{0}' does not exist").format(self.item_linked_code))

        pi = frappe.new_doc("Purchase Invoice")
        pi.company = self.company
        pi.supplier = self.get_purchase_party()
        pi.set_posting_time = 1
        pi.posting_date = self.posting_date
        pi.bill_no = self.supplier_invoice_number or ""
        if self.purchase_type == "Cash Purchase":
            pi.remarks = _("Fixed Asset Cash Purchase - {0}").format(self.name)
        pi.bill_date = self.supplier_invoice_date or self.posting_date
        pi.cost_center = self.cost_center
        pi.update_stock = 1

        if hasattr(self, 'project') and self.project:
            pi.project = self.project

        for item in self.asset_purchase_details:
            expense_account = self.get_asset_account_for_category(item.asset_category)

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

        if self.purchase_type == "Cash Purchase":
            # Paid via a separate Payment Entry (create_payment_entry), not is_paid
            pi.due_date = self.posting_date
        elif hasattr(self, 'payment_type') and self.payment_type == "Immediate Payment":
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

    def create_payment_entry(self):
        """Create + submit a Payment Entry (Pay) settling the cash purchase's Purchase Invoice.

        Mirrors Cash Purchase Sale: allocates against the invoice's own
        outstanding_amount (not self.grand_total) so any few-kobo rounding
        drift between the two cannot trigger "Allocated Amount cannot be
        greater than outstanding amount".
        """
        if self.payment_entry:
            return

        if not self.purchase_invoice:
            frappe.throw(_("Purchase Invoice must be created before the Payment Entry"))

        pi = frappe.get_doc("Purchase Invoice", self.purchase_invoice)
        allocate_amount = flt(pi.outstanding_amount)

        if allocate_amount <= 0:
            frappe.throw(_("Purchase Invoice {0} has no outstanding amount to pay").format(pi.name))

        pe = frappe.new_doc("Payment Entry")
        pe.payment_type = "Pay"
        pe.party_type = "Supplier"
        pe.party = self.cash_supplier
        pe.company = self.company
        pe.posting_date = self.posting_date
        pe.mode_of_payment = self.mode_of_payment
        pe.paid_from = self.bank_account
        pe.paid_to = pi.credit_to  # payable account the invoice was posted to
        pe.paid_amount = allocate_amount
        pe.received_amount = allocate_amount
        pe.source_exchange_rate = 1
        pe.target_exchange_rate = 1
        pe.reference_no = self.payment_reference or self.name
        pe.reference_date = self.posting_date
        pe.remarks = _("Fixed Asset Cash Purchase payment - {0}").format(self.name)

        if self.cost_center and frappe.get_meta("Payment Entry").has_field("cost_center"):
            pe.cost_center = self.cost_center
        if self.project and frappe.get_meta("Payment Entry").has_field("project"):
            pe.project = self.project

        pe.append("references", {
            "reference_doctype": "Purchase Invoice",
            "reference_name": pi.name,
            "allocated_amount": allocate_amount,
        })

        try:
            pe.flags.ignore_permissions = True
            pe.insert()
            pe.submit()

            self.db_set("payment_entry", pe.name)

            frappe.msgprint(_("Payment Entry {0} created").format(
                frappe.utils.get_link_to_form("Payment Entry", pe.name)
            ), alert=True, indicator="green")
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Payment Entry Creation Failed")
            frappe.throw(_("Failed to create Payment Entry: {0}").format(str(e)))

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


# ============================================================================
# WHITELISTED METHODS
# ============================================================================

@frappe.whitelist()
def unlink_cancelled_invoice_from_assets(purchase_name):
    """
    Repair tool: for assets still pointing at a cancelled Purchase Invoice
    ("Cannot link cancelled document: Purchase Document: PINV-xxxxx"),
    re-point them to this Fixed Asset Purchase. Safe to run on any document.
    """
    doc = frappe.get_doc("Fixed Asset Purchase", purchase_name)

    if not doc.purchase_invoice:
        return {"success": True, "unlinked": 0, "message": "No Purchase Invoice on this document"}

    assets = frappe.get_all(
        "Fixed Asset",
        filters={
            "purchase_document_type": "Purchase Invoice",
            "purchase_document": doc.purchase_invoice
        },
        pluck="name"
    )

    for asset_name in assets:
        frappe.db.set_value("Fixed Asset", asset_name, {
            "purchase_document_type": "Fixed Asset Purchase",
            "purchase_document": doc.name
        }, update_modified=False)

    frappe.db.commit()

    return {
        "success": True,
        "unlinked": len(assets),
        "assets": assets,
        "message": f"Unlinked {len(assets)} asset(s) from {doc.purchase_invoice}"
    }


@frappe.whitelist()
def create_assets_from_purchase(purchase_name):
    """Create Fixed Assets from purchase - Called by button click"""

    doc = frappe.get_doc("Fixed Asset Purchase", purchase_name)

    if doc.docstatus != 0:
        frappe.throw(_("Assets can only be created for draft documents"))

    if doc.assets_created:
        frappe.msgprint(_("Assets have already been created for this purchase"), indicator="orange")
        return {"success": False, "message": "Assets already created"}

    if not doc.asset_purchase_details:
        frappe.throw(_("No asset purchase details found"))

    assets_created = []
    errors = []

    try:
        categories = {}
        for item in doc.asset_purchase_details:
            if item.asset_category and item.asset_category not in categories:
                if not frappe.db.exists("Fixed Asset Category", item.asset_category):
                    frappe.throw(_("Asset Category '{0}' does not exist").format(item.asset_category))
                categories[item.asset_category] = frappe.get_doc("Fixed Asset Category", item.asset_category)

        for item_idx, item in enumerate(doc.asset_purchase_details, 1):
            try:
                qty = cint(item.qty)
                if qty <= 0:
                    errors.append(f"Row {item_idx}: Quantity must be greater than 0")
                    continue

                base_unit_cost = flt(item.amount) / flt(qty)

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

                category_doc = categories.get(item.asset_category)
                if not category_doc:
                    errors.append(f"Row {item_idx}: Category not found")
                    continue

                if not category_doc.get("fixed_asset_account"):
                    errors.append(f"Row {item_idx}: Fixed Asset Account not set in category")
                    continue

                for i in range(qty):
                    try:
                        asset_name = item.asset_name or item.description or "Unnamed Asset"
                        if qty > 1:
                            asset_name = f"{asset_name} - {i + 1}"

                        asset_dict = {
                            "doctype": "Fixed Asset",
                            "company": doc.company,
                            "asset_category": item.asset_category,
                            "asset_name": asset_name,
                            "purchase_date": doc.purchase_date,
                            "gross_purchase_amount": flt(unit_cost, 2),
                        }

                        if doc.cost_center:
                            asset_dict["cost_center"] = doc.cost_center
                        elif hasattr(item, 'cost_center') and item.cost_center:
                            asset_dict["cost_center"] = item.cost_center

                        asset = frappe.get_doc(asset_dict)
                        asset.flags.ignore_permissions = True
                        asset.flags.ignore_mandatory = True
                        asset.flags.ignore_validate = True
                        asset.insert(ignore_permissions=True, ignore_mandatory=True)

                        update_dict = {
                            "available_for_use_date": doc.expected_delivery_date or doc.purchase_date,
                            "asset_account": category_doc.fixed_asset_account,
                            "purchase_document_type": "Fixed Asset Purchase",
                            "purchase_document": doc.name,
                        }

                        if doc.purchase_type == "Supplier Purchase" and doc.supplier:
                            update_dict["supplier"] = doc.supplier
                        elif doc.purchase_type == "Cash Purchase" and doc.cash_supplier:
                            update_dict["supplier"] = doc.cash_supplier

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

                        frappe.db.set_value("Fixed Asset", asset.name, update_dict, update_modified=False)
                        frappe.db.commit()

                        assets_created.append(asset.name)

                    except Exception as e:
                        error_msg = f"Row {item_idx}, Unit {i+1}: {str(e)}"
                        errors.append(error_msg)
                        frappe.log_error(
                            message=f"{error_msg}\n\n{frappe.get_traceback()}",
                            title="Asset Creation Failed"
                        )

            except Exception as e:
                error_msg = f"Row {item_idx}: {str(e)}"
                errors.append(error_msg)
                frappe.log_error(
                    message=f"{error_msg}\n\n{frappe.get_traceback()}",
                    title="Row Processing Failed"
                )

        if assets_created:
            frappe.db.set_value("Fixed Asset Purchase", purchase_name, "assets_created", 1, update_modified=False)
            frappe.db.commit()

            msg_lines = [f"✅ <b>Successfully created {len(assets_created)} Fixed Asset(s)</b>", ""]

            for asset_name in assets_created[:10]:
                msg_lines.append(frappe.utils.get_link_to_form("Fixed Asset", asset_name))

            if len(assets_created) > 10:
                msg_lines.append(f"... and {len(assets_created) - 10} more")

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