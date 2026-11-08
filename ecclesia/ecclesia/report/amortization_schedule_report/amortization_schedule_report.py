# Copyright (c) 2026, Value Plus and contributors
# For license information, please see license.txt

"""
Amortization Schedule Report  (Purchase Invoice -> custom_amortization_schedule)

Three views, one engine:
  1. Detailed Schedule  - every instalment, running balance, status, JE trace, audit flags
  2. Invoice Summary    - audit roll-forward per invoice
                          (Opening + Additions - Charge = Closing)
  3. Monthly Summary    - P&L charge profile by month and expense account

Formatted Excel (workbook with banner, KPI cards, exceptions, chart, audit notes and
sign-off block) is produced by `export_excel` below via excel_export.py.

Basis of preparation
  * Balances are on a SCHEDULE basis (what should be recognised per the schedule).
  * "Posted" is decided by ONE of:
      - Trace Journal Entries ticked : a submitted JE (reference = the invoice) is
        found with a debit on the expense account for the instalment amount.
      - otherwise                    : the invoice's `custom_next_schedule` pointer.
  * "Overdue" = not posted and the schedule date is before today.
"""

from collections import Counter

import frappe
from frappe import _
from frappe.utils import cint, flt, formatdate, getdate, today

# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------
PRECISION = 2
TOL = 0.01

# custom_next_schedule is the 1-based number of the NEXT instalment to post
# (so instalments before it are posted).  If your posting code stores the
# 0-based index / count of instalments already posted, set this to 0.
NEXT_SCHEDULE_BASE = 1

POSTED, OVERDUE, SCHEDULED = "Posted", "Overdue", "Scheduled"
DATE_MIN = getdate("1900-01-01")
DATE_MAX = getdate("2999-12-31")

VIEW_DETAIL = "Detailed Schedule"
VIEW_SUMMARY = "Invoice Summary"
VIEW_MONTHLY = "Monthly Summary"


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------
def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)

	view = filters.view or VIEW_DETAIL
	currency = frappe.get_cached_value("Company", filters.company, "default_currency")
	columns = get_columns(view, filters)

	invoices = get_invoices(filters)
	if not invoices:
		return columns, [], _("No amortized Purchase Invoices found for the selected filters."), None, None, True

	schedule = get_schedule(invoices)
	evidence = get_je_evidence(invoices) if cint(filters.trace_je) else {}

	analysed = []
	for inv in invoices:
		result = analyse_invoice(inv, schedule.get(inv.name, []), evidence.get(inv.name, []), filters)
		if result:
			analysed.append(result)

	if view == VIEW_SUMMARY:
		shown = [
			a for a in analysed if has_activity(a) and (not cint(filters.exceptions_only) or a.exception)
		]
		data = get_summary_data(shown, currency)
		chart = get_summary_chart(shown)
	else:
		pairs = get_display_rows(analysed, filters)
		seen, shown = set(), []
		for a, _row, _first in pairs:
			if a.inv.name not in seen:
				seen.add(a.inv.name)
				shown.append(a)
		data = get_monthly_data(pairs, currency) if view == VIEW_MONTHLY else get_detail_data(pairs, currency)
		chart = get_period_chart(pairs)

	if not data:
		return columns, [], _("No records match the selected filters."), None, None, True

	return (
		columns,
		data,
		get_message(shown, filters),
		chart,
		get_report_summary(shown, currency),
		True,  # skip Frappe's automatic total row - totals are built here
	)


def validate_filters(filters):
	if not filters.company:
		frappe.throw(_("Please select a Company."))
	if filters.from_date and filters.to_date and getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date."))


