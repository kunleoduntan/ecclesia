# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, today
import json
from datetime import datetime
import io

def execute(filters=None):
    if not filters:
        filters = {}
    
    # Validate required filters
    if not filters.get("company"):
        frappe.throw(_("Company is required"))
    if not filters.get("as_at_date"):
        filters["as_at_date"] = today()
    
    # Get company default currency
    company_currency = get_company_currency(filters.get("company"))
    filters["currency"] = company_currency
    
    columns = get_columns(company_currency)
    data = get_data(filters)
    summary = get_report_summary(data, filters)
    
    return columns, data, None, None, summary


def get_company_currency(company):
    """Get default currency from Company doctype"""
    currency = frappe.db.get_value("Company", company, "default_currency")
    return currency or "INR"


def get_columns(currency):
    """Define report columns for Trial Balance with currency"""
    return [
        {
            "label": _("Account Code"),
            "fieldname": "account_code",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Account Name"),
            "fieldname": "account_name",
            "fieldtype": "Data",
            "width": 350
        },
        {
            "label": _("Account Type"),
            "fieldname": "account_type",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _(f"Debit ({currency})"),
            "fieldname": "debit",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 180
        },
        {
            "label": _(f"Credit ({currency})"),
            "fieldname": "credit",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 180
        },
        {
            "label": _(f"Balance ({currency})"),
            "fieldname": "balance",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 180
        }
    ]


def get_data(filters):
    """Fetch trial balance data with proper grouping by account type"""
    as_at_date = getdate(filters.get("as_at_date"))
    company = filters.get("company")
    include_zero = filters.get("include_zero_balance", 0)
    
    # Main query to get account balances
    data = frappe.db.sql("""
        SELECT
            acc.account_number AS account_code,
            acc.account_name,
            acc.root_type AS account_type,
            acc.parent_account,
            COALESCE(SUM(gle.debit_in_account_currency), 0) AS debit,
            COALESCE(SUM(gle.credit_in_account_currency), 0) AS credit,
            COALESCE(SUM(gle.debit_in_account_currency - gle.credit_in_account_currency), 0) AS balance
        FROM `tabAccount` acc
        LEFT JOIN `tabGL Entry` gle 
            ON gle.account = acc.name 
            AND gle.posting_date <= %(as_at_date)s
            AND gle.company = %(company)s
            AND gle.docstatus = 1
        WHERE acc.company = %(company)s
            AND acc.is_group = 0
        GROUP BY acc.name
        HAVING ABS(balance) > 0.01 OR %(include_zero)s = 1
        ORDER BY 
            CASE 
                WHEN acc.root_type = 'Asset' THEN 1
                WHEN acc.root_type = 'Liability' THEN 2
                WHEN acc.root_type = 'Equity' THEN 3
                WHEN acc.root_type = 'Income' THEN 4
                WHEN acc.root_type = 'Expense' THEN 5
                ELSE 6
            END,
            acc.account_number,
            acc.name
    """, {
        "as_at_date": as_at_date,
        "company": company,
        "include_zero": 1 if include_zero else 0
    }, as_dict=1)
    
    # Group accounts by root type for better presentation
    grouped_data = []
    current_account_type = None
    type_totals = {}
    
    for row in data:
        account_type = row.get('account_type', 'Other')
        
        # Add section header when account type changes
        if current_account_type != account_type:
            if current_account_type:
                # Add subtotal for previous account type
                add_type_subtotal(grouped_data, type_totals, current_account_type)
            
            current_account_type = account_type
            type_totals[account_type] = {
                'balance': 0,
                'debit': 0,
                'credit': 0
            }
            
            # Add account type header
            grouped_data.append({
                "account_code": "",
                "account_name": f"═══════════════════════════════════════════════════",
                "account_type": "",
                "debit": None,
                "credit": None,
                "balance": None,
                "is_header_row": True
            })
            
            grouped_data.append({
                "account_code": "",
                "account_name": f"► {account_type.upper()} ACCOUNTS",
                "account_type": "",
                "debit": None,
                "credit": None,
                "balance": None,
                "is_section_header": True
            })
            
            grouped_data.append({
                "account_code": "",
                "account_name": f"═══════════════════════════════════════════════════",
                "account_type": "",
                "debit": None,
                "credit": None,
                "balance": None,
                "is_header_row": True
            })
        
        # Update totals
        type_totals[account_type]['balance'] += flt(row.get('balance'))
        type_totals[account_type]['debit'] += flt(row.get('debit'))
        type_totals[account_type]['credit'] += flt(row.get('credit'))
        
        grouped_data.append(row)
    
    # Add last account type subtotal
    if current_account_type:
        add_type_subtotal(grouped_data, type_totals, current_account_type)
    
    # Calculate grand totals
    total_debit = 0
    total_credit = 0
    total_balance = 0
    
    for row in data:
        total_debit += flt(row.get("debit", 0))
        total_credit += flt(row.get("credit", 0))
        total_balance += flt(row.get("balance", 0))
    
    # Add spacing before grand total
    grouped_data.append({})
    
    # Append grand total row
    grouped_data.append({
        "account_code": "",
        "account_name": "GRAND TOTAL",
        "account_type": "",
        "debit": total_debit,
        "credit": total_credit,
        "balance": total_balance,
        "is_total_row": True
    })
    
    return grouped_data


