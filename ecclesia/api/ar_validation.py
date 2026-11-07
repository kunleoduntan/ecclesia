# apps/your_app/your_app/ar_validation.py

import frappe
from frappe import _
from frappe.utils import flt, today, getdate


def get_ar_account(company):
    """Fetch the default Accounts Receivable account for the company."""
    ar_account = frappe.db.get_value(
        "Company", company, "default_receivable_account"
    )
    if not ar_account:
        frappe.throw(_("Default Receivable Account not set for company {0}").format(company))
    return ar_account


def get_gl_balance_for_party(account, party, company, as_of_date=None):
    """
    Returns net GL balance (debit - credit) for a specific party
    against the AR account. This is what Trial Balance shows.
    """
    filters = {
        "account": account,
        "party_type": "Customer",
        "party": party,
        "company": company,
        "is_cancelled": 0,
    }
    if as_of_date:
        filters["posting_date"] = ("<=", as_of_date)

    result = frappe.db.sql("""
        SELECT
            COALESCE(SUM(debit - credit), 0) AS balance
        FROM `tabGL Entry`
        WHERE
            account = %(account)s
            AND party_type = 'Customer'
            AND party = %(party)s
            AND company = %(company)s
            AND is_cancelled = 0
            {date_filter}
    """.format(
        date_filter="AND posting_date <= %(as_of_date)s" if as_of_date else ""
    ), {**filters, "as_of_date": as_of_date}, as_dict=True)

    return flt(result[0].balance if result else 0)


def get_outstanding_from_invoices(party, company, as_of_date=None):
    """
    Returns sum of outstanding_amount from submitted, unpaid/partially-paid
    Sales Invoices. This is what AR Aging shows.
    """
    date_filter = "AND posting_date <= %(as_of_date)s" if as_of_date else ""
    result = frappe.db.sql("""
        SELECT COALESCE(SUM(outstanding_amount), 0) AS outstanding
        FROM `tabSales Invoice`
        WHERE
            customer = %(party)s
            AND company = %(company)s
            AND docstatus = 1
            AND outstanding_amount != 0
            {date_filter}
    """.format(date_filter=date_filter), {
        "party": party,
        "company": company,
        "as_of_date": as_of_date
    }, as_dict=True)

    return flt(result[0].outstanding if result else 0)


# ─── Hook: Sales Invoice Submit ───────────────────────────────────────────────

def validate_ar_gl_on_submit(doc, method):
    """The receivable posting for this invoice must equal its total.
    Gross side only, so an invoice paid on submit (POS) still passes."""
    ar_account = doc.debit_to or get_ar_account(doc.company)

    row = frappe.db.sql("""
        SELECT COALESCE(SUM(debit), 0) AS debit, COALESCE(SUM(credit), 0) AS credit
        FROM `tabGL Entry`
        WHERE voucher_type = 'Sales Invoice' AND voucher_no = %(v)s
          AND account = %(a)s AND is_cancelled = 0
    """, {"v": doc.name, "a": ar_account}, as_dict=True)[0]

    precision = doc.precision("base_grand_total")
    # Debit for a sale, credit for a return. GL is in company currency.
    posted = flt(row.credit if doc.is_return else row.debit, precision)
    expected = abs(flt(doc.base_rounded_total or doc.base_grand_total, precision))

    if abs(posted - expected) > 0.5:
        frappe.throw(_(
            "AR Integrity Check Failed on {0}: "
            "GL entry to Receivable account shows {1} but invoice grand total is {2}. "
            "Check your accounts mapping or deferred revenue settings."
        ).format(doc.name, posted, expected))
        

def validate_ar_gl_on_cancel(doc, method):
    """
    On cancellation, verify the reversal GL entry zeroes out
    the original AR impact. Prevents dangling outstanding_amount.
    """
    # ERPNext auto-reverses GL on cancel — but we verify it happened cleanly.
    ar_account = get_ar_account(doc.company)

    net_after_cancel = frappe.db.sql("""
        SELECT COALESCE(SUM(debit - credit), 0) AS net
        FROM `tabGL Entry`
        WHERE
            voucher_type = 'Sales Invoice'
            AND voucher_no = %(voucher_no)s
            AND account = %(account)s
    """, {"voucher_no": doc.name, "account": ar_account}, as_dict=True)

    net = flt(net_after_cancel[0].net if net_after_cancel else 0)

    if abs(net) > 0.01:
        frappe.log_error(
            title="AR Cancel Integrity Warning",
            message=_(
                "Cancelled Sales Invoice {0} has a non-zero net GL balance of {1} "
                "in account {2}. Manual review required."
            ).format(doc.name, net, ar_account)
        )


# ─── Hook: Payment Entry Submit ───────────────────────────────────────────────

