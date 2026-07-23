# apps/ecclesia/ecclesia/item_validation.py

import frappe
from frappe import _
from frappe.utils import flt, cint, today


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_sle_balance(item_code, warehouse, company, as_of_date=None):
    """
    Compute actual_qty and stock_value directly from Stock Ledger Entry.
    This is the ground truth — what Trial Balance stock valuation is based on.
    """
    result = frappe.db.sql("""
        SELECT
            COALESCE(SUM(actual_qty), 0)   AS actual_qty,
            COALESCE(SUM(stock_value_difference), 0) AS stock_value
        FROM `tabStock Ledger Entry`
        WHERE
            item_code  = %(item_code)s
            AND warehouse  = %(warehouse)s
            AND company    = %(company)s
            AND is_cancelled = 0
            {date_filter}
    """.format(
        date_filter="AND posting_date <= %(as_of_date)s" if as_of_date else ""
    ), {
        "item_code":  item_code,
        "warehouse":  warehouse,
        "company":    company,
        "as_of_date": as_of_date,
    }, as_dict=True)

    row = result[0] if result else {}
    return flt(row.get("actual_qty")), flt(row.get("stock_value"))


def get_bin_balance(item_code, warehouse):
    """
    Read the cached Bin record.
    This is what ERPNext shows in stock balance reports.
    """
    result = frappe.db.get_value(
        "Bin",
        {"item_code": item_code, "warehouse": warehouse},
        ["actual_qty", "stock_value"],
        as_dict=True,
    )
    if not result:
        return 0.0, 0.0
    return flt(result.actual_qty), flt(result.stock_value)


def _qty_precision():
    return cint(frappe.db.get_single_value("System Settings", "float_precision") or 3)


# ─── Hook: Stock Entry Submit ─────────────────────────────────────────────────

def validate_stock_entry_gl_on_submit(doc, method):
    """
    On Stock Entry submit, verify that every SLE created for this voucher
    has a matching GL Entry for valuation (for perpetual inventory companies).
    Catches missing GL postings from stock transactions early.
    """
    company = doc.company
    if not _is_perpetual_inventory(company):
        return

    # Each item row that moves stock should have a GL entry
    sle_items = frappe.db.sql("""
        SELECT item_code, warehouse,
               SUM(actual_qty) AS qty,
               SUM(stock_value_difference) AS val_diff
        FROM `tabStock Ledger Entry`
        WHERE
            voucher_type = 'Stock Entry'
            AND voucher_no   = %(voucher_no)s
            AND is_cancelled = 0
        GROUP BY item_code, warehouse
    """, {"voucher_no": doc.name}, as_dict=True)

    if not sle_items:
        frappe.throw(_(
            "Stock Integrity Check Failed on {0}: "
            "No Stock Ledger Entries found after submit. "
            "Check your item valuation settings."
        ).format(doc.name))

    # Verify total GL stock impact equals total SLE value difference
    stock_accounts = _get_stock_accounts(company)
    if not stock_accounts:
        return

    gl_stock_impact = frappe.db.sql("""
        SELECT COALESCE(SUM(debit - credit), 0) AS net
        FROM `tabGL Entry`
        WHERE
            voucher_type = 'Stock Entry'
            AND voucher_no   = %(voucher_no)s
            AND account      IN %(accounts)s
            AND is_cancelled = 0
    """, {"voucher_no": doc.name, "accounts": stock_accounts}, as_dict=True)

    gl_net   = flt(gl_stock_impact[0].net if gl_stock_impact else 0, 2)
    sle_val  = flt(sum(r.val_diff for r in sle_items), 2)

    # For internal transfers net GL impact on stock accounts should be 0
    # For consumption/production it should match sle_val
    if doc.stock_entry_type not in ("Material Transfer", "Material Transfer for Manufacture"):
        if abs(gl_net - sle_val) > 1.0:
            frappe.log_error(
                title="Stock Entry GL Mismatch",
                message=_(
                    "Stock Entry {0}: SLE value difference is {1} but GL stock "
                    "account impact is {2}. Variance: {3}. "
                    "Review valuation method or account mapping."
                ).format(doc.name, sle_val, gl_net, flt(gl_net - sle_val, 2))
            )


# ─── Hook: Purchase Receipt Submit ────────────────────────────────────────────

def validate_purchase_receipt_stock_on_submit(doc, method):
    """
    On GRN submit, verify that received_qty in each item row
    matches the SLE created for this voucher.
    Catches quantity discrepancies between document and stock posting.
    """
    for item in doc.get("items", []):
        if not item.warehouse:
            continue

        sle_qty = frappe.db.sql("""
            SELECT COALESCE(SUM(actual_qty), 0) AS qty
            FROM `tabStock Ledger Entry`
            WHERE
                voucher_type = 'Purchase Receipt'
                AND voucher_no   = %(voucher_no)s
                AND item_code    = %(item_code)s
                AND warehouse    = %(warehouse)s
                AND is_cancelled = 0
        """, {
            "voucher_no": doc.name,
            "item_code":  item.item_code,
            "warehouse":  item.warehouse,
        }, as_dict=True)

        sle_actual = flt(sle_qty[0].qty if sle_qty else 0)
        # Use received_qty instead of accepted_qty
        expected   = flt(item.received_qty)

        if abs(sle_actual - expected) > 0.001:
            frappe.throw(_(
                "Stock Integrity Check Failed on {0}, Item {1}: "
                "SLE shows qty {2} but received_qty on document is {3}. "
                "Contact system administrator."
            ).format(doc.name, item.item_code, sle_actual, expected))