def add_type_subtotal(grouped_data, type_totals, account_type):
    """Add subtotal row for an account type section"""
    totals = type_totals.get(account_type, {})
    
    # Add separator line
    grouped_data.append({
        "account_code": "",
        "account_name": "──────────────────────────────────────────────────",
        "account_type": "",
        "debit": None,
        "credit": None,
        "balance": None,
        "is_separator": True
    })
    
    # Add subtotal row
    grouped_data.append({
        "account_code": "",
        "account_name": f"SUBTOTAL - {account_type.upper()}",
        "account_type": "",
        "debit": totals.get('debit', 0),
        "credit": totals.get('credit', 0),
        "balance": totals.get('balance', 0),
        "is_subtotal_row": True
    })
    
    # Add spacer
    grouped_data.append({})


def get_report_summary(data, filters):
    """Generate summary cards for the report"""
    if not data:
        return []
    
    total_debit = 0
    total_credit = 0
    account_count = 0
    
    for row in data:
        if row and not row.get('is_header_row') and not row.get('is_subtotal_row') and not row.get('is_total_row') and not row.get('is_separator') and not row.get('is_section_header'):
            account_count += 1
            total_debit += flt(row.get("debit", 0))
            total_credit += flt(row.get("credit", 0))
    
    difference = abs(total_debit - total_credit)
    is_balanced = difference < 0.01
    
    currency = filters.get("currency", "INR")
    
    return [
        {
            "value": total_debit,
            "label": "Total Debit",
            "datatype": "Currency",
            "indicator": "Blue",
            "currency": currency
        },
        {
            "value": total_credit,
            "label": "Total Credit",
            "datatype": "Currency",
            "indicator": "Green",
            "currency": currency
        },
        {
            "value": difference,
            "label": "Difference",
            "datatype": "Currency",
            "indicator": "Green" if is_balanced else "Red",
            "currency": currency
        },
        {
            "value": account_count,
            "label": "Active Accounts",
            "datatype": "Int",
            "indicator": "Blue"
        }
    ]


