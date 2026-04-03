# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import (
    today, getdate, flt, get_url, now_datetime, add_months
)
from dateutil.relativedelta import relativedelta


class EmployeeLoanApplication(Document):

    # ── Lifecycle ────────────────────────────────────────────────────

    def validate(self):
        self._validate_employee_eligibility()
        self._validate_amount_and_tenure()
        self._validate_guarantor()
        self._validate_deduction_cap()
        self._compute_loan_figures()
        
        # Set outstanding principal if not set
        if not self.outstanding_principal:
            self.outstanding_principal = self.principal_amount or 0
            
        # Auto-generate schedule for preview if in draft mode
        if self.docstatus == 0 and self.principal_amount and self.tenure_months:
            self._generate_preview_schedule()

    def before_submit(self):
        if self.status not in ("Approved",):
            frappe.throw(
                "Only Approved applications can be submitted.",
                title="Cannot Submit"
            )

    def on_submit(self):
        # Generate final schedule on submit
        self._generate_repayment_schedule()
        self._create_disbursement_journal_entry()
        
        # Update status and disbursement date
        frappe.db.set_value("Employee Loan Application", self.name, {
            "status": "Disbursed",
            "disbursement_date": today(),
        })
        
        self._notify_employee_disbursement()
        
        # Reload to show updated schedule
        self.reload()

    def on_cancel(self):
        self._reverse_disbursement_journal_entry()
        frappe.db.set_value(
            "Employee Loan Application", self.name, "status", "Cancelled"
        )

    # ── Eligibility validation ───────────────────────────────────────

    def _validate_employee_eligibility(self):
        loan_type = frappe.get_doc("Employee Loan Type", self.loan_type)
        emp       = frappe.get_doc("Employee", self.employee)

        # Minimum months employed
        if loan_type.min_months_employed and emp.date_of_joining:
            months = (
                (getdate(today()).year  - getdate(emp.date_of_joining).year)  * 12 +
                (getdate(today()).month - getdate(emp.date_of_joining).month)
            )
            if months < loan_type.min_months_employed:
                frappe.throw(
                    f"Employee must have completed at least "
                    f"{loan_type.min_months_employed} months of service. "
                    f"Current tenure: {months} months.",
                    title="Eligibility Error"
                )

        # Max active loans
        if loan_type.max_active_loans:
            active = frappe.db.count("Employee Loan Application", {
                "employee": self.employee,
                "status":   ["in", ("Active", "Disbursed")],
                "name":     ["!=", self.name or ""],
            })
            if active >= loan_type.max_active_loans:
                frappe.throw(
                    f"Employee already has {active} active loan(s). "
                    f"Maximum allowed: {loan_type.max_active_loans}.",
                    title="Loan Limit Reached"
                )

        # Employment type restriction
        if loan_type.eligible_employment_types:
            allowed = [
                x.strip()
                for x in loan_type.eligible_employment_types.split(",")
            ]
            if emp.employment_type and emp.employment_type not in allowed:
                frappe.throw(
                    f"This loan type is only available to: {', '.join(allowed)}.",
                    title="Employment Type Restriction"
                )

    def _validate_amount_and_tenure(self):
        loan_type = frappe.get_doc("Employee Loan Type", self.loan_type)

        if self.principal_amount <= 0:
            frappe.throw("Principal amount must be greater than zero.")

        if self.principal_amount > loan_type.max_amount:
            frappe.throw(
                f"Requested amount ₦{self.principal_amount:,.2f} exceeds the "
                f"maximum of ₦{loan_type.max_amount:,.2f} for {self.loan_type}.",
                title="Amount Exceeds Limit"
            )

        if self.tenure_months <= 0:
            frappe.throw("Tenure must be at least 1 month.")

        if self.tenure_months > loan_type.max_tenure_months:
            frappe.throw(
                f"Tenure of {self.tenure_months} months exceeds the maximum of "
                f"{loan_type.max_tenure_months} months.",
                title="Tenure Exceeds Limit"
            )

    def _validate_guarantor(self):
        loan_type = frappe.get_doc("Employee Loan Type", self.loan_type)

        if not loan_type.requires_guarantor:
            return

        if not self.guarantor:
            frappe.throw(
                f"A guarantor is required for {self.loan_type}.",
                title="Guarantor Required"
            )
        if self.guarantor == self.employee:
            frappe.throw("An employee cannot guarantee their own loan.")
        if not self.guarantor_consent:
            frappe.throw(
                "Guarantor consent must be confirmed before submission.",
                title="Guarantor Consent Required"
            )

    def _validate_deduction_cap(self):
        """
        Nigerian labour best practice: total monthly loan deductions
        should not exceed 33% of net salary (configurable per Employee Loan Type).
        """
        if not self.monthly_deduction:
            return

        net_salary = self._get_employee_net_salary()
        if not net_salary:
            return

        loan_type   = frappe.get_doc("Employee Loan Type", self.loan_type)
        cap_pct     = flt(loan_type.max_deduction_pct or 33) / 100

        existing_deductions = frappe.db.sql("""
            SELECT COALESCE(SUM(monthly_deduction), 0)
            FROM   `tabEmployee Loan Application`
            WHERE  employee = %s
              AND  status   IN ('Active', 'Disbursed')
              AND  name     != %s
        """, (self.employee, self.name or ""))[0][0]

        total_deductions = flt(existing_deductions) + flt(self.monthly_deduction)
        cap_amount       = net_salary * cap_pct

        if total_deductions > cap_amount:
            frappe.msgprint(
                f"Warning: Total monthly deductions of ₦{total_deductions:,.2f} "
                f"will exceed {loan_type.max_deduction_pct}% of net salary "
                f"(₦{cap_amount:,.2f}). This may be flagged during payroll.",
                indicator="orange", alert=True
            )

    def _get_employee_net_salary(self) -> float:
        slip = frappe.db.get_value(
            "Salary Slip",
            {"employee": self.employee, "docstatus": 1},
            "net_pay",
            order_by="posting_date desc"
        )
        return flt(slip) if slip else 0.0

    # ── Loan computation (reducing balance EMI) ──────────────────────

    def _compute_loan_figures(self):
        """Compute monthly deduction and total repayable"""
        if not self.principal_amount or not self.tenure_months:
            return
            
        loan_type = frappe.get_doc("Employee Loan Type", self.loan_type)
        P = flt(self.principal_amount)
        n = int(self.tenure_months or 1)

        if n <= 0:
            n = 1

        if loan_type.is_interest_free or not flt(loan_type.annual_interest_rate):
            monthly = round(P / n, 2)
            total   = round(P, 2)
        else:
            r      = flt(loan_type.annual_interest_rate) / 100 / 12
            factor = (1 + r) ** n
            monthly = round(P * r * factor / (factor - 1), 2)
            total   = round(monthly * n, 2)

        self.interest_rate        = flt(loan_type.annual_interest_rate)
        self.monthly_deduction    = monthly
        self.total_repayable      = total
        
        # Only update these if this is a new loan or in draft
        if self.docstatus == 0:
            self.outstanding_principal = P
            self.outstanding_interest = round(total - P, 2)

    # ── Preview Schedule (for Draft) ─────────────────────────────────

    def _generate_preview_schedule(self):
        """Generate a preview schedule for display in draft mode"""
        if not self.principal_amount or not self.tenure_months:
            return
            
        loan_type = frappe.get_doc("Employee Loan Type", self.loan_type)
        P = flt(self.principal_amount)
        n = int(self.tenure_months)
        r = flt(loan_type.annual_interest_rate) / 100 / 12
        is_free = bool(loan_type.is_interest_free) or r == 0
        
        # Use first deduction date or default to next month
        if not self.first_deduction_date:
            self.first_deduction_date = add_months(today(), 1)
            
        start_date = getdate(self.first_deduction_date)

        balance = P
        schedule = []

        # Clear existing schedule
        self.set("repayment_schedule", [])

        for i in range(1, n + 1):
            due_date = start_date + relativedelta(months=i - 1)

            if is_free:
                principal = round(P / n, 2)
                interest = 0.0
                monthly_amount = principal
            else:
                interest = round(balance * r, 2)
                emi = flt(self.monthly_deduction)
                principal = round(emi - interest, 2)
                monthly_amount = emi

            # Last instalment: absorb rounding residuals
            if i == n:
                principal = round(balance, 2)
                if not is_free:
                    interest = round(flt(self.monthly_deduction) - principal, 2)
                    monthly_amount = round(principal + interest, 2)

            # Update balance
            balance = max(round(balance - principal, 2), 0)

            # Append to child table (without saving to DB in draft)
            self.append("repayment_schedule", {
                "installment_no": i,
                "payment_date": due_date.strftime("%Y-%m-%d"),
                "principal": principal,
                "interest": interest,
                "monthly_amount": monthly_amount,
                "balance": balance,
                "status": "Pending",
            })

    # ── Final Repayment schedule (on Submit) ─────────────────────────

    def _generate_repayment_schedule(self):
        """Generate and save final repayment schedule on loan disbursement"""
        loan_type = frappe.get_doc("Employee Loan Type", self.loan_type)
        P = flt(self.principal_amount)
        n = int(self.tenure_months)
        r = flt(loan_type.annual_interest_rate) / 100 / 12
        is_free = bool(loan_type.is_interest_free) or r == 0
        
        # Ensure first deduction date is set
        if not self.first_deduction_date:
            self.first_deduction_date = add_months(today(), 1)
            
        start_date = getdate(self.first_deduction_date)

        balance = P
        schedule = []

        # Clear existing schedule
        self.set("repayment_schedule", [])

        for i in range(1, n + 1):
            due_date = start_date + relativedelta(months=i - 1)

            if is_free:
                principal = round(P / n, 2)
                interest = 0.0
                monthly_amount = principal
            else:
                interest = round(balance * r, 2)
                emi = flt(self.monthly_deduction)
                principal = round(emi - interest, 2)
                monthly_amount = emi

            # Last instalment: absorb rounding residuals
            if i == n:
                principal = round(balance, 2)
                if not is_free:
                    interest = round(flt(self.monthly_deduction) - principal, 2)
                    monthly_amount = round(principal + interest, 2)

            # Update balance
            balance = max(round(balance - principal, 2), 0)

            # Append to child table
            self.append("repayment_schedule", {
                "installment_no": i,
                "payment_date": due_date.strftime("%Y-%m-%d"),
                "principal": principal,
                "interest": interest,
                "monthly_amount": monthly_amount,
                "balance": balance,
                "status": "Pending",
            })

        # Save the document with the new schedule
        self.save(ignore_permissions=True)
        
        frappe.msgprint(
            f"Repayment schedule generated successfully with {n} installments.",
            indicator="green"
        )

    # ── Disbursement journal entry ───────────────────────────────────

    def _create_disbursement_journal_entry(self):
        loan_type = frappe.get_doc("Employee Loan Type", self.loan_type)
        company   = (
            frappe.db.get_default("Company") or
            frappe.get_all("Company", limit=1)[0].name
        )

        je = frappe.get_doc({
            "doctype":      "Journal Entry",
            "voucher_type": "Journal Entry",
            "posting_date": today(),
            "company":      company,
            "user_remark":  (
                f"Loan disbursement — {self.employee_name} ({self.name})"
            ),
            "accounts": [
                {
                    "account":                    loan_type.loan_account,
                    "debit_in_account_currency":  flt(self.principal_amount),
                    "party_type":                 "Employee",
                    "party":                      self.employee,
                    "cost_center":                loan_type.cost_center,
                },
                {
                    "account":                    loan_type.disbursement_account,
                    "credit_in_account_currency": flt(self.principal_amount),
                    "cost_center":                loan_type.cost_center,
                },
            ]
        })
        je.insert(ignore_permissions=True)
        je.submit()
        
        frappe.db.set_value(
            "Employee Loan Application", self.name,
            "disbursement_journal_entry", je.name
        )
        
        return je

    def _reverse_disbursement_journal_entry(self):
        je_name = self.disbursement_journal_entry
        if not je_name:
            return
        je = frappe.get_doc("Journal Entry", je_name)
        if je.docstatus == 1:
            je.cancel()

    # ── Notification ─────────────────────────────────────────────────

    def _notify_employee_disbursement(self):
        user = frappe.db.get_value("Employee", self.employee, "user_id")
        if not user:
            return
            
        # Get repayment schedule summary
        schedule = self.get("repayment_schedule", [])
        first_payment = schedule[0] if schedule else None
        last_payment = schedule[-1] if schedule else None
        
        frappe.sendmail(
            recipients=[user],
            subject=(
                f"Loan disbursed — ₦{self.principal_amount:,.2f} ({self.loan_type})"
            ),
            message=f"""
                <div style="font-family:sans-serif;max-width:600px;padding:24px">
                    <p>Dear {self.employee_name},</p>
                    <p>Your loan of <strong>₦{self.principal_amount:,.2f}</strong>
                    ({self.loan_type}) has been disbursed.</p>
                    
                    <h3 style="margin:20px 0 10px">Loan Summary</h3>
                    <table style="width:100%;font-size:13px;border-collapse:collapse;
                                  margin:16px 0; background: #f8f9fa;">
                        <tr>
                            <td style="padding:8px;border:1px solid #dee2e6;">Total repayable</td>
                            <td style="padding:8px;border:1px solid #dee2e6; font-weight:500">
                                ₦{self.total_repayable:,.2f}
                            </td>
                        </tr>
                        <tr>
                            <td style="padding:8px;border:1px solid #dee2e6;">Monthly deduction</td>
                            <td style="padding:8px;border:1px solid #dee2e6; font-weight:500">
                                ₦{self.monthly_deduction:,.2f}
                            </td>
                        </tr>
                        <tr>
                            <td style="padding:8px;border:1px solid #dee2e6;">First deduction</td>
                            <td style="padding:8px;border:1px solid #dee2e6; font-weight:500">
                                {self.first_deduction_date}
                            </td>
                        </tr>
                        <tr>
                            <td style="padding:8px;border:1px solid #dee2e6;">Tenure</td>
                            <td style="padding:8px;border:1px solid #dee2e6; font-weight:500">
                                {self.tenure_months} months
                            </td>
                        </tr>
                    </table>
                    
                    <h3 style="margin:20px 0 10px">Repayment Schedule</h3>
                    <table style="width:100%;font-size:12px;border-collapse:collapse;">
                        <thead>
                            <tr style="background:#534AB7;color:white;">
                                <th style="padding:6px;border:1px solid #dee2e6;">#</th>
                                <th style="padding:6px;border:1px solid #dee2e6;">Due Date</th>
                                <th style="padding:6px;border:1px solid #dee2e6;">Principal</th>
                                <th style="padding:6px;border:1px solid #dee2e6;">Interest</th>
                                <th style="padding:6px;border:1px solid #dee2e6;">Total</th>
                            </tr>
                        </thead>
                        <tbody>
                            {self._get_schedule_html()}
                        </tbody>
                    </table>
                    
                    <p style="margin-top:30px">
                        <a href="{get_url(f'/app/employee-loan-application/{self.name}')}"
                           style="padding:10px 20px;background:#534AB7;color:#fff;
                                  border-radius:6px;text-decoration:none;
                                  font-weight:500">
                            View loan details
                        </a>
                    </p>
                </div>
            """,
            now=False
        )
    
    def _get_schedule_html(self):
        """Generate HTML for repayment schedule in email"""
        html = ""
        for i, row in enumerate(self.get("repayment_schedule", [])):
            if i < 5:  # Show first 5 installments
                html += f"""
                    <tr>
                        <td style="padding:6px;border:1px solid #dee2e6;">{row.installment_no}</td>
                        <td style="padding:6px;border:1px solid #dee2e6;">{row.payment_date}</td>
                        <td style="padding:6px;border:1px solid #dee2e6;text-align:right;">₦{row.principal:,.2f}</td>
                        <td style="padding:6px;border:1px solid #dee2e6;text-align:right;">₦{row.interest:,.2f}</td>
                        <td style="padding:6px;border:1px solid #dee2e6;text-align:right;">₦{row.monthly_amount:,.2f}</td>
                    </tr>
                """
        if len(self.get("repayment_schedule", [])) > 5:
            html += f"""
                <tr>
                    <td colspan="5" style="padding:6px;border:1px solid #dee2e6;text-align:center;font-style:italic;">
                        ... and {len(self.get("repayment_schedule", [])) - 5} more installments
                    </td>
                </tr>
            """
        return html


