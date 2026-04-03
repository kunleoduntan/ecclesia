# Copyright (c) 2026, Ecclesia Enterprise — License: MIT
# FILE: apps/ecclesia/ecclesia/www/supplier_portal.py

import frappe
from frappe.utils import today, flt


def get_context(context):

    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/supplier-portal"
        raise frappe.Redirect

    context.title = "Supplier Portal"

    supplier = _resolve_supplier(frappe.session.user)

    if not supplier:
        context.boot = frappe.as_json({
            "error": "no_supplier",
            "user": frappe.session.user,
            "today": today()
        })
        return

    sup = frappe.db.get_value(
        "Supplier", supplier,
        ["name", "supplier_name", "supplier_group", "supplier_type",
         "country", "tax_id", "default_currency", "payment_terms"],
        as_dict=True
    )

    if not sup:
        context.boot = frappe.as_json({
            "error": "no_supplier",
            "user": frappe.session.user,
            "today": today()
        })
        return

    currency = sup.default_currency or frappe.defaults.get_global_default("currency") or "NGN"

    open_pos = _count("Purchase Order", {
        "supplier": supplier,
        "docstatus": 1,
        "status": ["in", ["To Receive and Bill", "To Receive", "To Bill"]]
    })

    unpaid_bills = _count("Purchase Invoice", {
        "supplier": supplier,
        "docstatus": 1,
        "outstanding_amount": [">", 0]
    })

    open_rfqs = frappe.db.sql("""
        SELECT COUNT(DISTINCT rfq.name)
        FROM `tabRequest for Quotation` rfq
        JOIN `tabRequest for Quotation Supplier` s ON s.parent = rfq.name
        WHERE s.supplier = %s AND rfq.status = 'Open' AND rfq.docstatus = 1
    """, supplier)[0][0] or 0

    pending_qis = frappe.db.sql("""
        SELECT COUNT(qi.name)
        FROM `tabQuality Inspection` qi
        JOIN `tabPurchase Receipt` pr ON pr.name = qi.reference_name
        WHERE pr.supplier = %s AND pr.docstatus = 1
          AND qi.reference_type = 'Purchase Receipt' AND qi.status = 'Pending'
    """, supplier)[0][0] or 0

    total_payable = flt(frappe.db.sql("""
        SELECT COALESCE(SUM(outstanding_amount), 0)
        FROM `tabPurchase Invoice`
        WHERE supplier = %s AND docstatus = 1 AND outstanding_amount > 0
    """, supplier)[0][0])

    recent_pos = frappe.get_all(
        "Purchase Order",
        filters={"supplier": supplier, "docstatus": ["!=", 2]},
        fields=["name", "transaction_date", "schedule_date", "grand_total", "currency", "status"],
        order_by="transaction_date desc",
        limit=5
    )

    recent_rfqs = frappe.db.sql("""
        SELECT rfq.name, rfq.transaction_date, rfq.status, rfq.schedule_date
        FROM `tabRequest for Quotation` rfq
        JOIN `tabRequest for Quotation Supplier` s ON s.parent = rfq.name
        WHERE s.supplier = %s AND rfq.docstatus = 1
        ORDER BY rfq.transaction_date DESC LIMIT 5
    """, supplier, as_dict=True)

    context.boot = frappe.as_json({

        "user":           frappe.session.user,
        "today":          today(),

        "supplier":       sup.name,
        "supplier_name":  sup.supplier_name,
        "supplier_group": sup.supplier_group or "",
        "supplier_type":  sup.supplier_type or "",
        "country":        sup.country or "",
        "currency":       currency,
        "payment_terms":  sup.payment_terms or "",

        "contact": _get_contact(frappe.session.user),

        "stats": {
            "open_pos":      int(open_pos),
            "unpaid_bills":  int(unpaid_bills),
            "open_rfqs":     int(open_rfqs),
            "pending_qis":   int(pending_qis),
            "total_payable": float(total_payable),
        },

        "recent_pos":  [dict(r) for r in recent_pos],
        "recent_rfqs": [dict(r) for r in recent_rfqs],
    })


# ── ec_portal_user ONLY — no Contact fallback ─────────────────────────────────

def _resolve_supplier(user):
    if frappe.db.has_column("Supplier", "ec_portal_user"):
        name = frappe.db.get_value("Supplier", {"ec_portal_user": user}, "name")
        if name:
            return name
    return None


def _get_contact(user):
    c = frappe.db.get_value(
        "Contact", {"email_id": user},
        ["name", "first_name", "last_name", "email_id", "phone", "mobile_no"],
        as_dict=True
    )
    if c:
        result = dict(c)
        phones = frappe.get_all("Contact Phone",
            filters={"parent": c.name},
            fields=["phone", "is_primary_phone", "is_primary_mobile_no"],
            order_by="idx")
        for p in phones:
            if p.is_primary_phone and not result.get("phone"):
                result["phone"] = p.phone
            if p.is_primary_mobile_no and not result.get("mobile_no"):
                result["mobile_no"] = p.phone
        return result

    u = frappe.db.get_value("User", user, ["full_name", "email", "phone"], as_dict=True)
    if u:
        parts = (u.full_name or "").split()
        return {
            "first_name": parts[0] if parts else "",
            "last_name":  " ".join(parts[1:]) if len(parts) > 1 else "",
            "email_id":   user,
            "phone":      u.phone or "",
            "mobile_no":  ""
        }
    return {"email_id": user}


def _count(doctype, filters):
    try:
        return frappe.db.count(doctype, filters=filters) or 0
    except Exception:
        return 0