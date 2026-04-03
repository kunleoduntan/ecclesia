# Copyright (c) 2026, kunleadenuga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate, nowdate
from datetime import datetime
import json

def execute(filters=None):
    """
    Employee Pension Statement
    Shows individual employee pension contribution history from Salary Slips
    """
    
    if not filters:
        filters = {}
    
    validate_filters(filters)
    
    columns = get_columns()
    data = get_data(filters)
    message = get_employee_info_message(filters)
    chart = get_chart_data(data)
    
    return columns, data, message, chart, None


def validate_filters(filters):
    """Validate required filters"""
    if not filters.get("employee"):
        frappe.throw(_("Please select an Employee"))


def get_columns():
    """Define report columns"""
    
    columns = [
        {
            "label": _("Salary Slip"),
            "fieldname": "salary_slip",
            "fieldtype": "Link",
            "options": "Salary Slip",
            "width": 140
        },
        {
            "label": _("Period"),
            "fieldname": "period",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Month"),
            "fieldname": "month",
            "fieldtype": "Data",
            "width": 90
        },
        {
            "label": _("Year"),
            "fieldname": "year",
            "fieldtype": "Int",
            "width": 70
        },
        {
            "label": _("Posting Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 110
        },
        {
            "label": _("Gross Pay"),
            "fieldname": "gross_pay",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Employee (8%)"),
            "fieldname": "employee_contribution",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": _("Employer (10%)"),
            "fieldname": "employer_contribution",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": _("Total"),
            "fieldname": "total",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": _("Cumulative"),
            "fieldname": "cumulative",
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 100
        }
    ]
    
    return columns


def get_component_amount(salary_slip, table, component_name):
    """Get salary component amount from Salary Detail - EXACT COPY from Pension Remittance"""
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


def get_data(filters):
    """Fetch employee pension contribution history from Salary Slips"""
    
    employee = filters.get("employee")
    from_year = filters.get("from_year") or (datetime.now().year - 1)
    to_year = filters.get("to_year") or datetime.now().year
    
    # Build date range
    from_date = f"{from_year}-01-01"
    to_date = f"{to_year}-12-31"
    
    # Build filters for Salary Slip - SAME AS PENSION REMITTANCE
    slip_filters = {
        "docstatus": 1,
        "employee": employee,
        "start_date": ["between", [from_date, to_date]]
    }
    
    # Get salary slips - SAME AS PENSION REMITTANCE
    slips = frappe.get_all(
        "Salary Slip",
        filters=slip_filters,
        fields=[
            "name", "employee", "employee_name",
            "posting_date", "gross_pay", "company", "start_date"
        ],
        order_by="start_date, posting_date"
    )
    
    if not slips:
        frappe.msgprint(_("No salary slips found for this employee in the selected period"))
        return []
    
    data = []
    cumulative = 0
    
    for slip in slips:
        # Get pension amounts - EXACT SAME AS PENSION REMITTANCE
        er = flt(get_component_amount(slip.name, "earnings", "Pension (ER)"))
        ee = flt(get_component_amount(slip.name, "deductions", "Pension (EE)"))
        
        # Only add row if there's pension contribution
        if er > 0 or ee > 0:
            total = er + ee
            cumulative += total
            
            # Extract month and year from start_date
            start_date = getdate(slip.start_date)
            month_name = start_date.strftime("%B")
            year = start_date.year
            period = f"{month_name} {year}"
            
            # Determine status
            status = "Submitted"
            
            row = {
                "salary_slip": slip.name,
                "period": period,
                "month": month_name,
                "year": year,
                "posting_date": slip.posting_date,
                "gross_pay": flt(slip.gross_pay),
                "employee_contribution": ee,
                "employer_contribution": er,
                "total": total,
                "cumulative": cumulative,
                "status": status
            }
            
            data.append(row)
    
    if not data:
        frappe.msgprint(_("No pension contributions found in salary slips for the selected period"))
        return []
    
    # Add summary/total row
    total_row = {
        "salary_slip": "",
        "period": "<b>TOTAL</b>",
        "month": "",
        "year": "",
        "posting_date": "",
        "gross_pay": sum(flt(row.get("gross_pay")) for row in data),
        "employee_contribution": sum(flt(row.get("employee_contribution")) for row in data),
        "employer_contribution": sum(flt(row.get("employer_contribution")) for row in data),
        "total": sum(flt(row.get("total")) for row in data),
        "cumulative": cumulative,
        "status": ""
    }
    data.append(total_row)
    
    return data


def get_chart_data(data):
    """Generate chart showing contribution trends"""
    
    if not data or len(data) < 2:  # Need at least 2 rows (1 data + 1 summary)
        return None
    
    # Remove summary row for chart
    chart_data = [row for row in data if row.get("month")]
    
    if not chart_data:
        return None
    
    chart = {
        "data": {
            "labels": [row.get("period") for row in chart_data],
            "datasets": [
                {
                    "name": "Employee Contribution (8%)",
                    "values": [flt(row.get("employee_contribution")) for row in chart_data]
                },
                {
                    "name": "Employer Contribution (10%)",
                    "values": [flt(row.get("employer_contribution")) for row in chart_data]
                },
                {
                    "name": "Cumulative Total",
                    "values": [flt(row.get("cumulative")) for row in chart_data],
                    "chartType": "line"
                }
            ]
        },
        "type": "axis-mixed",
        "colors": ["#667eea", "#f093fb", "#4facfe"],
        "height": 300
    }
    
    return chart


def get_employee_info_message(filters):
    """Get employee information banner with pension details"""
    
    employee = frappe.get_doc("Employee", filters.get("employee"))
    
    # Get pension details - SAME AS PENSION REMITTANCE
    pin = employee.custom_pension_pin if hasattr(employee, 'custom_pension_pin') else "N/A"
    rsaid = employee.custom_pension_rsa_id if hasattr(employee, 'custom_pension_rsa_id') else "N/A"
    pfa = employee.custom_pension_fund_administrator if hasattr(employee, 'custom_pension_fund_administrator') else "N/A"
    pension_start = ""
    
    if hasattr(employee, 'custom_pension_start_date') and employee.custom_pension_start_date:
        pension_start = formatdate(employee.custom_pension_start_date)
    else:
        pension_start = "N/A"
    
    message = f"""
        <div style="padding: 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h3 style="margin-top: 0; margin-bottom: 15px;">
                <i class="fa fa-user-circle"></i> {employee.employee_name}
            </h3>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px;">
                <div>
                    <strong>Employee ID:</strong> {employee.name}<br>
                    <strong>Department:</strong> {employee.department or "N/A"}
                </div>
                <div>
                    <strong>Pension PIN:</strong> {pin}<br>
                    <strong>RSA ID:</strong> {rsaid}
                </div>
                <div>
                    <strong>PFA:</strong> {pfa}<br>
                    <strong>Pension Start:</strong> {pension_start}
                </div>
            </div>
        </div>
    """
    
    return message


@frappe.whitelist()
def get_employee_pension_summary(employee):
    """
    Get summary of employee pension contributions from Salary Slips
    Used for quick reference
    """
    
    # Get all submitted salary slips for employee
    slips = frappe.get_all(
        "Salary Slip",
        filters={
            "employee": employee,
            "docstatus": 1
        },
        fields=["name", "posting_date"],
        order_by="posting_date"
    )
    
    if not slips:
        return {
            "total_months": 0,
            "first_contribution": None,
            "last_contribution": None,
            "total_employee": 0,
            "total_employer": 0,
            "total_voluntary": 0,
            "total_all": 0
        }
    
    total_employee = 0
    total_employer = 0
    total_voluntary = 0
    
    for slip in slips:
        # Use EXACT SAME method as Pension Remittance
        ee = flt(get_component_amount(slip.name, "deductions", "Pension (EE)"))
        er = flt(get_component_amount(slip.name, "earnings", "Pension (ER)"))
        
        total_employee += ee
        total_employer += er
        # total_voluntary += flt(get_component_amount(slip.name, "deductions", "Voluntary Pension"))
    
    summary = {
        "total_months": len(slips),
        "first_contribution": slips[0].posting_date if slips else None,
        "last_contribution": slips[-1].posting_date if slips else None,
        "total_employee": total_employee,
        "total_employer": total_employer,
        "total_voluntary": total_voluntary,
        "total_all": total_employee + total_employer + total_voluntary
    }
    
    return summary


@frappe.whitelist()
def export_employee_statement_excel(filters):
    """Export individual employee pension statement to Excel"""
    
    # Parse filters if string
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    filters = frappe._dict(filters)
    
    # Validate
    if not filters.get("employee"):
        frappe.throw(_("Please select an Employee"))
    
    # Get data
    columns = get_columns()
    data = get_data(filters)
    
    if not data:
        frappe.throw(_("No data to export"))
    
    # Get employee info
    employee = frappe.get_doc("Employee", filters.get("employee"))
    
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
    from io import BytesIO
    from frappe.utils.file_manager import save_file
    
    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Pension Statement"
    
    # Styles
    header_font = Font(bold=True, color="FFFFFF", size=12)
    header_fill = PatternFill(start_color="667eea", end_color="667eea", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    data_alignment = Alignment(horizontal="left", vertical="center")
    number_alignment = Alignment(horizontal="right", vertical="center")
    
    border_style = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Employee header
    ws.merge_cells('A1:K1')
    ws['A1'] = f"EMPLOYEE PENSION STATEMENT"
    ws['A1'].font = Font(bold=True, size=16, color="667eea")
    ws['A1'].alignment = Alignment(horizontal="center")
    
    ws.merge_cells('A2:K2')
    ws['A2'] = f"{employee.employee_name} ({employee.name})"
    ws['A2'].font = Font(bold=True, size=14)
    ws['A2'].alignment = Alignment(horizontal="center")
    
    ws.merge_cells('A3:K3')
    ws['A3'] = f"Period: {filters.get('from_year')} - {filters.get('to_year')}"
    ws['A3'].font = Font(size=11)
    ws['A3'].alignment = Alignment(horizontal="center")
    
    # Employee details
    row = 5
    details = [
        ["Pension PIN:", employee.custom_pension_pin if hasattr(employee, 'custom_pension_pin') else "N/A"],
        ["RSA ID:", employee.custom_pension_rsa_id if hasattr(employee, 'custom_pension_rsa_id') else "N/A"],
        ["PFA:", employee.custom_pension_fund_administrator if hasattr(employee, 'custom_pension_fund_administrator') else "N/A"],
        ["Department:", employee.department or "N/A"]
    ]
    
    for detail in details:
        ws.cell(row, 1, detail[0]).font = Font(bold=True)
        ws.cell(row, 2, detail[1])
        row += 1
    
    # Column headers
    header_row = row + 1
    col_headers = [
        "Salary Slip", "Period", "Month", "Year", "Posting Date",
        "Gross Pay", "Employee (8%)", "Employer (10%)",
        "Total", "Cumulative", "Status"
    ]
    
    for col_num, header in enumerate(col_headers, 1):
        cell = ws.cell(header_row, col_num)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = border_style
    
    # Data rows
    data_start_row = header_row + 1
    for row_idx, row_data in enumerate(data, data_start_row):
        ws.cell(row_idx, 1, row_data.get("salary_slip") or "")
        ws.cell(row_idx, 2, row_data.get("period") or "")
        ws.cell(row_idx, 3, row_data.get("month") or "")
        ws.cell(row_idx, 4, row_data.get("year") or "")
        ws.cell(row_idx, 5, row_data.get("posting_date") or "")
        ws.cell(row_idx, 6, flt(row_data.get("gross_pay")))
        ws.cell(row_idx, 7, flt(row_data.get("employee_contribution")))
        ws.cell(row_idx, 8, flt(row_data.get("employer_contribution")))
        ws.cell(row_idx, 9, flt(row_data.get("total")))
        ws.cell(row_idx, 10, flt(row_data.get("cumulative")))
        ws.cell(row_idx, 11, row_data.get("status") or "")
        
        # Apply styles
        for col in range(1, 12):
            cell = ws.cell(row_idx, col)
            cell.border = border_style
            
            if col >= 6 and col <= 10:
                cell.alignment = number_alignment
                cell.number_format = '#,##0.00'
            else:
                cell.alignment = data_alignment
        
        # Highlight total row
        if row_data.get("period") and "<b>TOTAL</b>" in str(row_data.get("period")):
            for col in range(1, 12):
                cell = ws.cell(row_idx, col)
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")
    
    # Column widths
    column_widths = [18, 15, 12, 8, 15, 15, 15, 15, 15, 15, 12]
    for i, width in enumerate(column_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = width
    
    # Freeze panes
    ws.freeze_panes = ws.cell(header_row + 1, 1)
    
    # Save file
    file_name = f"Pension_Statement_{employee.name}_{filters.get('from_year')}_{filters.get('to_year')}.xlsx"
    
    file_stream = BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)
    
    file_doc = save_file(
        file_name,
        file_stream.read(),
        "Report",
        "Employee Pension Statement",
        is_private=1
    )
    
    return {
        "file_url": file_doc.file_url,
        "file_name": file_name
    }


@frappe.whitelist()
def debug_salary_components(employee, from_year=None, to_year=None):
    """
    Debug function to see what pension components exist in salary slips
    Helps identify the exact component names in the system
    """
    from_year = from_year or (datetime.now().year - 1)
    to_year = to_year or datetime.now().year
    
    from_date = f"{from_year}-01-01"
    to_date = f"{to_year}-12-31"
    
    # Get salary slips
    slips = frappe.db.sql("""
        SELECT name, posting_date, start_date, gross_pay
        FROM `tabSalary Slip`
        WHERE employee = %(employee)s
        AND start_date BETWEEN %(from_date)s AND %(to_date)s
        AND docstatus = 1
        ORDER BY start_date
        LIMIT 5
    """, {"employee": employee, "from_date": from_date, "to_date": to_date}, as_dict=1)
    
    if not slips:
        return {"error": "No salary slips found", "employee": employee, "date_range": f"{from_date} to {to_date}"}
    
    result = []
    for slip in slips:
        # Get ALL salary components
        components = frappe.db.sql("""
            SELECT 
                salary_component,
                amount,
                parentfield
            FROM `tabSalary Detail`
            WHERE parent = %(slip)s
            AND parenttype = 'Salary Slip'
            ORDER BY parentfield, idx
        """, {"slip": slip.name}, as_dict=1)
        
        # Filter pension-related components
        pension_components = [c for c in components if 'pension' in c.salary_component.lower()]
        
        # Test the exact extraction method
        er = flt(get_component_amount(slip.name, "earnings", "Pension (ER)"))
        ee = flt(get_component_amount(slip.name, "deductions", "Pension (EE)"))
        
        result.append({
            "salary_slip": slip.name,
            "date": slip.posting_date,
            "gross_pay": slip.gross_pay,
            "extracted_er": er,
            "extracted_ee": ee,
            "all_components_count": len(components),
            "pension_components": pension_components,
            "all_components": components
        })
    
    return result


@frappe.whitelist()
def preview_pension_print(filters):
    """
    Generate HTML preview of Employee Pension Statement
    """
    
    # Parse filters if string
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    filters = frappe._dict(filters)
    
    # Validate
    if not filters.get("employee"):
        frappe.throw(_("Please select an Employee"))
    
    # Get data
    data = get_data(filters)
    
    if not data:
        frappe.throw(_("No data available for printing"))
    
    # Get employee info
    employee = frappe.get_doc("Employee", filters.get("employee"))
    
    # Get pension details
    pin = employee.custom_pension_pin if hasattr(employee, 'custom_pension_pin') else "N/A"
    rsaid = employee.custom_pension_rsa_id if hasattr(employee, 'custom_pension_rsa_id') else "N/A"
    pfa = employee.custom_pension_fund_administrator if hasattr(employee, 'custom_pension_fund_administrator') else "N/A"
    pension_start = formatdate(employee.custom_pension_start_date) if hasattr(employee, 'custom_pension_start_date') and employee.custom_pension_start_date else "N/A"
    
    # Remove total row for display
    display_data = [row for row in data if row.get("month")]
    
    # Calculate totals
    total_gross = sum(flt(row.get("gross_pay")) for row in display_data)
    total_ee = sum(flt(row.get("employee_contribution")) for row in display_data)
    total_er = sum(flt(row.get("employer_contribution")) for row in display_data)
    total_all = sum(flt(row.get("total")) for row in display_data)
    
    # Build HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Employee Pension Statement - {employee.employee_name}</title>
        <style>
            @media print {{
                @page {{
                    size: A4;
                    margin: 15mm;
                }}
            }}
            
            body {{
                font-family: Arial, sans-serif;
                font-size: 11pt;
                color: #333;
                margin: 0;
                padding: 20px;
            }}
            
            .header {{
                text-align: center;
                margin-bottom: 30px;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 8px;
            }}
            
            .header h1 {{
                margin: 0 0 10px 0;
                font-size: 20pt;
            }}
            
            .header h2 {{
                margin: 0;
                font-size: 16pt;
                font-weight: normal;
            }}
            
            .employee-info {{
                background-color: #f8f9fa;
                border: 2px solid #667eea;
                padding: 20px;
                margin-bottom: 30px;
                border-radius: 8px;
            }}
            
            .employee-info h3 {{
                margin: 0 0 15px 0;
                color: #667eea;
                border-bottom: 2px solid #667eea;
                padding-bottom: 10px;
            }}
            
            .info-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
            }}
            
            .info-item {{
                padding: 8px;
            }}
            
            .info-label {{
                font-weight: bold;
                color: #555;
                display: inline-block;
                width: 150px;
            }}
            
            .info-value {{
                color: #333;
            }}
            
            .data-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 30px;
            }}
            
            .data-table thead {{
                background-color: #667eea;
                color: white;
            }}
            
            .data-table thead th {{
                padding: 12px 8px;
                text-align: left;
                font-weight: bold;
                border: 1px solid #5568d3;
            }}
            
            .data-table tbody tr {{
                border-bottom: 1px solid #dee2e6;
            }}
            
            .data-table tbody tr:nth-child(even) {{
                background-color: #f8f9fa;
            }}
            
            .data-table tbody td {{
                padding: 10px 8px;
                border: 1px solid #dee2e6;
            }}
            
            .data-table tfoot tr {{
                background-color: #f0f0f0;
                font-weight: bold;
                border-top: 3px solid #667eea;
            }}
            
            .data-table tfoot td {{
                padding: 12px 8px;
                border: 1px solid #dee2e6;
                font-size: 11pt;
            }}
            
            .text-right {{
                text-align: right;
            }}
            
            .text-center {{
                text-align: center;
            }}
            
            .summary-box {{
                background-color: #e8f5e9;
                border: 2px solid #4caf50;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 30px;
            }}
            
            .summary-box h3 {{
                margin: 0 0 15px 0;
                color: #2e7d32;
            }}
            
            .summary-grid {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 15px;
                text-align: center;
            }}
            
            .summary-item {{
                padding: 15px;
                background-color: white;
                border-radius: 4px;
            }}
            
            .summary-label {{
                font-weight: bold;
                color: #555;
                margin-bottom: 8px;
                font-size: 9pt;
            }}
            
            .summary-value {{
                font-size: 16pt;
                font-weight: bold;
                color: #2e7d32;
            }}
            
            .footer {{
                margin-top: 50px;
                padding-top: 20px;
                border-top: 2px solid #dee2e6;
                text-align: center;
                font-size: 9pt;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>EMPLOYEE PENSION STATEMENT</h1>
            <h2>Period: {filters.get('from_year')} - {filters.get('to_year')}</h2>
        </div>
        
        <div class="employee-info">
            <h3>Employee Information</h3>
            <div class="info-grid">
                <div class="info-item">
                    <span class="info-label">Employee ID:</span>
                    <span class="info-value">{employee.name}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Employee Name:</span>
                    <span class="info-value">{employee.employee_name}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Department:</span>
                    <span class="info-value">{employee.department or "N/A"}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Pension PIN:</span>
                    <span class="info-value">{pin}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">RSA ID:</span>
                    <span class="info-value">{rsaid}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">PFA:</span>
                    <span class="info-value">{pfa}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Pension Start Date:</span>
                    <span class="info-value">{pension_start}</span>
                </div>
            </div>
        </div>
        
        <table class="data-table">
            <thead>
                <tr>
                    <th style="width: 12%;">Salary Slip</th>
                    <th style="width: 12%;">Period</th>
                    <th style="width: 10%;">Posting Date</th>
                    <th class="text-right" style="width: 12%;">Gross Pay</th>
                    <th class="text-right" style="width: 13%;">Employee (8%)</th>
                    <th class="text-right" style="width: 13%;">Employer (10%)</th>
                    <th class="text-right" style="width: 12%;">Total</th>
                    <th class="text-right" style="width: 14%;">Cumulative</th>
                    <th class="text-center" style="width: 10%;">Status</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for row in display_data:
        html += f"""
                <tr>
                    <td>{row.get("salary_slip")}</td>
                    <td>{row.get("period")}</td>
                    <td>{formatdate(row.get("posting_date"))}</td>
                    <td class="text-right">{frappe.utils.fmt_money(row.get("gross_pay"))}</td>
                    <td class="text-right">{frappe.utils.fmt_money(row.get("employee_contribution"))}</td>
                    <td class="text-right">{frappe.utils.fmt_money(row.get("employer_contribution"))}</td>
                    <td class="text-right">{frappe.utils.fmt_money(row.get("total"))}</td>
                    <td class="text-right">{frappe.utils.fmt_money(row.get("cumulative"))}</td>
                    <td class="text-center">{row.get("status")}</td>
                </tr>
        """
    
    html += f"""
            </tbody>
            <tfoot>
                <tr>
                    <td colspan="3" class="text-right">TOTAL:</td>
                    <td class="text-right">{frappe.utils.fmt_money(total_gross)}</td>
                    <td class="text-right">{frappe.utils.fmt_money(total_ee)}</td>
                    <td class="text-right">{frappe.utils.fmt_money(total_er)}</td>
                    <td class="text-right">{frappe.utils.fmt_money(total_all)}</td>
                    <td colspan="2"></td>
                </tr>
            </tfoot>
        </table>
        
        <div class="summary-box">
            <h3>Pension Contribution Summary</h3>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="summary-label">Total Months</div>
                    <div class="summary-value">{len(display_data)}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Employee (8%)</div>
                    <div class="summary-value">{frappe.utils.fmt_money(total_ee)}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Employer (10%)</div>
                    <div class="summary-value">{frappe.utils.fmt_money(total_er)}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Total Accumulated</div>
                    <div class="summary-value">{frappe.utils.fmt_money(total_all)}</div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>This is a computer-generated document.</p>
            <p>Generated on {formatdate(nowdate())} at {frappe.utils.now_datetime().strftime("%H:%M:%S")}</p>
        </div>
    </body>
    </html>
    """
    
    return html


@frappe.whitelist()
def download_pension_pdf(filters):
    """
    Generate and download PDF of Employee Pension Statement
    """
    
    # Parse filters if string
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    filters = frappe._dict(filters)
    
    # Generate HTML
    html = preview_pension_print(filters)
    
    # Convert to PDF
    from frappe.utils.pdf import get_pdf
    from frappe.utils.file_manager import save_file
    
    pdf_content = get_pdf(html)
    
    # Generate filename
    employee_id = filters.get("employee")
    file_name = f"Pension_Statement_{employee_id}_{filters.get('from_year')}_{filters.get('to_year')}.pdf"
    
    # Save file
    file_doc = save_file(
        file_name,
        pdf_content,
        "Report",
        "Employee Pension Statement",
        is_private=1
    )
    
    return {
        "file_url": file_doc.file_url,
        "file_name": file_name
    }