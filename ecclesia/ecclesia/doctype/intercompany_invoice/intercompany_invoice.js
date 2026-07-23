// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

// Copyright (c) 2026, Value Impacts Consulting
// Intercompany Invoice — Client Script
// Features: live calculations, chart analytics, amortization preview, smart UX

frappe.ui.form.on("Intercompany Invoice", {

    // ──────────────────────────────────────────────────────────────────
    // SETUP & REFRESH
    // ──────────────────────────────────────────────────────────────────

    setup(frm) {
        // Filter intercompany accounts to issuing company
        frm.set_query("intercompany_account", () => ({
            filters: {
                company: frm.doc.company,
                is_group: 0,
                account_type: ["in", ["Receivable", "Payable", ""]],
            },
        }));

        frm.set_query("counterparty_intercompany_account", () => ({
            filters: {
                company: frm.doc.counterparty_company,
                is_group: 0,
            },
        }));

        // Items table: filter income_account to company
        frm.set_query("income_account", "items", () => ({
            filters: {
                company: frm.doc.company,
                is_group: 0,
                root_type: ["in", ["Income", "Expense"]],
            },
        }));

        frm.set_query("cost_center", "items", () => ({
            filters: { company: frm.doc.company, is_group: 0 },
        }));
    },

    refresh(frm) {
        frm.trigger("render_analytics_dashboard");
        frm.trigger("setup_custom_buttons");
        frm.trigger("set_direction_indicator");

        // Show journal entry link
        if (frm.doc.journal_entry) {
            frm.dashboard.add_indicator(
                __("GL Posted: {0}", [frm.doc.journal_entry]),
                "green"
            );
        }

        // Status badge coloring
        const colorMap = {
            "Draft": "orange",
            "Submitted": "blue",
            "Partially Settled": "yellow",
            "Settled": "green",
            "Cancelled": "red",
        };
        if (frm.doc.status && colorMap[frm.doc.status]) {
            frm.page.set_indicator(frm.doc.status, colorMap[frm.doc.status]);
        }
    },

    // ──────────────────────────────────────────────────────────────────
    // CUSTOM BUTTONS
    // ──────────────────────────────────────────────────────────────────

    setup_custom_buttons(frm) {
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__("View Amortization Schedule"), () => {
                frm.trigger("show_amortization_dialog");
            }, __("Reports"));

            frm.add_custom_button(__("Interest Accrual Breakdown"), () => {
                frm.trigger("show_interest_accrual_dialog");
            }, __("Reports"));

            frm.add_custom_button(__("Tax Summary"), () => {
                frm.trigger("show_tax_summary_dialog");
            }, __("Reports"));
        }

        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__("Preview Amortization"), () => {
                frm.trigger("show_amortization_dialog");
            });
        }
    },

    // ──────────────────────────────────────────────────────────────────
    // DIRECTION INDICATOR
    // ──────────────────────────────────────────────────────────────────

    set_direction_indicator(frm) {
        const dir = frm.doc.intercompany_direction;
        if (!dir) return;

        const isDebit = dir === "Debit Intercompany Account";
        const msg = isDebit
            ? `<span style="color:#2e7d32;font-weight:600;">▲ RECEIVABLE — You are owed by ${frm.doc.counterparty_company || "counterparty"}</span>`
            : `<span style="color:#c62828;font-weight:600;">▼ PAYABLE — You owe ${frm.doc.counterparty_company || "counterparty"}</span>`;

        frm.set_intro(msg, isDebit ? "green" : "red");
    },

    intercompany_direction(frm) {
        frm.trigger("set_direction_indicator");
    },

    counterparty_company(frm) {
        frm.trigger("set_direction_indicator");
    },

    // ──────────────────────────────────────────────────────────────────
    // FIELD CHANGE HANDLERS — RECALC
    // ──────────────────────────────────────────────────────────────────

    vat_applicable(frm) {
        frm.toggle_reqd("vat_rate", frm.doc.vat_applicable);
        frm.trigger("recalculate_totals");
    },

    vat_rate(frm)                { frm.trigger("recalculate_totals"); },
    withholding_tax_rate(frm)    { frm.trigger("recalculate_totals"); },
    annual_interest_rate(frm)    { frm.trigger("recalculate_totals"); },
    interest_period_from(frm)    { frm.trigger("recalculate_totals"); },
    interest_period_to(frm)      { frm.trigger("recalculate_totals"); },
    interest_basis(frm)          { frm.trigger("recalculate_totals"); },

    recalculate_totals(frm) {
        // Client-side mirror of Python calculations for live feedback
        let totalBase = 0, totalTax = 0, totalItemInterest = 0;

        (frm.doc.items || []).forEach(row => {
            const base   = flt(row.qty) * flt(row.rate);
            const tax    = base * flt(row.tax_rate) / 100;
            const intAmt = base * flt(row.interest_rate) / 100;

            frappe.model.set_value(row.doctype, row.name, "amount",          base);
            frappe.model.set_value(row.doctype, row.name, "tax_amount",      tax);
            frappe.model.set_value(row.doctype, row.name, "interest_amount", intAmt);
            frappe.model.set_value(row.doctype, row.name, "line_total",      base + tax + intAmt);

            totalBase        += base;
            totalTax         += tax;
            totalItemInterest += intAmt;
        });

        // Interest
        let docInterest = 0;
        if (frm.doc.interest_period_from && frm.doc.interest_period_to && flt(frm.doc.annual_interest_rate) > 0) {
            const days = frappe.datetime.get_day_diff(
                frm.doc.interest_period_to, frm.doc.interest_period_from
            );
            const basis   = frm.doc.interest_basis || "Actual/365";
            const divisor = basis.includes("365") ? 365 : 360;
            docInterest   = totalBase * (flt(frm.doc.annual_interest_rate) / 100) * (days / divisor);
            frm.set_value("days_outstanding",      Math.max(days, 0));
            frm.set_value("total_interest_charged", flt(docInterest.toFixed(2)));
        }

        // WHT
        const wht = totalBase * flt(frm.doc.withholding_tax_rate) / 100;
        frm.set_value("withholding_tax_amount", flt(wht.toFixed(2)));

        // VAT
        let vat = 0;
        if (frm.doc.vat_applicable) {
            vat = (totalBase + docInterest) * flt(frm.doc.vat_rate) / 100;
            frm.set_value("vat_amount", flt(vat.toFixed(2)));
        } else {
            frm.set_value("vat_amount", 0);
        }

        const allTax      = totalTax + vat;
        const allInterest = totalItemInterest + docInterest;
        const grand       = totalBase + allTax + allInterest - wht;

        frm.set_value("total_base_amount",     flt(totalBase.toFixed(2)));
        frm.set_value("total_tax_amount",      flt(allTax.toFixed(2)));
        frm.set_value("total_interest_amount", flt(allInterest.toFixed(2)));
        frm.set_value("grand_total",           flt(grand.toFixed(2)));

        frm.trigger("render_analytics_dashboard");
    },

    // ──────────────────────────────────────────────────────────────────
    // ANALYTICS DASHBOARD
    // ──────────────────────────────────────────────────────────────────

    render_analytics_dashboard(frm) {
        const base     = flt(frm.doc.total_base_amount);
        const tax      = flt(frm.doc.total_tax_amount);
        const interest = flt(frm.doc.total_interest_amount);
        const wht      = flt(frm.doc.withholding_tax_amount);
        const grand    = flt(frm.doc.grand_total);

        if (!base && !grand) return;

        const currency = frm.doc.currency || "NGN";
        const fmt = v => frappe.format(v, { fieldtype: "Currency", currency });

        const html = `
        <div style="
            background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
            border-radius: 12px;
            padding: 20px 24px;
            margin: 12px 0;
            font-family: 'Segoe UI', sans-serif;
            box-shadow: 0 8px 32px rgba(0,0,0,0.18);
        ">
            <div style="color:#90caf9;font-size:11px;letter-spacing:2px;text-transform:uppercase;margin-bottom:14px;font-weight:600;">
                ⚡ Transaction Intelligence
            </div>

            <!-- KPI Strip -->
            <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:18px;">
                ${kpiCard("Principal", fmt(base), "#4fc3f7")}
                ${kpiCard("Tax Load", fmt(tax), "#ffb74d")}
                ${kpiCard("Interest", fmt(interest), "#a5d6a7")}
                ${kpiCard("WHT Deducted", fmt(wht), "#ef9a9a")}
                ${kpiCard("Net Settlement", fmt(grand), "#ce93d8", true)}
            </div>

            <!-- Composition Bar -->
            ${compositionBar(base, tax, interest, wht)}

            <!-- Ratios -->
            <div style="display:flex;gap:24px;margin-top:14px;flex-wrap:wrap;">
                ${ratio("Effective Tax Rate", base ? ((tax/base)*100).toFixed(1)+"%" : "—", "#ffb74d")}
                ${ratio("Interest Yield", base ? ((interest/base)*100).toFixed(2)+"%" : "—", "#a5d6a7")}
                ${ratio("WHT Rate", base ? ((wht/base)*100).toFixed(1)+"%" : "—", "#ef9a9a")}
                ${ratio("Net / Gross", grand && (base+tax+interest) ? (grand/(base+tax+interest)*100).toFixed(1)+"%" : "—", "#ce93d8")}
            </div>
        </div>`;

        function kpiCard(label, value, color, bold=false) {
            return `<div style="
                flex:1;min-width:110px;
                background:rgba(255,255,255,0.06);
                border-radius:8px;padding:10px 12px;
                border-left:3px solid ${color};
            ">
                <div style="color:${color};font-size:10px;letter-spacing:1px;text-transform:uppercase;margin-bottom:4px;">${label}</div>
                <div style="color:#fff;font-size:${bold?'15':'13'}px;font-weight:${bold?700:500};">${value}</div>
            </div>`;
        }

        function compositionBar(base, tax, interest, wht) {
            const total = base + tax + interest;
            if (!total) return "";
            const pBase = (base/total*100).toFixed(1);
            const pTax  = (tax/total*100).toFixed(1);
            const pInt  = (interest/total*100).toFixed(1);
            return `
            <div>
                <div style="color:#90caf9;font-size:10px;letter-spacing:1px;margin-bottom:6px;">COMPOSITION</div>
                <div style="display:flex;border-radius:6px;overflow:hidden;height:10px;gap:1px;">
                    <div style="width:${pBase}%;background:#4fc3f7;" title="Principal ${pBase}%"></div>
                    <div style="width:${pTax}%;background:#ffb74d;"  title="Tax ${pTax}%"></div>
                    <div style="width:${pInt}%;background:#a5d6a7;"  title="Interest ${pInt}%"></div>
                </div>
                <div style="display:flex;gap:16px;margin-top:6px;font-size:10px;color:#b0bec5;">
                    <span><span style="color:#4fc3f7;">█</span> Principal ${pBase}%</span>
                    <span><span style="color:#ffb74d;">█</span> Tax ${pTax}%</span>
                    <span><span style="color:#a5d6a7;">█</span> Interest ${pInt}%</span>
                </div>
            </div>`;
        }

        function ratio(label, value, color) {
            return `<div style="text-align:center;">
                <div style="color:${color};font-size:13px;font-weight:700;">${value}</div>
                <div style="color:#78909c;font-size:10px;letter-spacing:1px;">${label}</div>
            </div>`;
        }

        // Render into a custom section above grand_total
        if (!frm.fields_dict["analytics_html"]) {
            // Inject dynamically only in refresh context
            $(frm.fields_dict.grand_total.wrapper).before(`
                <div id="ic-analytics-dashboard"></div>
            `);
        }
        $("#ic-analytics-dashboard").html(html);
    },

    // ──────────────────────────────────────────────────────────────────
    // AMORTIZATION SCHEDULE DIALOG
    // ──────────────────────────────────────────────────────────────────

    show_amortization_dialog(frm) {
        const d = new frappe.ui.Dialog({
            title: "Amortization Schedule",
            size: "extra-large",
            fields: [
                {
                    fieldtype: "Float",
                    fieldname: "principal",
                    label: "Principal Amount",
                    default: frm.doc.total_base_amount,
                    reqd: 1,
                },
                { fieldtype: "Column Break" },
                {
                    fieldtype: "Percent",
                    fieldname: "annual_rate",
                    label: "Annual Rate (%)",
                    default: frm.doc.annual_interest_rate || 15,
                    reqd: 1,
                },
                { fieldtype: "Column Break" },
                {
                    fieldtype: "Int",
                    fieldname: "periods",
                    label: "Number of Periods",
                    default: 12,
                    reqd: 1,
                },
                { fieldtype: "Column Break" },
                {
                    fieldtype: "Select",
                    fieldname: "period_type",
                    label: "Period Type",
                    options: "Monthly\nQuarterly\nSemi-Annual\nAnnual",
                    default: "Monthly",
                    reqd: 1,
                },
                { fieldtype: "Column Break" },
                {
                    fieldtype: "Date",
                    fieldname: "start_date",
                    label: "Start Date",
                    default: frm.doc.posting_date || frappe.datetime.get_today(),
                },
                { fieldtype: "Section Break" },
                {
                    fieldtype: "HTML",
                    fieldname: "schedule_html",
                    label: "",
                },
            ],
            primary_action_label: "Generate",
            primary_action(values) {
                frappe.call({
                    method: "ecclesia.ecclesia.doctype.intercompany_invoice.intercompany_invoice.get_amortization_schedule",
                    args: {
                        principal: values.principal,
                        annual_rate: values.annual_rate,
                        periods: values.periods,
                        period_type: values.period_type,
                        start_date: values.start_date,
                    },
                    callback(r) {
                        if (!r.message || !r.message.length) {
                            frappe.msgprint("No schedule generated. Check inputs.");
                            return;
                        }
                        const rows = r.message;
                        const currency = frm.doc.currency || "NGN";
                        const fmt = v => format_currency(v, currency);

                        let tableHtml = `
                        <div style="overflow-x:auto;max-height:420px;overflow-y:auto;">
                        <table style="width:100%;border-collapse:collapse;font-size:12px;font-family:monospace;">
                            <thead style="position:sticky;top:0;background:#1a237e;color:#fff;">
                                <tr>
                                    ${["#","Period End","Opening Bal","Instalment","Principal","Interest","Closing Bal","Cum. Principal","Cum. Interest"]
                                        .map(h => `<th style="padding:8px 10px;text-align:right;white-space:nowrap;">${h}</th>`)
                                        .join("")}
                                </tr>
                            </thead>
                            <tbody>
                                ${rows.map((r, i) => `
                                <tr style="background:${i%2===0?"#f5f5f5":"#fff"};border-bottom:1px solid #e0e0e0;">
                                    <td style="padding:7px 10px;text-align:right;">${r.period}</td>
                                    <td style="padding:7px 10px;text-align:right;">${r.period_end}</td>
                                    <td style="padding:7px 10px;text-align:right;">${fmt(r.opening_balance)}</td>
                                    <td style="padding:7px 10px;text-align:right;font-weight:600;">${fmt(r.instalment)}</td>
                                    <td style="padding:7px 10px;text-align:right;color:#1565c0;">${fmt(r.principal_component)}</td>
                                    <td style="padding:7px 10px;text-align:right;color:#e65100;">${fmt(r.interest_component)}</td>
                                    <td style="padding:7px 10px;text-align:right;font-weight:600;">${fmt(r.closing_balance)}</td>
                                    <td style="padding:7px 10px;text-align:right;color:#2e7d32;">${fmt(r.cumulative_principal)}</td>
                                    <td style="padding:7px 10px;text-align:right;color:#bf360c;">${fmt(r.cumulative_interest)}</td>
                                </tr>`).join("")}
                            </tbody>
                            <tfoot style="background:#e8eaf6;font-weight:700;">
                                <tr>
                                    <td colspan="4" style="padding:8px 10px;">Totals</td>
                                    <td style="padding:8px 10px;text-align:right;color:#1565c0;">${fmt(rows[rows.length-1].cumulative_principal)}</td>
                                    <td style="padding:8px 10px;text-align:right;color:#e65100;">${fmt(rows[rows.length-1].cumulative_interest)}</td>
                                    <td colspan="3"></td>
                                </tr>
                            </tfoot>
                        </table></div>`;

                        d.fields_dict.schedule_html.$wrapper.html(tableHtml);
                    }
                });
            },
            secondary_action_label: "Print Schedule",
            secondary_action() {
                // Trigger print format
                const w = window.open(
                    frappe.urllib.get_full_url(
                        `/api/method/frappe.utils.print_format.download_pdf?doctype=Intercompany Invoice&name=${frm.doc.name}&format=Intercompany Invoice Schedule&no_letterhead=0`
                    )
                );
                w && w.focus();
            },
        });
        d.show();
        // Auto-generate on open
        setTimeout(() => d.get_primary_btn().click(), 300);
    },

    // ──────────────────────────────────────────────────────────────────
    // INTEREST ACCRUAL DIALOG
    // ──────────────────────────────────────────────────────────────────

    show_interest_accrual_dialog(frm) {
        frappe.call({
            method: "ecclesia.ecclesia.doctype.intercompany_invoice.intercompany_invoice.get_interest_accrual_schedule",
            args: {
                principal: frm.doc.total_base_amount,
                annual_rate: frm.doc.annual_interest_rate,
                from_date: frm.doc.interest_period_from,
                to_date: frm.doc.interest_period_to,
                basis: frm.doc.interest_basis,
            },
            callback(r) {
                if (!r.message || !r.message.length) {
                    frappe.msgprint("No interest period set. Fill in Period From/To and Rate.");
                    return;
                }
                const rows = r.message;
                const currency = frm.doc.currency || "NGN";
                const fmt = v => format_currency(v, currency);
                const total = rows.reduce((s, r) => s + r.interest, 0);

                let html = `
                <h4 style="margin-bottom:12px;color:#e65100;">Monthly Interest Accrual — ${frm.doc.name}</h4>
                <div style="overflow-x:auto;">
                <table style="width:100%;border-collapse:collapse;font-size:13px;">
                    <thead style="background:#bf360c;color:#fff;">
                        <tr>${["Period Start","Period End","Days","Principal","Rate %","Interest"].map(h=>`<th style="padding:8px 12px;text-align:right;">${h}</th>`).join("")}</tr>
                    </thead>
                    <tbody>
                    ${rows.map((r,i)=>`
                    <tr style="background:${i%2?"#fff1f0":"#fff"};border-bottom:1px solid #ffccbc;">
                        <td style="padding:7px 12px;text-align:right;">${r.period_start}</td>
                        <td style="padding:7px 12px;text-align:right;">${r.period_end}</td>
                        <td style="padding:7px 12px;text-align:right;">${r.days}</td>
                        <td style="padding:7px 12px;text-align:right;">${fmt(r.principal)}</td>
                        <td style="padding:7px 12px;text-align:right;">${r.rate}%</td>
                        <td style="padding:7px 12px;text-align:right;font-weight:600;color:#bf360c;">${fmt(r.interest)}</td>
                    </tr>`).join("")}
                    </tbody>
                    <tfoot style="background:#fbe9e7;font-weight:700;">
                        <tr>
                            <td colspan="5" style="padding:8px 12px;">Total Interest</td>
                            <td style="padding:8px 12px;text-align:right;color:#bf360c;">${fmt(total)}</td>
                        </tr>
                    </tfoot>
                </table></div>`;

                frappe.msgprint({ title: "Interest Accrual Schedule", message: html, wide: true });
            },
        });
    },

    // ──────────────────────────────────────────────────────────────────
    // TAX SUMMARY DIALOG
    // ──────────────────────────────────────────────────────────────────

    show_tax_summary_dialog(frm) {
        frappe.call({
            method: "ecclesia.ecclesia.doctype.intercompany_invoice.intercompany_invoice.get_tax_summary",
            args: { docname: frm.doc.name },
            callback(r) {
                if (!r.message) return;
                const { lines, total_tax } = r.message;
                const currency = frm.doc.currency || "NGN";
                const fmt = v => format_currency(v, currency);

                const typeColors = {
                    "Item Tax": "#1565c0",
                    "VAT":      "#2e7d32",
                    "WHT":      "#b71c1c",
                };

                let html = `
                <h4 style="margin-bottom:12px;color:#1a237e;">Tax Breakdown — ${frm.doc.name}</h4>
                <table style="width:100%;border-collapse:collapse;font-size:13px;">
                    <thead style="background:#1a237e;color:#fff;">
                        <tr>${["Type","Description","Taxable Base","Rate","Tax Amount"].map(h=>`<th style="padding:9px 12px;text-align:right;">${h}</th>`).join("")}</tr>
                    </thead>
                    <tbody>
                    ${lines.map((l,i)=>`
                    <tr style="background:${i%2?"#fff":"#f3f4ff"};border-bottom:1px solid #e8eaf6;">
                        <td style="padding:8px 12px;text-align:right;">
                            <span style="background:${typeColors[l.type]||"#666"};color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;">${l.type}</span>
                        </td>
                        <td style="padding:8px 12px;text-align:right;">${l.description}</td>
                        <td style="padding:8px 12px;text-align:right;">${fmt(l.taxable_amount)}</td>
                        <td style="padding:8px 12px;text-align:right;">${l.rate}%</td>
                        <td style="padding:8px 12px;text-align:right;font-weight:700;color:${l.tax_amount<0?"#b71c1c":"#2e7d32"};">${fmt(l.tax_amount)}</td>
                    </tr>`).join("")}
                    </tbody>
                    <tfoot style="background:#e8eaf6;font-weight:700;font-size:14px;">
                        <tr>
                            <td colspan="4" style="padding:9px 12px;text-align:right;">Net Tax Effect</td>
                            <td style="padding:9px 12px;text-align:right;color:${total_tax<0?"#b71c1c":"#1a237e"};">${fmt(total_tax)}</td>
                        </tr>
                    </tfoot>
                </table>
                <p style="font-size:11px;color:#78909c;margin-top:10px;">
                    ⚠ WHT is shown as negative — it is withheld from the settlement amount and remitted to FIRS separately.
                </p>`;

                frappe.msgprint({ title: "Tax Summary", message: html, wide: true });
            },
        });
    },
});


// ──────────────────────────────────────────────────────────────────────
// ITEMS CHILD TABLE HANDLERS
// ──────────────────────────────────────────────────────────────────────

frappe.ui.form.on("Intercompany Invoice Item", {
    qty(frm)           { frm.trigger("recalculate_totals"); },
    rate(frm)          { frm.trigger("recalculate_totals"); },
    tax_rate(frm)      { frm.trigger("recalculate_totals"); },
    interest_rate(frm) { frm.trigger("recalculate_totals"); },

    item_code(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.item_code) {
            frappe.db.get_value("Item", row.item_code, ["item_name", "description"], (v) => {
                if (v) {
                    frappe.model.set_value(cdt, cdn, "item_name",   v.item_name);
                    frappe.model.set_value(cdt, cdn, "description", v.description);
                }
            });
        }
    },

    items_add(frm)    { frm.trigger("recalculate_totals"); },
    items_remove(frm) { frm.trigger("recalculate_totals"); },
});


// ──────────────────────────────────────────────────────────────────────
// UTILITY
// ──────────────────────────────────────────────────────────────────────

function format_currency(value, currency) {
    return frappe.format(flt(value), { fieldtype: "Currency", currency: currency || "NGN" });
}