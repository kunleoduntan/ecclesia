# Copyright (c) 2026, Kunle Oduntan and contributors
"""
Voucher Router  —  ecclesia/api/voucher_router.py
=================================================
ONE place that decides what a bank / petty-cash row becomes.

Every document that posts rows (Bank Transaction Processor, Batch Bank
Transaction, Expense Batch) carries a "Posting Policy" Select:

    Payments & Receipts       ->  Payments / Receipts vouchers
    Journal & Payment Entry   ->  ERPNext Journal Entry / Payment Entry

Each controller converts a child row into a plain ``line`` dict (the contract
below) and calls ``create_entry(line, policy, ...)``.  Nothing else in the
controllers knows which documents exist on the other side.

LINE CONTRACT  (keys are the Bank Transaction Line names, so the existing
Journal/Payment-Entry builders in bank_transaction_processor.py can consume
the same dict unchanged)
-------------------------------------------------------------------------
trans_type        canonical or alias name, see _ALIASES
posting_date, amount, remark
party_type, party, party_name, payee_name   (party = Supplier / Customer)
counter_account   GL for Payment / Receipt / Transfer rows (expense, income,
                  or the other side of a transfer)
bank_account_gl   optional GL override for the bank leg
mode_of_payment, reference_no, exch_rate, amount_in_fc, transaction_currency
cost_center, department, project, branch, customer_id, nature_of_expense
issued_by, cashflow_type
amortise, frequency, no_of_periods, start_date, deferred_account
idx               row number, for error messages
"""

import frappe
from frappe import _
from frappe.utils import add_months, add_days, cstr, flt, today

POLICY_VOUCHERS = "Payments & Receipts"
POLICY_ENTRIES = "Journal & Payment Entry"
POLICY_OPTIONS = f"{POLICY_VOUCHERS}\n{POLICY_ENTRIES}"

# Names used by the Batch Bank Transaction / older code -> canonical names
_ALIASES = {
    "Customer Refunds": "Customer Refund",
    "Supplier Refunds": "Supplier Refund",
    "Expense Payment": "Payment",
    "Revenue Receipt": "Receipt",
}

# canonical trans type -> (voucher doctype, voucher trans_type, direction)
_VOUCHER_MAP = {
    "Supplier Payment": ("Payments", "Supplier Payment", "out"),
    "Payment":          ("Payments", "Expense Payment",  "out"),
    "Transfer Out":     ("Payments", "Transfer Out",     "out"),
    "Supplier Refund":  ("Payments", "Supplier Refunds", "in"),
    "Customer Receipt": ("Receipts", "Customer Receipt", "in"),
    "Receipt":          ("Receipts", "Revenue Receipt",  "in"),
    "Transfer In":      ("Receipts", "Transfer In",      "in"),
    "Customer Refund":  ("Receipts", "Customer Refund",  "out"),
}

# cash direction per canonical type (drives inflow / outflow columns)
INFLOW_TYPES = {"Customer Receipt", "Transfer In", "Supplier Refund", "Receipt"}
OUTFLOW_TYPES = {"Supplier Payment", "Transfer Out", "Customer Refund", "Payment"}

PARTY_TYPE_FOR = {
    "Supplier Payment": "Supplier", "Supplier Refund": "Supplier",
    "Customer Receipt": "Customer", "Customer Refund": "Customer",
    "Payment": "Account", "Receipt": "Account",
    "Transfer In": "Account", "Transfer Out": "Account",
}

# Payments allows Monthly/Quarterly/Yearly, Receipts Monthly/Quarterly
_AMORT_FREQ = {"Payments": {"Monthly", "Quarterly", "Yearly"},
               "Receipts": {"Monthly", "Quarterly"}}
_MONTHS = {"Monthly": 1, "Quarterly": 3, "Yearly": 12}

# Preferred cash-flow classification per trans type, first VALID option wins.
# Payments.cashflow_type is mandatory, so every Payments type needs a fallback.
# "Funds Transfer" is tried first for Transfer Out: add it to the Cash Flow Type
# options on Payments (recommended) and it is picked up automatically.
_DEFAULT_CASHFLOW = {
    "Supplier Payment": ["Supplier payments"],
    "Supplier Refund":  ["Supplier payments"],
    "Payment":          ["Operating costs"],
    "Transfer Out":     ["Funds Transfer", "Operating costs"],
    "Customer Receipt": ["Customer payments for goods/services"],
}


# ─────────────────────────────────────────────────────────────────────────────
# Policy helpers
# ─────────────────────────────────────────────────────────────────────────────

