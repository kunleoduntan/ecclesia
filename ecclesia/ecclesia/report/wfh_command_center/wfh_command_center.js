// WFH Command Center — Client JS
// Ecclesia Module
// Renders a rich live dashboard on top of the standard report table.

frappe.query_reports["WFH Command Center"] = {

    filters: [
        {
            fieldname: "date",
            label: __("Date"),
            fieldtype: "Date",
            default: frappe.datetime.nowdate(),
            reqd: 1
        }
    ],

    // ── Column formatters for the Top Performers table ─────────────────────

    formatter(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "points") {
            const pts = parseFloat(data.points || 0);
            const color = pts >= 100 ? "#16a34a" : pts >= 40 ? "#d97706" : "#dc2626";
            return `<span style="color:${color};font-weight:700;">${pts}</span>`;
        }

        if (column.fieldname === "composite_score") {
            const s = parseFloat(data.composite_score || 0);
            const color = s >= 75 ? "#16a34a" : s >= 50 ? "#d97706" : "#dc2626";
            const w = Math.min(s, 100);
            return `
                <div style="display:flex;align-items:center;gap:6px;">
                    <div style="width:60px;background:#e5e7eb;border-radius:4px;height:5px;">
                        <div style="width:${w}%;height:5px;background:${color};border-radius:4px;"></div>
                    </div>
                    <span style="color:${color};font-weight:600;">${s}</span>
                </div>`;
        }

        if (column.fieldname === "hours") {
            const h = parseFloat(data.hours || 0);
            const color = h >= 6 ? "#16a34a" : h >= 4 ? "#d97706" : "#dc2626";
            return `<span style="color:${color};">${h} h</span>`;
        }

        return value;
    },

    // ── Dashboard rendering ────────────────────────────────────────────────

    onload(report) {
        report._cc_initialized = false;
        report._cc_interval    = null;

        // Inject dashboard above the table
        const $wrapper = report.page.main.find(".layout-main-section");
        report.$dashboard = $(`
            <div id="wfh-command-center" style="padding:16px 0 8px;">
                <div id="wfh-kpi-row" style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px;"></div>
                <div id="wfh-panels" style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px;"></div>
            </div>
        `).prependTo($wrapper);

        // Auto-refresh every 60 seconds
        report._cc_interval = setInterval(() => {
            report._render_dashboard();
        }, 60000);

        // Live clock in the page title
        report._clock_interval = setInterval(() => {
            const now = frappe.datetime.now_datetime();
            report.page.set_title(`WFH Command Center — ${now.split(" ")[1].slice(0, 5)}`);
        }, 10000);

        // Manual refresh button
        report.page.add_inner_button(__("⟳ Refresh Now"), () => {
            report._render_dashboard();
            report.refresh();
        });

        // Today quick-set
        report.page.add_inner_button(__("Today"), () => {
            report.set_filter_value("date", frappe.datetime.nowdate());
            report._render_dashboard();
            report.refresh();
        });
    },

    after_datatable_render(datatable) {
        // Called after the top-performers table renders
        this._render_dashboard();
    },

    // ── Internal render ────────────────────────────────────────────────────

    _render_dashboard() {
        const report = frappe.query_reports["WFH Command Center"];
        const date   = frappe.query_report.get_filter_value("date") || frappe.datetime.nowdate();

        frappe.call({
            method: "ecclesia.api.analytics.get_command_center_data",
            args: { date },
            callback(r) {
                if (!r.message) return;
                const d = r.message;
                report._render_kpis(d);
                report._render_panels(d);
            }
        });
    },

    _render_kpis(d) {
        const kpis = [
            { label: "Active WFH Today",      value: d.active_sessions,                    color: "#4f46e5", icon: "👤" },
            { label: "Total Hours Logged",     value: `${d.total_hours} h`,                color: "#0ea5e9", icon: "⏱" },
            { label: "Total Points Earned",    value: Math.round(d.total_points),           color: "#8b5cf6", icon: "⭐" },
            { label: "Business Value",         value: frappe.format(d.total_business_value, { fieldtype: "Currency" }), color: "#10b981", icon: "💰" },
            { label: "Flagged Employees",      value: (d.flagged_employees || []).length,   color: "#f59e0b", icon: "⚑" },
            { label: "Pending Summaries",      value: (d.pending_summaries || []).length,   color: "#ef4444", icon: "📋" },
        ];

        const html = kpis.map(k => `
            <div style="background:white;border:1px solid #e5e7eb;border-radius:10px;padding:16px 20px;
                        display:flex;align-items:center;gap:14px;box-shadow:0 1px 3px rgba(0,0,0,.06);">
                <div style="font-size:28px;">${k.icon}</div>
                <div>
                    <div style="font-size:22px;font-weight:700;color:${k.color};">${k.value}</div>
                    <div style="font-size:12px;color:#6b7280;margin-top:2px;">${k.label}</div>
                </div>
            </div>
        `).join("");

        document.getElementById("wfh-kpi-row").innerHTML = html;
    },

    _render_panels(d) {
        const flagged_rows = (d.flagged_employees || []).map(e => `
            <tr>
                <td style="padding:6px 8px;font-size:12px;">${e.employee_name}</td>
                <td style="padding:6px 8px;font-size:12px;">${e.department || "—"}</td>
                <td style="padding:6px 8px;font-size:12px;color:#d97706;">${e.session_status || "—"}</td>
                <td style="padding:6px 8px;font-size:12px;color:#dc2626;">${e.flag_notes || "—"}</td>
            </tr>
        `).join("") || `<tr><td colspan="4" style="text-align:center;color:#9ca3af;padding:12px;">No flagged employees today 🎉</td></tr>`;

        const dept_rows = (d.department_breakdown || []).slice(0, 6).map(dept => `
            <tr>
                <td style="padding:6px 8px;font-size:12px;">${dept.department || "—"}</td>
                <td style="padding:6px 8px;font-size:12px;text-align:center;">${dept.employees}</td>
                <td style="padding:6px 8px;font-size:12px;text-align:center;">${dept.avg_hours}</td>
                <td style="padding:6px 8px;font-size:12px;text-align:right;color:#4f46e5;font-weight:600;">${Math.round(dept.total_points)}</td>
            </tr>
        `).join("") || `<tr><td colspan="4" style="text-align:center;color:#9ca3af;padding:12px;">No data</td></tr>`;

        const pending_rows = (d.pending_summaries || []).map(e => `
            <li style="padding:4px 0;font-size:12px;color:#dc2626;">
                ${e.employee_name} <span style="color:#6b7280;">(${e.department || "—"} · ${e.total_hours || 0} h)</span>
            </li>
        `).join("") || `<li style="color:#9ca3af;">All summaries submitted ✓</li>`;

        document.getElementById("wfh-panels").innerHTML = `
            <!-- Flagged Employees Panel -->
            <div style="background:white;border:1px solid #fde68a;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.06);">
                <div style="background:#fffbeb;padding:10px 16px;border-bottom:1px solid #fde68a;font-size:13px;font-weight:600;color:#92400e;">
                    ⚑ Flagged Employees (${(d.flagged_employees||[]).length})
                </div>
                <div style="overflow-x:auto;max-height:240px;overflow-y:auto;">
                    <table style="width:100%;border-collapse:collapse;">
                        <thead>
                            <tr style="background:#fef9c3;">
                                <th style="padding:6px 8px;font-size:11px;text-align:left;color:#78350f;">Name</th>
                                <th style="padding:6px 8px;font-size:11px;text-align:left;color:#78350f;">Dept</th>
                                <th style="padding:6px 8px;font-size:11px;text-align:left;color:#78350f;">Session</th>
                                <th style="padding:6px 8px;font-size:11px;text-align:left;color:#78350f;">Flag Reason</th>
                            </tr>
                        </thead>
                        <tbody>${flagged_rows}</tbody>
                    </table>
                </div>
            </div>

            <!-- Department Breakdown Panel -->
            <div style="background:white;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.06);">
                <div style="background:#f9fafb;padding:10px 16px;border-bottom:1px solid #e5e7eb;font-size:13px;font-weight:600;color:#374151;">
                    🏢 Department Breakdown
                </div>
                <div style="overflow-x:auto;max-height:240px;overflow-y:auto;">
                    <table style="width:100%;border-collapse:collapse;">
                        <thead>
                            <tr style="background:#f3f4f6;">
                                <th style="padding:6px 8px;font-size:11px;text-align:left;color:#6b7280;">Department</th>
                                <th style="padding:6px 8px;font-size:11px;text-align:center;color:#6b7280;">Staff</th>
                                <th style="padding:6px 8px;font-size:11px;text-align:center;color:#6b7280;">Avg Hrs</th>
                                <th style="padding:6px 8px;font-size:11px;text-align:right;color:#6b7280;">Points</th>
                            </tr>
                        </thead>
                        <tbody>${dept_rows}</tbody>
                    </table>
                </div>
            </div>

            <!-- Pending Summaries Panel (full width) -->
            <div style="grid-column:1/-1;background:white;border:1px solid #fecaca;border-radius:10px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.06);">
                <div style="font-size:13px;font-weight:600;color:#991b1b;margin-bottom:8px;">
                    📋 Pending Daily Summaries (${(d.pending_summaries||[]).length})
                </div>
                <ul style="list-style:none;margin:0;padding:0;columns:2;gap:16px;">
                    ${pending_rows}
                </ul>
            </div>
        `;
    }
};
