// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

// loan_repayment_entry.js
frappe.ui.form.on('Loan Repayment Entry', {
    setup: function(frm) {
        // Set default payment date if not set
        if (!frm.doc.payment_date) {
            frm.set_value('payment_date', frappe.datetime.get_today());
        }
    },

    refresh: function(frm) {
        // Style the form
        set_form_style(frm);
        
        // Add custom buttons based on document status
        if (!frm.is_new() && frm.doc.docstatus === 0) {
            add_custom_buttons(frm);
        }
        
        // Show payment summary if document is saved
        if (!frm.is_new() && frm.doc.loan) {
            show_payment_summary(frm);
        }
    },

    // When loan is selected, fetch loan details
    loan: function(frm) {
        if (frm.doc.loan) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Employee Loan Application',
                    name: frm.doc.loan
                },
                callback: function(r) {
                    if (r.message) {
                        let loan = r.message;
                        frm.set_value('employee', loan.employee);
                        frm.set_value('employee_name', loan.employee_name);
                        
                        // Show pending installment info
                        show_pending_installment_info(frm, loan);
                    }
                }
            });
        }
    },

    // Validate amount paid is positive
    amount_paid: function(frm) {
        if (frm.doc.amount_paid && frm.doc.amount_paid < 0) {
            frappe.msgprint({
                title: __('Invalid Amount'),
                message: __('Amount paid cannot be negative'),
                indicator: 'red'
            });
            frm.set_value('amount_paid', 0);
        }
        
        // Auto-calculate if we have loan data
        if (frm.doc.loan && frm.doc.amount_paid) {
            calculate_principal_interest(frm);
        }
    },

    // Validate payment date is not in future
    payment_date: function(frm) {
        if (frm.doc.payment_date) {
            let today = frappe.datetime.get_today();
            if (frm.doc.payment_date > today) {
                frappe.msgprint({
                    title: __('Warning'),
                    message: __('Payment date is in the future. Are you sure?'),
                    indicator: 'orange'
                });
            }
        }
    },

    // When payment mode changes
    payment_mode: function(frm) {
        if (frm.doc.payment_mode === 'Payroll Deduction') {
            frm.set_df_property('salary_slip', 'reqd', 1);
            frm.set_df_property('reference_no', 'reqd', 0);
        } else {
            frm.set_df_property('salary_slip', 'reqd', 0);
            frm.set_df_property('reference_no', 'reqd', 1);
        }
    },

    // Validate before save
    validate: function(frm) {
        // Ensure amount paid matches expected (approximately)
        if (frm.doc.loan && frm.doc.amount_paid) {
            return frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Employee Loan Application',
                    name: frm.doc.loan
                },
                callback: function(r) {
                    if (r.message) {
                        let loan = r.message;
                        let pending = (loan.repayment_schedule || []).filter(
                            row => row.status === 'Pending'
                        );
                        
                        if (pending.length > 0) {
                            let expected = pending[0].monthly_amount;
                            let diff = Math.abs(frm.doc.amount_paid - expected);
                            
                            if (diff > 1 && diff / expected > 0.1) {
                                frappe.msgprint({
                                    title: __('Payment Amount Mismatch'),
                                    message: __(`Payment amount ₦${frm.doc.amount_paid.toFixed(2)} 
                                        differs significantly from expected ₦${expected.toFixed(2)}`),
                                    indicator: 'orange'
                                });
                            }
                        }
                    }
                }
            });
        }
    },

    // Before submit, confirm if amount differs
    before_submit: function(frm) {
        if (frm.doc.amount_paid && frm.doc.principal_paid) {
            let diff = frm.doc.amount_paid - (frm.doc.principal_paid + frm.doc.interest_paid);
            if (Math.abs(diff) > 0.01) {
                frappe.confirm(
                    __('The payment amount (₦' + frm.doc.amount_paid.toFixed(2) + 
                      ') does not match principal + interest (₦' + 
                      (frm.doc.principal_paid + frm.doc.interest_paid).toFixed(2) + 
                      '). Do you want to continue?'),
                    function() {
                        // User confirmed, proceed with submit
                        frm.submit();
                    }
                );
                return false;
            }
        }
    },

    // After load, show loan summary
    onload: function(frm) {
        if (frm.doc.loan) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Employee Loan Application',
                    name: frm.doc.loan
                },
                callback: function(r) {
                    if (r.message) {
                        show_loan_summary(frm, r.message);
                    }
                }
            });
        }
    }
});

// Helper function to calculate principal and interest
function calculate_principal_interest(frm) {
    frappe.call({
        method: 'frappe.client.get',
        args: {
            doctype: 'Employee Loan Application',
            name: frm.doc.loan
        },
        callback: function(r) {
            if (r.message) {
                let loan = r.message;
                let pending = (loan.repayment_schedule || []).filter(
                    row => row.status === 'Pending'
                );
                
                if (pending.length > 0) {
                    let next_inst = pending[0];
                    frm.set_value('principal_paid', next_inst.principal);
                    frm.set_value('interest_paid', next_inst.interest);
                    
                    // If amount paid is different, adjust principal
                    if (frm.doc.amount_paid && 
                        Math.abs(frm.doc.amount_paid - next_inst.monthly_amount) > 1) {
                        let diff = frm.doc.amount_paid - next_inst.monthly_amount;
                        frm.set_value('principal_paid', 
                            flt(next_inst.principal) + diff);
                    }
                } else {
                    frappe.msgprint({
                        title: __('No Pending Installments'),
                        message: __('This loan has no pending installments to repay.'),
                        indicator: 'red'
                    });
                }
            }
        }
    });
}

