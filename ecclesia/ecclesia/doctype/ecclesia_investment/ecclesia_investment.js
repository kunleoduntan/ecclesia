// ============================================================================
// ECCLESIA INVESTMENT MANAGEMENT - CLIENT SCRIPT
// Module: Ecclesia | DocType: Ecclesia Investment
// Handles: Money Market, Shares, Bonds, T-Bills, Fixed Deposits
// Interest Modes: Upfront | At Maturity | Periodic | Combinations
// WHT: Per period, upfront, maturity, dividend
// ============================================================================

'use strict';

// ---------------------------------------------------------------------------
// GLOBAL STATE
// ---------------------------------------------------------------------------
const ECC_INV = {
    loading: false,
    styles_loaded: false,
};

// ---------------------------------------------------------------------------
// STYLES
// ---------------------------------------------------------------------------
$(document).ready(function () {
    _inject_styles();
});

function _inject_styles() {
    if ($('#ecc-inv-styles').length) return;
    const css = `
        :root {
            --ecc-blue:    #1e40af;
            --ecc-sky:     #0ea5e9;
            --ecc-green:   #059669;
            --ecc-amber:   #d97706;
            --ecc-red:     #dc2626;
            --ecc-purple:  #7c3aed;
            --ecc-slate:   #475569;
            --ecc-border:  #e2e8f0;
            --ecc-surface: #ffffff;
            --ecc-bg:      #f8fafc;
            --ecc-radius:  10px;
            --ecc-shadow:  0 2px 8px rgba(0,0,0,0.08);
        }

        /* ── HERO BANNER ── */
        .ecc-hero {
            background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 50%, #0369a1 100%);
            border-radius: var(--ecc-radius);
            padding: 24px 28px;
            margin-bottom: 20px;
            color: #fff;
            position: relative;
            overflow: hidden;
        }
        .ecc-hero::after {
            content: '₦';
            position: absolute;
            right: 24px; top: 50%;
            transform: translateY(-50%);
            font-size: 96px;
            opacity: 0.07;
            font-weight: 900;
            line-height: 1;
        }
        .ecc-hero-title {
            font-size: 22px;
            font-weight: 700;
            margin: 0 0 4px 0;
        }
        .ecc-hero-subtitle {
            font-size: 13px;
            opacity: 0.8;
            margin: 0;
        }
        .ecc-hero-badges {
            display: flex;
            gap: 8px;
            margin-top: 14px;
            flex-wrap: wrap;
        }
        .ecc-badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: .4px;
            text-transform: uppercase;
        }
        .ecc-badge-white { background: rgba(255,255,255,0.2); color: #fff; border: 1px solid rgba(255,255,255,0.3); }
        .ecc-badge-green { background: #d1fae5; color: #065f46; }
        .ecc-badge-amber { background: #fef3c7; color: #92400e; }
        .ecc-badge-red   { background: #fee2e2; color: #991b1b; }

        /* ── KPI STRIP ── */
        .ecc-kpi-strip {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 14px;
            margin: 16px 0 20px;
        }
        .ecc-kpi {
            background: var(--ecc-surface);
            border: 1px solid var(--ecc-border);
            border-radius: var(--ecc-radius);
            padding: 16px 20px;
            position: relative;
            overflow: hidden;
            transition: box-shadow .2s, transform .2s;
        }
        .ecc-kpi:hover { box-shadow: var(--ecc-shadow); transform: translateY(-2px); }
        .ecc-kpi-accent {
            position: absolute;
            left: 0; top: 0; bottom: 0;
            width: 4px;
            border-radius: 10px 0 0 10px;
        }
        .ecc-kpi-label {
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: .6px;
            font-weight: 700;
            color: #94a3b8;
            margin-bottom: 6px;
        }
        .ecc-kpi-value {
            font-size: 20px;
            font-weight: 800;
            color: #1e293b;
            line-height: 1.2;
        }
        .ecc-kpi-sub {
            font-size: 11px;
            color: #64748b;
            margin-top: 4px;
        }

        /* ── ACTION BAR ── */
        .ecc-action-bar {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 20px;
            padding: 16px 20px;
            background: var(--ecc-surface);
            border: 1px solid var(--ecc-border);
            border-radius: var(--ecc-radius);
        }
        .ecc-btn {
            padding: 9px 18px;
            border-radius: 7px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            border: none;
            display: inline-flex;
            align-items: center;
            gap: 7px;
            transition: all .2s;
        }
        .ecc-btn-primary   { background: var(--ecc-blue); color: #fff; }
        .ecc-btn-primary:hover { background: #1e3a8a; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(30,64,175,.35); }
        .ecc-btn-success   { background: var(--ecc-green); color: #fff; }
        .ecc-btn-success:hover { background: #047857; transform: translateY(-1px); }
        .ecc-btn-outline   { background: #fff; color: var(--ecc-slate); border: 1px solid var(--ecc-border); }
        .ecc-btn-outline:hover { border-color: var(--ecc-blue); color: var(--ecc-blue); background: #eff6ff; }
        .ecc-btn-danger    { background: var(--ecc-red); color: #fff; }
        .ecc-btn-danger:hover { background: #b91c1c; transform: translateY(-1px); }
        .ecc-btn:disabled  { opacity: .5; cursor: not-allowed; transform: none !important; }

        /* ── INTEREST MODE PILLS ── */
        .ecc-mode-indicator {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 18px;
            background: linear-gradient(135deg, #eff6ff, #dbeafe);
            border: 1px solid #bfdbfe;
            border-radius: 8px;
            margin-bottom: 16px;
        }
        .ecc-mode-indicator .mode-icon { font-size: 18px; }
        .ecc-mode-indicator .mode-text { font-size: 13px; font-weight: 600; color: #1e40af; }
        .ecc-mode-indicator .mode-desc { font-size: 11px; color: #3b82f6; margin-top: 2px; }

        /* ── SCHEDULE TABLE ENHANCEMENTS ── */
        .ecc-schedule-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 16px;
            background: #f1f5f9;
            border: 1px solid var(--ecc-border);
            border-radius: 8px 8px 0 0;
            margin-top: 16px;
        }
        .ecc-schedule-header h4 {
            margin: 0;
            font-size: 14px;
            font-weight: 700;
            color: #1e293b;
        }
        .ecc-schedule-summary {
            font-size: 12px;
            color: #475569;
        }

        /* ── DIALOG PANELS ── */
        .ecc-panel {
            background: var(--ecc-surface);
            border: 1px solid var(--ecc-border);
            border-radius: var(--ecc-radius);
            padding: 20px;
            margin-bottom: 16px;
        }
        .ecc-panel-title {
            font-size: 13px;
            font-weight: 700;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: .5px;
            margin: 0 0 12px 0;
        }
        .ecc-gradient-card {
            border-radius: var(--ecc-radius);
            padding: 20px 24px;
            color: #fff;
            margin-bottom: 14px;
        }
        .ecc-gradient-blue   { background: linear-gradient(135deg,#1e40af,#0369a1); }
        .ecc-gradient-green  { background: linear-gradient(135deg,#065f46,#059669); }
        .ecc-gradient-amber  { background: linear-gradient(135deg,#92400e,#d97706); }
        .ecc-gradient-purple { background: linear-gradient(135deg,#4c1d95,#7c3aed); }

        /* ── WHT SUMMARY ── */
        .ecc-wht-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #f1f5f9;
            font-size: 13px;
        }
        .ecc-wht-row:last-child { border-bottom: none; }
        .ecc-wht-label { color: #64748b; }
        .ecc-wht-amount { font-weight: 700; color: #1e293b; }
        .ecc-wht-badge { font-size: 10px; padding: 2px 8px; border-radius: 10px; background: #fee2e2; color: #991b1b; font-weight: 700; }

        /* ── SHIMMER ── */
        @keyframes shimmer { 0%,100%{opacity:.6} 50%{opacity:1} }
        .ecc-shimmer { animation: shimmer 1.5s infinite; background: #e2e8f0; border-radius: 6px; }

        @media(max-width:768px){
            .ecc-kpi-strip { grid-template-columns: 1fr 1fr; }
            .ecc-action-bar { flex-direction: column; }
        }
    `;
    $('<style id="ecc-inv-styles">').text(css).appendTo('head');
}

