# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

"""
Payment Accounting Module
Handles all accounting entry creation for Payments DocType.
Creates Journal Entries and Payment Entries based on transaction type.

This file is the single source of truth for Payments server logic.
payments_utils.py has been retired — its useful pieces (notifications,
duplicate-payment check, bank balance check, batch processing, analytics)
were merged in below; everything else was dead code that duplicated
functionality already here and has been removed.
"""

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
    add_days,
    add_months,
    flt,
    fmt_money,
    get_url_to_form,
    getdate,
    money_in_words,
    nowdate,
)

# ── Auto Transaction Coding ───────────────────────────────────────────────────
from ecclesia.api.auto_transaction_coding import (
    _load_active_rules,
    _match_and_resolve,
    _partition_rules,
    _write_coding_log,
)


# ==================== Auto-Coding Helper (module level) ====================

def _attempt_auto_coding_if_needed(doc):
    """
    Called from Payments.before_submit().

    If account_to_debit is missing on an Expense Payment that has
    create_accounting_entries=True, attempt auto-coding BEFORE any
    validation fires.  Mutates doc.account_to_debit in-place so the
    subsequent _validate_before_creation check passes.

    Outcomes
    ────────
    Matched & resolved   → sets doc.account_to_debit, shows green alert,
                           continues to submit normally.
    Rule matched but
    account not in CoA   → throws with actionable guidance (stops submit).
    No rule matched      → returns silently; _validate_before_creation
                           will throw its normal "Account to Debit is
                           required" message.
    """
    needs_coding = (
        doc.trans_type == "Expense Payment"
        and doc.get("create_accounting_entries")
        and not doc.account_to_debit
        and doc.transaction_purposes
        and doc.company
    )

    if not needs_coding:
        return

    rules = _load_active_rules()
    if not rules:
        return  # No rules configured — fall through to validation

    company_rules, global_rules = _partition_rules(rules)
    cache = {}

    result = _match_and_resolve(
        description=doc.transaction_purposes,
        company=doc.company,
        company_rules=company_rules,
        global_rules=global_rules,
        cache=cache,
    )

    if result and result.get("account"):
        # ── Matched and resolved ─────────────────────────────────────────
        doc.account_to_debit              = result["account"]
        doc.auto_coding_rule              = result["rule"]
        doc.auto_coding_status            = "Matched"
        doc.auto_coding_resolution_method = result["resolution_method"]

        _write_coding_log(
            payment=doc.name,
            company=doc.company,
            description=doc.transaction_purposes,
            rule=result["rule"],
            account=result["account"],
            rule_scope=result["rule_scope"],
            resolution_method=result["resolution_method"],
            status="Matched",
            notes="Auto-coded during before_submit.",
        )

        frappe.msgprint(
            _("Account auto-coded: <b>{0}</b> (Rule: {1})").format(
                result["account"], result["rule"]
            ),
            indicator="green",
            alert=True,
        )

    elif result and result.get("resolution_failed"):
        # ── Rule matched but account not in this company's Chart of Accounts
        _write_coding_log(
            payment=doc.name,
            company=doc.company,
            description=doc.transaction_purposes,
            rule=result["rule"],
            account=None,
            rule_scope=result.get("rule_scope"),
            resolution_method="Not Resolved",
            status="Resolution Failed",
            notes=result.get("notes"),
        )

        frappe.throw(
            _(
                "Auto-coding matched rule <b>{0}</b> but the account does not exist "
                "in <b>{1}</b>'s Chart of Accounts.<br><br>"
                "Options:<br>"
                "• Add the account to <b>{1}</b>'s Chart of Accounts, <i>or</i><br>"
                "• Add a company-specific rule override for <b>{1}</b> in "
                "<b>Auto Transaction Coding Rule</b>, <i>or</i><br>"
                "• Set <b>Account to Debit</b> manually before submitting."
            ).format(result["rule"], doc.company),
            title=_("Account Resolution Failed"),
        )

    # else: no rule matched — fall through silently.
    # PaymentAccountingController._validate_before_creation will throw
    # "Account to Debit is required" as normal.


# ==================== PaymentAccountingController ====================

