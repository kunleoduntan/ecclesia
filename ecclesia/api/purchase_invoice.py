# -*- coding: utf-8 -*-
# Copyright (c) 2026, Value Impacts Consulting

"""
Purchase Invoice API Module
File: ecclesia/api/purchase_invoice.py

hooks.py (required):
    doc_events = {
        "Purchase Invoice": {
            "validate": "ecclesia.api.purchase_invoice.purchase_invoice_validate",
            "before_cancel": "ecclesia.api.purchase_invoice.purchase_invoice_before_cancel",
            "on_cancel": "ecclesia.api.purchase_invoice.purchase_invoice_on_cancel",
        }
    }
"""

import frappe
from frappe import _
from frappe.utils import getdate, flt, add_months, format_date, nowdate, cint


# ============================================================================
# DOCUMENT HOOKS
# ============================================================================

def purchase_invoice_validate(doc, method):
    if doc.custom_is_amortized_cost:
        validate_amortization(doc)
        calculate_amortization_schedule(doc)

    if doc.custom_is_shared_cost and doc.custom_cost_center_distribution:
        validate_cost_center_distribution(doc)

    if doc.custom_transaction_history:
        calculate_transaction_balances(doc)


def purchase_invoice_before_cancel(doc, method):
    """
    Runs while the invoice is still submitted in the DB and BEFORE Frappe's
    linked-document check. Cancels everything linked to this invoice so the
    cancel succeeds even if the invoice has been paid:

      1. Amortization Journal Entries (cheque_no = invoice name)
      2. Payment Entries referencing the invoice
      3. Journal Entries referencing the invoice (Journal Entry Account.reference_name)
      4. Return / Debit Notes against the invoice

    Any failure throws, so the whole cancel is rolled back (no half-cancelled state).
    """
    cleanup_linked_documents(doc)


def purchase_invoice_on_cancel(doc, method):
    """Safety net: sweep any amortization JEs that may remain (idempotent)."""
    delete_related_journal_entries(doc)


# ============================================================================
# VALIDATION
# ============================================================================

def validate_amortization(doc):
    if not doc.custom_frequency:
        frappe.throw(_("Frequency is required for amortization"))
    if not doc.custom_start_date:
        frappe.throw(_("Start Date is required for amortization"))
    if not doc.custom_expense_account:
        frappe.throw(_("Expense Account is required for amortization"))
    if not doc.custom_deferred_expense_account:
        frappe.throw(_("Deferred Expense Account is required for amortization"))
    if not doc.custom_charged_amount:
        frappe.throw(_("Charged Amount is required for amortization"))
    if not doc.custom_description:
        frappe.throw(_("Description is required for amortization"))
    if not doc.cost_center and not doc.custom_is_shared_cost:
        frappe.throw(_("Cost Center is required for amortization"))

    validate_account(doc.custom_expense_account, "Expense Account")
    validate_account(doc.custom_deferred_expense_account, "Deferred Expense Account")


def validate_account(account, label):
    if not account:
        return
    is_group = frappe.db.get_value("Account", account, "is_group")
    if is_group:
        frappe.throw(_(
            "{0} ({1}) is a group account and cannot be used for posting"
        ).format(label, account))


def validate_cost_center_distribution(doc):
    total = sum(flt(row.distribution) for row in doc.custom_cost_center_distribution)
    if abs(total - 100) > 0.01:
        frappe.throw(_(
            "Total cost center distribution must equal 100%. Current total: {0}%"
        ).format(total))


# ============================================================================
# CALCULATIONS (called on validate)
# ============================================================================

def calculate_amortization_schedule(doc):
    if not doc.custom_charged_amount or not doc.custom_no_of_periods:
        return

    doc.custom_amortization_schedule = []
    periods = cint(doc.custom_no_of_periods)
    amount_per_period = flt(doc.custom_charged_amount)
    remaining_balance = amount_per_period * periods

    for i in range(periods):
        posting_date = add_months(
            getdate(doc.custom_start_date),
            i * cint(doc.custom_next_schedule or 1)
        )
        remaining_balance -= amount_per_period

        doc.append("custom_amortization_schedule", {
            "date": posting_date,
            "title": doc.supplier_name,
            "amount": amount_per_period,
            "transaction_description": doc.custom_description or "",
            "frequency": doc.custom_frequency,
            "period": periods,
            "account_to_debit": doc.custom_expense_account,
            "account_to_credit": doc.custom_deferred_expense_account,
            "source_doc": "Purchase Invoice",
            "source_doc_ref": doc.name,
            "prepayment_balance": remaining_balance if remaining_balance > 0 else 0
        })


