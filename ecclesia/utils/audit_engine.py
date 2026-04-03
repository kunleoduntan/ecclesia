import frappe
import json
from frappe.utils import now_datetime

EXCLUDED_DOCTYPES = {
    "Document Audit Log", "System Integrity Log",
    "Error Log", "Activity Log", "Scheduled Job Log"
}

def _get_company_from_doc(doc):
    """Resolve which company this document belongs to."""
    if hasattr(doc, "company") and doc.company:
        return doc.company
    # Walk link fields to find a company reference
    for field in doc.meta.fields:
        if field.fieldtype == "Link" and field.options == "Company":
            val = doc.get(field.fieldname)
            if val:
                return val
    return None

def _audit_enabled(company):
    """Check company flag. Returns True if no company found (fail-safe: log it)."""
    if not company:
        return True  # unknown company — log to be safe
    return frappe.db.get_value("Company", company, "enable_audit_trail") == 1

def _write_log(data: dict):
    """Write directly to DB — bypasses hooks to avoid recursion."""
    doc = frappe.new_doc("Document Audit Log")
    doc.update(data)

    # 🔥 FIX: ensure name exists (bypass 'prompt' autoname)
    if not doc.name:
        doc.name = frappe.generate_hash(length=12)

    doc.flags.ignore_permissions = True
    doc.db_insert()

def _write_integrity_log(event: str, detail: str):
    doc = frappe.new_doc("System Integrity Log")
    doc.update({
        "event": event,
        "detail": detail,
        "performed_by": frappe.session.user,
        "ip_address": getattr(frappe.local, "request_ip", ""),
        "timestamp": now_datetime(),
    })

    # 🔥 FIX: ensure name exists
    if not doc.name:
        doc.name = frappe.generate_hash(length=12)

    doc.flags.ignore_permissions = True
    doc.db_insert()

def _detect_audit_toggle(doc):
    """
    Special handler for Company saves.
    Detects enable_audit_trail flipping before the new value hits the DB.
    """
    before = doc.get_doc_before_save()
    if not before:
        return

    old_val = int(before.get("enable_audit_trail") or 0)
    new_val = int(doc.get("enable_audit_trail") or 0)

    if old_val == new_val:
        return  # no change — nothing to record

    event_type = "AUDIT_DEACTIVATED" if new_val == 0 else "AUDIT_REACTIVATED"

    payload = {
        "document_type": "Company",
        "document_name": doc.name,
        "company": doc.name,
        "action": event_type,
        "changed_fields": json.dumps([{
            "fieldname": "enable_audit_trail",
            "label": "Enable audit trail",
            "old_value": str(old_val),
            "new_value": str(new_val),
        }]),
        "performed_by": frappe.session.user,
        "user_roles": ", ".join(frappe.get_roles(frappe.session.user)),
        "ip_address": getattr(frappe.local, "request_ip", ""),
        "timestamp": now_datetime(),
        "session_id": frappe.session.sid,
    }

    # Write to audit log BEFORE save completes (old value still in DB)
    _write_log(payload)

    # Also write to hardened integrity log
    _write_integrity_log(
        event=event_type,
        detail=(
            f"Company '{doc.name}' audit trail {'deactivated' if new_val == 0 else 'reactivated'} "
            f"by {frappe.session.user} "
            f"(roles: {', '.join(frappe.get_roles(frappe.session.user))})"
        )
    )

    # Notify System Manager role by email
    if new_val == 0:
        _send_deactivation_alert(doc.name)

def _send_deactivation_alert(company):
    sysadmin_emails = frappe.db.sql_list(
        """SELECT DISTINCT u.email FROM `tabUser` u
           JOIN `tabHas Role` r ON r.parent = u.name
           WHERE r.role = 'System Manager' AND u.enabled = 1"""
    )
    if sysadmin_emails:
        frappe.sendmail(
            recipients=sysadmin_emails,
            subject=f"[ALERT] Audit trail deactivated — {company}",
            message=(
                f"The audit trail for company <b>{company}</b> was deactivated by "
                f"<b>{frappe.session.user}</b> at {now_datetime()}.<br><br>"
                f"IP: {getattr(frappe.local, 'request_ip', 'unknown')}<br>"
                f"This action has been permanently recorded in the System Integrity Log."
            ),
            now=True
        )

def log_event(doc, method=None):
    if doc.doctype in EXCLUDED_DOCTYPES:
        return

    # Always intercept Company saves to detect audit toggle
    if doc.doctype == "Company":
        _detect_audit_toggle(doc)

    company = _get_company_from_doc(doc)

    if not _audit_enabled(company):
        return  # logging off for this company — skip (toggle already logged above)

    before = doc.get_doc_before_save()
    changed_fields = []

    if before:
        for field in doc.meta.fields:
            fn = field.fieldname
            old_val = before.get(fn)
            new_val = doc.get(fn)
            if str(old_val or "") != str(new_val or ""):
                changed_fields.append({
                    "fieldname": fn,
                    "label": field.label or fn,
                    "old_value": str(old_val) if old_val is not None else "",
                    "new_value": str(new_val) if new_val is not None else "",
                })

    action_map = {
        "after_insert": "CREATE",
        "on_update":    "UPDATE",
        "on_submit":    "SUBMIT",
        "on_cancel":    "CANCEL",
    }

    _write_log({
        "document_type": doc.doctype,
        "document_name": doc.name,
        "company": company or "",
        "action": action_map.get(method, method or "UNKNOWN"),
        "changed_fields": json.dumps(changed_fields),
        "performed_by": frappe.session.user,
        "user_roles": ", ".join(frappe.get_roles(frappe.session.user)),
        "ip_address": getattr(frappe.local, "request_ip", ""),
        "timestamp": now_datetime(),
        "session_id": frappe.session.sid,
    })

def log_delete(doc, method=None):
    if doc.doctype in EXCLUDED_DOCTYPES:
        return
    company = _get_company_from_doc(doc)
    # Always log deletions even if audit is off — someone deleted while it was off
    _write_log({
        "document_type": doc.doctype,
        "document_name": doc.name,
        "company": company or "",
        "action": "DELETE",
        "changed_fields": "[]",
        "performed_by": frappe.session.user,
        "user_roles": ", ".join(frappe.get_roles(frappe.session.user)),
        "ip_address": getattr(frappe.local, "request_ip", ""),
        "timestamp": now_datetime(),
        "session_id": frappe.session.sid,
    })

def purge_expired_logs():
    from frappe.utils import add_days
    retention = int(frappe.db.get_single_value("Audit Trail Settings", "retention_days") or 730)
    cutoff = add_days(now_datetime(), -retention)
    count = frappe.db.count("Document Audit Log", {"timestamp": ("<", cutoff)})
    frappe.db.delete("Document Audit Log", {"timestamp": ("<", cutoff)})
    frappe.db.commit()
    _write_integrity_log("AUTO_PURGE", f"Purged {count} records older than {cutoff}")