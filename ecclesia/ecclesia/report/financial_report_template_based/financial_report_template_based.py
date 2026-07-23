# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt
"""
Financial Report — Template-Based Dynamic Reporting System
===========================================================
Supports P&L, Balance Sheet, Cash Flow and any custom layout.

KEY DESIGN DECISIONS
────────────────────
1. Report Type awareness
   • P&L / Cash Flow  → period movement  (GL entries within the date window)
   • Balance Sheet    → accumulated balance (GL entries from inception up to
                        the closing date of the period — "as at" balance)

2. Balance method
   get_period_movement() — SUM of GL entries between from_date and to_date
   get_closing_balance() — SUM of ALL GL entries up to and including to_date

3. Retained Earnings
   Special line_type "Retained Earnings" accumulates net profit from all prior
   years plus the current year's YTD profit.
   Formula: RE(year N) = Σ Net_Profit(year 1..N-1) + Net_Profit_YTD(year N)
   The line references a line_code (e.g. NET_PROFIT) to identify which
   calculated line holds net profit.

4. Formula token safety
   Tokens replaced with word-boundary regex — 'GP' never corrupts 'GROSS_PROFIT'.

5. Header / Blank rows
   All numeric column keys are set to None so Frappe renders blank cells,
   not 0.00 or undefined.

6. Cutoff Date for Balance Sheet
   Supports partial current period reporting up to a cutoff date.
   Past periods always show full period data.
"""

import calendar
import re

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate, formatdate

_BALANCE_SHEET_TYPES = {"Balance Sheet"}

# Sentinel: marks a column value as "blank" for Header/Blank rows
_BLANK = None


# ═════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════════

def execute(filters=None):
    filters = filters or {}

    template_name = filters.get("template")
    if not template_name:
        frappe.throw(_("Please select a Financial Report Template."))

    template = frappe.get_doc("Financial Report Template", template_name)
    if not template.is_active:
        frappe.throw(_("The selected template is not active."))

    company = filters.get("company")
    if not company:
        frappe.throw(_("Please select a Company."))

    year          = int(filters.get("year") or getdate(nowdate()).year)
    frequency     = filters.get("frequency") or "Monthly"
    current_month = getdate(nowdate()).month
    is_bs         = template.report_type in _BALANCE_SHEET_TYPES
    show_budget   = bool(filters.get("show_budget")) and bool(template.enable_budget_comparison)
    budget_plan   = filters.get("budget_plan") if show_budget else None
    
    # Get cutoff date settings (only relevant for Balance Sheet)
    cutoff_mode = filters.get("cutoff_mode", "Today (Partial Current Period)")
    custom_cutoff_date = filters.get("custom_cutoff_date")
    cutoff_date = _get_cutoff_date(cutoff_mode, year, current_month, custom_cutoff_date)

    if template.use_column_definition:
        columns = _build_custom_columns(template)
        data    = _build_custom_data(
            template, company, year, current_month, budget_plan, is_bs, cutoff_date, cutoff_mode
        )
    else:
        periods = _get_periods_with_flags(frequency, current_month, year, cutoff_date, is_bs, cutoff_mode)
        columns = _build_standard_columns(periods, template, show_budget)
        data    = _build_standard_data(
            template, periods, company, year, current_month,
            show_budget, budget_plan, is_bs, cutoff_date, cutoff_mode
        )

    report_title = template.report_title or template.template_name
    return columns, data, report_title, None, None


# ═════════════════════════════════════════════════════════════════════════════
# CUTOFF DATE HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _get_cutoff_date(cutoff_mode, year, current_month, custom_cutoff_date=None):
    """
    Determine the cutoff date based on filter settings.
    Returns a date object.
    """
    if cutoff_mode == "Custom Date" and custom_cutoff_date:
        return getdate(custom_cutoff_date)
    
    if cutoff_mode == "End of Period (Full Periods)":
        # Return the last day of current month
        last_day = calendar.monthrange(year, current_month)[1]
        return getdate(f"{year}-{current_month:02d}-{last_day}")
    
    # Default: Today (Partial Current Period)
    return getdate(nowdate())


def _is_current_period(year, month, cutoff_date):
    """
    Determine if a given period (year, month) is the current period
    that contains the cutoff date.
    """
    cutoff_year = cutoff_date.year
    cutoff_month = cutoff_date.month
    
    return (year == cutoff_year and month == cutoff_month)


def _get_period_end_date(year, month, is_current, cutoff_date, cutoff_mode):
    """
    Get the end date for a period.
    - If it's the current period and cutoff mode is partial: return cutoff_date
    - Otherwise: return last day of the month
    """
    if is_current and cutoff_mode != "End of Period (Full Periods)":
        return cutoff_date
    else:
        last_day = calendar.monthrange(year, month)[1]
        return getdate(f"{year}-{month:02d}-{last_day}")


def _get_period_start_date(year, month):
    """Get the start date for a period."""
    return getdate(f"{year}-{month:02d}-01")


def _get_balance_with_cutoff(accounts, company, year, month, sign, is_bs, 
                               cutoff_date, cutoff_mode, is_current_period):
    """
    Get balance for a period, respecting cutoff date for current period.
    For P&L reports, always use full period (cutoff doesn't apply).
    """
    if not is_bs:
        # P&L: Always use full period movement
        return get_period_movement(
            accounts, company, 
            _month_start(year, month), 
            _month_end(year, month), 
            sign
        )
    
    # Balance Sheet: respect cutoff
    end_date = _get_period_end_date(year, month, is_current_period, cutoff_date, cutoff_mode)
    return get_closing_balance(accounts, company, end_date, sign)


