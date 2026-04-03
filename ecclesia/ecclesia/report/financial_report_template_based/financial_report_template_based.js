// Copyright (c) 2026, kunle Oduntan and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Financial Report Template Based"] = {
    "filters": [
        {
            "fieldname": "template",
            "label": __("Template"),
            "fieldtype": "Link",
            "options": "Financial Report Template",
            "reqd": 1,
            "get_query": function() {
                return {
                    "filters": {
                        "is_active": 1
                    }
                };
            },
            "on_change": function() {
                // Load template settings and update other filters
                let template = frappe.query_report.get_filter_value('template');
                if (template) {
                    frappe.db.get_doc('Financial Report Template', template).then(doc => {
                        // Update budget filter visibility
                        let budget_filter = frappe.query_report.get_filter('show_budget');
                        if (budget_filter) {
                            budget_filter.df.hidden = !doc.enable_budget_comparison;
                            budget_filter.refresh();
                        }
                        
                        // Show template info
                        frappe.show_alert({
                            message: __('Template loaded: {0} ({1})', [doc.template_name, doc.report_type]),
                            indicator: 'green'
                        }, 3);
                    });
                }
            }
        },
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "reqd": 1,
            "default": frappe.defaults.get_user_default("Company")
        },
        {
            "fieldname": "year",
            "label": __("Year"),
            "fieldtype": "Int",
            "reqd": 1,
            "default": new Date().getFullYear()
        },
        {
            "fieldname": "frequency",
            "label": __("Frequency"),
            "fieldtype": "Select",
            "options": "Monthly\nQuarterly\nHalf-Yearly",
            "default": "Monthly",
            "reqd": 1
        },
        {
            "fieldname": "hide_detail",
            "label": __("Hide Account Detail"),
            "fieldtype": "Check",
            "default": 0,
            "description": "Show only summary lines"
        },
        {
            "fieldname": "show_budget",
            "label": __("Show Budget Comparison"),
            "fieldtype": "Check",
            "default": 0,
            "hidden": 1,
            "description": "Compare actual vs budget (requires Budget Plan)"
        },
        {
            "fieldname": "budget_plan",
            "label": __("Budget Plan"),
            "fieldtype": "Link",
            "options": "Budget Plan",
            "depends_on": "eval:doc.show_budget==1",
            "get_query": function() {
                return {
                    "filters": {
                        "company": frappe.query_report.get_filter_value('company'),
                        "fiscal_year": frappe.query_report.get_filter_value('year'),
                        "docstatus": 1
                    }
                };
            }
        }
    ],
    
    "onload": function(report) {
        // Add custom buttons
        report.page.add_inner_button(__('Manage Templates'), function() {
            frappe.set_route('List', 'Financial Report Template');
        });
        
        report.page.add_inner_button(__('Create New Template'), function() {
            frappe.new_doc('Financial Report Template');
        });
        
        report.page.add_inner_button(__('Export to Excel'), function() {
            // Get current filters
            let filters = report.get_values();
            
            if (!filters.template) {
                frappe.msgprint(__('Please select a template first'));
                return;
            }
            
            // Show loading message
            frappe.show_alert({
                message: __('Generating Excel file...'),
                indicator: 'blue'
            });
            
            // Use open_url_post for proper file download
            let w = window.open(
                frappe.urllib.get_full_url(
                    "/api/method/ecclesia.ecclesia.report.financial_report_template_based.excel_export.download_excel"
                    + "?template_name=" + encodeURIComponent(filters.template)
                    + "&company=" + encodeURIComponent(filters.company)
                    + "&year=" + encodeURIComponent(filters.year)
                    + "&frequency=" + encodeURIComponent(filters.frequency || 'Monthly')
                    + "&show_budget=" + encodeURIComponent(filters.show_budget || 0)
                    + "&budget_plan=" + encodeURIComponent(filters.budget_plan || '')
                )
            );
            
            if (!w) {
                frappe.msgprint(__('Please enable popups for this site'));
            }
        }, __('Export'));
        
        // Add help button
        report.page.add_inner_button(__('Help'), function() {
            let help_html = `
                <div style="padding: 15px;">
                    <h4>Financial Report - Template Based</h4>
                    <p>This report uses configurable templates to generate financial statements.</p>
                    
                    <h5>Quick Start:</h5>
                    <ol>
                        <li>Select a template from the dropdown</li>
                        <li>Choose company and year</li>
                        <li>Select frequency (Monthly, Quarterly, or Half-Yearly)</li>
                        <li>Click 'Refresh' to run the report</li>
                    </ol>
                    
                    <h5>Customization:</h5>
                    <ul>
                        <li><strong>Row Colors:</strong> Set "Row Background Color" in template lines</li>
                        <li><strong>Borders:</strong> Choose border style for each line</li>
                        <li><strong>Bold Text:</strong> Check "Bold" option</li>
                        <li><strong>Indentation:</strong> Set indent level (0-3)</li>
                    </ul>
                    
                    <h5>Features:</h5>
                    <ul>
                        <li>Year-over-Year comparison</li>
                        <li>Budget comparison (requires Budget Plan)</li>
                        <li>Beautiful Excel export with colors and borders</li>
                        <li>Flexible account mapping (5 methods)</li>
                    </ul>
                </div>
            `;
            
            frappe.msgprint({
                title: __('Help'),
                message: help_html,
                wide: true
            });
        }, __('Actions'));
    },
    
    "after_datatable_render": function(datatable_obj) {
        // Apply custom styling to specific rows
        $(datatable_obj.wrapper).find('.dt-cell').each(function() {
            let $cell = $(this);
            let content = $cell.html();
            
            // Highlight negative values in red
            if ($cell.hasClass('dt-cell--col-currency') || $cell.hasClass('dt-cell--col-float')) {
                let value = parseFloat($cell.text().replace(/[^0-9.-]/g, ''));
                if (!isNaN(value) && value < 0) {
                    $cell.css('color', 'red');
                }
            }
            
            // Highlight large variances
            if (content && content.includes('%')) {
                let variance = parseFloat(content.replace(/[^0-9.-]/g, ''));
                if (!isNaN(variance) && Math.abs(variance) > 10) {
                    $cell.css({
                        'background-color': Math.abs(variance) > 20 ? '#ffcccc' : '#ffffcc',
                        'font-weight': 'bold'
                    });
                }
            }
        });
    },
    
    "formatter": function(value, row, column, data, default_formatter) {
        let cell_style = {};
        
        // Apply default formatting first
        value = default_formatter(value, row, column, data);
        
        // Get styling from data._style (comes from Financial Report Line doctype)
        if (data && data._style) {
            let style_str = data._style;
            
            // Extract background color (from row_color field or template defaults)
            if (style_str.includes('background-color')) {
                let match = style_str.match(/background-color:\s*([^;]+)/);
                if (match) {
                    cell_style['background-color'] = match[1].trim();
                }
            }
            
            // Extract font weight
            if (style_str.includes('font-weight: bold')) {
                cell_style['font-weight'] = 'bold';
            }
            
            // Extract border styling
            if (style_str.includes('border-top:')) {
                let match = style_str.match(/border-top:\s*([^;]+)/);
                if (match) {
                    cell_style['border-top'] = match[1].trim();
                }
            }
            if (style_str.includes('border-bottom:')) {
                let match = style_str.match(/border-bottom:\s*([^;]+)/);
                if (match) {
                    cell_style['border-bottom'] = match[1].trim();
                }
            }
        }
        
        // Add styling to account names based on indent
        if (column.fieldname === "account_name" && typeof value === 'string') {
            // Count leading spaces to determine indent
            let indent = 0;
            let stripped_value = value;
            while (stripped_value.startsWith('&nbsp;') || stripped_value.startsWith('    ')) {
                indent++;
                stripped_value = stripped_value.replace(/^(&nbsp;|    )/, '');
            }
            
            if (indent > 0) {
                stripped_value = `<span style="padding-left: ${indent * 20}px;">${stripped_value}</span>`;
                value = stripped_value;
            }
        }
        
        // Format currency columns - highlight negatives in red
        if (column.fieldtype === "Currency" && value) {
            let num_value = parseFloat(value.replace(/[^0-9.-]/g, ''));
            if (!isNaN(num_value) && num_value < 0) {
                // Only color red if background isn't dark
                if (!cell_style['background-color'] || 
                    !cell_style['background-color'].includes('darkblue') && 
                    !cell_style['background-color'].includes('rgb(0')) {
                    cell_style['color'] = 'red';
                }
            }
        }
        
        // Format variance columns
        if (column.fieldtype === "Percent" && value) {
            let variance_str = value.toString().replace(/%/g, '').replace(/,/g, '');
            let variance = parseFloat(variance_str);
            if (!isNaN(variance)) {
                let color = variance >= 0 ? 'green' : 'red';
                if (Math.abs(variance) > 20) {
                    if (!cell_style['font-weight']) {
                        cell_style['font-weight'] = 'bold';
                    }
                    cell_style['color'] = color;
                } else if (Math.abs(variance) > 10) {
                    cell_style['color'] = color;
                }
            }
        }
        
        // Return cell with full styling (all from doctype, no hardcoded colors)
        if (Object.keys(cell_style).length > 0) {
            let style_string = Object.entries(cell_style)
                .map(([k, v]) => `${k}:${v}`)
                .join(';');
            return `<div style="${style_string}; width: 100%; height: 100%; display: flex; align-items: center; padding: 0 8px;">${value}</div>`;
        }
        
        return value;
    }
};