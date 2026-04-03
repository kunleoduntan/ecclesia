// -*- coding: utf-8 -*-
// Copyright (c) 2025, Your Company
// Payments List View Customization

frappe.listview_settings['Payments'] = {
    // Add indicators for status
    get_indicator: function(doc) {
        const status_colors = {
            'Draft': 'red',
            'Pending Approval': 'orange',
            'Approved': 'blue',
            'Processing': 'yellow',
            'Completed': 'green',
            'Cancelled': 'darkgrey',
            'Rejected': 'red'
        };
        
        return [__(doc.payment_status || 'Draft'), status_colors[doc.payment_status || 'Draft'], 'payment_status,=,' + doc.payment_status];
    },
    
    // Color-code rows based on conditions
    onload: function(listview) {
        // Add custom buttons
        add_custom_list_buttons(listview);
        
        // Add custom filters
        add_custom_filters(listview);
        
        // Format list view
        format_list_view(listview);
        
        // Add bulk actions
        setup_bulk_actions(listview);
    },
    
    // Format columns
    formatters: {
        amount_paid: function(value, df, doc) {
            if (!value) return '';
            
            let currency = doc.payment_currency || 'NGN';
            let formatted = format_currency(value, currency);
            
            // Color code based on amount
            let color = 'inherit';
            if (value > 1000000) {
                color = '#d32f2f'; // Red for large amounts
            } else if (value > 500000) {
                color = '#f57c00'; // Orange for medium amounts
            }
            
            return `<span style="color: ${color}; font-weight: bold;">${formatted}</span>`;
        },
        
        transaction_date: function(value) {
            if (!value) return '';
            
            let today = frappe.datetime.get_today();
            let days_diff = frappe.datetime.get_day_diff(today, value);
            
            let color = 'inherit';
            if (days_diff < 0) {
                color = '#1976d2'; // Blue for future dates
            } else if (days_diff > 30) {
                color = '#757575'; // Grey for old dates
            }
            
            return `<span style="color: ${color};">${frappe.datetime.str_to_user(value)}</span>`;
        },
        
        payee_name: function(value, df, doc) {
            if (!value && doc.supplier_name) {
                value = doc.supplier_name;
            }
            return value || '';
        }
    },
    
    // Quick edit fields
    hide_name_column: false,
    
    // Refresh on specific events
    refresh: function(listview) {
        // Refresh list view when needed
    }
};


// ==================== Custom List Buttons ====================

function add_custom_list_buttons(listview) {
    // Bulk Approve Button
    listview.page.add_inner_button(__('Bulk Approve'), function() {
        let selected = listview.get_checked_items();
        
        if (selected.length === 0) {
            frappe.msgprint(__('Please select payments to approve'));
            return;
        }
        
        frappe.confirm(
            __('Are you sure you want to approve {0} payments?', [selected.length]),
            function() {
                bulk_approve_payments(selected);
            }
        );
    }, __('Actions'));
    
    // Bulk Submit Button
    listview.page.add_inner_button(__('Bulk Submit'), function() {
        let selected = listview.get_checked_items();
        
        if (selected.length === 0) {
            frappe.msgprint(__('Please select payments to submit'));
            return;
        }
        
        frappe.confirm(
            __('Are you sure you want to submit {0} payments?', [selected.length]),
            function() {
                bulk_submit_payments(selected);
            }
        );
    }, __('Actions'));
    
    // Export Selected Button
    listview.page.add_inner_button(__('Export Selected'), function() {
        let selected = listview.get_checked_items();
        
        if (selected.length === 0) {
            frappe.msgprint(__('Please select payments to export'));
            return;
        }
        
        export_selected_payments(selected);
    }, __('Actions'));
    
    // Payment Analytics Button
    listview.page.add_inner_button(__('Analytics Dashboard'), function() {
        show_analytics_dashboard();
    }, __('Reports'));
    
    // Payment Register Button
    listview.page.add_inner_button(__('Payment Register'), function() {
        frappe.set_route('query-report', 'Payment Register');
    }, __('Reports'));
}


// ==================== Custom Filters ====================

