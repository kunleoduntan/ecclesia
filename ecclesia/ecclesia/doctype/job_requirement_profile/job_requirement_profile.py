# ecclesia/doctype/job_requirement_profile/job_requirement_profile.py
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt

class JobRequirementProfile(Document):

    def validate(self):
        self._validate_weight_total()
        self._validate_thresholds()
        self._validate_salary_range()
        self._validate_equity_bonus()

    def before_save(self):
        self.total_weight_display = self._get_weight_total()

    def _get_weight_total(self):
        return flt(self.education_weight) + flt(self.degree_class_weight) +                flt(self.experience_weight) + flt(self.skills_weight) +                flt(self.certifications_weight) + flt(self.location_weight) +                flt(self.salary_weight)

    def _validate_weight_total(self):
        total = self._get_weight_total()
        if abs(total - 100) > 0.1:
            frappe.throw(
                _("All scoring weights must total 100%. Current total: {0}%").format(round(total, 1))
            )

    def _validate_thresholds(self):
        sl = flt(self.auto_shortlist_threshold)
        ar = flt(self.auto_reject_threshold)
        if ar >= sl:
            frappe.throw(
                _("Auto-Reject threshold ({0}%) must be lower than "
                  "Auto-Shortlist threshold ({1}%).").format(ar, sl))

    def _validate_salary_range(self):
        if self.salary_budget_min and self.salary_budget_max:
            if flt(self.salary_budget_min) >= flt(self.salary_budget_max):
                frappe.throw(_("Minimum budget must be less than maximum budget."))

    def _validate_equity_bonus(self):
        if flt(self.gender_equity_bonus) > 10:
            frappe.throw(_("Gender equity bonus should not exceed 10% to remain legally defensible."))

    def on_submit(self):
        # Check that a Job Opening exists and is open
        if self.job_opening:
            status = frappe.db.get_value("Job Opening", self.job_opening, "status")
            if status == "Closed":
                frappe.throw(_("The linked Job Opening {0} is already closed.").format(self.job_opening))
