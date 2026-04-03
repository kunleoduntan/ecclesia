// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

// ecclesia/doctype/wa_settings/wa_settings.js

frappe.ui.form.on("WA Settings", {

    refresh(frm) {
        // ── Test Connection Button ──────────────────────────────────────────
        frm.add_custom_button(__("📱 Test WhatsApp"), function () {
            if (!frm.doc.wa_test_number) {
                frappe.msgprint(__("Enter a test phone number first."));
                return;
            }
            frappe.show_alert({ message: __("Sending test message..."), indicator: "blue" });
            frappe.call({
                method: "ecclesia.doctype.wa_settings.wa_settings.test_connection",
                args: {
                    test_number:  frm.doc.wa_test_number,
                    test_message: frm.doc.wa_test_message || "Hello from ERPNext WhatsApp Engine!"
                },
                callback(r) {
                    if (r.message && r.message.success) {
                        frappe.show_alert({ message: r.message.message, indicator: "green" });
                    } else {
                        frappe.msgprint({
                            title: __("Test Failed"),
                            message: r.message ? r.message.message : __("Unknown error"),
                            indicator: "red"
                        });
                    }
                }
            });
        }, __("Actions"));

        // ── Copy Webhook URL ────────────────────────────────────────────────
        frm.add_custom_button(__("📋 Copy Webhook URL"), function () {
            const url = `${window.location.origin}/api/whatsapp/webhook`;
            frappe.utils.copy_to_clipboard(url);
            frappe.show_alert({ message: __("Webhook URL copied!"), indicator: "green" });
        }, __("Actions"));

        // ── Provider-specific help text ─────────────────────────────────────
        frm.trigger("wa_provider");
        frm.trigger("sms_provider");

        // Status indicators
        _render_status_indicators(frm);
    },

    wa_enabled(frm) {
        frm.trigger("wa_provider");
    },

    wa_provider(frm) {
        const hints = {
            "Meta Cloud API": "Get Phone Number ID and Access Token from <b>Meta for Developers → WhatsApp → API Setup</b>",
            "360dialog":      "Get API key from <b>360dialog Hub → Developer → API Keys</b>",
            "Twilio":         "Use Account SID as API Key and Auth Token as Secret",
            "Termii":         "Get API Key from <b>Termii Dashboard → Settings → API</b>"
        };
        const hint = hints[frm.doc.wa_provider];
        if (hint && frm.doc.wa_enabled) {
            frm.set_df_property("wa_phone_number_id", "description", hint);
        }
    },

    sms_provider(frm) {
        const hints = {
            "Twilio":          "Account SID → API Key, Auth Token → API Secret",
            "Termii":          "API Key only, no secret needed",
            "Africa's Talking": "Username → Sender ID, API Key only",
            "Nexmo (Vonage)":  "API Key and API Secret from Vonage dashboard"
        };
        const hint = hints[frm.doc.sms_provider];
        if (hint && frm.doc.sms_enabled) {
            frm.set_df_property("sms_api_key", "description", hint);
        }
    }
});

function _render_status_indicators(frm) {
    // Visual pill indicators for enabled channels
    const channels = [
        { label: "WhatsApp", enabled: frm.doc.wa_enabled,            color: "#25D366" },
        { label: "SMS",      enabled: frm.doc.sms_enabled,           color: "#FF6B35" },
        { label: "Email",    enabled: frm.doc.email_enabled,         color: "#2490EF" },
        { label: "Chat",     enabled: frm.doc.internal_chat_enabled, color: "#7C5CFC" }
    ];
    const pills = channels.map(c =>
        `<span style="display:inline-flex;align-items:center;gap:5px;
            background:${c.enabled ? c.color + "22" : "#f0f0f0"};
            color:${c.enabled ? c.color : "#999"};
            border:1px solid ${c.enabled ? c.color + "55" : "#ddd"};
            border-radius:20px;padding:3px 12px;font-size:12px;font-weight:600;margin-right:6px;">
            ${c.enabled ? "●" : "○"} ${c.label}
        </span>`
    ).join("");

    frm.set_intro(
        `<div style="padding:4px 0;">${pills}</div>`,
        frm.doc.wa_enabled || frm.doc.sms_enabled ? "blue" : "grey"
    );
}