# --------------------------------------------------------------------------
# Data access
# --------------------------------------------------------------------------
def get_invoices(filters):
	conditions = ["pi.custom_is_amortized_cost = 1", "pi.company = %(company)s"]
	values = {"company": filters.company}

	conditions.append("pi.docstatus IN (0, 1)" if cint(filters.include_draft) else "pi.docstatus = 1")

	if filters.to_date:
		conditions.append("pi.posting_date <= %(to_date)s")
		values["to_date"] = getdate(filters.to_date)

	for key, column in (
		("supplier", "pi.supplier"),
		("purchase_invoice", "pi.name"),
		("cost_center", "pi.cost_center"),
		("frequency", "pi.custom_frequency"),
	):
		if filters.get(key):
			conditions.append(f"{column} = %({key})s")
			values[key] = filters.get(key)

	if filters.expense_account:
		conditions.append(
			"""(pi.custom_expense_account = %(expense_account)s OR EXISTS (
				SELECT 1 FROM `tabAmortization Schedule` s
				WHERE s.parent = pi.name AND s.parenttype = 'Purchase Invoice'
				AND s.account_to_debit = %(expense_account)s))"""
		)
		values["expense_account"] = filters.expense_account

	return frappe.db.sql(
		f"""
		SELECT
			pi.name, pi.supplier, pi.supplier_name, pi.bill_no, pi.bill_date,
			pi.posting_date, pi.company, pi.docstatus, pi.cost_center,
			pi.custom_start_date, pi.custom_end_date, pi.custom_frequency,
			pi.custom_no_of_periods, pi.custom_charged_amount,
			pi.custom_next_schedule, pi.custom_next_posting_date,
			pi.custom_expense_account, pi.custom_deferred_expense_account,
			pi.custom_is_shared_cost
		FROM `tabPurchase Invoice` pi
		WHERE {" AND ".join(conditions)}
		ORDER BY pi.posting_date, pi.name
		""",
		values,
		as_dict=True,
	)


def get_schedule(invoices):
	rows = frappe.db.sql(
		"""
		SELECT parent, idx, title, `date`, transaction_description, amount,
			account_to_debit, account_to_credit, period, frequency, prepayment_balance
		FROM `tabAmortization Schedule`
		WHERE parenttype = 'Purchase Invoice'
			AND parentfield = 'custom_amortization_schedule'
			AND parent IN %(parents)s
		ORDER BY parent, idx
		""",
		{"parents": tuple(i.name for i in invoices)},
		as_dict=True,
	)
	out = {}
	for r in rows:
		out.setdefault(r.parent, []).append(r)
	return out


def get_je_evidence(invoices):
	"""Debit lines of submitted Journal Entries that reference the invoice."""
	rows = frappe.db.sql(
		"""
		SELECT jea.reference_name AS invoice, je.name AS journal_entry,
			je.posting_date, jea.account, jea.debit AS amount
		FROM `tabJournal Entry Account` jea
		INNER JOIN `tabJournal Entry` je ON je.name = jea.parent
		WHERE je.docstatus = 1
			AND jea.reference_type = 'Purchase Invoice'
			AND jea.reference_name IN %(names)s
			AND jea.debit > 0
		ORDER BY je.posting_date, je.name
		""",
		{"names": tuple(i.name for i in invoices)},
		as_dict=True,
	)
	out = {}
	for r in rows:
		out.setdefault(r.invoice, []).append(r)
	return out


# --------------------------------------------------------------------------
# Engine
# --------------------------------------------------------------------------
def detect_balance_convention(rows, base):
	"""Is the stored prepayment_balance the balance AFTER or BEFORE the instalment?"""
	if not rows:
		return "closing"
	first = rows[0]
	stored = flt(first.prepayment_balance)
	if abs(stored - (base - flt(first.amount))) <= TOL:
		return "closing"
	if abs(stored - base) <= TOL:
		return "opening"
	return "closing"


def match_journal_entries(rows, je_rows, inv):
	"""Greedy one-to-one match of instalments to JE debit lines (account + amount)."""
	used, matches = set(), {}
	for pos, r in enumerate(rows):
		account = r.account_to_debit or inv.custom_expense_account
		for i, je in enumerate(je_rows):
			if i in used:
				continue
			if account and je.account != account:
				continue
			if abs(flt(je.amount) - flt(r.amount)) > TOL:
				continue
			used.add(i)
			matches[pos] = je.journal_entry
			break
	return matches


