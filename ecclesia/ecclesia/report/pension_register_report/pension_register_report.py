# Copyright (c) 2026, 	kunle Oduntan and contributors
# For license information, please see license.txt



import frappe
from frappe import _
from frappe.utils import flt, getdate

def execute(filters=None):
    """
    Pension Register Report
    Shows all pension contributions for a period with detailed breakdown
    """
    
    if not filters:
        filters = {}
    
    columns = get_columns(filters)
    data = get_data(filters)
    chart = get_chart_data(data, filters)
    summary = get_summary(data)
    
    return columns, data, None, chart, summary


def get_columns(filters):
    """Define report columns"""
    
    columns = [
        {
            "label": _("Contribution ID"),
            "fieldname": "contribution_id",
            "fieldtype": "Link",
            "options": "Pension Contribution",
            "width": 150
        },
        {
            "label": _("Employee ID"),
            "fieldname": "employee_id",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 120
        },
        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 180
        },
        {
            "label": _("Department"),
            "fieldname": "department",
            "fieldtype": "Link",
            "options": "Department",
            "width": 130
        },
        {
            "label": _("PIN Number"),
            "fieldname": "pin_number",
            "fieldtype": "Data",
            "width": 140
        },
        {
            "label": _("PFA"),
            "fieldname": "pfa",
            "fieldtype": "Link",
            "options": "Supplier",
            "width": 150
        },
        {
            "label": _("Base Salary"),
            "fieldname": "base_salary",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Employee (8%)"),
            "fieldname": "employee_contribution",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Employer (10%)"),
            "fieldname": "employer_contribution",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Voluntary"),
            "fieldname": "voluntary_contribution",
            "fieldtype": "Currency",
            "width": 110
        },
        {
            "label": _("Total"),
            "fieldname": "total_contribution",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Payment Date"),
            "fieldname": "payment_date",
            "fieldtype": "Date",
            "width": 110
        },
        {
            "label": _("Remittance Schedule"),
            "fieldname": "remittance_schedule",
            "fieldtype": "Link",
            "options": "Pension Remittance Schedule",
            "width": 150
        }
    ]
    
    return columns


def get_data(filters):
    """Fetch pension contribution data"""
    
    conditions = get_conditions(filters)
    
    data = frappe.db.sql("""
        SELECT
            pc.name as contribution_id,
            pc.employee as employee_id,
            pc.employee_name,
            pc.department,
            pc.employee_pin as pin_number,
            pc.pension_fund_administrator as pfa,
            pc.base_salary,
            pc.employee_contribution_amount as employee_contribution,
            pc.employer_contribution_amount as employer_contribution,
            pc.employee_voluntary_amount as voluntary_contribution,
            pc.total_contribution,
            pc.status,
            pc.payment_date,
            pc.remittance_schedule,
            pc.posting_date,
            pc.period_month,
            pc.period_year
        FROM `tabPension Contribution` pc
        WHERE pc.docstatus = 1
        {conditions}
        ORDER BY pc.posting_date DESC, pc.employee_name
    """.format(conditions=conditions), filters, as_dict=1)
    
    return data


def get_conditions(filters):
    """Build SQL conditions from filters"""
    
    conditions = []
    
    if filters.get("company"):
        conditions.append("pc.company = %(company)s")
    
    if filters.get("from_date"):
        conditions.append("pc.posting_date >= %(from_date)s")
    
    if filters.get("to_date"):
        conditions.append("pc.posting_date <= %(to_date)s")
    
    if filters.get("period_month"):
        conditions.append("pc.period_month = %(period_month)s")
    
    if filters.get("period_year"):
        conditions.append("pc.period_year = %(period_year)s")
    
    if filters.get("department"):
        conditions.append("pc.department = %(department)s")
    
    if filters.get("pension_fund_administrator"):
        conditions.append("pc.pension_fund_administrator = %(pension_fund_administrator)s")
    
    if filters.get("status"):
        conditions.append("pc.status = %(status)s")
    
    if filters.get("employee"):
        conditions.append("pc.employee = %(employee)s")
    
    return " AND " + " AND ".join(conditions) if conditions else ""


def get_chart_data(data, filters):
    """Generate chart data"""
    
    if not data:
        return None
    
    # Group by PFA
    pfa_data = {}
    for row in data:
        pfa = row.get("pfa") or "Unknown"
        if pfa not in pfa_data:
            pfa_data[pfa] = {
                "employee": 0,
                "employer": 0,
                "voluntary": 0
            }
        
        pfa_data[pfa]["employee"] += flt(row.get("employee_contribution"))
        pfa_data[pfa]["employer"] += flt(row.get("employer_contribution"))
        pfa_data[pfa]["voluntary"] += flt(row.get("voluntary_contribution"))
    
    chart = {
        "data": {
            "labels": list(pfa_data.keys()),
            "datasets": [
                {
                    "name": "Employee Contribution",
                    "values": [pfa_data[pfa]["employee"] for pfa in pfa_data.keys()]
                },
                {
                    "name": "Employer Contribution",
                    "values": [pfa_data[pfa]["employer"] for pfa in pfa_data.keys()]
                },
                {
                    "name": "Voluntary Contribution",
                    "values": [pfa_data[pfa]["voluntary"] for pfa in pfa_data.keys()]
                }
            ]
        },
        "type": "bar",
        "colors": ["#667eea", "#f093fb", "#4facfe"]
    }
    
    return chart


def get_summary(data):
    """Generate summary statistics"""
    
    if not data:
        return []
    
    total_employees = len(data)
    total_employee_contrib = sum(flt(row.get("employee_contribution")) for row in data)
    total_employer_contrib = sum(flt(row.get("employer_contribution")) for row in data)
    total_voluntary = sum(flt(row.get("voluntary_contribution")) for row in data)
    grand_total = total_employee_contrib + total_employer_contrib + total_voluntary
    
    # Count by status
    status_count = {}
    for row in data:
        status = row.get("status") or "Unknown"
        status_count[status] = status_count.get(status, 0) + 1
    
    summary = [
        {
            "label": _("Total Employees"),
            "value": total_employees,
            "indicator": "blue",
            "datatype": "Int"
        },
        {
            "label": _("Employee Contribution"),
            "value": total_employee_contrib,
            "indicator": "green",
            "datatype": "Currency"
        },
        {
            "label": _("Employer Contribution"),
            "value": total_employer_contrib,
            "indicator": "orange",
            "datatype": "Currency"
        },
        {
            "label": _("Voluntary Contribution"),
            "value": total_voluntary,
            "indicator": "purple",
            "datatype": "Currency"
        },
        {
            "label": _("Grand Total"),
            "value": grand_total,
            "indicator": "red",
            "datatype": "Currency"
        }
    ]
    
    # Add status breakdown
    for status, count in status_count.items():
        summary.append({
            "label": _(f"{status} Status"),
            "value": count,
            "indicator": "grey",
            "datatype": "Int"
        })
    
    return summary