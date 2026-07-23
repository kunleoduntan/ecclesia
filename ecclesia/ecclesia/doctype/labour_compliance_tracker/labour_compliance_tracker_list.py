# ecclesia/ecclesia/doctype/labour_compliance_tracker/labour_compliance_tracker_list.py

import frappe
from frappe import _
from frappe.utils import today, getdate, flt
import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import io


@frappe.whitelist()
def get_lct_summary(filters=None):
    """Get Labour Compliance Tracker summary statistics"""
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
        "Labour Compliance Tracker",
        filters=query_filters,
        fields=["name", "overall_status", "minimum_wage_compliant", "working_hours_compliant"]
    )
    
    total_count = len(records)
    compliant_count = sum(1 for r in records if r.overall_status == "Compliant")
    issues_count = sum(1 for r in records if r.overall_status == "Minor Issues")
    noncompliant_count = sum(1 for r in records if r.overall_status in ["Major Issues", "Non-Compliant"])
    wage_issue_count = sum(1 for r in records if not r.minimum_wage_compliant)
    hours_issue_count = sum(1 for r in records if not r.working_hours_compliant)
    
    return {
        "total_count": total_count,
        "compliant_count": compliant_count,
        "issues_count": issues_count,
        "noncompliant_count": noncompliant_count,
        "wage_issue_count": wage_issue_count,
        "hours_issue_count": hours_issue_count
    }


@frappe.whitelist(allow_guest=True)
def export_lct_excel():
    """Export Labour Compliance Tracker data to Excel with professional formatting"""
    filters = frappe.form_dict.get("filters", {})
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    query_filters = {}
    if filters.get("overall_status"):
        query_filters["overall_status"] = filters["overall_status"]
    if filters.get("company"):
        query_filters["company"] = filters["company"]
    if filters.get("period_label"):
        query_filters["period_label"] = filters["period_label"]
    
    records = frappe.get_all(
        "Labour Compliance Tracker",
        filters=query_filters,
        fields=["name", "tracker_title", "company", "period_label", "review_date",
                "overall_status", "total_employees", "current_min_wage", "lowest_gross_paid",
                "minimum_wage_compliant", "working_hours_compliant", "annual_leave_days_granted",
                "statutory_leave_compliant", "employees_with_contracts_pct",
                "employment_contracts_compliant", "pencom_all_registered", "nhf_all_registered",
                "responsible_officer"],
        order_by="period_label desc, company asc"
    )
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Labour Compliance Trackers"
    summary_sheet = wb.create_sheet("Summary")
    
    # Styles
    header_fill = PatternFill(start_color="EA580C", end_color="EA580C", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Segoe UI", size=16, bold=True, color="EA580C")
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
    columns = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q']
    widths = [8, 25, 18, 14, 16, 18, 12, 14, 16, 10, 10, 10, 10, 10, 10, 10, 18]
    for col, width in zip(columns, widths):
        ws.column_dimensions[col].width = width
    
    # Title
    ws.merge_cells('A1:Q1')
    ws['A1'] = "👷 LABOUR COMPLIANCE TRACKERS"
    ws['A1'].font = title_font
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 35
    
    ws.merge_cells('A2:Q2')
    ws['A2'] = f"Generated: {frappe.utils.formatdate(today())} | Total Trackers: {len(records)}"
    ws['A2'].font = subtitle_font
    ws['A2'].alignment = Alignment(horizontal='center', vertical='center')
    
    # Headers
    headers = ["#", "Tracker Title", "Company", "Period", "Review Date", "Overall Status",
               "Employees", "Min Wage", "Lowest Gross", "Min Wage OK", "Hours OK", 
               "Leave OK", "Contracts %", "Contracts OK", "PenCom OK", "NHF OK", "Officer"]
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
            rec.tracker_title or "",
            rec.company or "",
            rec.period_label or "",
            frappe.utils.formatdate(rec.review_date) if rec.review_date else "",
            rec.overall_status or "",
            rec.total_employees or 0,
            flt(rec.current_min_wage or 0),
            flt(rec.lowest_gross_paid or 0),
            "Yes" if rec.minimum_wage_compliant else "No",
            "Yes" if rec.working_hours_compliant else "No",
            "Yes" if rec.statutory_leave_compliant else "No",
            rec.employees_with_contracts_pct or 0,
            "Yes" if rec.employment_contracts_compliant else "No",
            "Yes" if rec.pencom_all_registered else "No",
            "Yes" if rec.nhf_all_registered else "No",
            rec.responsible_officer or ""
        ]
        
        for col, value in enumerate(values, 1):
            cell = ws.cell(row=row_num, column=col, value=value)
            cell.border = thin_border
            
            if col in [1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]:
                cell.alignment = center_align
            else:
                cell.alignment = left_align
            
            if idx % 2 == 0:
                cell.fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
            
            # Status coloring
            if col == 6:
                status = values[5]
                if status == "Compliant":
                    cell.font = Font(color="16A34A", bold=True)
                    cell.fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
                elif status == "Minor Issues":
                    cell.font = Font(color="F59E0B", bold=True)
                    cell.fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
                elif status in ["Major Issues", "Non-Compliant"]:
                    cell.font = Font(color="DC2626", bold=True)
                    cell.fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
            
            # Min wage issue coloring
            if col == 10 and value == "No":
                cell.font = Font(color="DC2626", bold=True)
            
            # Hours issue coloring
            if col == 11 and value == "No":
                cell.font = Font(color="DC2626", bold=True)
        
        ws.row_dimensions[row_num].height = 22
    
    ws.freeze_panes = 'A5'
    ws.auto_filter.ref = f'A4:Q{4 + len(records)}'
    
    # Summary sheet
    summary_sheet.column_dimensions['A'].width = 25
    summary_sheet.column_dimensions['B'].width = 20
    
    summary_sheet.merge_cells('A1:B1')
    summary_sheet['A1'] = "📋 LABOUR COMPLIANCE SUMMARY"
    summary_sheet['A1'].font = Font(name="Segoe UI", size=14, bold=True, color="EA580C")
    summary_sheet['A1'].alignment = Alignment(horizontal='center')
    summary_sheet.row_dimensions[1].height = 30
    
    summary = get_lct_summary(filters)
    
    items = [
        ("Total Trackers", str(summary.get("total_count", 0))),
        ("Compliant", str(summary.get("compliant_count", 0))),
        ("Minor Issues", str(summary.get("issues_count", 0))),
        ("Major Issues / Non-Compliant", str(summary.get("noncompliant_count", 0))),
        ("Minimum Wage Issues", str(summary.get("wage_issue_count", 0))),
        ("Working Hours Issues", str(summary.get("hours_issue_count", 0)))
    ]
    
    for idx, (label, value) in enumerate(items, 3):
        summary_sheet.cell(row=idx, column=1, value=label)
        summary_sheet.cell(row=idx, column=1).font = Font(size=11, bold=True)
        summary_sheet.cell(row=idx, column=2, value=value)
        summary_sheet.cell(row=idx, column=2).font = Font(size=11, color="EA580C", bold=True)
        summary_sheet.cell(row=idx, column=2).alignment = right_align
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    frappe.response['filename'] = f"Labour_Compliance_Trackers_{today()}.xlsx"
    frappe.response['filecontent'] = output.read()
    frappe.response['type'] = 'binary'