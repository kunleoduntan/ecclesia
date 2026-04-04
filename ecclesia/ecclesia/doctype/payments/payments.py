# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

"""
Payment Accounting Module
Handles all accounting entry creation for Payments DocType
Creates Journal Entries and Payment Entries based on transaction type

Best Practices Applied:
- Separation of concerns
- Defensive programming
- Efficient database queries
- Comprehensive error handling
- Detailed logging
- Transaction management
- Optimized performance
- Complete validation
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
    flt, getdate, nowdate, fmt_money, money_in_words,
    add_months, add_days, get_url
)
import json
from datetime import datetime, timedelta


# ==================== PaymentAccountingController Class ====================

class PaymentAccountingController:
    """Main controller for creating accounting entries with optimized performance"""

    def __init__(self, payment_doc):
        self.doc = payment_doc
        self.company = payment_doc.company
        self.company_currency = self._get_company_currency()
        self.is_local_currency = self.doc.payment_currency == self.company_currency
        self.created_entries = []

        # Cache frequently used values
        self._cache = {
            'payable_account': None,
            'interbank_account': None
        }

        frappe.logger().info(f"PaymentAccountingController initialized for {payment_doc.name}")

    def _get_company_currency(self):
        """Get company currency with caching"""
        return frappe.db.get_value('Company', self.company, 'default_currency', cache=True)

    def create_accounting_entries(self):
        """Main method to create accounting entries"""
        if not self.doc.create_accounting_entries:
            frappe.logger().info(f"Accounting entry creation disabled for {self.doc.name}")
            return []

        try:
            # Validate before creating entries
            self._validate_before_creation()

            # Create appropriate entries based on transaction type
            if self.doc.trans_type == "Supplier Payment":
                return self._create_supplier_payment_entries()

            elif self.doc.trans_type == "Expense Payment":
                return self._create_expense_payment_entries()

            elif self.doc.trans_type == "Transfer Out":
                return self._create_transfer_out_entries()

            elif self.doc.trans_type == "Supplier Refunds":
                return self._create_supplier_refund_entries()

            else:
                frappe.logger().warning(f"Unknown transaction type: {self.doc.trans_type}")

            return self.created_entries

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"Payment Accounting Error - {self.doc.name}")
            raise

    def _validate_before_creation(self):
        """Validate before creating accounting entries"""
        if self.doc.trans_type == "Expense Payment" and not self.doc.account_to_debit:
            frappe.throw(_("Account to Debit is required for Expense Payment"))

        if not self.doc.remittance_bank_gl:
            frappe.throw(_("Bank GL Account is required"))

        self._validate_account_not_group(self.doc.remittance_bank_gl)

        if self.doc.account_to_debit:
            self._validate_account_not_group(self.doc.account_to_debit)

        frappe.logger().info(f"Validation passed for {self.doc.name}")

    def _validate_account_not_group(self, account):
        """Ensure account is not a group account"""
        if not account:
            return

        is_group = frappe.db.get_value("Account", account, "is_group", cache=True)
        if is_group:
            frappe.throw(_("The account {0} is a group account and cannot be used for posting").format(account))

    # ==================== Supplier Payment Entries ====================

    def _create_supplier_payment_entries(self):
        """Create Payment Entry for supplier payments"""
        frappe.logger().info(f"Creating supplier payment entry for {self.doc.name}")

        try:
            pe = frappe.new_doc("Payment Entry")

            pe.payment_type = "Pay"
            pe.party_type = "Supplier"
            pe.party = self.doc.payee_id
            pe.company = self.doc.company
            pe.posting_date = self.doc.transaction_date
            pe.mode_of_payment = self.doc.mode_of_payment
            pe.reference_no = self.doc.reference_no
            pe.reference_date = self.doc.transaction_date

            pe.paid_from = self.doc.remittance_bank_gl
            pe.bank_account = self.doc.remittance_bank
            pe.paid_to = self._get_payable_account()

            self._set_payment_entry_amounts(pe)
            self._set_accounting_dimensions(pe)

            if self.doc.payments_reference:
                self._add_invoice_references_to_pe(pe)

            pe.remarks = self.doc.transaction_purposes or f"Payment to {self.doc.supplier_name}"

            pe.flags.ignore_permissions = True
            pe.insert(ignore_permissions=True)
            pe.submit()

            self.created_entries.append({
                'doctype': 'Payment Entry',
                'name': pe.name,
                'amount': pe.paid_amount
            })

            frappe.logger().info(f"Supplier Payment Entry {pe.name} created successfully")
            frappe.msgprint(_("Payment Entry {0} created").format(pe.name), indicator="green")

            return self.created_entries

        except Exception as e:
            frappe.logger().error(f"Error creating supplier payment entry: {str(e)}")
            frappe.log_error(frappe.get_traceback(), "Supplier Payment Creation Error")
            raise

    def _get_payable_account(self):
        """Get payable account with caching"""
        if not self._cache['payable_account']:
            self._cache['payable_account'] = frappe.db.get_value(
                'Company', self.company, 'default_payable_account', cache=True
            )
        return self._cache['payable_account']

    def _set_payment_entry_amounts(self, pe):
        """Set amounts in Payment Entry — all fields wrapped with flt() for safety"""
        amount_paid = flt(self.doc.amount_paid)
        amount_paid_in_fc = flt(self.doc.amount_paid_in_fc)
        exchange_rate = flt(self.doc.exchange_rate) or 1

        if self.is_local_currency:
            pe.paid_amount = amount_paid
            pe.received_amount = amount_paid
            pe.source_exchange_rate = 1
            pe.target_exchange_rate = 1
        else:
            pe.paid_from_account_currency = self.doc.bank_account_currency
            pe.paid_to_account_currency = self.doc.payment_currency
            pe.paid_amount = amount_paid_in_fc
            pe.base_paid_amount = amount_paid_in_fc * exchange_rate          # FIX: was raw field arithmetic
            pe.received_amount = amount_paid_in_fc
            pe.base_received_amount = amount_paid_in_fc * exchange_rate      # FIX: was raw field arithmetic
            pe.source_exchange_rate = exchange_rate
            pe.target_exchange_rate = exchange_rate

    def _add_invoice_references_to_pe(self, pe):
        """Add invoice references to Payment Entry"""
        for ref in self.doc.payments_reference:
            if flt(ref.allocated_amount) > 0:
                pe.append('references', {
                    'reference_doctype': ref.reference_doctype,
                    'reference_name': ref.reference_name,
                    'due_date': ref.due_date,
                    'total_amount': ref.total_amount,
                    'outstanding_amount': ref.outstanding_amount,
                    'allocated_amount': ref.allocated_amount,
                    'exchange_rate': flt(ref.exchange_rate) or 1
                })

    # ==================== Expense Payment Entries ====================

    def _create_expense_payment_entries(self):
        """Create Journal Entry for expense payments"""
        frappe.logger().info(f"Creating expense payment entry for {self.doc.name}")

        if self.doc.is_multi_line:
            return self._create_multi_line_expense_entry()

        elif self.doc.is_shared_cost:
            return self._create_shared_cost_entry()

        elif self.doc.is_related_coy_trans:
            return self._create_related_company_entries()

        elif self.doc.deduct_wht:
            return self._create_expense_entry_with_wht()

        else:
            return self._create_simple_expense_entry()

    def _create_simple_expense_entry(self):
        """Create simple expense payment journal entry"""
        frappe.logger().info(f"Creating simple expense entry for {self.doc.name}")

        try:
            je = self._initialize_journal_entry("Bank Entry")

            debit_amount = self._get_payment_amount_in_local_currency()
            credit_amount = self._get_payment_amount_for_bank()

            je.append("accounts", {
                "account": self.doc.account_to_debit,
                "debit_in_account_currency": debit_amount,
                "debit": debit_amount,
                "exchange_rate": 1 if self.is_local_currency else flt(self.doc.exchange_rate),
                "user_remark": self.doc.transaction_purposes,
                "cost_center": self.doc.cost_center,
                "project": self.doc.project,
                "against_account": self.doc.remittance_bank_gl
            })

            je.append("accounts", {
                "account": self.doc.remittance_bank_gl,
                "credit_in_account_currency": credit_amount,
                "credit": debit_amount,
                "exchange_rate": flt(self.doc.exchange_rate) if not self.is_local_currency else 1,
                "user_remark": self.doc.transaction_purposes,
                "bank_account": self.doc.remittance_bank,
                "against_account": self.doc.account_to_debit
            })

            return self._save_and_submit_journal_entry(je)

        except Exception as e:
            frappe.logger().error(f"Error creating simple expense entry: {str(e)}")
            frappe.log_error(frappe.get_traceback(), "Simple Expense Entry Error")
            raise

    def _create_expense_entry_with_wht(self):
        """Create expense payment with WHT deduction"""
        frappe.logger().info(f"Creating expense entry with WHT for {self.doc.name}")

        try:
            je = self._initialize_journal_entry("Bank Entry")

            base_amount = self._get_payment_amount_in_local_currency()
            wht_amount = flt(self.doc.wht_amount)
            net_amount = flt(self.doc.net_amount)
            exchange_rate = flt(self.doc.exchange_rate) or 1

            self._validate_account_not_group(self.doc.wht_account)

            # Debit: Expense Account (full amount)
            je.append("accounts", {
                "account": self.doc.account_to_debit,
                "debit_in_account_currency": base_amount,
                "debit": base_amount,
                "exchange_rate": 1,
                "user_remark": self.doc.transaction_purposes,
                "cost_center": self.doc.cost_center,
                "project": self.doc.project,
                "against_account": f"{self.doc.remittance_bank_gl}, {self.doc.wht_account}"
            })

            # Credit: WHT Account
            je.append("accounts", {
                "account": self.doc.wht_account,
                "credit_in_account_currency": wht_amount,
                "credit": wht_amount,
                "exchange_rate": 1,
                "user_remark": f"WHT @ {flt(self.doc.whtax_rate)}% on {self.doc.transaction_purposes}",
                "cost_center": self.doc.cost_center,
                "against_account": self.doc.account_to_debit
            })

            # Credit: Bank Account (net amount)
            bank_credit = net_amount if self.is_local_currency else (net_amount / exchange_rate)

            je.append("accounts", {
                "account": self.doc.remittance_bank_gl,
                "credit_in_account_currency": bank_credit,
                "credit": net_amount,
                "exchange_rate": exchange_rate if not self.is_local_currency else 1,
                "user_remark": self.doc.transaction_purposes,
                "bank_account": self.doc.remittance_bank,
                "against_account": self.doc.account_to_debit
            })

            return self._save_and_submit_journal_entry(je)

        except Exception as e:
            frappe.logger().error(f"Error creating WHT expense entry: {str(e)}")
            frappe.log_error(frappe.get_traceback(), "WHT Expense Entry Error")
            raise

    def _create_multi_line_expense_entry(self):
        """Create multi-line expense payment"""
        frappe.logger().info(f"Creating multi-line expense entry for {self.doc.name}")

        try:
            je = self._initialize_journal_entry("Bank Entry")

            total_debit = 0
            against_accounts = []

            for item in self.doc.payments_item_line:
                if not item.gl_account or not flt(item.amount):
                    continue

                self._validate_account_not_group(item.gl_account)

                item_exch_rate = flt(item.exch_rate) or flt(self.doc.exchange_rate) or 1
                item_amount = flt(item.amount)
                amount_in_lc = item_amount if self.is_local_currency else (item_amount * item_exch_rate)
                total_debit += amount_in_lc
                against_accounts.append(item.gl_account)

                je.append("accounts", {
                    "account": item.gl_account,
                    "debit_in_account_currency": amount_in_lc,
                    "debit": amount_in_lc,
                    "exchange_rate": item_exch_rate,
                    "user_remark": item.description or self.doc.transaction_purposes,
                    "cost_center": item.cost_center,
                    "project": item.project,
                    "against_account": self.doc.remittance_bank_gl
                })

            credit_amount = self._get_payment_amount_for_bank()

            je.append("accounts", {
                "account": self.doc.remittance_bank_gl,
                "credit_in_account_currency": credit_amount,
                "credit": total_debit,
                "exchange_rate": flt(self.doc.exchange_rate) if not self.is_local_currency else 1,
                "user_remark": self.doc.transaction_purposes,
                "bank_account": self.doc.remittance_bank,
                "against_account": ", ".join(against_accounts)
            })

            return self._save_and_submit_journal_entry(je)

        except Exception as e:
            frappe.logger().error(f"Error creating multi-line expense entry: {str(e)}")
            frappe.log_error(frappe.get_traceback(), "Multi-line Expense Entry Error")
            raise

    def _create_shared_cost_entry(self):
        """Create shared cost allocation entry"""
        frappe.logger().info(f"Creating shared cost entry for {self.doc.name}")

        if not self.doc.cost_center_distribution:
            frappe.throw(_("Cost center distribution is required for shared cost allocation"))

        try:
            total_percentage = sum([flt(dist.distribution) for dist in self.doc.cost_center_distribution])
            if abs(total_percentage - 100) > 0.01:
                frappe.throw(_("Total cost center distribution must equal 100%. Current total: {0}%").format(
                    total_percentage))

            je = self._initialize_journal_entry("Bank Entry")

            base_amount = self._get_payment_amount_in_local_currency()
            cost_centers = []
            total_allocated = 0

            for idx, dist in enumerate(self.doc.cost_center_distribution, start=1):
                if not dist.cost_center:
                    frappe.throw(_("Row {0}: Cost Center is required").format(idx))

                dist_val = flt(dist.distribution)                            # FIX: was raw comparison
                if not dist_val or dist_val <= 0:
                    frappe.throw(_("Row {0}: Distribution percentage must be greater than zero").format(idx))

                if not frappe.db.exists('Cost Center', dist.cost_center):
                    frappe.throw(_("Row {0}: Cost Center '{1}' does not exist").format(idx, dist.cost_center))

                allocated_amount = (base_amount * dist_val) / 100
                total_allocated += allocated_amount
                cost_centers.append(dist.cost_center)

                je.append("accounts", {
                    "account": self.doc.account_to_debit,
                    "debit_in_account_currency": allocated_amount,
                    "debit": allocated_amount,
                    "exchange_rate": 1,
                    "user_remark": f"{dist.cost_center} ({dist_val}%): {self.doc.transaction_purposes}",
                    "cost_center": dist.cost_center,
                    "project": self.doc.project,
                    "against_account": self.doc.remittance_bank_gl
                })

            if abs(total_allocated - base_amount) > 0.01:
                frappe.msgprint(_("Warning: Allocated amount ({0}) does not exactly match payment amount ({1}) due to rounding").format(
                    total_allocated, base_amount
                ), indicator='orange', alert=True)

            credit_amount = self._get_payment_amount_for_bank()

            je.append("accounts", {
                "account": self.doc.remittance_bank_gl,
                "credit_in_account_currency": credit_amount,
                "credit": base_amount,
                "exchange_rate": flt(self.doc.exchange_rate) if not self.is_local_currency else 1,
                "user_remark": f"Shared cost allocation ({len(cost_centers)} cost centers): {self.doc.transaction_purposes}",
                "bank_account": self.doc.remittance_bank,
                "against_account": self.doc.account_to_debit
            })

            return self._save_and_submit_journal_entry(je)

        except Exception as e:
            frappe.logger().error(f"Error creating shared cost entry: {str(e)}")
            frappe.log_error(frappe.get_traceback(), "Shared Cost Entry Error")
            raise

    def _create_related_company_entries(self):
        """Create entries for related company transactions"""
        frappe.logger().info(f"Creating related company entries for {self.doc.name}")

        if not self.doc.related_company_payments:
            frappe.logger().warning("No related company payments found")
            return self.created_entries

        entries = []
        errors = []

        for idx, rc_payment in enumerate(self.doc.related_company_payments, start=1):
            validation_error = self._validate_related_company_row(rc_payment, idx)
            if validation_error:
                errors.append(validation_error)
                continue

            try:
                je_name = self._create_single_related_company_entry(rc_payment, idx)
                if je_name:
                    entries.append({
                        'doctype': 'Journal Entry',
                        'name': je_name,
                        'company': rc_payment.company,
                        'amount': flt(rc_payment.amount_in_lcy) or flt(rc_payment.amount)
                    })
                    frappe.logger().info(f"Related company entry {je_name} created for row {idx}")

            except Exception as e:
                error_msg = f"Row {idx}: {str(e)}"
                errors.append(error_msg)
                frappe.logger().error(f"Error creating related company entry for row {idx}: {str(e)}")
                frappe.log_error(frappe.get_traceback(), f"Related Company Entry Error - Row {idx}")

        if entries:
            self.created_entries.extend(entries)
            frappe.msgprint(_("Created {0} related company entries").format(len(entries)),
                            indicator="green")

        if errors:
            error_message = _("Failed to create {0} related company entries:").format(len(errors))
            error_message += "<br>" + "<br>".join(errors[:5])
            frappe.msgprint(error_message, indicator="orange", title=_("Partial Success"))

        return self.created_entries

    def _validate_related_company_row(self, rc_payment, row_num):
        """Validate a single related company payment row"""
        if not rc_payment.company:
            return _("Row {0}: Company is required").format(row_num)

        if not rc_payment.party:
            return _("Row {0}: Account/Party is required").format(row_num)

        rc_amount = flt(rc_payment.amount)                                   # FIX: was raw comparison
        if not rc_amount or rc_amount <= 0:
            return _("Row {0}: Amount must be greater than zero").format(row_num)

        if not rc_payment.related_company_account:
            return _("Row {0}: Related Company Account is required").format(row_num)

        if not frappe.db.exists('Account', rc_payment.party):
            return _("Row {0}: Account '{1}' does not exist").format(row_num, rc_payment.party)

        if not frappe.db.exists('Account', rc_payment.related_company_account):
            return _("Row {0}: Related Company Account '{1}' does not exist").format(
                row_num, rc_payment.related_company_account)

        if frappe.db.get_value('Account', rc_payment.party, 'is_group'):
            return _("Row {0}: '{1}' is a group account and cannot be used").format(
                row_num, rc_payment.party)

        if frappe.db.get_value('Account', rc_payment.related_company_account, 'is_group'):
            return _("Row {0}: '{1}' is a group account and cannot be used").format(
                row_num, rc_payment.related_company_account)

        if not frappe.db.exists('Company', rc_payment.company):
            return _("Row {0}: Company '{1}' does not exist").format(row_num, rc_payment.company)

        return None

    def _create_single_related_company_entry(self, rc_payment, row_num):
        """Create a single related company journal entry"""
        je = frappe.new_doc("Journal Entry")
        je.voucher_type = "Journal Entry"
        je.naming_series = "JV-.YYYY.-"
        je.company = rc_payment.company
        je.posting_date = self.doc.transaction_date
        je.cheque_no = f"{self.doc.reference_no}-RC{row_num}"
        je.cheque_date = self.doc.transaction_date
        je.user_remark = rc_payment.remark or self.doc.transaction_purposes or "Related Company Payment"
        je.multi_currency = 1 if not self.is_local_currency else 0

        amount = flt(rc_payment.amount_in_lcy) or flt(rc_payment.amount)
        exch_rate = flt(getattr(rc_payment, 'exch_rate', None)) or flt(self.doc.exchange_rate) or 1

        je.append("accounts", {
            "account": rc_payment.party,
            "debit_in_account_currency": amount,
            "debit": amount,
            "exchange_rate": exch_rate,
            "cost_center": rc_payment.cost_center,
            "project": getattr(rc_payment, 'project', None) or self.doc.project,
            "user_remark": rc_payment.remark or self.doc.transaction_purposes,
            "against_account": rc_payment.related_company_account
        })

        je.append("accounts", {
            "account": rc_payment.related_company_account,
            "credit_in_account_currency": amount,
            "credit": amount,
            "exchange_rate": exch_rate,
            "cost_center": rc_payment.cost_center,
            "user_remark": rc_payment.remark or f"Related company payment - {self.doc.name}",
            "against_account": rc_payment.party
        })

        je.set_total_debit_credit()
        je.flags.ignore_permissions = True
        je.insert(ignore_permissions=True)
        je.submit()

        return je.name

    # ==================== Transfer Out Entries ====================

    def _create_transfer_out_entries(self):
        """Create entries for fund transfer"""
        frappe.logger().info(f"Creating transfer out entry for {self.doc.name}")

        try:
            je = self._initialize_journal_entry("Bank Entry")

            interbank_account = self._get_interbank_account()
            self._validate_account_not_group(interbank_account)

            transfer_amount = self._get_payment_amount_in_local_currency()
            credit_amount = self._get_payment_amount_for_bank()

            je.append("accounts", {
                "account": interbank_account,
                "debit_in_account_currency": transfer_amount,
                "debit": transfer_amount,
                "exchange_rate": 1,
                "user_remark": f"Transfer from {self.doc.remittance_bank}: {self.doc.transaction_purposes}",
                "against_account": self.doc.remittance_bank_gl
            })

            je.append("accounts", {
                "account": self.doc.remittance_bank_gl,
                "credit_in_account_currency": credit_amount,
                "credit": transfer_amount,
                "exchange_rate": flt(self.doc.exchange_rate) if not self.is_local_currency else 1,
                "user_remark": self.doc.transaction_purposes,
                "bank_account": self.doc.remittance_bank,
                "against_account": interbank_account
            })

            return self._save_and_submit_journal_entry(je)

        except Exception as e:
            frappe.logger().error(f"Error creating transfer out entry: {str(e)}")
            frappe.log_error(frappe.get_traceback(), "Transfer Out Entry Error")
            raise

    def _get_interbank_account(self):
        """Get interbank transfer account with caching"""
        if not self._cache['interbank_account']:
            self._cache['interbank_account'] = frappe.db.get_value(
                'Company', self.company, 'custom_default_interbank_transfer', cache=True
            ) or self.doc.account_to_debit
        return self._cache['interbank_account']

    # ==================== Supplier Refund Entries ====================

    def _create_supplier_refund_entries(self):
        """Create entries for supplier refunds"""
        frappe.logger().info(f"Creating supplier refund entry for {self.doc.name}")

        try:
            je = self._initialize_journal_entry("Bank Entry")
            je.voucher_type = "Bank Entry"

            refund_amount = self._get_payment_amount_in_local_currency()
            debit_amount = self._get_payment_amount_for_bank()
            payable_account = self._get_payable_account()

            je.append("accounts", {
                "account": self.doc.remittance_bank_gl,
                "debit_in_account_currency": debit_amount,
                "debit": refund_amount,
                "exchange_rate": flt(self.doc.exchange_rate) if not self.is_local_currency else 1,
                "user_remark": f"Refund from {self.doc.supplier_name}: {self.doc.transaction_purposes}",
                "bank_account": self.doc.remittance_bank,
                "against_account": payable_account
            })

            je.append("accounts", {
                "account": payable_account,
                "party_type": "Supplier",
                "party": self.doc.payee_id,
                "credit_in_account_currency": refund_amount,
                "credit": refund_amount,
                "exchange_rate": 1,
                "user_remark": self.doc.transaction_purposes,
                "against_account": self.doc.remittance_bank_gl
            })

            return self._save_and_submit_journal_entry(je)

        except Exception as e:
            frappe.logger().error(f"Error creating supplier refund entry: {str(e)}")
            frappe.log_error(frappe.get_traceback(), "Supplier Refund Entry Error")
            raise

    # ==================== Helper Methods ====================

    def _initialize_journal_entry(self, voucher_type="Bank Entry"):
        """Initialize a new Journal Entry with common fields"""
        je = frappe.new_doc("Journal Entry")
        je.voucher_type = voucher_type
        je.naming_series = "JV-.YYYY.-"
        je.company = self.company
        je.posting_date = self.doc.transaction_date
        je.cheque_no = self.doc.reference_no
        je.cheque_date = self.doc.transaction_date
        je.user_remark = self.doc.transaction_purposes
        je.paid_to_or_received_from = self.doc.payee_name or self.doc.supplier_name
        je.multi_currency = 1 if not self.is_local_currency else 0
        return je

    def _get_payment_amount_in_local_currency(self):
        """Get payment amount in company currency — safe flt() wrapping"""
        if self.is_local_currency:
            return flt(self.doc.amount_paid)
        else:
            return flt(self.doc.amount_paid_in_fc) * (flt(self.doc.exchange_rate) or 1)

    def _get_payment_amount_for_bank(self):
        """Get payment amount in bank account currency — safe flt() wrapping"""
        if self.is_local_currency:
            return flt(self.doc.amount_paid)
        else:
            return flt(self.doc.amount_paid_in_fc)

    def _set_accounting_dimensions(self, doc):
        """Set accounting dimensions on document"""
        if self.doc.cost_center:
            doc.cost_center = self.doc.cost_center
        if self.doc.project:
            doc.project = self.doc.project
        if self.doc.department:
            doc.department = self.doc.department
        if self.doc.branch:
            doc.branch = self.doc.branch

    def _save_and_submit_journal_entry(self, je):
        """Save and submit journal entry with error handling"""
        try:
            je.set_total_debit_credit()
            je.flags.ignore_permissions = True
            je.insert(ignore_permissions=True)
            je.submit()

            self.created_entries.append({
                'doctype': 'Journal Entry',
                'name': je.name,
                'amount': je.total_debit
            })

            frappe.logger().info(f"Journal Entry {je.name} created and submitted")
            frappe.msgprint(_("Journal Entry {0} created").format(je.name), indicator="green")

            return self.created_entries

        except Exception as e:
            frappe.logger().error(f"Error saving journal entry: {str(e)}")
            raise

    def get_created_entries_summary(self):
        """Get summary of created entries"""
        return {
            'total_entries': len(self.created_entries),
            'entries': self.created_entries
        }


# ==================== AccountingEntryCanceller Class ====================

class AccountingEntryCanceller:
    """Handle cancellation of accounting entries with optimized queries"""

    def __init__(self, payment_doc):
        self.doc = payment_doc
        self.cancelled_entries = []

    def cancel_all_entries(self):
        """Cancel all related accounting entries"""
        frappe.logger().info(f"Cancelling accounting entries for {self.doc.name}")

        self._cancel_journal_entries()
        self._cancel_payment_entries()

        if self.cancelled_entries:
            frappe.msgprint(_("Cancelled {0} accounting entries").format(len(self.cancelled_entries)),
                            indicator="orange")

        return self.cancelled_entries

    def _cancel_journal_entries(self):
        """Cancel related journal entries"""
        je_list = frappe.db.sql("""
            SELECT name
            FROM `tabJournal Entry`
            WHERE (cheque_no = %s OR cheque_no LIKE %s)
            AND company = %s
            AND docstatus = 1
            LIMIT 50
        """, (self.doc.reference_no, f"{self.doc.reference_no}-RC%", self.doc.company), as_dict=1)

        for je in je_list:
            try:
                doc = frappe.get_doc('Journal Entry', je.name)
                doc.cancel()
                self.cancelled_entries.append({
                    'doctype': 'Journal Entry',
                    'name': je.name,
                    'status': 'Cancelled'
                })
                frappe.logger().info(f"Cancelled Journal Entry {je.name}")

            except Exception as e:
                frappe.log_error(frappe.get_traceback(),
                                 f"Error cancelling Journal Entry {je.name}")
                self.cancelled_entries.append({
                    'doctype': 'Journal Entry',
                    'name': je.name,
                    'status': 'Error',
                    'error': str(e)
                })

    def _cancel_payment_entries(self):
        """Cancel related payment entries"""
        pe_list = frappe.db.get_all('Payment Entry',
            filters={
                'reference_no': self.doc.reference_no,
                'company': self.doc.company,
                'docstatus': 1
            },
            fields=['name'],
            limit=50
        )

        for pe in pe_list:
            try:
                doc = frappe.get_doc('Payment Entry', pe.name)
                doc.cancel()
                self.cancelled_entries.append({
                    'doctype': 'Payment Entry',
                    'name': pe.name,
                    'status': 'Cancelled'
                })
                frappe.logger().info(f"Cancelled Payment Entry {pe.name}")

            except Exception as e:
                frappe.log_error(frappe.get_traceback(),
                                 f"Error cancelling Payment Entry {pe.name}")
                self.cancelled_entries.append({
                    'doctype': 'Payment Entry',
                    'name': pe.name,
                    'status': 'Error',
                    'error': str(e)
                })


# ==================== Main Document Class ====================

class Payments(Document):
    """Main Payments DocType Class with comprehensive validation"""

    def validate(self):
        """Validate payment document"""
        self.validate_required_fields()
        self.validate_amounts()
        self.validate_dates()
        self.validate_accounts()
        self.validate_cost_center_distribution()
        self.validate_related_company_payments()
        self.calculate_totals()
        self.set_amount_in_words()

    def validate_required_fields(self):
        """Validate required fields"""
        if not self.trans_type:
            frappe.throw(_("Transaction Type is required"))

        if not self.company:
            frappe.throw(_("Company is required"))

        if not self.transaction_date:
            frappe.throw(_("Transaction Date is required"))

        if not self.reference_no:
            frappe.throw(_("Reference Number is required"))

    def validate_amounts(self):
        """Validate payment amounts — all numeric fields coerced via flt() before comparison"""
        company_currency = frappe.db.get_value('Company', self.company, 'default_currency', cache=True)

        if not company_currency:
            frappe.throw(_("Company currency not found for {0}").format(self.company))

        # Safely coerce all numeric fields to float before any comparison or arithmetic
        amount_paid = flt(self.amount_paid)
        amount_paid_in_fc = flt(self.amount_paid_in_fc)
        exchange_rate = flt(self.exchange_rate)
        whtax_rate = flt(self.whtax_rate)

        # Ensure amount is positive
        amount = amount_paid if self.payment_currency == company_currency else amount_paid_in_fc
        if not amount or amount <= 0:
            frappe.throw(_("Payment amount must be greater than zero"))

        # Calculate local currency amount
        if self.payment_currency != company_currency:
            if not exchange_rate or exchange_rate <= 0:
                frappe.throw(_("Exchange rate must be greater than zero"))
            self.local_currency_amount = amount_paid_in_fc * exchange_rate
        else:
            self.local_currency_amount = amount_paid

        # Calculate WHT if applicable
        if self.deduct_wht:
            if not whtax_rate or whtax_rate <= 0:
                frappe.throw(_("WHT rate is required when deducting WHT"))
            self.wht_amount = (flt(self.local_currency_amount) * whtax_rate) / 100
            self.net_amount = flt(self.local_currency_amount) - self.wht_amount
        else:
            self.wht_amount = 0
            self.net_amount = flt(self.local_currency_amount)

    def validate_dates(self):
        """Validate dates"""
        if self.transaction_date and getdate(self.transaction_date) > getdate(nowdate()):
            frappe.throw(_("Transaction date cannot be in the future"))

        if self.amortize:
            if not self.start_date or not self.end_date:
                frappe.throw(_("Start date and end date are required for amortization"))

            if getdate(self.end_date) <= getdate(self.start_date):
                frappe.throw(_("End date must be after start date"))

    def validate_accounts(self):
        """Validate account selections"""
        if self.trans_type in ['Expense Payment', 'Transfer Out'] and not self.account_to_debit:
            frappe.throw(_("Account to Debit is required for {0}").format(self.trans_type))

        if self.deduct_wht and not self.wht_account:
            frappe.throw(_("WHT Account is required when deducting WHT"))

        if self.remittance_bank:
            if not frappe.db.exists('Bank Account', self.remittance_bank):
                frappe.throw(_("Bank Account {0} not found").format(self.remittance_bank))

    def validate_cost_center_distribution(self):
        """Validate cost center distribution for shared costs"""
        if not self.is_shared_cost:
            return

        if not self.cost_center_distribution:
            frappe.throw(_("Cost center distribution is required when 'Is Shared Cost' is enabled"))

        total_percentage = sum([flt(row.distribution) for row in self.cost_center_distribution])

        if abs(total_percentage - 100) > 0.01:
            frappe.throw(_("Total cost center distribution must equal 100%. Current total: {0}%").format(
                round(total_percentage, 2)
            ))

        for idx, row in enumerate(self.cost_center_distribution, start=1):
            if not row.cost_center:
                frappe.throw(_("Row {0}: Cost Center is required").format(idx))

            dist_val = flt(row.distribution)                                 # FIX: was raw comparison
            if not dist_val or dist_val <= 0:
                frappe.throw(_("Row {0}: Distribution percentage must be greater than zero").format(idx))

            if dist_val > 100:                                               # FIX: was raw comparison
                frappe.throw(_("Row {0}: Distribution percentage cannot exceed 100%").format(idx))

            if not frappe.db.exists('Cost Center', row.cost_center):
                frappe.throw(_("Row {0}: Cost Center '{1}' does not exist").format(idx, row.cost_center))

            if frappe.db.get_value('Cost Center', row.cost_center, 'disabled'):
                frappe.throw(_("Row {0}: Cost Center '{1}' is disabled").format(idx, row.cost_center))

        frappe.logger().info(f"Cost center distribution validated - Total: {total_percentage}%")

    def validate_related_company_payments(self):
        """Validate related company payments"""
        if not self.is_related_coy_trans:
            return

        if not self.related_company_payments:
            frappe.throw(_("Related company payment details are required when 'Is Related Company Transaction' is enabled"))

        total_amount = 0

        for idx, row in enumerate(self.related_company_payments, start=1):
            if not row.company:
                frappe.throw(_("Row {0}: Company is required").format(idx))

            if not row.party:
                frappe.throw(_("Row {0}: Account/Party is required").format(idx))

            row_amount = flt(row.amount)                                     # FIX: was raw comparison
            if not row_amount or row_amount <= 0:
                frappe.throw(_("Row {0}: Amount must be greater than zero").format(idx))

            if not row.related_company_account:
                frappe.throw(_("Row {0}: Related Company Account is required").format(idx))

            if not frappe.db.exists('Company', row.company):
                frappe.throw(_("Row {0}: Company '{1}' does not exist").format(idx, row.company))

            if not frappe.db.exists('Account', row.party):
                frappe.throw(_("Row {0}: Account '{1}' does not exist").format(idx, row.party))

            if not frappe.db.exists('Account', row.related_company_account):
                frappe.throw(_("Row {0}: Related Company Account '{1}' does not exist").format(
                    idx, row.related_company_account))

            if frappe.db.get_value('Account', row.party, 'is_group'):
                frappe.throw(_("Row {0}: '{1}' is a group account and cannot be used for transactions").format(
                    idx, row.party))

            if frappe.db.get_value('Account', row.related_company_account, 'is_group'):
                frappe.throw(_("Row {0}: '{1}' is a group account and cannot be used for transactions").format(
                    idx, row.related_company_account))

            if row.cost_center:
                if not frappe.db.exists('Cost Center', row.cost_center):
                    frappe.throw(_("Row {0}: Cost Center '{1}' does not exist").format(idx, row.cost_center))

                if frappe.db.get_value('Cost Center', row.cost_center, 'disabled'):
                    frappe.throw(_("Row {0}: Cost Center '{1}' is disabled").format(idx, row.cost_center))

            total_amount += flt(row.amount_in_lcy or row.amount)

        payment_amount = flt(self.local_currency_amount) or flt(self.amount_paid)
        if abs(total_amount - payment_amount) > 0.01:
            frappe.msgprint(_("Warning: Total related company amount ({0}) does not match payment amount ({1})").format(
                total_amount, payment_amount
            ), indicator='orange', alert=True)

        frappe.logger().info(f"Related company payments validated - Total: {total_amount}")

    def calculate_totals(self):
        """Calculate all totals"""
        if self.payments_reference:
            self.total_outstanding_invoice = sum([flt(row.allocated_amount) for row in self.payments_reference])

        if self.payments_item_line:
            self.total_multi_line_amount = sum([flt(row.amount_in_lcy or row.amount) for row in self.payments_item_line])

        if self.cost_center_distribution:
            self.total_percentage = sum([flt(row.distribution) for row in self.cost_center_distribution])

        if self.related_company_payments:
            self.total_rcoy = sum([flt(row.amount_in_lcy or row.amount) for row in self.related_company_payments])

    def set_amount_in_words(self):
        """Convert amount to words"""
        if self.local_currency_amount:
            company_currency = frappe.db.get_value('Company', self.company, 'default_currency', cache=True) or 'NGN'
            self.amount_in_words = money_in_words(flt(self.local_currency_amount), company_currency)

    def before_submit(self):
        """Before submit validations"""
        self.payment_status = 'Pending'
        frappe.logger().info(f"Submitting Payment {self.name}")

    def on_submit(self):
        """On submit event"""
        frappe.logger().info(f"Payment {self.name} submitted")

        try:
            if self.create_accounting_entries:
                controller = PaymentAccountingController(self)
                created = controller.create_accounting_entries()

                if created:
                    frappe.logger().info(f"Created {len(created)} accounting entries for {self.name}")

            if self.amortize and self.amortization_schedule:
                create_all_amortization_entries(self)

            self.db_set('payment_status', 'Completed')
            frappe.db.commit()

        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(frappe.get_traceback(), f"Payment Submission Error - {self.name}")
            frappe.throw(_("Error during submission: {0}").format(str(e)))

    def on_cancel(self):
        """On cancel event"""
        frappe.logger().info(f"Cancelling Payment {self.name}")

        try:
            canceller = AccountingEntryCanceller(self)
            canceller.cancel_all_entries()

            cancel_amortization_entries(self)

            self.db_set('payment_status', 'Cancelled')
            frappe.db.commit()

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"Payment Cancellation Error - {self.name}")
            frappe.throw(_("Error during cancellation: {0}").format(str(e)))


# ==================== Amortization Functions ====================

def create_all_amortization_entries(payment_doc):
    """Create all amortization journal entries immediately on submit"""
    try:
        if not payment_doc.amortization_schedule:
            return

        created_entries = []

        for schedule_entry in payment_doc.amortization_schedule:
            if not schedule_entry.journal_entry:
                je_name = create_single_amortization_entry(payment_doc, schedule_entry)
                if je_name:
                    created_entries.append(je_name)

        if created_entries:
            payment_doc.db_set('amortization_status', 'Completed')
            frappe.msgprint(
                _("Created {0} amortization journal entries").format(len(created_entries)),
                indicator='green',
                alert=True
            )
            frappe.logger().info(f"Created {len(created_entries)} amortization entries for {payment_doc.name}")

        return created_entries

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Amortization Creation Error")
        frappe.throw(_("Failed to create amortization entries: {0}").format(str(e)))


def create_single_amortization_entry(payment_doc, schedule_entry):
    """Create a single amortization journal entry"""
    try:
        je = frappe.new_doc("Journal Entry")
        je.voucher_type = "Journal Entry"
        je.naming_series = "JV-.YYYY.-"
        je.company = payment_doc.company
        je.posting_date = schedule_entry.period_start
        je.user_remark = f"Amortization for {payment_doc.name} - Period {schedule_entry.period_start} to {schedule_entry.period_end}"

        if not payment_doc.expense_account or not payment_doc.deferred_expense_account:
            frappe.throw(_("Expense Account and Deferred Expense Account are required for amortization"))

        entry_amount = flt(schedule_entry.amount)

        je.append("accounts", {
            "account": payment_doc.expense_account,
            "debit_in_account_currency": entry_amount,
            "debit": entry_amount,
            "cost_center": payment_doc.cost_center,
            "project": payment_doc.project,
            "user_remark": f"Amortization expense for period {schedule_entry.period_start}",
            "against_account": payment_doc.deferred_expense_account
        })

        je.append("accounts", {
            "account": payment_doc.deferred_expense_account,
            "credit_in_account_currency": entry_amount,
            "credit": entry_amount,
            "cost_center": payment_doc.cost_center,
            "project": payment_doc.project,
            "user_remark": f"Deferred expense amortization for period {schedule_entry.period_start}",
            "against_account": payment_doc.expense_account
        })

        je.set_total_debit_credit()
        je.flags.ignore_permissions = True
        je.insert(ignore_permissions=True)
        je.submit()

        frappe.db.set_value('Schedule of Prepayments', schedule_entry.name, {
            'journal_entry': je.name,
            'je_status': 'Posted'
        })

        frappe.logger().info(f"Created amortization entry {je.name} for {payment_doc.name}")

        return je.name

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"Amortization Entry Error - {schedule_entry.name}")
        return None


def cancel_amortization_entries(payment_doc):
    """Cancel all amortization journal entries"""
    try:
        schedule_entries = frappe.db.get_all('Schedule of Prepayments',
            filters={
                'parent': payment_doc.name,
                'parenttype': 'Payments',
                'journal_entry': ['is', 'set']
            },
            fields=['name', 'journal_entry'],
            limit=100
        )

        cancelled_count = 0

        for entry in schedule_entries:
            if entry.journal_entry:
                try:
                    je = frappe.get_doc('Journal Entry', entry.journal_entry)
                    if je.docstatus == 1:
                        je.cancel()
                        cancelled_count += 1

                    frappe.db.set_value('Schedule of Prepayments', entry.name, {
                        'journal_entry': None,
                        'je_status': 'Cancelled'
                    })

                except Exception as e:
                    frappe.log_error(frappe.get_traceback(),
                                     f"Error cancelling amortization entry {entry.journal_entry}")

        if cancelled_count > 0:
            payment_doc.db_set('amortization_status', 'Not Started')
            frappe.msgprint(
                _("Cancelled {0} amortization journal entries").format(cancelled_count),
                indicator='orange',
                alert=True
            )
            frappe.logger().info(f"Cancelled {cancelled_count} amortization entries for {payment_doc.name}")

        return cancelled_count

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Amortization Cancellation Error")


# ==================== Whitelisted API Methods ====================

@frappe.whitelist()
def create_accounting_entries_from_ui(payment_name):
    """Create accounting entries from UI button click"""
    try:
        doc = frappe.get_doc('Payments', payment_name)

        if doc.docstatus != 1:
            frappe.throw(_("Payment must be submitted before creating accounting entries"))

        controller = PaymentAccountingController(doc)
        created_entries = controller.create_accounting_entries()

        if not created_entries:
            frappe.msgprint(_("No accounting entries were created. Please check configuration."),
                            indicator="orange")
            return None

        frappe.db.commit()

        return controller.get_created_entries_summary()

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Payment Accounting UI Error")
        frappe.throw(_("Failed to create accounting entries: {0}").format(str(e)))


@frappe.whitelist()
def cancel_accounting_entries_from_ui(payment_name):
    """Cancel accounting entries from UI"""
    try:
        doc = frappe.get_doc('Payments', payment_name)

        canceller = AccountingEntryCanceller(doc)
        cancelled_entries = canceller.cancel_all_entries()

        frappe.db.commit()

        return {
            'cancelled_count': len(cancelled_entries),
            'entries': cancelled_entries
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Payment Cancellation UI Error")
        frappe.throw(_("Failed to cancel accounting entries: {0}").format(str(e)))


@frappe.whitelist()
def generate_amortization_schedule(start_date, end_date, frequency, amount):
    """Generate amortization schedule based on parameters"""
    try:
        start_date = getdate(start_date)
        end_date = getdate(end_date)
        amount = flt(amount)

        if amount <= 0:
            frappe.throw(_("Amount must be greater than zero"))

        schedule = []
        current_date = start_date

        if frequency == "Monthly":
            increment = lambda d: add_months(d, 1)
        elif frequency == "Quarterly":
            increment = lambda d: add_months(d, 3)
        elif frequency == "Yearly":
            increment = lambda d: add_months(d, 12)
        else:
            frappe.throw(_("Invalid frequency. Must be Monthly, Quarterly, or Yearly"))

        total_periods = 0
        temp_date = start_date
        while temp_date < end_date:
            total_periods += 1
            temp_date = increment(temp_date)

        if total_periods == 0:
            frappe.throw(_("Invalid date range - must span at least one period"))

        amount_per_period = amount / total_periods

        period_num = 1
        while current_date < end_date:
            period_end = increment(current_date)
            if period_end > end_date:
                period_end = end_date

            schedule.append({
                'period': period_num,
                'start': current_date.strftime('%Y-%m-%d'),
                'end': period_end.strftime('%Y-%m-%d'),
                'amount': round(amount_per_period, 2),
                'status': 'Pending'
            })

            current_date = period_end
            period_num += 1

        return schedule

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Amortization Schedule Generation Error")
        frappe.throw(_("Failed to generate schedule: {0}").format(str(e)))


@frappe.whitelist()
def get_linked_accounting_entries(payment_name):
    """Get all accounting entries linked to a payment"""
    try:
        doc = frappe.get_doc('Payments', payment_name)

        je_list = frappe.db.sql("""
            SELECT name, posting_date, total_debit, docstatus
            FROM `tabJournal Entry`
            WHERE (cheque_no = %s OR cheque_no LIKE %s)
            AND company = %s
            AND docstatus != 2
            ORDER BY posting_date DESC
            LIMIT 100
        """, (doc.reference_no, f"{doc.reference_no}-RC%", doc.company), as_dict=1)

        pe_list = frappe.db.get_all('Payment Entry',
            filters={
                'reference_no': doc.reference_no,
                'company': doc.company,
                'docstatus': ['!=', 2]
            },
            fields=['name', 'posting_date', 'paid_amount', 'docstatus'],
            order_by='posting_date desc',
            limit=100
        )

        amortization_entries = []
        if doc.amortize and doc.amortization_schedule:
            for schedule_entry in doc.amortization_schedule:
                if schedule_entry.journal_entry:
                    try:
                        je = frappe.get_doc('Journal Entry', schedule_entry.journal_entry)
                        amortization_entries.append({
                            'name': je.name,
                            'posting_date': je.posting_date,
                            'total_debit': je.total_debit,
                            'docstatus': je.docstatus,
                            'is_amortization': True
                        })
                    except Exception:
                        pass

        return {
            'journal_entries': je_list,
            'payment_entries': pe_list,
            'amortization_entries': amortization_entries,
            'total_entries': len(je_list) + len(pe_list) + len(amortization_entries)
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Linked Entries Error")
        return {
            'journal_entries': [],
            'payment_entries': [],
            'amortization_entries': [],
            'total_entries': 0,
            'error': str(e)
        }


@frappe.whitelist()
def get_bank_balance(bank_account):
    """Get current bank balance"""
    try:
        account = frappe.db.get_value('Bank Account', bank_account, 'account', cache=True)

        if not account:
            currency = frappe.db.get_value('Bank Account', bank_account, 'account_currency', cache=True) or 'NGN'
            return {'balance': 0, 'currency': currency, 'formatted': fmt_money(0, currency=currency)}

        from erpnext.accounts.utils import get_balance_on

        balance = get_balance_on(account)
        currency = frappe.db.get_value('Account', account, 'account_currency', cache=True) or 'NGN'

        return {
            'balance': balance,
            'currency': currency,
            'formatted': fmt_money(balance, currency=currency)
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Bank Balance Error")
        return {'balance': 0, 'currency': 'NGN', 'formatted': '0.00', 'error': str(e)}


# ==================== Hook Functions ====================

def validate_payment(doc, method):
    """Called on validate event - Check for duplicate reference"""
    if not doc.reference_no:
        return

    existing_payment = frappe.db.sql("""
        SELECT name
        FROM `tabPayments`
        WHERE reference_no = %s
        AND name != %s
        AND company = %s
        AND docstatus != 2
        LIMIT 1
    """, (doc.reference_no, doc.name, doc.company), as_dict=1)

    if existing_payment:
        frappe.throw(_("Payment with reference number {0} already exists: {1}").format(
            doc.reference_no, existing_payment[0].name
        ))


def before_submit_payment(doc, method):
    """Called before submit - Final validations"""
    pass


def on_trash_payment(doc, method):
    """Called when document is deleted"""
    if doc.docstatus == 1:
        frappe.throw(_("Cannot delete submitted payment. Please cancel it first."))