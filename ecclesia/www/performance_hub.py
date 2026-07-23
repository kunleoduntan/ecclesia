"""
ecclesia/www/performance_hub.py
================================
Frappe www controller for the 360 Performance Hub.
Place at: ecclesia/ecclesia/www/performance_hub.py
URL served: /performance-hub

The companion HTML file performance_hub.html goes in the same www/ folder.
"""
import frappe
from frappe import _
from frappe.utils import nowdate

no_cache = 1
login_required = True


def _safe(val):
    return val.isoformat() if hasattr(val, "isoformat") else val


def get_context(context):
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Please log in to access the Performance Hub."),
                     frappe.PermissionError)

    employee = frappe.db.get_value(
        "Employee",
        {"user_id": user, "status": "Active"},
        ["name", "employee_name", "designation", "department",
         "branch", "company", "reports_to"],
        as_dict=True,
    )
    if not employee:
        frappe.throw(_("No active Employee linked to your account."),
                     frappe.PermissionError)

    employee = {k: _safe(v) for k, v in employee.items()}

    # Active cycle
    cycle = frappe.db.get_value(
        "Performance Cycle", {"status": "Active"},
        ["name", "title", "end_date"], as_dict=True
    )
    if cycle:
        cycle = {k: _safe(v) for k, v in cycle.items()}

    # Roles
    roles = frappe.get_roles(user)
    is_manager = "Line Manager" in roles or "HR Manager" in roles
    is_hr = "HR Manager" in roles or "System Manager" in roles

    try:
        csrf_token = frappe.sessions.get_csrf_token()
    except Exception:
        csrf_token = frappe.local.session.get("csrf_token", "")

    context.no_cache = 1
    context.title = "Performance Hub - 360°"
    context.employee = employee
    context.cycle = cycle or {}
    context.today = nowdate()
    context.is_manager = is_manager
    context.is_hr = is_hr
    context.csrf_token = csrf_token