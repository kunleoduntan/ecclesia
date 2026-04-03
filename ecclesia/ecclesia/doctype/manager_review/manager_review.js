// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

// ecclesia/public/js/manager_review.js

frappe.ui.form.on("Manager Review", {

    refresh(frm) {
        frm.page.set_indicator(
            frm.doc.status || "Draft",
            frm.doc.status === "Submitted" ? "green" : "orange"
        );
        _render_context_panel(frm);
        _add_manager_buttons(frm);
        _lock_if_submitted(frm);
    },

    overall_score(frm) {
        _auto_suggest_rating(frm);
        _check_score_range(frm);
    },

    recommended_rating(frm) {
        _warn_rating_deviation(frm);
    },
});


frappe.ui.form.on("Manager Goal Comment", {
    manager_score(frm) {
        _refresh_goal_avg(frm);
    }
});


function _lock_if_submitted(frm) {
    if (frm.doc.status !== "Submitted") return;
    ["overall_score", "recommended_rating", "strengths",
     "areas_for_improvement", "development_plan"].forEach(f =>
        frm.set_df_property(f, "read_only", 1)
    );
}


function _render_context_panel(frm) {
    if (!frm.doc.performance_record || frm.is_new()) return;

    frappe.db.get_value(
        "Employee Performance Record",
        frm.doc.performance_record,
        ["kpi_score", "self_score", "peer_score", "composite_score",
         "peer_review_count", "final_rating", "department", "designation"]
    ).then(({ message: s }) => {
        if (!s) return;

        const score_bar = (label, val, color) => `
            <div style="margin-bottom:6px">
                <div style="display:flex;justify-content:space-between;
                            font-size:12px;margin-bottom:2px;color:var(--color-text-secondary)">
                    <span>${label}</span>
                    <span style="font-weight:500;color:var(--color-text-primary)">
                        ${(val || 0).toFixed(2)} / 5
                    </span>
                </div>
                <div style="height:4px;background:var(--color-background-secondary);
                            border-radius:2px;overflow:hidden">
                    <div style="width:${((val||0)/5)*100}%;height:4px;
                                background:${color};border-radius:2px"></div>
                </div>
            </div>`;

        const html = `
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;padding:.75rem 0">
                <div>
                    <p style="font-size:11px;font-weight:500;text-transform:uppercase;
                               letter-spacing:.05em;color:var(--color-text-tertiary);margin:0 0 10px">
                        Score context
                    </p>
                    ${score_bar("KPI score",    s.kpi_score,  "#185FA5")}
                    ${score_bar("Self score",   s.self_score, "#BA7517")}
                    ${score_bar("Peer score",   s.peer_score, "#534AB7")}
                    ${score_bar("Composite",    s.composite_score, "#1D9E75")}
                    <div style="font-size:11px;color:var(--color-text-tertiary);margin-top:6px">
                        ${s.peer_review_count || 0} peer review(s) ·
                        System rating: <strong>${s.final_rating || "Pending"}</strong>
                    </div>
                </div>
                <div id="peer-competency-panel">
                    <p style="font-size:11px;font-weight:500;text-transform:uppercase;
                               letter-spacing:.05em;color:var(--color-text-tertiary);margin:0 0 10px">
                        Peer competency (anonymous)
                    </p>
                    <div id="peer-comp-inner" style="font-size:12px;color:var(--color-text-tertiary)">
                        Loading…
                    </div>
                </div>
            </div>`;

        frm.dashboard.add_section(html, "Employee Review Context");

        frappe.call({
            method: "ecclesia.api.performance.get_peer_summary_for_manager",
            args: { performance_record: frm.doc.performance_record },
            callback({ message }) {
                if (!message || !message.length) {
                    $("#peer-comp-inner").text("No peer data yet.");
                    return;
                }
                $("#peer-comp-inner").html(
                    message.map(c => `
                        <div style="display:flex;align-items:center;gap:8px;margin-bottom:5px">
                            <span style="min-width:120px;color:var(--color-text-secondary)">
                                ${c.competency}
                            </span>
                            <div style="flex:1;height:4px;background:var(--color-background-secondary);
                                        border-radius:2px;overflow:hidden">
                                <div style="width:${(c.avg/5)*100}%;height:4px;
                                            background:${c.avg>=4?"#1D9E75":c.avg>=3?"#185FA5":"#BA7517"};
                                            border-radius:2px"></div>
                            </div>
                            <span style="font-weight:500;min-width:28px;text-align:right;
                                         color:var(--color-text-primary)">${c.avg.toFixed(1)}</span>
                            <span style="font-size:10px;color:var(--color-text-tertiary)">
                                (${c.count})
                            </span>
                        </div>`).join("")
                );
            }
        });
    });
}


