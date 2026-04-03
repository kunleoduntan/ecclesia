"""
ecclesia/ecclesia/api.py
========================
Single-file backend for the Ecclesia Telephone App.

Sections:
  1. Boot Info          — sends config to frontend on desk load
  2. Call Router        — decides Internal (WebRTC) vs External provider
  3. CRM Bridge         — resolves phone numbers to Frappe records
  4. Token Generator    — provider capability/access tokens
  5. WebRTC Signaling   — Socket.IO relay for WebRTC offer/answer/ICE
  6. Provider: Twilio
  7. Provider: Vonage
  8. Provider: Plivo
  9. Provider: Asterisk
 10. Webhook Handlers   — inbound call events from each provider
 11. Telephone Call Log Helpers   — create / update call logs
 12. Utility            — phone normaliser, user presence
"""

import frappe
import json
import re
import socket
from frappe.utils import now_datetime


# ═══════════════════════════════════════════════════════════════════════════════
# 1. BOOT INFO
# ═══════════════════════════════════════════════════════════════════════════════

def get_boot_info(bootinfo):
    """Called by hooks.py → boot_session. Sends safe config to every desk user."""
    try:
        settings = frappe.get_single("Telephone Settings")
        bootinfo.telephone = {
            "enabled":                   True,
            "default_call_mode":         settings.default_call_mode,
            "auto_detect_internal":      bool(settings.auto_detect_internal),
            "active_provider":           settings.active_provider,
            "dialpad_position":          settings.dialpad_position,
            "dialpad_theme":             settings.dialpad_theme,
            "show_dialpad_on_login":     bool(settings.show_dialpad_on_login),
            "keyboard_shortcut":         settings.keyboard_shortcut or "Alt+D",
            "ringtone_volume":           int(settings.ringtone_volume or 80),
            "enable_telephone_call_log":           bool(settings.enable_telephone_call_log),
            "enable_call_recording":     bool(settings.enable_call_recording),
            "stun_server_url":           settings.stun_server_url or "stun:stun.l.google.com:19302",
            "turn_server_url":           settings.turn_server_url or "",
            "turn_username":             settings.turn_username or "",
            # CRM Integration flags
            "enable_call_button_lead":        bool(settings.enable_call_button_lead),
            "enable_call_button_contact":     bool(settings.enable_call_button_contact),
            "enable_call_button_customer":    bool(settings.enable_call_button_customer),
            "enable_call_button_opportunity": bool(settings.enable_call_button_opportunity),
            "enable_call_button_employee":    bool(settings.enable_call_button_employee),
            "auto_create_telephone_call_log":           bool(settings.auto_create_telephone_call_log),
            "auto_open_record_on_inbound":    bool(settings.auto_open_record_on_inbound),
            "screen_pop_lookup_order":        [
                x.strip() for x in (settings.screen_pop_lookup_order or "Contact\nLead\nCustomer").splitlines()
                if x.strip()
            ],
        }
    except Exception:
        bootinfo.telephone = {"enabled": False}


# ═══════════════════════════════════════════════════════════════════════════════
# 2. CALL ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def initiate_call(receiver_number, source_doctype=None, source_docname=None):
    """
    Main entry point called by the frontend dialpad.
    Decides whether to route internally (WebRTC) or externally (provider).
    Returns a tcl_name + routing instructions to the client.
    """
    settings  = frappe.get_single("Telephone Settings")
    caller    = frappe.session.user
    number    = normalize_phone_number(receiver_number)
    crm_links = resolve_crm_links(number, source_doctype, source_docname)

    # Determine routing
    internal_user = _find_internal_user(number)
    is_internal   = bool(internal_user) and settings.auto_detect_internal

    if settings.default_call_mode == "Internal":
        is_internal = True

    tcl = _create_telephone_call_log(
        caller          = caller,
        receiver_number = number,
        direction       = "Outbound",
        call_type       = "Internal" if is_internal else "External",
        provider        = "WebRTC"   if is_internal else settings.active_provider,
        crm_links       = crm_links,
    )

    if is_internal:
        return {
            "routing":          "internal",
            "tcl_name":    tcl,
            "target_user":      internal_user,
            "crm_links":        crm_links,
        }
    else:
        token = _get_provider_token(settings, caller)
        return {
            "routing":          "external",
            "tcl_name":    tcl,
            "provider":         settings.active_provider,
            "token":            token,
            "caller_number":    _get_provider_caller_id(settings),
            "crm_links":        crm_links,
        }


