# Copyright (c) 2026, Kunle Oduntan and contributors
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

class AssetInspection(Document):
    def validate(self):
        if not self.inspection_date:
            self.inspection_date = nowdate()
        self._set_status_from_condition()

    def _set_status_from_condition(self):
        if self.overall_condition == "Critical - Action Required":
            self.status = "Failed - Action Pending"
        elif self.overall_condition in ("Excellent", "Good"):
            self.status = "Passed"

    def on_submit(self):
        if self.status == "Failed - Action Pending":
            self._raise_maintenance_request()

    def _raise_maintenance_request(self):
        if self.maintenance_request:
            return
        mr = frappe.new_doc("Facility Maintenance Request")
        mr.subject = "Follow-up from Asset Inspection: {}".format(self.asset)
        mr.facility = self.facility
        mr.reported_by = frappe.session.user
        mr.maintenance_category = "Other"
        mr.description = self.recommended_actions or "Action required: inspection {}.".format(self.name)
        mr.priority = "High"
        mr.insert(ignore_permissions=True)
        self.db_set("maintenance_request", mr.name)