function add_custom_filters(listview) {
    // Add date range filter
    listview.page.add_field({
        fieldname: 'date_range',
        label: __('Date Range'),
        fieldtype: 'Select',
        options: [
            '',
            'Today',
            'Yesterday',
            'This Week',
            'Last Week',
            'This Month',
            'Last Month',
            'This Quarter',
            'Last Quarter',
            'This Year',
            'Custom'
        ],
        change: function() {
            apply_date_filter(this.get_value(), listview);
        }
    });
    
    // Add amount range filter
    listview.page.add_field({
        fieldname: 'amount_range',
        label: __('Amount Range'),
        fieldtype: 'Select',
        options: [
            '',
            'Less than 100,000',
            '100,000 - 500,000',
            '500,000 - 1,000,000',
            'Above 1,000,000'
        ],
        change: function() {
            apply_amount_filter(this.get_value(), listview);
        }
    });
}


// ==================== List View Formatting ====================

function format_list_view(listview) {
    // Add custom CSS
    $('<style>')
        .prop('type', 'text/css')
        .html(`
            .list-row-head {
                background-color: #f5f7fa;
                font-weight: 600;
            }
            
            .payment-urgent {
                border-left: 3px solid #d32f2f !important;
                background-color: #ffebee !important;
            }
            
            .payment-approved {
                border-left: 3px solid #1976d2 !important;
            }
            
            .payment-completed {
                border-left: 3px solid #388e3c !important;
                background-color: #f1f8f4 !important;
            }
            
            .payment-cancelled {
                background-color: #fafafa !important;
                opacity: 0.7;
            }
            
            .list-row-container:hover {
                transform: translateY(-2px);
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                transition: all 0.2s ease;
            }
        `)
        .appendTo('head');
    
    // Apply row formatting after render
    listview.$result.on('DOMNodeInserted', function(e) {
        if ($(e.target).hasClass('list-row-container')) {
            format_payment_row($(e.target));
        }
    });
}


function format_payment_row($row) {
    let data = $row.data();
    
    if (!data) return;
    
    // Add class based on status
    if (data.payment_status === 'Completed') {
        $row.addClass('payment-completed');
    } else if (data.payment_status === 'Cancelled') {
        $row.addClass('payment-cancelled');
    } else if (data.payment_status === 'Approved') {
        $row.addClass('payment-approved');
    }
    
    // Mark urgent payments (large amounts)
    if (data.amount_paid && data.amount_paid > 1000000) {
        $row.addClass('payment-urgent');
    }
    
    // Add tooltips
    $row.attr('title', `${data.trans_type || 'Payment'} - ${data.reference_no || 'No Reference'}`);
}


// ==================== Bulk Actions ====================

function setup_bulk_actions(listview) {
    // Custom bulk action menu items
    listview.page.add_actions_menu_item(__('Send Notifications'), function() {
        let selected = listview.get_checked_items();
        
        if (selected.length === 0) {
            frappe.msgprint(__('Please select payments'));
            return;
        }
        
        send_bulk_notifications(selected);
    }, true);
    
    listview.page.add_actions_menu_item(__('Generate Reports'), function() {
        let selected = listview.get_checked_items();
        
        if (selected.length === 0) {
            frappe.msgprint(__('Please select payments'));
            return;
        }
        
        generate_bulk_reports(selected);
    }, true);
}


function bulk_approve_payments(selected_items) {
    let payment_names = selected_items.map(item => item.name);
    
    frappe.call({
        method: 'general.general_biz_apps.doctype.payments.payment_utils.BatchPaymentProcessor.bulk_approve',
        args: {
            payment_names: payment_names,
            user: frappe.session.user
        },
        freeze: true,
        freeze_message: __('Approving payments...'),
        callback: function(r) {
            if (r.message) {
                let success_count = r.message.filter(x => x.status === 'Approved').length;
                
                frappe.show_alert({
                    message: __('Approved {0} out of {1} payments', [success_count, payment_names.length]),
                    indicator: 'green'
                }, 5);
                
                cur_list.refresh();
            }
        }
    });
}


