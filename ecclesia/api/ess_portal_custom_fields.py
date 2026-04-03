# Copyright (c) 2026, Ecclesia Enterprise — License: MIT
# ess_portal_custom_fields.py
"""
ESS Portal — Custom Field Definitions

Rule: never edit standard doctype JSON files.
Fields are created directly via frappe.get_doc() so that the `module`
attribute is correctly persisted on each Custom Field record — enabling
fixture export via: {"dt": "Custom Field", "filters": [["module", "=", "Ecclesia"]]}

Fields added here:
  • Employee          — QR token/image, face encoding, face registration status
  • Employee Checkin  — check-in method, GPS coordinates, face confidence
  • Loan Application  — ESS submission flag + employee notes

Run manually:
    bench --site <site> execute ecclesia.api.ess_portal_custom_fields.install_custom_fields

Runs automatically on every `bench migrate` via `after_migrate` hook.
"""

import frappe

MODULE = "Ecclesia"  # matches hooks.py fixture filter: [["module", "=", "Ecclesia"]]

# ─────────────────────────────────────────────────────────────────
# FIELD DEFINITIONS
# insert_after must reference a real fieldname from the standard doctype.
# ─────────────────────────────────────────────────────────────────
CUSTOM_FIELDS = {

    # ── Employee (standard ERPNext) ──────────────────────────────
    "Employee": [
        {
            "fieldname":    "ess_section",
            "label":        "ESS Portal",
            "fieldtype":    "Section Break",
            "insert_after": "bio",
            "collapsible":  1,
        },
        {
            "fieldname":    "ess_qr_token",
            "label":        "QR Token",
            "fieldtype":    "Data",
            "insert_after": "ess_section",
            "read_only":    1,
            "hidden":       1,
            "no_copy":      1,
            "description":  "Auto-generated secure token for QR attendance. Do not share.",
        },
        {
            "fieldname":    "ess_qr_code_image",
            "label":        "ESS QR Code",
            "fieldtype":    "Attach Image",
            "insert_after": "ess_qr_token",
            "read_only":    1,
        },
        {
            "fieldname":    "ess_col",
            "fieldtype":    "Column Break",
            "insert_after": "ess_qr_code_image",
        },
        {
            "fieldname":    "ess_face_encoding",
            "label":        "Face Encoding (JSON)",
            "fieldtype":    "Long Text",
            "insert_after": "ess_col",
            "hidden":       1,
            "no_copy":      1,
            "description":  "128-dim face encoding stored as JSON. Used for Face ID check-in.",
        },
        {
            "fieldname":    "ess_face_registered",
            "label":        "Face ID Registered",
            "fieldtype":    "Check",
            "insert_after": "ess_face_encoding",
            "default":      "0",
            "read_only":    1,
        },
        {
            "fieldname":    "ess_face_registered_on",
            "label":        "Face Registered On",
            "fieldtype":    "Date",
            "insert_after": "ess_face_registered",
            "read_only":    1,
        },
    ],

    # ── Employee Checkin (standard ERPNext) ──────────────────────
    "Employee Checkin": [
        {
            "fieldname":    "ess_checkin_method",
            "label":        "ESS Check-in Method",
            "fieldtype":    "Select",
            "options":      "\nQR Code\nGeo-fence\nFace Recognition\nManual",
            "insert_after": "device_id",
            "in_list_view": 1,
        },
        {
            "fieldname":    "ess_latitude",
            "label":        "Latitude",
            "fieldtype":    "Float",
            "insert_after": "ess_checkin_method",
            "precision":    "6",
        },
        {
            "fieldname":    "ess_longitude",
            "label":        "Longitude",
            "fieldtype":    "Float",
            "insert_after": "ess_latitude",
            "precision":    "6",
        },
        {
            "fieldname":    "ess_distance_meters",
            "label":        "Distance from Office (m)",
            "fieldtype":    "Float",
            "insert_after": "ess_longitude",
            "read_only":    1,
        },
        {
            "fieldname":    "ess_face_confidence",
            "label":        "Face Match Confidence (%)",
            "fieldtype":    "Float",
            "insert_after": "ess_distance_meters",
            "read_only":    1,
        },
    ],

    # ── Loan Application (standard ERPNext) ──────────────────────
    "Loan Application": [
        {
            "fieldname":    "ess_portal_section",
            "label":        "ESS Portal",
            "fieldtype":    "Section Break",
            "insert_after": "amended_from",
            "collapsible":  1,
        },
        {
            "fieldname":    "ess_submitted_via_portal",
            "label":        "Submitted via ESS Portal",
            "fieldtype":    "Check",
            "insert_after": "ess_portal_section",
            "default":      "0",
            "read_only":    1,
        },
        {
            "fieldname":    "ess_portal_submitted_on",
            "label":        "Portal Submission Time",
            "fieldtype":    "Datetime",
            "insert_after": "ess_submitted_via_portal",
            "read_only":    1,
        },
        {
            "fieldname":    "ess_employee_notes",
            "label":        "Employee Notes (ESS)",
            "fieldtype":    "Small Text",
            "insert_after": "ess_portal_submitted_on",
            "description":  "Additional context submitted via ESS Portal.",
        },
    ],
}


