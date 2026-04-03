// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt



// Stock Availability Client Script
// Modern, optimized UI/UX with comprehensive features

frappe.ui.form.on('Stock Availability', {
    refresh: function(frm) {
        setup_custom_buttons(frm);
        apply_alternating_row_colors(frm);
        setup_dashboard(frm);
        set_field_properties(frm);
    },

    onload: function(frm) {
        setup_filters(frm);
    },

    report_date: function(frm) {
        update_month_and_note(frm);
    },

    warehouse: function(frm) {
        if (frm.doc.warehouse && frm.doc.report_date) {
            update_report_note(frm);
        }
    },

    criterion: function(frm) {
        handle_criterion_change(frm);
    },

    before_save: function(frm) {
        calculate_totals(frm);
    }
});


// ===========================
// Custom Buttons Setup
// ===========================

function setup_custom_buttons(frm) {
    if (!frm.is_new()) {
        // Primary action button
        frm.page.set_primary_action(__('Fetch Stock Balance'), function() {
            fetch_stock_balance(frm);
        }, 'refresh');

        // Secondary actions
        frm.add_custom_button(__('Email Report'), function() {
            send_email_report(frm);
        }, __('Actions'));

        frm.add_custom_button(__('Export to Excel'), function() {
            export_to_excel(frm);
        }, __('Actions'));

        frm.add_custom_button(__('Create Material Request'), function() {
            create_material_request(frm);
        }, __('Actions'));

        frm.add_custom_button(__('Refresh Dashboard'), function() {
            setup_dashboard(frm);
        }, __('Actions'));
    }
}


// ===========================
// Stock Balance Fetching
// ===========================

function fetch_stock_balance(frm) {
    if (!frm.doc.company || !frm.doc.warehouse || !frm.doc.report_date) {
        frappe.msgprint({
            title: __('Missing Information'),
            message: __('Please select Company, Warehouse, and Report Date'),
            indicator: 'red'
        });
        return;
    }

    frappe.call({
        method: 'ecclesia.ecclesia.doctype.stock_availability.stock_availability.fetch_stock_balance',
        args: {
            docname: frm.doc.name
        },
        freeze: true,
        freeze_message: __('Fetching stock data...'),
        callback: function(r) {
            if (r.message) {
                frm.reload_doc();
                
                if (r.message.status === 'success') {
                    frappe.show_alert({
                        message: r.message.message,
                        indicator: 'green'
                    }, 5);
                    
                    setup_dashboard(frm);
                } else if (r.message.status === 'warning') {
                    frappe.msgprint({
                        title: __('Warning'),
                        message: r.message.message,
                        indicator: 'orange'
                    });
                } else {
                    frappe.msgprint({
                        title: __('Error'),
                        message: r.message.message,
                        indicator: 'red'
                    });
                }
            }
        },
        error: function(r) {
            frappe.msgprint({
                title: __('Error'),
                message: __('Failed to fetch stock balance. Please check error logs.'),
                indicator: 'red'
            });
        }
    });
}


// ===========================
// Email Functionality
// ===========================

function send_email_report(frm) {
    if (!frm.doc.send_to) {
        frappe.msgprint({
            title: __('No Recipients'),
            message: __('Please add email recipients in the Email tab'),
            indicator: 'orange'
        });
        return;
    }

    frappe.confirm(
        __('Send stock availability report to {0}?', [frm.doc.send_to]),
        function() {
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.stock_availability.stock_availability.send_stock_availability_report',
                args: {
                    docname: frm.doc.name
                },
                freeze: true,
                freeze_message: __('Sending email...'),
                callback: function(r) {
                    if (r.message && r.message.status === 'success') {
                        frappe.show_alert({
                            message: r.message.message,
                            indicator: 'green'
                        }, 7);
                    } else if (r.message) {
                        frappe.msgprint({
                            title: __('Error'),
                            message: r.message.message,
                            indicator: 'red'
                        });
                    }
                }
            });
        }
    );
}


// ===========================
// Excel Export
// ===========================

function export_to_excel(frm) {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.stock_availability.stock_availability.export_to_excel',
        args: {
            docname: frm.doc.name
        },
        freeze: true,
        freeze_message: __('Generating Excel file...'),
        callback: function(r) {
            if (r.message) {
                frappe.show_alert({
                    message: __('Excel file downloaded successfully'),
                    indicator: 'green'
                }, 5);
            }
        }
    });
}


// ===========================
// Material Request Creation
// ===========================