# ─── Hook: Delivery Note Submit ───────────────────────────────────────────────

def validate_delivery_note_stock_on_submit(doc, method):
    """
    On Delivery Note submit, verify that qty delivered matches
    the negative SLE (stock reduction) created for this voucher.
    """
    for item in doc.get("items", []):
        if not item.warehouse:
            continue

        sle_qty = frappe.db.sql("""
            SELECT COALESCE(SUM(actual_qty), 0) AS qty
            FROM `tabStock Ledger Entry`
            WHERE
                voucher_type = 'Delivery Note'
                AND voucher_no   = %(voucher_no)s
                AND item_code    = %(item_code)s
                AND warehouse    = %(warehouse)s
                AND is_cancelled = 0
        """, {
            "voucher_no": doc.name,
            "item_code":  item.item_code,
            "warehouse":  item.warehouse,
        }, as_dict=True)

        sle_actual = flt(sle_qty[0].qty if sle_qty else 0)
        # Delivery reduces stock → SLE qty is negative
        expected = flt(item.qty) * -1

        if abs(sle_actual - expected) > 0.001:
            frappe.throw(_(
                "Stock Integrity Check Failed on {0}, Item {1}: "
                "SLE shows qty {2} but delivered qty is {3}. "
                "Contact system administrator."
            ).format(doc.name, item.item_code, sle_actual, abs(expected)))


# ─── Hook: Stock Entry / Purchase Receipt / Delivery Note Cancel ──────────────

def validate_stock_cancel_integrity(doc, method):
    """
    On cancel, verify the reversal SLE zeroes out the original stock impact.
    Prevents ghost stock from incomplete cancellations.
    """
    voucher_type_map = {
        "Stock Entry":      "Stock Entry",
        "Purchase Receipt": "Purchase Receipt",
        "Delivery Note":    "Delivery Note",
    }
    voucher_type = voucher_type_map.get(doc.doctype)
    if not voucher_type:
        return

    net_qty = frappe.db.sql("""
        SELECT COALESCE(SUM(actual_qty), 0) AS net_qty
        FROM `tabStock Ledger Entry`
        WHERE
            voucher_type = %(voucher_type)s
            AND voucher_no   = %(voucher_no)s
    """, {"voucher_type": voucher_type, "voucher_no": doc.name}, as_dict=True)

    net = flt(net_qty[0].net_qty if net_qty else 0)

    if abs(net) > 0.001:
        frappe.log_error(
            title="Stock Cancel Integrity Warning",
            message=_(
                "Cancelled {0} {1} has a non-zero net SLE qty of {2}. "
                "Manual stock reconciliation may be required."
            ).format(doc.doctype, doc.name, net)
        )


# ─── Scheduled: Nightly Bin vs SLE Reconciliation ─────────────────────────────

def nightly_item_reconciliation_check():
    """
    Nightly job: for every active Bin with SLE movement in last 90 days,
    compare Bin.actual_qty and Bin.stock_value against SLE aggregates.
    Logs discrepancies and creates a ToDo for the Stock Manager.
    """
    companies = frappe.get_all("Company", pluck="name")

    for company in companies:
        try:
            _check_company_stock(company)
        except Exception:
            frappe.log_error(
                title="Item Reconciliation Check Error",
                message=frappe.get_traceback()
            )


def _check_company_stock(company):
    # Active item-warehouse combinations with SLE movement in last 90 days
    active_bins = frappe.db.sql("""
        SELECT DISTINCT item_code, warehouse
        FROM `tabStock Ledger Entry`
        WHERE
            company      = %(company)s
            AND is_cancelled = 0
            AND posting_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
    """, {"company": company}, as_dict=True)

    if not active_bins:
        return

    discrepancies = []

    for row in active_bins:
        sle_qty, sle_val   = get_sle_balance(row.item_code, row.warehouse, company)
        bin_qty, bin_val   = get_bin_balance(row.item_code, row.warehouse)

        qty_variance = flt(sle_qty - bin_qty, 3)
        val_variance = flt(sle_val - bin_val, 2)

        if abs(qty_variance) > 0.001 or abs(val_variance) > 1.0:
            discrepancies.append({
                "item_code":    row.item_code,
                "warehouse":    row.warehouse,
                "sle_qty":      sle_qty,
                "bin_qty":      bin_qty,
                "qty_variance": qty_variance,
                "sle_val":      sle_val,
                "bin_val":      bin_val,
                "val_variance": val_variance,
            })

    if not discrepancies:
        return

    msg_lines = ["Bin vs SLE Discrepancies for {0}:\n".format(company)]
    for d in discrepancies:
        msg_lines.append(
            "  Item: {item_code} | Warehouse: {warehouse} | "
            "SLE Qty: {sle_qty} | Bin Qty: {bin_qty} | Qty Var: {qty_variance} | "
            "SLE Val: {sle_val:,.2f} | Bin Val: {bin_val:,.2f} | Val Var: {val_variance:,.2f}"
            .format(**d)
        )

    frappe.log_error(
        title="Item/Stock Reconciliation Variance — {0}".format(company),
        message="\n".join(msg_lines)
    )

    # Create ToDo for Stock Manager
    stock_manager = frappe.db.get_value(
        "Has Role",
        {"role": "Stock Manager", "parenttype": "User"},
        "parent"
    )
    if stock_manager:
        frappe.get_doc({
            "doctype":     "ToDo",
            "owner":       stock_manager,
            "description": (
                "Stock Bin vs SLE reconciliation variance detected for {0}. "
                "Check Error Log for details."
            ).format(company),
            "priority":    "High",
            "date":        today(),
        }).insert(ignore_permissions=True)

    frappe.db.commit()


