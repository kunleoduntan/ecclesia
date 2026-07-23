// ecclesia/doctype/resume_screening_result/resume_screening_result.js
frappe.ui.form.on("Resume Screening Result", {

    refresh(frm) {
        frm.trigger("_render_score_bars");
        frm.trigger("_decision_badge");

        if (!frm.is_new() && frappe.user.has_role("HR Manager")) {
            frm.add_custom_button(__("Override to Shortlisted"), () => {
                frm.trigger("_override_decision", "Shortlisted");
            }, __("HR Override"));
            frm.add_custom_button(__("Override to Rejected"), () => {
                frm.trigger("_override_decision", "Rejected");
            }, __("HR Override"));
            frm.add_custom_button(__("Hold for Review"), () => {
                frm.trigger("_override_decision", "Hold");
            }, __("HR Override"));
        }
    },

    _decision_badge(frm) {
        const effective = frm.doc.hr_override || frm.doc.auto_decision;
        const colors = { Shortlisted:"green","Refer to HR":"orange",
                         Rejected:"red", Hold:"yellow" };
        frm.page.set_indicator(effective, colors[effective]||"grey");

        if (frm.doc.knockout_failed) {
            frm.set_intro(
                `⛔ Auto-rejected: ${frm.doc.missing_mandatory_skills || "mandatory skill missing"}`,
                "red"
            );
        } else if (frm.doc.hr_override) {
            frm.set_intro(`HR Override applied: ${frm.doc.hr_override}`, "blue");
        }
    },

    _render_score_bars(frm) {
        // Build a visual score breakdown in the form header area
        const scores = [
            { label: "Education",    value: frm.doc.education_score,    color: "#378ADD" },
            { label: "Experience",   value: frm.doc.experience_score,   color: "#1D9E75" },
            { label: "Skills",       value: frm.doc.skills_score,       color: "#7F77DD" },
            { label: "Certifications",value:frm.doc.certifications_score,color:"#BA7517" },
            { label: "Total",        value: frm.doc.total_score,        color: "#059669" },
        ];
        let html = `<div style="padding:8px 0">`;
        scores.forEach(s => {
            const pct = Math.round(s.value || 0);
            html += `
            <div style="margin-bottom:8px">
              <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:3px">
                <span>${s.label}</span><span><b>${pct}%</b></span>
              </div>
              <div style="height:6px;background:#eee;border-radius:99px;overflow:hidden">
                <div style="width:${pct}%;height:100%;background:${s.color};border-radius:99px"></div>
              </div>
            </div>`;
        });
        html += `</div>`;
        frm.set_df_property("total_score", "description", html);
    },

    _override_decision(frm, decision) {
        frappe.prompt([
            { fieldname:"notes", fieldtype:"Small Text",
              label:"Reason for Override", reqd:1 }
        ], vals => {
            frappe.call({
                method: "ecclesia.api.recruitment_auto_screen.override_decision",
                args: {
                    result_name: frm.doc.name,
                    new_decision: decision,
                    notes: vals.notes
                },
                callback(r) {
                    if (r.message?.success) {
                        frappe.show_alert({ message: __("Decision overridden to {0}", [decision]),
                            indicator: "green" });
                        frm.reload_doc();
                    }
                }
            });
        }, `Override to ${decision}`);
    }
});
