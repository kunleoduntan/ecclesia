"""Permissions — role-based access control for audit documents."""

import frappe


def has_permission(doc, ptype="read", user=None):
    user = user or frappe.session.user
    roles = frappe.get_roles(user)

    if "Audit Manager" in roles or "System Manager" in roles:
        return True

    if ptype == "read" and "Senior Auditor" in roles:
        return True

    if ptype == "read" and "Auditor" in roles:
        return True

    if ptype in ("read", "write") and "Auditee" in roles:
        # Auditees can only see findings assigned to them
        if doc.doctype == "Audit Finding":
            return doc.action_owner == user
        return True

    return False
