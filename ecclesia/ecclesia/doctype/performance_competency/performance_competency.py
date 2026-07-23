# ecclesia/doctype/performance_competency/performance_competency.py
import frappe
from frappe.model.document import Document
from frappe import _

class PerformanceCompetency(Document):

    def validate(self):
        self._check_duplicate_name()

    def _check_duplicate_name(self):
        existing = frappe.db.get_value("Performance Competency",
            {"competency_name": self.competency_name, "name": ("!=", self.name)}, "name")
        if existing:
            frappe.throw(_("Competency '{0}' already exists.").format(self.competency_name))

    def on_update(self):
        # Clear form cache so linked tables pick up name changes
        frappe.clear_document_cache("Performance Competency", self.name)
