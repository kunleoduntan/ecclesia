// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["SFP - MQH"] = {
	"filters": [

	]
};

// Copyright (c) 2026, Ecclesia and contributors
// For license information, please see license.txt

frappe.query_reports["SFP - MQH"] = {
    "filters": [
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
            "default": new Date().getFullYear(),
            "reqd": 1
        },
        {
            "fieldname": "frequency",
            "label": __("Frequency"),
            "fieldtype": "Select",
            "options": ["Monthly", "Quarterly", "Half-Yearly"],
            "default": "Monthly",
            "reqd": 1
        },
        {
            "fieldname": "show_only_ytd",
            "label": __("Hide Zero YTD Rows"),
            "fieldtype": "Check",
            "default": 0
        },
        {
            "fieldname": "show_variance_only",
            "label": __("Highlight Significant Variance (>10%)"),
            "fieldtype": "Check",
            "default": 0
        }
    ],
    
    "formatter": function(value, row, column, data, default_formatter) {
        // Apply default formatting first
        value = default_formatter(value, row, column, data);
        
        if (!data || !data.account_name) {
            return value;
        }
        
        // Clean HTML from account name for comparison
        const clean_account_name = $('<div>').html(data.account_name).text().trim();
        
        // Define styling rules
        const styleRules = {
            // Main totals - Bright blue background
            totalAssets: {
                pattern: /^Total Assets$/,
                style: {
                    'color': '#000000',
                    'background-color': '#63C8FF',
                    'border-bottom': '2px solid #F1F5B6',
                    'font-weight': 'bold',
                    'font-size': '14px'
                }
            },
            totalLiabilities: {
                pattern: /^Total Equity & Liabilities$/,
                style: {
                    'color': '#000000',
                    'background-color': '#63C8FF',
                    'border-bottom': '2px solid #F1F5B6',
                    'font-weight': 'bold',
                    'font-size': '14px'
                }
            },
            
            // Section totals - Light blue
            sectionTotals: {
                pattern: /^Total - /,
                style: {
                    'color': '#000000',
                    'background-color': '#B3E5FC',
                    'font-weight': 'bold',
                    'border-top': '1px solid #81D4FA'
                }
            },
            
            // Headers - Gray background
            headers: {
                pattern: /^▶ /,
                style: {
                    'color': '#1565C0',
                    'background-color': '#ECEFF1',
                    'font-weight': 'bold',
                    'font-size': '13px',
                    'border-bottom': '1px solid #B0BEC5'
                }
            },
            
            // Retained earnings - Light green
            retainedEarnings: {
                pattern: /Retained Earnings/,
                style: {
                    'color': '#1B5E20',
                    'background-color': '#C8E6C9',
                    'font-style': 'italic'
                }
            }
        };
        
        // Apply styling based on account name
        let cellStyle = {};
        
        for (let ruleName in styleRules) {
            let rule = styleRules[ruleName];
            if (rule.pattern.test(clean_account_name)) {
                cellStyle = rule.style;
                break;
            }
        }
        
        // Variance highlighting for percentage columns
        if (column.fieldname && column.fieldname.endsWith('_var')) {
            const variance = parseFloat(data[column.fieldname]);
            
            if (!isNaN(variance)) {
                // Highlight significant positive variance (green)
                if (variance > 10) {
                    cellStyle = {
                        ...cellStyle,
                        'color': '#2E7D32',
                        'background-color': '#E8F5E9',
                        'font-weight': 'bold'
                    };
                }
                // Highlight significant negative variance (red)
                else if (variance < -10) {
                    cellStyle = {
                        ...cellStyle,
                        'color': '#C62828',
                        'background-color': '#FFEBEE',
                        'font-weight': 'bold'
                    };
                }
            }
        }
        
        // Apply cell styling
        if (Object.keys(cellStyle).length > 0) {
            const styleString = Object.entries(cellStyle)
                .map(([key, val]) => `${key}:${val}`)
                .join(';');
            
            return `<div style="${styleString}; width:100%; height:100%; display:flex; align-items:center; padding:0 8px;">${value}</div>`;
        }
        
        return value;
    },
    
    "onload": function(report) {
        // Add custom buttons
        report.page.add_inner_button(__("Export to Excel"), function() {
            report.export_report("xlsx");
        });
        
        report.page.add_inner_button(__("Print Report"), function() {
            report.print_report();
        });
        
        // Add refresh button with timestamp
        report.page.add_inner_button(__("Refresh"), function() {
            report.refresh();
            frappe.show_alert({
                message: __("Report refreshed at {0}", [frappe.datetime.now_time()]),
                indicator: "green"
            });
        });
    },
    
    "after_datatable_render": function(datatable_obj) {
        // Add tooltips to variance cells
        $(datatable_obj.wrapper).find('[data-fieldname$="_var"]').each(function() {
            const value = parseFloat($(this).text());
            if (!isNaN(value)) {
                let tooltip = "";
                if (value > 0) {
                    tooltip = "Increase of " + Math.abs(value).toFixed(2) + "% from last year";
                } else if (value < 0) {
                    tooltip = "Decrease of " + Math.abs(value).toFixed(2) + "% from last year";
                } else {
                    tooltip = "No change from last year";
                }
                $(this).attr("title", tooltip);
            }
        });
        
        // Make section headers collapsible
        $(datatable_obj.wrapper).find('div[data-row-index]').each(function() {
            const $row = $(this);
            const rowData = datatable_obj.datamanager.data[$row.data('row-index')];
            
            if (rowData && rowData.account_name && rowData.account_name.includes('▶')) {
                $row.css('cursor', 'pointer');
                $row.find('.dt-cell__content').first().prepend('<i class="fa fa-chevron-down" style="margin-right:5px;"></i>');
                
                // Store section name for collapsing
                const sectionName = rowData.account_name.replace('▶', '').trim();
                $row.data('section', sectionName);
            }
        });
    },
    
    "get_datatable_options": function(options) {
        // Customize datatable options
        return Object.assign(options, {
            checkboxColumn: false,
            inlineFilters: true,
            layout: 'fluid',
            serialNoColumn: false,
            clusterize: true,  // Better performance for large datasets
            dynamicRowHeight: false
        });
    },
    
    "get_chart_data": function(columns, result) {
        // Chart is generated from Python, but we can customize here
        if (result && result.chart) {
            return result.chart;
        }
        return null;
    }
};

