// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt
/* eslint-disable */



frappe.query_reports["Employee Pension Statement"] = {
    "filters": [
        {
            "fieldname": "employee",
            "label": __("Employee"),
            "fieldtype": "Link",
            "options": "Employee",
            "reqd": 1,
            "get_query": function() {
                return {
                    "filters": {
                        "custom_pension_applicable": 1,
                        "status": "Active"
                    }
                };
            }
        },
        {
            "fieldname": "from_year",
            "label": __("From Year"),
            "fieldtype": "Int",
            "default": new Date().getFullYear() - 1
        },
        {
            "fieldname": "to_year",
            "label": __("To Year"),
            "fieldtype": "Int",
            "default": new Date().getFullYear()
        }
    ],
    
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        // Format total row
        if (data && data.period && data.period.includes("<b>TOTAL</b>")) {
            value = `<div style="font-weight: bold; background-color: #f0f0f0; padding: 5px;">${value}</div>`;
        }
        
        // Highlight cumulative column with green color
        if (column.fieldname === "cumulative" && data && data.cumulative) {
            value = `<div style="color: #2ecc71; font-weight: bold;">${value}</div>`;
        }
        
        // Color code contribution amounts
        if (column.fieldname === "employee_contribution" && data && data.employee_contribution) {
            value = `<span style="color: #667eea; font-weight: bold;">${value}</span>`;
        }
        
        if (column.fieldname === "employer_contribution" && data && data.employer_contribution) {
            value = `<span style="color: #f093fb; font-weight: bold;">${value}</span>`;
        }
        
        if (column.fieldname === "total" && data && data.total) {
            value = `<span style="color: #4facfe; font-weight: bold;">${value}</span>`;
        }
        
        if (column.fieldname === "voluntary" && data && data.voluntary && data.voluntary > 0) {
            value = `<span style="color: #ffa502; font-weight: bold;">${value}</span>`;
        }
        
        return value;
    },
    
    "onload": function(report) {
        // Add export button
        report.page.add_inner_button(__("Export to Excel"), function() {
            export_to_excel(report);
        }, __("Export"));
        
        // Add action buttons
        report.page.add_inner_button(__("View Summary"), function() {
            show_summary(report);
        }, __("Actions"));
        
        report.page.add_inner_button(__("Email to Employee"), function() {
            email_statement(report);
        }, __("Actions"));
        
        // Add debug button (for troubleshooting)
        report.page.add_inner_button(__("Debug Components"), function() {
            debug_components(report);
        }, __("Developer"));
        
        // Add print buttons
        report.page.add_inner_button(__("Preview Print"), function() {
            preview_print_format(report);
        }, __("Print"));
        
        report.page.add_inner_button(__("Download PDF"), function() {
            download_pdf_format(report);
        }, __("Print"));
    }
};

function preview_print_format(report) {
    let filters = report.get_filter_values();
    
    if (!filters.employee) {
        frappe.msgprint(__("Please select an employee"));
        return;
    }
    
    frappe.show_alert({
        message: __("Generating print preview..."),
        indicator: "blue"
    }, 3);
    
    frappe.call({
        method: "ecclesia.ecclesia.report.employee_pension_statement.employee_pension_statement.preview_pension_print",
        args: {
            filters: filters
        },
        callback: function(r) {
            if (r.message) {
                // Open in new window
                let print_window = window.open("", "_blank");
                print_window.document.write(r.message);
                print_window.document.close();
            }
        }
    });
}

function download_pdf_format(report) {
    let filters = report.get_filter_values();
    
    if (!filters.employee) {
        frappe.msgprint(__("Please select an employee"));
        return;
    }
    
    frappe.show_alert({
        message: __("Generating PDF..."),
        indicator: "blue"
    }, 3);
    
    frappe.call({
        method: "ecclesia.ecclesia.report.employee_pension_statement.employee_pension_statement.download_pension_pdf",
        args: {
            filters: filters
        },
        callback: function(r) {
            if (r.message) {
                frappe.show_alert({
                    message: __("PDF generated successfully!"),
                    indicator: "green"
                }, 3);
                
                // Open file
                window.open(r.message.file_url);
            }
        }
    });
}

