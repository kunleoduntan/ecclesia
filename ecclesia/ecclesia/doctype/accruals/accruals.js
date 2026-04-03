// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt


// ========================================
// ACCRUALS MANAGEMENT SYSTEM - PROFESSIONAL UI
// Modern, Clean Design for Financial Professionals
// ========================================

// Global state management
let ACCRUALS_INITIALIZED = false;
let ACCRUALS_STATE = {
    loading: false,
    validation: { errors: [], warnings: [] }
};

// ========================================
// INITIALIZATION
// ========================================

$(document).ready(function() {
    console.log('🏦 Professional Accruals UI Loading...');
    apply_professional_styles();
    initialize_application();
});

function initialize_application() {
    if (ACCRUALS_INITIALIZED || typeof frappe === 'undefined') {
        setTimeout(initialize_application, 300);
        return;
    }
    
    console.log('✅ Initializing Professional Accruals Form...');
    initialize_form_events();
    ACCRUALS_INITIALIZED = true;
}

// ========================================
// PROFESSIONAL STYLING SYSTEM
// ========================================

function apply_professional_styles() {
    if ($('#professional-accruals-styles').length) return;
    
    const css = `
        /* PROFESSIONAL DESIGN SYSTEM */
        :root {
            --primary: #3b82f6;
            --primary-dark: #2563eb;
            --primary-light: #eff6ff;
            --secondary: #64748b;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --info: #06b6d4;
            --background: #f8fafc;
            --surface: #ffffff;
            --border: #e2e8f0;
            --border-dark: #cbd5e1;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
            --text-light: #94a3b8;
            --shadow-sm: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            --radius-sm: 6px;
            --radius-md: 8px;
            --radius-lg: 12px;
            --radius-xl: 16px;
        }
        
        /* Dashboard Header */
        .accruals-dashboard {
            background: var(--surface);
            border-radius: var(--radius-lg);
            padding: 24px;
            margin-bottom: 24px;
            border: 1px solid var(--border);
            box-shadow: var(--shadow-sm);
            position: relative;
            overflow: hidden;
        }
        
        .accruals-dashboard::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--primary), var(--info));
        }
        
        .dashboard-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
        }
        
        .dashboard-title {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        
        .dashboard-icon {
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
        
        .dashboard-text h2 {
            margin: 0;
            color: var(--text-primary);
            font-size: 20px;
            font-weight: 700;
        }
        
        .dashboard-text p {
            margin: 4px 0 0 0;
            color: var(--text-secondary);
            font-size: 14px;
        }
        
        /* Status Badges */
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border: 1px solid;
        }
        
        .status-draft {
            background: var(--primary-light);
            color: var(--primary-dark);
            border-color: #bfdbfe;
        }
        
        .status-submitted {
            background: #d1fae5;
            color: #065f46;
            border-color: #a7f3d0;
        }
        
        .status-cancelled {
            background: #fee2e2;
            color: #991b1b;
            border-color: #fecaca;
        }
        
        /* Financial Metrics */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin: 24px 0;
        }
        
        .metric-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 20px;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .metric-card:hover {
            border-color: var(--primary);
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
        }
        
        .metric-card::before {
            content: '';
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 4px;
        }
        
        .metric-card.primary::before {
            background: var(--primary);
        }
        
        .metric-card.success::before {
            background: var(--success);
        }
        
        .metric-card.warning::before {
            background: var(--warning);
        }
        
        .metric-card.danger::before {
            background: var(--danger);
        }
        
        .metric-icon {
            width: 40px;
            height: 40px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 12px;
            font-size: 18px;
        }
        
        .metric-icon.primary { background: #eff6ff; color: var(--primary); }
        .metric-icon.success { background: #f0fdf4; color: var(--success); }
        .metric-icon.warning { background: #fffbeb; color: var(--warning); }
        .metric-icon.danger { background: #fef2f2; color: var(--danger); }
        
        .metric-value {
            font-size: 24px;
            font-weight: 700;
            color: var(--text-primary);
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
            color: var(--text-light);
            display: flex;
            align-items: center;
            gap: 4px;
        }
        
        /* Action Toolbar */
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
        
        .btn-professional {
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
        
        .btn-professional-primary {
            background: var(--primary);
            color: white;
        }
        
        .btn-professional-primary:hover {
            background: var(--primary-dark);
            transform: translateY(-1px);
            box-shadow: var(--shadow-md);
        }
        
        .btn-professional-secondary {
            background: white;
            color: var(--text-primary);
            border: 1px solid var(--border);
        }
        
        .btn-professional-secondary:hover {
            background: var(--background);
            border-color: var(--primary);
            transform: translateY(-1px);
        }
        
        .btn-professional-outline {
            background: transparent;
            color: var(--primary);
            border: 1px solid var(--primary);
        }
        
        .btn-professional-outline:hover {
            background: var(--primary);
            color: white;
        }
        
        /* Enhanced Grid */
        .grid-professional .grid-heading-row {
            background: var(--background) !important;
            border-bottom: 2px solid var(--border) !important;
        }
        
        .grid-professional .grid-heading-row .grid-static-col {
            color: var(--text-primary) !important;
            font-weight: 600 !important;
            font-size: 11px !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .grid-professional .grid-row {
            border-bottom: 1px solid var(--border) !important;
            transition: background-color 0.2s ease;
        }
        
        .grid-professional .grid-row:hover {
            background-color: #f1f5f9 !important;
        }
        
        /* Progress Indicators */
        .progress-bar {
            height: 6px;
            background: var(--border);
            border-radius: 3px;
            overflow: hidden;
            margin-top: 8px;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--primary), var(--info));
            border-radius: 3px;
            transition: width 0.3s ease;
        }
        
        /* Notification Bubble */
        .notification-bubble {
            position: absolute;
            top: -8px;
            right: -8px;
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
        
        /* Validation Cards */
        .validation-card {
            padding: 16px;
            border-radius: var(--radius-md);
            margin: 16px 0;
            border-left: 4px solid;
            background: white;
            box-shadow: var(--shadow-sm);
        }
        
        .validation-error {
            border-left-color: var(--danger);
            background: #fef2f2;
        }
        
        .validation-warning {
            border-left-color: var(--warning);
            background: #fffbeb;
        }
        
        .validation-success {
            border-left-color: var(--success);
            background: #f0fdf4;
        }
        
        .validation-info {
            border-left-color: var(--info);
            background: #ecfeff;
        }
        
        /* Loading Animation */
        .loading-shimmer {
            background: linear-gradient(
                90deg,
                var(--background) 0%,
                #f1f5f9 50%,
                var(--background) 100%
            );
            background-size: 200% 100%;
            animation: shimmer 1.5s infinite;
            border-radius: var(--radius-sm);
        }
        
        @keyframes shimmer {
            0% { background-position: -200% 0; }
            100% { background-position: 200% 0; }
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
        
        /* Modal Styling */
        .modal-professional {
            background: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(4px);
        }
        
        .modal-content-professional {
            background: var(--surface);
            border-radius: var(--radius-lg);
            border: none;
            box-shadow: var(--shadow-lg);
        }
        
        /* Responsive Design */
        @media (max-width: 768px) {
            .metrics-grid {
                grid-template-columns: 1fr;
            }
            
            .action-toolbar {
                flex-direction: column;
            }
            
            .btn-professional {
                width: 100%;
            }
            
            .dashboard-header {
                flex-direction: column;
                align-items: flex-start;
                gap: 12px;
            }
        }
        
        /* Form Field Enhancement */
        .field-highlight {
            background: linear-gradient(90deg, #f0f9ff, #e0f2fe) !important;
            border: 1px solid #7dd3fc !important;
            border-radius: var(--radius-sm) !important;
        }
    `;
    
    const style = document.createElement('style');
    style.id = 'professional-accruals-styles';
    style.textContent = css;
    document.head.appendChild(style);
}

