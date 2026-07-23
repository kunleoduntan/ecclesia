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
            get_query: () => ({ filters: { is_active: 1 } }),
            on_change() {
                const tpl = frappe.query_report.get_filter_value("template");
                if (!tpl) return;
                frappe.db.get_doc("Financial Report Template", tpl).then(doc => {
                    // Show/hide budget related filters based on template setting
                    const sb = frappe.query_report.get_filter("show_budget");
                    if (sb) { 
                        sb.df.hidden = !doc.enable_budget_comparison;
                        sb.refresh();
                    }
                    const bp = frappe.query_report.get_filter("budget_plan");
                    if (bp) { bp.df.hidden = !doc.enable_budget_comparison; bp.refresh(); }
                    
                    // Show/hide comparison filter
                    const sc = frappe.query_report.get_filter("show_comparison");
                    if (sc) {
                        sc.df.hidden = !doc.show_comparison;
                        sc.refresh();
                    }
                    
                    frappe.show_alert(
                        { message: __("{0} ({1})", [doc.template_name, doc.report_type]),
                          indicator: "green" }, 3
                    );
                });
            }
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
            reqd: 1,
            on_change() {
                const dt = frappe.query_report.get_filter_value("dimension_type");
                const pc = frappe.query_report.get_filter("parent_cost_center");
                const sc = frappe.query_report.get_filter("specific_cost_centers");
                const sb = frappe.query_report.get_filter("specific_branches");
                const sp = fraquee.query_report.get_filter("specific_projects");
                
                if (pc) pc.df.hidden = (dt !== "Cost Center");
                if (sc) sc.df.hidden = (dt !== "Cost Center");
                if (sb) sb.df.hidden = (dt !== "Branch");
                if (sp) sp.df.hidden = (dt !== "Project");
                
                if (pc) pc.refresh();
                if (sc) sc.refresh();
                if (sb) sb.refresh();
                if (sp) sp.refresh();
            }
        },
        {
            fieldname: "parent_cost_center",
            label: __("Parent Cost Center"),
            fieldtype: "Link",
            options: "Cost Center",
            depends_on: "eval:doc.dimension_type=='Cost Center'",
            hidden: 1,
            get_query: () => ({ filters: { is_group: 1, company: frappe.query_report.get_filter_value("company") } })
        },
        {
            fieldname: "specific_cost_centers",
            label: __("Specific Cost Centers"),
            fieldtype: "MultiSelectList",
            depends_on: "eval:doc.dimension_type=='Cost Center'",
            hidden: 1,
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
            hidden: 1,
            get_data: txt => frappe.db.get_link_options("Branch", txt, {
                company: frappe.query_report.get_filter_value("company")
            })
        },
        {
            fieldname: "specific_projects",
            label: __("Projects"),
            fieldtype: "MultiSelectList",
            depends_on: "eval:doc.dimension_type=='Project'",
            hidden: 1,
            get_data: txt =>
                frappe.db.get_link_options("Project", txt, {
                    company: frappe.query_report.get_filter_value("company"),
                    status: "Open"
                })
        },
        {
            fieldname: "show_totals",
            label: __("Show Totals Row"),
            fieldtype: "Check",
            default: 1
        },
        {
            fieldname: "show_comparison",
            label: __("Show Prior Year Comparison"),
            fieldtype: "Check",
            default: 0,
            hidden: 1
        },
        {
            fieldname: "show_budget",
            label: __("Show Budget Comparison"),
            fieldtype: "Check",
            default: 0,
            hidden: 1
        },
        {
            fieldname: "budget_plan",
            label: __("Budget Plan"),
            fieldtype: "Link",
            options: "Budget Plan",
            hidden: 1,
            depends_on: "eval:doc.show_budget==1",
            get_query() {
                return {
                    filters: {
                        company: frappe.query_report.get_filter_value("company"),
                        docstatus: 1
                    }
                };
            }
        }
    ],

    /* ═══════════════════════════════════════════════════════════════════════════
       FORMATTER - Full styling from dimension report
    ═══════════════════════════════════════════════════════════════════════════ */

    formatter(value, row, column, data, default_formatter) {
        // Skip formatting for null values
        if (value === null || value === undefined) {
            return "";
        }

        let cell_style = {};

        // Default formatting first
        value = default_formatter(value, row, column, data);

        // Parse _style string from Python
        if (data && data._style) {
            let s = String(data._style);

            // Background color
            let bg_match = s.match(/background-color:\s*([^;]+)/i);
            if (bg_match) cell_style["background-color"] = bg_match[1].trim();

            // Font weight
            if (s.includes("font-weight: bold") || s.includes("font-weight:bold")) {
                cell_style["font-weight"] = "bold";
            }

            // Border top
            let bt_match = s.match(/border-top:\s*([^;]+)/i);
            if (bt_match) cell_style["border-top"] = bt_match[1].trim();

            // Border bottom
            let bb_match = s.match(/border-bottom:\s*([^;]+)/i);
            if (bb_match) cell_style["border-bottom"] = bb_match[1].trim();
        }

        // Indentation on account_name
        if (column.fieldname === "account_name" && typeof value === "string") {
            let indent = 0;
            let stripped = value;
            while (stripped.startsWith("&nbsp;") || stripped.startsWith("    ")) {
                indent++;
                stripped = stripped.replace(/^(&nbsp;|    )/, "");
            }
            // Remove any remaining HTML tags for clean display
            stripped = stripped.replace(/<\/?b>/g, "");
            if (indent > 0) {
                cell_style["padding-left"] = `${indent * 20}px`;
                cell_style["display"] = "block";
            }
            value = stripped;
        }

        // Red negatives on currency columns
        if (column.fieldtype === "Currency" && value !== "" && value !== null) {
            let num = parseFloat(String(value).replace(/[^0-9.-]/g, ""));
            if (!isNaN(num) && num < 0) {
                let bg = cell_style["background-color"] || "";
                if (!bg.includes("darkblue") && !bg.includes("rgb(0,") && !bg.includes("#0")) {
                    cell_style["color"] = "#cc0000";
                }
            }
            // Right align currency
            cell_style["text-align"] = "right";
            cell_style["display"] = "block";
            cell_style["width"] = "100%";
        }

        // Variance % colouring
        if (column.fieldtype === "Percent" && value !== "" && value !== null) {
            let pct = parseFloat(String(value).replace(/[^0-9.-]/g, ""));
            if (!isNaN(pct)) {
                let absPct = Math.abs(pct);
                cell_style["color"] = pct >= 0 ? "#1a7340" : "#cc0000";
                cell_style["text-align"] = "right";
                cell_style["display"] = "block";
                cell_style["width"] = "100%";
                if (absPct > 20) {
                    cell_style["font-weight"] = "bold";
                    cell_style["background-color"] = pct >= 0 ? "#d4edda" : "#f8d7da";
                }
            }
        }

        // Apply CSS if any
        if (Object.keys(cell_style).length > 0) {
            let css = Object.entries(cell_style).map(([k, v]) => `${k}:${v}`).join(";");
            return `<span style="${css}">${value}</span>`;
        }

        return value;
    },

    /* ═══════════════════════════════════════════════════════════════════════════
       AFTER DATATABLE RENDER - Additional styling
    ═══════════════════════════════════════════════════════════════════════════ */

    after_datatable_render(datatable_obj) {
        $(datatable_obj.wrapper).find(".dt-cell").each(function () {
            let $cell = $(this);
            let content = $cell.html();

            // Additional check for negative values
            if ($cell.hasClass("dt-cell--col-currency") || $cell.hasClass("dt-cell--col-float")) {
                let val = parseFloat($cell.text().replace(/[^0-9.-]/g, ""));
                if (!isNaN(val) && val < 0) {
                    if (!$cell.css("color") || $cell.css("color") === "rgb(0, 0, 0)") {
                        $cell.css("color", "#cc0000");
                    }
                }
            }
        });
    },

    /* ═══════════════════════════════════════════════════════════════════════════
       BUTTONS
    ═══════════════════════════════════════════════════════════════════════════ */

    onload(report) {
        // Refresh button to reload data
        report.page.add_inner_button(
            __("Refresh"),
            () => report.refresh(),
            __("Actions")
        );
        
        // Export to Excel
        report.page.add_inner_button(
            __("Export to Excel"),
            () => export_to_excel(report),
            __("Export")
        );
        
        // Dimension Comparison Chart
        report.page.add_inner_button(
            __("Dimension Comparison"),
            () => show_dimension_comparison(report),
            __("Chart")
        );
        
        // Help button
        report.page.add_inner_button(
            __("Help"),
            () => show_help(),
            __("Actions")
        );
    },

    /* ═══════════════════════════════════════════════════════════════════════════
       CHART DATA
    ═══════════════════════════════════════════════════════════════════════════ */

    get_chart_data(columns, data) {
        // Find dimension columns (currency columns that aren't total)
        let dim_cols = columns.filter(c => 
            c.fieldtype === "Currency" && 
            c.fieldname !== "total" &&
            c.fieldname !== "total_py" &&
            c.fieldname !== "total_bud" &&
            !c.fieldname.endsWith("_py") &&
            !c.fieldname.endsWith("_var") &&
            !c.fieldname.endsWith("_bud") &&
            !c.fieldname.endsWith("_bud_var")
        );
        
        // Find key metrics from data
        let metrics = [];
        let metric_keywords = ["Revenue", "Sales", "Income", "Gross Profit", "Operating Profit", "Net Profit", "Total Expense"];
        
        for (let row of data) {
            if (row.account_name && typeof row.account_name === "string") {
                let name = row.account_name.toLowerCase();
                for (let keyword of metric_keywords) {
                    if (name.includes(keyword.toLowerCase())) {
                        metrics.push(row.account_name);
                        break;
                    }
                }
            }
        }
        
        // Limit to top 5 metrics
        metrics = [...new Set(metrics)].slice(0, 5);
        
        let datasets = [];
        let colors = ["#5e64ff", "#7cd6fd", "#743ee2", "#ff5858", "#ffb347"];
        
        metrics.forEach((metric, idx) => {
            let found = data.find(r => r.account_name === metric);
            if (found) {
                datasets.push({
                    name: metric,
                    values: dim_cols.map(c => frappe.utils.flt(found[c.fieldname]))
                });
            }
        });
        
        if (datasets.length === 0) {
            return null;
        }
        
        return {
            data: {
                labels: dim_cols.map(c => c.label),
                datasets: datasets
            },
            type: "bar",
            colors: colors.slice(0, datasets.length),
            height: 300
        };
    }
};

