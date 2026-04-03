// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

// message_blast/message_blast/doctype/message_blast/message_blast.js
// Copyright (c) 2025, Value Impacts Consulting
// Enterprise Message Blast — client script

// ─────────────────────────────────────────────────────────────────────────────
// CONSTANTS
// ─────────────────────────────────────────────────────────────────────────────

const MB = {
    DOCTYPE: "Message Blast",
    API:     "ecclesia.api.message_blast_api",  
    STYLE: {
        row1:              "#ffffff",
        row2:              "#f9fbfd",
        table_border:      "#c7ddff",
        table_header_bg:   "#f0f6ff",
        table_header_text: "#1e3a8a"
    },
    STATUS: {
        "Draft":          { color: "#2563eb", bg: "#dbeafe", icon: "📝" },
        "Scheduled":      { color: "#7c3aed", bg: "#ede9fe", icon: "🕐" },
        "Sending":        { color: "#d97706", bg: "#fef3c7", icon: "📤" },
        "Sent":           { color: "#065f46", bg: "#d1fae5", icon: "✅" },
        "Partially Sent": { color: "#92400e", bg: "#fef3c7", icon: "⚠️" },
        "Failed":         { color: "#991b1b", bg: "#fee2e2", icon: "❌" },
        "Cancelled":      { color: "#6b7280", bg: "#f3f4f6", icon: "🚫" }
    },
    SECT_COLORS: {
        "scheduling": "#7c3aed",
        "audience":   "#06b6d4",
        "message":    "#8b5cf6",
        "settings":   "#f59e0b",
        "content":    "#8b5cf6"
    }
};

// ─────────────────────────────────────────────────────────────────────────────
// FORM EVENTS — single consolidated handler
// ─────────────────────────────────────────────────────────────────────────────

frappe.ui.form.on(MB.DOCTYPE, {

    audience_group(frm) {
        // Clear employee segment fields if audience changes away from Employee
        if (frm.doc.audience_group !== "Employee") {
            ["segment_by", "filter_department", "filter_designation",
             "filter_branch", "filter_employment_type", "filter_gender", "filter_company"]
                .forEach(f => frm.set_value(f, ""));
        }
    },

    segment_by(frm) {
        // Clear sub-filter when segment changes
        ["filter_department", "filter_designation", "filter_branch",
         "filter_employment_type", "filter_gender", "filter_company"]
            .forEach(f => frm.set_value(f, ""));
    },

    is_test(frm) {
        if (!frm.doc.is_test) {
            frm.set_value("test_email", "");
            frm.set_value("test_phone_number", "");
        }
    },

    sms_message_body(frm) {
        _update_sms_counter(frm);
    },

    onload(frm) {
     //   _apply_styling(frm);
        _update_sms_counter(frm);
    },

    refresh(frm) {
     //   _apply_styling(frm);
        _render_buttons(frm);
        _render_stats_banner(frm);
        _apply_table_styling(frm);
        _update_sms_counter(frm);
    }
});

// ─────────────────────────────────────────────────────────────────────────────
// BUTTONS
// ─────────────────────────────────────────────────────────────────────────────

function _render_buttons(frm) {
    const doc        = frm.doc;
    const isNew      = frm.is_new();
    const isDraft    = doc.docstatus === 0;
    const isSubmitted= doc.docstatus === 1;
    const isSending  = doc.status === "Sending";
    const isSent     = !!doc.sent;
    const isCancelled= doc.status === "Cancelled";
    const isTest     = !!doc.is_test;

    // Recipients group — draft only
    if (isDraft) {
        frm.add_custom_button(__("Get Contacts"),
            () => _get_contacts(frm), __("Recipients"));
        frm.add_custom_button(__("Import CSV / Excel"),
            () => _show_import_dialog(frm), __("Recipients"));
    }

    // Message preview — whenever subject exists
    if (doc.subject) {
        frm.add_custom_button(__("Preview Message"),
            () => _preview_message(frm), __("Message"));
    }

    // ── PRIMARY SEND BUTTON
    // Visible on draft and submitted.
    // Hidden only when fully sent, actively sending, or cancelled.
    if (!isNew && !isSent && !isSending && !isCancelled) {
        const label  = isTest ? __("🧪 Send Test") : __("🚀 Send Message Blast");
        const bg     = isTest
            ? "linear-gradient(135deg,#d97706 0%,#b45309 100%)"
            : "linear-gradient(135deg,#2563eb 0%,#1d4ed8 100%)";
        const shadow = isTest
            ? "0 2px 8px rgba(217,119,6,0.40)"
            : "0 2px 8px rgba(37,99,235,0.35)";

        frm.add_custom_button(label, () => _confirm_send(frm))
            .removeClass("btn-default")
            .addClass("btn-primary")
            .css({
                background:     bg,
                color:          "#fff",
                "font-weight":  "700",
                border:         "none",
                "border-radius":"6px",
                padding:        "6px 18px",
                "box-shadow":   shadow,
                "letter-spacing":"0.3px"
            });
    }

    // Retry Failed
    if (isSubmitted && doc.failed_count > 0 && !isSending) {
        frm.add_custom_button(__("↩ Retry Failed"),
            () => _retry_failed(frm)).addClass("btn-warning");
    }

    // Cancel Schedule
    if (isSubmitted && doc.status === "Scheduled") {
        frm.add_custom_button(__("Cancel Schedule"),
            () => _cancel_scheduled(frm));
    }

    // Delivery Report
    if (isSubmitted && doc.sent_count > 0) {
        frm.add_custom_button(__("📊 Delivery Report"),
            () => _show_delivery_report(frm));
    }

    // Sending indicator
    if (isSending) _show_sending_indicator();
}

