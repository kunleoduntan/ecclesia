# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt
"""
Financial Report by Dimension
=============================
Supports P&L, Balance Sheet, Cash Flow with cost center, branch, or project dimensions.
"""

import re
from datetime import datetime

import frappe
from frappe import _
from frappe.utils import flt, getdate

_BALANCE_SHEET_TYPES = {"Balance Sheet"}


# ═════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════════

def execute(filters=None):
    filters = filters or {}

    # Validate required filters
    template_name = filters.get("template")
    if not template_name:
        frappe.throw(_("Please select a Financial Report Template."))

    template = frappe.get_doc("Financial Report Template", template_name)
    if not template.is_active:
        frappe.throw(_("The selected template is not active."))

    company = filters.get("company")
    if not company:
        frappe.throw(_("Please select a Company."))

    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    if not from_date or not to_date:
        frappe.throw(_("Please select both From Date and To Date."))

    dimension_type = filters.get("dimension_type", "Cost Center")
    
    # Get dimensions based on filter type
    dimensions = _get_dimensions(filters, dimension_type, company)
    
    # If no dimensions found, show message and return empty
    if not dimensions:
        frappe.msgprint(_("No {0} found for the selected filters. Please check your selection.").format(dimension_type), alert=True)
        # Return at least one column so report doesn't error
        columns = [
            {"label": _("Account"), "fieldname": "account_name", "fieldtype": "Data", "width": 300},
            {"label": _("Total"), "fieldname": "total", "fieldtype": "Currency", "width": 160}
        ]
        return columns, [], template.template_name, None, None

    show_totals = filters.get("show_totals", False)
    show_budget = filters.get("show_budget", False) and template.enable_budget_comparison
    budget_plan = filters.get("budget_plan") if show_budget else None
    show_comparison = filters.get("show_comparison", False) and template.show_comparison

    # Determine if this is a balance sheet report
    is_bs = template.report_type in _BALANCE_SHEET_TYPES

    # Build columns and data
    columns = _build_dimension_columns(dimensions, template, show_budget, show_comparison)
    data = _build_dimension_data(
        template, dimensions, company, from_date, to_date,
        show_budget, budget_plan, is_bs, show_comparison
    )

    # Add totals row if requested
    if show_totals and data:
        _add_totals_row(data, dimensions, template)

    report_title = template.report_title or template.template_name
    return columns, data, report_title, None, None


# ═════════════════════════════════════════════════════════════════════════════
# DIMENSION HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _get_dimensions(filters, dimension_type, company):
    """Get list of dimensions based on filters."""
    dimensions = []

    def _normalize_list(val):
        if isinstance(val, list):
            return [v for v in val if v]
        if isinstance(val, str):
            return [v.strip() for v in val.split(",") if v.strip()]
        return []

    try:
        if dimension_type == "Cost Center":
            specific = _normalize_list(filters.get("specific_cost_centers"))
            if specific:
                for cc in specific:
                    # Verify cost center exists
                    if frappe.db.exists("Cost Center", cc):
                        dimensions.append({"name": cc, "type": "Cost Center"})
            elif filters.get("parent_cost_center"):
                parent = filters.get("parent_cost_center")
                rows = frappe.get_all(
                    "Cost Center",
                    filters={
                        "parent_cost_center": parent,
                        "is_group": 0,
                        "company": company
                    },
                    fields=["name"],
                    order_by="name"
                )
                dimensions = [{"name": r.name, "type": "Cost Center"} for r in rows]
            else:
                # Get all cost centers (limit to 30 for performance)
                rows = frappe.get_all(
                    "Cost Center",
                    filters={"is_group": 0, "company": company},
                    fields=["name"],
                    order_by="name",
                    limit=30
                )
                dimensions = [{"name": r.name, "type": "Cost Center"} for r in rows]

        elif dimension_type == "Branch":
            specific = _normalize_list(filters.get("specific_branches"))
            if specific:
                for branch in specific:
                    if frappe.db.exists("Branch", branch):
                        dimensions.append({"name": branch, "type": "Branch"})
            else:
                rows = frappe.get_all(
                    "Branch",
                    filters={"company": company},
                    fields=["name"],
                    order_by="name",
                    limit=30
                )
                dimensions = [{"name": r.name, "type": "Branch"} for r in rows]

        elif dimension_type == "Project":
            specific = _normalize_list(filters.get("specific_projects"))
            if specific:
                for project in specific:
                    if frappe.db.exists("Project", project):
                        dimensions.append({"name": project, "type": "Project"})
            else:
                rows = frappe.get_all(
                    "Project",
                    filters={"company": company, "status": "Open"},
                    fields=["name"],
                    order_by="name",
                    limit=30
                )
                dimensions = [{"name": r.name, "type": "Project"} for r in rows]
    except Exception as e:
        frappe.log_error(f"Error getting dimensions: {str(e)}", "Financial Report by Dimension")
    
    return dimensions


