# -*- coding: utf-8 -*-
# =============================================================
#  Ecclesia POS — Backend API
#  Page: ecc-pos  |  Module: Ecclesia
#  DocType: ECC POS Settings (Regular, multi-terminal)
#  Child Tables: ECC POS User Permission, ECC POS Payment Mode
# =============================================================

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import nowdate, now, flt, cint
import json


# =============================================================
#  SECTION 1 — CONFIGURATION & USER RESOLUTION
# =============================================================

@frappe.whitelist()
def get_user_terminals():
    """
    Return every active ECC POS Settings terminal the current user
    is allowed to access.

    Access rules (in priority order):
      1. System Manager  → sees every active terminal
      2. Accounts Manager → sees every active terminal
      3. Everyone else   → only terminals where their user appears
                           in user_permissions with is_active = 1
    """
    user = frappe.session.user
    is_privileged = _is_privileged_user(user)

    terminals = frappe.get_all(
        "ECC POS Settings",
        filters={"is_active": 1},
        fields=[
            "name", "pos_name", "company", "branch",
            "default_warehouse", "default_pos_profile",
            "price_list", "enable_vat", "vat_rate"
        ],
        order_by="pos_name asc"
    )

    result = []
    for t in terminals:
        if is_privileged:
            t["user_row"] = _default_user_row()
            result.append(t)
        else:
            row = _get_user_row(t["name"], user)
            if row:
                t["user_row"] = row
                result.append(t)

    return {"success": True, "terminals": result, "user": user}


@frappe.whitelist()
def get_terminal_config(settings_name):
    """
    Full resolved configuration for one terminal.
    Merges ECC POS Settings with the user's permission row.
    """
    user = frappe.session.user
    is_privileged = _is_privileged_user(user)

    doc = frappe.get_doc("ECC POS Settings", settings_name)

    if not doc.is_active:
        return {"success": False, "error": "This POS terminal is inactive."}

    # Resolve user permission row
    if is_privileged:
        user_row = _default_user_row()
    else:
        user_row = _get_user_row(settings_name, user)
        if not user_row:
            return {"success": False, "error": "You do not have access to this POS terminal."}

    # Effective warehouse: user override wins, else doc default
    warehouse = user_row.get("warehouse_override") or doc.default_warehouse

    # Default customer
    default_customer = doc.default_customer
    if not default_customer:
        default_customer = _get_or_create_walkin_customer(doc.company)

    # Payment modes from child table; fall back to all enabled modes
    payment_modes = _resolve_payment_modes(doc, doc.company)

    # Company details
    company_doc = frappe.get_doc("Company", doc.company)

    return {
        "success": True,
        "config": {
            # Identity
            "settings_name": doc.name,
            "pos_name": doc.pos_name,
            "company": doc.company,
            "company_name": company_doc.company_name,
            "company_logo": company_doc.company_logo or "",
            "branch": doc.branch or "",
            # Operational
            "warehouse": warehouse,
            "default_pos_profile": doc.default_pos_profile or "",
            "naming_series": doc.naming_series or "POS-.DD.-.MM.-.YY.-",
            "default_customer": default_customer,
            "price_list": doc.price_list or "Standard Selling",
            # Tax
            "enable_vat": cint(doc.enable_vat),
            "vat_rate": flt(doc.vat_rate or 0),
            "vat_account": doc.vat_account or "",
            # Items
            "item_groups": doc.item_groups or "",
            "show_stock_qty": cint(doc.show_stock_qty),
            # Payment
            "payment_modes": payment_modes,
            # User rights (resolved)
            "can_apply_discount": cint(user_row.get("can_apply_discount", 1)),
            "can_void_sale": cint(user_row.get("can_void_sale", 0)),
            "can_view_reports": cint(user_row.get("can_view_reports", 1)),
            "max_discount_pct": flt(user_row.get("max_discount_pct", 0)),
        }
    }


# =============================================================
#  SECTION 2 — PRODUCTS WITH FULL UOM SUPPORT
# =============================================================

