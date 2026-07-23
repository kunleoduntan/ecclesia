# ecclesia/ecclesia/doctype/data_breach_register/data_breach_register_list.py

import frappe
from frappe import _
from frappe.utils import today, getdate, flt
import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import io


@frappe.whitelist()
def get_breach_summary(filters=None):
    """Get Data Breach Register summary statistics"""
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    if not filters:
        filters = {}
    
    query_filters = {}
    if filters.get("severity"):
        query_filters["severity"] = filters["severity"]
    if filters.get("status"):
        query_filters["status"] = filters["status"]
    
    records = frappe.get_all(
        "Data Breach Register",
        filters=query_filters,
        fields=["name", "severity", "status", "nitda_notified"]
    )
    
    total_count = len(records)
    critical_count = sum(1 for r in records if r.severity == "Critical")
    high_count = sum(1 for r in records if r.severity == "High")
    medium_count = sum(1 for r in records if r.severity == "Medium")
    low_count = sum(1 for r in records if r.severity == "Low")
    notified_count = sum(1 for r in records if r.nitda_notified)
    pending_count = total_count - notified_count
    
    return {
        "total_count": total_count,
        "critical_count": critical_count,
        "high_count": high_count,
        "medium_count": medium_count,
        "low_count": low_count,
        "notified_count": notified_count,
        "pending_count": pending_count
    }


@frappe.whitelist(allow_guest=True)
def export_breach_excel():
    """Export Data Breach Register data to Excel with professional formatting"""
    filters = frappe.form_dict.get("filters", {})
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    query_filters = {}
    if filters.get("severity"):
        query_filters["severity"] = filters["severity"]
    if filters.get("status"):
        query_filters["status"] = filters["status"]
    
    records = frappe.get_all(
        "Data Breach Register",
        filters=query_filters,
        fields=["name", "breach_title", "breach_type", "severity", "breach_date",
                "data_subjects_affected", "data_categories_breached", 
                "nitda_notified", "nitda_notification_date", "nitda_notification_reference",
                "status", "dpo_sign_off"],
        order_by="breach_date desc"
    )
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Data Breach Register"
    summary_sheet = wb.create_sheet("Summary")
    
    # Styles
    header_fill = PatternFill(start_color="5B21B6", end_color="5B21B6", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Segoe UI", size=16, bold=True, color="5B21B6")
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
    columns = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']
    widths = [8, 28, 18, 18, 14, 14, 16, 22, 14, 16, 18, 18]
    for col, width in zip(columns, widths):
        ws.column_dimensions[col].width = width
    
    # Title
    ws.merge_cells('A1:L1')
    ws['A1'] = "🔐 DATA BREACH REGISTER"
    ws['A1'].font = title_font
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 35
    
    ws.merge_cells('A2:L2')
    ws['A2'] = f"Generated: {frappe.utils.formatdate(today())} | Total Breaches: {len(records)}"
    ws['A2'].font = subtitle_font
    ws['A2'].alignment = Alignment(horizontal='center', vertical='center')
    
    # Headers
    headers = ["#", "Breach Title", "Breach Type", "Severity", "Breach Date", "Subjects",
               "Data Categories", "NITDA Notified", "NITDA Date", "NITDA Ref", "Status", "DPO Sign-off"]
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
            rec.breach_title or "",
            rec.breach_type or "",
            rec.severity or "",
            frappe.utils.formatdate(rec.breach_date) if rec.breach_date else "",
            rec.data_subjects_affected or 0,
            rec.data_categories_breached or "",
            "Yes" if rec.nitda_notified else "No",
            frappe.utils.formatdate(rec.nitda_notification_date) if rec.nitda_notification_date else "",
            rec.nitda_notification_reference or "",
            rec.status or "",
            rec.dpo_sign_off or ""
        ]
        
        for col, value in enumerate(values, 1):
            cell = ws.cell(row=row_num, column=col, value=value)
            cell.border = thin_border
            
            if col in [1, 3, 4, 5, 6, 8, 9, 11]:
                cell.alignment = center_align
            else:
                cell.alignment = left_align
            
            if idx % 2 == 0:
                cell.fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
            
            # Severity coloring
            if col == 4:
                severity = values[3]
                if severity == "Critical":
                    cell.font = Font(color="DC2626", bold=True)
                    cell.fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
                elif severity == "High":
                    cell.font = Font(color="F59E0B", bold=True)
                    cell.fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
                elif severity == "Medium":
                    cell.font = Font(color="F59E0B")
                    cell.fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
                elif severity == "Low":
                    cell.font = Font(color="16A34A")
                    cell.fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
            
            # NITDA status coloring
            if col == 8:
                if value == "Yes":
                    cell.font = Font(color="16A34A", bold=True)
                else:
                    cell.font = Font(color="DC2626", bold=True)
        
        ws.row_dimensions[row_num].height = 22
    
    ws.freeze_panes = 'A5'
    ws.auto_filter.ref = f'A4:L{4 + len(records)}'
    
    # Summary sheet
    summary_sheet.column_dimensions['A'].width = 25
    summary_sheet.column_dimensions['B'].width = 20
    
    summary_sheet.merge_cells('A1:B1')
    summary_sheet['A1'] = "📋 DATA BREACH SUMMARY"
    summary_sheet['A1'].font = Font(name="Segoe UI", size=14, bold=True, color="5B21B6")
    summary_sheet['A1'].alignment = Alignment(horizontal='center')
    summary_sheet.row_dimensions[1].height = 30
    
    summary = get_breach_summary(filters)
    
    items = [
        ("Total Breaches", str(summary.get("total_count", 0))),
        ("Critical", str(summary.get("critical_count", 0))),
        ("High", str(summary.get("high_count", 0))),
        ("Medium", str(summary.get("medium_count", 0))),
        ("Low", str(summary.get("low_count", 0))),
        ("NITDA Notified", str(summary.get("notified_count", 0))),
        ("Pending Notification", str(summary.get("pending_count", 0)))
    ]
    
    for idx, (label, value) in enumerate(items, 3):
        summary_sheet.cell(row=idx, column=1, value=label)
        summary_sheet.cell(row=idx, column=1).font = Font(size=11, bold=True)
        summary_sheet.cell(row=idx, column=2, value=value)
        summary_sheet.cell(row=idx, column=2).font = Font(size=11, color="5B21B6", bold=True)
        summary_sheet.cell(row=idx, column=2).alignment = right_align
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    frappe.response['filename'] = f"Data_Breach_Register_{today()}.xlsx"
    frappe.response['filecontent'] = output.read()
    frappe.response['type'] = 'binary'