import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def auto_add_to_documents(doc, method):
    """Automatically add new accounting dimension fields to Receipts and Payments doctypes when an Accounting Dimension is created"""

    target_doctypes = [
        {
            "main": "Payments",
            "children": ["Payments Item Line", "Related Company Payments", "Schedule of Prepayments"],
            "insert_after_main": "project_name",
            "insert_after_child": "project"
        },
        {
            "main": "Receipts",
            "children": ["Receipts Item Line", "Related Company Receipts", "Schedule of Deferred Revenue"],
            "insert_after_main": "project_name",
            "insert_after_child": "project"
        }
    ]

    for target in target_doctypes:
        # Check if field already exists on the main doctype
        existing_field = frappe.db.exists('Custom Field', {
            'dt': target["main"],
            'fieldname': doc.fieldname
        })

        if not existing_field:
            custom_fields = {
                target["main"]: [
                    {
                        "fieldname": doc.fieldname,
                        "label": doc.label,
                        "fieldtype": "Link",
                        "options": doc.document_type,
                        "insert_after": target["insert_after_main"],
                        "in_list_view": 1 if doc.get('in_list_view') else 0,
                        "in_standard_filter": 1 if doc.get('in_standard_filter') else 0
                    }
                ]
            }

            # Add to child doctypes too
            for child in target["children"]:
                custom_fields[child] = [
                    {
                        "fieldname": doc.fieldname,
                        "label": doc.label,
                        "fieldtype": "Link",
                        "options": doc.document_type,
                        "insert_after": target["insert_after_child"]
                    }
                ]

            create_custom_fields(custom_fields, update=True)

            frappe.msgprint(
                f"✅ Accounting Dimension '{doc.label}' added to {target['main']} and related tables"
            )
