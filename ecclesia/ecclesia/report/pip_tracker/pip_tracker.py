# ecclesia/report/pip_tracker/pip_tracker.py
import frappe, json
from frappe import _
from frappe.utils import flt, date_diff, nowdate, getdate


def execute(filters=None):
    filters = filters or {}
    return get_columns(), get_data(filters)


def get_columns():
    return [
        {"label":_("PIP Document"),     "fieldname":"pip_name",      "fieldtype":"Link",
         "options":"Performance PIP",   "width":140},
        {"label":_("Employee"),         "fieldname":"employee",      "fieldtype":"Link",
         "options":"Employee",          "width":120},
        {"label":_("Employee Name"),    "fieldname":"employee_name", "fieldtype":"Data", "width":155},
        {"label":_("Department"),       "fieldname":"department",    "fieldtype":"Link",
         "options":"Department",        "width":130},
        {"label":_("Manager"),          "fieldname":"manager",       "fieldtype":"Link",
         "options":"Employee",          "width":120},
        {"label":_("Start Date"),       "fieldname":"start_date",    "fieldtype":"Date", "width":100},
        {"label":_("End Date"),         "fieldname":"end_date",      "fieldtype":"Date", "width":100},
        {"label":_("Days Remaining"),   "fieldname":"days_left",     "fieldtype":"Int",  "width":115},
        {"label":_("Status"),           "fieldname":"status",        "fieldtype":"Data", "width":100},
        {"label":_("Last Check-in"),    "fieldname":"last_checkin",  "fieldtype":"Date", "width":115},
        {"label":_("Check-in Status"),  "fieldname":"checkin_status","fieldtype":"Data", "width":130},
        {"label":_("Objectives Total"), "fieldname":"obj_total",     "fieldtype":"Int",  "width":120},
        {"label":_("Obj. Achieved"),    "fieldname":"obj_achieved",  "fieldtype":"Int",  "width":110},
        {"label":_("Outcome"),          "fieldname":"outcome",       "fieldtype":"Data", "width":150},
    ]


def get_data(filters):
    status_filter = filters.get("status")
    dept_filter   = filters.get("department")
    mgr_filter    = filters.get("manager")

    conds = {}
    if status_filter:
        conds["status"] = status_filter
    else:
        conds["status"] = ["in", ["Active", "Extended", "Passed", "Failed"]]

    pips = frappe.get_all("Performance PIP",
        filters=conds, fields=["name","employee","manager","start_date","end_date",
                                "status","final_outcome"])

    today = getdate(nowdate())
    rows  = []
    for pip in pips:
        doc  = frappe.get_doc("Performance PIP", pip.name)
        emp_data = frappe.db.get_value("Employee", pip.employee,
            ["employee_name","department"], as_dict=True) or {}

        if dept_filter and emp_data.get("department") != dept_filter:
            continue
        if mgr_filter and pip.manager != mgr_filter:
            continue

        checkins = sorted([r for r in (doc.weekly_checkins or []) if r.checkin_date],
                          key=lambda r: r.checkin_date, reverse=True)
        last_ci = checkins[0].checkin_date if checkins else None
        days_since = date_diff(today, last_ci) if last_ci else None
        if days_since is not None:
            ci_status = ("✅ On Track" if days_since <= 7
                         else f"⏳ Overdue ({days_since}d)")
        else:
            ci_status = "⏳ No check-ins"

        obj_total    = len(doc.pip_objectives or [])
        obj_achieved = sum(1 for o in (doc.pip_objectives or [])
                           if getattr(o, "status", "") == "Achieved")

        days_left = (date_diff(pip.end_date, today)
                     if pip.end_date and pip.status in ("Active","Extended") else None)

        rows.append({
            "pip_name":      pip.name,
            "employee":      pip.employee,
            "employee_name": emp_data.get("employee_name",""),
            "department":    emp_data.get("department",""),
            "manager":       pip.manager,
            "start_date":    pip.start_date,
            "end_date":      pip.end_date,
            "days_left":     days_left,
            "status":        pip.status,
            "last_checkin":  last_ci,
            "checkin_status":ci_status,
            "obj_total":     obj_total,
            "obj_achieved":  obj_achieved,
            "outcome":       pip.final_outcome or "In Progress",
        })
    return sorted(rows, key=lambda r: (r["status"], r["employee_name"]))


@frappe.whitelist()
def download_excel(filters=None):
    if isinstance(filters, str):
        filters = json.loads(filters)
    from ecclesia.report.excel_utils import EcclesiaReport
    columns = get_columns()
    data    = get_data(filters or {})
    report  = EcclesiaReport(
        "PIP Tracker Report", filters or {}, columns, data,
        subtitle="Active & Recent Performance Improvement Plans"
    )
    # Outcome summary sheet
    _add_pip_summary(report, data)
    return report.to_response("PIP_Tracker_Report.xlsx")


def _add_pip_summary(report, data):
    try:
        from ecclesia.report.excel_utils import (
            _fill, _font, _align, _bottom_border,
            NAVY, PURPLE, GREEN, AMBER, LGREY, WHITE
        )
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter

        ws = report.wb.create_sheet("PIP Summary")
        ws.sheet_view.showGridLines = False

        stats = {
            "Active":   sum(1 for r in data if r["status"] == "Active"),
            "Extended": sum(1 for r in data if r["status"] == "Extended"),
            "Passed":   sum(1 for r in data if r["status"] == "Passed"),
            "Failed":   sum(1 for r in data if r["status"] == "Failed"),
        }

        ws.merge_cells("B2:E2")
        t = ws["B2"]
        t.value     = "PIP Status Summary"
        t.font      = Font(color="FFFFFF", bold=True, size=12, name="Calibri")
        t.fill      = PatternFill("solid", fgColor=NAVY)
        t.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[2].height = 28
        ws.column_dimensions["A"].width = 3
        ws.column_dimensions["B"].width = 20
        ws.column_dimensions["C"].width = 14
        ws.column_dimensions["D"].width = 14
        ws.column_dimensions["E"].width = 14

        colors = {"Active":"F59E0B","Extended":"7C3AED","Passed":"059669","Failed":"DC2626"}
        row = 4
        for status, count in stats.items():
            ws.row_dimensions[row].height = 24
            sc = ws.cell(row=row, column=2, value=status)
            sc.font      = Font(color="374151", bold=True, size=11, name="Calibri")
            sc.fill      = PatternFill("solid", fgColor="F1F5F9")

            cc = ws.cell(row=row, column=3, value=count)
            cc.font      = Font(color=colors.get(status,"374151"),
                                bold=True, size=14, name="Calibri")
            cc.fill      = PatternFill("solid", fgColor="F1F5F9")
            cc.alignment = Alignment(horizontal="center", vertical="center")
            row += 1
    except Exception:
        frappe.log_error(frappe.get_traceback(), "PIP Summary Sheet Error")
