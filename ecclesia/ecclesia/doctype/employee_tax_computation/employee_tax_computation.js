// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt


frappe.ui.form.on('Employee Tax Computation', {
    setup: function(frm) {
        if (frm.fields_dict.employee) {
            frm.set_query('employee', function() {
                return {
                    filters: {
                        'status': 'Active'
                    }
                };
            });
        }
    },
    
    onload: function(frm) {
        frm.set_currency_labels(["annual_gross_income", "total_statutory_deductions", 
                                 "total_benefits_in_kind", "annual_tax_payable", 
                                 "monthly_tax_payable", "annual_taxable_income"], "NGN");
        load_tax_settings(frm);
    },
    
    refresh: function(frm) {
        // Compute deductions on every refresh
        frm.trigger('compute_statutory_deductions');
        
        // Add custom buttons
        if (!frm.doc.__islocal && frm.doc.docstatus === 0) {
            frm.add_custom_button(__('Populate All Deductions'), function() {
                auto_populate_all_deductions(frm);
            }, __('Actions'));
            
            frm.add_custom_button(__('Tax Summary'), function() {
                show_detailed_summary(frm);
            }, __('Reports'));
            
            frm.add_custom_button(__('Tax Settings'), function() {
                frappe.set_route('Form', 'Tax Settings');
            }, __('Settings'));
        }
        
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__('💰 Calculate Tax'), function() {
                frm.save().then(() => {
                    show_detailed_summary(frm);
                });
            }).addClass('btn-primary');
        }
        
        // Show beautiful dashboard
        if (frm.doc.annual_gross_income) {
            setup_beautiful_dashboard(frm);
        }
    },
    
    compute_statutory_deductions: function(frm) {
        frappe.db.get_single_value('Tax Settings', 'life_insurance_cap')
            .then(life_ins_cap => {
                return frappe.db.get_single_value('Tax Settings', 'rent_relief_cap')
                    .then(rent_relief_cap => {
                        apply_deductions(frm, life_ins_cap, rent_relief_cap);
                    });
            });
    },
    
    annual_gross_income: function(frm) {
        update_deduction_basis(frm);
        update_benefit_basis(frm);
        frm.trigger('compute_statutory_deductions');
        trigger_quick_calculate(frm);
    },
    
    total_statutory_deductions: function(frm) {
        trigger_quick_calculate(frm);
    },
    
    total_benefits_in_kind: function(frm) {
        trigger_quick_calculate(frm);
    }
});

// Child table events - Statutory Deductions
frappe.ui.form.on('Statutory Deduction Item', {
    deduction_type: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        auto_set_deduction_details(frm, row);
    },
    
    rate: function(frm, cdt, cdn) {
        calculate_deduction_amount_from_row(frm, cdt, cdn);
        update_total_deductions(frm);
        trigger_quick_calculate(frm);
    },
    
    basis_amount: function(frm, cdt, cdn) {
        calculate_deduction_amount_from_row(frm, cdt, cdn);
        update_total_deductions(frm);
        trigger_quick_calculate(frm);
    },
    
    deduction_amount: function(frm, cdt, cdn) {
        update_total_deductions(frm);
        trigger_quick_calculate(frm);
    },
    
    statutory_deductions_remove: function(frm) {
        setTimeout(() => {
            update_total_deductions(frm);
            trigger_quick_calculate(frm);
        }, 100);
    }
});

// Child table events - Benefits in Kind
frappe.ui.form.on('Benefit in Kind Item', {
    valuation_rate: function(frm, cdt, cdn) {
        calculate_benefit_value(frm, cdt, cdn);
        update_total_benefits(frm);
        trigger_quick_calculate(frm);
    },
    
    basis_amount: function(frm, cdt, cdn) {
        calculate_benefit_value(frm, cdt, cdn);
        update_total_benefits(frm);
        trigger_quick_calculate(frm);
    },
    
    taxable_value: function(frm) {
        update_total_benefits(frm);
        trigger_quick_calculate(frm);
    },
    
    benefits_in_kind_remove: function(frm) {
        setTimeout(() => {
            update_total_benefits(frm);
            trigger_quick_calculate(frm);
        }, 100);
    }
});

