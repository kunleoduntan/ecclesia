

frappe.ui.form.on('Receipts', {
    refresh: function(frm) {
        // Delay styling to ensure DOM is ready
        setTimeout(function() {
            apply_zebra_striping(frm);
            style_buttons(frm);
            apply_field_styling(frm);
        }, 300);
        
        // Set read-only properties
        frm.set_df_property('amount_in_words', 'read_only', 1);
        
        // Add custom action button for sending receipt email
        if (frm.doc.docstatus === 1 && frm.doc.customer_id) {
            frm.add_custom_button(__('Send Receipt Email'), function() {
                send_receipt_email(frm);
            }, __('Actions'));
        }
    },
    
    onload: function(frm) {
        // Set queries for accounts (non-group accounts only)
        set_account_queries(frm);
        
        // Set cost center query
        frm.set_query("cost_center", function() {
            return {
                filters: {
                    is_group: 0,
                    company: frm.doc.company
                }
            };
        });
        
        // Initial calculation
        calculate_local_currency_amount(frm);
        
        // Update allocation summary if references exist
        if (frm.doc.receipts_reference && frm.doc.receipts_reference.length > 0) {
            update_allocation_summary(frm);
        }
    },
    
    setup: function(frm) {
        // Initialize form settings
        frm.set_df_property('amount_in_words', 'read_only', 1);
    },
    
    trans_type: function(frm) {
        handle_transaction_type_change(frm);
    },
    
    customer_id: function(frm) {
        // Clear cash customer name when customer selected
        if (frm.doc.customer_id) {
            frm.set_value('payer_name', '');
        }
    },
    
    receipt_currency: function(frm) {
        handle_currency_change(frm);
        calculate_local_currency_amount(frm);
    },
    
    company: function(frm) {
        calculate_local_currency_amount(frm);
    },
    
    amortize: function(frm) {
        handle_amortization_toggle(frm);
    },
    
    frequency: function(frm) {
        calculate_amortization_schedule(frm);
    },
    
    start_date: function(frm) {
        calculate_end_date(frm);
    },
    
    no_of_days: function(frm) {
        calculate_end_date(frm);
        calculate_amortization_schedule(frm);
    },
    
    amount_received: function(frm) {
        calculate_amortization_schedule(frm);
        calculate_local_currency_amount(frm);
    },
    
    amount_received_in_fc: function(frm) {
        calculate_amortization_schedule(frm);
        calculate_local_currency_amount(frm);
    },
    
    exchange_rate: function(frm) {
        calculate_amortization_schedule(frm);
        calculate_local_currency_amount(frm);
    },
    
    account_to_credit: function(frm) {
        // Auto-populate deferred revenue account
        if (frm.doc.amortize && frm.doc.account_to_credit) {
            frm.set_value('deferred_revenue_account', frm.doc.account_to_credit);
        }
    },
    
    get_outstanding_invoices: function(frm) {
        fetch_outstanding_invoices(frm);
    },
    
    ai_smart_allocation: function(frm) {
        run_ai_smart_allocation(frm);
    },
    
    preview_allocation: function(frm) {
        show_preview_allocation(frm);
    },
    
    before_save: function(frm) {
        // Generate amortization schedule
        if (frm.doc.charge_amount && frm.doc.amortize == 1) {
            generate_amortization_schedule(frm);
        }
        
        // Calculate totals
        calculate_all_totals(frm);
    }
});

// Child Table: Receipts Reference (Outstanding Invoices)
frappe.ui.form.on('Receipts Reference', {
    allocated_amount: function(frm, cdt, cdn) {
        calculate_total_outstanding(frm);
        update_allocation_summary(frm);
    },
    
    receipts_reference_add: function(frm, cdt, cdn) {
        update_allocation_summary(frm);
    },
    
    receipts_reference_remove: function(frm, cdt, cdn) {
        calculate_total_outstanding(frm);
        update_allocation_summary(frm);
    }
});

