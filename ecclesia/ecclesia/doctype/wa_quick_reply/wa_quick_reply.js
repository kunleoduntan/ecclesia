// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt
// ecclesia/doctype/wa_quick_reply/wa_quick_reply.js

frappe.ui.form.on("WA Quick Reply", {

    refresh(frm) {
        _render_preview(frm);

        if (!frm.is_new()) {
            frm.add_custom_button(__("📋 Copy Body"), () => {
                frappe.utils.copy_to_clipboard(frm.doc.body || "");
                frappe.show_alert({ message: __("Copied!"), indicator: "green" });
            });
        }
    },

    body(frm)     { _render_preview(frm); },
    shortcut(frm) {
        // Ensure shortcut starts with /
        let val = frm.doc.shortcut || "";
        if (val && !val.startsWith("/")) {
            frm.set_value("shortcut", "/" + val);
        }
    }
});


function _render_preview(frm) {
    const body = frm.doc.body || "";
    const len  = body.replace(/<[^>]+>/g, "").length;

    frm.set_df_property("body", "description",
        `<span style="font-size:11px;color:${len > 1024 ? "red" : "#999"};">
            ${len}/1024 characters
        </span><br>
        <b>Trigger:</b> Type <code>${frm.doc.shortcut || "/shortcut"}</code> in any chat`
    );
}
