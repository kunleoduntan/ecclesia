"""
Bank Transaction Processor — Controller  (v2)
==============================================
Module: Ecclesia

Trans Type → Entry mapping (non-accountant friendly):
──────────────────────────────────────────────────────
  Supplier Payment  → Payment Entry  (Pay,     party=Supplier)
  Customer Receipt  → Payment Entry  (Receive,  party=Customer)
  Transfer Out      → Payment Entry  (Internal Transfer, paid_from=bank)
  Transfer In       → Payment Entry  (Internal Transfer, paid_to=bank)
  Customer Refund   → Payment Entry  (Pay,     party=Customer)
  Supplier Refund   → Payment Entry  (Receive,  party=Supplier)
  Payment           → Journal Entry  (expense / cost — Credit bank, Debit expense account)
  Receipt           → Journal Entry  (income / revenue — Debit bank, Credit income account)
                      + optional amortisation over N periods
  Pending           → No entry created; row flagged only

Inflow / Outflow auto-set:
  Inflow types:  Customer Receipt, Transfer In, Supplier Refund, Receipt
  Outflow types: Supplier Payment, Transfer Out, Customer Refund, Payment
"""

import io, base64
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today, add_days, add_months

# ── Type routing ──────────────────────────────────────────────────────────────
_PE_TYPES = {
    "Supplier Payment", "Customer Receipt",
    "Transfer Out", "Transfer In",
    "Customer Refund", "Supplier Refund",
}
_JE_TYPES     = {"Payment", "Receipt"}
_INFLOW_TYPES = {"Customer Receipt", "Transfer In", "Supplier Refund", "Receipt"}
_OUTFLOW_TYPES= {"Supplier Payment", "Transfer Out", "Customer Refund", "Payment"}

# PE payment_type derivation
_TRANS_TO_PAYMENT_TYPE = {
    "Supplier Payment":  "Pay",
    "Customer Receipt":  "Receive",
    "Transfer Out":      "Internal Transfer",
    "Transfer In":       "Internal Transfer",
    "Customer Refund":   "Pay",
    "Supplier Refund":   "Receive",
}

# PE party_type derivation (None = no party needed, e.g. Internal Transfer)
_TRANS_TO_PARTY_TYPE = {
    "Supplier Payment":  "Supplier",
    "Customer Receipt":  "Customer",
    "Transfer Out":      None,
    "Transfer In":       None,
    "Customer Refund":   "Customer",
    "Supplier Refund":   "Supplier",
}

# Excel column map
_COLUMNS = [
    ("Date*",              "posting_date",         True,  "date"),
    ("Trans Type*",        "trans_type",            True,  "str"),
    ("Description*",       "remark",                True,  "str"),
    ("Amount*",            "amount",                True,  "float"),
    ("Party Type",         "party_type",            False, "str"),
    ("Party",              "party",                 False, "str"),
    ("Party Name",         "party_name",            False, "str"),
    ("Payee Name",         "payee_name",            False, "str"),
    ("Account to Debit",   "account_to_debit",      False, "str"),
    ("Account to Credit",  "account_to_credit",     False, "str"),
    ("Bank GL Override",   "bank_account_gl",       False, "str"),
    ("Mode of Payment",    "mode_of_payment",       False, "str"),
    ("Reference No",       "reference_no",          False, "str"),
    ("Exch Rate",          "exch_rate",             False, "float"),
    ("Amount in FC",       "amount_in_fc",          False, "float"),
    ("Trans Currency",     "transaction_currency",  False, "str"),
    ("Cost Center",        "cost_center",           False, "str"),
    ("Department",         "department",            False, "str"),
    ("Project",            "project",               False, "str"),
    ("Branch",             "branch",                False, "str"),
    ("Nature of Expense",  "nature_of_expense",     False, "str"),
    ("Customer ID",        "customer_id",           False, "str"),
    ("Amortise",           "amortise",              False, "int"),
    ("Frequency",          "frequency",             False, "str"),
    ("No of Periods",      "no_of_periods",         False, "int"),
    ("Start Date",         "start_date",            False, "date"),
    ("JE Narration",       "transaction_description",False,"str"),
]


# ─────────────────────────────────────────────────────────────────────────────
# DocType controller
# ─────────────────────────────────────────────────────────────────────────────

