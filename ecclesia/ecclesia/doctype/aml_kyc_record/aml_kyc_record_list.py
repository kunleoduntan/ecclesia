# ecclesia/ecclesia/doctype/aml_kyc_record/aml_kyc_record_list.py

import frappe
from frappe import _
from frappe.utils import today, getdate, flt
import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import io


@frappe.whitelist()
def get_aml_summary(filters=None):
    """Get AML KYC summary statistics"""
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    if not filters:
        filters = {}
    
    query_filters = {}
    if filters.get("risk_rating"):
        query_filters["risk_rating"] = filters["risk_rating"]
    if filters.get("party_type"):
        query_filters["party_type"] = filters["party_type"]
    
    records = frappe.get_all(
        "AML KYC Record",
        filters=query_filters,
        fields=["name", "risk_rating", "is_pep", "sanctions_match", "identity_verified"]
    )
    
    total_count = len(records)
    low_count = sum(1 for r in records if r.risk_rating == "Low")
    medium_count = sum(1 for r in records if r.risk_rating == "Medium")
    high_count = sum(1 for r in records if r.risk_rating in ["High", "PEP — High", "Sanctioned — Blocked"])
    pep_count = sum(1 for r in records if r.is_pep)
    sanctioned_count = sum(1 for r in records if r.sanctions_match)
    verified_count = sum(1 for r in records if r.identity_verified)
    
    return {
        "total_count": total_count,
        "low_count": low_count,
        "medium_count": medium_count,
        "high_count": high_count,
        "pep_count": pep_count,
        "sanctioned_count": sanctioned_count,
        "verified_count": verified_count
    }


@frappe.whitelist(allow_guest=True)
def export_aml_excel():
    """Export AML KYC data to Excel with professional formatting"""
    filters = frappe.form_dict.get("filters", {})
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    query_filters = {}
    if filters.get("risk_rating"):
        query_filters["risk_rating"] = filters["risk_rating"]
    if filters.get("party_type"):
        query_filters["party_type"] = filters["party_type"]
    
    records = frappe.get_all(
        "AML KYC Record",
        filters=query_filters,
        fields=["name", "party_name_display", "party_type", "kyc_level", "risk_rating",
                "kyc_date", "kyc_expiry_date", "identity_verified", "address_verified",
                "beneficial_owner_identified", "pep_check_done", "is_pep",
                "sanctions_check_done", "sanctions_match", "responsible_officer"],
        order_by="kyc_date desc"
    )
    
    wb = Workbook()
    ws = wb.active
    ws.title = "AML KYC Records"
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
    columns = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N']
    widths = [16, 25, 14, 30, 16, 14, 16, 10, 10, 10, 10, 10, 10, 20]
    for col, width in zip(columns, widths):
        ws.column_dimensions[col].width = width
    
    # Title
    ws.merge_cells('A1:N1')
    ws['A1'] = "🔒 AML / KYC RECORDS"
    ws['A1'].font = title_font
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 35
    
    ws.merge_cells('A2:N2')
    ws['A2'] = f"Generated: {frappe.utils.formatdate(today())} | Total Records: {len(records)}"
    ws['A2'].font = subtitle_font
    ws['A2'].alignment = Alignment(horizontal='center', vertical='center')
    
    # Headers
    headers = ["#", "Party Name", "Type", "KYC Level", "Risk", "KYC Date", "Expiry",
               "ID", "Addr", "Beneficial", "PEP", "PEP Status", "Sanctions", "Officer"]
    row_num = 4
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row_num, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align
        cell.border = thin_border
    ws.row_dimensions[row_num].height = 28
    
    # Risk color mapping
    risk_colors = {
        "Low": "16A34A",
        "Medium": "F59E0B",
        "High": "DC2626",
        "PEP — High": "DC2626",
        "Sanctioned — Blocked": "991B1B"
    }
    
    # Data rows
    for idx, rec in enumerate(records, 1):
        row_num = 4 + idx
        values = [
            idx,
            rec.party_name_display or "",
            rec.party_type or "",
            rec.kyc_level or "",
            rec.risk_rating or "",
            frappe.utils.formatdate(rec.kyc_date) if rec.kyc_date else "",
            frappe.utils.formatdate(rec.kyc_expiry_date) if rec.kyc_expiry_date else "",
            "Yes" if rec.identity_verified else "No",
            "Yes" if rec.address_verified else "No",
            "Yes" if rec.beneficial_owner_identified else "No",
            "Yes" if rec.pep_check_done else "No",
            "Yes" if rec.is_pep else "No",
            "Yes" if rec.sanctions_match else "No",
            rec.responsible_officer or ""
        ]
        
        for col, value in enumerate(values, 1):
            cell = ws.cell(row=row_num, column=col, value=value)
            cell.border = thin_border
            
            if col in [1, 3, 4, 5, 8, 9, 10, 11, 12, 13]:
                cell.alignment = center_align
            else:
                cell.alignment = left_align
            
            if idx % 2 == 0:
                cell.fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
            
            # Risk cell coloring
            if col == 5:
                risk = values[4]
                color = risk_colors.get(risk, "64748B")
                cell.font = Font(color=color, bold=True)
                if risk in ["High", "PEP — High", "Sanctioned — Blocked"]:
                    cell.fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
                elif risk == "Medium":
                    cell.fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
                elif risk == "Low":
                    cell.fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
        
        ws.row_dimensions[row_num].height = 22
    
    ws.freeze_panes = 'A5'
    ws.auto_filter.ref = f'A4:N{4 + len(records)}'
    
    # Summary sheet
    summary_sheet.column_dimensions['A'].width = 25
    summary_sheet.column_dimensions['B'].width = 20
    
    summary_sheet.merge_cells('A1:B1')
    summary_sheet['A1'] = "📋 AML KYC SUMMARY"
    summary_sheet['A1'].font = Font(name="Segoe UI", size=14, bold=True, color="5B21B6")
    summary_sheet['A1'].alignment = Alignment(horizontal='center')
    summary_sheet.row_dimensions[1].height = 30
    
    summary = get_aml_summary(filters)
    
    items = [
        ("Total Records", str(summary.get("total_count", 0))),
        ("Low Risk", str(summary.get("low_count", 0))),
        ("Medium Risk", str(summary.get("medium_count", 0))),
        ("High Risk", str(summary.get("high_count", 0))),
        ("PEP Identified", str(summary.get("pep_count", 0))),
        ("Sanctions Match", str(summary.get("sanctioned_count", 0))),
        ("Identity Verified", str(summary.get("verified_count", 0)))
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
    
    frappe.response['filename'] = f"AML_KYC_Records_{today()}.xlsx"
    frappe.response['filecontent'] = output.read()
    frappe.response['type'] = 'binary'