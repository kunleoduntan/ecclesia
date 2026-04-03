// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt
/* eslint-disable */


// Audit Universe Coverage — Report Filters

frappe.query_reports["Audit Universe Coverage"] = {
	filters: [
		{
			fieldname: "risk_level",
			label: __("Risk Level"),
			fieldtype: "Select",
			options: "\nCritical\nHigh\nMedium\nLow",
		},
		{
			fieldname: "classification",
			label: __("Classification"),
			fieldtype: "Select",
			options: "\nFinancial\nProcurement\nHR & Payroll\nInventory & Stock\nSales\nCustom",
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "coverage_status") {
			const colors = {
				"✅ Current":            "#27ae60",
				"🟡 Due Soon":           "#f39c12",
				"🟠 Overdue":            "#e67e22",
				"🔴 Severely Overdue":   "#c0392b",
				"⚠️ Never Audited":      "#8e44ad",
			};
			const c = colors[data.coverage_status];
			if (c) value = `<span style="color:${c};font-weight:700;">${data.coverage_status}</span>`;
		}
		if (column.fieldname === "risk_level") {
			const colors = { Critical:"#c0392b", High:"#e67e22", Medium:"#f39c12", Low:"#27ae60" };
			const c = colors[data.risk_level];
			if (c) value = `<span style="color:${c};font-weight:700;">${data.risk_level}</span>`;
		}
		if (column.fieldname === "days_since_audit") {
			if (data.days_since_audit === 9999) {
				value = `<span style="color:#8e44ad;font-weight:700;">Never</span>`;
			} else if (data.days_since_audit > 365) {
				value = `<span style="color:#c0392b;font-weight:700;">${data.days_since_audit}</span>`;
			}
		}
		return value;
	},
};