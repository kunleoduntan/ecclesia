// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt
/* eslint-disable */



frappe.query_reports["Enterprise Payroll Report"] = {
    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            reqd: 1,
            default: frappe.defaults.get_user_default("Company")
        },
        {
            fieldname: "report_type",
            label: __("Report Type"),
            fieldtype: "Select",
            options: ["Monthly", "Yearly"],
            default: "Monthly",
            reqd: 1,
            on_change: function() {
                let report_type = frappe.query_report.get_filter_value('report_type');
                
                // Show/hide filters based on report type
                frappe.query_report.toggle_filter_display('from_date', report_type === 'Monthly');
                frappe.query_report.toggle_filter_display('to_date', report_type === 'Monthly');
                frappe.query_report.toggle_filter_display('year', report_type === 'Yearly');
            }
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_start(),
            depends_on: "eval:doc.report_type=='Monthly'"
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_end(),
            depends_on: "eval:doc.report_type=='Monthly'"
        },
        {
            fieldname: "year",
            label: __("Year"),
            fieldtype: "Select",
            options: get_year_options(),
            default: new Date().getFullYear().toString(),
            depends_on: "eval:doc.report_type=='Yearly'"
        },
        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee"
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department"
        },
        {
            fieldname: "cost_center",
            label: __("Cost Center"),
            fieldtype: "Link",
            options: "Cost Center"
        },
        {
            fieldname: "branch",
            label: __("Branch"),
            fieldtype: "Link",
            options: "Branch"
        },
        {
            fieldname: "group_by",
            label: __("Group By"),
            fieldtype: "Select",
            options: ["", "Department", "Cost Center", "Branch", "Employment Type"],
            default: ""
        }
    ],

    onload: function(report) {
        // Add custom buttons
        report.page.add_inner_button(__("Export Excel"), function() {
            export_excel(report);
        }, __("Export"));

        report.page.add_inner_button(__("Download Summary"), function() {
            download_summary(report);
        }, __("Actions"));

        report.page.add_inner_button(__("Department Analysis"), function() {
            show_department_analysis(report);
        }, __("Analytics"));

        report.page.add_inner_button(__("Cost Center Analysis"), function() {
            show_cost_center_analysis(report);
        }, __("Analytics"));
    },

    formatter: function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        // Style group headers
        if (data && data.is_group_header) {
            if (column.fieldname === "employee_name") {
                value = `<span style="font-weight: bold; color: #1F4788; font-size: 1.1em;">
                    ${value}
                </span>`;
            }
            return value;
        }

        // Style subtotals
        if (data && data.is_subtotal) {
            if (column.fieldname === "employee_name") {
                value = `<span style="font-weight: bold; color: #4472C4;">
                    ${value}
                </span>`;
            } else if (["gross_pay", "total_deductions", "net_pay"].includes(column.fieldname)) {
                value = `<span style="font-weight: bold; color: #4472C4;">
                    ${value}
                </span>`;
            }
            return value;
        }

        // Color code amounts
        if (column.fieldname === "gross_pay" && data && data.gross_pay) {
            value = `<span class="text-success font-weight-bold">${value}</span>`;
        }
        if (column.fieldname === "total_deductions" && data && data.total_deductions) {
            value = `<span class="text-warning font-weight-bold">${value}</span>`;
        }
        if (column.fieldname === "net_pay" && data && data.net_pay) {
            value = `<span class="text-primary font-weight-bold">${value}</span>`;
        }

        // Highlight earning components
        if (column.fieldname && column.fieldname.startsWith("component_") && data) {
            const comp_value = data[column.fieldname];
            if (comp_value && comp_value > 0) {
                // Check if it's an earning or deduction based on column position
                value = `<span class="font-weight-bold">${value}</span>`;
            }
        }

        return value;
    },

    get_datatable_options(options) {
        return Object.assign(options, {
            checkboxColumn: true,
            events: {
                onCheckRow: function(data) {
                    if (!frappe.query_report.selected_rows) {
                        frappe.query_report.selected_rows = [];
                    }
                    
                    const row_name = data[0] ? data[0].content : null;
                    if (row_name) {
                        const index = frappe.query_report.selected_rows.indexOf(row_name);
                        if (index === -1) {
                            frappe.query_report.selected_rows.push(row_name);
                        } else {
                            frappe.query_report.selected_rows.splice(index, 1);
                        }
                    }
                }
            }
        });
    }
};

function get_year_options() {
    const current_year = new Date().getFullYear();
    const years = [];
    
    for (let i = current_year; i >= current_year - 5; i--) {
        years.push(i.toString());
    }
    
    return years.join("\n");
}

function export_excel(report) {
    const filters = report.get_values();

    if (!report.data || report.data.length === 0) {
        frappe.msgprint(__("No data to export"));
        return;
    }

    frappe.call({
        method: "general.general_biz_apps.report.enterprise_payroll_report.enterprise_payroll_report.export_excel",
        args: {
            filters: filters
        },
        freeze: true,
        freeze_message: __("Generating Excel Report..."),
        callback: function(r) {
            if (r.message) {
                window.open(r.message.file_url);
                frappe.show_alert({
                    message: __("Excel report exported successfully"),
                    indicator: "green"
                }, 5);
            }
        },
        error: function(r) {
            frappe.msgprint({
                title: __("Export Failed"),
                message: __("Failed to generate Excel report. Please try again."),
                indicator: "red"
            });
        }
    });
}

