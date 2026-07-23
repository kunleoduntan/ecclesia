# ecclesia/report/cycle_completion_status/cycle_completion_status.py
"""
Cycle Completion Status Report
Shows per-stage submission status for every employee in a performance cycle.
Includes beautiful Excel export with traffic-light colour coding.
"""
import frappe
from frappe import _
from frappe.utils import flt
import json


def execute(filters=None):
    filters = filters or {}
    validate_filters(filters)
    columns = get_columns()
    data    = get_data(filters)
    return columns, data


def validate_filters(filters):
    if not filters.get("cycle"):
        frappe.throw(_("Please select a Performance Cycle."))


def get_columns():
    return [
        {"label":_("Employee ID"),      "fieldname":"employee",       "fieldtype":"Link",
         "options":"Employee",           "width":110},
        {"label":_("Employee Name"),     "fieldname":"employee_name",  "fieldtype":"Data",   "width":160},
        {"label":_("Department"),        "fieldname":"department",     "fieldtype":"Link",
         "options":"Department",         "width":130},
        {"label":_("Designation"),       "fieldname":"designation",    "fieldtype":"Data",   "width":130},
        {"label":_("Goal Set"),          "fieldname":"goal_set",       "fieldtype":"Data",   "width":100},
        {"label":_("Self Appraisal"),    "fieldname":"self_appraisal", "fieldtype":"Data",   "width":120},
        {"label":_("Peer Reviews"),      "fieldname":"peer_reviews",   "fieldtype":"Data",   "width":110},
        {"label":_("Manager Review"),    "fieldname":"manager_review", "fieldtype":"Data",   "width":120},
        {"label":_("KPI Score (%)"),     "fieldname":"kpi_score",      "fieldtype":"Float",  "width":110},
        {"label":_("Composite Score (%)"), "fieldname":"composite_score", "fieldtype":"Float","width":130},
        {"label":_("Performance Band"),  "fieldname":"performance_band", "fieldtype":"Data", "width":140},
        {"label":_("Record Status"),     "fieldname":"status",         "fieldtype":"Data",   "width":110},
    ]


def get_data(filters):
    cycle   = filters.get("cycle")
    dept    = filters.get("department")
    company = frappe.db.get_value("Performance Cycle", cycle, "company")

    emp_filters = {"status": "Active", "company": company}
    if dept:
        emp_filters["department"] = dept

    employees = frappe.get_all("Employee",
        filters=emp_filters,
        fields=["name","employee_name","department","designation"])

    emp_names = [e.name for e in employees]
    if not emp_names:
        return []

    # Pre-fetch all needed data in batch queries
    ph = ",".join(["%s"] * len(emp_names))

    self_done = set(frappe.db.sql_list(f"""
        SELECT DISTINCT employee FROM `tabSelf Appraisal`
        WHERE performance_cycle=%s AND employee IN ({ph}) AND docstatus=1
    """, [cycle] + emp_names))

    mgr_done = set(frappe.db.sql_list(f"""
        SELECT DISTINCT employee FROM `tabManager Review 360`
        WHERE performance_cycle=%s AND employee IN ({ph}) AND docstatus=1
    """, [cycle] + emp_names))

    peer_counts = dict(frappe.db.sql(f"""
        SELECT reviewee, COUNT(*) FROM `tabPeer Review`
        WHERE performance_cycle=%s AND reviewee IN ({ph}) AND docstatus=1
        GROUP BY reviewee
    """, [cycle] + emp_names))

    goal_done = set(frappe.db.sql_list(f"""
        SELECT DISTINCT owner_employee FROM `tabPerformance Goal`
        WHERE performance_cycle=%s AND owner_employee IN ({ph})
          AND status IN ('Approved','In Progress','Completed')
    """, [cycle] + emp_names))

    epr_map = {}
    if emp_names:
        for row in frappe.db.sql(f"""
            SELECT employee, composite_score, kpi_score, status, performance_band
            FROM `tabEmployee Performance Record`
            WHERE cycle=%s AND employee IN ({ph})
        """, [cycle] + emp_names, as_dict=True):
            epr_map[row.employee] = row

    rows = []
    for emp in sorted(employees, key=lambda e: e.employee_name or ""):
        epr = epr_map.get(emp.name, {})
        rows.append({
            "employee":       emp.name,
            "employee_name":  emp.employee_name,
            "department":     emp.department,
            "designation":    emp.designation,
            "goal_set":       "✅ Done"    if emp.name in goal_done   else "⏳ Pending",
            "self_appraisal": "✅ Done"    if emp.name in self_done   else "⏳ Pending",
            "peer_reviews":   f"{peer_counts.get(emp.name, 0)} received",
            "manager_review": "✅ Done"    if emp.name in mgr_done    else "⏳ Pending",
            "kpi_score":      flt(epr.get("kpi_score"))       if epr else 0,
            "composite_score":flt(epr.get("composite_score")) if epr else 0,
            "performance_band": epr.get("performance_band") or "—",
            "status":         epr.get("status") or "Not Created",
        })
    return rows


