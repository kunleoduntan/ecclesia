"""
ecclesia/ecclesia/page/ess_portal/ess_portal.py

Employee Self-Service Portal — Backend
All @frappe.whitelist() methods called from ess_portal.js via:
    frappe.call('ecclesia.ecclesia.page.ess_portal.ess_portal.<method>')

DocType priorities:
  - Ecclesia doctypes take priority over ERPNext standard where both exist
  - New portal-native doctypes: ESS Notification Log, ESS Quick Action, ESS Pulse Score
"""
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import (
    flt, cint, nowdate, now_datetime, get_datetime,
    get_first_day, get_last_day, date_diff, add_days,
    getdate, format_date, money_in_words
)
from datetime import datetime, date, timedelta
import json


# ═══════════════════════════════════════════════════════════════════════════
#  HELPER — resolve logged-in user → employee
# ═══════════════════════════════════════════════════════════════════════════

def _get_employee(user=None):
    """Return the Employee linked to the current (or supplied) Frappe user."""
    user = user or frappe.session.user
    employee = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
    if not employee:
        frappe.throw(_("No active Employee record linked to user {0}").format(user))
    return employee


def _employee_doc(employee=None):
    employee = employee or _get_employee()
    return frappe.get_doc("Employee", employee)


# ═══════════════════════════════════════════════════════════════════════════
#  BOOTSTRAP — everything the portal needs on first load
# ═══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_portal_context():
    """
    Single endpoint called on page load.
    Returns employee profile, today snapshot, pending counts, and notifications.
    """
    employee = _get_employee()
    emp = frappe.db.get_value(
        "Employee", employee,
        ["name", "employee_name", "designation", "department", "branch",
         "grade", "date_of_joining", "employment_type", "user_id",
         "reports_to", "company"],
        as_dict=True
    )

    today = nowdate()
    month_start = get_first_day(today)
    month_end   = get_last_day(today)

    # ── pending counts ───────────────────────────────────────────────────
    pending_leave = frappe.db.count(
        "Leave Application",
        {"employee": employee, "status": "Open"}
    )
    pending_tasks = frappe.db.count(
        "ESS Task",
        {"assigned_to": employee, "status": ["not in", ["Completed", "Cancelled"]]}
    )
    unread_notifs = frappe.db.count(
        "ESS Notification Log",
        {"employee": employee, "is_read": 0}
    ) if frappe.db.exists("DocType", "ESS Notification Log") else 0

    pending_ack = _count_pending_policy_acks(employee)

    # ── today attendance ─────────────────────────────────────────────────
    today_att = frappe.db.get_value(
        "Attendance",
        {"employee": employee, "attendance_date": today},
        ["status", "in_time", "out_time"],
        as_dict=True
    ) or {}

    # ── active WFH session ───────────────────────────────────────────────
    wfh_active = frappe.db.get_value(
        "WFH Session",
        {"employee": employee, "date": today, "status": "Open", "docstatus": ["!=", 2]},
        ["name", "check_in_time", "work_mode"],
        as_dict=True
    )

    # ── latest pulse score ───────────────────────────────────────────────
    pulse = None
    if frappe.db.exists("DocType", "ESS Pulse Score"):
        pulse = frappe.db.get_value(
            "ESS Pulse Score",
            {"employee": employee},
            ["overall_pulse_score", "attendance_score", "task_score",
             "leave_health_score", "performance_score", "period"],
            order_by="period_end desc",
            as_dict=True
        )

    return {
        "employee": emp,
        "today": today,
        "pending_leave": pending_leave,
        "pending_tasks": pending_tasks,
        "unread_notifications": unread_notifs,
        "pending_policy_acks": pending_ack,
        "today_attendance": today_att,
        "wfh_active": wfh_active,
        "pulse": pulse,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  HOME — dashboard snapshot
# ═══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_home_data():
    """Snapshot cards + pending action list + recent activity for Home panel."""
    employee = _get_employee()
    today    = nowdate()
    month_start = get_first_day(today)
    month_end   = get_last_day(today)
    year_start  = "{0}-01-01".format(today[:4])

    # Present days this month
    present = frappe.db.count(
        "Attendance",
        {"employee": employee, "attendance_date": ["between", [month_start, today]],
         "status": "Present", "docstatus": 1}
    )
    working_days = frappe.db.count(
        "Attendance",
        {"employee": employee, "attendance_date": ["between", [month_start, today]],
         "docstatus": 1}
    ) or 1

    # Annual leave balance
    leave_bal = _get_leave_balance(employee, "Annual Leave")

    # Task completion
    total_tasks = frappe.db.count("ESS Task", {"assigned_to": employee,
        "assigned_on": [">=", month_start]})
    done_tasks  = frappe.db.count("ESS Task", {"assigned_to": employee,
        "assigned_on": [">=", month_start], "status": "Completed"})

    # Latest performance score
    perf_score = frappe.db.get_value(
        "Employee Performance Record",
        {"employee": employee, "status": ["!=", "Cancelled"]},
        "composite_score",
        order_by="creation desc"
    ) or 0

    # Pending actions list
    pending_actions = _build_pending_actions(employee)

    # Recent activity (last 10 cross-doctype events)
    recent = _get_recent_activity(employee)

    return {
        "present_days": present,
        "working_days": working_days,
        "leave_balance": leave_bal,
        "tasks_total": total_tasks,
        "tasks_done": done_tasks,
        "performance_score": flt(perf_score, 1),
        "pending_actions": pending_actions,
        "recent_activity": recent,
    }


def _build_pending_actions(employee):
    """Gather cross-doctype pending items that need the employee's attention."""
    actions = []
    today = nowdate()

    # Open leave applications
    leaves = frappe.db.sql("""
        SELECT name, leave_type, from_date, to_date, status
        FROM `tabLeave Application`
        WHERE employee = %s AND status = 'Open'
        ORDER BY creation DESC LIMIT 5
    """, employee, as_dict=True)
    for l in leaves:
        actions.append({
            "type": "leave", "icon": "🌴", "color": "#34D399",
            "title": "Leave Application Pending",
            "sub": "{0} · {1} to {2}".format(l.leave_type,
                format_date(l.from_date), format_date(l.to_date)),
            "doc": l.name, "panel": "attendance"
        })

    # Pending policy acknowledgements
    unack = _get_unacknowledged_policies(employee)
    for p in unack:
        actions.append({
            "type": "policy", "icon": "📜", "color": "#F59E0B",
            "title": "Policy Acknowledgement Required",
            "sub": "{0} — due in {1} days".format(
                p.policy_title, p.days_remaining),
            "doc": p.policy, "panel": "policies"
        })

    # Open self-appraisal
    open_cycle = frappe.db.get_value(
        "Performance Cycle",
        {"status": "Active"},
        ["name", "title", "self_appraisal_deadline"],
        as_dict=True
    )
    if open_cycle:
        has_self = frappe.db.exists(
            "Employee Performance Record",
            {"employee": employee, "cycle": open_cycle.name,
             "self_appraisal_date": ["!=", ""]}
        )
        if not has_self:
            due = open_cycle.get("self_appraisal_deadline") or "soon"
            actions.append({
                "type": "appraisal", "icon": "⭐", "color": "#A78BFA",
                "title": "Self-Appraisal Pending",
                "sub": "{0} · Due {1}".format(
                    open_cycle.title, format_date(due) if due != "soon" else due),
                "doc": open_cycle.name, "panel": "performance"
            })

    # Latest payslip notification
    latest_slip = frappe.db.get_value(
        "Salary Slip",
        {"employee": employee, "docstatus": 1},
        ["name", "posting_date", "net_pay"],
        order_by="posting_date desc",
        as_dict=True
    )
    if latest_slip:
        actions.append({
            "type": "payslip", "icon": "💰", "color": "#34D399",
            "title": "Payslip Available",
            "sub": "Net Pay: ₦{0:,.0f} · {1}".format(
                flt(latest_slip.net_pay),
                format_date(latest_slip.posting_date)),
            "doc": latest_slip.name, "panel": "payroll"
        })

    # Overdue ESS tasks
    overdue = frappe.db.count(
        "ESS Task",
        {"assigned_to": employee,
         "due_date": ["<", today],
         "status": ["not in", ["Completed", "Cancelled"]]}
    )
    if overdue:
        actions.append({
            "type": "task", "icon": "⚠️", "color": "#EF4444",
            "title": "{0} Overdue Task{1}".format(overdue, "s" if overdue > 1 else ""),
            "sub": "Tasks past their due date",
            "doc": None, "panel": "tasks"
        })

    return actions


def _get_recent_activity(employee):
    """Last 10 events across Leave, Loan, WFH, Expense, Policy Ack, ESS Task."""
    rows = []

    rows += frappe.db.sql("""
        SELECT 'Leave Application' AS doctype, name, status,
               leave_type AS label, creation
        FROM `tabLeave Application`
        WHERE employee = %s AND docstatus != 2
        ORDER BY creation DESC LIMIT 4
    """, employee, as_dict=True)

    rows += frappe.db.sql("""
        SELECT 'Loan (Staff)' AS doctype, name, status,
               loan_type AS label, creation
        FROM `tabEmployee Loan Application`
        WHERE employee = %s AND docstatus != 2
        ORDER BY creation DESC LIMIT 3
    """, employee, as_dict=True)

    rows += frappe.db.sql("""
        SELECT 'WFH Session' AS doctype, name, status,
               'Work From Home' AS label, creation
        FROM `tabWFH Session`
        WHERE employee = %s AND docstatus != 2
        ORDER BY creation DESC LIMIT 3
    """, employee, as_dict=True)

    rows += frappe.db.sql("""
        SELECT 'Policy Acknowledgement' AS doctype, name, status,
               policy_title AS label, creation
        FROM `tabPolicy Acknowledgement`
        WHERE employee = %s
        ORDER BY creation DESC LIMIT 3
    """, employee, as_dict=True)

    rows.sort(key=lambda r: r.creation, reverse=True)
    return rows[:10]


# ═══════════════════════════════════════════════════════════════════════════
#  PROFILE
# ═══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_profile_data():
    """Full employee profile for My Profile panel."""
    employee = _get_employee()
    emp = frappe.get_doc("Employee", employee)

    # Documents
    docs = frappe.get_all(
        "Employee Document",
        filters={"employee": employee},
        fields=["name", "document_type", "expiry_date", "status", "creation"],
        order_by="creation desc"
    )

    # Skills
    skills = frappe.db.sql("""
        SELECT skill, proficiency FROM `tabEmployee Skill`
        WHERE parent = %s
    """, employee, as_dict=True)

    # Training history
    trainings = frappe.get_all(
        "Training Result",
        filters={"employee": employee},
        fields=["training_event", "grade", "creation", "docstatus"],
        order_by="creation desc", limit=10
    )

    # Handover notes
    handovers = frappe.get_all(
        "Handover Note",
        filters={"employee": employee},
        fields=["name", "title", "delegate_to", "effective_date", "status"],
        order_by="creation desc", limit=10
    )

    # Manager info
    manager_name = frappe.db.get_value(
        "Employee", emp.reports_to, "employee_name"
    ) if emp.reports_to else None

    return {
        "employee": emp.as_dict(),
        "documents": docs,
        "skills": skills,
        "trainings": trainings,
        "handovers": handovers,
        "manager_name": manager_name,
    }


@frappe.whitelist()
def update_profile(data):
    """Update personal fields the employee is allowed to self-edit."""
    if isinstance(data, str):
        data = json.loads(data)
    employee = _get_employee()
    allowed = ["cell_number", "personal_email", "permanent_address",
               "current_address", "emergency_phone_number",
               "emergency_contact_name", "relation"]
    emp = frappe.get_doc("Employee", employee)
    for field in allowed:
        if field in data:
            emp.set(field, data[field])
    emp.save(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True}


# ═══════════════════════════════════════════════════════════════════════════
#  ATTENDANCE & LEAVE
# ═══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_attendance_data(month=None, year=None):
    """Monthly attendance calendar + leave balance + leave history."""
    employee = _get_employee()
    today    = getdate(nowdate())
    year     = cint(year  or today.year)
    month    = cint(month or today.month)

    from_date = date(year, month, 1)
    last_day  = (date(year, month % 12 + 1, 1) - timedelta(days=1)
                 if month < 12 else date(year, 12, 31))

    # Attendance records for the month
    records = frappe.db.sql("""
        SELECT attendance_date, status, in_time, out_time, late_entry
        FROM `tabAttendance`
        WHERE employee = %s
          AND attendance_date BETWEEN %s AND %s
          AND docstatus = 1
        ORDER BY attendance_date
    """, (employee, from_date, last_day), as_dict=True)

    att_map = {str(r.attendance_date): r for r in records}

    # Leave balances for all leave types
    leave_types = frappe.get_all("Leave Type", fields=["name", "color"],
                                  filters={"is_lwp": 0}, limit=10)
    balances = []
    for lt in leave_types:
        alloc = frappe.db.sql("""
            SELECT SUM(total_leaves_allocated) AS allocated,
                   SUM(total_leaves_allocated - carry_forwarded_leaves_count) AS used
            FROM `tabLeave Allocation`
            WHERE employee = %s AND leave_type = %s
              AND docstatus = 1
              AND %s BETWEEN from_date AND to_date
        """, (employee, lt.name, nowdate()), as_dict=True)
        row = alloc[0] if alloc else {}
        allocated = flt(row.get("allocated"))
        if allocated > 0:
            used_leave = frappe.db.sql("""
                SELECT COALESCE(SUM(total_leave_days),0) AS used
                FROM `tabLeave Application`
                WHERE employee=%s AND leave_type=%s AND status='Approved'
                  AND docstatus=1 AND from_date >= %s
            """, (employee, lt.name, "{0}-01-01".format(year)), as_dict=True)
            used = flt(used_leave[0].get("used")) if used_leave else 0
            balances.append({
                "leave_type": lt.name,
                "color": lt.color or "#7C3AED",
                "allocated": allocated,
                "used": used,
                "remaining": max(0, allocated - used),
            })

    # Leave applications (history)
    history = frappe.get_all(
        "Leave Application",
        filters={"employee": employee},
        fields=["name", "leave_type", "from_date", "to_date",
                "total_leave_days", "status", "description"],
        order_by="from_date desc", limit=20
    )

    # Summary stats
    present = sum(1 for r in records if r.status == "Present")
    absent  = sum(1 for r in records if r.status == "Absent")
    wfh     = sum(1 for r in records if r.status == "Work From Home")
    holiday = sum(1 for r in records if r.status in ("Holiday", "Weekly Off"))

    return {
        "year": year, "month": month,
        "from_date": str(from_date), "to_date": str(last_day),
        "attendance_map": att_map,
        "leave_balances": balances,
        "leave_history": history,
        "summary": {"present": present, "absent": absent,
                    "wfh": wfh, "holiday": holiday},
    }


@frappe.whitelist()
def apply_leave(leave_type, from_date, to_date, description=None, half_day=0,
                half_day_date=None, follow_via_email=1, delegate_to=None):
    """Submit a Leave Application on behalf of the employee."""
    employee = _get_employee()

    # Validate balance
    _check_leave_balance(employee, leave_type, from_date, to_date)

    doc = frappe.new_doc("Leave Application")
    doc.employee      = employee
    doc.leave_type    = leave_type
    doc.from_date     = from_date
    doc.to_date       = to_date
    doc.description   = description or ""
    doc.half_day      = cint(half_day)
    doc.half_day_date = half_day_date
    doc.status        = "Open"
    doc.follow_via_email = cint(follow_via_email)
    doc.insert(ignore_permissions=True)

    # Create handover note if delegate supplied
    if delegate_to:
        _create_handover(employee, delegate_to, from_date, to_date, leave_type)

    _push_notification(employee,
        "Leave Application Submitted",
        "Your {0} application ({1} to {2}) has been submitted.".format(
            leave_type, format_date(from_date), format_date(to_date)),
        "leave", doc.name, "attendance")

    frappe.db.commit()
    return {"success": True, "name": doc.name}


def _check_leave_balance(employee, leave_type, from_date, to_date):
    total_days = date_diff(to_date, from_date) + 1
    bal = _get_leave_balance(employee, leave_type)
    if bal is not None and flt(bal) < total_days:
        frappe.throw(
            _("Insufficient {0} balance. Available: {1} day(s), Requested: {2} day(s)").format(
                leave_type, flt(bal, 1), total_days))


def _get_leave_balance(employee, leave_type):
    result = frappe.db.sql("""
        SELECT SUM(total_leaves_allocated - carry_forwarded_leaves_count)
        FROM `tabLeave Allocation`
        WHERE employee = %s AND leave_type = %s
          AND docstatus = 1 AND %s BETWEEN from_date AND to_date
    """, (employee, leave_type, nowdate()))
    alloc = flt(result[0][0]) if result else 0
    used  = frappe.db.sql("""
        SELECT COALESCE(SUM(total_leave_days), 0)
        FROM `tabLeave Application`
        WHERE employee=%s AND leave_type=%s AND status='Approved' AND docstatus=1
    """, (employee, leave_type))
    used_val = flt(used[0][0]) if used else 0
    return max(0, alloc - used_val)


def _create_handover(employee, delegate_to, from_date, to_date, context=""):
    if not frappe.db.exists("DocType", "Handover Note"):
        return
    h = frappe.new_doc("Handover Note")
    h.employee       = employee
    h.delegate_to    = delegate_to
    h.effective_date = from_date
    h.title          = "Leave Handover – {0}".format(context)
    h.insert(ignore_permissions=True)


# ═══════════════════════════════════════════════════════════════════════════
#  PAYROLL
# ═══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_payroll_data(year=None):
    """Payslip list, latest breakdown, and YTD summary."""
    employee = _get_employee()
    year     = year or getdate(nowdate()).year

    slips = frappe.get_all(
        "Salary Slip",
        filters={"employee": employee, "docstatus": 1},
        fields=["name", "posting_date", "gross_pay", "net_pay",
                "total_deduction", "start_date", "end_date",
                "payment_days", "working_days"],
        order_by="posting_date desc", limit=24
    )

    # Latest breakdown by component
    breakdown = []
    if slips:
        latest = frappe.get_doc("Salary Slip", slips[0].name)
        for row in latest.earnings:
            breakdown.append({"component": row.salary_component,
                               "amount": flt(row.amount), "type": "earning"})
        for row in latest.deductions:
            breakdown.append({"component": row.salary_component,
                               "amount": flt(row.amount), "type": "deduction"})

    # YTD aggregates for the year
    ytd = frappe.db.sql("""
        SELECT
            MONTH(posting_date) AS m,
            SUM(gross_pay)       AS gross,
            SUM(net_pay)         AS net,
            SUM(total_deduction) AS deductions
        FROM `tabSalary Slip`
        WHERE employee = %s AND YEAR(posting_date) = %s AND docstatus = 1
        GROUP BY MONTH(posting_date)
        ORDER BY m
    """, (employee, year), as_dict=True)

    # Tax computation (Ecclesia doctype)
    tax_comp = None
    if frappe.db.exists("DocType", "Employee Tax Computation"):
        tax_comp = frappe.db.get_value(
            "Employee Tax Computation",
            {"employee": employee},
            ["annual_gross", "taxable_income", "annual_tax", "monthly_tax",
             "pension_deduction", "nhf_deduction", "relief_allowance"],
            order_by="creation desc",
            as_dict=True
        )

    return {
        "slips": slips,
        "latest_breakdown": breakdown,
        "ytd_by_month": ytd,
        "tax_computation": tax_comp,
    }


@frappe.whitelist()
def download_payslip(slip_name):
    """Return payslip data for PDF generation on the client side."""
    employee = _get_employee()
    slip = frappe.get_doc("Salary Slip", slip_name)
    if slip.employee != employee:
        frappe.throw(_("Access denied"))
    return {
        "slip": slip.as_dict(),
        "employee": frappe.db.get_value(
            "Employee", employee,
            ["employee_name", "department", "designation", "branch"], as_dict=True)
    }


# ═══════════════════════════════════════════════════════════════════════════
#  LOANS & ADVANCES
# ═══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_loans_data():
    """Active loans, repayment schedules, expense claims."""
    employee = _get_employee()

    # Active Employee Loan Applications (Ecclesia doctype takes priority)
    loans = frappe.get_all(
        "Employee Loan Application",
        filters={"employee": employee, "docstatus": 1,
                 "status": ["not in", ["Rejected", "Cancelled"]]},
        fields=["name", "loan_type", "principal_amount", "outstanding_principal",
                "total_amount_paid", "monthly_deduction", "tenure_months",
                "installments_paid", "status", "disbursement_date",
                "first_deduction_date"],
        order_by="creation desc"
    )

    # Repayment schedules
    for loan in loans:
        schedule = frappe.get_all(
            "Loan Deduction Schedule",
            filters={"parent": loan.name},
            fields=["installment_number", "due_date", "principal",
                    "interest", "total_payment", "status"],
            order_by="installment_number"
        )
        loan["schedule"] = schedule

        # Staff Loan Payment records
        payments = frappe.get_all(
            "Staff Loan Payment",
            filters={"employee": employee,
                     "loan_type": loan.loan_type,
                     "status": ["!=", "Cancelled"]},
            fields=["name", "posting_date", "total_deducted_amount",
                    "outstanding_amount", "status"],
            order_by="posting_date desc", limit=12
        )
        loan["payments"] = payments

    # Expense Claims (ERPNext standard)
    expense_claims = frappe.get_all(
        "Expense Claim",
        filters={"employee": employee},
        fields=["name", "expense_approver", "total_claimed_amount",
                "total_sanctioned_amount", "status", "posting_date"],
        order_by="creation desc", limit=20
    )

    # Employee Advances
    advances = frappe.get_all(
        "Employee Advance",
        filters={"employee": employee},
        fields=["name", "purpose", "advance_amount", "claimed_amount",
                "return_amount", "status", "posting_date"],
        order_by="creation desc", limit=10
    )

    # Total outstanding
    total_outstanding = sum(flt(l.outstanding_principal) for l in loans)

    return {
        "loans": loans,
        "expense_claims": expense_claims,
        "advances": advances,
        "total_outstanding": total_outstanding,
    }


@frappe.whitelist()
def apply_loan(loan_type, principal_amount, tenure_months,
               loan_purpose=None, purpose_description=None):
    """Submit an Employee Loan Application."""
    employee = _get_employee()
    emp      = frappe.get_doc("Employee", employee)

    # Enforce 33% salary cap (Nigerian labour practice)
    monthly_salary = frappe.db.sql("""
        SELECT SUM(amount) FROM `tabSalary Detail`
        WHERE parent = (
            SELECT name FROM `tabSalary Slip`
            WHERE employee = %s AND docstatus = 1
            ORDER BY posting_date DESC LIMIT 1)
        AND parentfield = 'earnings'
    """, employee)
    gross = flt(monthly_salary[0][0]) if monthly_salary else 0

    proposed_monthly = flt(principal_amount) / max(1, cint(tenure_months))
    if gross and proposed_monthly > gross * 0.33:
        frappe.throw(_(
            "Monthly repayment of ₦{0:,.0f} exceeds 33% of gross salary "
            "(₦{1:,.0f}). Maximum allowed: ₦{2:,.0f}.".format(
                proposed_monthly, gross, gross * 0.33)))

    doc = frappe.new_doc("Employee Loan Application")
    doc.employee            = employee
    doc.employee_name       = emp.employee_name
    doc.department          = emp.department
    doc.loan_type           = loan_type
    doc.application_date    = nowdate()
    doc.principal_amount    = flt(principal_amount)
    doc.tenure_months       = cint(tenure_months)
    doc.loan_purpose        = loan_purpose
    doc.purpose_description = purpose_description
    doc.monthly_deduction   = proposed_monthly
    doc.status              = "Submitted"
    doc.insert(ignore_permissions=True)
    doc.submit()

    _push_notification(employee,
        "Loan Application Submitted",
        "Your {0} application of ₦{1:,.0f} has been submitted for approval.".format(
            loan_type, flt(principal_amount)),
        "Loan", doc.name, "loans")

    frappe.db.commit()
    return {"success": True, "name": doc.name}


@frappe.whitelist()
def submit_expense_claim(expense_type, amount, expense_date,
                         description, cost_center=None, attachment=None):
    """Submit an Expense Claim."""
    employee = _get_employee()
    emp      = frappe.get_doc("Employee", employee)

    doc = frappe.new_doc("Expense Claim")
    doc.employee        = employee
    doc.employee_name   = emp.employee_name
    doc.company         = emp.company
    doc.posting_date    = expense_date or nowdate()
    doc.expense_approver = frappe.db.get_value(
        "Employee", emp.reports_to, "user_id") if emp.reports_to else None
    doc.append("expenses", {
        "expense_date": expense_date or nowdate(),
        "expense_type": expense_type,
        "description": description,
        "amount": flt(amount),
        "cost_center": cost_center,
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True, "name": doc.name}


# ═══════════════════════════════════════════════════════════════════════════
#  PERFORMANCE & GOALS
# ═══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_performance_data():
    """Current cycle score, goals, appraisal history, training plan."""
    employee = _get_employee()

    # Active performance cycle
    cycle = frappe.db.get_value(
        "Performance Cycle",
        {"status": "Active"},
        ["name", "title", "cycle_type", "self_appraisal_deadline",
         "manager_review_deadline", "kpi_weight", "self_weight",
         "peer_weight", "manager_weight"],
        as_dict=True
    )

    # Latest performance record (Ecclesia)
    perf_record = None
    if frappe.db.exists("DocType", "Employee Performance Record"):
        perf_record = frappe.db.get_value(
            "Employee Performance Record",
            {"employee": employee, "status": ["!=", "Cancelled"]},
            ["name", "cycle", "composite_score", "final_rating",
             "calibrated_rating", "kpi_score", "self_score",
             "peer_score", "manager_score", "status"],
            order_by="creation desc",
            as_dict=True
        )

    # Goals for current cycle
    goals = []
    if cycle and frappe.db.exists("DocType", "Performance Goal"):
        goals = frappe.get_all(
            "Performance Goal",
            filters={"employee": employee, "performance_cycle": cycle["name"]},
            fields=["name", "goal_title", "category", "target_date",
                    "progress", "status", "kpi_description"],
            order_by="creation"
        )

    # Appraisal history (ERPNext Appraisal)
    appraisals = frappe.get_all(
        "Appraisal",
        filters={"employee": employee, "docstatus": 1},
        fields=["name", "appraisal_cycle", "total_score", "creation"],
        order_by="creation desc", limit=10
    )

    # Training (ERPNext)
    training_results = frappe.get_all(
        "Training Result",
        filters={"employee": employee},
        fields=["name", "training_event", "grade", "creation"],
        order_by="creation desc", limit=10
    )

    training_events = frappe.get_all(
        "Training Event",
        filters={"attendees.employee": employee,
                 "event_status": ["!=", "Cancelled"]},
        fields=["name", "event_name", "start_time", "event_status"],
        order_by="start_time desc", limit=10
    )

    return {
        "cycle": cycle,
        "performance_record": perf_record,
        "goals": goals,
        "appraisals": appraisals,
        "training_results": training_results,
        "training_events": training_events,
    }


@frappe.whitelist()
def submit_self_appraisal(cycle, achievements, challenges, training_done,
                           self_rating, development_goals, comments=None):
    """Write self-appraisal data into the Employee Performance Record."""
    employee = _get_employee()

    record = frappe.db.get_value(
        "Employee Performance Record",
        {"employee": employee, "cycle": cycle},
        "name"
    )
    if not record:
        doc = frappe.new_doc("Employee Performance Record")
        doc.employee = employee
        doc.cycle    = cycle
        doc.status   = "Self Appraisal"
    else:
        doc = frappe.get_doc("Employee Performance Record", record)

    doc.self_narrative     = (
        "Achievements:\n{0}\n\nChallenges:\n{1}\n\n"
        "Training Completed:\n{2}\n\nDevelopment Goals:\n{3}\n\n"
        "Additional Comments:\n{4}".format(
            achievements, challenges, training_done,
            development_goals, comments or "")
    )
    doc.self_score          = cint(self_rating)
    doc.self_appraisal_date = nowdate()
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    _push_notification(employee,
        "Self-Appraisal Submitted",
        "Your self-appraisal for {0} has been submitted.".format(cycle),
        "Appraisal", doc.name, "performance")

    return {"success": True, "name": doc.name}


@frappe.whitelist()
def add_goal(cycle, goal_title, category, target_date, kpi_description=None):
    """Add a performance goal for the employee."""
    employee = _get_employee()

    if not frappe.db.exists("DocType", "Performance Goal"):
        frappe.throw(_("Performance Goal DocType not found"))

    doc = frappe.new_doc("Performance Goal")
    doc.employee          = employee
    doc.performance_cycle = cycle
    doc.goal_title        = goal_title
    doc.category          = category
    doc.target_date       = target_date
    doc.kpi_description   = kpi_description
    doc.status            = "In Progress"
    doc.progress          = 0
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True, "name": doc.name}


@frappe.whitelist()
def update_goal_progress(goal_name, progress, status=None):
    """Update % progress on a goal."""
    employee = _get_employee()
    doc = frappe.get_doc("Performance Goal", goal_name)
    if doc.employee != employee:
        frappe.throw(_("Access denied"))
    doc.progress = cint(progress)
    if status:
        doc.status = status
    if cint(progress) == 100 and not status:
        doc.status = "Completed"
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True}


