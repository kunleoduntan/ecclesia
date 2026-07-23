# ecclesia/report/performance_rating_distribution/performance_rating_distribution.py
import frappe, json
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    filters = filters or {}
    if not filters.get("cycle"):
        frappe.throw(_("Please select a Performance Cycle."))
    return get_columns(), get_data(filters)


def get_columns():
    return [
        {"label":_("Department"),        "fieldname":"department",   "fieldtype":"Link",
         "options":"Department",          "width":160},
        {"label":_("Outstanding ≥90%"),  "fieldname":"outstanding",  "fieldtype":"Int","width":120},
        {"label":_("Exceeds 75-89%"),    "fieldname":"exceeds",      "fieldtype":"Int","width":120},
        {"label":_("Meets 60-74%"),      "fieldname":"meets",        "fieldtype":"Int","width":110},
        {"label":_("Needs Improv."),     "fieldname":"needs_imp",    "fieldtype":"Int","width":120},
        {"label":_("Unsatisfactory"),    "fieldname":"unsatis",      "fieldtype":"Int","width":120},
        {"label":_("Total Employees"),   "fieldname":"total",        "fieldtype":"Int","width":120},
        {"label":_("Avg Score (%)"),     "fieldname":"avg_score",    "fieldtype":"Float","width":120},
        {"label":_("Top Score (%)"),     "fieldname":"top_score",    "fieldtype":"Float","width":110},
        {"label":_("Std Dev"),           "fieldname":"std_dev",      "fieldtype":"Float","width":100},
    ]


def get_data(filters):
    cycle = filters.get("cycle")
    dept  = filters.get("department")
    conds = "epr.cycle = %(cycle)s AND epr.status != 'Cancelled'"
    params = {"cycle": cycle}
    if dept:
        conds += " AND emp.department = %(dept)s"
        params["dept"] = dept

    records = frappe.db.sql(f"""
        SELECT emp.department,
               COALESCE(epr.final_rating, epr.calibrated_rating, epr.composite_score, 0) AS score
        FROM `tabEmployee Performance Record` epr
        JOIN `tabEmployee` emp ON emp.name = epr.employee
        WHERE {conds}
        ORDER BY emp.department
    """, params, as_dict=True)

    dept_map = {}
    for r in records:
        d = r.department or "No Department"
        if d not in dept_map:
            dept_map[d] = []
        dept_map[d].append(flt(r.score))

    rows = []
    for dname, scores in sorted(dept_map.items()):
        total = len(scores)
        avg   = round(sum(scores) / total, 1) if total else 0
        top   = round(max(scores), 1) if scores else 0
        mean  = avg
        std_dev = round((sum((s - mean)**2 for s in scores) / max(1, total)) ** 0.5, 1)
        rows.append({
            "department":  dname,
            "outstanding": sum(1 for s in scores if s >= 90),
            "exceeds":     sum(1 for s in scores if 75 <= s < 90),
            "meets":       sum(1 for s in scores if 60 <= s < 75),
            "needs_imp":   sum(1 for s in scores if 40 <= s < 60),
            "unsatis":     sum(1 for s in scores if s < 40),
            "total":       total,
            "avg_score":   avg,
            "top_score":   top,
            "std_dev":     std_dev,
        })

    if len(rows) > 1:
        all_scores = [s for r in records for s in [flt(r.score)]]
        t = sum(r["total"] for r in rows)
        rows.append({
            "department":  "── COMPANY TOTAL ──",
            "outstanding": sum(r["outstanding"] for r in rows),
            "exceeds":     sum(r["exceeds"]     for r in rows),
            "meets":       sum(r["meets"]       for r in rows),
            "needs_imp":   sum(r["needs_imp"]   for r in rows),
            "unsatis":     sum(r["unsatis"]     for r in rows),
            "total":       t,
            "avg_score":   round(sum(all_scores) / max(1, len(all_scores)), 1),
            "top_score":   round(max(all_scores), 1) if all_scores else 0,
            "std_dev":     0,
        })
    return rows


@frappe.whitelist()
def download_excel(filters=None):
    if isinstance(filters, str):
        filters = json.loads(filters)
    from ecclesia.report.excel_utils import EcclesiaReport
    columns = get_columns()
    data    = get_data(filters or {})
    cycle   = (filters or {}).get("cycle", "")
    report  = EcclesiaReport(
        "Performance Rating Distribution", filters or {}, columns, data,
        subtitle=f"Bell curve by department · Cycle: {cycle}"
    )
    # Distribution bar chart
    if len(data) > 1:
        report.add_bar_chart(
            "Rating Distribution by Department",
            cat_col_idx=1,
            val_col_idxes=[2, 3, 4, 5, 6],
            sheet_title="Distribution Chart",
            legend_titles=["Outstanding", "Exceeds", "Meets",
                           "Needs Improvement", "Unsatisfactory"]
        )
    return report.to_response(f"RatingDistribution_{cycle}.xlsx")
