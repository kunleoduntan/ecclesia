# Copyright (c) 2026, Ecclesia and contributors
# For license information, please see license.txt

# Copyright (c) 2026, Ecclesia and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate, add_months, today, date_diff
import json
from datetime import datetime, date
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment, numbers
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet
from io import BytesIO
import base64


def safe_getdate(value):
    """
    Bulletproof conversion to datetime.date.

    Returns None instead of raising for anything unparseable
    (None, '', '0000-00-00', stray strings, bytes, etc.) so callers
    never end up comparing a str/None against a date object, which is
    what was causing:
        TypeError: '<' not supported between instances of 'datetime.date' and 'str'
    """
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        value_str = value.decode() if isinstance(value, bytes) else str(value)
        value_str = value_str.split(" ")[0].strip()
        if not value_str or value_str.startswith("0000-00-00"):
            return None
        return datetime.strptime(value_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        try:
            parsed = getdate(value)
            return parsed if isinstance(parsed, date) else None
        except Exception:
            return None


def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data, summary = get_data(filters)
    chart = get_chart(data)

    return columns, data, None, chart, summary


def get_columns():
    """Define the columns for the report matching the image format"""
    return [
        {
            "label": _("Asset Category"),
            "fieldname": "asset_category",
            "fieldtype": "Link",
            "options": "Fixed Asset Category",
            "width": 200
        },
        {
            "label": _("Opening Cost"),
            "fieldname": "opening_cost",
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "label": _("Additions"),
            "fieldname": "additions",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": _("Reclassifications"),
            "fieldname": "reclassifications",
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "label": _("Revaluations"),
            "fieldname": "revaluations",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": _("Disposals"),
            "fieldname": "disposals",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": _("Write-off"),
            "fieldname": "write_off",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Exchange Difference"),
            "fieldname": "exchange_difference",
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "label": _("Closing Cost"),
            "fieldname": "closing_cost",
            "fieldtype": "Currency",
            "width": 140,
            "bold": 1
        },
        {
            "label": _("Opening Depreciation"),
            "fieldname": "opening_depreciation",
            "fieldtype": "Currency",
            "width": 160
        },
        {
            "label": _("Charge for Year"),
            "fieldname": "charge_for_year",
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "label": _("Revaluations"),
            "fieldname": "depreciation_revaluations",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": _("Disposals"),
            "fieldname": "depreciation_disposals",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": _("Write-off"),
            "fieldname": "depreciation_write_off",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Exchange Difference"),
            "fieldname": "depreciation_exchange_diff",
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "label": _("Closing Depreciation"),
            "fieldname": "closing_depreciation",
            "fieldtype": "Currency",
            "width": 160,
            "bold": 1
        },
        {
            "label": _("Current Year Net Book Value"),
            "fieldname": "current_year_nbv",
            "fieldtype": "Currency",
            "width": 170,
            "bold": 1
        },
        {
            "label": _("Prior Year Net Book Value"),
            "fieldname": "prior_year_nbv",
            "fieldtype": "Currency",
            "width": 170
        }
    ]


def get_data(filters):
    """Fetch and process data for the report"""

    # Get all asset categories
    categories = frappe.db.get_all(
        "Fixed Asset Category",
        fields=["name", "category_name"],
        order_by="name"
    )

    # Get financial year from filters
    fiscal_year = filters.get("fiscal_year")
    company = filters.get("company")
    asset_category_filter = filters.get("asset_category")

    # Get date objects - CONVERT TO DATE OBJECTS IMMEDIATELY
    from_date_str, to_date_str = get_fiscal_year_dates(fiscal_year)
    from_date_obj = safe_getdate(from_date_str)
    to_date_obj = safe_getdate(to_date_str)

    prev_from_date_str, prev_to_date_str = get_previous_fiscal_year_dates(from_date_str, to_date_str)

    report_data = []
    totals = {
        "opening_cost": 0,
        "additions": 0,
        "reclassifications": 0,
        "revaluations": 0,
        "disposals": 0,
        "write_off": 0,
        "exchange_difference": 0,
        "closing_cost": 0,
        "opening_depreciation": 0,
        "charge_for_year": 0,
        "depreciation_revaluations": 0,
        "depreciation_disposals": 0,
        "depreciation_write_off": 0,
        "depreciation_exchange_diff": 0,
        "closing_depreciation": 0,
        "current_year_nbv": 0,
        "prior_year_nbv": 0
    }

    for category in categories:
        # Apply category filter if set
        if asset_category_filter and category.name != asset_category_filter:
            continue

        row = get_category_data(
            category.name,
            from_date_obj,  # Pass date objects
            to_date_obj,    # Pass date objects
            company
        )
        if row:
            report_data.append(row)
            # Accumulate totals
            for key in totals.keys():
                totals[key] += flt(row.get(key, 0))

    # Add total row
    if report_data:
        total_row = {
            "asset_category": "TOTAL",
            "is_total_row": 1,
            **totals
        }
        report_data.append(total_row)

    # Get summary statistics
    summary = get_summary(report_data)

    return report_data, summary


def get_category_data(category, from_date, to_date, company=None):
    """Get data for a specific asset category including revaluations"""

    # Normalize the period boundaries too - never assume a caller
    # always hands us real date objects
    from_date = safe_getdate(from_date)
    to_date = safe_getdate(to_date)

    # Build company filter
    company_condition = ""
    company_params = []
    if company:
        company_condition = "AND company = %s"
        company_params.append(company)

    # Get all assets in this category
    assets = frappe.db.sql(f"""
        SELECT 
            name,
            asset_name,
            gross_purchase_amount,
            purchase_date,
            current_gross_value,
            current_accumulated_depreciation,
            opening_accumulated_depreciation,
            current_net_book_value,
            asset_status,
            company
        FROM `tabFixed Asset`
        WHERE 
            asset_category = %s
            AND docstatus != 2
            {company_condition}
    """, (category, *company_params) if company else (category,), as_dict=1)

    if not assets:
        return None

    # Initialize values
    opening_cost = 0
    additions = 0
    reclassifications = 0
    revaluations = 0
    disposals = 0
    write_off = 0
    exchange_difference = 0
    closing_cost = 0

    opening_depreciation = 0
    charge_for_year = 0
    depreciation_revaluations = 0
    depreciation_disposals = 0
    depreciation_write_off = 0
    depreciation_exchange_diff = 0
    closing_depreciation = 0

    # For each asset, determine its status during the period
    for asset in assets:
        try:
            gross_value = flt(asset.current_gross_value)
            current_dep = flt(asset.current_accumulated_depreciation)
            opening_dep = flt(asset.opening_accumulated_depreciation or 0)

            # SAFELY convert purchase_date - this is what was previously
            # only checking isinstance(purchase_date, str)/datetime and
            # letting other bad values (e.g. '0000-00-00', None-ish
            # values, odd driver types) slip through to the "<" compare
            purchase_date = safe_getdate(asset.purchase_date)

            # Skip if no usable purchase date - treat as opening balance
            if not purchase_date:
                if asset.asset_status not in ["Disposed", "Scrapped"]:
                    opening_cost += gross_value
                    opening_depreciation += opening_dep
                continue

            # NOW SAFELY COMPARE DATE OBJECTS - both sides are guaranteed
            # to be real datetime.date instances at this point
            if purchase_date < from_date:
                # Asset existed before fiscal year
                opening_cost += gross_value
                opening_depreciation += opening_dep
            elif from_date <= purchase_date <= to_date:
                # Asset acquired during the fiscal year
                additions += gross_value
                # If acquired during the year, opening depreciation is 0
                opening_depreciation += 0

            # GET REVALUATIONS FOR THIS ASSET DURING THE PERIOD
            reval_data = get_asset_revaluations(asset.name, from_date, to_date)
            if reval_data:
                # Revaluation affects gross value
                revaluations += flt(reval_data.get("total_revaluation_amount", 0))
                # Revaluation can also affect accumulated depreciation
                depreciation_revaluations += flt(reval_data.get("depreciation_impact", 0))

            # Check if asset was disposed during the year
            if asset.asset_status in ["Disposed", "Scrapped"]:
                # Get disposal date from asset disposal
                disposal_info = frappe.db.sql("""
                    SELECT 
                        disposal_date,
                        disposal_sale_proceeds,
                        gain_loss_on_disposal
                    FROM `tabFixed Asset Disposal`
                    WHERE asset = %s
                    AND docstatus = 1
                    AND disposal_date BETWEEN %s AND %s
                """, (asset.name, from_date, to_date), as_dict=1)

                if disposal_info:
                    disposals += gross_value
                    depreciation_disposals += current_dep

            # Check for write-offs (assets that were entered but not completed)
            if asset.asset_status == "Draft" and purchase_date and purchase_date >= from_date:
                write_off += gross_value
                depreciation_write_off += current_dep

            # Calculate closing values for active assets
            if asset.asset_status not in ["Disposed", "Scrapped", "Draft"]:
                closing_cost += gross_value
                closing_depreciation += current_dep

        except Exception:
            # Don't let one bad asset record take down the whole report -
            # log it and keep going with the rest of the category
            frappe.log_error(
                title=_("Property and Equipment Schedule - skipped asset"),
                message=frappe.get_traceback() + f"\nAsset: {asset.get('name')}, Category: {category}"
            )
            continue

    # Calculate depreciation charge for the year
    charge_for_year = closing_depreciation - opening_depreciation + depreciation_disposals

    # Calculate NBV
    current_year_nbv = closing_cost - closing_depreciation
    prior_year_nbv = opening_cost - opening_depreciation

    # Get category name for display
    category_name = frappe.db.get_value("Fixed Asset Category", category, "category_name") or category

    return {
        "asset_category": category_name,
        "opening_cost": opening_cost,
        "additions": additions,
        "reclassifications": reclassifications,
        "revaluations": revaluations,
        "disposals": disposals,
        "write_off": write_off,
        "exchange_difference": exchange_difference,
        "closing_cost": closing_cost,
        "opening_depreciation": opening_depreciation,
        "charge_for_year": charge_for_year,
        "depreciation_revaluations": depreciation_revaluations,
        "depreciation_disposals": depreciation_disposals,
        "depreciation_write_off": depreciation_write_off,
        "depreciation_exchange_diff": depreciation_exchange_diff,
        "closing_depreciation": closing_depreciation,
        "current_year_nbv": current_year_nbv,
        "prior_year_nbv": prior_year_nbv
    }


def get_asset_revaluations(asset_name, from_date, to_date):
    """Get revaluation data for a specific asset during the period"""

    # Defensive normalization here too, since this is also called
    # directly from create_revaluation_sheet()
    from_date = safe_getdate(from_date)
    to_date = safe_getdate(to_date)

    revaluations = frappe.db.sql("""
        SELECT 
            name,
            revaluation_date,
            current_gross_value,
            new_gross_value,
            revaluation_amount,
            percentage_change,
            revaluation_type,
            current_accumulated_depreciation
        FROM `tabFixed Asset Revaluation`
        WHERE 
            asset = %s
            AND docstatus = 1
            AND revaluation_date BETWEEN %s AND %s
        ORDER BY revaluation_date
    """, (asset_name, from_date, to_date), as_dict=1)

    if not revaluations:
        return None

    total_revaluation = 0
    depreciation_impact = 0

    for reval in revaluations:
        reval_amount = flt(reval.get("revaluation_amount", 0))
        total_revaluation += reval_amount

        # If it's an upward revaluation, it may also affect accumulated depreciation
        if reval.get("revaluation_type") == "Upward Revaluation":
            old_gross = flt(reval.get("current_gross_value", 0))
            new_gross = flt(reval.get("new_gross_value", 0))
            if old_gross > 0:
                ratio = new_gross / old_gross
                old_dep = flt(reval.get("current_accumulated_depreciation", 0))
                new_dep = old_dep * ratio
                depreciation_impact += (new_dep - old_dep)

    return {
        "total_revaluation_amount": total_revaluation,
        "depreciation_impact": depreciation_impact,
        "count": len(revaluations)
    }


def get_fiscal_year_dates(fiscal_year):
    """Get start and end dates for a fiscal year"""
    if not fiscal_year:
        # Default to current year
        year = getdate().year
        return f"{year}-01-01", f"{year}-12-31"

    # Parse fiscal year (e.g., "2025" -> 2025-01-01 to 2025-12-31)
    try:
        year = int(fiscal_year)
        return f"{year}-01-01", f"{year}-12-31"
    except (ValueError, TypeError):
        year = getdate().year
        return f"{year}-01-01", f"{year}-12-31"


def get_previous_fiscal_year_dates(from_date, to_date):
    """Get previous fiscal year dates"""
    from_date_dt = safe_getdate(from_date)
    prev_year = from_date_dt.year - 1
    return f"{prev_year}-01-01", f"{prev_year}-12-31"


def get_summary(data):
    """Calculate summary statistics"""
    if not data:
        return []

    # Get totals from the total row
    total_row = None
    for row in data:
        if row.get("is_total_row"):
            total_row = row
            break

    if not total_row:
        return []

    summary = [
        {
            "label": _("Total Cost"),
            "value": total_row.get("closing_cost", 0),
            "datatype": "Currency"
        },
        {
            "label": _("Total Accumulated Depreciation"),
            "value": total_row.get("closing_depreciation", 0),
            "datatype": "Currency"
        },
        {
            "label": _("Total Net Book Value"),
            "value": total_row.get("current_year_nbv", 0),
            "datatype": "Currency"
        },
        {
            "label": _("Additions During Year"),
            "value": total_row.get("additions", 0),
            "datatype": "Currency"
        },
        {
            "label": _("Revaluations During Year"),
            "value": total_row.get("revaluations", 0),
            "datatype": "Currency"
        },
        {
            "label": _("Disposals During Year"),
            "value": total_row.get("disposals", 0),
            "datatype": "Currency"
        },
        {
            "label": _("Depreciation Charge"),
            "value": total_row.get("charge_for_year", 0),
            "datatype": "Currency"
        }
    ]

    return summary


def get_chart(data):
    """Generate chart data"""
    if not data or len(data) < 2:
        return None

    # Remove total row for chart
    chart_data = [row for row in data if not row.get("is_total_row")]

    if not chart_data:
        return None

    labels = [row.get("asset_category") for row in chart_data]
    nbv_values = [row.get("current_year_nbv") for row in chart_data]
    cost_values = [row.get("closing_cost") for row in chart_data]
    reval_values = [row.get("revaluations") for row in chart_data]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": _("Net Book Value"),
                    "values": nbv_values,
                    "chartType": "bar"
                },
                {
                    "name": _("Total Cost"),
                    "values": cost_values,
                    "chartType": "bar"
                },
                {
                    "name": _("Revaluations"),
                    "values": reval_values,
                    "chartType": "bar"
                }
            ]
        },
        "type": "bar",
        "height": 300,
        "fieldname": "asset_category"
    }


