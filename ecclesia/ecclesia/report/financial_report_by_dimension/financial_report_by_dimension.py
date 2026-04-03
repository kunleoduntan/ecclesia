# Copyright (c) 2026, Kunle Oduntan
# License: see license.txt

import frappe
from frappe import _
from frappe.utils import flt
import re


def execute(filters=None):
    if not filters:
        filters = {}

    if not filters.get("template"):
        frappe.throw(_("Please select a Financial Report Template"))
    if not filters.get("company"):
        frappe.throw(_("Please select a Company"))
    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw(_("Please select dates"))

    template   = frappe.get_doc("Financial Report Template", filters.get("template"))
    dimensions = get_dimensions(filters)
    columns    = build_dimension_columns(dimensions, filters)
    data       = build_dimension_data(template, dimensions, filters)

    if filters.get("show_totals"):
        add_totals_row(data, dimensions, template)

    return columns, data


# ─────────────────────────────────────────────
# DIMENSIONS
# ─────────────────────────────────────────────

def get_dimensions(filters):
    dimensions = []
    dim_type   = filters.get("dimension_type", "Cost Center")

    def normalize_list(val):
        if isinstance(val, list):
            return [v for v in val if v]
        if isinstance(val, str):
            return [v.strip() for v in val.split(",") if v.strip()]
        return []

    if dim_type == "Cost Center":
        specific = normalize_list(filters.get("specific_cost_centers"))
        if specific:
            dimensions = [{"name": cc, "type": "Cost Center"} for cc in specific]
        elif filters.get("parent_cost_center"):
            rows = frappe.get_all(
                "Cost Center",
                filters={"parent_cost_center": filters["parent_cost_center"], "is_group": 0},
                fields=["name"],
                order_by="name"
            )
            dimensions = [{"name": r.name, "type": "Cost Center"} for r in rows]

    elif dim_type == "Branch":
        dimensions = [{"name": b, "type": "Branch"}
                      for b in normalize_list(filters.get("specific_branches"))]

    elif dim_type == "Project":
        dimensions = [{"name": p, "type": "Project"}
                      for p in normalize_list(filters.get("specific_projects"))]

    return dimensions


# ─────────────────────────────────────────────
# COLUMNS
# ─────────────────────────────────────────────

def build_dimension_columns(dimensions, filters):
    columns = [{"label": _("Account"), "fieldname": "account_name",
                "fieldtype": "Data", "width": 300}]

    for dim in dimensions:
        columns.append({
            "label":     dim["name"],
            "fieldname": sanitize_fieldname(dim["name"]),
            "fieldtype": "Currency",
            "width":     150
        })

    columns.append({"label": _("Total"), "fieldname": "total",
                    "fieldtype": "Currency", "width": 160})
    return columns


# ─────────────────────────────────────────────
# DATA BUILD
# ─────────────────────────────────────────────

def build_dimension_data(template, dimensions, filters):
    data        = []
    line_values = {}

    for line in sorted(template.report_lines, key=lambda x: x.line_number):

        if line.line_type == "Blank Line":
            data.append({"account_name": ""})
            continue

        if line.line_type == "Header":
            data.append({
                "account_name": get_formatted_label(
                    line.line_label, line.indent_level, line.is_bold
                ),
                "_style": "font-weight: bold; background-color: #f5f5f5;"
            })
            continue

        if line.line_type == "Account Aggregate":
            row = process_account_line(line, dimensions, filters, template)
            if row:
                data.append(row)
                if line.line_code:
                    line_values[line.line_code] = extract_values(row, dimensions)

        elif line.line_type == "Calculated":
            row = process_calculated_line(line, dimensions, line_values, template)
            if row:
                data.append(row)
                if line.line_code:
                    line_values[line.line_code] = extract_values(row, dimensions)

    return data


# ─────────────────────────────────────────────
# ACCOUNT ROW
# ─────────────────────────────────────────────

def process_account_line(line, dimensions, filters, template):
    accounts = get_accounts_for_line(line, filters.get("company"))
    row      = {"account_name": get_formatted_label(
                    line.line_label, line.indent_level, line.is_bold)}
    sign     = -1 if line.sign_multiplier == "-1" else 1
    total    = 0

    for dim in dimensions:
        field = sanitize_fieldname(dim["name"])
        bal   = get_balance_by_dimension(
            accounts,
            filters.get("company"),
            filters.get("from_date"),
            filters.get("to_date"),
            dim["type"],
            dim["name"]
        )
        val        = flt(bal) * sign
        row[field] = val
        total     += val

    row["total"] = total

    # ← uses the exact same apply_row_styling from the working report
    style = apply_row_styling(line, template)
    if style:
        row["_style"] = style

    return row


