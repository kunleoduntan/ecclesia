// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt


// ============================================
// EXPENSE BATCH - PROFESSIONAL UI CLIENT SCRIPT
// Modern, Clean Design with Card Layout
// ============================================

// Global state
let ai_analysis_cache = {};

// ============================================
// MAIN FORM EVENTS
// ============================================

// Excel template / export / import (shared helper: public/js/batch_excel.js)
const _EB_XL = {
    module: "ecclesia.ecclesia.doctype.expense_batch.expense_batch",
    child_table: "petty_cash_transaction",
    label: __("Expenses"),
};

frappe.ui.form.on("Expense Batch", {
    setup: function(frm) {
        // Set read-only fields
        frm.set_df_property('balance', 'read_only', 1);
        frm.set_df_property('total_outflow', 'read_only', 1);
        frm.set_df_property('total_inflow', 'read_only', 1);
        frm.set_df_property('title', 'hidden', 1);
        
        // Filter for transactional accounts only
        frm.set_query('account', 'petty_cash_transaction', function() {
            return {
                filters: {
                    is_group: 0,
                    disabled: 0
                }
            };
        });
    },

    onload: function(frm) {
        apply_professional_styles();
        setup_modern_layout(frm);
        
        // Initialize with default transaction if empty
        if (!frm.doc.petty_cash_transaction || frm.doc.petty_cash_transaction.length === 0) {
            let row = frm.add_child('petty_cash_transaction');
            frappe.model.set_value(row.doctype, row.name, 'date', frappe.datetime.get_today());
            frm.refresh_field('petty_cash_transaction');
        }
        
        if (frm.is_new()) {
            show_toast_message('Professional expense tracking enabled', 'success');
        }
    },

    refresh: function(frm) {
        create_dashboard_header(frm);
        apply_modern_grid_styling(frm);
        add_professional_action_buttons(frm);
        ecclesia.batch_excel.add_buttons(frm, _EB_XL);
        update_month_display(frm);
        create_financial_metrics(frm);
        highlight_key_fields(frm);
        
        if (!frm.is_new() && frm.doc.petty_cash_transaction && frm.doc.petty_cash_transaction.length > 0) {
            setTimeout(() => check_anomalies(frm), 500);
        }
    },

    before_save: function(frm) {
        calculate_all_totals(frm);
        auto_populate_employee_details(frm);
        
        if (frm.doc.cost_center && frm.doc.employee_name) {
            frm.set_value('title', `${frm.doc.cost_center} - ${frm.doc.employee_name}`);
        }
    },

    validate: function(frm) {
        if (frm.doc.batch_end_date < frm.doc.batch_start_date) {
            frappe.throw(__('End date cannot be before start date'));
        }
        
        if (frm.doc.balance < 0) {
            frappe.warn(__('Closing balance is negative!'));
        }
    },

    batch_start_date: function(frm) {
        update_month_display(frm);
    },

    cost_center: function(frm) {
        set_petty_cash_account(frm);
        propagate_cost_center(frm);
    },

    opening_balance: function(frm) {
        calculate_all_totals(frm);
    },

    post_batch: function(frm) {
        if (frm.doc.post_batch === 1) {
            frappe.confirm(
                __('This will create payment vouchers. Continue?'),
                function() {
                    show_toast_message('Batch will be posted on save', 'info');
                },
                function() {
                    frm.set_value('post_batch', 0);
                }
            );
        }
    }
});

// ============================================
// CHILD TABLE EVENTS
// ============================================

frappe.ui.form.on("Petty Cash Transaction", {
    petty_cash_transaction_add: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, 'cost_center', frm.doc.cost_center);
        frappe.model.set_value(cdt, cdn, 'date', frappe.datetime.get_today());
    },

    inflow: function(frm) {
        calculate_all_totals(frm);
    },

    outflow: function(frm) {
        calculate_all_totals(frm);
    },

    transaction_description: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.transaction_description && row.transaction_description.length > 5) {
            auto_categorize_expense(row.transaction_description);
        }
    },

    beneficiary: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        check_duplicate_beneficiary(frm, row);
    },

    date: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        check_weekend_transaction(row);
    }
});

// ============================================
// PROFESSIONAL STYLING
// ============================================