def _find_internal_user(number):
    """Return frappe user email if phone matches a User or Employee record."""
    # Check User mobile_no
    user = frappe.db.get_value("User", {"mobile_no": number}, "name")
    if user:
        return user

    # Check Employee cell_number
    emp = frappe.db.get_value("Employee", {"cell_number": number}, "user_id")
    if emp:
        return emp

    return None


def _get_provider_caller_id(settings):
    caller_id_map = {
        "Twilio":   settings.twilio_phone_number,
        "Vonage":   settings.vonage_phone_number,
        "Plivo":    settings.plivo_phone_number,
        "Asterisk": settings.asterisk_sip_trunk,
    }
    return caller_id_map.get(settings.active_provider, "")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. CRM BRIDGE
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def resolve_crm_links(phone_number, source_doctype=None, source_docname=None):
    """
    Looks up a phone number across Contact, Lead, Customer, Employee.
    Returns dict of matched records for call log linking and screen-pop.
    """
    number = normalize_phone_number(phone_number)
    links  = {}

    # If called from a specific form, prefer that link
    source_map = {
        "Lead":        "lead",
        "Contact":     "contact",
        "Customer":    "customer",
        "Opportunity": "opportunity",
        "Employee":    "employee",
    }
    if source_doctype and source_docname and source_doctype in source_map:
        links[source_map[source_doctype]] = source_docname

        # If from Opportunity, also try to get linked Contact
        if source_doctype == "Opportunity" and not links.get("contact"):
            contact = frappe.db.get_value("Opportunity", source_docname, "contact_person")
            if contact:
                links["contact"] = contact

    # Search Contact
    if not links.get("contact"):
        contact = frappe.db.sql(
            """
            SELECT parent FROM `tabContact Phone`
            WHERE REPLACE(REPLACE(phone, ' ',''), '-','') = %s
            LIMIT 1
            """,
            normalize_phone_stripped(number),
            as_dict=True,
        )
        if contact:
            links["contact"] = contact[0].parent

    # Search Lead
    if not links.get("lead"):
        lead = frappe.db.sql(
            """
            SELECT name FROM `tabLead`
            WHERE REPLACE(REPLACE(mobile_no, ' ',''), '-','') = %s
               OR REPLACE(REPLACE(phone, ' ',''), '-','') = %s
            LIMIT 1
            """,
            (normalize_phone_stripped(number), normalize_phone_stripped(number)),
            as_dict=True,
        )
        if lead:
            links["lead"] = lead[0].name

    # Search Customer
    if not links.get("customer"):
        customer = frappe.db.get_value("Customer", {"mobile_no": number}, "name")
        if customer:
            links["customer"] = customer

    # Search Employee
    if not links.get("employee"):
        employee = frappe.db.get_value(
            "Employee", {"cell_number": number}, ["name", "employee_name"], as_dict=True
        )
        if employee:
            links["employee"] = employee.name

    # Resolve display names for screen-pop
    links["receiver_name"] = _resolve_display_name(links)

    return links


def _resolve_display_name(links):
    if links.get("contact"):
        c = frappe.db.get_value("Contact", links["contact"], ["first_name", "last_name"]) or ("", "")
        return " ".join(filter(None, c)).strip() or ""
    if links.get("lead"):
        return frappe.db.get_value("Lead", links["lead"], "lead_name") or ""
    if links.get("customer"):
        return links["customer"]
    if links.get("employee"):
        return frappe.db.get_value("Employee", links["employee"], "employee_name") or ""
    return ""


