"""
universal_excel_export.api.excel_export
========================================
Whitelisted Frappe API that receives doctype metadata + row data from the
client and returns a base64-encoded, richly-styled .xlsx file.

Supports:
  • Automatic column-width fitting
  • Styled header row (navy background, white bold text, filter dropdowns)
  • Freeze pane on header row
  • Alternating row shading
  • Right-aligned numbers / currencies
  • Formatted dates, datetimes, booleans
  • Auto number-format detection per fieldtype
  • Sheet tab colour
  • Print-ready page setup (landscape, fit-to-width)
  • A "Meta" sheet with export timestamp, doctype, filters
"""

import base64
import io
import re
from datetime import datetime, date

import frappe
from frappe import _
from frappe.utils import now_datetime, get_site_name

# ── openpyxl imports ───────────────────────────────────────────────────────────
try:
    from openpyxl import Workbook
    from openpyxl.styles import (
        Font, PatternFill, Alignment, Border, Side, GradientFill,
    )
    from openpyxl.styles.numbers import FORMAT_DATE_DDMMYY, FORMAT_NUMBER_COMMA_SEPARATED1
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.table import Table, TableStyleInfo
    from openpyxl.worksheet.views import SheetView, Pane
    from openpyxl.worksheet.page import PageMargins
    from openpyxl.drawing.image import Image as XLImage
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


# ── Brand colours (hex without #) ─────────────────────────────────────────────
C_NAVY        = "1A2E4A"   # header background
C_AMBER       = "E8A020"   # accent / tab colour
C_EMERALD     = "2EA87E"   # alternate accent
C_ROW_ALT     = "F0F4FA"   # alternating row fill
C_ROW_NORM    = "FFFFFF"   # normal row fill
C_BORDER      = "C8D0DF"   # cell borders
C_HEADER_FONT = "FFFFFF"   # header text
C_SUBHEADER   = "E8EEF6"   # meta sheet header bg

# ── Number formats per Frappe fieldtype ────────────────────────────────────────
FIELDTYPE_FORMAT = {
    "Currency":  '#,##0.00',
    "Float":     '#,##0.####',
    "Int":       '#,##0',
    "Percent":   '0.00%',
    "Date":      'DD-MMM-YYYY',
    "Datetime":  'DD-MMM-YYYY HH:MM',
    "Time":      'HH:MM:SS',
    "Duration":  '#,##0',
    "Check":     '"Yes";"Yes";"No"',
}

# ── Field types that align right ───────────────────────────────────────────────
RIGHT_ALIGN_TYPES = {"Currency", "Float", "Int", "Percent", "Duration"}
CENTER_ALIGN_TYPES = {"Date", "Datetime", "Time", "Check"}


# ═══════════════════════════════════════════════════════════════════════════════
@frappe.whitelist()
def generate_excel(doctype, fields, data, include_header=True, freeze_header=True):
    """
    Parameters
    ----------
    doctype       : str   — Frappe DocType name
    fields        : list  — [{"fieldname":..., "label":..., "fieldtype":...}, ...]
    data          : list  — list of dicts (rows)
    include_header: bool
    freeze_header : bool

    Returns
    -------
    str — base64-encoded .xlsx bytes
    """
    if not HAS_OPENPYXL:
        frappe.throw(_("openpyxl is required. Install it with: pip install openpyxl"))

    # Deserialise if coming in as JSON strings (Frappe whitelist quirk)
    if isinstance(fields, str):
        import json
        fields = json.loads(fields)
    if isinstance(data, str):
        import json
        data = json.loads(data)

    fields = fields or []
    data   = data   or []

    wb = Workbook()

    # ── Main data sheet ───────────────────────────────────────────────────────
    ws = wb.active
    safe_sheet_name = _safe_sheet_name(doctype)
    ws.title = safe_sheet_name
    ws.sheet_properties.tabColor = C_AMBER

    _apply_page_setup(ws, doctype)

    col_count = len(fields)
    row_offset = 0

    if include_header:
        _write_header_row(ws, fields, row=1)
        row_offset = 1

    _write_data_rows(ws, fields, data, start_row=row_offset + 1)

    if include_header and freeze_header:
        ws.freeze_panes = ws.cell(row=2, column=1)

    # Auto-fit columns
    _autofit_columns(ws, fields, data, header_row=include_header)

    # Excel Table (ListObject) for filter dropdowns and banding
    if include_header and len(data) > 0:
        _apply_table(ws, col_count, len(data) + 1)  # +1 for header

    # ── Meta sheet ────────────────────────────────────────────────────────────
    ws_meta = wb.create_sheet("Export Info")
    ws_meta.sheet_properties.tabColor = C_NAVY
    _write_meta_sheet(ws_meta, doctype, fields, data)

    # ── Serialise ─────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


