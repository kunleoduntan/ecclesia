// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt
/* eslint-disable */


frappe.query_reports["Receipt Summary by Customer"] = {
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
            "fieldname": "customer_id",
            "label": __("Customer"),
            "fieldtype": "Link",
            "options": "Customer"
        }
    ],
    
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        if (column.fieldname == "total_received" && data) {
            if (data.total_received > 100000) {
                value = `<span style="color: green; font-weight: bold;">${value}</span>`;
            }
        }
        
        if (column.fieldname == "customer_name" && data) {
            value = `<a href="/app/customer/${data.customer_id}">${value}</a>`;
        }
        
        return value;
    },
    
    "onload": function(report) {
        report.page.add_inner_button(__("View Details"), function() {
            let selected = report.get_checked_items();
            if (selected.length === 0) {
                frappe.msgprint(__("Please select at least one customer"));
                return;
            }
            
            if (selected.length === 1) {
                frappe.set_route("query-report", "Receipt Register", {
                    customer_id: selected[0].customer_id,
                    from_date: report.get_values().from_date,
                    to_date: report.get_values().to_date
                });
            }
        });
        
        report.page.add_inner_button(__("Show Summary"), function() {
            let data = report.data;
            if (data && data.length > 0) {
                let total_receipts = data.reduce((sum, d) => sum + (d.receipt_count || 0), 0);
                let total_amount = data.reduce((sum, d) => sum + (d.total_received || 0), 0);
                let total_wht = data.reduce((sum, d) => sum + (d.total_wht || 0), 0);
                
                frappe.msgprint({
                    title: __("Summary"),
                    message: `
                        <table class="table table-bordered">
                            <tr>
                                <th>${__("Total Customers")}</th>
                                <td>${data.length}</td>
                            </tr>
                            <tr>
                                <th>${__("Total Receipts")}</th>
                                <td>${total_receipts}</td>
                            </tr>
                            <tr>
                                <th>${__("Total Amount Received")}</th>
                                <td>${format_currency(total_amount)}</td>
                            </tr>
                            <tr>
                                <th>${__("Total WHT")}</th>
                                <td>${format_currency(total_wht)}</td>
                            </tr>
                            <tr>
                                <th>${__("Net Amount")}</th>
                                <td>${format_currency(total_amount - total_wht)}</td>
                            </tr>
                        </table>
                    `,
                    wide: true
                });
            }
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