# ═══════════════════════════════════════════════════════════════════════════════
# 4. TOKEN / CAPABILITY GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_provider_token():
    """Returns a short-lived token for the active external provider SDK."""
    settings = frappe.get_single("Telephone Settings")
    return _get_provider_token(settings, frappe.session.user)


def _get_provider_token(settings, user):
    provider = settings.active_provider
    try:
        if provider == "Twilio":
            return _twilio_generate_token(settings, user)
        elif provider == "Vonage":
            return _vonage_generate_token(settings, user)
        elif provider == "Plivo":
            return _plivo_generate_token(settings, user)
        elif provider == "Asterisk":
            return {"type": "sip", "wss_url": settings.asterisk_wss_url}
    except Exception as e:
        frappe.log_error(f"Token generation failed for {provider}: {e}", "Ecclesia Token")
        # Attempt fallback provider
        if settings.fallback_provider and settings.fallback_provider != provider:
            return {"provider": settings.fallback_provider, "error": str(e), "fallback": True}
        raise


# ═══════════════════════════════════════════════════════════════════════════════
# 5. WEBRTC SIGNALING  (Socket.IO relay — called from frontend via frappe.realtime)
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def webrtc_signal(target_user, signal_type, data):
    """
    Relay WebRTC signaling messages between peers via Frappe Socket.IO.
    signal_type: offer | answer | ice_candidate | hang_up | reject
    """
    allowed = ["offer", "answer", "ice_candidate", "hang_up", "reject"]
    if signal_type not in allowed:
        frappe.throw(f"Invalid signal type: {signal_type}")

    caller = frappe.session.user

    frappe.publish_realtime(
        event     = "ecclesia_webrtc_signal",
        room      = f"user:{target_user}",
        message   = {
            "signal_type": signal_type,
            "from_user":   caller,
            "payload":     data if isinstance(data, dict) else json.loads(data),
        },
        after_commit = False,
    )
    return {"status": "sent"}


@frappe.whitelist()
def notify_incoming_call(target_user, tcl_name, caller_number, caller_name):
    """Push an incoming call notification to a specific user's desk."""
    frappe.publish_realtime(
        event   = "ecclesia_incoming_call",
        room    = f"user:{target_user}",
        message = {
            "tcl_name":      tcl_name,
            "caller_number": caller_number,
            "caller_name":   caller_name,
            "from_user":     caller_number,  # same as caller_number for internal calls
        },
        after_commit = False,
    )
    return {"status": "notified"}


# ═══════════════════════════════════════════════════════════════════════════════
# 6. PROVIDER: TWILIO
# ═══════════════════════════════════════════════════════════════════════════════

def _twilio_generate_token(settings, user):
    from twilio.jwt.access_token import AccessToken
    from twilio.jwt.access_token.grants import VoiceGrant

    grant = VoiceGrant(
        outgoing_application_sid = settings.twilio_twiml_app_sid,
        incoming_allow            = True,
    )
    token = AccessToken(
        settings.twilio_account_sid,
        settings.twilio_auth_token,      # Use API Key SID in production
        settings.twilio_auth_token,      # Use API Key Secret in production
        identity = _safe_identity(user),
        ttl      = 3600,
    )
    token.add_grant(grant)
    return {"type": "twilio", "token": token.to_jwt()}


@frappe.whitelist(allow_guest=True)
def twilio_webhook():
    """Handle inbound Twilio call — TwiML response + screen-pop."""
    from_number = frappe.form_dict.get("From", "")
    to_number   = frappe.form_dict.get("To", "")
    call_sid    = frappe.form_dict.get("CallSid", "")

    crm_links = resolve_crm_links(from_number)
    tcl  = _create_telephone_call_log(
        caller          = "Inbound",
        receiver_number = to_number,
        direction       = "Inbound",
        call_type       = "External",
        provider        = "Twilio",
        call_sid        = call_sid,
        crm_links       = crm_links,
    )

    _push_screen_pop(from_number, crm_links, tcl)

    # Return TwiML to connect to the browser client
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Dial callerId="{to_number}">
        <Client>{_safe_identity(frappe.session.user)}</Client>
    </Dial>
