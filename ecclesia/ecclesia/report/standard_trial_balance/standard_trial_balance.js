// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt
/* eslint-disable */

// IMPORTANT: Replace "Standard Trial Balance" with your exact report name
frappe.query_reports["Standard Trial Balance"] = {
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
        
        // Get filter values
        let company = '';
        let as_at_date = '';
        
        try {
            if (frappe.query_report && frappe.query_report.filters) {
                const filters = frappe.query_report.filters;
                for (let f of filters) {
                    if (f.fieldname === 'company') {
                        company = f.value || frappe.defaults.get_user_default("Company") || '';
                    }
                    if (f.fieldname === 'as_at_date') {
                        as_at_date = f.value || frappe.datetime.get_today() || '';
                    }
                }
            }
        } catch(e) {
            company = frappe.defaults.get_user_default("Company") || '';
            as_at_date = frappe.datetime.get_today() || '';
        }
        
        if (!company) {
            company = frappe.defaults.get_user_default("Company") || '';
        }
        if (!as_at_date) {
            as_at_date = frappe.datetime.get_today() || '';
        }
        
        // Make account names clickable
        if (column.fieldname === "account_name" && data.account && 
            !data.is_total_row && !data.is_synthetic) {
            
            const gl_url = `/app/query-report/General%20Ledger?account=${encodeURIComponent(data.account)}&company=${encodeURIComponent(company)}&from_date=${encodeURIComponent(as_at_date)}&to_date=${encodeURIComponent(as_at_date)}`;
            
            return `<a href="${gl_url}" 
                       target="_blank"
                       style="color: #1E3F6E; text-decoration: none; cursor: pointer; 
                              display: block; padding: 2px 8px; margin: -4px -8px;"
                       onmouseover="this.style.textDecoration='underline'" 
                       onmouseout="this.style.textDecoration='none'"
                       title="View General Ledger for this account">
                        ${value}
                    </a>`;
        }
        
        // Make account codes clickable
        if (column.fieldname === "account_number" && data.account && 
            !data.is_total_row && !data.is_synthetic) {
            
            const gl_url = `/app/query-report/General%20Ledger?account=${encodeURIComponent(data.account)}&company=${encodeURIComponent(company)}&from_date=${encodeURIComponent(as_at_date)}&to_date=${encodeURIComponent(as_at_date)}`;
            
            return `<a href="${gl_url}" 
                       target="_blank"
                       style="color: #1E3F6E; text-decoration: none; cursor: pointer; 
                              display: block; padding: 2px 8px; margin: -4px -8px;"
                       onmouseover="this.style.textDecoration='underline'" 
                       onmouseout="this.style.textDecoration='none'"
                       title="View General Ledger for this account">
                        ${value}
                    </a>`;
        }
        
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
        
        // Color coding for amounts
        if (column.fieldname === "balance") {
            if (flt(data.balance) > 0) {
                return `<span style="color: #27AE60; font-weight: 600;">${value}</span>`;
            } else if (flt(data.balance) < 0) {
                return `<span style="color: #C0392B; font-weight: 600;">${value}</span>`;
            }
        }
        
        if (column.fieldname === "net_debit" && data.net_debit > 0) {
            return `<span style="color: #27AE60; font-weight: 500;">${value}</span>`;
        }
        
        if (column.fieldname === "net_credit" && data.net_credit > 0) {
            return `<span style="color: #C0392B; font-weight: 500;">${value}</span>`;
        }
        
        // Total row styling
        if (data.is_total_row) {
            if (column.fieldname === "account_name") {
                return `<div style="
                    background-color: #FFF9E6;
                    font-weight: bold;
                    color: #1B3B6F;
                    padding: 6px 8px;
                    margin: -4px -8px;
                    border-top: 2px solid #F39C12;
                    border-bottom: 2px solid #F39C12;
                ">${value}</div>`;
            }
            if (["balance", "net_debit", "net_credit", "debit", "credit"].includes(column.fieldname)) {
                return `<div style="
                    background-color: #FFF9E6;
                    font-weight: bold;
                    color: #1B3B6F;
                    text-align: right;
                    padding: 6px 8px;
                    margin: -4px -8px;
                    border-top: 2px solid #F39C12;
                    border-bottom: 2px solid #F39C12;
                ">${value}</div>`;
            }
        }
        
        // Synthetic row styling
        if (data.is_synthetic) {
            if (column.fieldname === "account_name") {
                return `<div style="
                    background-color: #EEF2FF;
                    font-style: italic;
                    color: #1B3B6F;
                    padding: 4px 8px;
                    margin: -4px -8px;
                    border: 1px solid #4A90E2;
                ">${value}</div>`;
            }
            if (["balance", "net_debit", "net_credit", "debit", "credit"].includes(column.fieldname)) {
                return `<div style="
                    background-color: #EEF2FF;
                    font-style: italic;
                    color: #1B3B6F;
                    text-align: right;
                    padding: 4px 8px;
                    margin: -4px -8px;
                    border: 1px solid #4A90E2;
                ">${value}</div>`;
            }
        }
        
        if (column.fieldname === "debit" && data.debit > 0) {
            return `<span style="color: #2568B2; font-weight: 500;">${value}</span>`;
        }
        if (column.fieldname === "credit" && data.credit > 0) {
            return `<span style="color: #1E7E34; font-weight: 500;">${value}</span>`;
        }
        
        return value;
    },
    
    "onload": function(report) {
        console.log("Standard Trial Balance report loaded"); // Debug message
        
        // Store report reference
        frappe.query_report = report;
        
        // Clear any existing buttons
        report.page.clear_primary_action();
        report.page.clear_inner_buttons();
        
        // Primary button - Cute Excel Export
        report.page.set_primary_action(__("📥 Download Cute Excel"), function() {
            download_cute_excel(report);
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
                download_cute_excel(report);
            }
        });
    }
};

