// ecclesia/doctype/performance_competency/performance_competency.js
frappe.ui.form.on("Performance Competency", {

    refresh(frm) {
        frm.set_intro(
            frm.doc.is_active
                ? __("Active — available for appraisal cycles.")
                : __("Inactive — not shown in appraisal forms."),
            frm.doc.is_active ? "blue" : "orange"
        );
        if (!frm.is_new()) {
            frm.add_custom_button(__("View Usage"), () => {
                frappe.route_options = { competency: frm.doc.name };
                frappe.set_route("List", "Self Appraisal Competency");
            }, __("Reports"));
        }
    },

    category(frm) {
        const hints = {
            "Leadership":    "Strategic thinking, decision-making, team inspiration",
            "Communication": "Written, verbal, presentation, active listening",
            "Technical":     "Role-specific technical knowledge and application",
            "Behavioural":   "Attitude, work ethic, collaboration, adaptability",
            "Core Value":    "Integrity, customer focus, continuous improvement"
        };
        const hint = hints[frm.doc.category];
        if (hint) frm.set_df_property("description", "description", hint);
    }
});