// ========================================
// FORM EVENTS
// ========================================

function initialize_form_events() {
    frappe.ui.form.on("Accruals", {
        setup: function(frm) {
            setup_intelligent_filters(frm);
        },

        onload: function(frm) {
            create_dashboard_header(frm);
            create_financial_metrics(frm);
            add_action_buttons(frm);
        },

        refresh: function(frm) {
            update_dashboard_ui(frm);
            apply_professional_grid_styling(frm);
            update_financial_metrics(frm);
        },

        reporting_date: function(frm) {
            if (frm.doc.reporting_date) {
                try {
                    const date = new Date(frm.doc.reporting_date);
                    frm.set_value('month', 
                        date.toLocaleString('default', { month: 'long' }) + ' ' + 
                        date.getFullYear()
                    );
                } catch (error) {
                    console.error('Error setting month:', error);
                }
            }
        },

        before_save: function(frm) {
            calculate_all_totals(frm);
            run_smart_validations(frm);
        },

        process_accruals: function(frm) {
            if (frm.doc.process_accruals) {
                show_confirmation_dialog(
                    'Process Accruals',
                    'This will create journal entries and cannot be easily undone.',
                    function() {
                        process_accruals_batch(frm);
                    },
                    function() {
                        frm.set_value('process_accruals', 0);
                    }
                );
            }
        },

        company: function(frm) {
            if (frm.doc.company) {
                refresh_grid_filters(frm);
            }
        }
    });

    // Child table events
    frappe.ui.form.on("Accrued Expense Schedule", {
        accrued_expense_schedule_add: function(frm, cdt, cdn) {
            const row = locals[cdt][cdn];
            setup_new_row(frm, row, cdt, cdn);
        },

        trans_type: function(frm, cdt, cdn) {
            const row = locals[cdt][cdn];
            handle_trans_type_change(frm, row, cdt, cdn);
        },

        frequency: function(frm, cdt, cdn) {
            const row = locals[cdt][cdn];
            handle_frequency_change(frm, row, cdt, cdn);
        },

        gross_amount: function(frm, cdt, cdn) {
            const row = locals[cdt][cdn];
            calculate_row_amounts(frm, row, cdt, cdn);
            update_financial_metrics(frm);
        },

        exch_rate: function(frm, cdt, cdn) {
            const row = locals[cdt][cdn];
            calculate_row_amounts(frm, row, cdt, cdn);
        },

        currency: function(frm, cdt, cdn) {
            const row = locals[cdt][cdn];
            handle_currency_change(frm, row, cdt, cdn);
        },

        wht_rate: function(frm, cdt, cdn) {
            const row = locals[cdt][cdn];
            calculate_wht(frm, row, cdt, cdn);
        },

        charge_wht: function(frm, cdt, cdn) {
            const row = locals[cdt][cdn];
            handle_wht_toggle(frm, row, cdt, cdn);
        },

        payable_to: function(frm, cdt, cdn) {
            const row = locals[cdt][cdn];
            auto_populate_supplier_data(frm, row, cdt, cdn);
        }
    });
}

