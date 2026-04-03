# Copyright (c) 2026, 	kunle Oduntan and contributors
# For license information, please see license.txt



# Copyright (c) 2026, Ecclesia and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, cint, get_first_day, get_last_day, add_days
from datetime import datetime
from collections import defaultdict

# Global message for report
message = "Statement of Financial Position"

# Cache for account mappings to avoid repeated queries
_account_cache = {}


def execute(filters=None):
    """Main execution function for the report"""
    if not filters:
        filters = {}
    
    # Validate required filters
    validate_filters(filters)
    
    # Get report configuration
    config = get_report_config(filters)
    
    # Get columns
    columns = get_columns(config)
    
    # Get data
    data = get_data(config)
    
    # Apply filters (e.g., hide zero YTD rows)
    data = apply_post_filters(data, filters)
    
    # Prepare chart data
    chart = get_chart_data(data, config)
    
    # Return report components
    return columns, data, message, chart, None


def validate_filters(filters):
    """Validate required filter values"""
    if not filters.get("company"):
        frappe.throw("Please select a Company")
    
    if not filters.get("year"):
        filters["year"] = str(frappe.utils.now_datetime().year)


def get_report_config(filters):
    """Build configuration object for the report"""
    current_year = cint(filters.get("year") or frappe.utils.now_datetime().year)
    previous_year = current_year - 1
    
    return {
        "company": filters.get("company"),
        "current_year": current_year,
        "previous_year": previous_year,
        "frequency": filters.get("frequency") or "Monthly",
        "periods": get_periods(filters.get("frequency") or "Monthly"),
        "hide_zero_ytd": cint(filters.get("show_only_ytd"))
    }


def get_periods(frequency):
    """Return period definitions based on frequency"""
    if frequency == "Quarterly":
        return [
            ("Q1", [1, 2, 3]),
            ("Q2", [4, 5, 6]),
            ("Q3", [7, 8, 9]),
            ("Q4", [10, 11, 12])
        ]
    elif frequency == "Half-Yearly":
        return [
            ("H1", [1, 2, 3, 4, 5, 6]),
            ("H2", [7, 8, 9, 10, 11, 12])
        ]
    else:  # Monthly
        return [
            ("Jan", [1]), ("Feb", [2]), ("Mar", [3]), ("Apr", [4]),
            ("May", [5]), ("Jun", [6]), ("Jul", [7]), ("Aug", [8]),
            ("Sep", [9]), ("Oct", [10]), ("Nov", [11]), ("Dec", [12])
        ]


def get_columns(config):
    """Generate column definitions"""
    columns = [
        {
            "label": "Account Name",
            "fieldname": "account_name",
            "fieldtype": "Data",
            "width": 300
        }
    ]
    
    period_keys = []
    for period_label, _ in config["periods"]:
        field_key = period_label.lower().replace(" ", "_")
        period_keys.append(field_key)
        
        # Current year column
        columns.append({
            "label": f"{period_label}",
            "fieldname": field_key,
            "fieldtype": "Currency",
            "width": 130
        })
        
        # Last year column
        columns.append({
            "label": f"{period_label} LY",
            "fieldname": f"{field_key}_ly",
            "fieldtype": "Currency",
            "width": 130
        })
        
        # Variance percentage column
        columns.append({
            "label": f"{period_label} Var %",
            "fieldname": f"{field_key}_var",
            "fieldtype": "Percent",
            "width": 110
        })
    
    # Year to date column
    columns.append({
        "label": "Year To Date",
        "fieldname": "year_to_date",
        "fieldtype": "Currency",
        "width": 150
    })
    
    # Store period keys in config for later use
    config["period_keys"] = period_keys
    
    return columns