// ---------------------------------------------------------------------------
// MAIN FORM HANDLERS
// ---------------------------------------------------------------------------
frappe.ui.form.on('Ecclesia Investment', {

    setup(frm) {
        _setup_queries(frm);
    },

    onload(frm) {
        _render_hero(frm);
        _render_kpi_strip(frm);
        _render_action_bar(frm);
        if (frm.doc.start_date && frm.doc.tenure_in_days && !frm.doc.end_date) {
            _calc_end_date(frm);
        }
    },

    refresh(frm) {
        _render_hero(frm);
        _render_kpi_strip(frm);
        _render_action_bar(frm);
        _setup_indicators(frm);
        _style_schedule_grid(frm);
    },

    // ── Identity triggers ──
    investment_type(frm) {
        _toggle_sections(frm);
        _recalculate_all(frm);
    },

    // ── Date / Tenor triggers ──
    posting_date(frm) {
        if (!frm.doc.start_date) frm.set_value('start_date', frm.doc.posting_date);
    },
    start_date(frm) {
        _calc_end_date(frm);
        _recalculate_all(frm);
    },
    tenure_in_days(frm) {
        _calc_end_date(frm);
        _set_duration_category(frm);
        _recalculate_all(frm);
    },

    // ── Money market triggers — recalculate figures, flag schedule as stale ──
    investment_amount(frm)    { _recalculate_all(frm); _flag_schedule_stale(frm); },
    interest_rate(frm)        { _recalculate_all(frm); _flag_schedule_stale(frm); },
    interest_type(frm)        { _recalculate_all(frm); _flag_schedule_stale(frm); },
    interest_payment_mode(frm) {
        _toggle_sections(frm);
        _recalculate_all(frm);
        _render_mode_indicator(frm);
        _render_action_bar(frm);     // show/hide Build Schedule for this mode
        _flag_schedule_stale(frm);
    },
    frequency_of_income_recognition(frm) { _recalculate_all(frm); _flag_schedule_stale(frm); },
    management_fee(frm)       { _recalculate_all(frm); _flag_schedule_stale(frm); },
    total_gross_interest(frm) { _recalculate_all(frm); _flag_schedule_stale(frm); },

    // ── Date / Tenor — also flag stale ──
    start_date(frm) {
        _calc_end_date(frm);
        _recalculate_all(frm);
        _flag_schedule_stale(frm);
    },
    tenure_in_days(frm) {
        _calc_end_date(frm);
        _set_duration_category(frm);
        _recalculate_all(frm);
        _flag_schedule_stale(frm);
    },

    // ── WHT triggers — figures only, never schedule ──
    wht_applicable(frm) { _recalculate_wht(frm); _flag_schedule_stale(frm); },
    wht_rate(frm)       { _recalculate_wht(frm); _flag_schedule_stale(frm); },

    // ── Shares triggers ──
    number_of_units(frm)      { _calc_shares(frm); },
    unit_price(frm)           { _calc_shares(frm); },
    dividend_rate(frm)        { _calc_shares(frm); },
    market_price_per_unit(frm){ _calc_shares(frm); },

    // ── Currency ──
    currency(frm)      { _calc_base_amount(frm); },
    exchange_rate(frm) { _calc_base_amount(frm); },

    // ── Schedule flags — checking these boxes does NOT auto-build.
    //    The user must click Calculate (figures) or Build Schedule (figures + table).
    amortise_income(frm) {
        if (!frm.doc.amortise_income) {
            frm.clear_table('schedule_of_interest');
            frm.refresh_field('schedule_of_interest');
            _toast('Schedule cleared', 'info');
        } else {
            _toast('Amortise Income enabled — click Build Schedule to generate the table', 'info');
        }
        _render_action_bar(frm);  // refresh bar to show/hide Build Schedule button
    },
    amortise_upfront_interest(frm) {
        if (frm.doc.amortise_upfront_interest) {
            _toast('Upfront amortisation enabled — click Build Schedule to generate the table', 'info');
        }
        _render_action_bar(frm);
    },

    // ── Save hook — recalculates figures only; never rebuilds the schedule ──
    before_save(frm) {
        _recalculate_all(frm);
        _validate_form(frm);
    },

    bank_account(frm) {
        if (frm.doc.bank_account) {
            frappe.db.get_value('Bank Account', frm.doc.bank_account, 'account')
                .then(r => r.message && frm.set_value('bank_gl', r.message.account));
        }
    },
});

// ---------------------------------------------------------------------------
// CALCULATION ENGINE
// ---------------------------------------------------------------------------

function _recalculate_all(frm) {
    // Recalculates figures only — never touches the schedule table.
    // Schedule is built exclusively by _run_calculate() or _run_build_schedule().
    _calc_end_date(frm);
    _calc_interest(frm);
    _calc_management_fee(frm);
    _recalculate_wht(frm);
    _calc_shares(frm);
    _calc_base_amount(frm);
    _calc_ai_metrics(frm);
    _render_kpi_strip(frm);
}

// Called by the Calculate button AND as the first half of Build Schedule.
// Runs figures then shows the stale-schedule indicator if a schedule exists.
function _run_calculate(frm) {
    _recalculate_all(frm);
    _toast('Figures recalculated — click Build Schedule to update the schedule', 'info');
    _flag_schedule_stale(frm);
}

// Called by the Build Schedule button.
// Re-runs figures first so the schedule is always based on current values.
function _run_build_schedule(frm) {
    _recalculate_all(frm);   // always recalc figures first

    const mode = frm.doc.interest_payment_mode || '';
    const is_periodic  = ['Periodic', 'Periodic and At Maturity'].includes(mode);
    const is_upfront   = ['Upfront', 'Upfront and At Maturity'].includes(mode);

    let built = false;

    if (is_periodic && frm.doc.amortise_income) {
        _build_interest_schedule(frm);
        built = true;
    }
    if (is_upfront && frm.doc.amortise_upfront_interest) {
        _build_upfront_amortisation(frm);
        built = true;
    }

    if (!built) {
        // Nothing to schedule — guide the user
        const missing = [];
        if (!frm.doc.interest_payment_mode)              missing.push('Interest Payment Mode');
        if (!frm.doc.frequency_of_income_recognition && is_periodic) missing.push('Frequency of Income Recognition');
        if (!frm.doc.amortise_income && is_periodic)     missing.push('"Amortise Income" checkbox');
        if (!frm.doc.amortise_upfront_interest && is_upfront) missing.push('"Amortise Upfront Interest" checkbox');
        if (!frm.doc.start_date)                         missing.push('Start Date');
        if (!frm.doc.tenure_in_days)                     missing.push('Tenure in Days');
        if (!frm.doc.monthly_interest_income && is_periodic) missing.push('Interest Per Period (run Calculate first)');

        frappe.msgprint({
            title: __('Schedule Cannot Be Built'),
            message: missing.length
                ? __('Please set the following before building the schedule:<br><ul><li>{0}</li></ul>',
                     [missing.join('</li><li>')])
                : __('No schedulable income mode is active. Enable "Amortise Income" for Periodic modes, or "Amortise Upfront Interest" for Upfront modes.'),
            indicator: 'orange',
        });
    }
    _unflag_schedule_stale(frm);
}

function _calc_end_date(frm) {
    if (frm.doc.start_date && frm.doc.tenure_in_days > 0) {
        const end = frappe.datetime.add_days(frm.doc.start_date, parseInt(frm.doc.tenure_in_days));
        frm.set_value('end_date', end);
    }
}