// ========================================
// DASHBOARD COMPONENTS
// ========================================

function create_dashboard_header(frm) {
    $('.accruals-dashboard').remove();
    
    const status = frm.doc.docstatus;
    let statusBadge = '';
    
    if (status === 0) {
        statusBadge = '<span class="status-badge status-draft">Draft</span>';
    } else if (status === 1) {
        statusBadge = '<span class="status-badge status-submitted">Submitted</span>';
    } else if (status === 2) {
        statusBadge = '<span class="status-badge status-cancelled">Cancelled</span>';
    }
    
    const headerHtml = `
        <div class="accruals-dashboard">
            <div class="dashboard-header">
                <div class="dashboard-title">
                    <div class="dashboard-icon">
                        <i class="fa fa-calculator"></i>
                    </div>
                    <div class="dashboard-text">
                        <h2>Accruals Management</h2>
                        <p>Professional accrual processing and reporting</p>
                    </div>
                </div>
                ${statusBadge}
            </div>
        </div>
    `;
    
    $(frm.wrapper).find('.form-section:first').before(headerHtml);
}

function create_financial_metrics(frm) {
    if (!frm.doc) return;
    
    $('.metrics-grid').remove();
    
    const entryCount = (frm.doc.accrued_expense_schedule || []).length;
    const budgetUsed = calculate_budget_utilization(frm);
    const avgAmount = calculate_average_amount(frm);
    const anomalyCount = calculate_anomalies(frm);
    
    const metricsHtml = `
        <div class="metrics-grid">
            <div class="metric-card primary">
                <div class="metric-icon primary">
                    <i class="fa fa-file-invoice-dollar"></i>
                </div>
                <div class="metric-value">${format_currency(frm.doc.total_accrued_amount || 0)}</div>
                <div class="metric-label">Total Accrued</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${budgetUsed > 100 ? 100 : budgetUsed}%"></div>
                </div>
            </div>
            
            <div class="metric-card danger">
                <div class="metric-icon danger">
                    <i class="fa fa-percentage"></i>
                </div>
                <div class="metric-value">${format_currency(frm.doc.total_wht || 0)}</div>
                <div class="metric-label">Total WHT</div>
                <div class="metric-subtitle">
                    <i class="fa fa-shield-alt"></i>
                    Tax compliance
                </div>
            </div>
            
            <div class="metric-card success">
                <div class="metric-icon success">
                    <i class="fa fa-chart-line"></i>
                </div>
                <div class="metric-value">${format_currency(frm.doc.total_charged_amount || 0)}</div>
                <div class="metric-label">Charged Amount</div>
                <div class="metric-subtitle">
                    <i class="fa fa-calendar-alt"></i>
                    Periodic charges
                </div>
            </div>
            
            <div class="metric-card warning">
                <div class="metric-icon warning">
                    <i class="fa fa-list-check"></i>
                </div>
                <div class="metric-value">${entryCount}</div>
                <div class="metric-label">Total Entries</div>
                <div class="metric-subtitle">
                    <i class="fa fa-exclamation-circle"></i>
                    ${anomalyCount} issues
                </div>
            </div>
        </div>
    `;
    
    $('.accruals-dashboard').append(metricsHtml);
}

