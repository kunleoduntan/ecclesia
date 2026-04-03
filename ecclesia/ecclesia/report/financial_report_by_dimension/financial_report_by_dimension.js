// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

frappe.query_reports["Financial Report by Dimension"] = {
    filters: [
        {
            fieldname: "template",
            label: __("Financial Report Template"),
            fieldtype: "Link",
            options: "Financial Report Template",
            reqd: 1,
            get_query: () => ({ filters: { is_active: 1 } })
        },
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            reqd: 1,
            default: frappe.defaults.get_user_default("Company")
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_start(),
            reqd: 1
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_end(),
            reqd: 1
        },
        {
            fieldname: "dimension_type",
            label: __("Dimension Type"),
            fieldtype: "Select",
            options: "Cost Center\nBranch\nProject",
            default: "Cost Center",
            reqd: 1
        },
        {
            fieldname: "parent_cost_center",
            label: __("Parent Cost Center"),
            fieldtype: "Link",
            options: "Cost Center",
            depends_on: "eval:doc.dimension_type=='Cost Center'",
            get_query: () => ({ filters: { is_group: 1 } })
        },
        {
            fieldname: "specific_cost_centers",
            label: __("Specific Cost Centers"),
            fieldtype: "MultiSelectList",
            depends_on: "eval:doc.dimension_type=='Cost Center'",
            get_data: txt =>
                frappe.db.get_link_options("Cost Center", txt, {
                    is_group: 0,
                    company: frappe.query_report.get_filter_value("company")
                })
        },
        {
            fieldname: "specific_branches",
            label: __("Branches"),
            fieldtype: "MultiSelectList",
            depends_on: "eval:doc.dimension_type=='Branch'",
            get_data: txt => frappe.db.get_link_options("Branch", txt)
        },
        {
            fieldname: "specific_projects",
            label: __("Projects"),
            fieldtype: "MultiSelectList",
            depends_on: "eval:doc.dimension_type=='Project'",
            get_data: txt =>
                frappe.db.get_link_options("Project", txt, {
                    company: frappe.query_report.get_filter_value("company"),
                    status: "Open"
                })
        },
        { fieldname: "show_totals", label: __("Show Totals"), fieldtype: "Check", default: 0 }
    ],

    /* ================================================================
       FORMATTER
       Full port from Financial Report Template Based.
       Reads the _style string written by apply_row_styling() in Python
       and applies: background-color, font-weight, border-top,
       border-bottom, indent, red negatives, variance % colours.
    ================================================================ */

    formatter(value, row, column, data, default_formatter) {
        let cell_style = {};

        // Default first
        value = default_formatter(value, row, column, data);

        // Parse _style string from Python (always cast to string to avoid TypeError)
        if (data && data._style) {
            let s = String(data._style);

            // Background color
            if (s.includes("background-color")) {
                let m = s.match(/background-color:\s*([^;]+)/);
                if (m) cell_style["background-color"] = m[1].trim();
            }

            // Font weight
            if (s.includes("font-weight: bold")) {
                cell_style["font-weight"] = "bold";
            }

            // Border top
            if (s.includes("border-top:")) {
                let m = s.match(/border-top:\s*([^;]+)/);
                if (m) cell_style["border-top"] = m[1].trim();
            }

            // Border bottom
            if (s.includes("border-bottom:")) {
                let m = s.match(/border-bottom:\s*([^;]+)/);
                if (m) cell_style["border-bottom"] = m[1].trim();
            }
        }

        // Indentation on account_name
        if (column.fieldname === "account_name" && typeof value === "string") {
            let indent  = 0;
            let stripped = value;
            while (stripped.startsWith("&nbsp;") || stripped.startsWith("    ")) {
                indent++;
                stripped = stripped.replace(/^(&nbsp;|    )/, "");
            }
            if (indent > 0) {
                value = `<span style="padding-left:${indent * 20}px;">${stripped}</span>`;
            }
        }

        // Red negatives on currency columns
        if (column.fieldtype === "Currency" && value) {
            let num = parseFloat(String(value).replace(/[^0-9.-]/g, ""));
            if (!isNaN(num) && num < 0) {
                let bg = cell_style["background-color"] || "";
                if (!bg.includes("darkblue") && !bg.includes("rgb(0")) {
                    cell_style["color"] = "red";
                }
            }
        }

        // Variance % colouring
        if (column.fieldtype === "Percent" && value) {
            let pct = parseFloat(String(value).replace(/%/g, "").replace(/,/g, ""));
            if (!isNaN(pct)) {
                let colour = pct >= 0 ? "green" : "red";
                if (Math.abs(pct) > 20) {
                    if (!cell_style["font-weight"]) cell_style["font-weight"] = "bold";
                    cell_style["color"] = colour;
                } else if (Math.abs(pct) > 10) {
                    cell_style["color"] = colour;
                }
            }
        }

        if (Object.keys(cell_style).length > 0) {
            let css = Object.entries(cell_style).map(([k, v]) => `${k}:${v}`).join(";");
            return `<div style="${css};width:100%;height:100%;display:flex;align-items:center;padding:0 8px;">${value}</div>`;
        }

        return value;
    },

    /* ================================================================
       AFTER DATATABLE RENDER
       Port from Financial Report Template Based — highlights negatives
       and large variances after the datatable is painted.
    ================================================================ */

    after_datatable_render(datatable_obj) {
        $(datatable_obj.wrapper).find(".dt-cell").each(function () {
            let $cell   = $(this);
            let content = $cell.html();

            // Negative values → red
            if ($cell.hasClass("dt-cell--col-currency") ||
                $cell.hasClass("dt-cell--col-float")) {
                let val = parseFloat($cell.text().replace(/[^0-9.-]/g, ""));
                if (!isNaN(val) && val < 0) {
                    $cell.css("color", "red");
                }
            }

            // Large variances → yellow / red background
            if (content && content.includes("%")) {
                let variance = parseFloat(content.replace(/[^0-9.-]/g, ""));
                if (!isNaN(variance) && Math.abs(variance) > 10) {
                    $cell.css({
                        "background-color": Math.abs(variance) > 20 ? "#ffcccc" : "#ffffcc",
                        "font-weight":      "bold"
                    });
                }
            }
        });
    },

    /* ================================================================
       BUTTONS
    ================================================================ */

    onload(report) {
        report.page.add_inner_button(
            __("Export to Excel"),
            () => export_to_excel(report),
            __("Tools")
        );
        report.page.add_inner_button(
            __("Compare Dimensions"),
            () => show_dimension_comparison(report),
            __("Tools")
        );
    },

    /* ================================================================
       CHART
    ================================================================ */

    get_chart_data(columns, data) {
        let dim_cols = columns.filter(c => c.fieldtype === "Currency" && c.fieldname !== "total");
        let metrics  = ["Revenue", "Gross Profit", "Operating Profit", "Net Profit"];
        let datasets = [];

        metrics.forEach(metric => {
            let found = data.find(r => r.account_name === metric);
            if (found) {
                datasets.push({
                    name:   metric,
                    values: dim_cols.map(c => _flt(found[c.fieldname]))
                });
            }
        });

        return {
            data:   { labels: dim_cols.map(c => c.label), datasets },
            type:   "bar",
            colors: ["#5e64ff", "#7cd6fd", "#743ee2", "#ff5858"]
        };
    }
};

