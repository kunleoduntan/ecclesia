"""
Audit Trail — hooks into document events for all DocTypes.
Logs submission, cancellation, and amendment events.
"""

import frappe


def on_submit_handler(doc, method=None):
    """Log document submission for registered DocTypes."""
    if _is_registered(doc.doctype):
        _log_event(doc, "Submitted")


def on_cancel_handler(doc, method=None):
    """Log document cancellation — high risk event."""
    if _is_registered(doc.doctype):
        _log_event(doc, "Cancelled")
        # Cancellations are always flagged
        _raise_cancel_flag(doc)


def on_amend_handler(doc, method=None):
    """Log post-submission amendments — moderate risk."""
    if _is_registered(doc.doctype):
        _log_event(doc, "Amended After Submit")


def _is_registered(doctype_name):
    return frappe.cache().hget("audit_registry", doctype_name) or \
           frappe.db.exists("Auditable DocType Registry", {"doctype_name": doctype_name, "is_active": 1})


def _log_event(doc, event_type):
    try:
        frappe.get_doc({
            "doctype":           "Comment",
            "comment_type":      "Info",
            "reference_doctype": doc.doctype,
            "reference_name":    doc.name,
            "content": f"[Audit Trail] {event_type} by {frappe.session.user} at {frappe.utils.now()}"
        }).insert(ignore_permissions=True)
    except Exception:
        pass


def _raise_cancel_flag(doc):
    """Auto-raise a finding for document cancellations."""
    transaction_code = frappe.db.get_value(
        "Auditable DocType Registry",
        {"doctype_name": doc.doctype},
        "transaction_code"
    ) or "AUTO"

    try:
        if not frappe.db.exists("Audit Finding", {
            "reference_doctype": doc.doctype,
            "reference_name": doc.name,
            "finding_type": "Document Cancellation"
        }):
            frappe.get_doc({
                "doctype":           "Audit Finding",
                "finding_title":     f"Document Cancelled: {doc.doctype} {doc.name}",
                "finding_type":      "Document Cancellation",
                "risk_rating":       "Medium",
                "reference_doctype": doc.doctype,
                "reference_name":    doc.name,
                "transaction_code":  transaction_code,
                "source":            "Continuous Monitoring",
                "status":            "Open",
                "observation": f"{doc.doctype} {doc.name} was cancelled by {frappe.session.user}. "
                               f"Verify this cancellation was authorized and determine if "
                               f"a corrected document was subsequently posted."
            }).insert(ignore_permissions=True)
    except Exception:
        pass
