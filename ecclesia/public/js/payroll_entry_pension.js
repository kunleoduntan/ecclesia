// File: general_biz_apps/public/js/payroll_entry_pension.js
// Extension for Payroll Entry to add pension management features

frappe.ui.form.on('Payroll Entry', {
    refresh: function(frm) {
        if (frm.doc.docstatus === 1) {
            add_pension_management_buttons(frm);
            show_pension_status_indicator(frm);
        }
    },
    
    onload: function(frm) {
        if (frm.doc.docstatus === 1) {
            check_pension_contribution_status(frm);
        }
    }
});

function add_pension_management_buttons(frm) {
    // Main button - Create Pension Contributions
    frm.add_custom_button(__('Create Pension Contributions'), function() {
        create_pension_contributions_bulk(frm);
    }, __('Pension Management')).addClass('btn-warning');
    
    // View existing contributions
    frm.add_custom_button(__('View Pension Contributions'), function() {
        view_pension_contributions(frm);
    }, __('Pension Management'));
    
    // Create remittance schedule
    frm.add_custom_button(__('Create Remittance Schedule'), function() {
        create_remittance_schedule_dialog(frm);
    }, __('Pension Management'));
    
    // Pension summary report
    frm.add_custom_button(__('Pension Summary'), function() {
        show_pension_summary(frm);
    }, __('Pension Management'));
}

function show_pension_status_indicator(frm) {
    // This runs async to show status
    check_pension_contribution_status(frm);
}

function check_pension_contribution_status(frm) {
    frappe.call({
        method: 'general.general_biz_apps.doctype.pension_contribution.pension_contribution.get_pending_salary_slips_for_pension',
        args: {
            payroll_entry: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                let pending_count = r.message.length;
                
                // Get total pension-applicable employees
                frappe.db.count('Salary Slip', {
                    filters: {
                        'payroll_entry': frm.doc.name,
                        'docstatus': 1
                    }
                }).then(total => {
                    let created = total - pending_count;
                    
                    if (created > 0 && pending_count === 0) {
                        // All created
                        frm.dashboard.add_indicator(
                            __('Pension: All {0} contributions created', [created]),
                            'green'
                        );
                    } else if (created > 0 && pending_count > 0) {
                        // Partially created
                        frm.dashboard.add_indicator(
                            __('Pension: {0} of {1} created', [created, total]),
                            'orange'
                        );
                        
                        frm.dashboard.set_headline_alert(
                            `<i class="fa fa-info-circle"></i> ${pending_count} salary slip(s) need pension contribution creation`,
                            'blue'
                        );
                    } else if (total > 0) {
                        // None created
                        frm.dashboard.add_indicator(
                            __('Pension contributions not created'),
                            'red'
                        );
                        
                        frm.dashboard.set_headline_alert(
                            '<i class="fa fa-exclamation-triangle"></i> Click "Create Pension Contributions" to process pension',
                            'orange'
                        );
                    }
                });
            }
        }
    });
}

function create_pension_contributions_bulk(frm) {
    // Show confirmation dialog with preview
    frappe.call({
        method: 'general.general_biz_apps.doctype.pension_contribution.pension_contribution.get_pending_salary_slips_for_pension',
        args: {
            payroll_entry: frm.doc.name
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                show_bulk_creation_dialog(frm, r.message);
            } else {
                frappe.msgprint({
                    title: __('No Pending Contributions'),
                    message: __('All pension contributions have already been created for this payroll.'),
                    indicator: 'blue'
                });
            }
        }
    });
}

