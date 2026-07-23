# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, today
import json
from datetime import datetime

def execute(filters=None):
    if not filters:
        filters = {}
        
    columns = get_columns()
    data = get_data(filters)
    summary = get_summary(data)
    
    return columns, data, None, None, summary

def get_columns():
    return [
        {
            "label": _("Posting Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 100
        },
        {
            "label": _("Supplier ID"),
            "fieldname": "supplier",
            "fieldtype": "Link",
            "options": "Supplier",
            "width": 120
        },
        {
            "label": _("Supplier Name"),
            "fieldname": "supplier_name",
            "fieldtype": "Data",
            "width": 200
        },
        {
            "label": _("Voucher Type"),
            "fieldname": "voucher_type",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Voucher No"),
            "fieldname": "voucher_no",
            "fieldtype": "Dynamic Link",
            "options": "voucher_type",
            "width": 150
        },
        {
            "label": _("Reference"),
            "fieldname": "against_voucher",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("Description"),
            "fieldname": "description",
            "fieldtype": "Data",
            "width": 250
        },
        {
            "label": _("Debit"),
            "fieldname": "debit",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 130
        },
        {
            "label": _("Credit"),
            "fieldname": "credit",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 130
        },
        {
            "label": _("Balance"),
            "fieldname": "balance",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 130
        },
        {
            "label": _("Currency"),
            "fieldname": "currency",
            "fieldtype": "Link",
            "options": "Currency",
            "width": 80,
            "hidden": 1
        }
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    
    gl_entries = frappe.db.sql("""
        SELECT 
            gle.posting_date,
            gle.party as supplier,
            supp.supplier_name,
            gle.voucher_type,
            gle.voucher_no,
            gle.against_voucher,
            gle.remarks as description,
            gle.debit,
            gle.credit,
            gle.debit_in_account_currency as debit_in_currency,
            gle.credit_in_account_currency as credit_in_currency,
            gle.account_currency as currency,
            gle.against
        FROM 
            `tabGL Entry` gle
        LEFT JOIN 
            `tabSupplier` supp ON supp.name = gle.party
        WHERE 
            gle.party_type = 'Supplier'
            AND gle.is_cancelled = 0
            {conditions}
        ORDER BY 
            gle.party, gle.posting_date, gle.creation
    """.format(conditions=conditions), filters, as_dict=1)
    
    # Group entries by supplier
    supplier_entries = {}
    supplier_meta = {}  # store name and currency
    
    for entry in gl_entries:
        supplier = entry.get('supplier')
        if supplier not in supplier_entries:
            supplier_entries[supplier] = []
            supplier_meta[supplier] = {
                'supplier_name': entry.get('supplier_name'),
                'currency': entry.get('currency', 'NGN')
            }
        supplier_entries[supplier].append(entry)

    final_data = []
    
    # Grand total accumulators
    grand_total_debit = 0
    grand_total_credit = 0
    grand_total_balance = 0

    for supplier, entries in supplier_entries.items():
        meta = supplier_meta[supplier]
        currency = meta.get('currency', 'NGN')
        supplier_name = meta.get('supplier_name', supplier)

        # HEADER ROW
        opening_balance = get_opening_balance(supplier, filters)

        final_data.append({
            "posting_date": "",
            "supplier": supplier,
            "supplier_name": supplier_name,
            "voucher_type": "",
            "voucher_no": "",
            "against_voucher": "",
            "description": "",
            "debit": None,
            "credit": None,
            "balance": opening_balance if opening_balance else None,
            "currency": currency,
            "is_header_row": True,
            "bold": 1,
        })

        # TRANSACTION ROWS
        running_balance = opening_balance
        supplier_total_debit = 0
        supplier_total_credit = 0

        for entry in entries:
            running_balance += flt(entry.get('debit')) - flt(entry.get('credit'))
            supplier_total_debit += flt(entry.get('debit'))
            supplier_total_credit += flt(entry.get('credit'))

            final_data.append({
                "posting_date": entry.get('posting_date'),
                "supplier": entry.get('supplier'),
                "supplier_name": entry.get('supplier_name'),
                "voucher_type": entry.get('voucher_type'),
                "voucher_no": entry.get('voucher_no'),
                "against_voucher": entry.get('against_voucher'),
                "description": entry.get('description') or entry.get('against'),
                "debit": flt(entry.get('debit')),
                "credit": flt(entry.get('credit')),
                "balance": running_balance,
                "currency": currency,
                "indent": 1,
            })

        # Add to grand totals
        grand_total_debit += supplier_total_debit
        grand_total_credit += supplier_total_credit
        grand_total_balance += running_balance

        # SUBTOTAL ROW
        final_data.append({
            "posting_date": "",
            "supplier": supplier,
            "supplier_name": f"Subtotal — {supplier_name}",
            "voucher_type": "",
            "voucher_no": "",
            "against_voucher": "",
            "description": "Closing Balance",
            "debit": supplier_total_debit,
            "credit": supplier_total_credit,
            "balance": running_balance,
            "currency": currency,
            "is_total_row": True,
            "bold": 1,
        })

        # SPACER ROW
        final_data.append({})

    # GRAND TOTAL ROW
    final_data.append({
        "posting_date": "",
        "supplier": "",
        "supplier_name": "═══════════════════════════════════════════════════════════════════════════════════════════════════",
        "voucher_type": "",
        "voucher_no": "",
        "against_voucher": "",
        "description": "GRAND TOTAL (All Suppliers)",
        "debit": grand_total_debit,
        "credit": grand_total_credit,
        "balance": grand_total_balance,
        "currency": "NGN",
        "is_grand_total": True,
        "bold": 1,
    })

    return final_data

def get_conditions(filters):
    conditions = []
    
    if filters.get('company'):
        conditions.append("gle.company = %(company)s")
    
    if filters.get('from_date'):
        conditions.append("gle.posting_date >= %(from_date)s")
    
    if filters.get('to_date'):
        conditions.append("gle.posting_date <= %(to_date)s")
    
    if filters.get('supplier'):
        conditions.append("gle.party = %(supplier)s")
    
    if filters.get('supplier_group'):
        conditions.append("supp.supplier_group = %(supplier_group)s")
    
    return "AND " + " AND ".join(conditions) if conditions else ""

def get_opening_balance(supplier, filters):
    if not filters.get('from_date'):
        return 0
    
    opening = frappe.db.sql("""
        SELECT 
            SUM(debit - credit) as balance
        FROM 
            `tabGL Entry`
        WHERE 
            party_type = 'Supplier'
            AND party = %s
            AND posting_date < %s
            AND is_cancelled = 0
    """, (supplier, filters.get('from_date')), as_dict=1)
    
    return flt(opening[0].get('balance')) if opening else 0

def get_summary(data):
    if not data:
        return None
    
    total_debit = 0
    total_credit = 0
    grand_balance = 0
    
    # Find the grand total row
    for row in data:
        if row and row.get('is_grand_total'):
            total_debit = flt(row.get('debit'))
            total_credit = flt(row.get('credit'))
            grand_balance = flt(row.get('balance'))
            break
    
    return [
        {
            "value": total_debit,
            "label": "Grand Total Debit",
            "datatype": "Currency",
            "currency": "NGN"
        },
        {
            "value": total_credit,
            "label": "Grand Total Credit",
            "datatype": "Currency",
            "currency": "NGN"
        },
        {
            "value": grand_balance,
            "label": "Grand Outstanding Balance",
            "datatype": "Currency",
            "currency": "NGN"
        }
    ]


@frappe.whitelist()
def download_excel(filters=None):
    """
    Beautifully formatted Excel export for Supplier Ledger with Grand Total
    """
    import re
    import io
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
    from openpyxl.utils import get_column_letter

    if filters is None:
        filters = {}
    if isinstance(filters, str):
        filters = json.loads(filters)

    data = get_data(filters)
    columns = get_columns()

    # Visible columns only
    vis_cols = [c for c in columns if not c.get("hidden")]
    col_labels = [c.get("label") for c in vis_cols]
    col_fields = [c.get("fieldname") for c in vis_cols]
    col_types = [c.get("fieldtype") for c in vis_cols]
    num_cols = len(vis_cols)

    # Indices of currency columns (0-based)
    currency_idx = {i for i, ft in enumerate(col_types) if ft == "Currency"}

    # Create Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Supplier Ledger"

    # Color Palette (Supplier theme - Purple/Burgundy)
    colors = {
        'dark_purple': '4A235A',
        'medium_purple': '6C3483',
        'light_purple': 'F5EEF8',
        'light_gray': 'F8F9F9',
        'white': 'FFFFFF',
        'debit_brown': '8B4513',
        'credit_green': '1E7E34',
        'positive_balance': '117A65',
        'negative_balance': 'B03A2E',
        'border_gray': 'D5D8DC',
        'title_bg': 'FBFCFC',
        'grand_total_gold': '7D3C98',
        'grand_total_bg': 'F4ECF7'
    }

    def get_fill(hex_color):
        return PatternFill("solid", fgColor=hex_color)

    thin_border = Border(
        left=Side(style='thin', color=colors['border_gray']),
        right=Side(style='thin', color=colors['border_gray']),
        top=Side(style='thin', color=colors['border_gray']),
        bottom=Side(style='thin', color=colors['border_gray'])
    )

    header_border = Border(
        bottom=Side(style='medium', color=colors['white']),
        right=Side(style='thin', color='9B59B6')
    )

    NUM_FMT = '#,##0.00'

    # Set Column Widths
    col_widths = [13, 15, 30, 16, 22, 22, 40, 17, 17, 17]
    for i, width in enumerate(col_widths[:num_cols], start=1):
        ws.column_dimensions[get_column_letter(i)].width = width

    def clean_html(value):
        if isinstance(value, str):
            value = re.sub(r'<[^>]+>', '', value)
            value = value.replace('&nbsp;', ' ').replace('\u2014', '-').strip()
        return value if value is not None else ''

    # Title Block
    company = filters.get('company', '')
    from_date = filters.get('from_date', '')
    to_date = filters.get('to_date', '')
    generated_on = datetime.now().strftime('%d %B %Y at %I:%M %p')

    title_rows = [
        ('SUPPLIER LEDGER REPORT', Font(bold=True, size=16, color=colors['dark_purple']), 28),
        (f'Company: {company}', Font(size=11, color='444444'), 20),
        (f'Period: {from_date} to {to_date}', Font(size=11, color='444444'), 20),
        (f'Generated: {generated_on}', Font(italic=True, size=10, color='666666'), 18),
        ('', None, 8)
    ]

    for text, font, height in title_rows:
        ws.append([text] + [''] * (num_cols - 1))
        row = ws.max_row
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=num_cols)
        cell = ws.cell(row=row, column=1)
        cell.value = text
        if font:
            cell.font = font
        cell.fill = get_fill(colors['title_bg'])
        cell.alignment = Alignment(horizontal='left', vertical='center', indent=1)
        ws.row_dimensions[row].height = height

    # Column Headers
    ws.append(col_labels)
    header_row = ws.max_row
    for col_idx, cell in enumerate(ws[header_row], start=1):
        cell.font = Font(bold=True, color=colors['white'], size=11)
        cell.fill = get_fill(colors['medium_purple'])
        cell.alignment = Alignment(
            horizontal='right' if (col_idx - 1) in currency_idx else 'center',
            vertical='center'
        )
        cell.border = header_border
    ws.row_dimensions[header_row].height = 26
    ws.freeze_panes = f'A{header_row + 1}'

    # Data Rows
    current_row = header_row + 1
    row_counter = 0

    for row_data in data:
        if not row_data:  # Spacer row
            ws.append([''] * num_cols)
            ws.row_dimensions[ws.max_row].height = 8
            continue

        is_header = row_data.get('is_header_row')
        is_total = row_data.get('is_total_row')
        is_grand_total = row_data.get('is_grand_total')

        excel_row = []
        for idx, field in enumerate(col_fields):
            val = row_data.get(field)
            if idx in currency_idx:
                excel_row.append(flt(val) if val is not None else 0)
            else:
                excel_row.append(clean_html(val) if val is not None else '')

        ws.append(excel_row)
        current_row = ws.max_row

        # Supplier Header Row
        if is_header:
            ws.merge_cells(start_row=current_row, start_column=1,
                          end_row=current_row, end_column=num_cols)

            supplier_text = f"  ⬤  {row_data.get('supplier_name', '')}  [{row_data.get('supplier', '')}]"
            cell = ws.cell(row=current_row, column=1)
            cell.value = supplier_text
            cell.font = Font(bold=True, color=colors['white'], size=12)
            cell.fill = get_fill(colors['dark_purple'])
            cell.alignment = Alignment(horizontal='left', vertical='center', indent=1)
            ws.row_dimensions[current_row].height = 24

            opening_bal = row_data.get('balance')
            if opening_bal:
                ws.unmerge_cells(start_row=current_row, start_column=1,
                                end_row=current_row, end_column=num_cols)
                if num_cols > 1:
                    ws.merge_cells(start_row=current_row, start_column=1,
                                  end_row=current_row, end_column=num_cols - 1)

                bal_cell = ws.cell(row=current_row, column=num_cols)
                bal_cell.value = flt(opening_bal)
                bal_cell.number_format = NUM_FMT
                bal_cell.font = Font(italic=True, color='E8DAEF', size=10)
                bal_cell.fill = get_fill(colors['dark_purple'])
                bal_cell.alignment = Alignment(horizontal='right', vertical='center')

        # Subtotal Row
        elif is_total:
            ws.row_dimensions[current_row].height = 22

            for col_idx in range(1, num_cols + 1):
                cell = ws.cell(row=current_row, column=col_idx)
                cell.fill = get_fill(colors['light_purple'])
                cell.border = Border(
                    top=Side(style='medium', color=colors['medium_purple']),
                    bottom=Side(style='thin', color=colors['border_gray'])
                )

                field = col_fields[col_idx - 1]

                if field == 'supplier_name':
                    cell.font = Font(bold=True, color=colors['dark_purple'], size=11)
                    cell.alignment = Alignment(horizontal='left', vertical='center', indent=1)

                elif field == 'description':
                    cell.font = Font(bold=True, color='555555', size=10)
                    cell.alignment = Alignment(horizontal='left', vertical='center')

                elif field == 'debit':
                    cell.number_format = NUM_FMT
                    cell.font = Font(bold=True, color=colors['debit_brown'], size=11)
                    cell.alignment = Alignment(horizontal='right', vertical='center')

                elif field == 'credit':
                    cell.number_format = NUM_FMT
                    cell.font = Font(bold=True, color=colors['credit_green'], size=11)
                    cell.alignment = Alignment(horizontal='right', vertical='center')

                elif field == 'balance':
                    balance = flt(row_data.get('balance'))
                    cell.number_format = NUM_FMT
                    balance_color = colors['positive_balance'] if balance > 0 else \
                                   colors['negative_balance'] if balance < 0 else '1E7E34'
                    cell.font = Font(bold=True, color=balance_color, size=11)
                    cell.alignment = Alignment(horizontal='right', vertical='center')

                elif (col_idx - 1) in currency_idx:
                    cell.number_format = NUM_FMT
                    cell.font = Font(bold=True, size=11)
                    cell.alignment = Alignment(horizontal='right', vertical='center')

        # Grand Total Row
        elif is_grand_total:
            ws.row_dimensions[current_row].height = 28
            
            # Merge cells for better visual appearance
            if num_cols > 1:
                ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=2)
                ws.merge_cells(start_row=current_row, start_column=3, end_row=current_row, end_column=6)
            
            for col_idx in range(1, num_cols + 1):
                cell = ws.cell(row=current_row, column=col_idx)
                cell.fill = get_fill(colors['grand_total_bg'])
                cell.border = Border(
                    top=Side(style='double', color=colors['grand_total_gold']),
                    bottom=Side(style='double', color=colors['grand_total_gold']),
                    left=Side(style='thin', color=colors['border_gray']),
                    right=Side(style='thin', color=colors['border_gray'])
                )
                
                field = col_fields[col_idx - 1]
                
                if field == 'supplier_name':
                    cell.font = Font(bold=True, color=colors['grand_total_gold'], size=12)
                    cell.alignment = Alignment(horizontal='left', vertical='center', indent=1)
                
                elif field == 'description':
                    cell.font = Font(bold=True, color=colors['grand_total_gold'], size=12)
                    cell.alignment = Alignment(horizontal='left', vertical='center')
                
                elif field == 'debit':
                    cell.number_format = NUM_FMT
                    cell.font = Font(bold=True, color=colors['debit_brown'], size=12)
                    cell.alignment = Alignment(horizontal='right', vertical='center')
                
                elif field == 'credit':
                    cell.number_format = NUM_FMT
                    cell.font = Font(bold=True, color=colors['credit_green'], size=12)
                    cell.alignment = Alignment(horizontal='right', vertical='center')
                
                elif field == 'balance':
                    balance = flt(row_data.get('balance'))
                    cell.number_format = NUM_FMT
                    balance_color = colors['positive_balance'] if balance > 0 else \
                                   colors['negative_balance'] if balance < 0 else colors['dark_purple']
                    cell.font = Font(bold=True, color=balance_color, size=13)
                    cell.alignment = Alignment(horizontal='right', vertical='center')
                
                elif (col_idx - 1) in currency_idx:
                    cell.number_format = NUM_FMT
                    cell.font = Font(bold=True, size=12)
                    cell.alignment = Alignment(horizontal='right', vertical='center')

        # Normal Transaction Row
        else:
            row_fill = get_fill(colors['light_gray']) if row_counter % 2 == 0 else get_fill(colors['white'])

            for col_idx in range(1, num_cols + 1):
                cell = ws.cell(row=current_row, column=col_idx)
                cell.fill = row_fill
                cell.border = thin_border

                field = col_fields[col_idx - 1]

                if (col_idx - 1) in currency_idx:
                    cell.number_format = NUM_FMT
                    cell.alignment = Alignment(horizontal='right', vertical='center')

                    if field == 'debit' and flt(row_data.get('debit')) > 0:
                        cell.font = Font(color=colors['debit_brown'], size=10)
                    elif field == 'credit' and flt(row_data.get('credit')) > 0:
                        cell.font = Font(color=colors['credit_green'], size=10)
                    elif field == 'balance':
                        balance = flt(row_data.get('balance'))
                        if balance > 0:
                            cell.font = Font(color=colors['positive_balance'], size=10, bold=True)
                        elif balance < 0:
                            cell.font = Font(color=colors['negative_balance'], size=10, bold=True)
                        else:
                            cell.font = Font(size=10)
                    else:
                        cell.font = Font(size=10)
                else:
                    cell.font = Font(size=10)
                    cell.alignment = Alignment(
                        horizontal='left',
                        vertical='center',
                        wrap_text=(field == 'description')
                    )

        row_counter += 1

    # Page Setup
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_options.gridLines = False
    ws.print_title_rows = f'1:{header_row}'

    # Save and return
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    frappe.response['filename'] = f'Supplier_Ledger_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    frappe.response['filecontent'] = output.getvalue()
    frappe.response['type'] = 'binary'