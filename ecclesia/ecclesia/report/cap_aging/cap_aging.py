# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

"""
CAP Aging Report — Script Report
==================================
Tracks all open/overdue Corrective Action Plans with aging buckets.
Colour-coded by overdue severity. Used for management follow-up
and Audit Committee reporting.

Aging buckets: Current | 1–30 days | 31–60 days | 61–90 days | 90+ days
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
        {"label": "CAP",            "fieldname": "name",              "fieldtype": "Link",     "options": "Corrective Action Plan", "width": 140},
        {"label": "Title",          "fieldname": "cap_title",         "fieldtype": "Data",     "width": 260},
        {"label": "Status",         "fieldname": "status",            "fieldtype": "Data",     "width": 110},
        {"label": "Risk",           "fieldname": "risk_rating",       "fieldtype": "Data",     "width": 80},
        {"label": "Finding",        "fieldname": "audit_finding",     "fieldtype": "Link",     "options": "Audit Finding", "width": 140},
        {"label": "Owner",          "fieldname": "action_owner",      "fieldtype": "Link",     "options": "User", "width": 160},
        {"label": "Due Date",       "fieldname": "due_date",          "fieldtype": "Date",     "width": 100},
        {"label": "Days Overdue",   "fieldname": "days_overdue",      "fieldtype": "Int",      "width": 110},
        {"label": "Aging Bucket",   "fieldname": "aging_bucket",      "fieldtype": "Data",     "width": 120},
        {"label": "Milestones",     "fieldname": "milestone_summary", "fieldtype": "Data",     "width": 120},
    ]


def _get_data(filters):
    conditions = ["c.status NOT IN ('Completed','Accepted Risk')"]

    if filters.get("action_owner"):
        conditions.append(f"c.action_owner = {frappe.db.escape(filters['action_owner'])}")
    if filters.get("risk_rating"):
        conditions.append(f"c.risk_rating = {frappe.db.escape(filters['risk_rating'])}")

    where = " AND ".join(conditions)

    rows = frappe.db.sql(f"""
        SELECT
            c.name,
            c.cap_title,
            c.status,
            c.risk_rating,
            c.audit_finding,
            c.action_owner,
            c.due_date,
            (SELECT COUNT(*) FROM `tabCAP Milestone` m WHERE m.parent = c.name) AS total_milestones,
            (SELECT COUNT(*) FROM `tabCAP Milestone` m WHERE m.parent = c.name AND m.status = 'Completed') AS done_milestones
        FROM `tabCorrectiveAction Plan` c
        WHERE {where}
        ORDER BY c.due_date ASC
    """, as_dict=True)

    # Handle possible table name variation
    if not rows:
        rows = frappe.db.sql(f"""
            SELECT
                c.name,
                c.cap_title,
                c.status,
                c.risk_rating,
                c.audit_finding,
                c.action_owner,
                c.due_date,
                0 AS total_milestones,
                0 AS done_milestones
            FROM `tabCorrective Action Plan` c
            WHERE {where}
            ORDER BY c.due_date ASC
        """, as_dict=True)

    today_date = getdate(today())
    for row in rows:
        if row.due_date:
            diff = date_diff(today_date, getdate(row.due_date))
            row["days_overdue"] = max(diff, 0)
            if diff <= 0:
                row["aging_bucket"] = "Current"
            elif diff <= 30:
                row["aging_bucket"] = "1–30 days"
            elif diff <= 60:
                row["aging_bucket"] = "31–60 days"
            elif diff <= 90:
                row["aging_bucket"] = "61–90 days"
            else:
                row["aging_bucket"] = "90+ days"
        else:
            row["days_overdue"] = 0
            row["aging_bucket"] = "No Due Date"

        t = row.get("total_milestones") or 0
        d = row.get("done_milestones") or 0
        row["milestone_summary"] = f"{d}/{t} done" if t else "No milestones"

    return rows


def _get_chart(data):
    buckets = ["Current", "1–30 days", "31–60 days", "61–90 days", "90+ days", "No Due Date"]
    counts  = {b: 0 for b in buckets}
    for row in data:
        b = row.get("aging_bucket","No Due Date")
        if b in counts:
            counts[b] += 1

    return {
        "data": {
            "labels": buckets,
            "datasets": [{"values": [counts[b] for b in buckets]}],
        },
        "type": "bar",
        "colors": ["#27ae60","#f39c12","#e67e22","#e74c3c","#c0392b","#95a5a6"],
        "height": 220,
        "title": "CAP Aging Buckets",
    }


def _get_summary(data):
    total   = len(data)
    overdue = sum(1 for r in data if (r.get("days_overdue") or 0) > 0)
    critical = sum(1 for r in data if r.get("risk_rating") == "Critical")
    over90  = sum(1 for r in data if r.get("aging_bucket") == "90+ days")
    return [
        {"label": "Total Open CAPs",  "value": total,    "indicator": "red"    if total    > 0 else "green"},
        {"label": "Overdue",          "value": overdue,  "indicator": "red"    if overdue  > 0 else "green"},
        {"label": "Critical Risk",    "value": critical, "indicator": "red"    if critical > 0 else "green"},
        {"label": "90+ Days Overdue", "value": over90,   "indicator": "red"    if over90   > 0 else "green"},
    ]