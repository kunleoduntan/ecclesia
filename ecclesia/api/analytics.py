"""
Ecclesia WFH – Analytics Engine  (ecclesia/ecclesia/api/analytics.py)
All import paths use ecclesia.ecclesia.* convention.
Queries updated to support BOTH Work Session (new) and WFH Session (legacy).
"""

import frappe
from frappe.utils import nowdate, add_days, flt


@frappe.whitelist()
def get_command_center_data(date=None):
    date = date or nowdate()
    return {
        "date":                date,
        "active_sessions":     _active_sessions(date),
        "total_hours":         _total_hours(date),
        "total_business_value":_total_value(date),
        "total_points":        _total_points(date),
        "top_performers":      _top_performers(date, limit=5),
        "flagged_employees":   _flagged(date),
        "pending_summaries":   _pending_summaries(date),
        "department_breakdown":_dept_breakdown(date),
    }


@frappe.whitelist()
def get_employee_wfh_stats(employee, from_date=None, to_date=None):
    to_date   = to_date   or nowdate()
    from_date = from_date or add_days(to_date, -29)
    return {
        "employee":            employee,
        "from_date":           from_date,
        "to_date":             to_date,
        "total_wfh_days":      _count_wfh_days(employee, from_date, to_date),
        "total_hours":         _emp_hours(employee, from_date, to_date),
        "total_points":        _emp_points(employee, from_date, to_date),
        "total_value":         _emp_value(employee, from_date, to_date),
        "avg_composite":       _emp_composite(employee, from_date, to_date),
        "summaries_submitted": _summaries_done(employee, from_date, to_date),
        "days_flagged":        _days_flagged(employee, from_date, to_date),
        "consistency_score":   _consistency(employee, from_date, to_date),
    }


# ── Aggregates ─────────────────────────────────────────────────────────────────

def _active_sessions(date):
    """Count from Work Session (new) + WFH Session (legacy)."""
    ws = frappe.db.count("Work Session",
        {"date": date, "status": ("in", ["Open","Closed","Flagged"]), "docstatus": ("!=",2)})
    legacy = frappe.db.count("WFH Session",
        {"date": date, "status": ("in", ["Open","Closed"]), "docstatus": ("!=",2)})
    return (ws or 0) + (legacy or 0)


def _total_hours(date):
    ws = frappe.db.sql(
        "SELECT COALESCE(SUM(total_hours),0) FROM `tabWork Session` WHERE date=%s AND docstatus!=2",
        date)[0][0]
    leg = frappe.db.sql(
        "SELECT COALESCE(SUM(total_hours),0) FROM `tabWFH Session` WHERE date=%s AND docstatus!=2",
        date)[0][0]
    return round(flt(ws) + flt(leg), 2)


def _total_value(date):
    r = frappe.db.sql(
        "SELECT COALESCE(SUM(business_value),0) FROM `tabWork Activity Log` WHERE date=%s", date)
    return round(flt(r[0][0]), 2)


def _total_points(date):
    r = frappe.db.sql(
        "SELECT COALESCE(SUM(points),0) FROM `tabWork Activity Log` WHERE date=%s", date)
    return round(flt(r[0][0]), 2)


def _top_performers(date, limit=5):
    return frappe.db.sql("""
        SELECT
            ws.employee, ws.employee_name,
            COALESCE(e.department,'') AS department,
            COALESCE(ws.total_hours,0) AS hours,
            COALESCE(SUM(al.points),0) AS points,
            COALESCE(SUM(al.business_value),0) AS value_generated,
            COALESCE(d.composite_score,0) AS composite_score
        FROM `tabWork Session` ws
        LEFT JOIN `tabEmployee` e ON e.name = ws.employee
        LEFT JOIN `tabWork Activity Log` al
               ON al.employee = ws.employee AND al.date = ws.date
        LEFT JOIN `tabWFH Daily Summary` d
               ON d.employee = ws.employee AND d.date = ws.date
        WHERE ws.date = %s AND ws.docstatus != 2 AND ws.employee IS NOT NULL
        GROUP BY ws.employee
        ORDER BY points DESC
        LIMIT %s
    """, (date, limit), as_dict=True)


