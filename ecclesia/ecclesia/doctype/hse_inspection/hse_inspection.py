# Copyright (c) 2026, Kunle Oduntan and contributors
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

class HseInspection(Document):
    def validate(self):
        if not self.inspection_date:
            self.inspection_date = nowdate()
        self._compute_compliance_score()
        self._set_pass_fail()

    def _compute_compliance_score(self):
        items = self.checklist or []
        if not items:
            self.overall_score = 0.0
            return
        applicable = [i for i in items if i.compliant != "N/A"]
        compliant  = [i for i in applicable if i.compliant == "Yes"]
        if applicable:
            self.overall_score = round(len(compliant) / len(applicable) * 100, 1)

    def _set_pass_fail(self):
        score = self.overall_score or 0
        if score >= 80:
            self.pass_fail = "Pass"
        elif score >= 60:
            self.pass_fail = "Conditional Pass"
        else:
            self.pass_fail = "Fail"
        self.status = "Completed"
