# Copyright (c) 2026, Ecclesia Enterprise — License: MIT
# FILE: apps/ecclesia/ecclesia/api/supplier_portal_api.py
from __future__ import annotations

import json
import frappe
import hashlib
import secrets
import bcrypt
from frappe.utils import flt, getdate, today, add_days


# ══════════════════════════════════════════════════════════════════════════════
#  PORTAL AUTHENTICATION (No ERPNext users required)
#  Uses ec_portal_user (email) and portal_password on Supplier doctype
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist(allow_guest=True)
def portal_login(email, password):
    """
    Authenticate supplier using ec_portal_user (email) and portal_password.
    No ERPNext user account required.

    Called via GET (URL params) — mirrors the church member portal pattern
    which is the only approach proven to work reliably with Frappe's
    allow_guest=True whitelist without CSRF complications.
    """
    if not email or not password:
        frappe.throw("Email and password are required.", frappe.AuthenticationError)

    email = (email or "").strip().lower()

    # ── Find supplier by portal email ────────────────────────────────────────
    supplier_data = frappe.db.get_value(
        "Supplier",
        {"ec_portal_user": ["like", email]},
        ["name", "supplier_name", "portal_password", "disabled"],
        as_dict=True
    )

    if not supplier_data:
        import time; time.sleep(0.4)
        frappe.throw("No supplier account found with that email.", frappe.AuthenticationError)

    if supplier_data.disabled:
        frappe.throw("This supplier account is disabled.", frappe.AuthenticationError)

    # ── Verify password ──────────────────────────────────────────────────────
    # Fallback default password — accepted when portal_password is not yet set.
    # Override via: bench set-config default_portal_password "StrongValue"
    DEFAULT_PASSWORD = frappe.conf.get("default_portal_password", "@@##portA")

    stored = (supplier_data.portal_password or "").strip()

    matched = False

    if not stored:
        # No password set yet — only the default is accepted
        if password == DEFAULT_PASSWORD:
            matched = True
            _migrate_password(supplier_data.name, DEFAULT_PASSWORD)
    elif stored.startswith('$2b$') or stored.startswith('$2a$'):
        # bcrypt hash
        try:
            matched = bcrypt.checkpw(password.encode('utf-8'), stored.encode('utf-8'))
        except Exception:
            matched = False
        # Safety: also accept the default password if bcrypt fails
        if not matched and password == DEFAULT_PASSWORD:
            matched = True
    else:
        # Plain-text (legacy) — migrate to bcrypt on success
        if password == stored or password == DEFAULT_PASSWORD:
            matched = True
            _migrate_password(supplier_data.name, password)

    if not matched:
        import time; time.sleep(0.4)
        frappe.throw("Invalid password.", frappe.AuthenticationError)

    # ── Issue session token ──────────────────────────────────────────────────
    import uuid
    token  = str(uuid.uuid4())
    expiry = add_days(None, 7)

    _ensure_session_columns()

    frappe.db.set_value("Supplier", supplier_data.name, {
        "portal_session_token":  token,
        "portal_session_expiry": expiry
    })

    # Set cookies — same pattern as church portal
    from datetime import datetime, timedelta
    expires_dt = datetime.utcnow() + timedelta(days=7)
    try:
        frappe.local.cookie_manager.set_cookie(
            "portal_sid", token,
            expires=expires_dt, httponly=True, samesite="Lax", path="/"
        )
        frappe.local.cookie_manager.set_cookie(
            "portal_user", email,
            expires=expires_dt, httponly=False, samesite="Lax", path="/"
        )
    except TypeError:
        frappe.local.cookie_manager.set_cookie("portal_sid",  token, expires_dt)
        frappe.local.cookie_manager.set_cookie("portal_user", email, expires_dt)

    frappe.db.commit()

    return {
        "success":       True,
        "supplier":      supplier_data.name,
        "supplier_name": supplier_data.supplier_name,
        "message":       f"Welcome, {supplier_data.supplier_name}!"
    }


def _migrate_password(supplier_name, plain_password):
    """Silently upgrade a plain-text password to bcrypt."""
    try:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt).decode('utf-8')
        frappe.db.set_value("Supplier", supplier_name, "portal_password", hashed)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(f"Password migration failed: {e}", "Supplier Portal")


def _ensure_session_columns():
    """Add portal session columns to Supplier table if they don't exist yet."""
    if not frappe.db.has_column("Supplier", "portal_session_token"):
        frappe.db.sql("ALTER TABLE `tabSupplier` ADD COLUMN `portal_session_token` VARCHAR(140)")
        frappe.db.sql("ALTER TABLE `tabSupplier` ADD COLUMN `portal_session_expiry` DATETIME")
        frappe.db.commit()


@frappe.whitelist(allow_guest=True)
def portal_logout():
    """
    Clear portal session. allow_guest=True so it works even with an invalid session.
    """
    portal_sid = frappe.request.cookies.get("portal_sid") if hasattr(frappe, 'request') else None
    portal_user = frappe.request.cookies.get("portal_user") if hasattr(frappe, 'request') else None

    if portal_sid and portal_user:
        supplier_name = frappe.db.get_value("Supplier", {"ec_portal_user": portal_user}, "name")
        if supplier_name:
            frappe.db.set_value("Supplier", supplier_name, {
                "portal_session_token": None,
                "portal_session_expiry": None
            })
            frappe.db.commit()

    frappe.local.cookie_manager.delete_cookie("portal_sid", path="/")
    frappe.local.cookie_manager.delete_cookie("portal_user", path="/")

    return {"message": "Logged out successfully"}


@frappe.whitelist(allow_guest=True)
def check_portal_session():
    """
    Check if current portal session is valid. Called on every page load.
    Returns full supplier data so the frontend can bootstrap without a second call.
    """
    portal_sid = frappe.request.cookies.get("portal_sid") if hasattr(frappe, 'request') else None
    portal_user = frappe.request.cookies.get("portal_user") if hasattr(frappe, 'request') else None

    if not portal_sid or not portal_user:
        return {"authenticated": False}


    supplier = frappe.db.get_value(
        "Supplier",
        {
            "ec_portal_user": portal_user,
            "portal_session_token": portal_sid,
            "portal_session_expiry": (">", frappe.utils.now())
        },
        ["name", "supplier_name", "supplier_group", "supplier_type",
         "country", "tax_id", "default_currency", "payment_terms"],
        as_dict=True
    )

    if not supplier:
        frappe.local.cookie_manager.delete_cookie("portal_sid", path="/")
        frappe.local.cookie_manager.delete_cookie("portal_user", path="/")
        return {"authenticated": False}

    return {
        "authenticated": True,
        "supplier": supplier.name,
        "supplier_name": supplier.supplier_name,
        "supplier_group": supplier.supplier_group,
        "supplier_type": supplier.supplier_type,
        "country": supplier.country,
        "currency": supplier.default_currency or frappe.defaults.get_global_default("currency") or "NGN",
        "tax_id": supplier.tax_id,
        "payment_terms": supplier.payment_terms,
    }


@frappe.whitelist()
def set_portal_password(new_password):
    """Allow supplier to set/change their portal password."""
    supplier = get_current_supplier()

    if not new_password or len(new_password) < 6:
        frappe.throw("Password must be at least 6 characters long")

    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(new_password.encode('utf-8'), salt).decode('utf-8')

    frappe.db.set_value("Supplier", supplier, "portal_password", hashed)
    frappe.db.commit()

    return {"message": "Password updated successfully"}


