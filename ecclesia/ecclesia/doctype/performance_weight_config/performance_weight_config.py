# ecclesia/doctype/performance_weight_config/performance_weight_config.py
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt

class PerformanceWeightConfig(Document):

    def validate(self):
        self._validate_weights_sum()
        self._validate_reviewer_weights()

    def _validate_weights_sum(self):
        total = flt(self.goal_weight) + flt(self.competency_weight) + flt(self.values_weight)
        if abs(total - 100) > 0.01:
            frappe.throw(
                _("Goal Weight + Competency Weight + Values Weight must total 100%. "
                  "Current total: {0}%").format(total)
            )

    def _validate_reviewer_weights(self):
        total = flt(self.self_weight) + flt(self.peer_weight) + flt(self.manager_weight)
        if abs(total - 100) > 0.01:
            frappe.throw(
                _("Self Weight + Peer Weight + Manager Weight must total 100%. "
                  "Current total: {0}%").format(total)
            )

    def before_save(self):
        if flt(self.min_peers) > flt(self.max_peers):
            frappe.throw(_("Minimum peers ({0}) cannot exceed maximum peers ({1}).").format(
                self.min_peers, self.max_peers))
