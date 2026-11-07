// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt
// ========================================
// BATCH BANK TRANSACTION - PROFESSIONAL UI
// Complete Enhanced Client Script
// ========================================

// Wait for page to load
$(document).ready(function() {
    console.log('🏦 Batch Bank Transaction Professional UI Loading...');
    
    // Apply professional styles immediately
    apply_professional_styles();
    
    // Initialize with a small delay to ensure frappe is ready
    setTimeout(initialize_application, 500);
});

function initialize_application() {
    if (typeof frappe === 'undefined') {
        console.log('⏳ Frappe not loaded yet, waiting...');
        setTimeout(initialize_application, 500);
        return;
    }
    
    console.log('✅ Frappe loaded, initializing professional UI...');
    initialize_form_events();
    setup_professional_ui();
}

// ========================================
// PROFESSIONAL UI STYLES 🎨
// ========================================

function apply_professional_styles() {
    if ($('#professional-styles').length > 0) return;
    
    const css = `
        /* Professional UI Container */
        .professional-ui-container {
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin: 0 0 20px 0;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            border: 1px solid #e8e8e8;
            position: relative;
            overflow: hidden;
        }
        
        .professional-ui-container::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 50%, #9b59b6 100%);
        }
        
        /* Header Section */
        .ui-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #f0f2f5;
        }
        
        .ui-header-left h3 {
            margin: 0;
            color: #2c3e50;
            font-size: 18px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .ui-header-left .subtitle {
            color: #7f8c8d;
            font-size: 13px;
            margin-top: 5px;
        }
        
        /* Professional Stats Cards */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin: 20px 0;
        }
        
        .stat-card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            border: 1px solid #e8e8e8;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }
        
        .stat-card.inflow {
            border-left: 4px solid #10b981;
        }
        
        .stat-card.outflow {
            border-left: 4px solid #ef4444;
        }
        
        .stat-card.balance {
            border-left: 4px solid #3b82f6;
        }
        
        .stat-icon {
            font-size: 24px;
            margin-bottom: 10px;
            display: inline-block;
            padding: 8px;
            border-radius: 8px;
            background: #f8fafc;
        }
        
        .stat-card.inflow .stat-icon {
            color: #10b981;
            background: #f0fdf4;
        }
        
        .stat-card.outflow .stat-icon {
            color: #ef4444;
            background: #fef2f2;
        }
        
        .stat-card.balance .stat-icon {
            color: #3b82f6;
            background: #eff6ff;
        }
        
        .stat-value {
            font-size: 22px;
            font-weight: 700;
            color: #1e293b;
            margin: 5px 0;
        }
        
        .stat-label {
            font-size: 12px;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 600;
        }
        
        .stat-trend {
            font-size: 12px;
            margin-top: 5px;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        
        .stat-trend.positive {
            color: #10b981;
        }
        
        .stat-trend.negative {
            color: #ef4444;
        }
        
        /* Action Buttons */
        .action-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin: 20px 0;
        }
        
        @media (min-width: 768px) {
            .action-grid {
                grid-template-columns: repeat(3, 1fr);
            }
        }
        
        @media (min-width: 1024px) {
            .action-grid {
                grid-template-columns: repeat(6, 1fr);
            }
        }
        
        .action-btn {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 15px 10px;
            color: #475569;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
            text-align: center;
            min-height: 80px;
            justify-content: center;
        }
        
        .action-btn:hover {
            background: #f8fafc;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            border-color: #cbd5e1;
        }
        
        .action-btn i {
            font-size: 20px;
            margin-bottom: 5px;
        }
        
        .action-btn.import { border-top: 3px solid #8b5cf6; color: #8b5cf6; }
        .action-btn.export { border-top: 3px solid #10b981; color: #10b981; }
        .action-btn.ai { border-top: 3px solid #ec4899; color: #ec4899; }
        .action-btn.reconcile { border-top: 3px solid #f59e0b; color: #f59e0b; }
        .action-btn.bulk { border-top: 3px solid #3b82f6; color: #3b82f6; }
        .action-btn.report { border-top: 3px solid #6366f1; color: #6366f1; }
        
        /* Enhanced Grid Styling */
        .grid-heading-row {
            background: #f8fafc !important;
            border-bottom: 2px solid #e2e8f0 !important;
        }
        
        .grid-heading-row .grid-row-check,
        .grid-heading-row .grid-static-col {
            color: #475569 !important;                // 475569
            font-weight: 700 !important;
            font-size: 12px !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
        }
        
        .grid-row {
            transition: background-color 0.2s ease;
        }
        
        .grid-row:hover {
            background-color: #ABE0F0 !important;    //#f1f5f9
        }
        
        .grid-row:nth-child(even) {
            background-color: #fafbfc !important;
        }
        
        /* Quick Status Indicators */
        .status-indicator {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
            margin-left: 10px;
        }
        
        .status-draft {
            background: #fef3c7;
            color: #92400e;
            border: 1px solid #fde68a;
        }
        
        .status-submitted {
            background: #d1fae5;
            color: #065f46;
            border: 1px solid #a7f3d0;
        }
        
        .status-cancelled {
            background: #fee2e2;
            color: #991b1b;
            border: 1px solid #fecaca;
        }
        
        /* Progress Bar */
        .progress-container {
            margin: 20px 0;
        }
        
        .progress-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }
        
        .progress-label {
            font-size: 13px;
            color: #475569;
            font-weight: 500;
        }
        
        .progress-percentage {
            font-size: 13px;
            color: #3b82f6;
            font-weight: 600;
        }
        
        .progress-bar {
            height: 8px;
            background: #e2e8f0;
            border-radius: 4px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #3b82f6, #6366f1);
            border-radius: 4px;
            transition: width 0.5s ease;
        }
        
        /* Notification Badge */
        .notification-badge {
            position: absolute;
            top: -5px;
            right: -5px;
            background: #ef4444;
            color: white;
            font-size: 10px;
            font-weight: 600;
            padding: 2px 6px;
            border-radius: 10px;
            min-width: 18px;
            text-align: center;
            border: 2px solid white;
        }
        
        /* Loading Animation */
        .loading-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255, 255, 255, 0.9);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            border-radius: 12px;
        }
        
        .loading-spinner {
            width: 40px;
            height: 40px;
            border: 3px solid #e2e8f0;
            border-top-color: #3b82f6;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-bottom: 15px;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: #64748b;
        }
        
        .empty-state i {
            font-size: 48px;
            color: #cbd5e1;
            margin-bottom: 15px;
            display: block;
        }
        
        .empty-state h4 {
            color: #475569;
            margin-bottom: 10px;
        }
        
        /* Alert Cards */
        .alert-card {
            padding: 15px;
            border-radius: 10px;
            margin: 15px 0;
            border-left: 4px solid;
            background: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        
        .alert-info {
            border-left-color: #3b82f6;
            background: #eff6ff;
        }
        
        .alert-success {
            border-left-color: #10b981;
            background: #f0fdf4;
        }
        
        .alert-warning {
            border-left-color: #f59e0b;
            background: #fffbeb;
        }
        
        .alert-error {
            border-left-color: #ef4444;
            background: #fef2f2;
        }
        
        /* Tooltip */
        .professional-tooltip {
            position: relative;
        }
        
        .professional-tooltip:hover::after {
            content: attr(data-tooltip);
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            background: #1e293b;
            color: white;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 12px;
            white-space: nowrap;
            z-index: 1000;
            margin-bottom: 5px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        .professional-tooltip:hover::before {
            content: '';
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            border: 5px solid transparent;
            border-top-color: #1e293b;
            margin-bottom: -5px;
            z-index: 1000;
        }
    `;
    
    $('<style id="professional-styles">' + css + '</style>').appendTo('head');
    console.log('🎨 Professional styles applied');
}

// ========================================
// PROFESSIONAL UI SETUP
// ========================================

function setup_professional_ui() {
    console.log('🔧 Setting up professional UI...');
    
    // Wait for form to be available
    const checkForm = setInterval(() => {
        if (cur_frm) {
            clearInterval(checkForm);
            create_professional_ui(cur_frm);
        }
    }, 200);
}

function create_professional_ui(frm) {
    if (!frm || !frm.$wrapper) {
        console.log('⚠️ Form wrapper not found, retrying...');
        setTimeout(() => create_professional_ui(frm), 300);
        return;
    }
    
    // Remove existing UI container
    $('.professional-ui-container').remove();
    
    // Create professional UI container
    const uiHtml = `
        <div class="professional-ui-container">
            <div class="ui-header">
                <div class="ui-header-left">
                    <h3>
                        <i class="fa fa-bank"></i>
                        Batch Bank Transaction
                        ${get_status_indicator(frm)}
                    </h3>
                    <div class="subtitle">Manage multiple bank transactions efficiently</div>
                </div>
                <div class="ui-header-right">
                    ${get_progress_indicator(frm)}
                </div>
            </div>
            
            <div class="stats-grid" id="professional-stats">
                ${get_stats_placeholder()}
            </div>
            
            <div class="action-grid">
                <button class="action-btn import" data-action="import" data-tooltip="Import from CSV/Excel">
                    <i class="fa fa-file-import"></i>
                    <span>Import</span>
                </button>
                <button class="action-btn export" data-action="export" data-tooltip="Export to Excel">
                    <i class="fa fa-file-export"></i>
                    <span>Export</span>
                </button>
                <button class="action-btn ai" data-action="ai" data-tooltip="AI Analysis & Suggestions">
                    <i class="fa fa-robot"></i>
                    <span>AI Analysis</span>
                </button>
                <button class="action-btn reconcile" data-action="reconcile" data-tooltip="Reconcile with Bank">
                    <i class="fa fa-balance-scale"></i>
                    <span>Reconcile</span>
                </button>
                <button class="action-btn bulk" data-action="bulk" data-tooltip="Bulk Update">
                    <i class="fa fa-cogs"></i>
                    <span>Bulk Update</span>
                </button>
                <button class="action-btn report" data-action="report" data-tooltip="Generate Report">
                    <i class="fa fa-chart-bar"></i>
                    <span>Report</span>
                </button>
            </div>
            
            <div id="alerts-container"></div>
        </div>
    `;
    
    // Insert at the top of the form
    $(frm.$wrapper).find('.form-page:first').prepend(uiHtml);
    
    // Attach event handlers
    attach_professional_handlers(frm);
    
    // Update stats
    update_professional_stats(frm);
    
    console.log('✅ Professional UI created');
}

