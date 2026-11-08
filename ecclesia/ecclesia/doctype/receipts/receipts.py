# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

"""
Receipts Accounting Module

Transaction-safe architecture
-----------------------------

The Receipt lifecycle is intentionally divided as follows:

1. validate()
   - Performs normal validation only.

2. before_submit()
   - Performs submission-time validation and prepares calculated fields.
   - DOES NOT create Journal Entries or Payment Entries.

3. on_submit()
   - Creates the required accounting entries.
   - Creates amortization entries where applicable.
   - Any accounting exception is allowed to propagate.
   - Frappe therefore rolls back the complete transaction if accounting
     creation fails.

4. No manual frappe.db.commit() or frappe.db.rollback() is performed
   inside the Receipt submission/cancellation lifecycle.

5. Accounting entries are protected against duplicates using reference_no
   / cheque_no.

6. Related-company accounting failures are NOT silently swallowed.
   A failed accounting operation causes the Receipt submission transaction
   to fail and roll back.

7. The Receipt's docstatus is never manually changed by this controller.
   Frappe remains responsible for docstatus.

8. UI recovery methods are separate requests and may commit after successful
   completion because they are not part of the Receipt submit transaction.
"""

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
    add_days,
    add_months,
    date_diff,
    flt,
    fmt_money,
    get_url,
    getdate,
    money_in_words,
    nowdate,
    today,
)


# ============================================================================
# Receipt Accounting Controller
# ============================================================================

