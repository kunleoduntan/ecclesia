# Copyright (c) 2026, Value Impacts Consulting
# Author: Kunle Oduntan
# ecclesia/ecclesia/doctype/bank_reconciliation_statement/bank_reconciliation_statement.py
#
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  BANK RECONCILIATION STATEMENT — DocType Controller                         ║
# ║  Ecclesia · Value Impacts Consulting                                         ║
# ╠══════════════════════════════════════════════════════════════════════════════╣
# ║  CRITICAL ACCOUNTING POLARITY — READ BEFORE EDITING                         ║
# ║                                                                              ║
# ║  BANK STATEMENT (bank's perspective — mirror of your books):                ║
# ║    Debit  = money LEAVING  your account → a PAYMENT made by you             ║
# ║    Credit = money ENTERING your account → a RECEIPT received by you         ║
# ║                                                                              ║
# ║  CASHBOOK / GL (your entity's perspective):                                 ║
# ║    Debit  = bank asset INCREASING       → a RECEIPT (money came in)         ║
# ║    Credit = bank asset DECREASING       → a PAYMENT (money went out)        ║
# ║                                                                              ║
# ║  They are MIRROR OPPOSITES. Matching must cross the polarity:               ║
# ║    Bank DR  ↔  Cashbook CR   (both represent a payment going out)           ║
# ║    Bank CR  ↔  Cashbook DR   (both represent a receipt coming in)           ║
# ║                                                                              ║
# ║  FOUR UNRECONCILED TABLES:                                                  ║
# ║    Unpresented Cheques/Transfers → Cashbook CR not yet in bank              ║
# ║      (payment recorded in books, not yet cleared by bank)                   ║
# ║    Uncredited Cheques/Transfers  → Cashbook DR not yet in bank              ║
# ║      (receipt recorded in books, not yet credited by bank)                  ║
# ║    Direct Withdrawals            → Bank DR not yet in cashbook              ║
# ║      (bank took money out; not yet posted in GL) → CREATE Payments          ║
# ║    Direct Lodgments              → Bank CR not yet in cashbook              ║
# ║      (bank received money in; not yet posted in GL) → CREATE Receipts       ║
# ║                                                                              ║
# ║  RECONCILIATION FORMULA:                                                    ║
# ║    Bank Closing Balance                                                      ║
# ║    + Uncredited Transfers  (cashbook DR not in bank — receipts in transit)  ║
# ║    − Unpresented Transfers (cashbook CR not in bank — payments outstanding) ║
# ║    + Direct Lodgments      (bank CR not in cashbook — add to GL)            ║
# ║    − Direct Withdrawals    (bank DR not in cashbook — deduct from GL)       ║
# ║    = Adjusted Bank Balance                                                   ║
# ║    Adjusted Bank Balance − Cashbook Closing Balance = Variance → 0          ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate, add_days, today, fmt_money, cstr
from datetime import datetime, date, timedelta
import json
import re

# ─── Nigerian Bank Abbreviation Dictionary ────────────────────────────────────
NIGERIAN_ABBREV = {
    'GTB': 'GUARANTY TRUST BANK', 'GT BANK': 'GUARANTY TRUST BANK',
    'FBN': 'FIRST BANK NIGERIA', 'FIRSTBANK': 'FIRST BANK NIGERIA',
    'UBA': 'UNITED BANK AFRICA', 'ZENITH': 'ZENITH BANK',
    'ACCESS': 'ACCESS BANK', 'STERLING': 'STERLING BANK',
    'FIDELITY': 'FIDELITY BANK', 'UNION': 'UNION BANK',
    'WEMA': 'WEMA BANK', 'FCMB': 'FIRST CITY MONUMENT BANK',
    'POLARIS': 'POLARIS BANK', 'KEYSTONE': 'KEYSTONE BANK',
    'HERITAGE': 'HERITAGE BANK', 'JAIZ': 'JAIZ BANK',
    'FLUTTERWAVE': 'FLUTTERWAVE COLLECTIONS', 'FW': 'FLUTTERWAVE',
    'PAYSTACK': 'PAYSTACK PAYMENTS', 'PS': 'PAYSTACK',
    'INTERSWITCH': 'INTERSWITCH PAYMENT',
    'NIP': 'NIP TRANSFER', 'TRF': 'TRANSFER',
    'INWARD TRF': 'INWARD TRANSFER', 'OUTWARD TRF': 'OUTWARD TRANSFER',
    'CHG': 'CHARGE', 'COMM': 'COMMISSION',
    'VAT': 'VALUE ADDED TAX', 'WHT': 'WITHHOLDING TAX',
    'PENCOM': 'PENSION COMMISSION', 'FIRS': 'FEDERAL INLAND REVENUE',
    'AFRIC': 'AFRICA', 'COMMS': 'COMMUNICATIONS',
}

STOP_WORDS = {
    'LTD', 'PLC', 'LIMITED', 'NIG', 'NIGERIA', 'NIGERIAN', 'AND', 'THE',
    'OF', 'CO', 'COMPANY', 'COMM', 'COMMS', 'COMMUNICATIONS', 'PETROLEUM',
    'DEVELOPMENT', 'ASSOCIATES', 'ENTERPRISE', 'GROUP', 'INTERNATIONAL',
    'GLOBAL', 'SERVICES', 'SOLUTIONS', 'RESOURCES', 'HOLDINGS',
}

# ─── Polarity constants — never use magic strings elsewhere ──────────────────
# Bank statement side
BANK_DR = 'BANK_DR'   # bank debit  = payment leaving your account
BANK_CR = 'BANK_CR'   # bank credit = receipt entering your account
# Cashbook / GL side
CASH_DR = 'CASH_DR'   # GL debit  = receipt (bank asset increases)
CASH_CR = 'CASH_CR'   # GL credit = payment (bank asset decreases)