function get_status_indicator(frm) {
    const status = frm.doc.docstatus;
    let statusHtml = '';
    
    switch(status) {
        case 0:
            statusHtml = '<span class="status-indicator status-draft"><i class="fa fa-edit"></i> Draft</span>';
            break;
        case 1:
            statusHtml = '<span class="status-indicator status-submitted"><i class="fa fa-check-circle"></i> Submitted</span>';
            break;
        case 2:
            statusHtml = '<span class="status-indicator status-cancelled"><i class="fa fa-times-circle"></i> Cancelled</span>';
            break;
    }
    
    return statusHtml;
}

function get_progress_indicator(frm) {
    const total = frm.doc.transaction_entry ? frm.doc.transaction_entry.length : 0;
    const completed = frm.doc.transaction_entry ? 
        frm.doc.transaction_entry.filter(t => t.remark && t.remark.length >= 5 && t.cost_center).length : 0;
    const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;
    
    return `
        <div class="progress-container">
            <div class="progress-header">
                <span class="progress-label">Completion</span>
                <span class="progress-percentage">${percentage}%</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${percentage}%"></div>
            </div>
        </div>
    `;
}

function get_stats_placeholder() {
    return `
        <div class="stat-card inflow">
            <div class="stat-icon">
                <i class="fa fa-arrow-down"></i>
            </div>
            <div class="stat-value">--</div>
            <div class="stat-label">Total Inflow</div>
            <div class="stat-trend positive">
                <i class="fa fa-arrow-up"></i>
                Loading...
            </div>
        </div>
        <div class="stat-card outflow">
            <div class="stat-icon">
                <i class="fa fa-arrow-up"></i>
            </div>
            <div class="stat-value">--</div>
            <div class="stat-label">Total Outflow</div>
            <div class="stat-trend negative">
                <i class="fa fa-arrow-down"></i>
                Loading...
            </div>
        </div>
        <div class="stat-card balance">
            <div class="stat-icon">
                <i class="fa fa-balance-scale"></i>
            </div>
            <div class="stat-value">--</div>
            <div class="stat-label">Current Balance</div>
            <div class="stat-trend">
                <i class="fa fa-sync"></i>
                Calculating...
            </div>
        </div>
    `;
}

function update_professional_stats(frm) {
    if (!frm || !frm.doc) return;
    
    let total_inflow = 0;
    let total_outflow = 0;
    
    if (frm.doc.transaction_entry && frm.doc.transaction_entry.length > 0) {
        frm.doc.transaction_entry.forEach(row => {
            total_inflow += flt(row.inflow || 0);
            total_outflow += flt(row.outflow || 0);
        });
    }
    
    const opening_balance = flt(frm.doc.opening_balance || 0);
    const balance = opening_balance + total_inflow - total_outflow;
    const currency = frm.doc.bank_account_currency || 'NGN';
    
    const statsHtml = `
        <div class="stat-card inflow">
            <div class="stat-icon">
                <i class="fa fa-arrow-down"></i>
            </div>
            <div class="stat-value">${format_currency(total_inflow, currency)}</div>
            <div class="stat-label">Total Inflow</div>
            <div class="stat-trend ${total_inflow > 0 ? 'positive' : ''}">
                <i class="fa fa-arrow-up"></i>
                ${frm.doc.transaction_entry ? frm.doc.transaction_entry.filter(t => t.inflow > 0).length : 0} transactions
            </div>
        </div>
        <div class="stat-card outflow">
            <div class="stat-icon">
                <i class="fa fa-arrow-up"></i>
            </div>
            <div class="stat-value">${format_currency(total_outflow, currency)}</div>
            <div class="stat-label">Total Outflow</div>
            <div class="stat-trend ${total_outflow > 0 ? 'negative' : ''}">
                <i class="fa fa-arrow-down"></i>
                ${frm.doc.transaction_entry ? frm.doc.transaction_entry.filter(t => t.outflow > 0).length : 0} transactions
            </div>
        </div>
        <div class="stat-card balance">
            <div class="stat-icon">
                <i class="fa fa-balance-scale"></i>
            </div>
            <div class="stat-value">${format_currency(balance, currency)}</div>
            <div class="stat-label">Current Balance</div>
            <div class="stat-trend">
                <i class="fa fa-sync"></i>
                Opening: ${format_currency(opening_balance, currency)}
            </div>
        </div>
    `;
    
    $('#professional-stats').html(statsHtml);
}

function attach_professional_handlers(frm) {
    console.log('🔗 Attaching professional handlers...');
    
    // Clear any existing handlers
    $('[data-action]').off('click');
    
    // Add tooltip functionality
    $('[data-tooltip]').addClass('professional-tooltip');
    
    // Import button
    $('[data-action="import"]').on('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        show_import_dialog(frm);
    });
    
    // Export button
    $('[data-action="export"]').on('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        export_to_excel(frm);
    });
    
    // AI button
    $('[data-action="ai"]').on('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        show_loading(frm, 'Analyzing with AI...');
        get_ai_suggestions(frm);
    });
    
    // Reconcile button
    $('[data-action="reconcile"]').on('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        reconcile_batch(frm);
    });
    
    // Bulk button
    $('[data-action="bulk"]').on('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        show_bulk_update_dialog(frm);
    });
    
    // Report button
    $('[data-action="report"]').on('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        generate_batch_report(frm);
    });
}

// ========================================
// ENHANCED FORM EVENTS
// ========================================

function initialize_form_events() {
    console.log('🔧 Initializing enhanced form events...');
    
    frappe.ui.form.on("Batch Bank Transaction", {
        onload: function(frm) {
            console.log("✨ Batch Bank Transaction loaded with professional UI!");
            
            // Setup grid field queries
            setup_grid_queries(frm);
            
            // Auto-create first row
            if (!frm.doc.transaction_entry || frm.doc.transaction_entry.length === 0) {
                add_smart_default_row(frm);
            }

            // Setup keyboard shortcuts
            setup_keyboard_shortcuts(frm);
            
            // Enable auto-save
            enable_auto_save(frm);
            
            // Show initial stats
            setTimeout(() => update_professional_stats(frm), 300);
            
            // Check for alerts
            check_for_alerts(frm);
        },

        refresh: function(frm) {
            console.log("🔄 Form refreshed");
            
            // Update professional UI
            update_professional_ui(frm);
            
            // Update stats
            update_professional_stats(frm);
            
            // Update party names
            update_party_names(frm);
        },

        bank_account: function(frm) {
            console.log("🏦 Bank account selected:", frm.doc.bank_account);
            
            if (frm.doc.bank_account) {
                show_loading(frm, 'Loading bank details...');
                
                frappe.call({
                    method: 'frappe.client.get_value',
                    args: {
                        doctype: 'Bank Account',
                        filters: { name: frm.doc.bank_account },
                        fieldname: ['account', 'account_currency', 'bank', 'company']
                    },
                    callback: function(r) {
                        hide_loading(frm);
                        if (r.message) {
                            frm.set_value('bank_gl', r.message.account);
                            frm.set_value('bank_account_currency', r.message.account_currency);
                            
                            if (r.message.company && !frm.doc.company) {
                                frm.set_value('company', r.message.company);
                            }
                            
                            update_naming_series(frm);
                            frm.refresh_field('bank_gl');
                            frm.refresh_field('bank_account_currency');
                            
                            if (!frm.doc.opening_balance) {
                                get_bank_balance(frm);
                            }
                            
                            setTimeout(() => update_professional_stats(frm), 200);
                            show_alert(frm, 'Bank account details loaded successfully', 'success');
                        }
                    }
                });
            }
        },

        before_save: function(frm) {
            if (!validate_batch(frm)) {
                frappe.validated = false;
                return;
            }
            
            calculate_totals(frm);
            generate_reference_numbers(frm);
            update_party_names(frm);
            
            // Show save notification
            show_alert(frm, 'Saving batch...', 'info');
        },

        after_save: function(frm) {
            show_alert(frm, 'Batch saved successfully!', 'success');
            update_professional_ui(frm);
            setTimeout(() => update_professional_stats(frm), 200);
        },

        before_submit: function(frm) {
            return validate_before_submit(frm);
        },

        after_submit: function(frm) {
            show_alert(frm, 'Batch submitted successfully!', 'success');
            update_professional_ui(frm);
        },

        validate: function(frm) {
            validate_duplicate_references(frm);
            validate_balance_integrity(frm);
        }
    });

    // Transaction Entry events
    frappe.ui.form.on("Transaction Entry", {
        trans_type: function(frm, cdt, cdn) {
            let row = locals[cdt][cdn];
            handle_trans_type_change(frm, row, cdt, cdn);
            update_professional_stats(frm);
        },

        remark: function(frm, cdt, cdn) {
            let row = locals[cdt][cdn];
            if (row.remark && !row.party) {
                auto_categorize_transaction(frm, row, cdt, cdn);
            }
            update_professional_ui(frm);
        },

        amount: function(frm, cdt, cdn) {
            let row = locals[cdt][cdn];
            calculate_row_amounts(frm, row, cdt, cdn);
            setTimeout(() => update_professional_stats(frm), 100);
        },

        party: function(frm, cdt, cdn) {
            let row = locals[cdt][cdn];
            fetch_party_details(frm, row, cdt, cdn);
        },

        transaction_currency: function(frm, cdt, cdn) {
            let row = locals[cdt][cdn];
            handle_currency_change(frm, row, cdt, cdn);
        },

        exch_rate: function(frm, cdt, cdn) {
            let row = locals[cdt][cdn];
            recalculate_amounts(frm, row, cdt, cdn);
        },

        frequency: function(frm, cdt, cdn) {
            let row = locals[cdt][cdn];
            handle_recurring_transaction(frm, row, cdt, cdn);
        },

        posting_date: function(frm, cdt, cdn) {
            let row = locals[cdt][cdn];
            if (frm.doc.bank_account_currency) {
                frappe.model.set_value(cdt, cdn, 'transaction_currency', frm.doc.bank_account_currency);
            }
            frm.refresh_field('transaction_entry');
        },

        transaction_entry_add: function(frm, cdt, cdn) {
            let row = locals[cdt][cdn];
            frappe.model.set_value(cdt, cdn, 'posting_date', frm.doc.batch_date || frappe.datetime.get_today());
            if (frm.doc.bank_account_currency) {
                frappe.model.set_value(cdt, cdn, 'transaction_currency', frm.doc.bank_account_currency);
            }
            frm.refresh_field('transaction_entry');
            setTimeout(() => update_professional_stats(frm), 100);
            show_alert(frm, 'New transaction row added', 'info');
        },
        
        transaction_entry_remove: function(frm) {
            setTimeout(() => {
                calculate_totals(frm);
                update_professional_stats(frm);
                show_alert(frm, 'Transaction removed', 'warning');
            }, 100);
        }
    });
}

