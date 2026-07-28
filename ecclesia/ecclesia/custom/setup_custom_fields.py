# setup_custom_fields.py
# Creates all new Ecclesia custom fields without touching existing ones.
#
# Deploy: apps/ecclesia/ecclesia/ecclesia/custom/setup_custom_fields.py
#
# Called from:
#   1. after_install hook:  hooks.py → after_install = ["ecclesia.ecclesia.custom.setup_custom_fields.install"]
#   2. after_migrate hook:  hooks.py → after_migrate = ["ecclesia.ecclesia.custom.setup_custom_fields.install"]
#   3. bench command:       bench --site <site> execute ecclesia.ecclesia.custom.setup_custom_fields.install
#
# SAFETY: Every field is checked with frappe.db.exists() before insert.
#         Existing fields are NEVER touched — only new fields are created.

import frappe
import logging

log = logging.getLogger(__name__)


# ── Field definitions ─────────────────────────────────────────────────────────
# Each dict maps to a Custom Field DocType record.
# These are ONLY the new fields — existing fields are preserved as-is.

NEW_CUSTOM_FIELDS = [

    # ════════════════════════════════════════════════════════════════════════
    # EMPLOYEE — NHF (National Housing Fund)
    # ════════════════════════════════════════════════════════════════════════
    {
        "dt":           "Employee",
        "fieldname":    "custom_nhf_number",
        "label":        "NHF Member Number",
        "fieldtype":    "Data",
        "insert_after": "custom_pension_start_date",
        "description":  "Federal Mortgage Bank of Nigeria NHF member number. "
                        "Appears on NHF remittance schedule (2.5% of basic salary).",
        "module":       "Ecclesia",
    },
    {
        "dt":           "Employee",
        "fieldname":    "custom_nhf_registration_date",
        "label":        "NHF Registration Date",
        "fieldtype":    "Date",
        "insert_after": "custom_nhf_number",
        "description":  "Date the employee was registered with FMBN for NHF contributions.",
        "module":       "Ecclesia",
    },
    {
        "dt":           "Employee",
        "fieldname":    "custom_nhf_applicable",
        "label":        "NHF Applicable",
        "fieldtype":    "Check",
        "insert_after": "custom_nhf_registration_date",
        "default":      "1",
        "description":  "Tick if this employee is subject to NHF (2.5% of basic salary). "
                        "Non-applicable employees are excluded from the NHF remittance schedule.",
        "module":       "Ecclesia",
    },

    # ════════════════════════════════════════════════════════════════════════
    # EMPLOYEE — NHIS (National Health Insurance Scheme)
    # ════════════════════════════════════════════════════════════════════════
    {
        "dt":           "Employee",
        "fieldname":    "custom_nhis_number",
        "label":        "NHIS Number",
        "fieldtype":    "Data",
        "insert_after": "custom_nhf_applicable",
        "description":  "National Health Insurance Scheme membership number.",
        "module":       "Ecclesia",
    },
    {
        "dt":           "Employee",
        "fieldname":    "custom_nhis_hmo",
        "label":        "HMO Provider",
        "fieldtype":    "Data",
        "insert_after": "custom_nhis_number",
        "description":  "Health Maintenance Organisation assigned to this employee "
                        "(e.g. Hygeia HMO, Reliance HMO, Total Health Trust). "
                        "Groups the NHIS remittance schedule by HMO.",
        "module":       "Ecclesia",
    },
    {
        "dt":           "Employee",
        "fieldname":    "custom_nhis_start_date",
        "label":        "NHIS Start Date",
        "fieldtype":    "Date",
        "insert_after": "custom_nhis_hmo",
        "description":  "Date this employee was enrolled on the NHIS / HMO plan.",
        "module":       "Ecclesia",
    },
    {
        "dt":           "Employee",
        "fieldname":    "custom_nhis_applicable",
        "label":        "NHIS Applicable",
        "fieldtype":    "Check",
        "insert_after": "custom_nhis_start_date",
        "default":      "1",
        "description":  "Tick if this employee is enrolled in NHIS. "
                        "Non-enrolled employees are excluded from the NHIS remittance schedule.",
        "module":       "Ecclesia",
    },

    # ════════════════════════════════════════════════════════════════════════
    # EMPLOYEE — Bank Details (for Zenith ISO 20022 salary payment file)
    # ════════════════════════════════════════════════════════════════════════
    {
        "dt":           "Employee",
        "fieldname":    "ec_bank_ac_no",
        "label":        "Salary Bank Account No (NUBAN)",
        "fieldtype":    "Data",
        "insert_after": "payroll_cost_center",
        "description":  "Employee 10-digit NUBAN account number. "
                        "Populates CREDACC_NUMBER in the Zenith ISO 20022 salary payment file. "
                        "Also used by the Bank Payment Export Engine.",
        "module":       "Ecclesia",
    },
    {
        "dt":           "Employee",
        "fieldname":    "ec_bank_name",
        "label":        "Salary Bank Name",
        "fieldtype":    "Data",
        "insert_after": "ec_bank_ac_no",
        "description":  "Employee bank name (e.g. Zenith Bank, GTBank, Access Bank). "
                        "Auto-resolves BIC/SWIFT code for CREDACC_BIC in the salary payment file.",
        "module":       "Ecclesia",
    },
    {
        "dt":           "Employee",
        "fieldname":    "ec_permanent_address",
        "label":        "Permanent Home Address",
        "fieldtype":    "Small Text",
        "insert_after": "ec_bank_name",
        "description":  "Employee full home address. "
                        "Populates CRED_ADDRESS_COUNTRYSUBDIVISION in the Zenith ISO 20022 file. "
                        "Only the first 70 characters are used in the file.",
        "module":       "Ecclesia",
    },

    # ════════════════════════════════════════════════════════════════════════
    # SALARY SLIP — Statutory contribution computed fields
    # ════════════════════════════════════════════════════════════════════════
    {
        "dt":           "Salary Slip",
        "fieldname":    "custom_nsitf_contribution",
        "label":        "NSITF Contribution",
        "fieldtype":    "Currency",
        "insert_after": "bonus",
        "read_only":    1,
        "description":  "Employer NSITF contribution for this slip "
                        "(1% of gross pay, capped at ₦1,000 per NSITF circular). "
                        "Auto-computed and stored for the NSITF remittance schedule.",
        "module":       "Ecclesia",
    },
    {
        "dt":           "Salary Slip",
        "fieldname":    "custom_nhf_contribution",
        "label":        "NHF Contribution",
        "fieldtype":    "Currency",
        "insert_after": "custom_nsitf_contribution",
        "read_only":    1,
        "description":  "Employee NHF deduction for this slip "
                        "(2.5% of basic salary). "
                        "Auto-computed from the 'NHF' salary component.",
        "module":       "Ecclesia",
    },
]


