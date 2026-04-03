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
