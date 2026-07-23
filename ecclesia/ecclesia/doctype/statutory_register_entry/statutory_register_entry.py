# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/ecclesia/doctype/statutory_register_entry/statutory_register_entry.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate


class StatutoryRegisterEntry(Document):

    def before_insert(self):
        if not self.entry_date:
            self.entry_date = nowdate()

    def validate(self):
        self._validate_shares()
        self._set_cac_form_type()

    def after_insert(self):
        self._update_corporate_register_flag()

    def _validate_shares(self):
        if self.register_type in ("Register of Allotments", "Register of Share Transfers"):
            if not self.shares_allotted:
                frappe.throw(_("Shares Allotted / Transferred is required for share registers."))
            if not self.share_class:
                frappe.msgprint(_("Share class is recommended for allotment entries."), indicator="orange")

    def _set_cac_form_type(self):
        """Auto-suggest the correct CAC form based on register type."""
        form_map = {
            "Register of Directors":         "CAC 7 (Notice of Change of Directors)",
            "Register of Members":           "CAC 2.1 (Return of Allotment)",
            "Register of Allotments":        "CAC 2.1 (Return of Allotment)",
            "Register of Share Transfers":   "CAC 2.1 (Return of Allotment) / Instrument of Transfer",
            "Register of Charges":           "CAC 8C (Notice of Charge)",
            "Register of Secretaries":       "CAC 10 (Notice of Change of Secretary)",
            "Register of Substantial Shareholders": "CAC 14 (Substantial Shareholder Notice)",
        }
        if not self.cac_form_type and self.register_type in form_map:
            self.cac_form_type = form_map[self.register_type]

    def _update_corporate_register_flag(self):
        """When an entry is made, mark the parent register as needing review."""
        if self.corporate_register:
            frappe.db.set_value(
                "Corporate Compliance Register",
                self.corporate_register,
                "statutory_registers_current", 0,
                update_modified=False
            )


@frappe.whitelist()
def get_entries_by_register_type(company, register_type, limit=20):
    """Return entries for a specific statutory register."""
    return frappe.db.get_all(
        "Statutory Register Entry",
        filters={"company": company, "register_type": register_type},
        fields=["name", "entry_date", "entry_description", "party_name",
                "shares_allotted", "cac_form_filed", "cac_filing_reference"],
        order_by="entry_date desc",
        limit=limit
    )
