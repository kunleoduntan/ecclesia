# FILE: apps/ecclesia/ecclesia/api/portal_custom_fields.py
# Adds ec_portal_user field to Customer and Supplier doctypes.
# Run once: bench execute ecclesia.api.portal_custom_fields.install
import frappe


FIELDS = [
    {
        "dt": "Customer",
        "fieldname": "ec_portal_user",
        "fieldtype": "Data",
        "label": "Portal User (Email)",
        "insert_after": "customer_name",
        "description": "Enter the login email of the user who should access this customer's portal",
        "unique": 0,
        "in_list_view": 1,
    },
    {
        "dt": "Supplier",
        "fieldname": "ec_portal_user",
        "fieldtype": "Data",
        "label": "Portal User (Email)",
        "insert_after": "supplier_name",
        "description": "Enter the login email of the user who should access this supplier's portal",
        "unique": 0,
        "in_list_view": 1,
    },
]


@frappe.whitelist()
def install():
    results = []

    for f in FIELDS:
        # Check if the field already exists on the doctype
        exists = frappe.db.exists(
            "Custom Field",
            {
                "dt": f["dt"],
                "fieldname": f["fieldname"]
            }
        )

        if exists:
            results.append(f"✓ Already exists: {f['dt']}.{f['fieldname']}")
            continue

        cf = frappe.get_doc({
            "doctype": "Custom Field",
            "dt": f["dt"],
            "module": "Ecclesia",
            "fieldname": f["fieldname"],
            "fieldtype": f["fieldtype"],
            "label": f["label"],
            "insert_after": f["insert_after"],
            "description": f.get("description", ""),
            "in_list_view": f.get("in_list_view", 0),
            "unique": f.get("unique", 0),
        })

        cf.insert(ignore_permissions=True)
        results.append(f"✅ Created: {f['dt']}.{f['fieldname']}")

    frappe.db.commit()

    for r in results:
        print(r)

    return results