# message_blast/api/message_blast_api.py
# Copyright (c) 2025, Value Impacts Consulting
# Enterprise Message Blast — all whitelisted API endpoints

import frappe
import json
from frappe.utils import now_datetime, get_datetime, cstr


# ─────────────────────────────────────────────────────────────────────────────
# 1. SEND
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def send_blast(docname):
    """Main entry point called from the Send button."""
    doc = frappe.get_doc("Message Blast", docname)

    if doc.docstatus != 1:
        frappe.throw("Message Blast must be submitted before sending.")
    if doc.sent:
        frappe.throw("This Message Blast has already been fully sent.")
    if doc.status in ("Sending", "Sent"):
        frappe.throw(f"Message Blast is already in '{doc.status}' state.")

    expiry = getattr(doc, "expiry_date", None)
    if expiry and get_datetime(expiry) < now_datetime():
        frappe.throw("This Message Blast has passed its expiry date and cannot be sent.")

    doc.db_set("status", "Sending")
    frappe.db.commit()

    try:
        _dispatch(doc)
    except Exception:
        doc.db_set("status", "Failed")
        frappe.log_error(frappe.get_traceback(), f"Message Blast Send Failure: {docname}")
        frappe.throw("Send failed. Check the Error Log for details.")

    return {"success": True}


# ─────────────────────────────────────────────────────────────────────────────
# 2. RETRY FAILED
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def retry_failed(docname):
    doc = frappe.get_doc("Message Blast", docname)
    if doc.docstatus != 1:
        frappe.throw("Message Blast must be submitted.")

    reset = 0
    for row in doc.recipients:
        if row.delivery_status == "Failed":
            row.delivery_status = "Pending"
            row.error_message   = ""
            reset += 1

    if not reset:
        frappe.throw("No failed recipients to retry.")

    doc.save(ignore_permissions=True)
    doc.reload()
    doc.db_set("status", "Sending")
    frappe.db.commit()
    _dispatch(doc)
    return {"retried": reset}


# ─────────────────────────────────────────────────────────────────────────────
# 3. CANCEL SCHEDULED
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def cancel_scheduled(docname):
    doc = frappe.get_doc("Message Blast", docname)
    if doc.status != "Scheduled":
        frappe.throw("Only Scheduled blasts can be cancelled this way.")
    doc.db_set("status", "Cancelled")
    return {"cancelled": True}


