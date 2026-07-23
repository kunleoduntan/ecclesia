# Report: AR vs TB Reconciliation
# Type: Script Report
# Ref Doctype: GL Entry

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    filters = filters or {}
    company = filters.get("company") or frappe.defaults.get_user_default("Company")
    as_of_date = filters.get("as_of_date") or frappe.utils.today()

    ar_account = frappe.db.get_value("Company", company, "default_receivable_account")
    if not ar_account:
        frappe.throw(_("No default receivable account set."))

    columns = [
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link",
         "options": "Customer", "width": 200},
        {"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 160},
        {"label": _("GL Balance (Trial Balance)"), "fieldname": "gl_balance",
         "fieldtype": "Currency", "width": 160},
        {"label": _("Invoice Outstanding"), "fieldname": "invoice_outstanding",
         "fieldtype": "Currency", "width": 160},
        {"label": _("Variance"), "fieldname": "variance",
         "fieldtype": "Currency", "width": 120},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
    ]

    # All customers with AR GL entries
    gl_balances = frappe.db.sql("""
        SELECT
            party AS customer,
            SUM(debit - credit) AS gl_balance
        FROM `tabGL Entry`
        WHERE
            account = %(account)s
            AND party_type = 'Customer'
            AND company = %(company)s
            AND is_cancelled = 0
            AND posting_date <= %(as_of_date)s
        GROUP BY party
        HAVING SUM(debit - credit) != 0
    """, {
        "account": ar_account,
        "company": company,
        "as_of_date": as_of_date
    }, as_dict=True)

    # Outstanding from invoices
    outstanding_map = {}
    if gl_balances:
        customers = [r.customer for r in gl_balances]
        inv_data = frappe.db.sql("""
            SELECT
                customer,
                SUM(outstanding_amount) AS outstanding
            FROM `tabSales Invoice`
            WHERE
                customer IN %(customers)s
                AND company = %(company)s
                AND docstatus = 1
                AND posting_date <= %(as_of_date)s
            GROUP BY customer
        """, {
            "customers": customers,
            "company": company,
            "as_of_date": as_of_date
        }, as_dict=True)

        for r in inv_data:
            outstanding_map[r.customer] = flt(r.outstanding)

    # Customer names
    cust_names = {
        r.name: r.customer_name
        for r in frappe.get_all(
            "Customer",
            filters={"name": ["in", [r.customer for r in gl_balances]]},
            fields=["name", "customer_name"]
        )
    }

    data = []
    for row in sorted(gl_balances, key=lambda x: x.customer):
        gl = flt(row.gl_balance, 2)
        outstanding = flt(outstanding_map.get(row.customer, 0), 2)
        variance = flt(gl - outstanding, 2)

        data.append({
            "customer": row.customer,
            "customer_name": cust_names.get(row.customer, ""),
            "gl_balance": gl,
            "invoice_outstanding": outstanding,
            "variance": variance,
            "status": "✅ Match" if abs(variance) <= 1.0 else "⚠️ Variance",
        })

    # Sort: variances first
    data.sort(key=lambda x: abs(x["variance"]), reverse=True)

    return columns, data