def get_financial_structure():
    """Define the financial statement structure"""
    return {
        "Non Current Assets": [
            "Property, plant and equipment",
            "Investments",
            "Investment In properties",
            "Intangible asset"
        ],
        "Current Assets": [
            "Inventories & consumables",
            "Trade & other receivables",
            "Cash and cash equivalent",
            "Short-term investments",
            "Other receivables"
        ],
        "Equity": [
            "Share capital",
            "Retained earnings",
            "Net profit/ (loss) for the month",
            "Revaluation reserves",
            "Other reserves"
        ],
        "Non Current Liabilities": [
            "Long-term liabilities",
            "Deferred tax liability"
        ],
        "Current Liabilities": [
            "Trade & other payables",
            "Borrowings",
            "Tax liabilities",
            "Finance lease",
            "Intercompany",
            "Other accrued expenses"
        ]
    }


def get_account_mapping(company):
    """Get account to financial group mapping with caching"""
    cache_key = f"account_mapping_{company}"
    
    if cache_key in _account_cache:
        return _account_cache[cache_key]
    
    accounts = frappe.get_all(
        "Account",
        filters={"company": company},
        fields=["name", "custom_financial_reporting_group"]
    )
    
    grouped = defaultdict(list)
    for account in accounts:
        if account.custom_financial_reporting_group:
            grouped[account.custom_financial_reporting_group].append(account.name)
    
    _account_cache[cache_key] = dict(grouped)
    return _account_cache[cache_key]


def get_gl_balances(accounts, from_date, to_date, company):
    """Fetch GL balances efficiently using single query"""
    if not accounts:
        return {}
    
    # Use parameterized query with IN clause
    account_placeholders = ', '.join(['%s'] * len(accounts))
    
    query = f"""
        SELECT 
            account,
            SUM(debit) as total_debit,
            SUM(credit) as total_credit
        FROM `tabGL Entry`
        WHERE 
            account IN ({account_placeholders})
            AND posting_date BETWEEN %s AND %s
            AND company = %s
            AND is_cancelled = 0
        GROUP BY account
    """
    
    params = list(accounts) + [from_date, to_date, company]
    results = frappe.db.sql(query, params, as_dict=1)
    
    balances = {}
    for row in results:
        balances[row.account] = {
            "debit": flt(row.total_debit),
            "credit": flt(row.total_credit)
        }
    
    return balances


def get_pl_totals(from_date, to_date, company):
    """Get P&L totals (income and expenses) efficiently"""
    query = """
        SELECT 
            acc.root_type,
            SUM(gl.debit) as total_debit,
            SUM(gl.credit) as total_credit
        FROM `tabGL Entry` gl
        INNER JOIN `tabAccount` acc ON gl.account = acc.name
        WHERE 
            gl.company = %s
            AND gl.posting_date BETWEEN %s AND %s
            AND acc.report_type = 'Profit and Loss'
            AND acc.root_type IN ('Income', 'Expense')
            AND gl.is_cancelled = 0
        GROUP BY acc.root_type
    """
    
    results = frappe.db.sql(query, (company, from_date, to_date), as_dict=1)
    
    income = 0
    expense = 0
    
    for row in results:
        if row.root_type == 'Income':
            income = flt(row.total_credit) - flt(row.total_debit)
        elif row.root_type == 'Expense':
            expense = flt(row.total_debit) - flt(row.total_credit)
    
    return income - expense


def calculate_balance(debit, credit, section):
    """Calculate balance based on account type"""
    if section in ["Equity", "Non Current Liabilities", "Current Liabilities"]:
        return flt(credit) - flt(debit)
    return flt(debit) - flt(credit)


def calculate_variance_percent(current, previous):
    """Calculate variance percentage safely"""
    if previous == 0:
        return None
    return ((current - previous) / abs(previous)) * 100


def get_date_range(year, month):
    """Get first and last day of month"""
    first_day = get_first_day(f"{year}-{month:02d}-01")
    last_day = get_last_day(f"{year}-{month:02d}-01")
    return first_day, last_day