@frappe.whitelist()
def get_products(settings_name, search="", item_group=""):
    """
    Returns items with:
      - Real-time available stock from Bin
      - Price from Item Price (price list aware), fallback to valuation rate
      - All valid UOMs with conversion factors
      - Item group for category filtering
    """
    cfg_result = get_terminal_config(settings_name)
    if not cfg_result["success"]:
        return cfg_result

    cfg = cfg_result["config"]
    warehouse = cfg["warehouse"]
    price_list = cfg["price_list"]

    # ── Build WHERE conditions ────────────────────────────────
    conditions = ["i.disabled = 0", "i.is_sales_item = 1"]
    params = {"warehouse": warehouse, "price_list": price_list}

    if search:
        conditions.append(
            "(i.item_name LIKE %(search)s "
            " OR i.item_code LIKE %(search)s "
            " OR i.barcode LIKE %(search)s)"
        )
        params["search"] = f"%{search}%"

    if item_group and item_group != "__all__":
        conditions.append("i.item_group = %(item_group)s")
        params["item_group"] = item_group
    elif cfg["item_groups"]:
        groups = [g.strip() for g in cfg["item_groups"].split(",") if g.strip()]
        if groups:
            placeholders = ", ".join([f"%(g{i})s" for i in range(len(groups))])
            conditions.append(f"i.item_group IN ({placeholders})")
            for idx, g in enumerate(groups):
                params[f"g{idx}"] = g

    where = " AND ".join(conditions)

    # ── Main product query ───────────────────────────────────
    items = frappe.db.sql(f"""
        SELECT
            i.item_code,
            i.item_name,
            i.item_group,
            i.stock_uom,
            COALESCE(i.sales_uom, i.stock_uom)      AS default_uom,
            COALESCE(i.image, '')                    AS image,
            COALESCE(i.description, '')              AS description,
            COALESCE(bin.actual_qty, 0)              AS stock_qty,
            COALESCE(bin.reserved_qty, 0)            AS reserved_qty,
            (COALESCE(bin.actual_qty, 0)
             - COALESCE(bin.reserved_qty, 0))        AS available_qty,
            COALESCE(
                (SELECT ip.price_list_rate
                 FROM `tabItem Price` ip
                 WHERE ip.item_code = i.item_code
                   AND ip.price_list = %(price_list)s
                   AND ip.uom = COALESCE(i.sales_uom, i.stock_uom)
                   AND (ip.valid_from IS NULL OR ip.valid_from <= CURDATE())
                   AND (ip.valid_upto IS NULL OR ip.valid_upto >= CURDATE())
                 ORDER BY ip.valid_from DESC LIMIT 1),
                (SELECT ip2.price_list_rate
                 FROM `tabItem Price` ip2
                 WHERE ip2.item_code = i.item_code
                   AND ip2.price_list = %(price_list)s
                   AND (ip2.valid_from IS NULL OR ip2.valid_from <= CURDATE())
                   AND (ip2.valid_upto IS NULL OR ip2.valid_upto >= CURDATE())
                 ORDER BY ip2.valid_from DESC LIMIT 1),
                i.last_purchase_rate * 1.2,
                0
            )                                        AS price
        FROM `tabItem` i
        LEFT JOIN `tabBin` bin
            ON bin.item_code = i.item_code
           AND bin.warehouse = %(warehouse)s
        WHERE {where}
        ORDER BY i.item_name
        LIMIT 500
    """, params, as_dict=True)

    # ── Attach UOM options for each item ─────────────────────
    for item in items:
        item["uom_options"] = _get_uom_options(item["item_code"], item["stock_uom"])
        item["price"] = flt(item["price"], 2)

    # ── Categories ───────────────────────────────────────────
    cat_where = "disabled = 0 AND is_sales_item = 1"
    cat_params = {}
    if cfg["item_groups"]:
        groups = [g.strip() for g in cfg["item_groups"].split(",") if g.strip()]
        if groups:
            placeholders = ", ".join([f"%(g{i})s" for i in range(len(groups))])
            cat_where += f" AND item_group IN ({placeholders})"
            for idx, g in enumerate(groups):
                cat_params[f"g{idx}"] = g

    categories = frappe.db.sql(f"""
        SELECT DISTINCT item_group
        FROM `tabItem`
        WHERE {cat_where}
        ORDER BY item_group
    """, cat_params, as_dict=True)

    return {
        "success": True,
        "items": items,
        "categories": [c["item_group"] for c in categories],
        "count": len(items)
    }


