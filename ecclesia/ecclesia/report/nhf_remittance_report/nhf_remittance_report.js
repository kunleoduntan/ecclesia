// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt
/* eslint-disable */



frappe.query_reports["NHF Remittance Report"] = {
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
            fieldname: "show_errors_only",
            label: __("Show Validation Errors Only"),
            fieldtype: "Check",
            default: 0
        }
    ],

    onload: function(report) {
        // Add custom buttons
        report.page.add_inner_button(__("Export NHF Template"), function() {
            export_nhf_template(report);
        }, __("Export"));

        report.page.add_inner_button(__("Export Detailed Excel"), function() {
            export_detailed_excel(report);
        }, __("Export"));

        report.page.add_inner_button(__("Download Summary"), function() {
            download_summary(report);
        }, __("Export"));
    },

    formatter: function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        // Highlight rows with missing information
        if (data && column.fieldname !== "nhf_contribution") {
            if (!data.nhf_number) {
                if (column.fieldname === "nhf_number" && !data.nhf_number) {
                    value = `<span class="text-danger" title="Missing NHF Number">
                        <i class="fa fa-exclamation-triangle"></i> ${value || "Not Set"}
                    </span>`;
                }
            }
        }

        // Color code NHF amounts
        if (column.fieldname === "basic_salary" && data && data.basic_salary) {
            value = `<span class="text-info font-weight-bold">${value}</span>`;
        }
        if (column.fieldname === "nhf_contribution" && data && data.nhf_contribution) {
            value = `<span class="text-success font-weight-bold">${value}</span>`;
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

function export_nhf_template(report) {
    const filters = report.get_values();

    if (!report.data || report.data.length === 0) {
        frappe.msgprint(__("No data to export"));
        return;
    }

    frappe.call({
        method: "ecclesia.ecclesia.report.nhf_remittance_report.nhf_remittance_report.export_nhf_format",
        args: {
            filters: filters
        },
        freeze: true,
        freeze_message: __("Generating NHF Template..."),
        callback: function(r) {
            if (r.message) {
                // Download the file
                window.open(r.message.file_url);
                frappe.show_alert({
                    message: __("NHF template exported successfully"),
                    indicator: "green"
                }, 5);
            }
        },
        error: function(r) {
            frappe.msgprint({
                title: __("Export Failed"),
                message: __("Failed to generate NHF template. Please try again."),
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
        method: "ecclesia.ecclesia.report.nhf_remittance_report.nhf_remittance_report.export_detailed_excel",
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

function download_summary(report) {
    const data = report.data;
    const filters = report.get_values();

    if (!data || data.length === 0) {
        frappe.msgprint(__("No data to export"));
        return;
    }

    // Calculate summary statistics
    let total_employees = 0;
    let total_basic = 0;
    let total_nhf = 0;
    let employees_with_errors = 0;

    data.forEach(row => {
        if (row.employee) {
            total_employees++;
            total_basic += row.basic_salary || 0;
            total_nhf += row.nhf_contribution || 0;
            
            if (!row.nhf_number) {
                employees_with_errors++;
            }
        }
    });

    const summary_html = `
        <div class="nhf-summary" style="padding: 20px;">
            <h4 style="color: #28a745; margin-bottom: 20px; border-bottom: 2px solid #28a745; padding-bottom: 10px;">
                NHF Remittance Summary
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
                    <th style="background-color: #f8f9fa;">Total Basic Salary</th>
                    <td class="text-info"><strong>${format_currency(total_basic)}</strong></td>
                </tr>
                <tr style="background-color: #f0f0f0;">
                    <th style="background-color: #e7e6e6; font-size: 1.1em;">Total NHF Contribution (2.5%)</th>
                    <td class="text-success" style="font-size: 1.1em;"><strong>${format_currency(total_nhf)}</strong></td>
                </tr>
            </table>
            ${employees_with_errors > 0 ? `
                <div class="alert alert-warning" style="margin-top: 20px;">
                    <i class="fa fa-exclamation-triangle"></i>
                    <strong>Warning:</strong> ${employees_with_errors} employee(s) have missing NHF Number.
                    Please ensure all employees have NHF Number assigned.
                </div>
            ` : ''}
            <div class="alert alert-info" style="margin-top: 20px;">
                <i class="fa fa-info-circle"></i>
                <strong>Note:</strong> NHF (National Housing Fund) contribution is 2.5% of basic salary,
                deducted from employee's monthly salary and remitted to the Federal Mortgage Bank of Nigeria (FMBN).
            </div>
        </div>
    `;

    const d = new frappe.ui.Dialog({
        title: __("NHF Remittance Summary"),
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
                method: "ecclesia.ecclesia.report.nhf_remittance_report.nhf_remittance_report.generate_summary_pdf",
                args: {
                    filters: filters,
                    summary: {
                        total_employees: total_employees,
                        total_basic: total_basic,
                        total_nhf: total_nhf,
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