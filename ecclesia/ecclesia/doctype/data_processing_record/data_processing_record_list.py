# ecclesia/ecclesia/doctype/data_processing_record/data_processing_record_list.py

import frappe
from frappe import _
from frappe.utils import today, getdate, flt
import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import io


@frappe.whitelist()
def get_dpr_summary(filters=None):
    """Get Data Processing Record summary statistics"""
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    if not filters:
        filters = {}
    
    query_filters = {}
    if filters.get("status"):
        query_filters["status"] = filters["status"]
    if filters.get("company"):
        query_filters["company"] = filters["company"]
    
    records = frappe.get_all(
        "Data Processing Record",
        filters=query_filters,
        fields=["name", "status", "nitda_registered", "is_sensitive_data"]
    )
    
    total_count = len(records)
    active_count = sum(1 for r in records if r.status == "Active")
    review_count = sum(1 for r in records if r.status == "Under Review")
    discontinued_count = sum(1 for r in records if r.status == "Discontinued")
    nitda_count = sum(1 for r in records if r.nitda_registered)
    sensitive_count = sum(1 for r in records if r.is_sensitive_data)
    
    return {
        "total_count": total_count,
        "active_count": active_count,
        "review_count": review_count,
        "discontinued_count": discontinued_count,
        "nitda_count": nitda_count,
        "sensitive_count": sensitive_count
    }


@frappe.whitelist(allow_guest=True)
def export_dpr_excel():
    """Export Data Processing Record data to Excel with professional formatting"""
    filters = frappe.form_dict.get("filters", {})
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    query_filters = {}
    if filters.get("status"):
        query_filters["status"] = filters["status"]
    if filters.get("company"):
        query_filters["company"] = filters["company"]
    if filters.get("department"):
        query_filters["department"] = filters["department"]
    
    records = frappe.get_all(
        "Data Processing Record",
        filters=query_filters,
        fields=["name", "processing_title", "company", "department", 
                "processing_purpose", "legal_basis", "is_sensitive_data",
                "nitda_registered", "nitda_registration_no", "status",
                "last_reviewed", "next_review_date", "dpo"],
        order_by="processing_title asc"
    )
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Data Processing Records"
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
    widths = [8, 30, 18, 16, 30, 18, 12, 14, 18, 14, 14, 16, 18]
    for col, width in zip(columns, widths):
        ws.column_dimensions[col].width = width
    
    # Title
    ws.merge_cells('A1:M1')
    ws['A1'] = "📋 DATA PROCESSING RECORDS"
    ws['A1'].font = title_font
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 35
    
    ws.merge_cells('A2:M2')
    ws['A2'] = f"Generated: {frappe.utils.formatdate(today())} | Total Records: {len(records)}"
    ws['A2'].font = subtitle_font
    ws['A2'].alignment = Alignment(horizontal='center', vertical='center')
    
    # Headers
    headers = ["#", "Processing Title", "Company", "Department", "Purpose", 
               "Legal Basis", "Sensitive", "NITDA", "NITDA No", "Status", 
               "Last Review", "Next Review", "DPO"]
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
            rec.processing_title or "",
            rec.company or "",
            rec.department or "",
            rec.processing_purpose or "",
            rec.legal_basis or "",
            "Yes" if rec.is_sensitive_data else "No",
            "Yes" if rec.nitda_registered else "No",
            rec.nitda_registration_no or "",
            rec.status or "",
            frappe.utils.formatdate(rec.last_reviewed) if rec.last_reviewed else "",
            frappe.utils.formatdate(rec.next_review_date) if rec.next_review_date else "",
            rec.dpo or ""
        ]
        
        for col, value in enumerate(values, 1):
            cell = ws.cell(row=row_num, column=col, value=value)
            cell.border = thin_border
            
            if col in [1, 6, 7, 8, 10, 11, 12]:
                cell.alignment = center_align
            else:
                cell.alignment = left_align
            
            if idx % 2 == 0:
                cell.fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
            
            # Status coloring
            if col == 10:
                status = values[9]
                if status == "Active":
                    cell.font = Font(color="16A34A", bold=True)
                    cell.fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
                elif status == "Under Review":
                    cell.font = Font(color="F59E0B", bold=True)
                    cell.fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
                elif status == "Discontinued":
                    cell.font = Font(color="64748B")
                    cell.fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
            
            # Sensitive data coloring
            if col == 7 and value == "Yes":
                cell.font = Font(color="DC2626", bold=True)
            
            # NITDA status coloring
            if col == 8:
                if value == "Yes":
                    cell.font = Font(color="16A34A", bold=True)
                else:
                    cell.font = Font(color="DC2626", bold=True)
        
        ws.row_dimensions[row_num].height = 22
    
    ws.freeze_panes = 'A5'
    ws.auto_filter.ref = f'A4:M{4 + len(records)}'
    
    # Summary sheet
    summary_sheet.column_dimensions['A'].width = 25
    summary_sheet.column_dimensions['B'].width = 20
    
    summary_sheet.merge_cells('A1:B1')
    summary_sheet['A1'] = "📋 DPR SUMMARY"
    summary_sheet['A1'].font = Font(name="Segoe UI", size=14, bold=True, color="1D4ED8")
    summary_sheet['A1'].alignment = Alignment(horizontal='center')
    summary_sheet.row_dimensions[1].height = 30
    
    summary = get_dpr_summary(filters)
    
    items = [
        ("Total DPRs", str(summary.get("total_count", 0))),
        ("Active", str(summary.get("active_count", 0))),
        ("Under Review", str(summary.get("review_count", 0))),
        ("Discontinued", str(summary.get("discontinued_count", 0))),
        ("NITDA Registered", str(summary.get("nitda_count", 0))),
        ("Sensitive Data", str(summary.get("sensitive_count", 0)))
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
    
    frappe.response['filename'] = f"Data_Processing_Records_{today()}.xlsx"
    frappe.response['filecontent'] = output.read()
    frappe.response['type'] = 'binary'