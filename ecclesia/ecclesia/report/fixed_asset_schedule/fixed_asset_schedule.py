# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt



import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate, add_months
from frappe.model.document import Document
import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter
from io import BytesIO
import base64

def execute(filters=None):
    if not filters:
        filters = {}
    
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    
    # Add summary statistics
    summary = get_summary(data)
    
    return columns, data, None, chart, summary

def get_columns():
    """Define the columns for the report"""
    return [
        {
            "label": _("Asset Code"),
            "fieldname": "asset_code",
            "fieldtype": "Data",
            "width": 140
        },
        {
            "label": _("Asset Name"),
            "fieldname": "asset_name",
            "fieldtype": "Data",
            "width": 200
        },
        {
            "label": _("Category"),
            "fieldname": "asset_category",
            "fieldtype": "Link",
            "options": "Fixed Asset Category",
            "width": 150
        },
        {
            "label": _("Status"),
            "fieldname": "asset_status",
            "fieldtype": "Data",
            "width": 140
        },
        {
            "label": _("Location"),
            "fieldname": "current_location",
            "fieldtype": "Link",
            "options": "Warehouse",
            "width": 150
        },
        {
            "label": _("Department"),
            "fieldname": "department",
            "fieldtype": "Link",
            "options": "Department",
            "width": 150
        },
        {
            "label": _("Cost Center"),
            "fieldname": "cost_center",
            "fieldtype": "Link",
            "options": "Cost Center",
            "width": 150
        },
        {
            "label": _("Purchase Date"),
            "fieldname": "purchase_date",
            "fieldtype": "Date",
            "width": 120
        },
        {
            "label": _("Gross Value"),
            "fieldname": "current_gross_value",
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "label": _("Accumulated Depreciation"),
            "fieldname": "current_accumulated_depreciation",
            "fieldtype": "Currency",
            "width": 160
        },
        {
            "label": _("Net Book Value"),
            "fieldname": "current_net_book_value",
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "label": _("Depreciation %"),
            "fieldname": "depreciation_percentage_complete",
            "fieldtype": "Percent",
            "width": 120
        },
        {
            "label": _("Next Depreciation"),
            "fieldname": "next_depreciation_date",
            "fieldtype": "Date",
            "width": 130
        },
        {
            "label": _("Custodian"),
            "fieldname": "custodian",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 150
        }
    ]

def get_data(filters):
    """Fetch data from the database with filters"""
    conditions = get_conditions(filters)
    
    query = f"""
        SELECT
            fa.name,
            fa.asset_code,
            fa.asset_name,
            fa.asset_category,
            fa.asset_status,
            fa.current_location,
            fa.department,
            fa.cost_center,
            fa.purchase_date,
            fa.current_gross_value,
            fa.current_accumulated_depreciation,
            fa.current_net_book_value,
            fa.depreciation_percentage_complete,
            fa.next_depreciation_date,
            fa.custodian,
            fa.is_depreciable_asset,
            fa.company
        FROM
            `tabFixed Asset` fa
        WHERE
            fa.docstatus != 2
            {conditions}
        ORDER BY
            fa.asset_category, fa.asset_name
    """
    
    data = frappe.db.sql(query, filters, as_dict=1)
    
    # Format data for display
    for row in data:
        # Add status color indicators
        row["asset_status_display"] = row.asset_status
        row["_status_color"] = get_status_color(row.asset_status)
        
        # Format numeric values for display
        row["current_gross_value"] = flt(row.current_gross_value)
        row["current_accumulated_depreciation"] = flt(row.current_accumulated_depreciation)
        row["current_net_book_value"] = flt(row.current_net_book_value)
        row["depreciation_percentage_complete"] = flt(row.depreciation_percentage_complete)
    
    return data

def get_conditions(filters):
    """Build the WHERE clause based on filters"""
    conditions = []
    
    if filters.get("company"):
        conditions.append("fa.company = %(company)s")
    
    if filters.get("asset_category"):
        conditions.append("fa.asset_category = %(asset_category)s")
    
    if filters.get("department"):
        conditions.append("fa.department = %(department)s")
    
    if filters.get("cost_center"):
        conditions.append("fa.cost_center = %(cost_center)s")
    
    if filters.get("asset_status"):
        if filters.get("asset_status") != "All":
            conditions.append("fa.asset_status = %(asset_status)s")
    
    if filters.get("from_date") and filters.get("to_date"):
        conditions.append("fa.purchase_date BETWEEN %(from_date)s AND %(to_date)s")
    
    if filters.get("is_depreciable"):
        if filters.get("is_depreciable") == 1:
            conditions.append("fa.is_depreciable_asset = 1")
    
    return "AND " + " AND ".join(conditions) if conditions else ""

