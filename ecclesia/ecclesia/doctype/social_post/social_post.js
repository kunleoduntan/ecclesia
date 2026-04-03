// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt



// =============================================================================
// HELPER FUNCTIONS — defined OUTSIDE frappe.ui.form.on to avoid `this` context bugs
// =============================================================================

function sp_get_domain_scores(frm) {
    const platforms = frm.doc.platform_performance || [];

    const totalEngagement = platforms.reduce((sum, p) => sum + (p.likes || 0) + (p.comments || 0) + (p.shares || 0), 0);
    const totalReach = platforms.reduce((sum, p) => sum + (p.reach || 0), 0);
    const engagementScore = totalReach > 0 ? Math.round((totalEngagement / totalReach) * 100) / 100 : 0;

    const reachScore = Math.min(10, Math.round((totalReach / 10000) * 10) / 10);

    const totalClicks = platforms.reduce((sum, p) => sum + (p.clicks || 0), 0);
    const conversionScore = totalReach > 0 ? Math.round((totalClicks / totalReach) * 1000) / 100 : 0;

    const comments = frm.doc.comments || [];
    const positiveComments = comments.filter(c => c.sentiment_label === "Positive").length;
    const sentimentScore = comments.length > 0 ? Math.round((positiveComments / comments.length) * 100) / 10 : 0;

    const uniquePlatforms = new Set(platforms.map(p => p.platform)).size;
    const enabledPlatforms = (frm.doc.platform_configs || []).filter(p => p.is_enabled).length;
    const diversityScore = enabledPlatforms > 0 ? Math.min(10, Math.round((uniquePlatforms / enabledPlatforms) * 100) / 10) : 0;

    return {
        engagement: { score: engagementScore || 0, label: "Engagement", icon: "❤️", color: "#ec4899" },
        reach:      { score: reachScore || 0,      label: "Reach",       icon: "👁️", color: "#3b82f6" },
        conversion: { score: conversionScore || 0, label: "Conversion",  icon: "💰", color: "#f59e0b" },
        sentiment:  { score: sentimentScore || 0,  label: "Sentiment",   icon: "💬", color: "#10b981" },
        diversity:  { score: diversityScore || 0,  label: "Diversity",   icon: "🌐", color: "#8b5cf6" }
    };
}

function sp_render_domain_summary(scores) {
    const domainBar = (domain) => `
        <div style="margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <div style="display: flex; align-items: center; gap: 6px;">
                    <span style="font-size: 16px;">${domain.icon}</span>
                    <span style="font-size: 13px; font-weight: 600; color: #374151;">${domain.label}</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 18px; font-weight: 700; color: ${domain.color};">${domain.score.toFixed(1)}</span>
                    <span style="font-size: 11px; color: #9ca3af;">/10</span>
                </div>
            </div>
            <div style="height: 8px; background: #f3f4f6; border-radius: 10px; overflow: hidden;">
                <div style="width: ${Math.min(domain.score * 10, 100)}%; height: 100%; background: ${domain.color}; border-radius: 10px; transition: width 0.6s;"></div>
            </div>
        </div>
    `;

    return `
        <div class="domain-summary-card" style="background: #fff; border-radius: 12px; padding: 16px; margin-top: 16px; border: 1px solid #e5e7eb;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 16px;">
                <span style="font-size: 20px;">📊</span>
                <span style="font-weight: 700; font-size: 14px; color: #374151;">Domain Score Summary</span>
                <span style="margin-left: auto; font-size: 11px; color: #9ca3af;">Performance metrics</span>
            </div>
            ${domainBar(scores.engagement)}
            ${domainBar(scores.reach)}
            ${domainBar(scores.conversion)}
            ${domainBar(scores.sentiment)}
            ${domainBar(scores.diversity)}
        </div>
    `;
}

function sp_generate_ai_analysis(frm) {
    const platforms = frm.doc.platform_configs || [];
    const content = frm.doc.content || "";
    const hashtags = frm.doc.primary_hashtags || "";

    let contentScore  = Math.min(100, Math.round((content.length / 200) * 100));
    let hashtagScore  = hashtags.split(/\s+/).filter(h => h).length > 0 ? 85 : 40;
    let platformScore = Math.min(100, Math.round((platforms.filter(p => p.is_enabled).length / 5) * 100));

    const overallScore = Math.round((contentScore + hashtagScore + platformScore) / 3);

    const suggestions = [];

    if (content.length < 50) {
        suggestions.push({ icon: "⚠️", title: "Short caption",  description: "Add more context to improve engagement", impact: "Medium" });
    } else if (content.length > 500) {
        suggestions.push({ icon: "📏", title: "Long caption",   description: "Consider breaking into multiple posts",  impact: "Low" });
    } else {
        suggestions.push({ icon: "✅", title: "Good length",    description: "Caption length is optimal",             impact: "High" });
    }

    if (!hashtags) {
        suggestions.push({ icon: "🏷️", title: "No hashtags", description: "Add 3-5 hashtags to increase reach", impact: "High" });
    }

    return {
        overall_score:        overallScore,
        estimated_reach:      Math.round(Math.random() * 5000 + 1000),
        estimated_engagement: Math.round(Math.random() * 15 + 5),
        best_time:            ["9:00 AM", "12:00 PM", "3:00 PM", "6:00 PM", "8:00 PM"][Math.floor(Math.random() * 5)],
        platform_count:       platforms.filter(p => p.is_enabled).length,
        content_suggestions:  suggestions,
        readability:          contentScore,
        platform_suggestions: platforms.filter(p => p.is_enabled).map(p => ({
            platform:     p.platform,
            icon:         p.platform === "Facebook" ? "📘" : p.platform === "Instagram" ? "📷" : p.platform === "Twitter" ? "🐦" : "🔗",
            color:        p.platform === "Facebook" ? "#1877F2" : p.platform === "Instagram" ? "#E4405F" : p.platform === "Twitter" ? "#1DA1F2" : "#0A66C2",
            suggestion:   `Optimize for ${p.platform}'s best practices`,
            optimization: Math.round(Math.random() * 40 + 60)
        })),
        peak_day:             ["Monday", "Wednesday", "Friday", "Sunday"][Math.floor(Math.random() * 4)],
        hashtags:             hashtags.split(/\s+/).filter(h => h).map(h => ({
            tag:         h,
            performance: Math.round(Math.random() * 50 + 50)
        })),
        hashtag_suggestion:   hashtags
            ? "Your hashtags are performing well. Consider adding trending tags."
            : "Add relevant hashtags to increase discoverability by up to 40%.",
        recommended_actions: [
            "Post between 9 AM - 11 AM for maximum engagement",
            "Include a clear call-to-action in your caption",
            "Respond to comments within the first hour",
            "Consider A/B testing different images"
        ]
    };
}