function _calc_interest(frm) {
    const p = flt(frm.doc.investment_amount);
    const days = parseInt(frm.doc.tenure_in_days || 0);
    const r = flt(frm.doc.interest_rate) / 100;

    if (!p || !days || !r) return;

    const t = days / 365;
    let gross = 0;

    switch (frm.doc.interest_type) {
        case 'Simple Interest':     gross = p * r * t;                       break;
        case 'Compound Interest':   gross = p * (Math.pow(1 + r, t) - 1);   break;
        case 'Discount (T-Bills)':  gross = p * r * t / (1 + r * t);        break;
        case 'Flat Rate':           gross = p * r * t;                       break;
        default: gross = p * r * t;
    }

    // Allow manual override
    const effective_gross = frm.doc.total_gross_interest > 0
        ? flt(frm.doc.total_gross_interest)
        : gross;

    frm.set_value('returns', flt(effective_gross.toFixed(4)));

    const mode = frm.doc.interest_payment_mode || '';

    // ── Split by mode ──
    if (mode === 'Upfront') {
        frm.set_value('upfront_interest_amount', flt(effective_gross.toFixed(4)));
        frm.set_value('maturity_interest_amount', 0);
    } else if (mode === 'At Maturity') {
        frm.set_value('upfront_interest_amount', 0);
        frm.set_value('maturity_interest_amount', flt(effective_gross.toFixed(4)));
    } else if (mode === 'Upfront and At Maturity') {
        // Equal split (can be overridden in template)
        frm.set_value('upfront_interest_amount', flt((effective_gross / 2).toFixed(4)));
        frm.set_value('maturity_interest_amount', flt((effective_gross / 2).toFixed(4)));
    } else if (mode === 'Periodic and At Maturity') {
        const periodic_portion = flt(effective_gross * 0.7);
        const maturity_portion = flt(effective_gross * 0.3);
        frm.set_value('maturity_interest_amount', maturity_portion);
        _calc_periodic_income(frm, periodic_portion);
    } else if (mode === 'Periodic') {
        _calc_periodic_income(frm, effective_gross);
        frm.set_value('maturity_interest_amount', 0);
        frm.set_value('upfront_interest_amount', 0);
    }

    frm.set_value('amount_realisable_on_liquidation', flt(p + effective_gross));
}

function _calc_periodic_income(frm, total_returns) {
    if (!frm.doc.tenure_in_days || !frm.doc.frequency_of_income_recognition) return;

    const freq_days = {
        'Monthly': 30, 'Quarterly': 90, 'Half-yearly': 180, 'Yearly': 365
    };
    const days_per_period = freq_days[frm.doc.frequency_of_income_recognition] || 30;
    const periods = Math.floor(frm.doc.tenure_in_days / days_per_period);

    if (periods > 0) {
        frm.set_value('monthly_interest_income', flt((total_returns / periods).toFixed(4)));
    }
}

function _calc_management_fee(frm) {
    const returns = flt(frm.doc.returns);
    const fee_pct = flt(frm.doc.management_fee);
    frm.set_value('management_fee_amount', fee_pct > 0 ? flt((returns * fee_pct / 100).toFixed(4)) : 0);
}

function _recalculate_wht(frm) {
    // WHT in Nigeria is statutory — one rate applies to all income types.
    // 5% for individuals (PITA), 10% for companies (CITA S.78).
    const applicable = frm.doc.wht_applicable && frm.doc.wht_rate;
    const rate = applicable
        ? (frm.doc.wht_rate.includes('5%') ? 0.05 : 0.10)
        : 0;

    const _wht = (base) => applicable && base ? flt((flt(base) * rate).toFixed(4)) : 0;

    // Per-component amounts (displayed conditionally by interest_payment_mode)
    const wht_periodic  = _wht(frm.doc.monthly_interest_income);
    const wht_upfront   = _wht(frm.doc.upfront_interest_amount);
    const wht_maturity  = _wht(frm.doc.maturity_interest_amount);
    const wht_dividend  = _wht(frm.doc.expected_dividend_income);

    frm.set_value('wht_amount_periodic',  wht_periodic);
    frm.set_value('wht_amount_upfront',   wht_upfront);
    frm.set_value('wht_amount_maturity',  wht_maturity);
    frm.set_value('wht_amount_dividend',  wht_dividend);

    // Aggregate WHT on total returns — for WHT certificate / remittance summary
    const total_wht = applicable ? flt((flt(frm.doc.returns) * rate).toFixed(4)) : 0;
    frm.set_value('total_wht_amount',     total_wht);
    frm.set_value('net_income_after_wht', flt(frm.doc.returns) - total_wht);
}

function _calc_shares(frm) {
    const units = flt(frm.doc.number_of_units);
    const cost   = flt(frm.doc.unit_price);
    const market = flt(frm.doc.market_price_per_unit);
    const div_r  = flt(frm.doc.dividend_rate) / 100;

    if (units && cost) {
        frm.set_value('total_share_cost', flt((units * cost).toFixed(4)));
    }
    if (units && market) {
        const mkt_val = units * market;
        frm.set_value('market_value', flt(mkt_val.toFixed(4)));
        frm.set_value('unrealised_gain_loss', flt((mkt_val - units * cost).toFixed(4)));
    }
    if (units && cost && div_r) {
        frm.set_value('expected_dividend_income', flt((units * cost * div_r).toFixed(4)));
        _recalculate_wht(frm);
    }
}

function _calc_base_amount(frm) {
    if (frm.doc.investment_amount && frm.doc.exchange_rate) {
        frm.set_value('investment_amount_base',
            flt(frm.doc.investment_amount) * flt(frm.doc.exchange_rate || 1));
    }
}

function _calc_ai_metrics(frm) {
    const p = flt(frm.doc.investment_amount);
    const r = flt(frm.doc.returns);
    if (!p || !r) return;

    const roi = (r / p) * 100;
    let score = 50;

    if (frm.doc.interest_rate > 15) score += 20;
    else if (frm.doc.interest_rate > 10) score += 10;
    else if (frm.doc.interest_rate < 5) score -= 10;

    if (frm.doc.tenure_in_days > 1825) score += 15;
    else if (frm.doc.tenure_in_days < 90)  score += 5;

    if (frm.doc.market_asset_class === 'Unquoted') score += 15;
    if (frm.doc.investment_type === 'Shares')       score += 10;
    if (frm.doc.liquidity_ratio < 50) score += 10;
    if (frm.doc.rate_of_inflation && frm.doc.interest_rate - frm.doc.rate_of_inflation < 2) score += 10;

    score = Math.min(Math.max(score, 0), 100);
    frm.set_value('ai_risk_score', score);

    const ann = frm.doc.tenure_in_days ? roi * (365 / frm.doc.tenure_in_days) : roi;
    let rec;
    if (ann > 15 && score < 60)  rec = '⭐ EXCELLENT – High returns, acceptable risk';
    else if (ann > 10 && score < 70) rec = '✅ GOOD – Solid performance, moderate risk';
    else if (score > 80)             rec = '🔴 HIGH RISK – Monitor closely';
    else if (ann < 5)                rec = '⚠️ REVIEW – Low returns';
    else                             rec = '📊 FAIR – Within market expectations';
    frm.set_value('ai_recommendation', rec);
}

// ---------------------------------------------------------------------------
// SCHEDULE BUILDERS
// ---------------------------------------------------------------------------