// Child Table: Related Company Receipts
frappe.ui.form.on('Related Company Receipts', {
    party: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.party && row.party_type) {
            fetch_party_name(frm, cdt, cdn, row);
        }
    },
    
    related_company: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        setup_related_company_queries(frm, cdt, cdn, row);
    },
    
    trans_type: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        // Clear party when trans_type changes
        frappe.model.set_value(cdt, cdn, 'party', '');
        frappe.model.set_value(cdt, cdn, 'party_name', '');
        
        setup_related_company_queries(frm, cdt, cdn, row);
    },
    
    amount: function(frm, cdt, cdn) {
        calculate_related_company_total(frm);
    },
    
    related_company_receipts_remove: function(frm, cdt, cdn) {
        calculate_related_company_total(frm);
    },
    
    form_render: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        setup_related_company_queries(frm, cdt, cdn, row);
    }
});

// Child Table: Receipts Item Line (Multi-line)
frappe.ui.form.on('Receipts Item Line', {
    amount: function(frm, cdt, cdn) {
        calculate_multi_line_total(frm);
    },
    
    receipts_item_line_remove: function(frm, cdt, cdn) {
        calculate_multi_line_total(frm);
    }
});

// ===============================================
// UTILITY FUNCTIONS
// ===============================================

function apply_zebra_striping(frm) {
    // Apply zebra striping to all child tables
    const tables = [
        'receipts_reference',
        'related_company_receipts',
        'receipts_item_line',
        'schedule_of_deferred_revenue'
    ];
    
    tables.forEach(table => {
        try {
            if (frm.fields_dict[table] && frm.fields_dict[table].grid && frm.fields_dict[table].grid.wrapper) {
                frm.fields_dict[table].grid.wrapper.find('.grid-row').each(function(i, row) {
                    $(row).css('background-color', i % 2 === 0 ? '#ffffff' : '#f0f8ff');
                });
            }
        } catch(e) {
            console.log('Zebra striping skipped for ' + table);
        }
    });
}

function style_buttons(frm) {
    // Style AI Smart Allocation Button
    try {
        if (frm.fields_dict.ai_smart_allocation && frm.fields_dict.ai_smart_allocation.$input) {
            frm.get_field('ai_smart_allocation').$input.css({
                'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                'color': 'white',
                'font-weight': 'bold',
                'border': 'none',
                'padding': '10px 20px',
                'border-radius': '5px',
                'cursor': 'pointer',
                'font-size': '14px',
                'transition': 'all 0.3s ease',
                'box-shadow': '0 4px 6px rgba(0,0,0,0.1)'
            });
            
            frm.get_field('ai_smart_allocation').$input.hover(
                function() {
                    $(this).css({
                        'transform': 'translateY(-2px)',
                        'box-shadow': '0 6px 8px rgba(0,0,0,0.15)'
                    });
                },
                function() {
                    $(this).css({
                        'transform': 'translateY(0)',
                        'box-shadow': '0 4px 6px rgba(0,0,0,0.1)'
                    });
                }
            );
        }
    } catch(e) {
        console.log('AI Smart Allocation button styling skipped');
    }
    
    // Style Preview Allocation Button
    try {
        if (frm.fields_dict.preview_allocation && frm.fields_dict.preview_allocation.$input) {
            frm.get_field('preview_allocation').$input.css({
                'background': 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                'color': 'white',
                'font-weight': 'bold',
                'border': 'none',
                'padding': '10px 20px',
                'border-radius': '5px',
                'cursor': 'pointer',
                'font-size': '14px',
                'transition': 'all 0.3s ease',
                'box-shadow': '0 4px 6px rgba(0,0,0,0.1)'
            });
            
            frm.get_field('preview_allocation').$input.hover(
                function() {
                    $(this).css({
                        'transform': 'translateY(-2px)',
                        'box-shadow': '0 6px 8px rgba(0,0,0,0.15)'
                    });
                },
                function() {
                    $(this).css({
                        'transform': 'translateY(0)',
                        'box-shadow': '0 4px 6px rgba(0,0,0,0.1)'
                    });
                }
            );
        }
    } catch(e) {
        console.log('Preview Allocation button styling skipped');
    }
    
    // Style Get Outstanding Invoices Button
    try {
        if (frm.fields_dict.get_outstanding_invoices && frm.fields_dict.get_outstanding_invoices.$input) {
            frm.get_field('get_outstanding_invoices').$input.css({
                'background': 'linear-gradient(135deg, #FA8BFF 0%, #2BD2FF 90%)',
                'color': 'white',
                'font-weight': 'bold',
                'border': 'none',
                'padding': '10px 20px',
                'border-radius': '5px',
                'cursor': 'pointer',
                'font-size': '14px',
                'transition': 'all 0.3s ease',
                'box-shadow': '0 4px 6px rgba(0,0,0,0.1)'
            });
            
            frm.get_field('get_outstanding_invoices').$input.hover(
                function() {
                    $(this).css({
                        'transform': 'translateY(-2px)',
                        'box-shadow': '0 6px 8px rgba(0,0,0,0.15)'
                    });
                },
                function() {
                    $(this).css({
                        'transform': 'translateY(0)',
                        'box-shadow': '0 4px 6px rgba(0,0,0,0.1)'
                    });
                }
            );
        }
    } catch(e) {
        console.log('Get Outstanding Invoices button styling skipped');
    }
}