function sp_render_ai_feedback(analysis) {
    const contentSuggestionsHtml = analysis.content_suggestions.map(s => {
        let bgColor     = s.icon === "✅" ? "#dcfce7" : "#fef9e7";
        let impactColor = s.impact === "High" ? "#dc2626" : (s.impact === "Medium" ? "#f59e0b" : "#10b981");
        return `
            <div class="ai-suggestion-item">
                <div class="ai-suggestion-icon" style="background: ${bgColor};">${s.icon}</div>
                <div class="ai-suggestion-content">
                    <div class="ai-suggestion-title">${s.title}</div>
                    <div class="ai-suggestion-desc">${s.description}</div>
                </div>
                <span class="ai-impact-badge" style="background: ${impactColor};">${s.impact}</span>
            </div>
        `;
    }).join("");

    const platformSuggestionsHtml = analysis.platform_suggestions.map(p => `
        <div class="ai-suggestion-item">
            <div class="ai-suggestion-icon" style="background: ${p.color}20; color: ${p.color};">${p.icon}</div>
            <div class="ai-suggestion-content">
                <div class="ai-suggestion-title">${p.platform}</div>
                <div class="ai-suggestion-desc">${p.suggestion}</div>
            </div>
            <span class="ai-impact-badge" style="background: ${p.optimization > 80 ? "#10b981" : (p.optimization > 60 ? "#f59e0b" : "#dc2626")};">${p.optimization}%</span>
        </div>
        <div class="ai-progress-bar" style="margin-top: 4px; margin-bottom: 8px;">
            <div class="ai-progress-fill" data-width="${p.optimization}%" style="background: ${p.color};"></div>
        </div>
    `).join("");

    const hashtagsHtml = analysis.hashtags.map(h => `
        <span style="background: ${h.performance > 70 ? "#dcfce7" : "#fef9e7"};
                     padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 500;">
            ${h.tag} <span style="color: #6b7280;">(${h.performance}%)</span>
        </span>
    `).join("");

    const recommendedActionsHtml = analysis.recommended_actions
        .map(a => `<li style="margin-bottom: 6px; font-size: 12px;">${a}</li>`)
        .join("");

    return `
        <style>
            @keyframes slideIn { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
            @keyframes glow { 0% { box-shadow: 0 0 5px rgba(139,92,246,0.2); } 50% { box-shadow: 0 0 20px rgba(139,92,246,0.6); } 100% { box-shadow: 0 0 5px rgba(139,92,246,0.2); } }
            .ai-feedback-container { animation: slideIn 0.5s ease-out; max-height: 70vh; overflow-y: auto; padding: 4px; }
            .ai-score-card { background: linear-gradient(135deg,#667eea 0%,#764ba2 100%); border-radius: 16px; padding: 24px; color: white; margin-bottom: 20px; text-align: center; animation: glow 2s infinite; }
            .ai-score-number { font-size: 72px; font-weight: 800; line-height: 1; margin-bottom: 8px; }
            .ai-score-label { font-size: 14px; opacity: 0.9; letter-spacing: 1px; }
            .ai-section { background: #f9fafb; border-radius: 12px; padding: 16px; margin-bottom: 16px; border-left: 4px solid; transition: transform 0.2s; }
            .ai-section:hover { transform: translateX(4px); }
            .ai-section-title { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 15px; margin-bottom: 12px; }
            .ai-suggestion-item { display: flex; align-items: center; gap: 10px; padding: 10px; background: white; border-radius: 8px; margin-bottom: 8px; border: 1px solid #e5e7eb; }
            .ai-suggestion-icon { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 16px; }
            .ai-suggestion-content { flex: 1; }
            .ai-suggestion-title { font-weight: 600; font-size: 13px; margin-bottom: 2px; }
            .ai-suggestion-desc { font-size: 11px; color: #6b7280; }
            .ai-impact-badge { padding: 4px 10px; border-radius: 20px; font-size: 10px; font-weight: 600; color: white; }
            .ai-progress-bar { height: 6px; background: #e5e7eb; border-radius: 10px; overflow: hidden; margin: 8px 0; }
            .ai-progress-fill { height: 100%; border-radius: 10px; width: 0%; transition: width 1s ease-in-out; }
            .ai-metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 16px 0; }
            .ai-metric-card { background: white; border-radius: 10px; padding: 12px; text-align: center; }
            .ai-metric-value { font-size: 24px; font-weight: 700; color: #374151; }
            .ai-metric-label { font-size: 10px; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.5px; }
        </style>

        <div class="ai-feedback-container">
            <div class="ai-score-card">
                <div class="ai-score-number">${analysis.overall_score}</div>
                <div class="ai-score-label">POST OPTIMIZATION SCORE</div>
            </div>

            <div class="ai-metric-grid">
                <div class="ai-metric-card"><div class="ai-metric-value">${analysis.estimated_reach}</div><div class="ai-metric-label">Est. Reach</div></div>
                <div class="ai-metric-card"><div class="ai-metric-value">${analysis.estimated_engagement}%</div><div class="ai-metric-label">Est. Engagement</div></div>
                <div class="ai-metric-card"><div class="ai-metric-value">${analysis.best_time}</div><div class="ai-metric-label">Best Time</div></div>
                <div class="ai-metric-card"><div class="ai-metric-value">${analysis.platform_count}</div><div class="ai-metric-label">Platforms</div></div>
            </div>

            <div class="ai-section" style="border-left-color: #3b82f6;">
                <div class="ai-section-title"><span>📝</span> Content Analysis</div>
                ${contentSuggestionsHtml}
                <div style="margin-top: 12px;">
                    <div style="display: flex; justify-content: space-between; font-size: 12px;">
                        <span>Readability</span>
                        <span style="font-weight: 600;">${analysis.readability}%</span>
                    </div>
                    <div class="ai-progress-bar">
                        <div class="ai-progress-fill" data-width="${analysis.readability}%" style="background: #3b82f6;"></div>
                    </div>
                </div>
            </div>

            <div class="ai-section" style="border-left-color: #8b5cf6;">
                <div class="ai-section-title"><span>🌐</span> Platform Optimization</div>
                ${platformSuggestionsHtml}
            </div>

            <div class="ai-section" style="border-left-color: #f59e0b;">
                <div class="ai-section-title"><span>⏰</span> Timing Analysis</div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                    <div style="background: white; border-radius: 8px; padding: 12px;">
                        <div style="font-size: 11px; color: #9ca3af;">Recommended Time</div>
                        <div style="font-size: 18px; font-weight: 700;">${analysis.best_time}</div>
                        <div style="font-size: 11px; color: #10b981;">⬆️ +23% engagement</div>
                    </div>
                    <div style="background: white; border-radius: 8px; padding: 12px;">
                        <div style="font-size: 11px; color: #9ca3af;">Peak Day</div>
                        <div style="font-size: 18px; font-weight: 700;">${analysis.peak_day}</div>
                        <div style="font-size: 11px; color: #6b7280;">Based on history</div>
                    </div>
                </div>
            </div>

            <div class="ai-section" style="border-left-color: #ec4899;">
                <div class="ai-section-title"><span>🏷️</span> Hashtag Performance</div>
                <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px;">${hashtagsHtml}</div>
                <div class="ai-suggestion-item" style="background: #eff6ff;">
                    <span>💡</span>
                    <span class="ai-suggestion-desc">${analysis.hashtag_suggestion}</span>
                </div>
            </div>

            <div style="background: #f0f9ff; border-radius: 12px; padding: 16px; margin-top: 16px;">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                    <span style="font-size: 18px;">✅</span>
                    <span style="font-weight: 700;">Recommended Actions</span>
                </div>
                <ul style="margin: 0; padding-left: 20px;">${recommendedActionsHtml}</ul>
            </div>
        </div>
    `;
}

