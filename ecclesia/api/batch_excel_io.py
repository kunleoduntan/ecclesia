# Copyright (c) 2026, Kunle Oduntan and contributors
"""
Batch Excel I/O  —  ecclesia/api/batch_excel_io.py
===================================================
Column-spec driven template / export / import, the same behaviour Bank
Transaction Processor has, for ANY document with one child table.

A column spec is a tuple:  (header, fieldname, required, dtype, extra)

    dtype : "str" | "float" | "int" | "date" | "check"
    extra : dict, optional keys
              link    -> DocType that the value must exist in
              options -> list of allowed values (case-insensitive match)
              accept  -> extra spellings that are accepted on import but not
                         advertised in the template (e.g. legacy aliases)
              width   -> column width
              note    -> text shown in the Instructions sheet
              example -> value written to the template's sample row

Round-trip rule: an exported file can be re-imported unchanged.  Export adds
read-only "status" columns after the importable ones; import ignores them.
"""

import base64
import csv
import io
from datetime import date, datetime

import frappe
from frappe import _
from frappe.utils import flt, getdate


# ─────────────────────────────────────────────────────────────────────────────
# Workbook builders
# ─────────────────────────────────────────────────────────────────────────────

def _openpyxl():
    try:
        import openpyxl  # noqa
        return openpyxl
    except ImportError:
        frappe.throw(_("openpyxl is not installed on this bench."))


def build_workbook(sheet_title, columns, rows=None, status_columns=None,
                   info=None, template=False):
    """
    rows            list of dicts keyed by fieldname (and status fieldnames)
    status_columns  [(header, fieldname, width)]  read-only, export only
    info            [(label, value)] for the 'Export Info' sheet
    template        True -> one grey example row + 'Instructions' sheet
    Returns {"filename_hint", "file_content"(base64)}.
    """
    openpyxl = _openpyxl()
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    status_columns = status_columns or []
    rows = rows or []

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_title

    thin = Side(style="thin", color="AAAAAA")
    thick = Side(style="medium", color="1F4E79")
    cell_border = Border(left=thin, right=thin, top=thin, bottom=thin)
    head_border = Border(left=thick, right=thick, top=thick, bottom=thick)
    REQ = PatternFill("solid", start_color="1F4E79")
    OPT = PatternFill("solid", start_color="2E75B6")
    STAT = PatternFill("solid", start_color="6C757D")
    DONE = PatternFill("solid", start_color="D4EDDA")
    ALT = PatternFill("solid", start_color="EBF3FB")
    SAMPLE = PatternFill("solid", start_color="F2F2F2")
    white_b = Font(name="Arial", bold=True, color="FFFFFF", size=10)
    white_n = Font(name="Arial", color="FFFFFF", size=10)
    base = Font(name="Arial", size=10)
    sample_font = Font(name="Arial", size=10, italic=True, color="888888")
    centre = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left = Alignment(horizontal="left", vertical="center")

    ws.row_dimensions[1].height = 40
    for ci, (hdr, _fn, req, _dt, extra) in enumerate(columns, 1):
        c = ws.cell(row=1, column=ci, value=hdr)
        c.font = white_b if req else white_n
        c.fill = REQ if req else OPT
        c.alignment = centre
        c.border = head_border
        ws.column_dimensions[get_column_letter(ci)].width = (extra or {}).get("width", 18)
    if not template:
        for j, (hdr, _fn, width) in enumerate(status_columns, len(columns) + 1):
            c = ws.cell(row=1, column=j, value=hdr)
            c.font = white_n
            c.fill = STAT
            c.alignment = centre
            c.border = head_border
            ws.column_dimensions[get_column_letter(j)].width = width or 16

    if template:
        for ci, (_h, _fn, _r, dtype, extra) in enumerate(columns, 1):
            v = (extra or {}).get("example")
            c = ws.cell(row=2, column=ci, value=v)
            c.font = sample_font
            c.fill = SAMPLE
            c.border = cell_border
            c.alignment = left
    else:
        for ri, rec in enumerate(rows, 2):
            done = bool(rec.get("_done"))
            for ci, (_h, fn, _r, dtype, _e) in enumerate(columns, 1):
                v = rec.get(fn)
                if dtype == "date":
                    v = str(v) if v else ""
                elif dtype == "check":
                    v = 1 if v else 0
                elif dtype in ("float", "int") and v in (None, ""):
                    v = None
                c = ws.cell(row=ri, column=ci, value=v)
                c.font = base
                c.fill = DONE if done else (ALT if ri % 2 == 0 else PatternFill(fill_type=None))
                c.border = cell_border
                c.alignment = left
                if dtype == "float":
                    c.number_format = "#,##0.00"
            for j, (_h, fn, _w) in enumerate(status_columns, len(columns) + 1):
                c = ws.cell(row=ri, column=j, value=rec.get(fn))
                c.font = base
                c.fill = DONE if done else PatternFill(fill_type=None)
                c.border = cell_border
                c.alignment = left
    ws.freeze_panes = "A2"

    if template:
        wi = wb.create_sheet("Instructions")
        wi.column_dimensions["A"].width = 24
        wi.column_dimensions["B"].width = 12
        wi.column_dimensions["C"].width = 12
        wi.column_dimensions["D"].width = 80
        bold = Font(name="Arial", bold=True, size=10)
        for j, h in enumerate(("Column", "Required", "Type", "Notes / allowed values"), 1):
            wi.cell(row=1, column=j, value=h).font = bold
        for i, (hdr, _fn, req, dtype, extra) in enumerate(columns, 2):
            extra = extra or {}
            note = extra.get("note", "")
            if extra.get("options"):
                note = (note + " " if note else "") + "One of: " + ", ".join(extra["options"])
            if extra.get("link"):
                note = (note + " " if note else "") + f"Must be an existing {extra['link']}."
            if dtype == "date":
                note = (note + " " if note else "") + "Format YYYY-MM-DD."
            wi.cell(row=i, column=1, value=hdr.replace("*", ""))
            wi.cell(row=i, column=2, value="Yes" if req else "No")
            wi.cell(row=i, column=3, value=dtype)
            wi.cell(row=i, column=4, value=note)
        wi.cell(row=len(columns) + 3, column=1,
                value="Delete the grey example row before importing. Keep headers exactly as they are.")
    elif info:
        wi = wb.create_sheet("Export Info")
        wi.column_dimensions["A"].width = 24
        wi.column_dimensions["B"].width = 44
        for r, (lbl, val) in enumerate(info, 1):
            wi.cell(row=r, column=1, value=lbl).font = Font(name="Arial", bold=True, size=10)
            wi.cell(row=r, column=2, value=val).font = Font(name="Arial", size=10)

    buf = io.BytesIO()
    wb.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


