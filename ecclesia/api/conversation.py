"""
ecclesia/api/conversation.py
Manages WA Conversation and WA Message documents.
Called by webhook and by desk agents sending outbound messages.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime
from ecclesia.utils.helpers import normalize_phone


# ─────────────────────────────────────────────────────────────────────────────
# CONVERSATION
# ─────────────────────────────────────────────────────────────────────────────

def get_or_create_conversation(phone: str, display_name: str = None,
                                linked_doctype: str = None, linked_docname: str = None):
    """Return existing open conversation or create a new one for this phone number."""
    phone = normalize_phone(phone)

    existing = frappe.db.get_value(
        "WA Conversation",
        {"phone_number": phone},
        "name"
    )
    if existing:
        return frappe.get_doc("WA Conversation", existing)

    conv = frappe.get_doc({
        "doctype":              "WA Conversation",
        "phone_number":         phone,
        "contact_display_name": display_name or phone,
        "status":               "Open",
        "channel_type":         "WhatsApp",
        "linked_doctype":       linked_doctype,
        "linked_docname":       linked_docname,
        "first_message_at":     now_datetime()
    })
    conv.insert(ignore_permissions=True)
    frappe.db.commit()
    return conv


@frappe.whitelist()
def get_conversation(conv_name: str) -> dict:
    """Fetch conversation with messages for desk inbox."""
    conv = frappe.get_doc("WA Conversation", conv_name)
    messages = frappe.get_all(
        "WA Message",
        filters={"conversation": conv_name},
        fields=["*"],
        order_by="timestamp asc",
        limit=50
    )
    return {"conversation": conv.as_dict(), "messages": messages}


@frappe.whitelist()
def get_conversations(status: str = "Open", limit: int = 30, offset: int = 0) -> list:
    """Get conversation list for the inbox."""
    convs = frappe.get_all(
        "WA Conversation",
        filters={"status": status} if status != "All" else {},
        fields=["name", "phone_number", "contact_display_name", "status",
                "assigned_to", "last_message_at", "last_message_preview",
                "unread_count", "channel_type", "linked_doctype", "linked_docname"],
        order_by="last_message_at desc",
        limit=limit,
        start=offset
    )
    return convs


@frappe.whitelist()
def assign_conversation(conv_name: str, user: str):
    frappe.db.set_value("WA Conversation", conv_name, "assigned_to", user)
    _add_system_message(conv_name, f"Assigned to {frappe.get_value('User', user, 'full_name') or user}")


@frappe.whitelist()
def resolve_conversation(conv_name: str):
    frappe.db.set_value("WA Conversation", conv_name, {
        "status":      "Resolved",
        "resolved_at": now_datetime(),
        "resolved_by": frappe.session.user
    })
    _add_system_message(conv_name, "Conversation resolved")


@frappe.whitelist()
def reopen_conversation(conv_name: str):
    frappe.db.set_value("WA Conversation", conv_name, "status", "Open")
    _add_system_message(conv_name, "Conversation reopened")


# ─────────────────────────────────────────────────────────────────────────────
# MESSAGES
# ─────────────────────────────────────────────────────────────────────────────

def save_inbound_message(data: dict):
    """Persist an inbound WA Message and update conversation counters."""
    msg = frappe.get_doc({"doctype": "WA Message", **data})
    msg.insert(ignore_permissions=True)

    # Update conversation
    frappe.db.set_value("WA Conversation", data["conversation"], {
        "last_message_at":      data.get("timestamp") or now_datetime(),
        "last_message_preview": _preview(data),
        "unread_count":         _increment_unread(data["conversation"])
    })
    frappe.db.commit()
    return msg


@frappe.whitelist()
def send_outbound_message(conv_name: str, message_type: str = "text",
                           body: str = None, template_name: str = None,
                           template_params: str = None, media_url: str = None,
                           caption: str = None, reply_to_message: str = None) -> dict:
    """
    Send a message from the desk inbox.
    Creates WA Message doc, then dispatches via whatsapp.py.
    """
    conv = frappe.get_doc("WA Conversation", conv_name)

    msg = frappe.get_doc({
        "doctype":           "WA Message",
        "conversation":      conv_name,
        "direction":         "Outbound",
        "message_type":      message_type,
        "body":              body,
        "caption":           caption,
        "media_url":         media_url,
        "reply_to_message":  reply_to_message,
        "sender_user":       frappe.session.user,
        "timestamp":         now_datetime(),
        "delivery_status":   "queued"
    })
    msg.insert(ignore_permissions=True)
    frappe.db.commit()

    # Dispatch
    from ecclesia.api import whatsapp as wa
    phone = conv.phone_number
    result = {}

    if message_type == "text" and body:
        result = wa.send_text(phone, body, conv_name)
    elif message_type == "template" and template_name:
        params = frappe.parse_json(template_params or "[]")
        result = wa.send_template(phone, template_name, "en_US", params, conv_name)
    elif message_type == "image" and media_url:
        result = wa.send_image(phone, media_url, caption, conv_name)
    elif message_type == "document" and media_url:
        result = wa.send_document(phone, media_url, caption or "file", None, conv_name)
    elif message_type == "audio" and media_url:
        result = wa.send_audio(phone, media_url, conv_name)
    elif message_type == "video" and media_url:
        result = wa.send_video(phone, media_url, caption, conv_name)

    # Update delivery status
    if result.get("status") == "sent":
        frappe.db.set_value("WA Message", msg.name, {
            "delivery_status": "sent",
            "wa_message_id":   result.get("wa_message_id")
        })
    elif result.get("status") == "failed":
        frappe.db.set_value("WA Message", msg.name, {
            "delivery_status": "failed",
            "error_code":       str(result.get("error_code", "")),
            "error_message":    result.get("error_message", "")
        })

    # Update conv preview
    frappe.db.set_value("WA Conversation", conv_name, {
        "last_message_at":      str(now_datetime()),
        "last_message_preview": f"You: {body or '[media]'}"
    })
    frappe.db.commit()

    return {"msg_name": msg.name, "send_result": result}


@frappe.whitelist()
def add_chat_note(conv_name: str, note: str):
    """Add an internal note to a conversation (not sent to customer)."""
    conv = frappe.get_doc("WA Conversation", conv_name)
    conv.append("chat_notes", {
        "note":     note,
        "added_by": frappe.session.user,
        "added_at": now_datetime()
    })
    conv.save(ignore_permissions=True)


@frappe.whitelist()
def mark_conv_read(conv_name: str):
    frappe.db.set_value("WA Conversation", conv_name, "unread_count", 0)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _preview(data: dict) -> str:
    body = data.get("body") or ""
    mtype = data.get("message_type", "text")
    icons = {"image": "📷 Image", "video": "🎥 Video", "audio": "🎵 Audio",
             "document": "📎 Document", "sticker": "🎭 Sticker",
             "location": "📍 Location"}
    if mtype != "text":
        return icons.get(mtype, f"[{mtype}]")
    return body[:60] + ("…" if len(body) > 60 else "")


def _increment_unread(conv_name: str) -> int:
    current = frappe.db.get_value("WA Conversation", conv_name, "unread_count") or 0
    return current + 1


def _add_system_message(conv_name: str, text: str):
    msg = frappe.get_doc({
        "doctype":       "WA Message",
        "conversation":  conv_name,
        "direction":     "Outbound",
        "message_type":  "system",
        "body":          text,
        "timestamp":     now_datetime(),
        "delivery_status": "sent"
    })
    msg.insert(ignore_permissions=True)
    frappe.db.commit()