class ReceiptAccountingController:
    """
    Creates accounting entries for a submitted Receipt.

    IMPORTANT:
    This controller must NOT manually commit or rollback the database.

    It is normally called from Receipts.on_submit(). If an exception occurs,
    the exception is allowed to propagate to Frappe so the complete transaction
    can be rolled back.
    """

    def __init__(self, doc):
        self.doc = doc

        if not doc.company:
            frappe.throw(_("Company is required"))

        self.company = doc.company
        self.company_doc = frappe.get_doc("Company", self.company)
        self.company_currency = self.company_doc.default_currency
        self.is_local_currency = (
            doc.receipt_currency == self.company_currency
        )

        self.created_entries = []
        self._cache = {}

        frappe.logger().info(
            f"ReceiptAccountingController initialized for {doc.name} - "
            f"Currency: {doc.receipt_currency}, "
            f"Company Currency: {self.company_currency}, "
            f"Is Local: {self.is_local_currency}"
        )

    # ----------------------------------------------------------------------
    # Existence / Duplicate Checks
    # ----------------------------------------------------------------------

    def accounting_entries_exist(self):
        """
        Check whether submitted accounting entries already exist for this
        Receipt.

        Journal Entries:
            reference_no is stored in cheque_no.

        Related-company and amortization entries:
            reference_no-RC1
            reference_no-RC2
            reference_no-AMORT1
            etc.

        Payment Entries:
            reference_no is stored in reference_no.
        """

        ref = self.doc.reference_no
        company = self.company

        if not ref:
            return False

        je_exists = frappe.db.sql(
            """
            SELECT name
            FROM `tabJournal Entry`
            WHERE
                (cheque_no = %s OR cheque_no LIKE %s)
                AND company = %s
                AND docstatus = 1
            LIMIT 1
            """,
            (ref, f"{ref}-%", company),
            as_dict=True,
        )

        if je_exists:
            return True

        pe_exists = frappe.db.get_all(
            "Payment Entry",
            filters={
                "reference_no": ref,
                "company": company,
                "docstatus": 1,
            },
            fields=["name"],
            limit=1,
        )

        return bool(pe_exists)

    def _je_exists(self, cheque_no, company=None):
        """
        Check for an existing submitted Journal Entry.
        """
        company = company or self.company

        if not cheque_no:
            return False

        return bool(
            frappe.db.exists(
                "Journal Entry",
                {
                    "cheque_no": cheque_no,
                    "company": company,
                    "docstatus": 1,
                },
            )
        )

    def _pe_exists(self, reference_no=None, company=None):
        """
        Check for an existing submitted Payment Entry.
        """
        reference_no = reference_no or self.doc.reference_no
        company = company or self.company

        if not reference_no:
            return False

        return bool(
            frappe.db.exists(
                "Payment Entry",
                {
                    "reference_no": reference_no,
                    "company": company,
                    "docstatus": 1,
                },
            )
        )

    # ----------------------------------------------------------------------
    # Account Validation
    # ----------------------------------------------------------------------

    def _validate_account_not_group(self, account):
        if not account:
            return

        is_group = frappe.db.get_value(
            "Account",
            account,
            "is_group",
            cache=True,
        )

        if is_group:
            frappe.throw(
                _(
                    "The account {0} is a group account and cannot be used "
                    "for posting transactions"
                ).format(account)
            )

    # ----------------------------------------------------------------------
    # Main Accounting Entry Creation
    # ----------------------------------------------------------------------

    def create_accounting_entries(self, skip_duplicate_check=False):
        """
        Create accounting entries for the Receipt.

        This method deliberately does NOT catch accounting exceptions.

        If any required accounting operation fails, the exception propagates
        to on_submit(), allowing Frappe to roll back the transaction.
        """

        if not self.doc.create_accounting_entries:
            frappe.logger().info(
                f"Accounting entry creation disabled for {self.doc.name}"
            )
            return []

        self._validate_before_creation()

        trans_type = self.doc.trans_type

        if trans_type in ("Customer Receipt", "Receive from One-Off"):
            self._create_customer_payment_entry(skip_duplicate_check)

        elif trans_type == "Revenue Receipt":
            self._create_revenue_receipt_entries(skip_duplicate_check)

        elif trans_type == "Transfer In":
            self._create_transfer_in_entries(skip_duplicate_check)

        elif trans_type == "Customer Refund":
            # No existing implementation was provided for Customer Refund.
            # If related-company processing is enabled, it will still run.
            frappe.logger().info(
                f"No direct accounting handler configured for "
                f"Customer Refund {self.doc.name}"
            )

        else:
            if not self.doc.is_related_coy_trans:
                frappe.throw(
                    _(
                        "No accounting-entry handler is configured for "
                        "transaction type {0}."
                    ).format(trans_type)
                )

        if self.doc.is_related_coy_trans:
            self._create_related_company_entries()

        return self.created_entries

    # ----------------------------------------------------------------------
    # Validation Before Accounting
    # ----------------------------------------------------------------------

    def _validate_before_creation(self):
        if (
            self.doc.trans_type
            not in ("Customer Receipt", "Customer Refund")
            and not self.doc.is_multi_line
            and not self.doc.account_to_credit
        ):
            frappe.throw(
                _("Account to Credit is required for {0}").format(
                    self.doc.trans_type
                )
            )

        if not self.doc.remittance_bank_gl:
            frappe.throw(
                _("Remittance Bank GL Account is required")
            )

        self._validate_account_not_group(
            self.doc.remittance_bank_gl
        )

        if self.doc.account_to_credit:
            self._validate_account_not_group(
                self.doc.account_to_credit
            )

    # =========================================================================
    # Customer Receipt / Receive from One-Off
    # =========================================================================

    def _create_customer_payment_entry(self, skip_duplicate_check=False):
        frappe.logger().info(
            f"Creating Customer Payment Entry for {self.doc.name}"
        )

        if (
            not skip_duplicate_check
            and self._pe_exists()
        ):
            frappe.msgprint(
                _(
                    "A Payment Entry already exists for reference {0}. "
                    "No duplicate Payment Entry will be created."
                ).format(self.doc.reference_no),
                indicator="orange",
                alert=True,
            )
            return self.created_entries

        if not self.doc.customer_id:
            frappe.throw(
                _(
                    "Customer is required for Customer Receipt "
                    "transactions"
                )
            )

        pe = frappe.new_doc("Payment Entry")

        pe.party_type = "Customer"
        pe.party = self.doc.customer_id
        pe.payment_type = "Receive"
        pe.mode_of_payment = self.doc.mode_of_payment
        pe.company = self.doc.company
        pe.paid_to = self.doc.remittance_bank_gl
        pe.paid_from = self.company_doc.default_receivable_account
        pe.bank_account = self.doc.remittance_bank
        pe.posting_date = self.doc.transaction_date
        pe.reference_no = self.doc.reference_no
        pe.reference_date = self.doc.transaction_date

        pe.remarks = (
            self.doc.transaction_purposes
            or f"Receipt from {self.doc.customer_name}"
        )

        if self.is_local_currency:
            pe.paid_amount = self.doc.amount_received
            pe.received_amount = self.doc.amount_received
            pe.source_exchange_rate = 1
            pe.target_exchange_rate = 1

        else:
            exchange_rate = flt(self.doc.exchange_rate) or 1

            pe.paid_amount = (
                flt(self.doc.amount_received_in_fc)
                * exchange_rate
            )

            pe.received_amount = self.doc.amount_received_in_fc
            pe.paid_to_account_currency = self.doc.receipt_currency
            pe.source_exchange_rate = 1
            pe.target_exchange_rate = exchange_rate

        # Invoice allocation
        for ref in self.doc.get("receipts_reference") or []:

            if flt(ref.allocated_amount) <= 0:
                continue

            pe.append(
                "references",
                {
                    "reference_doctype": (
                        ref.reference_doctype
                        or "Sales Invoice"
                    ),
                    "reference_name": ref.reference_name,
                    "due_date": ref.due_date,
                    "bill_no": ref.bill_no,
                    "payment_term": ref.payment_term or "",
                    "total_amount": ref.total_amount,
                    "outstanding_amount": ref.outstanding_amount,
                    "allocated_amount": ref.allocated_amount,
                    "exchange_rate": (
                        flt(ref.exchange_rate) or 1
                    ),
                    "exchange_gain_loss": (
                        ref.exchange_gain_loss or 0
                    ),
                },
            )

        pe.flags.ignore_permissions = True
        pe.flags.ignore_mandatory = True

        # IMPORTANT:
        # No frappe.db.commit() here.
        pe.insert(ignore_permissions=True)
        pe.submit()

        self.created_entries.append(
            {
                "doctype": "Payment Entry",
                "name": pe.name,
                "amount": pe.paid_amount,
            }
        )

        frappe.logger().info(
            f"Payment Entry {pe.name} created and submitted "
            f"for Receipt {self.doc.name}"
        )

        frappe.msgprint(
            _("Payment Entry {0} created").format(pe.name),
            indicator="green",
        )

        return self.created_entries

    # =========================================================================
    # Revenue Receipt
    # =========================================================================

    def _create_revenue_receipt_entries(
        self,
        skip_duplicate_check=False,
    ):
        frappe.logger().info(
            f"Creating Revenue Receipt Journal Entry "
            f"for {self.doc.name}"
        )

        if (
            not skip_duplicate_check
            and self._je_exists(self.doc.reference_no)
        ):
            frappe.msgprint(
                _(
                    "A Journal Entry already exists for reference {0}. "
                    "No duplicate Journal Entry will be created."
                ).format(self.doc.reference_no),
                indicator="orange",
                alert=True,
            )

            return self.created_entries

        if self.doc.is_multi_line:
            return self._create_multi_line_journal()

        return self._create_simple_revenue_journal()

    def _create_simple_revenue_journal(self):

        self._validate_account_not_group(
            self.doc.account_to_credit
        )

        je = self._init_je()

        je.voucher_type = "Bank Entry"

        if self.is_local_currency:

            debit_amount = flt(
                self.doc.amount_received
            )

            debit_company_amount = debit_amount

        else:

            debit_amount = flt(
                self.doc.amount_received_in_fc
            )

            debit_company_amount = (
                debit_amount
                * flt(self.doc.exchange_rate)
            )

        # Debit Bank
        je.append(
            "accounts",
            {
                "account": self.doc.remittance_bank_gl,
                "bank_account": self.doc.remittance_bank,
                "debit_in_account_currency": debit_amount,
                "debit": debit_company_amount,
                "exchange_rate": (
                    self.doc.exchange_rate
                    if not self.is_local_currency
                    else 1
                ),
                "user_remark": self.doc.transaction_purposes,
                "against_account": self.doc.account_to_credit,
            },
        )

        # Credit Revenue
        je.append(
            "accounts",
            {
                "account": self.doc.account_to_credit,
                "credit_in_account_currency": debit_company_amount,
                "credit": debit_company_amount,
                "user_remark": self.doc.transaction_purposes,
                "cost_center": self.doc.cost_center,
                "exchange_rate": 1,
                "account_currency": self.company_currency,
                "against_account": self.doc.remittance_bank_gl,
            },
        )

        return self._submit_je(je)

    # =========================================================================
    # Multi-Line Revenue Receipt
    # =========================================================================

    def _create_multi_line_journal(self):

        if not self.doc.receipts_item_line:
            frappe.throw(
                _("Please add line items for multi-line receipt")
            )

        je = self._init_je()

        total_credit = 0
        credit_accounts = []

        for row in self.doc.receipts_item_line:

            if not row.gl_account or not row.amount:
                continue

            self._validate_account_not_group(
                row.gl_account
            )

            if self.is_local_currency:
                amount = flt(row.amount)
                account_currency_amount = amount
                base_amount = amount
                exchange_rate = 1
            else:
                exchange_rate = flt(row.exch_rate) or 1
                account_currency_amount = flt(row.amount)
                base_amount = account_currency_amount * exchange_rate

            je.append(
                "accounts",
                {
                    "account": row.gl_account,
                    "credit_in_account_currency": (
                        account_currency_amount
                    ),
                    "credit": base_amount,
                    "exchange_rate": exchange_rate,
                    "user_remark": (
                        row.description
                        or self.doc.transaction_purposes
                    ),
                    "cost_center": row.cost_center,
                    "against_account": self.doc.remittance_bank_gl,
                },
            )

            total_credit += base_amount
            credit_accounts.append(row.gl_account)

        if total_credit <= 0:
            frappe.throw(
                _("At least one valid receipt line is required")
            )

        if self.is_local_currency:
            debit_amount = flt(self.doc.amount_received)
            debit_base_amount = debit_amount
            exchange_rate = 1
        else:
            debit_amount = flt(
                self.doc.amount_received_in_fc
            )
            exchange_rate = flt(
                self.doc.exchange_rate
            ) or 1
            debit_base_amount = debit_amount * exchange_rate

        against_accounts = ",".join(
            credit_accounts
        )

        je.append(
            "accounts",
            {
                "account": self.doc.remittance_bank_gl,
                "debit_in_account_currency": debit_amount,
                "debit": debit_base_amount,
                "exchange_rate": exchange_rate,
                "bank_account": self.doc.remittance_bank,
                "user_remark": self.doc.transaction_purposes,
                "against_account": against_accounts,
            },
        )

        return self._submit_je(je)

    # =========================================================================
    # Transfer In
    # =========================================================================

    def _create_transfer_in_entries(
        self,
        skip_duplicate_check=False,
    ):

        frappe.logger().info(
            f"Creating Transfer In Journal Entry "
            f"for {self.doc.name}"
        )

        if (
            not skip_duplicate_check
            and self._je_exists(self.doc.reference_no)
        ):
            frappe.msgprint(
                _(
                    "A Journal Entry already exists for reference {0}."
                ).format(self.doc.reference_no),
                indicator="orange",
                alert=True,
            )

            return self.created_entries

        self._validate_account_not_group(
            self.doc.account_to_credit
        )

        je = self._init_je()

        je.voucher_type = "Bank Entry"

        if self.is_local_currency:

            debit_amount = flt(
                self.doc.amount_received
            )

            debit_amount_company = debit_amount

        else:

            debit_amount = flt(
                self.doc.amount_received_in_fc
            )

            debit_amount_company = (
                debit_amount
                * flt(self.doc.exchange_rate)
            )

        # Debit bank
        je.append(
            "accounts",
            {
                "account": self.doc.remittance_bank_gl,
                "bank_account": self.doc.remittance_bank,
                "debit_in_account_currency": debit_amount,
                "debit": debit_amount_company,
                "user_remark": self.doc.transaction_purposes,
                "account_currency": self.doc.receipt_currency,
                "exchange_rate": (
                    self.doc.exchange_rate
                    if not self.is_local_currency
                    else 1
                ),
                "against_account": self.doc.account_to_credit,
            },
        )

        # Credit transfer account
        je.append(
            "accounts",
            {
                "account": self.doc.account_to_credit,
                "exchange_rate": 1,
                "account_currency": self.company_currency,
                "credit_in_account_currency": debit_amount_company,
                "credit": debit_amount_company,
                "user_remark": self.doc.transaction_purposes,
                "against_account": self.doc.remittance_bank_gl,
            },
        )

        return self._submit_je(je)

    # =========================================================================
    # Related Company Accounting
    # =========================================================================

    def _create_related_company_entries(self):

        if not self.doc.related_company_receipts:
            return self.created_entries

        created_count = 0

        for idx, row in enumerate(
            self.doc.related_company_receipts,
            1,
        ):

            self._validate_rc_row(row, idx)

            rc_cheque_no = (
                f"{self.doc.reference_no}-RC{idx}"
            )

            # --------------------------------------------------------------
            # Main company entry
            # --------------------------------------------------------------

            if not self._je_exists(
                rc_cheque_no,
                self.doc.company,
            ):

                je_main = self._create_main_company_journal(
                    row,
                    rc_cheque_no,
                )

                if je_main:
                    self.created_entries.append(
                        {
                            "doctype": "Journal Entry",
                            "name": je_main,
                            "company": self.doc.company,
                        }
                    )

                    created_count += 1

            # --------------------------------------------------------------
            # Owner company entry
            # --------------------------------------------------------------

            if row.trans_type == "Customer Receipt":

                owner_pe = self._create_owner_payment_entry(
                    row,
                    row.related_company,
                )

                if owner_pe:

                    self.created_entries.append(
                        {
                            "doctype": "Payment Entry",
                            "name": owner_pe,
                            "company": row.related_company,
                        }
                    )

                    created_count += 1

            else:

                owner_je = self._create_owner_journal_entry(
                    row,
                    row.related_company,
                    rc_cheque_no,
                )

                if owner_je:

                    self.created_entries.append(
                        {
                            "doctype": "Journal Entry",
                            "name": owner_je,
                            "company": row.related_company,
                        }
                    )

                    created_count += 1

        if created_count:

            frappe.msgprint(
                _(
                    "Created {0} related company accounting entries."
                ).format(created_count),
                indicator="green",
            )

        return self.created_entries

    def _validate_rc_row(self, row, row_num):

        if not row.party:
            frappe.throw(
                _("Row {0}: Party is required").format(row_num)
            )

        if not row.amount or flt(row.amount) <= 0:
            frappe.throw(
                _("Row {0}: Amount must be greater than zero").format(
                    row_num
                )
            )

        if not getattr(row, "related_company", None):
            frappe.throw(
                _("Row {0}: Related Company is required").format(
                    row_num
                )
            )

        if not frappe.db.exists(
            "Company",
            row.related_company,
        ):
            frappe.throw(
                _(
                    "Row {0}: Related Company '{1}' does not exist"
                ).format(
                    row_num,
                    row.related_company,
                )
            )

    def _create_main_company_journal(
        self,
        row,
        rc_cheque_no,
    ):

        transaction_purpose = (
            f"{row.remark or 'Receipt'} "
            f"for {row.related_company}"
        )

        je = frappe.new_doc("Journal Entry")

        je.naming_series = "BJV-.#####"
        je.paid_to_or_received_from = (
            row.party_name or row.party
        )
        je.transaction_description = transaction_purpose
        je.posting_date = self.doc.transaction_date
        je.reference_document_no = self.doc.name
        je.cheque_no = rc_cheque_no
        je.cheque_date = self.doc.transaction_date
        je.company = self.doc.company
        je.voucher_type = "Journal Entry"
        je.user_remark = transaction_purpose

        exch_rate = flt(
            getattr(row, "exch_rate", None)
        ) or 1

        amount = flt(row.amount) * exch_rate

        intercompany_account = (
            frappe.db.get_value(
                "Company",
                self.doc.company,
                "custom_intercompany_receivable_account",
            )
            or self.company_doc.default_receivable_account
        )

        if not intercompany_account:
            frappe.throw(
                _(
                    "Intercompany receivable account is not configured "
                    "for company {0}"
                ).format(self.doc.company)
            )

        self._validate_account_not_group(
            intercompany_account
        )

        # Debit intercompany receivable
        je.append(
            "accounts",
            {
                "account": intercompany_account,
                "debit_in_account_currency": amount,
                "debit": amount,
                "party_type": "Company",
                "party": row.related_company,
                "user_remark": transaction_purpose,
                "against_account": self.doc.remittance_bank_gl,
            },
        )

        # Credit bank
        je.append(
            "accounts",
            {
                "account": self.doc.remittance_bank_gl,
                "bank_account": self.doc.remittance_bank,
                "credit_in_account_currency": amount,
                "credit": amount,
                "user_remark": transaction_purpose,
                "against_account": intercompany_account,
            },
        )

        je.set_total_debit_credit()

        je.flags.ignore_permissions = True
        je.flags.ignore_fiscal_year = True

        je.insert(ignore_permissions=True)
        je.submit()

        return je.name

    def _create_owner_payment_entry(
        self,
        row,
        related_company,
    ):

        if not row.party:
            return None

        if self._pe_exists(
            self.doc.reference_no,
            related_company,
        ):
            return None

        owner_company_doc = frappe.get_doc(
            "Company",
            related_company,
        )

        pe = frappe.new_doc("Payment Entry")

        pe.party_type = "Customer"
        pe.party = row.party
        pe.payment_type = "Receive"
        pe.mode_of_payment = self.doc.mode_of_payment
        pe.company = related_company

        pe.paid_to = (
            owner_company_doc.default_receivable_account
        )

        pe.paid_from = (
            owner_company_doc.default_receivable_account
        )

        pe.posting_date = self.doc.transaction_date
        pe.reference_no = self.doc.reference_no
        pe.reference_date = self.doc.transaction_date

        pe.remarks = (
            f"Receipt via {self.doc.company} - "
            f"{self.doc.transaction_purposes}"
        )

        exch_rate = flt(
            getattr(row, "exch_rate", None)
        ) or 1

        amount = flt(row.amount) * exch_rate

        pe.paid_amount = amount
        pe.received_amount = amount
        pe.source_exchange_rate = 1
        pe.target_exchange_rate = 1

        invoice_reference = getattr(
            row,
            "invoice_references",
            None,
        )

        if invoice_reference:

            pe.append(
                "references",
                {
                    "reference_doctype": "Sales Invoice",
                    "reference_name": invoice_reference,
                    "allocated_amount": amount,
                },
            )

        pe.flags.ignore_mandatory = True
        pe.flags.ignore_permissions = True

        pe.insert(ignore_permissions=True)
        pe.submit()

        return pe.name

    def _create_owner_journal_entry(
        self,
        row,
        related_company,
        rc_cheque_no,
    ):

        transaction_purpose = (
            f"{row.remark or 'Receipt'} "
            f"received via {self.doc.company}"
        )

        if self._je_exists(
            rc_cheque_no,
            related_company,
        ):
            return None

        related_company_doc = frappe.get_doc(
            "Company",
            related_company,
        )

        je = frappe.new_doc("Journal Entry")

        je.naming_series = "BJV-.#####"
        je.paid_to_or_received_from = (
            row.party_name or row.party
        )
        je.transaction_description = transaction_purpose
        je.posting_date = self.doc.transaction_date
        je.reference_document_no = self.doc.name
        je.cheque_no = rc_cheque_no
        je.cheque_date = self.doc.transaction_date
        je.company = related_company
        je.voucher_type = "Journal Entry"
        je.user_remark = transaction_purpose

        exch_rate = flt(
            getattr(row, "exch_rate", None)
        ) or 1

        amount = flt(row.amount) * exch_rate

        intercompany_account = (
            frappe.db.get_value(
                "Company",
                related_company,
                "custom_intercompany_payable_account",
            )
            or related_company_doc.default_payable_account
        )

        if not intercompany_account:
            frappe.throw(
                _(
                    "Intercompany payable account is not configured "
                    "for company {0}"
                ).format(related_company)
            )

        self._validate_account_not_group(
            intercompany_account
        )

        self._validate_account_not_group(
            row.party
        )

        # Debit intercompany payable
        je.append(
            "accounts",
            {
                "account": intercompany_account,
                "debit_in_account_currency": amount,
                "debit": amount,
                "party_type": "Company",
                "party": self.doc.company,
                "user_remark": transaction_purpose,
                "against_account": row.party,
            },
        )

        # Credit party
        je.append(
            "accounts",
            {
                "account": row.party,
                "credit_in_account_currency": amount,
                "credit": amount,
                "user_remark": transaction_purpose,
                "cost_center": getattr(
                    row,
                    "cost_center",
                    None,
                ),
                "against_account": intercompany_account,
            },
        )

        je.set_total_debit_credit()

        je.flags.ignore_permissions = True
        je.flags.ignore_fiscal_year = True

        je.insert(ignore_permissions=True)
        je.submit()

        return je.name

    # =========================================================================
    # Amortization
    # =========================================================================

    def create_amortization_journals(self):

        if not (
            self.doc.trans_type == "Revenue Receipt"
            and self.doc.create_accounting_entries
            and self.doc.amortize
            and self.doc.frequency
            in ("Monthly", "Quarterly")
        ):
            return []

        self._validate_account_not_group(
            self.doc.deferred_revenue_account
        )

        self._validate_account_not_group(
            self.doc.revenue_account
        )

        if not self.doc.start_date:
            frappe.throw(
                _("Start Date is required for amortization")
            )

        if not self.doc.end_date:
            frappe.throw(
                _("End Date is required for amortization")
            )

        period_months = (
            1
            if self.doc.frequency == "Monthly"
            else 3
        )

        total_days = date_diff(
            self.doc.end_date,
            self.doc.start_date,
        )

        no_of_periods = int(
            total_days
            / (30 * period_months)
        )

        if no_of_periods <= 0:
            no_of_periods = 1

        created = []

        for i in range(
            1,
            no_of_periods + 1,
        ):

            posting_date = getdate(
                add_months(
                    self.doc.start_date,
                    (i - 1) * period_months,
                )
            )

            if posting_date > getdate(
                self.doc.end_date
            ):
                break

            amort_cheque_no = (
                f"{self.doc.reference_no}-AMORT{i}"
            )

            if self._je_exists(
                amort_cheque_no,
                self.doc.company,
            ):
                continue

            je = frappe.new_doc(
                "Journal Entry"
            )

            je.voucher_type = "Deferred Revenue"
            je.naming_series = "IRJ-JRN-.#####"
            je.paid_to_or_received_from = (
                self.doc.payer_name
            )
            je.company = self.doc.company
            je.transaction_description = (
                self.doc.transaction_purposes
            )
            je.posting_date = posting_date
            je.user_remark = (
                self.doc.transaction_purposes
            )
            je.reference_document_no = (
                self.doc.name
            )
            je.cheque_no = amort_cheque_no
            je.cheque_date = posting_date

            amount = flt(
                self.doc.charge_amount
            )

            # Debit Deferred Revenue
            je.append(
                "accounts",
                {
                    "account": self.doc.deferred_revenue_account,
                    "debit_in_account_currency": amount,
                    "debit": amount,
                    "user_remark": self.doc.transaction_purposes,
                    "against_account": self.doc.revenue_account,
                },
            )

            # Credit Revenue
            je.append(
                "accounts",
                {
                    "account": self.doc.revenue_account,
                    "credit_in_account_currency": amount,
                    "credit": amount,
                    "user_remark": self.doc.transaction_purposes,
                    "cost_center": self.doc.cost_center,
                    "against_account": self.doc.deferred_revenue_account,
                },
            )

            je.set_total_debit_credit()

            je.flags.ignore_permissions = True
            je.flags.ignore_fiscal_year = True

            je.insert(ignore_permissions=True)
            je.submit()

            created.append(
                je.name
            )

        if created:

            frappe.logger().info(
                f"Created {len(created)} amortization "
                f"entries for {self.doc.name}"
            )

            frappe.msgprint(
                _(
                    "Created {0} amortization entries"
                ).format(len(created)),
                indicator="green",
            )

        return created

    # =========================================================================
    # Shared Journal Entry Helpers
    # =========================================================================

    def _init_je(self, voucher_type="Bank Entry"):

        je = frappe.new_doc(
            "Journal Entry"
        )

        je.voucher_type = voucher_type
        je.naming_series = "BJV-.#####"

        je.paid_to_or_received_from = (
            self.doc.payer_name
        )

        je.company = self.doc.company

        je.custom_bank_account = (
            self.doc.remittance_bank
        )

        je.transaction_description = (
            self.doc.transaction_purposes
        )

        je.posting_date = (
            self.doc.transaction_date
        )

        je.user_remark = (
            self.doc.transaction_purposes
        )

        je.reference_document_no = (
            self.doc.name
        )

        je.cheque_no = (
            self.doc.reference_no
        )

        je.cheque_date = (
            self.doc.transaction_date
        )

        je.multi_currency = (
            0
            if self.is_local_currency
            else 1
        )

        return je

    def _submit_je(self, je):

        je.set_total_debit_credit()

        if not je.accounts:
            frappe.throw(
                _("Journal Entry has no account rows")
            )

        if flt(je.total_debit) <= 0:
            frappe.throw(
                _("Journal Entry debit total must be greater than zero")
            )

        if abs(
            flt(je.total_debit)
            - flt(je.total_credit)
        ) > 0.01:
            frappe.throw(
                _(
                    "Journal Entry is not balanced. "
                    "Debit: {0}, Credit: {1}"
                ).format(
                    je.total_debit,
                    je.total_credit,
                )
            )

        je.flags.ignore_permissions = True
        je.flags.ignore_fiscal_year = True

        je.insert(
            ignore_permissions=True
        )

        je.submit()

        self.created_entries.append(
            {
                "doctype": "Journal Entry",
                "name": je.name,
                "amount": je.total_debit,
            }
        )

        frappe.logger().info(
            f"Journal Entry {je.name} created "
            f"and submitted for Receipt {self.doc.name}"
        )

        frappe.msgprint(
            _("Journal Entry {0} created").format(
                je.name
            ),
            indicator="green",
        )

        return self.created_entries

    def get_created_entries_summary(self):

        return {
            "total_entries": len(
                self.created_entries
            ),
            "entries": self.created_entries,
        }


