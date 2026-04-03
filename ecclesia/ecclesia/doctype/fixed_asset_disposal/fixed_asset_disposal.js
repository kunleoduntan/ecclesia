// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt

// ecclesia/ecclesia/doctype/fixed_asset_disposal/fixed_asset_disposal.js

frappe.ui.form.on('Fixed Asset Disposal', {
    refresh: function(frm) {
        // Add custom buttons
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__('Fetch Asset Details'), function() {
                frm.trigger('fetch_asset_details');
            });
            
            frm.add_custom_button(__('Calculate Gain/Loss'), function() {
                frm.trigger('calculate_profit_loss');
            });
        }
        
        if (frm.doc.docstatus === 1 && !frm.doc.journal_entry) {
            frm.add_custom_button(__('Create Journal Entry'), function() {
                frm.trigger('make_journal_entry');
            }, __('Create'));
        }
        
        // Set queries
        frm.set_query('asset', function() {
            return {
                filters: {
                    'company': frm.doc.company,
                    'docstatus': 1,
                    'status': ['in', ['Submitted', 'Partially Depreciated', 'Fully Depreciated']]
                }
            };
        });
        
        frm.set_query('cost_center', function() {
            return {
                filters: {
                    'company': frm.doc.company,
                    'is_group': 0
                }
            };
        });
        
        // Color code disposal type
        if (frm.doc.disposal_type) {
            const color_map = {
                'Sale': 'green',
                'Scrap': 'orange',
                'Donation': 'blue',
                'Lost/Stolen': 'red',
                'Write Off': 'darkred',
                'Trade-In': 'purple'
            };
            frm.set_df_property('disposal_type', 'description', 
                `<span style="color: ${color_map[frm.doc.disposal_type] || 'black'}">
                    ${frm.doc.disposal_type}
                </span>`
            );
        }
    },
    
    company: function(frm) {
        frm.set_value('asset', '');
    },
    
    asset: function(frm) {
        if (frm.doc.asset) {
            frm.trigger('fetch_asset_details');
        }
    },
    
    fetch_asset_details: function(frm) {
        if (!frm.doc.asset) {
            frappe.msgprint(__('Please select an asset first'));
            return;
        }
        
        frappe.call({
            method: 'ecclesia.ecclesia.doctype.fixed_asset_disposal.fixed_asset_disposal.get_asset_details',
            args: {
                asset: frm.doc.asset,
                disposal_date: frm.doc.disposal_date,
                finance_book: frm.doc.finance_book
            },
            callback: function(r) {
                if (r.message) {
                    // Set asset basic info
                    frm.set_value('asset_code', r.message.asset_code);
                    frm.set_value('asset_name', r.message.asset_name);
                    frm.set_value('asset_category', r.message.asset_category);
                    frm.set_value('asset_location', r.message.location);
                    
                    // Set financial info
                    frm.set_value('original_purchase_value', r.message.gross_purchase_amount);
                    frm.set_value('accumulated_depreciation', r.message.accumulated_depreciation);
                    frm.set_value('current_book_value', r.message.value_after_depreciation);
                    
                    // Set accounting dimensions
                    frm.set_value('cost_center', r.message.cost_center);
                    
                    // Auto-calculate on fetch
                    frm.trigger('calculate_profit_loss');
                    
                    frappe.show_alert({
                        message: __('Asset details fetched successfully'),
                        indicator: 'green'
                    });
                }
            }
        });
    },
    
    disposal_date: function(frm) {
        if (frm.doc.asset && frm.doc.disposal_date) {
            frm.trigger('fetch_asset_details');
        }
    },
    
    disposal_type: function(frm) {
        // Auto-set disposal proceeds to 0 for certain types
        if (['Scrap', 'Lost/Stolen', 'Write Off'].includes(frm.doc.disposal_type)) {
            if (!frm.doc.disposal_proceeds) {
                frm.set_value('disposal_proceeds', 0);
            }
        }
    },
    
    disposal_proceeds: function(frm) {
        frm.trigger('calculate_amounts');
    },
    
    disposal_expenses: function(frm) {
        frm.trigger('calculate_amounts');
    },
    
    calculate_amounts: function(frm) {
        // Calculate net disposal amount
        let net_amount = flt(frm.doc.disposal_proceeds) - flt(frm.doc.disposal_expenses);
        frm.set_value('net_disposal_amount', net_amount);
        
        // Trigger profit/loss calculation
        frm.trigger('calculate_profit_loss');
    },
    
    calculate_profit_loss: function(frm) {
        if (!frm.doc.current_book_value) {
            frappe.msgprint(__('Please fetch asset details first'));
            return;
        }
        
        // Calculate gain or loss
        let book_value = flt(frm.doc.current_book_value);
        let net_disposal = flt(frm.doc.net_disposal_amount);
        let profit_loss = net_disposal - book_value;
        
        frm.set_value('gain_loss_on_disposal', profit_loss);
        
        // Set transaction type
        if (profit_loss > 0) {
            frm.set_value('transaction_type', 'Gain on Disposal');
        } else if (profit_loss < 0) {
            frm.set_value('transaction_type', 'Loss on Disposal');
        } else {
            frm.set_value('transaction_type', 'No Gain/Loss');
        }
        
        // Show visual indicator
        if (profit_loss !== 0) {
            frappe.show_alert({
                message: profit_loss > 0 ? 
                    __('Gain on Disposal: {0}', [format_currency(profit_loss, frm.doc.currency)]) :
                    __('Loss on Disposal: {0}', [format_currency(Math.abs(profit_loss), frm.doc.currency)]),
                indicator: profit_loss > 0 ? 'green' : 'orange'
            });
        }
    },
    
    check_profit_button: function(frm) {
        frm.trigger('calculate_profit_loss');
    },
    
    make_journal_entry: function(frm) {
        if (!frm.doc.asset) {
            frappe.msgprint(__('Asset is required'));
            return;
        }
        
        frappe.call({
            method: 'ecclesia.ecclesia.doctype.fixed_asset_disposal.fixed_asset_disposal.make_journal_entry',
            args: {
                disposal_doc: frm.doc.name
            },
            callback: function(r) {
                if (r.message) {
                    frappe.model.sync(r.message);
                    frappe.set_route('Form', r.message.doctype, r.message.name);
                }
            }
        });
    },
    
    buyer_name: function(frm) {
        // Auto-fill buyer details section when buyer is entered
        if (frm.doc.buyer_name) {
            frm.scroll_to_field('buyer_contact');
        }
    }
});

// Helper function for currency formatting
function format_currency(value, currency) {
    return frappe.format(value, {fieldtype: 'Currency', options: currency});
}