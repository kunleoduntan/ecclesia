# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/api/btp_bank_export.py
"""
Bank Transaction Processor — Bank Payment Export & Attach/Email
═══════════════════════════════════════════════════════════════
Separate API file for generating bank payment files directly from
a Bank Transaction Processor document.

Only PE-type rows are included in the payment file:
    Supplier Payment, Customer Receipt, Transfer Out, Transfer In,
    Customer Refund, Supplier Refund

JE-type rows (Payment / Receipt) are journal entries for bank charges /
income and are excluded — they are NOT payment instructions to the bank.

Reuses all format generators and helper utilities from bank_payment_export.py
via import rather than duplicating code.

Whitelisted methods:
    generate_btp_payment_file(processor_name, bank_format)
    preview_btp_payment_file(processor_name, bank_format)
    attach_btp_payment_file(processor_name, bank_format)
    email_btp_payment_file(processor_name, bank_format, recipients, subject, message)
    get_btp_attached_files(processor_name)

Deploy to: apps/ecclesia/ecclesia/api/btp_bank_export.py
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate
import base64
import json

# ── Reuse all format generators and helpers from the main export module ───────
from ecclesia.api.bank_payment_export import (
    FORMATS,
    _generate_file,
    _get_bank_bic,
    _get_bank_bic_from_account,
    _get_company_address,
    _clean_acc,
    _month_label,
)

# PE-type rows are the only ones that represent payment instructions to the bank
# Trans types included in the bank payment file.
# Payment (JE) is included — it represents a real outflow instruction to the bank
# (e.g. rent, utilities, bank charges paid via transfer).
# Receipt (JE) is excluded — it is income already credited by the bank,
# not an outgoing payment instruction.
# Pending is excluded — not yet classified.
_BTP_PE_TYPES = {
    "Supplier Payment",
    "Customer Receipt",
    "Transfer Out",
    "Transfer In",
    "Customer Refund",
    "Supplier Refund",
    "Payment",          # JE outflow — real payment instruction to the bank
}


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN ENTRY POINTS
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def generate_btp_payment_file(processor_name, bank_format="zenith_iso20022"):
    """
    Generate a bank payment file from a Bank Transaction Processor document.

    Only rows with trans_type in PE_TYPES are included (Supplier Payment,
    Customer Receipt, Transfer Out/In, Customer Refund, Supplier Refund).
    Journal Entry rows (Payment / Receipt) are excluded.

    Returns base64-encoded file + metadata.
    """
    if bank_format not in FORMATS:
        frappe.throw(_(f"Unsupported format: {bank_format}"))

    proc = frappe.get_doc("Bank Transaction Processor", processor_name)
    if proc.docstatus not in (0, 1):
        frappe.throw(_("Processor must be in Draft or Submitted status."))

    # ── Enrich payment rows ───────────────────────────────────────────────────
    payments = _enrich_btp_payments(proc)

    if not payments:
        frappe.throw(_(
            "No payment-eligible rows found. Only Supplier Payment, Customer Receipt, "
            "Transfer Out/In, Customer Refund and Supplier Refund rows are included. "
            "Journal Entry rows (Payment / Receipt) are excluded."
        ))

    # ── Generate file ─────────────────────────────────────────────────────────
    content, filename = _generate_file(
        payments      = payments,
        bank_format   = bank_format,
        company       = proc.company,
        debit_account = proc.bank_account,
        payment_date  = proc.posting_date,
        narration     = f"BTP {processor_name} {proc.title or ''}".strip(),
    )

    return {
        "success":      True,
        "file_data":    base64.b64encode(
                            content.encode("utf-8") if isinstance(content, str) else content
                        ).decode(),
        "file_name":    filename,
        "format":       FORMATS[bank_format]["label"],
        "row_count":    len(payments),
        "total_amount": sum(p["amount"] for p in payments),
        "excluded_je_rows": _count_je_rows(proc),
    }


@frappe.whitelist()
def preview_btp_payment_file(processor_name, bank_format="zenith_iso20022"):
    """Return first 3 rows as a text preview before download."""
    result = generate_btp_payment_file(processor_name, bank_format)
    if not result.get("success"):
        return result
    content = base64.b64decode(result["file_data"]).decode("utf-8", errors="replace")
    lines   = content.splitlines()
    return {
        **result,
        "preview":     "\n".join(lines[:4]),   # header + 3 data rows
        "total_lines": len(lines),
    }


@frappe.whitelist()
def attach_btp_payment_file(processor_name, bank_format="zenith_iso20022"):
    """
    Generate the payment file and attach it as a private File record
    linked to the Bank Transaction Processor document.
    Returns the file URL.
    """
    result = generate_btp_payment_file(processor_name, bank_format)
    if not result.get("success"):
        frappe.throw(_(result.get("error", "File generation failed")))

    file_content = base64.b64decode(result["file_data"])
    file_name    = result["file_name"]

    from frappe.utils.file_manager import save_file
    file_doc = save_file(
        fname      = file_name,
        content    = file_content,
        dt         = "Bank Transaction Processor",
        dn         = processor_name,
        folder     = "Home/Bank Payment Files",
        decode     = False,
        is_private = 1,
    )

    # Audit comment
    frappe.get_doc({
        "doctype":            "Comment",
        "comment_type":       "Info",
        "reference_doctype":  "Bank Transaction Processor",
        "reference_name":     processor_name,
        "content": (
            f"Bank payment file attached: {file_name} · "
            f"{result['row_count']} rows · ₦{result['total_amount']:,.2f} · "
            f"{bank_format} · {frappe.utils.now()}"
        ),
    }).insert(ignore_permissions=True)

    frappe.db.commit()

    return {
        "success":      True,
        "file_name":    file_name,
        "file_url":     file_doc.file_url,
        "row_count":    result["row_count"],
        "total_amount": result["total_amount"],
        "format":       result.get("format", bank_format),
    }


@frappe.whitelist()
def email_btp_payment_file(processor_name, bank_format="zenith_iso20022",
                            recipients=None, subject=None, message=None):
    """
    Generate the payment file and send it as an email attachment.

    recipients: comma-separated email addresses (defaults to current user)
    subject:    email subject (auto-generated if blank)
    message:    email body HTML (auto-generated if blank)
    """
    result = generate_btp_payment_file(processor_name, bank_format)
    if not result.get("success"):
        frappe.throw(_(result.get("error", "File generation failed")))

    file_content = base64.b64decode(result["file_data"])
    file_name    = result["file_name"]

    # Resolve recipients
    if not recipients:
        recipients = frappe.session.user
    if isinstance(recipients, str):
        recipient_list = [r.strip() for r in recipients.split(",") if r.strip()]
    else:
        recipient_list = list(recipients)

    proc = frappe.get_doc("Bank Transaction Processor", processor_name)

    if not subject:
        subject = f"Bank Payment File — {processor_name} — {proc.title or ''}"

    if not message:
        message = f"""
