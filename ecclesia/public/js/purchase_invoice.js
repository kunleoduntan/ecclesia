// ============================================================================
// PURCHASE INVOICE - CUSTOM CLIENT SCRIPT
// File: ecclesia/public/js/purchase_invoice.js
// ============================================================================

// Helper function for float conversion
const flt = (value, precision = 2) => parseFloat(value || 0);

// ============================================================================
// MAIN FORM HANDLERS
// ============================================================================

frappe.ui.form.on("Purchase Invoice", {
    onload: function(frm) {
        // Set account filters
        frm.set_query("custom_deferred_expense_account", function() {
            return { 
                filters: { 
                    is_group: 0, 
                    company: frm.doc.company,
                    account_type: ["in", ["Payable", "Expense Account" ,"Capital Work in Progress", "Current Asset", ""]] 
                } 
            };
        });
        
        frm.set_query("custom_expense_account", function() {
            return { 
                filters: { 
                    is_group: 0,
                    company: frm.doc.company,
                    account_type: ["in", ["Payable", "Expense Account" ,"Capital Work in Progress", "Current Asset"]] 
                } 
            };
        });
    },

    supplier: function(frm) {
        if (!frm.doc.supplier) return;
        load_supplier_transaction_history(frm);
    },

    before_save: function(frm) {
        // Calculate transaction history balances
        if (frm.doc.custom_transaction_history && frm.doc.custom_transaction_history.length) {
            calculate_transaction_balances(frm);
        }
        
        // Calculate amortization schedule
        if (frm.doc.custom_is_amortized_cost) {
            calculate_amortization_schedule(frm);
        }
        
        // Validate cost center distribution
        if (frm.doc.custom_is_shared_cost && frm.doc.custom_cost_center_distribution && frm.doc.custom_cost_center_distribution.length) {
            let total = 0;
            frm.doc.custom_cost_center_distribution.forEach(row => {
                total += flt(row.distribution);
            });
            
            if (Math.abs(total - 100) > 0.01) {
                frappe.msgprint({
                    message: __('Warning: Total cost center distribution is {0}%, not 100%', [total.toFixed(2)]),
                    indicator: 'orange'
                });
            }
        }
    },

    refresh: function(frm) {
        calculate_age_in_days(frm);
        apply_zebra_striping(frm);
        add_custom_buttons(frm);
    },

    custom_is_amortized_cost: function(frm) {
        toggle_amortization_fields(frm);
        if (frm.doc.custom_is_amortized_cost) {
            if (frm.doc.posting_date && !frm.doc.custom_start_date) {
                frm.set_value('custom_start_date', frm.doc.posting_date);
            }
            update_amortization_calculation(frm);
        }
    },
    
    custom_is_shared_cost: function(frm) {
        if (frm.doc.custom_is_shared_cost && (!frm.doc.custom_cost_center_distribution || !frm.doc.custom_cost_center_distribution.length)) {
            frappe.msgprint(__('Please add cost center distribution'));
        }
    },

    custom_frequency: function(frm) {
        if (frm.doc.custom_is_amortized_cost) {
            update_amortization_calculation(frm);
        }
    },
    
    custom_no_of_periods: function(frm) {
        if (frm.doc.custom_is_amortized_cost) {
            update_amortization_calculation(frm);
        }
    },
    
    posting_date: function(frm) {
        if (frm.doc.custom_is_amortized_cost && frm.doc.posting_date) {
            if (!frm.doc.custom_start_date) {
                frm.set_value('custom_start_date', frm.doc.posting_date);
            }
            update_amortization_calculation(frm);
        }
    },
    
    total: function(frm) {
        if (frm.doc.custom_is_amortized_cost) {
            update_amortization_calculation(frm);
        }
    },
    
    base_total: function(frm) {
        if (frm.doc.custom_is_amortized_cost) {
            update_amortization_calculation(frm);
        }
    },
    
    custom_deferred_expense_account: function(frm) {
        // Update expense account for all items
        if (frm.doc.items && frm.doc.items.length && frm.doc.custom_deferred_expense_account) {
            frm.doc.items.forEach(item => {
                frappe.model.set_value(item.doctype, item.name, "expense_account", frm.doc.custom_deferred_expense_account);
            });
        }
    }
});

// ============================================================================
// COST CENTER DISTRIBUTION HANDLERS
// ============================================================================

frappe.ui.form.on("Cost Center Distribution", {
    distribution: function(frm, cdt, cdn) {
        calculate_total_distribution(frm);
    },
    
    custom_cost_center_distribution_add: function(frm) {
        calculate_total_distribution(frm);
    },
    
    custom_cost_center_distribution_remove: function(frm) {
        calculate_total_distribution(frm);
    }
});