// Show pending installment info
function show_pending_installment_info(frm, loan) {
    let pending = (loan.repayment_schedule || []).filter(
        row => row.status === 'Pending'
    );
    
    if (pending.length > 0) {
        let next = pending[0];
        let html = `
            <div class="alert alert-info">
                <strong>Next Installment:</strong><br>
                Due Date: ${frappe.datetime.str_to_user(next.payment_date)}<br>
                Amount: ₦${next.monthly_amount.toFixed(2)}<br>
                Principal: ₦${next.principal.toFixed(2)}<br>
                Interest: ₦${next.interest.toFixed(2)}<br>
                <small>Remaining installments: ${pending.length}</small>
            </div>
        `;
        
        frm.dashboard.add_indicator(__('Next Payment: ₦' + next.monthly_amount.toFixed(2)), 'blue');
        
        // Show in a message
        frappe.msgprint({
            title: __('Pending Installment'),
            message: html,
            indicator: 'blue'
        });
    }
}

// Show loan summary
function show_loan_summary(frm, loan) {
    let html = `
        <table class="table table-bordered" style="background-color: #f8f9fa;">
            <tr>
                <th>Outstanding Principal</th>
                <th>Outstanding Interest</th>
                <th>Total Paid</th>
                <th>Installments Paid</th>
                <th>Status</th>
            </tr>
            <tr>
                <td>₦${loan.outstanding_principal.toFixed(2)}</td>
                <td>₦${loan.outstanding_interest.toFixed(2)}</td>
                <td>₦${loan.total_amount_paid.toFixed(2)}</td>
                <td>${loan.installments_paid || 0}</td>
                <td><span class="label label-${loan.status === 'Closed' ? 'success' : 'primary'}">${loan.status}</span></td>
            </tr>
        </table>
    `;
    
    frm.dashboard.add_section(html, __('Loan Summary'));
}

// Show payment summary for this document
function show_payment_summary(frm) {
    if (frm.doc.principal_paid || frm.doc.interest_paid) {
        let html = `
            <div style="padding: 10px; background-color: #f0f7ff; border-radius: 5px;">
                <strong>Payment Breakdown:</strong><br>
                Principal: ₦${(frm.doc.principal_paid || 0).toFixed(2)}<br>
                Interest: ₦${(frm.doc.interest_paid || 0).toFixed(2)}<br>
                <strong>Total: ₦${((frm.doc.principal_paid || 0) + (frm.doc.interest_paid || 0)).toFixed(2)}</strong>
            </div>
        `;
        frm.dashboard.add_section(html, __('This Payment'));
    }
}

// Add custom buttons
function add_custom_buttons(frm) {
    frm.add_custom_button(__('Get Next Installment'), function() {
        calculate_principal_interest(frm);
    });
    
    frm.add_custom_button(__('View Loan'), function() {
        frappe.set_route('Form', 'Employee Loan Application', frm.doc.loan);
    });
    
    if (frm.doc.journal_entry) {
        frm.add_custom_button(__('View Journal Entry'), function() {
            frappe.set_route('Form', 'Journal Entry', frm.doc.journal_entry);
        });
    }
}

// Set form styling
function set_form_style(frm) {
    // Hide columns if needed
    if (frm.doc.docstatus === 1) {
        frm.set_df_property('amount_paid', 'read_only', 1);
    }
    
    // Set field colors
    frm.set_df_property('principal_paid', 'description', 'Auto-calculated from loan schedule');
    frm.set_df_property('interest_paid', 'description', 'Auto-calculated from loan schedule');
    
    // Add currency symbols to labels
    frm.set_df_property('amount_paid', 'label', 'Amount Paid (₦)');
    frm.set_df_property('principal_paid', 'label', 'Principal (₦)');
    frm.set_df_property('interest_paid', 'label', 'Interest (₦)');
}

// Additional field event for reference number based on payment mode
frappe.ui.form.on('Loan Repayment Entry', {
    reference_no: function(frm) {
        if (frm.doc.payment_mode === 'Bank Transfer' && !frm.doc.reference_no) {
            frappe.msgprint({
                title: __('Warning'),
                message: __('Reference number is recommended for Bank Transfer'),
                indicator: 'orange'
            });
        }
    },
    
    salary_slip: function(frm) {
        if (frm.doc.salary_slip && frm.doc.payment_mode !== 'Payroll Deduction') {
            frappe.msgprint({
                title: __('Warning'),
                message: __('Salary Slip is linked but payment mode is not Payroll Deduction'),
                indicator: 'orange'
            });
        }
    }
});