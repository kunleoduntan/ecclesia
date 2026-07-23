"""
WFH Dashboard Page Backend
Path: ecclesia/ecclesia/page/wfh_dashboard/wfh_dashboard.py
Uses Work Session + falls back to WFH Session (legacy).
Works for ALL users regardless of Employee linkage.
"""

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, nowdate, get_datetime
import json


@frappe.whitelist()
def get_live_data(date=None, department=None):
    """Main dashboard data endpoint"""
    date = date or nowdate()
    users   = _get_active_users(date, department)
    kpis    = _calc_kpis(users, date)
    
    return {
        "date":            date,
        "users":           users,
        "wfh_users":       [u for u in users if u.get("work_mode") == "WFH"],
        "wfo_users":       [u for u in users if u.get("work_mode") == "WFO"],
        "field_users":     [u for u in users if u.get("work_mode") in ("Hybrid", "Field")],
        "flagged":         [u for u in users if u.get("inactivity_flag")],
        "kpis":            kpis,
        "schedule_today":  _schedule_overview(date, department),
        "recent_activity": _recent_activity(date),
        "generated_at":    frappe.utils.now(),
    }


def _get_active_users(date, department=None):
    """Get all users with active sessions for the given date"""
    dept_cond = "AND e.department = %(dept)s" if department else ""
    
    rows = frappe.db.sql("""
        SELECT
            s.name                 AS session_name,
            s.user,
            s.employee,
            s.employee_name,
            s.work_mode,
            s.location_label,
            s.date,
            s.check_in_time,
            s.check_out_time,
            COALESCE(s.total_hours, 0)      AS total_hours,
            s.status,
            COALESCE(s.inactivity_flag, 0)  AS inactivity_flag,
            COALESCE(s.gps_verified, 0)     AS gps_verified,
            u.full_name                     AS user_full_name,
            u.user_image,
            COALESCE(e.department, '')      AS department,
            COALESCE(e.designation, '')     AS designation,
            COALESCE(
                (SELECT SUM(al.points) 
                 FROM `tabWork Activity Log` al
                 WHERE al.employee = s.employee 
                   AND al.date = s.date), 0
            ) AS activity_points,
            COALESCE(
                (SELECT COUNT(*) 
                 FROM `tabWork Activity Log` al2
                 WHERE al2.employee = s.employee 
                   AND al2.date = s.date), 0
            ) AS activity_count,
            COALESCE(
                (SELECT al3.reference_doctype 
                 FROM `tabWork Activity Log` al3
                 WHERE al3.employee = s.employee 
                   AND al3.date = s.date
                 ORDER BY al3.timestamp DESC 
                 LIMIT 1), ''
            ) AS last_action_doc,
            COALESCE(
                (SELECT al4.timestamp 
                 FROM `tabWork Activity Log` al4
                 WHERE al4.employee = s.employee 
                   AND al4.date = s.date
                 ORDER BY al4.timestamp DESC 
                 LIMIT 1), NULL
            ) AS last_active
        FROM `tabWork Session` s
        INNER JOIN `tabUser` u ON u.name = s.user
        LEFT JOIN `tabEmployee` e ON e.name = s.employee
        WHERE s.date = %(date)s 
          AND s.docstatus != 2
          {dept_cond}
        ORDER BY s.check_in_time ASC
    """.format(dept_cond=dept_cond), 
    {"date": date, "dept": department or ""}, 
    as_dict=True)

    # Process each row for display
    for r in rows:
        r["display_name"]   = r.get("employee_name") or r.get("user_full_name") or r.get("user") or "Unknown"
        r["initials"]       = "".join(
            w[0].upper() for w in (r["display_name"] or "?").split()[:2]
        ) or "?"
        r["check_in_str"]   = _format_time(r.get("check_in_time"))
        r["check_out_str"]  = _format_time(r.get("check_out_time"))
        r["last_active_str"] = _format_time(r.get("last_active"))
        r["total_hours"]    = round(flt(r.get("total_hours", 0)), 1)
        r["activity_points"] = round(flt(r.get("activity_points", 0)))
        r["activity_count"]  = int(r.get("activity_count", 0))
        r["is_employee"]    = bool(r.get("employee"))
        r["session_name"]   = r.get("session_name") or ""
    
    return rows


def _format_time(dt):
    """Format datetime to readable string"""
    if not dt:
        return "—"
    try:
        return str(dt)[:16] if len(str(dt)) >= 16 else str(dt)
    except:
        return "—"


