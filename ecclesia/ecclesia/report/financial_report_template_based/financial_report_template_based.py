# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

#!/usr/bin/env python3
"""
Financial Report - Template-Based Dynamic Reporting System
Supports flexible P&L, Balance Sheet, and custom reports with optional budget comparison
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate, formatdate
import re
from datetime import datetime

def execute(filters=None):
    """
    Main entry point for the report
    """
    if not filters:
        filters = {}
    
    # Load template
    template_name = filters.get("template")
    if not template_name:
        frappe.throw(_("Please select a Financial Report Template"))
    
    template = frappe.get_doc("Financial Report Template", template_name)
    
    if not template.is_active:
        frappe.throw(_("Selected template is not active"))
    
    # Get report parameters
    company = filters.get("company")
    if not company:
        frappe.throw(_("Please select a Company"))
    
    year = int(filters.get("year", getdate(nowdate()).year))
    frequency = filters.get("frequency", "Monthly")
    hide_detail = int(filters.get("hide_detail") or 0)
    current_month = getdate().month
    
    # Budget comparison (optional)
    show_budget = filters.get("show_budget", 0) and template.enable_budget_comparison
    budget_plan = filters.get("budget_plan") if show_budget else None
    
    # Check if using custom column definition
    frappe.msgprint(f"Template: {template.template_name}, use_column_definition: {template.use_column_definition}")
    
    if template.use_column_definition:
        # Dynamic columns (INLINE - no imports!)
        columns = build_dynamic_columns_inline(template, filters)
        data = build_dynamic_data_inline(template, filters, company, year, current_month, budget_plan)
    else:
        # EXISTING: Default logic (unchanged)
        frappe.msgprint("Using STANDARD columns")
        # Define periods based on frequency
        periods = get_periods(frequency, current_month, year)
        
        # Build columns
        columns = build_columns(periods, template, show_budget)
        
        # Build data
        data = build_data(template, periods, company, year, current_month, hide_detail, show_budget, budget_plan)
    
    # Return results
    report_title = template.report_title or template.template_name
    return columns, data, report_title, None, None


def get_periods(frequency, current_month, year):
    """
    Generate period definitions based on frequency
    """
    if frequency == "Monthly":
        periods = []
        for m in range(1, current_month + 1):
            label = formatdate(f"{year}-{m:02d}-01", "MMM")
            periods.append((label, [m]))
    elif frequency == "Half-Yearly":
        periods = [("H1", [1,2,3,4,5,6]), ("H2", [7,8,9,10,11,12])]
    else:  # Quarterly
        periods = [("Q1", [1,2,3]), ("Q2", [4,5,6]), ("Q3", [7,8,9]), ("Q4", [10,11,12])]
    
    return periods


def build_columns(periods, template, show_budget):
    """
    Build column definitions based on template settings
    """
    columns = [{"label": "Account Name", "fieldname": "account_name", "fieldtype": "Data", "width": 300}]
    
    # Add period columns
    for p in periods:
        # Current period
        columns.append({
            "label": p[0], 
            "fieldname": p[0].lower(), 
            "fieldtype": "Currency", 
            "width": 120
        })
        
        # Last year comparison (if enabled)
        if template.show_comparison:
            columns.append({
                "label": f"{p[0]} LY", 
                "fieldname": f"{p[0].lower()}_ly", 
                "fieldtype": "Currency", 
                "width": 120
            })
            columns.append({
                "label": f"{p[0]} Var %", 
                "fieldname": f"{p[0].lower()}_var", 
                "fieldtype": "Percent", 
                "width": 90
            })
        
        # Budget comparison (if enabled)
        if show_budget:
            columns.append({
                "label": f"{p[0]} Bud", 
                "fieldname": f"{p[0].lower()}_bud", 
                "fieldtype": "Currency", 
                "width": 120
            })
            columns.append({
                "label": f"{p[0]} Bud Var %", 
                "fieldname": f"{p[0].lower()}_bud_var", 
                "fieldtype": "Percent", 
                "width": 90
            })
        
        # Spacer column
        columns.append({
            "label": "", 
            "fieldname": f"{p[0].lower()}_col", 
            "fieldtype": "Data", 
            "width": 15
        })
    
    # YTD columns
    columns.extend([
        {"label": "YTD", "fieldname": "year_to_date", "fieldtype": "Currency", "width": 130},
    ])
    
    if template.show_comparison:
        columns.extend([
            {"label": "YTD LY", "fieldname": "last_year_ytd", "fieldtype": "Currency", "width": 130},
            {"label": "YTD Var %", "fieldname": "achievement_ytd_pct", "fieldtype": "Percent", "width": 100}
        ])
    
    if show_budget:
        columns.extend([
            {"label": "YTD Budget", "fieldname": "ytd_budget", "fieldtype": "Currency", "width": 130},
            {"label": "YTD Bud Var %", "fieldname": "ytd_budget_var", "fieldtype": "Percent", "width": 100}
        ])
    
    # Percentage column (if enabled)
    if template.show_percentage_column:
        columns.append({
            "label": "% of Revenue", 
            "fieldname": "pct_revenue", 
            "fieldtype": "Percent", 
            "width": 100
        })
    
    return columns


def build_data(template, periods, company, year, current_month, hide_detail, show_budget, budget_plan):
    """
    Build report data based on template lines
    """
    data = []
    line_values = {}  # Store calculated values for use in formulas
    
    # Process each line in template
    for line in sorted(template.report_lines, key=lambda x: x.line_number):
        
        if line.line_type == "Blank Line":
            data.append({"account_name": ""})
            continue
        
        if line.line_type == "Header":
            row = {
                "account_name": get_formatted_label(line.line_label, line.indent_level, line.is_bold),
                "_style": "font-weight: bold; background-color: #f5f5f5;"
            }
            data.append(row)
            continue
        
        if line.line_type == "Account Aggregate":
            result = process_account_aggregate_line(
                line, periods, company, year, current_month, 
                show_budget, budget_plan, template
            )
            
            # Handle None return (skipped line)
            if result[0] is None:
                continue
            
            row, period_values, ytd_value, period_ly_values, ytd_ly_value, period_bud_values, ytd_bud_value = result
            
            # Store values for formula calculations
            if line.line_code:
                line_values[line.line_code] = {
                    'periods': period_values,
                    'ytd': ytd_value,
                    'periods_ly': period_ly_values,
                    'ytd_ly': ytd_ly_value,
                    'periods_bud': period_bud_values,
                    'ytd_bud': ytd_bud_value
                }
            
            data.append(row)
        
        elif line.line_type == "Calculated":
            row, period_values, ytd_value, period_ly_values, ytd_ly_value, period_bud_values, ytd_bud_value = process_calculated_line(
                line, periods, line_values, template, show_budget
            )
            
            # Store values for formula calculations
            if line.line_code:
                line_values[line.line_code] = {
                    'periods': period_values,
                    'ytd': ytd_value,
                    'periods_ly': period_ly_values,
                    'ytd_ly': ytd_ly_value,
                    'periods_bud': period_bud_values,
                    'ytd_bud': ytd_bud_value
                }
            
            data.append(row)
    
    return data


def process_account_aggregate_line(line, periods, company, year, current_month, 
                                   show_budget, budget_plan, template):
    """
    Process a line that aggregates account balances
    """
    # Get list of accounts based on mapping method
    accounts = get_accounts_for_line(line, company)
    
    if not accounts and not template.show_zero_values:
        # Skip this line if no accounts and zero values hidden
        return None, None, None, None, None, None, None
    
    # Initialize row
    row = {
        "account_name": get_formatted_label(line.line_label, line.indent_level, line.is_bold)
    }
    
    # Apply styling with borders
    style = apply_row_styling(line, template)
    if style:
        row["_style"] = style
    
    period_values = {}
    period_ly_values = {}
    period_bud_values = {}
    ytd_total = 0
    ytd_last_year = 0
    ytd_budget = 0
    
    # Get sign multiplier
    sign_multiplier = line.sign_multiplier
    if sign_multiplier == "-1":
        sign = -1
    elif sign_multiplier == "1":
        sign = 1
    else:
        sign = int(sign_multiplier) if sign_multiplier else 1
    
    # Process each period
    for period_label, months_list in periods:
        period_total = 0
        period_last_year = 0
        period_budget = 0
        
        for month in months_list:
            # Initialize budget value for this month
            month_budget_value = 0
            month_ly_value = 0
            
            # Current year actuals
            month_value = get_month_balance(accounts, company, year, month, sign)
            period_total += month_value
            
            # Last year actuals (if comparison enabled)
            if template.show_comparison:
                month_ly_value = get_month_balance(accounts, company, year - 1, month, sign)
                period_last_year += month_ly_value
            
            # Budget values (if enabled)
            if show_budget and budget_plan:
                month_budget_value = get_month_budget(accounts, budget_plan, month, sign)
                period_budget += month_budget_value
            
            # Add to YTD if month is in current period
            if month <= current_month:
                ytd_total += month_value
                if template.show_comparison:
                    ytd_last_year += month_ly_value
                if show_budget:
                    ytd_budget += month_budget_value
        
        # Store period values
        period_values[period_label.lower()] = period_total
        period_ly_values[period_label.lower()] = period_last_year
        period_bud_values[period_label.lower()] = period_budget
        row[period_label.lower()] = period_total
        
        # Last year comparison
        if template.show_comparison:
            row[f"{period_label.lower()}_ly"] = period_last_year
            row[f"{period_label.lower()}_var"] = calculate_variance_pct(period_total, period_last_year)
        
        # Budget comparison
        if show_budget:
            row[f"{period_label.lower()}_bud"] = period_budget
            row[f"{period_label.lower()}_bud_var"] = calculate_variance_pct(period_total, period_budget)
    
    # YTD columns
    row["year_to_date"] = ytd_total
    
    if template.show_comparison:
        row["last_year_ytd"] = ytd_last_year
        row["achievement_ytd_pct"] = calculate_variance_pct(ytd_total, ytd_last_year)
    
    if show_budget:
        row["ytd_budget"] = ytd_budget
        row["ytd_budget_var"] = calculate_variance_pct(ytd_total, ytd_budget)
    
    return row, period_values, ytd_total, period_ly_values, ytd_last_year, period_bud_values, ytd_budget


def process_calculated_line(line, periods, line_values, template, show_budget):
    """
    Process a calculated line using formula
    """
    if not line.calculation_formula:
        return {"account_name": line.line_label}, {}, 0
    
    # Initialize row
    row = {
        "account_name": get_formatted_label(line.line_label, line.indent_level, line.is_bold)
    }
    
    # Apply styling with borders
    style = apply_row_styling(line, template)
    if style:
        row["_style"] = style
    
    period_values = {}
    period_ly_values = {}
    period_bud_values = {}
    ytd_total = 0
    ytd_ly = 0
    ytd_bud = 0
    
    # Process each period
    for period_label, months_list in periods:
        period_value = evaluate_formula(line.calculation_formula, line_values, period_label.lower())
        period_values[period_label.lower()] = period_value
        # Only show value if it's not zero or if we're showing zeros
        row[period_label.lower()] = period_value if (period_value != 0 or template.show_zero_values) else None
        
        # Last year comparison (calculate from LY values)
        if template.show_comparison:
            period_ly_value = evaluate_formula(line.calculation_formula, line_values, period_label.lower(), suffix='_ly')
            period_ly_values[period_label.lower()] = period_ly_value
            row[f"{period_label.lower()}_ly"] = period_ly_value if (period_ly_value != 0 or template.show_zero_values) else None
            row[f"{period_label.lower()}_var"] = calculate_variance_pct(period_value, period_ly_value)
        
        # Budget comparison
        if show_budget:
            period_bud_value = evaluate_formula(line.calculation_formula, line_values, period_label.lower(), suffix='_bud')
            period_bud_values[period_label.lower()] = period_bud_value
            row[f"{period_label.lower()}_bud"] = period_bud_value if (period_bud_value != 0 or template.show_zero_values) else None
            row[f"{period_label.lower()}_bud_var"] = calculate_variance_pct(period_value, period_bud_value)
    
    # YTD calculation
    ytd_total = evaluate_formula_ytd(line.calculation_formula, line_values)
    row["year_to_date"] = ytd_total if (ytd_total != 0 or template.show_zero_values) else None
    
    if template.show_comparison:
        ytd_ly = evaluate_formula_ytd(line.calculation_formula, line_values, suffix='_ytd_ly')
        row["last_year_ytd"] = ytd_ly if (ytd_ly != 0 or template.show_zero_values) else None
        row["achievement_ytd_pct"] = calculate_variance_pct(ytd_total, ytd_ly)
    
    if show_budget:
        ytd_bud = evaluate_formula_ytd(line.calculation_formula, line_values, suffix='_ytd_bud')
        row["ytd_budget"] = ytd_bud if (ytd_bud != 0 or template.show_zero_values) else None
        row["ytd_budget_var"] = calculate_variance_pct(ytd_total, ytd_bud)
    
    return row, period_values, ytd_total, period_ly_values, ytd_ly, period_bud_values, ytd_bud


def apply_row_styling(line, template):
    """
    Apply styling including background color, font weight, and borders
    """
    styles = []
    
    # Custom row color from doctype (takes priority)
    row_color = getattr(line, 'row_color', None)
    if row_color:
        styles.append(f"background-color: {row_color}")
    # Background color from template (fallback)
    elif line.is_total_row:
        styles.append(f"background-color: {template.excel_total_row_color}")
    elif line.is_subtotal_row:
        styles.append(f"background-color: {template.excel_subtotal_color}")
    
    # Font weight
    if line.is_bold or line.is_total_row or line.is_subtotal_row:
        styles.append("font-weight: bold")
    
    # Borders from doctype
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


def get_accounts_for_line(line, company):
    """
    Get list of accounts based on line's mapping method
    """
    method = line.account_mapping_method
    
    if method == "Account Range":
        return get_accounts_by_range(line.account_from, line.account_to, company)
    
    elif method == "Account Numbers Pattern":
        return get_accounts_by_pattern(line.account_number_pattern, company)
    
    elif method == "Specific Accounts":
        return get_accounts_by_list(line.specific_accounts, company)
    
    elif method == "Financial Reporting Group":
        return get_accounts_by_group(line.financial_reporting_group, company)
    
    elif method == "Root Type":
        return get_accounts_by_root_type(line.root_type_filter, company)
    
    return []


def get_accounts_by_range(account_from, account_to, company):
    """
    Get accounts within a range
    """
    if not account_from or not account_to:
        return []
    
    # Get account numbers for comparison
    from_num = extract_account_number(account_from)
    to_num = extract_account_number(account_to)
    
    if from_num is None or to_num is None:
        return []
    
    accounts = frappe.get_all(
        "Account",
        filters={"company": company, "is_group": 0},
        fields=["name", "account_number"]
    )
    
    result = []
    for acc in accounts:
        acc_num = extract_account_number(acc.name)
        if acc_num and from_num <= acc_num <= to_num:
            result.append(acc.name)
    
    return result


def get_accounts_by_pattern(pattern, company):
    """
    Get accounts matching a pattern
    Examples: "7000-7599", "7%", "7[0-5]%"
    """
    if not pattern:
        return []
    
    # Check if it's a range pattern (7000-7599)
    if '-' in pattern and not pattern.startswith('-'):
        parts = pattern.split('-')
        if len(parts) == 2:
            try:
                from_num = int(parts[0].strip())
                to_num = int(parts[1].strip())
                
                accounts = frappe.get_all(
                    "Account",
                    filters={"company": company, "is_group": 0},
                    fields=["name", "account_number"]
                )
                
                result = []
                for acc in accounts:
                    acc_num = extract_account_number(acc.name)
                    if acc_num and from_num <= acc_num <= to_num:
                        result.append(acc.name)
                
                return result
            except ValueError:
                pass
    
    # Convert pattern to SQL LIKE pattern
    sql_pattern = pattern.replace('%', '%').replace('_', '_')
    
    # Get accounts
    accounts = frappe.get_all(
        "Account",
        filters={
            "company": company, 
            "is_group": 0,
            "account_number": ["like", sql_pattern]
        },
        fields=["name"]
    )
    
    return [acc.name for acc in accounts]


def get_accounts_by_list(account_list, company):
    """
    Get specific accounts from comma-separated list
    """
    if not account_list:
        return []
    
    accounts = [acc.strip() for acc in account_list.split(',')]
    
    # Verify accounts exist
    valid_accounts = frappe.get_all(
        "Account",
        filters={
            "company": company,
            "name": ["in", accounts],
            "is_group": 0
        },
        fields=["name"]
    )
    
    return [acc.name for acc in valid_accounts]


def get_accounts_by_group(group_name, company):
    """
    Get accounts by Financial Reporting Group
    """
    if not group_name:
        return []
    
    accounts = frappe.get_all(
        "Account",
        filters={
            "company": company,
            "custom_financial_reporting_group": group_name,
            "is_group": 0
        },
        fields=["name"]
    )
    
    return [acc.name for acc in accounts]


def get_accounts_by_root_type(root_type, company):
    """
    Get accounts by root type (Income, Expense, etc.)
    """
    if not root_type:
        return []
    
    accounts = frappe.get_all(
        "Account",
        filters={
            "company": company,
            "root_type": root_type,
            "is_group": 0
        },
        fields=["name"]
    )
    
    return [acc.name for acc in accounts]


def get_month_balance(accounts, company, year, month, sign=1):
    """
    Get total balance for accounts in a specific month
    """
    if not accounts:
        return 0
    
    day = get_month_end_day(year, month)
    
    result = frappe.db.sql("""
        SELECT SUM(
            CASE 
                WHEN acc.root_type = 'Income' THEN gle.credit - gle.debit
                ELSE gle.debit - gle.credit
            END
        ) AS balance
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE gle.account IN %(accounts)s
        AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
        AND gle.company = %(company)s
    """, {
        "accounts": accounts,
        "from_date": f"{year}-{month:02d}-01",
        "to_date": f"{year}-{month:02d}-{day}",
        "company": company
    }, as_dict=1)
    
    return flt(result[0].get("balance", 0)) * sign if result else 0


def get_month_budget(accounts, budget_plan, month, sign=1):
    """
    Get budget amount for accounts in a specific month
    """
    if not accounts or not budget_plan:
        return 0
    
    # Get budget plan document
    try:
        budget = frappe.get_doc("Budget Plan", budget_plan)
    except:
        return 0
    
    total = 0
    month_field = ["jan", "feb", "mar", "apr", "may", "jun", 
                   "jul", "aug", "sep", "oct", "nov", "dec"][month - 1]
    
    # Sum up budget for matching accounts
    for budget_line in budget.monthly_budget:
        if budget_line.gl_account in accounts:
            total += flt(budget_line.get(month_field, 0))
    
    return total * sign


def get_month_end_day(year, month):
    """
    Get the last day of a month
    """
    if month in [1, 3, 5, 7, 8, 10, 12]:
        return 31
    elif month in [4, 6, 9, 11]:
        return 30
    elif month == 2:
        return 29 if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0) else 28


def extract_account_number(account_name):
    """
    Extract numeric account number from account name
    """
    if not account_name:
        return None
    
    # Try to get account_number field
    acc = frappe.db.get_value("Account", account_name, "account_number")
    if acc:
        try:
            return int(acc)
        except:
            pass
    
    # Extract from name (e.g., "7000 - Sales Revenue" -> 7000)
    match = re.match(r'^(\d+)', str(account_name))
    if match:
        try:
            return int(match.group(1))
        except:
            pass
    
    return None


def evaluate_formula(formula, line_values, period_key, suffix=''):
    """
    Evaluate a formula for a specific period
    Example: "REV - COS" or "GP - ADMIN - SELL"
    """
    if not formula:
        return 0
    
    # Replace line codes with actual values
    formula_eval = formula
    
    # Find all line codes in formula (uppercase alphanumeric + underscore)
    tokens = re.findall(r'\b[A-Z_][A-Z0-9_]*\b', formula)
    
    for token in tokens:
        if token in line_values:
            value = 0
            if suffix == '_ly':
                # Get LY value from periods_ly
                value = line_values[token].get('periods_ly', {}).get(period_key, 0)
            elif suffix == '_bud':
                # Get Budget value from periods_bud  
                value = line_values[token].get('periods_bud', {}).get(period_key, 0)
            else:
                # Get current period value
                value = line_values[token]['periods'].get(period_key, 0)
            
            formula_eval = formula_eval.replace(token, str(value))
    
    try:
        return flt(eval(formula_eval))
    except:
        return 0


def evaluate_formula_ytd(formula, line_values, suffix=''):
    """
    Evaluate a formula for YTD
    """
    if not formula:
        return 0
    
    formula_eval = formula
    
    # Find all line codes in formula
    tokens = re.findall(r'\b[A-Z_][A-Z0-9_]*\b', formula)
    
    for token in tokens:
        if token in line_values:
            if suffix == '_ytd_ly':
                value = line_values[token].get('ytd_ly', 0)
            elif suffix == '_ytd_bud':
                value = line_values[token].get('ytd_bud', 0)
            else:
                value = line_values[token].get('ytd', 0)
            formula_eval = formula_eval.replace(token, str(value))
    
    try:
        return flt(eval(formula_eval))
    except:
        return 0


def calculate_variance_pct(current, previous):
    """
    Calculate variance percentage
    """
    if not previous or previous == 0:
        return None
    
    return ((current - previous) / abs(previous)) * 100


def get_formatted_label(label, indent_level, is_bold):
    """
    Format label with indentation and styling
    """
    indent = "    " * int(indent_level or 0)
    
    if is_bold:
        return f'{indent}<span style="font-weight:bold;">{label}</span>'
    
    return f'{indent}{label}'


# ============================================================================
# DYNAMIC COLUMN FUNCTIONS (INLINE - NO IMPORT NEEDED)
# ============================================================================

def resolve_column_code_inline(column_code, base_year, current_month=12):
    """Resolve column code to period details - M1, Q1, Y1, -Y1, M1:M3, etc."""
    code = column_code.upper().strip()
    year_offset = 0
    data_source = 'GL Entry'
    
    # Parse modifiers  
    if code.startswith('-'):
        match = re.match(r'^-Y(\d+)$', code)
        if match:
            year_offset = -int(match.group(1))
            code = 'FY'
        else:
            year_offset = -1
            code = code[1:]
    elif '_LY' in code:
        year_offset = -1
        code = code.replace('_LY', '')
    elif '_BUD' in code:
        data_source = 'Budget Plan'
        code = code.replace('_BUD', '')
    
    actual_year = base_year + year_offset
    
    # Range syntax (M1:M3, Q1:Q2)
    if ':' in code:
        parts = code.split(':')
        if len(parts) == 2:
            start_code = parts[0].strip()
            end_code = parts[1].strip()
            
            if start_code.startswith('M') and end_code.startswith('M'):
                start_month = int(start_code[1:])
                end_month = int(end_code[1:])
                if 1 <= start_month <= 12 and 1 <= end_month <= 12 and start_month <= end_month:
                    return {
                        'type': 'period',
                        'year': actual_year,
                        'month_from': start_month,
                        'month_to': end_month,
                        'data_source': data_source
                    }
            elif start_code.startswith('Q') and end_code.startswith('Q'):
                start_q = int(start_code[1:])
                end_q = int(end_code[1:])
                if 1 <= start_q <= 4 and 1 <= end_q <= 4 and start_q <= end_q:
                    start_month = (start_q - 1) * 3 + 1
                    end_month = end_q * 3
                    return {
                        'type': 'period',
                        'year': actual_year,
                        'month_from': start_month,
                        'month_to': end_month,
                        'data_source': data_source
                    }
    
    # Month codes (M1-M12)
    if code.startswith('M') and code[1:].isdigit():
        month_num = int(code[1:])
        if 1 <= month_num <= 12:
            return {
                'type': 'period',
                'year': actual_year,
                'month_from': month_num,
                'month_to': month_num,
                'data_source': data_source
            }
    
    # Quarter codes (Q1-Q4)
    elif code.startswith('Q') and code[1:].isdigit():
        quarter_num = int(code[1:])
        if 1 <= quarter_num <= 4:
            start_month = (quarter_num - 1) * 3 + 1
            return {
                'type': 'period',
                'year': actual_year,
                'month_from': start_month,
                'month_to': start_month + 2,
                'data_source': data_source
            }
    
    # Half-year codes (H1-H2)
    elif code.startswith('H') and code[1:].isdigit():
        half_num = int(code[1:])
        if 1 <= half_num <= 2:
            start_month = (half_num - 1) * 6 + 1
            return {
                'type': 'period',
                'year': actual_year,
                'month_from': start_month,
                'month_to': start_month + 5,
                'data_source': data_source
            }
    
    # YTD
    elif code == 'YTD':
        return {
            'type': 'ytd',
            'year': actual_year,
            'month_from': 1,
            'month_to': current_month,
            'data_source': data_source
        }
    
    # Year codes (Y1, FY)
    elif code in ['FY', 'Y1']:
        return {
            'type': 'period',
            'year': actual_year,
            'month_from': 1,
            'month_to': 12,
            'data_source': data_source
        }
    
    return None


def build_dynamic_columns_inline(template, filters):
    """Build columns from template's column definitions"""
    if not template.report_columns:
        frappe.throw(_("No columns defined. Add columns or disable 'Use Custom Column Definition'."))
    
    columns = [{"label": _("Account Name"), "fieldname": "account_name", "fieldtype": "Data", "width": 300}]
    
    for col in sorted(template.report_columns, key=lambda x: x.column_number):
        if col.is_hidden:
            continue
        
        fieldtype = 'Currency'
        if col.number_format == 'Percent':
            fieldtype = 'Percent'
        elif col.number_format == 'Integer':
            fieldtype = 'Int'
        elif col.number_format == 'Decimal':
            fieldtype = 'Float'
        
        columns.append({
            "label": col.column_label or col.column_code,
            "fieldname": f"col_{col.column_number}",
            "fieldtype": fieldtype,
            "width": col.column_width or 120
        })
    
    return columns


