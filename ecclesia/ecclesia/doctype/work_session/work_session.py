# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

"""
Work Session Controller
Ecclesia Module

CRITICAL DESIGN:
  Check-in time = ERPNext login timestamp (set by on_login hook in hooks.py).
  Users CANNOT manually enter check-in time — this prevents fraud.
  The login hook calls work_session.open_session_on_login() which creates
  the session with check_in_time = frappe.utils.now_datetime().

All import paths use ecclesia.ecclesia.* (double prefix — Frappe convention
when app folder name matches app name).
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
    now_datetime, getdate, nowdate,
    time_diff_in_hours, flt
)


class WorkSession(Document):

    def before_insert(self):
        self._resolve_user_identity()
        self._guard_duplicate()
        self._auto_detect_work_mode()

    def validate(self):
        self._calc_total_hours()
        self._validate_not_future()

    def on_submit(self):
        if self.status == "Open":
            self.status = "Closed"
            if not self.check_out_time:
                self.check_out_time = now_datetime()
            self._calc_total_hours()
            self.db_update()

    # ── Private ────────────────────────────────────────────────────────────────

    def _resolve_user_identity(self):
        if not self.user:
            self.user = frappe.session.user
        emp = frappe.db.get_value(
            "Employee",
            {"user_id": self.user, "status": "Active"},
            ["name", "employee_name", "department"],
            as_dict=True,
        )
        if emp:
            self.employee      = emp.name
            self.employee_name = emp.employee_name
            self.department    = emp.department if hasattr(self, "department") else None
        if not self.employee_name:
            self.employee_name = (
                frappe.db.get_value("User", self.user, "full_name") or self.user
            )

    def _guard_duplicate(self):
        existing = frappe.db.get_value(
            "Work Session",
            {
                "user":     self.user,
                "date":     self.date or nowdate(),
                "status":   ("in", ["Open", "Flagged"]),
                "docstatus": ("!=", 2),
            },
            "name",
        )
        if existing:
            frappe.throw(
                _("An open Work Session already exists for {0} on {1}: {2}").format(
                    self.employee_name, self.date, existing
                )
            )

    def _auto_detect_work_mode(self):
        """Auto-set work_mode from WFH Schedule if not explicitly provided."""
        if self.work_mode and self.work_mode not in ("WFH", ""):
            return
        if not self.employee:
            return
        try:
            from ecclesia.ecclesia.doctype.wfh_schedule.wfh_schedule import (
                get_today_work_mode, get_schedule_for_employee
            )
            mode = get_today_work_mode(self.employee)
            if mode in ("WFH", "WFO"):
                self.work_mode = mode

            schedule = get_schedule_for_employee(self.employee, self.date)
            if schedule:
                self.wfh_schedule = schedule.name

        except Exception as e:
            frappe.log_error(f"WorkSession auto-detect error: {e}", "Work Session")

        # Link ad-hoc WFH Request if no schedule found
        if self.work_mode == "WFH" and not self.wfh_schedule:
            req = frappe.db.sql("""
                SELECT name FROM `tabWFH Request`
                WHERE employee  = %s
                  AND status    = 'Approved'
                  AND from_date <= %s
                  AND to_date   >= %s
                  AND docstatus  = 1
                LIMIT 1
            """, (self.employee, self.date, self.date))
            if req:
                self.wfh_request = req[0][0]
                self.is_adhoc    = 1

    def _calc_total_hours(self):
        if self.check_in_time and self.check_out_time:
            self.total_hours = round(
                max(time_diff_in_hours(self.check_out_time, self.check_in_time), 0), 2
            )
        elif self.check_in_time and self.status in ("Open", "Flagged"):
            self.total_hours = round(
                max(time_diff_in_hours(now_datetime(), self.check_in_time), 0), 2
            )

    def _validate_not_future(self):
        if self.date and getdate(self.date) > getdate(nowdate()):
            frappe.throw(_("Cannot create a Work Session for a future date."))


# ── Login Hook (called from hooks.py on_login) ────────────────────────────────

def open_session_on_login(login_manager=None):
    """
    Called by hooks.py on_login event.
    Creates a Work Session with check_in_time = now (actual login time).
    This is the ONLY way a session gets a check-in time — preventing fraud.

    If a session already exists today (e.g. re-login after browser close),
    the existing session is kept; the login time is NOT overwritten.
    """
    try:
        user = frappe.session.user
        if user in ("Guest", "Administrator"):
            return

        today = nowdate()
        existing = frappe.db.get_value(
            "Work Session",
            {"user": user, "date": today, "docstatus": ("!=", 2)},
            ["name", "check_in_time", "status"],
            as_dict=True,
        )

        if existing:
            # Already has a session today — update last_seen but don't change check_in
            frappe.db.set_value(
                "Work Session", existing.name,
                {"last_activity_time": now_datetime()},
                update_modified=False,
            )
            return

        # Create new session — check_in_time = this exact login moment
        session = frappe.new_doc("Work Session")
        session.user           = user
        session.date           = today
        session.check_in_time  = now_datetime()   # ← LOCKED to actual login time
        session.status         = "Open"
        session.work_mode      = "WFH"   # will be corrected by _auto_detect_work_mode

        try:
            session.ip_address  = frappe.local.request_ip
            session.device_info = (
                frappe.request.headers.get("User-Agent") or ""
            )[:200]
        except Exception:
            pass

        session.insert(ignore_permissions=True)
        frappe.db.commit()

    except Exception as e:
        # Never break the login flow
        frappe.log_error(f"Work Session on_login error: {e}", "Work Session Login Hook")


# ── Whitelisted API ────────────────────────────────────────────────────────────

@frappe.whitelist()
def check_out(session_name):
    """Record check-out time and close the session."""
    doc = frappe.get_doc("Work Session", session_name)
    if doc.status not in ("Open", "Flagged"):
        frappe.throw(_("Session is not Open."))
    # Verify ownership (employee or HR)
    if (doc.user != frappe.session.user and
            not frappe.user.has_role(["HR Manager", "System Manager", "Line Manager"])):
        frappe.throw(_("You can only check out your own session."))
    doc.check_out_time = now_datetime()
    doc.status         = "Closed"
    doc._calc_total_hours()
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return doc.as_dict()


@frappe.whitelist()
def update_gps(session_name, latitude, longitude, accuracy=None):
    """Optionally attach GPS coordinates to an existing session."""
    doc = frappe.get_doc("Work Session", session_name)
    if doc.user != frappe.session.user and not frappe.user.has_role(["HR Manager", "System Manager"]):
        frappe.throw(_("You can only update your own session."))
    doc.latitude     = flt(latitude)
    doc.longitude    = flt(longitude)
    doc.gps_accuracy = flt(accuracy) if accuracy else None
    doc.gps_verified = 1
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"latitude": doc.latitude, "longitude": doc.longitude}


@frappe.whitelist()
def get_my_session(date=None):
    """Return current user's Work Session for today."""
    date = date or nowdate()
    return frappe.db.get_value(
        "Work Session",
        {"user": frappe.session.user, "date": date, "docstatus": ("!=", 2)},
        ["name", "work_mode", "check_in_time", "check_out_time",
         "total_hours", "status", "gps_verified", "location_label",
         "employee", "employee_name"],
        as_dict=True,
    )