// ========================================
// HELPER FUNCTIONS
// ========================================

function flt(val) {
    return parseFloat(val) || 0;
}

function format_currency(amount, currency) {
    if (!amount) amount = 0;
    return frappe.format(amount, {fieldtype: "Currency", options: currency || "NGN"});
}

// ========================================
// UI UTILITIES
// ========================================

function show_loading(frm, message = 'Processing...') {
    hide_loading(frm);
    
    const loadingHtml = `
        <div class="loading-overlay">
            <div class="loading-spinner"></div>
            <div style="color: #64748b; font-size: 14px; margin-top: 10px;">${message}</div>
        </div>
    `;
    
    $('.professional-ui-container').append(loadingHtml);
}

function hide_loading(frm) {
    $('.loading-overlay').remove();
}

function show_alert(frm, message, type = 'info') {
    const alertHtml = `
        <div class="alert-card alert-${type}">
            <div style="display: flex; align-items: center; gap: 10px;">
                <i class="fa fa-${get_alert_icon(type)}" style="font-size: 18px;"></i>
                <div>${message}</div>
            </div>
        </div>
    `;
    
    $('#alerts-container').prepend(alertHtml);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        $('.alert-card').first().remove();
    }, 5000);
}

function get_alert_icon(type) {
    switch(type) {
        case 'success': return 'check-circle';
        case 'warning': return 'exclamation-triangle';
        case 'error': return 'times-circle';
        default: return 'info-circle';
    }
}

function update_professional_ui(frm) {
    // Update progress indicator
    const progressHtml = get_progress_indicator(frm);
    $('.ui-header-right').html(progressHtml);
    
    // Update status indicator
    const statusHtml = get_status_indicator(frm);
    $('.ui-header-left h3').html(`
        <i class="fa fa-bank"></i>
        Batch Bank Transaction
        ${statusHtml}
    `);
}

function check_for_alerts(frm) {
    if (!frm.doc.bank_account) {
        show_alert(frm, 'Please select a bank account to continue', 'warning');
    }
    
    if (!frm.doc.transaction_entry || frm.doc.transaction_entry.length === 0) {
        show_alert(frm, 'Add transactions to get started', 'info');
    }
}

// ========================================
// IMPORT/EXPORT FUNCTIONALITY
// ========================================

// Header-driven Excel/CSV import + same-layout export (shared helper:
// public/js/batch_excel.js).  Template, export and import all use one column
// layout, so an exported file can be edited and imported again.
const _BBT_XL = {
    module: 'ecclesia.ecclesia.doctype.batch_bank_transaction.batch_bank_transaction',
    child_table: 'transaction_entry',
    label: __('Transactions'),
};

function show_import_dialog(frm) {
    ecclesia.batch_excel.import_dialog(frm, _BBT_XL);
}

function export_to_excel(frm) {
    ecclesia.batch_excel.export_rows(frm, _BBT_XL);
}

// ========================================
// AI ANALYSIS
// ========================================

function get_ai_suggestions(frm) {
    if (!frm.doc.name) {
        show_alert(frm, 'Please save the document first', 'warning');
        return;
    }
    
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.batch_bank_transaction.batch_bank_transaction.get_ai_suggestions',
        args: { doc_name: frm.doc.name },
        callback: function(r) {
            hide_loading(frm);
            if (r.message) {
                show_ai_results(r.message, frm);
            }
        },
        error: function() {
            hide_loading(frm);
            show_alert(frm, 'Error getting AI suggestions', 'error');
        }
    });
}

