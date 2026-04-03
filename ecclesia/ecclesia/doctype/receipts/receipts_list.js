// -*- coding: utf-8 -*-
// Copyright (c) 2025, Your Company
// Receipts List View Customization - Optimized

frappe.listview_settings['Receipts'] = {
    // Add indicators for status
    get_indicator: function(doc) {
        const status_colors = {
            'Draft': 'red',
            'Pending Approval': 'orange',
            'Approved': 'blue',
            'Verified': 'cyan',
            'Processing': 'yellow',
            'Completed': 'green',
            'Cancelled': 'darkgrey',
            'Rejected': 'red'
        };
        
        return [__(doc.receipt_status || 'Draft'), status_colors[doc.receipt_status || 'Draft'], 'receipt_status,=,' + doc.receipt_status];
    },
    
    // Setup list view
    onload: function(listview) {
        // Add custom buttons
        add_custom_buttons(listview);
        
        // Format list view
        format_list_view(listview);
    },
    
    // Format columns
    formatters: {
        amount_received: function(value, df, doc) {
            if (!value) return '';
            
            let currency = doc.receipt_currency || 'NGN';
            let formatted = format_currency(value, currency);
            
            // Color code based on amount
            let color = 'inherit';
            if (value > 1000000) {
                color = '#2e7d32'; // Green for large receipts
            } else if (value > 500000) {
                color = '#388e3c'; // Medium green
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
            } else if (days_diff === 0) {
                color = '#2e7d32'; // Green for today
            }
            
            return `<span style="color: ${color};">${frappe.datetime.str_to_user(value)}</span>`;
        },
        
        customer_name: function(value, df, doc) {
            if (!value && doc.payer_name) {
                value = doc.payer_name;
            }
            return value || '';
        },
        
        reference_no: function(value) {
            if (!value) return '';
            return `<span style="font-family: monospace; background: #f5f5f5; padding: 2px 6px; border-radius: 3px;">${value}</span>`;
        }
    }
};


// ==================== Custom Buttons ====================

function add_custom_buttons(listview) {
    // Send Customer Acknowledgements Button
    listview.page.add_inner_button(__('Send Customer Acknowledgements'), function() {
        let selected = listview.get_checked_items();
        
        if (selected.length === 0) {
            frappe.msgprint({
                title: __('No Selection'),
                message: __('Please select receipts to send acknowledgements'),
                indicator: 'orange'
            });
            return;
        }
        
        // Filter only submitted receipts
        let submitted_receipts = selected.filter(item => item.docstatus === 1);
        
        if (submitted_receipts.length === 0) {
            frappe.msgprint({
                title: __('No Submitted Receipts'),
                message: __('Please select submitted receipts to send acknowledgements'),
                indicator: 'orange'
            });
            return;
        }
        
        send_bulk_acknowledgements(submitted_receipts);
    }, __('Actions'));
    
    // Receipt Register Button
    listview.page.add_inner_button(__('Receipt Register'), function() {
        frappe.set_route('query-report', 'Receipt Register');
    }, __('Reports'));
}


// ==================== Send Bulk Acknowledgements ====================