def calculate_transaction_balances(doc):
    balance = flt(doc.custom_opening_balance)
    total_purchase = 0
    total_paid = 0

    for row in doc.custom_transaction_history:
        total_purchase += flt(row.invoice_amount)
        total_paid += flt(row.paid_amount)
        balance += flt(row.invoice_amount) - flt(row.paid_amount)
        row.balance = balance

    doc.custom_cum_paid_amount = total_paid
    doc.custom_total_purchases = total_purchase
    doc.custom_balance = balance


# ============================================================================
# AMORTIZATION JOURNAL ENTRY CREATION (button-triggered only)
# ============================================================================

@frappe.whitelist()
def create_amortization_entries(purchase_invoice):
    doc = frappe.get_doc("Purchase Invoice", purchase_invoice)

    # ===============================
    # VALIDATIONS
    # ===============================
    if doc.custom_is_amortized_cost != 1:
        frappe.msgprint(_("Amortization not enabled on this invoice"))
        return

    if doc.docstatus != 1:
        frappe.throw(_("Please submit the invoice before creating amortization entries"))

    if not doc.custom_frequency:
        frappe.throw(_("Custom Frequency is required"))
    if not doc.custom_next_schedule:
        frappe.throw(_("Custom Next Schedule is required"))
    if not doc.custom_no_of_periods:
        frappe.throw(_("Number of periods is missing"))
    if not doc.custom_start_date:
        frappe.throw(_("Start date is missing"))
    if not doc.custom_expense_account:
        frappe.throw(_("Expense account is missing"))
    if not doc.custom_deferred_expense_account:
        frappe.throw(_("Deferred expense account is missing"))
    if not doc.custom_charged_amount:
        frappe.throw(_("Charged amount is missing"))
    if not doc.custom_description:
        frappe.throw(_("Please enter a description"))

    # Check for already existing entries
    existing = frappe.get_all("Journal Entry",
        filters={
            "cheque_no": doc.name,
            "docstatus": ["!=", 2]
        },
        limit=1
    )
    if existing:
        frappe.throw(_("Amortization entries already exist for {0}").format(doc.name))

    # ===============================
    # CREATION LOOP
    # ===============================
    if doc.custom_is_shared_cost and doc.custom_cost_center_distribution:
        created = _create_shared_cost_entries(doc)
    else:
        created = _create_single_cost_entries(doc)

    frappe.msgprint(_("{0} Journal Entries created successfully (Draft).").format(created))
    return {"success": True, "entries_created": created}


def _create_single_cost_entries(doc):
    if not doc.cost_center:
        frappe.throw(_("Cost Center is required for amortization"))

    created = 0

    for i in range(int(doc.custom_no_of_periods)):
        try:
            next_due_date = add_months(
                getdate(doc.custom_start_date),
                i * int(doc.custom_next_schedule)
            )

            je = frappe.new_doc("Journal Entry")
            je.voucher_type = "Journal Entry"
            je.company = doc.company
            je.posting_date = next_due_date
            je.user_remark = doc.custom_description
            je.cheque_no = doc.name
            je.cheque_date = doc.posting_date
            je.paid_to_or_received_from = doc.supplier_name

            # Debit — Expense Account
            je.append("accounts", {
                "account": doc.custom_expense_account,
                "debit_in_account_currency": flt(doc.custom_charged_amount),
                "cost_center": doc.cost_center,
                "against_account": doc.custom_deferred_expense_account,
                "user_remark": doc.custom_description
            })

            # Credit — Deferred Expense Account
            je.append("accounts", {
                "account": doc.custom_deferred_expense_account,
                "credit_in_account_currency": flt(doc.custom_charged_amount),
                "against_account": doc.custom_expense_account,
                "user_remark": doc.custom_description
            })

            je.set_total_debit_credit()
            je.insert(ignore_permissions=True)
            created += 1

        except Exception:
            frappe.log_error(frappe.get_traceback(), "Amortization JE Failed - Period {}".format(i + 1))

    return created


