import frappe
from frappe.utils import now


def auto_sync_all_devices():
    """Scheduled every 30 min — pull logs from all enabled Pull-mode devices.
    Push-mode devices (e.g. TAMS Chrome set to real-time push) are skipped
    here entirely — their attendance arrives via the push receiver instead."""
    devices = frappe.get_all(
        "Biometric Device",
        filters={"enabled": 1, "sync_mode": "Pull (Scheduled)"},
        fields=["name"]
    )
    for d in devices:
        try:
            pull_device_logs(frappe.get_doc("Biometric Device", d.name))
        except Exception as e:
            frappe.log_error(str(e), f"Ecclesia Sync Failed: {d.name}")


def pull_device_logs(device_doc, from_date=None):
    """Pull raw logs from device, deduplicate, insert Biometric Attendance Logs."""
    from ecclesia.ecclesia.doctype.biometric_sync_log.biometric_sync_log import BiometricSyncLog

    log_name = BiometricSyncLog.start(device_doc.name, mode="Manual")
    fetched = created = skipped = failed = 0
    errors = []

    try:
        if not from_date and device_doc.last_sync:
            from frappe.utils import getdate
            from_date = getdate(device_doc.last_sync)

        connector = device_doc._get_connector()
        raw_logs = connector.get_attendance_logs(from_date)
        fetched = len(raw_logs)

        for log in raw_logs:
            status, error = record_log(
                device_doc,
                biometric_user_id=log["biometric_user_id"],
                punch_time=log["punch_time"],
                log_type=log["log_type"],
            )
            if status == "created":
                created += 1
            elif status == "skipped":
                skipped += 1
            else:
                failed += 1
                if error:
                    errors.append(error)

        device_doc.db_set("last_sync", now())
        frappe.db.commit()

    except Exception as e:
        errors.append(str(e))
        frappe.log_error(str(e), f"Ecclesia Device Pull Failed: {device_doc.name}")

    BiometricSyncLog.finish(
        log_name, fetched=fetched, created=created,
        skipped=skipped, failed=failed,
        errors="\n".join(errors) if errors else None
    )

    return {"device": device_doc.name, "fetched": fetched,
            "created": created, "skipped": skipped, "failed": failed}


def record_log(device_doc, biometric_user_id, punch_time, log_type):
    """
    Shared insert path for a single raw punch, used by both the scheduled/
    manual Pull connector loop and the real-time Push receiver, so both
    paths apply identical employee-resolution and dedup rules.

    Returns (status, error) where status is one of "created" / "skipped" / "failed".
    """
    from ecclesia.ecclesia.doctype.device_employee_mapping.device_employee_mapping import DeviceEmployeeMapping

    try:
        employee = DeviceEmployeeMapping.resolve(device_doc.name, biometric_user_id)
        if not employee:
            return "skipped", None

        if frappe.db.exists("Biometric Attendance Log", {
            "employee": employee,
            "punch_time": punch_time,
            "device": device_doc.name
        }):
            return "skipped", None

        frappe.get_doc({
            "doctype": "Biometric Attendance Log",
            "device": device_doc.name,
            "employee": employee,
            "biometric_user_id": biometric_user_id,
            "log_type": log_type,
            "punch_time": punch_time
        }).insert(ignore_permissions=True)

        return "created", None

    except Exception as e:
        return "failed", str(e)


def mark_absent_employees():
    """Daily task — mark employees with no attendance today as Absent."""
    from frappe.utils import today
    today_date = today()

    for emp in frappe.get_all("Employee", filters={"status": "Active"}, fields=["name"]):
        if frappe.db.exists("Attendance", {
            "employee": emp.name,
            "attendance_date": today_date,
            "docstatus": ["!=", 2]
        }):
            continue
        if not frappe.db.get_value("Employee", emp.name, "default_shift"):
            continue

        att = frappe.get_doc({
            "doctype": "Attendance",
            "employee": emp.name,
            "attendance_date": today_date,
            "status": "Absent"
        })
        att.insert(ignore_permissions=True)
        att.submit()

    frappe.db.commit()