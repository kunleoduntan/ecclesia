// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

// communique/communique/doctype/communique/communique.js
// Copyright (c) 2026, Value Impacts Consulting
//
// FLOW:
//   🧪 Send Test       → save only (never submit) → send_test      → reload
//   🚀 Send Communiqué → save → submit → send_communique            → reload

const COM = {
    DOCTYPE: "Communique",
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
    }
};

// ─────────────────────────────────────────────────────────────────────────────
// FORM EVENTS
// ─────────────────────────────────────────────────────────────────────────────

frappe.ui.form.on(COM.DOCTYPE, {

    audience_group(frm) {
        // Clear filter fields when audience changes
        ["filter","gender","marital_status","branch","department","member_status"]
            .forEach(f => frm.set_value(f, ""));
    },

    filter(frm) {
        if (!frm.doc.filter) {
            ["gender","marital_status","branch","department","member_status"]
                .forEach(f => frm.set_value(f, ""));
        }
    },

    is_test(frm) {
        if (!frm.doc.is_test) {
            frm.set_value("test_email", "");
            frm.set_value("test_phone_number", "");
        }
    },

    sms_message_body(frm) { _sms_counter(frm); },

    onload(frm) {
        //_apply_styling(frm);
        _sms_counter(frm);
    },

    refresh(frm) {
        //_apply_styling(frm);
        _render_buttons(frm);
        _render_stats_banner(frm);
        _apply_table_styling(frm);
        _sms_counter(frm);
    }
});

// ─────────────────────────────────────────────────────────────────────────────
// BUTTONS
// ─────────────────────────────────────────────────────────────────────────────

function _render_buttons(frm) {
    const doc         = frm.doc;
    const isNew       = frm.is_new();
    const isSent      = doc.status === "Sent";
    const isCancelled = doc.status === "Cancelled";

    // ── Recipients ────────────────────────────────────────────────────────
    frm.add_custom_button(__("Get Contacts"),
        () => _get_contacts(frm), __("Recipients"));
    frm.add_custom_button(__("Import CSV / Excel"),
        () => _show_import_dialog(frm), __("Recipients"));

    // ── Message ───────────────────────────────────────────────────────────
    frm.add_custom_button(__("👁 Preview Email"),
        () => _preview(frm), __("Message"));

    // ── 🧪 Send Test — always visible (except cancelled)
    if (!isNew && !isCancelled) {
        frm.add_custom_button(__("🧪 Send Test"), () => _do_test(frm))
            .css({
                background:      "linear-gradient(135deg,#d97706 0%,#b45309 100%)",
                color:           "#fff",
                "font-weight":   "700",
                border:          "none",
                "border-radius": "6px",
                padding:         "6px 18px",
                "box-shadow":    "0 2px 8px rgba(217,119,6,0.40)"
            });
    }

    // ── 🚀 Send Communiqué — hidden only when fully sent or cancelled
    if (!isNew && !isSent && !isCancelled) {
        frm.add_custom_button(__("🚀 Send Communiqué"), () => _do_send_all(frm))
            .removeClass("btn-default")
            .addClass("btn-primary")
            .css({
                background:      "linear-gradient(135deg,#065f46 0%,#059669 100%)",
                color:           "#fff",
                "font-weight":   "700",
                border:          "none",
                "border-radius": "6px",
                padding:         "6px 18px",
                "box-shadow":    "0 2px 8px rgba(6,95,70,0.40)"
            });
    }

    // ── Extras ────────────────────────────────────────────────────────────
    if (doc.docstatus === 1 && doc.failed_count > 0)
        frm.add_custom_button(__("↩ Retry Failed"), () => _retry(frm))
           .addClass("btn-warning");

    if (doc.docstatus === 1 && doc.status === "Scheduled")
        frm.add_custom_button(__("Cancel Schedule"), () => _cancel_schedule(frm));

    if (doc.sent_count > 0)
        frm.add_custom_button(__("📊 Delivery Report"), () => _delivery_report(frm));
}

// ─────────────────────────────────────────────────────────────────────────────
// 🧪 TEST SEND — save only, NEVER submit
// ─────────────────────────────────────────────────────────────────────────────