# ═══════════════════════════════════════════════════════════════════════════════
#  Internal helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _safe_sheet_name(name):
    """Trim and sanitise to valid Excel sheet name (max 31 chars)."""
    name = re.sub(r'[\\/*?\[\]:]', '_', name)
    return name[:31]


def _apply_page_setup(ws, doctype):
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToPage  = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.page_margins = PageMargins(left=0.5, right=0.5, top=0.75, bottom=0.75)
    ws.print_title_rows = "1:1"
    ws.oddHeader.center.text = f"&B{doctype}&B"
    ws.oddHeader.right.text  = "&D"
    ws.oddFooter.center.text = "Page &P of &N"


def _header_font():
    return Font(name="Calibri", bold=True, color=C_HEADER_FONT, size=10)

def _header_fill():
    return PatternFill("solid", fgColor=C_NAVY)

def _header_alignment():
    return Alignment(horizontal="center", vertical="center", wrap_text=True)

def _cell_border(thick=False):
    side = Side(style="thin" if not thick else "medium", color=C_BORDER)
    return Border(left=side, right=side, top=side, bottom=side)

def _alt_fill():
    return PatternFill("solid", fgColor=C_ROW_ALT)

def _norm_fill():
    return PatternFill("solid", fgColor=C_ROW_NORM)


def _write_header_row(ws, fields, row=1):
    ws.row_dimensions[row].height = 30
    for col_idx, field in enumerate(fields, start=1):
        cell = ws.cell(row=row, column=col_idx, value=field.get("label", field.get("fieldname", "")))
        cell.font      = _header_font()
        cell.fill      = _header_fill()
        cell.alignment = _header_alignment()
        cell.border    = _cell_border(thick=True)


def _coerce_value(raw, fieldtype):
    """
    Convert raw value (from frappe.client.get_list) into something
    Excel will render nicely.
    """
    if raw is None or raw == "":
        return None

    ft = fieldtype or "Data"

    # Boolean / Check
    if ft == "Check":
        return bool(int(raw)) if str(raw).isdigit() else bool(raw)

    # Numeric
    if ft in ("Currency", "Float", "Percent", "Duration"):
        try:
            v = float(raw)
            return v / 100 if ft == "Percent" else v
        except (ValueError, TypeError):
            return raw

    if ft == "Int":
        try:
            return int(raw)
        except (ValueError, TypeError):
            return raw

    # Dates
    if ft == "Date":
        if isinstance(raw, (date, datetime)):
            return raw
        try:
            return datetime.strptime(str(raw), "%Y-%m-%d").date()
        except Exception:
            return raw

    if ft == "Datetime":
        if isinstance(raw, datetime):
            return raw
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(str(raw), fmt)
            except Exception:
                continue
        return raw

    if ft == "Time":
        # Return as string; Excel will format via number format
        return str(raw)

    # Everything else: plain string
    return str(raw) if raw is not None else None


def _write_data_rows(ws, fields, data, start_row=2):
    data_font      = Font(name="Calibri", size=10)
    border         = _cell_border()

    for row_idx, record in enumerate(data, start=start_row):
        is_alt = (row_idx % 2 == 0)
        fill   = _alt_fill() if is_alt else _norm_fill()
        ws.row_dimensions[row_idx].height = 18

        for col_idx, field in enumerate(fields, start=1):
            fn       = field.get("fieldname", "")
            ft       = field.get("fieldtype", "Data")
            raw      = record.get(fn)
            value    = _coerce_value(raw, ft)

            cell         = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.font    = data_font
            cell.fill    = fill
            cell.border  = border

            # Number format
            if ft in FIELDTYPE_FORMAT:
                cell.number_format = FIELDTYPE_FORMAT[ft]

            # Alignment
            if ft in RIGHT_ALIGN_TYPES:
                cell.alignment = Alignment(horizontal="right", vertical="center")
            elif ft in CENTER_ALIGN_TYPES:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=False)


