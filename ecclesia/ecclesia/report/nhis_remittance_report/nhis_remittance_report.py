# Copyright (c) 2026, 	kunle Oduntan and contributors
# For license information, please see license.txt


import frappe
from frappe.utils import flt, formatdate, get_first_day, get_last_day, nowdate
from frappe import _
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
import json

def execute(filters=None):
    filters = filters or {}
    validate_filters(filters)
    columns = get_columns()
    data = get_data(filters)
    
    # Add chart if applicable
    chart = get_chart_data(data, filters)
    
    return columns, data, None, chart

def validate_filters(filters):
    if not filters.get("company"):
        frappe.throw(_("Please select a Company"))
    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw(_("Please select From Date and To Date"))

def get_columns():
    return [
        {
            "label": _("Employee"),
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 120
        },
        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "width": 200
        },
        {
            "label": _("NHIS Number"),
            "fieldname": "nhis_number",
            "width": 140
        },
        {
            "label": _("HMO"),
            "fieldname": "hmo",
            "width": 220
        },
        {
            "label": _("NHIS Start Date"),
            "fieldname": "nhis_start_date",
            "fieldtype": "Date",
            "width": 130
        },
        {
            "label": _("Salary Slip"),
            "fieldname": "salary_slip",
            "fieldtype": "Link",
            "options": "Salary Slip",
            "width": 140
        },
        {
            "label": _("Posting Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 110
        },
        {
            "label": _("Gross Pay"),
            "fieldname": "gross",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Employer NHIS (ER)"),
            "fieldname": "employer_nhis",
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "label": _("Employee NHIS (EE)"),
            "fieldname": "employee_nhis",
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "label": _("Total NHIS"),
            "fieldname": "total_nhis",
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "label": _("Company"),
            "fieldname": "company",
            "width": 200
        }
    ]

def get_data(filters):
    data = []
    
    # Build filters for Salary Slip
    slip_filters = {
        "docstatus": 1,
        "company": filters.get("company"),
        "start_date": ["between", [filters.get("from_date"), filters.get("to_date")]]
    }
    
    if filters.get("employee"):
        slip_filters["employee"] = filters.get("employee")
    
    slips = frappe.get_all(
        "Salary Slip",
        filters=slip_filters,
        fields=[
            "name", "employee", "employee_name",
            "posting_date", "gross_pay", "company", "start_date"
        ],
        order_by="posting_date, employee"
    )
    
    if not slips:
        frappe.msgprint(_("No salary slips found for the selected filters"))
        return data
    
    # Group by HMO if requested
    hmo_groups = {}
    
    for slip in slips:
        # Get employee NHIS details
        emp = frappe.db.get_value(
            "Employee",
            slip.employee,
            [
                "custom_nhis_number",
                "custom_nhis_hmo",
                "custom_nhis_start_date"
            ],
            as_dict=True
        ) or {}
        
        # Filter by HMO if specified
        if filters.get("hmo") and emp.get("custom_nhis_hmo") != filters.get("hmo"):
            continue
        
        # Get NHIS amounts
        er = flt(get_component_amount(slip.name, "earnings", "NHIS (ER)"))
        ee = flt(get_component_amount(slip.name, "deductions", "NHIS (EE)"))
        
        # Check for validation errors
        has_error = not emp.get("custom_nhis_number") or not emp.get("custom_nhis_hmo")
        
        # Skip if showing errors only and no error
        if filters.get("show_errors_only") and not has_error:
            continue
        
        # Only add row if there's NHIS contribution
        if er > 0 or ee > 0:
            row = {
                "employee": slip.employee,
                "employee_name": slip.employee_name,
                "nhis_number": emp.get("custom_nhis_number") or "",
                "hmo": emp.get("custom_nhis_hmo") or "",
                "nhis_start_date": emp.get("custom_nhis_start_date"),
                "salary_slip": slip.name,
                "posting_date": slip.posting_date,
                "gross": flt(slip.gross_pay),
                "employer_nhis": er,
                "employee_nhis": ee,
                "total_nhis": er + ee,
                "company": slip.company
            }
            
            if filters.get("group_by_hmo"):
                hmo_name = emp.get("custom_nhis_hmo") or "No HMO Set"
                if hmo_name not in hmo_groups:
                    hmo_groups[hmo_name] = []
                hmo_groups[hmo_name].append(row)
            else:
                data.append(row)
    
    # If grouping by HMO, format the data
    if filters.get("group_by_hmo") and hmo_groups:
        for hmo_name in sorted(hmo_groups.keys()):
            # Add HMO header
            data.append({
                "employee_name": f"HMO: {hmo_name}",
                "indent": 0
            })
            
            # Add rows for this HMO
            hmo_total_er = 0
            hmo_total_ee = 0
            hmo_total = 0
            
            for row in hmo_groups[hmo_name]:
                data.append(row)
                hmo_total_er += row["employer_nhis"]
                hmo_total_ee += row["employee_nhis"]
                hmo_total += row["total_nhis"]
            
            # Add HMO subtotal
            data.append({
                "employee_name": f"Total for {hmo_name}",
                "employer_nhis": hmo_total_er,
                "employee_nhis": hmo_total_ee,
                "total_nhis": hmo_total,
                "indent": 0
            })
            
            # Add blank row
            data.append({})
    
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