/* ═══════════════════════════════════════════════════════════════════════════
   EXPORT TO EXCEL
════════════════════════════════════════════════════════════════════════════ */

function export_to_excel(report) {
    if (!report.get_filter_value("template")) {
        frappe.msgprint(__("Please select a template first"));
        return;
    }

    frappe.dom.freeze(__("Generating Excel..."));

    // Clean data - strip HTML from strings
    let clean_data = report.data.map(row => {
        let out = {};
        Object.keys(row).forEach(k => {
            let v = row[k];
            if (typeof v === "string") {
                v = v.replace(/<[^>]*>/g, "").replace(/&nbsp;/g, " ");
                let num = parseFloat(v.replace(/[^0-9.-]/g, ""));
                out[k] = isNaN(num) ? v : num;
            } else {
                out[k] = v;
            }
        });
        return out;
    });

    frappe.call({
        method: "ecclesia.ecclesia.report.financial_report_by_dimension.get_excel_file",
        args: {
            columns: report.columns,
            data: clean_data,
            filters: report.get_values(),
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
            frappe.msgprint(__("Error generating Excel file. Please try again."));
        }
    });
}

/* ═══════════════════════════════════════════════════════════════════════════
   DIMENSION COMPARISON CHART (Popup)
════════════════════════════════════════════════════════════════════════════ */

