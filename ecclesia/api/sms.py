"""
ecclesia/api/sms.py
SMS sending via multiple providers.
"""

import frappe
import requests
from ecclesia.utils.helpers import get_settings, normalize_phone


def send_sms(phone: str, body: str) -> dict:
    settings = get_settings()
    provider = settings.sms_provider

    if not settings.sms_enabled:
        return {"status": "skipped"}

    phone = normalize_phone(phone)

    try:
        if provider == "Twilio":
            return _send_twilio(phone, body, settings)
        elif provider == "Termii":
            return _send_termii(phone, body, settings)
        elif provider == "Africa's Talking":
            return _send_africastalking(phone, body, settings)
        elif provider == "Nexmo (Vonage)":
            return _send_vonage(phone, body, settings)
        else:
            return {"status": "failed", "error": "No SMS provider configured"}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "SMS Send Error")
        return {"status": "failed", "error": str(e)}


def _send_twilio(phone: str, body: str, settings) -> dict:
    from twilio.rest import Client
    client = Client(
        settings.get_password("sms_api_key"),
        settings.get_password("sms_api_secret")
    )
    msg = client.messages.create(
        body=body,
        from_=settings.sms_sender_id,
        to=f"+{phone}"
    )
    return {"status": "sent", "sid": msg.sid}


def _send_termii(phone: str, body: str, settings) -> dict:
    resp = requests.post(
        "https://api.ng.termii.com/api/sms/send",
        json={
            "to":      phone,
            "from":    settings.sms_sender_id or "N-Alert",
            "sms":     body,
            "type":    "plain",
            "channel": "dnd",
            "api_key": settings.get_password("sms_api_key")
        },
        timeout=15
    )
    data = resp.json()
    if data.get("message_id"):
        return {"status": "sent", "message_id": data["message_id"]}
    return {"status": "failed", "error": data.get("message", "Unknown")}


def _send_africastalking(phone: str, body: str, settings) -> dict:
    import africastalking
    africastalking.initialize(
        settings.sms_sender_id or "sandbox",
        settings.get_password("sms_api_key")
    )
    sms = africastalking.SMS
    resp = sms.send(body, [f"+{phone}"])
    return {"status": "sent", "raw": resp}


def _send_vonage(phone: str, body: str, settings) -> dict:
    import vonage
    client = vonage.Client(
        key=settings.get_password("sms_api_key"),
        secret=settings.get_password("sms_api_secret")
    )
    sms = vonage.Sms(client)
    resp = sms.send_message({
        "from": settings.sms_sender_id or "ERPNext",
        "to":   phone,
        "text": body
    })
    msg = resp["messages"][0]
    if msg["status"] == "0":
        return {"status": "sent", "message_id": msg["message-id"]}
    return {"status": "failed", "error": msg.get("error-text")}
