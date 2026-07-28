// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt
/**
 * Bank Transaction Processor — Client Script  (v3)
 * Module: Ecclesia
 *
 * v3 additions (bank payment export & send):
 *   🏦 Bank Payment button group added alongside existing Actions / Excel groups
 *   All existing v2 functionality is fully preserved.
 *
 * Trans Type → what shows / what is created:
 *   Supplier Payment  → Payment Entry (Pay, Supplier)
 *   Customer Receipt  → Payment Entry (Receive, Customer)
 *   Transfer Out/In   → Payment Entry (Internal Transfer)
 *   Customer Refund   → Payment Entry (Pay, Customer)
 *   Supplier Refund   → Payment Entry (Receive, Supplier)
 *   Payment           → Journal Entry (expense/outflow) — INCLUDED in payment file
 *   Receipt           → Journal Entry (income/inflow)  — excluded (already received)
 *   Pending           → No entry
 *
 * Bank Payment file includes:
 *   Supplier Payment, Customer Receipt, Transfer Out/In, Customer Refund, Supplier Refund, Payment
 *   Receipt rows are excluded (income already credited by bank — not an outgoing instruction).
 *   Pending rows are excluded (not yet classified).
 */

const APP         = "ecclesia";
const MODULE_PATH = `${APP}.ecclesia.doctype.bank_transaction_processor.bank_transaction_processor`;

// ── Bank Payment API paths ────────────────────────────────────────────────────
const _BTP = {
    generate: 'ecclesia.api.btp_bank_export.generate_btp_payment_file',
    send:     'ecclesia.api.btp_bank_export.send_btp_payment',
    attach:   'ecclesia.api.btp_bank_export.attach_btp_payment_file',
    email:    'ecclesia.api.btp_bank_export.email_btp_payment_file',
    files:    'ecclesia.api.btp_bank_export.get_btp_attached_files',
    preview:  'ecclesia.api.btp_bank_export.preview_btp_payment_file',
    channels: 'ecclesia.api.bank_send_api.get_send_channels',
    status:   'ecclesia.api.bank_send_api.check_payment_status',
    formats:  'ecclesia.api.bank_payment_export.get_supported_formats',
};

// Which trans types produce a Payment Entry
const PE_TYPES = ["Supplier Payment","Customer Receipt","Transfer Out",
                  "Transfer In","Customer Refund","Supplier Refund"];
// Which trans types produce a Journal Entry
const JE_TYPES = ["Payment","Receipt"];

// Auto party_type when trans_type selected
const AUTO_PARTY_TYPE = {
    "Supplier Payment": "Supplier",
    "Customer Receipt": "Customer",
    "Customer Refund":  "Customer",
    "Supplier Refund":  "Supplier",
};

// ─────────────────────────────────────────────────────────────────────────────
// Helper — safe float parse
// ─────────────────────────────────────────────────────────────────────────────
function flt(v) { return parseFloat(v) || 0; }

// ─────────────────────────────────────────────────────────────────────────────
// Parent form
// ─────────────────────────────────────────────────────────────────────────────

frappe.ui.form.on("Bank Transaction Processor", {

    refresh(frm) {
        _render_toolbar(frm);
        _refresh_all_buttons(frm);
    },

    after_save(frm) {
        _refresh_all_buttons(frm);
    },

    bank_account(frm) {
        if (frm.doc.bank_account) {
            frappe.db.get_value("Bank Account", frm.doc.bank_account, "bank_account_no", (r) => {
                frm.set_value("bank_account_no", r?.bank_account_no || "");
            });
        }
    },

});

// ─────────────────────────────────────────────────────────────────────────────
// Child table events
// ─────────────────────────────────────────────────────────────────────────────