function export_to_excel(report) {
    let filters = report.get_filter_values();
    
    if (!filters.employee) {
        frappe.msgprint(__("Please select an employee"));
        return;
    }
    
    frappe.show_alert({
        message: __("Generating Excel file..."),
        indicator: "blue"
    }, 3);
    
    frappe.call({
        method: "ecclesia.ecclesia.report.employee_pension_statement.employee_pension_statement.export_employee_statement_excel",
        args: {
            filters: filters
        },
        callback: function(r) {
            if (r.message) {
                frappe.show_alert({
                    message: __("Excel file generated successfully!"),
                    indicator: "green"
                }, 3);
                
                // Open file
                window.open(r.message.file_url);
            }
        },
        error: function(r) {
            frappe.msgprint({
                title: __("Export Failed"),
                message: __("There was an error generating the Excel file. Please try again."),
                indicator: "red"
            });
        }
    });
}

function email_statement(report) {
    let filters = report.get_filter_values();
    
    if (!filters.employee) {
        frappe.msgprint(__("Please select an employee"));
        return;
    }
    
    // Get employee email
    frappe.call({
        method: "frappe.client.get",
        args: {
            doctype: "Employee",
            name: filters.employee
        },
        callback: function(r) {
            if (r.message) {
                let employee = r.message;
                let email = employee.personal_email || employee.company_email || employee.prefered_email;
                
                if (email) {
                    // Confirm before sending
                    frappe.confirm(
                        __("Send pension statement to {0} ({1})?", [employee.employee_name, email]),
                        function() {
                            frappe.msgprint({
                                title: __("Email Feature"),
                                message: __("Email functionality is being configured. For now, you can export to Excel and send manually."),
                                indicator: "blue"
                            });
                            
                            // TODO: Implement email with PDF attachment
                            /*
                            frappe.call({
                                method: "general.general_biz_apps.report.employee_pension_statement.employee_pension_statement.email_pension_statement",
                                args: {
                                    filters: filters,
                                    recipient: email
                                },
                                callback: function() {
                                    frappe.show_alert({
                                        message: __("Statement sent to {0}", [email]),
                                        indicator: "green"
                                    }, 5);
                                }
                            });
                            */
                        }
                    );
                } else {
                    frappe.msgprint({
                        title: __("No Email Found"),
                        message: __("No email address found for this employee. Please update the employee record with an email address."),
                        indicator: "orange"
                    });
                }
            }
        }
    });
}

function show_summary(report) {
    let filters = report.get_filter_values();
    
    if (!filters.employee) {
        frappe.msgprint(__("Please select an employee"));
        return;
    }
    
    // Show loading
    frappe.show_alert({
        message: __("Loading summary..."),
        indicator: "blue"
    }, 2);
    
    // Get pension summary
    frappe.call({
        method: "ecclesia.ecclesia.report.employee_pension_statement.employee_pension_statement.get_employee_pension_summary",
        args: {
            employee: filters.employee
        },
        callback: function(r) {
            if (r.message) {
                let summary = r.message;
                
                let html = `
                    <div style="padding: 20px;">
                        <h4 style="color: #667eea; margin-bottom: 20px; border-bottom: 2px solid #667eea; padding-bottom: 10px;">
                            <i class="fa fa-chart-line"></i> Pension Contribution Summary
                        </h4>
                        
                        <table class="table table-bordered" style="margin-top: 15px;">
                            <tr>
                                <th style="background-color: #f8f9fa; width: 50%;">Total Months Contributed</th>
                                <td><strong>${summary.total_months || 0}</strong> months</td>
                            </tr>
                            <tr>
                                <th style="background-color: #f8f9fa;">First Contribution</th>
                                <td>${summary.first_contribution ? frappe.datetime.str_to_user(summary.first_contribution) : "N/A"}</td>
                            </tr>
                            <tr>
                                <th style="background-color: #f8f9fa;">Last Contribution</th>
                                <td>${summary.last_contribution ? frappe.datetime.str_to_user(summary.last_contribution) : "N/A"}</td>
                            </tr>
                            <tr>
                                <th style="background-color: #f8f9fa;">Total Employee Contribution (8%)</th>
                                <td><strong style="color: #667eea;">${format_currency(summary.total_employee || 0)}</strong></td>
                            </tr>
                            <tr>
                                <th style="background-color: #f8f9fa;">Total Employer Contribution (10%)</th>
                                <td><strong style="color: #f093fb;">${format_currency(summary.total_employer || 0)}</strong></td>
                            </tr>
                            <tr>
                                <th style="background-color: #f8f9fa;">Total Voluntary Contribution</th>
                                <td><strong style="color: #ffa502;">${format_currency(summary.total_voluntary || 0)}</strong></td>
                            </tr>
                            <tr style="background-color: #f0f0f0;">
                                <th style="font-size: 1.1em;">Total Pension Accumulated</th>
                                <td style="font-size: 1.1em;"><strong style="color: #2ecc71;">${format_currency(summary.total_all || 0)}</strong></td>
                            </tr>
                        </table>
                        
                        <div class="alert alert-info" style="margin-top: 20px;">
                            <i class="fa fa-info-circle"></i>
                            <strong>Note:</strong> This summary includes all submitted pension contributions from salary slips.
                            The total accumulated amount represents the sum of employee (8%), employer (10%), and voluntary contributions.
                        </div>
                    </div>
                `;
                
                frappe.msgprint({
                    title: __("Pension Summary"),
                    message: html,
                    wide: true
                });
            }
        },
        error: function(r) {
            frappe.msgprint({
                title: __("Error"),
                message: __("Could not load pension summary. Please try again."),
                indicator: "red"
            });
        }
    });
}

