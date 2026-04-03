# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

"""
Annual Audit Plan — Controller
================================
Manages the organisation-wide annual audit plan document.

Responsibilities:
  ▸ Auto-calculates organisation materiality from three benchmarks
    (revenue / assets / PBT) — takes the most conservative basis
  ▸ AI-scores and ranks the entire audit universe by inherent risk,
    GL exposure, open-findings backlog, and time since last audit
  ▸ Tracks execution progress (planned / in-progress / completed)
    and YTD findings data across all linked engagements
  ▸ Creates Audit Engagements directly from planned rows (via whitelist)
  ▸ On submission, runs AI prioritisation and locks financial inputs

IIA Reference: IIA Standard 2010 — Planning
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint, now, date_diff, today


# ─────────────────────────────────────────────────────────────────────────────
# Materiality benchmark percentages (industry standard)
# ─────────────────────────────────────────────────────────────────────────────
MATERIALITY = {
    "Total Revenue":       0.0075,   # 0.75 %
    "Total Assets":        0.005,    # 0.50 %
    "Profit Before Tax":   0.07,     # 7.00 %
}

# Priority score weights (must total 100)
WEIGHT_RISK          = 40   # Inherent risk rating
WEIGHT_GL            = 15   # GL-posting exposure
WEIGHT_OPEN_FINDINGS = 20   # Backlog of open findings
WEIGHT_RECENCY       = 20   # Time since last audit
WEIGHT_CLASS         = 5    # Classification bonus


class AnnualAuditPlan(Document):

    # ─────────────────────────────────────────────────────────────────────
    # Lifecycle hooks
    # ─────────────────────────────────────────────────────────────────────

    def validate(self):
        self._set_defaults()
        self._calculate_materiality()
        self._update_execution_summary()

    def before_submit(self):
        if not self.planned_engagements:
            frappe.throw(
                _("Cannot approve an Annual Audit Plan with no planned engagements."),
                title=_("Missing Engagement Plan"),
            )
        if not self.chief_audit_executive:
            frappe.throw(
                _("Chief Audit Executive is required before approving the plan."),
            )

    def on_submit(self):
        self._run_ai_prioritisation()
        self.db_set("status", "Approved", update_modified=False)
        frappe.msgprint(
            _("✅ Annual Audit Plan approved. AI prioritisation has been generated."),
            title=_("Plan Approved"),
            indicator="green",
        )

    def on_cancel(self):
        self.db_set("status", "Cancelled", update_modified=False)

    # ─────────────────────────────────────────────────────────────────────
    # Materiality
    # ─────────────────────────────────────────────────────────────────────

    def _set_defaults(self):
        if not self.plan_title and self.plan_year:
            self.plan_title = f"Annual Audit Plan {self.plan_year}"
        if not self.status:
            self.status = "Draft"

    def _calculate_materiality(self):
        """
        ISA 320 / IIA 2320: Calculate planning materiality from prior-year
        financial data using three standard benchmarks.

        Priority: Revenue-based (most common) → Asset-based → PBT-based.
        Uses the first available basis; does not choose the highest,
        which would be less conservative.
        """
        candidates = {}

        if flt(self.total_revenue) > 0:
            candidates["Total Revenue"] = (
                flt(self.total_revenue) * MATERIALITY["Total Revenue"],
                0.75,
            )
        if flt(self.total_assets) > 0:
            candidates["Total Assets"] = (
                flt(self.total_assets) * MATERIALITY["Total Assets"],
                0.50,
            )
        if flt(self.profit_before_tax) > 0:
            candidates["Profit Before Tax"] = (
                flt(self.profit_before_tax) * MATERIALITY["Profit Before Tax"],
                7.00,
            )

        if not candidates:
            return

        # Revenue-based preferred; fall through to next available
        for basis in ["Total Revenue", "Total Assets", "Profit Before Tax"]:
            if basis in candidates:
                mat, pct = candidates[basis]
                self.organisation_materiality    = round(mat, 2)
                self.materiality_basis_used      = basis
                self.materiality_percentage_used = pct
                break

    # ─────────────────────────────────────────────────────────────────────
    # Execution summary
    # ─────────────────────────────────────────────────────────────────────

    def _update_execution_summary(self):
        """Aggregate progress counts from planned engagement rows."""
        if self.is_new():
            return

        rows = self.planned_engagements or []
        self.total_planned     = len(rows)
        self.total_completed   = sum(1 for r in rows if r.status == "Completed")
        self.total_in_progress = sum(1 for r in rows if r.status == "In Progress")

        # Pull findings data from linked engagements
        linked = [r.linked_engagement for r in rows if r.linked_engagement]
        if linked:
            result = frappe.db.sql(
                """
                SELECT
                    COUNT(*)                                              AS total,
                    SUM(risk_rating = 'Critical')                        AS critical
                FROM `tabAudit Finding`
                WHERE audit_engagement IN %(engagements)s
                """,
                {"engagements": linked},
                as_dict=True,
            )
            if result:
                self.total_findings_raised = cint(result[0].total)
                self.critical_findings_ytd = cint(result[0].critical)

        self.open_caps = frappe.db.count(
            "Corrective Action Plan",
            filters={"status": ["in", ["Open", "In Progress", "Overdue"]]},
        )

    # ─────────────────────────────────────────────────────────────────────
    # AI Prioritisation
    # ─────────────────────────────────────────────────────────────────────

    def _run_ai_prioritisation(self):
        """
        Score every registered DocType in the audit universe and rank them
        for inclusion in this year's plan. Writes results to
        ai_prioritisation_summary (HTML table) and updates ai_priority_score
        on each planned engagement row.
        """
        registries = frappe.get_all(
            "Auditable DocType Registry",
            filters={"is_active": 1},
            fields=[
                "doctype_name", "transaction_code", "risk_level",
                "doctype_classification", "is_gl_posting",
                "open_findings_count", "cumulative_findings",
                "last_audit_date", "audit_frequency", "avg_risk_score",
            ],
        )

        if not registries:
            return

        scored = sorted(
            [(compute_priority_score(r), r) for r in registries],
            key=lambda x: x[0],
            reverse=True,
        )

        # Build HTML table
        header = (
            "<table style='width:100%;border-collapse:collapse;font-size:13px;'>"
            "<thead><tr style='background:#2c3e50;color:#fff;'>"
            "<th style='padding:7px 10px;'>#</th>"
            "<th style='padding:7px 10px;text-align:left;'>DocType</th>"
            "<th style='padding:7px 10px;'>Code</th>"
            "<th style='padding:7px 10px;'>Risk</th>"
            "<th style='padding:7px 10px;'>Score</th>"
            "<th style='padding:7px 10px;text-align:left;'>Why</th>"
            "</tr></thead><tbody>"
        )

        risk_colors = {
            "Critical": "#c0392b", "High": "#d35400",
            "Medium": "#f39c12",   "Low": "#27ae60",
        }

        rows_html = []
        for rank, (score, reg) in enumerate(scored[:25], 1):
            bg   = "#fff" if rank % 2 else "#f8f9fa"
            rc   = risk_colors.get(reg.risk_level, "#888")
            why  = build_rationale(reg)
            rows_html.append(
                f"<tr style='background:{bg};'>"
                f"<td style='padding:5px 10px;text-align:center;color:#888;'>{rank}</td>"
                f"<td style='padding:5px 10px;font-weight:600;'>{reg.doctype_name}</td>"
                f"<td style='padding:5px 10px;font-family:monospace;font-size:11px;'>{reg.transaction_code}</td>"
                f"<td style='padding:5px 10px;'>"
                f"<span style='color:{rc};font-weight:700;'>{reg.risk_level}</span></td>"
                f"<td style='padding:5px 10px;text-align:center;font-weight:800;color:{rc};'>{score}</td>"
                f"<td style='padding:5px 10px;font-size:12px;color:#555;'>{why}</td>"
                f"</tr>"
            )

        self.ai_prioritisation_summary = (
            f"<p style='color:#888;font-size:12px;margin-bottom:8px;'>"
            f"Generated: {frappe.utils.now()} &nbsp;·&nbsp; "
            f"{len(registries)} DocTypes scored &nbsp;·&nbsp; "
            f"Showing top 25 by priority score</p>"
            + header
            + "".join(rows_html)
            + "</tbody></table>"
        )
        self.ai_generated_on = now()

        # Update priority scores on planned rows
        score_map = {reg.doctype_name: score for score, reg in scored}
        for row in self.planned_engagements or []:
            dts = [d.strip() for d in (row.doctype_names or "").split(",") if d.strip()]
            if dts:
                row.ai_priority_score = round(
                    sum(score_map.get(d, 0) for d in dts) / len(dts), 1
                )

        self.db_set("ai_prioritisation_summary", self.ai_prioritisation_summary)
        self.db_set("ai_generated_on", self.ai_generated_on)


# ─────────────────────────────────────────────────────────────────────────────
# Scoring helpers
# ─────────────────────────────────────────────────────────────────────────────

def compute_priority_score(reg) -> float:
    """
    0–100 composite priority score for audit scheduling.
    Higher = should be audited sooner this year.
    """
    score = 0.0

    # ── Inherent risk (0–40 pts) ──────────────────────────────────────────
    score += {"Critical": 40, "High": 30, "Medium": 20, "Low": 10}.get(
        reg.risk_level, 15
    )

    # ── GL posting exposure (0–15 pts) ───────────────────────────────────
    if reg.is_gl_posting:
        score += 15

    # ── Open findings backlog (0–20 pts, capped at 7 findings) ───────────
    score += min(cint(reg.open_findings_count) * 3, 20)

    # ── Time since last audit (0–20 pts) ─────────────────────────────────
    if not reg.last_audit_date:
        score += 20                                # Never audited — maximum urgency
    else:
        days = date_diff(today(), reg.last_audit_date)
        score += 20 if days > 365 else 15 if days > 180 else 8 if days > 90 else 2

    # ── Classification weight (0–5 pts) ──────────────────────────────────
    score += {
        "Financial": 5, "Procurement": 4, "HR & Payroll": 3,
        "Inventory & Stock": 3, "Sales": 2, "Custom": 1,
    }.get(reg.doctype_classification, 1)

    return round(min(score, 100), 1)


def build_rationale(reg) -> str:
    parts = []
    if reg.risk_level in ("Critical", "High"):
        parts.append(f"{reg.risk_level} inherent risk")
    if reg.is_gl_posting:
        parts.append("GL-posting")
    n = cint(reg.open_findings_count)
    if n:
        parts.append(f"{n} open finding{'s' if n > 1 else ''}")
    if not reg.last_audit_date:
        parts.append("never audited")
    return "; ".join(parts) or "Standard coverage"


# ─────────────────────────────────────────────────────────────────────────────
# Whitelisted API endpoints
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def run_ai_prioritisation(plan_name: str):
    """
    Trigger AI prioritisation on demand from the form button.
    Callable without submitting the document.
    """
    doc = frappe.get_doc("Annual Audit Plan", plan_name)
    if doc.docstatus == 2:
        frappe.throw(_("Cannot run AI prioritisation on a cancelled plan."))

    doc._run_ai_prioritisation()
    doc._calculate_materiality()
    doc.save(ignore_permissions=True)
    return {
        "status": "ok",
        "generated_on": doc.ai_generated_on,
        "registries_scored": frappe.db.count(
            "Auditable DocType Registry", filters={"is_active": 1}
        ),
    }


@frappe.whitelist()
def create_engagement_from_row(plan_name: str, row_name: str,
                                from_date: str, to_date: str):
    """
    Create an Audit Engagement linked to a planned row and update
    the row's status to 'In Progress'.
    """
    plan = frappe.get_doc("Annual Audit Plan", plan_name)
    row  = next((r for r in plan.planned_engagements if r.name == row_name), None)

    if not row:
        frappe.throw(_("Planned engagement row not found."))
    if row.linked_engagement:
        frappe.throw(
            _(f"An engagement already exists for this row: {row.linked_engagement}")
        )

    eng = frappe.get_doc({
        "doctype":         "Audit Engagement",
        "engagement_title": row.engagement_title,
        "annual_audit_plan": plan_name,
        "from_date":        from_date,
        "to_date":          to_date,
        "lead_auditor":     row.lead_auditor or frappe.session.user,
        "status":           "Planning",
        "overall_materiality": plan.organisation_materiality,
    })
    eng.insert(ignore_permissions=True)

    # Back-link on the planned row
    frappe.db.set_value(
        "Annual Plan Engagement Row", row_name,
        {"linked_engagement": eng.name, "status": "In Progress"},
    )

    return eng.name