# ecclesia/ecclesia/doctype/bank_statement_upload/exporter.py
"""
Two exports:
  export_staged_rows — ALL staged rows with full AI coding (download for review)
  export_failed      — only Failed rows with failure reason (for correction & re-upload)
"""

import frappe
import os
from frappe.utils import get_site_path, now_datetime


# ================================================================== #
#  SHARED HELPERS                                                      #
# ================================================================== #

def _save_workbook(wb, filename: str, import_name: str) -> str:
    """Save workbook to private files and register in File doctype."""
    try:
        import openpyxl
    except ImportError:
        frappe.throw("openpyxl required: bench pip install openpyxl")

    priv_dir = os.path.join(get_site_path(), "private", "files")
    os.makedirs(priv_dir, exist_ok=True)
    path = os.path.join(priv_dir, filename)
    wb.save(path)

    # Insert File record WITHOUT attached_to_* to avoid comment-hook ImportError
    file_doc = frappe.get_doc({
        "doctype":   "File",
        "file_name": filename,
        "file_url":  f"/private/files/{filename}",
        "is_private": 1,
        "folder":    "Home/Attachments",
    })
    file_doc.insert(ignore_permissions=True)

    # Link in a second step — bypasses the comment hook
    frappe.db.set_value(
        "File", file_doc.name,
        {"attached_to_doctype": "Bank Statement Upload",
         "attached_to_name":    import_name}
    )
    frappe.db.commit()
    return file_doc.file_url


def _header_style():
    from openpyxl.styles import Font, PatternFill, Alignment
    return {
        "hdr_fill":  PatternFill("solid", fgColor="1F3864"),
        "hdr_font":  Font(bold=True, color="FFFFFF", size=10),
        "body_font": Font(size=10),
        "center":    Alignment(horizontal="center", vertical="center"),
        "left":      Alignment(horizontal="left",   vertical="center", wrap_text=True),
    }


def _status_fill(status: str):
    from openpyxl.styles import PatternFill
    return {
        "Ready":   PatternFill("solid", fgColor="E8F5E9"),   # light green
        "Review":  PatternFill("solid", fgColor="FFF9C4"),   # light yellow
        "Failed":  PatternFill("solid", fgColor="FFEBEE"),   # light red
        "Skipped": PatternFill("solid", fgColor="F5F5F5"),   # light grey
        "Created": PatternFill("solid", fgColor="E3F2FD"),   # light blue
    }.get(status, None)


# ================================================================== #
#  EXPORT STAGED ROWS  (full analysis download)                       #
# ================================================================== #