def _sanitize_fieldname(name):
    """Create a safe fieldname from dimension name."""
    # Remove problematic characters
    name = str(name)
    # Replace spaces and special chars with underscore
    f = re.sub(r'[^a-zA-Z0-9]', '_', name)
    f = re.sub(r'_+', '_', f).strip('_')
    # Ensure it starts with letter
    if f and f[0].isdigit():
        f = "dim_" + f
    return f.lower()


# ═════════════════════════════════════════════════════════════════════════════
# COLUMN BUILDING
# ═════════════════════════════════════════════════════════════════════════════

def _build_dimension_columns(dimensions, template, show_budget, show_comparison):
    """Build column definitions for the report."""
    cols = [
        {"label": _("Account"), "fieldname": "account_name",
         "fieldtype": "Data", "width": 350}
    ]

    # Dimension columns - limit to first 15 to avoid performance issues
    for dim in dimensions[:15]:
        cols.append({
            "label": dim["name"][:30],  # Truncate long names
            "fieldname": _sanitize_fieldname(dim["name"]),
            "fieldtype": "Currency",
            "width": 140
        })

    # Total column
    cols.append({
        "label": _("Total"),
        "fieldname": "total",
        "fieldtype": "Currency",
        "width": 160
    })

    return cols


# ═════════════════════════════════════════════════════════════════════════════
# DATA BUILDING
# ═════════════════════════════════════════════════════════════════════════════

def _build_dimension_data(template, dimensions, company, from_date, to_date,
                           show_budget, budget_plan, is_bs, show_comparison):
    """Build report data rows."""
    data = []
    line_values = {}
    
    # Limit dimensions to first 15 for performance
    dimensions = dimensions[:15]

    for line in sorted(template.report_lines, key=lambda x: x.line_number):
        lt = line.line_type

        # Blank Line
        if lt == "Blank Line":
            data.append({"account_name": ""})
            continue

        # Header
        if lt == "Header":
            row = {
                "account_name": _format_label(line.line_label, line.indent_level, True),
                "_style": "font-weight: bold; background-color: #f5f5f5;"
            }
            data.append(row)
            continue

        # Account Aggregate
        if lt == "Account Aggregate":
            row = _process_account_line(
                line, dimensions, company, from_date, to_date,
                show_budget, budget_plan, is_bs, template
            )
            if row:
                if line.line_code:
                    # Store values for formula references
                    vals = {}
                    for dim in dimensions:
                        field = _sanitize_fieldname(dim["name"])
                        vals[field] = row.get(field, 0)
                    vals["total"] = row.get("total", 0)
                    line_values[line.line_code] = vals
                data.append(row)

        # Calculated
        elif lt == "Calculated" and line.calculation_formula:
            row = _process_calculated_line(
                line, dimensions, line_values, template
            )
            if row:
                if line.line_code:
                    vals = {}
                    for dim in dimensions:
                        field = _sanitize_fieldname(dim["name"])
                        vals[field] = row.get(field, 0)
                    vals["total"] = row.get("total", 0)
                    line_values[line.line_code] = vals
                data.append(row)

        # Retained Earnings
        elif lt == "Retained Earnings":
            row = _process_retained_earnings(
                line, dimensions, company, to_date, line_values, template, is_bs
            )
            if row:
                if line.line_code:
                    vals = {}
                    for dim in dimensions:
                        field = _sanitize_fieldname(dim["name"])
                        vals[field] = row.get(field, 0)
                    vals["total"] = row.get("total", 0)
                    line_values[line.line_code] = vals
                data.append(row)

    return data