# ─────────────────────────────────────────────────────────────────────────────
# Parser
# ─────────────────────────────────────────────────────────────────────────────

def _grid_from_file(raw, filename, sheet_title):
    """-> list of rows (each a list of cell values); first row = headers."""
    name = (filename or "").lower()
    if name.endswith(".csv"):
        text = raw.decode("utf-8-sig", errors="replace")
        return [list(r) for r in csv.reader(io.StringIO(text))]
    openpyxl = _openpyxl()
    try:
        wb = openpyxl.load_workbook(io.BytesIO(raw), data_only=True)
    except Exception as e:
        frappe.throw(_("Cannot open Excel file: {0}").format(e))
    ws = wb[sheet_title] if sheet_title in wb.sheetnames else wb.active
    return [list(r) for r in ws.iter_rows(values_only=True)]


def _coerce(raw_v, dtype):
    """-> (value, error_or_None)"""
    if isinstance(raw_v, str):
        raw_v = raw_v.strip()
    if raw_v is None or raw_v == "":
        return None, None
    try:
        if dtype == "date":
            if isinstance(raw_v, (datetime, date)):
                return getdate(raw_v).strftime("%Y-%m-%d"), None
            return getdate(str(raw_v)).strftime("%Y-%m-%d"), None
        if dtype == "float":
            return float(str(raw_v).replace(",", "")), None
        if dtype == "int":
            return int(float(str(raw_v).replace(",", ""))), None
        if dtype == "check":
            return (1 if str(raw_v).strip().lower() in ("1", "1.0", "yes", "y", "true") else 0), None
        return str(raw_v), None
    except Exception:
        return None, {"date": "must be YYYY-MM-DD", "float": "must be a number",
                      "int": "must be a whole number"}.get(dtype, "invalid value")


def parse_rows(file_content_b64, filename, sheet_title, columns, describe_field="remark"):
    """
    Returns (records, errors, skipped).
      records : list of dicts keyed by fieldname (ready for doc.append after
                popping the helper key "_excel_row", the sheet row number)
      errors  : [{"row": n, "description": ..., "errors": [..]}]
    Header matching is by name, case/spacing-insensitive, so column ORDER does
    not matter and optional columns may be missing.  Missing REQUIRED columns
    abort the import with a clear message.
    """
    try:
        raw = base64.b64decode(file_content_b64)
    except Exception:
        frappe.throw(_("Invalid file encoding."))

    grid = _grid_from_file(raw, filename, sheet_title)
    if not grid:
        frappe.throw(_("The file is empty."))

    def key(h):
        return "".join(str(h or "").replace("*", "").split()).lower()

    header = {key(h): i for i, h in enumerate(grid[0]) if h not in (None, "")}
    missing = [h for h, _f, req, _d, _e in columns if req and key(h) not in header]
    if missing:
        frappe.throw(_("Missing required column(s): {0}").format(", ".join(missing)))

    records, errors, skipped = [], [], 0
    for excel_row, vals in enumerate(grid[1:], 2):
        if all(v is None or str(v).strip() == "" for v in vals):
            skipped += 1
            continue
        rec, row_errors = {}, []
        for hdr, fn, req, dtype, extra in columns:
            idx = header.get(key(hdr))
            raw_v = vals[idx] if idx is not None and idx < len(vals) else None
            val, err = _coerce(raw_v, dtype)
            label = hdr.replace("*", "")
            if err:
                row_errors.append(f"'{label}' {err}")
                continue
            if val is None:
                if req:
                    row_errors.append(f"'{label}' is required")
                rec[fn] = None
                continue
            extra = extra or {}
            if extra.get("options"):
                valid = list(extra["options"]) + list(extra.get("accept") or [])
                match = {o.lower(): o for o in valid}.get(str(val).lower())
                if not match:
                    row_errors.append(f"'{label}' must be one of: {', '.join(extra['options'])}")
                    continue
                val = match
            if extra.get("link") and not frappe.db.exists(extra["link"], val):
                row_errors.append(f"'{label}': {extra['link']} '{val}' does not exist")
                continue
            rec[fn] = val
        if row_errors:
            errors.append({"row": excel_row, "errors": row_errors,
                           "description": rec.get(describe_field) or ""})
            skipped += 1
            continue
        rec["_excel_row"] = excel_row
        records.append(rec)
    return records, errors, skipped


def import_result(imported, skipped, errors):
    return {
        "rows_imported": imported,
        "rows_skipped": skipped,
        "errors": errors,
        "message": f"{imported} row(s) imported." + (f" {skipped} skipped." if skipped else ""),
    }
