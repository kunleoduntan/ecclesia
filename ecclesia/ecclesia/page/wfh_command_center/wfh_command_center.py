"""
WFH Command Center Backend
Path: ecclesia/ecclesia/page/wfh_command_center/wfh_command_center.py

Enhanced Dashboard with:
  - Productivity scoring
  - Department comparisons
  - Leaderboard rankings
  - Anomaly detection
  - User activity drill-down
  - Detailed time displays
  - Doctype breakdown per user
"""

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, nowdate, get_datetime, now_datetime, pretty_date
from datetime import timedelta
import json


@frappe.whitelist()
def get_command_center_data(date=None, department=None):
    """Main Command Center data endpoint"""
    date = date or nowdate()
    
    users = _get_active_users(date, department)
    kpis = _calc_kpis(users, date)
    leaderboard = _get_leaderboard(date, department)
    dept_breakdown = _get_department_breakdown(date)
    anomalies = _detect_anomalies(users, date)
    attention = _get_attention_required(users, date, department)
    
    return {
        "date":              date,
        "users":             users,
        "wfh_users":         [u for u in users if u.get("work_mode") == "WFH"],
        "wfo_users":         [u for u in users if u.get("work_mode") == "WFO"],
        "field_users":       [u for u in users if u.get("work_mode") in ("Hybrid", "Field")],
        "flagged":           [u for u in users if u.get("inactivity_flag")],
        "kpis":              kpis,
        "leaderboard":       leaderboard,
        "dept_breakdown":    dept_breakdown,
        "anomalies":         anomalies,
        "attention_required": attention,
        "recent_activity":   _recent_activity(date),
        "generated_at":      frappe.utils.now(),
    }