# ── Standalone utility functions ───────────────────────────────────────

@frappe.whitelist()
def get_loan_summary(loan_name):
    """Get loan summary for dashboard"""
    loan = frappe.get_doc("Employee Loan Application", loan_name)
    
    schedule = loan.get("repayment_schedule", [])
    next_payment = next((row for row in schedule if row.status == "Pending"), None)
    
    return {
        "principal": loan.principal_amount,
        "outstanding": loan.outstanding_principal,
        "monthly": loan.monthly_deduction,
        "total_repayable": loan.total_repayable,
        "paid": loan.total_amount_paid,
        "installments_paid": loan.installments_paid,
        "total_installments": loan.tenure_months,
        "next_payment": next_payment.as_dict() if next_payment else None,
        "status": loan.status
    }


@frappe.whitelist()
def update_loan_after_repayment(loan_name, repayment_amount, principal_paid, interest_paid):
    """Update loan balances after repayment"""
    loan = frappe.get_doc("Employee Loan Application", loan_name)
    
    # Update balances
    loan.outstanding_principal = max(flt(loan.outstanding_principal) - flt(principal_paid), 0)
    loan.outstanding_interest = max(flt(loan.outstanding_interest) - flt(interest_paid), 0)
    loan.total_amount_paid = flt(loan.total_amount_paid) + flt(repayment_amount)
    loan.installments_paid = (loan.installments_paid or 0) + 1
    
    # Check if loan is fully repaid
    if loan.outstanding_principal <= 0.01:
        loan.status = "Closed"
    
    loan.save(ignore_permissions=True)
    frappe.db.commit()
    
    return loan.as_dict()


