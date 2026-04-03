// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

// =============================================================================
// HELPER FUNCTIONS — standalone to avoid `this` context issues in Frappe events
// =============================================================================

function sms_get_platform_color(platform) {
    return {
        "Facebook":  "#1877F2",
        "Instagram": "#E4405F",
        "Twitter":   "#1DA1F2",
        "LinkedIn":  "#0A66C2",
        "TikTok":    "#000000",
        "Pinterest": "#BD081C",
        "YouTube":   "#FF0000"
    }[platform] || "#6b7280";
}

function sms_get_status_color(status) {
    return {
        "Connected":     "#16a34a",
        "Disconnected":  "#6b7280",
        "Token Expired": "#dc2626",
        "Rate Limited":  "#d97706",
        "API Error":     "#dc2626"
    }[status] || "#6b7280";
}

function sms_render_sparkline(value, max, color) {
    const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
    return `
        <div style="height:4px;background:#f3f4f6;border-radius:4px;margin-top:6px;overflow:hidden;">
            <div style="width:${pct}%;height:100%;background:${color};border-radius:4px;transition:width 0.8s ease;"></div>
        </div>
    `;
}

function sms_render_kpi_cards(data) {
    const cards = [
        { label: "Total Posts",        value: data.total_posts        || 0, color: "#2563eb", icon: "📄", suffix: "" },
        { label: "Total Engagement",   value: data.total_engagement   || 0, color: "#16a34a", icon: "❤️",  suffix: "" },
        { label: "Avg. Engagement",    value: data.avg_engagement_rate|| 0, color: "#7c3aed", icon: "📈", suffix: "%" },
        { label: "Total Reach",        value: data.total_reach        || 0, color: "#0891b2", icon: "👁️", suffix: "" },
        { label: "Total Clicks",       value: data.total_clicks       || 0, color: "#d97706", icon: "🔗", suffix: "" },
        { label: "Revenue",            value: data.total_revenue      || 0, color: "#f59e0b", icon: "💰", suffix: "" }
    ];

    const maxVals = cards.map(c => c.value);

    return `
        <div class="sms-kpi-grid">
            ${cards.map((c, i) => `
                <div class="sms-kpi-card" style="border-top:3px solid ${c.color};">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                        <div>
                            <div class="sms-kpi-value" style="color:${c.color};">${Number(c.value).toLocaleString()}${c.suffix}</div>
                            <div class="sms-kpi-label">${c.label}</div>
                        </div>
                        <span style="font-size:22px;opacity:0.8;">${c.icon}</span>
                    </div>
                    ${sms_render_sparkline(c.value, Math.max(...maxVals, 1), c.color)}
                </div>
            `).join("")}
        </div>
    `;
}

function sms_render_platform_breakdown(platformBreakdown) {
    const entries = Object.entries(platformBreakdown || {});
    if (!entries.length) return '<p class="sms-empty">No platform data yet</p>';

    return entries.map(([platform, stats]) => {
        const color   = sms_get_platform_color(platform);
        const total   = (stats.likes || 0) + (stats.comments || 0) + (stats.shares || 0);
        const engRate = stats.reach > 0 ? ((total / stats.reach) * 100).toFixed(1) : "0.0";

        return `
            <div class="sms-platform-card" style="border-left:4px solid ${color};">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                    <div style="display:flex;align-items:center;gap:8px;">
                        <div style="width:10px;height:10px;border-radius:50%;background:${color};"></div>
                        <span style="font-weight:700;font-size:14px;color:${color};">${platform}</span>
                    </div>
                    <div style="display:flex;gap:6px;align-items:center;">
                        <span class="sms-badge" style="background:${color}20;color:${color};">${stats.posts || 0} posts</span>
                        <span class="sms-badge" style="background:#dcfce7;color:#16a34a;">${engRate}% eng.</span>
                    </div>
                </div>
                <div class="sms-stats-grid">
                    <div class="sms-stat-item"><span>❤️</span><span>${(stats.likes    || 0).toLocaleString()}</span><span class="sms-stat-lbl">Likes</span></div>
                    <div class="sms-stat-item"><span>💬</span><span>${(stats.comments || 0).toLocaleString()}</span><span class="sms-stat-lbl">Comments</span></div>
                    <div class="sms-stat-item"><span>🔄</span><span>${(stats.shares   || 0).toLocaleString()}</span><span class="sms-stat-lbl">Shares</span></div>
                    <div class="sms-stat-item"><span>👁️</span><span>${(stats.views    || 0).toLocaleString()}</span><span class="sms-stat-lbl">Views</span></div>
                    <div class="sms-stat-item"><span>📊</span><span>${(stats.reach    || 0).toLocaleString()}</span><span class="sms-stat-lbl">Reach</span></div>
                    <div class="sms-stat-item"><span>🔗</span><span>${(stats.clicks   || 0).toLocaleString()}</span><span class="sms-stat-lbl">Clicks</span></div>
                </div>
                ${sms_render_sparkline(stats.reach || 0, 100000, color)}
            </div>
        `;
    }).join("");
}

