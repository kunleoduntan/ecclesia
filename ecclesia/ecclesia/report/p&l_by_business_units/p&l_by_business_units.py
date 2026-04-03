# Copyright (c) 2026, 	kunle Oduntan and contributors
# For license information, please see license.txt

# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

def execute(filters=None):
    """
    P&L by Business Units - Production Optimized
    Keeps original structure, adds efficiency and Excel export
    """
    if not filters:
        filters = {}

    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    company = filters.get("company")
    group_cost_center = filters.get("cost_center")
    hide_detail = int(filters.get("hide_detail") or 0)
    share_corporate_cost = int(filters.get("share_corporate_cost") or 0)
    selected_cc_to_share = filters.get("select_cc_to_share")

    # Get child cost centers
    cost_centers = frappe.get_all(
        "Cost Center", 
        filters={"parent_cost_center": group_cost_center}, 
        fields=["name"],
        order_by="name"
    )
    cost_center_names = [cc.name for cc in cost_centers]

    # Build columns
    columns = [{"label": "Account Name", "fieldname": "account_name", "fieldtype": "Data", "width": 250}]
    columns = columns + [{"label": cc, "fieldname": cc, "fieldtype": "Currency", "width": 150} for cc in cost_center_names]
    columns.append({"label": "Total", "fieldname": "total", "fieldtype": "Currency", "width": 150})

    # Parent accounts
    parent_accounts = [
        "Revenue from ordinary line of Business",
        "Revenue from Non line of business", 
        "Cost of Sales", 
        "Administrative Expenses",
        "Repairs & maintenance Expenses", 
        "Depreciation & amortisation expenses",
        "Impairment charges", 
        "Selling, distribution & marketing expenses",
        "Employees Benefit Expenses", 
        "Finance charges"
    ]

    # Get and group accounts
    accounts = frappe.get_all("Account", filters={"company": company}, fields=["name", "parent_account"])
    grouped_accounts = {}
    for acc in accounts:
        clean_parent = extract_account_name(acc.parent_account or "Unspecified")
        if clean_parent in parent_accounts:
            if clean_parent not in grouped_accounts:
                grouped_accounts[clean_parent] = []
            grouped_accounts[clean_parent].append(acc.name)

    data = []
    total_map = {}

    # Build data based on hide_detail
    if hide_detail == 0:
        # Show details
        for parent in parent_accounts:
            if parent not in grouped_accounts:
                continue

            data.append({"account_name": f"▶ {parent}"})
            group_totals = dict((cc, 0) for cc in cost_center_names)

            for acc_name in grouped_accounts[parent]:
                gl_url = f"/app/query-report/General Ledger?company={company}&account={acc_name}&from_date={from_date}&to_date={to_date}"
                row = {"account_name": f'<a href="{gl_url}" style="padding-left:12px;" target="_blank">{acc_name}</a>'}
                total = 0
                
                for cc in cost_center_names:
                    result = frappe.db.sql("""
                        SELECT SUM(gle.debit - gle.credit) AS balance
                        FROM `tabGL Entry` gle
                        WHERE gle.account = %s AND gle.cost_center = %s
                        AND gle.posting_date BETWEEN %s AND %s AND gle.company = %s
                    """, (acc_name, cc, from_date, to_date, company), as_dict=1)
                    
                    balance = result[0]["balance"] or 0
                    val = -balance if "Revenue" in parent else balance
                    row[cc] = val
                    group_totals[cc] = group_totals[cc] + balance
                    total = total + val
                
                row["total"] = total
                data.append(row)

            # Total row
            total_row = {"account_name": f"Total - {parent}"}
            group_total = 0
            for cc in cost_center_names:
                val = -group_totals[cc] if "Revenue" in parent else group_totals[cc]
                total_row[cc] = val
                group_total = group_total + val
            total_row["total"] = group_total
            total_row["_style"] = "background-color: #FFFF99; font-weight: bold;"
            data.append(total_row)
            data.append({"account_name": ""})
            total_map[parent] = total_row

        # Shared cost detail
        if share_corporate_cost == 1 and selected_cc_to_share:
            distribution_table = frappe.get_all(
                "Cost Center Distribution", 
                filters={"parent": company}, 
                fields=["cost_center", "distribution"]
            )
            
            shared_detail_row = {"account_name": "Shared Corporate Cost"}
            shared_detail_total = 0
            total_cop_expense = 0
            
            for parent in parent_accounts:
                row = total_map.get(parent, {})
                total_cop_expense = total_cop_expense + (row.get(selected_cc_to_share) or 0)

            for dist in distribution_table:
                cc_name = dist.cost_center
                percent = dist.distribution or 0
                shared_amount = -1 * total_cop_expense * percent / 100
                shared_detail_row[cc_name] = shared_amount
                shared_detail_total = shared_detail_total + shared_amount

            shared_detail_row["total"] = shared_detail_total
            shared_detail_row["_style"] = "background-color: #FADBD8; font-weight: bold;"
            data.append(shared_detail_row)
    
    else:
        # Hide details - summary only
        for parent in parent_accounts:
            if parent not in grouped_accounts:
                continue
            
            group_totals = dict((cc, 0) for cc in cost_center_names)
            
            for acc_name in grouped_accounts[parent]:
                for cc in cost_center_names:
                    result = frappe.db.sql("""
                        SELECT SUM(gle.debit - gle.credit) AS balance
                        FROM `tabGL Entry` gle
                        WHERE gle.account = %s AND gle.cost_center = %s
                        AND gle.posting_date BETWEEN %s AND %s AND gle.company = %s
                    """, (acc_name, cc, from_date, to_date, company), as_dict=1)
                    
                    balance = result[0]["balance"] or 0
                    group_totals[cc] = group_totals[cc] + balance
            
            total_row = {"account_name": f"Total - {parent}"}
            group_total = 0
            for cc in cost_center_names:
                val = -group_totals[cc] if "Revenue" in parent else group_totals[cc]
                total_row[cc] = val
                group_total = group_total + val
            total_row["total"] = group_total
            total_row["_style"] = "background-color: #FFFF99; font-weight: bold;"
            total_map[parent] = total_row

    # Summary rows
    summary_rows = [
        ("Revenue", [("Revenue from ordinary line of Business", -1), ("Revenue from Non line of business", -1)]),
        ("Cost of Sales", [("Cost of Sales", 1)]),
        ("Gross Profit", [("Revenue from ordinary line of Business", -1), ("Revenue from Non line of business", -1), ("Cost of Sales", -1)]),
        ("Administrative Expenses", [("Administrative Expenses", 1), ("Repairs & maintenance Expenses", 1)]),
        ("Selling & Distribution Expenses", [("Selling, distribution & marketing expenses", 1)]),
        ("Employees Benefits", [("Employees Benefit Expenses", 1)]),
        ("EBITDA", [
            ("Revenue from ordinary line of Business", -1),
            ("Revenue from Non line of business", -1),
            ("Cost of Sales", -1),
            ("Administrative Expenses", -1),
            ("Repairs & maintenance Expenses", -1),
            ("Selling, distribution & marketing expenses", -1),
            ("Employees Benefit Expenses", -1)
        ]),
        ("Depreciation & Amortisation Expenses", [
            ("Depreciation & amortisation expenses", 1),
            ("Impairment charges", 1)
        ]),
        ("EBIT", [
            ("Revenue from ordinary line of Business", -1),
            ("Revenue from Non line of business", -1),
            ("Cost of Sales", -1),
            ("Administrative Expenses", -1),
            ("Repairs & maintenance Expenses", -1),
            ("Selling, distribution & marketing expenses", -1),
            ("Employees Benefit Expenses", -1),
            ("Depreciation & amortisation expenses", -1),
            ("Impairment charges", -1)
        ]),
        ("Finance Charge", [("Finance charges", 1)]),
        ("Operating Profit", [
            ("Revenue from ordinary line of Business", -1),
            ("Revenue from Non line of business", -1),
            ("Cost of Sales", -1),
            ("Administrative Expenses", -1),
            ("Repairs & maintenance Expenses", -1),
            ("Selling, distribution & marketing expenses", -1),
            ("Employees Benefit Expenses", -1),
            ("Depreciation & amortisation expenses", -1),
            ("Impairment charges", -1),
            ("Finance charges", -1)
        ])
    ]

    summary_result_rows = []
    operating_profit_row = {}
    
    for label, components in summary_rows:
        row = compute_formula_row(label, components, cost_center_names, list(total_map.values()))
        if label in ["Gross Profit", "EBITDA", "EBIT", "Operating Profit"]:
            for cc in cost_center_names + ["total"]:
                row[cc] = row.get(cc, 0)
            row["_style"] = "background-color: #CCE5FF; font-weight: bold;"
        summary_result_rows.append(row)
        if label == "Operating Profit":
            operating_profit_row = row

    # Cost allocation for summary
    shared_row = None
    if share_corporate_cost == 1 and hide_detail == 1 and selected_cc_to_share:
        distribution_table = frappe.get_all(
            "Cost Center Distribution", 
            filters={"parent": company}, 
            fields=["cost_center", "distribution"]
        )
        
        shared_row = {"account_name": "Shared Corporate Cost"}
        total_to_share = operating_profit_row.get(selected_cc_to_share, 0) or 0
        total_shared = 0

        for dist in distribution_table:
            cc_name = dist.cost_center
            percent = dist.distribution or 0
            shared_amount = -1 * total_to_share * percent / 100
            shared_row[cc_name] = shared_amount
            total_shared = total_shared + shared_amount

        shared_row["total"] = total_shared
        shared_row["_style"] = "background-color: #FADBD8; font-weight: bold;"
        summary_result_rows.append(shared_row)

    # PBT
    if shared_row:
        pbt_row = {"account_name": "Profit Before Tax"}
        total_pbt = 0
        for cc in cost_center_names:
            op_val = operating_profit_row.get(cc, 0)
            shared_val = shared_row.get(cc, 0)
            pbt = op_val - shared_val
            pbt_row[cc] = pbt
            total_pbt = total_pbt + pbt
        pbt_row["total"] = total_pbt
        pbt_row["_style"] = "background-color: #D4EFDF; font-weight: bold;"
        summary_result_rows.append(pbt_row)

    data = data + summary_result_rows

    return columns, data


