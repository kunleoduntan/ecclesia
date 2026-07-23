# ecclesia/ecclesia/doctype/environmental_compliance_record/environmental_compliance_record_list.py

import frappe
from frappe import _
from frappe.utils import today, getdate, flt
import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import io


@frappe.whitelist()
def get_env_summary(filters=None):
    """Get Environmental Compliance Record summary statistics"""
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    if not filters:
        filters = {}
    
    query_filters = {}
    if filters.get("status"):
        query_filters["status"] = filters["status"]
    if filters.get("permit_type"):
        query_filters["permit_type"] = filters["permit_type"]
    
    records = frappe.get_all(
        "Environmental Compliance Record",
        filters=query_filters,
        fields=["name", "status", "permit_type", "expiry_date", "last_inspection_result"]
    )
    
    total_count = len(records)
    active_count = sum(1 for r in records if r.status == "Active")
    expiring_count = sum(1 for r in records if r.status == "Expiring Soon")
    expired_count = sum(1 for r in records if r.status == "Expired")
    under_renewal_count = sum(1 for r in records if r.status == "Under Renewal")
    suspended_count = sum(1 for r in records if r.status == "Suspended")
    revoked_count = sum(1 for r in records if r.status == "Revoked")
    
    # Permit type breakdown
    type_counts = {}
    for r in records:
        pt = r.permit_type or "Other"
        type_counts[pt] = type_counts.get(pt, 0) + 1
    
    # Inspection results
    inspection_results = {}
    for r in records:
        ir = r.last_inspection_result or "Not Inspected"
        inspection_results[ir] = inspection_results.get(ir, 0) + 1
    
    return {
        "total_count": total_count,
        "active_count": active_count,
        "expiring_count": expiring_count,
        "expired_count": expired_count,
        "under_renewal_count": under_renewal_count,
        "suspended_count": suspended_count,
        "revoked_count": revoked_count,
        "eia_count": type_counts.get("Environmental Impact Assessment (EIA)", 0),
        "waste_count": type_counts.get("Waste Disposal Permit", 0),
        "type_breakdown": type_counts,
        "inspection_results": inspection_results
    }


