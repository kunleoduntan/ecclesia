# Copyright (c) Value Plus
# For license information, please see license.txt

"""
SCI - Report: Statement of Comprehensive Income

Place at:
    apps/ecclesia/ecclesia/ecclesia/report/sci___report/sci___report.py
    apps/ecclesia/ecclesia/ecclesia/report/sci___report/sci___report.js

Nothing about the statement is hardcoded. Every row comes from the
Financial Reporting Group doctype and every column from the filters:

  ROWS      active groups with report_type Income Statement or Both, in sort_order
            * normal group   -> "▶ Group", its accounts, "Total - Group", blank row
            * formula group  -> calculated from its Components table (Add / Subtract any
                                other group, formula groups included); "Highlight" sets the
                                style: Subtotal / Key Result / Final Result

  COLUMNS   driven by the filters
            Fiscal Year range or Date Range  x  Monthly / Quarterly / Half-Yearly / Yearly
            Compare With    Previous Year (Jan | Jan LY) / Previous Period (Jan | Jan PP) / None
            Show Growth %   adds "<period> Growth %" after each comparison
            Show Total      adds the Year to date | Last Year | Growth % block at the end
            Cost Center / Project   restrict the GL postings

  DETAIL    Hide Details OFF  notes first (groups + accounts), then the statement lines
            Hide Details ON   statement lines only (or collapsed groups if none are defined)
            Hide Zero Balance Accounts   drops accounts with no figures in any column

Everything tunable (labels, comparisons, widths, prefixes, dimensions) is in the
CONFIGURATION block below. Period Closing Voucher entries are excluded.
"""

import re
from bisect import bisect_right

import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, escape_html, flt, get_last_day, getdate, today

# --------------------------------------------------------------------------
# CONFIGURATION
# --------------------------------------------------------------------------
REPORT_TITLE = "Statement of Comprehensive Income"
REPORT_TYPES = ["Income Statement", "Both"]  # Financial Reporting Group.report_type values used
ROOT_TYPES = ["Income", "Expense"]  # Account.root_type values on the statement
CREDIT_ROOT_TYPES = ("Income",)  # shown as credit - debit; all others debit - credit
EXCLUDED_VOUCHER_TYPE = "Period Closing Voucher"

FREQ_STEP = {"Monthly": 1, "Quarterly": 3, "Half-Yearly": 6, "Yearly": 12}  # months per period
DEFAULT_FREQUENCY = "Monthly"
MAX_PERIODS = 36

# Compare With options. "months": fixed shift back; None = shift back by the period length.
COMPARISONS = {
	"Previous Year": {"suffix": "LY", "total_label": "Last Year", "months": 12},
	"Previous Period": {"suffix": "PP", "total_label": "Previous Period", "months": None},
}
DEFAULT_COMPARISON = "Previous Year"

# GL Entry fields that can be used as report filters (filter fieldname == GL Entry field)
DIMENSION_FILTERS = ("cost_center", "project")

PRECISION = 2  # amounts
GROWTH_PRECISION = 1  # growth %
SPACER_WIDTH = 14  # blank column after each period; 0 removes it
ACCOUNT_WIDTH, AMOUNT_WIDTH, GROWTH_WIDTH = 340, 150, 105

SECTION_PREFIX = "▶ "  # in front of a group name
TOTAL_PREFIX = "Total - "  # in front of a group total
INDENT = ""  # the .js indents by `level`; put spaces here only if you also want them in exports
FULL_ACCOUNT_NAME = True  # "7002 - Commission Income - MIB"; False -> "Commission Income"

# Direct cost of the business. Every business names it differently, so the summary line is
# called "Cost of sales" and is matched to the first Financial Reporting Group found with any
# of these names (case and "&"/"and" ignored). Add your own spellings here.
COST_OF_SALES_NAMES = (
	"Cost of Sales", "Cost of Sale", "Cost of Goods Sold", "COGS", "Cost of Revenue",
	"Cost of Services", "Direct Costs", "Direct Cost", "Direct Expenses", "Direct Expense",
	"Direct Commission expenses", "Direct Commission",
)
COST_OF_SALES_LABEL = "Cost of sales"  # label used when no group matches
SHOW_GROUP_NAME_FOR_COST_OF_SALES = True  # True: show the matched group's own name (e.g. "Direct Commission expenses")

