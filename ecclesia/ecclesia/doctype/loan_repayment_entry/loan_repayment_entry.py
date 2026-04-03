# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, today


class LoanRepaymentEntry(Document):

    def validate(self):
        self._validate_loan_active()
        self._split_principal_interest()

    def on_submit(self):
        self._mark_installment_paid()
        self._update_loan_balances()
        self._create_repayment_journal_entry()
        self._check_loan_fully_repaid()

    def on_cancel(self):
        self._reverse_installment()
        self._reverse_loan_balances()
        self._cancel_repayment_journal_entry()

    # ── Validation ───────────────────────────────────────────────────

    def _validate_loan_active(self):
        status = frappe.db.get_value(
            "Employee Loan Application", self.loan, "status"
        )
        if status not in ("Disbursed", "Active"):
            frappe.throw(
                f"Loan {self.loan} is not active (status: {status}).",
                title="Inactive Loan"
            )

    def _split_principal_interest(self):
        loan    = frappe.get_doc("Employee Loan Application", self.loan)
        pending = sorted(
            [r for r in loan.repayment_schedule if r.status == "Pending"],
            key=lambda r: r.payment_date
        )
        if not pending:
            frappe.throw("No pending installments found for this loan.")

        next_inst = pending[0]
        self.principal_paid = flt(next_inst.principal)
        self.interest_paid  = flt(next_inst.interest)

        expected = flt(next_inst.monthly_amount)
        if abs(flt(self.amount_paid) - expected) > 1:
            frappe.msgprint(
                f"Payment of ₦{self.amount_paid:,.2f} differs from expected "
                f"₦{expected:,.2f}. Difference absorbed into principal.",
                indicator="orange", alert=True
            )
            diff = flt(self.amount_paid) - expected
            self.principal_paid = round(flt(next_inst.principal) + diff, 2)

    # ── Post-submit actions ──────────────────────────────────────────

    def _mark_installment_paid(self):
        loan    = frappe.get_doc("Employee Loan Application", self.loan)
        pending = sorted(
            [r for r in loan.repayment_schedule if r.status == "Pending"],
            key=lambda r: r.payment_date
        )
        if not pending:
            return
        frappe.db.set_value(
            "Loan Repayment Schedule", pending[0].name, {
                "status":      "Paid",
                "salary_slip": self.salary_slip or None,
            }
        )

    def _update_loan_balances(self):
        loan = frappe.get_doc("Employee Loan Application", self.loan)
        frappe.db.set_value("Employee Loan Application", self.loan, {
            "outstanding_principal": max(
                round(flt(loan.outstanding_principal) - flt(self.principal_paid), 2), 0
            ),
            "outstanding_interest": max(
                round(flt(loan.outstanding_interest)  - flt(self.interest_paid),  2), 0
            ),
            "total_amount_paid": round(
                flt(loan.total_amount_paid) + flt(self.amount_paid), 2
            ),
            "installments_paid": (loan.installments_paid or 0) + 1,
            "status": "Active",
        })

    def _check_loan_fully_repaid(self):
        loan = frappe.get_doc("Employee Loan Application", self.loan)
        loan.reload()
        if flt(loan.outstanding_principal) <= 0.01:
            frappe.db.set_value(
                "Employee Loan Application", self.loan, "status", "Closed"
            )
            user = frappe.db.get_value("Employee", loan.employee, "user_id")
            if user:
                frappe.sendmail(
                    recipients=[user],
                    subject=f"Loan fully repaid — {loan.loan_type}",
                    message=f"""
                        <div style="font-family:sans-serif;max-width:600px;
                                    padding:24px">
                            <p>Dear {loan.employee_name},</p>
                            <p>Congratulations! Your
                            <strong>{loan.loan_type}</strong>
                            loan has been fully repaid.</p>
                            <p>Total paid:
                            <strong>₦{loan.total_amount_paid:,.2f}</strong>
                            </p>
                        </div>
                    """,
                    now=False
                )

    def _create_repayment_journal_entry(self):
        loan      = frappe.get_doc("Employee Loan Application", self.loan)
        loan_type = frappe.get_doc("Employee Loan Type", loan.loan_type)
        company   = (
            frappe.db.get_default("Company") or
            frappe.get_all("Company", limit=1)[0].name
        )

        accounts = [
            {
                "account":                   loan_type.disbursement_account,
                "debit_in_account_currency": flt(self.principal_paid),
                "cost_center":               loan_type.cost_center,
            },
            {
                "account":                    loan_type.loan_account,
                "credit_in_account_currency": flt(self.principal_paid),
                "party_type":                 "Employee",
                "party":                      loan.employee,
                "cost_center":                loan_type.cost_center,
            },
        ]

        # Book interest income separately when applicable
        if flt(self.interest_paid) > 0 and loan_type.interest_income_account:
            accounts.append({
                "account":                   loan_type.disbursement_account,
                "debit_in_account_currency": flt(self.interest_paid),
                "cost_center":               loan_type.cost_center,
            })
            accounts.append({
                "account":                    loan_type.interest_income_account,
                "credit_in_account_currency": flt(self.interest_paid),
                "cost_center":                loan_type.cost_center,
            })

        je = frappe.get_doc({
            "doctype":      "Journal Entry",
            "voucher_type": "Journal Entry",
            "posting_date": self.payment_date or today(),
            "company":      company,
            "user_remark":  (
                f"Loan repayment — {loan.employee_name} ({self.loan})"
            ),
            "accounts": accounts
        })
        je.insert(ignore_permissions=True)
        je.submit()
        frappe.db.set_value(
            "Loan Repayment Entry", self.name, "journal_entry", je.name
        )

    # ── Cancel actions ───────────────────────────────────────────────

    def _reverse_installment(self):
        loan = frappe.get_doc("Employee Loan Application", self.loan)
        for row in loan.repayment_schedule:
            if row.salary_slip == self.salary_slip and row.status == "Paid":
                frappe.db.set_value(
                    "Loan Repayment Schedule", row.name, "status", "Pending"
                )
                break

    def _reverse_loan_balances(self):
        loan = frappe.get_doc("Employee Loan Application", self.loan)
        frappe.db.set_value("Employee Loan Application", self.loan, {
            "outstanding_principal": round(
                flt(loan.outstanding_principal) + flt(self.principal_paid), 2
            ),
            "outstanding_interest": round(
                flt(loan.outstanding_interest) + flt(self.interest_paid), 2
            ),
            "total_amount_paid": round(
                flt(loan.total_amount_paid) - flt(self.amount_paid), 2
            ),
            "installments_paid": max((loan.installments_paid or 1) - 1, 0),
        })

    def _cancel_repayment_journal_entry(self):
        if self.journal_entry:
            je = frappe.get_doc("Journal Entry", self.journal_entry)
            if je.docstatus == 1:
                je.cancel()