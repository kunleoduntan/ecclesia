// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

// ecclesia/ecclesia/report/amortized_cost_report/amortized_cost_report.js

frappe.query_reports["Amortized Cost Report"] = {
    filters: [
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "width": 130,
            "reqd": 1,
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "width": 130,
            "reqd": 1,
            "default": frappe.datetime.get_today()
        },
        {
            "fieldname": "purchase_invoice",
            "label": __("Purchase Invoice"),
            "fieldtype": "Link",
            "options": "Purchase Invoice",
            "width": 180
        },
        {
            "fieldname": "supplier",
            "label": __("Supplier"),
            "fieldtype": "Link",
            "options": "Supplier",
            "width": 150
        }
    ],
    
    onload: function(report) {
        report.page.add_inner_button(__("Export to Excel"), function() {
            var filters = report.get_values();
            
            // Show loading message
            frappe.show_alert({
                message: __('Generating Excel report...'),
                indicator: 'blue'
            }, 3);
            
            // Open download URL directly in a new tab
            var url = frappe.urllib.get_full_url(
                "/api/method/ecclesia.ecclesia.report.amortized_cost_report.amortized_cost_report.export_to_excel"
            );
            
            // Add filters as query parameters
            url += "?filters=" + encodeURIComponent(JSON.stringify(filters));
            
            // Open in new tab for download
            window.open(url, '_blank');
            
        }).addClass("btn-primary");
    },
    
    formatter: function(value, row, column, data) {
        // Format amount with styling
        if (column.fieldname === "amount") {
            if (value) {
                return `<span style="font-weight:500;">${format_currency(value)}</span>`;
            }
            return "—";
        }
        
        // Format prepayment balance with colors
        if (column.fieldname === "prepayment_balance") {
            if (value && value > 0) {
                return `<span style="color:#16a34a;font-weight:600;">${format_currency(value)}</span>`;
            } else if (value && value < 0) {
                return `<span style="color:#dc2626;font-weight:600;">${format_currency(value)}</span>`;
            }
            return value ? format_currency(value) : "—";
        }
        
        // Format frequency with badges
        if (column.fieldname === "custom_frequency") {
            if (!value) return "—";
            let badge_color = "#4f46e5";
            if (value === "Monthly") badge_color = "#0891b2";
            else if (value === "Quarterly") badge_color = "#7c3aed";
            else if (value === "Yearly") badge_color = "#059669";
            else if (value === "Weekly") badge_color = "#d97706";
            else if (value === "Daily") badge_color = "#dc2626";
            
            return `<span style="background:${badge_color};color:white;padding:2px 10px;border-radius:12px;font-size:0.85em;">${value}</span>`;
        }
        
        // Format dates
        if (column.fieldname === "custom_start_date" || column.fieldname === "custom_end_date" || column.fieldname === "date" || column.fieldname === "period") {
            if (value) {
                return frappe.datetime.str_to_user(value);
            }
            return "—";
        }
        
        // Highlight invoice numbers
        if (column.fieldname === "purchase_invoice") {
            return `<span style="color:#1e40af;font-weight:600;">${value}</span>`;
        }
        
        // Highlight supplier names
        if (column.fieldname === "supplier") {
            return `<span style="color:#6d28d9;font-weight:600;">${value || "—"}</span>`;
        }
        
        // Highlight description
        if (column.fieldname === "custom_description") {
            return `<span style="color:#374151;font-weight:500;">${value || "—"}</span>`;
        }
        
        // Format status with colors
        if (column.fieldname === "status") {
            if (value === "Completed") {
                return `<span style="color:#16a34a;font-weight:600;">✅ ${value}</span>`;
            } else if (value === "Due Today") {
                return `<span style="color:#dc2626;font-weight:700;">⚠️ ${value}</span>`;
            } else if (value === "Pending") {
                return `<span style="color:#d97706;font-weight:600;">⏳ ${value}</span>`;
            } else if (value === "No Schedule") {
                return `<span style="color:#6b7280;">— ${value}</span>`;
            }
            return value;
        }
        
        return value || "—";
    },
    
    tree: false,
    name_field: "name",
    parent_field: "parent_row"
};