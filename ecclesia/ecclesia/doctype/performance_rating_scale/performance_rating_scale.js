// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

// ecclesia/doctype/performance_rating_scale/performance_rating_scale.js
frappe.ui.form.on("Performance Rating Scale", {

    refresh(frm) {
        frm.trigger("_status_badge");
        frm.trigger("_render_levels_preview");
        frm.trigger("_render_analytics_dashboard");
        frm.trigger("_render_main_dashboard");
        if (!frm.is_new()) {
            frm.add_custom_button(__("Set as Default"), () => {
                frappe.db.set_value("Performance Rating Scale", frm.doc.name,
                    "is_default", 1).then(() => frm.reload_doc());
            });
        }
    },

    _status_badge(frm) {
        const colors = { Draft:"grey", Active:"green", Archived:"blue", Retired:"red" };
        frm.page.set_indicator(frm.doc.status || "Draft",
            colors[frm.doc.status] || "grey");
    },

    // ── Rating levels preview ────────────────────────────────────────
    _render_levels_preview(frm) {
        const levels = frm.doc.rating_levels || [];
        if (!levels.length) return;

        const colorMap = {
            Green:"#059669", Blue:"#2563EB",
            Orange:"#D97706", Red:"#DC2626", Grey:"#6B7280"
        };
        const sorted = [...levels]
            .filter(l => l.is_active !== 0)
            .sort((a, b) => (b.min_score || 0) - (a.min_score || 0));

        const bars = sorted.map(r => {
            const color = colorMap[r.color_indicator] || "#6B7280";
            const width = Math.min(100, (r.max_score - r.min_score) / 1);
            const barW  = r.max_score || 100;
            return `
            <div style="margin-bottom:10px">
              <div style="display:flex;align-items:center;gap:10px;margin-bottom:3px">
                <div style="background:${color};color:#fff;font-size:11px;font-weight:700;
                            padding:2px 12px;border-radius:99px;min-width:130px;
                            text-align:center">
                  ${r.rating_label || "—"}
                </div>
                <div style="font-size:11px;color:#6B7280">
                  ${r.min_score || 0}% – ${r.max_score || 0}%
                  ${r.rating_value ? " | Rating: " + r.rating_value : ""}
                </div>
                ${r.usage_count ? `
                <div style="margin-left:auto;font-size:10px;color:#9CA3AF">
                  Used ${r.usage_count}×
                </div>` : ""}
              </div>
              <div style="height:8px;background:#F3F4F6;border-radius:99px;
                          overflow:hidden;position:relative">
                <div style="position:absolute;left:${r.min_score}%;
                            width:${(r.max_score - r.min_score)}%;
                            height:100%;background:${color};
                            border-radius:99px;opacity:.85"></div>
              </div>
            </div>`;
        }).join("");

        const html = `
        <div style="font-family:var(--font-sans,Calibri)">
          <div style="font-size:10px;font-weight:700;color:#6B7280;
                      text-transform:uppercase;margin-bottom:8px;
                      letter-spacing:.4px">
            Score Range: 0% — 100%
          </div>
          ${bars}
          <div style="display:flex;gap:8px;margin-top:10px;flex-wrap:wrap">
            <div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:8px;
                        padding:8px 14px;text-align:center;flex:1">
              <div style="font-size:10px;color:#6B7280;font-weight:700">Levels</div>
              <div style="font-size:18px;font-weight:900;color:#374151">
                ${frm.doc.total_levels || sorted.length}
              </div>
            </div>
            <div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:8px;
                        padding:8px 14px;text-align:center;flex:1">
              <div style="font-size:10px;color:#6B7280;font-weight:700">Midpoint</div>
              <div style="font-size:18px;font-weight:900;color:#7C3AED">
                ${frm.doc.scale_midpoint || "—"}%
              </div>
            </div>
            <div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:8px;
                        padding:8px 14px;text-align:center;flex:1">
              <div style="font-size:10px;color:#6B7280;font-weight:700">Cycles Used</div>
              <div style="font-size:18px;font-weight:900;color:#059669">
                ${frm.doc.total_cycles_used || 0}
              </div>
            </div>
          </div>
        </div>`;

        frm.set_df_property("rating_levels", "description", html);
        frm.refresh_field("rating_levels");
    },

    // ── Analytics dashboard ──────────────────────────────────────────
    _render_analytics_dashboard(frm) {
        const d = frm.doc;
        if (!d.total_cycles_used) return;

        const biasColor = d.bias_indicator === "No Significant Bias" ? "#059669"
            : d.bias_indicator ? "#D97706" : "#6B7280";

        const html = `
        <div style="font-family:var(--font-sans,Calibri)">
          <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px">
            ${[
              ["📋","Cycles Used", d.total_cycles_used, "#2563EB"],
              ["👥","Employees Rated", d.total_employees_rated || 0, "#7C3AED"],
              ["📊","Avg Score", (d.avg_score_given || 0).toFixed(1) + "%", "#059669"],
              ["📐","Std Dev", (d.score_std_dev || 0).toFixed(1) + "%", "#D97706"],
            ].map(([icon, label, val, color]) => `
              <div style="flex:1;min-width:90px;background:#F9FAFB;
                          border:1px solid #E5E7EB;border-radius:10px;
                          padding:10px;text-align:center">
                <div style="font-size:18px">${icon}</div>
                <div style="font-size:16px;font-weight:900;color:${color};margin:2px 0">
                  ${val}
                </div>
                <div style="font-size:10px;color:#6B7280;font-weight:600">${label}</div>
              </div>`).join("")}
          </div>

          ${d.rating_distribution ? `
          <div style="background:#EDE9FE;border-radius:8px;padding:10px 14px;
                      margin-bottom:8px">
            <div style="font-size:10px;font-weight:700;color:#5B21B6;
                        text-transform:uppercase;margin-bottom:4px">
              Historical Distribution
            </div>
            <div style="font-size:12px;color:#374151">${d.rating_distribution}</div>
          </div>` : ""}

          <div style="background:${biasColor}15;border:1px solid ${biasColor}33;
                      border-radius:8px;padding:8px 14px;font-size:12px">
            <span style="color:${biasColor};font-weight:700">⚖️ ${d.bias_indicator || "—"}</span>
            <span style="color:#6B7280;margin-left:8px">
              Effectiveness: ${d.scale_effectiveness || "—"}
            </span>
            ${d.calibration_accuracy ? `
            <span style="color:#6B7280;margin-left:8px">
              | Calibration Accuracy: ${d.calibration_accuracy}%
            </span>` : ""}
          </div>
        </div>`;

        frm.set_df_property("total_cycles_used", "description", html);
        frm.refresh_field("total_cycles_used");
    },

    // ── Main dashboard ────────────────────────────────────────────────
    _render_main_dashboard(frm) {
        const d = frm.doc;
        if (!d.scale_name) return;

        const html = `
        <div style="font-family:var(--font-sans,Calibri);display:flex;
                    gap:10px;flex-wrap:wrap">
          <div style="flex:1;background:#1E2D5A;border-radius:10px;
                      padding:14px;color:#fff;min-width:160px">
            <div style="font-size:10px;color:rgba(255,255,255,.6);
                        text-transform:uppercase;font-weight:700;margin-bottom:6px">
              Scale
            </div>
            <div style="font-size:15px;font-weight:800">${d.scale_name}</div>
            <div style="font-size:11px;color:rgba(255,255,255,.7);margin-top:3px">
              ${d.status || "Draft"}
              ${d.is_default ? " ⭐ Default" : ""}
            </div>
          </div>
          <div style="flex:1;background:#F0FDF4;border:1px solid #BBF7D0;
                      border-radius:10px;padding:14px;min-width:120px;text-align:center">
            <div style="font-size:10px;color:#065F46;font-weight:700;
                        text-transform:uppercase">Score Range</div>
            <div style="font-size:16px;font-weight:900;color:#059669;margin:4px 0">
              ${d.min_overall_score || 0}%
            </div>
            <div style="font-size:10px;color:#6B7280">to</div>
            <div style="font-size:16px;font-weight:900;color:#059669">${d.max_overall_score || 0}%</div>
          </div>
          <div style="flex:1;background:#EFF6FF;border:1px solid #BFDBFE;
                      border-radius:10px;padding:14px;min-width:120px;text-align:center">
            <div style="font-size:10px;color:#1D4ED8;font-weight:700;
                        text-transform:uppercase">Effectiveness</div>
            <div style="font-size:13px;font-weight:700;color:#2563EB;margin-top:6px">
              ${d.scale_effectiveness || "Not used yet"}
            </div>
            <div style="font-size:10px;color:#6B7280;margin-top:3px">
              ${d.total_employees_rated || 0} employees rated
            </div>
          </div>
        </div>`;

        frm.set_df_property("dashboard_summary", "description", html);
        frm.refresh_field("dashboard_summary");
    }
});

// ── Child table: real-time midpoint/width calc ───────────────────────
frappe.ui.form.on("Performance Rating Level", {
    min_score(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        const mid = ((row.min_score || 0) + (row.max_score || 0)) / 2;
        const wid = (row.max_score || 0) - (row.min_score || 0);
        frappe.model.set_value(cdt, cdn, "range_midpoint", Math.round(mid * 10) / 10);
        frappe.model.set_value(cdt, cdn, "range_width",    Math.round(wid * 10) / 10);
        frm.trigger("_render_levels_preview");
    },
    max_score(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        const mid = ((row.min_score || 0) + (row.max_score || 0)) / 2;
        const wid = (row.max_score || 0) - (row.min_score || 0);
        frappe.model.set_value(cdt, cdn, "range_midpoint", Math.round(mid * 10) / 10);
        frappe.model.set_value(cdt, cdn, "range_width",    Math.round(wid * 10) / 10);
        frm.trigger("_render_levels_preview");
    },
    rating_label:      frm => frm.trigger("_render_levels_preview"),
    color_indicator:   frm => frm.trigger("_render_levels_preview"),
    is_active:         frm => frm.trigger("_render_levels_preview"),
});