// ─────────────────────────────────────────────────────────────────────────────
// SEND FLOW: confirm → save (if draft) → submit → send API
// ─────────────────────────────────────────────────────────────────────────────

function _confirm_send(frm) {
    const doc    = frm.doc;
    const isTest = !!doc.is_test;
    const total  = doc.total_recipients || (doc.recipients || []).length || 0;
    const mt     = doc.message_type || "Email";

    // ── Pre-flight validation
    if (!doc.subject) {
        frappe.msgprint({ title: "Missing Subject",
            message: "Please enter a Subject / Title.", indicator: "orange" });
        return;
    }

    if (isTest) {
        if (mt.includes("Email") && !doc.test_email) {
            frappe.msgprint({ title: "Test Email Required",
                message: "You are in Test Mode. Please fill in the <b>Test Email</b> field.",
                indicator: "orange" });
            return;
        }
        if ((mt.includes("WhatsApp") || mt.includes("SMS")) && !doc.test_phone_number) {
            frappe.msgprint({ title: "Test Phone Required",
                message: "You are in Test Mode. Please fill in the <b>Test Phone Number</b> field.",
                indicator: "orange" });
            return;
        }
    } else {
        if (!total) {
            frappe.msgprint({ title: "No Recipients",
                message: "Please add recipients via <b>Get Contacts</b> or <b>Import CSV / Excel</b>.",
                indicator: "orange" });
            return;
        }
    }

    // ── Badges
    const testBadge = isTest ? `
        <div style="background:#fef3c7;border-left:4px solid #d97706;
                    padding:10px 14px;border-radius:6px;margin-bottom:14px;font-size:13px;">
            🧪 <strong>TEST MODE</strong> — message will be sent only to the test
            address / number, not to the ${total} recipient(s) in the table.
        </div>` : "";

    const scheduleBadge = (!isTest && doc.schedule && doc.schedule_time) ? `
        <div style="background:#ede9fe;border-left:4px solid #7c3aed;
                    padding:10px 14px;border-radius:6px;margin-bottom:14px;font-size:13px;">
            🕐 <strong>SCHEDULED</strong> for ${frappe.datetime.str_to_user(doc.schedule_time)}
        </div>` : "";

    const actionLabel = isTest ? "Send Test"
        : (doc.schedule && doc.schedule_time) ? "Schedule"
        : "Send Now";

    const recipientRow = isTest
        ? `<tr><td style="padding:5px 0;color:#64748b;width:40%;">Test Target</td>
               <td style="font-weight:600;">${doc.test_email || doc.test_phone_number || "—"}</td></tr>`
        : `<tr><td style="padding:5px 0;color:#64748b;width:40%;">Recipients</td>
               <td style="font-weight:600;">${total}</td></tr>`;

    const footerNote = isTest
        ? `<div style="margin-top:14px;padding:10px 14px;background:#fef3c7;
                       border-radius:6px;font-size:12px;color:#92400e;border:1px solid #fde68a;">
               🧪 This is a test send. No live recipients will be affected.
               The document will be saved, submitted, then the test message dispatched.
           </div>`
        : `<div style="margin-top:14px;padding:10px 14px;background:#f0fdf4;
                       border-radius:6px;font-size:12px;color:#065f46;border:1px solid #bbf7d0;">
               ✅ Clicking <strong>${actionLabel}</strong> will save, submit, and dispatch
               this Message Blast immediately.
           </div>`;

    frappe.confirm(`
        <div style="font-family:'Segoe UI',sans-serif;font-size:14px;line-height:1.8;">
            <div style="font-size:16px;font-weight:700;
                        color:${isTest ? "#92400e" : "#1e3a8a"};margin-bottom:14px;">
                ${isTest ? "🧪 Confirm Test Send" : "🚀 Confirm Message Blast"}
            </div>
            ${testBadge}${scheduleBadge}
            <table style="width:100%;border-collapse:collapse;font-size:13px;">
                <tr><td style="padding:5px 0;color:#64748b;width:40%;">Subject</td>
                    <td style="font-weight:600;">${doc.subject}</td></tr>
                <tr><td style="padding:5px 0;color:#64748b;">Channel</td>
                    <td style="font-weight:600;">${mt}</td></tr>
                ${recipientRow}
                <tr><td style="padding:5px 0;color:#64748b;">Priority</td>
                    <td style="font-weight:600;">${doc.priority || "Normal"}</td></tr>
            </table>
            ${footerNote}
        </div>`,
        () => _execute_send_flow(frm),
        "Cancel"
    );

    setTimeout(() => {
        $(".modal-footer .btn-primary")
            .text(actionLabel)
            .css(isTest ? { background: "#d97706", "border-color": "#d97706" } : {});
    }, 100);
}