# ═══════════════════════════════════════════════════════════════════════════
#  TASKS & WFH
# ═══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_tasks_data():
    """ESS Tasks kanban + WFH status + work session log."""
    employee = _get_employee()
    today    = nowdate()

    # ESS Tasks (Ecclesia)
    tasks = frappe.get_all(
        "ESS Task",
        filters={"assigned_to": employee},
        fields=["name", "title", "task_category", "priority", "status",
                "due_date", "description", "assigned_by_name",
                "assigned_on", "completed_on"],
        order_by="due_date asc", limit=50
    )

    # WFH Request
    wfh_requests = frappe.get_all(
        "WFH Request",
        filters={"employee": employee},
        fields=["name", "from_date", "to_date", "work_mode",
                "status", "total_days", "expected_deliverables"],
        order_by="from_date desc", limit=10
    )

    # WFH Session (today)
    today_session = frappe.db.get_value(
        "WFH Session",
        {"employee": employee, "date": today, "docstatus": ["!=", 2]},
        ["name", "check_in_time", "check_out_time", "total_hours",
         "status", "work_mode"],
        as_dict=True
    )

    # WFH Daily Summary
    wfh_summary = frappe.db.get_value(
        "WFH Daily Summary",
        {"employee": employee, "date": today},
        ["name", "total_hours", "tasks_completed", "summary"],
        as_dict=True
    )

    # Work sessions this week
    week_start = add_days(today, -getdate(today).weekday())
    work_sessions = frappe.get_all(
        "Work Session",
        filters={"employee": employee,
                 "date": [">=", week_start],
                 "docstatus": ["!=", 2]},
        fields=["name", "date", "check_in_time", "check_out_time",
                "total_hours", "work_mode", "status"],
        order_by="date desc"
    )

    # Activity log
    activity_log = frappe.get_all(
        "Work Activity Log",
        filters={"employee": employee,
                 "creation": [">=", add_days(today, -7)]},
        fields=["name", "activity_type", "doctype_name",
                "creation", "duration_minutes"],
        order_by="creation desc", limit=20
    )

    return {
        "tasks": tasks,
        "wfh_requests": wfh_requests,
        "today_session": today_session,
        "wfh_summary": wfh_summary,
        "work_sessions": work_sessions,
        "activity_log": activity_log,
    }