@frappe.whitelist()
def get_user_activity_detail(employee, date=None):
    """
    Get detailed activity breakdown for a specific user.
    Includes session info, activity timeline, doctype breakdown, and time metrics.
    """
    date = date or nowdate()
    
    if not employee:
        return None
    
    # Get session info from Work Session
    session = frappe.db.get_value(
        "Work Session",
        {
            "employee": employee,
            "date": date,
            "docstatus": ("!=", 2)
        },
        [
            "name", "user", "employee", "employee_name", "work_mode",
            "check_in_time", "check_out_time", "total_hours", "status",
            "location_label", "gps_verified"
        ],
        as_dict=True
    )
    
    if not session:
        # Try WFH Session
        session = frappe.db.get_value(
            "WFH Session",
            {
                "employee": employee,
                "date": date,
                "docstatus": ("!=", 2)
            },
            [
                "name", "employee", "employee_name", 
                "check_in_time", "check_out_time", "total_hours", "status",
                "gps_verified"
            ],
            as_dict=True
        )
        
        if not session:
            return None
        
        # Add missing fields for WFH Session
        session["user"] = frappe.db.get_value("Employee", employee, "user_id")
        session["work_mode"] = "WFH"
        session["location_label"] = ""
    
    # Get employee details
    emp_details = frappe.db.get_value(
        "Employee",
        employee,
        ["department", "designation", "user_id"],
        as_dict=True
    )
    
    if emp_details:
        session["department"] = emp_details.get("department", "")
        session["designation"] = emp_details.get("designation", "")
    
    # Get user info (full_name and user_image)
    if session.get("user"):
        user_info = frappe.db.get_value(
            "User", 
            session["user"], 
            ["full_name", "user_image"], 
            as_dict=True
        )
        if user_info:
            session["user_full_name"] = user_info.get("full_name", "")
            session["user_image"] = user_info.get("user_image", None)
    
    # Get activities
    activities = frappe.db.get_all(
        "Work Activity Log",
        filters={"employee": employee, "date": date},
        fields=[
            "name", "reference_doctype", "reference_name", "action",
            "module", "points", "raw_score", "dampened_points",
            "business_value", "currency", "is_dampened", "timestamp",
            "config_ref"
        ],
        order_by="timestamp desc"
    )
    
    # Process activities
    for a in activities:
        a["time_display"] = _format_time_short(a.get("timestamp"))
        a["time_full"] = str(a.get("timestamp", ""))[:19] if a.get("timestamp") else ""
        a["points"] = round(flt(a.get("points", 0)), 1)
        a["raw_score"] = round(flt(a.get("raw_score", 0)), 1)
        a["business_value"] = flt(a.get("business_value", 0))
        a["is_dampened"] = bool(a.get("is_dampened", 0))
    
    # Doctype breakdown
    doctype_breakdown = {}
    for a in activities:
        dt = a.get("reference_doctype", "Unknown")
        if dt not in doctype_breakdown:
            doctype_breakdown[dt] = {
                "doctype": dt,
                "count": 0,
                "points": 0,
                "raw_score": 0,
                "module": a.get("module", "Other"),
                "actions_list": []
            }
        doctype_breakdown[dt]["count"] += 1
        doctype_breakdown[dt]["points"] += flt(a.get("points", 0))
        doctype_breakdown[dt]["raw_score"] += flt(a.get("raw_score", 0))
        doctype_breakdown[dt]["actions_list"].append(a.get("action", ""))
    
    # Get unique actions per doctype
    for dt in doctype_breakdown:
        doctype_breakdown[dt]["unique_actions"] = list(set(doctype_breakdown[dt]["actions_list"]))
        del doctype_breakdown[dt]["actions_list"]
    
    breakdown_list = sorted(doctype_breakdown.values(), key=lambda x: x["points"], reverse=True)
    
    # Time calculations
    total_hours = flt(session.get("total_hours", 0))
    total_points = sum(flt(a.get("points", 0)) for a in activities)
    total_raw = sum(flt(a.get("raw_score", 0)) for a in activities)
    points_per_hour = round(total_points / total_hours, 1) if total_hours > 0 else 0
    
    # Duration display
    duration_display = _format_duration(total_hours)
    duration_minutes = int(total_hours * 60) if total_hours > 0 else 0
    
    # Actions in last hour
    now = now_datetime()
    hour_ago = now - timedelta(hours=1)
    actions_last_hour = sum(
        1 for a in activities 
        if a.get("timestamp") and get_datetime(a["timestamp"]) >= hour_ago
    )
    
    # Actions in last 30 minutes
    half_hour_ago = now - timedelta(minutes=30)
    actions_last_30min = sum(
        1 for a in activities 
        if a.get("timestamp") and get_datetime(a["timestamp"]) >= half_hour_ago
    )
    
    # Check-in/out time formatting
    check_in = session.get("check_in_time")
    check_out = session.get("check_out_time")
    is_active = session.get("status") == "Open"
    
    # Calculate elapsed time for active sessions
    elapsed_display = ""
    if is_active and check_in:
        elapsed = now_datetime() - get_datetime(check_in)
        elapsed_hours = elapsed.total_seconds() / 3600
        h = int(elapsed_hours)
        m = int((elapsed_hours - h) * 60)
        elapsed_display = f"{h}h {m}m"
    
    return {
        # Session info
        "session_name": session.get("name"),
        "display_name": session.get("employee_name") or session.get("user_full_name", "") or employee,
        "initials": _get_initials(session.get("employee_name") or employee),
        "work_mode": session.get("work_mode", "WFH"),
        "department": session.get("department", ""),
        "designation": session.get("designation", ""),
        "status": session.get("status", "Unknown"),
        "is_active": is_active,
        "gps_verified": bool(session.get("gps_verified", 0)),
        "location_label": session.get("location_label", ""),
        "user_image": session.get("user_image", None),
        
        # Time information
        "check_in_str": _format_time(check_in),
        "check_in_full": str(check_in)[:19] if check_in else "—",
        "check_in_relative": _relative_time(check_in) if check_in else "",
        "check_in_iso": str(check_in) if check_in else "",
        
        "check_out_str": _format_time(check_out) if check_out else ("Active" if is_active else "—"),
        "check_out_full": str(check_out)[:19] if check_out else ("Active" if is_active else "—"),
        "check_out_relative": _relative_time(check_out) if check_out else "",
        "check_out_iso": str(check_out) if check_out else "",
        
        # Duration
        "total_hours": round(total_hours, 1),
        "duration_display": duration_display,
        "duration_minutes": duration_minutes,
        "elapsed_display": elapsed_display if is_active else "",
        
        # Activity metrics
        "activity_points": int(total_points),
        "activity_count": len(activities),
        "raw_score_total": round(total_raw, 1),
        "points_per_hour": points_per_hour,
        "actions_last_hour": actions_last_hour,
        "actions_last_30min": actions_last_30min,
        "avg_points_per_action": round(total_points / len(activities), 1) if activities else 0,
        
        # Breakdowns
        "doctype_breakdown": breakdown_list,
        "activities": activities[:100],
        "total_activities_today": len(activities),
    }