@frappe.whitelist()
def preview_schedule(principal, tenure_months, interest_rate, first_deduction_date=None, is_interest_free=0):
    """API endpoint to preview repayment schedule without saving"""
    from frappe.utils import flt, getdate
    from dateutil.relativedelta import relativedelta
    
    principal = flt(principal)
    n = int(tenure_months or 1)
    r = flt(interest_rate) / 100 / 12
    is_free = bool(is_interest_free) or r == 0
    
    if n <= 0:
        n = 1
        
    if not first_deduction_date:
        first_deduction_date = add_months(today(), 1)
        
    start_date = getdate(first_deduction_date)
    
    balance = principal
    schedule = []
    
    # Compute EMI
    if is_free:
        monthly = round(principal / n, 2)
        total = principal
    else:
        factor = (1 + r) ** n
        monthly = round(principal * r * factor / (factor - 1), 2)
        total = round(monthly * n, 2)
    
    for i in range(1, n + 1):
        due_date = start_date + relativedelta(months=i - 1)
        
        if is_free:
            principal_paid = round(principal / n, 2)
            interest = 0.0
            monthly_amount = principal_paid
        else:
            interest = round(balance * r, 2)
            principal_paid = round(monthly - interest, 2)
            monthly_amount = monthly
        
        # Last instalment: absorb rounding residuals
        if i == n:
            principal_paid = round(balance, 2)
            if not is_free:
                interest = round(monthly - principal_paid, 2)
                monthly_amount = round(principal_paid + interest, 2)
        
        # Update balance
        balance = max(round(balance - principal_paid, 2), 0)
        
        schedule.append({
            "installment_no": i,
            "payment_date": due_date.strftime("%Y-%m-%d"),
            "principal": principal_paid,
            "interest": interest,
            "monthly_amount": monthly_amount,
            "balance": balance
        })
    
    return {
        "schedule": schedule,
        "summary": {
            "monthly_deduction": monthly,
            "total_repayable": total,
            "total_interest": total - principal
        }
    }