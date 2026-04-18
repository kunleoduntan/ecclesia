# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

"""
Payment Invoice Match — AI-Powered Reconciliation Controller
=============================================================
Module: Ecclesia

Flow:
  1. run_ai_match()      → fetch unmatched payments + outstanding invoices
                           → call Claude AI to propose matches with confidence scores
                           → save proposed matches to match_lines child table
  2. apply_approved()    → for each Approved line, write the payment reference
                           onto the Payment Entry (marks invoice as paid in ERPNext)
  3. apply_single_line() → apply one specific approved line immediately
"""

import json
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today


class PaymentInvoiceMatch(Document):

    def validate(self):
        if self.from_date and self.to_date and self.from_date > self.to_date:
            frappe.throw(_("From Date cannot be after To Date."))

    def on_cancel(self):
        self.db_set("status", "Cancelled")


# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Fetch data + call AI + populate match_lines
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def run_ai_match(doc_name: str) -> dict:
    """
    Main entry point. Fetches unreconciled payments and outstanding invoices,
    sends them to Claude AI for matching, saves results to the document.
    """
    doc = frappe.get_doc("Payment Invoice Match", doc_name)
    doc.db_set("status", "In Progress")

    company     = doc.company
    party_type  = doc.party_type
    from_date   = doc.from_date
    to_date     = doc.to_date
    bank_account = doc.bank_account or None
    threshold   = flt(doc.confidence_threshold or 60)
    auto_above  = flt(doc.auto_apply_above or 95)

    # ── 1. Fetch unmatched Payment Entries ────────────────────────────────────
    payments = _fetch_unmatched_payments(company, party_type, from_date, to_date, bank_account)

    # ── 2. Fetch outstanding invoices ─────────────────────────────────────────
    invoices = _fetch_outstanding_invoices(company, party_type)

    if not payments:
        frappe.throw(_("No unmatched Payment Entries found for the given filters."))
    if not invoices:
        frappe.throw(_("No outstanding invoices found."))

    # ── 3. Call Claude AI ─────────────────────────────────────────────────────
    ai_matches = _call_claude_matcher(payments, invoices, party_type)

    # ── 4. Filter by threshold and populate match_lines ───────────────────────
    doc.match_lines = []
    approved_count  = 0

    for match in ai_matches:
        score = flt(match.get("confidence", 0))
        if score < threshold:
            continue

        # Find the payment and invoice details
        payment = next((p for p in payments if p["name"] == match.get("payment_entry")), None)
        invoice = next((i for i in invoices if i["name"] == match.get("invoice")), None)

        if not payment or not invoice:
            continue

        allocated = min(flt(payment["unallocated_amount"]), flt(invoice["outstanding_amount"]))
        status    = "Approved" if score >= auto_above else "Pending"
        if status == "Approved":
            approved_count += 1

        doc.append("match_lines", {
            "payment_entry":    payment["name"],
            "payment_date":     payment["posting_date"],
            "payment_amount":   payment["paid_amount"],
            "payment_party":    payment.get("party_name") or payment.get("party") or "",
            "invoice_type":     invoice["doctype"],
            "invoice":          invoice["name"],
            "invoice_date":     invoice["posting_date"],
            "invoice_amount":   invoice["grand_total"],
            "outstanding_amount": invoice["outstanding_amount"],
            "confidence_score": score,
            "ai_reasoning":     match.get("reasoning", ""),
            "match_status":     status,
            "allocated_amount": allocated,
            "applied":          0,
        })

    # ── 5. Update summary fields ───────────────────────────────────────────────
    doc.total_payments_fetched = len(payments)
    doc.total_invoices_fetched = len(invoices)
    doc.matches_proposed       = len(doc.match_lines)
    doc.matches_approved       = approved_count
    doc.matches_rejected       = 0
    doc.status                 = "In Progress"
    doc.save(ignore_permissions=False)
    frappe.db.commit()

    return {
        "payments_fetched": len(payments),
        "invoices_fetched": len(invoices),
        "matches_proposed": len(doc.match_lines),
        "auto_approved":    approved_count,
        "message":          (
            f"AI proposed {len(doc.match_lines)} match(es) from {len(payments)} payment(s) "
            f"and {len(invoices)} invoice(s). {approved_count} auto-approved at ≥{auto_above}% confidence."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Apply all Approved matches
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def apply_approved(doc_name: str) -> dict:
    """
    Iterates all Approved + not-yet-applied lines and reconciles them
    by adding the invoice to the Payment Entry's references table.
    """
    doc = frappe.get_doc("Payment Invoice Match", doc_name)

    applied = skipped = errors = 0
    total_amount = 0.0
    error_details = []

    for line in doc.match_lines:
        if line.match_status != "Approved" or line.applied:
            skipped += 1
            continue

        try:
            _apply_single_match(
                payment_entry=line.payment_entry,
                invoice_doctype=line.invoice_type,
                invoice_name=line.invoice,
                allocated_amount=flt(line.allocated_amount),
            )
            frappe.db.set_value("Payment Invoice Match Line", line.name,
                                "applied", 1, update_modified=False)
            total_amount += flt(line.allocated_amount)
            applied += 1

        except Exception as e:
            frappe.log_error(frappe.get_traceback(),
                f"PIM {doc_name}: apply failed {line.payment_entry} → {line.invoice}")
            error_details.append(f"Row {line.idx}: {str(e)}")
            errors += 1

    # Update summary
    frappe.db.set_value("Payment Invoice Match", doc_name, {
        "matches_approved":      applied,
        "total_amount_reconciled": total_amount,
        "status": "Completed" if errors == 0 else "In Progress",
    }, update_modified=False)
    frappe.db.commit()

    return {
        "applied":       applied,
        "skipped":       skipped,
        "errors":        errors,
        "total_amount":  total_amount,
        "error_details": error_details,
        "message":       f"Applied: {applied} | Skipped: {skipped} | Errors: {errors}",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Apply a single match line by row name
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def apply_single_line(line_name: str) -> dict:
    """Apply one specific match line immediately."""
    if not frappe.db.exists("Payment Invoice Match Line", line_name):
        frappe.throw(_("Match line not found."))

    line = frappe.get_doc("Payment Invoice Match Line", line_name)

    if line.applied:
        frappe.throw(_("This match has already been applied."))
    if line.match_status != "Approved":
        frappe.throw(_("Only Approved matches can be applied."))

    _apply_single_match(
        payment_entry=line.payment_entry,
        invoice_doctype=line.invoice_type,
        invoice_name=line.invoice,
        allocated_amount=flt(line.allocated_amount),
    )

    frappe.db.set_value("Payment Invoice Match Line", line_name,
                        "applied", 1, update_modified=False)

    # Update parent totals
    parent = line.parent
    total = frappe.db.sql("""
        SELECT SUM(allocated_amount) FROM `tabPayment Invoice Match Line`
        WHERE parent=%s AND applied=1
    """, parent)[0][0] or 0

    frappe.db.set_value("Payment Invoice Match", parent,
                        "total_amount_reconciled", total, update_modified=False)
    frappe.db.commit()

    return {
        "applied": True,
        "payment_entry": line.payment_entry,
        "invoice": line.invoice,
        "amount": flt(line.allocated_amount),
        "message": f"Payment {line.payment_entry} reconciled with {line.invoice}.",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Update a line's status (Approve / Reject) from the UI
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def update_line_status(line_name: str, status: str, allocated_amount: float = None) -> dict:
    """Called when user clicks Approve / Reject on a match line."""
    if status not in ("Approved", "Rejected", "Pending"):
        frappe.throw(_(f"Invalid status: {status}"))

    updates = {"match_status": status}
    if allocated_amount is not None:
        updates["allocated_amount"] = flt(allocated_amount)

    frappe.db.set_value("Payment Invoice Match Line", line_name, updates, update_modified=False)
    frappe.db.commit()
    return {"status": status, "line": line_name}


# ─────────────────────────────────────────────────────────────────────────────
# Fetch unmatched Payment Entries
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_unmatched_payments(company, party_type, from_date, to_date, bank_account=None):
    """
    Returns Payment Entries that:
    - Are submitted (docstatus=1)
    - Have unallocated amount > 0 (i.e., not fully matched to invoices)
    - Match party_type (Customer→Receive, Supplier→Pay)
    - Fall within the date range
    """
    payment_type = "Receive" if party_type == "Customer" else "Pay"

    filters = {
        "docstatus":    1,
        "company":      company,
        "payment_type": payment_type,
        "unallocated_amount": [">", 0],
        "posting_date": ["between", [from_date, to_date]],
    }
    if bank_account:
        filters["bank_account"] = bank_account

    payments = frappe.db.get_all(
        "Payment Entry",
        filters=filters,
        fields=[
            "name", "posting_date", "party", "party_name",
            "paid_amount", "unallocated_amount",
            "reference_no", "remarks", "mode_of_payment",
        ],
        order_by="posting_date asc",
        limit=200,
    )
    return [p for p in payments if flt(p.get("unallocated_amount")) > 0]


# ─────────────────────────────────────────────────────────────────────────────
# Fetch outstanding invoices
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_outstanding_invoices(company, party_type):
    """
    Returns submitted invoices with outstanding_amount > 0.
    Sales Invoice for Customer, Purchase Invoice for Supplier.
    """
    if party_type == "Customer":
        doctype    = "Sales Invoice"
        party_field = "customer"
        name_field  = "customer_name"
    else:
        doctype    = "Purchase Invoice"
        party_field = "supplier"
        name_field  = "supplier_name"

    invoices = frappe.db.get_all(
        doctype,
        filters={
            "docstatus":          1,
            "company":            company,
            "outstanding_amount": [">", 0],
        },
        fields=[
            "name", "posting_date", party_field + " as party",
            name_field + " as party_name",
            "grand_total", "outstanding_amount",
            "due_date", "remarks", "bill_no",
        ],
        order_by="posting_date asc",
        limit=500,
    )

    for inv in invoices:
        inv["doctype"] = doctype

    return invoices


# ─────────────────────────────────────────────────────────────────────────────
# Claude AI matcher
# ─────────────────────────────────────────────────────────────────────────────

def _call_claude_matcher(payments, invoices, party_type):
    """
    Sends payments and invoices to Claude claude-sonnet-4-20250514 for intelligent matching.
    Returns a list of proposed matches with confidence scores and reasoning.
    """
    import requests

    # Build concise representations for the AI
    payment_list = []
    for p in payments:
        payment_list.append({
            "name":              p["name"],
            "date":              str(p["posting_date"]),
            "party":             p.get("party") or "",
            "party_name":        p.get("party_name") or "",
            "amount":            flt(p["unallocated_amount"]),
            "reference":         p.get("reference_no") or "",
            "remarks":           (p.get("remarks") or "")[:120],
        })

    invoice_list = []
    for i in invoices:
        invoice_list.append({
            "name":              i["name"],
            "date":              str(i["posting_date"]),
            "due_date":          str(i.get("due_date") or ""),
            "party":             i.get("party") or "",
            "party_name":        i.get("party_name") or "",
            "grand_total":       flt(i["grand_total"]),
            "outstanding":       flt(i["outstanding_amount"]),
            "bill_no":           i.get("bill_no") or "",
            "remarks":           (i.get("remarks") or "")[:120],
        })

    system_prompt = """You are an expert accountant specialising in payment reconciliation.
Your task is to match payments to invoices. Return ONLY valid JSON — no markdown, no explanation outside the JSON.

Matching rules:
1. AMOUNT: Exact amount match = very high confidence. Partial match (payment covers part of invoice or invoice partly covers payment) = acceptable.
2. PARTY: Same party (by ID or name similarity) is essential. Fuzzy match party names (abbreviations, typos, trading names).
3. REFERENCE: If payment reference_no matches invoice name or bill_no = very high confidence boost.
4. DATE: Payment after invoice date is expected. Very large gaps (>180 days) reduce confidence slightly.
5. REMARKS: Look for invoice numbers, party names, or descriptions in remarks.
6. One payment can match multiple invoices. One invoice can only be matched once.
7. Only propose matches with genuine evidence. Do NOT guess randomly.

Return this exact JSON structure:
{
  "matches": [
    {
      "payment_entry": "<payment name>",
      "invoice": "<invoice name>",
      "confidence": <0-100 integer>,
      "reasoning": "<one concise sentence explaining the match>"
    }
  ],
  "summary": "<brief overall summary of matching quality>"
}"""

    user_prompt = f"""Match these {len(payment_list)} {party_type} payment(s) to these {len(invoice_list)} outstanding invoice(s).

PAYMENTS (unmatched, unallocated amount shown):
{json.dumps(payment_list, indent=2)}

OUTSTANDING INVOICES:
{json.dumps(invoice_list, indent=2)}

Return JSON only."""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={
                "model":      "claude-sonnet-4-20250514",
                "max_tokens": 4096,
                "system":     system_prompt,
                "messages":   [{"role": "user", "content": user_prompt}],
            },
            timeout=60,
        )
        response.raise_for_status()
        data     = response.json()
        raw_text = data["content"][0]["text"].strip()

        # Strip any accidental markdown fences
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        raw_text = raw_text.strip()

        result  = json.loads(raw_text)
        matches = result.get("matches", [])
        return matches

    except requests.exceptions.Timeout:
        frappe.log_error("Claude API timed out during payment matching", "Payment Invoice Match")
        frappe.throw(_("AI matching timed out. Please try again or reduce the date range."))
    except json.JSONDecodeError as e:
        frappe.log_error(f"Claude returned invalid JSON: {raw_text[:500]}", "Payment Invoice Match")
        frappe.throw(_("AI returned an unexpected response. Check Error Log for details."))
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Payment Invoice Match: Claude API error")
        frappe.throw(_(f"AI matching failed: {str(e)}"))


# ─────────────────────────────────────────────────────────────────────────────
# Apply a single match to ERPNext
# ─────────────────────────────────────────────────────────────────────────────

def _apply_single_match(payment_entry, invoice_doctype, invoice_name, allocated_amount):
    """
    Reconciles a payment with an invoice by adding an entry to the Payment Entry's
    `references` table (Payment Entry Reference child table).

    This is the standard ERPNext mechanism that:
    - Marks the invoice as (partially or fully) paid
    - Reduces the outstanding_amount on the invoice
    - Reduces the unallocated_amount on the payment
    """
    pe = frappe.get_doc("Payment Entry", payment_entry)

    # Check this invoice isn't already referenced
    existing = [r for r in pe.references if r.reference_name == invoice_name]
    if existing:
        frappe.throw(_(
            f"Invoice {invoice_name} is already referenced in Payment Entry {payment_entry}."
        ))

    # Validate there's enough unallocated amount
    if flt(pe.unallocated_amount) < flt(allocated_amount):
        frappe.throw(_(
            f"Payment Entry {payment_entry} only has {pe.unallocated_amount} unallocated. "
            f"Cannot allocate {allocated_amount}."
        ))

    # Add the reference
    pe.append("references", {
        "reference_doctype": invoice_doctype,
        "reference_name":    invoice_name,
        "allocated_amount":  allocated_amount,
        "total_amount":      frappe.db.get_value(invoice_doctype, invoice_name, "grand_total"),
        "outstanding_amount": frappe.db.get_value(invoice_doctype, invoice_name, "outstanding_amount"),
    })

    # Recalculate totals (ERPNext does this in validate)
    pe.set_amounts()
    pe.save(ignore_permissions=True)
    pe.reload()

    # If fully allocated, submit any pending status update
    frappe.db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Whitelisted: fetch match data for the UI (used by the standalone page)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_match_data(doc_name: str) -> dict:
    """Returns full match data for rendering in the custom UI page."""
    doc = frappe.get_doc("Payment Invoice Match", doc_name)
    return {
        "doc_name":   doc.name,
        "company":    doc.company,
        "party_type": doc.party_type,
        "status":     doc.status,
        "summary": {
            "payments_fetched": doc.total_payments_fetched,
            "invoices_fetched": doc.total_invoices_fetched,
            "proposed":         doc.matches_proposed,
            "approved":         doc.matches_approved,
            "rejected":         doc.matches_rejected,
            "reconciled":       flt(doc.total_amount_reconciled),
        },
        "lines": [
            {
                "name":               line.name,
                "payment_entry":      line.payment_entry,
                "payment_date":       str(line.payment_date or ""),
                "payment_amount":     flt(line.payment_amount),
                "payment_party":      line.payment_party or "",
                "invoice_type":       line.invoice_type or "",
                "invoice":            line.invoice or "",
                "invoice_date":       str(line.invoice_date or ""),
                "invoice_amount":     flt(line.invoice_amount),
                "outstanding_amount": flt(line.outstanding_amount),
                "confidence_score":   flt(line.confidence_score),
                "ai_reasoning":       line.ai_reasoning or "",
                "match_status":       line.match_status or "Pending",
                "allocated_amount":   flt(line.allocated_amount),
                "applied":            bool(line.applied),
            }
            for line in doc.match_lines
        ],
    }