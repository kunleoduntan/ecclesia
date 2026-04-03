# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class PolicyAcknowledgement(Document):

    def validate(self):
        if self.status == "Acknowledged" and not self.acknowledged_on:
            self.acknowledged_on = now_datetime()
            self.ip_address = frappe.local.request_ip if frappe.local.request else None

    def on_update(self):
        if self.status == "Acknowledged":
            self._check_all_acknowledged()

    def _check_all_acknowledged(self):
        pending = frappe.db.count("Policy Acknowledgement", {
            "policy":          self.policy,
            "policy_version":  self.policy_version,
            "status":          "Pending"
        })
        if pending == 0:
            frappe.db.set_value("Company Policy", self.policy,
                                "acknowledgement_status", "Fully Acknowledged")


@frappe.whitelist()
def acknowledge_policy(policy, employee, remarks=""):
    """Whitelisted — called from portal page or Employee self-service."""
    ack = frappe.db.get_value(
        "Policy Acknowledgement",
        {"policy": policy, "employee": employee, "status": "Pending"},
        "name"
    )
    if not ack:
        frappe.throw("No pending acknowledgement found for this policy and employee.")

    doc = frappe.get_doc("Policy Acknowledgement", ack)
    doc.status          = "Acknowledged"
    doc.acknowledged_on = now_datetime()
    doc.remarks         = remarks
    doc.ip_address      = frappe.local.request_ip if frappe.local.request else None
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": "Acknowledged successfully."}