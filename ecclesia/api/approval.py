"""
ecclesia/api/approval.py
Two-way approval flows.
Creates WA Pending Action records and processes replies.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime, add_to_date
from ecclesia.api.whatsapp import send_interactive_buttons, send_text
from ecclesia.utils.helpers import resolve_phone


# ─────────────────────────────────────────────────────────────────────────────
# SEND APPROVAL REQUEST
# ─────────────────────────────────────────────────────────────────────────────

def request_approval(linked_doctype: str, linked_docname: str, phone: str,
                     action_type: str, message_body: str,
                     option_1_label: str = "Approve", option_1_action: str = "Approve",
                     option_2_label: str = "Reject",  option_2_action: str = "Reject",
                     option_3_label: str = "Details",  option_3_action: str = "View Details",
                     expires_hours: int = 24) -> str:
    """
    Send an interactive approval message and create a WA Pending Action record.
    Returns the pending action name.
    """
    phone = resolve_phone(phone)

    # Create pending action record
    pending = frappe.get_doc({
        "doctype":          "WA Pending Action",
        "phone_number":     phone,
        "action_type":      action_type,
        "status":           "Pending",
        "linked_doctype":   linked_doctype,
        "linked_docname":   linked_docname,
        "option_1_key":     "1",
        "option_1_label":   option_1_label,
        "option_1_action":  option_1_action,
        "option_2_key":     "2",
        "option_2_label":   option_2_label,
        "option_2_action":  option_2_action,
        "option_3_key":     "3",
        "option_3_label":   option_3_label,
        "option_3_action":  option_3_action,
        "expires_at":       add_to_date(now_datetime(), hours=expires_hours)
    })
    pending.insert(ignore_permissions=True)
    frappe.db.commit()

    # Send interactive WhatsApp message
    result = send_interactive_buttons(
        phone=phone,
        body_text=message_body,
        buttons=[
            {"id": f"opt_1_{pending.name}", "title": option_1_label[:20]},
            {"id": f"opt_2_{pending.name}", "title": option_2_label[:20]},
            {"id": f"opt_3_{pending.name}", "title": option_3_label[:20]}
        ]
    )

    if result.get("wa_message_id"):
        frappe.db.set_value("WA Pending Action", pending.name,
                            "sent_message_id", result["wa_message_id"])

    return pending.name


def request_po_approval(doc, event):
    """Hook handler: request PO approval when PO is submitted."""
    from ecclesia.utils.helpers import get_settings
    settings = get_settings()
    if not settings.wa_enabled:
        return

    # Find approver's phone
    approver_role = frappe.db.get_single_value("Buying Settings", "purchase_approver_role") or "Purchase Manager"
    users = frappe.get_all(
        "Has Role",
        filters={"role": approver_role, "parenttype": "User"},
        fields=["parent"],
        limit=1
    )
    if not users:
        return

    user_doc = frappe.get_doc("User", users[0].parent)
    if not user_doc.mobile_no:
        return

    amount = frappe.format_value(doc.grand_total, {"fieldtype": "Currency"})
    msg = (
        f"🛒 *Purchase Order Approval Required*\n\n"
        f"PO: *{doc.name}*\n"
        f"Supplier: {doc.supplier_name}\n"
        f"Amount: {amount}\n"
        f"Items: {len(doc.items)} line(s)\n\n"
        f"Please review and respond:"
    )
    request_approval(
        linked_doctype="Purchase Order",
        linked_docname=doc.name,
        phone=user_doc.mobile_no,
        action_type="PO Approval",
        message_body=msg,
        option_1_label="✅ Approve",
        option_2_label="❌ Reject",
        option_3_label="📋 Details"
    )


# ─────────────────────────────────────────────────────────────────────────────
# PROCESS REPLY
# ─────────────────────────────────────────────────────────────────────────────

def process_approval_reply(pending_name: str, action: str, phone: str,
                            wa_msg_name: str = None):
    """
    Called by webhook when a user replies to a pending action.
    Executes the action on the linked document.
    """
    pending = frappe.get_doc("WA Pending Action", pending_name)

    if pending.status != "Pending":
        send_text(phone, "⚠️ This action has already been processed.")
        return

    # Mark pending action
    frappe.db.set_value("WA Pending Action", pending_name, {
        "status":       "Approved" if action in ("Approve", "Confirm", "Accept") else "Rejected",
        "responded_at": now_datetime(),
        "response_text": action
    })

    doc = frappe.get_doc(pending.linked_doctype, pending.linked_docname)

    try:
        if action in ("Approve", "Confirm", "Accept"):
            _execute_approve(doc, pending)
            send_text(phone,
                f"✅ *{pending.action_type}*\n"
                f"{pending.linked_doctype} *{pending.linked_docname}* has been approved.\n"
                f"Thank you!"
            )
        elif action in ("Reject", "Decline", "Cancel"):
            _execute_reject(doc, pending)
            send_text(phone,
                f"❌ *{pending.action_type}*\n"
                f"{pending.linked_doctype} *{pending.linked_docname}* has been rejected."
            )
        elif action == "View Details":
            _send_doc_details(phone, doc, pending)

        frappe.db.commit()

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"Approval Action Error: {pending_name}")
        frappe.db.set_value("WA Pending Action", pending_name, {
            "status":       "Error",
            "error_details": str(e)
        })
        send_text(phone, f"⚠️ Error processing action: {str(e)}")


def _execute_approve(doc, pending):
    """Execute approval based on action_type."""
    action = pending.action_type

    if action == "PO Approval":
        doc.flags.ignore_permissions = True
        doc.submit()

    elif action == "Leave Approval":
        doc.flags.ignore_permissions = True
        doc.status = "Approved"
        doc.save()

    elif action == "SO Confirmation":
        doc.flags.ignore_permissions = True
        doc.submit()

    elif action == "Quote Acceptance":
        # Create sales order from quotation
        from erpnext.selling.doctype.quotation.quotation import make_sales_order
        so = make_sales_order(doc.name)
        so.flags.ignore_permissions = True
        so.save()
        so.submit()

    else:
        # Generic: try to submit
        if doc.docstatus == 0:
            doc.flags.ignore_permissions = True
            doc.submit()


def _execute_reject(doc, pending):
    action = pending.action_type

    if action == "Leave Approval":
        doc.status = "Rejected"
        doc.flags.ignore_permissions = True
        doc.save()
    elif action in ("PO Approval", "SO Confirmation"):
        # Add rejection comment
        frappe.get_doc({
            "doctype":    "Comment",
            "comment_type": "Comment",
            "reference_doctype": doc.doctype,
            "reference_name":    doc.name,
            "content":    f"Rejected via WhatsApp by {frappe.session.user}"
        }).insert(ignore_permissions=True)


def _send_doc_details(phone: str, doc, pending):
    """Send a text summary of the linked document."""
    lines = [f"📋 *{doc.doctype}: {doc.name}*\n"]
    detail_fields = {
        "Purchase Order":  ["supplier_name", "transaction_date", "grand_total", "status"],
        "Sales Order":     ["customer_name", "transaction_date", "grand_total", "status"],
        "Leave Application": ["employee_name", "leave_type", "from_date", "to_date", "status"],
        "Sales Invoice":   ["customer_name", "due_date", "grand_total", "outstanding_amount"]
    }
    fields = detail_fields.get(doc.doctype, [])
    for f in fields:
        val = getattr(doc, f, "")
        if val is not None:
            label = f.replace("_", " ").title()
            lines.append(f"*{label}:* {val}")

    lines.append(f"\n_Reply 1 to Approve or 2 to Reject_")
    send_text(phone, "\n".join(lines))


# ─────────────────────────────────────────────────────────────────────────────
# EXPIRY TASK (called from scheduler)
# ─────────────────────────────────────────────────────────────────────────────

def expire_pending_actions():
    expired = frappe.get_all(
        "WA Pending Action",
        filters={"status": "Pending", "expires_at": ("<", now_datetime())},
        fields=["name"]
    )
    for row in expired:
        frappe.db.set_value("WA Pending Action", row.name, "status", "Expired")
    if expired:
        frappe.db.commit()
