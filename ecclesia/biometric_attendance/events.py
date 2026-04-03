import frappe


def validate_attendance(doc, method):
    """
    Fires on Attendance before_insert and before_save.
    Prevents duplicate attendance records created by biometric sync.
    Allows amendments (amended_from is set) to pass through.
    """
    if doc.get("amended_from"):
        return

    existing = frappe.db.exists("Attendance", {
        "employee":        doc.employee,
        "attendance_date": doc.attendance_date,
        "docstatus":       ["!=", 2],          # 2 = cancelled
        "name":            ["!=", doc.name or ""]
    })

    if existing:
        frappe.throw(
            f"Attendance already exists for {doc.employee} "
            f"on {doc.attendance_date}: {existing}",
            frappe.DuplicateEntryError
        )


def get_permission_query(user):
    """
    Restrict Biometric Sync Log list view:
    - System Manager and HR Manager see all records
    - Others see nothing
    """
    if not user:
        user = frappe.session.user
    roles = frappe.get_roles(user)
    allowed = {"System Manager", "HR Manager", "Ecclesia Attendance Manager"}
    if allowed & set(roles):
        return ""
    return "1=0"


def has_permission(doc, ptype, user):
    """Row-level permission for Biometric Sync Log."""
    if not user:
        user = frappe.session.user
    roles = frappe.get_roles(user)
    allowed = {"System Manager", "HR Manager", "Ecclesia Attendance Manager"}
    return bool(allowed & set(roles))