# Copyright (c) 2026, Ecclesia Enterprise — License: MIT
# ecclesia/ess_portal_leave.py

import frappe
from frappe.utils import today, getdate, date_diff


def _get_employee():
    emp = frappe.db.get_value(
        "Employee",
        {"user_id": frappe.session.user, "status": "Active"},
        ["name", "employee_name", "company", "department"],
        as_dict=True,
    )
    if not emp:
        frappe.throw("No active Employee record linked to your account.")
    return emp


@frappe.whitelist()
def submit_leave_application(
    leave_type, from_date, to_date,
    half_day=0, half_day_date=None,
    description="", save_draft=0
):
    emp = _get_employee()

    doc = frappe.new_doc("Leave Application")
    doc.employee        = emp.name
    doc.leave_type      = leave_type
    doc.from_date       = from_date
    doc.to_date         = to_date
    doc.half_day        = int(half_day)
    doc.half_day_date   = half_day_date or from_date
    doc.description     = description
    doc.status          = "Open"

    doc.insert(ignore_permissions=True)

    if not int(save_draft):
        doc.submit()

    return {"name": doc.name, "status": doc.status}


@frappe.whitelist()
def get_leave_applications():
    emp = _get_employee()

    records = frappe.get_all(
        "Leave Application",
        filters={"employee": emp.name, "docstatus": ["!=", 2]},
        fields=["name", "leave_type", "from_date", "to_date",
                "total_leave_days", "status", "description"],
        order_by="from_date desc",
        limit=20,
    )
    return records


@frappe.whitelist()
def get_leave_balance():
    emp = _get_employee()
    from frappe.utils import getdate
    today_d = getdate(today())

    allocs = frappe.get_all(
        "Leave Allocation",
        filters={"employee": emp.name, "docstatus": 1},
        fields=["leave_type", "total_leaves_allocated", "from_date", "to_date"],
    )
    result = []
    for a in allocs:
        if not (getdate(a.from_date) <= today_d <= getdate(a.to_date)):
            continue
        used = frappe.db.count(
            "Leave Application",
            {"employee": emp.name, "leave_type": a.leave_type,
             "status": "Approved", "docstatus": 1},
        )
        allocated = float(a.total_leaves_allocated or 0)
        result.append({
            "leave_type": a.leave_type,
            "allocated":  allocated,
            "used":       used,
            "remaining":  allocated - used,
        })
    return result