function bulk_submit_payments(selected_items) {
    let payment_names = selected_items.map(item => item.name);
    
    frappe.call({
        method: 'general.general_biz_apps.doctype.payments.payment_utils.batch_process_payments',
        args: {
            payment_names: payment_names
        },
        freeze: true,
        freeze_message: __('Submitting payments...'),
        callback: function(r) {
            if (r.message) {
                let success_count = r.message.filter(x => x.status === 'Success').length;
                let error_count = r.message.filter(x => x.status === 'Error').length;
                
                let message = __('Submitted {0} payments', [success_count]);
                if (error_count > 0) {
                    message += __('<br>{0} payments failed', [error_count]);
                }
                
                frappe.msgprint({
                    title: __('Batch Submission Results'),
                    message: message,
                    indicator: error_count > 0 ? 'orange' : 'green'
                });
                
                cur_list.refresh();
            }
        }
    });
}


function export_selected_payments(selected_items) {
    let payment_names = selected_items.map(item => item.name);
    
    frappe.call({
        method: 'general.general_biz_apps.doctype.payments.payment_utils.export_payments_report',
        args: {
            filters: {
                name: ['in', payment_names]
            }
        },
        callback: function(r) {
            frappe.show_alert({
                message: __('Export started. Download will begin shortly.'),
                indicator: 'green'
            }, 3);
        }
    });
}


function send_bulk_notifications(selected_items) {
    let d = new frappe.ui.Dialog({
        title: __('Send Notifications'),
        fields: [
            {
                fieldname: 'notification_type',
                label: __('Notification Type'),
                fieldtype: 'Select',
                options: ['Confirmation', 'Approval Request', 'Reminder'],
                reqd: 1
            },
            {
                fieldname: 'custom_message',
                label: __('Custom Message'),
                fieldtype: 'Text',
                description: __('Optional custom message to include')
            }
        ],
        primary_action_label: __('Send'),
        primary_action: function(values) {
            let payment_names = selected_items.map(item => item.name);
            
            frappe.call({
                method: 'general.general_biz_apps.doctype.payments.payment_utils.send_bulk_notifications',
                args: {
                    payment_names: payment_names,
                    notification_type: values.notification_type,
                    custom_message: values.custom_message
                },
                callback: function(r) {
                    frappe.show_alert({
                        message: __('Notifications sent successfully'),
                        indicator: 'green'
                    }, 5);
                    
                    d.hide();
                }
            });
        }
    });
    
    d.show();
}


function generate_bulk_reports(selected_items) {
    let payment_names = selected_items.map(item => item.name);
    
    let d = new frappe.ui.Dialog({
        title: __('Generate Reports'),
        fields: [
            {
                fieldname: 'report_type',
                label: __('Report Type'),
                fieldtype: 'Select',
                options: ['Payment Vouchers', 'Summary Report', 'WHT Certificates'],
                reqd: 1
            },
            {
                fieldname: 'format',
                label: __('Format'),
                fieldtype: 'Select',
                options: ['PDF', 'Excel'],
                default: 'PDF'
            }
        ],
        primary_action_label: __('Generate'),
        primary_action: function(values) {
            frappe.show_alert(__('Generating reports...'), 3);
            
            // Generate reports for each payment
            payment_names.forEach(function(name) {
                if (values.format === 'PDF') {
                    frappe.call({
                        method: 'general.general_biz_apps.doctype.payments.payment_utils.generate_payment_voucher_pdf',
                        args: {payment_name: name},
                        callback: function(r) {
                            if (r.message) {
                                // Download PDF
                                let w = window.open(
                                    frappe.urllib.get_full_url(
                                        `/api/method/frappe.utils.print_format.download_pdf?
                                        doctype=Payments&name=${name}&format=Standard&no_letterhead=0`
                                    )
                                );
                                if (!w) {
                                    frappe.msgprint(__('Please enable pop-ups'));
                                }
                            }
                        }
                    });
                }
            });
            
            d.hide();
        }
    });
    
    d.show();
}


// ==================== Filter Helpers ====================

