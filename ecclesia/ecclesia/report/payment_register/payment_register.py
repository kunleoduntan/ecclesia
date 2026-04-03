# Copyright (c) 2026, 	kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, fmt_money


def execute(filters=None):
    """Main execution function"""
    columns = get_columns(filters)
    data = get_data(filters)
    chart = get_chart_data(data, filters)
    summary = get_report_summary(data, filters)
    
    return columns, data, None, chart, summary


def get_columns(filters):
    """Define report columns"""
    columns = [
        {
            "label": _("Payment No"),
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "Payments",
            "width": 150
        },
        {
            "label": _("Date"),
            "fieldname": "transaction_date",
            "fieldtype": "Date",
            "width": 100
        },
        {
            "label": _("Type"),
            "fieldname": "trans_type",
            "fieldtype": "Data",
            "width": 130
        },
        {
            "label": _("Payee/Supplier"),
            "fieldname": "payee",
            "fieldtype": "Data",
            "width": 180
        },
        {
            "label": _("Supplier ID"),
            "fieldname": "payee_id",
            "fieldtype": "Link",
            "options": "Supplier",
            "width": 120
        },
        {
            "label": _("Reference No"),
            "fieldname": "reference_no",
            "fieldtype": "Data",
            "width": 130
        },
        {
            "label": _("Currency"),
            "fieldname": "payment_currency",
            "fieldtype": "Link",
            "options": "Currency",
            "width": 80
        },
        {
            "label": _("Amount"),
            "fieldname": "amount",
            "fieldtype": "Currency",
            "options": "payment_currency",
            "width": 130
        },
        {
            "label": _("Amount (LCY)"),
            "fieldname": "local_currency_amount",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": _("WHT Amount"),
            "fieldname": "wht_amount",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Net Amount"),
            "fieldname": "net_amount",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": _("Status"),
            "fieldname": "payment_status",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Mode of Payment"),
            "fieldname": "mode_of_payment",
            "fieldtype": "Link",
            "options": "Mode of Payment",
            "width": 130
        },
        {
            "label": _("Bank Account"),
            "fieldname": "remittance_bank",
            "fieldtype": "Link",
            "options": "Bank Account",
            "width": 150
        },
        {
            "label": _("Cost Center"),
            "fieldname": "cost_center",
            "fieldtype": "Link",
            "options": "Cost Center",
            "width": 130
        },
        {
            "label": _("Project"),
            "fieldname": "project",
            "fieldtype": "Link",
            "options": "Project",
            "width": 130
        },
        {
            "label": _("Purpose"),
            "fieldname": "transaction_purposes",
            "fieldtype": "Data",
            "width": 200
        },
        {
            "label": _("Issued By"),
            "fieldname": "issued_by",
            "fieldtype": "Link",
            "options": "User",
            "width": 130
        },
        {
            "label": _("Approved By"),
            "fieldname": "approved_by",
            "fieldtype": "Link",
            "options": "User",
            "width": 130
        }
    ]
    
    return columns


def get_data(filters):
    """Fetch report data"""
    conditions = get_conditions(filters)
    
    data = frappe.db.sql("""
        SELECT 
            p.name,
            p.transaction_date,
            p.trans_type,
            COALESCE(p.payee_name, p.supplier_name) as payee,
            p.payee_id,
            p.reference_no,
            p.payment_currency,
            COALESCE(p.amount_paid, p.amount_paid_in_fc) as amount,
            p.local_currency_amount,
            p.wht_amount,
            COALESCE(p.net_amount, p.amount_paid, p.amount_paid_in_fc) as net_amount,
            p.payment_status,
            p.mode_of_payment,
            p.remittance_bank,
            p.cost_center,
            p.project,
            p.transaction_purposes,
            p.issued_by,
            p.approved_by,
            p.company,
            p.docstatus
        FROM `tabPayments` p
        WHERE {conditions}
        ORDER BY p.transaction_date DESC, p.name DESC
    """.format(conditions=conditions), filters, as_dict=1)
    
    return data


def get_conditions(filters):
    """Build SQL conditions"""
    conditions = ["p.docstatus != 2"]  # Exclude cancelled
    
    if filters.get("company"):
        conditions.append("p.company = %(company)s")
    
    if filters.get("from_date"):
        conditions.append("p.transaction_date >= %(from_date)s")
    
    if filters.get("to_date"):
        conditions.append("p.transaction_date <= %(to_date)s")
    
    if filters.get("trans_type"):
        conditions.append("p.trans_type = %(trans_type)s")
    
    if filters.get("payment_status"):
        conditions.append("p.payment_status = %(payment_status)s")
    
    if filters.get("payee_id"):
        conditions.append("p.payee_id = %(payee_id)s")
    
    if filters.get("mode_of_payment"):
        conditions.append("p.mode_of_payment = %(mode_of_payment)s")
    
    if filters.get("cost_center"):
        conditions.append("p.cost_center = %(cost_center)s")
    
    if filters.get("project"):
        conditions.append("p.project = %(project)s")
    
    if filters.get("remittance_bank"):
        conditions.append("p.remittance_bank = %(remittance_bank)s")
    
    if filters.get("payment_currency"):
        conditions.append("p.payment_currency = %(payment_currency)s")
    
    if filters.get("min_amount"):
        conditions.append("p.local_currency_amount >= %(min_amount)s")
    
    if filters.get("max_amount"):
        conditions.append("p.local_currency_amount <= %(max_amount)s")
    
    return " AND ".join(conditions)


def get_chart_data(data, filters):
    """Generate chart data"""
    if not data:
        return None
    
    # Group by transaction type
    type_summary = {}
    for row in data:
        trans_type = row.get('trans_type', 'Unknown')
        amount = flt(row.get('local_currency_amount', 0))
        
        if trans_type not in type_summary:
            type_summary[trans_type] = 0
        type_summary[trans_type] += amount
    
    chart = {
        "data": {
            "labels": list(type_summary.keys()),
            "datasets": [
                {
                    "name": "Amount",
                    "values": list(type_summary.values())
                }
            ]
        },
        "type": "bar",
        "height": 280,
        "colors": ["#29cd42"]
    }
    
    return chart


def get_report_summary(data, filters):
    """Generate report summary"""
    if not data:
        return []
    
    total_amount = sum([flt(row.get('local_currency_amount', 0)) for row in data])
    total_wht = sum([flt(row.get('wht_amount', 0)) for row in data])
    total_net = sum([flt(row.get('net_amount', 0)) for row in data])
    total_count = len(data)
    
    # Count by status
    status_counts = {}
    for row in data:
        status = row.get('payment_status', 'Unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    summary = [
        {
            "value": total_count,
            "indicator": "Blue",
            "label": "Total Payments",
            "datatype": "Int"
        },
        {
            "value": total_amount,
            "indicator": "Green",
            "label": "Total Amount",
            "datatype": "Currency"
        }
    ]
    
    if total_wht > 0:
        summary.append({
            "value": total_wht,
            "indicator": "Orange",
            "label": "Total WHT",
            "datatype": "Currency"
        })
    
    summary.append({
        "value": total_net,
        "indicator": "Green",
        "label": "Net Amount",
        "datatype": "Currency"
    })
    
    # Add status-specific summaries
    for status, count in status_counts.items():
        if status == "Completed":
            indicator = "Green"
        elif status == "Pending Approval":
            indicator = "Orange"
        elif status == "Cancelled":
            indicator = "Red"
        else:
            indicator = "Blue"
        
        summary.append({
            "value": count,
            "indicator": indicator,
            "label": f"{status} Payments",
            "datatype": "Int"
        })
    
    return summary