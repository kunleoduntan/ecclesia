// ecclesia/doctype/performance_appeal/performance_appeal.js
frappe.ui.form.on("Performance Appeal", {

    refresh(frm) {
        const colors = {
            Submitted:"orange","Under Review":"blue",
            Upheld:"green",Dismissed:"red"
        };
        frm.page.set_indicator(frm.doc.status, colors[frm.doc.status]||"grey");
        frm.trigger("_show_rating_diff");

        if (frm.doc.docstatus === 1 && frappe.user.has_role("HR Manager")) {
            frm.add_custom_button(__("Uphold Appeal"), () => {
                frm.trigger("_decide_appeal", "Upheld");
            }, __("Decision"));
            frm.add_custom_button(__("Dismiss Appeal"), () => {
                frm.trigger("_decide_appeal", "Dismissed");
            }, __("Decision"));
        }
    },

    _show_rating_diff(frm) {
        if (!frm.doc.current_rating || !frm.doc.requested_rating) return;
        const diff = frm.doc.requested_rating - frm.doc.current_rating;
        frm.set_intro(
            `Requesting change: ${frm.doc.current_rating} → ${frm.doc.requested_rating} (${diff > 0 ? "+" : ""}${diff.toFixed(1)})`,
            diff > 0 ? "blue" : "orange"
        );
    },

    _decide_appeal(frm, outcome) {
        frappe.prompt([
            { fieldname:"final_rating", fieldtype:"Float", label:"Final Rating (1-5)",
              reqd: outcome==="Upheld" },
            { fieldname:"hr_decision",  fieldtype:"Text",  label:"Decision Rationale", reqd:1 }
        ], vals => {
            frappe.db.set_value("Performance Appeal", frm.doc.name, {
                status:       outcome,
                final_rating: vals.final_rating || frm.doc.current_rating,
                hr_decision:  vals.hr_decision,
                decided_by:   frappe.session.user,
                decision_date:frappe.datetime.get_today()
            }).then(() => frm.reload_doc());
        }, `${outcome} — Appeal Decision`);
    }
});
