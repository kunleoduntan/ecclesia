// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt
/* eslint-disable */


frappe.query_reports["Customer Outstanding with Receipts"] = {
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
            "fieldname": "customer_id",
            "label": __("Customer"),
            "fieldtype": "Link",
            "options": "Customer"
        },
        {
            "fieldname": "aging_days",
            "label": __("Aging Days"),
            "fieldtype": "Select",
            "options": "\n0-30\n31-60\n61-90\nOver 90"
        }
    ],
    
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        if (column.fieldname == "over_90" && data && data.over_90 > 0) {
            value = `<span style="color: red; font-weight: bold;">${value}</span>`;
        }
        
        if (column.fieldname == "days_61_90" && data && data.days_61_90 > 0) {
            value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
        }
        
        if (column.fieldname == "receipts_last_30_days" && data && data.receipts_last_30_days > 0) {
            value = `<span style="color: green; font-weight: bold;">${value}</span>`;
        }
        
        return value;
    },
    
    "onload": function(report) {
        report.page.add_inner_button(__("Send Reminder"), function() {
            let selected = report.get_checked_items();
            if (selected.length === 0) {
                frappe.msgprint(__("Please select at least one customer"));
                return;
            }
            
            frappe.call({
                method: "general.general_biz_apps.doctype.receipts.receipt_api.send_payment_reminders",
                args: {
                    customers: selected.map(d => d.customer)
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.msgprint(__("Reminders sent successfully"));
                    }
                }
            });
        });
        
        report.page.add_inner_button(__("Export Outstanding"), function() {
            frappe.utils.make_event("submit");
        });
    },
    
    "get_datatable_options": function(options) {
        return Object.assign(options, {
            checkboxColumn: true,
            events: {
                onCheckRow: function(data) {
                    // Handle row selection
                }
            }
        });
    }
};