// Apply deductions with capping logic
function apply_deductions(frm, life_ins_cap, rent_relief_cap) {
    life_ins_cap = flt(life_ins_cap || 100000);
    rent_relief_cap = flt(rent_relief_cap || 500000);
    
    let tax_settings = frm._tax_settings || {};
    
    (frm.doc.statutory_deductions || []).forEach(row => {
        let basis_amount = flt(row.basis_amount);
        let rate = flt(row.rate);
        let computed_amount = (basis_amount * rate) / 100;
        let final_amount = 0;
        
        if (row.deduction_type === "Life Insurance Premium") {
            final_amount = Math.min(computed_amount, life_ins_cap);
            if (computed_amount > life_ins_cap) {
                frappe.model.set_value(row.doctype, row.name, 'remarks', 
                    `Computed ₦${format_number(computed_amount)}, capped at ₦${format_number(life_ins_cap)}`);
            }
        }
        else if (row.deduction_type === "Rent Relief") {
            final_amount = Math.min(computed_amount, rent_relief_cap);
            if (computed_amount > rent_relief_cap) {
                frappe.model.set_value(row.doctype, row.name, 'remarks', 
                    `Computed ₦${format_number(computed_amount)}, capped at ₦${format_number(rent_relief_cap)}`);
            }
        }
        else {
            final_amount = computed_amount;
        }
        
        frappe.model.set_value(row.doctype, row.name, "deduction_amount", final_amount);
    });
    
    frm.refresh_field('statutory_deductions');
    update_total_deductions(frm);
}

// Auto set deduction details when type is selected
function auto_set_deduction_details(frm, row) {
    let tax_settings = frm._tax_settings || {};
    
    switch(row.deduction_type) {
        case "Pension Contribution":
            frappe.model.set_value(row.doctype, row.name, 'basis_amount', frm.doc.annual_gross_income);
            frappe.model.set_value(row.doctype, row.name, 'rate', tax_settings.pension_rate || 8);
            frappe.model.set_value(row.doctype, row.name, 'description', 'Employee Pension Contribution');
            break;
            
        case "NHF Contribution":
            frappe.model.set_value(row.doctype, row.name, 'basis_amount', frm.doc.annual_gross_income);
            frappe.model.set_value(row.doctype, row.name, 'rate', tax_settings.nhf_rate || 2.5);
            frappe.model.set_value(row.doctype, row.name, 'description', 'National Housing Fund Contribution');
            break;
            
        case "NHIS Contribution":
            frappe.model.set_value(row.doctype, row.name, 'basis_amount', frm.doc.annual_gross_income);
            frappe.model.set_value(row.doctype, row.name, 'rate', tax_settings.nhis_rate || 1.75);
            frappe.model.set_value(row.doctype, row.name, 'description', 'National Health Insurance Scheme');
            break;
            
        case "Rent Relief":
            frappe.model.set_value(row.doctype, row.name, 'rate', tax_settings.rent_relief_rate || 20);
            frappe.model.set_value(row.doctype, row.name, 'description', 'Rent Relief Allowance');
            break;
            
        case "Life Insurance Premium":
            frappe.model.set_value(row.doctype, row.name, 'rate', 100); // 100% of premium
            frappe.model.set_value(row.doctype, row.name, 'description', 'Life Insurance Premium Relief');
            break;
    }
    
    // Calculate the deduction amount after setting values
    setTimeout(() => {
        calculate_deduction_amount_from_row(frm, row.doctype, row.name);
    }, 100);
}

// Calculate deduction amount from a specific row
function calculate_deduction_amount_from_row(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let basis = flt(row.basis_amount);
    let rate = flt(row.rate);
    
    if (!basis || !rate) return;
    
    let computedAmount = basis * rate / 100;
    let cap = 0;
    let finalAmount = computedAmount;
    let tax_settings = frm._tax_settings || {};
    
    switch(row.deduction_type) {
        case "Pension Contribution":
        case "NHF Contribution":
        case "NHIS Contribution":
            // No cap for these
            break;
            
        case "Rent Relief":
            cap = tax_settings.rent_relief_cap || 500000;
            finalAmount = Math.min(computedAmount, cap);
            if (computedAmount > cap) {
                frappe.show_alert({
                    message: __("Rent Relief is capped at ₦500,000. Value adjusted."),
                    indicator: "orange"
                }, 3);
            }
            break;
            
        case "Life Insurance Premium":
            cap = tax_settings.life_insurance_cap || 100000;
            finalAmount = Math.min(computedAmount, cap);
            if (computedAmount > cap) {
                frappe.show_alert({
                    message: __("Life Insurance Premium is capped at ₦100,000. Value adjusted."),
                    indicator: "orange"
                }, 3);
            }
            break;
            
        default:
            finalAmount = computedAmount;
    }
    
    frappe.model.set_value(cdt, cdn, 'deduction_amount', finalAmount);
}

