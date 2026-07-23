# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

# ══════════════════════════════════════════════════════════════════════════════
# whistleblower_report.py
# ecclesia/ecclesia/doctype/whistleblower_report/whistleblower_report.py
# ══════════════════════════════════════════════════════════════════════════════
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, random_string


class WhistleblowerReport(Document):

    def before_insert(self):
        self._generate_masked_code()
        if not self.received_date:
            self.received_date = nowdate()

    def validate(self):
        self._protect_identity()

    def on_submit(self):
        self._notify_investigators()
        self._raise_compliance_incident_if_critical()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _generate_masked_code(self):
        """Generate a random, non-identifiable report code."""
        if not self.report_code:
            code = "WB-" + random_string(8).upper()
            self.report_code = code

    def _protect_identity(self):
        """Never store identifying information if anonymous."""
        if self.is_anonymous:
            # Clear any accidentally entered identifying details
            if self.alleged_parties and "@" in self.alleged_parties:
                frappe.msgprint(
                    _("Do not include contact details of anonymous reporters in the alleged parties field."),
                    indicator="orange"
                )

    def _notify_investigators(self):
        """Notify assigned investigator and compliance officer — confidentially."""
        emails = []
        if self.assigned_investigator:
            e = frappe.db.get_value("Employee", self.assigned_investigator, "company_email")
            if e:
                emails.append(e)
        co = frappe.db.get_value("Company", self.company, "compliance_officer")
        if co:
            e = frappe.db.get_value("Employee", co, "company_email")
            if e and e not in emails:
                emails.append(e)

        if not emails:
            return

        from ecclesia.api.compliance.email_templates import (
            render_whistleblower_received, send_compliance_email
        )
        html = render_whistleblower_received(self)
        send_compliance_email(
            recipients=emails,
            subject=f"🔒 [CONFIDENTIAL] Whistleblower Report Received: {self.report_code}",
            html_body=html
        )

    def _raise_compliance_incident_if_critical(self):
        if self.severity not in ("High", "Critical"):
            return
        if self.compliance_incident_ref:
            return
        inc = frappe.new_doc("Compliance Incident")
        inc.incident_title  = f"Whistleblower: {self.report_code} — {self.report_category}"
        inc.incident_date   = self.received_date
        inc.incident_type   = "Fraud" if "Fraud" in self.report_category else "Other"
        inc.severity        = self.severity
        inc.status          = "Under Investigation"
        inc.description     = (f"Whistleblower report {self.report_code}. "
                               f"Category: {self.report_category}. "
                               f"Severity: {self.severity}.")
        if self.assigned_investigator:
            inc.assigned_to = self.assigned_investigator
        inc.insert(ignore_permissions=True)
        self.db_set("compliance_incident_ref", inc.name)


@frappe.whitelist()
def get_whistleblower_summary(company):
    reports = frappe.db.get_all(
        "Whistleblower Report",
        filters={"company": company},
        fields=["status", "severity", "report_category", "outcome"]
    )
    return {
        "total":          len(reports),
        "under_investigation": sum(1 for r in reports if r.status == "Under Investigation"),
        "substantiated":  sum(1 for r in reports if r.outcome and "Substantiated" in r.outcome),
        "critical":       sum(1 for r in reports if r.severity == "Critical"),
        "by_category":    {}
    }

