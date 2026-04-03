#!/usr/bin/env python3
"""
Migration Script: Convert Hardcoded Report to Financial Report Template
This creates a template from your existing P&L configuration
"""

import frappe
from frappe import _

def create_standard_pl_template():
    """
    Create the standard P&L template from your existing code
    """
    
    print("Creating 'Standard P&L Template'...")
    
    # Check if template already exists
    if frappe.db.exists("Financial Report Template", "Standard P&L Template"):
        print("Template already exists. Updating...")
        template = frappe.get_doc("Financial Report Template", "Standard P&L Template")
        template.report_lines = []  # Clear existing lines
    else:
        template = frappe.new_doc("Financial Report Template")
        template.template_name = "Standard P&L Template"
    
    # Set template properties
    template.report_type = "Profit and Loss"
    template.is_default = 1
    template.is_active = 1
    template.description = "Standard Profit & Loss statement with EBITDA, EBIT, and PBT calculations"
    template.report_title = "Statement of Comprehensive Income"
    template.show_comparison = 1
    template.enable_budget_comparison = 1
    
    # Excel settings
    template.excel_header_color = "#4472C4"
    template.excel_total_row_color = "#E7E6E6"
    template.excel_subtotal_color = "#F2F2F2"
    template.excel_header_row = "#D9E1F2"
    template.show_zero_values = 0
    template.decimal_places = 2
    template.thousands_separator = 1
    template.show_percentage_column = 1
    template.variance_threshold_highlight = 10
    template.negative_values_color = "#FF0000"
    
    # Define report lines based on your existing code
    lines = [
        # Revenue
        {
            "line_number": 10,
            "line_label": "Brokerage Income",
            "line_code": "REV",
            "line_type": "Account Aggregate",
            "account_mapping_method": "Financial Reporting Group",
            "financial_reporting_group": "Brokerage income",
            "sign_multiplier": "1",
            "indent_level": 0,
            "is_bold": 1,
            "is_total_row": 0,
            "is_subtotal_row": 0,
            "hide_if_zero": 0,
            "show_percentage": 0
        },
        
        # Direct Commission Expenses
        {
            "line_number": 20,
            "line_label": "Direct Commission Expenses",
            "line_code": "DCE",
            "line_type": "Account Aggregate",
            "account_mapping_method": "Financial Reporting Group",
            "financial_reporting_group": "Direct commission expenses",
            "sign_multiplier": "1",
            "indent_level": 0,
            "is_bold": 0,
            "is_total_row": 0,
            "is_subtotal_row": 0,
            "hide_if_zero": 0,
            "show_percentage": 0
        },
        
        # Gross Profit
        {
            "line_number": 30,
            "line_label": "Gross Profit",
            "line_code": "GP",
            "line_type": "Calculated",
            "calculation_formula": "REV - DCE",
            "sign_multiplier": "1",
            "indent_level": 0,
            "is_bold": 1,
            "is_total_row": 1,
            "is_subtotal_row": 0,
            "hide_if_zero": 0,
            "show_percentage": 0
        },
        
        # Blank line
        {
            "line_number": 35,
            "line_label": "",
            "line_type": "Blank Line"
        },
        
        # Administrative Expenses
        {
            "line_number": 40,
            "line_label": "Administrative Expenses",
            "line_code": "ADMIN",
            "line_type": "Account Aggregate",
            "account_mapping_method": "Financial Reporting Group",
            "financial_reporting_group": "Administrative Expenses",
            "sign_multiplier": "1",
            "indent_level": 0,
            "is_bold": 0,
            "is_total_row": 0,
            "is_subtotal_row": 0,
            "hide_if_zero": 0,
            "show_percentage": 0
        },
        
        # Repairs & Maintenance
        {
            "line_number": 45,
            "line_label": "Repairs & Maintenance Expenses",
            "line_code": "REPAIR",
            "line_type": "Account Aggregate",
            "account_mapping_method": "Financial Reporting Group",
            "financial_reporting_group": "Repairs & maintenance Expenses",
            "sign_multiplier": "1",
            "indent_level": 0,
            "is_bold": 0,
            "is_total_row": 0,
            "is_subtotal_row": 0,
            "hide_if_zero": 0,
            "show_percentage": 0
        },
        
        # Selling & Distribution
        {
            "line_number": 50,
            "line_label": "Selling & Distribution Expenses",
            "line_code": "SELL",
            "line_type": "Account Aggregate",
            "account_mapping_method": "Financial Reporting Group",
            "financial_reporting_group": "Selling, distribution & marketing expenses",
            "sign_multiplier": "1",
            "indent_level": 0,
            "is_bold": 0,
            "is_total_row": 0,
            "is_subtotal_row": 0,
            "hide_if_zero": 0,
            "show_percentage": 0
        },
        
        # Employee Benefits
        {
            "line_number": 60,
            "line_label": "Employees Benefit Expenses",
            "line_code": "EMP",
            "line_type": "Account Aggregate",
            "account_mapping_method": "Financial Reporting Group",
            "financial_reporting_group": "Employees Benefit Expenses",
            "sign_multiplier": "1",
            "indent_level": 0,
            "is_bold": 0,
            "is_total_row": 0,
            "is_subtotal_row": 0,
            "hide_if_zero": 0,
            "show_percentage": 0
        },
        
        # EBITDA
        {
            "line_number": 70,
            "line_label": "EBITDA",
            "line_code": "EBITDA",
            "line_type": "Calculated",
            "calculation_formula": "GP - ADMIN - REPAIR - SELL - EMP",
            "sign_multiplier": "1",
            "indent_level": 0,
            "is_bold": 1,
            "is_total_row": 0,
            "is_subtotal_row": 1,
            "hide_if_zero": 0,
            "show_percentage": 0
        },
        
        # Depreciation & Amortisation
        {
            "line_number": 80,
            "line_label": "Depreciation & Amortisation Expenses",
            "line_code": "DEPR",
            "line_type": "Account Aggregate",
            "account_mapping_method": "Financial Reporting Group",
            "financial_reporting_group": "Depreciation and amortisation expenses",
            "sign_multiplier": "1",
            "indent_level": 0,
            "is_bold": 0,
            "is_total_row": 0,
            "is_subtotal_row": 0,
            "hide_if_zero": 0,
            "show_percentage": 0
        },
        
        # Impairment
        {
            "line_number": 85,
            "line_label": "Impairment Charges",
            "line_code": "IMP",
            "line_type": "Account Aggregate",
            "account_mapping_method": "Financial Reporting Group",
            "financial_reporting_group": "Impairment charges",
            "sign_multiplier": "1",
            "indent_level": 0,
            "is_bold": 0,
            "is_total_row": 0,
            "is_subtotal_row": 0,
            "hide_if_zero": 0,
            "show_percentage": 0
        },
        
        # EBIT
        {
            "line_number": 90,
            "line_label": "EBIT",
            "line_code": "EBIT",
            "line_type": "Calculated",
            "calculation_formula": "EBITDA - DEPR - IMP",
            "sign_multiplier": "1",
            "indent_level": 0,
            "is_bold": 1,
            "is_total_row": 0,
            "is_subtotal_row": 1,
            "hide_if_zero": 0,
            "show_percentage": 0
        },
        
        # Finance Charges
        {
            "line_number": 100,
            "line_label": "Finance Charges",
            "line_code": "FIN",
            "line_type": "Account Aggregate",
            "account_mapping_method": "Financial Reporting Group",
            "financial_reporting_group": "Finance charges",
            "sign_multiplier": "1",
            "indent_level": 0,
            "is_bold": 0,
            "is_total_row": 0,
            "is_subtotal_row": 0,
            "hide_if_zero": 0,
            "show_percentage": 0
        },
        
        # Operating Profit
        {
            "line_number": 110,
            "line_label": "Operating Profit",
            "line_code": "OP",
            "line_type": "Calculated",
            "calculation_formula": "EBIT - FIN",
            "sign_multiplier": "1",
            "indent_level": 0,
            "is_bold": 1,
            "is_total_row": 0,
            "is_subtotal_row": 1,
            "hide_if_zero": 0,
            "show_percentage": 0
        },
        
        # Other Income
        {
            "line_number": 120,
            "line_label": "Other Income",
            "line_code": "OTHER",
            "line_type": "Account Aggregate",
            "account_mapping_method": "Financial Reporting Group",
            "financial_reporting_group": "Other Income",
            "sign_multiplier": "1",
            "indent_level": 0,
            "is_bold": 0,
            "is_total_row": 0,
            "is_subtotal_row": 0,
            "hide_if_zero": 0,
            "show_percentage": 0
        },
        
        # Blank line
        {
            "line_number": 125,
            "line_label": "",
            "line_type": "Blank Line"
        },
        
        # Profit Before Tax
        {
            "line_number": 130,
            "line_label": "Profit Before Tax",
            "line_code": "PBT",
            "line_type": "Calculated",
            "calculation_formula": "OP + OTHER",
            "sign_multiplier": "1",
            "indent_level": 0,
            "is_bold": 1,
            "is_total_row": 1,
            "is_subtotal_row": 0,
            "hide_if_zero": 0,
            "show_percentage": 0
        }
    ]
    
    # Add lines to template
    for line_data in lines:
        line = template.append("report_lines", line_data)
    
    # Save template
    template.save()
    frappe.db.commit()
    
    print(f"✓ Template '{template.template_name}' created successfully with {len(lines)} lines")
    print(f"  - Report Type: {template.report_type}")
    print(f"  - Comparison Enabled: {template.show_comparison}")
    print(f"  - Budget Comparison Enabled: {template.enable_budget_comparison}")
    
    return template.name


