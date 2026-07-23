// ecclesia/ecclesia/report/aml_kyc_compliance/aml_kyc_compliance.js

frappe.query_reports["AML KYC Compliance"] = {
    filters: [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "width": 180
        },
        {
            "fieldname": "party_type",
            "label": __("Party Type"),
            "fieldtype": "Select",
            "options": [
                "",
                "Customer",
                "Supplier",
                "Employee",
                "Director",
                "Shareholder",
                "Agent",
                "Other"
            ],
            "width": 150
        },
        {
            "fieldname": "kyc_level",
            "label": __("KYC Level"),
            "fieldtype": "Select",
            "options": [
                "",
                "Simplified Due Diligence (SDD)",
                "Basic Customer Due Diligence (CDD)",
                "Enhanced Due Diligence (EDD)"
            ],
            "width": 250
        },
        {
            "fieldname": "risk_rating",
            "label": __("Risk Rating"),
            "fieldtype": "Select",
            "options": [
                "",
                "Low",
                "Medium",
                "High",
                "PEP — High",
                "Sanctioned — Blocked"
            ],
            "width": 180
        },
        {
            "fieldname": "from_date",
            "label": __("KYC From Date"),
            "fieldtype": "Date",
            "width": 130
        },
        {
            "fieldname": "to_date",
            "label": __("KYC To Date"),
            "fieldtype": "Date",
            "width": 130
        },
        {
            "fieldname": "identity_verified",
            "label": __("Identity Verified"),
            "fieldtype": "Check",
            "width": 130,
            "default": 0
        },
        {
            "fieldname": "show_expiring_only",
            "label": __("Show Expiring Only (≤30 days)"),
            "fieldtype": "Check",
            "width": 200,
            "default": 0
        },
        {
            "fieldname": "is_pep",
            "label": __("Is PEP"),
            "fieldtype": "Check",
            "width": 130,
            "default": 0
        },
        {
            "fieldname": "sanctions_match",
            "label": __("Sanctions Match Found"),
            "fieldtype": "Check",
            "width": 180,
            "default": 0
        }
    ],
    
    onload: function(report) {
        report.page.add_inner_button(__("Export to Excel"), function() {
            var filters = report.get_values();
            frappe.call({
                method: "ecclesia.ecclesia.report.aml_kyc_compliance.aml_kyc_compliance.export_to_excel",
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
        if (column.fieldname === "risk_rating") {
            if (value === "Low") {
                return `<span style="color:#16a34a;font-weight:600;">${value}</span>`;
            } else if (value === "Medium") {
                return `<span style="color:#f59e0b;font-weight:600;">${value}</span>`;
            } else if (value === "High") {
                return `<span style="color:#ea580c;font-weight:700;">${value}</span>`;
            } else if (value === "PEP — High") {
                return `<span style="color:#dc2626;font-weight:700;">${value}</span>`;
            } else if (value === "Sanctioned — Blocked") {
                return `<span style="color:#991b1b;font-weight:700;background:#fee2e2;padding:2px 8px;border-radius:4px;">${value}</span>`;
            }
            return value;
        }
        
        if (column.fieldname === "status_display") {
            if (value && value.includes("Expired")) {
                return `<span style="color:#dc2626;font-weight:700;">${value}</span>`;
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