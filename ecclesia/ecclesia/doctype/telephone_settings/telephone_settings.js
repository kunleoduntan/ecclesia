// Copyright (c) 2026, kunle Oduntan and contributors
// For license information, please see license.txt

frappe.ui.form.on("Telephone Settings", {

    // ─── On Form Load ──────────────────────────────────────────────────────
    refresh(frm) {
        frm.trigger("set_active_provider_indicator");
        frm.trigger("add_test_call_button");
        frm.trigger("add_copy_webhook_buttons");
    },

    // ─── Provider Change — Show/Hide Sections via depends_on ──────────────
    active_provider(frm) {
        frm.trigger("set_active_provider_indicator");
    },

    // ─── Status Indicator ──────────────────────────────────────────────────
    set_active_provider_indicator(frm) {
        const provider = frm.doc.active_provider;
        const icons = {
            "Twilio":   "🔴",
            "Vonage":   "🟡",
            "Plivo":    "🟢",
            "Asterisk": "🔵",
        };
        frm.set_intro(
            `${icons[provider] || "⚪"} Active External Provider: <strong>${provider || "None"}</strong>`,
            "blue"
        );
    },

    // ─── Test Call Button ──────────────────────────────────────────────────
    add_test_call_button(frm) {
        frm.add_custom_button(__("Test Provider Connection"), () => {
            frappe.call({
                method: "ecclesia.api.test_provider_connection",
                freeze: true,
                freeze_message: "Testing connection...",
                callback(r) {
                    if (r.message && r.message.success) {
                        frappe.msgprint({
                            title: "Connection OK",
                            message: r.message.detail,
                            indicator: "green",
                        });
                    } else {
                        frappe.msgprint({
                            title: "Connection Failed",
                            message: r.message ? r.message.detail : "Unknown error",
                            indicator: "red",
                        });
                    }
                },
            });
        }, __("Actions"));
    },

    // ─── Copy Webhook URL Buttons ──────────────────────────────────────────
    add_copy_webhook_buttons(frm) {
        const providers = [
            { name: "Twilio",  field: "twilio_webhook_url"  },
            { name: "Vonage",  field: "vonage_webhook_url"  },
            { name: "Plivo",   field: "plivo_webhook_url"   },
        ];

        providers.forEach(({ name, field }) => {
            const url = frm.doc[field];
            if (url) {
                frm.add_custom_button(__(`Copy ${name} Webhook`), () => {
                    frappe.utils.copy_to_clipboard(url);
                    frappe.show_alert({ message: `${name} Webhook URL copied!`, indicator: "green" });
                }, __("Webhooks"));
            }
        });
    },
});
