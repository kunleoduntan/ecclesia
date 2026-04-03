// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

frappe.ui.form.on("Performance Cycle", {

    refresh(frm) {
        _set_phase_indicator(frm);
        _render_phase_timeline(frm);
        _add_hr_buttons(frm);
        _render_completion_stats(frm);
    },

    kpi_weight:     frm => _check_weights(frm),
    manager_weight: frm => _check_weights(frm),
    peer_weight:    frm => _check_weights(frm),
    self_weight:    frm => _check_weights(frm),
});


function _set_phase_indicator(frm) {
    const map = {
        "Draft": "gray", "Goal Setting": "blue", "Self Appraisal": "purple",
        "Peer Review": "purple", "Manager Review": "teal",
        "Calibration": "orange", "Results Released": "green", "Closed": "darkgrey"
    };
    frm.page.set_indicator(frm.doc.status || "Draft", map[frm.doc.status] || "gray");
}


function _render_phase_timeline(frm) {
    const phases = [
        { key: "Goal Setting",    deadline: frm.doc.goal_setting_deadline },
        { key: "Self Appraisal",  deadline: frm.doc.self_appraisal_deadline },
        { key: "Peer Review",     deadline: frm.doc.peer_review_deadline },
        { key: "Manager Review",  deadline: frm.doc.manager_review_deadline },
        { key: "Calibration",     deadline: frm.doc.calibration_deadline },
        { key: "Results Released",deadline: null },
    ];
    const order  = phases.map(p => p.key);
    const current = order.indexOf(frm.doc.status);

    const html = `
        <div style="display:flex;align-items:center;gap:0;padding:1rem 0;overflow-x:auto">
            ${phases.map((p, i) => {
                const done    = i < current;
                const active  = i === current;
                const color   = done ? "#1D9E75" : active ? "#534AB7" : "var(--color-border-tertiary)";
                const txtClr  = done ? "#085041" : active ? "#26215C" : "var(--color-text-tertiary)";
                const bg      = done ? "#E1F5EE"  : active ? "#EEEDFE" : "var(--color-background-secondary)";
                const connector = i < phases.length - 1
                    ? `<div style="flex:1;height:2px;background:${done ? '#1D9E75' : 'var(--color-border-tertiary)'};min-width:16px"></div>`
                    : "";
                return `
                    <div style="display:flex;flex-direction:column;align-items:center;gap:4px;min-width:80px">
                        <div style="width:28px;height:28px;border-radius:50%;background:${bg};
                                    border:2px solid ${color};display:flex;align-items:center;
                                    justify-content:center;font-size:11px;font-weight:500;color:${txtClr}">
                            ${done ? "✓" : i + 1}
                        </div>
                        <span style="font-size:10px;font-weight:${active?'500':'400'};
                                     color:${txtClr};text-align:center;line-height:1.3">
                            ${p.key}
                        </span>
                        ${p.deadline ? `<span style="font-size:9px;color:var(--color-text-tertiary)">${frappe.datetime.str_to_user(p.deadline)}</span>` : ""}
                    </div>
                    ${connector}
                `;
            }).join("")}
        </div>`;

    $(frm.fields_dict["title"].$wrapper)
        .closest(".form-section")
        .before(`<div class="form-section" style="padding:0 15px">${html}</div>`);
}


function _add_hr_buttons(frm) {
    if (!frappe.user.has_role(["HR Manager", "System Manager"])) return;
    if (frm.doc.docstatus !== 1 || frm.doc.status === "Closed") return;

    const next_label = {
        "Goal Setting":    "Open Self-Appraisal phase",
        "Self Appraisal":  "Open Peer Review phase",
        "Peer Review":     "Open Manager Review phase",
        "Manager Review":  "Open Calibration phase",
        "Calibration":     "Release Results",
        "Results Released":"Close Cycle",
    }[frm.doc.status];

    if (next_label) {
        frm.add_custom_button(next_label, () => {
            frappe.confirm(
                `<strong>${next_label}</strong><br>This action cannot be undone.`,
                () => frm.call("advance_phase").then(r => {
                    frappe.show_alert({ message: `Phase → ${r.message}`, indicator: "green" });
                    frm.reload_doc();
                })
            );
        }).addClass("btn-primary");
    }

    frm.add_custom_button("Recompute All Scores", () => {
        frappe.call({
            method: "ecclesia.api.performance.recompute_all_scores",
            args: { cycle_name: frm.doc.name },
            callback: ({ message: m }) =>
                frappe.show_alert({ message: `Recomputed ${m.recomputed} records`, indicator: "green" })
        });
    }, "Tools");
}


function _render_completion_stats(frm) {
    if (frm.is_new() || frm.doc.docstatus === 0) return;
    frappe.call({
        method: "ecclesia.api.performance.get_cycle_completion_stats",
        args: { cycle: frm.doc.name },
        callback({ message: s }) {
            if (!s || !s.total) return;
            const pct = v => Math.round((v / s.total) * 100);
            const bar = (v, color) => `
                <div style="margin-bottom:8px">
                    <div style="display:flex;justify-content:space-between;
                                font-size:12px;margin-bottom:3px;color:var(--color-text-secondary)">
                        <span>${v.label}</span>
                        <span style="font-weight:500">${v.val} / ${s.total} (${pct(v.val)}%)</span>
                    </div>
                    <div style="height:6px;background:var(--color-background-secondary);
                                border-radius:3px;overflow:hidden">
                        <div style="width:${pct(v.val)}%;height:6px;
                                    background:${color};border-radius:3px;
                                    transition:width .4s"></div>
                    </div>
                </div>`;

            const html = `
                <div style="padding:1rem 0">
                    <p style="font-size:11px;font-weight:500;text-transform:uppercase;
                               letter-spacing:.05em;color:var(--color-text-tertiary);margin:0 0 12px">
                        Cycle completion
                    </p>
                    ${bar({ label: "Goals set",        val: s.goals_set  }, "#185FA5")}
                    ${bar({ label: "Self-appraisals",  val: s.self_done  }, "#534AB7")}
                    ${bar({ label: "Peer reviews",     val: s.peer_done  }, "#7F77DD")}
                    ${bar({ label: "Manager reviews",  val: s.mgr_done   }, "#1D9E75")}
                    ${bar({ label: "Calibrated",       val: s.calibrated }, "#BA7517")}
                </div>`;

            frm.dashboard.add_section(html, "Completion Progress");
        }
    });
}


function _check_weights(frm) {
    const total = (frm.doc.kpi_weight     || 0) + (frm.doc.manager_weight || 0) +
                  (frm.doc.peer_weight    || 0) + (frm.doc.self_weight    || 0);
    const ok    = Math.abs(total - 100) < 0.01;
    const desc  = ok ? "✓ Weights sum to 100%" : `⚠ Weights sum to ${total.toFixed(1)}% — must equal 100%`;
    frm.set_df_property("kpi_weight", "description", desc);
}