function download_summary(report) {
    const data = report.data;
    const filters = report.get_values();

    if (!data || data.length === 0) {
        frappe.msgprint(__("No data available"));
        return;
    }

    // Calculate summary statistics
    let total_employees = 0;
    let total_gross = 0;
    let total_deductions = 0;
    let total_net = 0;
    let departments = new Set();
    let cost_centers = new Set();

    data.forEach(row => {
        if (row.employee && !row.is_group_header && !row.is_subtotal) {
            total_employees++;
            total_gross += row.gross_pay || 0;
            total_deductions += row.total_deductions || 0;
            total_net += row.net_pay || 0;
            
            if (row.department) departments.add(row.department);
            if (row.cost_center) cost_centers.add(row.cost_center);
        }
    });

    const avg_gross = total_employees > 0 ? total_gross / total_employees : 0;
    const avg_net = total_employees > 0 ? total_net / total_employees : 0;
    const deduction_rate = total_gross > 0 ? (total_deductions / total_gross * 100) : 0;

    const period_text = filters.report_type === "Yearly" 
        ? `Year: ${filters.year}` 
        : `${filters.from_date} to ${filters.to_date}`;

    const summary_html = `
        <div class="payroll-summary" style="padding: 20px;">
            <h4 style="color: #1F4788; margin-bottom: 20px; border-bottom: 3px solid #1F4788; padding-bottom: 10px;">
                <i class="fa fa-money"></i> Payroll Summary Report
            </h4>
            
            <div class="row" style="margin-bottom: 20px;">
                <div class="col-md-6">
                    <table class="table table-bordered">
                        <tr style="background-color: #f8f9fa;">
                            <th colspan="2" style="text-align: center; background-color: #1F4788; color: white;">
                                Report Details
                            </th>
                        </tr>
                        <tr>
                            <th style="background-color: #f8f9fa; width: 40%;">Company</th>
                            <td>${filters.company}</td>
                        </tr>
                        <tr>
                            <th style="background-color: #f8f9fa;">Period</th>
                            <td>${period_text}</td>
                        </tr>
                        <tr>
                            <th style="background-color: #f8f9fa;">Report Type</th>
                            <td><span class="badge badge-info">${filters.report_type}</span></td>
                        </tr>
                    </table>
                </div>
                
                <div class="col-md-6">
                    <table class="table table-bordered">
                        <tr style="background-color: #f8f9fa;">
                            <th colspan="2" style="text-align: center; background-color: #1F4788; color: white;">
                                Organization Overview
                            </th>
                        </tr>
                        <tr>
                            <th style="background-color: #f8f9fa; width: 40%;">Total Employees</th>
                            <td><strong>${total_employees}</strong></td>
                        </tr>
                        <tr>
                            <th style="background-color: #f8f9fa;">Departments</th>
                            <td><strong>${departments.size}</strong></td>
                        </tr>
                        <tr>
                            <th style="background-color: #f8f9fa;">Cost Centers</th>
                            <td><strong>${cost_centers.size}</strong></td>
                        </tr>
                    </table>
                </div>
            </div>
            
            <table class="table table-bordered" style="margin-top: 15px;">
                <tr style="background-color: #f8f9fa;">
                    <th colspan="2" style="text-align: center; background-color: #4472C4; color: white;">
                        Financial Summary
                    </th>
                </tr>
                <tr>
                    <th style="background-color: #f8f9fa; width: 40%;">Total Gross Pay</th>
                    <td class="text-success"><strong>${format_currency(total_gross)}</strong></td>
                </tr>
                <tr>
                    <th style="background-color: #f8f9fa;">Total Deductions</th>
                    <td class="text-warning"><strong>${format_currency(total_deductions)}</strong></td>
                </tr>
                <tr style="background-color: #f0f0f0;">
                    <th style="background-color: #e7e6e6; font-size: 1.1em;">Total Net Pay</th>
                    <td class="text-primary" style="font-size: 1.1em;"><strong>${format_currency(total_net)}</strong></td>
                </tr>
                <tr>
                    <th style="background-color: #f8f9fa;">Average Gross Pay</th>
                    <td>${format_currency(avg_gross)}</td>
                </tr>
                <tr>
                    <th style="background-color: #f8f9fa;">Average Net Pay</th>
                    <td>${format_currency(avg_net)}</td>
                </tr>
                <tr>
                    <th style="background-color: #f8f9fa;">Deduction Rate</th>
                    <td><strong>${deduction_rate.toFixed(2)}%</strong></td>
                </tr>
            </table>
            
            <div class="alert alert-info" style="margin-top: 20px;">
                <i class="fa fa-info-circle"></i>
                <strong>Note:</strong> This is a ${filters.report_type.toLowerCase()} payroll report
                ${filters.report_type === "Yearly" ? "showing aggregated annual data" : "showing detailed monthly data"}.
            </div>
        </div>
    `;

    const d = new frappe.ui.Dialog({
        title: __("Payroll Summary"),
        size: "extra-large",
        fields: [
            {
                fieldtype: "HTML",
                options: summary_html
            }
        ],
        primary_action_label: __("Close"),
        primary_action: function() {
            d.hide();
        }
    });

    d.show();
}

