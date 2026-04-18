// ============================================================================
// Receipt Register Report - Optimized
// Path: general_biz_apps/report/receipt_register/receipt_register.js
// ============================================================================

frappe.query_reports["Receipt Register"] = {
    "filters": [
        // Primary Filters
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 1
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        
        // Customer & Transaction Filters
        {
            "fieldname": "customer_id",
            "label": __("Customer"),
            "fieldtype": "Link",
            "options": "Customer",
            "get_query": function() {
                return {
                    filters: {
                        "disabled": 0
                    }
                };
            }
        },
        {
            "fieldname": "trans_type",
            "label": __("Transaction Type"),
            "fieldtype": "Select",
            "options": "\nCustomer Receipt\nReceive from One-Off\nRevenue Receipt\nCustomer Refund\nTransfer In"
        },
        
        // Payment Details
        {
            "fieldname": "mode_of_payment",
            "label": __("Payment Mode"),
            "fieldtype": "Link",
            "options": "Mode of Payment"
        },
        {
            "fieldname": "remittance_bank",
            "label": __("Bank Account"),
            "fieldtype": "Link",
            "options": "Bank Account",
            "get_query": function() {
                let company = frappe.query_report.get_filter_value('company');
                return {
                    filters: {
                        "company": company,
                        "is_company_account": 1
                    }
                };
            }
        },
        
        // Status & Currency
        {
            "fieldname": "receipt_status",
            "label": __("Status"),
            "fieldtype": "Select",
            "options": "\nDraft\nPending Approval\nApproved\nProcessing\nCompleted\nCancelled\nRejected"
        },
        {
            "fieldname": "receipt_currency",
            "label": __("Currency"),
            "fieldtype": "Link",
            "options": "Currency"
        },
        
        // Amount Range Filter
        {
            "fieldname": "min_amount",
            "label": __("Min Amount"),
            "fieldtype": "Currency"
        },
        {
            "fieldname": "max_amount",
            "label": __("Max Amount"),
            "fieldtype": "Currency"
        }
    ],
    
    // Enhanced formatter with better styling
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        if (!data) return value;
        
        // Status formatting with badges
        if (column.fieldname == "receipt_status") {
            const status_styles = {
                "Completed": "background: #4caf50; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;",
                "Approved": "background: #2196f3; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;",
                "Processing": "background: #ff9800; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;",
                "Pending Approval": "background: #ffc107; color: #333; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;",
                "Cancelled": "background: #f44336; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;",
                "Rejected": "background: #e91e63; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;",
                "Draft": "background: #9e9e9e; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;"
            };
            
            let style = status_styles[data.receipt_status] || "";
            if (style) {
                value = `<span style="${style}">${data.receipt_status}</span>`;
            }
        }
        
        // Amount formatting with color coding
        if (column.fieldname == "amount_received" || column.fieldname == "local_currency_amount") {
            let amount = data.amount_received || data.local_currency_amount || 0;
            let color = amount > 1000000 ? "#2e7d32" : amount > 500000 ? "#388e3c" : "#666";
            value = `<span style="color: ${color}; font-weight: bold;">${value}</span>`;
        }
        
        // Transaction Type with icons
        if (column.fieldname == "trans_type") {
            const icons = {
                "Customer Receipt": "💰",
                "Revenue Receipt": "📈",
                "Customer Refund": "↩️",
                "Transfer In": "🔄"
            };
            let icon = icons[data.trans_type] || "📄";
            value = `<span title="${data.trans_type}">${icon} ${value}</span>`;
        }
        
        // Reference number with copy button
        if (column.fieldname == "reference_no") {
            value = `<span style="font-family: monospace; background: #f5f5f5; padding: 2px 6px; border-radius: 3px; cursor: pointer;" 
                     onclick="navigator.clipboard.writeText('${data.reference_no}'); frappe.show_alert('Copied!', 2);" 
                     title="Click to copy">${value}</span>`;
        }
        
        // Customer name with link
        if (column.fieldname == "customer_name" && data.customer_id) {
            value = `<a href="/app/customer/${data.customer_id}" target="_blank" style="color: #2196f3; text-decoration: none;">
                     ${value}</a>`;
        }
        
        return value;
    },
    
    // Report initialization
    "onload": function(report) {
        // Add custom buttons
        add_custom_buttons(report);
        
        // Add summary cards
        add_summary_section(report);
        
        // Style enhancements
        apply_report_styling();
    },
    
    // After data loads
    "after_datatable_render": function(datatable_obj) {
        // Add row hover effects
        $(datatable_obj.wrapper).find('.dt-row').hover(
            function() {
                $(this).css({
                    'background-color': '#f8f9fa',
                    'transform': 'scale(1.01)',
                    'box-shadow': '0 2px 4px rgba(0,0,0,0.1)',
                    'transition': 'all 0.2s ease'
                });
            },
            function() {
                $(this).css({
                    'background-color': '',
                    'transform': '',
                    'box-shadow': ''
                });
            }
        );
    }
};


// ==================== Custom Buttons ====================

