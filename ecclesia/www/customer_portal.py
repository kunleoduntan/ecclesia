# Copyright (c) 2026, Ecclesia Enterprise — License: MIT
# FILE: apps/ecclesia/ecclesia/www/customer_portal.py

import frappe
from frappe.utils import today, flt


def get_context(context):

    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/customer-portal"
        raise frappe.Redirect

    context.title = "Customer Portal"

    customer = _resolve_customer(frappe.session.user)

    if not customer:
        context.boot = frappe.as_json({
            "error": "no_customer",
            "user": frappe.session.user,
            "today": today()
        })
        return

    cust = frappe.db.get_value(
        "Customer",
        customer,
        [
            "name",
            "customer_name",
            "customer_group",
            "territory",
            "default_currency",
            "default_price_list"
        ],
        as_dict=True
    )

    if not cust:
        context.boot = frappe.as_json({
            "error": "no_customer",
            "user": frappe.session.user,
            "today": today()
        })
        return

    currency = (
        cust.default_currency
        or frappe.defaults.get_global_default("currency")
        or "NGN"
    )

    open_orders = _count("Sales Order", {
        "customer": customer,
        "docstatus": 1,
        "status": ["in", ["To Deliver and Bill", "To Deliver", "To Bill"]]
    })

    unpaid_inv = _count("Sales Invoice", {
        "customer": customer,
        "docstatus": 1,
        "outstanding_amount": [">", 0]
    })

    open_issues = _count("Issue", {
        "customer": customer,
        "status": ["in", ["Open", "Replied"]]
    })

    open_quotes = _count("Quotation", {
        "party_name": customer,
        "docstatus": 1,
        "status": "Open"
    })

    total_outstanding = flt(
        frappe.db.sql("""
            SELECT COALESCE(SUM(outstanding_amount),0)
            FROM `tabSales Invoice`
            WHERE customer=%s
            AND docstatus=1
            AND outstanding_amount>0
        """, (customer,))[0][0]
    )

    recent_orders = frappe.get_all(
        "Sales Order",
        filters={
            "customer": customer,
            "docstatus": ["!=", 2]
        },
        fields=[
            "name",
            "transaction_date",
            "delivery_date",
            "grand_total",
            "currency",
            "status"
        ],
        order_by="transaction_date desc",
        limit=5
    )

    recent_invoices = frappe.get_all(
        "Sales Invoice",
        filters={
            "customer": customer,
            "docstatus": 1
        },
        fields=[
            "name",
            "posting_date",
            "due_date",
            "grand_total",
            "outstanding_amount",
            "currency",
            "status"
        ],
        order_by="posting_date desc",
        limit=5
    )

    recent_issues = frappe.get_all(
        "Issue",
        filters={"customer": customer},
        fields=[
            "name",
            "subject",
            "status",
            "priority",
            "creation"
        ],
        order_by="creation desc",
        limit=5
    )

    context.boot = frappe.as_json({

        "user": frappe.session.user,
        "today": today(),

        "customer": cust.name,
        "customer_name": cust.customer_name,
        "customer_group": cust.customer_group or "",
        "territory": cust.territory or "",

        "currency": currency,
        "price_list": cust.default_price_list or "",

        "contact": _get_contact_for_display(frappe.session.user),

        "stats": {
            "open_orders": int(open_orders),
            "unpaid_invoices": int(unpaid_inv),
            "open_issues": int(open_issues),
            "open_quotes": int(open_quotes),
            "outstanding": float(total_outstanding)
        },

        "recent_orders": [dict(r) for r in recent_orders],
        "recent_invoices": [dict(r) for r in recent_invoices],
        "recent_issues": [dict(r) for r in recent_issues]

    })


# -------------------------------------------------
# Resolve Customer ONLY using ec_portal_user
# -------------------------------------------------

def _resolve_customer(user):

    if frappe.db.has_column("Customer", "ec_portal_user"):

        name = frappe.db.get_value(
            "Customer",
            {"ec_portal_user": user},
            "name"
        )

        if name:
            return name

    return None


# -------------------------------------------------
# Contact display helper
# -------------------------------------------------

def _get_contact_for_display(user):

    c = frappe.db.get_value(
        "Contact",
        {"email_id": user},
        [
            "name",
            "first_name",
            "last_name",
            "email_id",
            "phone",
            "mobile_no"
        ],
        as_dict=True
    )

    if c:

        result = dict(c)

        phones = frappe.get_all(
            "Contact Phone",
            filters={"parent": c.name},
            fields=["phone", "is_primary_phone", "is_primary_mobile_no"],
            order_by="idx"
        )

        for p in phones:

            if p.is_primary_phone and not result.get("phone"):
                result["phone"] = p.phone

            if p.is_primary_mobile_no and not result.get("mobile_no"):
                result["mobile_no"] = p.phone

        return result

    u = frappe.db.get_value(
        "User",
        user,
        ["full_name", "email", "phone"],
        as_dict=True
    )

    if u:

        parts = (u.full_name or "").split()

        return {
            "first_name": parts[0] if parts else "",
            "last_name": " ".join(parts[1:]) if len(parts) > 1 else "",
            "email_id": user,
            "phone": u.phone or "",
            "mobile_no": ""
        }

    return {"email_id": user}


# -------------------------------------------------
# Safe counter helper
# -------------------------------------------------

def _count(doctype, filters):

    try:
        return frappe.db.count(doctype, filters=filters) or 0
    except Exception:
        return 0