# ═════════════════════════════════════════════════════════════════════════════
# PERIOD HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _get_periods_with_flags(frequency, current_month, year, cutoff_date, is_bs, cutoff_mode):
    """
    Returns list of (label, months, is_current) where is_current indicates
    if this period contains the cutoff date.
    For P&L reports, is_current is always False (no partial periods).
    """
    periods = []
    
    # For P&L, we never use partial periods
    if not is_bs:
        cutoff_mode = "End of Period (Full Periods)"
    
    if frequency == "Monthly":
        for m in range(1, current_month + 1):
            is_current = _is_current_period(year, m, cutoff_date) if is_bs else False
            periods.append((formatdate(f"{year}-{m:02d}-01", "MMM"), [m], is_current))
    
    elif frequency == "Half-Yearly":
        h1_months = list(range(1, 7))
        h2_months = list(range(7, 13))
        cutoff_month = cutoff_date.month if is_bs else 1
        is_h1_current = (cutoff_date.year == year and cutoff_month in h1_months) if is_bs else False
        is_h2_current = (cutoff_date.year == year and cutoff_month in h2_months) if is_bs else False
        periods = [
            ("H1", h1_months, is_h1_current),
            ("H2", h2_months, is_h2_current),
        ]
        # Filter to only show periods up to current month
        if current_month < 7:
            periods = periods[:1]
    
    else:  # Quarterly
        quarters = [
            ("Q1", [1,2,3], (_is_current_period(year, 1, cutoff_date) or 
                             _is_current_period(year, 2, cutoff_date) or 
                             _is_current_period(year, 3, cutoff_date)) if is_bs else False),
            ("Q2", [4,5,6], (_is_current_period(year, 4, cutoff_date) or 
                             _is_current_period(year, 5, cutoff_date) or 
                             _is_current_period(year, 6, cutoff_date)) if is_bs else False),
            ("Q3", [7,8,9], (_is_current_period(year, 7, cutoff_date) or 
                             _is_current_period(year, 8, cutoff_date) or 
                             _is_current_period(year, 9, cutoff_date)) if is_bs else False),
            ("Q4", [10,11,12], (_is_current_period(year, 10, cutoff_date) or 
                                _is_current_period(year, 11, cutoff_date) or 
                                _is_current_period(year, 12, cutoff_date)) if is_bs else False),
        ]
        periods = [q for q in quarters if q[1][0] <= current_month]
    
    return periods


def _get_periods(frequency, current_month, year):
    """Legacy function for backward compatibility"""
    if frequency == "Monthly":
        return [
            (formatdate(f"{year}-{m:02d}-01", "MMM"), [m])
            for m in range(1, current_month + 1)
        ]
    if frequency == "Half-Yearly":
        return [("H1", list(range(1, 7))), ("H2", list(range(7, 13)))]
    return [
        ("Q1", [1,2,3]), ("Q2", [4,5,6]),
        ("Q3", [7,8,9]), ("Q4", [10,11,12]),
    ]


def _month_end(year, month):
    last = calendar.monthrange(year, month)[1]
    return f"{year}-{month:02d}-{last:02d}"


def _month_start(year, month):
    return f"{year}-{month:02d}-01"


# ═════════════════════════════════════════════════════════════════════════════
# GL BALANCE FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════

_GL_MOVEMENT_SQL = """
    SELECT COALESCE(SUM(
        CASE
            WHEN acc.root_type IN ('Income','Liability','Equity')
            THEN gle.credit - gle.debit
            ELSE gle.debit - gle.credit
        END
    ), 0) AS balance
    FROM `tabGL Entry` gle
    INNER JOIN `tabAccount` acc ON gle.account = acc.name
    WHERE gle.account IN %(accounts)s
      AND gle.company   = %(company)s
      AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
      AND gle.is_cancelled = 0
"""

_GL_CLOSING_SQL = """
    SELECT COALESCE(SUM(
        CASE
            WHEN acc.root_type IN ('Income','Liability','Equity')
            THEN gle.credit - gle.debit
            ELSE gle.debit - gle.credit
        END
    ), 0) AS balance
    FROM `tabGL Entry` gle
    INNER JOIN `tabAccount` acc ON gle.account = acc.name
    WHERE gle.account IN %(accounts)s
      AND gle.company   = %(company)s
      AND gle.posting_date <= %(as_at_date)s
      AND gle.is_cancelled = 0
"""


def get_period_movement(accounts, company, from_date, to_date, sign=1):
    """Period movement — for P&L and Cash Flow lines."""
    if not accounts:
        return 0.0
    r = frappe.db.sql(
        _GL_MOVEMENT_SQL,
        {"accounts": accounts, "company": company,
         "from_date": from_date, "to_date": to_date},
        as_dict=True,
    )
    return flt(r[0]["balance"]) * sign if r else 0.0


def get_closing_balance(accounts, company, as_at_date, sign=1):
    """Accumulated closing balance up to as_at_date — for Balance Sheet lines."""
    if not accounts:
        return 0.0
    # Ensure as_at_date is a string in YYYY-MM-DD format
    if hasattr(as_at_date, 'strftime'):
        as_at_date = as_at_date.strftime('%Y-%m-%d')
    r = frappe.db.sql(
        _GL_CLOSING_SQL,
        {"accounts": accounts, "company": company, "as_at_date": as_at_date},
        as_dict=True,
    )
    return flt(r[0]["balance"]) * sign if r else 0.0


def _get_balance(accounts, company, year, month, sign, is_bs):
    if is_bs:
        return get_closing_balance(accounts, company, _month_end(year, month), sign)
    return get_period_movement(
        accounts, company, _month_start(year, month), _month_end(year, month), sign
    )


# ═════════════════════════════════════════════════════════════════════════════
# RETAINED EARNINGS — ACCUMULATED NET PROFIT ACROSS ALL PERIODS
# ═════════════════════════════════════════════════════════════════════════════

def _get_net_profit_accumulated(company, as_at_date):
    """
    Get accumulated net profit (Income - Expense) from inception up to as_at_date.
    This is used for Retained Earnings calculation.
    """
    # Ensure as_at_date is a string
    if hasattr(as_at_date, 'strftime'):
        as_at_date = as_at_date.strftime('%Y-%m-%d')
    
    result = frappe.db.sql("""
        SELECT
            COALESCE(SUM(
                CASE WHEN acc.root_type = 'Income'
                THEN gle.credit - gle.debit
                ELSE 0 END
            ), 0) AS total_income,
            COALESCE(SUM(
                CASE WHEN acc.root_type = 'Expense'
                THEN gle.debit - gle.credit
                ELSE 0 END
            ), 0) AS total_expense
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE acc.root_type IN ('Income', 'Expense')
          AND gle.company = %(company)s
          AND gle.posting_date <= %(as_at_date)s
          AND gle.is_cancelled = 0
    """, {"company": company, "as_at_date": as_at_date}, as_dict=True)
    
    if result:
        return flt(result[0]["total_income"]) - flt(result[0]["total_expense"])
    return 0.0


def _get_retained_earnings_for_period_with_cutoff(line, company, year, end_date, 
                                                   line_values, cutoff_mode):
    """
    Compute retained earnings as at end_date.
    """
    net_profit_code = getattr(line, "net_profit_line_code", None) or \
                      getattr(line, "calculation_formula", None)

    accounts = get_accounts_for_line(line, company)

    # If actual RE accounts are mapped, use their closing balance
    if accounts:
        return get_closing_balance(accounts, company, end_date, _sign(line))

    # If formula references another line's computed net profit
    if net_profit_code and net_profit_code in line_values:
        # Use the referenced line's YTD value
        return line_values.get(net_profit_code, {}).get("ytd", 0.0)

    # Otherwise, accumulate net profit from all P&L accounts
    return _get_net_profit_accumulated(company, end_date)