def _create_shared_cost_entries(doc):
    total_pct = sum(flt(row.distribution) for row in doc.custom_cost_center_distribution)
    if abs(total_pct - 100) > 0.01:
        frappe.throw(_(
            "Total cost center distribution must equal 100%. Current: {0}%"
        ).format(total_pct))

    created = 0

    for i in range(int(doc.custom_no_of_periods)):
        try:
            next_due_date = add_months(
                getdate(doc.custom_start_date),
                i * int(doc.custom_next_schedule)
            )

            je = frappe.new_doc("Journal Entry")
            je.voucher_type = "Journal Entry"
            je.company = doc.company
            je.posting_date = next_due_date
            je.user_remark = doc.custom_description
            je.cheque_no = doc.name
            je.cheque_date = doc.posting_date
            je.paid_to_or_received_from = doc.supplier_name

            # One debit line per cost center
            for cc_row in doc.custom_cost_center_distribution:
                split_amount = flt(doc.custom_charged_amount) * flt(cc_row.distribution) / 100.0
                je.append("accounts", {
                    "account": doc.custom_expense_account,
                    "debit_in_account_currency": split_amount,
                    "cost_center": cc_row.cost_center,
                    "against_account": doc.custom_deferred_expense_account,
                    "user_remark": "{} - {} ({}%)".format(
                        doc.custom_description,
                        cc_row.title or "",
                        cc_row.distribution
                    )
                })

            # Single credit line
            je.append("accounts", {
                "account": doc.custom_deferred_expense_account,
                "credit_in_account_currency": flt(doc.custom_charged_amount),
                "against_account": doc.custom_expense_account,
                "user_remark": doc.custom_description
            })

            je.set_total_debit_credit()
            je.insert(ignore_permissions=True)
            created += 1

        except Exception:
            frappe.log_error(frappe.get_traceback(), "Shared Cost JE Failed - Period {}".format(i + 1))

    return created


# ============================================================================
# FORCE CANCEL — CANCEL INVOICE + ALL LINKED DOCUMENTS
# ============================================================================

def _cancel_submitted(doctype, name):
    """Cancel a submitted document (no-op if not submitted)."""
    d = frappe.get_doc(doctype, name)
    if d.docstatus == 1:
        d.flags.ignore_permissions = True
        d.cancel()
        return True
    return False


def get_linked_amortization_journals(doc):
    """Journal Entries created from this invoice (link field: cheque_no)."""
    return frappe.get_all(
        "Journal Entry",
        filters={"cheque_no": doc.name, "docstatus": ["!=", 2]},
        pluck="name",
        order_by="posting_date desc, creation desc"
    )


def get_linked_payment_entries(doc):
    """Submitted Payment Entries that settle this invoice."""
    rows = frappe.get_all(
        "Payment Entry Reference",
        filters={
            "reference_doctype": "Purchase Invoice",
            "reference_name": doc.name,
            "docstatus": 1
        },
        fields=["parent"]
    )
    return list(dict.fromkeys(r.parent for r in rows))


def get_linked_reference_journals(doc, exclude=None):
    """Submitted Journal Entries that reference this invoice on an account line
    (e.g. payments / adjustments posted through a Journal Entry)."""
    exclude = set(exclude or [])
    rows = frappe.get_all(
        "Journal Entry Account",
        filters={
            "reference_type": "Purchase Invoice",
            "reference_name": doc.name,
            "docstatus": 1
        },
        fields=["parent"]
    )
    return [p for p in dict.fromkeys(r.parent for r in rows) if p not in exclude]


def get_linked_returns(doc):
    """Submitted return / debit notes raised against this invoice."""
    return frappe.get_all(
        "Purchase Invoice",
        filters={"return_against": doc.name, "docstatus": 1},
        pluck="name"
    )


def cleanup_linked_documents(doc):
    """Cancel every document linked to the Purchase Invoice, in safe order."""
    log = {
        "journals": [],
        "payments": [],
        "reference_journals": [],
        "returns": [],
        "shared_payments": []
    }

    # 1. Amortization journals (cheque_no link) — cancel then delete
    for name in get_linked_amortization_journals(doc):
        _cancel_submitted("Journal Entry", name)
        frappe.delete_doc("Journal Entry", name, force=1, ignore_permissions=True)
        log["journals"].append(name)

    # 2. Payment Entries — releases the "paid" status
    for name in get_linked_payment_entries(doc):
        pe_refs = frappe.get_all(
            "Payment Entry Reference",
            filters={"parent": name},
            fields=["reference_doctype", "reference_name"]
        )
        others = [
            r for r in pe_refs
            if not (r.reference_doctype == "Purchase Invoice" and r.reference_name == doc.name)
        ]
        if others:
            log["shared_payments"].append(name)
        if _cancel_submitted("Payment Entry", name):
            log["payments"].append(name)

    # 3. Journal Entries that reference this invoice
    for name in get_linked_reference_journals(doc):
        if _cancel_submitted("Journal Entry", name):
            log["reference_journals"].append(name)

    # 4. Return / Debit Notes (their own before_cancel hook cleans their links)
    for name in get_linked_returns(doc):
        if _cancel_submitted("Purchase Invoice", name):
            log["returns"].append(name)

    # Refresh in-memory payment fields — cancelling payments changed them in DB
    fresh = frappe.db.get_value(
        "Purchase Invoice", doc.name, ["outstanding_amount", "status"], as_dict=True
    )
    if fresh:
        doc.outstanding_amount = fresh.outstanding_amount

    _report_cleanup(doc, log)
    return log