function apply_field_styling(frm) {
    // Apply color coding to important fields
    const field_colors = {
        'cost_center': '#90ee90',
        'trans_type': '#87ceeb',
        'transaction_date': '#fffacd',
        'account_to_credit': '#90ee90',
        'reference_no': '#87ceeb',
        'amount_received': '#fffacd',
        'amount_received_in_fc': '#fffacd',
        'frequency': '#90ee90',
        'end_date': '#87ceeb',
        'charge_amount': '#fffacd',
        'customer_id': '#90ee90',
        'payer_name': '#87ceeb',
        'mode_of_payment': '#fffacd'
    };
    
    Object.keys(field_colors).forEach(field => {
        try {
            if (frm.fields_dict[field] && frm.fields_dict[field].$input) {
                frm.get_field(field).$input.css('background-color', field_colors[field]);
            }
        } catch(e) {
            console.log('Field styling skipped for ' + field);
        }
    });
}

function set_account_queries(frm) {
    // Set query for account fields to exclude group accounts
    const account_fields = [
        'account_to_credit',
        'deferred_revenue_account',
        'revenue_account'
    ];
    
    account_fields.forEach(field => {
        frm.set_query(field, function() {
            return {
                filters: {
                    is_group: 0,
                    company: frm.doc.company
                }
            };
        });
    });
}

function handle_transaction_type_change(frm) {
    // Handle logic when transaction type changes
    if (["Customer Receipt", "Receive from One-Off"].includes(frm.doc.trans_type)) {
        frm.set_value('account_to_credit', '');
        frm.set_value('payer_name', '');
        
        // For One-Off, set cash customer
        if (frm.doc.trans_type === "Receive from One-Off") {
            frm.set_value('customer_id', 'CUST-2023-00001'); // Cash Sales ID
        }
    } else if (frm.doc.trans_type === "Transfer In") {
        // Set default transfer account
        frappe.db.get_value('Company', frm.doc.company, 'custom_default_interbank_transfer')
            .then(r => {
                if (r.message && r.message.custom_default_interbank_transfer) {
                    frm.set_value('account_to_credit', r.message.custom_default_interbank_transfer);
                    frm.set_df_property('account_to_credit', 'read_only', 1);
                }
            });
    } else {
        frm.set_df_property('account_to_credit', 'read_only', 0);
    }
}

function handle_currency_change(frm) {
    // Show/hide currency-specific fields
    let is_foreign = frm.doc.receipt_currency !== 'NGN';
    
    frm.toggle_display('amount_received', !is_foreign);
    frm.toggle_display('amount_received_in_fc', is_foreign);
    frm.toggle_display('exchange_rate', is_foreign);
    frm.toggle_reqd('exchange_rate', is_foreign);
}

function handle_amortization_toggle(frm) {
    // Clear amortization fields when disabled
    if (frm.doc.amortize === 0) {
        frm.set_value('frequency', '');
        frm.set_value('start_date', '');
        frm.set_value('end_date', '');
        frm.set_value('deferred_revenue_account', '');
        frm.set_value('revenue_account', '');
        frm.set_value('no_of_days', '');
        frm.set_value('charge_amount', 0);
        frm.clear_table('schedule_of_deferred_revenue');
        frm.refresh_field('schedule_of_deferred_revenue');
    }
}

