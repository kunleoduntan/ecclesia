"""
ecclesia/api/performance_scheduler.py
=======================================
All scheduled background jobs for the performance management module.
Registered in hooks.py under scheduler_events.

Place at: ecclesia/ecclesia/api/performance_scheduler.py
"""
import frappe
from frappe.utils import (
    nowdate, add_days, getdate, date_diff, flt, cint
)


# ── DAILY JOBS ────────────────────────────────────────────────────────

def send_deadline_reminders():
    """
    Runs daily. Sends reminder emails 3 days and 1 day before each
    cycle stage deadline. Covers: goal setting, self-appraisal,
    peer review, manager review, calibration.
    """
    today = getdate(nowdate())
    warn_days = [3, 1]   # send reminders at 3 days and 1 day out

    active_cycles = frappe.get_all("Performance Cycle",
        filters={"status": "Active"},
        fields=["name", "title", "company",
                "goal_setting_deadline", "self_appraisal_deadline",
                "peer_review_deadline", "manager_review_deadline",
                "calibration_deadline"])

    for cycle in active_cycles:
        stages = [
            ("goal_setting_deadline",   "Goal Setting",    "Employee"),
            ("self_appraisal_deadline", "Self Appraisal",  "Employee"),
            ("peer_review_deadline",    "Peer Review",     "Employee"),
            ("manager_review_deadline", "Manager Review",  "Line Manager"),
            ("calibration_deadline",    "Calibration",     "HR Manager"),
        ]
        for field, label, role in stages:
            deadline = cycle.get(field)
            if not deadline:
                continue
            days_left = date_diff(deadline, today)
            if days_left not in warn_days:
                continue

            # Find employees who still have a pending action
            if label == "Self Appraisal":
                _remind_pending_self_appraisals(cycle, label, days_left)
            elif label == "Peer Review":
                _remind_pending_peer_reviews(cycle, label, days_left)
            elif label == "Manager Review":
                _remind_pending_manager_reviews(cycle, label, days_left)
            elif label == "Goal Setting":
                _remind_goal_setting(cycle, label, days_left)


def _remind_pending_self_appraisals(cycle, label, days_left):
    submitted = frappe.db.sql_list("""
        SELECT employee FROM `tabSelf Appraisal`
        WHERE performance_cycle=%s AND docstatus=1
    """, cycle.name)

    employees = frappe.get_all("Employee",
        filters={"status": "Active", "company": cycle.company},
        fields=["name", "employee_name", "user_id"])

    for emp in employees:
        if emp.name in submitted or not emp.user_id:
            continue
        frappe.sendmail(
            recipients=[emp.user_id],
            subject=f"Reminder: Self Appraisal due in {days_left} day(s) — {cycle.title}",
            message=(f"Dear {emp.employee_name},<br><br>"
                     f"Your <b>Self Appraisal</b> for <b>{cycle.title}</b> is due in "
                     f"<b>{days_left} day(s)</b>. Please log in and submit before the deadline.")
        )


def _remind_pending_peer_reviews(cycle, label, days_left):
    pending_rows = frappe.db.sql("""
        SELECT prp.peer, prp.peer_name
        FROM `tabPeer Review Request Peer` prp
        JOIN `tabPeer Review Request` prr ON prr.name = prp.parent
        WHERE prr.performance_cycle=%s AND prp.status='Pending'
    """, cycle.name, as_dict=True)

    seen = set()
    for row in pending_rows:
        if row.peer in seen:
            continue
        seen.add(row.peer)
        peer_user = frappe.db.get_value("Employee", row.peer, "user_id")
        if peer_user:
            frappe.sendmail(
                recipients=[peer_user],
                subject=f"Reminder: Peer Review due in {days_left} day(s) — {cycle.title}",
                message=(f"You have one or more pending peer reviews for <b>{cycle.title}</b> "
                         f"due in <b>{days_left} day(s)</b>. Log in to complete them.")
            )


