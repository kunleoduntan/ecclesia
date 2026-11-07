/**
 * ecclesia/public/js/batch_excel.js
 * ---------------------------------
 * One client-side helper for Download Template / Export / Import on any
 * document whose controller exposes:
 *     download_template()
 *     export_to_excel(doc_name)
 *     import_from_excel(doc_name, file_content, filename, replace_existing)
 *
 * Usage inside a form script:
 *
 *   const XL = { module: "ecclesia.ecclesia.doctype.expense_batch.expense_batch",
 *                child_table: "petty_cash_transaction", label: __("Expenses") };
 *   refresh(frm) { ecclesia.batch_excel.add_buttons(frm, XL); }
 *   ecclesia.batch_excel.import_dialog(frm, XL);   // or .export_rows / .download_template
 *
 * Register in hooks.py:   app_include_js = ["/assets/ecclesia/js/batch_excel.js"]
 */
frappe.provide("ecclesia.batch_excel");

(function () {
    const XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

    function read_file_as_base64(url, cb) {
        fetch(url, { credentials: "same-origin" })
            .then(r => {
                if (!r.ok) throw new Error(`HTTP ${r.status}`);
                return r.arrayBuffer();
            })
            .then(buf => {
                const bytes = new Uint8Array(buf);
                const chunk = 0x8000;
                let bin = "";
                for (let i = 0; i < bytes.length; i += chunk) {
                    bin += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
                }
                cb(btoa(bin), decodeURIComponent(url.split("/").pop()));
            })
            .catch(e => frappe.msgprint(__("Cannot read file: {0}", [e.message])));
    }

    function download_xlsx(b64, filename) {
        try {
            const bin = atob(b64);
            const buf = new Uint8Array(bin.length);
            for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
            const url = URL.createObjectURL(new Blob([buf], { type: XLSX_MIME }));
            const a = Object.assign(document.createElement("a"), { href: url, download: filename });
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch (e) {
            frappe.msgprint(__("Download failed: {0}", [e.message]));
        }
    }

    function show_result(frm, res) {
        let err_html = "";
        if (res.errors && res.errors.length) {
            const rows = res.errors.map(e => `
                <tr>
                    <td style="padding:4px 8px;border:1px solid #ddd;">${frappe.utils.escape_html(String(e.row ?? ""))}</td>
                    <td style="padding:4px 8px;border:1px solid #ddd;">${frappe.utils.escape_html(e.description || "")}</td>
                    <td style="padding:4px 8px;border:1px solid #ddd;color:#c0392b;">
                        ${e.errors.map(x => frappe.utils.escape_html(x)).join("<br>")}</td>
                </tr>`).join("");
            err_html = `<hr style="margin:10px 0">
                <b style="color:#c0392b;">${__("Skipped rows")}:</b>
                <div style="max-height:220px;overflow-y:auto;margin-top:6px;">
                <table style="width:100%;border-collapse:collapse;font-size:12px;">
                <thead><tr style="background:#f5f5f5;">
                    <th style="padding:4px 8px;border:1px solid #ddd;">${__("Sheet row")}</th>
                    <th style="padding:4px 8px;border:1px solid #ddd;">${__("Description")}</th>
                    <th style="padding:4px 8px;border:1px solid #ddd;">${__("Problem")}</th>
                </tr></thead><tbody>${rows}</tbody></table></div>`;
        }
        frappe.msgprint({
            title: __("Import Complete"),
            indicator: res.rows_imported > 0 ? "green" : "orange",
            message: `<div style="font-size:13px;line-height:1.9;">
                <span style="color:#27ae60;font-weight:bold;">✓ ${__("Imported")}: ${res.rows_imported}</span><br>
                <span style="color:#888;">— ${__("Skipped")}: ${res.rows_skipped}</span>
            </div>${err_html}`,
        });
        if (res.rows_imported > 0) frm.reload_doc();
    }

    ecclesia.batch_excel = {
        download_template(cfg) {
            frappe.call({
                method: `${cfg.module}.download_template`,
                freeze: true,
                freeze_message: __("Preparing template..."),
                callback: r => r.message && download_xlsx(r.message.file_content, r.message.filename),
            });
        },

        export_rows(frm, cfg) {
            if (frm.is_new()) {
                frappe.msgprint(__("Please save the document first."));
                return;
            }
            if (!(frm.doc[cfg.child_table] || []).length) {
                frappe.msgprint(__("No rows to export."));
                return;
            }
            frappe.call({
                method: `${cfg.module}.export_to_excel`,
                args: { doc_name: frm.doc.name },
                freeze: true,
                freeze_message: __("Generating Excel..."),
                callback: r => r.message && download_xlsx(r.message.file_content, r.message.filename),
            });
        },

        import_dialog(frm, cfg) {
            if (frm.is_new()) {
                frappe.msgprint(__("Please save the document once before importing."));
                return;
            }
            if (frm.doc.docstatus !== 0) {
                frappe.msgprint(__("Rows can only be imported into a Draft document."));
                return;
            }
            const d = new frappe.ui.Dialog({
                title: __("Import {0} from Excel", [cfg.label || __("Rows")]),
                fields: [
                    {
                        fieldtype: "HTML",
                        fieldname: "info",
                        options: `<div style="padding:10px 14px;background:#EBF3FB;border-radius:6px;
                                   font-size:13px;line-height:1.7;margin-bottom:12px;">
                            <b>${__("Steps")}:</b><br>
                            1. ${__("Click")} <b>Excel → Download Template</b> ${__("for the correct format")}.<br>
                            2. ${__("Fill the sheet — keep the column headers exactly as they are")}.<br>
                            3. ${__("Upload it here. Every row is checked; bad rows are listed, good rows are imported")}.<br>
                            4. ${__("Review the rows, then Save / Submit")}.
                        </div>`,
                    },
                    { fieldtype: "Attach", fieldname: "excel_file", label: __("Excel or CSV file"), reqd: 1 },
                    {
                        fieldtype: "Check",
                        fieldname: "replace_existing",
                        label: __("Replace existing rows (otherwise rows are added)"),
                        default: 0,
                    },
                ],
                primary_action_label: __("Import"),
                primary_action(values) {
                    const f = (values.excel_file || "").toLowerCase();
                    if (!f.endsWith(".xlsx") && !f.endsWith(".csv")) {
                        frappe.msgprint(__("Only .xlsx or .csv files are supported."));
                        return;
                    }
                    d.hide();
                    read_file_as_base64(values.excel_file, (b64, filename) => {
                        frappe.call({
                            method: `${cfg.module}.import_from_excel`,
                            args: {
                                doc_name: frm.doc.name,
                                file_content: b64,
                                filename,
                                replace_existing: values.replace_existing ? 1 : 0,
                            },
                            freeze: true,
                            freeze_message: __("Importing rows..."),
                            callback: r => r.message && show_result(frm, r.message),
                        });
                    });
                },
            });
            d.show();
        },

        /** Adds the "Excel" button group to the form toolbar. */
        add_buttons(frm, cfg) {
            const grp = __("Excel");
            frm.add_custom_button(__("Download Template"), () => this.download_template(cfg), grp);
            frm.add_custom_button(__("Export to Excel"), () => this.export_rows(frm, cfg), grp);
            if (frm.doc.docstatus === 0) {
                frm.add_custom_button(__("Import from Excel"), () => this.import_dialog(frm, cfg), grp);
            }
        },
    };
})();
