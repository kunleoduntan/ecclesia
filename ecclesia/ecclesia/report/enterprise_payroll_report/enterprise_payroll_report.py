# Copyright (c) 2026, 	kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, formatdate, get_first_day, get_last_day, nowdate, add_months, getdate
from frappe import _
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, Reference
import json
from datetime import datetime

def execute(filters=None):
    filters = filters or {}
    validate_filters(filters)
    
    # Get dynamic salary components
    salary_components = get_salary_components()
    
    columns = get_columns(salary_components, filters)
    data = get_data(filters, salary_components)
    
    # Add chart
    chart = get_chart_data(data, filters)
    
    return columns, data, None, chart

def validate_filters(filters):
    if not filters.get("company"):
        frappe.throw(_("Please select a Company"))
    
    if filters.get("report_type") == "Monthly":
        if not filters.get("from_date") or not filters.get("to_date"):
            frappe.throw(_("Please select From Date and To Date for Monthly report"))
    elif filters.get("report_type") == "Yearly":
        if not filters.get("year"):
            frappe.throw(_("Please select Year for Yearly report"))

def get_salary_components():
    """Get all salary components where show_on_payroll_report = 1"""
    components = frappe.get_all(
        "Salary Component",
        filters={"show_on_payroll_report": 1},
        fields=["name", "salary_component_abbr", "type"],
        order_by="type desc, name"
    )
    
    return components

