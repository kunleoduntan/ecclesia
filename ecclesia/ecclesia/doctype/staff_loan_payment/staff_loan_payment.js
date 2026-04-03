// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

frappe.ui.form.on('Staff Loan Payment', {

    onload: function(frm) {
        // Set query filters for accounts
        frm.set_query('payment_account', function() {
            return {
                filters: {
                    account_type: ['in', ['Bank', 'Cash']],
                    is_group: 0,
                    company: frm.doc.company
                }
            };
        });

        frm.set_query('loan_account', function() {
            return {
                filters: {
                    account_type: 'Current Asset',
                    is_group: 0,
                    company: frm.doc.company
                }
            };
        });
    },

    refresh: function(frm) {
        // Add custom buttons based on document status
        add_custom_buttons(frm);
        
        // Set visual indicators
        set_status_indicator(frm);
        show_payment_summary(frm);
        
        // Show loan summary card
        show_loan_summary_card(frm);
    },

    company: function(frm) {
        if (frm.doc.company && !frm.doc.payment_account) {
            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'Company',
                    filters: { name: frm.doc.company },
                    fieldname: ['default_cash_account']
                },
                callback: function(r) {
                    if (r.message && r.message.default_cash_account) {
                        frm.set_value('payment_account', r.message.default_cash_account);
                    }
                }
            });
        }
    },

    employee: function(frm) {
        if (frm.doc.employee) {
            // Fetch existing loans
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.staff_loan_payment.staff_loan_payment.get_loan_balance',
                args: {
                    employee: frm.doc.employee
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        show_existing_loans_dialog(r.message);
                    }
                }
            });
        }
    },

    // 🔹 Core calculation trigger - Number of Installments
    number_of_installments: function(frm) {
        if (!frm.doc.total_loan_amount || 
            !frm.doc.number_of_installments || 
            !frm.doc.start_date) {
            return;
        }

        let total = flt(frm.doc.total_loan_amount);
        let installments = cint(frm.doc.number_of_installments);

        if (installments <= 0) {
            frappe.msgprint({
                title: __('Invalid Input'),
                message: __('Number of Installments must be greater than 0'),
                indicator: 'red'
            });
            return;
        }

        // Calculate Monthly Deduction
        let monthly = total / installments;
        frm.set_value('monthly_deduction_amount', flt(monthly, 2));

        // Calculate End Date
        calculate_end_date(frm);

        // Generate Schedule
        generate_schedule(frm);
    },

    monthly_deduction_amount: function(frm) {
        if (!frm.doc.total_loan_amount || 
            !frm.doc.monthly_deduction_amount || 
            !frm.doc.start_date) {
            return;
        }

        let total = flt(frm.doc.total_loan_amount);
        let monthly = flt(frm.doc.monthly_deduction_amount);

        if (monthly <= 0) return;

        let installments = Math.ceil(total / monthly);

        // Prevent recursion
        if (frm.doc.number_of_installments != installments) {
            frm.set_value('number_of_installments', installments);
        }
    },

    total_loan_amount: function(frm) {
        if (frm.doc.number_of_installments) {
            frm.trigger('number_of_installments');
        }
    },

    start_date: function(frm) {
        if (frm.doc.number_of_installments) {
            calculate_end_date(frm);
        }
    },

    apply_interest: function(frm) {
        if (!frm.doc.apply_interest) {
            frm.set_value('interest_rate', 0);
            frm.set_value('total_interest', 0);
        } else if (frm.doc.number_of_installments) {
            // Regenerate schedule with interest
            generate_schedule(frm);
        }
    },

    interest_rate: function(frm) {
        if (frm.doc.apply_interest && frm.doc.number_of_installments) {
            generate_schedule(frm);
        }
    },

    interest_calculation_method: function(frm) {
        if (frm.doc.apply_interest && frm.doc.number_of_installments) {
            generate_schedule(frm);
        }
    },

    create_all_at_once: function(frm) {
        if (frm.doc.create_all_at_once) {
            frappe.show_alert({
                message: __('One recurring Additional Salary will be created for the entire loan period'),
                indicator: 'blue'
            }, 7);
        } else {
            frappe.show_alert({
                message: __('Individual Additional Salary records will be created monthly'),
                indicator: 'blue'
            }, 7);
        }
    }
});


// =====================================================
// 🔹 Custom Buttons Manager
// =====================================================

