// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt
/* eslint-disable */


frappe.query_reports["PAYE Deduction Report"] = {
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
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_start()
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_end()
        },
        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee"
        },
        {
            fieldname: "state",
            label: __("State"),
            fieldtype: "Link",
            options: "State",
            description: __("Filter by Employee State")
        },
        {
            fieldname: "show_errors_only",
            label: __("Show Validation Errors Only"),
            fieldtype: "Check",
            default: 0
        },
        {
            fieldname: "group_by_state",
            label: __("Group by State"),
            fieldtype: "Check",
            default: 0
        }
    ],

    onload: function(report) {
        // Add custom buttons
        report.page.add_inner_button(__("Export PAYE Template"), function() {
            export_paye_template(report);
        }, __("Export"));

        report.page.add_inner_button(__("Export Detailed Excel"), function() {
            export_detailed_excel(report);
        }, __("Export"));

        report.page.add_inner_button(__("Download Summary"), function() {
            download_summary(report);
        }, __("Export"));

        report.page.add_inner_button(__("Generate Tax Remittance"), function() {
            generate_tax_remittance(report);
        }, __("Actions"));
    },

    formatter: function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        // Highlight rows with missing information
        if (data && column.fieldname !== "tax_deducted") {
            if (!data.tin || !data.state) {
                if (column.fieldname === "tin" && !data.tin) {
                    value = `<span class="text-danger" title="Missing TIN">
                        <i class="fa fa-exclamation-triangle"></i> ${value || "Not Set"}
                    </span>`;
                }
                if (column.fieldname === "state" && !data.state) {
                    value = `<span class="text-danger" title="Missing State">
                        <i class="fa fa-exclamation-triangle"></i> ${value || "Not Set"}
                    </span>`;
                }
            }
        }

        // Color code tax amounts
        if (column.fieldname === "gross" && data && data.gross) {
            value = `<span class="text-info font-weight-bold">${value}</span>`;
        }
        if (column.fieldname === "tax_deducted" && data && data.tax_deducted) {
            value = `<span style="color: #ff6384;" class="font-weight-bold">${value}</span>`;
        }

        // Highlight group totals
        if (data && data.indent === 0 && column.fieldname === "employee_name") {
            value = `<span class="font-weight-bold text-muted">${value}</span>`;
        }

        return value;
    },

    get_datatable_options(options) {
        return Object.assign(options, {
            checkboxColumn: true,
            events: {
                onCheckRow: function(data) {
                    // Store selected rows for export
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

function export_paye_template(report) {
    const filters = report.get_values();

    if (!report.data || report.data.length === 0) {
        frappe.msgprint(__("No data to export"));
        return;
    }

    frappe.call({
        method: "general.general_biz_apps.report.paye_deduction_report.paye_deduction_report.export_paye_format",
        args: {
            filters: filters
        },
        freeze: true,
        freeze_message: __("Generating PAYE Template..."),
        callback: function(r) {
            if (r.message) {
                // Download the file
                window.open(r.message.file_url);
                frappe.show_alert({
                    message: __("PAYE template exported successfully"),
                    indicator: "green"
                }, 5);
            }
        },
        error: function(r) {
            frappe.msgprint({
                title: __("Export Failed"),
                message: __("Failed to generate PAYE template. Please try again."),
                indicator: "red"
            });
        }
    });
}

function export_detailed_excel(report) {
    const filters = report.get_values();

    if (!report.data || report.data.length === 0) {
        frappe.msgprint(__("No data to export"));
        return;
    }

    frappe.call({
        method: "general.general_biz_apps.report.paye_deduction_report.paye_deduction_report.export_detailed_excel",
        args: {
            filters: filters
        },
        freeze: true,
        freeze_message: __("Generating Detailed Excel..."),
        callback: function(r) {
            if (r.message) {
                window.open(r.message.file_url);
                frappe.show_alert({
                    message: __("Detailed Excel exported successfully"),
                    indicator: "green"
                }, 5);
            }
        },
        error: function(r) {
            frappe.msgprint({
                title: __("Export Failed"),
                message: __("Failed to generate detailed Excel. Please try again."),
                indicator: "red"
            });
        }
    });
}

function generate_tax_remittance(report) {
    const data = report.data;
    const filters = report.get_values();

    if (!data || data.length === 0) {
        frappe.msgprint(__("No data available"));
        return;
    }

    frappe.prompt([
        {
            fieldname: "tax_authority",
            label: __("Tax Authority"),
            fieldtype: "Data",
            reqd: 1,
            default: "State Internal Revenue Service"
        },
        {
            fieldname: "remittance_date",
            label: __("Remittance Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.get_today()
        },
        {
            fieldname: "reference_number",
            label: __("Reference Number"),
            fieldtype: "Data"
        }
    ], function(values) {
        frappe.msgprint({
            title: __("Tax Remittance"),
            message: __("Tax remittance functionality would be implemented here. This would create a journal entry for tax payable and generate remittance documentation."),
            indicator: "blue"
        });
    }, __("Generate Tax Remittance"));
}

function download_summary(report) {
    const data = report.data;
    const filters = report.get_values();

    if (!data || data.length === 0) {
        frappe.msgprint(__("No data to export"));
        return;
    }

    // Calculate summary statistics
    let total_employees = 0;
    let total_gross = 0;
    let total_tax = 0;
    let employees_with_errors = 0;

    data.forEach(row => {
        if (row.employee) {
            total_employees++;
            total_gross += row.gross || 0;
            total_tax += row.tax_deducted || 0;
            
            if (!row.tin || !row.state) {
                employees_with_errors++;
            }
        }
    });

    const effective_rate = total_gross > 0 ? (total_tax / total_gross * 100) : 0;

    const summary_html = `
        <div class="paye-summary" style="padding: 20px;">
            <h4 style="color: #ff6384; margin-bottom: 20px; border-bottom: 2px solid #ff6384; padding-bottom: 10px;">
                PAYE Tax Deduction Summary
            </h4>
            <table class="table table-bordered" style="margin-top: 15px;">
                <tr>
                    <th style="background-color: #f8f9fa; width: 40%;">Period</th>
                    <td>${filters.from_date} to ${filters.to_date}</td>
                </tr>
                <tr>
                    <th style="background-color: #f8f9fa;">Company</th>
                    <td>${filters.company}</td>
                </tr>
                <tr>
                    <th style="background-color: #f8f9fa;">Total Employees</th>
                    <td><strong>${total_employees}</strong></td>
                </tr>
                <tr>
                    <th style="background-color: #f8f9fa;">Employees with Errors</th>
                    <td class="text-danger"><strong>${employees_with_errors}</strong></td>
                </tr>
                <tr>
                    <th style="background-color: #f8f9fa;">Total Gross Pay</th>
                    <td><strong>${format_currency(total_gross)}</strong></td>
                </tr>
                <tr style="background-color: #f0f0f0;">
                    <th style="background-color: #e7e6e6; font-size: 1.1em;">Total PAYE Tax Deducted</th>
                    <td style="color: #ff6384; font-size: 1.1em;"><strong>${format_currency(total_tax)}</strong></td>
                </tr>
                <tr>
                    <th style="background-color: #f8f9fa;">Effective Tax Rate (on Gross)</th>
                    <td><strong>${effective_rate.toFixed(2)}%</strong></td>
                </tr>
            </table>
            ${employees_with_errors > 0 ? `
                <div class="alert alert-warning" style="margin-top: 20px;">
                    <i class="fa fa-exclamation-triangle"></i>
                    <strong>Warning:</strong> ${employees_with_errors} employee(s) have missing tax information (TIN or State).
                    Please ensure all employees have TIN and State assigned for proper tax filing.
                </div>
            ` : ''}
            <div class="alert alert-info" style="margin-top: 20px;">
                <i class="fa fa-info-circle"></i>
                <strong>Note:</strong> PAYE (Pay As You Earn) is income tax deducted from employees' monthly salary
                and remitted to the relevant State Internal Revenue Service.
            </div>
        </div>
    `;

    const d = new frappe.ui.Dialog({
        title: __("PAYE Tax Deduction Summary"),
        size: "large",
        fields: [
            {
                fieldtype: "HTML",
                options: summary_html
            }
        ],
        primary_action_label: __("Download PDF"),
        primary_action: function() {
            frappe.call({
                method: "general.general_biz_apps.report.paye_deduction_report.paye_deduction_report.generate_summary_pdf",
                args: {
                    filters: filters,
                    summary: {
                        total_employees: total_employees,
                        total_gross: total_gross,
                        total_tax: total_tax,
                        employees_with_errors: employees_with_errors
                    }
                },
                freeze: true,
                freeze_message: __("Generating PDF..."),
                callback: function(r) {
                    if (r.message) {
                        window.open(r.message.file_url);
                        frappe.show_alert({
                            message: __("PDF generated successfully"),
                            indicator: "green"
                        }, 5);
                        d.hide();
                    }
                },
                error: function(r) {
                    frappe.msgprint({
                        title: __("PDF Generation Failed"),
                        message: __("Failed to generate PDF summary. Please try again."),
                        indicator: "red"
                    });
                }
            });
        },
        secondary_action_label: __("Close"),
        secondary_action: function() {
            d.hide();
        }
    });

    d.show();
}