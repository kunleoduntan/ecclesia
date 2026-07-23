// Copyright (c) 2026, Value Impacts Consulting
// ecclesia/ecclesia/doctype/annual_general_meeting/annual_general_meeting.js
//
// Annual General Meeting — Client Script
// CAMA 2020 compliant AGM management for Nigerian companies

const AGM_API = 'ecclesia.ecclesia.doctype.annual_general_meeting.annual_general_meeting';

frappe.ui.form.on('Annual General Meeting', {

    // ── Form load ─────────────────────────────────────────────────────────────
    refresh(frm) {
        _agm_set_indicators(frm);
        _agm_add_buttons(frm);
        _agm_render_compliance_panel(frm);
        _agm_set_field_visibility(frm);
    },

    // ── Field events ──────────────────────────────────────────────────────────
    agm_date(frm) {
        _agm_compute_notice_days(frm);
        _agm_set_cac_deadline(frm);
    },

    notice_date(frm) {
        _agm_compute_notice_days(frm);
    },

    agm_type(frm) {
        _agm_compute_notice_days(frm);
        _agm_set_field_visibility(frm);
    },

    venue_type(frm) {
        _agm_set_field_visibility(frm);
    },

    shareholders_present(frm) { _agm_check_quorum(frm); },
    total_shares(frm)         { _agm_compute_quorum_pct(frm); },
    shares_represented(frm)   { _agm_compute_quorum_pct(frm); },

    cac_filing_date(frm) {
        const deadline = frm.doc.cac_filing_deadline;
        if (deadline && frm.doc.cac_filing_date > deadline) {
            frappe.show_alert({
                message: `⚠️ CAC filing is AFTER the deadline (${deadline}). Late penalty may apply.`,
                indicator: 'red'
            }, 8);
            frm.set_value('late_filing_flag', 1);
        } else {
            frm.set_value('late_filing_flag', 0);
        }
    },
});

// ── Indicator colour ──────────────────────────────────────────────────────────
function _agm_set_indicators(frm) {
    const colours = {
        'Planning':         'orange',
        'Notices Sent':     'blue',
        'Scheduled':        'blue',
        'Postponed':        'red',
        'Held':             'green',
        'Minutes Approved': 'green',
        'CAC Filed':        'green',
        'Closed':           'grey',
    };
    frm.page.set_indicator(frm.doc.status, colours[frm.doc.status] || 'grey');
}

// ── Custom buttons ────────────────────────────────────────────────────────────
function _agm_add_buttons(frm) {
    if (frm.doc.__islocal) return;

    // ── Notices group ─────────────────────────────────────────────────────────
    frm.add_custom_button(__('📧 Send AGM Notices'), () => {
        _agm_send_notices_dialog(frm);
    }, __('📨 Notices'));

    frm.add_custom_button(__('👥 Load Shareholders from Register'), () => {
        frappe.confirm(
            'Auto-populate the Notice Log from the Register of Members?',
            () => {
                frappe.call({
                    method: `${AGM_API}.generate_notice_recipients_from_shareholders`,
                    args: { agm_name: frm.doc.name },
                    freeze: true, freeze_message: 'Loading shareholders…',
                    callback(r) {
                        const res = r.message || {};
                        frappe.show_alert({ message: res.message, indicator: 'green' }, 6);
                        frm.reload_doc();
                    }
                });
            }
        );
    }, __('📨 Notices'));

    // ── AGM Actions ───────────────────────────────────────────────────────────
    if (frm.doc.docstatus === 0) {
        frm.add_custom_button(__('✅ Mark as Held'), () => {
            frm.set_value('status', 'Held');
            frm.save();
        }, __('⚙️ Actions'));

        frm.add_custom_button(__('📋 Generate Agenda Template'), () => {
            _agm_insert_standard_agenda(frm);
        }, __('⚙️ Actions'));
    }

    if (frm.doc.status === 'Held' || frm.doc.status === 'Minutes Approved') {
        frm.add_custom_button(__('🏛️ Record CAC Filing'), () => {
            _agm_cac_dialog(frm);
        }, __('⚙️ Actions'));
    }

    // ── Compliance ────────────────────────────────────────────────────────────
    frm.add_custom_button(__('⚖️ Compliance Check'), () => {
        _agm_show_compliance_check(frm);
    }, __('📊 Reports'));

    frm.add_custom_button(__('🖨️ Print AGM Notice'), () => {
        frappe.set_route('print', frm.doctype, frm.doc.name, {format: 'AGM Notice'});
    }, __('📊 Reports'));
}

