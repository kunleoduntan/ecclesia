"""
WFH Schedule Controller  (ecclesia/ecclesia/doctype/wfh_schedule/wfh_schedule.py)
All import paths use ecclesia.ecclesia.* convention.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

DAY_FIELDS = {
    "monday":0,"tuesday":1,"wednesday":2,
    "thursday":3,"friday":4,"saturday":5,"sunday":6,
}


class WFHSchedule(Document):

    def validate(self):
        self._validate_dates()
        self._validate_at_least_one_day()
        self._check_conflicts()

    def on_submit(self):
        frappe.cache().delete_key("wfh_schedule_cache")

    def on_cancel(self):
        frappe.cache().delete_key("wfh_schedule_cache")

    def _validate_dates(self):
        if self.effective_from and self.effective_to:
            if getdate(self.effective_from) > getdate(self.effective_to):
                frappe.throw(_("Effective From cannot be after Effective To."))

    def _validate_at_least_one_day(self):
        if not any(self.get(f) for f in DAY_FIELDS):
            frappe.throw(_("Select at least one WFH day."))

    def _check_conflicts(self):
        filters = {"applies_to": self.applies_to, "is_active": 1, "docstatus": 1}
        if self.applies_to == "Department":
            filters["department"] = self.department
        elif self.applies_to == "Individual Employee":
            filters["employee"] = self.employee
        if not self.is_new():
            filters["name"] = ("!=", self.name)
        for s in frappe.get_all("WFH Schedule", filters=filters,
                                 fields=["name","title","effective_from","effective_to"]):
            s_from = getdate(s.effective_from)
            s_to   = getdate(s.effective_to) if s.effective_to else None
            my_from = getdate(self.effective_from)
            my_to   = getdate(self.effective_to) if self.effective_to else None
            overlap = not ((my_to and my_to < s_from) or (s_to and s_to < my_from))
            if overlap:
                frappe.msgprint(
                    _("Warning: Schedule <b>{0}</b> overlaps for the same scope.").format(s.title),
                    indicator="orange", alert=True)


# ── Runtime helpers ────────────────────────────────────────────────────────────

def get_schedule_for_employee(employee, date=None):
    """Return best-match WFH Schedule for employee on date. Priority: Individual > Dept > All."""
    date = getdate(date or nowdate())
    dept = frappe.db.get_value("Employee", employee, "department") or ""
    rows = frappe.db.sql("""
        SELECT name, applies_to, monday, tuesday, wednesday,
               thursday, friday, saturday, sunday,
               allow_adhoc_request, auto_create_session, require_summary
        FROM `tabWFH Schedule`
        WHERE docstatus=1 AND is_active=1
          AND effective_from <= %(date)s
          AND (effective_to IS NULL OR effective_to >= %(date)s)
          AND (applies_to='All Employees'
               OR (applies_to='Department' AND department=%(dept)s)
               OR (applies_to='Individual Employee' AND employee=%(emp)s))
        ORDER BY CASE applies_to
            WHEN 'Individual Employee' THEN 1
            WHEN 'Department' THEN 2
            ELSE 3 END
        LIMIT 1
    """, {"date": date, "dept": dept, "emp": employee}, as_dict=True)
    return rows[0] if rows else None


def is_scheduled_wfh_day(employee, date=None):
    date = getdate(date or nowdate())
    schedule = get_schedule_for_employee(employee, date)
    if not schedule:
        return False
    day_name = next((k for k, v in DAY_FIELDS.items() if v == date.weekday()), None)
    return bool(day_name and schedule.get(day_name))


def is_scheduled_wfo_day(employee, date=None):
    date = getdate(date or nowdate())
    if date.weekday() >= 5:
        return False
    return not is_scheduled_wfh_day(employee, date)


def get_today_work_mode(employee):
    today = nowdate()
    adhoc = frappe.db.sql("""
        SELECT name FROM `tabWFH Request`
        WHERE employee=%s AND status='Approved'
          AND from_date<=%s AND to_date>=%s AND docstatus=1
        LIMIT 1
    """, (employee, today, today))
    if adhoc:
        return "WFH"
    if is_scheduled_wfh_day(employee, today):
        return "WFH"
    if is_scheduled_wfo_day(employee, today):
        return "WFO"
    return "Unknown"


@frappe.whitelist()
def get_employee_schedule(employee=None, date=None):
    if not employee:
        employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
    if not employee:
        return {"work_mode": "Unknown", "schedule": None}
    schedule  = get_schedule_for_employee(employee, date)
    work_mode = get_today_work_mode(employee)
    return {
        "employee":  employee,
        "work_mode": work_mode,
        "is_wfh":    work_mode == "WFH",
        "is_wfo":    work_mode == "WFO",
        "schedule":  schedule,
    }


@frappe.whitelist()
def get_employees_on_schedule(schedule_name):
    doc = frappe.get_doc("WFH Schedule", schedule_name)
    if doc.applies_to == "Individual Employee":
        emp = frappe.db.get_value("Employee", doc.employee,
                                   ["name","employee_name","department"], as_dict=True)
        return [emp] if emp else []
    elif doc.applies_to == "Department":
        return frappe.get_all("Employee",
            filters={"department": doc.department, "status": "Active"},
            fields=["name","employee_name","department"])
    else:
        return frappe.get_all("Employee",
            filters={"status": "Active"},
            fields=["name","employee_name","department"])


def auto_open_sessions_for_today():
    """Scheduler (daily morning): auto-create Work Sessions for employees on auto-create schedules."""
    today = nowdate()
    for emp in frappe.get_all("Employee", filters={"status": "Active"},
                               fields=["name","employee_name"]):
        schedule = get_schedule_for_employee(emp.name, today)
        if not schedule or not schedule.auto_create_session:
            continue
        if not is_scheduled_wfh_day(emp.name, today):
            continue
        if frappe.db.exists("Work Session",
                            {"employee": emp.name, "date": today, "docstatus": ("!=", 2)}):
            continue
        try:
            # FIXED import path ↓
            from ecclesia.ecclesia.doctype.work_session.work_session import (
                open_session_on_login
            )
            # Build a minimal login_manager substitute
            class _FakeLogin:
                user = emp.name
            frappe.session.user = frappe.db.get_value("Employee", emp.name, "user_id") or "Administrator"
            open_session_on_login()
        except Exception as e:
            frappe.log_error(f"Auto session for {emp.employee_name}: {e}", "WFH Schedule")
    frappe.db.commit()