def export_staged_rows(items, import_name: str) -> str:
    """
    Export ALL staged rows with complete AI coding to Excel.
    Rows are colour-coded by status (Ready=green, Review=yellow, Failed=red).
    Includes a Legend sheet explaining columns and colours.
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        frappe.throw("openpyxl required: bench pip install openpyxl")

    st = _header_style()
    wb = openpyxl.Workbook()

    # ── Main sheet ────────────────────────────────────────────────── #
    ws = wb.active
    ws.title = "Analysed Transactions"

    HEADERS = [
        ("Date",              14),
        ("Bank Account",      22),
        ("Reference",         16),
        ("Pay Name",          28),
        ("Party Type",        14),
        ("Party ID",          20),
        ("Raw Description",   40),
        ("Cleaned",           30),
        ("Debit",             14),
        ("Credit",            14),
        ("Currency",          10),
        ("Local Amount",      16),
        ("Doc Type",          14),
        ("Trans Type",        22),
        ("Account (Debit)",   28),
        ("Account (Credit)",  28),
        ("Cost Center",       20),
        ("Cash Flow",         24),
        ("AI Confidence %",   14),
        ("Coding Method",     30),
        ("Anomaly",           10),
        ("Status",            12),
        ("Failure Reason",    40),
    ]

    # Header row
    ws.append([h for h, _ in HEADERS])
    for col_idx, (hdr, width) in enumerate(HEADERS, start=1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill      = st["hdr_fill"]
        cell.font      = st["hdr_font"]
        cell.alignment = st["center"]
        ws.column_dimensions[
            openpyxl.utils.get_column_letter(col_idx)
        ].width = width

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:W1"

    # Data rows
    for item in items:
        row_data = [
            str(item.transaction_date or ""),
            str(item.bank_account or ""),
            str(item.reference_no or ""),
            str(item.pay_name or ""),
            str(item.party_type or ""),
            str(item.party_id or ""),
            str(item.raw_narration or ""),
            str(item.cleaned_description or ""),
            float(item.debit_amount  or 0),
            float(item.credit_amount or 0),
            str(item.payment_currency or "NGN"),
            float(item.local_currency_amount or 0),
            str(item.doc_type or ""),
            str(item.trans_type or ""),
            str(item.account_to_debit  or ""),
            str(item.account_to_credit or ""),
            str(item.cost_center or ""),
            str(item.cashflow_type or ""),
            float(item.ai_confidence or 0),
            str(item.coding_method or ""),
            "Yes" if item.anomaly_flag else "",
            str(item.row_status or ""),
            str(item.failure_reason or ""),
        ]
        ws.append(row_data)

        # Colour-code row by status
        fill = _status_fill(item.row_status)
        if fill:
            for col_idx in range(1, len(HEADERS) + 1):
                cell = ws.cell(row=ws.max_row, column=col_idx)
                cell.fill      = fill
                cell.font      = st["body_font"]
                cell.alignment = (st["left"] if col_idx in (7, 8, 23)
                                  else st["center"])

    # ── Summary row ───────────────────────────────────────────────── #
    total = len(items)
    by_status = {}
    for item in items:
        s = item.row_status or "Unknown"
        by_status[s] = by_status.get(s, 0) + 1

    ws.append([])  # blank spacer
    summary_row = ws.max_row + 1
    ws.cell(row=summary_row, column=1, value="SUMMARY").font = Font(bold=True, size=10)
    ws.cell(row=summary_row, column=2, value=f"Total: {total}").font = Font(size=10)
    col = 3
    for status, count in by_status.items():
        ws.cell(row=summary_row, column=col, value=f"{status}: {count}").font = Font(size=10)
        col += 1

    # ── Legend sheet ──────────────────────────────────────────────── #
    leg = wb.create_sheet("Legend")
    leg.column_dimensions["A"].width = 20
    leg.column_dimensions["B"].width = 60

    leg_data = [
        ("COLOUR GUIDE", ""),
        ("Green row",    "Ready — AI confidence ≥ threshold, account coded, can create document"),
        ("Yellow row",   "Review — low confidence or missing field — check before creating"),
        ("Red row",      "Failed — could not create document, see Failure Reason column"),
        ("Grey row",     "Skipped — duplicate of a previously uploaded row"),
        ("Blue row",     "Created — document already created in ERPNext"),
        ("", ""),
        ("COLUMN GUIDE", ""),
        ("Pay Name",     "Universal payee/payer name extracted from narration"),
        ("Party Type",   "Auto-detected: Supplier / Customer / Employee / Member (blank = none matched)"),
        ("Party ID",     "ERPNext ID of matched party (e.g. SUP-0042, CUST-0018)"),
        ("Doc Type",     "Payments or Receipts — determined from debit/credit direction and party type"),
        ("Coding Method","How the account was determined: Alias / Party match / CoA rule / Payroll rule"),
        ("AI Confidence","0–100%. Rows below threshold go to Review status"),
        ("Anomaly",      "'Yes' = amount is statistically unusual for this payee (3σ from rolling mean)"),
    ]
    for i, (key, val) in enumerate(leg_data, start=1):
        leg.cell(row=i, column=1, value=key).font = Font(
            bold=(val == "" or key in ("COLOUR GUIDE", "COLUMN GUIDE")),
            size=10
        )
        leg.cell(row=i, column=2, value=val).font = Font(size=10)

    # Colour legend keys
    colour_map = {
        "Green row":  "E8F5E9",
        "Yellow row": "FFF9C4",
        "Red row":    "FFEBEE",
        "Grey row":   "F5F5F5",
        "Blue row":   "E3F2FD",
    }
    for i, (key, _) in enumerate(leg_data, start=1):
        if key in colour_map:
            leg.cell(row=i, column=1).fill = PatternFill("solid", fgColor=colour_map[key])

    timestamp = now_datetime().strftime("%Y%m%d_%H%M%S")
    filename  = f"BSU_Analysed_{import_name}_{timestamp}.xlsx"
    return _save_workbook(wb, filename, import_name)


# ================================================================== #
#  EXPORT FAILED ROWS  (for correction and re-upload)                 #
# ================================================================== #

def export_failed(failed_items: list, import_name: str) -> str:
    """
    Export only Failed rows with failure reason.
    Format matches the original upload template so users can correct and re-upload.
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        frappe.throw("openpyxl required: bench pip install openpyxl")

    st = _header_style()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Failed Rows"

    ERR_FILL = PatternFill("solid", fgColor="FFEBEE")
    ERR_HDR  = PatternFill("solid", fgColor="C00000")

    HEADERS = [
        ("Date",             14),
        ("Description",      40),
        ("Reference",        16),
        ("Debit",            14),
        ("Credit",           14),
        ("Bank Account",     22),
        ("Pay Name",         28),
        ("Party Type",       14),
        ("Party ID",         20),
        ("Account (Debit)",  28),
        ("Failure Reason",   50),
    ]

    ws.append([h for h, _ in HEADERS])
    for col_idx, (hdr, width) in enumerate(HEADERS, start=1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill      = ERR_HDR if hdr == "Failure Reason" else st["hdr_fill"]
        cell.font      = st["hdr_font"]
        cell.alignment = st["center"]
        ws.column_dimensions[
            openpyxl.utils.get_column_letter(col_idx)
        ].width = width

    ws.freeze_panes = "A2"

    for item in failed_items:
        ws.append([
            str(item.transaction_date or ""),
            str(item.raw_narration or ""),
            str(item.reference_no or ""),
            float(item.debit_amount  or 0),
            float(item.credit_amount or 0),
            str(item.bank_account or ""),
            str(item.pay_name or ""),
            str(item.party_type or ""),
            str(item.party_id or ""),
            str(item.account_to_debit or ""),
            str(item.failure_reason or ""),
        ])
        for col_idx in range(1, len(HEADERS) + 1):
            cell = ws.cell(row=ws.max_row, column=col_idx)
            cell.fill      = ERR_FILL
            cell.font      = Font(size=10)
            cell.alignment = (st["left"] if col_idx in (2, 11) else st["center"])

    # Instructions sheet
    ws2 = wb.create_sheet("How to Fix")
    ws2.column_dimensions["A"].width = 35
    ws2.column_dimensions["B"].width = 60
    for row in [
        ["Failure Reason", "How to Fix"],
        ["Missing cost center",      "Set Cost Center in bulk recode before creating documents"],
        ["Bank account not resolved","Fix Bank Account name to match exactly in ERPNext"],
        ["Zero amount",              "Remove the row or correct Debit/Credit in original file"],
        ["Closed accounting period", "Open the period in ERPNext → Accounting Period"],
        ["FX rate not found",        "Add Currency Exchange rate for that date in ERPNext"],
    ]:
        ws2.append(row)
    ws2["A1"].font = Font(bold=True, size=10)
    ws2["B1"].font = Font(bold=True, size=10)

    timestamp = now_datetime().strftime("%Y%m%d_%H%M%S")
    filename  = f"BSU_Failed_{import_name}_{timestamp}.xlsx"
    return _save_workbook(wb, filename, import_name)