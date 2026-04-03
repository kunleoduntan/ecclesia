// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt
/* eslint-disable */



// CAP Aging — Report Filters

frappe.query_reports["Cap Aging"] = {
	filters: [
		{
			fieldname: "risk_rating",
			label: __("Risk Rating"),
			fieldtype: "Select",
			options: "\nCritical\nHigh\nMedium\nLow",
		},
		{
			fieldname: "action_owner",
			label: __("Action Owner"),
			fieldtype: "Link",
			options: "User",
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "aging_bucket") {
			const colors = {
				"Current":        "#27ae60",
				"1–30 days":      "#f39c12",
				"31–60 days":     "#e67e22",
				"61–90 days":     "#e74c3c",
				"90+ days":       "#c0392b",
				"No Due Date":    "#95a5a6",
			};
			const c = colors[data.aging_bucket];
			if (c) value = `<span style="color:${c};font-weight:700;">${data.aging_bucket}</span>`;
		}
		if (column.fieldname === "days_overdue" && data.days_overdue > 0) {
			const c = data.days_overdue > 90 ? "#c0392b" : data.days_overdue > 30 ? "#e74c3c" : "#e67e22";
			value = `<span style="color:${c};font-weight:700;">${data.days_overdue}</span>`;
		}
		if (column.fieldname === "risk_rating") {
			const colors = { Critical:"#c0392b", High:"#e67e22", Medium:"#f39c12", Low:"#27ae60" };
			const c = colors[data.risk_rating];
			if (c) value = `<span style="color:${c};font-weight:700;">${data.risk_rating}</span>`;
		}
		return value;
	},
};