frappe.ui.form.on("Bank Transaction Line", {

    trans_type(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        const tt  = row.trans_type || "";

        const isJE = JE_TYPES.includes(tt);
        const isPE = PE_TYPES.includes(tt);

        // ── For JE types: clear party fields — GL accounts are used instead ─
        if (isJE) {
            frappe.model.set_value(cdt, cdn, "party_type", "");
            frappe.model.set_value(cdt, cdn, "party",      "");
            frappe.model.set_value(cdt, cdn, "party_name", "");
        }

        // ── For PE types: auto-set party_type, clear JE GL account fields ──
        if (isPE) {
            const auto_pt = AUTO_PARTY_TYPE[tt] || "";
            if (auto_pt && auto_pt !== row.party_type) {
                frappe.model.set_value(cdt, cdn, "party_type", auto_pt);
            }
            frappe.model.set_value(cdt, cdn, "account_to_debit",  "");
            frappe.model.set_value(cdt, cdn, "account_to_credit", "");
        }

        // ── Auto-set inflow / outflow ──────────────────────────────────────
        const inflow_types  = ["Customer Receipt","Transfer In","Supplier Refund","Receipt"];
        const outflow_types = ["Supplier Payment","Transfer Out","Customer Refund","Payment"];
        const amt = flt(row.amount);
        if (inflow_types.includes(tt)) {
            frappe.model.set_value(cdt, cdn, "inflow",  amt);
            frappe.model.set_value(cdt, cdn, "outflow", 0);
        } else if (outflow_types.includes(tt)) {
            frappe.model.set_value(cdt, cdn, "outflow", amt);
            frappe.model.set_value(cdt, cdn, "inflow",  0);
        }

        // ── Update the Party field label based on context ──────────────────
        const party_label = isJE
            ? "Party (optional reference)"
            : (AUTO_PARTY_TYPE[tt] ? AUTO_PARTY_TYPE[tt] + " ID" : "Party");
        frm.fields_dict.transactions.grid.update_docfield_property(
            "party", "label", party_label
        );

        // ── Copy bank_account_gl from parent if not set on row ────────────
        if (frm.doc.bank_account_gl && !row.bank_account_gl) {
            frappe.model.set_value(cdt, cdn, "bank_account_gl", frm.doc.bank_account_gl);
        }

        frm.fields_dict.transactions.grid.refresh_row(cdn);
    },

    amount(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        const tt  = row.trans_type || "";
        const amt = flt(row.amount);
        const inflow_types  = ["Customer Receipt","Transfer In","Supplier Refund","Receipt"];
        const outflow_types = ["Supplier Payment","Transfer Out","Customer Refund","Payment"];
        if (inflow_types.includes(tt))  frappe.model.set_value(cdt, cdn, "inflow",  amt);
        if (outflow_types.includes(tt)) frappe.model.set_value(cdt, cdn, "outflow", amt);
    },

    party_type(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!JE_TYPES.includes(row.trans_type || "")) {
            frappe.model.set_value(cdt, cdn, "party",      "");
            frappe.model.set_value(cdt, cdn, "party_name", "");
        }
    },

    party(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.party_type || !row.party) {
            frappe.model.set_value(cdt, cdn, "party_name", "");
            return;
        }
        frappe.call({
            method:   `${MODULE_PATH}.get_party_name`,
            args:     { party_type: row.party_type, party: row.party },
            callback: (r) => {
                if (r.message) frappe.model.set_value(cdt, cdn, "party_name", r.message);
            },
        });
    },

    customer_id(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.customer_id) {
            frappe.model.set_value(cdt, cdn, "customer_name", "");
            return;
        }
        frappe.db.get_value("Customer", row.customer_id, "customer_name", (r) => {
            frappe.model.set_value(cdt, cdn, "customer_name", r?.customer_name || "");
        });
    },

    amortise(frm, cdt, cdn) {
        frm.fields_dict.transactions.grid.refresh_row(cdn);
    },

    // ── Per-row "Create Entry" button ─────────────────────────────────────────
    create_entry_btn(frm, cdt, cdn) {
        const row = locals[cdt][cdn];

        if (row.entry_created) {
            const is_pe = row.entry_type_created === "Payment Entry";
            const url   = is_pe
                ? `/app/payment-entry/${row.entry_reference}`
                : `/app/journal-entry/${row.entry_reference}`;
            frappe.msgprint({
                title:     __("Already Created"),
                indicator: "orange",
                message:   __(
                    "{0} <b><a href='{1}'>{2}</a></b> already exists for this row.",
                    [row.entry_type_created || "Entry", url, row.entry_reference || ""]
                ),
            });
            return;
        }

        if (["Submitted","Cancelled"].includes(frm.doc.status)) {
            frappe.msgprint({ title: __("Locked"), indicator: "red",
                message: __("Processor is {0}.", [frm.doc.status]) });
            return;
        }

        if (!row.name || row.name.startsWith("new-") || frm.doc.__unsaved) {
            frappe.msgprint({ title: __("Save First"), indicator: "blue",
                message: __("Please save the processor first, then click Create Entry.") });
            return;
        }

        if (row.trans_type === "Pending") {
            frappe.msgprint({ title: __("Pending"), indicator: "orange",
                message: __("Change the Trans Type to process this row.") });
            return;
        }

        // ── Client-side field validation ──────────────────────────────────
        const missing = [];
        if (!row.posting_date)      missing.push("Date");
        if (!row.trans_type)        missing.push("Trans Type");
        if (!row.remark)            missing.push("Description");
        if (!(flt(row.amount) > 0)) missing.push("Amount (must be > 0)");

        const isJE_row = JE_TYPES.includes(row.trans_type);
        const isPE_row = PE_TYPES.includes(row.trans_type);

        if (isPE_row) {
            const noPartyNeeded = ["Transfer Out","Transfer In"].includes(row.trans_type);
            if (!noPartyNeeded) {
                if (!row.party_type) missing.push("Party Type");
                if (!row.party)      missing.push("Party");
            } else {
                if (!row.bank_account_gl) missing.push("Bank GL Override (target/source bank account)");
            }
        }

        if (isJE_row && row.amortise) {
            if (!row.frequency)                missing.push("Frequency");
            if (!(flt(row.no_of_periods) > 0)) missing.push("No of Periods (must be > 0)");
            if (!row.start_date)               missing.push("Start Date");
        }

        if (missing.length) {
            frappe.msgprint({ title: __("Incomplete Row"), indicator: "red",
                message: __("Please fill in: <b>{0}</b>", [missing.join(", ")]) });
            return;
        }

        // ── Build confirm message ─────────────────────────────────────────
        const entry_label = isJE_row ? "Journal Entry" : "Payment Entry";
        const detail      = isJE_row
            ? (row.trans_type === "Payment"
                ? `Dr: <b>${row.account_to_debit || "?"}</b> / Cr: <b>Bank GL</b>`
                : `Dr: <b>Bank GL</b> / Cr: <b>${row.account_to_credit || "?"}</b>`)
            : (row.party_name || row.party || "");
        const amort_note  = (isJE_row && row.amortise)
            ? `<br><small>Amortised over <b>${row.no_of_periods}</b> × ${row.frequency} periods`
              + ` starting <b>${row.start_date}</b>. Period 1 posted now.</small>`
            : "";

        frappe.confirm(
            __("Create a Draft <b>{0}</b> for:<br><b>{1}</b><br>{2} &bull; Amount: {3}{4}",
               [entry_label, row.remark || "(no description)", detail,
                frappe.format(row.amount, { fieldtype: "Currency" }), amort_note]),
            () => {
                frappe.call({
                    method:         `${MODULE_PATH}.create_entry_for_row`,
                    args:           { processor_name: frm.doc.name, row_name: row.name },
                    freeze:         true,
                    freeze_message: __("Creating entry..."),
                    callback(r) {
                        if (!r.exc && r.message?.entry) {
                            const is_pe = r.message.entry_type === "Payment Entry";
                            const url   = is_pe
                                ? `/app/payment-entry/${r.message.entry}`
                                : `/app/journal-entry/${r.message.entry}`;
                            frappe.show_alert({
                                message:   __(
                                    "✓ {0} <a href='{1}'><b>{2}</b></a> created as Draft.",
                                    [r.message.entry_type, url, r.message.entry]
                                ),
                                indicator: "green",
                            }, 8);
                            frm.reload_doc();
                        }
                    },
                });
            }
        );
    },

    // ── "Post Next Period" button for amortised rows ──────────────────────────
    post_next_period_btn(frm, cdt, cdn) {
        const row = locals[cdt][cdn];

        if (!row.next_schedule || !row.next_posting_date) {
            frappe.msgprint(__("No more periods to post for this row."));
            return;
        }
        if (!row.name || row.name.startsWith("new-") || frm.doc.__unsaved) {
            frappe.msgprint(__("Please save first."));
            return;
        }

        frappe.confirm(
            __("Post amortisation period <b>{0}</b> of {1} on date <b>{2}</b>?",
               [row.next_schedule, row.no_of_periods, row.next_posting_date]),
            () => {
                frappe.call({
                    method:         `${MODULE_PATH}.post_next_amortisation_period`,
                    args:           { processor_name: frm.doc.name, row_name: row.name },
                    freeze:         true,
                    freeze_message: __("Posting period..."),
                    callback(r) {
                        if (!r.exc && r.message) {
                            frappe.show_alert({
                                message:   __(r.message.message),
                                indicator: "green",
                            }, 8);
                            frm.reload_doc();
                        }
                    },
                });
            }
        );
    },

});