def get_chart_data(data, filters):
    """Generate chart data for visualization"""
    if not data:
        return None
    
    # Group by HMO for chart
    hmo_data = {}
    for row in data:
        if row.get("hmo") and row.get("total_nhis"):
            hmo = row["hmo"]
            if hmo not in hmo_data:
                hmo_data[hmo] = 0
            hmo_data[hmo] += row["total_nhis"]
    
    if not hmo_data:
        return None
    
    return {
        "data": {
            "labels": list(hmo_data.keys()),
            "datasets": [
                {
                    "name": "Total NHIS Contribution",
                    "values": list(hmo_data.values())
                }
            ]
        },
        "type": "bar",
        "height": 300,
        "colors": ["#dc3545"]
    }

@frappe.whitelist()
def export_nhis_format(filters, data=None):
    """Export data in NHIS standard format"""
    # Parse filters if string
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    filters = frappe._dict(filters)
    
    # Get fresh data if not provided
    if not data:
        data = get_data(filters)
    elif isinstance(data, str):
        data = json.loads(data)
    
    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "NHIS Remittance"
    
    # Define styles
    header_font = Font(bold=True, color="FFFFFF", size=12)
    header_fill = PatternFill(start_color="dc3545", end_color="dc3545", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    data_alignment = Alignment(horizontal="left", vertical="center")
    number_alignment = Alignment(horizontal="right", vertical="center")
    
    border_style = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Add company header
    company_name = frappe.db.get_value("Company", filters.get("company"), "company_name")
    ws.merge_cells('A1:H1')
    ws['A1'] = f"{company_name} - NHIS Remittance Schedule"
    ws['A1'].font = Font(bold=True, size=14)
    ws['A1'].alignment = Alignment(horizontal="center")
    
    # Add period
    ws.merge_cells('A2:H2')
    ws['A2'] = f"Period: {formatdate(filters.get('from_date'))} to {formatdate(filters.get('to_date'))}"
    ws['A2'].alignment = Alignment(horizontal="center")
    
    # NHIS headers
    headers = [
        "S/N",
        "NHIS Number",
        "Employee Name",
        "Gross Salary",
        "Employee Contribution (EE)",
        "Employer Contribution (ER)",
        "Total Contribution",
        "HMO Name"
    ]
    
    # Write headers
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_num)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = border_style
    
    # Write data
    row_num = 5
    sn = 1
    total_gross = 0
    total_ee = 0
    total_er = 0
    total_contribution = 0
    
    for item in data:
        if isinstance(item, dict) and item.get("employee"):
            ws.cell(row=row_num, column=1, value=sn)
            ws.cell(row=row_num, column=2, value=item.get("nhis_number") or "")
            ws.cell(row=row_num, column=3, value=item.get("employee_name") or "")
            ws.cell(row=row_num, column=4, value=flt(item.get("gross")))
            ws.cell(row=row_num, column=5, value=flt(item.get("employee_nhis")))
            ws.cell(row=row_num, column=6, value=flt(item.get("employer_nhis")))
            ws.cell(row=row_num, column=7, value=flt(item.get("total_nhis")))
            ws.cell(row=row_num, column=8, value=item.get("hmo") or "")
            
            # Apply styles
            for col in range(1, 9):
                cell = ws.cell(row=row_num, column=col)
                cell.border = border_style
                if col >= 4:
                    cell.alignment = number_alignment
                    cell.number_format = '#,##0.00'
                else:
                    cell.alignment = data_alignment
            
            total_gross += flt(item.get("gross"))
            total_ee += flt(item.get("employee_nhis"))
            total_er += flt(item.get("employer_nhis"))
            total_contribution += flt(item.get("total_nhis"))
            
            sn += 1
            row_num += 1
    
    # Add totals
    total_row = row_num + 1
    ws.cell(row=total_row, column=3, value="TOTAL").font = Font(bold=True)
    ws.cell(row=total_row, column=4, value=total_gross)
    ws.cell(row=total_row, column=5, value=total_ee)
    ws.cell(row=total_row, column=6, value=total_er)
    ws.cell(row=total_row, column=7, value=total_contribution)
    
    for col in range(3, 8):
        cell = ws.cell(row=total_row, column=col)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")
        cell.border = border_style
        if col >= 4:
            cell.number_format = '#,##0.00'
    
    # Adjust column widths
    column_widths = [8, 20, 30, 15, 20, 20, 20, 30]
    for i, width in enumerate(column_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = width
    
    # Save to file
    from frappe.utils.file_manager import save_file
    from io import BytesIO
    
    file_name = f"NHIS_Remittance_{filters.get('company')}_{formatdate(filters.get('from_date'))}_{formatdate(filters.get('to_date'))}.xlsx"
    
    # Save to BytesIO
    file_stream = BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)
    
    # Save file
    file_doc = save_file(
        file_name,
        file_stream.read(),
        "Report",
        "NHIS Remittance Report",
        is_private=1
    )
    
    return {
        "file_url": file_doc.file_url,
        "file_name": file_name
    }