function sms_render_top_posts(topPosts) {
    if (!topPosts || !topPosts.length) {
        return `
            <tr>
                <td colspan="4" style="text-align:center;padding:24px;color:#9ca3af;font-size:13px;">
                    📭 No posts published yet
                </td>
            </tr>
        `;
    }

    const maxEng = Math.max(...topPosts.map(p => p.total_engagement || 0), 1);

    return topPosts.map((post, idx) => {
        const engRate = post.total_engagement_rate || 0;
        const rateColor = engRate > 5 ? "#16a34a" : engRate > 2 ? "#d97706" : "#dc2626";
        const barWidth  = Math.round(((post.total_engagement || 0) / maxEng) * 100);
        const medals    = ["🥇", "🥈", "🥉"];

        return `
            <tr class="sms-table-row">
                <td style="padding:10px 8px;">
                    <div style="display:flex;align-items:center;gap:8px;">
                        <span style="font-size:16px;">${medals[idx] || `#${idx + 1}`}</span>
                        <div>
                            <a href="/app/social-post/${post.name}" style="font-weight:600;font-size:13px;color:#111827;">
                                ${post.post_title || post.name}
                            </a>
                            <div style="height:3px;background:#e5e7eb;border-radius:3px;margin-top:4px;width:120px;overflow:hidden;">
                                <div style="width:${barWidth}%;height:100%;background:#7c3aed;border-radius:3px;"></div>
                            </div>
                        </div>
                    </div>
                </td>
                <td style="padding:10px 8px;text-align:center;font-weight:700;color:#374151;">${(post.total_engagement || 0).toLocaleString()}</td>
                <td style="padding:10px 8px;text-align:center;color:#6b7280;">${(post.total_reach || 0).toLocaleString()}</td>
                <td style="padding:10px 8px;text-align:center;">
                    <span style="background:${rateColor}20;color:${rateColor};padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;">
                        ${engRate}%
                    </span>
                </td>
            </tr>
        `;
    }).join("");
}

function sms_render_platform_accounts(accounts) {
    if (!accounts || !accounts.length) {
        return '<p class="sms-empty">No platform accounts configured</p>';
    }

    const connected    = accounts.filter(a => a.account_status === "Connected").length;
    const total        = accounts.length;
    const healthPct    = Math.round((connected / total) * 100);
    const healthColor  = healthPct === 100 ? "#16a34a" : healthPct >= 50 ? "#d97706" : "#dc2626";

    return `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid #f3f4f6;">
            <span style="font-size:12px;color:#6b7280;">Account Health</span>
            <div style="display:flex;align-items:center;gap:8px;">
                <div style="width:80px;height:6px;background:#e5e7eb;border-radius:6px;overflow:hidden;">
                    <div style="width:${healthPct}%;height:100%;background:${healthColor};border-radius:6px;transition:width 0.8s;"></div>
                </div>
                <span style="font-size:12px;font-weight:700;color:${healthColor};">${connected}/${total} connected</span>
            </div>
        </div>
        ${accounts.map(acc => {
            const sc = sms_get_status_color(acc.account_status);
            const pc = sms_get_platform_color(acc.platform);
            return `
                <div class="sms-account-row">
                    <div style="width:8px;height:8px;border-radius:50%;background:${sc};flex-shrink:0;margin-top:2px;"></div>
                    <div style="flex:1;min-width:0;">
                        <div style="display:flex;align-items:center;gap:6px;">
                            <span style="font-weight:600;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${acc.account_name}</span>
                            <span class="sms-badge" style="background:${pc}20;color:${pc};flex-shrink:0;">${acc.platform}</span>
                        </div>
                        ${acc.token_expiry_date ? `<div style="font-size:10px;color:#9ca3af;margin-top:2px;">Expires: ${frappe.datetime.obj_to_user(acc.token_expiry_date)}</div>` : ""}
                    </div>
                    <span class="sms-badge" style="background:${sc}20;color:${sc};flex-shrink:0;">${acc.account_status}</span>
                </div>
            `;
        }).join("")}
    `;
}

function sms_render_insights_summary(data) {
    // Calculate derived insights
    const ctr     = data.total_reach > 0 ? ((data.total_clicks   / data.total_reach)      * 100).toFixed(2) : "0.00";
    const engRate = data.total_reach > 0 ? ((data.total_engagement / data.total_reach)     * 100).toFixed(2) : "0.00";
    const topPlat = (() => {
        let best = null, bestVal = -1;
        for (const [p, s] of Object.entries(data.platform_breakdown || {})) {
            const v = (s.likes || 0) + (s.comments || 0) + (s.shares || 0);
            if (v > bestVal) { bestVal = v; best = p; }
        }
        return best || "—";
    })();

    const insights = [
        { icon: "🎯", label: "Click-Through Rate",    value: `${ctr}%`,      note: ctr > 2 ? "Above average" : "Needs improvement", good: ctr > 2 },
        { icon: "🔥", label: "Overall Eng. Rate",     value: `${engRate}%`,  note: engRate > 3 ? "Strong performance" : "Room to grow",  good: engRate > 3 },
        { icon: "🏆", label: "Top Platform",          value: topPlat,        note: "By total engagement",                                good: true },
        { icon: "📅", label: "Posts This Period",     value: data.total_posts || 0, note: "Across all platforms",                       good: true }
    ];

    return `
        <div class="sms-insights-grid">
            ${insights.map(ins => `
                <div class="sms-insight-card">
                    <div style="font-size:24px;margin-bottom:6px;">${ins.icon}</div>
                    <div style="font-size:20px;font-weight:800;color:#111827;">${ins.value}</div>
                    <div style="font-size:11px;font-weight:600;color:#6b7280;margin-top:2px;">${ins.label}</div>
                    <div style="font-size:10px;margin-top:4px;color:${ins.good ? "#16a34a" : "#d97706"};">
                        ${ins.good ? "✅" : "⚠️"} ${ins.note}
                    </div>
                </div>
            `).join("")}
        </div>
    `;
}

function sms_build_dashboard_html(data, accounts) {
    return `
        <style>
            .sms-dashboard { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #111827; }
            .sms-section-title { font-size: 14px; font-weight: 700; color: #374151; display: flex; align-items: center; gap: 8px; margin-bottom: 14px; }
            .sms-section-title span { font-size: 18px; }
            .sms-card { background: #fff; border-radius: 14px; padding: 18px; box-shadow: 0 1px 6px rgba(0,0,0,0.06); margin-bottom: 16px; }
            .sms-kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(155px, 1fr)); gap: 12px; margin-bottom: 20px; }
            .sms-kpi-card { background: #fff; border-radius: 12px; padding: 16px; box-shadow: 0 1px 6px rgba(0,0,0,0.06); transition: transform 0.2s, box-shadow 0.2s; }
            .sms-kpi-card:hover { transform: translateY(-2px); box-shadow: 0 4px 14px rgba(0,0,0,0.1); }
            .sms-kpi-value { font-size: 26px; font-weight: 800; line-height: 1.2; }
            .sms-kpi-label { font-size: 10px; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.6px; margin-top: 2px; }
            .sms-two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
            .sms-platform-card { background: #f9fafb; border-radius: 10px; padding: 14px; margin-bottom: 10px; transition: background 0.2s; }
            .sms-platform-card:hover { background: #f3f4f6; }
            .sms-stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
            .sms-stat-item { display: flex; flex-direction: column; gap: 1px; font-size: 12px; }
            .sms-stat-lbl { font-size: 9px; color: #9ca3af; text-transform: uppercase; }
            .sms-badge { font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 20px; }
            .sms-table-row:hover td { background: #f9fafb; }
            .sms-table-row td { border-bottom: 1px solid #f3f4f6; }
            .sms-account-row { display: flex; align-items: flex-start; gap: 10px; padding: 8px 0; border-bottom: 1px solid #f9fafb; }
            .sms-account-row:last-child { border-bottom: none; }
            .sms-insights-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
            .sms-insight-card { background: #f9fafb; border-radius: 10px; padding: 14px; text-align: center; transition: transform 0.2s; }
            .sms-insight-card:hover { transform: translateY(-2px); }
            .sms-empty { color: #9ca3af; font-size: 13px; padding: 12px 0; }
            @media (max-width: 900px) {
                .sms-two-col { grid-template-columns: 1fr; }
                .sms-insights-grid { grid-template-columns: repeat(2, 1fr); }
            }
        </style>

        <div class="sms-dashboard">

            <!-- ── KPI Summary ── -->
            <div class="sms-card">
                <div class="sms-section-title"><span>📊</span> Overall Performance</div>
                ${sms_render_kpi_cards(data)}
            </div>

            <!-- ── Key Insights ── -->
            <div class="sms-card">
                <div class="sms-section-title"><span>💡</span> Key Insights</div>
                ${sms_render_insights_summary(data)}
            </div>

            <!-- ── Platform Breakdown + Top Posts ── -->
            <div class="sms-two-col">
                <div class="sms-card" style="margin-bottom:0;">
                    <div class="sms-section-title"><span>🌐</span> Platform Breakdown</div>
                    ${sms_render_platform_breakdown(data.platform_breakdown)}
                </div>

                <div class="sms-card" style="margin-bottom:0;">
                    <div class="sms-section-title"><span>🏆</span> Top Performing Posts</div>
                    <table style="width:100%;border-collapse:collapse;">
                        <thead>
                            <tr style="background:#f9fafb;">
                                <th style="padding:8px;text-align:left;font-size:11px;color:#6b7280;font-weight:600;text-transform:uppercase;">Post</th>
                                <th style="padding:8px;text-align:center;font-size:11px;color:#6b7280;font-weight:600;text-transform:uppercase;">Eng.</th>
                                <th style="padding:8px;text-align:center;font-size:11px;color:#6b7280;font-weight:600;text-transform:uppercase;">Reach</th>
                                <th style="padding:8px;text-align:center;font-size:11px;color:#6b7280;font-weight:600;text-transform:uppercase;">Rate</th>
                            </tr>
                        </thead>
                        <tbody>${sms_render_top_posts(data.top_posts)}</tbody>
                    </table>
                </div>
            </div>

            <!-- ── Platform Account Status ── -->
            <div class="sms-card" style="margin-top:16px;">
                <div class="sms-section-title"><span>🔌</span> Platform Account Status</div>
                ${sms_render_platform_accounts(accounts)}
            </div>

        </div>
    `;
}

// =============================================================================
// MAIN FORM EVENTS
// =============================================================================

frappe.ui.form.on("Social Media Settings", {

    refresh(frm) {
        frm.trigger("render_global_analytics");
        frm.trigger("setup_help_button");
    },

    // =========================================================================
    // GLOBAL ANALYTICS DASHBOARD
    // =========================================================================
    render_global_analytics(frm) {
        if (!frm.fields_dict["global_analytics_html"]) {
            console.warn("global_analytics_html field not found");
            return;
        }

        // Show loading state immediately
        $(frm.fields_dict["global_analytics_html"].wrapper).html(`
            <div style="padding:40px;text-align:center;color:#9ca3af;">
                <div style="font-size:32px;margin-bottom:10px;">⏳</div>
                <div style="font-size:13px;">Loading analytics...</div>
            </div>
        `);

        frappe.call({
            method: "carematrix.carematrix.doctype.social_media_settings.social_media_settings.get_global_analytics",
            callback(r) {
                if (!r.message) {
                    $(frm.fields_dict["global_analytics_html"].wrapper).html(`
                        <div style="padding:30px;text-align:center;color:#9ca3af;">
                            <div style="font-size:32px;margin-bottom:8px;">📭</div>
                            <div>No analytics data available yet.</div>
                        </div>
                    `);
                    return;
                }

                try {
                    const html = sms_build_dashboard_html(r.message, frm.doc.platform_accounts || []);
                    $(frm.fields_dict["global_analytics_html"].wrapper).html(html);
                } catch (err) {
                    console.error("Analytics render error:", err);
                    $(frm.fields_dict["global_analytics_html"].wrapper).html(`
                        <div style="padding:20px;background:#fee2e2;border-radius:8px;color:#dc2626;">
                            <strong>Error rendering analytics:</strong> ${err.message}
                        </div>
                    `);
                }
            }
        });
    },

    // =========================================================================
    // HELP BUTTON
    // =========================================================================
    setup_help_button(frm) {
        frm.add_custom_button(__("📚 User Manual"), () => {
            if (!window.socialMediaHelp) {
                frappe.require("/assets/carematrix/js/social_media_help.js").then(() => {
                    if (window.socialMediaHelp) {
                        window.socialMediaHelp.showHelp("settings");
                    } else {
                        frappe.msgprint({
                            title: __("📚 Help System"),
                            message: __(`
                                <div style="text-align:center;padding:20px;">
                                    <h3>Social Media Settings — User Manual</h3>
                                    <p>Help system is loading. Please try again in a moment.</p>
                                </div>
                            `),
                            wide: true
                        });
                    }
                });
            } else {
                window.socialMediaHelp.showHelp("settings");
            }
        }, __("Help"));
    },

    // =========================================================================
    // VALIDATION
    // =========================================================================
    before_save(frm) {
        if (!frm.doc.platform_accounts || frm.doc.platform_accounts.length === 0) {
            frappe.msgprint(__("Please add at least one platform account before saving."));
            frappe.validated = false;
        }
    }
});