# Revenue is matched the same way (first group found with any of these names).
REVENUE_NAMES = (
	"Revenue", "Revenues", "Turnover", "Sales", "Net Sales", "Revenue from Operations",
	"Brokerage income",
)


def build_summary_spec():
	"""The summary (Revenue ... Profit After Tax). Each line adds / subtracts earlier lines or
	Financial Reporting Groups; the first name that matches (ignoring case and "&"/"and") is used.

	  Gross Profit     = Revenue - Cost of sales
	  EBITDA           = Gross Profit - Administrative - Selling & Distribution - Employees Benefits
	  EBIT             = EBITDA - Depreciation & Amortisation
	  Operating Profit = EBIT - Finance Charge
	  Profit Before Tax = Operating Profit + Other Income
	  Profit After Tax = Profit Before Tax - Income Tax

	highlight: None = plain line (left out when no group matches); Key Result = bold blue
	subtotal; Final Result = bold blue with a double underline.
	warn: list the available groups in the message line when nothing matches."""
	rev, cos = "Revenue", COST_OF_SALES_LABEL
	return [
		{"label": rev, "parts": [(REVENUE_NAMES, 1)]},
		{"label": cos, "warn": True, "use_group_label": SHOW_GROUP_NAME_FOR_COST_OF_SALES,
			"parts": [(COST_OF_SALES_NAMES, 1)]},
		{"label": "Gross Profit", "highlight": "Key Result",
			"parts": [((rev,), 1), ((cos,), -1)]},
		{"label": "Administrative Expenses", "parts": [(("Administrative Expenses",), 1)]},
		{"label": "Selling & Distribution Expenses",
			"parts": [(("Selling & Distribution Expenses", "Selling, distribution & marketing expenses"), 1)]},
		{"label": "Employees Benefits", "parts": [(("Employees Benefits", "Employees Benefit Expenses"), 1)]},
		{"label": "EBITDA", "highlight": "Key Result",
			"parts": [(("Gross Profit",), 1), (("Administrative Expenses",), -1),
				(("Selling & Distribution Expenses",), -1), (("Employees Benefits",), -1)]},
		{"label": "Depreciation & Amortisation Expenses",
			"parts": [(("Depreciation & Amortisation Expenses",), 1)]},
		{"label": "EBIT", "highlight": "Key Result",
			"parts": [(("EBITDA",), 1), (("Depreciation & Amortisation Expenses",), -1)]},
		{"label": "Finance Charge", "parts": [(("Finance Charge", "Finance charges"), 1)]},
		{"label": "Operating Profit", "highlight": "Key Result",
			"parts": [(("EBIT",), 1), (("Finance Charge",), -1)]},
		{"label": "Other Income", "parts": [(("Other Income",), 1)]},
		{"label": "Profit Before Tax", "highlight": "Key Result",
			"parts": [(("Operating Profit",), 1), (("Other Income",), 1)]},
		{"label": "Income Tax Expense", "warn": True,
			"parts": [(("Income Tax Expense", "Income Tax", "Taxation", "Company Income Tax", "Tax"), 1)]},
		{"label": "Profit After Tax", "highlight": "Final Result",
			"parts": [(("Profit Before Tax",), 1), (("Income Tax Expense",), -1)]},
	]


SUMMARY_SPEC = build_summary_spec()
# "auto": use the formula groups defined in the doctype when they cover every highlighted
#         line above, otherwise use SUMMARY_SPEC; "spec": always SUMMARY_SPEC; "doctype": only the doctype
SUMMARY_SOURCE = "spec"

HIGHLIGHT_ROW_TYPE = {"Subtotal": "total", "Key Result": "grand_total", "Final Result": "profit"}
# --------------------------------------------------------------------------


