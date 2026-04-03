# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

"""
Corrective Action Plan Controller
===================================
Tracks management's remediation commitments to audit findings.
Sends reminders and triggers re-audit when due.
"""

import frappe
from frappe.model.document import Document
from frappe.utils import today, getdate, date_diff


class CorrectiveActionPlan(Document):

    def before_save(self):
        """Sync risk rating from linked finding."""
        if self.audit_finding and not self.risk_rating:
            self.risk_rating = frappe.db.get_value(
                "Audit Finding", self.audit_finding, "risk_rating"
            )

    def validate(self):
        self._check_overdue()
        self._update_milestones_status()

    def on_submit(self):
        """Notify action owner."""
        self._notify_action_owner()

    def _check_overdue(self):
        if self.due_date and self.status not in ("Completed", "Accepted Risk"):
            if getdate(self.due_date) < getdate(today()):
                self.status = "Overdue"

    def _update_milestones_status(self):
        if not self.milestones:
            return
        for milestone in self.milestones:
            if milestone.status not in ("Completed",):
                if milestone.due_date and getdate(milestone.due_date) < getdate(today()):
                    milestone.status = "Overdue"

    def on_update(self):
        """When CAP is completed, update the linked finding status."""
        if self.status == "Completed" and self.audit_finding:
            frappe.db.set_value(
                "Audit Finding",
                self.audit_finding,
                "status",
                "Closed - Resolved"
            )

    def _notify_action_owner(self):
        if not self.action_owner:
            return
        try:
            owner_email = frappe.db.get_value("User", self.action_owner, "email")
            finding_title = frappe.db.get_value(
                "Audit Finding", self.audit_finding, "finding_title"
            ) if self.audit_finding else ""

            frappe.sendmail(
                recipients=[owner_email],
                subject=f"[CAP Assigned] {self.cap_title}",
                message=f"""
                    <p>Dear {self.action_owner},</p>
                    <p>A Corrective Action Plan has been assigned to you.</p>
                    <table border="1" cellpadding="5">
                        <tr><td><b>CAP</b></td><td>{self.cap_title}</td></tr>
                        <tr><td><b>Finding</b></td><td>{finding_title}</td></tr>
                        <tr><td><b>Risk Rating</b></td><td>{self.risk_rating}</td></tr>
                        <tr><td><b>Due Date</b></td><td>{self.due_date}</td></tr>
                    </table>
                    <p><b>Action Plan:</b><br>{self.action_plan or ''}</p>
                    <p>Please log in to update progress and upload evidence of completion.</p>
                """,
                now=False
            )
        except Exception:
            pass