@frappe.whitelist()
def download_excel(filters=None):
    """
    Generate a stunning, beautifully formatted Trial Balance Excel report
    matching the Supplier Ledger style
    """
    if filters is None:
        filters = {}
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    # Get company currency
    filters["currency"] = get_company_currency(filters.get("company"))
    
    # Get report data
    columns, data = execute(filters)[:2]
    
    if not data:
        frappe.throw(_("No data available for the selected filters"))
    
    # Create Excel file with openpyxl
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
    from openpyxl.utils import get_column_letter
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Trial Balance"
    
    # ============================================================
    # PREMIUM COLOR PALETTE - Supplier Ledger Style (Blue Theme)
    # ============================================================
    colors = {
        'dark_blue': '1E3F6E',         # Customer header
        'medium_blue': '2C5A9E',        # Column headers
        'light_blue': 'E6F0FA',          # Subtotal background
        'light_gray': 'F5F5F5',          # Alternate row background
        'white': 'FFFFFF',
        'debit_blue': '2568B2',          # Debit amounts
        'credit_green': '1E7E34',        # Credit amounts
        'positive_orange': 'E67E22',      # Positive balance
        'negative_red': 'C0392B',         # Negative balance
        'border_gray': 'D0D7DE',
        'title_bg': 'F0F7FD',
        'section_line': 'B0C4DE'
    }
    
    # ============================================================
    # STYLE DEFINITIONS
    # ============================================================
    
    def get_fill(hex_color):
        return PatternFill("solid", fgColor=hex_color.replace('#', ''))
    
    thin_border = Border(
        left=Side(style='thin', color=colors['border_gray'].replace('#', '')),
        right=Side(style='thin', color=colors['border_gray'].replace('#', '')),
        top=Side(style='thin', color=colors['border_gray'].replace('#', '')),
        bottom=Side(style='thin', color=colors['border_gray'].replace('#', ''))
    )
    
    header_border = Border(
        bottom=Side(style='medium', color=colors['white'].replace('#', '')),
        right=Side(style='thin', color='4A7AB3')
    )
    
    # Title styles
    title_font = Font(name='Arial', size=22, bold=True, color='FFFFFF')
    title_fill = get_fill(colors['dark_blue'])
    title_alignment = Alignment(horizontal='center', vertical='center')
    
    subtitle_font = Font(name='Arial', size=14, bold=True, color='FFFFFF')
    subtitle_fill = get_fill(colors['medium_blue'])
    subtitle_alignment = Alignment(horizontal='center', vertical='center')
    
    # Header style
    header_font = Font(name='Arial', size=11, bold=True, color='FFFFFF')
    header_fill = get_fill(colors['medium_blue'])
    header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    
    # Section header style
    section_font = Font(name='Arial', size=11, bold=True, color=colors['dark_blue'])
    section_fill = get_fill(colors['light_blue'])
    section_alignment = Alignment(horizontal='left', vertical='center')
    section_border = Border(
        top=Side(style='medium', color=colors['dark_blue'].replace('#', '')),
        bottom=Side(style='thin', color=colors['border_gray'].replace('#', ''))
    )
    
    # Section line style
    line_font = Font(name='Arial', size=10, color=colors['section_line'])
    line_alignment = Alignment(horizontal='left', vertical='center')
    
    # Even row style
    even_font = Font(name='Calibri', size=10)
    even_fill = get_fill(colors['white'])
    
    # Odd row style
    odd_font = Font(name='Calibri', size=10)
    odd_fill = get_fill(colors['light_gray'])
    
    # Number format with company currency
    currency_symbol = frappe.db.get_value("Currency", filters.get("currency"), "symbol") or ""
    number_format = f'#,##0.00'
    
    # Positive/Negative styles
    positive_font = Font(name='Calibri', size=10, bold=True, color=colors['positive_orange'])
    negative_font = Font(name='Calibri', size=10, bold=True, color=colors['negative_red'])
    debit_font = Font(name='Calibri', size=10, bold=True, color=colors['debit_blue'])
    credit_font = Font(name='Calibri', size=10, bold=True, color=colors['credit_green'])
    
    # Subtotal style
    subtotal_font = Font(name='Arial', size=10, bold=True, color=colors['dark_blue'])
    subtotal_fill = get_fill(colors['light_blue'])
    subtotal_border = Border(
        top=Side(style='thin', color=colors['border_gray'].replace('#', '')),
        bottom=Side(style='thin', color=colors['border_gray'].replace('#', ''))
    )
    
    # Grand total style
    total_font = Font(name='Arial', size=12, bold=True, color='FFFFFF')
    total_fill = get_fill(colors['dark_blue'])
    total_border = Border(
        top=Side(style='double', color=colors['dark_blue'].replace('#', '')),
        bottom=Side(style='double', color=colors['dark_blue'].replace('#', ''))
    )
    
    # ============================================================
    # SET COLUMN WIDTHS
    # ============================================================
    col_widths = [18, 50, 18, 20, 20, 20]
    for i, width in enumerate(col_widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width
    
    # ============================================================
    # BUILD HEADER SECTION
    # ============================================================
    current_row = 1
    
    # Row 1: Main Title
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=6)
    cell = ws.cell(row=current_row, column=1, value="TRIAL BALANCE STATEMENT")
    cell.font = title_font
    cell.fill = title_fill
    cell.alignment = title_alignment
    ws.row_dimensions[current_row].height = 40
    current_row += 1
    
    # Row 2: Company Name
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=6)
    cell = ws.cell(row=current_row, column=1, value=filters.get('company', '').upper())
    cell.font = subtitle_font
    cell.fill = subtitle_fill
    cell.alignment = subtitle_alignment
    ws.row_dimensions[current_row].height = 30
    current_row += 1
    
    # Row 3: Date and Currency
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=6)
    date_text = f"AS AT {filters.get('as_at_date', '')} | Currency: {filters.get('currency', 'INR')}"
    cell = ws.cell(row=current_row, column=1, value=date_text)
    cell.font = Font(name='Arial', size=11, bold=True, color='333333')
    cell.alignment = Alignment(horizontal='center', vertical='center')
    cell.fill = get_fill('E8F0FE')
    ws.row_dimensions[current_row].height = 25
    current_row += 1
    
    # Row 4: Spacer
    ws.row_dimensions[current_row].height = 8
    current_row += 1
    
    # ============================================================
    # COLUMN HEADERS
    # ============================================================
    header_row = current_row
    for col_num, column in enumerate(columns, start=1):
        cell = ws.cell(row=header_row, column=col_num, value=column['label'])
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = header_border
    ws.row_dimensions[header_row].height = 35
    current_row += 1
    
    # Freeze panes
    ws.freeze_panes = f'A{current_row}'
    
    # ============================================================
    # DATA ROWS
    # ============================================================
    row_counter = 0
    
    for row_data in data:
        if not row_data:  # Spacer row
            for col in range(1, 7):
                cell = ws.cell(row=current_row, column=col, value='')
            ws.row_dimensions[current_row].height = 8
            current_row += 1
            continue
        
        is_header = row_data.get('is_header_row', False)
        is_section = row_data.get('is_section_header', False)
        is_separator = row_data.get('is_separator', False)
        is_subtotal = row_data.get('is_subtotal_row', False)
        is_total = row_data.get('is_total_row', False)
        
        if is_header or is_section or is_separator:
            # Section header or separator line
            ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=6)
            cell = ws.cell(row=current_row, column=1, value=row_data.get('account_name', ''))
            
            if is_section:
                cell.font = section_font
                cell.fill = section_fill
                cell.alignment = section_alignment
                cell.border = section_border
                ws.row_dimensions[current_row].height = 22
            elif is_separator:
                cell.font = Font(name='Arial', size=10, color=colors['section_line'])
                cell.alignment = Alignment(horizontal='left', vertical='center')
                ws.row_dimensions[current_row].height = 16
            else:
                cell.font = Font(name='Arial', size=10, color=colors['section_line'])
                cell.alignment = Alignment(horizontal='left', vertical='center')
                ws.row_dimensions[current_row].height = 16
            
            current_row += 1
            
        elif is_subtotal:
            # Subtotal row
            for col_num, column in enumerate(columns, 1):
                fieldname = column['fieldname']
                value = row_data.get(fieldname, '')
                
                cell = ws.cell(row=current_row, column=col_num)
                cell.fill = subtotal_fill
                cell.border = subtotal_border
                
                if column['fieldtype'] == 'Currency' and value:
                    cell.value = flt(value)
                    cell.number_format = number_format
                    cell.font = subtotal_font
                    cell.alignment = Alignment(horizontal='right', vertical='center')
                else:
                    cell.value = str(value) if value else ''
                    if fieldname == 'account_name':
                        cell.font = subtotal_font
                        cell.alignment = Alignment(horizontal='left', vertical='center')
                    else:
                        cell.font = Font(size=10)
                        cell.alignment = Alignment(horizontal='left', vertical='center')
            
            ws.row_dimensions[current_row].height = 22
            current_row += 1
            
        elif is_total:
            # Grand total row
            for col_num, column in enumerate(columns, 1):
                fieldname = column['fieldname']
                value = row_data.get(fieldname, '')
                
                cell = ws.cell(row=current_row, column=col_num)
                cell.font = total_font
                cell.fill = total_fill
                cell.border = total_border
                
                if column['fieldtype'] == 'Currency' and value:
                    cell.value = flt(value)
                    cell.number_format = number_format
                    cell.alignment = Alignment(horizontal='right', vertical='center')
                else:
                    cell.value = str(value) if value else ''
                    if fieldname == 'account_name':
                        cell.alignment = Alignment(horizontal='left', vertical='center')
                    else:
                        cell.alignment = Alignment(horizontal='left', vertical='center')
            
            ws.row_dimensions[current_row].height = 28
            current_row += 1
            
        else:
            # Regular transaction row
            is_even = row_counter % 2 == 0
            row_fill = even_fill if is_even else odd_fill
            
            for col_num, column in enumerate(columns, 1):
                fieldname = column['fieldname']
                value = row_data.get(fieldname, '')
                
                cell = ws.cell(row=current_row, column=col_num)
                cell.fill = row_fill
                cell.border = thin_border
                
                if column['fieldtype'] == 'Currency' and value:
                    cell.value = flt(value)
                    cell.number_format = number_format
                    cell.alignment = Alignment(horizontal='right', vertical='center')
                    
                    # Color code based on field and value
                    if fieldname == 'debit' and flt(value) > 0:
                        cell.font = debit_font
                    elif fieldname == 'credit' and flt(value) > 0:
                        cell.font = credit_font
                    elif fieldname == 'balance':
                        if flt(value) > 0:
                            cell.font = positive_font
                        elif flt(value) < 0:
                            cell.font = negative_font
                        else:
                            cell.font = Font(size=10)
                    else:
                        cell.font = Font(size=10)
                else:
                    cell.value = str(value) if value else ''
                    cell.font = Font(name='Calibri', size=10)
                    cell.alignment = Alignment(horizontal='left', vertical='center')
            
            ws.row_dimensions[current_row].height = 18
            current_row += 1
            row_counter += 1
    
    # ============================================================
    # EXECUTIVE SUMMARY SECTION
    # ============================================================
    current_row += 2
    
    # Summary title
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=6)
    summary_title = ws.cell(row=current_row, column=1, value="EXECUTIVE SUMMARY")
    summary_title.font = Font(name='Arial', size=14, bold=True, color='FFFFFF')
    summary_title.fill = get_fill(colors['medium_blue'])
    summary_title.alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[current_row].height = 30
    current_row += 1
    
    # Summary cards (2x2 grid)
    summary_data = get_report_summary(data, filters)
    
    for i, summary in enumerate(summary_data):
        col_start = 1 + (i % 2) * 3
        col_end = col_start + 2
        row = current_row + (i // 2) * 2
        
        # Card label
        ws.merge_cells(start_row=row, start_column=col_start, end_row=row, end_column=col_end)
        label_cell = ws.cell(row=row, column=col_start, value=summary.get('label', ''))
        label_cell.font = Font(name='Arial', size=10, bold=True, color='333333')
        label_cell.fill = get_fill('E8F0FE')
        label_cell.alignment = Alignment(horizontal='center', vertical='center')
        label_cell.border = thin_border
        ws.row_dimensions[row].height = 22
        
        # Card value
        ws.merge_cells(start_row=row+1, start_column=col_start, end_row=row+1, end_column=col_end)
        value_cell = ws.cell(row=row+1, column=col_start, value=flt(summary.get('value', 0)))
        value_cell.font = Font(name='Arial', size=16, bold=True, color=colors['dark_blue'])
        value_cell.fill = get_fill(colors['white'])
        value_cell.alignment = Alignment(horizontal='center', vertical='center')
        value_cell.border = Border(
            left=Side(style='thin', color=colors['border_gray'].replace('#', '')),
            right=Side(style='thin', color=colors['border_gray'].replace('#', '')),
            bottom=Side(style='thin', color=colors['border_gray'].replace('#', ''))
        )
        if summary.get('datatype') == 'Currency':
            value_cell.number_format = number_format
        ws.row_dimensions[row+1].height = 30
    
    # ============================================================
    # FOOTER
    # ============================================================
    current_row += 6
    
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=6)
    footer_cell = ws.cell(row=current_row, column=1, 
                         value=f"Generated on: {datetime.now().strftime('%d %B %Y at %I:%M %p')} | Trial Balance Report")
    footer_cell.font = Font(name='Arial', size=9, italic=True, color='666666')
    footer_cell.alignment = Alignment(horizontal='center', vertical='center')
    footer_cell.border = Border(top=Side(style='thin', color='CCCCCC'))
    ws.row_dimensions[current_row].height = 22
    
    # ============================================================
    # PAGE SETUP
    # ============================================================
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.paperSize = 9  # A4
    ws.page_setup.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    
    # Set print titles to repeat header row
    ws.print_title_rows = f'1:{header_row}'
    
    # ============================================================
    # SAVE AND RETURN
    # ============================================================
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    company_safe = filters.get('company', 'Company').replace(' ', '_').replace('/', '_')
    
    frappe.response['filename'] = f"Trial_Balance_{company_safe}_{filters.get('as_at_date')}_{timestamp}.xlsx"
    frappe.response['filecontent'] = output.getvalue()
    frappe.response['type'] = 'binary'