function show_ai_results(suggestions, frm) {
    let content = '<div style="padding: 20px;">';
    
    if (suggestions.error) {
        content = `<div class="alert alert-danger">${suggestions.error}</div>`;
    } else {
        // Summary Card
        content += `
            <div style="background: #f8fafc; padding: 15px; border-radius: 10px; margin-bottom: 20px;">
                <h4 style="color: #475569; margin: 0 0 10px 0;">🤖 AI Analysis Summary</h4>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;">
                    <div style="text-align: center;">
                        <div style="font-size: 24px; font-weight: 700; color: ${suggestions.anomalies?.length ? '#ef4444' : '#10b981'}">${suggestions.anomalies?.length || 0}</div>
                        <div style="font-size: 12px; color: #64748b;">Anomalies</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 24px; font-weight: 700; color: #3b82f6">${suggestions.optimizations?.length || 0}</div>
                        <div style="font-size: 12px; color: #64748b;">Suggestions</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 24px; font-weight: 700; color: ${suggestions.duplicate_risks?.length ? '#f59e0b' : '#10b981'}">${suggestions.duplicate_risks?.length || 0}</div>
                        <div style="font-size: 12px; color: #64748b;">Duplicates</div>
                    </div>
                </div>
            </div>
        `;
        
        // Anomalies
        if (suggestions.anomalies?.length > 0) {
            content += '<h4 style="color: #475569; margin: 20px 0 10px 0;">🚨 Anomalies Detected</h4>';
            suggestions.anomalies.forEach(function(anomaly, idx) {
                const icon = anomaly.severity === 'error' ? '❌' : anomaly.severity === 'warning' ? '⚠️' : 'ℹ️';
                content += `
                    <div style="background: white; border-left: 4px solid ${get_severity_color(anomaly.severity)}; padding: 12px; margin-bottom: 8px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <div style="font-size: 16px;">${icon}</div>
                            <div>
                                <div style="font-weight: 600; color: #1e293b;">Row ${anomaly.row}: ${anomaly.type}</div>
                                <div style="color: #64748b; font-size: 13px; margin-top: 2px;">${anomaly.message}</div>
                            </div>
                        </div>
                    </div>
                `;
            });
        }
        
        // Optimizations
        if (suggestions.optimizations?.length > 0) {
            content += '<h4 style="color: #475569; margin: 20px 0 10px 0;">💡 Optimization Suggestions</h4>';
            suggestions.optimizations.forEach(function(opt, idx) {
                content += `
                    <div style="background: #f0f9ff; border-left: 4px solid #3b82f6; padding: 12px; margin-bottom: 8px; border-radius: 6px;">
                        <div style="display: flex; align-items: flex-start; gap: 10px;">
                            <div style="font-size: 16px;">💡</div>
                            <div style="flex: 1;">
                                <div style="font-weight: 600; color: #1e293b;">${opt.type}</div>
                                <div style="color: #475569; font-size: 13px; margin-top: 2px;">${opt.message}</div>
                                ${opt.action ? `<div style="margin-top: 8px;"><button class="btn btn-xs btn-primary" onclick="apply_optimization('${opt.action}')">Apply</button></div>` : ''}
                            </div>
                        </div>
                    </div>
                `;
            });
        }
        
        // Duplicates
        if (suggestions.duplicate_risks?.length > 0) {
            content += '<h4 style="color: #475569; margin: 20px 0 10px 0;">🔍 Potential Duplicates</h4>';
            suggestions.duplicate_risks.forEach(function(dup, idx) {
                content += `
                    <div style="background: #fffbeb; border-left: 4px solid #f59e0b; padding: 12px; margin-bottom: 8px; border-radius: 6px;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <div style="font-size: 16px;">🔍</div>
                            <div>
                                <div style="font-weight: 600; color: #1e293b;">Rows ${dup.row1} & ${dup.row2}</div>
                                <div style="color: #92400e; font-size: 13px; margin-top: 2px;">
                                    Date: ${dup.date} | Party: ${dup.party} | Amount: ${format_currency(dup.amount, frm.doc.bank_account_currency)}
                                </div>
                                <div style="color: #92400e; font-size: 12px; margin-top: 4px;">
                                    Confidence: ${(dup.confidence * 100).toFixed(0)}%
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            });
        }
        
        if (!suggestions.anomalies?.length && !suggestions.optimizations?.length && !suggestions.duplicate_risks?.length) {
            content += '<div style="text-align: center; padding: 30px;">';
            content += '<div style="font-size: 48px; color: #10b981;">✅</div>';
            content += '<div style="color: #475569; font-size: 16px; margin-top: 15px;">No issues detected! Everything looks perfect. 🎉</div>';
            content += '</div>';
        }
    }
    
    content += '</div>';
    
    frappe.msgprint({
        title: __('🤖 AI Analysis Report'),
        message: content,
        wide: true,
        indicator: suggestions.anomalies?.length > 0 ? 'orange' : 'green'
    });
}

function get_severity_color(severity) {
    switch(severity) {
        case 'error': return '#ef4444';
        case 'warning': return '#f59e0b';
        default: return '#3b82f6';
    }
}

function auto_categorize_transaction(frm, row, cdt, cdn) {
    if (!row.remark) return;
    
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.batch_bank_transaction.batch_bank_transaction.auto_categorize_transaction',
        args: { remark: row.remark },
        callback: function(r) {
            if (r.message && r.message.account) {
                frappe.model.set_value(cdt, cdn, 'party', r.message.account);
                show_alert(frm, `AI suggestion: ${r.message.account} (${(r.message.confidence * 100).toFixed(0)}% confidence)`, 'info');
            }
        }
    });
}

// ========================================
// RECONCILIATION
// ========================================

function reconcile_batch(frm) {
    if (!frm.doc.bank_account) {
        show_alert(frm, 'Please select a bank account first', 'warning');
        return;
    }
    
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.batch_bank_transaction.batch_bank_transaction.reconcile_batch',
        args: { doc_name: frm.doc.name },
        callback: function(r) {
            if (r.message) {
                if (r.message.status === 'matched') {
                    frappe.msgprint({
                        title: __('✅ Balance Reconciled'),
                        message: `
                            <div style="padding: 20px;">
                                <div style="text-align: center; margin-bottom: 20px;">
                                    <div style="font-size: 48px; color: #10b981;">✓</div>
                                    <div style="font-size: 16px; color: #475569; margin-top: 10px;">Bank reconciliation successful!</div>
                                </div>
                                <div style="background: #f0fdf4; padding: 15px; border-radius: 8px; border: 1px solid #a7f3d0;">
                                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                                        <div style="text-align: center;">
                                            <div style="font-size: 12px; color: #64748b;">Expected Balance</div>
                                            <div style="font-size: 18px; font-weight: 700; color: #065f46;">${format_currency(r.message.expected_balance, frm.doc.bank_account_currency)}</div>
                                        </div>
                                        <div style="text-align: center;">
                                            <div style="font-size: 12px; color: #64748b;">Actual Balance</div>
                                            <div style="font-size: 18px; font-weight: 700; color: #065f46;">${format_currency(r.message.actual_balance, frm.doc.bank_account_currency)}</div>
                                        </div>
                                    </div>
                                    <div style="text-align: center; margin-top: 15px; padding-top: 15px; border-top: 1px solid #a7f3d0;">
                                        <div style="font-size: 12px; color: #64748b;">Difference</div>
                                        <div style="font-size: 24px; font-weight: 700; color: #10b981;">${format_currency(r.message.difference, frm.doc.bank_account_currency)}</div>
                                    </div>
                                </div>
                            </div>
                        `,
                        indicator: 'green'
                    });
                } else {
                    frappe.msgprint({
                        title: __('⚠️ Reconciliation Required'),
                        message: `
                            <div style="padding: 20px;">
                                <div style="text-align: center; margin-bottom: 20px;">
                                    <div style="font-size: 48px; color: #ef4444;">⚠️</div>
                                    <div style="font-size: 16px; color: #475569; margin-top: 10px;">Balance mismatch detected</div>
                                </div>
                                <div style="background: #fef2f2; padding: 15px; border-radius: 8px; border: 1px solid #fecaca;">
                                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;">
                                        <div style="text-align: center;">
                                            <div style="font-size: 12px; color: #64748b;">Expected Balance</div>
                                            <div style="font-size: 18px; font-weight: 700; color: #dc2626;">${format_currency(r.message.expected_balance, frm.doc.bank_account_currency)}</div>
                                        </div>
                                        <div style="text-align: center;">
                                            <div style="font-size: 12px; color: #64748b;">Actual Balance</div>
                                            <div style="font-size: 18px; font-weight: 700; color: #dc2626;">${format_currency(r.message.actual_balance, frm.doc.bank_account_currency)}</div>
                                        </div>
                                    </div>
                                    <div style="text-align: center; padding-top: 15px; border-top: 1px solid #fecaca;">
                                        <div style="font-size: 14px; color: #dc2626; font-weight: 600;">Difference: ${format_currency(r.message.difference, frm.doc.bank_account_currency)}</div>
                                        <div style="font-size: 12px; color: #dc2626; margin-top: 5px;">
                                            Please review transactions for accuracy
                                        </div>
                                    </div>
                                </div>
                            </div>
                        `,
                        indicator: 'red'
                    });
                }
            }
        }
    });
}

function get_bank_balance(frm) {
    if (!frm.doc.bank_account) return;
    
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.batch_bank_transaction.batch_bank_transaction.get_bank_balance',
        args: {
            bank_account: frm.doc.bank_account,
            as_on_date: frm.doc.batch_date
        },
        callback: function(r) {
            if (r.message) {
                frm.set_value('opening_balance', r.message.balance);
                show_alert(frm, `Opening balance updated: ${format_currency(r.message.balance, frm.doc.bank_account_currency)}`, 'success');
                setTimeout(() => update_professional_stats(frm), 200);
            }
        }
    });
}

// ========================================
// BULK UPDATE
// ========================================

function show_bulk_update_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __('🔧 Bulk Update'),
        fields: [
            {
                fieldname: 'section_break',
                fieldtype: 'Section Break',
                label: __('Update Settings')
            },
            {
                fieldname: 'cost_center',
                fieldtype: 'Link',
                label: __('Cost Center'),
                options: 'Cost Center',
                reqd: 1
            },
            {
                fieldname: 'column_break',
                fieldtype: 'Column Break'
            },
            {
                fieldname: 'apply_to_empty_only',
                fieldtype: 'Check',
                label: __('Apply to empty fields only'),
                default: 1
            },
            {
                fieldname: 'section_break_2',
                fieldtype: 'Section Break',
                label: __('Affected Transactions')
            },
            {
                fieldname: 'transaction_count',
                fieldtype: 'HTML',
                options: `
                    <div style="text-align: center; padding: 10px; background: #f8fafc; border-radius: 6px;">
                        <div style="font-size: 24px; font-weight: 700; color: #3b82f6;" id="affected-count">${frm.doc.transaction_entry?.length || 0}</div>
                        <div style="font-size: 12px; color: #64748b;">Transactions will be updated</div>
                    </div>
                `
            }
        ],
        primary_action_label: __('✨ Apply Update'),
        primary_action(values) {
            if (!frm.doc.name) {
                show_alert(frm, 'Please save the document first', 'warning');
                d.hide();
                return;
            }
            
            show_loading(frm, 'Applying bulk update...');
            
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.batch_bank_transaction.batch_bank_transaction.bulk_update_cost_center',
                args: {
                    doc_name: frm.doc.name,
                    cost_center: values.cost_center
                },
                callback: function(r) {
                    hide_loading(frm);
                    if (r.message) {
                        d.hide();
                        frm.reload_doc();
                        show_alert(frm, r.message.message, 'success');
                    }
                },
                error: function() {
                    hide_loading(frm);
                    show_alert(frm, 'Error applying bulk update', 'error');
                }
            });
        }
    });
    
    d.show();
}

// ========================================
// BATCH REPORT
// ========================================

function generate_batch_report(frm) {
    if (!frm.doc.name) {
        show_alert(frm, 'Please save the document first', 'warning');
        return;
    }
    
    show_loading(frm, 'Generating batch report...');
    
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.batch_bank_transaction.batch_bank_transaction.generate_batch_report',
        args: { doc_name: frm.doc.name },
        callback: function(r) {
            hide_loading(frm);
            if (r.message) {
                show_batch_report(r.message, frm);
            }
        },
        error: function() {
            hide_loading(frm);
            show_alert(frm, 'Error generating report', 'error');
        }
    });
}

function show_batch_report(report, frm) {
    let content = `
        <div style="padding: 20px;">
            <h3 style="color: #475569; margin-bottom: 20px;">📊 Batch Report Summary</h3>
            
            <!-- Summary Cards -->
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-bottom: 20px;">
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                    <div style="font-size: 12px; color: #64748b; margin-bottom: 5px;">Total Transactions</div>
                    <div style="font-size: 24px; font-weight: 700; color: #475569;">${report.summary?.total_transactions || 0}</div>
                </div>
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                    <div style="font-size: 12px; color: #64748b; margin-bottom: 5px;">Transaction Types</div>
                    <div style="font-size: 24px; font-weight: 700; color: #475569;">${Object.keys(report.type_breakdown || {}).length}</div>
                </div>
            </div>
            
            <!-- Financial Summary -->
            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                <h4 style="color: #475569; margin: 0 0 15px 0; font-size: 14px;">Financial Summary</h4>
                <table style="width: 100%;">
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">Opening Balance</td>
                        <td style="padding: 8px 0; text-align: right; font-weight: 600;">${format_currency(report.summary?.opening_balance || 0, frm.doc.bank_account_currency)}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #10b981;">➕ Total Inflow</td>
                        <td style="padding: 8px 0; text-align: right; font-weight: 600; color: #10b981;">${format_currency(report.summary?.total_inflow || 0, frm.doc.bank_account_currency)}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #ef4444;">➖ Total Outflow</td>
                        <td style="padding: 8px 0; text-align: right; font-weight: 600; color: #ef4444;">${format_currency(report.summary?.total_outflow || 0, frm.doc.bank_account_currency)}</td>
                    </tr>
                    <tr style="border-top: 2px solid #e2e8f0;">
                        <td style="padding: 12px 0; color: #475569; font-weight: 600;">Closing Balance</td>
                        <td style="padding: 12px 0; text-align: right; font-weight: 700; color: #3b82f6;">${format_currency(report.summary?.net_balance || 0, frm.doc.bank_account_currency)}</td>
                    </tr>
                </table>
            </div>
            
            <!-- Transaction Type Breakdown -->
            ${report.type_breakdown ? `
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                    <h4 style="color: #475569; margin: 0 0 15px 0; font-size: 14px;">Transaction Type Breakdown</h4>
                    ${Object.entries(report.type_breakdown).map(([type, count]) => `
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #f1f5f9;">
                            <span style="color: #475569;">${type}</span>
                            <span style="background: #f1f5f9; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; color: #3b82f6;">${count}</span>
                        </div>
                    `).join('')}
                </div>
            ` : ''}
            
            <!-- Top Parties -->
            ${report.party_breakdown ? `
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                    <h4 style="color: #475569; margin: 0 0 15px 0; font-size: 14px;">Top Parties</h4>
                    ${Object.entries(report.party_breakdown).slice(0, 5).map(([party, data]) => `
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #f1f5f9;">
                            <div>
                                <div style="color: #475569; font-weight: 500;">${party}</div>
                                <div style="color: #64748b; font-size: 11px;">${data.count} transactions</div>
                            </div>
                            <span style="font-weight: 600; color: #475569;">${format_currency(data.total_amount, frm.doc.bank_account_currency)}</span>
                        </div>
                    `).join('')}
                </div>
            ` : ''}
        </div>
    `;
    
    frappe.msgprint({
        title: __('📈 Detailed Batch Report'),
        message: content,
        wide: true,
        indicator: 'green'
    });
}

// ========================================
// VALIDATION FUNCTIONS
// ========================================

function validate_batch(frm) {
    if (!frm.doc.bank_account) {
        show_alert(frm, 'Please select a Bank Account', 'error');
        return false;
    }
    
    if (!frm.doc.batch_date) {
        show_alert(frm, 'Please select a Batch Date', 'error');
        return false;
    }
    
    if (!frm.doc.transaction_entry || frm.doc.transaction_entry.length === 0) {
        show_alert(frm, 'Please add at least one transaction', 'error');
        return false;
    }
    
    return true;
}

function validate_before_submit(frm) {
    let incomplete = [];
    
    for (let i = 0; i < frm.doc.transaction_entry.length; i++) {
        let row = frm.doc.transaction_entry[i];
        
        if (!row.remark || row.remark.length < 5) {
            incomplete.push(__('Row {0}: Insufficient remark', [i + 1]));
        }
        
        if (!row.cost_center) {
            incomplete.push(__('Row {0}: Cost Center is mandatory', [i + 1]));
        }
    }
    
    if (incomplete.length > 0) {
        frappe.msgprint({
            title: __('⚠️ Validation Errors'),
            message: `
                <div style="padding: 15px;">
                    <div style="color: #dc2626; font-weight: 600; margin-bottom: 10px;">Please fix the following issues:</div>
                    <div style="background: #fef2f2; padding: 10px; border-radius: 6px;">
                        ${incomplete.join('<br>')}
                    </div>
                </div>
            `,
            indicator: 'red'
        });
        return false;
    }
    
    return true;
}

function validate_duplicate_references(frm) {
    let refs = {};
    let duplicates = [];
    
    frm.doc.transaction_entry?.forEach((row, idx) => {
        if (row.reference_no) {
            if (refs[row.reference_no]) {
                duplicates.push({
                    row: idx + 1,
                    ref: row.reference_no
                });
            } else {
                refs[row.reference_no] = true;
            }
        }
    });
    
    if (duplicates.length > 0) {
        show_alert(frm, `Found ${duplicates.length} duplicate reference numbers`, 'warning');
    }
}

function validate_balance_integrity(frm) {
    let calculated_balance = flt(frm.doc.opening_balance || 0);
    
    frm.doc.transaction_entry?.forEach(row => {
        calculated_balance += flt(row.inflow || 0) - flt(row.outflow || 0);
    });
    
    let diff = Math.abs(calculated_balance - flt(frm.doc.balance || 0));
    if (diff > 0.01) {
        show_alert(frm, `Balance mismatch detected: ${format_currency(diff, frm.doc.bank_account_currency)}`, 'warning');
    }
}

// ========================================
// TRANSACTION MANAGEMENT FUNCTIONS
// ========================================

function add_smart_default_row(frm) {
    frm.add_child('transaction_entry', {
        posting_date: frm.doc.batch_date || frappe.datetime.get_today(),
        transaction_currency: frm.doc.bank_account_currency || 'NGN',
        amount: 0,
        inflow: 0,
        outflow: 0
    });
    frm.refresh_field('transaction_entry');
}

function setup_keyboard_shortcuts(frm) {
    $(document).on('keydown', function(e) {
        if (e.ctrlKey && cur_frm) {
            switch(e.key) {
                case 's':
                    e.preventDefault();
                    if (cur_frm.doc.docstatus === 0) {
                        cur_frm.save();
                        show_alert(cur_frm, 'Saved!', 'success');
                    }
                    break;
                case 'n':
                    e.preventDefault();
                    cur_frm.add_child('transaction_entry', {});
                    cur_frm.refresh_field('transaction_entry');
                    show_alert(cur_frm, 'New transaction added', 'info');
                    break;
                case 'd':
                    e.preventDefault();
                    if (cur_frm.get_selected()) {
                        cur_frm.remove_child('transaction_entry', cur_frm.get_selected().name);
                        cur_frm.refresh_field('transaction_entry');
                        show_alert(cur_frm, 'Transaction removed', 'warning');
                    }
                    break;
                case 'i':
                    e.preventDefault();
                    show_import_dialog(cur_frm);
                    break;
                case 'e':
                    e.preventDefault();
                    export_to_excel(cur_frm);
                    break;
            }
        }
    });
}

function enable_auto_save(frm) {
    let timeout;
    frm.cscript.save_draft = function() {
        clearTimeout(timeout);
        timeout = setTimeout(function() {
            if (frm.doc.docstatus === 0 && !frm.is_dirty()) {
                frm.save();
            }
        }, 5000);
    };
}

function setup_grid_queries(frm) {
    if (frm.fields_dict.transaction_entry && frm.fields_dict.transaction_entry.grid) {
        frm.fields_dict.transaction_entry.grid.get_field('party').get_query = function(doc, cdt, cdn) {
            return {};
        };
    }
}

function handle_trans_type_change(frm, row, cdt, cdn) {
    const trans_type = row.trans_type;
    if (!trans_type) return;
    
    const configs = {
        'Customer Receipt': {
            party_type: 'Customer',
            remark_template: `Money received from client: ${row.party || '{PARTY}'}`,
            flow: 'inflow'
        },
        'Supplier Payment': {
            party_type: 'Supplier',
            remark_template: `Payment to Supplier: ${row.party || '{PARTY}'}`,
            flow: 'outflow'
        },
        'Payment': {
            party_type: 'Account',
            remark_template: `Payment to ${row.payee_name || '{PAYEE}'}`,
            flow: 'outflow'
        },
        'Receipt': {
            party_type: 'Account',
            remark_template: `Receipt from ${row.payee_name || '{PAYEE}'}`,
            flow: 'inflow'
        },
        'Transfer In': {
            party_type: 'Account',
            remark_template: `Transfer from other account into ${frm.doc.bank_gl}`,
            flow: 'inflow'
        },
        'Transfer Out': {
            party_type: 'Account',
            remark_template: `Transfer to other account from ${frm.doc.bank_gl}`,
            flow: 'outflow'
        },
        'Customer Refunds': {
            party_type: 'Customer',
            remark_template: `Refund of money earlier received from ${row.party || '{PARTY}'}`,
            flow: 'outflow'
        },
        'Supplier Refunds': {
            party_type: 'Supplier',
            remark_template: `Receipt of money earlier paid to ${row.party || '{PARTY}'}`,
            flow: 'inflow'
        }
    };

    const config = configs[trans_type];
    if (config) {
        if (!row.party_type) {
            frappe.model.set_value(cdt, cdn, 'party_type', config.party_type);
        }
        
        if (!row.remark) {
            frappe.model.set_value(cdt, cdn, 'remark', config.remark_template);
        }
        
        if (config.flow === 'inflow') {
            frappe.model.set_value(cdt, cdn, 'outflow', 0);
        } else {
            frappe.model.set_value(cdt, cdn, 'inflow', 0);
        }
    }
}

function calculate_row_amounts(frm, row, cdt, cdn) {
    const amount = row.amount || 0;
    const trans_type = row.trans_type;
    const currency = row.transaction_currency;
    const exch_rate = row.exch_rate || 1;

    const inflow_types = ['Customer Receipt', 'Receipt', 'Transfer In', 'Supplier Refunds'];
    const outflow_types = ['Supplier Payment', 'Payment', 'Transfer Out', 'Customer Refunds'];

    if (inflow_types.includes(trans_type)) {
        frappe.model.set_value(cdt, cdn, 'inflow', amount);
        frappe.model.set_value(cdt, cdn, 'outflow', 0);
    } else if (outflow_types.includes(trans_type)) {
        frappe.model.set_value(cdt, cdn, 'outflow', amount);
        frappe.model.set_value(cdt, cdn, 'inflow', 0);
    }

    if (currency && currency !== 'NGN') {
        frappe.model.set_value(cdt, cdn, 'amount_in_fc', amount);
        frappe.model.set_value(cdt, cdn, 'amount_in_lc', amount * exch_rate);
    } else {
        frappe.model.set_value(cdt, cdn, 'amount_in_lc', amount);
    }
    
    calculate_totals(frm);
}

function calculate_totals(frm) {
    let total_inflow = 0;
    let total_outflow = 0;
    let balance = flt(frm.doc.opening_balance || 0);
    
    $.each(frm.doc.transaction_entry || [], function(index, row) {
        total_inflow += flt(row.inflow || 0);
        total_outflow += flt(row.outflow || 0);
        balance += flt(row.inflow || 0) - flt(row.outflow || 0);
        frappe.model.set_value(row.doctype, row.name, 'balance', balance);
    });

    frm.set_value('total_inflow', total_inflow);
    frm.set_value('total_outflow', total_outflow);
    frm.set_value('balance', balance);
}

function update_naming_series(frm) {
    const bank_gl = frm.doc.bank_gl;
    const naming_map = {
        '2602 - Fidelity Bank - Base - BC': 'FID-BAS-BJV-.#####',
        '2603 - Fidelity Bank - LAG - BC': 'FID-LAG-BJV-.#####',
        '2605 - Fidelity Bank - PHC - BC': 'FID-PHC-BJV-.#####',
        '2604 - Fidelity Bank - VI - BC': 'FID-VIS-BJV-.#####',
        '2602 - Office main cash - SN': 'MCH-CJV-.#####',
        '2624 - Access Bank USD - SN': 'ACC-USD-BJV-.#####',
        '2620 - Access Bank - SN': 'ACC-BJV-.#####'
    };

    if (naming_map[bank_gl]) {
        frm.set_value('naming_series', naming_map[bank_gl]);
    }
}

function fetch_party_details(frm, row, cdt, cdn) {
    if (row.party && row.party_type) {
        if (frm.doc.bank_account_currency) {
            frappe.model.set_value(cdt, cdn, 'transaction_currency', frm.doc.bank_account_currency);
        }
        
        update_single_party_name(frm, row, cdt, cdn);
    }
}

function update_party_names(frm) {
    if (!frm.doc.transaction_entry) return;
    
    frm.doc.transaction_entry.forEach(function(row, idx) {
        if (row.party && !row.party_name) {
            update_single_party_name(frm, row, row.doctype, row.name);
        }
    });
}

function update_single_party_name(frm, row, cdt, cdn) {
    if (row.party_type === 'Supplier') {
        frappe.call({
            method: 'frappe.client.get_value',
            args: {
                doctype: 'Supplier',
                filters: { name: row.party },
                fieldname: ['supplier_name']
            },
            callback: function(r) {
                if (r.message && r.message.supplier_name) {
                    frappe.model.set_value(cdt, cdn, 'party_name', r.message.supplier_name);
                    frappe.model.set_value(cdt, cdn, 'payee_name', r.message.supplier_name);
                }
            }
        });
    } else if (row.party_type === 'Customer') {
        frappe.call({
            method: 'frappe.client.get_value',
            args: {
                doctype: 'Customer',
                filters: { name: row.party },
                fieldname: ['customer_name']
            },
            callback: function(r) {
                if (r.message && r.message.customer_name) {
                    frappe.model.set_value(cdt, cdn, 'party_name', r.message.customer_name);
                    frappe.model.set_value(cdt, cdn, 'payee_name', r.message.customer_name);
                }
            }
        });
    }
}

function handle_currency_change(frm, row, cdt, cdn) {
    if (row.transaction_currency && row.transaction_currency !== 'NGN') {
        frappe.call({
            method: 'erpnext.setup.utils.get_exchange_rate',
            args: {
                from_currency: row.transaction_currency,
                to_currency: 'NGN',
                transaction_date: row.posting_date || frm.doc.batch_date
            },
            callback: function(r) {
                if (r.message) {
                    frappe.model.set_value(cdt, cdn, 'exch_rate', r.message);
                }
            }
        });
    }
}

function recalculate_amounts(frm, row, cdt, cdn) {
    const amount = row.amount || 0;
    const exch_rate = row.exch_rate || 1;
    
    if (row.transaction_currency !== 'NGN') {
        frappe.model.set_value(cdt, cdn, 'amount_in_fc', amount);
        frappe.model.set_value(cdt, cdn, 'amount_in_lc', amount * exch_rate);
    } else {
        frappe.model.set_value(cdt, cdn, 'amount_in_lc', amount);
    }
}

function generate_reference_numbers(frm) {
    if (frm.doc.transaction_entry) {
        frm.doc.transaction_entry.forEach((row, index) => {
            if (!row.reference_no) {
                const prefix = frm.doc.naming_series ? frm.doc.naming_series.split('.')[0] : 'BATCH';
                frappe.model.set_value(row.doctype, row.name, 'reference_no', `${prefix}-${index + 1}`);
            }
        });
    }
}

function handle_recurring_transaction(frm, row, cdt, cdn) {
    // Placeholder for recurring transaction handling
    if (row.frequency) {
        show_alert(frm, 'Recurring transaction setup initiated', 'info');
    }
}

// ========================================
// INITIALIZATION COMPLETE
// ========================================

console.log('🎉 Batch Bank Transaction Professional UI Ready!');

// Global helper for optimization application
window.apply_optimization = function(action) {
    console.log('Applying optimization:', action);
    show_alert(cur_frm, `Applying ${action} optimization...`, 'info');
    // Implementation would go here based on the specific action
};


//++++++++++++++++++++++++++++++++++++++++


frappe.ui.form.on("Batch Bank Transaction", {
    refresh(frm) {
        // ── Excel: template / export / import ────────────────────────────────
        ecclesia.batch_excel.add_buttons(frm, _BBT_XL);

        // ── Bank Payment buttons — shown on submitted docs only ──────────────
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('📥 Download Payment File'), () => {
                _bbt_dialog(frm, 'download');
            }, __('🏦 Bank Payment'));

            frm.add_custom_button(__('🚀 Send to Bank'), () => {
                _bbt_dialog(frm, 'send');
            }, __('🏦 Bank Payment'));

            frm.add_custom_button(__('📎 Attach to Document'), () => {
                _bbt_attach_dialog(frm);
            }, __('🏦 Bank Payment'));

            frm.add_custom_button(__('📧 Email Payment File'), () => {
                _bbt_email_dialog(frm);
            }, __('🏦 Bank Payment'));

            frm.add_custom_button(__('📡 Check Send Status'), () => {
                _bbt_status_dialog(frm);
            }, __('🏦 Bank Payment'));
        }

        // ── Existing: Set Party & Cost Center ────────────────────────────────
        frm.add_custom_button(__('Set Party & Cost Center'), function () {

            if (!frm.doc.company) {
                frappe.msgprint(__('Please select a Company first'));
                return;
            }

            if (!frm.doc.transaction_entry || frm.doc.transaction_entry.length === 0) {
                frappe.msgprint(__('No Transaction Entries found'));
                return;
            }

            frappe.confirm(
                __('This will update Party Type, Inflow/Outflow and Cost Center. Continue?'),
                function () {

                    frappe.db.get_value(
                        "Company",
                        frm.doc.company,
                        "cost_center",
                        function (r) {

                            let company_cost_center = (r && r.cost_center) ? r.cost_center : "";

                            frm.doc.transaction_entry.forEach(function (d) {
                                if (d.party_type) {
                                    return;
                                }
                                apply_transaction_rules(d, company_cost_center);
                            });

                            frm.refresh_field("transaction_entry");
                            frappe.msgprint(__('Transaction Entries updated successfully'));
                        }
                    );
                }
            );
        });
    }
});


frappe.ui.form.on("Transaction Entry", {
    trans_type(frm, cdt, cdn) {
        let d = locals[cdt][cdn];

        if (d.party_type || !frm.doc.company) {
            return;
        }

        frappe.db.get_value(
            "Company",
            frm.doc.company,
            "cost_center",
            function (r) {
                let company_cost_center = (r && r.cost_center) ? r.cost_center : "";
                apply_transaction_rules(d, company_cost_center);
            }
        );
    }
});


/* =========================
   CORE RULE ENGINE
========================= */

function apply_transaction_rules(d, company_cost_center) {
    let trans_type = d.trans_type || "";
    let amount = d.amount || 0;

    // Supplier
    if (["Supplier Payment", "Supplier Refunds"].includes(trans_type)) {

        set_party(d, "Supplier");
        set_outflow(d, amount);
        clear_cost_center(d);

    // Customer
    } else if (["Customer Receipt", "Customer Refunds"].includes(trans_type)) {

        set_party(d, "Customer");
        set_inflow(d, amount);
        clear_cost_center(d);

    // Account – Inflow
    } else if (["Receipt", "Transfer In"].includes(trans_type)) {

        set_party(d, "Account");
        set_inflow(d, amount);
        set_cost_center(d, company_cost_center);

    // Account – Outflow
    } else if (["Payment", "Transfer Out"].includes(trans_type)) {

        set_party(d, "Account");
        set_outflow(d, amount);
        set_account_or_company_cost_center(d, company_cost_center);
    }
}


/* =========================
   HELPER FUNCTIONS
========================= */

function set_party(d, party_type) {
    frappe.model.set_value(d.doctype, d.name, "party_type", party_type);
}

function set_inflow(d, amount) {
    frappe.model.set_value(d.doctype, d.name, "inflow", amount);
    frappe.model.set_value(d.doctype, d.name, "outflow", 0);
}

function set_outflow(d, amount) {
    frappe.model.set_value(d.doctype, d.name, "outflow", amount);
    frappe.model.set_value(d.doctype, d.name, "inflow", 0);
}

function clear_cost_center(d) {
    frappe.model.set_value(d.doctype, d.name, "cost_center", "");
}

function set_cost_center(d, cost_center) {
    frappe.model.set_value(d.doctype, d.name, "cost_center", cost_center || "");
}

function set_account_or_company_cost_center(d, company_cost_center) {
    if (d.account) {
        frappe.db.get_value(
            "Account",
            d.account,
            "cost_center",
            function (r) {
                set_cost_center(
                    d,
                    (r && r.cost_center) ? r.cost_center : company_cost_center
                );
            }
        );
    } else {
        set_cost_center(d, company_cost_center);
    }
}


// ══════════════════════════════════════════════════════════════════════════════
//  🏦 BANK PAYMENT — Batch Bank Transaction helpers
//  Fields used from Payment Gateway Settings:
//    sftp_host, sftp_port, sftp_username, sftp_password, sftp_path  → SFTP channel
//    secret_key (Password)                                           → Paystack / Flutterwave / Squad
//    bank_export_format, bank_bic_code                               → file format
// ══════════════════════════════════════════════════════════════════════════════

const _BBT = {
    export:   'ecclesia.api.bank_payment_export.generate_batch_payment_file',
    send:     'ecclesia.api.bank_send_api.send_batch_payment',
    channels: 'ecclesia.api.bank_send_api.get_send_channels',
    status:   'ecclesia.api.bank_send_api.check_payment_status',
    formats:  'ecclesia.api.bank_payment_export.get_supported_formats',
    attach:   'ecclesia.api.bank_payment_export.attach_payment_file_to_doc',
    email:    'ecclesia.api.bank_payment_export.email_payment_file',
    files:    'ecclesia.api.bank_payment_export.get_attached_payment_files',
};

function _bbt_dialog(frm, mode) {
    const isSend   = mode === 'send';
    const rowCount = (frm.doc.transaction_entry || []).length;
    const total    = (frm.doc.total_outflow || 0) + (frm.doc.total_inflow || 0);

    Promise.all([
        frappe.db.get_list('Payment Gateway Settings', {
            filters: { enabled: 1, company: frm.doc.company },
            fields: ['name', 'provider', 'bank_export_format'],
            limit: 20,
        }),
        frappe.call({ method: _BBT.formats }),
    ]).then(([gateways, fmtRes]) => {
        const formats    = fmtRes.message || [];
        const fmtOpts    = formats.map(f => f.key).join('\n');
        const defaultFmt = (gateways[0] || {}).bank_export_format || 'zenith_iso20022';

        const summaryHtml = `
            <div style="background:#EFF6FF;border-left:4px solid #3B82F6;
                        padding:11px 15px;border-radius:7px;margin-bottom:6px;font-size:12px">
                <div style="font-weight:700;color:#1E40AF;margin-bottom:4px">
                    📋 ${frm.doc.name} &nbsp;·&nbsp; ${frm.doc.company || ''}
                </div>
                <div style="display:flex;gap:20px;color:#1D4ED8">
                    <span>💳 <b>${rowCount}</b> transactions</span>
                    <span>📅 ${frm.doc.batch_date || ''}</span>
                    <span>💰 <b>₦${total.toLocaleString()}</b></span>
                </div>
            </div>`;

        const fields = [
            { fieldtype: 'HTML', options: summaryHtml },
            {
                fieldname: 'bank_format', fieldtype: 'Select',
                label: 'Bank Format', options: fmtOpts,
                reqd: 1, default: defaultFmt,
                description: 'Zenith: ISO 20022 · GTB/Access/UBA/FBN: CSV · EU: SEPA XML · US: NACHA · International: SWIFT MT103',
            },
            {
                fieldtype: 'HTML',
                options: `<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:8px 12px;font-size:11px;margin-top:-4px">
                    <b style="color:#475569">Format keys:</b>
                    <div style="display:grid;grid-template-columns:140px 1fr;gap:1px 8px;margin-top:4px;color:#64748B;line-height:1.7">
                      <span style="font-family:monospace;color:#1E40AF">zenith_iso20022</span><span>Zenith Bank Nigeria — ISO 20022 pain.001 CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">gtb_csv</span><span>GTBank Nigeria — CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">access_csv</span><span>Access Bank Nigeria — CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">uba_csv</span><span>UBA Nigeria — CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">firstbank_csv</span><span>First Bank Nigeria — CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">sepa_xml</span><span>SEPA Credit Transfer XML — EU banks</span>
                      <span style="font-family:monospace;color:#1E40AF">bacs_csv</span><span>BACS Direct Credit — UK</span>
                      <span style="font-family:monospace;color:#1E40AF">ach_nacha</span><span>ACH / NACHA — USA</span>
                      <span style="font-family:monospace;color:#1E40AF">swift_mt103</span><span>SWIFT MT103 — International wires</span>
                    </div>
                    <div style="margin-top:8px;padding:6px 10px;background:#FEF3C7;border-radius:5px;font-size:10px;color:#92400E;border:1px solid #F59E0B">
                        <b>Highlighted columns in template:</b><br>
                        <b>CRED_ADDRESS_COUNTRYSUBDIVISION</b> ← Fill <code>Payee Address</code> on each row in the child table<br>
                        <b>CREDACC_BIC</b> ← Auto-resolved from <code>Payee Bank</code> name → BIC dictionary → Bank master
                    </div>
                </div>`,
            },
        ];

        if (isSend) {
            fields.push(
                {
                    fieldname: 'gateway_name', fieldtype: 'Link',
                    label: 'Payment Gateway', options: 'Payment Gateway Settings',
                    reqd: 1, default: (gateways[0] || {}).name || '',
                    description: 'SFTP: requires sftp_host + sftp_username + sftp_password | REST APIs: requires secret_key',
                },
                {
                    fieldname: 'send_channel', fieldtype: 'Select',
                    label: 'Send Channel',
                    options: [
                        'sftp_upload:📡 SFTP Upload — direct to bank file server',
                        'paystack_bulk:💳 Paystack Bulk Transfer API',
                        'flutterwave_bulk:🦋 Flutterwave Bulk Transfer API',
                        'squad_bulk:🏦 Squad (GTBank) Bulk Transfer API',
                        'manual_download:📥 Manual Download — upload to portal yourself',
                    ].join('\n'),
                    reqd: 1, default: 'sftp_upload',
                },
                {
                    fieldtype: 'HTML',
                    options: `<div style="background:#FFFBEB;border-left:4px solid #F59E0B;
                              padding:9px 14px;border-radius:6px;font-size:11px;color:#92400E;margin-top:4px">
                        ⚠️ <b>This initiates actual bank transfers.</b><br>
                        SFTP — set <b>SFTP Host</b>, <b>SFTP Username</b>, <b>SFTP Password</b> and <b>SFTP Remote Path</b>
                        in the Payment Gateway Settings record.<br>
                        REST APIs (Paystack / Flutterwave / Squad) — set <b>Secret Key</b> in API Credentials section.
                    </div>`,
                }
            );
        }

        const d = new frappe.ui.Dialog({
            title:   isSend ? '🚀 Send Payment Batch to Bank' : '📥 Download Bank Payment File',
            size:    'large',
            fields,
            primary_action_label: isSend ? '🚀 Send Now' : '📥 Download',
            primary_action(vals) {
                d.hide();
                isSend ? _bbt_do_send(frm, vals) : _bbt_do_download(frm, vals.bank_format);
            },
        });

        // Reload channels when gateway selection changes
        if (isSend && d.fields_dict.gateway_name) {
            d.fields_dict.gateway_name.df.change = function() {
                const gw = d.get_value('gateway_name');
                if (!gw) return;
                frappe.call({
                    method: _BBT.channels,
                    args: { gateway_name: gw },
                    callback: r => {
                        const opts = (r.message || []).map(c => `${c.key}:${c.label}`).join('\n');
                        d.fields_dict.send_channel.df.options = opts;
                        d.fields_dict.send_channel.refresh();
                    }
                });
            };
        }

        d.show();
    });
}

function _bbt_do_download(frm, bank_format) {
    frappe.call({
        method: _BBT.export,
        args:   { payment_batch: frm.doc.name, bank_format },
        freeze: true, freeze_message: `Generating ${bank_format} file…`,
        callback(r) {
            const res = r.message || {};
            if (res.success) {
                _bbt_save_file(res);
                frappe.show_alert({
                    message: `✅ ${res.file_name} · ${res.row_count} rows · ₦${(res.total_amount || 0).toLocaleString()}`,
                    indicator: 'green',
                }, 7);
            } else {
                frappe.msgprint({ title: '❌ Export Failed', message: res.error || 'Unknown error', indicator: 'red' });
            }
        },
    });
}

function _bbt_do_send(frm, vals) {
    const freeze_msgs = {
        sftp_upload:      '📡 Uploading to bank SFTP server…',
        paystack_bulk:    '💳 Initiating Paystack bulk transfer…',
        flutterwave_bulk: '🦋 Initiating Flutterwave bulk transfer…',
        squad_bulk:       '🏦 Initiating Squad bulk transfer…',
        manual_download:  '📥 Preparing file for download…',
    };
    frappe.call({
        method: _BBT.send,
        args: {
            payment_batch: frm.doc.name,
            send_channel:  vals.send_channel,
            gateway_name:  vals.gateway_name,
        },
        freeze: true,
        freeze_message: freeze_msgs[vals.send_channel] || 'Sending…',
        callback(r) {
            const res = r.message || {};
            if (res.success) {
                if (res.channel === 'manual_download' && res.file_data) _bbt_save_file(res);
                _bbt_show_success(frm, res, vals);
            } else {
                _bbt_show_error(res);
            }
        },
    });
}

function _bbt_status_dialog(frm) {
    frappe.db.get_list('Payment Gateway Settings', {
        filters: { enabled: 1, company: frm.doc.company },
        fields: ['name', 'provider'],
        limit: 20,
    }).then(gateways => {
        new frappe.ui.Dialog({
            title: '📡 Check Payment Send Status',
            fields: [
                {
                    fieldname: 'gateway_name', fieldtype: 'Select', label: 'Payment Gateway',
                    options: gateways.map(g => g.name).join('\n'), reqd: 1,
                    default: (gateways[0] || {}).name || '',
                },
                {
                    fieldname: 'batch_reference', fieldtype: 'Data',
                    label: 'Batch / Transfer Reference', reqd: 1,
                    description: 'Reference returned when the payment was sent',
                },
            ],
            primary_action_label: '📡 Check',
            primary_action(vals) {
                this.hide();
                frappe.call({
                    method: _BBT.status,
                    args: { gateway_name: vals.gateway_name, batch_reference: vals.batch_reference },
                    freeze: true, freeze_message: 'Querying status…',
                    callback(r) {
                        const res = r.message || {};
                        const col = { success:'green', failed:'red', pending:'blue' }[res.status] || 'blue';
                        frappe.msgprint({
                            title: `📡 Status: ${(res.status || 'unknown').toUpperCase()}`,
                            message: `
                                <div style="font-size:12px;margin-bottom:8px;line-height:1.8">
                                    <b>Provider:</b> ${res.provider || vals.gateway_name}<br>
                                    <b>Reference:</b> ${res.reference || vals.batch_reference}<br>
                                    <b>Status:</b> ${res.status || 'unknown'}
                                </div>
                                <pre style="font-size:10px;background:#F8FAFC;padding:8px;border-radius:6px;
                                     max-height:220px;overflow:auto">${JSON.stringify(res.details || {}, null, 2)}</pre>`,
                            indicator: col,
                        });
                    },
                });
            },
        }).show();
    });
}