function _execute_send_flow(frm) {
    // Already submitted → call API directly
    if (frm.doc.docstatus === 1) {
        _call_send_api(frm);
        return;
    }

    // Draft → save → submit → send
    frappe.show_progress("Preparing…", 0, 100, "Saving…");

    frm.save("Save", () => {
        frappe.show_progress("Preparing…", 33, 100, "Submitting…");

        frappe.call({
            method: "frappe.client.submit",
            args:   { doc: frm.doc },
            callback(r) {
                if (r.exc) {
                    frappe.hide_progress();
                    frappe.msgprint({ title: "Submit Failed",
                        message: "Could not submit the Message Blast. Check validation errors.",
                        indicator: "red" });
                    return;
                }
                frm.reload_doc();
                frappe.show_progress("Preparing…", 66, 100, "Sending…");
                setTimeout(() => { frappe.hide_progress(); _call_send_api(frm); }, 800);
            }
        });
    });
}

function _call_send_api(frm) {
    frappe.show_progress("Sending…", 80, 100, "Dispatching messages…");
    frappe.call({
        method:         `${MB.API}.send_blast`,
        args:           { docname: frm.doc.name },
        freeze:         true,
        freeze_message: __("📨 Sending Message Blast — please wait…"),
        callback(r) {
            frappe.hide_progress();
            if (r.exc) {
                frappe.msgprint({ title: "Send Failed",
                    message: "The blast could not be sent. Check the Error Log.",
                    indicator: "red" });
            } else {
                frappe.show_alert({ message: "📨 Message Blast sent!", indicator: "green" }, 6);
            }
            frm.reload_doc();
        }
    });
}

// ─────────────────────────────────────────────────────────────────────────────
// GET CONTACTS
// ─────────────────────────────────────────────────────────────────────────────

function _get_contacts(frm) {
    const doc     = frm.doc;
    const doctype = doc.audience_group;

    if (!doctype) {
        frappe.msgprint("Please select an Audience Group first."); return;
    }
    if (doctype === "Imported") {
        frappe.msgprint("Use 'Import CSV / Excel' for the Imported audience."); return;
    }

    let filters = [];
    let fields  = [];

    if (doctype === "Customer") {
        fields = ["name","customer_name","email_id","mobile_no",
                  "custom_email","salutation","customer_group","territory"];

    } else if (doctype === "Contact") {
        fields = ["name","first_name","last_name","email_id",
                  "mobile_no","salutation","company_name"];

    } else if (doctype === "Supplier") {
        fields = ["name","supplier_name","email_id","mobile_no",
                  "custom_email","salutation","supplier_group"];

    } else if (doctype === "Lead") {
        fields = ["name","lead_name","email_id","mobile_no",
                  "salutation","company_name","status"];
        filters.push(["status", "not in", ["Converted","Do Not Contact"]]);

    } else if (doctype === "Employee") {
        fields = ["name","employee_name","personal_email","company_email",
                  "cell_number","salutation","department","company"];
        const seg = doc.segment_by;
        if (seg === "Department"       && doc.filter_department)
            filters.push(["department",       "=", doc.filter_department]);
        if (seg === "Designation"      && doc.filter_designation)
            filters.push(["designation",      "=", doc.filter_designation]);
        if (seg === "Branch"           && doc.filter_branch)
            filters.push(["branch",           "=", doc.filter_branch]);
        if (seg === "Employment Type"  && doc.filter_employment_type)
            filters.push(["employment_type",  "=", doc.filter_employment_type]);
        if (seg === "Gender"           && doc.filter_gender)
            filters.push(["gender",           "=", doc.filter_gender]);
        if (seg === "Company"          && doc.filter_company)
            filters.push(["company",          "=", doc.filter_company]);
        filters.push(["status", "=", "Active"]);

    } else {
        frappe.msgprint(`Audience group '${doctype}' is not yet configured.`);
        return;
    }

    frappe.call({
        method: "frappe.client.get_list",
        args:   { doctype, fields, filters, limit_page_length: 0 },
        freeze: true,
        freeze_message: __("Fetching contacts…"),
        callback(r) {
            if (!r.message?.length) {
                frappe.msgprint("No records found for the selected criteria."); return;
            }

            const existing = new Set(
                (frm.doc.recipients || [])
                    .map(r => (r.email || "").toLowerCase().trim()).filter(Boolean)
            );

            let added = 0, dupes = 0;

            r.message.forEach(c => {
                const email = (
                    c.email_id || c.custom_email || c.company_email || c.personal_email || ""
                ).trim();

                if (email && existing.has(email.toLowerCase())) { dupes++; return; }

                const row = frm.add_child("recipients");
                row.record_id    = c.name;
                row.full_name    = c.customer_name || c.supplier_name || c.employee_name
                                   || c.lead_name
                                   || [c.first_name, c.last_name].filter(Boolean).join(" ")
                                   || c.name;
                row.email        = email;
                row.mobile_phone = c.mobile_no || c.cell_number || "";
                row.salutation   = c.salutation || "";
                row.company      = c.company_name || c.company || "";
                row.delivery_status = "Pending";

                if (email) existing.add(email.toLowerCase());
                added++;
            });

            frm.refresh_field("recipients");
            frm.set_value("total_recipients", frm.doc.recipients.length);

            frappe.show_alert({
                message: `✅ Added ${added} recipient(s)${dupes ? ` — ${dupes} duplicate(s) skipped` : ""}`,
                indicator: "green"
            }, 6);
        }
    });
}