@frappe.whitelist()
def get_excel_data(filters=None):
    """Generate Excel with format matching the image including revaluations"""
    if isinstance(filters, str):
        filters = json.loads(filters)

    if not filters:
        filters = {}

    data, summary = get_data(filters)
    columns = get_columns()

    # Create workbook
    wb = Workbook()

    # Main sheet
    ws = wb.active
    ws.title = "Property and Equipment"

    # Style definitions
    header_fill = PatternFill(start_color="1a5276", end_color="1a5276", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=10)
    subheader_fill = PatternFill(start_color="2c7fb0", end_color="2c7fb0", fill_type="solid")
    subheader_font = Font(bold=True, color="FFFFFF", size=9)
    total_fill = PatternFill(start_color="d4e6f1", end_color="d4e6f1", fill_type="solid")
    total_font = Font(bold=True, size=10)
    reval_fill = PatternFill(start_color="e8f4fd", end_color="e8f4fd", fill_type="solid")
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # Title
    ws.merge_cells('A1:R1')
    title_cell = ws['A1']
    title_cell.value = "PROPERTY AND EQUIPMENT SCHEDULE"
    title_cell.font = Font(bold=True, size=16, color="1a5276")
    title_cell.alignment = Alignment(horizontal='center', vertical='center')

    # Subtitle with date
    ws.merge_cells('A2:R2')
    date_cell = ws['A2']
    fiscal_year = filters.get("fiscal_year", getdate().year)
    date_cell.value = f"As at December 31, {fiscal_year}"
    date_cell.font = Font(size=12, color="333333")
    date_cell.alignment = Alignment(horizontal='center', vertical='center')

    # Company
    ws.merge_cells('A3:R3')
    company_cell = ws['A3']
    company_name = filters.get('company', 'All Companies')
    company_cell.value = f"Group - {company_name}"
    company_cell.font = Font(size=11, color="555555")
    company_cell.alignment = Alignment(horizontal='center', vertical='center')

    # Main headers - COST section
    cost_row = 5
    ws.merge_cells(f'A{cost_row}:A{cost_row+1}')
    cell = ws.cell(row=cost_row, column=1)
    cell.value = "Asset Category"
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = Alignment(horizontal='center', vertical='center')
    cell.border = border

    # Cost headers (8 columns including revaluations)
    cost_headers = ["Opening Cost", "Additions", "Reclassifications", "Revaluations", 
                    "Disposals", "Write-off", "Exchange Difference", "Closing Cost"]
    col_start = 2
    for i, header in enumerate(cost_headers):
        col = col_start + i
        ws.merge_cells(f'{get_column_letter(col)}{cost_row}:{get_column_letter(col)}{cost_row+1}')
        cell = ws.cell(row=cost_row, column=col)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = border

    # Accumulated Depreciation headers (7 columns including revaluations)
    dep_headers = ["Opening Depreciation", "Charge for Year", "Revaluations", 
                   "Disposals", "Write-off", "Exchange Difference", "Closing Depreciation"]
    col_start = 10
    for i, header in enumerate(dep_headers):
        col = col_start + i
        ws.merge_cells(f'{get_column_letter(col)}{cost_row}:{get_column_letter(col)}{cost_row+1}')
        cell = ws.cell(row=cost_row, column=col)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = border

    # Carrying Amounts headers
    carrying_headers = ["Current Year\nNet Book Value", "Prior Year\nNet Book Value"]
    col_start = 17
    for i, header in enumerate(carrying_headers):
        col = col_start + i
        ws.merge_cells(f'{get_column_letter(col)}{cost_row}:{get_column_letter(col)}{cost_row+1}')
        cell = ws.cell(row=cost_row, column=col)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = border

    # Section labels - COST
    section_row = cost_row + 2
    ws.merge_cells(f'A{section_row}:I{section_row}')
    cell = ws.cell(row=section_row, column=1)
    cell.value = "COST"
    cell.fill = subheader_fill
    cell.font = subheader_font
    cell.alignment = Alignment(horizontal='center', vertical='center')
    cell.border = border

    # Section labels - ACCUMULATED DEPRECIATION
    ws.merge_cells(f'J{section_row}:P{section_row}')
    cell = ws.cell(row=section_row, column=10)
    cell.value = "ACCUMULATED DEPRECIATION"
    cell.fill = subheader_fill
    cell.font = subheader_font
    cell.alignment = Alignment(horizontal='center', vertical='center')
    cell.border = border

    # Section labels - CARRYING AMOUNTS
    ws.merge_cells(f'Q{section_row}:R{section_row}')
    cell = ws.cell(row=section_row, column=17)
    cell.value = "CARRYING AMOUNTS"
    cell.fill = subheader_fill
    cell.font = subheader_font
    cell.alignment = Alignment(horizontal='center', vertical='center')
    cell.border = border

    # Write data
    row_num = section_row + 1
    total_row_num = None

    for idx, record in enumerate(data):
        is_total = record.get("is_total_row", False)

        # Category name
        cell = ws.cell(row=row_num, column=1)
        cell.value = record.get("asset_category", "")
        if is_total:
            cell.font = total_font
            cell.fill = total_fill
        cell.border = border
        cell.alignment = Alignment(horizontal='left', vertical='center')

        # Write data columns (18 columns total)
        fields = [
            "opening_cost", "additions", "reclassifications", "revaluations",
            "disposals", "write_off", "exchange_difference", "closing_cost",
            "opening_depreciation", "charge_for_year", "depreciation_revaluations",
            "depreciation_disposals", "depreciation_write_off", 
            "depreciation_exchange_diff", "closing_depreciation",
            "current_year_nbv", "prior_year_nbv"
        ]

        for col_idx, field in enumerate(fields, 2):
            value = record.get(field, 0)
            cell = ws.cell(row=row_num, column=col_idx)
            cell.value = flt(value)
            cell.number_format = '#,##0.00'
            cell.border = border
            cell.alignment = Alignment(horizontal='right', vertical='center')

            # Apply formatting
            if is_total:
                cell.font = total_font
                cell.fill = total_fill
            elif field in ["closing_cost", "closing_depreciation", "current_year_nbv"]:
                cell.font = Font(bold=True)
            elif field in ["revaluations", "depreciation_revaluations"] and value != 0:
                # Highlight revaluation amounts
                cell.fill = reval_fill
                if value > 0:
                    cell.font = Font(color="0066cc")
                else:
                    cell.font = Font(color="cc0000")

        if is_total:
            total_row_num = row_num

        row_num += 1

    # Add totals row styling
    if total_row_num:
        for col in range(1, 19):
            cell = ws.cell(row=total_row_num, column=col)
            cell.fill = PatternFill(start_color="d4e6f1", end_color="d4e6f1", fill_type="solid")
            cell.font = Font(bold=True, size=10)

    # Auto-size columns
    for col_idx in range(1, 19):
        max_length = 15
        column_letter = get_column_letter(col_idx)

        # Check data length
        for row in range(1, row_num):
            cell_value = ws.cell(row=row, column=col_idx).value
            if cell_value:
                max_length = max(max_length, len(str(cell_value)))

        ws.column_dimensions[column_letter].width = min(max_length + 5, 30)

    # Summary sheet
    summary_ws = wb.create_sheet("Summary")
    create_summary_sheet(summary_ws, data, filters)

    # Revaluation details sheet
    reval_ws = wb.create_sheet("Revaluation Details")
    create_revaluation_sheet(reval_ws, filters)

    # Save
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    excel_data = base64.b64encode(output.getvalue()).decode()
    return excel_data