function _build_interest_schedule(frm) {
    if (!frm.doc.start_date || !frm.doc.end_date || !frm.doc.returns) return;

    const mode = frm.doc.interest_payment_mode || '';
    if (!['Periodic', 'Periodic and At Maturity'].includes(mode)) return;

    const freq_months   = { 'Monthly': 1, 'Quarterly': 3, 'Half-yearly': 6, 'Yearly': 12 };
    const freq_days     = { 'Monthly': 30, 'Quarterly': 90, 'Half-yearly': 180, 'Yearly': 365 };
    const months_step   = freq_months[frm.doc.frequency_of_income_recognition] || 1;
    const days_per      = freq_days[frm.doc.frequency_of_income_recognition] || 30;
    const total_periods = Math.floor(parseInt(frm.doc.tenure_in_days || 0) / days_per);
    if (total_periods <= 0) return;

    // Always compute inline from raw source fields — never read derived/read-only fields
    // which may lag behind due to async set_value calls.
    const gross_returns    = flt(frm.doc.returns);
    const fee_pct          = flt(frm.doc.management_fee);
    const total_fee        = fee_pct > 0 ? gross_returns * fee_pct / 100 : 0;
    const period_gross     = parseFloat((gross_returns / total_periods).toFixed(4));
    const period_fee       = fee_pct > 0 ? parseFloat((total_fee / total_periods).toFixed(4)) : 0;
    const wht_rate_num     = (frm.doc.wht_applicable && frm.doc.wht_rate)
                             ? (frm.doc.wht_rate.includes('5%') ? 0.05 : 0.10) : 0;
    const wht_type_label   = wht_rate_num > 0 ? frm.doc.wht_rate + ' WHT' : '';

    // Clear and rebuild — write directly to frm.doc rows then refresh once at the end.
    // Direct row mutation is the only reliable way to populate read_only child fields in Frappe.
    frm.doc.schedule_of_interest = [];

    for (let i = 1; i <= total_periods; i++) {
        const period_date = frappe.datetime.add_months(frm.doc.start_date, i * months_step);
        const period_wht  = parseFloat((period_gross * wht_rate_num).toFixed(4));
        const period_net  = parseFloat((period_gross - period_wht - period_fee).toFixed(4));

        const row = frappe.model.add_child(frm.doc, 'Ecclesia Interest Schedule', 'schedule_of_interest');
        row.period                  = i;
        row.date                    = period_date;
        row.period_label            = _period_label(frm.doc.start_date, i, months_step);
        row.interest_amount         = period_gross;
        row.wht_type                = wht_type_label;
        row.wht_rate                = parseFloat((wht_rate_num * 100).toFixed(2));
        row.wht_amount              = period_wht;
        row.management_fee_amount   = period_fee;
        row.net_amount              = period_net;
        row.is_deferred_amortisation = 0;
        row.status                  = 'Pending';
    }

    frm.refresh_field('schedule_of_interest');
    _toast(`${total_periods} period${total_periods > 1 ? 's' : ''} built`, 'success');
}

function _build_upfront_amortisation(frm) {
    if (!frm.doc.upfront_interest_amount || !frm.doc.tenure_in_days || !frm.doc.start_date) return;

    const total      = flt(frm.doc.upfront_interest_amount);
    const months     = Math.floor(parseInt(frm.doc.tenure_in_days) / 30);
    if (months <= 0) return;

    const per_period = parseFloat((total / months).toFixed(4));

    frm.doc.schedule_of_interest = [];

    for (let i = 1; i <= months; i++) {
        const period_date = frappe.datetime.add_months(frm.doc.start_date, i);

        const row = frappe.model.add_child(frm.doc, 'Ecclesia Interest Schedule', 'schedule_of_interest');
        row.period                   = i;
        row.date                     = period_date;
        row.period_label             = _period_label(frm.doc.start_date, i, 1) + ' (Amortisation)';
        row.interest_amount          = per_period;
        row.wht_type                 = '';
        row.wht_rate                 = 0;
        row.wht_amount               = 0;
        row.management_fee_amount    = 0;
        row.net_amount               = per_period;
        row.is_deferred_amortisation = 1;
        row.status                   = 'Pending';
    }

    frm.refresh_field('schedule_of_interest');
    _toast(`Upfront interest amortised over ${months} months`, 'success');
}

function _period_label(start_date, period_num, months_step) {
    const d = frappe.datetime.add_months(start_date, period_num * months_step);
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    const dt = new Date(d);
    return `${months[dt.getMonth()]} ${dt.getFullYear()}`;
}

// ---------------------------------------------------------------------------
// SCHEDULE STATE HELPERS
// ---------------------------------------------------------------------------

function _flag_schedule_stale(frm) {
    // Visual cue: if a schedule already exists and figures changed, warn user
    if ((frm.doc.schedule_of_interest || []).length > 0) {
        if (!$('#ecc-schedule-stale-banner').length) {
            const banner = $(`
                <div id="ecc-schedule-stale-banner" style="
                    display:flex; align-items:center; gap:10px;
                    background:#fffbeb; border:1px solid #f59e0b;
                    border-left:4px solid #f59e0b; border-radius:8px;
                    padding:10px 16px; margin-bottom:12px; font-size:13px; color:#92400e;">
                    <i class="fa fa-exclamation-triangle" style="font-size:16px;color:#f59e0b;"></i>
                    <span>Figures have changed. Click <b>Build Schedule</b> to regenerate the schedule with updated values.</span>
                    <button onclick="$('#ecc-schedule-stale-banner').remove()"
                        style="margin-left:auto;background:none;border:none;cursor:pointer;color:#92400e;font-size:16px;">✕</button>
                </div>
            `);
            // Insert just above the schedule tab content
            $(frm.fields_dict.schedule_of_interest.wrapper).before(banner);
        }
    }
}

function _unflag_schedule_stale(frm) {
    $('#ecc-schedule-stale-banner').remove();
}

// ---------------------------------------------------------------------------
// UI COMPONENTS
// ---------------------------------------------------------------------------

function _render_hero(frm) {
    $('.ecc-hero').remove();

    const type_label = frm.doc.investment_type || 'Investment';
    const mode_label = frm.doc.interest_payment_mode || '';
    const status_class = {
        'Active': 'ecc-badge-green',
        'Matured': 'ecc-badge-amber',
        'Liquidated': 'ecc-badge-red',
    }[frm.doc.status] || 'ecc-badge-white';

    const hero = $(`
        <div class="ecc-hero">
            <div class="ecc-hero-title">
                ${frm.doc.investment_name || 'New Investment'} — ${type_label}
            </div>
            <div class="ecc-hero-subtitle">
                ${frm.doc.counterparty_name || 'Counterparty not set'} 
                ${frm.doc.start_date ? '· ' + frappe.datetime.str_to_user(frm.doc.start_date) : ''}
                ${frm.doc.end_date   ? ' → ' + frappe.datetime.str_to_user(frm.doc.end_date) : ''}
            </div>
            <div class="ecc-hero-badges">
                <span class="ecc-badge ecc-badge-white">${type_label}</span>
                ${mode_label ? `<span class="ecc-badge ecc-badge-white">${mode_label}</span>` : ''}
                <span class="ecc-badge ${status_class}">${frm.doc.status || 'Pending'}</span>
                ${frm.doc.tenure_in_days ? `<span class="ecc-badge ecc-badge-white">${frm.doc.tenure_in_days} days</span>` : ''}
            </div>
        </div>
    `);

    $(frm.wrapper).find('.form-section:first').before(hero);
}

