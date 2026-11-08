# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate
import json
from datetime import datetime, date
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter
from io import BytesIO
import base64


def safe_getdate(value):
    """
    Bulletproof conversion to datetime.date.

    Returns None instead of raising for anything unparseable
    (None, '', '0000-00-00', stray strings, bytes, etc.) so callers
    never end up comparing a str/None against a date object.
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
    """One row per asset - full movement detail"""
    return [
        {"label": _("Asset Code"), "fieldname": "asset_code", "fieldtype": "Link",
         "options": "Fixed Asset", "width": 130},
        {"label": _("Asset Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 180},
        {"label": _("Asset Category"), "fieldname": "asset_category", "fieldtype": "Link",
         "options": "Fixed Asset Category", "width": 150},
        {"label": _("Purchase Date"), "fieldname": "purchase_date", "fieldtype": "Date", "width": 110},
        {"label": _("Status"), "fieldname": "asset_status", "fieldtype": "Data", "width": 100},
        {"label": _("Opening Cost"), "fieldname": "opening_cost", "fieldtype": "Currency", "width": 130},
        {"label": _("Additions"), "fieldname": "additions", "fieldtype": "Currency", "width": 120},
        {"label": _("Revaluations"), "fieldname": "revaluations", "fieldtype": "Currency", "width": 120},
        {"label": _("Disposals"), "fieldname": "disposals", "fieldtype": "Currency", "width": 120},
        {"label": _("Write-off"), "fieldname": "write_off", "fieldtype": "Currency", "width": 110},
        {"label": _("Closing Cost"), "fieldname": "closing_cost", "fieldtype": "Currency",
         "width": 130, "bold": 1},
        {"label": _("Opening Depreciation"), "fieldname": "opening_depreciation",
         "fieldtype": "Currency", "width": 150},
        {"label": _("Charge for Year"), "fieldname": "charge_for_year", "fieldtype": "Currency", "width": 130},
        {"label": _("Depreciation Revaluations"), "fieldname": "depreciation_revaluations",
         "fieldtype": "Currency", "width": 150},
        {"label": _("Depreciation Disposals"), "fieldname": "depreciation_disposals",
         "fieldtype": "Currency", "width": 140},
        {"label": _("Depreciation Write-off"), "fieldname": "depreciation_write_off",
         "fieldtype": "Currency", "width": 140},
        {"label": _("Closing Depreciation"), "fieldname": "closing_depreciation",
         "fieldtype": "Currency", "width": 150, "bold": 1},
        {"label": _("Current Year NBV"), "fieldname": "current_year_nbv", "fieldtype": "Currency",
         "width": 140, "bold": 1},
        {"label": _("Prior Year NBV"), "fieldname": "prior_year_nbv", "fieldtype": "Currency", "width": 130},
    ]


def get_data(filters):
    """Build one row per Fixed Asset for the selected period"""

    fiscal_year = filters.get("fiscal_year")
    company = filters.get("company")
    asset_category_filter = filters.get("asset_category")
    asset_status_filter = filters.get("asset_status")

    from_date_str, to_date_str = get_fiscal_year_dates(fiscal_year)
    from_date = safe_getdate(from_date_str)
    to_date = safe_getdate(to_date_str)

    conditions = ["docstatus != 2"]
    params = []

    if company:
        conditions.append("company = %s")
        params.append(company)
    if asset_category_filter:
        conditions.append("asset_category = %s")
        params.append(asset_category_filter)
    if asset_status_filter:
        conditions.append("asset_status = %s")
        params.append(asset_status_filter)

    where_clause = " AND ".join(conditions)

    assets = frappe.db.sql(f"""
        SELECT
            name,
            asset_name,
            asset_category,
            purchase_date,
            current_gross_value,
            current_accumulated_depreciation,
            opening_accumulated_depreciation,
            asset_status,
            company
        FROM `tabFixed Asset`
        WHERE {where_clause}
        ORDER BY asset_category, asset_name
    """, params, as_dict=1)

    report_data = []
    totals = {
        "opening_cost": 0, "additions": 0, "revaluations": 0, "disposals": 0,
        "write_off": 0, "closing_cost": 0, "opening_depreciation": 0,
        "charge_for_year": 0, "depreciation_revaluations": 0,
        "depreciation_disposals": 0, "depreciation_write_off": 0,
        "closing_depreciation": 0, "current_year_nbv": 0, "prior_year_nbv": 0
    }

    for asset in assets:
        row = get_asset_row(asset, from_date, to_date)
        if row:
            report_data.append(row)
            for key in totals.keys():
                totals[key] += flt(row.get(key, 0))

    if report_data:
        report_data.append({
            "asset_code": "",
            "asset_name": "TOTAL",
            "is_total_row": 1,
            **totals
        })

    summary = get_summary(totals, len(report_data) - 1 if report_data else 0)

    return report_data, summary


def get_asset_row(asset, from_date, to_date):
    """Compute the full cost/depreciation movement for a single asset"""

    try:
        gross_value = flt(asset.current_gross_value)
        current_dep = flt(asset.current_accumulated_depreciation)
        opening_dep = flt(asset.opening_accumulated_depreciation or 0)

        purchase_date = safe_getdate(asset.purchase_date)

        opening_cost = additions = 0
        opening_depreciation = 0
        disposals = write_off = 0
        depreciation_disposals = depreciation_write_off = 0
        closing_cost = closing_depreciation = 0

        if not purchase_date:
            if asset.asset_status not in ["Disposed", "Scrapped"]:
                opening_cost = gross_value
                opening_depreciation = opening_dep
        elif purchase_date < from_date:
            opening_cost = gross_value
            opening_depreciation = opening_dep
        elif from_date <= purchase_date <= to_date:
            additions = gross_value
            opening_depreciation = 0

        reval_data = get_asset_revaluations(asset.name, from_date, to_date)
        revaluations = flt(reval_data.get("total_revaluation_amount", 0)) if reval_data else 0
        depreciation_revaluations = flt(reval_data.get("depreciation_impact", 0)) if reval_data else 0

        if asset.asset_status in ["Disposed", "Scrapped"]:
            disposal_info = frappe.db.sql("""
                SELECT disposal_date
                FROM `tabFixed Asset Disposal`
                WHERE asset = %s AND docstatus = 1
                AND disposal_date BETWEEN %s AND %s
            """, (asset.name, from_date, to_date), as_dict=1)

            if disposal_info:
                disposals = gross_value
                depreciation_disposals = current_dep

        if asset.asset_status == "Draft" and purchase_date and purchase_date >= from_date:
            write_off = gross_value
            depreciation_write_off = current_dep

        if asset.asset_status not in ["Disposed", "Scrapped", "Draft"]:
            closing_cost = gross_value
            closing_depreciation = current_dep

        charge_for_year = closing_depreciation - opening_depreciation + depreciation_disposals
        current_year_nbv = closing_cost - closing_depreciation
        prior_year_nbv = opening_cost - opening_depreciation

        category_name = frappe.db.get_value(
            "Fixed Asset Category", asset.asset_category, "category_name"
        ) or asset.asset_category

        return {
            "asset_code": asset.name,
            "asset_name": asset.asset_name,
            "asset_category": category_name,
            "purchase_date": purchase_date,
            "asset_status": asset.asset_status,
            "opening_cost": opening_cost,
            "additions": additions,
            "revaluations": revaluations,
            "disposals": disposals,
            "write_off": write_off,
            "closing_cost": closing_cost,
            "opening_depreciation": opening_depreciation,
            "charge_for_year": charge_for_year,
            "depreciation_revaluations": depreciation_revaluations,
            "depreciation_disposals": depreciation_disposals,
            "depreciation_write_off": depreciation_write_off,
            "closing_depreciation": closing_depreciation,
            "current_year_nbv": current_year_nbv,
            "prior_year_nbv": prior_year_nbv,
        }

    except Exception:
        frappe.log_error(
            title=_("Fixed Asset Register - skipped asset"),
            message=frappe.get_traceback() + f"\nAsset: {asset.get('name')}"
        )
        return None


def get_asset_revaluations(asset_name, from_date, to_date):
    """Get revaluation data for a specific asset during the period"""

    from_date = safe_getdate(from_date)
    to_date = safe_getdate(to_date)

    revaluations = frappe.db.sql("""
        SELECT
            revaluation_date, current_gross_value, new_gross_value,
            revaluation_amount, revaluation_type, current_accumulated_depreciation
        FROM `tabFixed Asset Revaluation`
        WHERE asset = %s AND docstatus = 1
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
        year = getdate().year
        return f"{year}-01-01", f"{year}-12-31"
    try:
        year = int(fiscal_year)
        return f"{year}-01-01", f"{year}-12-31"
    except (ValueError, TypeError):
        year = getdate().year
        return f"{year}-01-01", f"{year}-12-31"