def _process_account_line(line, dimensions, company, from_date, to_date,
                           show_budget, budget_plan, is_bs, template):
    """Process an Account Aggregate line."""
    accounts = _get_accounts_for_line(line, company)
    
    # Create row with formatted label
    row = {
        "account_name": _format_label(line.line_label, line.indent_level, line.is_bold)
    }
    
    sign = _sign(line)
    total = 0.0
    
    try:
        for dim in dimensions:
            field = _sanitize_fieldname(dim["name"])
            
            # Get balance for this dimension
            bal = _get_balance_by_dimension(
                accounts, company, from_date, to_date,
                dim["type"], dim["name"], sign, is_bs
            )
            
            # Only show non-zero values or if show_zero_values is enabled
            if bal != 0 or template.show_zero_values:
                row[field] = bal
            else:
                row[field] = None
                
            total += bal
    except Exception as e:
        frappe.log_error(f"Error processing account line {line.line_label}: {str(e)}", "Financial Report by Dimension")
    
    row["total"] = total if (total != 0 or template.show_zero_values) else None
    
    # Apply styling
    style = _row_style(line, template)
    if style:
        row["_style"] = style
    
    # Skip row if no accounts and not showing zero values
    if not accounts and not template.show_zero_values:
        return None
    
    return row


def _process_calculated_line(line, dimensions, line_values, template):
    """Process a Calculated line using formula."""
    if not line.calculation_formula:
        return None
    
    row = {
        "account_name": _format_label(line.line_label, line.indent_level, line.is_bold)
    }
    
    formula = line.calculation_formula.strip()
    total = 0.0
    
    try:
        for dim in dimensions:
            field = _sanitize_fieldname(dim["name"])
            
            # Evaluate formula for this dimension
            val = _evaluate_formula(formula, line_values, field)
            
            if val != 0 or template.show_zero_values:
                row[field] = val
            else:
                row[field] = None
                
            total += val
    except Exception as e:
        frappe.log_error(f"Error processing calculated line {line.line_label}: {str(e)}", "Financial Report by Dimension")
    
    row["total"] = total if (total != 0 or template.show_zero_values) else None
    
    style = _row_style(line, template)
    if style:
        row["_style"] = style
    
    return row


def _process_retained_earnings(line, dimensions, company, to_date, line_values, template, is_bs):
    """Process Retained Earnings line."""
    row = {
        "account_name": _format_label(line.line_label, line.indent_level, line.is_bold)
    }
    
    net_profit_code = getattr(line, "net_profit_line_code", None) or \
                      getattr(line, "calculation_formula", None)
    
    total = 0.0
    
    try:
        for dim in dimensions:
            field = _sanitize_fieldname(dim["name"])
            
            if net_profit_code and net_profit_code in line_values:
                val = line_values.get(net_profit_code, {}).get(field, 0.0)
            else:
                val = _get_net_profit_accumulated_by_dimension(
                    company, to_date, dim["type"], dim["name"]
                )
            
            if val != 0 or template.show_zero_values:
                row[field] = val
            else:
                row[field] = None
                
            total += val
    except Exception as e:
        frappe.log_error(f"Error processing retained earnings line {line.line_label}: {str(e)}", "Financial Report by Dimension")
    
    row["total"] = total if (total != 0 or template.show_zero_values) else None
    
    style = _row_style(line, template)
    if style:
        row["_style"] = style
    
    return row


# ═════════════════════════════════════════════════════════════════════════════
# GL BALANCE FUNCTIONS WITH DIMENSIONS
# ═════════════════════════════════════════════════════════════════════════════

