# Copyright (c) 2026, Value Impacts Consulting
# ─────────────────────────────────────────────────────────────────────────────
# FILE LOCATION IN YOUR ECCLESIA APP:
#
#   apps/ecclesia/ecclesia/patches/license_management_patch.py
#
# ADD TO patches.txt:
#
#   ecclesia.patches.license_management_patch.execute
#
# This patch:
#   1. Renames the DocType from "License and Permit" → "License Management"
#      if the old name exists on the site (safe to run if already renamed).
#   2. Installs License Management as a new DocType if neither name exists.
#   3. Updates all Link field values in child tables and other DocTypes
#      that referenced the old name.
# ─────────────────────────────────────────────────────────────────────────────

import frappe
from frappe import _


OLD_NAME = "License and Permit"
NEW_NAME = "License Management"


def execute():
    """
    Entry point called by bench migrate via patches.txt.
    Idempotent — safe to run multiple times.
    """
    if frappe.db.exists("DocType", NEW_NAME):
        # Already correct — nothing to do
        frappe.logger().info(
            f"[license_management_patch] '{NEW_NAME}' already exists. Skipping."
        )
        return

    if frappe.db.exists("DocType", OLD_NAME):
        _rename_doctype()
    else:
        # Neither name exists — first-time install
        frappe.logger().info(
            f"[license_management_patch] Neither name found. "
            f"DocType will be created via bench migrate from the JSON fixture."
        )


def _rename_doctype():
    """
    Rename the DocType and update all downstream references.
    """
    frappe.logger().info(
        f"[license_management_patch] Renaming '{OLD_NAME}' → '{NEW_NAME}'"
    )

    # ── 1. Rename the DocType record itself ───────────────────────────────────
    frappe.rename_doc("DocType", OLD_NAME, NEW_NAME,
                      force=True, ignore_permissions=True)

    # ── 2. Rename the underlying table ────────────────────────────────────────
    old_table = f"tab{OLD_NAME}"
    new_table = f"tab{NEW_NAME}"
    if frappe.db.table_exists(old_table) and not frappe.db.table_exists(new_table):
        frappe.db.sql(f"RENAME TABLE `{old_table}` TO `{new_table}`")
        frappe.logger().info(
            f"[license_management_patch] Table renamed: {old_table} → {new_table}"
        )

    # ── 3. Update Custom Field options that referenced the old DocType name ───
    frappe.db.sql("""
        UPDATE `tabCustom Field`
        SET options = %s
        WHERE options = %s
    """, (NEW_NAME, OLD_NAME))

    # ── 4. Update DocField options in all DocTypes ─────────────────────────────
    frappe.db.sql("""
        UPDATE `tabDocField`
        SET options = %s
        WHERE options = %s
    """, (NEW_NAME, OLD_NAME))

    # ── 5. Update Property Setter ─────────────────────────────────────────────
    frappe.db.sql("""
        UPDATE `tabProperty Setter`
        SET value = %s
        WHERE value = %s
    """, (NEW_NAME, OLD_NAME))

    # ── 6. Update Link values in tables that had FK to old name ──────────────
    # Compliance Risk Item — related_license column
    if frappe.db.table_exists("tabCompliance Risk Item"):
        frappe.db.sql("""
            UPDATE `tabCompliance Risk Item`
            SET related_license = REPLACE(related_license, %s, %s)
            WHERE related_license LIKE %s
        """, (OLD_NAME, NEW_NAME, f"%{OLD_NAME}%"))

    # Compliance Audit Finding — related_license column
    if frappe.db.table_exists("tabCompliance Audit Finding"):
        frappe.db.sql("""
            UPDATE `tabCompliance Audit Finding`
            SET related_license = REPLACE(related_license, %s, %s)
            WHERE related_license LIKE %s
        """, (OLD_NAME, NEW_NAME, f"%{OLD_NAME}%"))

    # Compliance Exception — related_license column
    if frappe.db.table_exists("tabCompliance Exception"):
        frappe.db.sql("""
            UPDATE `tabCompliance Exception`
            SET related_license = REPLACE(related_license, %s, %s)
            WHERE related_license LIKE %s
        """, (OLD_NAME, NEW_NAME, f"%{OLD_NAME}%"))

    # ── 7. Commit and clear cache ─────────────────────────────────────────────
    frappe.db.commit()
    frappe.clear_cache()

    frappe.logger().info(
        f"[license_management_patch] Rename complete: '{OLD_NAME}' → '{NEW_NAME}'"
    )
    print(f"✓ DocType renamed: '{OLD_NAME}' → '{NEW_NAME}'")