// ─────────────────────────────────────────────────────────────────────────────
// IMPORT CSV / EXCEL
// ─────────────────────────────────────────────────────────────────────────────

function _show_import_dialog(frm) {
    const dialog = new frappe.ui.Dialog({
        title: "📥 Import Recipients from CSV / Excel",
        size:  "large",
        fields: [{
            fieldtype: "HTML",
            fieldname: "import_html",
            options: `
            <div style="font-family:'Segoe UI',sans-serif;">
                <div id="mb_drop_zone"
                     style="background:#eef7ff;border:1.5px dashed #3b82f6;border-radius:10px;
                            padding:24px;text-align:center;cursor:pointer;margin-bottom:16px;">
                    <div style="font-size:32px;margin-bottom:8px;">📂</div>
                    <div style="font-weight:600;color:#1e40af;font-size:15px;">
                        Drop your CSV or Excel file here
                    </div>
                    <div style="color:#64748b;font-size:13px;margin-top:4px;">
                        or <label for="mb_file_input"
                               style="color:#3b82f6;cursor:pointer;text-decoration:underline;">
                            browse to upload</label>
                    </div>
                    <input type="file" id="mb_file_input"
                           accept=".csv,.xlsx,.xls" style="display:none;">
                </div>
                <div id="mb_preview_area" style="display:none;">
                    <div style="font-weight:700;color:#1e3a8a;margin-bottom:8px;font-size:14px;">
                        📋 Map Columns
                    </div>
                    <div id="mb_column_mapper" style="margin-bottom:14px;"></div>
                    <div style="font-weight:600;color:#1e3a8a;margin-bottom:6px;font-size:13px;">
                        Preview — first 5 rows
                    </div>
                    <div id="mb_data_preview"
                         style="overflow-x:auto;max-height:220px;
                                border:1px solid #c7ddff;border-radius:6px;"></div>
                    <div id="mb_import_summary"
                         style="margin-top:10px;color:#64748b;font-size:13px;"></div>
                </div>
            </div>`
        }],
        primary_action_label: "Import",
        primary_action() { _execute_import(frm, dialog); }
    });

    dialog.show();

    setTimeout(() => {
        const inp  = document.getElementById("mb_file_input");
        const zone = document.getElementById("mb_drop_zone");
        if (!inp) return;
        inp.addEventListener("change", e => _handle_file(e.target.files[0], dialog));
        zone.addEventListener("click",    () => inp.click());
        zone.addEventListener("dragover", e => { e.preventDefault(); zone.style.background = "#dbeafe"; });
        zone.addEventListener("dragleave",() => { zone.style.background = "#eef7ff"; });
        zone.addEventListener("drop",     e => {
            e.preventDefault(); zone.style.background = "#eef7ff";
            _handle_file(e.dataTransfer.files[0], dialog);
        });
    }, 400);
}

function _handle_file(file, dialog) {
    if (!file) return;
    const ext = file.name.split(".").pop().toLowerCase();
    if      (ext === "csv")                   _parse_csv(file, dialog);
    else if (ext === "xlsx" || ext === "xls") _parse_excel(file, dialog);
    else frappe.msgprint("Please upload a .csv, .xlsx, or .xls file.");
}