def get_current_supplier():
    """
    Helper: resolve current supplier from portal session cookies.
    Raises AuthenticationError if not authenticated.
    """
    portal_sid = frappe.request.cookies.get("portal_sid") if hasattr(frappe, 'request') else None
    portal_user = frappe.request.cookies.get("portal_user") if hasattr(frappe, 'request') else None

    if not portal_sid or not portal_user:
        frappe.throw("Please log in to access the portal", frappe.AuthenticationError)


    supplier = frappe.db.get_value(
        "Supplier",
        {
            "portal_session_token": portal_sid,
            "portal_session_expiry": (">", frappe.utils.now())
        },
        "name"
    )

    if not supplier:
        frappe.throw("Session expired. Please log in again.", frappe.AuthenticationError)

    return supplier


def get_current_supplier_details():
    """Helper: return full supplier dict from session, or None."""
    portal_sid = frappe.request.cookies.get("portal_sid") if hasattr(frappe, 'request') else None
    portal_user = frappe.request.cookies.get("portal_user") if hasattr(frappe, 'request') else None

    if not portal_sid or not portal_user:
        return None


    return frappe.db.get_value(
        "Supplier",
        {
            "portal_session_token": portal_sid,
            "portal_session_expiry": (">", frappe.utils.now())
        },
        ["name", "supplier_name", "supplier_group", "supplier_type",
         "country", "tax_id", "default_currency", "payment_terms"],
        as_dict=True
    )


# ══════════════════════════════════════════════════════════════════════════════
#  PORTAL BOOT DATA
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist(allow_guest=True)
def get_portal_boot():
    """
    Return everything the dashboard needs in one call.
    Called after session is confirmed valid.
    """
    supplier = get_current_supplier_details()

    if not supplier:
        frappe.local.response.http_status_code = 401
        return {"error": "no_session"}

    portal_user = frappe.request.cookies.get("portal_user") if hasattr(frappe, 'request') else None

    stats = {
        "open_rfqs": frappe.db.sql("""
            SELECT COUNT(DISTINCT rfq.name)
            FROM `tabRequest for Quotation` rfq
            JOIN `tabRequest for Quotation Supplier` s ON s.parent = rfq.name
            WHERE s.supplier = %s AND rfq.status = 'Open' AND rfq.docstatus = 1
        """, supplier.name)[0][0],

        "open_pos": frappe.db.count("Purchase Order", {
            "supplier": supplier.name,
            "docstatus": 1,
            "status": ["in", ["To Receive and Bill", "To Receive"]]
        }),

        "unpaid_bills": frappe.db.count("Purchase Invoice", {
            "supplier": supplier.name,
            "docstatus": 1,
            "outstanding_amount": [">", 0]
        }),

        "pending_qis": frappe.db.sql("""
            SELECT COUNT(qi.name)
            FROM `tabQuality Inspection` qi
            JOIN `tabPurchase Receipt` pr ON pr.name = qi.reference_name
            WHERE pr.supplier = %s AND qi.status = 'Pending' AND pr.docstatus = 1
        """, supplier.name)[0][0],

        "total_payable": frappe.db.sql("""
            SELECT COALESCE(SUM(outstanding_amount), 0)
            FROM `tabPurchase Invoice`
            WHERE supplier = %s AND docstatus = 1 AND outstanding_amount > 0
        """, supplier.name)[0][0]
    }

    recent_pos = frappe.get_all("Purchase Order",
        filters={"supplier": supplier.name, "docstatus": 1},
        fields=["name", "transaction_date", "grand_total", "status", "currency"],
        order_by="transaction_date desc",
        limit=5
    )

    recent_rfqs = frappe.db.sql("""
        SELECT DISTINCT rfq.name, rfq.transaction_date, rfq.schedule_date, rfq.status
        FROM `tabRequest for Quotation` rfq
        JOIN `tabRequest for Quotation Supplier` s ON s.parent = rfq.name
        WHERE s.supplier = %s AND rfq.docstatus = 1
        ORDER BY rfq.transaction_date DESC
        LIMIT 5
    """, supplier.name, as_dict=True)

    contact = frappe.db.get_value(
        "Contact",
        {"email_id": portal_user},
        ["first_name", "last_name", "email_id", "phone", "mobile_no"],
        as_dict=True
    )

    return {
        "supplier":       supplier.name,
        "supplier_name":  supplier.supplier_name,
        "supplier_group": supplier.supplier_group,
        "supplier_type":  supplier.supplier_type,
        "country":        supplier.country,
        "tax_id":         supplier.tax_id,
        "currency":       supplier.default_currency or frappe.defaults.get_global_default("currency") or "NGN",
        "payment_terms":  supplier.payment_terms,
        "stats":          stats,
        "recent_pos":     [dict(r) for r in recent_pos],
        "recent_rfqs":    [dict(r) for r in recent_rfqs],
        "contact":        dict(contact) if contact else {},
        "today":          str(today())
    }


# ══════════════════════════════════════════════════════════════════════════════
#  RFQs
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_rfqs(status=None, page=1, page_size=20):
    supplier = get_current_supplier()
    start = (int(page) - 1) * int(page_size)

    extra, vals = "", [supplier]
    if status and status not in ("All", ""):
        extra = "AND rfq.status = %s"
        vals.append(status)

    rows = frappe.db.sql(f"""
        SELECT DISTINCT
            rfq.name, rfq.transaction_date, rfq.status,
            rfq.schedule_date, rfq.message_for_supplier, rfq.company
        FROM `tabRequest for Quotation` rfq
        JOIN `tabRequest for Quotation Supplier` s ON s.parent = rfq.name
        WHERE s.supplier = %s AND rfq.docstatus = 1 {extra}
        ORDER BY rfq.transaction_date DESC
        LIMIT %s OFFSET %s
    """, vals + [int(page_size), start], as_dict=True)

    total = frappe.db.sql(f"""
        SELECT COUNT(DISTINCT rfq.name)
        FROM `tabRequest for Quotation` rfq
        JOIN `tabRequest for Quotation Supplier` s ON s.parent = rfq.name
        WHERE s.supplier = %s AND rfq.docstatus = 1 {extra}
    """, vals)[0][0]

    for r in rows:
        sq = frappe.db.get_value("Supplier Quotation",
            {"supplier": supplier, "rfq_number": r.name, "docstatus": ["!=", 2]})
        r["responded"] = bool(sq)
        r["supplier_quotation"] = sq or None
        r["items_count"] = frappe.db.sql(
            "SELECT COUNT(*) FROM `tabRequest for Quotation Item` WHERE parent=%s", r.name)[0][0]

    return {"data": [dict(r) for r in rows], "total": int(total or 0)}


@frappe.whitelist()
def get_rfq_detail(name):
    supplier = get_current_supplier()
    if not frappe.db.exists("Request for Quotation Supplier", {"parent": name, "supplier": supplier}):
        frappe.throw("This RFQ was not sent to your account", frappe.PermissionError)

    doc = frappe.get_doc("Request for Quotation", name)
    items = [{
        "item_code":   i.item_code,
        "item_name":   i.item_name,
        "description": i.description or "",
        "qty":         i.qty,
        "uom":         i.uom,
        "warehouse":   getattr(i, "warehouse", ""),
    } for i in doc.items]

    existing_sq = frappe.db.get_value("Supplier Quotation",
        {"supplier": supplier, "rfq_number": name, "docstatus": ["!=", 2]},
        ["name", "status", "grand_total", "currency"], as_dict=True)

    return {
        "name":                 doc.name,
        "status":               doc.status,
        "transaction_date":     str(doc.transaction_date),
        "schedule_date":        str(doc.schedule_date) if doc.schedule_date else None,
        "message_for_supplier": doc.message_for_supplier or "",
        "items":                items,
        "existing_quotation":   dict(existing_sq) if existing_sq else None,
    }


