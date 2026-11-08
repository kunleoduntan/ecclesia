# Copyright (c) 2026, Value Plus and contributors
# For license information, please see license.txt

"""
Formatted Excel export for the Amortization Schedule Report.

Workbook layout
  Report       banner, KPI cards, styled table (frozen header, filter, SUBTOTAL totals)
  Exceptions   every overdue instalment / audit flag in one tidy list  (detail & summary views)
  Chart        native Excel chart + its data table
  Audit Notes  basis of preparation, flag legend, parameters, sign-off block
"""

import io
import math

import frappe
from frappe import _
from frappe.utils import flt, get_fullname, getdate, now_datetime
from openpyxl import Workbook
from openpyxl.chart import BarChart, DoughnutChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.properties import PageSetupProperties

try:
	from frappe.utils import get_url_to_form
except ImportError:  # pragma: no cover
	get_url_to_form = None

# --------------------------------------------------------------------------
# Palette - soft teal / mint / peach / rose
# --------------------------------------------------------------------------
FONT = "Arial"
DEEP = "1F4E5F"
TEAL = "2A7F8E"
MIST = "EEF6F6"
BAND = "F2F9F8"
TOTAL = "CDE7E3"
INK = "1F2933"
MUTED = "52606D"
LINE = "D5DEDC"

CARD = {  # indicator -> (fill, accent)
	"Blue": ("E3F0FB", "1E5A8E"),
	"Orange": ("FFF1E3", "A85B00"),
	"Green": ("E6F6EC", "1B6B3A"),
	"Red": ("FDE8E8", "B42318"),
}
CARD_EMOJI = ["🧾", "💼", "📆", "🏦", "⏰", "🔎"]

STATUS = {  # status -> (fill, font colour)
	"Posted": ("D8F3DC", "1B4332"),
	"Completed": ("D8F3DC", "1B4332"),
	"Overdue": ("FFD6D6", "9B1C1C"),
	"Scheduled": ("DCEBFF", "1E3A8A"),
	"In Progress": ("FFE8CC", "7C4A03"),
	"Not Started": ("E9ECEF", "495057"),
}

NUM = '#,##0.00;[Red]-#,##0.00;"-"'
INT = "#,##0"
PCT = "0.0%"
DATE = "dd-mmm-yyyy"

LEFT = Alignment(horizontal="left", vertical="center", indent=1)
LEFT_WRAP = Alignment(horizontal="left", vertical="center", wrap_text=True, indent=1)
CENTER = Alignment(horizontal="center", vertical="center")
RIGHT = Alignment(horizontal="right", vertical="center", indent=1)

FLAG_LEGEND = [
	("Schedule total ≠ Charged Amount", "The instalments on the schedule do not add up to the invoice's Charged Amount."),
	("Charged Amount not set", "The invoice has no Charged Amount; the schedule total is used as the base."),
	("Periods ≠ schedule lines", "No of Periods on the invoice differs from the number of schedule lines."),
	("No schedule generated", "Invoice is marked Amortized Cost but has no schedule lines."),
	("Balance mismatch", "Prepayment Balance stored on the line differs from Charged Amount less cumulative instalments."),
	("Date outside term", "Instalment date falls before the Start Date or after the End Date."),
	("Duplicate date", "Two or more instalments share the same date."),
	("Non-positive amount", "Instalment amount is zero or negative."),
	("Account missing / Debit = Credit account", "Expense or deferred account is blank, or both are the same account."),
	("Overdue instalments", "Instalment dated before today and not posted."),
	("Pointer says posted - no JE found", "Trace to Journal Entries only: the pointer shows posted but no matching submitted JE exists."),
	("JE found - pointer not advanced", "Trace to Journal Entries only: a JE exists but the invoice's Next Schedule pointer has not moved on."),
]


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def _font(size=10, bold=False, color=INK, italic=False, underline=None):
	return Font(name=FONT, size=size, bold=bold, color=color, italic=italic, underline=underline)


def _fill(hex_color):
	return PatternFill("solid", start_color=hex_color, end_color=hex_color)


def _d(value):
	return getdate(value).strftime("%d-%b-%Y") if value else ""