# Cross-match map: which cashbook polarity matches which bank polarity
# Bank DR (payment out)  ↔  Cashbook CR (payment out)
# Bank CR (receipt in)   ↔  Cashbook DR (receipt in)
BANK_TO_CASH_POLARITY = {
    BANK_DR: CASH_CR,
    BANK_CR: CASH_DR,
}


class BankReconciliationStatement(Document):
    """Bank Reconciliation Statement DocType Controller."""

    # ─── Lifecycle ───────────────────────────────────────────────────────────

    def validate(self):
        self._validate_dates()
        self._validate_required_fields()
        self._calculate_totals()
        self._calculate_adjusted_bank_balance()
        self._set_status()

    def before_submit(self):
        if self.status != 'Reconciled':
            frappe.throw(_(
                "Cannot submit: statement is not reconciled. "
                "Variance is {0}. Capture all reconciling items first."
            ).format(fmt_money(flt(self.variance), currency=self.account_currency or 'NGN')))

    def on_cancel(self):
        self.status = 'Draft'

    # ─── Validation ──────────────────────────────────────────────────────────

    def _validate_dates(self):
        if self.from_date and self.to_date:
            if getdate(self.from_date) > getdate(self.to_date):
                frappe.throw(_("From Date cannot be later than To Date."))

    def _validate_required_fields(self):
        for field in ('company', 'bank_account', 'from_date', 'to_date'):
            if not self.get(field):
                frappe.throw(_("Field '{0}' is required.").format(
                    frappe.get_meta(self.doctype).get_field(field).label
                ))

    # ─── Calculations ─────────────────────────────────────────────────────────

    def _calculate_totals(self):
        """
        Total the four reconciling tables.

        Unpresented Cheques: cashbook CR (payments recorded, not yet cleared)
          → use credit_amount from cashbook_entries
        Uncredited Cheques: cashbook DR (receipts recorded, not yet credited)
          → use debit_amount from cashbook_entries
        Direct Withdrawals: bank DR (bank took money, not in cashbook)
          → use debit_amount from bank_statement_entries
        Direct Lodgments: bank CR (bank received money, not in cashbook)
          → use credit_amount from bank_statement_entries
        """
        self.total_bank_debit      = sum(flt(r.debit_amount)  for r in (self.bank_statement_entries or []))
        self.total_bank_credit     = sum(flt(r.credit_amount) for r in (self.bank_statement_entries or []))
        self.total_cashbook_debit  = sum(flt(r.debit_amount)  for r in (self.cashbook_entries or []))
        self.total_cashbook_credit = sum(flt(r.credit_amount) for r in (self.cashbook_entries or []))

        # Unpresented = cashbook CR unmatched (payments pending clearance)
        self.total_unpresented = sum(flt(r.credit_amount) for r in (self.unpresented_cheques or []))
        # Uncredited = cashbook DR unmatched (receipts pending bank credit)
        self.total_uncredited  = sum(flt(r.debit_amount)  for r in (self.uncredited_cheques or []))
        # Direct Withdrawals = bank DR unmatched (bank debited, not in GL yet)
        self.total_direct_wd   = sum(flt(r.debit_amount)  for r in (self.direct_withdrawals or []))
        # Direct Lodgments = bank CR unmatched (bank credited, not in GL yet)
        self.total_direct_lgmt = sum(flt(r.credit_amount) for r in (self.direct_lodgments or []))

    def _calculate_adjusted_bank_balance(self):
        """
        Standard bank reconciliation formula:

        Bank Statement Closing Balance
        + Uncredited Transfers  (cashbook DR not in bank — receipts in transit)
        − Unpresented Transfers (cashbook CR not in bank — payments outstanding)
        + Direct Lodgments      (bank CR not in cashbook — not yet posted to GL)
        − Direct Withdrawals    (bank DR not in cashbook — not yet posted to GL)
        = Adjusted Bank Balance

        Adjusted Bank Balance − Cashbook Closing Balance = Variance (→ 0)
        """
        bank_bal = flt(self.bank_statement_closing_balance)
        adj = (
            bank_bal
            + flt(self.total_uncredited)    # cashbook DR not in bank → add (outstanding receipts)
            - flt(self.total_unpresented)   # cashbook CR not in bank → deduct (outstanding payments)
            + flt(self.total_direct_lgmt)   # bank CR not in cashbook → add (unposted receipts)
            - flt(self.total_direct_wd)     # bank DR not in cashbook → deduct (unposted payments)
        )
        self.adjusted_bank_balance = adj
        self.variance = adj - flt(self.cashbook_closing_balance)

    def _set_status(self):
        if not self.from_date or not self.to_date:
            self.status = 'Draft'
        elif abs(flt(self.variance)) < 0.01:
            self.status = 'Reconciled'
            self.is_reconciled = 1
        else:
            self.status = 'In Progress'
            self.is_reconciled = 0


