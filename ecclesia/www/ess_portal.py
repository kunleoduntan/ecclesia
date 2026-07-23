"""
ecclesia/ecclesia/www/ess-portal.py
====================================
Frappe www controller — serves the ESS web portal at /ess-portal

Frappe auto-discovers every file in the module's www/ folder:
    ecclesia/ecclesia/www/ess-portal.py  →  URL: /ess-portal

get_context() runs server-side before ess-portal.html is rendered.
It injects window.ESS_BOOT so the SPA can start without a round-trip.
All live data is loaded client-side via /api/method/ecclesia.api.ess_portal.*
"""
import frappe
from frappe import _
from frappe.utils import nowdate

# ── Frappe www page directives ──────────────────────────────────────────────
no_cache       = 1      # never serve a stale cached version
login_required = True   # redirect anonymous visitors to /login


def _safe_str(val):
    """Convert date/datetime/time objects to ISO strings; leave everything else."""
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return val


def get_context(context):
    """
    Called by Frappe before rendering ess-portal.html.
    Injects employee data and CSRF token into the Jinja context.
    """
    user = frappe.session.user

    # Reject guest / unauthenticated users (belt-and-suspenders with login_required)
    if not user or user == "Guest":
        frappe.throw(
            _("Please log in to access the Employee Self-Service Portal."),
            frappe.PermissionError,
        )

    # Resolve employee from the logged-in Frappe user
    employee = frappe.db.get_value(
        "Employee",
        {"user_id": user, "status": "Active"},
        ["name", "employee_name", "designation", "department",
         "branch", "company", "date_of_joining", "employment_type",
         "reports_to"],
        as_dict=True,
    )

    if not employee:
        frappe.throw(
            _("No active Employee record is linked to your user account. "
              "Please contact HR to link your user ID."),
            frappe.PermissionError,
        )

    # ── Fix: convert every date/datetime field to string ────────────────────
    # frappe.db.get_value returns Python date objects for Date fields.
    # Jinja's tojson filter uses stdlib json which can't encode date/datetime.
    # Stringify every value that has .isoformat() (date, datetime, time).
    employee_dict = {}
    for key, val in employee.items():
        employee_dict[key] = _safe_str(val)

    # Pending badge counts for sidebar
    pending_leave = frappe.db.count(
        "Leave Application",
        {"employee": employee_dict["name"], "status": "Open"},
    )
    pending_tasks = (
        frappe.db.count(
            "ESS Task",
            {"assigned_to": employee_dict["name"],
             "status": ["not in", ["Completed", "Cancelled"]]},
        )
        if frappe.db.exists("DocType", "ESS Task")
        else 0
    )

    unread_notifs = 0
    if frappe.db.exists("DocType", "ESS Notification Log"):
        unread_notifs = frappe.db.count(
            "ESS Notification Log",
            {"employee": employee_dict["name"], "is_read": 0},
        )

    # Latest pulse score — all numeric, safe for JSON
    pulse = {}
    if frappe.db.exists("DocType", "ESS Pulse Score"):
        row = frappe.db.get_value(
            "ESS Pulse Score",
            {"employee": employee_dict["name"]},
            ["overall_pulse_score", "attendance_score",
             "task_score", "leave_health_score", "performance_score"],
            order_by="period_end desc",
            as_dict=True,
        )
        if row:
            pulse = {
                "overall_pulse_score": float(row.overall_pulse_score or 0),
                "attendance_score":    float(row.attendance_score or 0),
                "task_score":          float(row.task_score or 0),
                "leave_health_score":  float(row.leave_health_score or 0),
                "performance_score":   float(row.performance_score or 0),
            }

    # Avatar initials
    parts = (employee_dict.get("employee_name") or "").split()
    if len(parts) >= 2:
        initials = (parts[0][0] + parts[-1][0]).upper()
    elif parts:
        initials = parts[0][:2].upper()
    else:
        initials = "ME"

    # CSRF token — works across Frappe v14 and v15
    try:
        csrf_token = frappe.sessions.get_csrf_token()
    except Exception:
        csrf_token = frappe.local.session.get("csrf_token", "")

    # ── Inject into Jinja context ────────────────────────────────────────────
    context.no_cache      = 1
    context.title         = "MyWork · Employee Self-Service"
    context.employee      = employee_dict   # plain dict, all values JSON-safe
    context.initials      = initials
    context.pending_leave = pending_leave
    context.pending_tasks = pending_tasks
    context.unread_notifs = unread_notifs
    context.pulse         = pulse
    context.today         = nowdate()       # frappe.utils.nowdate() → plain string
    context.csrf_token    = csrf_token