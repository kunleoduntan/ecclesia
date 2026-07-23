// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

// ecclesia/doctype/performance_goal/performance_goal.js
frappe.ui.form.on("Performance Goal", {

    refresh(frm) {
        frm.trigger("_status_indicator");
        frm.trigger("_render_goal_header");
        frm.trigger("_render_target_dashboard");
        frm.trigger("_render_analytics_dashboard");
        frm.trigger("_add_action_buttons");
    },

    // ── Status badge ─────────────────────────────────────────────────
    _status_indicator(frm) {
        const colors = {
            Draft:"grey", "Pending Approval":"orange",
            Approved:"blue", "In Progress":"blue",
            Completed:"green", Cancelled:"red"
        };
        frm.page.set_indicator(frm.doc.status, colors[frm.doc.status] || "grey");
    },

    // ── Goal header — progress ring + health ──────────────────────────
    _render_goal_header(frm) {
        const d = frm.doc;
        const pct = Math.min(100, d.progress || 0);

        const healthColors = {
            Healthy:"#059669", "At Risk":"#D97706",
            Critical:"#DC2626", Completed:"#2563EB"
        };
        const healthColor = healthColors[d.goal_health] || "#6B7280";

        // SVG ring
        const radius = 36, circ = 2 * Math.PI * radius;
        const fill   = circ - (pct / 100 * circ);
        const ringColor = pct >= 80 ? "#059669"
            : pct >= 50 ? "#D97706" : "#DC2626";

        const ring = `
        <svg width="90" height="90" viewBox="0 0 90 90">
          <circle cx="45" cy="45" r="${radius}" fill="none"
                  stroke="#F3F4F6" stroke-width="8"/>
          <circle cx="45" cy="45" r="${radius}" fill="none"
                  stroke="${ringColor}" stroke-width="8"
                  stroke-dasharray="${circ}" stroke-dashoffset="${fill}"
                  stroke-linecap="round"
                  transform="rotate(-90 45 45)"/>
          <text x="45" y="48" text-anchor="middle"
                style="font-size:16px;font-weight:900;fill:${ringColor}">
            ${pct.toFixed(0)}%
          </text>
        </svg>`;

        const html = `
        <div style="font-family:var(--font-sans,Calibri);display:flex;
                    gap:16px;align-items:center;flex-wrap:wrap">
          <!-- Ring -->
          <div style="text-align:center">${ring}</div>

          <!-- Info -->
          <div style="flex:1;min-width:180px">
            <div style="font-size:15px;font-weight:800;color:#111;margin-bottom:4px">
              ${d.goal_title || "New Goal"}
            </div>
            <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px">
              <span style="background:#EDE9FE;color:#5B21B6;font-size:11px;
                           font-weight:600;padding:2px 10px;border-radius:99px">
                ${d.goal_type || "KPI"}
              </span>
              <span style="background:#E0F2FE;color:#0369A1;font-size:11px;
                           font-weight:600;padding:2px 10px;border-radius:99px">
                ${d.priority || "Medium"} Priority
              </span>
              <span style="background:#F0FDF4;color:#15803D;font-size:11px;
                           font-weight:600;padding:2px 10px;border-radius:99px">
                Weight: ${d.weight || 0}%
              </span>
            </div>
            <!-- Health -->
            <div style="background:${healthColor}15;border:1px solid ${healthColor}33;
                        border-radius:8px;padding:7px 12px;display:inline-flex;
                        align-items:center;gap:6px">
              <div style="width:8px;height:8px;border-radius:50%;
                          background:${healthColor}"></div>
              <span style="font-size:12px;font-weight:700;color:${healthColor}">
                ${d.goal_health || "—"}
              </span>
              ${d.days_remaining !== undefined ? `
              <span style="font-size:11px;color:#6B7280;margin-left:6px">
                ${d.days_remaining} days left
              </span>` : ""}
            </div>
          </div>

          <!-- Velocity -->
          ${d.progress_velocity ? `
          <div style="text-align:center;background:#F9FAFB;border:1px solid #E5E7EB;
                      border-radius:10px;padding:10px 16px">
            <div style="font-size:10px;color:#6B7280;font-weight:600;
                        text-transform:uppercase">Velocity</div>
            <div style="font-size:18px;font-weight:900;color:#7C3AED;margin:2px 0">
              ${d.progress_velocity.toFixed(1)}%
            </div>
            <div style="font-size:9px;color:#9CA3AF">per day</div>
            ${d.estimated_completion ? `
            <div style="font-size:10px;color:#6B7280;margin-top:4px">
              Est. done:<br><b>${d.estimated_completion}</b>
            </div>` : ""}
          </div>` : ""}
        </div>`;

        frm.set_df_property("goal_title", "description", html);
        frm.refresh_field("goal_title");
    },

    // ── Target section dashboard ──────────────────────────────────────
    _render_target_dashboard(frm) {
        const d = frm.doc;
        if (!d.kpi && !d.target_value && !d.progress) return;

        const pct = d.progress || 0;
        const barColor = pct >= 80 ? "#059669" : pct >= 50 ? "#D97706" : "#DC2626";

        const html = `
        <div style="font-family:var(--font-sans,Calibri)">
          <!-- Progress bar -->
          <div style="margin-bottom:12px">
            <div style="display:flex;justify-content:space-between;
                        font-size:12px;margin-bottom:4px">
              <span style="color:#374151;font-weight:600">
                ${d.kpi || "Progress"}
              </span>
              <span style="color:${barColor};font-weight:800">${pct.toFixed(1)}%</span>
            </div>
            <div style="height:12px;background:#F3F4F6;border-radius:99px;overflow:hidden">
              <div style="width:${Math.min(100,pct)}%;height:100%;
                          background:${barColor};border-radius:99px;transition:.5s"></div>
            </div>
            <div style="display:flex;justify-content:space-between;
                        font-size:10px;color:#9CA3AF;margin-top:3px">
              <span>0</span>
              <span>${d.target_value || "100"} ${d.measurement_unit || "%"}</span>
            </div>
          </div>

          <!-- Current achievement -->
          <div style="display:flex;gap:10px">
            <div style="flex:1;background:#F0FDF4;border:1px solid #BBF7D0;
                        border-radius:8px;padding:10px;text-align:center">
              <div style="font-size:10px;color:#065F46;font-weight:700;
                          text-transform:uppercase">Current</div>
              <div style="font-size:16px;font-weight:900;color:#059669;margin-top:2px">
                ${d.current_achievement || "—"}
              </div>
            </div>
            <div style="flex:1;background:#EFF6FF;border:1px solid #BFDBFE;
                        border-radius:8px;padding:10px;text-align:center">
              <div style="font-size:10px;color:#1D4ED8;font-weight:700;
                          text-transform:uppercase">Target</div>
              <div style="font-size:16px;font-weight:900;color:#2563EB;margin-top:2px">
                ${d.target_value || "—"} ${d.measurement_unit || ""}
              </div>
            </div>
            ${d.variance_from_target ? `
            <div style="flex:1;background:#FFF7ED;border:1px solid #FED7AA;
                        border-radius:8px;padding:10px;text-align:center">
              <div style="font-size:10px;color:#92400E;font-weight:700;
                          text-transform:uppercase">Variance</div>
              <div style="font-size:13px;font-weight:700;color:#D97706;margin-top:2px">
                ${d.variance_from_target}
              </div>
            </div>` : ""}
          </div>

          ${d.risk_factors ? `
          <div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:8px;
                      padding:8px 12px;margin-top:10px;font-size:11px;color:#DC2626">
            ⚠️ <b>Risk:</b> ${d.risk_factors}
          </div>` : ""}
        </div>`;

        frm.set_df_property("progress", "description", html);
        frm.refresh_field("progress");
    },

    // ── Analytics dashboard ──────────────────────────────────────────
    _render_analytics_dashboard(frm) {
        const d = frm.doc;
        if (!d.goal_achievement_rate && !d.dept_avg_progress) return;

        const myRate = d.goal_achievement_rate || 0;
        const deptAvg = d.dept_avg_progress || 0;
        const diff = myRate - deptAvg;
        const diffColor = diff >= 0 ? "#059669" : "#DC2626";
        const diffIcon  = diff >= 0 ? "▲" : "▼";

        const html = `
        <div style="font-family:var(--font-sans,Calibri)">
          <div style="display:flex;gap:10px;flex-wrap:wrap">
            <div style="flex:1;min-width:100px;background:#F9FAFB;border:1px solid #E5E7EB;
                        border-radius:10px;padding:12px;text-align:center">
              <div style="font-size:10px;color:#6B7280;font-weight:700;
                          text-transform:uppercase">My Achievement</div>
              <div style="font-size:22px;font-weight:900;color:#7C3AED">
                ${myRate.toFixed(1)}%
              </div>
            </div>
            <div style="flex:1;min-width:100px;background:#F9FAFB;border:1px solid #E5E7EB;
                        border-radius:10px;padding:12px;text-align:center">
              <div style="font-size:10px;color:#6B7280;font-weight:700;
                          text-transform:uppercase">Dept Avg</div>
              <div style="font-size:22px;font-weight:900;color:#0D9488">
                ${deptAvg.toFixed(1)}%
              </div>
            </div>
            <div style="flex:1;min-width:100px;background:${diffColor}10;
                        border:1px solid ${diffColor}33;border-radius:10px;
                        padding:12px;text-align:center">
              <div style="font-size:10px;color:#6B7280;font-weight:700;
                          text-transform:uppercase">vs Dept</div>
              <div style="font-size:22px;font-weight:900;color:${diffColor}">
                ${diffIcon} ${Math.abs(diff).toFixed(1)}%
              </div>
            </div>
          </div>
          ${d.progress_velocity ? `
          <div style="background:#EDE9FE;border-radius:8px;padding:8px 12px;
                      margin-top:10px;font-size:12px;color:#5B21B6">
            📈 Progress velocity: <b>${d.progress_velocity.toFixed(2)}% per day</b>
            ${d.estimated_completion ? " | Est. completion: <b>" + d.estimated_completion + "</b>" : ""}
          </div>` : ""}
        </div>`;

        frm.set_df_property("goal_achievement_rate", "description", html);
        frm.refresh_field("goal_achievement_rate");
    },

    // ── Action buttons ───────────────────────────────────────────────
    _add_action_buttons(frm) {
        const d = frm.doc;
        if (d.status === "Pending Approval" && frappe.user.has_role("Line Manager")) {
            frm.add_custom_button(__("✅ Approve"), () => {
                frappe.call({
                    method: "approve_goal", doc: d,
                    callback(r) {
                        if (r.message?.success) {
                            frappe.show_alert({ message: __("Goal approved"), indicator: "green" });
                            frm.reload_doc();
                        }
                    }
                });
            }, __("Decision")).css("background","#059669").css("color","#fff");

            frm.add_custom_button(__("Request Revision"), () => {
                frappe.prompt([
                    { fieldname:"reason", fieldtype:"Text", label:"Reason", reqd:1 }
                ], v => frappe.call({
                    method:"reject_goal", doc:d,
                    args:{ reason: v.reason },
                    callback(r){
                        if(r.message?.success){ frm.reload_doc(); }
                    }
                }));
            }, __("Decision"));
        }

        if (["In Progress","Approved"].includes(d.status)) {
            frm.add_custom_button(__("Log Progress"), () => {
                frappe.prompt([
                    { fieldname:"progress",  fieldtype:"Float", label:"New Progress (%)", reqd:1 },
                    { fieldname:"current",   fieldtype:"Data",  label:"Current Achievement" },
                    { fieldname:"notes",     fieldtype:"Small Text", label:"Notes" },
                    { fieldname:"evidence",  fieldtype:"Attach",     label:"Evidence (optional)" },
                ], vals => {
                    frappe.db.set_value("Performance Goal", d.name, {
                        progress:            vals.progress,
                        current_achievement: vals.current,
                        last_update_notes:   vals.notes,
                        evidence_upload:     vals.evidence,
                        last_update_date:    frappe.datetime.get_today(),
                    }).then(() => frm.reload_doc());
                }, __("Log Progress Update"));
            });
        }
    },

    // Trigger re-render on key field changes
    progress(frm) {
        frm.trigger("_render_goal_header");
        frm.trigger("_render_target_dashboard");
    },
    goal_health(frm) { frm.trigger("_render_goal_header"); },
    weight(frm) {
        frm.trigger("_render_goal_header");
        // Live weight total check
        if (!frm.doc.owner_employee || !frm.doc.performance_cycle) return;
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Performance Goal",
                filters: {
                    owner_employee: frm.doc.owner_employee,
                    performance_cycle: frm.doc.performance_cycle,
                    name: ["!=", frm.doc.name || "new"],
                    status: ["not in", ["Cancelled"]]
                },
                fields: ["weight"]
            },
            callback(r) {
                const used = (r.message || []).reduce((a, g) => a + (g.weight || 0), 0);
                const total = used + (frm.doc.weight || 0);
                const color = total > 100 ? "red" : total === 100 ? "green" : "blue";
                frm.set_df_property("weight", "description",
                    `<span style="color:${color};font-weight:700">
                      Total: ${Math.round(total * 10) / 10}%
                    </span> (must equal 100%)`
                );
            }
        });
    }
});