// Compliance Report — Client JS
// Ecclesia Module

frappe.query_reports["Compliance Report"] = {

    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_start(),
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
            options: "Employee"
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department"
        },
        {
            fieldname: "compliance_level",
            label: __("Filter by Compliance"),
            fieldtype: "Select",
            options: "\nFull (100%)\nPartial (50–99%)\nFailed (<50%)",
            description: "Filter rows by compliance band"
        }
    ],

    // ── Column formatters ──────────────────────────────────────────────────

    formatter(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "compliance_score") {
            const score = parseFloat(data.compliance_score || 0);
            let color, label;
            if (score === 100) { color = "#16a34a"; label = "✓ Full"; }
            else if (score >= 50) { color = "#d97706"; label = `⚠ ${score}%`; }
            else { color = "#dc2626"; label = `✗ ${score}%`; }

            const bar_width = Math.min(score, 100);
            return `
                <div style="display:flex;align-items:center;gap:8px;">
                    <div style="width:80px;background:#e5e7eb;border-radius:4px;height:6px;">
                        <div style="width:${bar_width}%;height:6px;background:${color};border-radius:4px;"></div>
                    </div>
                    <span style="color:${color};font-weight:600;">${label}</span>
                </div>`;
        }

        if (column.fieldname === "wfh_approved") {
            return data.wfh_approved && data.wfh_approved.startsWith("✓")
                ? `<span style="color:#16a34a;">${data.wfh_approved}</span>`
                : `<span style="color:#dc2626;font-weight:500;">${data.wfh_approved}</span>`;
        }

        if (column.fieldname === "session_exists") {
            return data.session_exists && data.session_exists.startsWith("✓")
                ? `<span style="color:#16a34a;">${data.session_exists}</span>`
                : `<span style="color:#dc2626;font-weight:500;">${data.session_exists}</span>`;
        }

        if (column.fieldname === "summary_submitted") {
            return data.summary_submitted && data.summary_submitted.startsWith("✓")
                ? `<span style="color:#16a34a;">${data.summary_submitted}</span>`
                : `<span style="color:#dc2626;font-weight:500;">${data.summary_submitted}</span>`;
        }

        if (column.fieldname === "flagged") {
            return data.flagged && data.flagged !== "—"
                ? `<span style="color:#d97706;font-weight:600;">${data.flagged}</span>`
                : `<span style="color:#9ca3af;">—</span>`;
        }

        if (column.fieldname === "summary_status") {
            const colors = {
                Reviewed: "#16a34a", Submitted: "#3b82f6",
                Flagged:  "#d97706", Draft:     "#6b7280", "—": "#9ca3af"
            };
            const col = colors[data.summary_status] || "#6b7280";
            return `<span style="color:${col};font-weight:500;">${data.summary_status}</span>`;
        }

        if (column.fieldname === "issues") {
            return data.issues && data.issues !== "—"
                ? `<span style="color:#dc2626;font-size:11px;">${data.issues}</span>`
                : `<span style="color:#9ca3af;">—</span>`;
        }

        return value;
    },

    // ── Client-side compliance level filter ───────────────────────────────

    after_datatable_render(datatable) {
        // Client-side post-filter already applied via Python;
        // this hook kept for future live filtering.
    },

    // ── Toolbar buttons ────────────────────────────────────────────────────

    onload(report) {
        // Month quick-select
        report.page.add_inner_button(__("This Month"), () => {
            report.set_filter_value("from_date", frappe.datetime.month_start());
            report.set_filter_value("to_date",   frappe.datetime.month_end());
            report.refresh();
        });

        report.page.add_inner_button(__("Last Month"), () => {
            const lm_start = frappe.datetime.add_months(frappe.datetime.month_start(), -1);
            const lm_end   = frappe.datetime.add_days(frappe.datetime.month_start(), -1);
            report.set_filter_value("from_date", lm_start);
            report.set_filter_value("to_date",   lm_end);
            report.refresh();
        });

        // Export failed employees
        report.page.add_inner_button(__("Export Failed Only"), () => {
            const rows = report.data || [];
            const failed = rows.filter(r => parseFloat(r.compliance_score || 0) < 50);
            if (!failed.length) {
                frappe.msgprint(__("No failed compliance rows in current result."));
                return;
            }
            const csv = [
                ["Employee", "Employee Name", "Department", "Date", "Score", "Issues"],
                ...failed.map(r => [
                    r.employee, r.employee_name, r.department,
                    r.date, r.compliance_score, r.issues
                ])
            ].map(r => r.join(",")).join("\n");
            const blob = new Blob([csv], { type: "text/csv" });
            const url  = URL.createObjectURL(blob);
            const a    = document.createElement("a");
            a.href     = url;
            a.download = "wfh_failed_compliance.csv";
            a.click();
        });
    }
};