@frappe.whitelist()
def create_ess_task(title, task_category, priority, due_date,
                    description=None, linked_doctype=None, linked_docname=None):
    """Create a new ESS Task for the employee."""
    employee = _get_employee()
    emp = frappe.get_doc("Employee", employee)

    doc = frappe.new_doc("ESS Task")
    doc.assigned_to      = employee
    doc.assigned_by      = employee
    doc.assigned_by_name = emp.employee_name
    doc.title            = title
    doc.task_category    = task_category
    doc.priority         = priority
    doc.due_date         = due_date
    doc.status           = "Open"
    doc.description      = description
    if linked_doctype:
        doc.linked_doctype = linked_doctype
        doc.linked_docname = linked_docname
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True, "name": doc.name}


@frappe.whitelist()
def update_task_status(task_name, status):
    """Move ESS task between kanban columns."""
    employee = _get_employee()
    doc = frappe.get_doc("ESS Task", task_name)
    if doc.assigned_to != employee:
        frappe.throw(_("Access denied"))
    doc.status = status
    if status == "Completed":
        doc.completed_on = now_datetime()
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True}


@frappe.whitelist()
def log_wfh(from_date, to_date, work_mode, expected_deliverables,
            reason=None, approver=None):
    """Submit a WFH Request."""
    employee = _get_employee()
    emp      = frappe.get_doc("Employee", employee)

    doc = frappe.new_doc("WFH Request")
    doc.employee               = employee
    doc.employee_name          = emp.employee_name
    doc.department             = emp.department
    doc.designation            = emp.designation
    doc.from_date              = from_date
    doc.to_date                = to_date
    doc.work_mode              = work_mode or "WFH"
    doc.expected_deliverables  = expected_deliverables
    doc.reason                 = reason
    doc.status                 = "Pending"
    doc.approver               = (approver or
                                  frappe.db.get_value("Employee", emp.reports_to, "user_id"))
    doc.insert(ignore_permissions=True)
    doc.submit()

    # Auto-create WFH Session for single-day requests
    if from_date == to_date:
        sess = frappe.new_doc("WFH Session")
        sess.employee       = employee
        sess.employee_name  = emp.employee_name
        sess.department     = emp.department
        sess.date           = from_date
        sess.wfh_request    = doc.name
        sess.work_mode      = work_mode or "WFH"
        sess.status         = "Open"
        sess.check_in_time  = now_datetime()
        sess.insert(ignore_permissions=True)

    frappe.db.commit()
    return {"success": True, "name": doc.name}