function _render_kpi_strip(frm) {
    $('.ecc-kpi-strip').remove();

    const is_shares = frm.doc.investment_type === 'Shares';
    const roi = frm.doc.investment_amount && frm.doc.returns
        ? (flt(frm.doc.returns) / flt(frm.doc.investment_amount) * 100).toFixed(2) : '—';

    const days_left = frm.doc.end_date
        ? frappe.datetime.get_day_diff(frm.doc.end_date, frappe.datetime.nowdate()) : '—';

    const total_wht = (flt(frm.doc.wht_amount_periodic) || 0) +
                      (flt(frm.doc.wht_amount_upfront) || 0) +
                      (flt(frm.doc.wht_amount_maturity) || 0) +
                      (flt(frm.doc.wht_amount_dividend) || 0);

    const kpis = is_shares ? [
        { label: 'Total Cost',      value: _fmt_cur(frm.doc.total_share_cost),   sub: `${frm.doc.number_of_units || 0} units`,      accent: '#1e40af' },
        { label: 'Market Value',    value: _fmt_cur(frm.doc.market_value),        sub: `@ ${_fmt_cur(frm.doc.market_price_per_unit)} / unit`, accent: '#0ea5e9' },
        { label: 'Unrealised G/L',  value: _fmt_cur(frm.doc.unrealised_gain_loss), sub: 'Mark to market',                             accent: flt(frm.doc.unrealised_gain_loss) >= 0 ? '#059669' : '#dc2626' },
        { label: 'Net Dividend',    value: _fmt_cur(frm.doc.net_dividend_income), sub: `WHT: ${_fmt_cur(frm.doc.wht_amount_dividend)}`, accent: '#7c3aed' },
    ] : [
        { label: 'Principal',       value: _fmt_cur(frm.doc.investment_amount),  sub: frm.doc.currency || 'NGN',                    accent: '#1e40af' },
        { label: 'Gross Returns',   value: _fmt_cur(frm.doc.returns),            sub: `ROI ${roi}%`,                                accent: '#059669' },
        { label: 'Total WHT',       value: _fmt_cur(total_wht),                  sub: 'All WHT deductions',                         accent: '#dc2626' },
        { label: 'Days to Maturity',value: days_left,                             sub: frm.doc.end_date ? frappe.datetime.str_to_user(frm.doc.end_date) : '', accent: '#d97706' },
    ];

    const strip = $('<div class="ecc-kpi-strip">');
    kpis.forEach(k => {
        strip.append(`
            <div class="ecc-kpi">
                <div class="ecc-kpi-accent" style="background:${k.accent}"></div>
                <div class="ecc-kpi-label">${k.label}</div>
                <div class="ecc-kpi-value">${k.value}</div>
                <div class="ecc-kpi-sub">${k.sub}</div>
            </div>
        `);
    });

    $('.ecc-hero').after(strip);
}

function _render_action_bar(frm) {
    $('.ecc-action-bar').remove();
    const has_schedule = (frm.doc.schedule_of_interest || []).length > 0;
    const is_draft     = frm.doc.docstatus === 0;
    const is_submitted = frm.doc.docstatus === 1;
    const is_shares    = frm.doc.investment_type === 'Shares';
    const is_mm        = !is_shares;

    const bar = $('<div class="ecc-action-bar">');

    // ── Money market buttons ──────────────────────────────────────────────
    if (is_draft && is_mm) {
        bar.append(`<button class="ecc-btn ecc-btn-primary" id="ecc-btn-calc">
            <i class="fa fa-calculator"></i> Calculate
        </button>`);
        bar.append(`<button class="ecc-btn ecc-btn-success" id="ecc-btn-schedule">
            <i class="fa fa-calendar-alt"></i> ${has_schedule ? 'Rebuild Schedule' : 'Build Schedule'}
        </button>`);
    }

    // ── Shares corporate action buttons (submitted only) ──────────────────
    if (is_shares && is_submitted) {
        bar.append(`<button class="ecc-btn ecc-btn-primary" id="ecc-btn-dividend">
            <i class="fa fa-coins"></i> Record Dividend
        </button>`);
        bar.append(`<button class="ecc-btn ecc-btn-success" id="ecc-btn-bonus">
            <i class="fa fa-gift"></i> Bonus Issue
        </button>`);
        bar.append(`<button class="ecc-btn ecc-btn-outline" id="ecc-btn-rights">
            <i class="fa fa-plus-circle"></i> Rights Issue
        </button>`);
        bar.append(`<button class="ecc-btn ecc-btn-danger" id="ecc-btn-dispose">
            <i class="fa fa-exchange-alt"></i> Dispose Shares
        </button>`);
    }

    // ── Universal buttons ─────────────────────────────────────────────────
    bar.append(`<button class="ecc-btn ecc-btn-outline" id="ecc-btn-wht">
        <i class="fa fa-receipt"></i> WHT Summary
    </button>`);
    bar.append(`<button class="ecc-btn ecc-btn-outline" id="ecc-btn-ai">
        <i class="fa fa-robot"></i> AI Analysis
    </button>`);
    if (has_schedule && is_mm) {
        bar.append(`<button class="ecc-btn ecc-btn-outline" id="ecc-btn-export">
            <i class="fa fa-file-csv"></i> Export CSV
        </button>`);
    }

    $('.ecc-kpi-strip').after(bar);

    // ── Handlers ──────────────────────────────────────────────────────────
    $('#ecc-btn-calc').on('click', () => _run_calculate(frm));
    $('#ecc-btn-schedule').on('click', () => _run_build_schedule(frm));
    $('#ecc-btn-wht').on('click',     () => _show_wht_summary(frm));
    $('#ecc-btn-ai').on('click',      () => _show_ai_analysis(frm));
    $('#ecc-btn-export').on('click',  () => _export_schedule_csv(frm));
    $('#ecc-btn-dividend').on('click',() => _dialog_dividend(frm));
    $('#ecc-btn-bonus').on('click',   () => _dialog_bonus_issue(frm));
    $('#ecc-btn-rights').on('click',  () => _dialog_rights_issue(frm));
    $('#ecc-btn-dispose').on('click', () => _dialog_disposal(frm));
}

// ---------------------------------------------------------------------------
// SHARES CORPORATE ACTION DIALOGS
// ---------------------------------------------------------------------------

function _dialog_dividend(frm) {
    const d = new frappe.ui.Dialog({
        title: '💰 Record Dividend Receipt',
        fields: [
            {
                fieldtype: 'Date', fieldname: 'dividend_date', label: 'Dividend Date',
                reqd: 1, default: frappe.datetime.get_today(),
            },
            { fieldtype: 'Column Break' },
            {
                fieldtype: 'Select', fieldname: 'dividend_type', label: 'Dividend Type',
                options: 'Interim\nFinal\nSpecial', default: 'Final',
            },
            { fieldtype: 'Section Break', label: 'Amounts' },
            {
                fieldtype: 'Currency', fieldname: 'gross_dividend', label: 'Gross Dividend Amount', reqd: 1,
            },
            { fieldtype: 'Column Break' },
            {
                fieldtype: 'HTML', fieldname: 'wht_info',
                options: `<div style="padding:8px 12px;background:#f0fdf4;border-radius:6px;font-size:12px;color:#065f46;border-left:3px solid #10b981;">
                    WHT Rate: <b>${frm.doc.wht_applicable && frm.doc.wht_rate ? frm.doc.wht_rate : 'Not applicable'}</b>
                    — inherited from the investment's WHT configuration.
                </div>`,
            },
            { fieldtype: 'Section Break' },
            {
                fieldtype: 'Small Text', fieldname: 'notes', label: 'Notes',
            },
        ],
        primary_action_label: 'Book Dividend',
        primary_action(values) {
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.ecclesia_investment.ecclesia_investment.book_dividend',
                args: {
                    investment_name: frm.doc.name,
                    dividend_date: values.dividend_date,
                    gross_dividend: values.gross_dividend,
                    wht_rate: values.wht_rate || null,
                    dividend_type: values.dividend_type,
                },
                callback(r) {
                    if (r.message && r.message.success) {
                        d.hide();
                        frm.reload_doc();
                    }
                },
            });
        },
    });
    d.show();
}