// ─────────────────────────────────────────────────────────────────────────────
// Toolbar — builds ALL button groups on every refresh
// ─────────────────────────────────────────────────────────────────────────────

function _render_toolbar(frm) {
    if (frm.doc.__islocal) return;

    // ── Actions group ─────────────────────────────────────────────────────────
    if (!["Submitted","Cancelled"].includes(frm.doc.status)) {
        frm.add_custom_button(__("Create All Entries"), () => {
            if (!frm.doc.transactions?.length) {
                frappe.msgprint(__("No rows found.")); return;
            }
            if (frm.doc.__unsaved) {
                frappe.msgprint(__("Please save first.")); return;
            }
            const pending = frm.doc.transactions.filter(
                r => !r.entry_created && r.trans_type !== "Pending"
            ).length;
            if (!pending) {
                frappe.msgprint(__("All rows already processed.")); return;
            }
            frappe.confirm(
                __("Create Draft entries for <b>{0}</b> unprocessed row(s)?<br>"
                   + "Payment Entries and Journal Entries (incl. amortised) will be created as appropriate.",
                   [pending]),
                () => {
                    frappe.call({
                        method:         `${MODULE_PATH}.create_all_entries`,
                        args:           { processor_name: frm.doc.name },
                        freeze:         true,
                        freeze_message: __("Creating entries..."),
                        callback(r) {
                            if (r.message) {
                                _show_bulk_result(r.message);
                                frm.reload_doc();
                            }
                        },
                    });
                }
            );
        }, __("Actions"));
    }

    // ── Excel group ───────────────────────────────────────────────────────────
    frm.add_custom_button(__("Download Template"), () => {
        window.open("/files/bank_transaction_template.xlsx", "_blank");
    }, __("Excel"));

    frm.add_custom_button(__("Export to Excel"), () => {
        if (!frm.doc.transactions?.length) {
            frappe.msgprint(__("No rows to export.")); return;
        }
        frappe.call({
            method:         `${MODULE_PATH}.export_to_excel`,
            args:           { processor_name: frm.doc.name },
            freeze:         true,
            freeze_message: __("Generating Excel..."),
            callback(r) {
                if (r.message?.file_content)
                    _download_xlsx(r.message.file_content, r.message.filename);
            },
        });
    }, __("Excel"));

    if (!["Submitted","Cancelled"].includes(frm.doc.status)) {
        frm.add_custom_button(__("Import from Excel"), () => {
            _show_import_dialog(frm);
        }, __("Excel"));
    }

    // ── 🏦 Bank Payment group ─────────────────────────────────────────────────
    // Visible always (both Draft and Submitted) — download/attach/email
    // are useful at any stage; send requires submitted in practice but we
    // let the backend enforce that rather than hiding the button.

    frm.add_custom_button(__("📥 Download Payment File"), () => {
        _btp_file_dialog(frm, 'download');
    }, __("🏦 Bank Payment"));

    frm.add_custom_button(__("🚀 Send to Bank"), () => {
        _btp_file_dialog(frm, 'send');
    }, __("🏦 Bank Payment"));

    frm.add_custom_button(__("📎 Attach to Document"), () => {
        _btp_attach_dialog(frm);
    }, __("🏦 Bank Payment"));

    frm.add_custom_button(__("📧 Email Payment File"), () => {
        _btp_email_dialog(frm);
    }, __("🏦 Bank Payment"));

    frm.add_custom_button(__("📡 Check Send Status"), () => {
        _btp_status_dialog(frm);
    }, __("🏦 Bank Payment"));
}

