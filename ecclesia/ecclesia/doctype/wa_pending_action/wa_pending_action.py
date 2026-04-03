# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document

class WAPendingAction(Document):
    """
    Tracks pending WhatsApp actions such as scheduled messages,
    retries, and queued notifications waiting for processing.
    """

    def validate(self):
        self.validate_scheduled_time()

    def validate_scheduled_time(self):
        from frappe.utils import now_datetime
        if self.scheduled_at and self.scheduled_at < now_datetime():
            frappe.throw(frappe._("Scheduled time cannot be in the past"))

    def on_submit(self):
        self.status = "Queued"
        frappe.enqueue(
            "frappe_whatsapp.utils.process_pending_action",
            doc_name=self.name,
            queue="short",
        )

    def mark_as_failed(self, reason: str):
        self.db_set("status", "Failed")
        self.db_set("failure_reason", reason)
        frappe.log_error(title="WAPendingAction Failed", message=reason)