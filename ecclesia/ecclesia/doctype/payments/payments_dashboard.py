# ============================================================================
# FILE: payments_dashboard.py
# Path: general_biz_apps/general_biz_apps/doctype/payments/payments_dashboard.py
# Updated for Advanced Payment Voucher System
# ============================================================================

# -*- coding: utf-8 -*-
# Copyright (c) 2025, Your Company and contributors
# Payments Dashboard - Updated for Advanced Payment Voucher System

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate, add_days, add_months


@frappe.whitelist()
def get_dashboard_data(company=None, from_date=None, to_date=None):
    """Get comprehensive dashboard data for payments"""
    
    if not company:
        company = frappe.defaults.get_user_default("Company")
    
    if not from_date:
        from_date = add_days(nowdate(), -30)
    
    if not to_date:
        to_date = nowdate()
    
    return {
        "summary_cards": get_summary_cards(company, from_date, to_date),
        "cashflow_breakdown": get_cashflow_breakdown(company, from_date, to_date),
        "payment_mode_breakdown": get_payment_mode_breakdown(company, from_date, to_date),
        "daily_trend": get_daily_trend(company, from_date, to_date),
        "top_payees": get_top_payees(company, from_date, to_date),
        "status_distribution": get_status_distribution(company, from_date, to_date),
        "bank_wise_payments": get_bank_wise_payments(company, from_date, to_date),
        "transaction_type_summary": get_transaction_type_summary(company, from_date, to_date),
        "cashflow_comparison": get_cashflow_comparison(company, from_date, to_date)
    }


def get_summary_cards(company, from_date, to_date):
    """Get summary card data - Updated for Advanced Payment Voucher System"""
    
    current_period = frappe.db.sql("""
        SELECT 
            COUNT(*) as total_payments,
            SUM(COALESCE(amount_paid, 0)) as total_amount,
            AVG(COALESCE(amount_paid, 0)) as avg_amount,
            SUM(CASE WHEN payment_status = 'Cleared' THEN 1 ELSE 0 END) as cleared_count,
            SUM(CASE WHEN payment_status = 'Pending' THEN 1 ELSE 0 END) as pending_count,
            SUM(CASE WHEN payment_status = 'Bounced' THEN 1 ELSE 0 END) as bounced_count,
            SUM(CASE WHEN cashflow_type = 'Operating' OR cashflow_type = 'Payment of Operation' 
                THEN COALESCE(amount_paid, 0) ELSE 0 END) as operating_amount,
            SUM(CASE WHEN cashflow_type = 'Investing' 
                THEN COALESCE(amount_paid, 0) ELSE 0 END) as investing_amount,
            SUM(CASE WHEN cashflow_type = 'Financing' 
                THEN COALESCE(amount_paid, 0) ELSE 0 END) as financing_amount
        FROM `tabPayments`
        WHERE 
            company = %s
            AND transaction_date BETWEEN %s AND %s
            AND docstatus = 1
    """, (company, from_date, to_date), as_dict=1)[0]
    
    # Get previous period for comparison
    days_diff = (getdate(to_date) - getdate(from_date)).days
    prev_from = add_days(getdate(from_date), -days_diff - 1)
    prev_to = add_days(getdate(from_date), -1)
    
    previous_period = frappe.db.sql("""
        SELECT 
            COUNT(*) as total_payments,
            SUM(COALESCE(amount_paid, 0)) as total_amount
        FROM `tabPayments`
        WHERE 
            company = %s
            AND transaction_date BETWEEN %s AND %s
            AND docstatus = 1
    """, (company, prev_from, prev_to), as_dict=1)[0]
    
    def calc_growth(current, previous):
        if previous and previous > 0:
            return round(((current - previous) / previous) * 100, 2)
        return 0
    
    return {
        "total_payments": {
            "value": current_period.total_payments or 0,
            "growth": calc_growth(
                current_period.total_payments or 0,
                previous_period.total_payments or 0
            )
        },
        "total_amount": {
            "value": current_period.total_amount or 0,
            "growth": calc_growth(
                current_period.total_amount or 0,
                previous_period.total_amount or 0
            )
        },
        "avg_payment": {
            "value": current_period.avg_amount or 0,
            "growth": 0
        },
        "total_wht": {
            "value": 0,  # WHT not in current system - placeholder for future
            "growth": 0
        },
        "cleared": current_period.cleared_count or 0,
        "pending": current_period.pending_count or 0,
        "bounced": current_period.bounced_count or 0,
        "operating": current_period.operating_amount or 0,
        "investing": current_period.investing_amount or 0,
        "financing": current_period.financing_amount or 0
    }