// ─────────────────────────────────────────────────────────────────────────────
// 🏦 Bank Payment — Download / Send dialog
// ─────────────────────────────────────────────────────────────────────────────

function _btp_file_dialog(frm, mode) {
    const isSend = mode === 'send';

    // Count PE-type rows to show in summary
    const peTypes  = ["Supplier Payment","Customer Receipt","Transfer Out","Transfer In","Customer Refund","Supplier Refund","Payment"];
    const allRows  = frm.doc.transactions || [];
    const peRows   = allRows.filter(r => peTypes.includes(r.trans_type));
    const jeRows   = allRows.filter(r => ["Receipt","Pending"].includes(r.trans_type));
    const totPE    = peRows.reduce((s, r) => s + flt(r.amount), 0);

    Promise.all([
        frappe.db.get_list('Payment Gateway Settings', {
            filters: { enabled: 1, company: frm.doc.company },
            fields:  ['name', 'provider', 'bank_export_format'],
            limit:   20,
        }),
        frappe.call({ method: _BTP.formats }),
    ]).then(([gateways, fmtRes]) => {
        const formats    = fmtRes.message || [];
        const fmtOpts    = formats.map(f => f.key).join('\n');
        const defaultFmt = (gateways[0] || {}).bank_export_format || 'zenith_iso20022';

        const jeNote = jeRows.length
            ? `<div style="background:#FEF3C7;border-left:3px solid #F59E0B;
                padding:6px 10px;border-radius:5px;font-size:11px;color:#92400E;margin-top:6px">
               ℹ️ <b>${jeRows.length}</b> Receipt / Pending row(s) will be
               <b>excluded</b> — Receipt rows are income already credited by the bank (not outgoing instructions). Payment rows are included.
             </div>`
            : '';

        const summaryHtml = `
            <div style="background:#EFF6FF;border-left:4px solid #3B82F6;
                        padding:11px 15px;border-radius:7px;margin-bottom:6px;font-size:12px">
                <div style="font-weight:700;color:#1E40AF;margin-bottom:4px">
                    📋 ${frm.doc.name} &nbsp;·&nbsp; ${frm.doc.company || ''}
                </div>
                <div style="display:flex;gap:20px;color:#1D4ED8">
                    <span>💳 <b>${peRows.length}</b> payment row(s) in file</span>
                    <span>📅 ${frm.doc.posting_date || ''}</span>
                    <span>💰 <b>₦${totPE.toLocaleString()}</b></span>
                </div>
                ${jeNote}
            </div>`;

        const fields = [
            { fieldtype: 'HTML', options: summaryHtml },
            {
                fieldname: 'bank_format', fieldtype: 'Select',
                label: 'Bank Format', options: fmtOpts,
                reqd: 1, default: defaultFmt,
                description: 'Zenith: ISO 20022 · GTB/Access/UBA/FBN: CSV · EU: SEPA XML · US: NACHA · International: SWIFT MT103',
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
                        <b>CRED_ADDRESS_COUNTRYSUBDIVISION</b> ← Fill <code>Payee Address</code> on each row in the child table<br>
                        <b>CREDACC_BIC</b> ← Auto-resolved from <code>Payee Bank</code> name → BIC dictionary → Bank master
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
                    description: 'SFTP: sftp_host + sftp_username + sftp_password | REST: secret_key',
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
                },
                {
                    fieldtype: 'HTML',
                    options: `<div style="background:#FFFBEB;border-left:4px solid #F59E0B;
                              padding:9px 14px;border-radius:6px;font-size:11px;color:#92400E;margin-top:4px">
                        ⚠️ <b>This initiates actual bank transfers.</b><br>
                        SFTP — set <b>SFTP Host</b>, <b>SFTP Username</b>,
                        <b>SFTP Password</b> and <b>SFTP Remote Path</b>
                        in the Payment Gateway Settings record.<br>
                        REST APIs (Paystack / Flutterwave / Squad) — set <b>Secret Key</b>
                        and disable Sandbox / Test Mode for live transfers.
                    </div>`,
                }
            );
        }

        const d = new frappe.ui.Dialog({
            title:   isSend ? '🚀 Send Bank Payments' : '📥 Download Bank Payment File',
            size:    'large',
            fields,
            primary_action_label: isSend ? '🚀 Send Now' : '📥 Download',
            primary_action(vals) {
                if (peRows.length === 0) {
                    frappe.msgprint({
                        title: 'No Payment Rows',
                        message: 'Add Supplier Payment, Customer Receipt, Transfer Out/In, '
                               + 'Customer Refund or Supplier Refund rows before generating a payment file.',
                        indicator: 'orange',
                    });
                    return;
                }
                d.hide();
                isSend ? _btp_do_send(frm, vals) : _btp_do_download(frm, vals.bank_format);
            },
        });

        // Reload channels dynamically when gateway changes
        if (isSend && d.fields_dict.gateway_name) {
            d.fields_dict.gateway_name.df.change = function() {
                const gw = d.get_value('gateway_name');
                if (!gw) return;
                frappe.call({
                    method: _BTP.channels, args: { gateway_name: gw },
                    callback: r => {
                        const opts = (r.message || []).map(c => `${c.key}:${c.label}`).join('\n');
                        d.fields_dict.send_channel.df.options = opts;
                        d.fields_dict.send_channel.refresh();
                    }
                });
            };
        }

        d.show();
    });
}

