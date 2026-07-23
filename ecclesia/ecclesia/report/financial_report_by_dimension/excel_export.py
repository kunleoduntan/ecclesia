#!/usr/bin/env python3
"""
ecclesia/ecclesia/utils/excel_export.py
Professional Excel Export with Full Styling
"""

import io
import json
import re
from datetime import datetime

import frappe
from frappe import _
from frappe.utils import flt, getdate

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side, NamedStyle
from openpyxl.utils import get_column_letter


# ─────────────────────────────────────────────────────────────────────────────
# WHITELISTED ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_excel_file(columns, data, filters, template_name):
    """Main entry point for Excel export"""
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
    """Main export function with professional formatting"""
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Financial Report"
    
    # Define styles
    _define_styles(wb)
    
    # Build the report
    current_row = add_report_header(ws, template, filters)
    current_row = add_column_headers(ws, columns, template, current_row)
    current_row = add_data_rows(ws, data, columns, template, current_row)
    format_columns(ws, columns)
    
    # Freeze panes at header row
    ws.freeze_panes = f"A{current_row - len(data)}"
    
    # Add print settings
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    ws.page_setup.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# STYLE DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

def _define_styles(wb):
    """Define reusable cell styles"""
    
    # Currency style (right-aligned with thousand separators)
    currency_style = NamedStyle(name="currency_style")
    currency_style.number_format = "#,##0.00"
    currency_style.alignment = Alignment(horizontal="right", vertical="center")
    wb.add_named_style(currency_style)
    
    # Percent style
    percent_style = NamedStyle(name="percent_style")
    percent_style.number_format = "0.00%"
    percent_style.alignment = Alignment(horizontal="right", vertical="center")
    wb.add_named_style(percent_style)
    
    # Header style
    header_style = NamedStyle(name="header_style")
    header_style.font = Font(bold=True, size=11)
    header_style.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    wb.add_named_style(header_style)
    
    # Total row style
    total_style = NamedStyle(name="total_style")
    total_style.font = Font(bold=True)
    total_style.fill = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")
    total_style.border = Border(
        top=Side(style="medium"),
        bottom=Side(style="double")
    )
    wb.add_named_style(total_style)


# ─────────────────────────────────────────────────────────────────────────────
# REPORT HEADER
# ─────────────────────────────────────────────────────────────────────────────

def add_report_header(ws, template, filters):
    """Add professional report header"""
    row = 1
    
    # Report Title
    ws.merge_cells(f"A{row}:H{row}")
    title_cell = ws.cell(row=row, column=1)
    title_cell.value = template.report_title or template.template_name
    title_cell.font = Font(name="Arial", size=18, bold=True, color="1a3b5c")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    row += 1
    
    # Company Info
    ws.merge_cells(f"A{row}:D{row}")
    company_cell = ws.cell(row=row, column=1)
    company_cell.value = f"Company: {filters.get('company', '')}"
    company_cell.font = Font(size=11, bold=True)
    row += 1
    
    # Period Info
    ws.merge_cells(f"A{row}:D{row}")
    period_cell = ws.cell(row=row, column=1)
    
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    if from_date and to_date:
        period_cell.value = f"Period: {from_date} to {to_date}"
    else:
        period_cell.value = f"Period: {filters.get('frequency', 'Monthly')} {filters.get('year', '')}"
    period_cell.font = Font(size=11)
    row += 1
    
    # Dimension Info
    dim_type = filters.get("dimension_type")
    if dim_type:
        ws.merge_cells(f"A{row}:D{row}")
        dim_cell = ws.cell(row=row, column=1)
        dim_cell.value = f"Dimension: {dim_type}"
        dim_cell.font = Font(size=11)
        row += 1
    
    # Generation timestamp
    ws.merge_cells(f"A{row}:D{row}")
    date_cell = ws.cell(row=row, column=1)
    date_cell.value = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    date_cell.font = Font(size=10, italic=True)
    row += 2
    
    return row


# ─────────────────────────────────────────────────────────────────────────────
# COLUMN HEADERS
# ─────────────────────────────────────────────────────────────────────────────

