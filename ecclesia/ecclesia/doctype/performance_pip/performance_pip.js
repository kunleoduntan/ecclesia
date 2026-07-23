// ecclesia/doctype/performance_pip/performance_pip.js
frappe.ui.form.on("Performance PIP", {

    refresh(frm) {
        frm.trigger("_show_status_banner");
        if (frm.doc.docstatus === 1 && frm.doc.status === "Active") {
            frm.add_custom_button(__("Mark as Passed"), () => {
                frm.trigger("_close_pip", "Passed");
            }, __("Outcome"));
            frm.add_custom_button(__("Mark as Failed"), () => {
                frm.trigger("_close_pip", "Failed");
            }, __("Outcome"));
            frm.add_custom_button(__("Extend PIP"), () => {
                frm.trigger("_extend_pip");
            }, __("Outcome"));
        }
    },

    _show_status_banner(frm) {
        const colors = { Active:"blue", Extended:"orange", Passed:"green", Failed:"red", Cancelled:"grey" };
        frm.page.set_indicator(frm.doc.status, colors[frm.doc.status] || "grey");
        if (frm.doc.end_date) {
            const days = frappe.datetime.get_diff(frm.doc.end_date, frappe.datetime.get_today());
            if (days >= 0 && frm.doc.status === "Active") {
                frm.set_intro(`${days} day(s) remaining in PIP period.`,
                    days <= 7 ? "orange" : "blue");
            }
        }
    },

    _close_pip(frm, outcome) {
        frappe.prompt([
            { fieldname: "notes", fieldtype: "Text", label: "Outcome Notes", reqd: 1 }
        ], (vals) => {
            frappe.db.set_value("Performance PIP", frm.doc.name, {
                status: outcome,
                final_outcome: outcome === "Passed"
                    ? "Passed — Performance Improved"
                    : "Failed — Termination Recommended",
                outcome_notes: vals.notes
            }).then(() => frm.reload_doc());
        }, __(`Mark PIP as ${outcome}`));
    },

    _extend_pip(frm) {
        frappe.prompt([
            { fieldname: "new_end_date", fieldtype: "Date", label: "New End Date", reqd: 1 }
        ], (vals) => {
            frappe.db.set_value("Performance PIP", frm.doc.name, {
                end_date: vals.new_end_date,
                status: "Extended"
            }).then(() => frm.reload_doc());
        }, __("Extend PIP"));
    }
});
