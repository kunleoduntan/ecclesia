import frappe
from frappe.utils import getdate, get_datetime


def process_pending_logs(from_date=None, to_date=None):
    """
    Convert unprocessed Biometric Attendance Logs → ERPNext Attendance.
    Groups IN/OUT pairs per employee per day.
    """
    filters = {"processed": 0}
    if from_date:
        filters["attendance_date"] = [">=", from_date]
    if to_date:
        filters.setdefault("attendance_date", [])
        filters["attendance_date"] = ["between", [from_date or "2000-01-01", to_date]]

    logs = frappe.get_all(
        "Biometric Attendance Log",
        filters=filters,
        fields=["name", "employee", "attendance_date",
                "punch_time", "log_type", "biometric_user_id"],
        order_by="employee, punch_time asc"
    )

    grouped = {}
    for log in logs:
        key = (log.employee, str(log.attendance_date))
        grouped.setdefault(key, []).append(log)

    processed = 0
    for (employee, date), day_logs in grouped.items():
        try:
            _create_or_update_attendance(employee, date, day_logs)
            processed += 1
        except Exception as e:
            frappe.log_error(str(e), f"Ecclesia Processor: {employee} {date}")

    frappe.db.commit()
    return {"processed": processed, "total_logs": len(logs)}


def process_single_log(log_doc):
    """Process all logs for the same employee+date as this log."""
    date = str(log_doc.attendance_date)
    day_logs = frappe.get_all(
        "Biometric Attendance Log",
        filters={"employee": log_doc.employee, "attendance_date": date},
        fields=["name", "punch_time", "log_type"],
        order_by="punch_time asc"
    )
    _create_or_update_attendance(log_doc.employee, date, day_logs)


def _create_or_update_attendance(employee, date, day_logs):
    # Skip if a submitted attendance already exists
    existing = frappe.db.exists("Attendance", {
        "employee": employee,
        "attendance_date": date,
        "docstatus": 1
    })
    if existing:
        _mark_logs_processed(day_logs, existing)
        return

    in_punches  = [l for l in day_logs if l.get("log_type") == "IN"]
    out_punches = [l for l in day_logs if l.get("log_type") == "OUT"]

    if not in_punches:
        return  # No IN punch — cannot create attendance

    first_in  = get_datetime(in_punches[0]["punch_time"])
    last_out  = get_datetime(out_punches[-1]["punch_time"]) if out_punches else None

    att = frappe.get_doc({
        "doctype": "Attendance",
        "employee": employee,
        "attendance_date": date,
        "in_time": first_in,
        "out_time": last_out,
        "status": "Present"
    })
    att.insert(ignore_permissions=True)
    att.submit()

    _mark_logs_processed(day_logs, att.name)


def _mark_logs_processed(logs, attendance_name):
    for log in logs:
        frappe.db.set_value(
            "Biometric Attendance Log",
            log["name"],
            {"processed": 1, "attendance_record": attendance_name}
        )