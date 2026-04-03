# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

"""
Mail Vault Label — DocType Controller
ecclesia/doctype/mail_vault_label/mail_vault_label.py
"""
import frappe
from frappe.model.document import Document


class MailVaultLabel(Document):

    def validate(self):
        self.label_name = self.label_name.strip()
        # Enforce uniqueness per user
        existing = frappe.db.exists(
            "Mail Vault Label",
            {
                "label_name": self.label_name,
                "owner": frappe.session.user,
                "name": ["!=", self.name],
            },
        )
        if existing:
            frappe.throw(
                frappe._("Label '{0}' already exists for your account").format(
                    self.label_name
                )
            )
