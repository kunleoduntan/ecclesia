// Copyright (c) 2026, Value Impacts Consulting
frappe.ui.form.on("CRM Deal", {
    refresh(frm) {
        frm.trigger("setup_buttons");
        if (!frm.doc.deal_dashboard_html) {
            $(frm.fields_dict["deal_dashboard_html"].wrapper).html(
                '<div style="padding:20px;text-align:center;background:#FFFBEB;border-radius:10px;color:#B45309"><div style="font-size:28px">🔀</div><div style="font-weight:600;margin-top:8px">Save to generate the AI Deal Health Dashboard</div></div>'
            );
        }
    },

    setup_buttons(frm) {
        frm.clear_custom_buttons();
        const health = frm.doc.deal_health_score || 0;
        frm.page.set_indicator(`Health ${health} · ${frm.doc.stage}`,
            health >= 70 ? "green" : health >= 40 ? "yellow" : "red");

        frm.add_custom_button(__("📞 Log Call"),     () => frm.trigger("log_call"),     __("Actions"));
        frm.add_custom_button(__("📋 Log Activity"), () => frm.trigger("log_activity"), __("Actions"));
        frm.add_custom_button(__("🤖 Re-score"),     () => frm.trigger("rescore"),      __("AI"));

        if (frm.doc.lead) frm.add_custom_button(__("🎯 View Lead"), () => frappe.set_route("Form","CRM Lead",frm.doc.lead));

        if (frm.doc.stage === "Closed Won" && !frm.doc.__islocal) {
            frm.add_custom_button(__("📄 Create Invoice"), () => {
                frappe.msgprint("Navigate to ERPNext Sales Invoice and link this deal.");
            }, __("Finance"));
        }
    },

    rescore(frm) {
        frappe.call({
            method: "broker.broker.page.crm_dashboard.crm_dashboard.score_deal_health",
            args: { deal_name: frm.doc.name },
            freeze: true,
            callback(r) {
                if (r.message) {
                    frappe.show_alert({ message: `Health: ${r.message.score} · Grade ${r.message.grade}`, indicator: r.message.grade === "A" ? "green" : "yellow" });
                    frm.reload_doc();
                }
            }
        });
    },

    log_call(frm) {
        const d = new frappe.ui.Dialog({
            title: "📞 Log Call",
            fields: [
                { fieldtype:"Select", fieldname:"direction", label:"Direction", default:"Outbound", options:"\nOutbound\nInbound", reqd:1 },
                { fieldtype:"Select", fieldname:"status",    label:"Outcome",   default:"Answered", options:"\nAnswered\nMissed\nBusy\nDeclined", reqd:1 },
                { fieldtype:"Column Break" },
                { fieldtype:"Int",        fieldname:"duration_seconds", label:"Duration (seconds)" },
                { fieldtype:"Small Text", fieldname:"outcome_notes",    label:"Notes" },
            ],
            primary_action_label: "💾 Save",
            primary_action(vals) {
                frappe.call({
                    method: "frappe.client.insert",
                    args: { doc: { doctype:"Telephone Call Log", caller_name:frm.doc.deal_title, call_type:"External", ...vals } },
                    callback() {
                        d.hide();
                        frappe.db.set_value("CRM Deal", frm.doc.name, "last_activity_date", frappe.datetime.get_today());
                        frappe.show_alert({ message:"Call logged", indicator:"green" });
                    }
                });
            }
        });
        d.show();
    },

    log_activity(frm) {
        const d = new frappe.ui.Dialog({
            title: "📋 Log Activity",
            fields: [
                { fieldtype:"Select", fieldname:"activity_type", label:"Type", default:"Call",
                  options:"\nCall\nEmail\nMeeting\nNote\nFollow-up\nProposal\nTask", reqd:1 },
                { fieldtype:"Data", fieldname:"subject", label:"Subject", reqd:1 },
                { fieldtype:"Column Break" },
                { fieldtype:"Date", fieldname:"due_date", label:"Due Date", default:frappe.datetime.get_today(), reqd:1 },
                { fieldtype:"Small Text", fieldname:"outcome", label:"Outcome" },
            ],
            primary_action_label: "💾 Save",
            primary_action(vals) {
                frappe.call({
                    method: "frappe.client.insert",
                    args: { doc: { doctype:"CRM Activity", deal:frm.doc.name, status:"Open", ...vals } },
                    callback() {
                        d.hide();
                        frappe.db.set_value("CRM Deal", frm.doc.name, "last_activity_date", frappe.datetime.get_today());
                        frappe.show_alert({ message:"Activity logged", indicator:"green" });
                    }
                });
            }
        });
        d.show();
    },

    stage(frm) { frappe.show_alert({ message:"Save to update deal health score", indicator:"blue" }); },
    probability(frm) { frappe.show_alert({ message:"Save to recalculate AI score", indicator:"blue" }); },
    close_date(frm) { frappe.show_alert({ message:"Save to recalculate AI score", indicator:"blue" }); },
});
