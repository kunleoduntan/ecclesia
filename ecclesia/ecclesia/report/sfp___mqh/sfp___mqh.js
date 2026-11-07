// Copyright (c) Value Plus
// For license information, please see license.txt

const SFP_ROW_STYLES = {
	// ASSETS / EQUITY AND LIABILITIES
	heading: {
		color: "rgb(255, 255, 255)",
		"background-color": "rgb(0, 51, 102)",
		"font-weight": "bold",
		"letter-spacing": "0.5px",
	},
	// Non Current Assets, Current Assets, Equity, Non Current Liabilities, Current Liabilities
	section: {
		color: "rgb(0, 0, 0)",
		"background-color": "rgb(232, 236, 241)",
		"font-weight": "bold",
	},
	// Total - <section>, Total Liabilities
	total: {
		color: "rgb(0, 0, 0)",
		"background-color": "rgb(204, 229, 255)",
		"border-top": "1px solid rgb(120, 170, 220)",
		"font-weight": "bold",
	},
	// Total Assets, Total Equity & Liabilities
	grand_total: {
		color: "rgb(0, 0, 0)",
		"background-color": "rgb(99, 200, 255)",
		"border-top": "1px solid rgb(0, 51, 102)",
		"border-bottom": "3px double rgb(0, 51, 102)",
		"font-weight": "bold",
	},
	// Difference row (only shown when the statement is out of balance)
	difference: {
		color: "rgb(255, 255, 255)",
		"background-color": "rgb(192, 0, 0)",
		"font-weight": "bold",
	},
	// Profit for the year
	profit: {
		color: "rgb(0, 0, 0)",
		"background-color": "rgb(255, 248, 220)",
		"font-weight": "bold",
	},
};

frappe.query_reports["SFP - MQH"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "year",
			label: __("Fiscal Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today()),
			reqd: 1,
		},
		{
			fieldname: "frequency",
			label: __("Frequency"),
			fieldtype: "Select",
			options: ["Monthly", "Quarterly", "Half-Yearly", "Yearly"],
			default: "Monthly",
		},
		{
			fieldname: "show_only_ytd",
			label: __("Hide Zero YTD Rows"),
			fieldtype: "Check",
			default: 0,
		},
	],

	onload: function (report) {
		report.page.add_inner_button(__("Export Styled Excel"), function () {
			open_url_post("/api/method/ecclesia.ecclesia.utils.report_excel.export_report_excel", {
				report_name: report.report_name,
				filters: JSON.stringify(report.get_filter_values(true)),
			});
		});
	},

	formatter: function (value, row, column, data, default_formatter) {
		let out = default_formatter(value, row, column, data);
		if (!data) return out;

		if (column.fieldname === "account_name") {
			out = `<span style="padding-left:${(data.level || 0) * 16}px">${out}</span>`;
		}

		if (column.fieldname.endsWith("_var") && value !== null && value !== undefined && value !== "") {
			const v = flt(value, 1);
			const color = v < 0 ? "var(--red-600)" : "var(--green-600)";
			out = `<span style="color:${color}">${v}%</span>`;
		}

		const style = SFP_ROW_STYLES[data.row_type];
		if (style) {
			const css = Object.entries(style).map(([k, v]) => `${k}:${v}`).join(";");
			const align = column.fieldname === "account_name" ? "flex-start" : "flex-end";
			return `<div style="${css};width:100%;height:100%;display:flex;align-items:center;justify-content:${align};padding:0 8px;">${out}</div>`;
		}

		return out;
	},
};