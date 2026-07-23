# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/ecclesia/doctype/data_breach_register/data_breach_register.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, time_diff_in_hours, flt


class DataBreachRegister(Document):

    def validate(self):
        self._compute_notification_hours()
        self._flag_late_notification()
        self._auto_set_nitda_required()

    def on_submit(self):
        self._raise_compliance_incident()
        self._notify_dpo_and_management()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _auto_set_nitda_required(self):
        """
        NDPR: notify NITDA within 72 hours if the breach is likely to result
        in risk to rights/freedoms of data subjects (Medium/High/Critical severity).
        """
        if self.severity in ("Medium", "High", "Critical"):
            self.nitda_notification_required = 1

    def _compute_notification_hours(self):
        if self.breach_date and self.nitda_notification_date:
            try:
                from datetime import datetime
                breach_dt = datetime.combine(getdate(self.breach_date), datetime.min.time())
                notif_dt  = datetime.combine(getdate(self.nitda_notification_date), datetime.min.time())
                diff = (notif_dt - breach_dt).total_seconds() / 3600
                self.hours_to_notification = round(diff, 1)
            except Exception:
                pass

    def _flag_late_notification(self):
        if self.nitda_notification_required and self.nitda_notification_date:
            self.late_notification_flag = 1 if flt(self.hours_to_notification) > 72 else 0
        elif self.nitda_notification_required and not self.nitda_notified:
            # Check if 72 hours have elapsed since breach_date
            if self.breach_date:
                from datetime import datetime, date
                breach = getdate(self.breach_date)
                today  = getdate(nowdate())
                hours_elapsed = (today - breach).total_seconds() / 3600 if hasattr((today - breach), 'total_seconds') else (today - breach).days * 24
                if (today - breach).days * 24 > 72:
                    self.late_notification_flag = 1
                    frappe.msgprint(
                        _("⚠️ NITDA 72-hour notification window has passed. "
                          "File a late notification immediately and document the reasons for delay."),
                        indicator="red", title=_("Late NITDA Notification")
                    )

    def _raise_compliance_incident(self):
        """Auto-create a Compliance Incident for the breach."""
        if self.compliance_incident_ref:
            return
        inc = frappe.new_doc("Compliance Incident")
        inc.incident_title    = f"Data Breach: {self.breach_title}"
        inc.incident_date     = self.breach_date or nowdate()
        inc.incident_type     = "Data Breach"
        inc.obligation_type   = "Data Breach Notification"
        inc.severity          = self.severity
        inc.status            = "Reported"
        inc.description       = (
            f"Data breach reported: {self.breach_type}. "
            f"Data subjects affected: {self.data_subjects_affected or 'Unknown'}. "
            f"Data categories: {self.data_categories_breached or 'See breach register'}."
        )
        inc.insert(ignore_permissions=True)
        self.db_set("compliance_incident_ref", inc.name)
        frappe.msgprint(
            _("Compliance Incident {0} auto-created for this breach.").format(inc.name),
            indicator="blue", alert=True
        )

    def _notify_dpo_and_management(self):
        dpo_emp = frappe.db.get_value("Company", self.company, "dpo")
        emails = []
        if dpo_emp:
            e = frappe.db.get_value("Employee", dpo_emp, "company_email")
            if e:
                emails.append(e)
        if self.dpo_sign_off:
            e = frappe.db.get_value("Employee", self.dpo_sign_off, "company_email")
            if e and e not in emails:
                emails.append(e)
        # Always notify Accounts Manager role
        for u in frappe.db.get_all("Has Role", filters={"role": "Accounts Manager"}, fields=["parent"]):
            e = frappe.db.get_value("User", u.parent, "email")
            if e and e not in emails:
                emails.append(e)

        from ecclesia.api.compliance.email_templates import (
            render_breach_alert, send_compliance_email
        )
        html = render_breach_alert(self)
        send_compliance_email(
            recipients=emails,
            subject=f"🚨 [{self.severity}] Data Breach Alert: {self.breach_title}",
            html_body=html
        )


@frappe.whitelist()
def get_breach_summary(company):
    breaches = frappe.db.get_all(
        "Data Breach Register",
        filters={"company": company},
        fields=["name", "breach_title", "severity", "status",
                "breach_date", "nitda_notified", "late_notification_flag",
                "data_subjects_affected"]
    )
    return {
        "total":        len(breaches),
        "open":         sum(1 for b in breaches if b.status not in ("Remediated","Closed")),
        "late_notif":   sum(1 for b in breaches if b.late_notification_flag),
        "not_notified": sum(1 for b in breaches if not b.nitda_notified),
        "records":      breaches
    }