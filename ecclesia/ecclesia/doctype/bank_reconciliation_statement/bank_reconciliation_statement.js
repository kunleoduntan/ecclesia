// Copyright (c) 2026, Value Impacts Consulting
// Author: Kunle Oduntan
// ecclesia/ecclesia/doctype/bank_reconciliation_statement/bank_reconciliation_statement.js
//
// ╔══════════════════════════════════════════════════════════════════════════════╗
// ║  BANK RECONCILIATION STATEMENT — DocType Form Script                        ║
// ╠══════════════════════════════════════════════════════════════════════════════╣
// ║  ACCOUNTING POLARITY — CRITICAL                                              ║
// ║                                                                              ║
// ║  BANK STATEMENT (bank's perspective):                                        ║
// ║    Debit  = money LEAVING  your account  → a PAYMENT made by you            ║
// ║    Credit = money ENTERING your account  → a RECEIPT received by you        ║
// ║                                                                              ║
// ║  CASHBOOK / GL (your entity's perspective — MIRROR OPPOSITE):               ║
// ║    Debit  = bank asset INCREASING → a RECEIPT (money came in)               ║
// ║    Credit = bank asset DECREASING → a PAYMENT (money went out)              ║
// ║                                                                              ║
// ║  MATCHING (cross-polarity):                                                  ║
// ║    Bank DR  ↔  Cashbook CR  (both = payment out)                            ║
// ║    Bank CR  ↔  Cashbook DR  (both = receipt in)                             ║
// ║                                                                              ║
// ║  FOUR TABLES:                                                                ║
// ║    Unpresented Cheques  ← Cashbook CR unmatched (payment not yet in bank)   ║
// ║    Uncredited Cheques   ← Cashbook DR unmatched (receipt not yet in bank)   ║
// ║    Direct Withdrawals   ← Bank DR unmatched (not yet in GL) → Payments      ║
// ║    Direct Lodgments     ← Bank CR unmatched (not yet in GL) → Receipts      ║
// ║                                                                              ║
// ║  RECONCILIATION FORMULA:                                                     ║
// ║    Bank Closing Balance                                                      ║
// ║    + Uncredited (cashbook DR not in bank)                                   ║
// ║    − Unpresented (cashbook CR not in bank)                                  ║
// ║    + Direct Lodgments (bank CR not in GL)                                   ║
// ║    − Direct Withdrawals (bank DR not in GL)                                 ║
// ║    = Adjusted Bank Balance                                                   ║
// ║    Adjusted − Cashbook Closing = Variance (→ 0)                             ║
// ╚══════════════════════════════════════════════════════════════════════════════╝

