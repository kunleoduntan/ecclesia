// ecclesia/doctype/resume/resume.js
frappe.ui.form.on("Resume", {

    refresh(frm) {
        frm.trigger("_status_badge");
        frm.trigger("_show_ai_results");

        if (!frm.is_new()) {
            frm.add_custom_button(__("Run AI Screen Now"), () => {
                frm.trigger("_run_screening");
            }, __("Tools"));

            frm.add_custom_button(__("View Applicant"), () => {
                frappe.set_route("Form", "Job Applicant", frm.doc.job_applicant);
            });
        }
    },

    _status_badge(frm) {
        const colors = {
            Uploaded:"grey", Parsing:"orange", Parsed:"blue",
            Scoring:"orange", Scored:"blue",
            Shortlisted:"green", Rejected:"red"
        };
        frm.page.set_indicator(frm.doc.status, colors[frm.doc.status]||"grey");
    },

    _show_ai_results(frm) {
        if (!frm.doc.ai_recommendation) return;
        const colors = {
            "Strong Hire":"green","Hire":"blue","Maybe":"orange","No Hire":"red"
        };
        frm.set_intro(
            `AI Recommendation: <b>${frm.doc.ai_recommendation}</b>`,
            colors[frm.doc.ai_recommendation]||"grey"
        );
    },

    _run_screening(frm) {
        frappe.confirm(__("Run AI screening for this resume now?"), () => {
            frappe.show_progress("Screening", 30, 100, __("AI is reviewing the resume..."));
            frappe.call({
                method: "ecclesia.api.recruitment_auto_screen.screen_resume",
                args: { resume_name: frm.doc.name },
                callback(r) {
                    frappe.hide_progress();
                    if (r.message) {
                        frappe.show_alert({
                            message: __("Score: {0}% — Decision: {1}",
                                [r.message.total_score, r.message.auto_decision]),
                            indicator: r.message.auto_decision === "Shortlisted"
                                ? "green" : "red"
                        });
                        frm.reload_doc();
                    }
                }
            });
        });
    }
});