# ═════════════════════════════════════════════════════════════════════════════
# BUDGET HELPER
# ═════════════════════════════════════════════════════════════════════════════

_MONTH_FIELDS = ["jan","feb","mar","apr","may","jun",
                 "jul","aug","sep","oct","nov","dec"]


def _get_month_budget(accounts, budget_plan, month, sign=1):
    if not accounts or not budget_plan:
        return 0.0
    try:
        budget = frappe.get_doc("Budget Plan", budget_plan)
    except Exception:
        return 0.0
    field = _MONTH_FIELDS[month - 1]
    total = sum(
        flt(bl.get(field, 0))
        for bl in budget.monthly_budget
        if bl.gl_account in accounts
    )
    return total * sign


# ═════════════════════════════════════════════════════════════════════════════
# ACCOUNT RESOLUTION
# ═════════════════════════════════════════════════════════════════════════════

def get_accounts_for_line(line, company):
    method = line.account_mapping_method
    if method == "Account Range":
        return _accounts_by_range(line.account_from, line.account_to, company)
    if method == "Account Numbers Pattern":
        return _accounts_by_pattern(line.account_number_pattern, company)
    if method == "Specific Accounts":
        return _accounts_by_list(line.specific_accounts, company)
    if method == "Financial Reporting Group":
        return _accounts_by_group(line.financial_reporting_group, company)
    if method == "Root Type":
        return _accounts_by_root_type(line.root_type_filter, company)
    return []


def _extract_account_number(account_name):
    if not account_name:
        return None
    num = frappe.db.get_value("Account", account_name, "account_number")
    if num:
        try:
            return int(num)
        except (ValueError, TypeError):
            pass
    m = re.match(r"^(\d+)", str(account_name))
    if m:
        try:
            return int(m.group(1))
        except (ValueError, TypeError):
            pass
    return None


def _accounts_by_range(account_from, account_to, company):
    if not account_from or not account_to:
        return []
    from_num = _extract_account_number(account_from)
    to_num   = _extract_account_number(account_to)
    if from_num is None or to_num is None:
        return []
    all_accs = frappe.get_all("Account",
        filters={"company": company, "is_group": 0}, fields=["name"])
    return [a.name for a in all_accs
            if (n := _extract_account_number(a.name)) is not None
            and from_num <= n <= to_num]


def _accounts_by_pattern(pattern, company):
    if not pattern:
        return []
    m = re.match(r"^(\d+)-(\d+)$", pattern.strip())
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        all_accs = frappe.get_all("Account",
            filters={"company": company, "is_group": 0}, fields=["name"])
        return [a.name for a in all_accs
                if (n := _extract_account_number(a.name)) is not None
                and lo <= n <= hi]
    accs = frappe.get_all("Account",
        filters={"company": company, "is_group": 0,
                 "account_number": ["like", pattern]}, fields=["name"])
    return [a.name for a in accs]


def _accounts_by_list(account_list, company):
    if not account_list:
        return []
    names = [a.strip() for a in account_list.split(",") if a.strip()]
    valid = frappe.get_all("Account",
        filters={"company": company, "name": ["in", names], "is_group": 0},
        fields=["name"])
    return [a.name for a in valid]


def _accounts_by_group(group_name, company):
    if not group_name:
        return []
    accs = frappe.get_all("Account",
        filters={"company": company,
                 "custom_financial_reporting_group": group_name, "is_group": 0},
        fields=["name"])
    return [a.name for a in accs]


def _accounts_by_root_type(root_type, company):
    if not root_type:
        return []
    accs = frappe.get_all("Account",
        filters={"company": company, "root_type": root_type, "is_group": 0},
        fields=["name"])
    return [a.name for a in accs]


# ═════════════════════════════════════════════════════════════════════════════
# FORMULA ENGINE
# ═════════════════════════════════════════════════════════════════════════════

def _safe_replace(formula, token, value):
    """Word-boundary safe token replacement — 'GP' never mangles 'GROSS_PROFIT'."""
    return re.sub(r"\b" + re.escape(token) + r"\b", str(flt(value)), formula)


def _evaluate_formula(formula, line_values, period_key, data_key="periods"):
    """
    Evaluate a row formula for one period column.

    line_values structure:
      { "LINE_CODE": { "periods": {"jan": 1000, "feb": 2000, ...},
                       "periods_ly": {...},
                       "periods_bud": {...},
                       "ytd": 3000,
                       "ytd_ly": 2500,
                       "ytd_bud": 3500 } }

    data_key selects which sub-dict to read:
      "periods"     → current year per-period actuals
      "periods_ly"  → prior year per-period actuals
      "periods_bud" → budget per-period
    """
    if not formula:
        return 0.0

    expr   = formula.strip()
    tokens = re.findall(r"\b[A-Z_][A-Z0-9_]*\b", expr)

    # Replace longest tokens first to avoid partial-token corruption
    for token in sorted(tokens, key=len, reverse=True):
        if token in line_values:
            sub_dict = line_values[token].get(data_key, {})
            val      = sub_dict.get(period_key, 0) if isinstance(sub_dict, dict) else 0
            expr     = _safe_replace(expr, token, val)

    try:
        return flt(eval(expr))   # noqa: S307 — formula is admin-configured
    except Exception:
        return 0.0


def _evaluate_formula_ytd(formula, line_values, ytd_key="ytd"):
    """Evaluate a row formula for the YTD / Total column."""
    if not formula:
        return 0.0

    expr   = formula.strip()
    tokens = re.findall(r"\b[A-Z_][A-Z0-9_]*\b", expr)

    for token in sorted(tokens, key=len, reverse=True):
        if token in line_values:
            val  = line_values[token].get(ytd_key, 0)
            expr = _safe_replace(expr, token, val)

    try:
        return flt(eval(expr))   # noqa: S307
    except Exception:
        return 0.0


def _variance_pct(current, previous):
    if not previous:
        return None
    return round(((current - previous) / abs(previous)) * 100, 2)


# ═════════════════════════════════════════════════════════════════════════════
# ROW FORMATTING
# ═════════════════════════════════════════════════════════════════════════════

def _format_label(label, indent_level, is_bold):
    indent = "&nbsp;&nbsp;&nbsp;&nbsp;" * int(indent_level or 0)
    # Cast is_bold — may arrive as string "0"/"1" from CSV import
    if bool(int(is_bold or 0)):
        return f'{indent}<b>{label}</b>'
    return f"{indent}{label}"


