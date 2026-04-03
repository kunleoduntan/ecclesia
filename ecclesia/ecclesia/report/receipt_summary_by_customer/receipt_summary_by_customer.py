# Copyright (c) 2026, 	kunle Oduntan and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate, add_days, add_months
import json


def execute(filters=None):
    """Receipt Summary by Customer Report"""
    columns = get_columns()
    data = get_data(filters)
    
    return columns, data


def get_columns():
    """Get columns for Receipt Summary"""
    return [
        {
            "label": _("Customer ID"),
            "fieldname": "customer_id",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 120
        },
        {
            "label": _("Customer Name"),
            "fieldname": "customer_name",
            "fieldtype": "Data",
            "width": 200
        },
        {
            "label": _("Receipt Count"),
            "fieldname": "receipt_count",
            "fieldtype": "Int",
            "width": 100
        },
        {
            "label": _("Total Received"),
            "fieldname": "total_received",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": _("Total WHT"),
            "fieldname": "total_wht",
            "fieldtype": "Currency",
            "width": 110
        },
        {
            "label": _("Net Received"),
            "fieldname": "net_received",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": _("Avg Receipt"),
            "fieldname": "avg_receipt",
            "fieldtype": "Currency",
            "width": 110
        }
    ]


def get_data(filters):
    """Get data for Receipt Summary"""
    conditions = ""
    if filters.get("customer_id"):
        conditions = "AND customer_id = %(customer_id)s"
    
    data = frappe.db.sql("""
        SELECT 
            customer_id,
            COALESCE(customer_name, payer_name) as customer_name,
            COUNT(*) as receipt_count,
            SUM(COALESCE(amount_received, amount_received_in_fc, 0)) as total_received,
            SUM(COALESCE(wht_amount, 0)) as total_wht,
            SUM(COALESCE(net_amount, amount_received, 0)) as net_received,
            AVG(COALESCE(amount_received, amount_received_in_fc, 0)) as avg_receipt
        FROM `tabReceipts`
        WHERE 
            company = %(company)s
            AND transaction_date BETWEEN %(from_date)s AND %(to_date)s
            AND docstatus = 1
            {conditions}
        GROUP BY customer_id, customer_name
        HAVING receipt_count > 0
        ORDER BY total_received DESC
    """.format(conditions=conditions), filters, as_dict=1)
    
    return data

