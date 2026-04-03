# Copyright (c) 2026, Ecclesia Enterprise — License: MIT
# FILE: apps/ecclesia/ecclesia/api/customer_portal_api.py
#
# Authentication model — cookie-based, NO ERPNext user required
# ─────────────────────────────────────────────────────────────
# Customers authenticate with:  email (ec_portal_user)  +  portal_password
#
# The pattern is IDENTICAL to the working supplier portal:
#   - portal_login()  called via GET with URL params
#   - frappe.throw()  for errors (surfaces via _server_messages)
#   - Raw UUID stored as portal_session_token on Customer doctype
#   - 7-day sliding cookie  "portal_sid"
#   - Default fallback password: @@##portA (or bench set-config default_portal_password)
#
# Custom fields required on Customer doctype:
#   ec_portal_user          Data      (portal login email)
#   portal_password         Password  (bcrypt hash or plain text)
#   portal_session_token    Data      hidden=1
#   portal_session_expiry   Datetime  hidden=1

from __future__ import annotations
import uuid
import json
import frappe
import bcrypt
from frappe.utils import flt, getdate, today, nowdate, add_days
from datetime import datetime, timedelta


# ══════════════════════════════════════════════════════════════════════════════
#  PORTAL AUTHENTICATION  — ec_portal_user + portal_password
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist(allow_guest=True)
def portal_login(email, password):
    """
    Authenticate customer using ec_portal_user (email) and portal_password.
    Called via GET with URL params — the only approach that works reliably
    with Frappe allow_guest=True without CSRF complications.
    """
    if not email or not password:
        frappe.throw("Email and password are required.", frappe.AuthenticationError)

    email = (email or "").strip().lower()

    # ── Find customer by portal email ────────────────────────────────────────
    customer_data = frappe.db.get_value(
        "Customer",
        {"ec_portal_user": ["like", email]},
        ["name", "customer_name", "portal_password", "disabled"],
        as_dict=True
    )

    if not customer_data:
        import time; time.sleep(0.4)
        frappe.throw("No customer account found with that email.", frappe.AuthenticationError)

    if customer_data.disabled:
        frappe.throw("This customer account is disabled.", frappe.AuthenticationError)

    # ── Verify password ──────────────────────────────────────────────────────
    DEFAULT_PASSWORD = frappe.conf.get("default_portal_password", "@@##portA")
    stored = (customer_data.portal_password or "").strip()
    matched = False

    if not stored:
        if password == DEFAULT_PASSWORD:
            matched = True
            _migrate_password(customer_data.name, DEFAULT_PASSWORD)
    elif stored.startswith('$2b$') or stored.startswith('$2a$'):
        try:
            matched = bcrypt.checkpw(password.encode('utf-8'), stored.encode('utf-8'))
        except Exception:
            matched = False
        if not matched and password == DEFAULT_PASSWORD:
            matched = True
    else:
        if password == stored or password == DEFAULT_PASSWORD:
            matched = True
            _migrate_password(customer_data.name, password)

    if not matched:
        import time; time.sleep(0.4)
        frappe.throw("Invalid password.", frappe.AuthenticationError)

    # ── Issue session token ──────────────────────────────────────────────────
    token  = str(uuid.uuid4())
    expiry = add_days(None, 7)

    _ensure_session_columns()

    frappe.db.set_value("Customer", customer_data.name, {
        "portal_session_token":  token,
        "portal_session_expiry": expiry
    })

    expires_dt = datetime.utcnow() + timedelta(days=7)
    try:
        frappe.local.cookie_manager.set_cookie(
            "cp_sid", token,
            expires=expires_dt, httponly=True, samesite="Lax", path="/"
        )
        frappe.local.cookie_manager.set_cookie(
            "cp_user", email,
            expires=expires_dt, httponly=False, samesite="Lax", path="/"
        )
    except TypeError:
        frappe.local.cookie_manager.set_cookie("cp_sid",  token, expires_dt)
        frappe.local.cookie_manager.set_cookie("cp_user", email, expires_dt)

    frappe.db.commit()

    return {
        "success":       True,
        "customer":      customer_data.name,
        "customer_name": customer_data.customer_name,
        "message":       f"Welcome, {customer_data.customer_name}!"
    }


@frappe.whitelist(allow_guest=True)
def portal_logout():
    """Clear portal session. allow_guest=True so it works even if session is expired."""
    cp_sid  = _get_cookie("cp_sid")
    cp_user = _get_cookie("cp_user")

    if cp_sid and cp_user:
        customer_name = frappe.db.get_value(
            "Customer", {"portal_session_token": cp_sid}, "name"
        )
        if customer_name:
            frappe.db.set_value("Customer", customer_name, {
                "portal_session_token":  None,
                "portal_session_expiry": None
            })
            frappe.db.commit()

    _del_cookie("cp_sid")
    _del_cookie("cp_user")
    return {"message": "Logged out successfully"}


@frappe.whitelist(allow_guest=True)
def check_portal_session():
    """
    Check if current portal session is valid. Called on every page load.
    Returns full customer data so the frontend can bootstrap without a second call.
    """
    cp_sid = _get_cookie("cp_sid")
    if not cp_sid:
        return {"authenticated": False}

    customer = frappe.db.get_value(
        "Customer",
        {
            "portal_session_token":  cp_sid,
            "portal_session_expiry": (">", frappe.utils.now())
        },
        ["name", "customer_name", "customer_group", "territory",
         "default_currency", "default_price_list", "tax_id"],
        as_dict=True
    )

    if not customer:
        _del_cookie("cp_sid")
        _del_cookie("cp_user")
        return {"authenticated": False}

    return {
        "authenticated":   True,
        "customer":        customer.name,
        "customer_name":   customer.customer_name,
        "customer_group":  customer.customer_group,
        "territory":       customer.territory,
        "currency":        customer.default_currency or frappe.defaults.get_global_default("currency") or "NGN",
        "price_list":      customer.default_price_list or "",
        "tax_id":          customer.tax_id or "",
    }


@frappe.whitelist(allow_guest=True)
def set_portal_password(new_password):
    """Allow customer to change their portal password."""
    customer = get_current_customer()
    if not new_password or len(new_password) < 6:
        frappe.throw("Password must be at least 6 characters long")
    salt   = bcrypt.gensalt()
    hashed = bcrypt.hashpw(new_password.encode('utf-8'), salt).decode('utf-8')
    frappe.db.set_value("Customer", customer, "portal_password", hashed)
    frappe.db.commit()
    return {"message": "Password updated successfully"}


# ── Session helpers ───────────────────────────────────────────────────────────

def _get_cookie(name):
    try:
        req = getattr(frappe, 'request', None) or getattr(frappe.local, 'request', None)
        if req is None:
            return ""
        return (getattr(req, 'cookies', {}) or {}).get(name, "").strip()
    except Exception:
        return ""


def _del_cookie(name):
    try:
        frappe.local.cookie_manager.delete_cookie(name, path="/")
    except Exception:
        pass


def _migrate_password(customer_name, plain_password):
    try:
        salt   = bcrypt.gensalt()
        hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt).decode('utf-8')
        frappe.db.set_value("Customer", customer_name, "portal_password", hashed)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(f"Password migration failed: {e}", "Customer Portal")


def _ensure_session_columns():
    if not frappe.db.has_column("Customer", "portal_session_token"):
        frappe.db.sql("ALTER TABLE `tabCustomer` ADD COLUMN `portal_session_token` VARCHAR(140)")
        frappe.db.sql("ALTER TABLE `tabCustomer` ADD COLUMN `portal_session_expiry` DATETIME")
        frappe.db.commit()


