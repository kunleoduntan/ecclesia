# Copyright (c) Value Plus
# For license information, please see license.txt

"""
Styled Excel export for the Ecclesia financial reports (SFP - MQH, SCI - Report).

Place at:
    apps/ecclesia/ecclesia/ecclesia/utils/report_excel.py     (add an empty __init__.py if utils/ is new)

The report is executed through the normal report runner (so roles / permissions apply),
then written with openpyxl using the same colour scheme as the on-screen report:
  * navy title band (company, statement, period, currency, generated on)
  * frozen header + account column, hidden gridlines
  * accounting number formats, negatives in brackets, variance in red / plain
  * row styling driven by each row's `row_type` and `level`
  * landscape A4, fit to one page wide, header row repeated, page numbers
"""

import re
from io import BytesIO

import frappe
from frappe import _
from frappe.utils import flt, formatdate, getdate, now_datetime
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.properties import PageSetupProperties

NAVY = "003366"
STEEL = "1F4E79"
GRID = "D9D9D9"
FONT = "Calibri"

ACCOUNTING = '#,##0.00_);(#,##0.00);"-"_)'
PERCENT = '0.0"%"_);[Red](0.0"%");"-"_)'

THEMES = {
	"SFP - MQH": {
		"title": "Statement of Financial Position",
		"period": "as_at",
		"grand_fill": "63C8FF",
		"profit_fill": "FFF8DC",
		"profit_font": "000000",
	},
	"SCI - Report": {
		"title": "Statement of Comprehensive Income",
		"period": "for",
		"grand_fill": "4ED7F1",
		"profit_fill": "006400",
		"profit_font": "FFFFFF",
	},
}
DEFAULT_THEME = {
	"title": "Financial Report",
	"period": "for",
	"grand_fill": "63C8FF",
	"profit_fill": "FFF8DC",
	"profit_font": "000000",
}


# --------------------------------------------------------------------------
# Whitelisted entry point
# --------------------------------------------------------------------------
@frappe.whitelist()
def export_report_excel(report_name, filters=None):
	from frappe.desk.query_report import run

	filters = frappe.parse_json(filters) if filters else {}
	result = run(report_name, filters=filters, ignore_prepared_report=True)

	columns = [c for c in result.get("columns") or [] if isinstance(c, dict)]
	rows = normalise_rows(result.get("result") or [], columns)

	company = filters.get("company")
	company_name, currency = (company, None)
	if company:
		company_name, currency = frappe.get_cached_value(
			"Company", company, ["company_name", "default_currency"]
		)

	theme = THEMES.get(report_name, DEFAULT_THEME)
	content = build_workbook(
		company_name=company_name or "",
		title=theme["title"],
		period_text=get_period_text(filters, theme["period"]),
		currency=currency,
		columns=columns,
		rows=rows,
		notes=split_message(result.get("message")),
		theme=theme,
		sheet_name=report_name,
		prepared_by=frappe.utils.get_fullname(frappe.session.user),
	)

	safe = re.sub(r"[^A-Za-z0-9_-]+", "_", f"{report_name}_{company or ''}_{getdate().isoformat()}")
	frappe.response["filename"] = f"{safe.strip('_')}.xlsx"
	frappe.response["filecontent"] = content
	frappe.response["type"] = "binary"


def normalise_rows(result, columns):
	rows = []
	for r in result:
		if isinstance(r, dict):
			rows.append(r)
		elif isinstance(r, (list, tuple)):
			rows.append({c["fieldname"]: v for c, v in zip(columns, r)})
	return rows


def split_message(message):
	"""Everything after the first line of the report message (warnings / notes)."""
	if not message:
		return []
	text = message if isinstance(message, str) else " ".join(message)
	parts = [re.sub(r"<[^>]+>", "", p).strip() for p in re.split(r"<br\s*/?>", text)]
	return [p for p in parts[1:] if p]