def _merge(ws, row, c1, c2, value=None, font=None, fill=None, align=None, border=None, height=None):
	for c in range(c1, c2 + 1):
		cell = ws.cell(row=row, column=c)
		if fill:
			cell.fill = fill
		if border:
			cell.border = border
	if c2 > c1:
		ws.merge_cells(start_row=row, start_column=c1, end_row=row, end_column=c2)
	anchor = ws.cell(row=row, column=c1)
	if value is not None:
		anchor.value = value
	if font:
		anchor.font = font
	if align:
		anchor.alignment = align
	if height:
		ws.row_dimensions[row].height = height


def _banner(ws, n, title, subtitle=None, note=None):
	_merge(ws, 1, 1, n, title, _font(16, True, "FFFFFF"), _fill(DEEP), LEFT, height=34)
	if subtitle:
		_merge(ws, 2, 1, n, subtitle, _font(12, True, "FFFFFF"), _fill(TEAL), LEFT, height=24)
	if note:
		_merge(ws, 3, 1, n, note, _font(9, False, MUTED, italic=True), _fill(MIST), LEFT, height=20)


def _page_setup(ws, company, title_row=None, landscape=True):
	ws.page_setup.orientation = "landscape" if landscape else "portrait"
	ws.page_setup.paperSize = ws.PAPERSIZE_A4
	ws.page_setup.fitToWidth = 1
	ws.page_setup.fitToHeight = 0
	ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
	ws.page_margins.left = ws.page_margins.right = 0.4
	ws.page_margins.top = 0.6
	ws.page_margins.bottom = 0.6
	ws.print_options.horizontalCentered = True
	if title_row:
		ws.print_title_rows = f"{title_row}:{title_row}"
	ws.oddHeader.center.text = f"{company} - Amortization Schedule Report"
	ws.oddHeader.center.size = 9
	ws.oddFooter.left.text = f"Prepared by {get_fullname(frappe.session.user)}"
	ws.oddFooter.center.text = "Page &P of &N"
	ws.oddFooter.right.text = "&D"
	for part in (ws.oddFooter.left, ws.oddFooter.center, ws.oddFooter.right):
		part.size = 8


def _link(cell, doctype, name):
	if get_url_to_form and name:
		try:
			cell.hyperlink = get_url_to_form(doctype, name)
			cell.font = _font(10, False, "1E5A8E", underline="single")
		except Exception:
			pass


def _subtitle(filters, currency):
	period = (
		f"Period: {_d(filters.from_date) or 'start'} to {_d(filters.to_date) or 'end'}"
		if (filters.from_date or filters.to_date)
		else "Period: all schedule dates"
	)
	bits = [period, f"Run on {now_datetime().strftime('%d-%b-%Y %H:%M')}", f"Currency: {currency}"]
	for key, label in (
		("supplier", "Supplier"),
		("purchase_invoice", "Invoice"),
		("expense_account", "Expense A/c"),
		("cost_center", "Cost Center"),
		("frequency", "Frequency"),
		("status", "Status"),
	):
		if filters.get(key):
			bits.append(f"{label}: {filters.get(key)}")
	if filters.exceptions_only:
		bits.append("Exceptions only")
	return "   |   ".join(bits)