function create_material_request(frm) {
    if (!frm.doc.stock_balance_entry || frm.doc.stock_balance_entry.length === 0) {
        frappe.msgprint({
            title: __('No Items'),
            message: __('Please fetch stock balance first'),
            indicator: 'orange'
        });
        return;
    }

    frappe.confirm(
        __('Create Material Request for items below reorder level?'),
        function() {
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.stock_availability.stock_availability.create_material_request',
                args: {
                    docname: frm.doc.name
                },
                freeze: true,
                freeze_message: __('Creating Material Request...'),
                callback: function(r) {
                    if (r.message && r.message.status === 'success') {
                        frappe.show_alert({
                            message: r.message.message,
                            indicator: 'green'
                        }, 5);
                        
                        // Navigate to the created Material Request
                        frappe.set_route('Form', 'Material Request', r.message.docname);
                    } else if (r.message) {
                        frappe.msgprint({
                            title: __(r.message.status === 'warning' ? 'Warning' : 'Error'),
                            message: r.message.message,
                            indicator: r.message.status === 'warning' ? 'orange' : 'red'
                        });
                    }
                }
            });
        }
    );
}


// ===========================
// Dashboard Setup
// ===========================

function setup_dashboard(frm) {
    if (frm.is_new() || !frm.doc.stock_balance_entry || frm.doc.stock_balance_entry.length === 0) {
        return;
    }

    let total_items = frm.doc.stock_balance_entry.length;
    let total_value = 0;
    let items_below_reorder = 0;
    let total_reorder_value = 0;

    frm.doc.stock_balance_entry.forEach(function(item) {
        total_value += (item.qty * item.cost_price) || 0;
        
        if (item.qty < item.reorder_level) {
            items_below_reorder++;
            let reorder_qty = Math.max(0, item.reorder_level - item.qty);
            total_reorder_value += reorder_qty * item.cost_price;
        }
    });

    let currency = frappe.boot.sysdefaults.currency || 'NGN';

    // Build dashboard HTML
    let dashboard_html = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-bottom: 20px;">
            <div class="stock-stat-card">
                <div class="stat-icon" style="background: #e0f2fe;">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#0284c7" stroke-width="2">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                        <line x1="3" y1="9" x2="21" y2="9"></line>
                        <line x1="9" y1="21" x2="9" y2="9"></line>
                    </svg>
                </div>
                <div class="stat-content">
                    <div class="stat-label">Total Items</div>
                    <div class="stat-value">${total_items}</div>
                </div>
            </div>

            <div class="stock-stat-card">
                <div class="stat-icon" style="background: #dcfce7;">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2">
                        <line x1="12" y1="1" x2="12" y2="23"></line>
                        <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
                    </svg>
                </div>
                <div class="stat-content">
                    <div class="stat-label">Total Stock Value</div>
                    <div class="stat-value">${format_currency(total_value, currency)}</div>
                </div>
            </div>

            <div class="stock-stat-card">
                <div class="stat-icon" style="background: ${items_below_reorder > 0 ? '#fee2e2' : '#dcfce7'};">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="${items_below_reorder > 0 ? '#dc2626' : '#16a34a'}" stroke-width="2">
                        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                        <line x1="12" y1="9" x2="12" y2="13"></line>
                        <line x1="12" y1="17" x2="12.01" y2="17"></line>
                    </svg>
                </div>
                <div class="stat-content">
                    <div class="stat-label">Items Below Reorder</div>
                    <div class="stat-value" style="color: ${items_below_reorder > 0 ? '#dc2626' : '#16a34a'};">
                        ${items_below_reorder}
                    </div>
                </div>
            </div>

            ${items_below_reorder > 0 ? `
            <div class="stock-stat-card">
                <div class="stat-icon" style="background: #fef3c7;">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2">
                        <circle cx="9" cy="21" r="1"></circle>
                        <circle cx="20" cy="21" r="1"></circle>
                        <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
                    </svg>
                </div>
                <div class="stat-content">
                    <div class="stat-label">Reorder Cost</div>
                    <div class="stat-value">${format_currency(total_reorder_value, currency)}</div>
                </div>
            </div>
            ` : ''}
        </div>

        <style>
            .stock-stat-card {
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 16px;
                display: flex;
                align-items: center;
                gap: 12px;
                transition: all 0.3s ease;
            }
            .stock-stat-card:hover {
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                transform: translateY(-2px);
            }
            .stat-icon {
                width: 48px;
                height: 48px;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .stat-content {
                flex: 1;
            }
            .stat-label {
                font-size: 12px;
                color: #6b7280;
                margin-bottom: 4px;
            }
            .stat-value {
                font-size: 20px;
                font-weight: 600;
                color: #111827;
            }
        </style>
    `;

    frm.dashboard.add_section(dashboard_html, __('Stock Analysis Dashboard'));
}


// ===========================
// UI Enhancements
// ===========================

function apply_alternating_row_colors(frm) {
    setTimeout(() => {
        frm.fields_dict.stock_balance_entry.grid.wrapper.find('.grid-row').each(function(i, row) {
            let $row = $(row);
            if (i % 2 === 0) {
                $row.css('background-color', '#ffffff');
            } else {
                $row.css('background-color', '#f9fafb');
            }
            
            // Highlight items below reorder level
            let item_data = frm.doc.stock_balance_entry[i];
            if (item_data && item_data.qty < item_data.reorder_level) {
                $row.css('background-color', '#fef2f2');
                $row.css('border-left', '3px solid #ef4444');
            }
        });
    }, 500);
}


function set_field_properties(frm) {
    // Make calculated fields read-only
    frm.set_df_property('month', 'read_only', 1);
    frm.set_df_property('total', 'read_only', 1);
    frm.set_df_property('report_note', 'read_only', 1);

    // Set field descriptions
    frm.set_df_property('criterion', 'description', 
        'Availability: All items | Reorder Level: Only items below reorder level');
}


function setup_filters(frm) {
    // Warehouse filter
    frm.set_query('warehouse', function() {
        return {
            filters: {
                'company': frm.doc.company,
                'is_group': 0
            }
        };
    });
}


// ===========================
// Data Processing
// ===========================

function update_month_and_note(frm) {
    if (frm.doc.report_date) {
        const reportDate = new Date(frm.doc.report_date);
        const monthName = reportDate.toLocaleString('default', { month: 'long', year: 'numeric' });
        frm.set_value('month', monthName);
        update_report_note(frm);
    }
}


function update_report_note(frm) {
    if (frm.doc.report_date && frm.doc.warehouse) {
        let note = `Stock availability report for ${frm.doc.warehouse} as at ${frappe.format(frm.doc.report_date, {fieldtype: 'Date'})}`;
        frm.set_value('report_note', note);
    }
}


function handle_criterion_change(frm) {
    if (frm.doc.criterion === "Reorder Level") {
        frappe.show_alert({
            message: __('Criterion changed to Reorder Level. Fetch stock to see items below reorder.'),
            indicator: 'blue'
        }, 5);
    }
}


function calculate_totals(frm) {
    let total = 0;
    let total_reorder = 0;
    
    $.each(frm.doc.stock_balance_entry || [], function(index, item) {
        // Calculate amount
        let amount = (item.qty || 0) * (item.cost_price || 0);
        frappe.model.set_value(item.doctype, item.name, "amount", amount);
        total += amount;
        
        // Calculate reorder qty and amount
        let reorder_qty = Math.max(0, (item.reorder_level || 0) - (item.qty || 0));
        frappe.model.set_value(item.doctype, item.name, "reorder_qty", reorder_qty);
        
        let reorder_amount = reorder_qty * (item.cost_price || 0);
        frappe.model.set_value(item.doctype, item.name, "reorder_amount", reorder_amount);
        total_reorder += reorder_amount;
    });

    frm.set_value("total", total);
    frm.set_value("total_reorder_value", total_reorder);
}


// ===========================
// Child Table Events
// ===========================

frappe.ui.form.on('Stock Balance Entry', {
    qty: function(frm, cdt, cdn) {
        calculate_row_totals(frm, cdt, cdn);
    },
    
    cost_price: function(frm, cdt, cdn) {
        calculate_row_totals(frm, cdt, cdn);
    },
    
    reorder_level: function(frm, cdt, cdn) {
        calculate_row_totals(frm, cdt, cdn);
    }
});


function calculate_row_totals(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    
    // Calculate amount
    row.amount = (row.qty || 0) * (row.cost_price || 0);
    
    // Calculate reorder qty and amount
    row.reorder_qty = Math.max(0, (row.reorder_level || 0) - (row.qty || 0));
    row.reorder_amount = row.reorder_qty * (row.cost_price || 0);
    
    frm.refresh_field('stock_balance_entry');
}


// ===========================
// Utility Functions
// ===========================

function format_currency(value, currency) {
    return frappe.format(value, {fieldtype: 'Currency', currency: currency});
}