# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/ecclesia/api/compliance/allocation_engine.py
"""
Compliance Allocation Engine
═════════════════════════════
Links payments from the Payments DocType (and Payment Entry / Journal Entry)
to Compliance Liability Ledger (CLL) entries.

Design: Hybrid approach
  1. Auto-allocation (FIFO by due_date) for known compliance payment types
  2. Manual override: user selects which month to pay via dialog in JS
  3. Unallocated amount is tracked and flags on dashboard

This engine is called:
  - On submit of Payments DocType when cashflow_type == "Tax Payment"
    or trans_type triggers compliance (identified by obligation_type field added to Payments)
  - Manually from the ComplianceHQ dashboard
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate, getdate


# ── Obligation types that are auto-identified from Payments cashflow_type ────
CASHFLOW_TO_OBLIGATION = {
    "Tax Payment": None,  # use obligation_type field on the Payments doc
}

COMPLIANCE_PAYMENT_TRANS_TYPES = {"Tax Payment", "Statutory Payment", "Pension Remittance"}


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN ALLOCATION FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def allocate_payment_to_cll(
    payment_reference,
    payment_doctype="Payments",
    obligation_type=None,
    fiscal_month=None,
    company=None,
    allocated_amount=None,
    mode="auto"
):
    """
    Allocate a payment to one or more CLL entries.

    Parameters
    ──────────
    payment_reference : str   — name of the Payments / Payment Entry doc
    obligation_type   : str   — e.g. "VAT", "WHT", "PAYE", "Pension"
    fiscal_month      : str   — "YYYY-MM" (optional, used for exact-match)
    company           : str   — company
    allocated_amount  : float — amount being paid
    mode              : str   — "auto" (FIFO) | "exact" (specific month)

    Returns
    ───────
    dict with allocation summary
    """
    if not obligation_type:
        frappe.throw(_("Obligation Type is required for compliance allocation."))
    if not company:
        frappe.throw(_("Company is required."))
    if not allocated_amount or flt(allocated_amount) <= 0:
        frappe.throw(_("Allocated Amount must be positive."))

    amount_remaining = flt(allocated_amount)
    allocations_made = []

    if mode == "exact" and fiscal_month:
        # ── Exact match: user specified the month ──────────────────────────
        cll = _get_cll(company, obligation_type, fiscal_month)
        if not cll:
            frappe.throw(
                _("No CLL entry found for {0} / {1} / {2}. "
                  "Run liability generation first.").format(company, obligation_type, fiscal_month)
            )
        alloc = min(amount_remaining, flt(cll.balance))
        if alloc > 0:
            cll.apply_payment(payment_reference, payment_doctype, alloc)
            allocations_made.append({"cll": cll.name, "month": fiscal_month, "amount": alloc})
            amount_remaining -= alloc

    else:
        # ── Auto FIFO: oldest unpaid first ────────────────────────────────
        unpaid_clls = _get_unpaid_clls_ordered(company, obligation_type)
        for cll in unpaid_clls:
            if amount_remaining <= 0:
                break
            alloc = min(amount_remaining, flt(cll.balance))
            if alloc > 0:
                cll.apply_payment(payment_reference, payment_doctype, alloc)
                allocations_made.append({
                    "cll": cll.name,
                    "month": cll.fiscal_month,
                    "amount": alloc
                })
                amount_remaining -= alloc

    frappe.db.commit()

    return {
        "success": True,
        "allocations": allocations_made,
        "amount_allocated": flt(allocated_amount) - amount_remaining,
        "unallocated_remainder": amount_remaining,
        "message": _("Allocated ₦{0:,.2f} to {1} CLL entries. Unallocated: ₦{2:,.2f}").format(
            flt(allocated_amount) - amount_remaining,
            len(allocations_made),
            amount_remaining
        )
    }


# ── Helper: get specific CLL ─────────────────────────────────────────────────

def _get_cll(company, obligation_type, fiscal_month):
    name = frappe.db.get_value(
        "Compliance Liability Ledger",
        {"company": company, "obligation_type": obligation_type, "fiscal_month": fiscal_month},
        "name"
    )
    if name:
        return frappe.get_doc("Compliance Liability Ledger", name)
    return None


def _get_unpaid_clls_ordered(company, obligation_type):
    """Return CLL entries with a balance > 0, ordered by due_date ASC (FIFO)."""
    names = frappe.db.sql("""
        SELECT name FROM `tabCompliance Liability Ledger`
        WHERE company         = %s
          AND obligation_type = %s
          AND status          NOT IN ('Paid', 'Exempt')
          AND balance         > 0
        ORDER BY due_date ASC, fiscal_month ASC
    """, (company, obligation_type), pluck="name")
    return [frappe.get_doc("Compliance Liability Ledger", n) for n in names]


# ══════════════════════════════════════════════════════════════════════════════
#  HOOK: called on Payments DocType submit
# ══════════════════════════════════════════════════════════════════════════════

def on_payments_submit(doc, method=None):
    """
    Called from doc_events Payments.on_submit in hooks.py.
    If the payment is a compliance payment, auto-allocate to CLL.

    Reads fields we'll add to Payments:
      - compliance_obligation_type  (Select)
      - compliance_fiscal_month     (Data, YYYY-MM)
      - compliance_allocated_amount (Currency)
      - compliance_mode             (Select: Auto / Manual)
    """
    obligation_type = doc.get("compliance_obligation_type")
    if not obligation_type:
        # Only process if explicitly tagged as a compliance payment
        return

    fiscal_month    = doc.get("compliance_fiscal_month") or None
    amount          = flt(doc.get("compliance_allocated_amount") or doc.get("amount_paid") or 0)
    mode            = doc.get("compliance_mode") or "auto"

    if amount <= 0:
        return

    try:
        result = allocate_payment_to_cll(
            payment_reference = doc.name,
            payment_doctype   = "Payments",
            obligation_type   = obligation_type,
            fiscal_month      = fiscal_month,
            company           = doc.company,
            allocated_amount  = amount,
            mode              = mode if fiscal_month else "auto",
        )
        if result.get("success"):
            frappe.msgprint(result["message"], indicator="green", alert=True)
    except Exception as e:
        frappe.log_error(f"CLL allocation failed for {doc.name}: {e}",
                         "Compliance Allocation Engine")


# ══════════════════════════════════════════════════════════════════════════════
#  PREVIEW: called from JS before submit to show allocation breakdown
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def preview_allocation(company, obligation_type, amount, fiscal_month=None):
    """
    Show the user which months will be paid (FIFO) before committing.
    Called from the Payments form JS via frappe.call().
    """
    amount = flt(amount)
    remaining = amount
    preview = []

    if fiscal_month:
        cll = _get_cll(company, obligation_type, fiscal_month)
        if cll:
            alloc = min(remaining, flt(cll.balance))
            preview.append({
                "fiscal_month": cll.fiscal_month,
                "due_date":     cll.due_date,
                "liability":    cll.amount_calculated,
                "balance":      cll.balance,
                "to_allocate":  alloc,
                "status_after": "Paid" if alloc >= flt(cll.balance) else "Part Paid"
            })
            remaining -= alloc
    else:
        unpaid = _get_unpaid_clls_ordered(company, obligation_type)
        for cll in unpaid:
            if remaining <= 0:
                break
            alloc = min(remaining, flt(cll.balance))
            preview.append({
                "fiscal_month": cll.fiscal_month,
                "due_date":     cll.due_date,
                "liability":    cll.amount_calculated,
                "balance":      cll.balance,
                "to_allocate":  alloc,
                "status_after": "Paid" if alloc >= flt(cll.balance) else "Part Paid"
            })
            remaining -= alloc

    return {
        "preview":       preview,
        "total_amount":  amount,
        "total_covered": amount - remaining,
        "unallocated":   remaining
    }


# ══════════════════════════════════════════════════════════════════════════════
#  RECONCILIATION: detect gaps
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def reconcile_cll(company, obligation_type=None, fiscal_month=None):
    """
    Scan CLL entries and:
    1. Re-compute balance from allocation_lines
    2. Update status
    3. Flag overdue entries
    4. Return reconciliation report
    """
    filters = {"company": company}
    if obligation_type:
        filters["obligation_type"] = obligation_type
    if fiscal_month:
        filters["fiscal_month"] = fiscal_month

    clls = frappe.get_all(
        "Compliance Liability Ledger",
        filters=filters,
        fields=["name", "obligation_type", "fiscal_month", "amount_calculated",
                "amount_paid", "balance", "status", "due_date"]
    )

    summary = {"reconciled": 0, "status_changed": 0, "overdue_flagged": 0}

    for entry in clls:
        doc = frappe.get_doc("Compliance Liability Ledger", entry.name)
        old_status = doc.status
        doc._compute_balance()
        doc._compute_status()
        doc._compute_penalty()
        doc.last_reconciled = frappe.utils.now()
        doc.save(ignore_permissions=True)
        summary["reconciled"] += 1
        if doc.status != old_status:
            summary["status_changed"] += 1
        if doc.status == "Overdue":
            summary["overdue_flagged"] += 1

    frappe.db.commit()
    return summary