def get_summary(totals, asset_count):
    return [
        {"label": _("Number of Assets"), "value": asset_count, "datatype": "Int"},
        {"label": _("Total Closing Cost"), "value": totals.get("closing_cost", 0), "datatype": "Currency"},
        {"label": _("Total Closing Depreciation"), "value": totals.get("closing_depreciation", 0),
         "datatype": "Currency"},
        {"label": _("Total Net Book Value"), "value": totals.get("current_year_nbv", 0), "datatype": "Currency"},
        {"label": _("Additions During Year"), "value": totals.get("additions", 0), "datatype": "Currency"},
        {"label": _("Revaluations During Year"), "value": totals.get("revaluations", 0), "datatype": "Currency"},
        {"label": _("Disposals During Year"), "value": totals.get("disposals", 0), "datatype": "Currency"},
    ]


def get_chart(data):
    """Top 15 assets by closing cost"""
    if not data or len(data) < 2:
        return None

    rows = [r for r in data if not r.get("is_total_row")]
    rows = sorted(rows, key=lambda r: flt(r.get("closing_cost", 0)), reverse=True)[:15]

    if not rows:
        return None

    return {
        "data": {
            "labels": [r.get("asset_name") for r in rows],
            "datasets": [
                {"name": _("Closing Cost"), "values": [r.get("closing_cost") for r in rows], "chartType": "bar"},
                {"name": _("Net Book Value"), "values": [r.get("current_year_nbv") for r in rows], "chartType": "bar"},
            ]
        },
        "type": "bar",
        "height": 300,
        "fieldname": "asset_name"
    }