def _get_uom_options(item_code, stock_uom):
    """
    Return all UOMs this item can be sold in, with their
    conversion factor relative to the stock UOM.
    conversion_factor = how many stock units = 1 of this UOM
    e.g. 1 Dozen = 12 Nos  →  conversion_factor = 12
    """
    rows = frappe.db.sql("""
        SELECT uom, conversion_factor
        FROM `tabUOM Conversion Detail`
        WHERE parent = %(item_code)s
          AND uom != %(stock_uom)s
        ORDER BY conversion_factor
    """, {"item_code": item_code, "stock_uom": stock_uom}, as_dict=True)

    # Always include the stock UOM itself with factor 1
    options = [{"uom": stock_uom, "conversion_factor": 1.0}]
    for r in rows:
        options.append({
            "uom": r["uom"],
            "conversion_factor": flt(r["conversion_factor"], 6)
        })
    return options


# =============================================================
#  SECTION 3 — SESSION MANAGEMENT (POS Opening/Closing Entry)
# =============================================================

@frappe.whitelist()
def get_active_session():
    """Check if current user has an open POS Opening Entry."""
    user = frappe.session.user
    session = frappe.db.sql("""
        SELECT name, pos_profile, company,
               period_start_date, posting_date
        FROM `tabPOS Opening Entry`
        WHERE user = %(user)s
          AND status = 'Open'
          AND docstatus = 1
        ORDER BY period_start_date DESC
        LIMIT 1
    """, {"user": user}, as_dict=True)

    if session:
        return {"success": True, "has_session": True, "session": session[0]}
    return {"success": True, "has_session": False}


@frappe.whitelist()
def open_session(settings_name, opening_cash=0):
    """
    Open a POS Opening Entry.
    One open session per user — returns the existing one if found.
    """
    user = frappe.session.user

    # Existing open session?
    existing = frappe.db.get_value(
        "POS Opening Entry",
        {"user": user, "status": "Open", "docstatus": 1},
        "name"
    )
    if existing:
        return {
            "success": True,
            "session": existing,
            "message": "Existing session restored.",
            "restored": True
        }

    cfg_result = get_terminal_config(settings_name)
    if not cfg_result["success"]:
        return cfg_result
    cfg = cfg_result["config"]

    if not cfg["default_pos_profile"]:
        return {
            "success": False,
            "error": (
                "No POS Profile linked to this terminal. "
                "Set 'Default POS Profile' in ECC POS Settings."
            )
        }

    opening = frappe.get_doc({
        "doctype": "POS Opening Entry",
        "pos_profile": cfg["default_pos_profile"],
        "user": user,
        "company": cfg["company"],
        "period_start_date": now(),
        "posting_date": nowdate(),
        "balance_details": []
    })

    for pm in cfg["payment_modes"]:
        opening.append("balance_details", {
            "mode_of_payment": pm["mode"],
            "opening_amount": flt(opening_cash) if pm["mode"] == "Cash" else 0
        })

    opening.insert(ignore_permissions=True)
    opening.submit()
    frappe.db.commit()

    return {
        "success": True,
        "session": opening.name,
        "message": "Session opened.",
        "restored": False
    }


