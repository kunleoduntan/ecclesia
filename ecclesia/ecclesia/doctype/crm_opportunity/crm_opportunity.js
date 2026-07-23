// Copyright (c) 2026, Value Impacts Consulting
// broker/broker/doctype/crm_opportunity/crm_opportunity.js

frappe.ui.form.on("CRM Opportunity", {

    refresh(frm) {
        frm.trigger("setup_buttons");
        frm.trigger("render_placeholder");
    },

    setup_buttons(frm) {
        frm.clear_custom_buttons();

        // Status indicator
        const score = frm.doc.opportunity_score || 0;
        const prob  = frm.doc.predicted_close_prob || 0;
        const grade = score >= 75 ? "A" : score >= 55 ? "B" : score >= 35 ? "C" : "D";
        frm.page.set_indicator(
            `Score ${score} · Win ${prob}% · Grade ${grade}`,
            prob >= 70 ? "green" : prob >= 40 ? "yellow" : "red"
        );

        // Always available
        frm.add_custom_button(__("📋 Log Activity"), () => frm.trigger("log_activity_dialog"), __("Actions"));
        frm.add_custom_button(__("💬 WA Inbox"), () => {
            if (frm.doc.lead) frappe.set_route("List", "WA Conversation", { lead: frm.doc.lead });
            else frappe.set_route("List", "WA Conversation");
        }, __("Actions"));
        frm.add_custom_button(__("🤖 Re-score"), () => frm.trigger("rescore"), __("AI"));

        // Promote to Deal — only if not already promoted
        if (!["Won","Lost","Closed"].includes(frm.doc.status) && !frm.doc.deal) {
            frm.add_custom_button(__("🔀 Promote to Deal"), () => frm.trigger("promote_dialog"));
        }

        // View linked deal
        if (frm.doc.deal) {
            frm.add_custom_button(__("🔀 View Deal"), () => {
                frappe.set_route("Form", "CRM Deal", frm.doc.deal);
            });
        }

        // View source lead
        if (frm.doc.lead) {
            frm.add_custom_button(__("🎯 View Lead"), () => {
                frappe.set_route("Form", "CRM Lead", frm.doc.lead);
            });
        }
    },

    render_placeholder(frm) {
        if (!frm.fields_dict["opportunity_dashboard_html"]) return;
        if (!frm.doc.opportunity_dashboard_html) {
            $(frm.fields_dict["opportunity_dashboard_html"].wrapper).html(`
                <div style="padding:20px;text-align:center;background:#F5F3FF;border-radius:10px;color:#8B5CF6">
                    <div style="font-size:28px">💼</div>
                    <div style="font-weight:600;margin-top:8px">Save the record to generate the AI Opportunity Intelligence Dashboard</div>
                    <div style="font-size:12px;margin-top:4px">Bayesian win probability · Activity tracking · Forecasting signals</div>
                </div>
            `);
        }
    },

    rescore(frm) {
        frappe.call({
            method: "broker.broker.page.crm_dashboard.crm_dashboard.score_opportunity",
            args:   { opportunity_name: frm.doc.name },
            freeze: true,
            freeze_message: "🤖 Scoring opportunity...",
            callback(r) {
                if (r.message) {
                    frappe.show_alert({
                        message: `Score: ${r.message.score} · Win Prob: ${r.message.predicted_prob}% · Grade ${r.message.grade}`,
                        indicator: r.message.grade === "A" ? "green" : "yellow"
                    });
                    frm.reload_doc();
                }
            }
        });
    },

    promote_dialog(frm) {
        const d = new frappe.ui.Dialog({
            title: "🔀 Promote Opportunity to Deal",
            fields: [
                { fieldtype:"Data",     fieldname:"deal_title", label:"Deal Title", reqd:1,
                  default: frm.doc.opportunity_title },
                { fieldtype:"Currency", fieldname:"deal_value", label:"Deal Value (₦)", reqd:1,
                  default: frm.doc.opportunity_value },
                { fieldtype:"Column Break" },
                { fieldtype:"Select",   fieldname:"stage", label:"Initial Stage", default:"Qualified",
                  options:"Lead In\nQualified\nProposal Sent\nNegotiation" },
                { fieldtype:"Date",     fieldname:"close_date", label:"Close Date", reqd:1,
                  default: frm.doc.expected_close_date || frappe.datetime.add_days(frappe.datetime.get_today(), 30) },
                { fieldtype:"Link",     fieldname:"pipeline", label:"Pipeline", options:"CRM Pipeline" },
            ],
            primary_action_label: "🔀 Create Deal",
            primary_action(vals) {
                frappe.call({
                    method: "broker.broker.page.crm_dashboard.crm_dashboard.promote_opportunity_to_deal",
                    args:   { opportunity_name: frm.doc.name, ...vals },
                    freeze: true,
                    freeze_message: "Creating Deal...",
                    callback(r) {
                        d.hide();
                        if (r.message && r.message.deal) {
                            frappe.show_alert({ message: "Deal created!", indicator: "green" });
                            frappe.set_route("Form", "CRM Deal", r.message.deal);
                        }
                    }
                });
            }
        });
        d.show();
    },

    log_activity_dialog(frm) {
        const d = new frappe.ui.Dialog({
            title: "📋 Log Activity",
            fields: [
                { fieldtype:"Select", fieldname:"activity_type", label:"Type", default:"Call",
                  options:"\nCall\nEmail\nMeeting\nNote\nFollow-up\nTask", reqd:1 },
                { fieldtype:"Data",   fieldname:"subject",     label:"Subject", reqd:1 },
                { fieldtype:"Column Break" },
                { fieldtype:"Date",   fieldname:"due_date",    label:"Due Date",
                  default:frappe.datetime.get_today(), reqd:1 },
                { fieldtype:"Small Text", fieldname:"outcome", label:"Outcome / Notes" },
            ],
            primary_action_label: "💾 Save",
            primary_action(vals) {
                frappe.call({
                    method: "frappe.client.insert",
                    args: { doc: { doctype:"CRM Activity", opportunity:frm.doc.name, lead:frm.doc.lead, status:"Open", ...vals } },
                    callback() {
                        d.hide();
                        frappe.show_alert({ message:"Activity logged", indicator:"green" });
                        // Update last_activity_date
                        frappe.db.set_value("CRM Opportunity", frm.doc.name, "last_activity_date", frappe.datetime.get_today());
                    }
                });
            }
        });
        d.show();
    },

    // Track changes that affect score
    status(frm)               { frm.trigger("_hint"); },
    opportunity_value(frm)    { frm.trigger("_hint"); },
    probability(frm)          { frm.trigger("_hint"); },
    expected_close_date(frm)  { frm.trigger("_hint"); },
    last_activity_date(frm)   { frm.trigger("_hint"); },

    _hint(frm) {
        if (!frm.doc.__islocal) {
            frappe.show_alert({ message: "Save to refresh AI Win Probability", indicator: "blue" });
        }
    },
});