# ═══════════════════════════════════════════════════════════════════════════════
#  WHITELISTED API METHODS
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def fetch_gl_entries(docname):
    """
    Pull GL entries for the bank GL account for the statement period.
    Populates cashbook_entries.

    GL Entry polarity (your books):
        debit  → bank asset increases → RECEIPT coming in
        credit → bank asset decreases → PAYMENT going out

    Duplicate prevention: voucher_no + debit + credit + date composite key.
    Auto-computes cashbook closing balance from cumulative GL sum.
    """
    doc = frappe.get_doc('Bank Reconciliation Statement', docname)
    _assert_period(doc)

    bank_gl = _get_bank_gl(doc)
    company = doc.company
    from_dt = getdate(doc.from_date)
    to_dt   = getdate(doc.to_date)

    rows = frappe.db.sql("""
        SELECT
            gle.posting_date,
            COALESCE(NULLIF(gle.party, ''), gle.against, '') AS party,
            gle.voucher_no,
            gle.voucher_type,
            gle.debit   AS debit_amount,
            gle.credit  AS credit_amount,
            gle.account_currency,
            gle.remarks
        FROM `tabGL Entry` gle
        WHERE gle.posting_date BETWEEN %s AND %s
          AND gle.account      = %s
          AND gle.company      = %s
          AND gle.is_cancelled = 0
        ORDER BY gle.posting_date, gle.voucher_no
    """, (from_dt, to_dt, bank_gl, company), as_dict=True)

    if not rows:
        frappe.msgprint(
            _("No GL entries found for {0} to {1}.").format(doc.from_date, doc.to_date),
            indicator='orange'
        )
        return {'count': 0}

    existing = {_entry_key(r) for r in (doc.cashbook_entries or [])}
    appended = 0

    for r in rows:
        key = _entry_key(r)
        if key in existing:
            continue
        cheque_no = _cheque_from_voucher(r.voucher_type, r.voucher_no)
        doc.append('cashbook_entries', {
            'posting_date':     r.posting_date,
            'party':            (r.party or '')[:140],
            'voucher_no':       r.voucher_no or '',
            'debit_amount':     flt(r.debit_amount),    # GL DR = receipt
            'credit_amount':    flt(r.credit_amount),   # GL CR = payment
            'account_currency': r.account_currency or 'NGN',
            'cheque_no':        cheque_no or '',
            'remarks':          r.remarks or '',
            'rec':              0,
        })
        existing.add(key)
        appended += 1

    # Auto-compute cashbook closing balance: SUM(debit - credit) up to period end
    cb = frappe.db.sql("""
        SELECT SUM(debit - credit) AS bal
        FROM `tabGL Entry`
        WHERE account      = %s
          AND posting_date <= %s
          AND company      = %s
          AND is_cancelled = 0
    """, (bank_gl, to_dt, company), as_dict=True)

    if cb and cb[0].bal is not None:
        doc.cashbook_closing_balance = flt(cb[0].bal)

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        'count':   appended,
        'balance': doc.cashbook_closing_balance,
        'status':  'success',
    }


