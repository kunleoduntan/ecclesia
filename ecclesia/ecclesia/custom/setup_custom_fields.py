"""
MailVault Custom Fields Setup
Run this once to add required custom fields
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def setup_mailvault_custom_fields():
    """Setup custom fields for MailVault"""
    
    custom_fields = {
        "Communication": [
            {
                "fieldname": "mail_folder",
                "label": "Mail Folder",
                "fieldtype": "Data",
                "insert_after": "status",
                "description": "Custom folder for MailVault (Archive, etc.)",
                "translatable": 0,
                "no_copy": 1
            }
        ],
        "User": [
            {
                "fieldname": "mail_vault_prefs",
                "label": "MailVault Preferences",
                "fieldtype": "Text",
                "insert_after": "bio",
                "description": "JSON preferences for MailVault UI",
                "translatable": 0,
                "no_copy": 1
            }
        ]
    }
    
    create_custom_fields(custom_fields, ignore_validate=True)
    frappe.db.commit()
    print("✅ MailVault custom fields created successfully")

def add_to_hooks():
    """Instructions to add to hooks.py"""
    print("""
    Add this to your ecclesia/hooks.py:
    
    # MailVault Setup
    after_install = "ecclesia.custom.setup_custom_fields.setup_mailvault_custom_fields"
    """)

if __name__ == "__main__":
    setup_mailvault_custom_fields()