@frappe.whitelist()
def download_excel(filters=None):
    """Generate and return a styled Excel workbook for download."""
    if isinstance(filters, str):
        filters = json.loads(filters)

    from ecclesia.report.excel_utils import EcclesiaReport

    columns = get_columns()
    data    = get_data(filters or {})
    cycle   = (filters or {}).get("cycle", "")

    report = EcclesiaReport(
        report_title="Cycle Completion Status",
        filters=filters or {},
        columns=columns,
        data=data,
        subtitle=f"Performance Cycle: {cycle}",
    )

    # Add completion bar chart
    # Columns: goal_set=5, self=6, manager=8 → use numeric counts instead
    # We add a summary chart sheet manually
    _add_summary_chart(report)

    return report.to_response(f"CycleCompletion_{cycle}.xlsx")


def _add_summary_chart(report):
    """Add a department-level completion summary sheet."""
    try:
        import openpyxl
        from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
        from ecclesia.report.excel_utils import (
            _fill, _font, _align, _bottom_border, NAVY, PURPLE,
            GREEN, AMBER, LGREY, WHITE, GOLD
        )

        ws = report.wb.create_sheet("Dept Summary")
        ws.sheet_view.showGridLines = False

        headers = ["Department", "Total", "Goals Set", "Self Done",
                   "Manager Done", "Avg Score", "Completion %"]
        widths  = [24, 10, 12, 12, 15, 12, 14]

        ws.row_dimensions[1].height = 30
        for ci, (h, w) in enumerate(zip(headers, widths), 1):
            c = ws.cell(row=1, column=ci, value=h)
            c.font      = Font(color="FFFFFF", bold=True, size=10, name="Calibri")
            c.fill      = PatternFill("solid", fgColor=NAVY)
            c.alignment = Alignment(horizontal="center", vertical="center")
            ws.column_dimensions[get_column_letter(ci)].width = w

        # Aggregate by department
        dept_map = {}
        for row in report.data:
            d = row.get("department") or "No Department"
            if d not in dept_map:
                dept_map[d] = {"total":0,"goals":0,"self":0,"mgr":0,"scores":[]}
            dept_map[d]["total"] += 1
            if "✅" in str(row.get("goal_set", "")):
                dept_map[d]["goals"] += 1
            if "✅" in str(row.get("self_appraisal", "")):
                dept_map[d]["self"] += 1
            if "✅" in str(row.get("manager_review", "")):
                dept_map[d]["mgr"] += 1
            if row.get("composite_score"):
                dept_map[d]["scores"].append(flt(row["composite_score"]))

        for ri, (dept, v) in enumerate(sorted(dept_map.items()), 2):
            shade = LGREY if ri % 2 == 0 else WHITE
            avg   = round(sum(v["scores"]) / len(v["scores"]), 1) if v["scores"] else 0
            comp  = round(v["mgr"] / max(1, v["total"]) * 100, 1)
            for ci, val in enumerate([dept, v["total"], v["goals"],
                                       v["self"], v["mgr"], avg, comp], 1):
                c = ws.cell(row=ri, column=ci, value=val)
                c.fill      = PatternFill("solid", fgColor=shade)
                c.alignment = Alignment(horizontal="center" if ci > 1 else "left",
                                        vertical="center")
                if ci == 7:  # completion %
                    c.number_format = "0.0\"%\""
                    c.font = Font(
                        color=GREEN if comp >= 80 else AMBER if comp >= 50 else "DC2626",
                        bold=True, size=10, name="Calibri"
                    )

        ws.freeze_panes = "A2"
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Cycle Completion Chart Error")
