// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt


frappe.ui.form.on('Fixed Asset Revaluation', {
    refresh: function(frm) {
        add_revaluation_buttons(frm);
        set_status_indicators(frm);
        show_revaluation_summary(frm);
        setup_filters(frm);
    },
    
    onload: function(frm) {
        setup_filters(frm);
        
        if (frm.is_new() && !frm.doc.revaluation_date) {
            frm.set_value('revaluation_date', frappe.datetime.get_today());
        }
    },
    
    company: function(frm) {
        frm.set_value('asset', '');
    },
    
    asset: function(frm) {
        if (frm.doc.asset) {
            fetch_asset_details(frm);
        } else {
            clear_asset_fields(frm);
        }
    },
    
    current_gross_value: function(frm) {
        calculate_current_net_book_value(frm);
        calculate_revaluation_amount(frm);
    },
    
    current_accumulated_depreciation: function(frm) {
        calculate_current_net_book_value(frm);
    },
    
    new_gross_value: function(frm) {
        calculate_revaluation_amount(frm);
        validate_new_value(frm);
    },
    
    revaluation_amount: function(frm) {
        determine_revaluation_type(frm);
        calculate_percentage_change(frm);
        update_visual_indicators(frm);
    },
    
    revaluation_method: function(frm) {
        toggle_method_fields(frm);
        update_method_description(frm);
    }
});

function add_revaluation_buttons(frm) {
    if (frm.doc.docstatus === 1) {
        // View Journal Entry
        if (frm.doc.journal_entry) {
            frm.add_custom_button(__('View Journal Entry'), function() {
                frappe.set_route('Form', 'Journal Entry', frm.doc.journal_entry);
            }, __('View'));
        }
        
        // View Asset
        frm.add_custom_button(__('View Asset'), function() {
            frappe.set_route('Form', 'Fixed Asset', frm.doc.asset);
        }, __('View'));
        
        // Revaluation History
        if (frm.doc.asset) {
            frm.add_custom_button(__('Revaluation History'), function() {
                show_revaluation_history(frm);
            }, __('View'));
        }
    }
}

function set_status_indicators(frm) {
    if (!frm.doc.revaluation_type) return;
    
    const type_colors = {
        'Upward Revaluation': 'green',
        'Downward Revaluation': 'red',
        'No Change': 'gray'
    };
    
    if (frm.doc.revaluation_type && frm.doc.docstatus === 1) {
        frm.page.set_indicator(
            frm.doc.revaluation_type, 
            type_colors[frm.doc.revaluation_type] || 'blue'
        );
    }
}

function show_revaluation_summary(frm) {
    if (!frm.doc.docstatus) return;
    
    frm.dashboard.clear_headline();
    
    // Show revaluation amount
    if (frm.doc.revaluation_amount) {
        let color = flt(frm.doc.revaluation_amount) > 0 ? 'green' : 'red';
        frm.dashboard.add_indicator(
            __('Revaluation Amount: {0}', [format_currency(Math.abs(frm.doc.revaluation_amount))]), 
            color
        );
    }
    
    // Show percentage change
    if (frm.doc.percentage_change) {
        let pct_color = flt(frm.doc.percentage_change) > 0 ? 'green' : 'red';
        frm.dashboard.add_indicator(
            __('Change: {0}%', [flt(frm.doc.percentage_change).toFixed(2)]), 
            pct_color
        );
    }
    
    // Show current net book value
    if (frm.doc.current_net_book_value) {
        frm.dashboard.add_indicator(
            __('Current NBV: {0}', [format_currency(frm.doc.current_net_book_value)]), 
            'blue'
        );
    }
}

