# Copyright (c) 2026, 	kunle Oduntan and contributors
# For license information, please see license.txt

# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt
import re

def execute(filters=None):
    """
    Financial Report by Dimension - DEBUG VERSION
    Let's see what's actually happening
    """
    if not filters:
        filters = {}
    
    # Validate
    if not filters.get("template"):
        frappe.throw(_("Please select a Financial Report Template"))
    
    if not filters.get("company"):
        frappe.throw(_("Please select a Company"))
    
    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw(_("Please select dates"))
    
    company = filters.get("company")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    
    # DEBUG: Check if we have GL entries
    gl_check = frappe.db.sql("""
        SELECT COUNT(*) as count
        FROM `tabGL Entry`
        WHERE company = %(company)s
        AND posting_date BETWEEN %(from_date)s AND %(to_date)s
    """, {"company": company, "from_date": from_date, "to_date": to_date}, as_dict=1)
    
    frappe.msgprint(f"DEBUG: Found {gl_check[0].count} GL entries in date range")
    
    # DEBUG: Check cost centers
    cost_centers = []
    if filters.get("parent_cost_center"):
        cost_centers = frappe.db.sql("""
            SELECT name
            FROM `tabCost Center`
            WHERE parent_cost_center = %(parent)s
            ORDER BY name
        """, {"parent": filters.get("parent_cost_center")}, as_dict=1)
        
        frappe.msgprint(f"DEBUG: Found {len(cost_centers)} cost centers under {filters.get('parent_cost_center')}")
    
    cost_center_names = [cc.name for cc in cost_centers]
    
    # Load template
    template = frappe.get_doc("Financial Report Template", filters.get("template"))
    
    frappe.msgprint(f"DEBUG: Template has {len(template.report_lines)} lines")
    
    # Build columns
    columns = [{"label": "Account", "fieldname": "account", "fieldtype": "Data", "width": 300}]
    
    for cc in cost_center_names:
        columns.append({
            "label": cc,
            "fieldname": sanitize_fieldname(cc),
            "fieldtype": "Currency",
            "width": 120
        })
    
    columns.append({"label": "Total", "fieldname": "total", "fieldtype": "Currency", "width": 150})
    
    # Build data
    data = []
    
    for line in sorted(template.report_lines, key=lambda x: x.line_number):
        
        # Skip blank and header for now
        if line.line_type == "Blank Line":
            data.append({"account": ""})
            continue
        
        if line.line_type == "Header":
            row = {"account": line.line_label}
            row["_style"] = "font-weight: bold;"
            data.append(row)
            continue
        
        # Account line
        if line.line_type == "Account Aggregate":
            # Get accounts
            accounts = get_accounts_debug(line, company)
            
            if not accounts:
                data.append({
                    "account": f"{line.line_label} - NO ACCOUNTS FOUND",
                    "total": 0
                })
                continue
            
            # Show what we found
            frappe.msgprint(f"Line: {line.line_label}, Method: {line.account_mapping_method}, Found {len(accounts)} accounts")
            
            row = {"account": line.line_label}
            row_total = 0
            
            # Test query for first cost center or total
            if cost_center_names:
                cc = cost_center_names[0]
                
                # Test query
                test_result = frappe.db.sql("""
                    SELECT 
                        SUM(debit - credit) as balance
                    FROM `tabGL Entry`
                    WHERE account IN %(accounts)s
                    AND cost_center = %(cost_center)s
                    AND posting_date BETWEEN %(from_date)s AND %(to_date)s
                    AND company = %(company)s
                """, {
                    "accounts": accounts,
                    "cost_center": cc,
                    "from_date": from_date,
                    "to_date": to_date,
                    "company": company
                }, as_dict=1)
                
                balance = flt(test_result[0].balance) if test_result else 0
                frappe.msgprint(f"Test query for {line.line_label} + {cc}: Balance = {balance}")
                
                # Query all cost centers
                for cc in cost_center_names:
                    cc_fieldname = sanitize_fieldname(cc)
                    
                    result = frappe.db.sql("""
                        SELECT SUM(debit - credit) as balance
                        FROM `tabGL Entry`
                        WHERE account IN %(accounts)s
                        AND cost_center = %(cost_center)s
                        AND posting_date BETWEEN %(from_date)s AND %(to_date)s
                        AND company = %(company)s
                    """, {
                        "accounts": accounts,
                        "cost_center": cc,
                        "from_date": from_date,
                        "to_date": to_date,
                        "company": company
                    }, as_dict=1)
                    
                    balance = flt(result[0].balance) if result else 0
                    
                    # Apply sign
                    sign = -1 if line.sign_multiplier == "-1" else 1
                    value = balance * sign
                    
                    row[cc_fieldname] = value
                    row_total += value
            else:
                # No cost centers - get total
                result = frappe.db.sql("""
                    SELECT SUM(debit - credit) as balance
                    FROM `tabGL Entry`
                    WHERE account IN %(accounts)s
                    AND posting_date BETWEEN %(from_date)s AND %(to_date)s
                    AND company = %(company)s
                """, {
                    "accounts": accounts,
                    "from_date": from_date,
                    "to_date": to_date,
                    "company": company
                }, as_dict=1)
                
                balance = flt(result[0].balance) if result else 0
                sign = -1 if line.sign_multiplier == "-1" else 1
                row_total = balance * sign
                
                frappe.msgprint(f"{line.line_label}: Total balance = {balance}, After sign = {row_total}")
            
            row["total"] = row_total
            data.append(row)
    
    return columns, data