def analyse_invoice(inv, rows, je_rows, filters):
	from_date = getdate(filters.from_date) if filters.from_date else DATE_MIN
	to_date = getdate(filters.to_date) if filters.to_date else DATE_MAX
	posting_date = getdate(inv.posting_date)
	if posting_date > to_date:
		return None

	today_date = getdate(today())
	trace = cint(filters.trace_je)

	total = flt(sum(flt(r.amount) for r in rows), PRECISION)
	charged = flt(inv.custom_charged_amount, PRECISION)
	base = charged if charged > TOL else total

	# ---- invoice-level audit flags
	flags = []
	if not rows:
		flags.append(_("No schedule generated"))
	if charged <= TOL:
		flags.append(_("Charged Amount not set"))
	elif rows and abs(total - charged) > TOL:
		flags.append(_("Schedule total ≠ Charged Amount"))
	if rows and cint(inv.custom_no_of_periods) and cint(inv.custom_no_of_periods) != len(rows):
		flags.append(_("Periods ≠ schedule lines"))

	matches = match_journal_entries(rows, je_rows, inv) if trace else {}
	posted_pointer = max(cint(inv.custom_next_schedule) - NEXT_SCHEDULE_BASE, 0)
	convention = detect_balance_convention(rows, base)
	balance_maintained = any(abs(flt(r.prepayment_balance)) > TOL for r in rows)
	date_count = Counter(getdate(r.date) for r in rows if r.date)
	start = getdate(inv.custom_start_date) if inv.custom_start_date else None
	end = getdate(inv.custom_end_date) if inv.custom_end_date else None

	# ---- instalment loop
	prepared, cumulative = [], 0.0
	for pos, r in enumerate(rows):
		d = getdate(r.date) if r.date else None
		amount = flt(r.amount, PRECISION)
		opening_bal = flt(base - cumulative, PRECISION)
		cumulative = flt(cumulative + amount, PRECISION)
		closing_bal = flt(base - cumulative, PRECISION)

		je = matches.get(pos)
		by_pointer = pos < posted_pointer
		posted = bool(je) if trace else by_pointer
		if posted:
			status = POSTED
		elif d and d < today_date:
			status = OVERDUE
		else:
			status = SCHEDULED

		debit_acc = r.account_to_debit or inv.custom_expense_account
		credit_acc = r.account_to_credit or inv.custom_deferred_expense_account

		row_flags = []
		if not d:
			row_flags.append(_("Missing date"))
		else:
			if (start and d < start) or (end and d > end):
				row_flags.append(_("Date outside term"))
			if date_count[d] > 1:
				row_flags.append(_("Duplicate date"))
		if amount <= 0:
			row_flags.append(_("Non-positive amount"))
		if not debit_acc or not credit_acc:
			row_flags.append(_("Account missing"))
		elif debit_acc == credit_acc:
			row_flags.append(_("Debit = Credit account"))

		variance = None
		if balance_maintained:
			expected = closing_bal if convention == "closing" else opening_bal
			variance = flt(flt(r.prepayment_balance) - expected, PRECISION)
			if abs(variance) > TOL:
				row_flags.append(_("Balance mismatch"))

		if trace:
			if by_pointer and not je:
				row_flags.append(_("Pointer says posted - no JE found"))
			elif je and not by_pointer:
				row_flags.append(_("JE found - pointer not advanced"))

		prepared.append(
			frappe._dict(
				idx=r.idx,
				date=d,
				period=r.period,
				description=r.transaction_description or r.title,
				amount=amount,
				cumulative=cumulative,
				closing=closing_bal,
				schedule_balance=flt(r.prepayment_balance, PRECISION),
				variance=variance,
				status=status,
				journal_entry=je,
				debit_account=debit_acc,
				credit_account=credit_acc,
				flags=row_flags,
				in_window=(d is None and not filters.from_date and not filters.to_date)
				or (d is not None and from_date <= d <= to_date),
			)
		)

	# ---- period roll-forward: Opening + Additions - Charge = Closing
	split = {POSTED: 0.0, OVERDUE: 0.0, SCHEDULED: 0.0}
	amortised_before = 0.0
	for r in prepared:
		if r.date is None or r.date > to_date:
			continue
		if r.date >= from_date or posting_date >= from_date:
			split[r.status] += r.amount  # in the charge (incl. catch-up of back-dated lines)
		else:
			amortised_before += r.amount

	charge = flt(sum(split.values()), PRECISION)
	if posting_date < from_date:
		opening, additions = flt(base - amortised_before, PRECISION), 0.0
	else:
		opening, additions = 0.0, base
	closing = flt(opening + additions - charge, PRECISION)

	posted_rows = sum(1 for r in prepared if r.status == POSTED)
	overdue_rows = [r for r in prepared if r.status == OVERDUE]
	if not prepared or (not posted_rows and not overdue_rows):
		status = _("Not Started")
	elif overdue_rows:
		status = _("Overdue")
	elif posted_rows == len(prepared):
		status = _("Completed")
	else:
		status = _("In Progress")

	exception = bool(flags) or any(r.flags for r in prepared) or bool(overdue_rows)

	return frappe._dict(
		inv=inv,
		rows=prepared,
		base=base,
		total=total,
		opening=opening,
		additions=additions,
		charge=charge,
		charge_posted=flt(split[POSTED], PRECISION),
		charge_overdue=flt(split[OVERDUE], PRECISION),
		charge_scheduled=flt(split[SCHEDULED], PRECISION),
		closing=closing,
		overdue_amount=flt(sum(r.amount for r in overdue_rows), PRECISION),
		status=status,
		flags=flags,
		exception=exception,
	)