function _bbt_show_success(frm, res, vals) {
    const ref = res.reference || res.batch_code || '';
    frappe.msgprint({
        title: '✅ Payment Sent',
        message: `
            <div style="font-size:13px;line-height:2">
                <b>${res.message || 'Transfer initiated'}</b><br>
                Transactions: <b>${res.row_count || 0}</b><br>
                Total: <b>₦${(res.total_amount || 0).toLocaleString()}</b>
                ${ref ? `<div style="margin-top:6px;padding:5px 10px;background:#F1F5F9;
                          border-radius:5px;font-family:monospace;font-size:11px">
                          Reference: <b>${ref}</b></div>` : ''}
                ${res.remote_path ? `<div style="font-size:11px;color:#64748B;margin-top:4px">
                    SFTP path: <code>${res.remote_path}</code></div>` : ''}
            </div>`,
        indicator: 'green',
    });
    // Store reference for audit trail
    if (ref) {
        frappe.call({
            method: 'frappe.client.set_value',
            args: {
                doctype: 'Batch Bank Transaction', name: frm.doc.name,
                fieldname: 'remark',
                value: `Bank send: ${ref} via ${vals.send_channel} · ${frappe.datetime.now_datetime()}`,
            },
            callback: () => frm.reload_doc(),
        });
    }
}

