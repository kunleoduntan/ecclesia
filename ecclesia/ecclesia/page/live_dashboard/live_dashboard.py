"""
Live Dashboard Page Backend  (ecclesia/ecclesia/page/live_dashboard/live_dashboard.py)
Correct import paths: ecclesia.ecclesia.*
Uses Work Session (new unified) + falls back to WFH Session (legacy).
Works for ALL users regardless of Employee linkage.
"""

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, nowdate
import json


@frappe.whitelist()
def get_live_data(date=None, department=None):
    date = date or nowdate()
    users  = _get_active_users(date, department)
    kpis   = _calc_kpis(users, date)
    return {
        "date":           date,
        "users":          users,
        "kpis":           kpis,
        "schedule_today": _schedule_overview(date, department),
        "recent_activity":_recent_activity(date),
        "wfh_users":      [u for u in users if u["work_mode"] == "WFH"],
        "wfo_users":      [u for u in users if u["work_mode"] == "WFO"],
        "field_users":    [u for u in users if u["work_mode"] in ("Hybrid","Field")],
        "flagged":        [u for u in users if u["inactivity_flag"]],
    }


def _get_active_users(date, department=None):
    dept_cond = "AND e.department = %(dept)s" if department else ""
    rows = frappe.db.sql(f"""
        SELECT
            s.name, s.user, s.employee, s.employee_name,
            s.work_mode, s.location_label, s.date,
            s.check_in_time, s.check_out_time,
            COALESCE(s.total_hours,0)    AS total_hours,
            s.status,
            COALESCE(s.inactivity_flag,0) AS inactivity_flag,
            COALESCE(s.gps_verified,0)   AS gps_verified,
            u.full_name                  AS user_full_name,
            u.user_image,
            COALESCE(e.department,'')    AS department,
            COALESCE(e.designation,'')   AS designation,
            COALESCE(
                (SELECT SUM(al.points) FROM `tabWork Activity Log` al
                 WHERE al.employee=s.employee AND al.date=s.date),0
            ) AS activity_points,
            COALESCE(
                (SELECT COUNT(*) FROM `tabWork Activity Log` al2
                 WHERE al2.employee=s.employee AND al2.date=s.date),0
            ) AS activity_count,
            COALESCE(
                (SELECT al3.reference_doctype FROM `tabWork Activity Log` al3
                 WHERE al3.employee=s.employee AND al3.date=s.date
                 ORDER BY al3.timestamp DESC LIMIT 1),'') AS last_action_doc
        FROM `tabWork Session` s
        JOIN `tabUser` u ON u.name = s.user
        LEFT JOIN `tabEmployee` e ON e.name = s.employee
        WHERE s.date=%(date)s AND s.docstatus!=2 {dept_cond}
        ORDER BY s.check_in_time ASC
    """, {"date": date, "dept": department or ""}, as_dict=True)

    for r in rows:
        r["display_name"]  = r.employee_name or r.user_full_name or r.user
        r["initials"]      = "".join(w[0].upper() for w in (r["display_name"] or "?").split()[:2]) or "?"
        r["check_in_str"]  = str(r.check_in_time or "")[:16] or "—"
        r["check_out_str"] = str(r.check_out_time or "")[:16] or "—"
        r["total_hours"]   = round(flt(r.total_hours), 1)
        r["activity_points"]= round(flt(r.activity_points))
        r["activity_count"] = int(r.activity_count)
        r["is_employee"]   = bool(r.employee)
    return rows


def _calc_kpis(users, date):
    wfh   = [u for u in users if u["work_mode"] == "WFH"]
    wfo   = [u for u in users if u["work_mode"] == "WFO"]
    field = [u for u in users if u["work_mode"] in ("Hybrid","Field")]
    total_hrs  = sum(u["total_hours"]    for u in users)
    total_pts  = sum(u["activity_points"] for u in users)
    total_acts = sum(u["activity_count"]  for u in users)
    return {
        "total_active":  len(users),
        "wfh_count":     len(wfh),
        "wfo_count":     len(wfo),
        "field_count":   len(field),
        "total_hours":   round(total_hrs, 1),
        "total_points":  total_pts,
        "total_actions": total_acts,
        "flagged_count": sum(1 for u in users if u["inactivity_flag"]),
        "avg_hours":     round(total_hrs / len(users), 1) if users else 0,
    }


def _schedule_overview(date, department=None):
    # FIXED import path ↓
    from ecclesia.ecclesia.doctype.wfh_schedule.wfh_schedule import (
        is_scheduled_wfh_day, is_scheduled_wfo_day
    )
    filters = {"status": "Active"}
    if department:
        filters["department"] = department
    employees = frappe.get_all("Employee", filters=filters,
                               fields=["name","employee_name","department"])
    scheduled_wfh, not_in = [], []
    for emp in employees:
        if is_scheduled_wfh_day(emp.name, date):
            scheduled_wfh.append(emp)
            if not frappe.db.exists("Work Session",
                                    {"employee": emp.name, "date": date, "docstatus":("!=",2)}):
                not_in.append(emp)
    return {
        "scheduled_wfh_count": len(scheduled_wfh),
        "not_checked_in_wfh":  not_in,
    }


def _recent_activity(date):
    return frappe.db.sql("""
        SELECT al.employee,
               COALESCE(e.employee_name, al.employee) AS employee_name,
               al.reference_doctype, al.action,
               COALESCE(al.module,'Other') AS module,
               COALESCE(al.points,0)       AS points,
               al.timestamp
        FROM `tabWork Activity Log` al
        LEFT JOIN `tabEmployee` e ON e.name=al.employee
        WHERE al.date=%s
        ORDER BY al.timestamp DESC LIMIT 20
    """, date, as_dict=True)


@frappe.whitelist()
def get_user_detail(user, date=None):
    date = date or nowdate()
    session = frappe.db.get_value("Work Session",
        {"user": user, "date": date, "docstatus":("!=",2)},
        ["name","work_mode","check_in_time","check_out_time",
         "total_hours","status","location_label","gps_verified"],
        as_dict=True)
    activity = []
    if session:
        emp = frappe.db.get_value("Employee", {"user_id": user}, "name")
        if emp:
            activity = frappe.db.sql("""
                SELECT reference_doctype, action, module,
                       COALESCE(points,0) AS points,
                       COALESCE(business_value,0) AS business_value, timestamp
                FROM `tabWork Activity Log`
                WHERE employee=%s AND date=%s
                ORDER BY timestamp DESC LIMIT 10
            """, (emp, date), as_dict=True)
    tasks = frappe.get_all("External Task",
        filters={"user": user, "task_date": date},
        fields=["name","title","overall_status","total_tasks","completed_tasks","completion_pct"])
    return {"session": session, "activity": activity, "tasks": tasks}