function show_bulk_creation_dialog(frm, pending_slips) {
    let total_base = pending_slips.reduce((sum, slip) => sum + (slip.base || 0), 0);
    
    let html = `
        <div style="padding: 15px;">
            <h5>Pension Contributions to Create</h5>
            <table class="table table-bordered">
                <tr>
                    <td><strong>Employees:</strong></td>
                    <td class="text-right">${pending_slips.length}</td>
                </tr>
                <tr>
                    <td><strong>Total Base Salary:</strong></td>
                    <td class="text-right">${format_currency(total_base)}</td>
                </tr>
                <tr>
                    <td><strong>Est. Employee Contrib (8%):</strong></td>
                    <td class="text-right">${format_currency(total_base * 0.08)}</td>
                </tr>
                <tr>
                    <td><strong>Est. Employer Contrib (10%):</strong></td>
                    <td class="text-right">${format_currency(total_base * 0.10)}</td>
                </tr>
                <tr style="background-color: #f8f9fa; font-weight: bold;">
                    <td><strong>Est. Total Contribution:</strong></td>
                    <td class="text-right text-primary">${format_currency(total_base * 0.18)}</td>
                </tr>
            </table>
            
            <div class="alert alert-info" style="margin-top: 15px;">
                <i class="fa fa-info-circle"></i> 
                <strong>What will happen:</strong>
                <ul style="margin: 10px 0 0 20px;">
                    <li>System will create ${pending_slips.length} Pension Contribution records</li>
                    <li>Pension amounts will be auto-extracted from salary slips</li>
                    <li>All records will be auto-submitted</li>
                    <li>Ready for remittance scheduling</li>
                </ul>
            </div>
        </div>
    `;
    
    let d = new frappe.ui.Dialog({
        title: __('Create Pension Contributions'),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'preview_html',
                options: html
            }
        ],
        size: 'large',
        primary_action_label: __('Create {0} Contributions', [pending_slips.length]),
        primary_action: function() {
            d.hide();
            execute_bulk_creation(frm);
        }
    });
    
    d.show();
}

function execute_bulk_creation(frm) {
    frappe.show_alert({
        message: __('Creating pension contributions...'),
        indicator: 'blue'
    });
    
    frappe.call({
        method: 'general.general_biz_apps.doctype.pension_contribution.pension_contribution.bulk_create_from_payroll',
        args: {
            payroll_entry_name: frm.doc.name
        },
        freeze: true,
        freeze_message: __('Creating Pension Contributions...<br>Please wait...'),
        callback: function(r) {
            if (r.message) {
                show_bulk_creation_result(frm, r.message);
            }
        },
        error: function(err) {
            frappe.msgprint({
                title: __('Creation Failed'),
                message: __('Failed to create pension contributions. Check error log.'),
                indicator: 'red'
            });
        }
    });
}

