// -*- coding: utf-8 -*-
// Copyright (c) 2025, Your Company
// Payment Voucher Client Script

frappe.ui.form.on('Payments', {
    // ==================== Form Initialization ====================
    
    onload: function(frm) {
        // Set default values
        if (frm.is_new()) {
            frm.set_value('transaction_date', frappe.datetime.get_today());
            frm.set_value('payment_status', 'Draft');
            frm.set_value('create_accounting_entries', 1);
        }
        
        // Set field queries
        set_field_queries(frm);
        
        // Setup custom buttons
        setup_custom_buttons(frm);
        
        // Fetch company currency
        if (frm.doc.company) {
            get_company_currency(frm);
        }
        
        // Apply UI enhancements
        apply_zebra_striping(frm);
        style_buttons(frm);
        apply_field_styling(frm);
        
        // Initialize allocation summary
        if (frm.doc.payments_reference && frm.doc.payments_reference.length > 0) {
            update_allocation_summary(frm);
        }
    },
    
    refresh: function(frm) {
        // Apply UI enhancements
        apply_zebra_striping(frm);
        style_buttons(frm);
        apply_field_styling(frm);
        
        // Update field visibility
        toggle_field_visibility(frm);
        
        // Show accounting entries if submitted
        if (frm.doc.docstatus === 1) {
            show_accounting_entries(frm);
        }
        
        // Setup custom buttons
        setup_custom_buttons(frm);
        
        // Add custom buttons based on status
        add_action_buttons(frm);
        
        // Display allocation summary if supplier payment
        if (frm.doc.trans_type === 'Supplier Payment' && frm.doc.payments_reference) {
            display_allocation_summary(frm);
        }
        
        // Update allocation summary in real-time
        if (frm.doc.payments_reference && frm.doc.payments_reference.length > 0) {
            update_allocation_summary(frm);
        }
    },
    
    // ==================== Transaction Type Logic ====================
    
    company: function(frm) {
        // Fetch company currency when company changes
        if (frm.doc.company) {
            get_company_currency(frm);
        }
    },
    
    trans_type: function(frm) {
        // Clear dependent fields
        frm.set_value('payee_id', '');
        frm.set_value('payee_name', '');
        frm.set_value('account_to_debit', '');
        
        // Show/hide fields based on transaction type
        toggle_field_visibility(frm);
        
        // Set default accounts
        set_default_accounts(frm);
    },
    
    // ==================== Party/Beneficiary Logic ====================
    
    payee_id: function(frm) {
        if (frm.doc.payee_id) {
            // Fetch supplier details
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Supplier',
                    name: frm.doc.payee_id
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('supplier_name', r.message.supplier_name);
                    }
                }
            });
        }
    },
    
    customer_id: function(frm) {
        if (frm.doc.customer_id) {
            // Fetch customer details
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Customer',
                    name: frm.doc.customer_id
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('customer_name', r.message.customer_name);
                    }
                }
            });
        }
    },
    
    // ==================== Currency & Exchange Logic ====================
    
    payment_currency: function(frm) {
        // Set exchange rate
        if (frm.doc.payment_currency) {
            let company_currency = frm.doc.__company_currency || 'NGN';
            
            if (frm.doc.payment_currency === company_currency) {
                frm.set_value('exchange_rate', 1);
            } else {
                fetch_exchange_rate(frm);
            }
        }
        
        // Toggle amount fields
        toggle_field_visibility(frm);
    },
    
    exchange_rate: function(frm) {
        calculate_local_currency_amount(frm);
    },
    
    remittance_bank: function(frm) {
        if (frm.doc.remittance_bank) {
            // Fetch bank account details
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Bank Account',
                    name: frm.doc.remittance_bank
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('remittance_bank_gl', r.message.account);
                        frm.set_value('bank_account_currency', r.message.account_currency);
                    }
                }
            });
        }
    },
    
    // ==================== Amount Calculations ====================
    
    amount_paid: function(frm) {
        let company_currency = frm.doc.__company_currency || 'NGN';
        if (frm.doc.payment_currency === company_currency) {
            frm.set_value('local_currency_amount', frm.doc.amount_paid);
            calculate_wht(frm);
            convert_amount_to_words(frm);
        }
    },
    
    amount_paid_in_fc: function(frm) {
        let company_currency = frm.doc.__company_currency || 'NGN';
        if (frm.doc.payment_currency !== company_currency) {
            calculate_local_currency_amount(frm);
            calculate_wht(frm);
            convert_amount_to_words(frm);
        }
    },
    
    // ==================== WHT Calculation ====================
    
    deduct_wht: function(frm) {
        if (frm.doc.deduct_wht) {
            // Set default WHT rate if not set
            if (!frm.doc.whtax_rate) {
                frm.set_value('whtax_rate', 5);
            }
            calculate_wht(frm);
        } else {
            frm.set_value('wht_amount', 0);
            frm.set_value('net_amount', frm.doc.local_currency_amount);
        }
    },
    
    whtax_rate: function(frm) {
        calculate_wht(frm);
    },
    
    // ==================== Transaction Options ====================
    
    is_multi_line: function(frm) {
        toggle_field_visibility(frm);
    },
    
    is_shared_cost: function(frm) {
        toggle_field_visibility(frm);
    },
    
    is_related_coy_trans: function(frm) {
        toggle_field_visibility(frm);
    },
    
    amortize: function(frm) {
        if (frm.doc.amortize) {
            // Set default frequency
            if (!frm.doc.frequency) {
                frm.set_value('frequency', 'Monthly');
            }
        }
        toggle_field_visibility(frm);
    },
    
    // ==================== Amortization Logic ====================
    
    frequency: function(frm) {
        if (frm.doc.frequency && frm.doc.start_date && frm.doc.end_date) {
            calculate_amortization_schedule(frm);
        }
    },
    
    start_date: function(frm) {
        if (frm.doc.start_date && frm.doc.end_date) {
            validate_dates(frm);
            calculate_amortization_schedule(frm);
        }
    },
    
    end_date: function(frm) {
        if (frm.doc.start_date && frm.doc.end_date) {
            validate_dates(frm);
            calculate_amortization_schedule(frm);
        }
    },
    
    no_of_days: function(frm) {
        if (frm.doc.no_of_days && frm.doc.local_currency_amount) {
            calculate_charge_per_period(frm);
        }
    },
    
    // ==================== Button Handlers ====================
    
    get_outstanding_invoices: function(frm) {
        if (!frm.doc.payee_id) {
            frappe.msgprint(__('Please select a Supplier first'));
            return;
        }
        
        frappe.call({
            method: 'erpnext.accounts.doctype.payment_entry.payment_entry.get_outstanding_reference_documents',
            args: {
                args: {
                    party_type: 'Supplier',
                    party: frm.doc.payee_id,
                    party_account: frappe.defaults.get_default('default_payable_account'),
                    company: frm.doc.company
                }
            },
            callback: function(r) {
                if (r.message && r.message.length > 0) {
                    populate_invoice_table(frm, r.message);
                } else {
                    frappe.msgprint(__('No outstanding invoices found for this supplier'));
                }
            }
        });
    },
    
    ai_smart_allocation: function(frm) {
        if (!frm.doc.payments_reference || frm.doc.payments_reference.length === 0) {
            frappe.msgprint(__('Please fetch outstanding invoices first'));
            return;
        }
        
        if (!frm.doc.local_currency_amount || frm.doc.local_currency_amount <= 0) {
            frappe.msgprint(__('Please enter payment amount first'));
            return;
        }
        
        perform_smart_allocation(frm);
    },
    
    preview_allocation: function(frm) {
        if (!frm.doc.payments_reference || frm.doc.payments_reference.length === 0) {
            frappe.msgprint(__('No invoices to preview'));
            return;
        }
        
        display_allocation_summary(frm);
    },
    
    // ==================== Before Save ====================
    
    before_save: function(frm) {
        // Validate required fields
        validate_payment_data(frm);
        
        // Calculate totals
        calculate_all_totals(frm);
        
        // Validate allocations
        if (frm.doc.trans_type === 'Supplier Payment') {
            validate_invoice_allocation(frm);
        }
        
        // Validate multi-line totals
        if (frm.doc.is_multi_line) {
            validate_multi_line_totals(frm);
        }
        
        // Validate shared cost distribution
        if (frm.doc.is_shared_cost) {
            validate_cost_distribution(frm);
        }
    },
    
    // ==================== Before Submit ====================
    
    before_submit: function(frm) {
        // Final validations
        if (frm.doc.create_accounting_entries) {
            if (!frm.doc.remittance_bank_gl) {
                frappe.throw(__('Bank GL Account is required'));
            }
            
            if (frm.doc.trans_type === 'Expense Payment' && !frm.doc.account_to_debit) {
                frappe.throw(__('Account to Debit is required for Expense Payment'));
            }
        }
        
        // Set payment status
        frm.set_value('payment_status', 'Processing');
    },
    
    // ==================== On Submit ====================
    
    on_submit: function(frm) {
        // Create accounting entries
        if (frm.doc.create_accounting_entries) {
            create_accounting_entries(frm);
        }
        
        // Update payment status
        frappe.call({
            method: 'frappe.client.set_value',
            args: {
                doctype: 'Payments',
                name: frm.doc.name,
                fieldname: 'payment_status',
                value: 'Completed'
            }
        });
        
        frappe.show_alert({
            message: __('Payment submitted successfully'),
            indicator: 'green'
        }, 5);
    },
    
    // ==================== On Cancel ====================
    
    before_cancel: function(frm) {
        frappe.confirm(
            __('Are you sure you want to cancel this payment? All linked accounting entries will be cancelled.'),
            function() {
                // Cancel accounting entries
                cancel_accounting_entries(frm);
            }
        );
    },
    
    on_cancel: function(frm) {
        frappe.show_alert({
            message: __('Payment cancelled successfully'),
            indicator: 'red'
        }, 5);
    }
});

