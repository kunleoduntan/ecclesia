# ecclesia/ecclesia/doctype/bank_statement_upload/creator.py
"""
Creates Payments or Receipts documents from staged Bank Statement Upload Items.
Handles both immediate (inline) and batch (background job) modes.
"""

import frappe
from frappe.utils import flt, nowdate, now_datetime
from ecclesia.ecclesia.doctype.bank_statement_upload.ai_coder import (
    recalculate_wht
)


# ------------------------------------------------------------------ #
#  Single document creation                                            #
# ------------------------------------------------------------------ #

def create_document(item, import_doc) -> dict:
    """
    Create a single Payments or Receipts doc from an import item row.
    Returns {"success": True, "doctype": ..., "name": ...}
         or {"success": False, "error": ...}
    """
    try:
        _pre_validate(item)

        if item.doc_type == "Payments":
            name = _create_payment(item, import_doc)
        elif item.doc_type == "Receipts":
            name = _create_receipt(item, import_doc)
        else:
            return {"success": False, "error": f"Unknown doc_type: {item.doc_type}"}

        # Save alias learning
        _learn_alias(item, import_doc.company)

        return {"success": True, "doctype": item.doc_type, "name": name}

    except frappe.ValidationError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"BSU Creator — {item.transaction_date} {item.cleaned_description[:40]}")
        return {"success": False, "error": str(e)[:500]}


# ------------------------------------------------------------------ #
#  Payments document                                                   #
# ------------------------------------------------------------------ #

def _create_payment(item, import_doc) -> str:
    doc = frappe.new_doc("Payments")
    doc.company          = import_doc.company
    doc.transaction_date = item.transaction_date
    doc.trans_type       = item.trans_type or "Expense Payment"
    doc.payment_status   = "Draft"
    doc.remittance_bank  = item.bank_account
    doc.mode_of_payment  = "Electronic"
    doc.reference_no     = item.reference_no or _generate_ref(item)

    # Payee
    if item.party_type == "Supplier" and item.party_id:
        doc.payee_id      = item.party_id
        doc.supplier_name = frappe.db.get_value("Supplier", item.party_id, "supplier_name") or item.pay_name
    elif item.party_type == "Customer" and item.party_id:
        # Customer paying — use their name as beneficiary
        doc.payee_name    = frappe.db.get_value("Customer", item.party_id, "customer_name") or item.pay_name
    elif item.party_type == "Employee" and item.party_id:
        doc.payee_name    = frappe.db.get_value("Employee", item.party_id, "employee_name") or item.pay_name
    else:
        # Non-party transaction — use pay_name (the universal field)
        doc.payee_name    = item.pay_name or item.cleaned_description

    # Currency & amounts
    doc.payment_currency    = item.payment_currency or "NGN"
    doc.exchange_rate       = flt(item.exchange_rate or 1)
    if doc.payment_currency == "NGN":
        doc.amount_paid          = flt(item.debit_amount)
    else:
        doc.amount_paid_in_fc    = flt(item.debit_amount)
    doc.local_currency_amount    = flt(item.local_currency_amount)

    # Coding
    doc.account_to_debit    = item.account_to_debit
    doc.cost_center         = item.cost_center
    doc.department          = item.department
    doc.cashflow_type       = item.cashflow_type
    doc.project             = item.project
    doc.transaction_purposes = item.cleaned_description

    # WHT — only if user opted in
    if item.apply_wht and flt(item.wht_rate) > 0:
        doc.deduct_wht  = 1
        doc.whtax_rate  = flt(item.wht_rate)
        doc.wht_amount  = flt(item.wht_amount)
        doc.net_amount  = flt(item.net_amount)
    else:
        doc.deduct_wht  = 0
        doc.net_amount  = flt(item.local_currency_amount)

    # Accounting dimensions
    doc.branch           = None  # Set from cost_center mapping if needed
    doc.create_accounting_entries = 1

    doc.insert(ignore_permissions=True)
    return doc.name


# ------------------------------------------------------------------ #
#  Receipts document                                                   #
# ------------------------------------------------------------------ #

