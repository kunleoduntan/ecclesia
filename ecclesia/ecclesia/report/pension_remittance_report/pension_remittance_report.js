// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt
/* eslint-disable */


frappe.query_reports["Pension Remittance Report"] = {
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
            fieldname: "pfa",
            label: __("Pension Fund Administrator"),
            fieldtype: "Link",
            options: "Pension Manager",
            description: __("Filter by Employee Pension Fund Administrator")
        },
        {
            fieldname: "show_errors_only",
            label: __("Show Validation Errors Only"),
            fieldtype: "Check",
            default: 0
        },
        {
            fieldname: "group_by_pfa",
            label: __("Group by PFA"),
            fieldtype: "Check",
            default: 1
        }
    ],

    onload: function(report) {
        // Add custom buttons
        report.page.add_inner_button(__("Export PENCOM Template"), function() {
            export_pencom_template(report);
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
        if (data && column.fieldname !== "total_pension") {
            if (!data.pension_pin || !data.rsa_id || !data.pfa) {
                if (column.fieldname === "pension_pin" && !data.pension_pin) {
                    value = `<span class="text-danger" title="Missing Pension PIN">
                        <i class="fa fa-exclamation-triangle"></i> ${value || "Not Set"}
                    </span>`;
                }
                if (column.fieldname === "rsa_id" && !data.rsa_id) {
                    value = `<span class="text-danger" title="Missing RSA ID">
                        <i class="fa fa-exclamation-triangle"></i> ${value || "Not Set"}
                    </span>`;
                }
                if (column.fieldname === "pfa" && !data.pfa) {
                    value = `<span class="text-danger" title="Missing PFA">
                        <i class="fa fa-exclamation-triangle"></i> ${value || "Not Set"}
                    </span>`;
                }
            }
        }

        // Color code pension amounts
        if (column.fieldname === "employer_pension" && data && data.employer_pension) {
            value = `<span class="text-success font-weight-bold">${value}</span>`;
        }
        if (column.fieldname === "employee_pension" && data && data.employee_pension) {
            value = `<span class="text-info font-weight-bold">${value}</span>`;
        }
        if (column.fieldname === "total_pension" && data && data.total_pension) {
            value = `<span class="text-primary font-weight-bold">${value}</span>`;
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

function export_pencom_template(report) {
    const filters = report.get_values();

    if (!report.data || report.data.length === 0) {
        frappe.msgprint(__("No data to export"));
        return;
    }

    frappe.call({
        method: "ecclesia.ecclesia.report.pension_remittance_report.pension_remittance_report.export_pencom_format",
        args: {
            filters: filters
        },
        freeze: true,
        freeze_message: __("Generating PENCOM Template..."),
        callback: function(r) {
            if (r.message) {
                // Download the file
                window.open(r.message.file_url);
                frappe.show_alert({
                    message: __("PENCOM template exported successfully"),
                    indicator: "green"
                }, 5);
            }
        },
        error: function(r) {
            frappe.msgprint({
                title: __("Export Failed"),
                message: __("Failed to generate PENCOM template. Please try again."),
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
        method: "ecclesia.ecclesia.report.pension_remittance_report.pension_remittance_report.export_detailed_excel",
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
    let total_employer = 0;
    let total_employee = 0;
    let total_pension = 0;
    let employees_with_errors = 0;

    data.forEach(row => {
        if (row.employee) {
            total_employees++;
            total_employer += row.employer_pension || 0;
            total_employee += row.employee_pension || 0;
            total_pension += row.total_pension || 0;
            
            if (!row.pension_pin || !row.rsa_id || !row.pfa) {
                employees_with_errors++;
            }
        }
    });

    const summary_html = `
        <div class="pension-summary" style="padding: 20px;">
            <h4 style="color: #4472C4; margin-bottom: 20px; border-bottom: 2px solid #4472C4; padding-bottom: 10px;">
                Pension Remittance Summary
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
                    <th style="background-color: #f8f9fa;">Total Employer Contribution (10%)</th>
                    <td class="text-success"><strong>${format_currency(total_employer)}</strong></td>
                </tr>
                <tr>
                    <th style="background-color: #f8f9fa;">Total Employee Contribution (8%)</th>
                    <td class="text-info"><strong>${format_currency(total_employee)}</strong></td>
                </tr>
                <tr style="background-color: #f0f0f0;">
                    <th style="background-color: #e7e6e6; font-size: 1.1em;">Total Pension Remittance</th>
                    <td class="text-primary" style="font-size: 1.1em;"><strong>${format_currency(total_pension)}</strong></td>
                </tr>
            </table>
        </div>
    `;

    const d = new frappe.ui.Dialog({
        title: __("Pension Remittance Summary"),
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
                method: "ecclesia.ecclesia.report.pension_remittance_report.pension_remittance_report.generate_summary_pdf",
                args: {
                    filters: filters,
                    summary: {
                        total_employees: total_employees,
                        total_employer: total_employer,
                        total_employee: total_employee,
                        total_pension: total_pension,
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