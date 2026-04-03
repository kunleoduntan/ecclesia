// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

frappe.ui.form.on("Budget Plan", {
    refresh: function(frm) {
        setup_custom_buttons(frm);
        update_budget_metrics(frm);
        set_status_indicator(frm);
        setup_keyboard_shortcuts(frm);
    },

    onload: function(frm) {
        if (frm.is_new() && !frm.doc.fiscal_year) {
            set_default_fiscal_year(frm);
        }
        load_company_defaults(frm);
    },

    company: function(frm) {
        if (frm.doc.company) {
            load_company_defaults(frm);
        }
    },

    fiscal_year: function(frm) {
        if (frm.doc.fiscal_year) {
            get_fiscal_year_dates(frm);
        }
    },

    is_group_budget: function(frm) {
        frm.toggle_enable('allow_branch_split', frm.doc.is_group_budget);
        frm.toggle_enable('allow_cost_center_split', frm.doc.is_group_budget);
        
        if (!frm.doc.is_group_budget) {
            frm.set_value('allow_branch_split', 0);
            frm.set_value('allow_cost_center_split', 0);
        }
    },

    scenario_analysis_enabled: function(frm) {
        if (frm.doc.scenario_analysis_enabled && (!frm.doc.scenario_budgets || frm.doc.scenario_budgets.length === 0)) {
            frappe.confirm(
                __('🎯 Generate Best/Worst case scenarios automatically?'),
                function() { generate_scenarios(frm); },
                function() { frappe.show_alert({message: __('You can generate scenarios later'), indicator: 'blue'}, 3); }
            );
        }
    },

    enable_projection: function(frm) {
        if (frm.doc.enable_projection) {
            frappe.show_alert({
                message: __('📈 Projection enabled! Configure settings and click "Generate Projections"'),
                indicator: 'green'
            }, 5);
        }
    }
});

// =======================================
// CUSTOM BUTTONS WITH ICONS & TOOLTIPS
// =======================================
function setup_custom_buttons(frm) {
    frm.page.clear_inner_toolbar();
    
    // ============================================
    // EXPORT BUTTONS - AVAILABLE AT ALL TIMES
    // ============================================
    frm.add_custom_button(__('📊 Export to Excel'), function() {
        export_to_excel_advanced(frm);
    }, __('💾 Export'));

    frm.add_custom_button(__('📄 Export to PDF'), function() {
        export_to_pdf(frm);
    }, __('💾 Export'));
    
    // ============================================
    // DRAFT DOCUMENT BUTTONS (docstatus === 0)
    // ============================================
    if (frm.doc.docstatus === 0) {
        // Distribution Actions
        if (frm.doc.is_group_budget && frm.doc.allow_branch_split) {
            frm.add_custom_button(__('🏢 Distribute to Branches'), function() {
                show_distribution_dialog(frm, 'branch');
            }, __('📊 Distribution'));
        }

        if (frm.doc.is_group_budget && frm.doc.allow_cost_center_split) {
            frm.add_custom_button(__('🎯 Distribute to Cost Centers'), function() {
                show_distribution_dialog(frm, 'cost_center');
            }, __('📊 Distribution'));
        }

        // Forecasting Actions
        if (frm.doc.enable_projection) {
            frm.add_custom_button(__('📈 Generate Projections'), function() {
                show_projection_dialog(frm);
            }, __('🔮 Forecasting'));

            frm.add_custom_button(__('💹 Apply Growth Rate'), function() {
                apply_growth_rate_to_budget(frm);
            }, __('🔮 Forecasting'));
        }

        // Scenario Actions
        if (frm.doc.scenario_analysis_enabled) {
            frm.add_custom_button(__('🎯 Generate Scenarios'), function() {
                generate_scenarios(frm);
            }, __('📊 Scenarios'));
        }

        // Utility Actions
        frm.add_custom_button(__('📋 Copy from Previous'), function() {
            copy_from_previous_year(frm);
        }, __('🛠️ Tools'));

        frm.add_custom_button(__('📥 Import from Excel'), function() {
            import_from_excel(frm);
        }, __('🛠️ Tools'));

        // Bulk Edit
        if (frm.doc.monthly_budget && frm.doc.monthly_budget.length > 0) {
            frm.add_custom_button(__('⚡ Bulk Edit'), function() {
                bulk_edit_budget_lines(frm);
            }, __('🛠️ Tools'));
        }
    }

    // ============================================
    // SUBMITTED DOCUMENT BUTTONS (docstatus === 1)
    // ============================================
    if (frm.doc.docstatus === 1) {
        if (frm.doc.enable_variance_tracking) {
            frm.add_custom_button(__('📊 Calculate Variances'), function() {
                calculate_variances(frm);
            }, __('📈 Analysis'));

            frm.add_custom_button(__('📑 View Variance Report'), function() {
                view_variance_report(frm);
            }, __('📈 Analysis'));
        }

        frm.add_custom_button(__('📈 Get Summary'), function() {
            get_budget_summary(frm);
        }, __('📊 Reports'));

        // Child Budget Creation
        if (frm.doc.is_group_budget) {
            if (frm.doc.allow_branch_split && frm.doc.branch_allocations && frm.doc.branch_allocations.length > 0) {
                frm.add_custom_button(__('🏢 Create Branch Budgets'), function() {
                    create_branch_budgets(frm);
                }, __('⚡ Actions'));
            }

            if (frm.doc.allow_cost_center_split && frm.doc.cost_center_allocations && frm.doc.cost_center_allocations.length > 0) {
                frm.add_custom_button(__('🎯 Create Cost Center Budgets'), function() {
                    create_cost_center_budgets(frm);
                }, __('⚡ Actions'));
            }
        }
    }
}

