// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Loan Application", {
    setup: function(frm) {
        // Set default values
        if (!frm.doc.application_date) {
            frm.set_value('application_date', frappe.datetime.get_today());
        }
        if (!frm.doc.status) {
            frm.set_value('status', 'Draft');
        }
        if (!frm.doc.first_deduction_date) {
            // Set to first day of next month by default
            let next_month = frappe.datetime.add_months(frappe.datetime.get_today(), 1);
            let first_day = next_month.substring(0, 7) + '-01';
            frm.set_value('first_deduction_date', first_day);
        }
        
        // Set loan account head from loan type if available
        if (frm.doc.loan_type && !frm.doc.loan_account_head) {
            frappe.db.get_value('Employee Loan Type', frm.doc.loan_type, 'loan_account', function(r) {
                if (r && r.loan_account) {
                    frm.set_value('loan_account_head', r.loan_account);
                }
            });
        }
    },

    refresh: function(frm) {
        _set_status_indicator(frm);
        _render_dashboard(frm);
        _add_action_buttons(frm);
        _populate_repayment_schedule(frm);
        
        // Make repayment schedule read-only
        frm.set_df_property('repayment_schedule', 'read_only', 1);
    },

    // Trigger recalculation on field changes
    principal_amount: function(frm) {
        _recompute_and_update_schedule(frm);
    },
    
    tenure_months: function(frm) {
        _recompute_and_update_schedule(frm);
    },
    
    loan_type: function(frm) {
        _on_loan_type_change(frm);
    },
    
    first_deduction_date: function(frm) {
        _recompute_and_update_schedule(frm);
    },
    
    interest_rate: function(frm) {
        _recompute_and_update_schedule(frm);
    },
    
    status: function(frm) {
        _set_status_indicator(frm);
        _render_dashboard(frm);
    },
    
    outstanding_principal: function(frm) {
        _render_dashboard(frm);
    },
    
    installments_paid: function(frm) {
        _render_dashboard(frm);
    },

    employee: function(frm) {
        if (frm.doc.employee) {
            frappe.db.get_value('Employee', frm.doc.employee, ['employee_name', 'department'], function(r) {
                if (r) {
                    frm.set_value('employee_name', r.employee_name);
                    frm.set_value('department', r.department);
                }
            });
        }
    },

    guarantor: function(frm) {
        if (frm.doc.guarantor) {
            frappe.db.get_value('Employee', frm.doc.guarantor, 'employee_name', function(r) {
                if (r) {
                    frm.set_value('guarantor_name', r.employee_name);
                }
            });
        } else {
            frm.set_value('guarantor_name', '');
        }
    },
    
    // Validate before save
    validate: function(frm) {
        // Ensure first deduction date is valid
        if (frm.doc.first_deduction_date) {
            let date_parts = frm.doc.first_deduction_date.split('-');
            if (date_parts.length === 3 && date_parts[2] !== '01') {
                frappe.msgprint({
                    title: __('Warning'),
                    message: __('First deduction date should typically be the 1st of the month for payroll deduction.'),
                    indicator: 'orange'
                });
            }
        }
        
        // Validate guarantor consent if guarantor is set
        if (frm.doc.guarantor && !frm.doc.guarantor_consent) {
            frappe.msgprint({
                title: __('Warning'),
                message: __('Please confirm guarantor consent before submitting.'),
                indicator: 'orange'
            });
        }
    },
    
    // Before submit, check if approved
    before_submit: function(frm) {
        if (frm.doc.status !== 'Approved') {
            frappe.throw(__('Only approved applications can be submitted.'));
        }
    }
});


// ── Status indicator ──────────────────────────────────────────────────

function _set_status_indicator(frm) {
    if (!frm.doc.status) return;
    
    const map = {
        "Draft": { color: "gray", label: "Draft" },
        "Pending HR Review": { color: "orange", label: "Pending HR Review" },
        "Pending Manager Approval": { color: "orange", label: "Pending Manager" },
        "Pending Finance Approval": { color: "orange", label: "Pending Finance" },
        "Approved": { color: "blue", label: "Approved" },
        "Disbursed": { color: "blue", label: "Disbursed" },
        "Active": { color: "green", label: "Active" },
        "Closed": { color: "teal", label: "Closed" },
        "Rejected": { color: "red", label: "Rejected" },
        "Cancelled": { color: "darkgrey", label: "Cancelled" }
    };
    
    const status = map[frm.doc.status] || { color: "gray", label: frm.doc.status };
    frm.page.set_indicator(status.label, status.color);
}


// ── Loan type change ──────────────────────────────────────────────────

