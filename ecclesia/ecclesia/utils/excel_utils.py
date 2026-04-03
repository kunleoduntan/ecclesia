# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ecclesia and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, cint, getdate, nowdate
import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter
import io
import json


def get_excel_template(doctype):
    """Generate Excel template for importing data"""
    
    meta = frappe.get_meta(doctype)
    
    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Template"
    
    # Add instructions sheet
    instructions_ws = wb.create_sheet("Instructions")
    add_instructions(instructions_ws, doctype)
    
    # Header styling
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    
    # Get fields for template
    fields = get_importable_fields(meta)
    
    # Add headers
    for col_idx, field in enumerate(fields, 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.value = field.get("label")
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        
        # Add field description in second row
        desc_cell = ws.cell(row=2, column=col_idx)
        desc_cell.value = field.get("description", "")
        desc_cell.font = Font(italic=True, size=9)
        
        # Add mandatory indicator
        if field.get("reqd"):
            cell.value = f"{field.get('label')} *"
    
    # Add sample data row
    add_sample_data(ws, fields, 3)
    
    # Add dropdowns for select fields
    add_dropdowns(ws, fields)
    
    # Auto-fit columns
    for col_idx, field in enumerate(fields, 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = 20
    
    # Freeze header rows
    ws.freeze_panes = "A3"
    
    return wb


def get_importable_fields(meta):
    """Get list of fields that can be imported"""
    
    importable_fields = []
    
    for field in meta.fields:
        # Skip certain field types
        if field.fieldtype in [
            "Section Break", "Column Break", "HTML", "Button", 
            "Table", "Table MultiSelect", "Attach Image", "Signature"
        ]:
            continue
        
        # Skip read-only fields (except for linking)
        if field.read_only and field.fieldtype != "Link":
            continue
        
        importable_fields.append({
            "fieldname": field.fieldname,
            "label": field.label,
            "fieldtype": field.fieldtype,
            "options": field.options,
            "reqd": field.reqd,
            "description": field.description
        })
    
    return importable_fields


def add_instructions(ws, doctype):
    """Add instructions to the template"""
    
    instructions = [
        ["Excel Import Template - " + doctype, ""],
        ["", ""],
        ["Instructions:", ""],
        ["1.", "Fill in the template with your data starting from row 3"],
        ["2.", "Fields marked with * are mandatory"],
        ["3.", "For Link fields, enter the exact name of the linked document"],
        ["4.", "For Date fields, use format: YYYY-MM-DD (e.g., 2026-02-04)"],
        ["5.", "For Select fields, choose from the dropdown list"],
        ["6.", "Do not modify the header row"],
        ["7.", "Save the file and upload through the Import Tool"],
        ["", ""],
        ["Field Types:", ""],
        ["Link", "Reference to another document"],
        ["Select", "Choose from predefined options"],
        ["Date", "Date in YYYY-MM-DD format"],
        ["Currency", "Numeric value for money"],
        ["Check", "1 for checked, 0 for unchecked"],
    ]
    
    # Add instructions
    for row_idx, instruction in enumerate(instructions, 1):
        ws.cell(row=row_idx, column=1).value = instruction[0]
        ws.cell(row=row_idx, column=2).value = instruction[1]
    
    # Style header
    ws.cell(row=1, column=1).font = Font(size=14, bold=True)


def add_sample_data(ws, fields, start_row):
    """Add sample data row"""
    
    sample_data = {
        "Data": "Sample Value",
        "Link": "Example Document",
        "Select": "Option 1",
        "Date": "2026-02-04",
        "Currency": "1000.00",
        "Int": "10",
        "Check": "1",
        "Float": "10.5",
        "Percent": "50"
    }
    
    for col_idx, field in enumerate(fields, 1):
        cell = ws.cell(row=start_row, column=col_idx)
        cell.value = sample_data.get(field["fieldtype"], "Sample")
        cell.font = Font(italic=True, color="808080")


def add_dropdowns(ws, fields):
    """Add data validation dropdowns for select fields"""
    from openpyxl.worksheet.datavalidation import DataValidation
    
    for col_idx, field in enumerate(fields, 1):
        if field["fieldtype"] == "Select" and field.get("options"):
            options = field["options"].split("\n")
            
            # Create dropdown validation
            dv = DataValidation(
                type="list",
                formula1=f'"{",".join(options)}"',
                allow_blank=not field.get("reqd")
            )
            
            # Apply to column (rows 3 to 1000)
            col_letter = get_column_letter(col_idx)
            dv.add(f"{col_letter}3:{col_letter}1000")
            ws.add_data_validation(dv)


@frappe.whitelist()
def download_excel_template(doctype):
    """API endpoint to download Excel template"""
    
    wb = get_excel_template(doctype)
    
    # Save to bytes
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    frappe.response['filename'] = f'{doctype}_Import_Template.xlsx'
    frappe.response['filecontent'] = output.read()
    frappe.response['type'] = 'binary'


@frappe.whitelist()
def import_from_excel(doctype, file_content):
    """Import data from Excel file"""
    
    import base64
    
    # Decode file content
    file_bytes = base64.b64decode(file_content)
    
    # Load workbook
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes))
    ws = wb.active
    
    # Get headers from first row
    headers = []
    for cell in ws[1]:
        if cell.value:
            # Remove mandatory indicator
            header = cell.value.replace(" *", "")
            headers.append(header)
    
    # Get field mapping
    meta = frappe.get_meta(doctype)
    field_map = {}
    for field in meta.fields:
        field_map[field.label] = field.fieldname
    
    # Import data
    imported = []
    errors = []
    
    for row_idx, row in enumerate(ws.iter_rows(min_row=3), start=3):
        try:
            # Skip empty rows
            if not any(cell.value for cell in row):
                continue
            
            # Build document dict
            doc_dict = {"doctype": doctype}
            
            for col_idx, cell in enumerate(row):
                if col_idx >= len(headers):
                    break
                
                header = headers[col_idx]
                fieldname = field_map.get(header)
                
                if not fieldname:
                    continue
                
                value = cell.value
                
                # Process value based on field type
                field = meta.get_field(fieldname)
                if field:
                    value = process_field_value(value, field)
                
                doc_dict[fieldname] = value
            
            # Create document
            doc = frappe.get_doc(doc_dict)
            doc.insert()
            
            imported.append(doc.name)
        
        except Exception as e:
            error_msg = f"Row {row_idx}: {str(e)}"
            errors.append(error_msg)
            frappe.log_error(frappe.get_traceback(), f"Excel Import Error - Row {row_idx}")
    
    return {
        "success": True,
        "imported_count": len(imported),
        "imported_records": imported,
        "error_count": len(errors),
        "errors": errors
    }


