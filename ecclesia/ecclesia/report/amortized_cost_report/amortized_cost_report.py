# ecclesia/ecclesia/report/amortized_cost_report/amortized_cost_report.py
# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, formatdate, flt, fmt_money, today
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
            "fieldname": "purchase_invoice",
            "label": _("Purchase Invoice"),
            "fieldtype": "Link",
            "options": "Purchase Invoice",
            "width": 160,
            "bold": 1
        },
        {
            "fieldname": "supplier",
            "label": _("Supplier"),
            "fieldtype": "Link",
            "options": "Supplier",
            "width": 160
        },
        {
            "fieldname": "custom_description",
            "label": _("Description"),
            "fieldtype": "Data",
            "width": 200
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
        ORDER BY pi.supplier, pi.custom_description, pi.posting_date, pi.name
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
                    "purchase_invoice": invoice.purchase_invoice,
                    "supplier": invoice.supplier,
                    "custom_description": invoice.custom_description,
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
                    "parent_row": None
                }
                
                data.append(row)
        else:
            row = {
                "purchase_invoice": invoice.purchase_invoice,
                "supplier": invoice.supplier,
                "custom_description": invoice.custom_description,
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
                "parent_row": None
            }
            data.append(row)
    
    return data

def build_conditions(filters):
    conditions = ""
    
    if filters.get("from_date") and filters.get("to_date"):
        conditions += " AND pi.posting_date BETWEEN %(from_date)s AND %(to_date)s"
    
    if filters.get("purchase_invoice"):
        conditions += " AND pi.name = %(purchase_invoice)s"
    
    if filters.get("supplier"):
        conditions += " AND pi.supplier = %(supplier)s"
    
    return conditions

def get_chart_data(data):
    if not data:
        return None
    
    supplier_totals = defaultdict(float)
    status_counts = {"Completed": 0, "Pending": 0, "Due Today": 0, "No Schedule": 0}
    
    for row in data:
        if row.get("amount"):
            supplier_totals[row["supplier"]] += flt(row["amount"])
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
    
    return {
        "data": {
            "labels": list(supplier_totals.keys())[:10],
            "datasets": [
                {
                    "name": _("Total Amount by Supplier"),
                    "values": list(supplier_totals.values())[:10],
                    "chartType": "bar"
                }
            ]
        },
        "type": "bar",
        "height": 300,
        "colors": ["#4f46e5", "#0891b2", "#7c3aed", "#059669", "#d97706", "#dc2626", "#f59e0b", "#8b5cf6", "#ec4899", "#14b8a6"]
    }

