// ecclesia/ecclesia/report/environmental_compliance_report/environmental_compliance_report.js

frappe.query_reports["Environmental Compliance Report"] = {
    filters: [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "width": 180
        },
        {
            "fieldname": "permit_type",
            "label": __("Permit Type"),
            "fieldtype": "Select",
            "options": [
                "",
                "Environmental Impact Assessment (EIA)",
                "Environmental Management Plan (EMP)",
                "Waste Disposal Permit",
                "Effluent Discharge Consent",
                "Air Quality Permit",
                "Noise Permit",
                "Chemical Storage Permit",
                "NESREA Permit",
                "FEPA Licence",
                "State EPA Permit",
                "Other"
            ],
            "width": 250
        },
        {
            "fieldname": "issuing_authority",
            "label": __("Issuing Authority"),
            "fieldtype": "Link",
            "options": "Regulatory Authority",
            "width": 180
        },
        {
            "fieldname": "status",
            "label": __("Status"),
            "fieldtype": "Select",
            "options": [
                "",
                "Active",
                "Expiring Soon",
                "Expired",
                "Under Renewal",
                "Suspended",
                "Revoked"
            ],
            "width": 150
        },
        {
            "fieldname": "facility",
            "label": __("Facility Contains"),
            "fieldtype": "Data",
            "width": 180,
            "placeholder": "e.g. Lagos"
        },
        {
            "fieldname": "expiring_within_days",
            "label": __("Expiring Within (Days)"),
            "fieldtype": "Int",
            "width": 160,
            "placeholder": "e.g. 30"
        },
        {
            "fieldname": "show_expired_only",
            "label": __("Show Expired Only"),
            "fieldtype": "Check",
            "width": 150,
            "default": 0
        },
        {
            "fieldname": "last_inspection_result",
            "label": __("Last Inspection Result"),
            "fieldtype": "Select",
            "options": [
                "",
                "Not Yet Inspected",
                "Satisfactory",
                "Minor Non-Compliance",
                "Major Non-Compliance",
                "Prosecution"
            ],
            "width": 200
        }
    ],
    
    onload: function(report) {
        report.page.add_inner_button(__("Export to Excel"), function() {
            var filters = report.get_values();
            frappe.call({
                method: "ecclesia.ecclesia.report.environmental_compliance_report.environmental_compliance_report.export_to_excel",
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
            if (value && value.includes("Expired")) {
                return `<span style="color:#dc2626;font-weight:700;background:#fee2e2;padding:2px 8px;border-radius:4px;">${value}</span>`;
            } else if (value && value.includes("Expiring Soon")) {
                return `<span style="color:#ea580c;font-weight:700;">${value}</span>`;
            } else if (value && value.includes("Review Soon")) {
                return `<span style="color:#f59e0b;font-weight:600;">${value}</span>`;
            } else if (value && value.includes("Active")) {
                return `<span style="color:#16a34a;font-weight:600;">${value}</span>`;
            }
            return value;
        }
        
        if (column.fieldname === "days_to_expiry") {
            if (value && value < 0) {
                return `<span style="color:#dc2626;font-weight:700;">${value}</span>`;
            } else if (value && value <= 30) {
                return `<span style="color:#ea580c;font-weight:700;">${value}</span>`;
            } else if (value && value <= 90) {
                return `<span style="color:#f59e0b;font-weight:600;">${value}</span>`;
            } else if (value && value > 90) {
                return `<span style="color:#16a34a;">${value}</span>`;
            }
            return value || "—";
        }
        
        return value;
    }
};