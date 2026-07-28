// payroll_entry_remittance.js
// Adds "📋 Statutory Remittance" button group to a submitted Payroll Entry.
// Deploy : apps/ecclesia/ecclesia/public/js/payroll_entry_remittance.js
// hooks.py:
//   "Payroll Entry": [
//       "public/js/payroll_entry_pension.min.js",
//       "public/js/payroll_entry_bank.js",
//       "public/js/payroll_entry_remittance.js",   ← this file
//   ]

frappe.ui.form.on('Payroll Entry', {
    refresh(frm) {
        if (frm.doc.docstatus === 1) {
            _pe_remit_add_buttons(frm);
            _pe_remit_show_indicator(frm);
        }
    },
});

// ── Constants ─────────────────────────────────────────────────────────────────
var _REMIT_API = 'ecclesia.api.remittance_export';
var _BANK_API  = 'ecclesia.api.bank_payment_export';

// Newline-separated format options (no literal newlines in strings)
var _FMT_OPTIONS = [
    'zenith_iso20022',
    'gtb_csv',
    'access_csv',
    'uba_csv',
    'firstbank_csv',
    'sepa_xml',
    'bacs_csv',
    'ach_nacha',
    'swift_mt103',
].join('\n');

var _FMT_LEGEND_HTML = [
    '<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;',
    'padding:8px 12px;font-size:11px;margin-top:4px">',
    '<b style="color:#475569">Format reference:</b>',
    '<div style="display:grid;grid-template-columns:150px 1fr;gap:1px 8px;',
    'margin-top:4px;color:#64748B;line-height:1.8">',
    '<span style="font-family:monospace;color:#1E40AF">zenith_iso20022</span>',
    '<span>Zenith Bank NG — ISO 20022 pain.001 (138 cols)</span>',
    '<span style="font-family:monospace;color:#1E40AF">gtb_csv</span>',
    '<span>GTBank Nigeria — CSV</span>',
    '<span style="font-family:monospace;color:#1E40AF">access_csv</span>',
    '<span>Access Bank Nigeria — CSV</span>',
    '<span style="font-family:monospace;color:#1E40AF">uba_csv</span>',
    '<span>UBA Nigeria — CSV</span>',
    '<span style="font-family:monospace;color:#1E40AF">firstbank_csv</span>',
    '<span>First Bank Nigeria — CSV</span>',
    '<span style="font-family:monospace;color:#1E40AF">swift_mt103</span>',
    '<span>SWIFT MT103 — International</span>',
    '</div>',
    '<div style="margin-top:8px;padding:5px 10px;background:#FEF3C7;',
    'border-radius:4px;font-size:10px;color:#92400E;border:1px solid #F59E0B">',
    'Statutory bank file: one row per authority. Creditor details from ',
    '<b>Statutory Authority</b> master.',
    '</div></div>',
].join('');

// ── Obligation catalogue ──────────────────────────────────────────────────────
var _OBLIGATIONS = [
    {
        key:     'pension',
        label:   '🏦 Pension',
        type:    'Pension (PenCom)',
        method:  _REMIT_API + '.generate_pension_remittance',
        amount_key: 'total_pension',
        summary: function(r) {
            return [
                ['Employees',         r.row_count],
                ['PFAs',              r.pfa_count],
                ['Total Gross',       _r_fmt(r.total_gross)],
                ['Employee (8%)',     _r_fmt(r.total_employee)],
                ['Employer (10%)',    _r_fmt(r.total_employer)],
                ['Grand Total (18%)', _r_fmt(r.grand_total)],
            ];
        },
    },
    {
        key:     'paye',
        label:   '💰 PAYE / Tax',
        type:    'PAYE',
        method:  _REMIT_API + '.generate_paye_schedule',
        amount_key: 'paye_total',
        summary: function(r) {
            var rate = r.total_gross
                ? (r.total_tax / r.total_gross * 100).toFixed(2)
                : '0.00';
            return [
                ['Employees',     r.row_count],
                ['States',        (r.states || []).join(', ')],
                ['Total Gross',   _r_fmt(r.total_gross)],
                ['Total Tax',     _r_fmt(r.total_tax)],
                ['Effective Rate', rate + '%'],
            ];
        },
    },
    {
        key:     'nsitf',
        label:   '🏗 NSITF',
        type:    'NSITF',
        method:  _REMIT_API + '.generate_nsitf_schedule',
        amount_key: 'nsitf_total',
        summary: function(r) {
            return [
                ['Employees',    r.row_count],
                ['Total Gross',  _r_fmt(r.total_gross)],
                ['NSITF (1%)',   _r_fmt(r.total_nsitf)],
                ['Rate Applied', (r.rate_applied || 1) + '%'],
            ];
        },
    },
    {
        key:     'nhf',
        label:   '🏠 NHF',
        type:    'NHF',
        method:  _REMIT_API + '.generate_nhf_schedule',
        amount_key: 'nhf_total',
        summary: function(r) {
            return [
                ['Employees',   r.row_count],
                ['Total Basic', _r_fmt(r.total_basic)],
                ['NHF (2.5%)',  _r_fmt(r.total_nhf)],
            ];
        },
    },
];