def resolve_policy(value, default=POLICY_VOUCHERS):
    """Blank (documents saved before the field existed) -> ``default``, so old
    records keep the behaviour they always had."""
    value = (value or "").strip() or default
    if value not in (POLICY_VOUCHERS, POLICY_ENTRIES):
        frappe.throw(_("Unknown Posting Policy '{0}'.").format(value))
    return value


def canonical(trans_type):
    t = (trans_type or "").strip()
    return _ALIASES.get(t, t)


def accepted_spellings(options):
    """Every alias / canonical spelling that maps onto one of ``options``."""
    canon = {canonical(o) for o in options}
    extra = {a for a, c in _ALIASES.items() if c in canon} | canon
    return sorted(extra - set(options))


def is_inflow(trans_type):
    return canonical(trans_type) in INFLOW_TYPES


def is_outflow(trans_type):
    return canonical(trans_type) in OUTFLOW_TYPES


def party_type_for(trans_type):
    return PARTY_TYPE_FOR.get(canonical(trans_type))


def voucher_doctype(trans_type):
    """'Payments' / 'Receipts' for a trans type (or None, e.g. 'Pending')."""
    m = _VOUCHER_MAP.get(canonical(trans_type))
    return m[0] if m else None


def validate_amortisation(line, policy):
    """Raise early (at validate time) when an amortised row cannot be honoured."""
    if not line.get("amortise"):
        return
    idx = line.get("idx")
    if not line.get("frequency"):
        frappe.throw(_("Row {0}: Frequency is required when Amortise is ticked.").format(idx))
    if not (line.get("no_of_periods") or 0) > 0:
        frappe.throw(_("Row {0}: No of Periods must be > 0 when Amortise is ticked.").format(idx))
    if not line.get("start_date"):
        frappe.throw(_("Row {0}: Start Date is required when Amortise is ticked.").format(idx))
    if policy == POLICY_VOUCHERS:
        dt = voucher_doctype(line.get("trans_type"))
        if dt and line["frequency"] not in _AMORT_FREQ[dt]:
            frappe.throw(_("Row {0}: {1} supports amortisation frequency {2} only.").format(
                idx, dt, ", ".join(sorted(_AMORT_FREQ[dt]))))
        if canonical(line.get("trans_type")) not in ("Payment", "Receipt"):
            frappe.throw(_("Row {0}: only Payment / Receipt rows can be amortised.").format(idx))


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def create_entry(line, policy, company, bank_account, source_doctype, source_name,
                 source_row=None, submit=False, default_mode="Wire Transfer"):
    """
    Create the accounting document for one row.
    Returns (document_name, document_doctype).
    Raises on any problem (callers decide whether that aborts the batch).
    """
    policy = resolve_policy(policy)
    line = dict(line)
    line["trans_type"] = canonical(line.get("trans_type"))
    tt = line["trans_type"]
    if tt not in _VOUCHER_MAP:
        frappe.throw(_("Row {0}: unknown Trans Type '{1}'.").format(line.get("idx"), tt))

    # fill the legacy account_to_* keys so the Journal builder can use the line
    cp = line.get("counter_account")
    if cp:
        if tt == "Payment":
            line.setdefault("account_to_debit", cp)
        elif tt == "Receipt":
            line.setdefault("account_to_credit", cp)
    line.setdefault("mode_of_payment", default_mode)

    if policy == POLICY_VOUCHERS:
        name, dt = _create_voucher(line, company, bank_account, source_doctype,
                                   source_name, source_row, default_mode)
    else:
        name, dt = _create_ledger_entry(line, company, bank_account, source_name)

    if submit:
        frappe.get_doc(dt, name).submit()
    return name, dt


def cancel_or_delete(doctype, name):
    """Cancel a submitted document, delete a draft one. Returns 'cancelled' /
    'deleted' / None."""
    if not (doctype and name and frappe.db.exists(doctype, name)):
        return None
    ds = frappe.db.get_value(doctype, name, "docstatus")
    if ds == 1:
        frappe.get_doc(doctype, name).cancel()
        return "cancelled"
    if ds == 0:
        frappe.delete_doc(doctype, name, ignore_permissions=True)
        return "deleted"
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Policy 1 — Payments / Receipts
# ─────────────────────────────────────────────────────────────────────────────

def _has(meta, fieldname):
    return bool(meta.get_field(fieldname)) if hasattr(meta, "get_field") else meta.has_field(fieldname)


def _apply(doc, meta, values):
    """Set only values that are not blank AND exist on the doctype, so one
    dict can feed both Payments and Receipts without AttributeErrors."""
    for k, v in values.items():
        if v is None or v == "":
            continue
        if _has(meta, k):
            doc.set(k, v)