function _do_test(frm) {
    const doc = frm.doc;
    const mt  = doc.message_type || "Email";

    if (!doc.subject) {
        frappe.msgprint({ title: "Missing Subject",
            message: "Please enter a Subject.", indicator: "orange" }); return;
    }
    if (mt.includes("Email") && !doc.test_email) {
        frappe.msgprint({ title: "Test Email Required",
            message: "Please fill in the <b>Test Email</b> field.",
            indicator: "orange" }); return;
    }
    if ((mt.includes("WhatsApp") || mt.includes("SMS")) && !doc.test_phone_number) {
        frappe.msgprint({ title: "Test Phone Required",
            message: "Please fill in the <b>Test Phone Number</b> field.",
            indicator: "orange" }); return;
    }

    const target = doc.test_email || doc.test_phone_number || "—";

    frappe.confirm(`
        <div style="font-family:'Segoe UI',sans-serif;font-size:14px;line-height:1.8;">
            <div style="font-size:16px;font-weight:700;color:#92400e;margin-bottom:14px;">
                🧪 Confirm Test Send</div>
            <div style="background:#fef3c7;border-left:4px solid #d97706;
                        padding:10px 14px;border-radius:6px;margin-bottom:14px;
                        font-size:13px;">
                TEST MODE — sent only to the test address. No live recipients affected.
            </div>
            <table style="width:100%;border-collapse:collapse;font-size:13px;">
                <tr><td style="padding:5px 0;color:#64748b;width:40%;">Subject</td>
                    <td style="font-weight:600;">${doc.subject}</td></tr>
                <tr><td style="padding:5px 0;color:#64748b;">Channel</td>
                    <td style="font-weight:600;">${mt}</td></tr>
                <tr><td style="padding:5px 0;color:#64748b;">Test Target</td>
                    <td style="font-weight:600;">${target}</td></tr>
            </table>
        </div>`,
        () => {
            const _send = () => frappe.call({
                method:         "ecclesia.ecclesia.doctype.communique.communique.send_test",
                args:           { docname: frm.doc.name },
                freeze:         true,
                freeze_message: __("📨 Sending test message…"),
                callback(r) {
                    if (r.exc) {
                        frappe.msgprint({ title: "Test Failed",
                            message: "Check the Error Log for details.",
                            indicator: "red" });
                    }
                    frm.reload_doc();
                }
            });
            // Save only — do NOT submit
            frm.is_new()
                ? frm.save("Save", _send)
                : (frm.doc.docstatus === 0 && frm.is_dirty()
                    ? frm.save("Save", _send)
                    : _send());
        },
        "Cancel"
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// 🚀 SEND ALL — save → submit → send_communique
// ─────────────────────────────────────────────────────────────────────────────

function _do_send_all(frm) {
    const doc   = frm.doc;
    const total = doc.total_recipients || (doc.recipients || []).length || 0;
    const mt    = doc.message_type || "Email";

    if (!doc.subject) {
        frappe.msgprint({ title: "Missing Subject",
            message: "Please enter a Subject.", indicator: "orange" }); return;
    }
    if (!total) {
        frappe.msgprint({ title: "No Recipients",
            message: "Add recipients via <b>Get Contacts</b> or <b>Import CSV / Excel</b>.",
            indicator: "orange" }); return;
    }

    const scheduleBadge = (doc.schedule && doc.schedule_time) ? `
        <div style="background:#ede9fe;border-left:4px solid #7c3aed;
                    padding:10px 14px;border-radius:6px;margin-bottom:14px;
                    font-size:13px;">
            🕐 <strong>SCHEDULED</strong> for
            ${frappe.datetime.str_to_user(doc.schedule_time)}
        </div>` : "";

    const actionLabel = (doc.schedule && doc.schedule_time) ? "Schedule" : "Send Now";

    frappe.confirm(`
        <div style="font-family:'Segoe UI',sans-serif;font-size:14px;line-height:1.8;">
            <div style="font-size:16px;font-weight:700;color:#065f46;margin-bottom:14px;">
                📣 Confirm Communiqué</div>
            ${scheduleBadge}
            <table style="width:100%;border-collapse:collapse;font-size:13px;">
                <tr><td style="padding:5px 0;color:#64748b;width:40%;">Subject</td>
                    <td style="font-weight:600;">${doc.subject}</td></tr>
                <tr><td style="padding:5px 0;color:#64748b;">Channel</td>
                    <td style="font-weight:600;">${mt}</td></tr>
                <tr><td style="padding:5px 0;color:#64748b;">Recipients</td>
                    <td style="font-weight:600;">${total}</td></tr>
                <tr><td style="padding:5px 0;color:#64748b;">Priority</td>
                    <td style="font-weight:600;">${doc.priority || "Normal"}</td></tr>
            </table>
            <div style="margin-top:14px;padding:10px 14px;background:#f0fdf4;
                        border-radius:6px;font-size:12px;color:#065f46;
                        border:1px solid #bbf7d0;">
                ✅ Clicking <strong>${actionLabel}</strong> will save, submit, and dispatch.
            </div>
        </div>`,
        () => _execute_send_all(frm), "Cancel"
    );
    setTimeout(() => $(".modal-footer .btn-primary").text(actionLabel), 100);
}

function _execute_send_all(frm) {
    if (frm.doc.docstatus === 1) { _call_send_all_api(frm); return; }
    frm.save("Save", () => {
        frappe.call({
            method:         "frappe.client.submit",
            args:           { doc: frm.doc },
            freeze:         true,
            freeze_message: __("Submitting…"),
            callback(r) {
                if (r.exc) {
                    frappe.msgprint({ title: "Submit Failed",
                        message: "Could not submit. Check validation errors.",
                        indicator: "red" }); return;
                }
                frm.reload_doc();
                _call_send_all_api(frm);
            }
        });
    });
}

function _call_send_all_api(frm) {
    frappe.call({
        method:         "ecclesia.ecclesia.doctype.communique.communique.send_communique",
        args:           { docname: frm.doc.name },
        freeze:         true,
        freeze_message: __("📨 Sending communiqué…"),
        callback(r) {
            if (r.exc) {
                frappe.msgprint({ title: "Send Failed",
                    message: "Failed to send. Check error logs.", indicator: "red" });
            }
            frm.reload_doc();
        }
    });
}

// ─────────────────────────────────────────────────────────────────────────────
// GET CONTACTS — standard ERPNext business doctypes only
// ─────────────────────────────────────────────────────────────────────────────

function _get_contacts(frm) {
    const doc     = frm.doc;
    const doctype = doc.audience_group;

    if (!doctype || doctype === "Imported") {
        frappe.msgprint(doctype === "Imported"
            ? "Use 'Import CSV / Excel' for the Imported audience."
            : "Please select an Audience Group first.");
        return;
    }

    let filters = [], fields = [];

    if (doctype === "Customer") {
        fields  = ["name","customer_name","email_id", "custom_email", "mobile_no","salutation"];

    } else if (doctype === "Supplier") {
        fields  = ["name","supplier_name","email_id", "custom_email", "mobile_no"];

    } else if (doctype === "Contact") {
        fields  = ["name","first_name","last_name","email_id", "custom_email", "mobile_no","salutation"];

    } else if (doctype === "Lead") {
        fields  = ["name","lead_name","email_id", "custom_email", "mobile_no","salutation"];
        filters.push(["status","not in",["Converted","Do Not Contact"]]);

    } else if (doctype === "Employee") {
        fields  = ["name","employee_name","personal_email", "company_email", "cell_number",
                   "salutation","gender","department","branch"];
        filters.push(["status","=","Active"]);

        const f = doc.filter;
        if      (f === "Gender"          && doc.gender)
            filters.push(["gender","=",doc.gender]);
        else if (f === "Marital Status"  && doc.marital_status)
            filters.push(["marital_status","=",doc.marital_status]);
        else if (f === "Branch"          && doc.branch)
            filters.push(["branch","=",doc.branch]);
        else if (f === "Department"      && doc.department)
            filters.push(["department","=",doc.department]);
        else if (f === "Employment Type" && doc.member_status)
            filters.push(["employment_type","=",doc.member_status]);

    } else {
        frappe.msgprint(`No fetch logic defined for '${doctype}'.`); return;
    }

    frappe.call({
        method: "frappe.client.get_list",
        args:   { doctype, fields, filters, limit_page_length: 0 },
        freeze: true,
        freeze_message: __("Fetching contacts…"),
        callback(r) {
            if (!r.message?.length) {
                frappe.msgprint("No records found."); return;
            }
            const existing = new Set(
                (frm.doc.recipients || [])
                    .map(x => (x.email || "").toLowerCase().trim()).filter(Boolean)
            );
            let added = 0, dupes = 0;

            r.message.forEach(c => {
                const email = (
                    c.email_id || c.personal_email || c.email || c.custom_email || c.company_email || ""
                ).trim();
                if (email && existing.has(email.toLowerCase())) { dupes++; return; }

                const row        = frm.add_child("recipients");
                row.source_id    = c.name;
                row.source_type  = doctype;
                row.full_name    = c.full_name    || c.customer_name
                                || c.supplier_name || c.employee_name
                                || c.lead_name
                                || [c.first_name, c.last_name].filter(Boolean).join(" ");
                row.email        = email;
                row.mobile_phone = c.mobile_no || c.cell_number || c.mobile_phone || "";
                //row.salutation   = c.salutation || "";
                row.delivery_status = "Pending";

                if (email) existing.add(email.toLowerCase());
                added++;
            });

            frm.refresh_field("recipients");
            frm.set_value("total_recipients", frm.doc.recipients.length);
            frappe.show_alert({
                message: `✅ Added ${added}${dupes ? ` — ${dupes} duplicate(s) skipped` : ""}`,
                indicator: "green"
            }, 6);
        }
    });
}

// ─────────────────────────────────────────────────────────────────────────────
// IMPORT CSV / EXCEL
// ─────────────────────────────────────────────────────────────────────────────

function _show_import_dialog(frm) {
    const d = new frappe.ui.Dialog({
        title: "📥 Import Recipients",
        size:  "large",
        fields: [{ fieldtype: "HTML", options: `
            <div style="font-family:'Segoe UI',sans-serif;">
                <div id="com_drop_zone"
                     style="background:#eef7ff;border:1.5px dashed #3b82f6;
                            border-radius:10px;padding:24px;text-align:center;
                            cursor:pointer;margin-bottom:16px;">
                    <div style="font-size:32px;margin-bottom:8px;">📂</div>
                    <div style="font-weight:600;color:#1e40af;font-size:15px;">
                        Drop CSV or Excel file here</div>
                    <div style="color:#64748b;font-size:13px;margin-top:4px;">
                        or <label for="com_file_inp"
                                  style="color:#3b82f6;cursor:pointer;
                                         text-decoration:underline;">browse</label>
                    </div>
                    <input type="file" id="com_file_inp"
                           accept=".csv,.xlsx,.xls" style="display:none;">
                </div>
                <div id="com_preview_area" style="display:none;">
                    <div style="font-weight:700;color:#1e3a8a;margin-bottom:8px;">
                        📋 Map Columns</div>
                    <div id="com_mapper" style="margin-bottom:14px;"></div>
                    <div style="font-weight:600;color:#1e3a8a;margin-bottom:6px;
                                font-size:13px;">Preview — first 5 rows</div>
                    <div id="com_preview"
                         style="overflow-x:auto;max-height:200px;
                                border:1px solid #c7ddff;border-radius:6px;"></div>
                    <div id="com_summary"
                         style="margin-top:10px;color:#64748b;font-size:13px;"></div>
                </div>
            </div>`
        }],
        primary_action_label: "Import",
        primary_action() { _do_import(frm, d); }
    });
    d.show();
    setTimeout(() => {
        const inp  = document.getElementById("com_file_inp");
        const zone = document.getElementById("com_drop_zone");
        if (!inp) return;
        inp.addEventListener("change",  e => _handle_file(e.target.files[0], d));
        zone.addEventListener("click",    () => inp.click());
        zone.addEventListener("dragover", e => { e.preventDefault();
            zone.style.background = "#dbeafe"; });
        zone.addEventListener("dragleave",() => { zone.style.background = "#eef7ff"; });
        zone.addEventListener("drop",     e => {
            e.preventDefault(); zone.style.background = "#eef7ff";
            _handle_file(e.dataTransfer.files[0], d);
        });
    }, 400);
}

function _handle_file(file, d) {
    if (!file) return;
    const ext = file.name.split(".").pop().toLowerCase();
    if      (ext === "csv")                   _parse_csv(file, d);
    else if (ext === "xlsx" || ext === "xls") _parse_excel(file, d);
    else frappe.msgprint("Upload a .csv, .xlsx, or .xls file.");
}

function _parse_csv(file, d) {
    const r = new FileReader();
    r.onload = e => {
        const lines   = e.target.result.split(/\r?\n/).filter(l => l.trim());
        const headers = lines[0].split(",").map(h => h.replace(/^"|"$/g,"").trim());
        const rows    = lines.slice(1).map(line => {
            const vals = line.split(",").map(v => v.replace(/^"|"$/g,"").trim());
            const obj  = {}; headers.forEach((h,i) => obj[h] = vals[i] || "");
            return obj;
        }).filter(r => Object.values(r).some(v => v));
        _show_preview(headers, rows, d);
    };
    r.readAsText(file);
}

function _parse_excel(file, d) {
    const go = () => {
        const r = new FileReader();
        r.onload = e => {
            const wb   = XLSX.read(new Uint8Array(e.target.result), { type:"array" });
            const data = XLSX.utils.sheet_to_json(
                wb.Sheets[wb.SheetNames[0]], { defval:"" });
            if (!data.length) { frappe.msgprint("No data found."); return; }
            _show_preview(Object.keys(data[0]), data, d);
        };
        r.readAsArrayBuffer(file);
    };
    if (typeof XLSX === "undefined") {
        const s = document.createElement("script");
        s.src   = "https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js";
        s.onload = go; document.head.appendChild(s);
    } else go();
}

function _show_preview(headers, rows, d) {
    d._rows = rows;
    const auto = h => {
        const l = h.toLowerCase();
        if (/name|full.?name/.test(l))   return "full_name";
        if (/email|e.mail/.test(l))      return "email";
        if (/phone|mobile|cell/.test(l)) return "mobile_phone";
        if (/salut|title/.test(l))       return "salutation";
        return "";
    };
    const LABELS = { full_name:"Full Name *", email:"Email",
                     mobile_phone:"Mobile Phone", salutation:"Salutation" };
    let map = `<table style="width:100%;border-collapse:collapse;font-size:13px;">
        <thead><tr>
            <th style="padding:8px;background:#f0f6ff;color:#1e3a8a;
                        border:1px solid #c7ddff;">Field</th>
            <th style="padding:8px;background:#f0f6ff;color:#1e3a8a;
                        border:1px solid #c7ddff;">Column</th>
        </tr></thead><tbody>`;
    Object.entries(LABELS).forEach(([f, lbl]) => {
        const matched = headers.find(h => auto(h) === f) || "";
        map += `<tr>
            <td style="padding:8px;border:1px solid #e2e8f0;font-weight:600;">${lbl}</td>
            <td style="padding:8px;border:1px solid #e2e8f0;">
                <select id="com_map_${f}"
                        style="width:100%;padding:5px 8px;border-radius:6px;
                               border:1px solid #c7ddff;font-size:13px;">
                    <option value="">-- Not mapped --</option>
                    ${headers.map(h =>
                        `<option value="${h}"${h===matched?" selected":""}>${h}</option>`
                    ).join("")}
                </select></td></tr>`;
    });
    map += "</tbody></table>";
    let tbl = `<table style="width:100%;border-collapse:collapse;font-size:12px;">
        <thead><tr>${headers.map(h =>
            `<th style="padding:7px 10px;background:#f0f6ff;color:#1e3a8a;
                        border:1px solid #c7ddff;white-space:nowrap;">${h}</th>`
        ).join("")}</tr></thead><tbody>`;
    rows.slice(0,5).forEach((row,i) => {
        tbl += `<tr style="background:${i%2===0?"#fff":"#f9fbfd"};">
            ${headers.map(h =>
                `<td style="padding:6px 10px;border:1px solid #e2e8f0;">
                    ${row[h]??""}</td>`).join("")}</tr>`;
    });
    tbl += "</tbody></table>";
    document.getElementById("com_mapper").innerHTML  = map;
    document.getElementById("com_preview").innerHTML = tbl;
    document.getElementById("com_summary").textContent = `📊 ${rows.length} rows found.`;
    document.getElementById("com_preview_area").style.display = "block";
}

function _do_import(frm, d) {
    const rows = d._rows;
    if (!rows?.length) { frappe.msgprint("Upload a file first."); return; }
    const column_map = {};
    ["full_name","email","mobile_phone","salutation"].forEach(f => {
        const sel = document.getElementById(`com_map_${f}`);
        if (sel?.value) column_map[f] = sel.value;
    });
    if (!column_map.full_name) {
        frappe.msgprint("Map the 'Full Name' column."); return;
    }
    const run = () => frappe.call({
        method: "ecclesia.ecclesia.doctype.communique.communique.import_recipients",
        args:   { docname: frm.doc.name,
                  rows: JSON.stringify(rows),
                  column_map: JSON.stringify(column_map) },
        freeze: true, freeze_message: "Importing…",
        callback(r) {
            if (r.message) {
                frappe.show_alert({
                    message: `✅ Imported ${r.message.added}. `
                           + `Skipped ${r.message.skipped}. `
                           + `Total: ${r.message.total}`,
                    indicator: "green"
                }, 7);
                frm.reload_doc(); d.hide();
            }
        }
    });
    frm.is_new() ? frm.save("Save", run) : run();
}

// ─────────────────────────────────────────────────────────────────────────────
// PREVIEW
// ─────────────────────────────────────────────────────────────────────────────

function _preview(frm) {
    if (!frm.doc.subject && !frm.doc.message_body && !frm.doc.message_tx_html) {
        frappe.msgprint({ title: "Nothing to Preview",
            message: "Please add a Subject and message body first.",
            indicator: "orange" }); return;
    }
    const go = () => frappe.call({
        method: "ecclesia.ecclesia.doctype.communique.communique.preview_message",
        args:   { docname: frm.doc.name },
        freeze: true, freeze_message: __("Building preview…"),
        callback(r) {
            if (!r.message) return;
            const d = new frappe.ui.Dialog({
                title: `👁 Preview — ${r.message.subject}`,
                size:  "extra-large",
                fields: [{ fieldtype: "HTML",
                    options: `
                    <div style="background:#f4f6f9;padding:20px;border-radius:8px;
                                max-height:75vh;overflow-y:auto;">
                        <div style="max-width:640px;margin:0 auto;
                                    box-shadow:0 4px 24px rgba(0,0,0,0.12);
                                    border-radius:12px;overflow:hidden;">
                            ${r.message.html || "<p>No content.</p>"}
                        </div>
                    </div>`
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
// RETRY / CANCEL SCHEDULE
// ─────────────────────────────────────────────────────────────────────────────

function _retry(frm) {
    frappe.confirm(`Retry ${frm.doc.failed_count} failed recipient(s)?`, () =>
        frappe.call({
            method:         "ecclesia.ecclesia.doctype.communique.communique.retry_failed",
            args:           { docname: frm.doc.name },
            freeze:         true, freeze_message: "Retrying…",
            callback(r) {
                if (r.message) {
                    frappe.msgprint({
                        title:     "Retry Complete",
                        indicator: r.message.failed ? "orange" : "green",
                        message:   `✅ Sent: ${r.message.sent || 0} &nbsp;`
                                 + `❌ Failed: ${r.message.failed || 0}`
                    });
                    frm.reload_doc();
                }
            }
        })
    );
}

function _cancel_schedule(frm) {
    frappe.confirm("Cancel this scheduled communiqué?", () =>
        frappe.call({
            method: "ecclesia.ecclesia.doctype.communique.communique.cancel_scheduled",
            args:   { docname: frm.doc.name },
            callback(r) {
                if (r.message?.cancelled) {
                    frappe.show_alert({ message:"Schedule cancelled.",
                        indicator:"orange" }, 5);
                    frm.reload_doc();
                }
            }
        })
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// DELIVERY REPORT
// ─────────────────────────────────────────────────────────────────────────────

function _delivery_report(frm) {
    const doc     = frm.doc;
    const total   = doc.total_recipients || 0;
    const sent    = doc.sent_count       || 0;
    const failed  = doc.failed_count     || 0;
    const pending = doc.pending_count    || 0;
    const pct     = total ? Math.round((sent / total) * 100) : 0;
    const fail_rows = (doc.recipients || []).filter(r => r.delivery_status === "Failed");
    const fail_tbl  = fail_rows.length ? `
        <div style="margin-top:20px;">
            <div style="font-weight:700;font-size:13px;color:#991b1b;margin-bottom:8px;">
                Failed Recipients</div>
            <table style="width:100%;border-collapse:collapse;font-size:12px;">
                <thead><tr style="background:#fee2e2;">
                    <th style="padding:8px;border:1px solid #fca5a5;text-align:left;">Name</th>
                    <th style="padding:8px;border:1px solid #fca5a5;text-align:left;">
                        Email / Phone</th>
                    <th style="padding:8px;border:1px solid #fca5a5;text-align:left;">Error</th>
                </tr></thead><tbody>
                ${fail_rows.map((r,i) => `
                <tr style="background:${i%2===0?"#fff":"#fef2f2"};">
                    <td style="padding:7px 8px;border:1px solid #fecaca;">${r.full_name}</td>
                    <td style="padding:7px 8px;border:1px solid #fecaca;">
                        ${r.email || r.mobile_phone || "—"}</td>
                    <td style="padding:7px 8px;border:1px solid #fecaca;
                               color:#dc2626;font-size:11px;">
                        ${r.error_message || "Unknown"}</td>
                </tr>`).join("")}
            </tbody></table>
        </div>` : "";
    const d = new frappe.ui.Dialog({
        title: "📊 Delivery Report",
        size:  "large",
        fields: [{ fieldtype:"HTML", options:`
            <div style="font-family:'Segoe UI',sans-serif;padding:8px;">
                <div style="display:grid;grid-template-columns:repeat(4,1fr);
                            gap:12px;margin-bottom:20px;">
                    ${_stat("Total",   total,   "#2563eb","#dbeafe")}
                    ${_stat("Sent",    sent,    "#065f46","#d1fae5")}
                    ${_stat("Failed",  failed,  "#991b1b","#fee2e2")}
                    ${_stat("Pending", pending, "#d97706","#fef3c7")}
                </div>
                <div style="font-size:13px;font-weight:600;color:#374151;
                            margin-bottom:6px;">Delivery Rate — ${pct}%</div>
                <div style="background:#e5e7eb;border-radius:999px;
                            height:14px;overflow:hidden;">
                    <div style="background:linear-gradient(90deg,#10b981,#059669);
                                height:100%;width:${pct}%;border-radius:999px;"></div>
                </div>
                ${fail_tbl}
            </div>` }],
        primary_action_label: "Close",
        primary_action() { d.hide(); }
    });
    d.show();
}

function _stat(label, value, color, bg) {
    return `<div style="background:${bg};border-radius:10px;padding:14px;
                        text-align:center;border:1.5px solid ${color}30;">
        <div style="font-size:26px;font-weight:800;color:${color};">${value}</div>
        <div style="font-size:11px;font-weight:700;color:${color};letter-spacing:0.5px;
                    text-transform:uppercase;margin-top:2px;">${label}</div>
    </div>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// STATS BANNER
// ─────────────────────────────────────────────────────────────────────────────

function _render_stats_banner(frm) {
    $(".com-stats-banner").remove();
    const doc = frm.doc;
    if (!doc.total_recipients) return;
    const total   = doc.total_recipients || 0;
    const sent    = doc.sent_count       || 0;
    const failed  = doc.failed_count     || 0;
    const pending = doc.pending_count    || 0;
    const pct     = total ? Math.round((sent / total) * 100) : 0;
    const banner  = $(`
        <div class="com-stats-banner" style="
            display:flex;gap:12px;align-items:center;flex-wrap:wrap;
            background:linear-gradient(135deg,#f0f9ff 0%,#e0f2fe 100%);
            border:1.5px solid #bae6fd;border-radius:10px;
            padding:12px 18px;margin-bottom:14px;">
            <div style="display:flex;gap:20px;flex-wrap:wrap;flex:1;">
                ${_inline("📋 Total",   total,   "#2563eb")}
                ${_inline("✅ Sent",    sent,    "#065f46")}
                ${_inline("❌ Failed",  failed,  "#991b1b")}
                ${_inline("⏳ Pending", pending, "#d97706")}
            </div>
            <div style="flex:1;min-width:180px;">
                <div style="font-size:11px;color:#64748b;margin-bottom:4px;
                            font-weight:600;">DELIVERY RATE — ${pct}%</div>
                <div style="background:#e5e7eb;border-radius:999px;
                            height:8px;overflow:hidden;">
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

function _inline(label, value, color) {
    return `<div style="text-align:center;min-width:60px;">
        <div style="font-size:20px;font-weight:800;color:${color};">${value}</div>
        <div style="font-size:10px;color:${color};font-weight:600;">${label}</div>
    </div>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// STYLING HELPERS
// ─────────────────────────────────────────────────────────────────────────────

function _sms_counter(frm) {
    if (!frm.fields_dict.sms_message_body) return;
    const len  = (frm.doc.sms_message_body || "").length;
    const msgs = Math.ceil(len / 160) || 1;
    frm.set_df_property("sms_message_body", "description",
        `Merge tags: {{full_name}}, {{salutation}}. Keep under 160 chars.${
            len > 0
                ? ` — <strong>${len} chars / ${msgs} SMS part${msgs>1?"s":""}</strong>`
                : ""}`);
}

function _apply_styling(frm) {
    setTimeout(() => {
        const status = frm.doc.status || "Draft";
        const cfg    = COM.STATUS[status] || { color:"#6b7280", bg:"#f3f4f6", icon:"📄" };
        $(".com-status-badge").remove();
        $(".page-title").append(`
            <div class="com-status-badge" style="
                display:inline-flex;align-items:center;gap:6px;
                padding:5px 14px;border-radius:20px;font-weight:700;font-size:12px;
                color:${cfg.color};background:${cfg.bg};margin-left:12px;
                box-shadow:0 2px 8px ${cfg.color}30;border:2px solid ${cfg.color}40;">
                <span>${cfg.icon}</span><span>${status.toUpperCase()}</span>
            </div>`);
        $(".page-head").css({
            "border-bottom": `4px solid ${cfg.color}`,
            "box-shadow":    `0 4px 12px ${cfg.color}20`,
            "background":    `linear-gradient(135deg,${cfg.bg} 0%,#ffffff 100%)`
        });
        const SECT = { scheduling:"#7c3aed", audience:"#06b6d4",
                       message:"#8b5cf6",    settings:"#f59e0b", content:"#8b5cf6" };
        Object.keys(frm.fields_dict || {}).forEach(fn => {
            const field = frm.fields_dict[fn];
            if (!field || field.df.fieldtype !== "Section Break"
                       || !field.df.label) return;
            const lbl = field.df.label.toLowerCase();
            let color = "#6b7280";
            for (const [kw, c] of Object.entries(SECT))
                if (lbl.includes(kw)) { color = c; break; }
            $(field.wrapper).find(".form-section-heading,.section-head").css({
                background:       `linear-gradient(135deg,${color}15 0%,${color}08 100%)`,
                "border-left":    `4px solid ${color}`,
                "border-radius":  "8px",
                padding:          "12px 16px",
                "font-weight":    "700",
                "font-size":      "12px",
                color:            color,
                "letter-spacing": "0.5px",
                "text-transform": "uppercase",
                "margin-bottom":  "12px"
            });
        });
    }, 200);
}

function _apply_table_styling(frm) {
    setTimeout(() => {
        const grid = frm.fields_dict.recipients?.grid;
        if (!grid) return;
        grid.wrapper.find(".grid-heading-row").css({
            background:       COM.STYLE.table_header_bg,
            color:            COM.STYLE.table_header_text,
            "font-weight":    "700",
            "text-transform": "uppercase",
            "font-size":      "11px",
            "letter-spacing": "0.8px"
        });
        grid.wrapper.find(".grid-row").each((i, row) => {
            const $row = $(row);
            const ds   = $row
                .find("[data-fieldname='delivery_status'] .static-area")
                .text().trim();
            let bg = i % 2 === 0 ? COM.STYLE.row1 : COM.STYLE.row2;
            if (ds === "Sent")   bg = "#f0fdf4";
            if (ds === "Failed") bg = "#fef2f2";
            $row.css({ "background-color": bg,
                       "border-bottom": `1px solid ${COM.STYLE.table_border}` });
        });
        grid.wrapper.css({
            border:          `1px solid ${COM.STYLE.table_border}`,
            "border-radius": "8px",
            overflow:        "hidden"
        });
    }, 300);
}

console.log("✅ Communique loaded");