// ── Send Notices dialog ───────────────────────────────────────────────────────
function _agm_send_notices_dialog(frm) {
    if (!frm.doc.notice_logs || frm.doc.notice_logs.length === 0) {
        frappe.msgprint({
            title: 'No Recipients',
            message: 'Please add shareholders to the Notice Delivery Log first, or use "Load Shareholders from Register".',
            indicator: 'orange'
        });
        return;
    }

    const total = frm.doc.notice_logs.length;
    const pending = frm.doc.notice_logs.filter(r => !['Sent','Delivered'].includes(r.delivery_status)).length;

    new frappe.ui.Dialog({
        title: '📧 Send AGM Notices',
        fields: [
            { fieldtype: 'HTML', options: `
                <div style="background:#EFF6FF;border-left:4px solid #3B82F6;padding:12px 16px;border-radius:8px;margin-bottom:8px">
                    <b>${frm.doc.agm_title}</b><br>
                    <span style="font-size:12px;color:#1D4ED8">
                        ${total} recipients total · ${pending} pending notification<br>
                        AGM Date: <b>${frm.doc.agm_date}</b> · Notice date will be recorded as today
                    </span>
                </div>
                <div style="background:#FEF3C7;border-left:4px solid #F59E0B;padding:10px 14px;border-radius:6px;font-size:11px;color:#92400E">
                    ⚖️ <b>CAMA 2020 s.239:</b> Minimum 21 clear days notice required for AGM.
                    ${frm.doc.notice_compliant ? '✅ Notice period is compliant.' : '⚠️ Check notice period before sending.'}
                </div>` },
            { fieldname: 'channel', fieldtype: 'Select', label: 'Notification Channel',
              options: 'Email\nPost / Courier\nWhatsApp\nSMS', default: 'Email', reqd: 1 },
            { fieldname: 'include_proxy_form', fieldtype: 'Check', label: 'Attach Proxy Form', default: 1 },
            { fieldname: 'include_agenda', fieldtype: 'Check', label: 'Include Agenda', default: 1 },
        ],
        primary_action_label: `📧 Send to ${pending} Shareholders`,
        primary_action(vals) {
            this.hide();
            frappe.call({
                method: `${AGM_API}.send_agm_notices`,
                args: { agm_name: frm.doc.name, channel: vals.channel },
                freeze: true, freeze_message: 'Sending AGM notices…',
                callback(r) {
                    const res = r.message || {};
                    frappe.msgprint({
                        title: '📧 Notices Sent',
                        message: `<b>Sent:</b> ${res.sent}<br><b>Failed:</b> ${res.failed}<br><br>${res.message}`,
                        indicator: res.failed > 0 ? 'orange' : 'green'
                    });
                    frm.reload_doc();
                }
            });
        }
    }).show();
}

// ── CAC Filing dialog ─────────────────────────────────────────────────────────
function _agm_cac_dialog(frm) {
    new frappe.ui.Dialog({
        title: '🏛️ Record CAC Filing',
        fields: [
            { fieldname: 'cac_filing_date', fieldtype: 'Date', label: 'Date Filed', reqd: 1,
              default: frappe.datetime.get_today() },
            { fieldname: 'cac_reference', fieldtype: 'Data', label: 'CAC Reference / Receipt No', reqd: 1 },
            { fieldname: 'cac_form_type', fieldtype: 'Select', label: 'CAC Form',
              options: 'CAC 10 — Annual Return\nCAC 2 — Return of Allotment\nCAC 7 — Notice of Change of Director\nCAC 3 — Change of Registered Address\nOther',
              default: 'CAC 10 — Annual Return' },
            { fieldname: 'penalty', fieldtype: 'Currency', label: 'Penalty Paid (₦) if any' },
        ],
        primary_action_label: '✅ Record Filing',
        primary_action(vals) {
            this.hide();
            frappe.call({
                method: 'frappe.client.set_value',
                args: {
                    doctype: 'Annual General Meeting', name: frm.doc.name,
                    fieldname: {
                        cac_filed: 1,
                        cac_filing_date: vals.cac_filing_date,
                        cac_reference: vals.cac_reference,
                        cac_form_type: vals.cac_form_type,
                        cac_penalty_if_late: vals.penalty || 0,
                        status: 'CAC Filed',
                    }
                },
                callback() {
                    frappe.show_alert({ message: '✅ CAC filing recorded', indicator: 'green' }, 5);
                    frm.reload_doc();
                }
            });
        }
    }).show();
}

