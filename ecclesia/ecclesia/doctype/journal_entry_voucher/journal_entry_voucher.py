# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

"""
Journal Entry Voucher — Controller
===================================
Built around the confirmed-working create_bulk_journal_entries() logic.

Key design decisions
---------------------
* account_type drives everything. "Account GL" → no party_type on JE leg.
  Supplier/Customer → use company default payable/receivable.
  Employee         → use company default payable.
* party_doctype hidden field is NOT required for JE creation — we derive
  it entirely from account_type at runtime, exactly like the working script.
* JEs are created as Draft so the user can review before submitting the voucher.
* Voucher cancel → cancel submitted JEs, delete draft JEs, reset row flags.
* paid_to_or_received_from is populated from party_name on each JE.
* cheque_no stores the voucher name; cheque_date mirrors trans_date.
"""

import io, base64
from datetime import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today


# ── Column map (shared by Excel import / export) ─────────────────────────────
# (header_label, child_fieldname, required, dtype)
_COLUMNS = [
    ("Trans Date*",               "trans_date",               True,  "date"),
    ("Transaction Description*",  "transaction_description",  True,  "str"),
    ("Acct Type*",                "account_type",             True,  "str"),
    ("Party*",                    "party",                    True,  "str"),
    ("Party Name",                "party_name",               False, "str"),
    ("Corresponding Account*",    "corresponding_account",    True,  "str"),
    ("Corresponding Effect",      "corresponding_effect",     False, "str"),
    ("Trans Effect*",             "trans_effect",             True,  "str"),
    ("Amount*",                   "amount",                   True,  "float"),
    ("Amount in FC",              "amount_in_fc",             False, "float"),
    ("Exchange Rate",             "exchange_rate",            False, "float"),
    ("Cost Center",               "cost_center",              False, "str"),
    ("Project",                   "project",                  False, "str"),
    ("Branch",                    "branch",                   False, "str"),
    ("Corresponding Cost Center", "corresponding_cost_center",False, "str"),
    ("Corresponding Project",     "corresponding_project",    False, "str"),
]

_VALID_ACCT_TYPES   = {"Supplier", "Customer", "Employee", "Account GL"}
_VALID_TRANS_EFFECT = {"Debit", "Credit"}
_VALID_CORR_EFFECT  = {"Auto (Opposite)", "Debit", "Credit", ""}

# Maps account_type → party_type value for the JE accounts table
# "Account GL" has no party_type — it is a direct GL account entry
_ACCT_TO_PARTY_TYPE = {
    "Supplier":   "Supplier",
    "Customer":   "Customer",
    "Employee":   "Employee",
    "Account GL": None,
}


# ─────────────────────────────────────────────────────────────────────────────
# DocType controller
# ─────────────────────────────────────────────────────────────────────────────

class JournalEntryVoucher(Document):

    def validate(self):
        self._validate_rows()
        self._calc_totals()

    def on_submit(self):
        self.db_set("status", "Submitted")
        self.db_set("submit_remarks",
            f"Submitted on {today()} by {frappe.session.user}.")

    def on_cancel(self):
        _cancel_linked_journal_entries(self.name)
        self.db_set("status", "Cancelled")

    # ── private ──────────────────────────────────────────────────────────────

    def _validate_rows(self):
        for idx, row in enumerate(self.get("accounts", []), start=1):
            if not row.get("account_type"):
                frappe.throw(_(f"Row {idx}: Acct Type is required."))
            if not row.get("party"):
                frappe.throw(_(f"Row {idx}: Party is required."))
            if not row.get("corresponding_account"):
                frappe.throw(_(f"Row {idx}: Corresponding Account is required."))
            if not row.get("trans_effect"):
                frappe.throw(_(f"Row {idx}: Trans Effect is required."))
            if flt(row.get("amount")) <= 0:
                frappe.throw(_(f"Row {idx}: Amount must be greater than zero."))

    def _calc_totals(self):
        dr = cr = 0.0
        for row in self.get("accounts", []):
            if row.get("trans_effect") == "Debit":
                dr += flt(row.get("amount"))
            elif row.get("trans_effect") == "Credit":
                cr += flt(row.get("amount"))
        self.total_debit  = dr
        self.total_credit = cr
        self.difference   = dr - cr


