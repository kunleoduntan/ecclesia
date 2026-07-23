"""
Ecclesia – Session Hooks  (ecclesia/api/session_hooks.py)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Handles:
  1. Automatic Work Session creation on login
  2. Session heartbeat update on logout
  3. Auto-detection of WFH/WFO mode
  4. Auto-close stale sessions (scheduler)
"""

import frappe
from frappe.utils import now_datetime, nowdate


# ── Login Hook ────────────────────────────────────────────────────────────────

def on_login(login_manager):
    """
    Called automatically when a user logs in.
    Creates a Work Session for the employee if one doesn't exist today.
    """
    try:
        user = frappe.session.user
        
        # Skip for guest users
        if user == "Guest":
            return
        
        # Get employee record (Administrator can also have one)
        employee = frappe.db.get_value(
            "Employee",
            {"user_id": user, "status": "Active"},
            "name"
        )
        
        if not employee:
            return  # Not an employee — skip
        
        # Check if already have an open session today
        existing = _get_open_session(employee)
        if existing:
            return  # Session already exists
        
        # Auto-detect work mode
        work_mode = _detect_work_mode(employee)
        
        # Create automatic Work Session
        _create_auto_session(employee, work_mode)
        
    except Exception as e:
        frappe.log_error(
            title="Auto Check-In Error",
            message=f"User: {frappe.session.user}\nError: {str(e)}\n{frappe.get_traceback()}"
        )


# ── Logout Hook ───────────────────────────────────────────────────────────────

def on_logout(login_manager):
    """
    Called when a user logs out.
    Updates the last activity time on any open session.
    Does NOT close the session (session remains open for the day).
    """
    try:
        user = frappe.session.user
        
        if user == "Guest":
            return
        
        employee = frappe.db.get_value(
            "Employee",
            {"user_id": user, "status": "Active"},
            "name"
        )
        
        if not employee:
            return
        
        # Find open session
        session = _get_open_session(employee)
        
        if session:
            # Update last activity time
            _update_last_activity(session)
            
    except Exception as e:
        frappe.log_error(
            title="Logout Hook Error",
            message=f"User: {user}\nError: {str(e)}"
        )


# ── Session Cleanup Scheduler ─────────────────────────────────────────────────

def close_all_open_sessions():
    """
    Scheduler job: Close all open sessions from previous days.
    Run this daily at midnight or configured time.
    """
    try:
        # Close open Work Sessions from previous days
        open_work = frappe.get_all(
            "Work Session",
            filters={
                "status": "Open",
                "date": ("<", nowdate()),
                "docstatus": ("!=", 2)
            },
            fields=["name"]
        )
        
        for session in open_work:
            try:
                frappe.db.set_value(
                    "Work Session",
                    session.name,
                    {
                        "check_out_time": now_datetime(),
                        "status": "Closed"
                    },
                    update_modified=False
                )
            except Exception:
                pass
        
        # Close open WFH Sessions from previous days
        open_wfh = frappe.get_all(
            "WFH Session",
            filters={
                "status": "Open",
                "date": ("<", nowdate()),
                "docstatus": ("!=", 2)
            },
            fields=["name"]
        )
        
        for session in open_wfh:
            try:
                frappe.db.set_value(
                    "WFH Session",
                    session.name,
                    {
                        "check_out_time": now_datetime(),
                        "status": "Closed"
                    },
                    update_modified=False
                )
            except Exception:
                pass
        
        frappe.db.commit()
        
        total = len(open_work) + len(open_wfh)
        if total > 0:
            frappe.log_error(
                f"Auto-closed {total} sessions from previous days",
                "Session Cleanup"
            )
            
    except Exception as e:
        frappe.log_error(
            f"Session cleanup error: {str(e)}",
            "Session Cleanup"
        )


# ── Whitelisted API ───────────────────────────────────────────────────────────

@frappe.whitelist()
def manual_check_in(employee=None, work_mode=None):
    """
    Manual check-in for cases where auto check-in didn't work.
    """
    try:
        if not employee:
            employee = frappe.db.get_value(
                "Employee",
                {"user_id": frappe.session.user, "status": "Active"},
                "name"
            )
        
        if not employee:
            frappe.throw("No employee record found.")
        
        # Check existing session
        existing = _get_open_session(employee)
        if existing:
            return frappe.get_doc("Work Session", existing)
        
        # Detect work mode if not specified
        if not work_mode:
            work_mode = _detect_work_mode(employee)
        
        # Create session
        employee_name = frappe.db.get_value("Employee", employee, "employee_name")
        
        session = frappe.new_doc("Work Session")
        session.employee      = employee
        session.employee_name = employee_name
        session.date          = nowdate()
        session.check_in_time = now_datetime()
        session.work_mode     = work_mode
        session.status        = "Open"
        session.source        = "Manual Check-In"
        
        session.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return session
        
    except Exception as e:
        frappe.log_error(f"Manual check-in error: {str(e)}", "Manual Check-In")
        frappe.throw(f"Check-in failed: {str(e)}")