const BRS_PY = 'ecclesia.ecclesia.doctype.bank_reconciliation_statement.bank_reconciliation_statement';

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmtN(v, cur) {
    return new Intl.NumberFormat('en-NG', {
        style: 'currency', currency: cur || 'NGN', minimumFractionDigits: 2
    }).format(parseFloat(v) || 0);
}
function flt(v) { return parseFloat(v) || 0; }
function esc(s) {
    return (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function cstr(v) { return v == null ? '' : String(v); }

// ─── Form Events ─────────────────────────────────────────────────────────────

frappe.ui.form.on('Bank Reconciliation Statement', {

    setup(frm) {
        frm.custom_buttons = {};
    },

    refresh(frm) {
        brs_add_toolbar_buttons(frm);
        brs_render_dashboard(frm);
        brs_colour_status_badge(frm);
        brs_lock_computed_fields(frm);
    },

    company(frm) {
        frm.set_query('bank_account', () => ({ filters: { company: frm.doc.company } }));
    },

    bank_account(frm) {
        if (frm.doc.bank_account) {
            frappe.db.get_value('Bank Account', frm.doc.bank_account, 'account_currency', r => {
                if (r && r.account_currency) {
                    frm.set_value('account_currency', r.account_currency);
                }
            });
        }
    },

    // Recalculate instantly on balance field changes
    bank_statement_closing_balance(frm) { brs_recalc_client(frm); },
    cashbook_closing_balance(frm)       { brs_recalc_client(frm); },

    after_save(frm) {
        brs_render_dashboard(frm);
        brs_colour_status_badge(frm);
    },

    validate(frm) {
        if (frm.doc.from_date && frm.doc.to_date) {
            if (frappe.datetime.str_to_obj(frm.doc.from_date) >
                frappe.datetime.str_to_obj(frm.doc.to_date)) {
                frappe.throw(__('From Date cannot be later than To Date.'));
            }
        }
    },
});

// ─── Child Table Events ───────────────────────────────────────────────────────
// Trigger client recalc when any reconciling child table row changes

['Unpresented Cheque', 'Uncredited Cheque',
 'Direct Withdrawal',  'Direct Lodgment'].forEach(dt => {
    frappe.ui.form.on(dt, {
        credit_amount(frm) { brs_recalc_client(frm); },
        debit_amount(frm)  { brs_recalc_client(frm); },
    });
});


// ═══════════════════════════════════════════════════════════════════════════════
//  TOOLBAR BUTTONS
// ═══════════════════════════════════════════════════════════════════════════════

function brs_add_toolbar_buttons(frm) {
    frm.clear_custom_buttons();
    if (frm.doc.docstatus === 1) return;  // submitted — read only

    // Load Data group
    frm.add_custom_button(__('Fetch GL Entries'),       () => brs_fetch_gl(frm),      __('Load Data'));
    frm.add_custom_button(__('Upload Bank Statement'),  () => brs_upload_dialog(frm), __('Load Data'));

    // AI Tools group
    frm.add_custom_button(__('Run AI Matching'),    () => brs_ai_match_dialog(frm), __('AI Tools'));
    frm.add_custom_button(__('Smart Suggestions'),  () => brs_suggestions(frm),     __('AI Tools'));
    frm.add_custom_button(__('Open in Studio'),     () => frappe.set_route('bank-reconciliation-studio'), __('AI Tools'));

    // Actions group
    frm.add_custom_button(__('Recalculate'), () => brs_server_recalc(frm), __('Actions'));

    const dw = (frm.doc.direct_withdrawals || []).filter(r => flt(r.debit_amount) > 0).length;
    const dl = (frm.doc.direct_lodgments   || []).filter(r => flt(r.credit_amount) > 0).length;
    if (dw + dl > 0) {
        frm.add_custom_button(
            __('Create Payments & Receipts'),
            () => brs_create_transactions(frm),
            __('Actions')
        );
    }

    frm.change_custom_button_type(__('Fetch GL Entries'), __('Load Data'), 'primary');
}


// ═══════════════════════════════════════════════════════════════════════════════
//  DASHBOARD HTML PANEL
// ═══════════════════════════════════════════════════════════════════════════════

function brs_render_dashboard(frm) {
    const doc = frm.doc;
    const cur = doc.account_currency || 'NGN';
    const v   = flt(doc.variance);
    const isR = Math.abs(v) < 0.01;

    const bankRows  = (doc.bank_statement_entries || []).length;
    const cashRows  = (doc.cashbook_entries || []).length;
    const matched   = (doc.bank_statement_entries || []).filter(r => r.rec).length;
    const rate      = bankRows ? Math.round(matched / bankRows * 100) : 0;

    // Reconciling table totals (from child tables — correct fields per table)
    // Unpresented = cashbook CR (payments outstanding) — stored in credit_amount
    const totalUnpresented = (doc.unpresented_cheques || [])
        .reduce((s, r) => s + flt(r.credit_amount), 0);
    // Uncredited = cashbook DR (receipts outstanding) — stored in debit_amount
    const totalUncredited  = (doc.uncredited_cheques || [])
        .reduce((s, r) => s + flt(r.debit_amount), 0);
    // Direct Withdrawals = bank DR (payments not in GL) — stored in debit_amount
    const totalDirWD       = (doc.direct_withdrawals || [])
        .reduce((s, r) => s + flt(r.debit_amount), 0);
    // Direct Lodgments = bank CR (receipts not in GL) — stored in credit_amount
    const totalDirLgmt     = (doc.direct_lodgments || [])
        .reduce((s, r) => s + flt(r.credit_amount), 0);

    const html = `
    <div style="padding:10px 0">

        <!-- KPI strip -->
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(115px,1fr));gap:8px;margin-bottom:14px">
            ${kpi('Bank Rows',        bankRows,                '#6366F1')}
            ${kpi('GL Rows',          cashRows,                '#38BDF8')}
            ${kpi('Matched',          matched,                 '#22C55E')}
            ${kpi('Match Rate',       rate + '%',              rate>=90?'#22C55E':rate>=60?'#F59E0B':'#EF4444')}
            ${kpi('Bank Closing',     fmtN(flt(doc.bank_statement_closing_balance),cur), '#64748B')}
            ${kpi('GL Closing',       fmtN(flt(doc.cashbook_closing_balance),cur),       '#64748B')}
            ${kpi('Adjusted Bank',    fmtN(flt(doc.adjusted_bank_balance),cur),          '#818CF8')}
            ${kpi('Variance',         fmtN(v,cur),             isR?'#22C55E':'#EF4444',  isR)}
        </div>

        <!-- Reconciliation Statement card -->
        <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;
                    padding:14px 18px;margin-bottom:12px">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;
                        letter-spacing:.7px;color:#94A3B8;margin-bottom:10px">
                BANK RECONCILIATION STATEMENT
            </div>
            <table style="width:100%;border-collapse:collapse;font-size:12px">
                ${stmtRow('Balance per Bank Statement (Closing)',
                    fmtN(flt(doc.bank_statement_closing_balance),cur))}

                ${stmtRow(
                    '+ Uncredited Transfers &nbsp;<span style="font-size:10px;color:#94A3B8">' +
                    '(Cashbook DR not yet in bank — receipts in transit)</span>',
                    fmtN(totalUncredited, cur), false, '#22C55E')}

                ${stmtRow(
                    '&minus; Unpresented Transfers &nbsp;<span style="font-size:10px;color:#94A3B8">' +
                    '(Cashbook CR not yet in bank — payments outstanding)</span>',
                    '(' + fmtN(totalUnpresented, cur) + ')', false, '#EF4444')}

                ${stmtRow(
                    '+ Direct Lodgments &nbsp;<span style="font-size:10px;color:#94A3B8">' +
                    '(Bank CR not yet in GL — unposted receipts)</span>',
                    fmtN(totalDirLgmt, cur), false, '#22C55E')}

                ${stmtRow(
                    '&minus; Direct Withdrawals &nbsp;<span style="font-size:10px;color:#94A3B8">' +
                    '(Bank DR not yet in GL — unposted payments)</span>',
                    '(' + fmtN(totalDirWD, cur) + ')', false, '#EF4444')}

                ${stmtRow('= Adjusted Bank Balance',
                    fmtN(flt(doc.adjusted_bank_balance),cur), true)}

                ${stmtRow('Balance per Cashbook / GL (Closing)',
                    fmtN(flt(doc.cashbook_closing_balance),cur))}

                ${stmtRow(
                    isR ? '&#10003; Variance — NIL &nbsp;<em style="font-size:10px">(Fully Reconciled)</em>'
                        : '&#9888; Unexplained Variance',
                    isR ? '&#8358; 0.00' : fmtN(Math.abs(v),cur),
                    true, isR?'#22C55E':'#EF4444')}
            </table>
        </div>

        <!-- Four-table pill row -->
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;font-size:11px">
            ${tablePill('Unpresented<br><small style="color:#94A3B8">Cashbook CR not in bank</small>',
                (doc.unpresented_cheques||[]).length, '#EF4444')}
            ${tablePill('Uncredited<br><small style="color:#94A3B8">Cashbook DR not in bank</small>',
                (doc.uncredited_cheques||[]).length, '#38BDF8')}
            ${tablePill('Direct Withdrawals<br><small style="color:#94A3B8">Bank DR not in GL → Payments</small>',
                (doc.direct_withdrawals||[]).length, '#F59E0B')}
            ${tablePill('Direct Lodgments<br><small style="color:#94A3B8">Bank CR not in GL → Receipts</small>',
                (doc.direct_lodgments||[]).length, '#22C55E')}
        </div>

        ${doc.ai_match_summary ? `
        <div style="margin-top:10px;background:#F5F3FF;border:1px solid #DDD6FE;
                    border-radius:8px;padding:10px 12px;font-size:11px;color:#5B21B6">
            <i class="fa fa-brain" style="margin-right:6px"></i>
            ${esc(doc.ai_match_summary)}
        </div>` : ''}
    </div>`;

    frm.dashboard.add_section(html, __('Reconciliation Summary'));
    frm.dashboard.show();
}

function kpi(label, value, colour, bold) {
    return `
    <div style="background:#fff;border:1px solid #E2E8F0;border-radius:8px;
                padding:9px 10px;text-align:center">
        <div style="font-size:${bold?'16px':'14px'};font-weight:${bold?'800':'700'};
                    color:${colour}">${value}</div>
        <div style="font-size:9px;color:#94A3B8;margin-top:2px;
                    text-transform:uppercase;letter-spacing:.4px">${label}</div>
    </div>`;
}

function stmtRow(label, value, bold, colour) {
    const col = colour || (bold ? '#0F172A' : '#475569');
    const bdr = bold ? 'border-top:1.5px solid #CBD5E1;' : '';
    return `
    <tr style="border-bottom:1px solid #F1F5F9">
        <td style="padding:5px 2px;color:${bold?'#0F172A':'#475569'};
                   font-weight:${bold?'700':'400'};${bdr}">${label}</td>
        <td style="text-align:right;padding:5px 2px;color:${col};
                   font-weight:${bold?'700':'400'};${bdr}">${value}</td>
    </tr>`;
}

function tablePill(label, count, colour) {
    return `
    <div style="background:#fff;border:1px solid #E2E8F0;border-radius:8px;
                padding:9px 10px;text-align:center">
        <div style="font-size:18px;font-weight:800;color:${colour}">${count}</div>
        <div style="font-size:9px;color:#475569;margin-top:2px;line-height:1.4">${label}</div>
    </div>`;
}


// ═══════════════════════════════════════════════════════════════════════════════
//  CLIENT-SIDE INSTANT RECALCULATION
// ═══════════════════════════════════════════════════════════════════════════════

function brs_recalc_client(frm) {
    const doc = frm.doc;

    // Unpresented = cashbook CR not in bank → credit_amount
    const totalUnp  = (doc.unpresented_cheques  || []).reduce((s,r) => s + flt(r.credit_amount), 0);
    // Uncredited = cashbook DR not in bank → debit_amount
    const totalUnc  = (doc.uncredited_cheques   || []).reduce((s,r) => s + flt(r.debit_amount),  0);
    // Direct Withdrawals = bank DR not in GL → debit_amount
    const totalDWD  = (doc.direct_withdrawals   || []).reduce((s,r) => s + flt(r.debit_amount),  0);
    // Direct Lodgments = bank CR not in GL → credit_amount
    const totalDLgmt= (doc.direct_lodgments     || []).reduce((s,r) => s + flt(r.credit_amount), 0);

    const bankBal = flt(doc.bank_statement_closing_balance);
    const cashBal = flt(doc.cashbook_closing_balance);

    // Formula:
    // Adjusted = Bank Closing + Uncredited − Unpresented + Direct Lodgments − Direct Withdrawals
    const adj = bankBal + totalUnc - totalUnp + totalDLgmt - totalDWD;
    const v   = adj - cashBal;

    frm.set_value('adjusted_bank_balance', adj);
    frm.set_value('variance',              v);
    frm.set_value('is_reconciled',         Math.abs(v) < 0.01 ? 1 : 0);
    frm.set_value('status',
        Math.abs(v) < 0.01 ? 'Reconciled' : (doc.from_date ? 'In Progress' : 'Draft'));

    brs_colour_status_badge(frm);
}


// ═══════════════════════════════════════════════════════════════════════════════
//  FETCH GL ENTRIES
// ═══════════════════════════════════════════════════════════════════════════════

function brs_fetch_gl(frm) {
    if (!frm.doc.from_date || !frm.doc.to_date || !frm.doc.bank_account) {
        frappe.msgprint({
            title: __('Missing Fields'),
            message: __('Set Company, Bank Account, From Date and To Date first.'),
            indicator: 'orange',
        });
        return;
    }
    frappe.call({
        method:  `${BRS_PY}.fetch_gl_entries`,
        args:    { docname: frm.doc.name },
        freeze:  true,
        freeze_message: __('Fetching GL entries…'),
        callback(r) {
            if (r.message) {
                frappe.show_alert({
                    message: `${r.message.count} GL entries loaded. ` +
                             `Cashbook closing: ${fmtN(r.message.balance, frm.doc.account_currency)}`,
                    indicator: r.message.count > 0 ? 'green' : 'orange',
                });
                frm.reload_doc();
            }
        },
    });
}


// ═══════════════════════════════════════════════════════════════════════════════
//  AI MATCHING DIALOG
// ═══════════════════════════════════════════════════════════════════════════════

function brs_ai_match_dialog(frm) {
    const bankLen = (frm.doc.bank_statement_entries || []).length;
    const cashLen = (frm.doc.cashbook_entries || []).length;

    if (!bankLen || !cashLen) {
        frappe.msgprint({
            title: __('No Data'),
            message: __('Load bank statement entries and cashbook/GL entries first.'),
            indicator: 'orange',
        });
        return;
    }

    const d = new frappe.ui.Dialog({
        title: __('AI Matching Engine'),
        size:  'large',
        fields: [
            {
                fieldtype: 'HTML', fieldname: 'info',
                options: `
                <div style="background:#EEF2FF;border:1px solid #C7D2FE;border-radius:8px;
                            padding:12px;margin-bottom:12px;font-size:12px;color:#3730A3">
                    <strong>Loaded:</strong> ${bankLen} bank rows · ${cashLen} GL/cashbook rows<br>
                    <strong>Polarity rule:</strong>
                        Bank DR (payment) ↔ Cashbook CR (payment) ·
                        Bank CR (receipt) ↔ Cashbook DR (receipt)<br>
                    <strong>Algorithms:</strong>
                        Levenshtein + Jaccard token + partial containment ·
                        Nigerian bank abbrev expansion · stop-word removal<br>
                    <strong>Score weights:</strong> Amount 50% + Date 25% + Name 25%
                </div>`
            },
            { fieldtype: 'Section Break', label: __('Tolerance Settings') },
            {
                fieldtype: 'Int',   fieldname: 'date_tolerance',
                label: __('Date Tolerance (±days)'),
                default: frm.doc.date_tolerance_days || 3,
                description: __('Bank statement may post 1–3 days after cashbook entry')
            },
            {
                fieldtype: 'Float', fieldname: 'name_threshold',
                label: __('Min Name Similarity (%)'),
                default: frm.doc.name_similarity_threshold || 70,
                description: __('Minimum score for a name to qualify as a candidate match')
            },
            { fieldtype: 'Column Break' },
            {
                fieldtype: 'Float', fieldname: 'amount_tolerance',
                label: __('Amount Tolerance (%)'),
                default: frm.doc.amount_tolerance_pct || 0,
                description: __('Allow small % difference — useful for rounding/charges')
            },
            {
                fieldtype: 'Float', fieldname: 'hi_conf_cutoff',
                label: __('High Confidence Cutoff (%)'),
                default: 85,
                description: __('Pairs above this score are auto-accepted')
            },
            { fieldtype: 'Section Break', label: __('Options') },
            {
                fieldtype: 'Check', fieldname: 'auto_accept_high',
                label: __('Auto-accept all high-confidence pairs'), default: 1
            },
            {
                fieldtype: 'HTML', fieldname: 'progress',
                options: `
                <div id="brs-prog-wrap" style="display:none;margin-top:10px">
                    <div id="brs-prog-msg" style="font-size:12px;color:#64748B;margin-bottom:6px">
                        Running…
                    </div>
                    <div style="height:5px;background:#E2E8F0;border-radius:5px;overflow:hidden">
                        <div id="brs-prog-bar"
                             style="height:100%;background:#6366F1;width:0%;transition:width .4s">
                        </div>
                    </div>
                </div>`
            },
            { fieldtype: 'HTML', fieldname: 'results', options: '' },
        ],
        primary_action_label: __('Run AI Match'),
        primary_action(vals) {
            d.get_primary_btn().prop('disabled', true).text(__('Running…'));
            document.getElementById('brs-prog-wrap').style.display = '';

            const steps = [
                'Normalising bank statement descriptions…',
                'Expanding Nigerian bank abbreviations…',
                'Removing stop-words (LTD, PLC, NIG…)…',
                'Applying cross-polarity rule (Bank DR ↔ GL CR)…',
                'Computing Levenshtein name distance…',
                'Jaccard token overlap…',
                'Partial name containment check…',
                'Applying date ±' + (vals.date_tolerance || 3) + ' day tolerance…',
                'Computing composite confidence scores…',
                'Auto-accepting high-confidence pairs…',
                'Categorising unmatched items…',
                'Done!',
            ];
            let si = 0;
            const iv = setInterval(() => {
                si++;
                const bar = document.getElementById('brs-prog-bar');
                const msg = document.getElementById('brs-prog-msg');
                if (bar) bar.style.width = Math.min(95, Math.round(si / steps.length * 100)) + '%';
                if (msg) msg.textContent = steps[si - 1] || 'Finalising…';
                if (si >= steps.length) clearInterval(iv);
            }, 220);

            frappe.call({
                method: `${BRS_PY}.run_ai_matching`,
                args: {
                    docname:          frm.doc.name,
                    date_tolerance:   vals.date_tolerance  || 3,
                    name_threshold:   vals.name_threshold  || 70,
                    amount_tolerance: vals.amount_tolerance || 0,
                    hi_conf_cutoff:   vals.hi_conf_cutoff  || 85,
                    auto_accept_high: vals.auto_accept_high ? 1 : 0,
                },
                callback(r) {
                    clearInterval(iv);
                    const bar = document.getElementById('brs-prog-bar');
                    if (bar) bar.style.width = '100%';

                    if (!r.message) {
                        d.get_primary_btn().prop('disabled', false).text(__('Run AI Match'));
                        return;
                    }
                    const res = r.message;
                    window.__brs_pairs = res.pairs || [];

                    d.set_df_property('results', 'options', brs_match_html(res));
                    d.get_field('results').refresh();
                    d.get_primary_btn().prop('disabled', false).text(__('Re-run'));
                    d.set_secondary_action_label(__('Apply & Save'));
                    d.set_secondary_action(() => brs_apply(frm, d, window.__brs_pairs));
                },
            });
        },
    });
    d.show();
}

function brs_match_html(res) {
    const pairs  = res.pairs || [];
    const matched = pairs.filter(p => p.bank_idx && p.cash_idx);

    // Summary strip
    let html = `
    <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:6px;margin:12px 0 10px">
        ${mKpi(res.matched,            '#6366F1', 'Matched')}
        ${mKpi(res.high_conf,          '#22C55E', 'High')}
        ${mKpi(res.medium_conf,        '#F59E0B', 'Medium')}
        ${mKpi(res.direct_withdrawals, '#EF4444', 'Direct W/D')}
        ${mKpi(res.direct_lodgments,   '#22C55E', 'Direct Lgmt')}
        ${mKpi(res.match_rate + '%',   res.match_rate>=80?'#22C55E':'#F59E0B', 'Rate')}
    </div>
    <div style="max-height:360px;overflow-y:auto;border:1px solid #E2E8F0;border-radius:8px">`;

    // Matched pairs
    matched.forEach((p, i) => {
        const cc  = p.conf === 'high' ? '#22C55E' : p.conf === 'medium' ? '#F59E0B' : '#EF4444';
        const bg  = p.accepted ? (p.conf === 'high' ? '#F0FDF4' : '#FFFBEB') : '#fff';
        // Bank DR = payment; Bank CR = receipt
        const bLabel = p.bank_polarity === 'BANK_DR' ? 'PAYMENT (Bank DR)' : 'RECEIPT (Bank CR)';
        // Cashbook CR = payment; Cashbook DR = receipt (mirror)
        const cLabel = p.cash_polarity === 'CASH_CR' ? 'PAYMENT (GL CR)' : 'RECEIPT (GL DR)';
        html += `
        <div style="display:grid;grid-template-columns:1fr 72px 1fr 80px;gap:8px;align-items:center;
                    padding:9px 12px;border-bottom:1px solid #F1F5F9;
                    border-left:3px solid ${cc};background:${bg}">
            <div>
                <div style="font-size:11px;font-weight:700;color:#0F172A">
                    ${esc(p.bank_name || '—')}
                </div>
                <div style="font-size:9px;color:#94A3B8">${p.bank_date}</div>
                <div style="font-size:10px;color:${p.bank_polarity==='BANK_DR'?'#EF4444':'#22C55E'};
                            font-weight:600;margin-top:2px">
                    ₦${(p.bank_amt||0).toLocaleString('en-NG',{minimumFractionDigits:2})}
                    &nbsp;<em style="font-weight:400;font-size:9px">${bLabel}</em>
                </div>
            </div>
            <div style="text-align:center">
                <div style="font-size:14px;font-weight:800;color:${cc}">${p.score}%</div>
                <div style="font-size:9px;color:#94A3B8">${p.conf}</div>
                <div style="font-size:8px;color:#CBD5E1">↔</div>
            </div>
            <div>
                <div style="font-size:11px;font-weight:700;color:#0F172A">
                    ${esc(p.cash_name || '—')}
                </div>
                <div style="font-size:9px;color:#94A3B8">${p.cash_date} · ${esc(p.cash_ref||'GL')}</div>
                <div style="font-size:10px;color:${p.cash_polarity==='CASH_CR'?'#EF4444':'#22C55E'};
                            font-weight:600;margin-top:2px">
                    ₦${(p.cash_amt||0).toLocaleString('en-NG',{minimumFractionDigits:2})}
                    &nbsp;<em style="font-weight:400;font-size:9px">${cLabel}</em>
                </div>
            </div>
            <div style="text-align:right">
                <label style="display:flex;align-items:center;gap:4px;
                              justify-content:flex-end;cursor:pointer">
                    <input type="checkbox" data-pair="${i}"
                        ${p.accepted ? 'checked' : ''}
                        onchange="(function(el){
                            var idx=parseInt(el.dataset.pair);
                            if(window.__brs_pairs&&window.__brs_pairs[idx])
                                window.__brs_pairs[idx].accepted=el.checked;
                        })(this)"
                        style="width:14px;height:14px;accent-color:#6366F1">
                    <span style="font-size:10px;color:#64748B">Accept</span>
                </label>
            </div>
        </div>`;
    });

    // Bank-only unmatched rows (Direct Withdrawals / Direct Lodgments)
    pairs.filter(p => p.bank_idx && !p.cash_idx).forEach(p => {
        const isDW  = p.unmatched_category === 'direct_withdrawal';
        const label = isDW ? '→ Direct Withdrawal (Bank DR — create Payment)'
                           : '→ Direct Lodgment (Bank CR — create Receipt)';
        const col   = isDW ? '#F59E0B' : '#22C55E';
        html += `
        <div style="padding:9px 12px;border-bottom:1px solid #F1F5F9;
                    border-left:3px solid ${col};background:${isDW?'#FFFBEB':'#F0FDF4'}">
            <div style="font-size:10px;color:${isDW?'#92400E':'#14532D'};font-weight:700">${label}</div>
            <div style="font-size:11px;color:#0F172A;margin-top:2px">
                ${esc(p.bank_name)}
                — ₦${(p.bank_amt||0).toLocaleString('en-NG',{minimumFractionDigits:2})}
                on ${p.bank_date}
            </div>
        </div>`;
    });

    // Cashbook-only unmatched rows (Unpresented / Uncredited)
    pairs.filter(p => !p.bank_idx && p.cash_idx).forEach(p => {
        const isUnp = p.unmatched_category === 'unpresented_cheque';
        // Unpresented = cashbook CR (payment) | Uncredited = cashbook DR (receipt)
        const label = isUnp
            ? '→ Unpresented Transfer (Cashbook CR — payment not yet cleared by bank)'
            : '→ Uncredited Transfer (Cashbook DR — receipt not yet credited by bank)';
        const col = isUnp ? '#EF4444' : '#38BDF8';
        html += `
        <div style="padding:9px 12px;border-bottom:1px solid #F1F5F9;
                    border-left:3px solid ${col};background:${isUnp?'#FEF2F2':'#F0F9FF'}">
            <div style="font-size:10px;color:${isUnp?'#991B1B':'#075985'};font-weight:700">${label}</div>
            <div style="font-size:11px;color:#0F172A;margin-top:2px">
                ${esc(p.cash_name)}
                — ₦${(p.cash_amt||0).toLocaleString('en-NG',{minimumFractionDigits:2})}
                on ${p.cash_date}
                ${p.cash_ref ? '· ' + esc(p.cash_ref) : ''}
            </div>
        </div>`;
    });

    html += '</div>';
    return html;
}

function mKpi(val, col, lbl) {
    return `<div style="text-align:center;background:#F8FAFC;border-radius:8px;padding:8px 4px">
        <div style="font-size:16px;font-weight:800;color:${col}">${val}</div>
        <div style="font-size:9px;color:#94A3B8">${lbl}</div>
    </div>`;
}

function brs_apply(frm, d, pairs) {
    if (!pairs || !pairs.length) {
        frappe.show_alert({ message: __('No pairs to apply.'), indicator: 'orange' });
        return;
    }
    frappe.call({
        method:  `${BRS_PY}.apply_matches`,
        args:    { docname: frm.doc.name, pairs_json: JSON.stringify(pairs) },
        freeze:  true,
        freeze_message: __('Saving reconciliation…'),
        callback(r) {
            if (r.message && r.message.status === 'success') {
                d.hide();
                frappe.show_alert({ message: __('Matches applied and saved.'), indicator: 'green' });
                frm.reload_doc();
            }
        },
    });
}


// ═══════════════════════════════════════════════════════════════════════════════
//  UPLOAD BANK STATEMENT DIALOG
// ═══════════════════════════════════════════════════════════════════════════════

function brs_upload_dialog(frm) {
    let uploaded_url = '';

    const d = new frappe.ui.Dialog({
        title: __('Upload Bank Statement'),
        size:  'extra-large',
        fields: [
            {
                fieldtype: 'HTML', fieldname: 'polarity_note',
                options: `
                <div style="background:#FEF9C3;border:1px solid #FDE047;border-radius:8px;
                            padding:10px 12px;margin-bottom:12px;font-size:11px;color:#713F12">
                    <strong>Bank Statement polarity:</strong>
                    Debit column = money <strong>leaving</strong> your account (payments made) ·
                    Credit column = money <strong>entering</strong> your account (receipts received)
                </div>`
            },
            {
                fieldtype: 'Attach', fieldname: 'file_url',
                label: __('Select File (.xlsx, .xls, .csv)'),
                onchange() {
                    const url = d.get_value('file_url');
                    if (!url) return;
                    uploaded_url = url;
                    frappe.call({
                        method: 'ecclesia.ecclesia.page.bank_reconciliation_studio.' +
                                'bank_reconciliation_studio.preview_uploaded_file',
                        args: { file_url: url },
                        callback(r) {
                            if (!r.message) return;
                            const cols  = r.message.columns || [];
                            const opts  = '\n' + cols.join('\n');
                            ['date_col','party_col','debit_col','credit_col','amt_col'].forEach(f => {
                                d.set_df_property(f, 'options', opts);
                                d.get_field(f).refresh();
                            });
                            d.set_df_property('preview_html', 'options',
                                brs_preview_tbl(cols, r.message.preview));
                            d.get_field('preview_html').refresh();
                        },
                    });
                },
            },
            { fieldtype: 'Section Break', label: __('Column Mapping') },
            {
                fieldtype: 'Select', fieldname: 'date_col',
                label: __('Date Column'), options: '',
            },
            {
                fieldtype: 'Select', fieldname: 'party_col',
                label: __('Narration / Party Column'), options: '',
            },
            { fieldtype: 'Column Break' },
            {
                fieldtype: 'Select', fieldname: 'debit_col',
                label: __('Debit Column (money out / payments)'), options: '',
            },
            {
                fieldtype: 'Select', fieldname: 'credit_col',
                label: __('Credit Column (money in / receipts)'), options: '',
            },
            { fieldtype: 'Section Break', label: __('Amount Format') },
            {
                fieldtype: 'Select', fieldname: 'amount_format',
                label: __('Amount Column Format'),
                options: 'drcr\nsingle\nsingle_inv\ndrcr_flag',
                default:  'drcr',
                description: __(
                    'drcr = separate Debit (payment) and Credit (receipt) columns · ' +
                    'single = one column: positive=credit/receipt, negative=debit/payment · ' +
                    'single_inv = reversed: positive=debit/payment, negative=credit/receipt · ' +
                    'drcr_flag = amount column + DR/CR flag column'
                ),
            },
            {
                fieldtype: 'Select', fieldname: 'amt_col',
                label: __('Amount Column (for single ± or flag formats)'), options: '',
            },
            { fieldtype: 'Column Break' },
            {
                fieldtype: 'Int',   fieldname: 'header_row',
                label: __('Header Row Number'), default: 1,
            },
            {
                fieldtype: 'Check', fieldname: 'clear_existing',
                label: __('Clear Existing Bank Statement Entries'), default: 0,
            },
            { fieldtype: 'Section Break', label: __('File Preview') },
            {
                fieldtype: 'HTML', fieldname: 'preview_html',
                options: '<p style="font-size:12px;color:#94A3B8">Upload a file to preview…</p>',
            },
        ],
        primary_action_label: __('Import'),
        primary_action(vals) {
            if (!uploaded_url) {
                frappe.show_alert({ message: __('Select a file first.'), indicator: 'orange' });
                return;
            }
            frappe.call({
                method: 'ecclesia.ecclesia.page.bank_reconciliation_studio.' +
                        'bank_reconciliation_studio.import_bank_statement_file',
                args: {
                    docname:        frm.doc.name,
                    file_url:       uploaded_url,
                    date_col:       vals.date_col,
                    party_col:      vals.party_col,
                    debit_col:      vals.debit_col,
                    credit_col:     vals.credit_col,
                    amt_col:        vals.amt_col || '',
                    amount_format:  vals.amount_format || 'drcr',
                    header_row:     vals.header_row || 1,
                    clear_existing: vals.clear_existing ? 1 : 0,
                },
                freeze: true,
                freeze_message: __('Importing bank statement…'),
                callback(r) {
                    if (r.message) {
                        const m = r.message;
                        frappe.show_alert({
                            message: `Imported: ${m.imported} · Skipped: ${m.skipped} · Errors: ${m.errors}`,
                            indicator: m.errors > 0 ? 'orange' : 'green',
                        });
                        d.hide();
                        frm.reload_doc();
                    }
                },
            });
        },
    });
    d.show();
}

function brs_preview_tbl(columns, rows) {
    if (!columns || !columns.length) return '';
    let h = '<div style="overflow-x:auto;max-height:200px">' +
            '<table style="width:100%;border-collapse:collapse;font-size:11px"><thead><tr>';
    columns.forEach(c => {
        h += `<th style="padding:5px 8px;background:#F1F5F9;border:1px solid #E2E8F0;
                         white-space:nowrap;color:#334155">${esc(c)}</th>`;
    });
    h += '</tr></thead><tbody>';
    (rows || []).forEach(row => {
        h += '<tr>';
        (row || []).forEach(cell => {
            h += `<td style="padding:4px 8px;border:1px solid #F1F5F9;
                             white-space:nowrap;color:#475569">${esc(cstr(cell))}</td>`;
        });
        h += '</tr>';
    });
    h += '</tbody></table></div>';
    return h;
}


// ═══════════════════════════════════════════════════════════════════════════════
//  SMART SUGGESTIONS
// ═══════════════════════════════════════════════════════════════════════════════

function brs_suggestions(frm) {
    frappe.call({
        method:  `${BRS_PY}.get_smart_suggestions`,
        args:    { docname: frm.doc.name },
        callback(r) {
            const tips = r.message || [];
            if (!tips.length) {
                frappe.msgprint({ title: __('Smart Suggestions'),
                    message: __('No suggestions at this time.'), indicator: 'green' });
                return;
            }
            const COLOUR = { critical:'#EF4444', warning:'#F59E0B', success:'#22C55E', info:'#6366F1' };
            const BG     = { critical:'#FEF2F2', warning:'#FFFBEB', success:'#F0FDF4', info:'#EEF2FF' };
            let html = '';
            tips.forEach(t => {
                const col = COLOUR[t.priority] || COLOUR.info;
                const bg  = BG[t.priority]     || BG.info;
                html += `
                <div style="background:${bg};border:1px solid ${col}33;
                            border-left:4px solid ${col};border-radius:8px;
                            padding:11px 14px;margin-bottom:10px">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
                        <i class="fa ${t.icon}" style="color:${col};font-size:13px"></i>
                        <span style="font-size:12px;font-weight:700;color:${col}">${esc(t.title)}</span>
                    </div>
                    <div style="font-size:11px;color:#475569">${esc(t.desc)}</div>
                </div>`;
            });
            new frappe.ui.Dialog({
                title:  __('Smart Suggestions'),
                size:   'large',
                fields: [{ fieldtype:'HTML', fieldname:'tips', options: html }],
            }).show();
        },
    });
}


// ═══════════════════════════════════════════════════════════════════════════════
//  CREATE TRANSACTIONS
// ═══════════════════════════════════════════════════════════════════════════════

function brs_create_transactions(frm) {
    const dw = (frm.doc.direct_withdrawals || []).filter(r => flt(r.debit_amount) > 0).length;
    const dl = (frm.doc.direct_lodgments   || []).filter(r => flt(r.credit_amount) > 0).length;

    frappe.confirm(
        __(`This will create:<br><br>
            &bull; <strong>${dw} Payment(s)</strong> for Direct Withdrawals<br>
            &nbsp;&nbsp;&nbsp;&nbsp;<em>(Bank DR not yet in GL — money already left your account)</em><br><br>
            &bull; <strong>${dl} Receipt(s)</strong> for Direct Lodgments<br>
            &nbsp;&nbsp;&nbsp;&nbsp;<em>(Bank CR not yet in GL — money already in your account)</em><br><br>
            Duplicate-safe: existing Payments/Receipts with same date + amount + reference will be skipped.<br><br>
            Continue?`),
        () => {
            frappe.call({
                method:  `${BRS_PY}.create_transactions_for_unmatched`,
                args:    { docname: frm.doc.name },
                freeze:  true,
                freeze_message: __('Creating Payments and Receipts…'),
                callback(r) {
                    if (r.message) {
                        const m = r.message;
                        frappe.show_alert({
                            message: `Created: ${m.created_payments} Payment(s) · ` +
                                     `${m.created_receipts} Receipt(s) · ` +
                                     `Skipped: ${m.skipped_payments + m.skipped_receipts}`,
                            indicator: m.errors > 0 ? 'orange' : 'green',
                        });
                        frm.reload_doc();
                    }
                },
            });
        }
    );
}


// ═══════════════════════════════════════════════════════════════════════════════
//  SERVER RECALCULATE
// ═══════════════════════════════════════════════════════════════════════════════

function brs_server_recalc(frm) {
    frappe.call({
        method:  `${BRS_PY}.recalculate`,
        args:    { docname: frm.doc.name },
        callback(r) {
            if (r.message) {
                const m = r.message;
                frm.set_value('adjusted_bank_balance', m.adjusted_bank_balance);
                frm.set_value('variance',              m.variance);
                frm.set_value('status',                m.status);
                frm.set_value('is_reconciled',         m.is_reconciled);
                brs_render_dashboard(frm);
                brs_colour_status_badge(frm);
                frappe.show_alert({ message: __('Recalculated.'), indicator: 'green' });
            }
        },
    });
}


// ═══════════════════════════════════════════════════════════════════════════════
//  STATUS & READONLY HELPERS
// ═══════════════════════════════════════════════════════════════════════════════

function brs_colour_status_badge(frm) {
    const COLOUR = {
        Draft:         '#94A3B8',
        'In Progress': '#F59E0B',
        Reconciled:    '#22C55E',
        Amended:       '#6366F1',
    };
    const col = COLOUR[frm.doc.status] || '#94A3B8';
    setTimeout(() => {
        const el = frm.fields_dict['status'] && frm.fields_dict['status'].$wrapper;
        if (el) el.find('.control-value').css({ color: col, fontWeight: '700' });
    }, 200);
}

function brs_lock_computed_fields(frm) {
    [
        'adjusted_bank_balance', 'variance', 'is_reconciled',
        'auto_accepted_count', 'manually_matched_count', 'ai_match_summary',
        'total_unpresented', 'total_uncredited', 'total_direct_wd', 'total_direct_lgmt',
        'total_bank_debit', 'total_bank_credit',
        'total_cashbook_debit', 'total_cashbook_credit',
    ].forEach(f => {
        if (frm.fields_dict[f]) frm.set_df_property(f, 'read_only', 1);
    });
}