@frappe.whitelist()
def export_detailed_excel(filters, data=None):
    """Export detailed Excel with all information"""
    # Parse filters if string
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    filters = frappe._dict(filters)
    
    # Get fresh data if not provided
    if not data:
        data = get_data(filters)
    elif isinstance(data, str):
        data = json.loads(data)
    
    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "NHIS Details"
    
    # Define styles
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="dc3545", end_color="dc3545", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    data_alignment = Alignment(horizontal="left", vertical="center")
    number_alignment = Alignment(horizontal="right", vertical="center")
    date_alignment = Alignment(horizontal="center", vertical="center")
    
    border_style = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Add company header
    company_name = frappe.db.get_value("Company", filters.get("company"), "company_name")
    ws.merge_cells('A1:M1')
    ws['A1'] = f"{company_name} - Detailed NHIS Remittance Report"
    ws['A1'].font = Font(bold=True, size=14)
    ws['A1'].alignment = Alignment(horizontal="center")
    
    # Add period
    ws.merge_cells('A2:M2')
    ws['A2'] = f"Period: {formatdate(filters.get('from_date'))} to {formatdate(filters.get('to_date'))}"
    ws['A2'].alignment = Alignment(horizontal="center")
    ws['A2'].font = Font(size=11)
    
    # Add generation date
    ws.merge_cells('A3:M3')
    ws['A3'] = f"Generated on: {formatdate(nowdate())} at {frappe.utils.now_datetime().strftime('%H:%M:%S')}"
    ws['A3'].alignment = Alignment(horizontal="center")
    ws['A3'].font = Font(size=9, italic=True)
    
    # Headers
    headers = [
        "Employee ID",
        "Employee Name",
        "NHIS Number",
        "HMO",
        "NHIS Start Date",
        "Salary Slip",
        "Posting Date",
        "Gross Pay",
        "Employer NHIS (ER)",
        "Employee NHIS (EE)",
        "Total NHIS",
        "Company"
    ]
    
    # Write headers
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=5, column=col_num)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = border_style
    
    # Write data
    row_num = 6
    total_gross = 0
    total_ee = 0
    total_er = 0
    total_contribution = 0
    employee_count = 0
    
    for item in data:
        if isinstance(item, dict) and item.get("employee"):
            ws.cell(row=row_num, column=1, value=item.get("employee") or "")
            ws.cell(row=row_num, column=2, value=item.get("employee_name") or "")
            ws.cell(row=row_num, column=3, value=item.get("nhis_number") or "")
            ws.cell(row=row_num, column=4, value=item.get("hmo") or "")
            ws.cell(row=row_num, column=5, value=item.get("nhis_start_date") or "")
            ws.cell(row=row_num, column=6, value=item.get("salary_slip") or "")
            ws.cell(row=row_num, column=7, value=item.get("posting_date") or "")
            ws.cell(row=row_num, column=8, value=flt(item.get("gross")))
            ws.cell(row=row_num, column=9, value=flt(item.get("employer_nhis")))
            ws.cell(row=row_num, column=10, value=flt(item.get("employee_nhis")))
            ws.cell(row=row_num, column=11, value=flt(item.get("total_nhis")))
            ws.cell(row=row_num, column=12, value=item.get("company") or "")
            
            # Apply styles
            for col in range(1, 13):
                cell = ws.cell(row=row_num, column=col)
                cell.border = border_style
                
                if col in [8, 9, 10, 11]:  # Currency columns
                    cell.alignment = number_alignment
                    cell.number_format = '#,##0.00'
                elif col in [5, 7]:  # Date columns
                    cell.alignment = date_alignment
                else:
                    cell.alignment = data_alignment
            
            # Highlight missing information
            if not item.get("nhis_number"):
                ws.cell(row=row_num, column=3).fill = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid")
            if not item.get("hmo"):
                ws.cell(row=row_num, column=4).fill = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid")
            
            total_gross += flt(item.get("gross"))
            total_ee += flt(item.get("employee_nhis"))
            total_er += flt(item.get("employer_nhis"))
            total_contribution += flt(item.get("total_nhis"))
            employee_count += 1
            
            row_num += 1
    
    # Add totals
    total_row = row_num + 1
    ws.cell(row=total_row, column=2, value="GRAND TOTAL").font = Font(bold=True, size=12)
    ws.cell(row=total_row, column=8, value=total_gross)
    ws.cell(row=total_row, column=9, value=total_er)
    ws.cell(row=total_row, column=10, value=total_ee)
    ws.cell(row=total_row, column=11, value=total_contribution)
    
    for col in range(2, 12):
        cell = ws.cell(row=total_row, column=col)
        cell.font = Font(bold=True, size=11)
        cell.fill = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")
        cell.border = border_style
        if col >= 8:
            cell.number_format = '#,##0.00'
            cell.alignment = number_alignment
    
    # Add summary
    summary_row = total_row + 2
    ws.cell(row=summary_row, column=2, value="Total Employees:").font = Font(bold=True)
    ws.cell(row=summary_row, column=3, value=employee_count)
    
    # Adjust column widths
    column_widths = [15, 25, 18, 30, 18, 18, 15, 15, 18, 18, 18, 25]
    for i, width in enumerate(column_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = width
    
    # Freeze panes
    ws.freeze_panes = 'A6'
    
    # Save to file
    from frappe.utils.file_manager import save_file
    from io import BytesIO
    
    file_name = f"NHIS_Detailed_{filters.get('company')}_{formatdate(filters.get('from_date'))}_{formatdate(filters.get('to_date'))}.xlsx"
    
    # Save to BytesIO
    file_stream = BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)
    
    # Save file
    file_doc = save_file(
        file_name,
        file_stream.read(),
        "Report",
        "NHIS Remittance Report",
        is_private=1
    )
    
    return {
        "file_url": file_doc.file_url,
        "file_name": file_name
    }