def extract_account_name(full_name):
    """Extract account name from full path"""
    parts = full_name.split(' - ')
    return parts[1] if len(parts) >= 2 else full_name


def compute_formula_row(label, components, cost_centers, data):
    """Compute calculated row"""
    row = {"account_name": label}
    row_total = 0

    for cc in cost_centers:
        subtotal = 0
        for comp_label, sign in components:
            match = None
            for r in data:
                if f"Total - {comp_label}" in str(r.get("account_name", "")):
                    match = r
                    break
            if match:
                val = match.get(cc) or 0
                subtotal = subtotal + sign * val
        row[cc] = subtotal
        row_total = row_total + subtotal

    row["total"] = row_total
    return row


@frappe.whitelist()
def export_to_excel(filters):
    """Export report to beautifully formatted Excel"""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    import os
    from frappe.utils.file_manager import save_file
    
    # Get report data
    columns, data = execute(filters)
    
    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "P&L by Business Units"
    
    # Write headers
    for col_idx, col in enumerate(columns, 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.value = col["label"]
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")
    
    # Write data
    for row_idx, row_data in enumerate(data, 2):
        account_name = row_data.get("account_name", "")
        
        # Clean HTML from account name
        import re
        clean_name = re.sub('<[^<]+?>', '', account_name)
        
        for col_idx, col in enumerate(columns, 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            fieldname = col["fieldname"]
            value = row_data.get(fieldname)
            
            if col_idx == 1:
                cell.value = clean_name
                cell.alignment = Alignment(horizontal="left")
            else:
                cell.value = value if value else 0
                cell.number_format = '#,##0.00'
                cell.alignment = Alignment(horizontal="right")
            
            # Apply styling based on row type
            style = row_data.get("_style", "")
            
            if "background-color: #FFFF99" in style:  # Total rows
                cell.fill = PatternFill(start_color="FFFF99", end_color="FFFF99", fill_type="solid")
                cell.font = Font(bold=True)
            elif "background-color: #CCE5FF" in style:  # Key metrics
                cell.fill = PatternFill(start_color="CCE5FF", end_color="CCE5FF", fill_type="solid")
                cell.font = Font(bold=True)
            elif "background-color: #FADBD8" in style:  # Cost allocation
                cell.fill = PatternFill(start_color="FADBD8", end_color="FADBD8", fill_type="solid")
                cell.font = Font(bold=True)
            elif "background-color: #D4EFDF" in style:  # PBT
                cell.fill = PatternFill(start_color="D4EFDF", end_color="D4EFDF", fill_type="solid")
                cell.font = Font(bold=True)
    
    # Auto-adjust column widths
    ws.column_dimensions['A'].width = 40
    for col_idx in range(2, len(columns) + 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = 15
    
    # Save file
    file_path = f"/tmp/pl_by_business_units_{frappe.utils.now()}.xlsx"
    wb.save(file_path)
    
    # Upload to frappe
    with open(file_path, 'rb') as f:
        file_doc = save_file(
            fname=f"pl_by_business_units_{frappe.utils.now()}.xlsx",
            content=f.read(),
            dt="User",
            dn=frappe.session.user,
            is_private=1
        )
    
    # Clean up temp file
    os.remove(file_path)
    
    return {"file_url": file_doc.file_url}