// ─────────────────────────────────────────────────────────────────────────────
// Download
// ─────────────────────────────────────────────────────────────────────────────

function _btp_do_download(frm, bank_format) {
    frappe.call({
        method: _BTP.generate,
        args:   { processor_name: frm.doc.name, bank_format },
        freeze: true, freeze_message: `Generating ${bank_format} file…`,
        callback(r) {
            const res = r.message || {};
            if (res.success) {
                _btp_save_file(res);
                const excl = res.excluded_je_rows
                    ? ` · ${res.excluded_je_rows} JE row(s) excluded` : '';
                frappe.show_alert({
                    message: `✅ ${res.file_name} · ${res.row_count} rows · ₦${(res.total_amount || 0).toLocaleString()}${excl}`,
                    indicator: 'green',
                }, 8);
            } else {
                frappe.msgprint({ title: '❌ Export Failed', message: r.exc || 'Unknown error', indicator: 'red' });
            }
        },
    });
}

// ─────────────────────────────────────────────────────────────────────────────
// Send
// ─────────────────────────────────────────────────────────────────────────────

function _btp_do_send(frm, vals) {
    const freeze_msgs = {
        sftp_upload:      '📡 Uploading to bank SFTP server…',
        paystack_bulk:    '💳 Initiating Paystack bulk transfer…',
        flutterwave_bulk: '🦋 Initiating Flutterwave bulk transfer…',
        squad_bulk:       '🏦 Initiating Squad bulk transfer…',
        manual_download:  '📥 Preparing file for download…',
    };
    frappe.call({
        method: _BTP.send,
        args:   { processor_name: frm.doc.name, send_channel: vals.send_channel, gateway_name: vals.gateway_name },
        freeze: true,
        freeze_message: freeze_msgs[vals.send_channel] || 'Sending…',
        callback(r) {
            const res = r.message || {};
            if (res.success) {
                if (res.channel === 'manual_download' && res.file_data) _btp_save_file(res);
                _btp_show_success(frm, res, vals);
            } else {
                frappe.msgprint({
                    title: '❌ Send Failed',
                    message: `<b style="color:#DC2626">${res.error || 'Unknown error'}</b>
                        <div style="margin-top:10px;font-size:11px;color:#64748B;line-height:1.8">
                            <b>Troubleshooting:</b><br>
                            📡 <b>SFTP:</b> Check SFTP Host, SFTP Username, SFTP Password
                            and SFTP Remote Path in the Payment Gateway Settings record.<br>
                            💳 <b>REST APIs:</b> Check Secret Key. Disable Sandbox / Test Mode
                            for live transfers.
                        </div>`,
                    indicator: 'red',
                });
            }
        },
    });
}