def _create_receipt(item, import_doc) -> str:
    doc = frappe.new_doc("Receipts")
    doc.company          = import_doc.company
    doc.transaction_date = item.transaction_date
    doc.trans_type       = item.trans_type or "Revenue Receipt"
    doc.receipt_status   = "Draft"
    doc.remittance_bank  = item.bank_account
    doc.mode_of_payment  = "Electronic"
    doc.reference_no     = item.reference_no or _generate_ref(item)

    # Payer
    if item.party_type == "Customer" and item.party_id:
        doc.customer_id   = item.party_id
        doc.payer_name    = frappe.db.get_value("Customer", item.party_id, "customer_name") or item.pay_name
    elif item.party_type == "Supplier" and item.party_id:
        # Supplier refund
        doc.payer_name    = frappe.db.get_value("Supplier", item.party_id, "supplier_name") or item.pay_name
    elif item.party_type == "Member" and item.party_id:
        doc.payer_name    = item.pay_name or item.party_id
    else:
        doc.payer_name    = item.pay_name or item.cleaned_description

    # Currency & amounts
    doc.receipt_currency     = item.payment_currency or "NGN"
    doc.exchange_rate        = flt(item.exchange_rate or 1)
    if doc.receipt_currency == "NGN":
        doc.amount_received       = flt(item.credit_amount)
    else:
        doc.amount_received_in_fc = flt(item.credit_amount)
    doc.local_currency_amount    = flt(item.local_currency_amount)

    # Coding
    doc.account_to_credit   = item.account_to_credit
    doc.cost_center         = item.cost_center
    doc.cashflow_type       = item.cashflow_type
    doc.project             = item.project
    doc.transaction_purposes = item.cleaned_description

    # WHT on receipts (user discretion)
    if item.apply_wht and flt(item.wht_rate) > 0:
        doc.deduct_wht  = 1
        doc.wht_rate    = f"{int(item.wht_rate)}%"
        doc.wht_amount  = flt(item.wht_amount)
        doc.net_amount  = flt(item.net_amount)

    doc.create_accounting_entries = 1
    doc.insert(ignore_permissions=True)
    return doc.name


# ------------------------------------------------------------------ #
#  Validation before creation                                          #
# ------------------------------------------------------------------ #

def _pre_validate(item):
    errors = []

    if not item.transaction_date:
        errors.append("Transaction date is missing")

    if not item.bank_account:
        errors.append("Bank account could not be resolved — check bank_account_column in Excel")

    if flt(item.debit_amount) == 0 and flt(item.credit_amount) == 0:
        errors.append("Amount is zero — row skipped")

    if not item.trans_type:
        errors.append("Transaction type is not set")

    if item.doc_type == "Payments":
        if not item.account_to_debit:
            errors.append("Account to Debit is required for Payments")
        if item.trans_type == "Expense Payment" and not item.cost_center:
            errors.append("Cost Center is mandatory for Expense Payment")

    if item.doc_type == "Receipts":
        if item.trans_type not in ("Customer Receipt", "Customer Refund",
                                   "Member Tithe", "Pledges") and not item.account_to_credit:
            errors.append("Account to Credit is required")

    # Check accounting period
    if item.transaction_date:
        _check_accounting_period(item.transaction_date)

    if errors:
        raise frappe.ValidationError(" | ".join(errors))


def _check_accounting_period(txn_date: str):
    """Raise if the period is closed in ERPNext."""
    closed = frappe.db.sql(
        """SELECT name FROM `tabAccounting Period`
           WHERE %s BETWEEN start_date AND end_date
             AND closed = 1 LIMIT 1""",
        txn_date
    )
    if closed:
        raise frappe.ValidationError(
            f"Accounting period containing {txn_date} is closed. "
            "Open the period first or adjust the transaction date."
        )


# ------------------------------------------------------------------ #
#  Batch background job                                                #
# ------------------------------------------------------------------ #