function add_custom_buttons(frm) {
    // Clear existing custom buttons
    frm.clear_custom_buttons();

    // Draft document buttons
    if (frm.doc.docstatus === 0) {
        frm.add_custom_button(__('Generate Schedule'), function() {
            if (validate_schedule_generation(frm)) {
                generate_schedule(frm);
                frappe.show_alert({
                    message: __('Schedule generated successfully'),
                    indicator: 'green'
                }, 5);
            }
        }).addClass('btn-primary');
    }

    // Submitted document buttons
    if (frm.doc.docstatus === 1 && frm.doc.status === 'Active') {
        
        // Update Payment Status
        frm.add_custom_button(__('Update Payment Status'), function() {
            update_payment_status(frm);
        }, __('Actions')).addClass('btn-warning');

        // View Additional Salaries
        frm.add_custom_button(__('Additional Salaries'), function() {
            frappe.set_route('List', 'Additional Salary', {
                ref_doctype: frm.doc.doctype,
                ref_docname: frm.doc.name
            });
        }, __('View'));

        // View Disbursement Payment
        if (frm.doc.payment_entry) {
            frm.add_custom_button(__('Disbursement Payment'), function() {
                frappe.set_route('Form', 'Payment Entry', frm.doc.payment_entry);
            }, __('View'));
        }

        // View Interest Journal Entries
        if (frm.doc.apply_interest) {
            frm.add_custom_button(__('Interest Journals'), function() {
                view_interest_journals(frm);
            }, __('View'));
        }

        // Loan Statement Report
        frm.add_custom_button(__('Loan Statement'), function() {
            generate_loan_statement(frm);
        }, __('Reports'));
    }

    // Completed loan buttons
    if (frm.doc.docstatus === 1 && frm.doc.status === 'Completed') {
        frm.add_custom_button(__('View Completion Summary'), function() {
            show_completion_summary(frm);
        }).addClass('btn-success');
    }
}


// =====================================================
// 🔹 Schedule Generator with Interest Calculation
// =====================================================

function generate_schedule(frm) {
    let total = flt(frm.doc.total_loan_amount);
    let installments = cint(frm.doc.number_of_installments);
    let start_date = frappe.datetime.str_to_obj(frm.doc.start_date);
    let apply_interest = frm.doc.apply_interest || 0;
    let annual_rate = flt(frm.doc.interest_rate) / 100;
    let interest_method = frm.doc.interest_calculation_method || 'Flat Rate';

    if (!total || !installments || !start_date) return;

    frm.clear_table('loan_deduction_schedule');

    let monthly = flt(frm.doc.monthly_deduction_amount);
    let remaining_principal = total;
    let total_interest = 0;
    let monthly_interest_rate = annual_rate / 12;

    let current_date = new Date(start_date);

    for (let i = 0; i < installments; i++) {
        let principal_amount = 0;
        let interest_amount = 0;
        let total_deduction = 0;

        if (apply_interest && annual_rate > 0) {
            if (interest_method === 'Flat Rate') {
                // Flat Rate: Interest on original loan amount
                interest_amount = (total * monthly_interest_rate);
                principal_amount = monthly;
                total_deduction = principal_amount + interest_amount;
            } else {
                // Reducing Balance: Interest on remaining principal
                interest_amount = remaining_principal * monthly_interest_rate;
                principal_amount = monthly - interest_amount;
                total_deduction = monthly;

                // Ensure principal doesn't go negative
                if (principal_amount < 0) {
                    principal_amount = 0;
                    interest_amount = monthly;
                }
            }
        } else {
            // No interest
            principal_amount = Math.min(monthly, remaining_principal);
            total_deduction = principal_amount;
        }

        // Adjust last installment
        if (i === installments - 1) {
            if (apply_interest && interest_method === 'Reducing Balance') {
                principal_amount = remaining_principal;
                interest_amount = remaining_principal * monthly_interest_rate;
                total_deduction = principal_amount + interest_amount;
            } else if (!apply_interest) {
                principal_amount = remaining_principal;
                total_deduction = principal_amount;
            } else {
                // Flat rate last installment
                principal_amount = remaining_principal;
                total_deduction = principal_amount + interest_amount;
            }
        }

        // Get last day of month for payment date
        let payment_month = new Date(current_date);
        let payment_date = new Date(
            payment_month.getFullYear(),
            payment_month.getMonth() + 1,
            0
        );

        let row = frm.add_child('loan_deduction_schedule');
        row.payment_date = frappe.datetime.obj_to_str(payment_date);
        row.deduction_amount = flt(total_deduction, 2);
        row.principal_amount = flt(principal_amount, 2);
        row.interest_amount = flt(interest_amount, 2);
        row.is_paid = 0;

        total_interest += interest_amount;
        remaining_principal -= principal_amount;

        current_date.setMonth(current_date.getMonth() + 1);
    }

    // Set total interest
    if (apply_interest) {
        frm.set_value('total_interest', flt(total_interest, 2));
    } else {
        frm.set_value('total_interest', 0);
    }

    frm.refresh_field('loan_deduction_schedule');
    calculate_totals(frm);
}


