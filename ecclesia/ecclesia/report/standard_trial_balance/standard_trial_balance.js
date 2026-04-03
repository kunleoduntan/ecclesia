// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt
/* eslint-disable */



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
        
        // Bold formatting for total row
        if (data && data.is_total_row) {
            value = value.bold();
        }
        
        // Color coding for balance columns
        if (column.fieldname === "balance" && data && !data.is_total_row) {
            if (flt(data.balance) > 0) {
                value = `<span style="color: #28a745;">${value}</span>`;
            } else if (flt(data.balance) < 0) {
                value = `<span style="color: #dc3545;">${value}</span>`;
            }
        }
        
        return value;
    },
    
    onload: function(report) {
        // Add custom buttons
        report.page.add_inner_button(__("Export to Excel"), function() {
            report.export_report("xlsx");
        });
        
        report.page.add_inner_button(__("Export to PDF"), function() {
            report.export_report("pdf");
        });
        
        report.page.add_inner_button(__("Print"), function() {
            report.print_report();
        });
        
        // Add refresh button with custom styling
        report.page.set_primary_action(__("Refresh"), function() {
            report.refresh();
        }, "octicon octicon-sync");
    }
};