class PaymentAccountingController:
    """
    Main controller for creating accounting entries.

    KEY DESIGN RULES
    ────────────────
    1. on_submit must NEVER call frappe.throw() — any error is caught,
       logged, and shown as msgprint so docstatus change is never rolled back.
    2. The UI button path (create_accounting_entries_from_ui) skips the
       already-exist guard entirely and delegates straight here.
    3. Duplicate prevention is done per-method, not at the top level, so
       the UI button can still create entries if on_submit failed.
    """

    def __init__(self, payment_doc):
        self.doc               = payment_doc
        self.company            = payment_doc.company
        self.company_currency   = self._get_company_currency()
        self.is_local_currency  = self.doc.payment_currency == self.company_currency
        self.created_entries    = []
        self._cache = {'payable_account': None, 'interbank_account': None}
        frappe.logger().info(f"PaymentAccountingController initialised for {payment_doc.name}")

    def _get_company_currency(self):
        return frappe.db.get_value('Company', self.company, 'default_currency', cache=True)

    # ── Existence checks ────────────────────────────────────────────────────

    def accounting_entries_exist(self):
        """
        Returns True only when submitted (docstatus=1) entries already exist.
        Used by the UI button to decide whether to show a warning or proceed.
        """
        ref     = self.doc.reference_no
        company = self.company

        je_exists = frappe.db.sql("""
            SELECT name FROM `tabJournal Entry`
            WHERE (cheque_no = %s OR cheque_no LIKE %s)
              AND company = %s AND docstatus = 1
            LIMIT 1
        """, (ref, f"{ref}-RC%", company), as_dict=1)

        if je_exists:
            return True

        pe_exists = frappe.db.get_all('Payment Entry',
            filters={'reference_no': ref, 'company': company, 'docstatus': 1},
            fields=['name'], limit=1)

        return bool(pe_exists)

    def _je_exists(self, cheque_no):
        return bool(frappe.db.exists('Journal Entry', {
            'cheque_no': cheque_no, 'company': self.company, 'docstatus': 1
        }))

    def _pe_exists(self):
        return bool(frappe.db.exists('Payment Entry', {
            'reference_no': self.doc.reference_no,
            'company': self.company,
            'docstatus': 1
        }))

    # ── Main entry point ────────────────────────────────────────────────────

    def create_accounting_entries(self, skip_duplicate_check=False):
        """
        Create accounting entries based on trans_type.

        skip_duplicate_check=True is used by on_submit (first-time creation).
        skip_duplicate_check=False is the default for the UI button (re-creation).
        """
        if not self.doc.create_accounting_entries:
            frappe.logger().info(f"Accounting entry creation disabled for {self.doc.name}")
            return []

        self._validate_before_creation()

        trans_type = self.doc.trans_type

        if trans_type == "Supplier Payment":
            return self._create_supplier_payment_entries(skip_duplicate_check)

        elif trans_type == "Expense Payment":
            return self._create_expense_payment_entries(skip_duplicate_check)

        elif trans_type == "Transfer Out":
            return self._create_transfer_out_entries(skip_duplicate_check)

        elif trans_type == "Supplier Refunds":
            return self._create_supplier_refund_entries(skip_duplicate_check)

        elif trans_type in ("Payment Request", "Maintenance Request"):
            # Non-accounting workflow stages by design — they represent a
            # request/approval step that has not yet become an actual
            # disbursement, so no ledger entries are created for them.
            frappe.logger().info(
                f"{trans_type} is a non-accounting workflow stage — "
                f"no entries created for {self.doc.name}")
            return []

        else:
            frappe.logger().warning(f"Unknown transaction type: {trans_type}")
            return []

    def _validate_before_creation(self):
        if self.doc.trans_type == "Expense Payment" and not self.doc.account_to_debit:
            frappe.throw(_("Account to Debit is required for Expense Payment"))

        if not self.doc.remittance_bank_gl:
            frappe.throw(_("Bank GL Account is required"))

        self._validate_account_not_group(self.doc.remittance_bank_gl)

        if self.doc.account_to_debit:
            self._validate_account_not_group(self.doc.account_to_debit)

    def _validate_account_not_group(self, account):
        if not account:
            return
        if frappe.db.get_value("Account", account, "is_group", cache=True):
            frappe.throw(
                _("The account {0} is a group account and cannot be used for posting").format(account))

    # ── Supplier Payment ────────────────────────────────────────────────────

    def _create_supplier_payment_entries(self, skip_duplicate_check=False):
        frappe.logger().info(f"Creating supplier payment entry for {self.doc.name}")

        if not skip_duplicate_check and self._pe_exists():
            frappe.msgprint(
                _("A Payment Entry already exists for reference {0}.").format(self.doc.reference_no),
                indicator="orange", alert=True)
            return self.created_entries

        pe = frappe.new_doc("Payment Entry")
        pe.payment_type    = "Pay"
        pe.party_type      = "Supplier"
        pe.party           = self.doc.payee_id
        pe.company         = self.doc.company
        pe.posting_date    = self.doc.transaction_date
        pe.mode_of_payment = self.doc.mode_of_payment
        pe.reference_no    = self.doc.reference_no
        pe.reference_date  = self.doc.transaction_date
        pe.paid_from       = self.doc.remittance_bank_gl
        pe.bank_account    = self.doc.remittance_bank
        pe.paid_to         = self._get_payable_account()
        pe.remarks         = self.doc.transaction_purposes or f"Payment to {self.doc.supplier_name}"

        self._set_payment_entry_amounts(pe)
        self._set_accounting_dimensions(pe)

        if self.doc.payments_reference:
            self._add_invoice_references_to_pe(pe)

        pe.flags.ignore_permissions = True
        pe.flags.ignore_fiscal_year = True
        pe.insert(ignore_permissions=True)
        pe.submit()

        self.created_entries.append({'doctype': 'Payment Entry', 'name': pe.name, 'amount': pe.paid_amount})
        frappe.logger().info(f"Payment Entry {pe.name} created")
        frappe.msgprint(_("Payment Entry {0} created").format(pe.name), indicator="green")
        return self.created_entries

    def _get_payable_account(self):
        if not self._cache['payable_account']:
            self._cache['payable_account'] = frappe.db.get_value(
                'Company', self.company, 'default_payable_account', cache=True)
        return self._cache['payable_account']

    def _set_payment_entry_amounts(self, pe):
        amount_paid       = flt(self.doc.amount_paid)
        amount_paid_in_fc = flt(self.doc.amount_paid_in_fc)
        exchange_rate     = flt(self.doc.exchange_rate) or 1

        if self.is_local_currency:
            pe.paid_amount          = amount_paid
            pe.received_amount      = amount_paid
            pe.source_exchange_rate = 1
            pe.target_exchange_rate = 1
        else:
            pe.paid_from_account_currency = self.doc.bank_account_currency
            pe.paid_to_account_currency   = self.doc.payment_currency
            pe.paid_amount                = amount_paid_in_fc
            pe.base_paid_amount           = amount_paid_in_fc * exchange_rate
            pe.received_amount            = amount_paid_in_fc
            pe.base_received_amount       = amount_paid_in_fc * exchange_rate
            pe.source_exchange_rate       = exchange_rate
            pe.target_exchange_rate       = exchange_rate

    def _add_invoice_references_to_pe(self, pe):
        for ref in self.doc.payments_reference:
            if flt(ref.allocated_amount) > 0:
                pe.append('references', {
                    'reference_doctype':  ref.reference_doctype,
                    'reference_name':     ref.reference_name,
                    'due_date':           ref.due_date,
                    'total_amount':       ref.total_amount,
                    'outstanding_amount': ref.outstanding_amount,
                    'allocated_amount':   ref.allocated_amount,
                    'exchange_rate':      flt(ref.exchange_rate) or 1
                })

    # ── Expense Payment ─────────────────────────────────────────────────────

    def _create_expense_payment_entries(self, skip_duplicate_check=False):
        frappe.logger().info(f"Creating expense payment entry for {self.doc.name}")

        if not skip_duplicate_check and self._je_exists(self.doc.reference_no):
            frappe.msgprint(
                _("A Journal Entry already exists for reference {0}.").format(self.doc.reference_no),
                indicator="orange", alert=True)
            return self.created_entries

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
        je = self._init_je("Bank Entry")

        debit_amount  = self._amount_in_local_currency()
        credit_amount = self._amount_for_bank()

        je.append("accounts", {
            "account":                   self.doc.account_to_debit,
            "debit_in_account_currency": debit_amount,
            "debit":                     debit_amount,
            "exchange_rate":             1 if self.is_local_currency else flt(self.doc.exchange_rate),
            "user_remark":               self.doc.transaction_purposes,
            "cost_center":               self.doc.cost_center,
            "project":                   self.doc.project,
            "against_account":           self.doc.remittance_bank_gl
        })
        je.append("accounts", {
            "account":                    self.doc.remittance_bank_gl,
            "credit_in_account_currency": credit_amount,
            "credit":                     debit_amount,
            "exchange_rate":              flt(self.doc.exchange_rate) if not self.is_local_currency else 1,
            "user_remark":                self.doc.transaction_purposes,
            "bank_account":               self.doc.remittance_bank,
            "against_account":            self.doc.account_to_debit
        })

        return self._submit_je(je)

    def _create_expense_entry_with_wht(self):
        je = self._init_je("Bank Entry")

        base_amount   = self._amount_in_local_currency()
        wht_amount    = flt(self.doc.wht_amount)
        net_amount    = flt(self.doc.net_amount)
        exchange_rate = flt(self.doc.exchange_rate) or 1

        self._validate_account_not_group(self.doc.wht_account)

        je.append("accounts", {
            "account":                   self.doc.account_to_debit,
            "debit_in_account_currency": base_amount,
            "debit":                     base_amount,
            "exchange_rate":             1,
            "user_remark":               self.doc.transaction_purposes,
            "cost_center":               self.doc.cost_center,
            "project":                   self.doc.project,
            "against_account":           f"{self.doc.remittance_bank_gl}, {self.doc.wht_account}"
        })
        je.append("accounts", {
            "account":                    self.doc.wht_account,
            "credit_in_account_currency": wht_amount,
            "credit":                     wht_amount,
            "exchange_rate":              1,
            "user_remark":                f"WHT @ {flt(self.doc.whtax_rate)}% on {self.doc.transaction_purposes}",
            "cost_center":                self.doc.cost_center,
            "against_account":            self.doc.account_to_debit
        })

        bank_credit = net_amount if self.is_local_currency else (net_amount / exchange_rate)
        je.append("accounts", {
            "account":                    self.doc.remittance_bank_gl,
            "credit_in_account_currency": bank_credit,
            "credit":                     net_amount,
            "exchange_rate":              exchange_rate if not self.is_local_currency else 1,
            "user_remark":                self.doc.transaction_purposes,
            "bank_account":               self.doc.remittance_bank,
            "against_account":            self.doc.account_to_debit
        })

        return self._submit_je(je)

    def _create_multi_line_expense_entry(self):
        je = self._init_je("Bank Entry")

        total_debit      = 0
        against_accounts = []

        for item in self.doc.payments_item_line:
            if not item.gl_account or not flt(item.amount):
                continue

            self._validate_account_not_group(item.gl_account)

            item_exch_rate = flt(item.exch_rate) or flt(self.doc.exchange_rate) or 1
            item_amount    = flt(item.amount)
            amount_in_lc   = item_amount if self.is_local_currency else (item_amount * item_exch_rate)
            total_debit   += amount_in_lc
            against_accounts.append(item.gl_account)

            je.append("accounts", {
                "account":                   item.gl_account,
                "debit_in_account_currency": amount_in_lc,
                "debit":                     amount_in_lc,
                "exchange_rate":             item_exch_rate,
                "user_remark":               item.description or self.doc.transaction_purposes,
                "cost_center":               item.cost_center,
                "project":                   item.project,
                "against_account":           self.doc.remittance_bank_gl
            })

        credit_amount = self._amount_for_bank()
        je.append("accounts", {
            "account":                    self.doc.remittance_bank_gl,
            "credit_in_account_currency": credit_amount,
            "credit":                     total_debit,
            "exchange_rate":              flt(self.doc.exchange_rate) if not self.is_local_currency else 1,
            "user_remark":                self.doc.transaction_purposes,
            "bank_account":               self.doc.remittance_bank,
            "against_account":            ", ".join(against_accounts)
        })

        return self._submit_je(je)

    def _create_shared_cost_entry(self):
        if not self.doc.cost_center_distribution:
            frappe.throw(_("Cost center distribution is required for shared cost allocation"))

        total_pct = sum(flt(d.distribution) for d in self.doc.cost_center_distribution)
        if abs(total_pct - 100) > 0.01:
            frappe.throw(
                _("Total cost center distribution must equal 100%. Current total: {0}%").format(total_pct))

        je          = self._init_je("Bank Entry")
        base_amount = self._amount_in_local_currency()
        total_alloc = 0

        for idx, dist in enumerate(self.doc.cost_center_distribution, 1):
            allocated = (base_amount * flt(dist.distribution)) / 100
            total_alloc += allocated

            je.append("accounts", {
                "account":                   self.doc.account_to_debit,
                "debit_in_account_currency": allocated,
                "debit":                     allocated,
                "exchange_rate":             1,
                "user_remark":               f"{dist.cost_center} ({flt(dist.distribution)}%): {self.doc.transaction_purposes}",
                "cost_center":               dist.cost_center,
                "project":                   self.doc.project,
                "against_account":           self.doc.remittance_bank_gl
            })

        if abs(total_alloc - base_amount) > 0.01:
            frappe.msgprint(
                _("Warning: Allocated amount ({0}) differs from payment amount ({1}) due to rounding.").format(
                    total_alloc, base_amount),
                indicator='orange', alert=True)

        credit_amount = self._amount_for_bank()
        je.append("accounts", {
            "account":                    self.doc.remittance_bank_gl,
            "credit_in_account_currency": credit_amount,
            "credit":                     base_amount,
            "exchange_rate":              flt(self.doc.exchange_rate) if not self.is_local_currency else 1,
            "user_remark":                self.doc.transaction_purposes,
            "bank_account":               self.doc.remittance_bank,
            "against_account":            self.doc.account_to_debit
        })

        return self._submit_je(je)

    def _create_related_company_entries(self):
        if not self.doc.related_company_payments:
            return self.created_entries

        entries = []
        errors  = []

        for idx, rc in enumerate(self.doc.related_company_payments, 1):
            err = self._validate_rc_row(rc, idx)
            if err:
                errors.append(err)
                continue

            rc_cheque_no = f"{self.doc.reference_no}-RC{idx}"

            if self._je_exists(rc_cheque_no):
                errors.append(
                    _("Row {0}: Journal Entry already exists for {1}. Skipped.").format(idx, rc_cheque_no))
                continue

            try:
                je_name = self._create_single_rc_entry(rc, idx)
                if je_name:
                    entries.append({'doctype': 'Journal Entry', 'name': je_name,
                                    'company': rc.company,
                                    'amount': flt(rc.amount_in_lcy) or flt(rc.amount)})
            except Exception as e:
                errors.append(f"Row {idx}: {str(e)}")
                frappe.log_error(frappe.get_traceback(), f"Related Company Entry Error - Row {idx}")

        if entries:
            self.created_entries.extend(entries)
            frappe.msgprint(
                _("Created {0} related company entries.").format(len(entries)), indicator="green")

        if errors:
            frappe.msgprint(
                _("Warnings ({0}):").format(len(errors)) + "<br>" + "<br>".join(errors[:5]),
                indicator="orange", title=_("Partial Success"))

        return self.created_entries

    def _validate_rc_row(self, rc, row_num):
        if not rc.company:
            return _("Row {0}: Company is required").format(row_num)
        if not rc.party:
            return _("Row {0}: Account/Party is required").format(row_num)
        if not flt(rc.amount) or flt(rc.amount) <= 0:
            return _("Row {0}: Amount must be greater than zero").format(row_num)
        if not rc.related_company_account:
            return _("Row {0}: Related Company Account is required").format(row_num)
        if not frappe.db.exists('Account', rc.party):
            return _("Row {0}: Account '{1}' does not exist").format(row_num, rc.party)
        if not frappe.db.exists('Account', rc.related_company_account):
            return _("Row {0}: Related Company Account '{1}' does not exist").format(
                row_num, rc.related_company_account)
        if frappe.db.get_value('Account', rc.party, 'is_group'):
            return _("Row {0}: '{1}' is a group account").format(row_num, rc.party)
        if frappe.db.get_value('Account', rc.related_company_account, 'is_group'):
            return _("Row {0}: '{1}' is a group account").format(row_num, rc.related_company_account)
        if not frappe.db.exists('Company', rc.company):
            return _("Row {0}: Company '{1}' does not exist").format(row_num, rc.company)
        return None

    def _create_single_rc_entry(self, rc, row_num):
        je = frappe.new_doc("Journal Entry")
        je.voucher_type  = "Bank Entry"
        je.payee_name    = self.doc.payee_name or self.doc.supplier_name
        je.company       = rc.company
        je.posting_date  = self.doc.transaction_date
        je.cheque_no     = f"{self.doc.reference_no}-RC{row_num}"
        je.cheque_date   = self.doc.transaction_date
        je.user_remark   = rc.remark or self.doc.transaction_purposes or "Related Company Payment"
        je.multi_currency = 1 if not self.is_local_currency else 0

        amount     = flt(rc.amount_in_lcy) or flt(rc.amount)
        exch_rate  = flt(getattr(rc, 'exch_rate', None)) or flt(self.doc.exchange_rate) or 1

        je.append("accounts", {
            "account":                   rc.party,
            "debit_in_account_currency": amount,
            "debit":                     amount,
            "exchange_rate":             exch_rate,
            "cost_center":               rc.cost_center,
            "project":                   getattr(rc, 'project', None) or self.doc.project,
            "user_remark":               rc.remark or self.doc.transaction_purposes,
            "against_account":           rc.related_company_account
        })
        je.append("accounts", {
            "account":                    rc.related_company_account,
            "credit_in_account_currency": amount,
            "credit":                     amount,
            "exchange_rate":              exch_rate,
            "cost_center":                rc.cost_center,
            "user_remark":                rc.remark or f"Related company payment - {self.doc.name}",
            "against_account":            rc.party
        })

        je.set_total_debit_credit()
        je.flags.ignore_permissions = True
        je.flags.ignore_fiscal_year = True
        je.insert(ignore_permissions=True)
        je.submit()
        return je.name

    # ── Transfer Out ────────────────────────────────────────────────────────

    def _create_transfer_out_entries(self, skip_duplicate_check=False):
        frappe.logger().info(f"Creating transfer out entry for {self.doc.name}")

        if not skip_duplicate_check and self._je_exists(self.doc.reference_no):
            frappe.msgprint(
                _("A Journal Entry already exists for reference {0}.").format(self.doc.reference_no),
                indicator="orange", alert=True)
            return self.created_entries

        interbank_account = self._get_interbank_account()
        self._validate_account_not_group(interbank_account)

        je            = self._init_je("Bank Entry")
        transfer_amt  = self._amount_in_local_currency()
        credit_amt    = self._amount_for_bank()

        je.append("accounts", {
            "account":                   interbank_account,
            "debit_in_account_currency": transfer_amt,
            "debit":                     transfer_amt,
            "exchange_rate":             1,
            "user_remark":               f"Transfer from {self.doc.remittance_bank}: {self.doc.transaction_purposes}",
            "against_account":           self.doc.remittance_bank_gl
        })
        je.append("accounts", {
            "account":                    self.doc.remittance_bank_gl,
            "credit_in_account_currency": credit_amt,
            "credit":                     transfer_amt,
            "exchange_rate":              flt(self.doc.exchange_rate) if not self.is_local_currency else 1,
            "user_remark":                self.doc.transaction_purposes,
            "bank_account":               self.doc.remittance_bank,
            "against_account":            interbank_account
        })

        return self._submit_je(je)

    def _get_interbank_account(self):
        if not self._cache['interbank_account']:
            self._cache['interbank_account'] = (
                frappe.db.get_value('Company', self.company, 'custom_default_interbank_transfer', cache=True)
                or self.doc.account_to_debit
            )
        return self._cache['interbank_account']

    # ── Supplier Refund ─────────────────────────────────────────────────────

    def _create_supplier_refund_entries(self, skip_duplicate_check=False):
        frappe.logger().info(f"Creating supplier refund entry for {self.doc.name}")

        if not skip_duplicate_check and self._je_exists(self.doc.reference_no):
            frappe.msgprint(
                _("A Journal Entry already exists for reference {0}.").format(self.doc.reference_no),
                indicator="orange", alert=True)
            return self.created_entries

        je            = self._init_je("Bank Entry")
        refund_amt    = self._amount_in_local_currency()
        debit_amt     = self._amount_for_bank()
        payable_acct  = self._get_payable_account()

        je.append("accounts", {
            "account":                   self.doc.remittance_bank_gl,
            "debit_in_account_currency": debit_amt,
            "debit":                     refund_amt,
            "exchange_rate":             flt(self.doc.exchange_rate) if not self.is_local_currency else 1,
            "user_remark":               f"Refund from {self.doc.supplier_name}: {self.doc.transaction_purposes}",
            "bank_account":              self.doc.remittance_bank,
            "against_account":           payable_acct
        })
        je.append("accounts", {
            "account":                    payable_acct,
            "party_type":                 "Supplier",
            "party":                      self.doc.payee_id,
            "credit_in_account_currency": refund_amt,
            "credit":                     refund_amt,
            "exchange_rate":              1,
            "user_remark":                self.doc.transaction_purposes,
            "against_account":            self.doc.remittance_bank_gl
        })

        return self._submit_je(je)

    # ── Shared helpers ───────────────────────────────────────────────────────

    def _init_je(self, voucher_type="Bank Entry"):
        je = frappe.new_doc("Journal Entry")
        je.voucher_type             = voucher_type
        je.payee_name               = self.doc.payee_name or self.doc.supplier_name
        je.company                  = self.company
        je.posting_date             = self.doc.transaction_date
        je.cheque_no                = self.doc.reference_no
        je.cheque_date              = self.doc.transaction_date
        je.user_remark              = self.doc.transaction_purposes
        je.paid_to_or_received_from = self.doc.payee_name or self.doc.supplier_name
        je.multi_currency           = 1 if not self.is_local_currency else 0
        return je

    def _amount_in_local_currency(self):
        if self.is_local_currency:
            return flt(self.doc.amount_paid)
        return flt(self.doc.amount_paid_in_fc) * (flt(self.doc.exchange_rate) or 1)

    def _amount_for_bank(self):
        if self.is_local_currency:
            return flt(self.doc.amount_paid)
        return flt(self.doc.amount_paid_in_fc)

    def _set_accounting_dimensions(self, doc):
        for field in ['cost_center', 'project', 'department', 'branch']:
            val = getattr(self.doc, field, None)
            if val:
                setattr(doc, field, val)

    def _submit_je(self, je):
        """Save and submit a Journal Entry. No duplicate guard here — callers handle that."""
        je.set_total_debit_credit()
        je.flags.ignore_permissions = True
        je.flags.ignore_fiscal_year = True
        je.insert(ignore_permissions=True)
        je.submit()

        self.created_entries.append({
            'doctype': 'Journal Entry',
            'name':    je.name,
            'amount':  je.total_debit
        })
        frappe.logger().info(f"Journal Entry {je.name} created and submitted")
        frappe.msgprint(_("Journal Entry {0} created").format(je.name), indicator="green")
        return self.created_entries

    def get_created_entries_summary(self):
        return {
            'total_entries': len(self.created_entries),
            'entries':       self.created_entries
        }