function show_department_analysis(report) {
    const data = report.data;
    
    if (!data || data.length === 0) {
        frappe.msgprint(__("No data available"));
        return;
    }

    // Aggregate by department
    let dept_data = {};
    
    data.forEach(row => {
        if (row.employee && !row.is_group_header && !row.is_subtotal) {
            const dept = row.department || "No Department";
            
            if (!dept_data[dept]) {
                dept_data[dept] = {
                    employees: 0,
                    gross: 0,
                    deductions: 0,
                    net: 0
                };
            }
            
            dept_data[dept].employees++;
            dept_data[dept].gross += row.gross_pay || 0;
            dept_data[dept].deductions += row.total_deductions || 0;
            dept_data[dept].net += row.net_pay || 0;
        }
    });

    let table_html = `
        <div style="padding: 20px;">
            <h4 style="color: #1F4788; margin-bottom: 20px;">
                <i class="fa fa-building"></i> Department Analysis
            </h4>
            <table class="table table-bordered table-hover">
                <thead style="background-color: #4472C4; color: white;">
                    <tr>
                        <th>Department</th>
                        <th class="text-right">Employees</th>
                        <th class="text-right">Gross Pay</th>
                        <th class="text-right">Deductions</th>
                        <th class="text-right">Net Pay</th>
                        <th class="text-right">Avg per Employee</th>
                    </tr>
                </thead>
                <tbody>
    `;

    Object.keys(dept_data).sort().forEach(dept => {
        const d = dept_data[dept];
        const avg = d.employees > 0 ? d.net / d.employees : 0;
        
        table_html += `
            <tr>
                <td><strong>${dept}</strong></td>
                <td class="text-right">${d.employees}</td>
                <td class="text-right text-success">${format_currency(d.gross)}</td>
                <td class="text-right text-warning">${format_currency(d.deductions)}</td>
                <td class="text-right text-primary">${format_currency(d.net)}</td>
                <td class="text-right">${format_currency(avg)}</td>
            </tr>
        `;
    });

    table_html += `
                </tbody>
            </table>
        </div>
    `;

    frappe.msgprint({
        title: __("Department Analysis"),
        message: table_html,
        wide: true
    });
}

function show_cost_center_analysis(report) {
    const data = report.data;
    
    if (!data || data.length === 0) {
        frappe.msgprint(__("No data available"));
        return;
    }

    // Aggregate by cost center
    let cc_data = {};
    
    data.forEach(row => {
        if (row.employee && !row.is_group_header && !row.is_subtotal) {
            const cc = row.cost_center || "No Cost Center";
            
            if (!cc_data[cc]) {
                cc_data[cc] = {
                    employees: 0,
                    gross: 0,
                    deductions: 0,
                    net: 0
                };
            }
            
            cc_data[cc].employees++;
            cc_data[cc].gross += row.gross_pay || 0;
            cc_data[cc].deductions += row.total_deductions || 0;
            cc_data[cc].net += row.net_pay || 0;
        }
    });

    let table_html = `
        <div style="padding: 20px;">
            <h4 style="color: #1F4788; margin-bottom: 20px;">
                <i class="fa fa-sitemap"></i> Cost Center Analysis
            </h4>
            <table class="table table-bordered table-hover">
                <thead style="background-color: #4472C4; color: white;">
                    <tr>
                        <th>Cost Center</th>
                        <th class="text-right">Employees</th>
                        <th class="text-right">Gross Pay</th>
                        <th class="text-right">Deductions</th>
                        <th class="text-right">Net Pay</th>
                        <th class="text-right">% of Total</th>
                    </tr>
                </thead>
                <tbody>
    `;

    const total_net = Object.values(cc_data).reduce((sum, cc) => sum + cc.net, 0);

    Object.keys(cc_data).sort().forEach(cc => {
        const d = cc_data[cc];
        const percentage = total_net > 0 ? (d.net / total_net * 100) : 0;
        
        table_html += `
            <tr>
                <td><strong>${cc}</strong></td>
                <td class="text-right">${d.employees}</td>
                <td class="text-right text-success">${format_currency(d.gross)}</td>
                <td class="text-right text-warning">${format_currency(d.deductions)}</td>
                <td class="text-right text-primary">${format_currency(d.net)}</td>
                <td class="text-right">${percentage.toFixed(2)}%</td>
            </tr>
        `;
    });

    table_html += `
                </tbody>
            </table>
        </div>
    `;

    frappe.msgprint({
        title: __("Cost Center Analysis"),
        message: table_html,
        wide: true
    });
}