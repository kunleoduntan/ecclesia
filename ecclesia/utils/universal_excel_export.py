# universal_excel_export.py
# Place this in: your_app/your_app/utils/universal_excel_export.py
# Or inside any existing doctype's controller file.
#
# Exposes ONE whitelisted endpoint:
#   frappe.call("your_app.utils.universal_excel_export.universal_export_excel", {...})
#
# The JS companion (universal_listview_download.js) calls this automatically
# from every list view toolbar button.

import frappe
from frappe import _
from frappe.utils import today, cstr
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import json
import io


# ─── Colour palette ──────────────────────────────────────────────────────────
HEADER_BG   = "3730A3"   # indigo
HEADER_FG   = "FFFFFF"
TITLE_FG    = "3730A3"
SUBTITLE_FG = "64748B"
ALT_ROW_BG  = "F1F5F9"   # slate-100
SUMMARY_BG  = "FEF3C7"   # amber-100
BORDER_CLR  = "D1D5DB"


# ─── Field-type helpers ───────────────────────────────────────────────────────
# Fields that are rarely useful in a flat export
_SKIP_FIELDTYPES = {
    "Section Break", "Column Break", "Tab Break",
    "HTML", "HTML Editor", "Markdown Editor",
    "Button", "Image", "Fold", "Heading",
    "Table", "Table MultiSelect",
}

# Fields that exist on every doctype – include only a useful subset
_ALWAYS_INCLUDE = {"name", "creation", "modified", "owner", "docstatus"}


def _get_meta_fields(doctype: str) -> list[dict]:
    """
    Return an ordered list of {fieldname, label, fieldtype} dicts
    for all exportable fields in *doctype*, auto-discovered from Frappe meta.
    Standard fields (name, creation …) are appended at the end.
    """
    meta = frappe.get_meta(doctype)

    exportable = []
    for df in meta.fields:
        if df.fieldtype in _SKIP_FIELDTYPES:
            continue
        if df.hidden:
            continue
        exportable.append({
            "fieldname": df.fieldname,
            "label":     df.label or df.fieldname.replace("_", " ").title(),
            "fieldtype": df.fieldtype,
        })

    # Append a small set of useful standard fields
    std_labels = {
        "name":      "ID",
        "docstatus": "Status",
        "creation":  "Created On",
        "modified":  "Last Modified",
        "owner":     "Created By",
    }
    for fn, lbl in std_labels.items():
        exportable.append({"fieldname": fn, "label": lbl, "fieldtype": "Data"})

    return exportable


def _docstatus_label(val) -> str:
    return {0: "Draft", 1: "Submitted", 2: "Cancelled"}.get(val, cstr(val))


def _cell_value(raw, fieldtype: str):
    """Coerce a raw DB value to something Excel-friendly."""
    if raw is None:
        return ""
    if fieldtype == "Check":
        return "Yes" if raw else "No"
    if fieldtype in ("Date", "Datetime", "Time"):
        return cstr(raw)
    return raw


# ─── Styling helpers ──────────────────────────────────────────────────────────
def _thin_border():
    s = Side(style="thin", color=BORDER_CLR)
    return Border(left=s, right=s, top=s, bottom=s)


def _header_style():
    return (
        Font(name="Calibri", size=11, bold=True, color=HEADER_FG),
        PatternFill(start_color=HEADER_BG, end_color=HEADER_BG, fill_type="solid"),
        Alignment(horizontal="center", vertical="center"),
    )


def _guess_col_width(fieldtype: str, label: str) -> float:
    """Return a sensible default column width based on field type."""
    widths = {
        "Date":       12,
        "Datetime":   20,
        "Time":       10,
        "Int":         8,
        "Float":      12,
        "Currency":   14,
        "Percent":    10,
        "Check":       8,
        "Small Text": 30,
        "Long Text":  40,
        "Text":       30,
        "Text Editor":35,
        "Select":     16,
        "Link":       20,
    }
    return max(widths.get(fieldtype, 18), len(label) + 4)


