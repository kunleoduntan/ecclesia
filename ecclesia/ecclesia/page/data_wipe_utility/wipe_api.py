import frappe
from frappe import _
import json


# ──────────────────────────────────────────────
# PROTECTED DOCTYPES – never wiped
# ──────────────────────────────────────────────
PROTECTED_DOCTYPES = {
    "Document Audit Log",
    "Activity Log",
    "Error Log",
    "Access Log",
    "Route History",
    "User",
    "Role",
    "DocType",
    "Module Def",
    "Company",
    "Currency",
    "System Settings",
    "Global Defaults",
    "Patch Log",
    "Installed Application",
    "Installed Applications",
    "DefaultValue",
    "Singles",
    "File",  # handled separately
    "Version",
    "Communication",
}


# ──────────────────────────────────────────────
# 1. Get all submittable doctypes for a company
# ──────────────────────────────────────────────
@frappe.whitelist()
def get_submittable_doctypes(company=None):
    """Return list of submittable doctypes that have data for the given company."""
    frappe.only_for("System Manager")

    # All doctypes marked is_submittable
    all_submittable = frappe.get_all(
        "DocType",
        filters={"is_submittable": 1, "issingle": 0, "istable": 0},
        pluck="name",
    )

    result = []
    for dt in all_submittable:
        if dt in PROTECTED_DOCTYPES:
            continue

        try:
            meta = frappe.get_meta(dt)
            # Check if doctype has company field or can be filtered by company
            has_company = bool(meta.get_field("company"))
            filters = {}
            if company and has_company:
                filters["company"] = company

            count = frappe.db.count(dt, filters=filters)
            if count > 0:
                result.append({
                    "doctype": dt,
                    "label": dt,
                    "count": count,
                    "has_company_field": has_company,
                    "module": meta.module,
                })
        except Exception:
            continue

    result.sort(key=lambda x: (x["module"], x["doctype"]))
    return result


# ──────────────────────────────────────────────
# 2. Preview what will be deleted
# ──────────────────────────────────────────────
@frappe.whitelist()
def preview_wipe(doctypes, company=None):
    """Return record counts per doctype before wipe."""
    frappe.only_for("System Manager")

    if isinstance(doctypes, str):
        doctypes = json.loads(doctypes)

    preview = []
    for dt in doctypes:
        if dt in PROTECTED_DOCTYPES:
            continue
        try:
            meta = frappe.get_meta(dt)
            has_company = bool(meta.get_field("company"))
            filters = {}
            if company and has_company:
                filters["company"] = company

            count = frappe.db.count(dt, filters=filters)
            preview.append({"doctype": dt, "count": count})
        except Exception:
            preview.append({"doctype": dt, "count": 0, "error": True})

    return preview


# ──────────────────────────────────────────────
# 3. Core wipe function
# ──────────────────────────────────────────────
@frappe.whitelist()
def execute_wipe(doctypes, company=None, dry_run=False):
    """
    Wipe all records from the given submittable doctypes.
    - Cancels submitted docs first
    - Deletes child table rows
    - Unlinks attached files (does NOT delete the physical file)
    - Skips Document Audit Log and other protected doctypes
    - Processes in safe batches to avoid memory/lock issues
    """
    frappe.only_for("System Manager")

    if isinstance(doctypes, str):
        doctypes = json.loads(doctypes)

    # Validate no protected doctypes slipped through
    safe_doctypes = [dt for dt in doctypes if dt not in PROTECTED_DOCTYPES]

    results = []
    total_deleted = 0

    for dt in safe_doctypes:
        try:
            deleted, log = _wipe_single_doctype(dt, company, dry_run)
            results.append({
                "doctype": dt,
                "deleted": deleted,
                "status": "dry_run" if dry_run else "success",
                "log": log,
            })
            total_deleted += deleted
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"Data Wipe Error: {dt}")
            results.append({
                "doctype": dt,
                "deleted": 0,
                "status": "error",
                "log": str(e),
            })

    if not dry_run:
        # Write a single audit entry for the wipe operation
        _write_audit_log(safe_doctypes, company, total_deleted)

    return {
        "total_deleted": total_deleted,
        "results": results,
        "dry_run": dry_run,
    }


# ──────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────
def _wipe_single_doctype(doctype, company, dry_run):
    meta = frappe.get_meta(doctype)
    has_company = bool(meta.get_field("company"))

    filters = {}
    if company and has_company:
        filters["company"] = company

    # Fetch names in batches of 100 to avoid memory overload
    BATCH = 100
    deleted = 0
    log_lines = []

    while True:
        names = frappe.get_all(doctype, filters=filters, pluck="name", limit=BATCH)
        if not names:
            break

        if dry_run:
            deleted += len(names)
            break

        for name in names:
            try:
                doc = frappe.get_doc(doctype, name)

                # Step 1 – cancel if submitted
                if doc.docstatus == 1:
                    doc.flags.ignore_permissions = True
                    doc.flags.ignore_links = True
                    doc.cancel()

                # Step 2 – unlink attached files without deleting them
                _unlink_attachments(doctype, name)

                # Step 3 – delete the document
                frappe.delete_doc(
                    doctype,
                    name,
                    force=True,
                    ignore_permissions=True,
                    ignore_on_trash=True,
                    delete_permanently=True,
                )
                deleted += 1
            except Exception as e:
                log_lines.append(f"SKIP {name}: {e}")
                continue

        frappe.db.commit()

    return deleted, "\n".join(log_lines) if log_lines else "OK"


def _unlink_attachments(doctype, docname):
    """
    Unlink File records attached to this document.
    Sets attached_to_doctype and attached_to_name to blank
    so the file record persists but is no longer linked.
    """
    frappe.db.set_value(
        "File",
        {"attached_to_doctype": doctype, "attached_to_name": docname},
        {
            "attached_to_doctype": "",
            "attached_to_name": "",
            "attached_to_field": "",
        },
        update_modified=False,
    )


def _write_audit_log(doctypes, company, total_deleted):
    """Write a record to the system Activity Log for traceability."""
    try:
        frappe.get_doc({
            "doctype": "Activity Log",
            "subject": f"Data Wipe executed by {frappe.session.user}",
            "content": json.dumps({
                "company": company,
                "doctypes_wiped": doctypes,
                "total_records_deleted": total_deleted,
            }, indent=2),
            "reference_doctype": "Company",
            "reference_name": company,
            "operation": "Deleted",
            "user": frappe.session.user,
        }).insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        pass


# ──────────────────────────────────────────────
# 4. Get company list helper
# ──────────────────────────────────────────────
@frappe.whitelist()
def get_companies():
    frappe.only_for("System Manager")
    return frappe.get_all("Company", pluck="name", order_by="name")