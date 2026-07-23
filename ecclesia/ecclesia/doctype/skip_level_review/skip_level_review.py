# ecclesia/doctype/skip_level_review/skip_level_review.py
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, nowdate

class SkipLevelReview(Document):

    def validate(self):
        self._validate_rating()

    def on_submit(self):
        self.status = "Submitted"
        self.review_date = nowdate()
        if self.adjusted_rating:
            from ecclesia.api.performance_portal import _update_perf_record
            _update_perf_record(self.employee, self.performance_cycle,
                {"skip_level_score": flt(self.adjusted_rating or self.overall_skip_rating)})

    def _validate_rating(self):
        for f in ["overall_skip_rating","adjusted_rating"]:
            val = flt(getattr(self, f, 0))
            if val and not (1 <= val <= 5):
                frappe.throw(_("{0} must be between 1 and 5.").format(f.replace("_"," ").title()))
