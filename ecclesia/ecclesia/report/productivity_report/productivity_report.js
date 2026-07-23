// Productivity Report — Client JS
// Ecclesia Module

frappe.query_reports["Productivity Report"] = {

    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_days(frappe.datetime.nowdate(), -7),
            reqd: 1
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.nowdate(),
            reqd: 1
        },
        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee",
            get_query() {
                const dept = frappe.query_report.get_filter_value("department");
                return dept ? { filters: { department: dept } } : {};
            }
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department"
        },
        {
            fieldname: "module",
            label: __("Module"),
            fieldtype: "Select",
            options: "\nSales\nAccounts\nCRM\nBuying\nStock",
            description: "Filter by ERPNext module activity"
        }
    ],

    // ── Column formatters ──────────────────────────────────────────────────

    formatter(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "composite_score") {
            const score = parseFloat(data.composite_score || 0);
            const color = score >= 75 ? "#16a34a" : score >= 50 ? "#d97706" : "#dc2626";
            const bar_width = Math.min(score, 100);
            return `
                <div style="display:flex;align-items:center;gap:8px;">
                    <div style="flex:1;background:#e5e7eb;border-radius:4px;height:6px;min-width:60px;">
                        <div style="width:${bar_width}%;height:6px;background:${color};border-radius:4px;"></div>
                    </div>
                    <span style="color:${color};font-weight:600;min-width:32px;">${score}</span>
                </div>`;
        }

        if (column.fieldname === "summary_status") {
            const colors = {
                "Submitted": "green",
                "Reviewed":  "blue",
                "Flagged":   "orange",
                "Draft":     "gray",
                "No Summary":"red"
            };
            const col = colors[data.summary_status] || "gray";
            const indicator = `<span class="indicator-pill ${col}">${data.summary_status || "—"}</span>`;
            return indicator;
        }

        if (column.fieldname === "session_status") {
            const colors = { Open: "blue", Closed: "green", Flagged: "orange" };
            const col = colors[data.session_status] || "gray";
            return `<span class="indicator-pill ${col}">${data.session_status || "—"}</span>`;
        }

        if (column.fieldname === "hours") {
            const h = parseFloat(data.hours || 0);
            if (h < 4)  return `<span style="color:#dc2626;">${h}</span>`;
            if (h > 10) return `<span style="color:#d97706;">${h}</span>`;
            return `<span style="color:#16a34a;">${h}</span>`;
        }

        if (column.fieldname === "points") {
            const pts = parseFloat(data.points || 0);
            const color = pts >= 50 ? "#16a34a" : pts >= 20 ? "#d97706" : "#dc2626";
            return `<span style="color:${color};font-weight:600;">${pts}</span>`;
        }

        if (column.fieldname === "top_module") {
            const badges = {
                Sales:    "#3b82f6", Accounts: "#8b5cf6",
                CRM:      "#ec4899", Buying:   "#f59e0b",
                Stock:    "#10b981"
            };
            const bg = badges[data.top_module] || "#6b7280";
            return data.top_module
                ? `<span style="background:${bg};color:white;padding:2px 8px;border-radius:4px;font-size:11px;">${data.top_module}</span>`
                : `<span style="color:gray;">—</span>`;
        }

        return value;
    },

    // ── Toolbar buttons ────────────────────────────────────────────────────

    onload(report) {
        report.page.add_inner_button(__("Today Only"), () => {
            const today = frappe.datetime.nowdate();
            report.set_filter_value("from_date", today);
            report.set_filter_value("to_date", today);
            report.refresh();
        });

        report.page.add_inner_button(__("This Week"), () => {
            report.set_filter_value("from_date", frappe.datetime.week_start());
            report.set_filter_value("to_date",   frappe.datetime.week_end());
            report.refresh();
        });

        report.page.add_inner_button(__("View Activity Logs"), () => {
            const emp = report.get_filter_value("employee");
            const opts = emp ? { employee: emp } : {};
            frappe.route_options = opts;
            frappe.set_route("List", "Work Activity Log");
        });
    }
};