@frappe.whitelist()
def checkin_wfh(session_name=None):
    """Start or update a WFH session check-in."""
    employee = _get_employee()
    today    = nowdate()

    if session_name:
        sess = frappe.get_doc("WFH Session", session_name)
        if sess.employee != employee:
            frappe.throw(_("Access denied"))
    else:
        existing = frappe.db.get_value(
            "WFH Session",
            {"employee": employee, "date": today, "status": "Open"},
            "name"
        )
        if existing:
            return {"success": True, "name": existing, "already_open": True}
        emp  = frappe.get_doc("Employee", employee)
        sess = frappe.new_doc("WFH Session")
        sess.employee      = employee
        sess.employee_name = emp.employee_name
        sess.department    = emp.department
        sess.date          = today
        sess.work_mode     = "WFH"
        sess.status        = "Open"
        sess.check_in_time = now_datetime()
        sess.insert(ignore_permissions=True)

    frappe.db.commit()
    return {"success": True, "name": sess.name, "check_in_time": sess.check_in_time}


@frappe.whitelist()
def checkout_wfh(session_name):
    """End a WFH session."""
    employee = _get_employee()
    sess = frappe.get_doc("WFH Session", session_name)
    if sess.employee != employee:
        frappe.throw(_("Access denied"))
    sess.check_out_time = now_datetime()
    sess.status = "Completed"
    if sess.check_in_time:
        delta = get_datetime(sess.check_out_time) - get_datetime(sess.check_in_time)
        sess.total_hours = flt(delta.total_seconds() / 3600, 2)
    sess.save(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True, "total_hours": sess.total_hours}


