// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt
/**
 * Bank Transaction Processor — Client Script  (v2)
 * Module: Ecclesia
 *
 * Trans Type → what shows / what is created:
 *   Supplier Payment  → Payment Entry (Pay, Supplier)
 *   Customer Receipt  → Payment Entry (Receive, Customer)
 *   Transfer Out/In   → Payment Entry (Internal Transfer)
 *   Customer Refund   → Payment Entry (Pay, Customer)
 *   Supplier Refund   → Payment Entry (Receive, Supplier)
 *   Payment           → Journal Entry (expense)  + optional amortisation
 *   Receipt           → Journal Entry (income)   + optional amortisation
 *   Pending           → No entry
 */

const APP         = "ecclesia";
const MODULE_PATH = `${APP}.ecclesia.doctype.bank_transaction_processor.bank_transaction_processor`;

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

        const isJE = ["Payment", "Receipt"].includes(tt);
        const isPE = ["Supplier Payment","Customer Receipt","Transfer Out",
                      "Transfer In","Customer Refund","Supplier Refund"].includes(tt);

        // ── For JE types: clear party fields, they are not needed ──────────
        if (isJE) {
            frappe.model.set_value(cdt, cdn, "party_type", "");
            frappe.model.set_value(cdt, cdn, "party",      "");
            frappe.model.set_value(cdt, cdn, "party_name", "");
        }

        // ── For PE types: auto-set party_type, clear GL account fields ─────
        if (isPE) {
            const auto_pt = AUTO_PARTY_TYPE[tt] || "";
            if (auto_pt && auto_pt !== row.party_type) {
                frappe.model.set_value(cdt, cdn, "party_type", auto_pt);
            }
            // Clear JE-only fields to avoid confusion
            frappe.model.set_value(cdt, cdn, "account_to_debit",  "");
            frappe.model.set_value(cdt, cdn, "account_to_credit", "");
        }

        // ── Auto-set inflow / outflow ──────────────────────────────────────
        const inflow_types  = ["Customer Receipt","Transfer In","Supplier Refund","Receipt"];
        const outflow_types = ["Supplier Payment","Transfer Out","Customer Refund","Payment"];
        if (inflow_types.includes(tt)) {
            if (row.amount) frappe.model.set_value(cdt, cdn, "inflow",  row.amount);
            frappe.model.set_value(cdt, cdn, "outflow", 0);
        } else if (outflow_types.includes(tt)) {
            if (row.amount) frappe.model.set_value(cdt, cdn, "outflow", row.amount);
            frappe.model.set_value(cdt, cdn, "inflow",  0);
        }

        // ── Update the Party field label based on context ──────────────────
        const party_label = isJE
            ? "Party (optional reference)"
            : (AUTO_PARTY_TYPE[tt] ? AUTO_PARTY_TYPE[tt] + " ID" : "Party");
        frm.fields_dict.transactions.grid.update_docfield_property(
            "party", "label", party_label
        );

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
        frappe.model.set_value(cdt, cdn, "party", "");
        frappe.model.set_value(cdt, cdn, "party_name", "");
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

    // Per-row "Create Entry" button
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
                message: __("This row is marked Pending — change the Trans Type to process it.") });
            return;
        }

        // Client-side checks
        const missing = [];
        if (!row.posting_date)  missing.push("Date");
        if (!row.trans_type)    missing.push("Trans Type");
        if (!row.remark)        missing.push("Description");
        if (!(flt(row.amount) > 0)) missing.push("Amount (> 0)");

        if (PE_TYPES.includes(row.trans_type)) {
            if (!["Transfer Out","Transfer In"].includes(row.trans_type)) {
                if (!row.party_type) missing.push("Party Type");
                if (!row.party)      missing.push("Party");
            }
        }
        if (JE_TYPES.includes(row.trans_type)) {
            // Payment / Receipt → GL accounts required, party NOT required
            if (!row.account_to_debit)  missing.push("Account to Debit (GL)");
            if (!row.account_to_credit) missing.push("Account to Credit (GL)");
            if (row.amortise) {
                if (!row.frequency)     missing.push("Frequency");
                if (!row.no_of_periods) missing.push("No of Periods");
                if (!row.start_date)    missing.push("Start Date");
            }
        }

        if (missing.length) {
            frappe.msgprint({ title: __("Incomplete Row"), indicator: "red",
                message: __("Please fill in: <b>{0}</b>", [missing.join(", ")]) });
            return;
        }

        const isJE_row    = JE_TYPES.includes(row.trans_type);
        const entry_label = isJE_row ? "Journal Entry" : "Payment Entry";
        const party_desc  = isJE_row
            ? `Dr: ${row.account_to_debit || "?"} / Cr: ${row.account_to_credit || "?"}`
            : (row.party_name || row.party || "");
        const amort_note  = (row.amortise
            ? `<br><small>Amortised over <b>${row.no_of_periods}</b> ${row.frequency} periods starting ${row.start_date}. First period posted now.</small>`
            : "");

        frappe.confirm(
            __("Create a Draft <b>{0}</b> for:<br><b>{1}</b><br>{2} &bull; Amount: {3}{4}",
               [entry_label,
                row.remark || "(no description)",
                party_desc,
                frappe.format(row.amount, { fieldtype: "Currency" }),
                amort_note]),
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
                                message:   __("✓ {0} <a href='{1}'><b>{2}</b></a> created as Draft.",
                                    [r.message.entry_type, url, r.message.entry]),
                                indicator: "green",
                            }, 8);
                            frm.reload_doc();
                        }
                    },
                });
            }
        );
    },

    // "Post Next Period" button for amortised rows
    post_next_period_btn(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.next_schedule || !row.next_posting_date) {
            frappe.msgprint(__("No more periods to post for this row.")); return;
        }
        if (!row.name || row.name.startsWith("new-") || frm.doc.__unsaved) {
            frappe.msgprint(__("Please save first.")); return;
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
// Toolbar
// ─────────────────────────────────────────────────────────────────────────────

function _render_toolbar(frm) {
    if (frm.doc.__islocal) return;

    if (!["Submitted","Cancelled"].includes(frm.doc.status)) {
        frm.add_custom_button(__("Create All Entries"), () => {
            if (!frm.doc.transactions?.length) {
                frappe.msgprint(__("No rows.")); return;
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
                   +"Payment Entries and Journal Entries (incl. amortised) as appropriate.",
                   [pending]),
                () => {
                    frappe.call({
                        method:         `${MODULE_PATH}.create_all_entries`,
                        args:           { processor_name: frm.doc.name },
                        freeze:         true,
                        freeze_message: __("Creating entries..."),
                        callback(r) {
                            if (r.message) { _show_bulk_result(r.message); frm.reload_doc(); }
                        },
                    });
                }
            );
        }, __("Actions"));
    }

    frm.add_custom_button(__("Download Template"), () => {
        window.open("/files/bank_transaction_template.xlsx", "_blank");
    }, __("Excel"));

    frm.add_custom_button(__("Export to Excel"), () => {
        if (!frm.doc.transactions?.length) {
            frappe.msgprint(__("No rows.")); return;
        }
        frappe.call({
            method:   `${MODULE_PATH}.export_to_excel`,
            args:     { processor_name: frm.doc.name },
            freeze:   true, freeze_message: __("Generating Excel..."),
            callback(r) {
                if (r.message?.file_content) _download_xlsx(r.message.file_content, r.message.filename);
            },
        });
    }, __("Excel"));

    if (!["Submitted","Cancelled"].includes(frm.doc.status)) {
        frm.add_custom_button(__("Import from Excel"), () => {
            _show_import_dialog(frm);
        }, __("Excel"));
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Bulk result
// ─────────────────────────────────────────────────────────────────────────────

function _show_bulk_result(res) {
    const err_rows  = (res.results||[]).filter(r => r.status === "error");
    const pe_count  = (res.results||[]).filter(r => r.type === "Payment Entry").length;
    const je_count  = (res.results||[]).filter(r => r.type === "Journal Entry").length;
    let err_html = "";
    if (err_rows.length) {
        const rows = err_rows.map(e =>
            `<tr>
                <td style="padding:4px 8px;border:1px solid #ddd;">${e.row}</td>
                <td style="padding:4px 8px;border:1px solid #ddd;color:#c0392b;">
                    ${frappe.utils.escape_html(e.error||"")}</td>
            </tr>`).join("");
        err_html = `<hr style="margin:10px 0"><b style="color:#c0392b;">Errors:</b>
            <div style="max-height:180px;overflow-y:auto;margin-top:6px;">
            <table style="width:100%;border-collapse:collapse;font-size:12px;">
            <thead><tr style="background:#f5f5f5;">
                <th style="padding:4px 8px;border:1px solid #ddd;">Row</th>
                <th style="padding:4px 8px;border:1px solid #ddd;">Error</th>
            </tr></thead><tbody>${rows}</tbody></table></div>`;
    }
    frappe.msgprint({
        title: __("Bulk Creation Complete"),
        indicator: res.errors ? "orange" : "green",
        message: `<div style="font-size:13px;line-height:2.1;">
            <b style="color:#27ae60;">✓ Created: ${res.created}</b>
            ${pe_count ? `<br>&nbsp;&nbsp;• Payment Entries: ${pe_count}` : ""}
            ${je_count ? `<br>&nbsp;&nbsp;• Journal Entries: ${je_count}` : ""}
            <br><span style="color:#888;">— Skipped / Pending: ${res.skipped}</span>
            ${res.errors ? `<br><span style="color:#c0392b;font-weight:bold;">✗ Errors: ${res.errors}</span>` : ""}
        </div>${err_html}`,
    });
}

// ─────────────────────────────────────────────────────────────────────────────
// Import dialog
// ─────────────────────────────────────────────────────────────────────────────

function _show_import_dialog(frm) {
    const d = new frappe.ui.Dialog({
        title: __("Import Transactions from Excel"),
        fields: [{
            fieldtype: "HTML", fieldname: "info",
            options: `<div style="padding:10px 14px;background:#EBF3FB;border-radius:6px;font-size:13px;line-height:1.7;margin-bottom:12px;">
                <b>Steps:</b><br>
                1. Click <b>Excel → Download Template</b> for the correct format.<br>
                2. Fill the <em>Bank Transactions</em> sheet — keep column headers exactly.<br>
                3. Upload here. Rows are <b>appended</b> (existing rows untouched).<br>
                4. Save, then click <b>Actions → Create All Entries</b>.
            </div>`,
        },{
            fieldtype: "Attach", fieldname: "excel_file",
            label: __("Excel File (.xlsx)"), reqd: 1,
        }],
        primary_action_label: __("Import"),
        primary_action(values) {
            if (!values.excel_file) return;
            if (!values.excel_file.toLowerCase().endsWith(".xlsx")) {
                frappe.msgprint(__("Only .xlsx files supported.")); return;
            }
            d.hide();
            _read_file_as_base64(values.excel_file, (b64, filename) => {
                frappe.call({
                    method: `${MODULE_PATH}.import_from_excel`,
                    args:   { processor_name: frm.doc.name, file_content: b64, filename },
                    freeze: true, freeze_message: __("Importing..."),
                    callback(r) { if (r.message) _show_import_result(frm, r.message); },
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
                <td style="padding:4px 8px;border:1px solid #ddd;">${frappe.utils.escape_html(e.description||"")}</td>
                <td style="padding:4px 8px;border:1px solid #ddd;color:#c0392b;">${e.errors.join("<br>")}</td>
            </tr>`).join("");
        err_html = `<hr style="margin:10px 0"><b style="color:#c0392b;">Skipped:</b>
            <div style="max-height:180px;overflow-y:auto;margin-top:6px;">
            <table style="width:100%;border-collapse:collapse;font-size:12px;">
            <thead><tr style="background:#f5f5f5;">
                <th style="padding:4px 8px;border:1px solid #ddd;">Row</th>
                <th style="padding:4px 8px;border:1px solid #ddd;">Desc</th>
                <th style="padding:4px 8px;border:1px solid #ddd;">Errors</th>
            </tr></thead><tbody>${rows}</tbody></table></div>`;
    }
    frappe.msgprint({
        title: __("Import Complete"),
        indicator: res.rows_imported > 0 ? "green" : "orange",
        message: `<div style="font-size:13px;line-height:1.9;">
            <span style="color:#27ae60;font-weight:bold;">✓ Imported: ${res.rows_imported}</span><br>
            <span style="color:#888;">— Skipped: ${res.rows_skipped}</span>
        </div>${err_html}`,
    });
    if (res.rows_imported > 0) frm.reload_doc();
}

// ─────────────────────────────────────────────────────────────────────────────
// Row button state
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

    if (btn?.$input) {
        btn.$input.prop("disabled", done || locked || pend);
        if (done) {
            const lbl = row.entry_type_created === "Payment Entry" ? "✓ PE Created" : "✓ JE Created";
            btn.$input.val(__(lbl)).css({"background-color":"#d4edda",color:"#155724",cursor:"default"});
        } else if (pend) {
            btn.$input.val(__("Pending")).css({"background-color":"#fff3cd",color:"#856404",cursor:"default"});
        } else if (locked) {
            btn.$input.val(__("Locked")).css({color:"#aaa",cursor:"not-allowed"});
        } else {
            btn.$input.val(__("Create Entry")).css({"background-color":"",color:"",cursor:"pointer"});
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Utilities
// ─────────────────────────────────────────────────────────────────────────────

function flt(v) { return parseFloat(v) || 0; }

function _read_file_as_base64(url, cb) {
    fetch(url)
        .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.arrayBuffer(); })
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
        const blob = new Blob([buf], {type:"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"});
        const url  = URL.createObjectURL(blob);
        const a    = Object.assign(document.createElement("a"), {href:url, download:filename});
        document.body.appendChild(a); a.click();
        document.body.removeChild(a); URL.revokeObjectURL(url);
    } catch(e) { frappe.msgprint(__("Download failed: {0}", [e.message])); }
}