function _btp_show_success(frm, res, vals) {
    const ref = res.reference || res.batch_code || '';
    frappe.msgprint({
        title: '✅ Payment Sent',
        message: `
            <div style="font-size:13px;line-height:2">
                <b>${res.message || 'Transfer initiated'}</b><br>
                Rows sent: <b>${res.row_count || 0}</b><br>
                Total: <b>₦${(res.total_amount || 0).toLocaleString()}</b>
                ${ref ? `<div style="margin-top:6px;padding:5px 10px;background:#F1F5F9;
                          border-radius:5px;font-family:monospace;font-size:11px">
                          Reference: <b>${ref}</b></div>` : ''}
                ${res.remote_path ? `<div style="font-size:11px;color:#64748B;margin-top:4px">
                    SFTP path: <code>${res.remote_path}</code></div>` : ''}
            </div>`,
        indicator: 'green',
    });
    frm.reload_doc();
}

// ─────────────────────────────────────────────────────────────────────────────
// Attach to Document
// ─────────────────────────────────────────────────────────────────────────────

function _btp_attach_dialog(frm) {
    frappe.call({ method: _BTP.formats, callback: r => {
        const formats  = r.message || [];
        const fmtOpts  = formats.map(f => f.key).join('\n');
        const peTypes  = ["Supplier Payment","Customer Receipt","Transfer Out","Transfer In","Customer Refund","Supplier Refund","Payment"];
        const peCount  = (frm.doc.transactions || []).filter(r => peTypes.includes(r.trans_type)).length;
        const peTotal  = (frm.doc.transactions || [])
            .filter(r => peTypes.includes(r.trans_type))
            .reduce((s, r) => s + flt(r.amount), 0);

        new frappe.ui.Dialog({
            title: '📎 Attach Bank Payment File to Document',
            fields: [
                { fieldtype: 'HTML', options: `
                    <div style="background:#EFF6FF;border-left:4px solid #3B82F6;
                                padding:10px 14px;border-radius:7px;margin-bottom:6px;font-size:12px;color:#1E40AF">
                        <b>${frm.doc.name}</b> · ${peCount} payment row(s) · ₦${peTotal.toLocaleString()}<br>
                        The file will be saved as a private attachment on this document
                        and will appear in the Attachments panel.
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
                        <b>CRED_ADDRESS_COUNTRYSUBDIVISION</b> ← Fill <code>Payee Address</code> on each row in the child table<br>
                        <b>CREDACC_BIC</b> ← Auto-resolved from <code>Payee Bank</code> name → BIC dictionary → Bank master
                    </div>
                </div>`,
            },
            ],
            primary_action_label: '📎 Generate & Attach',
            primary_action(vals) {
                this.hide();
                frappe.call({
                    method: _BTP.attach,
                    args:   { processor_name: frm.doc.name, bank_format: (vals.bank_format || '').split(':')[0] },
                    freeze: true, freeze_message: 'Generating and attaching payment file…',
                    callback(r) {
                        const res = r.message || {};
                        if (res.success) {
                            frm.reload_doc();
                            frappe.show_alert({
                                message: `📎 Attached: <a href="${res.file_url}" target="_blank">${res.file_name}</a> · ${res.row_count} rows · ₦${(res.total_amount || 0).toLocaleString()}`,
                                indicator: 'green',
                            }, 8);
                        } else {
                            frappe.msgprint({ title: '❌ Attach Failed', message: r.exc || 'Unknown error', indicator: 'red' });
                        }
                    },
                });
            },
        }).show();
    }});
}

// ─────────────────────────────────────────────────────────────────────────────
// Email Payment File
// ─────────────────────────────────────────────────────────────────────────────

function _btp_email_dialog(frm) {
    frappe.call({ method: _BTP.formats, callback: r => {
        const formats  = r.message || [];
        const fmtOpts  = formats.map(f => f.key).join('\n');
        const peTypes  = ["Supplier Payment","Customer Receipt","Transfer Out","Transfer In","Customer Refund","Supplier Refund","Payment"];
        const peCount  = (frm.doc.transactions || []).filter(r => peTypes.includes(r.trans_type)).length;
        const peTotal  = (frm.doc.transactions || [])
            .filter(r => peTypes.includes(r.trans_type))
            .reduce((s, r) => s + flt(r.amount), 0);

        new frappe.ui.Dialog({
            title: '📧 Email Bank Payment File',
            size: 'large',
            fields: [
                { fieldtype: 'HTML', options: `
                    <div style="background:#EFF6FF;border-left:4px solid #3B82F6;
                                padding:10px 14px;border-radius:7px;margin-bottom:6px;font-size:12px;color:#1E40AF">
                        <b>${frm.doc.name}</b> · ${frm.doc.title || ''}<br>
                        ${peCount} payment row(s) · ₦${peTotal.toLocaleString()} will be included in the file.
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
                        <b>CRED_ADDRESS_COUNTRYSUBDIVISION</b> ← Fill <code>Payee Address</code> on each row in the child table<br>
                        <b>CREDACC_BIC</b> ← Auto-resolved from <code>Payee Bank</code> name → BIC dictionary → Bank master
                    </div>
                </div>`,
            },
                { fieldname: 'recipients', fieldtype: 'Data', label: 'Recipients (comma-separated emails)',
                  reqd: 1, default: frappe.session.user,
                  description: 'e.g. treasury@company.com, payments@zenithbank.com' },
                { fieldname: 'subject', fieldtype: 'Data', label: 'Subject',
                  default: `Bank Payment File — ${frm.doc.name} — ${frm.doc.title || ''}` },
                { fieldname: 'message', fieldtype: 'Small Text', label: 'Message (optional)',
                  description: 'Leave blank for auto-generated message with transaction details' },
            ],
            primary_action_label: '📧 Send Email',
            primary_action(vals) {
                this.hide();
                frappe.call({
                    method: _BTP.email,
                    args:   {
                        processor_name: frm.doc.name,
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
                                message: `📧 Sent: ${res.file_name} to ${(res.recipients || []).join(', ')} · ${res.row_count} rows`,
                                indicator: 'green',
                            }, 8);
                        } else {
                            frappe.msgprint({ title: '❌ Email Failed', message: r.exc || 'Unknown error', indicator: 'red' });
                        }
                    },
                });
            },
        }).show();
    }});
}

