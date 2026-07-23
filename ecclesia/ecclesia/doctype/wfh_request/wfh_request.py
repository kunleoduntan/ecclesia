"""
WFH Request Controller
Ecclesia Module – ERPNext

Uses custom get_date_range() because frappe.utils.date_range
does not exist in ERPNext v14/v15.
All import paths use ecclesia.ecclesia.* convention.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, now_datetime
from datetime import timedelta


def get_date_range(start_date, end_date):
    """Generate list of dates between start_date and end_date inclusive."""
    start = getdate(start_date)
    end   = getdate(end_date)
    dates, current = [], start
    while current <= end:
        dates.append(current)
        current += timedelta(days=1)
    return dates


class WFHRequest(Document):

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def before_save(self):
        self._set_total_days()
        self._set_approver()

    def validate(self):
        self._validate_dates()
        self._check_overlap()
        self._validate_future_dates()

    def on_submit(self):
        pass  # Approval handled via workflow actions below

    def on_cancel(self):
        self._cancel_attendance()
        self._cancel_sessions()

    # ── Workflow Actions ───────────────────────────────────────────────────────

    @frappe.whitelist()
    def approve(self):
        if self.status not in ("Pending Approval", "Draft"):
            frappe.throw(_("Only Pending / Draft requests can be approved."))
        self.status     = "Approved"
        self.approved_on = now_datetime()
        self.save(ignore_permissions=True)
        self._create_attendance()
        self._notify_employee("approved")
        frappe.msgprint(_("WFH Request approved and attendance records created."), alert=True)

    @frappe.whitelist()
    def reject(self, reason=""):
        if self.status not in ("Pending Approval", "Draft"):
            frappe.throw(_("Only Pending / Draft requests can be rejected."))
        self.status          = "Rejected"
        self.approved_on     = now_datetime()
        self.rejection_reason = reason
        self.save(ignore_permissions=True)
        self._notify_employee("rejected")

    @frappe.whitelist()
    def request_approval(self):
        self.status = "Pending Approval"
        self.save(ignore_permissions=True)
        self._notify_approver()

    # ── Private Helpers ────────────────────────────────────────────────────────

    def _set_total_days(self):
        if self.from_date and self.to_date:
            delta = (getdate(self.to_date) - getdate(self.from_date)).days + 1
            self.total_days = max(delta, 0)

    def _set_approver(self):
        if not self.approver and self.employee:
            reports_to = frappe.db.get_value("Employee", self.employee, "reports_to")
            if reports_to:
                user = frappe.db.get_value("Employee", reports_to, "user_id")
                self.approver = user

    def _validate_dates(self):
        if self.from_date and self.to_date:
            if getdate(self.from_date) > getdate(self.to_date):
                frappe.throw(_("From Date cannot be after To Date."))

    def _validate_future_dates(self):
        if self.from_date and getdate(self.from_date) < getdate(nowdate()):
            frappe.msgprint(
                _("Note: WFH Request starts in the past."),
                indicator="orange", alert=True,
            )

    def _check_overlap(self):
        if not (self.employee and self.from_date and self.to_date):
            return
        filters = {
            "employee": self.employee,
            "status":   ("in", ["Pending Approval", "Approved"]),
            "docstatus": ("!=", 2),
        }
        if not self.is_new():
            filters["name"] = ("!=", self.name)
        for req in frappe.get_all("WFH Request", filters=filters,
                                   fields=["name", "from_date", "to_date", "status"]):
            overlap = not (
                getdate(self.to_date)   < getdate(req.from_date) or
                getdate(self.from_date) > getdate(req.to_date)
            )
            if overlap:
                frappe.throw(
                    _("Overlapping WFH Request <b>{0}</b> ({1} to {2}) already exists.").format(
                        req.name, req.from_date, req.to_date)
                )

    def _create_attendance(self):
        for d in get_date_range(self.from_date, self.to_date):
            if frappe.db.exists("Attendance",
                                {"employee": self.employee, "attendance_date": d, "docstatus": 1}):
                continue
            att = frappe.new_doc("Attendance")
            att.employee        = self.employee
            att.attendance_date = d
            att.status          = "Work From Home"
            att.company         = frappe.db.get_value("Employee", self.employee, "company")
            att.wfh_request     = self.name
            att.insert(ignore_permissions=True)
            att.submit()
        frappe.db.commit()

    def _cancel_attendance(self):
        for r in frappe.get_all("Attendance",
                                 filters={"employee": self.employee, "status": "Work From Home",
                                          "wfh_request": self.name, "docstatus": 1},
                                 fields=["name"]):
            frappe.get_doc("Attendance", r.name).cancel()
        frappe.db.commit()

    def _cancel_sessions(self):
        for s in frappe.get_all("Work Session",
                                 filters={"wfh_request": self.name, "docstatus": ("!=", 2)},
                                 fields=["name", "docstatus"]):
            doc = frappe.get_doc("Work Session", s.name)
            if doc.docstatus == 1:
                doc.cancel()

    def _notify_employee(self, action):
        emp_user = frappe.db.get_value("Employee", self.employee, "user_id")
        if not emp_user:
            return
        subjects = {
            "approved": _("Your WFH Request {0} has been Approved").format(self.name),
            "rejected": _("Your WFH Request {0} has been Rejected").format(self.name),
        }
        message = (
            f"Your WFH Request <b>{self.name}</b> from {self.from_date} to {self.to_date} "
            f"has been <b>{action}</b>."
        )
        if action == "rejected" and self.rejection_reason:
            message += f"<br>Reason: {self.rejection_reason}"
        frappe.sendmail(recipients=[emp_user], subject=subjects[action], message=message,
                        reference_doctype=self.doctype, reference_name=self.name)

    def _notify_approver(self):
        if not self.approver:
            frappe.msgprint(_("No approver found for this employee."), alert=True)
            return
        frappe.sendmail(
            recipients=[self.approver],
            subject=_("WFH Request Pending Approval: {0}").format(self.name),
            message=(
                f"<b>{self.employee_name}</b> submitted WFH Request <b>{self.name}</b> "
                f"from <b>{self.from_date}</b> to <b>{self.to_date}</b>.<br>"
                f"Reason: {self.reason or 'Not specified'}<br><br>"
                f"Please review and approve/reject."
            ),
            reference_doctype=self.doctype, reference_name=self.name,
        )
        frappe.msgprint(_("Approval request sent to {0}").format(self.approver), alert=True)


@frappe.whitelist()
def get_active_wfh_request(employee, date=None):
    if not employee:
        return None
    date = date or nowdate()
    result = frappe.db.sql("""
        SELECT name, from_date, to_date, work_mode, status
        FROM `tabWFH Request`
        WHERE employee  = %s AND status = 'Approved'
          AND from_date <= %s AND to_date >= %s AND docstatus = 1
        LIMIT 1
    """, (employee, date, date), as_dict=True)
    return result[0] if result else None