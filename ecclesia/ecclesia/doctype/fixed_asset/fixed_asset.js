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
        render_dashboard(frm);
    },

    refresh: function(frm) {
        frm.page.clear_inner_toolbar();
        add_custom_buttons(frm);
        refresh_field_displays(frm);
        refresh_status_indicators(frm);
        show_smart_alerts(frm);
        apply_conditional_formatting(frm);
        apply_schedule_row_colors(frm);
        render_dashboard(frm);

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
        render_dashboard(frm);
    },

    gross_purchase_amount: function(frm) {
        calculate_depreciation_values(frm);
        calculate_current_value(frm);
        if (frm.doc.docstatus === 0 && frm.doc.calculate_depreciation)
            setTimeout(() => generate_depreciation_schedule(frm), 300);
        render_dashboard(frm);
    },

    salvage_value: function(frm) {
        if (frm.doc.salvage_value != frm.doc.residual_value)
            frm.set_value('residual_value', frm.doc.salvage_value);
        calculate_depreciation_values(frm);
        if (frm.doc.docstatus === 0 && frm.doc.calculate_depreciation)
            setTimeout(() => generate_depreciation_schedule(frm), 300);
        render_dashboard(frm);
    },

    residual_value: function(frm) {
        if (frm.doc.residual_value != frm.doc.salvage_value)
            frm.set_value('salvage_value', frm.doc.residual_value);
        calculate_depreciation_values(frm);
        if (frm.doc.docstatus === 0 && frm.doc.calculate_depreciation)
            setTimeout(() => generate_depreciation_schedule(frm), 300);
        render_dashboard(frm);
    },

    opening_accumulated_depreciation: function(frm) {
        calculate_current_value(frm);
        if (frm.doc.docstatus === 0 && frm.doc.calculate_depreciation && frm.doc.is_existing_asset)
            setTimeout(() => generate_depreciation_schedule(frm), 300);
        render_dashboard(frm);
    },

    is_depreciable_asset: function(frm) {
        if (frm.doc.is_depreciable_asset) frm.set_value('calculate_depreciation', 1);
        frm.trigger('refresh');
        render_dashboard(frm);
    },

    calculate_depreciation: function(frm) {
        if (frm.doc.calculate_depreciation) {
            calculate_depreciation_values(frm);
            if (frm.doc.docstatus === 0)
                setTimeout(() => generate_depreciation_schedule(frm), 300);
        }
        frm.trigger('refresh');
        render_dashboard(frm);
    },

    depreciation_method: function(frm) {
        calculate_depreciation_values(frm);
        if (frm.doc.docstatus === 0 && frm.doc.calculate_depreciation)
            setTimeout(() => generate_depreciation_schedule(frm), 300);
        render_dashboard(frm);
    },

    total_number_of_depreciations: function(frm) {
        calculate_depreciation_values(frm);
        if (frm.doc.docstatus === 0 && frm.doc.calculate_depreciation)
            setTimeout(() => generate_depreciation_schedule(frm), 300);
        render_dashboard(frm);
    },

    depreciation_frequency: function(frm) {
        if (frm.doc.useful_life_months && frm.doc.depreciation_frequency) {
            const freq = get_frequency_months(frm.doc.depreciation_frequency);
            frm.set_value('total_number_of_depreciations', Math.floor(frm.doc.useful_life_months / freq));
        }
        calculate_depreciation_values(frm);
        if (frm.doc.docstatus === 0 && frm.doc.calculate_depreciation)
            setTimeout(() => generate_depreciation_schedule(frm), 300);
        render_dashboard(frm);
    },

    useful_life_months: function(frm) {
        if (frm.doc.useful_life_months && frm.doc.depreciation_frequency) {
            const freq = get_frequency_months(frm.doc.depreciation_frequency);
            frm.set_value('total_number_of_depreciations', Math.floor(frm.doc.useful_life_months / freq));
        }
        render_dashboard(frm);
    },

    depreciation_start_date: function(frm) {
        if (frm.doc.docstatus === 0 && frm.doc.calculate_depreciation)
            setTimeout(() => generate_depreciation_schedule(frm), 300);
        render_dashboard(frm);
    },

    available_for_use_date: function(frm) {
        if (!frm.doc.depreciation_start_date && frm.doc.calculate_depreciation)
            frm.set_value('depreciation_start_date', frm.doc.available_for_use_date);
        render_dashboard(frm);
    },

    is_existing_asset: function(frm) {
        if (frm.doc.is_existing_asset) {
            frappe.msgprint({
                title: __('Existing Asset Setup'), indicator: 'blue',
                message: __('Please enter the Opening Accumulated Depreciation for this existing asset.')
            });
        }
        render_dashboard(frm);
    }
});

