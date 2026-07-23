// ecclesia/doctype/manager_review_360/manager_review_360.js
frappe.ui.form.on("Manager Review 360", {

    refresh(frm) {
        frm.trigger("_toggle_recommendation_fields");
        frm.trigger("_show_score_summary");
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__("View Employee Record"), () => {
                frappe.set_route("Form", "Employee", frm.doc.employee);
            });
        }
    },

    recommend_pip(frm) {
        if (frm.doc.recommend_pip) {
            frappe.msgprint({
                title: __("PIP Recommendation"),
                message: __("A Performance Improvement Plan draft will be created automatically on submit. Please enter the PIP Reason below."),
                indicator: "orange"
            });
            frm.set_df_property("pip_reason", "reqd", 1);
        } else {
            frm.set_df_property("pip_reason", "reqd", 0);
        }
    },

    recommend_increment(frm) {
        frm.set_df_property("increment_percentage", "reqd", frm.doc.recommend_increment ? 1 : 0);
    },

    recommend_succession(frm) {
        frm.set_df_property("succession_role", "reqd", frm.doc.recommend_succession ? 1 : 0);
    },

    _toggle_recommendation_fields(frm) {
        frm.set_df_property("increment_percentage","hidden", !frm.doc.recommend_increment);
        frm.set_df_property("bonus_amount",        "hidden", !frm.doc.recommend_bonus);
        frm.set_df_property("training_details",    "hidden", !frm.doc.recommend_training);
        frm.set_df_property("pip_reason",          "hidden", !frm.doc.recommend_pip);
        frm.set_df_property("succession_role",     "hidden", !frm.doc.recommend_succession);
    },

    _show_score_summary(frm) {
        if (!frm.doc.overall_manager_rating) return;
        const labels = {1:"Unsatisfactory",2:"Needs Improvement",3:"Meets Expectations",
                        4:"Exceeds Expectations",5:"Outstanding"};
        const label = labels[Math.round(frm.doc.overall_manager_rating)] || "";
        frm.set_intro(
            __("Overall Rating: {0} — {1}", [frm.doc.overall_manager_rating, label]),
            frm.doc.overall_manager_rating >= 4 ? "green" : frm.doc.overall_manager_rating >= 3 ? "blue" : "orange"
        );
    },

    overall_manager_rating(frm) { frm.trigger("_show_score_summary"); }
});