# ─────────────────────────────────────────────────────────────────────────────
# Internal: cancel/delete JEs when voucher is cancelled
# ─────────────────────────────────────────────────────────────────────────────

def _cancel_linked_journal_entries(voucher_name):
    """Cancel submitted JEs and delete draft JEs linked to this voucher."""
    linked = frappe.db.get_all(
        "Journal Entry Voucher Account",
        filters={"parent": voucher_name, "journal_entry_created": 1},
        fields=["name", "journal_entry_reference"],
    )
    cancelled = deleted = 0
    for row_data in linked:
        je_name = row_data.get("journal_entry_reference")
        if not je_name or not frappe.db.exists("Journal Entry", je_name):
            continue
        docstatus = frappe.db.get_value("Journal Entry", je_name, "docstatus")
        try:
            if docstatus == 1:          # Submitted → cancel
                frappe.get_doc("Journal Entry", je_name).cancel()
                cancelled += 1
            elif docstatus == 0:        # Draft → delete
                frappe.delete_doc("Journal Entry", je_name, ignore_permissions=True)
                deleted += 1
        except Exception:
            frappe.log_error(frappe.get_traceback(),
                f"JEV {voucher_name}: could not cancel/delete JE {je_name}")

    # Reset flags on all child rows
    frappe.db.sql("""
        UPDATE `tabJournal Entry Voucher Account`
           SET journal_entry_created = 0,
               journal_entry_reference = NULL
         WHERE parent = %s
    """, voucher_name)
    frappe.db.commit()

    parts = []
    if cancelled: parts.append(f"{cancelled} JE(s) cancelled")
    if deleted:   parts.append(f"{deleted} draft JE(s) deleted")
    if parts:
        frappe.msgprint(_(f"Voucher cancelled. {' and '.join(parts)}."),
                        indicator="orange", alert=True)


# ─────────────────────────────────────────────────────────────────────────────
# Internal: core JE builder  ← THE WORKING LOGIC, verbatim + enhancements
# ─────────────────────────────────────────────────────────────────────────────