def has_activity(a):
	return abs(a.opening) + abs(a.additions) + abs(a.charge) + abs(a.closing) > TOL


def get_display_rows(analysed, filters):
	"""(analysis, instalment, is_first_row_of_invoice) after window / status / exception filters."""
	exceptions_only = cint(filters.exceptions_only)
	pairs = []
	for a in analysed:
		if exceptions_only and not a.exception:
			continue
		rows = [r for r in a.rows if r.in_window and (not filters.status or r.status == filters.status)]
		if exceptions_only:
			keep = [r for r in rows if r.flags or r.status == OVERDUE]
			if not keep and a.flags and rows:
				keep = rows[:1]
			rows = keep
		for i, r in enumerate(rows):
			pairs.append((a, r, i == 0))
	return pairs


# --------------------------------------------------------------------------
# Columns
# --------------------------------------------------------------------------
def col(label, fieldname, fieldtype="Data", width=110, options=None, hidden=0):
	column = {"label": _(label), "fieldname": fieldname, "fieldtype": fieldtype, "width": width}
	if options:
		column["options"] = options
	if hidden:
		column["hidden"] = 1
	return column


def money(label, fieldname, width=130):
	return col(label, fieldname, "Currency", width, "currency")


def get_columns(view, filters):
	currency = col("Currency", "currency", "Link", 60, "Currency", hidden=1)

	if view == VIEW_SUMMARY:
		return [
			col("Purchase Invoice", "purchase_invoice", "Link", 150, "Purchase Invoice"),
			col("Supplier", "supplier_name", "Data", 180),
			col("Supplier Inv No", "bill_no", "Data", 110),
			col("Posting Date", "posting_date", "Date", 95),
			col("Start Date", "start_date", "Date", 95),
			col("End Date", "end_date", "Date", 95),
			col("Frequency", "frequency", "Data", 90),
			col("Instalments", "instalments", "Int", 85),
			money("Total Amortizable", "base"),
			money("Opening Balance", "opening"),
			money("Additions", "additions"),
			money("Charge for Period", "charge"),
			money("Charge - Posted", "charge_posted"),
			money("Charge - Overdue", "charge_overdue"),
			money("Charge - Scheduled", "charge_scheduled"),
			money("Closing Balance", "closing"),
			col("% Amortized", "percent", "Percent", 95),
			col("Next Posting Date", "next_posting_date", "Date", 110),
			col("Status", "status", "Data", 100),
			col("Expense Account", "expense_account", "Link", 200, "Account"),
			col("Deferred Account", "deferred_account", "Link", 200, "Account"),
			col("Cost Center", "cost_center", "Link", 150, "Cost Center"),
			col("Shared Cost", "shared_cost", "Data", 85),
			col("Audit Flags", "flags", "Data", 300),
			currency,
		]

	if view == VIEW_MONTHLY:
		return [
			col("Month", "month", "Data", 90),
			col("Expense Account", "expense_account", "Link", 240, "Account"),
			col("Instalments", "instalments", "Int", 90),
			money("Amount", "amount"),
			money("Posted", "posted"),
			money("Overdue", "overdue"),
			money("Scheduled", "scheduled"),
			money("Cumulative", "cumulative"),
			currency,
		]

	columns = [
		col("Purchase Invoice", "purchase_invoice", "Link", 150, "Purchase Invoice"),
		col("Supplier", "supplier_name", "Data", 180),
		col("Supplier Inv No", "bill_no", "Data", 110),
		col("#", "idx", "Int", 45),
		col("Schedule Date", "schedule_date", "Date", 100),
		col("Period", "period", "Data", 110),
		col("Description", "description", "Data", 230),
		money("Amount", "amount", 120),
		money("Cumulative Amortized", "cumulative"),
		money("Balance After (Computed)", "closing_balance", 150),
		money("Balance per Schedule", "schedule_balance", 140),
		money("Variance", "variance", 100),
		col("Status", "status", "Data", 90),
	]
	if cint(filters.trace_je):
		columns.append(col("Journal Entry", "journal_entry", "Link", 140, "Journal Entry"))
	columns += [
		col("Expense Account", "expense_account", "Link", 200, "Account"),
		col("Deferred Account", "deferred_account", "Link", 200, "Account"),
		col("Cost Center", "cost_center", "Link", 150, "Cost Center"),
		col("Audit Flags", "flags", "Data", 300),
		currency,
	]
	return columns