# ==================== AccountingEntryCanceller ====================

class AccountingEntryCanceller:

    def __init__(self, payment_doc):
        self.doc               = payment_doc
        self.cancelled_entries = []

    def cancel_all_entries(self):
        frappe.logger().info(f"Cancelling accounting entries for {self.doc.name}")
        self._cancel_journal_entries()
        self._cancel_payment_entries()

        if self.cancelled_entries:
            frappe.msgprint(
                _("Cancelled {0} accounting entries").format(len(self.cancelled_entries)),
                indicator="orange")

        return self.cancelled_entries

    def _cancel_journal_entries(self):
        je_list = frappe.db.sql("""
            SELECT name FROM `tabJournal Entry`
            WHERE (cheque_no = %s OR cheque_no LIKE %s)
              AND company = %s AND docstatus = 1
            LIMIT 50
        """, (self.doc.reference_no, f"{self.doc.reference_no}-RC%", self.doc.company), as_dict=1)

        for je in je_list:
            try:
                frappe.get_doc('Journal Entry', je.name).cancel()
                self.cancelled_entries.append({'doctype': 'Journal Entry', 'name': je.name, 'status': 'Cancelled'})
            except Exception as e:
                frappe.log_error(frappe.get_traceback(), f"Error cancelling JE {je.name}")
                self.cancelled_entries.append({'doctype': 'Journal Entry', 'name': je.name, 'status': 'Error', 'error': str(e)})

    def _cancel_payment_entries(self):
        pe_list = frappe.db.get_all('Payment Entry',
            filters={'reference_no': self.doc.reference_no, 'company': self.doc.company, 'docstatus': 1},
            fields=['name'], limit=50)

        for pe in pe_list:
            try:
                frappe.get_doc('Payment Entry', pe.name).cancel()
                self.cancelled_entries.append({'doctype': 'Payment Entry', 'name': pe.name, 'status': 'Cancelled'})
            except Exception as e:
                frappe.log_error(frappe.get_traceback(), f"Error cancelling PE {pe.name}")
                self.cancelled_entries.append({'doctype': 'Payment Entry', 'name': pe.name, 'status': 'Error', 'error': str(e)})


# ==================== Payment Notifications (merged from payments_utils.py) ====

class PaymentNotifier:
    """Handle payment email notifications."""

    @staticmethod
    def send_approval_notification(payment_doc):
        """Send notification for payment approval."""
        try:
            approvers = PaymentNotifier._get_approvers()

            if not approvers:
                return

            message = f"""
            <h3>Payment Approval Required</h3>
            <p><b>Payment No:</b> {payment_doc.name}</p>
            <p><b>Payee:</b> {payment_doc.payee_name or payment_doc.supplier_name}</p>
            <p><b>Amount:</b> {_format_currency_display(payment_doc.amount_paid or payment_doc.amount_paid_in_fc, payment_doc.payment_currency)}</p>
            <p><b>Purpose:</b> {payment_doc.transaction_purposes}</p>
            <p><a href="{get_url_to_form('Payments', payment_doc.name)}">Click here to review</a></p>
            """

            frappe.sendmail(
                recipients=approvers,
                subject=f"Payment Approval Required - {payment_doc.name}",
                message=message
            )

        except Exception:
            frappe.log_error(frappe.get_traceback(), "Payment Approval Notification Error")

    @staticmethod
    def send_payment_confirmation(payment_doc):
        """Send payment confirmation notification."""
        try:
            recipients = [payment_doc.issued_by] if payment_doc.issued_by else []
            if payment_doc.authorised_by:
                recipients.append(payment_doc.authorised_by)

            if not recipients:
                return

            message = f"""
            <h3>Payment Processed Successfully</h3>
            <p><b>Payment No:</b> {payment_doc.name}</p>
            <p><b>Payee:</b> {payment_doc.payee_name or payment_doc.supplier_name}</p>
            <p><b>Amount:</b> {_format_currency_display(payment_doc.amount_paid or payment_doc.amount_paid_in_fc, payment_doc.payment_currency)}</p>
            <p><b>Reference:</b> {payment_doc.reference_no}</p>
            <p><b>Date:</b> {payment_doc.transaction_date}</p>
            """

            frappe.sendmail(
                recipients=recipients,
                subject=f"Payment Processed - {payment_doc.name}",
                message=message
            )

        except Exception:
            frappe.log_error(frappe.get_traceback(), "Payment Confirmation Notification Error")

    @staticmethod
    def _get_approvers():
        """Get list of users holding the Accounts Manager role."""
        users = frappe.get_all('Has Role',
            filters={'role': 'Accounts Manager', 'parenttype': 'User'},
            fields=['parent'])
        return list({u.parent for u in users})


def _format_currency_display(amount, currency):
    """Small display helper — not a substitute for fmt_money, just used
    inline in notification HTML where a Currency-object isn't available."""
    if not amount:
        amount = 0
    return fmt_money(flt(amount), currency=currency)


# ==================== Duplicate & Balance Checks (merged from payments_utils.py) ==

def check_duplicate_payment(supplier, amount, transaction_date, current_doc=None):
    """Check for potential duplicate payments to the same supplier for the
    same amount within a 7-day window either side of transaction_date."""
    date_from = add_days(transaction_date, -7)
    date_to   = add_days(transaction_date, 7)

    filters = {
        'payee_id': supplier,
        'amount_paid': amount,
        'transaction_date': ['between', [date_from, date_to]],
        'docstatus': ['!=', 2]
    }

    if current_doc:
        filters['name'] = ['!=', current_doc]

    duplicates = frappe.get_all('Payments',
        filters=filters,
        fields=['name', 'transaction_date', 'reference_no'])

    if duplicates:
        return {'is_duplicate': True, 'possible_duplicates': duplicates}

    return {'is_duplicate': False}