// Update total deductions
function update_total_deductions(frm) {
    let total = 0;
    let deductions = frm.doc.statutory_deductions || [];
    
    deductions.forEach(function(row) {
        if (row.deduction_amount) {
            total += flt(row.deduction_amount);
        }
    });
    
    frappe.model.set_value(frm.doctype, frm.docname, 'total_statutory_deductions', total);
}

// Update total benefits
function update_total_benefits(frm) {
    let total = 0;
    let benefits = frm.doc.benefits_in_kind || [];
    
    benefits.forEach(function(row) {
        if (row.taxable_value) {
            total += flt(row.taxable_value);
        }
    });
    
    frappe.model.set_value(frm.doctype, frm.docname, 'total_benefits_in_kind', total);
}

// Helper Functions
function load_tax_settings(frm) {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.employee_tax_computation.employee_tax_computation.get_tax_settings_rates',
        callback: function(r) {
            if (r.message) {
                frm._tax_settings = r.message;
                if (frm.doc.annual_gross_income) {
                    trigger_quick_calculate(frm);
                }
            }
        }
    });
}

function auto_populate_all_deductions(frm) {
    if (!frm.doc.annual_gross_income) {
        frappe.msgprint({
            title: __('Missing Information'),
            indicator: 'orange',
            message: __('Please enter Annual Gross Income first')
        });
        return;
    }
    
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.employee_tax_computation.employee_tax_computation.auto_populate_all_deductions',
        args: {
            employee: frm.doc.employee,
            annual_gross_income: frm.doc.annual_gross_income,
            fiscal_year: frm.doc.fiscal_year
        },
        callback: function(r) {
            if (r.message) {
                frm.clear_table('statutory_deductions');
                r.message.forEach(function(d) {
                    let row = frm.add_child('statutory_deductions');
                    Object.assign(row, d);
                });
                frm.refresh_field('statutory_deductions');
                
                // Recalculate totals
                setTimeout(() => {
                    update_total_deductions(frm);
                    frm.trigger('compute_statutory_deductions');
                }, 500);
                
                frappe.show_alert({
                    message: __('All deduction types populated successfully'),
                    indicator: 'green'
                }, 5);
                trigger_quick_calculate(frm);
            }
        }
    });
}

function update_deduction_basis(frm) {
    if (!frm.doc.statutory_deductions) return;
    
    frm.doc.statutory_deductions.forEach(function(row) {
        if (['Pension Contribution', 'NHF Contribution', 'NHIS Contribution'].includes(row.deduction_type)) {
            frappe.model.set_value(row.doctype, row.name, 'basis_amount', frm.doc.annual_gross_income);
            // Trigger recalculation
            setTimeout(() => {
                calculate_deduction_amount_from_row(frm, row.doctype, row.name);
            }, 100);
        }
    });
}

function update_benefit_basis(frm) {
    if (!frm.doc.benefits_in_kind) return;
    
    frm.doc.benefits_in_kind.forEach(function(row) {
        if (row.benefit_type === 'Rent-Free Accommodation') {
            frappe.model.set_value(row.doctype, row.name, 'basis_amount', frm.doc.annual_gross_income);
            // Trigger recalculation
            setTimeout(() => {
                calculate_benefit_value(frm, row.doctype, row.name);
            }, 100);
        }
    });
}

function calculate_benefit_value(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.valuation_rate && row.basis_amount) {
        let value = (row.basis_amount * row.valuation_rate) / 100;
        frappe.model.set_value(cdt, cdn, 'taxable_value', value);
    }
}

// Real-time calculation
let calculation_timeout;
function trigger_quick_calculate(frm) {
    clearTimeout(calculation_timeout);
    calculation_timeout = setTimeout(() => {
        quick_calculate_tax(frm);
    }, 500);
}