// ============================================================================
// ITEM HANDLERS
// ============================================================================

frappe.ui.form.on("Purchase Invoice Item", {
    items_add: function(frm) {
        setTimeout(() => update_item_description(frm), 300);
    },
    
    description: function(frm, cdt, cdn) {
        setTimeout(() => update_item_description(frm), 300);
    }
});

// ============================================================================
// SUPPLIER TRANSACTION HISTORY
// ============================================================================

function load_supplier_transaction_history(frm) {
    // Clear existing data
    frm.clear_table("custom_transaction_history");

    // Fetch Purchase Invoices
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Purchase Invoice",
            filters: {
                supplier: frm.doc.supplier,
                docstatus: ["in", [0, 1]],
                name: ["!=", frm.doc.name || "New Purchase Invoice 1"]
            },
            fields: ["name", "supplier", "supplier_name", "grand_total", "posting_date"],
            order_by: "posting_date desc",
            limit: 100
        },
        callback: function(r) {
            if (r.message && r.message.length) {
                r.message.forEach(invoice => {
                    let row = frm.add_child("custom_transaction_history");
                    row.supplier = invoice.supplier;
                    row.trans_date = invoice.posting_date;
                    row.supplier_name = invoice.supplier_name;
                    row.trans_description = `Purchase Invoice ${invoice.name}`;
                    row.invoice_amount = invoice.grand_total;
                    row.paid_amount = 0.0;
                    row.balance = invoice.grand_total;
                    row.reference = invoice.name;
                });
                frm.refresh_field("custom_transaction_history");
            }
        }
    });

    // Fetch Payment Entries
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Payment Entry",
            filters: {
                party: frm.doc.supplier,
                party_type: "Supplier",
                docstatus: ["in", [0, 1]]
            },
            fields: ["name", "party", "party_name", "paid_amount", "posting_date"],
            order_by: "posting_date desc",
            limit: 100
        },
        callback: function(r) {
            if (r.message && r.message.length) {
                r.message.forEach(payment => {
                    let row = frm.add_child("custom_transaction_history");
                    row.supplier = payment.party;
                    row.trans_date = payment.posting_date;
                    row.supplier_name = payment.party_name;
                    row.trans_description = `Payment Entry ${payment.name}`;
                    row.invoice_amount = 0.0;
                    row.paid_amount = payment.paid_amount;
                    row.balance = -payment.paid_amount;
                    row.reference = payment.name;
                });
                frm.refresh_field("custom_transaction_history");
                calculate_age_in_days(frm);
            }
        }
    });
}

function calculate_transaction_balances(frm) {
    if (!frm.doc.custom_transaction_history || !frm.doc.custom_transaction_history.length) {
        return;
    }

    let balance = flt(frm.doc.custom_opening_balance);
    let total_purchase = 0;
    let total_paid = 0;

    frm.doc.custom_transaction_history.forEach(row => {
        total_purchase += flt(row.invoice_amount);
        total_paid += flt(row.paid_amount);
        balance += flt(row.invoice_amount) - flt(row.paid_amount);
        row.balance = balance;
    });

    frm.set_value("cum_paid_amount", total_paid);
    frm.set_value("total_purchases", total_purchase);
    frm.set_value("balance", balance);
}

function calculate_age_in_days(frm) {
    if (!frm.doc.custom_transaction_history || !frm.doc.custom_transaction_history.length) {
        return;
    }
    
    let today = frappe.datetime.now_date();
    frm.doc.custom_transaction_history.forEach(row => {
        if (row.trans_date) {
            let age = frappe.datetime.get_diff(today, row.trans_date);
            row.age_in_days = age;
        }
    });
    frm.refresh_field("custom_transaction_history");
}

// ============================================================================
// AMORTIZATION CALCULATIONS
// ============================================================================