def get_cashflow_breakdown(company, from_date, to_date):
    """Get cashflow type breakdown"""
    
    data = frappe.db.sql("""
        SELECT 
            COALESCE(cashflow_type, 'Unclassified') as cashflow_type,
            COUNT(*) as count,
            SUM(COALESCE(amount_paid, 0)) as amount
        FROM `tabPayments`
        WHERE 
            company = %s
            AND transaction_date BETWEEN %s AND %s
            AND docstatus = 1
        GROUP BY cashflow_type
        ORDER BY amount DESC
    """, (company, from_date, to_date), as_dict=1)
    
    return data


def get_payment_mode_breakdown(company, from_date, to_date):
    """Get payment mode breakdown"""
    
    data = frappe.db.sql("""
        SELECT 
            COALESCE(mode_of_payment, 'Unknown') as payment_mode,
            COUNT(*) as count,
            SUM(COALESCE(amount_paid, 0)) as amount
        FROM `tabPayments`
        WHERE 
            company = %s
            AND transaction_date BETWEEN %s AND %s
            AND docstatus = 1
        GROUP BY mode_of_payment
        ORDER BY amount DESC
        LIMIT 10
    """, (company, from_date, to_date), as_dict=1)
    
    return data


def get_daily_trend(company, from_date, to_date):
    """Get daily payment trend"""
    
    data = frappe.db.sql("""
        SELECT 
            DATE(transaction_date) as date,
            COUNT(*) as count,
            SUM(COALESCE(amount_paid, 0)) as amount,
            SUM(CASE WHEN cashflow_type = 'Operating' OR cashflow_type = 'Payment of Operation' 
                THEN COALESCE(amount_paid, 0) ELSE 0 END) as operating,
            SUM(CASE WHEN cashflow_type = 'Investing' 
                THEN COALESCE(amount_paid, 0) ELSE 0 END) as investing,
            SUM(CASE WHEN cashflow_type = 'Financing' 
                THEN COALESCE(amount_paid, 0) ELSE 0 END) as financing
        FROM `tabPayments`
        WHERE 
            company = %s
            AND transaction_date BETWEEN %s AND %s
            AND docstatus = 1
        GROUP BY DATE(transaction_date)
        ORDER BY date
    """, (company, from_date, to_date), as_dict=1)
    
    return data


def get_top_payees(company, from_date, to_date, limit=10):
    """Get top payees by payment amount"""
    
    data = frappe.db.sql("""
        SELECT 
            payee_name,
            COUNT(*) as payment_count,
            SUM(COALESCE(amount_paid, 0)) as total_amount
        FROM `tabPayments`
        WHERE 
            company = %s
            AND transaction_date BETWEEN %s AND %s
            AND docstatus = 1
            AND payee_name IS NOT NULL
        GROUP BY payee_name
        ORDER BY total_amount DESC
        LIMIT %s
    """, (company, from_date, to_date, limit), as_dict=1)
    
    return data


def get_status_distribution(company, from_date, to_date):
    """Get payment status distribution"""
    
    data = frappe.db.sql("""
        SELECT 
            COALESCE(payment_status, 'Unknown') as status,
            COUNT(*) as count,
            SUM(COALESCE(amount_paid, 0)) as amount
        FROM `tabPayments`
        WHERE 
            company = %s
            AND transaction_date BETWEEN %s AND %s
            AND docstatus = 1
        GROUP BY payment_status
        ORDER BY amount DESC
    """, (company, from_date, to_date), as_dict=1)
    
    return data


def get_bank_wise_payments(company, from_date, to_date):
    """Get bank-wise payments using remittance_bank field"""
    
    data = frappe.db.sql("""
        SELECT 
            COALESCE(remittance_bank, 'Not Specified') as bank,
            COUNT(*) as count,
            SUM(COALESCE(amount_paid, 0)) as amount
        FROM `tabPayments`
        WHERE 
            company = %s
            AND transaction_date BETWEEN %s AND %s
            AND docstatus = 1
        GROUP BY remittance_bank
        ORDER BY amount DESC
        LIMIT 10
    """, (company, from_date, to_date), as_dict=1)
    
    return data


