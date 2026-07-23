# ecclesia/doctype/resume_screening_result/resume_screening_result.py
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt

class ResumeScreeningResult(Document):

    def validate(self):
        # If HR overrides to Shortlisted, ensure we don't silently ignore knockout
        if self.hr_override == "Shortlisted" and self.knockout_failed:
            frappe.msgprint(
                _("Warning: This candidate failed a mandatory knockout check. "
                  "You are overriding the auto-rejection. Please add a note explaining the decision."),
                indicator="orange", alert=True
            )

    def after_insert(self):
        self._sync_applicant_status()

    def on_update(self):
        # If HR override changes, sync back to Job Applicant
        if self.hr_override:
            self._sync_applicant_status(decision=self.hr_override)

    def _sync_applicant_status(self, decision=None):
        decision = decision or self.auto_decision
        if not decision:
            return
        # Find the matching Job Applicant
        applicant = frappe.db.get_value("Job Applicant",
            {"applicant_name": self.candidate_name,
             "job_opening": self.job_opening}, "name")
        if applicant:
            status_map = {
                "Shortlisted": "Replied",
                "Rejected":    "Rejected",
                "Refer to HR": "Open",
                "Hold":        "Hold",
            }
            frappe.db.set_value("Job Applicant", applicant, {
                "custom_screening_status": decision,
                "status": status_map.get(decision, "Open"),
            })