function update_amortization_calculation(frm) {
    if (!frm.doc.custom_is_amortized_cost || !frm.doc.custom_frequency) {
        return;
    }
    
    if (!frm.doc.posting_date) {
        return;
    }
    
    let freq = frm.doc.custom_frequency;
    let periods = 1;
    let next_schedule = 1;
    let end_days = 365;

    switch (freq) {
        case 'Monthly':
            periods = frm.doc.custom_no_of_periods || 12;
            next_schedule = 1;
            end_days = periods * 30;
            break;
        case 'Quarterly':
            periods = 4;
            next_schedule = 3;
            end_days = 365;
            break;
        case 'Half-Yearly':
            periods = 2;
            next_schedule = 6;
            end_days = 365;
            break;
        case 'Yearly':
            periods = 1;
            next_schedule = 12;
            end_days = 365;
            break;
        case 'Freehand':
            periods = frm.doc.custom_no_of_periods || 1;
            next_schedule = 1;
            end_days = periods * 30;
            break;
        default:
            return;
    }

    let base_total = flt(frm.doc.base_total || frm.doc.total);
    if (base_total === 0) {
        return;
    }

    let charged_amount = base_total / periods;
    
    frm.set_value('custom_charged_amount', charged_amount);
    frm.set_value('custom_no_of_periods', periods);
    frm.set_value('custom_next_schedule', next_schedule);
    
    if (!frm.doc.custom_start_date) {
        frm.set_value('custom_start_date', frm.doc.posting_date);
    }
    
    if (frm.doc.custom_start_date) {
        frm.set_value('custom_end_date', frappe.datetime.add_days(frm.doc.custom_start_date, end_days));
        frm.set_value('custom_next_posting_date', frappe.datetime.add_months(frm.doc.custom_start_date, next_schedule));
    }
}

function calculate_amortization_schedule(frm) {
    if (!frm.doc.custom_is_amortized_cost) {
        return;
    }
    
    if (!frm.doc.custom_charged_amount || !frm.doc.custom_start_date || !frm.doc.custom_no_of_periods) {
        return;
    }

    frm.clear_table("custom_amortization_schedule");

    let periods = frm.doc.custom_no_of_periods;
    let amount_per_period = flt(frm.doc.custom_charged_amount);
    let total_amount = amount_per_period * periods;
    let remaining_balance = total_amount;

    for (let i = 0; i < periods; i++) {
        let posting_date = frappe.datetime.add_months(
            frm.doc.custom_start_date, 
            i * (frm.doc.custom_next_schedule || 1)
        );

        remaining_balance -= amount_per_period;

        let row = frm.add_child("custom_amortization_schedule");
        row.date = posting_date;
        row.title = frm.doc.supplier_name || '';
        row.amount = amount_per_period;
        row.transaction_description = frm.doc.custom_description || '';
        row.frequency = frm.doc.custom_frequency;
        row.period = periods;
        row.account_to_debit = frm.doc.custom_expense_account || '';
        row.account_to_credit = frm.doc.custom_deferred_expense_account || '';
        row.source_doc = "Purchase Invoice";
        row.source_doc_ref = frm.doc.name;
        row.prepayment_balance = remaining_balance > 0 ? remaining_balance : 0;
    }

    frm.refresh_field("custom_amortization_schedule");
}

function update_item_description(frm) {
    if (!frm.doc.items || !frm.doc.items.length) {
        return;
    }
    
    if (frm.doc.custom_description) {
        return; // Don't overwrite existing description
    }
    
    let first_item = frm.doc.items[0];
    if (first_item && first_item.description) {
        frm.set_value('custom_description', `Amortisation of ${first_item.description}`);
    }
}

// ============================================================================
// COST CENTER DISTRIBUTION
// ============================================================================

function calculate_total_distribution(frm) {
    let total = 0;
    (frm.doc.custom_cost_center_distribution || []).forEach(row => {
        total += flt(row.distribution);
    });
    frm.set_value('custom_total_percentage', total);
    
    if (Math.abs(total - 100) > 0.01) {
        frappe.msgprint({
            message: __('Total distribution should be 100%. Current total: {0}%', [total.toFixed(2)]),
            indicator: 'orange'
        });
    }
}

function get_cost_center_distribution(frm) {
    frappe.prompt([
        {
            'fieldname': 'company',
            'fieldtype': 'Link',
            'label': 'Company',
            'options': 'Company',
            'reqd': 1,
            'default': frm.doc.company
        }
    ], function(values) {
        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: 'Company',
                name: values.company
            },
            callback: function(r) {
                if (r.message && r.message.custom_cost_center_distribution) {
                    frm.clear_table('custom_cost_center_distribution');
                    r.message.custom_cost_center_distribution.forEach(row => {
                        let new_row = frm.add_child('custom_cost_center_distribution');
                        new_row.title = row.title;
                        new_row.cost_center = row.cost_center;
                        new_row.distribution = row.distribution;
                    });
                    frm.refresh_field('custom_cost_center_distribution');
                    calculate_total_distribution(frm);
                    frappe.msgprint(__('Cost Center Distribution populated successfully'));
                } else {
                    frappe.msgprint(__('No cost center distribution found for this company'));
                }
            }
        });
    }, __('Select Company'), __('Get Distribution'));
}