// ─────────────────────────────────────────────────────────────────────────────
// Check Send Status
// ─────────────────────────────────────────────────────────────────────────────

function _btp_status_dialog(frm) {
    frappe.db.get_list('Payment Gateway Settings', {
        filters: { enabled: 1, company: frm.doc.company },
        fields:  ['name', 'provider'],
        limit:   20,
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
                    description: 'Reference code returned when the payment was sent',
                },
            ],
            primary_action_label: '📡 Check',
            primary_action(vals) {
                this.hide();
                frappe.call({
                    method: _BTP.status,
                    args:   { gateway_name: vals.gateway_name, batch_reference: vals.batch_reference },
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

// ─────────────────────────────────────────────────────────────────────────────
// Bulk result dialog (unchanged from v2)
// ─────────────────────────────────────────────────────────────────────────────

function _show_bulk_result(res) {
    const err_rows = (res.results || []).filter(r => r.status === "error");
    const pe_count = (res.results || []).filter(r => r.type === "Payment Entry").length;
    const je_count = (res.results || []).filter(r => r.type === "Journal Entry").length;
    let err_html = "";

    if (err_rows.length) {
        const rows = err_rows.map(e =>
            `<tr>
                <td style="padding:4px 8px;border:1px solid #ddd;">${e.row}</td>
                <td style="padding:4px 8px;border:1px solid #ddd;color:#c0392b;">
                    ${frappe.utils.escape_html(e.error || "")}</td>
            </tr>`
        ).join("");
        err_html = `<hr style="margin:10px 0">
            <b style="color:#c0392b;">Rows with errors:</b>
            <div style="max-height:180px;overflow-y:auto;margin-top:6px;">
            <table style="width:100%;border-collapse:collapse;font-size:12px;">
            <thead><tr style="background:#f5f5f5;">
                <th style="padding:4px 8px;border:1px solid #ddd;">Row #</th>
                <th style="padding:4px 8px;border:1px solid #ddd;">Error</th>
            </tr></thead><tbody>${rows}</tbody></table></div>`;
    }

    frappe.msgprint({
        title:     __("Bulk Creation Complete"),
        indicator: res.errors ? "orange" : "green",
        message:   `<div style="font-size:13px;line-height:2.1;">
            <b style="color:#27ae60;">✓ Created: ${res.created}</b>
            ${pe_count ? `<br>&nbsp;&nbsp;• Payment Entries: ${pe_count}` : ""}
            ${je_count ? `<br>&nbsp;&nbsp;• Journal Entries: ${je_count}` : ""}
            <br><span style="color:#888;">— Skipped / Pending: ${res.skipped}</span>
            ${res.errors ? `<br><span style="color:#c0392b;font-weight:bold;">✗ Errors: ${res.errors}</span>` : ""}
        </div>${err_html}`,
    });
}

// ─────────────────────────────────────────────────────────────────────────────
// Import dialog (unchanged from v2)
// ─────────────────────────────────────────────────────────────────────────────

function _show_import_dialog(frm) {
    const d = new frappe.ui.Dialog({
        title: __("Import Transactions from Excel"),
        fields: [
            {
                fieldtype: "HTML",
                fieldname: "info",
                options: `<div style="padding:10px 14px;background:#EBF3FB;border-radius:6px;
                           font-size:13px;line-height:1.7;margin-bottom:12px;">
                    <b>Steps:</b><br>
                    1. Click <b>Excel → Download Template</b> for the correct format.<br>
                    2. Fill the <em>Bank Transactions</em> sheet — keep column headers exactly.<br>
                    3. Upload here. Rows are <b>appended</b> (existing rows untouched).<br>
                    4. Save, then click <b>Actions → Create All Entries</b>.
                </div>`,
            },
            {
                fieldtype: "Attach",
                fieldname: "excel_file",
                label:     __("Excel File (.xlsx)"),
                reqd:      1,
            },
        ],
        primary_action_label: __("Import"),
        primary_action(values) {
            if (!values.excel_file) return;
            if (!values.excel_file.toLowerCase().endsWith(".xlsx")) {
                frappe.msgprint(__("Only .xlsx files are supported.")); return;
            }
            d.hide();
            _read_file_as_base64(values.excel_file, (b64, filename) => {
                frappe.call({
                    method:         `${MODULE_PATH}.import_from_excel`,
                    args:           { processor_name: frm.doc.name, file_content: b64, filename },
                    freeze:         true,
                    freeze_message: __("Importing rows..."),
                    callback(r) {
                        if (r.message) _show_import_result(frm, r.message);
                    },
                });
            });
        },
    });
    d.show();
}

function _show_import_result(frm, res) {
    let err_html = "";
    if (res.errors?.length) {
        const rows = res.errors.map(e =>
            `<tr>
                <td style="padding:4px 8px;border:1px solid #ddd;">${e.row}</td>
                <td style="padding:4px 8px;border:1px solid #ddd;">
                    ${frappe.utils.escape_html(e.description || "")}</td>
                <td style="padding:4px 8px;border:1px solid #ddd;color:#c0392b;">
                    ${e.errors.join("<br>")}</td>
            </tr>`
        ).join("");
        err_html = `<hr style="margin:10px 0">
            <b style="color:#c0392b;">Skipped rows:</b>
            <div style="max-height:180px;overflow-y:auto;margin-top:6px;">
            <table style="width:100%;border-collapse:collapse;font-size:12px;">
            <thead><tr style="background:#f5f5f5;">
                <th style="padding:4px 8px;border:1px solid #ddd;">Row</th>
                <th style="padding:4px 8px;border:1px solid #ddd;">Description</th>
                <th style="padding:4px 8px;border:1px solid #ddd;">Errors</th>
            </tr></thead><tbody>${rows}</tbody></table></div>`;
    }
    frappe.msgprint({
        title:     __("Import Complete"),
        indicator: res.rows_imported > 0 ? "green" : "orange",
        message:   `<div style="font-size:13px;line-height:1.9;">
            <span style="color:#27ae60;font-weight:bold;">✓ Imported: ${res.rows_imported}</span><br>
            <span style="color:#888;">— Skipped: ${res.rows_skipped}</span>
        </div>${err_html}`,
    });
    if (res.rows_imported > 0) frm.reload_doc();
}

// ─────────────────────────────────────────────────────────────────────────────
// Row button state management (unchanged from v2)
// ─────────────────────────────────────────────────────────────────────────────

function _refresh_all_buttons(frm) {
    (frm.doc.transactions || []).forEach(row => _set_row_button(frm, row));
}

function _set_row_button(frm, row) {
    const grid_row = frm.fields_dict.transactions?.grid?.get_row(row.name);
    if (!grid_row) return;

    const done   = !!row.entry_created;
    const locked = ["Submitted","Cancelled"].includes(frm.doc.status);
    const pend   = row.trans_type === "Pending";
    const btn    = grid_row.columns["create_entry_btn"];

    if (!btn?.$input) return;

    btn.$input.prop("disabled", done || locked || pend);

    if (done) {
        const lbl = row.entry_type_created === "Payment Entry" ? "✓ PE Created" : "✓ JE Created";
        btn.$input.val(__(lbl))
            .css({ "background-color": "#d4edda", color: "#155724", cursor: "default" });
    } else if (pend) {
        btn.$input.val(__("Pending"))
            .css({ "background-color": "#fff3cd", color: "#856404", cursor: "default" });
    } else if (locked) {
        btn.$input.val(__("Locked"))
            .css({ "background-color": "", color: "#aaa", cursor: "not-allowed" });
    } else {
        btn.$input.val(__("Create Entry"))
            .css({ "background-color": "", color: "", cursor: "pointer" });
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Utilities (unchanged from v2)
// ─────────────────────────────────────────────────────────────────────────────

function _read_file_as_base64(url, cb) {
    fetch(url)
        .then(r => {
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            return r.arrayBuffer();
        })
        .then(buf => {
            let bin = "";
            new Uint8Array(buf).forEach(b => bin += String.fromCharCode(b));
            cb(btoa(bin), url.split("/").pop());
        })
        .catch(e => frappe.msgprint(__("Cannot read file: {0}", [e.message])));
}

function _download_xlsx(b64, filename) {
    try {
        const bin  = atob(b64);
        const buf  = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
        const blob = new Blob([buf], {
            type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        });
        const url = URL.createObjectURL(blob);
        const a   = Object.assign(document.createElement("a"), { href: url, download: filename });
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } catch (e) {
        frappe.msgprint(__("Download failed: {0}", [e.message]));
    }
}

function _btp_save_file(res) {
    const fname = res.file_name || 'BankPayment.csv';
    const ext   = fname.split('.').pop().toLowerCase();
    const mime  = ext === 'xml' ? 'application/xml' : ext === 'txt' ? 'text/plain' : 'text/csv';
    const a = document.createElement('a');
    a.href = `data:${mime};base64,${res.file_data}`;
    a.download = fname;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}