function _parse_csv(file, dialog) {
    const reader = new FileReader();
    reader.onload = e => {
        const lines   = e.target.result.split(/\r?\n/).filter(l => l.trim());
        const headers = lines[0].split(",").map(h => h.replace(/^"|"$/g,"").trim());
        const rows    = lines.slice(1).map(line => {
            const vals = line.split(",").map(v => v.replace(/^"|"$/g,"").trim());
            const obj  = {};
            headers.forEach((h, i) => obj[h] = vals[i] || "");
            return obj;
        }).filter(r => Object.values(r).some(v => v));
        _show_preview(headers, rows, dialog);
    };
    reader.readAsText(file);
}

function _parse_excel(file, dialog) {
    const go = () => _do_excel(file, dialog);
    if (typeof XLSX === "undefined") {
        const s = document.createElement("script");
        s.src   = "https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js";
        s.onload = go;
        document.head.appendChild(s);
    } else go();
}

function _do_excel(file, dialog) {
    const reader = new FileReader();
    reader.onload = e => {
        const wb   = XLSX.read(new Uint8Array(e.target.result), { type: "array" });
        const data = XLSX.utils.sheet_to_json(wb.Sheets[wb.SheetNames[0]], { defval: "" });
        if (!data.length) { frappe.msgprint("No data found."); return; }
        _show_preview(Object.keys(data[0]), data, dialog);
    };
    reader.readAsArrayBuffer(file);
}

