// Copyright (c) 2026, Value Impacts Consulting
// broker/broker/doctype/crm_lead/crm_lead.js

// =============================================================================
// HELPER FUNCTIONS — standalone to avoid `this` context issues
// =============================================================================

function cl_grade_color(score) {
    if (score >= 80) return "#10B981";
    if (score >= 60) return "#F59E0B";
    if (score >= 40) return "#06B6D4";
    return "#94A3B8";
}

function cl_status_color(status) {
    return {
        "New": "#2563EB", "Open": "#06B6D4", "Replied": "#8B5CF6",
        "Opportunity": "#F59E0B", "Qualified": "#10B981",
        "Unqualified": "#94A3B8", "Junk": "#EF4444",
        "Do Not Contact": "#EF4444", "Converted": "#10B981",
    }[status] || "#6B7280";
}

function cl_render_score_ring(score, size) {
    size = size || 56;
    const r   = size * 0.4;
    const c   = 2 * Math.PI * r;
    const off = c * (1 - score / 100);
    const col = cl_grade_color(score);
    const cx  = size / 2;
    return `
    <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
        <circle cx="${cx}" cy="${cx}" r="${r}" fill="none" stroke="#E2E8F0" stroke-width="${size*0.13}"/>
        <circle cx="${cx}" cy="${cx}" r="${r}" fill="none" stroke="${col}" stroke-width="${size*0.13}"
            stroke-dasharray="${c.toFixed(1)}" stroke-dashoffset="${off.toFixed(1)}"
            stroke-linecap="round" transform="rotate(-90 ${cx} ${cx})"/>
        <text x="${cx}" y="${cx + size*0.08}" text-anchor="middle"
              font-size="${size*0.28}" font-weight="800" fill="#0F172A">${score}</text>
    </svg>`;
}

// =============================================================================
// FORM CONTROLLER
// =============================================================================

