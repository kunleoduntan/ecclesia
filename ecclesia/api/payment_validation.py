# apps/general/general/api/payment_validation.py

import frappe
from frappe import _
from frappe.utils import flt


def _get_ar_account(company):
    account = frappe.db.get_value("Company", company, "default_receivable_account")
    if not account:
        frappe.throw(_("Default Receivable Account not set for company {0}").format(company))
    return account


def _get_ap_account(company):
    account = frappe.db.get_value("Company", company, "default_payable_account")
    if not account:
        frappe.throw(_("Default Payable Account not set for company {0}").format(company))
    return account


def validate_payment_ar_integrity(doc, method):
    """
    On Payment Entry submit for a Customer:
    Verify each allocated Sales Invoice GL credit matches the allocated amount.
    Catches partial-allocation bugs on the receivable side.
    """
    if doc.party_type != "Customer":
        return

    ar_account = _get_ar_account(doc.company)
    tolerance  = 0.5
    errors     = []

    for row in doc.get("references", []):
        if row.reference_doctype != "Sales Invoice":
            continue

        gl = frappe.db.sql("""
            SELECT COALESCE(SUM(credit - debit), 0) AS net
            FROM `tabGL Entry`
            WHERE
                voucher_type    = 'Payment Entry'
                AND voucher_no      = %(pe)s
                AND account         = %(account)s
                AND against_voucher = %(inv)s
                AND is_cancelled    = 0
        """, {
            "pe":      doc.name,
            "account": ar_account,
            "inv":     row.reference_name,
        }, as_dict=True)

        gl_net   = flt(gl[0].net if gl else 0)
        expected = flt(row.allocated_amount)

        if abs(gl_net - expected) > tolerance:
            errors.append(_(
                "AR Mismatch — Invoice {0}: GL shows {1} but allocated amount is {2}."
            ).format(row.reference_name, gl_net, expected))

    if errors:
        frappe.throw(
            "\n".join(errors),
            title=_("Payment AR Integrity Check Failed on {0}").format(doc.name)
        )


def validate_payment_ap_integrity(doc, method):
    """
    On Payment Entry submit for a Supplier:
    Verify each allocated Purchase Invoice GL debit matches the allocated amount.
    Catches partial-allocation bugs on the payable side.
    """
    if doc.party_type != "Supplier":
        return

    ap_account = _get_ap_account(doc.company)
    tolerance  = 0.5
    errors     = []

    for row in doc.get("references", []):
        if row.reference_doctype != "Purchase Invoice":
            continue

        gl = frappe.db.sql("""
            SELECT COALESCE(SUM(debit - credit), 0) AS net
            FROM `tabGL Entry`
            WHERE
                voucher_type    = 'Payment Entry'
                AND voucher_no      = %(pe)s
                AND account         = %(account)s
                AND against_voucher = %(inv)s
                AND is_cancelled    = 0
        """, {
            "pe":      doc.name,
            "account": ap_account,
            "inv":     row.reference_name,
        }, as_dict=True)

        gl_net   = flt(gl[0].net if gl else 0)
        expected = flt(row.allocated_amount)

        if abs(gl_net - expected) > tolerance:
            errors.append(_(
                "AP Mismatch — Invoice {0}: GL shows {1} but allocated amount is {2}."
            ).format(row.reference_name, gl_net, expected))

    if errors:
        frappe.throw(
            "\n".join(errors),
            title=_("Payment AP Integrity Check Failed on {0}").format(doc.name)
        )