def get_columns(salary_components, filters):
    """Build dynamic columns based on salary components"""
    
    columns = [
        {
            "label": _("Employee ID"),
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 120
        },
        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "width": 200
        }
    ]
    
    # Add employee detail columns
    employee_fields = [
        {"label": _("Department"), "fieldname": "department", "width": 150},
        {"label": _("Designation"), "fieldname": "designation", "width": 150},
        {"label": _("Cost Center"), "fieldname": "cost_center", "width": 150},
        {"label": _("Branch"), "fieldname": "branch", "width": 120},
        {"label": _("Employment Type"), "fieldname": "employment_type", "width": 120},
    ]
    
    columns.extend(employee_fields)
    
    # Add salary slip info for monthly report
    if filters.get("report_type") == "Monthly":
        columns.append({
            "label": _("Salary Slip"),
            "fieldname": "salary_slip",
            "fieldtype": "Link",
            "options": "Salary Slip",
            "width": 140
        })
        columns.append({
            "label": _("Posting Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 110
        })
    
    # Add dynamic salary component columns
    for component in salary_components:
        abbr = component.get("salary_component_abbr") or component.get("name")
        columns.append({
            "label": _(abbr),
            "fieldname": f"component_{frappe.scrub(component.name)}",
            "fieldtype": "Currency",
            "width": 120
        })
    
    # Add totals
    columns.extend([
        {
            "label": _("Gross Pay"),
            "fieldname": "gross_pay",
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "label": _("Total Deductions"),
            "fieldname": "total_deductions",
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "label": _("Net Pay"),
            "fieldname": "net_pay",
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "label": _("Company"),
            "fieldname": "company",
            "width": 200
        }
    ])
    
    return columns

def get_data(filters, salary_components):
    """Get payroll data based on filters"""
    
    data = []
    
    if filters.get("report_type") == "Yearly":
        data = get_yearly_data(filters, salary_components)
    else:
        data = get_monthly_data(filters, salary_components)
    
    # Apply grouping if requested
    if filters.get("group_by"):
        data = apply_grouping(data, filters.get("group_by"))
    
    return data

def get_monthly_data(filters, salary_components):
    """Get data for monthly report"""
    
    data = []
    
    # Build filters for Salary Slip
    slip_filters = {
        "docstatus": 1,
        "company": filters.get("company"),
        "start_date": ["between", [filters.get("from_date"), filters.get("to_date")]]
    }
    
    if filters.get("employee"):
        slip_filters["employee"] = filters.get("employee")
    if filters.get("department"):
        slip_filters["department"] = filters.get("department")
    if filters.get("cost_center"):
        # Get employees with this cost center
        employees_with_cc = frappe.get_all(
            "Employee",
            filters={"payroll_cost_center": filters.get("cost_center")},
            pluck="name"
        )
        if employees_with_cc:
            slip_filters["employee"] = ["in", employees_with_cc]
        else:
            return []  # No employees with this cost center
    if filters.get("branch"):
        slip_filters["branch"] = filters.get("branch")
    
    slips = frappe.get_all(
        "Salary Slip",
        filters=slip_filters,
        fields=[
            "name", "employee", "employee_name", "department", "designation",
            "branch", "posting_date", "gross_pay", "total_deduction", "net_pay",
            "company"
        ],
        order_by="department, employee, posting_date"
    )
    
    if not slips:
        frappe.msgprint(_("No salary slips found for the selected filters"))
        return data
    
    for slip in slips:
        # Get employee details
        emp_details = frappe.db.get_value(
            "Employee",
            slip.employee,
            ["payroll_cost_center", "employment_type"],
            as_dict=True
        ) or {}
        
        row = {
            "employee": slip.employee,
            "employee_name": slip.employee_name,
            "department": slip.department,
            "designation": slip.designation,
            "cost_center": emp_details.get("payroll_cost_center") or "",
            "branch": slip.branch or "",
            "employment_type": emp_details.get("employment_type") or "",
            "salary_slip": slip.name,
            "posting_date": slip.posting_date,
            "gross_pay": flt(slip.gross_pay),
            "total_deductions": flt(slip.total_deduction),
            "net_pay": flt(slip.net_pay),
            "company": slip.company
        }
        
        # Get component amounts
        for component in salary_components:
            table = "earnings" if component.type == "Earning" else "deductions"
            amount = get_component_amount(slip.name, table, component.name)
            row[f"component_{frappe.scrub(component.name)}"] = flt(amount)
        
        data.append(row)
    
    return data

def get_yearly_data(filters, salary_components):
    """Get aggregated data for yearly report"""
    
    data = []
    year = filters.get("year")
    
    # Build date range for the year
    from_date = f"{year}-01-01"
    to_date = f"{year}-12-31"
    
    # Build filters for Salary Slip
    slip_filters = {
        "docstatus": 1,
        "company": filters.get("company"),
        "start_date": ["between", [from_date, to_date]]
    }
    
    if filters.get("employee"):
        slip_filters["employee"] = filters.get("employee")
    if filters.get("department"):
        slip_filters["department"] = filters.get("department")
    if filters.get("cost_center"):
        # Get employees with this cost center
        employees_with_cc = frappe.get_all(
            "Employee",
            filters={"payroll_cost_center": filters.get("cost_center")},
            pluck="name"
        )
        if employees_with_cc:
            slip_filters["employee"] = ["in", employees_with_cc]
        else:
            return []  # No employees with this cost center
    if filters.get("branch"):
        slip_filters["branch"] = filters.get("branch")
    
    # Get all slips for the year
    slips = frappe.get_all(
        "Salary Slip",
        filters=slip_filters,
        fields=[
            "name", "employee", "employee_name", "department", "designation",
            "branch", "posting_date", "gross_pay", "total_deduction", "net_pay",
            "company"
        ],
        order_by="employee, posting_date"
    )
    
    if not slips:
        frappe.msgprint(_("No salary slips found for the selected year"))
        return data
    
    # Aggregate by employee
    employee_data = {}
    
    for slip in slips:
        if slip.employee not in employee_data:
            # Get employee details
            emp_details = frappe.db.get_value(
                "Employee",
                slip.employee,
                ["payroll_cost_center", "employment_type"],
                as_dict=True
            ) or {}
            
            employee_data[slip.employee] = {
                "employee": slip.employee,
                "employee_name": slip.employee_name,
                "department": slip.department,
                "designation": slip.designation,
                "cost_center": emp_details.get("payroll_cost_center") or "",
                "branch": slip.branch or "",
                "employment_type": emp_details.get("employment_type") or "",
                "gross_pay": 0,
                "total_deductions": 0,
                "net_pay": 0,
                "company": slip.company,
                "slip_count": 0
            }
            
            # Initialize component totals
            for component in salary_components:
                employee_data[slip.employee][f"component_{frappe.scrub(component.name)}"] = 0
        
        # Aggregate amounts
        employee_data[slip.employee]["gross_pay"] += flt(slip.gross_pay)
        employee_data[slip.employee]["total_deductions"] += flt(slip.total_deduction)
        employee_data[slip.employee]["net_pay"] += flt(slip.net_pay)
        employee_data[slip.employee]["slip_count"] += 1
        
        # Aggregate component amounts
        for component in salary_components:
            table = "earnings" if component.type == "Earning" else "deductions"
            amount = get_component_amount(slip.name, table, component.name)
            employee_data[slip.employee][f"component_{frappe.scrub(component.name)}"] += flt(amount)
    
    # Convert to list
    data = list(employee_data.values())
    
    return data

def get_component_amount(salary_slip, table, component_name):
    """Get salary component amount from Salary Detail"""
    rows = frappe.get_all(
        "Salary Detail",
        filters={
            "parent": salary_slip,
            "parenttype": "Salary Slip",
            "parentfield": table,
            "salary_component": component_name
        },
        fields=["amount"]
    )
    return flt(rows[0].amount) if rows else 0.0

def apply_grouping(data, group_by):
    """Apply grouping and add subtotals"""
    
    if not data:
        return data
    
    grouped_data = []
    group_totals = {}
    current_group = None
    
    # Sort data by group field
    data.sort(key=lambda x: x.get(group_by, ""))
    
    for row in data:
        group_value = row.get(group_by, "No Value")
        
        # Add group header
        if current_group != group_value:
            if current_group is not None:
                # Add subtotal for previous group
                grouped_data.append(create_subtotal_row(current_group, group_totals[current_group], group_by))
                grouped_data.append({})  # Blank row
            
            current_group = group_value
            group_totals[current_group] = {
                "gross_pay": 0,
                "total_deductions": 0,
                "net_pay": 0
            }
            
            # Add group header
            grouped_data.append({
                "employee_name": f"{group_by.replace('_', ' ').title()}: {group_value}",
                "indent": 0,
                "is_group_header": True
            })
        
        # Add data row
        grouped_data.append(row)
        
        # Accumulate totals
        group_totals[current_group]["gross_pay"] += flt(row.get("gross_pay", 0))
        group_totals[current_group]["total_deductions"] += flt(row.get("total_deductions", 0))
        group_totals[current_group]["net_pay"] += flt(row.get("net_pay", 0))
    
    # Add final subtotal
    if current_group:
        grouped_data.append(create_subtotal_row(current_group, group_totals[current_group], group_by))
    
    return grouped_data

def create_subtotal_row(group_name, totals, group_by):
    """Create a subtotal row"""
    return {
        "employee_name": f"Total for {group_name}",
        "gross_pay": totals["gross_pay"],
        "total_deductions": totals["total_deductions"],
        "net_pay": totals["net_pay"],
        "indent": 0,
        "is_subtotal": True
    }

def get_chart_data(data, filters):
    """Generate chart data for visualization"""
    if not data or len(data) == 0:
        return None
    
    # Chart by department
    dept_data = {}
    for row in data:
        if row.get("employee") and not row.get("is_group_header") and not row.get("is_subtotal"):
            dept = row.get("department", "No Department")
            if dept not in dept_data:
                dept_data[dept] = {"gross": 0, "net": 0, "deductions": 0}
            
            dept_data[dept]["gross"] += flt(row.get("gross_pay", 0))
            dept_data[dept]["net"] += flt(row.get("net_pay", 0))
            dept_data[dept]["deductions"] += flt(row.get("total_deductions", 0))
    
    if not dept_data:
        return None
    
    return {
        "data": {
            "labels": list(dept_data.keys()),
            "datasets": [
                {"name": "Gross Pay", "values": [dept_data[d]["gross"] for d in dept_data.keys()]},
                {"name": "Net Pay", "values": [dept_data[d]["net"] for d in dept_data.keys()]},
                {"name": "Deductions", "values": [dept_data[d]["deductions"] for d in dept_data.keys()]}
            ]
        },
        "type": "bar",
        "height": 300,
        "colors": ["#4CAF50", "#2196F3", "#FF9800"]
    }

@frappe.whitelist()
def export_excel(filters, data=None):
    """Export beautiful Excel report"""
    
    # Parse filters if string
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    filters = frappe._dict(filters)
    
    # Get salary components
    salary_components = get_salary_components()
    
    # Get fresh data if not provided
    if not data:
        data = get_data(filters, salary_components)
    elif isinstance(data, str):
        data = json.loads(data)
    
    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Payroll Report"
    
    # Define styles
    title_font = Font(bold=True, size=16, color="FFFFFF")
    title_fill = PatternFill(start_color="1F4788", end_color="1F4788", fill_type="solid")
    
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    subheader_font = Font(bold=True, size=10)
    subheader_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    
    data_alignment = Alignment(horizontal="left", vertical="center")
    number_alignment = Alignment(horizontal="right", vertical="center")
    
    border_style = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Company info
    company_name = frappe.db.get_value("Company", filters.get("company"), "company_name")
    
    # Title section
    ws.merge_cells('A1:P1')
    ws['A1'] = f"{company_name} - Payroll Report"
    ws['A1'].font = title_font
    ws['A1'].fill = title_fill
    ws['A1'].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30
    
    # Period info
    ws.merge_cells('A2:P2')
    if filters.get("report_type") == "Yearly":
        ws['A2'] = f"Year: {filters.get('year')}"
    else:
        ws['A2'] = f"Period: {formatdate(filters.get('from_date'))} to {formatdate(filters.get('to_date'))}"
    ws['A2'].alignment = Alignment(horizontal="center")
    ws['A2'].font = Font(size=11)
    
    # Generation date
    ws.merge_cells('A3:P3')
    ws['A3'] = f"Generated on: {formatdate(nowdate())} at {datetime.now().strftime('%H:%M:%S')}"
    ws['A3'].alignment = Alignment(horizontal="center")
    ws['A3'].font = Font(size=9, italic=True, color="666666")
    
    # Headers
    headers = [
        "Employee ID", "Employee Name", "Department", "Designation",
        "Cost Center", "Branch", "Employment Type"
    ]
    
    if filters.get("report_type") == "Monthly":
        headers.extend(["Salary Slip", "Posting Date"])
    
    # Add component headers
    for component in salary_components:
        abbr = component.get("salary_component_abbr") or component.get("name")
        headers.append(abbr)
    
    headers.extend(["Gross Pay", "Total Deductions", "Net Pay", "Company"])
    
    # Write headers
    header_row = 5
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_num)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = border_style
    
    # Write data
    row_num = header_row + 1
    totals = {
        "gross_pay": 0,
        "total_deductions": 0,
        "net_pay": 0,
        "employee_count": 0
    }
    
    # Initialize component totals
    for component in salary_components:
        totals[f"component_{frappe.scrub(component.name)}"] = 0
    
    for item in data:
        if isinstance(item, dict):
            # Group headers
            if item.get("is_group_header"):
                ws.merge_cells(f'A{row_num}:{get_column_letter(len(headers))}{row_num}')
                cell = ws.cell(row=row_num, column=1)
                cell.value = item.get("employee_name")
                cell.font = subheader_font
                cell.fill = subheader_fill
                cell.alignment = data_alignment
                row_num += 1
                continue
            
            # Subtotals
            if item.get("is_subtotal"):
                ws.cell(row=row_num, column=2, value=item.get("employee_name")).font = Font(bold=True)
                
                col_offset = 7 if filters.get("report_type") == "Monthly" else 5
                col_offset += len(salary_components)
                
                ws.cell(row=row_num, column=col_offset + 1, value=flt(item.get("gross_pay"))).font = Font(bold=True)
                ws.cell(row=row_num, column=col_offset + 2, value=flt(item.get("total_deductions"))).font = Font(bold=True)
                ws.cell(row=row_num, column=col_offset + 3, value=flt(item.get("net_pay"))).font = Font(bold=True)
                
                for col in range(2, len(headers) + 1):
                    ws.cell(row=row_num, column=col).fill = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")
                
                row_num += 1
                continue
            
            # Regular data row
            if item.get("employee"):
                col = 1
                ws.cell(row=row_num, column=col, value=item.get("employee"))
                col += 1
                ws.cell(row=row_num, column=col, value=item.get("employee_name"))
                col += 1
                ws.cell(row=row_num, column=col, value=item.get("department"))
                col += 1
                ws.cell(row=row_num, column=col, value=item.get("designation"))
                col += 1
                ws.cell(row=row_num, column=col, value=item.get("cost_center"))
                col += 1
                ws.cell(row=row_num, column=col, value=item.get("branch"))
                col += 1
                ws.cell(row=row_num, column=col, value=item.get("employment_type"))
                col += 1
                
                if filters.get("report_type") == "Monthly":
                    ws.cell(row=row_num, column=col, value=item.get("salary_slip"))
                    col += 1
                    ws.cell(row=row_num, column=col, value=item.get("posting_date"))
                    col += 1
                
                # Write component amounts
                for component in salary_components:
                    amount = flt(item.get(f"component_{frappe.scrub(component.name)}", 0))
                    ws.cell(row=row_num, column=col, value=amount)
                    totals[f"component_{frappe.scrub(component.name)}"] += amount
                    col += 1
                
                ws.cell(row=row_num, column=col, value=flt(item.get("gross_pay")))
                col += 1
                ws.cell(row=row_num, column=col, value=flt(item.get("total_deductions")))
                col += 1
                ws.cell(row=row_num, column=col, value=flt(item.get("net_pay")))
                col += 1
                ws.cell(row=row_num, column=col, value=item.get("company"))
                
                # Apply styles
                for c in range(1, len(headers) + 1):
                    cell = ws.cell(row=row_num, column=c)
                    cell.border = border_style
                    
                    # Currency columns
                    if c > 7 + (2 if filters.get("report_type") == "Monthly" else 0):
                        cell.alignment = number_alignment
                        cell.number_format = '#,##0.00'
                    else:
                        cell.alignment = data_alignment
                
                totals["gross_pay"] += flt(item.get("gross_pay"))
                totals["total_deductions"] += flt(item.get("total_deductions"))
                totals["net_pay"] += flt(item.get("net_pay"))
                totals["employee_count"] += 1
                
                row_num += 1
    
    # Grand total
    total_row = row_num + 1
    ws.cell(row=total_row, column=2, value="GRAND TOTAL").font = Font(bold=True, size=12)
    
    col_offset = 7 if filters.get("report_type") == "Monthly" else 5
    col = col_offset + 1
    
    # Component totals
    for component in salary_components:
        ws.cell(row=total_row, column=col, value=totals[f"component_{frappe.scrub(component.name)}"])
        col += 1
    
    ws.cell(row=total_row, column=col, value=totals["gross_pay"])
    col += 1
    ws.cell(row=total_row, column=col, value=totals["total_deductions"])
    col += 1
    ws.cell(row=total_row, column=col, value=totals["net_pay"])
    
    for c in range(2, len(headers) + 1):
        cell = ws.cell(row=total_row, column=c)
        cell.font = Font(bold=True, size=11)
        cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        cell.font = Font(bold=True, size=11, color="FFFFFF")
        cell.border = border_style
        if c >= col_offset:
            cell.number_format = '#,##0.00'
            cell.alignment = number_alignment
    
    # Summary
    summary_row = total_row + 2
    ws.cell(row=summary_row, column=2, value="Total Employees:").font = Font(bold=True)
    ws.cell(row=summary_row, column=3, value=totals["employee_count"])
    
    # Adjust column widths
    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 25
    for i in range(3, len(headers) + 1):
        ws.column_dimensions[get_column_letter(i)].width = 18
    
    # Freeze panes
    ws.freeze_panes = f'A{header_row + 1}'
    
    # Save to file
    from frappe.utils.file_manager import save_file
    from io import BytesIO
    
    report_name = "Yearly_Payroll" if filters.get("report_type") == "Yearly" else "Monthly_Payroll"
    file_name = f"{report_name}_{filters.get('company')}_{filters.get('year') or formatdate(filters.get('from_date'))}.xlsx"
    
    file_stream = BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)
    
    file_doc = save_file(
        file_name,
        file_stream.read(),
        "Report",
        "Payroll Report",
        is_private=1
    )
    
    return {
        "file_url": file_doc.file_url,
        "file_name": file_name
    }