// =======================================
// DISTRIBUTION DIALOG
// =======================================
function show_distribution_dialog(frm, type) {
    var title = type === 'branch' ? '🏢 Distribute to Branches' : '🎯 Distribute to Cost Centers';
    var methods = type === 'branch' 
        ? ['Equal Distribution', 'Proportional (Revenue)', 'Proportional (Headcount)', 'Custom']
        : ['Equal Distribution', 'Proportional (Budget Size)', 'Custom'];

    var d = new frappe.ui.Dialog({
        title: title,
        fields: [
            {
                fieldname: 'distribution_method',
                fieldtype: 'Select',
                label: __('Distribution Method'),
                options: methods.join('\n'),
                default: 'Equal Distribution',
                reqd: 1,
                description: __('Choose how to allocate budget')
            },
            {
                fieldname: 'preview_html',
                fieldtype: 'HTML',
                label: __('Preview')
            }
        ],
        primary_action_label: __('✅ Distribute'),
        primary_action: function(values) {
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.budget_plan.budget_plan.auto_distribute_branches',
                args: {
                    budget_name: frm.doc.name,
                    method: values.distribution_method
                },
                freeze: true,
                freeze_message: __('🔄 Distributing budget...'),
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frm.reload_doc();
                        frappe.show_alert({
                            message: '✅ ' + r.message.message,
                            indicator: 'green'
                        }, 5);
                        d.hide();
                    } else if (r.message) {
                        frappe.msgprint({
                            title: __('❌ Distribution Failed'),
                            message: r.message.message,
                            indicator: 'red'
                        });
                    }
                }
            });
        }
    });

    d.fields_dict.distribution_method.$input.on('change', function() {
        update_distribution_preview(d, frm, type);
    });

    d.show();
    update_distribution_preview(d, frm, type);
}

function update_distribution_preview(dialog, frm, type) {
    var method = dialog.get_value('distribution_method');
    var html = '<div style="padding: 10px; background: #f8f9fa; border-radius: 5px; margin-top: 10px;">';
    html += '<p style="margin: 0;"><strong>📊 Preview:</strong></p>';
    
    if (method === 'Equal Distribution') {
        html += '<p>Each ' + type + ' will receive an equal share of the budget.</p>';
    } else if (method.includes('Proportional')) {
        html += '<p>Budget will be distributed based on ' + method.split('(')[1].replace(')', '').toLowerCase() + '.</p>';
    } else {
        html += '<p>You can manually adjust allocations after distribution.</p>';
    }
    
    html += '</div>';
    dialog.fields_dict.preview_html.$wrapper.html(html);
}

// =======================================
// PROJECTION DIALOG
// =======================================
function show_projection_dialog(frm) {
    var d = new frappe.ui.Dialog({
        title: __('📈 Generate Budget Projections'),
        fields: [
            {
                fieldname: 'projection_method',
                fieldtype: 'Select',
                label: __('Projection Method'),
                options: '\nHistorical Average\nLinear Trend\nGrowth Rate',
                default: frm.doc.projection_method || 'Historical Average',
                reqd: 1
            },
            {
                fieldname: 'col_break_1',
                fieldtype: 'Column Break'
            },
            {
                fieldname: 'historical_years',
                fieldtype: 'Int',
                label: __('Historical Years'),
                default: frm.doc.historical_years_for_analysis || 3,
                depends_on: "eval:['Historical Average', 'Linear Trend'].includes(doc.projection_method)"
            },
            {
                fieldname: 'growth_rate',
                fieldtype: 'Percent',
                label: __('Growth Rate %'),
                default: frm.doc.growth_rate_percentage || 5,
                depends_on: "eval:doc.projection_method == 'Growth Rate'"
            },
            {
                fieldname: 'section_break_1',
                fieldtype: 'Section Break'
            },
            {
                fieldname: 'preview_info',
                fieldtype: 'HTML'
            }
        ],
        primary_action_label: __('🚀 Generate'),
        primary_action: function(values) {
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.budget_plan.budget_plan.generate_projections',
                args: {
                    budget_name: frm.doc.name,
                    projection_method: values.projection_method,
                    historical_years: values.historical_years || 3,
                    growth_rate: values.growth_rate || 5
                },
                freeze: true,
                freeze_message: __('🔮 Generating projections...'),
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frm.reload_doc();
                        frappe.show_alert({
                            message: '✅ ' + r.message.message,
                            indicator: 'green'
                        }, 5);
                        d.hide();
                    }
                }
            });
        }
    });

    d.fields_dict.preview_info.$wrapper.html(`
        <div style="padding: 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; border-radius: 8px; margin-top: 10px;">
            <h4 style="margin: 0 0 10px 0;">💡 How it works:</h4>
            <ul style="margin: 0; padding-left: 20px;">
                <li><strong>Historical Average:</strong> Uses past ${frm.doc.historical_years_for_analysis || 3} years average</li>
                <li><strong>Linear Trend:</strong> Predicts based on historical trends</li>
                <li><strong>Growth Rate:</strong> Applies ${frm.doc.growth_rate_percentage || 5}% growth to current budget</li>
            </ul>
        </div>
    `);

    d.show();
}

