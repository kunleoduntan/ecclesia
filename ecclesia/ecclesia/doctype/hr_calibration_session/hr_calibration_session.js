// ecclesia/doctype/hr_calibration_session/hr_calibration_session.js
frappe.ui.form.on("HR Calibration Session", {

    refresh(frm) {
        if (frm.doc.docstatus === 1) {
            frm.set_intro(__("Session completed. Rating overrides have been applied."), "green");
        }
        if (frm.doc.docstatus === 0 && frm.doc.performance_cycle) {
            frm.add_custom_button(__("Load Team Scores"), () => {
                frm.trigger("_load_team_scores");
            }, __("Tools"));
        }
    },

    _load_team_scores(frm) {
        if (!frm.doc.performance_cycle) {
            frappe.msgprint(__("Please select a Performance Cycle first."));
            return;
        }
        frappe.call({
            method: "ecclesia.api.performance_portal.get_calibration_data",
            args: {
                cycle: frm.doc.performance_cycle,
                department: frm.doc.department || null
            },
            callback(r) {
                if (!r.message) return;
                const data = r.message;
                let html = `<table class="table table-bordered table-sm">
                    <thead><tr><th>Employee</th><th>Goal</th><th>Peer</th><th>Manager</th><th>Composite</th></tr></thead><tbody>`;
                (data.records || []).forEach(rec => {
                    html += `<tr>
                        <td>${rec.employee}</td>
                        <td>${rec.kpi_score || "—"}</td>
                        <td>${rec.peer_score || "—"}</td>
                        <td>${rec.manager_score || "—"}</td>
                        <td><b>${rec.composite_score || "—"}</b></td>
                    </tr>`;
                });
                html += "</tbody></table>";
                html += `<p>Department average: <b>${data.average}%</b> across ${data.total} employees.</p>`;
                frappe.msgprint({ title: __("Team Score Summary"), message: html, wide: true });
            }
        });
    }
});
