# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

"""
Service Contract DocType Controller
Manages vendor/supplier contracts with SLA tracking and renewal alerts.
On submit: updates Service Provider active_contracts count.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate, date_diff, add_days


class ServiceContract(Document):

    def before_insert(self):
        if not self.status:
            self.status = "Draft"

    def validate(self):
        self._validate_dates()
        self._compute_days_to_expiry()
        self._set_status_from_expiry()

    def on_submit(self):
        self.db_set("status", "Active")
        self._update_provider_contract_count(1)

    def on_cancel(self):
        self.db_set("status", "Terminated")
        self._update_provider_contract_count(-1)

    # ── Validation ───────────────────────────────────────────────────────────

    def _validate_dates(self):
        if self.start_date and self.end_date:
            if getdate(self.end_date) <= getdate(self.start_date):
                frappe.throw(_("End Date must be after Start Date."))
        if self.renewal_date and self.end_date:
            if getdate(self.renewal_date) > getdate(self.end_date):
                frappe.throw(_("Renewal Due Date cannot be after End Date."))

    def _compute_days_to_expiry(self):
        if self.end_date:
            self.days_to_expiry = date_diff(self.end_date, nowdate())

    def _set_status_from_expiry(self):
        if self.docstatus != 1:
            return
        days = self.days_to_expiry or 0
        remind = self.renewal_reminder_days or 60
        if days < 0:
            self.db_set("status", "Expired")
        elif days <= remind:
            self.db_set("status", "Expiring Soon")

    # ── Side effects ─────────────────────────────────────────────────────────

    def _update_provider_contract_count(self, delta):
        if not self.service_provider:
            return
        provider = frappe.get_doc("Service Provider", self.service_provider)
        provider.update_active_contracts()


@frappe.whitelist()
def renew_contract(contract_name, new_end_date, new_contract_value=None):
    """Create a copy of this contract with a new end date."""
    doc = frappe.get_doc("Service Contract", contract_name)

    new_doc = frappe.copy_doc(doc)
    new_doc.start_date      = frappe.utils.add_days(doc.end_date, 1)
    new_doc.end_date        = new_end_date
    new_doc.status          = "Draft"
    new_doc.renewal_date    = None
    new_doc.amount_paid_to_date = 0
    if new_contract_value:
        new_doc.contract_value = flt(new_contract_value)

    new_doc.insert(ignore_permissions=True)

    # Mark old contract as Renewed
    frappe.db.set_value("Service Contract", contract_name, "status", "Renewed")

    return new_doc.name


@frappe.whitelist()
def get_contracts_expiring_soon(days=60):
    """Called by scheduler or dashboard to list contracts expiring within N days."""
    today = nowdate()
    cutoff = add_days(today, int(days))
    return frappe.db.get_all(
        "Service Contract",
        filters={
            "docstatus": 1,
            "status": ["in", ["Active", "Expiring Soon"]],
            "end_date": ["between", [today, cutoff]],
        },
        fields=["name", "contract_title", "vendor", "end_date", "contract_value", "days_to_expiry"],
        order_by="end_date asc",
    )