# ── Helper Functions ──────────────────────────────────────────────────────────

def _get_initials(name):
    """Get initials from name"""
    if not name:
        return "?"
    parts = str(name).split()
    return "".join(p[0].upper() for p in parts[:2]) or "?"


def _format_time(dt):
    """Format datetime to readable string (HH:MM)"""
    if not dt:
        return "—"
    try:
        d = get_datetime(dt)
        return d.strftime("%H:%M")
    except:
        return "—"


def _format_time_full(dt):
    """Format datetime to full time string (HH:MM:SS)"""
    if not dt:
        return "—"
    try:
        d = get_datetime(dt)
        return d.strftime("%H:%M:%S")
    except:
        return "—"


def _format_time_short(dt):
    """Format datetime to short time string (HH:MM)"""
    if not dt:
        return ""
    try:
        d = get_datetime(dt)
        return d.strftime("%H:%M")
    except:
        return ""


def _relative_time(dt):
    """Get relative time string (e.g., '2 hours ago')"""
    if not dt:
        return ""
    try:
        return pretty_date(dt)
    except:
        try:
            seconds = (now_datetime() - get_datetime(dt)).total_seconds()
            if seconds < 60:
                return "Just now"
            elif seconds < 3600:
                return f"{int(seconds/60)}m ago"
            elif seconds < 86400:
                return f"{int(seconds/3600)}h ago"
            else:
                return f"{int(seconds/86400)}d ago"
        except:
            return ""


def _format_duration(hours):
    """Format hours to readable duration string"""
    if not hours:
        return "0h"
    h = int(hours)
    m = int((hours - h) * 60)
    if m > 0:
        return f"{h}h {m}m"
    return f"{h}h"


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
        r["initials"]       = _get_initials(r["display_name"])
        r["user_image"]     = None  # Can be fetched separately if needed
        
        # Time displays
        r["check_in_str"]   = _format_time(r.get("check_in_time"))
        r["check_out_str"]  = _format_time(r.get("check_out_time"))
        r["last_active_str"] = _format_time(r.get("last_active"))
        
        # Full time displays
        r["check_in_time_display"] = _format_time_full(r.get("check_in_time"))
        r["check_out_time_display"] = _format_time_full(r.get("check_out_time"))
        
        # Duration display
        r["duration_display"] = _format_duration(r.get("total_hours", 0))
        
        # Numeric formatting
        r["total_hours"]    = round(flt(r.get("total_hours", 0)), 1)
        r["activity_points"] = round(flt(r.get("activity_points", 0)))
        r["activity_count"]  = int(r.get("activity_count", 0))
        r["is_employee"]    = bool(r.get("employee"))
        r["session_name"]   = r.get("session_name") or ""
        
        # Actions in last hour
        r["actions_last_hour"] = _get_actions_last_hour(r.get("employee"), date)
        
        # Performance tier
        pts = r["activity_points"]
        if pts >= 100:
            r["performance_tier"] = "exceptional"
        elif pts >= 50:
            r["performance_tier"] = "high"
        elif pts >= 20:
            r["performance_tier"] = "moderate"
        else:
            r["performance_tier"] = "low"
    
    return rows