// =======================================
// GROWTH RATE APPLICATION
// =======================================
function apply_growth_rate_to_budget(frm) {
    if (!frm.doc.growth_rate_percentage) {
        frappe.prompt({
            label: __('Growth Rate %'),
            fieldtype: 'Percent',
            fieldname: 'growth_rate',
            reqd: 1
        }, function(values) {
            apply_growth(frm, values.growth_rate);
        }, __('💹 Enter Growth Rate'));
        return;
    }
    apply_growth(frm, frm.doc.growth_rate_percentage);
}

function apply_growth(frm, growth_rate) {
    frappe.confirm(
        __('Apply <strong>{0}%</strong> growth rate to all budget lines?<br><br>This will increase all monthly values by {0}%', 
            [growth_rate]),
        function() {
            var factor = 1 + (growth_rate / 100);
            var months = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'];
            var updated_count = 0;
            
            frm.doc.monthly_budget.forEach(function(row) {
                months.forEach(function(month) {
                    if (row[month]) {
                        frappe.model.set_value(row.doctype, row.name, month, row[month] * factor);
                        updated_count++;
                    }
                });
            });
            
            frm.refresh_field('monthly_budget');
            update_budget_metrics(frm);
            
            frappe.show_alert({
                message: __('✅ Applied {0}% growth to {1} values', [growth_rate, updated_count]),
                indicator: 'green'
            }, 5);
        }
    );
}

// =======================================
// SCENARIO GENERATION
// =======================================
function generate_scenarios(frm) {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.budget_plan.budget_plan.generate_scenarios',
        args: {
            budget_name: frm.doc.name,
            best_case_pct: frm.doc.best_case_percentage || 20,
            worst_case_pct: frm.doc.worst_case_percentage || 20
        },
        freeze: true,
        freeze_message: __('🎯 Generating scenarios...'),
        callback: function(r) {
            if (r.message && r.message.success) {
                frm.reload_doc();
                show_scenarios_summary(frm, r.message);
            }
        }
    });
}

function show_scenarios_summary(frm, result) {
    var html = `
        <div style="padding: 20px;">
            <h3 style="color: #667eea;">🎯 Scenarios Generated Successfully!</h3>
            <p>Created ${result.scenarios_created || 3} budget scenarios:</p>
            <ul>
                <li>✅ <strong>Best Case:</strong> +${frm.doc.best_case_percentage}%</li>
                <li>📊 <strong>Most Likely:</strong> Base case</li>
                <li>⚠️ <strong>Worst Case:</strong> -${frm.doc.worst_case_percentage}%</li>
            </ul>
            <p>View the <strong>Scenarios</strong> tab for details.</p>
        </div>
    `;
    
    frappe.msgprint({
        title: __('Success'),
        message: html,
        indicator: 'green'
    });
}

// =======================================
// VARIANCE ANALYSIS
// =======================================
function calculate_variances(frm) {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.budget_plan.budget_plan.calculate_variance',
        args: {budget_name: frm.doc.name},
        freeze: true,
        freeze_message: __('📊 Calculating variances...'),
        callback: function(r) {
            if (r.message && r.message.success) {
                frm.reload_doc();
                frappe.show_alert({
                    message: '✅ Variance analysis completed',
                    indicator: 'blue'
                }, 5);
            }
        }
    });
}

function view_variance_report(frm) {
    frappe.route_options = {
        budget: frm.doc.name,
        fiscal_year: frm.doc.fiscal_year,
        company: frm.doc.company
    };
    frappe.set_route('query-report', 'Budget Variance Analysis');
}

// =======================================
// CHILD BUDGET CREATION
// =======================================
function create_branch_budgets(frm) {
    frappe.confirm(
        __('🏢 Create individual budgets for <strong>{0} branches</strong>?<br><br>This will create separate budget documents for each branch allocation.', 
            [frm.doc.branch_allocations.length]),
        function() {
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.budget_plan.budget_plan.split_budget_by_branches',
                args: {
                    budget_name: frm.doc.name,
                    distribution_method: frm.doc.branch_distribution_method || 'Equal Distribution'
                },
                freeze: true,
                freeze_message: __('🔄 Creating branch budgets...'),
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frm.reload_doc();
                        frappe.msgprint({
                            title: __('✅ Success'),
                            message: r.message.message,
                            indicator: 'green'
                        });
                    }
                }
            });
        }
    );
}

