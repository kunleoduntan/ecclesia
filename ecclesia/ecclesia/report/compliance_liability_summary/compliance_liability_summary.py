# ecclesia/ecclesia/report/compliance_liability_summary/compliance_liability_summary.py

import frappe
from frappe import _
from frappe.utils import getdate, add_days, today, flt
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import openpyxl
import io

def execute(filters=None):
    if not filters:
        filters = {}
    
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    summary = get_summary(data)
    
    return columns, data, None, chart, summary

def get_columns():
    return [
        {
            "fieldname": "obligation_type",
            "label": _("Obligation"),
            "fieldtype": "Data",
            "width": 160,
            "bold": 1
        },
        {
            "fieldname": "period_label",
            "label": _("Period"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "company",
            "label": _("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "width": 180
        },
        {
            "fieldname": "total_liability",
            "label": _("Liability (₦)"),
            "fieldtype": "Currency",
            "width": 140,
            "precision": 2,
            "align": "right"
        },
        {
            "fieldname": "total_allocated",
            "label": _("Paid (₦)"),
            "fieldtype": "Currency",
            "width": 140,
            "precision": 2,
            "align": "right"
        },
        {
            "fieldname": "balance_due",
            "label": _("Balance (₦)"),
            "fieldtype": "Currency",
            "width": 140,
            "precision": 2,
            "align": "right",
            "bold": 1
        },
        {
            "fieldname": "status_display",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "due_date",
            "label": _("Due Date"),
            "fieldtype": "Date",
            "width": 120
        },
        {
            "fieldname": "is_overdue_display",
            "label": _("Overdue"),
            "fieldtype": "Data",
            "width": 100
        }
    ]

def get_data(filters):
    conditions = build_conditions(filters)
    
    data = frappe.db.sql("""
        SELECT 
            obligation_type,
            period_label,
            company,
            total_liability,
            total_allocated,
            balance_due,
            status,
            due_date,
            is_overdue,
            name,
            creation
        FROM `tabCompliance Liability Ledger`
        WHERE {conditions}
        ORDER BY due_date ASC, obligation_type ASC
    """.format(conditions=conditions), filters, as_dict=1)
    
    for row in data:
        row["status_display"] = get_status_display(row)
        row["is_overdue_display"] = "🔴 Yes" if row.is_overdue else "✅ No"
        row["total_liability"] = flt(row.total_liability)
        row["total_allocated"] = flt(row.total_allocated)
        row["balance_due"] = flt(row.balance_due)
        
    return data

def build_conditions(filters):
    conditions = "1=1"
    
    if filters.get("company"):
        conditions += " AND company = %(company)s"
    
    if filters.get("obligation_type"):
        conditions += " AND obligation_type = %(obligation_type)s"
    
    if filters.get("period_label"):
        conditions += " AND period_label = %(period_label)s"
    
    if filters.get("status"):
        conditions += " AND status = %(status)s"
    
    if filters.get("from_date") and filters.get("to_date"):
        conditions += " AND due_date BETWEEN %(from_date)s AND %(to_date)s"
    
    if filters.get("show_overdue_only"):
        conditions += " AND is_overdue = 1"
    
    if filters.get("min_balance_amount"):
        conditions += " AND balance_due >= %(min_balance_amount)s"
    
    return conditions

def get_status_display(row):
    status_map = {
        "Open": "🟡 Open",
        "Partially Paid": "🟠 Partially Paid",
        "Fully Paid": "🟢 Fully Paid",
        "Overdue": "🔴 Overdue",
        "Reconciled": "🔄 Reconciled",
        "Exempt": "⚪ Exempt"
    }
    return status_map.get(row.status, row.status)

def get_chart(data):
    if not data:
        return None
        
    labels = []
    liability_values = []
    paid_values = []
    balance_values = []
    
    grouped = {}
    for row in data:
        key = row.obligation_type
        if key not in grouped:
            grouped[key] = {"liability": 0, "paid": 0, "balance": 0}
        grouped[key]["liability"] += row.total_liability or 0
        grouped[key]["paid"] += row.total_allocated or 0
        grouped[key]["balance"] += row.balance_due or 0
    
    for key, values in list(grouped.items())[:8]:
        labels.append(key[:12] + ("..." if len(key) > 12 else ""))
        liability_values.append(values["liability"])
        paid_values.append(values["paid"])
        balance_values.append(values["balance"])
    
    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": _("Liability"),
                    "values": liability_values,
                    "chartType": "bar",
                    "colors": ["#1e3a5f"]
                },
                {
                    "name": _("Paid"),
                    "values": paid_values,
                    "chartType": "bar",
                    "colors": ["#16a34a"]
                },
                {
                    "name": _("Balance"),
                    "values": balance_values,
                    "chartType": "bar",
                    "colors": ["#dc2626"]
                }
            ]
        },
        "type": "bar",
        "height": 300,
        "colors": ["#1e3a5f", "#16a34a", "#dc2626"]
    }