function quick_calculate_tax(frm) {
    if (!frm.doc.annual_gross_income) return;
    
    let deductions = frm.doc.statutory_deductions || [];
    let benefits = frm.doc.benefits_in_kind || [];
    
    // Calculate taxable income using the CORRECT formula: Gross - Deductions + Benefits
    let totalDeductions = 0;
    deductions.forEach(d => totalDeductions += flt(d.deduction_amount));
    let totalBenefits = frm.doc.total_benefits_in_kind || 0;
    
    // CORRECTED: Include benefits in taxable income calculation
    let taxableIncome = Math.max(flt(frm.doc.annual_gross_income) - totalDeductions + totalBenefits, 0);
    
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.employee_tax_computation.employee_tax_computation.quick_calculate',
        args: {
            annual_gross: frm.doc.annual_gross_income,
            taxable_income: taxableIncome,  // Now includes benefits
            deductions_json: JSON.stringify(deductions),
            benefits_json: JSON.stringify(benefits)
        },
        callback: function(r) {
            if (r.message) {
                update_beautiful_dashboard(frm, r.message);
            }
        }
    });
}

function setup_beautiful_dashboard(frm) {
    if (frm.doc.annual_gross_income && !frm.doc.__islocal) {
        // Remove existing dashboard if present
        let existingDashboard = document.getElementById(`tax-dashboard-${frm.doc.name}`);
        if (existingDashboard) {
            existingDashboard.remove();
        }
        
        const dashboard_html = `
            <div class="tax-dashboard-modern" id="tax-dashboard-${frm.doc.name}">
                <style>
                    .tax-dashboard-modern {
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        border-radius: 15px;
                        padding: 25px;
                        margin: 15px 0 25px 0;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                        position: relative;
                        overflow: hidden;
                    }
                    .tax-dashboard-modern::before {
                        content: '';
                        position: absolute;
                        top: 0;
                        left: 0;
                        right: 0;
                        height: 5px;
                        background: linear-gradient(90deg, #ff6b6b, #4ecdc4, #45b7d1, #96ceb4, #feca57, #ff6b6b);
                        background-size: 200% 100%;
                        animation: shimmer 3s infinite linear;
                    }
                    .tax-stat-grid {
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                        gap: 15px;
                        margin-top: 20px;
                    }
                    .tax-stat-card {
                        background: rgba(255,255,255,0.15);
                        backdrop-filter: blur(10px);
                        border: 1px solid rgba(255,255,255,0.2);
                        border-radius: 12px;
                        padding: 20px;
                        transition: all 0.3s ease;
                        position: relative;
                        overflow: hidden;
                    }
                    .tax-stat-card:hover {
                        transform: translateY(-5px);
                        background: rgba(255,255,255,0.25);
                        box-shadow: 0 8px 20px rgba(0,0,0,0.3);
                    }
                    .tax-stat-label {
                        font-size: 11px;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                        color: rgba(255,255,255,0.8);
                        margin-bottom: 8px;
                        font-weight: 600;
                    }
                    .tax-stat-value {
                        font-size: 24px;
                        font-weight: 700;
                        color: #ffffff;
                        margin: 5px 0;
                        text-shadow: 0 2px 4px rgba(0,0,0,0.2);
                    }
                    .tax-stat-subtitle {
                        font-size: 12px;
                        color: rgba(255,255,255,0.7);
                        margin-top: 5px;
                        display: flex;
                        align-items: center;
                        gap: 5px;
                    }
                    .tax-header {
                        color: white;
                        margin: 0 0 10px 0;
                        font-size: 24px;
                        font-weight: 700;
                        text-shadow: 0 2px 4px rgba(0,0,0,0.2);
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    }
                    .tax-subheader {
                        color: rgba(255,255,255,0.9);
                        margin: 0;
                        font-size: 14px;
                    }
                    .pulse-animation {
                        animation: pulse 2s infinite;
                    }
                    @keyframes pulse {
                        0%, 100% { opacity: 1; }
                        50% { opacity: 0.8; }
                    }
                    @keyframes shimmer {
                        0% { background-position: 200% 0; }
                        100% { background-position: -200% 0; }
                    }
                    .tax-update-indicator {
                        position: absolute;
                        top: 10px;
                        right: 10px;
                        background: rgba(255,255,255,0.2);
                        padding: 4px 8px;
                        border-radius: 12px;
                        font-size: 10px;
                        color: white;
                        animation: pulse 1.5s infinite;
                    }
                </style>
                <div class="tax-update-indicator" id="update-indicator">🔄 Live Updates</div>
                <h3 class="tax-header">💰 Tax Computation Dashboard</h3>
                <p class="tax-subheader">Real-time tax calculation • Nigeria Tax Act 2025</p>
                <div class="tax-stat-grid" id="tax-stats-content">
                    <div class="tax-stat-card pulse-animation">
                        <div class="tax-stat-label">⏳ Calculating...</div>
                        <div class="tax-stat-value">Please wait</div>
                        <div class="tax-stat-subtitle">Loading tax data</div>
                    </div>
                </div>
            </div>
        `;
        
        // Add dashboard to form
        $(dashboard_html).insertAfter(frm.wrapper.find('.form-section:first'));
        trigger_quick_calculate(frm);
    }
}

