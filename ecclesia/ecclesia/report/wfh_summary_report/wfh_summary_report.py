"""
WFH Summary Report
Ecclesia Module

Shows per-employee WFH statistics for a date range:
total days, hours, points, value, composite score, compliance.
"""

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data    = get_data(filters)
    chart   = get_chart(data)
    return columns, data, None, chart


def get_columns():
    return [
        {"label": _("Employee"),         "fieldname": "employee",         "fieldtype": "Link", "options": "Employee", "width": 130},
        {"label": _("Employee Name"),    "fieldname": "employee_name",    "fieldtype": "Data", "width": 160},
        {"label": _("Department"),       "fieldname": "department",       "fieldtype": "Link", "options": "Department", "width": 130},
        {"label": _("WFH Days"),         "fieldname": "wfh_days",         "fieldtype": "Int",  "width": 90},
        {"label": _("Total Hours"),      "fieldname": "total_hours",      "fieldtype": "Float","precision": 1, "width": 100},
        {"label": _("Avg Hours/Day"),    "fieldname": "avg_hours",        "fieldtype": "Float","precision": 1, "width": 110},
        {"label": _("Activity Points"),  "fieldname": "total_points",     "fieldtype": "Float","precision": 0, "width": 120},
        {"label": _("Business Value"),   "fieldname": "total_value",      "fieldtype": "Currency", "width": 130},
        {"label": _("Summaries Submitted"), "fieldname": "summaries",     "fieldtype": "Int",  "width": 140},
        {"label": _("Compliance %"),     "fieldname": "compliance_pct",   "fieldtype": "Percent","width": 110},
        {"label": _("Avg Composite Score"),"fieldname": "avg_composite",  "fieldtype": "Float","precision": 1, "width": 150},
        {"label": _("Days Flagged"),     "fieldname": "days_flagged",     "fieldtype": "Int",  "width": 100},
    ]


def get_data(filters):
    conditions = ""
    params = {
        "from_date": filters.get("from_date"),
        "to_date":   filters.get("to_date"),
    }

    if filters.get("department"):
        conditions += " AND e.department = %(department)s"
        params["department"] = filters["department"]

    if filters.get("employee"):
        conditions += " AND s.employee = %(employee)s"
        params["employee"] = filters["employee"]

    rows = frappe.db.sql(
        f"""
        SELECT
            s.employee,
            MAX(e.employee_name)                              AS employee_name,
            MAX(e.department)                                 AS department,
            COUNT(DISTINCT s.date)                            AS wfh_days,
            ROUND(COALESCE(SUM(s.total_hours), 0), 1)        AS total_hours,
            ROUND(COALESCE(AVG(s.total_hours), 0), 1)        AS avg_hours,
            ROUND(COALESCE(SUM(a.points_sum), 0), 0)         AS total_points,
            ROUND(COALESCE(SUM(a.value_sum), 0), 2)          AS total_value,
            COUNT(DISTINCT d.date)                            AS summaries,
            ROUND(
                COALESCE(COUNT(DISTINCT d.date), 0) /
                NULLIF(COUNT(DISTINCT s.date), 0) * 100, 1
            )                                                 AS compliance_pct,
            ROUND(COALESCE(AVG(d.composite_score), 0), 1)    AS avg_composite,
            COALESCE(SUM(CASE WHEN d.status='Flagged' THEN 1 ELSE 0 END), 0) AS days_flagged
        FROM `tabWFH Session` s
        JOIN `tabEmployee` e ON e.name = s.employee
        LEFT JOIN (
            SELECT employee, date,
                   SUM(points)         AS points_sum,
                   SUM(business_value) AS value_sum
            FROM `tabWork Activity Log`
            GROUP BY employee, date
        ) a ON a.employee = s.employee AND a.date = s.date
        LEFT JOIN `tabWFH Daily Summary` d
               ON d.employee = s.employee AND d.date = s.date AND d.docstatus != 2
        WHERE s.docstatus != 2
          AND s.date BETWEEN %(from_date)s AND %(to_date)s
          {conditions}
        GROUP BY s.employee
        ORDER BY total_points DESC
        """,
        params,
        as_dict=True,
    )
    return rows


def get_chart(data):
    if not data:
        return None
    labels = [d.employee_name for d in data[:10]]
    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": _("Activity Points"), "values": [d.total_points for d in data[:10]]},
                {"name": _("Hours × 10"),      "values": [round(d.total_hours * 10, 1) for d in data[:10]]},
            ],
        },
        "type": "bar",
        "height": 280,
        "colors": ["#4f46e5", "#0ea5e9"],
    }
