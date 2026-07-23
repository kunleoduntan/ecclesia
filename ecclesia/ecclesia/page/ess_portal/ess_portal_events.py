"""
ecclesia/ecclesia/page/ess_portal/ess_portal_events.py

Scheduler jobs and Document Event handlers wired through hooks.py.
Append these methods to ess_portal.py  (or import here and call from there).
"""
import frappe
from frappe.utils import (
    nowdate, now_datetime, get_first_day, get_last_day,
    flt, cint, format_date
)
from ecclesia.ecclesia.page.ess_portal.ess_portal import (
    _push_notification, compute_pulse_score
)


# ═══════════════════════════════════════════════════════════════════════════
#  DOCUMENT EVENT HANDLERS
# ═══════════════════════════════════════════════════════════════════════════

def on_leave_status_change(doc, method):
    """Push notification when a Leave Application is approved / rejected."""
    employee = doc.employee
    if doc.status == "Approved":
        _push_notification(
            employee,
            "Leave Approved ✅",
            "Your {0} ({1} to {2}) has been approved.".format(
                doc.leave_type,
                format_date(doc.from_date),
                format_date(doc.to_date)),
            notification_type="Leave",
            link_name=doc.name,
            portal_section="attendance",
            priority="High"
        )
    elif doc.status == "Rejected":
        _push_notification(
            employee,
            "Leave Application Rejected",
            "Your {0} request was not approved. Reason: {1}".format(
                doc.leave_type,
                doc.get("reason_for_rejection") or "See HR for details"),
            notification_type="Leave",
            link_name=doc.name,
            portal_section="attendance",
            priority="High"
        )
    frappe.db.commit()


def on_loan_status_change(doc, method):
    """Push notification when an Employee Loan Application status changes."""
    employee = doc.employee
    status   = doc.status

    if status == "Approved":
        _push_notification(
            employee,
            "Loan Application Approved 💳",
            "Your {0} of ₦{1:,.0f} has been approved. Disbursement pending.".format(
                doc.loan_type, flt(doc.principal_amount)),
            notification_type="Loan",
            link_name=doc.name,
            portal_section="loans",
            priority="High"
        )
    elif status == "Disbursed":
        _push_notification(
            employee,
            "Loan Disbursed 🏦",
            "₦{0:,.0f} has been disbursed for your {1}. First deduction: {2}.".format(
                flt(doc.principal_amount),
                doc.loan_type,
                format_date(doc.first_deduction_date) if doc.first_deduction_date else "next payroll"),
            notification_type="Loan",
            link_name=doc.name,
            portal_section="loans",
            priority="High"
        )
    elif status == "Rejected":
        _push_notification(
            employee,
            "Loan Application Rejected",
            "Your {0} application was rejected. Reason: {1}".format(
                doc.loan_type,
                doc.get("rejection_reason") or "Contact HR/Finance."),
            notification_type="Loan",
            link_name=doc.name,
            portal_section="loans",
            priority="High"
        )
    frappe.db.commit()


def on_expense_status_change(doc, method):
    """Push notification when an Expense Claim is actioned."""
    employee = doc.employee
    if doc.status == "Approved":
        _push_notification(
            employee,
            "Expense Claim Approved 🧾",
            "Your expense claim of ₦{0:,.0f} has been approved.".format(
                flt(doc.total_sanctioned_amount)),
            notification_type="Expense",
            link_name=doc.name,
            portal_section="loans",
            priority="Medium"
        )
    elif doc.status == "Rejected":
        _push_notification(
            employee,
            "Expense Claim Rejected",
            "Your expense claim of ₦{0:,.0f} was rejected. Contact your approver.".format(
                flt(doc.total_claimed_amount)),
            notification_type="Expense",
            link_name=doc.name,
            portal_section="loans",
            priority="Medium"
        )
    frappe.db.commit()


def on_salary_slip_submit(doc, method):
    """Push payslip-available notification when a Salary Slip is submitted."""
    employee = doc.employee
    _push_notification(
        employee,
        "Payslip Available 💰",
        "Your salary slip for {0} is ready. Net pay: ₦{1:,.0f}.".format(
            format_date(doc.posting_date),
            flt(doc.net_pay)),
        notification_type="Payroll",
        link_name=doc.name,
        portal_section="payroll",
        priority="High"
    )
    frappe.db.commit()


def on_attendance_submit(doc, method):
    """Trigger async pulse score recalculation on attendance submission."""
    frappe.enqueue(
        "ecclesia.ecclesia.page.ess_portal.ess_portal.compute_pulse_score",
        employee=doc.employee,
        queue="short",
        timeout=60
    )