@frappe.whitelist()
def check_out(session_name):
    """
    Manual check-out.
    """
    try:
        # Try Work Session first
        if frappe.db.exists("Work Session", session_name):
            doc = frappe.get_doc("Work Session", session_name)
        elif frappe.db.exists("WFH Session", session_name):
            doc = frappe.get_doc("WFH Session", session_name)
        else:
            frappe.throw("Session not found.")
        
        if doc.status != "Open":
            frappe.throw("Session is not open.")
        
        doc.check_out_time = now_datetime()
        doc.status = "Closed"
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        
        return doc
        
    except Exception as e:
        frappe.log_error(f"Check-out error: {str(e)}", "Manual Check-Out")
        frappe.throw(f"Check-out failed: {str(e)}")


@frappe.whitelist()
def get_today_session(employee=None):
    """
    Get today's session for the employee.
    """
    try:
        if not employee:
            employee = frappe.db.get_value(
                "Employee",
                {"user_id": frappe.session.user, "status": "Active"},
                "name"
            )
        
        if not employee:
            return None
        
        session_name = _get_open_session(employee)
        
        if session_name:
            # Determine which doctype
            if frappe.db.exists("Work Session", session_name):
                return frappe.get_doc("Work Session", session_name).as_dict()
            elif frappe.db.exists("WFH Session", session_name):
                return frappe.get_doc("WFH Session", session_name).as_dict()
        
        return None
        
    except Exception:
        return None


# ── Helper Functions ──────────────────────────────────────────────────────────

def _get_open_session(employee):
    """
    Find today's open session for an employee.
    Checks Work Session first, then WFH Session.
    Validates session actually exists.
    """
    try:
        # Check Work Session
        session = frappe.db.get_value(
            "Work Session",
            {
                "employee": employee,
                "date": nowdate(),
                "status": ("in", ["Open", "Flagged"]),
                "docstatus": ("!=", 2),
            },
            "name",
            order_by="check_in_time desc"
        )
        if session and frappe.db.exists("Work Session", session):
            return session
        
        # Check WFH Session
        session = frappe.db.get_value(
            "WFH Session",
            {
                "employee": employee,
                "date": nowdate(),
                "status": "Open",
                "docstatus": ("!=", 2),
            },
            "name",
            order_by="check_in_time desc"
        )
        if session and frappe.db.exists("WFH Session", session):
            return session
        
        return None
        
    except Exception:
        return None


def _detect_work_mode(employee):
    """
    Detect work mode (WFH/WFO) for an employee.
    Checks: WFH Schedule → WFH Request → WFO Schedule → Default WFH
    """
    try:
        today = nowdate()
        
        # Check WFH Schedule
        wfh_schedule = frappe.db.sql("""
            SELECT wfh_status 
            FROM `tabWFH Schedule`
            WHERE employee = %s AND date = %s AND docstatus = 1
            LIMIT 1
        """, (employee, today), as_dict=True)
        
        if wfh_schedule:
            status = wfh_schedule[0].wfh_status
            if status in ("WFH", "Work From Home"):
                return "WFH"
            elif status in ("WFO", "Work From Office"):
                return "WFO"
        
        # Check WFH Request
        wfh_request = frappe.db.sql("""
            SELECT name FROM `tabWFH Request`
            WHERE employee = %s AND status = 'Approved'
            AND from_date <= %s AND to_date >= %s AND docstatus = 1
            LIMIT 1
        """, (employee, today, today), as_dict=True)
        
        if wfh_request:
            return "WFH"
        
        # Default: WFH
        return "WFH"
        
    except Exception:
        return "WFH"


def _create_auto_session(employee, work_mode):
    """
    Create automatic Work Session on login.
    """
    try:
        employee_name = frappe.db.get_value("Employee", employee, "employee_name")
        
        session = frappe.new_doc("Work Session")
        session.employee      = employee
        session.employee_name = employee_name
        session.date          = nowdate()
        session.check_in_time = now_datetime()
        session.work_mode     = work_mode
        session.status        = "Open"
        session.auto_created  = 1
        session.source        = "Auto Check-In on Login"
        
        # Capture device info if available
        try:
            if hasattr(frappe.local, 'request_ip'):
                session.ip_address = frappe.local.request_ip
            if frappe.request and hasattr(frappe.request, 'headers'):
                user_agent = frappe.request.headers.get("User-Agent") or ""
                session.device_info = user_agent[:200]
        except Exception:
            pass
        
        session.insert(ignore_permissions=True)
        frappe.db.commit()
        
    except Exception as e:
        frappe.log_error(
            f"Auto session creation error for {employee}: {str(e)}",
            "Session Hooks"
        )


def _update_last_activity(session_name):
    """
    Update last activity timestamp on session.
    """
    try:
        if frappe.db.exists("Work Session", session_name):
            frappe.db.set_value(
                "Work Session",
                session_name,
                {"last_activity_time": now_datetime()},
                update_modified=False
            )
        elif frappe.db.exists("WFH Session", session_name):
            frappe.db.set_value(
                "WFH Session",
                session_name,
                {"last_activity_time": now_datetime()},
                update_modified=False
            )
    except Exception:
        pass