# ============================================================================
# Receipt Accounting Entry Canceller
# ============================================================================

class ReceiptAccountingEntryCanceller:

    def __init__(self, doc):

        self.doc = doc
        self.cancelled_entries = []

    def cancel_all_entries(self):

        frappe.logger().info(
            f"Cancelling accounting entries "
            f"for Receipt {self.doc.name}"
        )

        self._cancel_journal_entries()
        self._cancel_payment_entries()

        if self.cancelled_entries:

            frappe.msgprint(
                _(
                    "Cancelled {0} accounting entries"
                ).format(
                    len(self.cancelled_entries)
                ),
                indicator="orange",
            )

        return self.cancelled_entries

    def _cancel_journal_entries(self):

        je_list = frappe.db.sql(
            """
            SELECT name
            FROM `tabJournal Entry`
            WHERE
                (cheque_no = %s OR cheque_no LIKE %s)
                AND docstatus = 1
            LIMIT 100
            """,
            (
                self.doc.reference_no,
                f"{self.doc.reference_no}-%",
            ),
            as_dict=True,
        )

        for je_row in je_list:

            je = frappe.get_doc(
                "Journal Entry",
                je_row.name,
            )

            # Do NOT swallow the exception.
            # If cancellation fails, the parent Receipt cancellation
            # must fail too.
            je.cancel()

            self.cancelled_entries.append(
                {
                    "doctype": "Journal Entry",
                    "name": je.name,
                    "status": "Cancelled",
                }
            )

    def _cancel_payment_entries(self):

        pe_list = frappe.db.get_all(
            "Payment Entry",
            filters={
                "reference_no": self.doc.reference_no,
                "docstatus": 1,
            },
            fields=["name"],
            limit=100,
        )

        for pe_row in pe_list:

            pe = frappe.get_doc(
                "Payment Entry",
                pe_row.name,
            )

            # Do NOT swallow the exception.
            pe.cancel()

            self.cancelled_entries.append(
                {
                    "doctype": "Payment Entry",
                    "name": pe.name,
                    "status": "Cancelled",
                }
            )


