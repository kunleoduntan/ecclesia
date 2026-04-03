# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate
from frappe.utils.xlsxutils import make_xlsx
from frappe.core.doctype.data_import.data_import import export_csv
import pandas as pd
from io import BytesIO

def execute(filters=None):
    """
    Standard Trial Balance Report with Beautiful Excel Export
    Returns columns and data for trial balance as at a specific date
    """
    if not filters:
        filters = {}
    
    # Validate required filters
    if not filters.get("company"):
        frappe.throw(_("Company is required"))
    if not filters.get("as_at_date"):
        frappe.throw(_("As at Date is required"))
    
    columns = get_columns()
    data = get_data(filters)
    
    # Add report summary for the web view
    report_summary = get_report_summary(data, filters)
    
    return columns, data, None, None, report_summary


def get_columns():
    """Define report columns with cute emojis"""
    return [
        {
            "label": _("🔢 Code"),
            "fieldname": "account_number",
            "fieldtype": "Link",
            "options": "Account",
            "width": 100
        },
        {
            "label": _("📁 Account Name"),
            "fieldname": "account_name",
            "fieldtype": "Data",
            "width": 300
        },
        {
            "label": _("👪 Parent Account"),
            "fieldname": "parent_account",
            "fieldtype": "Link",
            "options": "Account",
            "width": 200
        },
        {
            "label": _("⚖️ Balance"),
            "fieldname": "balance",
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "label": _("💳 Net Debit"),
            "fieldname": "net_debit",
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "label": _("💰 Net Credit"),
            "fieldname": "net_credit",
            "fieldtype": "Currency",
            "width": 150
        }
    ]


def get_data(filters):
    """Fetch trial balance data"""
    as_at_date = getdate(filters.get("as_at_date"))
    company = filters.get("company")
    
    # Main query to get account balances
    data = frappe.db.sql("""
        SELECT
            acc.account_number,
            acc.account_name,
            acc.parent_account,
            COALESCE(SUM(gle.debit), 0) AS debit,
            COALESCE(SUM(gle.credit), 0) AS credit,
            COALESCE(SUM(gle.debit) - SUM(gle.credit), 0) AS balance,
            CASE 
                WHEN COALESCE(SUM(gle.debit) - SUM(gle.credit), 0) > 0 
                THEN COALESCE(SUM(gle.debit) - SUM(gle.credit), 0)
                ELSE 0 
            END AS net_debit,
            CASE 
                WHEN COALESCE(SUM(gle.debit) - SUM(gle.credit), 0) < 0 
                THEN ABS(COALESCE(SUM(gle.debit) - SUM(gle.credit), 0))
                ELSE 0 
            END AS net_credit
        FROM `tabAccount` acc
        LEFT JOIN `tabGL Entry` gle 
            ON gle.account = acc.name 
            AND gle.posting_date <= %(as_at_date)s
            AND gle.company = %(company)s
            AND gle.docstatus = 1
        WHERE acc.company = %(company)s
            AND acc.is_group = 0
        GROUP BY acc.name
        HAVING ABS(balance) > 0.01
        ORDER BY acc.account_number, acc.name
    """, {
        "as_at_date": as_at_date,
        "company": company
    }, as_dict=1)
    
    # Calculate totals
    total_balance = 0
    total_net_debit = 0
    total_net_credit = 0
    
    for row in data:
        total_balance += flt(row.get("balance", 0))
        total_net_debit += flt(row.get("net_debit", 0))
        total_net_credit += flt(row.get("net_credit", 0))
    
    # Append total row
    if data:
        data.append({
            "account_number": "🎯",
            "account_name": "<b>TOTAL</b>",
            "parent_account": "",
            "balance": total_balance,
            "net_debit": total_net_debit,
            "net_credit": total_net_credit,
            "is_total_row": 1
        })
    
    return data


