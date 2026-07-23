// ecclesia/doctype/candidate_comparison_matrix/candidate_comparison_matrix.js
frappe.ui.form.on("Candidate Comparison Matrix", {

    refresh(frm) {
        frm.trigger("_render_ranking");

        if (!frm.is_new()) {
            frm.add_custom_button(__("Generate AI Comparison"), () => {
                frm.trigger("_request_ai_comparison");
            }, __("Tools"));

            frm.add_custom_button(__("View Screening Dashboard"), () => {
                frappe.call({
                    method: "ecclesia.api.recruitment_auto_screen.get_screening_dashboard",
                    args: { job_opening: frm.doc.job_opening },
                    callback(r) {
                        if (!r.message) return;
                        const stats = r.message.stats;
                        frappe.msgprint({
                            title: __("Screening Dashboard — {0}", [frm.doc.job_opening]),
                            message: `
                                <b>Total Applicants:</b> ${stats.total}<br>
                                <b>Shortlisted:</b> ${stats.shortlisted}<br>
                                <b>Referred:</b> ${stats.referred}<br>
                                <b>Rejected:</b> ${stats.rejected}<br>
                                <b>Average Score:</b> ${stats.avg_score}%
                            `,
                            indicator: "blue"
                        });
                    }
                });
            }, __("Tools"));
        }
    },

    _render_ranking(frm) {
        if (!frm.doc.candidates?.length) return;

        const sorted = [...frm.doc.candidates].sort((a, b) => b.total_score - a.total_score);
        const top = sorted[0];

        let html = `<div style="padding:8px 0">
            <div style="font-size:11px;font-weight:700;color:#6B7280;
                        text-transform:uppercase;letter-spacing:.4px;margin-bottom:8px">
              Score Ranking
            </div>`;

        sorted.forEach((c, i) => {
            const pct = Math.round(c.total_score || 0);
            const color = i === 0 ? "#059669" : i === 1 ? "#1D9E75" : "#6B7280";
            html += `
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:7px">
              <div style="font-size:11px;font-weight:700;color:${color};min-width:16px">#${i+1}</div>
              <div style="font-size:12px;flex:1">${c.candidate_name || "—"}</div>
              <div style="width:120px">
                <div style="height:5px;background:#eee;border-radius:99px;overflow:hidden">
                  <div style="width:${pct}%;height:100%;background:${color};border-radius:99px"></div>
                </div>
              </div>
              <div style="font-size:11px;font-weight:700;color:${color};min-width:32px">${pct}%</div>
            </div>`;
        });

        html += `</div>`;
        frm.set_df_property("job_opening", "description", html);
    },

    _request_ai_comparison(frm) {
        frappe.show_progress("AI Comparison", 30, 100, __("Generating comparison..."));
        frappe.call({
            method: "ecclesia.api.recruitment_ai.generate_candidate_comparison",
            args: { matrix_name: frm.doc.name },
            callback(r) {
                frappe.hide_progress();
                frm.reload_doc();
                frappe.show_alert({ message: __("AI comparison generated"), indicator: "green" });
            }
        });
    }
});

frappe.ui.form.on("Comparison Candidate", {
    total_score(frm) {
        // Re-render ranking whenever a score changes
        frm.trigger("_render_ranking");

        // Auto-assign ranks
        const rows = frm.doc.candidates || [];
        const sorted = [...rows].sort((a, b) => (b.total_score||0) - (a.total_score||0));
        sorted.forEach((row, i) => {
            frappe.model.set_value("Comparison Candidate", row.name, "hr_rank", i + 1);
        });
    },

    shortlisted(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.shortlisted) {
            frappe.show_alert({
                message: __("{0} marked as shortlisted", [row.candidate_name]),
                indicator: "green"
            });
        }
    }
});