function _show_preview(headers, rows, dialog) {
    dialog._rows    = rows;
    dialog._headers = headers;

    const auto = h => {
        const l = h.toLowerCase();
        if (/name|full.?name/.test(l))   return "full_name";
        if (/email|e.mail/.test(l))      return "email";
        if (/phone|mobile|cell/.test(l)) return "mobile_phone";
        if (/salut|title|honor/.test(l)) return "salutation";
        if (/company|org/.test(l))       return "company";
        return "";
    };

    const FIELDS = {
        full_name:    "Full Name *",
        email:        "Email",
        mobile_phone: "Mobile Phone",
        salutation:   "Salutation",
        company:      "Company"
    };

    let mapHTML = `<table style="width:100%;border-collapse:collapse;font-size:13px;">
        <thead><tr>
            <th style="padding:8px;background:#f0f6ff;color:#1e3a8a;
                        border:1px solid #c7ddff;text-align:left;">Field</th>
            <th style="padding:8px;background:#f0f6ff;color:#1e3a8a;
                        border:1px solid #c7ddff;text-align:left;">CSV / Excel Column</th>
        </tr></thead><tbody>`;

    Object.entries(FIELDS).forEach(([f, label]) => {
        const matched = headers.find(h => auto(h) === f) || "";
        mapHTML += `<tr>
            <td style="padding:8px;border:1px solid #e2e8f0;font-weight:600;">${label}</td>
            <td style="padding:8px;border:1px solid #e2e8f0;">
                <select id="mb_map_${f}"
                        style="width:100%;padding:5px 8px;border-radius:6px;
                               border:1px solid #c7ddff;font-size:13px;">
                    <option value="">-- Not mapped --</option>
                    ${headers.map(h =>
                        `<option value="${h}"${h===matched?" selected":""}>${h}</option>`
                    ).join("")}
                </select>
            </td></tr>`;
    });
    mapHTML += "</tbody></table>";

    let tblHTML = `<table style="width:100%;border-collapse:collapse;font-size:12px;">
        <thead><tr>${headers.map(h =>
            `<th style="padding:7px 10px;background:#f0f6ff;color:#1e3a8a;
                        border:1px solid #c7ddff;white-space:nowrap;">${h}</th>`
        ).join("")}</tr></thead><tbody>`;
    rows.slice(0, 5).forEach((row, i) => {
        tblHTML += `<tr style="background:${i%2===0?"#fff":"#f9fbfd"};">
            ${headers.map(h =>
                `<td style="padding:6px 10px;border:1px solid #e2e8f0;">${row[h]??""}</td>`
            ).join("")}</tr>`;
    });
    tblHTML += "</tbody></table>";

    document.getElementById("mb_column_mapper").innerHTML  = mapHTML;
    document.getElementById("mb_data_preview").innerHTML   = tblHTML;
    document.getElementById("mb_import_summary").textContent =
        `📊 ${rows.length} row(s) found in file.`;
    document.getElementById("mb_preview_area").style.display = "block";
}

function _execute_import(frm, dialog) {
    const rows = dialog._rows;
    if (!rows?.length) { frappe.msgprint("Please upload a file first."); return; }

    const column_map = {};
    ["full_name","email","mobile_phone","salutation","company"].forEach(f => {
        const sel = document.getElementById(`mb_map_${f}`);
        if (sel?.value) column_map[f] = sel.value;
    });

    if (!column_map.full_name) {
        frappe.msgprint("Please map the 'Full Name' column."); return;
    }

    const doImport = () => frappe.call({
        method: `${MB.API}.import_recipients`,
        args: {
            docname:    frm.doc.name,
            rows:       JSON.stringify(rows),
            column_map: JSON.stringify(column_map)
        },
        freeze: true,
        freeze_message: "Importing recipients…",
        callback(r) {
            if (r.message) {
                const { added, skipped, total } = r.message;
                frappe.show_alert({
                    message: `✅ Imported ${added}. Skipped ${skipped} duplicates. Total: ${total}`,
                    indicator: "green"
                }, 7);
                frm.reload_doc();
                dialog.hide();
            }
        }
    });

    frm.is_new() ? frm.save("Save", doImport) : doImport();
}

// ─────────────────────────────────────────────────────────────────────────────
// RETRY FAILED
// ─────────────────────────────────────────────────────────────────────────────

function _retry_failed(frm) {
    frappe.confirm(`Retry sending to ${frm.doc.failed_count} failed recipient(s)?`, () => {
        frappe.call({
            method: `${MB.API}.retry_failed`,
            args:   { docname: frm.doc.name },
            freeze: true,
            freeze_message: "Retrying…",
            callback(r) {
                if (r.message) {
                    frappe.show_alert({
                        message: `↩ Retried ${r.message.retried} recipient(s).`,
                        indicator: "blue"
                    }, 5);
                    frm.reload_doc();
                }
            }
        });
    });
}

// ─────────────────────────────────────────────────────────────────────────────
// CANCEL SCHEDULED
// ─────────────────────────────────────────────────────────────────────────────

function _cancel_scheduled(frm) {
    frappe.confirm("Cancel this scheduled Message Blast?", () => {
        frappe.call({
            method: `${MB.API}.cancel_scheduled`,
            args:   { docname: frm.doc.name },
            callback(r) {
                if (r.message?.cancelled) {
                    frappe.show_alert({ message: "Schedule cancelled.", indicator: "orange" }, 5);
                    frm.reload_doc();
                }
            }
        });
    });
}

// ─────────────────────────────────────────────────────────────────────────────
// PREVIEW MESSAGE
// ─────────────────────────────────────────────────────────────────────────────

function _preview_message(frm) {
    const go = () => frappe.call({
        method: `${MB.API}.preview_message`,
        args:   { docname: frm.doc.name },
        callback(r) {
            if (!r.message) return;
            const { html, subject } = r.message;
            const d = new frappe.ui.Dialog({
                title: `🔍 Preview: ${subject}`,
                size:  "extra-large",
                fields: [{
                    fieldtype: "HTML",
                    options: `<div style="padding:16px;max-height:72vh;overflow-y:auto;
                                          border:1px solid #e2e8f0;border-radius:8px;
                                          background:#fff;">${html || "<em>No message content to preview.</em>"}</div>`
                }],
                primary_action_label: "Close",
                primary_action() { d.hide(); }
            });
            d.show();
        }
    });
    frm.is_new() ? frm.save("Save", go) : go();
}

// ─────────────────────────────────────────────────────────────────────────────
// DELIVERY REPORT
// ─────────────────────────────────────────────────────────────────────────────