# ─────────────────────────────────────────────────────────────────────────────
# 4. SEND PROGRESS
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_send_progress(docname):
    doc   = frappe.get_doc("Message Blast", docname)
    total = len(doc.recipients)
    sent  = sum(1 for r in doc.recipients if r.delivery_status == "Sent")
    fail  = sum(1 for r in doc.recipients if r.delivery_status == "Failed")
    pend  = sum(1 for r in doc.recipients if r.delivery_status == "Pending")
    return {
        "status":  doc.status,
        "total":   total,
        "sent":    sent,
        "failed":  fail,
        "pending": pend,
        "pct":     round((sent / total) * 100, 1) if total else 0
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. PREVIEW
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def preview_message(docname):
    doc     = frappe.get_doc("Message Blast", docname)
    context = _dummy_context(doc)
    body    = doc.message_tx_html if getattr(doc, "option", "") == "HTML" \
              else (doc.message_body or "")
    return {
        "html":    frappe.render_template(body or "", context),
        "subject": doc.subject
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6. IMPORT RECIPIENTS
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def import_recipients(docname, rows, column_map):
    """
    rows: JSON array of row objects parsed on the client from CSV/Excel.
    column_map: {full_name, email, mobile_phone, salutation, company} → column header string
    """
    doc = frappe.get_doc("Message Blast", docname)
    if isinstance(rows,       str): rows       = json.loads(rows)
    if isinstance(column_map, str): column_map = json.loads(column_map)

    existing = {(r.email or "").lower().strip() for r in doc.recipients}
    added = skipped = 0

    for row in rows:
        def _get(key):
            return cstr(row.get(column_map.get(key, ""), "")).strip()

        full_name  = _get("full_name")
        email      = _get("email")
        mobile     = _get("mobile_phone")
        salutation = _get("salutation")
        company    = _get("company")

        if not full_name:
            skipped += 1
            continue
        if email and email.lower() in existing:
            skipped += 1
            continue

        doc.append("recipients", {
            "full_name":       full_name,
            "email":           email,
            "mobile_phone":    mobile,
            "salutation":      salutation,
            "company":         company,
            "delivery_status": "Pending"
        })
        if email:
            existing.add(email.lower())
        added += 1

    doc.total_recipients = len(doc.recipients)
    doc.save(ignore_permissions=True)
    return {"added": added, "skipped": skipped, "total": len(doc.recipients)}


# ─────────────────────────────────────────────────────────────────────────────
# 7. SCHEDULER JOB — runs every 15 minutes via hooks.py
# ─────────────────────────────────────────────────────────────────────────────

def process_scheduled_blasts():
    now = now_datetime()
    due = frappe.get_all(
        "Message Blast",
        filters={"docstatus": 1, "status": "Scheduled", "schedule": 1,
                 "schedule_time": ["<=", now]},
        fields=["name", "expiry_date"]
    )
    for blast in due:
        if blast.get("expiry_date") and get_datetime(blast["expiry_date"]) < now:
            frappe.db.set_value("Message Blast", blast["name"], "status", "Cancelled")
            continue
        try:
            frappe.enqueue(
                "your_app.api.message_blast_api.send_blast",
                docname=blast["name"],
                queue="long",
                timeout=3600
            )
        except Exception:
            frappe.log_error(frappe.get_traceback(),
                             f"Scheduled Message Blast Error: {blast['name']}")


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL DISPATCH
# ─────────────────────────────────────────────────────────────────────────────

def _dispatch(doc):
    mt            = doc.message_type or ""
    do_email      = "Email"    in mt or getattr(doc, "send_email", 0)
    do_whatsapp   = "WhatsApp" in mt
    do_sms        = "SMS"      in mt

    attachments   = _collect_attachments(doc) if doc.include_attachments else []
    image_tags    = _collect_image_tags(doc)

    base_body = (
        (doc.message_tx_html if getattr(doc, "option", "") == "HTML" else doc.message_body) or ""
    ) + image_tags

    # ── Test mode
    if doc.is_test:
        _send_test(doc, base_body, attachments, do_email, do_whatsapp, do_sms)
        return

    # ── Live send
    sent_count = failed_count = 0

    for idx, r in enumerate(doc.recipients):
        if r.delivery_status == "Sent":
            sent_count += 1
            continue

        ctx    = _build_context(doc, r)
        errors = []

        if do_email and r.email:
            try:
                rendered = frappe.render_template(base_body, ctx)
                if getattr(doc, "unsubscribe_link", 0):
                    rendered += _unsubscribe_block(doc.name, r.name)
                from_addr = (
                    f"{doc.from_name or 'No Reply'} <{doc.from_email}>"
                    if doc.from_email else None
                )
                frappe.sendmail(
                    recipients=[r.email],
                    subject=doc.subject,
                    message=rendered,
                    sender=from_addr,
                    reply_to=getattr(doc, "reply_to_email", None) or doc.from_email,
                    attachments=attachments,
                    reference_doctype="Message Blast",
                    reference_name=doc.name,
                    template=False
                )
            except Exception as e:
                errors.append(f"Email: {e}")
                frappe.log_error(str(e), f"Message Blast Email [{doc.name}]")

        if do_whatsapp and r.mobile_phone:
            try:
                _send_whatsapp(doc, r.mobile_phone,
                               frappe.render_template(doc.whatsapp_message_body or "", ctx))
                frappe.db.set_value("Message Blast Recipient",
                                    r.name, "whatsapp_status", "Sent")
            except Exception as e:
                errors.append(f"WhatsApp: {e}")
                frappe.db.set_value("Message Blast Recipient",
                                    r.name, "whatsapp_status", "Failed")

        if do_sms and r.mobile_phone:
            try:
                _send_sms(doc, r.mobile_phone,
                          frappe.render_template(getattr(doc, "sms_message_body", "") or "", ctx))
                frappe.db.set_value("Message Blast Recipient",
                                    r.name, "sms_status", "Sent")
            except Exception as e:
                errors.append(f"SMS: {e}")
                frappe.db.set_value("Message Blast Recipient",
                                    r.name, "sms_status", "Failed")

        if errors:
            frappe.db.set_value("Message Blast Recipient", r.name, {
                "delivery_status": "Failed",
                "error_message":   "; ".join(errors),
                "sent_at":         now_datetime()
            })
            failed_count += 1
        else:
            frappe.db.set_value("Message Blast Recipient", r.name, {
                "delivery_status": "Sent",
                "error_message":   "",
                "sent_at":         now_datetime()
            })
            sent_count += 1

        if idx % 10 == 0:
            frappe.db.commit()

    frappe.db.commit()

    total = len(doc.recipients)
    if   failed_count == 0:   new_status = "Sent";           doc.db_set("sent", 1)
    elif sent_count   == 0:   new_status = "Failed"
    else:                     new_status = "Partially Sent"

    doc.db_set({
        "status":           new_status,
        "sent_count":       sent_count,
        "failed_count":     failed_count,
        "pending_count":    0,
        "total_recipients": total
    })


def _send_test(doc, base_body, attachments, do_email, do_whatsapp, do_sms):
    ctx = _dummy_context(doc)
    if do_email and getattr(doc, "test_email", None):
        rendered = frappe.render_template(base_body, ctx)
        frappe.sendmail(
            recipients=[doc.test_email],
            subject=f"[TEST] {doc.subject}",
            message=rendered,
            attachments=attachments,
            reference_doctype="Message Blast",
            reference_name=doc.name,
            template=False
        )
    if do_whatsapp and getattr(doc, "test_phone_number", None):
        _send_whatsapp(doc, doc.test_phone_number,
                       frappe.render_template(doc.whatsapp_message_body or "", ctx))
    if do_sms and getattr(doc, "test_phone_number", None):
        _send_sms(doc, doc.test_phone_number,
                  frappe.render_template(getattr(doc, "sms_message_body", "") or "", ctx))


def _build_context(doc, r):
    return {
        "full_name":       r.full_name or "",
        "salutation":      r.salutation or "Dear",
        "company":         getattr(r, "company", "") or "",
        "sender_name":     doc.from_name or "The Team",
        "summary":         getattr(doc, "summary", "") or "",
        "unsubscribe_url": _unsubscribe_url(doc.name, r.name)
    }


def _dummy_context(doc):
    return {
        "full_name":       "John Doe",
        "salutation":      "Dear",
        "company":         "Acme Corp",
        "sender_name":     doc.from_name or "The Team",
        "summary":         getattr(doc, "summary", "") or "",
        "unsubscribe_url": "#"
    }


def _unsubscribe_url(docname, recipient_name):
    token = frappe.generate_hash(length=24)
    return (f"{frappe.utils.get_url()}/unsubscribe"
            f"?doc={docname}&rid={recipient_name}&token={token}")


def _unsubscribe_block(docname, recipient_name):
    url = _unsubscribe_url(docname, recipient_name)
    return (
        "<br><br><hr style='border:none;border-top:1px solid #eee;margin:24px 0;'>"
        f"<p style='font-size:11px;color:#aaa;text-align:center;'>"
        f"You received this because you are on our mailing list. "
        f"<a href='{url}' style='color:#aaa;'>Unsubscribe</a></p>"
    )


def _collect_attachments(doc):
    result = []
    files  = frappe.get_all(
        "File",
        filters={"attached_to_doctype": "Message Blast", "attached_to_name": doc.name},
        fields=["file_url", "file_name", "is_private"]
    )
    for f in files:
        if f["file_url"].lower().endswith(('.png','.jpg','.jpeg','.gif','.webp')):
            continue
        try:
            fd   = frappe.get_doc("File", {"file_url": f["file_url"]})
            path = frappe.get_site_path(
                "private" if fd.is_private else "public",
                fd.file_url.lstrip('/')
            )
            with open(path, "rb") as fp:
                result.append((fd.file_name, fp.read()))
        except Exception:
            pass
    return result


def _collect_image_tags(doc):
    files = frappe.get_all(
        "File",
        filters={"attached_to_doctype": "Message Blast", "attached_to_name": doc.name},
        fields=["file_url"]
    )
    
    
    return "".join(
        f"<p style='text-align:center;'>"
        f"<img src='{f['file_url']}' style='max-width:100%;height:auto;border-radius:6px;'/></p>"
        for f in files
        if f.get("file_url") and f["file_url"].lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))
    )


def _send_whatsapp(doc, phone, message):
    """
    Plug in your WhatsApp gateway here.
    Example providers: Infobip, Twilio, Africa's Talking, TermiiNG.
    """
    # import requests
    # settings = frappe.get_single("WhatsApp Settings")
    # requests.post(settings.api_url, json={"to": phone, "message": message},
    #               headers={"Authorization": f"Bearer {settings.api_key}"})
    frappe.logger().info(f"[WhatsApp] To: {phone} | {message[:100]}")


def _send_sms(doc, phone, message):
    """Uses Frappe's built-in SMS Settings. Swap for your provider if needed."""
    try:
        from frappe.core.doctype.sms_settings.sms_settings import send_sms
        send_sms([phone], message)
    except Exception as e:
        frappe.log_error(str(e), "Message Blast SMS Error")
        raise