// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

// ecclesia/doctype/escalation_rule/escalation_rule.js

frappe.ui.form.on("Escalation Rule", {

    refresh(frm) {
        _render_level_timeline(frm);

        if (!frm.is_new()) {
            frm.add_custom_button(__("🧪 Test on Document"), () => _test_escalation(frm), __("Actions"));
            frm.add_custom_button(__("▶ Run Now"), () => {
                frappe.confirm(__("Run this escalation rule now? This will check all matching documents."), () => {
                    frappe.call({
                        method: "ecclesia.api.escalation._process_escalation_rule",
                        args:   { rule_name: frm.doc.name },
                        callback() {
                            frappe.show_alert({ message: __("Escalation rule executed!"), indicator: "green" });
                        }
                    });
                });
            }, __("Actions"));
        }
    },

    document_type(frm) { _render_level_timeline(frm); }
});


frappe.ui.form.on("Escalation Rule Level", {
    after_hours(frm)  { _render_level_timeline(frm); },
    label(frm)        { _render_level_timeline(frm); },
    channels(frm)     { _render_level_timeline(frm); }
});


function _render_level_timeline(frm) {
    const levels = frm.doc.escalation_levels || [];
    if (!levels.length) return;

    const sorted = [...levels].sort((a, b) => a.after_hours - b.after_hours);

    const channelIcon = { "WhatsApp": "📱", "WhatsApp + Email": "📱📧",
                          "WhatsApp + SMS + Email": "📱💬📧", "Email": "📧", "SMS": "💬" };

    const stepsHtml = sorted.map((l, i) => {
        const notifiee = l.notify_role || l.notify_user || l.notify_field || "?";
        const icon     = channelIcon[l.channels] || "📱";
        const isLast   = i === sorted.length - 1;
        return `
        <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:${isLast ? 0 : 16}px;">
            <div style="display:flex;flex-direction:column;align-items:center;">
                <div style="width:32px;height:32px;border-radius:50%;
                    background:${isLast ? "#dc3545" : "#2490EF"};
                    color:#fff;display:flex;align-items:center;justify-content:center;
                    font-weight:700;font-size:13px;flex-shrink:0;">L${l.level}</div>
                ${!isLast ? '<div style="width:2px;flex:1;background:#e2e6ea;margin:4px auto;min-height:16px;"></div>' : ""}
            </div>
            <div style="padding-top:4px;">
                <div style="font-weight:700;font-size:13px;">${l.label || `Level ${l.level}`}</div>
                <div style="font-size:12px;color:#6c757d;margin-top:2px;">
                    After <b>${l.after_hours}h</b> → Notify <b>${notifiee}</b> via ${icon} ${l.channels || "WhatsApp"}
                </div>
            </div>
        </div>`;
    }).join("");

    const html = `
    <div style="background:#f8f9fa;border-radius:8px;padding:14px 18px;margin-top:6px;
        border:1px solid #e2e6ea;">
        <div style="font-size:11px;font-weight:700;color:#6c757d;letter-spacing:.5px;
            text-transform:uppercase;margin-bottom:12px;">
            📊 Escalation Timeline — ${frm.doc.document_type || "?"}
        </div>
        ${stepsHtml}
        ${frm.doc.auto_action_type ? `
        <div style="margin-top:12px;padding-top:12px;border-top:1px solid #e2e6ea;
            font-size:12px;color:#dc3545;">
            ⚡ Auto-action on final level: <b>${frm.doc.auto_action_type}</b>
        </div>` : ""}
    </div>`;

    frm.set_df_property("filter_condition", "description", html);
    frm.refresh_field("filter_condition");
}


function _test_escalation(frm) {
    frappe.prompt(
        [{ label: __("Document Name"), fieldname: "docname", fieldtype: "Link",
           options: frm.doc.document_type, reqd: 1 }],
        values => {
            frappe.call({
                method: "frappe.client.get",
                args: { doctype: frm.doc.document_type, name: values.docname },
                callback(r) {
                    if (!r.message) return;
                    const triggerVal = r.message[frm.doc.trigger_field];
                    if (!triggerVal) {
                        frappe.msgprint(`Field <b>${frm.doc.trigger_field}</b> is empty on this document.`);
                        return;
                    }

                    const created = new Date(triggerVal);
                    const now     = new Date();
                    const hours   = (now - created) / 3600000;
                    const levels  = [...(frm.doc.escalation_levels || [])]
                        .sort((a, b) => a.after_hours - b.after_hours);

                    let fired = null;
                    for (const l of levels.reverse()) {
                        if (hours >= l.after_hours) { fired = l; break; }
                    }

                    frappe.msgprint({
                        title: __("Escalation Test"),
                        message: `
                            <b>Document:</b> ${values.docname}<br>
                            <b>Trigger field (${frm.doc.trigger_field}):</b> ${triggerVal}<br>
                            <b>Hours elapsed:</b> ${hours.toFixed(1)}h<br>
                            <b>Would fire:</b> ${fired
                                ? `Level ${fired.level} — <b>${fired.label || fired.level}</b>`
                                : `<span style='color:green'>No escalation (not yet past any threshold)</span>`
                            }
                        `
                    });
                }
            });
        },
        __("Test Escalation"), __("Check")
    );
}
