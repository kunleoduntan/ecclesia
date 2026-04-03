# Copyright (c) 2026, Ecclesia Enterprise — License: MIT
# ess_portal_attendance.py
"""
ESS Portal — Attendance API
Adapted from ess_portal_attendance (Ecclesia Church attendance module).

Three check-in methods:
  1. QR Code   — unique token per employee (ess_qr_token on Employee)
  2. Geo-fence — Haversine distance validation against ESS Office Location
  3. Face ID   — 128-dim face_recognition encoding (ess_face_encoding on Employee)

All methods write to standard ERPNext `Employee Checkin` doctype.
Method metadata stored in custom fields (ess_checkin_method, ess_latitude, etc.)
installed by ess_portal_custom_fields.py.
"""

import frappe
import secrets
import qrcode
import io
import json
import math

try:
    import numpy as np
    import face_recognition
    FACE_LIB_AVAILABLE = True
except ImportError:
    FACE_LIB_AVAILABLE = False

from frappe.utils.file_manager import save_file
from frappe.utils import now_datetime, today, flt


# ─────────────────────────────────────────────────────────────────
# SECTION 1 — QR CODE
# ─────────────────────────────────────────────────────────────────

def generate_employee_qr(doc, method=None):
    """
    Hook: Employee.after_insert
    Generates a unique QR token and QR image, stored on the Employee record
    via our custom fields ess_qr_token and ess_qr_code_image.
    """
    if doc.get("ess_qr_token"):
        return  # Already generated — skip

    token = secrets.token_hex(16)
    base_url = (
        frappe.db.get_single_value("ESS Settings", "portal_base_url")
        or frappe.utils.get_url()
    )
    qr_data = f"{base_url}/ess/checkin/{token}"

    img = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=8,
        border=3,
    )
    img.add_data(qr_data)
    img.make(fit=True)
    pil_img = img.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    buf.seek(0)

    file_doc = save_file(
        fname=f"{doc.name}_ess_qr.png",
        content=buf.getvalue(),
        dt="Employee",
        dn=doc.name,
        is_private=0,
    )

    # Write back via db_set to avoid re-triggering hooks
    frappe.db.set_value("Employee", doc.name, {
        "ess_qr_token":      token,
        "ess_qr_code_image": file_doc.file_url,
    })

    frappe.logger().info(f"[ESS QR] Generated QR for {doc.name}")


def sync_qr_on_update(doc, method=None):
    """
    Hook: Employee.on_update
    Regenerate QR if token is missing (e.g., employee record predates ESS install).
    """
    if not doc.get("ess_qr_token"):
        generate_employee_qr(doc)


@frappe.whitelist(allow_guest=False)
def qr_checkin(token: str, log_type: str = "IN"):
    """
    POST /api/method/ess_portal.ess_portal_attendance.qr_checkin

    Validates the QR token, enforces the time window, prevents duplicates,
    and creates an Employee Checkin record.

    Args:
        token    : Value scanned from QR code (ess_qr_token)
        log_type : "IN" or "OUT"
    """
    if not token:
        return {"status": "error", "code": "MISSING_TOKEN"}

    employee = frappe.db.get_value(
        "Employee",
        {"ess_qr_token": token, "status": "Active"},
        ["name", "employee_name", "department"],
        as_dict=True,
    )
    if not employee:
        return {"status": "error", "code": "INVALID_TOKEN",
                "message": "QR code not recognised. Please contact HR."}

    window = _checkin_window_check(log_type)
    if not window["allowed"]:
        return {"status": "error", "code": "OUTSIDE_WINDOW", "message": window["message"]}

    if _duplicate_checkin_today(employee.name, log_type):
        return {"status": "exists",
                "message": f"Already clocked {log_type} today.",
                "employee": employee.employee_name}

    _create_checkin(
        employee=employee.name,
        employee_name=employee.employee_name,
        log_type=log_type,
        method="QR Code",
    )

    return {
        "status":   "success",
        "employee": employee.employee_name,
        "department": employee.department,
        "log_type": log_type,
        "time":     str(now_datetime()),
        "message":  f"Welcome, {employee.employee_name}! Clocked {log_type}.",
    }


