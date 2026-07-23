// ecclesia/ecclesia/report/license_expiry_report/license_expiry_report.js

frappe.query_reports["License Expiry Report"] = {
    filters: [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "width": 180
        },
        {
            "fieldname": "license_type",
            "label": __("License Type"),
            "fieldtype": "Select",
            "options": [
                "",
                "Operating",
                "Environmental",
                "Health & Safety",
                "Professional",
                "Business Permit",
                "Factory License",
                "NAFDAC License",
                "NSITF Certificate",
                "ITF Certificate",
                "SON Registration",
                "Fire Certificate",
                "Food Handler Certificate",
                "Electrical Installation Certificate",
                "Signage Permit",
                "AML License",
                "Regulatory",
                "Other"
            ],
            "width": 200
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
            "fieldname": "assigned_to",
            "label": __("Responsible Person"),
            "fieldtype": "Link",
            "options": "Employee",
            "width": 180
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
        }
    ],
    
    onload: function(report) {
        report.page.add_inner_button(__("Export to Excel"), function() {
            var filters = report.get_values();
            frappe.call({
                method: "ecclesia.ecclesia.report.license_expiry_report.license_expiry_report.export_to_excel",
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
            } else if (value && value.includes("Expires in 7")) {
                return `<span style="color:#dc2626;font-weight:700;background:#fee2e2;padding:2px 8px;border-radius:4px;">${value}</span>`;
            } else if (value && value.includes("Expires in 30")) {
                return `<span style="color:#ea580c;font-weight:600;">${value}</span>`;
            } else if (value && value.includes("Expires in 60")) {
                return `<span style="color:#f59e0b;font-weight:600;">${value}</span>`;
            } else if (value && value.includes("Active")) {
                return `<span style="color:#16a34a;font-weight:600;">${value}</span>`;
            }
            return value;
        }
        
        if (column.fieldname === "days_to_expiry") {
            if (value && value < 0) {
                return `<span style="color:#dc2626;font-weight:700;">${value}</span>`;
            } else if (value && value <= 7) {
                return `<span style="color:#dc2626;font-weight:700;">${value}</span>`;
            } else if (value && value <= 30) {
                return `<span style="color:#ea580c;font-weight:600;">${value}</span>`;
            } else if (value && value <= 60) {
                return `<span style="color:#f59e0b;font-weight:600;">${value}</span>`;
            } else if (value && value > 60) {
                return `<span style="color:#16a34a;">${value}</span>`;
            }
            return value || "—";
        }
        
        return value;
    }
};