@frappe.whitelist()
def run_ai_matching(docname, date_tolerance=3, name_threshold=70,
                    amount_tolerance=0, hi_conf_cutoff=85, auto_accept_high=1):
    """
    AI Fuzzy Matching Engine with correct cross-polarity matching.

    MATCHING RULE (critical):
        Bank DR (payment out)  must match  Cashbook CR (payment out)
        Bank CR (receipt in)   must match  Cashbook DR (receipt in)

    Algorithms:
        • Levenshtein edit distance on normalised party names
        • Jaccard token overlap
        • Partial name containment
        • Nigerian bank abbreviation expansion
        • Stop-word removal (LTD, PLC, NIG, AND…)
        • Date ± configurable day tolerance
        • Amount exact + optional % tolerance
        • Composite score: amount 50% + date 25% + name 25%

    Returns match pairs with full metadata for frontend rendering.
    Cashbook-only rows are tagged with their correct unreconciled category.
    """
    doc = frappe.get_doc('Bank Reconciliation Statement', docname)

    date_tol    = int(date_tolerance)
    name_thr    = flt(name_threshold)  / 100.0
    amt_tol     = flt(amount_tolerance) / 100.0
    hi_conf     = flt(hi_conf_cutoff)  / 100.0
    auto_accept = int(auto_accept_high)

    bank_rows = list(doc.bank_statement_entries or [])
    cash_rows = list(doc.cashbook_entries or [])

    if not bank_rows or not cash_rows:
        frappe.throw(_("Both bank statement entries and cashbook entries are required."))

    used_cash = set()   # indices of cashbook rows already matched
    pairs     = []

    for b in bank_rows:
        # ── Determine bank polarity ──────────────────────────────────────────
        # Bank DR = payment leaving account; Bank CR = receipt entering account
        if flt(b.debit_amount) > 0:
            b_polarity = BANK_DR
            b_amt      = flt(b.debit_amount)
        else:
            b_polarity = BANK_CR
            b_amt      = flt(b.credit_amount)

        # The cashbook polarity we must match against (cross-polarity rule)
        required_cash_polarity = BANK_TO_CASH_POLARITY[b_polarity]

        best_score = 0.0
        best_cash  = None

        for ci, c in enumerate(cash_rows):
            if ci in used_cash:
                continue

            # ── Determine cashbook polarity ──────────────────────────────────
            # Cashbook DR = receipt (asset up); Cashbook CR = payment (asset down)
            if flt(c.debit_amount) > 0:
                c_polarity = CASH_DR
                c_amt      = flt(c.debit_amount)
            else:
                c_polarity = CASH_CR
                c_amt      = flt(c.credit_amount)

            # CROSS-POLARITY CHECK: must match opposite sides
            if c_polarity != required_cash_polarity:
                continue

            # ── Amount score (50%) ────────────────────────────────────────────
            if b_amt == 0 and c_amt == 0:
                continue
            amt_diff = abs(b_amt - c_amt) / max(b_amt, c_amt, 0.01)
            if amt_diff == 0:
                amt_score = 1.0
            elif amt_tol > 0 and amt_diff <= amt_tol:
                amt_score = 0.92
            elif amt_diff <= 0.001:      # rounding / penny difference
                amt_score = 0.88
            else:
                continue                 # amounts too different — skip

            # ── Date score (25%) ──────────────────────────────────────────────
            dd = _date_diff(b.posting_date, c.posting_date)
            if dd > date_tol:
                continue
            date_score = 1.0 if dd == 0 else 1.0 - (dd / (date_tol + 1)) * 0.20

            # ── Name score (25%) ──────────────────────────────────────────────
            b_name = cstr(b.party or b.remarks or '')
            c_name = cstr(c.party or c.remarks or '')
            ns = _name_similarity(b_name, c_name)

            total = amt_score * 0.50 + date_score * 0.25 + ns * 0.25

            if total > best_score and ns >= name_thr * 0.40:
                best_score = total
                best_cash  = (ci, c)

        # ── Classify confidence ───────────────────────────────────────────────
        conf_pct = round(best_score * 100, 1)
        if best_score >= hi_conf:
            conf = 'high'
        elif best_score >= 0.55:
            conf = 'medium'
        else:
            conf = 'low'

        accepted = bool(auto_accept and conf == 'high' and best_cash is not None)
        if best_cash:
            used_cash.add(best_cash[0])

        # ── What category does this bank row go to if unmatched? ──────────────
        # Bank DR unmatched → Direct Withdrawal (bank took money, not in GL)
        # Bank CR unmatched → Direct Lodgment   (bank received money, not in GL)
        unmatched_category = 'direct_withdrawal' if b_polarity == BANK_DR else 'direct_lodgment'

        # ── Cash amounts for display ──────────────────────────────────────────
        if best_cash:
            bc = best_cash[1]
            cash_display_amt = flt(bc.debit_amount) if flt(bc.debit_amount) > 0 else flt(bc.credit_amount)
        else:
            cash_display_amt = 0

        pairs.append({
            'bank_idx':           b.name,
            'cash_idx':           best_cash[1].name if best_cash else None,
            'score':              conf_pct,
            'conf':               conf,
            'accepted':           accepted,
            # Bank row details
            'bank_date':          cstr(b.posting_date),
            'bank_name':          cstr(b.party or b.remarks or ''),
            'bank_amt':           b_amt,
            'bank_polarity':      b_polarity,          # BANK_DR or BANK_CR
            # Cashbook row details
            'cash_date':          cstr(best_cash[1].posting_date) if best_cash else '',
            'cash_name':          cstr(best_cash[1].party or best_cash[1].remarks or '') if best_cash else '',
            'cash_amt':           cash_display_amt,
            'cash_polarity':      required_cash_polarity,   # what we looked for
            'cash_ref':           cstr(best_cash[1].voucher_no) if best_cash else '',
            # Routing
            'unmatched_category': unmatched_category,
        })

    # ── Cashbook-only rows: rows that found no bank match ────────────────────
    # Cashbook CR unmatched → Unpresented Cheque/Transfer
    #   (payment recorded in GL, not yet cleared by bank)
    # Cashbook DR unmatched → Uncredited Cheque/Transfer
    #   (receipt recorded in GL, not yet credited by bank)
    matched_cash_names = {p['cash_idx'] for p in pairs if p['cash_idx']}
    for c in cash_rows:
        if c.name in matched_cash_names:
            continue
        if flt(c.debit_amount) > 0:
            c_polarity = CASH_DR
            c_amt      = flt(c.debit_amount)
            # Cashbook DR unmatched = receipt not yet in bank → Uncredited
            unmatched_category = 'uncredited_cheque'
        else:
            c_polarity = CASH_CR
            c_amt      = flt(c.credit_amount)
            # Cashbook CR unmatched = payment not yet in bank → Unpresented
            unmatched_category = 'unpresented_cheque'

        pairs.append({
            'bank_idx':           None,
            'cash_idx':           c.name,
            'score':              0,
            'conf':               'unmatched',
            'accepted':           False,
            'bank_date':          '', 'bank_name': '', 'bank_amt': 0, 'bank_polarity': '',
            'cash_date':          cstr(c.posting_date),
            'cash_name':          cstr(c.party or c.remarks or ''),
            'cash_amt':           c_amt,
            'cash_polarity':      c_polarity,
            'cash_ref':           cstr(c.voucher_no),
            'unmatched_category': unmatched_category,
        })

    # ── Build statistics ──────────────────────────────────────────────────────
    matched  = [p for p in pairs if p['bank_idx'] and p['cash_idx']]
    unbank   = [p for p in pairs if p['bank_idx'] and not p['cash_idx']]
    uncash   = [p for p in pairs if not p['bank_idx'] and p['cash_idx']]

    return {
        'pairs':              pairs,
        'total_bank':         len(bank_rows),
        'total_cash':         len(cash_rows),
        'matched':            len(matched),
        'high_conf':          len([p for p in matched if p['conf'] == 'high']),
        'medium_conf':        len([p for p in matched if p['conf'] == 'medium']),
        'low_conf':           len([p for p in matched if p['conf'] == 'low']),
        'unmatched_bank':     len(unbank),
        'cashbook_only':      len(uncash),
        'auto_accepted':      len([p for p in pairs if p['accepted']]),
        'direct_withdrawals': len([p for p in unbank if p['unmatched_category'] == 'direct_withdrawal']),
        'direct_lodgments':   len([p for p in unbank if p['unmatched_category'] == 'direct_lodgment']),
        'unpresented':        len([p for p in uncash if p['unmatched_category'] == 'unpresented_cheque']),
        'uncredited':         len([p for p in uncash if p['unmatched_category'] == 'uncredited_cheque']),
        'match_rate':         round(len(matched) / max(len(bank_rows), 1) * 100, 1),
    }