// =====================================================
// 🔹 Helper Functions
// =====================================================

function calculate_end_date(frm) {
    if (!frm.doc.start_date || !frm.doc.number_of_installments) return;

    let start_date = frappe.datetime.str_to_obj(frm.doc.start_date);
    let installments = cint(frm.doc.number_of_installments);
    
    let end_date = new Date(start_date);
    end_date.setMonth(end_date.getMonth() + installments - 1);

    let last_day = new Date(
        end_date.getFullYear(),
        end_date.getMonth() + 1,
        0
    );

    frm.set_value('end_date', frappe.datetime.obj_to_str(last_day));
}

function validate_schedule_generation(frm) {
    if (!frm.doc.total_loan_amount) {
        frappe.msgprint(__('Please enter Total Loan Amount'));
        return false;
    }
    if (!frm.doc.number_of_installments && !frm.doc.monthly_deduction_amount) {
        frappe.msgprint(__('Please enter either Number of Installments or Monthly Deduction Amount'));
        return false;
    }
    if (!frm.doc.start_date) {
        frappe.msgprint(__('Please enter Repayment Start Date'));
        return false;
    }
    if (frm.doc.apply_interest && !frm.doc.interest_rate) {
        frappe.msgprint(__('Please enter Interest Rate'));
        return false;
    }
    return true;
}

function calculate_totals(frm) {
    let total_paid = 0;

    (frm.doc.loan_deduction_schedule || []).forEach(function(row) {
        if (row.is_paid) {
            total_paid += flt(row.deduction_amount);
        }
    });

    frm.set_value('total_deducted_amount', flt(total_paid, 2));
    frm.set_value('outstanding_amount', flt(frm.doc.total_loan_amount) - total_paid);
}


// =====================================================
// 🔹 Action Functions
// =====================================================

function update_payment_status(frm) {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.staff_loan_payment.staff_loan_payment.update_loan_repayment_status',
        args: {
            loan_payment_name: frm.doc.name
        },
        freeze: true,
        freeze_message: __('Updating payment status...'),
        callback: function(r) {
            if (r.message) {
                frappe.show_alert({
                    message: __('Payment status updated successfully'),
                    indicator: 'green'
                }, 5);
                frm.reload_doc();
            }
        }
    });
}

function view_interest_journals(frm) {
    let journal_entries = [];
    (frm.doc.loan_deduction_schedule || []).forEach(function(row) {
        if (row.interest_journal_entry) {
            journal_entries.push(row.interest_journal_entry);
        }
    });

    if (journal_entries.length > 0) {
        frappe.set_route('List', 'Journal Entry', {
            name: ['in', journal_entries]
        });
    } else {
        frappe.msgprint({
            title: __('No Records Found'),
            message: __('No interest journal entries have been created yet'),
            indicator: 'orange'
        });
    }
}

function generate_loan_statement(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Loan Statement'),
        fields: [
            {
                fieldname: 'html_content',
                fieldtype: 'HTML'
            }
        ],
        size: 'large'
    });

    let html = generate_statement_html(frm);
    d.fields_dict.html_content.$wrapper.html(html);
    
    d.show();
}

