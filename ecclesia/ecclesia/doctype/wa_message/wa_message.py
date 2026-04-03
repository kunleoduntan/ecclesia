# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WAMessage(Document):
    """
    Stores every individual WhatsApp message sent or received,
    including metadata, delivery status, and linked documents.
    """

    def validate(self):
        self.validate_phone_number()

    def validate_phone_number(self):
        import re
        pattern = re.compile(r"^\+?[1-9]\d{6,14}$")
        if self.phone_number and not pattern.match(self.phone_number.replace(" ", "")):
            frappe.throw(
                frappe._("Invalid phone number format: {0}")
                .format(self.phone_number)
            )

    def after_insert(self):
        """Link message to an open internal chat session if one exists."""
        chat = frappe.db.get_value(
            "WAInternalChat",
            {"phone_number": self.phone_number, "status": "Open"},
            "name",
        )
        if chat:
            self.db_set("internal_chat", chat)

    def mark_delivered(self):
        self.db_set("delivery_status", "Delivered")

    def mark_read(self):
        self.db_set("delivery_status", "Read")

    def mark_failed(self, error_message: str = None):
        self.db_set("delivery_status", "Failed")
        if error_message:
            self.db_set("error_message", error_message)