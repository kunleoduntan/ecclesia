// Copyright (c) 2026, Value Impacts Consulting
// ecclesia/public/js/payroll_entry_bank.js
//
// Bank Payment Export & Send for ERPNext Payroll Entry
// Register in hooks.py → doctype_js:
//   "Payroll Entry": "ecclesia/public/js/payroll_entry_bank.js"
//
// Payment Gateway Settings fields used:
//   SFTP channel  → sftp_host, sftp_port, sftp_username, sftp_password, sftp_path
//   REST APIs     → secret_key  (Paystack / Flutterwave / Squad)
//   Format config → bank_export_format, bank_bic_code
// ══════════════════════════════════════════════════════════════════════════════

const _PE = {
    export:   'ecclesia.api.bank_payment_export.generate_payroll_payment_file',
    send:     'ecclesia.api.bank_send_api.send_payroll_payment',
    channels: 'ecclesia.api.bank_send_api.get_send_channels',
    status:   'ecclesia.api.bank_send_api.check_payment_status',
    formats:  'ecclesia.api.bank_payment_export.get_supported_formats',
    attach:   'ecclesia.api.bank_payment_export.attach_payment_file_to_doc',
    email:    'ecclesia.api.bank_payment_export.email_payment_file',
    files:    'ecclesia.api.bank_payment_export.get_attached_payment_files',
};

frappe.ui.form.on('Payroll Entry', {
    refresh(frm) {
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('📥 Download Payment File'), () => {
                _pe_dialog(frm, 'download');
            }, __('🏦 Bank Payment'));

            frm.add_custom_button(__('🚀 Send to Bank'), () => {
                _pe_dialog(frm, 'send');
            }, __('🏦 Bank Payment'));

            frm.add_custom_button(__('📎 Attach to Document'), () => {
                _pe_attach_dialog(frm);
            }, __('🏦 Bank Payment'));

            frm.add_custom_button(__('📧 Email Payment File'), () => {
                _pe_email_dialog(frm);
            }, __('🏦 Bank Payment'));

            frm.add_custom_button(__('📡 Check Send Status'), () => {
                _pe_status_dialog(frm);
            }, __('🏦 Bank Payment'));
        }
    }
});

// ── Main dialog ───────────────────────────────────────────────────────────────

