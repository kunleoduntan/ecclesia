// Copyright (c) 2026, kunle Oduntan and contributors
// For license information, please see license.txt

frappe.query_reports["P&L by Business Units"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": "Company",
            "fieldtype": "Link",
            "options": "Company",
            "reqd": 1,
            "default": frappe.defaults.get_user_default("Company")
        },
        {
            "fieldname": "cost_center",
            "label": "Cost Center Group",
            "fieldtype": "Link",
            "options": "Cost Center",
            "get_query": function() {
                return {
                    "filters": {
                        "is_group": 1
                    }
                };
            },
            "reqd": 1
        },
        {
            "fieldname": "from_date",
            "label": "From Date",
            "fieldtype": "Date",
            "default": frappe.datetime.month_start(),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": "To Date",
            "fieldtype": "Date",
            "default": frappe.datetime.month_end(),
            "reqd": 1
        },
        {
            "fieldname": "section_break_1",
            "fieldtype": "Section Break",
            "label": "Cost Allocation"
        },
        {
            "fieldname": "share_corporate_cost",
            "label": "Share Corporate Cost",
            "fieldtype": "Check",
            "default": 0
        },
        {
            "fieldname": "select_cc_to_share",
            "label": "Cost Center to Share",
            "fieldtype": "Link",
            "options": "Cost Center",
            "depends_on": "eval:doc.share_corporate_cost==1"
        },
        {
            "fieldname": "section_break_2",
            "fieldtype": "Section Break",
            "label": "Display Options"
        },
        {
            "fieldname": "hide_detail",
            "label": "Hide Account Details",
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
        
        // Extract clean account name (remove HTML tags)
        const cleanName = $('<div>').html(data.account_name).text().trim();
        
        // Define styling rules with priority order
        let cellStyle = {};
        
        // 1. Final Profit - Highest Priority (Dark Blue)
        if (cleanName === "Profit for the year" || cleanName === "Net Profit After Tax") {
            cellStyle = {
                'background-color': '#00008B',
                'color': '#FFFFFF',
                'font-weight': 'bold'
            };
        }
        
        // 2. Key Metrics (Blue with border)
        else if (["Gross Profit", "EBITDA", "EBIT", "Operating Profit", "Profit Before Tax"].includes(cleanName)) {
            cellStyle = {
                'background-color': '#CCE5FF',
                'color': '#000000',
                'font-weight': 'bold',
                'border-top': '2px solid #0066CC',
                'border-bottom': '2px solid #0066CC'
            };
        }
        
        // 3. Total Rows (Yellow)
        else if (cleanName.startsWith("Total - ")) {
            cellStyle = {
                'background-color': '#FFFF99',
                'color': '#000000',
                'font-weight': 'bold'
            };
        }
        
        // 4. Cost Allocation (Pink)
        else if (cleanName === "Shared Corporate Cost") {
            cellStyle = {
                'background-color': '#FADBD8',
                'color': '#000000',
                'font-weight': 'bold'
            };
        }
        
        // 5. Revenue lines (Light Green)
        else if (cleanName.includes("Revenue") || cleanName.includes("Sales") || cleanName.includes("Income")) {
            cellStyle = {
                'background-color': '#E8F5E9',
                'color': '#000000'
            };
        }
        
        // 6. Expense lines (Light Red)
        else if (cleanName.includes("Expense") || cleanName.includes("Cost") || 
                 cleanName.includes("Depreciation") || cleanName.includes("Amortisation")) {
            cellStyle = {
                'background-color': '#FFEBEE',
                'color': '#000000'
            };
        }
        
        // Apply cell styling if any rules matched
        if (Object.keys(cellStyle).length > 0) {
            let styleString = Object.entries(cellStyle)
                .map(([k, v]) => `${k}:${v}`)
                .join(';');
            
            return `<div style="${styleString}; width: 100%; height: 100%; display: flex; align-items: center; padding: 0 8px;">${value}</div>`;
        }
        
        // Handle negative values - red text
        if (column.fieldtype === "Currency" && typeof value === "string" && value.includes('-')) {
            return `<span style="color: #D32F2F; font-weight: 500;">${value}</span>`;
        }
        
        return value;
    },
    
    "onload": function(report) {
        // Add Beautiful Excel Export button
        report.page.add_inner_button(__('Export to Excel'), function() {
            frappe.dom.freeze(__('Generating Excel...'));
            
            let filters = report.get_values();
            
            frappe.call({
                method: "ecclesia.ecclesia.report.pl_by_business_units.pl_by_business_units.export_to_excel",
                args: {
                    filters: filters,
                    columns: report.columns,
                    data: report.data
                },
                callback: function(r) {
                    frappe.dom.unfreeze();
                    
                    if (r.message && r.message.file_url) {
                        // Open file in new tab
                        window.open(r.message.file_url, '_blank');
                        
                        frappe.show_alert({
                            message: __('Excel file generated successfully!'),
                            indicator: 'green'
                        });
                    }
                },
                error: function() {
                    frappe.dom.unfreeze();
                }
            });
        }, __('Tools'));
        
        // Add Print button
        report.page.set_secondary_action(__('Print'), function() {
            window.print();
        });
        
        // Add help button
        report.page.add_menu_item(__('Help'), function() {
            frappe.msgprint({
                title: __('P&L by Business Units - Help'),
                message: `
                    <h4>How to use this report:</h4>
                    <ol>
                        <li><strong>Cost Center Group</strong>: Select a parent cost center to show child cost centers as columns</li>
                        <li><strong>Date Range</strong>: Select from and to dates</li>
                        <li><strong>Hide Details</strong>: Check to show only totals without account drill-down</li>
                        <li><strong>Share Corporate Cost</strong>: Enable to distribute selected cost center's costs across other centers</li>
                    </ol>
                    <h4>Color Coding:</h4>
                    <ul>
                        <li><span style="background: #FFFF99; padding: 2px 8px;">Yellow</span> - Total rows</li>
                        <li><span style="background: #CCE5FF; padding: 2px 8px;">Blue</span> - Key metrics (Gross Profit, EBITDA, EBIT)</li>
                        <li><span style="background: #FADBD8; padding: 2px 8px;">Pink</span> - Cost allocation</li>
                        <li><span style="background: #00008B; color: white; padding: 2px 8px;">Dark Blue</span> - Final profit</li>
                    </ul>
                `,
                wide: true
            });
        });
    },
    
    // Custom chart (optional - shows summary chart)
    "get_chart_data": function(columns, result) {
        // Extract cost center names (exclude Account Name and Total columns)
        let cost_centers = columns.slice(1, -1).map(col => col.label);
        
        // Find key metrics
        let metrics = ["Gross Profit", "EBITDA", "EBIT", "Operating Profit"];
        let datasets = [];
        
        for (let metric of metrics) {
            let row = result.find(r => r.account_name === metric);
            if (row) {
                let values = cost_centers.map(cc => {
                    let fieldname = cc.toLowerCase().replace(/[^a-z0-9]/g, '_');
                    return row[fieldname] || 0;
                });
                
                datasets.push({
                    name: metric,
                    values: values
                });
            }
        }
        
        return {
            data: {
                labels: cost_centers,
                datasets: datasets
            },
            type: 'bar',
            colors: ['#7cd6fd', '#5e64ff', '#743ee2', '#ff5858']
        };
    }
};