function apply_professional_styles() {
    if ($('#modern-expense-styles').length) return;
    
    $('head').append(`
        <style id="modern-expense-styles">
            /* MODERN DESIGN SYSTEM */
            :root {
                --primary: #3b82f6;
                --primary-dark: #2563eb;
                --secondary: #64748b;
                --success: #10b981;
                --warning: #f59e0b;
                --danger: #ef4444;
                --info: #06b6d4;
                --background: #f8fafc;
                --surface: #ffffff;
                --border: #e2e8f0;
                --text-primary: #1e293b;
                --text-secondary: #64748b;
                --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
                --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
                --radius-sm: 6px;
                --radius-md: 8px;
                --radius-lg: 12px;
            }
            
            /* Dashboard Header */
            .dashboard-header {
                background: var(--surface);
                border-radius: var(--radius-lg);
                padding: 20px;
                margin-bottom: 24px;
                border: 1px solid var(--border);
                box-shadow: var(--shadow-sm);
                position: relative;
                overflow: hidden;
            }
            
            .dashboard-header::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: linear-gradient(90deg, var(--primary), var(--info));
            }
            
            .header-title {
                display: flex;
                align-items: center;
                gap: 12px;
                margin-bottom: 20px;
            }
            
            .header-title-icon {
                width: 48px;
                height: 48px;
                background: linear-gradient(135deg, var(--primary), var(--info));
                border-radius: var(--radius-md);
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: 20px;
            }
            
            .header-title-text h3 {
                margin: 0;
                color: var(--text-primary);
                font-size: 20px;
                font-weight: 700;
            }
            
            .header-title-text p {
                margin: 4px 0 0 0;
                color: var(--text-secondary);
                font-size: 13px;
            }
            
            /* Metrics Cards */
            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                gap: 16px;
                margin-top: 20px;
            }
            
            .metric-card {
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: var(--radius-md);
                padding: 16px;
                transition: all 0.2s ease;
                position: relative;
                overflow: hidden;
            }
            
            .metric-card:hover {
                border-color: var(--primary);
                transform: translateY(-2px);
                box-shadow: var(--shadow-md);
            }
            
            .metric-card.inflow::before {
                content: '';
                position: absolute;
                left: 0;
                top: 0;
                bottom: 0;
                width: 4px;
                background: var(--success);
            }
            
            .metric-card.outflow::before {
                content: '';
                position: absolute;
                left: 0;
                top: 0;
                bottom: 0;
                width: 4px;
                background: var(--danger);
            }
            
            .metric-card.balance::before {
                content: '';
                position: absolute;
                left: 0;
                top: 0;
                bottom: 0;
                width: 4px;
                background: var(--primary);
            }
            
            .metric-card.overview::before {
                content: '';
                position: absolute;
                left: 0;
                top: 0;
                bottom: 0;
                width: 4px;
                background: var(--info);
            }
            
            .metric-icon {
                width: 36px;
                height: 36px;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-bottom: 12px;
                font-size: 16px;
            }
            
            .metric-icon.primary { background: #eff6ff; color: var(--primary); }
            .metric-icon.success { background: #f0fdf4; color: var(--success); }
            .metric-icon.danger { background: #fef2f2; color: var(--danger); }
            .metric-icon.warning { background: #fffbeb; color: var(--warning); }
            .metric-icon.info { background: #ecfeff; color: var(--info); }
            
            .metric-value {
                font-size: 24px;
                font-weight: 700;
                color: var(--text-primary);
                line-height: 1.2;
                margin-bottom: 4px;
            }
            
            .metric-label {
                font-size: 12px;
                color: var(--text-secondary);
                text-transform: uppercase;
                letter-spacing: 0.5px;
                font-weight: 600;
                margin-bottom: 8px;
            }
            
            .metric-subtitle {
                font-size: 11px;
                color: var(--text-secondary);
                display: flex;
                align-items: center;
                gap: 4px;
            }
            
            /* Action Buttons */
            .action-toolbar {
                display: flex;
                gap: 12px;
                margin: 24px 0;
                padding: 20px;
                background: var(--surface);
                border-radius: var(--radius-lg);
                border: 1px solid var(--border);
                flex-wrap: wrap;
            }
            
            .btn-modern {
                padding: 10px 20px;
                border-radius: var(--radius-sm);
                font-weight: 600;
                font-size: 13px;
                border: none;
                cursor: pointer;
                transition: all 0.2s ease;
                display: flex;
                align-items: center;
                gap: 8px;
                min-width: 140px;
                justify-content: center;
            }
            
            .btn-modern-primary {
                background: var(--primary);
                color: white;
            }
            
            .btn-modern-primary:hover {
                background: var(--primary-dark);
                transform: translateY(-1px);
                box-shadow: var(--shadow-md);
            }
            
            .btn-modern-secondary {
                background: white;
                color: var(--text-primary);
                border: 1px solid var(--border);
            }
            
            .btn-modern-secondary:hover {
                background: var(--background);
                border-color: var(--primary);
                transform: translateY(-1px);
            }
            
            .btn-modern-outline {
                background: transparent;
                color: var(--primary);
                border: 1px solid var(--primary);
            }
            
            .btn-modern-outline:hover {
                background: var(--primary);
                color: white;
            }
            
            /* Form Sections */
            .section-modern {
                background: var(--surface);
                border-radius: var(--radius-lg);
                padding: 24px;
                margin-bottom: 24px;
                border: 1px solid var(--border);
            }
            
            .section-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 20px;
                padding-bottom: 16px;
                border-bottom: 1px solid var(--border);
            }
            
            .section-title {
                display: flex;
                align-items: center;
                gap: 10px;
                color: var(--text-primary);
                font-size: 16px;
                font-weight: 600;
            }
            
            .section-title-icon {
                width: 32px;
                height: 32px;
                background: linear-gradient(135deg, var(--primary), var(--info));
                border-radius: var(--radius-sm);
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: 14px;
            }
            
            /* Enhanced Grid */
            .grid-modern .grid-heading-row {
                background: var(--background) !important;
                border-bottom: 2px solid var(--border) !important;
            }
            
            .grid-modern .grid-heading-row .grid-static-col {
                color: var(--text-primary) !important;
                font-weight: 600 !important;
                font-size: 11px !important;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .grid-modern .grid-row {
                border-bottom: 1px solid var(--border) !important;
                transition: background-color 0.2s ease;
            }
            
            .grid-modern .grid-row:hover {
                background-color: #f1f5f9 !important;
            }
            
            /* Status Indicators */
            .status-badge {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.3px;
            }
            
            .status-success {
                background: #d1fae5;
                color: #065f46;
                border: 1px solid #a7f3d0;
            }
            
            .status-warning {
                background: #fef3c7;
                color: #92400e;
                border: 1px solid #fde68a;
            }
            
            .status-danger {
                background: #fee2e2;
                color: #991b1b;
                border: 1px solid #fecaca;
            }
            
            .status-info {
                background: #dbeafe;
                color: #1e40af;
                border: 1px solid #bfdbfe;
            }
            
            /* Data Visualization */
            .progress-bar {
                height: 8px;
                background: var(--border);
                border-radius: 4px;
                overflow: hidden;
                margin-top: 8px;
            }
            
            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, var(--primary), var(--info));
                border-radius: 4px;
                transition: width 0.3s ease;
            }
            
            /* Notification Bubbles */
            .notification-bubble {
                position: absolute;
                top: -6px;
                right: -6px;
                background: var(--danger);
                color: white;
                font-size: 10px;
                font-weight: 700;
                padding: 2px 6px;
                border-radius: 10px;
                min-width: 18px;
                text-align: center;
                border: 2px solid var(--surface);
            }
            
            /* Loading States */
            .loading-shimmer {
                background: linear-gradient(90deg, 
                    var(--background) 0%, 
                    #f1f5f9 50%, 
                    var(--background) 100%);
                background-size: 200% 100%;
                animation: shimmer 1.5s infinite;
                border-radius: var(--radius-sm);
            }
            
            @keyframes shimmer {
                0% { background-position: -200% 0; }
                100% { background-position: 200% 0; }
            }
            
            /* Responsive Adjustments */
            @media (max-width: 768px) {
                .metrics-grid {
                    grid-template-columns: repeat(2, 1fr);
                }
                
                .action-toolbar {
                    flex-direction: column;
                }
                
                .btn-modern {
                    width: 100%;
                }
            }
            
            /* Custom Field Styling */
            .field-highlight {
                background: linear-gradient(90deg, #f0f9ff, #e0f2fe) !important;
                border: 1px solid #7dd3fc !important;
                border-radius: var(--radius-sm) !important;
            }
            
            .field-warning {
                background: linear-gradient(90deg, #fefce8, #fef9c3) !important;
                border: 1px solid #fde047 !important;
                border-radius: var(--radius-sm) !important;
            }
            
            .field-danger {
                background: linear-gradient(90deg, #fef2f2, #fee2e2) !important;
                border: 1px solid #fca5a5 !important;
                border-radius: var(--radius-sm) !important;
            }
        </style>
    `);
}