def validate_bank_balance(bank_account, amount, transaction_date):
    """Advisory check — does NOT block submission. Returns a dict the
    caller can use to show a warning."""
    try:
        account = frappe.db.get_value('Bank Account', bank_account, 'account')
        if not account:
            return {'valid': True}

        balance = frappe.db.sql("""
            SELECT SUM(debit_in_account_currency - credit_in_account_currency) as balance
            FROM `tabGL Entry`
            WHERE account = %(account)s
              AND posting_date <= %(date)s
              AND is_cancelled = 0
        """, {'account': account, 'date': transaction_date}, as_dict=1)

        current_balance = flt(balance[0].balance) if balance else 0

        if current_balance < flt(amount):
            return {
                'valid': False,
                'message': _("Bank account balance ({0}) may be insufficient for this payment ({1}).").format(
                    fmt_money(current_balance), fmt_money(amount)),
                'balance': current_balance
            }

        return {'valid': True, 'balance': current_balance}

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Bank Balance Check Error")
        return {'valid': True, 'message': "Could not verify balance"}


# ==================== Payments Document Class ====================

class Payments(Document):

    def validate(self):
        self.validate_required_fields()
        self.validate_amounts()
        self.validate_dates()
        self.validate_accounts()
        self.validate_cost_center_distribution()
        self.validate_related_company_payments()
        self.calculate_totals()
        self.set_amount_in_words()
        self.warn_on_possible_duplicate()

    def validate_required_fields(self):
        if not self.trans_type:
            frappe.throw(_("Transaction Type is required"))
        if not self.company:
            frappe.throw(_("Company is required"))
        if not self.transaction_date:
            frappe.throw(_("Transaction Date is required"))
        if not self.reference_no:
            frappe.throw(_("Reference Number is required"))

    def validate_amounts(self):
        company_currency = frappe.db.get_value('Company', self.company, 'default_currency', cache=True)
        if not company_currency:
            frappe.throw(_("Company currency not found for {0}").format(self.company))

        amount_paid       = flt(self.amount_paid)
        amount_paid_in_fc = flt(self.amount_paid_in_fc)
        exchange_rate     = flt(self.exchange_rate)
        whtax_rate        = flt(self.whtax_rate)

        amount = amount_paid if self.payment_currency == company_currency else amount_paid_in_fc
        if not amount or amount <= 0:
            frappe.throw(_("Payment amount must be greater than zero"))

        if self.payment_currency != company_currency:
            if not exchange_rate or exchange_rate <= 0:
                frappe.throw(_("Exchange rate must be greater than zero"))
            self.local_currency_amount = amount_paid_in_fc * exchange_rate
        else:
            self.local_currency_amount = amount_paid

        if self.deduct_wht:
            if not whtax_rate or whtax_rate <= 0:
                frappe.throw(_("WHT rate is required when deducting WHT"))
            self.wht_amount = (flt(self.local_currency_amount) * whtax_rate) / 100
            self.net_amount = flt(self.local_currency_amount) - self.wht_amount
        else:
            self.wht_amount = 0
            self.net_amount = flt(self.local_currency_amount)

    def validate_dates(self):
        if self.transaction_date and getdate(self.transaction_date) > getdate(nowdate()):
            frappe.throw(_("Transaction date cannot be in the future"))

        if self.amortize:
            if not self.start_date or not self.end_date:
                frappe.throw(_("Start date and end date are required for amortization"))
            if getdate(self.end_date) <= getdate(self.start_date):
                frappe.throw(_("End date must be after start date"))

    def validate_accounts(self):
        if self.trans_type in ['Expense Payment', 'Transfer Out'] and not self.account_to_debit:
            frappe.throw(_("Account to Debit is required for {0}").format(self.trans_type))
        if self.deduct_wht and not self.wht_account:
            frappe.throw(_("WHT Account is required when deducting WHT"))
        if self.remittance_bank and not frappe.db.exists('Bank Account', self.remittance_bank):
            frappe.throw(_("Bank Account {0} not found").format(self.remittance_bank))

        # fetch_from (remittance_bank.account -> remittance_bank_gl, and
        # remittance_bank.account_currency -> bank_account_currency) is a
        # CLIENT-SIDE mechanism — it only runs when a user changes the
        # remittance_bank field on the form. Documents created via the
        # bulk importer, the API, or any script never get it populated,
        # which then makes _validate_before_creation() throw "Bank GL
        # Account is required" during on_submit — silently blocking
        # Journal Entry / Payment Entry creation with no obvious cause.
        # Fetching it here server-side, unconditionally, closes that gap
        # regardless of how the document was created.
        if self.remittance_bank:
            bank_account = frappe.db.get_value(
                'Bank Account', self.remittance_bank,
                ['account', 'account_currency'], as_dict=True)
            if bank_account:
                if not self.remittance_bank_gl:
                    self.remittance_bank_gl = bank_account.account
                if not self.bank_account_currency:
                    self.bank_account_currency = bank_account.account_currency

    def validate_cost_center_distribution(self):
        if not self.is_shared_cost:
            return
        if not self.cost_center_distribution:
            frappe.throw(_("Cost center distribution is required when 'Is Shared Cost' is enabled"))

        total_pct = sum(flt(r.distribution) for r in self.cost_center_distribution)
        if abs(total_pct - 100) > 0.01:
            frappe.throw(
                _("Total cost center distribution must equal 100%. Current total: {0}%").format(
                    round(total_pct, 2)))

        for idx, row in enumerate(self.cost_center_distribution, 1):
            if not row.cost_center:
                frappe.throw(_("Row {0}: Cost Center is required").format(idx))
            dist_val = flt(row.distribution)
            if not dist_val or dist_val <= 0:
                frappe.throw(_("Row {0}: Distribution percentage must be greater than zero").format(idx))
            if dist_val > 100:
                frappe.throw(_("Row {0}: Distribution percentage cannot exceed 100%").format(idx))
            if not frappe.db.exists('Cost Center', row.cost_center):
                frappe.throw(_("Row {0}: Cost Center '{1}' does not exist").format(idx, row.cost_center))
            if frappe.db.get_value('Cost Center', row.cost_center, 'disabled'):
                frappe.throw(_("Row {0}: Cost Center '{1}' is disabled").format(idx, row.cost_center))

    def validate_related_company_payments(self):
        if not self.is_related_coy_trans:
            return
        if not self.related_company_payments:
            frappe.throw(
                _("Related company payment details are required when 'Is Related Company Transaction' is enabled"))

        total_amount = 0
        for idx, row in enumerate(self.related_company_payments, 1):
            if not row.company:
                frappe.throw(_("Row {0}: Company is required").format(idx))
            if not row.party:
                frappe.throw(_("Row {0}: Account/Party is required").format(idx))
            row_amount = flt(row.amount)
            if not row_amount or row_amount <= 0:
                frappe.throw(_("Row {0}: Amount must be greater than zero").format(idx))
            if not row.related_company_account:
                frappe.throw(_("Row {0}: Related Company Account is required").format(idx))
            if not frappe.db.exists('Company', row.company):
                frappe.throw(_("Row {0}: Company '{1}' does not exist").format(idx, row.company))
            if not frappe.db.exists('Account', row.party):
                frappe.throw(_("Row {0}: Account '{1}' does not exist").format(idx, row.party))
            if not frappe.db.exists('Account', row.related_company_account):
                frappe.throw(_("Row {0}: Account '{1}' does not exist").format(idx, row.related_company_account))
            if frappe.db.get_value('Account', row.party, 'is_group'):
                frappe.throw(_("Row {0}: '{1}' is a group account").format(idx, row.party))
            if frappe.db.get_value('Account', row.related_company_account, 'is_group'):
                frappe.throw(_("Row {0}: '{1}' is a group account").format(idx, row.related_company_account))
            if row.cost_center:
                if not frappe.db.exists('Cost Center', row.cost_center):
                    frappe.throw(_("Row {0}: Cost Center '{1}' does not exist").format(idx, row.cost_center))
                if frappe.db.get_value('Cost Center', row.cost_center, 'disabled'):
                    frappe.throw(_("Row {0}: Cost Center '{1}' is disabled").format(idx, row.cost_center))
            total_amount += flt(row.amount_in_lcy or row.amount)

        payment_amount = flt(self.local_currency_amount) or flt(self.amount_paid)
        if abs(total_amount - payment_amount) > 0.01:
            frappe.msgprint(
                _("Warning: Total related company amount ({0}) does not match payment amount ({1})").format(
                    total_amount, payment_amount),
                indicator='orange', alert=True)

    def calculate_totals(self):
        if self.payments_reference:
            self.total_outstanding_invoice = sum(
                flt(r.allocated_amount) for r in self.payments_reference)
        if self.payments_item_line:
            self.total_multi_line_amount = sum(
                flt(r.amount_in_lcy or r.amount) for r in self.payments_item_line)
        if self.cost_center_distribution:
            self.total_percentage = sum(
                flt(r.distribution) for r in self.cost_center_distribution)
        if self.related_company_payments:
            self.total_rcoy = sum(
                flt(r.amount_in_lcy or r.amount) for r in self.related_company_payments)

    def set_amount_in_words(self):
        if self.local_currency_amount:
            company_currency = frappe.db.get_value(
                'Company', self.company, 'default_currency', cache=True) or 'NGN'
            self.amount_in_words = money_in_words(flt(self.local_currency_amount), company_currency)

    def warn_on_possible_duplicate(self):
        """Advisory only — never blocks save. Only meaningful for Supplier
        Payment, where payee_id + amount_paid give a reliable fingerprint."""
        if self.trans_type != 'Supplier Payment' or not self.payee_id or not self.amount_paid:
            return
        if not self.transaction_date:
            return

        result = check_duplicate_payment(
            self.payee_id, self.amount_paid, self.transaction_date,
            current_doc=self.name if not self.is_new() else None)

        if result.get('is_duplicate'):
            names = ", ".join(d.name for d in result['possible_duplicates'])
            frappe.msgprint(
                _("Possible duplicate payment: a payment of the same amount to this "
                  "supplier already exists within 7 days ({0}). Please verify before proceeding.").format(names),
                indicator='orange', alert=True)

    def before_submit(self):
        """
        Accounting entries are created HERE, before docstatus is ever set
        to 1 — not in on_submit. Two reasons:

        1. If entry creation fails, this raises before the docstatus write
           happens at all, so there's no "was it really rolled back"
           question — the submit simply never got that far.
        2. before_submit is where it's natural to guard against creating a
           SECOND set of entries if a submit attempt is retried (e.g. the
           first attempt failed here, the underlying issue got fixed, and
           the user clicks Submit again) — accounting_entries_exist() is
           checked first, and if entries already exist for this reference,
           we skip straight past creation instead of duplicating them.
        """
        # ── Auto-code account_to_debit before any validation runs ────────────
        # If this is an Expense Payment with no account set, the engine will
        # attempt to match transaction_purposes against the coding rules
        # and populate account_to_debit in-place.  If it fails, it throws a
        # clear, actionable message instead of the generic validation error.
        _attempt_auto_coding_if_needed(self)

        # ── Accounting entries — hard requirement, created pre-submit ────────
        if self.create_accounting_entries:
            controller = PaymentAccountingController(self)

            if controller.accounting_entries_exist():
                # Idempotency guard: don't create a duplicate set if a prior
                # attempt (or the manual "Create Journal/Payment Entry"
                # button) already produced real entries for this reference.
                frappe.msgprint(
                    _("Accounting entries already exist for reference {0} — "
                      "skipping creation to avoid duplicates.").format(self.reference_no),
                    indicator="blue", alert=True)
            else:
                created = controller.create_accounting_entries(skip_duplicate_check=False)

                entries_expected = self.trans_type not in ("Payment Request", "Maintenance Request")
                if entries_expected and not created:
                    frappe.throw(
                        _("Submission blocked: no accounting entries were created for "
                          "this payment, and none were expected to be skipped for "
                          "trans_type '{0}'. Fix the underlying issue and try again — "
                          "this Payments app only allows a payment to submit once its "
                          "Journal Entry / Payment Entry actually exists.").format(self.trans_type),
                        title=_("Accounting Entries Required")
                    )

                frappe.logger().info(f"Created {len(created)} accounting entries for {self.name}")
                # Any exception raised inside create_accounting_entries() above
                # (missing Bank GL Account, group account used for posting,
                # WHT account misconfigured, etc.) is intentionally NOT caught
                # here — it propagates out of before_submit, which stops
                # docstatus from ever being set to 1.
        else:
            # Checkbox is a deliberate opt-out, not a failure.
            frappe.msgprint(
                _("'Create Accounting Entries' is unchecked — this payment will submit "
                  "without a Journal Entry or Payment Entry."),
                indicator="blue", title=_("Accounting Entries Skipped")
            )

        self.payment_status = 'Pending'

    def on_submit(self):
        """
        Accounting entries are handled in before_submit() now — see that
        method's docstring. By the time on_submit runs, docstatus is
        already 1 and, if create_accounting_entries was checked, a real
        Journal Entry / Payment Entry is guaranteed to already exist
        (before_submit would have raised and blocked the submit otherwise).
        This method only handles the parts that are fine to be best-effort
        post-submission: amortization posting, final status, and the
        confirmation email.
        """
        frappe.logger().info(f"Payment {self.name} submitted")

        # ── Amortization — stays best-effort/non-blocking ─────────────────────
        # Deliberately kept separate from the hard requirement in
        # before_submit: amortization posts a whole schedule of future-dated
        # entries in one go, which is a distinct concern from "was this
        # payment itself posted", and failing it shouldn't undo an
        # otherwise-valid payment submission with its Journal/Payment Entry
        # already correctly created.
        if self.amortize and self.amortization_schedule:
            amort_savepoint = f"payment_amortization_{self.name}".replace("-", "_")
            frappe.db.savepoint(amort_savepoint)
            try:
                create_all_amortization_entries(self)
            except Exception as e:
                frappe.db.rollback(save_point=amort_savepoint)
                frappe.log_error(frappe.get_traceback(), f"Amortization Error - {self.name}")
                frappe.msgprint(
                    _("⚠ Amortization entries failed: {0}").format(str(e)),
                    indicator="orange"
                )

        # ── Mark completed ───────────────────────────────────────────────────
        # Only reached if accounting entries succeeded (or were deliberately
        # skipped via the checkbox) — any hard failure above already raised
        # and aborted before this point.
        try:
            self.db_set('payment_status', 'Completed')
        except Exception:
            pass

        # ── Confirmation email (best-effort, never blocks submit) ────────────
        try:
            PaymentNotifier.send_payment_confirmation(self)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"Payment Confirmation Email Error - {self.name}")

    def on_cancel(self):
        frappe.logger().info(f"Cancelling Payment {self.name}")
        try:
            AccountingEntryCanceller(self).cancel_all_entries()
            cancel_amortization_entries(self)
            self.db_set('payment_status', 'Cancelled')
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"Payment Cancellation Error - {self.name}")
            frappe.throw(_("Error during cancellation: {0}").format(str(e)))


