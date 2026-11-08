// Copyright (c) 2026, Value Plus and contributors
// For license information, please see license.txt

// Dotted path of the whitelisted export function (app.module.report.report.function)
const AMORT_EXPORT_METHOD =
	"general.general_biz_apps.report.amortization_schedule_report.amortization_schedule_report.export_excel";

frappe.query_reports["Amortization Schedule Report"] = {
	onload: function (report) {
		report.page.add_inner_button(__("Formatted Excel"), () => {
			const filters = report.get_filter_values(true);
			if (!filters) return;
			open_url_post(frappe.request.url, {
				cmd: AMORT_EXPORT_METHOD,
				filters: JSON.stringify(filters),
			});
		});
	},

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
			fieldname: "view",
			label: __("View"),
			fieldtype: "Select",
			options: "Detailed Schedule\nInvoice Summary\nMonthly Summary",
			default: "Detailed Schedule",
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default:
				frappe.defaults.get_user_default("year_start_date") ||
				moment().startOf("year").format("YYYY-MM-DD"),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default:
				frappe.defaults.get_user_default("year_end_date") ||
				moment().endOf("year").format("YYYY-MM-DD"),
		},
		{
			fieldname: "supplier",
			label: __("Supplier"),
			fieldtype: "Link",
			options: "Supplier",
		},
		{
			fieldname: "purchase_invoice",
			label: __("Purchase Invoice"),
			fieldtype: "Link",
			options: "Purchase Invoice",
			get_query: () => ({
				filters: {
					custom_is_amortized_cost: 1,
					docstatus: ["<", 2],
					company: frappe.query_report.get_filter_value("company"),
				},
			}),
		},
		{
			fieldname: "expense_account",
			label: __("Expense Account"),
			fieldtype: "Link",
			options: "Account",
			get_query: () => ({
				filters: {
					company: frappe.query_report.get_filter_value("company"),
					is_group: 0,
				},
			}),
		},
		{
			fieldname: "cost_center",
			label: __("Cost Center"),
			fieldtype: "Link",
			options: "Cost Center",
			get_query: () => ({
				filters: {
					company: frappe.query_report.get_filter_value("company"),
				},
			}),
		},
		{
			fieldname: "frequency",
			label: __("Frequency"),
			fieldtype: "Select",
			options: "\nMonthly\nQuarterly\nHalf-Yearly\nYearly\nFreehand",
		},
		{
			fieldname: "status",
			label: __("Instalment Status"),
			fieldtype: "Select",
			options: "\nPosted\nOverdue\nScheduled",
		},
		{
			fieldname: "exceptions_only",
			label: __("Exceptions Only"),
			fieldtype: "Check",
		},
		{
			fieldname: "trace_je",
			label: __("Trace to Journal Entries"),
			fieldtype: "Check",
		},
		{
			fieldname: "include_draft",
			label: __("Include Draft Invoices"),
			fieldtype: "Check",
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		if (!data) {
			return default_formatter(value, row, column, data);
		}

		// Total row: bold, and never render "Total" as a document link
		if (data.is_total_row) {
			if (["Link", "Data", "Date"].includes(column.fieldtype)) {
				return `<strong>${frappe.utils.escape_html(value || "")}</strong>`;
			}
			return `<strong>${default_formatter(value, row, column, data)}</strong>`;
		}

		const formatted = default_formatter(value, row, column, data);

		if (column.fieldname === "status" && value) {
			const pill = {
				Posted: "green",
				Completed: "green",
				Overdue: "red",
				Scheduled: "blue",
				"In Progress": "orange",
				"Not Started": "gray",
			}[value] || "gray";
			return `<span class="indicator-pill ${pill} filterable no-indicator-dot ellipsis">${frappe.utils.escape_html(value)}</span>`;
		}

		if (column.fieldname === "flags" && value) {
			return `<span style="color: var(--red-600); font-weight: 600;">${formatted}</span>`;
		}

		if (["variance", "charge_overdue"].includes(column.fieldname) && flt(value) !== 0) {
			return `<span style="color: var(--red-600); font-weight: 600;">${formatted}</span>`;
		}

		if (["closing", "closing_balance"].includes(column.fieldname) && flt(value) < 0) {
			return `<span style="color: var(--red-600);">${formatted}</span>`;
		}

		return formatted;
	},
};