</Response>"""

    frappe.response.content_type = "text/xml"
    frappe.response.response      = twiml
    return


@frappe.whitelist(allow_guest=True)
def twilio_status_webhook():
    """Handle Twilio call status callbacks to update Telephone Call Log."""
    call_sid    = frappe.form_dict.get("CallSid", "")
    call_status = frappe.form_dict.get("CallStatus", "")

    status_map = {
        "completed":  "Answered",
        "busy":       "Busy",
        "no-answer":  "Missed",
        "failed":     "Failed",
        "canceled":   "Declined",
    }
    status = status_map.get(call_status, "Failed")

    log = frappe.db.get_value("Telephone Call Log", {"call_sid": call_sid}, "name")
    if log:
        from ecclesia.ecclesia.doctype.telephone_call_log.telephone_call_log import TelephoneCallLog as CallLog
        CallLog.update_status(log, status, ended_at=now_datetime())

    frappe.response.http_status_code = 204


# ═══════════════════════════════════════════════════════════════════════════════
# 7. PROVIDER: VONAGE
# ═══════════════════════════════════════════════════════════════════════════════

def _vonage_generate_token(settings, user):
    import vonage

    client = vonage.Client(
        application_id = settings.vonage_app_id,
        private_key    = settings.get_password("vonage_private_key"),
    )
    # Vonage JWT for client SDK
    token = client.generate_application_jwt()
    return {"type": "vonage", "token": token.decode("utf-8") if isinstance(token, bytes) else token}


@frappe.whitelist(allow_guest=True)
def vonage_webhook():
    """Handle inbound Vonage call — NCCO response + screen-pop."""
    data        = json.loads(frappe.request.data or "{}")
    from_number = data.get("from", "")
    to_number   = data.get("to", "")
    uuid        = data.get("uuid", "")

    crm_links = resolve_crm_links(from_number)
    tcl  = _create_telephone_call_log(
        caller          = "Inbound",
        receiver_number = to_number,
        direction       = "Inbound",
        call_type       = "External",
        provider        = "Vonage",
        call_sid        = uuid,
        crm_links       = crm_links,
    )

    _push_screen_pop(from_number, crm_links, tcl)

    ncco = [{"action": "talk", "text": "Connecting your call."},
            {"action": "connect", "endpoint": [{"type": "websocket", "uri": frappe.utils.get_url()}]}]

    frappe.response.content_type = "application/json"
    frappe.response.response      = json.dumps(ncco)
    return


@frappe.whitelist(allow_guest=True)
def vonage_event_webhook():
    """Handle Vonage call event updates."""
    data   = json.loads(frappe.request.data or "{}")
    uuid   = data.get("uuid", "")
    status = data.get("status", "")

    status_map = {
        "completed": "Answered",
        "busy":      "Busy",
        "unanswered":"Missed",
        "failed":    "Failed",
        "rejected":  "Declined",
    }
    mapped = status_map.get(status)
    if mapped and uuid:
        log = frappe.db.get_value("Telephone Call Log", {"call_sid": uuid}, "name")
        if log:
            from ecclesia.ecclesia.doctype.telephone_call_log.telephone_call_log import TelephoneCallLog as CallLog
            CallLog.update_status(log, mapped, ended_at=now_datetime())

    frappe.response.http_status_code = 204


# ═══════════════════════════════════════════════════════════════════════════════
# 8. PROVIDER: PLIVO
# ═══════════════════════════════════════════════════════════════════════════════

def _plivo_generate_token(settings, user):
    import plivo

    endpoint_username = _safe_identity(user)
    endpoint_password = frappe.generate_hash(user, 10)   # store if needed

    p = plivo.RestClient(settings.plivo_auth_id, settings.plivo_auth_token)

    # Ensure endpoint exists
    try:
        p.endpoints.get(endpoint_username)
    except Exception:
        p.endpoints.create(
            username    = endpoint_username,
            password    = endpoint_password,
            alias       = frappe.db.get_value("User", user, "full_name") or user,
            app_id      = None,
        )

    # Generate Plivo Web SDK token (access_token)
    token = plivo.utils.plivoxml.generate_token(
        settings.plivo_auth_id,
        settings.plivo_auth_token,
        endpoint_username,
        valid_secs = 3600,
    )
    return {"type": "plivo", "token": token, "username": endpoint_username}


@frappe.whitelist(allow_guest=True)
def plivo_webhook():
    """Handle inbound Plivo call — XML response + screen-pop."""
    from_number = frappe.form_dict.get("From", "")
    to_number   = frappe.form_dict.get("To", "")
    call_uuid   = frappe.form_dict.get("CallUUID", "")

    crm_links = resolve_crm_links(from_number)
    tcl  = _create_telephone_call_log(
        caller          = "Inbound",
        receiver_number = to_number,
        direction       = "Inbound",
        call_type       = "External",
        provider        = "Plivo",
        call_sid        = call_uuid,
        crm_links       = crm_links,
    )

    _push_screen_pop(from_number, crm_links, tcl)

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Dial>
        <User>{_safe_identity(frappe.session.user)}</User>
    </Dial>
</Response>"""

    frappe.response.content_type = "text/xml"
    frappe.response.response      = xml
    return