@frappe.whitelist()
def apply_matches(docname, pairs_json):
    """
    Receive accepted match pairs from the frontend.

    Actions performed:
    1. Mark rec=1 on matched rows in both bank_statement_entries and cashbook_entries.
    2. Rebuild the four unreconciled tables:

       UNPRESENTED CHEQUES  ← Cashbook CR rows with no bank match
         (payments posted to GL, not yet cleared by bank)

       UNCREDITED CHEQUES   ← Cashbook DR rows with no bank match
         (receipts posted to GL, not yet credited by bank)

       DIRECT WITHDRAWALS   ← Bank DR rows with no cashbook match
         (bank debited your account; not yet posted to GL)
         → CREATE Payments doctype transaction for each row

       DIRECT LODGMENTS     ← Bank CR rows with no cashbook match
         (bank credited your account; not yet posted to GL)
         → CREATE Receipts doctype transaction for each row

    3. Recalculate adjusted balance and variance.
    4. Save the document.
    """
    if isinstance(pairs_json, str):
        pairs = json.loads(pairs_json)
    else:
        pairs = list(pairs_json)

    doc = frappe.get_doc('Bank Reconciliation Statement', docname)

    bank_map = {r.name: r for r in (doc.bank_statement_entries or [])}
    cash_map = {r.name: r for r in (doc.cashbook_entries or [])}

    # Reset rec flags on all rows
    for r in bank_map.values():
        r.rec = 0
    for r in cash_map.values():
        r.rec = 0

    # Mark accepted matched pairs as reconciled
    for p in pairs:
        if p.get('accepted') and p.get('bank_idx') and p.get('cash_idx'):
            if p['bank_idx'] in bank_map:
                bank_map[p['bank_idx']].rec = 1
            if p['cash_idx'] in cash_map:
                cash_map[p['cash_idx']].rec = 1

    # Sets of matched row names
    matched_cash = {p['cash_idx'] for p in pairs if p.get('accepted') and p.get('cash_idx')}
    matched_bank = {p['bank_idx'] for p in pairs if p.get('accepted') and p.get('bank_idx')}

    # Clear the four reconciling tables — rebuild from scratch
    doc.unpresented_cheques = []
    doc.uncredited_cheques  = []
    doc.direct_withdrawals  = []
    doc.direct_lodgments    = []

    # ── UNPRESENTED CHEQUES: Cashbook CR not matched ──────────────────────────
    # Cashbook CR = payment recorded in GL, not yet cleared by bank
    for c in (doc.cashbook_entries or []):
        if c.name in matched_cash:
            continue
        if flt(c.credit_amount) > 0:
            doc.append('unpresented_cheques', _child_row(c))

    # ── UNCREDITED CHEQUES: Cashbook DR not matched ───────────────────────────
    # Cashbook DR = receipt recorded in GL, not yet credited by bank
    for c in (doc.cashbook_entries or []):
        if c.name in matched_cash:
            continue
        if flt(c.debit_amount) > 0:
            doc.append('uncredited_cheques', _child_row(c))

    # ── DIRECT WITHDRAWALS: Bank DR not matched ───────────────────────────────
    # Bank DR = bank debited your account; payment not yet posted to GL
    # → will need a Payments transaction created
    for b in (doc.bank_statement_entries or []):
        if b.name in matched_bank:
            continue
        if flt(b.debit_amount) > 0:
            doc.append('direct_withdrawals', _child_row(b))

    # ── DIRECT LODGMENTS: Bank CR not matched ────────────────────────────────
    # Bank CR = bank credited your account; receipt not yet posted to GL
    # → will need a Receipts transaction created
    for b in (doc.bank_statement_entries or []):
        if b.name in matched_bank:
            continue
        if flt(b.credit_amount) > 0:
            doc.append('direct_lodgments', _child_row(b))

    doc.auto_accepted_count    = len([p for p in pairs if p.get('accepted') and p.get('bank_idx') and p.get('cash_idx')])
    doc.manually_matched_count = len([p for p in pairs if p.get('manual') and p.get('accepted')])
    doc.ai_match_summary       = _build_summary(pairs, doc)

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {'status': 'success', 'doc_name': doc.name}


@frappe.whitelist()
def create_transactions_for_unmatched(docname):
    """
    Create accounting transactions for unposted bank items:

    DIRECT WITHDRAWALS (bank DR not in cashbook):
        Bank debited your account but no GL entry exists yet.
        → Create a Payments doctype record (money went out).
        The payment debits the expense/liability and credits the bank GL.

    DIRECT LODGMENTS (bank CR not in cashbook):
        Bank credited your account but no GL entry exists yet.
        → Create a Receipts doctype record (money came in).
        The receipt debits the bank GL and credits the income/receivable.

    Duplicate-safe: checks date + amount + reference_no before creating.
    If no reference_no, falls back to date + amount + party name.
    """
    doc = frappe.get_doc('Bank Reconciliation Statement', docname)

    created_pmts  = 0
    created_rcpts = 0
    skipped_pmts  = 0
    skipped_rcpts = 0
    errors        = []

    try:
        user_fullname = frappe.db.get_value('User', frappe.session.user, 'full_name') or frappe.session.user
    except Exception:
        user_fullname = frappe.session.user

    bank_gl  = _get_bank_gl(doc)
    currency = doc.account_currency or 'NGN'

    # ═══ DIRECT WITHDRAWALS → Payments ═══════════════════════════════════════
    # Bank DR = bank paid money out of your account
    # The company must post a Payment to record this in the GL
    for dw in (doc.direct_withdrawals or []):
        amt = flt(dw.debit_amount)   # bank DR amount = the payment amount
        if amt <= 0:
            continue

        ref      = cstr(dw.cheque_no or dw.voucher_no or '')
        existing = _check_payment_exists(dw.posting_date, amt, ref, dw.party, doc.company)
        if existing:
            skipped_pmts += 1
            continue

        try:
            pmt = frappe.new_doc('Payments')
            pmt.transaction_date     = dw.posting_date
            pmt.payee_name           = (dw.party or 'Bank Charge').title()
            pmt.account_to_debit     = bank_gl        # credit bank GL (asset reduces)
            pmt.trans_type           = 'Expense Payment'
            pmt.payment_currency     = currency
            pmt.transaction_purposes = (dw.remarks or 'Direct Withdrawal — Bank Reconciliation').title()
            pmt.mode_of_payment      = 'Wire Transfer'
            pmt.remittance_bank      = doc.bank_account
            pmt.remittance_bank_gl   = bank_gl
            pmt.amount_paid          = amt
            pmt.exchange_rate        = 1
            pmt.nature_of_expense    = 'Internal'
            pmt.create_accounting_entries = 1
            pmt.reference_no         = ref or f'BR-{doc.name}-DW-{dw.idx}'
            pmt.approval_doc         = cstr(dw.voucher_no or '')
            pmt.issued_by            = frappe.session.user
            pmt.date                 = today()
            pmt.cashflow_type        = 'Payment of Operation'
            pmt.auth_date            = today()
            pmt.app_date             = today()
            pmt.company              = doc.company
            try:
                pmt.cost_center = frappe.db.get_value('Company', doc.company, 'cost_center')
            except Exception:
                pass
            pmt.insert(ignore_permissions=True)
            created_pmts += 1
        except Exception as e:
            errors.append(f"Direct Withdrawal row {dw.idx} ({dw.party}): {e}")
            frappe.log_error(errors[-1], 'BRS Create Payment')

    # ═══ DIRECT LODGMENTS → Receipts ══════════════════════════════════════════
    # Bank CR = bank received money into your account
    # The company must post a Receipt to record this in the GL
    for dl in (doc.direct_lodgments or []):
        amt = flt(dl.credit_amount)  # bank CR amount = the receipt amount
        if amt <= 0:
            continue

        ref      = cstr(dl.cheque_no or dl.voucher_no or '')
        existing = _check_receipt_exists(dl.posting_date, amt, ref, dl.party, doc.company)
        if existing:
            skipped_rcpts += 1
            continue

        try:
            rct = frappe.new_doc('Receipts')
            rct.transaction_date     = dl.posting_date
            rct.customer_type        = 'Receive from Registered'
            rct.customer_id          = dl.party or ''
            rct.customer_name        = (dl.party or 'Direct Lodgment').title()
            rct.create_accounting_entries = 1
            rct.transaction_purposes = (dl.remarks or 'Direct Lodgment — Bank Reconciliation').title()
            rct.receipt_currency     = currency
            rct.amount_paid          = amt
            rct.mode_of_payment      = 'Wire Transfer'
            rct.reference_no         = ref or f'BR-{doc.name}-DL-{dl.idx}'
            rct.referenced_document_no = doc.name
            rct.remittance_bank      = doc.bank_account
            rct.remittance_bank_gl   = bank_gl
            rct.approval_doc         = cstr(dl.voucher_no or '')
            rct.issued_by            = frappe.session.user
            rct.name_of_issued_by    = user_fullname
            rct.date                 = today()
            rct.company              = doc.company
            try:
                rct.cost_center = frappe.db.get_value('Company', doc.company, 'cost_center')
            except Exception:
                pass
            rct.insert(ignore_permissions=True)
            created_rcpts += 1
        except Exception as e:
            errors.append(f"Direct Lodgment row {dl.idx} ({dl.party}): {e}")
            frappe.log_error(errors[-1], 'BRS Create Receipt')

    if created_pmts + created_rcpts > 0:
        frappe.db.commit()

    if errors:
        frappe.log_error('\n'.join(errors), f'BRS Create Transactions — {docname}')

    return {
        'created_payments': created_pmts,
        'created_receipts': created_rcpts,
        'skipped_payments': skipped_pmts,
        'skipped_receipts': skipped_rcpts,
        'errors':           len(errors),
        'total_created':    created_pmts + created_rcpts,
    }