function update_financial_metrics(frm) {
    create_financial_metrics(frm);
}

// ========================================
// ACTION BUTTONS
// ========================================

function add_action_buttons(frm) {
    $('.action-toolbar').remove();
    
    const hasEntries = frm.doc.accrued_expense_schedule && frm.doc.accrued_expense_schedule.length > 0;
    const anomalyCount = calculate_anomalies(frm);
    
    const buttonsHtml = `
        <div class="action-toolbar">
            <button class="btn-professional btn-professional-primary" id="btn-auto-fill">
                <i class="fa fa-robot"></i>
                Auto-Fill
                ${anomalyCount > 0 ? `<span class="notification-bubble">${anomalyCount}</span>` : ''}
            </button>
            
            <button class="btn-professional btn-professional-secondary" id="btn-calculate">
                <i class="fa fa-calculator"></i>
                Calculate
            </button>
            
            <button class="btn-professional btn-professional-secondary" id="btn-validate">
                <i class="fa fa-check-circle"></i>
                Validate
            </button>
            
            <button class="btn-professional btn-professional-secondary" id="btn-preview">
                <i class="fa fa-eye"></i>
                Preview
            </button>
            
            <button class="btn-professional btn-professional-secondary" id="btn-export">
                <i class="fa fa-file-export"></i>
                Export
            </button>
            
            ${frm.doc.docstatus === 0 ? `
                <button class="btn-professional btn-professional-outline" id="btn-process">
                    <i class="fa fa-play"></i>
                    Process
                </button>
            ` : ''}
        </div>
    `;
    
    $('.accruals-dashboard').after(buttonsHtml);
    
    // Attach event handlers
    attach_button_handlers(frm);
}

function attach_button_handlers(frm) {
    $('#btn-auto-fill').off('click').on('click', () => run_smart_autofill(frm));
    $('#btn-calculate').off('click').on('click', () => calculate_all_totals(frm));
    $('#btn-validate').off('click').on('click', () => run_comprehensive_validation(frm));
    $('#btn-preview').off('click').on('click', () => preview_journal_entries(frm));
    $('#btn-export').off('click').on('click', () => export_to_excel(frm));
    $('#btn-process').off('click').on('click', () => {
        frm.set_value('process_accruals', 1);
        frm.save();
    });
}

// ========================================
// GRID STYLING
// ========================================

