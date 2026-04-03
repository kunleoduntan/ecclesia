// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt

// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

frappe.ui.form.on('Fixed Asset Insurance', {
    refresh: function(frm) {
        add_insurance_buttons(frm);
        set_status_indicators(frm);
        show_coverage_alerts(frm);
        calculate_metrics(frm);
        setup_filters(frm);
    },
    
    onload: function(frm) {
        setup_filters(frm);
        
        if (frm.is_new() && !frm.doc.policy_status) {
            frm.set_value('policy_status', 'Draft');
        }
        
        if (frm.is_new() && !frm.doc.premium_frequency) {
            frm.set_value('premium_frequency', 'Annual');
        }
    },
    
    company: function(frm) {
        frm.set_value('asset', '');
    },
    
    asset: function(frm) {
        if (frm.doc.asset) {
            fetch_asset_details(frm);
        } else {
            clear_asset_fields(frm);
        }
    },
    
    policy_start_date: function(frm) {
        calculate_policy_end_date(frm);
        calculate_renewal_date(frm);
        calculate_next_payment_date(frm);
    },
    
    policy_term_months: function(frm) {
        calculate_policy_end_date(frm);
    },
    
    policy_end_date: function(frm) {
        calculate_renewal_date(frm);
        calculate_policy_term(frm);
    },
    
    sum_insured: function(frm) {
        validate_coverage(frm);
        calculate_coverage_percentage(frm);
        suggest_premium(frm);
    },
    
    asset_value: function(frm) {
        validate_coverage(frm);
        calculate_coverage_percentage(frm);
    },
    
    insurance_type: function(frm) {
        suggest_premium(frm);
        update_coverage_description(frm);
    },
    
    premium_amount: function(frm) {
        calculate_installment_amount(frm);
        calculate_total_premium(frm);
    },
    
    premium_frequency: function(frm) {
        calculate_installment_amount(frm);
        calculate_number_of_installments(frm);
        toggle_installment_fields(frm);
    },
    
    number_of_installments: function(frm) {
        calculate_installment_amount(frm);
    },
    
    policy_status: function(frm) {
        set_status_indicators(frm);
    }
});

function add_insurance_buttons(frm) {
    if (frm.doc.docstatus === 1) {
        // Renew Policy
        if (['Active', 'Expiring Soon'].includes(frm.doc.policy_status)) {
            frm.add_custom_button(__('Renew Policy'), function() {
                renew_policy(frm);
            }, __('Actions')).addClass('btn-success');
        }
        
        // File Claim
        if (frm.doc.policy_status === 'Active') {
            frm.add_custom_button(__('File Claim'), function() {
                file_claim_dialog(frm);
            }, __('Actions'));
        }
        
        // Cancel Policy
        if (['Active', 'Expiring Soon'].includes(frm.doc.policy_status)) {
            frm.add_custom_button(__('Cancel Policy'), function() {
                cancel_policy_dialog(frm);
            }, __('Actions'));
        }
        
        // Payment Reminder
        if (frm.doc.premium_frequency !== 'Annual' && frm.doc.policy_status === 'Active') {
            frm.add_custom_button(__('Payment Reminder'), function() {
                create_payment_reminder(frm);
            }, __('Actions'));
        }
        
        // View Asset
        frm.add_custom_button(__('View Asset'), function() {
            frappe.set_route('Form', 'Fixed Asset', frm.doc.asset);
        }, __('View'));
    }
}

function set_status_indicators(frm) {
    const status_colors = {
        'Draft': 'gray',
        'Active': 'green',
        'Expiring Soon': 'orange',
        'Expired': 'red',
        'Cancelled': 'darkred',
        'Renewed': 'blue',
        'Not Started': 'purple'
    };
    
    if (frm.doc.policy_status) {
        frm.page.set_indicator(frm.doc.policy_status, status_colors[frm.doc.policy_status] || 'gray');
        
        // Add expiry warning
        if (frm.doc.policy_status === 'Expiring Soon' && frm.doc.days_to_expiry) {
            frm.dashboard.add_comment(
                __('⚠️ Policy expiring in {0} days. Consider renewal.', [frm.doc.days_to_expiry]),
                'orange',
                true
            );
        }
    }
}

