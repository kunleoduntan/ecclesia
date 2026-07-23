# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/ecclesia/doctype/suspicious_transaction_report/suspicious_transaction_report.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, random_string


class SuspiciousTransactionReport(Document):

    def before_insert(self):
        self._set_report_date()
        self._set_amlco()

    def validate(self):
        self._warn_tipping_off()
        self._validate_nfiu_submission()

    def on_submit(self):
        self._notify_amlco_internal()
        self._log_event()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_report_date(self):
        if not self.report_date:
            self.report_date = nowdate()

    def _set_amlco(self):
        if not self.submitted_by and self.company:
            amlco = frappe.db.get_value("Company", self.company, "amlco")
            if amlco:
                self.submitted_by = amlco
        if not self.amlco_sign_off and self.company:
            amlco = frappe.db.get_value("Company", self.company, "amlco")
            if amlco:
                self.amlco_sign_off = amlco

    def _warn_tipping_off(self):
        frappe.msgprint(
            _("⚠️ REMINDER: Tipping off is a criminal offence under the Money Laundering "
              "(Prevention and Prohibition) Act 2022. Do not disclose this report to the "
              "subject of the report or any unauthorised person."),
            indicator="red", title=_("Confidentiality Warning"), alert=False
        )

    def _validate_nfiu_submission(self):
        if self.nfiu_submitted and not self.nfiu_submission_date:
            self.nfiu_submission_date = nowdate()
        if self.nfiu_submitted and not self.nfiu_reference:
            frappe.msgprint(
                _("Please enter the NFIU reference number received after goAML submission."),
                indicator="orange", alert=True
            )

    def _notify_amlco_internal(self):
        """Confidential internal notification — only to AMLCO and legal (if involved)."""
        recipients = []
        for field in ["submitted_by", "amlco_sign_off"]:
            emp = self.get(field)
            if emp:
                e = frappe.db.get_value("Employee", emp, "company_email")
                if e and e not in recipients:
                    recipients.append(e)

        from ecclesia.api.compliance.email_templates import (
            render_str_notification, send_compliance_email
        )
        html = render_str_notification(self)
        send_compliance_email(
            recipients=recipients,
            subject=f"🔐 [CONFIDENTIAL] STR Submitted: {self.str_title}",
            html_body=html
        )

    def _log_event(self):
        try:
            ev = frappe.new_doc("Compliance Event Log")
            ev.event_name      = f"STR Submitted: {self.name}"
            ev.event_type      = "Manual"
            ev.source_doctype  = "Suspicious Transaction Report"
            ev.source_document = self.name
            ev.obligation_type = "AML/KYC"
            ev.company         = self.company
            ev.status          = "Success"
            ev.processed_on    = frappe.utils.now()
            ev.triggered_by    = frappe.session.user
            ev.insert(ignore_permissions=True)
        except Exception:
            pass


@frappe.whitelist()
def get_str_summary(company):
    """Dashboard counts for STR tracking."""
    reports = frappe.db.get_all(
        "Suspicious Transaction Report",
        filters={"company": company},
        fields=["name", "status", "nfiu_submitted", "report_type"]
    )
    return {
        "total": len(reports),
        "pending_nfiu": sum(1 for r in reports if not r.nfiu_submitted and r.status not in ("Closed — No Action",)),
        "submitted_nfiu": sum(1 for r in reports if r.nfiu_submitted),
        "by_type": {t: sum(1 for r in reports if r.report_type == t) for t in ["Suspicious Transaction Report (STR)", "Currency Transaction Report (CTR)", "Suspicious Activity Report (SAR)"]}
    }