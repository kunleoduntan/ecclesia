// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt
/* eslint-disable */



// Open Findings by Risk — Report Filters

frappe.query_reports["Open Findings by Risk"] = {
	filters: [
		{
			fieldname: "risk_rating",
			label: __("Risk Rating"),
			fieldtype: "Select",
			options: "\nCritical\nHigh\nMedium\nLow",
		},
		{
			fieldname: "engagement",
			label: __("Audit Engagement"),
			fieldtype: "Link",
			options: "Audit Engagement",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "risk_rating") {
			const colors = { Critical:"#c0392b", High:"#e67e22", Medium:"#f39c12", Low:"#27ae60" };
			const c = colors[data.risk_rating];
			if (c) value = `<span style="color:${c};font-weight:700;">${data.risk_rating}</span>`;
		}
		if (column.fieldname === "days_overdue" && data.days_overdue > 0) {
			value = `<span style="color:#e74c3c;font-weight:600;">${data.days_overdue}</span>`;
		}
		if (column.fieldname === "financial_impact" && data.financial_impact > 0) {
			value = `<span style="color:#c0392b;">${value}</span>`;
		}
		return value;
	},
};