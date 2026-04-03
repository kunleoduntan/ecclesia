# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

"""
Audit Scope DocType — Child Table Controller
=============================================
Each row represents one DocType in an Audit Engagement's scope.
On validate, auto-populates transaction code, risk level, and
sampling method from the Auditable DocType Registry.

Also guards against scoping an unregistered DocType.
"""

import frappe
from frappe.model.document import Document


class AuditScopeDoctype(Document):

    def validate(self):
        if not self.doctype_name:
            return

        reg = frappe.db.get_value(
            "Auditable DocType Registry",
            {"doctype_name": self.doctype_name},
            [
                "transaction_code", "risk_level", "sampling_method",
                "is_gl_posting", "is_active", "recommended_sample_size",
                "audit_frequency",
            ],
            as_dict=True,
        )

        if not reg:
            frappe.throw(
                f"<b>{self.doctype_name}</b> is not registered in the Audit Universe. "
                "Register it via <b>Auditable DocType Registry</b> before adding it "
                "to an engagement scope.",
                title="DocType Not Registered",
            )

        if not reg.is_active:
            frappe.msgprint(
                f"⚠️ <b>{self.doctype_name}</b> is registered but currently marked "
                "<b>Inactive</b>. Consider reactivating it in the registry.",
                indicator="orange",
                alert=True,
            )

        # Auto-fill from registry (never overwrite manual edits)
        if not self.transaction_code:
            self.transaction_code = reg.transaction_code
        if not self.risk_level:
            self.risk_level = reg.risk_level
        if not self.sampling_method:
            self.sampling_method = reg.sampling_method