// ==================== Child Table: Payments Reference ====================

frappe.ui.form.on('Payments Reference', {
    allocated_amount: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        // Validate allocated amount
        if (row.allocated_amount > row.outstanding_amount) {
            frappe.msgprint(__('Allocated amount cannot be greater than outstanding amount'));
            frappe.model.set_value(cdt, cdn, 'allocated_amount', row.outstanding_amount);
        }
        
        // Calculate total allocated
        calculate_total_allocated(frm);
        
        // Update allocation summary in real-time
        update_allocation_summary(frm);
    },
    
    payments_reference_remove: function(frm) {
        calculate_total_allocated(frm);
        update_allocation_summary(frm);
    },
    
    payments_reference_add: function(frm) {
        update_allocation_summary(frm);
    }
});

// ==================== Child Table: Payments Item Line ====================

frappe.ui.form.on('Payments Item Line', {
    amount: function(frm, cdt, cdn) {
        calculate_multi_line_total(frm);
    },
    
    exch_rate: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.amount && row.exch_rate) {
            frappe.model.set_value(cdt, cdn, 'amount_in_lcy', row.amount * row.exch_rate);
        }
        calculate_multi_line_total(frm);
    },
    
    payments_item_line_remove: function(frm) {
        calculate_multi_line_total(frm);
    }
});