function _dialog_bonus_issue(frm) {
    const d = new frappe.ui.Dialog({
        title: '🎁 Record Bonus Share Issue',
        fields: [
            {
                fieldtype: 'Date', fieldname: 'bonus_date', label: 'Bonus Date',
                reqd: 1, default: frappe.datetime.get_today(),
            },
            { fieldtype: 'Column Break' },
            {
                fieldtype: 'Float', fieldname: 'bonus_units', label: 'Bonus Units Received',
                reqd: 1, precision: 4,
                description: `Current holding: ${(frm.doc.number_of_units || 0).toFixed(4)} units`,
            },
            { fieldtype: 'Section Break' },
            {
                fieldtype: 'HTML', fieldname: 'info_html',
                options: `<div style="padding:10px 14px;background:#f0fdf4;border-radius:8px;border-left:4px solid #10b981;font-size:12px;color:#065f46;">
                    ℹ️ <b>Accounting note:</b> Bonus shares are recorded at zero cost under IFRS 9 / cost model.
                    Your cost basis per unit decreases; total investment cost remains unchanged.
                    The journal entry is a memo entry for audit trail purposes.
                </div>`,
            },
            { fieldtype: 'Section Break' },
            {
                fieldtype: 'Small Text', fieldname: 'notes', label: 'Notes',
            },
        ],
        primary_action_label: 'Record Bonus Issue',
        primary_action(values) {
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.ecclesia_investment.ecclesia_investment.book_bonus_shares',
                args: {
                    investment_name: frm.doc.name,
                    bonus_date: values.bonus_date,
                    bonus_units: values.bonus_units,
                    notes: values.notes,
                },
                callback(r) {
                    if (r.message && r.message.success) {
                        d.hide();
                        const new_units = r.message.new_total_units;
                        const old_cost  = flt(frm.doc.total_share_cost);
                        const new_avg   = new_units > 0 ? (old_cost / new_units).toFixed(4) : 0;
                        frappe.msgprint(
                            `✅ Bonus recorded. New holding: <b>${new_units.toFixed(4)}</b> units. New avg cost: <b>₦${new_avg}</b>/unit.`,
                            'Bonus Issue Complete'
                        );
                        frm.reload_doc();
                    }
                },
            });
        },
    });
    d.show();
}

function _dialog_rights_issue(frm) {
    const d = new frappe.ui.Dialog({
        title: '➕ Record Rights Issue Subscription',
        fields: [
            {
                fieldtype: 'Date', fieldname: 'rights_date', label: 'Subscription Date',
                reqd: 1, default: frappe.datetime.get_today(),
            },
            { fieldtype: 'Column Break' },
            {
                fieldtype: 'Float', fieldname: 'units_subscribed', label: 'Units Subscribed',
                reqd: 1, precision: 4,
                description: `Current holding: ${(frm.doc.number_of_units || 0).toFixed(4)} units`,
            },
            { fieldtype: 'Section Break', label: 'Subscription Terms' },
            {
                fieldtype: 'Currency', fieldname: 'subscription_price_per_unit',
                label: 'Subscription Price Per Unit', reqd: 1,
                description: 'This is typically below current market price',
            },
            { fieldtype: 'Column Break' },
            {
                fieldtype: 'HTML', fieldname: 'cost_preview',
                options: `<div id="rights-cost-preview" style="padding:10px 14px;background:#eff6ff;border-radius:8px;border-left:4px solid #3b82f6;font-size:12px;color:#1e40af;">
                    Fill in units and price to see total cost.
                </div>`,
            },
            { fieldtype: 'Section Break' },
            {
                fieldtype: 'HTML', fieldname: 'accounting_note',
                options: `<div style="padding:10px 14px;background:#fffbeb;border-radius:8px;border-left:4px solid #f59e0b;font-size:12px;color:#92400e;">
                    ⚠️ <b>Cost basis impact:</b> Subscribing to a rights issue increases your total cost.
                    A new weighted average cost per unit will be calculated automatically.
                </div>`,
            },
            { fieldtype: 'Section Break' },
            { fieldtype: 'Small Text', fieldname: 'notes', label: 'Notes' },
        ],
        primary_action_label: 'Book Rights Subscription',
        primary_action(values) {
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.ecclesia_investment.ecclesia_investment.book_rights_issue',
                args: {
                    investment_name: frm.doc.name,
                    rights_date: values.rights_date,
                    units_subscribed: values.units_subscribed,
                    subscription_price_per_unit: values.subscription_price_per_unit,
                    notes: values.notes,
                },
                callback(r) {
                    if (r.message && r.message.success) {
                        d.hide();
                        frm.reload_doc();
                    }
                },
            });
        },
    });

    // Live cost preview
    ['units_subscribed', 'subscription_price_per_unit'].forEach(f => {
        d.fields_dict[f] && d.fields_dict[f].$input.on('change', () => {
            const u = flt(d.get_value('units_subscribed'));
            const p = flt(d.get_value('subscription_price_per_unit'));
            if (u && p) {
                const total = (u * p).toLocaleString('en-NG', { minimumFractionDigits: 2 });
                $('#rights-cost-preview').html(
                    `💳 Total cash outflow: <b>₦${total}</b><br>
                     New holding: <b>${(flt(frm.doc.number_of_units) + u).toFixed(4)}</b> units`
                );
            }
        });
    });

    d.show();
}

function _dialog_disposal(frm) {
    const max_units = flt(frm.doc.number_of_units) || 0;
    const d = new frappe.ui.Dialog({
        title: '📤 Dispose Shares',
        fields: [
            {
                fieldtype: 'Date', fieldname: 'disposal_date', label: 'Disposal Date',
                reqd: 1, default: frappe.datetime.get_today(),
            },
            { fieldtype: 'Column Break' },
            {
                fieldtype: 'Select', fieldname: 'disposal_type', label: 'Disposal Type',
                options: 'Partial Disposal\nFull Disposal', default: 'Partial Disposal',
            },
            { fieldtype: 'Section Break', label: 'Disposal Details' },
            {
                fieldtype: 'Float', fieldname: 'units_disposed', label: 'Units to Dispose',
                reqd: 1, precision: 4,
                description: `Maximum: ${max_units.toFixed(4)} units`,
            },
            { fieldtype: 'Column Break' },
            {
                fieldtype: 'Currency', fieldname: 'disposal_price_per_unit',
                label: 'Sale Price Per Unit', reqd: 1,
                description: `Cost basis: ₦${flt(frm.doc.unit_price).toLocaleString('en-NG', {minimumFractionDigits: 4})}/unit`,
            },
            { fieldtype: 'Section Break' },
            {
                fieldtype: 'HTML', fieldname: 'gl_preview',
                options: `<div id="disposal-preview" style="padding:10px 14px;background:#f8fafc;border-radius:8px;border-left:4px solid #64748b;font-size:12px;color:#475569;">
                    Fill in units and price to preview gain/loss.
                </div>`,
            },
            { fieldtype: 'Section Break' },
            { fieldtype: 'Small Text', fieldname: 'notes', label: 'Notes' },
        ],
        primary_action_label: 'Book Disposal',
        primary_action(values) {
            if (values.units_disposed > max_units) {
                frappe.throw(`Cannot dispose more than ${max_units.toFixed(4)} units.`);
                return;
            }
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.ecclesia_investment.ecclesia_investment.book_disposal',
                args: {
                    investment_name: frm.doc.name,
                    disposal_date: values.disposal_date,
                    units_disposed: values.units_disposed,
                    disposal_price_per_unit: values.disposal_price_per_unit,
                    notes: values.notes,
                },
                callback(r) {
                    if (r.message && r.message.success) {
                        d.hide();
                        frm.reload_doc();
                    }
                },
            });
        },
    });

    // Live gain/loss preview
    ['units_disposed', 'disposal_price_per_unit'].forEach(f => {
        d.fields_dict[f] && d.fields_dict[f].$input.on('change', () => {
            const u     = flt(d.get_value('units_disposed'));
            const price = flt(d.get_value('disposal_price_per_unit'));
            const cost  = flt(frm.doc.unit_price);
            if (u && price) {
                const proceeds  = u * price;
                const cost_basis = u * cost;
                const gl         = proceeds - cost_basis;
                const is_gain    = gl >= 0;
                const colour     = is_gain ? '#059669' : '#dc2626';
                const label      = is_gain ? 'Gain' : 'Loss';
                $('#disposal-preview').html(`
                    📤 Proceeds: <b>₦${proceeds.toLocaleString('en-NG', {minimumFractionDigits:2})}</b><br>
                    📦 Cost basis: <b>₦${cost_basis.toLocaleString('en-NG', {minimumFractionDigits:2})}</b><br>
                    <span style="color:${colour};font-weight:700;">
                        ${is_gain ? '📈' : '📉'} ${label}: ₦${Math.abs(gl).toLocaleString('en-NG', {minimumFractionDigits:2})}
                    </span>
                `);
            }
        });
    });

    // Auto-fill units on Full Disposal
    d.fields_dict.disposal_type.$input.on('change', () => {
        if (d.get_value('disposal_type') === 'Full Disposal') {
            d.set_value('units_disposed', max_units);
        }
    });

    d.show();
}