def _get_actions_last_hour(employee, date):
    """Get count of actions in the last hour for an employee"""
    if not employee:
        return 0
    try:
        now = now_datetime()
        hour_ago = now - timedelta(hours=1)
        return frappe.db.count(
            "Work Activity Log",
            {
                "employee": employee,
                "date": date,
                "timestamp": (">=", hour_ago)
            }
        )
    except:
        return 0


def _calc_kpis(users, date):
    """Calculate comprehensive KPI metrics"""
    wfh   = [u for u in users if u.get("work_mode") == "WFH"]
    wfo   = [u for u in users if u.get("work_mode") == "WFO"]
    field = [u for u in users if u.get("work_mode") in ("Hybrid", "Field")]
    
    total_hrs  = sum(u.get("total_hours", 0) for u in users)
    total_pts  = sum(u.get("activity_points", 0) for u in users)
    total_acts = sum(u.get("activity_count", 0) for u in users)
    flagged    = sum(1 for u in users if u.get("inactivity_flag"))
    gps_ok     = sum(1 for u in users if u.get("gps_verified"))
    
    # Department stats
    depts = list(set(u.get("department","") for u in users if u.get("department")))
    
    # Productivity score (weighted calculation)
    productivity = 0
    if users:
        hrs_score = min((total_hrs / (len(users) * 8)) * 100, 100) if len(users) > 0 else 0
        pts_score = min((total_pts / (len(users) * 100)) * 100, 100) if len(users) > 0 else 0
        productivity = round((hrs_score * 0.4 + pts_score * 0.6), 1)
    
    # Compliance rate
    compliance = round((gps_ok / len(users) * 100), 1) if users else 0
    
    # Actions per person
    actions_per_person = round(total_acts / len(users), 1) if users else 0
    
    return {
        "total_active":      len(users),
        "wfh_count":         len(wfh),
        "wfo_count":         len(wfo),
        "field_count":       len(field),
        "wfh_pct":           round(len(wfh)/len(users)*100, 1) if users else 0,
        "wfo_pct":           round(len(wfo)/len(users)*100, 1) if users else 0,
        "total_hours":       round(total_hrs, 1),
        "total_points":      total_pts,
        "total_actions":     total_acts,
        "flagged_count":     flagged,
        "gps_verified_count": gps_ok,
        "gps_pct":           round(gps_ok/len(users)*100, 1) if users else 0,
        "avg_hours":         round(total_hrs/len(users), 1) if users else 0,
        "avg_points":        round(total_pts/len(users), 1) if users else 0,
        "actions_per_person": actions_per_person,
        "active_depts":      len(depts),
        "total_depts":       len(depts),
        "productivity_score": productivity,
        "compliance_rate":    compliance,
    }


def _get_leaderboard(date, department=None):
    """Get top performers leaderboard"""
    dept_cond = "AND e.department = %(dept)s" if department else ""
    
    return frappe.db.sql("""
        SELECT 
            al.employee,
            e.employee_name,
            e.department,
            e.designation,
            SUM(COALESCE(al.points, 0)) AS total_points,
            COUNT(*) AS total_actions,
            COUNT(DISTINCT al.reference_doctype) AS unique_doctypes,
            MAX(al.timestamp) AS last_activity
        FROM `tabWork Activity Log` al
        LEFT JOIN `tabEmployee` e ON e.name = al.employee
        WHERE al.date = %(date)s
          {dept_cond}
        GROUP BY al.employee, e.employee_name, e.department, e.designation
        ORDER BY total_points DESC
        LIMIT 20
    """.format(dept_cond=dept_cond), 
    {"date": date, "dept": department or ""}, 
    as_dict=True)