@frappe.whitelist()
def close_session(session_name, closing_cash=0, actual_amounts=None):
    """
    Close the POS session by creating a POS Closing Entry.
    actual_amounts: JSON dict {mode_of_payment: actual_amount}
    """
    actual_amounts = frappe.parse_json(actual_amounts or "{}")
    opening = frappe.get_doc("POS Opening Entry", session_name)

    if opening.status != "Open":
        return {"success": False, "error": "Session is already closed."}

    # Aggregate invoices for this session
    invoices = frappe.db.sql("""
        SELECT si.name, si.grand_total,
               sip.mode_of_payment, sip.amount
        FROM `tabSales Invoice` si
        JOIN `tabSales Invoice Payment` sip ON sip.parent = si.name
        WHERE si.pos_profile = %(profile)s
          AND si.posting_date >= %(date)s
          AND si.docstatus = 1
    """, {
        "profile": opening.pos_profile,
        "date": opening.posting_date
    }, as_dict=True)

    # Sum collected per mode
    collected = {}
    for inv in invoices:
        mode = inv["mode_of_payment"]
        collected[mode] = collected.get(mode, 0) + flt(inv["amount"])

    closing = frappe.get_doc({
        "doctype": "POS Closing Entry",
        "pos_profile": opening.pos_profile,
        "user": opening.user,
        "company": opening.company,
        "pos_opening_entry": session_name,
        "period_start_date": opening.period_start_date,
        "period_end_date": now(),
        "posting_date": nowdate(),
    })

    for detail in opening.balance_details:
        mode = detail.mode_of_payment
        opening_amt = flt(detail.opening_amount)
        expected = opening_amt + collected.get(mode, 0)
        actual = flt(actual_amounts.get(mode,
            flt(closing_cash) if mode == "Cash" else collected.get(mode, 0)
        ))
        closing.append("payment_reconciliation", {
            "mode_of_payment": mode,
            "opening_amount": opening_amt,
            "expected_amount": expected,
            "closing_amount": actual,
            "difference": actual - expected
        })

    closing.insert(ignore_permissions=True)
    closing.submit()
    frappe.db.commit()

    total_invoices = len(set(i["name"] for i in invoices))
    total_sales = sum(flt(i["grand_total"]) for i in
                      frappe.db.sql("""
                          SELECT DISTINCT name, grand_total
                          FROM `tabSales Invoice`
                          WHERE pos_profile = %(profile)s
                            AND posting_date >= %(date)s
                            AND docstatus = 1
                      """, {
                          "profile": opening.pos_profile,
                          "date": opening.posting_date
                      }, as_dict=True))

    return {
        "success": True,
        "closing_entry": closing.name,
        "total_invoices": total_invoices,
        "total_sales": total_sales
    }


# =============================================================
#  SECTION 4 — SALES INVOICE WITH FULL UOM SUPPORT
# =============================================================