def calculate_retained_earnings(config):
    """Calculate retained earnings row with cumulative P&L"""
    company = config["company"]
    current_year = config["current_year"]
    previous_year = config["previous_year"]
    periods = config["periods"]
    
    retained_earnings_row = {
        "account_name": "    Retained Earnings (Calculated)",
        "indent": 1
    }
    
    cumulative_current = 0
    cumulative_previous = 0
    ytd_current = 0
    
    for period_label, month_list in periods:
        key = period_label.lower().replace(" ", "_")
        
        # Calculate for each month in period
        period_profit_current = 0
        period_profit_previous = 0
        
        for month in month_list:
            # Current year
            from_date_current, to_date_current = get_date_range(current_year, month)
            profit_current = get_pl_totals(from_date_current, to_date_current, company)
            period_profit_current += profit_current
            
            # Previous year
            from_date_previous, to_date_previous = get_date_range(previous_year, month)
            profit_previous = get_pl_totals(from_date_previous, to_date_previous, company)
            period_profit_previous += profit_previous
        
        # Accumulate
        cumulative_current += period_profit_current
        cumulative_previous += period_profit_previous
        ytd_current += period_profit_current
        
        # Store cumulative values
        retained_earnings_row[key] = cumulative_current
        retained_earnings_row[f"{key}_ly"] = cumulative_previous
        retained_earnings_row[f"{key}_var"] = calculate_variance_percent(
            cumulative_current, cumulative_previous
        )
    
    retained_earnings_row["year_to_date"] = ytd_current
    
    return retained_earnings_row


def get_data(config):
    """Generate report data"""
    company = config["company"]
    current_year = config["current_year"]
    previous_year = config["previous_year"]
    periods = config["periods"]
    period_keys = config["period_keys"]
    
    # Get account mappings
    account_mapping = get_account_mapping(company)
    
    # Get financial structure
    financial_structure = get_financial_structure()
    
    data = []
    
    # Initialize summary rows
    total_assets_row = {
        "account_name": '<span style="font-weight:bold;">Total Assets</span>',
        "is_total": True
    }
    total_liabilities_row = {
        "account_name": '<span style="font-weight:bold;">Total Equity & Liabilities</span>',
        "is_total": True
    }
    
    for key in period_keys:
        total_assets_row[key] = 0
        total_assets_row[f"{key}_ly"] = 0
        total_liabilities_row[key] = 0
        total_liabilities_row[f"{key}_ly"] = 0
    
    total_assets_ytd = 0
    total_liabilities_ytd = 0
    
    # Calculate retained earnings once
    retained_earnings_row = calculate_retained_earnings(config)
    
    # Process each financial section
    for section, categories in financial_structure.items():
        # Add section header
        data.append({
            "account_name": f"▶ {section}",
            "is_header": True
        })
        
        section_totals = defaultdict(float)
        section_ytd = 0
        
        # Process each category in section
        for category in categories:
            accounts = account_mapping.get(category, [])
            if not accounts:
                continue
            
            # Initialize category row
            category_row = {
                "account_name": f"    {category}",
                "indent": 1
            }
            
            category_ytd = 0
            cumulative_current = 0
            cumulative_previous = 0
            
            # Process each period
            for period_label, month_list in periods:
                key = period_label.lower().replace(" ", "_")
                
                period_total_current = 0
                period_total_previous = 0
                
                # Get balances for all months in period at once
                for month in month_list:
                    # Current year
                    from_date_current, to_date_current = get_date_range(current_year, month)
                    balances_current = get_gl_balances(
                        accounts, from_date_current, to_date_current, company
                    )
                    
                    # Previous year
                    from_date_previous, to_date_previous = get_date_range(previous_year, month)
                    balances_previous = get_gl_balances(
                        accounts, from_date_previous, to_date_previous, company
                    )
                    
                    # Sum up balances
                    for account in accounts:
                        if account in balances_current:
                            bal = balances_current[account]
                            period_total_current += calculate_balance(
                                bal["debit"], bal["credit"], section
                            )
                        
                        if account in balances_previous:
                            bal = balances_previous[account]
                            period_total_previous += calculate_balance(
                                bal["debit"], bal["credit"], section
                            )
                
                # Accumulate
                cumulative_current += period_total_current
                cumulative_previous += period_total_previous
                category_ytd += period_total_current
                
                # Store values
                category_row[key] = cumulative_current
                category_row[f"{key}_ly"] = cumulative_previous
                category_row[f"{key}_var"] = calculate_variance_percent(
                    cumulative_current, cumulative_previous
                )
                
                # Add to section totals
                section_totals[key] += cumulative_current
                section_totals[f"{key}_ly"] += cumulative_previous
            
            category_row["year_to_date"] = category_ytd
            section_ytd += category_ytd
            
            data.append(category_row)
        
        # Add retained earnings to Equity section
        if section == "Equity":
            data.append(retained_earnings_row)
            for key in period_keys:
                section_totals[key] += retained_earnings_row.get(key, 0)
                section_totals[f"{key}_ly"] += retained_earnings_row.get(f"{key}_ly", 0)
            section_ytd += retained_earnings_row.get("year_to_date", 0)
        
        # Add section total row
        section_total_row = {
            "account_name": f'<span style="font-weight:bold;">    Total - {section}</span>',
            "is_section_total": True,
            "indent": 1
        }
        
        for key in period_keys:
            section_total_row[key] = section_totals[key]
            section_total_row[f"{key}_ly"] = section_totals[f"{key}_ly"]
            section_total_row[f"{key}_var"] = calculate_variance_percent(
                section_totals[key], section_totals[f"{key}_ly"]
            )
            
            # Add to grand totals
            if section in ["Non Current Assets", "Current Assets"]:
                total_assets_row[key] += section_totals[key]
                total_assets_row[f"{key}_ly"] += section_totals[f"{key}_ly"]
            elif section in ["Equity", "Non Current Liabilities", "Current Liabilities"]:
                total_liabilities_row[key] += section_totals[key]
                total_liabilities_row[f"{key}_ly"] += section_totals[f"{key}_ly"]
        
        section_total_row["year_to_date"] = section_ytd
        
        if section in ["Non Current Assets", "Current Assets"]:
            total_assets_ytd += section_ytd
        elif section in ["Equity", "Non Current Liabilities", "Current Liabilities"]:
            total_liabilities_ytd += section_ytd
        
        data.append(section_total_row)
        
        # Add separator and total assets after current assets
        if section == "Current Assets":
            data.append({"account_name": ""})
            data.append(total_assets_row)
            data.append({"account_name": ""})
    
    # Calculate variance for grand totals
    for key in period_keys:
        total_assets_row[f"{key}_var"] = calculate_variance_percent(
            total_assets_row[key], total_assets_row[f"{key}_ly"]
        )
        total_liabilities_row[f"{key}_var"] = calculate_variance_percent(
            total_liabilities_row[key], total_liabilities_row[f"{key}_ly"]
        )
    
    total_assets_row["year_to_date"] = total_assets_ytd
    total_liabilities_row["year_to_date"] = total_liabilities_ytd
    
    # Add final total liabilities row
    data.append(total_liabilities_row)
    
    return data