def sanitize_fieldname(name):
    """Convert name to valid fieldname"""
    fieldname = re.sub(r'[^a-zA-Z0-9_]', '_', str(name))
    fieldname = re.sub(r'_+', '_', fieldname)
    fieldname = fieldname.strip('_').lower()
    if fieldname and not fieldname[0].isalpha():
        fieldname = 'cc_' + fieldname
    return fieldname


def get_accounts_debug(line, company):
    """Get accounts with detailed logging"""
    
    method = line.account_mapping_method
    
    frappe.msgprint(f"Getting accounts for: {line.line_label}, Method: {method}")
    
    if method == "Specific Accounts":
        if not line.specific_accounts:
            frappe.msgprint("No specific accounts defined")
            return []
        
        accounts = [acc.strip() for acc in line.specific_accounts.split(',')]
        frappe.msgprint(f"Specific accounts: {accounts}")
        return accounts
    
    elif method == "Account Numbers Pattern":
        if not line.account_number_pattern:
            frappe.msgprint("No pattern defined")
            return []
        
        pattern = line.account_number_pattern
        frappe.msgprint(f"Pattern: {pattern}")
        
        # Handle range (4000-4999)
        if '-' in pattern and not pattern.startswith('-'):
            parts = pattern.split('-')
            if len(parts) == 2:
                try:
                    from_num = int(parts[0].strip())
                    to_num = int(parts[1].strip())
                    
                    accounts = frappe.db.sql("""
                        SELECT name, account_number
                        FROM `tabAccount`
                        WHERE company = %(company)s
                        AND is_group = 0
                        AND account_number IS NOT NULL
                    """, {"company": company}, as_dict=1)
                    
                    result = []
                    for acc in accounts:
                        try:
                            acc_num = int(acc.account_number)
                            if from_num <= acc_num <= to_num:
                                result.append(acc.name)
                        except:
                            pass
                    
                    frappe.msgprint(f"Range {from_num}-{to_num} matched {len(result)} accounts")
                    if result:
                        frappe.msgprint(f"Sample accounts: {result[:3]}")
                    
                    return result
                except Exception as e:
                    frappe.msgprint(f"Range parse error: {str(e)}")
        
        # LIKE pattern
        accounts = frappe.db.sql("""
            SELECT name
            FROM `tabAccount`
            WHERE company = %(company)s
            AND is_group = 0
            AND (account_number LIKE %(pattern)s OR name LIKE %(pattern)s)
        """, {"company": company, "pattern": f"%{pattern}%"}, as_dict=1)
        
        result = [acc.name for acc in accounts]
        frappe.msgprint(f"LIKE pattern matched {len(result)} accounts")
        return result
    
    elif method == "Root Type":
        if not line.root_type_filter:
            frappe.msgprint("No root type specified")
            return []
        
        accounts = frappe.db.sql("""
            SELECT name
            FROM `tabAccount`
            WHERE company = %(company)s
            AND root_type = %(root_type)s
            AND is_group = 0
        """, {"company": company, "root_type": line.root_type_filter}, as_dict=1)
        
        result = [acc.name for acc in accounts]
        frappe.msgprint(f"Root type {line.root_type_filter} matched {len(result)} accounts")
        return result
    
    frappe.msgprint(f"Unknown mapping method: {method}")
    return []