// ecclesia/ecclesia/report/compliance_liability_summary/compliance_liability_summary.js

frappe.query_reports["Compliance Liability Summary"] = {
    filters: [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "width": 180
        },
        {
            "fieldname": "obligation_type",
            "label": __("Obligation Type"),
            "fieldtype": "Select",
            "options": [
                "",
                "VAT",
                "WHT",
                "PAYE",
                "Pension",
                "NHF",
                "NSITF",
                "ITF",
                "CIT",
                "Stamp Duty",
                "Capital Gains Tax",
                "CAC Annual Return",
                "Regulatory Return",
                "Work Permit",
                "Environmental Permit",
                "Data Breach Notification",
                "AML/KYC",
                "Contractual Obligation",
                "Training Levy",
                "Other"
            ],
            "width": 200
        },
        {
            "fieldname": "period_label",
            "label": __("Period (MM-YYYY)"),
            "fieldtype": "Data",
            "width": 150,
            "placeholder": "e.g. 03-2026"
        },
        {
            "fieldname": "status",
            "label": __("Status"),
            "fieldtype": "Select",
            "options": [
                "",
                "Open",
                "Partially Paid",
                "Fully Paid",
                "Overdue",
                "Reconciled",
                "Exempt"
            ],
            "width": 150
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
            "fieldname": "show_overdue_only",
            "label": __("Show Overdue Only"),
            "fieldtype": "Check",
            "width": 130,
            "default": 0
        },
        {
            "fieldname": "min_balance_amount",
            "label": __("Min Balance Amount (₦)"),
            "fieldtype": "Currency",
            "width": 180
        }
    ],
    
    onload: function(report) {
        // Add export button
        report.page.add_inner_button(__("Export to Excel"), function() {
            var filters = report.get_values();
            frappe.call({
                method: "ecclesia.ecclesia.report.compliance_liability_summary.compliance_liability_summary.export_to_excel",
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
            if (value && value.includes("Fully Paid")) {
                return `<span style="color:#16a34a;font-weight:600;">${value}</span>`;
            } else if (value && value.includes("Overdue")) {
                return `<span style="color:#dc2626;font-weight:700;">${value}</span>`;
            } else if (value && value.includes("Partially Paid")) {
                return `<span style="color:#ea580c;font-weight:600;">${value}</span>`;
            } else if (value && value.includes("Open")) {
                return `<span style="color:#0284c7;">${value}</span>`;
            }
            return value;
        }
        
        if (column.fieldname === "balance_due") {
            if (value > 0) {
                return `<span style="color:#dc2626;font-weight:700;">${value}</span>`;
            } else if (value === 0) {
                return `<span style="color:#16a34a;font-weight:600;">${value}</span>`;
            }
            return value;
        }
        
        if (column.fieldname === "is_overdue_display") {
            if (value && value.includes("Yes")) {
                return `<span style="color:#dc2626;font-weight:700;">🔴 Yes</span>`;
            }
            return `<span style="color:#16a34a;font-weight:600;">✅ No</span>`;
        }
        
        return value;
    }
};