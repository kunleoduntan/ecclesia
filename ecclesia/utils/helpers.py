"""
ecclesia/utils/helpers.py
Shared utility functions for Ecclesia including WA Engine.
"""

import re
import frappe


# ─────────────────────────────────────────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────────────────────────────────────────

_settings_cache = None


def get_settings():
    """Return WA Settings singleton (cached per request)."""
    global _settings_cache
    if not _settings_cache:
        _settings_cache = frappe.get_single("WA Settings")
    return _settings_cache


def clear_settings_cache(doc=None, event=None):
    """
    Clears the cached WA Settings object.
    Called by hooks.py doc_events on WA Settings on_update —
    Frappe passes (doc, event) so both params are required.
    """
    global _settings_cache
    _settings_cache = None
    frappe.cache().delete_key("wa_settings_boot")


# ─────────────────────────────────────────────────────────────────────────────
# BOOT SESSION DATA
# ─────────────────────────────────────────────────────────────────────────────

def get_chat_boot_info() -> dict:
    """
    Returns internal_chat config dict for frappe.boot.internal_chat.
    Called from ecclesia/api/__init__.py inside get_boot_info() —
    same pattern as frappe.boot.telephone used by telephone.js.

    NOTE: This is intentionally NOT named get_boot_info() because
    hooks.py boot_session points to ecclesia.api.get_boot_info,
    not ecclesia.utils.helpers. This function is a helper that
    api/__init__.py calls and merges into the main boot payload.
    """
    user = frappe.session.user
    if not user or user == "Guest":
        return {"enabled": False}

    try:
        settings = get_settings()
        return {
            "enabled":                  bool(settings.internal_chat_enabled),
            "max_file_size_mb":         settings.max_file_size_mb or 25,
            "allowed_file_types":       settings.allowed_file_types or "",
            "enable_read_receipts":     bool(settings.enable_read_receipts),
            "enable_typing_indicator":  bool(settings.enable_typing_indicator),
            "enable_online_status":     bool(settings.enable_online_status),
            "chat_position":            settings.chat_position or "Bottom Right",
        }
    except Exception:
        # WA Settings may not exist yet on first install
        return {"enabled": False}


# ─────────────────────────────────────────────────────────────────────────────
# PHONE NORMALIZATION
# ─────────────────────────────────────────────────────────────────────────────

def normalize_phone(phone: str) -> str:
    """
    Strip all non-digits and ensure country code is prepended.
    '+234 803 123 4567'  →  '2348031234567'
    '08031234567'        →  '2348031234567'
    """
    if not phone:
        return ""

    digits = re.sub(r"\D", "", str(phone))

    # Handle leading 0 (local Nigerian format)
    if digits.startswith("0") and len(digits) == 11:
        try:
            default_cc = frappe.db.get_single_value(
                "WA Settings", "default_country_code"
            ) or "234"
        except Exception:
            default_cc = "234"
        digits = default_cc + digits[1:]

    return digits


def resolve_phone(value: str):
    """Return normalized phone or None if empty or an email address."""
    if not value:
        return None
    if "@" in str(value):
        return None
    return normalize_phone(value) or None


# ─────────────────────────────────────────────────────────────────────────────
# MISC
# ─────────────────────────────────────────────────────────────────────────────

def format_currency(amount, currency: str = None) -> str:
    if currency is None:
        currency = frappe.db.get_default("currency") or "NGN"
    return frappe.format_value(amount, {"fieldtype": "Currency", "options": currency})


def truncate(text: str, max_len: int = 60) -> str:
    if not text:
        return ""
    return text[:max_len] + ("…" if len(text) > max_len else "")
    
    
    
    
    
    
#Helper functions for payment gateway
"""
Routes to the correct gateway handler based on Payment Gateway Settings provider field.
"""
import frappe


def get_gateway_handler(settings):
    provider = settings.provider
    handlers = {
        "Paystack": "ecclesia.utils.gateways.paystack.PaystackHandler",
        "Flutterwave": "ecclesia.utils.gateways.flutterwave.FlutterwaveHandler",
        "Remita": "ecclesia.utils.gateways.remita.RemitaHandler",
        "Stripe": "ecclesia.utils.gateways.stripe.StripeHandler",
        "Squad": "ecclesia.utils.gateways.squad.SquadHandler",
        "M-Pesa": "ecclesia.utils.gateways.mpesa.MpesaHandler",
    }
    path = handlers.get(provider)
    if not path:
        frappe.throw(f"No handler implemented for provider: {provider}")

    module_path, class_name = path.rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    return cls(settings)