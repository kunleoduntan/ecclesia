# ecclesia/ecclesia/doctype/corporate_compliance_register/corporate_compliance_register_list.py

import frappe
from frappe import _
from frappe.utils import today, getdate, flt
import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import io


@frappe.whitelist()
def get_ccr_summary(filters=None):
    """Get Corporate Compliance Register summary statistics"""
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    if not filters:
        filters = {}
    
    query_filters = {}
    if filters.get("overall_status"):
        query_filters["overall_status"] = filters["overall_status"]
    if filters.get("company"):
        query_filters["company"] = filters["company"]
    
    records = frappe.get_all(
        "Corporate Compliance Register",
        filters=query_filters,
        fields=["name", "overall_status", "annual_return_status"]
    )
    
    total_count = len(records)
    compliant_count = sum(1 for r in records if r.overall_status == "Compliant")
    minor_count = sum(1 for r in records if r.overall_status == "Minor Issues")
    major_count = sum(1 for r in records if r.overall_status in ["Major Issues", "Non-Compliant"])
    cac_due_count = sum(1 for r in records if r.annual_return_status == "Due")
    
    return {
        "total_count": total_count,
        "compliant_count": compliant_count,
        "minor_count": minor_count,
        "major_count": major_count,
        "cac_due_count": cac_due_count
    }


@frappe.whitelist(allow_guest=True)
def export_ccr_excel():
    """Export Corporate Compliance Register data to Excel with professional formatting"""
    filters = frappe.form_dict.get("filters", {})
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    query_filters = {}
    if filters.get("overall_status"):
        query_filters["overall_status"] = filters["overall_status"]
    if filters.get("company"):
        query_filters["company"] = filters["company"]
    if filters.get("fiscal_year"):
        query_filters["fiscal_year"] = filters["fiscal_year"]
    
    records = frappe.get_all(
        "Corporate Compliance Register",
        filters=query_filters,
        fields=["name", "register_title", "company", "fiscal_year", "rc_number",
                "company_type", "company_secretary", "date_of_incorporation",
                "annual_return_status", "annual_return_due_date", "annual_return_filed_date",
                "next_agm_due_date", "overall_status"],
        order_by="company asc, fiscal_year desc"
    )
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Corporate Compliance Registers"
    summary_sheet = wb.create_sheet("Summary")
    
    # Styles
    header_fill = PatternFill(start_color="0F766E", end_color="0F766E", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Segoe UI", size=16, bold=True, color="0F766E")
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
    widths = [8, 28, 18, 14, 16, 18, 18, 16, 16, 16, 16, 16, 16]
    for col, width in zip(columns, widths):
        ws.column_dimensions[col].width = width
    
    # Title
    ws.merge_cells('A1:M1')
    ws['A1'] = "🏛️ CORPORATE COMPLIANCE REGISTERS"
    ws['A1'].font = title_font
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 35
    
    ws.merge_cells('A2:M2')
    ws['A2'] = f"Generated: {frappe.utils.formatdate(today())} | Total Registers: {len(records)}"
    ws['A2'].font = subtitle_font
    ws['A2'].alignment = Alignment(horizontal='center', vertical='center')
    
    # Headers
    headers = ["#", "Register Title", "Company", "Fiscal Year", "RC Number", 
               "Company Type", "Secretary", "Incorporation", "CAC Status", 
               "CAC Due", "CAC Filed", "AGM Due", "Overall Status"]
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
            rec.register_title or "",
            rec.company or "",
            rec.fiscal_year or "",
            rec.rc_number or "",
            rec.company_type or "",
            rec.company_secretary or "",
            frappe.utils.formatdate(rec.date_of_incorporation) if rec.date_of_incorporation else "",
            rec.annual_return_status or "",
            frappe.utils.formatdate(rec.annual_return_due_date) if rec.annual_return_due_date else "",
            frappe.utils.formatdate(rec.annual_return_filed_date) if rec.annual_return_filed_date else "",
            frappe.utils.formatdate(rec.next_agm_due_date) if rec.next_agm_due_date else "",
            rec.overall_status or ""
        ]
        
        for col, value in enumerate(values, 1):
            cell = ws.cell(row=row_num, column=col, value=value)
            cell.border = thin_border
            
            if col in [1, 3, 4, 5, 6, 9, 10, 11, 12, 13]:
                cell.alignment = center_align
            else:
                cell.alignment = left_align
            
            if idx % 2 == 0:
                cell.fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
            
            # Overall status coloring
            if col == 13:
                status = values[12]
                if status == "Compliant":
                    cell.font = Font(color="16A34A", bold=True)
                    cell.fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
                elif status == "Minor Issues":
                    cell.font = Font(color="F59E0B", bold=True)
                    cell.fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
                elif status in ["Major Issues", "Non-Compliant"]:
                    cell.font = Font(color="DC2626", bold=True)
                    cell.fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
        
        ws.row_dimensions[row_num].height = 22
    
    ws.freeze_panes = 'A5'
    ws.auto_filter.ref = f'A4:M{4 + len(records)}'
    
    # Summary sheet
    summary_sheet.column_dimensions['A'].width = 25
    summary_sheet.column_dimensions['B'].width = 20
    
    summary_sheet.merge_cells('A1:B1')
    summary_sheet['A1'] = "📋 CORPORATE COMPLIANCE SUMMARY"
    summary_sheet['A1'].font = Font(name="Segoe UI", size=14, bold=True, color="0F766E")
    summary_sheet['A1'].alignment = Alignment(horizontal='center')
    summary_sheet.row_dimensions[1].height = 30
    
    summary = get_ccr_summary(filters)
    
    items = [
        ("Total Registers", str(summary.get("total_count", 0))),
        ("Compliant", str(summary.get("compliant_count", 0))),
        ("Minor Issues", str(summary.get("minor_count", 0))),
        ("Major Issues / Non-Compliant", str(summary.get("major_count", 0))),
        ("CAC Return Due", str(summary.get("cac_due_count", 0)))
    ]
    
    for idx, (label, value) in enumerate(items, 3):
        summary_sheet.cell(row=idx, column=1, value=label)
        summary_sheet.cell(row=idx, column=1).font = Font(size=11, bold=True)
        summary_sheet.cell(row=idx, column=2, value=value)
        summary_sheet.cell(row=idx, column=2).font = Font(size=11, color="0F766E", bold=True)
        summary_sheet.cell(row=idx, column=2).alignment = right_align
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    frappe.response['filename'] = f"Corporate_Compliance_Registers_{today()}.xlsx"
    frappe.response['filecontent'] = output.read()
    frappe.response['type'] = 'binary'