# ecclesia/ecclesia/doctype/suspicious_transaction_report/suspicious_transaction_report_list.py

import frappe
from frappe import _
from frappe.utils import today, getdate, flt
import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import io


@frappe.whitelist()
def get_str_summary(filters=None):
    """Get Suspicious Transaction Report summary statistics"""
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    if not filters:
        filters = {}
    
    query_filters = {}
    if filters.get("status"):
        query_filters["status"] = filters["status"]
    if filters.get("report_type"):
        query_filters["report_type"] = filters["report_type"]
    
    records = frappe.get_all(
        "Suspicious Transaction Report",
        filters=query_filters,
        fields=["name", "status", "nfiu_submitted", "transaction_amount"]
    )
    
    total_count = len(records)
    submitted_count = sum(1 for r in records if r.status == "Submitted to NFIU")
    review_count = sum(1 for r in records if r.status == "Under Review")
    referred_count = sum(1 for r in records if r.status == "Referred to Enforcement")
    draft_count = sum(1 for r in records if r.status == "Draft")
    closed_count = sum(1 for r in records if r.status == "Closed — No Action")
    nfiu_submitted_count = sum(1 for r in records if r.nfiu_submitted)
    total_amount = sum(r.transaction_amount or 0 for r in records)
    
    return {
        "total_count": total_count,
        "submitted_count": submitted_count,
        "review_count": review_count,
        "referred_count": referred_count,
        "draft_count": draft_count,
        "closed_count": closed_count,
        "nfiu_submitted_count": nfiu_submitted_count,
        "total_amount": total_amount
    }


@frappe.whitelist(allow_guest=True)
def export_str_excel():
    """Export Suspicious Transaction Report data to Excel with professional formatting"""
    filters = frappe.form_dict.get("filters", {})
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    query_filters = {}
    if filters.get("status"):
        query_filters["status"] = filters["status"]
    if filters.get("report_type"):
        query_filters["report_type"] = filters["report_type"]
    
    records = frappe.get_all(
        "Suspicious Transaction Report",
        filters=query_filters,
        fields=["name", "str_title", "report_type", "party_name", "transaction_amount",
                "transaction_date", "suspicious_indicators", "status", "nfiu_submitted",
                "nfiu_submission_date", "nfiu_reference", "submitted_by", "amlco_sign_off"],
        order_by="transaction_date desc"
    )
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Suspicious Transaction Reports"
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
    widths = [8, 22, 18, 18, 16, 14, 22, 18, 14, 14, 16, 16, 18]
    for col, width in zip(columns, widths):
        ws.column_dimensions[col].width = width
    
    # Title
    ws.merge_cells('A1:M1')
    ws['A1'] = "🚨 SUSPICIOUS TRANSACTION REPORTS"
    ws['A1'].font = title_font
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 35
    
    ws.merge_cells('A2:M2')
    ws['A2'] = f"Generated: {frappe.utils.formatdate(today())} | Total Reports: {len(records)}"
    ws['A2'].font = subtitle_font
    ws['A2'].alignment = Alignment(horizontal='center', vertical='center')
    
    # Headers
    headers = ["#", "STR Title", "Report Type", "Counterparty", "Amount (₦)", "Trans Date",
               "Indicator", "Status", "NFIU", "NFIU Date", "NFIU Ref", "Submitted By", "AMLCO"]
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
            rec.str_title or "",
            rec.report_type or "",
            rec.party_name or "",
            flt(rec.transaction_amount or 0),
            frappe.utils.formatdate(rec.transaction_date) if rec.transaction_date else "",
            rec.suspicious_indicators or "",
            rec.status or "",
            "Yes" if rec.nfiu_submitted else "No",
            frappe.utils.formatdate(rec.nfiu_submission_date) if rec.nfiu_submission_date else "",
            rec.nfiu_reference or "",
            rec.submitted_by or "",
            rec.amlco_sign_off or ""
        ]
        
        for col, value in enumerate(values, 1):
            cell = ws.cell(row=row_num, column=col, value=value)
            cell.border = thin_border
            
            if col in [1, 3, 5, 6, 8, 9, 10]:
                cell.alignment = center_align
            elif col == 5:
                cell.alignment = right_align
                cell.number_format = '#,##0.00'
            else:
                cell.alignment = left_align
            
            if idx % 2 == 0:
                cell.fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
            
            # Status coloring
            if col == 8:
                status = values[7]
                if status == "Referred to Enforcement":
                    cell.font = Font(color="DC2626", bold=True)
                    cell.fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
                elif status == "Submitted to NFIU":
                    cell.font = Font(color="2563EB", bold=True)
                    cell.fill = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")
                elif status == "Under Review":
                    cell.font = Font(color="F59E0B", bold=True)
                    cell.fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
                elif status == "Closed — No Action":
                    cell.font = Font(color="16A34A", bold=True)
                    cell.fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
            
            # Amount coloring
            if col == 5:
                if value > 10000000:
                    cell.font = Font(color="DC2626", bold=True)
                elif value > 5000000:
                    cell.font = Font(color="F59E0B")
        
        ws.row_dimensions[row_num].height = 22
    
    ws.freeze_panes = 'A5'
    ws.auto_filter.ref = f'A4:M{4 + len(records)}'
    
    # Summary sheet
    summary_sheet.column_dimensions['A'].width = 25
    summary_sheet.column_dimensions['B'].width = 20
    
    summary_sheet.merge_cells('A1:B1')
    summary_sheet['A1'] = "📋 STR SUMMARY"
    summary_sheet['A1'].font = Font(name="Segoe UI", size=14, bold=True, color="991B1B")
    summary_sheet['A1'].alignment = Alignment(horizontal='center')
    summary_sheet.row_dimensions[1].height = 30
    
    summary = get_str_summary(filters)
    
    items = [
        ("Total Reports", str(summary.get("total_count", 0))),
        ("Submitted to NFIU", str(summary.get("submitted_count", 0))),
        ("Under Review", str(summary.get("review_count", 0))),
        ("Referred to Enforcement", str(summary.get("referred_count", 0))),
        ("Draft", str(summary.get("draft_count", 0))),
        ("Closed", str(summary.get("closed_count", 0))),
        ("Total Amount", frappe.format_currency(summary.get("total_amount", 0), "NGN"))
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
    
    frappe.response['filename'] = f"Suspicious_Transaction_Reports_{today()}.xlsx"
    frappe.response['filecontent'] = output.read()
    frappe.response['type'] = 'binary'