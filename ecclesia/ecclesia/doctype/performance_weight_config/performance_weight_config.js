// ecclesia/doctype/performance_weight_config/performance_weight_config.js
frappe.ui.form.on("Performance Weight Config", {

    refresh(frm) {
        frm.trigger("_update_totals");
    },

    goal_weight: frm => frm.trigger("_update_totals"),
    competency_weight: frm => frm.trigger("_update_totals"),
    values_weight: frm => frm.trigger("_update_totals"),
    self_weight: frm => frm.trigger("_update_totals"),
    peer_weight: frm => frm.trigger("_update_totals"),
    manager_weight: frm => frm.trigger("_update_totals"),

    _update_totals(frm) {
        const d = frm.doc;
        const kpi_total = (d.goal_weight||0) + (d.competency_weight||0) + (d.values_weight||0);
        const rev_total = (d.self_weight||0) + (d.peer_weight||0) + (d.manager_weight||0);

        const kpiColor = Math.abs(kpi_total - 100) < 0.1 ? "green" : "red";
        const revColor = Math.abs(rev_total - 100) < 0.1 ? "green" : "red";

        frm.set_df_property("goal_weight", "description",
            `KPI Total: <b style="color:${kpiColor}">${kpi_total.toFixed(1)}%</b> (must be 100%)`);
        frm.set_df_property("self_weight", "description",
            `Reviewer Total: <b style="color:${revColor}">${rev_total.toFixed(1)}%</b> (must be 100%)`);
    },

    peer_anonymous(frm) {
        if (!frm.doc.peer_anonymous) {
            frappe.msgprint({
                title: __("Non-Anonymous Peer Reviews"),
                message: __("Reviewers will be identified. This may discourage honest feedback. Consider keeping reviews anonymous."),
                indicator: "orange"
            });
        }
    }
});
