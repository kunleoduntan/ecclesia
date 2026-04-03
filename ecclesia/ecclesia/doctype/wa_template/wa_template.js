// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

// ecclesia/doctype/wa_template/wa_template.js

frappe.ui.form.on("WA Template", {

    refresh(frm) {
        _render_preview(frm);

        // Status badge
        const colors = {
            "Approved":         "green",
            "Pending Approval": "orange",
            "Rejected":         "red",
            "Paused":           "orange",
            "Draft":            "grey"
        };
        frm.set_indicator_formatter("status", d => colors[d.status] || "grey");

        if (!frm.is_new()) {
            frm.add_custom_button(__("👁 Preview"), () => _show_preview_dialog(frm), __("Actions"));

            if (frm.doc.status === "Draft") {
                frm.add_custom_button(__("📤 Submit to Meta"), () => _submit_to_meta(frm), __("Actions"));
            }
        }

        // Auto-add params when body changes
        frm.trigger("body_text");
    },

    body_text(frm) {
        _render_preview(frm);
        _sync_params(frm);
    },

    header_text(frm)  { _render_preview(frm); },
    footer_text(frm)  { _render_preview(frm); },
    header_type(frm)  { _render_preview(frm); },
    category(frm)     { _render_preview(frm); }
});


frappe.ui.form.on("WA Template Param", {
    static_value(frm) { _render_preview(frm); },
    custom_expression(frm) { _render_preview(frm); }
});


function _sync_params(frm) {
    const body = frm.doc.body_text || "";
    const matches = [...body.matchAll(/\{\{(\d+)\}\}/g)];
    const indices = [...new Set(matches.map(m => parseInt(m[1])))].sort((a, b) => a - b);

    const existing = (frm.doc.template_params || []).map(p => p.param_index);

    indices.forEach(idx => {
        if (!existing.includes(idx)) {
            frm.add_child("template_params", {
                param_index:  idx,
                param_label:  `Variable ${idx}`,
                source_type:  "Document Field",
                field_name:   ""
            });
        }
    });

    if (indices.length > 0) {
        frm.refresh_field("template_params");
    }
}


function _render_preview(frm) {
    // Build a simulated WhatsApp bubble preview
    let body = frm.doc.body_text || "<em>No body text</em>";

    // Replace {{N}} with placeholder spans
    body = body.replace(/\{\{(\d+)\}\}/g, (_, n) => {
        const param = (frm.doc.template_params || []).find(p => p.param_index == n);
        const val   = param ? (param.static_value || param.field_name || `{${n}}`) : `{${n}}`;
        return `<span style="background:#e8f4fd;color:#2490EF;padding:0 3px;border-radius:3px;font-weight:600;">${val}</span>`;
    });

    const header = frm.doc.header_text
        ? `<div style="font-weight:700;font-size:14px;margin-bottom:6px;">${frm.doc.header_text}</div>` : "";
    const footer = frm.doc.footer_text
        ? `<div style="font-size:11px;color:#999;margin-top:6px;">${frm.doc.footer_text}</div>` : "";

    const html = `
        <div style="background:#DCF8C6;border-radius:12px 12px 0 12px;
            padding:10px 14px;max-width:280px;box-shadow:0 1px 3px rgba(0,0,0,0.12);
            font-family:-apple-system,sans-serif;font-size:13px;line-height:1.5;
            margin:8px auto;">
            ${header}
            <div>${body}</div>
            ${footer}
            <div style="text-align:right;font-size:10px;color:#999;margin-top:4px;">12:00 ✓✓</div>
        </div>`;

    frm.set_df_property("preview_html", "options", html);
    frm.refresh_field("preview_html");
}


function _show_preview_dialog(frm) {
    const d = new frappe.ui.Dialog({
        title: __("Template Preview"),
        size:  "small"
    });

    let body = frm.doc.body_text || "";
    (frm.doc.template_params || []).forEach(p => {
        const val = p.static_value || p.field_name || `[${p.param_label || p.param_index}]`;
        body = body.replace(`{{${p.param_index}}}`, `<b>${val}</b>`);
    });

    d.$body.html(`
        <div style="background:#e5ddd5;padding:20px;border-radius:8px;min-height:120px;display:flex;align-items:flex-end;justify-content:flex-end;">
            <div style="background:#DCF8C6;border-radius:12px 12px 0 12px;padding:12px 16px;
                max-width:260px;font-size:14px;line-height:1.6;
                box-shadow:0 1px 3px rgba(0,0,0,0.12);font-family:sans-serif;">
                ${frm.doc.header_text ? `<b>${frm.doc.header_text}</b><br>` : ""}
                ${body}
                ${frm.doc.footer_text ? `<br><span style="font-size:11px;color:#999;">${frm.doc.footer_text}</span>` : ""}
                <div style="text-align:right;font-size:10px;color:#999;margin-top:6px;">12:00 ✓✓</div>
            </div>
        </div>
        <p style="text-align:center;color:#888;font-size:12px;margin-top:10px;">
            Template: <b>${frm.doc.template_name || frm.doc.name}</b> · Lang: ${frm.doc.language_code || "en_US"}
        </p>`
    );
    d.show();
}


function _submit_to_meta(frm) {
    frappe.confirm(
        __("Submit this template to Meta for approval? This will use your WhatsApp Business API credentials."),
        () => {
            frappe.show_alert({ message: __("Submitting to Meta..."), indicator: "blue" });
            frappe.call({
                method: "ecclesia.api.whatsapp.submit_template_to_meta",
                args:   { template_name: frm.doc.name },
                callback(r) {
                    if (r.message && r.message.success) {
                        frappe.show_alert({ message: __("Submitted! Awaiting Meta approval."), indicator: "green" });
                        frm.set_value("status", "Pending Approval");
                        frm.save();
                    } else {
                        frappe.msgprint({ title: __("Submission Failed"), message: r.message?.error || "Unknown error", indicator: "red" });
                    }
                }
            });
        }
    );
}