def _get_department_breakdown(date):
    """Get performance breakdown by department"""
    return frappe.db.sql("""
        SELECT 
            e.department,
            COUNT(DISTINCT al.employee) AS count,
            SUM(COALESCE(al.points, 0)) AS total_points,
            ROUND(AVG(COALESCE(al.points, 0)), 1) AS avg_points,
            COUNT(*) AS total_actions,
            ROUND(SUM(COALESCE(al.points, 0)) / COUNT(DISTINCT al.employee), 1) AS points_per_person
        FROM `tabWork Activity Log` al
        INNER JOIN `tabEmployee` e ON e.name = al.employee
        WHERE al.date = %(date)s
          AND e.department IS NOT NULL
          AND e.department != ''
        GROUP BY e.department
        ORDER BY total_points DESC
    """, {"date": date}, as_dict=True)


def _detect_anomalies(users, date):
    """Detect anomalies in workforce data"""
    anomalies = []
    
    # Flagged users
    flagged = [u for u in users if u.get("inactivity_flag")]
    if flagged:
        names = ", ".join(u['display_name'] for u in flagged[:3])
        anomalies.append({
            "title": f"{len(flagged)} Flagged Session(s)",
            "description": f"{names}{'...' if len(flagged) > 3 else ''} have been idle for too long.",
            "severity": "high"
        })
    
    # Zero activity users
    zero_act = [u for u in users if u.get("activity_count", 0) == 0 and u.get("total_hours", 0) > 2]
    if zero_act:
        names = ", ".join(u['display_name'] for u in zero_act[:3])
        anomalies.append({
            "title": f"{len(zero_act)} User(s) with No Activity",
            "description": f"{names}{'...' if len(zero_act) > 3 else ''} logged in for hours with no recorded activity.",
            "severity": "medium"
        })
    
    # Low GPS compliance
    no_gps = [u for u in users if not u.get("gps_verified")]
    if len(no_gps) > len(users) * 0.5 and len(users) > 2:
        anomalies.append({
            "title": "Low GPS Compliance",
            "description": f"Only {len(users)-len(no_gps)} out of {len(users)} users have GPS verified.",
            "severity": "low"
        })
    
    # Unusually low activity day
    if users and len(users) > 3:
        avg_pts = sum(u.get("activity_points", 0) for u in users) / len(users)
        if avg_pts < 10:
            anomalies.append({
                "title": "Low Activity Day",
                "description": f"Average points per person is only {round(avg_pts, 1)}. This is unusually low.",
                "severity": "medium"
            })
    
    return anomalies


def _get_attention_required(users, date, department=None):
    """Get list of items requiring attention"""
    items = []
    
    # Flagged sessions
    for u in users:
        if u.get("inactivity_flag"):
            items.append({
                "icon": "⚠",
                "title": f"{u['display_name']} - Inactive Session",
                "description": f"Last active: {u['last_active_str']}. Session may need review.",
                "action": f"Form/Work Session/{u['session_name']}",
                "action_label": "View Session"
            })
    
    # Low performers
    for u in users:
        if u.get("activity_points", 0) < 10 and u.get("total_hours", 0) > 4:
            items.append({
                "icon": "📉",
                "title": f"{u['display_name']} - Low Activity",
                "description": f"Only {u['activity_points']} points in {u['total_hours']}h.",
                "action": f"Form/Work Session/{u['session_name']}",
                "action_label": "Review"
            })
    
    # Extended sessions
    for u in users:
        if u.get("status") == "Open" and u.get("total_hours", 0) > 12:
            items.append({
                "icon": "🕐",
                "title": f"{u['display_name']} - Extended Session",
                "description": f"Active for {u['total_hours']}h. May have forgotten to check out.",
                "action": f"Form/Work Session/{u['session_name']}",
                "action_label": "Check Session"
            })
    
    return items[:10]


def _recent_activity(date):
    """Get recent activity logs for the date"""
    return frappe.db.sql("""
        SELECT 
            al.employee,
            COALESCE(e.employee_name, al.employee) AS employee_name,
            al.reference_doctype,
            al.reference_name,
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