@frappe.whitelist(allow_guest=True)
def plivo_status_webhook():
    """Handle Plivo call hangup status."""
    call_uuid   = frappe.form_dict.get("CallUUID", "")
    hangup_cause = frappe.form_dict.get("HangupCause", "")

    status_map = {
        "NORMAL_CLEARING":      "Answered",
        "USER_BUSY":            "Busy",
        "NO_USER_RESPONSE":     "Missed",
        "NO_ANSWER":            "Missed",
        "ORIGINATOR_CANCEL":    "Declined",
    }
    status = status_map.get(hangup_cause, "Failed")

    if call_uuid:
        log = frappe.db.get_value("Telephone Call Log", {"call_sid": call_uuid}, "name")
        if log:
            from ecclesia.ecclesia.doctype.telephone_call_log.telephone_call_log import TelephoneCallLog as CallLog
            CallLog.update_status(log, status, ended_at=now_datetime())

    frappe.response.http_status_code = 204


# ═══════════════════════════════════════════════════════════════════════════════
# 9. PROVIDER: ASTERISK (AMI)
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def asterisk_originate(receiver_number, tcl_name):
    """Originate an outbound call via Asterisk AMI."""
    settings = frappe.get_single("Telephone Settings")
    number   = normalize_phone_number(receiver_number)

    try:
        response = _ami_originate(settings, number, frappe.session.user)
        return {"status": "ok", "response": response}
    except Exception as e:
        frappe.log_error(f"Asterisk originate failed: {e}", "Ecclesia Asterisk")
        _update_telephone_call_log_status(tcl_name, "Failed")
        frappe.throw(f"Asterisk error: {e}")


def _ami_originate(settings, number, user):
    """Low-level AMI socket communication."""
    host     = settings.asterisk_ami_host
    port     = int(settings.asterisk_ami_port or 5038)
    username = settings.asterisk_ami_username
    password = settings.get_password("asterisk_ami_password")
    context  = settings.asterisk_default_context or "from-internal"
    extension= _safe_identity(user)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    s.connect((host, port))

    def send(msg):
        s.sendall((msg + "\r\n").encode())

    def recv():
        data = b""
        while b"\r\n\r\n" not in data:
            data += s.recv(1024)
        return data.decode()

    recv()  # Banner

    send(f"Action: Login\r\nUsername: {username}\r\nSecret: {password}")
    recv()

    send(
        f"Action: Originate\r\n"
        f"Channel: SIP/{number}\r\n"
        f"Context: {context}\r\n"
        f"Exten: {extension}\r\n"
        f"Priority: 1\r\n"
        f"CallerID: {extension} <{number}>\r\n"
        f"Timeout: 30000\r\n"
        f"Async: true"
    )
    response = recv()

    send("Action: Logoff")
    s.close()

    return response


