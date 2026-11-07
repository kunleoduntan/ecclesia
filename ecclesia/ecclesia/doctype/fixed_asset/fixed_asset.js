// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

frappe.ui.form.on('Fixed Asset', {
    setup: function(frm) {
        setup_field_queries(frm);
    },

    onload: function(frm) {
        if (!frm.doc.company && frappe.defaults.get_user_default("Company")) {
            frm.set_value('company', frappe.defaults.get_user_default("Company"));
        }
        refresh_status_indicators(frm);
    },

    refresh: function(frm) {
        frm.page.clear_inner_toolbar();
        add_custom_buttons(frm);
        refresh_field_displays(frm);
        refresh_status_indicators(frm);
        show_smart_alerts(frm);
        apply_conditional_formatting(frm);
        apply_schedule_row_colors(frm);

        // QR code display — wait for DOM to be ready
        if (frm.doc.docstatus === 1 && frm.doc.qr_code_image) {
            setTimeout(() => enhance_qr_code_display(frm), 600);
        }
    },

    before_save: function(frm) {
        if (frm.doc.calculate_depreciation && frm.doc.docstatus === 0) {
            calculate_depreciation_values(frm);
            setTimeout(() => generate_depreciation_schedule(frm), 100);
        }
    },

    asset_category: function(frm) {
        if (frm.doc.asset_category) {
            frappe.call({
                method: 'frappe.client.get',
                args: { doctype: 'Fixed Asset Category', name: frm.doc.asset_category },
                callback: function(r) {
                    if (!r.message) return;
                    const cat = r.message;

                    if (!frm.doc.asset_account && cat.fixed_asset_account)
                        frm.set_value('asset_account', cat.fixed_asset_account);

                    if (cat.enable_depreciation) {
                        frm.set_value('is_depreciable_asset', 1);
                        if (!frm.doc.accumulated_depreciation_account && cat.accumulated_depreciation_account)
                            frm.set_value('accumulated_depreciation_account', cat.accumulated_depreciation_account);
                        if (!frm.doc.depreciation_expense_account && cat.depreciation_expense_account)
                            frm.set_value('depreciation_expense_account', cat.depreciation_expense_account);
                        if (!frm.doc.depreciation_method && cat.depreciation_method)
                            frm.set_value('depreciation_method', cat.depreciation_method);
                        if (!frm.doc.total_number_of_depreciations && cat.total_number_of_depreciations)
                            frm.set_value('total_number_of_depreciations', cat.total_number_of_depreciations);
                        if (!frm.doc.depreciation_frequency && cat.frequency_of_depreciation)
                            frm.set_value('depreciation_frequency', cat.frequency_of_depreciation);
                        if (!frm.doc.depreciation_rate && cat.rate_of_depreciation)
                            frm.set_value('depreciation_rate', cat.rate_of_depreciation);
                        if (!frm.doc.useful_life_months && cat.useful_life_months)
                            frm.set_value('useful_life_months', cat.useful_life_months);
                    }

                    frappe.show_alert({ message: __('Category defaults loaded'), indicator: 'green' }, 3);
                }
            });
        }
    },

    gross_purchase_amount: function(frm) {
        calculate_depreciation_values(frm);
        calculate_current_value(frm);
        if (frm.doc.docstatus === 0 && frm.doc.calculate_depreciation)
            setTimeout(() => generate_depreciation_schedule(frm), 300);
    },

    salvage_value: function(frm) {
        if (frm.doc.salvage_value != frm.doc.residual_value)
            frm.set_value('residual_value', frm.doc.salvage_value);
        calculate_depreciation_values(frm);
        if (frm.doc.docstatus === 0 && frm.doc.calculate_depreciation)
            setTimeout(() => generate_depreciation_schedule(frm), 300);
    },

    residual_value: function(frm) {
        if (frm.doc.residual_value != frm.doc.salvage_value)
            frm.set_value('salvage_value', frm.doc.residual_value);
        calculate_depreciation_values(frm);
        if (frm.doc.docstatus === 0 && frm.doc.calculate_depreciation)
            setTimeout(() => generate_depreciation_schedule(frm), 300);
    },

    opening_accumulated_depreciation: function(frm) {
        calculate_current_value(frm);
        if (frm.doc.docstatus === 0 && frm.doc.calculate_depreciation && frm.doc.is_existing_asset)
            setTimeout(() => generate_depreciation_schedule(frm), 300);
    },

    is_depreciable_asset: function(frm) {
        if (frm.doc.is_depreciable_asset) frm.set_value('calculate_depreciation', 1);
        frm.trigger('refresh');
    },

    calculate_depreciation: function(frm) {
        if (frm.doc.calculate_depreciation) {
            calculate_depreciation_values(frm);
            if (frm.doc.docstatus === 0)
                setTimeout(() => generate_depreciation_schedule(frm), 300);
        }
        frm.trigger('refresh');
    },

    depreciation_method: function(frm) {
        calculate_depreciation_values(frm);
        if (frm.doc.docstatus === 0 && frm.doc.calculate_depreciation)
            setTimeout(() => generate_depreciation_schedule(frm), 300);
    },

    total_number_of_depreciations: function(frm) {
        calculate_depreciation_values(frm);
        if (frm.doc.docstatus === 0 && frm.doc.calculate_depreciation)
            setTimeout(() => generate_depreciation_schedule(frm), 300);
    },

    depreciation_frequency: function(frm) {
        if (frm.doc.useful_life_months && frm.doc.depreciation_frequency) {
            const freq = get_frequency_months(frm.doc.depreciation_frequency);
            frm.set_value('total_number_of_depreciations', Math.floor(frm.doc.useful_life_months / freq));
        }
        calculate_depreciation_values(frm);
        if (frm.doc.docstatus === 0 && frm.doc.calculate_depreciation)
            setTimeout(() => generate_depreciation_schedule(frm), 300);
    },

    useful_life_months: function(frm) {
        if (frm.doc.useful_life_months && frm.doc.depreciation_frequency) {
            const freq = get_frequency_months(frm.doc.depreciation_frequency);
            frm.set_value('total_number_of_depreciations', Math.floor(frm.doc.useful_life_months / freq));
        }
    },

    depreciation_start_date: function(frm) {
        if (frm.doc.docstatus === 0 && frm.doc.calculate_depreciation)
            setTimeout(() => generate_depreciation_schedule(frm), 300);
    },

    available_for_use_date: function(frm) {
        if (!frm.doc.depreciation_start_date && frm.doc.calculate_depreciation)
            frm.set_value('depreciation_start_date', frm.doc.available_for_use_date);
    },

    purchase_date: function(frm) {
        if (frm.doc.is_existing_asset && frm.doc.calculate_depreciation) {
            calculate_depreciation_values(frm);
            if (frm.doc.docstatus === 0)
                setTimeout(() => generate_depreciation_schedule(frm), 300);
        }
    },

    is_existing_asset: function(frm) {
        if (frm.doc.is_existing_asset) {
            frappe.msgprint({
                title: __('Existing Asset Setup'), indicator: 'blue',
                message: __('Depreciation Start Date and Next Depreciation Date will be automatically set to the 25th of the first month of the current Fiscal Year, and Opening Accumulated Depreciation will be pre-filled from the elapsed periods since Purchase Date. Both are editable to match your migrated trial balance.')
            });
        }
        if (frm.doc.calculate_depreciation) {
            calculate_depreciation_values(frm);
            if (frm.doc.docstatus === 0)
                setTimeout(() => generate_depreciation_schedule(frm), 300);
        }
    }
});