# ═══════════════════════════════════════════════════════════════════════════
#  POLICY LIBRARY
# ═══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_policies_data():
    """All company policies with acknowledgement status for this employee."""
    employee = _get_employee()

    policies = frappe.get_all(
        "Company Policy",
        filters={"status": "Active"},
        fields=["name", "policy_code", "title", "category", "policy_type",
                "version", "effective_date", "requires_acknowledgement",
                "acknowledgement_deadline_days", "content", "attachment"],
        order_by="category, title"
    )

    # Fetch acknowledgement records for this employee
    ack_map = {}
    acks = frappe.get_all(
        "Policy Acknowledgement",
        filters={"employee": employee},
        fields=["policy", "status", "acknowledged_on", "policy_version"]
    )
    for a in acks:
        ack_map[a.policy] = a

    for p in policies:
        ack = ack_map.get(p.name)
        p["ack_status"]     = ack.status if ack else "Pending"
        p["acknowledged_on"] = ack.acknowledged_on if ack else None
        p["ack_version"]    = ack.policy_version if ack else None

        # Calculate deadline
        if p.requires_acknowledgement and p.acknowledgement_deadline_days:
            eff = getdate(p.effective_date)
            deadline = add_days(str(eff), cint(p.acknowledgement_deadline_days))
            p["deadline"] = str(deadline)
            p["days_remaining"] = max(0, date_diff(deadline, nowdate()))
        else:
            p["deadline"] = None
            p["days_remaining"] = None

    total    = len(policies)
    acked    = sum(1 for p in policies if p["ack_status"] == "Acknowledged")
    pending  = total - acked

    return {
        "policies": policies,
        "total": total,
        "acknowledged": acked,
        "pending": pending,
    }