@frappe.whitelist()
def regenerate_qr(employee: str):
    """Rotate QR token for an employee (HR Manager / System Manager only)."""
    frappe.only_for(["HR Manager", "System Manager"])

    doc = frappe.get_doc("Employee", employee)
    doc.ess_qr_token = None          # clear so generate_employee_qr creates fresh one
    generate_employee_qr(doc)

    return {
        "status":  "success",
        "message": f"QR code regenerated for {employee}.",
    }


# ─────────────────────────────────────────────────────────────────
# SECTION 2 — GEO-FENCE
# ─────────────────────────────────────────────────────────────────

@frappe.whitelist()
def geo_checkin(latitude: float, longitude: float, log_type: str = "IN", branch: str = None):
    """
    POST /api/method/ess_portal.ess_portal_attendance.geo_checkin

    Validates GPS coordinates against ESS Office Location radius.
    Distance is calculated using the Haversine formula.

    Args:
        latitude  : Employee current latitude  (from browser Geolocation API)
        longitude : Employee current longitude
        log_type  : "IN" or "OUT"
        branch    : Optional branch filter for multi-site organisations
    """
    employee_id = _resolve_employee()
    if not employee_id:
        frappe.throw("No Employee record linked to your account.", frappe.AuthenticationError)

    offices = _get_office_locations(branch)
    if not offices:
        frappe.throw("No office geo-fence configured. Ask your HR Administrator to add one.")

    emp_lat  = flt(latitude)
    emp_long = flt(longitude)
    min_dist = float("inf")
    nearest  = None
    in_fence = False

    for office in offices:
        dist = _haversine(emp_lat, emp_long, flt(office.latitude), flt(office.longitude))
        if dist < min_dist:
            min_dist = dist
            nearest  = office
        if dist <= flt(office.get("radius_meters") or 100):
            in_fence = True
            break

    if not in_fence:
        return {
            "status":   "error",
            "code":     "OUTSIDE_FENCE",
            "distance": round(min_dist, 1),
            "radius":   flt(nearest.get("radius_meters") or 100) if nearest else 100,
            "message":  f"You are {round(min_dist)}m from the office. "
                        f"Must be within {int(nearest.get('radius_meters') or 100)}m.",
        }

    window = _checkin_window_check(log_type)
    if not window["allowed"]:
        return {"status": "error", "code": "OUTSIDE_WINDOW", "message": window["message"]}

    if _duplicate_checkin_today(employee_id, log_type):
        return {"status": "exists", "message": f"Already clocked {log_type} today."}

    emp_name = frappe.db.get_value("Employee", employee_id, "employee_name")

    _create_checkin(
        employee=employee_id,
        employee_name=emp_name,
        log_type=log_type,
        method="Geo-fence",
        latitude=emp_lat,
        longitude=emp_long,
        distance=round(min_dist, 1),
    )

    return {
        "status":   "success",
        "employee": emp_name,
        "log_type": log_type,
        "distance": round(min_dist, 1),
        "office":   nearest.get("location_name") if nearest else "",
        "time":     str(now_datetime()),
        "message":  f"Clocked {log_type} via Geo-fence. Distance: {round(min_dist)}m.",
    }


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine formula — returns distance in metres between two GPS points."""
    R = 6_371_000
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lon2 - lon1)
    a = math.sin(dφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(dλ / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _get_office_locations(branch: str = None) -> list:
    """Return list of active ESS Office Location records."""
    filters = {"enabled": 1}
    if branch:
        filters["branch"] = branch

    locations = frappe.get_all(
        "ESS Office Location",
        filters=filters,
        fields=["location_name", "latitude", "longitude", "radius_meters", "branch"],
    )

    if not locations:
        # Fallback: single office from ESS Settings
        try:
            s = frappe.get_cached_doc("ESS Settings")
            if s.get("office_latitude") and s.get("office_longitude"):
                locations = [{
                    "location_name": "Main Office",
                    "latitude":      s.office_latitude,
                    "longitude":     s.office_longitude,
                    "radius_meters": s.get("geo_fence_radius") or 100,
                }]
        except Exception:
            pass

    return locations


# ─────────────────────────────────────────────────────────────────
# SECTION 3 — FACE RECOGNITION
# ─────────────────────────────────────────────────────────────────

@frappe.whitelist()
def register_face(employee: str, image_b64: str):
    """
    POST /api/method/ess_portal.ess_portal_attendance.register_face

    HR registers an employee's face encoding.
    Stores the 128-dim numpy array as JSON in ess_face_encoding custom field.

    Args:
        employee  : Employee docname
        image_b64 : Base64-encoded JPEG/PNG (clear, well-lit, face-forward)
    """
    if not FACE_LIB_AVAILABLE:
        frappe.throw("face_recognition library not installed. "
                     "Run: pip install face_recognition --break-system-packages")

    frappe.only_for(["HR Manager", "HR User", "System Manager"])

    import base64
    raw   = base64.b64decode(image_b64)
    image = face_recognition.load_image_file(io.BytesIO(raw))
    encs  = face_recognition.face_encodings(image)

    if not encs:
        return {"status": "error", "code": "NO_FACE",
                "message": "No face detected. Use a clear, well-lit, front-facing photo."}

    if len(encs) > 1:
        return {"status": "error", "code": "MULTIPLE_FACES",
                "message": "Multiple faces in image. Use a photo with only the employee's face."}

    frappe.db.set_value("Employee", employee, {
        "ess_face_encoding":     json.dumps(encs[0].tolist()),
        "ess_face_registered":   1,
        "ess_face_registered_on": today(),
    })

    frappe.logger().info(f"[ESS Face] Registered face for {employee}")
    return {"status": "success", "message": "Face registered. Employee can now use Face ID check-in."}


@frappe.whitelist()
def face_checkin(image_b64: str, log_type: str = "IN"):
    """
    POST /api/method/ess_portal.ess_portal_attendance.face_checkin

    Matches uploaded webcam image against all registered employee face encodings.
    Uses tolerance 0.50 (adjustable in ESS Settings).

    Args:
        image_b64 : Base64-encoded camera capture
        log_type  : "IN" or "OUT"
    """
    if not FACE_LIB_AVAILABLE:
        return {"status": "error", "code": "UNAVAILABLE",
                "message": "Face recognition not available on this server."}

    import base64

    raw     = base64.b64decode(image_b64)
    unknown = face_recognition.load_image_file(io.BytesIO(raw))
    unkn_encs = face_recognition.face_encodings(unknown)

    if not unkn_encs:
        return {"status": "error", "code": "NO_FACE",
                "message": "No face detected in the image. Try again."}

    unkn_enc = unkn_encs[0]

    # Load all employees with a registered face encoding
    registered = frappe.get_all(
        "Employee",
        filters={"status": "Active", "ess_face_registered": 1},
        fields=["name", "employee_name", "department", "ess_face_encoding"],
    )

    if not registered:
        return {"status": "error", "code": "NO_REGISTRATIONS",
                "message": "No employees have registered Face ID yet."}

    known_encs, emp_list = [], []
    for emp in registered:
        try:
            known_encs.append(np.array(json.loads(emp.ess_face_encoding)))
            emp_list.append(emp)
        except Exception:
            continue

    if not known_encs:
        return {"status": "error", "code": "CORRUPT_ENCODINGS",
                "message": "No valid face encodings found."}

    tolerance = flt(
        frappe.db.get_single_value("ESS Settings", "face_tolerance") or 0.50
    )

    matches   = face_recognition.compare_faces(known_encs, unkn_enc, tolerance=tolerance)
    distances = face_recognition.face_distance(known_encs, unkn_enc)
    best      = int(np.argmin(distances))

    if not matches[best]:
        return {"status": "error", "code": "NO_MATCH",
                "message": "Face not recognised. Use QR or Geo-fence, or contact HR."}

    matched  = emp_list[best]
    conf_pct = round((1 - float(distances[best])) * 100, 1)

    if _duplicate_checkin_today(matched.name, log_type):
        return {"status": "exists", "employee": matched.employee_name,
                "message": f"Already clocked {log_type} today."}

    _create_checkin(
        employee=matched.name,
        employee_name=matched.employee_name,
        log_type=log_type,
        method="Face Recognition",
        face_confidence=conf_pct,
    )

    return {
        "status":     "success",
        "employee":   matched.employee_name,
        "department": matched.department,
        "log_type":   log_type,
        "confidence": conf_pct,
        "time":       str(now_datetime()),
        "message":    f"Welcome, {matched.employee_name}! Face match: {conf_pct}%",
    }


# ─────────────────────────────────────────────────────────────────
# SECTION 4 — ANALYTICS
# ─────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_my_attendance_summary(employee: str = None, month: int = None, year: int = None):
    """Return monthly attendance stats for the ESS dashboard."""
    from datetime import date as _date
    emp = employee or _resolve_employee()
    if not emp:
        frappe.throw("Employee not found.")

    today_d = _date.today()
    m = month or today_d.month
    y = year  or today_d.year

    rows = frappe.db.sql("""
        SELECT attendance_date, status, in_time, out_time,
               working_hours, late_entry, early_exit
        FROM   `tabAttendance`
        WHERE  employee = %(emp)s
          AND  MONTH(attendance_date) = %(m)s
          AND  YEAR(attendance_date)  = %(y)s
        ORDER  BY attendance_date DESC
    """, {"emp": emp, "m": m, "y": y}, as_dict=True)

    return {
        "employee": emp, "month": m, "year": y,
        "total":    len(rows),
        "present":  sum(1 for r in rows if r.status == "Present"),
        "absent":   sum(1 for r in rows if r.status == "Absent"),
        "on_leave": sum(1 for r in rows if r.status == "On Leave"),
        "late":     sum(1 for r in rows if r.late_entry),
        "total_hours": round(sum(flt(r.working_hours) for r in rows), 1),
        "records":  rows,
    }


def send_weekly_attendance_summary():
    """Scheduled weekly job — emails each employee their weekly summary."""
    pass  # implemented per notification template


def log_checkin_activity(doc, method=None):
    """Hook: Employee Checkin.after_insert — ESS audit trail."""
    try:
        frappe.get_doc({
            "doctype":   "ESS Activity Log",
            "employee":  doc.employee,
            "activity":  f"Attendance {doc.log_type} via {doc.get('ess_checkin_method') or 'Unknown'}",
            "timestamp": now_datetime(),
        }).insert(ignore_permissions=True)
    except Exception:
        pass  # non-critical


# ─────────────────────────────────────────────────────────────────
# SHARED HELPERS
# ─────────────────────────────────────────────────────────────────

def _resolve_employee():
    return frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")


def _duplicate_checkin_today(employee: str, log_type: str) -> bool:
    from datetime import datetime, time as _time
    day_start = datetime.combine(datetime.today().date(), _time.min)
    day_end   = datetime.combine(datetime.today().date(), _time.max)
    return bool(frappe.db.exists("Employee Checkin", {
        "employee": employee,
        "log_type": log_type,
        "time":     ["between", [day_start, day_end]],
    }))


def _checkin_window_check(log_type: str) -> dict:
    """Returns {'allowed': bool, 'message': str}. HR Managers bypass window."""
    from datetime import datetime

    privileged = {"HR Manager", "System Manager"}
    if set(frappe.get_roles(frappe.session.user)) & privileged:
        return {"allowed": True, "message": ""}

    try:
        s = frappe.get_cached_doc("ESS Settings")
        now = datetime.now().time()

        if log_type == "IN":
            import datetime as dt
            start = dt.time(int(s.get("checkin_start_hour") or 6),  int(s.get("checkin_start_minute") or 0))
            end   = dt.time(int(s.get("checkin_end_hour") or 11),   int(s.get("checkin_end_minute") or 0))
            label = "Clock-In"
        else:
            import datetime as dt
            start = dt.time(int(s.get("checkout_start_hour") or 15), 0)
            end   = dt.time(23, 59)
            label = "Clock-Out"

        if start <= now <= end:
            return {"allowed": True, "message": ""}

        return {
            "allowed": False,
            "message": (f"{label} window is {start.strftime('%I:%M %p')} – "
                        f"{end.strftime('%I:%M %p')}. Now: {now.strftime('%I:%M %p')}."),
        }
    except Exception:
        return {"allowed": True, "message": ""}  # Fail open if settings missing


def _create_checkin(employee: str, employee_name: str, log_type: str,
                    method: str, latitude: float = None, longitude: float = None,
                    distance: float = None, face_confidence: float = None):
    """Create Employee Checkin record with ESS custom fields."""
    doc = frappe.get_doc({
        "doctype":             "Employee Checkin",
        "employee":            employee,
        "employee_name":       employee_name,
        "log_type":            log_type,
        "time":                now_datetime(),
        "device_id":           f"ESS-{method.replace(' ', '')}",
        "ess_checkin_method":  method,
        "ess_latitude":        latitude,
        "ess_longitude":       longitude,
        "ess_distance_meters": distance,
        "ess_face_confidence": face_confidence,
    })
    doc.flags.ignore_permissions = True
    doc.insert()
    return doc.name