// ==================== Child Table: Cost Center Distribution ====================

frappe.ui.form.on('Cost Center Distribution', {
    distribution: function(frm) {
        calculate_total_distribution(frm);
    },
    
    cost_center_distribution_remove: function(frm) {
        calculate_total_distribution(frm);
    }
});

// ==================== Child Table: Related Company Payments ====================

frappe.ui.form.on('Related Company Payments', {
    amount: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.amount && frm.doc.exchange_rate) {
            frappe.model.set_value(cdt, cdn, 'amount_in_lcy', row.amount * frm.doc.exchange_rate);
        }
        calculate_related_company_total(frm);
    },
    
    related_company_payments_remove: function(frm) {
        calculate_related_company_total(frm);
    }
});



// ==================== UI ENHANCEMENT FUNCTIONS ====================

function apply_zebra_striping(frm) {
    // Apply zebra striping to all child tables
    const tables = [
        'payments_reference',
        'payments_item_line',
        'cost_center_distribution',
        'related_company_payments',
        'amortization_schedule'
    ];
    
    tables.forEach(table => {
        if (frm.fields_dict[table]) {
            frm.fields_dict[table].grid.wrapper.find('.grid-row').each(function(i, row) {
                $(row).css('background-color', i % 2 === 0 ? '#ffffff' : '#f0f8ff');
            });
        }
    });
}

