# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

"""
ecclesia/doctype/wa_conversation/wa_conversation.py
"""

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class WAConversation(Document):

    def before_insert(self):
        self._try_link_contact()

    def after_insert(self):
        # Publish to inbox watchers
        frappe.publish_realtime("wa_new_conversation", self.as_dict(), after_commit=True)

    def on_update(self):
        frappe.publish_realtime("wa_conversation_updated", {
            "name":   self.name,
            "status": self.status,
            "unread_count": self.unread_count
        }, after_commit=True)

    def _try_link_contact(self):
        """Auto-link to Contact, Customer, or Lead by phone number."""
        if self.contact or self.customer or self.supplier or self.lead:
            return

        phone = self.phone_number

        # Check Contact
        contact = frappe.db.get_value(
            "Contact Phone",
            {"phone": phone},
            "parent"
        )
        if contact:
            self.contact = contact
            links = frappe.get_all(
                "Dynamic Link",
                filters={"parenttype": "Contact", "parent": contact, "link_doctype": "Customer"},
                fields=["link_name"]
            )
            if links:
                self.customer = links[0].link_name
            return

        # Check Customer mobile
        customer = frappe.db.get_value("Customer", {"mobile_no": phone}, "name")
        if customer:
            self.customer = customer
            return

        # Check Lead
        lead = frappe.db.get_value("Lead", {"mobile_no": phone}, "name")
        if lead:
            self.lead = lead
