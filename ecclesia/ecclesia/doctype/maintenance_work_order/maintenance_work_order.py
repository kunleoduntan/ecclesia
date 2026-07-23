# Copyright (c) 2026, Kunle Oduntan and contributors
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

class MaintenanceWorkOrder(Document):
    def validate(self):
        if self.start_date and self.end_date:
            if getdate(self.end_date) < getdate(self.start_date):
                frappe.throw(_("Planned Completion cannot be before Planned Start."))
        self._compute_task_progress()

    def on_submit(self):
        self.db_set("status", "Open")
        if self.maintenance_request:
            frappe.db.set_value("Facility Maintenance Request", self.maintenance_request, "status", "In Progress")

    def on_cancel(self):
        if self.maintenance_request:
            frappe.db.set_value("Facility Maintenance Request", self.maintenance_request, "status", "Open")

    def _compute_task_progress(self):
        tasks = self.tasks or []
        if not tasks:
            return
        if all(t.status == "Completed" for t in tasks):
            self.status = "Completed"
