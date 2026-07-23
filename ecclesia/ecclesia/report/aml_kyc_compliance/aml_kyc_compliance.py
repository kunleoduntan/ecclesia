# ecclesia/ecclesia/report/aml_kyc_compliance/aml_kyc_compliance.py

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
            "fieldname": "party_name_display",
            "label": _("Party Name"),
            "fieldtype": "Data",
            "width": 180,
            "bold": 1
        },
        {
            "fieldname": "party_type",
            "label": _("Party Type"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "kyc_level",
            "label": _("KYC Level"),
            "fieldtype": "Data",
            "width": 200
        },
        {
            "fieldname": "risk_rating",
            "label": _("Risk Rating"),
            "fieldtype": "Data",
            "width": 140
        },
        {
            "fieldname": "kyc_date",
            "label": _("KYC Date"),
            "fieldtype": "Date",
            "width": 120
        },
        {
            "fieldname": "kyc_expiry_date",
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
            "fieldname": "identity_verified_display",
            "label": _("Identity"),
            "fieldtype": "Data",
            "width": 100
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
            party_name_display,
            party_type,
            kyc_level,
            risk_rating,
            kyc_date,
            kyc_expiry_date,
            identity_verified,
            address_verified,
            pep_check_done,
            sanctions_check_done,
            name,
            responsible_officer
        FROM `tabAML KYC Record`
        WHERE {conditions}
        ORDER BY kyc_expiry_date ASC, risk_rating ASC
    """.format(conditions=conditions), filters, as_dict=1)
    
    for row in data:
        if row.kyc_expiry_date:
            expiry = getdate(row.kyc_expiry_date)
            today_dt = getdate(today_date)
            row["days_to_expiry"] = (expiry - today_dt).days
        else:
            row["days_to_expiry"] = None
        
        row["status_display"] = get_status_display(row)
        row["identity_verified_display"] = "✅" if row.identity_verified else "⬜"
    
    return data

def build_conditions(filters):
    conditions = "1=1"
    
    if filters.get("company"):
        conditions += " AND company = %(company)s"
    
    if filters.get("party_type"):
        conditions += " AND party_type = %(party_type)s"
    
    if filters.get("kyc_level"):
        conditions += " AND kyc_level = %(kyc_level)s"
    
    if filters.get("risk_rating"):
        conditions += " AND risk_rating = %(risk_rating)s"
    
    if filters.get("from_date") and filters.get("to_date"):
        conditions += " AND kyc_date BETWEEN %(from_date)s AND %(to_date)s"
    
    if filters.get("identity_verified"):
        conditions += " AND identity_verified = %(identity_verified)s"
    
    if filters.get("show_expiring_only"):
        conditions += " AND kyc_expiry_date IS NOT NULL"
        conditions += " AND DATEDIFF(kyc_expiry_date, CURDATE()) <= 30"
    
    if filters.get("is_pep"):
        conditions += " AND is_pep = 1"
    
    if filters.get("sanctions_match"):
        conditions += " AND sanctions_match = 1"
    
    return conditions

def get_status_display(row):
    if not row.kyc_expiry_date:
        return "⚪ No Expiry Set"
    
    days = row.days_to_expiry
    if days is None:
        return "⚪ No Expiry Set"
    
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
    
    risk_counts = {
        "Low": 0,
        "Medium": 0,
        "High": 0,
        "PEP — High": 0,
        "Sanctioned — Blocked": 0
    }
    
    for row in data:
        risk = row.risk_rating
        if risk in risk_counts:
            risk_counts[risk] += 1
    
    labels = list(risk_counts.keys())
    values = list(risk_counts.values())
    
    colors = {
        "Low": "#16a34a",
        "Medium": "#f59e0b",
        "High": "#ea580c",
        "PEP — High": "#dc2626",
        "Sanctioned — Blocked": "#991b1b"
    }
    
    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": _("Records"),
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
    
    total_records = len(data)
    expired = sum(1 for row in data if row.days_to_expiry is not None and row.days_to_expiry < 0)
    expiring_soon = sum(1 for row in data if row.days_to_expiry is not None and 0 <= row.days_to_expiry <= 30)
    low_risk = sum(1 for row in data if row.risk_rating == "Low")
    high_risk = sum(1 for row in data if row.risk_rating in ["High", "PEP — High", "Sanctioned — Blocked"])
    verified = sum(1 for row in data if row.identity_verified)
    
    return [
        {
            "label": _("Total Records"),
            "value": str(total_records),
            "indicator": "Blue"
        },
        {
            "label": _("Identity Verified"),
            "value": f"{verified}/{total_records}",
            "indicator": "Green" if verified > 0 else "Red"
        },
        {
            "label": _("Low Risk"),
            "value": str(low_risk),
            "indicator": "Green"
        },
        {
            "label": _("High Risk"),
            "value": str(high_risk),
            "indicator": "Red" if high_risk > 0 else "Green"
        },
        {
            "label": _("Expired"),
            "value": str(expired),
            "indicator": "Red" if expired > 0 else "Green"
        },
        {
            "label": _("Expiring Soon"),
            "value": str(expiring_soon),
            "indicator": "Orange" if expiring_soon > 0 else "Green"
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
    ws.title = "AML KYC Compliance"
    
    header_font = Font(name='Arial', size=11, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='1E3A5F', end_color='1E3A5F', fill_type='solid')
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
            
            if fieldname == "days_to_expiry" and value is not None:
                if value < 0:
                    cell.font = Font(color='DC2626', bold=True)
                elif value <= 30:
                    cell.font = Font(color='EA580C', bold=True)
                elif value <= 90:
                    cell.font = Font(color='F59E0B')
    
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
    summary_sheet.cell(row=1, column=1, value="AML KYC Compliance Summary")
    summary_sheet.cell(row=1, column=1).font = Font(size=14, bold=True)
    
    if summary:
        for idx, item in enumerate(summary, 2):
            summary_sheet.cell(row=idx, column=1, value=item["label"])
            summary_sheet.cell(row=idx, column=2, value=item["value"])
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    frappe.response["filename"] = f"AML_KYC_Compliance_{getdate()}.xlsx"
    frappe.response["filecontent"] = output.getvalue()
    frappe.response["type"] = "download"