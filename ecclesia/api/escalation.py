"""
ecclesia/api/escalation.py
Multi-level escalation engine.
Runs on scheduler (hourly) and checks all active Escalation Rules.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime, time_diff_in_hours
from ecclesia.api.notification import _render_jinja


# ─────────────────────────────────────────────────────────────────────────────
# SCHEDULER ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def check_all_escalations():
    """Called every hour from scheduler_events."""
    rules = frappe.get_all(
        "Escalation Rule",
        filters={"is_active": 1},
        fields=["name"]
    )
    for rule_ref in rules:
        try:
            _process_escalation_rule(rule_ref.name)
        except Exception:
            frappe.log_error(frappe.get_traceback(),
                             f"Escalation Rule Error: {rule_ref.name}")


def check_invoice_overdue(doc, event):
    """Hook: check invoice when updated (quick path)."""
    frappe.enqueue(
        "ecclesia.api.escalation.check_all_escalations",
        queue="long",
        enqueue_after_commit=True
    )


def check_ticket_escalation(doc, event):
    frappe.enqueue(
        "ecclesia.api.escalation.check_all_escalations",
        queue="long",
        enqueue_after_commit=True
    )


# ─────────────────────────────────────────────────────────────────────────────
# RULE PROCESSOR
# ─────────────────────────────────────────────────────────────────────────────

def _process_escalation_rule(rule_name: str):
    rule = frappe.get_doc("Escalation Rule", rule_name)
    if not rule.escalation_levels:
        return

    # Get matching documents
    docs = _get_matching_docs(rule)

    for doc_dict in docs:
        doc = frappe._dict(doc_dict)
        _escalate_doc(rule, doc)


def _get_matching_docs(rule) -> list:
    """Fetch documents that match the rule's doctype and condition."""
    base_filters = {}

    # Only submitted documents (docstatus=1) for transactional doctypes
    try:
        meta = frappe.get_meta(rule.document_type)
        if meta.is_submittable:
            base_filters["docstatus"] = 1
    except Exception:
        pass

    docs = frappe.get_all(
        rule.document_type,
        filters=base_filters,
        fields=["name", "creation", "owner", rule.trigger_field],
        limit=500
    )

    if not rule.filter_condition:
        return docs

    # Apply Python condition filter
    result = []
    for doc_dict in docs:
        try:
            doc = frappe.get_doc(rule.document_type, doc_dict["name"])
            if frappe.safe_eval(rule.filter_condition, eval_locals={"doc": doc}):
                result.append(doc.as_dict())
        except Exception:
            pass
    return result


def _escalate_doc(rule, doc):
    """Determine and fire the correct escalation level for a document."""
    trigger_val = doc.get(rule.trigger_field)
    if not trigger_val:
        return

    hours_elapsed = time_diff_in_hours(now_datetime(), trigger_val)
    if hours_elapsed <= 0:
        return

    # Sort levels by threshold ascending
    levels = sorted(rule.escalation_levels, key=lambda l: l.after_hours)

    # Find the highest level threshold that has been crossed
    # but hasn't been notified yet
    fired_level = None
    for level in reversed(levels):
        if hours_elapsed >= level.after_hours:
            fired_level = level
            break

    if not fired_level:
        return

    # Dedup: only fire each level once per document
    cache_key = f"esc:{rule.name}:{doc.name}:L{fired_level.level}"
    if frappe.cache().get_value(cache_key):
        return
    frappe.cache().set_value(cache_key, 1, expires_in_sec=3600 * 2)

    # Resolve notifiees
    notifiees = _resolve_notifiees(fired_level, doc)

    # Send notifications
    for phone, email, name in notifiees:
        _send_escalation_alert(rule, fired_level, doc, phone, email, name, hours_elapsed)

    # Execute auto-action on final level
    if fired_level.level == max(l.level for l in rule.escalation_levels):
        _execute_auto_action(rule, doc)


