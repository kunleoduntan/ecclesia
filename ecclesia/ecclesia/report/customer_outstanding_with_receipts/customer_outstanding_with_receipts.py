# Copyright (c) 2026, 	kunle Oduntan and contributors
# For license information, please see license.txt



import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate, add_days, add_months
import json


# ============================================================================
# FILE 3: customer_outstanding_with_receipts.py
# Path: general_biz_apps/report/customer_outstanding_with_receipts/customer_outstanding_with_receipts.py
# ============================================================================


def execute(filters=None):
    """Customer Outstanding with Receipts Report"""
    columns = get_columns()
    data = get_data(filters)
    
    return columns, data


def get_columns():
    """Get columns for Customer Outstanding"""
    return [
        {
            "label": _("Customer ID"),
            "fieldname": "customer",
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
            "label": _("Total Outstanding"),
            "fieldname": "total_outstanding",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": _("Current"),
            "fieldname": "current",
            "fieldtype": "Currency",
            "width": 110
        },
        {
            "label": _("30-60 Days"),
            "fieldname": "days_30_60",
            "fieldtype": "Currency",
            "width": 110
        },
        {
            "label": _("61-90 Days"),
            "fieldname": "days_61_90",
            "fieldtype": "Currency",
            "width": 110
        },
        {
            "label": _("Over 90 Days"),
            "fieldname": "over_90",
            "fieldtype": "Currency",
            "width": 110
        },
        {
            "label": _("Recent Receipts"),
            "fieldname": "receipts_last_30_days",
            "fieldtype": "Currency",
            "width": 130
        }
    ]


def get_data(filters):
    """Get data for Customer Outstanding"""
    conditions = ""
    if filters.get("customer_id"):
        conditions = "AND si.customer = %(customer_id)s"
    
    aging_filter = ""
    if filters.get("aging_days"):
        aging_map = {
            "0-30": "DATEDIFF(CURDATE(), si.due_date) BETWEEN 0 AND 30",
            "31-60": "DATEDIFF(CURDATE(), si.due_date) BETWEEN 31 AND 60",
            "61-90": "DATEDIFF(CURDATE(), si.due_date) BETWEEN 61 AND 90",
            "Over 90": "DATEDIFF(CURDATE(), si.due_date) > 90"
        }
        if filters.get("aging_days") in aging_map:
            aging_filter = f"AND {aging_map[filters.get('aging_days')]}"
    
    data = frappe.db.sql("""
        SELECT 
            si.customer,
            si.customer_name,
            SUM(si.outstanding_amount) as total_outstanding,
            SUM(CASE WHEN DATEDIFF(CURDATE(), si.due_date) BETWEEN 0 AND 30 
                THEN si.outstanding_amount ELSE 0 END) as current,
            SUM(CASE WHEN DATEDIFF(CURDATE(), si.due_date) BETWEEN 31 AND 60 
                THEN si.outstanding_amount ELSE 0 END) as days_30_60,
            SUM(CASE WHEN DATEDIFF(CURDATE(), si.due_date) BETWEEN 61 AND 90 
                THEN si.outstanding_amount ELSE 0 END) as days_61_90,
            SUM(CASE WHEN DATEDIFF(CURDATE(), si.due_date) > 90 
                THEN si.outstanding_amount ELSE 0 END) as over_90,
            (SELECT SUM(amount_received) 
             FROM `tabReceipts` 
             WHERE customer_id = si.customer 
             AND docstatus = 1 
             AND transaction_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)) as receipts_last_30_days
        FROM `tabSales Invoice` si
        WHERE 
            si.company = %(company)s
            AND si.docstatus = 1
            AND si.outstanding_amount > 0
            {conditions}
            {aging_filter}
        GROUP BY si.customer, si.customer_name
        ORDER BY total_outstanding DESC
    """.format(conditions=conditions, aging_filter=aging_filter), filters, as_dict=1)
    
    return data