# ─────────────────────────────────────────────
# CALCULATED ROW
# ─────────────────────────────────────────────

def process_calculated_line(line, dimensions, line_values, template):
    if not line.calculation_formula:
        return None

    row   = {"account_name": get_formatted_label(
                 line.line_label, line.indent_level, line.is_bold)}
    total = 0

    for dim in dimensions:
        field      = sanitize_fieldname(dim["name"])
        val        = evaluate_formula(line.calculation_formula, line_values, field)
        row[field] = val
        total     += val

    row["total"] = total

    style = apply_row_styling(line, template)
    if style:
        row["_style"] = style

    return row


# ─────────────────────────────────────────────
# STYLING  — copied verbatim from working report
# ─────────────────────────────────────────────

def apply_row_styling(line, template):
    """
    Exact copy of apply_row_styling from Financial Report Template Based.
    Reads from Financial Report Line fields:
      row_color       – custom hex background  (highest priority)
      is_total_row    – uses template.excel_total_row_color
      is_subtotal_row – uses template.excel_subtotal_color
      is_bold         – font-weight: bold
      border_style    – Top Border | Bottom Border | Top and Bottom |
                        Top Single Bottom Double | Top and Bottom Double
    Returns a CSS string or None.
    """
    styles = []

    # ── background colour ──────────────────────────────────────────────
    row_color = getattr(line, 'row_color', None)
    if row_color:
        styles.append(f"background-color: {row_color}")
    elif line.is_total_row:
        styles.append(f"background-color: {template.excel_total_row_color}")
    elif line.is_subtotal_row:
        styles.append(f"background-color: {template.excel_subtotal_color}")

    # ── font weight ───────────────────────────────────────────────────
    if line.is_bold or line.is_total_row or line.is_subtotal_row:
        styles.append("font-weight: bold")

    # ── borders ───────────────────────────────────────────────────────
    border_style = getattr(line, 'border_style', None)

    if border_style == "Top Border":
        styles.append("border-top: 1px solid #000")
    elif border_style == "Bottom Border":
        styles.append("border-bottom: 1px solid #000")
    elif border_style == "Top and Bottom":
        styles.append("border-top: 1px solid #000")
        styles.append("border-bottom: 1px solid #000")
    elif border_style == "Top Single Bottom Double":
        styles.append("border-top: 1px solid #000")
        styles.append("border-bottom: 3px double #000")
    elif border_style == "Top and Bottom Double":
        styles.append("border-top: 3px double #000")
        styles.append("border-bottom: 3px double #000")

    return "; ".join(styles) + ";" if styles else None


# ─────────────────────────────────────────────
# FORMULA ENGINE
# ─────────────────────────────────────────────

def evaluate_formula(formula, line_values, fieldname):
    expr   = formula
    tokens = re.findall(r'\b[A-Z_][A-Z0-9_]*\b', formula)
    for t in tokens:
        val  = flt(line_values.get(t, {}).get(fieldname, 0))
        expr = re.sub(r'\b' + t + r'\b', str(val), expr)
    try:
        return flt(eval(expr))  # noqa: S307
    except Exception:
        return 0


# ─────────────────────────────────────────────
# TOTALS ROW
# ─────────────────────────────────────────────

def add_totals_row(data, dimensions, template):
    total_color = getattr(template, "excel_total_row_color", "#E7E6E6") or "#E7E6E6"
    row = {
        "account_name": "TOTAL",
        "_style": f"font-weight: bold; border-top: 1px solid #000; background-color: {total_color};"
    }
    for dim in dimensions:
        f      = sanitize_fieldname(dim["name"])
        row[f] = sum(flt(r.get(f, 0)) for r in data)
    row["total"] = sum(flt(r.get("total", 0)) for r in data)
    data.append({"account_name": ""})
    data.append(row)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def extract_values(row, dimensions):
    out = {sanitize_fieldname(d["name"]): flt(row.get(sanitize_fieldname(d["name"]), 0))
           for d in dimensions}
    out["total"] = flt(row.get("total", 0))
    return out


def sanitize_fieldname(name):
    f = re.sub(r'[^a-zA-Z0-9_]', '_', str(name)).lower()
    f = re.sub(r'_+', '_', f).strip('_')
    return f if f and f[0].isalpha() else "dim_" + f


