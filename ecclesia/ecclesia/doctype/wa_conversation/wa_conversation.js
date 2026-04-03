// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt
// ecclesia/doctype/wa_conversation/wa_conversation.js

frappe.ui.form.on("WA Conversation", {

    refresh(frm) {
        _setup_buttons(frm);
        _render_chat_timeline(frm);
        _bind_realtime(frm);
        _set_status_indicator(frm);
    },

    onload(frm) {
        // Auto-clear unread when opened
        if (!frm.is_new() && frm.doc.unread_count > 0) {
            frappe.call({
                method: "ecclesia.api.conversation.mark_conv_read",
                args:   { conv_name: frm.doc.name }
            });
            frm.set_value("unread_count", 0);
        }
    }
});


function _setup_buttons(frm) {
    if (frm.is_new()) return;

    // ── Quick Reply ─────────────────────────────────────────────────────────
    frm.add_custom_button(__("💬 Send Message"), () => _show_send_dialog(frm), __("Actions"));

    // ── Assign ──────────────────────────────────────────────────────────────
    frm.add_custom_button(__("👤 Assign To"), () => {
        frappe.prompt({
            label: "User",
            fieldname: "user",
            fieldtype: "Link",
            options: "User",
            reqd: 1
        }, values => {
            frappe.call({
                method: "ecclesia.api.conversation.assign_conversation",
                args:   { conv_name: frm.doc.name, user: values.user },
                callback() {
                    frappe.show_alert({ message: __("Assigned!"), indicator: "green" });
                    frm.reload_doc();
                }
            });
        }, __("Assign Conversation"), __("Assign"));
    }, __("Actions"));

    // ── Resolve / Reopen ────────────────────────────────────────────────────
    if (frm.doc.status === "Open") {
        frm.add_custom_button(__("✅ Mark Resolved"), () => {
            frappe.call({
                method: "ecclesia.api.conversation.resolve_conversation",
                args:   { conv_name: frm.doc.name },
                callback() { frm.reload_doc(); }
            });
        }, __("Actions"));
    } else if (frm.doc.status === "Resolved") {
        frm.add_custom_button(__("🔄 Reopen"), () => {
            frappe.call({
                method: "ecclesia.api.conversation.reopen_conversation",
                args:   { conv_name: frm.doc.name },
                callback() { frm.reload_doc(); }
            });
        }, __("Actions"));
    }

    // ── View linked record ──────────────────────────────────────────────────
    if (frm.doc.linked_doctype && frm.doc.linked_docname) {
        frm.add_custom_button(
            __(`Open ${frm.doc.linked_doctype}`),
            () => frappe.set_route("Form", frm.doc.linked_doctype, frm.doc.linked_docname),
            __("Links")
        );
    }
    if (frm.doc.customer) {
        frm.add_custom_button(__("Open Customer"), () => frappe.set_route("Form", "Customer", frm.doc.customer), __("Links"));
    }
    if (frm.doc.contact) {
        frm.add_custom_button(__("Open Contact"), () => frappe.set_route("Form", "Contact", frm.doc.contact), __("Links"));
    }
}


function _set_status_indicator(frm) {
    const map = { "Open": "blue", "Resolved": "green", "Pending": "orange", "Spam": "red" };
    frm.set_intro(
        `Status: <b>${frm.doc.status}</b> · Unread: <b>${frm.doc.unread_count || 0}</b> · Channel: <b>${frm.doc.channel_type || "WhatsApp"}</b>`,
        map[frm.doc.status] || "grey"
    );
}


function _render_chat_timeline(frm) {
    if (frm.is_new()) return;

    frappe.call({
        method: "ecclesia.api.conversation.get_conversation",
        args:   { conv_name: frm.doc.name },
        callback(r) {
            if (!r.message) return;
            const messages = r.message.messages || [];

            const html = `
            <div style="background:#e5ddd5;border-radius:8px;padding:16px;
                max-height:420px;overflow-y:auto;font-family:-apple-system,sans-serif;"
                id="wa-chat-timeline-${frm.doc.name}">
                ${messages.length === 0
                    ? `<p style="text-align:center;color:#888;padding:40px 0;">No messages yet.</p>`
                    : messages.map(m => _render_bubble(m)).join("")
                }
            </div>
            <div style="margin-top:10px;">
                <textarea id="wa-quick-reply-input" rows="2"
                    placeholder="${__('Type a message...')}"
                    style="width:100%;padding:10px;border:1px solid #d1d8dd;border-radius:8px;
                        font-size:13px;resize:none;font-family:-apple-system,sans-serif;"></textarea>
                <div style="margin-top:6px;display:flex;gap:8px;">
                    <button class="btn btn-primary btn-sm" onclick="frappe.wa_send_reply('${frm.doc.name}')">
                        📤 ${__("Send")}
                    </button>
                    <button class="btn btn-default btn-sm" onclick="frappe.wa_send_template_dialog('${frm.doc.name}')">
                        📋 ${__("Use Template")}
                    </button>
                </div>
            </div>`;

            frm.set_df_property("phone_number", "description",
                `<div class="wa-chat-wrap">${html}</div>`);

            // Scroll to bottom
            setTimeout(() => {
                const el = document.getElementById(`wa-chat-timeline-${frm.doc.name}`);
                if (el) el.scrollTop = el.scrollHeight;
            }, 200);
        }
    });

    // ── Global helpers for inline onclick ───────────────────────────────────
    frappe.wa_send_reply = function (conv_name) {
        const txt = document.getElementById("wa-quick-reply-input");
        const body = txt ? txt.value.trim() : "";
        if (!body) return frappe.show_alert({ message: __("Type a message first."), indicator: "orange" });

        frappe.call({
            method: "ecclesia.api.conversation.send_outbound_message",
            args:   { conv_name, message_type: "text", body },
            callback(r) {
                if (r.message) {
                    txt.value = "";
                    frm.reload_doc();
                    frappe.show_alert({ message: __("Message sent!"), indicator: "green" });
                }
            }
        });
    };

    frappe.wa_send_template_dialog = function (conv_name) {
        _show_template_picker(conv_name, frm);
    };
}


