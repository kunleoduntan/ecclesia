"""
ecclesia/api/notification.py
Notification Rule engine.
Called from hooks.py doc_events → evaluates rules → sends messages.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime
from jinja2 import Environment, BaseLoader
from ecclesia.utils.helpers import get_settings, resolve_phone


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT (called from hooks)
# ─────────────────────────────────────────────────────────────────────────────

def trigger_notification(doc, event: str):
    """
    Main hook handler. Finds all active notification rules
    matching this doctype + event and dispatches them.
    """
    rules = frappe.get_all(
        "WA Notification Rule",
        filters={
            "is_active":    1,
            "document_type": doc.doctype,
            "trigger_event": event
        },
        fields=["name"]
    )
    for rule_ref in rules:
        try:
            _process_rule(rule_ref.name, doc)
        except Exception:
            frappe.log_error(frappe.get_traceback(),
                             f"Notification Rule Error: {rule_ref.name}")


def _process_rule(rule_name: str, doc):
    rule = frappe.get_doc("WA Notification Rule", rule_name)

    # Evaluate condition
    if rule.condition:
        try:
            if not frappe.safe_eval(rule.condition, eval_locals={"doc": doc}):
                return
        except Exception as e:
            frappe.log_error(str(e), f"WA Rule Condition Error: {rule_name}")
            return

    # Dedup: send once per doc if configured
    if rule.send_once_per_doc:
        key = f"wa_rule_sent:{rule_name}:{doc.name}"
        if frappe.cache().get_value(key):
            return
        frappe.cache().set_value(key, 1, expires_in_sec=86400 * 365)

    # Resolve recipients
    recipients = _resolve_recipients(rule, doc)
    if not recipients:
        return

    # Build message content
    wa_components = None
    if rule.send_whatsapp and rule.wa_template:
        wa_components = _build_template_components(rule.wa_template, doc)

    # Dispatch with optional delay
    if rule.delay_minutes:
        frappe.enqueue(
            _dispatch_to_all,
            queue="long",
            enqueue_after_commit=True,
            delay=rule.delay_minutes * 60,
            rule=rule.as_dict(),
            doc_dict=doc.as_dict(),
            recipients=recipients,
            wa_components=wa_components
        )
    else:
        _dispatch_to_all(rule.as_dict(), doc.as_dict(), recipients, wa_components)


def _dispatch_to_all(rule: dict, doc_dict: dict, recipients: list, wa_components):
    settings = get_settings()
    doc = frappe._dict(doc_dict)

    for phone, email, name in recipients:
        # WhatsApp
        if rule.get("send_whatsapp") and settings.wa_enabled and phone:
            from ecclesia.api.whatsapp import send_template, send_text
            if rule.get("wa_template") and wa_components is not None:
                tmpl = frappe.get_doc("WA Template", rule["wa_template"])
                send_template(phone, tmpl.template_name, tmpl.language_code, wa_components)
            elif rule.get("sms_body"):
                # Fallback: send as plain text if no template
                body = _render_jinja(rule["sms_body"], doc)
                send_text(phone, body)

        # SMS
        if rule.get("send_sms") and settings.sms_enabled and phone:
            from ecclesia.api.sms import send_sms
            body = _render_jinja(rule.get("sms_body", ""), doc)
            if body:
                send_sms(phone, body)

        # Email
        if rule.get("send_email") and settings.email_enabled and email:
            subject = _render_jinja(rule.get("email_subject", "Notification from ERPNext"), doc)
            body    = _render_jinja(rule.get("email_body", ""), doc)
            frappe.sendmail(
                recipients=[email],
                subject=subject,
                message=body,
                reference_doctype=doc.get("doctype"),
                reference_name=doc.get("name")
            )


# ─────────────────────────────────────────────────────────────────────────────
# RECIPIENT RESOLUTION
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_recipients(rule, doc) -> list:
    """
    Returns list of (phone, email, display_name) tuples.
    """
    results = []
    for row in rule.recipients:
        rtype = row.recipient_type

        if rtype == "Document Field":
            phone = resolve_phone(getattr(doc, row.field_name, None))
            email = None
            if "@" in (phone or ""):        # field contains email
                email = phone; phone = None
            results.append((phone, email, ""))

        elif rtype == "Static Number":
            val = row.static_number or ""
            if "@" in val:
                results.append((None, val, ""))
            else:
                results.append((resolve_phone(val), None, ""))

        elif rtype == "Role":
            users = frappe.get_all(
                "Has Role",
                filters={"role": row.role, "parenttype": "User"},
                fields=["parent"]
            )
            for u in users:
                user_doc = frappe.get_doc("User", u.parent)
                results.append((user_doc.mobile_no, user_doc.email, user_doc.full_name))

        elif rtype == "User":
            user_doc = frappe.get_doc("User", row.user)
            results.append((user_doc.mobile_no, user_doc.email, user_doc.full_name))

        elif rtype == "Customer Contact":
            customer = getattr(doc, "customer", None)
            if customer:
                contacts = frappe.get_all(
                    "Contact",
                    filters={"link_doctype": "Customer", "link_name": customer},
                    fields=["mobile_no", "email_id", "full_name"],
                    limit=1
                )
                if contacts:
                    c = contacts[0]
                    results.append((resolve_phone(c.mobile_no), c.email_id, c.full_name))

        elif rtype == "Supplier Contact":
            supplier = getattr(doc, "supplier", None)
            if supplier:
                contacts = frappe.get_all(
                    "Contact",
                    filters={"link_doctype": "Supplier", "link_name": supplier},
                    fields=["mobile_no", "email_id", "full_name"],
                    limit=1
                )
                if contacts:
                    c = contacts[0]
                    results.append((resolve_phone(c.mobile_no), c.email_id, c.full_name))

    return [(p, e, n) for p, e, n in results if p or e]


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATE COMPONENT BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def _build_template_components(template_name: str, doc) -> list:
    """Build Meta API components array from template param mappings."""
    tmpl = frappe.get_doc("WA Template", template_name)
    body_params = []

    for row in sorted(tmpl.template_params, key=lambda r: r.param_index):
        value = _resolve_param(row, doc)
        body_params.append({"type": "text", "text": str(value)})

    components = []
    if body_params:
        components.append({"type": "body", "parameters": body_params})
    return components


def _resolve_param(row, doc) -> str:
    if row.source_type == "Document Field":
        val = getattr(doc, row.field_name, "")
        if row.format:
            try:
                val = row.format.format(val)
            except Exception:
                pass
        return val or ""
    elif row.source_type == "Custom Expression":
        try:
            return str(frappe.safe_eval(row.custom_expression, eval_locals={"doc": doc}))
        except Exception:
            return ""
    elif row.source_type == "Static Value":
        return row.static_value or ""
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# JINJA HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _render_jinja(template_str: str, doc) -> str:
    if not template_str:
        return ""
    try:
        env = Environment(loader=BaseLoader())
        tmpl = env.from_string(template_str)
        return tmpl.render(doc=doc, frappe=frappe)
    except Exception as e:
        frappe.log_error(str(e), "WA Jinja Render Error")
        return template_str