function _bbt_show_error(res) {
    frappe.msgprint({
        title: '❌ Send Failed',
        message: `<b style="color:#DC2626">${res.error || 'Unknown error'}</b>
            <div style="margin-top:10px;font-size:11px;color:#64748B;line-height:1.8">
                <b>Troubleshooting:</b><br>
                📡 <b>SFTP:</b> Check SFTP Host, SFTP Username, SFTP Password and SFTP Remote Path
                in the Payment Gateway Settings record.<br>
                💳 <b>Paystack / Flutterwave / Squad:</b> Check Secret Key in API Credentials section.
                Ensure account is live (disable Sandbox / Test Mode) and has transfer permissions.<br>
                ✅ <b>All channels:</b> Batch Bank Transaction must be submitted (docstatus = 1).
            </div>`,
        indicator: 'red',
    });
}

function _bbt_save_file(res) {
    const fname = res.file_name || 'BankPayment.csv';
    const ext   = fname.split('.').pop().toLowerCase();
    const mime  = ext === 'xml' ? 'application/xml' : ext === 'txt' ? 'text/plain' : 'text/csv';
    const a = document.createElement('a');
    a.href = `data:${mime};base64,${res.file_data}`;
    a.download = fname;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}


// ── Attach to Document ────────────────────────────────────────────────────────