# ============================================================================
# Utility Functions
# ============================================================================

def format_currency_display(
    amount,
    currency,
):
    """
    Format currency for display.
    """

    try:

        return fmt_money(
            amount,
            currency=currency,
        )

    except Exception:

        return (
            f"{currency} "
            f"{flt(amount):,.2f}"
        )


def send_customer_email_async(
    receipt_name,
):
    """
    Async wrapper for customer email.

    Email failures must never affect the Receipt's accounting transaction.
    """

    try:

        receipt = frappe.get_doc(
            "Receipts",
            receipt_name,
        )

        receipt.send_customer_email()

        send_internal_receipt_notification(
            receipt
        )

    except Exception:

        frappe.log_error(
            frappe.get_traceback(),
            f"Async Email Error - {receipt_name}",
        )


# ============================================================================
# Receipts Document
# ============================================================================

class Receipts(Document):

    # ========================================================================
    # VALIDATION
    # ========================================================================

    def validate(self):

        self.validate_required_fields()
        self.validate_dates()
        self.validate_amounts()
        self.validate_bank_account()

        self.calculate_local_currency_amount()

        if (
            self.is_multi_line
            and self.receipts_item_line
        ):

            self.validate_multi_line_items()

            self.total = sum(
                flt(row.amount)
                for row in self.receipts_item_line
            )

        if (
            self.is_related_coy_trans
            and self.related_company_receipts
        ):

            self.total_rcoy = sum(
                flt(row.amount)
                for row in self.related_company_receipts
            )

        if self.receipts_reference:

            self.validate_customer_invoice_allocation()

            self.total_outstanding_invoice = sum(
                flt(row.allocated_amount)
                for row in self.receipts_reference
            )

        self.populate_related_party_names()

        self.validate_duplicate_receipt()
        self.validate_unallocated_amount()

    # ========================================================================
    # Required Fields
    # ========================================================================

    def validate_required_fields(self):

        if not self.trans_type:
            frappe.throw(
                _("Please select a Transaction Type")
            )

        if not self.company:
            frappe.throw(
                _("Please select a Company")
            )

        if not self.receipt_currency:
            frappe.throw(
                _("Please select Receipt Currency")
            )

        if (
            self.create_accounting_entries
            and not self.remittance_bank
        ):
            frappe.throw(
                _(
                    "Remittance Bank is required "
                    "for creating accounting entries"
                )
            )

        if (
            self.create_accounting_entries
            and not self.remittance_bank_gl
        ):
            frappe.throw(
                _(
                    "Remittance Bank GL is required "
                    "for creating accounting entries"
                )
            )

        if (
            self.trans_type
            in [
                "Customer Receipt",
                "Receive from One-Off",
            ]
            and not self.customer_id
        ):
            frappe.throw(
                _(
                    "Customer is required for Customer Receipt transactions"
                )
            )

        if (
            self.trans_type
            not in [
                "Customer Receipt",
                "Customer Refund",
            ]
            and not self.payer_name
        ):
            frappe.throw(
                _(
                    "Payer Name is required for {0}"
                ).format(
                    self.trans_type
                )
            )

        if (
            self.trans_type
            not in [
                "Customer Receipt",
                "Customer Refund",
            ]
            and not self.is_multi_line
            and not self.account_to_credit
        ):
            frappe.throw(
                _(
                    "Account to Credit is required for {0}"
                ).format(
                    self.trans_type
                )
            )

    # ========================================================================
    # Dates
    # ========================================================================

    def validate_dates(self):

        if not self.transaction_date:

            frappe.throw(
                _("Transaction Date is mandatory")
            )

        if (
            getdate(self.transaction_date)
            > getdate(nowdate())
        ):

            frappe.throw(
                _("Transaction Date cannot be in the future")
            )

        if self.amortize:

            if (
                not self.start_date
                or not self.end_date
            ):

                frappe.throw(
                    _(
                        "Start Date and End Date are mandatory "
                        "for amortization"
                    )
                )

            if (
                getdate(self.end_date)
                <= getdate(self.start_date)
            ):

                frappe.throw(
                    _("End Date must be after Start Date")
                )

    # ========================================================================
    # Amounts
    # ========================================================================

    def validate_amounts(self):

        if not self.company:

            frappe.throw(
                _("Company is required")
            )

        company_currency = frappe.db.get_value(
            "Company",
            self.company,
            "default_currency",
        )

        if not company_currency:

            frappe.throw(
                _(
                    "Company currency not found for {0}"
                ).format(
                    self.company
                )
            )

        if (
            self.receipt_currency
            == company_currency
        ):

            if (
                not self.amount_received
                or self.amount_received <= 0
            ):

                frappe.throw(
                    _(
                        "Amount Received must be greater than zero"
                    )
                )

        else:

            if (
                not self.amount_received_in_fc
                or self.amount_received_in_fc <= 0
            ):

                frappe.throw(
                    _(
                        "Amount Received in Foreign Currency "
                        "must be greater than zero"
                    )
                )

            if (
                not self.exchange_rate
                or self.exchange_rate <= 0
            ):

                frappe.throw(
                    _("Exchange Rate must be greater than zero")
                )

    # ========================================================================
    # Bank Account
    # ========================================================================

    def validate_bank_account(self):

        if not self.remittance_bank:
            return

        bank = frappe.db.get_value(
            "Bank Account",
            self.remittance_bank,
            [
                "account",
                "account_currency",
            ],
            as_dict=True,
        )

        if not bank:

            frappe.throw(
                _(
                    "Bank Account {0} not found"
                ).format(
                    self.remittance_bank
                )
            )

        if not self.company:
            return

        company_currency = frappe.db.get_value(
            "Company",
            self.company,
            "default_currency",
        )

        if (
            self.receipt_currency
            != company_currency
        ):

            if (
                bank.account_currency
                and bank.account_currency
                != self.receipt_currency
            ):

                frappe.msgprint(
                    _(
                        "Warning: Bank account currency ({0}) "
                        "does not match receipt currency ({1})"
                    ).format(
                        bank.account_currency,
                        self.receipt_currency,
                    ),
                    alert=True,
                    indicator="orange",
                )

    # ========================================================================
    # Invoice Allocation
    # ========================================================================

    def validate_customer_invoice_allocation(self):

        if (
            self.trans_type
            != "Customer Receipt"
        ):
            return

        if not self.receipts_reference:
            return

        total_allocated = sum(
            flt(row.allocated_amount)
            for row in self.receipts_reference
        )

        receipt_amount = (
            self.amount_received
            or self.amount_received_in_fc
            or 0
        )

        if (
            total_allocated
            > receipt_amount
        ):

            frappe.throw(
                _(
                    "Total allocated amount {0} {1:,.2f} "
                    "cannot exceed receipt amount {2} {3:,.2f}"
                ).format(
                    self.receipt_currency,
                    total_allocated,
                    self.receipt_currency,
                    receipt_amount,
                )
            )

        for row in self.receipts_reference:

            if (
                flt(row.allocated_amount)
                > flt(row.outstanding_amount)
            ):

                frappe.throw(
                    _(
                        "Row {0}: Allocated amount cannot "
                        "exceed outstanding amount"
                    ).format(
                        row.idx
                    )
                )

            if (
                flt(row.allocated_amount)
                < 0
            ):

                frappe.throw(
                    _(
                        "Row {0}: Allocated amount "
                        "cannot be negative"
                    ).format(
                        row.idx
                    )
                )

    # ========================================================================
    # Multi-Line
    # ========================================================================

    def validate_multi_line_items(self):

        if not self.is_multi_line:
            return

        if not self.receipts_item_line:

            frappe.throw(
                _("Please add line items for multi-line receipt")
            )

        total = sum(
            flt(row.amount)
            for row in self.receipts_item_line
        )

        receipt_amount = (
            self.local_currency_amount
            or self.amount_received
            or 0
        )

        for row in self.receipts_item_line:

            if not row.gl_account:

                frappe.throw(
                    _(
                        "Row {0}: GL Account is mandatory"
                    ).format(
                        row.idx
                    )
                )

            if (
                not row.amount
                or row.amount <= 0
            ):

                frappe.throw(
                    _(
                        "Row {0}: Amount must be greater than zero"
                    ).format(
                        row.idx
                    )
                )

        if (
            abs(total - receipt_amount)
            > 0.01
        ):

            frappe.msgprint(
                _(
                    "Warning: Multi-line total ({0}) "
                    "does not match receipt amount ({1})"
                ).format(
                    total,
                    receipt_amount,
                ),
                alert=True,
                indicator="orange",
            )

    # ========================================================================
    # Duplicate Receipt Warning
    # ========================================================================

    def validate_duplicate_receipt(self):

        if (
            not self.customer_id
            or not self.amount_received
        ):
            return

        if not self.transaction_date:
            return

        from_date = add_days(
            self.transaction_date,
            -7,
        )

        similar_receipts = frappe.db.sql(
            """
            SELECT
                name,
                transaction_date,
                amount_received,
                reference_no
            FROM `tabReceipts`
            WHERE
                customer_id = %(customer)s
                AND ABS(
                    amount_received - %(amount)s
                ) < 0.01
                AND transaction_date
                    BETWEEN %(from_date)s
                    AND %(to_date)s
                AND docstatus != 2
                AND name != %(current)s
            """,
            {
                "customer": self.customer_id,
                "amount": self.amount_received,
                "from_date": from_date,
                "to_date": self.transaction_date,
                "current": self.name or "new",
            },
            as_dict=True,
        )

        if similar_receipts:

            receipt_list = ", ".join(
                r.name
                for r in similar_receipts
            )

            frappe.msgprint(
                _(
                    "Warning: Similar receipt(s) found "
                    "in the last 7 days: {0}"
                ).format(
                    receipt_list
                ),
                alert=True,
                indicator="orange",
            )

    # ========================================================================
    # Unique Reference
    # ========================================================================

    def validate_unique_reference(self):

        if not self.reference_no:
            return

        filters = {
            "reference_no": self.reference_no,
            "docstatus": ["!=", 2],
            "name": ["!=", self.name],
        }

        exists = frappe.db.exists(
            "Receipts",
            filters,
        )

        if exists:

            frappe.throw(
                _(
                    "Reference number {0} already exists "
                    "in Receipt {1}"
                ).format(
                    self.reference_no,
                    exists,
                )
            )

    # ========================================================================
    # Local Currency
    # ========================================================================

    def calculate_local_currency_amount(self):

        if not self.company:
            return

        company_currency = frappe.db.get_value(
            "Company",
            self.company,
            "default_currency",
        )

        if not company_currency:
            return

        if (
            self.receipt_currency
            == company_currency
        ):

            self.local_currency_amount = (
                self.amount_received
                or 0
            )

        else:

            exchange_rate = (
                self.exchange_rate
                or 1
            )

            amount_fc = (
                self.amount_received_in_fc
                or 0
            )

            self.local_currency_amount = (
                amount_fc * exchange_rate
            )

    # ========================================================================
    # Related Party Names
    # ========================================================================

    def populate_related_party_names(self):

        for row in (
            self.related_company_receipts
            or []
        ):

            if not row.party_type or not row.party:
                continue

            try:

                if row.party_type == "Supplier":

                    doctype = "Supplier"
                    field_name = "supplier_name"

                else:

                    doctype = "Customer"
                    field_name = "customer_name"

                party_name = frappe.db.get_value(
                    doctype,
                    row.party,
                    field_name,
                )

                if party_name:
                    row.party_name = party_name

            except Exception as e:

                frappe.log_error(
                    f"Error fetching party name: {str(e)}",
                    "Party Name Error",
                )

    # ========================================================================
    # Unallocated Amount
    # ========================================================================

    def validate_unallocated_amount(self):

        if (
            self.trans_type
            != "Customer Receipt"
        ):
            return

        if not self.receipts_reference:

            frappe.msgprint(
                _(
                    "Info: Receipt amount is not allocated "
                    "to any invoice. This will create a credit balance."
                ),
                alert=True,
                indicator="blue",
            )

            return

        total_allocated = sum(
            flt(row.allocated_amount)
            for row in self.receipts_reference
        )

        receipt_amount = (
            self.amount_received
            or self.amount_received_in_fc
            or 0
        )

        unallocated = (
            receipt_amount
            - total_allocated
        )

        if unallocated > 0.01:

            frappe.msgprint(
                _(
                    "Info: Unallocated amount of {0} "
                    "will remain as customer credit balance"
                ).format(
                    frappe.format_value(
                        unallocated,
                        {
                            "fieldtype": "Currency",
                            "currency": self.receipt_currency,
                        },
                    )
                ),
                alert=True,
                indicator="blue",
            )

    # ========================================================================
    # BEFORE SUBMIT
    # ========================================================================

    def before_submit(self):
        """
        IMPORTANT:

        This method performs validation and prepares fields only.

        It DOES NOT create Journal Entries or Payment Entries.

        Accounting is created in on_submit().

        This prevents another accounting document from being submitted
        while the Receipt is still in the pre-submit lifecycle.
        """

        self.validate_required_fields()
        self.validate_unique_reference()

        if (
            self.create_accounting_entries
            and not self.reference_no
        ):

            frappe.throw(
                _(
                    "Reference No is required when "
                    "Create Accounting Entries is enabled."
                )
            )

        if (
            self.amount_received
            and self.amount_received > 0
        ):

            amount = self.amount_received

        elif self.amount_received_in_fc:

            amount = self.amount_received_in_fc

        else:

            amount = 0

        if amount > 0:

            amount_words = money_in_words(
                amount,
                self.receipt_currency,
            )

            if not amount_words.upper().startswith(
                self.receipt_currency.upper()
            ):

                amount_words = (
                    f"{self.receipt_currency} "
                    f"{amount_words}"
                )

            self.amount_in_words = amount_words

        self.title = (
            self.customer_name
            if self.customer_name
            else self.payer_name
        )

        self.issued_by = frappe.session.user

        self.date = (
            self.transaction_date
            or today()
        )

        self.auth_date = today()

        self.authorised_by = (
            frappe.session.user
        )

        self.calculate_local_currency_amount()

        frappe.logger().info(
            f"Preparing Receipt {self.name} "
            f"for submission - "
            f"Trans Type: {self.trans_type}, "
            f"Create Entries: "
            f"{self.create_accounting_entries}"
        )

    # ========================================================================
    # ON SUBMIT
    # ========================================================================

    def on_submit(self):
        """
        Create accounting entries AFTER Frappe has moved the Receipt into
        submitted lifecycle.

        IMPORTANT:

        There is intentionally NO frappe.db.commit() here.

        If any accounting operation raises an exception, Frappe will roll
        the complete request back. This protects the Receipt and accounting
        entries from being left in an inconsistent state.
        """

        frappe.logger().info(
            f"Submitting accounting for Receipt {self.name}"
        )

        # ---------------------------------------------------------------
        # Accounting
        # ---------------------------------------------------------------

        if self.create_accounting_entries:

            controller = ReceiptAccountingController(
                self
            )

            if controller.accounting_entries_exist():

                frappe.msgprint(
                    _(
                        "Accounting entries already exist for "
                        "reference {0}. No duplicate entries "
                        "will be created."
                    ).format(
                        self.reference_no
                    ),
                    indicator="blue",
                    alert=True,
                )

            else:

                created = (
                    controller.create_accounting_entries(
                        skip_duplicate_check=False
                    )
                )

                entries_expected = (
                    self.trans_type
                    in (
                        "Customer Receipt",
                        "Receive from One-Off",
                        "Revenue Receipt",
                        "Transfer In",
                    )
                    or self.is_related_coy_trans
                )

                if (
                    entries_expected
                    and not created
                ):

                    frappe.throw(
                        _(
                            "Submission failed because no accounting "
                            "entries were created for Receipt {0}."
                        ).format(
                            self.name
                        ),
                        title=_(
                            "Accounting Entries Required"
                        ),
                    )

                frappe.logger().info(
                    f"Created {len(created)} "
                    f"accounting entries for {self.name}"
                )

        else:

            frappe.msgprint(
                _(
                    "'Create Accounting Entries' is unchecked. "
                    "This Receipt will submit without accounting entries."
                ),
                indicator="blue",
                title=_(
                    "Accounting Entries Skipped"
                ),
            )

        # ---------------------------------------------------------------
        # Amortization
        # ---------------------------------------------------------------

        if (
            self.create_accounting_entries
            and self.amortize
            and self.trans_type
            == "Revenue Receipt"
        ):

            controller = ReceiptAccountingController(
                self
            )

            # IMPORTANT:
            # No savepoint and no rollback here.
            #
            # If amortization is mandatory for this Receipt and it fails,
            # the Receipt submission must fail as well.
            controller.create_amortization_journals()

        # ---------------------------------------------------------------
        # Confirmation email
        # ---------------------------------------------------------------

        # Email is asynchronous and deliberately does not affect
        # the accounting transaction.
        frappe.enqueue(
            method=(
                "ecclesia.ecclesia.doctype.receipts.receipts."
                "send_customer_email_async"
            ),
            queue="short",
            timeout=300,
            is_async=True,
            receipt_name=self.name,
        )

        frappe.logger().info(
            f"Receipt {self.name} successfully submitted"
        )

    # ========================================================================
    # ON CANCEL
    # ========================================================================

    def on_cancel(self):

        frappe.logger().info(
            f"Cancelling Receipt {self.name}"
        )

        self.validate_before_cancel()

        # IMPORTANT:
        # Cancellation errors are deliberately not swallowed.
        # If accounting entries cannot be cancelled, the Receipt cancellation
        # must fail and Frappe will roll back the transaction.
        if self.create_accounting_entries:

            ReceiptAccountingEntryCanceller(
                self
            ).cancel_all_entries()

        frappe.logger().info(
            f"Receipt {self.name} cancellation accounting completed"
        )

    # ========================================================================
    # Before Cancel Validation
    # ========================================================================

    def validate_before_cancel(self):

        linked_docs = (
            self.get_linked_documents()
        )

        if linked_docs:

            msg = _(
                "The following accounting entries "
                "will be cancelled:"
            )

            for doctype, docs in linked_docs.items():

                msg += (
                    f"\n{doctype}: "
                    f"{', '.join(docs)}"
                )

            frappe.msgprint(
                msg,
                alert=True,
                indicator="orange",
            )

    # ========================================================================
    # Linked Documents
    # ========================================================================

    def get_linked_documents(self):

        linked = {}

        je_list = frappe.get_all(
            "Journal Entry",
            filters={
                "cheque_no": self.reference_no,
                "docstatus": 1,
            },
            pluck="name",
        )

        # Include RC and AMORT entries
        if self.reference_no:

            related_je_list = frappe.db.sql(
                """
                SELECT name
                FROM `tabJournal Entry`
                WHERE
                    cheque_no LIKE %s
                    AND docstatus = 1
                """,
                (
                    f"{self.reference_no}-%",
                ),
                as_list=True,
            )

            for row in related_je_list:

                if row[0] not in je_list:
                    je_list.append(row[0])

        if je_list:

            linked[
                "Journal Entry"
            ] = je_list

        pe_list = frappe.get_all(
            "Payment Entry",
            filters={
                "reference_no": self.reference_no,
                "docstatus": 1,
            },
            pluck="name",
        )

        if pe_list:

            linked[
                "Payment Entry"
            ] = pe_list

        return linked

    # ========================================================================
    # Customer Email
    # ========================================================================

    def send_customer_email(self):

        if not self.customer_id:
            return

        try:

            customer = frappe.get_doc(
                "Customer",
                self.customer_id,
            )

            if not customer.email_id:
                return

            print_format = (
                frappe.db.get_single_value(
                    "Accounts Settings",
                    "default_receipt_print_format",
                )
                or "Standard"
            )

            pdf_content = frappe.attach_print(
                doctype=self.doctype,
                name=self.name,
                print_format=print_format,
                doc=self,
            )

            subject = _(
                "Payment Receipt - {0}"
            ).format(
                self.name
            )

            message = f"""
            <p>Dear {self.customer_name},</p>

            <p>
                Thank you for your payment. Please find attached
                your official receipt for the payment received.
            </p>

            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                        <strong>Receipt No:</strong>
                    </td>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                        {self.name}
                    </td>
                </tr>

                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                        <strong>Date:</strong>
                    </td>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                        {self.transaction_date}
                    </td>
                </tr>

                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                        <strong>Amount Received:</strong>
                    </td>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                        {self.amount_in_words}
                    </td>
                </tr>

                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                        <strong>Reference No:</strong>
                    </td>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                        {self.reference_no}
                    </td>
                </tr>
            </table>

            <p>
                If you have any questions, please don't hesitate
                to contact us.
            </p>

            <p>
                Best regards,<br>
                {self.company}
            </p>
            """

            frappe.sendmail(
                recipients=[
                    customer.email_id
                ],
                subject=subject,
                message=message,
                attachments=[
                    {
                        "fname": f"{self.name}.pdf",
                        "fcontent": pdf_content,
                    }
                ],
                reference_doctype=self.doctype,
                reference_name=self.name,
            )

            frappe.logger().info(
                f"Receipt confirmation email sent to "
                f"{customer.email_id}"
            )

        except Exception:

            # Email failure must never affect accounting.
            frappe.log_error(
                frappe.get_traceback(),
                "Receipt Customer Email Error",
            )


