# ecclesia/ecclesia/report/license_expiry_report/license_expiry_report.py

import frappe
from frappe import _
from frappe.utils import getdate, today, flt
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
            "fieldname": "license_name",
            "label": _("License Name"),
            "fieldtype": "Data",
            "width": 200,
            "bold": 1
        },
        {
            "fieldname": "license_number",
            "label": _("License Number"),
            "fieldtype": "Data",
            "width": 160
        },
        {
            "fieldname": "license_type",
            "label": _("License Type"),
            "fieldtype": "Data",
            "width": 160
        },
        {
            "fieldname": "issuing_authority",
            "label": _("Authority"),
            "fieldtype": "Data",
            "width": 160
        },
        {
            "fieldname": "current_expiry_date",
            "label": _("Expiry Date"),
            "fieldtype": "Date",
            "width": 120
        },
        {
            "fieldname": "days_to_expiry",
            "label": _("Days to Expiry"),
            "fieldtype": "Int",
            "width": 120,
            "align": "center"
        },
        {
            "fieldname": "status_display",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "assigned_to",
            "label": _("Responsible Person"),
            "fieldtype": "Data",
            "width": 160
        }
    ]

def get_data(filters):
    conditions = build_conditions(filters)
    today_date = today()
    
    data = frappe.db.sql("""
        SELECT 
            license_name,
            license_number,
            license_type,
            issuing_authority,
            current_expiry_date,
            status,
            assigned_to,
            name,
            renewal_cost
        FROM `tabLicense Management`
        WHERE {conditions}
        ORDER BY current_expiry_date ASC, status ASC
    """.format(conditions=conditions), filters, as_dict=1)
    
    for row in data:
        if row.current_expiry_date:
            expiry = getdate(row.current_expiry_date)
            today_dt = getdate(today_date)
            row["days_to_expiry"] = (expiry - today_dt).days
        else:
            row["days_to_expiry"] = None
        
        row["status_display"] = get_status_display(row)
    
    return data

def build_conditions(filters):
    conditions = "1=1"
    
    if filters.get("company"):
        conditions += " AND company = %(company)s"
    
    if filters.get("license_type"):
        conditions += " AND license_type = %(license_type)s"
    
    if filters.get("issuing_authority"):
        conditions += " AND issuing_authority = %(issuing_authority)s"
    
    if filters.get("status"):
        conditions += " AND status = %(status)s"
    
    if filters.get("expiring_within_days"):
        days = int(filters.get("expiring_within_days"))
        conditions += f" AND current_expiry_date IS NOT NULL"
        conditions += f" AND DATEDIFF(current_expiry_date, CURDATE()) <= {days}"
        conditions += f" AND DATEDIFF(current_expiry_date, CURDATE()) >= 0"
    
    if filters.get("show_expired_only"):
        conditions += " AND current_expiry_date IS NOT NULL"
        conditions += " AND DATEDIFF(current_expiry_date, CURDATE()) < 0"
    
    if filters.get("assigned_to"):
        conditions += " AND assigned_to = %(assigned_to)s"
    
    return conditions

def get_status_display(row):
    if not row.current_expiry_date:
        return "⚪ No Expiry Set"
    
    days = row.days_to_expiry
    if days is None:
        return "⚪ No Expiry Set"
    
    if days < 0:
        return "🔴 Expired"
    elif days <= 7:
        return "🔴 Expires in 7 days"
    elif days <= 30:
        return "🟠 Expires in 30 days"
    elif days <= 60:
        return "🟡 Expires in 60 days"
    elif days <= 90:
        return "🟡 Expires in 90 days"
    else:
        return "🟢 Active"

def get_chart(data):
    if not data:
        return None
    
    status_counts = {
        "Active": 0,
        "Expiring Soon": 0,
        "Expired": 0
    }
    
    for row in data:
        if row.days_to_expiry is None:
            continue
        if row.days_to_expiry < 0:
            status_counts["Expired"] += 1
        elif row.days_to_expiry <= 30:
            status_counts["Expiring Soon"] += 1
        else:
            status_counts["Active"] += 1
    
    labels = list(status_counts.keys())
    values = list(status_counts.values())
    
    colors = {
        "Active": "#16a34a",
        "Expiring Soon": "#f59e0b",
        "Expired": "#dc2626"
    }
    
    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": _("Licenses"),
                    "values": values,
                    "chartType": "pie",
                    "colors": [colors.get(label, "#94a3b8") for label in labels]
                }
            ]
        },
        "type": "pie",
        "height": 300
    }

def get_summary(data):
    if not data:
        return []
    
    total = len(data)
    expired = sum(1 for row in data if row.days_to_expiry is not None and row.days_to_expiry < 0)
    expiring_7 = sum(1 for row in data if row.days_to_expiry is not None and 0 <= row.days_to_expiry <= 7)
    expiring_30 = sum(1 for row in data if row.days_to_expiry is not None and 8 <= row.days_to_expiry <= 30)
    active = sum(1 for row in data if row.days_to_expiry is not None and row.days_to_expiry > 30)
    
    return [
        {
            "label": _("Total Licenses"),
            "value": str(total),
            "indicator": "Blue"
        },
        {
            "label": _("Active"),
            "value": str(active),
            "indicator": "Green"
        },
        {
            "label": _("Expiring in 7 days"),
            "value": str(expiring_7),
            "indicator": "Red" if expiring_7 > 0 else "Green"
        },
        {
            "label": _("Expiring in 30 days"),
            "value": str(expiring_30),
            "indicator": "Orange" if expiring_30 > 0 else "Green"
        },
        {
            "label": _("Expired"),
            "value": str(expired),
            "indicator": "Red" if expired > 0 else "Green"
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
    ws.title = "License Expiry Report"
    
    header_font = Font(name='Arial', size=11, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='F59E0B', end_color='F59E0B', fill_type='solid')
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
            elif column.get("align") == "center":
                cell.alignment = Alignment(horizontal='center')
            
            if fieldname == "days_to_expiry" and value is not None:
                if value < 0:
                    cell.font = Font(color='DC2626', bold=True)
                elif value <= 7:
                    cell.font = Font(color='DC2626', bold=True)
                elif value <= 30:
                    cell.font = Font(color='EA580C', bold=True)
                elif value <= 60:
                    cell.font = Font(color='F59E0B')
            
            if fieldname == "status_display":
                if "Expired" in str(value) or "Expires in 7" in str(value):
                    cell.font = Font(color='DC2626', bold=True)
                elif "Expires in 30" in str(value):
                    cell.font = Font(color='EA580C', bold=True)
                elif "Active" in str(value):
                    cell.font = Font(color='16A34A')
    
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
    summary_sheet.cell(row=1, column=1, value="License Expiry Summary")
    summary_sheet.cell(row=1, column=1).font = Font(size=14, bold=True)
    
    if summary:
        for idx, item in enumerate(summary, 2):
            summary_sheet.cell(row=idx, column=1, value=item["label"])
            summary_sheet.cell(row=idx, column=2, value=item["value"])
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    frappe.response["filename"] = f"License_Expiry_Report_{getdate()}.xlsx"
    frappe.response["filecontent"] = output.getvalue()
    frappe.response["type"] = "download"