function fetch_asset_details(frm) {
    if (!frm.doc.asset) return;
    
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.fixed_asset_revaluation.fixed_asset_revaluation.get_asset_for_revaluation',
        args: {
            asset: frm.doc.asset
        },
        callback: function(r) {
            if (r.message) {
                frm.set_value('asset_code', r.message.asset_code);
                frm.set_value('asset_name', r.message.asset_name);
                frm.set_value('asset_category', r.message.asset_category);
                frm.set_value('current_gross_value', r.message.current_gross_value);
                frm.set_value('current_accumulated_depreciation', r.message.current_accumulated_depreciation);
                frm.set_value('current_location', r.message.current_location);
                frm.set_value('department', r.message.department);
                
                // Auto-suggest new value (same as current for user to adjust)
                if (!frm.doc.new_gross_value) {
                    frm.set_value('new_gross_value', r.message.current_gross_value);
                }
                
                frappe.show_alert({
                    message: __('✓ Asset details loaded'),
                    indicator: 'green'
                }, 3);
                
                // Calculate values
                calculate_current_net_book_value(frm);
            }
        }
    });
}

function clear_asset_fields(frm) {
    frm.set_value('asset_code', '');
    frm.set_value('asset_name', '');
    frm.set_value('asset_category', '');
    frm.set_value('current_gross_value', 0);
    frm.set_value('current_accumulated_depreciation', 0);
    frm.set_value('current_net_book_value', 0);
    frm.set_value('current_location', '');
    frm.set_value('department', '');
}

function calculate_current_net_book_value(frm) {
    if (!frm.doc.current_gross_value) return;
    
    let nbv = flt(frm.doc.current_gross_value) - flt(frm.doc.current_accumulated_depreciation);
    frm.set_value('current_net_book_value', nbv);
}

function calculate_revaluation_amount(frm) {
    if (!frm.doc.current_gross_value || !frm.doc.new_gross_value) return;
    
    let revaluation = flt(frm.doc.new_gross_value) - flt(frm.doc.current_gross_value);
    frm.set_value('revaluation_amount', revaluation);
}

function calculate_percentage_change(frm) {
    if (!frm.doc.current_gross_value || flt(frm.doc.current_gross_value) === 0) return;
    
    let pct = (flt(frm.doc.revaluation_amount) / flt(frm.doc.current_gross_value)) * 100;
    frm.set_value('percentage_change', pct);
}

function determine_revaluation_type(frm) {
    if (!frm.doc.revaluation_amount) return;
    
    let type = '';
    if (flt(frm.doc.revaluation_amount) > 0) {
        type = 'Upward Revaluation';
    } else if (flt(frm.doc.revaluation_amount) < 0) {
        type = 'Downward Revaluation';
    } else {
        type = 'No Change';
    }
    
    frm.set_value('revaluation_type', type);
}

function validate_new_value(frm) {
    if (!frm.doc.new_gross_value || !frm.doc.current_gross_value) return;
    
    let change_pct = Math.abs((flt(frm.doc.revaluation_amount) / flt(frm.doc.current_gross_value)) * 100);
    
    if (change_pct > 50) {
        frappe.msgprint({
            title: __('⚠️ Large Revaluation'),
            message: __('The revaluation represents a {0}% change in value. Please ensure this is accurate and properly documented.', 
                [change_pct.toFixed(1)]),
            indicator: 'orange'
        });
    }
}

function update_visual_indicators(frm) {
    if (!frm.doc.revaluation_amount) return;
    
    // Clear previous comments
    frm.dashboard.clear_comment();
    
    if (flt(frm.doc.revaluation_amount) > 0) {
        frm.dashboard.add_comment(
            __('📈 Asset value will increase by {0} ({1}%)', [
                format_currency(frm.doc.revaluation_amount),
                flt(frm.doc.percentage_change).toFixed(2)
            ]),
            'green',
            true
        );
    } else if (flt(frm.doc.revaluation_amount) < 0) {
        frm.dashboard.add_comment(
            __('📉 Asset value will decrease by {0} ({1}%)', [
                format_currency(Math.abs(frm.doc.revaluation_amount)),
                Math.abs(flt(frm.doc.percentage_change)).toFixed(2)
            ]),
            'red',
            true
        );
    }
}