frappe.ui.form.on('Depreciation Schedule Details', {
    depreciation_schedules_add: function(frm, cdt, cdn) {}
});

// ============================================================================
// FIELD QUERIES
// ============================================================================

function setup_field_queries(frm) {
    frm.set_query('cost_center', () => ({ filters: { company: frm.doc.company, is_group: 0 } }));
    frm.set_query('asset_account', () => ({ filters: { company: frm.doc.company, account_type: 'Fixed Asset', is_group: 0 } }));
    frm.set_query('accumulated_depreciation_account', () => ({ filters: { company: frm.doc.company, root_type: 'Asset', is_group: 0 } }));
    frm.set_query('depreciation_expense_account', () => ({ filters: { company: frm.doc.company, root_type: 'Expense', is_group: 0 } }));
    frm.set_query('department', () => ({ filters: { company: frm.doc.company } }));
}

// ============================================================================
// CUSTOM BUTTONS
// ============================================================================

function add_custom_buttons(frm) {
    if (frm.doc.docstatus === 0) {
        frm.add_custom_button(__('🔄 Recalculate Depreciation'), () => recalculate_depreciation(frm), __('Actions'));

        if (frm.doc.calculate_depreciation) {
            frm.add_custom_button(__('📅 Generate Schedule'), () => {
                calculate_depreciation_values(frm);
                setTimeout(() => generate_depreciation_schedule(frm), 200);
            }, __('Actions'));
        }

        if (frm.doc.asset_quantity > 1) {
            frm.add_custom_button(__('✂️ Split Asset'), () => split_asset_dialog(frm), __('Actions'));
        }
    }

    if (frm.doc.docstatus === 1) {
        // Actions
        frm.add_custom_button(__('🔄 Recalculate'), () => recalculate_submitted_asset(frm), __('Actions'));

        // QR Code buttons
        if (frm.doc.qr_code_image) {
            frm.add_custom_button(__('👁️ View QR Code'), () => show_qr_code_dialog(frm), __('QR Code'));
            frm.add_custom_button(__('🖨️ Print QR Code'), () => print_qr_code(frm), __('QR Code'));
            frm.add_custom_button(__('📥 Download QR'), () => download_qr_code(frm), __('QR Code'));
        } else {
            frm.add_custom_button(__('🔄 Generate QR Code'), () => trigger_qr_generation(frm), __('QR Code'));
        }

        // View buttons — working implementations
        frm.add_custom_button(__('📋 View History'), () => show_asset_history(frm), __('View'));
        frm.add_custom_button(__('📅 View Schedule'), () => show_depreciation_schedule(frm), __('View'));
        frm.add_custom_button(__('🔍 Asset Details'), () => show_asset_details_dialog(frm), __('View'));

        // Depreciation buttons
        if (frm.doc.calculate_depreciation) {
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Depreciation Schedule Details',
                    filters: {
                        parent: frm.doc.name,
                        schedule_date: ['<=', frappe.datetime.get_today()],
                        status: 'Scheduled'
                    },
                    fields: ['name'], limit: 1
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        frm.add_custom_button(__('💵 Post Due Depreciation'), () => post_due_depreciation(frm), __('Depreciation'));
                    }
                }
            });

            frm.add_custom_button(__('📅 Post Catch-up Depreciation'), () => show_catchup_dialog(frm), __('Depreciation'));
        }
    }
}

// ============================================================================
// VIEW BUTTON IMPLEMENTATIONS (all working — no external reports needed)
// ============================================================================

function show_asset_history(frm) {
    // frappe.client.get_list cannot query child tables — must use whitelisted server method
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.fixed_asset.fixed_asset.get_asset_history',
        args: { asset_name: frm.doc.name },
        callback: function(r) {
            const logs = (r.message) || [];
            let html = '';
            if (!logs.length) {
                html = '<p class="text-muted text-center" style="padding:20px;">No history records found.</p>';
            } else {
                html = `<div style="max-height:450px;overflow-y:auto;">
                    <table class="table table-bordered table-condensed" style="font-size:12px;margin:0;">
                    <thead style="background:#f5f5f5;position:sticky;top:0;">
                        <tr><th>Date</th><th>Action</th><th>Type</th><th>Description</th><th>User</th></tr>
                    </thead><tbody>`;
                logs.forEach(log => {
                    html += `<tr>
                        <td style="white-space:nowrap">${frappe.datetime.str_to_user(log.transaction_date) || ''}</td>
                        <td><b>${log.action || ''}</b></td>
                        <td><span class="badge badge-info">${log.transaction_type || ''}</span></td>
                        <td>${log.description || ''}</td>
                        <td style="white-space:nowrap">${(log.user || '').split('@')[0]}</td>
                    </tr>`;
                });
                html += '</tbody></table></div>';
            }

            let d = new frappe.ui.Dialog({
                title: __('📋 Asset History — {0}', [frm.doc.asset_code]),
                fields: [{ fieldname: 'history_html', fieldtype: 'HTML' }],
                size: 'large'
            });
            d.fields_dict.history_html.$wrapper.html(html);
            d.show();
        }
    });
}