// Utility functions for report analysis
frappe.provide("frappe.reports.sfp_analysis");

frappe.reports.sfp_analysis = {
    // Calculate key financial ratios
    calculate_ratios: function(data) {
        let ratios = {};
        
        // Find key rows
        let current_assets = 0;
        let current_liabilities = 0;
        let total_assets = 0;
        let total_equity = 0;
        
        data.forEach(function(row) {
            const name = $('<div>').html(row.account_name || '').text().trim();
            
            if (name === 'Total - Current Assets') {
                current_assets = row.year_to_date || 0;
            } else if (name === 'Total - Current Liabilities') {
                current_liabilities = row.year_to_date || 0;
            } else if (name === 'Total Assets') {
                total_assets = row.year_to_date || 0;
            } else if (name === 'Total - Equity') {
                total_equity = row.year_to_date || 0;
            }
        });
        
        // Calculate ratios
        if (current_liabilities !== 0) {
            ratios.current_ratio = (current_assets / current_liabilities).toFixed(2);
        }
        
        if (total_assets !== 0) {
            ratios.debt_to_assets = ((total_assets - total_equity) / total_assets * 100).toFixed(2);
            ratios.equity_ratio = (total_equity / total_assets * 100).toFixed(2);
        }
        
        return ratios;
    },
    
    // Show analysis dialog
    show_analysis: function(data) {
        const ratios = this.calculate_ratios(data);
        
        let analysis_html = `
            <div style="padding: 20px;">
                <h3>Financial Ratios & Analysis</h3>
                <table class="table table-bordered" style="margin-top: 20px;">
                    <tr>
                        <th style="width: 50%;">Ratio</th>
                        <th style="width: 30%;">Value</th>
                        <th style="width: 20%;">Status</th>
                    </tr>
        `;
        
        // Current Ratio
        if (ratios.current_ratio) {
            let status = ratios.current_ratio >= 2 ? 
                '<span class="indicator green">Good</span>' :
                ratios.current_ratio >= 1 ?
                '<span class="indicator orange">Fair</span>' :
                '<span class="indicator red">Weak</span>';
            
            analysis_html += `
                <tr>
                    <td><strong>Current Ratio</strong><br><small>Current Assets / Current Liabilities</small></td>
                    <td>${ratios.current_ratio}</td>
                    <td>${status}</td>
                </tr>
            `;
        }
        
        // Debt to Assets
        if (ratios.debt_to_assets) {
            let status = ratios.debt_to_assets <= 40 ?
                '<span class="indicator green">Good</span>' :
                ratios.debt_to_assets <= 60 ?
                '<span class="indicator orange">Fair</span>' :
                '<span class="indicator red">High</span>';
            
            analysis_html += `
                <tr>
                    <td><strong>Debt to Assets Ratio</strong><br><small>(Total Assets - Equity) / Total Assets</small></td>
                    <td>${ratios.debt_to_assets}%</td>
                    <td>${status}</td>
                </tr>
            `;
        }
        
        // Equity Ratio
        if (ratios.equity_ratio) {
            let status = ratios.equity_ratio >= 60 ?
                '<span class="indicator green">Strong</span>' :
                ratios.equity_ratio >= 40 ?
                '<span class="indicator orange">Fair</span>' :
                '<span class="indicator red">Weak</span>';
            
            analysis_html += `
                <tr>
                    <td><strong>Equity Ratio</strong><br><small>Total Equity / Total Assets</small></td>
                    <td>${ratios.equity_ratio}%</td>
                    <td>${status}</td>
                </tr>
            `;
        }
        
        analysis_html += `
                </table>
                <div style="margin-top: 20px;">
                    <h4>Interpretation:</h4>
                    <ul>
                        <li><strong>Current Ratio:</strong> Measures ability to pay short-term obligations. Ideal: > 2.0</li>
                        <li><strong>Debt to Assets:</strong> Shows financial leverage. Lower is better. Ideal: < 40%</li>
                        <li><strong>Equity Ratio:</strong> Indicates financial stability. Higher is better. Ideal: > 60%</li>
                    </ul>
                </div>
            </div>
        `;
        
        frappe.msgprint({
            title: __("Financial Analysis"),
            message: analysis_html,
            indicator: "blue",
            wide: true
        });
    }
};