function _pe_dialog(frm, mode) {
    const isSend = mode === 'send';
    const netPay = frm.doc.total_amount || 0;

    Promise.all([
        frappe.db.count('Salary Slip', { payroll_entry: frm.doc.name, docstatus: 1 }),
        frappe.db.get_list('Payment Gateway Settings', {
            filters: { enabled: 1, company: frm.doc.company },
            fields: ['name', 'provider', 'bank_export_format'],
            limit: 20,
        }),
        frappe.call({ method: _PE.formats }),
    ]).then(([slipCount, gateways, fmtRes]) => {
        const formats    = fmtRes.message || [];
        const fmtOpts    = formats.map(f => f.key).join('\n');
        const defaultFmt = (gateways[0] || {}).bank_export_format || 'zenith_iso20022';

        const noSlips = slipCount === 0;
        const summaryHtml = `
            <div style="background:#EFF6FF;border-left:4px solid #3B82F6;
                        padding:12px 16px;border-radius:8px;margin-bottom:6px">
                <div style="font-size:13px;font-weight:700;color:#1E40AF;margin-bottom:5px">
                    📋 ${frm.doc.name} &nbsp;·&nbsp; ${frm.doc.company || ''}
                </div>
                <div style="display:flex;gap:24px;font-size:12px;color:#1D4ED8">
                    <span>👥 <b>${slipCount}</b> submitted salary slips</span>
                    <span>📅 ${frm.doc.start_date || ''} – ${frm.doc.end_date || ''}</span>
                    <span>💰 <b>₦${(netPay || 0).toLocaleString()}</b> net pay</span>
                </div>
                ${noSlips ? `<div style="color:#DC2626;margin-top:6px;font-size:11px;font-weight:600">
                    ⚠️ No submitted salary slips found. Submit salary slips before generating payment file.</div>` : ''}
            </div>`;

        const fields = [
            { fieldtype: 'HTML', options: summaryHtml },
            {
                fieldname: 'bank_format', fieldtype: 'Select',
                label: 'Bank Format', options: fmtOpts,
                reqd: 1, default: defaultFmt,
                description: 'Zenith: ISO 20022 · GTB/Access/UBA/FBN: CSV · EU banks: SEPA XML · US: NACHA · International wires: SWIFT MT103',
            },
            {
                fieldtype: 'HTML',
                options: `<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:8px 12px;font-size:11px;margin-top:-4px">
                    <b style="color:#475569">Format keys:</b>
                    <div style="display:grid;grid-template-columns:140px 1fr;gap:1px 8px;margin-top:4px;color:#64748B;line-height:1.7">
                      <span style="font-family:monospace;color:#1E40AF">zenith_iso20022</span><span>Zenith Bank Nigeria — ISO 20022 pain.001 CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">gtb_csv</span><span>GTBank Nigeria — CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">access_csv</span><span>Access Bank Nigeria — CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">uba_csv</span><span>UBA Nigeria — CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">firstbank_csv</span><span>First Bank Nigeria — CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">sepa_xml</span><span>SEPA Credit Transfer XML — EU banks</span>
                      <span style="font-family:monospace;color:#1E40AF">bacs_csv</span><span>BACS Direct Credit — UK</span>
                      <span style="font-family:monospace;color:#1E40AF">ach_nacha</span><span>ACH / NACHA — USA</span>
                      <span style="font-family:monospace;color:#1E40AF">swift_mt103</span><span>SWIFT MT103 — International wires</span>
                    </div>
                    <div style="margin-top:8px;padding:6px 10px;background:#FEF3C7;border-radius:5px;font-size:10px;color:#92400E;border:1px solid #F59E0B">
                        <b>Highlighted columns in template:</b><br>
                        <b>CRED_ADDRESS_COUNTRYSUBDIVISION</b> ← Employee <code>Permanent Address</code> field (HR → Employee → Personal Details)<br>
                        <b>CREDACC_BIC</b> ← Auto-resolved from Employee bank name → BIC dictionary → Bank master
                    </div>
                </div>`,
            },
        ];

        if (isSend) {
            fields.push(
                {
                    fieldname: 'gateway_name', fieldtype: 'Link',
                    label: 'Payment Gateway', options: 'Payment Gateway Settings',
                    reqd: 1, default: (gateways[0] || {}).name || '',
                    description: 'Must have credentials configured in the gateway record',
                },
                {
                    fieldname: 'send_channel', fieldtype: 'Select',
                    label: 'Send Channel',
                    options: [
                        'sftp_upload:📡 SFTP Upload — direct to bank file server',
                        'paystack_bulk:💳 Paystack Bulk Transfer API',
                        'flutterwave_bulk:🦋 Flutterwave Bulk Transfer API',
                        'squad_bulk:🏦 Squad (GTBank) Bulk Transfer API',
                        'manual_download:📥 Manual Download — upload to portal yourself',
                    ].join('\n'),
                    reqd: 1, default: 'sftp_upload',
                    description: 'SFTP reads: sftp_host · sftp_username · sftp_password · sftp_path. REST APIs read: secret_key.',
                },
                {
                    fieldname: 'confirm_amount', fieldtype: 'Currency',
                    label: 'Confirm Total Net Pay (₦)',
                    reqd: 1, default: netPay,
                    description: 'Re-enter total to confirm — must match payroll total exactly before sending',
                },
                {
                    fieldtype: 'HTML',
                    options: `<div style="background:#FFFBEB;border-left:4px solid #F59E0B;
                              padding:10px 14px;border-radius:6px;font-size:11px;color:#92400E;margin-top:4px">
                        ⚠️ <b>This will initiate actual bank transfers.</b>
                        Confirm all salary slips are correct and approved before sending.
                        This action cannot be reversed through ERPNext.
                    </div>`,
                }
            );
        }

        const d = new frappe.ui.Dialog({
            title: isSend ? '🚀 Send Payroll to Bank' : '📥 Download Payroll Payment File',
            size:  'large',
            fields,
            primary_action_label: isSend ? '🚀 Send to Bank' : '📥 Download',
            primary_action(vals) {
                if (noSlips) {
                    frappe.msgprint({ title: 'No Salary Slips', message: 'Submit salary slips first.', indicator: 'orange' });
                    return;
                }
                if (isSend && Math.abs((vals.confirm_amount || 0) - netPay) > 1) {
                    frappe.msgprint({
                        title: '⚠️ Amount Mismatch',
                        message: `Confirmed: ₦${(vals.confirm_amount || 0).toLocaleString()}<br>
                                  Payroll total: ₦${netPay.toLocaleString()}<br><br>
                                  Re-enter the exact total net pay.`,
                        indicator: 'red',
                    });
                    return;
                }
                d.hide();
                isSend ? _pe_do_send(frm, vals, netPay) : _pe_do_download(frm, vals.bank_format);
            },
        });

        // Reload channels dynamically when gateway changes
        if (isSend && d.fields_dict.gateway_name) {
            d.fields_dict.gateway_name.df.change = function() {
                const gw = d.get_value('gateway_name');
                if (!gw) return;
                frappe.call({
                    method: _PE.channels,
                    args: { gateway_name: gw },
                    callback: r => {
                        const opts = (r.message || []).map(c => `${c.key}:${c.label}`).join('\n');
                        d.fields_dict.send_channel.df.options = opts;
                        d.fields_dict.send_channel.refresh();
                    },
                });
            };
        }

        d.show();
    });
}