function setup_modern_layout(frm) {
    // Add modern layout classes
    setTimeout(() => {
        $(frm.wrapper).addClass('modern-expense-batch');
        $('.form-layout').css({
            'background': 'var(--background)',
            'padding': '20px'
        });
    }, 100);
}

// ============================================
// DASHBOARD COMPONENTS
// ============================================

function create_dashboard_header(frm) {
    $('.dashboard-header').remove();
    
    const status = frm.doc.docstatus;
    let statusBadge = '';
    
    if (status === 0) {
        statusBadge = '<span class="status-badge status-info">Draft</span>';
    } else if (status === 1) {
        statusBadge = '<span class="status-badge status-success">Submitted</span>';
    } else if (status === 2) {
        statusBadge = '<span class="status-badge status-danger">Cancelled</span>';
    }
    
    const headerHtml = `
        <div class="dashboard-header">
            <div class="header-title">
                <div class="header-title-icon">
                    <i class="fa fa-wallet"></i>
                </div>
                <div class="header-title-text">
                    <h3>Expense Batch ${frm.doc.name ? '• ' + frm.doc.name : ''}</h3>
                    <p>Manage petty cash transactions with AI-powered insights</p>
                </div>
                ${statusBadge}
            </div>
        </div>
    `;
    
    $(frm.wrapper).find('.form-section:first').before(headerHtml);
}

