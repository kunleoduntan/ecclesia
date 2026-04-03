// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt
/* eslint-disable */


// Debug version
frappe.query_reports["Financial Report by Dimension Debug"] = {
    "filters": [
        {
            "fieldname": "template",
            "label": "Financial Report Template",
            "fieldtype": "Link",
            "options": "Financial Report Template",
            "reqd": 1
        },
        {
            "fieldname": "company",
            "label": "Company",
            "fieldtype": "Link",
            "options": "Company",
            "reqd": 1,
            "default": frappe.defaults.get_user_default("Company")
        },
        {
            "fieldname": "from_date",
            "label": "From Date",
            "fieldtype": "Date",
            "default": frappe.datetime.month_start(),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": "To Date",
            "fieldtype": "Date",
            "default": frappe.datetime.month_end(),
            "reqd": 1
        },
        {
            "fieldname": "parent_cost_center",
            "label": "Parent Cost Center",
            "fieldtype": "Link",
            "options": "Cost Center",
            "get_query": function() {
                return {"filters": {"is_group": 1}};
            }
        }
    ]
};