def _remind_pending_manager_reviews(cycle, label, days_left):
    submitted_for = frappe.db.sql_list("""
        SELECT employee FROM `tabManager Review 360`
        WHERE performance_cycle=%s AND docstatus=1
    """, cycle.name)

    managers = frappe.db.sql("""
        SELECT DISTINCT e.reports_to, mgr.user_id,
               COUNT(e.name) AS report_count
        FROM `tabEmployee` e
        JOIN `tabEmployee` mgr ON mgr.name = e.reports_to
        WHERE e.status='Active' AND e.company=%s AND e.reports_to IS NOT NULL
        GROUP BY e.reports_to
    """, cycle.company, as_dict=True)

    for mgr in managers:
        if not mgr.user_id:
            continue
        # Check if all reports reviewed
        reports = frappe.db.sql_list("""
            SELECT name FROM `tabEmployee`
            WHERE reports_to=%s AND status='Active'
        """, mgr.reports_to)
        pending = [r for r in reports if r not in submitted_for]
        if not pending:
            continue
        frappe.sendmail(
            recipients=[mgr.user_id],
            subject=f"Reminder: Manager Reviews due in {days_left} day(s) — {cycle.title}",
            message=(f"You have <b>{len(pending)}</b> pending manager review(s) for "
                     f"<b>{cycle.title}</b> due in <b>{days_left} day(s)</b>. Please complete them.")
        )


def _remind_goal_setting(cycle, label, days_left):
    employees_with_approved = frappe.db.sql_list("""
        SELECT DISTINCT owner_employee FROM `tabPerformance Goal`
        WHERE performance_cycle=%s AND status='Approved'
    """, cycle.name)

    employees = frappe.get_all("Employee",
        filters={"status": "Active", "company": cycle.company},
        fields=["name", "employee_name", "user_id"])

    for emp in employees:
        if emp.name in employees_with_approved or not emp.user_id:
            continue
        frappe.sendmail(
            recipients=[emp.user_id],
            subject=f"Reminder: Set your goals — {days_left} day(s) left — {cycle.title}",
            message=(f"Dear {emp.employee_name},<br><br>"
                     f"Please submit and get your goals approved before the deadline in "
                     f"<b>{days_left} day(s)</b> for <b>{cycle.title}</b>.")
        )


def ensure_performance_records_exist():
    """
    For every active employee in an active cycle, create an
    Employee Performance Record if one doesn't already exist.
    Runs daily — safe to re-run (idempotent).
    """
    active_cycles = frappe.get_all("Performance Cycle",
        filters={"status": "Active"},
        fields=["name", "company"])

    for cycle in active_cycles:
        employees = frappe.get_all("Employee",
            filters={"status": "Active", "company": cycle.company},
            fields=["name"])

        for emp in employees:
            exists = frappe.db.exists("Employee Performance Record",
                {"employee": emp.name, "cycle": cycle.name})
            if not exists:
                try:
                    doc = frappe.new_doc("Employee Performance Record")
                    doc.employee = emp.name
                    doc.cycle    = cycle.name
                    doc.status   = "In Progress"
                    doc.insert(ignore_permissions=True)
                except Exception:
                    frappe.log_error(frappe.get_traceback(),
                        f"EPR Creation Error: {emp.name} / {cycle.name}")

    frappe.db.commit()


def flag_overdue_pip_checkins():
    """Flag PIPs where a weekly check-in is more than 7 days overdue."""
    if not frappe.db.exists("DocType", "Performance PIP"):
        return

    active_pips = frappe.get_all("Performance PIP",
        filters={"status": "Active"},
        fields=["name", "employee", "manager"])

    for pip in active_pips:
        doc = frappe.get_doc("Performance PIP", pip.name)
        if not doc.weekly_checkins:
            continue
        last = sorted(doc.weekly_checkins,
                      key=lambda r: r.checkin_date or "1900-01-01",
                      reverse=True)[0]
        if not last.checkin_date:
            continue
        days_since = date_diff(nowdate(), last.checkin_date)
        if days_since > 7:
            mgr_user = frappe.db.get_value("Employee", pip.manager, "user_id")
            emp_name = frappe.db.get_value("Employee", pip.employee, "employee_name")
            if mgr_user:
                frappe.sendmail(
                    recipients=[mgr_user],
                    subject=f"PIP Check-in Overdue: {emp_name}",
                    message=(f"The weekly PIP check-in for <b>{emp_name}</b> is "
                             f"<b>{days_since} days overdue</b>. "
                             f"Please schedule a check-in as soon as possible.")
                )


# ── WEEKLY JOBS ───────────────────────────────────────────────────────

