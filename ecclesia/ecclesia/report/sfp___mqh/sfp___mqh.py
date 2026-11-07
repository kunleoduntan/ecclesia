# Copyright (c) Value Plus
# For license information, please see license.txt

"""
SFP - MQH: Statement of Financial Position

Place at:
    apps/ecclesia/ecclesia/ecclesia/report/sfp___mqh/sfp___mqh.py

* Line items come from the Financial Reporting Group doctype:
    - label            = Financial Reporting Group name (what is set on Account.custom_financial_reporting_group)
    - order in section = sort_order, then name
    - section          = the group itself or the nearest ancestor in `parent_group`
                         whose name is one of: Non Current Assets, Current Assets, Equity,
                         Non Current Liabilities, Current Liabilities
                         (hyphen / case / "&" tolerant). If no ancestor matches, the account is
                         placed by its root/account type, keeping the group's name as the label.
* Balance Sheet accounts are selected by root_type (Asset / Liability / Equity) and Profit and Loss
  accounts by root_type (Income / Expense), so accounts with a blank report_type are not lost.
* Column names follow the frequency: Monthly "Jan 2026", Quarterly "Q1 2026",
  Half-Yearly "H1 2026", Yearly "FY 2026"; last-year columns carry the previous year.
* Rows carry `level` (not `indent`) so there is no expand/collapse tree.
"""

import frappe
from frappe import _
from frappe.utils import add_months, add_years, escape_html, flt, fmt_money, getdate, today

PCV = "Period Closing Voucher"
MONTHS = 12
PRECISION = 2

FREQ_STEP = {"Monthly": 1, "Quarterly": 3, "Half-Yearly": 6, "Yearly": 12}

BLOCKS = [
	("ASSETS", ("Non Current Assets", "Current Assets"), "Total Assets"),
	(
		"EQUITY AND LIABILITIES",
		("Equity", "Non Current Liabilities", "Current Liabilities"),
		"Total Equity & Liabilities",
	),
]

CREDIT_SECTIONS = ("Equity", "Non Current Liabilities", "Current Liabilities")
LIABILITY_SECTIONS = ("Non Current Liabilities", "Current Liabilities")
NON_CURRENT_ASSET_TYPES = (
	"Fixed Asset",
	"Capital Work in Progress",
	"Depreciation",
	"Accumulated Depreciation",
)

PROFIT_LABEL = "Profit for the year"
UNCLOSED_LABEL = "Retained earnings - prior years (not yet closed)"


def norm(text):
	return " ".join(
		(text or "").lower().replace("&", " and ").replace("/", " ").replace("-", " ").split()
	)


SECTION_LOOKUP = {norm(s): s for _b, sections, _t in BLOCKS for s in sections}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	fy = get_fiscal_year(filters)
	periods = get_periods(fy.start, filters.get("frequency"))

	columns = get_columns(periods)
	data, warnings, notes = get_data(filters, fy, periods)

	return columns, data, get_message(warnings, notes), None, None


# --------------------------------------------------------------------------
# Setup
# --------------------------------------------------------------------------
def get_fiscal_year(filters):
	if not filters.get("company"):
		frappe.throw(_("Please select a Company"))
	if not filters.get("year"):
		frappe.throw(_("Please select a Fiscal Year"))

	fy = frappe.db.get_value(
		"Fiscal Year", filters.year, ["year_start_date", "year_end_date"], as_dict=True
	)
	if not fy:
		frappe.throw(_("Fiscal Year {0} not found").format(filters.year))

	return frappe._dict(start=getdate(fy.year_start_date), end=getdate(fy.year_end_date))