@frappe.whitelist()
def acknowledge_policy(policy_name):
    """Mark a policy as acknowledged by the current employee."""
    employee = _get_employee()
    emp      = frappe.get_doc("Employee", employee)
    policy   = frappe.get_doc("Company Policy", policy_name)

    existing = frappe.db.get_value(
        "Policy Acknowledgement",
        {"policy": policy_name, "employee": employee},
        "name"
    )
    if existing:
        doc = frappe.get_doc("Policy Acknowledgement", existing)
        doc.status          = "Acknowledged"
        doc.acknowledged_on = now_datetime()
        doc.policy_version  = policy.version
        doc.save(ignore_permissions=True)
    else:
        doc = frappe.new_doc("Policy Acknowledgement")
        doc.policy          = policy_name
        doc.policy_title    = policy.title
        doc.policy_version  = policy.version
        doc.employee        = employee
        doc.employee_name   = emp.employee_name
        doc.department      = emp.department
        doc.designation     = emp.designation
        doc.status          = "Acknowledged"
        doc.acknowledged_on = now_datetime()
        doc.insert(ignore_permissions=True)

    frappe.db.commit()
    return {"success": True, "name": doc.name}


def _count_pending_policy_acks(employee):
    policies = frappe.get_all(
        "Company Policy",
        filters={"status": "Active", "requires_acknowledgement": 1},
        fields=["name"]
    )
    acked = frappe.get_all(
        "Policy Acknowledgement",
        filters={"employee": employee, "status": "Acknowledged"},
        fields=["policy"]
    )
    acked_set = {a.policy for a in acked}
    return sum(1 for p in policies if p.name not in acked_set)


