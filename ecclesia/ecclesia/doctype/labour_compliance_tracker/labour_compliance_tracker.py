# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/ecclesia/doctype/labour_compliance_tracker/labour_compliance_tracker.py
 
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate
 
 
class LabourComplianceTracker(Document):
 
    def validate(self):
        self._compute_overall_status()
        self._validate_minimum_wage()
        self._fetch_employee_count()
 
    def on_submit(self):
        self._notify_hr_officer()
        self._send_alert_if_issues()
 
    # ── Helpers ───────────────────────────────────────────────────────────────
 
    def _fetch_employee_count(self):
        if not self.total_employees and self.company:
            count = frappe.db.count("Employee", {
                "company": self.company,
                "status": "Active"
            })
            self.total_employees = count
 
    def _validate_minimum_wage(self):
        if self.lowest_gross_paid and self.current_min_wage:
            if flt(self.lowest_gross_paid) < flt(self.current_min_wage):
                self.minimum_wage_compliant = 0
                frappe.msgprint(
                    _("⚠️ Minimum wage non-compliance detected. "
                      "Lowest gross (₦{0:,.0f}) is below current minimum (₦{1:,.0f}).").format(
                          flt(self.lowest_gross_paid), flt(self.current_min_wage)
                      ),
                    indicator="red", title=_("Minimum Wage Alert")
                )
            else:
                self.minimum_wage_compliant = 1
 
    def _compute_overall_status(self):
        """Weighted status from all compliance checks."""
        critical_fails = []
        minor_fails = []
 
        if not self.minimum_wage_compliant:
            critical_fails.append("Minimum wage")
        if not self.pencom_all_registered:
            critical_fails.append("PenCom registration")
        if not self.working_hours_compliant:
            minor_fails.append("Working hours")
        if not self.statutory_leave_compliant:
            minor_fails.append("Statutory leave")
        if not self.maternity_leave_compliant:
            minor_fails.append("Maternity leave")
        if not self.employment_contracts_compliant:
            minor_fails.append("Employment contracts")
        if not self.disciplinary_procedure_current:
            minor_fails.append("Disciplinary procedure")
 
        if critical_fails:
            self.overall_status = "Non-Compliant"
        elif len(minor_fails) >= 3:
            self.overall_status = "Major Issues"
        elif minor_fails:
            self.overall_status = "Minor Issues"
        else:
            self.overall_status = "Compliant"
 
    def _notify_hr_officer(self):
        if not self.responsible_officer:
            return
        email = frappe.db.get_value("Employee", self.responsible_officer, "company_email")
        if not email:
            return
        frappe.sendmail(
            recipients=[email],
            subject=_(f"Labour Compliance Tracker — {self.period_label}: {self.overall_status}"),
            message=_("""
                <p>Labour Compliance Tracker <b>{0}</b> for period <b>{1}</b>
                has been submitted with status: <b>{2}</b>.</p>
                <p>Minimum Wage: {3} | Working Hours: {4} | PenCom: {5}</p>
                <p><a href="/Form/Labour Compliance Tracker/{6}">View Tracker →</a></p>
            """).format(
                self.name, self.period_label, self.overall_status,
                "✅" if self.minimum_wage_compliant else "❌ NON-COMPLIANT",
                "✅" if self.working_hours_compliant else "❌",
                "✅" if self.pencom_all_registered else "❌",
                self.name
            )
        )
 
    def _send_alert_if_issues(self):
        if self.overall_status in ("Non-Compliant", "Major Issues"):
            from ecclesia.api.compliance.email_templates import (
                render_labour_compliance_alert, send_compliance_email
            )
            emails = []
            for emp in [self.responsible_officer]:
                if emp:
                    e = frappe.db.get_value("Employee", emp, "company_email")
                    if e:
                        emails.append(e)
            co = frappe.db.get_value("Company", self.company, "compliance_officer")
            if co:
                e = frappe.db.get_value("Employee", co, "company_email")
                if e and e not in emails:
                    emails.append(e)
            html = render_labour_compliance_alert(self)
            send_compliance_email(
                recipients=emails,
                subject=f"⚠️ Labour Compliance Alert: {self.company} — {self.period_label}",
                html_body=html
            )
 
 
@frappe.whitelist()
def get_labour_trend(company, periods=6):
    """Return last N periods of labour compliance status."""
    return frappe.db.get_all(
        "Labour Compliance Tracker",
        filters={"company": company, "docstatus": 1},
        fields=["name", "period_label", "overall_status", "minimum_wage_compliant",
                "working_hours_compliant", "pencom_all_registered", "total_employees"],
        order_by="period_label desc",
        limit=int(periods)
    )
 
 
# ══════════════════════════════════════════════════════════════════════════════
 