// ── Download ──────────────────────────────────────────────────────────────────

function _pe_do_download(frm, bank_format) {
    frappe.call({
        method: _PE.export,
        args:   { payroll_entry: frm.doc.name, bank_format },
        freeze: true, freeze_message: `Generating ${bank_format} file…`,
        callback(r) {
            const res = r.message || {};
            if (res.success) {
                _pe_save_file(res);
                frappe.show_alert({
                    message: `✅ ${res.file_name} · ${res.row_count} employees · ₦${(res.total_amount || 0).toLocaleString()}`,
                    indicator: 'green',
                }, 7);
                frm.add_comment('Comment',
                    `Bank payment file downloaded: ${res.file_name} · ${res.row_count} employees · ₦${(res.total_amount || 0).toLocaleString()} · ${frappe.datetime.now_datetime()}`,
                    true
                );
            } else {
                frappe.msgprint({
                    title: '❌ Export Failed',
                    message: `<b>${res.error || 'Unknown error'}</b><br><br>
                        <div style="font-size:11px;color:#64748B">
                            Ensure salary slips are submitted and employees have bank account numbers configured.
                        </div>`,
                    indicator: 'red',
                });
            }
        },
    });
}

// ── Send ──────────────────────────────────────────────────────────────────────

function _pe_do_send(frm, vals, netPay) {
    const freeze_msgs = {
        sftp_upload:      '📡 Uploading to bank SFTP server…',
        paystack_bulk:    '💳 Initiating Paystack bulk transfer…',
        flutterwave_bulk: '🦋 Initiating Flutterwave bulk transfer…',
        squad_bulk:       '🏦 Initiating Squad bulk transfer…',
        manual_download:  '📥 Preparing file for download…',
    };

    frappe.call({
        method: _PE.send,
        args: {
            payroll_entry: frm.doc.name,
            send_channel:  vals.send_channel,
            gateway_name:  vals.gateway_name,
        },
        freeze: true,
        freeze_message: freeze_msgs[vals.send_channel] || 'Processing…',
        callback(r) {
            const res = r.message || {};
            if (res.success) {
                if (res.channel === 'manual_download' && res.file_data) _pe_save_file(res);
                _pe_show_success(frm, res, vals, netPay);
            } else {
                _pe_show_error(res);
            }
        },
    });
}

// ── Status check ──────────────────────────────────────────────────────────────