def _get_unacknowledged_policies(employee):
    policies = frappe.get_all(
        "Company Policy",
        filters={"status": "Active", "requires_acknowledgement": 1},
        fields=["name", "title", "acknowledgement_deadline_days", "effective_date"]
    )
    acked_set = {
        a.policy for a in frappe.get_all(
            "Policy Acknowledgement",
            filters={"employee": employee, "status": "Acknowledged"},
            fields=["policy"])
    }
    result = []
    for p in policies:
        if p.name in acked_set:
            continue
        days_remaining = None
        if p.acknowledgement_deadline_days and p.effective_date:
            deadline = add_days(str(getdate(p.effective_date)),
                                cint(p.acknowledgement_deadline_days))
            days_remaining = max(0, date_diff(deadline, nowdate()))
        result.append({
            "policy": p.name,
            "policy_title": p.title,
            "days_remaining": days_remaining
        })
    return result


# ═══════════════════════════════════════════════════════════════════════════
#  MESSAGES
# ═══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_messages_data():
    """Internal chats, announcements, communiqués."""
    employee = _get_employee()
    user     = frappe.session.user

    # WA Internal Chats (Ecclesia)
    chats = []
    if frappe.db.exists("DocType", "WA Internal Chat"):
        chats = frappe.get_all(
            "WA Internal Chat",
            filters={"members.member": user},
            fields=["name", "chat_name", "last_message", "last_message_time",
                    "unread_count", "chat_type"],
            order_by="last_message_time desc", limit=20
        )

    # Message Blasts addressed to this employee or all staff
    blasts = frappe.get_all(
        "Message Blast",
        filters={"docstatus": 1, "status": "Sent"},
        fields=["name", "subject", "message", "creation", "sent_by"],
        order_by="creation desc", limit=20
    )

    # Communiques
    communiques = []
    if frappe.db.exists("DocType", "Communique"):
        communiques = frappe.get_all(
            "Communique",
            filters={"docstatus": 1},
            fields=["name", "subject", "from_designation",
                    "creation", "message"],
            order_by="creation desc", limit=20
        )

    return {
        "chats": chats,
        "announcements": blasts,
        "communiques": communiques,
    }


@frappe.whitelist()
def send_internal_message(recipient_user, message_text):
    """Send a WA Internal Chat message."""
    sender = frappe.session.user

    if not frappe.db.exists("DocType", "WA Internal Chat"):
        frappe.throw(_("Internal messaging not configured. Please enable WA Internal Chat."))

    # Find or create 1-to-1 chat
    existing = frappe.db.sql("""
        SELECT wc.name FROM `tabWA Internal Chat` wc
        INNER JOIN `tabWA Internal Chat Member` m1 ON m1.parent=wc.name AND m1.member=%s
        INNER JOIN `tabWA Internal Chat Member` m2 ON m2.parent=wc.name AND m2.member=%s
        WHERE wc.chat_type='Direct'
        LIMIT 1
    """, (sender, recipient_user))

    if existing:
        chat_name = existing[0][0]
        chat = frappe.get_doc("WA Internal Chat", chat_name)
    else:
        chat = frappe.new_doc("WA Internal Chat")
        chat.chat_type = "Direct"
        chat.chat_name = "{0} ↔ {1}".format(
            frappe.db.get_value("User", sender, "full_name"),
            frappe.db.get_value("User", recipient_user, "full_name"))
        chat.append("members", {"member": sender})
        chat.append("members", {"member": recipient_user})
        chat.insert(ignore_permissions=True)

    msg = frappe.new_doc("WA Internal Chat Message")
    msg.chat       = chat.name
    msg.sender     = sender
    msg.message    = message_text
    msg.sent_at    = now_datetime()
    msg.insert(ignore_permissions=True)

    chat.last_message      = message_text[:120]
    chat.last_message_time = now_datetime()
    chat.save(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True, "chat": chat.name}


