# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/ecclesia/doctype/corporate_compliance_register/corporate_compliance_register.py
"""
Corporate Compliance Register — Python Controller
Tracks CAC annual return filing, AGM compliance, board meeting records,
and statutory register currency for each company per fiscal year.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, date_diff, flt


class CorporateComplianceRegister(Document):

    def before_insert(self):
        self._set_defaults()

    def validate(self):
        self._validate_dates()
        self._compute_overall_status()
        self._auto_set_cll_entry()

    def on_submit(self):
        self._notify_compliance_officer()

    def on_cancel(self):
        self.db_set("overall_status", "Non-Compliant")

    # ── Private helpers ───────────────────────────────────────────────────────

    def _set_defaults(self):
        """Auto-populate RC number from Company master if available."""
        if self.company and not self.rc_number:
            rc = frappe.db.get_value("Company", self.company, "cac_rc_number")
            if rc:
                self.rc_number = rc

    def _validate_dates(self):
        if self.annual_return_filed_date and self.annual_return_due_date:
            if getdate(self.annual_return_filed_date) > getdate(nowdate()):
                frappe.throw(_("Filing date cannot be in the future."))

    def _compute_overall_status(self):
        """
        Derive overall_status from the combination of all checklist items.
        Critical: CAC annual return overdue → Non-Compliant immediately.
        """
        issues = []

        # CAC Annual Return
        if self.annual_return_status == "Overdue":
            self.overall_status = "Non-Compliant"
            return
        if self.annual_return_status in ("Due", "Late Filed"):
            issues.append("CAC return late/due")

        # Board & governance
        if not self.agm_held_on_time:
            issues.append("AGM not held on time")
        if not self.director_changes_notified:
            issues.append("Director changes not notified")
        if not self.shareholder_changes_notified:
            issues.append("Shareholder changes not notified")
        if not self.registered_address_current:
            issues.append("Registered address not current")
        if not self.statutory_registers_current:
            issues.append("Statutory registers not up to date")

        if not issues:
            self.overall_status = "Compliant"
        elif len(issues) <= 2:
            self.overall_status = "Minor Issues"
        else:
            self.overall_status = "Major Issues"

    def _auto_set_cll_entry(self):
        """
        If annual return status transitions to Late Filed or Overdue,
        ensure a CLL entry exists for the CAC Annual Return obligation.
        """
        if self.annual_return_status not in ("Late Filed", "Overdue"):
            return
        if self.cac_compliance_liability:
            return

        try:
            from ecclesia.api.compliance.liability_engine_v2 import _get_or_create_cll
            import calendar as cal
            due = getdate(self.annual_return_due_date)
            period_label = f"{due.month:02d}-{due.year:04d}"
            cll = _get_or_create_cll(self.company, "CAC Annual Return", period_label)
            # Set a nominal liability if none set (filing fee estimate)
            if flt(cll.total_liability) == 0:
                cll.append("source_lines", {
                    "source_doctype": "Corporate Compliance Register",
                    "source_document": self.name or "New",
                    "posting_date": nowdate(),
                    "gross_amount": 0,
                    "liability_amount": flt(self.annual_return_penalty) or 10000,
                    "remarks": "CAC Annual Return filing fee / penalty estimate"
                })
                cll.save(ignore_permissions=True)
            self.cac_compliance_liability = cll.name
        except Exception as e:
            frappe.log_error(f"CLL auto-set failed for {self.name}: {e}",
                             "Corporate Compliance Register")

    def _notify_compliance_officer(self):
        if self.overall_status in ("Non-Compliant", "Major Issues"):
            co = frappe.db.get_value("Company", self.company, "compliance_officer")
            if co:
                email = frappe.db.get_value("Employee", co, "company_email")
                if email:
                    frappe.sendmail(
                        recipients=[email],
                        subject=_(
                            "⚠️ Corporate Compliance Alert: {0} — {1}"
                        ).format(self.company, self.overall_status),
                        message=_(
                            "Corporate Compliance Register <b>{0}</b> for {1} / {2} "
                            "has been submitted with status: <b>{3}</b>.<br><br>"
                            "CAC Return Status: {4}<br>"
                            "Please review: <a href='/Form/Corporate Compliance Register/{0}'>{0}</a>"
                        ).format(
                            self.name, self.company, self.fiscal_year,
                            self.overall_status, self.annual_return_status
                        )
                    )


# ── Whitelisted helpers ───────────────────────────────────────────────────────

@frappe.whitelist()
def get_cac_due_date(company, fiscal_year):
    """
    CAC annual returns are due by 30 June following the end of the fiscal year
    for most companies, or within 42 days for smaller companies.
    Returns the standard due date for the given fiscal year.
    """
    fy_end = frappe.db.get_value("Fiscal Year", fiscal_year, "year_end_date")
    if not fy_end:
        return None
    end = getdate(fy_end)
    # 30 June of the year following FY end
    return f"{end.year + 1:04d}-06-30"


@frappe.whitelist()
def get_company_register_for_year(company, fiscal_year):
    """Return the existing CCR name for a company/year, or None."""
    return frappe.db.get_value(
        "Corporate Compliance Register",
        {"company": company, "fiscal_year": fiscal_year},
        "name"
    )