@frappe.whitelist(allow_guest=True)
def export_env_excel():
    """Export Environmental Compliance data to Excel with professional formatting"""
    filters = frappe.form_dict.get("filters", {})
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    query_filters = {}
    if filters.get("status"):
        query_filters["status"] = filters["status"]
    if filters.get("permit_type"):
        query_filters["permit_type"] = filters["permit_type"]
    if filters.get("issuing_authority"):
        query_filters["issuing_authority"] = filters["issuing_authority"]
    
    records = frappe.get_all(
        "Environmental Compliance Record",
        filters=query_filters,
        fields=["name", "permit_title", "permit_type", "facility", "issuing_authority",
                "permit_number", "issue_date", "expiry_date", "status", 
                "last_inspection_date", "last_inspection_result", "renewal_cost"],
        order_by="expiry_date asc"
    )
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Environmental Compliance"
    summary_sheet = wb.create_sheet("Summary")
    
    # Styles
    header_fill = PatternFill(start_color="15803D", end_color="15803D", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Segoe UI", size=16, bold=True, color="15803D")
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
    widths = [8, 28, 20, 18, 20, 16, 14, 16, 16, 16, 18, 16]
    for col, width in zip(columns, widths):
        ws.column_dimensions[col].width = width
    
    # Title
    ws.merge_cells('A1:L1')
    ws['A1'] = "🌿 ENVIRONMENTAL COMPLIANCE RECORDS"
    ws['A1'].font = title_font
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 35
    
    ws.merge_cells('A2:L2')
    ws['A2'] = f"Generated: {frappe.utils.formatdate(today())} | Total Records: {len(records)}"
    ws['A2'].font = subtitle_font
    ws['A2'].alignment = Alignment(horizontal='center', vertical='center')
    
    # Headers
    headers = ["#", "Permit Title", "Permit Type", "Facility", "Issuing Authority",
               "Permit Number", "Issue Date", "Expiry Date", "Status", 
               "Last Inspection", "Inspection Result", "Renewal Cost"]
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
            rec.permit_type or "",
            rec.facility or "",
            rec.issuing_authority or "",
            rec.permit_number or "",
            frappe.utils.formatdate(rec.issue_date) if rec.issue_date else "",
            frappe.utils.formatdate(rec.expiry_date) if rec.expiry_date else "",
            rec.status or "",
            frappe.utils.formatdate(rec.last_inspection_date) if rec.last_inspection_date else "",
            rec.last_inspection_result or "Not Inspected",
            flt(rec.renewal_cost or 0)
        ]
        
        for col, value in enumerate(values, 1):
            cell = ws.cell(row=row_num, column=col, value=value)
            cell.border = thin_border
            
            if col in [1, 3, 6, 7, 8, 9, 10, 12]:
                cell.alignment = center_align
            elif col == 12:
                cell.alignment = right_align
                cell.number_format = '#,##0.00'
            else:
                cell.alignment = left_align
            
            if idx % 2 == 0:
                cell.fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
            
            # Status coloring
            if col == 9:
                status = values[8]
                if status == "Active":
                    cell.font = Font(color="16A34A", bold=True)
                    cell.fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
                elif status == "Expiring Soon":
                    cell.font = Font(color="F59E0B", bold=True)
                    cell.fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
                elif status == "Expired" or status == "Revoked":
                    cell.font = Font(color="DC2626", bold=True)
                    cell.fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
                elif status == "Under Renewal":
                    cell.font = Font(color="2563EB", bold=True)
                    cell.fill = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")
            
            # Expiry date coloring
            if col == 8 and rec.expiry_date:
                expiry = getdate(rec.expiry_date)
                today_dt = getdate(today())
                diff = (expiry - today_dt).days
                if diff < 0:
                    cell.font = Font(color="DC2626", bold=True)
                elif diff < 30:
                    cell.font = Font(color="F59E0B", bold=True)
            
            # Inspection result coloring
            if col == 11:
                result = values[10]
                if result == "Satisfactory":
                    cell.font = Font(color="16A34A", bold=True)
                elif result in ["Major Non-Compliance", "Prosecution"]:
                    cell.font = Font(color="DC2626", bold=True)
                elif result == "Minor Non-Compliance":
                    cell.font = Font(color="F59E0B", bold=True)
        
        ws.row_dimensions[row_num].height = 22
    
    ws.freeze_panes = 'A5'
    ws.auto_filter.ref = f'A4:L{4 + len(records)}'
    
    # Summary sheet
    summary_sheet.column_dimensions['A'].width = 25
    summary_sheet.column_dimensions['B'].width = 20
    
    summary_sheet.merge_cells('A1:B1')
    summary_sheet['A1'] = "📋 ENVIRONMENTAL COMPLIANCE SUMMARY"
    summary_sheet['A1'].font = Font(name="Segoe UI", size=14, bold=True, color="15803D")
    summary_sheet['A1'].alignment = Alignment(horizontal='center')
    summary_sheet.row_dimensions[1].height = 30
    
    summary = get_env_summary(filters)
    
    items = [
        ("Total Permits", str(summary.get("total_count", 0))),
        ("Active", str(summary.get("active_count", 0))),
        ("Expiring Soon", str(summary.get("expiring_count", 0))),
        ("Expired", str(summary.get("expired_count", 0))),
        ("Under Renewal", str(summary.get("under_renewal_count", 0))),
        ("Suspended", str(summary.get("suspended_count", 0))),
        ("Revoked", str(summary.get("revoked_count", 0)))
    ]
    
    for idx, (label, value) in enumerate(items, 3):
        summary_sheet.cell(row=idx, column=1, value=label)
        summary_sheet.cell(row=idx, column=1).font = Font(size=11, bold=True)
        summary_sheet.cell(row=idx, column=2, value=value)
        summary_sheet.cell(row=idx, column=2).font = Font(size=11, color="15803D", bold=True)
        summary_sheet.cell(row=idx, column=2).alignment = right_align
    
    # Inspection results
    row_num = len(items) + 5
    summary_sheet.cell(row=row_num, column=1, value="🔍 INSPECTION RESULTS")
    summary_sheet.cell(row=row_num, column=1).font = Font(size=12, bold=True, color="15803D")
    row_num += 1
    
    inspection_results = summary.get("inspection_results", {})
    for ir, count in inspection_results.items():
        summary_sheet.cell(row=row_num, column=1, value=f"  • {ir}")
        summary_sheet.cell(row=row_num, column=2, value=count)
        row_num += 1
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    frappe.response['filename'] = f"Environmental_Compliance_{today()}.xlsx"
    frappe.response['filecontent'] = output.read()
    frappe.response['type'] = 'binary'