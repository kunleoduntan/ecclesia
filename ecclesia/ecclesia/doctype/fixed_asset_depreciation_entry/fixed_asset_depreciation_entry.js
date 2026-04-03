// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt

// ecclesia/ecclesia/doctype/fixed_asset_depreciation_entry/fixed_asset_depreciation_entry.js

frappe.ui.form.on('Fixed Asset Depreciation Entry', {
    refresh: function(frm) {
        // Add custom buttons based on status
        if (frm.doc.docstatus === 0) {
            // Get Assets button
            frm.add_custom_button(__('Get Assets'), function() {
                frm.trigger('get_assets_for_depreciation');
            }, __('Actions'));
            
            // Preview button
            if (frm.doc.depreciation_entries && frm.doc.depreciation_entries.length > 0) {
                frm.add_custom_button(__('Preview Journal Entry'), function() {
                    frm.trigger('preview_journal_entry');
                }, __('Actions'));
            }
            
            // Clear all button
            if (frm.doc.depreciation_entries && frm.doc.depreciation_entries.length > 0) {
                frm.add_custom_button(__('Clear All Assets'), function() {
                    frm.trigger('clear_all_assets');
                }, __('Actions'));
            }
        }
        
        if (frm.doc.docstatus === 1) {
            // View journal entry button
            if (frm.doc.journal_entry) {
                frm.add_custom_button(__('View Journal Entry'), function() {
                    frappe.set_route('Form', 'Journal Entry', frm.doc.journal_entry);
                }, __('View'));
            }
            
            // Create another depreciation entry
            frm.add_custom_button(__('Create New'), function() {
                frm.trigger('create_new_entry');
            }, __('Actions'));
        }
        
        // Set field queries
        frm.set_query('asset_category', function() {
            return {
                filters: {
                    'enable_depreciation': 1
                }
            };
        });
        
        frm.set_query('location', function() {
            return {
                filters: {
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
        
        frm.set_query('department', function() {
            return {
                filters: {
                    'company': frm.doc.company
                }
            };
        });
        
        // Show status indicators
        frm.trigger('show_status_indicators');
        
        // Show summary statistics
        frm.trigger('show_summary_stats');
        
        // Highlight overdue depreciation
        if (frm.doc.docstatus === 0) {
            frm.trigger('highlight_overdue');
        }
    },
    
    setup: function(frm) {
        // Set default posting date
        if (!frm.doc.posting_date) {
            frm.set_value('posting_date', frappe.datetime.get_today());
        }
    },
    
    company: function(frm) {
        // Clear filters when company changes
        frm.set_value('asset_category', '');
        frm.set_value('location', '');
        frm.set_value('department', '');
        frm.set_value('cost_center', '');
        frm.clear_table('depreciation_entries');
        frm.refresh_field('depreciation_entries');
    },
    
    period_start_date: function(frm) {
        frm.trigger('validate_period_dates');
        
        // Auto-set period end date to end of month if not set
        if (frm.doc.period_start_date && !frm.doc.period_end_date) {
            let start_date = frappe.datetime.str_to_obj(frm.doc.period_start_date);
            let end_date = new Date(start_date.getFullYear(), start_date.getMonth() + 1, 0);
            frm.set_value('period_end_date', frappe.datetime.obj_to_str(end_date));
        }
    },
    
    period_end_date: function(frm) {
        frm.trigger('validate_period_dates');
    },
    
    validate_period_dates: function(frm) {
        if (frm.doc.period_start_date && frm.doc.period_end_date) {
            if (frappe.datetime.get_day_diff(frm.doc.period_end_date, frm.doc.period_start_date) < 0) {
                frappe.msgprint(__('Period End Date cannot be before Period Start Date'));
                frm.set_value('period_end_date', '');
            }
        }
    },
    
    posting_date: function(frm) {
        if (frm.doc.posting_date && frm.doc.period_end_date) {
            if (frappe.datetime.get_day_diff(frm.doc.posting_date, frm.doc.period_end_date) < 0) {
                frappe.msgprint({
                    title: __('Warning'),
                    message: __('Posting Date should typically be on or after Period End Date'),
                    indicator: 'orange'
                });
            }
        }
    },
    
    get_assets_button: function(frm) {
        frm.trigger('get_assets_for_depreciation');
    },
    
    get_assets_for_depreciation: function(frm) {
        // Validate required fields
        if (!frm.doc.company) {
            frappe.msgprint(__('Please select Company'));
            return;
        }
        
        if (!frm.doc.period_start_date || !frm.doc.period_end_date) {
            frappe.msgprint(__('Please select Period Start Date and Period End Date'));
            return;
        }
        
        // Show loading indicator
        frappe.dom.freeze(__('Fetching assets for depreciation...'));
        
        // Prepare filters
        let filters = {
            company: frm.doc.company,
            period_start_date: frm.doc.period_start_date,
            period_end_date: frm.doc.period_end_date,
            posting_date: frm.doc.posting_date,
            finance_book: frm.doc.finance_book,
            asset_category: frm.doc.asset_category,
            location: frm.doc.location,
            department: frm.doc.department,
            cost_center: frm.doc.cost_center
        };
        
        // Call server method
        frappe.call({
            method: 'ecclesia.ecclesia.doctype.fixed_asset_depreciation_entry.fixed_asset_depreciation_entry.get_assets_for_depreciation',
            args: {
                filters: filters
            },
            callback: function(r) {
                frappe.dom.unfreeze();
                
                if (r.message && r.message.length > 0) {
                    // Clear existing entries
                    frm.clear_table('depreciation_entries');
                    
                    // Add new entries
                    r.message.forEach(function(asset) {
                        let row = frm.add_child('depreciation_entries');
                        row.asset = asset.asset;
                        row.asset_name = asset.asset_name;
                        row.asset_category = asset.asset_category;
                        row.schedule_date = asset.schedule_date;
                        row.depreciation_amount = asset.depreciation_amount;
                        row.accumulated_depreciation_before = asset.accumulated_depreciation_before;
                        row.accumulated_depreciation_after = asset.accumulated_depreciation_after;
                        row.book_value_before = asset.book_value_before;
                        row.book_value_after = asset.book_value_after;
                        row.depreciation_account = asset.depreciation_account;
                        row.accumulated_depreciation_account = asset.accumulated_depreciation_account;
                        row.cost_center = asset.cost_center;
                    });
                    
                    frm.refresh_field('depreciation_entries');
                    
                    // Calculate totals
                    frm.trigger('calculate_totals');
                    
                    // Show success message
                    frappe.show_alert({
                        message: __('Loaded {0} assets for depreciation', [r.message.length]),
                        indicator: 'green'
                    }, 5);
                    
                } else {
                    frappe.msgprint({
                        title: __('No Assets Found'),
                        message: __('No assets found with pending depreciation for the selected period and filters.'),
                        indicator: 'orange'
                    });
                }
            },
            error: function(r) {
                frappe.dom.unfreeze();
                frappe.msgprint({
                    title: __('Error'),
                    message: __('Failed to fetch assets. Please check your filters and try again.'),
                    indicator: 'red'
                });
            }
        });
    },
    
    preview_journal_entry: function(frm) {
        if (!frm.doc.depreciation_entries || frm.doc.depreciation_entries.length === 0) {
            frappe.msgprint(__('No depreciation entries to preview'));
            return;
        }
        
        // Group entries by accounts and cost center
        let account_groups = {};
        
        frm.doc.depreciation_entries.forEach(function(entry) {
            let key = entry.depreciation_account + '|' + 
                     entry.accumulated_depreciation_account + '|' + 
                     entry.cost_center;
            
            if (!account_groups[key]) {
                account_groups[key] = {
                    depreciation_account: entry.depreciation_account,
                    accumulated_depreciation_account: entry.accumulated_depreciation_account,
                    cost_center: entry.cost_center,
                    amount: 0,
                    asset_count: 0
                };
            }
            
            account_groups[key].amount += flt(entry.depreciation_amount);
            account_groups[key].asset_count += 1;
        });
        
        // Build preview HTML
        let html = '<div class="row">';
        html += '<div class="col-md-12">';
        html += '<h4>Journal Entry Preview</h4>';
        html += '<table class="table table-bordered">';
        html += '<thead><tr>';
        html += '<th>Account</th>';
        html += '<th>Cost Center</th>';
        html += '<th style="text-align: right;">Debit</th>';
        html += '<th style="text-align: right;">Credit</th>';
        html += '<th>Assets</th>';
        html += '</tr></thead><tbody>';
        
        let total_debit = 0;
        let total_credit = 0;
        
        // Add debit entries
        Object.values(account_groups).forEach(function(group) {
            html += '<tr>';
            html += '<td>' + group.depreciation_account + '</td>';
            html += '<td>' + group.cost_center + '</td>';
            html += '<td style="text-align: right; font-weight: bold;">' + 
                   format_currency(group.amount) + '</td>';
            html += '<td style="text-align: right;">-</td>';
            html += '<td>' + group.asset_count + '</td>';
            html += '</tr>';
            total_debit += group.amount;
        });
        
        // Add credit entries
        Object.values(account_groups).forEach(function(group) {
            html += '<tr>';
            html += '<td>' + group.accumulated_depreciation_account + '</td>';
            html += '<td>' + group.cost_center + '</td>';
            html += '<td style="text-align: right;">-</td>';
            html += '<td style="text-align: right; font-weight: bold;">' + 
                   format_currency(group.amount) + '</td>';
            html += '<td>' + group.asset_count + '</td>';
            html += '</tr>';
            total_credit += group.amount;
        });
        
        // Add totals row
        html += '<tr style="background-color: #f5f5f5; font-weight: bold;">';
        html += '<td colspan="2">Total</td>';
        html += '<td style="text-align: right;">' + format_currency(total_debit) + '</td>';
        html += '<td style="text-align: right;">' + format_currency(total_credit) + '</td>';
        html += '<td>' + frm.doc.depreciation_entries.length + '</td>';
        html += '</tr>';
        
        html += '</tbody></table>';
        html += '</div></div>';
        
        // Show in dialog
        let d = new frappe.ui.Dialog({
            title: __('Journal Entry Preview'),
            size: 'large',
            fields: [
                {
                    fieldname: 'preview',
                    fieldtype: 'HTML',
                    options: html
                }
            ],
            primary_action_label: __('Close'),
            primary_action: function() {
                d.hide();
            }
        });
        
        d.show();
    },
    
    clear_all_assets: function(frm) {
        frappe.confirm(
            __('Are you sure you want to clear all assets from this entry?'),
            function() {
                frm.clear_table('depreciation_entries');
                frm.refresh_field('depreciation_entries');
                frm.trigger('calculate_totals');
                
                frappe.show_alert({
                    message: __('All assets cleared'),
                    indicator: 'orange'
                });
            }
        );
    },
    
    calculate_totals: function(frm) {
        if (!frm.doc.depreciation_entries || frm.doc.depreciation_entries.length === 0) {
            frm.set_value('total_assets', 0);
            frm.set_value('total_depreciation_amount', 0);
            frm.set_value('total_accumulated_depreciation', 0);
            return;
        }
        
        let total_assets = frm.doc.depreciation_entries.length;
        let total_depreciation = 0;
        let total_accumulated = 0;
        
        frm.doc.depreciation_entries.forEach(function(entry) {
            total_depreciation += flt(entry.depreciation_amount);
            total_accumulated += flt(entry.accumulated_depreciation_after);
        });
        
        frm.set_value('total_assets', total_assets);
        frm.set_value('total_depreciation_amount', total_depreciation);
        frm.set_value('total_accumulated_depreciation', total_accumulated);
    },
    
    show_status_indicators: function(frm) {
        // Color code status
        const status_colors = {
            'Draft': 'gray',
            'Submitted': 'blue',
            'Posted': 'green',
            'Cancelled': 'red'
        };
        
        if (frm.doc.status) {
            frm.set_df_property('status', 'description',
                `<span style="color: ${status_colors[frm.doc.status]}; font-weight: bold;">
                    ${frm.doc.status}
                </span>`
            );
        }
    },
    
    show_summary_stats: function(frm) {
        if (!frm.doc.docstatus || !frm.doc.depreciation_entries) {
            return;
        }
        
        // Show statistics on dashboard
        if (frm.doc.total_assets > 0) {
            frm.dashboard.add_indicator(__('Assets: {0}', [frm.doc.total_assets]), 'blue');
        }
        
        if (frm.doc.total_depreciation_amount > 0) {
            frm.dashboard.add_indicator(__('Depreciation: {0}', 
                [format_currency(frm.doc.total_depreciation_amount)]), 'orange');
        }
        
        if (frm.doc.journal_entry) {
            frm.dashboard.add_indicator(__('Journal Entry: {0}', [frm.doc.journal_entry]), 'green');
        }
        
        // Show posting info
        if (frm.doc.processed_by && frm.doc.processed_date) {
            let processed_info = __('Posted by {0} on {1}', [
                frm.doc.processed_by,
                frappe.datetime.str_to_user(frm.doc.processed_date)
            ]);
            frm.dashboard.add_comment(processed_info, 'blue', true);
        }
        
        // Group by category and show stats
        if (frm.doc.depreciation_entries && frm.doc.depreciation_entries.length > 0) {
            let category_stats = {};
            
            frm.doc.depreciation_entries.forEach(function(entry) {
                if (!category_stats[entry.asset_category]) {
                    category_stats[entry.asset_category] = {
                        count: 0,
                        amount: 0
                    };
                }
                category_stats[entry.asset_category].count += 1;
                category_stats[entry.asset_category].amount += flt(entry.depreciation_amount);
            });
            
            let stats_html = '<div style="margin-top: 10px;"><strong>Category Breakdown:</strong><ul>';
            Object.keys(category_stats).forEach(function(category) {
                let stat = category_stats[category];
                stats_html += `<li>${category}: ${stat.count} assets, ${format_currency(stat.amount)}</li>`;
            });
            stats_html += '</ul></div>';
            
            frm.dashboard.add_comment(stats_html, 'green', true);
        }
    },
    
    highlight_overdue: function(frm) {
        if (!frm.doc.depreciation_entries) {
            return;
        }
        
        let today = frappe.datetime.get_today();
        let overdue_count = 0;
        
        frm.doc.depreciation_entries.forEach(function(entry, idx) {
            if (entry.schedule_date < today) {
                overdue_count++;
                // Highlight overdue rows
                let row = frm.fields_dict.depreciation_entries.grid.grid_rows[idx];
                if (row) {
                    $(row.wrapper).find('.grid-row').css('background-color', '#fff3cd');
                }
            }
        });
        
        if (overdue_count > 0) {
            frappe.show_alert({
                message: __('Warning: {0} overdue depreciation schedule(s) found', [overdue_count]),
                indicator: 'orange'
            }, 10);
        }
    },
    
    create_new_entry: function(frm) {
        // Create a new depreciation entry with same filters
        frappe.call({
            method: 'ecclesia.ecclesia.doctype.fixed_asset_depreciation_entry.fixed_asset_depreciation_entry.create_depreciation_entry',
            args: {
                filters: {
                    company: frm.doc.company,
                    posting_date: frappe.datetime.get_today(),
                    period_start_date: frm.doc.period_start_date,
                    period_end_date: frm.doc.period_end_date,
                    finance_book: frm.doc.finance_book,
                    asset_category: frm.doc.asset_category,
                    location: frm.doc.location,
                    department: frm.doc.department,
                    cost_center: frm.doc.cost_center
                }
            },
            callback: function(r) {
                if (r.message) {
                    frappe.set_route('Form', 'Fixed Asset Depreciation Entry', r.message);
                }
            }
        });
    }
});

// Child table: Depreciation Entry Details
frappe.ui.form.on('Depreciation Entry Details', {
    depreciation_entries_add: function(frm, cdt, cdn) {
        // Auto-calculate when row is added
        frm.trigger('calculate_totals');
    },
    
    depreciation_entries_remove: function(frm, cdt, cdn) {
        // Recalculate when row is removed
        frm.trigger('calculate_totals');
    },
    
    depreciation_amount: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        // Recalculate after values
        if (row.book_value_before) {
            row.accumulated_depreciation_after = flt(row.accumulated_depreciation_before) + flt(row.depreciation_amount);
            row.book_value_after = flt(row.book_value_before) - flt(row.depreciation_amount);
            
            frm.refresh_field('depreciation_entries');
        }
        
        // Recalculate totals
        frm.trigger('calculate_totals');
    },
    
    asset: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        if (row.asset) {
            // Fetch asset details
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Fixed Asset',
                    name: row.asset
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.model.set_value(cdt, cdn, 'asset_name', r.message.asset_name);
                        frappe.model.set_value(cdt, cdn, 'asset_category', r.message.asset_category);
                        frappe.model.set_value(cdt, cdn, 'cost_center', r.message.cost_center);
                        frappe.model.set_value(cdt, cdn, 'accumulated_depreciation_before', r.message.accumulated_depreciation);
                        frappe.model.set_value(cdt, cdn, 'book_value_before', r.message.current_value);
                        
                        // Fetch category accounts
                        frappe.call({
                            method: 'frappe.client.get',
                            args: {
                                doctype: 'Fixed Asset Category',
                                name: r.message.asset_category
                            },
                            callback: function(r2) {
                                if (r2.message) {
                                    frappe.model.set_value(cdt, cdn, 'depreciation_account', 
                                        r2.message.depreciation_expense_account);
                                    frappe.model.set_value(cdt, cdn, 'accumulated_depreciation_account', 
                                        r2.message.accumulated_depreciation_account);
                                }
                            }
                        });
                    }
                }
            });
        }
    }
});

// Helper function
function format_currency(value) {
    return frappe.format(value, {fieldtype: 'Currency'});
}

// Add keyboard shortcuts
frappe.ui.keys.add_shortcut({
    shortcut: 'ctrl+g',
    action: () => {
        let frm = cur_frm;
        if (frm && frm.doctype === 'Fixed Asset Depreciation Entry' && frm.doc.docstatus === 0) {
            frm.trigger('get_assets_for_depreciation');
        }
    },
    description: __('Get Assets for Depreciation'),
    page: 'Fixed Asset Depreciation Entry'
});