def get_current_customer():
    """
    Resolve current customer from portal_sid cookie.
    Raises AuthenticationError if not authenticated.
    """
    cp_sid = _get_cookie("cp_sid")
    if not cp_sid:
        frappe.throw("Please log in to access the portal.", frappe.AuthenticationError)

    customer = frappe.db.get_value(
        "Customer",
        {
            "portal_session_token":  cp_sid,
            "portal_session_expiry": (">", frappe.utils.now())
        },
        "name"
    )

    if not customer:
        frappe.throw("Session expired. Please log in again.", frappe.AuthenticationError)

    return customer


def get_current_customer_details():
    """Return full customer dict from session, or None."""
    cp_sid = _get_cookie("cp_sid")
    if not cp_sid:
        return None

    return frappe.db.get_value(
        "Customer",
        {
            "portal_session_token":  cp_sid,
            "portal_session_expiry": (">", frappe.utils.now())
        },
        ["name", "customer_name", "customer_group", "territory",
         "default_currency", "default_price_list", "tax_id"],
        as_dict=True
    )


# ══════════════════════════════════════════════════════════════════════════════
#  PORTAL BOOT DATA
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist(allow_guest=True)
def get_portal_boot():
    """Return everything the dashboard needs in one call."""
    customer_obj = get_current_customer_details()
    if not customer_obj:
        frappe.local.response.http_status_code = 401
        return {"error": "no_session"}

    customer = customer_obj.name
    cp_user  = _get_cookie("cp_user")

    stats = {
        "open_orders": frappe.db.count("Sales Order", {
            "customer": customer, "docstatus": 1,
            "status": ["in", ["To Deliver and Bill", "To Deliver", "To Bill"]]
        }),
        "unpaid_invoices": frappe.db.count("Sales Invoice", {
            "customer": customer, "docstatus": 1,
            "outstanding_amount": [">", 0]
        }),
        "open_quotes": frappe.db.count("Quotation", {
            "party_name": customer, "quotation_to": "Customer",
            "docstatus": 1, "status": "Open"
        }),
        "open_issues": frappe.db.count("Issue", {
            "customer": customer,
            "status": ["in", ["Open", "Replied"]]
        }),
        "outstanding": frappe.db.sql("""
            SELECT COALESCE(SUM(outstanding_amount), 0)
            FROM `tabSales Invoice`
            WHERE customer = %s AND docstatus = 1 AND outstanding_amount > 0
        """, customer)[0][0]
    }

    recent_orders = frappe.get_all("Sales Order",
        filters={"customer": customer, "docstatus": 1},
        fields=["name", "transaction_date", "grand_total", "status", "currency"],
        order_by="transaction_date desc", limit=5)

    recent_invoices = frappe.get_all("Sales Invoice",
        filters={"customer": customer, "docstatus": 1},
        fields=["name", "posting_date", "grand_total", "outstanding_amount", "status", "currency"],
        order_by="posting_date desc", limit=5)

    recent_issues = frappe.get_all("Issue",
        filters={"customer": customer},
        fields=["name", "subject", "priority", "status", "opening_date"],
        order_by="opening_date desc", limit=5)

    contact = frappe.db.get_value(
        "Contact", {"email_id": cp_user},
        ["first_name", "last_name", "email_id", "phone", "mobile_no"],
        as_dict=True
    ) if cp_user else None

    return {
        "customer":       customer,
        "customer_name":  customer_obj.customer_name,
        "customer_group": customer_obj.customer_group,
        "territory":      customer_obj.territory,
        "currency":       customer_obj.default_currency or frappe.defaults.get_global_default("currency") or "NGN",
        "price_list":     customer_obj.default_price_list or "",
        "tax_id":         customer_obj.tax_id or "",
        "stats":          stats,
        "recent_orders":  [dict(r) for r in recent_orders],
        "recent_invoices":[dict(r) for r in recent_invoices],
        "recent_issues":  [dict(r) for r in recent_issues],
        "contact":        dict(contact) if contact else {},
        "today":          str(today())
    }


# ══════════════════════════════════════════════════════════════════════════════
#  QUOTATIONS
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist(allow_guest=True)
def get_quotations(page=1, page_size=20, status=None):
    customer = get_current_customer()
    start = (int(page) - 1) * int(page_size)
    filters = {"party_name": customer, "quotation_to": "Customer", "docstatus": ["!=", 2]}
    if status and status not in ("", "All"):
        filters["status"] = status
    rows = frappe.get_all("Quotation",
        filters=filters,
        fields=["name", "transaction_date", "valid_till", "grand_total", "currency", "status"],
        order_by="transaction_date desc",
        limit=int(page_size), start=start)
    total = frappe.db.count("Quotation", filters)
    return {"data": [dict(r) for r in rows], "total": total}


@frappe.whitelist(allow_guest=True)
def get_quotation_detail(name):
    customer = get_current_customer()
    doc = frappe.get_doc("Quotation", name)
    if doc.party_name != customer:
        frappe.throw("Not authorised", frappe.PermissionError)
    items = [{"item_code": i.item_code, "item_name": i.item_name,
              "qty": i.qty, "uom": i.uom, "rate": i.rate, "amount": i.amount}
             for i in doc.items]
    return {
        "name": doc.name, "status": doc.status,
        "transaction_date": str(doc.transaction_date),
        "valid_till": str(doc.valid_till) if doc.valid_till else None,
        "grand_total": doc.grand_total, "currency": doc.currency,
        "total_taxes_and_charges": flt(doc.total_taxes_and_charges),
        "items": items, "terms": doc.terms or "",
    }


# ══════════════════════════════════════════════════════════════════════════════
#  SALES ORDERS
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist(allow_guest=True)
def get_orders(status=None, page=1, page_size=20):
    customer = get_current_customer()
    filters = {"customer": customer, "docstatus": ["!=", 2]}
    if status and status != "All":
        filters["status"] = status
    start = (int(page) - 1) * int(page_size)
    rows = frappe.get_all("Sales Order",
        filters=filters,
        fields=["name", "transaction_date", "delivery_date",
                "grand_total", "currency", "status", "per_delivered", "per_billed"],
        order_by="transaction_date desc",
        limit=int(page_size), start=start)
    total = frappe.db.count("Sales Order", filters)
    return {"data": [dict(r) for r in rows], "total": total}


