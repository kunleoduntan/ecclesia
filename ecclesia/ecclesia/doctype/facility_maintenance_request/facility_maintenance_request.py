# Copyright (c) 2026, Kunle Oduntan and contributors
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

class FacilityMaintenanceRequest(Document):
    def before_insert(self):
        if not self.report_date:
            self.report_date = nowdate()
        if not self.status:
            self.status = "Open"

    def on_submit(self):
        self._notify_facility_manager()
        self._update_facility_kpis()

    def on_cancel(self):
        self._update_facility_kpis()

    def _notify_facility_manager(self):
        if not self.facility:
            return
        manager = frappe.db.get_value("Facility", self.facility, "facility_manager")
        if not manager:
            return
        email = frappe.db.get_value("Employee", manager, "company_email")
        if email:
            frappe.sendmail(
                recipients=[email],
                subject=_("Maintenance Request [{0}]: {1}").format(self.priority, self.facility),
                message=_("Category: {0}<br>Subject: {1}<br>"
                          "<a href='/Form/Facility Maintenance Request/{2}'>{2}</a>").format(
                    self.maintenance_category, self.subject, self.name
                ),
            )

    def _update_facility_kpis(self):
        if self.facility:
            frappe.get_doc("Facility", self.facility).update_kpis()
