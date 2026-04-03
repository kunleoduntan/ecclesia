# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

"""
Audit Finding Controller
=========================
The core output of every audit. Applies materiality classification,
auto-populates transaction codes, and links to GL entries.
"""

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class AuditFinding(Document):

    def before_save(self):
        self._auto_populate_transaction_code()
        self._classify_materiality()
        self._auto_populate_gl_dimension()
        self._auto_populate_coso()

    def _auto_populate_transaction_code(self):
        """Look up the transaction code from the registry."""
        if self.reference_doctype and not self.transaction_code:
            code = frappe.db.get_value(
                "Auditable DocType Registry",
                {"doctype_name": self.reference_doctype},
                "transaction_code"
            )
            if code:
                self.transaction_code = code

    def _classify_materiality(self):
        """
        Classify financial impact against engagement materiality thresholds (ISA 320).
        Materiality: Material > Performance Materiality > Management Letter > Trivial
        """
        if not self.audit_engagement or not self.financial_impact:
            return

        thresholds = frappe.db.get_value(
            "Audit Engagement",
            self.audit_engagement,
            ["overall_materiality", "performance_materiality", "trivial_threshold"],
            as_dict=True
        )
        if not thresholds:
            return

        impact = flt(self.financial_impact)
        overall_mat   = flt(thresholds.overall_materiality)
        perf_mat      = flt(thresholds.performance_materiality)
        trivial       = flt(thresholds.trivial_threshold)

        if impact >= overall_mat:
            self.materiality_level = "Material"
        elif impact >= perf_mat:
            self.materiality_level = "Significant"
        elif impact >= trivial:
            self.materiality_level = "Management Letter"
        else:
            self.materiality_level = "Trivial"

    def _auto_populate_gl_dimension(self):
        """Auto-populate GL account and financial statement line from registry."""
        if self.reference_doctype and not self.financial_statement_line:
            fsl = frappe.db.get_value(
                "Auditable DocType Registry",
                {"doctype_name": self.reference_doctype},
                "financial_statement_line"
            )
            if fsl:
                self.financial_statement_line = fsl

    def _auto_populate_coso(self):
        """Auto-populate COSO component from registry."""
        if self.reference_doctype and not self.coso_component:
            comp = frappe.db.get_value(
                "Auditable DocType Registry",
                {"doctype_name": self.reference_doctype},
                "coso_component"
            )
            if comp:
                self.coso_component = comp

    def on_update(self):
        """Notify auditee when finding is created."""
        if self.is_new() and self.action_owner:
            self._notify_auditee()

    def _notify_auditee(self):
        """Send email notification to action owner."""
        try:
            frappe.sendmail(
                recipients=[frappe.db.get_value("User", self.action_owner, "email")],
                subject=f"[Audit Finding] {self.finding_title} — {self.risk_rating} Risk",
                message=f"""
                    <p>Dear {self.action_owner},</p>
                    <p>An audit finding has been raised that requires your attention.</p>
                    <table border="1" cellpadding="5">
                        <tr><td><b>Finding</b></td><td>{self.finding_title}</td></tr>
                        <tr><td><b>Risk Rating</b></td><td>{self.risk_rating}</td></tr>
                        <tr><td><b>Transaction Code</b></td><td>{self.transaction_code}</td></tr>
                        <tr><td><b>Document</b></td><td>{self.reference_doctype}: {self.reference_name}</td></tr>
                        <tr><td><b>Due Date</b></td><td>{self.due_date or 'Not set'}</td></tr>
                    </table>
                    <p><b>Recommendation:</b><br>{self.corrective_action_suggested or ''}</p>
                    <p>Please log in to provide your management response.</p>
                """,
                now=False
            )
        except Exception:
            pass