def _row_style(line, template):
    # FIX 2: Fields from CSV import arrive as strings ("0", "1", "").
    # Cast them properly before use — "0" is truthy as a string but falsy as int.
    def _bool(attr):
        return bool(int(getattr(line, attr, 0) or 0))

    is_total    = _bool("is_total_row")
    is_subtotal = _bool("is_subtotal_row")
    is_bold_row = _bool("is_bold")

    parts = []
    row_color = getattr(line, "row_color", None) or ""
    if row_color.strip():
        parts.append(f"background-color:{row_color.strip()}")
    elif is_total:
        clr = (template.excel_total_row_color or "#E7E6E6").strip()
        parts.append(f"background-color:{clr}")
    elif is_subtotal:
        clr = (template.excel_subtotal_color or "#F2F2F2").strip()
        parts.append(f"background-color:{clr}")

    if is_bold_row or is_total or is_subtotal:
        parts.append("font-weight:bold")

    border_map = {
        "Top Border":              ["border-top:1px solid #000"],
        "Bottom Border":           ["border-bottom:1px solid #000"],
        "Top and Bottom":          ["border-top:1px solid #000", "border-bottom:1px solid #000"],
        "Top Single Bottom Double":["border-top:1px solid #000", "border-bottom:3px double #000"],
        "Top and Bottom Double":   ["border-top:3px double #000", "border-bottom:3px double #000"],
    }
    border = (getattr(line, "border_style", None) or "").strip()
    parts.extend(border_map.get(border, []))
    return ";".join(parts) + ";" if parts else None


def _sign(line):
    v = str(getattr(line, "sign_multiplier", "1") or "1").strip()
    # Handle CSV import where value may be "" or "None"
    if v in ("", "None", "none"):
        return 1
    try:
        return int(v)
    except (ValueError, TypeError):
        return 1


def _blank_numeric_row(col_fieldnames):
    """Return a dict with None for every numeric column — renders as blank cell."""
    return {fn: None for fn in col_fieldnames}


# ═════════════════════════════════════════════════════════════════════════════
# STANDARD (FREQUENCY-BASED) REPORT
# ═════════════════════════════════════════════════════════════════════════════

def _build_standard_columns(periods, template, show_budget):
    cols = [{"label": "Account", "fieldname": "account_name",
             "fieldtype": "Data", "width": 300}]
    for lbl, _, _ in periods:
        key = lbl.lower()
        cols.append({"label": lbl, "fieldname": key,
                     "fieldtype": "Currency", "width": 120})
        if template.show_comparison:
            cols += [
                {"label": f"{lbl} PY",   "fieldname": f"{key}_ly",  "fieldtype": "Currency", "width": 120},
                {"label": f"{lbl} Var%", "fieldname": f"{key}_var", "fieldtype": "Percent",  "width": 90},
            ]
        if show_budget:
            cols += [
                {"label": f"{lbl} Bud",  "fieldname": f"{key}_bud",     "fieldtype": "Currency", "width": 120},
                {"label": f"{lbl} Bud%", "fieldname": f"{key}_bud_var", "fieldtype": "Percent",  "width": 90},
            ]
        # visual spacer
        cols.append({"label": "", "fieldname": f"{key}_sp", "fieldtype": "Data", "width": 12})

    cols.append({"label": "YTD / Total", "fieldname": "ytd",
                 "fieldtype": "Currency", "width": 140})
    if template.show_comparison:
        cols += [
            {"label": "PY YTD",   "fieldname": "ytd_ly",  "fieldtype": "Currency", "width": 130},
            {"label": "YTD Var%", "fieldname": "ytd_var", "fieldtype": "Percent",  "width": 100},
        ]
    if show_budget:
        cols += [
            {"label": "YTD Bud",  "fieldname": "ytd_bud",     "fieldtype": "Currency", "width": 130},
            {"label": "Bud Var%", "fieldname": "ytd_bud_var", "fieldtype": "Percent",  "width": 100},
        ]
    return cols


def _standard_numeric_fieldnames(periods, template, show_budget):
    """Return every numeric fieldname used in standard columns."""
    fns = []
    for lbl, _, _ in periods:
        key = lbl.lower()
        fns.append(key)
        if template.show_comparison:
            fns += [f"{key}_ly", f"{key}_var"]
        if show_budget:
            fns += [f"{key}_bud", f"{key}_bud_var"]
    fns.append("ytd")
    if template.show_comparison:
        fns += ["ytd_ly", "ytd_var"]
    if show_budget:
        fns += ["ytd_bud", "ytd_bud_var"]
    return fns


def _build_standard_data(template, periods, company, year, current_month,
                          show_budget, budget_plan, is_bs, cutoff_date, cutoff_mode):
    data        = []
    line_values = {}
    numeric_fns = _standard_numeric_fieldnames(periods, template, show_budget)
    auto_insert = getattr(template, "auto_insert_retained_earnings", False)
    re_inserted = False

    for line in sorted(template.report_lines, key=lambda x: x.line_number):
        lt = line.line_type

        # ── Blank line ────────────────────────────────────────────────────────
        if lt == "Blank Line":
            row = {"account_name": ""}
            row.update(_blank_numeric_row(numeric_fns))
            data.append(row)
            continue

        # ── Header ────────────────────────────────────────────────────────────
        if lt == "Header":
            row = {"account_name": _format_label(line.line_label, line.indent_level, True)}
            row.update(_blank_numeric_row(numeric_fns))
            style = _row_style(line, template)
            if style:
                row["_style"] = style
            data.append(row)
            continue

        # ── Account Aggregate ─────────────────────────────────────────────────
        if lt == "Account Aggregate":
            row, vals = _standard_aggregate_with_cutoff(
                line, periods, company, year, current_month,
                show_budget, budget_plan, template, is_bs, cutoff_date, cutoff_mode
            )
            if line.line_code:
                line_values[line.line_code] = vals
            if row is None:
                continue
            data.append(row)

        # ── Calculated ────────────────────────────────────────────────────────
        elif lt == "Calculated":
            row, vals = _standard_calculated(
                line, periods, line_values, template, show_budget
            )
            if line.line_code:
                line_values[line.line_code] = vals
            data.append(row)

        # ── Retained Earnings (explicit template row) ─────────────────────────
        elif lt == "Retained Earnings":
            row, vals = _standard_retained_earnings_with_cutoff(
                line, periods, company, year, current_month,
                line_values, template, show_budget, budget_plan, cutoff_date, cutoff_mode
            )
            if line.line_code:
                line_values[line.line_code] = vals
            data.append(row)

    # Auto-insert Retained Earnings after processing all lines (if enabled)
    if auto_insert and not re_inserted:
        has_re_row = any(l.line_type == "Retained Earnings" for l in template.report_lines)
        if not has_re_row:
            re_row, re_vals = _make_auto_re_row_with_cutoff(
                periods, company, year, current_month,
                template, show_budget, numeric_fns,
                indent_level=1, cutoff_date=cutoff_date, cutoff_mode=cutoff_mode
            )
            line_values["_AUTO_RE"] = re_vals
            data.append(re_row)

    return data