function calculate_end_date(frm) {
    if (frm.doc.start_date && frm.doc.no_of_days) {
        let end_date = frappe.datetime.add_days(frm.doc.start_date, frm.doc.no_of_days);
        frm.set_value('end_date', end_date);
    }
}

function calculate_amortization_schedule(frm) {
    if (!frm.doc.start_date || !frm.doc.end_date || !frm.doc.frequency) {
        return;
    }
    
    let days_diff = frappe.datetime.get_day_diff(frm.doc.end_date, frm.doc.start_date);
    let no_of_months = Math.floor(days_diff / 30);
    let amount = frm.doc.amount_received || (frm.doc.amount_received_in_fc * frm.doc.exchange_rate);
    
    if (!amount || amount <= 0) {
        return;
    }
    
    let charge_amount = 0;
    
    if (frm.doc.frequency === "Monthly") {
        charge_amount = amount / no_of_months;
    } else if (frm.doc.frequency === "Quarterly") {
        charge_amount = (amount / no_of_months) * 3;
    }
    
    frm.set_value('charge_amount', charge_amount);
}

function generate_amortization_schedule(frm) {
    let period_months = frm.doc.frequency === "Monthly" ? 1 : 3;
    let days_diff = frappe.datetime.get_day_diff(frm.doc.end_date, frm.doc.start_date);
    let no_of_periods = Math.floor(days_diff / (30 * period_months));
    
    // Clear existing schedule
    frm.clear_table('schedule_of_deferred_revenue');
    
    // Generate schedule entries
    for (let i = 1; i <= no_of_periods; i++) {
        let posting_date = frappe.datetime.add_months(frm.doc.start_date, (i - 1) * period_months);
        
        if (frappe.datetime.get_day_diff(posting_date, frm.doc.end_date) > 0) {
            break;
        }
        
        let row = frm.add_child('schedule_of_deferred_revenue');
        row.date = posting_date;
        row.title = frm.doc.payer_name || frm.doc.customer_name;
        row.amount = frm.doc.charge_amount;
        row.transaction_description = `${frm.doc.frequency} amortization entry`;
        row.frequency = frm.doc.frequency;
        row.period = no_of_periods;
        row.account_to_debit = frm.doc.deferred_revenue_account;
        row.account_to_credit = frm.doc.revenue_account;
    }
    
    frm.refresh_field('schedule_of_deferred_revenue');
}

function fetch_outstanding_invoices(frm) {
    if (!frm.doc.customer_id) {
        frappe.msgprint(__('Please select a customer first'));
        return;
    }
    
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Sales Invoice',
            fields: [
                'posting_date', 'customer', 'customer_name', 'due_date',
                'currency', 'total', 'name', 'outstanding_amount',
                'grand_total', 'project', 'payment_terms_template',
                'base_total', 'docstatus'
            ],
            filters: [
                ['customer', '=', frm.doc.customer_id],
                ['docstatus', '=', 1],
                ['outstanding_amount', '>', 0]
            ],
            limit_page_length: 1000,
            order_by: 'due_date asc, posting_date asc'
        },
        callback: function(response) {
            let unpaid_invoices = response.message || [];
            
            if (unpaid_invoices.length === 0) {
                frappe.msgprint(__('No outstanding invoices found for this customer'));
                return;
            }
            
            // Clear existing rows
            frm.clear_table('receipts_reference');
            
            // Add invoices to table
            unpaid_invoices.forEach(function(invoice) {
                let row = frm.add_child('receipts_reference');
                row.date = invoice.posting_date;
                row.reference_doctype = 'Sales Invoice';
                row.reference_name = invoice.name;
                row.due_date = invoice.due_date;
                row.bill_no = invoice.name;
                row.payment_term = invoice.payment_terms_template || '';
                row.total_amount = invoice.grand_total;
                row.outstanding_amount = invoice.outstanding_amount;
                row.allocated_amount = 0;
                row.exchange_rate = 1;
                row.exchange_gain_loss = 0;
            });
            
            frm.refresh_field('receipts_reference');
            update_allocation_summary(frm);
            
            frappe.show_alert({
                message: __('Loaded {0} outstanding invoices', [unpaid_invoices.length]),
                indicator: 'green'
            }, 5);
        }
    });
}