@frappe.whitelist()
def submit_quotation(rfq_name, items, valid_till=None, payment_terms=None, notes=None):
    supplier = get_current_supplier()

    if isinstance(items, str):
        items = json.loads(items)

    if not rfq_name:
        frappe.throw("RFQ reference is required")
    if not items:
        frappe.throw("At least one item with pricing is required")
    if not frappe.db.exists("Request for Quotation Supplier", {"parent": rfq_name, "supplier": supplier}):
        frappe.throw("This RFQ was not sent to your account", frappe.PermissionError)

    rfq = frappe.get_doc("Request for Quotation", rfq_name)
    supplier_doc = frappe.get_doc("Supplier", supplier)

    sq_items = []
    for item in items:
        if not item.get("item_code"):
            continue
        rate = flt(item.get("rate", 0))
        if rate <= 0:
            frappe.throw(f"Rate is required for item {item.get('item_code')}")
        sq_items.append({
            "item_code":      item["item_code"],
            "item_name":      item.get("item_name") or frappe.db.get_value("Item", item["item_code"], "item_name") or item["item_code"],
            "qty":            flt(item.get("qty", 1)),
            "rate":           rate,
            "uom":            item.get("uom") or "Nos",
            "lead_time_days": int(item.get("lead_time_days") or 0),
            "description":    item.get("description") or "",
        })

    if not sq_items:
        frappe.throw("No valid items found")

    sq = frappe.get_doc({
        "doctype":                "Supplier Quotation",
        "supplier":               supplier,
        "rfq_number":             rfq_name,
        "company":                rfq.company,
        "transaction_date":       today(),
        "valid_till":             valid_till or None,
        "payment_terms_template": payment_terms or getattr(supplier_doc, "payment_terms", None) or None,
        "terms":                  notes or "",
        "items":                  sq_items,
    })
    sq.insert(ignore_permissions=True)
    sq.submit()
    frappe.db.commit()
    return {"name": sq.name, "status": sq.status, "docstatus": sq.docstatus}


@frappe.whitelist()
def get_my_quotations(page=1, page_size=20):
    supplier = get_current_supplier()
    start = (int(page) - 1) * int(page_size)
    rows = frappe.get_all("Supplier Quotation",
        filters={"supplier": supplier, "docstatus": ["!=", 2]},
        fields=["name", "transaction_date", "valid_till", "grand_total",
                "currency", "status", "rfq_number"],
        order_by="transaction_date desc",
        limit=int(page_size), start=start)
    total = frappe.db.count("Supplier Quotation", {"supplier": supplier, "docstatus": ["!=", 2]})
    return {"data": [dict(r) for r in rows], "total": total}


# ══════════════════════════════════════════════════════════════════════════════
#  PURCHASE ORDERS
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_purchase_orders(status=None, page=1, page_size=20):
    supplier = get_current_supplier()
    filters = {"supplier": supplier, "docstatus": ["!=", 2]}
    if status and status != "All":
        filters["status"] = status
    start = (int(page) - 1) * int(page_size)
    rows = frappe.get_all("Purchase Order",
        filters=filters,
        fields=["name", "transaction_date", "schedule_date", "grand_total",
                "currency", "status", "per_received", "per_billed"],
        order_by="transaction_date desc",
        limit=int(page_size), start=start)
    total = frappe.db.count("Purchase Order", filters)
    return {"data": [dict(r) for r in rows], "total": total}


@frappe.whitelist()
def get_purchase_order_detail(name):
    supplier = get_current_supplier()
    doc = frappe.get_doc("Purchase Order", name)
    if doc.supplier != supplier:
        frappe.throw("Not authorised", frappe.PermissionError)

    items = []
    for i in doc.items:
        # billed_qty lives on the PO item row as `billed_qty`; fall back gracefully
        billed_qty = getattr(i, "billed_qty", None)
        if billed_qty is None:
            # Derive from per_billed if field absent
            billed_qty = round((flt(doc.per_billed) / 100) * flt(i.qty), 4)

        items.append({
            "item_code":    i.item_code,
            "item_name":    i.item_name,
            "description":  i.description or "",
            "qty":          i.qty,
            "received_qty": i.received_qty,
            "billed_qty":   billed_qty,
            "uom":          i.uom,
            "rate":         i.rate,
            "amount":       i.amount,
            "schedule_date": str(i.schedule_date) if getattr(i, "schedule_date", None) else None,
        })

    receipts = frappe.db.sql("""
        SELECT DISTINCT parent FROM `tabPurchase Receipt Item`
        WHERE purchase_order = %s AND docstatus = 1
    """, name, as_dict=True)

    return {
        "name":             doc.name,
        "status":           doc.status,
        "transaction_date": str(doc.transaction_date),
        "schedule_date":    str(doc.schedule_date) if doc.schedule_date else None,
        "grand_total":      doc.grand_total,
        "currency":         doc.currency,
        "per_received":     doc.per_received,
        "per_billed":       doc.per_billed,
        "payment_terms":    doc.payment_terms_template,
        "items":            items,
        "receipts":         [r.parent for r in receipts],
    }


@frappe.whitelist()
def acknowledge_purchase_order(name):
    supplier = get_current_supplier()
    if frappe.db.get_value("Purchase Order", name, "supplier") != supplier:
        frappe.throw("Not authorised", frappe.PermissionError)
    if frappe.db.get_value("Purchase Order", name, "docstatus") != 1:
        frappe.throw("Only submitted Purchase Orders can be acknowledged")

    frappe.get_doc({
        "doctype":           "Comment",
        "comment_type":      "Info",
        "reference_doctype": "Purchase Order",
        "reference_name":    name,
        "content":           "Purchase Order acknowledged by supplier via portal.",
    }).insert(ignore_permissions=True)

    if frappe.db.has_column("Purchase Order", "supplier_acknowledged"):
        frappe.db.set_value("Purchase Order", name, {
            "supplier_acknowledged":    1,
            "supplier_acknowledged_on": frappe.utils.now(),
        })

    frappe.db.commit()
    return {"name": name, "acknowledged": True}


# ══════════════════════════════════════════════════════════════════════════════
#  SUBCONTRACTING ORDERS
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_subcontracting_orders(status=None, page=1, page_size=20):
    supplier = get_current_supplier()
    filters = {"supplier": supplier, "docstatus": ["!=", 2]}
    if status and status != "All":
        filters["status"] = status
    start = (int(page) - 1) * int(page_size)
    try:
        rows = frappe.get_all("Subcontracting Order",
            filters=filters,
            fields=["name", "transaction_date", "schedule_date",
                    "grand_total", "currency", "status", "per_received"],
            order_by="transaction_date desc",
            limit=int(page_size), start=start)
        total = frappe.db.count("Subcontracting Order", filters)
    except Exception:
        rows, total = [], 0
    return {"data": [dict(r) for r in rows], "total": total}


