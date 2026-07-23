# ecclesia/doctype/resume/resume.py
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import nowdate

class Resume(Document):

    def after_insert(self):
        """Trigger screening automatically when a Resume is created."""
        self._trigger_screening()

    def on_update(self):
        """Re-trigger if resume file is updated and status is Uploaded."""
        if self.status == "Uploaded" and self.resume_file:
            self._trigger_screening()

    def _trigger_screening(self):
        if not self.job_opening:
            return
        profile_name = frappe.db.get_value(
            "Job Requirement Profile", {"job_opening": self.job_opening}, "name")
        if not profile_name:
            return

        # Link the Job Applicant if not already set
        if self.job_applicant and not frappe.db.get_value(
                "Job Applicant", self.job_applicant, "custom_screening_status"):
            frappe.enqueue(
                "ecclesia.api.recruitment_auto_screen.screen_single_applicant",
                applicant_name=self.job_applicant,
                job_opening=self.job_opening,
                profile_name=profile_name,
                queue="short", timeout=90,
                now=frappe.flags.in_test,
            )
        self.db_set("status", "Scoring")