function fetch_party_name(frm, cdt, cdn, row) {
    let doctype = row.party_type === "Supplier" ? "Supplier" : "Customer";
    let fieldname = row.party_type === "Supplier" ? "supplier_name" : "customer_name";
    
    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: doctype,
            filters: { name: row.party },
            fieldname: fieldname
        },
        callback: function(response) {
            if (response.message) {
                frappe.model.set_value(cdt, cdn, "party_name", response.message[fieldname]);
            }
        }
    });
}

function setup_related_company_queries(frm, cdt, cdn, row) {
    // Set query for related_company_account
    frm.fields_dict['related_company_receipts'].grid.get_field('related_company_account').get_query = function() {
        if (!row.related_company) {
            frappe.msgprint(__('Please select Related Company first'));
            return { filters: {} };
        }
        
        return {
            filters: {
                company: row.related_company,
                is_group: 0,
                root_type: "Asset"
            }
        };
    };
    
    // Set query for party based on trans_type
    frm.fields_dict['related_company_receipts'].grid.get_field('party').get_query = function() {
        if (!row.related_company) {
            frappe.msgprint(__('Please select Related Company first'));
            return { filters: {} };
        }
        
        if (row.trans_type === 'Customer Receipt') {
            // Show customers from the related company
            return {
                query: 'frappe.contacts.doctype.contact.contact.contact_query',
                filters: {
                    company: row.related_company
                }
            };
        } else {
            // Show chart of accounts from the related company
            return {
                filters: {
                    company: row.related_company,
                    is_group: 0,
                    account_type: ['in', ['Income Account', 'Revenue']]
                }
            };
        }
    };
    
    // Set query for cost_center
    frm.fields_dict['related_company_receipts'].grid.get_field('cost_center').get_query = function() {
        if (!row.related_company) {
            return { filters: {} };
        }
        
        return {
            filters: {
                company: row.related_company,
                is_group: 0
            }
        };
    };
    
    // Update party_type based on trans_type
    if (row.trans_type === 'Customer Receipt') {
        frappe.model.set_value(cdt, cdn, 'party_type', 'Customer');
    } else {
        frappe.model.set_value(cdt, cdn, 'party_type', 'Account');
    }
}

function calculate_all_totals(frm) {
    calculate_total_outstanding(frm);
    calculate_related_company_total(frm);
    calculate_multi_line_total(frm);
}

function calculate_total_outstanding(frm) {
    let total = 0;
    (frm.doc.receipts_reference || []).forEach(row => {
        total += flt(row.allocated_amount);
    });
    frm.set_value('total_outstanding_invoice', total);
}

function calculate_related_company_total(frm) {
    let total = 0;
    (frm.doc.related_company_receipts || []).forEach(row => {
        total += flt(row.amount);
    });
    frm.set_value('total_rcoy', total);
}

function calculate_multi_line_total(frm) {
    let total = 0;
    (frm.doc.receipts_item_line || []).forEach(row => {
        total += flt(row.amount);
    });
    frm.set_value('total', total);
}

function calculate_local_currency_amount(frm) {
    if (!frm.doc.company) {
        return;
    }
    
    frappe.db.get_value('Company', frm.doc.company, 'default_currency', function(r) {
        if (r && r.default_currency) {
            let company_currency = r.default_currency;
            
            if (frm.doc.receipt_currency === company_currency) {
                frm.set_value('local_currency_amount', frm.doc.amount_received || 0);
            } else {
                let exchange_rate = frm.doc.exchange_rate || 1;
                let amount_fc = frm.doc.amount_received_in_fc || 0;
                frm.set_value('local_currency_amount', amount_fc * exchange_rate);
            }
        }
    });
}

// ========================================================================
// AI SMART ALLOCATION
// ========================================================================

