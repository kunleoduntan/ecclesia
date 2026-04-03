// Copyright (c) 2024, Ecclesia and contributors
// For license information, please see license.txt

frappe.query_reports["Customer Ledger Report"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 1
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname": "customer",
            "label": __("Customer"),
            "fieldtype": "Link",
            "options": "Customer"
        }
    ],

    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (!data) return value;

        // Customer Header Row
        if (data.is_header_row) {
            if (column.fieldname === "posting_date") {
                return `<div style="
                    background: linear-gradient(90deg, #1E3F6E 0%, #2C5A9E 100%);
                    margin: -4px -8px;
                    padding: 8px 12px;
                    color: white;
                    font-weight: 700;
                    font-size: 13px;
                ">⬤ ${frappe.utils.escape_html(data.customer_name || '')} 
                <span style="font-size:11px; opacity:0.8;">[${frappe.utils.escape_html(data.customer || '')}]</span>
                </div>`;
            }
            if (column.fieldname === "balance" && data.balance) {
                const color = data.balance > 0 ? "#90caf9" : "#ef9a9a";
                return `<div style="
                    background: linear-gradient(90deg, #1E3F6E 0%, #2C5A9E 100%);
                    margin: -4px -8px;
                    padding: 8px 12px;
                    color: ${color};
                    font-size: 11px;
                    text-align: right;
                ">Opening: ${frappe.format(data.balance, {fieldtype: "Currency"})}</div>`;
            }
            if (column.fieldname !== "posting_date" && column.fieldname !== "balance") {
                return `<div style="
                    background: linear-gradient(90deg, #1E3F6E 0%, #2C5A9E 100%);
                    margin: -4px -8px;
                    padding: 8px 12px;
                "></div>`;
            }
        }

        // Subtotal Row
        if (data.is_total_row) {
            const bgColor = "#E6F0FA";
            
            if (column.fieldname === "customer_name") {
                return `<div style="
                    background-color: ${bgColor};
                    margin: -4px -8px;
                    padding: 6px 12px;
                    font-weight: 700;
                    color: #1E3F6E;
                    border-top: 2px solid #2C5A9E;
                ">${frappe.utils.escape_html(data.customer_name || '')}</div>`;
            }
            
            if (column.fieldname === "debit") {
                return `<div style="
                    background-color: ${bgColor};
                    margin: -4px -8px;
                    padding: 6px 12px;
                    font-weight: 700;
                    color: #2568B2;
                    text-align: right;
                    border-top: 2px solid #2C5A9E;
                ">${frappe.format(data.debit || 0, {fieldtype: "Currency"})}</div>`;
            }
            
            if (column.fieldname === "credit") {
                return `<div style="
                    background-color: ${bgColor};
                    margin: -4px -8px;
                    padding: 6px 12px;
                    font-weight: 700;
                    color: #1E7E34;
                    text-align: right;
                    border-top: 2px solid #2C5A9E;
                ">${frappe.format(data.credit || 0, {fieldtype: "Currency"})}</div>`;
            }
            
            if (column.fieldname === "balance") {
                const color = data.balance > 0 ? "#E67E22" : data.balance < 0 ? "#C0392B" : "#1E7E34";
                return `<div style="
                    background-color: ${bgColor};
                    margin: -4px -8px;
                    padding: 6px 12px;
                    font-weight: 700;
                    color: ${color};
                    text-align: right;
                    border-top: 2px solid #2C5A9E;
                ">${frappe.format(data.balance || 0, {fieldtype: "Currency"})}</div>`;
            }
            
            if (column.fieldname === "description") {
                return `<div style="
                    background-color: ${bgColor};
                    margin: -4px -8px;
                    padding: 6px 12px;
                    font-style: italic;
                    color: #555;
                    border-top: 2px solid #2C5A9E;
                ">${frappe.utils.escape_html(data.description || '')}</div>`;
            }
            
            return `<div style="
                background-color: ${bgColor};
                margin: -4px -8px;
                padding: 6px 12px;
                border-top: 2px solid #2C5A9E;
            "></div>`;
        }

        // Normal Transaction Rows
        if (column.fieldname === "balance") {
            const color = data.balance > 0 ? "#E67E22" : data.balance < 0 ? "#C0392B" : "#555";
            return `<span style="color: ${color}; font-weight: 600;">${value}</span>`;
        }

        if (column.fieldname === "debit" && data.debit > 0) {
            return `<span style="color: #2568B2;">${value}</span>`;
        }

        if (column.fieldname === "credit" && data.credit > 0) {
            return `<span style="color: #1E7E34;">${value}</span>`;
        }

        return value;
    },

    "onload": function(report) {
        // Add Export to Excel button
        report.page.add_inner_button(__("Export to Excel"), function() {
            download_excel(report);
        });

        // Add Toggle Grouping button
        report.page.add_inner_button(__("Toggle Grouping"), function() {
            toggle_grouping(report);
        });

        // Add Expand All button
        report.page.add_inner_button(__("Expand All"), function() {
            expand_all(report);
        });

        // Add Collapse All button
        report.page.add_inner_button(__("Collapse All"), function() {
            collapse_all(report);
        });

        // Keyboard shortcuts
        report.page.wrapper.on("keydown", function(e) {
            if (e.ctrlKey && e.key === 'e') {
                e.preventDefault();
                download_excel(report);
            }
            if (e.ctrlKey && e.key === 'g') {
                e.preventDefault();
                toggle_grouping(report);
            }
        });
    }
};

// Download Excel function - FIXED
function download_excel(report) {
    const filters = report.get_values();

    // Validate required filters
    if (!filters.company || !filters.from_date || !filters.to_date) {
        frappe.msgprint(__("Please set Company, From Date and To Date before exporting."));
        return;
    }

    // Show loading message
    frappe.show_alert({
        message: __("Preparing Excel export..."),
        indicator: "blue"
    }, 3);

    // Build URL for download
    const params = new URLSearchParams({
        cmd: "ecclesia.ecclesia.report.customer_ledger_report.customer_ledger_report.download_excel",
        filters: JSON.stringify(filters)
    });

    // Trigger download
    window.open(`/api/method/ecclesia.ecclesia.report.customer_ledger_report.customer_ledger_report.download_excel?${params.toString()}`, "_blank");
}

// Toggle Grouping function - FIXED
function toggle_grouping(report) {
    if (!report.datatable) return;
    
    const current = report.datatable.options.tree;
    report.datatable.options.tree = !current;
    report.datatable.refresh();
    
    frappe.show_alert({
        message: current ? __("Grouping Disabled") : __("Grouping Enabled"),
        indicator: "blue"
    }, 2);
}

// Expand All function
function expand_all(report) {
    if (!report.datatable) return;
    report.datatable.rowManager.expandAllNodes();
    frappe.show_alert({
        message: __("All rows expanded"),
        indicator: "green"
    }, 2);
}

// Collapse All function
function collapse_all(report) {
    if (!report.datatable) return;
    report.datatable.rowManager.collapseAllNodes();
    frappe.show_alert({
        message: __("All rows collapsed"),
        indicator: "orange"
    }, 2);
}