@frappe.whitelist()
def get_live_users(date=None):
    """
    Return all Work Sessions for today with enriched data.
    Called by Live Dashboard. Works for all users.
    """
    date = date or nowdate()
    return frappe.db.sql("""
        SELECT
            s.name, s.user, s.employee, s.employee_name,
            s.work_mode, s.location_label, s.date,
            s.check_in_time, s.check_out_time,
            COALESCE(s.total_hours, 0)    AS total_hours,
            s.status,
            COALESCE(s.inactivity_flag,0) AS inactivity_flag,
            COALESCE(s.gps_verified, 0)   AS gps_verified,
            u.full_name                   AS user_full_name,
            u.user_image,
            COALESCE(e.department, '')    AS department,
            COALESCE(e.designation, '')   AS designation,
            COALESCE(
                (SELECT SUM(al.points)
                 FROM `tabWork Activity Log` al
                 WHERE al.employee = s.employee AND al.date = s.date), 0
            ) AS activity_points,
            COALESCE(
                (SELECT COUNT(*)
                 FROM `tabWork Activity Log` al2
                 WHERE al2.employee = s.employee AND al2.date = s.date), 0
            ) AS activity_count,
            COALESCE(
                (SELECT al3.reference_doctype
                 FROM `tabWork Activity Log` al3
                 WHERE al3.employee = s.employee AND al3.date = s.date
                 ORDER BY al3.timestamp DESC LIMIT 1), ''
            ) AS last_action_doc
        FROM `tabWork Session` s
        JOIN `tabUser` u ON u.name = s.user
        LEFT JOIN `tabEmployee` e ON e.name = s.employee
        WHERE s.date = %s AND s.docstatus != 2
        ORDER BY s.check_in_time ASC
    """, date, as_dict=True)


def flag_inactive_sessions():
    """Scheduler (hourly): flag sessions with no activity > threshold."""
    threshold = flt(
        frappe.db.get_single_value("WFH Activity Mapping", "inactivity_threshold_hours") or 3
    )
    open_sessions = frappe.get_all(
        "Work Session",
        filters={"status": "Open", "docstatus": ("!=", 2)},
        fields=["name", "employee", "last_activity_time", "check_in_time"],
    )
    for s in open_sessions:
        ref = s.last_activity_time or s.check_in_time
        if not ref:
            continue
        if time_diff_in_hours(now_datetime(), ref) >= threshold:
            frappe.db.set_value(
                "Work Session", s.name,
                {"inactivity_flag": 1, "status": "Flagged"},
                update_modified=False,
            )
    frappe.db.commit()