function add_custom_buttons(report) {
    // Export to Excel
    report.page.add_inner_button(__("Export to Excel"), function() {
        let filters = report.get_filter_values();
        
        frappe.call({
            method: "ecclesia.ecclesia.report.receipt_register.receipt_register.export_to_excel",
            args: {
                filters: filters
            },
            callback: function(r) {
                if (r.message) {
                    window.open(r.message);
                    frappe.show_alert({
                        message: __("Excel export ready for download"),
                        indicator: "green"
                    }, 3);
                }
            }
        });
    }, __("Export"));
    
    // Print Report
    report.page.add_inner_button(__("Print Report"), function() {
        print_receipt_register(report);
    }, __("Export"));
    
    // Send Email
    report.page.add_inner_button(__("Email Report"), function() {
        email_receipt_register(report);
    }, __("Actions"));
    
    // Refresh Summary
    report.page.add_inner_button(__("Refresh Summary"), function() {
        add_summary_section(report);
    }, __("Actions"));
}


// ==================== Summary Section ====================

function add_summary_section(report) {
    let data = report.data;
    
    if (!data || data.length === 0) {
        return;
    }
    
    // Calculate summary
    let summary = {
        total_receipts: data.length,
        total_amount: 0,
        completed_count: 0,
        pending_count: 0,
        cancelled_count: 0,
        customers: new Set()
    };
    
    data.forEach(row => {
        summary.total_amount += (row.amount_received || row.local_currency_amount || 0);
        
        if (row.receipt_status === "Completed") summary.completed_count++;
        if (row.receipt_status === "Pending Approval") summary.pending_count++;
        if (row.receipt_status === "Cancelled") summary.cancelled_count++;
        
        if (row.customer_id) summary.customers.add(row.customer_id);
    });
    
    let currency = frappe.query_report.get_filter_value('receipt_currency') || 
                   frappe.defaults.get_user_default("currency") || 'NGN';
    
    // Generate summary HTML
    let summary_html = `
        <div class="report-summary" style="margin: 15px 0; padding: 0;">
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                
                <div class="summary-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                     color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <div style="font-size: 12px; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px;">
                        Total Receipts
                    </div>
                    <div style="font-size: 32px; font-weight: bold; margin-top: 5px;">
                        ${summary.total_receipts}
                    </div>
                </div>
                
                <div class="summary-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                     color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <div style="font-size: 12px; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px;">
                        Total Amount
                    </div>
                    <div style="font-size: 28px; font-weight: bold; margin-top: 5px;">
                        ${format_currency(summary.total_amount, currency)}
                    </div>
                </div>
                
                <div class="summary-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); 
                     color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <div style="font-size: 12px; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px;">
                        Completed
                    </div>
                    <div style="font-size: 32px; font-weight: bold; margin-top: 5px;">
                        ${summary.completed_count}
                    </div>
                </div>
                
                <div class="summary-card" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); 
                     color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <div style="font-size: 12px; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px;">
                        Unique Customers
                    </div>
                    <div style="font-size: 32px; font-weight: bold; margin-top: 5px;">
                        ${summary.customers.size}
                    </div>
                </div>
                
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-top: 15px;">
                
                <div style="background: white; border: 2px solid #4caf50; padding: 15px; border-radius: 8px; text-align: center;">
                    <div style="color: #666; font-size: 11px; text-transform: uppercase; margin-bottom: 5px;">
                        Completed
                    </div>
                    <div style="color: #4caf50; font-size: 24px; font-weight: bold;">
                        ${summary.completed_count}
                    </div>
                </div>
                
                <div style="background: white; border: 2px solid #ff9800; padding: 15px; border-radius: 8px; text-align: center;">
                    <div style="color: #666; font-size: 11px; text-transform: uppercase; margin-bottom: 5px;">
                        Pending
                    </div>
                    <div style="color: #ff9800; font-size: 24px; font-weight: bold;">
                        ${summary.pending_count}
                    </div>
                </div>
                
                <div style="background: white; border: 2px solid #f44336; padding: 15px; border-radius: 8px; text-align: center;">
                    <div style="color: #666; font-size: 11px; text-transform: uppercase; margin-bottom: 5px;">
                        Cancelled
                    </div>
                    <div style="color: #f44336; font-size: 24px; font-weight: bold;">
                        ${summary.cancelled_count}
                    </div>
                </div>
                
            </div>
        </div>
    `;
    
    // Insert summary before report
    $('.report-summary').remove();
    $(report.wrapper).find('.frappe-control[data-fieldname="from_date"]').closest('.report-filters').after(summary_html);
}


// ==================== Print Report ====================

function print_receipt_register(report) {
    let filters = report.get_filter_values();
    let data = report.data;
    
    if (!data || data.length === 0) {
        frappe.msgprint(__("No data to print"));
        return;
    }
    
    let print_html = generate_print_html(data, filters);
    
    let print_window = window.open('', '_blank');
    print_window.document.write(print_html);
    print_window.document.close();
    
    setTimeout(function() {
        print_window.print();
    }, 500);
}