# --------------------------------------------------------------------------
# Sheet 1 - Report
# --------------------------------------------------------------------------
def _write_report(ws, filters, view, cols, data, cards, currency):
	n = len(cols)
	ws.sheet_view.showGridLines = False
	ws.sheet_view.zoomScale = 90
	ws.sheet_properties.tabColor = TEAL

	_banner(ws, n, filters.company, f"📊  Amortization Schedule Report  —  {view}", _subtitle(filters, currency))
	ws.row_dimensions[4].height = 8

	# ---- KPI cards (rows 5-6)
	span = max(1, n // max(len(cards), 1))
	for i, card in enumerate(cards):
		c1 = 1 + i * span
		c2 = c1 + span - 1
		fill_hex, accent = CARD.get(card.get("indicator"), CARD["Blue"])
		edge = Side(style="thin", color=LINE)
		label = f"{CARD_EMOJI[i] if i < len(CARD_EMOJI) else '•'} {card['label']}"
		box_top = Border(top=edge, right=edge, left=Side(style="thick", color=accent))
		box_bot = Border(bottom=edge, right=edge, left=Side(style="thick", color=accent))
		_merge(ws, 5, c1, c2, label, _font(9, True, MUTED), _fill(fill_hex), LEFT, box_top, 20)
		_merge(ws, 6, c1, c2, card["value"], _font(14, True, accent), _fill(fill_hex), LEFT, box_bot, 30)
		value_cell = ws.cell(row=6, column=c1)
		value_cell.number_format = NUM if card.get("datatype") == "Currency" else INT
	ws.row_dimensions[7].height = 8

	# ---- table header (row 8)
	hdr = 8
	for ci, col in enumerate(cols, 1):
		cell = ws.cell(row=hdr, column=ci, value=col["label"])
		cell.font = _font(10, True, "FFFFFF")
		cell.fill = _fill(DEEP)
		cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
		cell.border = Border(bottom=Side(style="medium", color=TEAL))
		ws.column_dimensions[get_column_letter(ci)].width = max(11, min(46, round(col.get("width", 110) / 6.4)))
	ws.row_dimensions[hdr].height = 34

	body = [r for r in data if not r.get("is_total_row")]
	total = next((r for r in data if r.get("is_total_row")), None)
	band_field = {"Detailed Schedule": "purchase_invoice", "Monthly Summary": "month"}.get(view)

	prev, flip = object(), False
	row_idx = hdr
	for r in body:
		row_idx += 1
		key = r.get(band_field) if band_field else None
		if band_field is None or key != prev:
			flip, prev = not flip, key
		band = _fill(BAND) if flip else None

		for ci, col in enumerate(cols, 1):
			fn, ft = col["fieldname"], col["fieldtype"]
			v = r.get(fn)
			cell = ws.cell(row=row_idx, column=ci)
			cell.font = _font(10)
			cell.border = Border(bottom=Side(style="hair", color=LINE))
			if band:
				cell.fill = band

			if ft == "Date":
				cell.value = getdate(v) if v else None
				cell.number_format, cell.alignment = DATE, CENTER
			elif ft == "Currency":
				cell.value = flt(v) if v not in (None, "") else None
				cell.number_format, cell.alignment = NUM, RIGHT
			elif ft == "Int":
				cell.value = int(v) if v not in (None, "") else None
				cell.number_format, cell.alignment = INT, CENTER
			elif ft == "Percent":
				cell.value = flt(v) / 100 if v not in (None, "") else None
				cell.number_format, cell.alignment = PCT, CENTER
			else:
				cell.value = v if v not in (None, "") else None
				cell.alignment = LEFT_WRAP if fn in ("description", "flags") else LEFT

			if fn == "purchase_invoice":
				_link(cell, "Purchase Invoice", v)
			elif fn == "journal_entry":
				_link(cell, "Journal Entry", v)
			elif fn == "status" and v in STATUS:
				bg, fg = STATUS[v]
				cell.fill, cell.font, cell.alignment = _fill(bg), _font(9, True, fg), CENTER
			elif fn == "flags" and v:
				cell.font = _font(9, True, "B42318")
			elif fn in ("variance", "charge_overdue") and v and abs(flt(v)) > 0.005:
				cell.font, cell.fill = _font(10, True, "B42318"), _fill("FDE8E8")

	first, last = hdr + 1, row_idx

	# ---- total row (SUBTOTAL so it follows the filter)
	if total and body:
		tr = last + 1
		letter = {c["fieldname"]: get_column_letter(i) for i, c in enumerate(cols, 1)}
		for ci, col in enumerate(cols, 1):
			fn, ft = col["fieldname"], col["fieldtype"]
			cell = ws.cell(row=tr, column=ci)
			cell.fill = _fill(TOTAL)
			cell.font = _font(10, True, DEEP)
			cell.border = Border(top=Side(style="thin", color=DEEP), bottom=Side(style="medium", color=DEEP))
			if ci == 1:
				cell.value = total.get(fn) or _("Total")
				cell.alignment = LEFT
			elif ft in ("Currency", "Int") and fn in total:
				cell.value = f"=SUBTOTAL(109,{letter[fn]}{first}:{letter[fn]}{last})"
				cell.number_format = NUM if ft == "Currency" else INT
				cell.alignment = RIGHT if ft == "Currency" else CENTER
			elif ft == "Percent" and "base" in letter and "closing" in letter:
				b, c = f"{letter['base']}{tr}", f"{letter['closing']}{tr}"
				cell.value = f"=IFERROR(({b}-{c})/{b},0)"
				cell.number_format, cell.alignment = PCT, CENTER
		ws.row_dimensions[tr].height = 22
		ws.auto_filter.ref = f"A{hdr}:{get_column_letter(n)}{last}"
		note_row = tr + 2
	else:
		note_row = last + 2

	ws.freeze_panes = f"B{hdr + 1}"
	_merge(
		ws,
		note_row,
		1,
		min(n, 10),
		"Totals use SUBTOTAL and follow the active filter. KPI cards are a snapshot at run time. "
		"See the 'Audit Notes' sheet for basis of preparation.",
		_font(8, False, MUTED, italic=True),
		None,
		LEFT,
	)
	_page_setup(ws, filters.company, title_row=hdr)


# --------------------------------------------------------------------------
# Sheet 2 - Exceptions
# --------------------------------------------------------------------------
EXC_SPEC = {
	"Detailed Schedule": [
		("Purchase Invoice", "purchase_invoice", 24, "link"),
		("Supplier", "supplier_name", 30, "text"),
		("#", "idx", 6, "int"),
		("Schedule Date", "schedule_date", 15, "date"),
		("Amount", "amount", 18, "num"),
		("Status", "status", 13, "status"),
		("Audit Flags", "flags", 70, "flags"),
	],
	"Invoice Summary": [
		("Purchase Invoice", "purchase_invoice", 24, "link"),
		("Supplier", "supplier_name", 30, "text"),
		("Closing Balance", "closing", 18, "num"),
		("Overdue (Period)", "charge_overdue", 18, "num"),
		("Status", "status", 13, "status"),
		("Audit Flags", "flags", 80, "flags"),
	],
}


def _write_exceptions(wb, filters, view, data):
	spec = EXC_SPEC.get(view)
	if not spec:
		return
	ws = wb.create_sheet("Exceptions")
	ws.sheet_view.showGridLines = False
	ws.sheet_view.zoomScale = 90
	ws.sheet_properties.tabColor = "E24C4C"
	n = len(spec)

	rows = [
		r
		for r in data
		if not r.get("is_total_row") and r.get("purchase_invoice") and (r.get("flags") or r.get("status") == "Overdue")
	]
	_banner(
		ws,
		n,
		filters.company,
		"🔎  Exceptions & Audit Flags",
		f"{len(rows)} line(s) need attention" if rows else "Nothing to report",
	)
	ws.row_dimensions[4].height = 8

	hdr = 5
	for ci, (label, _fn, width, _kind) in enumerate(spec, 1):
		cell = ws.cell(row=hdr, column=ci, value=label)
		cell.font, cell.fill = _font(10, True, "FFFFFF"), _fill(DEEP)
		cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
		cell.border = Border(bottom=Side(style="medium", color="E24C4C"))
		ws.column_dimensions[get_column_letter(ci)].width = width
	ws.row_dimensions[hdr].height = 28

	if not rows:
		_merge(ws, hdr + 1, 1, n, "🎉  No exceptions found for the selected filters.", _font(11, True, "1B6B3A"), _fill("E6F6EC"), LEFT, height=32)
		_page_setup(ws, filters.company, landscape=True)
		return

	r_idx = hdr
	for r in rows:
		r_idx += 1
		for ci, (_label, fn, _w, kind) in enumerate(spec, 1):
			v = r.get(fn)
			cell = ws.cell(row=r_idx, column=ci)
			cell.font = _font(10)
			cell.border = Border(bottom=Side(style="hair", color=LINE))
			if kind == "date":
				cell.value, cell.number_format, cell.alignment = (getdate(v) if v else None), DATE, CENTER
			elif kind == "num":
				cell.value, cell.number_format, cell.alignment = (flt(v) if v not in (None, "") else None), NUM, RIGHT
			elif kind == "int":
				cell.value, cell.number_format, cell.alignment = v, INT, CENTER
			else:
				cell.value, cell.alignment = v, (LEFT_WRAP if kind == "flags" else LEFT)
			if kind == "link":
				_link(cell, "Purchase Invoice", v)
			elif kind == "status" and v in STATUS:
				bg, fg = STATUS[v]
				cell.fill, cell.font, cell.alignment = _fill(bg), _font(9, True, fg), CENTER
			elif kind == "flags":
				cell.font = _font(9, True, "B42318")
	ws.freeze_panes = f"A{hdr + 1}"
	ws.auto_filter.ref = f"A{hdr}:{get_column_letter(n)}{r_idx}"
	_page_setup(ws, filters.company, title_row=hdr)


# --------------------------------------------------------------------------
# Sheet 3 - Chart
# --------------------------------------------------------------------------
def _write_chart(wb, filters, chart):
	if not chart:
		return
	labels = chart["data"]["labels"]
	datasets = chart["data"]["datasets"]
	if not labels or not datasets:
		return

	is_bar = chart.get("type") == "bar"
	ws = wb.create_sheet("Chart")
	ws.sheet_view.showGridLines = False
	ws.sheet_properties.tabColor = "7CD6FD"
	title = "Amortization charge by month" if is_bar else "Closing balance by deferred account"
	_banner(ws, 4 + len(datasets), filters.company, f"📈  {title}")

	hdr = 3
	head = ["Month" if is_bar else "Account"] + [d["name"] for d in datasets]
	for ci, text in enumerate(head, 1):
		cell = ws.cell(row=hdr, column=ci, value=text)
		cell.font, cell.fill = _font(10, True, "FFFFFF"), _fill(DEEP)
		cell.alignment = CENTER
		ws.column_dimensions[get_column_letter(ci)].width = 30 if ci == 1 else 16
	for i, label in enumerate(labels):
		r = hdr + 1 + i
		ws.cell(row=r, column=1, value=label).font = _font(10)
		ws.cell(row=r, column=1).alignment = LEFT
		for j, d in enumerate(datasets):
			c = ws.cell(row=r, column=2 + j, value=flt(d["values"][i]))
			c.number_format, c.font, c.alignment = NUM, _font(10), RIGHT
		if i % 2 == 0:
			for cc in range(1, len(head) + 1):
				ws.cell(row=r, column=cc).fill = _fill(BAND)

	last = hdr + len(labels)
	cats = Reference(ws, min_col=1, min_row=hdr + 1, max_row=last)
	data_ref = Reference(ws, min_col=2, max_col=1 + len(datasets), min_row=hdr, max_row=last)

	if is_bar:
		ch = BarChart()
		ch.type, ch.grouping, ch.overlap = "col", "stacked", 100
		ch.add_data(data_ref, titles_from_data=True)
		ch.set_categories(cats)
		for series, color in zip(ch.series, ("29CD42", "E24C4C", "7CD6FD")):
			series.graphicalProperties.solidFill = color
			series.graphicalProperties.line.solidFill = color
		ch.y_axis.numFmt = "#,##0"
		ch.y_axis.title = None
		ch.x_axis.delete = False
		ch.y_axis.delete = False
		ch.legend.position = "b"
	else:
		ch = DoughnutChart()
		ch.holeSize = 55
		ch.add_data(data_ref, titles_from_data=True)
		ch.set_categories(cats)
		ch.dataLabels = DataLabelList()
		ch.dataLabels.showPercent = True
		ch.legend.position = "r"
	ch.title = title
	ch.height, ch.width = 10.5, 26
	ws.add_chart(ch, f"{get_column_letter(len(head) + 2)}3")
	_page_setup(ws, filters.company)


# --------------------------------------------------------------------------
# Sheet 4 - Audit Notes
# --------------------------------------------------------------------------
def _write_notes(wb, filters, view, currency):
	ws = wb.create_sheet("Audit Notes")
	ws.sheet_view.showGridLines = False
	ws.sheet_properties.tabColor = "B8A9E8"
	for letter, width in zip("ABCD", (34, 52, 28, 18)):
		ws.column_dimensions[letter].width = width
	_banner(ws, 4, filters.company, "📝  Audit Notes & Sign-off", "Amortization Schedule Report - basis of preparation")

	def section(row, text):
		_merge(ws, row, 1, 4, text, _font(11, True, DEEP), _fill(TOTAL), LEFT, height=22)
		return row + 1

	def pair(row, left, right, left_bold=True):
		lines = max(1, math.ceil(len(str(right)) / 95), math.ceil(len(str(left)) / 34))
		a = ws.cell(row=row, column=1, value=left)
		a.font, a.alignment = _font(10, left_bold), LEFT_WRAP
		_merge(ws, row, 2, 4, right, _font(10), None, LEFT_WRAP, height=max(18, 14 * lines + 4))
		for c in range(1, 5):
			ws.cell(row=row, column=c).border = Border(bottom=Side(style="hair", color=LINE))
		return row + 1

	row = 5
	row = section(row, "Basis of preparation")
	trace = bool(filters.trace_je)
	for topic, text in (
		("Schedule basis", "Balances are what the amortization schedule says should be recognised; they are not read from the General Ledger."),
		(
			"Posted status",
			"Traced to submitted Journal Entries that reference the invoice (debit on the expense account for the instalment amount)."
			if trace
			else "Taken from the invoice's Next Schedule pointer: instalments before it are treated as posted.",
		),
		("Overdue", "An instalment that is not posted and is dated before the run date."),
		("Roll-forward", "Opening + Additions - Charge for Period = Closing Balance. Additions are recognised at the invoice posting date; back-dated lines of an invoice posted inside the period are included in that period's charge."),
		("Totals", "Table totals are SUBTOTAL formulas and follow the filter applied in Excel. KPI cards are a snapshot taken at run time."),
		("Currency", f"All amounts in {currency}."),
	):
		row = pair(row, topic, text)

	row += 1
	row = section(row, "Audit flag legend")
	for flag, meaning in FLAG_LEGEND:
		row = pair(row, flag, meaning, left_bold=False)

	row += 1
	row = section(row, "Report parameters")
	params = [("View", view)]
	for key, label in (
		("from_date", "From Date"),
		("to_date", "To Date"),
		("supplier", "Supplier"),
		("purchase_invoice", "Purchase Invoice"),
		("expense_account", "Expense Account"),
		("cost_center", "Cost Center"),
		("frequency", "Frequency"),
		("status", "Instalment Status"),
	):
		if filters.get(key):
			params.append((label, _d(filters.get(key)) if key.endswith("_date") else filters.get(key)))
	for key, label in (("exceptions_only", "Exceptions Only"), ("trace_je", "Trace to Journal Entries"), ("include_draft", "Include Draft Invoices")):
		params.append((label, "Yes" if filters.get(key) else "No"))
	for label, value in params:
		row = pair(row, label, value, left_bold=False)

	row += 1
	row = section(row, "Sign-off")
	for ci, text in enumerate(("Role", "Name", "Signature", "Date"), 1):
		cell = ws.cell(row=row, column=ci, value=text)
		cell.font, cell.fill, cell.alignment = _font(10, True, "FFFFFF"), _fill(DEEP), CENTER
	row += 1
	box = Border(*(Side(style="thin", color="B8C7C4"),) * 4)
	for role, name, when in (
		("Prepared by", get_fullname(frappe.session.user), now_datetime().strftime("%d-%b-%Y")),
		("Reviewed by", "", ""),
		("Approved by", "", ""),
	):
		for ci, val in enumerate((role, name, "", when), 1):
			cell = ws.cell(row=row, column=ci, value=val or None)
			cell.font, cell.border = _font(10, ci == 1), box
			cell.alignment = LEFT if ci < 3 else CENTER
		ws.row_dimensions[row].height = 30
		row += 1

	_page_setup(ws, filters.company, landscape=False)


# --------------------------------------------------------------------------
# Entry
# --------------------------------------------------------------------------
def build_workbook(filters, view, columns, data, chart, cards, currency):
	wb = Workbook()
	ws = wb.active
	ws.title = "Report"

	cols = [c for c in columns if not c.get("hidden")]
	_write_report(ws, filters, view, cols, data, cards, currency)
	_write_exceptions(wb, filters, view, data)
	_write_chart(wb, filters, chart)
	_write_notes(wb, filters, view, currency)

	out = io.BytesIO()
	wb.save(out)
	return out.getvalue()