def get_summary(data):
    if not data:
        return []
    
    total_liability = sum(row.total_liability or 0 for row in data)
    total_paid = sum(row.total_allocated or 0 for row in data)
    total_balance = sum(row.balance_due or 0 for row in data)
    overdue_count = sum(1 for row in data if row.is_overdue)
    fully_paid_count = sum(1 for row in data if row.status == "Fully Paid")
    
    return [
        {
            "label": _("Total Liability"),
            "value": frappe.format_currency(total_liability, "NGN"),
            "indicator": "Blue"
        },
        {
            "label": _("Total Paid"),
            "value": frappe.format_currency(total_paid, "NGN"),
            "indicator": "Green"
        },
        {
            "label": _("Total Balance"),
            "value": frappe.format_currency(total_balance, "NGN"),
            "indicator": "Red" if total_balance > 0 else "Green"
        },
        {
            "label": _("Overdue Records"),
            "value": str(overdue_count),
            "indicator": "Red" if overdue_count > 0 else "Green"
        },
        {
            "label": _("Fully Paid"),
            "value": str(fully_paid_count),
            "indicator": "Green"
        }
    ]

@frappe.whitelist()
def export_to_excel(filters=None):
    """Export report data to Excel with professional formatting"""
    if not filters:
        filters = {}
    elif isinstance(filters, str):
        import json
        filters = json.loads(filters)
    
    columns, data, _, _, summary = execute(filters)
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Report Data"
    
    # Define styles
    header_font = Font(name='Arial', size=11, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='1E3A5F', end_color='1E3A5F', fill_type='solid')
    header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    
    status_colors = {
        "Fully Paid": "16a34a",
        "Paid": "16a34a",
        "Active": "16a34a",
        "Compliant": "16a34a",
        "Open": "0284c7",
        "Pending": "0284c7",
        "Partially Paid": "ea580c",
        "Expiring Soon": "ea580c",
        "Overdue": "dc2626",
        "Expired": "dc2626",
        "Referred": "dc2626",
        "High": "dc2626",
        "Critical": "dc2626"
    }
    
    # Write headers
    for col_idx, column in enumerate(columns, 1):
        cell = ws.cell(row=1, column=col_idx, value=column["label"])
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
    
    # Write data
    for row_idx, row in enumerate(data, 2):
        for col_idx, column in enumerate(columns, 1):
            fieldname = column["fieldname"]
            value = row.get(fieldname, "")
            
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            
            if column.get("align") == "right":
                cell.alignment = Alignment(horizontal='right')
            elif column.get("align") == "center":
                cell.alignment = Alignment(horizontal='center')
            else:
                cell.alignment = Alignment(horizontal='left')
            
            if fieldname in ["status", "status_display", "overall_status"]:
                for status, color in status_colors.items():
                    if status in str(value):
                        cell.font = Font(color=color, bold=True)
                        break
            
            if fieldname == "balance_due" and value:
                if value > 0:
                    cell.font = Font(color='DC2626', bold=True)
                elif value == 0:
                    cell.font = Font(color='16A34A')
            
            if fieldname == "risk_rating":
                if value == "Low":
                    cell.font = Font(color='16A34A')
                elif value == "Medium":
                    cell.font = Font(color='F59E0B')
                elif value in ["High", "PEP — High"]:
                    cell.font = Font(color='DC2626', bold=True)
                elif value == "Sanctioned — Blocked":
                    cell.font = Font(color='991B1B', bold=True)
                    cell.fill = PatternFill(start_color='FEE2E2', end_color='FEE2E2', fill_type='solid')
    
    # Auto-size columns
    for col_idx in range(1, len(columns) + 1):
        column_letter = get_column_letter(col_idx)
        max_length = 0
        for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=col_idx, max_col=col_idx):
            for cell in row:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass
        adjusted_width = min(max_length + 5, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    # Add summary sheet
    summary_sheet = wb.create_sheet("Summary")
    summary_sheet.cell(row=1, column=1, value="Report Summary")
    summary_sheet.cell(row=1, column=1).font = Font(size=14, bold=True)
    
    if summary:
        for idx, item in enumerate(summary, 2):
            summary_sheet.cell(row=idx, column=1, value=item["label"])
            summary_sheet.cell(row=idx, column=2, value=item["value"])
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    frappe.response["filename"] = f"Compliance_Liability_Summary_{getdate()}.xlsx"
    frappe.response["filecontent"] = output.getvalue()
    frappe.response["type"] = "download"