# ─────────────────────────────────────────────────────────────────
# INSTALL
# ─────────────────────────────────────────────────────────────────
def install_custom_fields():
    """
    Safe to call multiple times.
    - Skips fields that already exist (by Frappe's "{DocType}-{fieldname}" key).
    - Sets module = MODULE on every field so fixture export works correctly.
    - Full traceback logged on any failure so nothing is silently swallowed.
    """
    installed = 0
    skipped   = 0
    errors    = []

    for doctype, fields in CUSTOM_FIELDS.items():
        for f in fields:
            # Frappe names Custom Fields as "{DocType}-{fieldname}"
            key = f"{doctype}-{f['fieldname']}"

            if frappe.db.exists("Custom Field", key):
                skipped += 1
                continue

            try:
                cf = frappe.get_doc({
                    "doctype":      "Custom Field",
                    "dt":           doctype,
                    "module":       MODULE,          # ← persisted on the record
                    "fieldname":    f["fieldname"],
                    "fieldtype":    f["fieldtype"],
                    "label":        f.get("label", ""),
                    "options":      f.get("options", ""),
                    "default":      f.get("default", ""),
                    "description":  f.get("description", ""),
                    "insert_after": f.get("insert_after", ""),
                    "read_only":    f.get("read_only", 0),
                    "hidden":       f.get("hidden", 0),
                    "no_copy":      f.get("no_copy", 0),
                    "collapsible":  f.get("collapsible", 0),
                    "in_list_view": f.get("in_list_view", 0),
                    "precision":    f.get("precision", ""),
                })
                cf.insert(ignore_permissions=True)
                installed += 1

            except Exception as e:
                errors.append(f"{doctype}.{f['fieldname']}: {e}")
                frappe.log_error(
                    message=frappe.get_traceback(),
                    title=f"ESS CF Failed: {doctype}.{f['fieldname']}"
                )

    frappe.db.commit()

    frappe.logger().info(
        f"[ESS Portal] Custom fields — installed: {installed}, skipped: {skipped}, errors: {len(errors)}"
    )

    if errors:
        frappe.logger().error(f"[ESS Portal] Field errors: {errors}")

    return {
        "status":    "ok",
        "installed": installed,
        "skipped":   skipped,
        "errors":    errors,
    }


# ─────────────────────────────────────────────────────────────────
# UNINSTALL
# ─────────────────────────────────────────────────────────────────
def uninstall_custom_fields():
    """Remove all ESS Portal custom fields on app uninstall."""
    for doctype, fields in CUSTOM_FIELDS.items():
        for f in fields:
            name = f"{doctype}-{f['fieldname']}"
            if frappe.db.exists("Custom Field", name):
                frappe.delete_doc("Custom Field", name, ignore_missing=True)
    frappe.db.commit()
    frappe.logger().info("[ESS Portal] Custom fields removed.")


# ─────────────────────────────────────────────────────────────────
# MIGRATE HOOK
# ─────────────────────────────────────────────────────────────────
def after_migrate():
    """Called automatically by Frappe after every `bench migrate`."""
    install_custom_fields()