function _pe_status_dialog(frm) {
    frappe.db.get_list('Payment Gateway Settings', {
        filters: { enabled: 1, company: frm.doc.company },
        fields: ['name', 'provider'],
        limit: 20,
    }).then(gateways => {
        new frappe.ui.Dialog({
            title: '📡 Check Payment Send Status',
            fields: [
                {
                    fieldname: 'gateway_name', fieldtype: 'Select', label: 'Payment Gateway',
                    options: gateways.map(g => g.name).join('\n'), reqd: 1,
                    default: (gateways[0] || {}).name || '',
                },
                {
                    fieldname: 'batch_reference', fieldtype: 'Data',
                    label: 'Batch / Transfer Reference', reqd: 1,
                    description: 'The reference code returned when the payroll payment was sent',
                },
            ],
            primary_action_label: '📡 Check',
            primary_action(vals) {
                this.hide();
                frappe.call({
                    method: _PE.status,
                    args: { gateway_name: vals.gateway_name, batch_reference: vals.batch_reference },
                    freeze: true, freeze_message: 'Querying status…',
                    callback(r) {
                        const res = r.message || {};
                        const col = { success:'green', failed:'red', pending:'blue', otp:'orange' }[res.status] || 'blue';
                        frappe.msgprint({
                            title: `📡 Status: ${(res.status || 'unknown').toUpperCase()}`,
                            message: `
                                <div style="font-size:12px;margin-bottom:10px;line-height:1.8">
                                    <b>Provider:</b> ${res.provider || vals.gateway_name}<br>
                                    <b>Reference:</b> ${res.reference || vals.batch_reference}<br>
                                    <b>Status:</b> <span style="font-weight:700">${res.status || 'unknown'}</span>
                                </div>
                                <pre style="font-size:10px;background:#F8FAFC;padding:8px;border-radius:6px;
                                     max-height:220px;overflow:auto">${JSON.stringify(res.details || {}, null, 2)}</pre>`,
                            indicator: col,
                        });
                    },
                });
            },
        }).show();
    });
}

// ── Result display ────────────────────────────────────────────────────────────

function _pe_show_success(frm, res, vals, netPay) {
    const channelLabel = {
        sftp_upload:      '📡 SFTP Upload',
        paystack_bulk:    '💳 Paystack',
        flutterwave_bulk: '🦋 Flutterwave',
        squad_bulk:       '🏦 Squad',
        manual_download:  '📥 Downloaded',
    }[res.channel] || '✅ Sent';

    const ref = res.reference || res.batch_code || '';

    frappe.msgprint({
        title: `${channelLabel} — Payroll Sent`,
        message: `
            <div style="font-size:13px;line-height:2">
                <b>${res.message || 'Transfer initiated'}</b><br>
                Employees:    <b>${res.row_count || 0}</b><br>
                Total Amount: <b>₦${(res.total_amount || netPay || 0).toLocaleString()}</b>
                ${ref ? `<div style="margin-top:8px;padding:6px 12px;background:#F1F5F9;
                          border-radius:6px;font-family:monospace;font-size:11px">
                          Reference: <b>${ref}</b></div>` : ''}
                ${res.remote_path ? `<div style="font-size:11px;color:#64748B;margin-top:4px">
                    SFTP path: <code>${res.remote_path}</code></div>` : ''}
            </div>`,
        indicator: 'green',
    });

    const comment = [
        `✅ Payroll sent via ${vals.send_channel}`,
        `Gateway: ${vals.gateway_name}`,
        ref ? `Ref: ${ref}` : null,
        `${res.row_count || 0} employees`,
        `₦${(res.total_amount || netPay || 0).toLocaleString()}`,
        frappe.datetime.now_datetime(),
    ].filter(Boolean).join(' · ');

    frm.add_comment('Comment', comment, true);
}

function _pe_show_error(res) {
    frappe.msgprint({
        title: '❌ Send Failed',
        message: `<b style="color:#DC2626">${res.error || 'Unknown error'}</b>
            <div style="margin-top:10px;font-size:11px;color:#64748B;line-height:1.8">
                <b>Troubleshooting:</b><br>
                📡 <b>SFTP:</b> Open the Payment Gateway Settings record and verify:<br>
                &nbsp;&nbsp;• SFTP Host (e.g. sftp.zenithbank.com)<br>
                &nbsp;&nbsp;• SFTP Username<br>
                &nbsp;&nbsp;• SFTP Password<br>
                &nbsp;&nbsp;• SFTP Remote Path (e.g. /uploads/payroll/)<br>
                💳 <b>Paystack / Flutterwave / Squad:</b> Check Secret Key in the
                API Credentials section. Disable Sandbox / Test Mode for live transfers.<br>
                ✅ <b>All channels:</b> Salary slips must be submitted (docstatus = 1).
            </div>`,
        indicator: 'red',
    });
}