def _standard_aggregate_with_cutoff(line, periods, company, year, current_month,
                                     show_budget, budget_plan, template, is_bs, 
                                     cutoff_date, cutoff_mode):
    accounts = get_accounts_for_line(line, company)
    if not accounts:
        if not template.show_zero_values:
            zero_pv = {}
            for lbl, _, _ in periods:
                zero_pv[lbl.lower()] = 0.0
            zero_vals = {"periods": zero_pv, "periods_ly": dict(zero_pv),
                         "periods_bud": dict(zero_pv),
                         "ytd": 0.0, "ytd_ly": 0.0, "ytd_bud": 0.0}
            return None, zero_vals

    sign = _sign(line)
    row = {"account_name": _format_label(line.line_label, line.indent_level, int(line.is_bold or 0))}
    style = _row_style(line, template)
    if style:
        row["_style"] = style

    pv = {}; pv_ly = {}; pv_bud = {}
    ytd_sum = 0.0

    for lbl, months, is_current in periods:
        key = lbl.lower()
        period_act = period_ly = period_bud = 0.0

        for m in months:
            # Current year with cutoff awareness
            act = _get_balance_with_cutoff(accounts, company, year, m, sign, is_bs, 
                                            cutoff_date, cutoff_mode, is_current)
            
            # Prior year (full period)
            ly = _get_balance(accounts, company, year - 1, m, sign, is_bs) \
                 if template.show_comparison else 0.0
            
            bud = _get_month_budget(accounts, budget_plan, m, sign) \
                  if show_budget else 0.0

            if is_bs:
                period_act = act
                period_ly = ly
                period_bud = bud
            else:
                period_act += act
                period_ly += ly
                period_bud += bud

        pv[key] = period_act
        pv_ly[key] = period_ly
        pv_bud[key] = period_bud

        row[key] = period_act if (period_act != 0 or template.show_zero_values) else None
        if template.show_comparison:
            row[f"{key}_ly"] = period_ly if (period_ly != 0 or template.show_zero_values) else None
            row[f"{key}_var"] = _variance_pct(period_act, period_ly)
        if show_budget:
            row[f"{key}_bud"] = period_bud if (period_bud != 0 or template.show_zero_values) else None
            row[f"{key}_bud_var"] = _variance_pct(period_act, period_bud)

        ytd_sum += period_act

    # YTD calculation
    if is_bs:
        ytd = get_closing_balance(accounts, company, cutoff_date, sign)
        if template.show_comparison:
            ly_cutoff = getdate(f"{year - 1}-{cutoff_date.month:02d}-{cutoff_date.day}")
            ytd_ly = get_closing_balance(accounts, company, ly_cutoff, sign)
        else:
            ytd_ly = 0.0
    else:
        ytd = ytd_sum
        ytd_ly = 0.0

    row["ytd"] = ytd if (ytd != 0 or template.show_zero_values) else None
    if template.show_comparison:
        row["ytd_ly"] = ytd_ly if (ytd_ly != 0 or template.show_zero_values) else None
        row["ytd_var"] = _variance_pct(ytd, ytd_ly)
    if show_budget:
        row["ytd_bud"] = None
        row["ytd_bud_var"] = None

    vals = {"periods": pv, "periods_ly": pv_ly, "periods_bud": pv_bud,
            "ytd": ytd, "ytd_ly": ytd_ly, "ytd_bud": 0.0}
    return row, vals


def _standard_calculated(line, periods, line_values, template, show_budget):
    """
    Process a Calculated line using a formula that references other line codes.
    """
    row   = {"account_name": _format_label(line.line_label, line.indent_level, int(line.is_bold or 0))}
    style = _row_style(line, template)
    if style:
        row["_style"] = style

    if not line.calculation_formula:
        return row, {}

    formula = line.calculation_formula.strip()
    pv = {}; pv_ly = {}; pv_bud = {}
    ytd = ytd_ly = ytd_bud = 0.0

    for lbl, _, _ in periods:
        key = lbl.lower()

        v     = _evaluate_formula(formula, line_values, key, "periods")
        v_ly  = _evaluate_formula(formula, line_values, key, "periods_ly")  \
                if template.show_comparison else 0.0
        v_bud = _evaluate_formula(formula, line_values, key, "periods_bud") \
                if show_budget else 0.0

        pv[key]     = v
        pv_ly[key]  = v_ly
        pv_bud[key] = v_bud

        row[key] = v if (v != 0 or template.show_zero_values) else None
        if template.show_comparison:
            row[f"{key}_ly"]  = v_ly if (v_ly != 0 or template.show_zero_values) else None
            row[f"{key}_var"] = _variance_pct(v, v_ly)
        if show_budget:
            row[f"{key}_bud"]     = v_bud if (v_bud != 0 or template.show_zero_values) else None
            row[f"{key}_bud_var"] = _variance_pct(v, v_bud)

    ytd    = _evaluate_formula_ytd(formula, line_values, "ytd")
    ytd_ly = _evaluate_formula_ytd(formula, line_values, "ytd_ly") \
             if template.show_comparison else 0.0
    ytd_bud = _evaluate_formula_ytd(formula, line_values, "ytd_bud") \
              if show_budget else 0.0

    row["ytd"] = ytd if (ytd != 0 or template.show_zero_values) else None
    if template.show_comparison:
        row["ytd_ly"]  = ytd_ly if (ytd_ly != 0 or template.show_zero_values) else None
        row["ytd_var"] = _variance_pct(ytd, ytd_ly)
    if show_budget:
        row["ytd_bud"]     = ytd_bud if (ytd_bud != 0 or template.show_zero_values) else None
        row["ytd_bud_var"] = _variance_pct(ytd, ytd_bud)

    vals = {"periods": pv, "periods_ly": pv_ly, "periods_bud": pv_bud,
            "ytd": ytd, "ytd_ly": ytd_ly, "ytd_bud": ytd_bud}
    return row, vals


