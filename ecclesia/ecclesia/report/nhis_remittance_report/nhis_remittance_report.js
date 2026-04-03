// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt
/* eslint-disable */




frappe.query_reports["NHIS Remittance Report"] = {
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
            fieldname: "hmo",
            label: __("Health Maintenance Organization (HMO)"),
            fieldtype: "Link",
            options: "HMO Manager",
            description: __("Filter by Employee HMO")
        },
        {
            fieldname: "show_errors_only",
            label: __("Show Validation Errors Only"),
            fieldtype: "Check",
            default: 0
        },
        {
            fieldname: "group_by_hmo",
            label: __("Group by HMO"),
            fieldtype: "Check",
            default: 1
        }
    ],

    onload: function(report) {
        // Add custom buttons
        report.page.add_inner_button(__("Export NHIS Template"), function() {
            export_nhis_template(report);
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
        if (data && column.fieldname !== "total_nhis") {
            if (!data.nhis_number || !data.hmo) {
                if (column.fieldname === "nhis_number" && !data.nhis_number) {
                    value = `<span class="text-danger" title="Missing NHIS Number">
                        <i class="fa fa-exclamation-triangle"></i> ${value || "Not Set"}
                    </span>`;
                }
                if (column.fieldname === "hmo" && !data.hmo) {
                    value = `<span class="text-danger" title="Missing HMO">
                        <i class="fa fa-exclamation-triangle"></i> ${value || "Not Set"}
                    </span>`;
                }
            }
        }

        // Color code NHIS amounts
        if (column.fieldname === "employer_nhis" && data && data.employer_nhis) {
            value = `<span class="text-success font-weight-bold">${value}</span>`;
        }
        if (column.fieldname === "employee_nhis" && data && data.employee_nhis) {
            value = `<span class="text-info font-weight-bold">${value}</span>`;
        }
        if (column.fieldname === "total_nhis" && data && data.total_nhis) {
            value = `<span class="text-danger font-weight-bold">${value}</span>`;
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

function export_nhis_template(report) {
    const filters = report.get_values();

    if (!report.data || report.data.length === 0) {
        frappe.msgprint(__("No data to export"));
        return;
    }

    frappe.call({
        method: "general.general_biz_apps.report.nhis_remittance_report.nhis_remittance_report.export_nhis_format",
        args: {
            filters: filters
        },
        freeze: true,
        freeze_message: __("Generating NHIS Template..."),
        callback: function(r) {
            if (r.message) {
                // Download the file
                window.open(r.message.file_url);
                frappe.show_alert({
                    message: __("NHIS template exported successfully"),
                    indicator: "green"
                }, 5);
            }
        },
        error: function(r) {
            frappe.msgprint({
                title: __("Export Failed"),
                message: __("Failed to generate NHIS template. Please try again."),
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
        method: "general.general_biz_apps.report.nhis_remittance_report.nhis_remittance_report.export_detailed_excel",
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
    let total_nhis = 0;
    let employees_with_errors = 0;

    data.forEach(row => {
        if (row.employee) {
            total_employees++;
            total_employer += row.employer_nhis || 0;
            total_employee += row.employee_nhis || 0;
            total_nhis += row.total_nhis || 0;
            
            if (!row.nhis_number || !row.hmo) {
                employees_with_errors++;
            }
        }
    });

    const summary_html = `
        <div class="nhis-summary" style="padding: 20px;">
            <h4 style="color: #dc3545; margin-bottom: 20px; border-bottom: 2px solid #dc3545; padding-bottom: 10px;">
                NHIS Remittance Summary
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
                    <th style="background-color: #f8f9fa;">Total Employer Contribution (ER)</th>
                    <td class="text-success"><strong>${format_currency(total_employer)}</strong></td>
                </tr>
                <tr>
                    <th style="background-color: #f8f9fa;">Total Employee Contribution (EE)</th>
                    <td class="text-info"><strong>${format_currency(total_employee)}</strong></td>
                </tr>
                <tr style="background-color: #f0f0f0;">
                    <th style="background-color: #e7e6e6; font-size: 1.1em;">Total NHIS Remittance</th>
                    <td class="text-danger" style="font-size: 1.1em;"><strong>${format_currency(total_nhis)}</strong></td>
                </tr>
            </table>
            ${employees_with_errors > 0 ? `
                <div class="alert alert-warning" style="margin-top: 20px;">
                    <i class="fa fa-exclamation-triangle"></i>
                    <strong>Warning:</strong> ${employees_with_errors} employee(s) have missing NHIS information.
                    Please ensure all employees have NHIS Number and HMO assigned.
                </div>
            ` : ''}
        </div>
    `;

    const d = new frappe.ui.Dialog({
        title: __("NHIS Remittance Summary"),
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
                method: "general.general_biz_apps.report.nhis_remittance_report.nhis_remittance_report.generate_summary_pdf",
                args: {
                    filters: filters,
                    summary: {
                        total_employees: total_employees,
                        total_employer: total_employer,
                        total_employee: total_employee,
                        total_nhis: total_nhis,
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