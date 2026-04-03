# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

"""
ecclesia/doctype/wa_settings/wa_settings.py
WA Settings DocType controller.
"""

import frappe
from frappe.model.document import Document
from ecclesia.utils.helpers import clear_settings_cache


class WASettings(Document):

    def on_update(self):
        clear_settings_cache()
        frappe.cache().delete_key("wa_settings_boot")

    def validate(self):
        if self.wa_enabled and not self.wa_phone_number_id:
            frappe.throw("Phone Number ID is required when WhatsApp is enabled.")
        if self.wa_enabled and not self.get_password("wa_access_token"):
            frappe.throw("Access Token is required when WhatsApp is enabled.")


@frappe.whitelist()
def test_connection(test_number: str, test_message: str) -> dict:
    """Send a test WhatsApp message from the settings page."""
    from ecclesia.api.whatsapp import send_text
    result = send_text(test_number, test_message)
    if result.get("status") == "sent":
        return {"success": True, "message": f"Test message sent to {test_number}"}
    return {"success": False, "message": result.get("error_message", "Failed")}
