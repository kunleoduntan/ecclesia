# ecclesia/doctype/hr_calibration_session/hr_calibration_session.py
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, nowdate

class HrCalibrationSession(Document):

    def validate(self):
        if not self.participants:
            frappe.throw(_("At least one participant is required for a calibration session."))

    def on_submit(self):
        self.status = "Completed"
        self._apply_overrides()
        self._notify_hr_team()

    def _apply_overrides(self):
        """Write calibrated ratings back to Employee Performance Records."""
        for row in (self.overrides or []):
            from ecclesia.api.performance_portal import _update_perf_record
            cycle = frappe.db.get_value("Performance Cycle",
                {"status": "Active"}, "name") or self.performance_cycle
            _update_perf_record(row.employee, cycle, {
                "calibrated_rating": flt(row.calibrated_rating),
                "calibration_notes": row.override_reason,
                "calibration_status": "Calibrated",
            })
        frappe.db.commit()

    def _notify_hr_team(self):
        count = len(self.overrides or [])
        if count:
            frappe.msgprint(
                _("{0} rating override(s) applied to Employee Performance Records.").format(count),
                indicator="green", alert=True
            )