function show_depreciation_schedule(frm) {
    const rows = frm.doc.depreciation_schedules || [];
    let html = '';

    if (!rows.length) {
        html = '<p class="text-muted text-center" style="padding:20px">No depreciation schedule found. Use Generate Schedule to create one.</p>';
    } else {
        // Summary bar
        const posted = rows.filter(r => r.journal_entry).length;
        const pending = rows.length - posted;
        const total_dep = rows.reduce((s, r) => s + flt(r.depreciation_amount), 0);

        html = `
            <div style="display:flex;gap:16px;margin-bottom:12px;flex-wrap:wrap;">
                <div style="background:#d4edda;padding:8px 16px;border-radius:6px;flex:1;text-align:center;">
                    <div style="font-size:18px;font-weight:bold;color:#155724;">${rows.length}</div>
                    <div style="font-size:11px;color:#155724;">Total Periods</div>
                </div>
                <div style="background:#cce5ff;padding:8px 16px;border-radius:6px;flex:1;text-align:center;">
                    <div style="font-size:18px;font-weight:bold;color:#004085;">${posted}</div>
                    <div style="font-size:11px;color:#004085;">Posted</div>
                </div>
                <div style="background:#fff3cd;padding:8px 16px;border-radius:6px;flex:1;text-align:center;">
                    <div style="font-size:18px;font-weight:bold;color:#856404;">${pending}</div>
                    <div style="font-size:11px;color:#856404;">Pending</div>
                </div>
                <div style="background:#e2e3e5;padding:8px 16px;border-radius:6px;flex:1;text-align:center;">
                    <div style="font-size:15px;font-weight:bold;color:#383d41;">${format_currency(total_dep)}</div>
                    <div style="font-size:11px;color:#383d41;">Total Depreciation</div>
                </div>
            </div>
            <div style="max-height:350px;overflow-y:auto;">
            <table class="table table-bordered table-condensed" style="font-size:12px;margin:0;">
                <thead style="background:#f5f5f5;position:sticky;top:0;">
                    <tr>
                        <th>#</th><th>Period Date</th><th>Opening</th>
                        <th>Depreciation</th><th>Closing</th><th>Accumulated</th><th>Status</th>
                    </tr>
                </thead><tbody>`;

        rows.forEach((row, i) => {
            const status_badge = row.journal_entry
                ? `<span class="badge badge-success">✅ Posted</span>`
                : `<span class="badge badge-secondary">⏳ Pending</span>`;
            html += `<tr>
                <td>${i + 1}</td>
                <td>${frappe.datetime.str_to_user(row.schedule_date)}</td>
                <td style="text-align:right">${format_currency(row.opening_balance || 0)}</td>
                <td style="text-align:right;color:#c0392b;">${format_currency(row.depreciation_amount)}</td>
                <td style="text-align:right">${format_currency(row.closing_balance || 0)}</td>
                <td style="text-align:right">${format_currency(row.accumulated_depreciation || 0)}</td>
                <td>${status_badge}</td>
            </tr>`;
        });
        html += '</tbody></table></div>';
    }

    let d = new frappe.ui.Dialog({
        title: __('📅 Depreciation Schedule — {0}', [frm.doc.asset_code]),
        fields: [{ fieldname: 'schedule_html', fieldtype: 'HTML' }],
        size: 'large'
    });
    d.fields_dict.schedule_html.$wrapper.html(html);
    d.show();
}

function show_asset_details_dialog(frm) {
    const doc = frm.doc;
    const pct = flt(doc.depreciation_percentage_complete || 0, 1);
    const bar_color = pct >= 90 ? '#dc3545' : pct >= 50 ? '#fd7e14' : '#28a745';

    const html = `
        <div style="font-size:13px;line-height:1.8;">
            <div style="display:flex;gap:20px;flex-wrap:wrap;margin-bottom:16px;">
                <div style="flex:1;min-width:200px;">
                    <div style="font-weight:bold;border-bottom:1px solid #dee2e6;margin-bottom:8px;">📦 Asset Info</div>
                    <table style="width:100%">
                        <tr><td style="color:#6c757d;">Code</td><td><b>${doc.asset_code || ''}</b></td></tr>
                        <tr><td style="color:#6c757d;">Category</td><td>${doc.asset_category || ''}</td></tr>
                        <tr><td style="color:#6c757d;">Status</td><td><span class="badge badge-success">${doc.asset_status || ''}</span></td></tr>
                        <tr><td style="color:#6c757d;">Location</td><td>${doc.current_location || '—'}</td></tr>
                        <tr><td style="color:#6c757d;">Department</td><td>${doc.department || '—'}</td></tr>
                        <tr><td style="color:#6c757d;">Custodian</td><td>${doc.custodian || '—'}</td></tr>
                    </table>
                </div>
                <div style="flex:1;min-width:200px;">
                    <div style="font-weight:bold;border-bottom:1px solid #dee2e6;margin-bottom:8px;">💰 Valuation</div>
                    <table style="width:100%">
                        <tr><td style="color:#6c757d;">Purchase Amount</td><td><b>${format_currency(doc.gross_purchase_amount)}</b></td></tr>
                        <tr><td style="color:#6c757d;">Current Gross Value</td><td>${format_currency(doc.current_gross_value)}</td></tr>
                        <tr><td style="color:#6c757d;">Accumulated Dep.</td><td style="color:#c0392b;">${format_currency(doc.current_accumulated_depreciation)}</td></tr>
                        <tr><td style="color:#6c757d;">Net Book Value</td><td><b style="color:#27ae60;">${format_currency(doc.current_net_book_value)}</b></td></tr>
                        <tr><td style="color:#6c757d;">Salvage Value</td><td>${format_currency(doc.salvage_value || 0)}</td></tr>
                    </table>
                </div>
            </div>
            ${doc.calculate_depreciation ? `
            <div style="margin-bottom:16px;">
                <div style="font-weight:bold;border-bottom:1px solid #dee2e6;margin-bottom:8px;">📊 Depreciation Progress</div>
                <div style="display:flex;align-items:center;gap:10px;">
                    <div style="flex:1;background:#e9ecef;border-radius:4px;height:18px;overflow:hidden;">
                        <div style="width:${pct}%;background:${bar_color};height:100%;border-radius:4px;transition:width 0.5s;"></div>
                    </div>
                    <div style="width:50px;text-align:right;font-weight:bold;">${pct}%</div>
                </div>
                <div style="display:flex;gap:16px;margin-top:8px;font-size:12px;color:#6c757d;">
                    <span>Method: <b>${doc.depreciation_method || ''}</b></span>
                    <span>Frequency: <b>${doc.depreciation_frequency || ''}</b></span>
                    <span>Rate: <b>${flt(doc.depreciation_rate, 2)}%</b></span>
                    <span>Next: <b>${doc.next_depreciation_date ? frappe.datetime.str_to_user(doc.next_depreciation_date) : '—'}</b></span>
                </div>
            </div>` : ''}
            <div>
                <div style="font-weight:bold;border-bottom:1px solid #dee2e6;margin-bottom:8px;">📅 Dates</div>
                <div style="display:flex;gap:20px;flex-wrap:wrap;font-size:12px;">
                    <span>Purchased: <b>${doc.purchase_date ? frappe.datetime.str_to_user(doc.purchase_date) : '—'}</b></span>
                    <span>In Use: <b>${doc.available_for_use_date ? frappe.datetime.str_to_user(doc.available_for_use_date) : '—'}</b></span>
                    ${doc.warranty_expiry_date ? `<span>Warranty Expires: <b>${frappe.datetime.str_to_user(doc.warranty_expiry_date)}</b></span>` : ''}
                </div>
            </div>
        </div>`;

    let d = new frappe.ui.Dialog({
        title: __('🔍 {0} — {1}', [doc.asset_code, doc.asset_name]),
        fields: [{ fieldname: 'details_html', fieldtype: 'HTML' }],
        size: 'large'
    });
    d.fields_dict.details_html.$wrapper.html(html);
    d.show();
}