@frappe.whitelist()
def test_provider_connection():
    """Test the active provider credentials without making a real call."""
    settings = frappe.get_single("Telephone Settings")
    provider = settings.active_provider

    try:
        if provider == "Twilio":
            from twilio.rest import Client
            client = Client(settings.twilio_account_sid, settings.get_password("twilio_auth_token"))
            account = client.api.accounts(settings.twilio_account_sid).fetch()
            return {"success": True, "detail": f"Twilio: Account '{account.friendly_name}' OK"}

        elif provider == "Vonage":
            import vonage
            client = vonage.Client(
                key    = settings.vonage_api_key,
                secret = settings.get_password("vonage_api_secret"),
            )
            balance = client.get_balance()
            return {"success": True, "detail": f"Vonage: Balance {balance['value']} EUR OK"}

        elif provider == "Plivo":
            import plivo
            p = plivo.RestClient(settings.plivo_auth_id, settings.get_password("plivo_auth_token"))
            acct = p.accounts.get()
            return {"success": True, "detail": f"Plivo: Account '{acct.api_id}' OK"}

        elif provider == "Asterisk":
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((settings.asterisk_ami_host, int(settings.asterisk_ami_port or 5038)))
            banner = s.recv(256).decode()
            s.close()
            return {"success": True, "detail": f"Asterisk AMI reachable: {banner.strip()}"}

    except Exception as e:
        return {"success": False, "detail": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# 10. WEBHOOK HELPERS — Screen-pop push
# ═══════════════════════════════════════════════════════════════════════════════

def _push_screen_pop(from_number, crm_links, tcl_name):
    """Push incoming call screen-pop to all online System Manager users."""
    settings = frappe.get_single("Telephone Settings")
    if not settings.auto_open_record_on_inbound:
        return

    online_users = frappe.db.get_all(
        "User",
        filters={"enabled": 1, "user_type": "System User"},
        pluck="name",
    )

    message = {
        "tcl_name":  tcl_name,
        "caller_number":  from_number,
        "caller_name":    crm_links.get("receiver_name", ""),
        "lead":           crm_links.get("lead"),
        "contact":        crm_links.get("contact"),
        "customer":       crm_links.get("customer"),
        "opportunity":    crm_links.get("opportunity"),
        "employee":       crm_links.get("employee"),
    }

    for user in online_users:
        frappe.publish_realtime(
            event   = "ecclesia_incoming_call",
            room    = f"user:{user}",
            message = message,
            after_commit = False,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 11. CALL LOG HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _create_telephone_call_log(caller, receiver_number, direction, call_type, provider,
                     crm_links=None, call_sid=None):
    """Internal helper — creates and inserts a Telephone Call Log document."""
    settings = frappe.get_single("Telephone Settings")
    if not settings.enable_telephone_call_log:
        return None

    crm_links = crm_links or {}
    doc = frappe.get_doc({
        "doctype":         "Telephone Call Log",
        "caller_user":     caller if frappe.db.exists("User", caller) else None,
        "direction":       direction,
        "call_type":       call_type,
        "provider":        provider,
        "status":          "Initiated",
        "receiver_number": receiver_number,
        "receiver_name":   crm_links.get("receiver_name", ""),
        "call_sid":        call_sid or "",
        "started_at":      now_datetime(),
        "lead":            crm_links.get("lead"),
        "contact":         crm_links.get("contact"),
        "customer":        crm_links.get("customer"),
        "opportunity":     crm_links.get("opportunity"),
        "employee":        crm_links.get("employee"),
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return doc.name


@frappe.whitelist()
def update_call_status(tcl_name, status, call_sid=None):
    """Called by frontend when call state changes."""
    if not tcl_name:
        return

    doc = frappe.get_doc("Telephone Call Log", tcl_name)
    doc.status = status

    if status == "Answered" and not doc.answered_at:
        doc.answered_at = now_datetime()

    if status in ("Answered", "Missed", "Failed", "Busy", "Declined"):
        doc.ended_at = now_datetime()

    if call_sid:
        doc.call_sid = call_sid

    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "updated"}


@frappe.whitelist()
def save_call_notes(tcl_name, call_notes, follow_up_date=None, follow_up_note=None):
    """Save notes during or after a call."""
    doc = frappe.get_doc("Telephone Call Log", tcl_name)
    doc.call_notes    = call_notes
    doc.follow_up_date = follow_up_date
    doc.follow_up_note = follow_up_note
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "saved"}


@frappe.whitelist()
def get_recent_telephone_call_logs(limit=20):
    """Return recent call logs for the current user — used by dialpad history tab."""
    from ecclesia.ecclesia.doctype.telephone_call_log.telephone_call_log import TelephoneCallLog as CallLog
    return CallLog.get_recent_logs(frappe.session.user, int(limit))


def on_telephone_call_log_insert(doc, method):
    """Hook: after_insert — broadcast new call log to all tabs of the caller."""
    frappe.publish_realtime(
        event   = "ecclesia_telephone_call_log_created",
        room    = f"user:{doc.caller_user}",
        message = {"tcl_name": doc.name},
        after_commit = True,
    )


def sync_missed_calls():
    """Scheduled: mark old Initiated/Ringing logs as Missed after max_call_duration."""
    settings = frappe.get_single("Telephone Settings")
    max_mins = int(settings.max_call_duration or 60)

    stale = frappe.db.sql(
        """
        SELECT name FROM `tabTelephone Call Log`
        WHERE status IN ('Initiated', 'Ringing')
          AND started_at < (NOW() - INTERVAL %s MINUTE)
        """,
        max_mins,
        as_dict=True,
    )
    for row in stale:
        from ecclesia.ecclesia.doctype.telephone_call_log.telephone_call_log import TelephoneCallLog as CallLog
        CallLog.update_status(row.name, "Missed", ended_at=now_datetime())


# ═══════════════════════════════════════════════════════════════════════════════
# 12. UTILITY
# ═══════════════════════════════════════════════════════════════════════════════

def normalize_phone_number(number):
    """Normalize a phone number to E.164 format (best-effort)."""
    if not number:
        return ""
    # Strip everything except digits and leading +
    cleaned = re.sub(r"[^\d+]", "", str(number).strip())
    if not cleaned.startswith("+"):
        # Assume international if > 10 digits, else local
        if len(cleaned) > 10:
            cleaned = "+" + cleaned
    return cleaned


def normalize_phone_stripped(number):
    """Return digits-only version for flexible DB matching."""
    return re.sub(r"\D", "", str(number or ""))


def _safe_identity(user):
    """Convert email to a provider-safe identity string (no @ or dots)."""
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", user)


def _update_telephone_call_log_status(tcl_name, status):
    if tcl_name:
        try:
            from ecclesia.ecclesia.doctype.telephone_call_log.telephone_call_log import TelephoneCallLog as CallLog
            CallLog.update_status(tcl_name, status, ended_at=now_datetime())
        except Exception:
            pass


@frappe.whitelist()
def install_crm_client_scripts():
    """
    Manually install/refresh the CRM Client Scripts.
    Run this from the browser console if buttons are missing after install:
        frappe.call('ecclesia.api.install_crm_client_scripts')
    Or from bench:
        bench --site yoursite execute ecclesia.api.install_crm_client_scripts
    """
    from ecclesia.install import install_client_scripts
    install_client_scripts()
    return {"status": "ok", "message": "Client Scripts installed successfully"}