function _add_manager_buttons(frm) {
    if (frm.doc.status === "Submitted") return;

    frm.add_custom_button("Average Goal Scores", () => {
        const rows = frm.doc.goals_commentary || [];
        const scored = rows.filter(r => r.manager_score);
        if (!scored.length) {
            frappe.msgprint("Score at least one goal in the Goal Review table first.");
            return;
        }
        const avg     = scored.reduce((s, r) => s + parseFloat(r.manager_score), 0) / scored.length;
        const rounded = Math.round(avg * 2) / 2;
        frm.set_value("overall_score", rounded);
        frappe.show_alert({
            message: `Overall score → ${rounded.toFixed(1)} (avg of ${scored.length} goals)`,
            indicator: "blue"
        });
    }, "Tools");

    frm.add_custom_button("Submit Review", () => _submit_guard(frm)).addClass("btn-primary");
}


function _submit_guard(frm) {
    const errors = [];
    if (!frm.doc.overall_score)                                errors.push("Overall Score is required.");
    else if (frm.doc.overall_score < 1 || frm.doc.overall_score > 5)
                                                               errors.push("Score must be 1–5.");
    if (!frm.doc.recommended_rating)                           errors.push("Recommended Rating is required.");
    if (!(frm.doc.strengths || "").trim())                     errors.push("Key Strengths narrative required.");
    if (!(frm.doc.areas_for_improvement || "").trim())         errors.push("Areas for Improvement required.");
    const unscored = (frm.doc.goals_commentary || []).filter(r => !r.manager_score);
    if (unscored.length) errors.push(`${unscored.length} goal(s) have no manager score.`);

    if (errors.length) {
        frappe.msgprint({
            title: "Cannot submit — resolve the following",
            message: `<ul>${errors.map(e => `<li>${e}</li>`).join("")}</ul>`,
            indicator: "red"
        });
        return;
    }

    frappe.confirm(
        `Submit review for <strong>${frm.doc.employee_name}</strong>?<br>
         Score: <strong>${frm.doc.overall_score}</strong> —
         <strong>${frm.doc.recommended_rating}</strong><br>
         <small>Scores will be recomputed on submission.</small>`,
        () => frm.savesubmit().then(() => frm.reload_doc())
    );
}


function _auto_suggest_rating(frm) {
    const s = frm.doc.overall_score;
    if (!s) return;
    const r = s >= 4.5 ? "Outstanding" :
              s >= 3.5 ? "Exceeds Expectations" :
              s >= 2.5 ? "Meets Expectations" :
              s >= 1.5 ? "Needs Improvement" : "Unsatisfactory";
    if (frm.doc.recommended_rating !== r) frm.set_value("recommended_rating", r);
}


function _check_score_range(frm) {
    const s = frm.doc.overall_score;
    if (s && (s < 1 || s > 5)) {
        frappe.show_alert({ message: "Score must be between 1 and 5.", indicator: "red" });
        frm.set_value("overall_score", Math.min(5, Math.max(1, s)));
    }
}


function _warn_rating_deviation(frm) {
    if (!frm.doc.performance_record || !frm.doc.recommended_rating) return;
    frappe.db.get_value("Employee Performance Record",
                        frm.doc.performance_record, "final_rating")
        .then(({ message }) => {
            if (!message?.final_rating) return;
            const rank = r => ["Unsatisfactory","Needs Improvement","Meets Expectations",
                               "Exceeds Expectations","Outstanding"].indexOf(r);
            const gap = Math.abs(rank(frm.doc.recommended_rating) - rank(message.final_rating));
            frm.set_df_property("recommended_rating", "description",
                gap >= 2
                    ? `⚠ ${gap} level(s) from system rating (${message.final_rating}). Justify in development plan.`
                    : ""
            );
        });
}


function _refresh_goal_avg(frm) {
    const rows   = frm.doc.goals_commentary || [];
    const scored = rows.filter(r => r.manager_score);
    if (!scored.length) return;
    const avg = scored.reduce((s, r) => s + parseFloat(r.manager_score), 0) / scored.length;
    frm.set_df_property("overall_score", "description",
        `Goal avg: ${avg.toFixed(2)} (${scored.length}/${rows.length} goals scored)`);
}