def get_period_text(filters, mode):
	start = end = None

	if filters.get("filter_based_on") == "Date Range":
		start, end = filters.get("period_start_date"), filters.get("period_end_date")
	else:
		from_fy = filters.get("from_fiscal_year") or filters.get("year")
		to_fy = filters.get("to_fiscal_year") or from_fy
		if from_fy:
			start = frappe.db.get_value("Fiscal Year", from_fy, "year_start_date")
		if to_fy:
			end = frappe.db.get_value("Fiscal Year", to_fy, "year_end_date")

	if not end:
		return ""
	if mode == "as_at":
		return _("As at {0}").format(formatdate(end, "dd MMMM yyyy"))
	if start:
		return _("For the period {0} to {1}").format(
			formatdate(start, "dd MMMM yyyy"), formatdate(end, "dd MMMM yyyy")
		)
	return _("Up to {0}").format(formatdate(end, "dd MMMM yyyy"))


# --------------------------------------------------------------------------
# Workbook
# --------------------------------------------------------------------------
def fill(color):
	return PatternFill("solid", start_color=color, end_color=color)


def row_style(row_type, theme):
	"""fill, font colour, bold, italic, top border, bottom border"""
	thin_navy = Side(style="thin", color=STEEL)
	double_navy = Side(style="double", color=NAVY)
	styles = {
		"heading": dict(fill=NAVY, color="FFFFFF", bold=True),
		"section": dict(fill="E8ECF1", color="000000", bold=True),
		"total": dict(fill="CCE5FF", color="000000", bold=True, top=thin_navy),
		"summary": dict(fill=None, color="000000", bold=True),
		"grand_total": dict(
			fill=theme["grand_fill"], color="000000", bold=True, top=thin_navy, bottom=double_navy
		),
		"profit": dict(fill=theme["profit_fill"], color=theme["profit_font"], bold=True),
		"difference": dict(fill="C00000", color="FFFFFF", bold=True),
	}
	return styles.get(row_type, dict(fill=None, color="000000", bold=False))


def is_percent(fieldname):
	return fieldname.endswith("_var") or fieldname == "achievement_ytd_pct"


def is_group_start(fieldname):
	return bool(re.fullmatch(r"p\d+", fieldname)) or fieldname == "year_to_date"


def clean_text(value):
	return re.sub(r"<[^>]+>", "", str(value or "")).strip()


