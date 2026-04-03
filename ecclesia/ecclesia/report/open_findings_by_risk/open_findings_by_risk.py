# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

"""
Open Findings by Risk — Script Report
=======================================
Shows all open Audit Findings grouped by risk rating,
with financial impact totals, age, and engagement context.
Designed for Audit Committee and management reporting.
"""

import frappe
from frappe.utils import getdate, date_diff, today


def execute(filters=None):
    filters = filters or {}
    columns = _get_columns()
    data    = _get_data(filters)
    chart   = _get_chart(data)
    summary = _get_summary(data)
    return columns, data, None, chart, summary


def _get_columns():
    return [
        {"label": "Finding",          "fieldname": "name",               "fieldtype": "Link",     "options": "Audit Finding", "width": 140},
        {"label": "Title",            "fieldname": "finding_title",       "fieldtype": "Data",     "width": 240},
        {"label": "Risk",             "fieldname": "risk_rating",         "fieldtype": "Data",     "width": 80},
        {"label": "Status",           "fieldname": "status",              "fieldtype": "Data",     "width": 120},
        {"label": "Type",             "fieldname": "finding_type",        "fieldtype": "Data",     "width": 160},
        {"label": "COSO",             "fieldname": "coso_component",      "fieldtype": "Data",     "width": 140},
        {"label": "Engagement",       "fieldname": "audit_engagement",    "fieldtype": "Link",     "options": "Audit Engagement", "width": 160},
        {"label": "DocType",          "fieldname": "reference_doctype",   "fieldtype": "Data",     "width": 160},
        {"label": "Tx Code",          "fieldname": "transaction_code",    "fieldtype": "Data",     "width": 100},
        {"label": "Financial Impact", "fieldname": "financial_impact",    "fieldtype": "Currency", "width": 130},
        {"label": "Materiality",      "fieldname": "materiality_level",   "fieldtype": "Data",     "width": 120},
        {"label": "Due Date",         "fieldname": "due_date",            "fieldtype": "Date",     "width": 100},
        {"label": "Age (days)",       "fieldname": "age_days",            "fieldtype": "Int",      "width": 90},
        {"label": "Source",           "fieldname": "source",              "fieldtype": "Data",     "width": 120},
    ]


def _get_data(filters):
    conditions = ["f.status NOT IN ('Closed - Resolved','Closed - Accepted Risk')"]

    if filters.get("risk_rating"):
        conditions.append(f"f.risk_rating = {frappe.db.escape(filters['risk_rating'])}")
    if filters.get("engagement"):
        conditions.append(f"f.audit_engagement = {frappe.db.escape(filters['engagement'])}")
    if filters.get("from_date"):
        conditions.append(f"f.creation >= {frappe.db.escape(filters['from_date'])}")

    where = " AND ".join(conditions)

    rows = frappe.db.sql(f"""
        SELECT
            f.name,
            f.finding_title,
            f.risk_rating,
            f.status,
            f.finding_type,
            f.coso_component,
            f.audit_engagement,
            f.reference_doctype,
            f.transaction_code,
            f.financial_impact,
            f.materiality_level,
            f.due_date,
            f.source,
            f.creation
        FROM `tabAudit Finding` f
        WHERE {where}
        ORDER BY
            FIELD(f.risk_rating, 'Critical','High','Medium','Low'),
            f.financial_impact DESC
    """, as_dict=True)

    risk_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}

    for row in rows:
        row["age_days"] = date_diff(today(), getdate(row.creation)) if row.creation else 0
        # Add indent for grouping visual
        row["indent"] = 0

    return rows


def _get_chart(data):
    risk_totals = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for row in data:
        r = row.get("risk_rating")
        if r in risk_totals:
            risk_totals[r] += 1

    return {
        "data": {
            "labels": list(risk_totals.keys()),
            "datasets": [{"values": list(risk_totals.values())}],
        },
        "type": "donut",
        "colors": ["#e74c3c", "#e67e22", "#f39c12", "#27ae60"],
        "height": 220,
        "title": "Open Findings by Risk Rating",
    }


def _get_summary(data):
    total   = len(data)
    crit    = sum(1 for r in data if r.get("risk_rating") == "Critical")
    high    = sum(1 for r in data if r.get("risk_rating") == "High")
    impact  = sum((r.get("financial_impact") or 0) for r in data)
    overdue = sum(1 for r in data if r.get("due_date") and getdate(r["due_date"]) < getdate(today()))

    return [
        {"label": "Total Open",      "value": total,  "indicator": "red"    if total   > 0 else "green"},
        {"label": "Critical",        "value": crit,   "indicator": "red"    if crit    > 0 else "green"},
        {"label": "High",            "value": high,   "indicator": "orange" if high    > 0 else "green"},
        {"label": "Overdue",         "value": overdue,"indicator": "red"    if overdue > 0 else "green"},
        {"label": "Total Impact",    "value": frappe.utils.fmt_money(impact), "indicator": "red" if impact > 0 else "green"},
    ]