def run_batch(import_name: str, batch_size: int = 50):
    """
    Frappe background job.
    Processes import items in chunks, updating progress via realtime.
    """
    import_doc = frappe.get_doc("Bank Statement Upload", import_name)
    created = failed = 0
    total_to_process = sum(
        1 for i in import_doc.import_items
        if i.row_status in ("Ready", "Review")
    )

    chunk = []
    for item in import_doc.import_items:
        if item.row_status not in ("Ready", "Review"):
            continue
        chunk.append(item)

        if len(chunk) >= batch_size:
            c, f = _process_chunk(chunk, import_doc)
            created += c
            failed  += f
            chunk    = []
            _emit_progress(import_doc, created, failed, total_to_process)

    # Process remainder
    if chunk:
        c, f = _process_chunk(chunk, import_doc)
        created += c
        failed  += f

    # Final save
    import_doc.reload()
    for item in import_doc.import_items:
        pass  # Already updated per chunk

    import_doc._update_summary()
    import_doc.import_status = "Completed" if failed == 0 else "Completed with Errors"
    import_doc._append_log(
        f"Batch complete. Created: {created}, Failed: {failed}"
    )
    import_doc.save()
    _emit_progress(import_doc, created, failed, total_to_process, done=True)


def _process_chunk(chunk: list, import_doc) -> tuple[int, int]:
    created = failed = 0
    for item in chunk:
        result = create_document(item, import_doc)
        if result["success"]:
            item.row_status       = "Created"
            item.created_doc_type  = result["doctype"]
            item.created_doc_name  = result["name"]
            created += 1
        else:
            item.row_status    = "Failed"
            item.failure_reason = result["error"]
            failed += 1

    # Save in one commit per chunk
    frappe.db.sql(
        "UPDATE `tabBank Statement Upload Item` SET row_status=%s, "
        "failure_reason=%s, created_doc_type=%s, created_doc_name=%s "
        "WHERE name=%s",
        tuple()  # Updated individually below via ORM
    )
    # Use frappe bulk approach: save parent and let child rows cascade
    import_doc.reload()
    import_doc._update_summary()
    import_doc.save(ignore_version=True)
    frappe.db.commit()

    return created, failed


def _emit_progress(import_doc, created: int, failed: int,
                   total: int, done: bool = False):
    pct = round(created / total * 100) if total else 100
    frappe.publish_realtime(
        event="bsu_progress",
        message={
            "import_name": import_doc.name,
            "created":  created,
            "failed":   failed,
            "total":    total,
            "pct":      pct,
            "done":     done,
            "status":   import_doc.import_status
        },
        user=import_doc.owner
    )


# ------------------------------------------------------------------ #
#  Alias learning                                                      #
# ------------------------------------------------------------------ #

def _learn_alias(item, company: str):
    """
    After successful creation, upsert a Bank Statement Alias
    so future imports auto-match this narration pattern.
    """
    pattern = (item.raw_narration or "")[:100].strip()
    if not pattern:
        return

    existing = frappe.db.exists("Bank Statement Alias", {"raw_pattern": pattern})
    if existing:
        frappe.db.sql(
            "UPDATE `tabBank Statement Alias` "
            "SET usage_count = usage_count + 1, last_used = NOW() "
            "WHERE raw_pattern = %s", pattern
        )
    else:
        alias = frappe.new_doc("Bank Statement Alias")
        alias.raw_pattern     = pattern
        alias.cleaned_name    = item.pay_name or item.cleaned_description
        alias.entity_type     = item.party_type or ""
        alias.supplier_id     = item.party_id if item.party_type == "Supplier" else ""
        alias.customer_id     = item.party_id if item.party_type == "Customer" else ""
        alias.account_to_debit = item.account_to_debit or item.account_to_credit or ""
        alias.trans_type      = item.trans_type or ""
        alias.cashflow_type   = item.cashflow_type or ""
        alias.company         = company
        alias.usage_count     = 1
        alias.insert(ignore_permissions=True)


def _generate_ref(item) -> str:
    """Fallback reference number when none supplied."""
    dt = str(item.transaction_date or "").replace("-", "")
    amt = str(int(flt(item.debit_amount or item.credit_amount or 0)))
    return f"BSU{dt[-6:]}{amt[-4:]}"