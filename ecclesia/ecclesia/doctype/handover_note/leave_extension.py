# ecclesia/handover/leave_extension.py
import frappe
from frappe.utils import date_diff


HANDOVER_REQUIRED_DAYS = 3   # require handover for leaves >= this many days


def validate_handover_exists(doc, method):
    """Block approval if leave duration needs a handover and none is submitted."""
    duration = date_diff(doc.to_date, doc.from_date) + 1
    if duration < HANDOVER_REQUIRED_DAYS:
        return

    if doc.workflow_state not in ("Approved", "Sanctioned"):
        return  # only block at the approval gate

    hn = _get_submitted_handover(doc)
    if not hn:
        frappe.throw(
            f"A submitted Handover Note is required before approving leave of "
            f"{duration} days or more. Please ask {doc.employee_name} to submit one.",
            title="Handover Note Required"
        )

    # Mirror the handover link back onto the leave application
    frappe.db.set_value("Leave Application", doc.name, {
        "custom_handover_note":   hn,
        "custom_handover_status": "Submitted"
    })


def on_leave_submitted(doc, method):
    """Activate delegations and notify acting officers when leave is approved."""
    hn_name = frappe.db.get_value(
        "Leave Application", doc.name, "custom_handover_note"
    )
    if not hn_name:
        return

    hn = frappe.get_doc("Handover Note", hn_name)
    frappe.db.set_value("Handover Note", hn_name, "status", "Active")
    _activate_delegations(hn)
    _notify_acting_officers(hn)


def on_leave_cancelled(doc, method):
    """Revoke delegations and close the handover if leave is cancelled."""
    hn_name = frappe.db.get_value(
        "Leave Application", doc.name, "custom_handover_note"
    )
    if not hn_name:
        return

    _revoke_delegations(frappe.get_doc("Handover Note", hn_name))
    frappe.db.set_value("Handover Note", hn_name, "status", "Closed")


def _get_submitted_handover(leave_doc):
    return frappe.db.get_value(
        "Handover Note",
        {
            "employee":          leave_doc.employee,
            "leave_application": leave_doc.name,
            "docstatus":         1,           # submitted
            "status":            ["in", ("Approved", "Active")]
        },
        "name"
    )