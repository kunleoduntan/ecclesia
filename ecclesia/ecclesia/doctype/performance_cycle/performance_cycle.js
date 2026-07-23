// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

// ecclesia/doctype/performance_cycle/performance_cycle.js
frappe.ui.form.on("Performance Cycle", {

    refresh(frm) {
        frm.trigger("_status_badge");
        frm.trigger("_render_dates_dashboard");
        frm.trigger("_render_analytics_dashboard");
        frm.trigger("_render_tracking_dashboard");
        frm.trigger("_add_buttons");
    },

    // ── Status indicator ─────────────────────────────────────────────
    _status_badge(frm) {
        const colors = { Draft:"grey", Active:"green", Closed:"blue", Cancelled:"red" };
        frm.page.set_indicator(frm.doc.status, colors[frm.doc.status] || "grey");
    },

    // ── Dates section dashboard ──────────────────────────────────────
    _render_dates_dashboard(frm) {
        const d = frm.doc;
        if (!d.start_date || !d.end_date) return;

        const today   = frappe.datetime.get_today();
        const elapsed = frappe.datetime.get_diff(today, d.start_date);
        const total   = frappe.datetime.get_diff(d.end_date, d.start_date);
        const pct     = total > 0 ? Math.min(100, Math.round(elapsed / total * 100)) : 0;
        const remaining = Math.max(0, frappe.datetime.get_diff(d.end_date, today));

        const barColor = pct >= 90 ? "#DC2626" : pct >= 70 ? "#D97706" : "#059669";

        const html = `
        <div style="font-family:var(--font-sans,Calibri)">
          <!-- Timeline bar -->
          <div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:10px;
                      padding:14px 16px;margin-bottom:10px">
            <div style="display:flex;justify-content:space-between;
                        font-size:11px;color:#6B7280;margin-bottom:6px">
              <span>📅 ${d.start_date}</span>
              <span style="font-weight:700;color:${barColor}">${pct}% elapsed</span>
              <span>🏁 ${d.end_date}</span>
            </div>
            <div style="height:10px;background:#E5E7EB;border-radius:99px;overflow:hidden">
              <div style="width:${pct}%;height:100%;background:${barColor};
                          border-radius:99px;transition:width .5s"></div>
            </div>
            <div style="display:flex;justify-content:space-between;
                        font-size:11px;margin-top:6px">
              <span style="color:#6B7280">${elapsed} days elapsed</span>
              <span style="color:${barColor};font-weight:700">
                ${remaining} days remaining
              </span>
              <span style="color:#6B7280">${total} days total</span>
            </div>
          </div>

          <!-- Stage deadlines -->
          ${frm.trigger("_deadline_timeline_html") || ""}
        </div>`;

        frm.set_df_property("cycle_duration_days", "description", html);
        frm.refresh_field("cycle_duration_days");
    },

    _deadline_timeline_html(frm) {
        const d = frm.doc;
        const today = frappe.datetime.get_today();
        const stages = [
            { field:"goal_setting_deadline",   label:"Goal Setting",   icon:"🎯" },
            { field:"goal_approval_deadline",  label:"Goal Approval",  icon:"✅" },
            { field:"self_appraisal_deadline", label:"Self Appraisal", icon:"📝" },
            { field:"peer_review_deadline",    label:"Peer Review",    icon:"👥" },
            { field:"manager_review_deadline", label:"Mgr Review",     icon:"👔" },
            { field:"calibration_deadline",    label:"Calibration",    icon:"⚖️" },
        ];
        if (!stages.some(s => d[s.field])) return "";

        const rows = stages.filter(s => d[s.field]).map(s => {
            const diff = frappe.datetime.get_diff(d[s.field], today);
            const past = diff < 0;
            const near = diff >= 0 && diff <= 3;
            const color = past ? "#9CA3AF" : near ? "#DC2626" : "#059669";
            const tag   = past ? "Done" : near ? `${diff}d left!` : `${diff}d`;
            return `<div style="display:flex;align-items:center;gap:8px;padding:5px 0;
                                border-bottom:1px solid #F3F4F6">
              <span style="font-size:14px">${s.icon}</span>
              <span style="font-size:12px;color:#374151;flex:1">${s.label}</span>
              <span style="font-size:11px;color:#6B7280">${d[s.field]}</span>
              <span style="background:${color}22;color:${color};font-size:10px;
                           font-weight:700;padding:2px 8px;border-radius:99px">${tag}</span>
            </div>`;
        }).join("");

        return `<div style="background:#F8FAFC;border:1px solid #E5E7EB;border-radius:10px;
                            padding:12px 14px;margin-top:8px">${rows}</div>`;
    },

    // ── Analytics section dashboard ──────────────────────────────────
    _render_analytics_dashboard(frm) {
        const d = frm.doc;
        if (!d.total_employees) return;

        const statCard = (icon, label, value, color, sub) => `
          <div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:10px;
                      padding:12px;text-align:center;flex:1;min-width:90px">
            <div style="font-size:20px">${icon}</div>
            <div style="font-size:18px;font-weight:900;color:${color};margin:3px 0">
              ${value}
            </div>
            <div style="font-size:10px;color:#6B7280;font-weight:600">${label}</div>
            ${sub ? `<div style="font-size:9px;color:#9CA3AF;margin-top:2px">${sub}</div>` : ""}
          </div>`;

        const html = `
        <div style="font-family:var(--font-sans,Calibri)">
          <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">
            ${statCard("👥", "Employees", d.total_employees, "#2563EB")}
            ${statCard("✅", "Completed", d.submitted_count || 0, "#059669",
                        d.completion_rate + "% rate")}
            ${statCard("📊", "Avg Score", (d.avg_composite_score || 0).toFixed(1) + "%",
                        "#7C3AED")}
            ${statCard("⭐", "Avg Final",
                        d.avg_final_rating ? d.avg_final_rating.toFixed(1) + "%" : "TBD",
                        "#D97706")}
          </div>
          ${d.performance_breakdown ? `
          <div style="background:#EDE9FE;border-radius:8px;padding:10px 14px;">
            <div style="font-size:10px;font-weight:700;color:#5B21B6;
                        text-transform:uppercase;letter-spacing:.4px;margin-bottom:4px">
              Rating Distribution
            </div>
            <div style="font-size:12px;color:#374151">${d.performance_breakdown}</div>
          </div>` : ""}
        </div>`;

        frm.set_df_property("total_employees", "description", html);
        frm.refresh_field("total_employees");
    },

    // ── Progress tracking dashboard ───────────────────────────────────
    _render_tracking_dashboard(frm) {
        const d = frm.doc;

        const stages = [
            { label:"Goal Setting",   value: d.goal_setting_progress   || 0, color:"#F59E0B" },
            { label:"Self Appraisal", value: d.self_appraisal_progress  || 0, color:"#7C3AED" },
            { label:"Peer Review",    value: d.peer_review_progress     || 0, color:"#0D9488" },
            { label:"Mgr Review",     value: d.manager_review_progress  || 0, color:"#2563EB" },
            { label:"Calibration",    value: d.calibration_progress     || 0, color:"#EA580C" },
        ];

        const overall = d.overall_progress || 0;
        const overallColor = overall >= 80 ? "#059669"
            : overall >= 50 ? "#D97706" : "#DC2626";

        const bars = stages.map(s => `
          <div style="margin-bottom:8px">
            <div style="display:flex;justify-content:space-between;
                        font-size:11px;margin-bottom:3px">
              <span style="color:#6B7280;font-weight:600">${s.label}</span>
              <span style="color:${s.color};font-weight:700">${(s.value||0).toFixed(0)}%</span>
            </div>
            <div style="height:7px;background:#F3F4F6;border-radius:99px;overflow:hidden">
              <div style="width:${Math.min(100, s.value||0)}%;height:100%;
                          background:${s.color};border-radius:99px;transition:.5s"></div>
            </div>
          </div>`).join("");

        const html = `
        <div style="font-family:var(--font-sans,Calibri)">
          ${bars}
          <!-- Overall -->
          <div style="background:#F8FAFC;border:1px solid #E5E7EB;border-radius:10px;
                      padding:12px 14px;margin-top:10px;display:flex;
                      align-items:center;gap:12px">
            <div>
              <div style="font-size:10px;font-weight:700;color:#6B7280;
                          text-transform:uppercase;margin-bottom:2px">
                Overall Cycle Progress
              </div>
              <div style="height:12px;width:200px;background:#E5E7EB;
                          border-radius:99px;overflow:hidden">
                <div style="width:${overall}%;height:100%;background:${overallColor};
                            border-radius:99px;transition:.5s"></div>
              </div>
            </div>
            <div style="font-size:28px;font-weight:900;color:${overallColor}">
              ${overall.toFixed(0)}%
            </div>
          </div>
        </div>`;

        frm.set_df_property("goal_setting_progress", "description", html);
        frm.refresh_field("goal_setting_progress");
    },

    // ── Action buttons ───────────────────────────────────────────────
    _add_buttons(frm) {
        frm.add_custom_button(__("Refresh Analytics"), () => {
            frappe.show_progress(__("Calculating"), 30, 100);
            frappe.call({
                method: "ecclesia.doctype.performance_cycle.performance_cycle.refresh_cycle_analytics",
                args: { docname: frm.doc.name },
                callback(r) {
                    frappe.hide_progress();
                    if (r.message) {
                        frm.reload_doc();
                        frappe.show_alert({
                            message: __("Analytics updated — Overall: {0}%",
                                [r.message.overall_progress]),
                            indicator: "green"
                        });
                    }
                }
            });
        }, __("Tools"));

        if (frm.doc.docstatus === 1 && frm.doc.status === "Active") {
            frm.add_custom_button(__("Close Cycle"), () => {
                frappe.confirm(__("Mark this cycle as Closed?"), () => {
                    frappe.db.set_value("Performance Cycle", frm.doc.name, "status", "Closed")
                        .then(() => frm.reload_doc());
                });
            }, __("Actions"));
            frm.add_custom_button(__("Completion Report"), () => {
                frappe.route_options = { cycle: frm.doc.name };
                frappe.set_route("query-report", "Cycle Completion Status");
            }, __("Reports"));
        }
    },

    // Recalculate duration on date change
    start_date: frm => frm.trigger("_render_dates_dashboard"),
    end_date:   frm => frm.trigger("_render_dates_dashboard"),
});