function show_dimension_comparison(report) {
    let totals = {};
    let dimension_columns = [];
    
    // Identify dimension columns
    for (let col of report.columns) {
        if (col.fieldtype === "Currency" && col.fieldname !== "total" && 
            col.fieldname !== "total_py" && col.fieldname !== "total_bud" &&
            !col.fieldname.endsWith("_py") && !col.fieldname.endsWith("_var") &&
            !col.fieldname.endsWith("_bud") && !col.fieldname.endsWith("_bud_var")) {
            dimension_columns.push(col);
        }
    }
    
    // Calculate totals for each dimension
    for (let col of dimension_columns) {
        totals[col.label] = report.data.reduce((sum, row) => {
            let val = row[col.fieldname];
            if (val && typeof val === "number") {
                return sum + Math.abs(val);
            }
            if (typeof val === "string") {
                let num = parseFloat(val.replace(/[^0-9.-]/g, ""));
                if (!isNaN(num)) return sum + Math.abs(num);
            }
            return sum;
        }, 0);
    }
    
    let sorted = Object.entries(totals).sort((a, b) => b[1] - a[1]);
    let grand = sorted.reduce((s, [, v]) => s + v, 0);
    
    let html = `
        <div style="padding: 10px;">
            <h4>${__("Dimension Comparison")}</h4>
            <table class="table table-bordered table-hover" style="width: 100%;">
                <thead>
                    <tr>
                        <th>${__("Dimension")}</th>
                        <th style="text-align: right">${__("Total")}</th>
                        <th style="text-align: right">${__("% of Grand Total")}</th>
                    </tr>
                </thead>
                <tbody>`;
    
    for (let [dim, val] of sorted) {
        let pct = grand > 0 ? ((val / grand) * 100).toFixed(1) : "0.0";
        html += `
            <tr>
                <td>${frappe.escape_html(dim)}</td>
                <td style="text-align: right">${format_currency(val)}</td>
                <td style="text-align: right">${pct}%</td>
            </tr>`;
    }
    
    html += `
                </tbody>
            </table>
            <div class="text-muted" style="margin-top: 15px;">
                <small>${__("Note: Values shown are absolute totals for comparison purposes.")}</small>
            </div>
        </div>`;
    
    frappe.msgprint({
        title: __("Dimension Comparison"),
        message: html,
        wide: true
    });
}

