# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

"""
Audit Sample Controller
========================
Manages individual sample records within an audit engagement.
"""

import frappe
from frappe.model.document import Document


class AuditSample(Document):

    def before_save(self):
        """Auto-populate transaction code if missing."""
        if self.reference_doctype and not self.transaction_code:
            code = frappe.db.get_value(
                "Auditable DocType Registry",
                {"doctype_name": self.reference_doctype},
                "transaction_code"
            )
            if code:
                self.transaction_code = code

    def on_update(self):
        """When a finding is raised from a sample, update sample status."""
        if self.audit_finding and self.status == "In Review":
            frappe.db.set_value("Audit Sample", self.name, "status", "Finding Raised")