class BankTransactionProcessor(Document):

    def validate(self):
        self._set_inflow_outflow()
        self._validate_rows()
        self._calc_totals()

    def on_submit(self):
        self.db_set("status", "Submitted")
        self.db_set("submit_remarks",
            f"Submitted on {today()} by {frappe.session.user}.")

    def on_cancel(self):
        _cancel_linked_entries(self.name)
        self.db_set("status", "Cancelled")

    # ── private ──────────────────────────────────────────────────────────────

    def _set_inflow_outflow(self):
        """Auto-populate inflow / outflow columns from amount + trans_type."""
        for row in self.get("transactions", []):
            amt = flt(row.get("amount"))
            tt  = row.get("trans_type") or ""
            if tt in _INFLOW_TYPES:
                row.inflow  = amt
                row.outflow = 0
            elif tt in _OUTFLOW_TYPES:
                row.inflow  = 0
                row.outflow = amt
            else:
                row.inflow  = 0
                row.outflow = 0

    def _validate_rows(self):
        for idx, row in enumerate(self.get("transactions", []), start=1):
            tt = row.get("trans_type") or ""
            if not tt:
                frappe.throw(_(f"Row {idx}: Trans Type is required."))
            if not row.get("remark"):
                frappe.throw(_(f"Row {idx}: Transaction Description is required."))
            if flt(row.get("amount")) <= 0:
                frappe.throw(_(f"Row {idx}: Amount must be greater than zero."))
            if tt == "Pending":
                continue   # No further validation for Pending rows

            if tt in _PE_TYPES:
                if not row.get("party") and tt not in ("Transfer Out", "Transfer In"):
                    frappe.throw(_(f"Row {idx}: Party is required for {tt}."))
                # party_type must also be set for non-transfer PE types
                if not row.get("party_type") and tt not in ("Transfer Out", "Transfer In"):
                    frappe.throw(_(f"Row {idx}: Party Type is required for {tt}."))

            # JE types (Payment / Receipt) do NOT need party — they use GL accounts directly
            if tt in _JE_TYPES:
                if row.get("party") or row.get("party_type"):
                    pass  # allowed but not required — user may optionally set for reference

            if tt in _JE_TYPES:
                if row.get("amortise"):
                    if not row.get("frequency"):
                        frappe.throw(_(f"Row {idx}: Frequency is required when Amortise is ticked."))
                    if not (row.get("no_of_periods") or 0) > 0:
                        frappe.throw(_(f"Row {idx}: No of Periods must be > 0 when Amortise is ticked."))
                    if not row.get("start_date"):
                        frappe.throw(_(f"Row {idx}: Start Date is required when Amortise is ticked."))

    def _calc_totals(self):
        receipts = payments = je_total = 0.0
        for row in self.get("transactions", []):
            receipts += flt(row.get("inflow"))
            payments += flt(row.get("outflow"))
            if row.get("trans_type") in _JE_TYPES:
                je_total += flt(row.get("amount"))
        self.total_receipts  = receipts
        self.total_payments  = payments
        self.total_je_amount = je_total
        self.net_movement    = receipts - payments


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_bank_gl(row, bank_account_name):
    """Return the GL account for the bank leg. Row override > Bank Account master."""
    if row.get("bank_account_gl"):
        return row.get("bank_account_gl")
    gl = frappe.db.get_value("Bank Account", bank_account_name, "account")
    if gl:
        return gl
    frappe.throw(_(
        "Cannot determine Bank GL Account. Set it on the row (Bank GL Override) "
        "or link a GL Account on the Bank Account master."
    ))


def _get_default_account(party_type, company, direction):
    """direction: 'payable' or 'receivable'"""
    field = ("default_receivable_account"
             if direction == "receivable"
             else "default_payable_account")
    acct = frappe.db.get_value("Company", company, field)
    if not acct:
        frappe.throw(_(
            f"No Default {direction.title()} Account set on Company '{company}'. "
            "Please configure it under Accounts Settings."
        ))
    return acct


def _next_date(current_date, frequency):
    """Advance a date by one frequency period."""
    freq_map = {
        "Daily":       lambda d: add_days(d, 1),
        "Weekly":      lambda d: add_days(d, 7),
        "Monthly":     lambda d: add_months(d, 1),
        "Quarterly":   lambda d: add_months(d, 3),
        "Half-yearly": lambda d: add_months(d, 6),
        "Yearly":      lambda d: add_months(d, 12),
    }
    fn = freq_map.get(frequency)
    if not fn:
        frappe.throw(_(f"Unknown frequency '{frequency}'."))
    result = fn(current_date)
    return result if isinstance(result, date) else result


