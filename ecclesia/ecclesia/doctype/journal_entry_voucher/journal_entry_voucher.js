// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

/**
 * Journal Entry Voucher — Client Script
 *
 * Works with account_type directly — no party_doctype dependency.
 * party field is a plain Data field; the Python resolves the correct
 * GL account from account_type + company defaults (same as working script).
 */

// ── Replace with your actual app name ────────────────────────────────────────
const APP         = "ecclesia";
const MODULE_PATH = `${APP}.ecclesia.doctype.journal_entry_voucher.journal_entry_voucher`;

// Label to show on the party field depending on Acct Type
const PARTY_LABEL = {
    "Supplier":   "Supplier ID",
    "Customer":   "Customer ID",
    "Employee":   "Employee ID",
    "Account GL": "GL Account Code",
};

// ─────────────────────────────────────────────────────────────────────────────
// Parent form events
// ─────────────────────────────────────────────────────────────────────────────

frappe.ui.form.on("Journal Entry Voucher", {

    refresh(frm) {
        _render_toolbar(frm);
        _refresh_all_row_buttons(frm);
    },

    after_save(frm) {
        _refresh_all_row_buttons(frm);
    },

});

// ─────────────────────────────────────────────────────────────────────────────
// Child table events
// ─────────────────────────────────────────────────────────────────────────────

