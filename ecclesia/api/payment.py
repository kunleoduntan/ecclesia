import frappe
import json


# ── Public endpoints ──────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def initiate(reference_doctype, reference_docname, gateway_name=None):
    """
    Initiate a payment for any document (Sales Invoice, Payment Request, etc.)
    Returns: { payment_url, log_name }
    """
    from ecclesia.utils.gateway_router import get_gateway_handler

    doc     = frappe.get_doc(reference_doctype, reference_docname)
    settings = _get_settings(gateway_name)
    handler  = get_gateway_handler(settings)

    amount   = getattr(doc, "grand_total", None) or getattr(doc, "amount", 0)
    currency = getattr(doc, "currency", None) or settings.currency or "NGN"
    email    = _customer_email(doc)

    result = handler.initiate(
        amount=amount, currency=currency,
        email=email, reference=reference_docname,
        callback_url=settings.callback_url
    )

    from ecclesia.payment_gateway.doctype.payment_gateway_log.payment_gateway_log import PaymentGatewayLog
    log_name = PaymentGatewayLog.create_log(
        gateway=settings.name,
        reference_doctype=reference_doctype,
        reference_docname=reference_docname,
        amount=amount, currency=currency,
        customer=getattr(doc, "customer", None),
        customer_email=email,
        transaction_ref=result.get("reference"),
        status="Initiated", response=result
    )

    return {"payment_url": result.get("authorization_url"), "log_name": log_name}


@frappe.whitelist(allow_guest=True)
def webhook(**kwargs):
    """
    Receive and process a payment gateway webhook.
    URL: /api/method/ecclesia.api.payment.webhook?gateway=<slug>
    """
    from ecclesia.utils.gateway_router import get_gateway_handler
    from ecclesia.payment_gateway.doctype.payment_gateway_log.payment_gateway_log import PaymentGatewayLog

    gateway_slug = frappe.request.args.get("gateway", "")
    payload      = json.loads(frappe.request.data or "{}")
    headers      = dict(frappe.request.headers)
    source_ip    = frappe.local.request_ip

    settings = _get_settings_by_slug(gateway_slug)
    handler  = get_gateway_handler(settings)

    sig_valid = handler.verify_webhook(
        payload, headers, settings.get_password("webhook_secret") or ""
    )

    # Find the pending log
    event     = handler.parse_event(payload)
    tx_ref    = event.get("transaction_ref")
    log_name  = frappe.db.get_value(
        "Payment Gateway Log",
        {"transaction_ref": tx_ref, "status": "Initiated"}, "name"
    ) if tx_ref else None

    if log_name:
        PaymentGatewayLog.update(
            log_name,
            status="Success" if event.get("status") == "success" else "Failed",
            transaction_ref=tx_ref,
            response=event,
            signature_valid=sig_valid,
            source_ip=source_ip
        )

    if event.get("status") == "success" and log_name:
        pe_name = _reconcile(log_name, event, settings)
        if pe_name:
            PaymentGatewayLog.update(log_name, status="Success", payment_entry=pe_name)

    return {"status": "ok"}


@frappe.whitelist()
def verify(transaction_ref, gateway_name=None):
    """Manually verify a transaction reference against the gateway."""
    from ecclesia.utils.gateway_router import get_gateway_handler
    settings = _get_settings(gateway_name)
    return get_gateway_handler(settings).verify(transaction_ref)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_settings(gateway_name=None):
    if gateway_name:
        return frappe.get_doc("Payment Gateway Settings", gateway_name)
    name = frappe.db.get_value(
        "Payment Gateway Settings", {"is_default": 1, "enabled": 1}, "name"
    )
    if not name:
        frappe.throw("No default Payment Gateway configured.")
    return frappe.get_doc("Payment Gateway Settings", name)


def _get_settings_by_slug(slug):
    # slug is frappe.scrub(gateway_name) — match on gateway_name field
    results = frappe.get_all(
        "Payment Gateway Settings",
        filters={"enabled": 1},
        fields=["name", "gateway_name"]
    )
    for r in results:
        if frappe.scrub(r.gateway_name) == slug or slug in r.gateway_name.lower():
            return frappe.get_doc("Payment Gateway Settings", r.name)
    frappe.throw(f"No active gateway found for slug: {slug}")


def _customer_email(doc):
    if getattr(doc, "contact_email", None):
        return doc.contact_email
    customer = getattr(doc, "customer", None)
    if customer:
        return frappe.db.get_value("Customer", customer, "email_id") or ""
    return ""


def _reconcile(log_name, event, settings):
    """Create Payment Entry linked to the Sales Invoice."""
    log = frappe.get_doc("Payment Gateway Log", log_name)
    if not log.reference_doctype or not log.reference_docname:
        return None
    try:
        inv = frappe.get_doc(log.reference_doctype, log.reference_docname)
        pe = frappe.get_doc({
            "doctype": "Payment Entry",
            "payment_type": "Receive",
            "party_type": "Customer",
            "party": getattr(inv, "customer", ""),
            "paid_amount": log.amount,
            "received_amount": log.amount,
            "reference_no": event.get("transaction_ref"),
            "reference_date": frappe.utils.today(),
            "mode_of_payment": settings.provider,
            "paid_to": frappe.db.get_value(
                "Company", inv.company, "default_bank_account"
            ) or "",
            "references": [{
                "reference_doctype": log.reference_doctype,
                "reference_name": log.reference_docname,
                "allocated_amount": log.amount
            }]
        })
        pe.insert(ignore_permissions=True)
        pe.submit()
        return pe.name
    except Exception as e:
        frappe.log_error(str(e), "Ecclesia Payment Reconciliation Failed")
        return None


def retry_failed_webhooks():
    """
    Scheduler task (every_15_minutes).
    Retries Payment Gateway Logs stuck in 'Failed' status — up to 3 attempts.
    Called from hooks.py scheduler_events.
    """
    failed_logs = frappe.get_all(
        "Payment Gateway Log",
        filters={
            "status":         "Failed",
            "retry_count":    ["<", 3],
            "transaction_ref": ["!=", ""],
        },
        fields=["name", "gateway", "transaction_ref", "retry_count"],
        limit=20
    )

    for log in failed_logs:
        try:
            settings = frappe.get_doc("Payment Gateway Settings", log.gateway)
            from ecclesia.utils.gateway_router import get_gateway_handler
            handler = get_gateway_handler(settings)
            result  = handler.verify(log.transaction_ref)

            from ecclesia.payment_gateway.doctype.payment_gateway_log.payment_gateway_log import PaymentGatewayLog
            if result.get("status") == "success":
                PaymentGatewayLog.update(log.name, status="Success", response=result)
                pe_name = _reconcile(log.name, result, settings)
                if pe_name:
                    PaymentGatewayLog.update(log.name, payment_entry=pe_name)
            else:
                frappe.db.set_value(
                    "Payment Gateway Log", log.name,
                    "retry_count", (log.retry_count or 0) + 1
                )
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Ecclesia: Webhook retry failed for log {log.name}"
            )

    if failed_logs:
        frappe.db.commit()