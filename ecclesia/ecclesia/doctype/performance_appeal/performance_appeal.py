# ecclesia/doctype/performance_appeal/performance_appeal.py
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, nowdate, date_diff, getdate

APPEAL_WINDOW_DAYS = 14

class PerformanceAppeal(Document):

    def validate(self):
        self._validate_appeal_window()
        self._validate_ratings()

    def on_submit(self):
        self.status = "Submitted"
        self._notify_hr()

    def on_update_after_submit(self):
        if self.status in ("Upheld","Dismissed") and self.final_rating:
            self._apply_final_rating()

    def _validate_appeal_window(self):
        cycle_end = frappe.db.get_value("Performance Cycle",
            self.performance_cycle, "end_date")
        if cycle_end and date_diff(nowdate(), cycle_end) > APPEAL_WINDOW_DAYS:
            frappe.throw(
                _("Appeals must be submitted within {0} days of cycle end. "
                  "This cycle ended on {1}.").format(APPEAL_WINDOW_DAYS, cycle_end))

    def _validate_ratings(self):
        for f in ["current_rating","requested_rating","final_rating"]:
            val = flt(getattr(self, f, 0))
            if val and not (1 <= val <= 5):
                frappe.throw(_("{0} must be between 1 and 5.").format(f.replace("_"," ").title()))

    def _notify_hr(self):
        emp_name = frappe.db.get_value("Employee", self.employee, "employee_name")
        hr_users = frappe.get_all("Has Role",
            filters={"role":"HR Manager","parenttype":"User"}, fields=["parent"])
        for u in hr_users:
            frappe.sendmail(
                recipients=[u.parent],
                subject=f"Performance Appeal Submitted: {emp_name}",
                message=(f"{emp_name} has submitted a performance appeal for "
                         f"{self.performance_cycle}. Current rating: {self.current_rating}, "
                         f"requested: {self.requested_rating}. Please review.")
            )

    def _apply_final_rating(self):
        from ecclesia.api.performance_portal import _update_perf_record
        _update_perf_record(self.employee, self.performance_cycle,
            {"final_rating": flt(self.final_rating),
             "appeal_outcome": self.status})
        emp_user = frappe.db.get_value("Employee", self.employee, "user_id")
        if emp_user:
            frappe.sendmail(
                recipients=[emp_user],
                subject=f"Performance Appeal Decision: {self.status}",
                message=(f"Your performance appeal has been reviewed. "
                         f"Decision: <b>{self.status}</b>. "
                         f"Final rating: {self.final_rating or self.current_rating}.<br><br>"
                         f"{self.hr_decision or ''}")
            )
