# Copyright (c) 2026, Ecclesia Enterprise — License: MIT
# ess_portal_loan.py
"""
ESS Portal — Loan Application Integration

Uses standard ERPNext `Loan Application` doctype (Lending module).
Standard fields referenced (no schema changes):
  applicant_type, applicant, applicant_name,
  loan_type, loan_amount, repayment_method,
  repayment_periods, repayment_amount,
  rate_of_interest, total_payable_amount,
  total_payable_interest, status,
  company, posting_date, amended_from,
  description (if exists)

Custom fields added by ess_portal_custom_fields.py:
  ess_submitted_via_portal  (Check, read_only)
  ess_portal_submitted_on   (Datetime, read_only)
  ess_employee_notes        (Small Text)

Loan status values (standard ERPNext):
  Open | Approved | Rejected | Cancelled | Withdrawn
"""

import frappe
from frappe.utils import now_datetime, today, flt, add_months


# ─────────────────────────────────────────────────────────────────
# SECTION 1 — READ
# ─────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_my_loans(status: str = None):
    """
    Return all Loan Applications for the current employee.

    Args:
        status: Optional filter — "Open" | "Approved" | "Rejected" | "Cancelled"

    Returns:
        { loans: [...], summary: {...} }
    """
    emp = _resolve_employee()
    if not emp:
        frappe.throw("No Employee record linked to your account.")

    filters = {"applicant_type": "Employee", "applicant": emp}
    if status:
        filters["status"] = status

    loans = frappe.get_all(
        "Loan Application",
        filters=filters,
        fields=[
            "name", "loan_type", "loan_amount", "status",
            "repayment_method", "repayment_periods", "repayment_amount",
            "rate_of_interest", "total_payable_amount", "total_payable_interest",
            "posting_date", "company",
            # Our custom fields (installed by ess_portal_custom_fields.py)
            "ess_submitted_via_portal", "ess_portal_submitted_on", "ess_employee_notes",
        ],
        order_by="posting_date desc",
    )

    # Enrich with active loan schedule summary if approved
    for loan in loans:
        if loan.status == "Approved":
            loan["loan_details"] = _get_loan_schedule_summary(loan.name)
        else:
            loan["loan_details"] = None

    summary = {
        "total":      len(loans),
        "open":       sum(1 for l in loans if l.status == "Open"),
        "approved":   sum(1 for l in loans if l.status == "Approved"),
        "rejected":   sum(1 for l in loans if l.status == "Rejected"),
        "total_approved_amount": sum(
            flt(l.loan_amount) for l in loans if l.status == "Approved"
        ),
    }

    return {"loans": loans, "summary": summary}


@frappe.whitelist()
def get_loan_types():
    """
    Return available loan types for the ESS portal dropdown.
    Reads from the ERPNext `Loan Type` doctype.
    """
    types = frappe.get_all(
        "Loan Type",
        filters={"disabled": 0},
        fields=[
            "name", "loan_name", "maximum_loan_amount",
            "rate_of_interest", "repayment_method",
            "repayment_periods", "description",
        ],
        order_by="loan_name",
    )
    return types


@frappe.whitelist()
def get_loan_detail(name: str):
    """Return full detail of one Loan Application."""
    emp = _resolve_employee()
    doc = frappe.get_doc("Loan Application", name)

    if doc.applicant != emp:
        frappe.only_for(["HR Manager", "Loan Manager", "System Manager"])

    schedule = _get_loan_schedule_summary(name)

    return {"loan": doc.as_dict(), "schedule": schedule}


# ─────────────────────────────────────────────────────────────────
# SECTION 2 — CREATE
# ─────────────────────────────────────────────────────────────────