def _build_and_insert_je(row, company, default_payable, default_receivable, voucher_name):
    """
    Build and insert one Journal Entry for a single voucher row.
    Returns the created JE name on success, raises on failure.

    Logic mirrors the confirmed-working create_bulk_journal_entries() script
    exactly, with these additions:
      - paid_to_or_received_from  ← party_name
      - cheque_no                 ← voucher name (for traceability)
      - cheque_date               ← trans_date
      - cost_center / project on both legs
      - exchange_rate support
    """
    flt_local = frappe.utils.flt

    # ── Resolve account for the party leg ────────────────────────────────────
    # Mirrors working script logic exactly:
    #   Supplier → default_payable
    #   Customer → default_receivable
    #   Employee → default_payable   (employees are a payable liability)
    #   Account GL → use row.party directly (it IS the account)
    account_type = row.get("account_type") or ""
    party        = row.get("party") or ""
    amount       = flt_local(row.get("amount"))

    if account_type == "Supplier":
        account = default_payable
    elif account_type == "Customer":
        account = default_receivable
    elif account_type == "Employee":
        account = default_payable
    elif account_type == "Account GL":
        account = party      # party field holds the GL account code
    else:
        frappe.throw(_(f"Unknown Acct Type '{account_type}'."))

    if not account:
        frappe.throw(_(
            f"No default account found for '{account_type}'. "
            "Set the Default Payable / Receivable Account on the Company record."
        ))

    # ── Debit / credit amounts ────────────────────────────────────────────────
    debit  = amount if row.get("trans_effect") == "Debit"  else 0
    credit = amount if row.get("trans_effect") == "Credit" else 0

    corr_effect = row.get("corresponding_effect") or "Auto (Opposite)"
    if corr_effect == "Auto (Opposite)":
        corr_debit  = credit
        corr_credit = debit
    else:
        corr_debit  = amount if corr_effect == "Debit"  else 0
        corr_credit = amount if corr_effect == "Credit" else 0

    # ── party_type for the JE leg ─────────────────────────────────────────────
    # "Account GL" has no party_type; everything else maps 1-to-1
    party_type = _ACCT_TO_PARTY_TYPE.get(account_type)

    exchange_rate = flt_local(row.get("exchange_rate")) or 1.0

    # ── Description ───────────────────────────────────────────────────────────
    description = row.get("transaction_description") or ""

    # ── Build JE ──────────────────────────────────────────────────────────────
    je = frappe.new_doc("Journal Entry")
    je.voucher_type              = "Journal Entry"
    je.company                   = company
    je.posting_date              = row.get("trans_date")
    je.user_remark               = description
    je.paid_to_or_received_from  = row.get("party_name") or party
    je.cheque_no                 = voucher_name          # traceability
    je.cheque_date               = row.get("trans_date")

    # Leg 1 — Party side
    party_leg = {
        "account":                    account,
        "debit_in_account_currency":  debit,
        "credit_in_account_currency": credit,
        "exchange_rate":              exchange_rate,
        "cost_center":                row.get("cost_center")  or None,
        "project":                    row.get("project")      or None,
        "user_remark":                description,
    }
    if party_type:                          # only for Supplier/Customer/Employee
        party_leg["party_type"] = party_type
        party_leg["party"]      = party
    je.append("accounts", party_leg)

    # Leg 2 — Corresponding account
    je.append("accounts", {
        "account":                    row.get("corresponding_account"),
        "debit_in_account_currency":  corr_debit,
        "credit_in_account_currency": corr_credit,
        "exchange_rate":              exchange_rate,
        "cost_center":                row.get("corresponding_cost_center") or None,
        "project":                    row.get("corresponding_project")     or None,
        "user_remark":                description,
    })

    je.insert(ignore_permissions=True)
    # Leave as Draft — user reviews before submitting voucher.
    # Uncomment to auto-submit: je.submit()
    return je.name


