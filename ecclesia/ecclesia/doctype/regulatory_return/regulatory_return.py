# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, flt, add_days


class RegulatoryReturn(Document):

    def validate(self):
        self._check_late_flag()
        self._validate_title()

    def on_submit(self):
        self._update_status_on_submit()
        self._create_cll_if_penalty()
        self._send_submission_confirmation()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _validate_title(self):
        if not self.return_title:
            self.return_title = f"{self.return_type} — {self.period_covered or ''} — {self.company}"

    def _check_late_flag(self):
        if self.submission_date and self.due_date:
            late = getdate(self.submission_date) > getdate(self.due_date)
            self.late_flag = 1 if late else 0
            if late:
                self.status = "Late Submitted"
                if self.penalty_for_non_filing:
                    self.penalty_incurred = flt(self.penalty_for_non_filing)
                frappe.msgprint(
                    _(f"⚠️ This return was submitted after the due date ({self.due_date}). "
                      f"Penalty of ₦{flt(self.penalty_for_non_filing):,.0f} may be applicable."),
                    indicator="orange", alert=True
                )
        elif not self.submission_date and self.due_date:
            if getdate(self.due_date) < getdate(nowdate()):
                self.status = "Overdue"
                self.late_flag = 1

    def _update_status_on_submit(self):
        if self.submission_date:
            self.db_set("status",
                        "Late Submitted" if self.late_flag else "Submitted")

    def _create_cll_if_penalty(self):
        """If a penalty was incurred, create/update a CLL entry."""
        if not self.penalty_incurred or not self.cll_entry:
            return
        try:
            cll = frappe.get_doc("Compliance Liability Ledger", self.cll_entry)
            if flt(cll.total_liability) < flt(self.penalty_incurred):
                cll.append("source_lines", {
                    "source_doctype": "Regulatory Return",
                    "source_document": self.name,
                    "posting_date": nowdate(),
                    "gross_amount": 0,
                    "liability_amount": flt(self.penalty_incurred),
                    "remarks": f"Late filing penalty for {self.return_type}"
                })
                cll.save(ignore_permissions=True)
        except Exception:
            pass

    def _send_submission_confirmation(self):
        if not self.filed_by:
            return
        email = frappe.db.get_value("Employee", self.filed_by, "company_email")
        if not email:
            return
        frappe.sendmail(
            recipients=[email],
            subject=_(f"Regulatory Return Submitted: {self.return_title}"),
            message=_("""
                <p>Regulatory Return <b>{0}</b> has been submitted.</p>
                <table cellpadding="6" style="font-size:13px">
                  <tr><td><b>Authority:</b></td><td>{1}</td></tr>
                  <tr><td><b>Period:</b></td><td>{2}</td></tr>
                  <tr><td><b>Submission Date:</b></td><td>{3}</td></tr>
                  <tr><td><b>Status:</b></td><td>{4}</td></tr>
                  <tr><td><b>Reference:</b></td><td>{5}</td></tr>
                  {6}
                </table>
                <p><a href="/Form/Regulatory Return/{7}">View Return →</a></p>
            """).format(
                self.return_title, self.authority, self.period_covered or "—",
                self.submission_date or "—", self.status, self.return_reference or "Pending",
                f"<tr><td><b>Penalty:</b></td><td style='color:red'>₦{flt(self.penalty_incurred):,.0f}</td></tr>"
                if self.penalty_incurred else "",
                self.name
            )
        )


@frappe.whitelist()
def get_regulatory_returns_dashboard(company):
    returns = frappe.db.get_all(
        "Regulatory Return",
        filters={"company": company},
        fields=["name","return_title","authority","status","due_date",
                "late_flag","penalty_incurred","industry_category"]
    )
    return {
        "total":     len(returns),
        "overdue":   sum(1 for r in returns if r.status == "Overdue"),
        "late":      sum(1 for r in returns if r.late_flag),
        "pending":   sum(1 for r in returns if r.status in ("Pending","Preparing")),
        "penalty_total": sum(flt(r.penalty_incurred or 0) for r in returns),
        "records":   returns
    }