# ==================== Amortization Functions ====================

def create_all_amortization_entries(payment_doc):
    try:
        if not payment_doc.amortization_schedule:
            return

        created = []
        for entry in payment_doc.amortization_schedule:
            if not entry.journal_entry:
                je_name = create_single_amortization_entry(payment_doc, entry)
                if je_name:
                    created.append(je_name)

        if created:
            payment_doc.db_set('amortization_status', 'Completed')
            frappe.msgprint(
                _("Created {0} amortization journal entries").format(len(created)),
                indicator='green', alert=True)

        return created

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Amortization Creation Error")
        frappe.throw(_("Failed to create amortization entries: {0}").format(str(e)))


def create_single_amortization_entry(payment_doc, schedule_entry):
    try:
        if not payment_doc.expense_account or not payment_doc.deferred_expense_account:
            frappe.throw(
                _("Expense Account and Deferred Expense Account are required for amortization"))

        je = frappe.new_doc("Journal Entry")
        je.voucher_type = "Journal Entry"
        je.payee_name   = payment_doc.payee_name or payment_doc.supplier_name
        je.company      = payment_doc.company
        je.posting_date = schedule_entry.period_start
        je.user_remark  = (
            f"Amortization for {payment_doc.name} - "
            f"Period {schedule_entry.period_start} to {schedule_entry.period_end}"
        )

        entry_amount = flt(schedule_entry.amount)

        je.append("accounts", {
            "account":                   payment_doc.expense_account,
            "debit_in_account_currency": entry_amount,
            "debit":                     entry_amount,
            "cost_center":               payment_doc.cost_center,
            "project":                   payment_doc.project,
            "user_remark":               f"Amortization expense for {schedule_entry.period_start}",
            "against_account":           payment_doc.deferred_expense_account
        })
        je.append("accounts", {
            "account":                    payment_doc.deferred_expense_account,
            "credit_in_account_currency": entry_amount,
            "credit":                     entry_amount,
            "cost_center":                payment_doc.cost_center,
            "project":                    payment_doc.project,
            "user_remark":                f"Deferred expense amortization for {schedule_entry.period_start}",
            "against_account":            payment_doc.expense_account
        })

        je.set_total_debit_credit()
        je.flags.ignore_permissions = True
        je.flags.ignore_fiscal_year = True
        je.insert(ignore_permissions=True)
        je.submit()

        frappe.db.set_value('Schedule of Prepayments', schedule_entry.name, {
            'journal_entry': je.name,
            'je_status':     'Posted'
        })

        return je.name

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"Amortization Entry Error - {schedule_entry.name}")
        return None


def cancel_amortization_entries(payment_doc):
    try:
        schedule_entries = frappe.db.get_all('Schedule of Prepayments',
            filters={'parent': payment_doc.name, 'parenttype': 'Payments',
                     'journal_entry': ['is', 'set']},
            fields=['name', 'journal_entry'], limit=100)

        cancelled_count = 0
        for entry in schedule_entries:
            if entry.journal_entry:
                try:
                    je = frappe.get_doc('Journal Entry', entry.journal_entry)
                    if je.docstatus == 1:
                        je.cancel()
                        cancelled_count += 1
                    frappe.db.set_value('Schedule of Prepayments', entry.name,
                                        {'journal_entry': None, 'je_status': 'Cancelled'})
                except Exception:
                    frappe.log_error(frappe.get_traceback(),
                                     f"Error cancelling amortization {entry.journal_entry}")

        if cancelled_count:
            payment_doc.db_set('amortization_status', 'Not Started')
            frappe.msgprint(
                _("Cancelled {0} amortization journal entries").format(cancelled_count),
                indicator='orange', alert=True)

        return cancelled_count

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Amortization Cancellation Error")


# ==================== Whitelisted API Methods ====================

@frappe.whitelist()
def create_accounting_entries_from_ui(payment_name):
    """
    UI button handler.

    Logic:
    - If entries already exist  → tell the user clearly (no silent "no entries created")
    - If entries do NOT exist   → create them (skip_duplicate_check=False so per-method
                                  guards still protect against concurrent calls)
    """
    try:
        doc = frappe.get_doc('Payments', payment_name)

        if doc.docstatus != 1:
            frappe.throw(_("Payment must be submitted before creating accounting entries"))

        controller = PaymentAccountingController(doc)

        # ── Show clear status if entries already exist ────────────────────
        if controller.accounting_entries_exist():
            frappe.msgprint(
                _("✅ Accounting entries already exist for this payment (reference: {0}). "
                  "No new entries were created.\n\n"
                  "If you believe entries are missing, cancel this payment and resubmit, "
                  "or contact your administrator.").format(doc.reference_no),
                indicator="blue",
                title=_("Entries Already Exist")
            )
            return controller.get_created_entries_summary()

        # ── Entries do not exist — create them ────────────────────────────
        # skip_duplicate_check=False so per-method guards still run
        created = controller.create_accounting_entries(skip_duplicate_check=False)

        frappe.db.commit()

        if created:
            frappe.msgprint(
                _("✅ Successfully created {0} accounting entries.").format(len(created)),
                indicator="green"
            )
        else:
            frappe.msgprint(
                _("⚠ No accounting entries were created. "
                  "Check that 'Create Accounting Entries' is enabled and all required fields are filled."),
                indicator="orange"
            )

        return controller.get_created_entries_summary()

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Payment Accounting UI Error")
        frappe.throw(_("Failed to create accounting entries: {0}").format(str(e)))


@frappe.whitelist()
def get_outstanding_supplier_invoices(supplier, company, payment_currency=None):
    """
    Returns outstanding (submitted, unpaid / part-paid) Purchase Invoices for
    a supplier, oldest due date first, ready to be dropped into the
    'Invoice References' (Payments Reference) child table.

    Queries Purchase Invoice directly instead of going through ERPNext's
    get_outstanding_reference_documents, which needs a party_account /
    posting_date / currency args bundle that varies between ERPNext v14
    and v15 and throws
    "TypeError: cannot unpack non-iterable NoneType object" when
    party_account is missing (which is what happens when the caller passes
    frappe.defaults.get_default('default_payable_account') and that user
    default is unset, as it usually is).

    If payment_currency is given, only invoices raised in that currency
    are returned — Payment Entry references must match the payment's
    currency.
    """
    if not supplier:
        frappe.throw(_("Supplier is required"))
    if not company:
        frappe.throw(_("Company is required"))

    filters = {
        'supplier':           supplier,
        'company':            company,
        'docstatus':          1,
        'outstanding_amount': ['>', 0],
    }
    if payment_currency:
        filters['currency'] = payment_currency

    invoices = frappe.get_all(
        'Purchase Invoice',
        filters=filters,
        fields=[
            'name', 'posting_date', 'due_date', 'bill_no', 'currency',
            'grand_total', 'outstanding_amount', 'conversion_rate'
        ],
        order_by='due_date asc, posting_date asc',
        limit_page_length=0,
    )

    return [{
        'voucher_type':       'Purchase Invoice',
        'voucher_no':         inv.name,
        'posting_date':       inv.posting_date,
        'due_date':           inv.due_date or inv.posting_date,
        'bill_no':            inv.bill_no,
        'currency':           inv.currency,
        'invoice_amount':     flt(inv.grand_total),
        'outstanding_amount': flt(inv.outstanding_amount),
        'exchange_rate':      flt(inv.conversion_rate) or 1,
    } for inv in invoices]






@frappe.whitelist()
def cancel_accounting_entries_from_ui(payment_name):
    try:
        doc        = frappe.get_doc('Payments', payment_name)
        canceller  = AccountingEntryCanceller(doc)
        cancelled  = canceller.cancel_all_entries()
        frappe.db.commit()
        return {'cancelled_count': len(cancelled), 'entries': cancelled}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Payment Cancellation UI Error")
        frappe.throw(_("Failed to cancel accounting entries: {0}").format(str(e)))