function _on_loan_type_change(frm) {
    if (!frm.doc.loan_type) return;

    frappe.db.get_doc("Employee Loan Type", frm.doc.loan_type).then(lt => {
        frm.set_value("interest_rate", lt.annual_interest_rate || 0);
        frm.set_value("annual_interest_rate", lt.annual_interest_rate || 0);
        frm.set_value("loan_account_head", lt.loan_account || '');

        // Set field properties
        frm.set_df_property("principal_amount", "description",
            `Max: ₦${(lt.max_amount || 0).toLocaleString("en-NG")} · ` +
            `Max tenure: ${lt.max_tenure_months || 0} months`
        );
        frm.set_df_property("tenure_months", "description",
            `Max: ${lt.max_tenure_months || 0} months`
        );
        
        // Guarantor requirement
        if (lt.requires_guarantor) {
            frm.set_df_property("guarantor", "reqd", 1);
            frm.set_df_property("guarantor", "description", "Required for this loan type");
            frm.set_df_property("guarantor_consent", "reqd", 1);
        } else {
            frm.set_df_property("guarantor", "reqd", 0);
            frm.set_df_property("guarantor", "description", "Optional");
            frm.set_df_property("guarantor_consent", "reqd", 0);
        }

        _recompute_and_update_schedule(frm);
    });
}


// ── Recompute and update schedule ────────────────────────────────────

function _recompute_and_update_schedule(frm) {
    if (!frm.doc.principal_amount || !frm.doc.tenure_months || !frm.doc.loan_type) {
        return;
    }
    
    // First recompute the loan figures
    frappe.call({
        method: "frappe.client.get",
        args: {
            doctype: "Employee Loan Type",
            name: frm.doc.loan_type
        },
        callback: function(r) {
            if (r.message) {
                let lt = r.message;
                
                // Calculate EMI
                let P = frm.doc.principal_amount;
                let n = frm.doc.tenure_months;
                let annual_rate = lt.annual_interest_rate || 0;
                let r_rate = annual_rate / 100 / 12;
                
                let monthly, total;
                
                if (lt.is_interest_free || !annual_rate) {
                    monthly = Math.round((P / n) * 100) / 100;
                    total = P;
                } else {
                    let factor = Math.pow(1 + r_rate, n);
                    monthly = Math.round((P * r_rate * factor / (factor - 1)) * 100) / 100;
                    total = Math.round(monthly * n * 100) / 100;
                }
                
                frm.set_value("monthly_deduction", monthly);
                frm.set_value("total_repayable", total);
                
                // Update schedule
                _populate_repayment_schedule(frm);
                
                // Trigger dashboard refresh
                _render_dashboard(frm);
            }
        }
    });
}


// ── Populate Repayment Schedule Table ─────────────────────────────────

function _populate_repayment_schedule(frm) {
    // Only populate if we have the required fields
    if (!frm.doc.principal_amount || !frm.doc.tenure_months || !frm.doc.loan_type) {
        return;
    }
    
    // Clear existing schedule
    frm.clear_table("repayment_schedule");
    
    frappe.call({
        method: "frappe.client.get",
        args: {
            doctype: "Employee Loan Type",
            name: frm.doc.loan_type
        },
        callback: function(r) {
            if (r.message) {
                let lt = r.message;
                let P = frm.doc.principal_amount;
                let n = frm.doc.tenure_months;
                let annual_rate = lt.annual_interest_rate || 0;
                let r_rate = annual_rate / 100 / 12;
                let is_free = lt.is_interest_free || !annual_rate;
                
                // Use first deduction date or default to next month
                let start_date = frm.doc.first_deduction_date || 
                    frappe.datetime.add_months(frappe.datetime.get_today(), 1).substring(0, 7) + '-01';
                
                let balance = P;
                
                // Calculate monthly EMI
                let monthly;
                if (is_free) {
                    monthly = Math.round((P / n) * 100) / 100;
                } else {
                    let factor = Math.pow(1 + r_rate, n);
                    monthly = Math.round((P * r_rate * factor / (factor - 1)) * 100) / 100;
                }
                
                // Generate each installment
                for (let i = 1; i <= n; i++) {
                    let due_date = frappe.datetime.add_months(start_date, i - 1);
                    
                    let principal_paid, interest, monthly_amount;
                    
                    if (is_free) {
                        principal_paid = Math.round((P / n) * 100) / 100;
                        interest = 0;
                        monthly_amount = principal_paid;
                    } else {
                        interest = Math.round(balance * r_rate * 100) / 100;
                        principal_paid = Math.round((monthly - interest) * 100) / 100;
                        monthly_amount = monthly;
                    }
                    
                    // Last installment adjustment to absorb rounding
                    if (i === n) {
                        principal_paid = Math.round(balance * 100) / 100;
                        if (!is_free) {
                            interest = Math.round((monthly - principal_paid) * 100) / 100;
                            monthly_amount = Math.round((principal_paid + interest) * 100) / 100;
                        }
                    }
                    
                    // Update balance for next iteration
                    balance = Math.max(Math.round((balance - principal_paid) * 100) / 100, 0);
                    
                    // Determine status based on document status and actual payments
                    let status = "Pending";
                    if (frm.doc.docstatus === 1) {
                        // For submitted documents, check if this installment should be marked as paid
                        // This would be updated by repayment entries
                        status = "Pending";
                    }
                    
                    // Add row to the table
                    let child_row = frm.add_child("repayment_schedule");
                    child_row.installment_no = i;
                    child_row.payment_date = due_date;
                    child_row.principal = principal_paid;
                    child_row.interest = interest;
                    child_row.monthly_amount = monthly_amount;
                    child_row.balance = balance;
                    child_row.status = status;
                    child_row.salary_slip = ""; // Will be populated when paid via payroll
                }
                
                // Refresh the table field
                frm.refresh_field("repayment_schedule");
                
                // Show summary message for draft documents
                if (frm.doc.docstatus === 0) {
                    frappe.show_alert({
                        message: __(`Repayment schedule generated with ${n} installments`),
                        indicator: "green"
                    });
                }
            }
        }
    });
}