def create_summary_sheet(ws, data, filters):
    """Create summary sheet with additional analysis"""

    # Title
    ws.merge_cells('A1:C1')
    title_cell = ws['A1']
    title_cell.value = "PROPERTY AND EQUIPMENT - SUMMARY ANALYSIS"
    title_cell.font = Font(bold=True, size=14, color="1a5276")
    title_cell.alignment = Alignment(horizontal='center')

    # Date
    ws.merge_cells('A2:C2')
    date_cell = ws['A2']
    fiscal_year = filters.get("fiscal_year", getdate().year)
    date_cell.value = f"As at December 31, {fiscal_year}"
    date_cell.font = Font(size=11, color="555555")
    date_cell.alignment = Alignment(horizontal='center')

    row = 4

    # Key statistics
    total_row = None
    for row_data in data:
        if row_data.get("is_total_row"):
            total_row = row_data
            break

    if total_row:
        stats = [
            ("Total Cost", total_row.get("closing_cost", 0)),
            ("Total Accumulated Depreciation", total_row.get("closing_depreciation", 0)),
            ("Total Net Book Value", total_row.get("current_year_nbv", 0)),
            ("Additions During Year", total_row.get("additions", 0)),
            ("Revaluations During Year", total_row.get("revaluations", 0)),
            ("Disposals During Year", total_row.get("disposals", 0)),
            ("Depreciation Charge for Year", total_row.get("charge_for_year", 0))
        ]

        for label, value in stats:
            ws.cell(row=row, column=1).value = label
            ws.cell(row=row, column=1).font = Font(bold=True)
            ws.cell(row=row, column=2).value = flt(value)
            ws.cell(row=row, column=2).number_format = '#,##0.00'
            row += 1

    row += 1

    # Category breakdown
    ws.cell(row=row, column=1).value = "ASSET CATEGORY BREAKDOWN"
    ws.cell(row=row, column=1).font = Font(bold=True, size=12, color="1a5276")
    row += 1

    # Headers
    headers = ["Category", "Cost", "Depreciation", "Revaluations", "Net Book Value", "Depreciation %"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col)
        cell.value = header
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="d4e6f1", end_color="d4e6f1", fill_type="solid")
    row += 1

    for row_data in data:
        if not row_data.get("is_total_row"):
            category = row_data.get("asset_category", "")
            cost = row_data.get("closing_cost", 0)
            depreciation = row_data.get("closing_depreciation", 0)
            revaluations = row_data.get("revaluations", 0)
            nbv = row_data.get("current_year_nbv", 0)
            dep_percent = (depreciation / cost * 100) if cost > 0 else 0

            ws.cell(row=row, column=1).value = category
            ws.cell(row=row, column=2).value = flt(cost)
            ws.cell(row=row, column=2).number_format = '#,##0.00'
            ws.cell(row=row, column=3).value = flt(depreciation)
            ws.cell(row=row, column=3).number_format = '#,##0.00'
            ws.cell(row=row, column=4).value = flt(revaluations)
            ws.cell(row=row, column=4).number_format = '#,##0.00'
            ws.cell(row=row, column=5).value = flt(nbv)
            ws.cell(row=row, column=5).number_format = '#,##0.00'
            ws.cell(row=row, column=6).value = flt(dep_percent) / 100
            ws.cell(row=row, column=6).number_format = '0.00%'
            row += 1

    # Adjust columns
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 20
    ws.column_dimensions['D'].width = 20
    ws.column_dimensions['E'].width = 20
    ws.column_dimensions['F'].width = 15