@frappe.whitelist()
def generate_amortization_schedule(start_date, end_date, frequency, amount):
    try:
        start_date = getdate(start_date)
        end_date   = getdate(end_date)
        amount     = flt(amount)

        if amount <= 0:
            frappe.throw(_("Amount must be greater than zero"))

        freq_map = {"Monthly": 1, "Quarterly": 3, "Yearly": 12}
        if frequency not in freq_map:
            frappe.throw(_("Invalid frequency. Must be Monthly, Quarterly, or Yearly"))

        months        = freq_map[frequency]
        increment     = lambda d: add_months(d, months)
        total_periods = 0
        temp_date     = start_date

        while temp_date < end_date:
            total_periods += 1
            temp_date      = increment(temp_date)

        if total_periods == 0:
            frappe.throw(_("Invalid date range - must span at least one period"))

        amount_per_period = amount / total_periods
        schedule          = []
        current_date      = start_date
        period_num        = 1

        while current_date < end_date:
            period_end = increment(current_date)
            if period_end > end_date:
                period_end = end_date

            schedule.append({
                'period': period_num,
                'start':  current_date.strftime('%Y-%m-%d'),
                'end':    period_end.strftime('%Y-%m-%d'),
                'amount': round(amount_per_period, 2),
                'status': 'Pending'
            })
            current_date = period_end
            period_num  += 1

        return schedule

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Amortization Schedule Generation Error")
        frappe.throw(_("Failed to generate schedule: {0}").format(str(e)))


