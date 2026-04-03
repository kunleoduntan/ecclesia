"""
ecclesia/api/webhook.py
Meta WhatsApp Cloud API webhook handler.
Handles: GET verify, POST inbound messages, status updates.
"""

import json
import frappe
from frappe import _
from ecclesia.api.conversation import get_or_create_conversation, save_inbound_message
from ecclesia.api.approval import process_approval_reply
from ecclesia.utils.helpers import get_settings


# ─────────────────────────────────────────────────────────────────────────────
# WEBHOOK VERIFY (GET)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def verify():
    """Meta calls GET /api/whatsapp/webhook to verify the endpoint."""
    settings = get_settings()
    mode      = frappe.request.args.get("hub.mode")
    token     = frappe.request.args.get("hub.verify_token")
    challenge = frappe.request.args.get("hub.challenge")

    if mode == "subscribe" and token == settings.get_password("wa_webhook_verify_token"):
        frappe.local.response.http_status_code = 200
        frappe.local.response.type = "text"
        frappe.local.response.message = challenge
    else:
        frappe.local.response.http_status_code = 403


# ─────────────────────────────────────────────────────────────────────────────
# WEBHOOK RECEIVE (POST)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def receive():
    """
    Meta POSTs all events here.
    We handle: messages, statuses, reactions.
    Always returns 200 immediately (async processing).
    """
    try:
        data = frappe.request.json or {}
        frappe.enqueue(
            "ecclesia.api.webhook._process_webhook",
            queue="short",
            data=data,
            is_async=True
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "WA Webhook Parse Error")

    # Always 200 to Meta
    frappe.local.response.http_status_code = 200
    return "OK"


def _process_webhook(data: dict):
    """Background job: process one webhook payload."""
    try:
        entry = (data.get("entry") or [{}])[0]
        changes = (entry.get("changes") or [{}])[0]
        value = changes.get("value") or {}

        # ── Inbound messages ──────────────────────────────────────────────
        for message in value.get("messages") or []:
            _handle_inbound_message(message, value)

        # ── Status updates ────────────────────────────────────────────────
        for status in value.get("statuses") or []:
            _handle_status_update(status)

    except Exception:
        frappe.log_error(frappe.get_traceback(), "WA Webhook Process Error")


def _handle_inbound_message(message: dict, value: dict):
    msg_type  = message.get("type", "text")
    from_num  = message.get("from", "")
    wa_msg_id = message.get("id", "")
    timestamp = message.get("timestamp")

    # Resolve contact display name from contacts block
    contacts = value.get("contacts") or []
    contact_name = from_num
    if contacts:
        profile = contacts[0].get("profile") or {}
        contact_name = profile.get("name") or from_num

    # Get/create conversation
    conv = get_or_create_conversation(from_num, contact_name)

    # Build message record
    msg_data = {
        "conversation":  conv.name,
        "direction":     "Inbound",
        "message_type":  msg_type,
        "wa_message_id": wa_msg_id,
        "sender_phone":  from_num,
        "timestamp":     _unix_to_frappe(timestamp)
    }

    # Extract content per type
    if msg_type == "text":
        msg_data["body"] = (message.get("text") or {}).get("body", "")

    elif msg_type in ("image", "video", "audio", "document", "sticker"):
        media = message.get(msg_type) or {}
        msg_data.update({
            "media_id":       media.get("id"),
            "media_mime_type":media.get("mime_type"),
            "media_sha256":   media.get("sha256"),
            "media_filename": media.get("filename"),
            "caption":        media.get("caption")
        })

    elif msg_type == "location":
        loc = message.get("location") or {}
        msg_data.update({
            "location_latitude":  loc.get("latitude"),
            "location_longitude": loc.get("longitude"),
            "location_name":      loc.get("name"),
            "location_address":   loc.get("address")
        })

    elif msg_type == "reaction":
        reaction = message.get("reaction") or {}
        msg_data.update({
            "body":                  reaction.get("emoji"),
            "replied_wa_message_id": reaction.get("message_id")
        })

    elif msg_type == "interactive":
        interactive = message.get("interactive") or {}
        itype = interactive.get("type")
        if itype == "button_reply":
            reply = interactive.get("button_reply") or {}
            msg_data["body"] = reply.get("title", "")
            msg_data["_interactive_id"] = reply.get("id", "")
        elif itype == "list_reply":
            reply = interactive.get("list_reply") or {}
            msg_data["body"] = reply.get("title", "")
            msg_data["_interactive_id"] = reply.get("id", "")

    # Reply context
    context = message.get("context") or {}
    if context.get("id"):
        msg_data["replied_wa_message_id"] = context["id"]
        # Lookup local message
        local = frappe.db.get_value("WA Message", {"wa_message_id": context["id"]}, "name")
        if local:
            msg_data["reply_to_message"] = local

    # Save message
    wa_msg = save_inbound_message(msg_data)

    # Mark read
    from ecclesia.api.whatsapp import mark_as_read
    frappe.enqueue(mark_as_read, queue="short", message_id=wa_msg_id)

    # Two-way approval check
    if msg_type in ("text", "interactive"):
        _check_approval_reply(from_num, msg_data.get("body", ""),
                              msg_data.get("_interactive_id", ""), wa_msg.name)

    # Trigger notification rules for inbound
    _fire_inbound_notification(wa_msg, conv)