def _cancel_linked_entries(processor_name):
    linked = frappe.db.get_all(
        "Bank Transaction Line",
        filters={"parent": processor_name, "entry_created": 1},
        fields=["name", "entry_reference", "entry_type_created"],
    )
    cancelled = deleted = 0
    for r in linked:
        ename = r.get("entry_reference")
        etype = r.get("entry_type_created")
        if not ename or not etype or not frappe.db.exists(etype, ename):
            continue
        docstatus = frappe.db.get_value(etype, ename, "docstatus")
        try:
            if docstatus == 1:
                frappe.get_doc(etype, ename).cancel()
                cancelled += 1
            elif docstatus == 0:
                frappe.delete_doc(etype, ename, ignore_permissions=True)
                deleted += 1
        except Exception:
            frappe.log_error(frappe.get_traceback(),
                f"BTP {processor_name}: could not cancel {etype} {ename}")

    frappe.db.sql("""
        UPDATE `tabBank Transaction Line`
           SET entry_created=0, entry_reference=NULL, entry_type_created=NULL,
               charged_amount=0, next_posting_date=NULL, next_schedule=0
         WHERE parent=%s
    """, processor_name)
    frappe.db.commit()

    parts = []
    if cancelled: parts.append(f"{cancelled} entr{'y' if cancelled==1 else 'ies'} cancelled")
    if deleted:   parts.append(f"{deleted} draft entr{'y' if deleted==1 else 'ies'} deleted")
    if parts:
        frappe.msgprint(_(f"Processor cancelled — {' and '.join(parts)}."),
                        indicator="orange", alert=True)


# ─────────────────────────────────────────────────────────────────────────────
# Payment Entry builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_payment_entry(row, company, bank_account_name, processor_name):
    """
    Creates a Draft Payment Entry.

    Trans Type     → PE payment_type  / party_type
    ─────────────────────────────────────────────────
    Supplier Payment  → Pay,      Supplier
    Customer Receipt  → Receive,  Customer
    Transfer Out      → Internal Transfer (bank → target)
    Transfer In       → Internal Transfer (source → bank)
    Customer Refund   → Pay,      Customer
    Supplier Refund   → Receive,  Supplier
    """
    tt            = row.get("trans_type")
    payment_type  = _TRANS_TO_PAYMENT_TYPE[tt]
    party_type_pe = _TRANS_TO_PARTY_TYPE.get(tt)
    party         = row.get("party") or ""
    amount        = flt(row.get("amount"))
    exch_rate     = flt(row.get("exch_rate")) or 1.0
    description   = row.get("remark") or ""
    bank_gl       = _get_bank_gl(row, bank_account_name)
    company_ccy   = frappe.db.get_value("Company", company, "default_currency")

    pe = frappe.new_doc("Payment Entry")
    pe.payment_type    = payment_type
    pe.company         = company
    pe.posting_date    = row.get("posting_date")
    pe.mode_of_payment = row.get("mode_of_payment") or "Bank Transfer"
    pe.reference_no    = row.get("reference_no") or processor_name
    pe.reference_date  = row.get("posting_date")
    pe.remarks         = description
    pe.paid_amount     = amount
    pe.received_amount = amount

    if payment_type == "Receive":
        # Money IN: Customer/Supplier pays us → receivable → bank
        pe.party_type = party_type_pe
        pe.party      = party
        pe.paid_from  = _get_default_account(party_type_pe, company, "receivable")
        pe.paid_to    = bank_gl
        pe.paid_from_account_currency = company_ccy
        pe.paid_to_account_currency   = company_ccy

    elif payment_type == "Pay":
        # Money OUT: we pay Supplier/Customer → bank → payable
        pe.party_type = party_type_pe
        pe.party      = party
        pe.paid_from  = bank_gl
        pe.paid_to    = _get_default_account(party_type_pe, company, "payable")
        pe.paid_from_account_currency = company_ccy
        pe.paid_to_account_currency   = company_ccy

    elif payment_type == "Internal Transfer":
        # Transfer Out: bank_gl → target  |  Transfer In: source → bank_gl
        target_gl = row.get("bank_account_gl")
        if tt == "Transfer Out":
            if not target_gl:
                frappe.throw(_(
                    f"Row {row.get('idx')}: Transfer Out requires a target Bank GL in "
                    "'Bank GL Override' field."
                ))
            pe.paid_from = bank_gl
            pe.paid_to   = target_gl
        else:  # Transfer In
            if not target_gl:
                frappe.throw(_(
                    f"Row {row.get('idx')}: Transfer In requires the source Bank GL in "
                    "'Bank GL Override' field."
                ))
            pe.paid_from = target_gl
            pe.paid_to   = bank_gl

        pe.paid_from_account_currency = company_ccy
        pe.paid_to_account_currency   = company_ccy

    if row.get("cost_center"):
        pe.cost_center = row.get("cost_center")
    if row.get("project"):
        pe.project = row.get("project")

    pe.insert(ignore_permissions=True)
    return pe.name