// ============================================================================
// UI HELPERS
// ============================================================================

function toggle_amortization_fields(frm) {
    let is_amortized = frm.doc.custom_is_amortized_cost;
    
    // Hide stock-related fields for amortized costs
    ['scan_barcode', 'update_stock', 'is_subcontracted', 'total_qty'].forEach(field => {
        frm.set_df_property(field, 'hidden', is_amortized ? 1 : 0);
    });
    
    // Make cost center required for amortization
    if (!frm.doc.custom_is_shared_cost) {
        frm.set_df_property('cost_center', 'reqd', is_amortized ? 1 : 0);
    }
}

function apply_zebra_striping(frm) {
    setTimeout(() => {
        // Transaction history
        if (frm.fields_dict.custom_transaction_history) {
            frm.fields_dict.custom_transaction_history.grid.wrapper.find('.grid-row').each(function(i, row) {
                $(row).css('background-color', i % 2 === 0 ? '#ffffff' : '#e9ffdb');
            });
        }
        
        // Amortization schedule
        if (frm.fields_dict.custom_amortization_schedule) {
            frm.fields_dict.custom_amortization_schedule.grid.wrapper.find('.grid-row').each(function(i, row) {
                $(row).css('background-color', i % 2 === 0 ? '#ffffff' : '#e9ffdb');
            });
        }
        
        // Items
        if (frm.fields_dict.items) {
            frm.fields_dict.items.grid.wrapper.find('.grid-row').each(function(i, row) {
                $(row).css('background-color', i % 2 === 0 ? '#ffffff' : '#e9ffdb');
            });
        }
        
        // Cost center distribution
        if (frm.fields_dict.custom_cost_center_distribution) {
            frm.fields_dict.custom_cost_center_distribution.grid.wrapper.find('.grid-row').each(function(i, row) {
                $(row).css('background-color', i % 2 === 0 ? '#ffffff' : '#FFFFCC');
            });
        }
    }, 500);
}

function add_custom_buttons(frm) {
    // Get CC Distribution button
    if (frm.doc.custom_is_shared_cost && frm.doc.docstatus === 0) {
        frm.add_custom_button(__('Get CC Sharing'), function() {
            get_cost_center_distribution(frm);
        });
    }
    
    // Create Amortization Entries button
    if (frm.doc.custom_is_amortized_cost && frm.doc.docstatus === 1) {
        frm.add_custom_button(__('Create Amortization Entries'), function() {
            create_amortization_entries(frm);
        }, __('Actions'));
    }
    
    // Print Amortization Schedule
    if (frm.doc.custom_is_amortized_cost && frm.doc.custom_amortization_schedule && frm.doc.custom_amortization_schedule.length) {
        frm.add_custom_button(__('Print Amortization Schedule'), function() {
            print_amortization_schedule(frm);
        }, __('Print'));
    }
    
    // Print Cost Sharing
    if (frm.doc.custom_is_shared_cost && frm.doc.custom_cost_center_distribution && frm.doc.custom_cost_center_distribution.length) {
        frm.add_custom_button(__('Print Cost Sharing'), function() {
            print_cost_sharing(frm);
        }, __('Print'));
    }
}

// ============================================================================
// SERVER CALLS
// ============================================================================

function create_amortization_entries(frm) {
    frappe.confirm(
        __('This will create {0} journal entries. Continue?', [frm.doc.custom_no_of_periods]),
        function() {
            frappe.call({
                method: 'ecclesia.api.purchase_invoice.create_amortization_entries',
                args: {
                    purchase_invoice: frm.doc.name
                },
                freeze: true,
                freeze_message: __('Creating Amortization Entries...'),
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.msgprint({
                            title: __('Success'),
                            message: __('Created {0} amortization entries successfully', [r.message.entries_created]),
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    }
                }
            });
        }
    );
}

function print_amortization_schedule(frm) {
    frappe.call({
        method: 'ecclesia.api.purchase_invoice.generate_amortization_html',
        args: {
            purchase_invoice: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                let print_window = window.open('', '_blank');
                print_window.document.write(r.message);
                print_window.document.close();
            }
        }
    });
}

function print_cost_sharing(frm) {
    frappe.call({
        method: 'ecclesia.api.purchase_invoice.generate_cost_sharing_html',
        args: {
            purchase_invoice: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                let print_window = window.open('', '_blank');
                print_window.document.write(r.message);
                print_window.document.close();
            }
        }
    });
}