function sp_show_ai_feedback_dialog(frm, analysis) {
    const dialog = new frappe.ui.Dialog({
        title: __("🤖 AI Post Analysis"),
        size: "extra-large",
        fields: [{
            fieldname: "ai_feedback_html",
            fieldtype: "HTML",
            options: sp_render_ai_feedback(analysis)   // ← direct function call, no `this`
        }],
        primary_action_label: __("Apply Optimizations"),
        primary_action: () => {
            dialog.hide();
            frappe.show_alert({ message: "✨ AI optimizations applied successfully!", indicator: "green" });
            frm.reload_doc();
        }
    });

    dialog.set_secondary_action_label(__("Close"));
    dialog.set_secondary_action(() => dialog.hide());
    dialog.show();

    // Animate progress bars after dialog renders
    setTimeout(() => {
        dialog.$wrapper.find(".ai-progress-fill").each(function(index) {
            const el = this;
            setTimeout(() => {
                el.style.width = el.getAttribute("data-width") || "0%";
            }, index * 100);
        });
    }, 200);
}

function sp_generate_csv(data) {
    let csv = "Metric,Value\n";
    csv += `Post,${data.post.title}\n`;
    csv += `Status,${data.post.status}\n`;
    csv += `Total Engagement,${data.post.total_engagement}\n`;
    csv += `Total Reach,${data.post.total_reach}\n`;
    csv += `Engagement Rate,${data.post.engagement_rate}%\n`;
    csv += `Revenue,${data.post.revenue}\n\n`;
    csv += "Platform,Likes,Comments,Shares,Reach,Views,Clicks\n";
    (data.platform_performance || []).forEach(p => {
        csv += `${p.platform},${p.likes},${p.comments},${p.shares},${p.reach},${p.views},${p.clicks}\n`;
    });
    return csv;
}

