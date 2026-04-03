// File: general_biz_apps/public/js/salary_slip_pension.js
// Extension for Salary Slip to add pension contribution features

frappe.ui.form.on('Salary Slip', {
    refresh: function(frm) {
        if (frm.doc.docstatus === 1) {
            add_pension_buttons(frm);
            show_pension_status(frm);
        }
    },
    
    onload: function(frm) {
        setup_pension_watchers(frm);
    },
    
    before_save: function(frm) {
        highlight_pension_components(frm);
    }
});

function add_pension_buttons(frm) {
    // Check if pension contribution already exists
    frappe.db.exists('Pension Contribution', {
        'salary_slip': frm.doc.name,
        'docstatus': ['!=', 2]
    }).then(exists => {
        if (exists) {
            // View existing contribution
            frm.add_custom_button(__('View Pension Contribution'), function() {
                frappe.set_route('Form', 'Pension Contribution', exists);
            }, __('Pension')).addClass('btn-primary');
            
            // View remittance schedule if linked
            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'Pension Contribution',
                    filters: { name: exists },
                    fieldname: 'remittance_schedule'
                },
                callback: function(r) {
                    if (r.message && r.message.remittance_schedule) {
                        frm.add_custom_button(__('View Remittance Schedule'), function() {
                            frappe.set_route('Form', 'Pension Remittance Schedule', r.message.remittance_schedule);
                        }, __('Pension'));
                    }
                }
            });
        } else {
            // Create pension contribution
            if (check_if_pension_applicable(frm)) {
                frm.add_custom_button(__('Create Pension Contribution'), function() {
                    create_pension_contribution(frm);
                }, __('Pension')).addClass('btn-warning');
            }
        }
        
        // Pension breakdown
        frm.add_custom_button(__('Pension Breakdown'), function() {
            show_pension_breakdown(frm);
        }, __('Pension'));
    });
}

function show_pension_status(frm) {
    // Check if employee has pension enabled
    if (!check_if_pension_applicable(frm)) {
        return;
    }
    
    // Check if pension contribution exists
    frappe.db.exists('Pension Contribution', {
        'salary_slip': frm.doc.name,
        'docstatus': ['!=', 2]
    }).then(exists => {
        if (exists) {
            // Get pension contribution details
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Pension Contribution',
                    name: exists
                },
                callback: function(r) {
                    if (r.message) {
                        display_pension_indicator(frm, r.message);
                    }
                }
            });
        } else {
            // Show warning if pension not created
            frm.dashboard.set_headline_alert(
                '<i class="fa fa-exclamation-circle"></i> Pension contribution not created yet',
                'orange'
            );
        }
    });
}

function display_pension_indicator(frm, pension_doc) {
    // Status indicator
    let status_color = {
        'Submitted': 'blue',
        'Pending': 'orange',
        'Scheduled': 'blue',
        'Paid': 'green',
        'Confirmed': 'darkgreen'
    };
    
    let color = status_color[pension_doc.remittance_status] || 'grey';
    frm.dashboard.add_indicator(
        __('Pension: {0}', [pension_doc.remittance_status || 'Created']),
        color
    );
    
    // Show pension summary card
    let html = `
        <div class="row" style="margin-top: 10px;">
            <div class="col-sm-12">
                <div class="card" style="border-left: 3px solid #2490ef;">
                    <div class="card-body">
                        <h6 class="card-title">Pension Contribution Summary</h6>
                        <div class="row">
                            <div class="col-sm-4">
                                <small class="text-muted">Employee (${pension_doc.employee_contribution_rate}%)</small>
                                <h6 class="text-success">${format_currency(pension_doc.employee_contribution_amount)}</h6>
                            </div>
                            <div class="col-sm-4">
                                <small class="text-muted">Employer (${pension_doc.employer_contribution_rate}%)</small>
                                <h6 class="text-warning">${format_currency(pension_doc.employer_contribution_amount)}</h6>
                            </div>
                            <div class="col-sm-4">
                                <small class="text-muted">Total Contribution</small>
                                <h6 class="text-primary">${format_currency(pension_doc.total_contribution)}</h6>
                            </div>
                        </div>
                        ${pension_doc.remittance_schedule ? 
                            `<div style="margin-top: 10px;">
                                <small class="text-muted">Remittance Schedule:</small>
                                <a href="/app/pension-remittance-schedule/${pension_doc.remittance_schedule}">
                                    ${pension_doc.remittance_schedule}
                                </a>
                            </div>` : ''
                        }
                    </div>
                </div>
            </div>
        </div>
    `;
    
    frm.dashboard.add_section(html);
}

