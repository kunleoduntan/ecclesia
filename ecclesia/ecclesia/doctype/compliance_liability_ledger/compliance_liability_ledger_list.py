# ecclesia/ecclesia/doctype/compliance_liability_ledger/compliance_liability_ledger_list.py

import frappe
from frappe import _
from frappe.utils import today, getdate, flt
import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, NamedStyle
from openpyxl.utils import get_column_letter
import io


@frappe.whitelist()
def get_cll_summary(filters=None):
    """Get Compliance Liability Ledger summary statistics"""
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    if not filters:
        filters = {}
    
    query_filters = {}
    if filters.get("status"):
        query_filters["status"] = filters["status"]
    if filters.get("obligation_type"):
        query_filters["obligation_type"] = filters["obligation_type"]
    if filters.get("company"):
        query_filters["company"] = filters["company"]
    
    records = frappe.get_all(
        "Compliance Liability Ledger",
        filters=query_filters,
        fields=["name", "status", "obligation_type", "total_liability", 
                "total_allocated", "balance_due", "due_date", "is_overdue"]
    )
    
    total_count = len(records)
    total_liability = sum([r.total_liability or 0 for r in records])
    
    status_counts = {}
    obligation_counts = {}
    
    for rec in records:
        status = rec.status or "Unknown"
        status_counts[status] = status_counts.get(status, 0) + 1
        
        ob_type = rec.obligation_type or "Other"
        obligation_counts[ob_type] = obligation_counts.get(ob_type, 0) + 1
    
    return {
        "total_count": total_count,
        "total_liability": total_liability,
        "paid_count": status_counts.get("Fully Paid", 0),
        "partial_count": status_counts.get("Partially Paid", 0),
        "overdue_count": status_counts.get("Overdue", 0),
        "open_count": status_counts.get("Open", 0),
        "reconciled_count": status_counts.get("Reconciled", 0),
        "vat_count": obligation_counts.get("VAT", 0),
        "wht_count": obligation_counts.get("WHT", 0),
        "paye_count": obligation_counts.get("PAYE", 0),
        "pension_count": obligation_counts.get("Pension", 0),
        "status_breakdown": status_counts,
        "obligation_breakdown": obligation_counts
    }