function run_ai_smart_allocation(frm) {
    if (!frm.doc.customer_id) {
        frappe.msgprint({
            title: __('Customer Required'),
            message: __('Please select a customer before running smart allocation'),
            indicator: 'orange'
        });
        return;
    }
    
    if (!frm.doc.local_currency_amount && !frm.doc.amount_received && !frm.doc.amount_received_in_fc) {
        frappe.msgprint({
            title: __('Amount Required'),
            message: __('Please enter the receipt amount before running smart allocation'),
            indicator: 'orange'
        });
        return;
    }
    
    frappe.show_alert({
        message: __('Running AI Smart Allocation...'),
        indicator: 'blue'
    }, 3);
    
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.receipts.receipts.ai_smart_allocation',
        args: {
            doc_name: frm.doc.name
        },
        freeze: true,
        freeze_message: __('AI is analyzing invoices and allocating payments...'),
        callback: function(r) {
            if (r.message) {
                frm.reload_doc();
                
                let result = r.message;
                let message = `
                    <div style="padding: 15px; font-family: Arial, sans-serif;">
                        <h4 style="color: #27ae60; margin-bottom: 15px;">
                            <i class="fa fa-check-circle"></i> AI Allocation Completed Successfully!
                        </h4>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Invoices Matched:</strong></td>
                                <td style="padding: 8px; border-bottom: 1px solid #ddd;">${result.invoices_matched}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Total Allocated:</strong></td>
                                <td style="padding: 8px; border-bottom: 1px solid #ddd; color: #27ae60; font-weight: bold;">
                                    ${format_currency(result.total_allocated, frm.doc.receipt_currency)}
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 8px;"><strong>Remaining Amount:</strong></td>
                                <td style="padding: 8px; color: ${result.remaining_amount > 0 ? '#f39c12' : '#27ae60'}; font-weight: bold;">
                                    ${format_currency(result.remaining_amount, frm.doc.receipt_currency)}
                                </td>
                            </tr>
                        </table>
                    </div>
                `;
                
                frappe.msgprint({
                    title: __('AI Smart Allocation Results'),
                    message: message,
                    indicator: 'green',
                    primary_action: {
                        label: __('Preview Allocation'),
                        action: function() {
                            show_preview_allocation(frm);
                        }
                    }
                });
            }
        }
    });
}

// ========================================================================
// PREVIEW ALLOCATION
// ========================================================================

function show_preview_allocation(frm) {
    if (!frm.doc.receipts_reference || frm.doc.receipts_reference.length === 0) {
        frappe.msgprint({
            title: __('No Allocations'),
            message: __('No invoice allocations found. Please run AI Smart Allocation or add invoices manually.'),
            indicator: 'orange'
        });
        return;
    }
    
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.receipts.receipts.preview_allocation',
        args: {
            doc_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                let d = new frappe.ui.Dialog({
                    title: __('Invoice Allocation Preview'),
                    size: 'extra-large',
                    fields: [
                        {
                            fieldtype: 'HTML',
                            fieldname: 'preview_html'
                        }
                    ],
                    primary_action_label: __('Close'),
                    primary_action: function() {
                        d.hide();
                    }
                });
                
                d.fields_dict.preview_html.$wrapper.html(r.message);
                d.show();
            }
        }
    });
}

// ========================================================================
// SEND RECEIPT EMAIL FUNCTION
// ========================================================================

function send_receipt_email(frm) {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.receipts.receipts.send_internal_receipt_notification',
        args: {
            doc_name: frm.doc.name
        },
        freeze: true,
        freeze_message: __('Sending receipt email...'),
        callback: function(r) {
            if (!r.exc) {
                frappe.show_alert({
                    message: __('Receipt email sent successfully'),
                    indicator: 'green'
                }, 5);
            }
        }
    });
}

// ========================================================================
// ALLOCATION SUMMARY HTML (Real-time Update)
// ========================================================================