def process_field_value(value, field):
    """Process field value based on field type"""
    
    if value is None or value == "":
        return None
    
    fieldtype = field.fieldtype
    
    if fieldtype in ["Currency", "Float"]:
        return flt(value)
    
    elif fieldtype == "Int":
        return cint(value)
    
    elif fieldtype == "Date":
        if isinstance(value, str):
            return getdate(value)
        return value
    
    elif fieldtype == "Check":
        if isinstance(value, str):
            return 1 if value.lower() in ["1", "yes", "true", "checked"] else 0
        return cint(value)
    
    return value


@frappe.whitelist()
def export_to_excel(doctype, filters=None, fields=None):
    """Export data to Excel"""
    
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    if isinstance(fields, str):
        fields = json.loads(fields)
    
    # Get data
    data = frappe.get_all(doctype, filters=filters or {}, fields=fields or ["*"])
    
    if not data:
        frappe.throw(_("No data to export"))
    
    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = doctype
    
    # Header styling
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Add headers
    headers = list(data[0].keys())
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.value = header.replace("_", " ").title()
        cell.fill = header_fill
        cell.font = header_font
        cell.border = border
        cell.alignment = Alignment(horizontal="center", vertical="center")
    
    # Add data
    for row_idx, row_data in enumerate(data, 2):
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.value = row_data.get(header)
            cell.border = border
            
            # Format based on value type
            value = row_data.get(header)
            if isinstance(value, (int, float)):
                cell.alignment = Alignment(horizontal="right")
            elif isinstance(value, str) and len(value) > 50:
                cell.alignment = Alignment(wrap_text=True)
    
    # Auto-fit columns
    for col_idx in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = 20
    
    # Freeze header row
    ws.freeze_panes = "A2"
    
    # Add summary sheet
    summary_ws = wb.create_sheet("Summary")
    add_export_summary(summary_ws, doctype, len(data))
    
    # Save to bytes
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    frappe.response['filename'] = f'{doctype}_Export_{nowdate()}.xlsx'
    frappe.response['filecontent'] = output.read()
    frappe.response['type'] = 'binary'


def add_export_summary(ws, doctype, record_count):
    """Add summary information to export"""
    
    summary = [
        ["Export Summary", ""],
        ["", ""],
        ["Document Type:", doctype],
        ["Total Records:", record_count],
        ["Export Date:", nowdate()],
        ["Exported By:", frappe.session.user],
    ]
    
    for row_idx, row in enumerate(summary, 1):
        ws.cell(row=row_idx, column=1).value = row[0]
        ws.cell(row=row_idx, column=2).value = row[1]
        
        if row_idx == 1:
            ws.cell(row=row_idx, column=1).font = Font(size=14, bold=True)


# Bulk operations utilities

@frappe.whitelist()
def bulk_update_assets(assets, field, value):
    """Bulk update assets"""
    
    if isinstance(assets, str):
        assets = json.loads(assets)
    
    updated = []
    errors = []
    
    for asset in assets:
        try:
            asset_doc = frappe.get_doc("Fixed Asset", asset)
            asset_doc.set(field, value)
            asset_doc.save()
            updated.append(asset)
        
        except Exception as e:
            errors.append(f"{asset}: {str(e)}")
            frappe.log_error(frappe.get_traceback(), f"Bulk Update Error - {asset}")
    
    return {
        "success": True,
        "updated_count": len(updated),
        "updated_records": updated,
        "error_count": len(errors),
        "errors": errors
    }


@frappe.whitelist()
def bulk_delete_assets(assets):
    """Bulk delete assets"""
    
    if isinstance(assets, str):
        assets = json.loads(assets)
    
    deleted = []
    errors = []
    
    for asset in assets:
        try:
            asset_doc = frappe.get_doc("Fixed Asset", asset)
            
            # Check if asset can be deleted
            if asset_doc.docstatus == 1:
                errors.append(f"{asset}: Cannot delete submitted asset")
                continue
            
            asset_doc.delete()
            deleted.append(asset)
        
        except Exception as e:
            errors.append(f"{asset}: {str(e)}")
            frappe.log_error(frappe.get_traceback(), f"Bulk Delete Error - {asset}")
    
    return {
        "success": True,
        "deleted_count": len(deleted),
        "deleted_records": deleted,
        "error_count": len(errors),
        "errors": errors
    }