# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt


# ══════════════════════════════════════════════════════════════════════════════
# compliance_training_record.py
# ecclesia/ecclesia/doctype/compliance_training_record/compliance_training_record.py
# ══════════════════════════════════════════════════════════════════════════════


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate


class ComplianceTrainingRecord(Document):

    def validate(self):
        self._set_passed()
        self._set_title()

    def on_submit(self):
        self._update_training_calendar()
        self._notify_employee()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_title(self):
        if not self.training_title and self.training_category:
            emp_name = frappe.db.get_value("Employee", self.employee, "employee_name") or self.employee
            self.training_title = f"{self.training_category} — {emp_name} — {self.training_date or nowdate()}"

    def _set_passed(self):
        if self.completion_status == "Completed":
            if self.score is not None:
                self.passed = 1 if flt(self.score) >= 70 else 0
            else:
                self.passed = 1
        elif self.completion_status in ("Failed",):
            self.passed = 0

    def _update_training_calendar(self):
        if not self.training_calendar:
            return
        cal = frappe.get_doc("Compliance Training Calendar", self.training_calendar)
        completed = frappe.db.count("Compliance Training Record", {
            "training_calendar": self.training_calendar,
            "completion_status": "Completed",
            "docstatus": 1
        })
        if cal.target_headcount and cal.target_headcount > 0:
            cal.actual_attendees = completed
            cal.actual_completion_pct = round(completed / cal.target_headcount * 100, 1)
            if cal.actual_completion_pct >= 95:
                cal.status = "Completed"
            cal.save(ignore_permissions=True)

    def _notify_employee(self):
        email = frappe.db.get_value("Employee", self.employee, "company_email")
        if not email:
            return
        from ecclesia.api.compliance.email_templates import (
            render_training_completion, send_compliance_email
        )
        html = render_training_completion(self)
        send_compliance_email(
            recipients=[email],
            subject=f"{'✅ Training Completed' if self.passed else '❌ Training Incomplete'}: {self.training_category}",
            html_body=html
        )


@frappe.whitelist()
def get_training_completion_rate(company, fiscal_year=None):
    filters = {"company": company, "docstatus": 1}
    if fiscal_year:
        pass  # training_date filter
    records = frappe.db.get_all(
        "Compliance Training Record",
        filters=filters,
        fields=["completion_status","training_category","is_mandatory","passed","employee"]
    )
    mandatory = [r for r in records if r.is_mandatory]
    return {
        "total": len(records),
        "mandatory": len(mandatory),
        "mandatory_completed": sum(1 for r in mandatory if r.completion_status == "Completed"),
        "mandatory_completion_pct": round(
            sum(1 for r in mandatory if r.completion_status == "Completed") / len(mandatory) * 100, 1
        ) if mandatory else 0,
        "by_category": {}
    }