# ============================================================================
# AI SMART ALLOCATION
# ============================================================================

@frappe.whitelist()
def ai_smart_allocation(doc_name):
    """
    AI-powered invoice allocation.

    A submitted Receipt must NEVER be modified by this method.
    """

    doc = frappe.get_doc(
        "Receipts",
        doc_name,
    )

    if doc.docstatus != 0:

        frappe.throw(
            _(
                "Invoice allocation can only be performed "
                "while the Receipt is in Draft."
            )
        )

    if not doc.customer_id:

        frappe.throw(
            _("Please select a customer first")
        )

    amount_to_allocate = (
        doc.local_currency_amount
        or doc.amount_received
        or (
            doc.amount_received_in_fc
            * doc.exchange_rate
            if doc.amount_received_in_fc
            else 0
        )
    )

    if (
        not amount_to_allocate
        or amount_to_allocate <= 0
    ):

        frappe.throw(
            _("Please enter a valid amount")
        )

    invoices = frappe.db.sql(
        """
        SELECT
            name,
            posting_date,
            due_date,
            grand_total,
            outstanding_amount,
            payment_terms_template,
            DATEDIFF(
                CURDATE(),
                due_date
            ) AS days_overdue,

            CASE
                WHEN DATEDIFF(CURDATE(), due_date) > 90
                    THEN 1

                WHEN DATEDIFF(CURDATE(), due_date) > 60
                    THEN 2

                WHEN DATEDIFF(CURDATE(), due_date) > 30
                    THEN 3

                WHEN DATEDIFF(CURDATE(), due_date) > 0
                    THEN 4

                ELSE 5
            END AS priority

        FROM `tabSales Invoice`

        WHERE
            customer = %s
            AND docstatus = 1
            AND outstanding_amount > 0

        ORDER BY
            priority ASC,
            due_date ASC,
            posting_date ASC
        """,
        (
            doc.customer_id,
        ),
        as_dict=True,
    )

    if not invoices:

        frappe.msgprint(
            _("No outstanding invoices found for this customer")
        )

        return []

    doc.receipts_reference = []

    remaining_amount = (
        amount_to_allocate
    )

    allocated_invoices = []

    for invoice in invoices:

        if remaining_amount <= 0:
            break

        allocated_amount = min(
            remaining_amount,
            invoice.outstanding_amount,
        )

        doc.append(
            "receipts_reference",
            {
                "date": invoice.posting_date,
                "reference_doctype": "Sales Invoice",
                "reference_name": invoice.name,
                "due_date": invoice.due_date,
                "bill_no": invoice.name,
                "payment_term": (
                    invoice.payment_terms_template
                    or ""
                ),
                "total_amount": invoice.grand_total,
                "outstanding_amount": (
                    invoice.outstanding_amount
                ),
                "allocated_amount": allocated_amount,
                "exchange_rate": 1,
                "exchange_gain_loss": 0,
            },
        )

        allocated_invoices.append(
            {
                "invoice": invoice.name,
                "amount": allocated_amount,
                "days_overdue": invoice.days_overdue,
                "priority": invoice.priority,
            }
        )

        remaining_amount -= (
            allocated_amount
        )

    doc.save()

    return {
        "total_allocated": (
            amount_to_allocate
            - remaining_amount
        ),
        "remaining_amount": remaining_amount,
        "invoices_matched": len(
            allocated_invoices
        ),
        "allocations": allocated_invoices,
    }