function create_cost_center_budgets(frm) {
    frappe.confirm(
        __('🎯 Create individual budgets for <strong>{0} cost centers</strong>?', 
            [frm.doc.cost_center_allocations.length]),
        function() {
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.budget_plan.budget_plan.split_budget_by_cost_centers',
                args: {
                    budget_name: frm.doc.name,
                    distribution_method: frm.doc.cost_center_distribution_method || 'Equal Distribution'
                },
                freeze: true,
                freeze_message: __('🔄 Creating cost center budgets...'),
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frm.reload_doc();
                        frappe.msgprint({
                            title: __('✅ Success'),
                            message: r.message.message,
                            indicator: 'green'
                        });
                    }
                }
            });
        }
    );
}

// =======================================
// EXCEL EXPORT
// =======================================
function export_to_excel_advanced(frm) {
    var d = new frappe.ui.Dialog({
        title: __('📊 Export to Excel'),
        fields: [
            {
                fieldname: 'export_preview',
                fieldtype: 'HTML',
                options: `
                    <div style="padding: 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                color: white; border-radius: 8px; margin-bottom: 15px;">
                        <h4 style="margin: 0 0 10px 0;">✨ Beautiful Excel Export</h4>
                        <p style="margin: 0; opacity: 0.9;">Your budget will be exported with:</p>
                        <ul style="margin: 10px 0 0 0; padding-left: 20px;">
                            <li>🎨 Professional color-coded formatting</li>
                            <li>📊 Interactive charts and graphs</li>
                            <li>📈 Monthly trend analysis</li>
                            <li>🎯 Summary dashboard</li>
                        </ul>
                    </div>
                `
            },
            {
                fieldname: 'export_type',
                fieldtype: 'Select',
                label: __('📋 Export Type'),
                options: '\nStandard\nDetailed Analysis\nWith Scenarios',
                default: 'Standard',
                reqd: 1,
                description: __('Choose the level of detail')
            },
            {
                fieldname: 'col_break_1',
                fieldtype: 'Column Break'
            },
            {
                fieldname: 'include_charts',
                fieldtype: 'Check',
                label: __('📊 Include Charts'),
                default: 1,
                description: __('Add visual charts to Excel')
            },
            {
                fieldname: 'include_summary',
                fieldtype: 'Check',
                label: __('📄 Include Summary Sheet'),
                default: 1,
                description: __('Add executive summary')
            },
            {
                fieldname: 'section_break_1',
                fieldtype: 'Section Break'
            },
            {
                fieldname: 'preview_html',
                fieldtype: 'HTML'
            }
        ],
        primary_action_label: __('💾 Export Now'),
        primary_action: function(values) {
            frappe.show_alert({
                message: __('📥 Generating beautiful Excel file...'),
                indicator: 'blue'
            }, 3);
            
            var url = `/api/method/ecclesia.ecclesia.doctype.budget_plan.budget_plan.export_to_excel_advanced`;
            url += `?budget_name=${encodeURIComponent(frm.doc.name)}`;
            url += `&export_type=${encodeURIComponent(values.export_type)}`;
            url += `&include_charts=${values.include_charts ? 1 : 0}`;
            url += `&include_summary=${values.include_summary ? 1 : 0}`;
            
            window.open(url, '_blank');
            
            setTimeout(function() {
                frappe.show_alert({
                    message: __('✅ Excel export complete! Check your downloads.'),
                    indicator: 'green'
                }, 5);
            }, 2000);
            
            d.hide();
        },
        secondary_action_label: __('Preview'),
        secondary_action: function(values) {
            show_export_preview(d, values);
        }
    });

    d.fields_dict.export_type.$input.on('change', function() {
        show_export_preview(d, d.get_values());
    });

    d.show();
    show_export_preview(d, d.get_values());
}

