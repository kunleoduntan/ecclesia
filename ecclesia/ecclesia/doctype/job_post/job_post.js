// ecclesia/doctype/job_post/job_post.js
frappe.ui.form.on("Job Post", {

    refresh(frm) {
        frm.trigger("_status_badge");
        frm.trigger("_render_summary_dashboard");
        frm.trigger("_render_target_status");
        frm.trigger("_add_action_buttons");
    },

    job_opening(frm) {
        if (!frm.doc.job_opening) return;
        // Auto-fill title and apply URL
        frappe.db.get_value("Job Opening", frm.doc.job_opening,
            ["job_title","location","description"],
            r => {
                if (!frm.doc.location_display && r.location) {
                    frm.set_value("location_display", r.location);
                }
                if (!frm.doc.base_description && r.description) {
                    frm.set_value("base_description", r.description);
                }
                const apply_url = `${window.location.origin}/apply?job=${frm.doc.job_opening}`;
                if (!frm.doc.apply_url) {
                    frm.set_value("apply_url", apply_url);
                }
            }
        );
    },

    // ── Status badge ───────────────────────────────────────────────────
    _status_badge(frm) {
        const colors = {
            Draft:"grey", Scheduled:"blue", Posting:"orange",
            Posted:"green", "Partially Posted":"blue",
            Failed:"red", Expired:"grey"
        };
        frm.page.set_indicator(frm.doc.posting_status,
            colors[frm.doc.posting_status] || "grey");
    },

    // ── Summary dashboard ──────────────────────────────────────────────
    _render_summary_dashboard(frm) {
        const d = frm.doc;
        if (!d.job_title) return;

        const priorityColors = {
            Urgent:"#DC2626", High:"#D97706", Normal:"#059669", Low:"#64748B"
        };
        const pColor = priorityColors[d.priority] || "#64748B";

        const statCard = (icon, label, val, color) =>
            `<div style="flex:1;min-width:80px;background:var(--surface-1);
                         border:1px solid var(--border);border-radius:8px;
                         padding:10px;text-align:center">
               <div style="font-size:18px">${icon}</div>
               <div style="font-size:17px;font-weight:700;color:${color}">${val}</div>
               <div style="font-size:10px;color:var(--text-secondary)">${label}</div>
             </div>`;

        const html = `
        <div style="font-family:var(--font-sans)">
          <!-- Header -->
          <div style="background:var(--bg-accent);border:1px solid var(--border-accent);
                      border-radius:10px;padding:14px 16px;margin-bottom:10px;
                      display:flex;gap:12px;align-items:center">
            <div style="font-size:28px">💼</div>
            <div style="flex:1">
              <div style="font-size:15px;font-weight:600;color:var(--text-accent)">
                ${d.job_title}
              </div>
              <div style="font-size:11px;color:var(--text-secondary);margin-top:2px">
                ${d.company || ""} · ${d.location_display || ""} ${d.work_mode ? "(" + d.work_mode + ")" : ""}
                ${d.salary_display ? " · " + d.salary_display : ""}
              </div>
            </div>
            <span style="background:${pColor}22;color:${pColor};font-size:11px;
                         font-weight:700;padding:3px 10px;border-radius:99px">
              ${d.priority || "Normal"}
            </span>
          </div>
          <!-- Stats row -->
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            ${statCard("🌐","Platforms", d.total_platforms || 0, "var(--text-primary)")}
            ${statCard("✅","Posted",    d.successfully_posted || 0, "#059669")}
            ${statCard("👁️","Views",    d.total_views || 0, "#2563EB")}
            ${statCard("❤️","Reactions",d.total_likes || 0, "#DB2777")}
            ${statCard("📋","Applications",d.total_applications || 0, "#7C3AED")}
          </div>
          ${d.apply_url ? `
          <div style="margin-top:8px;background:var(--surface-1);border:1px solid var(--border);
                      border-radius:8px;padding:8px 12px;font-size:11px;
                      display:flex;align-items:center;gap:8px">
            <span style="color:var(--text-secondary)">Apply URL:</span>
            <a href="${d.apply_url}" target="_blank"
               style="color:var(--text-accent);flex:1;overflow:hidden;
                      text-overflow:ellipsis;white-space:nowrap">${d.apply_url}</a>
            <button onclick="navigator.clipboard.writeText('${d.apply_url}').then(()=>frappe.show_alert({message:'Copied!',indicator:'green'}))"
                    style="border:none;background:none;cursor:pointer;color:var(--text-secondary);font-size:13px">⎘</button>
          </div>` : ""}
        </div>`;

        frm.set_df_property("job_title", "description", html);
        frm.refresh_field("job_title");
    },

    // ── Per-platform target status ─────────────────────────────────────
    _render_target_status(frm) {
        const targets = frm.doc.targets || [];
        if (!targets.length) return;

        const statusIcon = {
            Pending:"⏳", Scheduled:"🗓️", Posting:"⚡",
            Posted:"✅", Failed:"❌", Skipped:"⊘"
        };
        const statusColor = {
            Pending:"#D97706", Scheduled:"#2563EB", Posting:"#D97706",
            Posted:"#059669", Failed:"#DC2626", Skipped:"#9CA3AF"
        };
        const platformIcon = name => {
            const nl = (name||"").toLowerCase();
            if (nl.includes("linkedin"))  return "🔷";
            if (nl.includes("twitter")||nl.includes("/x")) return "🐦";
            if (nl.includes("facebook"))  return "📘";
            if (nl.includes("instagram")) return "📸";
            if (nl.includes("whatsapp"))  return "💬";
            if (nl.includes("telegram"))  return "✈️";
            if (nl.includes("indeed"))    return "🔍";
            if (nl.includes("glassdoor")) return "🚪";
            if (nl.includes("jobberman")) return "💼";
            return "🌐";
        };

        const cards = targets.filter(t => t.include).map(t => {
            const sc   = statusColor[t.post_status] || "#9CA3AF";
            const si   = statusIcon[t.post_status] || "⏳";
            const chars = (t.custom_message || "").length;
            const limit = t.character_limit || 0;
            const charBar = limit > 0 ? `
              <div style="height:3px;background:#e5e7eb;border-radius:99px;overflow:hidden;margin-top:4px">
                <div style="width:${Math.min(100,chars/limit*100)}%;height:100%;
                            background:${chars/limit>0.9?"#DC2626":"#059669"};border-radius:99px"></div>
              </div>
              <div style="font-size:9px;color:#9CA3AF">${chars}${limit?" / "+limit:""} chars</div>` : "";

            const engagement = t.post_status === "Posted" ? `
              <div style="font-size:10px;color:var(--text-secondary);margin-top:4px">
                👁️ ${t.views||0}  ❤️ ${t.likes||0}  🔄 ${t.shares||0}
              </div>` : "";

            const urlLink = t.post_url ? `<div style="font-size:9px;margin-top:3px">
              <a href="${t.post_url}" target="_blank" style="color:var(--text-accent)">
                View post ↗
              </a></div>` : "";

            return `
            <div style="background:var(--surface-1);border:1px solid var(--border);
                        border-radius:8px;padding:10px 12px;min-width:120px;flex:1">
              <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
                <span style="font-size:16px">${platformIcon(t.platform_name)}</span>
                <span style="font-size:11px;font-weight:600;color:var(--text-primary);flex:1">
                  ${t.platform_name || ""}
                </span>
                <span style="color:${sc};font-size:12px">${si}</span>
              </div>
              <div style="font-size:10px;font-weight:600;color:${sc}">${t.post_status||"Pending"}</div>
              ${charBar}${engagement}${urlLink}
              ${t.error_message ? `<div style="font-size:9px;color:#DC2626;margin-top:3px;word-break:break-word">${t.error_message.slice(0,80)}</div>` : ""}
            </div>`;
        }).join("");

        const html = `
        <div>
          <div style="font-size:10px;font-weight:700;color:var(--text-secondary);
                      text-transform:uppercase;letter-spacing:.4px;margin-bottom:8px">
            Platform status
          </div>
          <div style="display:flex;gap:8px;flex-wrap:wrap">${cards}</div>
        </div>`;

        frm.set_df_property("posting_status", "description", html);
        frm.refresh_field("posting_status");
    },

    // ── Action buttons ─────────────────────────────────────────────────
    _add_action_buttons(frm) {
        const d = frm.doc;

        // Add all active platforms
        if (!frm.is_new()) {
            frm.add_custom_button(__("Add All Active Platforms"), () => {
                frappe.call({
                    method: "populate_all_active_platforms",
                    doc:    frm.doc,
                    callback(r) {
                        if (r.message !== undefined) {
                            frm.reload_doc();
                            frappe.show_alert({
                                message: __(r.message > 0
                                    ? `${r.message} platform(s) added`
                                    : "All active platforms already added"),
                                indicator: r.message > 0 ? "green" : "blue"
                            });
                        }
                    }
                });
            }, __("Setup"));
        }

        // AI Optimize
        if (!frm.is_new() && d.ai_optimize) {
            frm.add_custom_button(__("✨ AI Optimize All Posts"), () => {
                frappe.confirm(
                    __("Use AI to rewrite content for each platform's style and character limit?"),
                    () => {
                        frappe.show_progress(__("AI Optimizing"), 15, 100,
                            __("Claude is crafting platform-specific posts..."));
                        frappe.call({
                            method: "ecclesia.api.job_post_api.ai_optimize_targets",
                            args: { job_post_name: frm.doc.name },
                            timeout: 90,
                            callback(r) {
                                frappe.hide_progress();
                                if (r.message) {
                                    const ok = Object.values(r.message)
                                        .filter(v => v === "optimized").length;
                                    frappe.show_alert({
                                        message: __(`AI optimized ${ok} platform(s). Review in the Targets table.`),
                                        indicator: "green"
                                    }, 6);
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                );
            }, __("AI Tools")).addClass("btn-primary");
        }

        // Post Now (submitted, not yet posted)
        if (d.docstatus === 1 && ["Scheduled","Draft","Failed","Partially Posted"].includes(d.posting_status)) {
            frm.add_custom_button(__("🚀 Post Now"), () => {
                frappe.confirm(__("Post to all included platforms immediately?"), () => {
                    frappe.call({
                        method: "ecclesia.api.job_post_api.post_now",
                        args:   { job_post_name: frm.doc.name },
                        callback(r) {
                            if (r.message?.queued) {
                                frappe.show_alert({
                                    message: __("Posting queued! Refresh in ~1 minute to see results."),
                                    indicator: "green"
                                }, 8);
                                setTimeout(() => frm.reload_doc(), 5000);
                            }
                        }
                    });
                });
            }, __("Actions")).css("background","#7C3AED").css("color","#fff");
        }

        // Sync engagement
        if (d.docstatus === 1 && d.posting_status === "Posted") {
            frm.add_custom_button(__("↻ Sync Engagement"), () => {
                frappe.show_progress(__("Syncing"), 20, 100);
                frappe.call({
                    method: "ecclesia.api.job_post_api.sync_engagement",
                    args:   { job_post_name: frm.doc.name },
                    callback(r) {
                        frappe.hide_progress();
                        frm.reload_doc();
                        frappe.show_alert({ message: __("Engagement data updated"),
                                           indicator: "green" });
                    }
                });
            }, __("Actions"));
        }

        // Copy apply URL
        if (d.apply_url) {
            frm.add_custom_button(__("Copy Apply URL"), () => {
                navigator.clipboard.writeText(d.apply_url)
                    .then(() => frappe.show_alert({ message: __("Apply URL copied!"),
                                                   indicator: "green" }));
            }, __("Actions"));
        }
    }
});

// ── Target child table: live character counter ──────────────────────────────
frappe.ui.form.on("Job Post Target", {
    custom_message(frm, cdt, cdn) {
        const row   = locals[cdt][cdn];
        const count = (row.custom_message || "").length;
        const limit = row.character_limit || 0;

        frappe.model.set_value(cdt, cdn, "character_count", count);

        if (limit > 0 && count > limit) {
            frappe.show_alert({
                message: __("{0} exceeds platform limit of {1} chars ({2} over)",
                    [row.platform_name, limit, count - limit]),
                indicator: "orange"
            }, 4);
        }
    },

    include(frm) {
        frm.trigger("_render_target_status");
    }
});