// ── Add all buttons ───────────────────────────────────────────────────────────
function _pe_remit_add_buttons(frm) {
    var group = '📋 Statutory Remittance';

    _OBLIGATIONS.forEach(function(obl) {
        var name = obl.label;

        // Excel schedule download
        frm.add_custom_button(
            __('📥 Download — ') + name,
            function() { _pe_remit_download_dialog(frm, obl); },
            group
        );

        // Bank payment file (Zenith ISO 20022)
        frm.add_custom_button(
            __('🚀 Bank File — ') + name,
            function() { _pe_remit_bank_file_dialog(frm, obl); },
            group
        );

        // Attach Excel to document
        frm.add_custom_button(
            __('📎 Attach — ') + name,
            function() { _pe_remit_do_attach(frm, obl); },
            group
        );

        // Email Excel
        frm.add_custom_button(
            __('📧 Email — ') + name,
            function() { _pe_remit_email_dialog(frm, obl); },
            group
        );
    });

    // Summary dashboard
    frm.add_custom_button(
        __('📊 Remittance Summary'),
        function() { _pe_remit_summary_dashboard(frm); },
        group
    );
}

// ── Indicator banner ──────────────────────────────────────────────────────────
function _pe_remit_show_indicator(frm) {
    frappe.call({
        method: _REMIT_API + '.get_remittance_summary',
        args: { payroll_entry: frm.doc.name },
        callback: function(r) {
            if (!r.message || !r.message.employee_count) return;
            var m = r.message;
            frm.dashboard.add_indicator(
                '📋 ' + m.employee_count + ' employees | '
                + 'Pension: ₦' + _r_abbr(m.total_pension) + ' | '
                + 'PAYE: ₦' + _r_abbr(m.paye_total) + ' | '
                + 'NSITF: ₦' + _r_abbr(m.nsitf_total) + ' | '
                + 'NHF: ₦' + _r_abbr(m.nhf_total),
                'blue'
            );
        },
    });
}

// ── Download Excel dialog ─────────────────────────────────────────────────────
function _pe_remit_download_dialog(frm, obl) {
    frappe.call({
        method: _REMIT_API + '.get_remittance_summary',
        args: { payroll_entry: frm.doc.name },
        callback: function(r) {
            var m = r.message || {};
            var info_html = _pe_remit_info_card(frm, obl, m);

            var d = new frappe.ui.Dialog({
                title: __('Download') + ' ' + obl.label,
                fields: [
                    { fieldtype: 'HTML', options: info_html },
                ],
                size: 'small',
                primary_action_label: '📥 Download',
                primary_action: function() {
                    d.hide();
                    _pe_remit_do_download(frm, obl);
                },
            });
            d.show();
        },
    });
}