def get_formatted_label(label, indent_level, is_bold):
    """Exact copy from working report."""
    indent = "    " * int(indent_level or 0)
    if is_bold:
        return f'{indent}<span style="font-weight:bold;">{label}</span>'
    return f'{indent}{label}'


# ─────────────────────────────────────────────
# GL BALANCE
# ─────────────────────────────────────────────

def get_balance_by_dimension(accounts, company, from_date, to_date, dim_type, dim_value):
    if not accounts:
        return 0

    field_map = {"Cost Center": "cost_center", "Branch": "branch", "Project": "project"}
    field     = field_map.get(dim_type)
    if not field:
        return 0

    if not frappe.get_meta("GL Entry").has_field(field):
        frappe.log_error(
            f"GL Entry has no field '{field}'. Add '{dim_type}' as an Accounting Dimension.",
            "Financial Report by Dimension"
        )
        return 0

    res = frappe.db.sql(f"""
        SELECT SUM(
            CASE WHEN acc.root_type = 'Income'
                 THEN gle.credit - gle.debit
                 ELSE gle.debit - gle.credit
            END
        ) AS bal
        FROM  `tabGL Entry` gle
        JOIN  `tabAccount`  acc ON acc.name = gle.account
        WHERE gle.account      IN %(accounts)s
          AND gle.{field}       = %(val)s
          AND gle.company       = %(company)s
          AND gle.posting_date BETWEEN %(fd)s AND %(td)s
    """, {"accounts": accounts, "val": dim_value,
          "company": company, "fd": from_date, "td": to_date}, as_dict=1)

    return flt(res[0].bal) if res else 0


# ─────────────────────────────────────────────
# ACCOUNT MAPPING — all 5 methods
# ─────────────────────────────────────────────

def get_accounts_for_line(line, company):
    method = line.account_mapping_method

    if method == "Account Range":
        if not line.account_from or not line.account_to:
            return []
        from_num = extract_account_number(line.account_from)
        to_num   = extract_account_number(line.account_to)
        if from_num is None or to_num is None:
            return []
        accounts = frappe.get_all(
            "Account",
            filters={"company": company, "is_group": 0},
            fields=["name", "account_number"]
        )
        result = []
        for acc in accounts:
            acc_num = _safe_int(acc.account_number)
            if acc_num is not None and from_num <= acc_num <= to_num:
                result.append(acc.name)
        return result

    if method == "Specific Accounts" and line.specific_accounts:
        accounts = [a.strip() for a in line.specific_accounts.split(",") if a.strip()]
        valid = frappe.get_all(
            "Account",
            filters={"company": company, "name": ["in", accounts], "is_group": 0},
            fields=["name"]
        )
        return [a.name for a in valid]

    if method == "Root Type" and line.root_type_filter:
        return frappe.get_all(
            "Account",
            filters={"company": company, "root_type": line.root_type_filter, "is_group": 0},
            pluck="name"
        )

    if method == "Account Numbers Pattern" and line.account_number_pattern:
        p = line.account_number_pattern
        if '-' in p and not p.startswith('-'):
            parts = p.split('-', 1)
            try:
                lo, hi = int(parts[0].strip()), int(parts[1].strip())
                rows = frappe.get_all(
                    "Account",
                    filters={"company": company, "is_group": 0},
                    fields=["name", "account_number"]
                )
                return [r.name for r in rows
                        if _safe_int(r.account_number) is not None
                        and lo <= _safe_int(r.account_number) <= hi]
            except (ValueError, TypeError):
                pass
        return frappe.get_all(
            "Account",
            filters={"company": company, "is_group": 0,
                     "account_number": ["like", f"%{p}%"]},
            pluck="name"
        )

    if method == "Financial Reporting Group":
        grp = getattr(line, "financial_reporting_group", None)
        if grp:
            return frappe.get_all(
                "Account",
                filters={"company": company, "is_group": 0,
                         "custom_financial_reporting_group": grp},
                pluck="name"
            )

    return []


def extract_account_number(account_name):
    """Exact copy from working report."""
    if not account_name:
        return None
    acc = frappe.db.get_value("Account", account_name, "account_number")
    if acc:
        try:
            return int(acc)
        except Exception:
            pass
    match = re.match(r'^(\d+)', str(account_name))
    if match:
        try:
            return int(match.group(1))
        except Exception:
            pass
    return None


def _safe_int(val):
    try:
        return int(val)
    except (ValueError, TypeError):
        return None