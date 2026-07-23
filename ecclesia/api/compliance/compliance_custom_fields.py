# Copyright (c) 2026, Value Impacts Consulting
# ─────────────────────────────────────────────────────────────────────────────
# FILE LOCATION IN YOUR ECCLESIA APP:
#
#   apps/ecclesia/ecclesia/api/compliance/compliance_custom_fields.py
#
# The JSON it reads must sit at:
#
#   apps/ecclesia/ecclesia/fixtures/compliance_custom_fields.json
#
# HOW IT AUTO-RUNS ON BENCH MIGRATE:
#
#   Add ONE line to apps/ecclesia/ecclesia/hooks.py:
#
#       after_migrate = [
#           "ecclesia.api.compliance.compliance_custom_fields.install"
#       ]
#
#   That is all. Every `bench migrate` will call install(), which is
#   fully idempotent — safe to run as many times as needed.
#
# MANUAL RUN (one-off):
#
#   bench --site <site> execute ecclesia.api.compliance.compliance_custom_fields.install
#
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import unicode_literals

import json
import os

import frappe

# Keys from the JSON that map directly to Custom Field doctype fields
_ALLOWED_KEYS = {
    "fieldtype", "label", "insert_after", "options",
    "default", "read_only", "collapsible", "description",
    "no_copy", "reqd", "hidden", "bold", "in_list_view",
    "in_filter", "search_index", "translatable",
}

# DocTypes that belong to AdminHQ — skip silently if AdminHQ is not installed
_ADMIN_HQ_DOCTYPES = {
    "HSE Inspection",
    "Facility",
    "Security Incident",
    "Service Contract",
}


def install():
    """
    Read compliance_custom_fields.json and create/update all Custom Fields.

    Called automatically by hooks.py → after_migrate.
    Fully idempotent: existing fields are updated in-place; new ones created.
    AdminHQ DocTypes are skipped with a log entry when the app is not installed.
    """
    json_path = _get_json_path()

    try:
        with open(json_path, encoding="utf-8") as fh:
            fields = json.load(fh)
    except FileNotFoundError:
        frappe.log_error(
            f"compliance_custom_fields.json not found at: {json_path}",
            "Custom Field Installer"
        )
        return
    except json.JSONDecodeError as exc:
        frappe.log_error(
            f"compliance_custom_fields.json is not valid JSON: {exc}",
            "Custom Field Installer"
        )
        return

    installed = updated = skipped = errors = 0

    for cf in fields:
        dt        = cf.get("dt")
        fieldname = cf.get("fieldname")

        # Skip comment / metadata-only entries (those with only _group/_note keys)
        if not dt or not fieldname:
            continue

        # ── AdminHQ guard ────────────────────────────────────────────────────
        if dt in _ADMIN_HQ_DOCTYPES:
            if not frappe.db.exists("DocType", dt):
                frappe.logger().info(
                    f"[compliance_custom_fields] Skipping {dt}.{fieldname} "
                    f"— AdminHQ DocType not found (AdminHQ app not installed)"
                )
                skipped += 1
                continue

        # ── General DocType guard ────────────────────────────────────────────
        if not frappe.db.exists("DocType", dt):
            frappe.log_error(
                f"Skipping {dt}.{fieldname} — DocType '{dt}' does not exist on this site",
                "Custom Field Installer"
            )
            skipped += 1
            continue

        # ── Create or update ─────────────────────────────────────────────────
        cf_name = f"{dt}-{fieldname}"   # Frappe's canonical Custom Field name
        try:
            if frappe.db.exists("Custom Field", cf_name):
                doc = frappe.get_doc("Custom Field", cf_name)
                _is_new = False
            else:
                doc = frappe.new_doc("Custom Field")
                doc.dt        = dt
                doc.fieldname = fieldname
                _is_new = True

            # Apply every key from JSON that the Custom Field doctype understands
            for key, val in cf.items():
                if key.startswith("_") or key in ("dt", "fieldname"):
                    continue
                if key in _ALLOWED_KEYS:
                    setattr(doc, key, val)

            doc.save(ignore_permissions=True)
            frappe.db.commit()

            if _is_new:
                installed += 1
            else:
                updated += 1

        except Exception as exc:
            frappe.db.rollback()
            errors += 1
            frappe.log_error(
                f"Failed on {dt}.{fieldname}: {exc}",
                "Custom Field Installer"
            )

    # Clear form cache so changes are visible immediately in the browser
    frappe.clear_cache()

    summary = (
        f"[compliance_custom_fields] Done — "
        f"{installed} installed, {updated} updated, "
        f"{skipped} skipped, {errors} errors"
    )
    frappe.logger().info(summary)
    print(summary)   # visible in bench output during migrate


def _get_json_path():
    """
    Resolve the absolute path to compliance_custom_fields.json.

    Expected layout:
        apps/ecclesia/ecclesia/api/compliance/compliance_custom_fields.py  ← this file
        apps/ecclesia/ecclesia/fixtures/compliance_custom_fields.json       ← the data
    """
    # __file__ → .../ecclesia/api/compliance/compliance_custom_fields.py
    # go up 3 levels → .../ecclesia/  then down into fixtures/
    api_compliance_dir = os.path.dirname(os.path.abspath(__file__))   # api/compliance/
    api_dir            = os.path.dirname(api_compliance_dir)           # api/
    app_module_dir     = os.path.dirname(api_dir)                      # ecclesia/  (the python package)
    fixtures_dir       = os.path.join(app_module_dir, "fixtures")

    return os.path.join(fixtures_dir, "compliance_custom_fields.json")