# ─────────────────────────────────────────────────────────────────────────────
# Journal Entry builder (single JE, no amortisation)
# ─────────────────────────────────────────────────────────────────────────────

def _build_journal_entry_single(row, company, bank_account_name, processor_name,
                                 posting_date=None, amount=None, period_num=None):
    """
    Creates one Journal Entry for a Payment or Receipt row.
    Used for immediate (non-amortised) rows and called per-period by the
    amortisation builder.

    The bank GL account is taken from row.bank_account_gl (populated from the
    parent processor's bank_account_gl field). The user only needs to supply
    ONE non-bank GL account per row:

    Payment (expense / cost out of bank):
        Dr  account_to_debit   ← user sets this (expense / cost account)
        Cr  bank_gl            ← auto-resolved from row.bank_account_gl

    Receipt (income / revenue into bank):
        Dr  bank_gl            ← auto-resolved from row.bank_account_gl
        Cr  account_to_credit  ← user sets this (income / revenue account)
    """
    tt          = row.get("trans_type")
    use_amount  = flt(amount if amount is not None else row.get("amount"))
    use_date    = posting_date or row.get("posting_date")
    description = row.get("remark") or ""
    exch_rate   = flt(row.get("exch_rate")) or 1.0

    # ── Resolve bank GL ───────────────────────────────────────────────────────
    # Priority: row.bank_account_gl (copied from parent) → Bank Account master
    bank_gl = (
        row.get("bank_account_gl")
        or frappe.db.get_value("Bank Account", bank_account_name, "account")
    )
    if not bank_gl:
        frappe.throw(_(
            f"Row {row.get('idx')}: Cannot determine Bank GL Account. "
            "Set it on the processor's 'Bank Account GL' field or link a GL "
            "Account on the Bank Account master."
        ))

    # ── Resolve the non-bank leg ──────────────────────────────────────────────
    if tt == "Payment":
        # Money OUT — user specifies the expense/cost account to debit
        non_bank_account = row.get("account_to_debit")
        if not non_bank_account:
            frappe.throw(_(
                f"Row {row.get('idx')}: Account to Debit is required for Payment "
                "(the expense or cost account being charged)."
            ))
        dr_account = non_bank_account
        cr_account = bank_gl

    elif tt == "Receipt":
        # Money IN — user specifies the income/revenue account to credit
        non_bank_account = row.get("account_to_credit")
        if not non_bank_account:
            frappe.throw(_(
                f"Row {row.get('idx')}: Account to Credit is required for Receipt "
                "(the income or revenue account being recognised)."
            ))
        dr_account = bank_gl
        cr_account = non_bank_account

    else:
        frappe.throw(_(f"Row {row.get('idx')}: Unknown JE trans_type '{tt}'."))

    narration = row.get("transaction_description") or description
    if period_num:
        narration = f"{narration} — Period {period_num}"

    je = frappe.new_doc("Journal Entry")
    je.voucher_type             = "Journal Entry"
    je.company                  = company
    je.posting_date             = use_date
    je.user_remark              = narration
    je.paid_to_or_received_from = row.get("party_name") or row.get("payee_name") or ""
    je.cheque_no                = row.get("reference_no") or processor_name
    je.cheque_date              = row.get("posting_date")

    # Leg 1 — Debit side
    je.append("accounts", {
        "account":                    dr_account,
        "debit_in_account_currency":  use_amount,
        "credit_in_account_currency": 0,
        "exchange_rate":              exch_rate,
        "cost_center":                row.get("cost_center") or None,
        "project":                    row.get("project")     or None,
        "user_remark":                narration,
    })

    # Leg 2 — Credit side
    je.append("accounts", {
        "account":                    cr_account,
        "debit_in_account_currency":  0,
        "credit_in_account_currency": use_amount,
        "exchange_rate":              exch_rate,
        "cost_center":                row.get("cost_center") or None,
        "project":                    row.get("project")     or None,
        "user_remark":                narration,
    })

    je.insert(ignore_permissions=True)
    return je.name


# ─────────────────────────────────────────────────────────────────────────────
# Amortisation builder — creates N Journal Entries on a schedule
# ─────────────────────────────────────────────────────────────────────────────

