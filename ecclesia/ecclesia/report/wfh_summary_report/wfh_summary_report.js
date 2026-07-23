// WFH Summary Report — Client JS
// Ecclesia Module

frappe.query_reports["WFH Summary Report"] = {

    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.nowdate(), -1),
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
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department"
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
        }
    ],

    // ── Column formatters ──────────────────────────────────────────────────

    formatter(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "compliance_pct") {
            const pct = parseFloat(data.compliance_pct || 0);
            const color = pct >= 90 ? "green" : pct >= 70 ? "orange" : "red";
            return `<span style="color:${color};font-weight:600;">${pct}%</span>`;
        }

        if (column.fieldname === "avg_composite") {
            const score = parseFloat(data.avg_composite || 0);
            const color = score >= 75 ? "green" : score >= 50 ? "orange" : "red";
            return `<span style="color:${color};font-weight:600;">${score}</span>`;
        }

        if (column.fieldname === "days_flagged") {
            const n = parseInt(data.days_flagged || 0);
            if (n > 0) return `<span style="color:red;font-weight:600;">⚑ ${n}</span>`;
            return `<span style="color:gray;">—</span>`;
        }

        if (column.fieldname === "total_points") {
            const pts = parseFloat(data.total_points || 0);
            const color = pts >= 100 ? "green" : pts >= 50 ? "orange" : "red";
            return `<span style="color:${color};font-weight:500;">${pts}</span>`;
        }

        return value;
    },

    // ── Row click → employee detail ────────────────────────────────────────

    onload(report) {
        report.page.add_inner_button(__("Export to Excel"), () => {
            report.export_report("xlsx");
        });

        report.page.add_inner_button(__("View Productivity Detail"), () => {
            const employee = report.get_filter_value("employee");
            frappe.set_route("query-report/Productivity Report", {
                from_date: report.get_filter_value("from_date"),
                to_date:   report.get_filter_value("to_date"),
                employee:  employee || ""
            });
        });
    },

    get_datatable_options(options) {
        return Object.assign(options, {
            checkboxColumn: false,
            events: {
                onRowClick(_, rowIndex, nativeEvent) {
                    // No-op; using formatter links instead
                }
            }
        });
    }
};