// ============================================================================
// QR CODE
// ============================================================================

function enhance_qr_code_display(frm) {
    if (!frm.doc.qr_code_image) return;

    // Use a dedicated HTML field (qr_code_display) to show the QR panel.
    // This avoids manipulating Frappe's internal field DOM which is unreliable.
    const field = frm.fields_dict['qr_code_display'];
    if (!field) return;  // field must exist in the DocType JSON as HTML fieldtype

    field.$wrapper.html(`
        <div style="text-align:center;padding:16px;border:1px solid #dee2e6;
                    border-radius:8px;background:#f9f9f9;margin-top:4px;">
            <img src="${frm.doc.qr_code_image}"
                 style="width:180px;height:180px;border:2px solid #dee2e6;
                        padding:8px;background:white;border-radius:4px;
                        display:block;margin:0 auto;"
                 alt="QR Code"
                 onerror="this.parentElement.innerHTML='<p class=text-muted>QR image failed to load</p>'">
            <p style="margin-top:8px;font-size:12px;color:#6c757d;margin-bottom:8px;">
                <b>${frm.doc.asset_code}</b>
            </p>
            <div style="display:flex;gap:6px;justify-content:center;flex-wrap:wrap;">
                <button class="btn btn-xs btn-default qr-view-btn">
                    <i class="fa fa-eye"></i> View
                </button>
                <button class="btn btn-xs btn-default qr-print-btn">
                    <i class="fa fa-print"></i> Print
                </button>
                <button class="btn btn-xs btn-default qr-download-btn">
                    <i class="fa fa-download"></i> Download
                </button>
            </div>
        </div>
    `);

    field.$wrapper.find('.qr-view-btn').on('click', () => show_qr_code_dialog(frm));
    field.$wrapper.find('.qr-print-btn').on('click', () => print_qr_code(frm));
    field.$wrapper.find('.qr-download-btn').on('click', () => download_qr_code(frm));
}



function show_qr_code_dialog(frm) {
    if (!frm.doc.qr_code_image) {
        frappe.msgprint(__('No QR Code available. Click "Generate QR Code" to create one.'));
        return;
    }
    let d = new frappe.ui.Dialog({
        title: __('QR Code — {0}', [frm.doc.asset_code]),
        fields: [{ fieldname: 'qr_html', fieldtype: 'HTML' }]
    });
    d.fields_dict.qr_html.$wrapper.html(`
        <div style="text-align:center;padding:20px;">
            <img src="${frm.doc.qr_code_image}" style="width:280px;height:280px;border:2px solid #dee2e6;padding:12px;background:white;">
            <p style="margin-top:12px;"><b>${frm.doc.asset_code}</b><br>
            <small class="text-muted">${frm.doc.asset_name}</small></p>
            <div style="margin-top:12px;">
                <button class="btn btn-sm btn-default" id="qr-print-btn"><i class="fa fa-print"></i> Print</button>
                <button class="btn btn-sm btn-default" id="qr-download-btn"><i class="fa fa-download"></i> Download</button>
            </div>
        </div>
    `);
    d.fields_dict.qr_html.$wrapper.find('#qr-print-btn').on('click', () => { d.hide(); print_qr_code(frm); });
    d.fields_dict.qr_html.$wrapper.find('#qr-download-btn').on('click', () => download_qr_code(frm));
    d.show();
}

function print_qr_code(frm) {
    if (!frm.doc.qr_code_image) return;
    let w = window.open('', '_blank');
    w.document.write(`
        <html><head><title>QR Code — ${frm.doc.asset_code}</title>
        <style>
            body{text-align:center;font-family:Arial,sans-serif;padding:30px;}
            img{width:280px;height:280px;border:2px solid #000;padding:10px;}
            @media print{button{display:none}}
        </style></head>
        <body>
            <h2>${frm.doc.asset_code}</h2>
            <p>${frm.doc.asset_name}</p>
            <img src="${frm.doc.qr_code_image}">
            <p><small>Category: ${frm.doc.asset_category} | Company: ${frm.doc.company}</small></p>
            <br><button onclick="window.print()">🖨️ Print</button>
        </body></html>
    `);
    w.document.close();
}

function download_qr_code(frm) {
    if (!frm.doc.qr_code_image) return;
    let a = document.createElement('a');
    a.href = frm.doc.qr_code_image;
    a.download = `QR_${frm.doc.asset_code}.png`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    frappe.show_alert({ message: __('QR Code downloaded'), indicator: 'green' }, 3);
}

function trigger_qr_generation(frm) {
    frappe.confirm(__('Generate QR Code for this asset? The page will reload.'), () => {
        frappe.call({
            method: 'ecclesia.ecclesia.doctype.fixed_asset.fixed_asset.regenerate_qr_code',
            args: { asset_name: frm.doc.name },
            callback: function(r) {
                if (!r.exc) frm.reload_doc();
            }
        });
    });
}

// ============================================================================
// FIELD DISPLAY AND STATUS
// ============================================================================

function refresh_field_displays(frm) {
    frm.toggle_display('opening_accumulated_depreciation', frm.doc.is_existing_asset);
    frm.toggle_display('depreciation_tab', frm.doc.is_depreciable_asset);
    frm.toggle_display('depreciation_schedule_tab', frm.doc.calculate_depreciation);

    if (frm.doc.docstatus === 1) {
        frm.set_df_property('gross_purchase_amount', 'read_only', 1);
        frm.set_df_property('purchase_date', 'read_only', 1);
        frm.set_df_property('asset_category', 'read_only', 1);
    }
}

function refresh_status_indicators(frm) {
    if (!frm.doc.asset_status) return;

    frm.page.clear_indicator();

    const status_colors = {
        'Draft': 'gray', 'Active': 'green', 'Under Maintenance': 'orange',
        'Disposed': 'red', 'Fully Depreciated': 'blue', 'Scrapped': 'red',
        'Transferred': 'purple', 'Cancelled': 'darkgray'
    };
    frm.page.set_indicator(__(frm.doc.asset_status), status_colors[frm.doc.asset_status] || 'gray');

    if (frm.doc.calculate_depreciation && frm.doc.depreciation_percentage_complete) {
        const pct = flt(frm.doc.depreciation_percentage_complete, 1);
        frm.dashboard.add_indicator(
            __('Depreciation: {0}% Complete', [pct]),
            pct >= 90 ? 'blue' : pct >= 50 ? 'orange' : 'green'
        );
    }

    if (frm.doc.current_net_book_value) {
        frm.dashboard.add_indicator(
            __('Book Value: {0}', [format_currency(frm.doc.current_net_book_value)]),
            'blue'
        );
    }
}