# --------------------------------------------------------------------------
# Data builders
# --------------------------------------------------------------------------
def get_detail_data(pairs, currency):
	data, total = [], 0.0
	for a, r, first in pairs:
		inv = a.inv
		flags = list(r.flags) + (list(a.flags) if first else [])
		data.append(
			{
				"purchase_invoice": inv.name,
				"supplier_name": inv.supplier_name or inv.supplier,
				"bill_no": inv.bill_no,
				"idx": r.idx,
				"schedule_date": r.date,
				"period": r.period,
				"description": r.description,
				"amount": r.amount,
				"cumulative": r.cumulative,
				"closing_balance": r.closing,
				"schedule_balance": r.schedule_balance,
				"variance": r.variance,
				"status": r.status,
				"journal_entry": r.journal_entry,
				"expense_account": r.debit_account,
				"deferred_account": r.credit_account,
				"cost_center": inv.cost_center,
				"flags": "; ".join(flags),
				"currency": currency,
			}
		)
		total += r.amount
	if data:
		data.append({"purchase_invoice": _("Total"), "amount": flt(total, PRECISION), "currency": currency, "is_total_row": 1})
	return data


def get_summary_data(shown, currency):
	data = []
	totals = {k: 0.0 for k in ("base", "opening", "additions", "charge", "charge_posted", "charge_overdue", "charge_scheduled", "closing")}
	for a in shown:
		inv = a.inv
		amortised = a.base - a.closing
		first = a.rows[0] if a.rows else None
		data.append(
			{
				"purchase_invoice": inv.name,
				"supplier_name": inv.supplier_name or inv.supplier,
				"bill_no": inv.bill_no,
				"posting_date": inv.posting_date,
				"start_date": inv.custom_start_date,
				"end_date": inv.custom_end_date,
				"frequency": inv.custom_frequency,
				"instalments": len(a.rows),
				"base": a.base,
				"opening": a.opening,
				"additions": a.additions,
				"charge": a.charge,
				"charge_posted": a.charge_posted,
				"charge_overdue": a.charge_overdue,
				"charge_scheduled": a.charge_scheduled,
				"closing": a.closing,
				"percent": flt(amortised / a.base * 100, 2) if a.base > TOL else 0,
				"next_posting_date": inv.custom_next_posting_date,
				"status": a.status,
				"expense_account": (first.debit_account if first else None) or inv.custom_expense_account,
				"deferred_account": (first.credit_account if first else None) or inv.custom_deferred_expense_account,
				"cost_center": inv.cost_center,
				"shared_cost": _("Yes") if cint(inv.custom_is_shared_cost) else "",
				"flags": "; ".join(_flatten_flags(a)),
				"currency": currency,
			}
		)
		for k in totals:
			totals[k] += a[k]

	if data:
		total_base = totals["base"]
		data.append(
			{
				"purchase_invoice": _("Total"),
				**{k: flt(v, PRECISION) for k, v in totals.items()},
				"percent": flt((total_base - totals["closing"]) / total_base * 100, 2) if total_base > TOL else 0,
				"currency": currency,
				"is_total_row": 1,
			}
		)
	return data


