# Copyright (c) 2026, Kunle Oduntan / Value Impacts Consulting
# ecclesia/ecclesia/page/ap_ar_check/ap_ar_check.py
#
# ═══════════════════════════════════════════════════════════════════════════════
#  AP / AR CHECK — Backend Engine
#  All methods are @frappe.whitelist() and called directly from the JS page.
#
#  CHECK CATEGORIES
#  ─────────────────
#  AR (Accounts Receivable — Customer):
#    1.  Unbalanced AR — SI submitted but no matching GL debit on Debtor account
#    2.  Payment without invoice — Payment Entry has no linked SI
#    3.  Overpayment — total receipts exceed invoice outstanding
#    4.  Duplicate invoice — same customer, same amount, same date (±1 day)
#    5.  Credit note without original — credit note references cancelled/missing SI
#    6.  Outstanding > credit limit — customer outstanding exceeds credit_limit
#    7.  SI submitted but not delivered — Delivery Note still draft/pending
#    8.  Stale outstanding — SI unpaid beyond payment_terms due date
#
#  AP (Accounts Payable — Supplier):
#    9.  Unbalanced AP — PI submitted but no matching GL credit on Creditor account
#    10. Payment without bill — Payment Entry has no linked PI
#    11. Overpayment to supplier — total payments exceed bill outstanding
#    12. Duplicate bill — same supplier, same amount, same date (±1 day)
#    13. Bill without PO — PI has no purchase_order reference
#    14. Bill amount > PO amount — PI grand_total exceeds linked PO grand_total
#    15. Quality inspection missing — PI submitted but no QI linked to receipt
#    16. Stale payable — PI unpaid beyond due date
#
#  CROSS-CHECKS:
#    CX-01a. Journal Entry lines on AR control account with no Customer party tag
#    CX-01b. AR control account net GL balance ≠ sum of customer outstanding (sub-ledger)
#    CX-02a. Journal Entry lines on AP control account with no Supplier party tag
#    CX-02b. AP control account net GL balance ≠ sum of supplier outstanding (sub-ledger)
#    CX-03a. Journal Entry lines posted directly to Stock/COGS control accounts
#    CX-04.  Payment Entry allocated amount ≠ linked document outstanding
# ═══════════════════════════════════════════════════════════════════════════════

import frappe
from frappe import _
from frappe.utils import flt, cint, getdate, nowdate, date_diff, add_days
import json


# ─── helpers ──────────────────────────────────────────────────────────────────

def _sf(v, p=2):
    return round(flt(v or 0), p)

def _date(v):
    try:
        return getdate(v)
    except Exception:
        return None

def _escape(v):
    return frappe.db.escape(str(v)) if v else "''"

def _company_filter(company, alias=None):
    col = f"{alias}.company" if alias else "company"
    return f"AND {col} = {_escape(company)}" if company else ""

def _date_filter(from_date, to_date, field="posting_date"):
    parts = []
    if from_date:
        parts.append(f"{field} >= {_escape(from_date)}")
    if to_date:
        parts.append(f"{field} <= {_escape(to_date)}")
    return ("AND " + " AND ".join(parts)) if parts else ""

# Keep the old alias helper for backward compatibility in SQL that uses it
def _company_filter_alias(company, alias):
    return _company_filter(company, alias)