function setup_pension_watchers(frm) {
    // Watch for changes in earnings and deductions
    if (frm.doc.docstatus === 0) {
        // Highlight pension-related components
        highlight_pension_components(frm);
    }
}

function highlight_pension_components(frm) {
    // Highlight pension components in earnings and deductions
    setTimeout(() => {
        // Earnings table
        if (frm.fields_dict.earnings && frm.fields_dict.earnings.grid) {
            frm.fields_dict.earnings.grid.grid_rows.forEach(row => {
                if (row.doc && row.doc.salary_component) {
                    let component_name = row.doc.salary_component.toLowerCase();
                    if (component_name.includes('pension')) {
                        $(row.row).css('background-color', '#fff9e6');
                        $(row.row).find('.grid-row-check').css('border-left', '3px solid #ffc107');
                    }
                }
            });
        }
        
        // Deductions table
        if (frm.fields_dict.deductions && frm.fields_dict.deductions.grid) {
            frm.fields_dict.deductions.grid.grid_rows.forEach(row => {
                if (row.doc && row.doc.salary_component) {
                    let component_name = row.doc.salary_component.toLowerCase();
                    if (component_name.includes('pension')) {
                        $(row.row).css('background-color', '#e6f7ff');
                        $(row.row).find('.grid-row-check').css('border-left', '3px solid #2490ef');
                    }
                }
            });
        }
    }, 500);
}

function check_if_pension_applicable(frm) {
    // Check if employee has pension enabled
    if (!frm.doc.employee) return false;
    
    let pension_applicable = false;
    
    frappe.call({
        method: 'frappe.client.get_value',
        args: {
            doctype: 'Employee',
            filters: { name: frm.doc.employee },
            fieldname: 'custom_pension_applicable'
        },
        async: false,
        callback: function(r) {
            if (r.message && r.message.custom_pension_applicable) {
                pension_applicable = true;
            }
        }
    });
    
    return pension_applicable;
}

function create_pension_contribution(frm) {
    // Validate
    if (!frm.doc.employee) {
        frappe.msgprint(__('Employee is required'));
        return;
    }
    
    if (frm.doc.docstatus !== 1) {
        frappe.msgprint(__('Salary Slip must be submitted first'));
        return;
    }
    
    // Preview pension amounts
    let pension_preview = extract_pension_preview(frm);
    
    if (!pension_preview.found) {
        frappe.msgprint({
            title: __('No Pension Components Found'),
            message: __('No pension-related components found in this salary slip. Please add pension components to salary structure.'),
            indicator: 'orange'
        });
        return;
    }
    
    // Show confirmation dialog
    show_create_pension_dialog(frm, pension_preview);
}

function extract_pension_preview(frm) {
    let employee_contrib = 0;
    let employer_contrib = 0;
    let voluntary_contrib = 0;
    let found = false;
    
    // Check deductions for employee contribution
    if (frm.doc.deductions) {
        frm.doc.deductions.forEach(d => {
            let component = d.salary_component.toLowerCase();
            if (component.includes('pension')) {
                if (component.includes('employee') || component.includes('deduction')) {
                    employee_contrib += d.amount;
                    found = true;
                } else if (component.includes('voluntary') || component.includes('additional')) {
                    voluntary_contrib += d.amount;
                    found = true;
                } else {
                    // Generic pension deduction
                    employee_contrib += d.amount;
                    found = true;
                }
            }
        });
    }
    
    // Check earnings for employer contribution
    if (frm.doc.earnings) {
        frm.doc.earnings.forEach(e => {
            let component = e.salary_component.toLowerCase();
            if (component.includes('pension') && component.includes('employer')) {
                employer_contrib += e.amount;
                found = true;
            }
        });
    }
    
    // If employer not found in earnings, calculate from base
    if (!employer_contrib && found) {
        employer_contrib = frm.doc.base * 0.10; // 10% default
    }
    
    return {
        found: found,
        employee_contrib: employee_contrib,
        employer_contrib: employer_contrib,
        voluntary_contrib: voluntary_contrib,
        total_contrib: employee_contrib + employer_contrib + voluntary_contrib,
        base_salary: frm.doc.base,
        gross_salary: frm.doc.gross_pay
    };
}

