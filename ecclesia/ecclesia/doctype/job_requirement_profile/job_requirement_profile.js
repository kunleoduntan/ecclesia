// ecclesia/doctype/job_requirement_profile/job_requirement_profile.js
frappe.ui.form.on("Job Requirement Profile", {

    refresh(frm) {
        frm.trigger("_update_weight_total");
        frm.trigger("_toggle_diversity_fields");
        frm.trigger("_toggle_salary_fields");

        if (!frm.is_new()) {
            frm.add_custom_button(__("Re-Screen All Applicants"), () => {
                frappe.confirm(
                    __("Re-run AI screening for all applicants against this updated profile?"),
                    () => {
                        frappe.call({
                            method: "ecclesia.api.recruitment_auto_screen.rescreen_all_applicants",
                            args: { job_opening: frm.doc.job_opening },
                            callback(r) {
                                if (r.message) {
                                    frappe.show_alert({
                                        message: __("{0} applicants queued for re-screening", [r.message.enqueued]),
                                        indicator: "green"
                                    });
                                }
                            }
                        });
                    }
                );
            }, __("Tools"));

            frm.add_custom_button(__("Dispatch Emails Now"), () => {
                frappe.confirm(__("Send shortlist and rejection emails to all screened applicants?"), () => {
                    frappe.call({
                        method: "ecclesia.api.recruitment_auto_screen.manually_dispatch_emails",
                        args: { job_opening: frm.doc.job_opening },
                        callback(r) {
                            if (r.message?.success) {
                                frappe.show_alert({ message: __("Emails dispatched!"), indicator: "green" });
                            }
                        }
                    });
                });
            }, __("Tools"));
        }
    },

    // Live weight total calculator
    education_weight:       frm => frm.trigger("_update_weight_total"),
    degree_class_weight:    frm => frm.trigger("_update_weight_total"),
    experience_weight:      frm => frm.trigger("_update_weight_total"),
    skills_weight:          frm => frm.trigger("_update_weight_total"),
    certifications_weight:  frm => frm.trigger("_update_weight_total"),
    location_weight:        frm => frm.trigger("_update_weight_total"),
    salary_weight:          frm => frm.trigger("_update_weight_total"),

    _update_weight_total(frm) {
        const d = frm.doc;
        const total = (d.education_weight||0) + (d.degree_class_weight||0) +
                      (d.experience_weight||0) + (d.skills_weight||0) +
                      (d.certifications_weight||0) + (d.location_weight||0) +
                      (d.salary_weight||0);
        frm.set_value("total_weight_display", Math.round(total * 10) / 10);
        const color = Math.abs(total - 100) < 0.1 ? "green" : "red";
        frm.set_df_property("total_weight_display", "description",
            `<b style="color:${color}">Total must equal 100%. Currently: ${total.toFixed(1)}%</b>`);
    },

    gender_target_enabled(frm) { frm.trigger("_toggle_diversity_fields"); },

    _toggle_diversity_fields(frm) {
        const en = !!frm.doc.gender_target_enabled;
        frm.set_df_property("gender_target",       "hidden", !en);
        frm.set_df_property("gender_equity_bonus", "hidden", !en);
        frm.set_df_property("diversity_note",      "hidden", !en);
        if (en) {
            frm.set_df_property("gender_target",       "reqd", 1);
            frm.set_df_property("gender_equity_bonus", "reqd", 1);
        }
    },

    salary_knockout(frm) {
        if (frm.doc.salary_knockout) {
            frappe.msgprint({
                title: __("Salary Knockout Enabled"),
                message: __("Applicants expecting more than the maximum budget will be automatically rejected. Ensure the budget range is realistic before enabling this."),
                indicator: "orange"
            });
        }
    },

    _toggle_salary_fields(frm) {
        frm.set_df_property("salary_budget_min", "reqd", !!frm.doc.salary_knockout);
        frm.set_df_property("salary_budget_max", "reqd", !!frm.doc.salary_knockout);
    },

    location_requirement(frm) {
        const req = frm.doc.location_requirement;
        const needsCity = req === "Specified City Only" || req === "Same City";
        frm.set_df_property("job_location_city",  "reqd", needsCity);
        frm.set_df_property("job_location_state",
            "reqd", req === "Same State" || needsCity);
    },

    degree_class_knockout(frm) {
        if (frm.doc.degree_class_knockout) {
            frm.set_df_property("min_degree_class", "reqd", 1);
        }
    }
});
