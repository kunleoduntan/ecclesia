// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Financial Report Template Based"] = {

    // ── Filters ───────────────────────────────────────────────────────────────
    filters: [
        {
            fieldname: "template",
            label:     __("Template"),
            fieldtype: "Link",
            options:   "Financial Report Template",
            reqd:      1,
            get_query: () => ({ filters: { is_active: 1 } }),
            on_change() {
                const tpl = frappe.query_report.get_filter_value("template");
                if (!tpl) return;
                frappe.db.get_doc("Financial Report Template", tpl).then(doc => {
                    const bf = frappe.query_report.get_filter("show_budget");
                    if (bf) { bf.df.hidden = !doc.enable_budget_comparison; bf.refresh(); }
                    const ff = frappe.query_report.get_filter("frequency");
                    if (ff) { ff.df.hidden = !!doc.use_column_definition; ff.refresh(); }
                    
                    // Show/hide cutoff mode based on report type
                    const cf = frappe.query_report.get_filter("cutoff_mode");
                    if (cf && doc.report_type === "Balance Sheet") {
                        cf.df.hidden = false;
                        cf.refresh();
                    } else if (cf) {
                        cf.df.hidden = true;
                        cf.refresh();
                    }
                    
                    frappe.show_alert(
                        { message: __("{0} ({1})", [doc.template_name, doc.report_type]),
                          indicator: "green" }, 3
                    );
                });
            },
        },
        {
            fieldname: "company",
            label:     __("Company"),
            fieldtype: "Link",
            options:   "Company",
            reqd:      1,
            default:   frappe.defaults.get_user_default("Company"),
        },
        {
            fieldname: "year",
            label:     __("Year"),
            fieldtype: "Int",
            reqd:      1,
            default:   new Date().getFullYear(),
        },
        {
            fieldname: "frequency",
            label:     __("Frequency"),
            fieldtype: "Select",
            options:   "Monthly\nQuarterly\nHalf-Yearly",
            default:   "Monthly",
            reqd:      1,
            description: "Not used when template has Custom Column Definition enabled.",
        },
        {
            fieldname: "cutoff_mode",
            label:     __("Cutoff Mode"),
            fieldtype: "Select",
            options:   "Today (Partial Current Period)\nEnd of Period (Full Periods)\nCustom Date",
            default:   "Today (Partial Current Period)",
            hidden:    1,
            description: "For Balance Sheet: 'Today' shows current period up to today, past periods in full. 'End of Period' shows all periods in full.",
            on_change() {
                const mode = frappe.query_report.get_filter_value("cutoff_mode");
                const customDateFilter = frappe.query_report.get_filter("custom_cutoff_date");
                if (customDateFilter) {
                    customDateFilter.df.hidden = (mode !== "Custom Date");
                    customDateFilter.refresh();
                }
            },
        },
        {
            fieldname: "custom_cutoff_date",
            label:     __("Custom Cutoff Date"),
            fieldtype: "Date",
            hidden:    1,
            description: "For Balance Sheet: Show data up to this date for current period, full periods for past periods.",
        },
        {
            fieldname: "show_budget",
            label:     __("Show Budget Comparison"),
            fieldtype: "Check",
            default:   0,
            hidden:    1,
        },
        {
            fieldname: "budget_plan",
            label:     __("Budget Plan"),
            fieldtype: "Link",
            options:   "Budget Plan",
            depends_on: "eval:doc.show_budget==1",
            get_query() {
                return {
                    filters: {
                        company:     frappe.query_report.get_filter_value("company"),
                        fiscal_year: frappe.query_report.get_filter_value("year"),
                        docstatus:   1,
                    },
                };
            },
        },
    ],

    // ── Toolbar ───────────────────────────────────────────────────────────────
    onload(report) {
        report.page.add_inner_button(__("Manage Templates"), () => {
            frappe.set_route("List", "Financial Report Template");
        });

        report.page.add_inner_button(__("New Template"), () => {
            frappe.new_doc("Financial Report Template");
        });

        report.page.add_inner_button(__("Export to Excel"), () => {
            const f = report.get_values();
            if (!f.template) { frappe.msgprint(__("Please select a template first.")); return; }
            const p = new URLSearchParams({
                template_name: f.template,
                company:       f.company,
                year:          f.year,
                frequency:     f.frequency || "Monthly",
                cutoff_mode:   f.cutoff_mode || "Today (Partial Current Period)",
                custom_cutoff_date: f.custom_cutoff_date || "",
                show_budget:   f.show_budget || 0,
                budget_plan:   f.budget_plan || "",
            });
            const w = window.open(frappe.urllib.get_full_url(
                "/api/method/ecclesia.ecclesia.report"
                + ".financial_report_template_based.excel_export.download_excel?" + p
            ));
            if (!w) frappe.msgprint(__("Please allow popups for this site."));
        }, __("Export"));

        report.page.add_inner_button(__("Help"), () => {
            frappe.msgprint({
                title: __("Financial Report — Help"),
                wide:  true,
                message: `
<div style="padding:12px;font-size:13px;line-height:1.9">
<h4>Balance Sheet vs P&L</h4>
<ul>
<li><b>Balance Sheet</b>: columns show <em>accumulated closing balance</em>
up to the end of that period ("as at" position).</li>
<li><b>P&L / Cash Flow</b>: columns show <em>period movement</em>
(activity during that month/quarter).</li>
</ul>

<h4>Cutoff Mode (Balance Sheet only)</h4>
<ul>
<li><b>Today (Partial Current Period)</b>: Current period shows data up to today's date.
Past periods show full periods. Prior year comparison uses same day-of-month.</li>
<li><b>End of Period (Full Periods)</b>: All periods show full month/quarter data
(legacy behavior).</li>
<li><b>Custom Date</b>: Specify a custom cutoff date for the current period.</li>
</ul>

<h4>Retained Earnings</h4>
<p>Set <code>line_type = Retained Earnings</code>. The system automatically
accumulates all Income and Expense GL entries from inception up to each
period-end date (or cutoff date for current period). No formula needed.</p>

<h4>Calculated Lines</h4>
<p>Set <code>line_type = Calculated</code> and enter a formula using other
line codes: <code>REV - COS</code>, <code>GP - OPEX</code>, etc.
Each line code must be set on the referenced line.</p>

<h4>Column Codes (Custom Column Definition)</h4>
<table style="border-collapse:collapse;font-size:12px;width:100%">
<tr style="background:#f0f0f0">
  <th style="padding:4px 8px;border:1px solid #ddd">Code</th>
  <th style="padding:4px 8px;border:1px solid #ddd">Meaning</th>
</td>

${[
  ["M1–M12",    "Specific month of selected year"],
  ["Q1–Q4",     "Quarter 1–4"],
  ["H1, H2",    "Half-year 1 and 2"],
  ["YTD",       "Year to date (up to cutoff date for current period, full for past)"],
  ["FY / Y1",   "Full year (Jan–Dec)"],
  ["-M3",       "Prior year March"],
  ["M1:M6",     "Range: Jan through Jun"],
  ["Q1_BUD",    "Q1 Budget"],
].map(([c,d]) => `<tr><td style="padding:4px 8px;border:1px solid #ddd"><code>${c}</code></td>
<td style="padding:4px 8px;border:1px solid #ddd">${d}</td></tr>`).join("")}
</table>
</div>`,
            });
        }, __("Actions"));
    },

    // ── Cell formatter ────────────────────────────────────────────────────────
    formatter(value, row, column, data, default_formatter) {

        // ── 1. Blank cell for Header / Blank rows on numeric columns ──────────
        const isHeaderOrBlank =
            data && (data._is_header || data._is_blank ||
                (data.account_name !== undefined &&
                 typeof data.account_name === "string" &&
                 data.account_name === ""));

        if (column.fieldname !== "account_name" && value === null) {
            return "";   // render nothing — no 0.00, no "undefined"
        }

        // Apply Frappe's default formatting first
        value = default_formatter(value, row, column, data);

        if (!data) return value;

        // ── 2. Collect styles from _style string set by Python ─────────────────
        const css = {};

        if (data._style) {
            const s = data._style;
            const bg = s.match(/background-color\s*:\s*([^;]+)/i);
            if (bg) css["background-color"] = bg[1].trim();
            if (/font-weight\s*:\s*bold/i.test(s)) css["font-weight"] = "bold";
            const bt = s.match(/border-top\s*:\s*([^;]+)/i);
            if (bt) css["border-top"] = bt[1].trim();
            const bb = s.match(/border-bottom\s*:\s*([^;]+)/i);
            if (bb) css["border-bottom"] = bb[1].trim();
        }

        // ── 3. Account name: indentation via padding ───────────────────────────
        if (column.fieldname === "account_name" && typeof value === "string") {
            const groups = (value.match(/&nbsp;&nbsp;&nbsp;&nbsp;/g) || []).length;
            if (groups > 0) {
                const clean = value.replace(/(&nbsp;)+/g, "");
                const indent = groups * 20;
                if (Object.keys(css).length) {
                    const cssStr = Object.entries(css).map(([k, v]) => `${k}:${v}`).join(";");
                    return `<span style="${cssStr};display:block;padding-left:${indent}px">${clean}</span>`;
                }
                return `<span style="display:block;padding-left:${indent}px">${clean}</span>`;
            }
            // No indent — still apply row styles if any
            if (Object.keys(css).length) {
                const cssStr = Object.entries(css).map(([k, v]) => `${k}:${v}`).join(";");
                return `<span style="${cssStr}">${value}</span>`;
            }
            return value;
        }

        // ── 4. Currency / Float columns: align right, negative = red ──────────
        if (column.fieldtype === "Currency" || column.fieldtype === "Float") {
            // Right-align using text-align, NOT flex (flex overrides column alignment)
            css["text-align"] = "right";
            css["display"]    = "block";
            css["width"]      = "100%";
            css["padding-right"] = "8px";

            const num = parseFloat(String(value).replace(/[^0-9.-]/g, ""));
            if (!isNaN(num) && num < 0) {
                const bg = css["background-color"] || "";
                // Don't apply red on dark backgrounds
                if (!/darkblue|navy|#[0-3][0-9a-f]{5}/i.test(bg)) {
                    css["color"] = "#cc0000";
                }
            }
        }

        // ── 5. Percent columns: colour by direction and magnitude ──────────────
        if (column.fieldtype === "Percent" && value !== null && value !== "") {
            const pct = parseFloat(String(value).replace(/[^0-9.-]/g, ""));
            if (!isNaN(pct)) {
                const abs = Math.abs(pct);
                css["color"]       = pct >= 0 ? "#1a7340" : "#cc0000";
                css["font-weight"] = abs > 20 ? "bold" : (css["font-weight"] || "normal");
                css["text-align"]  = "right";
                css["display"]     = "block";
                css["width"]       = "100%";
                css["padding-right"] = "8px";
                if (abs > 20 && !css["background-color"])
                    css["background-color"] = pct >= 0 ? "#d4edda" : "#f8d7da";
            }
        }

        if (!Object.keys(css).length) return value;
        const cssStr = Object.entries(css).map(([k, v]) => `${k}:${v}`).join(";");
        return `<span style="${cssStr}">${value}</span>`;
    },
};