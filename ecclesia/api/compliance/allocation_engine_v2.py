# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/ecclesia/api/compliance/allocation_engine_v2.py
"""
Compliance Allocation Engine v2
════════════════════════════════
Creates a Compliance Payment Allocation transaction AND updates the CLL child table.
Double-entry approach: standalone transaction + child table row = audit grade.

Flow:
  Payments (submit) → on_payments_submit()
    → allocate_payment() → creates Compliance Payment Allocation doc
    → cll.apply_payment() → appends to CLL.allocations child table
    → cll.status recomputed
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate


# ── Get unpaid CLL entries (FIFO) ────────────────────────────────────────────

def _get_unpaid_clls(company, obligation_type):
    """Return CLL names with balance_due > 0, ordered oldest first."""
    return frappe.db.sql("""
        SELECT name FROM `tabCompliance Liability Ledger`
        WHERE company = %s AND obligation_type = %s
          AND status NOT IN ('Fully Paid','Exempt')
          AND balance_due > 0
        ORDER BY due_date ASC, period_label ASC
    """, (company, obligation_type), pluck="name")


def _get_exact_cll(company, obligation_type, period_label):
    return frappe.db.get_value(
        "Compliance Liability Ledger",
        {"company": company, "obligation_type": obligation_type, "period_label": period_label},
        "name"
    )


# ── Core allocation function ──────────────────────────────────────────────────

@frappe.whitelist()
def allocate_payment(payment_reference, obligation_type, company,
                     allocated_amount, period_label=None,
                     payments_doctype_ref=None, mode="auto"):
    """
    Allocate a payment to CLL entries.

    mode="auto"  → FIFO across oldest unpaid entries
    mode="exact" → allocate to specific period_label only

    Creates a Compliance Payment Allocation doc per allocation.
    Also updates the CLL child table via cll.apply_payment().
    """
    amount_remaining = flt(allocated_amount)
    if amount_remaining <= 0:
        frappe.throw(_("Allocated amount must be greater than zero."))

    allocations_made = []

    if mode == "exact" and period_label:
        cll_name = _get_exact_cll(company, obligation_type, period_label)
        if not cll_name:
            frappe.throw(_(
                "No CLL entry found for {0} / {1} / {2}. "
                "Run liability generation first."
            ).format(company, obligation_type, period_label))
        cll = frappe.get_doc("Compliance Liability Ledger", cll_name)
        alloc = min(amount_remaining, flt(cll.balance_due))
        if alloc > 0:
            _create_cpa_and_update_cll(cll, payment_reference, payments_doctype_ref,
                                        obligation_type, period_label, alloc)
            allocations_made.append({"cll": cll_name, "period": period_label, "amount": alloc})
            amount_remaining -= alloc

    else:
        # Auto FIFO
        for cll_name in _get_unpaid_clls(company, obligation_type):
            if amount_remaining <= 0:
                break
            cll   = frappe.get_doc("Compliance Liability Ledger", cll_name)
            alloc = min(amount_remaining, flt(cll.balance_due))
            if alloc > 0:
                _create_cpa_and_update_cll(cll, payment_reference, payments_doctype_ref,
                                            obligation_type, cll.period_label, alloc)
                allocations_made.append({"cll": cll_name, "period": cll.period_label, "amount": alloc})
                amount_remaining -= alloc

    frappe.db.commit()

    return {
        "success":      True,
        "allocations":  allocations_made,
        "allocated":    flt(allocated_amount) - amount_remaining,
        "unallocated":  amount_remaining,
        "message": _(
            "Allocated ₦{0:,.0f} to {1} period(s). Unallocated: ₦{2:,.0f}."
        ).format(
            flt(allocated_amount) - amount_remaining,
            len(allocations_made),
            amount_remaining
        )
    }


def _create_cpa_and_update_cll(cll, payment_ref, payments_ref,
                                 obligation_type, period_label, amount):
    """
    1. Create Compliance Payment Allocation (standalone transaction)
    2. Update CLL.allocations child table + recompute status
    """
    # 1. Standalone transaction
    cpa = frappe.new_doc("Compliance Payment Allocation")
    cpa.payment_reference      = payment_ref
    cpa.payments_doctype_ref   = payments_ref or ""
    cpa.compliance_liability   = cll.name
    cpa.obligation_type        = obligation_type
    cpa.period_label           = period_label
    cpa.allocated_amount       = flt(amount)
    cpa.allocation_method      = "Auto FIFO" if not period_label else "Manual Exact"
    cpa.allocation_date        = frappe.utils.now()
    cpa.company                = cll.company
    cpa.insert(ignore_permissions=True)

    # 2. CLL child table update
    cll.apply_payment(
        payment_reference  = payment_ref,
        payments_doc       = payments_ref,
        allocated_amount   = amount,
        allocation_method  = cpa.allocation_method,
        period_label       = period_label
    )


# ── Hook: Payments DocType on_submit ─────────────────────────────────────────

def on_payments_submit(doc, method=None):
    """
    Called from hooks.py doc_events on Payments.on_submit.
    Only fires if compliance_obligation_type is set on the Payments doc.
    """
    obligation_type = doc.get("compliance_obligation_type")
    if not obligation_type:
        return

    amount       = flt(doc.get("compliance_allocated_amount") or doc.get("amount_paid") or 0)
    period_label = doc.get("compliance_fiscal_month") or None
    mode         = "exact" if period_label else "auto"

    if amount <= 0:
        return

    try:
        result = allocate_payment(
            payment_reference    = doc.name,
            obligation_type      = obligation_type,
            company              = doc.company,
            allocated_amount     = amount,
            period_label         = period_label,
            payments_doctype_ref = doc.name,
            mode                 = mode,
        )
        if result.get("success"):
            frappe.msgprint(result["message"], indicator="green", alert=True)
    except Exception as e:
        frappe.log_error(f"CLL allocation failed for {doc.name}: {e}", "Allocation Engine v2")


# ── Preview (for JS before submit) ───────────────────────────────────────────

@frappe.whitelist()
def preview_allocation(company, obligation_type, amount, period_label=None):
    amount = flt(amount)
    remaining = amount
    preview = []

    if period_label:
        cll_name = _get_exact_cll(company, obligation_type, period_label)
        if cll_name:
            cll   = frappe.get_doc("Compliance Liability Ledger", cll_name)
            alloc = min(remaining, flt(cll.balance_due))
            preview.append({
                "period":       cll.period_label,
                "due_date":     cll.due_date,
                "liability":    cll.total_liability,
                "balance":      cll.balance_due,
                "to_allocate":  alloc,
                "status_after": "Fully Paid" if alloc >= flt(cll.balance_due) else "Partially Paid"
            })
            remaining -= alloc
    else:
        for cll_name in _get_unpaid_clls(company, obligation_type):
            if remaining <= 0:
                break
            cll   = frappe.get_doc("Compliance Liability Ledger", cll_name)
            alloc = min(remaining, flt(cll.balance_due))
            preview.append({
                "period":       cll.period_label,
                "due_date":     cll.due_date,
                "liability":    cll.total_liability,
                "balance":      cll.balance_due,
                "to_allocate":  alloc,
                "status_after": "Fully Paid" if alloc >= flt(cll.balance_due) else "Partially Paid"
            })
            remaining -= alloc

    return {
        "preview":    preview,
        "total":      amount,
        "allocated":  amount - remaining,
        "unallocated": remaining
    }


# ── Reconcile ─────────────────────────────────────────────────────────────────

@frappe.whitelist()
def reconcile_all_cll(company=None, obligation_type=None):
    filters = {}
    if company:         filters["company"] = company
    if obligation_type: filters["obligation_type"] = obligation_type

    clls = frappe.get_all("Compliance Liability Ledger", filters=filters,
                           fields=["name","status"])
    changed = 0
    for entry in clls:
        doc = frappe.get_doc("Compliance Liability Ledger", entry.name)
        old = doc.status
        doc._compute_totals()
        doc._compute_status()
        doc._compute_penalty()
        doc.last_reconciled_on = frappe.utils.now()
        doc.save(ignore_permissions=True)
        if doc.status != old:
            changed += 1

    frappe.db.commit()
    return {"reconciled": len(clls), "status_changed": changed}


# ── Hook: Payments DocType on_cancel ─────────────────────────────────────────

def on_payments_cancel(doc, method=None):
    """
    hooks.py doc_events → Payments → on_cancel
    Reverses all CLL allocations made when this Payments doc was submitted.

    Strategy:
      1. Find all Compliance Payment Allocation docs linked to this payment.
      2. For each, subtract the allocated amount from the CLL entry's allocations
         child table and delete the CPA transaction.
      3. Recompute CLL totals and status.
    """
    if not doc or not doc.name:
        return

    try:
        # Find all Compliance Payment Allocation docs for this payment
        cpas = frappe.db.get_all(
            "Compliance Payment Allocation",
            filters={"payment_reference": doc.name},
            fields=["name", "compliance_liability", "allocated_amount",
                    "obligation_type", "period_label"]
        )

        if not cpas:
            return

        reversed_count = 0

        for cpa in cpas:
            try:
                # Load the CLL and remove the matching allocation row
                cll = frappe.get_doc("Compliance Liability Ledger",
                                     cpa.compliance_liability)

                # Remove the matching row from the allocations child table
                rows_before = len(cll.allocations or [])
                cll.allocations = [
                    row for row in (cll.allocations or [])
                    if row.payment_reference != doc.name
                ]
                rows_after = len(cll.allocations)

                if rows_before != rows_after:
                    # Recompute totals and status
                    cll._compute_totals()
                    cll._compute_status()
                    cll.last_reconciled_on = frappe.utils.now()
                    cll.save(ignore_permissions=True)

                # Cancel the standalone CPA transaction
                frappe.delete_doc("Compliance Payment Allocation",
                                  cpa.name, ignore_permissions=True)
                reversed_count += 1

            except Exception as inner_e:
                frappe.log_error(
                    f"Failed to reverse CLL allocation {cpa.name} "
                    f"for payment {doc.name}: {inner_e}",
                    "Allocation Engine v2 — Cancel"
                )

        frappe.db.commit()

        if reversed_count:
            frappe.msgprint(
                f"✅ Reversed {reversed_count} CLL allocation(s) for cancelled payment {doc.name}.",
                indicator="orange",
                alert=True
            )

    except Exception as e:
        frappe.log_error(
            f"on_payments_cancel failed for {doc.name}: {e}",
            "Allocation Engine v2"
        )