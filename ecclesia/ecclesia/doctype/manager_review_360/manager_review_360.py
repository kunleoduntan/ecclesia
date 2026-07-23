# ecclesia/doctype/manager_review_360/manager_review_360.py
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import nowdate, flt

class ManagerReview360(Document):

    def validate(self):
        self._validate_is_manager()
        self._validate_ratings()
        self._check_duplicate()

    def on_submit(self):
        self.status = "Submitted"
        self.review_date = nowdate()
        self._update_performance_record()
        self._handle_pip_recommendation()
        self._notify_employee()

    def _validate_is_manager(self):
        reports_to = frappe.db.get_value("Employee", self.employee, "reports_to")
        if reports_to and reports_to != self.manager:
            # Allow HR to also submit — don't hard-block
            if not frappe.has_permission("Manager Review 360", "write", raise_exception=False):
                frappe.msgprint(
                    _("{0} does not report directly to {1}. Please confirm this review is appropriate.").format(
                        self.employee, self.manager),
                    indicator="orange", alert=True
                )

    def _validate_ratings(self):
        for field in ["goal_score","competency_score","values_score","overall_manager_rating"]:
            val = flt(getattr(self, field, 0))
            if val and not (1 <= val <= 5):
                frappe.throw(_("{0} must be between 1 and 5.").format(
                    self.meta.get_label(field)))

    def _check_duplicate(self):
        existing = frappe.db.get_value("Manager Review 360",
            {"employee": self.employee,
             "performance_cycle": self.performance_cycle,
             "name": ("!=", self.name),
             "docstatus": ("!=", 2)}, "name")
        if existing:
            frappe.throw(_("A manager review for {0} in this cycle already exists.").format(self.employee))

    def _update_performance_record(self):
        from ecclesia.api.performance_portal import _update_perf_record
        updates = {
            "manager_score": flt(self.overall_manager_rating),
            "manager_review_date": nowdate(),
        }
        if self.recommend_promotion:
            updates["promotion_recommended"] = 1
        _update_perf_record(self.employee, self.performance_cycle, updates)

    def _handle_pip_recommendation(self):
        if self.recommend_pip:
            frappe.enqueue(
                "ecclesia.api.performance_portal.auto_create_pip_draft",
                employee=self.employee,
                cycle=self.performance_cycle,
                reason=self.pip_reason or "",
                queue="short"
            )

    def _notify_employee(self):
        emp_user = frappe.db.get_value("Employee", self.employee, "user_id")
        manager_name = frappe.db.get_value("Employee", self.manager, "employee_name")
        if emp_user:
            frappe.sendmail(
                recipients=[emp_user],
                subject="Your Manager Review is Complete",
                message=(f"Your manager review for {self.performance_cycle} has been completed "
                         f"by {manager_name}. Log in to view your feedback.")
            )