/* ═══════════════════════════════════════════════════════════════════════════
   HELP
════════════════════════════════════════════════════════════════════════════ */

function show_help() {
    let html = `
        <div style="padding: 15px; font-family: inherit;">
            <h4>${__("Financial Report by Dimension - Help")}</h4>
            <hr>
            <h5>${__("Overview")}</h5>
            <p>${__("This report provides financial data broken down by dimension (Cost Center, Branch, or Project). It supports all template features including:")}</p>
            <ul>
                <li>${__("Account Aggregate lines (with all 5 account mapping methods)")}</li>
                <li>${__("Calculated lines with formulas referencing other line codes")}</li>
                <li>${__("Retained Earnings lines (auto-accumulates P&L)")}</li>
                <li>${__("Headers and Blank lines for organization")}</li>
                <li>${__("Prior year comparison (toggle in filters)")}</li>
                <li>${__("Budget comparison (toggle in filters)")}</li>
                <li>${__("Row styling: colors, borders, bold, totals/subtotals")}</li>
            </ul>
            
            <h5>${__("Filters")}</h5>
            <ul>
                <li><strong>${__("Template")}</strong> - ${__("Select any active Financial Report Template")}</li>
                <li><strong>${__("Company")}</strong> - ${__("Your company")}</li>
                <li><strong>${__("Date Range")}</strong> - ${__("Period for the report")}</li>
                <li><strong>${__("Dimension Type")}</strong> - ${__("Cost Center, Branch, or Project")}</li>
                <li><strong>${__("Dimensions")}</strong> - ${__("Select specific dimensions or use parent cost center")}</li>
                <li><strong>${__("Show Totals Row")}</strong> - ${__("Add a totals row at the bottom")}</li>
            </ul>
            
            <h5>${__("Tips")}</h5>
            <ul>
                <li>${__("Use the Dimension Comparison button to see a bar chart of your top dimensions")}</li>
                <li>${__("Export to Excel for further analysis")}</li>
                <li>${__("Calculated lines can reference any line_code from the template")}</li>
                <li>${__("Retained Earnings automatically accumulates all Income minus Expense")}</li>
            </ul>
        </div>
    `;
    
    frappe.msgprint({
        title: __("Help"),
        message: html,
        wide: true
    });
}

/* ═══════════════════════════════════════════════════════════════════════════
   UTILITIES
════════════════════════════════════════════════════════════════════════════ */

function format_currency(value) {
    if (value === null || value === undefined) return "0.00";
    return frappe.format(value, { fieldtype: "Currency" });
}