# ══════════════════════════════════════════════════════════════════════════════
#  PURCHASE RECEIPTS & QUALITY INSPECTIONS
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_purchase_receipts(page=1, page_size=20):
    supplier = get_current_supplier()
    start = (int(page) - 1) * int(page_size)
    rows = frappe.get_all("Purchase Receipt",
        filters={"supplier": supplier, "docstatus": 1},
        fields=["name", "posting_date", "grand_total", "currency",
                "status", "is_return", "supplier_delivery_note"],
        order_by="posting_date desc",
        limit=int(page_size), start=start)
    total = frappe.db.count("Purchase Receipt", {"supplier": supplier, "docstatus": 1})
    return {"data": [dict(r) for r in rows], "total": total}


@frappe.whitelist()
def get_receipt_detail(name):
    supplier = get_current_supplier()
    doc = frappe.get_doc("Purchase Receipt", name)
    if doc.supplier != supplier:
        frappe.throw("Not authorised", frappe.PermissionError)

    items = [{
        "item_code":    i.item_code,
        "item_name":    i.item_name,
        "qty":          i.qty,
        "accepted_qty": i.accepted_qty,
        "rejected_qty": i.rejected_qty,
        "uom":          i.uom,
        "rate":         i.rate,
        "amount":       i.amount,
    } for i in doc.items]

    qi_list = frappe.get_all("Quality Inspection",
        filters={"reference_type": "Purchase Receipt", "reference_name": name},
        fields=["name", "item_code", "item_name", "status",
                "inspected_by", "inspection_date"])

    return {
        "name":                   doc.name,
        "status":                 doc.status,
        "posting_date":           str(doc.posting_date),
        "is_return":              doc.is_return,
        "grand_total":            doc.grand_total,
        "currency":               doc.currency,
        "supplier_delivery_note": doc.supplier_delivery_note or "",
        "items":                  items,
        "quality_inspections":    [dict(q) for q in qi_list],
    }


@frappe.whitelist()
def get_quality_inspections(page=1, page_size=20):
    supplier = get_current_supplier()
    start = (int(page) - 1) * int(page_size)

    rows = frappe.db.sql("""
        SELECT qi.name, qi.item_code, qi.item_name, qi.status,
               qi.reference_name, qi.report_date,
               qi.inspected_by, qi.docstatus
        FROM `tabQuality Inspection` qi
        JOIN `tabPurchase Receipt` pr ON pr.name = qi.reference_name
        WHERE pr.supplier = %s AND pr.docstatus = 1
          AND qi.reference_type = 'Purchase Receipt'
        ORDER BY qi.report_date DESC
        LIMIT %s OFFSET %s
    """, (supplier, int(page_size), start), as_dict=True)

    total = frappe.db.sql("""
        SELECT COUNT(qi.name)
        FROM `tabQuality Inspection` qi
        JOIN `tabPurchase Receipt` pr ON pr.name = qi.reference_name
        WHERE pr.supplier = %s AND pr.docstatus = 1
          AND qi.reference_type = 'Purchase Receipt'
    """, supplier)[0][0]

    return {"data": [dict(r) for r in rows], "total": int(total or 0)}


# ══════════════════════════════════════════════════════════════════════════════
#  INVOICES & PAYMENTS
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_invoices(status=None, page=1, page_size=20):
    supplier = get_current_supplier()
    filters = {"supplier": supplier, "docstatus": 1}
    if status == "Unpaid":
        filters["outstanding_amount"] = [">", 0]
    elif status == "Paid":
        filters["outstanding_amount"] = ["<=", 0]
    elif status == "Overdue":
        filters["outstanding_amount"] = [">", 0]
        filters["due_date"] = ["<", today()]
    start = (int(page) - 1) * int(page_size)
    rows = frappe.get_all("Purchase Invoice",
        filters=filters,
        fields=["name", "posting_date", "due_date", "grand_total",
                "outstanding_amount", "currency", "status", "is_return",
                "bill_no", "bill_date"],
        order_by="posting_date desc",
        limit=int(page_size), start=start)
    total = frappe.db.count("Purchase Invoice", filters)
    today_d = getdate(today())
    for r in rows:
        r["is_overdue"] = (flt(r.outstanding_amount) > 0 and
                           r.due_date and getdate(r.due_date) < today_d)
    return {"data": [dict(r) for r in rows], "total": total}


@frappe.whitelist()
def get_invoice_detail(name):
    supplier = get_current_supplier()
    doc = frappe.get_doc("Purchase Invoice", name)
    if doc.supplier != supplier:
        frappe.throw("Not authorised", frappe.PermissionError)

    items = [{
        "item_code":        i.item_code,
        "item_name":        i.item_name,
        "qty":              i.qty,
        "uom":              i.uom,
        "rate":             i.rate,
        "amount":           i.amount,
        "purchase_order":   i.purchase_order or "",
        "purchase_receipt": i.purchase_receipt or "",
    } for i in doc.items]

    payments = frappe.get_all("Payment Entry Reference",
        filters={"reference_doctype": "Purchase Invoice", "reference_name": name},
        fields=["parent", "allocated_amount"])

    return {
        "name":                    doc.name,
        "status":                  doc.status,
        "posting_date":            str(doc.posting_date),
        "due_date":                str(doc.due_date) if doc.due_date else None,
        "bill_no":                 doc.bill_no or "",
        "bill_date":               str(doc.bill_date) if doc.bill_date else None,
        "grand_total":             doc.grand_total,
        "outstanding_amount":      doc.outstanding_amount,
        "currency":                doc.currency,
        "total_taxes_and_charges": doc.total_taxes_and_charges,
        "is_return":               doc.is_return,
        "items":                   items,
        "payments":                [dict(p) for p in payments],
        "payment_terms":           doc.payment_terms_template or "",
        "remarks":                 doc.remarks or "",
    }


@frappe.whitelist()
def get_payment_history(page=1, page_size=20):
    supplier = get_current_supplier()
    start = (int(page) - 1) * int(page_size)
    rows = frappe.get_all("Payment Entry",
        filters={"party_type": "Supplier", "party": supplier, "docstatus": 1},
        fields=["name", "posting_date", "paid_amount", "paid_to_account_currency as currency",
                "mode_of_payment", "reference_no", "remarks"],
        order_by="posting_date desc",
        limit=int(page_size), start=start)
    total = frappe.db.count("Payment Entry",
        {"party_type": "Supplier", "party": supplier, "docstatus": 1})
    return {"data": [dict(r) for r in rows], "total": total}


@frappe.whitelist()
def get_outstanding_summary():
    supplier = get_current_supplier()
    today_d = getdate(today())
    rows = frappe.db.sql("""
        SELECT name, posting_date, due_date, grand_total,
               outstanding_amount, currency, status, bill_no
        FROM `tabPurchase Invoice`
        WHERE supplier = %s AND docstatus = 1 AND outstanding_amount > 0
        ORDER BY due_date ASC
    """, supplier, as_dict=True)
    total_payable = sum(flt(r.outstanding_amount) for r in rows)
    overdue = [r for r in rows if r.due_date and getdate(r.due_date) < today_d]
    total_overdue = sum(flt(r.outstanding_amount) for r in overdue)
    return {
        "total_payable": total_payable,
        "total_overdue": total_overdue,
        "invoices":      [dict(r) for r in rows],
    }