# ─── Main export function ─────────────────────────────────────────────────────
@frappe.whitelist()
def universal_export_excel():
    """
    Generic Excel export for any Frappe DocType.

    Query-string / form-dict parameters
    ------------------------------------
    doctype  : str   – required, e.g. "Sales Invoice"
    filters  : JSON  – optional Frappe filter dict or list
    fields   : JSON  – optional list of fieldnames to include;
                       when omitted every exportable field is used
    order_by : str   – optional, e.g. "creation desc"
    title    : str   – optional sheet / file title override
    page_length : int – default 10 000; hard-capped at 100 000
    """
    fd = frappe.form_dict

    # ── Inputs ────────────────────────────────────────────────────────────────
    doctype = fd.get("doctype")
    if not doctype:
        frappe.throw(_("doctype is required"))

    # Permission check
    if not frappe.has_permission(doctype, "export"):
        frappe.throw(_("No export permission for {0}").format(doctype), frappe.PermissionError)

    filters = fd.get("filters", {})
    if isinstance(filters, str):
        filters = json.loads(filters) or {}

    requested_fields = fd.get("fields")
    if isinstance(requested_fields, str):
        requested_fields = json.loads(requested_fields)

    order_by    = fd.get("order_by", "modified desc")
    file_title  = fd.get("title") or doctype.replace(" ", "_")
    page_length = min(int(fd.get("page_length", 10000)), 100000)

    # ── Discover fields ───────────────────────────────────────────────────────
    all_meta_fields = _get_meta_fields(doctype)           # [{fieldname, label, fieldtype}]
    meta_index = {f["fieldname"]: f for f in all_meta_fields}

    if requested_fields:
        # Keep only valid fieldnames, preserve caller's order
        columns = [meta_index[fn] for fn in requested_fields if fn in meta_index]
    else:
        columns = all_meta_fields

    fieldnames = [c["fieldname"] for c in columns]

    # ── Fetch data ────────────────────────────────────────────────────────────
    records = frappe.get_all(
        doctype,
        filters=filters,
        fields=fieldnames,
        order_by=order_by,
        limit=page_length,
    )

    # ── Build workbook ────────────────────────────────────────────────────────
    wb = Workbook()
    ws = wb.active
    ws.title = file_title[:31]          # Excel sheet-name limit

    border   = _thin_border()
    hdr_font, hdr_fill, hdr_align = _header_style()
    center   = Alignment(horizontal="center", vertical="center")
    left     = Alignment(horizontal="left",   vertical="center")
    title_font    = Font(name="Calibri", size=14, bold=True, color=TITLE_FG)
    subtitle_font = Font(name="Calibri", size=10, color=SUBTITLE_FG)
    alt_fill      = PatternFill(start_color=ALT_ROW_BG, end_color=ALT_ROW_BG, fill_type="solid")
    summary_fill  = PatternFill(start_color=SUMMARY_BG, end_color=SUMMARY_BG, fill_type="solid")

    num_cols = len(columns)
    last_col = get_column_letter(num_cols)

    # Row 1 – Title
    ws.merge_cells(f"A1:{last_col}1")
    ws["A1"] = file_title.replace("_", " ").upper()
    ws["A1"].font      = title_font
    ws["A1"].alignment = center
    ws.row_dimensions[1].height = 32

    # Row 2 – Subtitle
    ws.merge_cells(f"A2:{last_col}2")
    ws["A2"] = (
        f"Exported on {frappe.utils.formatdate(today())}  |  "
        f"{len(records)} record{'s' if len(records) != 1 else ''}  |  "
        f"Filters: {json.dumps(filters) if filters else 'None'}"
    )
    ws["A2"].font      = subtitle_font
    ws["A2"].alignment = center
    ws.row_dimensions[2].height = 18

    # Row 3 – blank spacer
    ws.row_dimensions[3].height = 6

    # Row 4 – Column headers
    HEADER_ROW = 4
    for col_idx, col in enumerate(columns, 1):
        cell = ws.cell(row=HEADER_ROW, column=col_idx, value=col["label"])
        cell.font      = hdr_font
        cell.fill      = hdr_fill
        cell.alignment = hdr_align
        cell.border    = border
    ws.row_dimensions[HEADER_ROW].height = 24

    # Set column widths
    for col_idx, col in enumerate(columns, 1):
        letter = get_column_letter(col_idx)
        ws.column_dimensions[letter].width = _guess_col_width(col["fieldtype"], col["label"])

    # Rows 5+ – Data
    for row_offset, rec in enumerate(records):
        row_num = HEADER_ROW + 1 + row_offset
        row_fill = alt_fill if row_offset % 2 == 1 else None

        for col_idx, col in enumerate(columns, 1):
            raw = rec.get(col["fieldname"])

            # Special rendering
            if col["fieldname"] == "docstatus":
                value = _docstatus_label(raw)
            else:
                value = _cell_value(raw, col["fieldtype"])

            cell = ws.cell(row=row_num, column=col_idx, value=value)
            cell.border    = border
            cell.font      = Font(name="Calibri", size=10)
            cell.alignment = (
                left if col["fieldtype"] in ("Data", "Link", "Small Text", "Text", "Long Text",
                                              "Text Editor", "Select", "Dynamic Link")
                else center
            )
            if row_fill:
                cell.fill = row_fill

        ws.row_dimensions[row_num].height = 20

    # Summary row
    if records:
        summary_row = HEADER_ROW + len(records) + 1
        ws.merge_cells(f"A{summary_row}:{last_col}{summary_row}")
        summary_cell = ws.cell(
            row=summary_row, column=1,
            value=f"Total records: {len(records)}"
        )
        summary_cell.font      = Font(name="Calibri", size=10, bold=True, color=TITLE_FG)
        summary_cell.fill      = summary_fill
        summary_cell.alignment = center
        ws.row_dimensions[summary_row].height = 22

    # Freeze header row, enable auto-filter
    ws.freeze_panes = f"A{HEADER_ROW + 1}"
    ws.auto_filter.ref = f"A{HEADER_ROW}:{last_col}{HEADER_ROW + len(records)}"

    # ── Stream response ───────────────────────────────────────────────────────
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    safe_title = file_title.replace(" ", "_").replace("/", "-")
    frappe.response["filename"]    = f"{safe_title}_{today()}.xlsx"
    frappe.response["filecontent"] = output.read()
    frappe.response["type"]        = "binary"