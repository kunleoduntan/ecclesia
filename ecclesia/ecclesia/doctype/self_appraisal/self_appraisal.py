# ecclesia/doctype/self_appraisal/self_appraisal.py
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import nowdate, flt, getdate

class SelfAppraisal(Document):

    def validate(self):
        self._one_per_cycle()
        self._validate_deadline()
        self._validate_self_rating()
        self._calculate_competency_average()

    def on_submit(self):
        self._lock_and_notify()
        self._update_performance_record()
        self._trigger_ai_feedback()

    def on_cancel(self):
        frappe.db.set_value("Self Appraisal", self.name, "status", "Draft")

    # ── Private ──────────────────────────────────────────────────────

    def _one_per_cycle(self):
        existing = frappe.db.get_value("Self Appraisal",
            {"employee": self.employee,
             "performance_cycle": self.performance_cycle,
             "name": ("!=", self.name),
             "docstatus": ("!=", 2)},
            "name")
        if existing:
            frappe.throw(
                _("A self appraisal for {0} in cycle {1} already exists: {2}").format(
                    self.employee, self.performance_cycle, existing))

    def _validate_deadline(self):
        if not self.performance_cycle:
            return
        deadline = frappe.db.get_value("Performance Cycle",
            self.performance_cycle, "self_appraisal_deadline")
        if deadline and getdate(nowdate()) > getdate(deadline):
            if not frappe.has_permission("Performance Cycle", "write"):
                frappe.throw(
                    _("The self-appraisal deadline ({0}) for this cycle has passed.").format(deadline))

    def _validate_self_rating(self):
        rating = flt(self.overall_self_rating)
        if rating and not (1 <= rating <= 5):
            frappe.throw(_("Overall self rating must be between 1 and 5."))

    def _calculate_competency_average(self):
        if not self.competency_ratings:
            return
        total_weight = sum(flt(r.weight) for r in self.competency_ratings)
        if total_weight == 0:
            return
        weighted_sum = sum(flt(r.self_rating) * flt(r.weight) for r in self.competency_ratings)
        # Store on goal_self_score as a composite if not manually set
        if not self.goal_self_score:
            self.goal_self_score = round(weighted_sum / total_weight, 2)

    def _lock_and_notify(self):
        self.status = "Submitted"
        self.submission_date = nowdate()
        # Notify manager
        manager = frappe.db.get_value("Employee", self.employee, "reports_to")
        if manager:
            manager_user = frappe.db.get_value("Employee", manager, "user_id")
            emp_name = frappe.db.get_value("Employee", self.employee, "employee_name")
            if manager_user:
                frappe.sendmail(
                    recipients=[manager_user],
                    subject=f"Self Appraisal Submitted: {emp_name}",
                    message=(f"{emp_name} has submitted their self appraisal for "
                             f"{self.performance_cycle}. Please review and complete "
                             f"the manager review at your earliest convenience.")
                )

    def _update_performance_record(self):
        from ecclesia.api.performance_portal import _update_perf_record
        _update_perf_record(self.employee, self.performance_cycle, {
            "self_score": flt(self.overall_self_rating),
            "self_appraisal_date": nowdate(),
        })

    def _trigger_ai_feedback(self):
        frappe.enqueue(
            "ecclesia.api.performance_portal._generate_ai_feedback",
            appraisal=self.name,
            queue="short", timeout=120
        )