function apply_professional_grid_styling(frm) {
    setTimeout(() => {
        if (frm.fields_dict.accrued_expense_schedule && frm.fields_dict.accrued_expense_schedule.grid) {
            const grid = frm.fields_dict.accrued_expense_schedule.grid;
            $(grid.wrapper).addClass('grid-professional');
            
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

// ========================================
// INTELLIGENT FEATURES
// ========================================

function run_smart_autofill(frm) {
    if (!frm.doc.accrued_expense_schedule || frm.doc.accrued_expense_schedule.length === 0) {
        show_toast_message('No entries to auto-fill', 'warning');
        return;
    }
    
    show_loading(frm, 'Auto-filling data...');
    
    let filledCount = 0;
    const promises = [];
    
    frm.doc.accrued_expense_schedule.forEach((row, idx) => {
        const cdt = row.doctype;
        const cdn = row.name;
        
        // Auto-fill WHT
        if (!row.charge_wht && row.payable_to && detect_wht_requirement(row.payable_to)) {
            promises.push(
                frappe.model.set_value(cdt, cdn, 'charge_wht', 1)
                    .then(() => filledCount++)
                    .catch(console.error)
            );
        }
        
        // Auto-generate description
        if (!row.description || row.description.trim() === '') {
            const desc = generate_smart_description(row, frm);
            promises.push(
                frappe.model.set_value(cdt, cdn, 'description', desc)
                    .then(() => filledCount++)
                    .catch(console.error)
            );
        }
    });
    
    Promise.all(promises).then(() => {
        hide_loading(frm);
        frm.refresh_field('accrued_expense_schedule');
        
        if (filledCount > 0) {
            show_toast_message(`Auto-filled ${filledCount} fields`, 'success');
        } else {
            show_toast_message('All fields already populated', 'info');
        }
    }).catch(error => {
        hide_loading(frm);
        console.error('Auto-fill error:', error);
        show_toast_message('Error during auto-fill', 'error');
    });
}

function detect_wht_requirement(payable_to) {
    if (!payable_to) return false;
    const lower = payable_to.toLowerCase();
    return lower.includes('limited') || lower.includes('ltd') || 
           lower.includes('plc') || lower.includes('inc');
}

function generate_smart_description(row, frm) {
    const parts = [];
    if (row.trans_type) parts.push(row.trans_type);
    if (row.payable_to) parts.push(`for ${row.payable_to}`);
    if (frm.doc.month) parts.push(`(${frm.doc.month})`);
    return parts.join(' ') || 'Accrual Entry';
}

// ========================================
// CALCULATION FUNCTIONS
// ========================================

function calculate_row_amounts(frm, row, cdt, cdn) {
    const gross = flt(row.gross_amount);
    const exch = flt(row.exch_rate) || 1;
    const lc = row.currency !== "NGN" ? gross * exch : gross;
    
    frappe.model.set_value(cdt, cdn, 'lc_amount', lc);
    
    if (row.no_of_periods && flt(row.no_of_periods) > 0) {
        const periodic = lc / flt(row.no_of_periods);
        frappe.model.set_value(cdt, cdn, 'periodic_charge', periodic);
    }
    
    calculate_wht(frm, row, cdt, cdn);
    calculate_all_totals(frm);
}

function calculate_wht(frm, row, cdt, cdn) {
    if (!row.charge_wht) {
        frappe.model.set_value(cdt, cdn, 'wh_tax', 0);
        frappe.model.set_value(cdt, cdn, 'net_amount', flt(row.lc_amount));
        return;
    }
    
    const lc = flt(row.lc_amount);
    const rate = flt(row.wht_rate);
    const wht = lc * rate / 100;
    
    frappe.model.set_value(cdt, cdn, 'wh_tax', wht);
    frappe.model.set_value(cdt, cdn, 'net_amount', lc - wht);
}

function calculate_all_totals(frm) {
    if (!frm.doc) return;
    
    let total_accrued = 0;
    let total_wht = 0;
    let total_charged = 0;
    
    (frm.doc.accrued_expense_schedule || []).forEach(row => {
        total_accrued += flt(row.lc_amount);
        total_wht += flt(row.wh_tax);
        total_charged += flt(row.periodic_charge);
    });
    
    frm.set_value('total_accrued_amount', total_accrued);
    frm.set_value('total_wht', total_wht);
    frm.set_value('total_charged_amount', total_charged);
    
    update_financial_metrics(frm);
}

// ========================================
// VALIDATION FUNCTIONS
// ========================================

function run_comprehensive_validation(frm) {
    if (!frm.doc) return;
    
    ACCRUALS_STATE.validation.errors = [];
    ACCRUALS_STATE.validation.warnings = [];
    
    // Basic validations
    if (!frm.doc.reporting_date) {
        ACCRUALS_STATE.validation.errors.push('Reporting Date is required');
    }
    
    if (!frm.doc.company) {
        ACCRUALS_STATE.validation.errors.push('Company is required');
    }
    
    if (!frm.doc.accrued_expense_schedule || frm.doc.accrued_expense_schedule.length === 0) {
        ACCRUALS_STATE.validation.errors.push('At least one accrual entry is required');
    }
    
    // Row validations
    (frm.doc.accrued_expense_schedule || []).forEach((row, idx) => {
        const rowNum = idx + 1;
        
        if (!row.payable_to) {
            ACCRUALS_STATE.validation.errors.push(`Row ${rowNum}: Payable To is required`);
        }
        
        if (!row.dr_account) {
            ACCRUALS_STATE.validation.errors.push(`Row ${rowNum}: Debit Account is required`);
        }
        
        if (!row.cr_account) {
            ACCRUALS_STATE.validation.errors.push(`Row ${rowNum}: Credit Account is required`);
        }
        
        if (flt(row.gross_amount) <= 0) {
            ACCRUALS_STATE.validation.errors.push(`Row ${rowNum}: Gross Amount must be greater than 0`);
        }
        
        if (row.trans_type === "ACCRUAL & PREPAY" && !row.deferred_expense_account) {
            ACCRUALS_STATE.validation.errors.push(`Row ${rowNum}: Deferred Expense Account is required for prepayments`);
        }
        
        // Warnings
        if (row.currency !== "NGN" && (!row.exch_rate || flt(row.exch_rate) <= 0)) {
            ACCRUALS_STATE.validation.warnings.push(`Row ${rowNum}: Exchange Rate is required for foreign currency`);
        }
        
        if (row.charge_wht && !row.wht_account) {
            ACCRUALS_STATE.validation.warnings.push(`Row ${rowNum}: WHT Account should be specified`);
        }
    });
    
    display_validation_results();
}

function display_validation_results() {
    $('.validation-results').remove();
    
    const errors = ACCRUALS_STATE.validation.errors;
    const warnings = ACCRUALS_STATE.validation.warnings;
    
    let html = '<div class="validation-results">';
    
    if (errors.length > 0) {
        html += `
            <div class="validation-card validation-error">
                <div style="display: flex; align-items: flex-start; gap: 12px;">
                    <div style="font-size: 20px; color: var(--danger);">❌</div>
                    <div>
                        <div style="font-weight: 600; color: var(--danger); margin-bottom: 8px;">
                            ${errors.length} Validation Error${errors.length !== 1 ? 's' : ''}
                        </div>
                        <div style="font-size: 13px; color: #991b1b;">
                            ${errors.slice(0, 5).map(e => `<div style="margin-bottom: 4px;">• ${e}</div>`).join('')}
                            ${errors.length > 5 ? `<div style="margin-top: 4px; font-style: italic;">... and ${errors.length - 5} more errors</div>` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    if (warnings.length > 0) {
        html += `
            <div class="validation-card validation-warning">
                <div style="display: flex; align-items: flex-start; gap: 12px;">
                    <div style="font-size: 20px; color: var(--warning);">⚠️</div>
                    <div>
                        <div style="font-weight: 600; color: var(--warning); margin-bottom: 8px;">
                            ${warnings.length} Warning${warnings.length !== 1 ? 's' : ''}
                        </div>
                        <div style="font-size: 13px; color: #92400e;">
                            ${warnings.slice(0, 5).map(w => `<div style="margin-bottom: 4px;">• ${w}</div>`).join('')}
                            ${warnings.length > 5 ? `<div style="margin-top: 4px; font-style: italic;">... and ${warnings.length - 5} more warnings</div>` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    if (errors.length === 0 && warnings.length === 0) {
        html += `
            <div class="validation-card validation-success">
                <div style="display: flex; align-items: flex-start; gap: 12px;">
                    <div style="font-size: 20px; color: var(--success);">✅</div>
                    <div>
                        <div style="font-weight: 600; color: var(--success); margin-bottom: 4px;">
                            All Validations Passed
                        </div>
                        <div style="font-size: 13px; color: #065f46;">
                            No issues detected. Ready to process.
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    html += '</div>';
    
    $('.action-toolbar').after(html);
}

function run_smart_validations(frm) {
    if (!frm.doc) return;
    
    const errors = [];
    
    if (frm.doc.accrued_expense_schedule) {
        frm.doc.accrued_expense_schedule.forEach((row, idx) => {
            if (row.dr_account === row.cr_account && row.dr_account && row.cr_account) {
                errors.push(`Row ${idx + 1}: Debit and Credit accounts cannot be the same`);
            }
        });
    }
    
    if (errors.length > 0) {
        frappe.validated = false;
        frappe.throw(errors.join('<br>'));
    }
}

// ========================================
// PREVIEW & EXPORT
// ========================================

function preview_journal_entries(frm) {
    if (!frm.doc.accrued_expense_schedule || frm.doc.accrued_expense_schedule.length === 0) {
        show_toast_message('No entries to preview', 'warning');
        return;
    }
    
    let html = `
        <div style="padding: 24px;">
            <div class="section-header" style="border: none; padding: 0; margin: 0 0 20px 0;">
                <div class="section-title">
                    <div class="section-title-icon">
                        <i class="fa fa-file-invoice"></i>
                    </div>
                    <div>Journal Entry Preview</div>
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px;">
                <div style="background: #f8fafc; padding: 16px; border-radius: 8px; border: 1px solid #e2e8f0;">
                    <div style="font-size: 12px; color: #64748b; font-weight: 600; margin-bottom: 8px;">Document Summary</div>
                    <div style="font-size: 13px; color: #475569;">
                        <div style="margin-bottom: 6px;"><strong>Company:</strong> ${frm.doc.company || 'Not set'}</div>
                        <div style="margin-bottom: 6px;"><strong>Reporting Date:</strong> ${frm.doc.reporting_date || 'Not set'}</div>
                        <div style="margin-bottom: 6px;"><strong>Month:</strong> ${frm.doc.month || 'Not set'}</div>
                        <div><strong>Total Entries:</strong> ${frm.doc.accrued_expense_schedule.length}</div>
                    </div>
                </div>
                
                <div style="background: #f8fafc; padding: 16px; border-radius: 8px; border: 1px solid #e2e8f0;">
                    <div style="font-size: 12px; color: #64748b; font-weight: 600; margin-bottom: 8px;">Financial Summary</div>
                    <div style="font-size: 13px; color: #475569;">
                        <div style="margin-bottom: 6px;"><strong>Total Accrued:</strong> ${format_currency(frm.doc.total_accrued_amount || 0)}</div>
                        <div style="margin-bottom: 6px;"><strong>Total WHT:</strong> ${format_currency(frm.doc.total_wht || 0)}</div>
                        <div style="margin-bottom: 6px;"><strong>Total Charged:</strong> ${format_currency(frm.doc.total_charged_amount || 0)}</div>
                        <div><strong>Net Payable:</strong> ${format_currency(flt(frm.doc.total_accrued_amount) - flt(frm.doc.total_wht))}</div>
                    </div>
                </div>
            </div>
            
            <div style="max-height: 400px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 8px;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead style="background: #f1f5f9; position: sticky; top: 0;">
                        <tr>
                            <th style="padding: 12px; border-bottom: 1px solid #e2e8f0; text-align: left; font-weight: 600; font-size: 11px; color: #475569; text-transform: uppercase;">#</th>
                            <th style="padding: 12px; border-bottom: 1px solid #e2e8f0; text-align: left; font-weight: 600; font-size: 11px; color: #475569; text-transform: uppercase;">Payable To</th>
                            <th style="padding: 12px; border-bottom: 1px solid #e2e8f0; text-align: left; font-weight: 600; font-size: 11px; color: #475569; text-transform: uppercase;">Gross Amount</th>
                            <th style="padding: 12px; border-bottom: 1px solid #e2e8f0; text-align: left; font-weight: 600; font-size: 11px; color: #475569; text-transform: uppercase;">WHT</th>
                            <th style="padding: 12px; border-bottom: 1px solid #e2e8f0; text-align: left; font-weight: 600; font-size: 11px; color: #475569; text-transform: uppercase;">Net Amount</th>
                        </tr>
                    </thead>
                    <tbody>
    `;
    
    frm.doc.accrued_expense_schedule.forEach((row, idx) => {
        html += `
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 12px;">${idx + 1}</td>
                <td style="padding: 12px;">${row.payable_to || ''}</td>
                <td style="padding: 12px;">${format_currency(row.gross_amount || 0, row.currency)}</td>
                <td style="padding: 12px;">${row.charge_wht ? format_currency(row.wh_tax || 0) : 'No'}</td>
                <td style="padding: 12px;">${format_currency(row.net_amount || 0)}</td>
            </tr>
        `;
    });
    
    html += `
                    </tbody>
                </table>
            </div>
        </div>
    `;
    
    frappe.msgprint({
        title: __('Journal Entry Preview'),
        message: html,
        width: 800,
        min_height: 500
    });
}

function export_to_excel(frm) {
    if (!frm.doc.accrued_expense_schedule || frm.doc.accrued_expense_schedule.length === 0) {
        show_toast_message('No data to export', 'warning');
        return;
    }
    
    show_loading(frm, 'Preparing export...');
    
    try {
        let csv = 'Accruals Export\n';
        csv += `Company: ${frm.doc.company || ''}\n`;
        csv += `Reporting Date: ${frm.doc.reporting_date || ''}\n`;
        csv += `Month: ${frm.doc.month || ''}\n\n`;
        
        csv += 'No.,Payable To,Transaction Type,Description,Currency,Gross Amount,Exchange Rate,LC Amount,WHT Rate,WHT Amount,Net Amount,Debit Account,Credit Account\n';
        
        frm.doc.accrued_expense_schedule.forEach((row, idx) => {
            csv += [
                idx + 1,
                `"${(row.payable_to || '').replace(/"/g, '""')}"`,
                row.trans_type || '',
                `"${(row.description || '').replace(/"/g, '""')}"`,
                row.currency || 'NGN',
                row.gross_amount || 0,
                row.exch_rate || 1,
                row.lc_amount || 0,
                row.wht_rate || 0,
                row.wh_tax || 0,
                row.net_amount || 0,
                row.dr_account || '',
                row.cr_account || ''
            ].join(',') + '\n';
        });
        
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        
        link.href = url;
        link.download = `Accruals_${frm.doc.company || 'Export'}_${frappe.datetime.get_today()}.csv`;
        link.style.display = 'none';
        
        document.body.appendChild(link);
        link.click();
        
        setTimeout(() => {
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        }, 100);
        
        hide_loading(frm);
        show_toast_message('Export completed successfully', 'success');
    } catch (error) {
        hide_loading(frm);
        console.error('Export error:', error);
        show_toast_message('Error during export', 'error');
    }
}

// ========================================
// UTILITY FUNCTIONS
// ========================================

function flt(val) {
    if (val === null || val === undefined || val === '') return 0;
    return parseFloat(val) || 0;
}

function format_currency(amount, currency = 'NGN') {
    if (!frappe.format) return amount.toLocaleString();
    return frappe.format(amount, {fieldtype: "Currency", options: currency});
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
    }, 4);
}