def get_status_color(status):
    """Return color code for status"""
    colors = {
        "Active": "#28a745",
        "Draft": "#6c757d",
        "Under Maintenance": "#ffc107",
        "Disposed": "#dc3545",
        "Fully Depreciated": "#17a2b8",
        "Scrapped": "#6c757d",
        "Transferred": "#fd7e14"
    }
    return colors.get(status, "#6c757d")

def get_chart(data):
    """Generate chart data for the report"""
    if not data:
        return None
    
    # Group by status
    status_counts = {}
    for row in data:
        status = row.asset_status or "Unknown"
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # Group by category
    category_counts = {}
    for row in data:
        category = row.asset_category or "Uncategorized"
        category_counts[category] = category_counts.get(category, 0) + 1
    
    # Calculate total values
    total_gross = sum(flt(row.current_gross_value) for row in data)
    total_nbv = sum(flt(row.current_net_book_value) for row in data)
    total_dep = sum(flt(row.current_accumulated_depreciation) for row in data)
    
    return {
        "data": {
            "labels": list(status_counts.keys()),
            "datasets": [
                {
                    "name": _("Asset Status"),
                    "values": list(status_counts.values()),
                    "colors": ["#28a745", "#6c757d", "#ffc107", "#dc3545", "#17a2b8", "#fd7e14"]
                }
            ]
        },
        "type": "donut",
        "height": 300,
        "fieldname": "asset_status"
    }

def get_summary(data):
    """Calculate summary statistics"""
    if not data:
        return []
    
    total_assets = len(data)
    total_gross_value = sum(flt(row.current_gross_value) for row in data)
    total_accumulated_dep = sum(flt(row.current_accumulated_depreciation) for row in data)
    total_net_book_value = sum(flt(row.current_net_book_value) for row in data)
    
    # Count by status
    status_counts = {}
    for row in data:
        status = row.asset_status or "Unknown"
        status_counts[status] = status_counts.get(status, 0) + 1
    
    summary = [
        {
            "label": _("Total Assets"),
            "value": total_assets,
            "datatype": "Int"
        },
        {
            "label": _("Total Gross Value"),
            "value": total_gross_value,
            "datatype": "Currency"
        },
        {
            "label": _("Total Accumulated Depreciation"),
            "value": total_accumulated_dep,
            "datatype": "Currency"
        },
        {
            "label": _("Total Net Book Value"),
            "value": total_net_book_value,
            "datatype": "Currency"
        }
    ]
    
    # Add status breakdown
    for status, count in status_counts.items():
        summary.append({
            "label": _(f"{status} Assets"),
            "value": count,
            "datatype": "Int"
        })
    
    return summary