def _report_cleanup(doc, log):
    lines = []
    if log["journals"]:
        lines.append(_("Amortization Journal Entries removed: {0}").format(", ".join(log["journals"])))
    if log["payments"]:
        lines.append(_("Payment Entries cancelled: {0}").format(", ".join(log["payments"])))
    if log["reference_journals"]:
        lines.append(_("Referencing Journal Entries cancelled: {0}").format(", ".join(log["reference_journals"])))
    if log["returns"]:
        lines.append(_("Debit Notes cancelled: {0}").format(", ".join(log["returns"])))
    if log["shared_payments"]:
        lines.append(_(
            "<b>Warning:</b> these Payment Entries also settled other invoices, which are now "
            "unallocated: {0}"
        ).format(", ".join(log["shared_payments"])))

    if lines:
        frappe.msgprint(
            "<br>".join(lines),
            title=_("Linked documents cancelled for {0}").format(doc.name),
            indicator="orange"
        )


@frappe.whitelist()
def force_cancel_purchase_invoice(purchase_invoice):
    """Button endpoint: cancel the invoice and every linked document in one transaction."""
    doc = frappe.get_doc("Purchase Invoice", purchase_invoice)

    if doc.docstatus == 2:
        frappe.throw(_("Purchase Invoice {0} is already cancelled").format(doc.name))
    if doc.docstatus == 0:
        frappe.throw(_("Purchase Invoice {0} is a draft; delete it instead").format(doc.name))

    frappe.has_permission("Purchase Invoice", "cancel", doc=doc, throw=True)

    # before_cancel hook performs the cleanup as part of doc.cancel()
    doc.cancel()
    return {"success": True, "name": doc.name}


@frappe.whitelist()
def get_cancel_preview(purchase_invoice):
    """Lists what will be cancelled — use in the UI confirm dialog."""
    doc = frappe.get_doc("Purchase Invoice", purchase_invoice)
    journals = get_linked_amortization_journals(doc)
    payments = get_linked_payment_entries(doc)
    return {
        "journals": journals,
        "payments": payments,
        "reference_journals": get_linked_reference_journals(doc, exclude=journals),
        "returns": get_linked_returns(doc),
        "outstanding_amount": doc.outstanding_amount,
        "status": doc.status
    }


def delete_related_journal_entries(doc):
    """Cancel + delete any amortization JE still linked via cheque_no. Idempotent."""
    for entry_name in get_linked_amortization_journals(doc):
        _cancel_submitted("Journal Entry", entry_name)
        frappe.delete_doc("Journal Entry", entry_name, force=1, ignore_permissions=True)


# ============================================================================
# HTML PRINT FORMATS
# ============================================================================

