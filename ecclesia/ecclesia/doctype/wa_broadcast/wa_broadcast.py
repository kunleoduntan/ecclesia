# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

"""
ecclesia/doctype/wa_broadcast/wa_broadcast.py
"""

import frappe
from frappe.model.document import Document


class WABroadcast(Document):

    def validate(self):
        if self.recipient_source == "Manual List" and not self.recipients:
            frappe.throw("Add at least one recipient.")
        if not self.wa_template and not self.custom_message:
            frappe.throw("Provide a WhatsApp Template or Custom Message.")

    def on_submit(self):
        if not self.scheduled_at:
            # Send immediately
            frappe.enqueue(
                "ecclesia.api.broadcast.run_broadcast",
                queue="long",
                broadcast_name=self.name
            )
        else:
            frappe.db.set_value("WA Broadcast", self.name, "status", "Scheduled")
