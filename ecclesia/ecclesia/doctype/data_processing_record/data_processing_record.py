# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/ecclesia/doctype/data_processing_record/data_processing_record.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, add_days, getdate


class DataProcessingRecord(Document):

    def before_insert(self):
        self._set_dpo_from_company()

    def validate(self):
        self._validate_dpia_requirement()
        self._validate_sensitive_data()
        self._set_next_review()

    def on_submit(self):
        self._notify_dpo()

    def on_cancel(self):
        self.db_set("status", "Discontinued")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_dpo_from_company(self):
        if not self.dpo and self.company:
            dpo = frappe.db.get_value("Company", self.company, "dpo")
            if dpo:
                self.dpo = dpo
        if not self.data_controller and self.company:
            self.data_controller = self.company

    def _validate_dpia_requirement(self):
        """
        NDPR requires a DPIA for high-risk processing activities:
        - Sensitive / special category data
        - Large scale processing
        - Automated decision-making
        """
        if self.is_sensitive_data and not self.privacy_impact_done:
            frappe.msgprint(
                _("⚠️ DPIA Recommended: This record involves sensitive/special category data. "
                  "A Data Protection Impact Assessment (DPIA) should be conducted before processing."),
                indicator="orange", title=_("DPIA Required")
            )

    def _validate_sensitive_data(self):
        """Warn if international transfer has no safeguards."""
        if self.international_transfer and not self.transfer_safeguards:
            frappe.msgprint(
                _("International data transfer requires documented safeguards under NDPR Article 43. "
                  "Please complete the 'Transfer Safeguards' field."),
                indicator="red", alert=True
            )

    def _set_next_review(self):
        if not self.last_reviewed:
            self.last_reviewed = nowdate()
        if not self.next_review_date:
            self.next_review_date = add_days(self.last_reviewed, 365)

    def _notify_dpo(self):
        """Notify DPO on submission of a new Data Processing Record."""
        if not self.dpo:
            return
        email = frappe.db.get_value("Employee", self.dpo, "company_email")
        if not email:
            return
        frappe.sendmail(
            recipients=[email],
            subject=_("New Data Processing Record Submitted: {0}").format(self.processing_title),
            message=_("""
                <p>A new Data Processing Record has been submitted for your review.</p>
                <table cellpadding="6" style="font-size:13px;border-collapse:collapse">
                  <tr><td><b>Title:</b></td><td>{0}</td></tr>
                  <tr><td><b>Company:</b></td><td>{1}</td></tr>
                  <tr><td><b>Legal Basis:</b></td><td>{2}</td></tr>
                  <tr><td><b>Sensitive Data:</b></td><td>{3}</td></tr>
                  <tr><td><b>DPIA Done:</b></td><td>{4}</td></tr>
                  <tr><td><b>Retention Period:</b></td><td>{5}</td></tr>
                </table>
                <p><a href="/Form/Data Processing Record/{6}">Review Record →</a></p>
            """).format(
                self.processing_title, self.company, self.legal_basis,
                "Yes" if self.is_sensitive_data else "No",
                "Yes ✅" if self.privacy_impact_done else "No — Review Required ⚠️",
                self.retention_period, self.name
            )
        )


@frappe.whitelist()
def get_processing_records_requiring_review(company):
    """Return records where next_review_date is past or within 30 days."""
    cutoff = add_days(nowdate(), 30)
    return frappe.db.get_all(
        "Data Processing Record",
        filters={
            "company": company,
            "status": "Active",
            "next_review_date": ["<=", cutoff]
        },
        fields=["name", "processing_title", "legal_basis", "is_sensitive_data",
                "privacy_impact_done", "next_review_date", "dpo"],
        order_by="next_review_date asc"
    )
