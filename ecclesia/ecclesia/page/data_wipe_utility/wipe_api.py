import json
import frappe
from frappe import _

# Never delete these records through this utility.
PROTECTED_DOCTYPES = {
    "Document Audit Log", "Activity Log", "Error Log", "Access Log",
    "Route History", "User", "Role", "DocType", "Module Def", "Company",
    "Currency", "System Settings", "Global Defaults", "Patch Log",
    "Installed Application", "Installed Applications", "DefaultValue",
    "Singles", "File", "Version", "Communication",
}

BATCH_SIZE = 100
MAX_ROUNDS = 25


def _parse_doctypes(doctypes):
    if isinstance(doctypes, str):
        doctypes = json.loads(doctypes)
    if not isinstance(doctypes, (list, tuple)):
        frappe.throw(_("Invalid DocType list."))
    return list(dict.fromkeys(str(x) for x in doctypes if x))


def _company_field(dt):
    try:
        return frappe.get_meta(dt).get_field("company")
    except Exception:
        return None


def _valid_target(dt):
    if dt in PROTECTED_DOCTYPES:
        return False
    try:
        meta = frappe.get_meta(dt)
        return bool(meta and not meta.issingle and not meta.istable and meta.get_field("company"))
    except Exception:
        return False


@frappe.whitelist()
def get_company_doctypes(company=None):
    """Return every non-single, non-child DocType with a Company field and records for that company."""
    frappe.only_for("System Manager")
    if not company:
        frappe.throw(_("Please select a Company."))

    doctypes = frappe.get_all(
        "DocType",
        filters={"issingle": 0, "istable": 0},
        pluck="name",
    )

    result = []
    for dt in doctypes:
        if not _valid_target(dt):
            continue
        try:
            meta = frappe.get_meta(dt)
            count = frappe.db.count(dt, {"company": company})
            if count:
                result.append({
                    "doctype": dt,
                    "count": count,
                    "module": meta.module or "Other",
                })
        except Exception:
            continue

    result.sort(key=lambda x: (x["module"], x["doctype"]))
    return result


@frappe.whitelist()
def preview_wipe(doctypes, company=None):
    frappe.only_for("System Manager")
    doctypes = _parse_doctypes(doctypes)
    if not company:
        frappe.throw(_("Please select a Company."))

    out = []
    for dt in doctypes:
        if dt in PROTECTED_DOCTYPES:
            out.append({"doctype": dt, "count": 0, "status": "protected"})
            continue
        if not _valid_target(dt):
            out.append({"doctype": dt, "count": 0, "status": "skipped"})
            continue
        try:
            count = frappe.db.count(dt, {"company": company})
            out.append({"doctype": dt, "count": count, "status": "ready"})
        except Exception as e:
            out.append({"doctype": dt, "count": 0, "status": "error", "error": str(e)})
    return out