function style_buttons(frm) {
    // Style AI Smart Allocation Button
    if (frm.fields_dict.ai_smart_allocation) {
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
    
    // Style Preview Allocation Button
    if (frm.fields_dict.preview_allocation) {
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
    
    // Style Get Outstanding Invoices Button
    if (frm.fields_dict.get_outstanding_invoices) {
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
}

function apply_field_styling(frm) {
    // Apply color coding to important fields
    const field_colors = {
        'cost_center': '#90ee90',
        'trans_type': '#87ceeb',
        'transaction_date': '#fffacd',
        'account_to_debit': '#90ee90',
        'reference_no': '#87ceeb',
        'amount_paid': '#fffacd',
        'amount_paid_in_fc': '#fffacd',
        'frequency': '#90ee90',
        'end_date': '#87ceeb',
        'charge_amount': '#fffacd',
        'payee_id': '#90ee90',
        'payee_name': '#87ceeb',
        'mode_of_payment': '#fffacd',
        'remittance_bank': '#90ee90',
        'whtax_rate': '#ffb3ba',
        'deduct_wht': '#bae1ff'
    };
    
    Object.keys(field_colors).forEach(field => {
        if (frm.fields_dict[field]) {
            frm.get_field(field).$input.css('background-color', field_colors[field]);
        }
    });
}

function update_allocation_summary(frm) {
    if (!frm.doc.payments_reference || frm.doc.payments_reference.length === 0) {
        if (frm.fields_dict.allocation_summary_html) {
            frm.fields_dict.allocation_summary_html.$wrapper.html(
                '<div class="alert alert-info">No invoice allocations yet</div>'
            );
        }
        return;
    }
    
    let total_allocated = 0;
    let total_outstanding = 0;
    let fully_paid_count = 0;
    
    frm.doc.payments_reference.forEach(row => {
        total_allocated += flt(row.allocated_amount);
        total_outstanding += flt(row.outstanding_amount);
        
        if (flt(row.allocated_amount) >= flt(row.outstanding_amount)) {
            fully_paid_count++;
        }
    });
    
    let amount_paid = frm.doc.local_currency_amount || frm.doc.amount_paid || 
                     (frm.doc.amount_paid_in_fc * frm.doc.exchange_rate);
    let remaining = amount_paid - total_allocated;
    
    let html = `
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin: 10px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h4 style="margin: 0 0 15px 0; font-size: 18px; display: flex; align-items: center;">
                <i class="fa fa-calculator" style="margin-right: 10px;"></i>
                Allocation Summary
            </h4>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px;">
                <div style="text-align: center; background: rgba(255,255,255,0.1); padding: 15px; border-radius: 8px;">
                    <div style="font-size: 12px; opacity: 0.9; margin-bottom: 5px;">Invoices</div>
                    <div style="font-size: 28px; font-weight: bold;">${frm.doc.payments_reference.length}</div>
                </div>
                <div style="text-align: center; background: rgba(255,255,255,0.1); padding: 15px; border-radius: 8px;">
                    <div style="font-size: 12px; opacity: 0.9; margin-bottom: 5px;">Fully Paid</div>
                    <div style="font-size: 28px; font-weight: bold; color: #a5d8ff;">${fully_paid_count}</div>
                </div>
                <div style="text-align: center; background: rgba(255,255,255,0.1); padding: 15px; border-radius: 8px;">
                    <div style="font-size: 12px; opacity: 0.9; margin-bottom: 5px;">Allocated</div>
                    <div style="font-size: 28px; font-weight: bold; color: #51cf66;">${format_currency(total_allocated)}</div>
                </div>
                <div style="text-align: center; background: rgba(255,255,255,0.1); padding: 15px; border-radius: 8px;">
                    <div style="font-size: 12px; opacity: 0.9; margin-bottom: 5px;">Remaining</div>
                    <div style="font-size: 28px; font-weight: bold; color: ${remaining > 0 ? '#ffe066' : '#a5d8ff'};">
                        ${format_currency(remaining)}
                    </div>
                </div>
            </div>
            ${remaining > 0 ? `
                <div style="margin-top: 15px; padding: 10px; background: rgba(255, 230, 102, 0.2); border-radius: 5px; border-left: 4px solid #ffe066;">
                    <i class="fa fa-info-circle"></i> <strong>Unallocated Amount:</strong> ${format_currency(remaining)} remaining
                </div>
            ` : `
                <div style="margin-top: 15px; padding: 10px; background: rgba(81, 207, 102, 0.2); border-radius: 5px; border-left: 4px solid #51cf66;">
                    <i class="fa fa-check-circle"></i> <strong>Fully Allocated!</strong> All payment amount has been allocated.
                </div>
            `}
        </div>
    `;
    
    if (frm.fields_dict.allocation_summary_html) {
        frm.fields_dict.allocation_summary_html.$wrapper.html(html);
    }
}

function get_company_currency(frm) {
    if (frm.doc.company) {
        frappe.db.get_value('Company', frm.doc.company, 'default_currency', function(r) {
            if (r && r.default_currency) {
                frm.doc.__company_currency = r.default_currency;
                
                // Set payment currency to company currency if not set
                if (!frm.doc.payment_currency) {
                    frm.set_value('payment_currency', r.default_currency);
                }
                
                // Refresh field visibility
                toggle_field_visibility(frm);
            }
        });
    }
}

function set_field_queries(frm) {
    // Account filters
    frm.set_query('account_to_debit', function() {
        return {
            filters: {
                company: frm.doc.company,
                is_group: 0,
                disabled: 0
            }
        };
    });
    
    frm.set_query('wht_account', function() {
        return {
            filters: {
                company: frm.doc.company,
                account_type: 'Tax',
                is_group: 0
            }
        };
    });
    
    // Bank account filter
    frm.set_query('remittance_bank', function() {
        return {
            filters: {
                company: frm.doc.company,
                is_company_account: 1
            }
        };
    });
    
    // Supplier filter
    frm.set_query('payee_id', function() {
        return {
            filters: {
                disabled: 0
            }
        };
    });
}

function toggle_field_visibility(frm) {
    // Get company currency dynamically
    let company_currency = frm.doc.__company_currency || 'NGN';
    
    // Currency amount fields
    let is_foreign = frm.doc.payment_currency !== company_currency;
    frm.toggle_display('amount_paid', !is_foreign);
    frm.toggle_display('amount_paid_in_fc', is_foreign);
    frm.toggle_display('exchange_rate', is_foreign);
    frm.toggle_reqd('amount_paid', !is_foreign);
    frm.toggle_reqd('amount_paid_in_fc', is_foreign);
    
    // Transaction type specific fields
    let is_expense = frm.doc.trans_type === 'Expense Payment';
    let is_supplier = frm.doc.trans_type === 'Supplier Payment';
    let show_beneficiary = ['Expense Payment', 'Transfer Out'].includes(frm.doc.trans_type);
    
    frm.toggle_display('payee_id', is_supplier);
    frm.toggle_display('payee_name', show_beneficiary);
    frm.toggle_display('account_to_debit', is_expense || frm.doc.trans_type === 'Transfer Out');
    frm.toggle_display('nature_of_expense', is_expense);
    frm.toggle_reqd('cost_center', is_expense);
    
    // WHT fields
    frm.toggle_display('section_break_r9iee', frm.doc.deduct_wht);
    frm.toggle_reqd('wht_account', frm.doc.deduct_wht);
    
    // Multi-line section
    frm.toggle_display('multi_line_transactions_section', frm.doc.is_multi_line);
    
    // Shared cost section
    frm.toggle_display('cost_center_distribution_section', frm.doc.is_shared_cost);
    
    // Related company section
    frm.toggle_display('related_company_transactions_section', frm.doc.is_related_coy_trans);
    
    // Amortization section
    frm.toggle_display('amortization_tab', frm.doc.amortize);
    
    // Supplier invoice tab
    frm.toggle_display('supplier_invoice_tab', is_supplier);
}

function calculate_local_currency_amount(frm) {
    if (frm.doc.amount_paid_in_fc && frm.doc.exchange_rate) {
        let local_amount = frm.doc.amount_paid_in_fc * frm.doc.exchange_rate;
        frm.set_value('local_currency_amount', local_amount);
    }
}

function calculate_wht(frm) {
    if (frm.doc.deduct_wht && frm.doc.whtax_rate && frm.doc.local_currency_amount) {
        let wht_amount = (frm.doc.local_currency_amount * frm.doc.whtax_rate) / 100;
        let net_amount = frm.doc.local_currency_amount - wht_amount;
        
        frm.set_value('wht_amount', wht_amount);
        frm.set_value('net_amount', net_amount);
    } else {
        frm.set_value('wht_amount', 0);
        frm.set_value('net_amount', frm.doc.local_currency_amount);
    }
}

function convert_amount_to_words(frm) {
    // Amount in words is now handled by the Python backend
    // The backend will automatically convert using frappe.utils.money_in_words
    // No need to call from JS - it will be set during validation
    frm.refresh_field('amount_in_words');
}

function fetch_exchange_rate(frm) {
    let company_currency = frm.doc.__company_currency || 'NGN';
    
    if (frm.doc.payment_currency && frm.doc.transaction_date && frm.doc.payment_currency !== company_currency) {
        frappe.call({
            method: 'erpnext.setup.utils.get_exchange_rate',
            args: {
                from_currency: frm.doc.payment_currency,
                to_currency: company_currency,
                transaction_date: frm.doc.transaction_date
            },
            callback: function(r) {
                if (r.message) {
                    frm.set_value('exchange_rate', r.message);
                }
            }
        });
    }
}

function calculate_total_allocated(frm) {
    let total = 0;
    if (frm.doc.payments_reference && frm.doc.payments_reference.length > 0) {
        frm.doc.payments_reference.forEach(function(row) {
            total += flt(row.allocated_amount);
        });
    }
    frm.set_value('total_outstanding_invoice', total);
}

function calculate_multi_line_total(frm) {
    let total = 0;
    if (frm.doc.payments_item_line && frm.doc.payments_item_line.length > 0) {
        frm.doc.payments_item_line.forEach(function(row) {
            total += flt(row.amount_in_lcy || row.amount);
        });
    }
    frm.set_value('total_multi_line_amount', total);
}

function calculate_total_distribution(frm) {
    let total = 0;
    if (frm.doc.cost_center_distribution && frm.doc.cost_center_distribution.length > 0) {
        frm.doc.cost_center_distribution.forEach(function(row) {
            total += flt(row.distribution);
        });
        
        frm.set_value('total_percentage', total);
        
        if (total !== 100) {
            frappe.msgprint(__('Total distribution must equal 100%'));
        }
    } else {
        frm.set_value('total_percentage', 0);
    }
}

function calculate_related_company_total(frm) {
    let total = 0;
    if (frm.doc.related_company_payments && frm.doc.related_company_payments.length > 0) {
        frm.doc.related_company_payments.forEach(function(row) {
            total += flt(row.amount_in_lcy || row.amount);
        });
    }
    frm.set_value('total_rcoy', total);
}

function calculate_all_totals(frm) {
    calculate_total_allocated(frm);
    calculate_multi_line_total(frm);
    calculate_total_distribution(frm);
    calculate_related_company_total(frm);
}

function populate_invoice_table(frm, invoices) {
    frm.clear_table('payments_reference');
    
    invoices.forEach(function(invoice) {
        let row = frm.add_child('payments_reference');
        row.reference_doctype = invoice.voucher_type;
        row.reference_name = invoice.voucher_no;
        row.due_date = invoice.due_date;
        row.total_amount = invoice.invoice_amount;
        row.outstanding_amount = invoice.outstanding_amount;
        row.allocated_amount = 0;
        row.exchange_rate = invoice.exchange_rate || 1;
    });
    
    frm.refresh_field('payments_reference');
}

function perform_smart_allocation(frm) {
    let available_amount = frm.doc.local_currency_amount;
    let remaining_amount = available_amount;
    
    // Sort by due date (oldest first)
    let invoices = frm.doc.payments_reference.sort(function(a, b) {
        return new Date(a.due_date) - new Date(b.due_date);
    });
    
    let invoices_matched = 0;
    
    invoices.forEach(function(row) {
        if (remaining_amount > 0) {
            if (remaining_amount >= row.outstanding_amount) {
                frappe.model.set_value(row.doctype, row.name, 'allocated_amount', row.outstanding_amount);
                remaining_amount -= row.outstanding_amount;
                invoices_matched++;
            } else {
                frappe.model.set_value(row.doctype, row.name, 'allocated_amount', remaining_amount);
                remaining_amount = 0;
                invoices_matched++;
            }
        }
    });
    
    frm.refresh_field('payments_reference');
    calculate_total_allocated(frm);
    update_allocation_summary(frm);
    
    // Show enhanced success message
    let total_allocated = available_amount - remaining_amount;
    let message = `
        <div style="padding: 15px; font-family: Arial, sans-serif;">
            <h4 style="color: #27ae60; margin-bottom: 15px;">
                <i class="fa fa-check-circle"></i> AI Allocation Completed Successfully!
            </h4>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Invoices Matched:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">${invoices_matched}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Total Allocated:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd; color: #27ae60; font-weight: bold;">
                        ${format_currency(total_allocated)}
                    </td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><strong>Remaining Amount:</strong></td>
                    <td style="padding: 8px; color: ${remaining_amount > 0 ? '#f39c12' : '#27ae60'}; font-weight: bold;">
                        ${format_currency(remaining_amount)}
                    </td>
                </tr>
            </table>
        </div>
    `;
    
    frappe.msgprint({
        title: __('AI Smart Allocation Results'),
        message: message,
        indicator: 'green'
    });
}

function display_allocation_summary(frm) {
    if (!frm.doc.payments_reference || frm.doc.payments_reference.length === 0) {
        return;
    }
    
    let html = `
        <div style="background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px;">
                <h4 style="margin: 0; font-size: 16px;">
                    <i class="fa fa-list-alt"></i> Invoice Allocation Details
                </h4>
            </div>
            <div class="table-responsive">
                <table class="table table-bordered table-sm" style="margin: 0;">
                    <thead style="background: #f8f9fa;">
                        <tr>
                            <th style="padding: 12px;">Invoice</th>
                            <th style="padding: 12px;">Due Date</th>
                            <th style="padding: 12px; text-align: right;">Outstanding</th>
                            <th style="padding: 12px; text-align: right;">Allocated</th>
                            <th style="padding: 12px; text-align: center;">Status</th>
                        </tr>
                    </thead>
                    <tbody>
    `;
    
    frm.doc.payments_reference.forEach(function(row, index) {
        if (row.allocated_amount > 0) {
            let percentage = (row.allocated_amount / row.outstanding_amount) * 100;
            let status_color = percentage >= 100 ? '#51cf66' : percentage > 0 ? '#ffd43b' : '#868e96';
            let status_text = percentage >= 100 ? 'Fully Paid' : percentage > 0 ? 'Partial' : 'Unpaid';
            
            html += `
                <tr style="background-color: ${index % 2 === 0 ? '#ffffff' : '#f8f9fa'};">
                    <td style="padding: 10px;">
                        <strong>${row.reference_name}</strong>
                    </td>
                    <td style="padding: 10px;">
                        ${frappe.datetime.str_to_user(row.due_date)}
                    </td>
                    <td style="padding: 10px; text-align: right;">
                        ${format_currency(row.outstanding_amount)}
                    </td>
                    <td style="padding: 10px; text-align: right;">
                        <strong style="color: #667eea;">${format_currency(row.allocated_amount)}</strong>
                    </td>
                    <td style="padding: 10px; text-align: center;">
                        <span style="background-color: ${status_color}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: bold;">
                            ${status_text}
                        </span>
                    </td>
                </tr>
            `;
        }
    });
    
    html += `
                    </tbody>
                </table>
            </div>
        </div>
    `;
    
    if (frm.get_field('allocation_summary_html')) {
        frm.get_field('allocation_summary_html').$wrapper.html(html);
    }
}

function validate_payment_data(frm) {
    // Validate amount
    let company_currency = frm.doc.__company_currency || 'NGN';
    let amount = frm.doc.payment_currency === company_currency ? frm.doc.amount_paid : frm.doc.amount_paid_in_fc;
    if (!amount || amount <= 0) {
        frappe.throw(__('Payment amount must be greater than zero'));
    }
}

function validate_invoice_allocation(frm) {
    if (frm.doc.payments_reference && frm.doc.payments_reference.length > 0) {
        let total_allocated = 0;
        frm.doc.payments_reference.forEach(function(row) {
            total_allocated += flt(row.allocated_amount);
        });
        
        if (total_allocated > frm.doc.local_currency_amount) {
            frappe.throw(__('Total allocated amount cannot exceed payment amount'));
        }
    }
}

function validate_multi_line_totals(frm) {
    if (frm.doc.payments_item_line && frm.doc.payments_item_line.length > 0) {
        if (Math.abs(frm.doc.total_multi_line_amount - frm.doc.local_currency_amount) > 0.01) {
            frappe.throw(__('Multi-line total must equal payment amount'));
        }
    }
}

function validate_cost_distribution(frm) {
    if (frm.doc.cost_center_distribution && frm.doc.cost_center_distribution.length > 0) {
        if (frm.doc.total_percentage !== 100) {
            frappe.throw(__('Total cost distribution must equal 100%'));
        }
    }
}

function validate_dates(frm) {
    if (frm.doc.start_date && frm.doc.end_date) {
        if (frappe.datetime.get_diff(frm.doc.end_date, frm.doc.start_date) < 0) {
            frappe.throw(__('End date cannot be before start date'));
        }
    }
}

function calculate_charge_per_period(frm) {
    if (frm.doc.local_currency_amount && frm.doc.no_of_days) {
        let charge = frm.doc.local_currency_amount / frm.doc.no_of_days;
        frm.set_value('charge_amount', charge);
    }
}

function calculate_amortization_schedule(frm) {
    if (!frm.doc.frequency || !frm.doc.start_date || !frm.doc.end_date || !frm.doc.local_currency_amount) {
        return;
    }
    
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.payments.payments.generate_amortization_schedule',
        args: {
            start_date: frm.doc.start_date,
            end_date: frm.doc.end_date,
            frequency: frm.doc.frequency,
            amount: frm.doc.local_currency_amount
        },
        callback: function(r) {
            if (r.message) {
                frm.clear_table('amortization_schedule');
                r.message.forEach(function(entry) {
                    let row = frm.add_child('amortization_schedule');
                    row.period_start = entry.start;
                    row.period_end = entry.end;
                    row.amount = entry.amount;
                });
                frm.refresh_field('amortization_schedule');
            }
        }
    });
}

function create_accounting_entries(frm) {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.payments.payments.create_accounting_entries_from_ui',
        args: {
            payment_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                frappe.msgprint({
                    title: __('Accounting Entries Created'),
                    message: __('Successfully created {0} accounting entries', [r.message.total_entries]),
                    indicator: 'green'
                });
                frm.reload_doc();
            }
        }
    });
}

