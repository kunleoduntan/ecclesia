// ecclesia/ecclesia/report/suspicious_transaction_summary/suspicious_transaction_summary.js

frappe.query_reports["Suspicious Transaction Summary"] = {
    filters: [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "width": 180
        },
        {
            "fieldname": "report_type",
            "label": __("Report Type"),
            "fieldtype": "Select",
            "options": [
                "",
                "Suspicious Transaction Report (STR)",
                "Currency Transaction Report (CTR)",
                "Suspicious Activity Report (SAR)"
            ],
            "width": 220
        },
        {
            "fieldname": "status",
            "label": __("Status"),
            "fieldtype": "Select",
            "options": [
                "",
                "Draft",
                "Under Review",
                "Submitted to NFIU",
                "Closed — No Action",
                "Referred to Enforcement"
            ],
            "width": 180
        },
        {
            "fieldname": "nfiu_submitted",
            "label": __("NFIU Submitted"),
            "fieldtype": "Check",
            "width": 130,
            "default": 0
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "width": 130
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "width": 130
        },
        {
            "fieldname": "min_amount",
            "label": __("Min Amount (₦)"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "suspicious_indicators",
            "label": __("Indicator Contains"),
            "fieldtype": "Data",
            "width": 180,
            "placeholder": "e.g. Structuring"
        }
    ],
    
    onload: function(report) {
        report.page.add_inner_button(__("Export to Excel"), function() {
            var filters = report.get_values();
            frappe.call({
                method: "ecclesia.ecclesia.report.suspicious_transaction_summary.suspicious_transaction_summary.export_to_excel",
                args: {
                    filters: filters
                },
                callback: function(r) {
                    if (r.message) {
                        window.location.href = r.message;
                    }
                }
            });
        });
    },
    
    formatter: function(value, row, column, data) {
        if (column.fieldname === "status_display") {
            if (value && value.includes("Referred to Enforcement")) {
                return `<span style="color:#dc2626;font-weight:700;background:#fee2e2;padding:2px 8px;border-radius:4px;">${value}</span>`;
            } else if (value && value.includes("Submitted to NFIU")) {
                return `<span style="color:#2563eb;font-weight:600;">${value}</span>`;
            } else if (value && value.includes("Under Review")) {
                return `<span style="color:#f59e0b;font-weight:600;">${value}</span>`;
            } else if (value && value.includes("Closed")) {
                return `<span style="color:#16a34a;font-weight:600;">${value}</span>`;
            }
            return value;
        }
        
        if (column.fieldname === "nfiu_submitted_display") {
            if (value && value.includes("Yes")) {
                return `<span style="color:#16a34a;font-weight:600;">${value}</span>`;
            }
            return `<span style="color:#94a3b8;">${value}</span>`;
        }
        
        if (column.fieldname === "transaction_amount") {
            if (value > 10000000) {
                return `<span style="color:#dc2626;font-weight:700;">${value}</span>`;
            } else if (value > 5000000) {
                return `<span style="color:#ea580c;font-weight:600;">${value}</span>`;
            }
            return value;
        }
        
        return value;
    }
};