#!/usr/bin/env python3
"""
ecclesia/ecclesia/utils/excel_export.py
"""

import io
import json
import re
from datetime import datetime

import frappe
from frappe import _
from frappe.utils import flt

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


# ─────────────────────────────────────────────────────────────────────────────
# WHITELISTED ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_excel_file(columns, data, filters, template_name):

    if isinstance(columns, str):
        columns = json.loads(columns)
    if isinstance(data, str):
        data = json.loads(data)
    if isinstance(filters, str):
        filters = json.loads(filters)

    template = frappe.get_doc("Financial Report Template", template_name)
    buf = export_to_excel(columns, data, template, filters)
    fname = _make_filename(template, filters)
    return _save_to_frappe(buf, fname).file_url


# ─────────────────────────────────────────────────────────────────────────────
# CORE BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def export_to_excel(columns, data, template, filters):

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Financial Report"

    add_report_header(ws, template, filters)
    header_row = add_column_headers(ws, columns, template)
    add_data_rows(ws, data, columns, template, header_row)
    format_columns(ws, columns, header_row)

    ws.freeze_panes = f"A{header_row + 1}"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────

def add_report_header(ws, template, filters):

    ws.merge_cells("A1:F1")
    c = ws["A1"]
    c.value = template.report_title or template.template_name
    c.font = Font(name="Arial", size=16, bold=True)
    c.alignment = Alignment(horizontal="center", vertical="center")

    ws["A2"] = f"Company: {filters.get('company', '')}"
    ws["A3"] = f"Period: {filters.get('from_date') or filters.get('frequency')}"

    ws["A4"] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    for r in (2, 3, 4):
        ws[f"A{r}"].font = Font(size=10)


# ─────────────────────────────────────────────────────────────────────────────
# COLUMN HEADERS
# ─────────────────────────────────────────────────────────────────────────────

def add_column_headers(ws, columns, template):

    start_row = 6

    border = Border(
        left=Side(style="medium", color="000000"),
        right=Side(style="medium", color="000000"),
        top=Side(style="medium", color="000000"),
        bottom=Side(style="medium", color="000000"),
    )

    color = (template.excel_header_row or "#D9E1F2").replace("#", "")
    fill = PatternFill(start_color=color, end_color=color, fill_type="solid")

    for i, col in enumerate(columns, 1):
        cell = ws.cell(start_row, i)
        cell.value = col.get("label")
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.fill = fill
        cell.border = border

    ws.row_dimensions[start_row].height = 30
    return start_row


# ─────────────────────────────────────────────────────────────────────────────
# DATA ROWS
# ─────────────────────────────────────────────────────────────────────────────

def add_data_rows(ws, data, columns, template, header_row):

    def css_to_hex(val):
        if val.startswith("rgb"):
            nums = re.findall(r"\d+", val)
            return "{:02X}{:02X}{:02X}".format(int(nums[0]), int(nums[1]), int(nums[2]))
        return val.replace("#", "").upper()

    # Borders
    thin = Border(
        left=Side(style="thin", color="999999"),
        right=Side(style="thin", color="999999"),
        top=Side(style="thin", color="999999"),
        bottom=Side(style="thin", color="999999"),
    )

    top_bottom_double = Border(
        left=Side(style="thin", color="999999"),
        right=Side(style="thin", color="999999"),
        top=Side(style="double", color="000000"),
        bottom=Side(style="double", color="000000"),
    )

    current_row = header_row + 1

    for row in data:

        style = str(row.get("_style") or "").lower().replace(" ", "")

        fill = None
        m = re.search(r"background-color:([^;]+)", style)
        if m:
            color = css_to_hex(m.group(1))
            fill = PatternFill(start_color=color, end_color=color, fill_type="solid")

        is_bold = "bold" in style

        border = top_bottom_double if "double" in style else thin

        ws.row_dimensions[current_row].height = 18

        for i, col in enumerate(columns, 1):
            cell = ws.cell(current_row, i)

            value = row.get(col.get("fieldname"))
            cell.value = "" if value is None else value

            if col.get("fieldtype") == "Currency" and value not in (None, ""):
                cell.value = flt(value)
                cell.number_format = "#,##0.00"

            if i == 1:
                cell.alignment = Alignment(horizontal="left")
            else:
                cell.alignment = Alignment(horizontal="right")

            cell.font = Font(bold=is_bold)
            cell.border = border
            if fill:
                cell.fill = fill

        current_row += 1


# ─────────────────────────────────────────────────────────────────────────────
# COLUMN WIDTHS
# ─────────────────────────────────────────────────────────────────────────────

def format_columns(ws, columns, header_row):

    for i, col in enumerate(columns, 1):
        letter = get_column_letter(i)
        ws.column_dimensions[letter].width = max(col.get("width", 120) / 7, 12)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _make_filename(template, filters):

    name = re.sub(r"[^\w]", "_", template.template_name)
    return f"{name}.xlsx"


def _save_to_frappe(buf, filename):

    from frappe.utils.file_manager import save_file
    return save_file(
        fname=filename,
        content=buf.read(),
        dt="User",
        dn=frappe.session.user,
        is_private=1,
    )