@frappe.whitelist()
def create_invoice(payload):
    """
    Create a submitted Sales Invoice from a POS transaction.

    Expected payload fields:
      settings_name      str
      session_name       str
      customer           str   (optional, falls back to default)
      items              list  [{item_code, item_name, qty, rate,
                                 uom, conversion_factor}]
      discount_type      str   "Percentage" | "Amount" | ""
      discount_value     float
      payment_mode       str
      paid_amount        float
    """
    payload = frappe.parse_json(payload)

    # ── Validate ─────────────────────────────────────────────
    if not payload.get("items"):
        return {"success": False, "error": "No items in transaction."}

    cfg_result = get_terminal_config(payload["settings_name"])
    if not cfg_result["success"]:
        return cfg_result
    cfg = cfg_result["config"]

    # ── Discount permission check ─────────────────────────────
    discount_value = flt(payload.get("discount_value", 0))
    discount_type  = payload.get("discount_type", "")
    if discount_value > 0:
        if not cfg["can_apply_discount"]:
            return {"success": False, "error": "You are not permitted to apply discounts."}
        max_disc = cfg["max_discount_pct"]
        if max_disc > 0 and discount_type == "Percentage" and discount_value > max_disc:
            return {
                "success": False,
                "error": f"Your maximum allowed discount is {max_disc}%."
            }

    customer    = payload.get("customer") or cfg["default_customer"]
    warehouse   = cfg["warehouse"]
    company     = cfg["company"]
    payment_mode = payload.get("payment_mode", "Cash")
    paid_amount  = flt(payload.get("paid_amount", 0))

    # ── Build Sales Invoice ──────────────────────────────────
    company_doc = frappe.get_doc("Company", company)

    invoice = frappe.get_doc({
        "doctype": "Sales Invoice",
        "naming_series": cfg["naming_series"],
        "customer": customer,
        "company": company,
        "posting_date": nowdate(),
        "posting_time": now(),
        "set_warehouse": warehouse,
        "is_pos": 1,
        "pos_profile": cfg["default_pos_profile"] or None,
        "update_stock": 1,
        "selling_price_list": cfg["price_list"],
        "currency": company_doc.default_currency or "NGN",
        "items": [],
        "taxes": [],
        "payments": []
    })

    # ── Items with UOM & conversion factor ───────────────────
    subtotal = 0
    for item in payload["items"]:
        qty               = flt(item["qty"])
        rate              = flt(item["rate"])
        uom               = item.get("uom") or item.get("stock_uom", "")
        stock_uom         = item.get("stock_uom", uom)
        conversion_factor = flt(item.get("conversion_factor", 1)) or 1.0

        # If selling UOM differs from stock UOM we must pass
        # conversion_factor so ERPNext debits the right stock qty.
        # stock_qty_deducted = qty * conversion_factor
        invoice.append("items", {
            "item_code": item["item_code"],
            "item_name": item.get("item_name", item["item_code"]),
            "qty": qty,
            "rate": rate,
            "uom": uom,
            "stock_uom": stock_uom,
            "conversion_factor": conversion_factor,
            "warehouse": warehouse,
        })
        subtotal += qty * rate

    # ── Discount ─────────────────────────────────────────────
    if discount_type == "Percentage" and discount_value > 0:
        invoice.additional_discount_percentage = discount_value
    elif discount_type == "Amount" and discount_value > 0:
        invoice.discount_amount = discount_value

    # ── VAT ──────────────────────────────────────────────────
    vat_amount = 0
    if cfg["enable_vat"] and cfg["vat_rate"] > 0:
        discount_amt = (subtotal * discount_value / 100
                        if discount_type == "Percentage"
                        else discount_value)
        taxable = subtotal - discount_amt
        vat_amount = flt(taxable * cfg["vat_rate"] / 100, 2)
        vat_account = cfg["vat_account"] or _resolve_vat_account(company)
        if vat_account:
            invoice.append("taxes", {
                "charge_type": "Actual",
                "account_head": vat_account,
                "description": f"VAT @ {cfg['vat_rate']}%",
                "tax_amount": vat_amount,
                "cost_center": company_doc.cost_center or None
            })

    # ── Payment ───────────────────────────────────────────────
    payment_account = _get_payment_account(payment_mode, company)
    if payment_account:
        invoice.append("payments", {
            "mode_of_payment": payment_mode,
            "account": payment_account,
            "amount": paid_amount
        })

    # ── Calculate, insert, submit ─────────────────────────────
    invoice.set_missing_values()
    invoice.insert(ignore_permissions=True)
    invoice.submit()
    frappe.db.commit()

    grand_total = flt(invoice.grand_total, 2)
    change      = max(0, paid_amount - grand_total)

    return {
        "success": True,
        "invoice": invoice.name,
        "grand_total": grand_total,
        "paid_amount": paid_amount,
        "change": change,
        "vat_amount": vat_amount,
        "subtotal": subtotal
    }


# =============================================================
#  SECTION 5 — CUSTOMER
# =============================================================

@frappe.whitelist()
def search_customers(search_term, company=None):
    """Fuzzy search across customer_name, mobile_no, email_id."""
    s = f"%{search_term}%"
    extra = ""
    params = [s, s, s, s]
    if company:
        extra = " AND (c.company = %s OR c.company IS NULL OR c.company = '')"
        params.append(company)

    rows = frappe.db.sql(f"""
        SELECT c.name, c.customer_name, c.mobile_no,
               c.email_id, c.customer_type
        FROM `tabCustomer` c
        WHERE c.disabled = 0
          AND (c.customer_name LIKE %s
               OR c.mobile_no    LIKE %s
               OR c.email_id     LIKE %s
               OR c.name         LIKE %s)
          {extra}
        ORDER BY c.customer_name
        LIMIT 20
    """, params, as_dict=True)

    return {"success": True, "customers": rows}


