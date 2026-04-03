frappe.pages["audit-dashboard"].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "🛡️ Audit Risk Dashboard",
        single_column: true
    });

    // Store the load_dashboard function in a variable that can be accessed by the refresh button
    var self = this;
    
    // Define load_dashboard function first so it's available
    function load_dashboard() {
        frappe.call({
            method: "ecclesia.api.audit_dashboard.get_dashboard_data",
            callback: function (r) {
                if (r.message) {
                    render_dashboard(r.message);
                } else {
                    show_error("No data received from server");
                }
            },
            error: function (err) {
                console.error("Dashboard load error:", err);
                show_error("Failed to load dashboard data");
            }
        });
    }

    function show_error(message) {
        const root = $("#audit-dashboard-root");
        root.html(`
            <div style="text-align:center; padding:40px; color:#c0392b;">
                <i class="fa fa-exclamation-circle fa-3x"></i>
                <p style="margin-top:16px;">${message}</p>
                <button class="btn btn-primary" onclick="location.reload()">Retry</button>
            </div>
        `);
    }

    // Now set the refresh button handler (this is the fix!)
    page.set_secondary_action("Refresh", function() {
        load_dashboard();
    }, "octicon octicon-sync");

    // Show loading state
    page.main.html(`
        <div id="audit-dashboard-root" style="padding:20px;">
            <div style="text-align:center; padding:40px; color:#888;">
                <i class="fa fa-spinner fa-spin fa-2x"></i>
                <p>Loading dashboard...</p>
            </div>
        </div>
    `);

    // Load the dashboard
    load_dashboard();

    // All rendering functions remain the same
    function render_dashboard(data) {
        const root = $("#audit-dashboard-root");
        root.html("");

        // ── KPI Cards ────────────────────────────────────────────────────────
        const kpis = data.kpis || {};
        const fmt_money = (val) => (val || 0).toLocaleString("en-NG", {minimumFractionDigits:2, maximumFractionDigits:2});

        root.append(`
            <div style="display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:24px;">
                ${kpi_card("Critical Open", kpis.open_critical || 0, "#c0392b", "fa-exclamation-circle",
                    "Critical findings requiring immediate action")}
                ${kpi_card("High Open", kpis.open_high || 0, "#e67e22", "fa-exclamation-triangle",
                    "High risk findings open")}
                ${kpi_card("Open CAPs", kpis.open_caps || 0, "#2980b9", "fa-tasks",
                    "Corrective action plans in progress")}
                ${kpi_card("Overdue CAPs", kpis.overdue_caps || 0, "#8e44ad", "fa-clock-o",
                    "CAPs past due date")}
            </div>
            <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin-bottom:24px;">
                ${kpi_card("Financial Impact", "₦" + fmt_money(kpis.total_financial_impact), "#c0392b", "fa-money",
                    "Total open findings financial exposure")}
                ${kpi_card("Registered DocTypes", kpis.total_registered || 0, "#27ae60", "fa-database",
                    "DocTypes in audit universe")}
                ${kpi_card("Active Engagements", kpis.active_engagements || 0, "#16a085", "fa-shield",
                    "Engagements currently in progress")}
            </div>
        `);

        // ── Two-column layout ────────────────────────────────────────────────
        const grid = $(`<div style="display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:24px;"></div>`);
        root.append(grid);

        // Findings trend chart (left)
        const trend_card = card("📈 Findings Trend — Last 12 Months");
        grid.append(trend_card);
        render_trend_chart(trend_card.find(".card-body"), data.findings_trend || []);

        // Financial Statement Exposure (right)
        const fs_card = card("💰 Financial Statement Exposure (Open Findings)");
        grid.append(fs_card);
        render_fs_table(fs_card.find(".card-body"), data.fs_exposure || []);

        // ── Second row ───────────────────────────────────────────────────────
        const grid2 = $(`<div style="display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:24px;"></div>`);
        root.append(grid2);

        // CAP Status
        const cap_card = card("📋 CAP Status Breakdown");
        grid2.append(cap_card);
        render_cap_status(cap_card.find(".card-body"), data.cap_status || []);

        // GL Summary
        const gl_card = card("🔍 GL Monitoring Summary");
        grid2.append(gl_card);
        render_gl_summary(gl_card.find(".card-body"), data.gl_summary || {});

        // ── Full width ───────────────────────────────────────────────────────
        const risk_card = card("🔥 Top 10 Open Risk Items");
        root.append(risk_card);
        render_top_risks(risk_card.find(".card-body"), data.top_risks || []);

        const universe_card = card("🌐 Audit Universe Coverage");
        root.append(universe_card);
        render_universe(universe_card.find(".card-body"), data.universe_stats || {});
    }

    function kpi_card(label, value, color, icon, subtitle) {
        return `
            <div style="background:#fff; border-radius:8px; padding:20px;
                        box-shadow:0 2px 8px rgba(0,0,0,0.08);
                        border-top:4px solid ${color};">
                <div style="display:flex; align-items:center; margin-bottom:8px;">
                    <i class="fa ${icon}" style="color:${color}; font-size:20px; margin-right:10px;"></i>
                    <span style="color:#666; font-size:12px; text-transform:uppercase;">${label}</span>
                </div>
                <div style="font-size:32px; font-weight:700; color:${color};">${value}</div>
                <div style="font-size:11px; color:#999; margin-top:4px;">${subtitle}</div>
            </div>`;
    }

    function card(title) {
        return $(`
            <div style="background:#fff; border-radius:8px; padding:20px;
                        box-shadow:0 2px 8px rgba(0,0,0,0.08);">
                <h5 style="margin:0 0 16px 0; font-size:14px; font-weight:600;
                           padding-bottom:8px; border-bottom:2px solid #ecf0f1;">${title}</h5>
                <div class="card-body"></div>
            </div>
        `);
    }

    function render_trend_chart(container, trend_data) {
        if (!trend_data || !trend_data.length) {
            container.html("<p style='color:#888; text-align:center; padding:20px;'>No trend data available.</p>");
            return;
        }

        // Group by month
        const months = [...new Set(trend_data.map(d => d.month))].sort();
        const risk_levels = ["Critical", "High", "Medium", "Low"];
        const colors = { Critical: "#c0392b", High: "#e67e22", Medium: "#f1c40f", Low: "#27ae60" };

        const grouped = {};
        months.forEach(m => { grouped[m] = { Critical: 0, High: 0, Medium: 0, Low: 0 }; });
        trend_data.forEach(d => {
            if (grouped[d.month]) grouped[d.month][d.risk_rating] = (grouped[d.month][d.risk_rating] || 0) + (d.count || 1);
        });

        // Simple bar chart using divs
        const max_total = Math.max(...months.map(m =>
            Object.values(grouped[m]).reduce((a, b) => a + b, 0)
        ));

        let html = `<div style="display:flex; align-items:flex-end; gap:6px; height:140px; overflow-x:auto;">`;
        months.slice(-12).forEach(month => {
            const totals = grouped[month];
            const total = Object.values(totals).reduce((a, b) => a + b, 0);
            const bar_height = max_total > 0 ? (total / max_total * 120) : 0;
            html += `
                <div style="display:flex; flex-direction:column; align-items:center; flex:1; min-width:30px;">
                    <div style="display:flex; flex-direction:column-reverse; height:${bar_height}px; width:100%; background:#ecf0f1; border-radius:3px; overflow:hidden;">
                        ${risk_levels.filter(r => totals[r] > 0).map(r =>
                            `<div style="background:${colors[r]}; height:${(totals[r]/total*100)}%; width:100%;" title="${r}: ${totals[r]}"></div>`
                        ).join("")}
                    </div>
                    <div style="font-size:9px; color:#666; margin-top:4px; transform:rotate(-45deg); 
                                transform-origin:top left; white-space:nowrap;">${month.slice(5)}</div>
                </div>`;
        });
        html += `</div>`;

        // Legend
        html += `<div style="display:flex; gap:12px; margin-top:12px; flex-wrap:wrap;">`;
        risk_levels.forEach(r => {
            html += `<span><span style="background:${colors[r]}; display:inline-block; 
                     width:12px; height:12px; border-radius:2px; margin-right:4px;"></span>
                     <span style="font-size:12px;">${r}</span></span>`;
        });
        html += `</div>`;
        container.html(html);
    }

    function render_fs_table(container, fs_data) {
        if (!fs_data || !fs_data.length) {
            container.html("<p style='color:#888; text-align:center; padding:20px;'>No financial impact findings.</p>");
            return;
        }

        const total = fs_data.reduce((s, d) => s + flt(d.total_impact), 0);
        let rows = fs_data.map(d => {
            const pct = total > 0 ? ((d.total_impact / total) * 100).toFixed(1) : 0;
            return `
                <tr style="border-bottom:1px solid #ecf0f1;">
                    <td style="padding:8px; font-size:12px;">${d.fs_line || '—'}</td>
                    <td style="padding:8px; text-align:center;">${d.findings_count || 0}</td>
                    <td style="padding:8px; text-align:right; font-weight:600; color:#c0392b;">
                        ${(flt(d.total_impact)).toLocaleString("en-NG", {minimumFractionDigits:2, maximumFractionDigits:2})}
                    </td>
                    <td style="padding:8px; width:80px;">
                        <div style="background:#e74c3c; height:6px; border-radius:3px; width:${Math.min(pct,100)}%;"></div>
                    </td>
                </tr>`;
        }).join("");

        container.html(`
            <table style="width:100%; border-collapse:collapse; font-size:12px;">
                <thead><tr style="background:#2c3e50; color:#fff;">
                    <th style="padding:8px; text-align:left;">FS Line</th>
                    <th style="padding:8px; text-align:center;">Findings</th>
                    <th style="padding:8px; text-align:right;">Impact (₦)</th>
                    <th style="padding:8px; text-align:left;">Exposure</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
        `);
    }

    function render_cap_status(container, cap_data) {
        if (!cap_data || !cap_data.length) {
            container.html("<p style='color:#888; text-align:center; padding:20px;'>No CAPs found.</p>");
            return;
        }

        const colors = {
            "Open": "#3498db", "In Progress": "#f39c12",
            "Completed": "#27ae60", "Overdue": "#c0392b", "Accepted Risk": "#95a5a6"
        };

        let html = "";
        cap_data.forEach(d => {
            const color = colors[d.status] || "#95a5a6";
            html += `
                <div style="display:flex; align-items:center; margin-bottom:12px;">
                    <div style="width:12px; height:12px; border-radius:50%; 
                                background:${color}; margin-right:10px; flex-shrink:0;"></div>
                    <div style="flex:1; font-size:13px;">${d.status}</div>
                    <div style="font-weight:700; font-size:18px; color:${color};">${d.count || 0}</div>
                    ${d.critical_count > 0 ? `<div style="margin-left:8px; font-size:11px; color:#c0392b;">(${d.critical_count} Critical)</div>` : ""}
                </div>`;
        });
        container.html(html);
    }

    function render_gl_summary(container, gl) {
        gl = gl || {};
        container.html(`
            <div style="display:grid; gap:12px;">
                <div style="background:#ffeaea; border-radius:6px; padding:15px; display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:13px; font-weight:500;">Total GL Exceptions</span>
                    <b style="color:#c0392b; font-size:24px;">${gl.total_gl_findings || 0}</b>
                </div>
                <div style="background:#fff8e1; border-radius:6px; padding:15px; display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:13px; font-weight:500;">GL Cancellations</span>
                    <b style="color:#e67e22; font-size:24px;">${gl.cancellations || 0}</b>
                </div>
                <div style="background:#fce4ec; border-radius:6px; padding:15px; display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:13px; font-weight:500;">SOD Failures</span>
                    <b style="color:#8e44ad; font-size:24px;">${gl.sod_failures || 0}</b>
                </div>
                <div style="text-align:center; margin-top:8px;">
                    <a href="/app/audit-finding?finding_type=GL Entry Cancellation" 
                       style="font-size:12px; color:#3498db; text-decoration:none;">View all GL findings →</a>
                </div>
            </div>
        `);
    }

    function render_top_risks(container, findings) {
        if (!findings || !findings.length) {
            container.html("<p style='color:#888; text-align:center; padding:20px;'>No open high-risk findings.</p>");
            return;
        }

        const risk_colors = { Critical: "#c0392b", High: "#e67e22", Medium: "#f1c40f", Low: "#27ae60" };
        let rows = findings.map((f, i) => {
            const isOverdue = f.due_date && f.due_date < frappe.datetime.get_today();
            return `
                <tr style="background:${i%2===0?'#fff':'#f8f9fa'};">
                    <td style="padding:10px;">
                        <span style="background:${risk_colors[f.risk_rating] || '#95a5a6'}; color:#fff;
                                     padding:3px 8px; border-radius:3px; font-size:11px; font-weight:500;">${f.risk_rating || 'N/A'}</span>
                    </td>
                    <td style="padding:10px;">
                        <a href="/app/audit-finding/${f.name}" style="font-weight:600; font-size:13px; color:#2c3e50; text-decoration:none;">${f.finding_title || 'Untitled'}</a><br>
                        <small style="color:#7f8c8d;">${f.reference_doctype || ''} | Code: ${f.transaction_code || '—'}</small>
                    </td>
                    <td style="padding:10px; font-size:12px; color:#7f8c8d;">${f.financial_statement_line || '—'}</td>
                    <td style="padding:10px; text-align:right; font-weight:600; color:#c0392b;">
                        ${f.financial_impact ? '₦' + (flt(f.financial_impact)).toLocaleString("en-NG", {minimumFractionDigits:2, maximumFractionDigits:2}) : '—'}
                    </td>
                    <td style="padding:10px; font-size:12px; color:${isOverdue ? '#c0392b' : '#7f8c8d'};">
                        ${f.due_date || 'Not set'}
                        ${isOverdue ? '<span style="margin-left:4px;">⚠️</span>' : ''}
                    </td>
                </tr>
            `;
        }).join("");

        container.html(`
            <div style="overflow-x:auto;">
                <table style="width:100%; border-collapse:collapse;">
                    <thead>
                        <tr style="background:#2c3e50; color:#fff;">
                            <th style="padding:10px; text-align:left;">Risk</th>
                            <th style="padding:10px; text-align:left;">Finding</th>
                            <th style="padding:10px; text-align:left;">FS Line</th>
                            <th style="padding:10px; text-align:right;">Impact</th>
                            <th style="padding:10px; text-align:left;">Due Date</th>
                        </tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
        `);
    }

    function render_universe(container, u) {
        u = u || {};
        const pct = u.coverage_pct || 0;
        container.html(`
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:16px; align-items:center;">
                <div style="text-align:center;">
                    <div style="font-size:36px; font-weight:700; color:#2980b9;">${u.total || 0}</div>
                    <div style="font-size:12px; color:#7f8c8d;">Registered DocTypes</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:36px; font-weight:700; color:#27ae60;">${u.audited_this_year || 0}</div>
                    <div style="font-size:12px; color:#7f8c8d;">Audited This Year</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:36px; font-weight:700; color:#e74c3c;">${u.never_audited || 0}</div>
                    <div style="font-size:12px; color:#7f8c8d;">Never Audited</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:36px; font-weight:700; color:#2c3e50;">${pct}%</div>
                    <div style="font-size:12px; color:#7f8c8d;">Coverage YTD</div>
                    <div style="background:#ecf0f1; border-radius:10px; height:8px; margin-top:8px; width:100%;">
                        <div style="background:#27ae60; width:${pct}%; height:8px; border-radius:10px;"></div>
                    </div>
                </div>
            </div>
            <div style="margin-top:16px; text-align:center;">
                <a href="/app/auditable-doctype-registry" style="font-size:12px; color:#3498db; text-decoration:none; margin:0 8px;">View full Audit Universe →</a>
                <span style="color:#bdc3c7;">|</span>
                <a href="/app/audit-finding" style="font-size:12px; color:#3498db; text-decoration:none; margin:0 8px;">All Findings →</a>
                <span style="color:#bdc3c7;">|</span>
                <a href="/app/corrective-action-plan" style="font-size:12px; color:#3498db; text-decoration:none; margin:0 8px;">All CAPs →</a>
            </div>
        `);
    }

    function flt(v) { 
        if (v === null || v === undefined) return 0;
        return parseFloat(v) || 0; 
    }
};