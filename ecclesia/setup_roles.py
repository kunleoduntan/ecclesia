import frappe


ECCLESIA_ROLES = [
    {
        "role_name": "Policy Author",
        "desk_access": 1,
        "description": "Can create and edit Company Policy drafts"
    },
    {
        "role_name": "HR Manager",
        "desk_access": 1,
        "description": "Full access to HR and Policy management"
    },
    {
        "role_name": "HR User",
        "desk_access": 1,
        "description": "Read and report access to HR documents"
    },
    {
        "role_name": "Department Manager",
        "desk_access": 1,
        "description": "Read access to policies scoped to their department"
    },
]


def create_roles_if_not_exist():
    """
    Idempotent role bootstrap for the Ecclesia module.
    Safe to call on every bench migrate — skips roles that already exist.
    """
    for role_def in ECCLESIA_ROLES:
        role_name = role_def["role_name"]

        if frappe.db.exists("Role", role_name):
            continue

        role = frappe.get_doc({
            "doctype":     "Role",
            "role_name":   role_name,
            "desk_access": role_def.get("desk_access", 1),
            "description": role_def.get("description", ""),
        })
        role.insert(ignore_permissions=True)
        frappe.logger().info(f"[Ecclesia] Role created: {role_name}")

    frappe.db.commit()