def _standard_retained_earnings_with_cutoff(line, periods, company, year, current_month,
                                              line_values, template, show_budget, budget_plan,
                                              cutoff_date, cutoff_mode):
    """
    Retained Earnings — PRIMARY METHOD: Uses line_type == "Retained Earnings"
    
    The calculation accumulates net profit from inception up to each period end,
    respecting cutoff date for current period.
    """
    row   = {"account_name": _format_label(line.line_label, line.indent_level, int(line.is_bold or 0))}
    style = _row_style(line, template)
    if style:
        row["_style"] = style

    net_profit_code = getattr(line, "net_profit_line_code", None) or \
                      getattr(line, "calculation_formula", None)

    pv = {}; pv_ly = {}
    ytd = ytd_ly = 0.0

    for lbl, months, is_current in periods:
        key       = lbl.lower()
        end_month = months[-1]

        # Determine end date for this period
        if is_current and cutoff_mode != "End of Period (Full Periods)":
            end_date = cutoff_date
        else:
            last_day = calendar.monthrange(year, end_month)[1]
            end_date = getdate(f"{year}-{end_month:02d}-{last_day}")

        # Get RE value
        if net_profit_code and net_profit_code in line_values:
            val = line_values.get(net_profit_code, {}).get("ytd", 0.0)
        else:
            val = _get_net_profit_accumulated(company, end_date)
        
        pv[key] = val
        row[key] = val if (val != 0 or template.show_zero_values) else None

        if template.show_comparison:
            # Prior year: use same day-of-month for current period, full for others
            if is_current and cutoff_mode != "End of Period (Full Periods)":
                ly_end_date = getdate(f"{year - 1}-{cutoff_date.month:02d}-{cutoff_date.day}")
            else:
                last_day_ly = calendar.monthrange(year - 1, end_month)[1]
                ly_end_date = getdate(f"{year - 1}-{end_month:02d}-{last_day_ly}")
            
            ly_val = _get_net_profit_accumulated(company, ly_end_date)
            pv_ly[key] = ly_val
            row[f"{key}_ly"] = ly_val if (ly_val != 0 or template.show_zero_values) else None
            row[f"{key}_var"] = _variance_pct(val, ly_val)

        if show_budget:
            row[f"{key}_bud"] = None
            row[f"{key}_bud_var"] = None

    # YTD = accumulated up to cutoff_date
    if net_profit_code and net_profit_code in line_values:
        ytd = line_values.get(net_profit_code, {}).get("ytd", 0.0)
        ytd_ly = line_values.get(net_profit_code, {}).get("ytd_ly", 0.0) if template.show_comparison else 0.0
    else:
        ytd = _get_net_profit_accumulated(company, cutoff_date)
        if template.show_comparison:
            ly_cutoff = getdate(f"{year - 1}-{cutoff_date.month:02d}-{cutoff_date.day}")
            ytd_ly = _get_net_profit_accumulated(company, ly_cutoff)

    row["ytd"] = ytd if (ytd != 0 or template.show_zero_values) else None
    if template.show_comparison:
        row["ytd_ly"] = ytd_ly if (ytd_ly != 0 or template.show_zero_values) else None
        row["ytd_var"] = _variance_pct(ytd, ytd_ly)
    if show_budget:
        row["ytd_bud"] = None
        row["ytd_bud_var"] = None

    vals = {"periods": pv, "periods_ly": pv_ly, "periods_bud": {},
            "ytd": ytd, "ytd_ly": ytd_ly, "ytd_bud": 0.0}
    return row, vals


def _make_auto_re_row_with_cutoff(periods, company, year, current_month, template,
                                   show_budget, numeric_fns, indent_level=1, 
                                   cutoff_date=None, cutoff_mode=None):
    """
    Build a Retained Earnings data row automatically — used when
    auto_insert_retained_earnings = 1 on the template AND no explicit
    Retained Earnings row exists in the template.
    """
    indent  = "&nbsp;&nbsp;&nbsp;&nbsp;" * indent_level
    row     = {"account_name": f"{indent}Retained Earnings"}
    pv      = {}; pv_ly = {}
    
    # Use today as default cutoff if not provided
    if cutoff_date is None:
        cutoff_date = getdate(nowdate())
    if cutoff_mode is None:
        cutoff_mode = "Today (Partial Current Period)"

    for lbl, months, is_current in periods:
        key       = lbl.lower()
        end_month = months[-1]

        if is_current and cutoff_mode != "End of Period (Full Periods)":
            end_date = cutoff_date
        else:
            last_day = calendar.monthrange(year, end_month)[1]
            end_date = getdate(f"{year}-{end_month:02d}-{last_day}")

        val = _get_net_profit_accumulated(company, end_date)
        pv[key]  = val
        row[key] = val if (val != 0 or template.show_zero_values) else None

        if template.show_comparison:
            if is_current and cutoff_mode != "End of Period (Full Periods)":
                ly_end_date = getdate(f"{year - 1}-{cutoff_date.month:02d}-{cutoff_date.day}")
            else:
                last_day_ly = calendar.monthrange(year - 1, end_month)[1]
                ly_end_date = getdate(f"{year - 1}-{end_month:02d}-{last_day_ly}")
            
            ly_val = _get_net_profit_accumulated(company, ly_end_date)
            pv_ly[key] = ly_val
            row[f"{key}_ly"] = ly_val if (ly_val != 0 or template.show_zero_values) else None
            row[f"{key}_var"] = _variance_pct(val, ly_val)

        if show_budget:
            row[f"{key}_bud"] = None
            row[f"{key}_bud_var"] = None

    ytd = _get_net_profit_accumulated(company, cutoff_date)
    row["ytd"] = ytd if (ytd != 0 or template.show_zero_values) else None
    
    if template.show_comparison:
        ly_cutoff = getdate(f"{year - 1}-{cutoff_date.month:02d}-{cutoff_date.day}")
        ytd_ly = _get_net_profit_accumulated(company, ly_cutoff)
        row["ytd_ly"] = ytd_ly if (ytd_ly != 0 or template.show_zero_values) else None
        row["ytd_var"] = _variance_pct(ytd, ytd_ly)
    
    if show_budget:
        row["ytd_bud"] = None
        row["ytd_bud_var"] = None

    vals = {"periods": pv, "periods_ly": pv_ly, "periods_bud": {},
            "ytd": ytd, "ytd_ly": ytd_ly if template.show_comparison else 0.0, "ytd_bud": 0.0}
    return row, vals


# ═════════════════════════════════════════════════════════════════════════════
# CUSTOM COLUMN DEFINITION REPORT
# ═════════════════════════════════════════════════════════════════════════════

