# apps/your_app/your_app/ap_validation.py

import frappe
from frappe import _
from frappe.utils import flt, today


def get_ap_account(company):
    """Fetch the default Accounts Payable account for the company."""
    ap_account = frappe.db.get_value(
        "Company", company, "default_payable_account"
    )
    if not ap_account:
        frappe.throw(_("Default Payable Account not set for company {0}").format(company))
    return ap_account


def get_gl_balance_for_supplier(account, party, company, as_of_date=None):
    """
    Returns net GL balance (credit - debit) for a specific supplier
    against the AP account. Suppliers are credit-normal.
    This is what Trial Balance shows for payables.
    """
    result = frappe.db.sql("""
        SELECT
            COALESCE(SUM(credit - debit), 0) AS balance
        FROM `tabGL Entry`
        WHERE
            account = %(account)s
            AND party_type = 'Supplier'
            AND party = %(party)s
            AND company = %(company)s
            AND is_cancelled = 0
            {date_filter}
    """.format(
        date_filter="AND posting_date <= %(as_of_date)s" if as_of_date else ""
    ), {
        "account": account,
        "party": party,
        "company": company,
        "as_of_date": as_of_date
    }, as_dict=True)

    return flt(result[0].balance if result else 0)


def get_outstanding_from_purchase_invoices(party, company, as_of_date=None):
    """
    Returns sum of outstanding_amount from submitted, unpaid/partially-paid
    Purchase Invoices. This is what AP Aging shows.
    """
    result = frappe.db.sql("""
        SELECT COALESCE(SUM(outstanding_amount), 0) AS outstanding
        FROM `tabPurchase Invoice`
        WHERE
            supplier = %(party)s
            AND company = %(company)s
            AND docstatus = 1
            AND outstanding_amount != 0
            {date_filter}
    """.format(
        date_filter="AND posting_date <= %(as_of_date)s" if as_of_date else ""
    ), {
        "party": party,
        "company": company,
        "as_of_date": as_of_date
    }, as_dict=True)

    return flt(result[0].outstanding if result else 0)


# ─── Hook: Purchase Invoice Submit ────────────────────────────────────────────

def validate_ap_gl_on_submit(doc, method):
    """
    After a Purchase Invoice submits, the GL credit for this invoice
    must equal the invoice's grand_total (rounded).
    Catches misconfigured account mappings and deferred expense issues early.
    """
    ap_account = get_ap_account(doc.company)

    gl_for_this_doc = frappe.db.sql("""
        SELECT COALESCE(SUM(credit - debit), 0) AS net
        FROM `tabGL Entry`
        WHERE
            voucher_type = 'Purchase Invoice'
            AND voucher_no = %(voucher_no)s
            AND account = %(account)s
            AND is_cancelled = 0
    """, {"voucher_no": doc.name, "account": ap_account}, as_dict=True)

    gl_net = flt(gl_for_this_doc[0].net if gl_for_this_doc else 0, doc.precision("grand_total"))
    expected = flt(doc.grand_total, doc.precision("grand_total"))

    if abs(gl_net - expected) > 0.5:
        frappe.throw(_(
            "AP Integrity Check Failed on {0}: "
            "GL entry to Payable account shows {1} but invoice grand total is {2}. "
            "Check your accounts mapping or deferred expense settings."
        ).format(doc.name, gl_net, expected))


def validate_ap_gl_on_cancel(doc, method):
    """
    On cancellation, verify the reversal GL entry zeroes out
    the original AP impact. Prevents dangling outstanding_amount on supplier ledger.
    """
    ap_account = get_ap_account(doc.company)

    net_after_cancel = frappe.db.sql("""
        SELECT COALESCE(SUM(credit - debit), 0) AS net
        FROM `tabGL Entry`
        WHERE
            voucher_type = 'Purchase Invoice'
            AND voucher_no = %(voucher_no)s
            AND account = %(account)s
    """, {"voucher_no": doc.name, "account": ap_account}, as_dict=True)

    net = flt(net_after_cancel[0].net if net_after_cancel else 0)

    if abs(net) > 0.01:
        frappe.log_error(
            title="AP Cancel Integrity Warning",
            message=_(
                "Cancelled Purchase Invoice {0} has a non-zero net GL balance of {1} "
                "in account {2}. Manual review required."
            ).format(doc.name, net, ap_account)
        )