# ══════════════════════════════════════════════════════════════════════════════
#  SUPPLIER ACCOUNT LEDGER
#  Shows every debit/credit entry from the supplier's perspective:
#    Purchase Invoices  → Credit (we owe supplier — supplier's receivable)
#    Debit Notes        → Debit  (return/rejection reduces what we owe)
#    Payment Entries    → Debit  (cash paid out to supplier)
#    Journal Entries    → Debit or Credit per party account direction
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist(allow_guest=True)
def get_ledger(from_date=None, to_date=None, page=1, page_size=50):
    """
    Return a chronological debit/credit ledger for the supplier.

    From the SUPPLIER's perspective (what they are owed / paid):
      PI   Purchase Invoice        → Credit (supplier earns this — raises balance payable)
      DN   Debit Note (is_return)  → Debit  (return reduces balance payable)
      PMT  Payment Entry           → Debit  (payment reduces what we owe)
      JV   Journal Entry           → Debit or Credit per account entry direction

    Positive closing balance = we still owe supplier money.
    Negative closing balance = supplier owes us money (overpaid / credit).
    """
    supplier = get_current_supplier()
    page, page_size = int(page), int(page_size)

    fd = from_date or add_days(today(), -365)
    td = to_date   or today()

    # ── Purchase Invoices (regular) ──────────────────────────────────────────
    invoices = frappe.db.sql("""
        SELECT
            name               AS ref_no,
            posting_date       AS trx_date,
            'Purchase Invoice' AS doc_type,
            'PI'               AS doc_abbr,
            0                  AS debit,
            grand_total        AS credit,
            outstanding_amount,
            currency,
            status,
            bill_no            AS ext_ref
        FROM `tabPurchase Invoice`
        WHERE supplier   = %(supplier)s
          AND docstatus  = 1
          AND is_return  = 0
          AND posting_date BETWEEN %(fd)s AND %(td)s
    """, {"supplier": supplier, "fd": fd, "td": td}, as_dict=True)

    # ── Debit Notes (is_return = 1 on Purchase Invoice) ──────────────────────
    debit_notes = frappe.db.sql("""
        SELECT
            name               AS ref_no,
            posting_date       AS trx_date,
            'Debit Note'       AS doc_type,
            'DN'               AS doc_abbr,
            ABS(grand_total)   AS debit,
            0                  AS credit,
            0                  AS outstanding_amount,
            currency,
            status,
            bill_no            AS ext_ref
        FROM `tabPurchase Invoice`
        WHERE supplier   = %(supplier)s
          AND docstatus  = 1
          AND is_return  = 1
          AND posting_date BETWEEN %(fd)s AND %(td)s
    """, {"supplier": supplier, "fd": fd, "td": td}, as_dict=True)

    # ── Payment Entries ───────────────────────────────────────────────────────
    payments = frappe.db.sql("""
        SELECT
            name                       AS ref_no,
            posting_date               AS trx_date,
            'Payment'                  AS doc_type,
            'PMT'                      AS doc_abbr,
            paid_amount                AS debit,
            0                          AS credit,
            0                          AS outstanding_amount,
            paid_to_account_currency   AS currency,
            'Submitted'                AS status,
            reference_no               AS ext_ref,
            mode_of_payment
        FROM `tabPayment Entry`
        WHERE party_type  = 'Supplier'
          AND party       = %(supplier)s
          AND docstatus   = 1
          AND posting_date BETWEEN %(fd)s AND %(td)s
    """, {"supplier": supplier, "fd": fd, "td": td}, as_dict=True)

    # ── Journal Entries (party-level) ─────────────────────────────────────────
    je_rows = frappe.db.sql("""
        SELECT
            jea.parent                        AS ref_no,
            je.posting_date                   AS trx_date,
            'Journal Entry'                   AS doc_type,
            'JV'                              AS doc_abbr,
            jea.debit_in_account_currency     AS debit,
            jea.credit_in_account_currency    AS credit,
            0                                 AS outstanding_amount,
            jea.account_currency              AS currency,
            je.voucher_type                   AS status,
            je.user_remark                    AS ext_ref
        FROM `tabJournal Entry Account` jea
        JOIN `tabJournal Entry` je ON je.name = jea.parent
        WHERE jea.party_type = 'Supplier'
          AND jea.party      = %(supplier)s
          AND je.docstatus   = 1
          AND je.posting_date BETWEEN %(fd)s AND %(td)s
    """, {"supplier": supplier, "fd": fd, "td": td}, as_dict=True)

    # ── Merge and sort chronologically ───────────────────────────────────────
    all_entries = list(invoices) + list(debit_notes) + list(payments) + list(je_rows)
    all_entries.sort(key=lambda x: (str(x.get("trx_date") or ""), x.get("ref_no") or ""))

    # ── Running balance (credit positive = supplier is owed money) ────────────
    running = flt(0)
    for e in all_entries:
        e["debit"]  = flt(e.get("debit",  0))
        e["credit"] = flt(e.get("credit", 0))
        running    += e["credit"] - e["debit"]   # credit increases, debit decreases
        e["balance"] = running
        if hasattr(e.get("trx_date"), "strftime"):
            e["trx_date"] = str(e["trx_date"])

    total_debit  = sum(flt(e["debit"])  for e in all_entries)
    total_credit = sum(flt(e["credit"]) for e in all_entries)

    # ── Paginate after running balance is computed ────────────────────────────
    start     = (page - 1) * page_size
    page_data = all_entries[start: start + page_size]

    return {
        "data":            page_data,
        "total":           len(all_entries),
        "total_debit":     total_debit,
        "total_credit":    total_credit,
        "closing_balance": running,
        "from_date":       fd,
        "to_date":         td,
    }


@frappe.whitelist()
def upload_invoice(purchase_order, bill_no, bill_date, items, remarks=None):
    """Supplier submits their invoice against a PO — saved as DRAFT for AP review."""
    supplier = get_current_supplier()

    if isinstance(items, str):
        items = json.loads(items)

    if not purchase_order:
        frappe.throw("Purchase Order reference is required")
    if frappe.db.get_value("Purchase Order", purchase_order, "supplier") != supplier:
        frappe.throw("This PO does not belong to your account", frappe.PermissionError)
    if not bill_no:
        frappe.throw("Your invoice number (Bill No.) is required")
    if not items:
        frappe.throw("At least one item is required")

    po_doc = frappe.get_doc("Purchase Order", purchase_order)

    pi_items = []
    for item in items:
        if not item.get("item_code"):
            continue
        pi_items.append({
            "item_code":      item["item_code"],
            "qty":            flt(item.get("qty", 1)),
            "rate":           flt(item.get("rate", 0)),
            "uom":            item.get("uom") or "Nos",
            "purchase_order": purchase_order,
        })

    if not pi_items:
        frappe.throw("No valid line items provided")

    pi = frappe.get_doc({
        "doctype":   "Purchase Invoice",
        "supplier":  supplier,
        "company":   po_doc.company,
        "currency":  po_doc.currency,
        "bill_no":   bill_no,
        "bill_date": bill_date,
        "remarks":   remarks or "Uploaded via Supplier Portal",
        "items":     pi_items,
    })
    pi.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": pi.name, "status": pi.status, "note": "Invoice submitted for AP team review."}


