

import frappe
from frappe.utils import flt

@frappe.whitelist()
def get_customer_opening_balance(customer, company, transaction_date, current_docname=None):
    """
    Get customer AR balance BEFORE the current Receipts document.
    Excludes the current document to avoid double-counting.
    """

    # Get the receivable account for this customer/company
    receivable_account = frappe.get_value(
        'Company', company, 'default_receivable_account'
    )

    if not receivable_account:
        frappe.throw('Default Receivable Account not set for Company: {}'.format(company))

    # Build exclusion filter for current document
    exclude_filter = ""
    if current_docname:
        exclude_filter = "AND gle.voucher_no != %(current_docname)s"

    # Query GL Entry: sum all debit - credit for this customer
    # up to (but NOT including) the current transaction_date entries
    # for this specific document
    balance = frappe.db.sql("""
        SELECT 
            SUM(gle.debit) - SUM(gle.credit) AS balance
        FROM 
            `tabGL Entry` gle
        WHERE
            gle.party_type = 'Customer'
            AND gle.party = %(customer)s
            AND gle.company = %(company)s
            AND gle.account = %(receivable_account)s
            AND gle.is_cancelled = 0
            AND (
                gle.posting_date < %(transaction_date)s
                OR (
                    gle.posting_date = %(transaction_date)s
                    {exclude_filter}
                )
            )
    """.format(exclude_filter=exclude_filter), {
        'customer': customer,
        'company': company,
        'receivable_account': receivable_account,
        'transaction_date': transaction_date,
        'current_docname': current_docname
    }, as_dict=True)

    return flt(balance[0].get('balance')) if balance else 0.0