// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

// ecclesia/doctype/wa_notification_rule/wa_notification_rule.js

frappe.ui.form.on("WA Notification Rule", {

    refresh(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__("🧪 Test Rule"), () => _test_rule(frm), __("Actions"));

            frm.add_custom_button(__("📋 View Sent Messages"), () => {
                frappe.set_route("List", "WA Message", {
                    delivery_status: ["in", ["sent", "delivered", "read"]]
                });
            }, __("Actions"));
        }

        _toggle_channel_fields(frm);
    },

    send_whatsapp(frm) { _toggle_channel_fields(frm); },
    send_sms(frm)      { _toggle_channel_fields(frm); },
    send_email(frm)    { _toggle_channel_fields(frm); },

    document_type(frm) {
        // Clear trigger field when doctype changes
        frm.set_value("trigger_field", "");
        if (frm.doc.document_type) {
            _load_doctype_fields(frm);
        }
    },

    trigger_event(frm) {
        const isScheduled = frm.doc.trigger_event === "Scheduled";
        frm.set_df_property("condition", "description",
            isScheduled
                ? "Evaluated on schedule. Use <code>doc</code> for each matching document."
                : `Evaluated on <b>${frm.doc.trigger_event}</b>. Example: <code>doc.grand_total &gt; 100000</code>`
        );
    }
});


frappe.ui.form.on("WA Notification Rule Recipient", {
    recipient_type(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        // Clear irrelevant fields
        frappe.model.set_value(cdt, cdn, "field_name",     "");
        frappe.model.set_value(cdt, cdn, "static_number",  "");
        frappe.model.set_value(cdt, cdn, "role",           "");
        frappe.model.set_value(cdt, cdn, "user",           "");
    }
});


function _toggle_channel_fields(frm) {
    const channels = ["whatsapp", "sms", "email"];
    channels.forEach(ch => {
        const enabled = frm.doc[`send_${ch}`];
        // Show relevant fields
        if (ch === "whatsapp") {
            frm.set_df_property("wa_template", "hidden", !enabled);
        } else if (ch === "sms") {
            frm.set_df_property("sms_body", "hidden", !enabled);
        } else if (ch === "email") {
            frm.set_df_property("email_subject", "hidden", !enabled);
            frm.set_df_property("email_body",    "hidden", !enabled);
        }
    });
}


function _load_doctype_fields(frm) {
    frappe.model.with_doctype(frm.doc.document_type, () => {
        const meta   = frappe.get_meta(frm.doc.document_type);
        const fields = meta.fields
            .filter(f => !["Section Break","Column Break","Tab Break","HTML"].includes(f.fieldtype))
            .map(f => ({ label: `${f.label} (${f.fieldname})`, value: f.fieldname }));

        // Populate field name suggestions in recipient rows
        frm.set_df_property("condition", "description",
            `Fields available: ${meta.fields.slice(0, 5).map(f => `<code>${f.fieldname}</code>`).join(", ")}...`
        );
    });
}


function _test_rule(frm) {
    if (!frm.doc.document_type) {
        frappe.show_alert({ message: __("Set a Document Type first."), indicator: "orange" });
        return;
    }
    frappe.prompt(
        [{ label: __("Document Name"), fieldname: "docname", fieldtype: "Link",
           options: frm.doc.document_type, reqd: 1 }],
        values => {
            frappe.show_alert({ message: __("Testing rule..."), indicator: "blue" });
            frappe.call({
                method: "frappe.client.get",
                args: { doctype: frm.doc.document_type, name: values.docname },
                callback(r) {
                    if (!r.message) return;
                    // Evaluate condition locally for preview
                    let conditionResult = true;
                    if (frm.doc.condition) {
                        try {
                            const doc = r.message;
                            conditionResult = eval(frm.doc.condition.replace(/doc\./g, "doc."));
                        } catch(e) {
                            conditionResult = `Error: ${e.message}`;
                        }
                    }

                    const recipients = frm.doc.recipients || [];
                    frappe.msgprint({
                        title: __("Test Result"),
                        message: `
                            <b>Document:</b> ${values.docname}<br>
                            <b>Condition:</b> ${frm.doc.condition || "(none)"}<br>
                            <b>Would Fire:</b> <span style="color:${conditionResult === true ? "green" : "red"}">
                                ${conditionResult === true ? "✅ Yes" : `❌ No (${conditionResult})`}
                            </span><br>
                            <b>Recipients:</b> ${recipients.length} configured<br>
                            <b>Channels:</b> 
                            ${frm.doc.send_whatsapp ? "WhatsApp " : ""}
                            ${frm.doc.send_sms ? "SMS " : ""}
                            ${frm.doc.send_email ? "Email" : ""}
                        `
                    });
                }
            });
        },
        __("Test on Document"), __("Test")
    );
}
