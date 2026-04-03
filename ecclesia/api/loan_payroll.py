# ecclesia/api/loan_payroll.py
import frappe
from frappe.utils import flt, getdate, today


def on_salary_slip_before_submit(doc, method):
    """
    Before a Salary Slip is submitted, inject loan deduction components
    for all active loans belonging to this employee.
    """
    if doc.docstatus != 0:
        return

    active_loans = frappe.get_all(
        "Employee Loan Application",
        filters={
            "employee": doc.employee,
            "status":   ["in", ("Disbursed", "Active")],
        },
        fields=["name", "loan_type", "monthly_deduction",
                "outstanding_principal", "first_deduction_date"]
    )

    if not active_loans:
        return

    slip_month_start = getdate(doc.start_date)

    for loan in active_loans:
        if getdate(loan.first_deduction_date) > slip_month_start:
            continue

        already_deducted = frappe.db.exists("Loan Repayment Entry", {
            "loan":        loan.name,
            "salary_slip": doc.name,
            "docstatus":   ["!=", 2],
        })
        if already_deducted:
            continue

        component = _get_or_create_loan_deduction_component(loan.loan_type)

        existing = next(
            (d for d in doc.deductions if d.salary_component == component),
            None
        )

        deduction_amount = min(
            flt(loan.monthly_deduction),
            flt(loan.outstanding_principal)
        )

        if existing:
            existing.amount += deduction_amount
        else:
            doc.append("deductions", {
                "salary_component": component,
                "amount":           deduction_amount,
            })

    doc.calculate_net_pay()


def on_salary_slip_on_submit(doc, method):
    """
    After Salary Slip is submitted, create Loan Repayment Entry records
    for each loan deduction that was applied.
    """
    active_loans = frappe.get_all(
        "Employee Loan Application",
        filters={
            "employee": doc.employee,
            "status":   ["in", ("Disbursed", "Active")],
        },
        fields=["name", "loan_type", "monthly_deduction",
                "outstanding_principal", "first_deduction_date",
                "employee_name"]
    )

    slip_month_start = getdate(doc.start_date)

    for loan in active_loans:
        if getdate(loan.first_deduction_date) > slip_month_start:
            continue

        already = frappe.db.exists("Loan Repayment Entry", {
            "loan":        loan.name,
            "salary_slip": doc.name,
            "docstatus":   ["!=", 2],
        })
        if already:
            continue

        deduction_amount = min(
            flt(loan.monthly_deduction),
            flt(loan.outstanding_principal)
        )
        if deduction_amount <= 0:
            continue

        lre = frappe.get_doc({
            "doctype":      "Loan Repayment Entry",
            "loan":         loan.name,
            "employee":     doc.employee,
            "payment_date": doc.end_date,
            "amount_paid":  deduction_amount,
            "payment_mode": "Payroll Deduction",
            "salary_slip":  doc.name,
            "reference_no": doc.name,
            "remarks": (
                f"Payroll deduction — "
                f"{getattr(doc, 'month_name', None) or doc.start_date}"
            ),
        })
        lre.insert(ignore_permissions=True)
        lre.submit()

    frappe.db.commit()


def on_salary_slip_on_cancel(doc, method):
    """
    Cancel all Loan Repayment Entries linked to this salary slip.
    """
    entries = frappe.get_all(
        "Loan Repayment Entry",
        filters={"salary_slip": doc.name, "docstatus": 1},
        fields=["name"]
    )
    for entry in entries:
        frappe.get_doc("Loan Repayment Entry", entry.name).cancel()
    if entries:
        frappe.db.commit()


def _get_or_create_loan_deduction_component(loan_type_name: str) -> str:
    """
    Return the Salary Component for loan deductions, creating it if absent.
    Component name pattern: 'Loan Deduction — {Employee Loan Type name}'
    """
    component_name = f"Loan Deduction — {loan_type_name}"
    if not frappe.db.exists("Salary Component", component_name):
        frappe.get_doc({
            "doctype":               "Salary Component",
            "salary_component":      component_name,
            "salary_component_abbr": f"LD-{loan_type_name[:6].upper()}",
            "type":                  "Deduction",
            "is_tax_applicable":     0,
            "statistical_component": 0,
            "description":           f"Monthly deduction for {loan_type_name}",
        }).insert(ignore_permissions=True)
    return component_name


@frappe.whitelist()
def get_loan_statement(loan: str) -> dict:
    """
    Return full repayment schedule with current status for the statement dialog.
    """
    doc = frappe.get_doc("Employee Loan Application", loan)
    return {
        "employee_name":    doc.employee_name,
        "loan_type":        doc.loan_type,
        "principal":        doc.principal_amount,
        "total_repayable":  doc.total_repayable,
        "outstanding":      doc.outstanding_principal,
        "total_paid":       doc.total_amount_paid,
        "schedule": [
            {
                "installment_no": r.installment_no,
                "payment_date":   str(r.payment_date),
                "principal":      r.principal,
                "interest":       r.interest,
                "monthly_amount": r.monthly_amount,
                "balance":        r.balance,
                "status":         r.status,
            }
            for r in doc.repayment_schedule
        ],
    }