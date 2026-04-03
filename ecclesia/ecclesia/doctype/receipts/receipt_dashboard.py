# ============================================================================
# FILE 1: receipt_dashboard.py
# Path: general_biz_apps/general_biz_apps/doctype/receipts/receipt_dashboard.py
# ============================================================================

# -*- coding: utf-8 -*-
# Copyright (c) 2025, Your Company and contributors
# Receipt Dashboard

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate, add_days, add_months


@frappe.whitelist()
def get_dashboard_data(company=None, from_date=None, to_date=None):
    """Get comprehensive dashboard data for receipts"""
    
    if not company:
        company = frappe.defaults.get_user_default("Company")
    
    if not from_date:
        from_date = add_days(nowdate(), -30)
    
    if not to_date:
        to_date = nowdate()
    
    return {
        "summary_cards": get_summary_cards(company, from_date, to_date),
        "payment_mode_breakdown": get_payment_mode_breakdown(company, from_date, to_date),
        "daily_trend": get_daily_trend(company, from_date, to_date),
        "top_customers": get_top_customers(company, from_date, to_date),
        "status_distribution": get_status_distribution(company, from_date, to_date),
        "bank_wise_collections": get_bank_wise_collections(company, from_date, to_date),
        "aging_summary": get_aging_summary(company)
    }


