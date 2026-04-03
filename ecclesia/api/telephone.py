# ecclesia/ecclesia/api/telephone.py

import frappe
from frappe import _
from frappe.utils import now_datetime, add_days, getdate


@frappe.whitelist()
def sync_missed_calls():
    """
    Scheduler / whitelisted endpoint.
    Marks Telephone Call Logs that are still in 'Initiated' or 'Ringing'
    status — but whose started_at is older than a threshold — as 'Missed'.
    Called from ecclesia/api/__init__.py via:
        from ecclesia.api.telephone import sync_missed_calls as _sync
    """
    timeout_minutes = frappe.db.get_single_value(
        "Telephone Settings", "missed_call_timeout_minutes"
    ) or 2  # default: 2 minutes with no answer = missed

    cutoff = frappe.utils.add_to_date(now_datetime(), minutes=-int(timeout_minutes))

    stale_logs = frappe.db.get_all(
        "Telephone Call Log",
        filters={
            "status": ["in", ["Initiated", "Ringing"]],
            "started_at": ["<", cutoff],
        },
        fields=["name", "started_at", "receiver_number"],
        limit=200,
    )

    updated = []
    for log in stale_logs:
        try:
            doc = frappe.get_doc("Telephone Call Log", log["name"])
            doc.status = "Missed"
            if not doc.ended_at:
                doc.ended_at = now_datetime()
            doc.save(ignore_permissions=True)
            updated.append(log["name"])
        except Exception as e:
            frappe.log_error(
                title=f"sync_missed_calls: failed on {log['name']}",
                message=frappe.get_traceback(),
            )

    if updated:
        frappe.db.commit()

    frappe.logger().info(f"sync_missed_calls: marked {len(updated)} log(s) as Missed")
    return {"marked_missed": len(updated), "logs": updated}


@frappe.whitelist()
def log_call(
    receiver_number,
    direction="Outbound",
    call_type="External",
    provider="WebRTC",
    call_sid=None,
    lead=None,
    contact=None,
    customer=None,
    opportunity=None,
    employee=None,
):
    """Create a new Telephone Call Log and return its name."""
    doc = frappe.get_doc({
        "doctype": "Telephone Call Log",
        "caller_user": frappe.session.user,
        "receiver_number": receiver_number,
        "direction": direction,
        "call_type": call_type,
        "provider": provider,
        "call_sid": call_sid,
        "status": "Initiated",
        "lead": lead,
        "contact": contact,
        "customer": customer,
        "opportunity": opportunity,
        "employee": employee,
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name}


@frappe.whitelist()
def update_call_status(name, status, ended_at=None, answered_at=None):
    """Update the status (and optionally timestamps) of an existing log."""
    from ecclesia.ecclesia.doctype.telephone_call_log.telephone_call_log import TelephoneCallLog  # noqa

    doc = frappe.get_doc("Telephone Call Log", name)
    doc.status = status
    if answered_at:
        doc.answered_at = answered_at
    if ended_at:
        doc.ended_at = ended_at
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name, "status": doc.status}


@frappe.whitelist()
def get_recent_logs(limit=20):
    """Return recent call logs for the current user."""
    from ecclesia.ecclesia.doctype.telephone_call_log.telephone_call_log import TelephoneCallLog  # noqa

    return TelephoneCallLog.get_recent_logs(frappe.session.user, limit=int(limit))