# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

# ecclesia/ecclesia/report/amortized_cost_report_grouped_by_description/amortized_cost_report_grouped_by_description.py

import frappe
from frappe import _
from frappe.utils import getdate, formatdate, flt, fmt_money, today, now_datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import io
import json
from collections import defaultdict

def execute(filters=None):
    if not filters:
        filters = {}
    
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart_data(data)
    summary = get_summary_data(data)
    
    return columns, data, None, chart, summary

def get_columns():
    return [
        {
            "fieldname": "custom_description",
            "label": _("Description"),
            "fieldtype": "Data",
            "width": 200,
            "bold": 1
        },
        {
            "fieldname": "purchase_invoice",
            "label": _("Purchase Invoice"),
            "fieldtype": "Link",
            "options": "Purchase Invoice",
            "width": 160
        },
        {
            "fieldname": "supplier",
            "label": _("Supplier"),
            "fieldtype": "Link",
            "options": "Supplier",
            "width": 160
        },
        {
            "fieldname": "custom_start_date",
            "label": _("Start Date"),
            "fieldtype": "Date",
            "width": 110
        },
        {
            "fieldname": "custom_end_date",
            "label": _("End Date"),
            "fieldtype": "Date",
            "width": 110
        },
        {
            "fieldname": "custom_frequency",
            "label": _("Frequency"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "date",
            "label": _("Schedule Date"),
            "fieldtype": "Date",
            "width": 120
        },
        {
            "fieldname": "period",
            "label": _("Period"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "account_to_debit",
            "label": _("Account to Debit"),
            "fieldtype": "Link",
            "options": "Account",
            "width": 180
        },
        {
            "fieldname": "account_to_credit",
            "label": _("Account to Credit"),
            "fieldtype": "Link",
            "options": "Account",
            "width": 180
        },
        {
            "fieldname": "amount",
            "label": _("Amount"),
            "fieldtype": "Currency",
            "width": 130,
            "align": "right"
        },
        {
            "fieldname": "prepayment_balance",
            "label": _("Prepayment Balance"),
            "fieldtype": "Currency",
            "width": 140,
            "align": "right"
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 120
        }
    ]

def get_data(filters):
    conditions = build_conditions(filters)
    
    invoices = frappe.db.sql("""
        SELECT 
            pi.name as purchase_invoice,
            pi.supplier,
            pi.custom_description,
            pi.custom_start_date,
            pi.custom_end_date,
            pi.custom_frequency,
            pi.custom_is_amortized_cost,
            pi.grand_total,
            pi.posting_date
        FROM `tabPurchase Invoice` pi
        WHERE pi.custom_is_amortized_cost = 1
        AND pi.docstatus = 1
        {conditions}
        ORDER BY pi.custom_description, pi.supplier, pi.posting_date, pi.name
    """.format(conditions=conditions), filters, as_dict=1)
    
    data = []
    
    for invoice in invoices:
        schedules = frappe.db.sql("""
            SELECT 
                date,
                account_to_debit,
                account_to_credit,
                period,
                frequency,
                prepayment_balance,
                amount
            FROM `tabAmortization Schedule`
            WHERE parent = %s
            AND parenttype = 'Purchase Invoice'
            ORDER BY date
        """, invoice.purchase_invoice, as_dict=1)
        
        if schedules:
            for idx, schedule in enumerate(schedules):
                schedule_date = getdate(schedule.date)
                today_date = getdate(today())
                
                if schedule_date < today_date:
                    status = "Completed"
                elif schedule_date == today_date:
                    status = "Due Today"
                else:
                    status = "Pending"
                
                row = {
                    "custom_description": invoice.custom_description,
                    "purchase_invoice": invoice.purchase_invoice,
                    "supplier": invoice.supplier,
                    "custom_start_date": invoice.custom_start_date,
                    "custom_end_date": invoice.custom_end_date,
                    "custom_frequency": invoice.custom_frequency,
                    "date": schedule.date,
                    "period": schedule.period,
                    "account_to_debit": schedule.account_to_debit,
                    "account_to_credit": schedule.account_to_credit,
                    "amount": schedule.amount,
                    "prepayment_balance": schedule.prepayment_balance,
                    "status": status,
                    "is_new_invoice": (idx == 0),
                    "is_new_description": False
                }
                
                data.append(row)
        else:
            row = {
                "custom_description": invoice.custom_description,
                "purchase_invoice": invoice.purchase_invoice,
                "supplier": invoice.supplier,
                "custom_start_date": invoice.custom_start_date,
                "custom_end_date": invoice.custom_end_date,
                "custom_frequency": invoice.custom_frequency,
                "date": None,
                "period": None,
                "account_to_debit": None,
                "account_to_credit": None,
                "amount": None,
                "prepayment_balance": None,
                "status": "No Schedule",
                "is_new_invoice": True,
                "is_new_description": False
            }
            data.append(row)
    
    # Mark new description groups and calculate totals
    current_description = None
    description_totals = defaultdict(lambda: {"total": 0, "count": 0, "invoice_count": 0})
    processed_invoices = set()
    
    for row in data:
        if row["custom_description"] != current_description:
            current_description = row["custom_description"]
            row["is_new_description"] = True
        
        if row["purchase_invoice"] not in processed_invoices:
            processed_invoices.add(row["purchase_invoice"])
            description_totals[current_description]["invoice_count"] += 1
        
        if row.get("amount"):
            description_totals[current_description]["total"] += flt(row["amount"])
            description_totals[current_description]["count"] += 1
    
    # Add totals to each row
    for row in data:
        desc = row["custom_description"]
        if desc in description_totals:
            row["description_total"] = description_totals[desc]["total"]
            row["description_count"] = description_totals[desc]["count"]
            row["description_invoice_count"] = description_totals[desc]["invoice_count"]
    
    return data

def build_conditions(filters):
    conditions = ""
    
    if filters.get("from_date") and filters.get("to_date"):
        conditions += " AND pi.posting_date BETWEEN %(from_date)s AND %(to_date)s"
    
    if filters.get("purchase_invoice"):
        conditions += " AND pi.name = %(purchase_invoice)s"
    
    if filters.get("supplier"):
        conditions += " AND pi.supplier = %(supplier)s"
    
    if filters.get("custom_description"):
        conditions += " AND pi.custom_description LIKE %(custom_description)s"
        filters["custom_description"] = "%" + filters["custom_description"] + "%"
    
    return conditions

def get_chart_data(data):
    if not data:
        return None
    
    status_counts = defaultdict(int)
    
    for row in data:
        status_counts[row["status"]] += 1
    
    return {
        "data": {
            "labels": list(status_counts.keys()),
            "datasets": [
                {
                    "name": _("Schedule Status Distribution"),
                    "values": list(status_counts.values()),
                    "chartType": "pie"
                }
            ]
        },
        "type": "pie",
        "height": 300,
        "colors": ["#16a34a", "#d97706", "#dc2626", "#6b7280"]
    }

def get_summary_data(data):
    if not data:
        return []
    
    total_amount = sum(flt(row.get("amount", 0)) for row in data)
    total_balance = sum(flt(row.get("prepayment_balance", 0)) for row in data if row.get("prepayment_balance"))
    unique_invoices = len(set(row["purchase_invoice"] for row in data))
    unique_descriptions = len(set(row["custom_description"] for row in data))
    unique_suppliers = len(set(row["supplier"] for row in data))
    completed = sum(1 for row in data if row["status"] == "Completed")
    pending = sum(1 for row in data if row["status"] in ["Pending", "Due Today"])
    no_schedule = sum(1 for row in data if row["status"] == "No Schedule")
    
    return [
        {
            "label": _("Total Descriptions"),
            "value": str(unique_descriptions),
            "indicator": "Blue"
        },
        {
            "label": _("Total Invoices"),
            "value": str(unique_invoices),
            "indicator": "Purple"
        },
        {
            "label": _("Total Suppliers"),
            "value": str(unique_suppliers),
            "indicator": "Indigo"
        },
        {
            "label": _("Total Amortized Amount"),
            "value": fmt_money(total_amount, currency=frappe.defaults.get_global_default('currency')),
            "indicator": "Green"
        },
        {
            "label": _("Remaining Balance"),
            "value": fmt_money(total_balance, currency=frappe.defaults.get_global_default('currency')),
            "indicator": "Orange"
        },
        {
            "label": _("Completed Schedules"),
            "value": str(completed),
            "indicator": "Green"
        },
        {
            "label": _("Pending Schedules"),
            "value": str(pending),
            "indicator": "Red" if pending > 0 else "Green"
        },
        {
            "label": _("No Schedule"),
            "value": str(no_schedule),
            "indicator": "Grey"
        }
    ]

@frappe.whitelist()
def export_to_excel(filters=None):
    """Export report data to Excel with professional formatting grouped by description"""
    try:
        if not filters:
            filters = {}
        elif isinstance(filters, str):
            filters = json.loads(filters)
        
        # Get columns and data
        columns = get_columns()
        data = get_data(filters)
        summary = get_summary_data(data)
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Amortized by Description"
        
        # Define styles
        title_font = Font(name='Calibri', size=16, bold=True, color='FFFFFF')
        title_fill = PatternFill(start_color='1E3A5F', end_color='1E3A5F', fill_type='solid')
        subtitle_font = Font(name='Calibri', size=11, color='4B5563')
        header_font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='374151', end_color='374151', fill_type='solid')
        
        # Description group header colors
        description_colors = [
            PatternFill(start_color='DBEAFE', end_color='DBEAFE', fill_type='solid'),
            PatternFill(start_color='D1FAE5', end_color='D1FAE5', fill_type='solid'),
            PatternFill(start_color='FEF3C7', end_color='FEF3C7', fill_type='solid'),
            PatternFill(start_color='EDE9FE', end_color='EDE9FE', fill_type='solid'),
            PatternFill(start_color='FCE7F3', end_color='FCE7F3', fill_type='solid'),
            PatternFill(start_color='E0F2FE', end_color='E0F2FE', fill_type='solid'),
            PatternFill(start_color='FEE2E2', end_color='FEE2E2', fill_type='solid'),
            PatternFill(start_color='F3E8FF', end_color='F3E8FF', fill_type='solid'),
        ]
        
        description_font_colors = [
            '1E40AF', '065F46', '92400E', '5B21B6',
            '9D174D', '075985', '991B1B', '6B21A8',
        ]
        
        # Invoice row colors
        invoice_colors = [
            PatternFill(start_color='F8FAFC', end_color='F8FAFC', fill_type='solid'),
            PatternFill(start_color='F1F5F9', end_color='F1F5F9', fill_type='solid'),
        ]
        
        thin_border = Border(
            left=Side(style='thin', color='D1D5DB'),
            right=Side(style='thin', color='D1D5DB'),
            top=Side(style='thin', color='D1D5DB'),
            bottom=Side(style='thin', color='D1D5DB')
        )
        
        center_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        left_alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
        right_alignment = Alignment(horizontal='right', vertical='center')
        
        # Title section
        ws.merge_cells('A1:M1')
        title_cell = ws['A1']
        title_cell.value = "Amortized Cost Report - Grouped by Description"
        title_cell.font = title_font
        title_cell.fill = title_fill
        title_cell.alignment = Alignment(horizontal='center', vertical='center')
        ws.row_dimensions[1].height = 40
        
        ws.merge_cells('A2:M2')
        subtitle_cell = ws['A2']
        from_date = filters.get('from_date', 'N/A')
        to_date = filters.get('to_date', 'N/A')
        if from_date != 'N/A':
            from_date = formatdate(getdate(from_date))
        if to_date != 'N/A':
            to_date = formatdate(getdate(to_date))
        subtitle_cell.value = "Period: {} to {} | Generated: {} | Grouped by Description".format(
            from_date, to_date, formatdate(today())
        )
        subtitle_cell.font = subtitle_font
        subtitle_cell.alignment = Alignment(horizontal='center', vertical='center')
        ws.row_dimensions[2].height = 25
        
        # Headers
        header_row = 4
        for col_idx, column in enumerate(columns, 1):
            cell = ws.cell(row=header_row, column=col_idx, value=column["label"])
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_alignment
            cell.border = thin_border
        ws.row_dimensions[header_row].height = 30
        
        # Data rows with description grouping and demarcation
        current_description = None
        current_invoice = None
        description_counter = 0
        invoice_counter = 0
        row_idx = header_row + 1
        
        for data_row in data:
            # Check if new description group
            if data_row.get("custom_description") != current_description:
                # Add demarcation line before new description (except first)
                if current_description is not None:
                    ws.merge_cells('A{}:M{}'.format(row_idx, row_idx))
                    demarcation_cell = ws.cell(row=row_idx, column=1)
                    demarcation_cell.value = ""
                    demarcation_cell.fill = PatternFill(start_color='FFFFFF', end_color='FFFFFF', fill_type='solid')
                    for col in range(1, 14):
                        ws.cell(row=row_idx, column=col).border = Border(
                            top=Side(style='medium', color='94A3B8'),
                            bottom=Side(style='medium', color='94A3B8')
                        )
                    ws.row_dimensions[row_idx].height = 10
                    row_idx += 1
                
                current_description = data_row.get("custom_description")
                description_counter += 1
                current_invoice = None
                invoice_counter = 0
                
                color_idx = (description_counter - 1) % len(description_colors)
                desc_fill = description_colors[color_idx]
                desc_font_color = description_font_colors[color_idx]
                
                # Description group header
                ws.merge_cells('A{}:M{}'.format(row_idx, row_idx))
                desc_header_cell = ws.cell(row=row_idx, column=1)
                
                desc_total = data_row.get("description_total", 0)
                desc_invoice_count = data_row.get("description_invoice_count", 0)
                desc_schedule_count = data_row.get("description_count", 0)
                
                desc_header_cell.value = "Description: {} | Total Amount: {} | Invoices: {} | Schedules: {}".format(
                    current_description or 'N/A',
                    fmt_money(desc_total, currency=frappe.defaults.get_global_default('currency')),
                    desc_invoice_count,
                    desc_schedule_count
                )
                desc_header_cell.font = Font(name='Calibri', size=12, bold=True, color=desc_font_color)
                desc_header_cell.fill = desc_fill
                desc_header_cell.alignment = left_alignment
                desc_header_cell.border = thin_border
                
                for col in range(1, 14):
                    ws.cell(row=row_idx, column=col).border = thin_border
                    ws.cell(row=row_idx, column=col).fill = desc_fill
                
                ws.row_dimensions[row_idx].height = 30
                row_idx += 1
            
            # Check if new invoice
            if data_row.get("purchase_invoice") != current_invoice:
                current_invoice = data_row.get("purchase_invoice")
                invoice_counter += 1
                current_row_color = invoice_colors[(invoice_counter - 1) % len(invoice_colors)]
            
            # Data row
            for col_idx, column in enumerate(columns, 1):
                fieldname = column["fieldname"]
                value = data_row.get(fieldname, "")
                
                # Format values
                if fieldname in ["amount", "prepayment_balance"] and value is not None:
                    value = flt(value)
                elif fieldname in ["custom_start_date", "custom_end_date", "date"] and value:
                    value = formatdate(getdate(value))
                
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.font = Font(name='Calibri', size=10)
                cell.border = thin_border
                cell.fill = current_row_color
                
                # Align numbers right
                if fieldname in ["amount", "prepayment_balance"]:
                    cell.alignment = right_alignment
                    if value:
                        cell.number_format = '#,##0.00'
                elif column.get("align") == "right":
                    cell.alignment = right_alignment
                elif column.get("align") == "center":
                    cell.alignment = center_alignment
                else:
                    cell.alignment = left_alignment
                
                # Bold for new invoice first row
                if data_row.get("is_new_invoice"):
                    cell.font = Font(name='Calibri', size=10, bold=True)
                    cell.border = Border(
                        left=Side(style='thin', color='D1D5DB'),
                        right=Side(style='thin', color='D1D5DB'),
                        top=Side(style='medium', color='CBD5E1'),
                        bottom=Side(style='thin', color='D1D5DB')
                    )
                
                # Color code status
                if fieldname == "status":
                    if value == "Completed":
                        cell.fill = PatternFill(start_color='DCFCE7', end_color='DCFCE7', fill_type='solid')
                        cell.font = Font(name='Calibri', size=10, color='16A34A', bold=True)
                    elif value == "Due Today":
                        cell.fill = PatternFill(start_color='FEE2E2', end_color='FEE2E2', fill_type='solid')
                        cell.font = Font(name='Calibri', size=10, color='DC2626', bold=True)
                    elif value == "Pending":
                        cell.fill = PatternFill(start_color='FEF3C7', end_color='FEF3C7', fill_type='solid')
                        cell.font = Font(name='Calibri', size=10, color='D97706', bold=True)
                    elif value == "No Schedule":
                        cell.fill = PatternFill(start_color='F3F4F6', end_color='F3F4F6', fill_type='solid')
                        cell.font = Font(name='Calibri', size=10, color='6B7280', italic=True)
                
                # Highlight prepayment balance
                if fieldname == "prepayment_balance" and value is not None:
                    if value > 0:
                        cell.font = Font(name='Calibri', size=10, color='16A34A', bold=True)
                    elif value < 0:
                        cell.font = Font(name='Calibri', size=10, color='DC2626', bold=True)
                
                # Make description column bold and prominent
                if fieldname == "custom_description":
                    cell.font = Font(name='Calibri', size=10, bold=True, color='1E40AF')
            
            ws.row_dimensions[row_idx].height = 22
            row_idx += 1
        
        # Add final demarcation line
        if data:
            ws.merge_cells('A{}:M{}'.format(row_idx, row_idx))
            for col in range(1, 14):
                ws.cell(row=row_idx, column=col).border = Border(
                    top=Side(style='medium', color='94A3B8'),
                    bottom=Side(style='medium', color='94A3B8')
                )
            ws.row_dimensions[row_idx].height = 10
        
        # Auto-adjust column widths
        for col_idx in range(1, len(columns) + 1):
            column_letter = get_column_letter(col_idx)
            max_length = 0
            for row in range(header_row, row_idx):
                cell_value = ws.cell(row=row, column=col_idx).value
                if cell_value:
                    max_length = max(max_length, len(str(cell_value)))
            adjusted_width = min(max_length + 3, 45)
            ws.column_dimensions[column_letter].width = max(adjusted_width, 12)
        
        # Freeze panes
        ws.freeze_panes = 'A{}'.format(header_row + 1)
        
        # Add auto-filter
        ws.auto_filter.ref = 'A{}:M{}'.format(header_row, row_idx - 1)
        
        # Create Summary sheet
        summary_sheet = wb.create_sheet("Summary")
        create_summary_sheet(summary_sheet, summary, filters)
        
        # Create Description Analysis sheet
        analysis_sheet = wb.create_sheet("Description Analysis")
        create_description_analysis_sheet(analysis_sheet, data)
        
        # Save to bytes
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        # Set response for download
        frappe.response["filename"] = "Amortized_Cost_by_Description_{}.xlsx".format(getdate())
        frappe.response["filecontent"] = output.getvalue()
        frappe.response["type"] = "download"
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Export Excel Failed")
        frappe.throw(_("Failed to export Excel: {0}".format(str(e))))

def create_summary_sheet(ws, summary, filters):
    """Create a summary sheet with key metrics"""
    
    ws.merge_cells('A1:C1')
    ws['A1'].value = "Amortized Cost Summary - By Description"
    ws['A1'].font = Font(name='Calibri', size=16, bold=True, color='1E3A5F')
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 35
    
    ws.merge_cells('A2:C2')
    from_date = filters.get('from_date', 'N/A')
    to_date = filters.get('to_date', 'N/A')
    if from_date != 'N/A':
        from_date = formatdate(getdate(from_date))
    if to_date != 'N/A':
        to_date = formatdate(getdate(to_date))
    ws['A2'].value = "Report Period: {} to {}".format(from_date, to_date)
    ws['A2'].font = Font(name='Calibri', size=11, color='6B7280')
    ws['A2'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[2].height = 25
    
    headers = ["Metric", "Value", "Indicator"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col, value=header)
        cell.font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
        cell.fill = PatternFill(start_color='1E3A5F', end_color='1E3A5F', fill_type='solid')
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = Border(
            left=Side(style='thin', color='D1D5DB'),
            right=Side(style='thin', color='D1D5DB'),
            top=Side(style='thin', color='D1D5DB'),
            bottom=Side(style='thin', color='D1D5DB')
        )
    ws.row_dimensions[4].height = 25
    
    if summary:
        for idx, item in enumerate(summary, 5):
            label_cell = ws.cell(row=idx, column=1, value=item["label"])
            value_cell = ws.cell(row=idx, column=2, value=item["value"])
            
            label_cell.font = Font(name='Calibri', size=11, bold=True)
            label_cell.border = Border(
                left=Side(style='thin', color='D1D5DB'),
                right=Side(style='thin', color='D1D5DB'),
                bottom=Side(style='thin', color='D1D5DB')
            )
            
            value_cell.font = Font(name='Calibri', size=11)
            value_cell.alignment = Alignment(horizontal='right')
            value_cell.border = Border(
                left=Side(style='thin', color='D1D5DB'),
                right=Side(style='thin', color='D1D5DB'),
                bottom=Side(style='thin', color='D1D5DB')
            )
            
            indicator_color = {
                "Blue": "2563EB",
                "Green": "16A34A",
                "Red": "DC2626",
                "Orange": "EA580C",
                "Purple": "7C3AED",
                "Indigo": "4F46E5",
                "Grey": "6B7280"
            }.get(item.get("indicator", ""), "374151")
            
            indicator_cell = ws.cell(row=idx, column=3, value="●")
            indicator_cell.font = Font(name='Calibri', size=14, color=indicator_color)
            indicator_cell.alignment = Alignment(horizontal='center', vertical='center')
            indicator_cell.border = Border(
                left=Side(style='thin', color='D1D5DB'),
                right=Side(style='thin', color='D1D5DB'),
                bottom=Side(style='thin', color='D1D5DB')
            )
            
            ws.row_dimensions[idx].height = 25
    
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 25
    ws.column_dimensions['C'].width = 12

def create_description_analysis_sheet(ws, data):
    """Create detailed analysis by description"""
    
    ws.merge_cells('A1:G1')
    ws['A1'].value = "Detailed Analysis by Description"
    ws['A1'].font = Font(name='Calibri', size=14, bold=True, color='1E3A5F')
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 30
    
    headers = [
        "Description",
        "Total Amount",
        "Invoices",
        "Schedules",
        "Completed",
        "Pending",
        "Status"
    ]
    
    header_fill = PatternFill(start_color='4F46E5', end_color='4F46E5', fill_type='solid')
    header_font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = Border(
            left=Side(style='thin', color='D1D5DB'),
            right=Side(style='thin', color='D1D5DB'),
            top=Side(style='thin', color='D1D5DB'),
            bottom=Side(style='thin', color='D1D5DB')
        )
    ws.row_dimensions[3].height = 25
    
    # Aggregate data by description
    desc_data = defaultdict(lambda: {
        "total": 0, "invoices": set(), "schedules": 0,
        "completed": 0, "pending": 0
    })
    
    for row in data:
        desc = row.get("custom_description", "N/A")
        desc_data[desc]["total"] += flt(row.get("amount", 0))
        desc_data[desc]["invoices"].add(row.get("purchase_invoice"))
        desc_data[desc]["schedules"] += 1
        
        if row["status"] == "Completed":
            desc_data[desc]["completed"] += 1
        elif row["status"] in ["Pending", "Due Today"]:
            desc_data[desc]["pending"] += 1
    
    row_idx = 4
    for desc, values in sorted(desc_data.items()):
        ws.cell(row=row_idx, column=1, value=desc).font = Font(name='Calibri', size=10, bold=True)
        ws.cell(row=row_idx, column=2, value=values["total"]).number_format = '#,##0.00'
        ws.cell(row=row_idx, column=3, value=len(values["invoices"]))
        ws.cell(row=row_idx, column=4, value=values["schedules"])
        ws.cell(row=row_idx, column=5, value=values["completed"])
        ws.cell(row=row_idx, column=6, value=values["pending"])
        
        # Status indicator
        pending_count = values["pending"]
        if pending_count == 0:
            status = "All Complete"
            status_color = '16A34A'
        elif pending_count <= 3:
            status = "In Progress"
            status_color = 'D97706'
        else:
            status = "Action Needed"
            status_color = 'DC2626'
        
        status_cell = ws.cell(row=row_idx, column=7, value=status)
        status_cell.font = Font(name='Calibri', size=10, bold=True, color=status_color)
        
        for col in range(1, 8):
            ws.cell(row=row_idx, column=col).border = Border(
                bottom=Side(style='thin', color='E5E7EB')
            )
            if col in [2, 3, 4, 5, 6]:
                ws.cell(row=row_idx, column=col).alignment = Alignment(horizontal='center')
        
        ws.row_dimensions[row_idx].height = 22
        row_idx += 1
    
    ws.column_dimensions['A'].width = 35
    ws.column_dimensions['B'].width = 18
    ws.column_dimensions['C'].width = 12
    ws.column_dimensions['D'].width = 12
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['F'].width = 12
    ws.column_dimensions['G'].width = 15