// ── Execute Excel download ────────────────────────────────────────────────────
function _pe_remit_do_download(frm, obl) {
    frappe.show_alert({ message: __('Generating') + ' ' + obl.label + '...', indicator: 'blue' });

    frappe.call({
        method: obl.method,
        args: { payroll_entry: frm.doc.name },
        freeze: true,
        freeze_message: __('Generating') + ' ' + obl.label + '...',
        callback: function(r) {
            if (!r.message) return;
            var res = r.message;
            _pe_remit_trigger_download(res.b64, res.filename,
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
            _pe_remit_result_dialog(obl, res);
        },
    });
}

// ── Attach Excel to document ──────────────────────────────────────────────────
function _pe_remit_do_attach(frm, obl) {
    frappe.show_alert({ message: __('Attaching') + ' ' + obl.label + '...', indicator: 'blue' });

    frappe.call({
        method: _REMIT_API + '.attach_remittance_file',
        args: { payroll_entry: frm.doc.name, obligation_type: obl.type },
        freeze: true,
        freeze_message: __('Generating & attaching') + ' ' + obl.label + '...',
        callback: function(r) {
            if (!r.message) return;
            frappe.show_alert({
                message: '📎 ' + obl.label + ' attached: ' + r.message.filename,
                indicator: 'green',
            }, 6);
            frm.reload_doc();
        },
    });
}

// ── Email dialog ──────────────────────────────────────────────────────────────
function _pe_remit_email_dialog(frm, obl) {
    var subj = obl.type + ' Remittance — ' + frm.doc.company
        + ' — ' + _pe_remit_month_label();

    var d = new frappe.ui.Dialog({
        title: __('Email') + ' ' + obl.label,
        fields: [
            {
                fieldtype: 'HTML',
                options: '<div style="background:#F8FAFC;border:1px solid #E2E8F0;'
                    + 'border-radius:6px;padding:10px 14px;margin-bottom:8px;font-size:11px">'
                    + '<b>' + obl.label + '</b> for <b>' + frm.doc.company + '</b><br>'
                    + 'The file will be generated and sent as an Excel attachment.</div>',
            },
            {
                fieldtype: 'Small Text',
                fieldname: 'recipients',
                label: 'To (Recipients)',
                reqd: 1,
                description: 'Comma or semicolon-separated email addresses',
            },
            {
                fieldtype: 'Data',
                fieldname: 'subject',
                label: 'Subject',
                default: subj,
            },
            {
                fieldtype: 'Small Text',
                fieldname: 'message',
                label: 'Message (optional)',
            },
        ],
        size: 'small',
        primary_action_label: '📧 Send',
        primary_action: function(vals) {
            if (!vals.recipients) {
                frappe.msgprint(__('Please enter at least one recipient.'));
                return;
            }
            d.hide();
            frappe.call({
                method: _REMIT_API + '.email_remittance_file',
                args: {
                    payroll_entry:   frm.doc.name,
                    obligation_type: obl.type,
                    recipients:      vals.recipients,
                    subject:         vals.subject || '',
                    message:         vals.message || '',
                },
                freeze: true,
                freeze_message: __('Sending') + ' ' + obl.label + '...',
                callback: function(r) {
                    if (!r.message) return;
                    frappe.show_alert({
                        message: '📧 ' + obl.label + ' emailed to '
                            + r.message.sent_to.join(', '),
                        indicator: 'green',
                    }, 6);
                    frm.reload_doc();
                },
            });
        },
    });
    d.show();
}

// ── Bank File dialog ──────────────────────────────────────────────────────────
function _pe_remit_bank_file_dialog(frm, obl) {
    frappe.call({
        method: _REMIT_API + '.get_remittance_summary',
        args: { payroll_entry: frm.doc.name },
        callback: function(r) {
            var m   = r.message || {};
            var amt = m[obl.amount_key] || 0;
            var info_html = _pe_remit_info_card(frm, obl, m, amt);

            var d = new frappe.ui.Dialog({
                title: __('Bank Payment File — ') + obl.label,
                fields: [
                    { fieldtype: 'HTML', options: info_html },
                    {
                        fieldtype: 'Select',
                        fieldname: 'bank_format',
                        label:     'Bank Format',
                        options:   _FMT_OPTIONS,
                        default:   'zenith_iso20022',
                    },
                    { fieldtype: 'HTML', options: _FMT_LEGEND_HTML },
                    {
                        fieldtype: 'Select',
                        fieldname: 'action',
                        label:     'After Generating',
                        options:   'Download only\nDownload and Attach to Document',
                        default:   'Download only',
                    },
                ],
                size: 'small',
                primary_action_label: '🚀 Generate Bank File',
                primary_action: function(vals) {
                    d.hide();
                    var fmt = (vals.bank_format || 'zenith_iso20022').split(':')[0].trim();
                    var attach = (vals.action || '').indexOf('Attach') >= 0;
                    _pe_remit_do_bank_file(frm, obl, fmt, attach);
                },
            });
            d.show();
        },
    });
}

// ── Execute bank file generation ──────────────────────────────────────────────
function _pe_remit_do_bank_file(frm, obl, bank_format, attach) {
    frappe.show_alert({
        message: __('Generating bank file for') + ' ' + obl.label + '...',
        indicator: 'blue',
    });

    frappe.call({
        method: _BANK_API + '.generate_statutory_bank_file',
        args: {
            payroll_entry:   frm.doc.name,
            obligation_type: obl.type,
            bank_format:     bank_format,
        },
        freeze: true,
        freeze_message: __('Generating Zenith ISO 20022 file...'),
        callback: function(r) {
            if (!r.message || !r.message.success) return;
            var res = r.message;

            // Trigger download
            _pe_remit_trigger_download(
                res.file_data,
                res.file_name,
                'text/csv;charset=utf-8'
            );

            // Optionally attach
            if (attach) {
                frappe.call({
                    method: _BANK_API + '.attach_statutory_bank_file',
                    args: {
                        payroll_entry:   frm.doc.name,
                        obligation_type: obl.type,
                        bank_format:     bank_format,
                    },
                    callback: function(r2) {
                        if (r2.message && r2.message.status === 'ok') {
                            frappe.show_alert({
                                message: '📎 Attached: ' + res.file_name,
                                indicator: 'green',
                            }, 5);
                            frm.reload_doc();
                        }
                    },
                });
            }

            // Result summary
            frappe.msgprint({
                title: obl.label + ' — Bank File Generated',
                indicator: 'green',
                message:
                    '<div style="background:#D1FAE5;border-left:4px solid #059669;'
                    + 'padding:10px 14px;border-radius:6px;margin-bottom:10px">'
                    + '<b style="color:#065F46">✅ File generated successfully</b><br>'
                    + '<span style="color:#065F46;font-size:11px">' + res.file_name + '</span>'
                    + '</div>'
                    + '<table style="width:100%;font-size:12px;border-collapse:collapse">'
                    + '<tr><td style="color:#475569;padding:4px 0">Period</td>'
                    + '<td style="font-weight:600">' + (res.period || '') + '</td></tr>'
                    + '<tr><td style="color:#475569;padding:4px 0">Rows</td>'
                    + '<td style="font-weight:600">' + res.row_count + '</td></tr>'
                    + '<tr><td style="color:#475569;padding:4px 0">Total Amount</td>'
                    + '<td style="font-weight:700;color:#059669">₦' + _r_fmt(res.total_amount) + '</td></tr>'
                    + '<tr><td style="color:#475569;padding:4px 0">Format</td>'
                    + '<td style="font-weight:600">' + res.format + '</td></tr>'
                    + '</table>'
                    + '<div style="margin-top:10px;background:#FEF3C7;border-left:4px solid #F59E0B;'
                    + 'padding:8px 12px;border-radius:4px;font-size:11px;color:#92400E">'
                    + '⚠️ Upload to <b>Zenith Corporate IB</b> → Bulk Payments → Upload Payment File.'
                    + '</div>',
            });
        },
    });
}

// ── Summary dashboard ─────────────────────────────────────────────────────────
function _pe_remit_summary_dashboard(frm) {
    frappe.call({
        method: _REMIT_API + '.get_remittance_summary',
        args: { payroll_entry: frm.doc.name },
        callback: function(r) {
            if (!r.message) return;
            var m = r.message;

            var rows = [
                ['🏦 Pension — Employee (8%)',  m.employee_pension],
                ['🏦 Pension — Employer (10%)', m.employer_pension],
                ['🏦 Pension — Total (18%)',    m.total_pension],
                ['💰 PAYE',                      m.paye_total],
                ['🏗 NSITF (1%)',               m.nsitf_total],
                ['🏠 NHF (2.5%)',               m.nhf_total],
                ['🏥 NHIS',                     m.nhis_total],
            ];

            var rows_html = rows.map(function(pair) {
                return '<tr>'
                    + '<td style="padding:6px 12px;border-bottom:1px solid #F1F5F9;color:#475569">'
                    + pair[0] + '</td>'
                    + '<td style="padding:6px 12px;border-bottom:1px solid #F1F5F9;'
                    + 'text-align:right;font-weight:600;font-family:monospace">'
                    + '₦' + _r_fmt(pair[1] || 0) + '</td>'
                    + '</tr>';
            }).join('');

            var auths = (m.configured_authorities || []).map(function(a) {
                return '<span style="display:inline-block;background:#DBEAFE;color:#1E40AF;'
                    + 'border-radius:12px;padding:2px 10px;margin:2px;font-size:11px">'
                    + a.obligation_type + ': ' + a.authority_name + '</span>';
            }).join('');

            frappe.msgprint({
                title: '📊 Statutory Remittance Summary — ' + (m.period || ''),
                indicator: 'blue',
                wide: true,
                message:
                    '<div style="background:#1E3A5F;color:#fff;border-radius:8px;'
                    + 'padding:14px 18px;margin-bottom:12px">'
                    + '<div style="font-size:16px;font-weight:700">' + (m.company || frm.doc.company) + '</div>'
                    + '<div style="font-size:12px;opacity:0.8">' + (m.period_range || '') + '</div>'
                    + '<div style="font-size:13px;margin-top:6px">'
                    + (m.employee_count || 0) + ' employees | '
                    + 'Total Gross: ₦' + _r_fmt(m.total_gross) + '</div>'
                    + '</div>'
                    + '<table style="width:100%;border-collapse:collapse;font-size:12px">'
                    + rows_html + '</table>'
                    + '<div style="margin-top:14px;font-size:11px;color:#475569;font-weight:600">'
                    + 'Configured Authorities:</div>'
                    + '<div style="margin-top:6px">'
                    + (auths || '<i style="color:#94A3B8">No Statutory Authority records found</i>')
                    + '</div>'
                    + '<div style="margin-top:14px;background:#FEF3C7;border-left:4px solid #F59E0B;'
                    + 'padding:8px 12px;border-radius:4px;font-size:11px;color:#92400E">'
                    + '⚠️ Amounts are computed from salary slip components. '
                    + 'Actual figures depend on your payroll component setup.</div>',
            });
        },
    });
}

// ── Result dialog (after Excel download) ─────────────────────────────────────
function _pe_remit_result_dialog(obl, result) {
    var rows = (obl.summary(result) || []).map(function(pair) {
        return '<tr>'
            + '<td style="padding:5px 10px;color:#475569">' + pair[0] + '</td>'
            + '<td style="padding:5px 10px;font-weight:600;text-align:right">' + pair[1] + '</td>'
            + '</tr>';
    }).join('');

    frappe.msgprint({
        title: obl.label,
        indicator: 'green',
        message:
            '<div style="background:#D1FAE5;border-left:4px solid #059669;'
            + 'padding:10px 14px;border-radius:6px;margin-bottom:12px">'
            + '<b style="color:#065F46">✅ File generated successfully</b><br>'
            + '<span style="color:#065F46;font-size:11px">'
            + (result.filename || '') + '</span></div>'
            + '<table style="width:100%;border-collapse:collapse;font-size:12px">'
            + rows + '</table>',
    });
}

// ── Info card HTML ────────────────────────────────────────────────────────────
function _pe_remit_info_card(frm, obl, m, estimated_amount) {
    return '<div style="background:#F8FAFC;border:1px solid #E2E8F0;'
        + 'border-radius:8px;padding:14px 18px;margin-bottom:10px">'
        + '<div style="font-weight:700;color:#1E3A5F;font-size:13px;margin-bottom:10px">'
        + obl.label + ' — ' + (m.period || '') + '</div>'
        + '<table style="width:100%;border-collapse:collapse;font-size:12px">'
        + '<tr><td style="padding:4px 0;color:#475569">Document</td>'
        + '<td style="font-weight:600">' + frm.doc.name + '</td></tr>'
        + '<tr><td style="padding:4px 0;color:#475569">Company</td>'
        + '<td style="font-weight:600">' + frm.doc.company + '</td></tr>'
        + '<tr><td style="padding:4px 0;color:#475569">Period</td>'
        + '<td style="font-weight:600">' + (m.period_range || '') + '</td></tr>'
        + '<tr><td style="padding:4px 0;color:#475569">Employees</td>'
        + '<td style="font-weight:600">' + (m.employee_count || 0) + '</td></tr>'
        + (estimated_amount ? (
            '<tr><td style="padding:4px 0;color:#475569">Estimated Amount</td>'
            + '<td style="font-weight:700;color:#059669">₦' + _r_fmt(estimated_amount) + '</td></tr>'
        ) : '')
        + '</table></div>';
}

// ── Trigger file download ─────────────────────────────────────────────────────
function _pe_remit_trigger_download(b64, filename, mime) {
    var bytes = Uint8Array.from(atob(b64), function(c) { return c.charCodeAt(0); });
    var blob  = new Blob([bytes], { type: mime });
    var url   = URL.createObjectURL(blob);
    var link  = document.createElement('a');
    link.href     = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

// ── Month label ───────────────────────────────────────────────────────────────
function _pe_remit_month_label() {
    return new Date().toLocaleString('en-GB', { month: 'long', year: 'numeric' });
}

// ── Number formatters ─────────────────────────────────────────────────────────
function _r_fmt(n) {
    return (parseFloat(n) || 0).toLocaleString('en-NG', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
}

function _r_abbr(n) {
    var v = parseFloat(n) || 0;
    if (v >= 1000000) return (v / 1000000).toFixed(2) + 'M';
    if (v >= 1000)    return (v / 1000).toFixed(1) + 'K';
    return v.toFixed(2);
}