def _calc_kpis(users, date):
    """Calculate KPI metrics from user data"""
    wfh   = [u for u in users if u.get("work_mode") == "WFH"]
    wfo   = [u for u in users if u.get("work_mode") == "WFO"]
    field = [u for u in users if u.get("work_mode") in ("Hybrid", "Field")]
    
    total_hrs  = sum(u.get("total_hours", 0) for u in users)
    total_pts  = sum(u.get("activity_points", 0) for u in users)
    total_acts = sum(u.get("activity_count", 0) for u in users)
    flagged    = sum(1 for u in users if u.get("inactivity_flag"))
    gps_ok     = sum(1 for u in users if u.get("gps_verified"))
    
    return {
        "total_active":   len(users),
        "wfh_count":      len(wfh),
        "wfo_count":      len(wfo),
        "field_count":    len(field),
        "total_hours":    round(total_hrs, 1),
        "total_points":   total_pts,
        "total_actions":  total_acts,
        "flagged_count":  flagged,
        "gps_verified_count": gps_ok,
        "avg_hours":      round(total_hrs / len(users), 1) if users else 0,
        "avg_points":     round(total_pts / len(users), 1) if users else 0,
    }


def _schedule_overview(date, department=None):
    """Get WFH schedule overview for the date"""
    try:
        from ecclesia.ecclesia.doctype.wfh_schedule.wfh_schedule import (
            is_scheduled_wfh_day, is_scheduled_wfo_day
        )
    except ImportError:
        frappe.logger().warning("WFH Schedule module not found")
        return {
            "scheduled_wfh_count": 0,
            "not_checked_in_wfh": []
        }
    
    filters = {"status": "Active"}
    if department:
        filters["department"] = department
    
    employees = frappe.get_all(
        "Employee", 
        filters=filters,
        fields=["name", "employee_name", "department"]
    )
    
    scheduled_wfh = []
    not_in = []
    
    for emp in employees:
        try:
            if is_scheduled_wfh_day(emp.name, date):
                scheduled_wfh.append(emp)
                # Check if they have a session today
                exists = frappe.db.exists(
                    "Work Session",
                    {
                        "employee": emp.name,
                        "date": date,
                        "docstatus": ("!=", 2)
                    }
                )
                if not exists:
                    not_in.append(emp)
        except Exception as e:
            frappe.logger().debug(f"Error checking schedule for {emp.name}: {e}")
    
    return {
        "scheduled_wfh_count": len(scheduled_wfh),
        "not_checked_in_wfh":  not_in,
    }


def _recent_activity(date):
    """Get recent activity logs for the date"""
    return frappe.db.sql("""
        SELECT 
            al.employee,
            COALESCE(e.employee_name, al.employee) AS employee_name,
            al.reference_doctype,
            al.action,
            COALESCE(al.module, 'Other')           AS module,
            COALESCE(al.points, 0)                 AS points,
            al.timestamp
        FROM `tabWork Activity Log` al
        LEFT JOIN `tabEmployee` e ON e.name = al.employee
        WHERE al.date = %s
        ORDER BY al.timestamp DESC 
        LIMIT 20
    """, date, as_dict=True)


@frappe.whitelist()
def get_user_detail(user, date=None):
    """Get detailed info for a specific user"""
    date = date or nowdate()
    
    session = frappe.db.get_value(
        "Work Session",
        {
            "user": user,
            "date": date,
            "docstatus": ("!=", 2)
        },
        [
            "name", "work_mode", "check_in_time", "check_out_time",
            "total_hours", "status", "location_label", "gps_verified",
            "employee", "employee_name"
        ],
        as_dict=True
    )
    
    activity = []
    if session and session.get("employee"):
        activity = frappe.db.sql("""
            SELECT 
                reference_doctype, action, module,
                COALESCE(points, 0)           AS points,
                COALESCE(business_value, 0)   AS business_value,
                timestamp
            FROM `tabWork Activity Log`
            WHERE employee = %s AND date = %s
            ORDER BY timestamp DESC 
            LIMIT 10
        """, (session.employee, date), as_dict=True)
    
    tasks = frappe.get_all(
        "External Task",
        filters={"user": user, "task_date": date},
        fields=[
            "name", "title", "overall_status",
            "total_tasks", "completed_tasks", "completion_pct"
        ]
    )
    
    return {
        "session":  session,
        "activity": activity,
        "tasks":    tasks,
    }