# Copyright (c) 2026, Value Impacts Consulting
# Author: Kunle Oduntan
# ecclesia/ecclesia/page/bank_reconciliation_studio/bank_reconciliation_studio.py
#
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  BANK RECONCILIATION STUDIO — Page Controller                               ║
# ║  All whitelisted endpoints called by bank_reconciliation_studio.js           ║
# ╠══════════════════════════════════════════════════════════════════════════════╣
# ║  ACCOUNTING POLARITY (see doctype controller for full explanation):          ║
# ║    Bank DR = payment out   ↔   Cashbook CR = payment out                    ║
# ║    Bank CR = receipt in    ↔   Cashbook DR = receipt in                     ║
# ║    Direct Withdrawals (bank DR unmatched) → CREATE Payments                 ║
# ║    Direct Lodgments   (bank CR unmatched) → CREATE Receipts                 ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

import frappe
from frappe import _
from frappe.utils import flt, cstr

# Import all engine functions from the DocType controller — single source of truth
from ecclesia.ecclesia.doctype.bank_reconciliation_statement.bank_reconciliation_statement import (
    fetch_gl_entries              as _fetch_gl_entries,
    run_ai_matching               as _run_ai_matching,
    apply_matches                 as _apply_matches,
    create_transactions_for_unmatched as _create_txns,
    get_smart_suggestions         as _get_suggestions,
    recalculate                   as _recalculate,
    import_bank_statement_file    as _import_file,
)


# ─── Document CRUD ────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_doc_list(limit=100):
    """Return recent Bank Reconciliation Statement list for the dashboard."""
    return frappe.get_list(
        'Bank Reconciliation Statement',
        fields=[
            'name', 'bank_account', 'company', 'from_date', 'to_date',
            'status', 'is_reconciled', 'variance', 'account_currency',
            'auto_accepted_count', 'manually_matched_count', 'ai_match_summary',
            'modified',
        ],
        order_by='modified desc',
        limit_page_length=int(limit),
    )


@frappe.whitelist()
def get_doc(docname):
    """Return a full Bank Reconciliation Statement document as dict."""
    _check_perm(docname)
    return frappe.get_doc('Bank Reconciliation Statement', docname).as_dict()


@frappe.whitelist()
def create_doc(company, bank_account, from_date, to_date,
               bank_statement_opening_balance=0,
               bank_statement_closing_balance=0,
               cashbook_opening_balance=0,
               cashbook_closing_balance=0,
               account_currency='NGN',
               date_tolerance_days=3,
               name_similarity_threshold=70,
               amount_tolerance_pct=0):
    """Create a new Bank Reconciliation Statement document."""
    frappe.has_permission('Bank Reconciliation Statement', 'create', throw=True)
    doc = frappe.new_doc('Bank Reconciliation Statement')
    doc.company                        = company
    doc.bank_account                   = bank_account
    doc.from_date                      = from_date
    doc.to_date                        = to_date
    doc.bank_statement_opening_balance = flt(bank_statement_opening_balance)
    doc.bank_statement_closing_balance = flt(bank_statement_closing_balance)
    doc.cashbook_opening_balance       = flt(cashbook_opening_balance)
    doc.cashbook_closing_balance       = flt(cashbook_closing_balance)
    doc.account_currency               = account_currency or 'NGN'
    doc.date_tolerance_days            = int(date_tolerance_days)
    doc.name_similarity_threshold      = flt(name_similarity_threshold)
    doc.amount_tolerance_pct           = flt(amount_tolerance_pct)
    doc.status                         = 'Draft'
    doc.insert(ignore_permissions=False)
    frappe.db.commit()
    return doc.as_dict()


@frappe.whitelist()
def save_balances(docname,
                  bank_statement_closing_balance=None,
                  cashbook_closing_balance=None,
                  bank_statement_opening_balance=None,
                  cashbook_opening_balance=None):
    """Patch balance fields and trigger recalculation."""
    _check_perm(docname, 'write')
    doc = frappe.get_doc('Bank Reconciliation Statement', docname)
    if bank_statement_closing_balance is not None:
        doc.bank_statement_closing_balance = flt(bank_statement_closing_balance)
    if cashbook_closing_balance is not None:
        doc.cashbook_closing_balance       = flt(cashbook_closing_balance)
    if bank_statement_opening_balance is not None:
        doc.bank_statement_opening_balance = flt(bank_statement_opening_balance)
    if cashbook_opening_balance is not None:
        doc.cashbook_opening_balance       = flt(cashbook_opening_balance)
    doc.validate()
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {
        'adjusted_bank_balance': doc.adjusted_bank_balance,
        'variance':              doc.variance,
        'status':                doc.status,
        'is_reconciled':         doc.is_reconciled,
    }


