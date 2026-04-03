

frappe.pages["gl-analytical-review"].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "📊 GL Analytical Review — ISA 520",
        single_column: true
    });

    // Date filters
    const today = frappe.datetime.get_today();
    const first_this_month  = frappe.datetime.month_start();
    const last_this_month   = frappe.datetime.month_end(0);
    const first_prior_month = frappe.datetime.add_months(first_this_month, -1);
    const last_prior_month  = frappe.datetime.add_days(first_this_month, -1);

    page.add_field({ fieldtype: "Date", label: "Current Period From",
                     fieldname: "from_date", default: first_this_month });
    page.add_field({ fieldtype: "Date", label: "Current Period To",
                     fieldname: "to_date", default: last_this_month });
    page.add_field({ fieldtype: "Date", label: "Prior Period From",
                     fieldname: "prior_from", default: first_prior_month });
    page.add_field({ fieldtype: "Date", label: "Prior Period To",
                     fieldname: "prior_to", default: last_prior_month });
    page.add_field({ fieldtype: "Percent", label: "Flag Threshold %",
                     fieldname: "threshold_pct", default: 50 });
    page.add_field({ fieldtype: "Currency", label: "Min Amount",
                     fieldname: "min_amount", default: 10000 });

    page.set_primary_action("Run Review", run_review, "octicon octicon-graph");

    page.main.html(`
        <div id="gl-review-root" style="padding:20px;">
            <div style="background:#e8f4fd; border-left:4px solid #2980b9; padding:16px; border-radius:4px;">
                <b>ISA 520 — Analytical Procedures</b><br>
                Set the current and prior period dates above, then click <b>Run Review</b> to
                compare GL account balances, detect unusual movements, analyse suspense accounts,
                and review journal entry patterns.
            </div>
        </div>
    `);

    function run_review() {
        const from_date    = page.fields_dict.from_date.get_value();
        const to_date      = page.fields_dict.to_date.get_value();
        const prior_from   = page.fields_dict.prior_from.get_value();
        const prior_to     = page.fields_dict.prior_to.get_value();
        const threshold_pct= page.fields_dict.threshold_pct.get_value() || 50;
        const min_amount   = page.fields_dict.min_amount.get_value() || 10000;

        if (!from_date || !to_date || !prior_from || !prior_to) {
            frappe.msgprint("Please fill in all date fields.");
            return;
        }

        $("#gl-review-root").html(`
            <div style="text-align:center; padding:40px; color:#888;">
                <i class="fa fa-spinner fa-spin fa-2x"></i>
                <p>Running GL Analytical Review...</p>
            </div>
        `);

        frappe.call({
            method: "ecclesia.api.gl_review.get_analytical_review",
            args: { from_date, to_date, prior_from_date: prior_from,
                    prior_to_date: prior_to, threshold_pct, min_amount },
            callback: function (r) {
                if (r.message) {
                    render_review(r.message);
                }
            }
        });
    }

    function render_review(data) {
        const root = $("#gl-review-root");
        root.html("");

        const s = data.summary;
        const je = data.je_summary || {};

        // ── Summary KPIs ──────────────────────────────────────────────────────
        root.append(`
            <div style="display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:20px;">
                ${kpi("Accounts Analysed", s.total_accounts_current, "#2980b9")}
                ${kpi("Flagged Accounts", s.flagged_count, "#e74c3c")}
                ${kpi("Total JVs", je.total_jes || 0, "#8e44ad")}
                ${kpi("JVs No Narration", je.no_narration || 0, "#e67e22")}
            </div>
            <div style="background:#f0f8ff; border-left:4px solid #2980b9; padding:12px;
                        border-radius:4px; font-size:13px; margin-bottom:20px;">
                Comparing <b>${s.from_date} → ${s.to_date}</b>
                vs prior period <b>${s.prior_from} → ${s.prior_to}</b>
            </div>
        `);

        // ── Flagged Accounts ───────────────────────────────────────────────────
        const flag_section = section("🚩 Flagged Accounts (Unusual Movements)");
        root.append(flag_section);
        render_flagged_table(flag_section.find(".section-body"), data.flagged_accounts);

        // ── Suspense Accounts ──────────────────────────────────────────────────
        const susp_section = section("⚠️ Suspense / Clearing Account Usage");
        root.append(susp_section);
        render_suspense_table(susp_section.find(".section-body"), data.suspense_usage);

        // ── Period-end Clustering ──────────────────────────────────────────────
        const pe_section = section("📅 Period-End Transaction Clustering");
        root.append(pe_section);
        render_period_end(pe_section.find(".section-body"), data.period_end_entries);

        // ── JE Analysis ────────────────────────────────────────────────────────
        const je_section = section("📝 Journal Entry Risk Analysis (ACFE)");
        root.append(je_section);
        render_je_summary(je_section.find(".section-body"), je);

        // ── All Accounts ───────────────────────────────────────────────────────
        const all_section = section("📋 All Account Movements (Top 50 by Absolute Change)");
        root.append(all_section);
        render_all_accounts(all_section.find(".section-body"), data.all_accounts);
    }

    function kpi(label, value, color) {
        return `
            <div style="background:#fff; border-radius:6px; padding:16px;
                        box-shadow:0 2px 6px rgba(0,0,0,0.07); text-align:center;">
                <div style="font-size:28px; font-weight:700; color:${color};">${value}</div>
                <div style="font-size:11px; color:#666; text-transform:uppercase;">${label}</div>
            </div>`;
    }

    function section(title) {
        return $(`
            <div style="background:#fff; border-radius:8px; padding:20px; margin-bottom:20px;
                        box-shadow:0 2px 8px rgba(0,0,0,0.07);">
                <h5 style="margin:0 0 14px 0; padding-bottom:8px; border-bottom:2px solid #ecf0f1;
                           font-size:14px;">${title}</h5>
                <div class="section-body"></div>
            </div>
        `);
    }

    function render_flagged_table(container, accounts) {
        if (!accounts || !accounts.length) {
            container.html("<p style='color:#27ae60; text-align:center; padding:12px;'>✅ No accounts flagged for unusual movements.</p>");
            return;
        }

        let rows = accounts.map(a => {
            const chg_color = a.change_pct > 0 ? "#27ae60" : "#c0392b";
            return `
                <tr>
                    <td style="padding:7px; font-size:12px; font-weight:600;">${a.account}</td>
                    <td style="padding:7px; font-size:11px; color:#666;">${a.root_type || '—'}</td>
                    <td style="padding:7px; text-align:right;">${fmt(a.prior)}</td>
                    <td style="padding:7px; text-align:right; font-weight:600;">${fmt(a.current)}</td>
                    <td style="padding:7px; text-align:right; color:${chg_color}; font-weight:600;">
                        ${a.change_pct > 0 ? '+' : ''}${a.change_pct}%
                    </td>
                    <td style="padding:7px; font-size:11px; color:#e67e22;">${a.flag_reasons}</td>
                    <td style="padding:7px; text-align:center;">
                        <button class="btn btn-xs btn-danger btn-flag-finding"
                                data-account="${a.account}"
                                data-pct="${a.change_pct}"
                                data-reason="${a.flag_reasons}">
                            Raise Finding
                        </button>
                    </td>
                </tr>`;
        }).join("");

        container.html(`
            <table style="width:100%; border-collapse:collapse; font-size:12px;">
                <thead><tr style="background:#2c3e50; color:#fff;">
                    <th style="padding:7px;">Account</th>
                    <th style="padding:7px;">Type</th>
                    <th style="padding:7px; text-align:right;">Prior Period</th>
                    <th style="padding:7px; text-align:right;">Current Period</th>
                    <th style="padding:7px; text-align:right;">Change %</th>
                    <th style="padding:7px;">Flag Reason</th>
                    <th style="padding:7px;">Action</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
        `);

        container.find(".btn-flag-finding").on("click", function () {
            const btn = $(this);
            frappe.call({
                method: "ecclesia.api.findings.create_finding",
                args: {
                    reference_doctype: "GL Entry",
                    reference_name:    btn.data("account"),
                    finding_title:     `GL Analytical Review: Unusual Movement — ${btn.data("account")}`,
                    risk_rating:       Math.abs(btn.data("pct")) > 100 ? "High" : "Medium",
                    finding_type:      "GL Posting Error",
                    observation:       `ISA 520 Analytical Review flagged account ${btn.data("account")}: ${btn.data("reason")}`,
                    source:            "Continuous Monitoring"
                },
                callback: function (r) {
                    if (r.message) {
                        btn.text("✅ Raised").prop("disabled", true).addClass("btn-success").removeClass("btn-danger");
                    }
                }
            });
        });
    }

    function render_suspense_table(container, items) {
        if (!items || !items.length) {
            container.html("<p style='color:#27ae60; text-align:center; padding:12px;'>✅ No suspense/clearing account usage detected.</p>");
            return;
        }
        let rows = items.map(i => `
            <tr>
                <td style="padding:7px; color:#e74c3c; font-weight:600;">${i.account}</td>
                <td style="padding:7px;">${i.voucher_type}</td>
                <td style="padding:7px;"><a href="/app/${frappe.router.slug(i.voucher_type)}/${i.voucher_no}">${i.voucher_no}</a></td>
                <td style="padding:7px;">${i.posting_date}</td>
                <td style="padding:7px; text-align:right; font-weight:600;">${fmt(i.amount)}</td>
                <td style="padding:7px; font-size:11px;">${i.remarks || '—'}</td>
            </tr>`).join("");

        container.html(`
            <p style="color:#e74c3c; font-size:12px; margin-bottom:8px;">
                ⚠️ ${items.length} suspense/clearing account posting(s) detected. 
                All require immediate reclassification.
            </p>
            <table style="width:100%; border-collapse:collapse; font-size:12px;">
                <thead><tr style="background:#c0392b; color:#fff;">
                    <th style="padding:7px;">Account</th>
                    <th style="padding:7px;">Voucher Type</th>
                    <th style="padding:7px;">Voucher No</th>
                    <th style="padding:7px;">Date</th>
                    <th style="padding:7px; text-align:right;">Amount</th>
                    <th style="padding:7px;">Remarks</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
        `);
    }

    function render_period_end(container, items) {
        if (!items || !items.length) {
            container.html("<p style='color:#888;'>No data.</p>"); return;
        }
        let rows = items.map(i => {
            const pct = i.total_count > 0 ? ((i.period_end_count / i.total_count) * 100).toFixed(1) : 0;
            const flag = pct > 30 ? "🚩 High concentration" : "";
            return `
                <tr style="background:${pct > 30 ? '#fff8e1':'#fff'};">
                    <td style="padding:7px;">${i.month}</td>
                    <td style="padding:7px; text-align:right;">${i.total_count}</td>
                    <td style="padding:7px; text-align:right; font-weight:600;">${i.period_end_count}</td>
                    <td style="padding:7px; text-align:right;">${fmt(i.period_end_amount)}</td>
                    <td style="padding:7px; text-align:right; color:${pct>30?'#e67e22':'#27ae60'};">
                        ${pct}%
                    </td>
                    <td style="padding:7px; color:#e67e22; font-size:11px;">${flag}</td>
                </tr>`;
        }).join("");

        container.html(`
            <p style="font-size:12px; color:#666; margin-bottom:8px;">
                Transactions on days 28–31 of each month. High concentration (>30%) may indicate window dressing.
            </p>
            <table style="width:100%; border-collapse:collapse; font-size:12px;">
                <thead><tr style="background:#2c3e50; color:#fff;">
                    <th style="padding:7px;">Month</th>
                    <th style="padding:7px; text-align:right;">Total Entries</th>
                    <th style="padding:7px; text-align:right;">Period-end Entries</th>
                    <th style="padding:7px; text-align:right;">Amount</th>
                    <th style="padding:7px; text-align:right;">% at Period-end</th>
                    <th style="padding:7px;">Flag</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
        `);
    }

    function render_je_summary(container, je) {
        const round_flag = (je.round_amounts || 0) > 0
            ? `<span style="color:#c0392b;">🚩 ${je.round_amounts} round-number JV(s) — ACFE fraud indicator</span>` : "✅ None";
        const narration_flag = (je.no_narration || 0) > 0
            ? `<span style="color:#e67e22;">⚠️ ${je.no_narration} JV(s) with no narration</span>` : "✅ All JVs have narration";

        container.html(`
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; font-size:13px;">
                <div>
                    <p><b>Total Journal Entries:</b> ${je.total_jes || 0}</p>
                    <p><b>Total Amount:</b> ${fmt(je.total_amount || 0)}</p>
                </div>
                <div>
                    <p><b>Round Number JVs:</b> ${round_flag}</p>
                    <p><b>Missing Narration:</b> ${narration_flag}</p>
                </div>
            </div>
            <div style="margin-top:8px;">
                <a href="/app/journal-entry" style="font-size:12px;">View all Journal Entries →</a>
                &nbsp;|&nbsp;
                <a href="/app/audit-finding?finding_type=Non-Finance User JV" style="font-size:12px;">JV Findings →</a>
            </div>
        `);
    }

    function render_all_accounts(container, accounts) {
        if (!accounts || !accounts.length) {
            container.html("<p style='color:#888;'>No account data.</p>"); return;
        }
        let rows = accounts.map(a => `
            <tr style="background:${a.flagged?'#fff8e1':'#fff'};">
                <td style="padding:6px; font-size:12px;">${a.account}</td>
                <td style="padding:6px; font-size:11px; color:#666;">${a.root_type || '—'}</td>
                <td style="padding:6px; text-align:right; font-size:12px;">${fmt(a.prior)}</td>
                <td style="padding:6px; text-align:right; font-size:12px; font-weight:600;">${fmt(a.current)}</td>
                <td style="padding:6px; text-align:right; font-size:12px;
                           color:${a.change_pct > 0 ? '#27ae60' : '#c0392b'};">
                    ${a.change_pct > 0 ? '+' : ''}${a.change_pct}%
                </td>
                <td style="padding:6px; font-size:11px; color:#e67e22;">${a.flag_reasons || ''}</td>
            </tr>`).join("");

        container.html(`
            <table style="width:100%; border-collapse:collapse;">
                <thead><tr style="background:#2c3e50; color:#fff; font-size:12px;">
                    <th style="padding:6px;">Account</th>
                    <th style="padding:6px;">Type</th>
                    <th style="padding:6px; text-align:right;">Prior</th>
                    <th style="padding:6px; text-align:right;">Current</th>
                    <th style="padding:6px; text-align:right;">Change %</th>
                    <th style="padding:6px;">Notes</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
        `);
    }

    function fmt(val) {
        return frappe.utils.format_number(val || 0, null, 2);
    }
};