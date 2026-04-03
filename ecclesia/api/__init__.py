"""
ecclesia/api/__init__.py
Main API entry point for Ecclesia.
Provides get_boot_info() consumed by hooks.py boot_session.
"""

import frappe


def get_boot_info():
    """
    Called by hooks.py boot_session.
    Merges all Ecclesia boot data into frappe.boot so every desk
    page has it available immediately — same pattern as telephone.js.
    """
    boot = {}

    # ── Telephone (already existing) ─────────────────────────────────────────
    try:
        from ecclesia.api.telephone import get_telephone_boot_info
        boot["telephone"] = get_telephone_boot_info()
    except Exception:
        boot["telephone"] = {"enabled": False}

    # ── Internal Chat (WA Engine) ─────────────────────────────────────────────
    try:
        from ecclesia.utils.helpers import get_chat_boot_info
        boot["internal_chat"] = get_chat_boot_info()
    except Exception:
        boot["internal_chat"] = {"enabled": False}

    return boot


# ── Telephone API (existing) ──────────────────────────────────────────────────

@frappe.whitelist()
def initiate_call(receiver_number, source_doctype=None, source_docname=None):
    from ecclesia.api.telephone import initiate_call as _initiate_call
    return _initiate_call(receiver_number, source_doctype, source_docname)


@frappe.whitelist()
def update_call_status(tcl_name, status):
    from ecclesia.api.telephone import update_call_status as _update
    return _update(tcl_name, status)


@frappe.whitelist()
def save_call_notes(tcl_name, call_notes):
    from ecclesia.api.telephone import save_call_notes as _save
    return _save(tcl_name, call_notes)


@frappe.whitelist()
def webrtc_signal(target_user, signal_type, data):
    from ecclesia.api.telephone import webrtc_signal as _signal
    return _signal(target_user, signal_type, data)


@frappe.whitelist()
def notify_incoming_call(target_user, tcl_name, caller_number, caller_name):
    from ecclesia.api.telephone import notify_incoming_call as _notify
    return _notify(target_user, tcl_name, caller_number, caller_name)


@frappe.whitelist()
def asterisk_originate(receiver_number, tcl_name):
    from ecclesia.api.telephone import asterisk_originate as _originate
    return _originate(receiver_number, tcl_name)


def on_telephone_call_log_insert(doc, event):
    from ecclesia.api.telephone import on_call_log_insert
    on_call_log_insert(doc, event)


def sync_missed_calls():
    try:
        from ecclesia.api.telephone import sync_missed_calls as _sync
        _sync()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Sync Missed Calls Error")