function send_bulk_acknowledgements(selected_items) {
    let receipt_names = selected_items.map(item => item.name);
    
    // Show confirmation dialog
    let d = new frappe.ui.Dialog({
        title: __('Send Customer Acknowledgements'),
        fields: [
            {
                fieldname: 'preview_section',
                fieldtype: 'Section Break',
                label: __('Preview')
            },
            {
                fieldname: 'preview_html',
                fieldtype: 'HTML'
            },
            {
                fieldname: 'email_section',
                fieldtype: 'Section Break',
                label: __('Email Settings')
            },
            {
                fieldname: 'email_subject',
                label: __('Email Subject'),
                fieldtype: 'Data',
                default: 'Payment Receipt Confirmation',
                reqd: 1
            },
            {
                fieldname: 'include_pdf',
                label: __('Attach Receipt PDF'),
                fieldtype: 'Check',
                default: 1
            },
            {
                fieldname: 'custom_message',
                label: __('Additional Message'),
                fieldtype: 'Small Text',
                description: __('Optional message to include in the email')
            }
        ],
        primary_action_label: __('Send Acknowledgements'),
        primary_action: function(values) {
            frappe.call({
                method: 'general.general_biz_apps.doctype.receipts.receipts.send_bulk_acknowledgements',
                args: {
                    receipt_names: receipt_names,
                    email_subject: values.email_subject,
                    include_pdf: values.include_pdf,
                    custom_message: values.custom_message
                },
                freeze: true,
                freeze_message: __('Sending acknowledgements to {0} customers...', [receipt_names.length]),
                callback: function(r) {
                    if (r.message) {
                        let result = r.message;
                        
                        let message = `
                            <div style="padding: 15px;">
                                <h4 style="color: #2e7d32; margin-bottom: 15px;">
                                    <i class="fa fa-check-circle"></i> Acknowledgements Sent Successfully
                                </h4>
                                <table style="width: 100%; border-collapse: collapse;">
                                    <tr>
                                        <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Total Receipts:</strong></td>
                                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">${receipt_names.length}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Emails Sent:</strong></td>
                                        <td style="padding: 8px; border-bottom: 1px solid #ddd; color: #2e7d32; font-weight: bold;">
                                            ${result.success_count || receipt_names.length}
                                        </td>
                                    </tr>
                                    ${result.failed_count ? `
                                    <tr>
                                        <td style="padding: 8px;"><strong>Failed:</strong></td>
                                        <td style="padding: 8px; color: #d32f2f; font-weight: bold;">
                                            ${result.failed_count}
                                        </td>
                                    </tr>
                                    ` : ''}
                                </table>
                            </div>
                        `;
                        
                        frappe.msgprint({
                            title: __('Acknowledgement Results'),
                            message: message,
                            indicator: result.failed_count > 0 ? 'orange' : 'green'
                        });
                        
                        d.hide();
                        cur_list.refresh();
                    }
                },
                error: function(r) {
                    frappe.msgprint({
                        title: __('Error'),
                        message: __('Failed to send acknowledgements. Please try again.'),
                        indicator: 'red'
                    });
                }
            });
        },
        secondary_action_label: __('Cancel')
    });
    
    // Generate preview
    let preview_html = `
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; padding: 20px; border-radius: 8px; margin-bottom: 15px;">
            <h4 style="margin: 0; color: white;">Selected Receipts</h4>
            <div style="font-size: 32px; font-weight: bold; margin-top: 10px;">
                ${receipt_names.length}
            </div>
            <div style="margin-top: 10px; opacity: 0.9;">
                Acknowledgement emails will be sent to customers
            </div>
        </div>
        
        <div style="max-height: 300px; overflow-y: auto; border: 1px solid #ddd; border-radius: 4px; padding: 10px;">
            <table style="width: 100%; font-size: 12px;">
                <thead>
                    <tr style="background: #f5f5f5;">
                        <th style="padding: 8px; text-align: left;">Receipt No</th>
                        <th style="padding: 8px; text-align: left;">Customer</th>
                        <th style="padding: 8px; text-align: right;">Amount</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    selected_items.forEach(function(item, index) {
        let bg = index % 2 === 0 ? '#ffffff' : '#f9f9f9';
        preview_html += `
            <tr style="background: ${bg};">
                <td style="padding: 8px;">${item.name}</td>
                <td style="padding: 8px;">${item.customer_name || item.payer_name || 'N/A'}</td>
                <td style="padding: 8px; text-align: right; font-weight: bold;">
                    ${format_currency(item.amount_received || item.local_currency_amount, item.receipt_currency)}
                </td>
            </tr>
        `;
    });
    
    preview_html += `
                </tbody>
            </table>
        </div>
    `;
    
    d.fields_dict.preview_html.$wrapper.html(preview_html);
    d.show();
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
            
            .receipt-large {
                border-left: 3px solid #2e7d32 !important;
                background-color: #f1f8f4 !important;
            }
            
            .receipt-approved {
                border-left: 3px solid #1976d2 !important;
            }
            
            .receipt-completed {
                border-left: 3px solid #388e3c !important;
                background-color: #e8f5e9 !important;
            }
            
            .receipt-cancelled {
                background-color: #fafafa !important;
                opacity: 0.7;
            }
            
            .receipt-today {
                background-color: #fff3e0 !important;
                border-left: 3px solid #ff9800 !important;
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
            format_receipt_row($(e.target));
        }
    });
}


function format_receipt_row($row) {
    let data = $row.data();
    
    if (!data) return;
    
    // Add class based on status
    if (data.receipt_status === 'Completed') {
        $row.addClass('receipt-completed');
    } else if (data.receipt_status === 'Cancelled') {
        $row.addClass('receipt-cancelled');
    } else if (data.receipt_status === 'Approved' || data.receipt_status === 'Verified') {
        $row.addClass('receipt-approved');
    }
    
    // Mark large receipts
    if (data.amount_received && data.amount_received > 1000000) {
        $row.addClass('receipt-large');
    }
    
    // Mark today's receipts
    if (data.transaction_date === frappe.datetime.get_today()) {
        $row.addClass('receipt-today');
    }
    
    // Add tooltips
    let tooltip = `${data.trans_type || 'Receipt'} - ${data.reference_no || 'No Reference'}`;
    if (data.customer_name) {
        tooltip += ` - ${data.customer_name}`;
    }
    $row.attr('title', tooltip);
}


// ==================== Helper Functions ====================

function format_currency(value, currency) {
    if (!value) return '0.00';
    
    currency = currency || 'NGN';
    
    try {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency,
            minimumFractionDigits: 2
        }).format(value);
    } catch(e) {
        // Fallback if currency is not recognized
        return currency + ' ' + parseFloat(value).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    }
}