def create_revaluation_sheet(ws, filters):
    """Create detailed revaluation sheet"""

    # Get fiscal year
    fiscal_year = filters.get("fiscal_year", getdate().year)
    from_date_str, to_date_str = get_fiscal_year_dates(fiscal_year)
    from_date = safe_getdate(from_date_str)
    to_date = safe_getdate(to_date_str)
    company = filters.get("company")

    # Build company filter
    company_condition = ""
    if company:
        company_condition = "AND far.company = %s"

    # Get all revaluations for the period
    query = f"""
        SELECT 
            far.name as revaluation_id,
            far.revaluation_date,
            far.asset,
            fa.asset_code,
            fa.asset_name,
            fa.asset_category,
            far.current_gross_value,
            far.new_gross_value,
            far.revaluation_amount,
            far.percentage_change,
            far.revaluation_type,
            far.revaluation_method,
            far.revaluation_status,
            far.company
        FROM `tabFixed Asset Revaluation` far
        LEFT JOIN `tabFixed Asset` fa ON far.asset = fa.name
        WHERE 
            far.docstatus = 1
            AND far.revaluation_date BETWEEN %s AND %s
            {company_condition}
        ORDER BY 
            far.revaluation_date DESC,
            fa.asset_category
    """

    params = [from_date, to_date]
    if company:
        params.append(company)

    revaluations = frappe.db.sql(query, params, as_dict=1)

    if not revaluations:
        ws.cell(row=1, column=1).value = "No revaluations recorded for this period"
        return

    # Title
    ws.merge_cells('A1:L1')
    title_cell = ws['A1']
    title_cell.value = f"REVALUATION DETAILS - {fiscal_year}"
    title_cell.font = Font(bold=True, size=14, color="1a5276")
    title_cell.alignment = Alignment(horizontal='center')

    # Headers
    headers = [
        "Date", "Revaluation ID", "Asset Code", "Asset Name", "Category",
        "Old Gross Value", "New Gross Value", "Revaluation Amount",
        "Percentage Change", "Type", "Method", "Status"
    ]

    row = 3
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col)
        cell.value = header
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="1a5276", end_color="1a5276", fill_type="solid")
        cell.font = Font(bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal='center')

    # Write data
    row = 4
    total_revaluation = 0

    for reval in revaluations:
        ws.cell(row=row, column=1).value = reval.get("revaluation_date")
        ws.cell(row=row, column=2).value = reval.get("revaluation_id")
        ws.cell(row=row, column=3).value = reval.get("asset_code")
        ws.cell(row=row, column=4).value = reval.get("asset_name")
        ws.cell(row=row, column=5).value = reval.get("asset_category")
        ws.cell(row=row, column=6).value = flt(reval.get("current_gross_value", 0))
        ws.cell(row=row, column=6).number_format = '#,##0.00'
        ws.cell(row=row, column=7).value = flt(reval.get("new_gross_value", 0))
        ws.cell(row=row, column=7).number_format = '#,##0.00'

        reval_amount = flt(reval.get("revaluation_amount", 0))
        ws.cell(row=row, column=8).value = reval_amount
        ws.cell(row=row, column=8).number_format = '#,##0.00'
        if reval_amount > 0:
            ws.cell(row=row, column=8).font = Font(color="0066cc")
        elif reval_amount < 0:
            ws.cell(row=row, column=8).font = Font(color="cc0000")
        total_revaluation += reval_amount

        ws.cell(row=row, column=9).value = flt(reval.get("percentage_change", 0))
        ws.cell(row=row, column=9).number_format = '0.00%'
        ws.cell(row=row, column=10).value = reval.get("revaluation_type")
        ws.cell(row=row, column=11).value = reval.get("revaluation_method")
        ws.cell(row=row, column=12).value = reval.get("revaluation_status")

        row += 1

    # Total row
    ws.cell(row=row, column=7).value = "TOTAL REVALUATION:"
    ws.cell(row=row, column=7).font = Font(bold=True)
    ws.cell(row=row, column=8).value = total_revaluation
    ws.cell(row=row, column=8).number_format = '#,##0.00'
    ws.cell(row=row, column=8).font = Font(bold=True)

    # Auto-size columns
    for col_idx in range(1, 13):
        max_length = 15
        column_letter = get_column_letter(col_idx)
        for row_num in range(1, row + 1):
            cell_value = ws.cell(row=row_num, column=col_idx).value
            if cell_value:
                max_length = max(max_length, len(str(cell_value)))
        ws.column_dimensions[column_letter].width = min(max_length + 5, 30)


@frappe.whitelist()
def download_excel(filters=None):
    """Download the report as Excel"""
    if isinstance(filters, str):
        filters = json.loads(filters)

    if not filters:
        filters = {}

    excel_data = get_excel_data(filters)

    frappe.response["filename"] = f"Property_and_Equipment_{getdate()}.xlsx"
    frappe.response["filecontent"] = base64.b64decode(excel_data)
    frappe.response["type"] = "download"
    frappe.response["content_type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"