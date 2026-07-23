# ecclesia/doctype/performance_pip/performance_pip.py
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import nowdate, getdate, date_diff

class PerformancePip(Document):

    def validate(self):
        self._validate_dates()

    def on_submit(self):
        self.status = "Active"
        self._notify_employee_and_manager()

    def _validate_dates(self):
        if self.start_date and self.end_date:
            if getdate(self.end_date) <= getdate(self.start_date):
                frappe.throw(_("PIP end date must be after start date."))

    def _notify_employee_and_manager(self):
        emp_user = frappe.db.get_value("Employee", self.employee, "user_id")
        emp_name = frappe.db.get_value("Employee", self.employee, "employee_name")
        mgr_user = frappe.db.get_value("Employee", self.manager, "user_id") if self.manager else None

        msg = (f"A Performance Improvement Plan has been created for {emp_name}. "
               f"Duration: {self.start_date} to {self.end_date}. "
               f"Please log in to review the objectives and check-in schedule.")

        for user in filter(None, [emp_user, mgr_user]):
            frappe.sendmail(recipients=[user],
                subject=f"Performance Improvement Plan: {emp_name}",
                message=msg)

    def check_overdue_checkins(self):
        """Called by scheduler to flag missed weekly check-ins."""
        from frappe.utils import add_days, getdate, nowdate
        for row in (self.weekly_checkins or []):
            if not row.checkin_date:
                continue
            if getdate(row.checkin_date) < getdate(add_days(nowdate(), -7)):
                frappe.msgprint(
                    _(f"PIP check-in for week of {row.checkin_date} is overdue."),
                    indicator="red", alert=True
                )
