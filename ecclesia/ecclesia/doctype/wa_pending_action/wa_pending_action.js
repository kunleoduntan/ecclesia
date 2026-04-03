// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

// ecclesia/doctype/wa_pending_action/wa_pending_action.js

frappe.ui.form.on("WA Pending Action", {

    refresh(frm) {
        _set_status_display(frm);

        if (!frm.is_new() && frm.doc.status === "Pending") {
            frm.add_custom_button(__("✅ Manually Approve"), () => {
                frappe.call({
                    method: "ecclesia.api.approval.process_approval_reply",
                    args: {
                        pending_name: frm.doc.name,
                        action:       frm.doc.option_1_action || "Approve",
                        phone:        frm.doc.phone_number
                    },
                    callback() {
                        frappe.show_alert({ message: __("Approved!"), indicator: "green" });
                        frm.reload_doc();
                    }
                });
            }, __("Actions"));

            frm.add_custom_button(__("❌ Manually Reject"), () => {
                frappe.call({
                    method: "ecclesia.api.approval.process_approval_reply",
                    args: {
                        pending_name: frm.doc.name,
                        action:       frm.doc.option_2_action || "Reject",
                        phone:        frm.doc.phone_number
                    },
                    callback() {
                        frappe.show_alert({ message: __("Rejected."), indicator: "red" });
                        frm.reload_doc();
                    }
                });
            }, __("Actions"));

            frm.add_custom_button(__("🔗 Open Linked Doc"), () => {
                frappe.set_route("Form", frm.doc.linked_doctype, frm.doc.linked_docname);
            });
        }
    }
});


function _set_status_display(frm) {
    const map = {
        Pending:  { color: "orange", icon: "⏳" },
        Approved: { color: "green",  icon: "✅" },
        Rejected: { color: "red",    icon: "❌" },
        Expired:  { color: "grey",   icon: "⌛" },
        Error:    { color: "red",    icon: "⚠️" }
    };
    const s = map[frm.doc.status] || { color: "grey", icon: "" };

    let msg = `${s.icon} <b>${frm.doc.status}</b> · ${frm.doc.action_type}`;
    if (frm.doc.linked_docname) {
        msg += ` · ${frm.doc.linked_doctype}: <b>${frm.doc.linked_docname}</b>`;
    }
    if (frm.doc.expires_at && frm.doc.status === "Pending") {
        const exp = frappe.datetime.str_to_user(frm.doc.expires_at);
        msg += ` · Expires: ${exp}`;
    }
    frm.set_intro(msg, s.color);
}
