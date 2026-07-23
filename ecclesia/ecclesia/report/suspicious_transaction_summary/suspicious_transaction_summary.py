# ecclesia/ecclesia/report/suspicious_transaction_summary/suspicious_transaction_summary.py

import frappe
from frappe import _
from frappe.utils import getdate, flt
from openpyxl.styles import Font, PatternFill, Alignment
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
            "fieldname": "str_title",
            "label": _("STR Title"),
            "fieldtype": "Data",
            "width": 200,
            "bold": 1
        },
        {
            "fieldname": "report_type",
            "label": _("Report Type"),
            "fieldtype": "Data",
            "width": 180
        },
        {
            "fieldname": "party_name",
            "label": _("Counterparty"),
            "fieldtype": "Data",
            "width": 160
        },
        {
            "fieldname": "transaction_amount",
            "label": _("Amount (₦)"),
            "fieldtype": "Currency",
            "width": 140,
            "precision": 2,
            "align": "right"
        },
        {
            "fieldname": "transaction_date",
            "label": _("Transaction Date"),
            "fieldtype": "Date",
            "width": 120
        },
        {
            "fieldname": "suspicious_indicators",
            "label": _("Indicator"),
            "fieldtype": "Data",
            "width": 180
        },
        {
            "fieldname": "status_display",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 160
        },
        {
            "fieldname": "nfiu_submitted_display",
            "label": _("NFIU Submitted"),
            "fieldtype": "Data",
            "width": 120
        }
    ]

def get_data(filters):
    conditions = build_conditions(filters)
    
    data = frappe.db.sql("""
        SELECT 
            str_title,
            report_type,
            party_name,
            transaction_amount,
            transaction_date,
            suspicious_indicators,
            status,
            nfiu_submitted,
            nfiu_submission_date,
            nfiu_reference,
            name,
            report_date
        FROM `tabSuspicious Transaction Report`
        WHERE {conditions}
        ORDER BY transaction_date DESC, report_date DESC
    """.format(conditions=conditions), filters, as_dict=1)
    
    for row in data:
        row["status_display"] = get_status_display(row)
        row["nfiu_submitted_display"] = "✅ Yes" if row.nfiu_submitted else "⬜ No"
        row["transaction_amount"] = flt(row.transaction_amount)
    
    return data

def build_conditions(filters):
    conditions = "1=1"
    
    if filters.get("company"):
        conditions += " AND company = %(company)s"
    
    if filters.get("report_type"):
        conditions += " AND report_type = %(report_type)s"
    
    if filters.get("status"):
        conditions += " AND status = %(status)s"
    
    if filters.get("nfiu_submitted") is not None:
        conditions += " AND nfiu_submitted = %(nfiu_submitted)s"
    
    if filters.get("from_date") and filters.get("to_date"):
        conditions += " AND transaction_date BETWEEN %(from_date)s AND %(to_date)s"
    
    if filters.get("min_amount"):
        conditions += " AND transaction_amount >= %(min_amount)s"
    
    if filters.get("suspicious_indicators"):
        conditions += " AND suspicious_indicators LIKE %(suspicious_indicators)s"
    
    return conditions

def get_status_display(row):
    status_map = {
        "Draft": "📄 Draft",
        "Under Review": "🔍 Under Review",
        "Submitted to NFIU": "📤 Submitted to NFIU",
        "Closed — No Action": "✅ Closed — No Action",
        "Referred to Enforcement": "🚨 Referred to Enforcement"
    }
    return status_map.get(row.status, row.status)

def get_chart(data):
    if not data:
        return None
    
    status_counts = {}
    for row in data:
        status = row.status
        if status not in status_counts:
            status_counts[status] = 0
        status_counts[status] += 1
    
    labels = list(status_counts.keys())
    values = list(status_counts.values())
    
    colors = {
        "Draft": "#94a3b8",
        "Under Review": "#f59e0b",
        "Submitted to NFIU": "#2563eb",
        "Closed — No Action": "#16a34a",
        "Referred to Enforcement": "#dc2626"
    }
    
    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": _("Reports"),
                    "values": values,
                    "chartType": "bar",
                    "colors": [colors.get(label, "#94a3b8") for label in labels]
                }
            ]
        },
        "type": "bar",
        "height": 300
    }

def get_summary(data):
    if not data:
        return []
    
    total = len(data)
    submitted_to_nfiu = sum(1 for row in data if row.nfiu_submitted)
    under_review = sum(1 for row in data if row.status == "Under Review")
    referred = sum(1 for row in data if row.status == "Referred to Enforcement")
    total_amount = sum(row.transaction_amount or 0 for row in data)
    
    return [
        {
            "label": _("Total Reports"),
            "value": str(total),
            "indicator": "Blue"
        },
        {
            "label": _("Submitted to NFIU"),
            "value": str(submitted_to_nfiu),
            "indicator": "Green" if submitted_to_nfiu > 0 else "Blue"
        },
        {
            "label": _("Under Review"),
            "value": str(under_review),
            "indicator": "Orange" if under_review > 0 else "Green"
        },
        {
            "label": _("Referred to Enforcement"),
            "value": str(referred),
            "indicator": "Red" if referred > 0 else "Green"
        },
        {
            "label": _("Total Amount"),
            "value": frappe.format_currency(total_amount, "NGN"),
            "indicator": "Blue"
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
    ws.title = "Suspicious Transaction Summary"
    
    header_font = Font(name='Arial', size=11, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='B91C1C', end_color='B91C1C', fill_type='solid')
    header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    
    for col_idx, column in enumerate(columns, 1):
        cell = ws.cell(row=1, column=col_idx, value=column["label"])
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
    
    for row_idx, row in enumerate(data, 2):
        for col_idx, column in enumerate(columns, 1):
            fieldname = column["fieldname"]
            value = row.get(fieldname, "")
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            
            if column.get("align") == "right":
                cell.alignment = Alignment(horizontal='right')
            
            if fieldname == "status_display":
                if "Referred" in str(value):
                    cell.font = Font(color='DC2626', bold=True)
                elif "Submitted" in str(value):
                    cell.font = Font(color='2563EB', bold=True)
                elif "Closed" in str(value):
                    cell.font = Font(color='16A34A')
            
            if fieldname == "transaction_amount" and value:
                if value > 10000000:
                    cell.font = Font(color='DC2626', bold=True)
                elif value > 5000000:
                    cell.font = Font(color='EA580C')
    
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
    
    summary_sheet = wb.create_sheet("Summary")
    summary_sheet.cell(row=1, column=1, value="Suspicious Transaction Summary")
    summary_sheet.cell(row=1, column=1).font = Font(size=14, bold=True)
    
    if summary:
        for idx, item in enumerate(summary, 2):
            summary_sheet.cell(row=idx, column=1, value=item["label"])
            summary_sheet.cell(row=idx, column=2, value=item["value"])
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    frappe.response["filename"] = f"Suspicious_Transaction_Summary_{getdate()}.xlsx"
    frappe.response["filecontent"] = output.getvalue()
    frappe.response["type"] = "download"