# ─────────────────────────────────────────────────────────────────────────────
# Whitelisted: create JE for a single row (button click)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def create_journal_entry_for_row(voucher_name: str, row_name: str) -> dict:
    """
    Called by the 'Create Journal Entry' button on each child row.
    Creates a single Draft JE for that row.
    """
    # Guard: voucher state
    voucher_status = frappe.db.get_value("Journal Entry Voucher", voucher_name, "status")
    if voucher_status in ("Submitted", "Cancelled"):
        frappe.throw(_(f"Voucher {voucher_name} is {voucher_status}. Cannot create more JEs."))

    # Fetch row from DB (reliable — uses the DB primary key set after save)
    if not frappe.db.exists("Journal Entry Voucher Account", row_name):
        frappe.throw(_("Row not found. Please save the voucher first, then click Create Journal Entry."))

    row = frappe.get_doc("Journal Entry Voucher Account", row_name)

    if row.parent != voucher_name:
        frappe.throw(_(f"Row does not belong to voucher {voucher_name}."))

    # Duplicate guard
    if row.get("journal_entry_created"):
        frappe.throw(_(
            f"Journal Entry {row.journal_entry_reference or ''} already created for this row."
        ))

    # Fetch company defaults
    company           = frappe.db.get_value("Journal Entry Voucher", voucher_name, "company")
    default_payable   = frappe.db.get_value("Company", company, "default_payable_account")
    default_receivable = frappe.db.get_value("Company", company, "default_receivable_account")

    if not company:
        frappe.throw(_("Company is not set on the voucher."))

    try:
        je_name = _build_and_insert_je(
            row, company, default_payable, default_receivable, voucher_name
        )
    except Exception as e:
        frappe.log_error(frappe.get_traceback(),
            f"JEV {voucher_name}: JE creation failed for row {row_name}")
        frappe.throw(_(f"Failed to create Journal Entry: {e}"))

    # Mark row as done
    frappe.db.set_value(
        "Journal Entry Voucher Account", row_name,
        {"journal_entry_created": 1, "journal_entry_reference": je_name},
        update_modified=False,
    )
    frappe.db.commit()

    return {
        "journal_entry": je_name,
        "message": f"Journal Entry {je_name} created as Draft.",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Whitelisted: create JEs for ALL unprocessed rows at once
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def create_all_journal_entries(voucher_name: str) -> dict:
    """
    Bulk-creates Draft JEs for every row that doesn't yet have one.
    Mirrors create_bulk_journal_entries() from the working script.
    Skips rows with journal_entry_created=1 (no duplicates).
    Skips rows with no amount.
    Logs errors per-row without aborting the batch.
    """
    voucher_status = frappe.db.get_value("Journal Entry Voucher", voucher_name, "status")
    if voucher_status in ("Submitted", "Cancelled"):
        frappe.throw(_(f"Voucher is {voucher_status}. Cannot create JEs."))

    voucher = frappe.get_doc("Journal Entry Voucher", voucher_name)
    company = voucher.company

    if not company:
        frappe.throw(_("Company is not set on the voucher."))

    default_payable    = frappe.db.get_value("Company", company, "default_payable_account")
    default_receivable = frappe.db.get_value("Company", company, "default_receivable_account")

    created = skipped = errors = 0
    results = []

    for row in voucher.get("accounts", []):
        # Skip already processed
        if row.get("journal_entry_created"):
            skipped += 1
            continue

        # Skip rows with no amount
        if not flt(row.get("amount")):
            skipped += 1
            continue

        try:
            je_name = _build_and_insert_je(
                row, company, default_payable, default_receivable, voucher_name
            )
            frappe.db.set_value(
                "Journal Entry Voucher Account", row.name,
                {"journal_entry_created": 1, "journal_entry_reference": je_name},
                update_modified=False,
            )
            results.append({"row": row.idx, "je": je_name, "status": "created"})
            created += 1

        except Exception as e:
            frappe.log_error(frappe.get_traceback(),
                f"JEV {voucher_name}: bulk JE failed row {row.idx}")
            results.append({"row": row.idx, "status": "error", "error": str(e)})
            errors += 1

    frappe.db.commit()

    return {
        "created": created,
        "skipped": skipped,
        "errors":  errors,
        "results": results,
        "message": f"Created: {created} | Skipped: {skipped} | Errors: {errors}",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Whitelisted: party name lookup (JS on-change)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_party_name(account_type: str, party: str) -> str:
    if not party or not account_type:
        return ""
    doctype_map = {
        "Supplier":   ("Supplier",  "supplier_name"),
        "Customer":   ("Customer",  "customer_name"),
        "Employee":   ("Employee",  "employee_name"),
        "Account GL": ("Account",   "account_name"),
    }
    entry = doctype_map.get(account_type)
    if not entry:
        return party
    return frappe.db.get_value(entry[0], party, entry[1]) or party


# ─────────────────────────────────────────────────────────────────────────────
# Whitelisted: Excel Export
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def export_to_excel(voucher_name: str) -> dict:
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        frappe.throw(_("openpyxl is not installed. Run: pip install openpyxl"))

    voucher = frappe.get_doc("Journal Entry Voucher", voucher_name)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Journal Lines"

    # Styles
    thin  = Side(style="thin",   color="AAAAAA")
    thick = Side(style="medium", color="1F3864")
    cb    = Border(left=thin,  right=thin,  top=thin,  bottom=thin)
    hb    = Border(left=thick, right=thick, top=thick, bottom=thick)
    REQ   = PatternFill("solid", start_color="2E75B6")
    OPT   = PatternFill("solid", start_color="4472C4")
    DONE  = PatternFill("solid", start_color="D4EDDA")
    ALT   = PatternFill("solid", start_color="EBF3FB")
    NONE  = PatternFill(fill_type=None)
    WB    = Font(name="Arial", bold=True,  color="FFFFFF", size=10)
    WN    = Font(name="Arial", bold=False, color="FFFFFF", size=10)
    DF    = Font(name="Arial", size=10)
    GB    = Font(name="Arial", bold=True,  color="155724", size=10)
    CTR   = Alignment(horizontal="center", vertical="center", wrap_text=True)
    LFT   = Alignment(horizontal="left",   vertical="center")

    REQ_IDX        = {i for i,(_, __, r, ___) in enumerate(_COLUMNS) if r}
    export_headers = [h for h,*_ in _COLUMNS] + ["JE Created","Journal Entry Reference"]
    widths         = [14,32,16,24,28,28,22,14,14,14,14,20,20,16,24,24,14,28]

    ws.row_dimensions[1].height = 38
    for ci, hdr in enumerate(export_headers, 1):
        c = ws.cell(row=1, column=ci, value=hdr)
        c.font = WB if (ci-1) in REQ_IDX else WN
        c.fill = REQ if (ci-1) in REQ_IDX else OPT
        c.alignment = CTR; c.border = hb
        if ci <= len(widths):
            ws.column_dimensions[get_column_letter(ci)].width = widths[ci-1]

    for ri, row in enumerate(voucher.accounts, 2):
        alt  = ri % 2 == 0
        done = bool(row.journal_entry_created)
        vals = [
            str(row.trans_date)              if row.trans_date else "",
            row.transaction_description      or "",
            row.account_type                 or "",
            row.party                        or "",
            row.party_name                   or "",
            row.corresponding_account        or "",
            row.corresponding_effect         or "Auto (Opposite)",
            row.trans_effect                 or "",
            flt(row.amount),
            flt(row.amount_in_fc)            if row.amount_in_fc else "",
            flt(row.exchange_rate)           if row.exchange_rate else 1.0,
            row.cost_center                  or "",
            row.project                      or "",
            row.branch                       or "",
            row.corresponding_cost_center    or "",
            row.corresponding_project        or "",
            "YES" if done else "NO",
            row.journal_entry_reference      or "",
        ]
        for ci, v in enumerate(vals, 1):
            c = ws.cell(row=ri, column=ci, value=v)
            c.font      = GB if done and ci >= 17 else DF
            c.fill      = DONE if done else (ALT if alt else NONE)
            c.border    = cb;  c.alignment = LFT
        ws.cell(row=ri, column=9).number_format  = "#,##0.00"
        ws.cell(row=ri, column=10).number_format = "#,##0.00"
        ws.cell(row=ri, column=11).number_format = "#,##0.000000"

    ws.freeze_panes = "C2"

    # Info sheet
    wi = wb.create_sheet("Export Info")
    wi.column_dimensions["A"].width = 24
    wi.column_dimensions["B"].width = 40
    BF = Font(name="Arial", bold=True, size=10)
    NF = Font(name="Arial", size=10)
    for r,(lbl,val) in enumerate([
        ("Voucher",      voucher_name),
        ("Company",      voucher.company or ""),
        ("Status",       voucher.status  or "Draft"),
        ("Exported By",  frappe.session.user),
        ("Exported At",  datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("Total Rows",   len(voucher.accounts)),
        ("Total Debit",  flt(voucher.total_debit)),
        ("Total Credit", flt(voucher.total_credit)),
        ("Difference",   flt(voucher.difference)),
    ], 1):
        wi.cell(row=r, column=1, value=lbl).font = BF
        wi.cell(row=r, column=2, value=val).font = NF

    buf = io.BytesIO()
    wb.save(buf); buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    return {
        "filename":     f"JEV_{voucher_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        "file_content": b64,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Whitelisted: Excel Import
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def import_from_excel(voucher_name: str, file_content: str, filename: str) -> dict:
    try:
        import openpyxl
    except ImportError:
        frappe.throw(_("openpyxl is not installed. Run: pip install openpyxl"))

    try:
        raw = base64.b64decode(file_content)
    except Exception:
        frappe.throw(_("Invalid file encoding."))

    try:
        wb = openpyxl.load_workbook(io.BytesIO(raw), data_only=True)
    except Exception as e:
        frappe.throw(_(f"Cannot open Excel file: {e}"))

    ws = wb["Journal Lines"] if "Journal Lines" in wb.sheetnames else wb.active

    hdr_row   = [str(c.value).strip() if c.value else "" for c in ws[1]]
    col_index = {name: idx for idx, name in enumerate(hdr_row)}

    missing = [h for h,*_ in _COLUMNS if h not in col_index]
    if missing:
        frappe.throw(_(f"Missing columns: {', '.join(missing)}"))

    voucher = frappe.get_doc("Journal Entry Voucher", voucher_name)
    if voucher.status == "Submitted":
        frappe.throw(_("Cannot import into a Submitted voucher."))

    rows_imported = rows_skipped = 0
    errors = []

    for excel_row, vals in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
        if all(v is None or str(v).strip() == "" for v in vals):
            rows_skipped += 1
            continue

        row_errors = []
        data = {}

        for hdr, fieldname, required, dtype in _COLUMNS:
            idx   = col_index.get(hdr)
            raw_v = vals[idx] if idx is not None else None
            if raw_v is not None and str(raw_v).strip() == "":
                raw_v = None

            if required and raw_v is None:
                row_errors.append(f"'{hdr}' is required")
                continue
            if raw_v is None:
                data[fieldname] = None
                continue

            val = str(raw_v).strip()
            if dtype == "date":
                try:
                    data[fieldname] = (raw_v.strftime("%Y-%m-%d")
                                       if hasattr(raw_v, "strftime")
                                       else datetime.strptime(val, "%Y-%m-%d").strftime("%Y-%m-%d"))
                except ValueError:
                    row_errors.append(f"'{hdr}' must be YYYY-MM-DD (got: {val})")
            elif dtype == "float":
                try:
                    data[fieldname] = float(val)
                except ValueError:
                    row_errors.append(f"'{hdr}' must be a number (got: {val})")
            else:
                data[fieldname] = val

        # Business validation
        if data.get("account_type") and data["account_type"] not in _VALID_ACCT_TYPES:
            row_errors.append(f"Acct Type invalid: '{data['account_type']}'")
        if data.get("trans_effect") and data["trans_effect"] not in _VALID_TRANS_EFFECT:
            row_errors.append("Trans Effect must be Debit or Credit")
        if data.get("amount") is not None and flt(data.get("amount", 0)) <= 0:
            row_errors.append("Amount must be > 0")

        if row_errors:
            errors.append({"row": excel_row, "errors": row_errors,
                           "description": data.get("transaction_description", "")})
            rows_skipped += 1
            continue

        # Auto-resolve party name
        if data.get("account_type") and data.get("party"):
            data["party_name"] = _get_party_display_name(data["account_type"], data["party"])

        data.setdefault("exchange_rate", 1.0)
        data.setdefault("corresponding_effect", "Auto (Opposite)")

        voucher.append("accounts", data)
        rows_imported += 1

    if rows_imported > 0:
        voucher.save(ignore_permissions=False)
        frappe.db.commit()

    return {
        "rows_imported": rows_imported,
        "rows_skipped":  rows_skipped,
        "errors":        errors,
        "message":       (f"{rows_imported} row(s) imported."
                          + (f" {rows_skipped} skipped." if rows_skipped else "")),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_party_display_name(account_type: str, party: str) -> str:
    m = {
        "Supplier":   ("Supplier",  "supplier_name"),
        "Customer":   ("Customer",  "customer_name"),
        "Employee":   ("Employee",  "employee_name"),
        "Account GL": ("Account",   "account_name"),
    }
    entry = m.get(account_type)
    if not entry:
        return party
    return frappe.db.get_value(entry[0], party, entry[1]) or party
    