frappe.ui.form.on('Depreciation Schedule Details', {
    depreciation_schedules_add: function(frm, cdt, cdn) {}
});

// ============================================================================
// DASHBOARD RENDERING
// ============================================================================

function render_dashboard(frm) {
    if (!frm.fields_dict['html_dashboard']) return;

    var container = frm.fields_dict['html_dashboard'].$wrapper;
    var doc = frm.doc;

    var gross       = flt(doc.gross_purchase_amount);
    var accumulated = flt(doc.current_accumulated_depreciation || 0);
    var net_book    = flt(doc.current_net_book_value || gross - accumulated);
    var salvage     = flt(doc.salvage_value || 0);
    var depPct      = gross > 0 ? ((accumulated / gross) * 100) : 0;

    var statusConfig = {
        'Draft':              { color: '#6b7280', bg: '#f3f4f6',  icon: '📝' },
        'Active':             { color: '#059669', bg: '#d1fae5',  icon: '✅' },
        'Under Maintenance':  { color: '#f59e0b', bg: '#fef3c7',  icon: '🔧' },
        'Disposed':           { color: '#dc2626', bg: '#fee2e2',  icon: '🗑️' },
        'Fully Depreciated':  { color: '#3b82f6', bg: '#dbeafe',  icon: '📉' },
        'Transferred':        { color: '#8b5cf6', bg: '#ede9fe',  icon: '📦' }
    };
    var st = statusConfig[doc.asset_status] || { color: '#6b7280', bg: '#f3f4f6', icon: '📄' };

    var html = `
    <style>
        .fa-db { display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); gap:15px; padding:10px 0; }
        .fa-card { border-radius:12px; padding:20px; color:#fff; box-shadow:0 4px 15px rgba(0,0,0,0.1); position:relative; overflow:hidden; }
        .fa-card::after { content:''; position:absolute; top:-30px; right:-30px; width:100px; height:100px; background:rgba(255,255,255,0.1); border-radius:50%; }
        .fa-card.blue   { background:linear-gradient(135deg,#667eea,#764ba2); }
        .fa-card.green  { background:linear-gradient(135deg,#11998e,#38ef7d); }
        .fa-card.orange { background:linear-gradient(135deg,#f093fb,#f5576c); }
        .fa-card.teal   { background:linear-gradient(135deg,#4facfe,#00f2fe); color:#1a202c; }
        .fa-card h4     { font-size:11px; text-transform:uppercase; letter-spacing:1px; opacity:0.9; margin:0 0 10px; font-weight:600; position:relative; z-index:1; }
        .fa-card .big   { font-size:26px; font-weight:700; margin-bottom:4px; position:relative; z-index:1; }
        .fa-card .sub   { font-size:11px; opacity:0.85; position:relative; z-index:1; }
        .fa-card .row   { display:flex; justify-content:space-between; margin-top:7px; font-size:12px; position:relative; z-index:1; }
        .fa-card .row .lbl { opacity:0.8; }
        .fa-card .row .val { font-weight:600; }
        .fa-badge       { display:inline-block; padding:4px 10px; border-radius:12px; font-size:10px; font-weight:600; margin-bottom:8px; position:relative; z-index:1; }
        .fa-bar         { height:6px; background:rgba(255,255,255,0.3); border-radius:3px; margin-top:10px; overflow:hidden; position:relative; z-index:1; }
        .fa-bar-fill    { height:100%; border-radius:3px; background:rgba(255,255,255,0.9); }
        .fa-grid        { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:12px; position:relative; z-index:1; }
        .fa-stat        { text-align:center; padding:10px 8px; background:rgba(255,255,255,0.2); border-radius:8px; }
        .fa-stat .n     { font-size:18px; font-weight:700; }
        .fa-stat .l     { font-size:9px; text-transform:uppercase; opacity:0.85; margin-top:2px; }
    </style>

    <div class="fa-db">
        <div class="fa-card blue">
            <h4>📋 Asset Information</h4>
            <span class="fa-badge" style="background:${st.bg};color:${st.color}">${st.icon} ${doc.asset_status || 'Draft'}</span>
            <div class="big" style="font-size:18px;word-break:break-all;">${doc.asset_code || 'N/A'}</div>
            <div class="sub">${doc.asset_name || 'N/A'}</div>
            <div class="row"><span class="lbl">Category</span><span class="val">${doc.asset_category || '-'}</span></div>
            <div class="row"><span class="lbl">Location</span><span class="val">${doc.current_location || '-'}</span></div>
            <div class="row"><span class="lbl">Department</span><span class="val">${doc.department || '-'}</span></div>
            <div class="row"><span class="lbl">Custodian</span><span class="val">${doc.custodian || '-'}</span></div>
        </div>

        <div class="fa-card green">
            <h4>💰 Financial Overview</h4>
            <div class="big">${format_currency(gross)}</div>
            <div class="sub">Gross Purchase Amount</div>
            <div class="row" style="margin-top:12px;"><span class="lbl">Net Book Value</span><span class="val">${format_currency(net_book)}</span></div>
            <div class="row"><span class="lbl">Accumulated Dep.</span><span class="val" style="color:#ff6b6b;">${format_currency(accumulated)}</span></div>
            <div class="row"><span class="lbl">Salvage Value</span><span class="val">${format_currency(salvage)}</span></div>
            <div class="fa-bar"><div class="fa-bar-fill" style="width:${Math.min(100,depPct).toFixed(1)}%"></div></div>
            <div style="text-align:right;font-size:10px;margin-top:4px;opacity:0.9;">${depPct.toFixed(1)}% depreciated</div>
        </div>

        ${doc.calculate_depreciation ? `
        <div class="fa-card orange">
            <h4>📊 Depreciation Status</h4>
            <div class="big" style="font-size:22px;">${doc.depreciation_method || 'N/A'}</div>
            <div class="sub">${doc.depreciation_frequency || 'N/A'}</div>
            <div class="fa-grid">
                <div class="fa-stat"><div class="n">${flt(doc.depreciation_rate||0,2)}%</div><div class="l">Rate</div></div>
                <div class="fa-stat"><div class="n">${cint(doc.total_number_of_depreciations)}</div><div class="l">Periods</div></div>
                <div class="fa-stat"><div class="n">${flt(doc.depreciation_percentage_complete||0,1)}%</div><div class="l">Complete</div></div>
                <div class="fa-stat"><div class="n">${doc.useful_life_months||0}</div><div class="l">Life (mo)</div></div>
            </div>
            ${doc.next_depreciation_date ? `<div class="row" style="margin-top:10px;border-top:1px solid rgba(255,255,255,0.2);padding-top:8px;"><span class="lbl">Next Dep.</span><span class="val">${frappe.datetime.str_to_user(doc.next_depreciation_date)}</span></div>` : ''}
        </div>` : ''}

        <div class="fa-card teal">
            <h4>📅 Key Dates & Info</h4>
            <div class="row" style="margin-top:10px;"><span class="lbl">Purchase Date</span><span class="val">${doc.purchase_date ? frappe.datetime.str_to_user(doc.purchase_date) : 'N/A'}</span></div>
            <div class="row"><span class="lbl">Available for Use</span><span class="val">${doc.available_for_use_date ? frappe.datetime.str_to_user(doc.available_for_use_date) : 'N/A'}</span></div>
            ${doc.depreciation_start_date ? `<div class="row"><span class="lbl">Dep. Start Date</span><span class="val">${frappe.datetime.str_to_user(doc.depreciation_start_date)}</span></div>` : ''}
            ${doc.warranty_expiry_date ? `<div class="row"><span class="lbl">Warranty Expires</span><span class="val">${frappe.datetime.str_to_user(doc.warranty_expiry_date)}</span></div>` : ''}
            ${doc.insurance_expiry_date ? `<div class="row"><span class="lbl">Insurance Expires</span><span class="val">${frappe.datetime.str_to_user(doc.insurance_expiry_date)}</span></div>` : ''}
            <div class="row"><span class="lbl">Company</span><span class="val">${doc.company || 'N/A'}</span></div>
        </div>
    </div>`;

    container.html(html);
}

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
        frm.add_custom_button(__('🔄 Recalculate'), () => recalculate_submitted_asset(frm), __('Actions'));

        if (frm.doc.qr_code_image) {
            frm.add_custom_button(__('👁️ View QR Code'), () => show_qr_code_dialog(frm), __('QR Code'));
            frm.add_custom_button(__('🖨️ Print QR Code'), () => print_qr_code(frm), __('QR Code'));
            frm.add_custom_button(__('📥 Download QR'), () => download_qr_code(frm), __('QR Code'));
        } else {
            frm.add_custom_button(__('🔄 Generate QR Code'), () => trigger_qr_generation(frm), __('QR Code'));
        }

        frm.add_custom_button(__('📋 View History'), () => show_asset_history(frm), __('View'));
        frm.add_custom_button(__('📅 View Schedule'), () => show_depreciation_schedule(frm), __('View'));
        frm.add_custom_button(__('🔍 Asset Details'), () => show_asset_details_dialog(frm), __('View'));

        if (frm.doc.calculate_depreciation) {
            // Check for regular due entries
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

            // Catch-up (for partially missed periods)
            frm.add_custom_button(__('📅 Post Catch-up Depreciation'), () => show_catchup_dialog(frm), __('Depreciation'));

            // ── NEW: Backdated depreciation for assets registered late ──
            frm.add_custom_button(__('⏮️ Post Backdated Depreciation'), () => show_backdated_depreciation_dialog(frm), __('Depreciation'));
        }
    }
}

