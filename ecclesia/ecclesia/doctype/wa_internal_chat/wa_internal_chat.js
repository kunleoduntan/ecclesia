// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

// ecclesia/doctype/wa_internal_chat/wa_internal_chat.js

frappe.ui.form.on("WA Internal Chat", {

    refresh(frm) {
        _set_intro(frm);
        _setup_buttons(frm);
    },

    chat_type(frm) {
        // DM: hide group name input
        frm.set_df_property("chat_name",           "hidden", frm.doc.chat_type === "Direct Message");
        frm.set_df_property("only_admins_can_post","hidden",
            !["Announcement", "Department"].includes(frm.doc.chat_type));
    }
});


frappe.ui.form.on("WA Internal Chat Member", {
    user(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.user) {
            frappe.db.get_value("User", row.user, "full_name", r => {
                frappe.model.set_value(cdt, cdn, "full_name", r.full_name);
            });
        }
    }
});


function _setup_buttons(frm) {
    if (frm.is_new()) return;

    // Open in chat widget
    frm.add_custom_button(__("💬 Open Chat"), () => {
        if (window.ecclesia_internal_chat) {
            window.ecclesia_internal_chat.open_conv(frm.doc.name);
        } else {
            frappe.show_alert({ message: __("Chat widget not loaded. Refresh the page."), indicator: "orange" });
        }
    }, __("Actions"));

    // Add member
    frm.add_custom_button(__("➕ Add Member"), () => {
        frappe.prompt(
            [{ label: __("User"), fieldname: "user", fieldtype: "Link", options: "User", reqd: 1 }],
            values => {
                frappe.call({
                    method: "ecclesia.api.internal_chat.add_member",
                    args:   { chat_name: frm.doc.name, user: values.user },
                    callback() {
                        frappe.show_alert({ message: __("Member added!"), indicator: "green" });
                        frm.reload_doc();
                    }
                });
            }, __("Add Member"), __("Add")
        );
    }, __("Actions"));

    // Archive
    if (!frm.doc.is_archived) {
        frm.add_custom_button(__("📦 Archive"), () => {
            frappe.db.set_value("WA Internal Chat", frm.doc.name, "is_archived", 1)
                .then(() => frm.reload_doc());
        }, __("Actions"));
    }
}


function _set_intro(frm) {
    const typeIcons = {
        "Direct Message":   "👤",
        "Group":            "👥",
        "Department":       "🏢",
        "Document Channel": "📄",
        "Announcement":     "📢"
    };
    const icon    = typeIcons[frm.doc.chat_type] || "💬";
    const members = frm.doc.member_count || (frm.doc.members || []).length;
    const msgs    = frm.doc.total_messages || 0;

    frm.set_intro(
        `${icon} ${frm.doc.chat_type} · ${members} members · ${msgs} messages`
        + (frm.doc.is_archived ? " · <b style='color:orange'>ARCHIVED</b>" : ""),
        frm.doc.is_archived ? "orange" : "blue"
    );
}