# ============================================================================
# PREVIEW ALLOCATION
# ============================================================================

@frappe.whitelist()
def preview_allocation(doc_name):

    doc = frappe.get_doc(
        "Receipts",
        doc_name,
    )

    if not doc.receipts_reference:

        return (
            "<div class='alert alert-warning'>"
            "No invoice allocations found"
            "</div>"
        )

    total_allocated = sum(
        flt(row.allocated_amount)
        for row in doc.receipts_reference
    )

    total_outstanding = sum(
        flt(row.outstanding_amount)
        for row in doc.receipts_reference
    )

    html = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px;">

        <h3 style="
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        ">
            Invoice Allocation Preview
        </h3>

        <div style="
            background: linear-gradient(
                135deg,
                #667eea 0%,
                #764ba2 100%
            );
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        ">

            <div style="
                display: grid;
                grid-template-columns:
                    repeat(3, 1fr);
                gap: 20px;
            ">

                <div style="text-align: center;">
                    <div style="font-size: 14px;">
                        Amount Received
                    </div>

                    <div style="
                        font-size: 24px;
                        font-weight: bold;
                        margin-top: 5px;
                    ">
                        {doc.receipt_currency}
                        {flt(doc.local_currency_amount, 2):,.2f}
                    </div>
                </div>

                <div style="text-align: center;">
                    <div style="font-size: 14px;">
                        Total Allocated
                    </div>

                    <div style="
                        font-size: 24px;
                        font-weight: bold;
                        margin-top: 5px;
                    ">
                        {doc.receipt_currency}
                        {total_allocated:,.2f}
                    </div>
                </div>

                <div style="text-align: center;">
                    <div style="font-size: 14px;">
                        Remaining
                    </div>

                    <div style="
                        font-size: 24px;
                        font-weight: bold;
                        margin-top: 5px;
                    ">
                        {doc.receipt_currency}
                        {flt(
                            doc.local_currency_amount
                            - total_allocated,
                            2
                        ):,.2f}
                    </div>
                </div>

            </div>
        </div>

        <table style="
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        ">

            <thead>

                <tr style="
                    background: #34495e;
                    color: white;
                ">

                    <th style="padding: 15px;">
                        Invoice
                    </th>

                    <th style="padding: 15px;">
                        Due Date
                    </th>

                    <th style="padding: 15px;">
                        Outstanding
                    </th>

                    <th style="padding: 15px;">
                        Allocated
                    </th>

                    <th style="padding: 15px;">
                        Remaining
                    </th>

                    <th style="padding: 15px;">
                        Status
                    </th>

                </tr>

            </thead>

            <tbody>
    """

    for i, row in enumerate(
        doc.receipts_reference
    ):

        remaining = (
            flt(row.outstanding_amount)
            - flt(row.allocated_amount)
        )

        status = (
            "Fully Paid"
            if remaining <= 0
            else "Partially Paid"
        )

        status_color = (
            "#27ae60"
            if remaining <= 0
            else "#f39c12"
        )

        bg_color = (
            "#f8f9fa"
            if i % 2 == 0
            else "#ffffff"
        )

        is_overdue = False
        overdue_days = 0

        if row.due_date:

            overdue_days = date_diff(
                nowdate(),
                row.due_date,
            )

            is_overdue = (
                overdue_days > 0
            )

        due_date_display = (
            row.due_date
            or "N/A"
        )

        if is_overdue:

            due_date_display = (
                f"<span style='color: #e74c3c; "
                f"font-weight: bold;'>"
                f"{row.due_date} "
                f"({overdue_days} days overdue)"
                f"</span>"
            )

        html += f"""
            <tr style="
                background: {bg_color};
            ">

                <td style="padding: 12px;">
                    <strong>
                        {row.reference_name}
                    </strong>
                </td>

                <td style="
                    padding: 12px;
                    text-align: center;
                ">
                    {due_date_display}
                </td>

                <td style="
                    padding: 12px;
                    text-align: right;
                ">
                    {flt(
                        row.outstanding_amount,
                        2
                    ):,.2f}
                </td>

                <td style="
                    padding: 12px;
                    text-align: right;
                    font-weight: bold;
                ">
                    {flt(
                        row.allocated_amount,
                        2
                    ):,.2f}
                </td>

                <td style="
                    padding: 12px;
                    text-align: right;
                ">
                    {remaining:,.2f}
                </td>

                <td style="
                    padding: 12px;
                    text-align: center;
                ">
                    <span style="
                        background: {status_color};
                        color: white;
                        padding: 5px 10px;
                        border-radius: 15px;
                        font-size: 11px;
                        font-weight: bold;
                    ">
                        {status}
                    </span>
                </td>

            </tr>
        """

    html += f"""
            </tbody>

            <tfoot>

                <tr style="
                    background: #34495e;
                    color: white;
                    font-weight: bold;
                ">

                    <td colspan="2"
                        style="padding: 15px;">
                        TOTAL
                    </td>

                    <td style="
                        padding: 15px;
                        text-align: right;
                    ">
                        {total_outstanding:,.2f}
                    </td>

                    <td style="
                        padding: 15px;
                        text-align: right;
                    ">
                        {total_allocated:,.2f}
                    </td>

                    <td colspan="2"></td>

                </tr>

            </tfoot>

        </table>

    </div>
    """

    return html


# ============================================================================
# BULK ACKNOWLEDGEMENTS
# ============================================================================

@frappe.whitelist()
def send_bulk_acknowledgements(
    receipt_names,
    email_subject=None,
    include_pdf=1,
    custom_message=None,
):
    """
    Send acknowledgement emails for multiple submitted Receipts.

    This is a standalone request and is intentionally separate from the
    Receipt submission transaction.
    """

    if isinstance(
        receipt_names,
        str,
    ):

        receipt_names = json.loads(
            receipt_names
        )

    if not receipt_names:

        frappe.throw(
            _("No receipts selected")
        )

    success_count = 0
    failed_count = 0
    failed_receipts = []

    from frappe.utils import create_batch

    for batch in create_batch(
        receipt_names,
        50,
    ):

        for receipt_name in batch:

            try:

                doc = frappe.get_doc(
                    "Receipts",
                    receipt_name,
                )

                if doc.docstatus != 1:

                    failed_count += 1

                    failed_receipts.append(
                        {
                            "receipt": receipt_name,
                            "reason": "Not submitted",
                        }
                    )

                    continue

                if not doc.customer_id:

                    failed_count += 1

                    failed_receipts.append(
                        {
                            "receipt": receipt_name,
                            "reason": "No customer",
                        }
                    )

                    continue

                customer = frappe.get_doc(
                    "Customer",
                    doc.customer_id,
                )

                if not customer.email_id:

                    failed_count += 1

                    failed_receipts.append(
                        {
                            "receipt": receipt_name,
                            "reason": "No email address",
                        }
                    )

                    continue

                print_format = (
                    frappe.db.get_single_value(
                        "Accounts Settings",
                        "default_receipt_print_format",
                    )
                    or "Standard"
                )

                subject = (
                    email_subject
                    or f"Payment Receipt - {doc.name}"
                )

                message = f"""
                <div style="
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: 0 auto;
                ">

                    <div style="
                        background:
                        linear-gradient(
                            135deg,
                            #667eea 0%,
                            #764ba2 100%
                        );
                        color: white;
                        padding: 30px;
                        text-align: center;
                    ">

                        <h2>
                            Payment Receipt Confirmation
                        </h2>

                    </div>

                    <div style="
                        padding: 30px;
                        background: #ffffff;
                        border: 1px solid #e0e0e0;
                    ">

                        <p>
                            Dear {doc.customer_name},
                        </p>

                        <p>
                            Thank you for your payment.
                            We are pleased to confirm that
                            we have received your payment.
                        </p>

                        <table style="
                            width: 100%;
                            border-collapse: collapse;
                        ">

                            <tr>

                                <td style="
                                    padding: 15px;
                                    border-bottom:
                                    1px solid #e0e0e0;
                                    font-weight: bold;
                                ">
                                    Receipt No:
                                </td>

                                <td style="
                                    padding: 15px;
                                    border-bottom:
                                    1px solid #e0e0e0;
                                ">
                                    {doc.name}
                                </td>

                            </tr>

                            <tr>

                                <td style="
                                    padding: 15px;
                                    border-bottom:
                                    1px solid #e0e0e0;
                                    font-weight: bold;
                                ">
                                    Date:
                                </td>

                                <td style="
                                    padding: 15px;
                                    border-bottom:
                                    1px solid #e0e0e0;
                                ">
                                    {doc.transaction_date}
                                </td>

                            </tr>

                            <tr>

                                <td style="
                                    padding: 15px;
                                    font-weight: bold;
                                ">
                                    Amount Received:
                                </td>

                                <td style="
                                    padding: 15px;
                                    font-weight: bold;
                                ">
                                    {
                                        doc.amount_in_words
                                        or money_in_words(
                                            doc.local_currency_amount,
                                            doc.receipt_currency,
                                        )
                                    }
                                </td>

                            </tr>

                            <tr>

                                <td style="
                                    padding: 15px;
                                    font-weight: bold;
                                ">
                                    Reference No:
                                </td>

                                <td style="
                                    padding: 15px;
                                ">
                                    {doc.reference_no}
                                </td>

                            </tr>

                            <tr>

                                <td style="
                                    padding: 15px;
                                    font-weight: bold;
                                ">
                                    Payment Mode:
                                </td>

                                <td style="
                                    padding: 15px;
                                ">
                                    {doc.mode_of_payment or "N/A"}
                                </td>

                            </tr>

                        </table>
                """

                if custom_message:

                    message += f"""
                        <div style="
                            background: #e3f2fd;
                            padding: 15px;
                            margin: 20px 0;
                        ">

                            <strong>
                                Note:
                            </strong>

                            {custom_message}

                        </div>
                    """

                if doc.receipts_reference:

                    message += """
                        <h3>
                            Allocated to Invoices
                        </h3>

                        <table style="
                            width: 100%;
                            border-collapse: collapse;
                        ">

                            <thead>

                                <tr>

                                    <th>
                                        Invoice
                                    </th>

                                    <th>
                                        Amount Allocated
                                    </th>

                                </tr>

                            </thead>

                            <tbody>
                    """

                    for ref in doc.receipts_reference:

                        if (
                            ref.allocated_amount
                            and ref.allocated_amount > 0
                        ):

                            message += f"""
                                <tr>

                                    <td style="
                                        padding: 10px;
                                    ">
                                        {ref.reference_name}
                                    </td>

                                    <td style="
                                        padding: 10px;
                                        text-align: right;
                                    ">
                                        {doc.receipt_currency}
                                        {
                                            flt(
                                                ref.allocated_amount,
                                                2
                                            ):,.2f
                                        }
                                    </td>

                                </tr>
                            """

                    message += """
                            </tbody>
                        </table>
                    """

                message += f"""
                        <p>
                            If you have any questions regarding
                            this receipt, please don't hesitate
                            to contact us.
                        </p>

                        <p>
                            Best regards,<br>
                            <strong>
                                {doc.company}
                            </strong>
                        </p>

                    </div>

                    <div style="
                        background: #f5f5f5;
                        padding: 20px;
                        text-align: center;
                    ">

                        <small>
                            This is an automated email.
                        </small>

                    </div>

                </div>
                """

                attachments = []

                if int(include_pdf):

                    try:

                        pdf_content = frappe.attach_print(
                            doctype=doc.doctype,
                            name=doc.name,
                            print_format=print_format,
                            doc=doc,
                        )

                        attachments.append(
                            {
                                "fname": (
                                    f"{doc.name}.pdf"
                                ),
                                "fcontent": pdf_content,
                            }
                        )

                    except Exception as e:

                        frappe.log_error(
                            str(e),
                            "Receipt PDF Error",
                        )

                frappe.sendmail(
                    recipients=[
                        customer.email_id
                    ],
                    subject=subject,
                    message=message,
                    attachments=attachments,
                    reference_doctype=doc.doctype,
                    reference_name=doc.name,
                    now=True,
                )

                success_count += 1

            except Exception as e:

                failed_count += 1

                failed_receipts.append(
                    {
                        "receipt": receipt_name,
                        "reason": str(e),
                    }
                )

                frappe.log_error(
                    frappe.get_traceback(),
                    f"Bulk Acknowledgement Error - {receipt_name}",
                )

        # This function is a standalone batch process.
        # Committing here is acceptable.
        frappe.db.commit()

    return {
        "success_count": success_count,
        "failed_count": failed_count,
        "failed_receipts": failed_receipts,
        "total": len(receipt_names),
    }


# ============================================================================
# INTERNAL NOTIFICATION
# ============================================================================

@frappe.whitelist()
def send_internal_receipt_notification(
    receipt_doc,
):

    if isinstance(
        receipt_doc,
        str,
    ):

        receipt_doc = frappe.get_doc(
            "Receipts",
            receipt_doc,
        )

    try:

        recipients = []

        if receipt_doc.issued_by:

            issued_by_email = frappe.db.get_value(
                "User",
                receipt_doc.issued_by,
                "email",
            )

            if issued_by_email:
                recipients.append(
                    issued_by_email
                )

        if receipt_doc.authorised_by:

            auth_email = frappe.db.get_value(
                "User",
                receipt_doc.authorised_by,
                "email",
            )

            if auth_email:
                recipients.append(
                    auth_email
                )

        recipients = list(
            set(recipients)
        )

        if not recipients:

            frappe.log_error(
                "No internal recipients found",
                "Receipt Internal Notification Warning",
            )

            return {
                "success": False,
                "error": "No recipients",
            }

        amount_display = (
            format_currency_display(
                receipt_doc.amount_received
                or receipt_doc.amount_received_in_fc,
                receipt_doc.receipt_currency,
            )
        )

        message = f"""
        <div style="
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 0 auto;
        ">

            <h2>
                Receipt Processed Successfully
            </h2>

            <table style="
                width: 100%;
                border-collapse: collapse;
            ">

                <tr>

                    <td>
                        Receipt No:
                    </td>

                    <td>
                        {receipt_doc.name}
                    </td>

                </tr>

                <tr>

                    <td>
                        Customer/Payer:
                    </td>

                    <td>
                        {
                            receipt_doc.customer_name
                            or receipt_doc.payer_name
                            or "N/A"
                        }
                    </td>

                </tr>

                <tr>

                    <td>
                        Amount:
                    </td>

                    <td>
                        {amount_display}
                    </td>

                </tr>

                <tr>

                    <td>
                        Reference No:
                    </td>

                    <td>
                        {receipt_doc.reference_no or "N/A"}
                    </td>

                </tr>

                <tr>

                    <td>
                        Transaction Date:
                    </td>

                    <td>
                        {
                            receipt_doc.transaction_date
                            or "N/A"
                        }
                    </td>

                </tr>

                <tr>

                    <td>
                        Amount in Words:
                    </td>

                    <td>
                        {
                            receipt_doc.amount_in_words
                            or "N/A"
                        }
                    </td>

                </tr>

                <tr>

                    <td>
                        Transaction Type:
                    </td>

                    <td>
                        {
                            receipt_doc.trans_type
                            or "N/A"
                        }
                    </td>

                </tr>

            </table>

            <p>
                This receipt has been successfully processed
                and saved in the system.
            </p>

            <p>
                <a href="{get_url()}/app/receipts/{receipt_doc.name}">
                    View Receipt
                </a>
            </p>

        </div>
        """

        frappe.sendmail(
            recipients=recipients,
            subject=(
                f"Receipt Processed - "
                f"{receipt_doc.name}"
            ),
            message=message,
            reference_doctype="Receipts",
            reference_name=receipt_doc.name,
            now=True,
        )

        return {
            "success": True,
            "recipients": recipients,
            "message": "Email sent successfully",
        }

    except Exception as e:

        frappe.log_error(
            frappe.get_traceback(),
            "Receipt Internal Notification Error",
        )

        return {
            "success": False,
            "error": str(e),
        }


# ============================================================================
# UI: CREATE ACCOUNTING ENTRIES
# ============================================================================

@frappe.whitelist()
def create_accounting_entries_from_ui(
    receipt_name,
):
    """
    Recovery function for a Receipt that is already submitted but does not
    have accounting entries.

    This is a standalone request, therefore commit is acceptable after
    successful creation.
    """

    try:

        doc = frappe.get_doc(
            "Receipts",
            receipt_name,
        )

        if doc.docstatus != 1:

            frappe.throw(
                _(
                    "Receipt must be submitted before "
                    "creating accounting entries"
                )
            )

        controller = ReceiptAccountingController(
            doc
        )

        if controller.accounting_entries_exist():

            frappe.msgprint(
                _(
                    "Accounting entries already exist "
                    "for this receipt."
                ),
                indicator="blue",
                title=_(
                    "Entries Already Exist"
                ),
            )

            return (
                controller
                .get_created_entries_summary()
            )

        created = (
            controller.create_accounting_entries(
                skip_duplicate_check=False
            )
        )

        if created:

            frappe.db.commit()

            frappe.msgprint(
                _(
                    "Successfully created {0} "
                    "accounting entries."
                ).format(
                    len(created)
                ),
                indicator="green",
            )

        else:

            frappe.throw(
                _(
                    "No accounting entries were created."
                )
            )

        return (
            controller
            .get_created_entries_summary()
        )

    except Exception as e:

        frappe.log_error(
            frappe.get_traceback(),
            "Receipt Accounting UI Error",
        )

        frappe.throw(
            _(
                "Failed to create accounting entries: {0}"
            ).format(
                str(e)
            )
        )


# ============================================================================
# UI: CANCEL ACCOUNTING ENTRIES
# ============================================================================

@frappe.whitelist()
def cancel_accounting_entries_from_ui(
    receipt_name,
):

    try:

        doc = frappe.get_doc(
            "Receipts",
            receipt_name,
        )

        if doc.docstatus != 1:

            frappe.throw(
                _(
                    "Only a submitted Receipt "
                    "can have accounting entries cancelled."
                )
            )

        canceller = (
            ReceiptAccountingEntryCanceller(
                doc
            )
        )

        cancelled = (
            canceller.cancel_all_entries()
        )

        frappe.db.commit()

        return {
            "cancelled_count": len(
                cancelled
            ),
            "entries": cancelled,
        }

    except Exception as e:

        frappe.log_error(
            frappe.get_traceback(),
            "Receipt Cancellation UI Error",
        )

        frappe.throw(
            _(
                "Failed to cancel accounting entries: {0}"
            ).format(
                str(e)
            )
        )