// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt
/* eslint-disable */


frappe.query_reports["Standard Trial Balance - Classified"] = {
    "filters": [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            reqd: 1,
            default: frappe.defaults.get_user_default("Company")
        },
        {
            fieldname: "as_at_date",
            label: __("As at Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1
        },
        {
            fieldname: "include_zero_balance",
            label: __("Include Zero Balance Accounts"),
            fieldtype: "Check",
            default: 0
        }
    ],
    
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        if (!data) return value;
        
        // Section Headers
        if (data.is_header_row || data.is_separator) {
            return `<div style="
                color: #B0C4DE;
                font-weight: normal;
                padding: 2px 8px;
                margin: -4px -8px;
            ">${value}</div>`;
        }
        
        // Section Title
        if (data.is_section_header) {
            return `<div style="
                background-color: #E6F0FA;
                font-weight: bold;
                color: #1E3F6E;
                padding: 6px 8px;
                border-top: 2px solid #1E3F6E;
                border-bottom: 1px solid #D0D7DE;
                margin: -4px -8px;
            ">${value}</div>`;
        }
        
        // Subtotal Rows
        if (data.is_subtotal_row) {
            if (column.fieldname === "account_name") {
                return `<div style="
                    background-color: #E6F0FA;
                    font-weight: bold;
                    color: #1E3F6E;
                    padding: 4px 8px;
                    margin: -4px -8px;
                ">${value}</div>`;
            }
            if (["debit", "credit", "balance"].includes(column.fieldname)) {
                return `<div style="
                    background-color: #E6F0FA;
                    font-weight: bold;
                    color: #1E3F6E;
                    text-align: right;
                    padding: 4px 8px;
                    margin: -4px -8px;
                ">${value}</div>`;
            }
        }
        
        // Total Row
        if (data.is_total_row) {
            if (column.fieldname === "account_name") {
                return `<div style="
                    background-color: #1E3F6E;
                    color: white;
                    font-weight: bold;
                    padding: 6px 8px;
                    margin: -4px -8px;
                    border-top: 2px solid #1E3F6E;
                    border-bottom: 2px solid #1E3F6E;
                ">${value}</div>`;
            }
            if (["debit", "credit", "balance"].includes(column.fieldname)) {
                return `<div style="
                    background-color: #1E3F6E;
                    color: white;
                    font-weight: bold;
                    text-align: right;
                    padding: 6px 8px;
                    margin: -4px -8px;
                    border-top: 2px solid #1E3F6E;
                    border-bottom: 2px solid #1E3F6E;
                ">${value}</div>`;
            }
        }
        
        // Color coding for amounts
        if (column.fieldname === "debit" && data.debit > 0) {
            return `<span style="color: #2568B2; font-weight: 500;">${value}</span>`;
        }
        if (column.fieldname === "credit" && data.credit > 0) {
            return `<span style="color: #1E7E34; font-weight: 500;">${value}</span>`;
        }
        if (column.fieldname === "balance") {
            if (flt(data.balance) > 0) {
                return `<span style="color: #E67E22; font-weight: 600;">${value}</span>`;
            } else if (flt(data.balance) < 0) {
                return `<span style="color: #C0392B; font-weight: 600;">${value}</span>`;
            }
        }
        
        return value;
    },
    
    onload: function(report) {
        // Clear any existing buttons
        report.page.clear_primary_action();
        report.page.clear_inner_buttons();
        
        // Primary button - Beautiful Excel Export
        report.page.set_primary_action(__("📥 Download Beautiful Excel"), function() {
            download_beautiful_excel(report);
        });
        
        // Secondary buttons
        report.page.add_inner_button(__("📄 Export Standard Excel"), function() {
            frappe.query_report.export_report("xlsx");
        });
        
        report.page.add_inner_button(__("📑 Export PDF"), function() {
            frappe.query_report.export_report("pdf");
        });
        
        report.page.add_inner_button(__("🖨️ Print"), function() {
            frappe.query_report.print_report();
        });
        
        // Keyboard shortcuts
        report.page.wrapper.off("keydown").on("keydown", function(e) {
            if (e.ctrlKey && e.key === 'e') {
                e.preventDefault();
                download_beautiful_excel(report);
            }
        });
    }
};

// Beautiful Excel download function
function download_beautiful_excel(report) {
    const filters = report.get_values();
    
    if (!filters.company || !filters.as_at_date) {
        frappe.msgprint(__("Please set Company and As at Date before exporting."));
        return;
    }
    
    frappe.show_alert({
        message: __("✨ Creating beautifully formatted Trial Balance Excel report..."),
        indicator: "blue"
    }, 5);
    
    // Build URL for download
    const params = new URLSearchParams();
    params.append("cmd", "ecclesia.ecclesia.report.standard_trial_balance.standard_trial_balance.download_excel");
    params.append("filters", JSON.stringify(filters));
    
    // Trigger download
    const download_url = `/api/method/${params.get("cmd")}?${params.toString()}`;
    window.open(download_url, "_blank");
    
    setTimeout(function() {
        frappe.show_alert({
            message: __("✅ Excel download started!"),
            indicator: "green"
        }, 3);
    }, 2000);
}