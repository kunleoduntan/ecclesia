// ecclesia/doctype/skip_level_review/skip_level_review.js
frappe.ui.form.on("Skip Level Review", {

    refresh(frm) {
        if (frm.doc.employee && frm.doc.performance_cycle) {
            frm.trigger("_load_manager_rating");
        }
    },

    manager_rating_agreement(frm) {
        const show = frm.doc.manager_rating_agreement === "Disagree" ||
                     frm.doc.manager_rating_agreement === "Partially Agree";
        frm.set_df_property("adjusted_rating",    "hidden", !show);
        frm.set_df_property("adjustment_reason",  "hidden", !show);
        if (show) {
            frm.set_df_property("adjusted_rating",   "reqd", 1);
            frm.set_df_property("adjustment_reason", "reqd", 1);
        }
    },

    _load_manager_rating(frm) {
        frappe.db.get_value("Employee Performance Record",
            { employee: frm.doc.employee, cycle: frm.doc.performance_cycle },
            "manager_score"
        ).then(r => {
            if (r?.message?.manager_score) {
                frm.set_intro(
                    __("Manager's score for this employee: {0}/5", [r.message.manager_score]),
                    "blue"
                );
            }
        });
    }
});