function show_smart_alerts(frm) {
    if (frm.doc.docstatus !== 1) return;

    if (frm.doc.warranty_expiry_date) {
        const days = frappe.datetime.get_day_diff(frm.doc.warranty_expiry_date, frappe.datetime.get_today());
        if (days < 0)
            frappe.show_alert({ message: __('⚠️ Warranty expired {0} days ago', [Math.abs(days)]), indicator: 'red' }, 8);
        else if (days <= 30)
            frappe.show_alert({ message: __('⚠️ Warranty expiring in {0} days', [days]), indicator: 'orange' }, 8);
    }

    if (frm.doc.insurance_expiry_date) {
        const days = frappe.datetime.get_day_diff(frm.doc.insurance_expiry_date, frappe.datetime.get_today());
        if (days < 0)
            frappe.show_alert({ message: __('🚨 Insurance expired {0} days ago!', [Math.abs(days)]), indicator: 'red' }, 8);
        else if (days <= 30)
            frappe.show_alert({ message: __('⚠️ Insurance expiring in {0} days', [days]), indicator: 'orange' }, 8);
    }

    if (frm.doc.next_depreciation_date && frm.doc.calculate_depreciation) {
        const days = frappe.datetime.get_day_diff(frm.doc.next_depreciation_date, frappe.datetime.get_today());
        if (days <= 0)
            frappe.show_alert({ message: __('💵 Depreciation is due — use Post Due Depreciation'), indicator: 'blue' }, 8);
    }
}

function apply_conditional_formatting(frm) {
    if (frm.doc.current_net_book_value && frm.doc.salvage_value) {
        if (flt(frm.doc.current_net_book_value) <= flt(frm.doc.salvage_value) * 1.1) {
            const f = frm.fields_dict['current_net_book_value'];
            if (f && f.wrapper) f.wrapper.style.backgroundColor = '#fff3cd';
        }
    }
}

function apply_schedule_row_colors(frm) {
    setTimeout(() => {
        if (!frm.fields_dict.depreciation_schedules) return;
        const grid = frm.fields_dict.depreciation_schedules.grid;
        if (!grid) return;
        grid.wrapper.find('.grid-row').each((i, row) => {
            $(row).css('background-color', i % 2 === 0 ? '#ffffff' : '#f8f9fa');
        });
    }, 500);
}

// ============================================================================
// DEPRECIATION CALCULATIONS (client side — draft only)
// ============================================================================

function calculate_depreciation_values(frm) {
    if (!frm.doc.calculate_depreciation || !frm.doc.gross_purchase_amount) return;

    if (!frm.doc.salvage_value && !frm.doc.residual_value) {
        const sv = flt(frm.doc.gross_purchase_amount) * 0.10;
        frm.set_value('salvage_value', sv);
        frm.set_value('residual_value', sv);
    }

    const depreciable = flt(frm.doc.gross_purchase_amount) - flt(frm.doc.salvage_value || 0);
    frm.set_value('depreciable_amount', depreciable);

    if (frm.doc.total_number_of_depreciations && frm.doc.depreciation_frequency) {
        const freq = get_frequency_months(frm.doc.depreciation_frequency);
        const total_months = frm.doc.total_number_of_depreciations * freq;
        frm.set_value('total_depreciation_months', total_months);
        if (!frm.doc.useful_life_months) frm.set_value('useful_life_months', total_months);
    }

    if (!frm.doc.depreciation_rate && frm.doc.total_number_of_depreciations) {
        let rate = 0;
        if (frm.doc.depreciation_method === 'Straight Line') {
            rate = 100 / frm.doc.total_number_of_depreciations;
        } else if (frm.doc.depreciation_method === 'Double Declining Balance' && frm.doc.total_depreciation_months) {
            const years = frm.doc.total_depreciation_months / 12;
            rate = (2 / years) * 100;
        } else if (frm.doc.depreciation_method === 'Written Down Value' && frm.doc.total_depreciation_months) {
            const years = frm.doc.total_depreciation_months / 12;
            const ratio = flt(frm.doc.salvage_value) / flt(frm.doc.gross_purchase_amount);
            if (ratio > 0 && ratio < 1) rate = (1 - Math.pow(ratio, 1 / years)) * 100;
        }
        if (rate > 0) frm.set_value('depreciation_rate', flt(rate, 2));
    }
}

function calculate_current_value(frm) {
    if (frm.doc.docstatus === 0) {
        const net = flt(frm.doc.current_gross_value || frm.doc.gross_purchase_amount)
                  - flt(frm.doc.current_accumulated_depreciation || frm.doc.opening_accumulated_depreciation || 0);
        frm.set_value('current_net_book_value', net);
    }
}

function get_frequency_months(frequency) {
    return { 'Monthly': 1, 'Quarterly': 3, 'Half-Yearly': 6, 'Yearly': 12 }[frequency] || 1;
}

// ============================================================================
// DEPRECIATION SCHEDULE GENERATION (client side — draft)
// ============================================================================