def _build_amortised_entries(row, company, bank_account_name, processor_name):
    """
    Creates the first amortisation-period Journal Entry immediately,
    then stores schedule state (next_posting_date, next_schedule, end_date)
    so that subsequent periods can be triggered by a scheduled job or manually.

    Returns the name of the first JE created.

    Amortisation pattern:
      Total amount / no_of_periods = per-period amount
      Starting from start_date, one JE per frequency until no_of_periods reached.
    """
    total_amount = flt(row.get("amount"))
    n_periods    = int(row.get("no_of_periods") or 0)
    frequency    = row.get("frequency") or ""
    start_date   = row.get("start_date")

    if n_periods <= 0:
        frappe.throw(_(f"Row {row.get('idx')}: No of Periods must be > 0."))
    if not frequency:
        frappe.throw(_(f"Row {row.get('idx')}: Frequency is required for amortisation."))
    if not start_date:
        frappe.throw(_(f"Row {row.get('idx')}: Start Date is required for amortisation."))

    per_period  = round(total_amount / n_periods, 2)
    # Adjust last period for rounding
    last_period = round(total_amount - per_period * (n_periods - 1), 2)

    # Create period 1 immediately
    amount_p1 = per_period if n_periods > 1 else last_period
    je_name = _build_journal_entry_single(
        row, company, bank_account_name, processor_name,
        posting_date=start_date,
        amount=amount_p1,
        period_num=1,
    )

    # Compute schedule state
    next_date_val = _next_date(
        start_date if isinstance(start_date, date)
        else datetime.strptime(str(start_date), "%Y-%m-%d").date(),
        frequency,
    )
    end_date_val = start_date
    for _ in range(n_periods - 1):
        end_date_val = _next_date(
            end_date_val if isinstance(end_date_val, date)
            else datetime.strptime(str(end_date_val), "%Y-%m-%d").date(),
            frequency,
        )

    # Persist schedule on the row
    frappe.db.set_value("Bank Transaction Line", row.name, {
        "charged_amount":    amount_p1,
        "next_posting_date": str(next_date_val) if n_periods > 1 else None,
        "next_schedule":     2 if n_periods > 1 else 0,
        "end_date":          str(end_date_val),
    }, update_modified=False)

    return je_name