# ═══════════════════════════════════════════════════════════════════════════
#  STATUTORY & TAX
# ═══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_statutory_data(year=None):
    """PAYE, pension, NHF, NSITF data for the employee."""
    employee = _get_employee()
    year     = year or getdate(nowdate()).year
    year_str = str(year)

    # Employee Tax Computation (Ecclesia)
    tax_comp = None
    if frappe.db.exists("DocType", "Employee Tax Computation"):
        tax_comp = frappe.db.get_value(
            "Employee Tax Computation",
            {"employee": employee},
            ["annual_gross", "taxable_income", "annual_tax", "monthly_tax",
             "pension_deduction", "nhf_deduction", "relief_allowance",
             "consolidated_relief", "name"],
            order_by="creation desc",
            as_dict=True
        )

    # Pension (Ecclesia: Pension Remittance Batch → line items)
    pension_ytd = frappe.db.sql("""
        SELECT COALESCE(SUM(l.employee_contribution + l.employer_contribution), 0) AS total,
               COALESCE(SUM(l.employee_contribution), 0) AS employee_part,
               COALESCE(SUM(l.employer_contribution), 0) AS employer_part
        FROM `tabPencom Remittance Line` l
        INNER JOIN `tabPension Remittance Batch` b ON l.parent = b.name
        WHERE l.employee = %s AND YEAR(b.period_date) = %s AND b.docstatus = 1
    """, (employee, year), as_dict=True)
    pension = pension_ytd[0] if pension_ytd else {}

    # Pension manager & RSA
    pension_mgr = frappe.db.get_value(
        "Pension Manager",
        {"employee": employee},
        ["pfa_name", "rsa_pin", "monthly_contribution"],
        as_dict=True
    )

    # NHF (Ecclesia)
    nhf_ytd = None
    if frappe.db.exists("DocType", "NHF Remittance Batch"):
        nhf_ytd = frappe.db.sql("""
            SELECT COALESCE(SUM(l.amount), 0) AS total
            FROM `tabNHF Remittance Line` l
            INNER JOIN `tabNHF Remittance Batch` b ON l.parent = b.name
            WHERE l.employee = %s AND YEAR(b.period_date) = %s AND b.docstatus = 1
        """, (employee, year), as_dict=True)

    # NSITF
    nsitf_ytd = None
    if frappe.db.exists("DocType", "NSITF Assessment"):
        nsitf_ytd = frappe.db.get_value(
            "NSITF Assessment",
            {"year": year_str, "docstatus": 1},
            "assessment_amount",
            as_dict=False
        )

    # Monthly PAYE from salary slips
    monthly_paye = frappe.db.sql("""
        SELECT MONTH(posting_date) AS m,
               SUM(amount) AS paye
        FROM `tabSalary Detail`
        WHERE parent IN (
            SELECT name FROM `tabSalary Slip`
            WHERE employee=%s AND YEAR(posting_date)=%s AND docstatus=1)
          AND salary_component LIKE '%%PAYE%%'
        GROUP BY MONTH(posting_date)
        ORDER BY m
    """, (employee, year), as_dict=True)

    return {
        "tax_computation": tax_comp,
        "pension_ytd": pension,
        "pension_manager": pension_mgr,
        "nhf_ytd": flt(nhf_ytd[0].total) if nhf_ytd else 0,
        "nsitf_ytd": flt(nsitf_ytd) if nsitf_ytd else 0,
        "monthly_paye": monthly_paye,
        "year": year,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  NOTIFICATIONS  (ESS Notification Log)
# ═══════════════════════════════════════════════════════════════════════════

def _push_notification(employee, title, message, notification_type="System",
                        link_name=None, portal_section=None, priority="Medium"):
    """Internal helper — insert an ESS Notification Log entry."""
    if not frappe.db.exists("DocType", "ESS Notification Log"):
        return
    doc = frappe.new_doc("ESS Notification Log")
    doc.employee          = employee
    doc.notification_type = notification_type
    doc.title             = title
    doc.message           = message
    doc.is_read           = 0
    doc.link_name         = link_name
    doc.portal_section    = portal_section
    doc.priority          = priority
    doc.insert(ignore_permissions=True)


@frappe.whitelist()
def get_notifications(limit=20):
    """Return ESS notifications for the current employee."""
    if not frappe.db.exists("DocType", "ESS Notification Log"):
        return {"notifications": [], "unread": 0}
    employee = _get_employee()
    notifs = frappe.get_all(
        "ESS Notification Log",
        filters={"employee": employee},
        fields=["name", "notification_type", "title", "message",
                "is_read", "creation", "portal_section", "priority"],
        order_by="creation desc",
        limit=cint(limit)
    )
    unread = sum(1 for n in notifs if not n.is_read)
    return {"notifications": notifs, "unread": unread}


@frappe.whitelist()
def mark_notifications_read(names=None):
    """Mark one, many, or all notifications as read."""
    employee = _get_employee()
    if not frappe.db.exists("DocType", "ESS Notification Log"):
        return {"success": True}
    filters = {"employee": employee, "is_read": 0}
    if names:
        if isinstance(names, str):
            names = json.loads(names)
        filters["name"] = ["in", names]
    frappe.db.set_value("ESS Notification Log", filters, {
        "is_read": 1, "read_on": now_datetime()})
    frappe.db.commit()
    return {"success": True}


# ═══════════════════════════════════════════════════════════════════════════
#  PULSE SCORE  (compute & cache)
# ═══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def compute_pulse_score(employee=None):
    """
    Compute the 4-component ESS Pulse Score for the employee and save to
    ESS Pulse Score DocType.  Can be called from a Scheduler Event or on demand.
    """
    employee = employee or _get_employee()
    today    = nowdate()
    month_start = str(get_first_day(today))
    month_end   = str(get_last_day(today))

    # 1. Attendance score
    present = frappe.db.count(
        "Attendance",
        {"employee": employee,
         "attendance_date": ["between", [month_start, today]],
         "status": "Present", "docstatus": 1})
    working = frappe.db.count(
        "Attendance",
        {"employee": employee,
         "attendance_date": ["between", [month_start, today]],
         "docstatus": 1}) or 1
    attendance_score = round(present / working * 100, 1)

    # 2. Task completion score
    total_tasks = frappe.db.count("ESS Task", {
        "assigned_to": employee, "assigned_on": [">=", month_start]}) or 1
    done_tasks = frappe.db.count("ESS Task", {
        "assigned_to": employee, "assigned_on": [">=", month_start],
        "status": "Completed"})
    task_score = round(done_tasks / total_tasks * 100, 1)

    # 3. Leave health score (ratio of remaining annual leave vs full entitlement)
    remaining  = _get_leave_balance(employee, "Annual Leave")
    alloc_val  = frappe.db.sql("""
        SELECT COALESCE(SUM(total_leaves_allocated),0)
        FROM `tabLeave Allocation`
        WHERE employee=%s AND leave_type='Annual Leave' AND docstatus=1
          AND %s BETWEEN from_date AND to_date
    """, (employee, today))
    total_alloc = flt(alloc_val[0][0]) if alloc_val else 20
    leave_health_score = round(flt(remaining) / max(1, total_alloc) * 100, 1)

    # 4. Performance score from latest record
    perf_score = 0
    if frappe.db.exists("DocType", "Employee Performance Record"):
        score = frappe.db.get_value(
            "Employee Performance Record",
            {"employee": employee},
            "composite_score",
            order_by="creation desc"
        )
        perf_score = flt(score, 1) if score else 0

    overall = round(
        (attendance_score + task_score + leave_health_score + perf_score) / 4, 1)

    if not frappe.db.exists("DocType", "ESS Pulse Score"):
        return {
            "attendance_score": attendance_score,
            "task_score": task_score,
            "leave_health_score": leave_health_score,
            "performance_score": perf_score,
            "overall_pulse_score": overall,
        }

    # Upsert into ESS Pulse Score
    period_label = today[:7]  # YYYY-MM
    existing = frappe.db.get_value(
        "ESS Pulse Score",
        {"employee": employee, "period": period_label}, "name")
    if existing:
        frappe.db.set_value("ESS Pulse Score", existing, {
            "attendance_score":   attendance_score,
            "task_score":         task_score,
            "leave_health_score": leave_health_score,
            "performance_score":  perf_score,
            "overall_pulse_score": overall,
            "computed_on":        now_datetime(),
        })
    else:
        doc = frappe.new_doc("ESS Pulse Score")
        doc.employee           = employee
        doc.period             = period_label
        doc.period_start       = month_start
        doc.period_end         = month_end
        doc.attendance_score   = attendance_score
        doc.task_score         = task_score
        doc.leave_health_score = leave_health_score
        doc.performance_score  = perf_score
        doc.overall_pulse_score = overall
        doc.computed_on        = now_datetime()
        doc.insert(ignore_permissions=True)

    frappe.db.commit()
    return {
        "attendance_score":   attendance_score,
        "task_score":         task_score,
        "leave_health_score": leave_health_score,
        "performance_score":  perf_score,
        "overall_pulse_score": overall,
    }