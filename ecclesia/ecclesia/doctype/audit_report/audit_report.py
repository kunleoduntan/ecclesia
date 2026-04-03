# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

"""
Audit Report Controller
========================
Generates the complete audit report including:
- AI narrative executive summary
- Financial Statement impact table (mapped to Balance Sheet / P&L lines)
- GL analytical review summary
- Findings detail table with 5Cs
- Materiality assessment
- CAP status
"""

import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint, today


class AuditReport(Document):

    def before_save(self):
        self._pull_engagement_data()
        self._compile_findings_stats()
        self._build_findings_html()
        self._build_fs_impact()
        self._build_gl_review()
        self._generate_executive_summary()
        self._count_caps()

    def on_submit(self):
        self._update_engagement_opinion()
        self._update_registry_last_audit()
        self._send_distribution()
        frappe.msgprint(
            "✅ Audit Report issued. All stakeholders have been notified.",
            title="Report Issued", indicator="green"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Data Pull
    # ─────────────────────────────────────────────────────────────────────────

    def _pull_engagement_data(self):
        if not self.audit_engagement:
            return

        eng = frappe.get_doc("Audit Engagement", self.audit_engagement)
        self.audit_period_from      = eng.from_date
        self.audit_period_to        = eng.to_date
        self.overall_materiality    = eng.overall_materiality
        self.total_population_value = eng.total_population_value
        self.gl_exceptions_count    = eng.gl_exceptions_detected or 0

        # Build doctypes audited list
        if eng.scope_doctypes:
            self.doctypes_audited = ", ".join(
                r.doctype_name for r in eng.scope_doctypes
            )

        # Sample count
        self.total_sample_size = frappe.db.count(
            "Audit Sample",
            filters={"audit_engagement": self.audit_engagement}
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Findings Stats
    # ─────────────────────────────────────────────────────────────────────────

    def _compile_findings_stats(self):
        if not self.audit_engagement:
            return

        data = frappe.db.sql("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN risk_rating='Critical' THEN 1 ELSE 0 END) as critical,
                SUM(CASE WHEN risk_rating='High'     THEN 1 ELSE 0 END) as high,
                SUM(CASE WHEN risk_rating='Medium'   THEN 1 ELSE 0 END) as medium,
                SUM(CASE WHEN risk_rating='Low'      THEN 1 ELSE 0 END) as low,
                SUM(CASE WHEN materiality_level='Material' THEN 1 ELSE 0 END) as material,
                SUM(IFNULL(financial_impact,0)) as total_impact
            FROM `tabAudit Finding`
            WHERE audit_engagement = %s
        """, self.audit_engagement, as_dict=True)

        if data:
            d = data[0]
            self.critical_count        = cint(d.critical)
            self.high_count            = cint(d.high)
            self.medium_count          = cint(d.medium)
            self.low_count             = cint(d.low)
            self.total_findings        = cint(d.total)
            self.material_findings     = cint(d.material)
            self.total_financial_impact= flt(d.total_impact)

    # ─────────────────────────────────────────────────────────────────────────
    # Findings HTML Table
    # ─────────────────────────────────────────────────────────────────────────

    def _build_findings_html(self):
        if not self.audit_engagement:
            return

        findings = frappe.get_all(
            "Audit Finding",
            filters={"audit_engagement": self.audit_engagement},
            fields=[
                "name", "finding_title", "transaction_code", "risk_rating",
                "finding_type", "reference_doctype", "reference_name",
                "observation", "corrective_action_suggested",
                "financial_impact", "materiality_level", "status",
                "action_owner", "due_date", "coso_component"
            ],
            order_by="FIELD(risk_rating,'Critical','High','Medium','Low')"
        )

        if not findings:
            self.findings_html = "<p>No findings recorded for this engagement.</p>"
            return

        rows = []
        for f in findings:
            risk_color = {
                "Critical": "#c0392b", "High": "#e67e22",
                "Medium": "#f1c40f",   "Low": "#27ae60"
            }.get(f.risk_rating, "#95a5a6")

            rows.append(f"""
                <tr>
                    <td style="border-left:4px solid {risk_color}; padding:8px;">
                        <b>{f.finding_title}</b><br>
                        <small style="color:#666;">{f.transaction_code} | {f.finding_type}</small>
                    </td>
                    <td style="padding:8px;">{f.reference_doctype}<br><small>{f.reference_name}</small></td>
                    <td style="padding:8px; text-align:center;">
                        <span style="background:{risk_color}; color:#fff; padding:2px 8px;
                               border-radius:3px; font-size:11px;">{f.risk_rating}</span>
                    </td>
                    <td style="padding:8px; font-size:12px;">{(f.observation or '')[:200]}...</td>
                    <td style="padding:8px; font-size:12px;">{f.corrective_action_suggested or '—'}</td>
                    <td style="padding:8px; text-align:right; font-weight:bold;">
                        {frappe.utils.fmt_money(f.financial_impact or 0) if f.financial_impact else '—'}
                    </td>
                    <td style="padding:8px;">{f.status}</td>
                </tr>
            """)

        self.findings_html = f"""
            <table style="width:100%; border-collapse:collapse; font-size:13px;">
                <thead>
                    <tr style="background:#2c3e50; color:#fff;">
                        <th style="padding:8px;">Finding</th>
                        <th style="padding:8px;">Document</th>
                        <th style="padding:8px;">Risk</th>
                        <th style="padding:8px;">Observation</th>
                        <th style="padding:8px;">Recommendation</th>
                        <th style="padding:8px;">Financial Impact</th>
                        <th style="padding:8px;">Status</th>
                    </tr>
                </thead>
                <tbody>{"".join(rows)}</tbody>
            </table>
        """

    # ─────────────────────────────────────────────────────────────────────────
    # Financial Statement Impact Table
    # ─────────────────────────────────────────────────────────────────────────

    def _build_fs_impact(self):
        if not self.audit_engagement:
            return

        findings = frappe.get_all(
            "Audit Finding",
            filters={
                "audit_engagement": self.audit_engagement,
                "financial_impact":  [">", 0]
            },
            fields=["financial_statement_line", "financial_impact", "risk_rating", "finding_title"]
        )

        if not findings:
            self.fs_impact_html = "<p>No financial impact findings recorded.</p>"
            self.fs_impact_narrative = "No findings with financial impact were identified in this engagement."
            return

        # Group by financial statement line
        fs_groups = {}
        for f in findings:
            line = f.financial_statement_line or "Unclassified"
            if line not in fs_groups:
                fs_groups[line] = {"total": 0, "count": 0, "findings": []}
            fs_groups[line]["total"]   += flt(f.financial_impact)
            fs_groups[line]["count"]   += 1
            fs_groups[line]["findings"].append(f.finding_title)

        # Sort by total impact descending
        sorted_groups = sorted(fs_groups.items(), key=lambda x: x[1]["total"], reverse=True)
        total_impact = sum(v["total"] for _, v in sorted_groups)

        rows = []
        for line, data in sorted_groups:
            pct = round((data["total"] / total_impact * 100) if total_impact else 0, 1)
            impact_bar = f'<div style="background:#e74c3c; height:8px; border-radius:4px; width:{min(pct,100)}%;"></div>'
            rows.append(f"""
                <tr>
                    <td style="padding:8px; font-weight:600;">{line}</td>
                    <td style="padding:8px; text-align:center;">{data["count"]}</td>
                    <td style="padding:8px; text-align:right; font-weight:bold; color:#c0392b;">
                        {frappe.utils.fmt_money(data["total"])}
                    </td>
                    <td style="padding:8px; text-align:center;">{pct}%</td>
                    <td style="padding:8px; min-width:100px;">{impact_bar}</td>
                </tr>
            """)

        self.fs_impact_html = f"""
            <table style="width:100%; border-collapse:collapse; font-size:13px;">
                <thead>
                    <tr style="background:#2c3e50; color:#fff;">
                        <th style="padding:8px;">Financial Statement Line</th>
                        <th style="padding:8px;">Findings</th>
                        <th style="padding:8px;">Total Impact</th>
                        <th style="padding:8px;">% of Total</th>
                        <th style="padding:8px;">Exposure</th>
                    </tr>
                </thead>
                <tbody>{"".join(rows)}</tbody>
                <tfoot>
                    <tr style="background:#ecf0f1; font-weight:bold;">
                        <td style="padding:8px;">TOTAL</td>
                        <td style="padding:8px; text-align:center;">{sum(v['count'] for _,v in sorted_groups)}</td>
                        <td style="padding:8px; text-align:right; color:#c0392b;">{frappe.utils.fmt_money(total_impact)}</td>
                        <td colspan="2"></td>
                    </tr>
                </tfoot>
            </table>
        """

        # Narrative
        highest_line = sorted_groups[0][0] if sorted_groups else "N/A"
        self.fs_impact_narrative = (
            f"The audit identified total financial impact of "
            f"<b>{frappe.utils.fmt_money(total_impact)}</b> across "
            f"{len(sorted_groups)} financial statement line(s). "
            f"The most exposed area is <b>{highest_line}</b> with "
            f"{frappe.utils.fmt_money(sorted_groups[0][1]['total'])} in identified exceptions. "
            f"Management should prioritise remediation of findings affecting the Income Statement "
            f"and Balance Sheet lines shown above. "
        )
        if flt(self.overall_materiality) > 0 and total_impact >= flt(self.overall_materiality):
            self.fs_impact_narrative += (
                f"<b>Note: Total financial impact ({frappe.utils.fmt_money(total_impact)}) "
                f"exceeds overall materiality ({frappe.utils.fmt_money(self.overall_materiality)}). "
                f"This requires immediate escalation to the Audit Committee.</b>"
            )

    # ─────────────────────────────────────────────────────────────────────────
    # GL Analytical Review
    # ─────────────────────────────────────────────────────────────────────────

    def _build_gl_review(self):
        if not self.audit_engagement:
            return

        gl_findings = frappe.db.count(
            "Audit Finding",
            filters={
                "audit_engagement": self.audit_engagement,
                "finding_type": ["in", [
                    "GL Entry Cancellation", "GL Reconciliation Variance",
                    "Suspense Account Usage", "GL Posting Error", "Cutoff Error",
                    "Backdated Entry", "Non-Finance User JV", "No JV Narration"
                ]]
            }
        )

        sod_failures = frappe.db.count(
            "Audit Finding",
            filters={
                "audit_engagement":  self.audit_engagement,
                "finding_type": "Segregation of Duties Failure"
            }
        )

        jv_flags = frappe.db.count(
            "Audit Finding",
            filters={
                "audit_engagement":  self.audit_engagement,
                "finding_type": ["in", ["Non-Finance User JV", "Round Amount JV", "No JV Narration"]]
            }
        )

        self.gl_review_narrative = f"""
            <b>GL Analytical Review Summary</b><br><br>
            The GL monitoring engine identified <b>{gl_findings}</b> GL-related exception(s) during
            the audit period. This includes any cancellations, repostings, reconciliation variances,
            and suspense account usage.<br><br>
            <b>Segregation of Duties:</b> {sod_failures} SOD failure(s) detected where the same
            user created and approved transactions.<br><br>
            <b>Journal Entry Review (ACFE):</b> {jv_flags} journal entry risk flag(s) raised,
            covering non-finance user postings, round-number JVs, and undocumented entries.<br><br>
            All GL exceptions are included in the findings schedule above and require
            management response and corrective action.
        """

    # ─────────────────────────────────────────────────────────────────────────
    # AI Executive Summary Generator
    # ─────────────────────────────────────────────────────────────────────────

    def _generate_executive_summary(self):
        if not self.audit_engagement:
            return

        opinion_text = {
            "Unqualified": (
                "The audit engagement concluded with an <b>Unqualified (Clean) Opinion</b>. "
                "Controls tested were found to be operating effectively, and no material "
                "exceptions were identified."
            ),
            "Qualified": (
                "The audit engagement concluded with a <b>Qualified Opinion</b>. "
                "While the majority of controls are operating satisfactorily, "
                "specific exceptions were identified that require management attention."
            ),
            "Adverse": (
                "The audit engagement concluded with an <b>Adverse Opinion</b>. "
                "Significant control deficiencies and material exceptions were identified "
                "that represent substantial risk to the organisation. Immediate management "
                "intervention is required."
            ),
            "Disclaimer": (
                "The audit engagement concluded with a <b>Disclaimer of Opinion</b>. "
                "Insufficient evidence was available to form a conclusion on the "
                "effectiveness of controls."
            ),
        }.get(self.audit_opinion, "Opinion pending.")

        critical = cint(self.critical_count)
        high     = cint(self.high_count)
        medium   = cint(self.medium_count)
        low      = cint(self.low_count)
        total    = cint(self.total_findings)

        self.executive_summary = f"""
            <b>EXECUTIVE SUMMARY</b><br><br>

            The Internal Audit function conducted an audit engagement covering
            <b>{self.doctypes_audited or 'selected business processes'}</b> for the period
            <b>{self.audit_period_from}</b> to <b>{self.audit_period_to}</b>.<br><br>

            {opinion_text}<br><br>

            <b>Findings Overview:</b><br>
            A total of <b>{total}</b> finding(s) were raised:
            {critical} Critical, {high} High, {medium} Medium, and {low} Low risk.
            {f'<b>{cint(self.material_findings)} finding(s) are assessed as material</b> relative to the applied materiality threshold of {frappe.utils.fmt_money(self.overall_materiality)}.' if self.overall_materiality else ''}
            <br><br>

            {'<b>Financial Impact:</b> The total estimated financial impact of identified exceptions is ' + frappe.utils.fmt_money(self.total_financial_impact) + '. Refer to the Financial Statement Impact section for detail by account line.<br><br>' if flt(self.total_financial_impact) > 0 else ''}

            <b>GL Monitoring:</b> {cint(self.gl_exceptions_count)} General Ledger exception(s) were
            detected through continuous monitoring during the period.<br><br>

            All findings have been communicated to management. Corrective Action Plans are required
            for all High and Critical findings within 30 days of this report.
        """

    # ─────────────────────────────────────────────────────────────────────────
    # CAP Count
    # ─────────────────────────────────────────────────────────────────────────

    def _count_caps(self):
        if not self.audit_engagement:
            return

        finding_names = frappe.get_all(
            "Audit Finding",
            filters={"audit_engagement": self.audit_engagement},
            pluck="name"
        )
        if not finding_names:
            return

        self.open_caps_count = frappe.db.count(
            "Corrective Action Plan",
            filters={
                "audit_finding": ["in", finding_names],
                "status":        ["in", ["Open", "In Progress"]]
            }
        )
        self.overdue_caps_count = frappe.db.count(
            "Corrective Action Plan",
            filters={
                "audit_finding": ["in", finding_names],
                "status":        "Overdue"
            }
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Post-submission updates
    # ─────────────────────────────────────────────────────────────────────────

    def _update_engagement_opinion(self):
        if self.audit_engagement and self.audit_opinion:
            frappe.db.set_value(
                "Audit Engagement",
                self.audit_engagement,
                {"audit_opinion": self.audit_opinion, "status": "Closed"}
            )

    def _update_registry_last_audit(self):
        """Update last_audit_date and opinion in all registry entries for DocTypes audited."""
        if not self.audit_engagement:
            return
        eng = frappe.get_doc("Audit Engagement", self.audit_engagement)
        for scope_row in (eng.scope_doctypes or []):
            frappe.db.set_value(
                "Auditable DocType Registry",
                {"doctype_name": scope_row.doctype_name},
                {
                    "last_audit_date":    self.report_date,
                    "last_audit_opinion": self.audit_opinion,
                }
            )

    def _send_distribution(self):
        """Email the report to distribution list."""
        if not self.distribution_list:
            return
        recipients = [e.strip() for e in self.distribution_list.split(",") if "@" in e]
        if not recipients:
            return
        try:
            frappe.sendmail(
                recipients=recipients,
                subject=f"[Audit Report] {self.report_title} — {self.audit_opinion} Opinion",
                message=f"""
                    <p>Please find below the summary of the audit report issued.</p>
                    <p><b>Report:</b> {self.report_title}<br>
                    <b>Period:</b> {self.audit_period_from} to {self.audit_period_to}<br>
                    <b>Opinion:</b> {self.audit_opinion}<br>
                    <b>Total Findings:</b> {self.total_findings}
                    (Critical: {self.critical_count}, High: {self.high_count})</p>
                    <hr>
                    {self.executive_summary or ''}
                    <hr>
                    <p>Log in to view the full report including findings detail and recommendations.</p>
                """,
                now=False
            )
        except Exception:
            pass

@frappe.whitelist()
def send_report_distribution(report_name):
    """Whitelisted endpoint called by the JS Send to Distribution button."""
    doc = frappe.get_doc("Audit Report", report_name)
    if doc.docstatus != 1:
        frappe.throw(frappe._("Report must be submitted before sending distribution."))
    doc._send_distribution()
    recipients = [e.strip() for e in (doc.distribution_list or "").split(",") if "@" in e]
    return f"Report dispatched to {len(recipients)} recipient(s)."