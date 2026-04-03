// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Performance Record", {

    refresh(frm) {
        _set_status_color(frm);
        _render_score_radar(frm);
        _render_goal_progress(frm);
        _add_employee_buttons(frm);
    },
});


function _set_status_color(frm) {
    const map = {
        "Goal Setting": "blue", "Self Appraisal": "purple",
        "Peer Review": "purple", "Manager Review": "teal",
        "Calibration": "orange", "Results Released": "green"
    };
    frm.page.set_indicator(frm.doc.status, map[frm.doc.status] || "gray");
}


function _render_score_radar(frm) {
    if (!frm.doc.composite_score) return;

    const scores = [
        { label: "KPI",     val: frm.doc.kpi_score     || 0, color: "#185FA5" },
        { label: "Manager", val: frm.doc.manager_score  || 0, color: "#1D9E75" },
        { label: "Peer",    val: frm.doc.peer_score     || 0, color: "#534AB7" },
        { label: "Self",    val: frm.doc.self_score     || 0, color: "#BA7517" },
    ];

    const ratingColor = {
        "Outstanding": "#1D9E75", "Exceeds Expectations": "#185FA5",
        "Meets Expectations": "#534AB7", "Needs Improvement": "#BA7517",
        "Unsatisfactory": "#E24B4A"
    };

    const html = `
        <div style="display:grid;grid-template-columns:auto 1fr;gap:1rem;
                    align-items:center;padding:1rem 0">
            <div style="text-align:center">
                <div style="font-size:36px;font-weight:500;
                            color:${ratingColor[frm.doc.calibrated_rating || frm.doc.final_rating] || '#534AB7'}">
                    ${(frm.doc.composite_score || 0).toFixed(2)}
                </div>
                <div style="font-size:12px;font-weight:500;margin-top:2px;
                            color:${ratingColor[frm.doc.calibrated_rating || frm.doc.final_rating] || '#534AB7'}">
                    ${frm.doc.calibrated_rating || frm.doc.final_rating || "Pending"}
                </div>
                ${frm.doc.calibrated_rating && frm.doc.calibrated_rating !== frm.doc.final_rating
                    ? `<div style="font-size:10px;color:var(--color-text-tertiary);margin-top:2px">
                           calibrated from ${frm.doc.final_rating}
                       </div>` : ""}
                <div style="font-size:10px;color:var(--color-text-tertiary);margin-top:4px">
                    composite / 5.0
                </div>
            </div>
            <div>
                ${scores.map(s => `
                    <div style="margin-bottom:8px">
                        <div style="display:flex;justify-content:space-between;
                                    font-size:12px;margin-bottom:3px">
                            <span style="color:var(--color-text-secondary)">${s.label}</span>
                            <span style="font-weight:500;color:var(--color-text-primary)">
                                ${s.val.toFixed(2)}
                            </span>
                        </div>
                        <div style="height:5px;background:var(--color-background-secondary);
                                    border-radius:3px;overflow:hidden">
                            <div style="width:${(s.val / 5) * 100}%;height:5px;
                                        background:${s.color};border-radius:3px"></div>
                        </div>
                    </div>`).join("")}
                <div style="font-size:11px;color:var(--color-text-tertiary);margin-top:6px">
                    ${frm.doc.peer_review_count || 0} peer review(s) received
                </div>
            </div>
        </div>`;

    frm.dashboard.add_section(html, "Score Summary");
}


function _render_goal_progress(frm) {
    if (!frm.doc.goals || !frm.doc.goals.length) return;

    const status_color = {
        "Achieved": "#1D9E75", "Partially Achieved": "#BA7517",
        "In Progress": "#185FA5", "Not Achieved": "#E24B4A",
        "Not Started": "#888780"
    };

    const rows = frm.doc.goals.map(g => {
        const pct  = g.achievement_pct ? Math.min(g.achievement_pct, 120) : 0;
        const bar_pct = Math.min(pct, 100);
        const color = pct >= 100 ? "#1D9E75" : pct >= 80 ? "#BA7517" : "#E24B4A";
        return `
            <div style="border:0.5px solid var(--color-border-tertiary);
                        border-radius:6px;padding:10px 12px;margin-bottom:8px">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;
                             margin-bottom:6px">
                    <div>
                        <span style="font-size:13px;font-weight:500;
                                     color:var(--color-text-primary)">${g.goal_description}</span>
                        <span style="font-size:11px;color:var(--color-text-tertiary);
                                     margin-left:8px">${g.kpi || ""}</span>
                    </div>
                    <span style="font-size:11px;font-weight:500;padding:2px 8px;
                                 border-radius:20px;background:var(--color-background-secondary);
                                 color:${status_color[g.status] || '#888780'}">
                        ${g.status || "Not Started"}
                    </span>
                </div>
                <div style="display:flex;gap:1rem;font-size:12px;
                             color:var(--color-text-secondary);margin-bottom:6px">
                    <span>Target: <strong>${g.target_value || "—"}</strong></span>
                    <span>Actual: <strong>${g.actual_value || "—"}</strong></span>
                    <span>Weight: <strong>${g.weight || 0}%</strong></span>
                    ${g.self_score ? `<span>Self score: <strong>${g.self_score}/5</strong></span>` : ""}
                </div>
                <div style="height:5px;background:var(--color-background-secondary);
                             border-radius:3px;overflow:hidden">
                    <div style="width:${bar_pct}%;height:5px;background:${color};
                                 border-radius:3px"></div>
                </div>
                ${pct ? `<div style="font-size:10px;color:var(--color-text-tertiary);
                                     margin-top:3px">${pct.toFixed(0)}% achieved</div>` : ""}
            </div>`;
    }).join("");

    frm.dashboard.add_section(`<div style="padding:.5rem 0">${rows}</div>`, "Goal Progress");
}


function _add_employee_buttons(frm) {
    if (frm.is_new() || frm.doc.docstatus !== 1) return;

    if (frm.doc.status === "Self Appraisal") {
        frm.add_custom_button("Submit Self-Appraisal", () => {
            if (!frm.doc.self_narrative || !frm.doc.self_narrative.trim()) {
                frappe.msgprint("Please write a self-appraisal narrative before submitting.");
                return;
            }
            const unscored = (frm.doc.goals || []).filter(g => !g.self_score);
            if (unscored.length) {
                frappe.msgprint(`${unscored.length} goal(s) have no self-score. Rate all goals first.`);
                return;
            }
            frappe.confirm("Submit your self-appraisal? You cannot edit it after submission.", () => {
                frappe.db.set_value("Employee Performance Record", frm.doc.name, {
                    "status": "Peer Review",
                    "self_appraisal_date": frappe.datetime.now_datetime()
                }).then(() => { frm.reload_doc(); });
            });
        }).addClass("btn-primary");
    }
}