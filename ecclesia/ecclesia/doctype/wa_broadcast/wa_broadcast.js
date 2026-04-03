// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

// ecclesia/doctype/wa_broadcast/wa_broadcast.js

frappe.ui.form.on("WA Broadcast", {

    refresh(frm) {
        _render_stats_bar(frm);
        _setup_buttons(frm);
    },

    recipient_source(frm) {
        _toggle_source_fields(frm);
    },

    onload(frm) {
        _toggle_source_fields(frm);
    }
});


frappe.ui.form.on("WA Broadcast Recipient", {
    recipients_add(frm) { _update_count(frm); },
    recipients_remove(frm) { _update_count(frm); }
});


function _setup_buttons(frm) {
    if (frm.is_new() || frm.doc.docstatus !== 1) return;

    if (frm.doc.status === "Draft" || frm.doc.status === "Scheduled") {
        frm.add_custom_button(__("▶ Send Now"), () => {
            frappe.confirm(
                __(`Send to ${frm.doc.total_recipients || "all"} recipients now?`),
                () => {
                    frappe.call({
                        method: "ecclesia.api.broadcast.run_broadcast",
                        args:   { broadcast_name: frm.doc.name },
                        callback() {
                            frappe.show_alert({ message: __("Broadcast started!"), indicator: "green" });
                            frm.reload_doc();
                        }
                    });
                }
            );
        }, __("Actions"));
    }

    if (frm.doc.status === "Completed") {
        frm.add_custom_button(__("📊 Delivery Report"), () => {
            frappe.set_route("List", "WA Broadcast Recipient", { parent: frm.doc.name });
        }, __("Actions"));
    }
}


function _render_stats_bar(frm) {
    if (!frm.doc.total_recipients) return;

    const total     = frm.doc.total_recipients || 0;
    const sent      = frm.doc.sent_count      || 0;
    const delivered = frm.doc.delivered_count || 0;
    const read      = frm.doc.read_count      || 0;
    const failed    = frm.doc.failed_count    || 0;

    const pct = v => total ? Math.round((v / total) * 100) : 0;
    const statusColors = {
        "Running":   "blue",
        "Completed": "green",
        "Failed":    "red",
        "Scheduled": "orange",
        "Draft":     "grey"
    };

    frm.set_intro(`
        <div style="font-size:12px;line-height:2;">
            <b>Status:</b> <span style="color:${statusColors[frm.doc.status] || '#666'}">${frm.doc.status}</span> &nbsp;|&nbsp;
            <b>Total:</b> ${total} &nbsp;|&nbsp;
            <b>Sent:</b> ${sent} (${pct(sent)}%) &nbsp;|&nbsp;
            <b>Delivered:</b> ${delivered} (${pct(delivered)}%) &nbsp;|&nbsp;
            <b>Read:</b> ${read} (${pct(read)}%) &nbsp;|&nbsp;
            <b>Failed:</b> <span style="color:${failed ? 'red' : 'inherit'}">${failed}</span>
        </div>
        <div style="height:6px;background:#e2e6ea;border-radius:3px;margin-top:4px;overflow:hidden;">
            <div style="height:100%;width:${pct(sent)}%;background:linear-gradient(90deg,#2490EF,#28a745);
                border-radius:3px;transition:width .5s;"></div>
        </div>
    `, statusColors[frm.doc.status] || "grey");
}


function _toggle_source_fields(frm) {
    const source = frm.doc.recipient_source;
    frm.set_df_property("customer_group",  "hidden", source !== "Customer Group");
    frm.set_df_property("supplier_group",  "hidden", source !== "Supplier Group");
    frm.set_df_property("report_name",     "hidden", source !== "Report");
    frm.set_df_property("phone_column",    "hidden", source !== "Report");
    frm.set_df_property("recipients",      "hidden", source !== "Manual List");
}


function _update_count(frm) {
    const count = (frm.doc.recipients || []).length;
    frm.set_df_property("recipients", "label",
        `Recipients (${count} added)`
    );
}