# ─────────────────────────────────────────────────────────────────────────────
# Whitelisted: post next amortisation period
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def post_next_amortisation_period(processor_name: str, row_name: str) -> dict:
    """
    Creates the next Journal Entry in an amortisation schedule.
    Called manually by the user (or by a scheduled job) to post each period.
    """
    if not frappe.db.exists("Bank Transaction Line", row_name):
        frappe.throw(_("Row not found."))

    row = frappe.get_doc("Bank Transaction Line", row_name)

    n_periods   = int(row.get("no_of_periods") or 0)
    next_sched  = int(row.get("next_schedule") or 0)
    next_date   = row.get("next_posting_date")

    if not next_sched or next_sched > n_periods:
        frappe.throw(_("All amortisation periods have already been posted."))
    if not next_date:
        frappe.throw(_("No next posting date found on this row."))

    company      = frappe.db.get_value("Bank Transaction Processor", processor_name, "company")
    bank_account = frappe.db.get_value("Bank Transaction Processor", processor_name, "bank_account")

    total_amount   = flt(row.get("amount"))
    charged_so_far = flt(row.get("charged_amount"))
    per_period     = round(total_amount / n_periods, 2)
    is_last        = (next_sched == n_periods)
    this_amount    = round(total_amount - charged_so_far, 2) if is_last else per_period

    je_name = _build_journal_entry_single(
        row, company, bank_account, processor_name,
        posting_date=next_date,
        amount=this_amount,
        period_num=next_sched,
    )

    new_charged = charged_so_far + this_amount
    if is_last:
        new_next_date   = None
        new_next_sched  = 0
    else:
        nd = next_date if isinstance(next_date, date) else datetime.strptime(str(next_date), "%Y-%m-%d").date()
        new_next_date   = str(_next_date(nd, row.get("frequency")))
        new_next_sched  = next_sched + 1

    frappe.db.set_value("Bank Transaction Line", row_name, {
        "charged_amount":    new_charged,
        "next_posting_date": new_next_date,
        "next_schedule":     new_next_sched,
    }, update_modified=False)
    frappe.db.commit()

    return {
        "journal_entry": je_name,
        "period":        next_sched,
        "remaining":     max(0, n_periods - next_sched),
        "message":       f"Period {next_sched} posted → JE {je_name}. "
                         + (f"{n_periods - next_sched} period(s) remaining." if not is_last
                            else "All periods complete."),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Internal: route one row to the right builder
# ─────────────────────────────────────────────────────────────────────────────

def _process_row(row, company, bank_account_name, processor_name):
    """Returns (entry_name, entry_doctype) or (None, 'Pending')."""
    tt = row.get("trans_type") or ""

    if tt == "Pending":
        return None, "Pending"

    if tt in _PE_TYPES:
        name = _build_payment_entry(row, company, bank_account_name, processor_name)
        return name, "Payment Entry"

    if tt in _JE_TYPES:
        if row.get("amortise"):
            name = _build_amortised_entries(row, company, bank_account_name, processor_name)
        else:
            name = _build_journal_entry_single(row, company, bank_account_name, processor_name)
        return name, "Journal Entry"

    frappe.throw(_(f"Unknown Trans Type '{tt}'."))


# ─────────────────────────────────────────────────────────────────────────────
# Whitelisted: create entry for a single row
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def create_entry_for_row(processor_name: str, row_name: str) -> dict:
    status = frappe.db.get_value("Bank Transaction Processor", processor_name, "status")
    if status in ("Submitted", "Cancelled"):
        frappe.throw(_(f"Processor is {status}. Cannot create more entries."))

    if not frappe.db.exists("Bank Transaction Line", row_name):
        frappe.throw(_("Row not found. Please save the processor first."))

    row = frappe.get_doc("Bank Transaction Line", row_name)
    if row.parent != processor_name:
        frappe.throw(_("Row does not belong to this processor."))
    if row.get("entry_created"):
        frappe.throw(_(f"{row.entry_type_created or 'Entry'} {row.entry_reference or ''} already created."))
    if row.get("trans_type") == "Pending":
        frappe.throw(_("This row is marked Pending — no entry will be created."))

    company      = frappe.db.get_value("Bank Transaction Processor", processor_name, "company")
    bank_account = frappe.db.get_value("Bank Transaction Processor", processor_name, "bank_account")

    if not company:
        frappe.throw(_("Company is not set on the processor."))
    if not bank_account:
        frappe.throw(_("Bank Account is not set on the processor."))

    try:
        entry_name, entry_dtype = _process_row(row, company, bank_account, processor_name)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(),
            f"BTP {processor_name}: failed row {row_name}")
        frappe.throw(_(f"Failed to create entry: {e}"))

    frappe.db.set_value("Bank Transaction Line", row_name, {
        "entry_created":      1,
        "entry_reference":    entry_name or "",
        "entry_type_created": entry_dtype,
    }, update_modified=False)
    frappe.db.commit()

    return {
        "entry":      entry_name,
        "entry_type": entry_dtype,
        "message":    f"{entry_dtype} {entry_name or ''} created as Draft."
                      + (" First amortisation period posted." if row.get("amortise") else ""),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Whitelisted: create all unprocessed rows at once
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def create_all_entries(processor_name: str) -> dict:
    status = frappe.db.get_value("Bank Transaction Processor", processor_name, "status")
    if status in ("Submitted", "Cancelled"):
        frappe.throw(_(f"Processor is {status}."))

    proc         = frappe.get_doc("Bank Transaction Processor", processor_name)
    company      = proc.company
    bank_account = proc.bank_account

    created = skipped = errors = 0
    results = []

    for row in proc.get("transactions", []):
        if row.get("entry_created"):
            skipped += 1; continue
        if not flt(row.get("amount")):
            skipped += 1; continue
        if row.get("trans_type") == "Pending":
            skipped += 1; continue

        try:
            entry_name, entry_dtype = _process_row(row, company, bank_account, processor_name)
            frappe.db.set_value("Bank Transaction Line", row.name, {
                "entry_created":      1,
                "entry_reference":    entry_name or "",
                "entry_type_created": entry_dtype,
            }, update_modified=False)
            results.append({"row": row.idx, "entry": entry_name,
                            "type": entry_dtype, "status": "created"})
            created += 1
        except Exception as e:
            frappe.log_error(frappe.get_traceback(),
                f"BTP {processor_name}: bulk failed row {row.idx}")
            results.append({"row": row.idx, "status": "error", "error": str(e)})
            errors += 1

    frappe.db.commit()
    return {
        "created": created, "skipped": skipped, "errors": errors,
        "results": results,
        "message": f"Created: {created} | Skipped: {skipped} | Errors: {errors}",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Whitelisted: party name lookup
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_party_name(party_type: str, party: str) -> str:
    if not party or not party_type:
        return ""
    m = {
        "Supplier":    ("Supplier",    "supplier_name"),
        "Customer":    ("Customer",    "customer_name"),
        "Employee":    ("Employee",    "employee_name"),
        "Shareholder": ("Shareholder", "shareholder_name"),
    }
    entry = m.get(party_type)
    if not entry:
        return party
    return frappe.db.get_value(entry[0], party, entry[1]) or party


# ─────────────────────────────────────────────────────────────────────────────
# Whitelisted: Excel Export
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def export_to_excel(processor_name: str) -> dict:
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        frappe.throw(_("openpyxl is not installed."))

    proc = frappe.get_doc("Bank Transaction Processor", processor_name)
    wb   = openpyxl.Workbook()
    ws   = wb.active
    ws.title = "Bank Transactions"

    thin  = Side(style="thin",   color="AAAAAA")
    thick = Side(style="medium", color="1F4E79")
    cb    = Border(left=thin,  right=thin,  top=thin,  bottom=thin)
    hb    = Border(left=thick, right=thick, top=thick, bottom=thick)
    REQ   = PatternFill("solid", start_color="1F4E79")
    OPT   = PatternFill("solid", start_color="2E75B6")
    DONE  = PatternFill("solid", start_color="D4EDDA")
    PEND  = PatternFill("solid", start_color="FFF3CD")
    ALT   = PatternFill("solid", start_color="EBF3FB")
    NONE  = PatternFill(fill_type=None)
    WB    = Font(name="Arial", bold=True,  color="FFFFFF", size=10)
    WN    = Font(name="Arial", bold=False, color="FFFFFF", size=10)
    DF    = Font(name="Arial", size=10)
    GB    = Font(name="Arial", bold=True,  color="155724", size=10)
    CTR   = Alignment(horizontal="center", vertical="center", wrap_text=True)
    LFT   = Alignment(horizontal="left",   vertical="center")

    REQ_IDX        = {i for i,(_, __, r, ___) in enumerate(_COLUMNS) if r}
    export_headers = [h for h,*_ in _COLUMNS] + [
        "Inflow","Outflow","Entry Created","Entry Reference","Entry Type",
        "Next Posting Date","Next Period #","Charged So Far",
    ]
    widths = [12,18,30,12,16,24,28,20,24,24,20,18,16,10,12,14,18,14,14,12,18,14,
              8,12,10,12,28,10,10,12,18,10,12,28,18]

    ws.row_dimensions[1].height = 40
    for ci, hdr in enumerate(export_headers, 1):
        c = ws.cell(row=1, column=ci, value=hdr)
        c.font = WB if (ci-1) in REQ_IDX else WN
        c.fill = REQ if (ci-1) in REQ_IDX else OPT
        c.alignment = CTR; c.border = hb
        if ci <= len(widths):
            ws.column_dimensions[get_column_letter(ci)].width = widths[ci-1]

    for ri, row in enumerate(proc.transactions, 2):
        done = bool(row.entry_created)
        pend = row.trans_type == "Pending"
        alt  = ri % 2 == 0
        vals = [
            str(row.posting_date)         if row.posting_date else "",
            row.trans_type                or "",
            row.remark                    or "",
            flt(row.amount),
            row.party_type                or "",
            row.party                     or "",
            row.party_name                or "",
            row.payee_name                or "",
            row.account_to_debit          or "",
            row.account_to_credit         or "",
            row.bank_account_gl           or "",
            row.mode_of_payment           or "",
            row.reference_no              or "",
            flt(row.exch_rate)            if row.exch_rate else 1.0,
            flt(row.amount_in_fc)         if row.amount_in_fc else "",
            row.transaction_currency      or "",
            row.cost_center               or "",
            row.department                or "",
            row.project                   or "",
            row.branch                    or "",
            row.nature_of_expense         or "",
            row.customer_id               or "",
            1 if row.amortise else 0,
            row.frequency                 or "",
            int(row.no_of_periods or 0),
            str(row.start_date)           if row.start_date else "",
            row.transaction_description   or "",
            flt(row.inflow),
            flt(row.outflow),
            "YES" if done else ("PENDING" if pend else "NO"),
            row.entry_reference           or "",
            row.entry_type_created        or "",
            str(row.next_posting_date)    if row.next_posting_date else "",
            int(row.next_schedule or 0),
            flt(row.charged_amount),
        ]
        for ci, v in enumerate(vals, 1):
            c = ws.cell(row=ri, column=ci, value=v)
            c.font   = GB if done and ci >= 28 else DF
            c.fill   = DONE if done else (PEND if pend else (ALT if alt else NONE))
            c.border = cb; c.alignment = LFT
        ws.cell(row=ri, column=4).number_format  = "#,##0.00"
        ws.cell(row=ri, column=28).number_format = "#,##0.00"
        ws.cell(row=ri, column=29).number_format = "#,##0.00"

    ws.freeze_panes = "C2"

    wi = wb.create_sheet("Export Info")
    wi.column_dimensions["A"].width = 24
    wi.column_dimensions["B"].width = 40
    BF = Font(name="Arial", bold=True, size=10)
    NF = Font(name="Arial", size=10)
    for r,(lbl,val) in enumerate([
        ("Processor",      processor_name),
        ("Company",        proc.company or ""),
        ("Bank Account",   proc.bank_account or ""),
        ("Status",         proc.status  or "Draft"),
        ("Exported By",    frappe.session.user),
        ("Exported At",    datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("Total Rows",     len(proc.transactions)),
        ("Total Receipts", flt(proc.total_receipts)),
        ("Total Payments", flt(proc.total_payments)),
        ("Net Movement",   flt(proc.net_movement)),
    ], 1):
        wi.cell(row=r, column=1, value=lbl).font = BF
        wi.cell(row=r, column=2, value=val).font = NF

    buf = io.BytesIO()
    wb.save(buf); buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    return {
        "filename":     f"BTP_{processor_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        "file_content": b64,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Whitelisted: Excel Import
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def import_from_excel(processor_name: str, file_content: str, filename: str) -> dict:
    try:
        import openpyxl
    except ImportError:
        frappe.throw(_("openpyxl is not installed."))

    try:
        raw = base64.b64decode(file_content)
    except Exception:
        frappe.throw(_("Invalid file encoding."))
    try:
        wb = openpyxl.load_workbook(io.BytesIO(raw), data_only=True)
    except Exception as e:
        frappe.throw(_(f"Cannot open Excel file: {e}"))

    ws = wb["Bank Transactions"] if "Bank Transactions" in wb.sheetnames else wb.active
    hdr  = [str(c.value).strip() if c.value else "" for c in ws[1]]
    cidx = {name: idx for idx, name in enumerate(hdr)}

    missing = [h for h,*_ in _COLUMNS if h not in cidx]
    if missing:
        frappe.throw(_(f"Missing columns: {', '.join(missing)}"))

    proc = frappe.get_doc("Bank Transaction Processor", processor_name)
    if proc.status == "Submitted":
        frappe.throw(_("Cannot import into a Submitted processor."))

    imported = skipped = 0
    errors = []

    for excel_row, vals in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
        if all(v is None or str(v).strip() == "" for v in vals):
            skipped += 1; continue

        row_errors = []
        data = {}

        for hdr_lbl, fieldname, required, dtype in _COLUMNS:
            idx   = cidx.get(hdr_lbl)
            raw_v = vals[idx] if idx is not None else None
            if raw_v is not None and str(raw_v).strip() == "":
                raw_v = None
            if required and raw_v is None:
                row_errors.append(f"'{hdr_lbl}' is required")
                continue
            if raw_v is None:
                data[fieldname] = None; continue

            val = str(raw_v).strip()
            if dtype == "date":
                try:
                    data[fieldname] = (raw_v.strftime("%Y-%m-%d")
                                       if hasattr(raw_v, "strftime")
                                       else datetime.strptime(val, "%Y-%m-%d").strftime("%Y-%m-%d"))
                except ValueError:
                    row_errors.append(f"'{hdr_lbl}' must be YYYY-MM-DD")
            elif dtype == "float":
                try:
                    data[fieldname] = float(val)
                except ValueError:
                    row_errors.append(f"'{hdr_lbl}' must be a number")
            elif dtype == "int":
                try:
                    data[fieldname] = int(float(val))
                except ValueError:
                    row_errors.append(f"'{hdr_lbl}' must be an integer")
            else:
                data[fieldname] = val

        if data.get("amount") is not None and flt(data.get("amount", 0)) <= 0:
            row_errors.append("Amount must be > 0")

        # For PE types: party and party_type are required (unless Internal Transfer)
        tt_import = data.get("trans_type") or ""
        if tt_import in {"Supplier Payment", "Customer Receipt", "Customer Refund", "Supplier Refund"}:
            if not data.get("party_type"):
                row_errors.append("'Party Type' is required for " + tt_import)
            if not data.get("party"):
                row_errors.append("'Party' is required for " + tt_import)
        if row_errors:
            errors.append({"row": excel_row, "errors": row_errors,
                           "description": data.get("remark","")})
            skipped += 1; continue

        if data.get("party_type") and data.get("party"):
            data["party_name"] = get_party_name(data["party_type"], data["party"])
        data.setdefault("exch_rate", 1.0)

        proc.append("transactions", data)
        imported += 1

    if imported > 0:
        proc.save(ignore_permissions=False)
        frappe.db.commit()

    return {
        "rows_imported": imported, "rows_skipped": skipped,
        "errors": errors,
        "message": f"{imported} row(s) imported." + (f" {skipped} skipped." if skipped else ""),
    }