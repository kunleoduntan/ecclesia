# ecclesia/doctype/performance_idp/performance_idp.py
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, nowdate

class PerformanceIdp(Document):

    def validate(self):
        self._recalculate_overall_progress()

    def on_submit(self):
        self.status = "Active"
        self._notify_mentor()

    def _recalculate_overall_progress(self):
        if not self.idp_items:
            return
        progs = [flt(r.progress) for r in self.idp_items]
        self.overall_progress = round(sum(progs) / max(1, len(progs)), 1)

    def _notify_mentor(self):
        if not self.mentor:
            return
        mentor_user = frappe.db.get_value("Employee", self.mentor, "user_id")
        emp_name = frappe.db.get_value("Employee", self.employee, "employee_name")
        if mentor_user:
            frappe.sendmail(
                recipients=[mentor_user],
                subject=f"You have been assigned as Mentor: {emp_name}",
                message=(f"You have been assigned as mentor for {emp_name}'s "
                         f"Individual Development Plan ({self.plan_period}). "
                         f"Please log in to review the plan and arrange your first session.")
            )
