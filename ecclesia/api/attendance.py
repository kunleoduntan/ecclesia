import frappe


@frappe.whitelist()
def sync_device(device_name, from_date=None):
    """Manually trigger a pull-sync for one device."""
    from ecclesia.biometric_attendance.sync import pull_device_logs
    device = frappe.get_doc("Biometric Device", device_name)
    return pull_device_logs(device, from_date)


@frappe.whitelist()
def process_logs(from_date=None, to_date=None):
    """Process all unprocessed Biometric Attendance Logs into Attendance records."""
    from ecclesia.biometric_attendance.processor import process_pending_logs
    return process_pending_logs(from_date, to_date)


@frappe.whitelist()
def ping_device(device_name):
    """Test connectivity to a Biometric Device."""
    device = frappe.get_doc("Biometric Device", device_name)
    online = device.ping()
    return {"online": online, "status": "Online" if online else "Offline"}


@frappe.whitelist()
def get_device_users(device_name):
    """Fetch the list of enrolled users from a device."""
    device = frappe.get_doc("Biometric Device", device_name)
    return device.get_users()


@frappe.whitelist(allow_guest=True)
def receive_push(device_serial, biometric_user_id, log_type, punch_time):
    """
    Real-time push endpoint — device calls this on every punch.
    URL: /api/method/ecclesia.api.attendance.receive_push
    """
    from ecclesia.biometric_attendance.doctype.device_employee_mapping.device_employee_mapping import DeviceEmployeeMapping

    device_name = frappe.db.get_value(
        "Biometric Device",
        {"device_serial": device_serial, "enabled": 1}, "name"
    )
    if not device_name:
        frappe.throw("Device not registered or disabled.", frappe.AuthenticationError)

    employee = DeviceEmployeeMapping.resolve(device_name, str(biometric_user_id))

    log = frappe.get_doc({
        "doctype": "Biometric Attendance Log",
        "device": device_name,
        "biometric_user_id": str(biometric_user_id),
        "employee": employee,
        "log_type": log_type.upper(),
        "punch_time": punch_time
    })
    log.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "ok", "log": log.name}