# ══════════════════════════════════════════════════════════════════════════════
#  ITEM CATALOGUE
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_items(search=None, page=1, page_size=20):
    supplier = get_current_supplier()
    start = (int(page) - 1) * int(page_size)

    where = "isup.supplier = %s AND i.disabled = 0 AND i.is_purchase_item = 1"
    vals = [supplier]

    if search and search.strip():
        where += " AND (i.item_code LIKE %s OR i.item_name LIKE %s)"
        s = f"%{search.strip()}%"
        vals += [s, s]

    items = frappe.db.sql(f"""
        SELECT DISTINCT
            i.name AS item_code,
            i.item_name,
            i.item_group,
            i.stock_uom,
            COALESCE(isup.supplier_part_no,'') AS supplier_part_no,
            COALESCE(isup.lead_time_days, 0)   AS lead_time_days
        FROM `tabItem` i
        JOIN `tabItem Supplier` isup ON isup.parent = i.name
        WHERE {where}
        ORDER BY i.item_name
        LIMIT %s OFFSET %s
    """, vals + [int(page_size), start], as_dict=True)

    total = frappe.db.sql(f"""
        SELECT COUNT(DISTINCT i.name) FROM `tabItem` i
        JOIN `tabItem Supplier` isup ON isup.parent = i.name
        WHERE {where}
    """, vals)[0][0]

    for item in items:
        price = frappe.db.sql("""
            SELECT price_list_rate, currency
            FROM `tabItem Price`
            WHERE item_code = %s AND buying = 1
            ORDER BY COALESCE(valid_from,'1970-01-01') DESC LIMIT 1
        """, item.item_code, as_dict=True)
        item["last_price"]     = flt(price[0].price_list_rate) if price else 0
        item["price_currency"] = price[0].currency if price else ""

    return {"data": [dict(i) for i in items], "total": int(total or 0)}


@frappe.whitelist()
def update_part_number(item_code, supplier_part_no, lead_time_days=None):
    supplier = get_current_supplier()
    row = frappe.db.get_value("Item Supplier",
        {"parent": item_code, "supplier": supplier}, "name")
    if not row:
        frappe.throw("This item is not in your catalogue", frappe.PermissionError)
    frappe.db.set_value("Item Supplier", row, {
        "supplier_part_no": supplier_part_no or "",
        "lead_time_days":   int(lead_time_days or 0),
    })
    frappe.db.commit()
    return {"item_code": item_code, "status": "updated"}


# ══════════════════════════════════════════════════════════════════════════════
#  PROFILE
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_profile():
    supplier = get_current_supplier()
    sup = frappe.db.get_value("Supplier", supplier,
        ["name", "supplier_name", "supplier_group", "supplier_type",
         "country", "tax_id", "payment_terms", "default_currency",
         "website", "mobile_no"], as_dict=True)

    return {
        "supplier":      dict(sup) if sup else {},
        "contact":       _get_contact(),
        "addresses":     _get_addresses(supplier),
        "bank_accounts": _get_bank_accounts(supplier),
    }


@frappe.whitelist()
def update_contact(first_name, last_name=None, phone=None, mobile_no=None):
    if not first_name or not first_name.strip():
        frappe.throw("First name is required")

    portal_user = frappe.request.cookies.get("portal_user") if hasattr(frappe, 'request') else None
    if not portal_user:
        frappe.throw("Session expired", frappe.AuthenticationError)

    contact_name = frappe.db.get_value("Contact", {"email_id": portal_user})

    if not contact_name:
        supplier = get_current_supplier()
        phone_nos = []
        if phone or mobile_no:
            phone_nos.append({"phone": phone or mobile_no or "", "is_primary_phone": 1})
        contact = frappe.get_doc({
            "doctype":    "Contact",
            "first_name": first_name.strip(),
            "last_name":  (last_name or "").strip(),
            "email_ids":  [{"email_id": portal_user, "is_primary": 1}],
            "phone_nos":  phone_nos,
            "links":      [{"link_doctype": "Supplier", "link_name": supplier}],
        })
        contact.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"status": "created", "name": contact.name}

    contact = frappe.get_doc("Contact", contact_name)
    contact.first_name = first_name.strip()
    contact.last_name = (last_name or "").strip()

    if phone is not None:
        found = False
        for p in contact.phone_nos:
            if p.is_primary_phone:
                p.phone = phone
                found = True
                break
        if not found and phone:
            contact.append("phone_nos", {"phone": phone, "is_primary_phone": 1})

    if mobile_no is not None:
        found = False
        for p in contact.phone_nos:
            if p.is_primary_mobile_no:
                p.phone = mobile_no
                found = True
                break
        if not found and mobile_no:
            contact.append("phone_nos", {"phone": mobile_no, "is_primary_mobile_no": 1})

    contact.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "updated", "name": contact.name}


@frappe.whitelist()
def add_address(address_type, address_line1, city, country,
                address_line2=None, state=None, pincode=None,
                is_primary=0, is_shipping=0):
    supplier = get_current_supplier()
    if not all([address_line1, city, country]):
        frappe.throw("Address line 1, city and country are required")

    addr = frappe.get_doc({
        "doctype":             "Address",
        "address_title":       f"{supplier}-{address_type}",
        "address_type":        address_type or "Billing",
        "address_line1":       address_line1.strip(),
        "address_line2":       (address_line2 or "").strip(),
        "city":                city.strip(),
        "state":               state or "",
        "country":             country,
        "pincode":             pincode or "",
        "is_primary_address":  int(is_primary),
        "is_shipping_address": int(is_shipping),
        "links": [{"link_doctype": "Supplier", "link_name": supplier}],
    })
    addr.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": addr.name, "status": "created"}