function generate_statement_html(frm) {
    let paid_count = 0;
    let paid_amount = 0;
    let pending_count = 0;
    let pending_amount = 0;

    (frm.doc.loan_deduction_schedule || []).forEach(function(row) {
        if (row.is_paid) {
            paid_count++;
            paid_amount += flt(row.deduction_amount);
        } else {
            pending_count++;
            pending_amount += flt(row.deduction_amount);
        }
    });

    let html = `
        <div style="padding: 20px;">
            <h3 style="text-align: center; color: #2c3e50;">Loan Statement</h3>
            <hr>
            <table class="table table-bordered" style="margin-top: 20px;">
                <tr>
                    <td><strong>Employee:</strong></td>
                    <td>${frm.doc.employee_name}</td>
                    <td><strong>Loan Type:</strong></td>
                    <td>${frm.doc.loan_type}</td>
                </tr>
                <tr>
                    <td><strong>Loan Amount:</strong></td>
                    <td>${format_currency(frm.doc.total_loan_amount)}</td>
                    <td><strong>Start Date:</strong></td>
                    <td>${frappe.datetime.str_to_user(frm.doc.start_date)}</td>
                </tr>
                <tr>
                    <td><strong>Monthly Deduction:</strong></td>
                    <td>${format_currency(frm.doc.monthly_deduction_amount)}</td>
                    <td><strong>End Date:</strong></td>
                    <td>${frappe.datetime.str_to_user(frm.doc.end_date)}</td>
                </tr>
                <tr>
                    <td><strong>Total Interest:</strong></td>
                    <td>${format_currency(frm.doc.total_interest || 0)}</td>
                    <td><strong>Outstanding:</strong></td>
                    <td><strong style="color: #e74c3c;">${format_currency(frm.doc.outstanding_amount)}</strong></td>
                </tr>
            </table>

            <h4 style="margin-top: 30px;">Payment Summary</h4>
            <div class="row" style="margin-top: 15px;">
                <div class="col-sm-6">
                    <div class="alert alert-success">
                        <strong>Paid Installments:</strong> ${paid_count} (${format_currency(paid_amount)})
                    </div>
                </div>
                <div class="col-sm-6">
                    <div class="alert alert-warning">
                        <strong>Pending Installments:</strong> ${pending_count} (${format_currency(pending_amount)})
                    </div>
                </div>
            </div>

            <h4 style="margin-top: 30px;">Payment Schedule</h4>
            <table class="table table-striped" style="margin-top: 15px;">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Principal</th>
                        <th>Interest</th>
                        <th>Total</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
    `;

    (frm.doc.loan_deduction_schedule || []).forEach(function(row) {
        let status_badge = row.is_paid 
            ? '<span class="badge badge-success">Paid</span>' 
            : '<span class="badge badge-warning">Pending</span>';
        
        html += `
            <tr>
                <td>${frappe.datetime.str_to_user(row.payment_date)}</td>
                <td>${format_currency(row.principal_amount)}</td>
                <td>${format_currency(row.interest_amount)}</td>
                <td><strong>${format_currency(row.deduction_amount)}</strong></td>
                <td>${status_badge}</td>
            </tr>
        `;
    });

    html += `
                </tbody>
            </table>
        </div>
    `;

    return html;
}

function show_completion_summary(frm) {
    frappe.msgprint({
        title: __('Loan Completion Summary'),
        message: `
            <div style="padding: 15px;">
                <p><strong>Loan has been fully repaid!</strong></p>
                <hr>
                <table class="table">
                    <tr>
                        <td>Total Loan Amount:</td>
                        <td><strong>${format_currency(frm.doc.total_loan_amount)}</strong></td>
                    </tr>
                    <tr>
                        <td>Total Interest Paid:</td>
                        <td><strong>${format_currency(frm.doc.total_interest || 0)}</strong></td>
                    </tr>
                    <tr>
                        <td>Total Amount Paid:</td>
                        <td><strong>${format_currency(frm.doc.total_deducted_amount)}</strong></td>
                    </tr>
                    <tr>
                        <td>Number of Installments:</td>
                        <td><strong>${frm.doc.number_of_installments}</strong></td>
                    </tr>
                    <tr>
                        <td>Loan Duration:</td>
                        <td><strong>${frappe.datetime.str_to_user(frm.doc.start_date)} to ${frappe.datetime.str_to_user(frm.doc.end_date)}</strong></td>
                    </tr>
                </table>
            </div>
        `,
        indicator: 'green',
        primary_action: {
            label: __('Print Certificate'),
            action: function() {
                frm.print_doc();
            }
        }
    });
}

function show_existing_loans_dialog(loans) {
    let html = '<table class="table table-bordered"><thead><tr><th>Loan Type</th><th>Outstanding</th></tr></thead><tbody>';
    
    loans.forEach(function(loan) {
        html += `<tr><td>${loan.loan_type}</td><td>${format_currency(loan.outstanding_amount)}</td></tr>`;
    });
    
    html += '</tbody></table>';

    frappe.msgprint({
        title: __('Existing Active Loans'),
        message: html,
        indicator: 'blue'
    });
}


// =====================================================
// 🔹 Visual Indicators & Summary Cards
// =====================================================