def _get_balance_by_dimension(accounts, company, from_date, to_date, dim_type, dim_value, sign, is_bs):
    """Get balance for specific dimension."""
    if not accounts:
        return 0.0
    
    field_map = {"Cost Center": "cost_center", "Branch": "branch", "Project": "project"}
    field = field_map.get(dim_type)
    if not field:
        return 0.0
    
    # Check if field exists in GL Entry
    if not frappe.get_meta("GL Entry").has_field(field):
        return 0.0
    
    # Convert accounts list to tuple for SQL IN clause
    accounts_tuple = tuple(accounts) if len(accounts) > 1 else f"('{accounts[0]}')"
    
    if is_bs:
        # Balance Sheet: closing balance up to to_date
        sql = f"""
            SELECT COALESCE(SUM(
                CASE
                    WHEN acc.root_type IN ('Income','Liability','Equity')
                    THEN gle.credit - gle.debit
                    ELSE gle.debit - gle.credit
                END
            ), 0) AS balance
            FROM `tabGL Entry` gle
            INNER JOIN `tabAccount` acc ON gle.account = acc.name
            WHERE gle.account IN {accounts_tuple}
              AND gle.{field} = '{dim_value}'
              AND gle.company = '{company}'
              AND gle.posting_date <= '{to_date}'
              AND gle.is_cancelled = 0
        """
    else:
        # P&L: period movement
        sql = f"""
            SELECT COALESCE(SUM(
                CASE
                    WHEN acc.root_type IN ('Income','Liability','Equity')
                    THEN gle.credit - gle.debit
                    ELSE gle.debit - gle.credit
                END
            ), 0) AS balance
            FROM `tabGL Entry` gle
            INNER JOIN `tabAccount` acc ON gle.account = acc.name
            WHERE gle.account IN {accounts_tuple}
              AND gle.{field} = '{dim_value}'
              AND gle.company = '{company}'
              AND gle.posting_date BETWEEN '{from_date}' AND '{to_date}'
              AND gle.is_cancelled = 0
        """
    
    try:
        result = frappe.db.sql(sql, as_dict=True)
        if result and result[0].get("balance") is not None:
            return flt(result[0]["balance"]) * sign
        return 0.0
    except Exception as e:
        frappe.log_error(f"SQL Error in _get_balance_by_dimension: {str(e)}\nSQL: {sql}", "Financial Report by Dimension")
        return 0.0


def _get_net_profit_accumulated_by_dimension(company, as_at_date, dim_type, dim_value):
    """Get accumulated net profit for a dimension up to as_at_date."""
    field_map = {"Cost Center": "cost_center", "Branch": "branch", "Project": "project"}
    field = field_map.get(dim_type)
    if not field:
        return 0.0
    
    if not frappe.get_meta("GL Entry").has_field(field):
        return 0.0
    
    try:
        sql = f"""
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
              AND gle.{field} = '{dim_value}'
              AND gle.company = '{company}'
              AND gle.posting_date <= '{as_at_date}'
              AND gle.is_cancelled = 0
        """
        
        result = frappe.db.sql(sql, as_dict=True)
        
        if result:
            return flt(result[0].get("total_income", 0)) - flt(result[0].get("total_expense", 0))
        return 0.0
    except Exception as e:
        frappe.log_error(f"Error in _get_net_profit_accumulated_by_dimension: {str(e)}", "Financial Report by Dimension")
        return 0.0


# ═════════════════════════════════════════════════════════════════════════════
# FORMULA ENGINE
# ═════════════════════════════════════════════════════════════════════════════

def _evaluate_formula(formula, line_values, field):
    """Evaluate a formula for a specific dimension field."""
    if not formula:
        return 0.0
    
    expr = formula.strip()
    tokens = re.findall(r"\b[A-Z_][A-Z0-9_]*\b", expr)
    
    for token in sorted(tokens, key=len, reverse=True):
        if token in line_values:
            val = line_values[token].get(field, 0)
            expr = re.sub(r"\b" + re.escape(token) + r"\b", str(flt(val)), expr)
    
    try:
        return flt(eval(expr))  # noqa: S307
    except Exception:
        return 0.0


