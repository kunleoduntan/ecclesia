// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

// ecclesia/doctype/employee_performance_record/employee_performance_record.js

const EPR_BANDS = {
    "Outstanding":          { color: "#059669", bg: "#D1FAE5", icon: "🏆" },
    "Exceeds Expectations": { color: "#2563EB", bg: "#DBEAFE", icon: "⭐" },
    "Meets Expectations":   { color: "#0D9488", bg: "#CCFBF1", icon: "✅" },
    "Needs Improvement":    { color: "#D97706", bg: "#FEF3C7", icon: "⚠️" },
    "Unsatisfactory":       { color: "#DC2626", bg: "#FEE2E2", icon: "🔴" },
};

frappe.ui.form.on("Employee Performance Record", {

    refresh(frm) {
        frm.trigger("_status_badge");
        frm.trigger("_render_score_dashboard");
        frm.trigger("_render_analytics_dashboard");
        frm.trigger("_add_action_buttons");
    },

    // ── Status badge ────────────────────────────────────────────────
    _status_badge(frm) {
        const colors = {
            Draft:"grey", "In Progress":"blue", Calibrated:"orange",
            Final:"green", Released:"green", Cancelled:"red"
        };
        frm.page.set_indicator(frm.doc.status, colors[frm.doc.status] || "grey");
    },

    // ── Score dashboard (Section: Component Scores) ──────────────────
    _render_score_dashboard(frm) {
        const d = frm.doc;
        const band  = d.performance_band || "Meets Expectations";
        const style = EPR_BANDS[band] || EPR_BANDS["Meets Expectations"];
        const comp  = d.composite_score || 0;
        const final = d.final_rating    || 0;
        const calib = d.calibrated_rating || 0;

        const scoreBar = (label, val, max, color) => {
            const pct = Math.min(100, max === 5
                ? Math.round(val / 5 * 100)
                : Math.round(val));
            const disp = max === 5 ? val.toFixed(1) + "/5" : val.toFixed(1) + "%";
            return `
            <div style="margin-bottom:10px">
              <div style="display:flex;justify-content:space-between;
                          font-size:11px;margin-bottom:3px">
                <span style="color:#6B7280;font-weight:600">${label}</span>
                <span style="color:${color};font-weight:700">${disp}</span>
              </div>
              <div style="height:7px;background:#F3F4F6;border-radius:99px;overflow:hidden">
                <div style="width:${pct}%;height:100%;background:${color};
                            border-radius:99px;transition:width .5s ease"></div>
              </div>
            </div>`;
        };

        const html = `
        <div style="font-family:var(--font-sans,Calibri)">
          <!-- Band badge -->
          <div style="background:${style.bg};border:1px solid ${style.color}22;
                      border-radius:12px;padding:14px 18px;margin-bottom:14px;
                      display:flex;align-items:center;gap:14px">
            <div style="font-size:32px">${style.icon}</div>
            <div>
              <div style="font-size:18px;font-weight:800;color:${style.color}">
                ${comp.toFixed(1)}%
              </div>
              <div style="font-size:13px;font-weight:600;color:${style.color}">
                ${band}
              </div>
              ${calib ? `<div style="font-size:11px;color:#6B7280;margin-top:2px">
                Calibrated: ${calib.toFixed(1)}%
                ${final ? " | Final: " + final.toFixed(1) + "%" : ""}
              </div>` : ""}
            </div>
            <div style="margin-left:auto;text-align:right">
              <div style="font-size:10px;color:#6B7280;font-weight:600">PERCENTILE</div>
              <div style="font-size:20px;font-weight:800;color:${style.color}">
                ${(d.percentile_rank || 0).toFixed(0)}<span style="font-size:12px">th</span>
              </div>
            </div>
          </div>

          <!-- Score bars -->
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 24px">
            <div>
              ${scoreBar("Goal / KPI Score",  d.kpi_score   || 0, 100, "#F59E0B")}
              ${scoreBar("Self Score",         d.self_score  || 0, 5,   "#7C3AED")}
              ${scoreBar("Peer Average",       d.peer_score  || 0, 5,   "#0D9488")}
            </div>
            <div>
              ${scoreBar("Manager Score",      d.manager_score    || 0, 5,   "#2563EB")}
              ${scoreBar("Skip-Level Score",   d.skip_level_score || 0, 5,   "#DB2777")}
              ${scoreBar("Values Score",       d.values_score     || 0, 100, "#EA580C")}
            </div>
          </div>
        </div>`;

        frm.set_df_property("kpi_score", "description", html);
        frm.refresh_field("kpi_score");
    },

    // ── Analytics dashboard ──────────────────────────────────────────
    _render_analytics_dashboard(frm) {
        const d = frm.doc;
        if (!d.composite_score) return;

        const variance   = d.score_variance || 0;
        const varColor   = variance > 0 ? "#059669" : variance < 0 ? "#DC2626" : "#6B7280";
        const varIcon    = variance > 0 ? "▲" : variance < 0 ? "▼" : "—";

        const statCard = (label, value, sub, color) => `
          <div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:10px;
                      padding:12px 14px;flex:1;min-width:100px">
            <div style="font-size:10px;color:#6B7280;font-weight:700;
                        text-transform:uppercase;letter-spacing:.4px;margin-bottom:4px">
              ${label}
            </div>
            <div style="font-size:20px;font-weight:900;color:${color}">${value}</div>
            ${sub ? `<div style="font-size:10px;color:#9CA3AF;margin-top:2px">${sub}</div>` : ""}
          </div>`;

        const trend = d.performance_trend || "—";

        const html = `
        <div style="font-family:var(--font-sans,Calibri)">

          <!-- Trend bar -->
          <div style="background:#EDE9FE;border-radius:10px;padding:12px 16px;
                      margin-bottom:12px">
            <div style="font-size:10px;font-weight:700;color:#5B21B6;
                        text-transform:uppercase;letter-spacing:.4px;margin-bottom:5px">
              Performance Trend
            </div>
            <div style="font-size:13px;color:#1E293B;font-weight:500">${trend}</div>
          </div>

          <!-- Stat cards -->
          <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">
            ${statCard("Dept Rank", "#" + (d.rank_in_dept || "—"),
                       "in department", "#2563EB")}
            ${statCard("Percentile", (d.percentile_rank || 0).toFixed(0) + "th",
                       "company-wide", "#7C3AED")}
            ${statCard("Dept Avg", (d.dept_avg_score || 0).toFixed(1) + "%",
                       "department", "#0D9488")}
            ${statCard("Cycle Avg", (d.cycle_avg_score || 0).toFixed(1) + "%",
                       "company-wide", "#D97706")}
          </div>

          <!-- Variance indicator -->
          <div style="background:#F8FAFC;border:1px solid #E5E7EB;border-radius:10px;
                      padding:12px 16px;display:flex;align-items:center;gap:12px">
            <div style="font-size:24px;font-weight:900;color:${varColor};min-width:60px">
              ${varIcon} ${Math.abs(variance).toFixed(1)}%
            </div>
            <div>
              <div style="font-size:12px;font-weight:700;color:#374151">
                ${variance >= 0 ? "Above" : "Below"} Company Average
              </div>
              <div style="font-size:11px;color:#6B7280">
                Score: ${(d.composite_score||0).toFixed(1)}%  vs  
                Company Avg: ${(d.cycle_avg_score||0).toFixed(1)}%
              </div>
            </div>
          </div>
        </div>`;

        frm.set_df_property("performance_trend", "description", html);
        frm.refresh_field("performance_trend");

        // Dashboard view section
        const band   = d.performance_band || "Meets Expectations";
        const bStyle = EPR_BANDS[band] || EPR_BANDS["Meets Expectations"];
        const dashHtml = `
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;
                    font-family:var(--font-sans,Calibri)">
          <div style="background:${bStyle.bg};border:1px solid ${bStyle.color}33;
                      border-radius:10px;padding:14px;text-align:center">
            <div style="font-size:28px">${bStyle.icon}</div>
            <div style="font-size:13px;font-weight:800;color:${bStyle.color};margin-top:4px">
              ${band}
            </div>
            <div style="font-size:20px;font-weight:900;color:${bStyle.color};margin-top:2px">
              ${(d.composite_score||0).toFixed(1)}%
            </div>
          </div>
          <div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:10px;
                      padding:14px;text-align:center">
            <div style="font-size:22px">🎯</div>
            <div style="font-size:11px;font-weight:700;color:#065F46;margin-top:4px">
              KPI Achievement
            </div>
            <div style="font-size:18px;font-weight:900;color:#059669;margin-top:2px">
              ${(d.kpi_score||0).toFixed(1)}%
            </div>
          </div>
          <div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:10px;
                      padding:14px;text-align:center">
            <div style="font-size:22px">📊</div>
            <div style="font-size:11px;font-weight:700;color:#1D4ED8;margin-top:4px">
              Dept Rank
            </div>
            <div style="font-size:18px;font-weight:900;color:#2563EB;margin-top:2px">
              #${d.rank_in_dept||"—"}
            </div>
            <div style="font-size:10px;color:#6B7280">${(d.percentile_rank||0).toFixed(0)}th percentile</div>
          </div>
        </div>`;

        frm.set_df_property("dashboard_summary", "description", dashHtml);
        frm.refresh_field("dashboard_summary");
    },

    // ── Action buttons ───────────────────────────────────────────────
    _add_action_buttons(frm) {
        frm.add_custom_button(__("Refresh Analytics"), () => {
            frappe.show_progress(__("Calculating"), 30, 100);
            frappe.call({
                method: "ecclesia.ecclesia.doctype.employee_performance_record.employee_performance_record.refresh_analytics",
                args: { docname: frm.doc.name },
                callback(r) {
                    frappe.hide_progress();
                    if (r.message) {
                        frm.reload_doc();
                        frappe.show_alert({
                            message: __("Analytics updated — Composite: {0}%  |  {1}",
                                [r.message.composite_score, r.message.performance_band]),
                            indicator: "green"
                        });
                    }
                }
            });
        }, __("Tools"));

        if (frm.doc.status === "Final" && frappe.user.has_role("HR Manager")) {
            frm.add_custom_button(__("Release to Employee"), () => {
                frappe.confirm(__("Release this record to the employee? They will be notified by email."), () => {
                    frappe.call({
                        method: "release_to_employee", doc: frm.doc,
                        callback() {
                            frappe.show_alert({ message: __("Record released"), indicator: "green" });
                            frm.reload_doc();
                        }
                    });
                });
            }, __("Actions")).css("background", "#059669").css("color", "#fff");
        }
    }
});