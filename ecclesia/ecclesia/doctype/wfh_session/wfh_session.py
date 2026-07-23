# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

"""
WFH Session Controller
Ecclesia Module – ERPNext

GPS is OPTIONAL throughout. Every function works fully without it.
When an employee grants browser location permission, coordinates are
stored and gps_verified is set to 1. When permission is denied or
the browser does not support geolocation, check-in proceeds normally
and gps_verified stays 0 — this is not treated as a flag or error.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
    now_datetime, getdate, nowdate, get_datetime,
    time_diff_in_hours, cint, flt
)


class WFHSession(Document):

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def before_insert(self):
        self._guard_duplicate_open_session()
        self._link_wfh_request()

    def validate(self):
        self._calc_total_hours()
        self._validate_session_date()

    def on_submit(self):
        if self.status == "Open":
            self.status = "Closed"
            if not self.check_out_time:
                self.check_out_time = now_datetime()
            self._calc_total_hours()
            self.db_update()

    # ── Private helpers ────────────────────────────────────────────────────────

    def _guard_duplicate_open_session(self):
        try:
            existing = frappe.db.exists(
                "WFH Session",
                {
                    "employee": self.employee,
                    "date":     self.date or nowdate(),
                    "status":   "Open",
                    "docstatus": ("!=", 2),
                },
            )
            if existing:
                frappe.throw(
                    _("An open WFH Session already exists for {0} on {1}: {2}").format(
                        self.employee_name or self.employee, self.date, existing
                    )
                )
        except Exception as e:
            frappe.log_error(
                f"Error in _guard_duplicate_open_session: {str(e)}",
                "WFH Session Error"
            )
            frappe.throw(_("Error checking existing sessions. Please try again."))

    def _link_wfh_request(self):
        if self.wfh_request:
            return
        
        try:
            result = frappe.db.sql(
                """
                SELECT name FROM `tabWFH Request`
                WHERE employee  = %s
                  AND status    = 'Approved'
                  AND from_date <= %s
                  AND to_date   >= %s
                  AND docstatus  = 1
                LIMIT 1
                """,
                (self.employee, self.date or nowdate(), self.date or nowdate()),
                as_dict=True,
            )
            if result:
                self.wfh_request = result[0].name

            # Strict mode - check if custom field exists before using it
            strict = 0
            try:
                strict = cint(
                    frappe.db.get_single_value("HR Settings", "wfh_strict_mode") or 0
                )
            except Exception:
                # Field doesn't exist, skip strict mode check
                pass
            
            if strict and not self.wfh_request:
                frappe.throw(
                    _("No approved WFH Request found for {0} on {1}. "
                      "Session cannot be created.").format(self.employee, self.date)
                )
        except Exception as e:
            if "No approved WFH Request" in str(e):
                raise
            frappe.log_error(
                f"Error in _link_wfh_request: {str(e)}",
                "WFH Session Error"
            )

    def _calc_total_hours(self):
        try:
            if self.check_in_time and self.check_out_time:
                diff = time_diff_in_hours(self.check_out_time, self.check_in_time)
                self.total_hours = round(max(diff, 0), 2)
            elif self.check_in_time and self.status == "Open":
                diff = time_diff_in_hours(now_datetime(), self.check_in_time)
                self.total_hours = round(max(diff, 0), 2)
        except Exception as e:
            frappe.log_error(
                f"Error in _calc_total_hours: {str(e)}",
                "WFH Session Error"
            )

    def _validate_session_date(self):
        try:
            if self.date and getdate(self.date) > getdate(nowdate()):
                frappe.throw(_("Cannot create a WFH Session for a future date."))
        except Exception as e:
            frappe.log_error(
                f"Error in _validate_session_date: {str(e)}",
                "WFH Session Error"
            )


# ── Whitelisted API ────────────────────────────────────────────────────────────

@frappe.whitelist()
def check_in(employee=None, latitude=None, longitude=None, accuracy=None):
    """
    Create or return today's open WFH Session.

    GPS parameters (latitude, longitude, accuracy) are all optional.
    - If provided → stored on the session, gps_verified = 1
    - If not provided → session created normally, gps_verified = 0
    - A session without GPS is fully valid and not flagged

    Called from:
      - WFH Session form (Check In button)
      - WFH Dashboard page (GPS check-in widget)
      - Mobile/API integration
    """
    # CRITICAL: Check session user first before ANY database operation
    try:
        # Safely get user session
        if not frappe.session:
            frappe.throw(_("No active session. Please log in."))
        
        user = frappe.session.user if frappe.session.user else None
    except Exception:
        frappe.throw(_("Error accessing user session. Please log in again."))
    
    if not user or user == "Guest":
        frappe.throw(_("No active user session. Please log in."))

    # Only proceed if we have a valid user
    if not employee:
        try:
            employee = frappe.db.get_value(
                "Employee", {"user_id": user}, "name"
            )
        except Exception as e:
            frappe.log_error(
                f"Error fetching employee for user {user}: {str(e)}",
                "WFH Session Error"
            )
            frappe.throw(_("Error fetching employee record. Please try again."))
    
    if not employee:
        frappe.throw(_("No Employee record linked to the current user."))

    today = nowdate()

    # Return existing open session rather than creating a duplicate
    try:
        existing = frappe.db.get_value(
            "WFH Session",
            {
                "employee": employee,
                "date":     today,
                "status":   "Open",
                "docstatus": ("!=", 2),
            },
            "name",
        )
    except Exception as e:
        frappe.log_error(
            f"Error checking existing sessions for employee {employee}: {str(e)}",
            "WFH Session Error"
        )
        frappe.throw(_("Error checking existing sessions. Please try again."))
    
    if existing:
        # If GPS was not captured before but is now available, update it
        if latitude and longitude:
            try:
                frappe.db.set_value(
                    "WFH Session", existing,
                    {
                        "latitude":     flt(latitude),
                        "longitude":    flt(longitude),
                        "gps_accuracy": flt(accuracy) if accuracy else None,
                        "gps_verified": 1,
                    },
                    update_modified=False,
                )
            except Exception as e:
                frappe.log_error(
                    f"Error updating GPS for session {existing}: {str(e)}",
                    "WFH Session Error"
                )
                # GPS update is optional, don't fail if it errors
        return frappe.get_doc("WFH Session", existing)

    # Create new session
    try:
        session = frappe.new_doc("WFH Session")
        session.employee      = employee
        session.date          = today
        session.check_in_time = now_datetime()
        session.status        = "Open"

        # Capture IP and browser info (always — not GPS-dependent)
        try:
            if hasattr(frappe.local, 'request_ip'):
                session.ip_address = frappe.local.request_ip
            if frappe.request and hasattr(frappe.request, 'headers'):
                user_agent = frappe.request.headers.get("User-Agent") or ""
                session.device_info = user_agent[:200]
        except Exception:
            pass

        # GPS — store only if coordinates were actually provided
        if latitude and longitude:
            session.latitude     = flt(latitude)
            session.longitude    = flt(longitude)
            session.gps_accuracy = flt(accuracy) if accuracy else None
            session.gps_verified = 1
        else:
            session.gps_verified = 0   # explicit, not a flag — just informational

        session.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return session
        
    except Exception as e:
        frappe.log_error(
            f"Error creating WFH Session for employee {employee}: {str(e)}",
            "WFH Session Error"
        )
        frappe.throw(_("Error creating WFH Session. Please try again."))


@frappe.whitelist()
def check_out(session_name):
    """Close a WFH Session and record check-out time."""
    # Check session user first
    try:
        if not frappe.session:
            frappe.throw(_("No active session. Please log in."))
        
        user = frappe.session.user if frappe.session.user else None
    except Exception:
        frappe.throw(_("Error accessing user session. Please log in again."))
    
    if not user or user == "Guest":
        frappe.throw(_("No active user session. Please log in."))

    if not session_name:
        frappe.throw(_("Session name is required."))

    try:
        doc = frappe.get_doc("WFH Session", session_name)
    except Exception as e:
        frappe.log_error(
            f"Error fetching WFH Session {session_name}: {str(e)}",
            "WFH Session Error"
        )
        frappe.throw(_("Error fetching WFH Session. Please try again."))
    
    if doc.status != "Open":
        frappe.throw(_("Session is not Open."))
    
    try:
        doc.check_out_time = now_datetime()
        doc.status         = "Closed"
        doc._calc_total_hours()
        doc.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(
            f"Error updating WFH Session {session_name}: {str(e)}",
            "WFH Session Error"
        )
        frappe.throw(_("Error updating WFH Session. Please try again."))
    
    return doc


@frappe.whitelist()
def get_today_session(employee=None):
    """Return today's session for the employee (or current user's employee)."""
    # Check session user first
    try:
        if not frappe.session:
            return None
        
        user = frappe.session.user if frappe.session.user else None
    except Exception:
        return None
    
    if not user or user == "Guest":
        return None

    if not employee:
        try:
            employee = frappe.db.get_value(
                "Employee", {"user_id": user}, "name"
            )
        except Exception:
            return None
    
    if not employee:
        return None
    
    try:
        return frappe.db.get_value(
            "WFH Session",
            {"employee": employee, "date": nowdate(), "docstatus": ("!=", 2)},
            ["name", "check_in_time", "check_out_time", "total_hours",
             "status", "gps_verified", "latitude", "longitude"],
            as_dict=True,
        )
    except Exception:
        return None


def flag_inactive_sessions():
    """
    Scheduler (hourly): flag sessions with no activity for > threshold hours.
    Inactivity is based on work activity logs, NOT on GPS presence.
    A session without GPS coordinates is never flagged by this function.
    """
    # This function might be called by scheduler without user session
    
    # Check if custom field exists before using it
    threshold = 3  # default value
    try:
        threshold = flt(
            frappe.db.get_single_value("WFH Activity Mapping", "inactivity_threshold_hours") or 3
        )
    except Exception:
        # Field or DocType doesn't exist, use default
        pass
    
    try:
        open_sessions = frappe.get_all(
            "WFH Session",
            filters={"status": "Open", "docstatus": ("!=", 2)},
            fields=["name", "employee", "last_activity_time", "check_in_time"],
        )
    except Exception as e:
        frappe.log_error(
            f"Error fetching open sessions in flag_inactive_sessions: {str(e)}",
            "WFH Session Scheduler Error"
        )
        return  # Exit if we can't fetch sessions
    
    for s in open_sessions:
        try:
            reference = s.last_activity_time or s.check_in_time
            if not reference:
                continue
            idle = time_diff_in_hours(now_datetime(), reference)
            if idle >= threshold:
                frappe.db.set_value(
                    "WFH Session", s.name,
                    {"inactivity_flag": 1, "status": "Flagged"},
                    update_modified=False,
                )
        except Exception as e:
            frappe.log_error(
                f"Error flagging inactive session {s.name}: {str(e)}",
                "WFH Session Scheduler Error"
            )
            continue
    
    try:
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(
            f"Error committing in flag_inactive_sessions: {str(e)}",
            "WFH Session Scheduler Error"
        )