// ── Update Installment Status ─────────────────────────────────────────

function _update_installment_status(frm, installment_no, status, salary_slip = null) {
    let schedule = frm.doc.repayment_schedule;
    if (!schedule || !schedule.length) return;
    
    let updated = false;
    $.each(schedule, function(i, row) {
        if (row.installment_no == installment_no) {
            row.status = status;
            if (salary_slip) {
                row.salary_slip = salary_slip;
            }
            updated = true;
            return false; // break the loop
        }
    });
    
    if (updated) {
        frm.refresh_field("repayment_schedule");
        
        // Update loan summary
        let paid_count = schedule.filter(row => row.status === "Paid").length;
        frm.set_value("installments_paid", paid_count);
        
        // Calculate total paid amount
        let total_paid = schedule
            .filter(row => row.status === "Paid")
            .reduce((sum, row) => sum + row.monthly_amount, 0);
        frm.set_value("total_amount_paid", total_paid);
        
        // Update outstanding principal
        let last_row = schedule[schedule.length - 1];
        if (last_row && last_row.status === "Paid") {
            frm.set_value("outstanding_principal", 0);
            frm.set_value("status", "Closed");
        } else {
            let pending_row = schedule.find(row => row.status === "Pending");
            if (pending_row) {
                frm.set_value("outstanding_principal", pending_row.balance);
            }
        }
    }
}


// ── Dashboard Renderer ────────────────────────────────────────────────

function _render_dashboard(frm) {
    if (frm.is_new() || !frm.doc.principal_amount) {
        $(frm.fields_dict.dashboard_detail.wrapper).html(`
            <div class="alert alert-info" style="margin: 10px 0;">
                <i class="fa fa-info-circle"></i>
                Enter loan details to view dashboard
            </div>
        `);
        return;
    }

    const schedule = frm.doc.repayment_schedule || [];
    const paid_installments = schedule.filter(row => row.status === "Paid").length;
    const total_installments = schedule.length;
    const next_payment = schedule.find(row => row.status === "Pending");

    const html = `
        <div style="padding: 15px 0;">
            <!-- Status Alert -->
            ${_render_status_alert(frm)}
            
            <!-- Header Stats Cards -->
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px;">
                ${_render_stat_card("Principal Amount", frm.doc.principal_amount, "#2c3e50", "₦")}
                ${_render_stat_card("Outstanding", frm.doc.outstanding_principal, 
                    _get_outstanding_color(frm.doc.outstanding_principal, frm.doc.status), "₦")}
                ${_render_stat_card("Monthly Deduction", frm.doc.monthly_deduction, "#3498db", "₦")}
                ${_render_stat_card("Total Repayable", frm.doc.total_repayable, "#9b59b6", "₦")}
            </div>

            <!-- Progress & Timeline Section -->
            <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 15px; margin-bottom: 20px;">
                <!-- Left: Repayment Progress -->
                <div style="background: #f8f9fa; border-radius: 8px; padding: 15px; border: 1px solid #e9ecef;">
                    <h6 style="margin: 0 0 15px 0; color: #2c3e50; font-weight: 600; border-bottom: 1px solid #dee2e6; padding-bottom: 8px;">
                        <i class="fa fa-chart-line" style="margin-right: 8px;"></i>Repayment Progress
                    </h6>
                    ${_render_repayment_progress(frm, paid_installments, total_installments, next_payment)}
                </div>

                <!-- Right: Loan Status Timeline -->
                <div style="background: #f8f9fa; border-radius: 8px; padding: 15px; border: 1px solid #e9ecef;">
                    <h6 style="margin: 0 0 15px 0; color: #2c3e50; font-weight: 600; border-bottom: 1px solid #dee2e6; padding-bottom: 8px;">
                        <i class="fa fa-clock-o" style="margin-right: 8px;"></i>Loan Timeline
                    </h6>
                    ${_render_timeline(frm)}
                </div>
            </div>

            <!-- Schedule Summary -->
            <div style="background: #f8f9fa; border-radius: 8px; padding: 15px; margin-bottom: 20px; border: 1px solid #e9ecef;">
                <h6 style="margin: 0 0 15px 0; color: #2c3e50; font-weight: 600; border-bottom: 1px solid #dee2e6; padding-bottom: 8px;">
                    <i class="fa fa-calendar" style="margin-right: 8px;"></i>Installment Summary
                </h6>
                ${_render_installment_summary(frm, schedule)}
            </div>

            <!-- Quick Info Row -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                <div style="background: #f8f9fa; border-radius: 8px; padding: 15px; border: 1px solid #e9ecef;">
                    <h6 style="margin: 0 0 15px 0; color: #2c3e50; font-weight: 600; border-bottom: 1px solid #dee2e6; padding-bottom: 8px;">
                        <i class="fa fa-users" style="margin-right: 8px;"></i>Loan Details
                    </h6>
                    ${_render_loan_details(frm)}
                </div>
                
                <div style="background: #f8f9fa; border-radius: 8px; padding: 15px; border: 1px solid #e9ecef;">
                    <h6 style="margin: 0 0 15px 0; color: #2c3e50; font-weight: 600; border-bottom: 1px solid #dee2e6; padding-bottom: 8px;">
                        <i class="fa fa-check-circle" style="margin-right: 8px;"></i>Approval Status
                    </h6>
                    ${_render_approval_status(frm)}
                </div>
            </div>
            
            <!-- Installment Table Preview -->
            <div style="margin-top: 20px; background: #f8f9fa; border-radius: 8px; padding: 15px; border: 1px solid #e9ecef;">
                <h6 style="margin: 0 0 15px 0; color: #2c3e50; font-weight: 600; border-bottom: 1px solid #dee2e6; padding-bottom: 8px;">
                    <i class="fa fa-table" style="margin-right: 8px;"></i>Repayment Schedule (First 5 Installments)
                </h6>
                ${_render_schedule_preview_table(frm, schedule)}
            </div>
        </div>
    `;

    $(frm.fields_dict.dashboard_detail.wrapper).html(html);
}

