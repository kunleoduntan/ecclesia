# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/ecclesia/doctype/environmental_compliance_record/environmental_compliance_record.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff, nowdate, add_days


class EnvironmentalComplianceRecord(Document):

    def validate(self):
        self._compute_days_to_expiry()
        if self.auto_status_update:
            self._update_status()
        self._check_annual_report()

    def before_save(self):
        self._compute_days_to_expiry()
        if self.auto_status_update:
            self._update_status()

    def on_update(self):
        if self.status == "Expired" and not frappe.db.exists(
            "Compliance Incident",
            {"incident_title": f"Expired Environmental Permit: {self.permit_title}",
             "status": ["not in", ["Resolved","Closed"]]}
        ):
            self._raise_expired_incident()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _compute_days_to_expiry(self):
        if self.expiry_date:
            self.days_to_expiry = date_diff(self.expiry_date, nowdate())

    def _update_status(self):
        if self.status in ("Suspended","Revoked"):
            return
        days = self.days_to_expiry or 0
        if days < 0:
            self.status = "Expired"
        elif days <= 30:
            self.status = "Expiring Soon"
        elif days > 90 and self.status not in ("Under Renewal",):
            self.status = "Active"

    def _check_annual_report(self):
        if self.annual_report_required and self.annual_report_due_date:
            if not self.annual_report_filed:
                from frappe.utils import getdate
                if getdate(self.annual_report_due_date) < getdate(nowdate()):
                    frappe.msgprint(
                        _(f"⚠️ Annual Environmental Report for '{self.permit_title}' "
                          f"was due {self.annual_report_due_date} and has not been filed."),
                        indicator="red", alert=True
                    )

    def _raise_expired_incident(self):
        inc = frappe.new_doc("Compliance Incident")
        inc.incident_title  = f"Expired Environmental Permit: {self.permit_title}"
        inc.incident_date   = nowdate()
        inc.incident_type   = "Expired License"
        inc.obligation_type = "Environmental Permit"
        inc.severity        = "Major"
        inc.status          = "Reported"
        inc.description     = (
            f"Environmental permit '{self.permit_title}' ({self.permit_type}) "
            f"issued by {self.issuing_authority} has expired. "
            f"Operating without a valid permit is a regulatory offence."
        )
        if self.responsible_officer:
            inc.assigned_to = self.responsible_officer
        inc.insert(ignore_permissions=True)
        frappe.msgprint(
            _("Compliance Incident {0} created for expired environmental permit.").format(inc.name),
            indicator="orange", alert=True
        )

    def send_expiry_alert(self, days_remaining):
        """Called by scheduler for expiry alerts."""
        if not self.responsible_officer:
            return
        email = frappe.db.get_value("Employee", self.responsible_officer, "company_email")
        if not email:
            return
        from ecclesia.api.compliance.email_templates import (
            render_permit_expiry_alert, send_compliance_email
        )
        html = render_permit_expiry_alert(
            doc_name=self.name,
            doc_type="Environmental Compliance Record",
            permit_name=self.permit_title,
            company=self.company,
            expiry_date=self.expiry_date,
            days_to_expiry=days_remaining,
            responsible_officer=self.responsible_officer,
            renewal_cost=self.renewal_cost,
            renewal_lead_days=self.renewal_lead_time_days or 90
        )
        send_compliance_email(
            recipients=[email],
            subject=f"⚠️ Environmental Permit Expiring in {days_remaining} days: {self.permit_title}",
            html_body=html
        )


@frappe.whitelist()
def get_environmental_dashboard(company):
    records = frappe.db.get_all(
        "Environmental Compliance Record",
        filters={"company": company},
        fields=["name","permit_title","permit_type","status","expiry_date",
                "days_to_expiry","facility","corrective_actions_pending"]
    )
    return {
        "total":          len(records),
        "active":         sum(1 for r in records if r.status == "Active"),
        "expiring_soon":  sum(1 for r in records if r.status == "Expiring Soon"),
        "expired":        sum(1 for r in records if r.status == "Expired"),
        "pending_actions":sum(1 for r in records if (r.corrective_actions_pending or 0) > 0),
        "records":        records
    }