def get_report_summary(data, filters):
    """Generate cute report summary cards"""
    if not data:
        return []
    
    total_net_debit = 0
    total_net_credit = 0
    account_count = 0
    
    for row in data:
        if row.get("is_total_row"):
            continue
        account_count += 1
        total_net_debit += flt(row.get("net_debit", 0))
        total_net_credit += flt(row.get("net_credit", 0))
    
    balance_difference = abs(total_net_debit - total_net_credit)
    is_balanced = balance_difference < 0.01
    
    return [
        {
            "value": total_net_debit,
            "label": _("💳 Total Debit"),
            "datatype": "Currency",
            "indicator": "blue",
            "emoji": "💳"
        },
        {
            "value": total_net_credit,
            "label": _("💰 Total Credit"),
            "datatype": "Currency",
            "indicator": "orange",
            "emoji": "💰"
        },
        {
            "value": balance_difference,
            "label": _("⚖️ Difference"),
            "datatype": "Currency",
            "indicator": "green" if is_balanced else "red",
            "emoji": "✅" if is_balanced else "⚠️"
        },
        {
            "value": account_count,
            "label": _("📊 Active Accounts"),
            "datatype": "Int",
            "indicator": "blue",
            "emoji": "📊"
        }
    ]


@frappe.whitelist()
def download_cute_excel(filters):
    """Generate a STUNNING, world-class Excel report that rivals Big 4 accounting firms"""
    filters = frappe._dict(frappe.parse_json(filters))
    columns, data = execute(filters)[:2]
    
    if not data:
        frappe.throw(_("No data available for the selected filters"))
    
    # Create Excel file with XlsxWriter for advanced formatting
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # ============================================================
        # PREMIUM COLOR PALETTE - Corporate Excellence
        # ============================================================
        colors = {
            # Sophisticated Blues (Primary Brand)
            'navy': '#1B3B6F',              # Deep corporate blue
            'royal_blue': '#2E5090',        # Professional blue
            'sky_blue': '#4A90E2',          # Accent blue
            'ice_blue': '#E8F1FA',          # Light blue
            'powder_blue': '#D4E6F7',       # Very light blue
            
            # Premium Greys (Neutral Tones)
            'charcoal': '#2C3E50',          # Dark grey
            'slate': '#5D6D7E',             # Medium grey
            'silver': '#BDC3C7',            # Light grey
            'pearl': '#ECF0F1',             # Very light grey
            'snow': '#F8F9FA',              # Off-white
            'white': '#FFFFFF',             # Pure white
            
            # Accent Colors (Status Indicators)
            'emerald': '#27AE60',           # Success green
            'mint': '#D5F4E6',              # Light green
            'ruby': '#C0392B',              # Error red
            'rose': '#FADBD8',              # Light red
            'gold': '#F39C12',              # Warning orange
            'amber': '#FCF3CF',             # Light yellow
            
            # Special Purpose
            'total_gold': '#FFF9E6',        # Total row background
            'border_dark': '#34495E',       # Dark borders
            'border_light': '#D5DBDB',      # Light borders
        }
        
        # Create worksheet
        worksheet = workbook.add_worksheet('Trial Balance')
        
        # ============================================================
        # SECTION 1: MAGNIFICENT HEADER
        # ============================================================
        
        # Logo/Branding Bar - Deep Navy with Gradient Effect
        branding_format = workbook.add_format({
            'bold': True,
            'font_size': 26,
            'font_name': 'Arial',
            'font_color': colors['white'],
            'bg_color': colors['navy'],
            'align': 'center',
            'valign': 'vcenter',
            'border': 0
        })
        
        # Company Name Subtitle
        company_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'font_name': 'Arial',
            'font_color': colors['white'],
            'bg_color': colors['royal_blue'],
            'align': 'center',
            'valign': 'vcenter',
            'border': 0
        })
        
        # Report Type Badge
        report_type_format = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'font_name': 'Arial',
            'font_color': colors['navy'],
            'bg_color': colors['ice_blue'],
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'border_color': colors['sky_blue']
        })
        
        # Info Labels (Left Column)
        info_label = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'font_name': 'Arial',
            'font_color': colors['navy'],
            'bg_color': colors['powder_blue'],
            'align': 'right',
            'valign': 'vcenter',
            'border': 1,
            'border_color': colors['border_light'],
            'right': 2,
            'right_color': colors['royal_blue']
        })
        
        # Info Values (Right Column)
        info_value = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'font_name': 'Arial',
            'font_color': colors['charcoal'],
            'bg_color': colors['white'],
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
            'border_color': colors['border_light']
        })
        
        # Set premium row heights
        worksheet.set_row(0, 45)   # Main title - Extra tall
        worksheet.set_row(1, 32)   # Company name
        worksheet.set_row(2, 8)    # Spacer
        worksheet.set_row(3, 24)   # Report type badge
        worksheet.set_row(4, 20)   # Company info
        worksheet.set_row(5, 20)   # Date info
        worksheet.set_row(6, 8)    # Spacer
        worksheet.set_row(7, 35)   # Column headers - Tall
        
        # Write stunning header
        worksheet.merge_range('A1:F1', '✨ TRIAL BALANCE REPORT ✨', branding_format)
        worksheet.merge_range('A2:F2', filters.get("company", "N/A").upper(), company_format)
        worksheet.merge_range('A4:F4', '📊 FINANCIAL STATEMENT', report_type_format)
        
        # Elegant info table
        worksheet.merge_range('A5:B5', '🏢  Company Name:', info_label)
        worksheet.merge_range('C5:F5', filters.get('company', 'N/A'), info_value)
        
        worksheet.merge_range('A6:B6', '📅  Reporting Date:', info_label)
        worksheet.merge_range('C6:F6', filters.get('as_at_date', 'N/A'), info_value)
        
        # ============================================================
        # SECTION 2: PREMIUM COLUMN HEADERS
        # ============================================================
        
        header_format = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'font_name': 'Arial',
            'font_color': colors['white'],
            'bg_color': colors['royal_blue'],
            'align': 'center',
            'valign': 'vcenter',
            'border': 2,
            'border_color': colors['navy'],
            'text_wrap': True,
            'top': 3,
            'bottom': 3,
            'top_color': colors['navy'],
            'bottom_color': colors['navy']
        })
        
        # Optimized column widths for professional appearance
        col_widths = [16, 45, 38, 20, 20, 20]
        
        for col_num, column in enumerate(columns):
            # Write header with emoji cleaned for Excel compatibility
            header_text = column['label']
            worksheet.write(7, col_num, header_text, header_format)
            worksheet.set_column(col_num, col_num, col_widths[col_num])
        
        # ============================================================
        # SECTION 3: BEAUTIFUL DATA ROWS
        # ============================================================
        
        # Even row formats (White background)
        text_even = workbook.add_format({
            'font_size': 10,
            'font_name': 'Calibri',
            'font_color': colors['charcoal'],
            'bg_color': colors['white'],
            'border': 1,
            'border_color': colors['border_light'],
            'valign': 'vcenter',
            'left': 1,
            'right': 1
        })
        
        currency_even = workbook.add_format({
            'font_size': 10,
            'font_name': 'Calibri',
            'num_format': '#,##0.00',
            'font_color': colors['charcoal'],
            'bg_color': colors['white'],
            'border': 1,
            'border_color': colors['border_light'],
            'align': 'right',
            'valign': 'vcenter'
        })
        
        # Odd row formats (Light grey background)
        text_odd = workbook.add_format({
            'font_size': 10,
            'font_name': 'Calibri',
            'font_color': colors['charcoal'],
            'bg_color': colors['snow'],
            'border': 1,
            'border_color': colors['border_light'],
            'valign': 'vcenter'
        })
        
        currency_odd = workbook.add_format({
            'font_size': 10,
            'font_name': 'Calibri',
            'num_format': '#,##0.00',
            'font_color': colors['charcoal'],
            'bg_color': colors['snow'],
            'border': 1,
            'border_color': colors['border_light'],
            'align': 'right',
            'valign': 'vcenter'
        })
        
        # Special formats for positive/negative values
        # Debit (Positive) - Emerald Green
        debit_even = workbook.add_format({
            'font_size': 10,
            'font_name': 'Calibri',
            'num_format': '#,##0.00',
            'font_color': colors['emerald'],
            'bold': True,
            'bg_color': colors['white'],
            'border': 1,
            'border_color': colors['border_light'],
            'align': 'right',
            'valign': 'vcenter'
        })
        
        debit_odd = workbook.add_format({
            'font_size': 10,
            'font_name': 'Calibri',
            'num_format': '#,##0.00',
            'font_color': colors['emerald'],
            'bold': True,
            'bg_color': colors['snow'],
            'border': 1,
            'border_color': colors['border_light'],
            'align': 'right',
            'valign': 'vcenter'
        })
        
        # Credit (Negative) - Ruby Red
        credit_even = workbook.add_format({
            'font_size': 10,
            'font_name': 'Calibri',
            'num_format': '#,##0.00',
            'font_color': colors['ruby'],
            'bold': True,
            'bg_color': colors['white'],
            'border': 1,
            'border_color': colors['border_light'],
            'align': 'right',
            'valign': 'vcenter'
        })
        
        credit_odd = workbook.add_format({
            'font_size': 10,
            'font_name': 'Calibri',
            'num_format': '#,##0.00',
            'font_color': colors['ruby'],
            'bold': True,
            'bg_color': colors['snow'],
            'border': 1,
            'border_color': colors['border_light'],
            'align': 'right',
            'valign': 'vcenter'
        })
        
        # TOTAL ROW - Premium Gold Theme
        total_text = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'font_name': 'Arial',
            'font_color': colors['navy'],
            'bg_color': colors['total_gold'],
            'border': 2,
            'border_color': colors['gold'],
            'top': 3,
            'top_color': colors['navy'],
            'valign': 'vcenter'
        })
        
        total_currency = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'font_name': 'Arial',
            'num_format': '#,##0.00',
            'font_color': colors['navy'],
            'bg_color': colors['total_gold'],
            'border': 2,
            'border_color': colors['gold'],
            'top': 3,
            'top_color': colors['navy'],
            'align': 'right',
            'valign': 'vcenter'
        })
        
        # Write data rows with beautiful formatting
        row_num = 8  # Start after headers
        
        for data_row in data:
            is_total = data_row.get('is_total_row', 0)
            is_even = (row_num - 8) % 2 == 0
            
            # Set row height
            worksheet.set_row(row_num, 28 if is_total else 22)
            
            for col_num, column in enumerate(columns):
                fieldname = column['fieldname']
                value = data_row.get(fieldname, '')
                
                if is_total:
                    # TOTAL ROW - Special formatting
                    if column['fieldtype'] == 'Currency' and value != '':
                        worksheet.write_number(row_num, col_num, flt(value), total_currency)
                    else:
                        # Clean up total row text
                        display_value = str(value).replace('<b>', '').replace('</b>', '')
                        worksheet.write(row_num, col_num, display_value, total_text)
                else:
                    # REGULAR DATA ROWS
                    if column['fieldtype'] == 'Currency' and value != '':
                        # Smart color-coding based on column and value
                        if fieldname == 'balance':
                            if flt(value) > 0:
                                fmt = debit_even if is_even else debit_odd
                            elif flt(value) < 0:
                                fmt = credit_even if is_even else credit_odd
                            else:
                                fmt = currency_even if is_even else currency_odd
                        elif fieldname == 'net_debit' and flt(value) > 0:
                            fmt = debit_even if is_even else debit_odd
                        elif fieldname == 'net_credit' and flt(value) > 0:
                            fmt = credit_even if is_even else credit_odd
                        else:
                            fmt = currency_even if is_even else currency_odd
                        
                        worksheet.write_number(row_num, col_num, flt(value), fmt)
                    else:
                        # Text fields
                        fmt = text_even if is_even else text_odd
                        worksheet.write(row_num, col_num, str(value), fmt)
            
            row_num += 1
        
        # ============================================================
        # SECTION 4: EXECUTIVE SUMMARY DASHBOARD
        # ============================================================
        
        summary_data = get_report_summary(data, filters)
        
        # Add elegant spacing
        row_num += 3
        
        # Summary section title with gradient effect
        summary_title = workbook.add_format({
            'bold': True,
            'font_size': 15,
            'font_name': 'Arial',
            'font_color': colors['white'],
            'bg_color': colors['royal_blue'],
            'align': 'center',
            'valign': 'vcenter',
            'border': 2,
            'border_color': colors['navy']
        })
        
        worksheet.set_row(row_num, 32)
        worksheet.merge_range(row_num, 0, row_num, 5, '📈 EXECUTIVE SUMMARY', summary_title)
        row_num += 1
        
        # Beautiful summary card formats
        card_label = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'font_name': 'Arial',
            'font_color': colors['navy'],
            'bg_color': colors['ice_blue'],
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'border_color': colors['sky_blue']
        })
        
        card_value = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'font_name': 'Arial',
            'font_color': colors['navy'],
            'bg_color': colors['white'],
            'align': 'center',
            'valign': 'vcenter',
            'border': 2,
            'border_color': colors['sky_blue'],
            'num_format': '#,##0.00'
        })
        
        # Create 2x2 dashboard grid
        summary_row = row_num
        for i, summary in enumerate(summary_data):
            col_offset = (i % 2) * 3
            row_offset = summary_row + (i // 2) * 3
            
            worksheet.set_row(row_offset, 24)
            worksheet.set_row(row_offset + 1, 32)
            worksheet.set_row(row_offset + 2, 4)  # Spacer
            
            # Card label
            worksheet.merge_range(
                row_offset, col_offset,
                row_offset, col_offset + 2,
                summary.get('label', ''),
                card_label
            )
            
            # Card value
            value = summary.get('value', 0)
            worksheet.merge_range(
                row_offset + 1, col_offset,
                row_offset + 1, col_offset + 2,
                flt(value),
                card_value
            )
        
        # ============================================================
        # SECTION 5: PROFESSIONAL FOOTER
        # ============================================================
        
        footer_row = summary_row + 7
        
        footer_format = workbook.add_format({
            'italic': True,
            'font_size': 9,
            'font_name': 'Arial',
            'font_color': colors['slate'],
            'bg_color': colors['pearl'],
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'border_color': colors['silver']
        })
        
        from datetime import datetime
        footer_text = f"Report Generated: {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')} | Powered by ERPNext & Value Impacts Consulting"
        
        worksheet.set_row(footer_row, 22)
        worksheet.merge_range(footer_row, 0, footer_row, 5, footer_text, footer_format)
        
        # ============================================================
        # SECTION 6: EXCEL MAGIC - Advanced Features
        # ============================================================
        
        # Freeze panes at header row
        worksheet.freeze_panes(8, 0)
        
        # Auto-filter on header row
        worksheet.autofilter(7, 0, row_num - 1, 5)
        
        # Print settings for professional output
        worksheet.set_landscape()
        worksheet.set_paper(9)  # A4
        worksheet.fit_to_pages(1, 0)  # Fit width to 1 page
        
        # Premium margins
        worksheet.set_margins(left=0.6, right=0.6, top=0.8, bottom=0.8)
        
        # Page header and footer
        company_name = filters.get("company", "")
        worksheet.set_header(f'&L&"Arial,Bold"&12{company_name}&R&"Arial"&10Page &P of &N')
        worksheet.set_footer('&C&"Arial,Italic"&9Trial Balance Report - Confidential')
        
        # Repeat header row on every printed page
        worksheet.repeat_rows(7)
    
    # ============================================================
    # GENERATE FILE
    # ============================================================
    
    xlsx_file = output.getvalue()
    
    # Professional filename with timestamp
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    company_safe = filters.get('company', 'Company').replace(' ', '_').replace('/', '_')
    
    frappe.response['filename'] = f"TB_{company_safe}_{filters.get('as_at_date')}_{timestamp}.xlsx"
    frappe.response['filecontent'] = xlsx_file
    frappe.response['type'] = 'binary'
    frappe.response['content_type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    
    return


# Override the default Excel export
def get_xlsx_data(columns, data):
    """Override default Excel export to use custom format"""
    return None  # This will trigger the custom download button instead