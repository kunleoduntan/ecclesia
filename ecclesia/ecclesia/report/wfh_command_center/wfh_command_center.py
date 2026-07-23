"""
WFH Command Center Report
Ecclesia Module

This feeds the real-time management dashboard.
Shows today's live WFH snapshot: who's in, who's flagged,
department breakdown, top performers.
"""

import frappe
from frappe import _
from ecclesia.api.analytics import get_command_center_data


def execute(filters=None):
    filters = filters or {}
    date = filters.get("date") or frappe.utils.nowdate()

    data_raw = get_command_center_data(date)

    # Top performers table
    columns = [
        {"label": _("Employee Name"),    "fieldname": "employee_name",   "fieldtype": "Data",     "width": 180},
        {"label": _("Department"),       "fieldname": "department",      "fieldtype": "Data",     "width": 130},
        {"label": _("Hours"),            "fieldname": "hours",           "fieldtype": "Float", "precision": 1, "width": 80},
        {"label": _("Points"),           "fieldname": "points",          "fieldtype": "Float", "precision": 0, "width": 80},
        {"label": _("Value Generated"),  "fieldname": "value_generated", "fieldtype": "Currency", "width": 140},
        {"label": _("Composite Score"),  "fieldname": "composite_score", "fieldtype": "Float", "precision": 1, "width": 130},
    ]

    data = data_raw.get("top_performers", [])

    summary = [
        {"value": data_raw["active_sessions"],      "label": _("Active Today"),         "datatype": "Int",      "color": "blue"},
        {"value": data_raw["total_hours"],           "label": _("Total Hours Logged"),   "datatype": "Float",    "color": "green"},
        {"value": data_raw["total_points"],          "label": _("Total Points Earned"),  "datatype": "Float",    "color": "purple"},
        {"value": data_raw["total_business_value"],  "label": _("Business Value (₦)"),   "datatype": "Currency", "color": "teal"},
        {"value": len(data_raw["flagged_employees"]),"label": _("Flagged Employees"),    "datatype": "Int",      "color": "orange"},
        {"value": len(data_raw["pending_summaries"]),"label": _("Pending Summaries"),    "datatype": "Int",      "color": "red"},
    ]

    return columns, data, None, None, summary