function show_coverage_alerts(frm) {
    if (!frm.doc.docstatus || !frm.doc.sum_insured || !frm.doc.asset_value) return;
    
    let coverage_pct = (flt(frm.doc.sum_insured) / flt(frm.doc.asset_value)) * 100;
    
    frm.dashboard.clear_headline();
    
    if (coverage_pct < 80) {
        frm.dashboard.add_indicator(
            __('Coverage: {0}% - Under-insured ⚠️', [coverage_pct.toFixed(1)]), 
            'orange'
        );
    } else if (coverage_pct > 120) {
        frm.dashboard.add_indicator(
            __('Coverage: {0}% - Over-insured ℹ️', [coverage_pct.toFixed(1)]), 
            'yellow'
        );
    } else {
        frm.dashboard.add_indicator(
            __('Coverage: {0}% - Adequate ✓', [coverage_pct.toFixed(1)]), 
            'green'
        );
    }
}

function calculate_metrics(frm) {
    if (!frm.doc.docstatus) return;
    
    // Show total premium
    if (frm.doc.premium_amount) {
        frm.dashboard.add_indicator(
            __('Total Premium: {0}', [format_currency(frm.doc.premium_amount)]), 
            'blue'
        );
    }
    
    // Show claims summary
    if (frm.doc.insurance_claims && frm.doc.insurance_claims.length > 0) {
        let total_claims = 0;
        let settled_claims = 0;
        
        frm.doc.insurance_claims.forEach(claim => {
            total_claims += flt(claim.claim_amount);
            if (claim.claim_status === 'Settled') {
                settled_claims += flt(claim.approved_amount || 0);
            }
        });
        
        if (total_claims > 0) {
            frm.dashboard.add_indicator(
                __('Total Claims: {0}', [format_currency(total_claims)]), 
                'red'
            );
        }
        
        if (settled_claims > 0) {
            frm.dashboard.add_indicator(
                __('Settled Claims: {0}', [format_currency(settled_claims)]), 
                'green'
            );
        }
    }
}

function fetch_asset_details(frm) {
    if (!frm.doc.asset) return;
    
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.fixed_asset_insurance.fixed_asset_insurance.get_asset_details',
        args: {
            asset: frm.doc.asset
        },
        callback: function(r) {
            if (r.message) {
                frm.set_value('asset_code', r.message.asset_code);
                frm.set_value('asset_name', r.message.asset_name);
                frm.set_value('asset_category', r.message.asset_category);
                frm.set_value('asset_location', r.message.location);
                frm.set_value('asset_value', r.message.current_value);
                
                if (r.message.cost_center && !frm.doc.cost_center) {
                    frm.set_value('cost_center', r.message.cost_center);
                }
                
                // Auto-suggest sum insured (100% of asset value)
                if (!frm.doc.sum_insured && r.message.current_value) {
                    frm.set_value('sum_insured', r.message.current_value);
                }
                
                frappe.show_alert({
                    message: __('✓ Asset details loaded'),
                    indicator: 'green'
                });
            }
        }
    });
}

function clear_asset_fields(frm) {
    frm.set_value('asset_code', '');
    frm.set_value('asset_name', '');
    frm.set_value('asset_category', '');
    frm.set_value('asset_location', '');
    frm.set_value('asset_value', 0);
}

function calculate_policy_end_date(frm) {
    if (!frm.doc.policy_start_date || !frm.doc.policy_term_months) return;
    
    frappe.call({
        method: 'frappe.utils.add_months',
        args: {
            date: frm.doc.policy_start_date,
            months: frm.doc.policy_term_months
        },
        callback: function(r) {
            if (r.message) {
                frm.set_value('policy_end_date', r.message);
            }
        }
    });
}

function calculate_policy_term(frm) {
    if (!frm.doc.policy_start_date || !frm.doc.policy_end_date) return;
    
    let days = frappe.datetime.get_day_diff(frm.doc.policy_end_date, frm.doc.policy_start_date);
    let months = Math.round(days / 30);
    
    frm.set_value('policy_term_months', months);
}