@frappe.whitelist()
def get_linked_accounting_entries(payment_name):
    """
    Single source of truth for the Connections/Accounting tabs.
    Returns journal entries, payment entries, amortization entries AND
    (merged in from the old payments_utils.get_document_links) fresh
    purchase invoice data for any allocated invoice references.
    """
    try:
        doc = frappe.get_doc('Payments', payment_name)

        je_list = frappe.db.sql("""
            SELECT name, posting_date, total_debit, docstatus
            FROM `tabJournal Entry`
            WHERE (cheque_no = %s OR cheque_no LIKE %s)
              AND company = %s AND docstatus != 2
            ORDER BY posting_date DESC LIMIT 100
        """, (doc.reference_no, f"{doc.reference_no}-RC%", doc.company), as_dict=1)

        pe_list = frappe.db.get_all('Payment Entry',
            filters={'reference_no': doc.reference_no, 'company': doc.company, 'docstatus': ['!=', 2]},
            fields=['name', 'posting_date', 'paid_amount', 'docstatus'],
            order_by='posting_date desc', limit=100)

        amort_entries = []
        if doc.amortize and doc.amortization_schedule:
            for s in doc.amortization_schedule:
                if s.journal_entry:
                    try:
                        je = frappe.get_doc('Journal Entry', s.journal_entry)
                        amort_entries.append({
                            'name':            je.name,
                            'posting_date':    je.posting_date,
                            'total_debit':     je.total_debit,
                            'docstatus':       je.docstatus,
                            'is_amortization': True
                        })
                    except Exception:
                        pass

        purchase_invoices = []
        if doc.trans_type == 'Supplier Payment' and doc.payments_reference:
            for ref in doc.payments_reference:
                if ref.reference_doctype == 'Purchase Invoice' and ref.reference_name:
                    if frappe.db.exists('Purchase Invoice', ref.reference_name):
                        pi = frappe.db.get_value('Purchase Invoice', ref.reference_name,
                            ['name', 'posting_date', 'grand_total', 'outstanding_amount'], as_dict=1)
                        if pi:
                            purchase_invoices.append(pi)

        return {
            'journal_entries':      je_list,
            'payment_entries':      pe_list,
            'amortization_entries': amort_entries,
            'purchase_invoices':    purchase_invoices,
            'total_entries':        len(je_list) + len(pe_list) + len(amort_entries)
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Linked Entries Error")
        return {
            'journal_entries': [], 'payment_entries': [],
            'amortization_entries': [], 'purchase_invoices': [],
            'total_entries': 0, 'error': str(e)
        }


@frappe.whitelist()
def get_bank_balance(bank_account):
    try:
        account = frappe.db.get_value('Bank Account', bank_account, 'account', cache=True)
        if not account:
            currency = frappe.db.get_value('Bank Account', bank_account, 'account_currency', cache=True) or 'NGN'
            return {'balance': 0, 'currency': currency, 'formatted': fmt_money(0, currency=currency)}

        from erpnext.accounts.utils import get_balance_on
        balance  = get_balance_on(account)
        currency = frappe.db.get_value('Account', account, 'account_currency', cache=True) or 'NGN'
        return {'balance': balance, 'currency': currency, 'formatted': fmt_money(balance, currency=currency)}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Bank Balance Error")
        return {'balance': 0, 'currency': 'NGN', 'formatted': '0.00', 'error': str(e)}


@frappe.whitelist()
def check_bank_balance_before_submit(payment_name):
    """Advisory-only endpoint the client can call before submit to show a
    non-blocking warning if the bank balance looks insufficient."""
    doc = frappe.get_doc('Payments', payment_name)
    if not doc.remittance_bank:
        return {'valid': True}
    amount = doc.local_currency_amount or doc.amount_paid or 0
    return validate_bank_balance(doc.remittance_bank, amount, doc.transaction_date)


@frappe.whitelist()
def check_payment_duplicates(supplier, amount, transaction_date, current_doc=None):
    """Check for duplicate payments (also run automatically in validate())."""
    return check_duplicate_payment(supplier, amount, transaction_date, current_doc)


@frappe.whitelist()
def get_payment_summary_card(payment_name):
    """Get payment summary for display card."""
    payment = frappe.get_doc('Payments', payment_name)

    summary = {
        'payment_no': payment.name,
        'payee': payment.payee_name or payment.supplier_name,
        'amount': _format_currency_display(
            payment.amount_paid or payment.amount_paid_in_fc,
            payment.payment_currency
        ),
        'amount_in_words': payment.amount_in_words,
        'status': payment.payment_status,
        'date': payment.transaction_date,
        'reference': payment.reference_no,
        'purpose': payment.transaction_purposes
    }

    if payment.deduct_wht:
        summary['wht_amount'] = _format_currency_display(payment.wht_amount, payment.payment_currency)
        summary['net_amount'] = _format_currency_display(payment.net_amount, payment.payment_currency)

    return summary


@frappe.whitelist()
def batch_process_payments(payment_names):
    """Submit multiple draft payments."""
    if isinstance(payment_names, str):
        payment_names = json.loads(payment_names)

    results = []
    for payment_name in payment_names:
        try:
            payment = frappe.get_doc('Payments', payment_name)

            if payment.docstatus != 0:
                results.append({
                    'payment': payment_name, 'status': 'Skipped',
                    'message': 'Already submitted or cancelled'
                })
                continue

            payment.submit()
            results.append({'payment': payment_name, 'status': 'Success', 'message': 'Submitted successfully'})

        except Exception as e:
            results.append({'payment': payment_name, 'status': 'Error', 'message': str(e)})
            frappe.log_error(frappe.get_traceback(), f"Batch Processing Error - {payment_name}")

    return results


@frappe.whitelist()
def bulk_approve_payments(payment_names, user=None):
    """Bulk approve draft payments."""
    if isinstance(payment_names, str):
        payment_names = json.loads(payment_names)

    user = user or frappe.session.user
    results = []

    for payment_name in payment_names:
        try:
            payment = frappe.get_doc('Payments', payment_name)
            payment.approved_by     = user
            payment.app_date        = nowdate()
            payment.payment_status  = 'Approved'
            payment.save()
            results.append({'payment': payment_name, 'status': 'Approved'})
        except Exception as e:
            results.append({'payment': payment_name, 'status': 'Error', 'message': str(e)})
            frappe.log_error(frappe.get_traceback(), f"Bulk Approve Error - {payment_name}")

    return results


# ==================== Dashboard & Analytics ====================
# Merged and corrected from payments_dashboard.py, which was written
# against a different/older schema (payment_status values 'Cleared' /
# 'Bounced' that don't exist on this DocType; a clearance_date column
# that doesn't exist at all; cashflow_type literals 'Operating' /
# 'Investing' / 'Financing' that don't match the 14 real options; and
# amount_paid instead of local_currency_amount, which silently dropped
# every foreign-currency payment from every total). Fixed against the
# real DocType below.

# Maps the 14 real cashflow_type options to a 3-way IFRS-style bucket,
# since that summary view is genuinely useful — it just needs to be
# derived from the real field instead of comparing against literals
# that were never valid values in the first place.
CASHFLOW_IFRS_CATEGORY = {
    'Supplier payments':     'Operating',
    'Salary payments':       'Operating',
    'Rent & utilities':      'Operating',
    'Office expenses':       'Operating',
    'Operating costs':       'Operating',
    'Tax Payment':           'Operating',
    'Equipment purchases':   'Investing',
    'Property acquisitions': 'Investing',
    'Investment purchases':  'Investing',
    'Capital expenditures':  'Investing',
    'Loan repayments':       'Financing',
    'Dividend payments':     'Financing',
    'Interest on loans':     'Financing',
    'Capital withdrawals':   'Financing',
}


@frappe.whitelist()
def get_payment_dashboard_data(company=None, from_date=None, to_date=None):
    """
    Single entry point for the payments dashboard. Replaces the old
    payments_dashboard.get_dashboard_data — if any frontend still calls
    that path, update it to ecclesia.ecclesia.doctype.payments.payments.get_payment_dashboard_data.
    """
    if not company:
        company = frappe.defaults.get_user_default("Company")
    if not from_date:
        from_date = add_days(nowdate(), -30)
    if not to_date:
        to_date = nowdate()

    return {
        "summary_cards":            _dash_summary_cards(company, from_date, to_date),
        "cashflow_breakdown":       _dash_cashflow_breakdown(company, from_date, to_date),
        "cashflow_ifrs_summary":    _dash_cashflow_ifrs_summary(company, from_date, to_date),
        "payment_mode_breakdown":   _dash_payment_mode_breakdown(company, from_date, to_date),
        "daily_trend":              _dash_daily_trend(company, from_date, to_date),
        "top_payees":               _dash_top_payees(company, from_date, to_date),
        "status_distribution":      _dash_status_distribution(company, from_date, to_date),
        "bank_wise_payments":       _dash_bank_wise_payments(company, from_date, to_date),
        "transaction_type_summary": _dash_transaction_type_summary(company, from_date, to_date),
    }


def _dash_summary_cards(company, from_date, to_date):
    current = frappe.db.sql("""
        SELECT
            COUNT(*) as total_payments,
            SUM(COALESCE(local_currency_amount, amount_paid, 0)) as total_amount,
            AVG(COALESCE(local_currency_amount, amount_paid, 0)) as avg_amount,
            SUM(COALESCE(wht_amount, 0)) as total_wht,
            SUM(CASE WHEN payment_status = 'Completed' THEN 1 ELSE 0 END) as completed_count,
            SUM(CASE WHEN payment_status IN ('Draft', 'Pending', 'Approved', 'Processing')
                THEN 1 ELSE 0 END) as pending_count,
            SUM(CASE WHEN payment_status IN ('Failed', 'Rejected') THEN 1 ELSE 0 END) as failed_count
        FROM `tabPayments`
        WHERE company = %s AND transaction_date BETWEEN %s AND %s AND docstatus = 1
    """, (company, from_date, to_date), as_dict=1)[0]

    days_diff  = (getdate(to_date) - getdate(from_date)).days
    prev_from  = add_days(getdate(from_date), -days_diff - 1)
    prev_to    = add_days(getdate(from_date), -1)

    previous = frappe.db.sql("""
        SELECT
            COUNT(*) as total_payments,
            SUM(COALESCE(local_currency_amount, amount_paid, 0)) as total_amount
        FROM `tabPayments`
        WHERE company = %s AND transaction_date BETWEEN %s AND %s AND docstatus = 1
    """, (company, prev_from, prev_to), as_dict=1)[0]

    def growth(cur, prev):
        return round(((cur - prev) / prev) * 100, 2) if prev else 0

    return {
        "total_payments": {
            "value": current.total_payments or 0,
            "growth": growth(current.total_payments or 0, previous.total_payments or 0)
        },
        "total_amount": {
            "value": flt(current.total_amount),
            "growth": growth(flt(current.total_amount), flt(previous.total_amount))
        },
        "avg_payment": {"value": flt(current.avg_amount), "growth": 0},
        "total_wht":   {"value": flt(current.total_wht), "growth": 0},
        "completed":   current.completed_count or 0,
        "pending":     current.pending_count or 0,
        "failed":      current.failed_count or 0,
    }


def _dash_cashflow_breakdown(company, from_date, to_date):
    return frappe.db.sql("""
        SELECT
            COALESCE(cashflow_type, 'Unclassified') as cashflow_type,
            COUNT(*) as count,
            SUM(COALESCE(local_currency_amount, amount_paid, 0)) as amount
        FROM `tabPayments`
        WHERE company = %s AND transaction_date BETWEEN %s AND %s AND docstatus = 1
        GROUP BY cashflow_type
        ORDER BY amount DESC
    """, (company, from_date, to_date), as_dict=1)


def _dash_cashflow_ifrs_summary(company, from_date, to_date):
    """3-way Operating/Investing/Financing rollup derived from the real
    cashflow_type values via CASHFLOW_IFRS_CATEGORY, with percentages."""
    rows = frappe.db.sql("""
        SELECT
            cashflow_type,
            SUM(COALESCE(local_currency_amount, amount_paid, 0)) as amount
        FROM `tabPayments`
        WHERE company = %s AND transaction_date BETWEEN %s AND %s AND docstatus = 1
        GROUP BY cashflow_type
    """, (company, from_date, to_date), as_dict=1)

    buckets = {"Operating": 0, "Investing": 0, "Financing": 0, "Unclassified": 0}
    for row in rows:
        category = CASHFLOW_IFRS_CATEGORY.get(row.cashflow_type, "Unclassified")
        buckets[category] += flt(row.amount)

    total = sum(buckets.values())
    return {
        k: {"amount": v, "percentage": round((v / total * 100), 2) if total else 0}
        for k, v in buckets.items()
    }


def _dash_payment_mode_breakdown(company, from_date, to_date):
    return frappe.db.sql("""
        SELECT
            COALESCE(mode_of_payment, 'Unknown') as payment_mode,
            COUNT(*) as count,
            SUM(COALESCE(local_currency_amount, amount_paid, 0)) as amount
        FROM `tabPayments`
        WHERE company = %s AND transaction_date BETWEEN %s AND %s AND docstatus = 1
        GROUP BY mode_of_payment
        ORDER BY amount DESC LIMIT 10
    """, (company, from_date, to_date), as_dict=1)


def _dash_daily_trend(company, from_date, to_date):
    return frappe.db.sql("""
        SELECT
            DATE(transaction_date) as date,
            COUNT(*) as count,
            SUM(COALESCE(local_currency_amount, amount_paid, 0)) as amount
        FROM `tabPayments`
        WHERE company = %s AND transaction_date BETWEEN %s AND %s AND docstatus = 1
        GROUP BY DATE(transaction_date)
        ORDER BY date
    """, (company, from_date, to_date), as_dict=1)


def _dash_top_payees(company, from_date, to_date, limit=10):
    # payee_name is only populated for Expense Payment / Transfer Out;
    # Supplier Payments carry the name in supplier_name instead — the
    # original query grouped on payee_name alone and silently dropped
    # every Supplier Payment from this report.
    return frappe.db.sql("""
        SELECT
            COALESCE(NULLIF(payee_name, ''), NULLIF(supplier_name, ''), 'Unknown') as payee,
            COUNT(*) as payment_count,
            SUM(COALESCE(local_currency_amount, amount_paid, 0)) as total_amount
        FROM `tabPayments`
        WHERE company = %s AND transaction_date BETWEEN %s AND %s AND docstatus = 1
        GROUP BY payee
        ORDER BY total_amount DESC LIMIT %s
    """, (company, from_date, to_date, limit), as_dict=1)


def _dash_status_distribution(company, from_date, to_date):
    return frappe.db.sql("""
        SELECT
            COALESCE(payment_status, 'Unknown') as status,
            COUNT(*) as count,
            SUM(COALESCE(local_currency_amount, amount_paid, 0)) as amount
        FROM `tabPayments`
        WHERE company = %s AND transaction_date BETWEEN %s AND %s AND docstatus = 1
        GROUP BY payment_status
        ORDER BY amount DESC
    """, (company, from_date, to_date), as_dict=1)


def _dash_bank_wise_payments(company, from_date, to_date):
    return frappe.db.sql("""
        SELECT
            COALESCE(remittance_bank, 'Not Specified') as bank,
            COUNT(*) as count,
            SUM(COALESCE(local_currency_amount, amount_paid, 0)) as amount
        FROM `tabPayments`
        WHERE company = %s AND transaction_date BETWEEN %s AND %s AND docstatus = 1
        GROUP BY remittance_bank
        ORDER BY amount DESC LIMIT 10
    """, (company, from_date, to_date), as_dict=1)


def _dash_transaction_type_summary(company, from_date, to_date):
    return frappe.db.sql("""
        SELECT
            COALESCE(trans_type, 'Uncategorized') as trans_type,
            COUNT(*) as count,
            SUM(COALESCE(local_currency_amount, amount_paid, 0)) as amount,
            AVG(COALESCE(local_currency_amount, amount_paid, 0)) as avg_amount
        FROM `tabPayments`
        WHERE company = %s AND transaction_date BETWEEN %s AND %s AND docstatus = 1
        GROUP BY trans_type
        ORDER BY amount DESC LIMIT 10
    """, (company, from_date, to_date), as_dict=1)


@frappe.whitelist()
def get_payment_kpis(company=None, period="This Month"):
    """Key performance indicators for a rolling period."""
    if not company:
        company = frappe.defaults.get_user_default("Company")

    if period == "Today":
        from_date = to_date = nowdate()
    elif period == "This Week":
        from_date, to_date = add_days(nowdate(), -7), nowdate()
    elif period == "This Month":
        from_date, to_date = frappe.utils.get_first_day(nowdate()), nowdate()
    elif period == "This Quarter":
        from_date, to_date = frappe.utils.get_quarter_start(nowdate()), nowdate()
    else:  # This Year
        from_date, to_date = frappe.utils.get_year_start(nowdate()), nowdate()

    totals = frappe.db.sql("""
        SELECT
            COUNT(*) as total_payments,
            SUM(COALESCE(local_currency_amount, amount_paid, 0)) as total_paid,
            SUM(CASE WHEN payment_status IN ('Failed', 'Rejected') THEN 1 ELSE 0 END) as failed_count,
            -- clearance_date does not exist on this DocType. `modified` is used as an
            -- approximation of when a Completed payment last changed state (i.e. when
            -- on_submit's db_set('payment_status','Completed') fired) — not a true
            -- clearance timestamp. If real bank-clearance tracking is needed, that
            -- requires a new dedicated date field on the DocType.
            AVG(CASE WHEN payment_status = 'Completed'
                THEN DATEDIFF(modified, transaction_date) ELSE NULL END) as avg_days_to_complete
        FROM `tabPayments`
        WHERE company = %s AND transaction_date BETWEEN %s AND %s AND docstatus = 1
    """, (company, from_date, to_date), as_dict=1)[0]

    total_payments = totals.total_payments or 0
    failed_rate = (flt(totals.failed_count) / total_payments * 100) if total_payments else 0

    return {
        "failed_rate": round(failed_rate, 2),
        "avg_days_to_complete": round(flt(totals.avg_days_to_complete), 2),
        "total_paid": flt(totals.total_paid),
        "total_payments": total_payments,
    }


@frappe.whitelist()
def get_cashflow_analysis(company, year=None):
    """Monthly cashflow_type breakdown for a given year."""
    if not year:
        year = nowdate().split('-')[0]

    return frappe.db.sql("""
        SELECT
            DATE_FORMAT(transaction_date, '%%Y-%%m') as month,
            COALESCE(cashflow_type, 'Unclassified') as cashflow_type,
            SUM(COALESCE(local_currency_amount, amount_paid, 0)) as amount
        FROM `tabPayments`
        WHERE company = %s AND YEAR(transaction_date) = %s AND docstatus = 1
        GROUP BY DATE_FORMAT(transaction_date, '%%Y-%%m'), cashflow_type
        ORDER BY month, cashflow_type
    """, (company, year), as_dict=1)


# ==================== Bulk Import (merged from payments_import_handler.py) ====
# Backs the "Import Payments" dialog in payments_list.js. Two bugs fixed
# from the original: (1) currency checks hardcoded 'NGN' instead of the
# row's actual company default currency — same class of bug fixed
# elsewhere in this file/DocType; (2) frappe.log_error() had its
# (message, title) arguments reversed everywhere else in this codebase
# calls it correctly, this file alone had them backwards, which dumped
# full tracebacks into the 140-char title field and truncated them.

def _company_currency(company):
    return frappe.db.get_value('Company', company, 'default_currency', cache=True) or 'NGN'


@frappe.whitelist()
def get_payments_import_template():
    """Generate import template for Payments with headers and sample data."""

    template_columns = [
        # Transaction Header
        "Transaction Date*", "Transaction Type*", "Company*", "Payment Status",
        # Beneficiary Information
        "Supplier ID", "Beneficiary Name", "Customer ID",
        # Transaction Options
        "Create Accounting Entries", "Deduct WHT", "Amortize Expense",
        "Multiple Line Items", "Shared Cost Allocation", "Inter-Company Transaction",
        # Accounting Dimensions
        "Branch", "Nature of Expense", "Cost Center", "Department", "Project",
        # Currency & Exchange
        "Payment Currency*", "Exchange Rate",
        # Payment Amount — column labels kept generic; local-currency vs
        # foreign-currency is now resolved per-row against that row's
        # Company default currency, not a hardcoded 'NGN'.
        "Amount Paid (Local Currency)", "Amount Paid (Foreign Currency)",
        # Payment Details
        "Mode of Payment*", "Cheque/Reference No*", "Account To Debit",
        "Transaction Purpose*",
        # WHT Details
        "WHT Rate (%)", "WHT Account",
        # Banking Details
        "Bank Account*", "Cash Flow Classification*", "Approval Document Reference",
        # Approval/Signatures
        "Issued By", "Issue Date", "Authorised By", "Authorization Date",
        "Approved By", "Approval Date"
    ]

    sample_data = [
        "2026-07-01", "Supplier Payment", "Your Company Name", "Draft",
        "SUPP-00001", "", "",
        "1", "0", "0", "0", "0", "0",
        "Head Office", "", "Main - YC", "Accounts", "",
        "NGN", "1",
        "500000", "",
        "Bank Draft", "CHQ-001", "", "Payment for office supplies",
        "", "",
        "FCMB - YC", "Supplier payments", "",
        "", "2026-07-01", "", "", "", ""
    ]

    return {"columns": template_columns, "sample_data": sample_data}


@frappe.whitelist()
def validate_payments_import(data):
    """Validate imported payments data before creating records."""
    if isinstance(data, str):
        data = json.loads(data)

    errors = []
    validated_data = []

    for idx, row in enumerate(data, start=2):  # row 2 = first data row after header
        row_errors = []

        if not row.get("Transaction Date"):
            row_errors.append(f"Row {idx}: Transaction Date is mandatory")

        if not row.get("Transaction Type"):
            row_errors.append(f"Row {idx}: Transaction Type is mandatory")
        elif row.get("Transaction Type") not in [
            "Supplier Payment", "Expense Payment", "Transfer Out",
            "Supplier Refunds", "Payment Request", "Maintenance Request"
        ]:
            row_errors.append(f"Row {idx}: Invalid Transaction Type")

        company = row.get("Company")
        if not company:
            row_errors.append(f"Row {idx}: Company is mandatory")
        elif not frappe.db.exists("Company", company):
            row_errors.append(f"Row {idx}: Company '{company}' does not exist")

        if not row.get("Payment Currency"):
            row_errors.append(f"Row {idx}: Payment Currency is mandatory")

        if not row.get("Mode of Payment"):
            row_errors.append(f"Row {idx}: Mode of Payment is mandatory")

        if not row.get("Cheque/Reference No"):
            row_errors.append(f"Row {idx}: Cheque/Reference No is mandatory")

        if not row.get("Transaction Purpose"):
            row_errors.append(f"Row {idx}: Transaction Purpose is mandatory")

        if not row.get("Bank Account"):
            row_errors.append(f"Row {idx}: Bank Account is mandatory")

        if not row.get("Cash Flow Classification"):
            row_errors.append(f"Row {idx}: Cash Flow Classification is mandatory")

        trans_type = row.get("Transaction Type")

        if trans_type == "Supplier Payment":
            if not row.get("Supplier ID"):
                row_errors.append(f"Row {idx}: Supplier ID is required for Supplier Payment")
            elif not frappe.db.exists("Supplier", row.get("Supplier ID")):
                row_errors.append(f"Row {idx}: Supplier '{row.get('Supplier ID')}' does not exist")

        elif trans_type == "Expense Payment":
            if not row.get("Account To Debit"):
                row_errors.append(f"Row {idx}: Account To Debit is required for Expense Payment")
            if not row.get("Cost Center"):
                row_errors.append(f"Row {idx}: Cost Center is required for Expense Payment")
            if not row.get("Beneficiary Name"):
                row_errors.append(f"Row {idx}: Beneficiary Name is required for Expense Payment")

        elif trans_type == "Transfer Out":
            if not row.get("Account To Debit"):
                row_errors.append(f"Row {idx}: Account To Debit is required for Transfer Out")
            if not row.get("Beneficiary Name"):
                row_errors.append(f"Row {idx}: Beneficiary Name is required for Transfer Out")

        # Amount validation — dynamic against the row's own company currency,
        # not a hardcoded 'NGN'.
        payment_currency = row.get("Payment Currency")
        company_currency = _company_currency(company) if company else 'NGN'
        is_local = payment_currency == company_currency

        if is_local:
            if not row.get("Amount Paid (Local Currency)"):
                row_errors.append(f"Row {idx}: Amount Paid (Local Currency) is required "
                                   f"when Payment Currency matches the company currency")
            elif flt(row.get("Amount Paid (Local Currency)")) <= 0:
                row_errors.append(f"Row {idx}: Amount Paid must be greater than zero")
        else:
            if not row.get("Amount Paid (Foreign Currency)"):
                row_errors.append(f"Row {idx}: Amount Paid (Foreign Currency) is required "
                                   f"for a currency other than the company currency")
            elif flt(row.get("Amount Paid (Foreign Currency)")) <= 0:
                row_errors.append(f"Row {idx}: Amount Paid must be greater than zero")
            if not row.get("Exchange Rate") or flt(row.get("Exchange Rate")) <= 0:
                row_errors.append(f"Row {idx}: Valid Exchange Rate is required for foreign currency")

        if row.get("Deduct WHT") in ["1", "Yes", "yes", "TRUE", "true", 1, True]:
            if not row.get("WHT Rate (%)"):
                row_errors.append(f"Row {idx}: WHT Rate is required when WHT is enabled")
            if not row.get("WHT Account"):
                row_errors.append(f"Row {idx}: WHT Account is required when WHT is enabled")

        if row.get("Customer ID"):
            if row.get("Nature of Expense") != "For Customer":
                row_errors.append(f"Row {idx}: Nature of Expense must be 'For Customer' "
                                   f"when Customer ID is specified")
            if not frappe.db.exists("Customer", row.get("Customer ID")):
                row_errors.append(f"Row {idx}: Customer '{row.get('Customer ID')}' does not exist")

        if row_errors:
            errors.extend(row_errors)
        else:
            validated_data.append(row)

    return {
        "success": len(errors) == 0,
        "errors": errors,
        "validated_count": len(validated_data),
        "error_count": len(errors)
    }


@frappe.whitelist()
def import_payments(data):
    """Import validated payments data. Each row is inserted (not submitted)
    so it lands as a Draft for review — matches the template's default
    Payment Status and lets the normal validate()/duplicate-check/auto-coding
    flow run per-row exactly as it would for a manually created payment."""
    if isinstance(data, str):
        data = json.loads(data)

    imported = []
    failed   = []

    for idx, row in enumerate(data, start=1):
        try:
            payment = frappe.new_doc("Payments")

            payment.transaction_date = getdate(row.get("Transaction Date"))
            payment.trans_type       = row.get("Transaction Type")
            payment.company          = row.get("Company")
            payment.payment_status   = row.get("Payment Status") or "Draft"

            if row.get("Supplier ID"):
                payment.payee_id = row.get("Supplier ID")
            if row.get("Beneficiary Name"):
                payment.payee_name = row.get("Beneficiary Name")
            if row.get("Customer ID"):
                payment.customer_id = row.get("Customer ID")

            truthy = ["1", "Yes", "yes", "TRUE", "true", 1, True]
            payment.create_accounting_entries = 1 if row.get("Create Accounting Entries") in truthy else 0
            payment.deduct_wht                = 1 if row.get("Deduct WHT") in truthy else 0
            payment.amortize                  = 1 if row.get("Amortize Expense") in truthy else 0
            payment.is_multi_line             = 1 if row.get("Multiple Line Items") in truthy else 0
            payment.is_shared_cost            = 1 if row.get("Shared Cost Allocation") in truthy else 0
            payment.is_related_coy_trans      = 1 if row.get("Inter-Company Transaction") in truthy else 0

            if row.get("Branch"):
                payment.branch = row.get("Branch")
            if row.get("Nature of Expense"):
                payment.nature_of_expense = row.get("Nature of Expense")
            if row.get("Cost Center"):
                payment.cost_center = row.get("Cost Center")
            if row.get("Department"):
                payment.department = row.get("Department")
            if row.get("Project"):
                payment.project = row.get("Project")

            payment.payment_currency = row.get("Payment Currency")
            payment.exchange_rate    = flt(row.get("Exchange Rate", 1)) or 1

            company_currency = _company_currency(payment.company)
            if payment.payment_currency == company_currency:
                payment.amount_paid = flt(row.get("Amount Paid (Local Currency)"))
            else:
                payment.amount_paid_in_fc = flt(row.get("Amount Paid (Foreign Currency)"))

            payment.mode_of_payment = row.get("Mode of Payment")
            payment.reference_no    = row.get("Cheque/Reference No")
            if row.get("Account To Debit"):
                payment.account_to_debit = row.get("Account To Debit")
            payment.transaction_purposes = row.get("Transaction Purpose")

            if payment.deduct_wht:
                payment.whtax_rate = flt(row.get("WHT Rate (%)"))
                payment.wht_account = row.get("WHT Account")

            payment.remittance_bank = row.get("Bank Account")
            payment.cashflow_type   = row.get("Cash Flow Classification")
            if row.get("Approval Document Reference"):
                payment.approval_doc = row.get("Approval Document Reference")

            if row.get("Issued By"):
                payment.issued_by = row.get("Issued By")
                payment.date = getdate(row.get("Issue Date")) if row.get("Issue Date") else nowdate()
            if row.get("Authorised By"):
                payment.authorised_by = row.get("Authorised By")
                if row.get("Authorization Date"):
                    payment.auth_date = getdate(row.get("Authorization Date"))
            if row.get("Approved By"):
                payment.approved_by = row.get("Approved By")
                if row.get("Approval Date"):
                    payment.app_date = getdate(row.get("Approval Date"))

            payment.insert()

            imported.append({"row": idx, "name": payment.name, "status": "Success"})

        except Exception as e:
            failed.append({"row": idx, "error": str(e), "data": row})
            frappe.log_error(frappe.get_traceback(), f"Payment Import Error - Row {idx}")

    frappe.db.commit()

    return {
        "success": len(failed) == 0,
        "imported_count": len(imported),
        "failed_count": len(failed),
        "imported": imported,
        "failed": failed
    }


@frappe.whitelist()
def get_supplier_payment_summary(supplier, from_date, to_date):
    """Payment summary for a supplier over a date range."""
    payments = frappe.db.sql("""
        SELECT
            name,
            transaction_date,
            COALESCE(local_currency_amount, amount_paid) as amount_paid,
            reference_no,
            transaction_purposes,
            payment_status,
            wht_amount,
            COALESCE(net_amount, local_currency_amount, amount_paid) as net_amount
        FROM `tabPayments`
        WHERE
            payee_id = %(supplier)s
            AND transaction_date BETWEEN %(from_date)s AND %(to_date)s
            AND docstatus = 1
        ORDER BY transaction_date DESC
    """, {'supplier': supplier, 'from_date': from_date, 'to_date': to_date}, as_dict=1)

    return {
        'total_payments': len(payments),
        'total_amount': sum(p.amount_paid for p in payments),
        'total_wht': sum(p.wht_amount or 0 for p in payments),
        'total_net': sum(p.net_amount or p.amount_paid for p in payments),
        'payments': payments
    }


# ==================== Hook Functions ====================

def validate_payment(doc, method):
    """doc_events hook: enforces reference_no uniqueness per company across
    all payments regardless of trans_type. Kept separate from
    Payments.validate() since it is registered independently in hooks.py."""
    if not doc.reference_no:
        return

    existing = frappe.db.sql("""
        SELECT name FROM `tabPayments`
        WHERE reference_no = %s AND name != %s AND company = %s AND docstatus != 2
        LIMIT 1
    """, (doc.reference_no, doc.name, doc.company), as_dict=1)

    if existing:
        frappe.throw(_("Payment with reference number {0} already exists: {1}").format(
            doc.reference_no, existing[0].name))


def before_submit_payment(doc, method):
    """
    doc_events hook registered in hooks.py for Payments' before_submit event.
    Currently a no-op — the real pre-submit work (auto-coding, status set)
    lives in Payments.before_submit() on the Document class itself, which
    Frappe calls in addition to this hook. Kept as a stable, importable
    attribute so hooks.py doesn't need to change; left intentionally empty
    unless you want doc_event-level logic here specifically.
    """
    pass


def on_trash_payment(doc, method):
    if doc.docstatus == 1:
        frappe.throw(_("Cannot delete submitted payment. Please cancel it first."))