@frappe.whitelist()
def get_excel_data(filters=None):
    """Generate Excel for the asset-level register"""
    if isinstance(filters, str):
        filters = json.loads(filters)
    if not filters:
        filters = {}

    data, summary = get_data(filters)

    wb = Workbook()
    ws = wb.active
    ws.title = "Fixed Asset Register"

    header_fill = PatternFill(start_color="1a5276", end_color="1a5276", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=10)
    total_fill = PatternFill(start_color="d4e6f1", end_color="d4e6f1", fill_type="solid")
    total_font = Font(bold=True, size=10)
    reval_fill = PatternFill(start_color="e8f4fd", end_color="e8f4fd", fill_type="solid")
    border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    fiscal_year = filters.get("fiscal_year", getdate().year)
    company_name = filters.get("company", "All Companies")

    ws.merge_cells('A1:S1')
    ws['A1'].value = "FIXED ASSET REGISTER"
    ws['A1'].font = Font(bold=True, size=16, color="1a5276")
    ws['A1'].alignment = Alignment(horizontal='center')

    ws.merge_cells('A2:S2')
    ws['A2'].value = f"{company_name} - Fiscal Year {fiscal_year}"
    ws['A2'].font = Font(size=11, color="555555")
    ws['A2'].alignment = Alignment(horizontal='center')

    headers = [
        "Asset Code", "Asset Name", "Asset Category", "Purchase Date", "Status",
        "Opening Cost", "Additions", "Revaluations", "Disposals", "Write-off",
        "Closing Cost", "Opening Depreciation", "Charge for Year",
        "Depreciation Revaluations", "Depreciation Disposals", "Depreciation Write-off",
        "Closing Depreciation", "Current Year NBV", "Prior Year NBV"
    ]
    header_row = 4
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = border

    currency_fields = [
        "opening_cost", "additions", "revaluations", "disposals", "write_off",
        "closing_cost", "opening_depreciation", "charge_for_year",
        "depreciation_revaluations", "depreciation_disposals", "depreciation_write_off",
        "closing_depreciation", "current_year_nbv", "prior_year_nbv"
    ]

    row_num = header_row + 1
    total_row_num = None

    for record in data:
        is_total = record.get("is_total_row", False)

        plain_fields = ["asset_code", "asset_name", "asset_category", "purchase_date", "asset_status"]
        for col_idx, field in enumerate(plain_fields, 1):
            cell = ws.cell(row=row_num, column=col_idx)
            cell.value = record.get(field, "")
            cell.border = border
            if is_total:
                cell.font = total_font
                cell.fill = total_fill

        for col_idx, field in enumerate(currency_fields, 6):
            value = record.get(field, 0)
            cell = ws.cell(row=row_num, column=col_idx)
            cell.value = flt(value)
            cell.number_format = '#,##0.00'
            cell.border = border
            cell.alignment = Alignment(horizontal='right')

            if is_total:
                cell.font = total_font
                cell.fill = total_fill
            elif field in ["closing_cost", "closing_depreciation", "current_year_nbv"]:
                cell.font = Font(bold=True)
            elif field in ["revaluations", "depreciation_revaluations"] and value != 0:
                cell.fill = reval_fill
                cell.font = Font(color="0066cc" if value > 0 else "cc0000")

        if is_total:
            total_row_num = row_num

        row_num += 1

    if total_row_num:
        for col in range(1, len(headers) + 1):
            cell = ws.cell(row=total_row_num, column=col)
            cell.fill = total_fill
            cell.font = total_font

    ws.freeze_panes = f"A{header_row + 1}"
    ws.auto_filter.ref = f"A{header_row}:{get_column_letter(len(headers))}{header_row}"

    for col_idx in range(1, len(headers) + 1):
        max_length = 14
        for row in range(header_row, row_num):
            cell_value = ws.cell(row=row, column=col_idx).value
            if cell_value:
                max_length = max(max_length, len(str(cell_value)))
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_length + 4, 28)

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return base64.b64encode(output.getvalue()).decode()


@frappe.whitelist()
def download_excel(filters=None):
    """Download the asset register as Excel"""
    if isinstance(filters, str):
        filters = json.loads(filters)
    if not filters:
        filters = {}

    excel_data = get_excel_data(filters)

    frappe.response["filename"] = f"Fixed_Asset_Register_{getdate()}.xlsx"
    frappe.response["filecontent"] = base64.b64decode(excel_data)
    frappe.response["type"] = "download"
    frappe.response["content_type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"