def on_perf_record_update(doc, method):
    """Trigger pulse recalculation when performance score changes."""
    frappe.enqueue(
        "ecclesia.ecclesia.page.ess_portal.ess_portal.compute_pulse_score",
        employee=doc.employee,
        queue="short",
        timeout=60
    )


def on_policy_published(doc, method):
    """
    When a Company Policy requiring acknowledgement is submitted,
    push a notification to all relevant employees.
    """
    if not doc.requires_acknowledgement:
        return

    # Get applicable employees
    filters = {"status": "Active"}
    scope   = doc.get("scope") or "All Employees"

    if scope == "All Employees":
        employees = frappe.get_all("Employee", filters=filters, fields=["name"])
    else:
        # If scoped to departments/designations — extend as needed
        employees = frappe.get_all("Employee", filters=filters, fields=["name"])

    for emp in employees:
        _push_notification(
            emp.name,
            "Policy Acknowledgement Required 📜",
            "{0} — please read and acknowledge by {1}.".format(
                doc.title,
                format_date(doc.get("effective_date")) if doc.effective_date else "soon"),
            notification_type="Policy",
            link_name=doc.name,
            portal_section="policies",
            priority="High"
        )

    frappe.db.commit()


# ═══════════════════════════════════════════════════════════════════════════
#  SCHEDULER JOBS
# ═══════════════════════════════════════════════════════════════════════════

def run_daily_pulse_batch():
    """
    Daily scheduler: recompute ESS Pulse Score for every active employee.
    Runs at the start of each day via hooks.py scheduler_events["daily"].
    """
    if not frappe.db.exists("DocType", "ESS Pulse Score"):
        frappe.logger().info("ESS Pulse Score DocType not found — skipping batch")
        return

    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name"],
        limit=5000
    )
    frappe.logger().info("ESS Pulse: computing scores for {0} employees".format(
        len(employees)))

    for emp in employees:
        try:
            compute_pulse_score(employee=emp.name)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                "ESS Pulse Score Error — {0}".format(emp.name)
            )


def send_policy_ack_reminders():
    """
    Daily scheduler: send reminders for pending policy acknowledgements
    that are due within the next `reminder_interval_days`.
    """
    today = nowdate()

    policies = frappe.get_all(
        "Company Policy",
        filters={"status": "Active", "requires_acknowledgement": 1},
        fields=["name", "title", "effective_date",
                "acknowledgement_deadline_days", "reminder_interval_days"]
    )

    employees = frappe.get_all("Employee", filters={"status": "Active"},
                                fields=["name"])

    acked_pairs = set(
        (a.employee, a.policy) for a in frappe.get_all(
            "Policy Acknowledgement",
            filters={"status": "Acknowledged"},
            fields=["employee", "policy"])
    )

    for policy in policies:
        if not policy.effective_date or not policy.acknowledgement_deadline_days:
            continue
        from frappe.utils import add_days, date_diff
        deadline = add_days(
            str(policy.effective_date),
            cint(policy.acknowledgement_deadline_days))
        days_left = date_diff(deadline, today)
        reminder_interval = cint(policy.reminder_interval_days) or 3

        if 0 < days_left <= reminder_interval:
            for emp in employees:
                if (emp.name, policy.name) not in acked_pairs:
                    _push_notification(
                        emp.name,
                        "⏰ Policy Reminder: {0}".format(policy.title),
                        "You have {0} day(s) left to acknowledge "{1}".".format(
                            days_left, policy.title),
                        notification_type="Policy",
                        link_name=policy.name,
                        portal_section="policies",
                        priority="High"
                    )

    frappe.db.commit()


def check_new_payslips():
    """
    Hourly scheduler: check for salary slips submitted in the last hour
    and ensure notifications have been sent (failsafe for on_submit misses).
    """
    from frappe.utils import add_to_date
    one_hour_ago = add_to_date(now_datetime(), hours=-1)

    slips = frappe.get_all(
        "Salary Slip",
        filters={"docstatus": 1, "modified": [">=", one_hour_ago]},
        fields=["name", "employee", "posting_date", "net_pay"]
    )

    if not frappe.db.exists("DocType", "ESS Notification Log"):
        return

    for slip in slips:
        already = frappe.db.exists(
            "ESS Notification Log",
            {"employee": slip.employee, "link_name": slip.name,
             "notification_type": "Payroll"}
        )
        if not already:
            _push_notification(
                slip.employee,
                "Payslip Available 💰",
                "Your salary slip for {0} is ready. Net: ₦{1:,.0f}.".format(
                    format_date(slip.posting_date), flt(slip.net_pay)),
                notification_type="Payroll",
                link_name=slip.name,
                portal_section="payroll",
                priority="High"
            )

    if slips:
        frappe.db.commit()