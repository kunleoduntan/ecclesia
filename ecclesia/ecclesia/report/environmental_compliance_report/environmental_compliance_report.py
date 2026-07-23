# ecclesia/ecclesia/report/environmental_compliance_report/environmental_compliance_report.py

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
            "fieldname": "permit_title",
            "label": _("Permit Title"),
            "fieldtype": "Data",
            "width": 200,
            "bold": 1
        },
        {
            "fieldname": "permit_type",
            "label": _("Permit Type"),
            "fieldtype": "Data",
            "width": 180
        },
        {
            "fieldname": "facility",
            "label": _("Facility"),
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
            "fieldname": "permit_number",
            "label": _("Permit Number"),
            "fieldtype": "Data",
            "width": 140
        },
        {
            "fieldname": "expiry_date",
            "label": _("Expiry Date"),
            "fieldtype": "Date",
            "width": 120
        },
        {
            "fieldname": "days_to_expiry",
            "label": _("Days"),
            "fieldtype": "Int",
            "width": 90,
            "align": "center"
        },
        {
            "fieldname": "status_display",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 150
        }
    ]

def get_data(filters):
    conditions = build_conditions(filters)
    today_date = today()
    
    data = frappe.db.sql("""
        SELECT 
            permit_title,
            permit_type,
            facility,
            issuing_authority,
            permit_number,
            expiry_date,
            status,
            name,
            issue_date,
            last_inspection_date,
            last_inspection_result
        FROM `tabEnvironmental Compliance Record`
        WHERE {conditions}
        ORDER BY expiry_date ASC, status ASC
    """.format(conditions=conditions), filters, as_dict=1)
    
    for row in data:
        if row.expiry_date:
            expiry = getdate(row.expiry_date)
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
    
    if filters.get("permit_type"):
        conditions += " AND permit_type = %(permit_type)s"
    
    if filters.get("issuing_authority"):
        conditions += " AND issuing_authority = %(issuing_authority)s"
    
    if filters.get("status"):
        conditions += " AND status = %(status)s"
    
    if filters.get("facility"):
        conditions += " AND facility LIKE %(facility)s"
    
    if filters.get("expiring_within_days"):
        days = int(filters.get("expiring_within_days"))
        conditions += f" AND expiry_date IS NOT NULL"
        conditions += f" AND DATEDIFF(expiry_date, CURDATE()) <= {days}"
        conditions += f" AND DATEDIFF(expiry_date, CURDATE()) >= 0"
    
    if filters.get("show_expired_only"):
        conditions += " AND expiry_date IS NOT NULL"
        conditions += " AND DATEDIFF(expiry_date, CURDATE()) < 0"
    
    if filters.get("last_inspection_result"):
        conditions += " AND last_inspection_result = %(last_inspection_result)s"
    
    return conditions

def get_status_display(row):
    if not row.expiry_date:
        return "⚪ No Expiry"
    
    days = row.days_to_expiry
    if days is None:
        return "⚪ No Expiry"
    
    if days < 0:
        return "🔴 Expired"
    elif days <= 30:
        return "🟠 Expiring Soon"
    elif days <= 90:
        return "🟡 Review Soon"
    else:
        return "🟢 Active"

def get_chart(data):
    if not data:
        return None
    
    permit_counts = {}
    for row in data:
        permit_type = row.permit_type
        if permit_type not in permit_counts:
            permit_counts[permit_type] = 0
        permit_counts[permit_type] += 1
    
    labels = list(permit_counts.keys())[:8]
    values = list(permit_counts.values())[:8]
    
    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": _("Permits"),
                    "values": values,
                    "chartType": "bar",
                    "colors": ["#16a34a", "#2563eb", "#f59e0b", "#dc2626", "#7c3aed", "#0d9488", "#ea580c", "#6366f1"]
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
    active = sum(1 for row in data if row.days_to_expiry is not None and row.days_to_expiry > 90)
    expiring_soon = sum(1 for row in data if row.days_to_expiry is not None and 0 <= row.days_to_expiry <= 30)
    expired = sum(1 for row in data if row.days_to_expiry is not None and row.days_to_expiry < 0)
    
    return [
        {
            "label": _("Total Permits"),
            "value": str(total),
            "indicator": "Blue"
        },
        {
            "label": _("Active"),
            "value": str(active),
            "indicator": "Green"
        },
        {
            "label": _("Expiring Soon (≤30 days)"),
            "value": str(expiring_soon),
            "indicator": "Orange" if expiring_soon > 0 else "Green"
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
    ws.title = "Environmental Compliance"
    
    header_font = Font(name='Arial', size=11, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='16A34A', end_color='16A34A', fill_type='solid')
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
                elif value <= 30:
                    cell.font = Font(color='EA580C', bold=True)
                elif value <= 90:
                    cell.font = Font(color='F59E0B')
            
            if fieldname == "status_display":
                if "Expired" in str(value):
                    cell.font = Font(color='DC2626', bold=True)
                elif "Expiring Soon" in str(value):
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
    summary_sheet.cell(row=1, column=1, value="Environmental Compliance Summary")
    summary_sheet.cell(row=1, column=1).font = Font(size=14, bold=True)
    
    if summary:
        for idx, item in enumerate(summary, 2):
            summary_sheet.cell(row=idx, column=1, value=item["label"])
            summary_sheet.cell(row=idx, column=2, value=item["value"])
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    frappe.response["filename"] = f"Environmental_Compliance_{getdate()}.xlsx"
    frappe.response["filecontent"] = output.getvalue()
    frappe.response["type"] = "download"