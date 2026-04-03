# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, time_diff_in_seconds


class TelephoneCallLog(Document):

    def before_insert(self):
        if not self.started_at:
            self.started_at = now_datetime()
        self._resolve_caller_name()
        self._resolve_receiver_name()

    def before_save(self):
        self._calculate_duration()
        self._resolve_caller_name()
        self._resolve_receiver_name()

    # ─── Duration Calculation ─────────────────────────────────────────────────

    def _calculate_duration(self):
        if self.answered_at and self.ended_at:
            seconds = int(time_diff_in_seconds(self.ended_at, self.answered_at))
            self.duration = seconds
            self.duration_formatted = self._format_duration(seconds)

    @staticmethod
    def _format_duration(seconds):
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            m, s = divmod(seconds, 60)
            return f"{m}m {s}s"
        else:
            h, remainder = divmod(seconds, 3600)
            m, s = divmod(remainder, 60)
            return f"{h}h {m}m {s}s"

    # ─── Name Resolution ──────────────────────────────────────────────────────

    def _resolve_caller_name(self):
        if self.caller_user and not self.caller_name:
            self.caller_name = frappe.db.get_value(
                "User", self.caller_user, "full_name"
            ) or self.caller_user

    def _resolve_receiver_name(self):
        if self.receiver_name:
            return

        # Try Contact
        if self.contact:
            self.receiver_name = frappe.db.get_value(
                "Contact", self.contact, "full_name"
            )
            return

        # Try Lead
        if self.lead:
            self.receiver_name = frappe.db.get_value(
                "Lead", self.lead, "lead_name"
            )
            return

        # Try Customer
        if self.customer:
            self.receiver_name = self.customer
            return

        # Try Employee
        if self.employee:
            self.receiver_name = frappe.db.get_value(
                "Employee", self.employee, "employee_name"
            )
            return

        # Fallback — use number
        self.receiver_name = self.receiver_number

    # ─── Static Helpers (used by api.py) ─────────────────────────────────────

    @staticmethod
    def update_status(tcl_name, status, ended_at=None):
        doc = frappe.get_doc("Telephone Call Log", tcl_name)
        doc.status = status
        if ended_at:
            doc.ended_at = ended_at
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        return doc

    @staticmethod
    def get_recent_logs(user, limit=20):
        return frappe.get_list(
            "Telephone Call Log",
            filters={"caller_user": user},
            fields=[
                "name", "receiver_number", "receiver_name",
                "direction", "call_type", "status",
                "provider", "started_at", "duration_formatted",
                "lead", "contact", "customer",
            ],
            order_by="started_at desc",
            limit=limit,
        )