def _resolve_notifiees(level, doc) -> list:
    results = []

    if level.notify_role:
        users = frappe.get_all(
            "Has Role",
            filters={"role": level.notify_role, "parenttype": "User"},
            fields=["parent"]
        )
        for u in users:
            ud = frappe.get_doc("User", u.parent)
            results.append((ud.mobile_no, ud.email, ud.full_name))

    if level.notify_user:
        ud = frappe.get_doc("User", level.notify_user)
        results.append((ud.mobile_no, ud.email, ud.full_name))

    if level.notify_field:
        field_val = doc.get(level.notify_field)
        if field_val and "@" in str(field_val):
            ud = frappe.get_doc("User", field_val)
            results.append((ud.mobile_no, ud.email, ud.full_name))

    return [(p, e, n) for p, e, n in results if p or e]


def _send_escalation_alert(rule, level, doc, phone: str, email: str,
                            name: str, hours_elapsed: float):
    from ecclesia.utils.helpers import get_settings
    settings = get_settings()

    # Build message text
    if level.message_body:
        msg = _render_jinja(level.message_body, doc)
    else:
        msg = (
            f"⚠️ *Escalation Alert — Level {level.level}*\n"
            f"{rule.document_type}: *{doc.name}*\n"
            f"Open for: {hours_elapsed:.1f} hours\n"
            f"Requires immediate attention."
        )

    channels = level.channels or "WhatsApp"

    # WhatsApp
    if "WhatsApp" in channels and settings.wa_enabled and phone:
        from ecclesia.api.whatsapp import send_text
        if level.wa_template:
            from ecclesia.api.whatsapp import send_template
            from ecclesia.api.notification import _build_template_components
            tmpl = frappe.get_doc("WA Template", level.wa_template)
            components = _build_template_components(level.wa_template, doc)
            send_template(phone, tmpl.template_name, tmpl.language_code, components)
        else:
            send_text(phone, msg)

    # SMS
    if "SMS" in channels and settings.sms_enabled and phone:
        from ecclesia.api.sms import send_sms
        send_sms(phone, msg)

    # Email
    if "Email" in channels and settings.email_enabled and email:
        frappe.sendmail(
            recipients=[email],
            subject=f"[Escalation L{level.level}] {rule.document_type}: {doc.name}",
            message=msg.replace("\n", "<br>"),
            reference_doctype=rule.document_type,
            reference_name=doc.name
        )

    # Log escalation
    frappe.get_doc({
        "doctype":         "Comment",
        "comment_type":    "Info",
        "reference_doctype": rule.document_type,
        "reference_name":    doc.name,
        "content": f"[WA Escalation L{level.level}] Notified {name or phone or email}"
    }).insert(ignore_permissions=True)
    frappe.db.commit()


def _execute_auto_action(rule, doc):
    """Execute the configured auto-action on final escalation."""
    if not rule.auto_action_type:
        return
    try:
        full_doc = frappe.get_doc(rule.document_type, doc.name)
        full_doc.flags.ignore_permissions = True

        if rule.auto_action_type == "Assign to User" and rule.auto_action_assign_to:
            frappe.assign_to.add({
                "assign_to": [rule.auto_action_assign_to],
                "doctype":   rule.document_type,
                "name":      doc.name,
                "description": "Auto-assigned by Escalation Rule"
            })

        elif rule.auto_action_type == "Set Field Value":
            frappe.db.set_value(rule.document_type, doc.name,
                                rule.auto_action_field, rule.auto_action_value)

        elif rule.auto_action_type == "Submit" and full_doc.docstatus == 0:
            full_doc.submit()

        elif rule.auto_action_type == "Cancel" and full_doc.docstatus == 1:
            full_doc.cancel()

        elif rule.auto_action_type == "Custom Script" and rule.auto_action_script:
            frappe.safe_eval(rule.auto_action_script,
                             eval_locals={"doc": full_doc, "frappe": frappe})

        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         f"Escalation Auto-Action Error: {rule.name}")