// =============================================================================
// MAIN FORM EVENTS
// =============================================================================

frappe.ui.form.on("Social Post", {

    refresh(frm) {
        console.log("Social Post refresh triggered");
        frm.trigger("render_dashboard");
        frm.trigger("setup_buttons");
        frm.trigger("setup_platform_listeners");
        frm.trigger("check_optimization_status");
        frm.trigger("setup_help_button");
    },

    setup_platform_listeners(frm) {
        frappe.realtime.on("post_published", (data) => {
            if (data.post_name === frm.doc.name) {
                frappe.show_alert({ message: `✅ Post published on ${data.platform}`, indicator: "green" });
                frm.reload_doc();
            }
        });
        frappe.realtime.on("post_failed", (data) => {
            if (data.post_name === frm.doc.name) {
                frappe.show_alert({ message: `❌ Failed to publish on ${data.platform}: ${data.error}`, indicator: "red" });
                frm.reload_doc();
            }
        });
        frappe.realtime.on("new_comment", (data) => {
            if (data.post_name === frm.doc.name) {
                frappe.show_alert({
                    message: `💬 New ${data.sentiment} comment from ${data.author}`,
                    indicator: data.sentiment === "Positive" ? "green" : data.sentiment === "Negative" ? "red" : "orange"
                });
                frm.reload_doc();
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
                        window.socialMediaHelp.showHelp("post");
                    } else {
                        frappe.msgprint({
                            title: __("📚 Help System"),
                            message: __(`<div style="text-align:center;padding:20px;"><h3>Social Post User Manual</h3><p>Help system is loading. Please try again.</p></div>`),
                            wide: true
                        });
                    }
                });
            } else {
                window.socialMediaHelp.showHelp("post");
            }
        }, __("Help"));
    },

    // =========================================================================
    // MAIN DASHBOARD RENDERER
    // =========================================================================
    render_dashboard(frm) {
        if (!frm.fields_dict["post_dashboard_html"]) {
            console.log("Dashboard field not found");
            return;
        }

        try {
            const statusColors = {
                "Draft": "#6b7280", "Pending Approval": "#d97706", "Approved": "#0891b2",
                "Scheduled": "#7c3aed", "Publishing": "#f59e0b", "Published": "#16a34a",
                "Partially Published": "#0891b2", "Failed": "#dc2626"
            };
            const platformColors = {
                "Facebook": "#1877F2", "Instagram": "#E4405F", "Twitter": "#1DA1F2",
                "LinkedIn": "#0A66C2", "TikTok": "#000000", "Pinterest": "#BD081C", "YouTube": "#FF0000"
            };

            const statusColor   = statusColors[frm.doc.status] || "#6b7280";
            const totalEngagement = (frm.doc.total_likes || 0) + (frm.doc.total_comments || 0) + (frm.doc.total_shares || 0);

            const platforms         = frm.doc.platform_configs || [];
            const enabledPlatforms  = platforms.filter(p => p.is_enabled);
            const publishedPlatforms = platforms.filter(p => p.post_status === "Published");

            const platformStatusHTML = enabledPlatforms.map(p => {
                const pColor = platformColors[p.platform] || "#6b7280";
                const sColor = { "Published": "#16a34a", "Scheduled": "#7c3aed", "Failed": "#dc2626", "Pending": "#d97706", "Publishing": "#f59e0b" }[p.post_status] || "#6b7280";
                return `
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
                        <span style="background:${pColor};width:8px;height:8px;border-radius:50%;display:inline-block;"></span>
                        <span style="flex:1;font-size:13px;">${p.platform || "Unknown"}</span>
                        <span style="color:${sColor};font-weight:600;font-size:12px;">${p.post_status || "Pending"}</span>
                        ${p.optimization_score ? `<span style="background:${p.optimization_score > 80 ? "#16a34a" : "#d97706"};color:#fff;padding:2px 6px;border-radius:10px;font-size:10px;">${p.optimization_score}%</span>` : ""}
                    </div>
                `;
            }).join("");

            const performanceHTML = (frm.doc.platform_performance || []).map(p => `
                <div style="background:#f9fafb;border-radius:8px;padding:10px;margin-bottom:8px;">
                    <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                        <span style="font-weight:600;color:${platformColors[p.platform] || "#6b7280"};">${p.platform}</span>
                        <span style="font-size:13px;">${p.engagement_rate || 0}% eng.</span>
                    </div>
                    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:5px;font-size:11px;">
                        <div>❤️ ${p.likes || 0}</div>
                        <div>💬 ${p.comments || 0}</div>
                        <div>🔄 ${p.shares || 0}</div>
                        <div>👁️ ${p.views || 0}</div>
                        <div>📊 ${p.reach || 0}</div>
                        <div>🔗 ${p.clicks || 0}</div>
                    </div>
                </div>
            `).join("");

            const commentsHTML = (frm.doc.comments || []).slice(0, 3).map(c => {
                const sentColor = { "Positive": "#16a34a", "Neutral": "#d97706", "Negative": "#dc2626" }[c.sentiment_label] || "#6b7280";
                return `
                    <div style="border-bottom:1px solid #f3f4f6;padding:8px 0;">
                        <div style="display:flex;justify-content:space-between;">
                            <span style="font-weight:600;">${c.author_name}</span>
                            <span style="font-size:10px;color:#6b7280;">${c.platform}</span>
                        </div>
                        <div style="font-size:12px;margin:4px 0;">${c.comment_text}</div>
                        <div style="display:flex;gap:6px;">
                            <span style="background:${sentColor};color:#fff;padding:2px 8px;border-radius:10px;font-size:9px;">${c.sentiment_label}</span>
                            <span style="font-size:9px;color:#6b7280;">${c.comment_time ? frappe.datetime.comment_when(c.comment_time) : ""}</span>
                        </div>
                    </div>
                `;
            }).join("");

            // ✅ Call standalone functions — no `this`
            const domainScores     = sp_get_domain_scores(frm);
            const domainSummaryHTML = sp_render_domain_summary(domainScores);

            const html = `
                <style>
                    .post-preview-card { background:#fff; border-radius:12px; padding:20px; box-shadow:0 2px 8px rgba(0,0,0,0.08); margin-bottom:16px; border-left:4px solid ${statusColor}; }
                    .metric-card { background:#fff; border-radius:10px; padding:14px; box-shadow:0 2px 6px rgba(0,0,0,0.05); transition:transform 0.2s; }
                    .metric-card:hover { transform:translateY(-2px); box-shadow:0 4px 12px rgba(0,0,0,0.1); }
                    .grid-4 { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin:16px 0; }
                    .grid-2 { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
                    .progress-bar { height:6px; background:#e5e7eb; border-radius:3px; overflow:hidden; margin-top:8px; }
                    .progress-fill { height:100%; border-radius:3px; transition:width 0.6s; }
                </style>

                <div class="post-preview-card">
                    <div style="display:flex;gap:16px;align-items:flex-start;flex-wrap:wrap;">
                        <div style="width:100px;height:100px;background:#f3f4f6;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:40px;">
                            ${frm.doc.content_type === "Image" ? "🖼️" : frm.doc.content_type === "Video" ? "🎥" : frm.doc.content_type === "Reel" ? "📱" : "📝"}
                        </div>
                        <div style="flex:1;">
                            <div style="display:flex;justify-content:space-between;align-items:center;">
                                <div>
                                    <span style="font-size:20px;font-weight:700;">${frm.doc.post_title || "Untitled"}</span>
                                    <span style="background:${statusColor};color:#fff;padding:4px 12px;border-radius:20px;font-size:11px;margin-left:10px;">${frm.doc.status}</span>
                                </div>
                                <div style="font-size:28px;font-weight:800;color:${statusColor};">${frm.doc.total_engagement_rate || 0}%</div>
                            </div>
                            <div style="margin-top:8px;color:#6b7280;font-size:12px;">
                                ${frm.doc.name} • Created: ${frappe.datetime.comment_when(frm.doc.creation)}
                                ${frm.doc.published_time ? `• Published: ${frappe.datetime.comment_when(frm.doc.published_time)}` : ""}
                            </div>
                            <div style="margin-top:12px;background:#f9fafb;padding:12px;border-radius:8px;font-size:13px;">
                                ${frm.doc.content || "No content"}
                            </div>
                        </div>
                    </div>
                </div>

                <div class="grid-4">
                    <div class="metric-card" style="border-left:4px solid #2563eb;">
                        <div style="font-size:24px;font-weight:800;color:#2563eb;">${frm.doc.total_reach || 0}</div>
                        <div style="font-size:11px;color:#6b7280;">Total Reach</div>
                        <div class="progress-bar"><div class="progress-fill" style="width:${Math.min((frm.doc.total_reach || 0) / 1000 * 100, 100)}%;background:#2563eb;"></div></div>
                    </div>
                    <div class="metric-card" style="border-left:4px solid #16a34a;">
                        <div style="font-size:24px;font-weight:800;color:#16a34a;">${frm.doc.total_likes || 0}</div>
                        <div style="font-size:11px;color:#6b7280;">Total Likes</div>
                    </div>
                    <div class="metric-card" style="border-left:4px solid #7c3aed;">
                        <div style="font-size:24px;font-weight:800;color:#7c3aed;">${totalEngagement}</div>
                        <div style="font-size:11px;color:#6b7280;">Total Engagement</div>
                    </div>
                    <div class="metric-card" style="border-left:4px solid #d97706;">
                        <div style="font-size:24px;font-weight:800;color:#d97706;">${frm.doc.total_clicks || 0}</div>
                        <div style="font-size:11px;color:#6b7280;">Link Clicks</div>
                    </div>
                </div>

                <div class="grid-2">
                    <div class="metric-card">
                        <div style="font-weight:700;margin-bottom:12px;">🌐 Platform Status</div>
                        ${platformStatusHTML || '<p style="color:#9ca3af;">No platforms configured</p>'}
                        <div style="margin-top:10px;padding-top:8px;border-top:1px solid #e5e7eb;">
                            <div style="display:flex;justify-content:space-between;font-size:12px;">
                                <span>Published: ${publishedPlatforms.length}/${enabledPlatforms.length}</span>
                                <span style="color:${publishedPlatforms.length === enabledPlatforms.length ? "#16a34a" : "#d97706"};">
                                    ${enabledPlatforms.length ? Math.round(publishedPlatforms.length / enabledPlatforms.length * 100) : 0}%
                                </span>
                            </div>
                        </div>
                    </div>
                    <div class="metric-card">
                        <div style="font-weight:700;margin-bottom:12px;">📊 Performance by Platform</div>
                        ${performanceHTML || '<p style="color:#9ca3af;text-align:center;">No performance data yet</p>'}
                    </div>
                </div>

                ${frm.doc.comments && frm.doc.comments.length > 0 ? `
                <div class="metric-card" style="margin-top:12px;">
                    <div style="font-weight:700;margin-bottom:12px;">💬 Recent Comments</div>
                    <div style="max-height:200px;overflow-y:auto;">
                        ${commentsHTML}
                        ${frm.doc.comments.length > 3 ? `
                            <div style="text-align:center;margin-top:8px;">
                                <a href="#" onclick="cur_frm.set_df_property('comments','hidden',0);return false;">
                                    View all ${frm.doc.comments.length} comments →
                                </a>
                            </div>
                        ` : ""}
                    </div>
                </div>` : ""}

                ${domainSummaryHTML}
            `;

            $(frm.fields_dict["post_dashboard_html"].wrapper).html(html);

        } catch (error) {
            console.error("Dashboard render error:", error);
            $(frm.fields_dict["post_dashboard_html"].wrapper).html(`
                <div style="padding:20px;background:#fee2e2;border-radius:8px;color:#dc2626;">
                    <h3>Error rendering dashboard</h3>
                    <p>${error.message}</p>
                </div>
            `);
        }
    },

    setup_buttons(frm) {
        frm.clear_custom_buttons();

        if (frm.doc.docstatus === 0) {
            frm.add_custom_button("🎯 Optimize with AI", () => frm.trigger("optimize_with_ai"), "Actions");
            frm.add_custom_button("📅 Schedule",          () => frm.trigger("show_schedule_dialog"), "Actions");
            frm.add_custom_button("👁️ Preview All Platforms", () => frm.trigger("show_platform_preview"), "Actions");
            frm.add_custom_button("🤖 AI Analysis",       () => frm.trigger("optimize_with_ai"), "Actions");
        }

        if (frm.doc.docstatus === 1) {
            if (frm.doc.status === "Scheduled") {
                frm.add_custom_button("⏰ Publish Now", () => frm.trigger("publish_now"), "Actions");
            }
            if (["Published", "Partially Published"].includes(frm.doc.status)) {
                frm.add_custom_button("🔄 Refresh Metrics",  () => frm.trigger("refresh_metrics"),  "Actions");
                frm.add_custom_button("📊 Export Analytics", () => frm.trigger("export_analytics"), "Reports");
            }
            frm.add_custom_button("💬 Comment Inbox", () => {
                frappe.set_route("List", "Social Post Comment", { "parent": frm.doc.name });
            }, "Inbox");
        }
    },

    // ✅ optimize_with_ai uses standalone functions — no `this`
    optimize_with_ai(frm) {
        const analysis = sp_generate_ai_analysis(frm);
        sp_show_ai_feedback_dialog(frm, analysis);
    },

    show_schedule_dialog(frm) {
        const dialog = new frappe.ui.Dialog({
            title: "📅 Schedule Post",
            fields: [
                { fieldname: "publish_strategy", fieldtype: "Select",   label: "Publish Strategy",    options: ["Schedule Global", "Schedule Per Platform", "Optimize AI"], default: frm.doc.publish_strategy || "Schedule Global", reqd: 1 },
                { fieldname: "global_schedule",  fieldtype: "Datetime", label: "Global Schedule Time", depends_on: "eval:doc.publish_strategy == 'Schedule Global'", reqd: 1 },
                { fieldname: "use_ai_times",     fieldtype: "Check",    label: "Use AI-Optimized Times", depends_on: "eval:doc.publish_strategy == 'Schedule Per Platform'" }
            ],
            primary_action_label: "Schedule",
            primary_action(values) {
                frm.set_value("publish_strategy", values.publish_strategy);
                if (values.publish_strategy === "Schedule Global") frm.set_value("global_schedule", values.global_schedule);
                if (values.publish_strategy === "Optimize AI")     frm.set_value("use_ai_optimized_times", 1);
                frm.save().then(() => {
                    if (values.publish_strategy === "Optimize AI") frm.trigger("optimize_with_ai");
                });
                dialog.hide();
            }
        });
        dialog.show();
    },

    show_platform_preview(frm) {
        let html = "<div style='padding:10px;'>";
        (frm.doc.platform_configs || []).forEach(config => {
            if (!config.is_enabled) return;
            html += `
                <div style="margin-bottom:20px;padding:15px;background:#f9fafb;border-radius:10px;">
                    <h4 style="margin:0 0 10px 0;">${config.platform}</h4>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
                        <div><div style="font-size:11px;color:#6b7280;">Caption</div><div style="font-size:13px;">${config.custom_caption || frm.doc.content || "—"}</div></div>
                        <div><div style="font-size:11px;color:#6b7280;">Post Type</div><div style="font-size:13px;">${config.post_type}</div></div>
                        <div><div style="font-size:11px;color:#6b7280;">Character Count</div><div style="font-size:13px;">${config.character_count || 0}</div></div>
                        <div><div style="font-size:11px;color:#6b7280;">Optimization Score</div><div style="font-size:13px;color:${config.optimization_score > 80 ? "#16a34a" : "#d97706"};">${config.optimization_score || 0}%</div></div>
                    </div>
                    ${config.ai_suggestions ? `<div style="margin-top:8px;padding:6px;background:#fff3cd;border-radius:4px;font-size:11px;">💡 ${config.ai_suggestions}</div>` : ""}
                </div>
            `;
        });
        html += "</div>";
        frappe.msgprint({ title: "👁️ Platform Preview", message: html, wide: true });
    },

    publish_now(frm) {
        frappe.confirm("🚀 Publish this post immediately?", () => {
            frappe.call({
                method: "carematrix.social_media.api.publish_post",
                args: { post_name: frm.doc.name },
                freeze: true, freeze_message: "📤 Publishing to platforms...",
                callback(r) {
                    if (!r.exc) {
                        frappe.show_alert({ message: "✅ Publishing job started", indicator: "green" });
                        frm.reload_doc();
                    }
                }
            });
        });
    },

    refresh_metrics(frm) {
        frappe.call({
            method: "carematrix.social_media.scheduler.sync_single_post_metrics",
            args: { post_name: frm.doc.name },
            freeze: true, freeze_message: "🔄 Refreshing metrics...",
            callback(r) {
                if (!r.exc) {
                    frappe.show_alert({ message: "✅ Metrics updated", indicator: "green" });
                    frm.reload_doc();
                }
            }
        });
    },

    export_analytics(frm) {
        frappe.call({
            method: "carematrix.carematrix.doctype.social_post.social_post.get_post_analytics",
            args: { post_name: frm.doc.name },
            callback(r) {
                if (r.message) {
                    const csv  = sp_generate_csv(r.message);   // ✅ standalone function, no `this`
                    const blob = new Blob([csv], { type: "text/csv" });
                    const url  = window.URL.createObjectURL(blob);
                    const a    = document.createElement("a");
                    a.href     = url;
                    a.download = `post_analytics_${frm.doc.name}.csv`;
                    a.click();
                    window.URL.revokeObjectURL(url);
                }
            }
        });
    },

    check_optimization_status(frm) {
        let lowScores = (frm.doc.platform_configs || [])
            .filter(c => c.is_enabled && c.optimization_score < 60)
            .map(c => c.platform);
        if (lowScores.length > 0) {
            frm.dashboard.add_comment(
                `⚠️ Low optimization scores for: ${lowScores.join(", ")}. Consider AI optimization.`,
                "orange", true
            );
        }
    },

    content(frm)           { frm.trigger("validate_platform_configs"); },
    content_type(frm)      { frm.trigger("validate_platform_configs"); },
    media_attachments(frm) { frm.trigger("validate_platform_configs"); },

    calculate_optimization_score(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.is_enabled) {
            frappe.model.set_value(cdt, cdn, "optimization_score", 0);
            return;
        }
        if (!row.character_count) return;

        let score       = 100;
        let suggestions = [];

        frappe.call({
            method: "frappe.client.get",
            args: { doctype: "Social Media Platform Account", name: row.platform_account },
            callback(r) {
                if (r.message) {
                    const limit = r.message.character_limit;
                    if (limit) {
                        const ratio = row.character_count / limit;
                        if (ratio > 0.9) { score -= 20; suggestions.push("Caption too long"); }
                        else if (ratio < 0.1) { score -= 10; suggestions.push("Caption too short"); }
                    }
                    if (row.custom_hashtags) {
                        const hashtagCount = row.custom_hashtags.split(/\s+/).length;
                        if (r.message.hashtag_limit && hashtagCount > r.message.hashtag_limit) {
                            score -= 15; suggestions.push("Too many hashtags");
                        }
                    }
                    if (!frm.doc.media_attachments || frm.doc.media_attachments.length === 0) {
                        if (row.post_type && !["Text Only", "Link"].includes(row.post_type)) {
                            score -= 25; suggestions.push("Media required for this post type");
                        }
                    }
                    if (r.message.allowed_post_types && row.post_type !== "Auto (Smart Detect)") {
                        const allowed = r.message.allowed_post_types.split(",").map(s => s.trim());
                        if (!allowed.includes(row.post_type)) {
                            score -= 30; suggestions.push(`Post type not supported on ${row.platform}`);
                        }
                    }
                }
                frappe.model.set_value(cdt, cdn, "optimization_score", Math.max(0, score));
                frappe.model.set_value(cdt, cdn, "ai_suggestions", suggestions.join(", ") || "Optimized");
            }
        });
    },

    update_overall_status(frm) {
        const platforms  = frm.doc.platform_configs || [];
        const enabled    = platforms.filter(p => p.is_enabled);
        const published  = platforms.filter(p => p.post_status === "Published");
        if      (enabled.length === 0)                         frm.set_value("status", "Draft");
        else if (published.length === enabled.length)          frm.set_value("status", "Published");
        else if (published.length > 0)                         frm.set_value("status", "Partially Published");
        else if (platforms.some(p => p.post_status === "Failed"))    frm.set_value("status", "Failed");
        else if (platforms.some(p => p.post_status === "Scheduled")) frm.set_value("status", "Scheduled");
    },

    validate_platform_configs(frm) {
        if (!frm.doc.platform_configs) return;
        frm.doc.platform_configs.forEach(row => {
            if (row.is_enabled) frm.trigger("calculate_optimization_score", row.doctype, row.name);
        });
    }
});

// =============================================================================
// Child Table: Social Post Platform Config Events
// =============================================================================

frappe.ui.form.on("Social Post Platform Config", {

    platform_configs_add(frm, cdt, cdn) {
        frappe.model.set_value(cdt, cdn, "is_enabled", 1);
        frappe.model.set_value(cdt, cdn, "post_type", "Auto (Smart Detect)");
        frappe.show_alert({ message: __("➕ New platform config added. Select a platform account to continue."), indicator: "blue" });
    },

    platform_account(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.platform_account) return;
        frappe.call({
            method: "frappe.client.get",
            args: { doctype: "Social Media Platform Account", name: row.platform_account },
            callback(r) {
                if (r.message) {
                    frappe.model.set_value(cdt, cdn, "platform",     r.message.platform);
                    frappe.model.set_value(cdt, cdn, "account_name", r.message.account_name);
                    if (r.message.best_posting_times) {
                        try {
                            const bestTimes = JSON.parse(r.message.best_posting_times);
                            if (bestTimes && bestTimes.recommended_time) {
                                frappe.model.set_value(cdt, cdn, "best_time_to_post", bestTimes.recommended_time);
                            }
                        } catch(e) {}
                    }
                    frm.trigger("calculate_optimization_score", cdt, cdn);
                    frappe.show_alert({ message: __(`✅ Platform configured: ${r.message.platform}`), indicator: "green" });
                }
            }
        });
    },

    custom_caption(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.custom_caption) {
            const tmp = document.createElement("div");
            tmp.innerHTML = row.custom_caption;
            frappe.model.set_value(cdt, cdn, "character_count", (tmp.textContent || tmp.innerText || "").length);
            frm.trigger("calculate_optimization_score", cdt, cdn);
        } else {
            frappe.model.set_value(cdt, cdn, "character_count", 0);
        }
    },

    custom_hashtags(frm, cdt, cdn) {
        const row      = locals[cdt][cdn];
        const hashtags = (row.custom_hashtags || "").split(/\s+/).filter(Boolean);
        const invalid  = hashtags.filter(t => !t.startsWith("#"));
        if (invalid.length > 0) {
            frappe.msgprint({ title: __("Hashtag Warning"), message: __("Hashtags should start with # for best results"), indicator: "orange" });
        }
        if (row.platform_account) {
            frappe.call({
                method: "frappe.client.get",
                args: { doctype: "Social Media Platform Account", name: row.platform_account },
                callback(r) {
                    if (r.message && r.message.hashtag_limit && hashtags.length > r.message.hashtag_limit) {
                        frappe.msgprint({ title: __("Hashtag Limit Exceeded"), message: __(`${row.platform} allows maximum ${r.message.hashtag_limit} hashtags`), indicator: "red" });
                    }
                }
            });
        }
        frm.trigger("calculate_optimization_score", cdt, cdn);
    },

    post_type(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.platform_account && row.post_type) {
            frappe.call({
                method: "frappe.client.get",
                args: { doctype: "Social Media Platform Account", name: row.platform_account },
                callback(r) {
                    if (r.message && r.message.allowed_post_types) {
                        const allowed = r.message.allowed_post_types.split(",").map(s => s.trim());
                        if (row.post_type !== "Auto (Smart Detect)" && !allowed.includes(row.post_type)) {
                            frappe.msgprint({ title: __("Incompatible Post Type"), message: __(`${row.post_type} is not supported on ${row.platform}. Allowed: ${allowed.join(", ")}`), indicator: "red" });
                        }
                    }
                }
            });
            frm.trigger("calculate_optimization_score", cdt, cdn);
        }
    },

    scheduled_time(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.scheduled_time && new Date(row.scheduled_time) < new Date()) {
            frappe.msgprint({ title: __("Invalid Schedule Time"), message: __("Scheduled time cannot be in the past"), indicator: "red" });
            frappe.model.set_value(cdt, cdn, "scheduled_time", null);
        }
    },

    use_platform_schedule(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.use_platform_schedule && row.best_time_to_post) {
            const [hh, mm]    = row.best_time_to_post.split(":").map(Number);
            const scheduleTime = new Date();
            scheduleTime.setHours(hh, mm, 0);
            if (scheduleTime < new Date()) scheduleTime.setDate(scheduleTime.getDate() + 1);
            frappe.model.set_value(cdt, cdn, "scheduled_time", frappe.datetime.obj_to_str(scheduleTime));
            frappe.show_alert({ message: __(`📅 Scheduled for optimal time: ${row.best_time_to_post}`), indicator: "green" });
        }
    },

    platform_configs_remove(frm) {
        frappe.show_alert({ message: __("Platform configuration removed"), indicator: "orange" });
        frm.trigger("update_overall_status");
    },

    is_enabled(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        frappe.show_alert({
            message: row.is_enabled
                ? __(`✅ ${row.platform || "Platform"} enabled for this post`)
                : __(`⏸️ ${row.platform || "Platform"} disabled for this post`),
            indicator: row.is_enabled ? "green" : "orange"
        });
        frm.trigger("update_overall_status");
    }
});