function update_allocation_summary(frm) {
    if (!frm.fields_dict.allocation_summary_html) {
        return;
    }
    
    if (!frm.doc.receipts_reference || frm.doc.receipts_reference.length === 0) {
        frm.fields_dict.allocation_summary_html.$wrapper.html(
            '<div class="alert alert-info">No invoice allocations yet</div>'
        );
        return;
    }
    
    let total_allocated = 0;
    let total_outstanding = 0;
    let fully_paid_count = 0;
    
    frm.doc.receipts_reference.forEach(row => {
        total_allocated += flt(row.allocated_amount);
        total_outstanding += flt(row.outstanding_amount);
        
        if (flt(row.allocated_amount) >= flt(row.outstanding_amount)) {
            fully_paid_count++;
        }
    });
    
    let amount_received = frm.doc.local_currency_amount || frm.doc.amount_received || 
                         (frm.doc.amount_received_in_fc * frm.doc.exchange_rate);
    let remaining = amount_received - total_allocated;
    
    let html = `
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin: 10px 0;">
            <h4 style="margin: 0 0 15px 0; font-size: 18px;">Allocation Summary</h4>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px;">
                <div style="text-align: center;">
                    <div style="font-size: 12px; opacity: 0.9;">Invoices</div>
                    <div style="font-size: 24px; font-weight: bold; margin-top: 5px;">${frm.doc.receipts_reference.length}</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 12px; opacity: 0.9;">Fully Paid</div>
                    <div style="font-size: 24px; font-weight: bold; margin-top: 5px;">${fully_paid_count}</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 12px; opacity: 0.9;">Allocated</div>
                    <div style="font-size: 24px; font-weight: bold; margin-top: 5px;">${format_currency(total_allocated, frm.doc.receipt_currency)}</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 12px; opacity: 0.9;">Remaining</div>
                    <div style="font-size: 24px; font-weight: bold; margin-top: 5px; color: ${remaining > 0 ? '#ffe066' : '#a5d8ff'};">
                        ${format_currency(remaining, frm.doc.receipt_currency)}
                    </div>
                </div>
            </div>
        </div>
    `;
    
    frm.fields_dict.allocation_summary_html.$wrapper.html(html);
}

// ========================================================================
// HELPER FUNCTIONS
// ========================================================================

function format_currency(value, currency) {
    return format_number(value, null, 2) + ' ' + (currency || '');
}


// === Receipts Custom Script ===

frappe.ui.form.on('Receipts', {

    // Trigger on form load and refresh
    onload: function(frm) {
        frm.trigger('calculate_custom_fields');
    },

    refresh: function(frm) {
        frm.trigger('calculate_custom_fields');
    },

    // Trigger when customer changes
    customer_id: function(frm) {
        frm.trigger('calculate_custom_fields');
    },

    // Trigger when transaction_date changes
    transaction_date: function(frm) {
        frm.trigger('calculate_custom_fields');
    },

    // Trigger when amount_paid changes
    amount_paid: function(frm) {
        frm.trigger('derive_balance');
    },

    // Trigger when amount_paid_in_fc changes
    amount_paid_in_fc: function(frm) {
        frm.trigger('derive_balance');
    },

    // Fetch opening balance from customer ledger
    calculate_custom_fields: function(frm) {
        if (!frm.doc.customer_id || !frm.doc.company) return;

        frappe.call({
            method: 'erpnext.accounts.utils.get_balance_on',
            args: {
                party_type: 'Customer',
                party: frm.doc.customer_id,
                company: frm.doc.company,
                date: frm.doc.transaction_date || frappe.datetime.get_today(),
                in_account_currency: false
            },
            callback: function(r) {
                if (r.message !== undefined) {
                    let opening_balance = flt(r.message);

                    // If already saved/submitted, avoid double-counting
                    if (!frm.doc.__islocal && frm.doc.docstatus !== 0) {
                        opening_balance = opening_balance - flt(frm.doc.invoice_amount);
                    }

                    frm.set_value('opening_balance', opening_balance);
                    frm.trigger('derive_balance');
                }
            }
        });
    },

    // Derive invoice_amount, balance_due from child table and paid amounts
    derive_balance: function(frm) {
        // Sum the total column from receipt_detail child table
        let invoice_amount = 0;
        (frm.doc.receipt_detail || []).forEach(function(row) {
            invoice_amount += flt(row.total);
        });

        let opening_balance = flt(frm.doc.opening_balance);
        let amount_paid = 0;

        if (frm.doc.amount_received != null && frm.doc.amount_received !== "") {
            amount_paid = flt(frm.doc.amount_received);
        } else {
            amount_paid = flt(frm.doc.amount_received_in_fc);
        }

        // balance_due = opening_balance + invoice_amount - amount_paid
        let balance_due = opening_balance + invoice_amount - amount_paid;

        frm.set_value('invoice_amount', invoice_amount);
        frm.set_value('balance_due', balance_due);
    }
});