// ============================================================================
// VIEW BUTTON IMPLEMENTATIONS
// ============================================================================

function show_asset_history(frm) {
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
        html = '<p class="text-muted text-center" style="padding:20px">No depreciation schedule found.</p>';
    } else {
        const posted  = rows.filter(r => r.journal_entry).length;
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
                    <tr><th>#</th><th>Period Date</th><th>Opening</th><th>Depreciation</th><th>Closing</th><th>Accumulated</th><th>Status</th></tr>
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
                        <div style="width:${pct}%;background:${bar_color};height:100%;border-radius:4px;"></div>
                    </div>
                    <div style="width:50px;text-align:right;font-weight:bold;">${pct}%</div>
                </div>
                <div style="display:flex;gap:16px;margin-top:8px;font-size:12px;color:#6c757d;">
                    <span>Method: <b>${doc.depreciation_method || ''}</b></span>
                    <span>Frequency: <b>${doc.depreciation_frequency || ''}</b></span>
                    <span>Rate: <b>${flt(doc.depreciation_rate, 2)}%</b></span>
                </div>
            </div>` : ''}
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
// QR CODE FUNCTIONS
// ============================================================================

function enhance_qr_code_display(frm) {
    if (!frm.doc.qr_code_image) return;
    const field = frm.fields_dict['qr_code_display'];
    if (!field) return;

    field.$wrapper.html(`
        <div style="text-align:center;padding:16px;border:1px solid #dee2e6;border-radius:8px;background:#f9f9f9;margin-top:4px;">
            <img src="${frm.doc.qr_code_image}" style="width:180px;height:180px;border:2px solid #dee2e6;padding:8px;background:white;border-radius:4px;display:block;margin:0 auto;">
            <p style="margin-top:8px;font-size:12px;color:#6c757d;margin-bottom:8px;"><b>${frm.doc.asset_code}</b></p>
            <div style="display:flex;gap:6px;justify-content:center;flex-wrap:wrap;">
                <button class="btn btn-xs btn-default qr-view-btn"><i class="fa fa-eye"></i> View</button>
                <button class="btn btn-xs btn-default qr-print-btn"><i class="fa fa-print"></i> Print</button>
                <button class="btn btn-xs btn-default qr-download-btn"><i class="fa fa-download"></i> Download</button>
            </div>
        </div>
    `);

    field.$wrapper.find('.qr-view-btn').on('click', () => show_qr_code_dialog(frm));
    field.$wrapper.find('.qr-print-btn').on('click', () => print_qr_code(frm));
    field.$wrapper.find('.qr-download-btn').on('click', () => download_qr_code(frm));
}

function show_qr_code_dialog(frm) {
    if (!frm.doc.qr_code_image) { frappe.msgprint(__('No QR Code available.')); return; }
    let d = new frappe.ui.Dialog({
        title: __('QR Code — {0}', [frm.doc.asset_code]),
        fields: [{ fieldname: 'qr_html', fieldtype: 'HTML' }]
    });
    d.fields_dict.qr_html.$wrapper.html(`
        <div style="text-align:center;padding:20px;">
            <img src="${frm.doc.qr_code_image}" style="width:280px;height:280px;border:2px solid #dee2e6;padding:12px;background:white;">
            <p style="margin-top:12px;"><b>${frm.doc.asset_code}</b><br><small class="text-muted">${frm.doc.asset_name}</small></p>
        </div>
    `);
    d.show();
}

function print_qr_code(frm) {
    if (!frm.doc.qr_code_image) return;
    let w = window.open('', '_blank');
    w.document.write(`<html><head><title>QR Code</title></head><body style="text-align:center;padding:30px;"><h2>${frm.doc.asset_code}</h2><img src="${frm.doc.qr_code_image}" style="width:280px;height:280px;"><br><button onclick="window.print()">Print</button></body></html>`);
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
}

function trigger_qr_generation(frm) {
    frappe.confirm(__('Generate QR Code?'), () => {
        frappe.call({
            method: 'ecclesia.ecclesia.doctype.fixed_asset.fixed_asset.regenerate_qr_code',
            args: { asset_name: frm.doc.name },
            callback: function(r) { if (!r.exc) frm.reload_doc(); }
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
        frm.dashboard.add_indicator(__('Depreciation: {0}% Complete', [pct]), pct >= 90 ? 'blue' : pct >= 50 ? 'orange' : 'green');
    }
    if (frm.doc.current_net_book_value) {
        frm.dashboard.add_indicator(__('Book Value: {0}', [format_currency(frm.doc.current_net_book_value)]), 'blue');
    }
}

function show_smart_alerts(frm) {
    if (frm.doc.docstatus !== 1) return;

    if (frm.doc.warranty_expiry_date) {
        const days = frappe.datetime.get_day_diff(frm.doc.warranty_expiry_date, frappe.datetime.get_today());
        if (days < 0) frappe.show_alert({ message: __('⚠️ Warranty expired {0} days ago', [Math.abs(days)]), indicator: 'red' }, 8);
        else if (days <= 30) frappe.show_alert({ message: __('⚠️ Warranty expiring in {0} days', [days]), indicator: 'orange' }, 8);
    }

    if (frm.doc.insurance_expiry_date) {
        const days = frappe.datetime.get_day_diff(frm.doc.insurance_expiry_date, frappe.datetime.get_today());
        if (days < 0) frappe.show_alert({ message: __('🚨 Insurance expired {0} days ago!', [Math.abs(days)]), indicator: 'red' }, 8);
        else if (days <= 30) frappe.show_alert({ message: __('⚠️ Insurance expiring in {0} days', [days]), indicator: 'orange' }, 8);
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
            $(row).css('background-color', i % 2 === 0 ? '#ffffff' : '#04fce1');
        });
    }, 500);
}

// ============================================================================
// DEPRECIATION CALCULATIONS
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
        if (frm.doc.depreciation_method === 'Straight Line')
            rate = 100 / frm.doc.total_number_of_depreciations;
        else if (frm.doc.depreciation_method === 'Double Declining Balance' && frm.doc.total_depreciation_months)
            rate = (2 / (frm.doc.total_depreciation_months / 12)) * 100;
        else if (frm.doc.depreciation_method === 'Written Down Value' && frm.doc.total_depreciation_months) {
            const ratio = flt(frm.doc.salvage_value) / flt(frm.doc.gross_purchase_amount);
            if (ratio > 0 && ratio < 1)
                rate = (1 - Math.pow(ratio, 1 / (frm.doc.total_depreciation_months / 12))) * 100;
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
// DEPRECIATION SCHEDULE GENERATION
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

    const start_date = frm.doc.depreciation_start_date || frm.doc.available_for_use_date || frm.doc.purchase_date;
    if (!start_date) return;

    const schedule_fn = {
        'Straight Line':         calculate_straight_line_schedule,
        'Written Down Value':    calculate_wdv_schedule,
        'Double Declining Balance': calculate_ddb_schedule,
        'Sum of Years Digits':   calculate_sum_of_years_digits_schedule,
    }[frm.doc.depreciation_method];

    if (!schedule_fn) return;

    const schedule = schedule_fn(frm, start_date);
    if (!schedule || !schedule.length) return;

    frm.clear_table('depreciation_schedules');
    schedule.forEach(entry => {
        let row = frm.add_child('depreciation_schedules');
        row.schedule_date          = entry.schedule_date;
        row.opening_balance        = entry.opening_balance;
        row.depreciation_amount    = entry.depreciation_amount;
        row.closing_balance        = entry.closing_balance;
        row.accumulated_depreciation = entry.accumulated_depreciation;
    });

    frm.refresh_field('depreciation_schedules');
    apply_schedule_row_colors(frm);
    if (schedule.length) frm.set_value('next_depreciation_date', schedule[0].schedule_date);
    frappe.show_alert({ message: __('✅ {0} depreciation periods generated', [schedule.length]), indicator: 'green' }, 3);
    render_dashboard(frm);
}

// Period-date helper — adds (period_index * freq_months) to start_date then month-end
function add_schedule_date(start, period_index, freq_months) {
    let d = frappe.datetime.add_months(start, freq_months * period_index);
    return frappe.datetime.month_end(d);
}

function calculate_straight_line_schedule(frm, start_date) {
    const n    = cint(frm.doc.total_number_of_depreciations);
    const freq = get_frequency_months(frm.doc.depreciation_frequency);
    const depreciable = flt(frm.doc.gross_purchase_amount)
                      - flt(frm.doc.opening_accumulated_depreciation || 0)
                      - flt(frm.doc.salvage_value || 0);
    if (depreciable <= 0) return [];

    const per_period = flt(depreciable / n, 2);
    let opening      = flt(frm.doc.gross_purchase_amount);
    let accumulated  = flt(frm.doc.opening_accumulated_depreciation || 0);
    const schedule   = [];

    for (let i = 1; i <= n; i++) {
        let amount = i === n ? (opening - flt(frm.doc.salvage_value || 0)) : per_period;
        if (opening - amount < flt(frm.doc.salvage_value || 0)) amount = opening - flt(frm.doc.salvage_value || 0);
        if (amount <= 0) break;
        accumulated += amount;
        const closing = opening - amount;
        schedule.push({
            schedule_date:           add_schedule_date(start_date, i - 1, freq),
            opening_balance:         flt(opening, 2),
            depreciation_amount:     flt(amount, 2),
            closing_balance:         flt(closing, 2),
            accumulated_depreciation: flt(accumulated, 2),
        });
        opening = closing;
        if (opening <= flt(frm.doc.salvage_value || 0)) break;
    }
    return schedule;
}

function calculate_wdv_schedule(frm, start_date) {
    const n           = cint(frm.doc.total_number_of_depreciations);
    const freq        = get_frequency_months(frm.doc.depreciation_frequency);
    const period_rate = (flt(frm.doc.depreciation_rate) / 100) * (freq / 12);
    let opening       = flt(frm.doc.gross_purchase_amount);
    let accumulated   = flt(frm.doc.opening_accumulated_depreciation || 0);
    const schedule    = [];

    for (let i = 1; i <= n; i++) {
        let amount = opening * period_rate;
        if (opening - amount < flt(frm.doc.salvage_value || 0)) amount = opening - flt(frm.doc.salvage_value || 0);
        if (amount <= 0) break;
        accumulated += amount;
        const closing = opening - amount;
        schedule.push({
            schedule_date:           add_schedule_date(start_date, i - 1, freq),
            opening_balance:         flt(opening, 2),
            depreciation_amount:     flt(amount, 2),
            closing_balance:         flt(closing, 2),
            accumulated_depreciation: flt(accumulated, 2),
        });
        opening = closing;
        if (opening <= flt(frm.doc.salvage_value || 0)) break;
    }
    return schedule;
}

function calculate_ddb_schedule(frm, start_date) {
    const n           = cint(frm.doc.total_number_of_depreciations);
    const freq        = get_frequency_months(frm.doc.depreciation_frequency);
    const years       = flt(frm.doc.total_depreciation_months || 0) / 12;
    const period_rate = years > 0 ? (2 / years) * (freq / 12) : 0;
    let opening       = flt(frm.doc.gross_purchase_amount);
    let accumulated   = flt(frm.doc.opening_accumulated_depreciation || 0);
    const schedule    = [];

    for (let i = 1; i <= n; i++) {
        const remaining = n - i + 1;
        const ddb = opening * period_rate;
        const sl  = remaining > 0 ? (opening - flt(frm.doc.salvage_value || 0)) / remaining : 0;
        let amount = Math.max(ddb, sl);
        if (opening - amount < flt(frm.doc.salvage_value || 0)) amount = opening - flt(frm.doc.salvage_value || 0);
        if (amount <= 0) break;
        accumulated += amount;
        const closing = opening - amount;
        schedule.push({
            schedule_date:           add_schedule_date(start_date, i - 1, freq),
            opening_balance:         flt(opening, 2),
            depreciation_amount:     flt(amount, 2),
            closing_balance:         flt(closing, 2),
            accumulated_depreciation: flt(accumulated, 2),
        });
        opening = closing;
        if (opening <= flt(frm.doc.salvage_value || 0)) break;
    }
    return schedule;
}

function calculate_sum_of_years_digits_schedule(frm, start_date) {
    const n          = cint(frm.doc.total_number_of_depreciations);
    const freq       = get_frequency_months(frm.doc.depreciation_frequency);
    const sum_digits = (n * (n + 1)) / 2;
    const depreciable = flt(frm.doc.gross_purchase_amount)
                      - flt(frm.doc.opening_accumulated_depreciation || 0)
                      - flt(frm.doc.salvage_value || 0);
    if (depreciable <= 0) return [];

    let opening     = flt(frm.doc.gross_purchase_amount);
    let accumulated = flt(frm.doc.opening_accumulated_depreciation || 0);
    const schedule  = [];

    for (let i = 1; i <= n; i++) {
        const remaining = n - i + 1;
        let amount = (remaining / sum_digits) * depreciable;
        if (opening - amount < flt(frm.doc.salvage_value || 0)) amount = opening - flt(frm.doc.salvage_value || 0);
        if (amount <= 0) break;
        accumulated += amount;
        const closing = opening - amount;
        schedule.push({
            schedule_date:           add_schedule_date(start_date, i - 1, freq),
            opening_balance:         flt(opening, 2),
            depreciation_amount:     flt(amount, 2),
            closing_balance:         flt(closing, 2),
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
            callback: function(r) { if (!r.exc) frm.reload_doc(); }
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
            { label: __('Split Quantity'),   fieldname: 'split_qty',   fieldtype: 'Int',  reqd: 1, description: __('Max: {0}', [frm.doc.asset_quantity - 1]) }
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
// CATCH-UP DEPRECIATION  (periods missed through normal monthly run)
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
                    { fieldtype: 'HTML',          fieldname: 'preview',    options: preview_html },
                    { fieldtype: 'Section Break', label: __('Posting Options') },
                    { fieldtype: 'Date',   fieldname: 'up_to_date', label: __('Post Up To Date'), default: frappe.datetime.get_today() },
                    { fieldtype: 'Column Break' },
                    { fieldtype: 'Select', fieldname: 'post_as',    label: __('Posting Mode'), options: 'individual\nconsolidated', default: 'individual' },
                ],
                primary_action_label: __('✅ Post {0} Entries', [data.count]),
                primary_action(values) {
                    d.hide();
                    frappe.confirm(__('Post <b>{0}</b> catch-up entries?', [data.count]), () => {
                        frappe.call({
                            method: 'ecclesia.ecclesia.doctype.fixed_asset.fixed_asset.post_catchup_depreciation',
                            args: { asset_name: frm.doc.name, up_to_date: values.up_to_date, post_as: values.post_as },
                            freeze: true,
                            callback(r) {
                                if (r.message && r.message.success) {
                                    frm.reload_doc();
                                    frappe.show_alert({ message: __('✅ Posted'), indicator: 'green' }, 5);
                                }
                            }
                        });
                    });
                }
            });
            d.show();
        }
    });
}

// ============================================================================
// BACKDATED DEPRECIATION  (asset registered today but purchased in the past)
// ============================================================================

function show_backdated_depreciation_dialog(frm) {
    frappe.call({
        method: 'ecclesia.api.backdated_depreciation.preview_backdated_entries',
        args: { asset_name: frm.doc.name },
        freeze: true,
        freeze_message: __('⏳ Checking backdated periods...'),
        callback: function(r) {
            if (r.exc || !r.message) return;

            const data   = r.message;
            const rows   = data.pending_rows || [];
            const total  = data.total_count  || 0;
            const amount = data.total_amount || 0;

            if (total === 0) {
                frappe.msgprint({
                    title:     __('No Backdated Periods'),
                    message:   __('✅ There are no past-due unposted depreciation periods for this asset.'),
                    indicator: 'green'
                });
                return;
            }

            let table_rows = '';
            rows.forEach((row, idx) => {
                const bg = idx % 2 === 0 ? '#ffffff' : '#f0fffe';
                table_rows += `
                    <tr style="background:${bg}">
                        <td>${idx + 1}</td>
                        <td><b>${frappe.datetime.str_to_user(row.schedule_date)}</b></td>
                        <td style="text-align:right">${format_currency(row.depreciation_amount)}</td>
                        <td style="text-align:right">${format_currency(row.accumulated_depreciation_amount)}</td>
                        <td style="text-align:right">${format_currency(row.asset_book_value)}</td>
                    </tr>`;
            });

            const preview_html = `
                <div style="background:#fff3cd;padding:10px 14px;border-radius:6px;margin-bottom:12px;font-size:13px;">
                    <b>⏮️ ${total} past-due period(s)</b> totalling <b>${format_currency(amount)}</b>.<br>
                    <small>Each Journal Entry will be posted on its exact historical date.</small>
                </div>
                <div style="max-height:300px;overflow-y:auto;">
                <table class="table table-bordered table-condensed" style="font-size:12px;margin:0;">
                    <thead style="background:#f5f5f5;position:sticky;top:0;">
                        <tr><th>#</th><th>Period Date</th><th style="text-align:right">Depreciation</th><th style="text-align:right">Accumulated</th><th style="text-align:right">Book Value</th></tr>
                    </thead>
                    <tbody>${table_rows}</tbody>
                </table></div>
                <div style="margin-top:10px;padding:8px 12px;background:#d1ecf1;border-radius:4px;font-size:12px;">
                    ℹ️ This will create <b>${total} Journal Entries</b> backdated to each period's date, 
                    debiting <i>Depreciation Expense</i> and crediting <i>Accumulated Depreciation</i>.
                </div>`;

            const d = new frappe.ui.Dialog({
                title:  __('⏮️ Post Backdated Depreciation — {0}', [frm.doc.asset_code || frm.doc.name]),
                size:   'large',
                fields: [{ fieldname: 'preview_html', fieldtype: 'HTML', options: preview_html }],
                primary_action_label: __('✅ Confirm & Post {0} Entries', [total]),
                primary_action: function() {
                    d.disable_primary_action();
                    d.set_title(__('Posting... please wait'));
                    frappe.call({
                        method: 'ecclesia.api.backdated_depreciation.run_for_asset',
                        args:   { asset_name: frm.doc.name },
                        callback: function(res) {
                            d.hide();
                            if (!res.exc) frm.reload_doc();
                        }
                    });
                }
            });
            d.show();
        }
    });
}

// ============================================================================
// HELPERS
// ============================================================================

function format_currency(value) {
    return frappe.format(parseFloat(value || 0), { fieldtype: 'Currency' });
}

function flt(value, precision) {
    return parseFloat(value || 0).toFixed(precision || 2);
}

function cint(value) {
    return parseInt(value) || 0;
}