def get_summary_data(data):
    if not data:
        return []
    
    total_amount = sum(flt(row.get("amount", 0)) for row in data)
    total_balance = sum(flt(row.get("prepayment_balance", 0)) for row in data if row.get("prepayment_balance"))
    unique_invoices = len(set(row["purchase_invoice"] for row in data))
    unique_suppliers = len(set(row["supplier"] for row in data))
    completed = sum(1 for row in data if row["status"] == "Completed")
    pending = sum(1 for row in data if row["status"] in ["Pending", "Due Today"])
    no_schedule = sum(1 for row in data if row["status"] == "No Schedule")
    
    return [
        {
            "label": _("Total Invoices"),
            "value": str(unique_invoices),
            "indicator": "Blue"
        },
        {
            "label": _("Total Suppliers"),
            "value": str(unique_suppliers),
            "indicator": "Purple"
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
    """Export report data to Excel with professional formatting"""
    try:
        if not filters:
            filters = {}
        elif isinstance(filters, str):
            filters = json.loads(filters)
        
        columns = get_columns()
        data = get_data(filters)
        summary = get_summary_data(data)
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Amortized Cost Report"
        
        # Define styles
        title_font = Font(name='Calibri', size=16, bold=True, color='1E3A5F')
        subtitle_font = Font(name='Calibri', size=11, color='4B5563')
        header_font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='1E3A5F', end_color='1E3A5F', fill_type='solid')
        
        invoice_colors = [
            PatternFill(start_color='F0F9FF', end_color='F0F9FF', fill_type='solid'),
            PatternFill(start_color='F0FDF4', end_color='F0FDF4', fill_type='solid'),
            PatternFill(start_color='FEF7ED', end_color='FEF7ED', fill_type='solid'),
            PatternFill(start_color='F5F3FF', end_color='F5F3FF', fill_type='solid'),
        ]
        
        supplier_fill = PatternFill(start_color='DBEAFE', end_color='DBEAFE', fill_type='solid')
        description_fill = PatternFill(start_color='D1FAE5', end_color='D1FAE5', fill_type='solid')
        
        completed_fill = PatternFill(start_color='DCFCE7', end_color='DCFCE7', fill_type='solid')
        pending_fill = PatternFill(start_color='FEF3C7', end_color='FEF3C7', fill_type='solid')
        due_today_fill = PatternFill(start_color='FEE2E2', end_color='FEE2E2', fill_type='solid')
        no_schedule_fill = PatternFill(start_color='F3F4F6', end_color='F3F4F6', fill_type='solid')
        
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
        title_cell.value = "Amortized Cost Analysis Report"
        title_cell.font = title_font
        title_cell.alignment = Alignment(horizontal='center', vertical='center')
        ws.row_dimensions[1].height = 35
        
        ws.merge_cells('A2:M2')
        subtitle_cell = ws['A2']
        from_date = filters.get('from_date', 'N/A')
        to_date = filters.get('to_date', 'N/A')
        if from_date != 'N/A':
            from_date = formatdate(getdate(from_date))
        if to_date != 'N/A':
            to_date = formatdate(getdate(to_date))
        subtitle_cell.value = "Period: {} to {} | Generated: {}".format(
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
        
        # Data rows
        current_supplier = None
        current_description = None
        current_invoice = None
        invoice_counter = 0
        row_idx = header_row + 1
        
        for data_row in data:
            if data_row.get("purchase_invoice") != current_invoice:
                current_invoice = data_row.get("purchase_invoice")
                invoice_counter += 1
                current_row_color = invoice_colors[(invoice_counter - 1) % len(invoice_colors)]
            
            if data_row.get("supplier") != current_supplier:
                current_supplier = data_row.get("supplier")
                current_description = None
                
                ws.merge_cells('A{}:M{}'.format(row_idx, row_idx))
                supplier_cell = ws.cell(row=row_idx, column=1)
                supplier_cell.value = "Supplier: {}".format(current_supplier or 'N/A')
                supplier_cell.font = Font(name='Calibri', size=12, bold=True, color='1E40AF')
                supplier_cell.fill = supplier_fill
                supplier_cell.alignment = left_alignment
                supplier_cell.border = thin_border
                for col in range(1, 14):
                    ws.cell(row=row_idx, column=col).border = thin_border
                    ws.cell(row=row_idx, column=col).fill = supplier_fill
                ws.row_dimensions[row_idx].height = 28
                row_idx += 1
            
            if data_row.get("custom_description") != current_description:
                current_description = data_row.get("custom_description")
                
                ws.merge_cells('A{}:M{}'.format(row_idx, row_idx))
                desc_cell = ws.cell(row=row_idx, column=1)
                desc_cell.value = "  Description: {}".format(current_description or 'N/A')
                desc_cell.font = Font(name='Calibri', size=11, bold=True, color='065F46')
                desc_cell.fill = description_fill
                desc_cell.alignment = left_alignment
                desc_cell.border = thin_border
                for col in range(1, 14):
                    ws.cell(row=row_idx, column=col).border = thin_border
                    ws.cell(row=row_idx, column=col).fill = description_fill
                ws.row_dimensions[row_idx].height = 25
                row_idx += 1
            
            for col_idx, column in enumerate(columns, 1):
                fieldname = column["fieldname"]
                value = data_row.get(fieldname, "")
                
                if fieldname in ["amount", "prepayment_balance"] and value is not None:
                    value = flt(value)
                elif fieldname in ["custom_start_date", "custom_end_date", "date"] and value:
                    value = formatdate(getdate(value))
                
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.font = Font(name='Calibri', size=10)
                cell.border = thin_border
                cell.fill = current_row_color
                
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
                
                if data_row.get("is_new_invoice"):
                    cell.font = Font(name='Calibri', size=10, bold=True)
                
                if fieldname == "status":
                    if value == "Completed":
                        cell.fill = completed_fill
                        cell.font = Font(name='Calibri', size=10, color='16A34A', bold=True)
                    elif value == "Due Today":
                        cell.fill = due_today_fill
                        cell.font = Font(name='Calibri', size=10, color='DC2626', bold=True)
                    elif value == "Pending":
                        cell.fill = pending_fill
                        cell.font = Font(name='Calibri', size=10, color='D97706', bold=True)
                    elif value == "No Schedule":
                        cell.fill = no_schedule_fill
                        cell.font = Font(name='Calibri', size=10, color='6B7280', italic=True)
                
                if fieldname == "prepayment_balance" and value is not None:
                    if value > 0:
                        cell.font = Font(name='Calibri', size=10, color='16A34A', bold=True)
                    elif value < 0:
                        cell.font = Font(name='Calibri', size=10, color='DC2626', bold=True)
            
            ws.row_dimensions[row_idx].height = 22
            row_idx += 1
        
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
        
        ws.freeze_panes = 'A{}'.format(header_row + 1)
        ws.auto_filter.ref = 'A{}:M{}'.format(header_row, row_idx - 1)
        
        # Create Summary sheet
        summary_sheet = wb.create_sheet("Summary")
        create_summary_sheet(summary_sheet, summary, filters)
        
        # Create pivot by supplier
        pivot_sheet = wb.create_sheet("By Supplier")
        create_pivot_sheet(pivot_sheet, data)
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        frappe.response["filename"] = "Amortized_Cost_Report_{}.xlsx".format(getdate())
        frappe.response["filecontent"] = output.getvalue()
        frappe.response["type"] = "download"
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Export Excel Failed - Amortized Cost Report")
        frappe.throw(_("Failed to export Excel: {0}".format(str(e))))

def create_summary_sheet(ws, summary, filters):
    """Create a summary sheet with key metrics"""
    
    ws.merge_cells('A1:C1')
    ws['A1'].value = "Amortized Cost Summary"
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

def create_pivot_sheet(ws, data):
    """Create a pivot table by supplier"""
    
    ws.merge_cells('A1:D1')
    ws['A1'].value = "Amortized Cost by Supplier & Description"
    ws['A1'].font = Font(name='Calibri', size=14, bold=True, color='1E3A5F')
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 30
    
    pivot_headers = ["Supplier", "Description", "Total Amount", "Schedule Count"]
    header_fill = PatternFill(start_color='4F46E5', end_color='4F46E5', fill_type='solid')
    header_font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
    
    for col, header in enumerate(pivot_headers, 1):
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
    
    pivot_data = defaultdict(lambda: {"amount": 0, "count": 0})
    processed_invoices = set()
    
    for row in data:
        supplier = row.get("supplier", "N/A")
        description = row.get("custom_description", "N/A")
        invoice = row.get("purchase_invoice")
        
        if invoice and invoice not in processed_invoices:
            processed_invoices.add(invoice)
            key = (supplier, description)
            pivot_data[key]["amount"] += flt(row.get("amount", 0))
            pivot_data[key]["count"] += 1
    
    row_idx = 4
    current_supplier = None
    
    for (supplier, description), values in sorted(pivot_data.items()):
        if supplier != current_supplier:
            current_supplier = supplier
            ws.merge_cells('A{}:D{}'.format(row_idx, row_idx))
            supplier_cell = ws.cell(row=row_idx, column=1, value=supplier)
            supplier_cell.font = Font(name='Calibri', size=11, bold=True, color='1E40AF')
            supplier_cell.fill = PatternFill(start_color='DBEAFE', end_color='DBEAFE', fill_type='solid')
            for col in range(1, 5):
                ws.cell(row=row_idx, column=col).border = Border(
                    bottom=Side(style='thin', color='D1D5DB')
                )
            ws.row_dimensions[row_idx].height = 22
            row_idx += 1
        
        ws.cell(row=row_idx, column=1, value="")
        ws.cell(row=row_idx, column=2, value=description).font = Font(name='Calibri', size=10)
        ws.cell(row=row_idx, column=3, value=values["amount"]).number_format = '#,##0.00'
        ws.cell(row=row_idx, column=4, value=values["count"])
        
        for col in range(1, 5):
            ws.cell(row=row_idx, column=col).border = Border(
                bottom=Side(style='thin', color='E5E7EB')
            )
            if col in [3, 4]:
                ws.cell(row=row_idx, column=col).alignment = Alignment(horizontal='center')
        
        ws.row_dimensions[row_idx].height = 20
        row_idx += 1
    
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 30
    ws.column_dimensions['C'].width = 18
    ws.column_dimensions['D'].width = 15