def _resolve_col(col_code, base_year, current_month):
    """
    Resolve a column code string to a time-window descriptor dict.
    Returns None if the code is unrecognisable.
    """
    code        = col_code.upper().strip()
    year_offset = 0
    data_source = "actual"

    # Prior-year prefix: -M1, -Q1, -YTD, -Y1
    if code.startswith("-"):
        m = re.match(r"^-Y(\d+)$", code)
        if m:
            return {"year": base_year - int(m.group(1)),
                    "from_month": 1, "to_month": 12, "data_source": "actual"}
        year_offset = -1
        code = code[1:]

    # Budget suffix
    if code.endswith("_BUD"):
        data_source = "budget"
        code = code[:-4]

    actual_year = base_year + year_offset

    # Range: M1:M6, Q1:Q3
    if ":" in code:
        left, right = [c.strip() for c in code.split(":", 1)]
        def _month_of(c):
            if c.startswith("M") and c[1:].isdigit(): return int(c[1:])
            if c.startswith("Q") and c[1:].isdigit(): return (int(c[1:]) - 1) * 3 + 1
            return None
        lm = _month_of(left)
        rm = _month_of(right)
        if lm and rm:
            rm_end = rm + 2 if right.startswith("Q") else rm
            return {"year": actual_year, "from_month": lm, "to_month": rm_end,
                    "data_source": data_source}
        return None

    # M1–M12
    m = re.fullmatch(r"M(\d{1,2})", code)
    if m:
        mn = int(m.group(1))
        if 1 <= mn <= 12:
            return {"year": actual_year, "from_month": mn, "to_month": mn,
                    "data_source": data_source}

    # Q1–Q4
    m = re.fullmatch(r"Q(\d)", code)
    if m:
        q = int(m.group(1))
        if 1 <= q <= 4:
            sm = (q - 1) * 3 + 1
            return {"year": actual_year, "from_month": sm, "to_month": sm + 2,
                    "data_source": data_source}

    # H1–H2
    m = re.fullmatch(r"H([12])", code)
    if m:
        h = int(m.group(1))
        sm = 1 if h == 1 else 7
        return {"year": actual_year, "from_month": sm, "to_month": sm + 5,
                "data_source": data_source}

    # YTD
    if code == "YTD":
        return {"year": actual_year, "from_month": 1, "to_month": current_month,
                "data_source": data_source}

    # FY / Y1
    if code in ("FY", "Y1"):
        return {"year": actual_year, "from_month": 1, "to_month": 12,
                "data_source": data_source}

    return None


def _col_value_with_cutoff(col_def, accounts, company, budget_plan, sign, is_bs, 
                            cutoff_date, cutoff_mode):
    if not accounts or not col_def:
        return 0.0
    ds   = col_def["data_source"]
    year = col_def["year"]
    fm   = col_def["from_month"]
    tm   = col_def["to_month"]

    if ds == "budget":
        return sum(_get_month_budget(accounts, budget_plan, m, sign)
                   for m in range(fm, tm + 1))
    
    if is_bs:
        # Check if this column represents the current period
        cutoff_year = cutoff_date.year
        cutoff_month = cutoff_date.month
        is_current_column = (year == cutoff_year and tm == cutoff_month and fm == cutoff_month)
        
        if is_current_column and cutoff_mode != "End of Period (Full Periods)":
            # Use cutoff date for current period
            return get_closing_balance(accounts, company, cutoff_date, sign)
        else:
            # Use full period end for past periods
            return get_closing_balance(accounts, company, _month_end(year, tm), sign)
    
    # P&L: always use full period
    return get_period_movement(
        accounts, company, _month_start(year, fm), _month_end(year, tm), sign
    )


def _build_custom_columns(template):
    if not template.report_columns:
        frappe.throw(_("No columns defined. Add columns or disable "
                       "'Use Custom Column Definition'."))
    cols = [{"label": "Account", "fieldname": "account_name",
             "fieldtype": "Data", "width": 300}]
    ft_map = {"Currency": "Currency", "Percent": "Percent",
               "Integer": "Int", "Decimal": "Float"}
    for col in sorted(template.report_columns, key=lambda x: x.column_number):
        if col.is_hidden:
            continue
        cols.append({
            "label":     col.column_label or col.column_code,
            "fieldname": f"col_{col.column_number}",
            "fieldtype": ft_map.get(col.number_format, "Currency"),
            "width":     col.column_width or 120,
        })
    return cols


def _custom_numeric_fieldnames(template):
    return [
        f"col_{col.column_number}"
        for col in sorted(template.report_columns, key=lambda x: x.column_number)
        if not col.is_hidden
    ]