@frappe.whitelist()
def generate_amortization_html(purchase_invoice):
    doc = frappe.get_doc("Purchase Invoice", purchase_invoice)

    if not doc.custom_amortization_schedule:
        frappe.throw(_("No amortization schedule found"))

    rows_html = ""
    total_amount = 0
    for idx, row in enumerate(doc.custom_amortization_schedule, 1):
        total_amount += flt(row.amount)
        rows_html += """
        <tr>
            <td>{idx}</td>
            <td>{date}</td>
            <td>{desc}</td>
            <td class="amount">{amount}</td>
            <td class="amount">{balance}</td>
        </tr>""".format(
            idx=idx,
            date=format_date(row.date),
            desc=row.transaction_description or "",
            amount=frappe.utils.fmt_money(row.amount, currency=doc.currency),
            balance=frappe.utils.fmt_money(row.prepayment_balance, currency=doc.currency)
        )

    return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Amortization Schedule - {name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f4f6f9; padding: 20px; }}
        .container {{ max-width: 1100px; margin: 0 auto; background: white; border-radius: 12px;
                      overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.12); }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                   padding: 32px 40px; color: white; }}
        .header h1 {{ font-size: 28px; margin-bottom: 6px; }}
        .header p {{ opacity: 0.85; font-size: 14px; margin-top: 4px; }}
        .info-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;
                      padding: 24px 40px; background: #f8f9fa; }}
        .info-item {{ background: white; padding: 14px 18px; border-radius: 8px;
                      box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
        .info-label {{ color: #888; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .info-value {{ font-size: 16px; font-weight: 600; color: #2c3e50; margin-top: 4px; }}
        .schedule-section {{ padding: 24px 40px 40px; }}
        .schedule-section h2 {{ color: #2c3e50; margin-bottom: 16px; font-size: 18px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;
              padding: 12px 14px; text-align: left; font-size: 12px; text-transform: uppercase; }}
        td {{ padding: 10px 14px; border-bottom: 1px solid #f0f0f0; font-size: 14px; }}
        tr:hover td {{ background: #f8f9fa; }}
        tr:nth-child(even) td {{ background: #fafafa; }}
        .amount {{ text-align: right; font-weight: 500; }}
        .total-row td {{ background: #2c3e50 !important; color: white; font-weight: 600; }}
        .footer {{ background: #2c3e50; color: rgba(255,255,255,0.7);
                   padding: 16px 40px; font-size: 12px; text-align: center; }}
        @media print {{ body {{ background: white; }} .container {{ box-shadow: none; }} }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>Amortization Schedule</h1>
        <p>{supplier} &nbsp;|&nbsp; Invoice: {name}</p>
    </div>
    <div class="info-grid">
        <div class="info-item"><div class="info-label">Total Amount</div>
            <div class="info-value">{total}</div></div>
        <div class="info-item"><div class="info-label">Frequency</div>
            <div class="info-value">{frequency}</div></div>
        <div class="info-item"><div class="info-label">No. of Periods</div>
            <div class="info-value">{periods}</div></div>
        <div class="info-item"><div class="info-label">Amount Per Period</div>
            <div class="info-value">{per_period}</div></div>
        <div class="info-item"><div class="info-label">Start Date</div>
            <div class="info-value">{start_date}</div></div>
        <div class="info-item"><div class="info-label">End Date</div>
            <div class="info-value">{end_date}</div></div>
    </div>
    <div class="schedule-section">
        <h2>Payment Schedule</h2>
        <table>
            <thead>
                <tr>
                    <th>#</th><th>Date</th><th>Description</th>
                    <th class="amount">Amount</th>
                    <th class="amount">Remaining Balance</th>
                </tr>
            </thead>
            <tbody>
                {rows}
                <tr class="total-row">
                    <td colspan="3">TOTAL</td>
                    <td class="amount">{total_amount}</td>
                    <td class="amount">—</td>
                </tr>
            </tbody>
        </table>
    </div>
    <div class="footer">
        Generated {today} &nbsp;|&nbsp; {company}<br>
        Debit: {debit_acct} &nbsp;|&nbsp; Credit: {credit_acct}
    </div>
</div>
</body>
</html>""".format(
        name=doc.name,
        supplier=doc.supplier_name,
        total=frappe.utils.fmt_money(doc.base_total, currency=doc.currency),
        frequency=doc.custom_frequency,
        periods=doc.custom_no_of_periods,
        per_period=frappe.utils.fmt_money(doc.custom_charged_amount, currency=doc.currency),
        start_date=format_date(doc.custom_start_date),
        end_date=format_date(doc.custom_end_date) if doc.custom_end_date else "—",
        rows=rows_html,
        total_amount=frappe.utils.fmt_money(total_amount, currency=doc.currency),
        today=format_date(nowdate()),
        company=frappe.db.get_value("Company", doc.company, "company_name") or doc.company,
        debit_acct=doc.custom_expense_account,
        credit_acct=doc.custom_deferred_expense_account
    )


@frappe.whitelist()
def generate_cost_sharing_html(purchase_invoice):
    doc = frappe.get_doc("Purchase Invoice", purchase_invoice)

    if not doc.custom_cost_center_distribution:
        frappe.throw(_("No cost center distribution found"))

    cards_html = ""
    bars_html = ""
    for row in doc.custom_cost_center_distribution:
        amount = flt(doc.custom_charged_amount) * flt(row.distribution) / 100.0
        cards_html += """
        <div class="cc-card">
            <div class="cc-info">
                <div class="cc-name">{cc}</div>
                <div class="cc-title">{title}</div>
            </div>
            <div class="cc-amount">
                <div class="cc-pct">{pct}%</div>
                <div class="cc-money">{money}</div>
            </div>
        </div>""".format(
            cc=row.cost_center,
            title=row.title or "",
            pct=row.distribution,
            money=frappe.utils.fmt_money(amount, currency=doc.currency)
        )
        bars_html += """
        <div class="bar-item">
            <div class="bar-label">
                <span>{cc}</span><span>{money}</span>
            </div>
            <div class="bar-track">
                <div class="bar-fill" style="width:{pct}%"></div>
            </div>
        </div>""".format(
            cc=row.cost_center,
            money=frappe.utils.fmt_money(amount, currency=doc.currency),
            pct=row.distribution
        )

    return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Cost Sharing - {name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f4f6f9; padding: 20px; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; border-radius: 12px;
                      overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.12); }}
        .header {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                   padding: 32px 40px; color: white; }}
        .header h1 {{ font-size: 28px; margin-bottom: 6px; }}
        .header p {{ opacity: 0.85; font-size: 14px; margin-top: 4px; }}
        .summary {{ display: flex; gap: 20px; padding: 24px 40px; background: #f8f9fa; }}
        .summary-card {{ flex: 1; background: white; padding: 16px 20px; border-radius: 8px;
                         box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
        .summary-label {{ color: #888; font-size: 11px; text-transform: uppercase; }}
        .summary-value {{ font-size: 22px; font-weight: 700; color: #2c3e50; margin-top: 4px; }}
        .section {{ padding: 24px 40px; }}
        .section h2 {{ color: #2c3e50; margin-bottom: 16px; font-size: 18px; }}
        .section.alt {{ background: #f8f9fa; }}
        .cc-card {{ display: flex; justify-content: space-between; align-items: center;
                    background: white; border-left: 4px solid #f5576c; padding: 16px 20px;
                    margin-bottom: 12px; border-radius: 8px;
                    box-shadow: 0 1px 6px rgba(0,0,0,0.08); }}
        .cc-name {{ font-size: 16px; font-weight: 600; color: #2c3e50; }}
        .cc-title {{ color: #888; font-size: 13px; margin-top: 3px; }}
        .cc-pct {{ font-size: 22px; font-weight: 700; color: #f5576c; text-align: right; }}
        .cc-money {{ font-size: 14px; color: #555; text-align: right; margin-top: 2px; }}
        .bar-item {{ margin-bottom: 14px; }}
        .bar-label {{ display: flex; justify-content: space-between;
                      font-size: 13px; color: #555; margin-bottom: 6px; }}
        .bar-track {{ background: #f0f0f0; border-radius: 10px; height: 20px; overflow: hidden; }}
        .bar-fill {{ height: 100%;
                     background: linear-gradient(90deg, #f093fb 0%, #f5576c 100%);
                     border-radius: 10px; }}
        .footer {{ background: #2c3e50; color: rgba(255,255,255,0.7);
                   padding: 16px 40px; font-size: 12px; text-align: center; }}
        @media print {{ body {{ background: white; }} .container {{ box-shadow: none; }} }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>Cost Sharing Analysis</h1>
        <p>{supplier} &nbsp;|&nbsp; Invoice: {name}</p>
    </div>
    <div class="summary">
        <div class="summary-card">
            <div class="summary-label">Total Invoice Amount</div>
            <div class="summary-value">{total}</div>
        </div>
        <div class="summary-card">
            <div class="summary-label">Amount Per Period</div>
            <div class="summary-value">{per_period}</div>
        </div>
    </div>
    <div class="section">
        <h2>Cost Center Distribution</h2>
        {cards}
    </div>
    <div class="section alt">
        <h2>Distribution Breakdown</h2>
        {bars}
    </div>
    <div class="footer">
        Generated {today} &nbsp;|&nbsp; {company} &nbsp;|&nbsp; Total: {total_pct}%
    </div>
</div>
</body>
</html>""".format(
        name=doc.name,
        supplier=doc.supplier_name,
        total=frappe.utils.fmt_money(doc.base_total, currency=doc.currency),
        per_period=frappe.utils.fmt_money(doc.custom_charged_amount, currency=doc.currency),
        cards=cards_html,
        bars=bars_html,
        today=format_date(nowdate()),
        company=frappe.db.get_value("Company", doc.company, "company_name") or doc.company,
        total_pct=sum(flt(r.distribution) for r in doc.custom_cost_center_distribution)
    )