function _show_delivery_report(frm) {
    const doc     = frm.doc;
    const total   = doc.total_recipients || 0;
    const sent    = doc.sent_count   || 0;
    const failed  = doc.failed_count || 0;
    const pending = doc.pending_count|| 0;
    const pct     = total ? Math.round((sent / total) * 100) : 0;

    const failRows = (doc.recipients || []).filter(r => r.delivery_status === "Failed");
    const failTable = failRows.length ? `
        <div style="margin-top:20px;">
            <div style="font-weight:700;font-size:13px;color:#991b1b;margin-bottom:8px;">
                Failed Recipients
            </div>
            <table style="width:100%;border-collapse:collapse;font-size:12px;">
                <thead><tr style="background:#fee2e2;">
                    <th style="padding:8px;border:1px solid #fca5a5;text-align:left;">Name</th>
                    <th style="padding:8px;border:1px solid #fca5a5;text-align:left;">Email / Phone</th>
                    <th style="padding:8px;border:1px solid #fca5a5;text-align:left;">Error</th>
                </tr></thead><tbody>
                ${failRows.map((r,i) => `
                <tr style="background:${i%2===0?"#fff":"#fef2f2"};">
                    <td style="padding:7px 8px;border:1px solid #fecaca;">${r.full_name}</td>
                    <td style="padding:7px 8px;border:1px solid #fecaca;">
                        ${r.email || r.mobile_phone || "—"}</td>
                    <td style="padding:7px 8px;border:1px solid #fecaca;
                               color:#dc2626;font-size:11px;">
                        ${r.error_message || "Unknown error"}</td>
                </tr>`).join("")}
            </tbody></table>
        </div>` : "";

    const d = new frappe.ui.Dialog({
        title: "📊 Delivery Report",
        size:  "large",
        fields: [{
            fieldtype: "HTML",
            options: `
            <div style="font-family:'Segoe UI',sans-serif;padding:8px;">
                <div style="display:grid;grid-template-columns:repeat(4,1fr);
                            gap:12px;margin-bottom:20px;">
                    ${_stat_card("Total",   total,   "#2563eb","#dbeafe")}
                    ${_stat_card("Sent",    sent,    "#065f46","#d1fae5")}
                    ${_stat_card("Failed",  failed,  "#991b1b","#fee2e2")}
                    ${_stat_card("Pending", pending, "#d97706","#fef3c7")}
                </div>
                <div style="margin-bottom:12px;">
                    <div style="font-size:13px;font-weight:600;color:#374151;margin-bottom:6px;">
                        Delivery Rate — ${pct}%
                    </div>
                    <div style="background:#e5e7eb;border-radius:999px;height:14px;overflow:hidden;">
                        <div style="background:linear-gradient(90deg,#10b981,#059669);
                                    height:100%;width:${pct}%;border-radius:999px;"></div>
                    </div>
                </div>
                ${failTable}
            </div>`
        }],
        primary_action_label: "Close",
        primary_action() { d.hide(); }
    });
    d.show();
}