// ── Compliance Check dialog ───────────────────────────────────────────────────
function _agm_show_compliance_check(frm) {
    if (frm.doc.__islocal) { frappe.msgprint('Save the record first.'); return; }
    frappe.call({
        method: `${AGM_API}.get_agm_compliance_summary`,
        args: { agm_name: frm.doc.name },
        freeze: true, freeze_message: 'Running compliance check…',
        callback(r) {
            const checks = (r.message || {}).checks || [];
            const rows = checks.map(c => {
                const icon = c.status === 'Pass' ? '✅' : c.status === 'Fail' ? '❌' : '⏳';
                const col  = c.status === 'Pass' ? '#059669' : c.status === 'Fail' ? '#DC2626' : '#D97706';
                return `<tr>
                    <td style="padding:8px;border:1px solid #E2E8F0;font-weight:600">${icon} ${c.item}</td>
                    <td style="padding:8px;border:1px solid #E2E8F0;color:${col};font-weight:700">${c.status}</td>
                    <td style="padding:8px;border:1px solid #E2E8F0;font-size:12px;color:#475569">${c.detail}</td>
                </tr>`;
            }).join('');
            const pass  = checks.filter(c => c.status === 'Pass').length;
            const fail  = checks.filter(c => c.status === 'Fail').length;
            const pend  = checks.filter(c => c.status === 'Pending').length;
            frappe.msgprint({
                title: '⚖️ AGM Compliance Check',
                message: `
                    <div style="margin-bottom:12px;padding:10px;background:#F8FAFC;border-radius:6px;font-size:13px">
                        ✅ Pass: <b>${pass}</b> &nbsp; ❌ Fail: <b style="color:#DC2626">${fail}</b>
                        &nbsp; ⏳ Pending: <b style="color:#D97706">${pend}</b>
                    </div>
                    <table style="width:100%;border-collapse:collapse;font-size:13px">
                        <thead><tr style="background:#1E3A5F;color:white">
                            <th style="padding:8px;text-align:left">Item</th>
                            <th style="padding:8px;width:80px">Status</th>
                            <th style="padding:8px;text-align:left">Detail</th>
                        </tr></thead>
                        <tbody>${rows}</tbody>
                    </table>`,
                indicator: fail > 0 ? 'red' : pend > 0 ? 'orange' : 'green',
            });
        }
    });
}

// ── Standard Agenda template ──────────────────────────────────────────────────
function _agm_insert_standard_agenda(frm) {
    if (frm.doc.agenda_items && frm.doc.agenda_items.length > 0) {
        frappe.confirm('This will add standard items. Existing items will be kept. Continue?',
            () => _do_insert_agenda(frm));
    } else {
        _do_insert_agenda(frm);
    }
}

function _do_insert_agenda(frm) {
    const standard = [
        { no: 1, type: 'Ordinary Business', title: 'Opening and Establishment of Quorum', res: 0 },
        { no: 2, type: 'Ordinary Business', title: 'Apologies for Absence', res: 0 },
        { no: 3, type: 'Ordinary Business', title: 'Confirmation of Notice of Meeting', res: 0 },
        { no: 4, type: 'Ordinary Business', title: 'Minutes of Previous AGM — Confirmation and Matters Arising', res: 0 },
        { no: 5, type: 'Ordinary Business', title: 'Presentation and Adoption of Financial Statements', res: 1,
          res_type: 'Ordinary Resolution' },
        { no: 6, type: 'Ordinary Business', title: "Directors' Report", res: 0 },
        { no: 7, type: 'Ordinary Business', title: "Auditors' Report", res: 0 },
        { no: 8, type: 'Ordinary Business', title: 'Declaration of Dividend (if any)', res: 1,
          res_type: 'Ordinary Resolution' },
        { no: 9, type: 'Ordinary Business', title: 'Re-election of Directors Retiring by Rotation', res: 1,
          res_type: 'Ordinary Resolution' },
        { no: 10, type: 'Ordinary Business', title: 'Appointment / Re-appointment of Auditors and Fixing of Remuneration', res: 1,
          res_type: 'Ordinary Resolution' },
        { no: 11, type: 'Special Business',  title: 'Any Special Business (as per notice)', res: 1,
          res_type: 'Special Resolution' },
        { no: 12, type: 'Any Other Business', title: 'Any Other Business with the Permission of the Chair', res: 0 },
        { no: 13, type: 'Ordinary Business', title: 'Vote of Thanks and Closure', res: 0 },
    ];
    const existing_nos = (frm.doc.agenda_items || []).map(a => a.item_no);
    const start_no = existing_nos.length > 0 ? Math.max(...existing_nos) + 1 : 1;
    let offset = start_no - 1;
    standard.forEach(s => {
        frm.add_child('agenda_items', {
            item_no: s.no + offset,
            agenda_type: s.type,
            agenda_title: s.title,
            resolution_required: s.res,
            resolution_type: s.res_type || '',
        });
    });
    frm.refresh_field('agenda_items');
    frappe.show_alert({ message: `${standard.length} standard agenda items added`, indicator: 'green' }, 5);
}