function _render_bubble(msg) {
    const isOut    = msg.direction === "Outbound";
    const time     = msg.timestamp ? frappe.datetime.str_to_user(msg.timestamp) : "";
    const icons    = { image: "📷", video: "🎥", audio: "🎵", document: "📎", location: "📍", system: "🔔" };
    const typeIcon = icons[msg.message_type] || "";

    let content = msg.body || `${typeIcon} ${msg.message_type || ""}`;

    if (msg.message_type === "image" && msg.media_url) {
        content = `<img src="${msg.media_url}" style="max-width:180px;border-radius:8px;display:block;margin-bottom:4px;"><span style="font-size:11px;">${msg.caption || ""}</span>`;
    } else if (msg.message_type === "document" && msg.media_url) {
        content = `<a href="${msg.media_url}" target="_blank" style="display:flex;align-items:center;gap:6px;text-decoration:none;color:inherit;">📎 <span style="font-size:12px;font-weight:600;">${msg.media_filename || "Document"}</span></a>`;
    } else if (msg.message_type === "system") {
        return `<div style="text-align:center;font-size:11px;color:#888;margin:6px 0;font-style:italic;">${msg.body}</div>`;
    }

    const align = isOut ? "flex-end" : "flex-start";
    const bg    = isOut ? "#DCF8C6" : "#fff";
    const tick  = isOut ? (msg.delivery_status === "read" ? " <span style='color:#4fc3f7'>✓✓</span>" : " <span style='color:#aaa'>✓</span>") : "";

    return `
    <div style="display:flex;justify-content:${align};margin-bottom:6px;">
        <div style="background:${bg};border-radius:${isOut ? "12px 12px 0 12px" : "12px 12px 12px 0"};
            padding:8px 12px;max-width:72%;box-shadow:0 1px 2px rgba(0,0,0,0.1);
            font-size:13px;line-height:1.5;">
            ${!isOut ? `<div style="font-size:10px;color:#2490EF;font-weight:700;margin-bottom:2px;">
                ${msg.sender_phone || "Customer"}</div>` : ""}
            ${content}
            <div style="text-align:right;font-size:10px;color:#999;margin-top:3px;">
                ${time}${tick}
            </div>
        </div>
    </div>`;
}


function _show_send_dialog(frm) {
    const d = new frappe.ui.Dialog({
        title: __("Send WhatsApp Message"),
        fields: [
            { label: __("Message Type"), fieldname: "message_type", fieldtype: "Select",
              options: "text\ntemplate\nimage\ndocument", default: "text", reqd: 1 },
            { label: __("Message Body"), fieldname: "body", fieldtype: "Small Text",
              depends_on: "eval:doc.message_type=='text'" },
            { label: __("Template"), fieldname: "wa_template", fieldtype: "Link",
              options: "WA Template", depends_on: "eval:doc.message_type=='template'" },
            { label: __("Media URL"), fieldname: "media_url", fieldtype: "Data",
              depends_on: "eval:['image','document'].includes(doc.message_type)" },
            { label: __("Caption / Filename"), fieldname: "caption", fieldtype: "Data",
              depends_on: "eval:['image','document'].includes(doc.message_type)" }
        ],
        primary_action_label: __("Send"),
        primary_action(values) {
            frappe.call({
                method: "ecclesia.api.conversation.send_outbound_message",
                args: {
                    conv_name:     frm.doc.name,
                    message_type:  values.message_type,
                    body:          values.body,
                    template_name: values.wa_template,
                    media_url:     values.media_url,
                    caption:       values.caption
                },
                callback(r) {
                    if (r.message) {
                        frappe.show_alert({ message: __("Sent!"), indicator: "green" });
                        d.hide();
                        frm.reload_doc();
                    }
                }
            });
        }
    });
    d.show();
}


function _show_template_picker(conv_name, frm) {
    const d = new frappe.ui.Dialog({
        title: __("Send Template"),
        fields: [
            { label: __("Template"), fieldname: "template", fieldtype: "Link",
              options: "WA Template", reqd: 1 }
        ],
        primary_action_label: __("Send"),
        primary_action(v) {
            frappe.call({
                method: "ecclesia.api.conversation.send_outbound_message",
                args: { conv_name, message_type: "template", template_name: v.template },
                callback() {
                    frappe.show_alert({ message: __("Template sent!"), indicator: "green" });
                    d.hide();
                    frm.reload_doc();
                }
            });
        }
    });
    d.show();
}


function _bind_realtime(frm) {
    frappe.realtime.on("wa_new_inbound_message", data => {
        if (data.conv_name === frm.doc.name) {
            frm.reload_doc();
        }
    });
    frappe.realtime.on("wa_message_status", data => {
        if (data.conv_name === frm.doc.name) {
            _render_chat_timeline(frm);
        }
    });
}