function create_financial_metrics(frm) {
    if (!frm.doc.petty_cash_transaction || frm.doc.petty_cash_transaction.length === 0) return;
    
    // Remove existing metrics
    $('.metrics-grid').remove();
    
    const transactions = frm.doc.petty_cash_transaction;
    const outflows = transactions.map(t => flt(t.outflow)).filter(o => o > 0);
    const avgTransaction = outflows.length > 0 ? outflows.reduce((a, b) => a + b, 0) / outflows.length : 0;
    const largestTransaction = outflows.length > 0 ? Math.max(...outflows) : 0;
    const budgetUsed = flt(frm.doc.opening_balance) > 0 ? 
        (flt(frm.doc.total_outflow) / flt(frm.doc.opening_balance) * 100).toFixed(1) : 0;
    const netFlow = flt(frm.doc.total_inflow) - flt(frm.doc.total_outflow);
    const days = frm.doc.batch_start_date && frm.doc.batch_end_date ? 
        frappe.datetime.get_day_diff(frm.doc.batch_end_date, frm.doc.batch_start_date) + 1 : 'N/A';
    const dailyAvg = days !== 'N/A' ? flt(frm.doc.total_outflow) / days : 0;
    
    const metricsHtml = `
        <div class="metrics-grid">
            <div class="metric-card balance">
                <div class="metric-icon primary">
                    <i class="fa fa-piggy-bank"></i>
                </div>
                <div class="metric-value">${format_currency(frm.doc.balance, frm.doc.account_currency)}</div>
                <div class="metric-label">Current Balance</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${budgetUsed > 100 ? 100 : budgetUsed}%"></div>
                </div>
            </div>
            
            <div class="metric-card outflow">
                <div class="metric-icon danger">
                    <i class="fa fa-arrow-up"></i>
                </div>
                <div class="metric-value">${format_currency(frm.doc.total_outflow, frm.doc.account_currency)}</div>
                <div class="metric-label">Total Outflow</div>
                <div class="metric-subtitle">
                    <i class="fa fa-chart-line"></i>
                    ${budgetUsed}% of budget
                </div>
            </div>
            
            <div class="metric-card inflow">
                <div class="metric-icon success">
                    <i class="fa fa-arrow-down"></i>
                </div>
                <div class="metric-value">${format_currency(frm.doc.total_inflow, frm.doc.account_currency)}</div>
                <div class="metric-label">Total Inflow</div>
                <div class="metric-subtitle">
                    <i class="fa fa-exchange-alt"></i>
                    Net: ${format_currency(netFlow, frm.doc.account_currency)}
                </div>
            </div>
            
            <div class="metric-card overview">
                <div class="metric-icon info">
                    <i class="fa fa-chart-pie"></i>
                </div>
                <div class="metric-value">${transactions.length}</div>
                <div class="metric-label">Transactions</div>
                <div class="metric-subtitle">
                    <i class="fa fa-calculator"></i>
                    Avg: ${format_currency(avgTransaction, frm.doc.account_currency)}
                </div>
            </div>
        </div>
    `;
    
    $('.dashboard-header').append(metricsHtml);
}

// ============================================
// ACTION BUTTONS
// ============================================

function add_professional_action_buttons(frm) {
    if (frm.is_new()) return;
    
    // Remove existing buttons
    $('.action-toolbar').remove();
    
    const hasTransactions = frm.doc.petty_cash_transaction && frm.doc.petty_cash_transaction.length > 0;
    const anomalyCount = count_anomalies(frm);
    
    const buttonsHtml = `
        <div class="action-toolbar">
            <button class="btn-modern btn-modern-primary" id="btn-ai-analysis">
                <i class="fa fa-robot"></i>
                AI Analysis
                ${anomalyCount > 0 ? `<span class="notification-bubble">${anomalyCount}</span>` : ''}
            </button>
            
            <button class="btn-modern btn-modern-secondary" id="btn-check-issues">
                <i class="fa fa-search"></i>
                Check Issues
            </button>
            
            <button class="btn-modern btn-modern-secondary" id="btn-insights">
                <i class="fa fa-chart-bar"></i>
                Insights
            </button>
            
            <button class="btn-modern btn-modern-secondary" id="btn-duplicates">
                <i class="fa fa-copy"></i>
                Duplicates
            </button>
            
            ${hasTransactions ? `
                <button class="btn-modern btn-modern-outline" id="btn-export">
                    <i class="fa fa-file-export"></i>
                    Export
                </button>
            ` : ''}

            ${frm.doc.docstatus === 0 ? `
                <button class="btn-modern btn-modern-outline" id="btn-import">
                    <i class="fa fa-file-import"></i>
                    Import
                </button>
            ` : ''}
        </div>
    `;
    
    $('.dashboard-header').after(buttonsHtml);
    
    // Add event listeners
    $('#btn-ai-analysis').click(() => analyze_with_ai(frm));
    $('#btn-check-issues').click(() => check_anomalies(frm, true));
    $('#btn-insights').click(() => show_insights_dialog(frm));
    $('#btn-duplicates').click(() => check_duplicate_payments(frm));
    $('#btn-export').click(() => export_expenses(frm));
    $('#btn-import').click(() => ecclesia.batch_excel.import_dialog(frm, _EB_XL));
}

function count_anomalies(frm) {
    const transactions = frm.doc.petty_cash_transaction || [];
    if (transactions.length === 0) return 0;
    
    let count = 0;
    const outflows = transactions.map(t => flt(t.outflow)).filter(o => o > 0);
    const avg = outflows.length > 0 ? outflows.reduce((a, b) => a + b, 0) / outflows.length : 0;
    
    transactions.forEach(trans => {
        if (flt(trans.outflow) > avg * 3 && avg > 0) count++;
        if (!trans.transaction_description || trans.transaction_description.trim() === '') count++;
        if (!trans.beneficiary || trans.beneficiary.trim() === '') count++;
    });
    
    return count;
}

// ============================================
// GRID STYLING
// ============================================

function apply_modern_grid_styling(frm) {
    setTimeout(() => {
        if (frm.fields_dict.petty_cash_transaction && frm.fields_dict.petty_cash_transaction.grid) {
            const grid = frm.fields_dict.petty_cash_transaction.grid;
            $(grid.wrapper).addClass('grid-modern');
            
            // Apply zebra striping
            grid.wrapper.find('.grid-row').each(function(i, row) {
                $(row).css({
                    'background-color': i % 2 === 0 ? '#ffffff' : '#f8fafc',
                    'border-bottom': '1px solid #e2e8f0',
                    'transition': 'background-color 0.2s ease'
                });
                
                $(row).hover(
                    function() { $(this).css('background-color', '#f1f5f9'); },
                    function() { $(this).css('background-color', i % 2 === 0 ? '#ffffff' : '#f8fafc'); }
                );
            });
        }
    }, 300);
}