function show_create_pension_dialog(frm, preview) {
    let html = `
        <div style="padding: 15px;">
            <h5>Pension Contribution Preview</h5>
            <table class="table table-bordered">
                <tr>
                    <td><strong>Employee:</strong></td>
                    <td>${frm.doc.employee_name}</td>
                </tr>
                <tr>
                    <td><strong>Base Salary:</strong></td>
                    <td class="text-right">${format_currency(preview.base_salary)}</td>
                </tr>
                <tr style="background-color: #e6f7ff;">
                    <td><strong>Employee Contribution:</strong></td>
                    <td class="text-right">${format_currency(preview.employee_contrib)}</td>
                </tr>
                <tr style="background-color: #fff9e6;">
                    <td><strong>Employer Contribution:</strong></td>
                    <td class="text-right">${format_currency(preview.employer_contrib)}</td>
                </tr>
                ${preview.voluntary_contrib > 0 ? `
                <tr>
                    <td><strong>Voluntary Contribution:</strong></td>
                    <td class="text-right">${format_currency(preview.voluntary_contrib)}</td>
                </tr>
                ` : ''}
                <tr style="background-color: #f8f9fa; font-weight: bold;">
                    <td><strong>Total Contribution:</strong></td>
                    <td class="text-right text-primary">${format_currency(preview.total_contrib)}</td>
                </tr>
            </table>
            
            <div class="alert alert-info" style="margin-top: 10px;">
                <i class="fa fa-info-circle"></i> 
                This will create a Pension Contribution record that can be included in the monthly remittance schedule.
            </div>
        </div>
    `;
    
    let d = new frappe.ui.Dialog({
        title: __('Create Pension Contribution'),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'preview_html',
                options: html
            }
        ],
        primary_action_label: __('Create'),
        primary_action: function() {
            d.hide();
            execute_pension_creation(frm);
        }
    });
    
    d.show();
}

function execute_pension_creation(frm) {
    frappe.show_alert({
        message: __('Creating pension contribution...'),
        indicator: 'blue'
    });
    
    frappe.call({
        method: 'general.general_biz_apps.doctype.pension_contribution.pension_contribution.create_from_salary_slip',
        args: {
            salary_slip_name: frm.doc.name
        },
        freeze: true,
        freeze_message: __('Creating Pension Contribution...'),
        callback: function(r) {
            if (r.message) {
                frappe.show_alert({
                    message: __('Pension contribution created successfully'),
                    indicator: 'green'
                }, 5);
                
                // Refresh form to show new button
                frm.reload_doc();
                
                // Ask if user wants to view
                frappe.confirm(
                    __('Pension contribution created successfully. Do you want to view it?'),
                    function() {
                        frappe.set_route('Form', 'Pension Contribution', r.message);
                    }
                );
            }
        },
        error: function(err) {
            frappe.msgprint({
                title: __('Creation Failed'),
                message: __('Failed to create pension contribution. Check error log for details.'),
                indicator: 'red'
            });
        }
    });
}