def norm(text):
	return " ".join(
		(text or "").lower().replace("&", " and ").replace("/", " ").replace("-", " ").split()
	)


def natural_key(text):
	return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", text or "")]


def flag(filters, name, default=1):
	value = filters.get(name)
	return cint(default if value is None else value)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	start, end, fy_mode = get_date_range(filters)

	step = FREQ_STEP.get(filters.get("frequency") or DEFAULT_FREQUENCY, 1)
	periods = get_periods(start, end, step, fy_mode)
	cmp = get_comparison(filters, step, len(periods))
	attach_comparison(periods, cmp)

	opts = frappe._dict(
		cmp=cmp,
		growth=bool(cmp and flag(filters, "show_growth")),
		total=bool(flag(filters, "show_total")),
	)

	columns = get_columns(periods, fy_mode, opts)
	data, warnings, notes = get_data(filters, start, end, periods, cmp)

	return columns, data, get_message(filters, start, end, cmp, warnings, notes), None, None


# --------------------------------------------------------------------------
# Dates, periods, comparison
# --------------------------------------------------------------------------
def shift_start(d, months):
	return getdate(add_months(d, -months))


def shift_end(d, months):
	d = getdate(d)
	if d == getdate(get_last_day(d)):
		return getdate(get_last_day(add_months(d, -months)))
	return getdate(add_months(d, -months))


def get_date_range(filters):
	if not filters.get("company"):
		frappe.throw(_("Please select a Company"))

	if (filters.get("filter_based_on") or "Fiscal Year") == "Date Range":
		if not (filters.get("period_start_date") and filters.get("period_end_date")):
			frappe.throw(_("Please select Start Date and End Date"))
		start, end, fy_mode = getdate(filters.period_start_date), getdate(filters.period_end_date), False
	else:
		from_fy = filters.get("from_fiscal_year") or filters.get("year")
		to_fy = filters.get("to_fiscal_year") or from_fy
		if not from_fy:
			frappe.throw(_("Please select a Fiscal Year"))
		f = frappe.db.get_value("Fiscal Year", from_fy, ["year_start_date"], as_dict=True)
		t = frappe.db.get_value("Fiscal Year", to_fy, ["year_end_date"], as_dict=True)
		if not f or not t:
			frappe.throw(_("Fiscal Year not found"))
		start, end, fy_mode = getdate(f.year_start_date), getdate(t.year_end_date), True

	if start > end:
		frappe.throw(_("The start of the range must be before its end"))
	return start, end, fy_mode


