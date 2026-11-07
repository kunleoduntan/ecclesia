// Copyright (c) Value Plus
// For license information, please see license.txt

// Colours (same as the Excel summary)
const SCI_BLUE = "#B7DEE8";
const SCI_GREY = "#E8ECF1";
const SCI_NAVY = "#003366";

// Row types come from the .py: section | line | total | summary | grand_total | profit | spacer
// Each cell carries a marker class (sci-<row_type>) and the CSS colours the WHOLE cell from it.
const SCI_CSS = `
	/* whole-cell colouring, incl. spacer columns */
	.dt-cell:has(.sci-section) { background: ${SCI_GREY} !important; font-weight: 700; color: #000; }
	.dt-cell:has(.sci-total),
	.dt-cell:has(.sci-grand_total),
	.dt-cell:has(.sci-profit) { background: ${SCI_BLUE} !important; font-weight: 700; color: #000; }
	.dt-cell:has(.sci-profit) {
		border-top: 1px solid ${SCI_NAVY} !important;
		border-bottom: 3px double ${SCI_NAVY} !important;
	}
	/* keep the colour on hover / selection */
	.dt-row:hover .dt-cell:has(.sci-section) { background: ${SCI_GREY} !important; }
	.dt-row:hover .dt-cell:has(.sci-total),
	.dt-row:hover .dt-cell:has(.sci-grand_total),
	.dt-row:hover .dt-cell:has(.sci-profit) { background: ${SCI_BLUE} !important; }
	/* Excel-like look */
	.dt-cell { border-color: #d0d7de; }
	.dt-cell__content { font-size: 13px; }
	.sci-cell { display: block; width: 100%; }
`;

// Amounts as plain numbers (53,034,087.20) like the Excel; set true to show the currency symbol
const SCI_SHOW_CURRENCY_SYMBOL = false;
const SCI_AMOUNT_PRECISION = 2;

// px of indent per `level` on the Account Name column
const SCI_INDENT_PX = 16;

frappe.query_reports["SCI - Report"] = {
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
			fieldname: "filter_based_on",
			label: __("Filter Based On"),
			fieldtype: "Select",
			options: ["Fiscal Year", "Date Range"],
			default: "Fiscal Year",
			reqd: 1,
			on_change: function () {
				const based_on = frappe.query_report.get_filter_value("filter_based_on");
				frappe.query_report.toggle_filter_display("from_fiscal_year", based_on === "Date Range");
				frappe.query_report.toggle_filter_display("to_fiscal_year", based_on === "Date Range");
				frappe.query_report.toggle_filter_display("period_start_date", based_on === "Fiscal Year");
				frappe.query_report.toggle_filter_display("period_end_date", based_on === "Fiscal Year");
				frappe.query_report.refresh();
			},
		},
		{
			fieldname: "from_fiscal_year",
			label: __("Start Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today()),
		},
		{
			fieldname: "to_fiscal_year",
			label: __("End Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today()),
		},
		{
			fieldname: "period_start_date",
			label: __("Start Date"),
			fieldtype: "Date",
			hidden: 1,
			default: frappe.datetime.year_start(),
		},
		{
			fieldname: "period_end_date",
			label: __("End Date"),
			fieldtype: "Date",
			hidden: 1,
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "frequency",
			label: __("Frequency"),
			fieldtype: "Select",
			options: ["Monthly", "Quarterly", "Half-Yearly", "Yearly"],
			default: "Monthly",
		},
		{
			// must match the keys of COMPARISONS in the .py (plus "None")
			fieldname: "compare_with",
			label: __("Compare With"),
			fieldtype: "Select",
			options: ["Previous Year", "Previous Period", "None"],
			default: "Previous Year",
		},
		{
			fieldname: "show_growth",
			label: __("Show Growth %"),
			fieldtype: "Check",
			default: 1,
		},
		{
			fieldname: "show_total",
			label: __("Show Year To Date"),
			fieldtype: "Check",
			default: 1,
		},
		{
			fieldname: "cost_center",
			label: __("Cost Center"),
			fieldtype: "Link",
			options: "Cost Center",
			get_query: function () {
				return { filters: { company: frappe.query_report.get_filter_value("company") } };
			},
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			options: "Project",
		},
		{
			fieldname: "hide_detail",
			label: __("Hide Details"),
			fieldtype: "Check",
			default: 0,
		},
		{
			fieldname: "hide_zero_accounts",
			label: __("Hide Zero Balance Accounts"),
			fieldtype: "Check",
			default: 0,
		},
	],

	onload: function (report) {
		frappe.dom.set_style(SCI_CSS, "sci-report-style");

		report.page.add_inner_button(__("Export Styled Excel"), function () {
			open_url_post("/api/method/ecclesia.ecclesia.utils.report_excel.export_report_excel", {
				report_name: report.report_name,
				filters: JSON.stringify(report.get_filter_values(true)),
			});
		});
	},

	get_datatable_options: function (options) {
		return Object.assign(options, { cellHeight: 30 });
	},

	formatter: function (value, row, column, data, default_formatter) {
		let out = default_formatter(value, row, column, data);
		if (!data) return out;

		const field = column.fieldname || "";
		const is_growth = field.endsWith("_var") || field === "achievement_ytd_pct";
		const is_amount = field !== "account_name" && !field.startsWith("sp_") && !is_growth;

		if (is_amount && !SCI_SHOW_CURRENCY_SYMBOL) {
			out =
				value === null || value === undefined || value === ""
					? ""
					: format_number(value, null, SCI_AMOUNT_PRECISION);
		}

		if (field === "account_name") {
			out = `<span style="padding-left:${(data.level || 0) * SCI_INDENT_PX}px">${out}</span>`;
		}

		if (is_growth && value !== null && value !== undefined && value !== "") {
			const precision = column.precision !== undefined ? column.precision : 1;
			const v = flt(value, precision);
			const color = v < 0 ? "var(--red-600)" : "var(--green-600)";
			out = `<span style="color:${color}">${v}%</span>`;
		}

		// marker class: the CSS above colours the whole cell from it
		const align = field === "account_name" ? "left" : "right";
		return `<span class="sci-cell sci-${data.row_type || "line"}" style="text-align:${align}">${out}</span>`;
	},
};