@frappe.whitelist()
def update_address(name, address_line1, city, country,
                   address_line2=None, state=None, pincode=None,
                   address_type=None, is_primary=0, is_shipping=0):
    supplier = get_current_supplier()
    if not frappe.db.exists("Dynamic Link", {
        "parenttype": "Address", "parent": name,
        "link_doctype": "Supplier", "link_name": supplier,
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


@frappe.whitelist()
def get_bank_accounts():
    supplier = get_current_supplier()
    return _get_bank_accounts(supplier)


@frappe.whitelist()
def add_bank_account(bank_name, account_name, account_no,
                     branch_code=None, iban=None, swift_number=None):
    supplier = get_current_supplier()
    if not all([bank_name, account_name, account_no]):
        frappe.throw("Bank name, account name and account number are required")

    if not frappe.db.exists("Bank", bank_name):
        frappe.get_doc({"doctype": "Bank", "bank_name": bank_name}).insert(ignore_permissions=True)

    ba = frappe.get_doc({
        "doctype":         "Bank Account",
        "account_name":    account_name.strip(),
        "bank":            bank_name,
        "bank_account_no": account_no.strip(),
        "branch_code":     branch_code or "",
        "iban":            iban or "",
        "swift_number":    swift_number or "",
        "party_type":      "Supplier",
        "party":           supplier,
        "is_default":      0,
    })
    ba.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": ba.name, "status": "created",
            "note": "Submitted for finance team review before activation."}


# ── Private helpers ───────────────────────────────────────────────────────────

def _get_contact():
    portal_user = frappe.request.cookies.get("portal_user") if hasattr(frappe, 'request') else None
    if not portal_user:
        return {}

    c = frappe.db.get_value("Contact", {"email_id": portal_user},
        ["name", "first_name", "last_name", "email_id", "phone", "mobile_no"], as_dict=True)
    if c:
        result = dict(c)
        if not result.get("phone") or not result.get("mobile_no"):
            phones = frappe.get_all("Contact Phone",
                filters={"parent": c.name},
                fields=["phone", "is_primary_phone", "is_primary_mobile_no"], order_by="idx")
            for p in phones:
                if p.is_primary_phone and not result.get("phone"):
                    result["phone"] = p.phone
                if p.is_primary_mobile_no and not result.get("mobile_no"):
                    result["mobile_no"] = p.phone
        return result
    return {}


def _get_addresses(supplier):
    links = frappe.get_all("Dynamic Link",
        filters={"link_doctype": "Supplier", "link_name": supplier, "parenttype": "Address"},
        fields=["parent"])
    result = []
    for l in links:
        a = frappe.db.get_value("Address", l.parent,
            ["name", "address_type", "address_line1", "address_line2",
             "city", "state", "country", "pincode",
             "is_primary_address", "is_shipping_address"], as_dict=True)
        if a:
            result.append(dict(a))
    return result


def _get_bank_accounts(supplier):
    try:
        rows = frappe.get_all("Bank Account",
            filters={"party_type": "Supplier", "party": supplier},
            fields=["name", "account_name", "bank", "bank_account_no",
                    "branch_code", "iban", "is_default"])
        return [dict(r) for r in rows]
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════════════════
#  NOTIFICATION HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _get_supplier_email(supplier):
    if frappe.db.has_column("Supplier", "ec_portal_user"):
        email = frappe.db.get_value("Supplier", supplier, "ec_portal_user")
        if email:
            return email
    result = frappe.db.sql("""
        SELECT c.email_id FROM `tabContact` c
        JOIN `tabDynamic Link` dl ON dl.parent = c.name
        WHERE dl.link_doctype='Supplier' AND dl.link_name=%s
          AND c.email_id IS NOT NULL AND c.email_id != ''
        LIMIT 1
    """, supplier, as_dict=True)
    return result[0].email_id if result else None


def _send(to, subject, body, ref_dt=None, ref_name=None):
    if not to:
        return
    try:
        frappe.sendmail(recipients=[to], subject=subject, message=body,
                        reference_doctype=ref_dt, reference_name=ref_name, now=True)
    except Exception as e:
        frappe.log_error(f"Supplier Portal email: {e}", "Supplier Portal Notifications")


def _url():
    return f"{frappe.utils.get_url()}/supplier-portal"


def _fmt(amount, currency=""):
    return f"{currency} {flt(amount):,.2f}".strip()


def _row(label, value):
    return f"<tr><td style='padding:6px 0;color:#64748b'>{label}</td><td><strong>{value}</strong></td></tr>"


# ══════════════════════════════════════════════════════════════════════════════
#  DOC EVENT HOOKS
# ══════════════════════════════════════════════════════════════════════════════

def on_rfq_submit(doc, method=None):
    try:
        for sup_row in doc.suppliers:
            email = _get_supplier_email(sup_row.supplier)
            if not email:
                continue
            _send(email,
                f"Request for Quotation {doc.name} — Please Respond by {doc.schedule_date or 'ASAP'}",
                f"""<p>Dear {sup_row.supplier_name or sup_row.supplier},</p>
<p>We invite you to submit a quotation for RFQ <strong>{doc.name}</strong>.</p>
<table style="border-collapse:collapse;width:100%;max-width:480px">
  {_row('RFQ No.', doc.name)}
  {_row('Date', doc.transaction_date)}
  {_row('Required By', doc.schedule_date or '—')}
  {_row('Items', str(len(doc.items)) + ' item(s)')}
</table>
{f"<p style='margin-top:12px;font-style:italic'>{doc.message_for_supplier}</p>" if doc.message_for_supplier else ""}
<p style="margin-top:20px"><a href="{_url()}" style="background:#0a5c3a;color:white;padding:10px 20px;border-radius:6px;text-decoration:none">Submit Quotation</a></p>""",
                ref_dt="Request for Quotation", ref_name=doc.name)
    except Exception as e:
        frappe.log_error(f"on_rfq_submit: {e}", "Supplier Portal Notifications")


def on_rfq_cancel(doc, method=None):
    try:
        for sup_row in doc.suppliers:
            email = _get_supplier_email(sup_row.supplier)
            if not email:
                continue
            _send(email, f"RFQ {doc.name} Has Been Cancelled",
                f"<p>Dear {sup_row.supplier_name or sup_row.supplier},</p><p>RFQ <strong>{doc.name}</strong> has been cancelled.</p>",
                ref_dt="Request for Quotation", ref_name=doc.name)
    except Exception as e:
        frappe.log_error(f"on_rfq_cancel: {e}", "Supplier Portal Notifications")


def on_purchase_order_submit(doc, method=None):
    try:
        email = _get_supplier_email(doc.supplier)
        if not email:
            return
        _send(email,
            f"Purchase Order {doc.name} — Please Acknowledge",
            f"""<p>Dear {doc.supplier_name},</p>
<p>A Purchase Order has been issued to you. Please acknowledge receipt via the portal.</p>
<table style="border-collapse:collapse;width:100%;max-width:480px">
  {_row('PO No.', doc.name)}
  {_row('Date', doc.transaction_date)}
  {_row('Delivery Required By', doc.schedule_date or '—')}
  {_row('Order Value', _fmt(doc.grand_total, doc.currency))}
</table>
<p style="margin-top:20px"><a href="{_url()}" style="background:#0a5c3a;color:white;padding:10px 20px;border-radius:6px;text-decoration:none">View &amp; Acknowledge PO</a></p>""",
            ref_dt="Purchase Order", ref_name=doc.name)
    except Exception as e:
        frappe.log_error(f"on_purchase_order_submit: {e}", "Supplier Portal Notifications")


def on_purchase_order_cancel(doc, method=None):
    try:
        email = _get_supplier_email(doc.supplier)
        if not email:
            return
        _send(email, f"Purchase Order {doc.name} Cancelled",
            f"<p>Dear {doc.supplier_name},</p><p>PO <strong>{doc.name}</strong> for {_fmt(doc.grand_total, doc.currency)} has been cancelled.</p>",
            ref_dt="Purchase Order", ref_name=doc.name)
    except Exception as e:
        frappe.log_error(f"on_purchase_order_cancel: {e}", "Supplier Portal Notifications")


def on_purchase_receipt_submit(doc, method=None):
    try:
        email = _get_supplier_email(doc.supplier)
        if not email:
            return
        _send(email, f"Goods Received — {doc.name}",
            f"""<p>Dear {doc.supplier_name},</p>
<p>We have received your delivery and recorded it in our system.</p>
<table style="border-collapse:collapse;width:100%;max-width:480px">
  {_row('Receipt No.', doc.name)}
  {_row('Date', doc.posting_date)}
  {_row('Your Delivery Note', doc.supplier_delivery_note or '—')}
  {_row('Items Received', str(len(doc.items)))}
</table>
<p style="margin-top:20px"><a href="{_url()}" style="background:#0a5c3a;color:white;padding:10px 20px;border-radius:6px;text-decoration:none">View Receipt</a></p>""",
            ref_dt="Purchase Receipt", ref_name=doc.name)
    except Exception as e:
        frappe.log_error(f"on_purchase_receipt_submit: {e}", "Supplier Portal Notifications")


def on_purchase_invoice_submit(doc, method=None):
    try:
        if doc.is_return:
            return
        email = _get_supplier_email(doc.supplier)
        if not email:
            return
        _send(email, f"Invoice {doc.name} Processed — Payment Scheduled",
            f"""<p>Dear {doc.supplier_name},</p>
<p>Your invoice has been processed and payment will be made on the due date.</p>
<table style="border-collapse:collapse;width:100%;max-width:480px">
  {_row('Invoice No.', doc.name)}
  {_row('Your Bill No.', doc.bill_no or '—')}
  {_row('Due Date', doc.due_date or '—')}
  {_row('Amount Payable', _fmt(doc.grand_total, doc.currency))}
</table>
<p style="margin-top:20px"><a href="{_url()}" style="background:#0a5c3a;color:white;padding:10px 20px;border-radius:6px;text-decoration:none">View Invoice</a></p>""",
            ref_dt="Purchase Invoice", ref_name=doc.name)
    except Exception as e:
        frappe.log_error(f"on_purchase_invoice_submit: {e}", "Supplier Portal Notifications")


def on_payment_submit(doc, method=None):
    try:
        if doc.party_type != "Supplier":
            return
        email = _get_supplier_email(doc.party)
        if not email:
            return
        _send(email, f"Payment Sent — {_fmt(doc.paid_amount, doc.paid_to_account_currency)}",
            f"""<p>Dear {doc.party_name or doc.party},</p>
<p>A payment has been made to your account.</p>
<table style="border-collapse:collapse;width:100%;max-width:480px">
  {_row('Payment Ref.', doc.name)}
  {_row('Date', doc.posting_date)}
  {_row('Amount', _fmt(doc.paid_amount, doc.paid_to_account_currency))}
  {_row('Mode', doc.mode_of_payment or '—')}
  {_row('Reference', doc.reference_no or '—')}
</table>
<p style="margin-top:20px"><a href="{_url()}" style="background:#0a5c3a;color:white;padding:10px 20px;border-radius:6px;text-decoration:none">View Payment History</a></p>""",
            ref_dt="Payment Entry", ref_name=doc.name)
    except Exception as e:
        frappe.log_error(f"on_payment_submit (supplier): {e}", "Supplier Portal Notifications")


def on_quality_inspection_submit(doc, method=None):
    try:
        if doc.reference_type != "Purchase Receipt":
            return
        supplier = frappe.db.get_value("Purchase Receipt", doc.reference_name, "supplier")
        if not supplier:
            return
        email = _get_supplier_email(supplier)
        if not email:
            return
        passed = doc.status == "Accepted"
        _send(email,
            f"Quality Inspection {'Passed ✅' if passed else 'Failed ❌'} — {doc.name}",
            f"""<p>Dear Supplier,</p>
<p>The quality inspection for your delivery has been completed.</p>
<table style="border-collapse:collapse;width:100%;max-width:480px">
  {_row('QI No.', doc.name)}
  {_row('Item', doc.item_name or doc.item_code)}
  {_row('Receipt', doc.reference_name)}
  {_row('Result', f'<span style="color:{"#10b981" if passed else "#ef4444"};font-weight:700">{doc.status}</span>')}
</table>
{"<p style='color:#ef4444;margin-top:12px'>Please contact us regarding rejected items.</p>" if not passed else ""}
<p style="margin-top:20px"><a href="{_url()}" style="background:#0a5c3a;color:white;padding:10px 20px;border-radius:6px;text-decoration:none">View in Portal</a></p>""",
            ref_dt="Quality Inspection", ref_name=doc.name)
    except Exception as e:
        frappe.log_error(f"on_quality_inspection_submit: {e}", "Supplier Portal Notifications")


# ══════════════════════════════════════════════════════════════════════════════
#  SCHEDULED TASKS
# ══════════════════════════════════════════════════════════════════════════════

def send_rfq_expiry_reminders():
    try:
        closing_date = add_days(today(), 2)
        rfqs = frappe.get_all("Request for Quotation",
            filters={"status": "Open", "docstatus": 1, "schedule_date": closing_date},
            fields=["name", "schedule_date"])
        for rfq in rfqs:
            doc = frappe.get_doc("Request for Quotation", rfq.name)
            for sup_row in doc.suppliers:
                responded = frappe.db.exists("Supplier Quotation", {
                    "supplier": sup_row.supplier, "rfq_number": rfq.name, "docstatus": ["!=", 2]})
                if responded:
                    continue
                email = _get_supplier_email(sup_row.supplier)
                if not email:
                    continue
                _send(email, f"Reminder: RFQ {rfq.name} closes on {rfq.schedule_date}",
                    f"<p>Dear {sup_row.supplier_name or sup_row.supplier},</p>"
                    f"<p>RFQ <strong>{rfq.name}</strong> closes on <strong>{rfq.schedule_date}</strong>. "
                    f"Please submit your quotation before the deadline.</p>"
                    f"<p><a href='{_url()}'>Submit Quotation Now</a></p>",
                    ref_dt="Request for Quotation", ref_name=rfq.name)
    except Exception as e:
        frappe.log_error(f"send_rfq_expiry_reminders: {e}", "Supplier Portal Notifications")


def send_po_delivery_reminders():
    try:
        due_date = add_days(today(), 3)
        pos = frappe.get_all("Purchase Order",
            filters={"status": ["in", ["To Receive and Bill", "To Receive"]], "docstatus": 1, "schedule_date": due_date},
            fields=["name", "supplier", "supplier_name", "schedule_date", "grand_total", "currency"])
        for po in pos:
            email = _get_supplier_email(po.supplier)
            if not email:
                continue
            _send(email, f"Delivery Reminder — PO {po.name} due {po.schedule_date}",
                f"<p>Dear {po.supplier_name},</p>"
                f"<p>PO <strong>{po.name}</strong> for <strong>{_fmt(po.grand_total, po.currency)}</strong> "
                f"is due for delivery on <strong>{po.schedule_date}</strong>.</p>"
                f"<p><a href='{_url()}'>View PO in Portal</a></p>",
                ref_dt="Purchase Order", ref_name=po.name)
    except Exception as e:
        frappe.log_error(f"send_po_delivery_reminders: {e}", "Supplier Portal Notifications")


def send_weekly_supplier_summary():
    try:
        suppliers = frappe.db.sql("""
            SELECT DISTINCT ec_portal_user AS email, name AS supplier, supplier_name
            FROM `tabSupplier`
            WHERE ec_portal_user IS NOT NULL AND ec_portal_user != '' AND disabled = 0
        """, as_dict=True)

        for row in suppliers:
            supplier, email = row.supplier, row.email
            if not email:
                continue
            open_pos = frappe.db.count("Purchase Order", {
                "supplier": supplier, "docstatus": 1,
                "status": ["in", ["To Receive and Bill", "To Receive", "To Bill"]]})
            open_rfqs = frappe.db.sql("""
                SELECT COUNT(DISTINCT rfq.name) FROM `tabRequest for Quotation` rfq
                JOIN `tabRequest for Quotation Supplier` s ON s.parent = rfq.name
                WHERE s.supplier = %s AND rfq.status = 'Open' AND rfq.docstatus = 1
            """, supplier)[0][0]
            total_payable = frappe.db.sql("""
                SELECT COALESCE(SUM(outstanding_amount),0) FROM `tabPurchase Invoice`
                WHERE supplier = %s AND docstatus = 1 AND outstanding_amount > 0
            """, supplier)[0][0]
            currency = frappe.db.get_value("Supplier", supplier, "default_currency") or \
                       frappe.defaults.get_global_default("currency") or ""
            if not any([open_pos, open_rfqs, total_payable]):
                continue
            _send(email, f"Weekly Supplier Summary — {row.supplier_name}",
                f"""<p>Dear {row.supplier_name},</p>
<table style="border-collapse:collapse;width:100%;max-width:400px">
  {_row('Open Purchase Orders', open_pos)}
  {_row('Open RFQs Awaiting Response', open_rfqs)}
  {_row('Total Payable to You', _fmt(total_payable, currency))}
</table>
<p style="margin-top:20px"><a href="{_url()}" style="background:#0a5c3a;color:white;padding:10px 20px;border-radius:6px;text-decoration:none">Go to Supplier Portal</a></p>""")
    except Exception as e:
        frappe.log_error(f"send_weekly_supplier_summary: {e}", "Supplier Portal Notifications")