function calculate_renewal_date(frm) {
    if (!frm.doc.policy_end_date) return;
    
    // Set renewal date 30 days before expiry
    let renewal_date = frappe.datetime.add_days(frm.doc.policy_end_date, -30);
    frm.set_value('renewal_date', renewal_date);
}

function calculate_next_payment_date(frm) {
    if (!frm.doc.policy_start_date || !frm.doc.premium_frequency) return;
    
    let frequency_months = {
        'Annual': 12,
        'Semi-Annual': 6,
        'Quarterly': 3,
        'Monthly': 1
    };
    
    let months = frequency_months[frm.doc.premium_frequency] || 12;
    
    frappe.call({
        method: 'frappe.utils.add_months',
        args: {
            date: frm.doc.policy_start_date,
            months: months
        },
        callback: function(r) {
            if (r.message && !frm.doc.next_payment_date) {
                frm.set_value('next_payment_date', r.message);
            }
        }
    });
}

function validate_coverage(frm) {
    if (!frm.doc.sum_insured || !frm.doc.asset_value) return;
    
    let coverage_pct = (flt(frm.doc.sum_insured) / flt(frm.doc.asset_value)) * 100;
    
    if (coverage_pct < 70) {
        frappe.msgprint({
            title: __('⚠️ Under-insurance Warning'),
            message: __('Sum insured is only {0}% of asset value. This may lead to claim rejections or partial settlements. Consider increasing coverage to at least 80%.', 
                [coverage_pct.toFixed(1)]),
            indicator: 'orange'
        });
    } else if (coverage_pct > 150) {
        frappe.msgprint({
            title: __('ℹ️ Over-insurance Notice'),
            message: __('Sum insured is {0}% of asset value. You are paying for more coverage than needed. Consider reducing to save on premiums.', 
                [coverage_pct.toFixed(1)]),
            indicator: 'yellow'
        });
    }
}

function calculate_coverage_percentage(frm) {
    if (!frm.doc.sum_insured || !frm.doc.asset_value) return;
    
    let coverage_pct = (flt(frm.doc.sum_insured) / flt(frm.doc.asset_value)) * 100;
    frm.set_value('coverage_percentage', coverage_pct);
}

function suggest_premium(frm) {
    if (!frm.doc.sum_insured || !frm.doc.insurance_type) return;
    
    // Premium rate suggestions based on insurance type
    let rate_map = {
        'Comprehensive': 0.005,    // 0.5% of sum insured
        'Fire': 0.002,             // 0.2%
        'Theft': 0.003,            // 0.3%
        'All Risk': 0.006,         // 0.6%
        'Specified Perils': 0.004, // 0.4%
        'Liability': 0.001         // 0.1%
    };
    
    let suggested_premium = flt(frm.doc.sum_insured) * (rate_map[frm.doc.insurance_type] || 0.003);
    
    if (!frm.doc.premium_amount || frm.doc.premium_amount === 0) {
        frm.set_df_property('premium_amount', 'description', 
            __('💡 Suggested premium: {0} (based on industry standards)', [format_currency(suggested_premium)]));
    }
}

function update_coverage_description(frm) {
    if (!frm.doc.insurance_type) return;
    
    let descriptions = {
        'Comprehensive': 'Comprehensive coverage typically includes: Fire, Theft, Natural Disasters, Accidental Damage, Third Party Liability',
        'Fire': 'Fire coverage includes damage from fire, lightning, and related perils',
        'Theft': 'Theft coverage protects against burglary, robbery, and theft',
        'All Risk': 'All Risk provides the broadest coverage against all perils except those specifically excluded',
        'Specified Perils': 'Coverage for specific named perils only',
        'Liability': 'Third-party liability coverage for damages to others'
    };
    
    if (descriptions[frm.doc.insurance_type]) {
        frm.set_df_property('coverage_description', 'description', __(descriptions[frm.doc.insurance_type]));
    }
}