function show_pension_breakdown(frm) {
    let pension_components = {
        employee: [],
        employer: [],
        voluntary: []
    };
    
    // Extract pension components
    if (frm.doc.deductions) {
        frm.doc.deductions.forEach(d => {
            let component = d.salary_component.toLowerCase();
            if (component.includes('pension')) {
                if (component.includes('voluntary') || component.includes('additional')) {
                    pension_components.voluntary.push({
                        component: d.salary_component,
                        amount: d.amount
                    });
                } else {
                    pension_components.employee.push({
                        component: d.salary_component,
                        amount: d.amount
                    });
                }
            }
        });
    }
    
    if (frm.doc.earnings) {
        frm.doc.earnings.forEach(e => {
            let component = e.salary_component.toLowerCase();
            if (component.includes('pension') && component.includes('employer')) {
                pension_components.employer.push({
                    component: e.salary_component,
                    amount: e.amount
                });
            }
        });
    }
    
    let html = `
        <div style="padding: 20px;">
            <h4>Pension Components Breakdown</h4>
            <p><strong>Employee:</strong> ${frm.doc.employee_name}</p>
            <p><strong>Period:</strong> ${frappe.datetime.str_to_user(frm.doc.start_date)} to ${frappe.datetime.str_to_user(frm.doc.end_date)}</p>
            <hr>
    `;
    
    // Employee contributions
    if (pension_components.employee.length > 0) {
        html += `
            <h5 class="text-primary">Employee Contributions</h5>
            <table class="table table-bordered table-sm">
                <thead>
                    <tr>
                        <th>Component</th>
                        <th class="text-right">Amount</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        let employee_total = 0;
        pension_components.employee.forEach(item => {
            html += `
                <tr>
                    <td>${item.component}</td>
                    <td class="text-right">${format_currency(item.amount)}</td>
                </tr>
            `;
            employee_total += item.amount;
        });
        
        html += `
                <tr style="font-weight: bold; background-color: #f8f9fa;">
                    <td>Total Employee</td>
                    <td class="text-right">${format_currency(employee_total)}</td>
                </tr>
                </tbody>
            </table>
        `;
    }
    
    // Employer contributions
    if (pension_components.employer.length > 0) {
        html += `
            <h5 class="text-warning" style="margin-top: 20px;">Employer Contributions</h5>
            <table class="table table-bordered table-sm">
                <thead>
                    <tr>
                        <th>Component</th>
                        <th class="text-right">Amount</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        let employer_total = 0;
        pension_components.employer.forEach(item => {
            html += `
                <tr>
                    <td>${item.component}</td>
                    <td class="text-right">${format_currency(item.amount)}</td>
                </tr>
            `;
            employer_total += item.amount;
        });
        
        html += `
                <tr style="font-weight: bold; background-color: #f8f9fa;">
                    <td>Total Employer</td>
                    <td class="text-right">${format_currency(employer_total)}</td>
                </tr>
                </tbody>
            </table>
        `;
    }
    
    // Voluntary contributions
    if (pension_components.voluntary.length > 0) {
        html += `
            <h5 class="text-success" style="margin-top: 20px;">Voluntary Contributions</h5>
            <table class="table table-bordered table-sm">
                <thead>
                    <tr>
                        <th>Component</th>
                        <th class="text-right">Amount</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        let voluntary_total = 0;
        pension_components.voluntary.forEach(item => {
            html += `
                <tr>
                    <td>${item.component}</td>
                    <td class="text-right">${format_currency(item.amount)}</td>
                </tr>
            `;
            voluntary_total += item.amount;
        });
        
        html += `
                <tr style="font-weight: bold; background-color: #f8f9fa;">
                    <td>Total Voluntary</td>
                    <td class="text-right">${format_currency(voluntary_total)}</td>
                </tr>
                </tbody>
            </table>
        `;
    }
    
    // Grand total
    let grand_total = 0;
    pension_components.employee.forEach(i => grand_total += i.amount);
    pension_components.employer.forEach(i => grand_total += i.amount);
    pension_components.voluntary.forEach(i => grand_total += i.amount);
    
    html += `
        <div class="alert alert-primary" style="margin-top: 20px;">
            <h5>Grand Total Pension Contribution</h5>
            <h3>${format_currency(grand_total)}</h3>
        </div>
    `;
    
    // Statutory compliance check
    let employee_rate = (pension_components.employee.reduce((sum, i) => sum + i.amount, 0) / frm.doc.base) * 100;
    let employer_rate = (pension_components.employer.reduce((sum, i) => sum + i.amount, 0) / frm.doc.base) * 100;
    
    html += `
        <div class="alert ${employee_rate >= 8 && employer_rate >= 10 ? 'alert-success' : 'alert-warning'}" style="margin-top: 20px;">
            <h6>Statutory Compliance Check</h6>
            <ul>
                <li>Employee Rate: <strong>${employee_rate.toFixed(2)}%</strong> (Minimum: 8%) ${employee_rate >= 8 ? '✓' : '✗'}</li>
                <li>Employer Rate: <strong>${employer_rate.toFixed(2)}%</strong> (Minimum: 10%) ${employer_rate >= 10 ? '✓' : '✗'}</li>
            </ul>
        </div>
    `;
    
    if (pension_components.employee.length === 0 && pension_components.employer.length === 0) {
        html = `
            <div style="padding: 20px;">
                <div class="alert alert-warning">
                    <h5><i class="fa fa-exclamation-triangle"></i> No Pension Components Found</h5>
                    <p>This salary slip does not contain any pension-related components.</p>
                    <p>Please ensure:</p>
                    <ul>
                        <li>Employee has pension enabled in Employee master</li>
                        <li>Salary structure includes pension components</li>
                        <li>Component names contain "Pension"</li>
                    </ul>
                </div>
            </div>
        `;
    }
    
    html += '</div>';
    
    frappe.msgprint({
        title: __('Pension Breakdown'),
        message: html,
        wide: true
    });
}

function format_currency(amount) {
    return frappe.format(amount, {fieldtype: 'Currency'});
}