function show_loan_summary_card(frm) {
    if (frm.doc.docstatus === 1 && frm.doc.loan_deduction_schedule) {
        let total_principal = 0;
        let total_interest = 0;
        
        frm.doc.loan_deduction_schedule.forEach(function(row) {
            total_principal += flt(row.principal_amount);
            total_interest += flt(row.interest_amount);
        });

        let progress_percent = ((flt(frm.doc.total_deducted_amount) / flt(frm.doc.total_loan_amount)) * 100).toFixed(1);

        let html = `
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 20px; 
                        border-radius: 10px; 
                        color: white; 
                        margin-bottom: 15px;">
                <h4 style="color: white; margin-bottom: 15px;">
                    <i class="fa fa-money"></i> Loan Overview
                </h4>
                <div class="row">
                    <div class="col-sm-3">
                        <div style="text-align: center;">
                            <div style="font-size: 28px; font-weight: bold;">${format_currency(frm.doc.total_loan_amount)}</div>
                            <div style="opacity: 0.9;">Total Loan</div>
                        </div>
                    </div>
                    <div class="col-sm-3">
                        <div style="text-align: center;">
                            <div style="font-size: 28px; font-weight: bold;">${format_currency(frm.doc.outstanding_amount)}</div>
                            <div style="opacity: 0.9;">Outstanding</div>
                        </div>
                    </div>
                    <div class="col-sm-3">
                        <div style="text-align: center;">
                            <div style="font-size: 28px; font-weight: bold;">${frm.doc.number_of_installments}</div>
                            <div style="opacity: 0.9;">Installments</div>
                        </div>
                    </div>
                    <div class="col-sm-3">
                        <div style="text-align: center;">
                            <div style="font-size: 28px; font-weight: bold;">${progress_percent}%</div>
                            <div style="opacity: 0.9;">Completed</div>
                        </div>
                    </div>
                </div>
                <div style="margin-top: 15px;">
                    <div class="progress" style="height: 25px; background: rgba(255,255,255,0.3);">
                        <div class="progress-bar progress-bar-success" role="progressbar" 
                             style="width: ${progress_percent}%; background: #2ecc71;">
                            ${progress_percent}% Repaid
                        </div>
                    </div>
                </div>
            </div>
        `;

        frm.dashboard.add_section(html, __('Summary'));
        frm.dashboard.show();
    }
}

function set_status_indicator(frm) {
    if (frm.doc.docstatus !== 1) return;

    if (frm.doc.status === 'Active') {
        let message = __('Outstanding: {0}', [format_currency(frm.doc.outstanding_amount || 0)]);
        if (frm.doc.apply_interest) {
            message += __(', Total Interest: {0}', [format_currency(frm.doc.total_interest || 0)]);
        }
        frm.dashboard.set_headline_alert(message, 'blue');
    } else if (frm.doc.status === 'Completed') {
        frm.dashboard.set_headline_alert(__('Loan Fully Paid ✓'), 'green');
    }
}

function show_payment_summary(frm) {
    if (frm.doc.docstatus !== 1) return;

    let paid = 0;
    let pending = 0;
    let paid_amount = 0;
    let pending_amount = 0;

    (frm.doc.loan_deduction_schedule || []).forEach(function(row) {
        if (row.is_paid) {
            paid++;
            paid_amount += flt(row.deduction_amount);
        } else {
            pending++;
            pending_amount += flt(row.deduction_amount);
        }
    });

    let html = `
        <div class="row" style="margin-top: 15px;">
            <div class="col-sm-4">
                <div class="alert alert-info" style="margin-bottom: 10px;">
                    <i class="fa fa-list"></i> <strong>Total Installments:</strong> 
                    <span class="pull-right">${frm.doc.number_of_installments || 0}</span>
                </div>
            </div>
            <div class="col-sm-4">
                <div class="alert alert-success" style="margin-bottom: 10px;">
                    <i class="fa fa-check-circle"></i> <strong>Paid:</strong> 
                    <span class="pull-right">${paid} (${format_currency(paid_amount)})</span>
                </div>
            </div>
            <div class="col-sm-4">
                <div class="alert alert-warning" style="margin-bottom: 10px;">
                    <i class="fa fa-clock-o"></i> <strong>Pending:</strong> 
                    <span class="pull-right">${pending} (${format_currency(pending_amount)})</span>
                </div>
            </div>
        </div>
    `;

    frm.set_df_property('loan_deduction_schedule_section', 'description', html);
}


// =====================================================
// 🔹 Child Table Events
// =====================================================

frappe.ui.form.on('Loan Deduction Schedule', {
    is_paid: function(frm) {
        calculate_totals(frm);
    },

    loan_deduction_schedule_remove: function(frm) {
        calculate_totals(frm);
    }
});