def get_transaction_type_summary(company, from_date, to_date):
    """Get transaction type summary (replaces payment_category)"""
    
    data = frappe.db.sql("""
        SELECT 
            COALESCE(trans_type, 'Uncategorized') as trans_type,
            COUNT(*) as count,
            SUM(COALESCE(amount_paid, 0)) as amount,
            AVG(COALESCE(amount_paid, 0)) as avg_amount
        FROM `tabPayments`
        WHERE 
            company = %s
            AND transaction_date BETWEEN %s AND %s
            AND docstatus = 1
        GROUP BY trans_type
        ORDER BY amount DESC
        LIMIT 10
    """, (company, from_date, to_date), as_dict=1)
    
    return data


def get_cashflow_comparison(company, from_date, to_date):
    """Get cashflow type comparison with percentages"""
    
    data = frappe.db.sql("""
        SELECT 
            COALESCE(cashflow_type, 'Unclassified') as cashflow_type,
            COUNT(*) as count,
            SUM(COALESCE(amount_paid, 0)) as amount
        FROM `tabPayments`
        WHERE 
            company = %s
            AND transaction_date BETWEEN %s AND %s
            AND docstatus = 1
        GROUP BY cashflow_type
    """, (company, from_date, to_date), as_dict=1)
    
    # Calculate percentages
    total = sum(d.amount for d in data)
    for row in data:
        row["percentage"] = (row.amount / total * 100) if total > 0 else 0
    
    return data


@frappe.whitelist()
def get_payment_kpis(company=None, period="This Month"):
    """Get key performance indicators for payments"""
    
    if not company:
        company = frappe.defaults.get_user_default("Company")
    
    # Determine date range based on period
    if period == "Today":
        from_date = to_date = nowdate()
    elif period == "This Week":
        from_date = add_days(nowdate(), -7)
        to_date = nowdate()
    elif period == "This Month":
        from_date = frappe.utils.get_first_day(nowdate())
        to_date = nowdate()
    elif period == "This Quarter":
        from_date = frappe.utils.get_quarter_start(nowdate())
        to_date = nowdate()
    else:  # This Year
        from_date = frappe.utils.get_year_start(nowdate())
        to_date = nowdate()
    
    # Total Payments Made
    total_paid = frappe.db.sql("""
        SELECT SUM(COALESCE(amount_paid, 0))
        FROM `tabPayments`
        WHERE company = %s 
        AND transaction_date BETWEEN %s AND %s
        AND docstatus = 1
    """, (company, from_date, to_date))[0][0] or 0
    
    # Bounce Rate
    total_payments = frappe.db.sql("""
        SELECT COUNT(*) 
        FROM `tabPayments`
        WHERE company = %s 
        AND transaction_date BETWEEN %s AND %s
        AND docstatus = 1
    """, (company, from_date, to_date))[0][0] or 0
    
    bounced_payments = frappe.db.sql("""
        SELECT COUNT(*) 
        FROM `tabPayments`
        WHERE company = %s 
        AND transaction_date BETWEEN %s AND %s
        AND docstatus = 1
        AND payment_status = 'Bounced'
    """, (company, from_date, to_date))[0][0] or 0
    
    bounce_rate = (bounced_payments / total_payments * 100) if total_payments > 0 else 0
    
    # Average Days to Clear (if clearance_date exists)
    avg_clear_days = frappe.db.sql("""
        SELECT AVG(DATEDIFF(clearance_date, transaction_date))
        FROM `tabPayments`
        WHERE company = %s 
        AND transaction_date BETWEEN %s AND %s
        AND docstatus = 1
        AND payment_status = 'Cleared'
        AND clearance_date IS NOT NULL
    """, (company, from_date, to_date))[0][0] or 0
    
    return {
        "bounce_rate": round(bounce_rate, 2),
        "avg_clear_days": round(avg_clear_days, 2),
        "total_paid": total_paid,
        "total_payments": total_payments
    }


@frappe.whitelist()
def get_cashflow_analysis(company, year=None):
    """Get detailed cashflow analysis by type"""
    
    if not year:
        year = nowdate().split('-')[0]
    
    data = frappe.db.sql("""
        SELECT 
            DATE_FORMAT(transaction_date, '%%Y-%%m') as month,
            COALESCE(cashflow_type, 'Unclassified') as cashflow_type,
            SUM(COALESCE(amount_paid, 0)) as amount
        FROM `tabPayments`
        WHERE 
            company = %s
            AND YEAR(transaction_date) = %s
            AND docstatus = 1
        GROUP BY DATE_FORMAT(transaction_date, '%%Y-%%m'), cashflow_type
        ORDER BY month, cashflow_type
    """, (company, year), as_dict=1)
    
    return data