function generate_depreciation_schedule(frm) {
    if (!frm.doc.calculate_depreciation) return;
    if (!frm.doc.gross_purchase_amount || frm.doc.gross_purchase_amount <= 0) return;
    if (!frm.doc.depreciation_method || !frm.doc.depreciation_frequency) return;

    if (frm.doc.useful_life_months && (!frm.doc.total_number_of_depreciations || frm.doc.total_number_of_depreciations <= 0)) {
        const freq = get_frequency_months(frm.doc.depreciation_frequency);
        frm.set_value('total_number_of_depreciations', Math.floor(frm.doc.useful_life_months / freq));
    }

    if (!frm.doc.total_number_of_depreciations || frm.doc.total_number_of_depreciations <= 0) return;

    // Existing/migrated assets: ask the server for the cutover date, elapsed
    // periods, and computed opening accumulated depreciation (single source
    // of truth shared with the save-time Python logic), then render the
    // remaining-periods-only preview. New purchases skip straight to the
    // normal full-life preview.
    if (frm.doc.is_existing_asset) {
        frappe.call({
            method: 'ecclesia.ecclesia.doctype.fixed_asset.fixed_asset.get_cutover_info',
            args: {
                company: frm.doc.company,
                is_existing_asset: 1,
                purchase_date: frm.doc.purchase_date,
                available_for_use_date: frm.doc.available_for_use_date,
                gross_purchase_amount: frm.doc.gross_purchase_amount,
                salvage_value: frm.doc.salvage_value,
                depreciation_method: frm.doc.depreciation_method,
                depreciation_rate: frm.doc.depreciation_rate,
                total_number_of_depreciations: frm.doc.total_number_of_depreciations,
                depreciation_frequency: frm.doc.depreciation_frequency,
                total_depreciation_months: frm.doc.total_depreciation_months,
                opening_accumulated_depreciation: frm.doc.opening_accumulated_depreciation
            },
            callback: function(r) {
                if (!r.message) return;
                const info = r.message;

                if (info.cutover_date) {
                    frm.set_value('depreciation_start_date', info.cutover_date);
                    frm.set_value('next_depreciation_date', info.cutover_date);
                }
                frm.set_value('elapsed_depreciation_periods', info.elapsed_periods || 0);
                if (!frm.doc.opening_accumulated_depreciation) {
                    frm.set_value('opening_accumulated_depreciation', info.computed_opening_accumulated_depreciation || 0);
                }

                render_schedule_preview(frm, info.elapsed_periods || 0);
            }
        });
        return;
    }

    frm.set_value('elapsed_depreciation_periods', 0);
    render_schedule_preview(frm, 0);
}

function render_schedule_preview(frm, elapsed) {
    const start_date = frm.doc.depreciation_start_date || frm.doc.available_for_use_date || frm.doc.purchase_date;
    if (!start_date) return;

    const schedule_fn = {
        'Straight Line': calculate_straight_line_schedule,
        'Written Down Value': calculate_wdv_schedule,
        'Double Declining Balance': calculate_ddb_schedule,
        'Sum of Years Digits': calculate_sum_of_years_digits_schedule,
    }[frm.doc.depreciation_method];

    if (!schedule_fn) return;

    const schedule = schedule_fn(frm, start_date, elapsed || 0);
    if (!schedule || !schedule.length) return;

    frm.clear_table('depreciation_schedules');
    schedule.forEach(entry => {
        let row = frm.add_child('depreciation_schedules');
        row.schedule_date = entry.schedule_date;
        row.opening_balance = entry.opening_balance;
        row.depreciation_amount = entry.depreciation_amount;
        row.closing_balance = entry.closing_balance;
        row.accumulated_depreciation = entry.accumulated_depreciation;
    });

    frm.refresh_field('depreciation_schedules');
    apply_schedule_row_colors(frm);
    if (schedule.length) frm.set_value('next_depreciation_date', schedule[0].schedule_date);
    frappe.show_alert({ message: __('✅ {0} depreciation periods generated', [schedule.length]), indicator: 'green' }, 3);
}

function add_schedule_date(start, period_index, freq_months) {
    // Compute date by adding freq_months * period_index to start
    return frappe.datetime.add_months(start, freq_months * period_index);
}

function calculate_straight_line_schedule(frm, start_date, elapsed) {
    elapsed = elapsed || 0;
    const n = cint(frm.doc.total_number_of_depreciations);
    const remaining = Math.max(n - elapsed, 0);
    if (remaining <= 0) return [];

    const freq = get_frequency_months(frm.doc.depreciation_frequency);
    const depreciable = flt(frm.doc.gross_purchase_amount) - flt(frm.doc.opening_accumulated_depreciation || 0) - flt(frm.doc.salvage_value || 0);
    if (depreciable <= 0) return [];

    const per_period = flt(depreciable / remaining, 2);
    let opening = flt(frm.doc.gross_purchase_amount) - flt(frm.doc.opening_accumulated_depreciation || 0);
    let accumulated = flt(frm.doc.opening_accumulated_depreciation || 0);
    const schedule = [];

    for (let i = 1; i <= remaining; i++) {
        const absolute_period = elapsed + i;
        let amount = absolute_period === n ? (opening - flt(frm.doc.salvage_value || 0)) : per_period;
        if (opening - amount < flt(frm.doc.salvage_value || 0)) amount = opening - flt(frm.doc.salvage_value || 0);
        if (amount <= 0) break;
        accumulated += amount;
        const closing = opening - amount;
        schedule.push({
            schedule_date: add_schedule_date(start_date, i - 1, freq),
            opening_balance: flt(opening, 2),
            depreciation_amount: flt(amount, 2),
            closing_balance: flt(closing, 2),
            accumulated_depreciation: flt(accumulated, 2),
        });
        opening = closing;
        if (opening <= flt(frm.doc.salvage_value || 0)) break;
    }
    return schedule;
}

function calculate_wdv_schedule(frm, start_date, elapsed) {
    elapsed = elapsed || 0;
    const n = cint(frm.doc.total_number_of_depreciations);
    const remaining = Math.max(n - elapsed, 0);
    if (remaining <= 0) return [];

    const freq = get_frequency_months(frm.doc.depreciation_frequency);
    const period_rate = (flt(frm.doc.depreciation_rate) / 100) * (freq / 12);
    let opening = flt(frm.doc.gross_purchase_amount) - flt(frm.doc.opening_accumulated_depreciation || 0);
    let accumulated = flt(frm.doc.opening_accumulated_depreciation || 0);
    const schedule = [];

    for (let i = 1; i <= remaining; i++) {
        let amount = opening * period_rate;
        if (opening - amount < flt(frm.doc.salvage_value || 0)) amount = opening - flt(frm.doc.salvage_value || 0);
        if (amount <= 0) break;
        accumulated += amount;
        const closing = opening - amount;
        schedule.push({
            schedule_date: add_schedule_date(start_date, i - 1, freq),
            opening_balance: flt(opening, 2),
            depreciation_amount: flt(amount, 2),
            closing_balance: flt(closing, 2),
            accumulated_depreciation: flt(accumulated, 2),
        });
        opening = closing;
        if (opening <= flt(frm.doc.salvage_value || 0)) break;
    }
    return schedule;
}