# ═════════════════════════════════════════════════════════════════════════════
# ACCOUNT MAPPING
# ═════════════════════════════════════════════════════════════════════════════

def _get_accounts_for_line(line, company):
    """Get accounts for a line based on mapping method."""
    method = line.account_mapping_method
    
    if method == "Account Range":
        return _accounts_by_range(line.account_from, line.account_to, company)
    if method == "Specific Accounts" and line.specific_accounts:
        accounts = [a.strip() for a in line.specific_accounts.split(",") if a.strip()]
        return frappe.get_all("Account", filters={"name": ["in", accounts], "is_group": 0}, pluck="name")
    if method == "Root Type" and line.root_type_filter:
        return frappe.get_all("Account", filters={"root_type": line.root_type_filter, "is_group": 0}, pluck="name")
    
    # If no accounts found or method not supported, return empty list
    return []


def _accounts_by_range(account_from, account_to, company):
    """Get accounts by number range."""
    if not account_from or not account_to:
        return []
    
    # Get all accounts and filter by number range
    accounts = frappe.get_all("Account", 
        filters={"company": company, "is_group": 0},
        fields=["name", "account_number"])
    
    # Convert account numbers to integers for comparison
    result = []
    for acc in accounts:
        acc_num = acc.get("account_number")
        if acc_num and acc_num.isdigit():
            if int(acc_num) >= int(account_from) and int(acc_num) <= int(account_to):
                result.append(acc.name)
    return result


# ═════════════════════════════════════════════════════════════════════════════
# ROW FORMATTING & STYLING
# ═════════════════════════════════════════════════════════════════════════════

def _format_label(label, indent_level, is_bold):
    """Format row label with indentation and bold."""
    indent = "&nbsp;&nbsp;&nbsp;&nbsp;" * int(indent_level or 0)
    if bool(int(is_bold or 0)):
        return f'{indent}<b>{label}</b>'
    return f"{indent}{label}"


def _row_style(line, template):
    """Apply row styling based on line properties."""
    def _bool(attr):
        return bool(int(getattr(line, attr, 0) or 0))

    is_total = _bool("is_total_row")
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
        "Top Border": ["border-top:1px solid #000"],
        "Bottom Border": ["border-bottom:1px solid #000"],
        "Top and Bottom": ["border-top:1px solid #000", "border-bottom:1px solid #000"],
        "Top Single Bottom Double": ["border-top:1px solid #000", "border-bottom:3px double #000"],
        "Top and Bottom Double": ["border-top:3px double #000", "border-bottom:3px double #000"],
    }
    border = (getattr(line, "border_style", None) or "").strip()
    parts.extend(border_map.get(border, []))
    return "; ".join(parts) + ";" if parts else None


def _sign(line):
    """Get sign multiplier for a line."""
    v = str(getattr(line, "sign_multiplier", "1") or "1").strip()
    if v in ("", "None", "none"):
        return 1
    try:
        return int(v)
    except (ValueError, TypeError):
        return 1


def _add_totals_row(data, dimensions, template):
    """Add totals row at the end of the report."""
    total_color = getattr(template, "excel_total_row_color", "#E7E6E6") or "#E7E6E6"
    
    # Calculate totals for each dimension
    dim_totals = {}
    for dim in dimensions:
        field = _sanitize_fieldname(dim["name"])
        total_val = 0
        for row in data:
            val = row.get(field, 0)
            if val and isinstance(val, (int, float)):
                total_val += val
        dim_totals[field] = total_val
    
    total_sum = 0
    for row in data:
        val = row.get("total", 0)
        if val and isinstance(val, (int, float)):
            total_sum += val
    
    row = {
        "account_name": "<b>TOTAL</b>",
        "_style": f"font-weight: bold; border-top: 1px solid #000; background-color: {total_color};"
    }
    
    # Add dimension totals
    for dim in dimensions:
        field = _sanitize_fieldname(dim["name"])
        row[field] = dim_totals.get(field, 0)
    
    row["total"] = total_sum
    
    data.append({"account_name": ""})  # Blank separator
    data.append(row)