def apply_post_filters(data, filters):
    """Apply post-processing filters"""
    if cint(filters.get("show_only_ytd")):
        # Filter out rows with zero YTD
        data = [row for row in data if row.get("year_to_date") or row.get("is_header")]
    
    return data


def get_chart_data(data, config):
    """Generate chart data for visualization"""
    chart_data = {
        "data": {
            "labels": [],
            "datasets": []
        },
        "type": "bar",
        "colors": ["#4CAF50", "#FF9800", "#2196F3"]
    }
    
    # Extract summary data for chart
    assets_data = []
    liabilities_data = []
    equity_data = []
    
    for row in data:
        account_name = row.get("account_name", "")
        
        if "Total - Current Assets" in account_name:
            for key in config["period_keys"]:
                assets_data.append(row.get(key, 0))
        elif "Total - Equity" in account_name:
            for key in config["period_keys"]:
                equity_data.append(row.get(key, 0))
        elif "Total - Current Liabilities" in account_name:
            for key in config["period_keys"]:
                liabilities_data.append(row.get(key, 0))
    
    chart_data["data"]["labels"] = [p[0] for p in config["periods"]]
    chart_data["data"]["datasets"] = [
        {"name": "Assets", "values": assets_data},
        {"name": "Liabilities", "values": liabilities_data},
        {"name": "Equity", "values": equity_data}
    ]
    
    return chart_data