def _autofit_columns(ws, fields, data, header_row=True):
    """
    Estimate column widths from header label length and max value length.
    Caps at 50 characters; minimum 10.
    """
    for col_idx, field in enumerate(fields, start=1):
        label_len  = len(str(field.get("label", field.get("fieldname", "")) or ""))
        max_val    = label_len

        fn = field.get("fieldname", "")
        ft = field.get("fieldtype", "Data")

        for record in data:
            raw = record.get(fn)
            if raw is None:
                continue
            # Use formatted length hint
            if ft in ("Date", "Datetime"):
                max_val = max(max_val, 14)
            elif ft in ("Currency", "Float", "Int"):
                try:
                    max_val = max(max_val, len(f"{float(raw):,.2f}"))
                except Exception:
                    max_val = max(max_val, len(str(raw)))
            else:
                max_val = max(max_val, len(str(raw)[:80]))

        col_width  = min(max(max_val + 3, 10), 50)
        ws.column_dimensions[get_column_letter(col_idx)].width = col_width


def _apply_table(ws, col_count, total_rows):
    """
    Wrap data in an Excel Table so users get auto-filters, banding,
    and can sort/filter each column natively.
    """
    if col_count == 0 or total_rows < 2:
        return

    last_col  = get_column_letter(col_count)
    ref       = f"A1:{last_col}{total_rows}"

    table = Table(displayName="ExportTable", ref=ref)
    style = TableStyleInfo(
        name="TableStyleMedium2",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False,
    )
    table.tableStyleInfo = style
    # Suppress the default table banding so our fill wins in alternating rows
    ws.add_table(table)


def _write_meta_sheet(ws, doctype, fields, data):
    """
    A tidy 'Export Info' sheet with timestamp, record count, column list.
    """
    ws.column_dimensions["A"].width = 24
    ws.column_dimensions["B"].width = 48
    ws.sheet_view.showGridLines = False

    title_font  = Font(name="Calibri", bold=True, size=13, color=C_NAVY)
    label_font  = Font(name="Calibri", bold=True, size=10, color=C_NAVY)
    value_font  = Font(name="Calibri", size=10)
    hdr_fill    = PatternFill("solid", fgColor=C_SUBHEADER)
    accent_fill = PatternFill("solid", fgColor=C_AMBER)

    # Title bar
    ws.merge_cells("A1:B1")
    t = ws["A1"]
    t.value     = "📊 Universal Excel Export — Summary"
    t.font      = title_font
    t.fill      = PatternFill("solid", fgColor=C_NAVY)
    t.font      = Font(name="Calibri", bold=True, size=13, color="FFFFFF")
    t.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[1].height = 32

    rows = [
        ("DocType",        doctype),
        ("Exported by",    frappe.session.user),
        ("Site",           get_site_name(frappe.local.request.host) if frappe.local.request else frappe.local.site),
        ("Timestamp",      now_datetime().strftime("%d %b %Y  %H:%M:%S")),
        ("Total Records",  len(data)),
        ("Columns Exported", len(fields)),
    ]

    for i, (label, value) in enumerate(rows, start=2):
        lc = ws.cell(row=i, column=1, value=label)
        vc = ws.cell(row=i, column=2, value=value)
        lc.font  = label_font
        vc.font  = value_font
        lc.fill  = hdr_fill
        lc.alignment = Alignment(vertical="center", indent=1)
        vc.alignment = Alignment(vertical="center", indent=1)
        ws.row_dimensions[i].height = 20

    # Column list header
    sep_row = len(rows) + 3
    ws.merge_cells(f"A{sep_row}:B{sep_row}")
    h = ws[f"A{sep_row}"]
    h.value     = "Exported Columns"
    h.font      = Font(name="Calibri", bold=True, size=10, color="FFFFFF")
    h.fill      = PatternFill("solid", fgColor=C_NAVY)
    h.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[sep_row].height = 22

    # Column sub-header
    sh = sep_row + 1
    for col, hdr in [(1, "Label"), (2, "Field Name / Type")]:
        c = ws.cell(row=sh, column=col, value=hdr)
        c.font      = Font(name="Calibri", bold=True, size=9, color=C_NAVY)
        c.fill      = hdr_fill
        c.alignment = Alignment(vertical="center", indent=1)
    ws.row_dimensions[sh].height = 18

    alt = PatternFill("solid", fgColor="F8FAFD")
    for i, field in enumerate(fields, start=sh + 1):
        a = ws.cell(row=i, column=1, value=field.get("label", ""))
        b = ws.cell(row=i, column=2, value=f"{field.get('fieldname','')}  [{field.get('fieldtype','')}]")
        fill = alt if i % 2 == 0 else _norm_fill()
        for c in (a, b):
            c.font      = Font(name="Calibri", size=9)
            c.fill      = fill
            c.alignment = Alignment(vertical="center", indent=1)
        ws.row_dimensions[i].height = 16