function show_export_preview(dialog, values) {
    var preview_html = `
        <div style="padding: 15px; background: #f8f9fa; border-radius: 8px; margin-top: 10px;">
            <h5 style="margin: 0 0 10px 0; color: #667eea;">📋 Export Preview: ${values.export_type || 'Standard'}</h5>
    `;
    
    if (values.export_type === 'Standard') {
        preview_html += `
            <p><strong>Includes:</strong></p>
            <ul style="margin: 5px 0; padding-left: 20px;">
                <li>✅ Budget details with color-coded amounts</li>
                <li>✅ Monthly totals with highlighting</li>
                ${values.include_summary ? '<li>✅ Executive summary dashboard</li>' : ''}
                ${values.include_charts ? '<li>✅ Monthly trend charts</li>' : ''}
            </ul>
        `;
    } else if (values.export_type === 'Detailed Analysis') {
        preview_html += `
            <p><strong>Includes everything in Standard plus:</strong></p>
            <ul style="margin: 5px 0; padding-left: 20px;">
                <li>✅ Account-wise breakdown</li>
                <li>✅ Cost center analysis</li>
                <li>✅ Quarterly summaries</li>
                ${values.include_charts ? '<li>✅ Multiple chart types (Bar, Line, Pie)</li>' : ''}
            </ul>
        `;
    } else if (values.export_type === 'With Scenarios') {
        preview_html += `
            <p><strong>Includes everything plus:</strong></p>
            <ul style="margin: 5px 0; padding-left: 20px;">
                <li>✅ Best/Worst case scenarios</li>
                <li>✅ Scenario comparison charts</li>
                <li>✅ Risk analysis</li>
                ${values.include_charts ? '<li>✅ Scenario visualization</li>' : ''}
            </ul>
        `;
    }
    
    preview_html += `
        <div style="margin-top: 15px; padding: 10px; background: white; border-radius: 5px; border-left: 4px solid #667eea;">
            <strong>💡 Tip:</strong> The exported file will have professional formatting with color-coded cells, 
            borders, and automatic column widths for easy reading.
        </div>
    </div>
    `;
    
    dialog.fields_dict.preview_html.$wrapper.html(preview_html);
}

function export_to_pdf(frm) {
    frappe.show_alert({message: __('📄 Generating PDF...'), indicator: 'blue'}, 3);
    window.open(frm.doc.doctype + '/' + frm.doc.name + '.pdf', '_blank');
}

// =======================================
// EXCEL IMPORT
// =======================================
function import_from_excel(frm) {
    var d = new frappe.ui.Dialog({
        title: __('📥 Import Budget from Excel'),
        fields: [
            {
                fieldname: 'import_instructions',
                fieldtype: 'HTML',
                options: `
                    <div style="padding: 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                color: white; border-radius: 8px; margin-bottom: 15px;">
                        <h4 style="margin: 0 0 10px 0;">📋 How to Import:</h4>
                        <ol style="margin: 0; padding-left: 20px;">
                            <li>Download the Excel template using the button below</li>
                            <li>Fill in your budget data (GL Account and monthly amounts)</li>
                            <li>Save the Excel file</li>
                            <li>Upload it back here</li>
                        </ol>
                    </div>
                `
            },
            {
                fieldname: 'download_template_html',
                fieldtype: 'HTML',
                options: `
                    <div style="text-align: center; margin: 20px 0;">
                        <button class="btn btn-primary btn-lg" id="download-template-btn">
                            📊 Download Excel Template
                        </button>
                    </div>
                `
            },
            {
                fieldname: 'section_break_1',
                fieldtype: 'Section Break',
                label: __('Upload Filled Template')
            },
            {
                fieldname: 'excel_file',
                fieldtype: 'Attach',
                label: __('Select Excel File'),
                reqd: 1,
                description: __('Upload the filled Excel template')
            },
            {
                fieldname: 'replace_existing',
                fieldtype: 'Check',
                label: __('Replace Existing Budget Lines'),
                default: 1,
                description: __('Clear all existing lines before import')
            },
            {
                fieldname: 'validation_html',
                fieldtype: 'HTML'
            }
        ],
        primary_action_label: __('🚀 Import Data'),
        primary_action: function(values) {
            if (!values.excel_file) {
                frappe.msgprint(__('Please upload an Excel file'));
                return;
            }
            
            import_excel_data(frm, values.excel_file, d);
        }
    });

    // Download template button handler
    d.$wrapper.find('#download-template-btn').on('click', function() {
        download_import_template(frm);
    });

    // File upload validation
    d.fields_dict.excel_file.$input.on('change', function() {
        var file_url = d.get_value('excel_file');
        if (file_url) {
            validate_excel_file(file_url, d);
        }
    });

    d.show();
}

function download_import_template(frm) {
    if (!frm.doc.name) {
        frappe.msgprint(__('Please save the budget first'));
        return;
    }

    frappe.show_alert({
        message: __('📥 Generating template...'),
        indicator: 'blue'
    }, 3);

    window.open(
        `/api/method/ecclesia.ecclesia.doctype.budget_plan.budget_plan.get_excel_import_template?budget_name=${frm.doc.name}`,
        '_blank'
    );
}

function validate_excel_file(file_url, dialog) {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.budget_plan.budget_plan.validate_import_file',
        args: {
            file_url: file_url
        },
        callback: function(r) {
            var html = '';
            if (r.message && r.message.valid) {
                html = `
                    <div style="padding: 10px; background: #d4edda; border: 1px solid #c3e6cb; 
                                border-radius: 5px; color: #155724; margin-top: 10px;">
                        <strong>✅ ${r.message.message}</strong>
                    </div>
                `;
            } else if (r.message) {
                html = `
                    <div style="padding: 10px; background: #f8d7da; border: 1px solid #f5c6cb; 
                                border-radius: 5px; color: #721c24; margin-top: 10px;">
                        <strong>${r.message.message}</strong>
                    </div>
                `;
            }
            dialog.fields_dict.validation_html.$wrapper.html(html);
        }
    });
}