function show_bulk_creation_result(frm, result) {
    let html = `
        <div style="padding: 20px;">
            <h4><i class="fa fa-check-circle text-success"></i> Pension Contributions Created</h4>
            <hr>
            
            <div class="row" style="margin-bottom: 20px;">
                <div class="col-md-4">
                    <div class="card text-center" style="border-left: 4px solid #28a745; padding: 15px;">
                        <h2 class="text-success" style="margin: 0;">${result.created}</h2>
                        <p style="margin: 5px 0 0 0; color: #666;">Created</p>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card text-center" style="border-left: 4px solid #ffc107; padding: 15px;">
                        <h2 class="text-warning" style="margin: 0;">${result.skipped || 0}</h2>
                        <p style="margin: 5px 0 0 0; color: #666;">Skipped</p>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card text-center" style="border-left: 4px solid #dc3545; padding: 15px;">
                        <h2 class="text-danger" style="margin: 0;">${result.errors ? result.errors.length : 0}</h2>
                        <p style="margin: 5px 0 0 0; color: #666;">Errors</p>
                    </div>
                </div>
            </div>
    `;
    
    // Show created list
    if (result.created_list && result.created_list.length > 0) {
        html += `
            <div style="margin-top: 20px;">
                <h5>✓ Successfully Created</h5>
                <div style="max-height: 200px; overflow-y: auto; border: 1px solid #ddd; padding: 10px;">
                    <table class="table table-sm table-bordered">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Employee</th>
                                <th>Document</th>
                            </tr>
                        </thead>
                        <tbody>
        `;
        
        result.created_list.slice(0, 20).forEach((item, idx) => {
            html += `
                <tr>
                    <td>${idx + 1}</td>
                    <td>${item.employee}</td>
                    <td><a href="/app/pension-contribution/${item.name}" target="_blank">${item.name}</a></td>
                </tr>
            `;
        });
        
        if (result.created_list.length > 20) {
            html += `
                <tr>
                    <td colspan="3" class="text-center text-muted">
                        <em>... and ${result.created_list.length - 20} more</em>
                    </td>
                </tr>
            `;
        }
        
        html += `
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }
    
    // Show skipped list
    if (result.skipped_list && result.skipped_list.length > 0) {
        html += `
            <div style="margin-top: 20px;">
                <h5>⊘ Skipped Records</h5>
                <div style="max-height: 150px; overflow-y: auto; border: 1px solid #ddd; padding: 10px;">
                    <table class="table table-sm table-bordered">
                        <thead>
                            <tr>
                                <th>Employee</th>
                                <th>Reason</th>
                            </tr>
                        </thead>
                        <tbody>
        `;
        
        result.skipped_list.forEach(item => {
            html += `
                <tr>
                    <td>${item.employee}</td>
                    <td><small class="text-muted">${item.reason}</small></td>
                </tr>
            `;
        });
        
        html += `
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }
    
    // Show errors
    if (result.errors && result.errors.length > 0) {
        html += `
            <div style="margin-top: 20px;">
                <h5 class="text-danger">✗ Errors</h5>
                <div style="max-height: 150px; overflow-y: auto; border: 1px solid #dc3545; padding: 10px; background-color: #fff5f5;">
                    <table class="table table-sm table-bordered">
                        <thead>
                            <tr>
                                <th>Employee</th>
                                <th>Error</th>
                            </tr>
                        </thead>
                        <tbody>
        `;
        
        result.errors.forEach(err => {
            html += `
                <tr>
                    <td>${err.employee}</td>
                    <td><small class="text-danger">${err.error}</small></td>
                </tr>
            `;
        });
        
        html += `
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }
    
    // Next steps
    html += `
        <div class="alert alert-success" style="margin-top: 20px;">
            <strong><i class="fa fa-lightbulb-o"></i> Next Steps:</strong>
            <ol style="margin: 10px 0 0 20px;">
                <li>Review created contributions</li>
                <li>Create Remittance Schedule for the period</li>
                <li>Export to Excel for payment processing</li>
                <li>Process payments to PFAs by 10th of next month</li>
            </ol>
        </div>
    `;
    
    html += '</div>';
    
    let d = new frappe.ui.Dialog({
        title: __('Bulk Creation Complete'),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'result_html',
                options: html
            }
        ],
        size: 'extra-large',
        primary_action_label: __('View Contributions'),
        primary_action: function() {
            d.hide();
            view_pension_contributions(frm);
        },
        secondary_action_label: __('Create Remittance Schedule'),
        secondary_action: function() {
            d.hide();
            create_remittance_schedule_dialog(frm);
        }
    });
    
    d.show();
    
    // Reload form to update indicators
    frm.reload_doc();
}

function view_pension_contributions(frm) {
    if (!frm.doc.start_date) {
        frappe.set_route('List', 'Pension Contribution', {
            'company': frm.doc.company
        });
        return;
    }
    
    let start_date = frappe.datetime.str_to_obj(frm.doc.start_date);
    let period_month = frappe.datetime.str_to_user(start_date, 'MMMM');
    let period_year = start_date.getFullYear();
    
    frappe.set_route('List', 'Pension Contribution', {
        'company': frm.doc.company,
        'period_month': period_month,
        'period_year': period_year
    });
}

function create_remittance_schedule_dialog(frm) {
    if (!frm.doc.start_date) {
        frappe.msgprint(__('Payroll start date not found'));
        return;
    }
    
    let start_date = frappe.datetime.str_to_obj(frm.doc.start_date);
    let period_month = frappe.datetime.str_to_user(start_date, 'MMMM');
    let period_year = start_date.getFullYear();
    
    // Check if already exists
    frappe.db.exists('Pension Remittance Schedule', {
        'company': frm.doc.company,
        'period_month': period_month,
        'period_year': period_year
    }).then(exists => {
        if (exists) {
            frappe.confirm(
                __('Remittance Schedule already exists for {0} {1}. Open it?', [period_month, period_year]),
                function() {
                    frappe.set_route('Form', 'Pension Remittance Schedule', exists);
                }
            );
        } else {
            frappe.confirm(
                __('Create Pension Remittance Schedule for {0} {1}?', [period_month, period_year]),
                function() {
                    create_remittance_schedule(frm, period_month, period_year);
                }
            );
        }
    });
}

function create_remittance_schedule(frm, period_month, period_year) {
    frappe.call({
        method: 'general.general_biz_apps.doctype.pension_remittance_schedule.pension_remittance_schedule.create_remittance_schedule',
        args: {
            company: frm.doc.company,
            period_month: period_month,
            period_year: period_year
        },
        freeze: true,
        freeze_message: __('Creating Remittance Schedule...'),
        callback: function(r) {
            if (r.message) {
                frappe.set_route('Form', 'Pension Remittance Schedule', r.message);
                frappe.show_alert({
                    message: __('Remittance Schedule created'),
                    indicator: 'green'
                }, 5);
            }
        }
    });
}

function show_pension_summary(frm) {
    if (!frm.doc.start_date) {
        frappe.msgprint(__('Payroll start date not found'));
        return;
    }
    
    let start_date = frappe.datetime.str_to_obj(frm.doc.start_date);
    let period_month = frappe.datetime.str_to_user(start_date, 'MMMM');
    let period_year = start_date.getFullYear();
    
    frappe.call({
        method: 'general.general_biz_apps.doctype.pension_contribution.pension_contribution.get_pension_summary_by_pfa',
        args: {
            company: frm.doc.company,
            month: period_month,
            year: period_year
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                display_pension_summary(r.message, period_month, period_year);
            } else {
                frappe.msgprint({
                    title: __('No Data'),
                    message: __('No pension contributions found for {0} {1}', [period_month, period_year]),
                    indicator: 'orange'
                });
            }
        }
    });
}

function display_pension_summary(data, month, year) {
    let total_employees = data.reduce((sum, pfa) => sum + pfa.employee_count, 0);
    let total_amount = data.reduce((sum, pfa) => sum + pfa.total_contribution, 0);
    
    let html = `
        <div style="padding: 20px;">
            <h4>Pension Summary - ${month} ${year}</h4>
            <hr>
            
            <div class="row" style="margin-bottom: 20px;">
                <div class="col-md-6">
                    <div class="card text-center" style="padding: 15px;">
                        <h3>${total_employees}</h3>
                        <p>Total Employees</p>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card text-center" style="padding: 15px;">
                        <h3 class="text-primary">${format_currency(total_amount)}</h3>
                        <p>Total Contribution</p>
                    </div>
                </div>
            </div>
            
            <h5>Breakdown by PFA</h5>
            <table class="table table-bordered">
                <thead style="background-color: #f8f9fa;">
                    <tr>
                        <th>PFA</th>
                        <th class="text-center">Employees</th>
                        <th class="text-right">Employee</th>
                        <th class="text-right">Employer</th>
                        <th class="text-right">Voluntary</th>
                        <th class="text-right">Total</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    data.forEach(pfa => {
        html += `
            <tr>
                <td><strong>${pfa.pension_fund_administrator}</strong></td>
                <td class="text-center">${pfa.employee_count}</td>
                <td class="text-right">${format_currency(pfa.total_employee)}</td>
                <td class="text-right">${format_currency(pfa.total_employer)}</td>
                <td class="text-right">${format_currency(pfa.total_voluntary || 0)}</td>
                <td class="text-right"><strong>${format_currency(pfa.total_contribution)}</strong></td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    frappe.msgprint({
        title: __('Pension Summary'),
        message: html,
        wide: true
    });
}

function format_currency(amount) {
    return frappe.format(amount, {fieldtype: 'Currency'});
}