function _stat_card(label, value, color, bg) {
    return `<div style="background:${bg};border-radius:10px;padding:14px;text-align:center;
                        border:1.5px solid ${color}30;">
        <div style="font-size:26px;font-weight:800;color:${color};">${value}</div>
        <div style="font-size:11px;font-weight:700;color:${color};letter-spacing:0.5px;
                    text-transform:uppercase;margin-top:2px;">${label}</div>
    </div>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// STATS BANNER
// ─────────────────────────────────────────────────────────────────────────────

function _render_stats_banner(frm) {
    $(".mb-stats-banner").remove();
    const doc = frm.doc;
    if (!doc.total_recipients) return;

    const total   = doc.total_recipients || 0;
    const sent    = doc.sent_count   || 0;
    const failed  = doc.failed_count || 0;
    const pending = doc.pending_count|| 0;
    const pct     = total ? Math.round((sent / total) * 100) : 0;

    const banner = $(`
        <div class="mb-stats-banner" style="
            display:flex;gap:12px;align-items:center;flex-wrap:wrap;
            background:linear-gradient(135deg,#f0f9ff 0%,#e0f2fe 100%);
            border:1.5px solid #bae6fd;border-radius:10px;
            padding:12px 18px;margin-bottom:14px;">
            <div style="display:flex;gap:20px;flex-wrap:wrap;flex:1;">
                ${_inline_stat("📋 Total",   total,   "#2563eb")}
                ${_inline_stat("✅ Sent",    sent,    "#065f46")}
                ${_inline_stat("❌ Failed",  failed,  "#991b1b")}
                ${_inline_stat("⏳ Pending", pending, "#d97706")}
            </div>
            <div style="flex:1;min-width:180px;">
                <div style="font-size:11px;color:#64748b;margin-bottom:4px;font-weight:600;">
                    DELIVERY RATE — ${pct}%
                </div>
                <div style="background:#e5e7eb;border-radius:999px;height:8px;overflow:hidden;">
                    <div style="background:linear-gradient(90deg,#10b981,#059669);
                                height:100%;width:${pct}%;border-radius:999px;"></div>
                </div>
            </div>
        </div>`);

    setTimeout(() => {
        const grid = frm.fields_dict.recipients?.grid?.wrapper;
        if (grid) $(grid).before(banner);
    }, 300);
}

function _inline_stat(label, value, color) {
    return `<div style="text-align:center;min-width:60px;">
        <div style="font-size:20px;font-weight:800;color:${color};">${value}</div>
        <div style="font-size:10px;color:${color};font-weight:600;letter-spacing:0.3px;">
            ${label}</div>
    </div>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// SMS COUNTER
// ─────────────────────────────────────────────────────────────────────────────

function _update_sms_counter(frm) {
    if (!frm.fields_dict.sms_message_body) return;
    const len  = (frm.doc.sms_message_body || "").length;
    const msgs = Math.ceil(len / 160) || 1;
    frm.set_df_property("sms_message_body", "description",
        `Merge tags: {{full_name}}. Keep under 160 characters for a single SMS.${
            len > 0 ? ` — <strong>${len} chars / ${msgs} SMS part${msgs>1?"s":""}</strong>` : ""}`);
}

// ─────────────────────────────────────────────────────────────────────────────
// SENDING SPINNER
// ─────────────────────────────────────────────────────────────────────────────

function _show_sending_indicator() {
    $(".mb-sending-indicator").remove();
    if (!$("#mb-spin-style").length) {
        $("head").append(`<style id="mb-spin-style">
            @keyframes mb-spin { to { transform:rotate(360deg); } }
        </style>`);
    }
    $(".page-actions").append(`
        <div class="mb-sending-indicator"
             style="display:inline-flex;align-items:center;gap:8px;
                    background:#fef3c7;border:1.5px solid #f59e0b;
                    border-radius:8px;padding:6px 14px;font-size:13px;
                    font-weight:600;color:#92400e;margin-left:10px;">
            <span style="display:inline-block;width:12px;height:12px;
                         border:2px solid #f59e0b;border-top-color:transparent;
                         border-radius:50%;animation:mb-spin 0.8s linear infinite;"></span>
            Sending in progress…
        </div>`);
}

// ─────────────────────────────────────────────────────────────────────────────
// STYLING
// ─────────────────────────────────────────────────────────────────────────────

function _apply_styling(frm) {
    setTimeout(() => {
        _apply_status_badge(frm);
        _apply_section_colors(frm);
    }, 200);
}

function _apply_status_badge(frm) {
    const status = frm.doc.status || "Draft";
    const cfg    = MB.STATUS[status] || { color: "#6b7280", bg: "#f3f4f6", icon: "📄" };

    $(".mb-status-badge").remove();
    $(".page-title").append(`
        <div class="mb-status-badge" style="
            display:inline-flex;align-items:center;gap:6px;
            padding:5px 14px;border-radius:20px;font-weight:700;font-size:12px;
            color:${cfg.color};background:${cfg.bg};margin-left:12px;
            box-shadow:0 2px 8px ${cfg.color}30;border:2px solid ${cfg.color}40;
            letter-spacing:0.3px;">
            <span>${cfg.icon}</span><span>${status.toUpperCase()}</span>
        </div>`);

    $(".page-head").css({
        "border-bottom": `4px solid ${cfg.color}`,
        "box-shadow":    `0 4px 12px ${cfg.color}20`,
        "background":    `linear-gradient(135deg,${cfg.bg} 0%,#ffffff 100%)`
    });
}

function _apply_section_colors(frm) {
    Object.keys(frm.fields_dict || {}).forEach(fn => {
        const field = frm.fields_dict[fn];
        if (!field || field.df.fieldtype !== "Section Break" || !field.df.label) return;
        const label = field.df.label.toLowerCase();
        let color = "#6b7280";
        for (const [kw, c] of Object.entries(MB.SECT_COLORS)) {
            if (label.includes(kw)) { color = c; break; }
        }
        $(field.wrapper).find(".form-section-heading,.section-head").css({
            "background":     `linear-gradient(135deg,${color}15 0%,${color}08 100%)`,
            "border-left":    `4px solid ${color}`,
            "border-radius":  "8px",
            "padding":        "12px 16px",
            "font-weight":    "700",
            "font-size":      "12px",
            "color":          color,
            "letter-spacing": "0.5px",
            "text-transform": "uppercase",
            "margin-bottom":  "12px"
        });
    });
}

function _apply_table_styling(frm) {
    setTimeout(() => {
        const grid = frm.fields_dict.recipients?.grid;
        if (!grid) return;

        grid.wrapper.find(".grid-heading-row").css({
            "background":     MB.STYLE.table_header_bg,
            "color":          MB.STYLE.table_header_text,
            "font-weight":    "700",
            "text-transform": "uppercase",
            "font-size":      "11px",
            "letter-spacing": "0.8px"
        });

        grid.wrapper.find(".grid-row").each((i, row) => {
            const $row   = $(row);
            const status = $row.find("[data-fieldname='delivery_status'] .static-area")
                              .text().trim();
            let bg = i % 2 === 0 ? MB.STYLE.row1 : MB.STYLE.row2;
            if (status === "Sent")   bg = "#f0fdf4";
            if (status === "Failed") bg = "#fef2f2";
            $row.css({
                "background-color": bg,
                "border-bottom":    `1px solid ${MB.STYLE.table_border}`
            });
        });

        grid.wrapper.css({
            "border":        `1px solid ${MB.STYLE.table_border}`,
            "border-radius": "8px",
            "overflow":      "hidden"
        });
    }, 300);
}

console.log("✅ Message Blast — Enterprise Messaging Module Loaded");