// ── File download trigger ─────────────────────────────────────────────────────

function _pe_save_file(res) {
    const fname = res.file_name || 'PayrollPayment.csv';
    const ext   = fname.split('.').pop().toLowerCase();
    const mime  = ext === 'xml' ? 'application/xml' : ext === 'txt' ? 'text/plain' : 'text/csv';
    const a = document.createElement('a');
    a.href = `data:${mime};base64,${res.file_data}`;
    a.download = fname;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}


// ── Attach to Document ────────────────────────────────────────────────────────

function _pe_attach_dialog(frm) {
    frappe.call({ method: _PE.formats, callback: r => {
        const formats = (r.message || []);
        const fmtOpts = formats.map(f => f.key).join('\n');
        new frappe.ui.Dialog({
            title: '📎 Attach Bank Payment File to Document',
            fields: [
                { fieldtype: 'HTML', options: `
                    <div style="background:#EFF6FF;border-left:4px solid #3B82F6;padding:10px 14px;border-radius:7px;margin-bottom:6px;font-size:12px;color:#1E40AF">
                        The file will be generated and saved as an attachment on this Payroll Entry.
                        It will appear in the Attachments section and can be downloaded anytime.
                    </div>` },
                { fieldname: 'bank_format', fieldtype: 'Select', label: 'Bank Format',
                  options: fmtOpts, reqd: 1, default: 'zenith_iso20022' },
            {
                fieldtype: 'HTML',
                options: `<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:8px 12px;font-size:11px;margin-top:-4px">
                    <b style="color:#475569">Format keys:</b>
                    <div style="display:grid;grid-template-columns:140px 1fr;gap:1px 8px;margin-top:4px;color:#64748B;line-height:1.7">
                      <span style="font-family:monospace;color:#1E40AF">zenith_iso20022</span><span>Zenith Bank Nigeria — ISO 20022 pain.001 CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">gtb_csv</span><span>GTBank Nigeria — CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">access_csv</span><span>Access Bank Nigeria — CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">uba_csv</span><span>UBA Nigeria — CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">firstbank_csv</span><span>First Bank Nigeria — CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">sepa_xml</span><span>SEPA Credit Transfer XML — EU banks</span>
                      <span style="font-family:monospace;color:#1E40AF">bacs_csv</span><span>BACS Direct Credit — UK</span>
                      <span style="font-family:monospace;color:#1E40AF">ach_nacha</span><span>ACH / NACHA — USA</span>
                      <span style="font-family:monospace;color:#1E40AF">swift_mt103</span><span>SWIFT MT103 — International wires</span>
                    </div>
                    <div style="margin-top:8px;padding:6px 10px;background:#FEF3C7;border-radius:5px;font-size:10px;color:#92400E;border:1px solid #F59E0B">
                        <b>Highlighted columns in template:</b><br>
                        <b>CRED_ADDRESS_COUNTRYSUBDIVISION</b> ← Employee <code>Permanent Address</code> field (HR → Employee → Personal Details)<br>
                        <b>CREDACC_BIC</b> ← Auto-resolved from Employee bank name → BIC dictionary → Bank master
                    </div>
                </div>`,
            },
            ],
            primary_action_label: '📎 Attach',
            primary_action(vals) {
                this.hide();
                frappe.call({
                    method: _PE.attach,
                    args: { source_doctype: 'Payroll Entry', source_name: frm.doc.name, bank_format: (vals.bank_format || '').split(':')[0] },
                    freeze: true, freeze_message: 'Generating and attaching file…',
                    callback(r) {
                        const res = r.message || {};
                        if (res.success) {
                            frm.reload_doc();
                            frappe.show_alert({
                                message: `📎 Attached: <a href="${res.file_url}" target="_blank">${res.file_name}</a> · ${res.row_count} employees`,
                                indicator: 'green'
                            }, 8);
                        } else {
                            frappe.msgprint({ title: '❌ Attach Failed', message: r.exc || 'Unknown error', indicator: 'red' });
                        }
                    }
                });
            }
        }).show();
    }});
}

// ── Email Payment File ────────────────────────────────────────────────────────

