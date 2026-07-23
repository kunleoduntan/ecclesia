"""
Productivity Report — Daily Activity Detail
Ecclesia Module

Shows per-employee, per-day breakdown of:
  hours, activity count, points, business value,
  top DocType, summary status, composite score.
"""

import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data    = get_data(filters)
    chart   = get_chart(data, filters)
    return columns, data, None, chart


def get_columns():
    return [
        {"label": _("Date"),            "fieldname": "date",            "fieldtype": "Date",     "width": 100},
        {"label": _("Employee"),        "fieldname": "employee",        "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": _("Employee Name"),   "fieldname": "employee_name",   "fieldtype": "Data",     "width": 160},
        {"label": _("Department"),      "fieldname": "department",      "fieldtype": "Data",     "width": 120},
        {"label": _("Hours"),           "fieldname": "hours",           "fieldtype": "Float", "precision": 1, "width": 80},
        {"label": _("Check-In"),        "fieldname": "check_in",        "fieldtype": "Datetime", "width": 140},
        {"label": _("Check-Out"),       "fieldname": "check_out",       "fieldtype": "Datetime", "width": 140},
        {"label": _("Activity Count"),  "fieldname": "activity_count",  "fieldtype": "Int",      "width": 120},
        {"label": _("Points"),          "fieldname": "points",          "fieldtype": "Float", "precision": 0, "width": 80},
        {"label": _("Business Value"),  "fieldname": "business_value",  "fieldtype": "Currency", "width": 130},
        {"label": _("Top Module"),      "fieldname": "top_module",      "fieldtype": "Data",     "width": 100},
        {"label": _("Summary Status"),  "fieldname": "summary_status",  "fieldtype": "Data",     "width": 120},
        {"label": _("Self Rating"),     "fieldname": "self_rating",     "fieldtype": "Float", "precision": 1, "width": 100},
        {"label": _("Composite Score"), "fieldname": "composite_score", "fieldtype": "Float", "precision": 1, "width": 130},
        {"label": _("Session Status"),  "fieldname": "session_status",  "fieldtype": "Data",     "width": 110},
    ]


def get_data(filters):
    conditions = ""
    params = {
        "from_date": filters.get("from_date"),
        "to_date":   filters.get("to_date"),
    }
    if filters.get("employee"):
        conditions += " AND s.employee = %(employee)s"
        params["employee"] = filters["employee"]
    if filters.get("department"):
        conditions += " AND e.department = %(department)s"
        params["department"] = filters["department"]
    if filters.get("module"):
        conditions += " AND EXISTS (SELECT 1 FROM `tabWork Activity Log` am WHERE am.employee=s.employee AND am.date=s.date AND am.module=%(module)s)"
        params["module"] = filters["module"]

    rows = frappe.db.sql(
        f"""
        SELECT
            s.date,
            s.employee,
            e.employee_name,
            e.department,
            ROUND(COALESCE(s.total_hours, 0), 1)               AS hours,
            s.check_in_time                                     AS check_in,
            s.check_out_time                                    AS check_out,
            COALESCE(act.activity_count, 0)                    AS activity_count,
            ROUND(COALESCE(act.total_points, 0), 0)            AS points,
            ROUND(COALESCE(act.total_value, 0), 2)             AS business_value,
            act.top_module,
            COALESCE(d.status, 'No Summary')                   AS summary_status,
            COALESCE(d.self_rating, 0)                         AS self_rating,
            ROUND(COALESCE(d.composite_score, 0), 1)           AS composite_score,
            s.status                                            AS session_status
        FROM `tabWFH Session` s
        JOIN `tabEmployee` e ON e.name = s.employee
        LEFT JOIN (
            SELECT
                employee, date,
                COUNT(*)                AS activity_count,
                SUM(points)             AS total_points,
                SUM(business_value)     AS total_value,
                (
                    SELECT module
                    FROM `tabWork Activity Log` inner_a
                    WHERE inner_a.employee = outer_a.employee
                      AND inner_a.date     = outer_a.date
                    GROUP BY module
                    ORDER BY SUM(points) DESC
                    LIMIT 1
                )                       AS top_module
            FROM `tabWork Activity Log` outer_a
            GROUP BY employee, date
        ) act ON act.employee = s.employee AND act.date = s.date
        LEFT JOIN `tabWFH Daily Summary` d
               ON d.employee = s.employee AND d.date = s.date AND d.docstatus != 2
        WHERE s.docstatus != 2
          AND s.date BETWEEN %(from_date)s AND %(to_date)s
          {conditions}
        ORDER BY s.date DESC, points DESC
        """,
        params,
        as_dict=True,
    )
    return rows


def get_chart(data, filters):
    if not data:
        return None
    # Group by date for trend chart
    from collections import defaultdict
    by_date = defaultdict(lambda: {"points": 0, "hours": 0})
    for row in data:
        key = str(row.date)
        by_date[key]["points"] += float(row.points or 0)
        by_date[key]["hours"]  += float(row.hours  or 0)

    sorted_dates = sorted(by_date.keys())
    return {
        "data": {
            "labels": sorted_dates,
            "datasets": [
                {"name": _("Total Points"), "values": [round(by_date[d]["points"]) for d in sorted_dates]},
                {"name": _("Total Hours × 10"), "values": [round(by_date[d]["hours"] * 10, 1) for d in sorted_dates]},
            ],
        },
        "type": "line",
        "height": 260,
        "colors": ["#4f46e5", "#10b981"],
    }
