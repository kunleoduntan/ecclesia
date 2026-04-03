"""
ecclesia/api/whatsapp.py
Low-level WhatsApp Cloud API sender.
Handles: text, template, image, video, audio, document, location, reactions.
"""

import json
import frappe
import requests
from frappe import _
from ecclesia.utils.helpers import get_settings, normalize_phone


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC SEND FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def send_text(phone: str, body: str, conversation_name: str = None) -> dict:
    """Send a plain text WhatsApp message."""
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": normalize_phone(phone),
        "type": "text",
        "text": {"preview_url": True, "body": body}
    }
    return _call_api(payload, conversation_name=conversation_name)


def send_template(phone: str, template_name: str, language_code: str,
                  components: list = None, conversation_name: str = None) -> dict:
    """Send a pre-approved HSM template."""
    payload = {
        "messaging_product": "whatsapp",
        "to": normalize_phone(phone),
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code},
            "components": components or []
        }
    }
    return _call_api(payload, conversation_name=conversation_name)


def send_image(phone: str, image_url: str, caption: str = None,
               conversation_name: str = None) -> dict:
    payload = {
        "messaging_product": "whatsapp",
        "to": normalize_phone(phone),
        "type": "image",
        "image": {"link": image_url, "caption": caption or ""}
    }
    return _call_api(payload, conversation_name=conversation_name)


def send_document(phone: str, doc_url: str, filename: str, caption: str = None,
                  conversation_name: str = None) -> dict:
    payload = {
        "messaging_product": "whatsapp",
        "to": normalize_phone(phone),
        "type": "document",
        "document": {"link": doc_url, "filename": filename, "caption": caption or ""}
    }
    return _call_api(payload, conversation_name=conversation_name)


def send_audio(phone: str, audio_url: str, conversation_name: str = None) -> dict:
    payload = {
        "messaging_product": "whatsapp",
        "to": normalize_phone(phone),
        "type": "audio",
        "audio": {"link": audio_url}
    }
    return _call_api(payload, conversation_name=conversation_name)


def send_video(phone: str, video_url: str, caption: str = None,
               conversation_name: str = None) -> dict:
    payload = {
        "messaging_product": "whatsapp",
        "to": normalize_phone(phone),
        "type": "video",
        "video": {"link": video_url, "caption": caption or ""}
    }
    return _call_api(payload, conversation_name=conversation_name)


def send_location(phone: str, latitude: float, longitude: float,
                  name: str = None, address: str = None,
                  conversation_name: str = None) -> dict:
    payload = {
        "messaging_product": "whatsapp",
        "to": normalize_phone(phone),
        "type": "location",
        "location": {
            "latitude": latitude,
            "longitude": longitude,
            "name": name or "",
            "address": address or ""
        }
    }
    return _call_api(payload, conversation_name=conversation_name)


def send_reaction(phone: str, message_id: str, emoji: str,
                  conversation_name: str = None) -> dict:
    payload = {
        "messaging_product": "whatsapp",
        "to": normalize_phone(phone),
        "type": "reaction",
        "reaction": {"message_id": message_id, "emoji": emoji}
    }
    return _call_api(payload, conversation_name=conversation_name)


def mark_as_read(message_id: str) -> dict:
    """Send read receipt to WhatsApp."""
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id
    }
    return _call_api(payload)


def send_interactive_buttons(phone: str, body_text: str, buttons: list,
                              header_text: str = None, footer_text: str = None,
                              conversation_name: str = None) -> dict:
    """
    Send interactive message with up to 3 quick-reply buttons.
    buttons = [{"id": "btn_1", "title": "Approve"}, ...]
    """
    interactive = {
        "type": "button",
        "body": {"text": body_text},
        "action": {
            "buttons": [
                {"type": "reply", "reply": {"id": b["id"], "title": b["title"]}}
                for b in buttons[:3]
            ]
        }
    }
    if header_text:
        interactive["header"] = {"type": "text", "text": header_text}
    if footer_text:
        interactive["footer"] = {"text": footer_text}

    payload = {
        "messaging_product": "whatsapp",
        "to": normalize_phone(phone),
        "type": "interactive",
        "interactive": interactive
    }
    return _call_api(payload, conversation_name=conversation_name)


# ─────────────────────────────────────────────────────────────────────────────
# MEDIA UPLOAD
# ─────────────────────────────────────────────────────────────────────────────

def upload_media(file_path: str, mime_type: str) -> str:
    """Upload a file to WhatsApp and return the media_id."""
    settings = get_settings()
    url = f"https://graph.facebook.com/{settings.wa_api_version}/{settings.wa_phone_number_id}/media"
    headers = {"Authorization": f"Bearer {settings.get_password('wa_access_token')}"}

    with open(file_path, "rb") as f:
        resp = requests.post(url, headers=headers, files={
            "file": (file_path, f, mime_type),
            "type": (None, mime_type),
            "messaging_product": (None, "whatsapp")
        }, timeout=60)

    resp.raise_for_status()
    return resp.json().get("id")


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL API CALLER
# ─────────────────────────────────────────────────────────────────────────────

def _call_api(payload: dict, conversation_name: str = None) -> dict:
    settings = get_settings()

    if not settings.wa_enabled:
        frappe.log_error("WhatsApp not enabled in settings", "WA Send Skipped")
        return {"status": "skipped", "reason": "wa_not_enabled"}

    url = (
        f"https://graph.facebook.com/{settings.wa_api_version}"
        f"/{settings.wa_phone_number_id}/messages"
    )
    headers = {
        "Authorization": f"Bearer {settings.get_password('wa_access_token')}",
        "Content-Type": "application/json"
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        data = resp.json()

        if resp.status_code == 200:
            wa_msg_id = (data.get("messages") or [{}])[0].get("id")
            if conversation_name and wa_msg_id:
                _update_message_id(conversation_name, wa_msg_id)
            return {"status": "sent", "wa_message_id": wa_msg_id, "raw": data}
        else:
            err = data.get("error", {})
            frappe.log_error(
                f"WhatsApp API Error {resp.status_code}: {err.get('message')}",
                "WA API Error"
            )
            return {"status": "failed", "error_code": err.get("code"),
                    "error_message": err.get("message"), "raw": data}

    except requests.exceptions.Timeout:
        frappe.log_error("WhatsApp API timeout", "WA Timeout")
        return {"status": "failed", "error_message": "Request timeout"}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "WA Exception")
        return {"status": "failed", "error_message": str(e)}


def _update_message_id(conversation_name: str, wa_msg_id: str):
    """Backfill wa_message_id on the most recent outbound WA Message."""
    try:
        msgs = frappe.get_all(
            "WA Message",
            filters={"conversation": conversation_name, "direction": "Outbound",
                     "wa_message_id": ("is", "not set")},
            fields=["name"],
            order_by="creation desc",
            limit=1
        )
        if msgs:
            frappe.db.set_value("WA Message", msgs[0].name, "wa_message_id", wa_msg_id)
    except Exception:
        pass