function apply_date_filter(range, listview) {
    let from_date, to_date;
    let today = frappe.datetime.get_today();
    
    switch(range) {
        case 'Today':
            from_date = to_date = today;
            break;
        case 'Yesterday':
            from_date = to_date = frappe.datetime.add_days(today, -1);
            break;
        case 'This Week':
            from_date = frappe.datetime.week_start();
            to_date = frappe.datetime.week_end();
            break;
        case 'Last Week':
            from_date = frappe.datetime.add_days(frappe.datetime.week_start(), -7);
            to_date = frappe.datetime.add_days(frappe.datetime.week_end(), -7);
            break;
        case 'This Month':
            from_date = frappe.datetime.month_start();
            to_date = frappe.datetime.month_end();
            break;
        case 'Last Month':
            from_date = frappe.datetime.add_months(frappe.datetime.month_start(), -1);
            to_date = frappe.datetime.add_days(frappe.datetime.month_start(), -1);
            break;
        default:
            listview.filter_area.clear();
            return;
    }
    
    listview.filter_area.add([[
        'Payments',
        'transaction_date',
        'between',
        [from_date, to_date]
    ]]);
}


function apply_amount_filter(range, listview) {
    let filters = [];
    
    switch(range) {
        case 'Less than 100,000':
            filters = [['Payments', 'amount_paid', '<', 100000]];
            break;
        case '100,000 - 500,000':
            filters = [
                ['Payments', 'amount_paid', '>=', 100000],
                ['Payments', 'amount_paid', '<=', 500000]
            ];
            break;
        case '500,000 - 1,000,000':
            filters = [
                ['Payments', 'amount_paid', '>=', 500000],
                ['Payments', 'amount_paid', '<=', 1000000]
            ];
            break;
        case 'Above 1,000,000':
            filters = [['Payments', 'amount_paid', '>', 1000000]];
            break;
        default:
            listview.filter_area.clear();
            return;
    }
    
    listview.filter_area.add(filters);
}


// ==================== Analytics Dashboard ====================

function show_analytics_dashboard() {
    let d = new frappe.ui.Dialog({
        title: __('Payment Analytics'),
        size: 'extra-large',
        fields: [
            {
                fieldname: 'company',
                label: __('Company'),
                fieldtype: 'Link',
                options: 'Company',
                default: frappe.defaults.get_user_default('Company'),
                reqd: 1,
                onchange: function() {
                    load_analytics(d);
                }
            },
            {
                fieldname: 'from_date',
                label: __('From Date'),
                fieldtype: 'Date',
                default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
                reqd: 1,
                onchange: function() {
                    load_analytics(d);
                }
            },
            {
                fieldname: 'to_date',
                label: __('To Date'),
                fieldtype: 'Date',
                default: frappe.datetime.get_today(),
                reqd: 1,
                onchange: function() {
                    load_analytics(d);
                }
            },
            {
                fieldname: 'section_break',
                fieldtype: 'Section Break'
            },
            {
                fieldname: 'analytics_html',
                fieldtype: 'HTML'
            }
        ]
    });
    
    d.show();
    load_analytics(d);
}


function load_analytics(dialog) {
    let values = dialog.get_values();
    
    if (!values.company || !values.from_date || !values.to_date) {
        return;
    }
    
    frappe.call({
        method: 'general.general_biz_apps.doctype.payments.payment_utils.get_payment_dashboard_data',
        args: values,
        callback: function(r) {
            if (r.message) {
                render_analytics(dialog, r.message);
            }
        }
    });
}


function render_analytics(dialog, data) {
    let html = `
        <div class="row">
            <div class="col-sm-6">
                <h4>Payment Summary</h4>
                <table class="table table-bordered">
                    <thead>
                        <tr>
                            <th>Transaction Type</th>
                            <th>Count</th>
                            <th>Total Amount</th>
                        </tr>
                    </thead>
                    <tbody>
    `;
    
    data.forEach(function(row) {
        html += `
            <tr>
                <td>${row.trans_type}</td>
                <td>${row.count}</td>
                <td>${format_currency(row.total_amount, row.payment_currency)}</td>
            </tr>
        `;
    });
    
    html += `
                    </tbody>
                </table>
            </div>
            <div class="col-sm-6">
                <h4>Status Distribution</h4>
                <div id="status_chart"></div>
            </div>
        </div>
    `;
    
    dialog.fields_dict.analytics_html.$wrapper.html(html);
}