function _render_mode_indicator(frm) {
    $('.ecc-mode-indicator').remove();
    const mode = frm.doc.interest_payment_mode;
    if (!mode) return;

    const icons = {
        'Upfront': '💰',
        'At Maturity': '🏁',
        'Periodic': '📅',
        'Upfront and At Maturity': '💰🏁',
        'Periodic and At Maturity': '📅🏁',
    };
    const descs = {
        'Upfront': 'Interest paid to investor at the start of the tenor',
        'At Maturity': 'Interest paid at the end of the tenor',
        'Periodic': 'Interest recognised at each period (monthly/quarterly)',
        'Upfront and At Maturity': 'Portion paid upfront; balance paid at maturity',
        'Periodic and At Maturity': 'Periodic recognition plus a balloon at maturity',
    };

    const ind = $(`
        <div class="ecc-mode-indicator">
            <span class="mode-icon">${icons[mode] || '📊'}</span>
            <div>
                <div class="mode-text">${mode}</div>
                <div class="mode-desc">${descs[mode] || ''}</div>
            </div>
        </div>
    `);

    $(frm.fields_dict.interest_payment_mode.wrapper).after(ind);
}

// ---------------------------------------------------------------------------
// DIALOGS
// ---------------------------------------------------------------------------

function _show_wht_summary(frm) {
    const total_wht = (flt(frm.doc.wht_amount_periodic) || 0) +
                      (flt(frm.doc.wht_amount_upfront) || 0) +
                      (flt(frm.doc.wht_amount_maturity) || 0) +
                      (flt(frm.doc.wht_amount_dividend) || 0);

    // One statutory rate applies across all income types
    const wht_rate_label = frm.doc.wht_rate || (frm.doc.wht_applicable ? 'Set on form' : 'Not applicable');
    const mode = frm.doc.interest_payment_mode || '';
    const is_shares = frm.doc.investment_type === 'Shares';

    const rows = [
        {
            label: 'Periodic Interest',
            gross: _fmt_cur(frm.doc.monthly_interest_income),
            wht: _fmt_cur(frm.doc.wht_amount_periodic),
            net: _fmt_cur(flt(frm.doc.monthly_interest_income) - flt(frm.doc.wht_amount_periodic)),
            show: ['Periodic','Periodic and At Maturity'].includes(mode),
        },
        {
            label: 'Upfront Interest',
            gross: _fmt_cur(frm.doc.upfront_interest_amount),
            wht: _fmt_cur(frm.doc.wht_amount_upfront),
            net: _fmt_cur(flt(frm.doc.upfront_interest_amount) - flt(frm.doc.wht_amount_upfront)),
            show: ['Upfront','Upfront and At Maturity'].includes(mode),
        },
        {
            label: 'Maturity Interest',
            gross: _fmt_cur(frm.doc.maturity_interest_amount),
            wht: _fmt_cur(frm.doc.wht_amount_maturity),
            net: _fmt_cur(flt(frm.doc.maturity_interest_amount) - flt(frm.doc.wht_amount_maturity)),
            show: ['At Maturity','Upfront and At Maturity','Periodic and At Maturity'].includes(mode),
        },
        {
            label: 'Dividends',
            gross: _fmt_cur(frm.doc.expected_dividend_income),
            wht: _fmt_cur(frm.doc.wht_amount_dividend),
            net: _fmt_cur(flt(frm.doc.expected_dividend_income) - flt(frm.doc.wht_amount_dividend)),
            show: is_shares,
        },
    ].filter(r => r.show);

    const rows_html = rows.map(r => `
        <tr style="border-bottom:1px solid #e2e8f0;">
            <td style="padding:12px 14px;font-weight:600;color:#1e293b;">${r.label}</td>
            <td style="padding:12px 14px;color:#475569;">${r.gross}</td>
            <td style="padding:12px 14px;">
                <span style="background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;">
                    ${frm.doc.wht_applicable ? wht_rate_label : 'N/A'}
                </span>
            </td>
            <td style="padding:12px 14px;color:#dc2626;font-weight:600;">${r.wht}</td>
            <td style="padding:12px 14px;color:#059669;font-weight:700;">${r.net}</td>
        </tr>
    `).join('');

    const html = `
        <div style="padding:24px;">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px;">
                <div class="ecc-gradient-card ecc-gradient-blue">
                    <div style="font-size:11px;opacity:.8;margin-bottom:6px;">GROSS RETURNS</div>
                    <div style="font-size:26px;font-weight:800;">${_fmt_cur(frm.doc.returns)}</div>
                </div>
                <div class="ecc-gradient-card ecc-gradient-amber">
                    <div style="font-size:11px;opacity:.8;margin-bottom:6px;">TOTAL WHT DEDUCTIONS</div>
                    <div style="font-size:26px;font-weight:800;">${_fmt_cur(total_wht)}</div>
                </div>
            </div>
            <table style="width:100%;border-collapse:collapse;font-size:13px;">
                <thead>
                    <tr style="background:#f1f5f9;">
                        <th style="padding:10px 14px;text-align:left;font-size:11px;color:#64748b;text-transform:uppercase;">Component</th>
                        <th style="padding:10px 14px;text-align:left;font-size:11px;color:#64748b;text-transform:uppercase;">Gross</th>
                        <th style="padding:10px 14px;text-align:left;font-size:11px;color:#64748b;text-transform:uppercase;">WHT Rate</th>
                        <th style="padding:10px 14px;text-align:left;font-size:11px;color:#64748b;text-transform:uppercase;">WHT Amount</th>
                        <th style="padding:10px 14px;text-align:left;font-size:11px;color:#64748b;text-transform:uppercase;">Net</th>
                    </tr>
                </thead>
                <tbody>${rows_html}</tbody>
            </table>
            <div style="margin-top:16px;padding:14px;background:#f0fdf4;border-radius:8px;border-left:4px solid #10b981;font-size:12px;color:#065f46;">
                ℹ️ WHT is remitted to FIRS. Ensure the WHT payable account is configured in the Accounting section.
            </div>
        </div>
    `;

    const d = new frappe.ui.Dialog({
        title: 'Withholding Tax Summary',
        size: 'extra-large',
        fields: [{ fieldtype: 'HTML', fieldname: 'content' }],
    });
    d.fields_dict.content.$wrapper.html(html);
    d.show();
}