function _bbt_attach_dialog(frm) {
    frappe.call({ method: _BBT.formats, callback: r => {
        const formats = (r.message || []);
        const fmtOpts = formats.map(f => f.key).join('\n');
        const rowCount = (frm.doc.transaction_entry || []).length;
        const total    = (frm.doc.total_outflow || 0) + (frm.doc.total_inflow || 0);

        new frappe.ui.Dialog({
            title: '📎 Attach Bank Payment File to Document',
            fields: [
                { fieldtype: 'HTML', options: `
                    <div style="background:#EFF6FF;border-left:4px solid #3B82F6;padding:10px 14px;border-radius:7px;margin-bottom:6px;font-size:12px;color:#1E40AF">
                        <b>${frm.doc.name}</b> · ${rowCount} transactions · ₦${total.toLocaleString()}<br>
                        The file will be saved as an attachment on this Batch Bank Transaction
                        and will appear in the Attachments panel.
                    </div>` },
                { fieldname: 'bank_format', fieldtype: 'Select', label: 'Bank Format',
                  options: fmtOpts, reqd: 1, default: 'zenith_iso20022' },
            {
                fieldtype: 'HTML',
                options: `<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:8px 12px;font-size:11px;margin-top:-4px">
                    <b style="color:#475569">Format keys:</b>
                    <div style="display:grid;grid-template-columns:140px 1fr;gap:1px 8px;margin-top:4px;color:#64748B;line-height:1.7">
                      <span style="font-family:monospace;color:#1E40AF">zenith_iso20022</span><span>Zenith Bank Nigeria — ISO 20022 pain.001 CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">gtb_csv</span><span>GTBank Nigeria — CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">access_csv</span><span>Access Bank Nigeria — CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">uba_csv</span><span>UBA Nigeria — CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">firstbank_csv</span><span>First Bank Nigeria — CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">sepa_xml</span><span>SEPA Credit Transfer XML — EU banks</span>
                      <span style="font-family:monospace;color:#1E40AF">bacs_csv</span><span>BACS Direct Credit — UK</span>
                      <span style="font-family:monospace;color:#1E40AF">ach_nacha</span><span>ACH / NACHA — USA</span>
                      <span style="font-family:monospace;color:#1E40AF">swift_mt103</span><span>SWIFT MT103 — International wires</span>
                    </div>
                    <div style="margin-top:8px;padding:6px 10px;background:#FEF3C7;border-radius:5px;font-size:10px;color:#92400E;border:1px solid #F59E0B">
                        <b>Highlighted columns in template:</b><br>
                        <b>CRED_ADDRESS_COUNTRYSUBDIVISION</b> ← Fill <code>Payee Address</code> on each row in the child table<br>
                        <b>CREDACC_BIC</b> ← Auto-resolved from <code>Payee Bank</code> name → BIC dictionary → Bank master
                    </div>
                </div>`,
            },
            ],
            primary_action_label: '📎 Generate & Attach',
            primary_action(vals) {
                this.hide();
                frappe.call({
                    method: _BBT.attach,
                    args: { source_doctype: 'Batch Bank Transaction', source_name: frm.doc.name, bank_format: (vals.bank_format || '').split(':')[0] },
                    freeze: true, freeze_message: 'Generating and attaching payment file…',
                    callback(r) {
                        const res = r.message || {};
                        if (res.success) {
                            frm.reload_doc();
                            frappe.show_alert({
                                message: `📎 Attached: <a href="${res.file_url}" target="_blank">${res.file_name}</a> · ${res.row_count} rows · ₦${(res.total_amount||0).toLocaleString()}`,
                                indicator: 'green'
                            }, 8);
                        } else {
                            frappe.msgprint({ title: '❌ Attach Failed', message: r.exc || 'Unknown error', indicator: 'red' });
                        }
                    }
                });
            }
        }).show();
    }});
}