@frappe.whitelist()
def generate_summary_pdf(filters, summary):
    """Generate PDF summary report"""
    # Parse parameters if string
    if isinstance(filters, str):
        filters = json.loads(filters)
    if isinstance(summary, str):
        summary = json.loads(summary)
    
    filters = frappe._dict(filters)
    summary = frappe._dict(summary)
    
    company_name = frappe.db.get_value("Company", filters.get("company"), "company_name")
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .header h2 {{ color: #dc3545; margin-bottom: 5px; }}
            .header p {{ color: #666; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ padding: 12px; text-align: left; border: 1px solid #ddd; }}
            th {{ background-color: #dc3545; color: white; font-weight: bold; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .total {{ font-weight: bold; background-color: #E7E6E6; }}
            .currency {{ text-align: right; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>{company_name}</h2>
            <h3>NHIS Remittance Summary</h3>
            <p>Period: {formatdate(filters.get('from_date'))} to {formatdate(filters.get('to_date'))}</p>
            <p>Generated on: {formatdate(nowdate())}</p>
        </div>
        
        <table>
            <tr>
                <th>Description</th>
                <th class="currency">Amount/Count</th>
            </tr>
            <tr>
                <td>Total Employees</td>
                <td class="currency">{summary.get('total_employees', 0)}</td>
            </tr>
            <tr>
                <td>Employees with Validation Errors</td>
                <td class="currency" style="color: red;">{summary.get('employees_with_errors', 0)}</td>
            </tr>
            <tr>
                <td>Total Employer Contribution (ER)</td>
                <td class="currency">{frappe.utils.fmt_money(summary.get('total_employer', 0), currency=frappe.db.get_value('Company', filters.get('company'), 'default_currency'))}</td>
            </tr>
            <tr>
                <td>Total Employee Contribution (EE)</td>
                <td class="currency">{frappe.utils.fmt_money(summary.get('total_employee', 0), currency=frappe.db.get_value('Company', filters.get('company'), 'default_currency'))}</td>
            </tr>
            <tr class="total">
                <td>Total NHIS Remittance</td>
                <td class="currency">{frappe.utils.fmt_money(summary.get('total_nhis', 0), currency=frappe.db.get_value('Company', filters.get('company'), 'default_currency'))}</td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    from frappe.utils.pdf import get_pdf
    from frappe.utils.file_manager import save_file
    
    pdf_content = get_pdf(html)
    file_name = f"NHIS_Summary_{filters.get('company')}_{formatdate(filters.get('from_date'))}_{formatdate(filters.get('to_date'))}.pdf"
    
    file_doc = save_file(
        file_name,
        pdf_content,
        "Report",
        "NHIS Remittance Report",
        is_private=1
    )
    
    return {
        "file_url": file_doc.file_url,
        "file_name": file_name
    }