function show_confirmation_dialog(title, message, confirmCallback, cancelCallback) {
    frappe.confirm(message, confirmCallback, cancelCallback);
}

function show_loading(frm, message = 'Processing...') {
    if (ACCRUALS_STATE.loading) return;
    ACCRUALS_STATE.loading = true;
    
    frappe.show_progress(message, 0, 100);
}

function hide_loading(frm) {
    if (!ACCRUALS_STATE.loading) return;
    ACCRUALS_STATE.loading = false;
    
    frappe.hide_progress();
}

function calculate_budget_utilization(frm) {
    // Placeholder for budget calculation
    return 0;
}

function calculate_average_amount(frm) {
    if (!frm.doc.accrued_expense_schedule || frm.doc.accrued_expense_schedule.length === 0) return 0;
    
    const total = frm.doc.accrued_expense_schedule.reduce((sum, row) => sum + flt(row.lc_amount), 0);
    return total / frm.doc.accrued_expense_schedule.length;
}

function calculate_anomalies(frm) {
    if (!frm.doc.accrued_expense_schedule) return 0;
    
    let count = 0;
    frm.doc.accrued_expense_schedule.forEach(row => {
        if (!row.description || row.description.trim() === '') count++;
        if (!row.dr_account) count++;
        if (!row.cr_account) count++;
        if (flt(row.gross_amount) > 10000000) count++; // Large amount check
    });
    
    return count;
}