frappe.ui.form.on("Journal Entry Voucher Account", {

    // When Acct Type changes → update party field label, clear party fields
    account_type(frm, cdt, cdn) {
        const row   = locals[cdt][cdn];
        const label = PARTY_LABEL[row.account_type] || "Party / Account";
        frm.fields_dict.accounts.grid.update_docfield_property("party", "label", label);
        frm.fields_dict.accounts.grid.refresh_field("party");
        frappe.model.set_value(cdt, cdn, "party", "");
        frappe.model.set_value(cdt, cdn, "party_name", "");
    },

    // When Party changes → fetch and show party name
    party(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.account_type || !row.party) {
            frappe.model.set_value(cdt, cdn, "party_name", "");
            return;
        }
        frappe.call({
            method:   `${MODULE_PATH}.get_party_name`,
            args:     { account_type: row.account_type, party: row.party },
            callback: (r) => {
                if (r.message !== undefined)
                    frappe.model.set_value(cdt, cdn, "party_name", r.message);
            },
        });
    },

    // Auto-fetch corresponding account name
    corresponding_account(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.corresponding_account) {
            frappe.model.set_value(cdt, cdn, "corresponding_account_name", "");
            return;
        }
        frappe.db.get_value("Account", row.corresponding_account, "account_name", (r) => {
            frappe.model.set_value(cdt, cdn, "corresponding_account_name", r?.account_name || "");
        });
    },

    // Per-row Create Journal Entry button
    create_journal_entry_btn(frm, cdt, cdn) {
        const row = locals[cdt][cdn];

        if (row.journal_entry_created) {
            frappe.msgprint({
                title:     __("Already Created"),
                indicator: "orange",
                message:   __(
                    "Journal Entry <b><a href='/app/journal-entry/{0}'>{0}</a></b> already exists for this row.",
                    [row.journal_entry_reference || ""]
                ),
            });
            return;
        }

        if (["Submitted", "Cancelled"].includes(frm.doc.status)) {
            frappe.msgprint({
                title:     __("Voucher Locked"),
                indicator: "red",
                message:   __("Voucher is {0}. No new Journal Entries can be created.", [frm.doc.status]),
            });
            return;
        }

        // Must be saved first so row.name is a real DB key
        if (!row.name || row.name.startsWith("new-") || frm.doc.__unsaved) {
            frappe.msgprint({
                title:     __("Save Required"),
                indicator: "blue",
                message:   __("Please <b>save the voucher</b> first. This assigns database IDs to each row so Journal Entries can be created reliably."),
            });
            return;
        }

        // Quick client-side field check
        const missing = [];
        if (!row.trans_date)            missing.push("Trans Date");
        if (!row.account_type)          missing.push("Acct Type");
        if (!row.party)                 missing.push("Party / Account");
        if (!row.corresponding_account) missing.push("Corresponding Account");
        if (!row.trans_effect)          missing.push("Trans Effect");
        if (!(flt(row.amount) > 0))     missing.push("Amount (> 0)");

        if (missing.length) {
            frappe.msgprint({
                title:     __("Incomplete Row"),
                indicator: "red",
                message:   __("Please complete: <b>{0}</b>", [missing.join(", ")]),
            });
            return;
        }

        frappe.confirm(
            __("Create a Draft Journal Entry for:<br>"
               + "<b>{0}</b><br>{1} &bull; {2} &bull; {3}",
               [
                   row.transaction_description || "(no description)",
                   row.account_type,
                   row.party,
                   frappe.format(row.amount, { fieldtype: "Currency" }),
               ]),
            () => {
                frappe.call({
                    method:          `${MODULE_PATH}.create_journal_entry_for_row`,
                    args:            { voucher_name: frm.doc.name, row_name: row.name },
                    freeze:          true,
                    freeze_message:  __("Creating Journal Entry..."),
                    callback(r) {
                        if (!r.exc && r.message?.journal_entry) {
                            const je = r.message.journal_entry;
                            frappe.show_alert({
                                message:   __("✓ <a href='/app/journal-entry/{0}'><b>{0}</b></a> created as Draft.", [je]),
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
// Toolbar buttons
// ─────────────────────────────────────────────────────────────────────────────

function _render_toolbar(frm) {
    if (frm.doc.__islocal) return;

    // ── Create ALL Journal Entries (bulk) ─────────────────────────────────────
    if (!["Submitted", "Cancelled"].includes(frm.doc.status)) {
        frm.add_custom_button(__("Create All Journal Entries"), () => {
            if (!frm.doc.accounts?.length) {
                frappe.msgprint(__("No rows found."));
                return;
            }
            if (frm.doc.__unsaved) {
                frappe.msgprint(__("Please save the voucher first."));
                return;
            }
            const pending = frm.doc.accounts.filter(r => !r.journal_entry_created).length;
            if (!pending) {
                frappe.msgprint(__("All rows already have Journal Entries."));
                return;
            }
            frappe.confirm(
                __("Create Draft Journal Entries for <b>{0}</b> unprocessed row(s)?", [pending]),
                () => {
                    frappe.call({
                        method:         `${MODULE_PATH}.create_all_journal_entries`,
                        args:           { voucher_name: frm.doc.name },
                        freeze:         true,
                        freeze_message: __("Creating Journal Entries..."),
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
        window.open("/files/journal_entry_template.xlsx", "_blank");
    }, __("Excel"));

    frm.add_custom_button(__("Export to Excel"), () => {
        if (!frm.doc.accounts?.length) {
            frappe.msgprint(__("No rows to export."));
            return;
        }
        frappe.call({
            method:         `${MODULE_PATH}.export_to_excel`,
            args:           { voucher_name: frm.doc.name },
            freeze:         true,
            freeze_message: __("Generating Excel..."),
            callback(r) {
                if (r.message?.file_content)
                    _download_xlsx(r.message.file_content, r.message.filename);
            },
        });
    }, __("Excel"));

    if (!["Submitted", "Cancelled"].includes(frm.doc.status)) {
        frm.add_custom_button(__("Import from Excel"), () => {
            _show_import_dialog(frm);
        }, __("Excel"));
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Bulk result dialog
// ─────────────────────────────────────────────────────────────────────────────

function _show_bulk_result(res) {
    let error_html = "";
    const err_rows = (res.results || []).filter(r => r.status === "error");

    if (err_rows.length) {
        const rows = err_rows.map(e =>
            `<tr>
                <td style="padding:4px 8px;border:1px solid #ddd;">${e.row}</td>
                <td style="padding:4px 8px;border:1px solid #ddd;color:#c0392b;">${frappe.utils.escape_html(e.error || "")}</td>
            </tr>`
        ).join("");
        error_html = `<hr style="margin:10px 0">
            <b style="color:#c0392b;">Rows with errors:</b>
            <div style="max-height:200px;overflow-y:auto;margin-top:6px;">
            <table style="width:100%;border-collapse:collapse;font-size:12px;">
                <thead><tr style="background:#f5f5f5;">
                    <th style="padding:4px 8px;border:1px solid #ddd;">Row #</th>
                    <th style="padding:4px 8px;border:1px solid #ddd;">Error</th>
                </tr></thead><tbody>${rows}</tbody></table></div>`;
    }

    frappe.msgprint({
        title:     __("Bulk JE Creation Complete"),
        indicator: res.errors ? "orange" : "green",
        message:   `<div style="font-size:13px;line-height:1.9;">
            <span style="color:#27ae60;font-weight:bold;">✓ Created:  ${res.created}</span><br>
            <span style="color:#888;">— Skipped:  ${res.skipped}</span><br>
            ${res.errors ? `<span style="color:#c0392b;font-weight:bold;">✗ Errors:  ${res.errors}</span>` : ""}
        </div>${error_html}`,
    });
}

// ─────────────────────────────────────────────────────────────────────────────
// Import dialog
// ─────────────────────────────────────────────────────────────────────────────

function _show_import_dialog(frm) {
    const d = new frappe.ui.Dialog({
        title: __("Import Rows from Excel"),
        fields: [
            {
                fieldtype: "HTML",
                fieldname: "info",
                options: `<div style="padding:10px 14px;background:#EBF3FB;border-radius:6px;font-size:13px;line-height:1.7;margin-bottom:12px;">
                    <b>How to import:</b><br>
                    1. Click <b>Download Template</b> (in the Excel menu) to get the correct file.<br>
                    2. Fill the <em>Journal Lines</em> sheet — do <b>not</b> rename columns.<br>
                    3. Upload here. Rows are <b>appended</b>; existing rows are untouched.<br>
                    4. Save the voucher, then use <b>Create Journal Entry</b> per row
                       or <b>Create All Journal Entries</b> in the Actions menu.
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
                frappe.msgprint(__("Only .xlsx files are supported."));
                return;
            }
            d.hide();
            _read_file_as_base64(values.excel_file, (b64, filename) => {
                frappe.call({
                    method:         `${MODULE_PATH}.import_from_excel`,
                    args:           { voucher_name: frm.doc.name, file_content: b64, filename },
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
                <td style="padding:4px 8px;border:1px solid #ddd;">${frappe.utils.escape_html(e.description || "")}</td>
                <td style="padding:4px 8px;border:1px solid #ddd;color:#c0392b;">${e.errors.join("<br>")}</td>
            </tr>`
        ).join("");
        err_html = `<hr style="margin:10px 0"><b style="color:#c0392b;">Skipped rows:</b>
            <div style="max-height:200px;overflow-y:auto;margin-top:6px;">
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
            <span style="color:#888;">— Skipped:  ${res.rows_skipped}</span>
        </div>${err_html}`,
    });
    if (res.rows_imported > 0) frm.reload_doc();
}

// ─────────────────────────────────────────────────────────────────────────────
// Row button state
// ─────────────────────────────────────────────────────────────────────────────

function _refresh_all_row_buttons(frm) {
    (frm.doc.accounts || []).forEach(row => _set_row_button(frm, row));
}

function _set_row_button(frm, row) {
    const grid_row = frm.fields_dict.accounts?.grid?.get_row(row.name);
    if (!grid_row) return;
    const done      = !!row.journal_entry_created;
    const locked    = ["Submitted", "Cancelled"].includes(frm.doc.status);
    const btn       = grid_row.columns["create_journal_entry_btn"];
    if (!btn?.$input) return;

    btn.$input.prop("disabled", done || locked);
    if (done) {
        btn.$input.val(__("✓ JE Created"))
            .css({ "background-color": "#d4edda", color: "#155724", cursor: "default" });
    } else if (locked) {
        btn.$input.val(__("Voucher Locked"))
            .css({ "background-color": "", color: "#aaa", cursor: "not-allowed" });
    } else {
        btn.$input.val(__("Create Journal Entry"))
            .css({ "background-color": "", color: "", cursor: "pointer" });
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
        .catch(e => frappe.msgprint(__("Could not read file: {0}", [e.message])));
}

function _download_xlsx(b64, filename) {
    try {
        const bin  = atob(b64);
        const buf  = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
        const blob = new Blob([buf], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
        const url  = URL.createObjectURL(blob);
        const a    = Object.assign(document.createElement("a"), { href: url, download: filename });
        document.body.appendChild(a); a.click();
        document.body.removeChild(a); URL.revokeObjectURL(url);
    } catch (e) {
        frappe.msgprint(__("Download failed: {0}", [e.message]));
    }
}