def build_workbook(
	company_name, title, period_text, currency, columns, rows, notes, theme, sheet_name, prepared_by
):
	wb = Workbook()
	ws = wb.active
	ws.title = re.sub(r"[\\/*?:\[\]]", "", sheet_name)[:31]
	ws.sheet_view.showGridLines = False

	ncols = len(columns)
	last_col = get_column_letter(ncols)
	HEADER_ROW, FIRST_DATA = 6, 7

	# ---- title band -------------------------------------------------------
	band = [
		(company_name.upper(), Font(name=FONT, size=16, bold=True, color="FFFFFF"), 26),
		(title, Font(name=FONT, size=13, bold=True, color="BFE3FF"), 20),
		(period_text, Font(name=FONT, size=11, color="FFFFFF"), 18),
		(
			" · ".join(
				x
				for x in (
					_("Amounts in {0}").format(currency) if currency else "",
					_("Generated {0}").format(now_datetime().strftime("%d %b %Y %H:%M")),
				)
				if x
			),
			Font(name=FONT, size=9, italic=True, color="BFE3FF"),
			16,
		),
	]
	for i, (text, font, height) in enumerate(band, start=1):
		ws.row_dimensions[i].height = height
		for c in range(1, ncols + 1):
			ws.cell(row=i, column=c).fill = fill(NAVY)
		cell = ws.cell(row=i, column=1, value=text)
		cell.font = font
		cell.alignment = Alignment(vertical="center", indent=1)
	ws.row_dimensions[5].height = 8

	# ---- header -----------------------------------------------------------
	ws.row_dimensions[HEADER_ROW].height = 32
	for c, col in enumerate(columns, start=1):
		cell = ws.cell(row=HEADER_ROW, column=c, value=clean_text(col.get("label")))
		cell.fill = fill(STEEL)
		cell.font = Font(name=FONT, size=10, bold=True, color="FFFFFF")
		cell.alignment = Alignment(
			horizontal="left" if c == 1 else "center", vertical="center", wrap_text=True, indent=1 if c == 1 else 0
		)
		left = Side(style="medium", color="FFFFFF") if is_group_start(col["fieldname"]) else None
		cell.border = Border(left=left)

	# ---- body -------------------------------------------------------------
	thin_grid = Side(style="hair", color=GRID)
	group_edge = Side(style="thin", color=STEEL)
	r = FIRST_DATA
	longest = 0

	for row in rows:
		row_type = row.get("row_type") or "line"
		if row_type == "spacer":
			ws.row_dimensions[r].height = 8
			r += 1
			continue

		style = row_style(row_type, theme)
		font = Font(name=FONT, size=10, bold=style.get("bold", False), color=style["color"])
		ws.row_dimensions[r].height = 18

		for c, col in enumerate(columns, start=1):
			fn = col["fieldname"]
			cell = ws.cell(row=r, column=c)

			if fn == "account_name":
				text = clean_text(row.get(fn))
				cell.value = text or None
				cell.alignment = Alignment(
					vertical="center", indent=1 + int(row.get("level") or 0)
				)
				longest = max(longest, len(text) + 2 * int(row.get("level") or 0))
			else:
				val = row.get(fn)
				if val not in (None, ""):
					cell.value = flt(val)
				cell.number_format = PERCENT if is_percent(fn) else ACCOUNTING
				cell.alignment = Alignment(horizontal="right", vertical="center")

			cell.font = font
			if style.get("fill"):
				cell.fill = fill(style["fill"])

			cell.border = Border(
				left=group_edge if (c > 1 and is_group_start(fn)) else None,
				top=style.get("top"),
				bottom=style.get("bottom") or (thin_grid if row_type == "line" else None),
			)
		r += 1

	last_data = r - 1

	# ---- notes ------------------------------------------------------------
	r += 1
	for note in notes:
		cell = ws.cell(row=r, column=1, value=note)
		cell.font = Font(name=FONT, size=9, italic=True, color="C00000")
		r += 1
	cell = ws.cell(row=r + 1, column=1, value=_("Prepared by {0}").format(prepared_by))
	cell.font = Font(name=FONT, size=9, italic=True, color="7F7F7F")

	# ---- widths, freeze, print -------------------------------------------
	for c, col in enumerate(columns, start=1):
		letter = get_column_letter(c)
		if c == 1:
			ws.column_dimensions[letter].width = max(34, min(longest + 6, 62))
		elif is_percent(col["fieldname"]):
			ws.column_dimensions[letter].width = 10
		else:
			ws.column_dimensions[letter].width = 18

	ws.freeze_panes = f"B{FIRST_DATA}"
	ws.auto_filter.ref = None

	ws.page_setup.orientation = "landscape"
	ws.page_setup.paperSize = ws.PAPERSIZE_A4
	ws.page_setup.fitToWidth = 1
	ws.page_setup.fitToHeight = 0
	ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
	ws.print_title_rows = f"{HEADER_ROW}:{HEADER_ROW}"
	ws.print_area = f"A1:{last_col}{max(r + 1, last_data, FIRST_DATA)}"
	ws.page_margins.left = ws.page_margins.right = 0.4
	ws.page_margins.top = ws.page_margins.bottom = 0.6
	ws.oddFooter.left.text = company_name
	ws.oddFooter.left.size = 8
	ws.oddFooter.right.text = "Page &P of &N"
	ws.oddFooter.right.size = 8

	buf = BytesIO()
	wb.save(buf)
	return buf.getvalue()