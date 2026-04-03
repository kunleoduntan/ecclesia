# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from ecclesia.utils.score_engine import compute_composite_score


class EmployeePerformanceRecord(Document):

    def validate(self):
        self._validate_goal_weights()

    def before_submit(self):
        # Lock self-appraisal timestamp
        if not self.self_appraisal_date:
            self.self_appraisal_date = now_datetime()

    def on_update(self):
        # Recompute whenever actuals or self-scores are saved
        if self.goals and self.docstatus == 1:
            compute_composite_score(self.name)

    def _validate_goal_weights(self):
        total = sum(g.weight or 0 for g in (self.goals or []))
        if self.goals and abs(total - 100) > 0.01:
            frappe.throw(
                f"Goal weights must sum to 100% — currently {total:.1f}%."
            )