def get_periods(fy_start, frequency):
	step = FREQ_STEP.get(frequency or "Monthly", 1)
	periods = []
	for i in range(MONTHS // step):
		end_idx = (i + 1) * step - 1
		year = getdate(add_months(fy_start, end_idx)).year  # year of the period's last month

		if step == 1:
			month_name = getdate(add_months(fy_start, i)).strftime("%b")
			label, ly_label = f"{month_name} {year}", f"{month_name} {year - 1}"
		elif step == 3:
			label, ly_label = f"Q{i + 1} {year}", f"Q{i + 1} {year - 1}"
		elif step == 6:
			label, ly_label = f"H{i + 1} {year}", f"H{i + 1} {year - 1}"
		else:
			label, ly_label = f"FY {year}", f"FY {year - 1}"

		periods.append(
			frappe._dict(key=f"p{i}", label=label, ly_label=ly_label, end_idx=end_idx)
		)
	return periods


def get_columns(periods):
	columns = [
		{"label": _("Account Name"), "fieldname": "account_name", "fieldtype": "Data", "width": 300}
	]
	for p in periods:
		columns += [
			{"label": p.label, "fieldname": p.key, "fieldtype": "Currency", "width": 150},
			{"label": p.ly_label, "fieldname": f"{p.key}_ly", "fieldtype": "Currency", "width": 150},
			{"label": _("Var %"), "fieldname": f"{p.key}_var", "fieldtype": "Float", "precision": 1, "width": 60},
		]
	columns.append(
		{"label": _("Year To Date"), "fieldname": "year_to_date", "fieldtype": "Currency", "width": 150}
	)
	return columns


# --------------------------------------------------------------------------
# Financial Reporting Group -> lines
# --------------------------------------------------------------------------
def get_group_meta():
	rows = frappe.get_all(
		"Financial Reporting Group", fields=["name", "parent_group", "sort_order"]
	)
	by_name = {r.name: r for r in rows}
	by_norm = {norm(r.name): r for r in rows}
	return by_name, by_norm


def resolve_section(group_name, by_name):
	seen, current = set(), group_name
	while current and current not in seen:
		seen.add(current)
		section = SECTION_LOOKUP.get(norm(current))
		if section:
			return section
		current = (by_name.get(current) or {}).get("parent_group")
	return None


def fallback_section(acc):
	if acc.root_type == "Asset":
		return "Non Current Assets" if acc.account_type in NON_CURRENT_ASSET_TYPES else "Current Assets"
	if acc.root_type == "Liability":
		return "Current Liabilities"
	return "Equity"


def build_lines(accounts):
	"""Returns ({section: [(label, [accounts])]}, {(section, label)} placed without a valid group)."""
	by_name, by_norm = get_group_meta()
	groups, no_group = {}, set()

	for a in accounts:
		raw = a.custom_financial_reporting_group
		meta = (by_name.get(raw) or by_norm.get(norm(raw))) if raw else None

		label = meta.name if meta else (raw or a.account_name or a.name)
		section = resolve_section(meta.name, by_name) if meta else None
		if not section:
			section = fallback_section(a)

		key = (section, label)
		entry = groups.setdefault(
			key, {"order": flt(meta.sort_order) if meta else 9999, "accounts": []}
		)
		entry["accounts"].append(a.name)
		if not meta:
			no_group.add(key)

	lines = {s: [] for _b, sections, _t in BLOCKS for s in sections}
	for (section, label), entry in sorted(groups.items(), key=lambda kv: (kv[1]["order"], kv[0][1])):
		lines[section].append((label, entry["accounts"]))

	return lines, no_group


# --------------------------------------------------------------------------
# GL access
# --------------------------------------------------------------------------
def month_index(ly_start, year, month):
	return (year - ly_start.year) * 12 + (month - ly_start.month)


def cumulative(values, start=0.0):
	out, running = [], start
	for v in values:
		running += v
		out.append(running)
	return out


def get_balances(company, accounts, ly_start, fy_end):
	"""{account: {"ly": [12 net], "cur": [12 net]}}  (net = debit - credit)."""
	result = {}
	if not accounts:
		return result

	values = {"company": company, "accounts": tuple(accounts), "ly_start": ly_start, "to": fy_end}

	opening = {
		r.account: flt(r.net)
		for r in frappe.db.sql(
			"""
			SELECT account, SUM(debit) - SUM(credit) AS net
			FROM `tabGL Entry`
			WHERE company = %(company)s AND is_cancelled = 0
				AND posting_date < %(ly_start)s AND account IN %(accounts)s
			GROUP BY account
			""",
			values,
			as_dict=True,
		)
	}

	movements = frappe.db.sql(
		"""
		SELECT account, YEAR(posting_date) AS y, MONTH(posting_date) AS m,
			IFNULL(voucher_type, '') = %(pcv)s AS is_pcv,
			SUM(debit) AS debit, SUM(credit) AS credit
		FROM `tabGL Entry`
		WHERE company = %(company)s AND is_cancelled = 0
			AND posting_date BETWEEN %(ly_start)s AND %(to)s AND account IN %(accounts)s
		GROUP BY account, y, m, is_pcv
		""",
		{**values, "pcv": PCV},
		as_dict=True,
	)

	ly_move = {a: [0.0] * MONTHS for a in accounts}
	cur_move = {a: [0.0] * MONTHS for a in accounts}
	carry = dict.fromkeys(accounts, 0.0)

	for r in movements:
		idx = month_index(ly_start, r.y, r.m)
		net = flt(r.debit) - flt(r.credit)
		if 0 <= idx < MONTHS:
			carry[r.account] += net
			if not r.is_pcv:
				ly_move[r.account][idx] += net
		elif MONTHS <= idx < 2 * MONTHS and not r.is_pcv:
			cur_move[r.account][idx - MONTHS] += net

	for a in accounts:
		open_bal = opening.get(a, 0.0)
		result[a] = {
			"ly": cumulative(ly_move[a], open_bal),
			"cur": cumulative(cur_move[a], open_bal + carry[a]),
		}
	return result


def get_profit(company, fy_start, ly_start, fy_end):
	"""
	profit  : cumulative P&L (credit - debit) from each year's start, excluding closing entries.
	unclosed: P&L of earlier years not yet moved to equity by a Period Closing Voucher
	          (all P&L entries incl. closing entries before the year start; zero once closed).
	"""
	rows = frappe.db.sql(
		"""
		SELECT YEAR(gle.posting_date) AS y, MONTH(gle.posting_date) AS m,
			SUM(gle.credit - gle.debit) AS amount
		FROM `tabGL Entry` gle
		INNER JOIN `tabAccount` acc ON acc.name = gle.account
		WHERE gle.company = %(company)s AND gle.is_cancelled = 0
			AND acc.root_type IN ('Income', 'Expense')
			AND IFNULL(gle.voucher_type, '') != %(pcv)s
			AND gle.posting_date BETWEEN %(ly_start)s AND %(to)s
		GROUP BY y, m
		""",
		{"company": company, "pcv": PCV, "ly_start": ly_start, "to": fy_end},
		as_dict=True,
	)

	ly, cur = [0.0] * MONTHS, [0.0] * MONTHS
	for r in rows:
		idx = month_index(ly_start, r.y, r.m)
		if 0 <= idx < MONTHS:
			ly[idx] += flt(r.amount)
		elif MONTHS <= idx < 2 * MONTHS:
			cur[idx - MONTHS] += flt(r.amount)

	def before(date):
		res = frappe.db.sql(
			"""
			SELECT SUM(gle.credit - gle.debit)
			FROM `tabGL Entry` gle
			INNER JOIN `tabAccount` acc ON acc.name = gle.account
			WHERE gle.company = %s AND gle.is_cancelled = 0
				AND acc.root_type IN ('Income', 'Expense') AND gle.posting_date < %s
			""",
			(company, date),
		)
		return flt(res[0][0]) if res else 0.0

	return {
		"profit": {"ly": cumulative(ly), "cur": cumulative(cur)},
		"unclosed": {"ly": [before(ly_start)] * MONTHS, "cur": [before(fy_start)] * MONTHS},
	}


# --------------------------------------------------------------------------
# Report body
# --------------------------------------------------------------------------
def variance(current, last_year):
	if not flt(last_year, PRECISION):
		return None
	return flt((current - last_year) / abs(last_year) * 100, 1)


def zeros():
	return {"cur": [0.0] * MONTHS, "ly": [0.0] * MONTHS}


def add_into(total, line):
	for k in ("cur", "ly"):
		for i in range(MONTHS):
			total[k][i] += line[k][i]


def is_zero(line):
	return all(abs(v) < 0.005 for k in ("cur", "ly") for v in line[k])


def make_row(name, line, periods, ytd_idx, row_type, level=0):
	row = {"account_name": name, "row_type": row_type, "level": level}
	for p in periods:
		cur = flt(line["cur"][p.end_idx], PRECISION)
		ly = flt(line["ly"][p.end_idx], PRECISION)
		row[p.key] = cur
		row[f"{p.key}_ly"] = ly
		row[f"{p.key}_var"] = variance(cur, ly)
	row["year_to_date"] = flt(line["cur"][ytd_idx], PRECISION)
	return row


def spacer():
	return {"account_name": "", "row_type": "spacer", "level": 0}


def get_ytd_index(fy):
	today_date = getdate(today())
	if today_date >= fy.end:
		return MONTHS - 1
	if today_date < fy.start:
		return 0
	return min(max(month_index(fy.start, today_date.year, today_date.month), 0), MONTHS - 1)


def get_data(filters, fy, periods):
	company = filters.company
	ly_start = getdate(add_years(fy.start, -1))
	hide_zero = frappe.parse_json(filters.get("show_only_ytd") or 0)
	ytd_idx = get_ytd_index(fy)

	accounts = frappe.get_all(
		"Account",
		filters={"company": company, "is_group": 0, "root_type": ["in", ["Asset", "Liability", "Equity"]]},
		fields=["name", "account_name", "custom_financial_reporting_group", "root_type", "account_type"],
	)
	balances = get_balances(company, [a.name for a in accounts], ly_start, fy.end)
	lines, no_group = build_lines(accounts)
	pl = get_profit(company, fy.start, ly_start, fy.end)

	def account_line(names, sign):
		line = zeros()
		for n in names:
			for k in ("cur", "ly"):
				for i in range(MONTHS):
					line[k][i] += sign * balances[n][k][i]
		return line

	data, grand = [], {}
	liabilities = zeros()
	auto_notes = []

	for heading, sections, grand_label in BLOCKS:
		data.append({"account_name": heading, "row_type": "heading", "level": 0})
		block_total = zeros()

		for section in sections:
			sign = -1 if section in CREDIT_SECTIONS else 1
			section_total = zeros()
			rows = []

			for label, names in lines[section]:
				line = account_line(names, sign)
				if (section, label) in no_group:
					if is_zero(line):
						continue
					auto_notes.append(f"{escape_html(label)} → {section}")
				add_into(section_total, line)
				row = make_row(label, line, periods, ytd_idx, "line", level=2)
				if hide_zero and not row["year_to_date"]:
					continue
				rows.append(row)

			if section == "Equity":
				unclosed = pl["unclosed"]
				if not is_zero(unclosed):
					add_into(section_total, unclosed)
					rows.append(make_row(UNCLOSED_LABEL, unclosed, periods, ytd_idx, "line", level=2))
				profit = pl["profit"]
				add_into(section_total, profit)
				rows.append(make_row(PROFIT_LABEL, profit, periods, ytd_idx, "profit", level=2))

			data.append({"account_name": section, "row_type": "section", "level": 1})
			data.extend(rows)
			data.append(make_row(f"Total - {section}", section_total, periods, ytd_idx, "total", level=1))

			add_into(block_total, section_total)
			if section in LIABILITY_SECTIONS:
				add_into(liabilities, section_total)
				if section == LIABILITY_SECTIONS[-1]:
					data.append(make_row("Total Liabilities", liabilities, periods, ytd_idx, "total", level=1))
			data.append(spacer())

		data.append(make_row(grand_label, block_total, periods, ytd_idx, "grand_total"))
		data.append(spacer())
		grand[heading] = block_total

	warnings, notes = [], []

	assets, eql = grand["ASSETS"], grand["EQUITY AND LIABILITIES"]
	diff = {k: [assets[k][i] - eql[k][i] for i in range(MONTHS)] for k in ("cur", "ly")}
	if any(abs(v) > 0.01 for k in diff for v in diff[k]):
		data.append(make_row("Difference (Assets - Equity & Liabilities)", diff, periods, ytd_idx, "difference"))
		worst = max(
			((abs(v), k, i) for k in diff for i, v in enumerate(diff[k])), key=lambda t: t[0]
		)
		warnings.append(
			_("Statement out of balance. Largest difference: {0} ({1}, month {2} of the fiscal year).").format(
				fmt_money(worst[0], currency=frappe.get_cached_value("Company", company, "default_currency")),
				_("this year") if worst[1] == "cur" else _("last year"),
				worst[2] + 1,
			)
		)

	if auto_notes:
		notes.append(
			_("Placed by account type because the account has no valid Financial Reporting Group: {0}").format(
				"; ".join(sorted(set(auto_notes))[:10])
			)
		)

	return data, warnings, notes


def get_message(warnings, notes):
	message = _("Statement of Financial Position")
	for w in warnings:
		message += f'<br><span style="color:var(--red-600)">{w}</span>'
	for n in notes:
		message += f'<br><span style="color:var(--text-muted)">{n}</span>'
	return message