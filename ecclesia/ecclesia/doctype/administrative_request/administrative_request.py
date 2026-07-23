# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

"""
Administrative Request DocType Controller
Central intake form for all admin department requests.
Workflow: Draft → Submitted → Approved → In Progress → Completed → Closed
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate, date_diff


SLA_DAYS = {
    "Urgent":  1,
    "High":    3,
    "Medium":  7,
    "Low":     14,
}


class AdministrativeRequest(Document):

    def before_insert(self):
        if not self.request_date:
            self.request_date = nowdate()
        if not self.status:
            self.status = "Draft"

    def validate(self):
        self._validate_dates()
        self._compute_age()

    def on_submit(self):
        self.db_set("status", "Submitted")
        self._notify_admin_department()

    def on_cancel(self):
        self.db_set("status", "Cancelled")

    # ── Validation helpers ───────────────────────────────────────────────────

    def _validate_dates(self):
        if self.required_by_date and self.request_date:
            if getdate(self.required_by_date) < getdate(self.request_date):
                frappe.throw(
                    _("Required By date cannot be before Request Date.")
                )

    def _compute_age(self):
        if self.request_date:
            self.request_age_days = date_diff(nowdate(), self.request_date)

        if self.actual_completion_date and self.request_date:
            self.completion_days = date_diff(
                self.actual_completion_date, self.request_date
            )

        # SLA breach check
        sla = SLA_DAYS.get(self.priority or "Medium", 7)
        if self.request_age_days and self.status not in ("Completed", "Closed", "Rejected"):
            self.sla_breached = 1 if self.request_age_days > sla else 0

    def _notify_admin_department(self):
        """Send email notification to assigned admin staff or admin role."""
        recipients = []
        if self.assigned_to_employee:
            email = frappe.db.get_value("Employee", self.assigned_to_employee, "company_email")
            if email:
                recipients.append(email)

        if not recipients:
            return  # silent if no one to notify

        frappe.sendmail(
            recipients=recipients,
            subject=_("New Admin Request: {0} — {1}").format(
                self.name, self.request_title
            ),
            message=_(
                "A new administrative request has been submitted.<br>"
                "<b>Type:</b> {0}<br><b>Priority:</b> {1}<br>"
                "<b>Required By:</b> {2}<br><b>Description:</b> {3}"
            ).format(
                self.request_type, self.priority,
                self.required_by_date or "Not specified",
                self.description or ""
            ),
        )


@frappe.whitelist()
def approve_request(request_name, approved_cost=None):
    """Approve the request and optionally set approved cost."""
    doc = frappe.get_doc("Administrative Request", request_name)
    if doc.status != "Submitted":
        frappe.throw(_("Only Submitted requests can be approved."))

    doc.db_set("status", "Approved")
    doc.db_set("approved_by", frappe.session.user)
    doc.db_set("approval_date", nowdate())
    if approved_cost is not None:
        doc.db_set("approved_cost", flt(approved_cost))

    frappe.msgprint(
        _("Request {0} approved.").format(request_name),
        indicator="green"
    )
    return "Approved"


@frappe.whitelist()
def reject_request(request_name, rejection_reason):
    """Reject the request with a reason."""
    doc = frappe.get_doc("Administrative Request", request_name)
    if doc.status not in ("Submitted", "Approved"):
        frappe.throw(_("Only Submitted or Approved requests can be rejected."))
    doc.db_set("status", "Rejected")
    doc.db_set("rejection_reason", rejection_reason)
    return "Rejected"


@frappe.whitelist()
def mark_in_progress(request_name):
    doc = frappe.get_doc("Administrative Request", request_name)
    if doc.status != "Approved":
        frappe.throw(_("Only Approved requests can be moved to In Progress."))
    doc.db_set("status", "In Progress")
    return "In Progress"


@frappe.whitelist()
def complete_request(request_name, actual_cost=None):
    doc = frappe.get_doc("Administrative Request", request_name)
    if doc.status != "In Progress":
        frappe.throw(_("Only In Progress requests can be completed."))
    doc.db_set("status", "Completed")
    doc.db_set("actual_completion_date", nowdate())
    if actual_cost is not None:
        doc.db_set("actual_cost", flt(actual_cost))
    return "Completed"