// ── Computed fields ───────────────────────────────────────────────────────────
function _agm_compute_notice_days(frm) {
    if (!frm.doc.notice_date || !frm.doc.agm_date) return;
    const d1 = frappe.datetime.str_to_obj(frm.doc.notice_date);
    const d2 = frappe.datetime.str_to_obj(frm.doc.agm_date);
    const days = Math.round((d2 - d1) / (1000 * 60 * 60 * 24));
    frm.set_value('notice_days', days);
    const min = frm.doc.agm_type === 'Annual General Meeting' ? 21 : 14;
    frm.set_value('notice_compliant', days >= min ? 1 : 0);
    if (days < min) {
        frappe.show_alert({
            message: `⚠️ Only ${days} days notice — CAMA 2020 requires ${min} clear days`,
            indicator: 'red'
        }, 8);
    }
}

function _agm_set_cac_deadline(frm) {
    if (frm.doc.agm_date && !frm.doc.cac_filing_deadline) {
        const d = frappe.datetime.str_to_obj(frm.doc.agm_date);
        d.setDate(d.getDate() + 42);
        frm.set_value('cac_filing_deadline', frappe.datetime.obj_to_str(d));
    }
}

function _agm_check_quorum(frm) {
    const present = cint(frm.doc.shareholders_present);
    const reqd    = cint(frm.doc.quorum_required) || 2;
    if (present > 0) {
        frm.set_value('quorum_met', present >= reqd ? 1 : 0);
        if (present < reqd) {
            frappe.show_alert({
                message: `⚠️ Quorum not met — ${present} present, ${reqd} required`,
                indicator: 'red'
            }, 6);
        }
    }
}

function _agm_compute_quorum_pct(frm) {
    const total = cint(frm.doc.total_shares);
    const repd  = cint(frm.doc.shares_represented);
    if (total > 0 && repd > 0) {
        frm.set_value('quorum_percentage', (repd / total * 100).toFixed(2));
    }
}

function cint(v) { return parseInt(v) || 0; }

function _agm_set_field_visibility(frm) {
    const is_virtual  = ['Virtual (Online)', 'Hybrid'].includes(frm.doc.venue_type);
    const is_physical = ['Physical', 'Hybrid'].includes(frm.doc.venue_type);
    frm.toggle_display('venue',            is_physical);
    frm.toggle_display('virtual_platform', is_virtual);
    frm.toggle_display('virtual_link',     is_virtual);
    frm.toggle_display('meeting_password', is_virtual);
}

// ── Mini compliance panel in form ─────────────────────────────────────────────
function _agm_render_compliance_panel(frm) {
    if (frm.doc.__islocal) return;
    const today = frappe.datetime.get_today();
    const agm   = frm.doc.agm_date;
    const daysTo = agm ? Math.round((new Date(agm) - new Date(today)) / 86400000) : null;
    const label  = daysTo === null ? '—'
                 : daysTo > 0    ? `📅 ${daysTo} days to AGM`
                 : daysTo === 0  ? '📅 AGM is TODAY'
                 : `⚠️ AGM was ${Math.abs(daysTo)} days ago`;
    const colour = daysTo === null ? '#94A3B8'
                 : daysTo > 30   ? '#059669'
                 : daysTo > 7    ? '#D97706'
                 : '#DC2626';

    const notice_ok = frm.doc.notice_compliant;
    const quorum_ok = frm.doc.quorum_met;
    const cac_ok    = frm.doc.cac_filed;

    const html = `
        <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;
                    padding:12px 16px;margin-bottom:12px;display:flex;gap:24px;flex-wrap:wrap">
            <div style="font-size:13px;font-weight:700;color:${colour}">${label}</div>
            <div style="font-size:12px;color:#475569">
                ${notice_ok ? '✅' : '⏳'} Notice Period &nbsp;&nbsp;
                ${quorum_ok ? '✅' : '⏳'} Quorum &nbsp;&nbsp;
                ${cac_ok    ? '✅' : '⏳'} CAC Filed
            </div>
        </div>`;

    if (!frm.compliance_panel_rendered) {
        $(frm.fields_dict.overview_tab.wrapper).before(html);
        frm.compliance_panel_rendered = true;
    }
}