def create_sample_balance_sheet_template():
    """
    Create a sample Balance Sheet template
    """
    
    print("\nCreating 'Standard Balance Sheet Template'...")
    
    if frappe.db.exists("Financial Report Template", "Standard Balance Sheet"):
        print("Template already exists. Skipping...")
        return
    
    template = frappe.new_doc("Financial Report Template")
    template.template_name = "Standard Balance Sheet"
    template.report_type = "Balance Sheet"
    template.is_default = 1
    template.is_active = 1
    template.description = "Standard Balance Sheet with Assets, Liabilities, and Equity"
    template.report_title = "Statement of Financial Position"
    template.show_comparison = 1
    template.enable_budget_comparison = 0
    
    # Excel settings
    template.excel_header_color = "#4472C4"
    template.excel_total_row_color = "#E7E6E6"
    template.excel_subtotal_color = "#F2F2F2"
    template.show_zero_values = 0
    template.decimal_places = 2
    template.thousands_separator = 1
    
    # Define basic balance sheet structure
    lines = [
        # ASSETS Header
        {
            "line_number": 10,
            "line_label": "ASSETS",
            "line_type": "Header",
            "is_bold": 1
        },
        
        # Current Assets
        {
            "line_number": 20,
            "line_label": "Current Assets",
            "line_code": "CA",
            "line_type": "Account Aggregate",
            "account_mapping_method": "Root Type",
            "root_type_filter": "Asset",
            "sign_multiplier": "1",
            "indent_level": 1,
            "is_bold": 1
        },
        
        # Total Assets
        {
            "line_number": 100,
            "line_label": "TOTAL ASSETS",
            "line_code": "TA",
            "line_type": "Calculated",
            "calculation_formula": "CA",
            "is_bold": 1,
            "is_total_row": 1
        },
        
        # Blank
        {
            "line_number": 110,
            "line_label": "",
            "line_type": "Blank Line"
        },
        
        # LIABILITIES Header
        {
            "line_number": 200,
            "line_label": "LIABILITIES",
            "line_type": "Header",
            "is_bold": 1
        },
        
        # Current Liabilities
        {
            "line_number": 210,
            "line_label": "Current Liabilities",
            "line_code": "CL",
            "line_type": "Account Aggregate",
            "account_mapping_method": "Root Type",
            "root_type_filter": "Liability",
            "sign_multiplier": "1",
            "indent_level": 1,
            "is_bold": 1
        },
        
        # Total Liabilities
        {
            "line_number": 300,
            "line_label": "TOTAL LIABILITIES",
            "line_code": "TL",
            "line_type": "Calculated",
            "calculation_formula": "CL",
            "is_bold": 1,
            "is_total_row": 1
        },
        
        # Blank
        {
            "line_number": 310,
            "line_label": "",
            "line_type": "Blank Line"
        },
        
        # EQUITY Header
        {
            "line_number": 400,
            "line_label": "EQUITY",
            "line_type": "Header",
            "is_bold": 1
        },
        
        # Equity
        {
            "line_number": 410,
            "line_label": "Total Equity",
            "line_code": "EQ",
            "line_type": "Account Aggregate",
            "account_mapping_method": "Root Type",
            "root_type_filter": "Equity",
            "sign_multiplier": "1",
            "indent_level": 1,
            "is_bold": 1
        },
        
        # Blank
        {
            "line_number": 490,
            "line_label": "",
            "line_type": "Blank Line"
        },
        
        # Total Liabilities & Equity
        {
            "line_number": 500,
            "line_label": "TOTAL LIABILITIES & EQUITY",
            "line_code": "TLE",
            "line_type": "Calculated",
            "calculation_formula": "TL + EQ",
            "is_bold": 1,
            "is_total_row": 1
        }
    ]
    
    for line_data in lines:
        template.append("report_lines", line_data)
    
    template.save()
    frappe.db.commit()
    
    print(f"✓ Template '{template.template_name}' created successfully with {len(lines)} lines")


def run_migration():
    """
    Main migration function
    """
    print("=" * 70)
    print("FINANCIAL REPORT TEMPLATE MIGRATION")
    print("=" * 70)
    
    try:
        # Create Standard P&L Template
        pl_template = create_standard_pl_template()
        
        # Create Sample Balance Sheet Template
        create_sample_balance_sheet_template()
        
        print("\n" + "=" * 70)
        print("MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print("\nNext Steps:")
        print("1. Go to 'Financial Report Template' list to view templates")
        print("2. Customize templates as needed")
        print("3. Update your report to use the new template-based system")
        print("4. Test the report with different templates")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        frappe.db.rollback()
        raise


# Run migration if executed directly
if __name__ == "__main__":
    run_migration()