function import_excel_data(frm, file_url, dialog) {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.budget_plan.budget_plan.process_excel_import',
        args: {
            budget_name: frm.doc.name,
            file_url: file_url
        },
        freeze: true,
        freeze_message: __('📊 Importing budget data...'),
        callback: function(r) {
            if (r.message && r.message.success) {
                dialog.hide();
                frm.reload_doc();
                
                show_import_summary(r.message);
            } else if (r.message) {
                frappe.msgprint({
                    title: __('Import Failed'),
                    message: r.message.message,
                    indicator: 'red'
                });
            }
        }
    });
}

function show_import_summary(result) {
    var html = `
        <div style="padding: 20px;">
            <div style="text-align: center; margin-bottom: 20px;">
                <div style="font-size: 48px; margin-bottom: 10px;">✅</div>
                <h3 style="color: #28a745; margin: 0;">Import Completed!</h3>
            </div>
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 10px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px;">
                    <div style="text-align: center; padding: 15px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <div style="font-size: 32px; color: #28a745; font-weight: bold;">${result.imported}</div>
                        <div style="color: #6c757d; margin-top: 5px;">Imported</div>
                    </div>
                    
                    ${result.skipped > 0 ? `
                    <div style="text-align: center; padding: 15px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <div style="font-size: 32px; color: #ffc107; font-weight: bold;">${result.skipped}</div>
                        <div style="color: #6c757d; margin-top: 5px;">Skipped</div>
                    </div>
                    ` : ''}
                </div>
            </div>
            
            ${result.errors && result.errors.length > 0 ? `
            <div style="margin-top: 20px; padding: 15px; background: #fff3cd; border-radius: 8px; border-left: 4px solid #ffc107;">
                <strong>⚠️ Warnings/Errors:</strong>
                <ul style="margin-top: 10px; margin-bottom: 0;">
                    ${result.errors.slice(0, 5).map(error => `<li>${error}</li>`).join('')}
                    ${result.errors.length > 5 ? `<li><em>...and ${result.errors.length - 5} more</em></li>` : ''}
                </ul>
            </div>
            ` : ''}
            
            <div style="margin-top: 20px; padding: 15px; background: #e7f3ff; border-radius: 8px; border-left: 4px solid #007bff;">
                <strong>💡 Next Steps:</strong>
                <ul style="margin-top: 10px; margin-bottom: 0;">
                    <li>Review the imported budget lines below</li>
                    <li>Make any necessary adjustments</li>
                    <li>Save and submit the budget when ready</li>
                </ul>
            </div>
        </div>
    `;
    
    frappe.msgprint({
        title: __('📊 Import Summary'),
        message: html,
        wide: true,
        primary_action: {
            label: __('Got it!'),
            action: function() {
                // Close the dialog
            }
        }
    });
}

// =======================================
// BULK EDIT
// =======================================
function bulk_edit_budget_lines(frm) {
    if (!frm.doc.monthly_budget || frm.doc.monthly_budget.length === 0) {
        frappe.msgprint(__('No budget lines to edit'));
        return;
    }

    var d = new frappe.ui.Dialog({
        title: __('⚡ Bulk Edit Budget Lines'),
        fields: [
            {
                fieldname: 'operation',
                fieldtype: 'Select',
                label: __('Operation'),
                options: '\nApply Percentage Change\nSet Fixed Amount\nClear All Amounts',
                reqd: 1
            },
            {
                fieldname: 'percentage',
                fieldtype: 'Percent',
                label: __('Percentage'),
                depends_on: 'eval:doc.operation=="Apply Percentage Change"'
            },
            {
                fieldname: 'fixed_amount',
                fieldtype: 'Currency',
                label: __('Fixed Amount'),
                depends_on: 'eval:doc.operation=="Set Fixed Amount"'
            },
            {
                fieldname: 'apply_to',
                fieldtype: 'Select',
                label: __('Apply To'),
                options: 'All Months\nSpecific Months',
                default: 'All Months'
            },
            {
                fieldname: 'selected_months',
                fieldtype: 'MultiSelect',
                label: __('Select Months'),
                options: 'January\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember',
                depends_on: 'eval:doc.apply_to=="Specific Months"'
            }
        ],
        primary_action_label: __('Apply'),
        primary_action: function(values) {
            apply_bulk_edit(frm, values);
            d.hide();
        }
    });

    d.show();
}