def _flagged(date):
    return frappe.db.sql("""
        SELECT DISTINCT ws.employee, ws.employee_name,
               COALESCE(e.department,'') AS department,
               ws.status AS session_status,
               ws.inactivity_flag,
               d.status  AS summary_status,
               d.flag_notes
        FROM `tabWork Session` ws
        LEFT JOIN `tabEmployee` e ON e.name = ws.employee
        LEFT JOIN `tabWFH Daily Summary` d ON d.employee=ws.employee AND d.date=ws.date
        WHERE ws.date = %s AND ws.docstatus != 2
          AND (ws.status = 'Flagged' OR d.status = 'Flagged'
               OR (ws.status IN ('Open','Closed') AND d.employee IS NULL))
    """, date, as_dict=True)


def _pending_summaries(date):
    return frappe.db.sql("""
        SELECT ws.employee, ws.employee_name,
               COALESCE(e.department,'') AS department,
               ws.total_hours
        FROM `tabWork Session` ws
        LEFT JOIN `tabEmployee` e ON e.name = ws.employee
        WHERE ws.date = %s AND ws.docstatus != 2
          AND NOT EXISTS (
              SELECT 1 FROM `tabWFH Daily Summary` d
              WHERE d.employee=ws.employee AND d.date=ws.date AND d.docstatus!=2)
        ORDER BY ws.employee_name
    """, date, as_dict=True)


def _dept_breakdown(date):
    return frappe.db.sql("""
        SELECT
            COALESCE(e.department,'Other') AS department,
            COUNT(DISTINCT ws.employee) AS employees,
            ROUND(AVG(ws.total_hours),2) AS avg_hours,
            COALESCE(SUM(al.points),0) AS total_points,
            COALESCE(SUM(al.business_value),0) AS total_value
        FROM `tabWork Session` ws
        LEFT JOIN `tabEmployee` e ON e.name = ws.employee
        LEFT JOIN `tabWork Activity Log` al ON al.employee=ws.employee AND al.date=ws.date
        WHERE ws.date = %s AND ws.docstatus != 2
        GROUP BY e.department
        ORDER BY total_points DESC
    """, date, as_dict=True)


# ── Per-employee helpers ───────────────────────────────────────────────────────

def _count_wfh_days(emp, fd, td):
    return (frappe.db.count("Work Session",
        {"employee": emp, "date": ("between",[fd,td]), "docstatus":("!=",2)}) or 0)


def _emp_hours(emp, fd, td):
    r = frappe.db.sql(
        "SELECT COALESCE(SUM(total_hours),0) FROM `tabWork Session` "
        "WHERE employee=%s AND date BETWEEN %s AND %s AND docstatus!=2",
        (emp,fd,td))
    return round(flt(r[0][0]),2)


def _emp_points(emp, fd, td):
    r = frappe.db.sql(
        "SELECT COALESCE(SUM(points),0) FROM `tabWork Activity Log` "
        "WHERE employee=%s AND date BETWEEN %s AND %s", (emp,fd,td))
    return round(flt(r[0][0]),2)


def _emp_value(emp, fd, td):
    r = frappe.db.sql(
        "SELECT COALESCE(SUM(business_value),0) FROM `tabWork Activity Log` "
        "WHERE employee=%s AND date BETWEEN %s AND %s", (emp,fd,td))
    return round(flt(r[0][0]),2)


def _emp_composite(emp, fd, td):
    r = frappe.db.sql(
        "SELECT COALESCE(AVG(composite_score),0) FROM `tabWFH Daily Summary` "
        "WHERE employee=%s AND date BETWEEN %s AND %s AND docstatus!=2", (emp,fd,td))
    return round(flt(r[0][0]),2)


def _summaries_done(emp, fd, td):
    return (frappe.db.count("WFH Daily Summary",
        {"employee":emp,"date":("between",[fd,td]),
         "status":("in",["Submitted","Reviewed"]),"docstatus":("!=",2)}) or 0)


def _days_flagged(emp, fd, td):
    return (frappe.db.count("WFH Daily Summary",
        {"employee":emp,"date":("between",[fd,td]),
         "status":"Flagged","docstatus":("!=",2)}) or 0)


def _consistency(emp, fd, td):
    total = _count_wfh_days(emp, fd, td)
    if not total:
        return 0
    return round(_summaries_done(emp, fd, td) / total * 100, 1)


def recompute_weekly_consistency():
    today = nowdate()
    for s in frappe.get_all("WFH Daily Summary",
                             filters={"date": today, "docstatus":("!=",2)},
                             fields=["name","employee","date"]):
        doc = frappe.get_doc("WFH Daily Summary", s.name)
        doc._calc_consistency_score()
        doc._calc_composite_score()
        doc.db_update()
    frappe.db.commit()