function debug_components(report) {
    let filters = report.get_filter_values();
    
    if (!filters.employee) {
        frappe.msgprint(__("Please select an employee"));
        return;
    }
    
    frappe.show_alert({
        message: __("Analyzing salary components..."),
        indicator: "blue"
    }, 3);
    
    frappe.call({
        method: "ecclesia.ecclesia.report.employee_pension_statement.employee_pension_statement.debug_salary_components",
        args: {
            employee: filters.employee,
            from_year: filters.from_year,
            to_year: filters.to_year
        },
        callback: function(r) {
            if (r.message) {
                if (r.message.error) {
                    frappe.msgprint({
                        title: __("Debug Results"),
                        message: `<div class="alert alert-warning">
                            <strong>Error:</strong> ${r.message.error}<br>
                            <strong>Employee:</strong> ${r.message.employee}<br>
                            <strong>Date Range:</strong> ${r.message.date_range}
                        </div>`,
                        indicator: "orange"
                    });
                    return;
                }
                
                let html = '<div style="padding: 15px;">';
                html += '<h4 style="color: #667eea; margin-bottom: 15px;"><i class="fa fa-bug"></i> Salary Components Debug Report</h4>';
                
                r.message.forEach(function(slip, index) {
                    html += `
                        <div style="margin-bottom: 25px; border: 1px solid #ddd; padding: 15px; border-radius: 5px;">
                            <h5 style="color: #333; margin-bottom: 10px;">
                                <strong>Salary Slip ${index + 1}:</strong> ${slip.salary_slip}
                            </h5>
                            <p style="margin: 5px 0;"><strong>Date:</strong> ${slip.date}</p>
                            <p style="margin: 5px 0;"><strong>Gross Pay:</strong> ${format_currency(slip.gross_pay)}</p>
                            <p style="margin: 5px 0;"><strong>Total Components:</strong> ${slip.all_components_count}</p>
                            
                            ${slip.pension_components.length > 0 ? `
                                <div style="margin-top: 15px;">
                                    <strong style="color: #2ecc71;">Pension Components Found:</strong>
                                    <table class="table table-bordered" style="margin-top: 10px; font-size: 12px;">
                                        <thead>
                                            <tr style="background-color: #f8f9fa;">
                                                <th>Component Name</th>
                                                <th>Amount</th>
                                                <th>Type</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${slip.pension_components.map(c => `
                                                <tr>
                                                    <td>${c.salary_component}</td>
                                                    <td>${format_currency(c.amount)}</td>
                                                    <td><span class="badge badge-${c.parentfield === 'earnings' ? 'success' : 'warning'}">${c.parentfield}</span></td>
                                                </tr>
                                            `).join('')}
                                        </tbody>
                                    </table>
                                </div>
                            ` : `
                                <div class="alert alert-warning" style="margin-top: 15px;">
                                    <i class="fa fa-exclamation-triangle"></i> No pension components found in this salary slip
                                </div>
                            `}
                            
                            <details style="margin-top: 10px;">
                                <summary style="cursor: pointer; color: #667eea;"><strong>View All Components (${slip.all_components_count})</strong></summary>
                                <table class="table table-bordered" style="margin-top: 10px; font-size: 11px;">
                                    <thead>
                                        <tr style="background-color: #f8f9fa;">
                                            <th>Component Name</th>
                                            <th>Amount</th>
                                            <th>Type</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${slip.all_components.map(c => `
                                            <tr>
                                                <td>${c.salary_component}</td>
                                                <td>${format_currency(c.amount)}</td>
                                                <td><span class="badge badge-${c.parentfield === 'earnings' ? 'success' : 'warning'}">${c.parentfield}</span></td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </details>
                        </div>
                    `;
                });
                
                html += `
                    <div class="alert alert-info">
                        <i class="fa fa-lightbulb"></i>
                        <strong>Troubleshooting Tips:</strong>
                        <ul style="margin-top: 10px; margin-bottom: 0;">
                            <li>Look for pension components in the tables above</li>
                            <li>Check if component names match: "Pension (EE)", "Pension (ER)", or similar</li>
                            <li>Verify that pension components exist in both earnings and deductions</li>
                            <li>If no pension components are found, check your Salary Structure setup</li>
                        </ul>
                    </div>
                `;
                
                html += '</div>';
                
                let dialog = new frappe.ui.Dialog({
                    title: __("Debug Report - Salary Components"),
                    fields: [
                        {
                            fieldtype: 'HTML',
                            fieldname: 'debug_html',
                            options: html
                        }
                    ],
                    size: 'extra-large',
                    primary_action_label: __('Close'),
                    primary_action: function() {
                        dialog.hide();
                    }
                });
                
                dialog.show();
            }
        },
        error: function(r) {
            frappe.msgprint({
                title: __("Debug Error"),
                message: __("Could not retrieve debug information. Please check the console for errors."),
                indicator: "red"
            });
            console.error("Debug error:", r);
        }
    });
}


// Add these functions to your existing pension_remittance_report.js file
// Add the buttons in the onload function

// In onload function, add these buttons:
report.page.add_inner_button(__("Preview Print"), function() {
    preview_remittance_print(report);
}, __("Print"));

report.page.add_inner_button(__("Download PDF"), function() {
    download_remittance_pdf(report);
}, __("Print"));

// Then add these functions at the end of the file:

function preview_remittance_print(report) {
    let filters = report.get_filter_values();
    let data = report.data;
    
    if (!filters.company) {
        frappe.msgprint(__("Please select a company"));
        return;
    }
    
    if (!filters.from_date || !filters.to_date) {
        frappe.msgprint(__("Please select date range"));
        return;
    }
    
    frappe.show_alert({
        message: __("Generating print preview..."),
        indicator: "blue"
    }, 3);
    
    frappe.call({
        method: "ecclesia.ecclesia.report.pension_remittance_report.pension_remittance_report.preview_remittance_print",
        args: {
            filters: filters,
            data: data
        },
        callback: function(r) {
            if (r.message) {
                // Open in new window
                let print_window = window.open("", "_blank");
                print_window.document.write(r.message);
                print_window.document.close();
            }
        },
        error: function(r) {
            frappe.msgprint({
                title: __("Preview Failed"),
                message: __("There was an error generating the print preview. Please try again."),
                indicator: "red"
            });
        }
    });
}

function download_remittance_pdf(report) {
    let filters = report.get_filter_values();
    let data = report.data;
    
    if (!filters.company) {
        frappe.msgprint(__("Please select a company"));
        return;
    }
    
    if (!filters.from_date || !filters.to_date) {
        frappe.msgprint(__("Please select date range"));
        return;
    }
    
    frappe.show_alert({
        message: __("Generating PDF... This may take a moment."),
        indicator: "blue"
    }, 5);
    
    frappe.call({
        method: "ecclesia.ecclesia.report.pension_remittance_report.pension_remittance_report.download_remittance_pdf",
        args: {
            filters: filters,
            data: data
        },
        callback: function(r) {
            if (r.message) {
                frappe.show_alert({
                    message: __("PDF generated successfully!"),
                    indicator: "green"
                }, 3);
                
                // Open file
                window.open(r.message.file_url);
            }
        },
        error: function(r) {
            frappe.msgprint({
                title: __("PDF Generation Failed"),
                message: __("There was an error generating the PDF. Please try again."),
                indicator: "red"
            });
        }
    });
}