def _flatten_flags(a):
	"""Invoice-level flags + a de-duplicated count of instalment-level flags."""
	out = list(a.flags)
	counter = Counter(f for r in a.rows for f in r.flags)
	out += [f"{label} ({n})" if n > 1 else label for label, n in counter.items()]
	if a.overdue_amount > TOL:
		out.append(_("Overdue instalments"))
	return out


def get_monthly_data(pairs, currency):
	buckets = {}
	for _a, r, _first in pairs:
		if not r.date:
			continue
		key = (r.date.strftime("%Y-%m"), r.debit_account or "")
		b = buckets.setdefault(key, {"n": 0, "amount": 0.0, POSTED: 0.0, OVERDUE: 0.0, SCHEDULED: 0.0})
		b["n"] += 1
		b["amount"] += r.amount
		b[r.status] += r.amount

	data, running = [], 0.0
	totals = {"n": 0, "amount": 0.0, POSTED: 0.0, OVERDUE: 0.0, SCHEDULED: 0.0}
	for (month, account) in sorted(buckets):
		b = buckets[(month, account)]
		running += b["amount"]
		data.append(
			{
				"month": month,
				"expense_account": account,
				"instalments": b["n"],
				"amount": flt(b["amount"], PRECISION),
				"posted": flt(b[POSTED], PRECISION),
				"overdue": flt(b[OVERDUE], PRECISION),
				"scheduled": flt(b[SCHEDULED], PRECISION),
				"cumulative": flt(running, PRECISION),
				"currency": currency,
			}
		)
		for k in totals:
			totals[k] += b[k]
	if data:
		data.append(
			{
				"month": _("Total"),
				"instalments": totals["n"],
				"amount": flt(totals["amount"], PRECISION),
				"posted": flt(totals[POSTED], PRECISION),
				"overdue": flt(totals[OVERDUE], PRECISION),
				"scheduled": flt(totals[SCHEDULED], PRECISION),
				"currency": currency,
				"is_total_row": 1,
			}
		)
	return data


# --------------------------------------------------------------------------
# Chart, cards, message
# --------------------------------------------------------------------------
def get_period_chart(pairs):
	months = {}
	for _a, r, _first in pairs:
		if not r.date:
			continue
		m = months.setdefault(r.date.strftime("%Y-%m"), {POSTED: 0.0, OVERDUE: 0.0, SCHEDULED: 0.0})
		m[r.status] += r.amount
	if not months:
		return None
	keys = sorted(months)
	return {
		"data": {
			"labels": [getdate(k + "-01").strftime("%b %Y") for k in keys],
			"datasets": [
				{"name": _("Posted"), "values": [flt(months[k][POSTED], PRECISION) for k in keys]},
				{"name": _("Overdue"), "values": [flt(months[k][OVERDUE], PRECISION) for k in keys]},
				{"name": _("Scheduled"), "values": [flt(months[k][SCHEDULED], PRECISION) for k in keys]},
			],
		},
		"type": "bar",
		"barOptions": {"stacked": 1},
		"colors": ["#29CD42", "#E24C4C", "#7CD6FD"],
		"fieldtype": "Currency",
	}