@frappe.whitelist()
def get_excel_data(filters=None):
    """Generate Excel data with beautiful formatting"""
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    # Get data
    data = get_data(filters)
    columns = get_columns()
    
    # Create workbook
    wb = Workbook()
    
    # Create main sheet
    ws = wb.active
    ws.title = "Fixed Asset Schedule"
    
    # Define styles
    header_fill = PatternFill(start_color="1a5276", end_color="1a5276", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_border = Border(
        bottom=Side(style='medium', color='1a5276')
    )
    
    # Title row
    ws.merge_cells('A1:N1')
    title_cell = ws['A1']
    title_cell.value = "FIXED ASSET SCHEDULE REPORT"
    title_cell.font = Font(bold=True, size=14, color="1a5276")
    title_cell.alignment = Alignment(horizontal='center')
    
    # Date row
    ws.merge_cells('A2:N2')
    date_cell = ws['A2']
    date_cell.value = f"Generated on: {formatdate(getdate())}"
    date_cell.font = Font(size=10, italic=True, color="666666")
    date_cell.alignment = Alignment(horizontal='center')
    
    # Filter info row
    filter_text = get_filter_description(filters)
    ws.merge_cells('A3:N3')
    filter_cell = ws['A3']
    filter_cell.value = filter_text
    filter_cell.font = Font(size=10, color="555555")
    filter_cell.alignment = Alignment(horizontal='center')
    
    # Write headers starting from row 5
    header_row = 5
    for col_idx, col in enumerate(columns, 1):
        cell = ws.cell(row=header_row, column=col_idx)
        cell.value = col.get("label", "")
        cell.fill = header_fill
        cell.font = header_font
        cell.border = header_border
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # Write data
    row_num = header_row + 1
    for record in data:
        for col_idx, col in enumerate(columns, 1):
            fieldname = col.get("fieldname")
            value = record.get(fieldname)
            
            # Format values
            if col.get("fieldtype") == "Currency":
                if value:
                    value = flt(value)
            
            cell = ws.cell(row=row_num, column=col_idx)
            cell.value = value
            
            # Apply alternating row colors
            if row_num % 2 == 0:
                cell.fill = PatternFill(start_color="f8f9fa", end_color="f8f9fa", fill_type="solid")
            else:
                cell.fill = PatternFill(start_color="ffffff", end_color="ffffff", fill_type="solid")
            
            # Apply status color
            if fieldname == "asset_status":
                color = get_status_color(value)
                cell.fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
                cell.font = Font(color="FFFFFF", bold=True)
            
            # Right align numbers
            if col.get("fieldtype") in ["Currency", "Percent", "Int", "Float"]:
                cell.alignment = Alignment(horizontal='right')
            else:
                cell.alignment = Alignment(horizontal='left')
        
        row_num += 1
    
    # Auto-size columns
    for col_idx, col in enumerate(columns, 1):
        max_length = len(col.get("label", ""))
        column_letter = get_column_letter(col_idx)
        
        # Check data length
        for row in range(header_row + 1, row_num):
            cell_value = ws.cell(row=row, column=col_idx).value
            if cell_value:
                max_length = max(max_length, len(str(cell_value)))
        
        # Set column width with some padding
        ws.column_dimensions[column_letter].width = min(max_length + 5, 50)
    
    # Summary sheet
    summary_ws = wb.create_sheet("Summary")
    summary_data = get_summary(data)
    
    # Summary header
    summary_ws.merge_cells('A1:B1')
    summary_cell = summary_ws['A1']
    summary_cell.value = "SUMMARY STATISTICS"
    summary_cell.font = Font(bold=True, size=14, color="1a5276")
    summary_cell.alignment = Alignment(horizontal='center')
    
    # Write summary data
    row = 3
    for item in summary_data:
        label_cell = summary_ws.cell(row=row, column=1)
        label_cell.value = item.get("label")
        label_cell.font = Font(bold=True)
        
        value_cell = summary_ws.cell(row=row, column=2)
        value = item.get("value")
        if item.get("datatype") == "Currency":
            value_cell.value = flt(value)
            value_cell.number_format = '#,##0.00'
        else:
            value_cell.value = value
        
        row += 1
    
    # Style summary sheet
    summary_ws.column_dimensions['A'].width = 40
    summary_ws.column_dimensions['B'].width = 20
    
    # Save to BytesIO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    # Convert to base64
    excel_data = base64.b64encode(output.getvalue()).decode()
    return excel_data

def get_filter_description(filters):
    """Generate a description of applied filters"""
    if not filters:
        return "All Assets"
    
    parts = []
    filter_labels = {
        "company": "Company",
        "asset_category": "Category",
        "department": "Department",
        "cost_center": "Cost Center",
        "asset_status": "Status",
        "from_date": "From Date",
        "to_date": "To Date",
        "is_depreciable": "Depreciable Only"
    }
    
    for key, label in filter_labels.items():
        if filters.get(key):
            value = filters.get(key)
            if key == "is_depreciable" and value == 1:
                parts.append("Depreciable Assets Only")
            elif key not in ["from_date", "to_date", "is_depreciable"]:
                parts.append(f"{label}: {value}")
    
    if filters.get("from_date") and filters.get("to_date"):
        parts.append(f"Purchase Date: {filters.get('from_date')} to {filters.get('to_date')}")
    
    return " | ".join(parts) if parts else "All Assets"

@frappe.whitelist()
def download_excel(filters=None):
    """Download the report as Excel"""
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    excel_data = get_excel_data(filters)
    
    frappe.response["filename"] = f"Fixed_Asset_Schedule_{getdate()}.xlsx"
    frappe.response["filecontent"] = base64.b64decode(excel_data)
    frappe.response["type"] = "download"
    frappe.response["content_type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"