@frappe.whitelist()
def execute_wipe(doctypes, company=None, dry_run=False):
    """
    Company-scoped destructive wipe.

    Important design:
    - Only DocTypes with a real Company field are targeted.
    - Protected system DocTypes are never targeted.
    - Submitted documents are cancelled when possible, then deleted.
    - Link restrictions are retried across multiple passes.
    - Every failed record is reported rather than silently ignored.
    - Final database counts are used to verify success.
    """
    frappe.only_for("System Manager")
    doctypes = _parse_doctypes(doctypes)

    if not company:
        frappe.throw(_("Please select a Company."))

    dry_run = bool(int(dry_run)) if not isinstance(dry_run, bool) else dry_run

    targets = [dt for dt in doctypes if _valid_target(dt)]
    skipped = [dt for dt in doctypes if dt not in targets]

    if dry_run:
        results = []
        total = 0
        for dt in skipped:
            results.append({
                "doctype": dt, "deleted": 0, "remaining": 0,
                "status": "skipped",
                "status_label": "Protected / unsupported",
            })
        for dt in targets:
            try:
                count = frappe.db.count(dt, {"company": company})
                total += count
                results.append({
                    "doctype": dt, "deleted": count, "remaining": count,
                    "status": "dry_run", "status_label": "Would delete",
                })
            except Exception as e:
                results.append({
                    "doctype": dt, "deleted": 0, "remaining": 0,
                    "status": "error", "status_label": "Error",
                    "errors": [str(e)],
                })
        return {
            "dry_run": True,
            "total_targeted": total,
            "total_deleted": total,
            "total_remaining": total,
            "total_failed": 0,
            "results": results,
        }

    deleted_map = {dt: 0 for dt in targets}
    error_map = {dt: [] for dt in targets}
    pending = list(targets)

    # Repeated passes allow a child/linked transaction to disappear before
    # its parent is attempted again.
    for _ in range(MAX_ROUNDS):
        if not pending:
            break

        progress = False
        next_pending = []

        for dt in pending:
            deleted, remaining, errors = _delete_doctype_batch(dt, company)
            deleted_map[dt] += deleted
            error_map[dt].extend(errors)

            if deleted:
                progress = True
            if remaining:
                next_pending.append(dt)

        pending = next_pending
        if not progress:
            break

        frappe.db.commit()

    results = []
    total_deleted = 0
    total_remaining = 0
    total_failed = 0

    for dt in skipped:
        results.append({
            "doctype": dt, "deleted": 0, "remaining": 0,
            "status": "skipped", "status_label": "Protected / unsupported",
        })

    for dt in targets:
        try:
            remaining = frappe.db.count(dt, {"company": company})
        except Exception as e:
            remaining = 0
            error_map[dt].append(str(e))

        deleted = deleted_map[dt]
        errors = error_map[dt]
        total_deleted += deleted
        total_remaining += remaining
        total_failed += len(errors)

        if remaining == 0 and not errors:
            status = "success"
            label = "Verified — empty"
        elif deleted > 0:
            status = "partial"
            label = "Partial"
        else:
            status = "error"
            label = "Failed"

        results.append({
            "doctype": dt,
            "deleted": deleted,
            "remaining": remaining,
            "status": status,
            "status_label": label,
            "errors": errors[-20:],
        })

    _write_audit_log(company, targets, total_deleted, total_remaining, total_failed)
    frappe.db.commit()

    return {
        "dry_run": False,
        "total_targeted": sum(deleted_map.values()) + total_remaining,
        "total_deleted": total_deleted,
        "total_remaining": total_remaining,
        "total_failed": total_failed,
        "results": results,
    }


def _delete_doctype_batch(dt, company):
    filters = {"company": company}
    deleted = 0
    errors = []

    while True:
        names = frappe.get_all(dt, filters=filters, pluck="name", limit=BATCH_SIZE)
        if not names:
            break

        batch_deleted = 0

        for name in names:
            try:
                doc = frappe.get_doc(dt, name)

                # Remove attachment links before deleting the document.
                _unlink_attachments(dt, name)

                if doc.docstatus == 1:
                    doc.flags.ignore_permissions = True
                    doc.flags.ignore_links = True
                    try:
                        doc.cancel()
                    except Exception as cancel_error:
                        # Cancellation is not allowed to prevent a deletion
                        # attempt. Record the reason for diagnostics.
                        errors.append(f"{dt} {name}: cancel: {cancel_error}")

                # Force deletion after cancellation attempt.
                frappe.delete_doc(
                    dt,
                    name,
                    force=True,
                    ignore_permissions=True,
                    ignore_on_trash=True,
                    delete_permanently=True,
                )
                deleted += 1
                batch_deleted += 1

            except Exception as e:
                errors.append(f"{dt} {name}: {e}")

        frappe.db.commit()

        # If none from the current batch can be removed, another pass may
        # succeed after linked records in other DocTypes are removed.
        if batch_deleted == 0:
            break

    remaining = frappe.db.count(dt, filters)
    return deleted, remaining, errors


def _unlink_attachments(doctype, docname):
    try:
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
    except Exception:
        # File records are intentionally retained; failure to unlink one
        # must not hide the primary document deletion failure.
        pass


def _write_audit_log(company, doctypes, deleted, remaining, failed):
    try:
        frappe.get_doc({
            "doctype": "Activity Log",
            "subject": f"Data Wipe executed by {frappe.session.user}",
            "content": json.dumps({
                "company": company,
                "doctypes_wiped": doctypes,
                "total_records_deleted": deleted,
                "total_records_remaining": remaining,
                "total_failures": failed,
            }, indent=2),
            "reference_doctype": "Company",
            "reference_name": company,
            "operation": "Deleted",
            "user": frappe.session.user,
        }).insert(ignore_permissions=True)
    except Exception:
        # Audit logging must never make an otherwise successful wipe fail.
        pass
