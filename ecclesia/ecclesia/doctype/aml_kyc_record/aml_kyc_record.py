# Copyright (c) 2026, Value Impacts Consulting
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, add_days, getdate, date_diff


class AmlKycRecord(Document):

    def before_insert(self):
        self._set_amlco_from_company()
        self._set_kyc_expiry()

    def validate(self):
        self._validate_edd_requirement()
        self._validate_sanctions_block()
        self._auto_set_kyc_level()
        self._set_kyc_expiry()

    def on_submit(self):
        self._notify_amlco()
        if self.risk_rating in ("High", "PEP — High", "Sanctioned — Blocked"):
            self._send_risk_alert()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_amlco_from_company(self):
        if not self.approval_officer and self.company:
            amlco = frappe.db.get_value("Company", self.company, "amlco")
            if amlco:
                self.approval_officer = amlco

    def _set_kyc_expiry(self):
        """KYC review periods: Low=2yr, Medium=1yr, High/PEP=6mo, Sanctioned=blocked."""
        if not self.kyc_date or self.kyc_expiry_date:
            return
        expiry_days = {
            "Low": 730, "Medium": 365,
            "High": 180, "PEP — High": 180,
            "Sanctioned — Blocked": 0
        }
        days = expiry_days.get(self.risk_rating, 365)
        if days > 0:
            self.kyc_expiry_date = add_days(self.kyc_date, days)

    def _validate_edd_requirement(self):
        """PEP or High risk requires EDD level — warn if SDD/CDD is set."""
        if self.risk_rating in ("PEP — High", "High") and \
           self.kyc_level != "Enhanced Due Diligence (EDD)":
            frappe.msgprint(
                _("Enhanced Due Diligence (EDD) is required for High Risk and PEP parties "
                  "under the Money Laundering (Prevention and Prohibition) Act 2022. "
                  "Please update KYC Level to EDD."),
                indicator="red", title=_("EDD Required")
            )

    def _validate_sanctions_block(self):
        """Hard block: sanctioned parties cannot be approved."""
        if self.risk_rating == "Sanctioned — Blocked" and self.docstatus == 1:
            frappe.throw(
                _("This record cannot be submitted. The party '{0}' has been matched "
                  "to a sanctioned entity. All transactions must be blocked. "
                  "Contact the AMLCO and legal counsel immediately.").format(
                      self.party_name_display
                  )
            )

    def _auto_set_kyc_level(self):
        """Auto-upgrade KYC level based on risk rating."""
        if self.risk_rating == "Sanctioned — Blocked":
            frappe.throw(_("Sanctioned parties cannot have KYC records created. Contact AMLCO."))
        if self.risk_rating == "PEP — High" and \
           self.kyc_level != "Enhanced Due Diligence (EDD)":
            self.kyc_level = "Enhanced Due Diligence (EDD)"

    def _notify_amlco(self):
        if not self.approval_officer:
            return
        email = frappe.db.get_value("Employee", self.approval_officer, "company_email")
        if not email:
            return
        
        subject = _("KYC Record Submitted for Approval: {0} [{1}]").format(
            self.party_name_display, self.risk_rating
        )
        
        message = _("""
            <p>An AML/KYC Record has been submitted and requires your review.</p>
            <table cellpadding="6" style="font-size:13px">
              <tr><td><b>Party:</b></td><td>{0}</td></tr>
              <tr><td><b>Party Type:</b></td><td>{1}</td></tr>
              <tr><td><b>Risk Rating:</b></td><td><b>{2}</b></td></tr>
              <tr><td><b>KYC Level:</b></td><td>{3}</td></tr>
              <tr><td><b>KYC Expiry:</b></td><td>{4}</td></tr>
              <tr><td><b>PEP:</b></td><td>{5}</td></tr>
              <tr><td><b>Sanctions Match:</b></td><td>{6}</td></tr>
            </table>
            <p><a href="/Form/AML KYC Record/{7}">Review KYC Record →</a></p>
        """).format(
            self.party_name_display, self.party_type, self.risk_rating,
            self.kyc_level, self.kyc_expiry_date or "—",
            "YES ⚠️" if self.is_pep else "No",
            "YES 🚨" if self.sanctions_match else "No",
            self.name
        )
        
        frappe.sendmail(
            recipients=[email],
            subject=subject,
            message=message
        )

    def _send_risk_alert(self):
        """Send risk alert email - with fallback if email templates not available."""
        try:
            from ecclesia.api.compliance.email_templates import (
                render_aml_risk_alert, send_compliance_email
            )
            
            emails = []
            for field in ["responsible_officer", "approval_officer"]:
                emp = self.get(field)
                if emp:
                    e = frappe.db.get_value("Employee", emp, "company_email")
                    if e and e not in emails:
                        emails.append(e)
            
            if emails:
                html = render_aml_risk_alert(self)
                send_compliance_email(
                    recipients=emails,
                    subject="AML High-Risk Alert: {0} [{1}]".format(
                        self.party_name_display, self.risk_rating
                    ),
                    html_body=html
                )
        except ImportError:
            # Fallback: send simple email if templates not available
            frappe.log_error(
                title="AML Risk Alert - Templates Missing",
                message="Email templates not found for AML KYC Record {0}".format(self.name)
            )
            self._send_simple_risk_alert()
        except Exception as e:
            frappe.log_error(
                title="AML Risk Alert Error",
                message="Error sending risk alert for {0}: {1}".format(self.name, str(e))
            )

    def _send_simple_risk_alert(self):
        """Simple fallback risk alert email."""
        emails = []
        for field in ["responsible_officer", "approval_officer"]:
            emp = self.get(field)
            if emp:
                e = frappe.db.get_value("Employee", emp, "company_email")
                if e and e not in emails:
                    emails.append(e)
        
        if emails:
            frappe.sendmail(
                recipients=emails,
                subject="AML High-Risk Alert: {0} [{1}]".format(
                    self.party_name_display, self.risk_rating
                ),
                message="""
                    <h3>AML High-Risk Alert</h3>
                    <p>A high-risk party requires immediate attention:</p>
                    <ul>
                        <li><b>Party:</b> {0}</li>
                        <li><b>Risk Rating:</b> {1}</li>
                        <li><b>KYC Level:</b> {2}</li>
                        <li><b>PEP:</b> {3}</li>
                        <li><b>Sanctions Match:</b> {4}</li>
                    </ul>
                    <p><a href="/Form/AML KYC Record/{5}">Review KYC Record →</a></p>
                """.format(
                    self.party_name_display,
                    self.risk_rating,
                    self.kyc_level,
                    "YES ⚠️" if self.is_pep else "No",
                    "YES 🚨" if self.sanctions_match else "No",
                    self.name
                )
            )


@frappe.whitelist()
def get_kyc_expiring_soon(company, days=30):
    """Return KYC records expiring within N days."""
    try:
        days = int(days)
    except (ValueError, TypeError):
        days = 30
    
    cutoff = add_days(nowdate(), days)
    return frappe.db.get_all(
        "AML KYC Record",
        filters={
            "company": company,
            "docstatus": 1,
            "kyc_expiry_date": ["between", [nowdate(), cutoff]]
        },
        fields=["name", "party_name_display", "party_type", "risk_rating",
                "kyc_level", "kyc_expiry_date", "responsible_officer"],
        order_by="kyc_expiry_date asc"
    )


@frappe.whitelist()
def get_high_risk_parties(company):
    """Return all High/PEP/Sanctioned parties."""
    return frappe.db.get_all(
        "AML KYC Record",
        filters={
            "company": company,
            "docstatus": 1,
            "risk_rating": ["in", ["High", "PEP — High", "Sanctioned — Blocked"]]
        },
        fields=["name", "party_name_display", "party_type", "risk_rating",
                "kyc_expiry_date", "sanctions_match", "is_pep"],
        order_by="risk_rating desc"
    )