function apply_bulk_edit(frm, values) {
    var months_map = {
        'January': 'jan', 'February': 'feb', 'March': 'mar', 'April': 'apr',
        'May': 'may', 'June': 'jun', 'July': 'jul', 'August': 'aug',
        'September': 'sep', 'October': 'oct', 'November': 'nov', 'December': 'dec'
    };

    var months_to_edit = [];
    
    if (values.apply_to === 'All Months') {
        months_to_edit = Object.values(months_map);
    } else if (values.selected_months) {
        var selected = values.selected_months.split(',');
        months_to_edit = selected.map(function(m) { return months_map[m.trim()]; });
    }

    var updated_count = 0;

    frm.doc.monthly_budget.forEach(function(row) {
        months_to_edit.forEach(function(month) {
            if (values.operation === 'Apply Percentage Change') {
                var current = flt(row[month] || 0);
                var new_value = current * (1 + values.percentage / 100);
                frappe.model.set_value(row.doctype, row.name, month, new_value);
                updated_count++;
            } else if (values.operation === 'Set Fixed Amount') {
                frappe.model.set_value(row.doctype, row.name, month, values.fixed_amount);
                updated_count++;
            } else if (values.operation === 'Clear All Amounts') {
                frappe.model.set_value(row.doctype, row.name, month, 0);
                updated_count++;
            }
        });
    });

    frm.refresh_field('monthly_budget');
    update_budget_metrics(frm);

    frappe.show_alert({
        message: __('✅ Updated {0} values', [updated_count]),
        indicator: 'green'
    }, 5);
}

// =======================================
// GET SUMMARY
// =======================================
function get_budget_summary(frm) {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.budget_plan.budget_plan.get_budget_summary',
        args: {budget_name: frm.doc.name},
        freeze: true,
        freeze_message: __('📊 Loading summary...'),
        callback: function(r) {
            if (r.message && r.message.success) {
                show_summary_dialog(r.message.summary);
            }
        }
    });
}

function show_summary_dialog(summary) {
    var html = `
        <div style="padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                <h2 style="margin: 0 0 10px 0;">📊 ${summary.budget_name || 'Budget Summary'}</h2>
                <p style="margin: 0; opacity: 0.9;">${summary.company} • ${summary.fiscal_year}</p>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px;">
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #28a745;">
                    <div style="font-size: 12px; color: #6c757d; margin-bottom: 5px;">Total Budget</div>
                    <div style="font-size: 24px; font-weight: bold; color: #28a745;">${format_currency(summary.total_budget)}</div>
                </div>
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #007bff;">
                    <div style="font-size: 12px; color: #6c757d; margin-bottom: 5px;">Status</div>
                    <div style="font-size: 20px; font-weight: bold; color: #007bff;">${summary.status}</div>
                </div>
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #6c757d;">
                    <div style="font-size: 12px; color: #6c757d; margin-bottom: 5px;">Type</div>
                    <div style="font-size: 18px; font-weight: bold;">${summary.is_group ? 'Group Budget' : 'Standard'}</div>
                </div>
            </div>
            
            <h4>📅 Monthly Breakdown</h4>
            <table class="table table-bordered" style="margin-top: 10px;">
                <thead style="background: #667eea; color: white;">
                    <tr>
                        <th>Month</th>
                        <th style="text-align: right;">Amount</th>
                    </tr>
                </thead>
                <tbody>`;
    
    var months = {
        'jan': 'January', 'feb': 'February', 'mar': 'March', 'apr': 'April',
        'may': 'May', 'jun': 'June', 'jul': 'July', 'aug': 'August',
        'sep': 'September', 'oct': 'October', 'nov': 'November', 'dec': 'December'
    };
    
    Object.keys(months).forEach(function(key) {
        if (summary.monthly_breakdown && summary.monthly_breakdown[key]) {
            html += `
                <tr>
                    <td><strong>${months[key]}</strong></td>
                    <td style="text-align: right;">${format_currency(summary.monthly_breakdown[key])}</td>
                </tr>`;
        }
    });
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    frappe.msgprint({
        title: __('📊 Budget Summary'),
        message: html,
        wide: true
    });
}

// =======================================
// COPY FROM PREVIOUS YEAR
// =======================================
function copy_from_previous_year(frm) {
    var d = new frappe.ui.Dialog({
        title: __('📋 Copy from Previous Budget'),
        fields: [
            {
                fieldname: 'previous_budget',
                fieldtype: 'Link',
                label: __('Previous Budget'),
                options: 'Budget Plan',
                get_query: function() {
                    return {
                        filters: {
                            company: frm.doc.company,
                            docstatus: 1,
                            name: ['!=', frm.doc.name]
                        }
                    };
                },
                reqd: 1
            },
            {
                fieldname: 'apply_adjustment',
                fieldtype: 'Check',
                label: __('Apply Adjustment'),
                default: 0
            },
            {
                fieldname: 'adjustment_percentage',
                fieldtype: 'Percent',
                label: __('Adjustment %'),
                depends_on: 'eval:doc.apply_adjustment',
                description: __('Positive for increase, negative for decrease')
            }
        ],
        primary_action_label: __('✅ Copy'),
        primary_action: function(values) {
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.budget_plan.budget_plan.copy_from_previous_budget',
                args: {
                    source_budget: values.previous_budget,
                    target_budget: frm.doc.name,
                    apply_growth: values.apply_adjustment ? 1 : 0,
                    growth_rate: values.adjustment_percentage || 0
                },
                freeze: true,
                freeze_message: __('📋 Copying budget...'),
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frm.reload_doc();
                        frappe.show_alert({
                            message: '✅ ' + r.message.message,
                            indicator: 'green'
                        }, 5);
                        d.hide();
                    }
                }
            });
        }
    });
    d.show();
}

