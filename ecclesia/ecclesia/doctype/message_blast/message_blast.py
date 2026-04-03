# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt



import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, get_datetime


class MessageBlast(Document):

    def validate(self):
        self._deduplicate_recipients()
        self._update_counts()
        self._validate_content()

    def before_submit(self):
        if not self.recipients:
            frappe.throw("Cannot submit a Message Blast with no recipients.")
        if self.schedule and self.schedule_time:
            if get_datetime(self.schedule_time) < now_datetime():
                frappe.throw("Schedule time cannot be in the past.")

    def on_submit(self):
        if self.schedule and self.schedule_time:
            self.db_set("status", "Scheduled")

    # ─────────────────────────────────────────────────────────────────────
    # INTERNAL
    # ─────────────────────────────────────────────────────────────────────

    def _validate_content(self):
        mt = self.message_type or ""
        if "Email" in mt:
            has_body = (self.option == "HTML" and self.message_tx_html) or \
                       (self.option == "Text"  and self.message_body)
            if not has_body:
                frappe.msgprint(
                    "Warning: Email channel selected but no email body was provided.",
                    alert=True
                )
        if "WhatsApp" in mt and not self.whatsapp_message_body:
            frappe.msgprint(
                "Warning: WhatsApp channel selected but no WhatsApp message provided.",
                alert=True
            )
        if "SMS" in mt and not self.sms_message_body:
            frappe.msgprint(
                "Warning: SMS channel selected but no SMS message provided.",
                alert=True
            )

    def _deduplicate_recipients(self):
        seen, unique = set(), []
        for row in self.recipients:
            key = (row.email or "").lower().strip() \
                  or (row.mobile_phone or "").strip() \
                  or (row.full_name or "").strip()
            if key and key not in seen:
                seen.add(key)
                unique.append(row)
        self.recipients = unique

    def _update_counts(self):
        self.total_recipients = len(self.recipients)
        self.sent_count       = sum(1 for r in self.recipients if r.delivery_status == "Sent")
        self.failed_count     = sum(1 for r in self.recipients if r.delivery_status == "Failed")
        self.pending_count    = sum(1 for r in self.recipients if r.delivery_status == "Pending")