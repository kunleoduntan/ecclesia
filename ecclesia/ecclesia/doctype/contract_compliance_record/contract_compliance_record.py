# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/ecclesia/doctype/contract_compliance_record/contract_compliance_record.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, date_diff, add_days, flt


class ContractComplianceRecord(Document):

    def before_insert(self):
        self._pull_from_service_contract()

    def validate(self):
        self._pull_from_service_contract()
        self._compute_compliance_status()
        self._set_next_review()

    def on_update(self):
        self._alert_on_breach()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _pull_from_service_contract(self):
        """Auto-populate vendor, dates, value from the linked Service Contract."""
        if not self.service_contract:
            return
        try:
            sc = frappe.db.get_value(
                "Service Contract",
                self.service_contract,
                ["vendor", "contract_start_date", "contract_end_date",
                 "contract_value", "contract_type"],
                as_dict=True
            )
            if not sc:
                return
            if not self.vendor:
                self.vendor = sc.get("vendor") or sc.get("supplier") or ""
            if not self.contract_start:
                self.contract_start = sc.get("contract_start_date")
            if not self.contract_end:
                self.contract_end = sc.get("contract_end_date")
            if not self.contract_value:
                self.contract_value = flt(sc.get("contract_value") or 0)
            if not self.contract_type:
                self.contract_type = sc.get("contract_type") or ""
        except Exception:
            pass  # Service Contract DocType may not have exact same fieldnames

    def _compute_compliance_status(self):
        """Derive compliance_status from SLA %, open breaches, and expiry."""
        # Expired?
        if self.contract_end and getdate(self.contract_end) < getdate(nowdate()):
            self.compliance_status = "Expired"
            return

        sla = flt(self.sla_compliance_pct)
        breaches = int(self.open_breaches or 0)

        if sla >= 95 and breaches == 0 and self.obligations_met:
            self.compliance_status = "Compliant"
        elif sla >= 80 and breaches <= 2:
            self.compliance_status = "Minor Breach"
        elif sla >= 60 or breaches <= 5:
            self.compliance_status = "Material Breach"
        else:
            self.compliance_status = "Termination Risk"

        # Insurance check
        if self.insurance_current and self.insurance_expiry:
            if getdate(self.insurance_expiry) < getdate(nowdate()):
                self.insurance_current = 0
                frappe.msgprint(
                    _("Vendor insurance has expired. 'Insurance Current' has been unchecked."),
                    indicator="red", alert=True
                )

    def _set_next_review(self):
        """Compute next_review_date from last_review_date + frequency."""
        if not self.last_review_date or not self.review_frequency:
            return
        freq_days = {
            "Monthly": 30, "Quarterly": 90,
            "Bi-Annual": 180, "Annual": 365
        }
        days = freq_days.get(self.review_frequency, 90)
        self.next_review_date = add_days(self.last_review_date, days)

    def _alert_on_breach(self):
        """Send email if status moves to Material Breach or Termination Risk."""
        if self.compliance_status not in ("Material Breach", "Termination Risk"):
            return

        officer = self.responsible_officer
        if not officer:
            return
        email = frappe.db.get_value("Employee", officer, "company_email")
        if not email:
            return

        from ecclesia.api.compliance.email_templates import (
            render_contract_breach_alert, send_compliance_email
        )
        html = render_contract_breach_alert(self)
        send_compliance_email(
            recipients=[email],
            subject=f"⚠️ Contract Compliance Alert: {self.compliance_title} — {self.compliance_status}",
            html_body=html
        )


@frappe.whitelist()
def get_contract_compliance_summary(company):
    """Dashboard data: counts by compliance_status for a company."""
    data = frappe.db.sql("""
        SELECT compliance_status, COUNT(*) AS count
        FROM `tabContract Compliance Record`
        WHERE company = %s
        GROUP BY compliance_status
    """, (company,), as_dict=True)
    return {r.compliance_status: r.count for r in data}


@frappe.whitelist()
def contracts_expiring_soon(company, days=60):
    """Return contracts expiring within N days."""
    cutoff = add_days(nowdate(), int(days))
    return frappe.db.get_all(
        "Contract Compliance Record",
        filters={
            "company": company,
            "contract_end": ["between", [nowdate(), cutoff]],
            "compliance_status": ["!=", "Expired"]
        },
        fields=["name", "compliance_title", "vendor", "contract_end",
                "compliance_status", "contract_value", "responsible_officer"],
        order_by="contract_end asc"
    )