@frappe.whitelist()
def create_customer(customer_name, mobile_no="", email="", company=None):
    """Quick walk-in customer creation."""
    if not customer_name:
        return {"success": False, "error": "Customer name is required."}

    doc = frappe.get_doc({
        "doctype": "Customer",
        "customer_name": customer_name,
        "customer_type": "Individual",
        "customer_group": frappe.db.get_value(
            "Customer Group", {"is_group": 0}, "name"
        ) or "Individual",
        "territory": frappe.db.get_value(
            "Territory", {"is_group": 0}, "name"
        ) or "All Territories",
        "mobile_no": mobile_no,
        "email_id": email
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {"success": True, "customer": doc.name, "customer_name": doc.customer_name}


# =============================================================
#  SECTION 6 — REPORTS
# =============================================================

@frappe.whitelist()
def get_daily_report(settings_name, report_date=None):
    """
    Daily sales summary for a terminal:
      - Per-invoice breakdown
      - Summary totals
      - Sales by payment mode
      - Top 10 items by revenue
    """
    cfg_result = get_terminal_config(settings_name)
    if not cfg_result["success"]:
        return cfg_result
    cfg = cfg_result["config"]

    if not cfg["can_view_reports"]:
        return {"success": False, "error": "You do not have access to reports."}

    if not report_date:
        report_date = nowdate()

    base_filter = {
        "company": cfg["company"],
        "set_warehouse": cfg["warehouse"],
        "posting_date": report_date,
        "is_pos": 1,
        "docstatus": 1
    }

    # Per-invoice list
    invoices = frappe.db.sql("""
        SELECT
            si.name,
            si.customer,
            si.posting_time,
            si.grand_total,
            si.total_taxes_and_charges    AS vat_amount,
            si.discount_amount,
            (si.grand_total
             - si.total_taxes_and_charges
             + si.discount_amount)        AS subtotal,
            GROUP_CONCAT(
                sip.mode_of_payment
                ORDER BY sip.mode_of_payment
                SEPARATOR ', '
            )                             AS payment_modes
        FROM `tabSales Invoice` si
        LEFT JOIN `tabSales Invoice Payment` sip
            ON sip.parent = si.name
        WHERE si.company    = %(company)s
          AND si.set_warehouse = %(warehouse)s
          AND si.posting_date = %(date)s
          AND si.is_pos = 1
          AND si.docstatus = 1
        GROUP BY si.name
        ORDER BY si.posting_time DESC
    """, {
        "company": cfg["company"],
        "warehouse": cfg["warehouse"],
        "date": report_date
    }, as_dict=True)

    # Summary
    total_sales    = sum(flt(i["grand_total"]) for i in invoices)
    total_vat      = sum(flt(i["vat_amount"]) for i in invoices)
    total_discount = sum(flt(i["discount_amount"]) for i in invoices)
    count          = len(invoices)

    # By payment mode
    by_payment = frappe.db.sql("""
        SELECT sip.mode_of_payment, SUM(sip.amount) AS total
        FROM `tabSales Invoice Payment` sip
        JOIN `tabSales Invoice` si ON si.name = sip.parent
        WHERE si.company      = %(company)s
          AND si.set_warehouse= %(warehouse)s
          AND si.posting_date = %(date)s
          AND si.is_pos       = 1
          AND si.docstatus    = 1
        GROUP BY sip.mode_of_payment
        ORDER BY total DESC
    """, {
        "company": cfg["company"],
        "warehouse": cfg["warehouse"],
        "date": report_date
    }, as_dict=True)

    # Top items
    top_items = frappe.db.sql("""
        SELECT
            sii.item_name,
            sii.uom,
            SUM(sii.qty)    AS total_qty,
            SUM(sii.amount) AS total_amount
        FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si ON si.name = sii.parent
        WHERE si.company      = %(company)s
          AND sii.warehouse   = %(warehouse)s
          AND si.posting_date = %(date)s
          AND si.is_pos       = 1
          AND si.docstatus    = 1
        GROUP BY sii.item_code
        ORDER BY total_amount DESC
        LIMIT 10
    """, {
        "company": cfg["company"],
        "warehouse": cfg["warehouse"],
        "date": report_date
    }, as_dict=True)

    return {
        "success": True,
        "date": report_date,
        "summary": {
            "total_invoices": count,
            "total_sales": total_sales,
            "total_vat": total_vat,
            "total_discount": total_discount,
            "average_order": flt(total_sales / count, 2) if count else 0
        },
        "invoices": invoices,
        "by_payment": by_payment,
        "top_items": top_items
    }


# =============================================================
#  SECTION 7 — HELPERS (not whitelisted)
# =============================================================

def _is_privileged_user(user):
    roles = frappe.get_roles(user)
    return "System Manager" in roles or "Accounts Manager" in roles


def _get_user_row(settings_name, user):
    rows = frappe.db.sql("""
        SELECT
            warehouse_override,
            can_apply_discount,
            max_discount_pct,
            can_void_sale,
            can_view_reports,
            is_active
        FROM `tabECC POS User Permission`
        WHERE parent     = %(settings_name)s
          AND parenttype = 'ECC POS Settings'
          AND user       = %(user)s
          AND is_active  = 1
        LIMIT 1
    """, {"settings_name": settings_name, "user": user}, as_dict=True)
    return rows[0] if rows else None


def _default_user_row():
    """Privileged users get unrestricted access."""
    return {
        "warehouse_override": None,
        "can_apply_discount": 1,
        "max_discount_pct": 0,       # 0 = unlimited
        "can_void_sale": 1,
        "can_view_reports": 1,
        "is_active": 1
    }


def _resolve_payment_modes(doc, company):
    """
    Return list of {mode, account, icon} from child table.
    Falls back to all enabled Modes of Payment if child table is empty.
    """
    icons = {
        "Cash": "💵", "Card": "💳", "Credit Card": "💳",
        "Bank Transfer": "🏦", "Transfer": "🏦",
        "Cheque": "🧾", "Credit": "📝", "Online": "📱",
        "POS": "💳", "Mobile Money": "📱"
    }

    if doc.allowed_payment_modes:
        result = []
        for row in doc.allowed_payment_modes:
            acc = row.account or _get_payment_account(row.mode_of_payment, company)
            result.append({
                "mode": row.mode_of_payment,
                "account": acc or "",
                "icon": icons.get(row.mode_of_payment, "💰")
            })
        return result

    # Fallback: all enabled modes
    all_modes = frappe.db.sql("""
        SELECT name FROM `tabMode of Payment`
        WHERE enabled = 1 ORDER BY name
    """, as_dict=True)
    return [{
        "mode": m["name"],
        "account": _get_payment_account(m["name"], company) or "",
        "icon": icons.get(m["name"], "💰")
    } for m in all_modes]


def _get_payment_account(mode_of_payment, company):
    return frappe.db.get_value(
        "Mode of Payment Account",
        {"parent": mode_of_payment, "company": company},
        "default_account"
    )


def _resolve_vat_account(company):
    """Find or create a VAT Output account under Duties and Taxes."""
    account = frappe.db.get_value(
        "Account",
        {"company": company, "account_name": "VAT Output", "is_group": 0},
        "name"
    )
    if account:
        return account

    parent = frappe.db.get_value(
        "Account",
        {"company": company, "account_name": "Duties and Taxes", "is_group": 1},
        "name"
    ) or frappe.db.get_value(
        "Account",
        {"company": company, "root_type": "Liability", "is_group": 1},
        "name"
    )

    if not parent:
        return None

    try:
        vat = frappe.get_doc({
            "doctype": "Account",
            "account_name": "VAT Output",
            "parent_account": parent,
            "company": company,
            "is_group": 0,
            "account_type": "Tax"
        })
        vat.insert(ignore_permissions=True)
        frappe.db.commit()
        return vat.name
    except Exception:
        return None


def _get_or_create_walkin_customer(company):
    name = "Walk-In Customer"
    if not frappe.db.exists("Customer", name):
        frappe.get_doc({
            "doctype": "Customer",
            "customer_name": name,
            "customer_type": "Individual",
            "customer_group": frappe.db.get_value(
                "Customer Group", {"is_group": 0}, "name"
            ) or "Individual",
            "territory": frappe.db.get_value(
                "Territory", {"is_group": 0}, "name"
            ) or "All Territories",
        }).insert(ignore_permissions=True)
        frappe.db.commit()
    return name