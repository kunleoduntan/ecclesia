# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class WAInternalChat(Document):
    """
    Represents an internal agent-facing chat session with a WhatsApp contact.
    Aggregates all messages for a given phone number into a threaded conversation.
    """

    def validate(self):
        self.validate_phone_number()
        self.set_title()

    def validate_phone_number(self):
        if not self.phone_number:
            frappe.throw(frappe._("Phone Number is required"))

    def set_title(self):
        if self.contact_name:
            self.title = f"{self.contact_name} ({self.phone_number})"
        else:
            self.title = self.phone_number

    def get_messages(self) -> list:
        """Fetch all messages linked to this chat session, ordered by creation."""
        return frappe.get_all(
            "WAMessage",
            filters={"internal_chat": self.name},
            fields=["name", "message_type", "body", "delivery_status", "creation", "direction"],
            order_by="creation asc",
        )

    def close_chat(self, resolved_by: str = None):
        self.db_set("status", "Closed")
        if resolved_by:
            self.db_set("resolved_by", resolved_by)
        self.db_set("resolved_on", frappe.utils.now_datetime())

    def reopen_chat(self):
        self.db_set("status", "Open")
        self.db_set("resolved_by", None)
        self.db_set("resolved_on", None)

    def assign_to_agent(self, agent_user: str):
        if not frappe.db.exists("User", agent_user):
            frappe.throw(frappe._("User '{0}' does not exist").format(agent_user))
        self.db_set("assigned_agent", agent_user)
        frappe.share.add("WAInternalChat", self.name, agent_user, read=1, write=1)