@frappe.whitelist()
def get_smart_suggestions(docname):
    """Analyse the reconciliation state and return actionable suggestions."""
    doc  = frappe.get_doc('Bank Reconciliation Statement', docname)
    tips = []

    bank_rows = list(doc.bank_statement_entries or [])
    cash_rows = list(doc.cashbook_entries or [])
    total     = len(bank_rows)
    matched   = len([r for r in bank_rows if r.rec == 1])
    rate      = round(matched / max(total, 1) * 100, 1)

    if rate < 50:
        tips.append({'priority': 'critical', 'icon': 'fa-circle-exclamation',
                     'title': f'Low match rate: {rate}%',
                     'desc': 'Run the AI matching engine to auto-match high-confidence pairs.'})
    elif rate >= 90:
        tips.append({'priority': 'success', 'icon': 'fa-circle-check',
                     'title': f'Excellent progress: {rate}% matched',
                     'desc': 'Almost done! Review remaining unmatched items.'})

    variance = flt(doc.variance or 0)
    if abs(variance) > 0.01:
        tips.append({'priority': 'critical', 'icon': 'fa-scale-unbalanced',
                     'title': f'Variance: {fmt_money(abs(variance), currency=doc.account_currency or "NGN")}',
                     'desc': 'Capture all direct withdrawals, lodgments, and outstanding items.'})
    else:
        tips.append({'priority': 'success', 'icon': 'fa-check-double',
                     'title': 'Variance is NIL — fully reconciled!',
                     'desc': 'Submit the document to lock the reconciliation.'})

    large = [r for r in bank_rows if r.rec == 0 and (flt(r.debit_amount) + flt(r.credit_amount)) > 100_000]
    if large:
        tips.append({'priority': 'warning', 'icon': 'fa-money-bill-wave',
                     'title': f'{len(large)} large unmatched transaction(s) > ₦100,000',
                     'desc': 'Prioritise these — large unmatched items may indicate posting errors.'})

    cutoff = add_days(doc.to_date or nowdate(), -30)
    old = [r for r in bank_rows if r.rec == 0 and getdate(r.posting_date) < getdate(cutoff)]
    if old:
        tips.append({'priority': 'warning', 'icon': 'fa-clock-rotate-left',
                     'title': f'{len(old)} item(s) older than 30 days unmatched',
                     'desc': 'Old unmatched items may indicate stale entries or posting errors.'})

    seen = {}
    dups = []
    for r in bank_rows:
        k = f"{r.posting_date}|{flt(r.debit_amount)}|{flt(r.credit_amount)}"
        if k in seen:
            dups.append(r)
        seen[k] = r
    if dups:
        tips.append({'priority': 'warning', 'icon': 'fa-copy',
                     'title': f'{len(dups)} potential duplicate bank row(s)',
                     'desc': 'Same date and amount appears more than once in bank statement.'})

    if not cash_rows:
        tips.append({'priority': 'critical', 'icon': 'fa-book-open',
                     'title': 'No cashbook / GL entries loaded',
                     'desc': 'Use Fetch GL Entries or upload your cashbook to begin matching.'})

    dw_count = len(doc.direct_withdrawals or [])
    dl_count = len(doc.direct_lodgments or [])
    if dw_count + dl_count > 0:
        tips.append({'priority': 'warning', 'icon': 'fa-file-invoice',
                     'title': f'{dw_count} Direct Withdrawal(s) + {dl_count} Direct Lodgment(s) need GL posting',
                     'desc': 'Use "Create Payments & Receipts" to post these to the GL.'})

    return tips