function calculate_ddb_schedule(frm, start_date, elapsed) {
    elapsed = elapsed || 0;
    const n = cint(frm.doc.total_number_of_depreciations);
    const remaining = Math.max(n - elapsed, 0);
    if (remaining <= 0) return [];

    const freq = get_frequency_months(frm.doc.depreciation_frequency);
    const years = flt(frm.doc.total_depreciation_months || 0) / 12;
    const period_rate = years > 0 ? (2 / years) * (freq / 12) : 0;
    let opening = flt(frm.doc.gross_purchase_amount) - flt(frm.doc.opening_accumulated_depreciation || 0);
    let accumulated = flt(frm.doc.opening_accumulated_depreciation || 0);
    const schedule = [];

    for (let i = 1; i <= remaining; i++) {
        const absolute_period = elapsed + i;
        const remaining_from_here = n - absolute_period + 1;
        const ddb = opening * period_rate;
        const sl = remaining_from_here > 0 ? (opening - flt(frm.doc.salvage_value || 0)) / remaining_from_here : 0;
        let amount = Math.max(ddb, sl);
        if (opening - amount < flt(frm.doc.salvage_value || 0)) amount = opening - flt(frm.doc.salvage_value || 0);
        if (amount <= 0) break;
        accumulated += amount;
        const closing = opening - amount;
        schedule.push({
            schedule_date: add_schedule_date(start_date, i - 1, freq),
            opening_balance: flt(opening, 2),
            depreciation_amount: flt(amount, 2),
            closing_balance: flt(closing, 2),
            accumulated_depreciation: flt(accumulated, 2),
        });
        opening = closing;
        if (opening <= flt(frm.doc.salvage_value || 0)) break;
    }
    return schedule;
}

function calculate_sum_of_years_digits_schedule(frm, start_date, elapsed) {
    elapsed = elapsed || 0;
    const n = cint(frm.doc.total_number_of_depreciations);
    const remaining = Math.max(n - elapsed, 0);
    if (remaining <= 0) return [];

    const freq = get_frequency_months(frm.doc.depreciation_frequency);
    const sum_digits = (n * (n + 1)) / 2;
    const depreciable = flt(frm.doc.gross_purchase_amount) - flt(frm.doc.opening_accumulated_depreciation || 0) - flt(frm.doc.salvage_value || 0);
    if (depreciable <= 0) return [];

    let opening = flt(frm.doc.gross_purchase_amount) - flt(frm.doc.opening_accumulated_depreciation || 0);
    let accumulated = flt(frm.doc.opening_accumulated_depreciation || 0);
    const schedule = [];

    for (let i = 1; i <= remaining; i++) {
        const absolute_period = elapsed + i;
        const remaining_life = n - absolute_period + 1;
        let amount = (remaining_life / sum_digits) * depreciable;
        if (opening - amount < flt(frm.doc.salvage_value || 0)) amount = opening - flt(frm.doc.salvage_value || 0);
        if (amount <= 0) break;
        accumulated += amount;
        const closing = opening - amount;
        schedule.push({
            schedule_date: add_schedule_date(start_date, i - 1, freq),
            opening_balance: flt(opening, 2),
            depreciation_amount: flt(amount, 2),
            closing_balance: flt(closing, 2),
            accumulated_depreciation: flt(accumulated, 2),
        });
        opening = closing;
        if (opening <= flt(frm.doc.salvage_value || 0)) break;
    }
    return schedule;
}

// ============================================================================
// ACTIONS
// ============================================================================

function recalculate_depreciation(frm) {
    calculate_depreciation_values(frm);
    calculate_current_value(frm);
    generate_depreciation_schedule(frm);
    frappe.show_alert({ message: __('✅ Depreciation recalculated'), indicator: 'green' }, 3);
}

function recalculate_submitted_asset(frm) {
    frappe.confirm(__('Recalculate depreciation values for this asset?'), () => {
        frappe.call({
            method: 'ecclesia.ecclesia.doctype.fixed_asset.fixed_asset.recalculate_depreciation',
            args: { asset_name: frm.doc.name },
            callback: function(r) {
                if (!r.exc) frm.reload_doc();
            }
        });
    });
}

function post_due_depreciation(frm) {
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Depreciation Schedule Details',
            filters: {
                parent: frm.doc.name,
                schedule_date: ['<=', frappe.datetime.get_today()],
                status: 'Scheduled'
            },
            fields: ['name', 'schedule_date', 'depreciation_amount']
        },
        callback: function(r) {
            if (!r.message || !r.message.length) {
                frappe.msgprint(__('No due depreciation schedules found.'));
                return;
            }
            frappe.confirm(__('Post {0} due depreciation entries?', [r.message.length]), () => {
                const promises = r.message.map(s => frappe.call({
                    method: 'ecclesia.ecclesia.doctype.fixed_asset.fixed_asset.post_depreciation_entry',
                    args: { schedule_name: s.name }
                }));
                Promise.all(promises).then(() => {
                    frm.reload_doc();
                    frappe.show_alert({ message: __('✅ All entries posted'), indicator: 'green' }, 5);
                });
            });
        }
    });
}

function split_asset_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Split Asset'),
        fields: [
            { label: __('Current Quantity'), fieldname: 'current_qty', fieldtype: 'Data', read_only: 1, default: frm.doc.asset_quantity },
            { label: __('Split Quantity'), fieldname: 'split_qty', fieldtype: 'Int', reqd: 1, description: __('Max: {0}', [frm.doc.asset_quantity - 1]) }
        ],
        primary_action_label: __('Split'),
        primary_action: function(values) {
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.fixed_asset.fixed_asset.split_asset',
                args: { asset: frm.doc.name, split_qty: values.split_qty },
                callback: function(r) { if (!r.exc) { d.hide(); frm.reload_doc(); } }
            });
        }
    });
    d.show();
}

// ============================================================================
// CATCH-UP DEPRECIATION
// ============================================================================