@frappe.whitelist(allow_guest=True)
def export_cll_excel():
    """Export Compliance Liability Ledger data to Excel with professional formatting"""
    filters = frappe.form_dict.get("filters", {})
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    query_filters = {}
    if filters.get("status"):
        query_filters["status"] = filters["status"]
    if filters.get("obligation_type"):
        query_filters["obligation_type"] = filters["obligation_type"]
    if filters.get("company"):
        query_filters["company"] = filters["company"]
    
    records = frappe.get_all(
        "Compliance Liability Ledger",
        filters=query_filters,
        fields=["name", "ledger_key", "obligation_type", "period_label", 
                "company", "fiscal_year", "total_liability", "total_allocated", 
                "balance_due", "status", "due_date", "is_overdue",
                "period_start", "period_end", "generation_method"],
        order_by="due_date asc"
    )
    
    wb = Workbook()
    
    # Main data sheet
    ws = wb.active
    ws.title = "Compliance Liabilities"
    
    # Summary sheet
    summary_sheet = wb.create_sheet("Summary")
    
    # Styles
    header_fill = PatternFill(start_color="1E40AF", end_color="1E40AF", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Segoe UI", size=16, bold=True, color="1E40AF")
    subtitle_font = Font(name="Segoe UI", size=10, color="64748B")
    
    # Status colors
    status_colors = {
        "Fully Paid": "16A34A",
        "Partially Paid": "F59E0B",
        "Overdue": "DC2626",
        "Open": "2563EB",
        "Reconciled": "7C3AED",
        "Exempt": "64748B"
    }
    
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
    widths = [20, 18, 16, 14, 22, 14, 16, 16, 16, 16, 14, 14, 18]
    for col, width in zip(columns, widths):
        ws.column_dimensions[col].width = width
    
    # Title Section
    ws.merge_cells('A1:M1')
    ws['A1'] = "📊 COMPLIANCE LIABILITY LEDGER"
    ws['A1'].font = title_font
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 35
    
    ws.merge_cells('A2:M2')
    ws['A2'] = f"Generated: {frappe.utils.formatdate(today())} | Total Records: {len(records)}"
    ws['A2'].font = subtitle_font
    ws['A2'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[2].height = 25
    
    # Headers - Row 4
    headers = ["#", "Ledger Key", "Obligation", "Period", "Company", "Fiscal Year",
               "Liability (₦)", "Paid (₦)", "Balance (₦)", "Status", "Due Date", 
               "Overdue", "Generation"]
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
            rec.ledger_key or "",
            rec.obligation_type or "",
            rec.period_label or "",
            rec.company or "",
            rec.fiscal_year or "",
            flt(rec.total_liability or 0),
            flt(rec.total_allocated or 0),
            flt(rec.balance_due or 0),
            rec.status or "",
            frappe.utils.formatdate(rec.due_date) if rec.due_date else "",
            "Yes" if rec.is_overdue else "No",
            rec.generation_method or ""
        ]
        
        for col, value in enumerate(values, 1):
            cell = ws.cell(row=row_num, column=col, value=value)
            cell.border = thin_border
            
            # Apply alignment
            if col in [1, 4, 10, 11, 12]:
                cell.alignment = center_align
            elif col in [7, 8, 9]:
                cell.alignment = right_align
                cell.number_format = '#,##0.00'
            else:
                cell.alignment = left_align
            
            # Alternate row coloring
            if idx % 2 == 0:
                cell.fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
            
            # Status cell color coding
            if col == 10:
                status = values[9]
                color = status_colors.get(status, "64748B")
                cell.font = Font(color=color, bold=True)
                if status == "Overdue":
                    cell.fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
                elif status == "Fully Paid":
                    cell.fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
                elif status == "Partially Paid":
                    cell.fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
            
            # Balance color coding
            if col == 9:
                if value > 0:
                    cell.font = Font(color="DC2626", bold=True)
                elif value == 0:
                    cell.font = Font(color="16A34A")
        
        ws.row_dimensions[row_num].height = 22
    
    # Freeze panes and add filter
    ws.freeze_panes = 'A5'
    ws.auto_filter.ref = f'A4:M{4 + len(records)}'
    
    # ============ SUMMARY SHEET ============
    summary_sheet.column_dimensions['A'].width = 25
    summary_sheet.column_dimensions['B'].width = 20
    summary_sheet.column_dimensions['C'].width = 20
    
    # Title
    summary_sheet.merge_cells('A1:C1')
    summary_sheet['A1'] = "📋 COMPLIANCE LIABILITY SUMMARY"
    summary_sheet['A1'].font = Font(name="Segoe UI", size=14, bold=True, color="1E40AF")
    summary_sheet['A1'].alignment = Alignment(horizontal='center', vertical='center')
    summary_sheet.row_dimensions[1].height = 30
    
    # Get summary data
    summary = get_cll_summary(filters)
    
    # Summary items with icons
    items = [
        ("Total Records", str(summary.get("total_count", 0)), "🔵"),
        ("Total Liability", frappe.format_currency(summary.get("total_liability", 0), "NGN"), "💰"),
        ("Fully Paid", str(summary.get("paid_count", 0)), "✅"),
        ("Partially Paid", str(summary.get("partial_count", 0)), "⏳"),
        ("Overdue", str(summary.get("overdue_count", 0)), "🚨"),
        ("Open", str(summary.get("open_count", 0)), "📋"),
        ("Reconciled", str(summary.get("reconciled_count", 0)), "🔄")
    ]
    
    for idx, (label, value, icon) in enumerate(items, 3):
        summary_sheet.cell(row=idx, column=1, value=f"{icon} {label}")
        summary_sheet.cell(row=idx, column=1).font = Font(size=11, bold=True)
        summary_sheet.cell(row=idx, column=2, value=value)
        summary_sheet.cell(row=idx, column=2).font = Font(size=11, color="1E40AF", bold=True)
        summary_sheet.cell(row=idx, column=2).alignment = right_align
    
    # Obligation breakdown
    row_num = len(items) + 5
    summary_sheet.cell(row=row_num, column=1, value="📊 OBLIGATION BREAKDOWN")
    summary_sheet.cell(row=row_num, column=1).font = Font(size=12, bold=True, color="1E40AF")
    row_num += 1
    
    obligation_breakdown = summary.get("obligation_breakdown", {})
    for ob_type, count in obligation_breakdown.items():
        summary_sheet.cell(row=row_num, column=1, value=f"  • {ob_type}")
        summary_sheet.cell(row=row_num, column=2, value=count)
        row_num += 1
    
    # Output
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    frappe.response['filename'] = f"Compliance_Liabilities_{today()}.xlsx"
    frappe.response['filecontent'] = output.read()
    frappe.response['type'] = 'binary'