# ─── Script Report ─────────────────────────────────────────────────────────────
# Report Name:  Item vs SLE Reconciliation
# Type:         Script Report
# Ref Doctype:  Stock Ledger Entry

def execute(filters=None):
    filters   = filters or {}
    company   = filters.get("company") or frappe.defaults.get_user_default("Company")
    as_of_date = filters.get("as_of_date") or frappe.utils.today()
    warehouse = filters.get("warehouse")

    columns = [
        {"label": _("Item Code"),        "fieldname": "item_code",     "fieldtype": "Link",
         "options": "Item",              "width": 160},
        {"label": _("Item Name"),        "fieldname": "item_name",     "fieldtype": "Data",    "width": 160},
        {"label": _("Warehouse"),        "fieldname": "warehouse",     "fieldtype": "Link",
         "options": "Warehouse",         "width": 160},
        {"label": _("SLE Qty"),          "fieldname": "sle_qty",       "fieldtype": "Float",   "width": 100},
        {"label": _("Bin Qty"),          "fieldname": "bin_qty",       "fieldtype": "Float",   "width": 100},
        {"label": _("Qty Variance"),     "fieldname": "qty_variance",  "fieldtype": "Float",   "width": 110},
        {"label": _("SLE Value"),        "fieldname": "sle_val",       "fieldtype": "Currency","width": 130},
        {"label": _("Bin Value"),        "fieldname": "bin_val",       "fieldtype": "Currency","width": 130},
        {"label": _("Value Variance"),   "fieldname": "val_variance",  "fieldtype": "Currency","width": 130},
        {"label": _("Status"),           "fieldname": "status",        "fieldtype": "Data",    "width": 100},
    ]

    warehouse_filter = "AND sle.warehouse = %(warehouse)s" if warehouse else ""

    active_bins = frappe.db.sql("""
        SELECT DISTINCT sle.item_code, sle.warehouse
        FROM `tabStock Ledger Entry` sle
        WHERE
            sle.company      = %(company)s
            AND sle.is_cancelled = 0
            AND sle.posting_date <= %(as_of_date)s
            {warehouse_filter}
    """.format(warehouse_filter=warehouse_filter), {
        "company":    company,
        "as_of_date": as_of_date,
        "warehouse":  warehouse,
    }, as_dict=True)

    # Item names lookup
    item_names = {
        r.name: r.item_name
        for r in frappe.get_all(
            "Item",
            filters={"name": ["in", list({r.item_code for r in active_bins})]},
            fields=["name", "item_name"]
        )
    } if active_bins else {}

    data = []
    for row in active_bins:
        sle_qty, sle_val = get_sle_balance(row.item_code, row.warehouse, company, as_of_date)
        bin_qty, bin_val = get_bin_balance(row.item_code, row.warehouse)

        qty_var = flt(sle_qty - bin_qty, 3)
        val_var = flt(sle_val - bin_val, 2)

        data.append({
            "item_code":    row.item_code,
            "item_name":    item_names.get(row.item_code, ""),
            "warehouse":    row.warehouse,
            "sle_qty":      sle_qty,
            "bin_qty":      bin_qty,
            "qty_variance": qty_var,
            "sle_val":      sle_val,
            "bin_val":      bin_val,
            "val_variance": val_var,
            "status":       "✅ Match" if abs(qty_var) <= 0.001 and abs(val_var) <= 1.0 else "⚠️ Variance",
        })

    data.sort(key=lambda x: abs(x["val_variance"]), reverse=True)
    return columns, data


# ─── Internal Helpers ─────────────────────────────────────────────────────────

def _is_perpetual_inventory(company):
    return frappe.db.get_value("Company", company, "enable_perpetual_inventory")


def _get_stock_accounts(company):
    accounts = frappe.get_all(
        "Account",
        filters={
            "account_type": "Stock",
            "company":      company,
            "disabled":     0,
        },
        pluck="name"
    )
    return tuple(accounts) if accounts else None