def send_manager_pending_digest():
    """
    Weekly digest to each manager listing all pending actions:
    goal approvals, manager reviews, PIP check-ins.
    """
    active_cycle = frappe.db.get_value("Performance Cycle",
        {"status": "Active"}, "name")

    managers = frappe.db.sql("""
        SELECT DISTINCT reports_to FROM `tabEmployee`
        WHERE status='Active' AND reports_to IS NOT NULL
    """, as_list=True)

    for (manager_emp,) in managers:
        mgr_user = frappe.db.get_value("Employee", manager_emp, "user_id")
        if not mgr_user:
            continue

        mgr_name = frappe.db.get_value("Employee", manager_emp, "employee_name")
        reports  = frappe.db.sql_list("""
            SELECT name FROM `tabEmployee`
            WHERE reports_to=%s AND status='Active'
        """, manager_emp)

        if not reports:
            continue

        lines = []

        # Pending goal approvals
        pending_goals = frappe.db.count("Performance Goal",
            {"owner_employee": ["in", reports],
             "performance_cycle": active_cycle or "",
             "status": "Pending Approval"})
        if pending_goals:
            lines.append(f"<li><b>{pending_goals}</b> goal(s) awaiting your approval</li>")

        # Pending manager reviews
        if active_cycle:
            reviewed = frappe.db.sql_list("""
                SELECT employee FROM `tabManager Review 360`
                WHERE performance_cycle=%s AND docstatus=1
            """, active_cycle)
            pending_reviews = [r for r in reports if r not in reviewed]
            if pending_reviews:
                lines.append(f"<li><b>{len(pending_reviews)}</b> manager review(s) not yet submitted</li>")

        # Overdue PIP check-ins
        if frappe.db.exists("DocType", "Performance PIP"):
            active_pips = frappe.db.count("Performance PIP",
                {"manager": manager_emp, "status": "Active"})
            if active_pips:
                lines.append(f"<li><b>{active_pips}</b> active PIP(s) requiring weekly check-ins</li>")

        if not lines:
            continue

        frappe.sendmail(
            recipients=[mgr_user],
            subject="Weekly HR Digest — Your Pending Actions",
            message=(
                f"Dear {mgr_name},<br><br>"
                f"Here is your weekly summary of pending HR actions:<br><ul>"
                + "".join(lines) +
                "</ul><br>Please log in to complete these actions."
            )
        )


def send_hr_recruitment_summary():
    """
    Weekly email to HR summarising open job openings and screening status.
    """
    open_roles = frappe.get_all("Job Opening",
        filters={"status": "Open"},
        fields=["name", "job_title", "closes_on"])

    if not open_roles:
        return

    rows = ""
    for role in open_roles:
        count = frappe.db.count("Job Applicant",
            {"job_opening": role.name})
        shortlisted = frappe.db.count("Resume Screening Result",
            {"job_opening": role.name, "auto_decision": "Shortlisted"})
        rows += (f"<tr><td>{role.job_title}</td>"
                 f"<td>{count}</td><td>{shortlisted}</td>"
                 f"<td>{role.closes_on or '—'}</td></tr>")

    hr_users = frappe.get_all("Has Role",
        filters={"role": "HR Manager", "parenttype": "User"},
        fields=["parent"])

    for u in hr_users:
        email = frappe.db.get_value("User", u.parent, "email")
        if email:
            frappe.sendmail(
                recipients=[email],
                subject="Weekly Recruitment Summary",
                message=(
                    "<h3>Open Roles — Weekly Status</h3>"
                    "<table border='1' cellpadding='6' style='border-collapse:collapse'>"
                    "<tr><th>Role</th><th>Applicants</th><th>Shortlisted</th><th>Closes</th></tr>"
                    + rows + "</table>"
                )
            )


# ── MONTHLY JOBS ──────────────────────────────────────────────────────

def close_stale_goals():
    """
    Monthly: mark goals as Cancelled if they are past their due date
    and no progress has been logged. Prevents stale records polluting reports.
    """
    today = getdate(nowdate())
    stale = frappe.get_all("Performance Goal",
        filters={
            "due_date": ["<", nowdate()],
            "progress": 0,
            "status": ["in", ["Approved", "In Progress"]],
        },
        fields=["name", "goal_title", "owner_employee"])

    for goal in stale:
        frappe.db.set_value("Performance Goal", goal.name, "status", "Cancelled")
        frappe.log_error(
            f"Auto-cancelled stale goal: {goal.goal_title} ({goal.owner_employee})",
            "Stale Goal Auto-Cancel"
        )

    if stale:
        frappe.db.commit()