function generate_print_html(data, filters) {
    let total = 0;
    data.forEach(row => {
        total += (row.amount_received || row.local_currency_amount || 0);
    });
    
    let rows_html = '';
    data.forEach((row, index) => {
        rows_html += `
            <tr style="${index % 2 === 0 ? 'background: #f9f9f9;' : ''}">
                <td style="padding: 8px; border: 1px solid #ddd;">${row.transaction_date || ''}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">${row.name || ''}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">${row.customer_name || row.payer_name || ''}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">${row.reference_no || ''}</td>
                <td style="padding: 8px; border: 1px solid #ddd; text-align: right; font-weight: bold;">
                    ${format_currency(row.amount_received || row.local_currency_amount || 0)}
                </td>
                <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">${row.receipt_status || ''}</td>
            </tr>
        `;
    });
    
    return `
        <!DOCTYPE html>
        <html>
        <head>
            <title>Receipt Register</title>
            <style>
                body { font-family: Arial, sans-serif; padding: 20px; }
                .header { text-align: center; margin-bottom: 30px; }
                .header h1 { margin: 0; color: #333; }
                .filters { background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                table { width: 100%; border-collapse: collapse; }
                th { background: #2196f3; color: white; padding: 12px; text-align: left; border: 1px solid #1976d2; }
                @media print {
                    .no-print { display: none; }
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Receipt Register</h1>
                <div style="color: #666;">Generated on ${frappe.datetime.now_datetime()}</div>
            </div>
            
            <div class="filters">
                <strong>Filters:</strong><br>
                From: ${filters.from_date || 'N/A'} | To: ${filters.to_date || 'N/A'} | 
                Company: ${filters.company || 'All'}
            </div>
            
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Receipt No</th>
                        <th>Customer</th>
                        <th>Reference</th>
                        <th>Amount</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows_html}
                </tbody>
                <tfoot>
                    <tr style="background: #e3f2fd; font-weight: bold;">
                        <td colspan="4" style="padding: 12px; border: 1px solid #ddd;">TOTAL</td>
                        <td style="padding: 12px; border: 1px solid #ddd; text-align: right;">
                            ${format_currency(total)}
                        </td>
                        <td style="padding: 12px; border: 1px solid #ddd;">${data.length} Receipts</td>
                    </tr>
                </tfoot>
            </table>
        </body>
        </html>
    `;
}


// ==================== Email Report ====================

function email_receipt_register(report) {
    let d = new frappe.ui.Dialog({
        title: __("Email Receipt Register"),
        fields: [
            {
                fieldname: "recipients",
                label: __("Recipients"),
                fieldtype: "Small Text",
                reqd: 1,
                description: __("Comma separated email addresses")
            },
            {
                fieldname: "subject",
                label: __("Subject"),
                fieldtype: "Data",
                default: `Receipt Register - ${frappe.datetime.get_today()}`,
                reqd: 1
            },
            {
                fieldname: "message",
                label: __("Message"),
                fieldtype: "Text Editor",
                default: "Please find attached the Receipt Register report."
            },
            {
                fieldname: "attach_excel",
                label: __("Attach Excel File"),
                fieldtype: "Check",
                default: 1
            }
        ],
        primary_action_label: __("Send Email"),
        primary_action: function(values) {
            let filters = report.get_filter_values();
            
            frappe.call({
                method: "ecclesia.ecclesia.report.receipt_register.receipt_register.send_email_report",
                args: {
                    filters: filters,
                    recipients: values.recipients,
                    subject: values.subject,
                    message: values.message,
                    attach_excel: values.attach_excel
                },
                freeze: true,
                freeze_message: __("Sending email..."),
                callback: function(r) {
                    frappe.show_alert({
                        message: __("Email sent successfully"),
                        indicator: "green"
                    }, 5);
                    d.hide();
                }
            });
        }
    });
    
    d.show();
}


// ==================== Styling ====================

function apply_report_styling() {
    // Add custom CSS for better report appearance
    if (!$('#receipt-register-styles').length) {
        $('<style id="receipt-register-styles">')
            .html(`
                .report-wrapper .dt-scrollable {
                    border-radius: 8px;
                    overflow: hidden;
                }
                
                .report-wrapper .dt-header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
                    color: white !important;
                }
                
                .report-wrapper .dt-cell--header {
                    color: white !important;
                    font-weight: 600 !important;
                    text-transform: uppercase !important;
                    font-size: 11px !important;
                    letter-spacing: 0.5px !important;
                }
                
                .summary-card {
                    cursor: pointer;
                    transition: transform 0.2s ease, box-shadow 0.2s ease;
                }
                
                .summary-card:hover {
                    transform: translateY(-5px);
                    box-shadow: 0 8px 12px rgba(0,0,0,0.2) !important;
                }
                
                .report-wrapper .page-title {
                    color: #2196f3;
                    font-size: 24px;
                    font-weight: bold;
                }
            `)
            .appendTo('head');
    }
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
        return currency + ' ' + parseFloat(value).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    }
}