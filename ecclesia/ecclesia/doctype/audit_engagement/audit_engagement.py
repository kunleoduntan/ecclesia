# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

"""
Audit Engagement Controller
=============================
Manages the lifecycle of an audit engagement from planning through reporting.
Integrates AI intelligence, GL analysis, sample selection, and materiality.
"""

import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint, today, add_days
from ecclesia.utils.sample_engine import generate_samples_for_engagement
from ecclesia.utils.gl_monitor import get_gl_summary_for_engagement
from ecclesia.utils.ai_engine import run_anomaly_detection, _csv_to_list


class AuditEngagement(Document):

    def validate(self):
        self._validate_dates()
        self._calculate_materiality()
        self._update_findings_summary()

    def on_submit(self):
        self._generate_ai_intelligence()
        self._auto_generate_samples()
        self._auto_generate_checklists()
        frappe.msgprint(
            "✅ Audit Engagement submitted. Samples and checklists are being generated.",
            title="Engagement Active", indicator="green"
        )

    def _validate_dates(self):
        if self.from_date and self.to_date:
            if self.from_date > self.to_date:
                frappe.throw("Audit Period From date cannot be after To date.")

    def _calculate_materiality(self):
        """Auto-calculate performance materiality and trivial threshold per ISA 320."""
        if self.overall_materiality:
            self.performance_materiality = flt(self.overall_materiality) * 0.75
            self.trivial_threshold       = flt(self.overall_materiality) * 0.05

    def _update_findings_summary(self):
        """Refresh findings count from Audit Finding child records."""
        if not self.name or self.name == "new-audit-engagement-1":
            return

        counts = frappe.db.sql("""
            SELECT
                SUM(CASE WHEN risk_rating = 'Critical' THEN 1 ELSE 0 END) as critical,
                SUM(CASE WHEN risk_rating = 'High'     THEN 1 ELSE 0 END) as high,
                SUM(CASE WHEN risk_rating = 'Medium'   THEN 1 ELSE 0 END) as medium,
                SUM(CASE WHEN risk_rating = 'Low'      THEN 1 ELSE 0 END) as low,
                COUNT(*) as total,
                SUM(CASE WHEN status IN ('Open','In Progress') THEN 1 ELSE 0 END) as open_count
            FROM `tabAudit Finding`
            WHERE audit_engagement = %s
        """, self.name, as_dict=True)

        if counts:
            c = counts[0]
            self.critical_findings = cint(c.critical)
            self.high_findings     = cint(c.high)
            self.medium_findings   = cint(c.medium)
            self.low_findings      = cint(c.low)
            self.total_findings    = cint(c.total)
            self.open_findings     = cint(c.open_count)

    def _generate_ai_intelligence(self):
        """Generate AI risk overview for this engagement's scope."""
        if not self.scope_doctypes:
            return

        risk_lines  = []
        priority_lines = []
        total_anomalies = 0
        total_gl_exceptions = 0
        total_value = 0

        for row in self.scope_doctypes:
            dt = row.doctype_name
            reg = frappe.db.get_value(
                "Auditable DocType Registry",
                {"doctype_name": dt},
                ["doctype_name", "risk_level", "amount_fields", "date_fields",
                 "approval_fields", "is_gl_posting", "transaction_code"],
                as_dict=True
            )
            if not reg:
                continue

            # Get records in date range
            records = self._get_records_in_scope(dt, reg)
            if records:
                # Run anomaly detection
                anomalies = run_anomaly_detection(dt, records, reg)
                total_anomalies += len(anomalies)

                # Sum population value
                amount_field = _csv_to_list(reg.amount_fields or "")
                if amount_field:
                    for r in records:
                        total_value += flt(r.get(amount_field[0], 0))

            risk_lines.append(
                f"• <b>{dt}</b> [{reg.transaction_code}] — Risk: {reg.risk_level}"
            )

            if reg.risk_level in ("Critical", "High"):
                priority_lines.append(
                    f"• <b>{dt}</b>: Prioritize for extensive testing due to {reg.risk_level} risk"
                )

            # GL exceptions
            if reg.is_gl_posting:
                gl_exc = get_gl_summary_for_engagement(dt, self.from_date, self.to_date)
                total_gl_exceptions += gl_exc.get("exceptions", 0)

        self.ai_risk_overview        = "<br>".join(risk_lines)
        self.ai_priority_areas       = "<br>".join(priority_lines)
        self.total_anomalies_detected= total_anomalies
        self.gl_exceptions_detected  = total_gl_exceptions
        self.total_population_value  = total_value
        self.save(ignore_permissions=True)

    def _get_records_in_scope(self, doctype_name, reg):
        """Fetch records within the engagement date range."""
        if not frappe.db.table_exists(f"tab{doctype_name}"):
            return []

        date_field = "posting_date"
        if not frappe.db.has_column(doctype_name, "posting_date"):
            date_field = "creation"

        fields = ["name", "owner", "modified", "modified_by", "creation"]
        for f in _csv_to_list(reg.amount_fields or ""):
            if frappe.db.has_column(doctype_name, f):
                fields.append(f)
        for f in _csv_to_list(reg.approval_fields or ""):
            if frappe.db.has_column(doctype_name, f):
                fields.append(f)

        return frappe.db.get_all(
            doctype_name,
            filters={date_field: ["between", [self.from_date, self.to_date]]},
            fields=list(set(fields)),
            limit=1000
        )

    def _auto_generate_samples(self):
        """Auto-generate audit samples for all DocTypes in scope."""
        frappe.enqueue(
            "ecclesia.utils.sample_engine.generate_samples_for_engagement",
            engagement_name=self.name,
            queue="long",
            timeout=300
        )

    def _auto_generate_checklists(self):
        """Auto-generate checklists from templates for all DocTypes in scope."""
        frappe.enqueue(
            "ecclesia.utils.checklist_generator.generate_checklists_for_engagement",
            engagement_name=self.name,
            queue="long",
            timeout=300
        )