function highlight_key_fields(frm) {
    // Reset classes
    ['balance', 'total_outflow', 'total_inflow'].forEach(field => {
        if (frm.fields_dict[field]) {
            frm.fields_dict[field].$input
                .removeClass('field-highlight field-warning field-danger');
        }
    });
    
    // Apply appropriate highlighting
    if (frm.doc.balance < 0) {
        frm.fields_dict.balance.$input.addClass('field-danger');
    } else if (frm.doc.balance > frm.doc.opening_balance * 1.5) {
        frm.fields_dict.balance.$input.addClass('field-highlight');
    } else if (frm.doc.balance < frm.doc.opening_balance * 0.3) {
        frm.fields_dict.balance.$input.addClass('field-warning');
    }
    
    if (frm.doc.total_outflow > frm.doc.opening_balance * 0.8) {
        frm.fields_dict.total_outflow.$input.addClass('field-warning');
    }
}

// ============================================
// CALCULATION FUNCTIONS
// ============================================

function calculate_all_totals(frm) {
    let total_inflow = 0;
    let total_outflow = 0;
    let running_balance = flt(frm.doc.opening_balance);

    $.each(frm.doc.petty_cash_transaction || [], function(i, row) {
        total_inflow += flt(row.inflow);
        total_outflow += flt(row.outflow);
        running_balance += flt(row.inflow) - flt(row.outflow);
        frappe.model.set_value(row.doctype, row.name, "balance", running_balance);
    });

    frm.set_value('total_inflow', total_inflow);
    frm.set_value('total_outflow', total_outflow);
    frm.set_value('balance', running_balance);
    
    frm.refresh_field('petty_cash_transaction');
    create_financial_metrics(frm);
}

function propagate_cost_center(frm) {
    if (!frm.doc.cost_center) return;
    
    $.each(frm.doc.petty_cash_transaction || [], function(i, row) {
        frappe.model.set_value(row.doctype, row.name, "cost_center", frm.doc.cost_center);
    });
}

// ============================================
// AUTO-POPULATION FUNCTIONS
// ============================================

function auto_populate_employee_details(frm) {
    if (frm.doc.cost_center && frm.doc.prepared_by) return;
    
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Employee',
            filters: { user_id: frappe.session.user },
            fields: ['payroll_cost_center', 'name', 'employee_name']
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                let emp = r.message[0];
                if (!frm.doc.cost_center) {
                    frm.set_value('cost_center', emp.payroll_cost_center);
                }
                if (!frm.doc.prepared_by) {
                    frm.set_value('prepared_by', frappe.session.user);
                }
                if (!frm.doc.employee_name) {
                    frm.set_value('employee_name', emp.employee_name);
                }
            }
        }
    });
}


function update_month_display(frm) {
    if (!frm.doc.batch_start_date) return;
    
    let date = new Date(frm.doc.batch_start_date);
    let month = date.toLocaleString('default', { month: 'long' });
    frm.set_value('month', month);
}

// ============================================
// AI & SMART FEATURES
// ============================================

function analyze_with_ai(frm) {
    show_toast_message('Starting AI analysis...', 'info');
    
    // Add loading state
    $('#btn-ai-analysis').addClass('loading-shimmer');
    
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.expense_batch.expense_batch.analyze_expense_batch',
        args: { doc: frm.doc },
        callback: function(r) {
            $('#btn-ai-analysis').removeClass('loading-shimmer');
            if (r.message) {
                show_professional_ai_results(frm, r.message);
            } else {
                show_professional_manual_analysis(frm);
            }
        },
        error: function() {
            $('#btn-ai-analysis').removeClass('loading-shimmer');
            show_professional_manual_analysis(frm);
        }
    });
}

function show_professional_manual_analysis(frm) {
    let transactions = frm.doc.petty_cash_transaction || [];
    if (transactions.length === 0) return;
    
    let outflows = transactions.map(t => flt(t.outflow)).filter(o => o > 0);
    let avg = outflows.reduce((a, b) => a + b, 0) / outflows.length;
    let total = flt(frm.doc.total_outflow);
    let budget_used = (total / flt(frm.doc.opening_balance) * 100).toFixed(1);
    
    let analysis = {
        summary: `Analyzed ${transactions.length} transactions with average amount ${format_currency(avg, frm.doc.account_currency)}`,
        recommendations: [],
        risks: []
    };
    
    if (budget_used > 80) {
        analysis.recommendations.push('Budget utilization is high (>80%). Consider requesting additional funds.');
    }
    
    if (budget_used > 100) {
        analysis.risks.push('Budget exceeded! Balance is negative.');
    }
    
    let large_trans = transactions.filter(t => flt(t.outflow) > avg * 3);
    if (large_trans.length > 0) {
        analysis.risks.push(`${large_trans.length} transaction(s) are significantly larger than average.`);
    }
    
    show_professional_ai_results(frm, analysis);
}