function update_beautiful_dashboard(frm, data) {
    const stats_html = `
        <div class="tax-stat-card">
            <div class="tax-stat-label">💵 Gross Income</div>
            <div class="tax-stat-value">${format_currency(data.gross_income, 'NGN')}</div>
            <div class="tax-stat-subtitle">📅 Annual Salary</div>
        </div>
        
        <div class="tax-stat-card">
            <div class="tax-stat-label">➖ Statutory Deductions</div>
            <div class="tax-stat-value">${format_currency(data.total_deductions, 'NGN')}</div>
            <div class="tax-stat-subtitle">🧾 Pension, NHF, NHIS</div>
        </div>
        
        <div class="tax-stat-card">
            <div class="tax-stat-label">➕ Benefits in Kind</div>
            <div class="tax-stat-value">${format_currency(data.total_benefits, 'NGN')}</div>
            <div class="tax-stat-subtitle">🏠 Housing, Car, etc.</div>
        </div>
        
        <div class="tax-stat-card" style="background: rgba(33,150,243,0.25); border-color: rgba(33,150,243,0.4);">
            <div class="tax-stat-label">📊 Taxable Income</div>
            <div class="tax-stat-value" style="color: #bbdefb;">${format_currency(data.taxable_income, 'NGN')}</div>
            <div class="tax-stat-subtitle">Gross - Deductions + Benefits</div>
        </div>
        
        <div class="tax-stat-card" style="background: rgba(244,67,54,0.25); border-color: rgba(244,67,54,0.4);">
            <div class="tax-stat-label">📈 Annual Tax Payable</div>
            <div class="tax-stat-value" style="color: #ffcdd2;">${format_currency(data.total_annual_tax, 'NGN')}</div>
            <div class="tax-stat-subtitle">📋 PAYE Tax Liability</div>
        </div>
        
        <div class="tax-stat-card" style="background: rgba(244,67,54,0.25); border-color: rgba(244,67,54,0.4);">
            <div class="tax-stat-label">📅 Monthly Tax (PAYE)</div>
            <div class="tax-stat-value" style="color: #ffcdd2;">${format_currency(data.monthly_tax, 'NGN')}</div>
            <div class="tax-stat-subtitle">💰 Monthly Remittance</div>
        </div>
        
        <div class="tax-stat-card" style="background: rgba(76,175,80,0.25); border-color: rgba(76,175,80,0.4);">
            <div class="tax-stat-label">✅ Net Monthly Income</div>
            <div class="tax-stat-value" style="color: #c8e6c9;">${format_currency(data.net_monthly_income, 'NGN')}</div>
            <div class="tax-stat-subtitle">💳 Take Home Pay</div>
        </div>
        
        <div class="tax-stat-card" style="background: rgba(255,193,7,0.25); border-color: rgba(255,193,7,0.4);">
            <div class="tax-stat-label">📊 Effective Tax Rate</div>
            <div class="tax-stat-value" style="color: #fff8e1;">${data.effective_rate.toFixed(2)}%</div>
            <div class="tax-stat-subtitle">⚖️ Tax Burden Percentage</div>
        </div>
    `;
    
    let elem = document.getElementById('tax-stats-content');
    let updateIndicator = document.getElementById('update-indicator');
    
    if (elem) {
        if (updateIndicator) {
            updateIndicator.innerHTML = '🔄 Updated just now';
            updateIndicator.style.animation = 'none';
            setTimeout(() => {
                updateIndicator.innerHTML = '🔄 Live Updates';
                updateIndicator.style.animation = 'pulse 1.5s infinite';
            }, 1000);
        }
        
        elem.innerHTML = stats_html;
    }
}

