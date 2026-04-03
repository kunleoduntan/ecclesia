// Copyright (c) 2026, kunle Oduntan and contributors
// For license information, please see license.txt

// ecclesia/ecclesia/doctype/fixed_asset_category/fixed_asset_category.js

frappe.ui.form.on('Fixed Asset Category', {
    refresh: function(frm) {
        // Add custom buttons
        if (!frm.is_new()) {
            frm.add_custom_button(__('View Assets'), function() {
                frappe.set_route('List', 'Fixed Asset', {
                    'asset_category': frm.doc.name
                });
            });
            
            frm.add_custom_button(__('Category Summary'), function() {
                frm.trigger('show_category_summary');
            });
        }
        
        // Set field queries
        frm.set_query('parent_category', function() {
            return {
                filters: {
                    'is_group': 1,
                    'name': ['!=', frm.doc.name]
                }
            };
        });
        
        frm.set_query('fixed_asset_account', function() {
            return {
                filters: {
                    'account_type': 'Fixed Asset',
                    'is_group': 0
                }
            };
        });
        
        frm.set_query('accumulated_depreciation_account', function() {
            return {
                filters: {
                    'account_type': 'Accumulated Depreciation',
                    'is_group': 0
                }
            };
        });
        
        frm.set_query('depreciation_expense_account', function() {
            return {
                filters: {
                    'root_type': 'Expense',
                    'is_group': 0
                }
            };
        });
        
        frm.set_query('capital_work_in_progress_account', function() {
            return {
                filters: {
                    'account_type': 'Capital Work in Progress',
                    'is_group': 0
                }
            };
        });
        
        // Show/hide fields based on settings
        frm.trigger('toggle_depreciation_fields');
        frm.trigger('toggle_insurance_fields');
        
        // Show indicators
        frm.trigger('show_status_indicators');
    },
    
    enable_depreciation: function(frm) {
        frm.trigger('toggle_depreciation_fields');
        
        if (!frm.doc.enable_depreciation) {
            // Clear depreciation fields
            frm.set_value('depreciation_method', '');
            frm.set_value('depreciation_rate', 0);
            frm.set_value('total_number_of_depreciations', 0);
            frm.set_value('frequency_of_depreciation', '');
        } else {
            // Set defaults
            if (!frm.doc.depreciation_method) {
                frm.set_value('depreciation_method', 'Straight Line');
            }
            if (!frm.doc.frequency_of_depreciation) {
                frm.set_value('frequency_of_depreciation', '1');
            }
        }
    },
    
    toggle_depreciation_fields: function(frm) {
        let show = frm.doc.enable_depreciation;
        
        frm.toggle_display('depreciation_section', show);
        frm.toggle_display('advanced_depreciation_section', show);
        frm.toggle_reqd('depreciation_method', show);
        frm.toggle_reqd('total_number_of_depreciations', show);
        frm.toggle_reqd('frequency_of_depreciation', show);
        frm.toggle_reqd('accumulated_depreciation_account', show);
        frm.toggle_reqd('depreciation_expense_account', show);
    },
    
    depreciation_method: function(frm) {
        // Show/hide depreciation rate based on method
        let show_rate = ['Written Down Value', 'Double Declining Balance'].includes(frm.doc.depreciation_method);
        
        frm.toggle_display('depreciation_rate', show_rate);
        frm.toggle_reqd('depreciation_rate', show_rate);
        
        // Set default rates
        if (show_rate && !frm.doc.depreciation_rate) {
            if (frm.doc.depreciation_method === 'Written Down Value') {
                frm.set_value('depreciation_rate', 20);
            } else if (frm.doc.depreciation_method === 'Double Declining Balance') {
                frm.set_value('depreciation_rate', 40);
            }
        }
        
        // Calculate useful life if depreciation rate is set
        if (frm.doc.depreciation_rate) {
            frm.trigger('calculate_from_depreciation_rate');
        }
        
        // Show method description
        frm.trigger('show_method_description');
    },
    
    depreciation_rate: function(frm) {
        // Calculate useful life when depreciation rate changes
        if (frm.doc.depreciation_rate && frm.doc.depreciation_rate > 0) {
            frm.trigger('calculate_from_depreciation_rate');
        }
    },
    
    frequency_of_depreciation: function(frm) {
        // Recalculate when frequency changes
        if (frm.doc.depreciation_rate && frm.doc.depreciation_rate > 0) {
            frm.trigger('calculate_from_depreciation_rate');
        } else {
            frm.trigger('calculate_useful_life');
        }
    },
    
    total_number_of_depreciations: function(frm) {
        // Only calculate if not auto-calculating from depreciation rate
        if (!frm.doc.depreciation_rate || frm.doc.depreciation_rate <= 0) {
            frm.trigger('calculate_useful_life');
        }
    },
    
    calculate_from_depreciation_rate: function(frm) {
        if (!frm.doc.depreciation_rate || frm.doc.depreciation_rate <= 0) {
            return;
        }
        
        // Calculate Useful Life in Years: 100 / depreciation_rate
        let useful_life_years = Math.round(100 / flt(frm.doc.depreciation_rate));
        frm.set_value('useful_life_years', useful_life_years);
        
        // Get frequency in months (default to 1 if not set)
        let frequency = flt(frm.doc.frequency_of_depreciation) || 1;
        
        // Calculate Useful Life in Months
        let useful_life_months = useful_life_years * 12;
        frm.set_value('useful_life_months', useful_life_months);
        
        // Calculate Total Number of Depreciations based on frequency
        // If Monthly (1): useful_life_months / 1
        // If Quarterly (3): useful_life_months / 3
        // If Half-yearly (6): useful_life_months / 6
        // If Yearly (12): useful_life_months / 12
        let total_depreciations = Math.round(useful_life_months / frequency);
        frm.set_value('total_number_of_depreciations', total_depreciations);
        
        // Set typical useful life years
        frm.set_value('typical_useful_life_years', useful_life_years);
        
        // Show calculation summary
        let frequency_name = get_frequency_name(frequency);
        frappe.show_alert({
            message: __('📊 Auto-calculated: {0} years ({1} months) = {2} {3} periods', [
                useful_life_years,
                useful_life_months,
                total_depreciations,
                frequency_name
            ]),
            indicator: 'green'
        }, 5);
    },
    
    calculate_useful_life: function(frm) {
        if (frm.doc.total_number_of_depreciations && frm.doc.frequency_of_depreciation) {
            let frequency = flt(frm.doc.frequency_of_depreciation);
            let months = flt(frm.doc.total_number_of_depreciations) * frequency;
            let years = months / 12;
            
            frm.set_value('useful_life_months', months);
            frm.set_value('useful_life_years', Math.round(years));
            frm.set_value('typical_useful_life_years', Math.round(years));
            
            frappe.show_alert({
                message: __('Calculated useful life: {0} months ({1} years)', [months, years.toFixed(1)]),
                indicator: 'blue'
            }, 3);
        }
    },
    
    show_method_description: function(frm) {
        if (!frm.doc.depreciation_method) return;
        
        let descriptions = {
            'Straight Line': 'Equal depreciation each period. Simple and widely used.',
            'Written Down Value': 'Depreciation on reducing balance. Higher depreciation in early years.',
            'Double Declining Balance': 'Accelerated depreciation at twice the straight-line rate.',
            'Sum of Years Digits': 'Accelerated depreciation based on sum of years.',
            'Units of Production': 'Depreciation based on actual usage/production.'
        };
        
        let desc = descriptions[frm.doc.depreciation_method];
        if (desc) {
            frm.set_df_property('depreciation_method', 'description', desc);
        }
    },
    
    asset_code_prefix: function(frm) {
        if (frm.doc.asset_code_prefix) {
            // Auto-uppercase prefix
            frm.set_value('asset_code_prefix', frm.doc.asset_code_prefix.toUpperCase());
            
            // Preview asset code
            frm.trigger('preview_asset_code');
        }
    },
    
    asset_code_format: function(frm) {
        frm.trigger('preview_asset_code');
    },
    
    asset_code_series_start: function(frm) {
        frm.trigger('preview_asset_code');
    },
    
    preview_asset_code: function(frm) {
        if (!frm.doc.asset_code_prefix || !frm.doc.asset_code_format) {
            return;
        }
        
        let prefix = frm.doc.asset_code_prefix;
        let start = frm.doc.asset_code_series_start || 1;
        let format = frm.doc.asset_code_format;
        let preview = '';
        
        if (format === 'PREFIX-####') {
            preview = prefix + '-' + String(start).padStart(4, '0');
        } else if (format === 'PREFIX-#####') {
            preview = prefix + '-' + String(start).padStart(5, '0');
        } else if (format === 'PREFIX-######') {
            preview = prefix + '-' + String(start).padStart(6, '0');
        } else if (format === 'PREFIX-YYYY-####') {
            let year = new Date().getFullYear();
            preview = prefix + '-' + year + '-' + String(start).padStart(4, '0');
        } else if (format === 'PREFIX-YYYY-#####') {
            let year = new Date().getFullYear();
            preview = prefix + '-' + year + '-' + String(start).padStart(5, '0');
        }
        
        if (preview) {
            frm.set_df_property('asset_code_format', 'description', 
                __('Preview: {0}', [preview]));
        }
    },
    
    insurance_required: function(frm) {
        frm.trigger('toggle_insurance_fields');
    },
    
    toggle_insurance_fields: function(frm) {
        frm.toggle_display('minimum_insurance_amount', frm.doc.insurance_required);
        frm.toggle_reqd('minimum_insurance_amount', frm.doc.insurance_required);
    },
    
    is_group: function(frm) {
        if (frm.doc.is_group) {
            frappe.msgprint({
                title: __('Group Category'),
                message: __('Group categories cannot have assets directly assigned. Assets must be assigned to child categories.'),
                indicator: 'blue'
            });
        }
    },
    
    parent_category: function(frm) {
        if (frm.doc.parent_category) {
            // Fetch parent category settings
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Fixed Asset Category',
                    name: frm.doc.parent_category
                },
                callback: function(r) {
                    if (r.message && !r.message.is_group) {
                        frappe.msgprint(__('Parent category must be a Group'));
                        frm.set_value('parent_category', '');
                    }
                }
            });
        }
    },
    
    show_category_summary: function(frm) {
        frappe.call({
            method: 'ecclesia.ecclesia.doctype.fixed_asset_category.fixed_asset_category.get_category_defaults',
            args: {
                category: frm.doc.name
            },
            callback: function(r) {
                if (r.message) {
                    // Get asset count
                    frappe.call({
                        method: 'frappe.client.get_count',
                        args: {
                            doctype: 'Fixed Asset',
                            filters: {
                                asset_category: frm.doc.name,
                                docstatus: 1
                            }
                        },
                        callback: function(r2) {
                            let asset_count = r2.message || 0;
                            
                            // Build summary HTML
                            let html = '<div class="row">';
                            html += '<div class="col-md-12">';
                            html += '<h4>' + __('Category Summary') + '</h4>';
                            html += '<table class="table table-bordered">';
                            html += '<tr><th>' + __('Total Assets') + '</th><td>' + asset_count + '</td></tr>';
                            html += '<tr><th>' + __('Depreciation Enabled') + '</th><td>' + (frm.doc.enable_depreciation ? 'Yes' : 'No') + '</td></tr>';
                            
                            if (frm.doc.enable_depreciation) {
                                html += '<tr><th>' + __('Depreciation Method') + '</th><td>' + frm.doc.depreciation_method + '</td></tr>';
                                html += '<tr><th>' + __('Depreciation Rate') + '</th><td>' + (frm.doc.depreciation_rate || 'N/A') + '%</td></tr>';
                                html += '<tr><th>' + __('Useful Life') + '</th><td>' + (frm.doc.useful_life_years || 'N/A') + ' years (' + (frm.doc.useful_life_months || 'N/A') + ' months)</td></tr>';
                                html += '<tr><th>' + __('Total Depreciations') + '</th><td>' + (frm.doc.total_number_of_depreciations || 'N/A') + '</td></tr>';
                            }
                            
                            html += '<tr><th>' + __('Asset Code Format') + '</th><td>' + frm.doc.asset_code_prefix + '...</td></tr>';
                            html += '<tr><th>' + __('Next Asset Number') + '</th><td>' + (frm.doc.next_asset_number || 1) + '</td></tr>';
                            html += '</table>';
                            html += '</div></div>';
                            
                            frappe.msgprint({
                                title: __('Category: {0}', [frm.doc.name]),
                                message: html,
                                wide: true
                            });
                        }
                    });
                }
            }
        });
    },
    
    show_status_indicators: function(frm) {
        if (frm.is_new()) return;
        
        // Show depreciation status
        if (frm.doc.enable_depreciation) {
            frm.dashboard.add_indicator(__('Depreciation Enabled'), 'green');
            
            // Show calculation method
            if (frm.doc.depreciation_rate && frm.doc.depreciation_rate > 0) {
                frm.dashboard.add_indicator(__('Auto-calculated from Rate: {0}%', [frm.doc.depreciation_rate]), 'blue');
            }
        } else {
            frm.dashboard.add_indicator(__('Depreciation Disabled'), 'gray');
        }
        
        // Show group status
        if (frm.doc.is_group) {
            frm.dashboard.add_indicator(__('Group Category'), 'blue');
        }
        
        // Show insurance requirement
        if (frm.doc.insurance_required) {
            frm.dashboard.add_indicator(__('Insurance Required'), 'orange');
        }
    },
    
    // Validation helpers
    validate: function(frm) {
        // Validate accounts are set if depreciation is enabled
        if (frm.doc.enable_depreciation) {
            let required_accounts = [
                'fixed_asset_account',
                'accumulated_depreciation_account',
                'depreciation_expense_account'
            ];
            
            let missing = [];
            required_accounts.forEach(function(field) {
                if (!frm.doc[field]) {
                    missing.push(frappe.meta.get_label('Fixed Asset Category', field));
                }
            });
            
            if (missing.length > 0) {
                frappe.throw(__('Please set the following accounts: {0}', [missing.join(', ')]));
            }
        }
    }
});

// Helper functions
function flt(val) {
    return parseFloat(val) || 0;
}

function get_frequency_name(frequency) {
    const freq_map = {
        1: 'monthly',
        3: 'quarterly',
        6: 'half-yearly',
        12: 'yearly'
    };
    return freq_map[frequency] || 'periodic';
}