function cancel_accounting_entries(frm) {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.payments.payments.cancel_accounting_entries_from_ui',
        args: {
            payment_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                frappe.msgprint({
                    title: __('Entries Cancelled'),
                    message: __('Successfully cancelled {0} accounting entries', [r.message.cancelled_count]),
                    indicator: 'orange'
                });
            }
        }
    });
}

function show_accounting_entries(frm) {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.payments.payments.get_linked_accounting_entries',
        args: {
            payment_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                let html = generate_accounting_entries_html(r.message);
                frm.get_field('accounting_entries_html').$wrapper.html(html);
                
                let links_html = generate_linked_documents_html(r.message);
                frm.get_field('linked_documents_html').$wrapper.html(links_html);
            }
        }
    });
}

function generate_accounting_entries_html(data) {
    let html = '<div class="table-responsive"><table class="table table-bordered">';
    html += '<thead><tr><th>Type</th><th>Document</th><th>Date</th><th>Amount</th><th>Status</th></tr></thead><tbody>';
    
    if (data.journal_entries) {
        data.journal_entries.forEach(function(je) {
            html += '<tr>';
            html += '<td>Journal Entry</td>';
            html += '<td><a href="/app/journal-entry/' + je.name + '">' + je.name + '</a></td>';
            html += '<td>' + frappe.datetime.str_to_user(je.posting_date) + '</td>';
            html += '<td>' + format_currency(je.total_debit) + '</td>';
            html += '<td>' + get_status_indicator(je.docstatus) + '</td>';
            html += '</tr>';
        });
    }
    
    if (data.payment_entries) {
        data.payment_entries.forEach(function(pe) {
            html += '<tr>';
            html += '<td>Payment Entry</td>';
            html += '<td><a href="/app/payment-entry/' + pe.name + '">' + pe.name + '</a></td>';
            html += '<td>' + frappe.datetime.str_to_user(pe.posting_date) + '</td>';
            html += '<td>' + format_currency(pe.paid_amount) + '</td>';
            html += '<td>' + get_status_indicator(pe.docstatus) + '</td>';
            html += '</tr>';
        });
    }
    
    html += '</tbody></table></div>';
    return html;
}