def add_column_headers(ws, columns, template, start_row):
    """Add formatted column headers"""
    
    # Header fill color
    header_color = (template.excel_header_row or "#D9E1F2").replace("#", "")
    header_fill = PatternFill(start_color=header_color, end_color=header_color, fill_type="solid")
    
    # Header border
    header_border = Border(
        left=Side(style="medium", color="000000"),
        right=Side(style="medium", color="000000"),
        top=Side(style="medium", color="000000"),
        bottom=Side(style="medium", color="000000"),
    )
    
    for i, col in enumerate(columns, 1):
        cell = ws.cell(row=start_row, column=i)
        cell.value = col.get("label", "")
        cell.font = Font(bold=True, size=11, color="1a3b5c")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.fill = header_fill
        cell.border = header_border
    
    ws.row_dimensions[start_row].height = 35
    return start_row + 1


# ─────────────────────────────────────────────────────────────────────────────
# DATA ROWS
# ─────────────────────────────────────────────────────────────────────────────

def add_data_rows(ws, data, columns, template, start_row):
    """Add formatted data rows"""
    
    def hex_to_rgb(hex_color):
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.replace("#", "").upper()
        if len(hex_color) == 6:
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return None
    
    def rgb_to_hex(rgb_str):
        """Convert rgb(r,g,b) to hex"""
        match = re.search(r"rgb\((\d+),\s*(\d+),\s*(\d+)\)", rgb_str)
        if match:
            return "{:02X}{:02X}{:02X}".format(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        return rgb_str.replace("#", "").upper()
    
    row = start_row
    
    for data_row in data:
        style_str = str(data_row.get("_style") or "").lower()
        
        # Parse styling
        bg_color = None
        if "background-color:" in style_str:
            color_match = re.search(r"background-color:\s*([^;]+)", style_str)
            if color_match:
                color_val = color_match.group(1).strip()
                if color_val.startswith("rgb"):
                    color_val = rgb_to_hex(color_val)
                else:
                    color_val = color_val.replace("#", "")
                if len(color_val) == 6:
                    bg_color = color_val
        elif "is_total" in style_str or "total_row" in style_str:
            bg_color = (template.excel_total_row_color or "#E7E6E6").replace("#", "")
        elif "subtotal" in style_str:
            bg_color = (template.excel_subtotal_color or "#F2F2F2").replace("#", "")
        
        is_bold = "bold" in style_str or "total" in style_str or "subtotal" in style_str
        
        # Determine borders
        thin_border = Border(
            left=Side(style="thin", color="CCCCCC"),
            right=Side(style="thin", color="CCCCCC"),
            top=Side(style="thin", color="CCCCCC"),
            bottom=Side(style="thin", color="CCCCCC"),
        )
        
        top_border = Border(
            left=Side(style="thin", color="CCCCCC"),
            right=Side(style="thin", color="CCCCCC"),
            top=Side(style="medium", color="000000"),
            bottom=Side(style="thin", color="CCCCCC"),
        )
        
        bottom_border = Border(
            left=Side(style="thin", color="CCCCCC"),
            right=Side(style="thin", color="CCCCCC"),
            top=Side(style="thin", color="CCCCCC"),
            bottom=Side(style="medium", color="000000"),
        )
        
        double_border = Border(
            left=Side(style="thin", color="CCCCCC"),
            right=Side(style="thin", color="CCCCCC"),
            top=Side(style="double", color="000000"),
            bottom=Side(style="double", color="000000"),
        )
        
        # Select border based on style
        if "double" in style_str:
            border = double_border
        elif "border-top" in style_str and "border-bottom" in style_str:
            border = top_bottom_double = Border(
                left=Side(style="thin", color="CCCCCC"),
                right=Side(style="thin", color="CCCCCC"),
                top=Side(style="medium", color="000000"),
                bottom=Side(style="medium", color="000000"),
            )
        elif "border-top" in style_str:
            border = top_border
        elif "border-bottom" in style_str:
            border = bottom_border
        else:
            border = thin_border
        
        # Create fill if background color specified
        fill = PatternFill(start_color=bg_color, end_color=bg_color, fill_type="solid") if bg_color else None
        
        # Set row height
        ws.row_dimensions[row].height = 20
        
        for col_idx, col in enumerate(columns, 1):
            fieldname = col.get("fieldname")
            value = data_row.get(fieldname)
            cell = ws.cell(row=row, column=col_idx)
            
            # Handle None values
            if value is None or value == "":
                cell.value = ""
            else:
                cell.value = value
            
            # Apply number formatting
            fieldtype = col.get("fieldtype")
            
            if fieldtype == "Currency" and value not in (None, ""):
                try:
                    num_val = flt(value)
                    cell.value = num_val
                    cell.number_format = '#,##0.00'
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                except:
                    pass
            elif fieldtype == "Percent" and value not in (None, ""):
                try:
                    # Convert percentage string to decimal if needed
                    if isinstance(value, str):
                        value = value.replace("%", "")
                    num_val = flt(value) / 100 if flt(value) > 1 else flt(value)
                    cell.value = num_val
                    cell.number_format = '0.00%'
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                except:
                    pass
            elif fieldname == "account_name":
                # Clean HTML from account name
                if isinstance(value, str):
                    clean_value = re.sub(r'<[^>]*>', '', value)
                    clean_value = clean_value.replace("&nbsp;", " ")
                    cell.value = clean_value
                    # Apply indentation
                    indent_count = clean_value.count("    ")
                    if indent_count > 0:
                        cell.alignment = Alignment(horizontal="left", vertical="center", indent=indent_count)
                    else:
                        cell.alignment = Alignment(horizontal="left", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="right" if col_idx > 1 else "left", vertical="center")
            
            # Apply font
            cell.font = Font(bold=is_bold)
            
            # Apply border
            cell.border = border
            
            # Apply fill
            if fill:
                cell.fill = fill
            
            # Apply negative number red color
            if fieldtype == "Currency" and value not in (None, ""):
                try:
                    if flt(value) < 0:
                        cell.font = Font(color="CC0000", bold=is_bold)
                except:
                    pass
            elif fieldtype == "Percent" and value not in (None, ""):
                try:
                    pct_val = flt(value) * 100 if flt(value) <= 1 else flt(value)
                    if pct_val > 20:
                        cell.fill = PatternFill(start_color="D4EDDA", end_color="D4EDDA", fill_type="solid")
                    elif pct_val < -20:
                        cell.fill = PatternFill(start_color="F8D7DA", end_color="F8D7DA", fill_type="solid")
                except:
                    pass
        
        row += 1
    
    return row


# ─────────────────────────────────────────────────────────────────────────────
# COLUMN FORMATTING
# ─────────────────────────────────────────────────────────────────────────────

def format_columns(ws, columns):
    """Auto-size columns for better readability"""
    
    for col_idx, col in enumerate(columns, 1):
        column_letter = get_column_letter(col_idx)
        
        # Set default width based on column type
        fieldtype = col.get("fieldtype")
        label = col.get("label", "")
        
        if fieldtype == "Data" and col_idx == 1:
            # Account column - wider
            ws.column_dimensions[column_letter].width = 45
        elif fieldtype == "Currency":
            ws.column_dimensions[column_letter].width = 16
        elif fieldtype == "Percent":
            ws.column_dimensions[column_letter].width = 12
        else:
            ws.column_dimensions[column_letter].width = 14
        
        # Auto-fit for better appearance (max 50, min 8)
        max_width = 0
        for row in range(1, ws.max_row + 1):
            cell = ws.cell(row=row, column=col_idx)
            if cell.value:
                try:
                    cell_len = len(str(cell.value))
                    if cell_len > max_width:
                        max_width = min(cell_len, 50)
                except:
                    pass
        
        if max_width > 8:
            ws.column_dimensions[column_letter].width = max(max_width + 2, ws.column_dimensions[column_letter].width)


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _make_filename(template, filters):
    """Generate filename for the export"""
    name = re.sub(r"[^\w]", "_", template.template_name)
    date = datetime.now().strftime("%Y%m%d")
    return f"{name}_{date}.xlsx"


def _save_to_frappe(buf, filename):
    """Save file to Frappe"""
    from frappe.utils.file_manager import save_file
    return save_file(
        fname=filename,
        content=buf.read(),
        dt="User",
        dn=frappe.session.user,
        is_private=1,
    )