function show_detailed_summary(frm) {
    if (frm.is_dirty()) {
        frappe.msgprint({
            title: __('Unsaved Changes'),
            indicator: 'orange',
            message: __('Please save the document first to generate the tax summary')
        });
        return;
    }
    
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.employee_tax_computation.employee_tax_computation.get_tax_summary',
        args: { name: frm.doc.name },
        callback: function(r) {
            if (r.message) {
                display_tax_summary_dialog(r.message);
            }
        }
    });
}

function display_tax_summary_dialog(data) {
    let tax_breakdown_html = `
        <div style="overflow-x: auto; margin-top: 15px;">
            <table class="table table-bordered" style="min-width: 800px;">
                <thead style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                    <tr>
                        <th style="padding: 12px 15px; border-radius: 8px 0 0 0;">Tax Band</th>
                        <th style="padding: 12px 15px; text-align: right;">Income in Band</th>
                        <th style="padding: 12px 15px; text-align: center;">Rate</th>
                        <th style="padding: 12px 15px; text-align: right;">Tax Amount</th>
                        <th style="padding: 12px 15px; text-align: right; border-radius: 0 8px 0 0;">Cumulative</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    data.tax_breakdown.forEach(function(band, idx) {
        const rowColor = idx % 2 === 0 ? '#f8f9fa' : '#ffffff';
        const isLastRow = idx === data.tax_breakdown.length - 1;
        tax_breakdown_html += `
            <tr style="background: ${rowColor}; ${isLastRow ? 'border-bottom: 2px solid #667eea;' : ''}">
                <td style="padding: 10px 15px; ${isLastRow ? 'border-radius: 0 0 0 8px;' : ''}">
                    <strong>${band.description}</strong>
                </td>
                <td style="padding: 10px 15px; text-align: right;">${format_currency(band.income, 'NGN')}</td>
                <td style="padding: 10px 15px; text-align: center;">
                    <span class="badge" style="background: ${getRateColor(band.rate)}; color: white; padding: 4px 8px; border-radius: 12px;">
                        ${band.rate}%
                    </span>
                </td>
                <td style="padding: 10px 15px; text-align: right;">
                    ${format_currency(band.tax, 'NGN')}
                </td>
                <td style="padding: 10px 15px; text-align: right; ${isLastRow ? 'border-radius: 0 0 8px 0;' : ''}">
                    <strong style="color: #667eea;">${format_currency(band.cumulative, 'NGN')}</strong>
                </td>
            </tr>
        `;
    });
    
    tax_breakdown_html += '</tbody></table></div>';
    
    let summary_html = `
        <div class="tax-summary-modern">
            <style>
                .tax-summary-modern {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                }
                .tax-summary-modern .summary-header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 12px;
                    margin-bottom: 25px;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.2);
                    position: relative;
                    overflow: hidden;
                }
                .tax-summary-modern .stat-box {
                    border-radius: 10px;
                    padding: 20px;
                    margin-bottom: 20px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                    transition: all 0.3s ease;
                    border: 1px solid rgba(0,0,0,0.05);
                    position: relative;
                }
                .tax-summary-modern .stat-box:hover {
                    transform: translateY(-5px);
                    box-shadow: 0 8px 20px rgba(0,0,0,0.15);
                }
                .tax-summary-modern .highlight-box {
                    background: linear-gradient(135deg, #e0f7fa 0%, #b2ebf2 100%);
                    border-left: 4px solid #00695c;
                }
                .tax-summary-modern .tax-box {
                    background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
                    border-left: 4px solid #e65100;
                }
                .tax-summary-modern .net-box {
                    background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
                    border-left: 4px solid #2e7d32;
                }
                .tax-summary-modern .benefits-box {
                    background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%);
                    border-left: 4px solid #7b1fa2;
                }
                .stat-row {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 8px 0;
                    border-bottom: 1px solid rgba(0,0,0,0.05);
                }
                .stat-row:last-child {
                    border-bottom: none;
                }
                .stat-label {
                    font-size: 14px;
                    color: #555;
                }
                .stat-value {
                    font-size: 16px;
                    font-weight: 600;
                    color: #333;
                }
                .tax-total {
                    font-size: 18px;
                    color: #d32f2f;
                    font-weight: 700;
                }
            </style>
            
            <div class="summary-header">
                <h2 style="margin: 0 0 8px 0; color: white; font-size: 28px; position: relative;">🧾 Comprehensive Tax Report</h2>
                <p style="margin: 0; opacity: 0.9; font-size: 16px; position: relative;">
                    ${data.employee} • ${data.employee_name} • ${data.tax_year}
                </p>
                <div style="position: absolute; bottom: 20px; right: 20px; background: rgba(255,255,255,0.2); padding: 8px 15px; border-radius: 20px;">
                    <span style="font-weight: 600;">Generated: ${new Date().toLocaleDateString()}</span>
                </div>
            </div>
            
            <div class="row">
                <div class="col-sm-6">
                    <div class="stat-box highlight-box">
                        <h5 style="margin-top: 0; color: #00695c; border-bottom: 2px solid rgba(0,105,92,0.3); padding-bottom: 10px;">
                            💰 Income Breakdown
                        </h5>
                        <div class="stat-row">
                            <div class="stat-label">Gross Annual Income:</div>
                            <div class="stat-value">${format_currency(data.gross_income, 'NGN')}</div>
                        </div>
                        <div class="stat-row">
                            <div class="stat-label">Statutory Deductions:</div>
                            <div class="stat-value" style="color: #d84315;">- ${format_currency(data.total_deductions, 'NGN')}</div>
                        </div>
                        <div class="stat-row">
                            <div class="stat-label">Benefits in Kind:</div>
                            <div class="stat-value" style="color: #7b1fa2;">+ ${format_currency(data.total_benefits, 'NGN')}</div>
                        </div>
                        <div class="stat-row" style="border-top: 2px solid #00695c; margin-top: 10px; padding-top: 15px;">
                            <div class="stat-label"><strong>Taxable Income:</strong></div>
                            <div class="stat-value" style="font-size: 20px; color: #00695c;">
                                <strong>${format_currency(data.taxable_income, 'NGN')}</strong>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="col-sm-6">
                    <div class="stat-box tax-box">
                        <h5 style="margin-top: 0; color: #e65100; border-bottom: 2px solid rgba(230,81,0,0.3); padding-bottom: 10px;">
                            📊 Tax Liability
                        </h5>
                        <div class="stat-row">
                            <div class="stat-label">Annual Tax Payable:</div>
                            <div class="stat-value tax-total">${format_currency(data.annual_tax, 'NGN')}</div>
                        </div>
                        <div class="stat-row">
                            <div class="stat-label">Monthly Tax (PAYE):</div>
                            <div class="stat-value" style="color: #d32f2f;">${format_currency(data.monthly_tax, 'NGN')}</div>
                        </div>
                        <div class="stat-row">
                            <div class="stat-label">Effective Tax Rate:</div>
                            <div class="stat-value">${data.effective_rate.toFixed(2)}%</div>
                        </div>
                        <div class="stat-row">
                            <div class="stat-label">Tax Year:</div>
                            <div class="stat-value"><span class="badge" style="background: #e65100; color: white;">${data.tax_year}</span></div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-sm-6">
                    <div class="stat-box net-box">
                        <h5 style="margin-top: 0; color: #2e7d32; border-bottom: 2px solid rgba(46,125,50,0.3); padding-bottom: 10px;">
                            💵 Net Take Home Pay
                        </h5>
                        <div style="text-align: center; padding: 15px 0;">
                            <div style="font-size: 14px; color: #558b2f; margin-bottom: 10px;">Monthly Net Income After Tax</div>
                            <div style="font-size: 36px; font-weight: 700; color: #1b5e20; margin: 15px 0;">
                                ${format_currency(data.net_monthly_income, 'NGN')}
                            </div>
                            <div style="font-size: 14px; color: #7cb342; background: rgba(124,179,66,0.1); padding: 8px; border-radius: 8px;">
                                ≈ ${format_currency(data.net_monthly_income / 30, 'NGN')} per day
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="col-sm-6">
                    <div class="stat-box benefits-box">
                        <h5 style="margin-top: 0; color: #7b1fa2; border-bottom: 2px solid rgba(123,31,162,0.3); padding-bottom: 10px;">
                            🎁 Fringe Benefits Overview
                        </h5>
                        <div class="stat-row">
                            <div class="stat-label">Total Benefits Value:</div>
                            <div class="stat-value" style="color: #7b1fa2;">${format_currency(data.total_benefits, 'NGN')}</div>
                        </div>
                        <div class="stat-row">
                            <div class="stat-label">Benefits Count:</div>
                            <div class="stat-value">${data.benefits_count || 0} items</div>
                        </div>
                        <div class="stat-row">
                            <div class="stat-label">Avg. Benefit Value:</div>
                            <div class="stat-value">${format_currency((data.total_benefits || 0) / (data.benefits_count || 1), 'NGN')}</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <h4 style="margin-top: 30px; color: #667eea; border-bottom: 3px solid #667eea; padding-bottom: 10px; display: flex; align-items: center; gap: 10px;">
                📈 Progressive Tax Breakdown
                <span style="font-size: 14px; color: #999; font-weight: normal;">(Nigeria Tax Bands 2025)</span>
            </h4>
            ${tax_breakdown_html}
            
            <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 10px; border-left: 4px solid #667eea;">
                <h5 style="margin-top: 0; color: #667eea;">📝 Notes & Assumptions</h5>
                <ul style="margin-bottom: 0; color: #666;">
                    <li>Based on Nigeria Personal Income Tax Act (PITA) 2025</li>
                    <li>Statutory deductions include Pension (8%), NHF (2.5%), and NHIS (1.75%)</li>
                    <li>Rent relief capped at ₦500,000 or 20% of rent paid</li>
                    <li>Life insurance premium relief capped at ₦100,000</li>
                    <li>Calculations assume tax residency in Nigeria</li>
                </ul>
            </div>
        </div>
    `;
    
    let d = new frappe.ui.Dialog({
        title: __('Tax Computation Summary'),
        size: 'extra-large',
        fields: [{ fieldtype: 'HTML', options: summary_html }],
        primary_action_label: __('🖨️ Print Report'),
        primary_action: function() {
            print_tax_summary(summary_html, data);
        },
        secondary_action_label: __('📥 Export PDF'),
        secondary_action: function() {
            export_pdf_summary(data);
        }
    });
    
    d.show();
}

function getRateColor(rate) {
    if (rate <= 7) return '#4CAF50';
    if (rate <= 11) return '#2196F3';
    if (rate <= 15) return '#FF9800';
    return '#F44336';
}

function print_tax_summary(html, data) {
    let print_window = window.open('', '_blank');
    print_window.document.write(`
        <html>
            <head>
                <title>Tax Summary - ${data.employee} - ${data.employee_name}</title>
                <style>
                    body { 
                        font-family: 'Segoe UI', sans-serif; 
                        padding: 30px; 
                        background: #f5f7fa;
                    }
                    .print-container {
                        max-width: 1200px;
                        margin: 0 auto;
                        background: white;
                        padding: 40px;
                        border-radius: 12px;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                    }
                    .print-header {
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 30px;
                        border-radius: 8px;
                        margin-bottom: 30px;
                        text-align: center;
                    }
                    @media print {
                        body { 
                            padding: 0; 
                            background: white;
                        }
                        .print-container {
                            box-shadow: none;
                            padding: 20px;
                        }
                        .no-print { display: none !important; }
                    }
                </style>
            </head>
            <body>
                <div class="print-container">
                    ${html}
                </div>
                <div class="no-print" style="text-align: center; margin-top: 20px; padding: 20px;">
                    <button onclick="window.print()" style="
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        border: none;
                        padding: 12px 24px;
                        border-radius: 6px;
                        font-weight: 600;
                        cursor: pointer;
                        margin-right: 10px;
                    ">🖨️ Print Report</button>
                    <button onclick="window.close()" style="
                        background: #f44336;
                        color: white;
                        border: none;
                        padding: 12px 24px;
                        border-radius: 6px;
                        font-weight: 600;
                        cursor: pointer;
                    ">✕ Close Window</button>
                </div>
                <script>
                    setTimeout(() => {
                        window.print();
                    }, 1000);
                </script>
            </body>
        </html>
    `);
    print_window.document.close();
}

function export_pdf_summary(data) {
    frappe.show_alert({
        message: __('PDF export feature coming soon!'),
        indicator: 'blue'
    }, 3);
}

function format_currency(value, currency) {
    return frappe.format(value, {fieldtype: 'Currency', options: currency});
}