// ecclesia/doctype/performance_idp/performance_idp.js
frappe.ui.form.on("Performance IDP", {

    refresh(frm) {
        frm.trigger("_update_progress_display");
        if (!frm.is_new() && frm.doc.docstatus === 1) {
            frm.add_custom_button(__("Mark Complete"), () => {
                frappe.confirm(__("Mark this IDP as completed?"), () => {
                    frappe.db.set_value("Performance IDP", frm.doc.name, "status", "Completed")
                        .then(() => frm.reload_doc());
                });
            }, __("Actions"));
        }
    },

    _update_progress_display(frm) {
        const pct = frm.doc.overall_progress || 0;
        const color = pct >= 80 ? "green" : pct >= 40 ? "blue" : "orange";
        frm.set_intro(`Overall progress: <b>${pct}%</b>`, color);
    }
});

frappe.ui.form.on("IDP Item", {
    progress(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.progress >= 100) {
            frappe.model.set_value(cdt, cdn, "status", "Completed");
        } else if (row.progress > 0) {
            frappe.model.set_value(cdt, cdn, "status", "In Progress");
        }
        // Recalculate overall
        let total = 0, count = 0;
        (frm.doc.idp_items || []).forEach(r => { total += (r.progress || 0); count++; });
        if (count) frm.set_value("overall_progress", Math.round(total / count * 10) / 10);
        frm.trigger("_update_progress_display");
    }
});
