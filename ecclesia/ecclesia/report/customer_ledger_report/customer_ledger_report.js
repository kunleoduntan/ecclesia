// Copyright (c) 2024, Ecclesia and contributors
// For license information, please see license.txt

// ── Palette (soft tints so it works in light and dark desk themes) ──
const CLR = {
    accent:   "#1F3A5F",                 // navy
    band:     "rgba(31, 58, 95, 0.10)",  // customer header band
    subtle:   "rgba(31, 58, 95, 0.05)",  // subtotal band
    line:     "rgba(31, 58, 95, 0.35)",
    debit:    "#1D4ED8",                 // blue
    credit:   "#0F766E",                 // teal
    owing:    "#B45309",                 // amber  (customer owes)
    negative: "#B91C1C",                 // red    (customer in credit)
    muted:    "#6B7280"
};

frappe.query_reports["Customer Ledger Report"] = {
    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
            reqd: 1
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            reqd: 1
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1
        },
        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "Link",
            options: "Customer"
        }
    ],

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        // spacer rows / empty rows
        if (!data || !Object.keys(data).length) return value;

        const f = column.fieldname;
        const money = (v) => frappe.format(v || 0, { fieldtype: "Currency", options: "currency" }, {}, data);
        const esc = (v) => frappe.utils.escape_html(v || "");
        const cell = (inner, css = "") =>
            `<div style="margin:-4px -8px;padding:7px 10px;${css}">${inner}</div>`;
        const balColor = (b) => (b > 0 ? CLR.owing : b < 0 ? CLR.negative : CLR.muted);

        // ── Customer header band ───────────────────────────────────
        if (data.is_header_row) {
            const band = `background:${CLR.band};`;
            const accent = f === "posting_date" ? `border-left:3px solid ${CLR.accent};` : "";

            if (f === "customer_name")
                return cell(esc(data.customer_name), `${band}font-weight:700;font-size:13px;`);
            if (f === "customer")
                return cell(esc(data.customer), `${band}color:${CLR.muted};font-size:11px;`);
            if (f === "description" && data.balance)
                return cell("Opening balance", `${band}color:${CLR.muted};font-size:11px;text-align:right;`);
            if (f === "balance" && data.balance)
                return cell(money(data.balance), `${band}font-weight:600;text-align:right;color:${balColor(data.balance)};`);
            return cell("", band + accent);
        }

        // ── Subtotal row ───────────────────────────────────────────
        if (data.is_total_row) {
            const base = `background:${CLR.subtle};border-top:1px solid ${CLR.line};font-weight:700;`;
            if (f === "customer_name") return cell(esc(data.customer_name), base);
            if (f === "description")   return cell(esc(data.description), `${base}color:${CLR.muted};font-weight:500;text-align:right;`);
            if (f === "debit")         return cell(money(data.debit),  `${base}color:${CLR.debit};text-align:right;`);
            if (f === "credit")        return cell(money(data.credit), `${base}color:${CLR.credit};text-align:right;`);
            if (f === "balance")       return cell(money(data.balance), `${base}color:${balColor(data.balance)};text-align:right;`);
            return cell("", base);
        }

        // ── Grand total row ────────────────────────────────────────
        if (data.is_grand_total) {
            const base = `background:${CLR.accent};color:#fff;font-weight:700;padding:9px 10px;`;
            const wrap = (inner, extra = "") => `<div style="margin:-4px -8px;${base}${extra}">${inner}</div>`;
            if (f === "description") return wrap(esc(data.description), "text-align:right;");
            if (f === "debit")       return wrap(money(data.debit),   "text-align:right;");
            if (f === "credit")      return wrap(money(data.credit),  "text-align:right;");
            if (f === "balance")     return wrap(money(data.balance), "text-align:right;font-size:13px;");
            return wrap("");
        }

        // ── Normal transaction rows ────────────────────────────────
        // customer is already shown in the header band, so keep rows clean
        if (f === "customer" || f === "customer_name") return "";

        if (f === "debit" || f === "credit") {
            const v = data[f];
            if (!v) return `<span style="color:${CLR.muted};opacity:.4;">${value}</span>`;
            return `<span style="color:${f === "debit" ? CLR.debit : CLR.credit};">${value}</span>`;
        }
        if (f === "balance")
            return `<span style="color:${balColor(data.balance)};font-weight:600;">${value}</span>`;
        if (f === "voucher_type" || f === "against_voucher")
            return `<span style="color:${CLR.muted};">${value}</span>`;

        return value;
    },

    onload: function (report) {
        report.page.add_inner_button(__("Export to Excel"), () => download_excel(report));

        report.page.wrapper.on("keydown", function (e) {
            if (e.ctrlKey && e.key === "e") {
                e.preventDefault();
                download_excel(report);
            }
        });
    }
};

function download_excel(report) {
    const filters = report.get_values();

    if (!filters.company || !filters.from_date || !filters.to_date) {
        frappe.msgprint(__("Please set Company, From Date and To Date before exporting."));
        return;
    }

    frappe.show_alert({ message: __("Preparing Excel export..."), indicator: "blue" }, 3);

    const params = new URLSearchParams({ filters: JSON.stringify(filters) });
    window.open(
        `/api/method/ecclesia.ecclesia.report.customer_ledger_report.customer_ledger_report.download_excel?${params.toString()}`,
        "_blank"
    );
}