function calculate_installment_amount(frm) {
    if (!frm.doc.premium_amount) return;
    
    calculate_number_of_installments(frm);
    
    if (frm.doc.number_of_installments && frm.doc.number_of_installments > 0) {
        let installment = flt(frm.doc.premium_amount) / flt(frm.doc.number_of_installments);
        frm.set_value('installment_amount', installment);
    }
}

function calculate_number_of_installments(frm) {
    if (!frm.doc.policy_term_months || !frm.doc.premium_frequency) return;
    
    let frequency_months = {
        'Annual': 12,
        'Semi-Annual': 6,
        'Quarterly': 3,
        'Monthly': 1
    };
    
    let months = frequency_months[frm.doc.premium_frequency] || 12;
    let installments = Math.max(1, Math.floor(flt(frm.doc.policy_term_months) / months));
    
    frm.set_value('number_of_installments', installments);
}

function calculate_total_premium(frm) {
    if (frm.doc.installment_amount && frm.doc.number_of_installments) {
        let total = flt(frm.doc.installment_amount) * flt(frm.doc.number_of_installments);
        
        if (Math.abs(total - flt(frm.doc.premium_amount)) > 0.01) {
            frm.set_value('premium_amount', total);
        }
    }
}

function toggle_installment_fields(frm) {
    let show = frm.doc.premium_frequency !== 'Annual';
    
    frm.toggle_display('number_of_installments', show);
    frm.toggle_display('installment_amount', show);
    frm.toggle_display('next_payment_date', show);
}

function renew_policy(frm) {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.fixed_asset_insurance.fixed_asset_insurance.renew_policy',
        args: {
            source_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                frappe.model.sync(r.message);
                frappe.set_route('Form', r.message.doctype, r.message.name);
                frappe.show_alert({
                    message: __('✓ Renewal policy created'),
                    indicator: 'green'
                }, 5);
            }
        }
    });
}

function cancel_policy_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Cancel Insurance Policy'),
        fields: [
            {
                fieldname: 'cancellation_reason',
                fieldtype: 'Small Text',
                label: __('Cancellation Reason'),
                reqd: 1
            },
            {
                fieldname: 'refund_amount',
                fieldtype: 'Currency',
                label: __('Refund Amount (if any)'),
                default: 0,
                description: __('Enter any refund amount from the insurer')
            }
        ],
        primary_action_label: __('Cancel Policy'),
        primary_action: function(values) {
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.fixed_asset_insurance.fixed_asset_insurance.cancel_policy',
                args: {
                    doc_name: frm.doc.name,
                    reason: values.cancellation_reason,
                    refund_amount: values.refund_amount
                },
                callback: function(r) {
                    if (r.message) {
                        frm.reload_doc();
                        frappe.show_alert({
                            message: __('Policy cancelled successfully'),
                            indicator: 'red'
                        });
                    }
                }
            });
            d.hide();
        }
    });
    d.show();
}