// Helper function to format numbers
function format_number(num) {
    if (num === undefined || num === null) return '0.00';
    return num.toLocaleString("en-NG", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function _render_status_alert(frm) {
    if (frm.doc.status === "Rejected") {
        return `
            <div class="alert alert-danger" style="margin-bottom: 15px;">
                <i class="fa fa-exclamation-triangle"></i>
                <strong>Rejected:</strong> ${frm.doc.rejection_reason || 'No reason provided'}
            </div>
        `;
    }
    
    if (frm.doc.status === "Closed") {
        return `
            <div class="alert alert-success" style="margin-bottom: 15px;">
                <i class="fa fa-check-circle"></i>
                <strong>Loan Fully Repaid and Closed</strong>
            </div>
        `;
    }
    
    return "";
}

function _get_outstanding_color(outstanding, status) {
    if (status === "Closed") return "#27ae60";
    if (!outstanding || outstanding === 0) return "#27ae60";
    if (outstanding > 1000000) return "#e74c3c";
    if (outstanding > 500000) return "#f39c12";
    return "#3498db";
}

function _render_stat_card(label, value, color, prefix = "") {
    if (value === undefined || value === null) value = 0;
    
    return `
        <div style="background: ${color}; border-radius: 8px; padding: 15px; color: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <div style="font-size: 12px; opacity: 0.9; margin-bottom: 5px;">${label}</div>
            <div style="font-size: 20px; font-weight: 600;">
                ${prefix}${format_number(value)}
            </div>
        </div>
    `;
}

function _render_repayment_progress(frm, paid, total, next_payment) {
    if (!["Active", "Disbursed", "Closed"].includes(frm.doc.status)) {
        return `
            <div style="text-align: center; padding: 20px; color: #7f8c8d;">
                <i class="fa fa-hourglass-start" style="font-size: 24px; margin-bottom: 10px; display: block;"></i>
                <p>Loan not yet active</p>
                <p style="font-size: 11px;">Current status: ${frm.doc.status}</p>
            </div>
        `;
    }

    const pct = total > 0 ? Math.min(Math.round((paid / total) * 100), 100) : 0;

    return `
        <div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <span style="font-size: 13px;">${paid} of ${total} installments paid</span>
                <span style="font-size: 13px; font-weight: 600;">${pct}%</span>
            </div>
            <div style="height: 10px; background: #e9ecef; border-radius: 5px; overflow: hidden; margin-bottom: 15px;">
                <div style="width: ${pct}%; height: 10px; background: linear-gradient(90deg, #3498db, #2ecc71); 
                            border-radius: 5px; transition: width 0.5s;"></div>
            </div>
            
            ${next_payment ? `
                <div style="background: white; border-radius: 6px; padding: 10px; margin-top: 10px; border: 1px solid #dee2e6;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                        <span style="color: #7f8c8d;">Next Payment:</span>
                        <span style="font-weight: 600;">₦${format_number(next_payment.monthly_amount)}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #7f8c8d;">Due Date:</span>
                        <span>${frappe.datetime.str_to_user(next_payment.payment_date)}</span>
                    </div>
                </div>
            ` : paid === total ? `
                <div style="background: #d4edda; color: #155724; border-radius: 6px; padding: 10px; text-align: center; border: 1px solid #c3e6cb;">
                    <i class="fa fa-check-circle" style="margin-right: 5px;"></i> Loan Fully Repaid
                </div>
            ` : ""}
        </div>
    `;
}

function _render_timeline(frm) {
    const timeline = [];
    
    if (frm.doc.application_date) {
        timeline.push({
            date: frm.doc.application_date,
            event: "Application Submitted",
            status: "completed"
        });
    }
    
    if (frm.doc.hr_review_date) {
        timeline.push({
            date: frm.doc.hr_review_date.split(" ")[0],
            event: "HR Review",
            status: "completed"
        });
    }
    
    if (frm.doc.manager_approval_date) {
        timeline.push({
            date: frm.doc.manager_approval_date.split(" ")[0],
            event: "Manager Approval",
            status: "completed"
        });
    }
    
    if (frm.doc.finance_approval_date) {
        timeline.push({
            date: frm.doc.finance_approval_date.split(" ")[0],
            event: "Finance Approval",
            status: "completed"
        });
    }
    
    if (frm.doc.disbursement_date) {
        timeline.push({
            date: frm.doc.disbursement_date,
            event: "Disbursed",
            status: "completed"
        });
    }
    
    if (timeline.length === 0) {
        return `
            <div style="text-align: center; padding: 20px; color: #7f8c8d;">
                <i class="fa fa-clock-o" style="font-size: 24px; margin-bottom: 10px; display: block;"></i>
                <p>No timeline events yet</p>
            </div>
        `;
    }
    
    return `
        <div style="max-height: 200px; overflow-y: auto;">
            ${timeline.map(item => `
                <div style="display: flex; align-items: flex-start; margin-bottom: 10px;">
                    <div style="width: 10px; height: 10px; background: #27ae60; border-radius: 50%; margin-right: 10px; margin-top: 3px;"></div>
                    <div style="flex: 1;">
                        <div style="font-size: 11px; color: #7f8c8d;">${frappe.datetime.str_to_user(item.date)}</div>
                        <div style="font-size: 13px;">${item.event}</div>
                    </div>
                </div>
            `).join("")}
            
            <div style="display: flex; align-items: flex-start;">
                <div style="width: 10px; height: 10px; background: #3498db; border-radius: 50%; margin-right: 10px; margin-top: 3px;"></div>
                <div style="flex: 1;">
                    <div style="font-size: 11px; color: #7f8c8d;">Current</div>
                    <div style="font-size: 13px; font-weight: 500;">${frm.doc.status}</div>
                </div>
            </div>
        </div>
    `;
}

function _render_installment_summary(frm, schedule) {
    const today = new Date();
    const stats = {
        total: schedule.length,
        paid: schedule.filter(row => row.status === "Paid").length,
        pending: schedule.filter(row => row.status === "Pending").length,
        overdue: schedule.filter(row => {
            if (row.status !== "Pending") return false;
            const due_date = new Date(row.payment_date);
            return due_date < today;
        }).length
    };
    
    return `
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;">
            <div style="text-align: center; padding: 10px; background: white; border-radius: 6px;">
                <div style="font-size: 20px; font-weight: 600; color: #3498db;">${stats.total}</div>
                <div style="font-size: 11px; color: #7f8c8d;">Total</div>
            </div>
            <div style="text-align: center; padding: 10px; background: white; border-radius: 6px;">
                <div style="font-size: 20px; font-weight: 600; color: #27ae60;">${stats.paid}</div>
                <div style="font-size: 11px; color: #7f8c8d;">Paid</div>
            </div>
            <div style="text-align: center; padding: 10px; background: white; border-radius: 6px;">
                <div style="font-size: 20px; font-weight: 600; color: #f39c12;">${stats.pending}</div>
                <div style="font-size: 11px; color: #7f8c8d;">Pending</div>
            </div>
            <div style="text-align: center; padding: 10px; background: white; border-radius: 6px;">
                <div style="font-size: 20px; font-weight: 600; color: ${stats.overdue > 0 ? '#e74c3c' : '#95a5a6'};">${stats.overdue}</div>
                <div style="font-size: 11px; color: #7f8c8d;">Overdue</div>
            </div>
        </div>
    `;
}

function _render_schedule_preview_table(frm, schedule) {
    if (!schedule || schedule.length === 0) {
        return `
            <div style="text-align: center; padding: 20px; color: #7f8c8d;">
                <i class="fa fa-table" style="font-size: 24px; margin-bottom: 10px; display: block;"></i>
                <p>No schedule generated yet</p>
            </div>
        `;
    }
    
    let rows = '';
    const preview_count = Math.min(schedule.length, 5);
    
    for (let i = 0; i < preview_count; i++) {
        let row = schedule[i];
        let status_color = row.status === "Paid" ? "#27ae60" : 
                          row.status === "Overdue" ? "#e74c3c" : "#3498db";
        
        rows += `
            <tr>
                <td style="padding:5px; border:1px solid #dee2e6;">${row.installment_no}</td>
                <td style="padding:5px; border:1px solid #dee2e6;">${frappe.datetime.str_to_user(row.payment_date)}</td>
                <td style="padding:5px; border:1px solid #dee2e6; text-align:right;">₦${format_number(row.principal)}</td>
                <td style="padding:5px; border:1px solid #dee2e6; text-align:right;">₦${format_number(row.interest)}</td>
                <td style="padding:5px; border:1px solid #dee2e6; text-align:right;">₦${format_number(row.monthly_amount)}</td>
                <td style="padding:5px; border:1px solid #dee2e6; text-align:right;">₦${format_number(row.balance)}</td>
                <td style="padding:5px; border:1px solid #dee2e6;">
                    <span style="color: ${status_color};">${row.status}</span>
                </td>
                <td style="padding:5px; border:1px solid #dee2e6;">${row.salary_slip || '-'}</td>
            </tr>
        `;
    }
    
    return `
        <div style="overflow-x: auto;">
            <table style="width:100%; border-collapse:collapse; font-size:12px;">
                <thead>
                    <tr style="background:#f0f0f0;">
                        <th style="padding:5px; border:1px solid #dee2e6;">#</th>
                        <th style="padding:5px; border:1px solid #dee2e6;">Due Date</th>
                        <th style="padding:5px; border:1px solid #dee2e6; text-align:right;">Principal</th>
                        <th style="padding:5px; border:1px solid #dee2e6; text-align:right;">Interest</th>
                        <th style="padding:5px; border:1px solid #dee2e6; text-align:right;">Total</th>
                        <th style="padding:5px; border:1px solid #dee2e6; text-align:right;">Balance</th>
                        <th style="padding:5px; border:1px solid #dee2e6;">Status</th>
                        <th style="padding:5px; border:1px solid #dee2e6;">Salary Slip</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows}
                </tbody>
            </table>
            ${schedule.length > 5 ? `
                <p style="margin-top: 10px; font-size: 11px; color: #6c757d; text-align: center;">
                    <i class="fa fa-ellipsis-h"></i> 
                    Showing first 5 of ${schedule.length} installments. 
                    <a href="#" onclick="cur_frm.trigger('show_full_schedule'); return false;">View Full Schedule</a>
                </p>
            ` : ''}
        </div>
    `;
}

function _render_loan_details(frm) {
    return `
        <table style="width: 100%; font-size: 13px;">
            <tr>
                <td style="padding: 5px 0; color: #7f8c8d;">Employee:</td>
                <td style="padding: 5px 0; font-weight: 500;">${frm.doc.employee_name || 'Not set'}</td>
            </tr>
            <tr>
                <td style="padding: 5px 0; color: #7f8c8d;">Department:</td>
                <td style="padding: 5px 0;">${frm.doc.department || 'Not set'}</td>
            </tr>
            <tr>
                <td style="padding: 5px 0; color: #7f8c8d;">Loan Type:</td>
                <td style="padding: 5px 0;">${frm.doc.loan_type || 'Not set'}</td>
            </tr>
            <tr>
                <td style="padding: 5px 0; color: #7f8c8d;">Interest Rate:</td>
                <td style="padding: 5px 0;">${frm.doc.interest_rate || 0}% p.a.</td>
            </tr>
            <tr>
                <td style="padding: 5px 0; color: #7f8c8d;">First Deduction:</td>
                <td style="padding: 5px 0;">${frm.doc.first_deduction_date ? frappe.datetime.str_to_user(frm.doc.first_deduction_date) : 'Not set'}</td>
            </tr>
            <tr>
                <td style="padding: 5px 0; color: #7f8c8d;">Guarantor:</td>
                <td style="padding: 5px 0;">${frm.doc.guarantor_name || 'None'}</td>
            </tr>
        </table>
    `;
}

function _render_approval_status(frm) {
    const approvals = [
        { label: "HR Review", user: frm.doc.hr_reviewer, date: frm.doc.hr_review_date },
        { label: "Manager Approval", user: frm.doc.manager_approver, date: frm.doc.manager_approval_date },
        { label: "Finance Approval", user: frm.doc.finance_approver, date: frm.doc.finance_approval_date }
    ];
    
    return `
        <div>
            ${approvals.map(approval => `
                <div style="margin-bottom: 12px; padding: 8px; background: white; border-radius: 4px; border: 1px solid #e9ecef;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                        <span style="font-weight: 500;">${approval.label}</span>
                        ${approval.user ? 
                            '<span style="color: #27ae60;"><i class="fa fa-check-circle"></i> Completed</span>' : 
                            '<span style="color: #95a5a6;"><i class="fa fa-clock-o"></i> Pending</span>'
                        }
                    </div>
                    ${approval.user ? `
                        <div style="font-size: 11px; color: #7f8c8d;">
                            ${approval.user} • ${approval.date ? frappe.datetime.str_to_user(approval.date.split(" ")[0]) : ''}
                        </div>
                    ` : ''}
                </div>
            `).join("")}
        </div>
    `;
}


// ── Action buttons ────────────────────────────────────────────────────

function _add_action_buttons(frm) {
    if (frm.is_new()) return;

    // Clear existing custom buttons
    frm.clear_custom_buttons();

    // ── HR: initiate review ──────────────────────────────────────────
    if (frappe.user.has_role(["HR Manager", "System Manager"])) {

        if (frm.doc.status === "Draft") {
            frm.add_custom_button(__("Start HR Review"), () => {
                _set_status(frm, "Pending HR Review", {
                    hr_reviewer: frappe.session.user,
                    hr_review_date: frappe.datetime.now_datetime(),
                });
            }, __("Actions")).addClass("btn-primary");
        }

        if (frm.doc.status === "Pending HR Review") {
            frm.add_custom_button(__("Pass to Manager"), () => {
                _set_status(frm, "Pending Manager Approval", {
                    hr_reviewer: frappe.session.user,
                    hr_review_date: frappe.datetime.now_datetime(),
                });
            }, __("Actions")).addClass("btn-primary");

            frm.add_custom_button(__("Reject"), () => _reject_loan(frm), __("Actions"));
        }
    }

    // ── Manager approval ─────────────────────────────────────────────
    if (frappe.user.has_role(["Department Manager", "HR Manager", "System Manager"])) {
        if (frm.doc.status === "Pending Manager Approval") {
            frm.add_custom_button(__("Approve — Send to Finance"), () => {
                _set_status(frm, "Pending Finance Approval", {
                    manager_approver: frappe.session.user,
                    manager_approval_date: frappe.datetime.now_datetime(),
                });
            }, __("Actions")).addClass("btn-primary");

            frm.add_custom_button(__("Reject"), () => _reject_loan(frm), __("Actions"));
        }
    }

    // ── Finance approval ─────────────────────────────────────────────
    if (frappe.user.has_role(["Accounts Manager", "System Manager"])) {
        if (frm.doc.status === "Pending Finance Approval") {
            frm.add_custom_button(__("Approve Loan"), () => {
                _set_status(frm, "Approved", {
                    finance_approver: frappe.session.user,
                    finance_approval_date: frappe.datetime.now_datetime(),
                });
            }, __("Actions")).addClass("btn-primary");

            frm.add_custom_button(__("Reject"), () => _reject_loan(frm), __("Actions"));
        }
    }

    // ── Disburse (submit) ────────────────────────────────────────────
    if (frm.doc.status === "Approved" && frm.doc.docstatus === 0) {
        frm.add_custom_button(__("Disburse Loan"), () => {
            frappe.confirm(
                __(`Disburse <strong>₦${format_number(frm.doc.principal_amount || 0)}</strong> to <strong>${frm.doc.employee_name}</strong>?<br>A journal entry and repayment schedule will be created.`),
                () => frm.savesubmit().then(() => frm.reload_doc())
            );
        }, __("Actions")).addClass("btn-primary");
    }

    // ── Manual repayment entry ───────────────────────────────────────
    if (["Active", "Disbursed"].includes(frm.doc.status) && frm.doc.docstatus === 1) {
        frm.add_custom_button(__("Record Repayment"), () => {
            frappe.new_doc("Loan Repayment Entry", { 
                loan: frm.doc.name,
                employee: frm.doc.employee,
                employee_name: frm.doc.employee_name
            });
        }, __("Tools"));
    }

    // ── View Repayment Entries ───────────────────────────────────────
    if (frm.doc.docstatus === 1) {
        frm.add_custom_button(__("View Repayments"), () => {
            frappe.set_route("List", "Loan Repayment Entry", {
                loan: frm.doc.name
            });
        }, __("Tools"));
    }

    // ── Regenerate Schedule ──────────────────────────────────────────
    if (frm.doc.docstatus === 0 && frm.doc.principal_amount && frm.doc.tenure_months) {
        frm.add_custom_button(__("Regenerate Schedule"), () => {
            _populate_repayment_schedule(frm);
        }, __("Tools"));
    }

    // ── Loan statement ───────────────────────────────────────────────
    if (!frm.is_new() && frm.doc.status !== "Draft") {
        frm.add_custom_button(__("Loan Statement"), () => {
            _show_loan_statement(frm);
        }, __("Reports"));
    }
    
    // ── Show Full Schedule ───────────────────────────────────────────
    if (frm.doc.repayment_schedule && frm.doc.repayment_schedule.length > 0) {
        frm.add_custom_button(__("Full Schedule"), () => {
            _show_loan_statement(frm);
        }, __("Reports"));
    }
}


// ── Helpers ───────────────────────────────────────────────────────────

function _set_status(frm, new_status, extra_fields = {}) {
    frappe.call({
        method: "frappe.client.set_value",
        args: {
            doctype: "Employee Loan Application",
            name: frm.doc.name,
            fieldname: { status: new_status, ...extra_fields },
        },
        callback: function(r) {
            if (!r.exc) {
                frappe.show_alert({
                    message: __(`Status changed to ${new_status}`),
                    indicator: "green"
                });
                frm.reload_doc();
            }
        }
    });
}


function _reject_loan(frm) {
    frappe.prompt({
        label: __("Rejection Reason"),
        fieldtype: "Small Text",
        reqd: 1,
        fieldname: "reason"
    }, (values) => {
        frappe.call({
            method: "frappe.client.set_value",
            args: {
                doctype: "Employee Loan Application",
                name: frm.doc.name,
                fieldname: { 
                    status: "Rejected", 
                    rejection_reason: values.reason 
                },
            },
            callback: function(r) {
                if (!r.exc) {
                    frappe.show_alert({
                        message: __("Loan rejected"),
                        indicator: "red"
                    });
                    frm.reload_doc();
                }
            }
        });
    }, __("Reject Loan Application"), __("Reject"));
}


function _show_loan_statement(frm) {
    if (!frm.doc.repayment_schedule || !frm.doc.repayment_schedule.length) {
        frappe.msgprint({
            title: __("No Data"),
            message: __("No repayment schedule found for this loan."),
            indicator: "orange"
        });
        return;
    }

    const schedule = frm.doc.repayment_schedule;
    
    let rows = '';
    schedule.forEach(row => {
        let status_color = row.status === "Paid" ? "green" : 
                          row.status === "Overdue" ? "red" : "blue";
        
        rows += `
            <tr style="border-bottom:1px solid var(--border-color)">
                <td style="padding:7px 10px;font-size:12px">${row.installment_no}</td>
                <td style="padding:7px 10px;font-size:12px">${frappe.datetime.str_to_user(row.payment_date)}</td>
                <td style="padding:7px 10px;font-size:12px;text-align:right">
                    ₦${format_number(row.principal)}</td>
                <td style="padding:7px 10px;font-size:12px;text-align:right;
                           color:${row.interest > 0 ? '#BA7517' : 'inherit'}">
                    ₦${format_number(row.interest)}</td>
                <td style="padding:7px 10px;font-size:12px;text-align:right;
                           font-weight:500">
                    ₦${format_number(row.monthly_amount)}</td>
                <td style="padding:7px 10px;font-size:12px;text-align:right">
                    ₦${format_number(row.balance)}</td>
                <td style="padding:7px 10px;font-size:12px">
                    <span class="indicator ${status_color}">${row.status}</span>
                </td>
                <td style="padding:7px 10px;font-size:12px">${row.salary_slip || '-'}</td>
            </tr>
        `;
    });

    frappe.msgprint({
        title:   __(`Loan Statement — ${frm.doc.employee_name}`),
        message: `
            <div style="overflow-x:auto; max-height: 400px; overflow-y: auto;">
                <table style="width:100%; border-collapse:collapse;">
                    <thead style="background:var(--control-bg); position: sticky; top: 0;">
                        <tr>
                            <th style="padding:8px 10px;font-size:11px;text-align:left">#</th>
                            <th style="padding:8px 10px;font-size:11px;text-align:left">Date</th>
                            <th style="padding:8px 10px;font-size:11px;text-align:right">Principal</th>
                            <th style="padding:8px 10px;font-size:11px;text-align:right">Interest</th>
                            <th style="padding:8px 10px;font-size:11px;text-align:right">Total</th>
                            <th style="padding:8px 10px;font-size:11px;text-align:right">Balance</th>
                            <th style="padding:8px 10px;font-size:11px;text-align:left">Status</th>
                            <th style="padding:8px 10px;font-size:11px;text-align:left">Salary Slip</th>
                        </tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
            
            <div style="margin-top: 15px; padding: 10px; background: #f8f9fa; border-radius: 4px;">
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;">
                    <div>
                        <span style="color: #7f8c8d; font-size: 11px;">Total Paid:</span>
                        <span style="font-weight: 500; display: block;">₦${format_number(frm.doc.total_amount_paid || 0)}</span>
                    </div>
                    <div>
                        <span style="color: #7f8c8d; font-size: 11px;">Outstanding:</span>
                        <span style="font-weight: 500; display: block;">₦${format_number(frm.doc.outstanding_principal || 0)}</span>
                    </div>
                    <div>
                        <span style="color: #7f8c8d; font-size: 11px;">Installments:</span>
                        <span style="font-weight: 500; display: block;">${frm.doc.installments_paid || 0} / ${frm.doc.tenure_months || 0}</span>
                    </div>
                </div>
            </div>
        `,
        wide: true
    });
}

// Custom trigger for showing full schedule
frappe.ui.form.on("Employee Loan Application", {
    show_full_schedule: function(frm) {
        _show_loan_statement(frm);
    }
});