def _select_or_none(meta, fieldname, value):
    """Return value only if it is a valid option of a Select field."""
    if not value:
        return None
    df = meta.get_field(fieldname)
    if not df:
        return None
    opts = [o.strip() for o in (df.options or "").split("\n")]
    return value if value in opts else None


def _bank_context(line, company, bank_account):
    """-> (Bank Account name, bank GL, bank currency, company currency)."""
    override = line.get("bank_account_gl")
    if override:
        bank_doc = frappe.db.get_value("Bank Account", {"account": override}, "name")
        if not bank_doc and frappe.db.exists("Bank Account", bank_account):
            bank_doc = bank_account
        bank_gl = override
    else:
        bank_doc = bank_account if frappe.db.exists("Bank Account", bank_account) else \
            frappe.db.get_value("Bank Account", {"account": bank_account}, "name")
        bank_gl = (frappe.db.get_value("Bank Account", bank_doc, "account")
                   if bank_doc else None) or bank_account
    if not bank_doc:
        frappe.throw(_(
            "Row {0}: Payments / Receipts need a Bank Account record. No Bank Account "
            "is linked to GL '{1}'. Create one (Bank Account -> Account = that GL), "
            "for example for the petty cash account."
        ).format(line.get("idx"), bank_gl or bank_account))
    local = frappe.db.get_value("Company", company, "default_currency")
    ccy = frappe.db.get_value("Account", bank_gl, "account_currency") or local
    return bank_doc, bank_gl, ccy, local


def _create_voucher(line, company, bank_account, source_doctype, source_name,
                    source_row, default_mode):
    tt = line["trans_type"]
    dt, vtype, _dir = _VOUCHER_MAP[tt]
    idx = line.get("idx")
    amount = flt(line.get("amount"))
    if amount <= 0:
        frappe.throw(_("Row {0}: Amount must be greater than zero.").format(idx))

    bank_doc, _bank_gl, ccy, local = _bank_context(line, company, bank_account)
    is_local = ccy == local
    rate = 1.0
    amount_fc = 0.0
    if not is_local:
        rate = flt(line.get("exch_rate"))
        if rate <= 0 or rate == 1:
            frappe.throw(_("Row {0}: Exchange Rate is required for a {1} bank account.").format(idx, ccy))
        amount_fc = flt(line.get("amount_in_fc")) or amount

    ref = line.get("reference_no") or (cstr(source_row)[-7:].upper() if source_row else source_name)
    party = line.get("party") or None
    counter = line.get("counter_account") or None
    payee = (line.get("payee_name") or line.get("party_name") or "").strip()
    purpose = (line.get("remark") or "").strip()

    doc = frappe.new_doc(dt)
    meta = frappe.get_meta(dt)

    common = {
        "company": company,
        "trans_type": vtype,
        "transaction_date": line.get("posting_date"),
        "mode_of_payment": line.get("mode_of_payment"),
        "remittance_bank": bank_doc,
        "reference_no": ref,
        "transaction_purposes": purpose,
        "cost_center": line.get("cost_center"),
        "branch": line.get("branch"),
        "department": line.get("department"),
        "project": line.get("project"),
        "create_accounting_entries": 1,
        "issued_by": line.get("issued_by") or frappe.session.user,
        "date": today(),
    }

    if dt == "Payments":
        vals = dict(common)
        vals.update({
            "payment_currency": ccy,
            "exchange_rate": rate,
            "amount_paid": amount if is_local else 0,
            "amount_paid_in_fc": 0 if is_local else amount_fc,
            "approval_doc": source_row,
            "nature_of_expense": line.get("nature_of_expense") or "Internal",
            "customer_id": line.get("customer_id"),
        })
        if tt in ("Supplier Payment", "Supplier Refund"):
            if not party:
                frappe.throw(_("Row {0}: Supplier is required for {1}.").format(idx, tt))
            vals["payee_id"] = party
            vals["supplier_name"] = line.get("party_name") or \
                frappe.db.get_value("Supplier", party, "supplier_name")
        else:  # Payment (Expense Payment) / Transfer Out
            if not counter:
                frappe.throw(_("Row {0}: an account to debit is required for {1}.").format(idx, tt))
            vals["account_to_debit"] = counter
            vals["payee_name"] = payee or counter
    else:  # Receipts
        vals = dict(common)
        vals.update({
            "receipt_currency": ccy,
            "exchange_rate": rate,
            "amount_received": amount if is_local else 0,
            "amount_received_in_fc": 0 if is_local else amount_fc,
            "referenced_document_no": source_name,
        })
        if tt in ("Customer Receipt", "Customer Refund"):
            if not party:
                frappe.throw(_("Row {0}: Customer is required for {1}.").format(idx, tt))
            vals["customer_id"] = party
        else:  # Revenue Receipt / Transfer In
            if not counter:
                frappe.throw(_("Row {0}: an account to credit is required for {1}.").format(idx, tt))
            vals["account_to_credit"] = counter
            vals["payer_name"] = payee or counter

    # Select fields only accept their listed options: use the caller's value if
    # valid, else a sensible default, else leave blank (never fail on this).
    vals["cashflow_type"] = next(
        (v for v in [line.get("cashflow_type")] + _DEFAULT_CASHFLOW.get(tt, [])
         if _select_or_none(meta, "cashflow_type", v)), None)

    _apply(doc, meta, vals)
    _apply_amortisation(doc, meta, dt, tt, line, amount)

    doc.insert(ignore_permissions=True)
    return doc.name, dt


