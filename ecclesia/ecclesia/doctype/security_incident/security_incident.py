# Copyright (c) 2026, Kunle Oduntan and contributors
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

class SecurityIncident(Document):
    def validate(self):
        if not self.report_date:
            self.report_date = nowdate()

    def on_submit(self):
        self.db_set("status", "Under Investigation")
        self._notify_hr_manager()

    def _notify_hr_manager(self):
        hr_users = frappe.db.get_all("Has Role", filters={"role": "HR Manager"}, fields=["parent"])
        emails = [frappe.db.get_value("User", u.parent, "email") for u in hr_users]
        emails = [e for e in emails if e]
        if emails:
            frappe.sendmail(
                recipients=emails,
                subject=_("Security Incident: {0} at {1}").format(self.incident_type, self.facility),
                message=_("Severity: {0}<br>Date: {1}<br>Reported by: {2}<br>"
                          "<a href='/Form/Security Incident/{3}'>{3}</a>").format(
                    self.severity, self.incident_date, self.reported_by, self.name
                ),
            )
