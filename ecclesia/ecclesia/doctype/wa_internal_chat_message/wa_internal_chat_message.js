// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

// ecclesia/doctype/wa_internal_chat_message/wa_internal_chat_message.js

frappe.ui.form.on("WA Internal Chat Message", {

    refresh(frm) {
        _render_bubble(frm);

        // Open parent chat
        if (frm.doc.chat) {
            frm.add_custom_button(__("Open Chat"), () => {
                if (window.ecclesia_internal_chat) {
                    window.ecclesia_internal_chat.open_conv(frm.doc.chat);
                } else {
                    frappe.set_route("Form", "WA Internal Chat", frm.doc.chat);
                }
            });
        }

        // Pin / unpin
        if (!frm.is_new() && frm.doc.sender === frappe.session.user) {
            frm.add_custom_button(frm.doc.is_pinned ? __("📌 Unpin") : __("📌 Pin"), () => {
                frappe.call({
                    method: "ecclesia.api.internal_chat.pin_message",
                    args:   { message_name: frm.doc.name, pinned: !frm.doc.is_pinned },
                    callback() { frm.reload_doc(); }
                });
            }, __("Actions"));
        }

        // Show edit indicator
        if (frm.doc.is_edited) {
            frm.set_df_property("body", "description",
                `<span style="font-size:11px;color:#999;font-style:italic;">
                    ✏️ Edited ${frappe.datetime.str_to_user(frm.doc.edited_at)}
                </span>`
            );
        }

        // Show deletion indicator
        if (frm.doc.is_deleted) {
            frm.set_intro("🗑️ This message has been deleted.", "red");
        }
    }
});


function _render_bubble(frm) {
    const isOwn   = frm.doc.sender === frappe.session.user;
    const type    = frm.doc.message_type;
    const time    = frm.doc.timestamp ? frappe.datetime.str_to_user(frm.doc.timestamp) : "";
    const deleted = frm.doc.is_deleted;

    let content = "";
    if (deleted) {
        content = `<span style="font-style:italic;color:#999;">🗑️ This message was deleted</span>`;
    } else if (type === "text") {
        content = frappe.utils.escape_html(frm.doc.body || "");
    } else if (type === "image") {
        const att = (frm.doc.attachments || [])[0];
        if (att?.file) content = `<img src="${att.file}" style="max-width:220px;border-radius:8px;">`;
    } else if (type === "audio") {
        const att = (frm.doc.attachments || [])[0];
        if (att?.file) content = `<audio controls src="${att.file}" style="max-width:220px;"></audio>`;
    } else if (type === "system") {
        content = `<span style="font-style:italic;color:#888;">🔔 ${frappe.utils.escape_html(frm.doc.body || "")}</span>`;
    }

    // Reactions
    let reactionsHtml = "";
    if (frm.doc.reactions) {
        try {
            const reactions = JSON.parse(frm.doc.reactions);
            reactionsHtml = Object.keys(reactions).map(emoji => {
                const count = reactions[emoji].length;
                return `<span style="background:#f0f2f5;border:1px solid #e0e0e0;
                    border-radius:20px;padding:2px 8px;font-size:13px;margin:2px;">
                    ${emoji} ${count}
                </span>`;
            }).join("");
        } catch(e) {}
    }

    const bg   = isOwn ? "#DCF8C6" : "#fff";
    const align= isOwn ? "flex-end" : "flex-start";
    const br   = isOwn ? "12px 12px 0 12px" : "12px 12px 12px 0";

    const html = `
    <div style="display:flex;justify-content:${align};padding:8px 0;
        font-family:-apple-system,BlinkMacSystemFont,sans-serif;">
        <div style="background:${bg};border-radius:${br};
            padding:10px 14px;max-width:320px;
            box-shadow:0 1px 3px rgba(0,0,0,0.1);
            font-size:13px;line-height:1.5;">
            ${!isOwn ? `<div style="font-size:11px;color:#2490EF;font-weight:700;margin-bottom:4px;">
                ${frappe.utils.escape_html(frm.doc.sender_name || frm.doc.sender)}</div>` : ""}
            ${content}
            <div style="text-align:right;font-size:10px;color:#999;margin-top:4px;">
                ${time}${frm.doc.is_edited ? " ✏️" : ""}${frm.doc.is_pinned ? " 📌" : ""}
            </div>
        </div>
    </div>
    ${reactionsHtml ? `<div style="display:flex;justify-content:${align};gap:4px;padding:0 8px;">${reactionsHtml}</div>` : ""}`;

    frm.set_df_property("body", "description", html);
    frm.refresh_field("body");
}