// ========================================
// HELPER FUNCTIONS
// ========================================

function setup_new_row(frm, row, cdt, cdn) {
    setTimeout(() => {
        if (!row.currency) frappe.model.set_value(cdt, cdn, 'currency', 'NGN');
        if (!row.exch_rate) frappe.model.set_value(cdt, cdn, 'exch_rate', 1);
        if (!row.frequency) frappe.model.set_value(cdt, cdn, 'frequency', 'NA');
        if (!row.trans_type) frappe.model.set_value(cdt, cdn, 'trans_type', 'ACCRUAL');
    }, 100);
}

function handle_trans_type_change(frm, row, cdt, cdn) {
    if (row.trans_type === "ACCRUAL & PREPAY" && !row.no_of_periods) {
        frappe.model.set_value(cdt, cdn, 'no_of_periods', 1);
    }
}

function handle_frequency_change(frm, row, cdt, cdn) {
    if (row.frequency && row.frequency !== "NA") {
        const periods_map = { 'Monthly': 1, 'Quarterly': 3, 'Bi-Annually': 6, 'Annually': 12 };
        if (!row.no_of_periods) {
            frappe.model.set_value(cdt, cdn, 'no_of_periods', periods_map[row.frequency] || 1);
        }
    }
}

function handle_currency_change(frm, row, cdt, cdn) {
    if (row.currency === "NGN") {
        frappe.model.set_value(cdt, cdn, 'exch_rate', 1);
    }
}

