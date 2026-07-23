# ecclesia/ecclesia/doctype/whistleblower_report/whistleblower_report_list.py

import frappe
from frappe import _
from frappe.utils import today, getdate, flt
import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import io


@frappe.whitelist()
def get_wb_summary(filters=None):
    """Get Whistleblower Report summary statistics"""
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    if not filters:
        filters = {}
    
    query_filters = {}
    if filters.get("status"):
        query_filters["status"] = filters["status"]
    if filters.get("severity"):
        query_filters["severity"] = filters["severity"]
    
    records = frappe.get_all(
        "Whistleblower Report",
        filters=query_filters,
        fields=["name", "status", "severity", "is_anonymous"]
    )
    
    total_count = len(records)
    investigating_count = sum(1 for r in records if r.status == "Under Investigation")
    substantiated_count = sum(1 for r in records if r.status == "Closed — Substantiated")
    unsubstantiated_count = sum(1 for r in records if r.status == "Closed — Unsubstantiated")
    escalated_count = sum(1 for r in records if r.status == "Escalated")
    anonymous_count = sum(1 for r in records if r.is_anonymous)
    high_count = sum(1 for r in records if r.severity in ["High", "Critical"])
    
    return {
        "total_count": total_count,
        "investigating_count": investigating_count,
        "substantiated_count": substantiated_count,
        "unsubstantiated_count": unsubstantiated_count,
        "escalated_count": escalated_count,
        "anonymous_count": anonymous_count,
        "high_count": high_count
    }


@frappe.whitelist(allow_guest=True)
def export_wb_excel():
    """Export Whistleblower Report data to Excel with professional formatting"""
    filters = frappe.form_dict.get("filters", {})
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    query_filters = {}
    if filters.get("status"):
        query_filters["status"] = filters["status"]
    if filters.get("severity"):
        query_filters["severity"] = filters["severity"]
    if filters.get("report_category"):
        query_filters["report_category"] = filters["report_category"]
    
    records = frappe.get_all(
        "Whistleblower Report",
        filters=query_filters,
        fields=["name", "report_code", "report_category", "severity", "received_date",
                "channel", "is_anonymous", "status", "assigned_investigator", 
                "investigation_start", "investigation_close", "outcome"],
        order_by="received_date desc"
    )
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Whistleblower Reports"
    summary_sheet = wb.create_sheet("Summary")
    
    # Styles
    header_fill = PatternFill(start_color="991B1B", end_color="991B1B", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Segoe UI", size=16, bold=True, color="991B1B")
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
    widths = [8, 16, 20, 14, 16, 14, 14, 18, 18, 16, 16, 18, 20]
    for col, width in zip(columns, widths):
        ws.column_dimensions[col].width = width
    
    # Title
    ws.merge_cells('A1:M1')
    ws['A1'] = "🔍 WHISTLEBLOWER REPORTS"
    ws['A1'].font = title_font
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 35
    
    ws.merge_cells('A2:M2')
    ws['A2'] = f"Generated: {frappe.utils.formatdate(today())} | Total Reports: {len(records)}"
    ws['A2'].font = subtitle_font
    ws['A2'].alignment = Alignment(horizontal='center', vertical='center')
    
    # Headers
    headers = ["#", "Report Code", "Category", "Severity", "Received", "Channel", 
               "Anonymous", "Status", "Investigator", "Start Date", "Close Date", 
               "Outcome", "Compliance Incident"]
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
            rec.report_code or "",
            rec.report_category or "",
            rec.severity or "",
            frappe.utils.formatdate(rec.received_date) if rec.received_date else "",
            rec.channel or "",
            "Yes" if rec.is_anonymous else "No",
            rec.status or "",
            rec.assigned_investigator or "",
            frappe.utils.formatdate(rec.investigation_start) if rec.investigation_start else "",
            frappe.utils.formatdate(rec.investigation_close) if rec.investigation_close else "",
            rec.outcome or "",
            rec.compliance_incident_ref or ""
        ]
        
        for col, value in enumerate(values, 1):
            cell = ws.cell(row=row_num, column=col, value=value)
            cell.border = thin_border
            
            if col in [1, 3, 4, 5, 7, 8, 10, 11]:
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
                elif severity == "Low":
                    cell.font = Font(color="16A34A")
            
            # Status coloring
            if col == 8:
                status = values[7]
                if status == "Closed — Substantiated":
                    cell.font = Font(color="DC2626", bold=True)
                    cell.fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
                elif status == "Escalated":
                    cell.font = Font(color="DC2626", bold=True)
                    cell.fill = PatternFill(start_color="FEF2F2", end_color="FEF2F2", fill_type="solid")
                elif status == "Under Investigation":
                    cell.font = Font(color="F59E0B", bold=True)
                    cell.fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
                elif status == "Closed — Unsubstantiated":
                    cell.font = Font(color="16A34A", bold=True)
                    cell.fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
            
            # Anonymous coloring
            if col == 7 and value == "Yes":
                cell.font = Font(color="7C3AED", bold=True)
        
        ws.row_dimensions[row_num].height = 22
    
    ws.freeze_panes = 'A5'
    ws.auto_filter.ref = f'A4:M{4 + len(records)}'
    
    # Summary sheet
    summary_sheet.column_dimensions['A'].width = 25
    summary_sheet.column_dimensions['B'].width = 20
    
    summary_sheet.merge_cells('A1:B1')
    summary_sheet['A1'] = "📋 WHISTLEBLOWER SUMMARY"
    summary_sheet['A1'].font = Font(name="Segoe UI", size=14, bold=True, color="991B1B")
    summary_sheet['A1'].alignment = Alignment(horizontal='center')
    summary_sheet.row_dimensions[1].height = 30
    
    summary = get_wb_summary(filters)
    
    items = [
        ("Total Reports", str(summary.get("total_count", 0))),
        ("Under Investigation", str(summary.get("investigating_count", 0))),
        ("Substantiated", str(summary.get("substantiated_count", 0))),
        ("Unsubstantiated", str(summary.get("unsubstantiated_count", 0))),
        ("Escalated", str(summary.get("escalated_count", 0))),
        ("Anonymous Reports", str(summary.get("anonymous_count", 0))),
        ("High/Critical Severity", str(summary.get("high_count", 0)))
    ]
    
    for idx, (label, value) in enumerate(items, 3):
        summary_sheet.cell(row=idx, column=1, value=label)
        summary_sheet.cell(row=idx, column=1).font = Font(size=11, bold=True)
        summary_sheet.cell(row=idx, column=2, value=value)
        summary_sheet.cell(row=idx, column=2).font = Font(size=11, color="991B1B", bold=True)
        summary_sheet.cell(row=idx, column=2).alignment = right_align
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    frappe.response['filename'] = f"Whistleblower_Reports_{today()}.xlsx"
    frappe.response['filecontent'] = output.read()
    frappe.response['type'] = 'binary'