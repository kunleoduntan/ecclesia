#!/usr/bin/env python3
"""
Excel Export with Beautiful Formatting for Financial Reports
Supports dynamic colors and borders from Financial Report Line doctype
"""

import frappe
from frappe import _
from frappe.utils import flt
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime
import io
import json
import re


def export_to_excel(columns, data, template, filters):
    """
    Export financial report to Excel with beautiful formatting
    """
    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Financial Report"
    
    # Add report header
    add_report_header(ws, template, filters)
    
    # Add column headers
    header_row = add_column_headers(ws, columns, template)
    
    # Add data rows
    add_data_rows(ws, data, columns, template, header_row)
    
    # Format columns
    format_columns(ws, columns, header_row)
    
    # Freeze panes
    ws.freeze_panes = f"A{header_row + 1}"
    
    # Return Excel file
    excel_file = io.BytesIO()
    wb.save(excel_file)
    excel_file.seek(0)
    
    return excel_file


def add_report_header(ws, template, filters):
    """
    Add report title and filters at the top
    """
    # Report title
    title = template.report_title or template.template_name
    ws.merge_cells('A1:F1')
    title_cell = ws['A1']
    title_cell.value = title
    title_cell.font = Font(name='Arial', size=16, bold=True)
    title_cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # Company and period info
    ws['A2'] = f"Company: {filters.get('company', '')}"
    ws['A3'] = f"Period: {filters.get('frequency', 'Monthly')} - Year {filters.get('year', '')}"
    ws['A4'] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    # Style info rows
    for row in [2, 3, 4]:
        ws[f'A{row}'].font = Font(name='Arial', size=10)
    
    # Add blank row
    return 5  # Starting row for headers


def add_column_headers(ws, columns, template):
    """
    Add column headers with formatting
    """
    start_row = 6
    
    # Define border style
    thin_border = Border(
        left=Side(style='thin', color='666666'),
        right=Side(style='thin', color='666666'),
        top=Side(style='thin', color='666666'),
        bottom=Side(style='thin', color='666666')
    )
    
    # Header background color
    header_color = template.excel_header_row.replace('#', '') if template.excel_header_row else 'D9E1F2'
    header_fill = PatternFill(start_color=header_color, end_color=header_color, fill_type='solid')
    
    # Add headers
    for col_idx, col in enumerate(columns, start=1):
        cell = ws.cell(row=start_row, column=col_idx)
        cell.value = col.get('label', '')
        cell.font = Font(name='Arial', size=11, bold=True, color='000000')
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.fill = header_fill
        cell.border = thin_border
    
    # Set row height
    ws.row_dimensions[start_row].height = 30
    
    return start_row


def add_data_rows(ws, data, columns, template, header_row):
    """
    Add data rows with conditional formatting and borders from doctype
    """
    # Define border styles
    thin_border = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='CCCCCC'),
        bottom=Side(style='thin', color='CCCCCC')
    )
    
    top_border = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='000000'),
        bottom=Side(style='thin', color='CCCCCC')
    )
    
    bottom_border = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='CCCCCC'),
        bottom=Side(style='thin', color='000000')
    )
    
    top_bottom_border = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='000000'),
        bottom=Side(style='thin', color='000000')
    )
    
    top_single_bottom_double = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='000000'),
        bottom=Side(style='double', color='000000')
    )
    
    top_bottom_double = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='double', color='000000'),
        bottom=Side(style='double', color='000000')
    )
    
    # Default colors
    total_color = template.excel_total_row_color.replace('#', '') if template.excel_total_row_color else 'E7E6E6'
    subtotal_color = template.excel_subtotal_color.replace('#', '') if template.excel_subtotal_color else 'F2F2F2'
    
    total_fill = PatternFill(start_color=total_color, end_color=total_color, fill_type='solid')
    subtotal_fill = PatternFill(start_color=subtotal_color, end_color=subtotal_color, fill_type='solid')
    
    # Number format
    decimal_places = template.decimal_places or 2
    if template.thousands_separator:
        number_format = f'#,##0.{"0" * decimal_places}'
    else:
        number_format = f'0.{"0" * decimal_places}'
    
    percentage_format = '0.00%'
    
    # Add data rows
    current_row = header_row + 1
    
    for row_data in data:
        # Parse style from _style field
        row_style = row_data.get('_style', '')
        
        # Extract custom background color from style (from row_color field)
        custom_bg_color = None
        if 'background-color:' in row_style:
            # Extract hex color
            match = re.search(r'background-color:\s*([#\w]+)', row_style)
            if match:
                custom_bg_color = match.group(1).replace('#', '')
        
        # Determine fill (priority: custom color > total > subtotal)
        if custom_bg_color:
            fill = PatternFill(start_color=custom_bg_color, end_color=custom_bg_color, fill_type='solid')
        elif 'Total' in row_data.get('account_name', '') or 'background-color: #e7e6e6' in row_style.lower():
            fill = total_fill
        elif 'subtotal' in row_style.lower() or 'background-color: #f2f2f2' in row_style.lower():
            fill = subtotal_fill
        else:
            fill = None
        
        # Determine if bold
        is_bold = 'bold' in row_style.lower()
        
        # Extract border style from _style
        border_to_apply = thin_border
        if 'border-top: 1px solid' in row_style and 'border-bottom: 3px double' in row_style:
            border_to_apply = top_single_bottom_double
        elif 'border-top: 3px double' in row_style and 'border-bottom: 3px double' in row_style:
            border_to_apply = top_bottom_double
        elif 'border-top: 1px solid' in row_style and 'border-bottom: 1px solid' in row_style:
            border_to_apply = top_bottom_border
        elif 'border-top: 1px solid' in row_style:
            border_to_apply = top_border
        elif 'border-bottom: 1px solid' in row_style or 'border-bottom: 3px double' in row_style:
            if 'border-bottom: 3px double' in row_style:
                border_to_apply = Border(
                    left=Side(style='thin', color='CCCCCC'),
                    right=Side(style='thin', color='CCCCCC'),
                    top=Side(style='thin', color='CCCCCC'),
                    bottom=Side(style='double', color='000000')
                )
            else:
                border_to_apply = bottom_border
        
        # Add cells
        for col_idx, col in enumerate(columns, start=1):
            cell = ws.cell(row=current_row, column=col_idx)
            fieldname = col.get('fieldname', '')
            value = row_data.get(fieldname)
            
            # Set value
            if value is not None:
                if col.get('fieldtype') == 'Currency':
                    cell.value = flt(value)
                    cell.number_format = number_format
                elif col.get('fieldtype') == 'Percent':
                    cell.value = flt(value) / 100 if value else None
                    cell.number_format = percentage_format
                else:
                    # Text field - strip HTML tags
                    cell.value = strip_html(str(value))
            
            # Apply styling
            if col_idx == 1:  # Account name column
                cell.alignment = Alignment(horizontal='left', vertical='center')
                if is_bold:
                    cell.font = Font(name='Arial', size=10, bold=True)
                else:
                    cell.font = Font(name='Arial', size=10)
            else:
                cell.alignment = Alignment(horizontal='right', vertical='center')
                
                # Color negative values red
                if col.get('fieldtype') == 'Currency' and value and flt(value) < 0:
                    cell.font = Font(name='Arial', size=10, color='FF0000')
                else:
                    if is_bold:
                        cell.font = Font(name='Arial', size=10, bold=True)
                    else:
                        cell.font = Font(name='Arial', size=10)
            
            # Apply fill
            if fill:
                cell.fill = fill
            
            # Apply border
            cell.border = border_to_apply
        
        current_row += 1


