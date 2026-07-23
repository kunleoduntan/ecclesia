# permissions.py
def policy_query_condition(user):
    if frappe.user.has_role(["HR Manager", "System Manager"]):
        return ""   # No restriction
    # Department Managers see published policies for their department
    dept = frappe.db.get_value("Employee", {"user_id": user}, "department")
    if dept:
        return f"""(
            `tabCompany Policy`.applicable_to = 'All Employees'
            OR EXISTS (
                SELECT 1 FROM `tabPolicy Scope` ps
                WHERE ps.parent = `tabCompany Policy`.name
                AND ps.scope_type = 'Department'
                AND ps.scope_value = {frappe.db.escape(dept)}
            )
        )"""
    return "1=0"
    


"""
ecclesia_erequest/utils/permissions.py
─────────────────────────────────────────────────────────────────────────────
Custom permission logic for eRequest.
Employees can only see their own requests; managers/finance/admin see all.
"""
import frappe


def has_permission(doc, ptype="read", user=None):
    user = user or frappe.session.user
    if user == "Administrator":
        return True

    roles = frappe.get_roles(user)

    # Admins / Finance / Managers see everything
    if any(r in roles for r in ("eRequest Admin", "eRequest Finance",
                                "eRequest Manager", "System Manager")):
        return True

    # Employees only see their own
    if "eRequest Employee" in roles:
        # Match on the user email stored in requested_by
        return doc.requested_by == user

    return False


"""
Ecclesia – Permission Helpers  (ecclesia/ecclesia/permissions.py)
Row-level security for all WFH/WFO DocTypes.

Work Session: uses 'user' field (not 'employee') since non-employee users
can have sessions. Employees see their own session; managers see team sessions.

External Task: uses 'user' field directly.
"""

import frappe


# ─────────────────────────────────────────────────────────────
# SAFE ROLE CHECK HELPERS
# ─────────────────────────────────────────────────────────────

def _has_role(roles):
    """
    Safe role checker that works even when frappe.session is not fully initialized.
    """
    try:
        return frappe.has_role(roles)
    except Exception:
        return False


def _is_hr():
    return _has_role(["HR Manager", "System Manager"])


def _is_manager():
    return _has_role(["Line Manager"])


# ─────────────────────────────────────────────────────────────
# EMPLOYEE HELPERS
# ─────────────────────────────────────────────────────────────

def _get_employee(user=None):
    user = user or frappe.session.user
    return frappe.db.get_value(
        "Employee",
        {"user_id": user, "status": "Active"},
        "name"
    )


def _get_reportees(manager_emp):
    return frappe.db.get_all(
        "Employee",
        filters={"reports_to": manager_emp, "status": "Active"},
        pluck="name"
    )


# ─────────────────────────────────────────────────────────────
# EMPLOYEE-BASED DOCTYPES
# (WFH Request, WFH Session, Activity Log, Summary)
# ─────────────────────────────────────────────────────────────

def get_employee_permission_query(user=None):
    user = user or frappe.session.user

    if _is_hr():
        return ""

    emp = _get_employee(user)
    if not emp:
        return "1=0"

    if _is_manager():
        visible = [emp] + _get_reportees(emp)
        quoted = ", ".join(frappe.db.escape(e) for e in visible)
        return f"`tabWFH Request`.employee IN ({quoted})"

    return f"`tabWFH Request`.employee = {frappe.db.escape(emp)}"


def has_permission(doc, user=None, permission_type="read"):
    user = user or frappe.session.user

    if _is_hr():
        return True

    emp = _get_employee(user)
    if not emp:
        return False

    doc_emp = getattr(doc, "employee", None)

    if doc_emp == emp:
        return True

    if _is_manager() and doc_emp in _get_reportees(emp):
        return True

    return False


# ─────────────────────────────────────────────────────────────
# WORK SESSION (USER-BASED)
# ─────────────────────────────────────────────────────────────

def get_work_session_permission_query(user=None):
    user = user or frappe.session.user

    if _is_hr():
        return ""

    if _is_manager():
        emp = _get_employee(user)
        if emp:
            reportee_users = []

            for r_emp in _get_reportees(emp):
                u = frappe.db.get_value("Employee", r_emp, "user_id")
                if u:
                    reportee_users.append(u)

            visible = [user] + reportee_users
            quoted = ", ".join(frappe.db.escape(u) for u in visible)
            return f"`tabWork Session`.user IN ({quoted})"

    return f"`tabWork Session`.user = {frappe.db.escape(user)}"


def has_work_session_permission(doc, user=None, permission_type="read"):
    user = user or frappe.session.user

    if _is_hr():
        return True

    if getattr(doc, "user", None) == user:
        return True

    if _is_manager():
        emp = _get_employee(user)
        if emp:
            reportee_users = []

            for r_emp in _get_reportees(emp):
                u = frappe.db.get_value("Employee", r_emp, "user_id")
                if u:
                    reportee_users.append(u)

            if doc.user in reportee_users:
                return True

    return False


# ─────────────────────────────────────────────────────────────
# EXTERNAL TASK (USER-BASED)
# ─────────────────────────────────────────────────────────────

def get_user_permission_query(user=None):
    user = user or frappe.session.user

    if _is_hr():
        return ""

    if _is_manager():
        emp = _get_employee(user)
        if emp:
            reportee_users = [user]

            for r_emp in _get_reportees(emp):
                u = frappe.db.get_value("Employee", r_emp, "user_id")
                if u:
                    reportee_users.append(u)

            quoted = ", ".join(frappe.db.escape(u) for u in reportee_users)
            return f"`tabExternal Task`.user IN ({quoted})"

    return f"`tabExternal Task`.user = {frappe.db.escape(user)}"


def has_user_permission(doc, user=None, permission_type="read"):
    user = user or frappe.session.user

    if _is_hr():
        return True

    if getattr(doc, "user", None) == user:
        return True

    if _is_manager():
        emp = _get_employee(user)
        if emp:
            for r_emp in _get_reportees(emp):
                u = frappe.db.get_value("Employee", r_emp, "user_id")
                if u == doc.user:
                    return True

    return False