def period_label(s, e, step, idx, fy_mode, multi_year):
	"""Short labels like the Excel: Jan, Q1, H1 (year added only when the range spans years)."""
	if step == 1:
		return s.strftime("%b %Y") if multi_year else s.strftime("%b")
	if fy_mode:
		n = idx % (12 // step) + 1
		year = f" {e.year}" if multi_year else ""
		if step == 3:
			return f"Q{n}{year}"
		if step == 6:
			return f"H{n}{year}"
		return f"FY {e.year}"
	if multi_year:
		return f"{s.strftime('%b %Y')} - {e.strftime('%b %Y')}"
	return f"{s.strftime('%b')} - {e.strftime('%b')}"


def get_periods(start, end, step, fy_mode):
	multi_year = start.year != end.year
	periods, s, i = [], start, 0
	while s <= end:
		e = min(getdate(add_days(add_months(s, step), -1)), end)
		periods.append(
			frappe._dict(
				key=f"p{i}",
				start=s,
				end=e,
				label=period_label(s, e, step, i, fy_mode, multi_year),
			)
		)
		s, i = getdate(add_days(e, 1)), i + 1
		if i > MAX_PERIODS:
			frappe.throw(_("Too many periods ({0} max). Choose a shorter range or a longer frequency.").format(MAX_PERIODS))
	return periods


def get_comparison(filters, step, n_periods):
	"""None, or the comparison basis chosen in the Compare With filter."""
	name = filters.get("compare_with") or DEFAULT_COMPARISON
	conf = COMPARISONS.get(name)
	if not conf:
		return None
	fixed = conf.get("months")
	return frappe._dict(
		name=name,
		suffix=conf["suffix"],
		total_label=conf["total_label"],
		period_months=fixed or step,
		total_months=fixed or step * n_periods,
	)


def attach_comparison(periods, cmp):
	for per in periods:
		per.cmp_start = shift_start(per.start, cmp.period_months) if cmp else None
		per.cmp_end = shift_end(per.end, cmp.period_months) if cmp else None


def amount_col(label, fieldname):
	return {"label": label, "fieldname": fieldname, "fieldtype": "Currency", "width": AMOUNT_WIDTH}


def growth_col(label, fieldname):
	return {
		"label": label,
		"fieldname": fieldname,
		"fieldtype": "Float",
		"precision": GROWTH_PRECISION,
		"width": GROWTH_WIDTH,
	}


def get_columns(periods, fy_mode, opts):
	"""Account | (Period [, Period LY] [, Period Growth %] [, spacer]) x n | [Year to date, Last Year, Growth %]"""
	cmp = opts.cmp
	columns = [
		{"label": _("Account Name"), "fieldname": "account_name", "fieldtype": "Data", "width": ACCOUNT_WIDTH}
	]
	for per in periods:
		columns.append(amount_col(per.label, per.key))
		if cmp:
			columns.append(amount_col(f"{per.label} {_(cmp.suffix)}", f"{per.key}_ly"))
		if opts.growth:
			columns.append(growth_col(f"{per.label} {_('Growth %')}", f"{per.key}_var"))
		if SPACER_WIDTH:
			columns.append({"label": "", "fieldname": f"sp_{per.key}", "fieldtype": "Data", "width": SPACER_WIDTH})

	if opts.total:
		columns.append(amount_col(_("Year to date") if fy_mode else _("Period Total"), "year_to_date"))
		if cmp:
			columns.append(amount_col(_(cmp.total_label), "last_year_ytd"))
		if opts.growth:
			columns.append(growth_col(_("Growth %"), "achievement_ytd_pct"))
	return columns


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
def zline(n):
	return {"cur": [0.0] * n, "ly": [0.0] * n, "ytd": 0.0, "ly_ytd": 0.0}


def add_into(total, line, sign=1):
	for k in ("cur", "ly"):
		for i, v in enumerate(line[k]):
			total[k][i] += sign * v
	total["ytd"] += sign * line["ytd"]
	total["ly_ytd"] += sign * line["ly_ytd"]


def is_zero(line):
	return all(abs(v) < 0.005 for v in line["cur"] + line["ly"] + [line["ytd"], line["ly_ytd"]])


def variance(current, previous):
	if not flt(previous, PRECISION):
		return None
	return flt((current - previous) / abs(previous) * 100, GROWTH_PRECISION)


def make_row(name, line, periods, row_type, level=0):
	row = {"account_name": name, "row_type": row_type, "level": level}
	for i, per in enumerate(periods):
		cur, ly = flt(line["cur"][i], PRECISION), flt(line["ly"][i], PRECISION)
		row[per.key], row[f"{per.key}_ly"], row[f"{per.key}_var"] = cur, ly, variance(cur, ly)
	ytd, ly_ytd = flt(line["ytd"], PRECISION), flt(line["ly_ytd"], PRECISION)
	row["year_to_date"], row["last_year_ytd"], row["achievement_ytd_pct"] = ytd, ly_ytd, variance(ytd, ly_ytd)
	return row


def spacer_row():
	return {"account_name": "", "row_type": "spacer", "level": 0}


def blank_zeros(rows):
	for row in rows:
		for k, v in row.items():
			if k in ("account_name", "row_type", "level") or v is None:
				continue
			if isinstance(v, (int, float)) and abs(v) < 0.005:
				row[k] = None


def get_account_lines(filters, accounts, start, end, periods, cmp):
	"""One GL query -> {account: line}. Credit - debit for CREDIT_ROOT_TYPES, debit - credit otherwise."""
	company = filters.company
	n = len(periods)
	lines = {a.name: zline(n) for a in accounts}
	if not accounts:
		return lines, 0

	root = {a.name: a.root_type for a in accounts}
	ytd_end = min(end, getdate(today()))

	from_date = start
	if cmp:
		cmp_total_start = shift_start(start, cmp.total_months)
		cmp_ytd_end = shift_end(ytd_end, cmp.total_months)
		from_date = min(start, cmp_total_start, periods[0].cmp_start)
		cmp_starts = [x.cmp_start for x in periods]

	params = {"company": company, "voucher": EXCLUDED_VOUCHER_TYPE, "from": from_date, "to": end, "accounts": tuple(root)}
	extra = ""
	for field in DIMENSION_FILTERS:
		if filters.get(field):
			extra += f" AND `{field}` = %({field})s"
			params[field] = filters.get(field)

	rows = frappe.db.sql(
		f"""
		SELECT account, posting_date, SUM(debit) AS debit, SUM(credit) AS credit
		FROM `tabGL Entry`
		WHERE company = %(company)s AND is_cancelled = 0
			AND IFNULL(voucher_type, '') != %(voucher)s
			AND posting_date BETWEEN %(from)s AND %(to)s
			AND account IN %(accounts)s
			{extra}
		GROUP BY account, posting_date
		""",
		params,
		as_dict=True,
	)

	cur_starts = [x.start for x in periods]

	for r in rows:
		d = getdate(r.posting_date)
		credit_normal = root[r.account] in CREDIT_ROOT_TYPES
		val = flt(r.credit) - flt(r.debit) if credit_normal else flt(r.debit) - flt(r.credit)
		line = lines[r.account]

		i = bisect_right(cur_starts, d) - 1
		if i >= 0 and d <= periods[i].end:
			line["cur"][i] += val
			if d <= ytd_end:
				line["ytd"] += val

		if cmp:
			j = bisect_right(cmp_starts, d) - 1
			if j >= 0 and d <= periods[j].cmp_end:
				line["ly"][j] += val
			if cmp_total_start <= d <= cmp_ytd_end:
				line["ly_ytd"] += val

	return lines, len(rows)


def get_components(names):
	"""{formula group: [(component group, +1 / -1)]} in table order."""
	if not names:
		return {}
	rows = frappe.get_all(
		"Financial Reporting Group Component",
		filters={"parent": ["in", names], "parenttype": "Financial Reporting Group"},
		fields=["parent", "component", "operation"],
		order_by="parent asc, idx asc",
		parent_doctype="Financial Reporting Group",
	)
	out = {}
	for r in rows:
		out.setdefault(r.parent, []).append((r.component, -1 if r.operation == "Subtract" else 1))
	return out


def get_data(filters, start, end, periods, cmp):
	hide_detail = cint(filters.get("hide_detail"))
	hide_zero = cint(filters.get("hide_zero_accounts"))
	n = len(periods)

	defs = [
		d
		for d in frappe.get_all(
			"Financial Reporting Group",
			filters={"report_type": ["in", REPORT_TYPES], "is_active": 1},
			fields=["name", "is_formula", "is_group", "highlight"],
			order_by="sort_order asc, name asc",
		)
		if not d.is_group
	]
	def_by_name = {d.name: d for d in defs}
	group_by_norm = {norm(d.name): d.name for d in defs if not d.is_formula}
	components = get_components([d.name for d in defs if d.is_formula])

	accounts = frappe.get_all(
		"Account",
		filters={"company": filters.company, "is_group": 0, "root_type": ["in", ROOT_TYPES]},
		fields=["name", "account_name", "account_number", "custom_financial_reporting_group", "root_type"],
	)
	# numbered accounts first, in number order; then the rest by name
	accounts.sort(
		key=lambda a: (0, natural_key(a.account_number)) if a.account_number else (1, natural_key(a.name))
	)
	label_of = {a.name: (a.name if FULL_ACCOUNT_NAME else (a.account_name or a.name)) for a in accounts}
	lines, posting_rows = get_account_lines(filters, accounts, start, end, periods, cmp)

	by_group, unmapped = {}, []
	for a in accounts:
		g = group_by_norm.get(norm(a.custom_financial_reporting_group)) if a.custom_financial_reporting_group else None
		if g:
			by_group.setdefault(g, []).append(a.name)
		elif not is_zero(lines[a.name]):
			unmapped.append(label_of[a.name])

	# totals of normal groups (every mapped account, shown or not)
	group_lines = {}
	for name, names in by_group.items():
		total = zline(n)
		for acc in names:
			add_into(total, lines[acc])
		group_lines[name] = total

	# formula groups (may reference other formula groups)
	memo, missing, cyclic = {}, set(), set()

	def evaluate(name, stack=()):
		if name in memo:
			return memo[name]
		d = def_by_name.get(name)
		if not d:
			missing.add(name)
			return zline(n)
		if not d.is_formula:
			return group_lines.get(name) or zline(n)
		if name in stack:
			cyclic.add(name)
			return zline(n)
		line = zline(n)
		for comp, sign in components.get(name, []):
			add_into(line, evaluate(comp, stack + (name,)), sign)
		memo[name] = line
		return line

	def statement_row(d):
		return make_row(d.name, evaluate(d.name), periods, HIGHLIGHT_ROW_TYPE.get(d.highlight, "summary"))

	def visible_accounts(d):
		names = by_group.get(d.name) or []
		return [a for a in names if not (hide_zero and is_zero(lines[a]))]

	def note_rows(d):
		"""▶ Group / accounts / Total - Group / blank row"""
		shown = visible_accounts(d)
		if not shown:
			return []
		rows = [{"account_name": f"{SECTION_PREFIX}{d.name}", "row_type": "section", "level": 0}]
		rows += [make_row(INDENT + label_of[a], lines[a], periods, "line", 1) for a in shown]
		rows.append(make_row(f"{TOTAL_PREFIX}{d.name}", group_lines[d.name], periods, "total"))
		rows.append(spacer_row())
		return rows

	def collapsed_row(d):
		return [make_row(d.name, group_lines[d.name], periods, "summary")] if visible_accounts(d) else []

	normal_defs = [d for d in defs if not d.is_formula]
	formula_defs = [d for d in defs if d.is_formula]

	spec_notes = []

	def spec_rows():
		"""Summary calculated from SUMMARY_SPEC and the normal groups."""
		results, rows = {}, []
		for item in SUMMARY_SPEC:
			line, resolved, matched = zline(n), 0, None
			for refs, sign in item["parts"]:
				src = None
				for ref in refs:
					key = norm(ref)
					if key in results:
						src = results[key]
					elif group_by_norm.get(key) in group_lines:
						src = group_lines[group_by_norm[key]]
						matched = matched or group_by_norm[key]
					if src is not None:
						break
				if src is not None:
					add_into(line, src, sign)
					resolved += 1
				elif not item.get("warn"):
					spec_notes.append(
						_("{0}: no Financial Reporting Group named {1}").format(item["label"], " / ".join(refs))
					)
			results[norm(item["label"])] = line
			highlight = item.get("highlight")
			if not highlight and not resolved:
				if item.get("warn"):
					available = ", ".join(escape_html(g) for g in sorted(group_lines)) or "-"
					spec_notes.append(
						_("No Financial Reporting Group found for {0} (treated as zero). Groups with figures: {1}").format(
							item["label"], available
						)
					)
				continue
			label = matched if (item.get("use_group_label") and matched) else item["label"]
			rows.append(make_row(label, line, periods, HIGHLIGHT_ROW_TYPE.get(highlight, "summary")))
		return rows

	spec_results = {norm(i["label"]) for i in SUMMARY_SPEC if i.get("highlight")}
	doctype_complete = spec_results <= {norm(d.name) for d in formula_defs}
	use_spec = SUMMARY_SOURCE == "spec" or (SUMMARY_SOURCE == "auto" and not doctype_complete)
	statement = spec_rows() if use_spec else [statement_row(d) for d in formula_defs]

	data = []
	if hide_detail:
		if statement:  # statement lines only
			data = statement
		else:
			for d in normal_defs:
				data.extend(collapsed_row(d))
	else:  # notes first, then the statement lines
		for d in normal_defs:
			data.extend(note_rows(d))
		data.extend(statement)

	while data and data[-1]["row_type"] == "spacer":
		data.pop()

	blank_zeros(data)

	warnings, notes = [], list(spec_notes)
	if not defs:
		warnings.append(
			_("No active Financial Reporting Group with report type {0} was found.").format(" / ".join(REPORT_TYPES))
		)
	elif not group_lines or all(is_zero(t) for t in group_lines.values()):
		warnings.append(
			_(
				"No figures found. Income Statement groups: {0}; Income/Expense accounts: {1} "
				"(in a group: {2}); GL posting rows in {3} to {4}: {5}."
			).format(len(defs), len(accounts), sum(len(v) for v in by_group.values()), start, end, posting_rows)
		)
	if unmapped:
		shown = ", ".join(escape_html(x) for x in unmapped[:10])
		more = f" (+{len(unmapped) - 10} more)" if len(unmapped) > 10 else ""
		warnings.append(
			_("{0} Income/Expense account(s) with postings are not in an Income Statement group and are excluded: {1}{2}").format(
				len(unmapped), shown, more
			)
		)
	if cyclic:
		warnings.append(_("Circular formula in: {0}").format(", ".join(escape_html(x) for x in sorted(cyclic))))
	if missing:
		notes.append(
			_("Formula components that are not active Income Statement groups (treated as zero): {0}").format(
				", ".join(escape_html(x) for x in sorted(missing))
			)
		)

	return data, warnings, notes


def get_message(filters, start, end, cmp, warnings, notes):
	message = "<b>{0}</b> &ndash; {1} &middot; {2} to {3}".format(
		_(REPORT_TITLE),
		escape_html(filters.company),
		start.strftime("%d %b %Y"),
		end.strftime("%d %b %Y"),
	)
	if cmp:
		message += " &middot; " + _("compared with {0}").format(_(cmp.name))
	for w in warnings:
		message += f'<br><span style="color:var(--red-600)">{w}</span>'
	for n in notes:
		message += f'<br><span style="color:var(--text-muted)">{n}</span>'
	return message


def diagnose(company, from_date=None, to_date=None):
	"""
	bench --site <site> execute ecclesia.ecclesia.report.sci___report.sci___report.diagnose \
		--kwargs "{'company': 'My Company'}"
	"""
	from_date = getdate(from_date or f"{getdate(today()).year}-01-01")
	to_date = getdate(to_date or today())

	groups = frappe.get_all("Financial Reporting Group", fields=["name", "report_type"])
	print("Financial Reporting Groups by report_type:")
	for rt in sorted({g.report_type or "(blank)" for g in groups}):
		print("  ", rt, sum(1 for g in groups if (g.report_type or "(blank)") == rt))

	accounts = frappe.get_all(
		"Account",
		filters={"company": company, "is_group": 0, "root_type": ["in", ROOT_TYPES]},
		fields=["name", "custom_financial_reporting_group"],
	)
	print("Income/Expense leaf accounts:", len(accounts), "| with a group:", sum(1 for a in accounts if a.custom_financial_reporting_group))

	count = frappe.db.sql(
		"""
		SELECT COUNT(*) FROM `tabGL Entry` gle
		INNER JOIN `tabAccount` acc ON acc.name = gle.account
		WHERE gle.company = %s AND gle.is_cancelled = 0
			AND acc.root_type IN %s
			AND IFNULL(gle.voucher_type, '') != %s
			AND gle.posting_date BETWEEN %s AND %s
		""",
		(company, tuple(ROOT_TYPES), EXCLUDED_VOUCHER_TYPE, from_date, to_date),
	)[0][0]
	print(f"GL rows on Income/Expense accounts {from_date} to {to_date} (excl. closing):", count)