def format_columns(ws, columns, header_row):
    """
    Auto-size columns and set specific widths
    """
    # Set column widths
    for col_idx, col in enumerate(columns, start=1):
        col_letter = get_column_letter(col_idx)
        
        # Get specified width or auto-calculate
        width = col.get('width', 100)
        
        # Convert width to Excel column width (approximate)
        excel_width = width / 7  # Rough conversion
        
        # Set minimum and maximum widths
        if col_idx == 1:  # Account name column
            excel_width = max(excel_width, 30)
        else:
            excel_width = max(excel_width, 10)
            excel_width = min(excel_width, 50)
        
        ws.column_dimensions[col_letter].width = excel_width


def strip_html(text):
    """
    Strip HTML tags from text
    """
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)


# Integration with ERPNext export
@frappe.whitelist()
def download_excel(template_name, company, year, frequency='Monthly', show_budget=0, budget_plan=None):
    """
    Download Excel file directly via URL
    This method is called via window.open() from JavaScript
    """
    try:
        # Get the report
        from ecclesia.ecclesia.report.financial_report_template_based import financial_report_template_based
        
        # Build filters
        filters = {
            'template': template_name,
            'company': company,
            'year': int(year),
            'frequency': frequency,
            'show_budget': int(show_budget) if show_budget else 0,
            'budget_plan': budget_plan if budget_plan and budget_plan != 'null' else None
        }
        
        # Execute report to get columns and data
        columns, data, message, chart, report_summary = financial_report_template_based.execute(filters)
        
        # Get template
        template = frappe.get_doc("Financial Report Template", template_name)
        
        # Generate Excel
        excel_file = export_to_excel(columns, data, template, filters)
        
        # Create filename
        filename = f"{template.template_name}_{year}_{frequency}.xlsx"
        filename = filename.replace(' ', '_')
        
        # Build response
        frappe.response['filename'] = filename
        frappe.response['filecontent'] = excel_file.read()
        frappe.response['type'] = 'download'
        
    except Exception as e:
        frappe.log_error(f"Excel Export Error: {str(e)}", "Financial Report Excel Export")
        frappe.throw(_("Error generating Excel file: {0}").format(str(e)))


@frappe.whitelist()
def get_excel_file(columns, data, filters, template_name):
    """
    Alternative method - get Excel file with pre-computed data
    (Kept for backward compatibility)
    """
    try:
        # Parse JSON strings if needed (when called from JavaScript)
        if isinstance(columns, str):
            columns = json.loads(columns)
        if isinstance(data, str):
            data = json.loads(data)
        if isinstance(filters, str):
            filters = json.loads(filters)
        
        # Get template
        template = frappe.get_doc("Financial Report Template", template_name)
        
        # Generate Excel
        excel_file = export_to_excel(columns, data, template, filters)
        
        # Create filename
        filename = f"{template.template_name}_{filters.get('year', '')}_{filters.get('frequency', 'Monthly')}.xlsx"
        filename = filename.replace(' ', '_')
        
        # Set response
        frappe.response['filename'] = filename
        frappe.response['filecontent'] = excel_file.read()
        frappe.response['type'] = 'download'
        
    except Exception as e:
        frappe.log_error(f"Excel Export Error: {str(e)}", "Financial Report Excel Export")
        frappe.throw(_("Error generating Excel file: {0}").format(str(e)))