/* ================================================================
   EXCEL EXPORT
================================================================ */

function export_to_excel(report) {
    if (!report.get_filter_value("template")) {
        frappe.msgprint(__("Please select a template first"));
        return;
    }

    frappe.dom.freeze(__("Generating Excel…"));

    // Strip HTML from string cells before sending to Python
    let clean_data = report.data.map(row => {
        let out = {};
        Object.keys(row).forEach(k => {
            let v = row[k];
            if (typeof v === "string") {
                v = v.replace(/<[^>]*>/g, "");               // strip HTML
                let n = parseFloat(v.replace(/[^0-9.-]/g, ""));
                out[k] = isNaN(n) ? v : n;
            } else {
                out[k] = v;
            }
        });
        return out;
    });

    frappe.call({
        method: "ecclesia.ecclesia.utils.excel_export.get_excel_file",
        args: {
            columns:       report.columns,
            data:          clean_data,
            filters:       report.get_values(),
            template_name: report.get_filter_value("template")
        },
        callback(r) {
            frappe.dom.unfreeze();
            if (r.message) {
                window.open(r.message);
                frappe.show_alert(
                    { message: __("Excel exported successfully!"), indicator: "green" }, 3
                );
            }
        },
        error() {
            frappe.dom.unfreeze();
        }
    });
}

/* ================================================================
   DIMENSION COMPARISON POPUP
================================================================ */

function show_dimension_comparison(report) {
    let totals = {};
    report.columns
        .filter(c => c.fieldtype === "Currency" && c.fieldname !== "total")
        .forEach(c => {
            totals[c.label] = report.data.reduce((sum, r) => sum + _flt(r[c.fieldname]), 0);
        });

    let sorted = Object.entries(totals).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
    let grand  = sorted.reduce((s, [, v]) => s + Math.abs(v), 0);

    let html = `<table class="table table-bordered table-hover">
        <thead><tr>
            <th>Dimension</th>
            <th style="text-align:right">Total</th>
            <th style="text-align:right">% of Grand Total</th>
        </tr></thead><tbody>`;

    sorted.forEach(([dim, val]) => {
        let pct = grand > 0 ? (Math.abs(val) / grand * 100).toFixed(1) : "0.0";
        html += `<tr>
            <td>${dim}</td>
            <td style="text-align:right">${frappe.format(val, { fieldtype: "Currency" })}</td>
            <td style="text-align:right">${pct}%</td>
        </tr>`;
    });

    html += "</tbody></table>";
    frappe.msgprint({ title: __("Dimension Comparison"), message: html, wide: true });
}

/* ================================================================
   UTIL
================================================================ */

function _flt(v) {
    let n = parseFloat(v);
    return isNaN(n) ? 0 : n;
}