function file_claim_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __('File Insurance Claim'),
        fields: [
            {
                fieldname: 'claim_date',
                fieldtype: 'Date',
                label: __('Claim Date'),
                reqd: 1,
                default: frappe.datetime.get_today()
            },
            {
                fieldname: 'claim_number',
                fieldtype: 'Data',
                label: __('Claim Number'),
                reqd: 1,
                description: __('Reference number from insurance company')
            },
            {
                fieldname: 'claim_type',
                fieldtype: 'Select',
                label: __('Claim Type'),
                options: 'Fire\nTheft\nAccident\nNatural Disaster\nVandalism\nMalfunction\nOther',
                reqd: 1
            },
            {
                fieldname: 'claim_amount',
                fieldtype: 'Currency',
                label: __('Claim Amount'),
                reqd: 1,
                description: __('Maximum: {0}', [format_currency(frm.doc.sum_insured)])
            },
            {
                fieldname: 'claim_status',
                fieldtype: 'Select',
                label: __('Status'),
                options: 'Submitted\nUnder Review\nApproved\nRejected\nSettled',
                default: 'Submitted',
                reqd: 1
            },
            {
                fieldname: 'incident_description',
                fieldtype: 'Small Text',
                label: __('Incident Description'),
                reqd: 1
            },
            {
                fieldname: 'remarks',
                fieldtype: 'Small Text',
                label: __('Additional Remarks')
            }
        ],
        primary_action_label: __('File Claim'),
        primary_action: function(values) {
            // Validate claim amount
            if (flt(values.claim_amount) > flt(frm.doc.sum_insured)) {
                frappe.msgprint({
                    title: __('Invalid Claim Amount'),
                    message: __('Claim amount cannot exceed Sum Insured: {0}', 
                        [format_currency(frm.doc.sum_insured)]),
                    indicator: 'red'
                });
                return;
            }
            
            let row = frm.add_child('insurance_claims');
            row.claim_date = values.claim_date;
            row.claim_number = values.claim_number;
            row.claim_type = values.claim_type;
            row.claim_amount = values.claim_amount;
            row.claim_status = values.claim_status;
            row.incident_description = values.incident_description;
            row.remarks = values.remarks;
            
            frm.refresh_field('insurance_claims');
            frm.save();
            
            d.hide();
            
            frappe.show_alert({
                message: __('✓ Claim filed successfully'),
                indicator: 'green'
            }, 5);
        }
    });
    d.show();
}

function create_payment_reminder(frm) {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.fixed_asset_insurance.fixed_asset_insurance.create_payment_reminder',
        args: {
            doc_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                frappe.msgprint({
                    title: __('Payment Reminder'),
                    message: __('Next payment of {0} is due on {1}', [
                        format_currency(r.message.amount),
                        frappe.datetime.str_to_user(r.message.reminder_date)
                    ]),
                    indicator: 'blue'
                });
            }
        }
    });
}

function setup_filters(frm) {
    frm.set_query('asset', function() {
        return {
            filters: {
                'docstatus': 1,
                'asset_status': ['not in', ['Disposed', 'Sold', 'Scrapped']],
                'company': frm.doc.company
            }
        };
    });
    
    frm.set_query('insurance_provider', function() {
        return {
            filters: {
                'supplier_group': 'Insurance Company'
            }
        };
    });
    
    frm.set_query('cost_center', function() {
        return {
            filters: {
                'company': frm.doc.company,
                'is_group': 0
            }
        };
    });
    
    frm.set_query('insurance_expense_account', function() {
        return {
            filters: {
                'company': frm.doc.company,
                'account_type': 'Expense Account',
                'is_group': 0
            }
        };
    });
    
    frm.set_query('prepaid_insurance_account', function() {
        return {
            filters: {
                'company': frm.doc.company,
                'account_type': 'Prepaid',
                'is_group': 0
            }
        };
    });
}

// Child table: Insurance Claims
frappe.ui.form.on('Asset Insurance Claim', {
    claim_amount: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        // Validate against sum insured
        if (flt(row.claim_amount) > flt(frm.doc.sum_insured)) {
            frappe.model.set_value(cdt, cdn, 'claim_amount', frm.doc.sum_insured);
            frappe.msgprint({
                title: __('Claim Amount Adjusted'),
                message: __('Claim amount cannot exceed Sum Insured'),
                indicator: 'orange'
            });
        }
    },
    
    claim_status: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        // Auto-set settlement date for settled claims
        if (row.claim_status === 'Settled' && !row.settlement_date) {
            frappe.model.set_value(cdt, cdn, 'settlement_date', frappe.datetime.get_today());
        }
        
        // Alert for rejected claims
        if (row.claim_status === 'Rejected') {
            frappe.show_alert({
                message: __('⚠️ Claim {0} has been rejected', [row.claim_number]),
                indicator: 'red'
            }, 7);
        }
        
        // Alert for settled claims
        if (row.claim_status === 'Settled') {
            frappe.show_alert({
                message: __('✓ Claim {0} has been settled', [row.claim_number]),
                indicator: 'green'
            }, 5);
        }
    }
});

// Helper function
function format_currency(value) {
    return frappe.format(value, {fieldtype: 'Currency'});
}