# ═══════════════════════════════════════════════════════════════════════════════
#  MASTER RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def run_check(from_date, to_date, company=None, check_scope="Both",
              severity_filter="All", party_filter=None):
    """
    Run all selected checks and return a flat list of mismatch rows
    plus summary statistics.

    Returns:
        {
          "rows":    [ { ...mismatch fields... } ],
          "summary": { total, critical, high, medium, low, ar_count, ap_count },
          "meta":    { from_date, to_date, company, ran_at, duration_ms }
        }
    """
    import time
    t0 = time.time()

    rows = []

    run_ar = check_scope in ("Both", "AR Only")
    run_ap = check_scope in ("Both", "AP Only")

    if run_ar:
        rows += _check_ar_gl_balance(from_date, to_date, company)
        rows += _check_ar_payment_without_invoice(from_date, to_date, company)
        rows += _check_ar_overpayment(from_date, to_date, company)
        rows += _check_ar_duplicate_invoices(from_date, to_date, company)
        rows += _check_ar_credit_note_orphan(from_date, to_date, company)
        rows += _check_ar_credit_limit_breach(from_date, to_date, company)
        rows += _check_ar_invoice_no_delivery(from_date, to_date, company)
        rows += _check_ar_stale_outstanding(from_date, to_date, company)

    if run_ap:
        rows += _check_ap_gl_balance(from_date, to_date, company)
        rows += _check_ap_payment_without_bill(from_date, to_date, company)
        rows += _check_ap_overpayment(from_date, to_date, company)
        rows += _check_ap_duplicate_bills(from_date, to_date, company)
        rows += _check_ap_bill_without_po(from_date, to_date, company)
        rows += _check_ap_bill_exceeds_po(from_date, to_date, company)
        rows += _check_ap_missing_quality_inspection(from_date, to_date, company)
        rows += _check_ap_stale_payable(from_date, to_date, company)
        rows += _check_ap_supplier_credit_limit_breach(from_date, to_date, company)

    if run_ar and run_ap:
        rows += _check_gl_control_account_reconciliation(from_date, to_date, company)
        rows += _check_payment_allocation_mismatch(from_date, to_date, company)

    # Apply party filter
    if party_filter:
        rows = [r for r in rows if party_filter.lower() in
                (r.get("party") or "").lower()]

    # Apply severity filter
    if severity_filter != "All":
        rows = [r for r in rows if r.get("severity") == severity_filter]

    # Assign row numbers
    for i, r in enumerate(rows, 1):
        r["row_number"] = i

    # Summary
    ar_rows = [r for r in rows if r.get("check_type") == "AR"]
    ap_rows = [r for r in rows if r.get("check_type") == "AP"]
    cx_rows = [r for r in rows if r.get("check_type") == "Cross"]

    summary = {
        "total":        len(rows),
        "critical":     sum(1 for r in rows if r.get("severity") == "Critical"),
        "high":         sum(1 for r in rows if r.get("severity") == "High"),
        "medium":       sum(1 for r in rows if r.get("severity") == "Medium"),
        "low":          sum(1 for r in rows if r.get("severity") == "Low"),
        "ar_count":     len(ar_rows),
        "ap_count":     len(ap_rows),
        "cross_count":  len(cx_rows),
        "total_impact": _sf(sum(flt(r.get("impact_amount") or 0) for r in rows)),
        "ar_impact":    _sf(sum(flt(r.get("impact_amount") or 0) for r in ar_rows)),
        "ap_impact":    _sf(sum(flt(r.get("impact_amount") or 0) for r in ap_rows)),
    }

    duration_ms = round((time.time() - t0) * 1000)

    return {
        "rows":    rows,
        "summary": summary,
        "meta": {
            "from_date":   from_date,
            "to_date":     to_date,
            "company":     company or "All",
            "ran_at":      frappe.utils.now(),
            "duration_ms": duration_ms,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  AR CHECK FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _check_ar_gl_balance(from_date, to_date, company):
    """
    AR-01: SI submitted but GL debit on the Debtor/Receivable account is
    missing or does not match.  Checks each individual Sales Invoice.
    """
    rows = []
    df = _date_filter(from_date, to_date)
    cf = _company_filter(company)

    invoices = frappe.db.sql(f"""
        SELECT si.name, si.customer, si.grand_total, si.posting_date,
               si.outstanding_amount, si.currency
        FROM `tabSales Invoice` si
        WHERE si.docstatus = 1 {df} {cf}
        AND si.grand_total > 0
    """, as_dict=True)

    for inv in invoices:
        gl_debit = frappe.db.sql("""
            SELECT COALESCE(SUM(debit - credit), 0) AS net
            FROM `tabGL Entry`
            WHERE voucher_no = %s AND voucher_type = 'Sales Invoice'
              AND party_type = 'Customer' AND party = %s
              AND is_cancelled = 0
        """, (inv.name, inv.customer), as_dict=True)

        net      = _sf(gl_debit[0].net if gl_debit else 0)
        expected = _sf(inv.grand_total)
        diff     = _sf(abs(net - expected))

        if diff > 0.01:
            rows.append(_row(
                check_type="AR",
                check_code="AR-01",
                check_name="AR GL Imbalance",
                severity="Critical",
                document_type="Sales Invoice",
                document=inv.name,
                party_type="Customer",
                party=inv.customer,
                posting_date=str(inv.posting_date),
                description=(
                    f"SI grand_total ₦{expected:,.2f} but GL net debit "
                    f"is ₦{net:,.2f} — difference ₦{diff:,.2f}"
                ),
                impact_amount=diff,
                recommendation=(
                    "Reconcile GL entries — check if on_submit GL hook failed. "
                    "Re-save or cancel/re-submit the invoice."
                ),
            ))
    return rows


def _check_ar_payment_without_invoice(from_date, to_date, company):
    """AR-02: Payment Entry (receive) with no allocated Sales Invoice."""
    rows = []
    df = _date_filter(from_date, to_date)
    cf = _company_filter(company)

    payments = frappe.db.sql(f"""
        SELECT pe.name, pe.party, pe.paid_amount, pe.posting_date,
               pe.paid_from_account_currency
        FROM `tabPayment Entry` pe
        WHERE pe.payment_type = 'Receive'
          AND pe.docstatus = 1
          AND pe.party_type = 'Customer'
          {_date_filter(from_date, to_date, field='pe.posting_date')}
          {_company_filter(company, alias='pe')}
    """, as_dict=True)

    for p in payments:
        alloc = frappe.db.sql("""
            SELECT COALESCE(SUM(allocated_amount), 0) AS total
            FROM `tabPayment Entry Reference`
            WHERE parent = %s AND reference_doctype = 'Sales Invoice'
        """, (p.name,), as_dict=True)

        total_alloc = _sf(alloc[0].total if alloc else 0)
        unalloc     = _sf(flt(p.paid_amount) - total_alloc)

        if unalloc > 0.01:
            rows.append(_row(
                check_type="AR",
                check_code="AR-02",
                check_name="Unallocated Customer Receipt",
                severity="High",
                document_type="Payment Entry",
                document=p.name,
                party_type="Customer",
                party=p.party,
                posting_date=str(p.posting_date),
                description=(
                    f"Receipt of ₦{_sf(p.paid_amount):,.2f} — "
                    f"₦{unalloc:,.2f} not allocated to any Sales Invoice"
                ),
                impact_amount=unalloc,
                recommendation=(
                    "Allocate the unallocated amount in Payment Entry → References tab. "
                    "If advance payment, ensure it is linked to future invoices."
                ),
            ))
    return rows


def _check_ar_overpayment(from_date, to_date, company):
    """AR-03: Total receipts allocated to an SI exceed the invoice grand_total."""
    rows = []
    df = _date_filter(from_date, to_date)
    cf = _company_filter(company)

    invoices = frappe.db.sql(f"""
        SELECT name, customer, grand_total, posting_date
        FROM `tabSales Invoice`
        WHERE docstatus = 1 {df} {cf}
        AND grand_total > 0
    """, as_dict=True)

    for inv in invoices:
        total_paid = frappe.db.sql("""
            SELECT COALESCE(SUM(per.allocated_amount), 0) AS total
            FROM `tabPayment Entry Reference` per
            JOIN `tabPayment Entry` pe ON pe.name = per.parent
            WHERE per.reference_doctype = 'Sales Invoice'
              AND per.reference_name = %s
              AND pe.docstatus = 1
        """, (inv.name,), as_dict=True)

        paid  = _sf(total_paid[0].total if total_paid else 0)
        excess = _sf(paid - flt(inv.grand_total))

        if excess > 0.01:
            rows.append(_row(
                check_type="AR",
                check_code="AR-03",
                check_name="Customer Overpayment",
                severity="High",
                document_type="Sales Invoice",
                document=inv.name,
                party_type="Customer",
                party=inv.customer,
                posting_date=str(inv.posting_date),
                description=(
                    f"Overpayment of ₦{excess:,.2f} — invoice "
                    f"₦{_sf(inv.grand_total):,.2f}, total receipts ₦{paid:,.2f}"
                ),
                impact_amount=excess,
                recommendation=(
                    "Issue a credit note for the excess or refund the customer. "
                    "Verify no duplicate payment was posted."
                ),
            ))
    return rows


def _check_ar_duplicate_invoices(from_date, to_date, company):
    """AR-04: Same customer, same amount, posting dates within 1 day of each other."""
    rows = []

    dupes = frappe.db.sql(f"""
        SELECT a.name AS doc1, b.name AS doc2,
               a.customer, a.grand_total, a.posting_date
        FROM `tabSales Invoice` a
        JOIN `tabSales Invoice` b
          ON a.customer = b.customer
         AND ABS(a.grand_total - b.grand_total) < 1
         AND ABS(DATEDIFF(a.posting_date, b.posting_date)) <= 1
         AND a.name < b.name
        WHERE a.docstatus = 1 AND b.docstatus = 1
          {_date_filter(from_date, to_date, field='a.posting_date')}
          {_company_filter(company, alias='a')}
    """, as_dict=True)

    seen = set()
    for d in dupes:
        key = (d.doc1, d.doc2)
        if key in seen:
            continue
        seen.add(key)
        rows.append(_row(
            check_type="AR",
            check_code="AR-04",
            check_name="Possible Duplicate Invoice",
            severity="Medium",
            document_type="Sales Invoice",
            document=d.doc1,
            party_type="Customer",
            party=d.customer,
            posting_date=str(d.posting_date),
            description=(
                f"Possible duplicate: {d.doc1} and {d.doc2} — same customer, "
                f"same amount ₦{_sf(d.grand_total):,.2f}, dates within 1 day"
            ),
            impact_amount=_sf(d.grand_total),
            recommendation=(
                f"Review {d.doc1} and {d.doc2} — cancel one if it is a duplicate entry. "
                "Verify Sales Order reference is different."
            ),
        ))
    return rows


def _check_ar_credit_note_orphan(from_date, to_date, company):
    """AR-05: Credit note (return invoice) with no valid original SI."""
    rows = []
    df = _date_filter(from_date, to_date)
    cf = _company_filter(company)

    returns = frappe.db.sql(f"""
        SELECT name, customer, grand_total, posting_date, return_against
        FROM `tabSales Invoice`
        WHERE docstatus = 1 AND is_return = 1 {df} {cf}
    """, as_dict=True)

    for r in returns:
        if not r.return_against:
            rows.append(_row(
                check_type="AR",
                check_code="AR-05",
                check_name="Orphan Credit Note",
                severity="Medium",
                document_type="Sales Invoice",
                document=r.name,
                party_type="Customer",
                party=r.customer,
                posting_date=str(r.posting_date),
                description="Credit note has no 'return_against' reference — original invoice not linked",
                impact_amount=_sf(r.grand_total),
                recommendation=(
                    "Edit the credit note and set the Return Against field "
                    "to the original Sales Invoice."
                ),
            ))
        else:
            orig_status = frappe.db.get_value(
                "Sales Invoice", r.return_against, "docstatus"
            )
            if orig_status is None:
                rows.append(_row(
                    check_type="AR",
                    check_code="AR-05",
                    check_name="Orphan Credit Note",
                    severity="High",
                    document_type="Sales Invoice",
                    document=r.name,
                    party_type="Customer",
                    party=r.customer,
                    posting_date=str(r.posting_date),
                    description=(
                        f"Return Against = {r.return_against} which does not exist"
                    ),
                    impact_amount=_sf(r.grand_total),
                    recommendation=(
                        "Original invoice appears deleted. "
                        "Manually reconcile the credit note in GL."
                    ),
                ))
    return rows


def _check_ar_credit_limit_breach(from_date, to_date, company):
    """
    AR-06: Customer outstanding > credit limit defined in the Customer Credit
    Limit child table (tabCustomer Credit Limit — fields: parent, parenttype,
    company, credit_limit).
    """
    rows = []
    company_clause = f"AND ccl.company = {_escape(company)}" if company else ""

    credit_limit_rows = frappe.db.sql(f"""
        SELECT
            ccl.parent          AS customer,
            c.customer_name,
            ccl.company,
            ccl.credit_limit
        FROM `tabCustomer Credit Limit` ccl
        JOIN `tabCustomer` c ON c.name = ccl.parent
        WHERE ccl.parenttype = 'Customer'
          AND ccl.credit_limit > 0
          {company_clause}
    """, as_dict=True)

    for cl in credit_limit_rows:
        outstanding = frappe.db.sql("""
            SELECT COALESCE(SUM(outstanding_amount), 0) AS total
            FROM `tabSales Invoice`
            WHERE customer = %s AND docstatus = 1
              AND outstanding_amount > 0 AND company = %s
        """, (cl.customer, cl.company), as_dict=True)

        outs   = _sf(outstanding[0].total if outstanding else 0)
        limit  = _sf(cl.credit_limit)
        excess = _sf(outs - limit)

        if excess > 0.01:
            rows.append(_row(
                check_type="AR",
                check_code="AR-06",
                check_name="Credit Limit Breach",
                severity="High",
                document_type="Customer",
                document=cl.customer,
                party_type="Customer",
                party=cl.customer,
                posting_date=nowdate(),
                description=(
                    f"{cl.customer_name} [{cl.company}] — outstanding "
                    f"₦{outs:,.2f} exceeds credit limit ₦{limit:,.2f} "
                    f"by ₦{excess:,.2f}"
                ),
                impact_amount=excess,
                recommendation=(
                    "Put customer account on hold or escalate for collection. "
                    "Consider reducing credit limit or requiring upfront payment."
                ),
            ))
    return rows


def _check_ar_invoice_no_delivery(from_date, to_date, company):
    """AR-07: SI submitted but no Delivery Note — for physical goods."""
    rows = []
    df = _date_filter(from_date, to_date)
    cf = _company_filter(company)

    invoices = frappe.db.sql(f"""
        SELECT si.name, si.customer, si.grand_total, si.posting_date
        FROM `tabSales Invoice` si
        WHERE si.docstatus = 1 {df} {cf}
          AND si.update_stock = 0
          AND EXISTS (
              SELECT 1 FROM `tabSales Invoice Item` sii
              WHERE sii.parent = si.name AND sii.delivery_note IS NULL
              AND EXISTS (
                  SELECT 1 FROM `tabItem` i
                  WHERE i.name = sii.item_code AND i.is_stock_item = 1
              )
          )
    """, as_dict=True)

    for inv in invoices:
        has_dn = frappe.db.sql("""
            SELECT 1 FROM `tabDelivery Note Item` dni
            JOIN `tabDelivery Note` dn ON dn.name = dni.parent
            WHERE dni.against_sales_invoice = %s AND dn.docstatus = 1
            LIMIT 1
        """, (inv.name,))

        if not has_dn:
            rows.append(_row(
                check_type="AR",
                check_code="AR-07",
                check_name="Invoice Without Delivery",
                severity="Medium",
                document_type="Sales Invoice",
                document=inv.name,
                party_type="Customer",
                party=inv.customer,
                posting_date=str(inv.posting_date),
                description=(
                    f"Stock items invoiced but no submitted Delivery Note "
                    f"found for {inv.name}"
                ),
                impact_amount=_sf(inv.grand_total),
                recommendation=(
                    "Create and submit the Delivery Note, or verify if "
                    "update_stock should be enabled on the invoice."
                ),
            ))
    return rows


def _check_ar_stale_outstanding(from_date, to_date, company):
    """AR-08: SI unpaid past due date."""
    rows = []
    cf = _company_filter(company)
    today = getdate(nowdate())

    invoices = frappe.db.sql(f"""
        SELECT si.name, si.customer, si.outstanding_amount,
               si.posting_date, si.due_date, si.payment_terms_template
        FROM `tabSales Invoice` si
        WHERE si.docstatus = 1
          AND si.outstanding_amount > 0.01
          AND si.due_date < CURDATE()
          AND si.due_date >= %s
          {cf}
    """, (from_date,), as_dict=True)

    for inv in invoices:
        due          = getdate(inv.due_date) if inv.due_date else getdate(inv.posting_date)
        days_overdue = date_diff(today, due)
        severity     = "Critical" if days_overdue > 90 else "High" if days_overdue > 60 else "Medium"

        rows.append(_row(
            check_type="AR",
            check_code="AR-08",
            check_name="Stale Outstanding",
            severity=severity,
            document_type="Sales Invoice",
            document=inv.name,
            party_type="Customer",
            party=inv.customer,
            posting_date=str(inv.posting_date),
            description=(
                f"Overdue {days_overdue} days — outstanding "
                f"₦{_sf(inv.outstanding_amount):,.2f}, due date {inv.due_date}"
            ),
            impact_amount=_sf(inv.outstanding_amount),
            recommendation=(
                f"Escalate to collections. {days_overdue} days overdue. "
                "Consider legal notice if > 90 days."
            ),
        ))
    return rows


# ═══════════════════════════════════════════════════════════════════════════════
#  AP CHECK FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _check_ap_gl_balance(from_date, to_date, company):
    """AP-01: PI submitted but GL credit on Creditor account missing or mismatched."""
    rows = []
    df = _date_filter(from_date, to_date)
    cf = _company_filter(company)

    bills = frappe.db.sql(f"""
        SELECT name, supplier, grand_total, posting_date, currency
        FROM `tabPurchase Invoice`
        WHERE docstatus = 1 {df} {cf}
        AND grand_total > 0 AND is_return = 0
    """, as_dict=True)

    for bill in bills:
        gl = frappe.db.sql("""
            SELECT COALESCE(SUM(credit - debit), 0) AS net
            FROM `tabGL Entry`
            WHERE voucher_no = %s AND voucher_type = 'Purchase Invoice'
              AND party_type = 'Supplier' AND party = %s
              AND is_cancelled = 0
        """, (bill.name, bill.supplier), as_dict=True)

        net      = _sf(gl[0].net if gl else 0)
        expected = _sf(bill.grand_total)
        diff     = _sf(abs(net - expected))

        if diff > 0.01:
            rows.append(_row(
                check_type="AP",
                check_code="AP-01",
                check_name="AP GL Imbalance",
                severity="Critical",
                document_type="Purchase Invoice",
                document=bill.name,
                party_type="Supplier",
                party=bill.supplier,
                posting_date=str(bill.posting_date),
                description=(
                    f"PI grand_total ₦{expected:,.2f} but GL net credit "
                    f"is ₦{net:,.2f} — difference ₦{diff:,.2f}"
                ),
                impact_amount=diff,
                recommendation=(
                    "Reconcile GL entries — check if on_submit GL hook failed. "
                    "Re-save or cancel/re-submit the bill."
                ),
            ))
    return rows


def _check_ap_payment_without_bill(from_date, to_date, company):
    """AP-02: Payment Entry (pay) with no allocated Purchase Invoice."""
    rows = []

    payments = frappe.db.sql(f"""
        SELECT pe.name, pe.party, pe.paid_amount, pe.posting_date
        FROM `tabPayment Entry` pe
        WHERE pe.payment_type = 'Pay'
          AND pe.docstatus = 1
          AND pe.party_type = 'Supplier'
          {_date_filter(from_date, to_date, field='pe.posting_date')}
          {_company_filter(company, alias='pe')}
    """, as_dict=True)

    for p in payments:
        alloc = frappe.db.sql("""
            SELECT COALESCE(SUM(allocated_amount), 0) AS total
            FROM `tabPayment Entry Reference`
            WHERE parent = %s AND reference_doctype = 'Purchase Invoice'
        """, (p.name,), as_dict=True)

        total_alloc = _sf(alloc[0].total if alloc else 0)
        unalloc     = _sf(flt(p.paid_amount) - total_alloc)

        if unalloc > 0.01:
            rows.append(_row(
                check_type="AP",
                check_code="AP-02",
                check_name="Unallocated Supplier Payment",
                severity="High",
                document_type="Payment Entry",
                document=p.name,
                party_type="Supplier",
                party=p.party,
                posting_date=str(p.posting_date),
                description=(
                    f"Payment of ₦{_sf(p.paid_amount):,.2f} — "
                    f"₦{unalloc:,.2f} not allocated to any Purchase Invoice"
                ),
                impact_amount=unalloc,
                recommendation=(
                    "Allocate the unallocated amount to the correct Purchase Invoice "
                    "in the References tab."
                ),
            ))
    return rows


def _check_ap_overpayment(from_date, to_date, company):
    """AP-03: Total payments to supplier exceed PI grand_total."""
    rows = []
    df = _date_filter(from_date, to_date)
    cf = _company_filter(company)

    bills = frappe.db.sql(f"""
        SELECT name, supplier, grand_total, posting_date
        FROM `tabPurchase Invoice`
        WHERE docstatus = 1 {df} {cf}
        AND grand_total > 0 AND is_return = 0
    """, as_dict=True)

    for bill in bills:
        total_paid = frappe.db.sql("""
            SELECT COALESCE(SUM(per.allocated_amount), 0) AS total
            FROM `tabPayment Entry Reference` per
            JOIN `tabPayment Entry` pe ON pe.name = per.parent
            WHERE per.reference_doctype = 'Purchase Invoice'
              AND per.reference_name = %s AND pe.docstatus = 1
        """, (bill.name,), as_dict=True)

        paid  = _sf(total_paid[0].total if total_paid else 0)
        excess = _sf(paid - flt(bill.grand_total))

        if excess > 0.01:
            rows.append(_row(
                check_type="AP",
                check_code="AP-03",
                check_name="Supplier Overpayment",
                severity="High",
                document_type="Purchase Invoice",
                document=bill.name,
                party_type="Supplier",
                party=bill.supplier,
                posting_date=str(bill.posting_date),
                description=(
                    f"Overpayment of ₦{excess:,.2f} — bill "
                    f"₦{_sf(bill.grand_total):,.2f}, total payments ₦{paid:,.2f}"
                ),
                impact_amount=excess,
                recommendation=(
                    "Contact supplier for credit note or refund. "
                    "Verify no duplicate payment was made."
                ),
            ))
    return rows


def _check_ap_duplicate_bills(from_date, to_date, company):
    """AP-04: Same supplier, same amount, dates within 1 day."""
    rows = []

    dupes = frappe.db.sql(f"""
        SELECT a.name AS doc1, b.name AS doc2,
               a.supplier, a.grand_total, a.posting_date
        FROM `tabPurchase Invoice` a
        JOIN `tabPurchase Invoice` b
          ON a.supplier = b.supplier
         AND ABS(a.grand_total - b.grand_total) < 1
         AND ABS(DATEDIFF(a.posting_date, b.posting_date)) <= 1
         AND a.name < b.name
        WHERE a.docstatus = 1 AND b.docstatus = 1
          AND a.is_return = 0 AND b.is_return = 0
          {_date_filter(from_date, to_date, field='a.posting_date')}
          {_company_filter(company, alias='a')}
    """, as_dict=True)

    seen = set()
    for d in dupes:
        key = (d.doc1, d.doc2)
        if key in seen:
            continue
        seen.add(key)
        rows.append(_row(
            check_type="AP",
            check_code="AP-04",
            check_name="Possible Duplicate Bill",
            severity="Medium",
            document_type="Purchase Invoice",
            document=d.doc1,
            party_type="Supplier",
            party=d.supplier,
            posting_date=str(d.posting_date),
            description=(
                f"Possible duplicate: {d.doc1} and {d.doc2} — same supplier, "
                f"same amount ₦{_sf(d.grand_total):,.2f}, dates within 1 day"
            ),
            impact_amount=_sf(d.grand_total),
            recommendation=(
                f"Check supplier bill numbers on {d.doc1} and {d.doc2}. "
                "Cancel the duplicate to avoid double-payment."
            ),
        ))
    return rows


def _check_ap_bill_without_po(from_date, to_date, company):
    """AP-05: PI submitted with no Purchase Order reference."""
    rows = []
    df = _date_filter(from_date, to_date)
    cf = _company_filter(company)

    bills = frappe.db.sql(f"""
        SELECT pi.name, pi.supplier, pi.grand_total, pi.posting_date
        FROM `tabPurchase Invoice` pi
        WHERE pi.docstatus = 1 {df} {cf}
          AND pi.is_return = 0
          AND NOT EXISTS (
              SELECT 1 FROM `tabPurchase Invoice Item` pii
              WHERE pii.parent = pi.name AND pii.purchase_order IS NOT NULL
              LIMIT 1
          )
    """, as_dict=True)

    for bill in bills:
        rows.append(_row(
            check_type="AP",
            check_code="AP-05",
            check_name="Bill Without Purchase Order",
            severity="Medium",
            document_type="Purchase Invoice",
            document=bill.name,
            party_type="Supplier",
            party=bill.supplier,
            posting_date=str(bill.posting_date),
            description=(
                f"Purchase Invoice {bill.name} (₦{_sf(bill.grand_total):,.2f}) "
                "has no Purchase Order reference"
            ),
            impact_amount=_sf(bill.grand_total),
            recommendation=(
                "Ensure all supplier bills have a matching Purchase Order. "
                "Request retroactive PO approval if valid."
            ),
        ))
    return rows


def _check_ap_bill_exceeds_po(from_date, to_date, company):
    """AP-06: PI amount exceeds the linked PO amount."""
    rows = []

    overruns = frappe.db.sql(f"""
        SELECT pi.name, pi.supplier, pi.grand_total AS bill_amt,
               po.grand_total AS po_amt, po.name AS po_name,
               pi.posting_date
        FROM `tabPurchase Invoice` pi
        JOIN `tabPurchase Invoice Item` pii ON pii.parent = pi.name
        JOIN `tabPurchase Order` po ON po.name = pii.purchase_order
        WHERE pi.docstatus = 1 AND po.docstatus = 1
          AND pi.grand_total > po.grand_total + 1
          AND pi.is_return = 0
          {_date_filter(from_date, to_date, field='pi.posting_date')}
          {_company_filter(company, alias='pi')}
        GROUP BY pi.name
    """, as_dict=True)

    for r in overruns:
        excess = _sf(flt(r.bill_amt) - flt(r.po_amt))
        rows.append(_row(
            check_type="AP",
            check_code="AP-06",
            check_name="Bill Exceeds PO Value",
            severity="High",
            document_type="Purchase Invoice",
            document=r.name,
            party_type="Supplier",
            party=r.supplier,
            posting_date=str(r.posting_date),
            description=(
                f"Bill ₦{_sf(r.bill_amt):,.2f} exceeds PO {r.po_name} "
                f"value ₦{_sf(r.po_amt):,.2f} by ₦{excess:,.2f}"
            ),
            impact_amount=excess,
            recommendation=(
                "Amend the PO to cover the excess or reject the invoice. "
                "Obtain management approval for the variance."
            ),
        ))
    return rows


def _check_ap_missing_quality_inspection(from_date, to_date, company):
    """AP-07: PI submitted but linked Purchase Receipt has no Quality Inspection."""
    rows = []
    df = _date_filter(from_date, to_date)
    cf = _company_filter(company)

    bills = frappe.db.sql(f"""
        SELECT pi.name, pi.supplier, pi.grand_total, pi.posting_date
        FROM `tabPurchase Invoice` pi
        WHERE pi.docstatus = 1 {df} {cf}
          AND pi.is_return = 0
          AND EXISTS (
              SELECT 1 FROM `tabPurchase Invoice Item` pii
              WHERE pii.parent = pi.name AND pii.purchase_receipt IS NOT NULL
              LIMIT 1
          )
    """, as_dict=True)

    for bill in bills:
        receipts = frappe.db.sql("""
            SELECT DISTINCT pii.purchase_receipt
            FROM `tabPurchase Invoice Item` pii
            WHERE pii.parent = %s AND pii.purchase_receipt IS NOT NULL
        """, (bill.name,), as_dict=True)

        for rec in receipts:
            qi = frappe.db.sql("""
                SELECT 1 FROM `tabQuality Inspection`
                WHERE reference_type = 'Purchase Receipt'
                  AND reference_name = %s AND docstatus = 1
                LIMIT 1
            """, (rec.purchase_receipt,))

            if not qi:
                rows.append(_row(
                    check_type="AP",
                    check_code="AP-07",
                    check_name="Missing Quality Inspection",
                    severity="Medium",
                    document_type="Purchase Invoice",
                    document=bill.name,
                    party_type="Supplier",
                    party=bill.supplier,
                    posting_date=str(bill.posting_date),
                    description=(
                        f"Receipt {rec.purchase_receipt} linked to "
                        f"{bill.name} has no submitted Quality Inspection"
                    ),
                    impact_amount=_sf(bill.grand_total),
                    recommendation=(
                        "Create and submit a Quality Inspection for the receipt "
                        "before processing payment."
                    ),
                ))
                break
    return rows


def _check_ap_stale_payable(from_date, to_date, company):
    """AP-08: PI outstanding past due date."""
    rows = []
    cf = _company_filter(company)
    today = getdate(nowdate())

    bills = frappe.db.sql(f"""
        SELECT name, supplier, outstanding_amount, posting_date, due_date
        FROM `tabPurchase Invoice`
        WHERE docstatus = 1
          AND outstanding_amount > 0.01
          AND due_date < CURDATE()
          AND due_date >= %s
          {cf}
          AND is_return = 0
    """, (from_date,), as_dict=True)

    for bill in bills:
        due          = getdate(bill.due_date) if bill.due_date else getdate(bill.posting_date)
        days_overdue = date_diff(today, due)
        severity     = "High" if days_overdue > 45 else "Medium"

        rows.append(_row(
            check_type="AP",
            check_code="AP-08",
            check_name="Stale Payable",
            severity=severity,
            document_type="Purchase Invoice",
            document=bill.name,
            party_type="Supplier",
            party=bill.supplier,
            posting_date=str(bill.posting_date),
            description=(
                f"Unpaid {days_overdue} days past due — outstanding "
                f"₦{_sf(bill.outstanding_amount):,.2f}, due date {bill.due_date}"
            ),
            impact_amount=_sf(bill.outstanding_amount),
            recommendation=(
                f"Schedule payment immediately — {days_overdue} days past due. "
                "Late payment may attract penalties or supplier suspension."
            ),
        ))
    return rows


def _check_ap_supplier_credit_limit_breach(from_date, to_date, company):
    """
    AP-09: Supplier outstanding > credit limit defined in the custom
    Supplier Credit Limit child table on Supplier doctype.
    Catches OperationalError gracefully if the child table does not yet exist.
    """
    rows = []
    company_clause = f"AND scl.company = {_escape(company)}" if company else ""

    try:
        credit_limit_rows = frappe.db.sql(f"""
            SELECT
                scl.parent      AS supplier,
                s.supplier_name,
                scl.company,
                scl.credit_limit
            FROM `tabSupplier Credit Limit` scl
            JOIN `tabSupplier` s ON s.name = scl.parent
            WHERE scl.parenttype = 'Supplier'
              AND scl.credit_limit > 0
              {company_clause}
        """, as_dict=True)
    except Exception:
        return rows   # Table does not exist yet

    for cl in credit_limit_rows:
        outstanding = frappe.db.sql("""
            SELECT COALESCE(SUM(outstanding_amount), 0) AS total
            FROM `tabPurchase Invoice`
            WHERE supplier = %s AND docstatus = 1
              AND outstanding_amount > 0 AND is_return = 0 AND company = %s
        """, (cl.supplier, cl.company), as_dict=True)

        outs   = _sf(outstanding[0].total if outstanding else 0)
        limit  = _sf(cl.credit_limit)
        excess = _sf(outs - limit)

        if excess > 0.01:
            rows.append(_row(
                check_type="AP",
                check_code="AP-09",
                check_name="Supplier Credit Limit Breach",
                severity="High",
                document_type="Supplier",
                document=cl.supplier,
                party_type="Supplier",
                party=cl.supplier,
                posting_date=nowdate(),
                description=(
                    f"{cl.supplier_name} [{cl.company}] — payable outstanding "
                    f"₦{outs:,.2f} exceeds supplier credit limit ₦{limit:,.2f} "
                    f"by ₦{excess:,.2f}"
                ),
                impact_amount=excess,
                recommendation=(
                    "Review supplier payment terms — outstanding payable "
                    "exceeds the agreed credit limit. Arrange immediate payment "
                    "or negotiate a temporary limit increase with the supplier "
                    "to avoid supply disruption."
                ),
            ))
    return rows


# ═══════════════════════════════════════════════════════════════════════════════
#  CROSS-CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

def _check_gl_control_account_reconciliation(from_date, to_date, company):
    """
    Entry point: runs AR orphan scan, AP orphan scan, stock control scan,
    then the net-balance headline check for both AR and AP.
    """
    rows = []
    cf = _company_filter(company)

    # ── discover control accounts (once, shared across all sub-checks) ────────
    ar_accounts = frappe.db.sql(f"""
        SELECT name FROM `tabAccount`
        WHERE account_type = 'Receivable' AND is_group = 0 {cf}
    """, pluck="name")

    ap_accounts = frappe.db.sql(f"""
        SELECT name FROM `tabAccount`
        WHERE account_type = 'Payable' AND is_group = 0 {cf}
    """, pluck="name")

    stock_accounts = frappe.db.sql(f"""
        SELECT name FROM `tabAccount`
        WHERE account_type IN ('Stock', 'Stock Received But Not Billed',
                               'Cost of Goods Sold')
          AND is_group = 0 {cf}
    """, pluck="name")

    rows += _scan_jv_orphan_lines(
        from_date, to_date, company,
        control_accounts = ar_accounts,
        expected_party_type = "Customer",
        check_type  = "AR",
        check_code  = "CX-01a",
        check_name  = "AR Control Account — JV Line Missing Party",
        label       = "AR",
    )

    rows += _scan_jv_orphan_lines(
        from_date, to_date, company,
        control_accounts = ap_accounts,
        expected_party_type = "Supplier",
        check_type  = "AP",
        check_code  = "CX-02a",
        check_name  = "AP Control Account — JV Line Missing Party",
        label       = "AP",
    )

    rows += _scan_jv_stock_control_direct_postings(
        from_date, to_date, company,
        stock_accounts = stock_accounts,
    )

    rows += _check_control_net_balance(
        from_date, to_date, company,
        control_accounts = ar_accounts,
        party_type   = "Customer",
        check_type   = "AR",
        check_code   = "CX-01b",
        check_name   = "AR Control vs Subsidiary Ledger — Net Balance Mismatch",
        debit_normal = True,
    )

    rows += _check_control_net_balance(
        from_date, to_date, company,
        control_accounts = ap_accounts,
        party_type   = "Supplier",
        check_type   = "AP",
        check_code   = "CX-02b",
        check_name   = "AP Control vs Subsidiary Ledger — Net Balance Mismatch",
        debit_normal = False,
    )

    return rows


def _scan_jv_orphan_lines(
    from_date, to_date, company,
    control_accounts, expected_party_type,
    check_type, check_code, check_name, label,
):
    """
    CX-01a (AR) / CX-02a (AP)
    ══════════════════════════
    Scan `tabJournal Entry Account` — the child table of every Journal Entry —
    for lines where:

        account  ∈  {Receivable accounts}  (AR)
                 ∈  {Payable accounts}      (AP)

    AND one of:
        (a) party_type is blank / NULL
        (b) party is blank / NULL
        (c) party_type is set but to the wrong type
            (e.g. 'Supplier' on an AR account)

    These are the true orphan postings: the Journal Entry has moved the
    control account balance without updating any individual customer or
    supplier sub-ledger record.  Every such line is raised as a separate
    Critical finding so the accountant can open the exact JV and fix it.

    WHY tabJournal Entry Account rather than tabGL Entry?
    ──────────────────────────────────────────────────────
    tabGL Entry reflects what was *generated* by ERPNext on submission.
    For a Journal Entry with a missing party, the GL entry is also missing
    the party — so both tables show the same defect.  However, scanning
    tabJournal Entry Account gives us:
      • The raw user input before any GL generation (catches the user error
        at source, not the downstream symptom).
      • Access to the `user_remark` and `reference_type` fields, which help
        diagnose *why* the party was omitted.
      • The ability to flag the problem on *draft* JVs before submission,
        if desired in future.
    Scanning the source document is best-practice audit methodology.
    """
    rows = []
    if not control_accounts:
        return rows

    in_clause = "(" + ", ".join(_escape(a) for a in control_accounts) + ")"
    df = _date_filter(from_date, to_date, field="jv.posting_date")
    cf = _company_filter(company, alias="jv")

    orphan_lines = frappe.db.sql(f"""
        SELECT
            jv.name                             AS jv_name,
            jv.posting_date,
            jv.voucher_type,
            jv.user_remark,
            jvl.account,
            jvl.debit_in_account_currency       AS debit,
            jvl.credit_in_account_currency      AS credit,
            COALESCE(jvl.party_type, '')        AS party_type,
            COALESCE(jvl.party, '')             AS party,
            jvl.reference_type,
            jvl.reference_name,
            jvl.idx
        FROM `tabJournal Entry` jv
        JOIN `tabJournal Entry Account` jvl ON jvl.parent = jv.name
        WHERE jv.docstatus = 1
          AND jvl.account IN {in_clause}
          AND (
                jvl.party_type IS NULL OR jvl.party_type = ''
             OR jvl.party      IS NULL OR jvl.party      = ''
             OR jvl.party_type != %s
          )
          {df}
          {cf}
        ORDER BY jv.posting_date, jv.name, jvl.idx
    """, (expected_party_type,), as_dict=True)

    for line in orphan_lines:
        debit  = _sf(line.debit)
        credit = _sf(line.credit)

        # Characterise exactly what is wrong with this line
        if not line.party_type and not line.party:
            fault = "both party_type and party are blank"
        elif not line.party_type:
            fault = "party_type is blank (party field has a value but type is missing)"
        elif not line.party:
            fault = f"party_type is '{line.party_type}' but party name is blank"
        else:
            fault = (
                f"party_type is '{line.party_type}' but expected '{expected_party_type}' "
                f"for this control account"
            )

        remark_note = f" — remark: \"{line.user_remark}\"" if line.user_remark else ""
        ref_note    = (
            f" — references {line.reference_type} {line.reference_name}"
            if line.reference_type else ""
        )

        rows.append(_row(
            check_type    = check_type,
            check_code    = check_code,
            check_name    = check_name,
            severity      = "Critical",
            document_type = "Journal Entry",
            document      = line.jv_name,
            party_type    = expected_party_type,
            party         = line.party or "— not set —",
            posting_date  = str(line.posting_date),
            description   = (
                f"Journal Entry {line.jv_name} (row {line.idx}) "
                f"[{line.posting_date}] posts ₦{debit:,.2f} Dr / ₦{credit:,.2f} Cr "
                f"directly to {label} control account '{line.account}' "
                f"but {fault}{ref_note}{remark_note}. "
                f"This moves the control account without updating any individual "
                f"{'customer' if expected_party_type == 'Customer' else 'supplier'} "
                f"balance — the subsidiary ledger will diverge from the control account."
            ),
            impact_amount = _sf(debit or credit),
            recommendation = (
                f"Open Journal Entry {line.jv_name}, go to row {line.idx}, "
                f"and set Party Type = '{expected_party_type}' and Party = the "
                f"correct {'customer' if expected_party_type == 'Customer' else 'supplier'} name. "
                f"If this posting is a period-end adjustment with no single party "
                f"(e.g. a write-off across multiple customers, a revaluation, or an "
                f"opening balance entry), it must NOT be posted to the {label} control "
                f"account directly. Instead: (a) use a suspense or adjustment account, "
                f"or (b) break the JV into individual lines — one per "
                f"{'customer' if expected_party_type == 'Customer' else 'supplier'} — "
                f"each with the correct party tag."
            ),
        ))

    return rows


def _scan_jv_stock_control_direct_postings(
    from_date, to_date, company,
    stock_accounts,
):
    """
    CX-03a — Journal Entry lines posted directly to Stock / COGS control accounts
    ═══════════════════════════════════════════════════════════════════════════════
    Stock, Stock Received But Not Billed, and Cost of Goods Sold accounts are
    system-managed control accounts.  Their balances are maintained by ERPNext
    through the normal inventory workflow:

        Purchase Receipt → Stock Received But Not Billed (interim)
        Purchase Invoice → clears interim, credits Creditor
        Stock Entry      → Stock / COGS accounts via valuation

    A Journal Entry that posts directly to any of these accounts bypasses the
    inventory sub-ledger (Stock Ledger Entry / Bin).  The result is that the
    GL balance of the stock account no longer agrees with the valuation of stock
    on hand — the same break that the Stock reconciliation checks (in the main
    engine) detect from the other direction.

    We flag every such JV line as a High-severity finding.  We do not flag:
      • Lines where reference_type IN ('Purchase Receipt', 'Purchase Invoice',
        'Stock Entry', 'Delivery Note') — these are system-generated GL entries
        that legitimately touch stock accounts through the approved workflow.
      • Cancelled JVs (docstatus = 2).
    """
    rows = []
    if not stock_accounts:
        return rows

    in_clause = "(" + ", ".join(_escape(a) for a in stock_accounts) + ")"
    df = _date_filter(from_date, to_date, field="jv.posting_date")
    cf = _company_filter(company, alias="jv")

    # Voucher types that legitimately generate GL on stock accounts via workflow
    ALLOWED_REF_TYPES = (
        "Purchase Receipt", "Purchase Invoice", "Stock Entry",
        "Delivery Note", "Sales Invoice", "Subcontracting Receipt",
        "Stock Reconciliation",
    )
    allowed_in = "(" + ", ".join(f"'{t}'" for t in ALLOWED_REF_TYPES) + ")"

    direct_lines = frappe.db.sql(f"""
        SELECT
            jv.name                             AS jv_name,
            jv.posting_date,
            jv.voucher_type,
            jv.user_remark,
            jvl.account,
            jvl.debit_in_account_currency       AS debit,
            jvl.credit_in_account_currency      AS credit,
            COALESCE(jvl.reference_type, '')    AS reference_type,
            COALESCE(jvl.reference_name, '')    AS reference_name,
            jvl.idx
        FROM `tabJournal Entry` jv
        JOIN `tabJournal Entry Account` jvl ON jvl.parent = jv.name
        WHERE jv.docstatus = 1
          AND jvl.account IN {in_clause}
          AND (
                jvl.reference_type IS NULL
             OR jvl.reference_type = ''
             OR jvl.reference_type NOT IN {allowed_in}
          )
          {df}
          {cf}
        ORDER BY jv.posting_date, jv.name, jvl.idx
    """, as_dict=True)

    for line in direct_lines:
        debit   = _sf(line.debit)
        credit  = _sf(line.credit)
        remark  = f" — remark: \"{line.user_remark}\"" if line.user_remark else ""

        rows.append(_row(
            check_type    = "Cross",
            check_code    = "CX-03a",
            check_name    = "Stock Control Account — Direct JV Posting",
            severity      = "High",
            document_type = "Journal Entry",
            document      = line.jv_name,
            party_type    = "",
            party         = "",
            posting_date  = str(line.posting_date),
            description   = (
                f"Journal Entry {line.jv_name} (row {line.idx}) "
                f"[{line.posting_date}] posts ₦{debit:,.2f} Dr / ₦{credit:,.2f} Cr "
                f"directly to stock control account '{line.account}' "
                f"without a valid inventory document reference{remark}. "
                f"This bypasses the stock ledger and will cause the GL stock "
                f"account balance to disagree with the physical stock valuation."
            ),
            impact_amount = _sf(debit or credit),
            recommendation = (
                f"Cancel Journal Entry {line.jv_name} and reverse the effect "
                f"through the correct ERPNext workflow: use a Stock Reconciliation "
                f"for quantity/value corrections, a Stock Entry (Material Receipt / "
                f"Write-Off) for movement adjustments, or a Purchase Invoice / "
                f"Delivery Note for goods received/dispatched. "
                f"Direct JV entries to stock accounts should only be posted with "
                f"CFO approval and must be accompanied by a Stock Reconciliation "
                f"to realign the sub-ledger."
            ),
        ))

    return rows


def _check_control_net_balance(
    from_date, to_date, company,
    control_accounts, party_type, check_type,
    check_code, check_name, debit_normal,
):
    """
    CX-01b (AR) / CX-02b (AP) — Net balance headline check
    ════════════════════════════════════════════════════════
    After all voucher-level orphan lines have been identified above,
    this check confirms the aggregate consequence: does the running
    net balance of the control account agree with the sum of all
    individual party outstanding amounts?

    GL control account net balance  (all entries up to to_date)
      vs
    Sum of outstanding_amount across all open submitted invoices
    (the sub-ledger total from tabSales Invoice / tabPurchase Invoice)

    A non-zero difference means some historical or period-end drift exists
    beyond what the individual JV line scans above have already flagged —
    e.g. orphan postings before from_date, multi-currency revaluation
    entries generated by ERPNext itself, or incomplete GL reversals on
    cancelled documents.
    """
    rows = []
    if not control_accounts:
        return rows

    in_clause  = "(" + ", ".join(_escape(a) for a in control_accounts) + ")"
    cf_gl      = _company_filter(company, alias="gl")
    cf_plain   = _company_filter(company)
    df_to_date = _date_filter(None, to_date, field="gl.posting_date")
    sign       = "debit - credit" if debit_normal else "credit - debit"
    label      = "AR" if party_type == "Customer" else "AP"

    ctrl = frappe.db.sql(f"""
        SELECT COALESCE(SUM({sign}), 0) AS net
        FROM `tabGL Entry` gl
        WHERE gl.account IN {in_clause}
          AND gl.is_cancelled = 0
          {df_to_date}
          {cf_gl}
    """, as_dict=True)
    gl_balance = _sf(ctrl[0].net if ctrl else 0)

    if party_type == "Customer":
        sub = frappe.db.sql(f"""
            SELECT COALESCE(SUM(outstanding_amount), 0) AS total
            FROM `tabSales Invoice`
            WHERE docstatus = 1
              AND outstanding_amount > 0
              AND posting_date <= {_escape(to_date)}
              {cf_plain}
        """, as_dict=True)
    else:
        sub = frappe.db.sql(f"""
            SELECT COALESCE(SUM(outstanding_amount), 0) AS total
            FROM `tabPurchase Invoice`
            WHERE docstatus = 1
              AND outstanding_amount > 0
              AND is_return = 0
              AND posting_date <= {_escape(to_date)}
              {cf_plain}
        """, as_dict=True)

    sub_total    = _sf(sub[0].total if sub else 0)
    balance_diff = _sf(abs(gl_balance - sub_total))

    if balance_diff > 1.0:
        rows.append(_row(
            check_type    = check_type,
            check_code    = check_code,
            check_name    = check_name,
            severity      = "Critical",
            document_type = "GL Entry",
            document      = f"{label} Control Accounts",
            party_type    = party_type,
            party         = f"All {label} Parties",
            posting_date  = nowdate(),
            description   = (
                f"Cumulative {label} control account GL net balance "
                f"(up to {to_date}): ₦{gl_balance:,.2f}. "
                f"Sum of individual {party_type.lower()} outstanding "
                f"(subsidiary ledger): ₦{sub_total:,.2f}. "
                f"Net difference: ₦{balance_diff:,.2f}. "
                f"The subsidiary ledger total does not agree with the control "
                f"account. This is the aggregate consequence of all orphan "
                f"postings — including any that occurred before {from_date}."
            ),
            impact_amount = balance_diff,
            recommendation = (
                f"First resolve every CX-01a / CX-02a orphan JV line flagged "
                f"above — fixing those will reduce or eliminate this balance gap. "
                f"For any residual difference, run the ERPNext "
                f"{'Accounts Receivable' if party_type == 'Customer' else 'Accounts Payable'} "
                f"Summary report and compare its grand total to the {label} control "
                f"account balance in the Trial Balance. "
                f"Trace each component of the remaining gap before posting any "
                f"correcting entry — do not post a single blanket adjustment."
            ),
        ))

    return rows


def _check_payment_allocation_mismatch(from_date, to_date, company):
    """CX-04: Payment Entry allocated_amount exceeds reference outstanding."""
    rows = []

    refs = frappe.db.sql(f"""
        SELECT per.parent AS pe_name, per.reference_doctype,
               per.reference_name, per.allocated_amount,
               pe.posting_date, pe.party, pe.party_type
        FROM `tabPayment Entry Reference` per
        JOIN `tabPayment Entry` pe ON pe.name = per.parent
        WHERE pe.docstatus = 1
          {_date_filter(from_date, to_date, field='pe.posting_date')}
          {_company_filter(company, alias='pe')}
    """, as_dict=True)

    for ref in refs:
        if ref.reference_doctype == "Sales Invoice":
            outstanding = frappe.db.get_value(
                "Sales Invoice", ref.reference_name, "outstanding_amount"
            ) or 0
        elif ref.reference_doctype == "Purchase Invoice":
            outstanding = frappe.db.get_value(
                "Purchase Invoice", ref.reference_name, "outstanding_amount"
            ) or 0
        else:
            continue

        alloc = _sf(ref.allocated_amount)
        outs  = _sf(outstanding)

        if alloc > outs + 0.05 and outs >= 0:
            rows.append(_row(
                check_type    = "Cross",
                check_code    = "CX-03",
                check_name    = "Payment Allocation Exceeds Outstanding",
                severity      = "Medium",
                document_type = "Payment Entry",
                document      = ref.pe_name,
                party_type    = ref.party_type,
                party         = ref.party,
                posting_date  = str(ref.posting_date),
                description   = (
                    f"{ref.pe_name} allocates ₦{alloc:,.2f} to "
                    f"{ref.reference_name} but outstanding is only ₦{outs:,.2f}"
                ),
                impact_amount = _sf(alloc - outs),
                recommendation = (
                    "Edit the Payment Entry Reference and reduce "
                    "allocated_amount to match the outstanding balance."
                ),
            ))
    return rows


# ═══════════════════════════════════════════════════════════════════════════════
#  AI ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def run_ai_analysis(check_results_json, company=None, from_date=None, to_date=None):
    """
    Send the mismatch summary to Claude AI for narrative analysis and
    prioritised recommendations.  Falls back to rule engine if no API key.
    """
    data    = json.loads(check_results_json) if isinstance(check_results_json, str) else check_results_json
    rows    = data.get("rows", [])
    summary = data.get("summary", {})

    prompt = _build_ai_prompt(rows, summary, company, from_date, to_date)

    try:
        api_key = frappe.conf.get("anthropic_api_key") or ""
        if not api_key:
            raise ValueError("No API key configured")
        import anthropic
        client  = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model      = "claude-opus-4-5",
            max_tokens = 1600,
            messages   = [{"role": "user", "content": prompt}],
        )
        raw  = message.content[0].text
        diag = _safe_json(raw)
        src  = "claude-ai"
    except Exception:
        diag = _rule_based_ai(rows, summary)
        src  = "rule-engine"

    diag["source"]       = src
    diag["generated_at"] = frappe.utils.now()
    return diag


def _build_ai_prompt(rows, summary, company, from_date, to_date):
    total  = summary.get("total", 0)
    impact = summary.get("total_impact", 0)
    ar_imp = summary.get("ar_impact", 0)
    ap_imp = summary.get("ap_impact", 0)

    top = sorted(rows, key=lambda r: flt(r.get("impact_amount") or 0), reverse=True)[:10]
    top_lines = "\n".join(
        f"  [{r['check_code']}] {r['check_name']} — {r['party']} — "
        f"₦{_sf(r.get('impact_amount',0)):,.2f} ({r['severity']})"
        for r in top
    )

    from collections import Counter
    code_freq  = Counter(r["check_code"] for r in rows)
    freq_lines = "\n".join(
        f"  {code}: {cnt} occurrences"
        for code, cnt in code_freq.most_common(8)
    )

    return f"""You are a senior Nigerian chartered accountant and ERP financial controller specialising in ERPNext.
Analyse this AP/AR reconciliation check result and produce a structured JSON diagnosis.

PERIOD: {from_date} to {to_date} | Company: {company or 'All'}

SUMMARY:
  Total mismatches: {total}
  Critical: {summary.get('critical',0)} | High: {summary.get('high',0)} | Medium: {summary.get('medium',0)} | Low: {summary.get('low',0)}
  AR issues: {summary.get('ar_count',0)} (₦{ar_imp:,.2f} impact)
  AP issues: {summary.get('ap_count',0)} (₦{ap_imp:,.2f} impact)
  Cross-ledger: {summary.get('cross_count',0)}
  Total financial impact: ₦{impact:,.2f}

TOP 10 MISMATCHES BY IMPACT:
{top_lines or '  None'}

CHECK CODE FREQUENCY:
{freq_lines or '  None'}

CONTROL ACCOUNT RECONCILIATION NOTES:
  CX-01a/CX-02a = Orphan GL postings on the control account with no party tag (manual JVs bypassing sub-ledger)
  CX-01b/CX-02b = Cumulative balance mismatch between GL control account and subsidiary ledger total

Return ONLY this JSON (no markdown, no extra text):
{{
  "overall_health": "Critical|Poor|Fair|Good|Clean",
  "health_score": <0-100>,
  "executive_summary": "2-3 sentence plain English assessment",
  "ar_assessment": "...",
  "ap_assessment": "...",
  "top_risks": [
    {{"risk": "...", "impact": "...", "urgency": "Immediate|This Week|This Month"}}
  ],
  "root_causes": ["...", "..."],
  "action_plan": [
    {{"priority": 1, "action": "...", "owner": "...", "deadline": "...", "expected_outcome": "..."}}
  ],
  "process_improvements": ["...", "..."],
  "compliance_flags": ["...", "..."],
  "positive_observations": ["...", "..."]
}}"""


def _rule_based_ai(rows, summary):
    total  = summary.get("total", 0)
    crit   = summary.get("critical", 0)
    high   = summary.get("high", 0)
    impact = summary.get("total_impact", 0)
    ar_imp = summary.get("ar_impact", 0)
    ap_imp = summary.get("ap_impact", 0)

    health = (
        "Clean"    if total == 0 else
        "Good"     if crit == 0 and high < 3 else
        "Fair"     if crit < 2 else
        "Poor"     if crit < 5 else
        "Critical"
    )
    score = 95 if total == 0 else max(10, 95 - crit * 15 - high * 5 - (total - crit - high) * 2)

    risks, actions, improvements, flags = [], [], [], []

    from collections import Counter
    code_freq = Counter(r["check_code"] for r in rows)

    # ── Control account orphan postings ──────────────────────────────────────
    if code_freq.get("CX-01a") or code_freq.get("CX-02a"):
        risks.append({
            "risk":    "Manual JVs posted directly to the AR/AP control account without a party tag",
            "impact":  "Sub-ledger will not reconcile with the control account — financial statements may be misstated",
            "urgency": "Immediate",
        })
        actions.append({
            "priority": 1,
            "action":   (
                "Identify all Journal Entries on AR/AP control accounts that lack a party tag "
                "(see CX-01a / CX-02a voucher list). Amend each JV to post to a suspense or "
                "adjustment account instead, or add the correct party_type/party reference."
            ),
            "owner":    "Chief Accountant",
            "deadline": "Today",
            "expected_outcome": "Eliminate orphan postings; control account movements will equal sub-ledger movements",
        })
        flags.append(
            "GL control account contains postings with no party tag — subsidiary ledger "
            "reconciliation will fail until these are corrected"
        )

    # ── Control account balance mismatch ─────────────────────────────────────
    if code_freq.get("CX-01b") or code_freq.get("CX-02b"):
        risks.append({
            "risk":    "Cumulative AR/AP control account balance does not match sub-ledger total",
            "impact":  "Balance sheet AR/AP figures are incorrect — audit qualification risk",
            "urgency": "Immediate",
        })
        actions.append({
            "priority": 2,
            "action":   (
                "Run the ERPNext AR/AP Reconciliation report to see the party-by-party breakdown. "
                "Identify historical orphan JVs, cancelled vouchers with incomplete GL reversals, "
                "and opening balance entries. Post correcting Journal Entries after approval."
            ),
            "owner":    "Chief Accountant",
            "deadline": "Within 2 days",
            "expected_outcome": "GL balance reconciles with sub-ledger total; balance sheet is accurate",
        })
        flags.append(
            "Subsidiary ledger does not reconcile with GL control account — "
            "likely indicates historical manual postings bypassing the AR/AP workflow"
        )
        improvements.append(
            "Restrict direct posting access to Receivable/Payable accounts in the Chart of Accounts "
            "— set 'Is Group' = No and remove from Journal Entry account permission for non-system users"
        )

    # ── Individual invoice GL mismatches (AR-01 / AP-01) ────────────────────
    if code_freq.get("AR-01") or code_freq.get("AP-01"):
        risks.append({
            "risk":    "Submitted invoices with missing or mismatched GL entries",
            "impact":  "Understated revenue or expense; control account will be out of balance",
            "urgency": "Immediate",
        })
        actions.append({
            "priority": 3,
            "action":   "Re-save or cancel/re-submit affected invoices to regenerate GL entries",
            "owner":    "Accountant",
            "deadline": "Within 24 hours",
            "expected_outcome": "GL balanced with sub-ledger at individual document level",
        })

    if code_freq.get("AR-06"):
        risks.append({
            "risk":    f"{code_freq['AR-06']} customer(s) over credit limit",
            "impact":  "Credit risk exposure — potential bad debt",
            "urgency": "This Week",
        })
        actions.append({
            "priority": 4,
            "action":   "Place over-limit customers on credit hold pending payment or credit review",
            "owner":    "Credit Manager",
            "deadline": "Within 2 days",
            "expected_outcome": "Prevent further exposure beyond approved credit",
        })

    if code_freq.get("AP-09"):
        risks.append({
            "risk":    f"{code_freq['AP-09']} supplier(s) over agreed credit limit",
            "impact":  "Supply disruption risk — supplier may halt deliveries",
            "urgency": "This Week",
        })
        actions.append({
            "priority": 5,
            "action":   "Schedule payments to bring supplier balances within agreed credit limits",
            "owner":    "AP Manager",
            "deadline": "Within 3 days",
            "expected_outcome": "Maintain supplier relationships and avoid supply chain disruption",
        })

    if code_freq.get("AP-04") or code_freq.get("AR-04"):
        risks.append({
            "risk":    "Possible duplicate invoices/bills",
            "impact":  "Risk of double payment or double revenue recognition",
            "urgency": "This Week",
        })
        actions.append({
            "priority": 6,
            "action":   "Review all flagged duplicate pairs — cancel confirmed duplicates",
            "owner":    "AP/AR Clerks",
            "deadline": "Within 3 days",
            "expected_outcome": "Eliminate duplicate entries",
        })
        improvements.append(
            "Implement duplicate invoice prevention in ERPNext — "
            "require unique supplier bill numbers per supplier"
        )

    if code_freq.get("AR-08"):
        cnt = code_freq["AR-08"]
        risks.append({
            "risk":    f"{cnt} stale AR invoices overdue",
            "impact":  f"₦{ar_imp:,.2f} collections at risk",
            "urgency": "This Week",
        })
        actions.append({
            "priority": 7,
            "action":   "Escalate all overdue invoices to collections team",
            "owner":    "AR Manager",
            "deadline": "This week",
            "expected_outcome": "Improve cash collections",
        })

    if code_freq.get("AP-05"):
        improvements.append(
            "Enforce Purchase Order requirement before accepting supplier bills — "
            "configure mandatory PO in ERPNext"
        )
        flags.append(
            "Bills processed without Purchase Orders — procurement controls may be bypassed"
        )

    if not risks:
        risks.append({
            "risk":    "No critical risks identified",
            "impact":  "Ledgers are substantially clean",
            "urgency": "This Month",
        })
    if not actions:
        actions.append({
            "priority": 1,
            "action":   "Continue regular monthly reconciliation checks",
            "owner":    "Accounts Team",
            "deadline": "Monthly",
            "expected_outcome": "Maintain clean ledgers",
        })
    if not improvements:
        improvements.append(
            "Maintain current controls — consider automating this reconciliation check weekly"
        )

    pos = []
    if summary.get("ar_count", 0) == 0:
        pos.append("AR ledger is clean — no customer mismatches found")
    if summary.get("ap_count", 0) == 0:
        pos.append("AP ledger is clean — no supplier mismatches found")
    if total == 0:
        pos.append("Both AR and AP ledgers are fully reconciled for this period")

    root_causes = list(filter(None, [
        "Manual journal entries posted directly to AR/AP control accounts without a party tag"
        if (code_freq.get("CX-01a") or code_freq.get("CX-02a") or
            code_freq.get("CX-01b") or code_freq.get("CX-02b")) else None,
        "Submitted invoice GL hooks failing — possible system error during on_submit"
        if (code_freq.get("AR-01") or code_freq.get("AP-01")) else None,
        "Insufficient payment allocation discipline"
        if (code_freq.get("AR-02") or code_freq.get("AP-02")) else None,
        "Weak duplicate invoice controls"
        if (code_freq.get("AR-04") or code_freq.get("AP-04")) else None,
        "Procurement controls bypassed — bills submitted without Purchase Orders"
        if code_freq.get("AP-05") else None,
    ]))

    return {
        "overall_health":        health,
        "health_score":          score,
        "executive_summary":     (
            f"AP/AR check for the period found {total} mismatches with a total financial impact "
            f"of ₦{impact:,.2f}. There are {crit} critical and {high} high-severity issues "
            f"requiring immediate attention. "
            f"{'Ledgers are substantially clean.' if total < 5 else 'Immediate reconciliation action is recommended.'}"
        ),
        "ar_assessment":         (
            f"{summary.get('ar_count',0)} AR issues totalling ₦{ar_imp:,.2f}. "
            + ("Clean." if summary.get('ar_count', 0) == 0
               else "Review and resolve before period close.")
        ),
        "ap_assessment":         (
            f"{summary.get('ap_count',0)} AP issues totalling ₦{ap_imp:,.2f}. "
            + ("Clean." if summary.get('ap_count', 0) == 0
               else "Prioritise critical AP items to avoid supplier disputes.")
        ),
        "top_risks":             risks[:5],
        "root_causes":           root_causes or ["No systemic root causes identified for this period"],
        "action_plan":           actions[:6],
        "process_improvements":  improvements[:4],
        "compliance_flags":      flags[:4] or ["No major compliance flags for this period"],
        "positive_observations": pos or ["Regular reconciliation checks are being performed — good practice"],
    }


def _safe_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:])
    if text.endswith("```"):
        text = "\n".join(text.split("\n")[:-1])
    return json.loads(text.strip())


# ─── row builder ──────────────────────────────────────────────────────────────

def _row(**kwargs):
    """Return a standardised mismatch row dict."""
    return {
        "row_number":     0,
        "check_type":     kwargs.get("check_type", ""),
        "check_code":     kwargs.get("check_code", ""),
        "check_name":     kwargs.get("check_name", ""),
        "severity":       kwargs.get("severity", "Medium"),
        "document_type":  kwargs.get("document_type", ""),
        "document":       kwargs.get("document", ""),
        "party_type":     kwargs.get("party_type", ""),
        "party":          kwargs.get("party", ""),
        "posting_date":   kwargs.get("posting_date", ""),
        "description":    kwargs.get("description", ""),
        "impact_amount":  kwargs.get("impact_amount", 0),
        "recommendation": kwargs.get("recommendation", ""),
        "status":         "Open",
    }