function generate_linked_documents_html(data) {
    let html = '<div class="alert alert-info">';
    html += '<strong>Linked Documents:</strong><br>';
    
    let total_entries = (data.journal_entries ? data.journal_entries.length : 0) + 
                       (data.payment_entries ? data.payment_entries.length : 0);
    
    html += 'Total Accounting Entries: ' + total_entries;
    html += '</div>';
    
    return html;
}

function get_status_indicator(docstatus) {
    if (docstatus === 0) {
        return '<span class="indicator grey">Draft</span>';
    } else if (docstatus === 1) {
        return '<span class="indicator green">Submitted</span>';
    } else if (docstatus === 2) {
        return '<span class="indicator red">Cancelled</span>';
    }
}

function setup_custom_buttons(frm) {
    if (frm.doc.docstatus === 1 && frm.doc.create_accounting_entries) {
        frm.add_custom_button(__('View Accounting Entries'), function() {
            show_accounting_entries(frm);
        });
    }
    
    if (frm.doc.docstatus === 0 && frm.doc.amortize) {
        frm.add_custom_button(__('Generate Schedule'), function() {
            calculate_amortization_schedule(frm);
        });
    }
}

function add_action_buttons(frm) {
    if (frm.doc.docstatus === 1) {
        // Add print button
        frm.page.set_inner_btn_group_as_primary(__('Print'));
        
        // Add email button
        frm.page.add_inner_button(__('Send Email'), function() {
            frappe.utils.send_email(frm);
        }, __('Actions'));
    }
}

function set_default_accounts(frm) {
    if (frm.doc.trans_type === 'Expense Payment' && frm.doc.company) {
        frappe.db.get_value('Company', frm.doc.company, 'default_expense_account', function(r) {
            if (r && r.default_expense_account && !frm.doc.account_to_debit) {
                frm.set_value('account_to_debit', r.default_expense_account);
            }
        });
    }
}

