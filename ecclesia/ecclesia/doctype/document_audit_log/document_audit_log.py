# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

import frappe

class DocumentAuditLog(frappe.model.document.Document):

    def on_trash(self):
        # Log the attempt first, then block it
        try:
            doc = frappe.new_doc("System Integrity Log")
            doc.update({
                "event": "TAMPER_ATTEMPT",
                "detail": f"User {frappe.session.user} attempted manual deletion of audit log {self.name}",
                "performed_by": frappe.session.user,
                "ip_address": getattr(frappe.local, "request_ip", ""),
                "timestamp": frappe.utils.now_datetime(),
            })
            doc.db_insert()
        except Exception:
            pass
        frappe.throw(
            "Audit logs cannot be manually deleted. "
            "This attempt has been recorded in the System Integrity Log.",
            frappe.PermissionError
        )

    def before_save(self):
        if not self.is_new():
            frappe.throw("Audit logs are immutable.", frappe.PermissionError)