def build_dynamic_data_inline(template, filters, company, base_year, current_month, budget_plan):
    """Build report data using dynamic columns"""
    data = []
    line_values = {}
    
    for line in sorted(template.report_lines, key=lambda x: x.line_number):
        if line.line_type == "Blank Line":
            data.append({"account_name": ""})
            continue
        
        if line.line_type == "Header":
            row = {
                "account_name": get_formatted_label(line.line_label, line.indent_level, line.is_bold),
                "_style": "font-weight: bold; background-color: #f5f5f5;"
            }
            data.append(row)
            continue
        
        row = process_line_inline(line, template, company, base_year, current_month, budget_plan, line_values)
        if row:
            data.append(row)
    
    return data


def process_line_inline(line, template, company, base_year, current_month, budget_plan, line_values):
    """Process a single line with dynamic columns"""
    
    # Calculated lines
    if line.line_type == 'Calculated':
        if not line.calculation_formula:
            return None
        
        row = {"account_name": get_formatted_label(line.line_label, line.indent_level, line.is_bold)}
        
        style = apply_row_styling(line, template)
        if style:
            row["_style"] = style
        
        row_column_values = {}
        for col in sorted(template.report_columns, key=lambda x: x.column_number):
            if col.is_hidden:
                continue
            
            col_key = f"col_{col.column_number}"
            
            if col.column_type != 'Calculated':
                # Evaluate row formula
                formula_eval = line.calculation_formula
                tokens = re.findall(r'\b[A-Z_][\w]*\b', formula_eval)
                
                for token in tokens:
                    if token in line_values and col_key in line_values[token]:
                        formula_eval = formula_eval.replace(token, str(line_values[token][col_key]))
                
                try:
                    value = flt(eval(formula_eval))
                except:
                    value = 0
                
                row[col_key] = value if (value != 0 or template.show_zero_values) else None
                row_column_values[col_key] = value
        
        if line.line_code:
            line_values[line.line_code] = row_column_values
        
        return row
    
    # Account aggregate lines
    accounts = get_accounts_for_line(line, company)
    
    if not accounts and not template.show_zero_values:
        return None
    
    row = {"account_name": get_formatted_label(line.line_label, line.indent_level, line.is_bold)}
    
    style = apply_row_styling(line, template)
    if style:
        row["_style"] = style
    
    # Get sign
    sign_multiplier = line.sign_multiplier
    if sign_multiplier == "-1":
        sign = -1
    elif sign_multiplier == "1":
        sign = 1
    else:
        sign = int(sign_multiplier) if sign_multiplier else 1
    
    # Process each column
    row_column_values = {}
    for col in sorted(template.report_columns, key=lambda x: x.column_number):
        if col.is_hidden:
            continue
        
        col_key = f"col_{col.column_number}"
        
        if col.column_type != 'Calculated':
            col_def = resolve_column_code_inline(col.column_code, base_year, current_month)
            if col_def:
                total = 0
                for month in range(col_def['month_from'], col_def['month_to'] + 1):
                    if col_def['data_source'] == 'Budget Plan':
                        total += get_month_budget(accounts, budget_plan, month, sign)
                    else:
                        total += get_month_balance(accounts, company, col_def['year'], month, sign)
                
                row[col_key] = total if (total != 0 or template.show_zero_values) else None
                row_column_values[col_key] = total
    
    if line.line_code:
        line_values[line.line_code] = row_column_values
    
    return row