def validate_payment_ar_integrity(doc, method):
    """
    When a Payment Entry is submitted, verify that each allocated invoice's
    GL credit matches the allocated amount. Catches partial-allocation bugs.
    """
    if doc.payment_type not in ("Receive", "Pay"):
        return
    if doc.party_type != "Customer":
        return

    ar_account = get_ar_account(doc.company)
    tolerance = 0.5

    for row in doc.get("references", []):
        if row.reference_doctype != "Sales Invoice":
            continue

        # What the GL was credited for this voucher against this invoice
        gl_allocated = frappe.db.sql("""
            SELECT COALESCE(SUM(credit - debit), 0) AS net
            FROM `tabGL Entry`
            WHERE
                voucher_type = 'Payment Entry'
                AND voucher_no = %(pe_name)s
                AND account = %(account)s
                AND against_voucher = %(inv)s
                AND is_cancelled = 0
        """, {
            "pe_name": doc.name,
            "account": ar_account,
            "inv": row.reference_name
        }, as_dict=True)

        gl_net = flt(gl_allocated[0].net if gl_allocated else 0)
        expected = flt(row.allocated_amount)

        if abs(gl_net - expected) > tolerance:
            frappe.throw(_(
                "Payment Allocation Mismatch on {0} for invoice {1}: "
                "GL shows {2} but allocated amount is {3}. "
                "Re-check payment reconciliation."
            ).format(doc.name, row.reference_name, gl_net, expected))


# ─── Hook: Journal Entry Submit ───────────────────────────────────────────────

def validate_jv_party_required(doc, method):
    """
    Any JV line posting to an AR/AP account MUST have party_type and party set.
    Missing party = silent TB vs ledger divergence.
    """
    receivable_accounts = frappe.get_all(
        "Account",
        filters={
            "account_type": "Receivable",
            "company": doc.company,
            "disabled": 0
        },
        pluck="name"
    )
    payable_accounts = frappe.get_all(
        "Account",
        filters={
            "account_type": "Payable",
            "company": doc.company,
            "disabled": 0
        },
        pluck="name"
    )
    controlled_accounts = set(receivable_accounts + payable_accounts)

    errors = []
    for i, row in enumerate(doc.get("accounts", []), start=1):
        if row.account in controlled_accounts:
            if not row.party_type or not row.party:
                errors.append(
                    _("Row {0}: Account '{1}' is a controlled receivable/payable account. "
                      "Party Type and Party are mandatory.").format(i, row.account)
                )

    if errors:
        frappe.throw("\n".join(errors), title=_("Party Required on AR/AP Account"))


# ─── Scheduled: Nightly Reconciliation Check ──────────────────────────────────

def nightly_ar_reconciliation_check():
    """
    Nightly job: for every active customer with GL movement in the last 90 days,
    compare GL balance vs outstanding invoices. Log discrepancies.
    """
    companies = frappe.get_all("Company", pluck="name")

    for company in companies:
        try:
            _check_company_ar(company)
        except Exception:
            frappe.log_error(
                title="AR Reconciliation Check Error",
                message=frappe.get_traceback()
            )


def _check_company_ar(company):
    ar_account = frappe.db.get_value("Company", company, "default_receivable_account")
    if not ar_account:
        return

    # Customers with GL activity in last 90 days
    active_customers = frappe.db.sql("""
        SELECT DISTINCT party
        FROM `tabGL Entry`
        WHERE
            account = %(account)s
            AND party_type = 'Customer'
            AND company = %(company)s
            AND is_cancelled = 0
            AND posting_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
    """, {"account": ar_account, "company": company}, as_dict=True)

    discrepancies = []

    for row in active_customers:
        customer = row.party

        gl_balance = get_gl_balance_for_party(ar_account, customer, company)
        outstanding = get_outstanding_from_invoices(customer, company)

        variance = flt(gl_balance - outstanding, 2)

        if abs(variance) > 1.0:  # ₦1 tolerance
            discrepancies.append({
                "customer": customer,
                "gl_balance": gl_balance,
                "invoice_outstanding": outstanding,
                "variance": variance,
            })

    if discrepancies:
        msg_lines = ["AR vs Outstanding Discrepancies for {0}:\n".format(company)]
        for d in discrepancies:
            msg_lines.append(
                "  Customer: {customer} | GL Balance: {gl_balance:,.2f} | "
                "Invoice Outstanding: {invoice_outstanding:,.2f} | "
                "Variance: {variance:,.2f}".format(**d)
            )

        frappe.log_error(
            title="AR Reconciliation Variance — {0}".format(company),
            message="\n".join(msg_lines)
        )

        # Also create a ToDo for the Finance Manager
        finance_manager = frappe.db.get_value(
            "Has Role",
            {"role": "Accounts Manager", "parenttype": "User"},
            "parent"
        )
        if finance_manager:
            frappe.get_doc({
                "doctype": "ToDo",
                "owner": finance_manager,
                "description": "AR Reconciliation variance detected for {0}. Check Error Log.".format(company),
                "priority": "High",
                "date": today(),
            }).insert(ignore_permissions=True)

        frappe.db.commit()