@frappe.whitelist()
def apply_for_loan(
    loan_type:         str,
    loan_amount:       float,
    repayment_method:  str   = "Repay Over Number of Periods",
    repayment_periods: int   = 12,
    description:       str   = None,
    employee_notes:    str   = None,   # goes into ess_employee_notes
):
    """
    Submit a Loan Application on behalf of the current employee.

    All core field names are standard ERPNext Loan Application fields.
    applicant_type is always "Employee", applicant is the resolved employee.

    The ERPNext Loan module calculates repayment_amount, total_payable_amount,
    and total_payable_interest from loan_type.rate_of_interest on save.

    Args:
        loan_type         : Link to Loan Type docname
        loan_amount       : Requested amount
        repayment_method  : "Repay Over Number of Periods" | "Repay Fixed Amount per Period"
        repayment_periods : Number of months (ignored for fixed amount method)
        description       : Free-text purpose of the loan
        employee_notes    : Additional ESS-only notes (stored in ess_employee_notes)
    """
    emp = _resolve_employee()
    if not emp:
        frappe.throw("Your account is not linked to an Employee record.")

    emp_doc = frappe.get_doc("Employee", emp)

    # Validate against maximum loan amount configured in Loan Type
    max_amount = frappe.db.get_value("Loan Type", loan_type, "maximum_loan_amount")
    if max_amount and flt(loan_amount) > flt(max_amount):
        frappe.throw(
            f"Requested amount {loan_amount:,.2f} exceeds the maximum of {max_amount:,.2f} "
            f"for loan type '{loan_type}'."
        )

    doc = frappe.get_doc({
        "doctype":            "Loan Application",
        "applicant_type":     "Employee",
        "applicant":          emp,
        "applicant_name":     emp_doc.employee_name,
        "loan_type":          loan_type,
        "loan_amount":        flt(loan_amount),
        "repayment_method":   repayment_method,
        "repayment_periods":  cint(repayment_periods),
        "posting_date":       today(),
        "company":            emp_doc.company or frappe.db.get_single_value(
                                  "Global Defaults", "default_company"),
        # ERPNext Loan Application has a description / purpose field on some versions
        # Use it if it exists, otherwise skip gracefully
        # Custom ESS fields
        "ess_submitted_via_portal": 1,
        "ess_portal_submitted_on":  now_datetime(),
        "ess_employee_notes":       employee_notes,
    })

    # description field exists on some ERPNext versions — set conditionally
    if frappe.db.has_column("Loan Application", "description") and description:
        doc.description = description

    doc.insert()

    return {
        "status":     "success",
        "name":       doc.name,
        "loan_type":  loan_type,
        "amount":     flt(loan_amount),
        "message":    (f"{doc.name} submitted successfully. "
                       "HR will review and contact you once a decision is made."),
    }


@frappe.whitelist()
def withdraw_loan(name: str, reason: str = None):
    """
    Employee withdraws/cancels their own Open loan application.
    Only allowed while status is "Open".
    """
    emp = _resolve_employee()
    doc = frappe.get_doc("Loan Application", name)

    if doc.applicant != emp:
        frappe.throw("You can only withdraw your own loan applications.", frappe.PermissionError)
    if doc.status != "Open":
        frappe.throw(f"Cannot withdraw — current status is '{doc.status}'.")

    doc.status = "Cancelled"
    doc.save(ignore_permissions=True)

    if reason:
        frappe.db.set_value("Loan Application", name, "ess_employee_notes",
                            f"[Withdrawn] {reason}")

    return {"status": "success", "message": "Loan application withdrawn."}


# ─────────────────────────────────────────────────────────────────
# SECTION 3 — DOC EVENT HOOKS
# ─────────────────────────────────────────────────────────────────

def on_loan_application_update(doc, method=None):
    """
    Hook: Loan Application.on_update
    Notify employee when HR changes status to Approved or Rejected.
    Also creates an ESS Task for the employee when a loan is Approved
    so they know repayments will begin.
    """
    if doc.is_new():
        return

    prev_status = frappe.db.get_value("Loan Application", doc.name, "status")
    if doc.status == prev_status:
        return  # Nothing changed

    if doc.status == "Approved":
        _notify_employee_loan(doc, "Approved")
        _create_loan_repayment_task(doc)

    elif doc.status == "Rejected":
        _notify_employee_loan(doc, "Rejected")


def on_loan_application_submit(doc, method=None):
    """
    Hook: Loan Application.on_submit
    Notify HR/Loan Manager that a new application is awaiting approval.
    """
    _notify_loan_manager(doc)


def on_loan_application_cancel(doc, method=None):
    """
    Hook: Loan Application.on_cancel
    Cancel any pending ESS Tasks linked to this loan.
    """
    tasks = frappe.get_all(
        "ESS Task",
        filters={"linked_doctype": "Loan Application",
                 "linked_docname": doc.name,
                 "status": ["!=", "Completed"]},
        pluck="name",
    )
    for t in tasks:
        frappe.db.set_value("ESS Task", t, "status", "Cancelled")


# ─────────────────────────────────────────────────────────────────
# SECTION 4 — REPAYMENT REMINDERS (Scheduled Job)
# ─────────────────────────────────────────────────────────────────

