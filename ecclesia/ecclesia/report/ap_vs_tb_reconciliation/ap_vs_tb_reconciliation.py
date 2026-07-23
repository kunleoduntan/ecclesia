# Report: AP vs TB Reconciliation
# Type: Script Report
# Ref Doctype: GL Entry

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    filters = filters or {}
    company = filters.get("company") or frappe.defaults.get_user_default("Company")
    as_of_date = filters.get("as_of_date") or frappe.utils.today()

    ap_account = frappe.db.get_value("Company", company, "default_payable_account")
    if not ap_account:
        frappe.throw(_("No default payable account set."))

    columns = [
        {"label": _("Supplier"), "fieldname": "supplier", "fieldtype": "Link",
         "options": "Supplier", "width": 200},
        {"label": _("Supplier Name"), "fieldname": "supplier_name",
         "fieldtype": "Data", "width": 160},
        {"label": _("GL Balance (Trial Balance)"), "fieldname": "gl_balance",
         "fieldtype": "Currency", "width": 170},
        {"label": _("Invoice Outstanding"), "fieldname": "invoice_outstanding",
         "fieldtype": "Currency", "width": 160},
        {"label": _("Variance"), "fieldname": "variance",
         "fieldtype": "Currency", "width": 120},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
    ]

    # All suppliers with AP GL entries up to as_of_date
    gl_balances = frappe.db.sql("""
        SELECT
            party AS supplier,
            SUM(credit - debit) AS gl_balance
        FROM `tabGL Entry`
        WHERE
            account = %(account)s
            AND party_type = 'Supplier'
            AND company = %(company)s
            AND is_cancelled = 0
            AND posting_date <= %(as_of_date)s
        GROUP BY party
        HAVING SUM(credit - debit) != 0
    """, {
        "account": ap_account,
        "company": company,
        "as_of_date": as_of_date
    }, as_dict=True)

    # Outstanding from purchase invoices
    outstanding_map = {}
    if gl_balances:
        suppliers = [r.supplier for r in gl_balances]
        inv_data = frappe.db.sql("""
            SELECT
                supplier,
                SUM(outstanding_amount) AS outstanding
            FROM `tabPurchase Invoice`
            WHERE
                supplier IN %(suppliers)s
                AND company = %(company)s
                AND docstatus = 1
                AND posting_date <= %(as_of_date)s
            GROUP BY supplier
        """, {
            "suppliers": suppliers,
            "company": company,
            "as_of_date": as_of_date
        }, as_dict=True)

        for r in inv_data:
            outstanding_map[r.supplier] = flt(r.outstanding)

    # Supplier names
    supp_names = {
        r.name: r.supplier_name
        for r in frappe.get_all(
            "Supplier",
            filters={"name": ["in", [r.supplier for r in gl_balances]]},
            fields=["name", "supplier_name"]
        )
    }

    data = []
    for row in gl_balances:
        gl = flt(row.gl_balance, 2)
        outstanding = flt(outstanding_map.get(row.supplier, 0), 2)
        variance = flt(gl - outstanding, 2)

        data.append({
            "supplier": row.supplier,
            "supplier_name": supp_names.get(row.supplier, ""),
            "gl_balance": gl,
            "invoice_outstanding": outstanding,
            "variance": variance,
            "status": "✅ Match" if abs(variance) <= 1.0 else "⚠️ Variance",
        })

    # Sort: worst variances first
    data.sort(key=lambda x: abs(x["variance"]), reverse=True)

    return columns, data