# ─── Hook: Payment Entry Submit ───────────────────────────────────────────────

def validate_payment_ap_integrity(doc, method):
    """
    When a Payment Entry is submitted for a supplier, verify that each allocated
    invoice's GL debit matches the allocated amount.
    Catches partial-allocation bugs on the payable side.
    """
    if doc.party_type != "Supplier":
        return

    ap_account = get_ap_account(doc.company)
    tolerance = 0.5

    for row in doc.get("references", []):
        if row.reference_doctype != "Purchase Invoice":
            continue

        # AP is credited on invoice, debited on payment — so net credit reduction
        gl_allocated = frappe.db.sql("""
            SELECT COALESCE(SUM(debit - credit), 0) AS net
            FROM `tabGL Entry`
            WHERE
                voucher_type = 'Payment Entry'
                AND voucher_no = %(pe_name)s
                AND account = %(account)s
                AND against_voucher = %(inv)s
                AND is_cancelled = 0
        """, {
            "pe_name": doc.name,
            "account": ap_account,
            "inv": row.reference_name
        }, as_dict=True)

        gl_net = flt(gl_allocated[0].net if gl_allocated else 0)
        expected = flt(row.allocated_amount)

        if abs(gl_net - expected) > tolerance:
            frappe.throw(_(
                "Payment Allocation Mismatch on {0} for purchase invoice {1}: "
                "GL shows {2} but allocated amount is {3}. "
                "Re-check payment reconciliation."
            ).format(doc.name, row.reference_name, gl_net, expected))


# ─── Scheduled: Nightly Reconciliation Check ──────────────────────────────────

def nightly_ap_reconciliation_check():
    """
    Nightly job: for every active supplier with GL movement in the last 90 days,
    compare GL balance vs outstanding purchase invoices. Log discrepancies.
    """
    companies = frappe.get_all("Company", pluck="name")

    for company in companies:
        try:
            _check_company_ap(company)
        except Exception:
            frappe.log_error(
                title="AP Reconciliation Check Error",
                message=frappe.get_traceback()
            )


def _check_company_ap(company):
    ap_account = frappe.db.get_value("Company", company, "default_payable_account")
    if not ap_account:
        return

    # Suppliers with GL activity in last 90 days
    active_suppliers = frappe.db.sql("""
        SELECT DISTINCT party
        FROM `tabGL Entry`
        WHERE
            account = %(account)s
            AND party_type = 'Supplier'
            AND company = %(company)s
            AND is_cancelled = 0
            AND posting_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
    """, {"account": ap_account, "company": company}, as_dict=True)

    discrepancies = []

    for row in active_suppliers:
        supplier = row.party

        gl_balance = get_gl_balance_for_supplier(ap_account, supplier, company)
        outstanding = get_outstanding_from_purchase_invoices(supplier, company)

        variance = flt(gl_balance - outstanding, 2)

        if abs(variance) > 1.0:  # ₦1 tolerance
            discrepancies.append({
                "supplier": supplier,
                "gl_balance": gl_balance,
                "invoice_outstanding": outstanding,
                "variance": variance,
            })

    if discrepancies:
        msg_lines = ["AP vs Outstanding Discrepancies for {0}:\n".format(company)]
        for d in discrepancies:
            msg_lines.append(
                "  Supplier: {supplier} | GL Balance: {gl_balance:,.2f} | "
                "Invoice Outstanding: {invoice_outstanding:,.2f} | "
                "Variance: {variance:,.2f}".format(**d)
            )

        frappe.log_error(
            title="AP Reconciliation Variance — {0}".format(company),
            message="\n".join(msg_lines)
        )

        # Create a ToDo for Accounts Manager
        accounts_manager = frappe.db.get_value(
            "Has Role",
            {"role": "Accounts Manager", "parenttype": "User"},
            "parent"
        )
        if accounts_manager:
            frappe.get_doc({
                "doctype": "ToDo",
                "owner": accounts_manager,
                "description": "AP Reconciliation variance detected for {0}. Check Error Log.".format(company),
                "priority": "High",
                "date": today(),
            }).insert(ignore_permissions=True)

        frappe.db.commit()