def _handle_status_update(status: dict):
    wa_msg_id = status.get("id")
    new_status = status.get("status")  # sent / delivered / read / failed

    if not wa_msg_id or not new_status:
        return

    msg_name = frappe.db.get_value("WA Message", {"wa_message_id": wa_msg_id}, "name")
    if not msg_name:
        return

    status_map = {
        "sent":      "sent",
        "delivered": "delivered",
        "read":      "read",
        "failed":    "failed"
    }
    frappe.db.set_value("WA Message", msg_name, "delivery_status",
                        status_map.get(new_status, new_status))

    if new_status == "failed":
        errors = status.get("errors") or [{}]
        err = errors[0]
        frappe.db.set_value("WA Message", msg_name, {
            "error_code":    err.get("code"),
            "error_message": err.get("title")
        })

    # Realtime update to desk users watching this conversation
    conv_name = frappe.db.get_value("WA Message", msg_name, "conversation")
    if conv_name:
        frappe.publish_realtime("wa_message_status", {
            "msg_name":   msg_name,
            "status":     new_status,
            "conv_name":  conv_name
        })


def _check_approval_reply(phone: str, body: str, interactive_id: str, wa_msg_name: str):
    """Check if this reply is an answer to a pending action."""
    pending = frappe.db.get_value(
        "WA Pending Action",
        {"phone_number": phone, "status": "Pending"},
        ["name", "option_1_key", "option_2_key", "option_3_key",
         "option_1_action", "option_2_action", "option_3_action"],
        as_dict=True
    )
    if not pending:
        return

    reply = (interactive_id or body or "").strip().upper()
    action = None

    if reply in (pending.option_1_key.upper(), pending.option_1_label.upper() if hasattr(pending, "option_1_label") else ""):
        action = pending.option_1_action
    elif reply in (pending.option_2_key.upper(),):
        action = pending.option_2_action
    elif reply in (pending.option_3_key.upper(),):
        action = pending.option_3_action

    if action:
        process_approval_reply(pending.name, action, phone, wa_msg_name)


def _fire_inbound_notification(wa_msg, conv):
    """Publish realtime event so desk agents see the new message."""
    frappe.publish_realtime(
        "wa_new_inbound_message",
        {
            "conv_name":    conv.name,
            "msg_name":     wa_msg.name,
            "phone":        conv.phone_number,
            "contact_name": conv.contact_display_name,
            "body":         wa_msg.body,
            "message_type": wa_msg.message_type,
            "timestamp":    str(wa_msg.timestamp)
        },
        after_commit=True
    )


def _unix_to_frappe(ts):
    if not ts:
        return frappe.utils.now()
    import datetime
    return datetime.datetime.utcfromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")
