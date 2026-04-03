// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt



frappe.ui.form.on('Fixed Asset Lease', {
    refresh: function(frm) {
        // Add custom buttons
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__('Calculate Lease Values'), function() {
                frm.trigger('calculate_lease_values');
            });
            
            frm.add_custom_button(__('Generate Payment Schedule'), function() {
                frm.trigger('generate_payment_schedule');
            });
        }
        
        if (frm.doc.docstatus === 1) {
            // Journal entry button for finance lease
            if (frm.doc.lease_classification === 'Finance Lease' && !frm.doc.journal_entry) {
                frm.add_custom_button(__('Create Initial JE'), function() {
                    frm.trigger('create_initial_journal_entry');
                }, __('Create'));
            }
            
            // Payment entry button
            if (frm.doc.lease_status === 'Active') {
                frm.add_custom_button(__('Record Payment'), function() {
                    frm.trigger('record_payment');
                }, __('Create'));
            }
            
            // Terminate lease button
            if (['Active', 'Grace Period'].includes(frm.doc.lease_status)) {
                frm.add_custom_button(__('Terminate Lease'), function() {
                    frm.trigger('terminate_lease');
                }, __('Actions'));
            }
            
            // Renew lease button
            if (frm.doc.lease_status === 'Expiring Soon') {
                frm.add_custom_button(__('Renew Lease'), function() {
                    frm.trigger('renew_lease');
                }, __('Actions'));
            }
        }
        
        // Set field queries
        frm.set_query('asset', function() {
            return {
                filters: {
                    'company': frm.doc.company,
                    'docstatus': 0,
                    'asset_status': ['not in', ['Sold', 'Scrapped', 'Disposed']]
                }
            };
        });
        
        frm.set_query('lessor', function() {
            if (frm.doc.lease_type === 'Lease In (We are Lessee)') {
                return {
                    filters: {
                        'supplier_type': 'Company'
                    }
                };
            }
        });
        
        frm.set_query('lessee', function() {
            if (frm.doc.lease_type === 'Lease Out (We are Lessor)') {
                return {
                    filters: {
                        'customer_type': 'Company'
                    }
                };
            }
        });
        
        frm.set_query('cost_center', function() {
            return {
                filters: {
                    'company': frm.doc.company,
                    'is_group': 0
                }
            };
        });
        
        // Show status indicators
        frm.trigger('show_status_indicators');
        
        // Show lease classification explanation
        frm.trigger('show_classification_info');
        
        // Calculate and show key metrics
        frm.trigger('show_lease_metrics');
    },
    
    setup: function(frm) {
        // Set default values
        if (frm.is_new()) {
            frm.set_value('lease_classification', 'Operating Lease');
            frm.set_value('lease_status', 'Draft');
            frm.set_value('payment_frequency', 'Monthly');
            frm.set_value('depreciation_method', 'Straight Line');
        }
    },
    
    company: function(frm) {
        frm.set_value('asset', '');
    },
    
    lease_type: function(frm) {
        // Show/hide relevant fields based on lease type
        if (frm.doc.lease_type === 'Lease In (We are Lessee)') {
            frm.set_df_property('lessor', 'hidden', 0);
            frm.set_df_property('lessee', 'hidden', 1);
            frm.set_df_property('lessor', 'reqd', 1);
            frm.set_df_property('lessee', 'reqd', 0);
            frm.set_value('lessee', '');
            
            // Show depreciation fields for finance lease
            if (frm.doc.lease_classification === 'Finance Lease') {
                frm.set_df_property('depreciation_section', 'hidden', 0);
            }
        } else if (frm.doc.lease_type === 'Lease Out (We are Lessor)') {
            frm.set_df_property('lessor', 'hidden', 1);
            frm.set_df_property('lessee', 'hidden', 0);
            frm.set_df_property('lessor', 'reqd', 0);
            frm.set_df_property('lessee', 'reqd', 1);
            frm.set_value('lessor', '');
            
            // Hide depreciation fields
            frm.set_df_property('depreciation_section', 'hidden', 1);
        }
        
        // Re-evaluate classification
        frm.trigger('evaluate_lease_classification');
    },
    
    asset: function(frm) {
        if (frm.doc.asset) {
            frm.trigger('fetch_asset_details');
        }
    },
    
    fetch_asset_details: function(frm) {
        if (!frm.doc.asset) {
            return;
        }
        
        frappe.call({
            method: 'ecclesia.ecclesia.doctype.fixed_asset_lease.fixed_asset_lease.get_asset_details',
            args: {
                asset: frm.doc.asset
            },
            callback: function(r) {
                if (r.message) {
                    frm.set_value('asset_code', r.message.asset_code);
                    frm.set_value('asset_name', r.message.asset_name);
                    frm.set_value('asset_category', r.message.asset_category);
                    
                    if (r.message.cost_center) {
                        frm.set_value('cost_center', r.message.cost_center);
                    }
                    
                    // Set fair value for lease evaluation
                    frm.set_value('asset_fair_value', r.message.current_value);
                    
                    frappe.show_alert({
                        message: __('Asset details loaded'),
                        indicator: 'green'
                    });
                }
            }
        });
    },
    
    lease_start_date: function(frm) {
        frm.trigger('calculate_lease_end_date');
        frm.trigger('update_lease_status');
    },
    
    lease_term_months: function(frm) {
        frm.trigger('calculate_lease_end_date');
        frm.trigger('calculate_number_of_payments');
        frm.trigger('evaluate_lease_classification');
    },
    
    calculate_lease_end_date: function(frm) {
        if (frm.doc.lease_start_date && frm.doc.lease_term_months) {
            frappe.call({
                method: 'frappe.utils.add_months',
                args: {
                    date: frm.doc.lease_start_date,
                    months: frm.doc.lease_term_months
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('lease_end_date', r.message);
                    }
                }
            });
        }
    },
    
    payment_frequency: function(frm) {
        frm.trigger('calculate_number_of_payments');
    },
    
    calculate_number_of_payments: function(frm) {
        if (frm.doc.lease_term_months && frm.doc.payment_frequency) {
            let frequency_months = {
                'Monthly': 1,
                'Quarterly': 3,
                'Semi-Annual': 6,
                'Annual': 12
            };
            
            let months = frequency_months[frm.doc.payment_frequency] || 1;
            let num_payments = Math.floor(frm.doc.lease_term_months / months);
            
            frm.set_value('number_of_payments', num_payments);
        }
    },
    
    lease_payment_amount: function(frm) {
        frm.trigger('calculate_total_lease_payments');
    },
    
    number_of_payments: function(frm) {
        frm.trigger('calculate_total_lease_payments');
    },
    
    calculate_total_lease_payments: function(frm) {
        if (frm.doc.lease_payment_amount && frm.doc.number_of_payments) {
            let total = flt(frm.doc.lease_payment_amount) * flt(frm.doc.number_of_payments);
            frm.set_value('total_lease_payments', total);
            
            // Trigger lease classification evaluation
            frm.trigger('evaluate_lease_classification');
        }
    },
    
    residual_value: function(frm) {
        frm.trigger('evaluate_lease_classification');
        frm.trigger('calculate_present_value');
    },
    
    discount_rate: function(frm) {
        frm.trigger('calculate_present_value');
    },
    
    evaluate_lease_classification: function(frm) {
        // Auto-classify lease based on criteria
        if (!frm.doc.lease_term_months || !frm.doc.asset_fair_value) {
            return;
        }
        
        let is_finance_lease = false;
        let reasons = [];
        
        // Test 1: Ownership transfer
        if (frm.doc.ownership_transfer_at_end) {
            is_finance_lease = true;
            reasons.push('Ownership transfers at end of lease');
        }
        
        // Test 2: Bargain purchase option
        if (frm.doc.bargain_purchase_option) {
            is_finance_lease = true;
            reasons.push('Bargain purchase option exists');
        }
        
        // Test 3: Lease term >= 75% of economic life
        if (frm.doc.asset_useful_life_months) {
            let lease_percentage = (flt(frm.doc.lease_term_months) / flt(frm.doc.asset_useful_life_months)) * 100;
            if (lease_percentage >= 75) {
                is_finance_lease = true;
                reasons.push(`Lease term is ${lease_percentage.toFixed(1)}% of asset's economic life (≥75%)`);
            }
        }
        
        // Test 4: PV of lease payments >= 90% of fair value
        if (frm.doc.present_value_of_lease_payments && frm.doc.asset_fair_value) {
            let pv_percentage = (flt(frm.doc.present_value_of_lease_payments) / flt(frm.doc.asset_fair_value)) * 100;
            if (pv_percentage >= 90) {
                is_finance_lease = true;
                reasons.push(`PV of payments is ${pv_percentage.toFixed(1)}% of fair value (≥90%)`);
            }
        }
        
        // Test 5: Asset is specialized
        if (frm.doc.asset_is_specialized) {
            is_finance_lease = true;
            reasons.push('Asset is specialized with no alternative use');
        }
        
        // Set classification
        let new_classification = is_finance_lease ? 'Finance Lease' : 'Operating Lease';
        
        // Only update if classification changed
        if (frm.doc.lease_classification !== new_classification) {
            frm.set_value('lease_classification', new_classification);
            
            // Store classification reasons
            if (reasons.length > 0) {
                frm.set_value('classification_notes', 'Finance Lease Criteria Met:\n' + reasons.join('\n'));
            }
            
            // Show result
            if (is_finance_lease) {
                frappe.show_alert({
                    message: __('Classified as Finance Lease'),
                    indicator: 'blue'
                });
            }
        }
    },
    
    calculate_lease_values: function(frm) {
        if (!frm.doc.lease_payment_amount || !frm.doc.number_of_payments) {
            frappe.msgprint(__('Please enter lease payment details first'));
            return;
        }
        
        if (!frm.doc.discount_rate) {
            frappe.msgprint(__('Please enter discount rate'));
            return;
        }
        
        frappe.call({
            method: 'ecclesia.ecclesia.doctype.fixed_asset_lease.fixed_asset_lease.calculate_lease_values',
            args: {
                doc: frm.doc
            },
            callback: function(r) {
                if (r.message) {
                    frm.set_value('present_value_of_lease_payments', r.message.present_value);
                    frm.set_value('total_interest_expense', r.message.total_interest);
                    
                    // Re-evaluate classification
                    frm.trigger('evaluate_lease_classification');
                    
                    frappe.show_alert({
                        message: __('Lease values calculated'),
                        indicator: 'green'
                    });
                }
            }
        });
    },
    
    calculate_present_value: function(frm) {
        if (!frm.doc.lease_payment_amount || !frm.doc.number_of_payments || !frm.doc.discount_rate) {
            return;
        }
        
        // Calculate PV based on payment frequency
        let frequency_periods = {
            'Monthly': 12,
            'Quarterly': 4,
            'Semi-Annual': 2,
            'Annual': 1
        };
        
        let periods_per_year = frequency_periods[frm.doc.payment_frequency] || 12;
        let rate = flt(frm.doc.discount_rate) / 100 / periods_per_year;
        let n = flt(frm.doc.number_of_payments);
        let pmt = flt(frm.doc.lease_payment_amount);
        
        let pv = 0;
        if (rate > 0) {
            pv = pmt * ((1 - Math.pow(1 + rate, -n)) / rate);
        } else {
            pv = pmt * n;
        }
        
        // Add residual value PV if applicable
        if (frm.doc.residual_value && rate > 0) {
            pv += flt(frm.doc.residual_value) / Math.pow(1 + rate, n);
        }
        
        frm.set_value('present_value_of_lease_payments', pv);
        
        // Calculate total interest
        let total_interest = flt(frm.doc.total_lease_payments) - pv;
        frm.set_value('total_interest_expense', total_interest);
    },
    
    lease_classification: function(frm) {
        frm.trigger('show_classification_info');
        
        // Show/hide depreciation fields
        if (frm.doc.lease_classification === 'Finance Lease' && 
            frm.doc.lease_type === 'Lease In (We are Lessee)') {
            frm.set_df_property('depreciation_section', 'hidden', 0);
        } else {
            frm.set_df_property('depreciation_section', 'hidden', 1);
        }
    },
    
    show_classification_info: function(frm) {
        if (!frm.doc.lease_classification) {
            return;
        }
        
        // Clear previous comments
        frm.dashboard.clear_comment();
        
        if (frm.doc.lease_classification === 'Finance Lease') {
            frm.dashboard.add_comment(
                __('Finance Lease: Asset is capitalized and depreciated. Lease liability is recognized.'), 
                'blue', 
                true
            );
        } else if (frm.doc.lease_classification === 'Operating Lease') {
            frm.dashboard.add_comment(
                __('Operating Lease: Lease payments are expensed. No asset/liability recognition.'), 
                'green', 
                true
            );
        }
    },
    
    depreciation_method: function(frm) {
        if (frm.doc.depreciation_method && frm.doc.useful_life_months) {
            frm.trigger('calculate_depreciation');
        }
    },
    
    useful_life_months: function(frm) {
        if (frm.doc.depreciation_method && frm.doc.useful_life_months) {
            frm.trigger('calculate_depreciation');
        }
    },
    
    present_value_of_lease_payments: function(frm) {
        if (frm.doc.lease_classification === 'Finance Lease' && 
            frm.doc.lease_type === 'Lease In (We are Lessee)') {
            frm.trigger('calculate_depreciation');
        }
    },
    
    calculate_depreciation: function(frm) {
        if (frm.doc.lease_classification !== 'Finance Lease' || 
            frm.doc.lease_type !== 'Lease In (We are Lessee)') {
            return;
        }
        
        if (!frm.doc.present_value_of_lease_payments || !frm.doc.useful_life_months) {
            return;
        }
        
        let depreciable_amount = flt(frm.doc.present_value_of_lease_payments) - flt(frm.doc.residual_value);
        let months = flt(frm.doc.useful_life_months);
        
        if (frm.doc.depreciation_method === 'Straight Line' && months > 0) {
            let monthly_dep = depreciable_amount / months;
            frm.set_value('monthly_depreciation', monthly_dep);
        }
    },
    
    generate_payment_schedule: function(frm) {
        if (!frm.doc.lease_payment_amount || !frm.doc.number_of_payments || !frm.doc.lease_start_date) {
            frappe.msgprint(__('Please enter lease payment amount, number of payments, and lease start date'));
            return;
        }
        
        frappe.call({
            method: 'ecclesia.ecclesia.doctype.fixed_asset_lease.fixed_asset_lease.generate_payment_schedule',
            args: {
                doc: frm.doc
            },
            callback: function(r) {
                if (r.message && r.message.length > 0) {
                    // Clear existing schedule
                    frm.clear_table('lease_payment_schedule');
                    
                    // Add new schedule
                    r.message.forEach(function(payment) {
                        let row = frm.add_child('lease_payment_schedule');
                        row.payment_number = payment.payment_number;
                        row.payment_date = payment.payment_date;
                        row.payment_amount = payment.payment_amount;
                        row.principal_amount = payment.principal_amount;
                        row.interest_amount = payment.interest_amount;
                        row.outstanding_balance = payment.outstanding_balance;
                        row.payment_status = payment.payment_status || 'Pending';
                    });
                    
                    frm.refresh_field('lease_payment_schedule');
                    
                    frappe.show_alert({
                        message: __('Payment schedule generated with {0} payments', [r.message.length]),
                        indicator: 'green'
                    });
                } else {
                    frappe.msgprint(__('No payment schedule generated'));
                }
            }
        });
    },
    
    create_initial_journal_entry: function(frm) {
        if (frm.doc.lease_classification !== 'Finance Lease') {
            frappe.msgprint(__('Initial JE is only for Finance Leases'));
            return;
        }
        
        if (!frm.doc.right_of_use_asset_account || !frm.doc.lease_liability_account) {
            frappe.msgprint(__('Please set Right-of-Use Asset and Lease Liability accounts'));
            return;
        }
        
        frappe.call({
            method: 'ecclesia.ecclesia.doctype.fixed_asset_lease.fixed_asset_lease.create_initial_journal_entry',
            args: {
                lease_doc: frm.doc.name
            },
            callback: function(r) {
                if (r.message) {
                    frappe.model.sync(r.message);
                    frappe.set_route('Form', r.message.doctype, r.message.name);
                    frappe.show_alert({
                        message: __('Initial journal entry created'),
                        indicator: 'green'
                    });
                }
            }
        });
    },
    
    record_payment: function(frm) {
        // Find next pending payment
        let next_payment = null;
        if (frm.doc.lease_payment_schedule) {
            for (let row of frm.doc.lease_payment_schedule) {
                if (row.payment_status === 'Pending') {
                    next_payment = row;
                    break;
                }
            }
        }
        
        if (!next_payment) {
            frappe.msgprint(__('No pending payments found'));
            return;
        }
        
        let d = new frappe.ui.Dialog({
            title: __('Record Lease Payment'),
            fields: [
                {
                    fieldname: 'payment_date',
                    fieldtype: 'Date',
                    label: __('Payment Date'),
                    reqd: 1,
                    default: next_payment.payment_date || frappe.datetime.get_today()
                },
                {
                    fieldname: 'payment_amount',
                    fieldtype: 'Currency',
                    label: __('Payment Amount'),
                    reqd: 1,
                    default: next_payment.payment_amount || frm.doc.lease_payment_amount,
                    read_only: 1
                },
                {
                    fieldname: 'payment_mode',
                    fieldtype: 'Link',
                    label: __('Mode of Payment'),
                    options: 'Mode of Payment',
                    reqd: 1
                },
                {
                    fieldname: 'payment_reference',
                    fieldtype: 'Data',
                    label: __('Payment Reference')
                }
            ],
            primary_action_label: __('Record Payment'),
            primary_action: function(values) {
                frappe.call({
                    method: 'ecclesia.ecclesia.doctype.fixed_asset_lease.fixed_asset_lease.record_lease_payment',
                    args: {
                        lease_doc: frm.doc.name,
                        payment_details: values
                    },
                    callback: function(r) {
                        if (r.message) {
                            frm.reload_doc();
                            d.hide();
                            frappe.show_alert({
                                message: __('Payment recorded successfully'),
                                indicator: 'green'
                            });
                        }
                    }
                });
            }
        });
        d.show();
    },
    
    terminate_lease: function(frm) {
        frappe.prompt([
            {
                fieldname: 'termination_date',
                fieldtype: 'Date',
                label: __('Termination Date'),
                reqd: 1,
                default: frappe.datetime.get_today()
            },
            {
                fieldname: 'termination_reason',
                fieldtype: 'Small Text',
                label: __('Reason for Termination'),
                reqd: 1
            },
            {
                fieldname: 'early_termination_penalty',
                fieldtype: 'Currency',
                label: __('Early Termination Penalty'),
                default: 0
            }
        ], function(values) {
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.fixed_asset_lease.fixed_asset_lease.terminate_lease',
                args: {
                    doc_name: frm.doc.name,
                    termination_details: values
                },
                callback: function(r) {
                    if (r.message) {
                        frm.reload_doc();
                        frappe.show_alert({
                            message: __('Lease terminated'),
                            indicator: 'red'
                        });
                    }
                }
            });
        }, __('Terminate Lease'), __('Terminate'));
    },
    
    renew_lease: function(frm) {
        frappe.call({
            method: 'ecclesia.ecclesia.doctype.fixed_asset_lease.fixed_asset_lease.renew_lease',
            args: {
                source_name: frm.doc.name
            },
            callback: function(r) {
                if (r.message) {
                    frappe.model.sync(r.message);
                    frappe.set_route('Form', r.message.doctype, r.message.name);
                    frappe.show_alert({
                        message: __('Lease renewal created'),
                        indicator: 'green'
                    });
                }
            }
        });
    },
    
    update_lease_status: function(frm) {
        if (frm.doc.lease_start_date && frm.doc.lease_end_date && frm.doc.docstatus === 1) {
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.fixed_asset_lease.fixed_asset_lease.update_lease_status',
                args: {
                    doc_name: frm.doc.name
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('lease_status', r.message);
                    }
                }
            });
        }
    },
    
    show_status_indicators: function(frm) {
        // Color code lease status
        const status_colors = {
            'Draft': 'gray',
            'Active': 'green',
            'Expiring Soon': 'orange',
            'Expired': 'red',
            'Terminated': 'darkred',
            'Renewed': 'blue',
            'Grace Period': 'yellow',
            'Cancelled': 'darkgray'
        };
        
        if (frm.doc.lease_status && frm.fields_dict.lease_status) {
            let color = status_colors[frm.doc.lease_status] || 'gray';
            frm.set_df_property('lease_status', 'description',
                `<span style="color: ${color}; font-weight: bold;">
                    ${frm.doc.lease_status}
                </span>`
            );
        }
        
        // Color code lease classification
        const class_colors = {
            'Finance Lease': 'blue',
            'Operating Lease': 'green'
        };
        
        if (frm.doc.lease_classification && frm.fields_dict.lease_classification) {
            let color = class_colors[frm.doc.lease_classification] || 'gray';
            frm.set_df_property('lease_classification', 'description',
                `<span style="color: ${color}; font-weight: bold;">
                    ${frm.doc.lease_classification}
                </span>`
            );
        }
    },
    
    show_lease_metrics: function(frm) {
        if (!frm.doc.docstatus || frm.doc.docstatus === 0) {
            return;
        }
        
        // Clear previous indicators
        frm.dashboard.clear_headline();
        
        // Calculate and show key metrics
        if (frm.doc.total_lease_payments) {
            frm.dashboard.add_indicator(__('Total Payments: {0}', 
                [format_currency(frm.doc.total_lease_payments, frm.doc.currency)]), 'blue');
        }
        
        if (frm.doc.present_value_of_lease_payments) {
            frm.dashboard.add_indicator(__('Present Value: {0}', 
                [format_currency(frm.doc.present_value_of_lease_payments, frm.doc.currency)]), 'green');
        }
        
        // Show payment progress
        if (frm.doc.lease_payment_schedule && frm.doc.lease_payment_schedule.length > 0) {
            let total_payments = frm.doc.lease_payment_schedule.length;
            let paid_payments = frm.doc.lease_payment_schedule.filter(p => p.payment_status === 'Paid').length;
            
            let progress = (paid_payments / total_payments) * 100;
            let indicator_color = progress > 75 ? 'green' : progress > 50 ? 'orange' : 'blue';
            
            frm.dashboard.add_indicator(__('Payment Progress: {0}% ({1}/{2})', 
                [progress.toFixed(1), paid_payments, total_payments]), 
                indicator_color);
        }
    }
});

// Child table: Lease Payment Schedule
frappe.ui.form.on('Lease Payment Schedule', {
    payment_status: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        if (row.payment_status === 'Paid' && !row.actual_payment_date) {
            frappe.model.set_value(cdt, cdn, 'actual_payment_date', frappe.datetime.get_today());
        }
    }
});

// Helper function
function format_currency(value, currency) {
    if (!currency) {
        currency = frappe.defaults.get_default('currency') || 'USD';
    }
    return frappe.format(value, {fieldtype: 'Currency', options: currency});
}