def _apply_amortisation(doc, meta, dt, tt, line, amount):
    """Let the voucher's own schedule engine do the spreading."""
    if not line.get("amortise") or tt not in ("Payment", "Receipt"):
        return
    n = int(line.get("no_of_periods") or 0)
    freq = line.get("frequency")
    start = line.get("start_date")
    step = _MONTHS.get(freq)
    if not (n > 0 and step and start):
        frappe.throw(_("Row {0}: invalid amortisation settings.").format(line.get("idx")))
    end = add_days(add_months(start, step * n), -1)
    counter = line.get("counter_account")
    vals = {
        "amortize": 1,
        "frequency": freq,
        "start_date": start,
        "end_date": end,
        "charge_amount": round(amount / n, 2),
    }
    if dt == "Payments":
        vals.update({"expense_account": counter,
                     "deferred_expense_account": line.get("deferred_account")})
    else:
        vals.update({"defer_revenue": 1, "revenue_account": counter,
                     "deferred_revenue_account": line.get("deferred_account")})
    _apply(doc, meta, vals)


# ─────────────────────────────────────────────────────────────────────────────
# Policy 2 — Journal Entry / Payment Entry
# (re-uses the builders already proven in Bank Transaction Processor; only
#  Internal Transfers are built here, because the BTP builder reads the same
#  `bank_account_gl` key for BOTH legs of a transfer)
# ─────────────────────────────────────────────────────────────────────────────

def _create_ledger_entry(line, company, bank_account, source_name):
    from ecclesia.ecclesia.doctype.bank_transaction_processor import bank_transaction_processor as btp

    tt = line["trans_type"]
    if tt in ("Transfer Out", "Transfer In"):
        return _build_internal_transfer(line, company, bank_account), "Payment Entry"

    if tt in btp._PE_TYPES:
        return btp._build_payment_entry(line, company, bank_account, source_name), "Payment Entry"

    # Payment / Receipt -> Journal Entry
    if line.get("amortise"):
        frappe.throw(_(
            "Row {0}: amortisation under the 'Journal & Payment Entry' policy is only "
            "supported in Bank Transaction Processor. Use 'Payments & Receipts' or "
            "post this row from the Processor."
        ).format(line.get("idx")))
    return btp._build_journal_entry_single(line, company, bank_account, source_name), "Journal Entry"


def _build_internal_transfer(line, company, bank_account):
    tt = line["trans_type"]
    counter = line.get("counter_account")
    if not counter:
        frappe.throw(_("Row {0}: the other account of the transfer is required.").format(line.get("idx")))
    bank_gl = line.get("bank_account_gl") or frappe.db.get_value("Bank Account", bank_account, "account") \
        or bank_account
    ccy = frappe.db.get_value("Company", company, "default_currency")
    amount = flt(line.get("amount"))

    pe = frappe.new_doc("Payment Entry")
    pe.payment_type = "Internal Transfer"
    pe.company = company
    pe.posting_date = line.get("posting_date")
    pe.mode_of_payment = line.get("mode_of_payment")
    pe.reference_no = line.get("reference_no") or ""
    pe.reference_date = line.get("posting_date")
    pe.remarks = line.get("remark") or ""
    pe.paid_amount = amount
    pe.received_amount = amount
    pe.paid_from = bank_gl if tt == "Transfer Out" else counter
    pe.paid_to = counter if tt == "Transfer Out" else bank_gl
    pe.paid_from_account_currency = ccy
    pe.paid_to_account_currency = ccy
    if line.get("cost_center"):
        pe.cost_center = line["cost_center"]
    if line.get("project"):
        pe.project = line["project"]
    pe.insert(ignore_permissions=True)
    return pe.name