async function _show_ai_analysis(frm) {
    if (ECC_INV.loading) return;

    const d = new frappe.ui.Dialog({
        title: 'AI Investment Analysis',
        size: 'extra-large',
        fields: [{ fieldtype: 'HTML', fieldname: 'content' }],
    });
    d.show();
    d.fields_dict.content.$wrapper.html(`
        <div style="padding:60px;text-align:center;">
            <div class="ecc-shimmer" style="width:80px;height:80px;border-radius:50%;margin:0 auto 20px;"></div>
            <div class="ecc-shimmer" style="width:200px;height:16px;margin:0 auto 10px;"></div>
            <div class="ecc-shimmer" style="width:150px;height:12px;margin:0 auto;"></div>
        </div>
    `);

    try {
        ECC_INV.loading = true;
        const res = await frappe.call({
            method: 'ecclesia.ecclesia.doctype.ecclesia_investment.ecclesia_investment.generate_investment_analysis',
            args: { investment_name: frm.doc.name },
        });

        if (res.message && res.message.success) {
            const a = res.message;
            const risk_color = a.risk_score > 70 ? '#dc2626' : a.risk_score > 50 ? '#d97706' : '#059669';

            const html = `
                <div style="padding:24px;">
                    <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-bottom:24px;">
                        <div class="ecc-gradient-card ecc-gradient-blue">
                            <div style="font-size:11px;opacity:.8;margin-bottom:6px;">ROI</div>
                            <div style="font-size:30px;font-weight:800;">${a.roi}%</div>
                            <div style="font-size:12px;opacity:.8;">Annualised: ${a.annualized_return}%</div>
                        </div>
                        <div class="ecc-gradient-card ecc-gradient-purple">
                            <div style="font-size:11px;opacity:.8;margin-bottom:6px;">RISK SCORE</div>
                            <div style="font-size:30px;font-weight:800;">${a.risk_score}<span style="font-size:16px;">/100</span></div>
                            <div style="font-size:12px;opacity:.8;">${a.risk_score > 70 ? 'High Risk' : a.risk_score > 50 ? 'Moderate' : 'Low Risk'}</div>
                        </div>
                        <div class="ecc-gradient-card ecc-gradient-green">
                            <div style="font-size:11px;opacity:.8;margin-bottom:6px;">REALISABLE VALUE</div>
                            <div style="font-size:22px;font-weight:800;">${_fmt_cur(a.total_return_amount)}</div>
                        </div>
                        <div class="ecc-gradient-card ecc-gradient-amber">
                            <div style="font-size:11px;opacity:.8;margin-bottom:6px;">MARKET COMPARISON</div>
                            <div style="font-size:22px;font-weight:800;">${a.market_comparison}</div>
                            <div style="font-size:12px;opacity:.8;">Market avg: ${a.market_average}%</div>
                        </div>
                    </div>

                    <div class="ecc-panel" style="border-left:4px solid ${risk_color};">
                        <div class="ecc-panel-title">AI Recommendation</div>
                        <div style="font-size:15px;font-weight:600;color:#1e293b;">${a.recommendation}</div>
                    </div>

                    <div class="ecc-panel">
                        <div class="ecc-panel-title">Key Insights</div>
                        <div style="font-size:13px;line-height:1.7;color:#475569;">${a.insights}</div>
                    </div>

                    <div style="padding:12px 16px;background:#fffbeb;border-radius:8px;border-left:4px solid #f59e0b;font-size:11px;color:#92400e;">
                        ⚠️ AI analysis is for informational purposes only. Consult a qualified investment advisor before making decisions.
                    </div>
                </div>
            `;
            d.fields_dict.content.$wrapper.html(html);
        }
    } catch (e) {
        d.fields_dict.content.$wrapper.html(`
            <div style="padding:60px;text-align:center;">
                <div style="font-size:16px;color:#dc2626;font-weight:600;">Analysis failed. Please try again.</div>
            </div>
        `);
    } finally {
        ECC_INV.loading = false;
    }
}

function _export_schedule_csv(frm) {
    const rows = frm.doc.schedule_of_interest || [];
    if (!rows.length) { _toast('No schedule to export', 'warning'); return; }

    let csv = `Ecclesia Investment – Interest Schedule\n`;
    csv += `Investment,${frm.doc.investment_name || frm.doc.name}\n`;
    csv += `Counterparty,${frm.doc.counterparty_name || ''}\n`;
    csv += `Principal,${frm.doc.investment_amount || 0}\n`;
    csv += `Interest Rate,${frm.doc.interest_rate || 0}%\n`;
    csv += `Mode,${frm.doc.interest_payment_mode || ''}\n\n`;
    csv += `Period,Date,Label,Gross Interest,WHT Type,WHT Amount,Mgmt Fee,Net Amount,Status\n`;

    rows.forEach(r => {
        csv += [
            r.period, r.date, r.period_label, r.interest_amount,
            r.wht_type || '', r.wht_amount, r.management_fee_amount, r.net_amount, r.status
        ].join(',') + '\n';
    });

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url;
    a.download = `ECC_INV_Schedule_${frm.doc.name || 'Draft'}_${frappe.datetime.get_today()}.csv`;
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { document.body.removeChild(a); URL.revokeObjectURL(url); }, 200);
    _toast('Schedule exported', 'success');
}

// ---------------------------------------------------------------------------
// HELPERS
// ---------------------------------------------------------------------------

function _setup_queries(frm) {
    ['principal_account','interest_income_account','accrued_interest_account',
     'upfront_interest_deferred_account','wht_payable_account',
     'management_fee_expense_account','dividend_income_account','capital_gain_account']
    .forEach(f => {
        frm.set_query(f, () => ({ filters: { is_group: 0, disabled: 0 } }));
    });
}

function _setup_indicators(frm) {
    frm.dashboard.clear_headline();

    if (frm.doc.investment_amount && frm.doc.returns) {
        const roi = (flt(frm.doc.returns) / flt(frm.doc.investment_amount) * 100).toFixed(2);
        frm.dashboard.add_indicator(__(`ROI: ${roi}%`), roi > 10 ? 'green' : roi > 5 ? 'orange' : 'red');
    }
    if (frm.doc.end_date) {
        const days = frappe.datetime.get_day_diff(frm.doc.end_date, frappe.datetime.nowdate());
        const color = days <= 0 ? 'red' : days <= 30 ? 'orange' : 'blue';
        const label = days <= 0 ? 'Matured' : days === 0 ? 'Matures Today' : `${days} days to maturity`;
        frm.dashboard.add_indicator(__(label), color);
    }
    if (frm.doc.ai_risk_score) {
        const color = frm.doc.ai_risk_score > 70 ? 'red' : frm.doc.ai_risk_score > 50 ? 'orange' : 'green';
        frm.dashboard.add_indicator(__(`Risk: ${frm.doc.ai_risk_score}/100`), color);
    }
}

function _toggle_sections(frm) {
    // Handled by depends_on in JSON; this is for any dynamic logic
}

function _set_duration_category(frm) {
    const years = (frm.doc.tenure_in_days || 0) / 365;
    let cat;
    if (years <= 1)      cat = 'Short-Term (Up to 1 year)';
    else if (years <= 3) cat = 'Short-Term (1-3 years)';
    else if (years <= 5) cat = 'Medium-Term (3-5 years)';
    else                 cat = 'Long-Term (5+ years)';
    frm.set_value('investment_duration_category', cat);
}

function _validate_form(frm) {
    const errors = [];
    if (!frm.doc.investment_amount || frm.doc.investment_amount <= 0) errors.push('Investment amount must be > 0');
    if (!frm.doc.tenure_in_days || frm.doc.tenure_in_days <= 0) errors.push('Tenure must be > 0 days');
    if (frm.doc.investment_type !== 'Shares' && (!frm.doc.interest_rate || frm.doc.interest_rate <= 0)) {
        errors.push('Interest rate must be > 0 for fixed income instruments');
    }
    if (errors.length) {
        frappe.validated = false;
        frappe.throw(errors.join('<br>'));
    }
}

function _style_schedule_grid(frm) {
    setTimeout(() => {
        const grid = frm.fields_dict.schedule_of_interest && frm.fields_dict.schedule_of_interest.grid;
        if (!grid) return;
        grid.wrapper.find('.grid-row').each((i, row) => {
            $(row).css({
                'background': i % 2 === 0 ? '#fff' : '#f8fafc',
                'border-bottom': '1px solid #e2e8f0',
            });
        });
    }, 400);
}

function _fmt_cur(val) {
    return frappe.format(flt(val) || 0, { fieldtype: 'Currency' });
}

function _toast(msg, type = 'info') {
    const icons = { success: '✅', warning: '⚠️', error: '❌', info: 'ℹ️' };
    frappe.show_alert({ message: `${icons[type] || ''} ${msg}`, indicator: type === 'error' ? 'red' : type }, 4);
}

console.log('💎 Ecclesia Investment UI Ready');