function _pe_email_dialog(frm) {
    frappe.call({ method: _PE.formats, callback: r => {
        const formats = (r.message || []);
        const fmtOpts = formats.map(f => f.key).join('\n');
        new frappe.ui.Dialog({
            title: '📧 Email Bank Payment File',
            size: 'large',
            fields: [
                { fieldtype: 'HTML', options: `
                    <div style="background:#EFF6FF;border-left:4px solid #3B82F6;padding:10px 14px;border-radius:7px;margin-bottom:6px;font-size:12px;color:#1E40AF">
                        The payment file will be generated and sent as an email attachment.
                        Use this to send to your bank's operations email or your treasury team.
                    </div>` },
                { fieldname: 'bank_format', fieldtype: 'Select', label: 'Bank Format',
                  options: fmtOpts, reqd: 1, default: 'zenith_iso20022' },
            {
                fieldtype: 'HTML',
                options: `<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:8px 12px;font-size:11px;margin-top:-4px">
                    <b style="color:#475569">Format keys:</b>
                    <div style="display:grid;grid-template-columns:140px 1fr;gap:1px 8px;margin-top:4px;color:#64748B;line-height:1.7">
                      <span style="font-family:monospace;color:#1E40AF">zenith_iso20022</span><span>Zenith Bank Nigeria — ISO 20022 pain.001 CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">gtb_csv</span><span>GTBank Nigeria — CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">access_csv</span><span>Access Bank Nigeria — CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">uba_csv</span><span>UBA Nigeria — CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">firstbank_csv</span><span>First Bank Nigeria — CSV</span>
                      <span style="font-family:monospace;color:#1E40AF">sepa_xml</span><span>SEPA Credit Transfer XML — EU banks</span>
                      <span style="font-family:monospace;color:#1E40AF">bacs_csv</span><span>BACS Direct Credit — UK</span>
                      <span style="font-family:monospace;color:#1E40AF">ach_nacha</span><span>ACH / NACHA — USA</span>
                      <span style="font-family:monospace;color:#1E40AF">swift_mt103</span><span>SWIFT MT103 — International wires</span>
                    </div>
                    <div style="margin-top:8px;padding:6px 10px;background:#FEF3C7;border-radius:5px;font-size:10px;color:#92400E;border:1px solid #F59E0B">
                        <b>Highlighted columns in template:</b><br>
                        <b>CRED_ADDRESS_COUNTRYSUBDIVISION</b> ← Employee <code>Permanent Address</code> field (HR → Employee → Personal Details)<br>
                        <b>CREDACC_BIC</b> ← Auto-resolved from Employee bank name → BIC dictionary → Bank master
                    </div>
                </div>`,
            },
                { fieldname: 'recipients', fieldtype: 'Data', label: 'Recipients (comma-separated emails)',
                  reqd: 1, default: frappe.session.user,
                  description: 'e.g. treasury@company.com, payments@zenithbank.com' },
                { fieldname: 'subject', fieldtype: 'Data', label: 'Subject',
                  default: `Bank Payment File — ${frm.doc.name}` },
                { fieldname: 'message', fieldtype: 'Small Text', label: 'Message (optional)',
                  description: 'Leave blank for auto-generated message' },
            ],
            primary_action_label: '📧 Send Email',
            primary_action(vals) {
                this.hide();
                frappe.call({
                    method: _PE.email,
                    args: {
                        source_doctype: 'Payroll Entry',
                        source_name:    frm.doc.name,
                        bank_format:    (vals.bank_format || '').split(':')[0],
                        recipients:     vals.recipients,
                        subject:        vals.subject,
                        message:        vals.message || null,
                    },
                    freeze: true, freeze_message: 'Generating file and sending email…',
                    callback(r) {
                        const res = r.message || {};
                        if (res.success) {
                            frm.reload_doc();
                            frappe.show_alert({
                                message: `📧 Sent: ${res.file_name} to ${(res.recipients||[]).join(', ')} · ${res.row_count} employees`,
                                indicator: 'green'
                            }, 8);
                        } else {
                            frappe.msgprint({ title: '❌ Email Failed', message: r.exc || 'Unknown error', indicator: 'red' });
                        }
                    }
                });
            }
        }).show();
    }});
}