@frappe.whitelist(allow_guest=True)
def get_order_detail(name):
    customer = get_current_customer()
    doc = frappe.get_doc("Sales Order", name)
    if doc.customer != customer:
        frappe.throw("Not authorised", frappe.PermissionError)
    items = [{"item_code": i.item_code, "item_name": i.item_name,
              "qty": i.qty, "delivered_qty": i.delivered_qty,
              "uom": i.uom, "rate": i.rate, "amount": i.amount}
             for i in doc.items]
    dn_names = list({d.parent for d in frappe.get_all(
        "Delivery Note Item",
        filters={"against_sales_order": name, "docstatus": 1},
        fields=["parent"])})
    return {
        "name": doc.name, "status": doc.status,
        "transaction_date": str(doc.transaction_date),
        "delivery_date": str(doc.delivery_date) if doc.delivery_date else None,
        "grand_total": doc.grand_total, "currency": doc.currency,
        "per_delivered": doc.per_delivered, "per_billed": doc.per_billed,
        "items": items, "delivery_notes": dn_names,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  PLACE NEW SALES ORDER (from portal)
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist(allow_guest=True)
def get_items_for_order(search=None, page=1, page_size=20):
    """
    Return items the customer can order with full UOM list and best selling price.

    Price strategy: return the HIGHEST price_list_rate across all active selling
    price lists. This ensures the customer always sees a real price and the company
    can discount later if needed. Falls back to the customer's assigned price list,
    then any selling price list, then 0.
    """
    customer = get_current_customer()
    start = (int(page) - 1) * int(page_size)

    where = "i.disabled = 0 AND i.is_sales_item = 1 AND (i.has_variants = 0 OR i.has_variants IS NULL)"
    vals  = []

    if search and search.strip():
        where += " AND (i.item_code LIKE %s OR i.item_name LIKE %s)"
        s = f"%{search.strip()}%"
        vals += [s, s]

    items = frappe.db.sql(f"""
        SELECT
            i.name       AS item_code,
            i.item_name,
            i.item_group,
            i.stock_uom  AS uom,
            i.description
        FROM `tabItem` i
        WHERE {where}
        ORDER BY i.item_name
        LIMIT %s OFFSET %s
    """, vals + [int(page_size), start], as_dict=True)

    total = frappe.db.sql(f"""
        SELECT COUNT(*) FROM `tabItem` i WHERE {where}
    """, vals)[0][0]

    # Customer default currency
    cust_data = frappe.db.get_value(
        "Customer", customer,
        ["default_price_list", "default_currency"],
        as_dict=True
    ) or {}
    default_currency = cust_data.get("default_currency") or                        frappe.db.get_single_value("Global Defaults", "default_currency") or "NGN"
    customer_price_list = cust_data.get("default_price_list") or ""

    for item in items:
        item_code = item.item_code

        # ── UOM list: stock_uom always first, then sales UOMs from Item row ──
        stock_uom = item.uom or "Nos"
        uom_rows = frappe.db.sql("""
            SELECT ucd.uom, ucd.conversion_factor
            FROM `tabUOM Conversion Detail` ucd
            WHERE ucd.parent = %s
            ORDER BY ucd.idx
        """, item_code, as_dict=True)

        seen = set()
        uoms = []
        # Always add stock UOM first
        seen.add(stock_uom)
        uoms.append({"uom": stock_uom, "conversion_factor": 1.0})
        for u in uom_rows:
            if u.uom and u.uom not in seen:
                seen.add(u.uom)
                uoms.append({"uom": u.uom, "conversion_factor": flt(u.conversion_factor) or 1.0})

        item["uoms"] = uoms

        # ── Best price: highest rate across all selling price lists ──────────
        # Prefer customer's price list; if 0 or absent, show highest available
        all_prices = frappe.db.sql("""
            SELECT ip.price_list_rate, ip.currency, ip.price_list,
                   CASE WHEN ip.price_list = %s THEN 1 ELSE 0 END AS is_customer_pl
            FROM `tabItem Price` ip
            JOIN `tabPrice List` pl ON pl.name = ip.price_list
            WHERE ip.item_code = %s
              AND pl.selling = 1
              AND pl.enabled = 1
              AND (ip.valid_from IS NULL OR ip.valid_from <= CURDATE())
              AND (ip.valid_upto IS NULL OR ip.valid_upto >= CURDATE())
            ORDER BY is_customer_pl DESC, ip.price_list_rate DESC
            LIMIT 10
        """, (customer_price_list, item_code), as_dict=True)

        best_rate     = 0
        best_currency = default_currency
        best_pl       = ""

        if all_prices:
            # Pick customer price list rate if > 0, otherwise highest available
            for p in all_prices:
                r = flt(p.price_list_rate)
                if p.is_customer_pl and r > 0:
                    best_rate     = r
                    best_currency = p.currency or default_currency
                    best_pl       = p.price_list
                    break
            if best_rate == 0:
                # Fallback: highest rate from any selling price list
                best_rate     = flt(all_prices[0].price_list_rate)
                best_currency = all_prices[0].currency or default_currency
                best_pl       = all_prices[0].price_list

        item["rate"]       = best_rate
        item["currency"]   = best_currency
        item["price_list"] = best_pl

        # Strip HTML from description
        if item.get("description"):
            import re as _re
            item["description"] = _re.sub(r'<[^>]+>', '', item["description"]).strip()[:120]

    return {
        "data":       [dict(i) for i in items],
        "total":      int(total or 0),
        "price_list": customer_price_list,
    }


@frappe.whitelist(allow_guest=True)
def get_item_price(item_code, uom=None):
    """
    Return best selling price for an item + optional UOM.
    Same strategy: customer price list first, then highest available.
    """
    customer  = get_current_customer()
    cust_data = frappe.db.get_value(
        "Customer", customer,
        ["default_price_list", "default_currency"],
        as_dict=True
    ) or {}
    customer_price_list = cust_data.get("default_price_list") or ""
    default_currency    = cust_data.get("default_currency") or                           frappe.db.get_single_value("Global Defaults", "default_currency") or "NGN"

    # UOM conversion factor
    conversion = 1.0
    if uom:
        cf = frappe.db.get_value("UOM Conversion Detail",
            {"parent": item_code, "uom": uom}, "conversion_factor")
        if cf:
            conversion = flt(cf)

    # Fetch prices: customer price list first, then highest
    uom_filter = f"AND ip.uom = {frappe.db.escape(uom)}" if uom else ""
    prices = frappe.db.sql(f"""
        SELECT ip.price_list_rate, ip.currency, ip.price_list,
               CASE WHEN ip.price_list = %s THEN 1 ELSE 0 END AS is_customer_pl
        FROM `tabItem Price` ip
        JOIN `tabPrice List` pl ON pl.name = ip.price_list
        WHERE ip.item_code = %s
          AND pl.selling = 1
          AND pl.enabled = 1
          {uom_filter}
          AND (ip.valid_from IS NULL OR ip.valid_from <= CURDATE())
          AND (ip.valid_upto IS NULL OR ip.valid_upto >= CURDATE())
        ORDER BY is_customer_pl DESC, ip.price_list_rate DESC
        LIMIT 5
    """, (customer_price_list, item_code), as_dict=True)

    # Also try without UOM filter if no result
    if not prices and uom:
        prices = frappe.db.sql("""
            SELECT ip.price_list_rate, ip.currency, ip.price_list,
                   CASE WHEN ip.price_list = %s THEN 1 ELSE 0 END AS is_customer_pl
            FROM `tabItem Price` ip
            JOIN `tabPrice List` pl ON pl.name = ip.price_list
            WHERE ip.item_code = %s
              AND pl.selling = 1 AND pl.enabled = 1
              AND (ip.valid_from IS NULL OR ip.valid_from <= CURDATE())
              AND (ip.valid_upto IS NULL OR ip.valid_upto >= CURDATE())
            ORDER BY is_customer_pl DESC, ip.price_list_rate DESC
            LIMIT 5
        """, (customer_price_list, item_code), as_dict=True)

    rate     = 0
    currency = default_currency
    if prices:
        for p in prices:
            if p.is_customer_pl and flt(p.price_list_rate) > 0:
                rate = flt(p.price_list_rate); currency = p.currency or default_currency; break
        if rate == 0:
            rate = flt(prices[0].price_list_rate); currency = prices[0].currency or default_currency

    return {
        "rate":       rate,
        "currency":   currency,
        "conversion": conversion,
    }


@frappe.whitelist(allow_guest=True)
def get_order_defaults():
    """
    Return defaults needed to pre-fill a new sales order form:
    company, taxes template, payment terms, warehouses, currencies, addresses.
    """
    customer = get_current_customer()

    # Company
    company = frappe.defaults.get_global_default("company") or ""

    # Customer details
    cust = frappe.db.get_value("Customer", customer,
        ["customer_name", "default_currency", "default_price_list",
         "payment_terms", "territory", "customer_group"],
        as_dict=True) or {}

    # Default selling price list
    price_list = cust.get("default_price_list") or                  frappe.db.get_single_value("Selling Settings", "selling_price_list") or                  "Standard Selling"

    # Tax templates for this company
    taxes = frappe.get_all("Sales Taxes and Charges Template",
        filters={"company": company, "disabled": 0},
        fields=["name", "title"],
        order_by="is_default desc, name")

    # Default tax template
    default_tax = frappe.db.get_value(
        "Sales Taxes and Charges Template",
        {"company": company, "is_default": 1},
        "name"
    )

    # Payment terms
    payment_terms = frappe.get_all("Payment Terms Template",
        fields=["name"], order_by="name")

    # Warehouses
    warehouses = frappe.get_all("Warehouse",
        filters={"company": company, "disabled": 0, "is_group": 0},
        fields=["name"],
        order_by="name")

    # Customer shipping addresses
    addresses = _get_customer_addresses(customer)

    # Currency
    currency = cust.get("default_currency") or                frappe.db.get_single_value("Global Defaults", "default_currency") or "NGN"

    return {
        "company":       company,
        "customer":      customer,
        "customer_name": cust.get("customer_name", ""),
        "currency":      currency,
        "price_list":    price_list,
        "payment_terms": cust.get("payment_terms", ""),
        "territory":     cust.get("territory", ""),
        "default_tax":   default_tax or (taxes[0].name if taxes else ""),
        "taxes":         [dict(t) for t in taxes],
        "payment_terms_list": [dict(p) for p in payment_terms],
        "warehouses":    [w.name for w in warehouses],
        "addresses":     addresses,
    }


def _get_customer_addresses(customer):
    """Return customer's shipping addresses for delivery address dropdown."""
    links = frappe.get_all("Dynamic Link",
        filters={"link_doctype": "Customer", "link_name": customer, "parenttype": "Address"},
        fields=["parent"])
    result = []
    for l in links:
        a = frappe.db.get_value("Address", l.parent,
            ["name", "address_title", "address_type", "address_line1",
             "address_line2", "city", "state", "country", "pincode",
             "is_primary_address", "is_shipping_address"],
            as_dict=True)
        if a:
            result.append(dict(a))
    return result


@frappe.whitelist(allow_guest=True)
def place_order(order_data):
    """
    Create a submitted Sales Order from portal data.

    order_data (JSON string or dict):
      {
        transaction_date, delivery_date,
        po_no, po_date,
        payment_terms_template, taxes_and_charges,
        shipping_address_name, notes,
        items: [
          { item_code, item_name, qty, uom, rate, warehouse, description }
        ]
      }
    """
    customer = get_current_customer()

    if isinstance(order_data, str):
        order_data = json.loads(order_data)

    if not order_data:
        frappe.throw("Order data is required")

    items = order_data.get("items") or []
    if not items:
        frappe.throw("At least one item is required")

    # Validate items
    so_items = []
    for idx, item in enumerate(items):
        item_code = (item.get("item_code") or "").strip()
        if not item_code:
            frappe.throw(f"Item code is required on row {idx + 1}")
        if not frappe.db.exists("Item", item_code):
            frappe.throw(f"Item '{item_code}' does not exist")
        qty = flt(item.get("qty") or 0)
        if qty <= 0:
            frappe.throw(f"Quantity must be greater than 0 for item '{item_code}'")
        rate = flt(item.get("rate") or 0)

        so_items.append({
            "item_code":   item_code,
            "item_name":   item.get("item_name") or frappe.db.get_value("Item", item_code, "item_name"),
            "qty":         qty,
            "uom":         item.get("uom") or frappe.db.get_value("Item", item_code, "stock_uom") or "Nos",
            "rate":        rate,
            "warehouse":   item.get("warehouse") or "",
            "description": item.get("description") or "",
        })

    # Get company and customer defaults
    company  = frappe.defaults.get_global_default("company")
    cust_doc = frappe.get_doc("Customer", customer)

    price_list = cust_doc.default_price_list or                  frappe.db.get_single_value("Selling Settings", "selling_price_list") or                  "Standard Selling"
    currency   = cust_doc.default_currency or                  frappe.db.get_single_value("Global Defaults", "default_currency") or "NGN"

    # Build SO doc
    so = frappe.get_doc({
        "doctype":                  "Sales Order",
        "customer":                 customer,
        "customer_name":            cust_doc.customer_name,
        "company":                  company,
        "transaction_date":         order_data.get("transaction_date") or today(),
        "delivery_date":            order_data.get("delivery_date") or None,
        "po_no":                    order_data.get("po_no") or "",
        "po_date":                  order_data.get("po_date") or None,
        "currency":                 currency,
        "selling_price_list":       price_list,
        "payment_terms_template":   order_data.get("payment_terms_template") or cust_doc.payment_terms or None,
        "taxes_and_charges":        order_data.get("taxes_and_charges") or None,
        "shipping_address_name":    order_data.get("shipping_address_name") or None,
        "territory":                cust_doc.territory or None,
        "order_type":               "Sales",
        "status":                   "Draft",
        "items":                    so_items,
        "notes":                    order_data.get("notes") or "",
    })

    so.flags.ignore_permissions = True
    so.flags.ignore_validate_update_after_submit = True

    # Insert as draft first (triggers on_update — our hook guards against None prev)
    so.insert()

    # Immediately submit so it enters the ERPNext workflow
    so.flags.ignore_permissions = True
    so.submit()
    frappe.db.commit()

    return {
        "name":             so.name,
        "status":           so.status,
        "grand_total":      so.grand_total,
        "currency":         so.currency,
        "transaction_date": str(so.transaction_date),
        "delivery_date":    str(so.delivery_date) if so.delivery_date else None,
        "message":          f"Order {so.name} placed successfully!"
    }



# ══════════════════════════════════════════════════════════════════════════════
#  DELIVERIES
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist(allow_guest=True)
def get_deliveries(page=1, page_size=20):
    customer = get_current_customer()
    start = (int(page) - 1) * int(page_size)
    rows = frappe.get_all("Delivery Note",
        filters={"customer": customer, "docstatus": 1},
        fields=["name", "posting_date", "grand_total", "currency", "status", "lr_no", "lr_date"],
        order_by="posting_date desc",
        limit=int(page_size), start=start)
    total = frappe.db.count("Delivery Note", {"customer": customer, "docstatus": 1})
    return {"data": [dict(r) for r in rows], "total": total}


# ══════════════════════════════════════════════════════════════════════════════
#  INVOICES & PAYMENTS
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist(allow_guest=True)
def get_invoices(status=None, page=1, page_size=20):
    customer = get_current_customer()
    filters = {"customer": customer, "docstatus": 1}
    if status == "Unpaid":
        filters["outstanding_amount"] = [">", 0]
    elif status == "Paid":
        filters["outstanding_amount"] = ["<=", 0]
    elif status == "Overdue":
        filters["outstanding_amount"] = [">", 0]
        filters["due_date"] = ["<", today()]
    start = (int(page) - 1) * int(page_size)
    rows = frappe.get_all("Sales Invoice",
        filters=filters,
        fields=["name", "posting_date", "due_date", "grand_total",
                "outstanding_amount", "currency", "status", "is_return"],
        order_by="posting_date desc",
        limit=int(page_size), start=start)
    total = frappe.db.count("Sales Invoice", filters)
    today_d = getdate(today())
    for r in rows:
        r["is_overdue"] = (flt(r.outstanding_amount) > 0 and
                           r.due_date and getdate(r.due_date) < today_d)
    return {"data": [dict(r) for r in rows], "total": total}


@frappe.whitelist(allow_guest=True)
def get_invoice_detail(name):
    customer = get_current_customer()
    doc = frappe.get_doc("Sales Invoice", name)
    if doc.customer != customer:
        frappe.throw("Not authorised", frappe.PermissionError)
    items = [{"item_code": i.item_code, "item_name": i.item_name,
              "qty": i.qty, "uom": i.uom, "rate": i.rate,
              "amount": i.amount, "description": i.description or ""}
             for i in doc.items]
    payments = frappe.get_all("Payment Entry Reference",
        filters={"reference_doctype": "Sales Invoice", "reference_name": name},
        fields=["parent", "allocated_amount"])
    return {
        "name": doc.name, "status": doc.status,
        "posting_date": str(doc.posting_date),
        "due_date": str(doc.due_date) if doc.due_date else None,
        "grand_total": doc.grand_total,
        "outstanding_amount": doc.outstanding_amount,
        "currency": doc.currency,
        "total_taxes_and_charges": flt(doc.total_taxes_and_charges),
        "items": items,
        "payments": [dict(p) for p in payments],
        "payment_terms": doc.payment_terms_template or "",
        "remarks": doc.remarks or "",
    }


@frappe.whitelist(allow_guest=True)
def get_payment_history(page=1, page_size=20):
    customer = get_current_customer()
    start = (int(page) - 1) * int(page_size)
    rows = frappe.get_all("Payment Entry",
        filters={"party_type": "Customer", "party": customer, "docstatus": 1},
        fields=["name", "posting_date", "paid_amount",
                "paid_from_account_currency as currency",
                "mode_of_payment", "reference_no", "remarks"],
        order_by="posting_date desc",
        limit=int(page_size), start=start)
    total = frappe.db.count("Payment Entry",
        {"party_type": "Customer", "party": customer, "docstatus": 1})
    return {"data": [dict(r) for r in rows], "total": total}


@frappe.whitelist(allow_guest=True)
def get_outstanding_summary():
    customer = get_current_customer()
    today_d = getdate(today())
    rows = frappe.db.sql("""
        SELECT name, posting_date, due_date, grand_total,
               outstanding_amount, currency, status
        FROM `tabSales Invoice`
        WHERE customer = %s AND docstatus = 1 AND outstanding_amount > 0
        ORDER BY due_date ASC
    """, customer, as_dict=True)
    total_outstanding = sum(flt(r.outstanding_amount) for r in rows)
    overdue = [r for r in rows if r.due_date and getdate(r.due_date) < today_d]
    total_overdue = sum(flt(r.outstanding_amount) for r in overdue)
    return {
        "total_outstanding": total_outstanding,
        "total_overdue": total_overdue,
        "invoices": [dict(r) for r in rows],
    }


# ══════════════════════════════════════════════════════════════════════════════
#  TRANSACTION LEDGER
#  Shows every debit/credit entry for the customer:
#    Sales Invoices  → Debit  (amount customer owes)
#    Credit Notes    → Credit (return/refund reducing balance)
#    Payment Entries → Credit (cash received)
#    Journal Entries → Debit or Credit depending on party entry direction
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist(allow_guest=True)
def get_ledger(from_date=None, to_date=None, page=1, page_size=50):
    """
    Return a chronological debit/credit ledger for the customer.

    Entry types included:
      SI   Sales Invoice        → Debit  (raises balance due)
      SINV Credit Note (return) → Credit (reduces balance due)
      PE   Payment Entry        → Credit (payment received)
      JV   Journal Entry        → Debit or Credit per account direction
    """
    customer = get_current_customer()
    page, page_size = int(page), int(page_size)

    fd = from_date or add_days(today(), -365)
    td = to_date   or today()

    entries = []

    # ── Sales Invoices (regular) ──────────────────────────────────────────────
    invoices = frappe.db.sql("""
        SELECT
            name            AS ref_no,
            posting_date    AS trx_date,
            'Sales Invoice' AS doc_type,
            'SI'            AS doc_abbr,
            grand_total     AS debit,
            0               AS credit,
            outstanding_amount,
            currency,
            status,
            0               AS is_return
        FROM `tabSales Invoice`
        WHERE customer  = %(customer)s
          AND docstatus = 1
          AND is_return = 0
          AND posting_date BETWEEN %(fd)s AND %(td)s
    """, {"customer": customer, "fd": fd, "td": td}, as_dict=True)

    # ── Credit Notes (is_return = 1 on Sales Invoice) ────────────────────────
    credit_notes = frappe.db.sql("""
        SELECT
            name            AS ref_no,
            posting_date    AS trx_date,
            'Credit Note'   AS doc_type,
            'CN'            AS doc_abbr,
            0               AS debit,
            ABS(grand_total) AS credit,
            0               AS outstanding_amount,
            currency,
            status,
            1               AS is_return
        FROM `tabSales Invoice`
        WHERE customer  = %(customer)s
          AND docstatus = 1
          AND is_return = 1
          AND posting_date BETWEEN %(fd)s AND %(td)s
    """, {"customer": customer, "fd": fd, "td": td}, as_dict=True)

    # ── Payment Entries ───────────────────────────────────────────────────────
    payments = frappe.db.sql("""
        SELECT
            name                        AS ref_no,
            posting_date                AS trx_date,
            'Payment'                   AS doc_type,
            'PMT'                       AS doc_abbr,
            0                           AS debit,
            paid_amount                 AS credit,
            0                           AS outstanding_amount,
            paid_from_account_currency  AS currency,
            'Submitted'                 AS status,
            reference_no                AS ext_ref,
            mode_of_payment
        FROM `tabPayment Entry`
        WHERE party_type = 'Customer'
          AND party      = %(customer)s
          AND docstatus  = 1
          AND payment_type IN ('Receive', 'Pay')
          AND posting_date BETWEEN %(fd)s AND %(td)s
    """, {"customer": customer, "fd": fd, "td": td}, as_dict=True)

    # ── Journal Entries (party-level) ─────────────────────────────────────────
    # Each JE account row that references this customer contributes either
    # a debit (debit_in_account_currency) or credit (credit_in_account_currency)
    je_rows = frappe.db.sql("""
        SELECT
            jea.parent                          AS ref_no,
            je.posting_date                     AS trx_date,
            'Journal Entry'                     AS doc_type,
            'JV'                                AS doc_abbr,
            jea.debit_in_account_currency       AS debit,
            jea.credit_in_account_currency      AS credit,
            0                                   AS outstanding_amount,
            jea.account_currency                AS currency,
            je.voucher_type                     AS status,
            je.user_remark                      AS remarks
        FROM `tabJournal Entry Account` jea
        JOIN `tabJournal Entry` je ON je.name = jea.parent
        WHERE jea.party_type = 'Customer'
          AND jea.party      = %(customer)s
          AND je.docstatus   = 1
          AND je.posting_date BETWEEN %(fd)s AND %(td)s
    """, {"customer": customer, "fd": fd, "td": td}, as_dict=True)

    # ── Merge and sort ────────────────────────────────────────────────────────
    all_entries = (list(invoices) + list(credit_notes) +
                   list(payments) + list(je_rows))

    all_entries.sort(key=lambda x: (str(x.get("trx_date") or ""), x.get("ref_no") or ""))

    # ── Running balance (debit positive = customer owes us) ───────────────────
    running = flt(0)
    for e in all_entries:
        e["debit"]  = flt(e.get("debit", 0))
        e["credit"] = flt(e.get("credit", 0))
        running    += e["debit"] - e["credit"]
        e["balance"] = running
        # Serialise dates
        if hasattr(e.get("trx_date"), "strftime"):
            e["trx_date"] = str(e["trx_date"])

    # ── Totals ────────────────────────────────────────────────────────────────
    total_debit  = sum(flt(e["debit"])  for e in all_entries)
    total_credit = sum(flt(e["credit"]) for e in all_entries)

    # ── Paginate AFTER computing running balance ──────────────────────────────
    start = (page - 1) * page_size
    page_data = all_entries[start: start + page_size]

    return {
        "data":          page_data,
        "total":         len(all_entries),
        "total_debit":   total_debit,
        "total_credit":  total_credit,
        "closing_balance": running,
        "from_date":     fd,
        "to_date":       td,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  SUPPORT / ISSUES
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist(allow_guest=True)
def get_issues(status=None, page=1, page_size=20):
    customer = get_current_customer()
    filters = {"customer": customer}
    if status and status != "All":
        filters["status"] = status
    start = (int(page) - 1) * int(page_size)
    rows = frappe.get_all("Issue",
        filters=filters,
        fields=["name", "subject", "status", "priority",
                "opening_date", "resolution_date", "issue_type"],
        order_by="opening_date desc",
        limit=int(page_size), start=start)
    total = frappe.db.count("Issue", filters)
    return {"data": [dict(r) for r in rows], "total": total}


@frappe.whitelist(allow_guest=True)
def get_issue_detail(name):
    customer = get_current_customer()
    doc = frappe.get_doc("Issue", name)
    if doc.customer != customer:
        frappe.throw("Not authorised", frappe.PermissionError)
    comms = frappe.get_all("Communication",
        filters={"reference_doctype": "Issue", "reference_name": name},
        fields=["name", "sender", "sender_full_name", "subject",
                "content", "sent_or_received", "communication_date"],
        order_by="communication_date asc")
    return {
        "name": doc.name, "subject": doc.subject,
        "status": doc.status, "priority": doc.priority,
        "issue_type": doc.issue_type,
        "opening_date": str(doc.opening_date),
        "resolution_date": str(doc.resolution_date) if doc.resolution_date else None,
        "description": doc.description,
        "communications": [dict(c) for c in comms],
    }


@frappe.whitelist(allow_guest=True)
def create_issue(subject, description, priority="Medium", issue_type=None):
    customer = get_current_customer()
    if not (subject or "").strip():
        frappe.throw("Subject is required")
    if not (description or "").strip():
        frappe.throw("Description is required")
    cp_user = _get_cookie("cp_user")
    contact = frappe.db.get_value("Contact", {"email_id": cp_user}, "name") if cp_user else None
    doc = frappe.get_doc({
        "doctype":     "Issue",
        "subject":     subject.strip(),
        "customer":    customer,
        "contact":     contact or None,
        "priority":    priority or "Medium",
        "issue_type":  issue_type or None,
        "description": description.strip(),
        "status":      "Open",
        "raised_by":   cp_user or "",
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name, "status": doc.status}


@frappe.whitelist(allow_guest=True)
def reply_to_issue(name, message):
    customer = get_current_customer()
    if not frappe.db.exists("Issue", {"name": name, "customer": customer}):
        frappe.throw("Not authorised", frappe.PermissionError)
    if not (message or "").strip():
        frappe.throw("Message cannot be empty")
    cp_user = _get_cookie("cp_user")
    from frappe.utils import now
    comm = frappe.get_doc({
        "doctype":               "Communication",
        "communication_type":    "Communication",
        "communication_medium":  "Email",
        "sent_or_received":      "Sent",
        "sender":                cp_user or customer,
        "sender_full_name":      frappe.db.get_value("Customer", customer, "customer_name") or customer,
        "subject":               f"Re: {frappe.db.get_value('Issue', name, 'subject')}",
        "content":               message.strip(),
        "reference_doctype":     "Issue",
        "reference_name":        name,
        "communication_date":    now(),
    })
    comm.insert(ignore_permissions=True)
    if frappe.db.get_value("Issue", name, "status") in ("Resolved", "Closed"):
        frappe.db.set_value("Issue", name, "status", "Open")
    frappe.db.commit()
    return {"name": comm.name, "status": "sent"}


@frappe.whitelist(allow_guest=True)
def close_issue(name):
    customer = get_current_customer()
    if not frappe.db.exists("Issue", {"name": name, "customer": customer}):
        frappe.throw("Not authorised", frappe.PermissionError)
    frappe.db.set_value("Issue", name, "status", "Closed")
    frappe.db.commit()
    return {"name": name, "status": "Closed"}


# ══════════════════════════════════════════════════════════════════════════════
#  PROFILE
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist(allow_guest=True)
def get_profile():
    customer = get_current_customer()
    cust = frappe.db.get_value("Customer", customer,
        ["name", "customer_name", "customer_group", "territory",
         "mobile_no", "website", "default_currency", "tax_id",
         "default_price_list"],
        as_dict=True)
    return {
        "customer":  dict(cust) if cust else {},
        "contact":   _get_contact(),
        "addresses": _get_addresses(customer),
    }


@frappe.whitelist(allow_guest=True)
def update_contact(first_name, last_name=None, phone=None, mobile_no=None):
    if not (first_name or "").strip():
        frappe.throw("First name is required")
    cp_user = _get_cookie("cp_user")
    if not cp_user:
        frappe.throw("Session expired", frappe.AuthenticationError)
    contact_name = frappe.db.get_value("Contact", {"email_id": cp_user})
    if not contact_name:
        customer = get_current_customer()
        phone_nos = []
        if phone or mobile_no:
            phone_nos.append({"phone": phone or mobile_no or "", "is_primary_phone": 1})
        contact = frappe.get_doc({
            "doctype":    "Contact",
            "first_name": first_name.strip(),
            "last_name":  (last_name or "").strip(),
            "email_ids":  [{"email_id": cp_user, "is_primary": 1}],
            "phone_nos":  phone_nos,
            "links":      [{"link_doctype": "Customer", "link_name": customer}],
        })
        contact.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"status": "created", "name": contact.name}
    contact = frappe.get_doc("Contact", contact_name)
    contact.first_name = first_name.strip()
    contact.last_name  = (last_name or "").strip()
    if phone is not None:
        found = False
        for p in contact.phone_nos:
            if p.is_primary_phone:
                p.phone = phone; found = True; break
        if not found and phone:
            contact.append("phone_nos", {"phone": phone, "is_primary_phone": 1})
    if mobile_no is not None:
        found = False
        for p in contact.phone_nos:
            if p.is_primary_mobile_no:
                p.phone = mobile_no; found = True; break
        if not found and mobile_no:
            contact.append("phone_nos", {"phone": mobile_no, "is_primary_mobile_no": 1})
    contact.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "updated", "name": contact.name}


@frappe.whitelist(allow_guest=True)
def add_address(address_type, address_line1, city, country,
                address_line2=None, state=None, pincode=None,
                is_primary=0, is_shipping=0):
    customer = get_current_customer()
    if not all([address_line1, city, country]):
        frappe.throw("Address line 1, city and country are required")
    addr = frappe.get_doc({
        "doctype":             "Address",
        "address_title":       f"{customer}-{address_type}",
        "address_type":        address_type or "Billing",
        "address_line1":       address_line1.strip(),
        "address_line2":       (address_line2 or "").strip(),
        "city":                city.strip(),
        "state":               state or "",
        "country":             country,
        "pincode":             pincode or "",
        "is_primary_address":  int(is_primary),
        "is_shipping_address": int(is_shipping),
        "links": [{"link_doctype": "Customer", "link_name": customer}],
    })
    addr.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": addr.name, "status": "created"}


@frappe.whitelist(allow_guest=True)
def update_address(name, address_line1, city, country,
                   address_line2=None, state=None, pincode=None,
                   address_type=None, is_primary=0, is_shipping=0):
    customer = get_current_customer()
    if not frappe.db.exists("Dynamic Link", {
        "parenttype": "Address", "parent": name,
        "link_doctype": "Customer", "link_name": customer,
    }):
        frappe.throw("Not authorised", frappe.PermissionError)
    addr = frappe.get_doc("Address", name)
    addr.address_line1       = address_line1.strip()
    addr.address_line2       = (address_line2 or "").strip()
    addr.city                = city.strip()
    addr.state               = state or ""
    addr.country             = country
    addr.pincode             = pincode or ""
    addr.is_primary_address  = int(is_primary)
    addr.is_shipping_address = int(is_shipping)
    if address_type:
        addr.address_type = address_type
    addr.save(ignore_permissions=True)
    frappe.db.commit()
    return {"name": addr.name, "status": "updated"}


# ── Profile helpers ───────────────────────────────────────────────────────────

def _get_contact():
    cp_user = _get_cookie("cp_user")
    if not cp_user:
        return {}
    c = frappe.db.get_value("Contact", {"email_id": cp_user},
        ["name", "first_name", "last_name", "email_id", "phone", "mobile_no"],
        as_dict=True)
    if c:
        result = dict(c)
        if not result.get("phone") or not result.get("mobile_no"):
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
    return {"email_id": cp_user}


def _get_addresses(customer):
    links = frappe.get_all("Dynamic Link",
        filters={"link_doctype": "Customer", "link_name": customer, "parenttype": "Address"},
        fields=["parent"])
    result = []
    for l in links:
        a = frappe.db.get_value("Address", l.parent,
            ["name", "address_type", "address_line1", "address_line2",
             "city", "state", "country", "pincode",
             "is_primary_address", "is_shipping_address"],
            as_dict=True)
        if a:
            result.append(dict(a))
    return result


# ══════════════════════════════════════════════════════════════════════════════
#  NOTIFICATION HELPERS  (unchanged from original — kept intact)
# ══════════════════════════════════════════════════════════════════════════════

def _get_customer_email(customer_name):
    if frappe.db.has_column("Customer", "ec_portal_user"):
        email = frappe.db.get_value("Customer", customer_name, "ec_portal_user")
        if email:
            return email
    primary = frappe.db.get_value("Customer", customer_name, "customer_primary_contact")
    if primary:
        email = frappe.db.get_value("Contact", primary, "email_id")
        if email:
            return email
    row = frappe.db.sql("""
        SELECT c.email_id FROM `tabContact` c
        JOIN `tabDynamic Link` dl ON dl.parent = c.name
        WHERE dl.link_doctype = 'Customer' AND dl.link_name = %s
          AND c.email_id IS NOT NULL AND c.email_id != ''
        LIMIT 1
    """, customer_name, as_dict=True)
    return row[0].email_id if row else None


def _send_email(to, subject, body, reference_doctype=None, reference_name=None):
    if not to:
        return
    try:
        frappe.sendmail(recipients=[to], subject=subject, message=body,
                        reference_doctype=reference_doctype,
                        reference_name=reference_name, now=True)
    except Exception as e:
        frappe.log_error(f"Customer Portal email error: {e}", "Customer Portal Notifications")


def _portal_url(path=""):
    return f"{frappe.utils.get_url()}/customer-portal{path}"


def _fmt(amount, currency=""):
    return f"{currency} {flt(amount):,.2f}".strip()


# ── Doc event hooks (notifications — unchanged from original) ─────────────────

def on_quotation_submit(doc, method=None):
    try:
        email = _get_customer_email(doc.party_name)
        if not email: return
        _send_email(email, f"Quotation {doc.name} from {doc.company}",
            f"<p>Dear {doc.customer_name or doc.party_name},</p>"
            f"<p>A quotation for <strong>{_fmt(doc.grand_total, doc.currency)}</strong> "
            f"has been prepared for you (valid till {doc.valid_till or '—'}).</p>"
            f"<p><a href='{_portal_url()}'>View in Customer Portal</a></p>",
            "Quotation", doc.name)
    except Exception as e:
        frappe.log_error(f"on_quotation_submit: {e}", "Customer Portal Notifications")


def on_sales_order_submit(doc, method=None):
    try:
        email = _get_customer_email(doc.customer)
        if not email: return
        _send_email(email, f"Order Confirmed — {doc.name}",
            f"<p>Dear {doc.customer_name},</p>"
            f"<p>Your order <strong>{doc.name}</strong> for "
            f"<strong>{_fmt(doc.grand_total, doc.currency)}</strong> has been confirmed. "
            f"Expected delivery: {doc.delivery_date or '—'}.</p>"
            f"<p><a href='{_portal_url()}'>Track Your Order</a></p>",
            "Sales Order", doc.name)
    except Exception as e:
        frappe.log_error(f"on_sales_order_submit: {e}", "Customer Portal Notifications")


def on_delivery_submit(doc, method=None):
    try:
        email = _get_customer_email(doc.customer)
        if not email: return
        _send_email(email, f"Your Order Has Been Dispatched — {doc.name}",
            f"<p>Dear {doc.customer_name},</p>"
            f"<p>Your goods have been dispatched (Delivery Note: <strong>{doc.name}</strong>"
            f"{', LR: ' + doc.lr_no if doc.lr_no else ''}).</p>"
            f"<p><a href='{_portal_url()}'>View Delivery Details</a></p>",
            "Delivery Note", doc.name)
    except Exception as e:
        frappe.log_error(f"on_delivery_submit: {e}", "Customer Portal Notifications")


def on_invoice_submit(doc, method=None):
    try:
        if doc.is_return: return
        email = _get_customer_email(doc.customer)
        if not email: return
        _send_email(email,
            f"Invoice {doc.name} — {_fmt(doc.grand_total, doc.currency)} due {doc.due_date or ''}",
            f"<p>Dear {doc.customer_name},</p>"
            f"<p>Invoice <strong>{doc.name}</strong> for "
            f"<strong>{_fmt(doc.grand_total, doc.currency)}</strong> is due on "
            f"<strong>{doc.due_date or '—'}</strong>.</p>"
            f"<p><a href='{_portal_url()}'>View &amp; Pay Invoice</a></p>",
            "Sales Invoice", doc.name)
    except Exception as e:
        frappe.log_error(f"on_invoice_submit: {e}", "Customer Portal Notifications")


def on_payment_submit(doc, method=None):
    try:
        if doc.party_type != "Customer": return
        email = _get_customer_email(doc.party)
        if not email: return
        _send_email(email,
            f"Payment Received — {_fmt(doc.paid_amount, doc.paid_from_account_currency)}",
            f"<p>Dear {doc.party_name or doc.party},</p>"
            f"<p>Thank you! We have received your payment of "
            f"<strong>{_fmt(doc.paid_amount, doc.paid_from_account_currency)}</strong>.</p>"
            f"<p><a href='{_portal_url()}'>View Account Statement</a></p>",
            "Payment Entry", doc.name)
    except Exception as e:
        frappe.log_error(f"on_payment_submit: {e}", "Customer Portal Notifications")


def on_issue_update(doc, method=None):
    try:
        prev = doc.get_doc_before_save()
        if not prev or prev.status == doc.status or not doc.customer: return
        email = _get_customer_email(doc.customer) or doc.raised_by or None
        if not email: return
        _send_email(email, f"Support Ticket {doc.name} — {doc.status}",
            f"<p>Your ticket <strong>{doc.name}</strong> ({doc.subject}) "
            f"is now <strong>{doc.status}</strong>.</p>"
            f"<p><a href='{_portal_url()}'>View Ticket</a></p>",
            "Issue", doc.name)
    except Exception as e:
        frappe.log_error(f"on_issue_update: {e}", "Customer Portal Notifications")




def on_sales_order_update(doc, method=None):
    """
    Called on Sales Order on_update (after save/submit/cancel).
    Notifies the customer when order status changes to Completed or Closed.
    """
    try:
        prev = doc.get_doc_before_save()
        if not prev or prev.status == doc.status:
            return
        if doc.status not in ("Completed", "Closed"):
            return
        email = _get_customer_email(doc.customer)
        if not email:
            return
        _send_email(
            email,
            f"Order {doc.name} — {doc.status}",
            f"<p>Dear {doc.customer_name},</p>"
            f"<p>Your order <strong>{doc.name}</strong> is now <strong>{doc.status}</strong>.</p>"
            f"<p><a href='{_portal_url()}'>View in Customer Portal</a></p>",
            "Sales Order", doc.name
        )
    except Exception as e:
        frappe.log_error(f"on_sales_order_update: {e}", "Customer Portal Notifications")


def on_sales_order_cancel(doc, method=None):
    try:
        email = _get_customer_email(doc.customer)
        if not email:
            return
        _send_email(
            email,
            f"Order {doc.name} Cancelled",
            f"<p>Dear {doc.customer_name},</p>"
            f"<p>Your order <strong>{doc.name}</strong> has been cancelled. "
            f"Please contact us if this was unexpected.</p>"
            f"<p><a href='{_portal_url()}'>View in Customer Portal</a></p>",
            "Sales Order", doc.name
        )
    except Exception as e:
        frappe.log_error(f"on_sales_order_cancel: {e}", "Customer Portal Notifications")


def on_quotation_cancel(doc, method=None):
    try:
        email = _get_customer_email(doc.party_name)
        if not email:
            return
        _send_email(
            email,
            f"Quotation {doc.name} has been cancelled",
            f"<p>Dear {doc.customer_name or doc.party_name},</p>"
            f"<p>Quotation <strong>{doc.name}</strong> has been cancelled. "
            f"Please contact us if you have any questions.</p>",
            "Quotation", doc.name
        )
    except Exception as e:
        frappe.log_error(f"on_quotation_cancel: {e}", "Customer Portal Notifications")


def on_invoice_cancel(doc, method=None):
    try:
        if doc.is_return:
            return
        email = _get_customer_email(doc.customer)
        if not email:
            return
        _send_email(
            email,
            f"Invoice {doc.name} Cancelled",
            f"<p>Dear {doc.customer_name},</p>"
            f"<p>Invoice <strong>{doc.name}</strong> for "
            f"{_fmt(doc.grand_total, doc.currency)} has been cancelled.</p>"
            f"<p><a href='{_portal_url()}'>View in Customer Portal</a></p>",
            "Sales Invoice", doc.name
        )
    except Exception as e:
        frappe.log_error(f"on_invoice_cancel: {e}", "Customer Portal Notifications")


def on_communication_insert(doc, method=None):
    """
    Notify customer when support staff replies to their Issue.
    Only fires for incoming (Received) communications — not the customer's own messages.
    """
    try:
        if doc.reference_doctype != "Issue":
            return
        if doc.sent_or_received == "Sent":
            # This is the customer's own outbound message — don't echo back
            return
        issue = frappe.db.get_value(
            "Issue", doc.reference_name,
            ["customer", "subject", "raised_by"],
            as_dict=True
        )
        if not issue:
            return
        email = None
        if issue.customer:
            email = _get_customer_email(issue.customer)
        if not email:
            email = issue.raised_by or None
        if not email or doc.sender == email:
            return
        _send_email(
            email,
            f"New reply on Ticket {doc.reference_name}: {issue.subject}",
            f"<p>Hi,</p>"
            f"<p>Our support team has replied to your ticket "
            f"<strong>{doc.reference_name}</strong>.</p>"
            f"<div style='background:#f1f5f9;border-radius:8px;padding:16px;margin:16px 0;"
            f"font-size:14px;line-height:1.6'>{doc.content}</div>"
            f"<p><a href='{_portal_url()}' style='background:#0a4b7a;color:white;"
            f"padding:10px 20px;border-radius:6px;text-decoration:none'>"
            f"Reply in Customer Portal</a></p>",
            "Issue", doc.reference_name
        )
    except Exception as e:
        frappe.log_error(f"on_communication_insert: {e}", "Customer Portal Notifications")

# ── Scheduled tasks (unchanged) ───────────────────────────────────────────────

def send_overdue_invoice_reminders():
    try:
        today_d = getdate(today())
        overdue = frappe.db.sql("""
            SELECT customer, customer_name, name, due_date, outstanding_amount, currency
            FROM `tabSales Invoice`
            WHERE docstatus = 1 AND outstanding_amount > 0 AND due_date < %s
            ORDER BY customer, due_date
        """, today_d, as_dict=True)
        if not overdue: return
        from itertools import groupby
        for customer, invoices in groupby(
            sorted(overdue, key=lambda x: x.customer), key=lambda x: x.customer
        ):
            inv_list = list(invoices)
            email = _get_customer_email(customer)
            if not email: continue
            total    = sum(flt(i.outstanding_amount) for i in inv_list)
            currency = inv_list[0].currency
            _send_email(email,
                f"Payment Reminder — {len(inv_list)} Overdue Invoice(s) — {_fmt(total, currency)}",
                f"<p>Dear {inv_list[0].customer_name},</p>"
                f"<p>You have {len(inv_list)} overdue invoice(s) totalling "
                f"<strong>{_fmt(total, currency)}</strong>.</p>"
                f"<p><a href='{_portal_url()}'>Pay Now</a></p>")
    except Exception as e:
        frappe.log_error(f"send_overdue_invoice_reminders: {e}", "Customer Portal Notifications")


def send_weekly_account_summary():
    try:
        week_start = add_days(today(), -7)
        if not frappe.db.has_column("Customer", "ec_portal_user"):
            return
        customers = frappe.db.sql("""
            SELECT name AS customer, customer_name, ec_portal_user AS email
            FROM `tabCustomer`
            WHERE ec_portal_user IS NOT NULL AND ec_portal_user != ''
        """, as_dict=True)
        for row in customers:
            customer  = row.customer
            email     = row.email
            cust_name = row.customer_name or customer
            outstanding = frappe.db.sql("""
                SELECT COALESCE(SUM(outstanding_amount), 0)
                FROM `tabSales Invoice`
                WHERE customer = %s AND docstatus = 1 AND outstanding_amount > 0
            """, customer)[0][0]
            open_issues = frappe.db.count("Issue", {
                "customer": customer, "status": ["in", ["Open", "Replied"]]})
            if not outstanding and not open_issues:
                continue
            currency = (frappe.db.get_value("Customer", customer, "default_currency") or
                        frappe.defaults.get_global_default("currency") or "")
            _send_email(email, f"Weekly Account Summary — {cust_name}",
                f"<p>Dear {cust_name},</p>"
                f"<p>Outstanding: <strong>{_fmt(outstanding, currency)}</strong> · "
                f"Open Tickets: <strong>{open_issues}</strong></p>"
                f"<p><a href='{_portal_url()}'>Go to Customer Portal</a></p>")
    except Exception as e:
        frappe.log_error(f"send_weekly_account_summary: {e}", "Customer Portal Notifications")