def _build_custom_data(template, company, base_year, current_month, budget_plan, is_bs,
                        cutoff_date, cutoff_mode):
    """
    Build data rows for Custom Column Definition mode.

    PRIMARY METHOD for Retained Earnings: Uses line_type == "Retained Earnings"
    to insert RE rows with assignable line_code for formula references.
    """
    data        = []
    line_values = {}
    sorted_cols = sorted(template.report_columns, key=lambda x: x.column_number)
    numeric_fns = _custom_numeric_fieldnames(template)
    auto_insert = getattr(template, "auto_insert_retained_earnings", False)
    has_re_row = False

    for line in sorted(template.report_lines, key=lambda x: x.line_number):
        lt = line.line_type

        # ── Blank ─────────────────────────────────────────────────────────────
        if lt == "Blank Line":
            row = {"account_name": ""}
            row.update(_blank_numeric_row(numeric_fns))
            data.append(row)
            continue

        # ── Header ────────────────────────────────────────────────────────────
        if lt == "Header":
            row = {"account_name": _format_label(line.line_label, line.indent_level, True)}
            row.update(_blank_numeric_row(numeric_fns))
            style = _row_style(line, template)
            if style:
                row["_style"] = style
            data.append(row)
            continue

        # ── All data lines share this base row dict ────────────────────────────
        row   = {"account_name": _format_label(line.line_label, line.indent_level, int(line.is_bold or 0))}
        style = _row_style(line, template)
        if style:
            row["_style"] = style

        col_vals = {}

        # ── Pass 1: data columns based on line type ──────────────────────────
        if lt == "Account Aggregate":
            accounts = get_accounts_for_line(line, company)
            sign = _sign(line)
            for col in sorted_cols:
                if col.is_hidden or col.column_type == "Calculated":
                    continue
                col_key = f"col_{col.column_number}"
                col_def = _resolve_col(col.column_code, base_year, current_month)
                val = _col_value_with_cutoff(col_def, accounts, company, budget_plan, sign, is_bs, 
                                              cutoff_date, cutoff_mode) if accounts else 0.0
                row[col_key]      = val if (val != 0 or template.show_zero_values) else None
                col_vals[col_key] = val
            
            if line.line_code:
                line_values[line.line_code] = col_vals
            if not accounts and not template.show_zero_values:
                continue

        elif lt == "Calculated":
            formula = (line.calculation_formula or "").strip()
            if not formula:
                continue

            for col in sorted_cols:
                if col.is_hidden or col.column_type == "Calculated":
                    continue
                col_key = f"col_{col.column_number}"
                expr   = formula
                tokens = re.findall(r"\b[A-Z_][A-Z0-9_]*\b", expr)
                for tok in sorted(tokens, key=len, reverse=True):
                    if tok in line_values:
                        val = line_values[tok].get(col_key, 0)
                        expr = _safe_replace(expr, tok, val)
                try:
                    val = flt(eval(expr))
                except Exception:
                    val = 0.0
                row[col_key]      = val if (val != 0 or template.show_zero_values) else None
                col_vals[col_key] = val

            if line.line_code:
                line_values[line.line_code] = col_vals

        elif lt == "Retained Earnings":
            has_re_row = True
            net_profit_code = getattr(line, "net_profit_line_code", None) or \
                              getattr(line, "calculation_formula", None)
            
            for col in sorted_cols:
                if col.is_hidden or col.column_type == "Calculated":
                    continue
                col_key = f"col_{col.column_number}"
                col_def = _resolve_col(col.column_code, base_year, current_month)
                
                if col_def:
                    # Check if this is the current period column
                    cutoff_year = cutoff_date.year
                    cutoff_month = cutoff_date.month
                    is_current_column = (col_def["year"] == cutoff_year and 
                                         col_def["to_month"] == cutoff_month and
                                         col_def["from_month"] == cutoff_month)
                    
                    if net_profit_code and net_profit_code in line_values:
                        val = line_values.get(net_profit_code, {}).get(col_key, 0.0)
                    else:
                        if is_current_column and cutoff_mode != "End of Period (Full Periods)":
                            end_date = cutoff_date
                        else:
                            end_date = getdate(_month_end(col_def["year"], col_def["to_month"]))
                        val = _get_net_profit_accumulated(company, end_date)
                else:
                    val = 0.0
                
                row[col_key]      = val if (val != 0 or template.show_zero_values) else None
                col_vals[col_key] = val
            
            if line.line_code:
                line_values[line.line_code] = col_vals

        # ── Pass 2: Calculated columns (same-row column formulas) ─────────────
        code_to_val = {}
        for c2 in sorted_cols:
            if not c2.is_hidden and c2.column_type != "Calculated":
                code_to_val[c2.column_code.upper()] = col_vals.get(f"col_{c2.column_number}", 0)

        for col in sorted_cols:
            if col.is_hidden or col.column_type != "Calculated":
                continue
            col_key = f"col_{col.column_number}"
            if not col.calculation_formula:
                continue

            expr   = col.calculation_formula.strip()
            tokens = re.findall(r"\b[A-Z0-9_:]+\b", expr)

            for tok in sorted(tokens, key=len, reverse=True):
                if tok in code_to_val:
                    expr = _safe_replace(expr, tok, code_to_val[tok])
                elif tok in line_values:
                    val_from_lv = line_values[tok].get(col_key, 0)
                    expr = _safe_replace(expr, tok, val_from_lv)

            try:
                val = flt(eval(expr))
            except Exception:
                val = 0.0

            row[col_key]          = val if (val != 0 or template.show_zero_values) else None
            col_vals[col_key]     = val
            code_to_val[col.column_code.upper()] = val

        if line.line_code:
            line_values[line.line_code] = col_vals

        data.append(row)

    # Auto-insert Retained Earnings if enabled and no explicit RE row exists
    if auto_insert and not has_re_row:
        re_row, re_vals = _make_auto_re_row_custom_with_cutoff(
            sorted_cols, company, base_year, current_month, template,
            numeric_fns, indent_level=1, budget_plan=budget_plan,
            cutoff_date=cutoff_date, cutoff_mode=cutoff_mode
        )
        line_values["_AUTO_RE"] = re_vals
        data.append(re_row)

    return data


def _make_auto_re_row_custom_with_cutoff(sorted_cols, company, base_year, current_month,
                                          template, numeric_fns, indent_level=1, budget_plan=None,
                                          cutoff_date=None, cutoff_mode=None):
    """
    Build a Retained Earnings row for custom-column-definition templates (auto-insert).
    Used only when auto_insert_retained_earnings is enabled AND no explicit RE row exists.
    """
    if cutoff_date is None:
        cutoff_date = getdate(nowdate())
    if cutoff_mode is None:
        cutoff_mode = "Today (Partial Current Period)"
    
    indent = "&nbsp;&nbsp;&nbsp;&nbsp;" * indent_level
    row    = {"account_name": f"{indent}Retained Earnings"}
    row.update({fn: None for fn in numeric_fns})
    col_vals = {}

    for col in sorted_cols:
        if col.is_hidden or col.column_type == "Calculated":
            continue
        col_key = f"col_{col.column_number}"
        col_def = _resolve_col(col.column_code, base_year, current_month)
        if not col_def:
            row[col_key] = None
            col_vals[col_key] = 0.0
            continue
        
        # Check if this is the current period column
        cutoff_year = cutoff_date.year
        cutoff_month = cutoff_date.month
        is_current_column = (col_def["year"] == cutoff_year and 
                             col_def["to_month"] == cutoff_month and
                             col_def["from_month"] == cutoff_month)
        
        if is_current_column and cutoff_mode != "End of Period (Full Periods)":
            end_date = cutoff_date
        else:
            end_date = getdate(_month_end(col_def["year"], col_def["to_month"]))
        
        val = _get_net_profit_accumulated(company, end_date)
        row[col_key]      = val if val != 0 else None
        col_vals[col_key] = val

    # Calculated columns
    code_to_val = {}
    for c2 in sorted_cols:
        if not c2.is_hidden and c2.column_type != "Calculated":
            code_to_val[c2.column_code.upper()] = col_vals.get(f"col_{c2.column_number}", 0)

    for col in sorted_cols:
        if col.is_hidden or col.column_type != "Calculated" or not col.calculation_formula:
            continue
        col_key = f"col_{col.column_number}"
        expr    = col.calculation_formula.strip()
        tokens  = re.findall(r"\b[A-Z0-9_:]+\b", expr)
        for tok in sorted(tokens, key=len, reverse=True):
            if tok in code_to_val:
                expr = _safe_replace(expr, tok, code_to_val[tok])
        try:
            val = flt(eval(expr))
        except Exception:
            val = 0.0
        row[col_key]      = val if val != 0 else None
        col_vals[col_key] = val
        code_to_val[col.column_code.upper()] = val

    return row, col_vals


# ═════════════════════════════════════════════════════════════════════════════
# VARIANCE HELPER — re-exported for excel_export module
# ═════════════════════════════════════════════════════════════════════════════
calculate_variance_pct = _variance_pct