frappe.ui.form.on("CRM Lead", {

    refresh(frm) {
        frm.trigger("setup_buttons");
        frm.trigger("render_score_indicator");
        frm.trigger("setup_realtime");
    },

    setup_buttons(frm) {
        frm.clear_custom_buttons();

        // Always available
        frm.add_custom_button(__("📞 Log Call"), () => frm.trigger("log_call_dialog"), __("Actions"));
        frm.add_custom_button(__("📋 Log Activity"), () => frm.trigger("log_activity_dialog"), __("Actions"));
        frm.add_custom_button(__("💬 WA Conversations"),
            () => frappe.set_route("List", "WA Conversation", { lead: frm.doc.name }), __("Actions"));
        frm.add_custom_button(__("🤖 Re-score Lead"), () => frm.trigger("rescore_lead"), __("AI"));

        // Convert to Opportunity — only if not already converted
        if (!["Converted", "Junk", "Do Not Contact"].includes(frm.doc.status)) {
            frm.add_custom_button(__("💼 Convert to Opportunity"), () => {
                frm.trigger("convert_to_opportunity");
            });
        }

        // View linked opportunity/deal
        if (frm.doc.status === "Converted" && frm.doc.converted_deal) {
            frm.add_custom_button(__("🔀 View Deal"), () => {
                frappe.set_route("Form", "CRM Deal", frm.doc.converted_deal);
            });
        }

        // Dashboard banner on indicator
        const score = frm.doc.lead_score || 0;
        const grade = score >= 80 ? "A" : score >= 60 ? "B" : score >= 40 ? "C" : "D";
        frm.page.set_indicator(`ICP Grade ${grade} · Score ${score}`,
            score >= 80 ? "green" : score >= 60 ? "yellow" : score >= 40 ? "blue" : "gray");
    },

    render_score_indicator(frm) {
        if (!frm.fields_dict["lead_dashboard_html"]) return;
        // The dashboard HTML is rendered server-side on validate; just ensure it's visible
        // If blank (new unsaved doc), show a placeholder
        if (!frm.doc.lead_dashboard_html) {
            $(frm.fields_dict["lead_dashboard_html"].wrapper).html(`
                <div style="padding:20px;text-align:center;background:#F8FAFC;border-radius:10px;color:#94A3B8">
                    <div style="font-size:28px">🎯</div>
                    <div style="font-weight:600;margin-top:8px">Save the record to generate the AI Lead Intelligence Dashboard</div>
                    <div style="font-size:12px;margin-top:4px">Scores update on every save · Factors: revenue, industry, seniority, engagement</div>
                </div>
            `);
        }
    },

    setup_realtime(frm) {
        // Refresh form if a WA message or call links to this lead
        frappe.realtime.on("lead_activity_update", (data) => {
            if (data.lead === frm.doc.name) {
                frm.reload_doc();
            }
        });
    },

    rescore_lead(frm) {
        frappe.call({
            method: "broker.broker.page.crm_dashboard.crm_dashboard.score_lead",
            args:   { lead_name: frm.doc.name },
            freeze: true,
            freeze_message: "🤖 Scoring lead...",
            callback(r) {
                if (r.message) {
                    frappe.show_alert({
                        message: `Score: ${r.message.score}/100 · Grade ${r.message.grade}`,
                        indicator: r.message.grade === "A" ? "green" : r.message.grade === "B" ? "yellow" : "blue"
                    });
                    frm.reload_doc();
                }
            }
        });
    },

    convert_to_opportunity(frm) {
        const d = new frappe.ui.Dialog({
            title: "💼 Convert Lead to Opportunity",
            size: "large",
            fields: [
                { fieldtype:"Data",     fieldname:"opportunity_title",  label:"Opportunity Title", reqd:1,
                  default: `${frm.doc.company_name || frm.doc.lead_name} — Opportunity` },
                { fieldtype:"Currency", fieldname:"opportunity_value",  label:"Estimated Value (₦)", reqd:1 },
                { fieldtype:"Column Break" },
                { fieldtype:"Select",   fieldname:"status", label:"Initial Status", default:"Needs Analysis",
                  options:"Prospecting\nNeeds Analysis\nValue Proposition\nIdentified Decision Makers\nProposal/Price Quote\nNegotiation/Review" },
                { fieldtype:"Percent",  fieldname:"probability", label:"Win Probability %", default:30 },
                { fieldtype:"Date",     fieldname:"expected_close_date", label:"Expected Close Date", reqd:1,
                  default: frappe.datetime.add_days(frappe.datetime.get_today(), 30) },
                { fieldtype:"Section Break", label:"Assignment" },
                { fieldtype:"Link",     fieldname:"assigned_to", label:"Assign To", options:"User",
                  default: frm.doc.assigned_to },
                { fieldtype:"Link",     fieldname:"territory", label:"Territory", options:"CRM Territory",
                  default: frm.doc.territory },
                { fieldtype:"Section Break", label:"Next Step" },
                { fieldtype:"Small Text", fieldname:"next_step", label:"Agreed Next Step" },
            ],
            primary_action_label: "✅ Create Opportunity",
            primary_action(vals) {
                frappe.call({
                    method: "broker.broker.page.crm_dashboard.crm_dashboard.convert_lead_to_opportunity",
                    args:   { lead_name: frm.doc.name, ...vals },
                    freeze: true,
                    freeze_message: "Creating Opportunity...",
                    callback(r) {
                        d.hide();
                        if (r.message && r.message.opportunity) {
                            frappe.show_alert({ message: "Opportunity created!", indicator: "green" });
                            frappe.set_route("Form", "CRM Opportunity", r.message.opportunity);
                        }
                    }
                });
            }
        });
        d.show();
    },

    log_call_dialog(frm) {
        const d = new frappe.ui.Dialog({
            title: "📞 Log Call",
            fields: [
                { fieldtype:"Select",  fieldname:"direction", label:"Direction", default:"Outbound", options:"\nOutbound\nInbound", reqd:1 },
                { fieldtype:"Select",  fieldname:"status",    label:"Outcome",   default:"Answered", options:"\nAnswered\nMissed\nBusy\nDeclined", reqd:1 },
                { fieldtype:"Column Break" },
                { fieldtype:"Int",     fieldname:"duration_seconds", label:"Duration (seconds)" },
                { fieldtype:"Small Text", fieldname:"outcome_notes", label:"Notes" },
            ],
            primary_action_label: "💾 Save Call",
            primary_action(vals) {
                frappe.call({
                    method: "frappe.client.insert",
                    args: { doc: { doctype:"Telephone Call Log", caller_name:frm.doc.lead_name, call_type:"External", ...vals } },
                    callback() { d.hide(); frappe.show_alert({ message:"Call logged", indicator:"green" }); }
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
                { fieldtype:"Date",   fieldname:"due_date",    label:"Due Date", default:frappe.datetime.get_today(), reqd:1 },
                { fieldtype:"Small Text", fieldname:"outcome", label:"Notes / Outcome" },
            ],
            primary_action_label: "💾 Save",
            primary_action(vals) {
                frappe.call({
                    method: "frappe.client.insert",
                    args: { doc: { doctype:"CRM Activity", lead:frm.doc.name, status:"Open", ...vals } },
                    callback() { d.hide(); frappe.show_alert({ message:"Activity logged", indicator:"green" }); }
                });
            }
        });
        d.show();
    },

    // Trigger re-score hint when key fields change
    industry(frm)        { frm.trigger("_score_hint"); },
    annual_revenue(frm)  { frm.trigger("_score_hint"); },
    job_title(frm)       { frm.trigger("_score_hint"); },
    lead_source(frm)     { frm.trigger("_score_hint"); },
    email(frm)           { frm.trigger("_score_hint"); },

    _score_hint(frm) {
        if (frm.doc.__islocal) return;
        frappe.show_alert({ message: "Save to refresh AI score", indicator: "blue" });
    },
});
