"""
ecclesia/api/broadcast.py
Broadcast / bulk message campaigns.
"""

import frappe
from frappe.utils import now_datetime
from ecclesia.utils.helpers import resolve_phone


# ─────────────────────────────────────────────────────────────────────────────
# SCHEDULER ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def process_pending_broadcasts():
    """Called every hour — send broadcasts that are scheduled and due."""
    broadcasts = frappe.get_all(
        "WA Broadcast",
        filters={
            "status": "Scheduled",
            "scheduled_at": ("<=", now_datetime())
        },
        fields=["name"]
    )
    for b in broadcasts:
        frappe.enqueue(
            "ecclesia.api.broadcast.run_broadcast",
            queue="long",
            broadcast_name=b.name
        )


# ─────────────────────────────────────────────────────────────────────────────
# RUN BROADCAST
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def run_broadcast(broadcast_name: str):
    """Execute a broadcast: build recipient list and send to each."""
    broadcast = frappe.get_doc("WA Broadcast", broadcast_name)

    if broadcast.status not in ("Scheduled", "Draft"):
        return

    frappe.db.set_value("WA Broadcast", broadcast_name, "status", "Running")
    frappe.db.commit()

    # Build full recipient list
    recipients = _build_recipients(broadcast)
    total = len(recipients)

    frappe.db.set_value("WA Broadcast", broadcast_name, "total_recipients", total)
    frappe.db.commit()

    sent = delivered = failed = 0

    for phone, name, custom_params, row_name in recipients:
        result = _send_to_recipient(broadcast, phone, name, custom_params)
        status = result.get("status", "failed")

        if row_name:
            frappe.db.set_value("WA Broadcast Recipient", row_name, {
                "status":       status if status in ("sent", "failed") else "pending",
                "wa_message_id": result.get("wa_message_id", ""),
                "error":         result.get("error_message", "")
            })

        if status == "sent":
            sent += 1
        else:
            failed += 1

    frappe.db.set_value("WA Broadcast", broadcast_name, {
        "status":      "Completed",
        "sent_count":  sent,
        "failed_count": failed
    })
    frappe.db.commit()


def _build_recipients(broadcast) -> list:
    """Returns list of (phone, name, custom_params, row_name)."""
    results = []
    source = broadcast.recipient_source

    if source == "Manual List":
        for row in broadcast.recipients:
            results.append((
                resolve_phone(row.phone_number),
                row.name_display or row.phone_number,
                row.custom_params or None,
                row.name
            ))

    elif source == "Customer Group":
        customers = frappe.get_all(
            "Customer",
            filters={"customer_group": broadcast.customer_group},
            fields=["name", "customer_name", "mobile_no"],
            limit=10000
        )
        for c in customers:
            if c.mobile_no:
                results.append((resolve_phone(c.mobile_no), c.customer_name, None, None))

    elif source == "Supplier Group":
        suppliers = frappe.get_all(
            "Supplier",
            filters={"supplier_group": broadcast.supplier_group},
            fields=["name", "supplier_name", "mobile_no"],
            limit=10000
        )
        for s in suppliers:
            if s.mobile_no:
                results.append((resolve_phone(s.mobile_no), s.supplier_name, None, None))

    elif source == "Report":
        from frappe.desk.query_report import run as run_report
        report_result = run_report({"report_name": broadcast.report_name, "filters": {}})
        col_idx = None
        for i, col in enumerate(report_result.get("columns") or []):
            col_name = col.get("fieldname") or col.get("label", "")
            if col_name == broadcast.phone_column:
                col_idx = i
                break
        if col_idx is not None:
            for row in report_result.get("result") or []:
                phone = row[col_idx] if isinstance(row, list) else row.get(broadcast.phone_column)
                if phone:
                    results.append((resolve_phone(str(phone)), "", None, None))

    return [(p, n, cp, rn) for p, n, cp, rn in results if p]


def _send_to_recipient(broadcast, phone: str, name: str,
                        custom_params_json: str) -> dict:
    from ecclesia.api import whatsapp as wa

    try:
        if broadcast.wa_template:
            tmpl = frappe.get_doc("WA Template", broadcast.wa_template)
            # Build components from template or override with custom_params
            if custom_params_json:
                import json
                params = json.loads(custom_params_json)
                components = [{"type": "body", "parameters": [
                    {"type": "text", "text": str(v)} for v in params.values()
                ]}]
            else:
                components = [{"type": "body", "parameters": [
                    {"type": "text", "text": name}
                ]}] if name else []

            return wa.send_template(phone, tmpl.template_name,
                                    tmpl.language_code, components)
        elif broadcast.custom_message:
            from ecclesia.api.notification import _render_jinja
            doc = frappe._dict({"name": name, "phone": phone})
            body = _render_jinja(broadcast.custom_message, doc)
            return wa.send_text(phone, body)
        else:
            return {"status": "failed", "error_message": "No template or message configured"}

    except Exception as e:
        frappe.log_error(str(e), f"Broadcast Send Error: {broadcast.name}")
        return {"status": "failed", "error_message": str(e)}
