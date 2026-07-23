"""
Compliance Report
Ecclesia Module

Audit report: for each employee on a WFH day, did they:
  ✓ Have an approved request?
  ✓ Check in (session exists)?
  ✓ Submit a daily summary?
  ✓ Avoid flags?

Used by HR for monthly WFH compliance audits.
"""

import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data    = get_data(filters)
    summary = get_summary(data)
    return columns, data, None, None, summary


def get_columns():
    return [
        {"label": _("Date"),              "fieldname": "date",             "fieldtype": "Date",    "width": 100},
        {"label": _("Employee"),          "fieldname": "employee",         "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": _("Employee Name"),     "fieldname": "employee_name",    "fieldtype": "Data",    "width": 160},
        {"label": _("Department"),        "fieldname": "department",       "fieldtype": "Data",    "width": 120},
        {"label": _("WFH Approved"),      "fieldname": "wfh_approved",     "fieldtype": "Data",    "width": 110},
        {"label": _("Session Exists"),    "fieldname": "session_exists",   "fieldtype": "Data",    "width": 110},
        {"label": _("Hours Logged"),      "fieldname": "hours_logged",     "fieldtype": "Float", "precision": 1, "width": 100},
        {"label": _("Summary Submitted"), "fieldname": "summary_submitted","fieldtype": "Data",    "width": 130},
        {"label": _("Summary Status"),    "fieldname": "summary_status",   "fieldtype": "Data",    "width": 120},
        {"label": _("Activity Points"),   "fieldname": "activity_points",  "fieldtype": "Float", "precision": 0, "width": 120},
        {"label": _("Flagged"),           "fieldname": "flagged",          "fieldtype": "Data",    "width": 80},
        {"label": _("Compliance Score"),  "fieldname": "compliance_score", "fieldtype": "Percent", "width": 130},
        {"label": _("Issues"),            "fieldname": "issues",           "fieldtype": "Data",    "width": 250},
    ]


def get_data(filters):
    conditions = ""
    params = {
        "from_date": filters.get("from_date"),
        "to_date":   filters.get("to_date"),
    }
    if filters.get("employee"):
        conditions += " AND att.employee = %(employee)s"
        params["employee"] = filters["employee"]
    if filters.get("department"):
        conditions += " AND e.department = %(department)s"
        params["department"] = filters["department"]

    # Base: all WFH attendance records
    rows = frappe.db.sql(
        f"""
        SELECT
            att.attendance_date                                 AS date,
            att.employee,
            e.employee_name,
            e.department,
            att.wfh_request,
            s.name                                             AS session_name,
            ROUND(COALESCE(s.total_hours, 0), 1)              AS hours_logged,
            d.name                                             AS summary_name,
            COALESCE(d.status, NULL)                           AS summary_status,
            ROUND(COALESCE(act.total_points, 0), 0)           AS activity_points,
            COALESCE(s.inactivity_flag, 0)                     AS inactivity_flag,
            COALESCE(d.has_inactivity_flag, 0)                AS summary_flagged
        FROM `tabAttendance` att
        JOIN `tabEmployee` e ON e.name = att.employee
        LEFT JOIN `tabWFH Session` s
               ON s.employee = att.employee AND s.date = att.attendance_date AND s.docstatus != 2
        LEFT JOIN `tabWFH Daily Summary` d
               ON d.employee = att.employee AND d.date = att.attendance_date AND d.docstatus != 2
        LEFT JOIN (
            SELECT employee, date, SUM(points) AS total_points
            FROM `tabWork Activity Log`
            GROUP BY employee, date
        ) act ON act.employee = att.employee AND act.date = att.attendance_date
        WHERE att.status = 'Work From Home'
          AND att.docstatus = 1
          AND att.attendance_date BETWEEN %(from_date)s AND %(to_date)s
          {conditions}
        ORDER BY att.attendance_date DESC, att.employee
        """,
        params,
        as_dict=True,
    )

    result = []
    for row in rows:
        issues = []
        score  = 100

        wfh_approved = "✓ Yes" if row.wfh_request else "✗ No"
        if not row.wfh_request:
            issues.append("No approved WFH Request")
            score -= 25

        session_exists = "✓ Yes" if row.session_name else "✗ No"
        if not row.session_name:
            issues.append("No check-in session")
            score -= 30

        summary_submitted = "✓ Yes" if row.summary_name else "✗ No"
        if not row.summary_name:
            issues.append("No daily summary")
            score -= 30

        flagged = "⚑ Yes" if (row.inactivity_flag or row.summary_flagged) else "—"
        if row.inactivity_flag or row.summary_flagged:
            issues.append("Session or summary flagged")
            score -= 15

        result.append({
            "date":             row.date,
            "employee":         row.employee,
            "employee_name":    row.employee_name,
            "department":       row.department,
            "wfh_approved":     wfh_approved,
            "session_exists":   session_exists,
            "hours_logged":     row.hours_logged,
            "summary_submitted":summary_submitted,
            "summary_status":   row.summary_status or "—",
            "activity_points":  row.activity_points,
            "flagged":          flagged,
            "compliance_score": max(score, 0),
            "issues":           "; ".join(issues) if issues else "—",
        })

    return result


def get_summary(data):
    if not data:
        return []
    total   = len(data)
    perfect = sum(1 for r in data if r["compliance_score"] == 100)
    flagged = sum(1 for r in data if r["flagged"] != "—")
    avg_score = round(sum(r["compliance_score"] for r in data) / total, 1) if total else 0

    return [
        {"value": total,     "label": _("Total WFH Days Reviewed"), "datatype": "Int",     "color": "blue"},
        {"value": perfect,   "label": _("Fully Compliant Days"),     "datatype": "Int",     "color": "green"},
        {"value": avg_score, "label": _("Average Compliance Score"), "datatype": "Percent", "color": "purple"},
        {"value": flagged,   "label": _("Flagged Days"),             "datatype": "Int",     "color": "orange"},
    ]