def send_loan_repayment_reminders():
    """
    Daily scheduled job.
    Reminds employees of upcoming loan repayment deductions.
    Fires on the 25th of each month (3 days before typical month-end payroll).
    """
    from datetime import date
    today_d = date.today()

    if today_d.day != 25:
        return  # Only run on the 25th

    # Find all active (Approved) loans that were submitted via ESS portal
    active_loans = frappe.get_all(
        "Loan Application",
        filters={"status": "Approved"},
        fields=["name", "applicant", "loan_type", "loan_amount",
                "repayment_amount", "repayment_periods"],
    )

    for loan in active_loans:
        emp_user = frappe.db.get_value("Employee", loan.applicant, "user_id")
        if not emp_user:
            continue

        emp_name = frappe.db.get_value("Employee", loan.applicant, "employee_name")

        frappe.sendmail(
            recipients=[emp_user],
            subject=f"[ESS] Loan Repayment Reminder — {loan.name}",
            message=f"""
                <p>Dear {emp_name},</p>
                <p>This is a reminder that your loan repayment of
                <strong>{loan.repayment_amount:,.2f}</strong> for
                <strong>{loan.loan_type}</strong> ({loan.name}) will be
                deducted in the upcoming payroll.</p>
                <p><a href="{frappe.utils.get_url()}/ess">View in ESS Portal →</a></p>
            """,
            now=False,
        )


# ─────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────

def _resolve_employee():
    return frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")


def cint(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0


def _get_loan_schedule_summary(loan_name: str) -> dict:
    """
    Return a light summary of the loan repayment schedule.
    Reads from `Loan Repayment Schedule` child table if available.
    Falls back to computed values from the Loan Application itself.
    """
    try:
        schedule = frappe.get_all(
            "Repayment Schedule",
            filters={"parent": loan_name},
            fields=["payment_date", "principal_amount", "interest_amount",
                    "total_payment", "balance_loan_amount"],
            order_by="payment_date",
            limit=3,   # next 3 instalments
        )
        return {
            "next_instalments": schedule,
            "total_rows": frappe.db.count("Repayment Schedule", {"parent": loan_name}),
        }
    except Exception:
        return {}


def _notify_employee_loan(doc, outcome: str):
    emp_user = frappe.db.get_value("Employee", doc.applicant, "user_id")
    if not emp_user:
        return

    body = ""
    if outcome == "Approved":
        body = f"""
            <p>Your loan application <strong>{doc.name}</strong> has been
            <strong>APPROVED</strong>.</p>
            <ul>
                <li><strong>Loan Type:</strong> {doc.loan_type}</li>
                <li><strong>Amount:</strong> {doc.loan_amount:,.2f}</li>
                <li><strong>Monthly Repayment:</strong> {flt(doc.repayment_amount):,.2f}</li>
                <li><strong>Repayment Periods:</strong> {doc.repayment_periods} months</li>
            </ul>
            <p>Repayments will begin in the next payroll cycle.</p>
        """
    elif outcome == "Rejected":
        body = f"""
            <p>Your loan application <strong>{doc.name}</strong> for
            <strong>{doc.loan_type}</strong> has been <strong>REJECTED</strong>.</p>
            <p>Please contact HR for further information.</p>
        """

    frappe.sendmail(
        recipients=[emp_user],
        subject=f"[ESS] Loan Application {outcome}: {doc.name}",
        message=body + f'<p><a href="{frappe.utils.get_url()}/ess">View in ESS Portal →</a></p>',
        now=False,
    )


def _notify_loan_manager(doc):
    """Notify HR / Loan Manager of a new application."""
    managers = frappe.get_all(
        "Has Role",
        filters={"role": ["in", ["HR Manager", "Loan Manager"]], "parenttype": "User"},
        pluck="parent",
        limit=3,
    )
    if not managers:
        return

    emp_name = frappe.db.get_value("Employee", doc.applicant, "employee_name")

    frappe.sendmail(
        recipients=list(set(managers)),
        subject=f"[ESS] New Loan Application: {doc.name} — {emp_name}",
        message=f"""
            <p>A new Loan Application has been submitted via ESS Portal:</p>
            <ul>
                <li><strong>Reference:</strong> {doc.name}</li>
                <li><strong>Employee:</strong> {emp_name}</li>
                <li><strong>Loan Type:</strong> {doc.loan_type}</li>
                <li><strong>Amount:</strong> {doc.loan_amount:,.2f}</li>
                <li><strong>Repayment Periods:</strong> {doc.repayment_periods} months</li>
            </ul>
            <p><a href="{frappe.utils.get_url()}/app/loan-application/{doc.name}">
               Review in ERPNext →</a></p>
        """,
        now=False,
    )


def _create_loan_repayment_task(doc):
    """Create an ESS Task informing the employee that repayments will begin."""
    try:
        emp_name = frappe.db.get_value("Employee", doc.applicant, "employee_name")
        frappe.get_doc({
            "doctype":        "ESS Task",
            "assigned_to":    doc.applicant,
            "title":          f"Loan Approved — Repayments Begin Next Payroll ({doc.name})",
            "task_category":  "Finance",
            "priority":       "Medium",
            "status":         "Open",
            "linked_doctype": "Loan Application",
            "linked_docname": doc.name,
            "assigned_on":    today(),
        }).insert(ignore_permissions=True)
    except Exception as e:
        frappe.logger().warning(f"[ESS Loan] Could not create repayment task: {e}")