// =======================================
// UTILITY FUNCTIONS
// =======================================
function set_default_fiscal_year(frm) {
    frappe.call({
        method: 'frappe.client.get_value',
        args: {
            doctype: 'Fiscal Year',
            filters: {disabled: 0},
            fieldname: 'name',
            order_by: 'year_start_date desc'
        },
        callback: function(r) {
            if (r.message && r.message.name) {
                frm.set_value('fiscal_year', r.message.name);
            }
        }
    });
}

function load_company_defaults(frm) {
    if (!frm.doc.company) return;
    
    frappe.call({
        method: 'frappe.client.get_value',
        args: {
            doctype: 'Company',
            filters: {name: frm.doc.company},
            fieldname: ['default_currency']
        },
        callback: function(r) {
            if (r.message && r.message.default_currency && !frm.doc.currency) {
                frm.set_value('currency', r.message.default_currency);
            }
        }
    });
}

function get_fiscal_year_dates(frm) {
    frappe.call({
        method: 'frappe.client.get_value',
        args: {
            doctype: 'Fiscal Year',
            filters: {name: frm.doc.fiscal_year},
            fieldname: ['year_start_date', 'year_end_date']
        },
        callback: function(r) {
            if (r.message) {
                if (!frm.doc.start_date) {
                    frm.set_value('start_date', r.message.year_start_date);
                }
                if (!frm.doc.end_date) {
                    frm.set_value('end_date', r.message.year_end_date);
                }
            }
        }
    });
}

function set_status_indicator(frm) {
    if (frm.doc.budget_status) {
        var colors = {
            'Draft': 'grey',
            'Pending Approval': 'orange',
            'Approved': 'blue',
            'Active': 'green',
            'Locked': 'red',
            'Closed': 'darkgrey'
        };
        frm.page.set_indicator(frm.doc.budget_status, colors[frm.doc.budget_status] || 'grey');
    }
}

function update_budget_metrics(frm) {
    if (!frm.doc.monthly_budget) return;
    
    var total = 0;
    var months = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'];
    
    frm.doc.monthly_budget.forEach(function(row) {
        var row_total = 0;
        months.forEach(function(m) {
            row_total += flt(row[m] || 0);
        });
        total += row_total;
    });
    
    frm.set_value('total_budget_amount', total);
}

function format_currency(value) {
    return frappe.format(value, {fieldtype: 'Currency'});
}

function setup_keyboard_shortcuts(frm) {
    $(document).off('keydown.budget_shortcuts');
    $(document).on('keydown.budget_shortcuts', function(e) {
        // Ctrl+Shift+E = Export
        if (e.ctrlKey && e.shiftKey && e.keyCode === 69) {
            e.preventDefault();
            export_to_excel_advanced(frm);
        }
        // Ctrl+Shift+P = Projections
        if (e.ctrlKey && e.shiftKey && e.keyCode === 80) {
            e.preventDefault();
            if (frm.doc.enable_projection && frm.doc.docstatus === 0) {
                show_projection_dialog(frm);
            }
        }
    });
}

// =======================================
// CHILD TABLE HANDLERS
// =======================================
frappe.ui.form.on('Monthly Budget', {
    jan: function(frm) { update_budget_metrics(frm); },
    feb: function(frm) { update_budget_metrics(frm); },
    mar: function(frm) { update_budget_metrics(frm); },
    apr: function(frm) { update_budget_metrics(frm); },
    may: function(frm) { update_budget_metrics(frm); },
    jun: function(frm) { update_budget_metrics(frm); },
    jul: function(frm) { update_budget_metrics(frm); },
    aug: function(frm) { update_budget_metrics(frm); },
    sep: function(frm) { update_budget_metrics(frm); },
    oct: function(frm) { update_budget_metrics(frm); },
    nov: function(frm) { update_budget_metrics(frm); },
    dec: function(frm) { update_budget_metrics(frm); }
});

frappe.ui.form.on('Budget Branch Allocation', {
    allocation_percentage: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if (row.allocation_percentage && frm.doc.total_budget_amount) {
            frappe.model.set_value(cdt, cdn, 'allocated_amount', 
                frm.doc.total_budget_amount * row.allocation_percentage / 100);
        }
    }
});

frappe.ui.form.on('Budget Cost Center Allocation', {
    allocation_percentage: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if (row.allocation_percentage && frm.doc.total_budget_amount) {
            frappe.model.set_value(cdt, cdn, 'allocated_amount', 
                frm.doc.total_budget_amount * row.allocation_percentage / 100);
        }
    }
});