def get_summary_cards(company, from_date, to_date):
    """Get summary card data"""
    
    current_period = frappe.db.sql("""
        SELECT 
            COUNT(*) as total_receipts,
            SUM(COALESCE(amount_received, amount_received_in_fc, 0)) as total_amount,
            AVG(COALESCE(amount_received, amount_received_in_fc, 0)) as avg_amount,
            SUM(COALESCE(wht_amount, 0)) as total_wht,
            SUM(CASE WHEN receipt_status = 'Cleared' THEN 1 ELSE 0 END) as cleared_count,
            SUM(CASE WHEN receipt_status = 'Pending' THEN 1 ELSE 0 END) as pending_count,
            SUM(CASE WHEN receipt_status = 'Bounced' THEN 1 ELSE 0 END) as bounced_count
        FROM `tabReceipts`
        WHERE 
            company = %s
            AND transaction_date BETWEEN %s AND %s
            AND docstatus = 1
    """, (company, from_date, to_date), as_dict=1)[0]
    
    # Get previous period for comparison
    days_diff = (getdate(to_date) - getdate(from_date)).days
    prev_from = add_days(getdate(from_date), -days_diff)
    prev_to = getdate(from_date)
    
    previous_period = frappe.db.sql("""
        SELECT 
            COUNT(*) as total_receipts,
            SUM(COALESCE(amount_received, amount_received_in_fc, 0)) as total_amount
        FROM `tabReceipts`
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
        "total_receipts": {
            "value": current_period.total_receipts or 0,
            "growth": calc_growth(
                current_period.total_receipts or 0,
                previous_period.total_receipts or 0
            )
        },
        "total_amount": {
            "value": current_period.total_amount or 0,
            "growth": calc_growth(
                current_period.total_amount or 0,
                previous_period.total_amount or 0
            )
        },
        "avg_receipt": {
            "value": current_period.avg_amount or 0,
            "growth": 0
        },
        "total_wht": {
            "value": current_period.total_wht or 0,
            "growth": 0
        },
        "cleared": current_period.cleared_count or 0,
        "pending": current_period.pending_count or 0,
        "bounced": current_period.bounced_count or 0
    }


def get_payment_mode_breakdown(company, from_date, to_date):
    """Get payment mode breakdown"""
    
    data = frappe.db.sql("""
        SELECT 
            COALESCE(mode_of_payment, 'Unknown') as payment_mode,
            COUNT(*) as count,
            SUM(COALESCE(amount_received, amount_received_in_fc, 0)) as amount
        FROM `tabReceipts`
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
    """Get daily collection trend"""
    
    data = frappe.db.sql("""
        SELECT 
            DATE(transaction_date) as date,
            COUNT(*) as count,
            SUM(COALESCE(amount_received, amount_received_in_fc, 0)) as amount
        FROM `tabReceipts`
        WHERE 
            company = %s
            AND transaction_date BETWEEN %s AND %s
            AND docstatus = 1
        GROUP BY DATE(transaction_date)
        ORDER BY date
    """, (company, from_date, to_date), as_dict=1)
    
    return data


def get_top_customers(company, from_date, to_date, limit=10):
    """Get top customers by receipt amount"""
    
    data = frappe.db.sql("""
        SELECT 
            customer_id,
            COALESCE(customer_name, payer_name) as customer_name,
            COUNT(*) as receipt_count,
            SUM(COALESCE(amount_received, amount_received_in_fc, 0)) as total_amount
        FROM `tabReceipts`
        WHERE 
            company = %s
            AND transaction_date BETWEEN %s AND %s
            AND docstatus = 1
        GROUP BY customer_id, customer_name
        ORDER BY total_amount DESC
        LIMIT %s
    """, (company, from_date, to_date, limit), as_dict=1)
    
    return data


def get_status_distribution(company, from_date, to_date):
    """Get receipt status distribution"""
    
    data = frappe.db.sql("""
        SELECT 
            COALESCE(receipt_status, 'Unknown') as status,
            COUNT(*) as count,
            SUM(COALESCE(amount_received, amount_received_in_fc, 0)) as amount
        FROM `tabReceipts`
        WHERE 
            company = %s
            AND transaction_date BETWEEN %s AND %s
            AND docstatus = 1
        GROUP BY receipt_status
        ORDER BY amount DESC
    """, (company, from_date, to_date), as_dict=1)
    
    return data


def get_bank_wise_collections(company, from_date, to_date):
    """Get bank-wise collections"""
    
    data = frappe.db.sql("""
        SELECT 
            COALESCE(remittance_bank, 'Not Specified') as bank,
            COUNT(*) as count,
            SUM(COALESCE(amount_received, amount_received_in_fc, 0)) as amount
        FROM `tabReceipts`
        WHERE 
            company = %s
            AND transaction_date BETWEEN %s AND %s
            AND docstatus = 1
        GROUP BY remittance_bank
        ORDER BY amount DESC
        LIMIT 10
    """, (company, from_date, to_date), as_dict=1)
    
    return data


def get_aging_summary(company):
    """Get customer aging summary"""
    
    data = frappe.db.sql("""
        SELECT 
            SUM(CASE WHEN DATEDIFF(CURDATE(), due_date) BETWEEN 0 AND 30 
                THEN outstanding_amount ELSE 0 END) as current,
            SUM(CASE WHEN DATEDIFF(CURDATE(), due_date) BETWEEN 31 AND 60 
                THEN outstanding_amount ELSE 0 END) as days_30_60,
            SUM(CASE WHEN DATEDIFF(CURDATE(), due_date) BETWEEN 61 AND 90 
                THEN outstanding_amount ELSE 0 END) as days_61_90,
            SUM(CASE WHEN DATEDIFF(CURDATE(), due_date) > 90 
                THEN outstanding_amount ELSE 0 END) as over_90,
            SUM(outstanding_amount) as total_outstanding
        FROM `tabSales Invoice`
        WHERE 
            company = %s
            AND docstatus = 1
            AND outstanding_amount > 0
    """, company, as_dict=1)[0]
    
    return data


@frappe.whitelist()
def get_receipt_kpis(company=None, period="This Month"):
    """Get key performance indicators"""
    
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
    
    # Collection Efficiency
    total_invoiced = frappe.db.sql("""
        SELECT SUM(grand_total) 
        FROM `tabSales Invoice`
        WHERE company = %s 
        AND posting_date BETWEEN %s AND %s
        AND docstatus = 1
    """, (company, from_date, to_date))[0][0] or 0
    
    total_collected = frappe.db.sql("""
        SELECT SUM(COALESCE(amount_received, amount_received_in_fc, 0))
        FROM `tabReceipts`
        WHERE company = %s 
        AND transaction_date BETWEEN %s AND %s
        AND docstatus = 1
    """, (company, from_date, to_date))[0][0] or 0
    
    collection_efficiency = (total_collected / total_invoiced * 100) if total_invoiced > 0 else 0
    
    # Bounce Rate
    total_receipts = frappe.db.sql("""
        SELECT COUNT(*) 
        FROM `tabReceipts`
        WHERE company = %s 
        AND transaction_date BETWEEN %s AND %s
        AND docstatus = 1
    """, (company, from_date, to_date))[0][0] or 0
    
    bounced_receipts = frappe.db.sql("""
        SELECT COUNT(*) 
        FROM `tabReceipts`
        WHERE company = %s 
        AND transaction_date BETWEEN %s AND %s
        AND docstatus = 1
        AND receipt_status = 'Bounced'
    """, (company, from_date, to_date))[0][0] or 0
    
    bounce_rate = (bounced_receipts / total_receipts * 100) if total_receipts > 0 else 0
    
    # Average Days to Clear
    avg_clear_days = frappe.db.sql("""
        SELECT AVG(DATEDIFF(clearance_date, transaction_date))
        FROM `tabReceipts`
        WHERE company = %s 
        AND transaction_date BETWEEN %s AND %s
        AND docstatus = 1
        AND receipt_status = 'Cleared'
        AND clearance_date IS NOT NULL
    """, (company, from_date, to_date))[0][0] or 0
    
    # Outstanding vs Collected Ratio
    total_outstanding = frappe.db.sql("""
        SELECT SUM(outstanding_amount)
        FROM `tabSales Invoice`
        WHERE company = %s
        AND docstatus = 1
        AND outstanding_amount > 0
    """, company)[0][0] or 0
    
    return {
        "collection_efficiency": round(collection_efficiency, 2),
        "bounce_rate": round(bounce_rate, 2),
        "avg_clear_days": round(avg_clear_days, 2),
        "total_invoiced": total_invoiced,
        "total_collected": total_collected,
        "total_outstanding": total_outstanding,
        "collection_ratio": round((total_collected / (total_collected + total_outstanding) * 100), 2) if (total_collected + total_outstanding) > 0 else 0
    }


@frappe.whitelist()
def get_receipt_heatmap(company, year=None):
    """Get receipt heatmap data for calendar view"""
    
    if not year:
        year = nowdate().split('-')[0]
    
    data = frappe.db.sql("""
        SELECT 
            DATE(transaction_date) as date,
            COUNT(*) as count,
            SUM(COALESCE(amount_received, amount_received_in_fc, 0)) as amount
        FROM `tabReceipts`
        WHERE 
            company = %s
            AND YEAR(transaction_date) = %s
            AND docstatus = 1
        GROUP BY DATE(transaction_date)
    """, (company, year), as_dict=1)
    
    return data


# ============================================================================
# FILE 2: receipt_dashboard.js (Standalone Page Version)
# Path: general_biz_apps/general_biz_apps/public/js/receipt_dashboard.js
# OR create as a Page in Frappe
# ============================================================================

"""
// Receipt Dashboard JS
// This can be used as a standalone page or integrated into workspace

frappe.pages['receipt-dashboard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Receipt Dashboard',
        single_column: true
    });
    
    frappe.receipt_dashboard = new ReceiptDashboard(page);
};

class ReceiptDashboard {
    constructor(page) {
        this.page = page;
        this.company = frappe.defaults.get_user_default("Company");
        this.from_date = frappe.datetime.add_months(frappe.datetime.get_today(), -1);
        this.to_date = frappe.datetime.get_today();
        
        this.setup_filters();
        this.setup_page();
        this.refresh();
    }
    
    setup_filters() {
        // Company Filter
        this.page.add_field({
            fieldname: 'company',
            label: __('Company'),
            fieldtype: 'Link',
            options: 'Company',
            default: this.company,
            change: () => {
                this.company = this.page.fields_dict.company.get_value();
                this.refresh();
            }
        });
        
        // From Date
        this.page.add_field({
            fieldname: 'from_date',
            label: __('From Date'),
            fieldtype: 'Date',
            default: this.from_date,
            change: () => {
                this.from_date = this.page.fields_dict.from_date.get_value();
                this.refresh();
            }
        });
        
        // To Date
        this.page.add_field({
            fieldname: 'to_date',
            label: __('To Date'),
            fieldtype: 'Date',
            default: this.to_date,
            change: () => {
                this.to_date = this.page.fields_dict.to_date.get_value();
                this.refresh();
            }
        });
        
        // Quick Filters
        this.page.add_inner_button(__('Today'), () => {
            this.set_date_range('today');
        });
        
        this.page.add_inner_button(__('This Week'), () => {
            this.set_date_range('week');
        });
        
        this.page.add_inner_button(__('This Month'), () => {
            this.set_date_range('month');
        });
        
        this.page.add_inner_button(__('This Quarter'), () => {
            this.set_date_range('quarter');
        });
        
        // Refresh Button
        this.page.set_primary_action(__('Refresh'), () => {
            this.refresh();
        }, 'refresh');
    }
    
    set_date_range(period) {
        let today = frappe.datetime.get_today();
        
        switch(period) {
            case 'today':
                this.from_date = this.to_date = today;
                break;
            case 'week':
                this.from_date = frappe.datetime.add_days(today, -7);
                this.to_date = today;
                break;
            case 'month':
                this.from_date = frappe.datetime.month_start();
                this.to_date = today;
                break;
            case 'quarter':
                this.from_date = frappe.datetime.quarter_start();
                this.to_date = today;
                break;
        }
        
        this.page.fields_dict.from_date.set_value(this.from_date);
        this.page.fields_dict.to_date.set_value(this.to_date);
        this.refresh();
    }
    
    setup_page() {
        this.page.main.html(`
            <div class="receipt-dashboard">
                <div class="dashboard-loading" style="text-align: center; padding: 50px;">
                    <i class="fa fa-spinner fa-spin fa-3x"></i>
                    <p>${__('Loading Dashboard...')}</p>
                </div>
            </div>
        `);
    }
    
    refresh() {
        frappe.call({
            method: 'general_biz_apps.general_biz_apps.doctype.receipts.receipt_dashboard.get_dashboard_data',
            args: {
                company: this.company,
                from_date: this.from_date,
                to_date: this.to_date
            },
            callback: (r) => {
                if (r.message) {
                    this.render_dashboard(r.message);
                }
            }
        });
    }
    
    render_dashboard(data) {
        let html = `
            <div class="receipt-dashboard">
                ${this.render_summary_cards(data.summary_cards)}
                
                <div class="row mt-4">
                    <div class="col-md-6">
                        ${this.render_chart_card('Daily Trend', 'daily-trend-chart')}
                    </div>
                    <div class="col-md-6">
                        ${this.render_chart_card('Payment Mode Distribution', 'payment-mode-chart')}
                    </div>
                </div>
                
                <div class="row mt-4">
                    <div class="col-md-6">
                        ${this.render_chart_card('Status Distribution', 'status-chart')}
                    </div>
                    <div class="col-md-6">
                        ${this.render_chart_card('Bank-wise Collections', 'bank-chart')}
                    </div>
                </div>
                
                <div class="row mt-4">
                    <div class="col-md-6">
                        ${this.render_top_customers(data.top_customers)}
                    </div>
                    <div class="col-md-6">
                        ${this.render_aging_summary(data.aging_summary)}
                    </div>
                </div>
            </div>
        `;
        
        this.page.main.html(html);
        
        // Render charts
        this.render_daily_trend_chart(data.daily_trend);
        this.render_payment_mode_chart(data.payment_mode_breakdown);
        this.render_status_chart(data.status_distribution);
        this.render_bank_chart(data.bank_wise_collections);
    }
    
    render_summary_cards(summary) {
        let growth_icon = (growth) => {
            if (growth > 0) return `<span style="color: green;">▲ ${growth}%</span>`;
            if (growth < 0) return `<span style="color: red;">▼ ${Math.abs(growth)}%</span>`;
            return `<span>─ 0%</span>`;
        };
        
        return `
            <div class="row">
                <div class="col-md-3">
                    <div class="card dashboard-card" style="border-left: 4px solid #5e64ff;">
                        <div class="card-body">
                            <h6 class="text-muted">${__('Total Receipts')}</h6>
                            <h3>${summary.total_receipts.value}</h3>
                            <small>${growth_icon(summary.total_receipts.growth)}</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card dashboard-card" style="border-left: 4px solid #2ecc71;">
                        <div class="card-body">
                            <h6 class="text-muted">${__('Total Amount')}</h6>
                            <h3>${format_currency(summary.total_amount.value)}</h3>
                            <small>${growth_icon(summary.total_amount.growth)}</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card dashboard-card" style="border-left: 4px solid #ffa00a;">
                        <div class="card-body">
                            <h6 class="text-muted">${__('Average Receipt')}</h6>
                            <h3>${format_currency(summary.avg_receipt.value)}</h3>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card dashboard-card" style="border-left: 4px solid #e74c3c;">
                        <div class="card-body">
                            <h6 class="text-muted">${__('Total WHT')}</h6>
                            <h3>${format_currency(summary.total_wht.value)}</h3>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row mt-3">
                <div class="col-md-4">
                    <div class="card" style="border-top: 3px solid #2ecc71;">
                        <div class="card-body text-center" style="background-color: #d4edda;">
                            <h6>${__('Cleared')}</h6>
                            <h3 style="color: #2ecc71;">${summary.cleared}</h3>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card" style="border-top: 3px solid #ffa00a;">
                        <div class="card-body text-center" style="background-color: #fff3cd;">
                            <h6>${__('Pending')}</h6>
                            <h3 style="color: #ffa00a;">${summary.pending}</h3>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card" style="border-top: 3px solid #e74c3c;">
                        <div class="card-body text-center" style="background-color: #f8d7da;">
                            <h6>${__('Bounced')}</h6>
                            <h3 style="color: #e74c3c;">${summary.bounced}</h3>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    render_chart_card(title, chart_id) {
        return `
            <div class="card">
                <div class="card-header" style="background-color: #f8f9fa;">
                    <h5 style="margin: 0;">${title}</h5>
                </div>
                <div class="card-body">
                    <div id="${chart_id}" style="height: 300px;"></div>
                </div>
            </div>
        `;
    }
    
    render_daily_trend_chart(data) {
        if (!data || data.length === 0) {
            document.getElementById('daily-trend-chart').innerHTML = '<p class="text-center text-muted">No data available</p>';
            return;
        }
        
        new frappe.Chart("#daily-trend-chart", {
            data: {
                labels: data.map(d => frappe.datetime.str_to_user(d.date)),
                datasets: [
                    {
                        name: "Amount",
                        values: data.map(d => d.amount)
                    }
                ]
            },
            type: 'line',
            height: 280,
            colors: ['#5e64ff']
        });
    }
    
    render_payment_mode_chart(data) {
        if (!data || data.length === 0) {
            document.getElementById('payment-mode-chart').innerHTML = '<p class="text-center text-muted">No data available</p>';
            return;
        }
        
        new frappe.Chart("#payment-mode-chart", {
            data: {
                labels: data.map(d => d.payment_mode),
                datasets: [
                    {
                        name: "Amount",
                        values: data.map(d => d.amount)
                    }
                ]
            },
            type: 'pie',
            height: 280,
            colors: ['#5e64ff', '#ffa00a', '#2ecc71', '#e74c3c', '#9b59b6', '#3498db', '#f39c12', '#1abc9c']
        });
    }
    
    render_status_chart(data) {
        if (!data || data.length === 0) {
            document.getElementById('status-chart').innerHTML = '<p class="text-center text-muted">No data available</p>';
            return;
        }
        
        new frappe.Chart("#status-chart", {
            data: {
                labels: data.map(d => d.status),
                datasets: [
                    {
                        name: "Count",
                        values: data.map(d => d.count)
                    }
                ]
            },
            type: 'bar',
            height: 280,
            colors: ['#2ecc71']
        });
    }
    
    render_bank_chart(data) {
        if (!data || data.length === 0) {
            document.getElementById('bank-chart').innerHTML = '<p class="text-center text-muted">No data available</p>';
            return;
        }
        
        new frappe.Chart("#bank-chart", {
            data: {
                labels: data.map(d => d.bank),
                datasets: [
                    {
                        name: "Amount",
                        values: data.map(d => d.amount)
                    }
                ]
            },
            type: 'bar',
            height: 280,
            colors: ['#9b59b6']
        });
    }
    
    render_top_customers(customers) {
        if (!customers || customers.length === 0) {
            return `
                <div class="card">
                    <div class="card-header" style="background-color: #f8f9fa;">
                        <h5 style="margin: 0;">${__('Top Customers')}</h5>
                    </div>
                    <div class="card-body">
                        <p class="text-center text-muted">No data available</p>
                    </div>
                </div>
            `;
        }
        
        let rows = customers.map(c => `
            <tr>
                <td><a href="/app/customer/${c.customer_id}">${c.customer_name}</a></td>
                <td class="text-right">${c.receipt_count}</td>
                <td class="text-right"><strong>${format_currency(c.total_amount)}</strong></td>
            </tr>
        `).join('');
        
        return `
            <div class="card">
                <div class="card-header" style="background-color: #f8f9fa;">
                    <h5 style="margin: 0;">${__('Top Customers')}</h5>
                </div>
                <div class="card-body">
                    <table class="table table-sm table-hover">
                        <thead>
                            <tr>
                                <th>${__('Customer')}</th>
                                <th class="text-right">${__('Receipts')}</th>
                                <th class="text-right">${__('Amount')}</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rows}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }
    
    render_aging_summary(aging) {
        return `
            <div class="card">
                <div class="card-header" style="background-color: #f8f9fa;">
                    <h5 style="margin: 0;">${__('Outstanding Aging Summary')}</h5>
                </div>
                <div class="card-body">
                    <table class="table table-sm">
                        <tbody>
                            <tr>
                                <td>${__('Current (0-30 days)')}</td>
                                <td class="text-right"><strong>${format_currency(aging.current || 0)}</strong></td>
                            </tr>
                            <tr>
                                <td>${__('31-60 days')}</td>
                                <td class="text-right"><strong>${format_currency(aging.days_30_60 || 0)}</strong></td>
                            </tr>
                            <tr style="background-color: #fff3cd;">
                                <td>${__('61-90 days')}</td>
                                <td class="text-right"><strong style="color: #ffa00a;">${format_currency(aging.days_61_90 || 0)}</strong></td>
                            </tr>
                            <tr style="background-color: #f8d7da;">
                                <td>${__('Over 90 days')}</td>
                                <td class="text-right"><strong style="color: #e74c3c;">${format_currency(aging.over_90 || 0)}</strong></td>
                            </tr>
                            <tr style="font-weight: bold; background-color: #f8f9fa;">
                                <td>${__('Total Outstanding')}</td>
                                <td class="text-right">${format_currency(aging.total_outstanding || 0)}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }
}

// Add custom CSS
frappe.after_ajax(() => {
    if (!document.getElementById('receipt-dashboard-styles')) {
        const style = document.createElement('style');
        style.id = 'receipt-dashboard-styles';
        style.textContent = `
            .dashboard-card {
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                transition: all 0.3s;
                margin-bottom: 15px;
            }
            
            .dashboard-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            }
            
            .receipt-dashboard .card {
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }
            
            .receipt-dashboard .card-header {
                border-radius: 8px 8px 0 0;
            }
            
            .receipt-dashboard h3 {
                margin: 10px 0;
                font-size: 2em;
            }
            
            .receipt-dashboard h6 {
                margin-bottom: 5px;
                font-size: 0.85em;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
        `;
        document.head.appendChild(style);
    }
});
"""