function handle_wht_toggle(frm, row, cdt, cdn) {
    if (row.charge_wht && !row.wht_rate) {
        frappe.model.set_value(cdt, cdn, 'wht_rate', 10);
    }
    calculate_wht(frm, row, cdt, cdn);
}

function auto_populate_supplier_data(frm, row, cdt, cdn) {
    // Placeholder for supplier data population
}

function setup_intelligent_filters(frm) {
    if (!frm.doc) return;
    
    frm.set_query('dr_account', 'accrued_expense_schedule', function() {
        return {
            filters: {
                'company': frm.doc.company,
                'is_group': 0
            }
        };
    });
    
    frm.set_query('cr_account', 'accrued_expense_schedule', function() {
        return {
            filters: {
                'company': frm.doc.company,
                'is_group': 0
            }
        };
    });
}

function refresh_grid_filters(frm) {
    if (frm.fields_dict.accrued_expense_schedule?.grid) {
        frm.fields_dict.accrued_expense_schedule.grid.refresh();
    }
}

function update_dashboard_ui(frm) {
    const header = $('.dashboard-text h2');
    if (header.length) {
        header.text('Accruals Management' + (frm.doc.name ? ` • ${frm.doc.name}` : ''));
    }
}

function process_accruals_batch(frm) {
    show_loading(frm, 'Processing accruals...');
    
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.accruals.accruals.process_accruals',
        args: { accrual_doc: frm.doc.name },
        freeze: true,
        callback: function(r) {
            hide_loading(frm);
            if (r.message?.success) {
                show_toast_message(r.message.message, 'success');
                frm.reload_doc();
            } else {
                frappe.msgprint({
                    title: __('Processing Error'),
                    indicator: 'red',
                    message: r.message?.message || __('An error occurred')
                });
            }
        },
        error: function() {
            hide_loading(frm);
            show_toast_message('Error processing accruals', 'error');
        }
    });
}

// ========================================
// INITIALIZATION COMPLETE
// ========================================

console.log('✅ Professional Accruals UI Ready');