@frappe.whitelist()
def recalculate(docname):
    """Force recalculate totals, adjusted balance, variance and save."""
    doc = frappe.get_doc('Bank Reconciliation Statement', docname)
    doc.validate()
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {
        'adjusted_bank_balance': doc.adjusted_bank_balance,
        'variance':              doc.variance,
        'status':                doc.status,
        'is_reconciled':         doc.is_reconciled,
        'total_unpresented':     doc.total_unpresented,
        'total_uncredited':      doc.total_uncredited,
        'total_direct_wd':       doc.total_direct_wd,
        'total_direct_lgmt':     doc.total_direct_lgmt,
    }


@frappe.whitelist()
def import_bank_statement_file(docname, file_url, date_col, party_col,
                                debit_col, credit_col, amt_col='',
                                amount_format='drcr', header_row=1,
                                clear_existing=0):
    """
    Import bank statement from uploaded Excel/CSV.

    Bank statement polarity in the file:
        debit_col  = money leaving your account (payment)
        credit_col = money entering your account (receipt)

    Supported amount formats:
        drcr       = separate Debit and Credit columns
        single     = one column: positive value = credit (receipt), negative = debit (payment)
        single_inv = one column: positive value = debit (payment), negative = credit (receipt)
        drcr_flag  = one amount column + one Dr/Cr flag column
    """
    try:
        file_doc  = frappe.get_doc('File', {'file_url': file_url})
        file_path = file_doc.get_full_path()
    except Exception:
        frappe.throw(_("File not found: {0}").format(file_url))

    doc = frappe.get_doc('Bank Reconciliation Statement', docname)

    if int(clear_existing):
        doc.bank_statement_entries = []

    existing = {_entry_key(r) for r in (doc.bank_statement_entries or [])}
    rows     = _read_file(file_path, int(header_row))

    imported = 0
    skipped  = 0
    errors   = []

    for i, row in enumerate(rows, 1):
        try:
            row_lc = {k.lower().strip(): v for k, v in row.items()}

            def get(col_name):
                return row_lc.get((col_name or '').lower().strip(), '') if col_name else ''

            raw_date     = get(date_col)
            raw_party    = cstr(get(party_col)).strip()
            posting_date = _parse_date(raw_date)
            if not posting_date:
                errors.append(f"Row {i}: cannot parse date '{raw_date}'")
                continue

            debit_amt  = 0.0
            credit_amt = 0.0
            fmt        = (amount_format or 'drcr').lower()

            if fmt == 'drcr':
                # Bank DR column = payment; Bank CR column = receipt
                debit_amt  = flt(get(debit_col)  or 0)
                credit_amt = flt(get(credit_col) or 0)

            elif fmt == 'single':
                # Positive = receipt (bank CR); Negative = payment (bank DR)
                raw = flt(get(amt_col) or 0)
                if raw >= 0:
                    credit_amt = raw      # positive = money in = bank CR
                else:
                    debit_amt = abs(raw)  # negative = money out = bank DR

            elif fmt == 'single_inv':
                # Positive = payment (bank DR); Negative = receipt (bank CR)
                raw = flt(get(amt_col) or 0)
                if raw >= 0:
                    debit_amt  = raw       # positive = money out = bank DR
                else:
                    credit_amt = abs(raw)  # negative = money in = bank CR

            elif fmt == 'drcr_flag':
                # amt_col = amount column; debit_col = flag column (DR/CR/D/C)
                raw  = abs(flt(get(amt_col) or 0))
                flag = cstr(get(debit_col) or '').upper().strip()
                if flag in ('CR', 'C', 'CREDIT'):
                    credit_amt = raw   # bank CR = receipt
                else:
                    debit_amt = raw    # bank DR = payment

            if debit_amt == 0 and credit_amt == 0:
                skipped += 1
                continue

            voucher_no = f"{posting_date}|{raw_party}|{debit_amt}|{credit_amt}"[:140]
            key        = (voucher_no, debit_amt, credit_amt, str(posting_date))

            if key in existing:
                skipped += 1
                continue

            doc.append('bank_statement_entries', {
                'posting_date':    posting_date,
                'party':           raw_party[:140],
                'voucher_no':      voucher_no,
                'debit_amount':    debit_amt,    # bank DR = payment leaving account
                'credit_amount':   credit_amt,   # bank CR = receipt entering account
                'account_currency': doc.account_currency or 'NGN',
                'rec':             0,
            })
            existing.add(key)
            imported += 1

        except Exception as e:
            errors.append(f"Row {i}: {e}")

    if imported:
        doc.save(ignore_permissions=True)
        frappe.db.commit()

    if errors:
        frappe.log_error('\n'.join(errors[:100]), f'BRS Import Errors — {docname}')

    return {
        'imported': imported,
        'skipped':  skipped,
        'errors':   len(errors),
        'status':   'success',
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  PRIVATE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _assert_period(doc):
    if not doc.from_date or not doc.to_date:
        frappe.throw(_("Set From Date and To Date before fetching entries."))


def _get_bank_gl(doc):
    gl = frappe.db.get_value('Bank Account', doc.bank_account, 'account')
    if not gl:
        frappe.throw(_("Bank Account '{0}' has no linked GL Account.").format(doc.bank_account))
    return gl


def _entry_key(row):
    return (
        cstr(getattr(row, 'voucher_no', '') or ''),
        flt(getattr(row, 'debit_amount',  0)),
        flt(getattr(row, 'credit_amount', 0)),
        cstr(getattr(row, 'posting_date', '') or ''),
    )


def _child_row(source):
    """Map any child table row to a reconciling table row dict."""
    return {
        'posting_date':    source.posting_date,
        'party':           cstr(source.party or '')[:140],
        'voucher_no':      cstr(source.voucher_no or ''),
        'debit_amount':    flt(source.debit_amount),
        'credit_amount':   flt(source.credit_amount),
        'amount':          flt(source.debit_amount or source.credit_amount),
        'account_currency': cstr(getattr(source, 'account_currency', '') or 'NGN'),
        'cheque_no':       cstr(getattr(source, 'cheque_no', '') or ''),
        'rec':             0,
        'remarks':         cstr(getattr(source, 'remarks', '') or ''),
    }


def _date_diff(a, b):
    try:
        return abs((getdate(a) - getdate(b)).days)
    except Exception:
        return 9999


def _parse_date(v):
    if not v:
        return None
    if isinstance(v, (date, datetime)):
        return getdate(v)
    s = str(v).strip()
    if re.match(r'^\d{4,5}$', s):
        try:
            return date(1899, 12, 30) + timedelta(days=int(s))
        except Exception:
            pass
    m = re.match(r'^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})$', s)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except Exception:
            pass
    m2 = re.match(r'^(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})', s)
    if m2:
        try:
            return date(int(m2.group(1)), int(m2.group(2)), int(m2.group(3)))
        except Exception:
            pass
    try:
        return getdate(s)
    except Exception:
        return None


def _normalise_text(s):
    s = str(s or '').upper()
    for k, v in NIGERIAN_ABBREV.items():
        s = re.sub(r'\b' + re.escape(k) + r'\b', v or '', s)
    tokens = re.sub(r'[^A-Z0-9 ]', ' ', s).split()
    tokens = [t for t in tokens if t and t not in STOP_WORDS]
    return ' '.join(tokens).strip()


def _levenshtein(a, b):
    m, n = len(a), len(b)
    if not m: return n
    if not n: return m
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        curr = [i] + [0] * n
        for j in range(1, n + 1):
            curr[j] = prev[j-1] if a[i-1] == b[j-1] else 1 + min(prev[j], curr[j-1], prev[j-1])
        prev = curr
    return prev[n]


def _name_similarity(a, b):
    na = _normalise_text(a)
    nb = _normalise_text(b)
    if not na or not nb:
        return 0.0
    max_len = max(len(na), len(nb))
    lev  = 1.0 - _levenshtein(na, nb) / max_len
    sa   = set(na.split())
    sb   = set(nb.split())
    jacc = len(sa & sb) / len(sa | sb) if sa | sb else 0.0
    part = 1.0 if (na in nb or nb in na) else 0.0
    return max(lev, jacc * 0.9, part)


def _cheque_from_voucher(voucher_type, voucher_no):
    if not voucher_type or not voucher_no:
        return None
    field_map = {
        'Payment Entry': 'reference_no',
        'Journal Entry': 'cheque_no',
        'Payments':      'reference_no',
        'Receipts':      'reference_no',
    }
    field = field_map.get(voucher_type)
    if field:
        try:
            return frappe.db.get_value(voucher_type, voucher_no, field)
        except Exception:
            return None
    return None


def _check_payment_exists(txn_date, amount, ref_no, payee, company):
    filters = {'transaction_date': txn_date, 'amount_paid': amount,
               'company': company, 'docstatus': ['!=', 2]}
    if ref_no:
        filters['reference_no'] = ref_no
    result = frappe.db.get_value('Payments', filters, 'name')
    if result:
        return result
    if not ref_no and payee:
        filters.pop('reference_no', None)
        filters['payee_name'] = payee
        return frappe.db.get_value('Payments', filters, 'name')
    return None


def _check_receipt_exists(txn_date, amount, ref_no, customer, company):
    filters = {'transaction_date': txn_date, 'amount_paid': amount,
               'company': company, 'docstatus': ['!=', 2]}
    if ref_no:
        filters['reference_no'] = ref_no
    result = frappe.db.get_value('Receipts', filters, 'name')
    if result:
        return result
    if not ref_no and customer:
        filters.pop('reference_no', None)
        filters['customer_name'] = customer
        return frappe.db.get_value('Receipts', filters, 'name')
    return None


def _build_summary(pairs, doc):
    matched = len([p for p in pairs if p.get('bank_idx') and p.get('cash_idx')])
    high    = len([p for p in pairs if p.get('conf') == 'high'   and p.get('accepted')])
    med     = len([p for p in pairs if p.get('conf') == 'medium' and p.get('accepted')])
    unbank  = len([p for p in pairs if p.get('bank_idx') and not p.get('cash_idx')])
    uncash  = len([p for p in pairs if not p.get('bank_idx') and p.get('cash_idx')])
    dw      = len([p for p in pairs if p.get('unmatched_category') == 'direct_withdrawal'])
    dl      = len([p for p in pairs if p.get('unmatched_category') == 'direct_lodgment'])
    unp     = len([p for p in pairs if p.get('unmatched_category') == 'unpresented_cheque'])
    unc     = len([p for p in pairs if p.get('unmatched_category') == 'uncredited_cheque'])
    return (
        f"Matched: {matched} pair(s) — High: {high}, Medium: {med}. "
        f"Direct Withdrawals: {dw} | Direct Lodgments: {dl}. "
        f"Unpresented: {unp} | Uncredited: {unc}. "
        f"Variance: {fmt_money(flt(doc.variance), currency=doc.account_currency or 'NGN')}."
    )


def _read_file(file_path, header_row=1):
    if file_path.endswith(('.xlsx', '.xls')):
        try:
            import openpyxl
            wb      = openpyxl.load_workbook(file_path, data_only=True)
            ws      = wb.active
            all_r   = list(ws.iter_rows(values_only=True))
            headers = [str(c) if c is not None else '' for c in all_r[header_row - 1]]
            return [
                {headers[j]: (str(cell) if cell is not None else '')
                 for j, cell in enumerate(row)}
                for row in all_r[header_row:]
            ]
        except ImportError:
            frappe.throw(_("openpyxl required. Run: bench pip install openpyxl"))
    else:
        import csv
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            return list(csv.DictReader(f))