// Cute Excel download function
function download_cute_excel(report) {
    console.log("Download Cute Excel called"); // Debug message
    
    // Get filter values from the report
    let company = '';
    let as_at_date = '';
    let include_zero_balance = 0;
    
    if (report && report.filters) {
        for (let f of report.filters) {
            if (f.fieldname === 'company') {
                company = f.value || '';
            }
            if (f.fieldname === 'as_at_date') {
                as_at_date = f.value || '';
            }
            if (f.fieldname === 'include_zero_balance') {
                include_zero_balance = f.value || 0;
            }
        }
    }
    
    // Fallback to defaults
    if (!company) {
        company = frappe.defaults.get_user_default("Company") || '';
    }
    if (!as_at_date) {
        as_at_date = frappe.datetime.get_today() || '';
    }
    
    // Validate filters
    if (!company) {
        frappe.msgprint(__("Please select a Company before exporting."));
        return;
    }
    if (!as_at_date) {
        frappe.msgprint(__("Please select an As at Date before exporting."));
        return;
    }
    
    frappe.show_alert({
        message: __("✨ Creating beautifully formatted Cute Excel report..."),
        indicator: "blue"
    }, 5);
    
    // Build filters object
    const filters = {
        company: company,
        as_at_date: as_at_date,
        include_zero_balance: include_zero_balance
    };
    
    console.log("Filters:", filters); // Debug message
    
    // Build URL for download - UPDATE THIS TO MATCH YOUR APP
    const params = new URLSearchParams();
    // IMPORTANT: Change 'ecclesia.ecclesia' to your actual app name
    params.append("cmd", "ecclesia.ecclesia.report.standard_trial_balance.standard_trial_balance.download_cute_excel");
    params.append("filters", JSON.stringify(filters));
    
    // Trigger download
    const download_url = `/api/method/${params.get("cmd")}?${params.toString()}`;
    console.log("Download URL:", download_url); // Debug message
    window.open(download_url, "_blank");
    
    setTimeout(function() {
        frappe.show_alert({
            message: __("✅ Excel download started!"),
            indicator: "green"
        }, 3);
    }, 2000);
}