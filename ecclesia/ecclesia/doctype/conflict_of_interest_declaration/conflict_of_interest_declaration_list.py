# ecclesia/ecclesia/doctype/conflict_of_interest_declaration/conflict_of_interest_declaration_list.py

import frappe
from frappe import _
from frappe.utils import today, getdate, flt
import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import io


@frappe.whitelist()
def get_coi_summary(filters=None):
    """Get Conflict of Interest Declaration summary statistics"""
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    if not filters:
        filters = {}
    
    query_filters = {}
    if filters.get("approval_status"):
        query_filters["approval_status"] = filters["approval_status"]
    if filters.get("company"):
        query_filters["company"] = filters["company"]
    
    records = frappe.get_all(
        "Conflict of Interest Declaration",
        filters=query_filters,
        fields=["name", "has_conflict", "approval_status", "declaration_type"]
    )
    
    total_count = len(records)
    conflict_count = sum(1 for r in records if r.has_conflict)
    approved_count = sum(1 for r in records if r.approval_status in ["Approved — No Further Action", "Approved with Conditions"])
    pending_count = sum(1 for r in records if r.approval_status == "Pending")
    escalated_count = sum(1 for r in records if r.approval_status == "Escalated to Board")
    annual_count = sum(1 for r in records if r.declaration_type == "Annual Declaration")
    
    return {
        "total_count": total_count,
        "conflict_count": conflict_count,
        "approved_count": approved_count,
        "pending_count": pending_count,
        "escalated_count": escalated_count,
        "annual_count": annual_count
    }


@frappe.whitelist(allow_guest=True)
def export_coi_excel():
    """Export Conflict of Interest Declaration data to Excel with professional formatting"""
    filters = frappe.form_dict.get("filters", {})
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    query_filters = {}
    if filters.get("approval_status"):
        query_filters["approval_status"] = filters["approval_status"]
    if filters.get("company"):
        query_filters["company"] = filters["company"]
    if filters.get("department"):
        query_filters["department"] = filters["department"]
    
    records = frappe.get_all(
        "Conflict of Interest Declaration",
        filters=query_filters,
        fields=["name", "declaration_title", "employee", "department", "designation",
                "declaration_date", "declaration_type", "has_conflict", "conflict_type",
                "conflict_description", "approval_status", "mitigation", "company"],
        order_by="declaration_date desc"
    )
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Conflict of Interest Declarations"
    summary_sheet = wb.create_sheet("Summary")
    
    # Styles
    header_fill = PatternFill(start_color="D97706", end_color="D97706", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Segoe UI", size=16, bold=True, color="D97706")
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
    widths = [8, 25, 18, 18, 16, 16, 18, 12, 18, 30, 20, 25, 18]
    for col, width in zip(columns, widths):
        ws.column_dimensions[col].width = width
    
    # Title
    ws.merge_cells('A1:M1')
    ws['A1'] = "🤝 CONFLICT OF INTEREST DECLARATIONS"
    ws['A1'].font = title_font
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 35
    
    ws.merge_cells('A2:M2')
    ws['A2'] = f"Generated: {frappe.utils.formatdate(today())} | Total Declarations: {len(records)}"
    ws['A2'].font = subtitle_font
    ws['A2'].alignment = Alignment(horizontal='center', vertical='center')
    
    # Headers
    headers = ["#", "Declaration Title", "Employee", "Department", "Designation", 
               "Declaration Date", "Type", "Conflict", "Conflict Type", "Description", 
               "Approval Status", "Mitigation", "Company"]
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
            rec.declaration_title or "",
            rec.employee or "",
            rec.department or "",
            rec.designation or "",
            frappe.utils.formatdate(rec.declaration_date) if rec.declaration_date else "",
            rec.declaration_type or "",
            "Yes" if rec.has_conflict else "No",
            rec.conflict_type or "",
            rec.conflict_description or "",
            rec.approval_status or "",
            rec.mitigation or "",
            rec.company or ""
        ]
        
        for col, value in enumerate(values, 1):
            cell = ws.cell(row=row_num, column=col, value=value)
            cell.border = thin_border
            
            if col in [1, 3, 5, 6, 7, 8, 9, 11, 13]:
                cell.alignment = center_align
            else:
                cell.alignment = left_align
            
            if idx % 2 == 0:
                cell.fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
            
            # Conflict coloring
            if col == 8 and value == "Yes":
                cell.font = Font(color="DC2626", bold=True)
                cell.fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
            
            # Approval status coloring
            if col == 11:
                status = values[10]
                if status == "Approved — No Further Action":
                    cell.font = Font(color="16A34A", bold=True)
                    cell.fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
                elif status == "Approved with Conditions":
                    cell.font = Font(color="2563EB", bold=True)
                    cell.fill = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")
                elif status == "Pending":
                    cell.font = Font(color="F59E0B", bold=True)
                    cell.fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
                elif status == "Escalated to Board":
                    cell.font = Font(color="DC2626", bold=True)
                    cell.fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
        
        ws.row_dimensions[row_num].height = 22
    
    ws.freeze_panes = 'A5'
    ws.auto_filter.ref = f'A4:M{4 + len(records)}'
    
    # Summary sheet
    summary_sheet.column_dimensions['A'].width = 25
    summary_sheet.column_dimensions['B'].width = 20
    
    summary_sheet.merge_cells('A1:B1')
    summary_sheet['A1'] = "📋 COI SUMMARY"
    summary_sheet['A1'].font = Font(name="Segoe UI", size=14, bold=True, color="D97706")
    summary_sheet['A1'].alignment = Alignment(horizontal='center')
    summary_sheet.row_dimensions[1].height = 30
    
    summary = get_coi_summary(filters)
    
    items = [
        ("Total Declarations", str(summary.get("total_count", 0))),
        ("Conflicts Declared", str(summary.get("conflict_count", 0))),
        ("Approved", str(summary.get("approved_count", 0))),
        ("Pending", str(summary.get("pending_count", 0))),
        ("Escalated to Board", str(summary.get("escalated_count", 0))),
        ("Annual Declarations", str(summary.get("annual_count", 0)))
    ]
    
    for idx, (label, value) in enumerate(items, 3):
        summary_sheet.cell(row=idx, column=1, value=label)
        summary_sheet.cell(row=idx, column=1).font = Font(size=11, bold=True)
        summary_sheet.cell(row=idx, column=2, value=value)
        summary_sheet.cell(row=idx, column=2).font = Font(size=11, color="D97706", bold=True)
        summary_sheet.cell(row=idx, column=2).alignment = right_align
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    frappe.response['filename'] = f"Conflict_of_Interest_Declarations_{today()}.xlsx"
    frappe.response['filecontent'] = output.read()
    frappe.response['type'] = 'binary'