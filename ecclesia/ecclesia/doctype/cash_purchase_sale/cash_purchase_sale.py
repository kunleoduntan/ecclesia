# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

# -*- coding: utf-8 -*-
"""
Cash Purchase Sale DocType Controller

One document = one transaction_type ("Cash Purchase" or "Cash Sale").

Cash Purchase, on submit:
  1. Create + submit a Purchase Invoice against the Walk-in Supplier.
  2. If WHT/VAT applied: create + submit a Journal Entry booking the
     withheld amount as a LIABILITY (Debit Walk-in Supplier payable,
     Credit WHT/VAT Payable) — same treatment as the Payments doctype,
     since this is tax you owe to FIRS.
  3. Create + submit a Payment Entry (Pay) for the net amount, fully
     settling the Purchase Invoice.

Cash Sale, on submit:
  1. Create + submit a Sales Invoice against the Walk-in Customer.
  2. If WHT/VAT withheld by the customer: create + submit a Journal
     Entry booking the withheld amount as a RECOVERABLE ASSET (Debit
     WHT/VAT Recoverable, Credit Walk-in Customer receivable) — this is
     a tax credit note you'll later use to offset your own tax
     liability, not money you owe.
  3. Create + submit a Payment Entry (Receive) for the net amount,
     fully settling the Sales Invoice.

NOTE ON COMPANY FIELDS: this reuses default_wht_payable_account /
default_vat_payable_account from the Payments controller (Purchase
side), and additionally needs default_wht_recoverable_account /
default_vat_recoverable_account (Sales side) as custom fields on the
Company doctype. Create/confirm these fieldnames before going live.

NOTE ON PAYMENT AMOUNTS: the Payment Entry is allocated against the
invoice's own `outstanding_amount`, not the doc's stored
net_payable/net_receivable. Item rates carried in from migrated data
can have more decimal places than the currency precision the invoice
rounds to, so grand_total can differ from the stored total by a few
kobo — allocating against the stale stored value then throws
"Allocated Amount cannot be greater than outstanding amount". Reading
outstanding_amount straight off the submitted invoice avoids that
drift entirely.

Drop this in: <app>/<app>/doctype/cash_purchase_sale/cash_purchase_sale.py
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class CashPurchaseSale(Document):

    # ────────────────────────────────────────────────────────────
    # VALIDATE
    # ────────────────────────────────────────────────────────────

    def validate(self):
        if self.transaction_type == "Cash Purchase":
            if not self.purchase_items:
                frappe.throw(_("Please add at least one item under Items Purchased."))
        elif self.transaction_type == "Cash Sale":
            if not self.sales_items:
                frappe.throw(_("Please add at least one item under Items Sold."))

    # ────────────────────────────────────────────────────────────
    # ON SUBMIT
    # ────────────────────────────────────────────────────────────

    def on_submit(self):
        if self.transaction_type == "Cash Purchase":
            self._process_cash_purchase()
        elif self.transaction_type == "Cash Sale":
            self._process_cash_sale()

    def _process_cash_purchase(self):
        pi = self._create_purchase_invoice()
        self.db_set("purchase_invoice", pi.name, notify=False)

        tax_je = self._create_purchase_tax_je()
        if tax_je:
            self.db_set("purchase_tax_journal_entry", tax_je.name, notify=False)

        pe = self._create_purchase_payment_entry(pi)
        self.db_set("purchase_payment_entry", pe.name, notify=False)

        frappe.msgprint(
            _("Cash Purchase posted: Purchase Invoice {0}, Payment Entry {1}.").format(
                pi.name, pe.name
            )
        )

    def _process_cash_sale(self):
        si = self._create_sales_invoice()
        self.db_set("sales_invoice", si.name, notify=False)

        tax_je = self._create_sales_tax_je()
        if tax_je:
            self.db_set("sales_tax_journal_entry", tax_je.name, notify=False)

        pe = self._create_sales_payment_entry(si)
        self.db_set("sales_payment_entry", pe.name, notify=False)

        frappe.msgprint(
            _("Cash Sale posted: Sales Invoice {0}, Payment Entry {1}.").format(
                si.name, pe.name
            )
        )

    # ---------------- Purchase side ----------------

    def _create_purchase_invoice(self):
        pi = frappe.new_doc("Purchase Invoice")
        pi.supplier = self.walk_in_supplier
        pi.company = self.company
        pi.posting_date = self.transaction_date
        pi.set_posting_time = 1
        pi.update_stock = 1
        pi.remarks = _("Cash Purchase from {0} ({1}) — Voucher {2}").format(
            self.actual_supplier_name, self.actual_supplier_phone or "N/A", self.name
        )

        for row in self.purchase_items:
            pi.append("items", {
                "item_code": row.item_code,
                "qty": row.qty,
                "rate": row.rate,
                "uom": row.uom,
                "warehouse": self.purchase_warehouse,
            })

        pi.insert(ignore_permissions=True)
        pi.submit()
        pi.reload()
        return pi

    def _create_purchase_tax_je(self):
        if not (self.apply_withholding_tax_purchase or self.apply_vat_deduction_purchase):
            return None

        wht_amt = flt(self.wht_amount_purchase) if self.apply_withholding_tax_purchase else 0
        vat_amt = flt(self.vat_amount_purchase) if self.apply_vat_deduction_purchase else 0

        if not (wht_amt or vat_amt):
            return None

        default_payable = frappe.db.get_value("Company", self.company, "default_payable_account")
        wht_account = frappe.db.get_value("Company", self.company, "default_wht_payable_account")
        vat_account = frappe.db.get_value("Company", self.company, "default_vat_payable_account")

        if wht_amt and not wht_account:
            frappe.throw(_("Set the WHT Payable Account on Company {0}.").format(self.company))
        if vat_amt and not vat_account:
            frappe.throw(_("Set the VAT Payable Account on Company {0}.").format(self.company))

        je = frappe.new_doc("Journal Entry")
        je.voucher_type = "Journal Entry"
        je.company = self.company
        je.posting_date = self.transaction_date
        je.paid_to_or_received_from = self.actual_supplier_name
        je.user_remark = _("WHT/VAT withheld — Cash Purchase {0}").format(self.name)

        je.append("accounts", {
            "account": default_payable,
            "party_type": "Supplier",
            "party": self.walk_in_supplier,
            "debit_in_account_currency": wht_amt + vat_amt,
            "user_remark": "WHT/VAT withheld from cash purchase",
        })
        if wht_amt:
            je.append("accounts", {
                "account": wht_account,
                "credit_in_account_currency": wht_amt,
                "user_remark": "WHT withheld @ {0}%".format(self.wht_rate_purchase),
            })
        if vat_amt:
            je.append("accounts", {
                "account": vat_account,
                "credit_in_account_currency": vat_amt,
                "user_remark": "VAT withheld @ {0}%".format(self.vat_rate_purchase),
            })

        je.set_total_debit_credit()
        je.insert(ignore_permissions=True)
        je.submit()
        return je

    def _create_purchase_payment_entry(self, pi):
        # Use the invoice's own outstanding_amount rather than
        # self.net_payable: item rates carried in from migrated data
        # can have more decimals than currency precision, so the
        # invoice's rounded grand_total can differ by a few kobo from
        # the stored total. Allocating against a stale value throws
        # "Allocated Amount cannot be greater than outstanding amount".
        allocate_amount = flt(pi.outstanding_amount)

        if allocate_amount <= 0:
            frappe.throw(
                _("Purchase Invoice {0} has no outstanding amount to pay.").format(pi.name)
            )

        pe = frappe.new_doc("Payment Entry")
        pe.payment_type = "Pay"
        pe.party_type = "Supplier"
        pe.party = self.walk_in_supplier
        pe.company = self.company
        pe.posting_date = self.transaction_date
        pe.mode_of_payment = self.mode_of_payment_purchase
        pe.paid_from = self.cash_bank_account_purchase
        pe.paid_to = frappe.db.get_value("Company", self.company, "default_payable_account")
        pe.paid_amount = allocate_amount
        pe.received_amount = allocate_amount
        pe.source_exchange_rate = 1
        pe.target_exchange_rate = 1
        pe.reference_no = self.name
        pe.reference_date = self.transaction_date
        pe.remarks = _("Cash Purchase payment — Voucher {0}").format(self.name)

        pe.append("references", {
            "reference_doctype": "Purchase Invoice",
            "reference_name": pi.name,
            "allocated_amount": allocate_amount,
        })

        pe.insert(ignore_permissions=True)
        pe.submit()
        return pe

    # ---------------- Sales side ----------------

    def _create_sales_invoice(self):
        si = frappe.new_doc("Sales Invoice")
        si.customer = self.walk_in_customer
        si.company = self.company
        si.posting_date = self.transaction_date
        si.set_posting_time = 1
        si.update_stock = 1
        si.remarks = _("Cash Sale to {0} ({1}) — Voucher {2}").format(
            self.actual_customer_name, self.actual_customer_phone or "N/A", self.name
        )

        for row in self.sales_items:
            si.append("items", {
                "item_code": row.item_code,
                "qty": row.qty,
                "rate": row.rate,
                "uom": row.uom,
                "warehouse": self.sales_warehouse,
            })

        si.insert(ignore_permissions=True)
        si.submit()
        si.reload()
        return si

    def _create_sales_tax_je(self):
        if not (self.apply_withholding_tax_sales or self.apply_vat_deduction_sales):
            return None

        wht_amt = flt(self.wht_amount_sales) if self.apply_withholding_tax_sales else 0
        vat_amt = flt(self.vat_amount_sales) if self.apply_vat_deduction_sales else 0

        if not (wht_amt or vat_amt):
            return None

        default_receivable = frappe.db.get_value("Company", self.company, "default_receivable_account")
        wht_recoverable = frappe.db.get_value("Company", self.company, "default_wht_recoverable_account")
        vat_recoverable = frappe.db.get_value("Company", self.company, "default_vat_recoverable_account")

        if wht_amt and not wht_recoverable:
            frappe.throw(_("Set the WHT Recoverable Account on Company {0}.").format(self.company))
        if vat_amt and not vat_recoverable:
            frappe.throw(_("Set the VAT Recoverable Account on Company {0}.").format(self.company))

        je = frappe.new_doc("Journal Entry")
        je.voucher_type = "Journal Entry"
        je.company = self.company
        je.posting_date = self.transaction_date
        je.paid_to_or_received_from = self.actual_customer_name
        je.user_remark = _("WHT/VAT withheld by customer — Cash Sale {0}").format(self.name)

        if wht_amt:
            je.append("accounts", {
                "account": wht_recoverable,
                "debit_in_account_currency": wht_amt,
                "user_remark": "WHT withheld by customer @ {0}%".format(self.wht_rate_sales),
            })
        if vat_amt:
            je.append("accounts", {
                "account": vat_recoverable,
                "debit_in_account_currency": vat_amt,
                "user_remark": "VAT withheld by customer @ {0}%".format(self.vat_rate_sales),
            })
        je.append("accounts", {
            "account": default_receivable,
            "party_type": "Customer",
            "party": self.walk_in_customer,
            "credit_in_account_currency": wht_amt + vat_amt,
            "user_remark": "WHT/VAT withheld by customer from cash sale",
        })

        je.set_total_debit_credit()
        je.insert(ignore_permissions=True)
        je.submit()
        return je

    def _create_sales_payment_entry(self, si):
        # See note in _create_purchase_payment_entry: allocate against
        # the invoice's actual outstanding_amount, not self.net_receivable.
        allocate_amount = flt(si.outstanding_amount)

        if allocate_amount <= 0:
            frappe.throw(
                _("Sales Invoice {0} has no outstanding amount to receive.").format(si.name)
            )

        pe = frappe.new_doc("Payment Entry")
        pe.payment_type = "Receive"
        pe.party_type = "Customer"
        pe.party = self.walk_in_customer
        pe.company = self.company
        pe.posting_date = self.transaction_date
        pe.mode_of_payment = self.mode_of_payment_sales
        pe.paid_from = frappe.db.get_value("Company", self.company, "default_receivable_account")
        pe.paid_to = self.cash_bank_account_sales
        pe.paid_amount = allocate_amount
        pe.received_amount = allocate_amount
        pe.source_exchange_rate = 1
        pe.target_exchange_rate = 1
        pe.reference_no = self.name
        pe.reference_date = self.transaction_date
        pe.remarks = _("Cash Sale receipt — Voucher {0}").format(self.name)

        pe.append("references", {
            "reference_doctype": "Sales Invoice",
            "reference_name": si.name,
            "allocated_amount": allocate_amount,
        })

        pe.insert(ignore_permissions=True)
        pe.submit()
        return pe

    # ────────────────────────────────────────────────────────────
    # ON CANCEL
    # ────────────────────────────────────────────────────────────

    def on_cancel(self):
        # Cancel in reverse dependency order: Payment Entry first, then
        # the tax Journal Entry, then the Invoice.
        for fieldname, doctype in (
            ("purchase_payment_entry", "Payment Entry"),
            ("purchase_tax_journal_entry", "Journal Entry"),
            ("purchase_invoice", "Purchase Invoice"),
            ("sales_payment_entry", "Payment Entry"),
            ("sales_tax_journal_entry", "Journal Entry"),
            ("sales_invoice", "Sales Invoice"),
        ):
            docname = self.get(fieldname)
            if not docname:
                continue
            linked_doc = frappe.get_doc(doctype, docname)
            if linked_doc.docstatus == 1:
                linked_doc.cancel()

        frappe.msgprint(_("Linked Invoice, Payment Entry and Journal Entry (if any) have been cancelled."))