function toggle_method_fields(frm) {
    let method = frm.doc.revaluation_method;
    
    if (['Market Value', 'Professional Valuation'].includes(method)) {
        frm.set_df_property('valuer_appraiser', 'reqd', 1);
    } else {
        frm.set_df_property('valuer_appraiser', 'reqd', 0);
    }
    
    if (method === 'Professional Valuation') {
        frm.set_df_property('valuation_report_reference', 'reqd', 1);
    } else {
        frm.set_df_property('valuation_report_reference', 'reqd', 0);
    }
}

function update_method_description(frm) {
    if (!frm.doc.revaluation_method) return;
    
    let descriptions = {
        'Market Value': 'Current market price of similar assets in active markets',
        'Replacement Cost': 'Cost to replace the asset with a similar one at current prices',
        'Fair Value': 'Price that would be received to sell the asset in an orderly transaction',
        'Indexed Cost': 'Original cost adjusted by relevant price indices',
        'Professional Valuation': 'Independent professional appraisal of the asset value',
        'Insurance Valuation': 'Value based on insurance replacement cost assessment'
    };
    
    if (descriptions[frm.doc.revaluation_method]) {
        frm.set_df_property('revaluation_method', 'description', 
            __(descriptions[frm.doc.revaluation_method]));
    }
}

function show_revaluation_history(frm) {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.fixed_asset_revaluation.fixed_asset_revaluation.get_revaluation_history',
        args: {
            asset: frm.doc.asset
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                let html = '<div style="max-height: 500px; overflow-y: auto;">';
                html += '<table class="table table-bordered"><thead><tr>';
                html += '<th>Date</th><th>Method</th><th>Previous Value</th><th>New Value</th><th>Change</th><th>% Change</th><th>Type</th>';
                html += '</tr></thead><tbody>';
                
                $.each(r.message, function(i, record) {
                    let type_class = record.revaluation_type === 'Upward Revaluation' ? 'text-success' : 'text-danger';
                    let change_icon = flt(record.revaluation_amount) > 0 ? '▲' : '▼';
                    
                    html += `<tr>
                        <td><a href="/app/fixed-asset-revaluation/${record.name}">${frappe.datetime.str_to_user(record.revaluation_date)}</a></td>
                        <td>${record.revaluation_method}</td>
                        <td>${format_currency(record.current_gross_value)}</td>
                        <td>${format_currency(record.new_gross_value)}</td>
                        <td class="${type_class}">${change_icon} ${format_currency(Math.abs(record.revaluation_amount))}</td>
                        <td class="${type_class}">${flt(record.percentage_change).toFixed(2)}%</td>
                        <td>${record.revaluation_type}</td>
                    </tr>`;
                });
                
                html += '</tbody></table></div>';
                
                frappe.msgprint({
                    title: __('Revaluation History - {0}', [frm.doc.asset_name]),
                    message: html,
                    wide: true
                });
            } else {
                frappe.msgprint(__('No revaluation history found for this asset'));
            }
        }
    });
}

function setup_filters(frm) {
    frm.set_query('asset', function() {
        return {
            filters: {
                'docstatus': 0,
                'asset_status': ['not in', ['Disposed', 'Sold', 'Scrapped']],
                'company': frm.doc.company
            }
        };
    });
    
    frm.set_query('revaluation_reserve_account', function() {
        return {
            filters: {
                'company': frm.doc.company,
                'account_type': 'Equity',
                'is_group': 0
            }
        };
    });
    
    frm.set_query('revaluation_surplus_loss_account', function() {
        return {
            filters: {
                'company': frm.doc.company,
                'is_group': 0
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
}

// Helper function
function format_currency(value) {
    return frappe.format(value, {fieldtype: 'Currency'});
}