# ecclesia/ecclesia/doctype/expatriate_permit_register/expatriate_permit_register_list.py

import frappe
from frappe import _
from frappe.utils import today, getdate, flt
import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import io


@frappe.whitelist()
def get_epr_summary(filters=None):
    """Get Expatriate Permit Register summary statistics"""
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    if not filters:
        filters = {}
    
    query_filters = {}
    if filters.get("status"):
        query_filters["status"] = filters["status"]
    if filters.get("permit_type"):
        query_filters["permit_type"] = filters["permit_type"]
    if filters.get("company"):
        query_filters["company"] = filters["company"]
    
    records = frappe.get_all(
        "Expatriate Permit Register",
        filters=query_filters,
        fields=["name", "status", "permit_type"]
    )
    
    total_count = len(records)
    active_count = sum(1 for r in records if r.status == "Active")
    expiring_count = sum(1 for r in records if r.status == "Expiring Soon")
    expired_count = sum(1 for r in records if r.status == "Expired")
    renewing_count = sum(1 for r in records if r.status == "Renewing")
    quota_count = sum(1 for r in records if r.permit_type == "Expatriate Quota")
    cerpac_count = sum(1 for r in records if r.permit_type == "Combined Expatriate Residence Permit & Alien Card (CERPAC)")
    
    return {
        "total_count": total_count,
        "active_count": active_count,
        "expiring_count": expiring_count,
        "expired_count": expired_count,
        "renewing_count": renewing_count,
        "quota_count": quota_count,
        "cerpac_count": cerpac_count
    }