@frappe.whitelist()
def save_config(docname, date_tolerance_days=3, name_similarity_threshold=70,
                amount_tolerance_pct=0):
    """Persist matching configuration."""
    _check_perm(docname, 'write')
    frappe.db.set_value('Bank Reconciliation Statement', docname, {
        'date_tolerance_days':      int(date_tolerance_days),
        'name_similarity_threshold': flt(name_similarity_threshold),
        'amount_tolerance_pct':     flt(amount_tolerance_pct),
    })
    frappe.db.commit()
    return {'status': 'saved'}


# ─── Engine wrappers (stable URL surface for JS) ──────────────────────────────

@frappe.whitelist()
def fetch_gl_entries(docname):
    return _fetch_gl_entries(docname)


@frappe.whitelist()
def run_ai_matching(docname, date_tolerance=3, name_threshold=70,
                    amount_tolerance=0, hi_conf_cutoff=85, auto_accept_high=1):
    return _run_ai_matching(
        docname,
        date_tolerance=date_tolerance,
        name_threshold=name_threshold,
        amount_tolerance=amount_tolerance,
        hi_conf_cutoff=hi_conf_cutoff,
        auto_accept_high=auto_accept_high,
    )


@frappe.whitelist()
def apply_matches(docname, pairs_json):
    return _apply_matches(docname, pairs_json)


@frappe.whitelist()
def create_transactions(docname):
    return _create_txns(docname)


@frappe.whitelist()
def get_smart_suggestions(docname):
    return _get_suggestions(docname)


@frappe.whitelist()
def recalculate(docname):
    return _recalculate(docname)


@frappe.whitelist()
def import_bank_statement_file(docname, file_url, date_col, party_col,
                                debit_col, credit_col, amt_col='',
                                amount_format='drcr', header_row=1,
                                clear_existing=0):
    return _import_file(
        docname, file_url, date_col, party_col,
        debit_col, credit_col, amt_col,
        amount_format, header_row, clear_existing,
    )


# ─── Page-level helpers ────────────────────────────────────────────────────────

@frappe.whitelist()
def get_bank_accounts(company=None):
    """Return bank accounts for a given company (for the New Recon dialog)."""
    filters = {}
    if company:
        filters['company'] = company
    return frappe.get_list(
        'Bank Account',
        filters=filters,
        fields=['name', 'bank', 'account', 'account_currency'],
        order_by='name',
        limit_page_length=100,
    )


@frappe.whitelist()
def get_companies():
    """Return all companies accessible to the current user."""
    return frappe.get_list(
        'Company',
        fields=['name', 'default_currency', 'cost_center'],
        order_by='name',
    )


@frappe.whitelist()
def preview_uploaded_file(file_url, header_row=1):
    """
    Return column headers and first 15 data rows from an uploaded Excel/CSV.
    Used by the column-mapping dialog in the Import view.
    """
    try:
        file_doc  = frappe.get_doc('File', {'file_url': file_url})
        file_path = file_doc.get_full_path()
    except Exception:
        frappe.throw(_("File not found: {0}").format(file_url))

    header_row_int = int(header_row)

    if file_path.endswith(('.xlsx', '.xls')):
        try:
            import openpyxl
            wb   = openpyxl.load_workbook(file_path, data_only=True)
            ws   = wb.active
            rows = list(ws.iter_rows(values_only=True))
            hdrs = [cstr(c) if c is not None else '' for c in rows[header_row_int - 1]]
            data = [
                [cstr(c) if c is not None else '' for c in row]
                for row in rows[header_row_int: header_row_int + 15]
            ]
            return {
                'columns':    hdrs,
                'preview':    data,
                'total_rows': ws.max_row - header_row_int,
            }
        except ImportError:
            frappe.throw(_("openpyxl not installed. Run: bench pip install openpyxl"))
    else:
        import csv
        with open(file_path, encoding='utf-8-sig') as f:
            reader = list(csv.reader(f))
        hdrs = reader[header_row_int - 1] if len(reader) >= header_row_int else []
        data = reader[header_row_int: header_row_int + 15]
        return {
            'columns':    hdrs,
            'preview':    data,
            'total_rows': max(0, len(reader) - header_row_int),
        }


# ─── Internal ─────────────────────────────────────────────────────────────────

def _check_perm(docname, ptype='read'):
    frappe.has_permission(
        'Bank Reconciliation Statement',
        ptype=ptype,
        doc=docname,
        throw=True,
    )