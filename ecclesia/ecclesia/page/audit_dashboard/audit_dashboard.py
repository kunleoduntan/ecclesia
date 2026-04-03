"""Audit Dashboard data API."""
import frappe
from frappe.utils import flt, cint, today, add_months, get_first_day, get_last_day


@frappe.whitelist()
def get_dashboard_data():
    """Return all data needed to render the audit risk dashboard."""
    return {
        "kpis":            _get_kpis(),
        "risk_heatmap":    _get_risk_heatmap(),
        "findings_trend":  _get_findings_trend(),
        "fs_exposure":     _get_fs_exposure(),
        "cap_status":      _get_cap_status(),
        "top_risks":       _get_top_risks(),
        "gl_summary":      _get_gl_summary(),
        "universe_stats":  _get_universe_stats(),
    }


def _get_kpis():
    open_critical = frappe.db.count("Audit Finding", {"risk_rating": "Critical", "status": ["in", ["Open", "In Progress"]]})
    open_high     = frappe.db.count("Audit Finding", {"risk_rating": "High",     "status": ["in", ["Open", "In Progress"]]})
    open_caps     = frappe.db.count("Corrective Action Plan", {"status": ["in", ["Open", "In Progress"]]})
    overdue_caps  = frappe.db.count("Corrective Action Plan", {"status": "Overdue"})
    total_registered = frappe.db.count("Auditable DocType Registry", {"is_active": 1})
    active_engagements = frappe.db.count("Audit Engagement", {"status": ["in", ["Planning", "Fieldwork", "Review"]]})

    total_financial_impact = frappe.db.sql("""
        SELECT SUM(IFNULL(financial_impact, 0)) as total
        FROM `tabAudit Finding`
        WHERE status IN ('Open','In Progress')
        AND financial_impact > 0
    """, as_dict=True)

    return {
        "open_critical":        open_critical,
        "open_high":            open_high,
        "open_caps":            open_caps,
        "overdue_caps":         overdue_caps,
        "total_registered":     total_registered,
        "active_engagements":   active_engagements,
        "total_financial_impact": flt(total_financial_impact[0].total if total_financial_impact else 0),
    }


def _get_risk_heatmap():
    """Risk heatmap: DocType classification × risk level."""
    data = frappe.db.sql("""
        SELECT r.doctype_classification, r.risk_level, COUNT(*) as count,
               SUM(r.open_findings_count) as open_findings
        FROM `tabAuditable DocType Registry` r
        WHERE r.is_active = 1
        GROUP BY r.doctype_classification, r.risk_level
    """, as_dict=True)
    return data


def _get_findings_trend():
    """Monthly findings count for last 12 months."""
    data = frappe.db.sql("""
        SELECT
            DATE_FORMAT(creation, '%%Y-%%m') as month,
            risk_rating,
            COUNT(*) as count
        FROM `tabAudit Finding`
        WHERE creation >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
        GROUP BY DATE_FORMAT(creation, '%%Y-%%m'), risk_rating
        ORDER BY month ASC
    """, as_dict=True)
    return data


def _get_fs_exposure():
    """Financial impact grouped by financial statement line."""
    data = frappe.db.sql("""
        SELECT
            IFNULL(financial_statement_line, 'Unclassified') as fs_line,
            COUNT(*) as findings_count,
            SUM(IFNULL(financial_impact, 0)) as total_impact
        FROM `tabAudit Finding`
        WHERE status IN ('Open','In Progress')
        AND financial_impact > 0
        GROUP BY financial_statement_line
        ORDER BY total_impact DESC
        LIMIT 10
    """, as_dict=True)
    return data


def _get_cap_status():
    """CAP status breakdown."""
    data = frappe.db.sql("""
        SELECT status, COUNT(*) as count,
               SUM(CASE WHEN risk_rating='Critical' THEN 1 ELSE 0 END) as critical_count
        FROM `tabCorrective Action Plan`
        GROUP BY status
    """, as_dict=True)
    return data


def _get_top_risks():
    """Top 10 open findings by risk and financial impact."""
    return frappe.get_all(
        "Audit Finding",
        filters={"status": ["in", ["Open", "In Progress"]]},
        fields=[
            "name", "finding_title", "risk_rating", "reference_doctype",
            "transaction_code", "financial_impact", "due_date",
            "financial_statement_line", "finding_type"
        ],
        order_by="FIELD(risk_rating,'Critical','High','Medium','Low'), financial_impact DESC",
        limit=10
    )


def _get_gl_summary():
    """GL monitoring summary."""
    gl_findings = frappe.db.count(
        "Audit Finding",
        {"finding_type": ["in", [
            "GL Entry Cancellation", "GL Reconciliation Variance",
            "Suspense Account Usage", "Backdated Entry",
            "Non-Finance User JV", "Segregation of Duties Failure"
        ]]}
    )
    cancellations = frappe.db.count("Audit Finding", {"finding_type": "GL Entry Cancellation"})
    sod_failures  = frappe.db.count("Audit Finding", {"finding_type": "Segregation of Duties Failure"})
    return {
        "total_gl_findings":  gl_findings,
        "cancellations":      cancellations,
        "sod_failures":       sod_failures,
    }


def _get_universe_stats():
    """Audit universe coverage stats."""
    total = frappe.db.count("Auditable DocType Registry", {"is_active": 1})
    audited_this_year = frappe.db.count(
        "Auditable DocType Registry",
        {"last_audit_date": [">=", f"{frappe.utils.now_datetime().year}-01-01"]}
    )
    never_audited = frappe.db.count(
        "Auditable DocType Registry",
        {"last_audit_date": ["is", "not set"], "is_active": 1}
    )
    return {
        "total":             total,
        "audited_this_year": audited_this_year,
        "never_audited":     never_audited,
        "coverage_pct":      round((audited_this_year / total * 100) if total else 0, 1),
    }