def install():
    """
    Create all new custom fields. Safe to run multiple times — skips any
    field that already exists. Never modifies existing fields.
    """
    created = []
    skipped = []
    errors   = []

    for spec in NEW_CUSTOM_FIELDS:
        dt       = spec["dt"]
        fieldname = spec["fieldname"]
        # ERPNext stores Custom Fields as "DocType-fieldname"
        cf_name  = f"{dt}-{fieldname}"

        try:
            if frappe.db.exists("Custom Field", cf_name):
                skipped.append(cf_name)
                continue

            cf = frappe.new_doc("Custom Field")
            cf.update(spec)
            cf.name = cf_name
            cf.insert(ignore_permissions=True)
            frappe.db.commit()
            created.append(cf_name)
            log.info(f"[setup_custom_fields] Created: {cf_name}")

        except Exception as e:
            errors.append({"field": cf_name, "error": str(e)})
            log.error(f"[setup_custom_fields] Error creating {cf_name}: {e}")

    # Report
    print(f"\n{'='*55}")
    print(f"Ecclesia Custom Fields Setup")
    print(f"{'='*55}")
    print(f"  Created : {len(created)}")
    print(f"  Skipped : {len(skipped)} (already existed — untouched)")
    print(f"  Errors  : {len(errors)}")

    if created:
        print(f"\n  New fields created:")
        for f in created:
            print(f"    ✅ {f}")

    if skipped:
        print(f"\n  Already existed (skipped):")
        for f in skipped:
            print(f"    ⏭  {f}")

    if errors:
        print(f"\n  Errors:")
        for e in errors:
            print(f"    ❌ {e['field']}: {e['error']}")

    print(f"{'='*55}\n")

    # Reload metadata so new fields are immediately visible
    if created:
        frappe.clear_cache()

    return {
        "created": created,
        "skipped": skipped,
        "errors":  errors,
    }