function show_catchup_dialog(frm) {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.fixed_asset.fixed_asset.get_outstanding_depreciation_schedules',
        args: { asset_name: frm.doc.name, up_to_date: frappe.datetime.get_today() },
        freeze: true,
        freeze_message: __('⏳ Checking outstanding schedules...'),
        callback(r) {
            if (!r.message) return;
            const data = r.message;

            if (data.count === 0) {
                frappe.msgprint({ title: __('All Up to Date'), message: __('✅ All depreciation schedules are up to date.'), indicator: 'green' });
                return;
            }

            const rows = data.schedules.map(s => `
                <tr>
                    <td>${frappe.datetime.str_to_user(s.schedule_date)}</td>
                    <td style="text-align:right">${format_currency(s.depreciation_amount)}</td>
                    <td style="text-align:right">${format_currency(s.accumulated_depreciation)}</td>
                    <td style="text-align:right">${format_currency(s.closing_balance || 0)}</td>
                </tr>`).join('');

            const preview_html = `
                <div style="background:#fff3cd;padding:8px 12px;border-radius:4px;margin-bottom:12px;font-size:13px;">
                    ⚠ <b>${data.count} outstanding period(s)</b> — Total: <b>${format_currency(data.total_amount)}</b>
                </div>
                <div style="max-height:260px;overflow-y:auto;">
                <table class="table table-bordered table-condensed" style="font-size:12px;margin:0;">
                    <thead style="background:#f5f5f5;">
                        <tr><th>Period Date</th><th style="text-align:right">Depreciation</th><th style="text-align:right">Accumulated</th><th style="text-align:right">Closing Balance</th></tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table></div>`;

            const d = new frappe.ui.Dialog({
                title: __('📅 Post Catch-up Depreciation — {0}', [data.asset_code]),
                fields: [
                    { fieldtype: 'HTML', fieldname: 'preview', options: preview_html },
                    { fieldtype: 'Section Break', label: __('Posting Options') },
                    { fieldtype: 'Date', fieldname: 'up_to_date', label: __('Post Up To Date'), default: frappe.datetime.get_today(), description: __('Post all unposted schedules on or before this date.') },
                    { fieldtype: 'Column Break' },
                    { fieldtype: 'Select', fieldname: 'post_as', label: __('Posting Mode'),
                      options: 'individual\nconsolidated',
                      default: 'individual',
                      description: __('Individual: one JE per period. Consolidated: single combined JE.') },
                ],
                primary_action_label: __('✅ Post {0} Entries', [data.count]),
                primary_action(values) {
                    d.hide();
                    frappe.confirm(
                        __('Post <b>{0}</b> catch-up entries for <b>{1}</b>?<br>Total: <b>{2}</b>', [data.count, data.asset_code, format_currency(data.total_amount)]),
                        () => {
                            frappe.call({
                                method: 'ecclesia.ecclesia.doctype.fixed_asset.fixed_asset.post_catchup_depreciation',
                                args: { asset_name: frm.doc.name, up_to_date: values.up_to_date, post_as: values.post_as },
                                freeze: true,
                                freeze_message: __('⏳ Posting catch-up entries...'),
                                callback(r) {
                                    if (r.message && r.message.success) {
                                        frm.reload_doc();
                                        frappe.show_alert({
                                            message: __('✅ Posted {0} depreciation entries', [r.message.posted || data.count]),
                                            indicator: 'green'
                                        }, 5);
                                    }
                                }
                            });
                        }
                    );
                }
            });
            d.show();
        }
    });
}

// ============================================================================
// LIST VIEW — BULK CATCH-UP
// ============================================================================

frappe.listview_settings['Fixed Asset'] = frappe.listview_settings['Fixed Asset'] || {};

Object.assign(frappe.listview_settings['Fixed Asset'], {
    onload(listview) {
        listview.page.add_action_item(__('📅 Post Catch-up Depreciation'), () => show_bulk_catchup_dialog(listview));
    }
});

function show_bulk_catchup_dialog(listview) {
    const selected = listview.get_checked_items();

    const d = new frappe.ui.Dialog({
        title: __('📅 Bulk Catch-up Depreciation'),
        fields: [
            {
                fieldtype: 'HTML', fieldname: 'scope_info',
                options: selected.length
                    ? `<div style="background:#d4edda;padding:8px 12px;border-radius:4px;font-size:13px;">✅ Will process <b>${selected.length} selected asset(s)</b>.</div>`
                    : `<div style="background:#fff3cd;padding:8px 12px;border-radius:4px;font-size:13px;">⚠ No assets selected — will process <b>all submitted depreciable assets</b>.</div>`
            },
            { fieldtype: 'Section Break', label: __('Posting Options') },
            { fieldtype: 'Date', fieldname: 'up_to_date', label: __('Post Up To Date'), default: frappe.datetime.get_today(), reqd: 1 },
            { fieldtype: 'Column Break' },
            { fieldtype: 'Select', fieldname: 'post_as', label: __('Posting Mode'), options: 'individual\nconsolidated', default: 'individual' },
        ],
        primary_action_label: selected.length ? __('✅ Post for {0} Asset(s)', [selected.length]) : __('✅ Post for All Assets'),
        primary_action(values) {
            d.hide();
            if (selected.length) {
                run_bulk_for_selected(selected, values.up_to_date, values.post_as, listview);
            } else {
                frappe.confirm(__('Post catch-up depreciation for all submitted depreciable assets up to {0}?', [frappe.datetime.str_to_user(values.up_to_date)]), () => {
                    frappe.call({
                        method: 'ecclesia.ecclesia.doctype.fixed_asset.fixed_asset.bulk_post_catchup_depreciation',
                        args: { up_to_date: values.up_to_date, post_as: values.post_as },
                        freeze: true,
                        freeze_message: __('⏳ Posting...'),
                        callback(r) {
                            if (r.message) {
                                listview.refresh();
                                frappe.show_alert({ message: __('✅ Bulk catch-up complete'), indicator: 'green' }, 5);
                            }
                        }
                    });
                });
            }
        }
    });
    d.show();
}

function run_bulk_for_selected(selected, up_to_date, post_as, listview) {
    frappe.confirm(
        __('Post catch-up for <b>{0} selected asset(s)</b> up to <b>{1}</b>?', [selected.length, frappe.datetime.str_to_user(up_to_date)]),
        () => {
            let posted = 0, errors = 0, processed = 0;

            const progress_d = new frappe.ui.Dialog({
                title: __('⏳ Posting...'),
                fields: [{ fieldtype: 'HTML', fieldname: 'prog', options: `<div id="bcp"><p>Starting...</p><div class="progress"><div class="progress-bar" style="width:0%"></div></div></div>` }]
            });
            progress_d.show();
            progress_d.get_close_btn().hide();

            function update() {
                const pct = Math.round((processed / selected.length) * 100);
                progress_d.fields_dict.prog.$wrapper.find('.progress-bar').css('width', pct + '%');
                progress_d.fields_dict.prog.$wrapper.find('p').html(
                    `Processing ${processed}/${selected.length}... ✅ ${posted} posted ${errors ? '❌ ' + errors + ' errors' : ''}`
                );
            }

            function next(i) {
                if (i >= selected.length) {
                    progress_d.hide();
                    frappe.msgprint({ title: __('Complete'), message: __('Processed: <b>{0}</b>, Posted: <b>{1}</b>, Errors: <b>{2}</b>', [selected.length, posted, errors]), indicator: errors ? 'orange' : 'green' });
                    listview.refresh();
                    return;
                }
                frappe.call({
                    method: 'ecclesia.ecclesia.doctype.fixed_asset.fixed_asset.post_catchup_depreciation',
                    args: { asset_name: selected[i].name, up_to_date, post_as },
                    callback(r) {
                        processed++;
                        if (r.message && r.message.success) posted += (r.message.posted || 0);
                        else errors++;
                        update();
                        next(i + 1);
                    },
                    error() { processed++; errors++; update(); next(i + 1); }
                });
            }
            next(0);
        }
    );
}

// ============================================================================
// HELPERS
// ============================================================================

function format_currency(value) {
    return frappe.format(flt(value || 0), { fieldtype: 'Currency' });
}