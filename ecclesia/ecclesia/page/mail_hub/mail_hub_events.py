"""
MailVault Document Event Handlers
ecclesia/page/mail_hub/mail_hub_events.py

Triggered by hooks.py doc_events on Communication doctype.
Pushes realtime notification to desk users when a new inbound
email arrives so the frontend refresh bar appears instantly.
"""
import frappe
from email.utils import parseaddr


def on_communication_insert(doc, method=None):
    """
    Fires after a new Communication is inserted.
    If it's an inbound email, push a realtime event to all
    users who have access to that email account.
    """
    if doc.communication_medium != "Email":
        return
    if doc.sent_or_received != "Received":
        return
    if not doc.email_account:
        return

    # Parse sender display name
    sender_name, sender_email = _parse_sender(doc.sender or "")

    payload = {
        "name":          doc.name,
        "subject":       doc.subject or "(No Subject)",
        "sender":        doc.sender or "",
        "sender_name":   sender_name,
        "sender_email":  sender_email,
        "email_account": doc.email_account,
        "communication_date": str(doc.communication_date),
    }

    # Broadcast to all users who can see this email account
    # For now: publish to all active users; filter client-side
    frappe.publish_realtime(
        event="new_email",
        message=payload,
        # room= could be set to a specific email_account room for finer routing
    )

    frappe.logger().info(
        f"[MailVault] Realtime push: new email from {sender_email} "
        f"on account {doc.email_account}"
    )


def on_communication_update(doc, method=None):
    """
    Fires on Communication update.
    Used to keep folder counts in sync when status changes
    (e.g. when Frappe's spam filter marks something as Spam).
    """
    if doc.communication_medium != "Email":
        return

    # Push a lightweight "counts_changed" event — frontend will re-poll
    frappe.publish_realtime(
        event="email_sync_complete",
        message={"new_count": 0, "updated": True},
    )


def _parse_sender(sender_str):
    name, email = parseaddr(sender_str)
    return (name or email.split("@")[0] if email else "Unknown", email)
