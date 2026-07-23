# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt


# ══════════════════════════════════════════════════════════════════════════════
# conflict_of_interest_declaration.py
# ecclesia/ecclesia/doctype/conflict_of_interest_declaration/conflict_of_interest_declaration.py
# ══════════════════════════════════════════════════════════════════════════════


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, add_days


class ConflictOfInterestDeclaration(Document):

    def before_insert(self):
        self._set_title()
        self._pull_employee_details()

    def validate(self):
        self._set_title()
        self._set_next_review()

    def on_submit(self):
        self._notify_line_manager()
        if self.has_conflict and self.financial_interest:
            self._notify_compliance_officer()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_title(self):
        if not self.declaration_title and self.employee and self.declaration_type:
            emp_name = frappe.db.get_value("Employee", self.employee, "employee_name") or self.employee
            self.declaration_title = f"{emp_name} — {self.declaration_type} — {self.declaration_date or nowdate()}"

    def _pull_employee_details(self):
        if self.employee and not self.designation:
            details = frappe.db.get_value(
                "Employee", self.employee,
                ["designation", "department", "company"], as_dict=True
            )
            if details:
                self.designation = details.designation
                if not self.department:
                    self.department = details.department
                if not self.company:
                    self.company = details.company

    def _set_next_review(self):
        if not self.next_review_date:
            self.next_review_date = add_days(self.declaration_date or nowdate(), 365)

    def _notify_line_manager(self):
        """Send review request to line manager."""
        if not self.acknowledged_by:
            # Try to find reporting manager
            manager = frappe.db.get_value("Employee", self.employee, "reports_to")
            if manager:
                self.db_set("acknowledged_by", manager)

        reviewer = self.acknowledged_by
        if not reviewer:
            return
        email = frappe.db.get_value("Employee", reviewer, "company_email")
        if not email:
            return

        from ecclesia.api.compliance.email_templates import (
            render_coi_review_request, send_compliance_email
        )
        html = render_coi_review_request(self)
        send_compliance_email(
            recipients=[email],
            subject=f"COI Declaration for Review: {self.employee} — {'CONFLICT DECLARED' if self.has_conflict else 'No Conflict'}",
            html_body=html
        )

    def _notify_compliance_officer(self):
        co = frappe.db.get_value("Company", self.company, "compliance_officer")
        if not co:
            return
        email = frappe.db.get_value("Employee", co, "company_email")
        if not email:
            return
        frappe.sendmail(
            recipients=[email],
            subject=_(f"⚠️ Conflict of Interest with Financial Interest: {self.employee}"),
            message=_("""
                <p>A Conflict of Interest declaration has been submitted with a financial interest declared.</p>
                <p><b>Employee:</b> {0}<br>
                <b>Conflict Type:</b> {1}<br>
                <b>Financial Value:</b> ₦{2:,.0f}<br>
                <b>Recusal Required:</b> {3}</p>
                <p><a href="/Form/Conflict of Interest Declaration/{4}">Review Declaration →</a></p>
            """).format(
                self.employee, self.conflict_type or "—",
                float(self.financial_value or 0),
                "YES" if self.recusal_required else "No",
                self.name
            )
        )


@frappe.whitelist()
def get_coi_dashboard(company, fiscal_year=None):
    filters = {"company": company}
    if fiscal_year:
        filters["fiscal_year"] = fiscal_year
    declarations = frappe.db.get_all(
        "Conflict of Interest Declaration",
        filters=filters,
        fields=["name","employee","has_conflict","approval_status","declaration_type","fiscal_year"]
    )
    return {
        "total":          len(declarations),
        "with_conflict":  sum(1 for d in declarations if d.has_conflict),
        "pending_review": sum(1 for d in declarations if d.approval_status == "Pending"),
        "annual":         sum(1 for d in declarations if d.declaration_type == "Annual Declaration")
    }

