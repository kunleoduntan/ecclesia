# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

# import frappe


"""
Audit Universe Coverage — Script Report
=========================================
Shows every registered DocType with its last audit date,
opinion, open findings, risk score, and coverage gap (days
since last audit vs recommended frequency).

Used by Audit Manager and Audit Committee to identify
which areas are overdue for coverage.
"""

import frappe
from frappe.utils import getdate, date_diff, today


# Recommended frequency → max days between audits
FREQUENCY_DAYS = {
    "Monthly":      30,
    "Quarterly":    90,
    "Semi-Annual":  180,
    "Annual":       365,
    "As Required":  730,
}


def execute(filters=None):
    filters = filters or {}
    columns = _get_columns()
    data    = _get_data(filters)
    chart   = _get_chart(data)
    summary = _get_summary(data)
    return columns, data, None, chart, summary


def _get_columns():
    return [
        {"label": "DocType",          "fieldname": "doctype_name",       "fieldtype": "Data",   "width": 200},
        {"label": "Tx Code",          "fieldname": "transaction_code",   "fieldtype": "Data",   "width": 120},
        {"label": "Classification",   "fieldname": "doctype_classification","fieldtype": "Data", "width": 140},
        {"label": "Risk Level",       "fieldname": "risk_level",         "fieldtype": "Data",   "width": 90},
        {"label": "AI Risk Score",    "fieldname": "avg_risk_score",     "fieldtype": "Float",  "width": 100, "precision": 1},
        {"label": "GL Posting",       "fieldname": "is_gl_posting",      "fieldtype": "Check",  "width": 90},
        {"label": "Frequency",        "fieldname": "audit_frequency",    "fieldtype": "Data",   "width": 110},
        {"label": "Last Audit",       "fieldname": "last_audit_date",    "fieldtype": "Date",   "width": 110},
        {"label": "Days Since Audit", "fieldname": "days_since_audit",   "fieldtype": "Int",    "width": 130},
        {"label": "Coverage Status",  "fieldname": "coverage_status",    "fieldtype": "Data",   "width": 120},
        {"label": "Last Opinion",     "fieldname": "last_audit_opinion", "fieldtype": "Data",   "width": 110},
        {"label": "Open Findings",    "fieldname": "open_findings_count","fieldtype": "Int",    "width": 110},
        {"label": "Txns YTD",         "fieldname": "total_transactions_ytd","fieldtype": "Int", "width": 100},
    ]


def _get_data(filters):
    conditions = ["is_active = 1"]

    if filters.get("risk_level"):
        conditions.append(f"risk_level = {frappe.db.escape(filters['risk_level'])}")
    if filters.get("classification"):
        conditions.append(f"doctype_classification = {frappe.db.escape(filters['classification'])}")

    where = " AND ".join(conditions)

    rows = frappe.db.sql(f"""
        SELECT
            doctype_name, transaction_code, doctype_classification,
            risk_level, avg_risk_score, is_gl_posting,
            audit_frequency, last_audit_date, last_audit_opinion,
            open_findings_count, total_transactions_ytd
        FROM `tabAuditable DocType Registry`
        WHERE {where}
        ORDER BY
            FIELD(risk_level,'Critical','High','Medium','Low'),
            avg_risk_score DESC
    """, as_dict=True)

    today_date = getdate(today())
    for row in rows:
        if row.last_audit_date:
            row["days_since_audit"] = date_diff(today_date, getdate(row.last_audit_date))
        else:
            row["days_since_audit"] = 9999   # Never audited

        max_days = FREQUENCY_DAYS.get(row.audit_frequency, 365)
        days     = row["days_since_audit"]

        if days == 9999:
            row["coverage_status"] = "⚠️ Never Audited"
        elif days > max_days * 1.5:
            row["coverage_status"] = "🔴 Severely Overdue"
        elif days > max_days:
            row["coverage_status"] = "🟠 Overdue"
        elif days > max_days * 0.75:
            row["coverage_status"] = "🟡 Due Soon"
        else:
            row["coverage_status"] = "✅ Current"

    return rows


def _get_chart(data):
    statuses = ["✅ Current", "🟡 Due Soon", "🟠 Overdue", "🔴 Severely Overdue", "⚠️ Never Audited"]
    counts   = {s: 0 for s in statuses}
    for row in data:
        s = row.get("coverage_status", "⚠️ Never Audited")
        if s in counts:
            counts[s] += 1

    return {
        "data": {
            "labels": [s.split(" ", 1)[1] for s in statuses],   # strip emoji
            "datasets": [{"values": [counts[s] for s in statuses]}],
        },
        "type": "donut",
        "colors": ["#27ae60", "#f39c12", "#e67e22", "#e74c3c", "#95a5a6"],
        "height": 220,
        "title": "Audit Coverage Status",
    }


def _get_summary(data):
    total    = len(data)
    never    = sum(1 for r in data if r.get("days_since_audit") == 9999)
    overdue  = sum(1 for r in data if "Overdue" in (r.get("coverage_status") or ""))
    critical = sum(1 for r in data if r.get("risk_level") == "Critical")
    covered  = sum(1 for r in data if r.get("coverage_status") == "✅ Current")
    pct      = round(covered / total * 100) if total else 0

    return [
        {"label": "Registered DocTypes", "value": total,    "indicator": "blue"},
        {"label": "Coverage %",          "value": f"{pct}%","indicator": "green" if pct >= 80 else "orange"},
        {"label": "Overdue / Never",     "value": overdue + never, "indicator": "red" if (overdue+never) > 0 else "green"},
        {"label": "Critical Risk",       "value": critical, "indicator": "red" if critical > 0 else "green"},
    ]