<p>Please find attached the bank payment file generated from
<b>Bank Transaction Processor {processor_name}</b>.</p>
<ul>
  <li><b>Title:</b> {proc.title or processor_name}</li>
  <li><b>Company:</b> {proc.company or '—'}</li>
  <li><b>Bank Account:</b> {proc.bank_account or '—'}</li>
  <li><b>Posting Date:</b> {proc.posting_date or '—'}</li>
  <li><b>File:</b> {file_name}</li>
  <li><b>Format:</b> {result.get('format', bank_format)}</li>
  <li><b>Payment Rows:</b> {result['row_count']}</li>
  <li><b>Total Amount:</b> ₦{result['total_amount']:,.2f}</li>
  <li><b>Generated:</b> {frappe.utils.now()}</li>
</ul>
<p>This file should be uploaded to your bank's Corporate Internet Banking
portal or transmitted via the configured SFTP channel.</p>
<p style="color:#64748B;font-size:12px">
Generated by Ecclesia ERP — Value Impacts Consulting</p>
"""

    frappe.sendmail(
        recipients        = recipient_list,
        subject           = subject,
        message           = message,
        attachments       = [{"fname": file_name, "fcontent": file_content}],
        reference_doctype = "Bank Transaction Processor",
        reference_name    = processor_name,
    )

    # Audit comment
    frappe.get_doc({
        "doctype":           "Comment",
        "comment_type":      "Info",
        "reference_doctype": "Bank Transaction Processor",
        "reference_name":    processor_name,
        "content": (
            f"Bank payment file emailed: {file_name} to "
            f"{', '.join(recipient_list)} · {frappe.utils.now()}"
        ),
    }).insert(ignore_permissions=True)

    frappe.db.commit()

    return {
        "success":      True,
        "file_name":    file_name,
        "recipients":   recipient_list,
        "row_count":    result["row_count"],
        "total_amount": result["total_amount"],
    }


@frappe.whitelist()
def get_btp_attached_files(processor_name):
    """Return list of previously attached bank payment files for this processor."""
    files = frappe.db.get_all(
        "File",
        filters={
            "attached_to_doctype": "Bank Transaction Processor",
            "attached_to_name":    processor_name,
            "file_name":           ["like", "BankPayment%"],
        },
        fields=["name", "file_name", "file_url", "file_size", "creation", "modified_by"],
        order_by="creation desc",
        limit=20,
    )
    return {"success": True, "files": files}


# ══════════════════════════════════════════════════════════════════════════════
#  SEND — wraps bank_send_api.py for BTP context
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def send_btp_payment(processor_name, send_channel, gateway_name):
    """
    Generate and send the payment file from a Bank Transaction Processor.

    Generates the file via generate_btp_payment_file(), then routes to the
    same send channels used for Payroll Entry and Batch Bank Transaction:
        sftp_upload       → SFTP to bank file server
        paystack_bulk     → Paystack Bulk Transfer API
        flutterwave_bulk  → Flutterwave Bulk Transfer API
        squad_bulk        → Squad (GTBank) Bulk Transfer API
        manual_download   → Return base64 for browser download

    Returns send result with batch reference (if aggregator) or remote path (SFTP).
    """
    from ecclesia.api import bank_send_api

    gw     = frappe.get_doc("Payment Gateway Settings", gateway_name)
    fmt    = gw.bank_export_format or "zenith_iso20022"
    result = generate_btp_payment_file(processor_name, fmt)

    if not result.get("success"):
        return result

    # Delegate to the existing send dispatcher in bank_send_api
    send_result = bank_send_api._dispatch_send(
        result      = result,
        send_channel= send_channel,
        gateway     = gw,
        source_doc  = processor_name,
        source_type = "Bank Transaction Processor",
    )
    return send_result


# ══════════════════════════════════════════════════════════════════════════════
#  DATA ENRICHMENT
# ══════════════════════════════════════════════════════════════════════════════

def _enrich_btp_payments(proc):
    """
    Build the standardised payment list from a Bank Transaction Processor.

    Rules:
    • PE-type rows + Payment (JE outflow) are included. Receipt and Pending are excluded.
    • Creditor name: party_name (auto-set from party link) or payee_name.
    • Creditor account: payee_account_no field (new field to add to BTL).
      Falls back to Supplier/Customer bank account if not set directly.
    • Creditor bank BIC: looked up from payee_bank_name field.
    • Execution date: row.posting_date (each row can have its own date).
    • Amount: row.amount.
    • Currency: row.transaction_currency or NGN.
    • Narration: row.remark.
    """
    comp_name = proc.company
    company   = frappe.get_doc("Company", comp_name)

    # Resolve gateway for this company
    gws = frappe.db.get_all(
        "Payment Gateway Settings",
        filters={"company": comp_name, "enabled": 1},
        fields=["name"],
        order_by="is_default desc",
        limit=1
    )
    gateway_name = gws[0].name if gws else None

    debt_addr = _get_company_address(company, gateway_name)
    debt_bic  = _get_bank_bic_from_account(proc.bank_account, comp_name, gateway_name)
    acc_no    = _clean_acc(proc.bank_account, comp_name, gateway_name)

    payments = []

    for row in proc.get("transactions", []):
        tt = row.get("trans_type") or ""
        if tt not in _BTP_PE_TYPES:
            continue  # Skip Receipt and Pending rows

        # ── Creditor name ─────────────────────────────────────────────────────
        # Payment (JE) rows: party/party_name are cleared by JS — use payee_name.
        # PE-type rows: party_name is auto-set from party link — use that first.
        cred_name = (
            row.get("party_name") or   # PE-type rows (Supplier/Customer link)
            row.get("payee_name") or   # Payment (JE) rows — user-entered payee
            row.get("party") or ""
        )

        # ── Creditor bank account number ──────────────────────────────────────
        # For all row types: payee_account_no is the primary source (user fills this).
        # For PE-type rows only: fall back to party bank account master.
        cred_acc_no = getattr(row, "payee_account_no", "") or ""

        if not cred_acc_no and row.get("party") and row.get("party_type"):
            # PE-type rows only — Payment rows have no party set
            cred_acc_no = _get_party_bank_account_no(row.get("party_type"), row.get("party"))

        # ── Creditor bank BIC ─────────────────────────────────────────────────
        # payee_bank_name is the primary source for all row types.
        # For PE-type rows only: fall back to party bank account master.
        cred_bank_name = getattr(row, "payee_bank_name", "") or ""
        cred_bic       = _get_bank_bic(cred_bank_name)

        if not cred_bic and row.get("party") and row.get("party_type"):
            # PE-type rows only — Payment rows have no party set
            cred_bic = _get_party_bank_bic(row.get("party_type"), row.get("party"))

        # ── Currency ──────────────────────────────────────────────────────────
        currency = row.get("transaction_currency") or "NGN"

        # ── Execution date ────────────────────────────────────────────────────
        exec_dt = str(getdate(row.get("posting_date") or proc.posting_date)).replace("-", "/")

        payments.append({
            # Debtor (company / our bank account)
            "debt_name":      company.company_name.upper(),
            "debt_address":   debt_addr,
            "debt_country":   "NG",
            "debt_bic":       debt_bic,
            "debt_acc_no":    acc_no,
            "debt_acc_type":  "DOMESTIC",
            "debt_acc_bic":   debt_bic,

            # Creditor (supplier / customer / counter-party)
            "cred_name":         cred_name,
            "cred_city":         "LAGOS",
            "cred_country":      "NG",
            "cred_district":     "",
            "cred_acc_no":       cred_acc_no,
            "cred_acc_type":     "DOMESTIC",
            "cred_acc_country":  "NG",
            "cred_acc_bic":      cred_bic,
            "cred_bank_name":    cred_bank_name,

            # Transaction
            "amount":         flt(row.get("amount")),
            "currency":       currency,
            "execution_date": exec_dt,
            "details":        (row.get("remark") or row.get("transaction_description") or "")[:35],
            "reference":      row.get("reference_no") or row.get("name") or "",
        })

    return payments


def _count_je_rows(proc):
    """Return count of rows excluded from the payment file (Receipt + Pending only)."""
    return sum(
        1 for row in proc.get("transactions", [])
        if (row.get("trans_type") or "") not in _BTP_PE_TYPES
    )


def _get_party_bank_account_no(party_type, party):
    """
    Fallback: look up bank account number from the Supplier or Customer master.
    Checks ERPNext Bank Account linked to the party.
    """
    if not party or not party_type:
        return ""
    # ERPNext stores party bank accounts in the Bank Account DocType
    acc = frappe.db.get_all(
        "Bank Account",
        filters={"party_type": party_type, "party": party, "is_default": 1},
        fields=["bank_account_no"],
        limit=1,
    )
    if acc:
        return acc[0].bank_account_no or ""
    # Try without is_default flag
    acc = frappe.db.get_all(
        "Bank Account",
        filters={"party_type": party_type, "party": party},
        fields=["bank_account_no"],
        limit=1,
    )
    return (acc[0].bank_account_no or "") if acc else ""


def _get_party_bank_bic(party_type, party):
    """
    Fallback: look up BIC/SWIFT from the Supplier or Customer bank account.
    """
    if not party or not party_type:
        return ""
    acc = frappe.db.get_all(
        "Bank Account",
        filters={"party_type": party_type, "party": party},
        fields=["bank"],
        order_by="is_default desc",
        limit=1,
    )
    if not acc or not acc[0].bank:
        return ""
    swift = frappe.db.get_value("Bank", acc[0].bank, "swift_number") or ""
    if swift:
        return swift
    # Last resort: name-based BIC lookup
    return _get_bank_bic(acc[0].bank)