@frappe.whitelist(allow_guest=True)
def export_epr_excel():
    """Export Expatriate Permit Register data to Excel with professional formatting"""
    filters = frappe.form_dict.get("filters", {})
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    query_filters = {}
    if filters.get("status"):
        query_filters["status"] = filters["status"]
    if filters.get("permit_type"):
        query_filters["permit_type"] = filters["permit_type"]
    if filters.get("company"):
        query_filters["company"] = filters["company"]
    
    records = frappe.get_all(
        "Expatriate Permit Register",
        filters=query_filters,
        fields=["name", "permit_title", "employee", "nationality", "company",
                "permit_type", "permit_number", "quota_position", "issue_date",
                "expiry_date", "status", "renewal_cost", "notes"],
        order_by="expiry_date asc"
    )
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Expatriate Permits"
    summary_sheet = wb.create_sheet("Summary")
    
    # Styles
    header_fill = PatternFill(start_color="1D4ED8", end_color="1D4ED8", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Segoe UI", size=16, bold=True, color="1D4ED8")
    subtitle_font = Font(name="Segoe UI", size=10, color="64748B")
    
    thin_border = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )
    
    center_align = Alignment(horizontal='center', vertical='center')
    left_align = Alignment(horizontal='left', vertical='center')
    right_align = Alignment(horizontal='right', vertical='center')
    
    # Set column widths
    columns = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M']
    widths = [8, 25, 18, 14, 18, 22, 16, 18, 14, 16, 16, 16, 30]
    for col, width in zip(columns, widths):
        ws.column_dimensions[col].width = width
    
    # Title
    ws.merge_cells('A1:M1')
    ws['A1'] = "🛂 EXPATRIATE PERMIT REGISTER"
    ws['A1'].font = title_font
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 35
    
    ws.merge_cells('A2:M2')
    ws['A2'] = f"Generated: {frappe.utils.formatdate(today())} | Total Permits: {len(records)}"
    ws['A2'].font = subtitle_font
    ws['A2'].alignment = Alignment(horizontal='center', vertical='center')
    
    # Headers
    headers = ["#", "Permit Title", "Employee", "Nationality", "Company", 
               "Permit Type", "Permit Number", "Quota Position", "Issue Date", 
               "Expiry Date", "Status", "Renewal Cost", "Notes"]
    row_num = 4
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row_num, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align
        cell.border = thin_border
    ws.row_dimensions[row_num].height = 28
    
    # Data rows
    for idx, rec in enumerate(records, 1):
        row_num = 4 + idx
        values = [
            idx,
            rec.permit_title or "",
            rec.employee or "",
            rec.nationality or "",
            rec.company or "",
            rec.permit_type or "",
            rec.permit_number or "",
            rec.quota_position or "",
            frappe.utils.formatdate(rec.issue_date) if rec.issue_date else "",
            frappe.utils.formatdate(rec.expiry_date) if rec.expiry_date else "",
            rec.status or "",
            flt(rec.renewal_cost or 0),
            rec.notes or ""
        ]
        
        for col, value in enumerate(values, 1):
            cell = ws.cell(row=row_num, column=col, value=value)
            cell.border = thin_border
            
            if col in [1, 3, 4, 5, 6, 8, 9, 10, 11, 12]:
                cell.alignment = center_align
            elif col == 12:
                cell.alignment = right_align
                cell.number_format = '#,##0.00'
            else:
                cell.alignment = left_align
            
            if idx % 2 == 0:
                cell.fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
            
            # Status coloring
            if col == 11:
                status = values[10]
                if status == "Active":
                    cell.font = Font(color="16A34A", bold=True)
                    cell.fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
                elif status == "Expiring Soon":
                    cell.font = Font(color="F59E0B", bold=True)
                    cell.fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
                elif status == "Expired":
                    cell.font = Font(color="DC2626", bold=True)
                    cell.fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
                elif status == "Renewing":
                    cell.font = Font(color="2563EB", bold=True)
                    cell.fill = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")
            
            # Expiry date coloring
            if col == 10 and rec.expiry_date:
                expiry = getdate(rec.expiry_date)
                today_dt = getdate(today())
                diff = (expiry - today_dt).days
                if diff < 0:
                    cell.font = Font(color="DC2626", bold=True)
                elif diff < 30:
                    cell.font = Font(color="F59E0B", bold=True)
        
        ws.row_dimensions[row_num].height = 22
    
    ws.freeze_panes = 'A5'
    ws.auto_filter.ref = f'A4:M{4 + len(records)}'
    
    # Summary sheet
    summary_sheet.column_dimensions['A'].width = 25
    summary_sheet.column_dimensions['B'].width = 20
    
    summary_sheet.merge_cells('A1:B1')
    summary_sheet['A1'] = "📋 EXPATRIATE PERMIT SUMMARY"
    summary_sheet['A1'].font = Font(name="Segoe UI", size=14, bold=True, color="1D4ED8")
    summary_sheet['A1'].alignment = Alignment(horizontal='center')
    summary_sheet.row_dimensions[1].height = 30
    
    summary = get_epr_summary(filters)
    
    items = [
        ("Total Permits", str(summary.get("total_count", 0))),
        ("Active", str(summary.get("active_count", 0))),
        ("Expiring Soon", str(summary.get("expiring_count", 0))),
        ("Expired", str(summary.get("expired_count", 0))),
        ("Renewing", str(summary.get("renewing_count", 0))),
        ("Expatriate Quota", str(summary.get("quota_count", 0))),
        ("CERPAC", str(summary.get("cerpac_count", 0)))
    ]
    
    for idx, (label, value) in enumerate(items, 3):
        summary_sheet.cell(row=idx, column=1, value=label)
        summary_sheet.cell(row=idx, column=1).font = Font(size=11, bold=True)
        summary_sheet.cell(row=idx, column=2, value=value)
        summary_sheet.cell(row=idx, column=2).font = Font(size=11, color="1D4ED8", bold=True)
        summary_sheet.cell(row=idx, column=2).alignment = right_align
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    frappe.response['filename'] = f"Expatriate_Permits_{today()}.xlsx"
    frappe.response['filecontent'] = output.read()
    frappe.response['type'] = 'binary'