function show_professional_ai_results(frm, analysis) {
    let html = `
        <div style="padding: 20px;">
            <div class="section-header" style="border: none; padding: 0; margin: 0 0 20px 0;">
                <div class="section-title">
                    <div class="section-title-icon">
                        <i class="fa fa-robot"></i>
                    </div>
                    <div>AI Analysis Results</div>
                </div>
            </div>
            
            <div style="background: #f8fafc; padding: 16px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #e2e8f0;">
                <div style="color: #4a5568; font-size: 14px; line-height: 1.6;">${analysis.summary || 'No summary available'}</div>
            </div>
            
            ${analysis.recommendations && analysis.recommendations.length > 0 ? `
                <div style="background: linear-gradient(90deg, #f0fff4, #dcfce7); padding: 16px; border-radius: 8px; margin-bottom: 16px; border: 1px solid #86efac;">
                    <div style="color: #166534; font-weight: 600; margin-bottom: 10px; font-size: 14px; display: flex; align-items: center; gap: 8px;">
                        <i class="fa fa-lightbulb"></i> Recommendations
                    </div>
                    <div style="color: #15803d; font-size: 13px; line-height: 1.6;">
                        ${analysis.recommendations.map(rec => `
                            <div style="margin-bottom: 6px; padding-left: 8px; border-left: 3px solid #22c55e;">${rec}</div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
            
            ${analysis.risks && analysis.risks.length > 0 ? `
                <div style="background: linear-gradient(90deg, #fef2f2, #fee2e2); padding: 16px; border-radius: 8px; border: 1px solid #fca5a5;">
                    <div style="color: #991b1b; font-weight: 600; margin-bottom: 10px; font-size: 14px; display: flex; align-items: center; gap: 8px;">
                        <i class="fa fa-exclamation-triangle"></i> Risk Factors
                    </div>
                    <div style="color: #dc2626; font-size: 13px; line-height: 1.6;">
                        ${analysis.risks.map(risk => `
                            <div style="margin-bottom: 6px; padding-left: 8px; border-left: 3px solid #ef4444;">${risk}</div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
        </div>
    `;
    
    frappe.msgprint({
        title: __('AI Analysis Report'),
        indicator: 'blue',
        message: html,
        width: 450,
        min_width: 450
    });
}

function auto_categorize_expense(description) {
    const categories = {
        'Transport': ['taxi', 'uber', 'fuel', 'transport', 'bus', 'vehicle', 'logistics'],
        'Meals': ['lunch', 'dinner', 'breakfast', 'food', 'restaurant', 'meal', 'catering'],
        'Supplies': ['stationery', 'supplies', 'office', 'paper', 'pen', 'material'],
        'Utilities': ['electricity', 'water', 'internet', 'phone', 'utility', 'telecom'],
        'Maintenance': ['repair', 'maintenance', 'fix', 'service', 'cleaning'],
        'Professional': ['consultant', 'legal', 'audit', 'professional', 'advisory']
    };
    
    let desc_lower = description.toLowerCase();
    let detected = 'Other';
    
    for (let category in categories) {
        if (categories[category].some(keyword => desc_lower.includes(keyword))) {
            detected = category;
            break;
        }
    }
    
    show_toast_message(`Auto-categorized as: ${detected}`, 'info');
}

// ============================================
// ANOMALY DETECTION
// ============================================

function check_anomalies(frm, show_success = false) {
    let transactions = frm.doc.petty_cash_transaction || [];
    if (transactions.length === 0) return;
    
    let anomalies = [];
    let outflows = transactions.map(t => flt(t.outflow)).filter(o => o > 0);
    
    if (outflows.length === 0) return;
    
    let avg = outflows.reduce((a, b) => a + b, 0) / outflows.length;
    
    transactions.forEach((trans, idx) => {
        // Large transactions
        if (flt(trans.outflow) > avg * 3 && avg > 0) {
            anomalies.push({
                severity: 'high',
                message: `Row ${idx + 1}: Large transaction (${format_currency(trans.outflow)})`,
                amount: trans.outflow
            });
        }
        
        // Missing description
        if (!trans.transaction_description || trans.transaction_description.trim() === '') {
            anomalies.push({
                severity: 'high',
                message: `Row ${idx + 1}: Missing description`,
                amount: trans.outflow
            });
        }
        
        // Missing beneficiary
        if (!trans.beneficiary || trans.beneficiary.trim() === '') {
            anomalies.push({
                severity: 'medium',
                message: `Row ${idx + 1}: Missing beneficiary`,
                amount: trans.outflow
            });
        }
        
        // Weekend transactions
        if (trans.date) {
            let day = new Date(trans.date).getDay();
            if (day === 0 || day === 6) {
                anomalies.push({
                    severity: 'low',
                    message: `Row ${idx + 1}: Weekend transaction`,
                    amount: trans.outflow
                });
            }
        }
    });
    
    if (anomalies.length > 0) {
        show_professional_anomalies_dialog(anomalies);
    } else if (show_success) {
        show_toast_message('No anomalies detected', 'success');
    }
}

function show_professional_anomalies_dialog(anomalies) {
    let highCount = anomalies.filter(a => a.severity === 'high').length;
    let mediumCount = anomalies.filter(a => a.severity === 'medium').length;
    let lowCount = anomalies.filter(a => a.severity === 'low').length;
    
    let html = `
        <div style="padding: 20px;">
            <div class="section-header" style="border: none; padding: 0; margin: 0 0 20px 0;">
                <div class="section-title">
                    <div class="section-title-icon" style="background: linear-gradient(135deg, #f59e0b, #f97316);">
                        <i class="fa fa-exclamation-triangle"></i>
                    </div>
                    <div>Issue Detection</div>
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 20px;">
                <div style="background: #fef2f2; padding: 12px; border-radius: 8px; text-align: center; border: 1px solid #fecaca;">
                    <div style="font-size: 20px; font-weight: 700; color: #dc2626;">${highCount}</div>
                    <div style="font-size: 11px; color: #991b1b; font-weight: 600;">High Priority</div>
                </div>
                <div style="background: #fffbeb; padding: 12px; border-radius: 8px; text-align: center; border: 1px solid #fde68a;">
                    <div style="font-size: 20px; font-weight: 700; color: #d97706;">${mediumCount}</div>
                    <div style="font-size: 11px; color: #92400e; font-weight: 600;">Medium Priority</div>
                </div>
                <div style="background: #eff6ff; padding: 12px; border-radius: 8px; text-align: center; border: 1px solid #bfdbfe;">
                    <div style="font-size: 20px; font-weight: 700; color: #2563eb;">${lowCount}</div>
                    <div style="font-size: 11px; color: #1e40af; font-weight: 600;">Low Priority</div>
                </div>
            </div>
            
            <div style="max-height: 300px; overflow-y: auto;">
    `;
    
    anomalies.forEach(anomaly => {
        let icon = anomaly.severity === 'high' ? '🚨' : 
                   anomaly.severity === 'medium' ? '⚠️' : 'ℹ️';
        let color = anomaly.severity === 'high' ? '#dc2626' :
                    anomaly.severity === 'medium' ? '#d97706' : '#2563eb';
        let bgColor = anomaly.severity === 'high' ? '#fef2f2' :
                      anomaly.severity === 'medium' ? '#fffbeb' : '#eff6ff';
        let borderColor = anomaly.severity === 'high' ? '#fecaca' :
                          anomaly.severity === 'medium' ? '#fde68a' : '#bfdbfe';
        
        html += `
            <div style="background: ${bgColor}; border-left: 4px solid ${color}; padding: 12px; margin-bottom: 8px; border-radius: 6px; border: 1px solid ${borderColor};">
                <div style="display: flex; align-items: flex-start; gap: 10px;">
                    <div style="font-size: 16px; margin-top: 2px;">${icon}</div>
                    <div style="flex: 1;">
                        <div style="font-weight: 600; color: ${color}; font-size: 13px; text-transform: uppercase; letter-spacing: 0.3px;">
                            ${anomaly.severity} Priority
                        </div>
                        <div style="font-weight: 500; color: #4a5568; font-size: 13px; margin-top: 4px;">
                            ${anomaly.message}
                        </div>
                        ${anomaly.amount ? `
                            <div style="font-size: 12px; color: #64748b; margin-top: 4px;">
                                Amount: ${format_currency(anomaly.amount)}
                            </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
    });
    
    html += `
            </div>
        </div>
    `;
    
    frappe.msgprint({
        title: __(`Detected ${anomalies.length} Issue(s)`),
        indicator: 'orange',
        message: html,
        width: 450,
        min_width: 450
    });
}

function check_duplicate_beneficiary(frm, row) {
    if (!row.beneficiary || !row.date) return;
    
    let duplicates = frm.doc.petty_cash_transaction.filter(t => 
        t.name !== row.name &&
        t.beneficiary === row.beneficiary &&
        t.date === row.date
    );
    
    if (duplicates.length > 0) {
        show_toast_message('Duplicate beneficiary on same date', 'warning');
    }
}

function check_weekend_transaction(row) {
    if (!row.date) return;
    
    let day = new Date(row.date).getDay();
    if (day === 0 || day === 6) {
        show_toast_message('Weekend transaction - verify if intended', 'info');
    }
}

function check_duplicate_payments(frm) {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.expense_batch.expense_batch.check_duplicate_payments',
        args: { doc: frm.doc },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                frappe.msgprint({
                    title: __('Duplicate Payments Found'),
                    indicator: 'orange',
                    message: `
                        <div style="padding: 20px; text-align: center;">
                            <div style="width: 64px; height: 64px; background: #fef3c7; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px auto;">
                                <i class="fa fa-exclamation-triangle" style="font-size: 24px; color: #d97706;"></i>
                            </div>
                            <div style="font-size: 20px; font-weight: 700; color: #4a5568; margin-bottom: 8px;">
                                ${r.message.length} Potential Duplicate(s)
                            </div>
                            <div style="font-size: 13px; color: #718096;">
                                Please review these transactions for accuracy
                            </div>
                        </div>
                    `,
                    width: 350
                });
            } else {
                show_toast_message('No duplicates found', 'success');
            }
        }
    });
}