// ── Email Payment File ────────────────────────────────────────────────────────

function _bbt_email_dialog(frm) {
    frappe.call({ method: _BBT.formats, callback: r => {
        const formats = (r.message || []);
        const fmtOpts = formats.map(f => f.key).join('\n');
        const rowCount = (frm.doc.transaction_entry || []).length;
        const total    = (frm.doc.total_outflow || 0) + (frm.doc.total_inflow || 0);

        new frappe.ui.Dialog({
            title: '📧 Email Bank Payment File',
            size: 'large',
            fields: [
                { fieldtype: 'HTML', options: `
                    <div style="background:#EFF6FF;border-left:4px solid #3B82F6;padding:10px 14px;border-radius:7px;margin-bottom:6px;font-size:12px;color:#1E40AF">
                        <b>${frm.doc.name}</b> · ${rowCount} transactions · ₦${total.toLocaleString()}<br>
                        The file will be generated and emailed as an attachment.
                    </div>` },
                { fieldname: 'bank_format', fieldtype: 'Select', label: 'Bank Format',
                  options: fmtOpts, reqd: 1, default: 'zenith_iso20022' },
            {
                fieldtype: 'HTML',
                options: `<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:8px 12px;font-size:11px;margin-top:-4px">
                    <b style="color:#475569">Format keys:</b>
                    <div style="display:grid;grid-template-columns:140px 1fr;gap:1px 8px;margin-top:4px;color:#64748B;line-height:1.7">
                      <span style="font-family:monospace;color:#1E40AF">zenith_iso20022</span><span>Zenith Bank Nigeria — ISO 20022 pain.001 CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">gtb_csv</span><span>GTBank Nigeria — CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">access_csv</span><span>Access Bank Nigeria — CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">uba_csv</span><span>UBA Nigeria — CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">firstbank_csv</span><span>First Bank Nigeria — CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">sepa_xml</span><span>SEPA Credit Transfer XML — EU banks</span>
                      <span style="font-family:monospace;color:#1E40AF">bacs_csv</span><span>BACS Direct Credit — UK</span>
                      <span style="font-family:monospace;color:#1E40AF">ach_nacha</span><span>ACH / NACHA — USA</span>
                      <span style="font-family:monospace;color:#1E40AF">swift_mt103</span><span>SWIFT MT103 — International wires</span>
                    </div>
                    <div style="margin-top:8px;padding:6px 10px;background:#FEF3C7;border-radius:5px;font-size:10px;color:#92400E;border:1px solid #F59E0B">
                        <b>Highlighted columns in template:</b><br>
                        <b>CRED_ADDRESS_COUNTRYSUBDIVISION</b> ← Fill <code>Payee Address</code> on each row in the child table<br>
                        <b>CREDACC_BIC</b> ← Auto-resolved from <code>Payee Bank</code> name → BIC dictionary → Bank master
                    </div>
                </div>`,
            },
                { fieldname: 'recipients', fieldtype: 'Data', label: 'Recipients (comma-separated)',
                  reqd: 1, default: frappe.session.user,
                  description: 'e.g. treasury@company.com, payments@zenithbank.com' },
                { fieldname: 'subject', fieldtype: 'Data', label: 'Subject',
                  default: `Bank Payment File — ${frm.doc.name}` },
                { fieldname: 'message', fieldtype: 'Small Text', label: 'Message (optional)',
                  description: 'Leave blank for auto-generated message' },
            ],
            primary_action_label: '📧 Send Email',
            primary_action(vals) {
                this.hide();
                frappe.call({
                    method: _BBT.email,
                    args: {
                        source_doctype: 'Batch Bank Transaction',
                        source_name:    frm.doc.name,
                        bank_format:    (vals.bank_format || '').split(':')[0],
                        recipients:     vals.recipients,
                        subject:        vals.subject,
                        message:        vals.message || null,
                    },
                    freeze: true, freeze_message: 'Generating file and sending email…',
                    callback(r) {
                        const res = r.message || {};
                        if (res.success) {
                            frm.reload_doc();
                            frappe.show_alert({
                                message: `📧 Sent: ${res.file_name} to ${(res.recipients||[]).join(', ')} · ${res.row_count} rows`,
                                indicator: 'green'
                            }, 8);
                        } else {
                            frappe.msgprint({ title: '❌ Email Failed', message: r.exc || 'Unknown error', indicator: 'red' });
                        }
                    }
                });
            }
        }).show();
    }});
}
