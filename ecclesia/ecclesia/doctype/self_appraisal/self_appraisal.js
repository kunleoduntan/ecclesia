// ecclesia/doctype/self_appraisal/self_appraisal.js
frappe.ui.form.on("Self Appraisal", {

    refresh(frm) {
        frm.trigger("_set_indicators");
        frm.trigger("_add_buttons");
        frm.trigger("_load_competencies");
    },

    _set_indicators(frm) {
        const colors = { Draft:"orange", Submitted:"blue", Locked:"green" };
        frm.page.set_indicator(frm.doc.status, colors[frm.doc.status] || "grey");
        if (frm.doc.ai_feedback) {
            frm.set_df_property("ai_feedback", "hidden", 0);
        }
    },

    _add_buttons(frm) {
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__("View Performance Record"), () => {
                frappe.set_route("Form", "Employee Performance Record", {
                    employee: frm.doc.employee
                });
            });
        }
        if (!frm.is_new() && frm.doc.docstatus === 0) {
            frm.add_custom_button(__("Get AI Tips"), () => {
                frm.trigger("_fetch_ai_tips");
            }, __("Tools"));
        }
    },

    _load_competencies(frm) {
        // Auto-populate competency table from active competencies if empty
        if (!frm.is_new() || frm.doc.competency_ratings?.length) return;
        if (!frm.doc.performance_cycle) return;

        frappe.db.get_value("Performance Weight Config",
            { performance_cycle: frm.doc.performance_cycle },
            ["competency_weight"]
        ).then(r => {
            if (!r?.message) return;
        });
    },

    performance_cycle(frm) {
        if (!frm.doc.performance_cycle) return;
        frappe.db.get_value("Performance Cycle",
            frm.doc.performance_cycle,
            ["self_appraisal_deadline", "title"]
        ).then(r => {
            if (r?.message?.self_appraisal_deadline) {
                frm.set_intro(
                    __("Deadline: {0}", [frappe.datetime.str_to_user(r.message.self_appraisal_deadline)]),
                    "blue"
                );
            }
        });
    },

    overall_self_rating(frm) {
        const rating = frm.doc.overall_self_rating;
        if (!rating) return;
        const labels = { 1:"Unsatisfactory", 2:"Needs Improvement",
                         3:"Meets Expectations", 4:"Exceeds Expectations", 5:"Outstanding" };
        const label = labels[Math.round(rating)] || "";
        if (label) {
            frm.set_df_property("overall_self_rating", "description",
                `<b>${label}</b>`);
        }
    },

    _fetch_ai_tips(frm) {
        if (!frm.doc.key_accomplishments) {
            frappe.msgprint(__("Please fill in Key Accomplishments first."));
            return;
        }
        frappe.show_progress("AI Tips", 30, 100, __("Calling AI coach..."));
        frappe.call({
            method: "ecclesia.api.performance_portal.get_ai_coaching",
            args: { message: "Give me tips to write a strong self-appraisal narrative based on my accomplishments." },
            callback(r) {
                frappe.hide_progress();
                if (r.message?.response) {
                    frappe.msgprint({
                        title: __("AI Writing Tips"),
                        message: r.message.response,
                        indicator: "blue"
                    });
                }
            }
        });
    }
});

// Competency ratings child table
frappe.ui.form.on("Self Appraisal Competency", {
    self_rating(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.self_rating < 1 || row.self_rating > 5) {
            frappe.model.set_value(cdt, cdn, "self_rating",
                Math.max(1, Math.min(5, row.self_rating)));
            frappe.show_alert({ message: __("Rating must be between 1 and 5"), indicator: "orange" });
        }
    }
});