def get_summary_chart(shown):
	by_account = {}
	for a in shown:
		if a.closing > TOL:
			first = a.rows[0] if a.rows else None
			account = (first.credit_account if first else None) or a.inv.custom_deferred_expense_account or _("Unassigned")
			by_account[account] = by_account.get(account, 0.0) + a.closing
	if not by_account:
		return None
	ranked = sorted(by_account.items(), key=lambda kv: kv[1], reverse=True)
	top, rest = ranked[:8], sum(v for _k, v in ranked[8:])
	if rest > TOL:
		top.append((_("Others"), rest))
	return {
		"data": {
			"labels": [k for k, _v in top],
			"datasets": [{"name": _("Closing Balance"), "values": [flt(v, PRECISION) for _k, v in top]}],
		},
		"type": "donut",
		"fieldtype": "Currency",
	}


def get_report_summary(shown, currency):
	overdue = flt(sum(a.overdue_amount for a in shown), PRECISION)
	exceptions = sum(1 for a in shown if a.exception)
	return [
		{"value": len(shown), "label": _("Amortized Invoices"), "datatype": "Int", "indicator": "Blue"},
		{
			"value": flt(sum(a.base for a in shown), PRECISION),
			"label": _("Total Amortizable"),
			"datatype": "Currency",
			"currency": currency,
			"indicator": "Blue",
		},
		{
			"value": flt(sum(a.charge for a in shown), PRECISION),
			"label": _("Charge for Period"),
			"datatype": "Currency",
			"currency": currency,
			"indicator": "Orange",
		},
		{
			"value": flt(sum(a.closing for a in shown), PRECISION),
			"label": _("Closing Prepayment Balance"),
			"datatype": "Currency",
			"currency": currency,
			"indicator": "Green",
		},
		{
			"value": overdue,
			"label": _("Overdue - Not Posted"),
			"datatype": "Currency",
			"currency": currency,
			"indicator": "Red" if overdue > TOL else "Green",
		},
		{
			"value": exceptions,
			"label": _("Invoices with Exceptions"),
			"datatype": "Int",
			"indicator": "Red" if exceptions else "Green",
		},
	]


def get_message(shown, filters):
	basis = (
		_("Posted status traced to submitted Journal Entries")
		if cint(filters.trace_je)
		else _("Posted status per the invoice's Next Schedule pointer")
	)
	exceptions = sum(1 for a in shown if a.exception)
	parts = [
		_("As on {0}").format(formatdate(today())),
		_("Balances on schedule basis"),
		basis,
		_("Overdue = not posted and dated before today"),
	]
	html = f"<div style='font-size:12px;color:var(--text-muted)'>{' &nbsp;|&nbsp; '.join(parts)}</div>"
	if exceptions:
		html += (
			"<div style='font-size:12px;margin-top:4px;color:var(--red-600);font-weight:600'>"
			+ _("{0} invoice(s) with audit exceptions - see Audit Flags column.").format(exceptions)
			+ "</div>"
		)
	return html


# --------------------------------------------------------------------------
# Formatted Excel export  (called from the "Formatted Excel" button in the .js)
# --------------------------------------------------------------------------
@frappe.whitelist()
def export_excel(filters=None):
	frappe.has_permission("Purchase Invoice", "read", throw=True)

	if isinstance(filters, str):
		filters = frappe.parse_json(filters)
	filters = frappe._dict(filters or {})

	columns, data, _message, chart, cards, _skip = execute(filters)
	if not data:
		frappe.throw(_("Nothing to export for the selected filters."))

	from .excel_export import build_workbook

	view = filters.view or VIEW_DETAIL
	currency = frappe.get_cached_value("Company", filters.company, "default_currency")
	content = build_workbook(filters, view, columns, data, chart, cards, currency)

	frappe.response["filename"] = "Amortization_Schedule_{}_{}.xlsx".format(view.replace(" ", "_"), today())
	frappe.response["filecontent"] = content
	frappe.response["type"] = "binary"