// ============================================
// INSIGHTS DIALOG
// ============================================

function show_insights_dialog(frm) {
    if (!frm.doc.petty_cash_transaction || frm.doc.petty_cash_transaction.length === 0) {
        frappe.msgprint(__('No transactions to analyze'));
        return;
    }
    
    let budget_used = (flt(frm.doc.total_outflow) / flt(frm.doc.opening_balance) * 100).toFixed(1);
    let days = frm.doc.batch_start_date && frm.doc.batch_end_date ? 
        frappe.datetime.get_day_diff(frm.doc.batch_end_date, frm.doc.batch_start_date) + 1 : 'N/A';
    let daily_avg = days !== 'N/A' ? flt(frm.doc.total_outflow) / days : 0;
    let net_flow = flt(frm.doc.total_inflow) - flt(frm.doc.total_outflow);
    let transaction_count = frm.doc.petty_cash_transaction.length;
    let outflows = frm.doc.petty_cash_transaction.map(t => flt(t.outflow)).filter(o => o > 0);
    let largest_transaction = outflows.length > 0 ? Math.max(...outflows) : 0;
    
    let html = `
        <div style="padding: 20px;">
            <div class="section-header" style="border: none; padding: 0; margin: 0 0 20px 0;">
                <div class="section-title">
                    <div class="section-title-icon" style="background: linear-gradient(135deg, #10b981, #059669);">
                        <i class="fa fa-chart-line"></i>
                    </div>
                    <div>Expense Insights</div>
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 20px;">
                <div style="background: #f8fafc; padding: 12px; border-radius: 8px; border: 1px solid #e2e8f0;">
                    <div style="font-size: 12px; color: #64748b; font-weight: 600; margin-bottom: 4px;">Budget Utilization</div>
                    <div style="font-size: 18px; font-weight: 700; color: ${budget_used > 80 ? '#dc2626' : '#059669'};">${budget_used}%</div>
                </div>
                <div style="background: #f8fafc; padding: 12px; border-radius: 8px; border: 1px solid #e2e8f0;">
                    <div style="font-size: 12px; color: #64748b; font-weight: 600; margin-bottom: 4px;">Period Days</div>
                    <div style="font-size: 18px; font-weight: 700; color: #4a5568;">${days}</div>
                </div>
                <div style="background: #f8fafc; padding: 12px; border-radius: 8px; border: 1px solid #e2e8f0;">
                    <div style="font-size: 12px; color: #64748b; font-weight: 600; margin-bottom: 4px;">Daily Average</div>
                    <div style="font-size: 18px; font-weight: 700; color: #4a5568;">${format_currency(daily_avg)}</div>
                </div>
                <div style="background: #f8fafc; padding: 12px; border-radius: 8px; border: 1px solid #e2e8f0;">
                    <div style="font-size: 12px; color: #64748b; font-weight: 600; margin-bottom: 4px;">Total Transactions</div>
                    <div style="font-size: 18px; font-weight: 700; color: #4a5568;">${transaction_count}</div>
                </div>
            </div>
            
            <div style="background: linear-gradient(90deg, #f8fafc, #f1f5f9); padding: 16px; border-radius: 8px; border: 1px solid #e2e8f0;">
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px;">
                    <div>
                        <div style="font-size: 11px; color: #64748b; font-weight: 600; margin-bottom: 4px;">Opening Balance</div>
                        <div style="font-size: 16px; font-weight: 700; color: #2563eb;">${format_currency(frm.doc.opening_balance)}</div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: #64748b; font-weight: 600; margin-bottom: 4px;">Closing Balance</div>
                        <div style="font-size: 16px; font-weight: 700; color: ${frm.doc.balance < 0 ? '#dc2626' : '#059669'}">${format_currency(frm.doc.balance)}</div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: #64748b; font-weight: 600; margin-bottom: 4px;">Total Outflow</div>
                        <div style="font-size: 16px; font-weight: 700; color: #dc2626;">${format_currency(frm.doc.total_outflow)}</div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: #64748b; font-weight: 600; margin-bottom: 4px;">Total Inflow</div>
                        <div style="font-size: 16px; font-weight: 700; color: #059669;">${format_currency(frm.doc.total_inflow)}</div>
                    </div>
                </div>
                
                <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid #e2e8f0;">
                    <div style="font-size: 12px; color: #64748b; font-weight: 600; margin-bottom: 8px;">Key Metrics</div>
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
                        <div>
                            <div style="font-size: 11px; color: #64748b;">Net Flow</div>
                            <div style="font-size: 14px; font-weight: 600; color: ${net_flow >= 0 ? '#059669' : '#dc2626'}">${format_currency(net_flow)}</div>
                        </div>
                        <div>
                            <div style="font-size: 11px; color: #64748b;">Largest Transaction</div>
                            <div style="font-size: 14px; font-weight: 600; color: #d97706">${format_currency(largest_transaction)}</div>
                        </div>
                        <div>
                            <div style="font-size: 11px; color: #64748b;">Avg Transaction</div>
                            <div style="font-size: 14px; font-weight: 600; color: #4a5568">${format_currency(outflows.length > 0 ? outflows.reduce((a, b) => a + b, 0) / outflows.length : 0)}</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    frappe.msgprint({
        title: __('Expense Insights'),
        indicator: 'blue',
        message: html,
        width: 450,
        min_width: 450
    });
}

// ============================================
// UTILITY FUNCTIONS
// ============================================

function format_currency(amount, currency = 'NGN') {
    if (!amount) amount = 0;
    return frappe.format(amount, {fieldtype: "Currency", options: currency});
}

function flt(val) {
    return parseFloat(val) || 0;
}

function show_toast_message(message, type = 'info') {
    const icons = {
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'info': 'ℹ️'
    };
    
    frappe.show_alert({
        message: `${icons[type] || ''} ${message}`,
        indicator: type === 'error' ? 'red' : type
    }, type === 'error' ? 6 : 4);
}

function export_expenses(frm) {
    ecclesia.batch_excel.export_rows(frm, _EB_XL);
}

// ============================================
// INITIALIZATION
// ============================================

console.log('🏦 Expense Batch Professional UI Loaded');