// === Child Table: receipt_detail ===
frappe.ui.form.on('receipt_detail', {

    // Recalculate row total when qty or unit_price changes
    qty: function(frm, cdt, cdn) {
        calculate_row_total(frm, cdt, cdn);
    },

    unit_price: function(frm, cdt, cdn) {
        calculate_row_total(frm, cdt, cdn);
    },

    // Recalculate invoice_amount when rows are added/removed
    receipt_detail_add: function(frm) {
        frm.trigger('derive_balance');
    },

    receipt_detail_remove: function(frm) {
        frm.trigger('derive_balance');
    },

    // Recalculate when total is directly edited
    total: function(frm) {
        frm.trigger('derive_balance');
    }
});


// Helper: calculate individual row total
function calculate_row_total(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let total = flt(row.qty) * flt(row.unit_price);
    frappe.model.set_value(cdt, cdn, 'total', total);
    // After row total is set, re-sum invoice_amount
    frm.trigger('derive_balance');
}

//===========RECEIPTS=====================

// === Receipts Custom Script ===

frappe.ui.form.on('Receipts', {

    onload: function(frm) {
        frm.trigger('fetch_opening_balance');
    },

    refresh: function(frm) {
        frm.trigger('fetch_opening_balance');
    },

    customer_id: function(frm) {
        frm.trigger('fetch_opening_balance');
    },

    transaction_date: function(frm) {
        frm.trigger('fetch_opening_balance');
    },

    amount_paid: function(frm) {
        frm.trigger('derive_balance');
    },

    amount_paid_in_fc: function(frm) {
        frm.trigger('derive_balance');
    },

    // Fetch correct opening balance via custom Python API
    fetch_opening_balance: function(frm) {
        if (!frm.doc.customer_id || !frm.doc.transaction_date) return;

        let company = frm.doc.company || frappe.defaults.get_default('company');

        frappe.call({
            method: 'ecclesia.api.customer_balance.get_customer_opening_balance',  // update your_app
            args: {
                customer: frm.doc.customer_id,
                company: company,
                transaction_date: frm.doc.transaction_date,
                current_docname: frm.doc.name || null
            },
            callback: function(r) {
                if (r.message !== undefined) {
                    frm.set_value('opening_balance', flt(r.message));
                    frm.trigger('derive_balance');
                }
            }
        });
    },

    derive_balance: function(frm) {
        // Sum total column from receipt_detail child table
        let invoice_amount = 0;
        (frm.doc.receipt_detail || []).forEach(function(row) {
            invoice_amount += flt(row.total);
        });

        let opening_balance = flt(frm.doc.opening_balance);
        let amount_paid     = flt(frm.doc.amount_paid);

        // balance_due = opening_balance + invoice_amount - amount_paid
        let balance_due = opening_balance + invoice_amount - amount_paid;

        frm.set_value('invoice_amount', invoice_amount);
        frm.set_value('balance_due', balance_due);
    }
});


// === Child Table ===
frappe.ui.form.on('receipt_detail', {

    qty: function(frm, cdt, cdn) {
        calculate_row_total(frm, cdt, cdn);
    },

    unit_price: function(frm, cdt, cdn) {
        calculate_row_total(frm, cdt, cdn);
    },

    receipt_detail_add: function(frm) {
        frm.trigger('derive_balance');
    },

    receipt_detail_remove: function(frm) {
        frm.trigger('derive_balance');
    },

    total: function(frm) {
        frm.trigger('derive_balance');
    }
});


function calculate_row_total(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let total = flt(row.qty) * flt(row.unit_price);
    frappe.model.set_value(cdt, cdn, 'total', total);
    frm.trigger('derive_balance');
}