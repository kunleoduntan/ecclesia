// Copyright (c) 2026, Value Impacts Consulting
// ecclesia/ecclesia/page/compliance_dashboard/compliance_dashboard_v3.js
//
// ╔══════════════════════════════════════════════════════════════════════════╗
// ║  🏛️ ComplianceHQ v3 — World-Class GRC Command Centre                   ║
// ║  11 Domains · 14 Tabs · AI Analytics · Executive Reports               ║
// ╚══════════════════════════════════════════════════════════════════════════╝

frappe.pages['compliance-dashboard'] = frappe.pages['compliance-dashboard'] || {};

frappe.pages['compliance-dashboard'].on_page_load = function(wrapper) {
    const boot = () => new ComplianceHQv3(wrapper);
    if (typeof Chart === 'undefined') {
        const s = document.createElement('script');
        s.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
        s.onload = boot;
        document.head.appendChild(s);
    } else {
        boot();
    }
};

frappe.pages['compliance-dashboard'].on_page_show = function(wrapper) {
    if (window.__chq3) window.__chq3.refresh(true);
};

// ── THEME REGISTRY ──────────────────────────────────────────────────────────
const CHQ_THEMES = {
    candy: {
        name: 'Candy', icon: '🍬', dark: false,
        colors: {
            bg: '#FDF2F8', bg2: '#FCE7F3', bg3: '#FBCFE8', card: '#FFFFFF',
            brd: '#FBCFE8', brd2: '#F9A8D4', tx1: '#500724', tx2: '#831843', tx3: '#F9A8D4',
            pri: '#DB2777', pri_d: '#BE185D', pri2: '#F472B6', pri_x: 'rgba(219,39,119,.09)',
            acc: '#F472B6', acc_x: 'rgba(244,114,182,.12)',
            grn: '#10B981', grn_x: 'rgba(16,185,129,.09)',
            red: '#EF4444', red_x: 'rgba(239,68,68,.09)',
            amb: '#F59E0B', amb_x: 'rgba(245,158,11,.09)',
            sky: '#06B6D4', sky_x: 'rgba(6,182,212,.09)',
            pink: '#EC4899', pink_x: 'rgba(236,72,153,.09)',
            banner: 'linear-gradient(135deg,#500724 0%,#831843 40%,#DB2777 70%,#EC4899 100%)'
        }
    },
    ocean: {
        name: 'Ocean', icon: '🌊', dark: false,
        colors: {
            bg: '#F0F9FF', bg2: '#E0F2FE', bg3: '#BAE6FD', card: '#FFFFFF',
            brd: '#BAE6FD', brd2: '#7DD3FC', tx1: '#0C4A6E', tx2: '#075985', tx3: '#7DD3FC',
            pri: '#0EA5E9', pri_d: '#0284C7', pri2: '#38BDF8', pri_x: 'rgba(14,165,233,.09)',
            acc: '#38BDF8', acc_x: 'rgba(56,189,248,.12)',
            grn: '#10B981', grn_x: 'rgba(16,185,129,.09)',
            red: '#F43F5E', red_x: 'rgba(244,63,94,.09)',
            amb: '#F59E0B', amb_x: 'rgba(245,158,11,.09)',
            sky: '#06B6D4', sky_x: 'rgba(6,182,212,.09)',
            pink: '#EC4899', pink_x: 'rgba(236,72,153,.09)',
            banner: 'linear-gradient(135deg,#0C4A6E 0%,#0369A1 40%,#0EA5E9 70%,#06B6D4 100%)'
        }
    },
    midnight: {
        name: 'Midnight', icon: '🌙', dark: true,
        colors: {
            bg: '#0F172A', bg2: '#1E293B', bg3: '#334155', card: '#1E293B',
            brd: 'rgba(255,255,255,.08)', brd2: 'rgba(255,255,255,.14)',
            tx1: '#F1F5F9', tx2: '#94A3B8', tx3: '#475569',
            pri: '#818CF8', pri_d: '#6366F1', pri2: '#A5B4FC', pri_x: 'rgba(129,140,248,.12)',
            acc: '#A5B4FC', acc_x: 'rgba(165,180,252,.12)',
            grn: '#34D399', grn_x: 'rgba(52,211,153,.12)',
            red: '#F87171', red_x: 'rgba(248,113,113,.12)',
            amb: '#FCD34D', amb_x: 'rgba(252,211,77,.12)',
            sky: '#38BDF8', sky_x: 'rgba(56,189,248,.12)',
            pink: '#F9A8D4', pink_x: 'rgba(249,168,212,.12)',
            banner: 'linear-gradient(135deg,#020617 0%,#0F172A 50%,#1E3A5F 70%,#312E81 100%)'
        }
    },
    verdant: {
        name: 'Verdant', icon: '🌿', dark: false,
        colors: {
            bg: '#ECFDF5', bg2: '#D1FAE5', bg3: '#A7F3D0', card: '#FFFFFF',
            brd: '#A7F3D0', brd2: '#6EE7B7', tx1: '#022C22', tx2: '#065F46', tx3: '#6EE7B7',
            pri: '#059669', pri_d: '#047857', pri2: '#34D399', pri_x: 'rgba(5,150,105,.09)',
            acc: '#34D399', acc_x: 'rgba(52,211,153,.12)',
            grn: '#10B981', grn_x: 'rgba(16,185,129,.09)',
            red: '#EF4444', red_x: 'rgba(239,68,68,.09)',
            amb: '#F59E0B', amb_x: 'rgba(245,158,11,.09)',
            sky: '#0EA5E9', sky_x: 'rgba(14,165,233,.09)',
            pink: '#EC4899', pink_x: 'rgba(236,72,153,.09)',
            banner: 'linear-gradient(135deg,#022C22 0%,#047857 40%,#059669 70%,#10B981 100%)'
        }
    },
    ember: {
        name: 'Ember', icon: '🔥', dark: false,
        colors: {
            bg: '#FFF7ED', bg2: '#FFEDD5', bg3: '#FED7AA', card: '#FFFFFF',
            brd: '#FED7AA', brd2: '#FDBA74', tx1: '#431407', tx2: '#9A3412', tx3: '#FDBA74',
            pri: '#F97316', pri_d: '#EA580C', pri2: '#FB923C', pri_x: 'rgba(249,115,22,.09)',
            acc: '#FB923C', acc_x: 'rgba(251,146,60,.12)',
            grn: '#22C55E', grn_x: 'rgba(34,197,94,.09)',
            red: '#EF4444', red_x: 'rgba(239,68,68,.09)',
            amb: '#EAB308', amb_x: 'rgba(234,179,8,.09)',
            sky: '#0EA5E9', sky_x: 'rgba(14,165,233,.09)',
            pink: '#EC4899', pink_x: 'rgba(236,72,153,.09)',
            banner: 'linear-gradient(135deg,#431407 0%,#C2410C 40%,#F97316 70%,#EAB308 100%)'
        }
    },
    arctic: {
        name: 'Arctic', icon: '❄️', dark: false,
        colors: {
            bg: '#F8FAFC', bg2: '#F1F5F9', bg3: '#E2E8F0', card: '#FFFFFF',
            brd: '#E2E8F0', brd2: '#CBD5E1', tx1: '#0F172A', tx2: '#334155', tx3: '#94A3B8',
            pri: '#0284C7', pri_d: '#0369A1', pri2: '#7DD3FC', pri_x: 'rgba(2,132,199,.09)',
            acc: '#7DD3FC', acc_x: 'rgba(125,211,252,.12)',
            grn: '#10B981', grn_x: 'rgba(16,185,129,.09)',
            red: '#EF4444', red_x: 'rgba(239,68,68,.09)',
            amb: '#F59E0B', amb_x: 'rgba(245,158,11,.09)',
            sky: '#06B6D4', sky_x: 'rgba(6,182,212,.09)',
            pink: '#EC4899', pink_x: 'rgba(236,72,153,.09)',
            banner: 'linear-gradient(135deg,#0F172A 0%,#1E3A5F 40%,#0284C7 70%,#06B6D4 100%)'
        }
    },
    sunset: {
        name: 'Sunset', icon: '🌅', dark: false,
        colors: {
            bg: '#FFF1F2', bg2: '#FFE4E6', bg3: '#FECDD3', card: '#FFFFFF',
            brd: '#FECDD3', brd2: '#FDA4AF', tx1: '#4C0519', tx2: '#881337', tx3: '#FDA4AF',
            pri: '#DC2626', pri_d: '#B91C1C', pri2: '#F87171', pri_x: 'rgba(220,38,38,.09)',
            acc: '#F87171', acc_x: 'rgba(248,113,113,.12)',
            grn: '#10B981', grn_x: 'rgba(16,185,129,.09)',
            red: '#EF4444', red_x: 'rgba(239,68,68,.09)',
            amb: '#F59E0B', amb_x: 'rgba(245,158,11,.09)',
            sky: '#06B6D4', sky_x: 'rgba(6,182,212,.09)',
            pink: '#EC4899', pink_x: 'rgba(236,72,153,.09)',
            banner: 'linear-gradient(135deg,#4C0519 0%,#881337 40%,#DC2626 70%,#F59E0B 100%)'
        }
    },
    forest: {
        name: 'Forest', icon: '🌲', dark: true,
        colors: {
            bg: '#052E16', bg2: '#14532D', bg3: '#166534', card: '#14532D',
            brd: 'rgba(187,247,208,.1)', brd2: 'rgba(134,239,172,.18)',
            tx1: '#F0FDF4', tx2: '#86EFAC', tx3: '#4ADE80',
            pri: '#22C55E', pri_d: '#16A34A', pri2: '#4ADE80', pri_x: 'rgba(34,197,94,.12)',
            acc: '#4ADE80', acc_x: 'rgba(74,222,128,.12)',
            grn: '#22C55E', grn_x: 'rgba(34,197,94,.12)',
            red: '#F87171', red_x: 'rgba(248,113,113,.12)',
            amb: '#FBBF24', amb_x: 'rgba(251,191,36,.12)',
            sky: '#38BDF8', sky_x: 'rgba(56,189,248,.12)',
            pink: '#F472B6', pink_x: 'rgba(244,114,182,.12)',
            banner: 'linear-gradient(135deg,#052E16 0%,#14532D 40%,#166534 70%,#22C55E 100%)'
        }
    },
    nova: {
        name: 'Nova', icon: '🌟', dark: false,
        colors: {
            bg: '#FAF5FF', bg2: '#F5F3FF', bg3: '#EDE9FE', card: '#FFFFFF',
            brd: '#E9D5FF', brd2: '#D8B4FE', tx1: '#2E1065', tx2: '#5B21B6', tx3: '#A78BFA',
            pri: '#7C3AED', pri_d: '#6D28D9', pri2: '#A78BFA', pri_x: 'rgba(124,58,237,.09)',
            acc: '#A78BFA', acc_x: 'rgba(167,139,250,.12)',
            grn: '#10B981', grn_x: 'rgba(16,185,129,.09)',
            red: '#EF4444', red_x: 'rgba(239,68,68,.09)',
            amb: '#F59E0B', amb_x: 'rgba(245,158,11,.09)',
            sky: '#06B6D4', sky_x: 'rgba(6,182,212,.09)',
            pink: '#EC4899', pink_x: 'rgba(236,72,153,.09)',
            banner: 'linear-gradient(135deg,#1E1B4B 0%,#4C1D95 40%,#7C3AED 70%,#EC4899 100%)'
        }
    }
};

// ── DOMAIN CONFIG ────────────────────────────────────────────────────────────
const CHQ_DOMAINS = [
    { key: 'overview',     icon: '🏠', label: 'Overview',     badge: null },
    { key: 'statutory',    icon: '💰', label: 'Statutory Tax', badge: 'vat_overdue' },
    { key: 'corporate',    icon: '🏢', label: 'Governance',    badge: 'corporate_issues' },
    { key: 'contracts',    icon: '📄', label: 'Contracts',     badge: 'contract_breaches' },
    { key: 'ndpr',         icon: '🔒', label: 'NDPR',          badge: 'breach_open' },
    { key: 'aml',          icon: '🕵️', label: 'AML & KYC',    badge: 'high_risk' },
    { key: 'labour',       icon: '👷', label: 'Labour',        badge: 'permit_expired' },
    { key: 'environmental', icon: '🌿', label: 'Environmental', badge: 'env_expired' },
    { key: 'industry',     icon: '🏭', label: 'Regulatory',    badge: 'reg_overdue' },
    { key: 'fraud',        icon: '🚨', label: 'Integrity',     badge: 'wb_open' },
    { key: 'training',     icon: '🎓', label: 'Training',      badge: 'training_gap' },
    { key: 'ai',           icon: '🤖', label: 'AI Analysis',   badge: null },
    { key: 'calendar',     icon: '📅', label: 'Calendar',      badge: null },
    { key: 'reports',      icon: '📊', label: 'Reports',       badge: null },
];

// ═══════════════════════════════════════════════════════════════════════════════
//  MAIN CLASS
// ═══════════════════════════════════════════════════════════════════════════════
class ComplianceHQv3 {
    constructor(wrapper) {
        this.wrapper = wrapper;
        this.page = frappe.ui.make_app_page({
            parent: wrapper,
            title: '🏛️ ComplianceHQ',
            single_column: true
        });
        this.charts = {};
        this.activeTab = 'overview';
        this.company = frappe.defaults.get_default('company') || '';
        this.fiscalMonth = this._curMonth();
        this.data = {};
        this.v3data = {};
        this.scores = {};
        this.theme = this._getTheme();
        this.timer = null;
        window.__chq3 = this;
        this._init();
    }

    _init() {
        this._injectCSS();
        this._buildLayout();
        this._applyTheme(this.theme, false);
        this._bindEvents();
        this._clock();
        this._loadAll();
        setInterval(() => this.refresh(true), 60000);
    }

    _getTheme() {
        try { return localStorage.getItem('chq3-theme') || 'ocean'; }
        catch (e) { return 'ocean'; }
    }

    _curMonth() {
        const d = new Date();
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    }

    // ── THEME ENGINE ──────────────────────────────────────────────────────────
    _applyTheme(key, save = true) {
        const t = CHQ_THEMES[key] || CHQ_THEMES.ocean;
        this.theme = key;
        if (save) {
            try { localStorage.setItem('chq3-theme', key); } catch (e) {}
        }
        const root = document.getElementById('chq3-root');
        if (!root) return;
        const c = t.colors;
        Object.entries(c).forEach(([k, v]) => {
            root.style.setProperty(`--chq-${k}`, v);
        });
        if (t.dark) root.classList.add('dark');
        else root.classList.remove('dark');
        document.getElementById('chq3-theme-lbl').textContent = t.icon + ' ' + t.name;
        Object.values(this.charts).forEach(ch => { try { ch.update(); } catch (e) {} });
    }

    openThemePicker() {
        const cur = this.theme;
        const d = new frappe.ui.Dialog({
            title: '🎨 ComplianceHQ Theme',
            size: 'large',
            fields: [{
                fieldtype: 'HTML',
                options: `
                <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;padding:8px 0">
                    ${Object.entries(CHQ_THEMES).map(([k, t]) => {
                        const c = t.colors;
                        const isActive = k === cur;
                        return `
                        <div onclick="window.__chq3._applyTheme('${k}');if(window.__chq3_td)window.__chq3_td.hide();"
                            style="display:flex;align-items:center;gap:12px;padding:14px 16px;border-radius:14px;
                                border:2px solid ${isActive ? c.pri : c.brd2};
                                background:${c.card};cursor:pointer;transition:all .18s;color:${c.tx1}">
                            <div style="font-size:24px;width:40px;height:40px;border-radius:10px;
                                        background:${c.pri_x};display:flex;align-items:center;justify-content:center;flex-shrink:0">
                                ${t.icon}
                            </div>
                            <div style="flex:1">
                                <div style="font-size:13px;font-weight:700;margin-bottom:4px">${t.name}</div>
                                <div style="display:flex;gap:4px;margin-bottom:4px">
                                    ${['pri','acc','grn','sky','pink'].map(h => `
                                        <div style="width:14px;height:14px;border-radius:4px;background:${c[h]}"></div>
                                    `).join('')}
                                </div>
                                <div style="font-size:10px;color:${c.tx3}">${t.dark ? '🌙 Dark' : '☀️ Light'}</div>
                            </div>
                            ${isActive ? `<span style="font-size:18px;color:${c.pri};flex-shrink:0">✓</span>` : ''}
                        </div>`;
                    }).join('')}
                </div>
                <div style="font-size:11px;color:var(--chq-tx3);margin-top:12px;text-align:center">
                    ✨ Themes are stored in your browser — no database writes
                </div>
                `
            }]
        });
        window.__chq3_td = d;
        d.show();
    }

    // ── CSS INJECTION ────────────────────────────────────────────────────────
    _injectCSS() {
        if (document.getElementById('chq3-css')) return;
        const s = document.createElement('style');
        s.id = 'chq3-css';
        s.textContent = `
        /* ─── ROOT VARIABLES ─── */
        #chq3-root {
            --chq-bg: #F0F9FF;
            --chq-bg2: #E0F2FE;
            --chq-bg3: #BAE6FD;
            --chq-card: #FFFFFF;
            --chq-brd: #BAE6FD;
            --chq-brd2: #7DD3FC;
            --chq-tx1: #0C4A6E;
            --chq-tx2: #075985;
            --chq-tx3: #7DD3FC;
            --chq-pri: #0EA5E9;
            --chq-pri_d: #0284C7;
            --chq-pri2: #38BDF8;
            --chq-pri_x: rgba(14,165,233,.09);
            --chq-acc: #38BDF8;
            --chq-acc_x: rgba(56,189,248,.12);
            --chq-grn: #10B981;
            --chq-grn_x: rgba(16,185,129,.09);
            --chq-red: #F43F5E;
            --chq-red_x: rgba(244,63,94,.09);
            --chq-amb: #F59E0B;
            --chq-amb_x: rgba(245,158,11,.09);
            --chq-sky: #06B6D4;
            --chq-sky_x: rgba(6,182,212,.09);
            --chq-pink: #EC4899;
            --chq-pink_x: rgba(236,72,153,.09);
            --chq-banner: linear-gradient(135deg,#0C4A6E 0%,#0369A1 40%,#0EA5E9 70%,#06B6D4 100%);
            font-family: 'Inter', system-ui, sans-serif;
            background: var(--chq-bg);
            color: var(--chq-tx1);
            min-height: 100vh;
            transition: background .3s ease, color .3s ease;
        }
        #chq3-root * { box-sizing: border-box; }

        /* ─── BANNER ─── */
        .chq-banner {
            background: var(--chq-banner);
            padding: 24px 32px 20px;
            border-radius: 20px;
            margin: -12px -12px 20px;
            position: relative;
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(0,0,0,.12);
        }
        .chq-banner::before {
            content: '';
            position: absolute;
            width: 500px;
            height: 500px;
            top: -40%;
            right: -10%;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(255,255,255,.08), transparent 65%);
        }
        .chq-banner-inner {
            position: relative;
            z-index: 1;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 16px;
        }
        .chq-banner h1 {
            font-size: 24px;
            font-weight: 800;
            letter-spacing: -.4px;
            margin: 0 0 6px;
            display: flex;
            align-items: center;
            gap: 12px;
            color: #fff;
        }
        .chq-banner h1 small {
            font-size: 13px;
            font-weight: 400;
            opacity: .7;
        }
        .chq-meta {
            display: flex;
            align-items: center;
            gap: 14px;
            font-size: 12px;
            color: rgba(255,255,255,.8);
            flex-wrap: wrap;
        }
        .chq-live {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(5,150,105,.22);
            padding: 3px 12px;
            border-radius: 30px;
            font-size: 10px;
            color: #34d399;
            border: 1px solid rgba(5,150,105,.3);
        }
        .chq-live-dot {
            width: 7px;
            height: 7px;
            background: #34d399;
            border-radius: 50%;
            animation: chq-pulse 2s infinite;
        }
        @keyframes chq-pulse {
            0%,100% { opacity: 1; transform: scale(1); }
            50% { opacity: .4; transform: scale(1.3); }
        }
        .chq-chip {
            background: rgba(255,255,255,.14);
            padding: 3px 12px;
            border-radius: 30px;
            font-size: 10px;
            font-weight: 600;
            color: rgba(255,255,255,.9);
        }
        .chq-score-ring {
            display: inline-flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            width: 80px;
            height: 80px;
            border-radius: 50%;
            border: 4px solid rgba(255,255,255,.3);
            background: rgba(255,255,255,.08);
            backdrop-filter: blur(8px);
            transition: border-color .6s ease;
        }
        .chq-score-num {
            font-size: 22px;
            font-weight: 800;
            color: #fff;
            line-height: 1;
        }
        .chq-score-lbl {
            font-size: 9px;
            opacity: .7;
            color: #fff;
            margin-top: 2px;
        }
        .chq-top-btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 5px 14px;
            border-radius: 30px;
            font-size: 11px;
            font-weight: 700;
            background: rgba(255,255,255,.15);
            border: 1px solid rgba(255,255,255,.25);
            color: #fff;
            cursor: pointer;
            transition: background .18s;
            font-family: inherit;
        }
        .chq-top-btn:hover { background: rgba(255,255,255,.28); }

        /* ─── ALERTS ─── */
        .chq-alerts {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 16px;
        }
        .chq-alert {
            display: flex;
            align-items: center;
            gap: 7px;
            padding: 6px 14px;
            border-radius: 11px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            border: 1px solid transparent;
            transition: transform .15s;
            text-decoration: none !important;
        }
        .chq-alert:hover { transform: translateY(-2px); }
        .chq-alert-red   { background: var(--chq-red_x); border-color: rgba(244,63,94,.2); color: var(--chq-red); }
        .chq-alert-amb   { background: var(--chq-amb_x); border-color: rgba(245,158,11,.2); color: var(--chq-amb); }
        .chq-alert-grn   { background: var(--chq-grn_x); border-color: rgba(16,185,129,.2); color: var(--chq-grn); }
        .chq-alert-pri   { background: var(--chq-pri_x); border-color: rgba(14,165,233,.2); color: var(--chq-pri); }

        /* ─── TABS ─── */
        .chq-tabs {
            display: flex;
            gap: 2px;
            background: var(--chq-card);
            border: 1px solid var(--chq-brd);
            border-radius: 14px;
            margin-bottom: 18px;
            overflow-x: auto;
            scrollbar-width: none;
            padding: 4px;
        }
        .chq-tabs::-webkit-scrollbar { display: none; }
        .chq-tab {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 8px 14px;
            font-size: 11px;
            font-weight: 600;
            color: var(--chq-tx2);
            cursor: pointer;
            border-radius: 10px;
            transition: all .15s;
            white-space: nowrap;
            background: none;
            border: none;
            font-family: inherit;
        }
        .chq-tab:hover { color: var(--chq-pri); background: var(--chq-pri_x); }
        .chq-tab.active {
            color: var(--chq-pri);
            background: var(--chq-pri_x);
            box-shadow: inset 0 0 0 1px var(--chq-pri);
        }
        .chq-tab-badge {
            background: var(--chq-red);
            color: #fff;
            font-size: 9px;
            font-weight: 800;
            padding: 1px 6px;
            border-radius: 30px;
            min-width: 16px;
            text-align: center;
        }

        /* ─── KPI CARDS ─── */
        .chq-kpis {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 12px;
            margin-bottom: 18px;
        }
        .chq-kpi {
            background: var(--chq-card);
            border: 1px solid var(--chq-brd);
            border-radius: 14px;
            padding: 16px 18px;
            cursor: pointer;
            transition: all .2s;
            position: relative;
            overflow: hidden;
        }
        .chq-kpi::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: var(--chq-kc, var(--chq-pri));
            opacity: 0;
            transition: opacity .2s;
        }
        .chq-kpi:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 30px rgba(0,0,0,.08);
            border-color: var(--chq-brd2);
        }
        .chq-kpi:hover::after { opacity: 1; }
        .chq-kpi-icon { font-size: 18px; margin-bottom: 6px; }
        .chq-kpi-label {
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: .6px;
            color: var(--chq-tx3);
            margin-bottom: 4px;
        }
        .chq-kpi-value {
            font-size: 24px;
            font-weight: 800;
            color: var(--chq-tx1);
            line-height: 1;
            margin-bottom: 2px;
        }
        .chq-kpi-sub {
            font-size: 10px;
            color: var(--chq-tx3);
        }

        /* ─── CARDS ─── */
        .chq-card {
            background: var(--chq-card);
            border: 1px solid var(--chq-brd);
            border-radius: 14px;
            overflow: hidden;
            transition: box-shadow .2s;
            margin-bottom: 16px;
        }
        .chq-card:hover { box-shadow: 0 4px 24px rgba(0,0,0,.06); }
        .chq-card-head {
            padding: 12px 18px;
            border-bottom: 1px solid var(--chq-brd);
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            flex-wrap: wrap;
        }
        .chq-card-title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            font-weight: 700;
            color: var(--chq-tx1);
        }
        .chq-card-body { padding: 16px 18px; }

        /* ─── GRIDS ─── */
        .chq-g2  { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
        .chq-g3  { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin-bottom: 16px; }
        .chq-g21 { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; margin-bottom: 16px; }
        .chq-g31 { display: grid; grid-template-columns: 3fr 1fr; gap: 16px; margin-bottom: 16px; }
        @media (max-width: 1100px) { .chq-g21, .chq-g31 { grid-template-columns: 1fr; } }
        @media (max-width: 900px)  { .chq-g2, .chq-g3 { grid-template-columns: 1fr; } }

        /* ─── BUTTONS ─── */
        .chq-btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            border-radius: 30px;
            font-size: 11px;
            font-weight: 700;
            cursor: pointer;
            border: 1.5px solid transparent;
            font-family: inherit;
            transition: all .15s;
            text-decoration: none !important;
        }
        .chq-btn:hover { transform: translateY(-1px); }
        .chq-btn-pri  { background: var(--chq-pri_x); color: var(--chq-pri); border-color: rgba(14,165,233,.2); }
        .chq-btn-pri:hover  { background: var(--chq-pri); color: #fff; }
        .chq-btn-grn  { background: var(--chq-grn_x); color: var(--chq-grn); border-color: rgba(16,185,129,.2); }
        .chq-btn-grn:hover  { background: var(--chq-grn); color: #fff; }
        .chq-btn-red  { background: var(--chq-red_x); color: var(--chq-red); border-color: rgba(244,63,94,.2); }
        .chq-btn-red:hover  { background: var(--chq-red); color: #fff; }
        .chq-btn-amb  { background: var(--chq-amb_x); color: var(--chq-amb); border-color: rgba(245,158,11,.2); }
        .chq-btn-amb:hover  { background: var(--chq-amb); color: #fff; }
        .chq-btn-sky  { background: var(--chq-sky_x); color: var(--chq-sky); border-color: rgba(6,182,212,.2); }
        .chq-btn-sky:hover  { background: var(--chq-sky); color: #fff; }
        .chq-btn-ghost { background: transparent; color: var(--chq-tx2); border-color: var(--chq-brd2); }
        .chq-btn-ghost:hover { background: var(--chq-bg2); color: var(--chq-tx1); }
        .chq-btn-solid { background: var(--chq-pri); color: #fff; border-color: var(--chq-pri); box-shadow: 0 4px 16px rgba(14,165,233,.35); }
        .chq-btn-solid:hover { background: var(--chq-pri_d); box-shadow: 0 6px 24px rgba(14,165,233,.45); }
        .chq-btn-sm { padding: 4px 10px; font-size: 10px; }
        .chq-btn-xs { padding: 2px 8px; font-size: 9px; border-radius: 20px; }

        /* ─── BADGES ─── */
        .chq-badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 2px 9px;
            border-radius: 30px;
            font-size: 10px;
            font-weight: 700;
            white-space: nowrap;
        }
        .chq-badge-pri  { background: var(--chq-pri_x); color: var(--chq-pri); }
        .chq-badge-grn  { background: var(--chq-grn_x); color: var(--chq-grn); }
        .chq-badge-red  { background: var(--chq-red_x); color: var(--chq-red); }
        .chq-badge-amb  { background: var(--chq-amb_x); color: var(--chq-amb); }
        .chq-badge-sky  { background: var(--chq-sky_x); color: var(--chq-sky); }
        .chq-badge-grey { background: var(--chq-bg3); color: var(--chq-tx3); border: 1px solid var(--chq-brd); }

        /* ─── TABLES ─── */
        .chq-table-wrap {
            overflow-x: auto;
            max-height: 460px;
            overflow-y: auto;
            scrollbar-width: thin;
            scrollbar-color: var(--chq-brd2) transparent;
        }
        .chq-table-wrap::-webkit-scrollbar { width: 4px; height: 4px; }
        .chq-table-wrap::-webkit-scrollbar-thumb { background: var(--chq-brd2); border-radius: 10px; }
        .chq-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }
        .chq-table thead th {
            padding: 8px 12px;
            text-align: left;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: .5px;
            color: var(--chq-tx3);
            background: var(--chq-bg2);
            border-bottom: 2px solid var(--chq-brd);
            position: sticky;
            top: 0;
            z-index: 2;
            white-space: nowrap;
        }
        .chq-table tbody td {
            padding: 8px 12px;
            border-bottom: 1px solid var(--chq-brd);
            color: var(--chq-tx2);
        }
        .chq-table tbody tr {
            cursor: pointer;
            transition: background .1s;
        }
        .chq-table tbody tr:hover {
            background: var(--chq-pri_x);
        }
        .chq-table tbody tr:hover td {
            color: var(--chq-tx1);
        }
        .chq-table tbody tr:last-child td {
            border-bottom: none;
        }

        /* ─── DOMAIN SCORE GRID ─── */
        .chq-domain-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px;
            margin-bottom: 16px;
        }
        .chq-domain-item {
            background: var(--chq-card);
            border: 1px solid var(--chq-brd);
            border-radius: 12px;
            padding: 14px;
            text-align: center;
            cursor: pointer;
            transition: all .15s;
        }
        .chq-domain-item:hover {
            transform: translateY(-3px);
            border-color: var(--chq-pri);
            box-shadow: 0 4px 20px rgba(0,0,0,.06);
        }
        .chq-domain-item .chq-di-icon { font-size: 24px; margin-bottom: 6px; }
        .chq-domain-item .chq-di-name {
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: .4px;
            color: var(--chq-tx3);
            margin-bottom: 6px;
        }
        .chq-domain-item .chq-di-score {
            font-size: 22px;
            font-weight: 800;
            line-height: 1;
        }
        .chq-domain-item .chq-di-bar {
            height: 4px;
            background: var(--chq-brd);
            border-radius: 10px;
            overflow: hidden;
            margin-top: 8px;
        }
        .chq-domain-item .chq-di-bar-fill {
            height: 100%;
            border-radius: 10px;
            transition: width .7s cubic-bezier(.4,0,.2,1);
        }

        /* ─── PROGRESS BARS ─── */
        .chq-bar-row {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 8px;
        }
        .chq-bar-label {
            font-size: 11px;
            color: var(--chq-tx2);
            width: 140px;
            flex-shrink: 0;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .chq-bar {
            flex: 1;
            height: 5px;
            background: var(--chq-brd);
            border-radius: 40px;
            overflow: hidden;
        }
        .chq-bar-fill {
            height: 100%;
            border-radius: 40px;
            transition: width .6s cubic-bezier(.4,0,.2,1);
        }
        .chq-bar-value {
            font-size: 11px;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            width: 50px;
            text-align: right;
            color: var(--chq-tx1);
        }

        /* ─── PANELS ─── */
        .chq-panel { display: none; }
        .chq-panel.active { display: block; animation: chq-fade .3s ease; }
        @keyframes chq-fade { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

        /* ─── MISC ─── */
        .chq-empty {
            text-align: center;
            padding: 40px 20px;
            color: var(--chq-tx3);
            font-size: 13px;
        }
        .chq-empty-icon { font-size: 36px; margin-bottom: 12px; }
        .chq-divider { border: none; border-top: 1px solid var(--chq-brd); margin: 16px 0; }
        .chq-mono { font-family: 'JetBrains Mono', monospace; }
        .chq-spin { animation: chq-spin .8s linear infinite; display: inline-block; }
        @keyframes chq-spin { to { transform: rotate(360deg); } }

        .chq-loader {
            position: fixed;
            inset: 0;
            background: rgba(10,15,30,.82);
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            gap: 14px;
            z-index: 999;
        }
        .chq-spinner {
            width: 40px;
            height: 40px;
            border: 3px solid var(--chq-brd2);
            border-top-color: var(--chq-pri);
            border-radius: 50%;
            animation: chq-spin .7s linear infinite;
        }

        .chq-content { padding: 0 16px 32px; }

        /* ─── REPORTS ─── */
        .chq-report-card {
            background: var(--chq-bg2);
            border-radius: 12px;
            padding: 16px 20px;
            border-left: 4px solid var(--chq-pri);
            margin-bottom: 12px;
        }
        .chq-report-card h4 {
            font-size: 12px;
            font-weight: 700;
            color: var(--chq-tx1);
            margin: 0 0 4px;
        }
        .chq-report-card p {
            font-size: 12px;
            color: var(--chq-tx2);
            margin: 0;
            line-height: 1.6;
        }
        `;
        document.head.appendChild(s);
    }

    // ── LAYOUT ────────────────────────────────────────────────────────────────
    _buildLayout() {
        $(this.page.main).empty();

        const tabsHTML = CHQ_DOMAINS.map(d => `
            <button class="chq-tab ${d.key === 'overview' ? 'active' : ''}" data-tab="${d.key}">
                ${d.icon} ${d.label}
                ${d.badge ? `<span class="chq-tab-badge" id="chq-badge-${d.key}" style="display:none">!</span>` : ''}
            </button>
        `).join('');

        const panelsHTML = CHQ_DOMAINS.map(d => `
            <div id="chq-panel-${d.key}" class="chq-panel ${d.key === 'overview' ? 'active' : ''}"></div>
        `).join('');

        $(`
        <div id="chq3-root">
            <div class="chq-banner">
                <div class="chq-banner-inner">
                    <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap">
                        <div>
                            <h1>🏛️ ComplianceHQ <small>v3 · Full GRC Suite</small></h1>
                            <div class="chq-meta">
                                <span>📅 <span id="chq-date"></span></span>
                                <span>🕐 <span id="chq-clock" class="chq-mono"></span></span>
                                <span class="chq-live"><span class="chq-live-dot"></span> Live</span>
                                <span class="chq-chip" id="chq-chip1">Loading…</span>
                                <span class="chq-chip" id="chq-chip2">Loading…</span>
                            </div>
                        </div>
                        <div class="chq-score-ring" id="chq-score-ring">
                            <div class="chq-score-num" id="chq-score-num">—</div>
                            <div class="chq-score-lbl">GRC Score</div>
                        </div>
                    </div>
                    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
                        <select id="chq-company" class="chq-top-btn" style="cursor:pointer;outline:none;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.15);color:#fff">
                            <option value="">Select Company</option>
                        </select>
                        <select id="chq-period" class="chq-top-btn" style="cursor:pointer;outline:none;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.15);color:#fff;font-family:'JetBrains Mono',monospace">
                        </select>
                        <button class="chq-top-btn" onclick="window.__chq3.openThemePicker()">
                            🎨 <span id="chq3-theme-lbl">🌊 Ocean</span>
                        </button>
                        <span id="chq-ts" style="font-size:10px;opacity:.5;color:#fff"></span>
                    </div>
                </div>
            </div>

            <div class="chq-content">
                <div class="chq-alerts" id="chq-alerts"></div>
                <div class="chq-tabs">${tabsHTML}</div>
                ${panelsHTML}
            </div>

            <div class="chq-loader" id="chq-loader" style="display:none">
                <div class="chq-spinner"></div>
                <div style="font-weight:600;font-size:14px;color:#F1F5F9">Loading ComplianceHQ</div>
                <div style="font-size:12px;color:#94A3B8">Fetching all 11 compliance domains…</div>
            </div>
        </div>
        `).appendTo(this.page.main);

        this._populateSelects();
    }

    _populateSelects() {
        // Company
        frappe.db.get_list('Company', { filters: { is_group: 0 }, fields: ['name'], limit: 50 }).then(rows => {
            const sel = document.getElementById('chq-company');
            if (!sel) return;
            rows.forEach(r => {
                const o = document.createElement('option');
                o.value = r.name;
                o.text = r.name;
                if (r.name === this.company) o.selected = true;
                sel.appendChild(o);
            });
            if (!this.company && rows.length) this.company = rows[0].name;
            sel.onchange = () => { this.company = sel.value; this._loadAll(); };
        });

        // Period
        const sel = document.getElementById('chq-period');
        if (!sel) return;
        const now = new Date();
        for (let i = 0; i < 24; i++) {
            const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
            const val = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
            const o = document.createElement('option');
            o.value = val;
            o.text = d.toLocaleDateString('en-NG', { month: 'short', year: 'numeric' });
            if (val === this.fiscalMonth) o.selected = true;
            sel.appendChild(o);
        }
        sel.onchange = () => { this.fiscalMonth = sel.value; this._loadAll(); };
    }

    _bindEvents() {
        $(document).on('click', '.chq-tab', e => {
            this._switchTab($(e.currentTarget).data('tab'));
        });
    }

    _switchTab(name) {
        $('.chq-tab').removeClass('active');
        $(`.chq-tab[data-tab="${name}"]`).addClass('active');
        $('.chq-panel').removeClass('active');
        $(`#chq-panel-${name}`).addClass('active');
        this.activeTab = name;
        if (Object.keys(this.data).length || Object.keys(this.v3data).length) {
            this._render(name);
        }
    }

    _clock() {
        const tick = () => {
            document.getElementById('chq-clock').textContent =
                new Date().toLocaleTimeString('en-NG', { hour12: true, hour: '2-digit', minute: '2-digit', second: '2-digit' });
            document.getElementById('chq-date').textContent =
                frappe.datetime.str_to_user(frappe.datetime.get_today());
        };
        tick();
        setInterval(tick, 1000);
    }

    // ── DATA LOADING ─────────────────────────────────────────────────────────
    async _loadAll(silent = false) {
        if (!this.company) return;
        if (!silent) document.getElementById('chq-loader').style.display = 'flex';

        try {
            const [r1, r2, r3] = await Promise.all([
                frappe.call({
                    method: 'ecclesia.ecclesia.page.compliance_dashboard.compliance_dashboard.get_dashboard_summary',
                    args: { company: this.company, fiscal_month: this.fiscalMonth }
                }),
                frappe.call({
                    method: 'ecclesia.ecclesia.page.compliance_dashboard.compliance_dashboard.get_v3_domain_summary',
                    args: { company: this.company }
                }),
                frappe.call({
                    method: 'ecclesia.ecclesia.page.compliance_dashboard.compliance_dashboard.get_full_compliance_score',
                    args: { company: this.company }
                })
            ]);

            this.data = r1.message || {};
            this.v3data = r2.message || {};
            this.scores = r3.message || {};

            this._updateBanner();
            this._buildAlerts();
            this._updateScoreRing();
            this._updateTabBadges();
            this._render(this.activeTab);

            document.getElementById('chq-ts').textContent =
                'Updated ' + new Date().toLocaleTimeString('en-NG', { hour12: true });

        } catch (e) {
            console.error('ComplianceHQ load error:', e);
            if (!silent) {
                frappe.msgprint({
                    title: 'Load Error',
                    indicator: 'red',
                    message: 'Failed to load compliance data. Please try again.'
                });
            }
        } finally {
            document.getElementById('chq-loader').style.display = 'none';
        }
    }

    refresh(silent = false) { this._loadAll(silent); }

    // ── UI UPDATES ──────────────────────────────────────────────────────────
    _updateBanner() {
        const v3 = this.v3data;
        const lic = this.data.licenses || {};
        const cal = this.data.calendar || {};
        const totalIssues = (lic.expired || 0) +
            (v3.corporate?.non_compliant || 0) +
            (v3.ndpr?.open_breaches || 0) +
            (v3.environmental?.expired || 0) +
            (v3.industry?.overdue || 0);

        document.getElementById('chq-chip1').textContent =
            `${totalIssues} compliance issues · ${lic.expired||0} expired licenses`;
        document.getElementById('chq-chip2').textContent =
            `${(v3.training?.mandatory_pct||0).toFixed(0)}% training complete · ${cal.count||0} obligations due`;
    }

    _updateScoreRing() {
        const s = this.scores.overall_v3 || 0;
        const ring = document.getElementById('chq-score-ring');
        const num = document.getElementById('chq-score-num');
        if (num) num.textContent = Math.round(s) + '%';
        if (ring) {
            ring.style.borderColor = s >= 80 ? '#34d399' : s >= 60 ? '#fcd34d' : '#f87171';
        }
    }

    _updateTabBadges() {
        const v3 = this.v3data;
        const tax = this.data.tax || {};
        const _b = (id, count) => {
            const el = document.getElementById(`chq-badge-${id}`);
            if (el) {
                el.textContent = count > 0 ? count : '';
                el.style.display = count > 0 ? '' : 'none';
            }
        };
        _b('statutory', ['VAT', 'WHT', 'PAYE'].filter(o => (tax[o] || {}).status === 'Overdue').length);
        _b('corporate', (v3.corporate?.non_compliant || 0) + (v3.corporate?.annual_return_overdue || 0));
        _b('contracts', (v3.contracts?.material_breach || 0) + (v3.contracts?.termination_risk || 0));
        _b('ndpr', v3.ndpr?.open_breaches || 0);
        _b('aml', (v3.aml?.high_risk || 0) + (v3.aml?.sanctions_match || 0));
        _b('labour', v3.labour?.expired_permits || 0);
        _b('environmental', v3.environmental?.expired || 0);
        _b('industry', v3.industry?.overdue || 0);
        _b('fraud', (v3.fraud?.under_investigation || 0) + (v3.fraud?.coi_pending_review || 0));
        _b('training', Math.max(0, 100 - (v3.training?.mandatory_pct || 100)) > 20 ? 1 : 0);
    }

    _buildAlerts() {
        const v3 = this.v3data;
        const tax = this.data.tax || {};
        const lic = this.data.licenses || {};
        const alerts = [];
        const add = (cls, icon, text, tab) => alerts.push({ cls, icon, text, tab });

        if (lic.expired > 0) add('chq-alert-red', '🎖', `${lic.expired} license${lic.expired>1?'s':''} EXPIRED`, 'statutory');
        if ((tax.VAT || {}).status === 'Overdue') add('chq-alert-red', '💼', `VAT ${this.fiscalMonth} OVERDUE`, 'statutory');
        if ((tax.PAYE || {}).status === 'Overdue') add('chq-alert-red', '👤', `PAYE ${this.fiscalMonth} OVERDUE`, 'statutory');
        if (v3.corporate?.annual_return_overdue > 0) add('chq-alert-red', '🏢', `${v3.corporate.annual_return_overdue} CAC return${v3.corporate.annual_return_overdue>1?'s':''} OVERDUE`, 'corporate');
        if (v3.ndpr?.open_breaches > 0) add('chq-alert-red', '🔒', `${v3.ndpr.open_breaches} open data breach${v3.ndpr.open_breaches>1?'es':''}`, 'ndpr');
        if (v3.aml?.sanctions_match > 0) add('chq-alert-red', '⛔', `${v3.aml.sanctions_match} SANCTIONS MATCH`, 'aml');
        if (v3.environmental?.expired > 0) add('chq-alert-red', '🌿', `${v3.environmental.expired} environmental permit${v3.environmental.expired>1?'s':''} EXPIRED`, 'environmental');
        if (v3.industry?.overdue > 0) add('chq-alert-amb', '🏭', `${v3.industry.overdue} regulatory return${v3.industry.overdue>1?'s':''} OVERDUE`, 'industry');
        if (v3.contracts?.material_breach > 0) add('chq-alert-amb', '📄', `${v3.contracts.material_breach} contract material breach${v3.contracts.material_breach>1?'es':''}`, 'contracts');
        if (v3.fraud?.under_investigation > 0) add('chq-alert-amb', '🚨', `${v3.fraud.under_investigation} whistleblower report${v3.fraud.under_investigation>1?'s':''} under investigation`, 'fraud');

        const container = document.getElementById('chq-alerts');
        if (container) {
            container.innerHTML = alerts.length ?
                alerts.map(a =>
                    `<a class="chq-alert ${a.cls}" href="#" onclick="window.__chq3._switchTab('${a.tab}');return false">${a.icon} ${a.text}</a>`
                ).join('') :
                '<div class="chq-alert chq-alert-grn">✅ No critical compliance alerts at this time</div>';
        }
    }

    // ── RENDER DISPATCHER ───────────────────────────────────────────────────
    _render(name) {
        const map = {
            overview: () => this._renderOverview(),
            statutory: () => this._renderStatutory(),
            corporate: () => this._renderCorporate(),
            contracts: () => this._renderContracts(),
            ndpr: () => this._renderNdpr(),
            aml: () => this._renderAml(),
            labour: () => this._renderLabour(),
            environmental: () => this._renderEnvironmental(),
            industry: () => this._renderIndustry(),
            fraud: () => this._renderFraud(),
            training: () => this._renderTraining(),
            ai: () => this._renderAI(),
            calendar: () => this._renderCalendar(),
            reports: () => this._renderReports(),
        };
        if (map[name]) map[name]();
    }

    // ── HELPERS ──────────────────────────────────────────────────────────────
    F(v) {
        const n = parseFloat(v) || 0;
        if (n >= 1e9) return '₦' + (n / 1e9).toFixed(1) + 'B';
        if (n >= 1e6) return '₦' + (n / 1e6).toFixed(1) + 'M';
        if (n >= 1e3) return '₦' + (n / 1e3).toFixed(0) + 'k';
        return '₦' + Math.round(n).toLocaleString();
    }

    B(text, cls) { return `<span class="chq-badge chq-badge-${cls}">${text}</span>`; }

    SB(status) {
        const m = {
            'Compliant': 'grn',
            'Non-Compliant': 'red',
            'Minor Issues': 'amb',
            'Major Issues': 'red',
            'Material Breach': 'red',
            'Termination Risk': 'red',
            'Minor Breach': 'amb',
            'Expired': 'red',
            'Active': 'grn',
            'Expiring Soon': 'amb',
            'Open': 'pri',
            'Closed': 'grey',
            'Overdue': 'red',
            'Submitted': 'grn',
            'Late Submitted': 'amb',
            'Pending': 'grey',
            'High': 'red',
            'Medium': 'amb',
            'Low': 'grn',
            'Critical': 'red',
            'PEP — High': 'pri',
            'Sanctioned — Blocked': 'red',
            'Received': 'pri',
            'Under Investigation': 'amb',
            'Escalated': 'red',
            'Satisfactory': 'grn',
        };
        return this.B(status, m[status] || 'grey');
    }

    KPI(icon, label, val, sub, link, kc) {
        return `
        <div class="chq-kpi" style="--chq-kc:${kc || 'var(--chq-pri)'}" onclick="${link ? `frappe.set_route('${link}')` : ''}">
            ${icon ? `<div class="chq-kpi-icon">${icon}</div>` : ''}
            <div class="chq-kpi-label">${label}</div>
            <div class="chq-kpi-value">${val}</div>
            <div class="chq-kpi-sub">${sub}</div>
        </div>`;
    }

    DC(id) {
        if (this.charts[id]) {
            try { this.charts[id].destroy(); } catch (e) {}
            delete this.charts[id];
        }
    }

    MC(id, cfg) {
        this.DC(id);
        const el = document.getElementById(id);
        if (el) this.charts[id] = new Chart(el, cfg);
    }

    colors() {
        return ['#0EA5E9', '#10B981', '#F59E0B', '#7C3AED', '#F43F5E', '#06B6D4', '#F97316', '#22C55E', '#EC4899', '#94A3B8'];
    }

    TBL(headers, rows, emptyMsg) {
        return `
        <div class="chq-table-wrap">
            <table class="chq-table">
                <thead><tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr></thead>
                <tbody>${rows.length ? rows.join('') : `<tr><td colspan="${headers.length}" class="chq-empty">${emptyMsg || 'No records found'}</td></tr>`}</tbody>
            </table>
        </div>`;
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW: OVERVIEW
    // ═══════════════════════════════════════════════════════════════════════════
    _renderOverview() {
        const sc = this.scores.domain_scores || {};
        const v3 = this.v3data;
        const overall = this.scores.overall_v3 || 0;

        const domainItems = [
            { key: 'corporate', icon: '🏢', label: 'Governance', score: sc.corporate, tab: 'corporate' },
            { key: 'contracts', icon: '📄', label: 'Contracts', score: sc.contracts, tab: 'contracts' },
            { key: 'ndpr', icon: '🔒', label: 'NDPR', score: sc.ndpr, tab: 'ndpr' },
            { key: 'aml', icon: '🕵️', label: 'AML & KYC', score: sc.aml, tab: 'aml' },
            { key: 'labour', icon: '👷', label: 'Labour', score: sc.labour, tab: 'labour' },
            { key: 'environmental', icon: '🌿', label: 'Environmental', score: sc.environmental, tab: 'environmental' },
            { key: 'industry', icon: '🏭', label: 'Regulatory', score: sc.industry, tab: 'industry' },
            { key: 'fraud', icon: '🚨', label: 'Integrity', score: sc.fraud, tab: 'fraud' },
            { key: 'training', icon: '🎓', label: 'Training', score: sc.training, tab: 'training' },
        ].map(d => {
            const s = d.score || 0;
            const col = s >= 80 ? 'var(--chq-grn)' : s >= 60 ? 'var(--chq-amb)' : 'var(--chq-red)';
            return `
            <div class="chq-domain-item" onclick="window.__chq3._switchTab('${d.tab}')">
                <div class="chq-di-icon">${d.icon}</div>
                <div class="chq-di-name">${d.label}</div>
                <div class="chq-di-score" style="color:${col}">${Math.round(s)}%</div>
                <div class="chq-di-bar"><div class="chq-di-bar-fill" style="width:${s}%;background:${col}"></div></div>
            </div>`;
        }).join('');

        const domainLabels = ['Governance', 'Contracts', 'NDPR', 'AML', 'Labour', 'Environmental', 'Regulatory', 'Integrity', 'Training'];
        const domainData = [sc.corporate, sc.contracts, sc.ndpr, sc.aml, sc.labour, sc.environmental, sc.industry, sc.fraud, sc.training].map(v => Math.round(v || 0));

        document.getElementById('chq-panel-overview').innerHTML = `
        <div class="chq-card">
            <div class="chq-card-head">
                <div class="chq-card-title">📊 Compliance Health — All 11 Domains</div>
                <div style="display:flex;align-items:center;gap:12px">
                    <div style="font-size:11px;color:var(--chq-tx3)">Overall GRC Score</div>
                    <div style="font-size:26px;font-weight:800;color:${overall>=80?'var(--chq-grn)':overall>=60?'var(--chq-amb)':'var(--chq-red)'}">${Math.round(overall)}%</div>
                </div>
            </div>
            <div class="chq-card-body">
                <div style="height:6px;background:var(--chq-brd);border-radius:10px;overflow:hidden;margin-bottom:18px">
                    <div style="height:100%;width:${overall}%;background:${overall>=80?'var(--chq-grn)':overall>=60?'var(--chq-amb)':'var(--chq-red)'};transition:width .8s"></div>
                </div>
                <div class="chq-domain-grid">${domainItems}</div>
            </div>
        </div>

        <div class="chq-kpis">
            ${this.KPI('💼', 'VAT Status', (this.data.tax||{}).VAT?.status||'—', '', '', (this.data.tax||{}).VAT?.status==='Fully Paid'?'var(--chq-grn)':'var(--chq-red)')}
            ${this.KPI('🎖', 'Expired Licenses', this.data.licenses?.expired||0, 'need renewal', '', 'var(--chq-red)')}
            ${this.KPI('⚠️', 'Open Incidents', this.data.incidents?.open||0, 'active issues', '', 'var(--chq-amb)')}
            ${this.KPI('🔒', 'Data Breaches', this.v3data.ndpr?.open_breaches||0, 'open', '', 'var(--chq-red)')}
            ${this.KPI('🎓', 'Training Complete', Math.round(this.v3data.training?.mandatory_pct||0)+'%', 'mandatory', '', this.v3data.training?.mandatory_pct>=80?'var(--chq-grn)':'var(--chq-amb)')}
            ${this.KPI('💰', 'Total Liability', this.F(this.data.total_liability||0), 'all obligations', '', 'var(--chq-pri)')}
        </div>

        <div class="chq-g2">
            <div class="chq-card">
                <div class="chq-card-head"><div class="chq-card-title">📊 Domain Scores Breakdown</div></div>
                <div class="chq-card-body" style="height:220px"><canvas id="chq-ch-domains"></canvas></div>
            </div>
            <div class="chq-card">
                <div class="chq-card-head">
                    <div class="chq-card-title">🚨 Active Incidents by Type</div>
                    <button class="chq-btn chq-btn-ghost chq-btn-sm" onclick="window.__chq3._switchTab('statutory')">View →</button>
                </div>
                <div class="chq-card-body" style="height:220px"><canvas id="chq-ch-incidents"></canvas></div>
            </div>
        </div>
        `;

        this.MC('chq-ch-domains', {
            type: 'bar',
            data: {
                labels: domainLabels,
                datasets: [{
                    data: domainData,
                    backgroundColor: this.colors(),
                    borderRadius: 6,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false }, ticks: { color: 'var(--chq-tx3)', font: { size: 9 } } },
                    y: { max: 100, ticks: { color: 'var(--chq-tx3)', font: { size: 9 }, callback: v => v + '%' }, grid: { color: 'rgba(148,163,184,.08)' } }
                }
            }
        });

        const byType = (this.data.incidents || {}).by_type || [];
        this.MC('chq-ch-incidents', {
            type: 'doughnut',
            data: {
                labels: byType.map(t => t.incident_type || 'Other'),
                datasets: [{ data: byType.map(t => t.cnt), backgroundColor: this.colors(), borderWidth: 0 }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '60%',
                plugins: {
                    legend: { display: true, position: 'right', labels: { color: 'var(--chq-tx3)', font: { size: 10 }, boxWidth: 10 } }
                }
            }
        });
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW: STATUTORY TAX
    // ═══════════════════════════════════════════════════════════════════════════
    _renderStatutory() {
        const tax = this.data.tax || {};
        const sta = this.data.statutory || {};
        const lic = this.data.licenses || {};
        const cal = this.data.calendar || {};

        const obCard = (ob, d) => {
            const liability = parseFloat(d?.liability || 0);
            const paid = parseFloat(d?.paid || 0);
            const pct = liability > 0 ? Math.min(100, Math.round(paid / liability * 100)) : 0;
            const col = d?.status === 'Fully Paid' ? 'var(--chq-grn)' :
                d?.status === 'Overdue' ? 'var(--chq-red)' :
                d?.status === 'Partially Paid' ? 'var(--chq-amb)' : 'var(--chq-tx3)';
            return `
            <div class="chq-kpi" onclick="frappe.set_route('List','Compliance Liability Ledger',{obligation_type:'${ob}'})">
                <div class="chq-kpi-label">${ob}</div>
                <div class="chq-kpi-value chq-mono">${this.F(liability)}</div>
                <div class="chq-kpi-sub">Paid: ${this.F(paid)} · Bal: ${this.F(liability-paid)}</div>
                <div style="height:4px;background:var(--chq-brd);border-radius:10px;overflow:hidden;margin:6px 0">
                    <div style="height:100%;width:${pct}%;background:${col};transition:width .7s"></div>
                </div>
                ${this.SB(d?.status||'Not Generated')}
            </div>`;
        };

        document.getElementById('chq-panel-statutory').innerHTML = `
        <div class="chq-g2">
            <div class="chq-card">
                <div class="chq-card-head">
                    <div class="chq-card-title">💼 Tax Obligations — ${this.fiscalMonth}</div>
                    <button class="chq-btn chq-btn-solid chq-btn-sm" onclick="window.__chq3._genLiabilities()">⚡ Generate</button>
                </div>
                <div class="chq-card-body">
                    <div class="chq-kpis" style="grid-template-columns:repeat(2,1fr)">
                        ${obCard('VAT', tax.VAT)}${obCard('WHT', tax.WHT)}
                        ${obCard('PAYE', tax.PAYE)}${obCard('CIT', tax.CIT)}
                    </div>
                </div>
            </div>
            <div class="chq-card">
                <div class="chq-card-head">
                    <div class="chq-card-title">📋 Statutory Obligations — ${this.fiscalMonth}</div>
                </div>
                <div class="chq-card-body">
                    <div class="chq-kpis" style="grid-template-columns:repeat(2,1fr)">
                        ${obCard('Pension', sta.Pension)}${obCard('NHF', sta.NHF)}
                        ${obCard('NSITF', sta.NSITF)}${obCard('ITF', sta.ITF)}
                    </div>
                </div>
            </div>
        </div>

        <div class="chq-g2">
            <div class="chq-card">
                <div class="chq-card-head">
                    <div class="chq-card-title">🎖 License Status</div>
                    <button class="chq-btn chq-btn-ghost chq-btn-sm" onclick="frappe.set_route('List','License Management')">All →</button>
                </div>
                <div class="chq-card-body">
                    <div style="display:flex;gap:16px;margin-bottom:14px">
                        ${[['✅','Valid',lic.valid||0,'var(--chq-grn)'],['⚠️','Expiring',lic.expiring||0,'var(--chq-amb)'],['🔴','Expired',lic.expired||0,'var(--chq-red)']].map(([i,l,n,c])=>`
                            <div style="text-align:center;flex:1;padding:12px;background:var(--chq-bg2);border-radius:12px">
                                <div style="font-size:20px">${i}</div>
                                <div style="font-size:20px;font-weight:800;color:${c}">${n}</div>
                                <div style="font-size:10px;color:var(--chq-tx3)">${l}</div>
                            </div>`).join('')}
                    </div>
                    ${(lic.expiring_list||[]).slice(0,5).map(l => `
                        <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--chq-brd);cursor:pointer" onclick="frappe.set_route('Form','License Management','${l.name}')">
                            <div><div style="font-size:12px;font-weight:600;color:var(--chq-tx1)">${l.license_name}</div>
                            <div style="font-size:10px;color:var(--chq-tx3)">${l.license_type}</div></div>
                            ${this.B(l.days_to_expiry+'d', l.days_to_expiry<=7?'red':l.days_to_expiry<=30?'amb':'sky')}
                        </div>`).join('') || '<div class="chq-empty">No expiring licenses</div>'}
                </div>
            </div>
            <div class="chq-card">
                <div class="chq-card-head">
                    <div class="chq-card-title">📅 Upcoming Obligations</div>
                </div>
                <div class="chq-card-body">
                    ${(cal.upcoming||[]).slice(0,8).map(l => `
                        <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--chq-brd)">
                            <div><div style="font-size:12px;font-weight:600;color:var(--chq-tx1)">${l.requirement_name||l.obligation_type}</div>
                            <div style="font-size:10px;color:var(--chq-tx3)">${l.fiscal_month} · Due ${l.due_date}</div></div>
                            ${this.SB(l.status)}
                        </div>`).join('') || '<div class="chq-empty">No upcoming obligations</div>'}
                </div>
            </div>
        </div>
        `;
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW: CORPORATE GOVERNANCE
    // ═══════════════════════════════════════════════════════════════════════════
    _renderCorporate() {
        const d = this.v3data.corporate || {};
        frappe.call({
            method: 'ecclesia.ecclesia.page.compliance_dashboard.compliance_dashboard.get_corporate_governance_tab',
            args: { company: this.company },
            callback: r => {
                const data = r.message || {};
                const regs = data.registers || [];
                const ress = data.pending_resolutions || [];

                document.getElementById('chq-panel-corporate').innerHTML = `
                <div class="chq-kpis">
                    ${this.KPI('🏢','Total Registers',d.total_registers||0,'fiscal years tracked','List/Corporate Compliance Register')}
                    ${this.KPI('🚨','Non-Compliant',d.non_compliant||0,'registers','','var(--chq-red)')}
                    ${this.KPI('📋','CAC Returns Overdue',d.annual_return_overdue||0,'immediate filing','','var(--chq-red)')}
                    ${this.KPI('📅','AGM Missed',d.agm_missed||0,'this fiscal year','','var(--chq-amb)')}
                    ${this.KPI('⚖️','CAC Filings Outstanding',d.cac_filings_outstanding||0,'from board resolutions','','var(--chq-amb)')}
                    ${this.KPI('📝','Resolutions Pending',d.resolutions_pending||0,'implementation','','var(--chq-sky)')}
                </div>

                <div class="chq-g21">
                    <div>
                        <div class="chq-card">
                            <div class="chq-card-head">
                                <div class="chq-card-title">🏢 Corporate Compliance Registers</div>
                                <button class="chq-btn chq-btn-solid chq-btn-sm" onclick="frappe.new_doc('Corporate Compliance Register')">+ New</button>
                            </div>
                            ${this.TBL(
                                ['Company / FY','RC Number','CAC Return','AGM','Status'],
                                regs.map(r => `<tr onclick="frappe.set_route('Form','Corporate Compliance Register','${r.name}')">
                                    <td><div style="font-weight:600;color:var(--chq-tx1)">${r.company}</div><div style="font-size:10px;color:var(--chq-tx3)">${r.fiscal_year}</div></td>
                                    <td class="chq-mono" style="font-size:10px">${r.rc_number||'—'}</td>
                                    <td>${this.SB(r.annual_return_status||'—')}</td>
                                    <td style="color:${r.agm_held_on_time?'var(--chq-grn)':'var(--chq-red)'}">${r.agm_held_on_time?'✅':'❌'}</td>
                                    <td>${this.SB(r.overall_status||'—')}</td>
                                </tr>`)
                            )}
                        </div>
                        <div class="chq-card">
                            <div class="chq-card-head">
                                <div class="chq-card-title">⚖️ Pending Board Resolutions</div>
                                <button class="chq-btn chq-btn-solid chq-btn-sm" onclick="frappe.new_doc('Board Resolution')">+ New</button>
                            </div>
                            ${this.TBL(
                                ['Resolution','Meeting','CAC Required','Status'],
                                ress.map(r => `<tr onclick="frappe.set_route('Form','Board Resolution','${r.name}')">
                                    <td style="font-weight:600;color:var(--chq-tx1)">${r.resolution_number||r.name}</td>
                                    <td style="font-size:10px">${r.meeting_type}<br><span style="color:var(--chq-tx3)">${r.meeting_date}</span></td>
                                    <td>${r.cac_filing_required?(r.cac_filed?this.B('Filed','grn'):this.B('OUTSTANDING','red')):this.B('N/A','grey')}</td>
                                    <td>${this.SB(r.implementation_status)}</td>
                                </tr>`)
                            )}
                        </div>
                    </div>
                    <div>
                        <div class="chq-card">
                            <div class="chq-card-head">
                                <div class="chq-card-title">📖 Statutory Registers</div>
                                <button class="chq-btn chq-btn-solid chq-btn-sm" onclick="frappe.new_doc('Statutory Register Entry')">+ Entry</button>
                            </div>
                            <div class="chq-card-body">
                                ${(data.register_entries||[]).map(e => `
                                <div class="chq-bar-row" onclick="frappe.set_route('List','Statutory Register Entry',{register_type:'${e.register_type}'})" style="cursor:pointer">
                                    <div class="chq-bar-label" style="font-size:10px">${e.register_type.replace('Register of ','')}</div>
                                    <div class="chq-bar"><div class="chq-bar-fill" style="width:${e.count>0?100:0}%;background:var(--chq-grn)"></div></div>
                                    <div class="chq-bar-value">${e.count}</div>
                                </div>`).join('') || '<div class="chq-empty">No register entries yet</div>'}
                            </div>
                        </div>
                    </div>
                </div>
                `;
            }
        });
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW: CONTRACTS
    // ═══════════════════════════════════════════════════════════════════════════
    _renderContracts() {
        const d = this.v3data.contracts || {};
        frappe.call({
            method: 'ecclesia.ecclesia.page.compliance_dashboard.compliance_dashboard.get_contracts_tab',
            args: { company: this.company },
            callback: r => {
                const data = r.message || {};
                const records = data.records || [];

                document.getElementById('chq-panel-contracts').innerHTML = `
                <div class="chq-kpis">
                    ${this.KPI('📄','Total Contracts',d.total||0,'monitored','List/Contract Compliance Record')}
                    ${this.KPI('✅','Compliant',d.compliant||0,'all obligations met','','var(--chq-grn)')}
                    ${this.KPI('⚠️','Minor Breach',d.minor_breach||0,'resolve soon','','var(--chq-amb)')}
                    ${this.KPI('🔴','Material Breach',d.material_breach||0,'legal review needed','','var(--chq-red)')}
                    ${this.KPI('🚨','Termination Risk',d.termination_risk||0,'urgent action','','var(--chq-red)')}
                    ${this.KPI('📊','Average SLA',Math.round(d.avg_sla||0)+'%','across all contracts','','var(--chq-sky)')}
                </div>

                <div class="chq-card">
                    <div class="chq-card-head">
                        <div class="chq-card-title">📄 All Contract Compliance Records</div>
                        <button class="chq-btn chq-btn-solid chq-btn-sm" onclick="frappe.new_doc('Contract Compliance Record')">+ New</button>
                    </div>
                    ${this.TBL(
                        ['Contract','Vendor','SLA %','Breaches','End Date','Status'],
                        records.slice(0,20).map(c => `<tr onclick="frappe.set_route('Form','Contract Compliance Record','${c.name}')">
                            <td style="font-weight:600;color:var(--chq-tx1)">${c.compliance_title||c.name}</td>
                            <td style="font-size:10px;color:var(--chq-tx2)">${c.vendor||'—'}</td>
                            <td class="chq-mono" style="color:${(c.sla_compliance_pct||0)>=95?'var(--chq-grn)':(c.sla_compliance_pct||0)>=80?'var(--chq-amb)':'var(--chq-red)'}">${Math.round(c.sla_compliance_pct||0)}%</td>
                            <td class="chq-mono" style="color:${(c.open_breaches||0)>0?'var(--chq-red)':'var(--chq-grn)'}">${c.open_breaches||0}</td>
                            <td class="chq-mono" style="font-size:10px">${c.contract_end||'—'}</td>
                            <td>${this.SB(c.compliance_status)}</td>
                        </tr>`)
                    )}
                </div>
                `;
            }
        });
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW: NDPR
    // ═══════════════════════════════════════════════════════════════════════════
    _renderNdpr() {
        const d = this.v3data.ndpr || {};
        frappe.call({
            method: 'ecclesia.ecclesia.page.compliance_dashboard.compliance_dashboard.get_ndpr_tab',
            args: { company: this.company },
            callback: r => {
                const data = r.message || {};
                const breaches = data.open_breaches_detail || [];

                document.getElementById('chq-panel-ndpr').innerHTML = `
                <div class="chq-kpis">
                    ${this.KPI('📋','Processing Records',d.processing_records||0,'active data processing','List/Data Processing Record')}
                    ${this.KPI('🔒','Sensitive Data Records',d.sensitive_data_records||0,'require DPIA','','var(--chq-amb)')}
                    ${this.KPI('🚫','DPIAs Missing',d.dpia_missing||0,'for sensitive processing','','var(--chq-red)')}
                    ${this.KPI('🇳🇬','NITDA Registered',d.nitda_registered||0,'out of '+d.processing_records,'','var(--chq-grn)')}
                    ${this.KPI('🚨','Open Breaches',d.open_breaches||0,'data breach incidents','','var(--chq-red)')}
                    ${this.KPI('⏰','Late NITDA Notifications',d.late_notifications||0,'72-hour rule breached','','var(--chq-red)')}
                </div>

                <div class="chq-card">
                    <div class="chq-card-head">
                        <div class="chq-card-title">🚨 Open Data Breaches</div>
                        <button class="chq-btn chq-btn-solid chq-btn-sm" onclick="frappe.new_doc('Data Breach Register')">+ Report Breach</button>
                    </div>
                    ${this.TBL(
                        ['Breach','Type','Severity','Subjects','NITDA Notified','Status'],
                        breaches.map(b => `<tr onclick="frappe.set_route('Form','Data Breach Register','${b.name}')">
                            <td style="font-weight:600;color:var(--chq-tx1)">${b.breach_title}</td>
                            <td style="font-size:10px;color:var(--chq-tx2)">${b.breach_type||'—'}</td>
                            <td>${this.SB(b.severity)}</td>
                            <td class="chq-mono">${b.data_subjects_affected||'?'}</td>
                            <td style="color:${b.nitda_notified?'var(--chq-grn)':'var(--chq-red)'}">${b.nitda_notified?'✅':'❌'}</td>
                            <td>${this.SB(b.status)}</td>
                        </tr>`),
                        'No open data breaches ✅'
                    )}
                </div>
                `;
            }
        });
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW: AML & KYC
    // ═══════════════════════════════════════════════════════════════════════════
    _renderAml() {
        const d = this.v3data.aml || {};
        frappe.call({
            method: 'ecclesia.ecclesia.page.compliance_dashboard.compliance_dashboard.get_aml_tab',
            args: { company: this.company },
            callback: r => {
                const data = r.message || {};
                const high = data.high_risk_parties || [];

                document.getElementById('chq-panel-aml').innerHTML = `
                <div class="chq-kpis">
                    ${this.KPI('🆔','Total KYC Records',d.total_kyc||0,'all parties','List/AML KYC Record')}
                    ${this.KPI('🔴','High / PEP Risk',d.high_risk||0,'require EDD','','var(--chq-red)')}
                    ${this.KPI('🏛️','PEP Parties',d.pep_count||0,'politically exposed','','var(--chq-pri)')}
                    ${this.KPI('⛔','Sanctions Matches',d.sanctions_match||0,'IMMEDIATE action','','var(--chq-red)')}
                    ${this.KPI('⏰','KYC Expiring 30d',d.kyc_expiring_30d||0,'need renewal','','var(--chq-amb)')}
                    ${this.KPI('📤','STRs Pending NFIU',d.strs_pending_nfiu||0,'not yet submitted','','var(--chq-amb)')}
                </div>
                ${d.sanctions_match>0 ? `
                    <div style="padding:12px 16px;background:var(--chq-red_x);border:2px solid var(--chq-red);border-radius:12px;margin-bottom:16px;font-size:13px;font-weight:700;color:var(--chq-red)">
                        ⛔ SANCTIONS MATCH DETECTED — Do NOT proceed with any transaction.
                    </div>` : ''}

                <div class="chq-card">
                    <div class="chq-card-head">
                        <div class="chq-card-title">🔴 High-Risk & PEP Parties</div>
                        <button class="chq-btn chq-btn-solid chq-btn-sm" onclick="frappe.new_doc('AML KYC Record')">+ New KYC</button>
                    </div>
                    ${this.TBL(
                        ['Party','Type','Risk Rating','KYC Level','KYC Expiry','PEP','Sanctioned'],
                        high.map(p => `<tr onclick="frappe.set_route('Form','AML KYC Record','${p.name}')">
                            <td style="font-weight:600;color:var(--chq-tx1)">${p.party_name_display}</td>
                            <td style="font-size:10px">${p.party_type}</td>
                            <td>${this.SB(p.risk_rating)}</td>
                            <td style="font-size:10px;color:var(--chq-tx2)">${(p.kyc_level||'').replace('Enhanced Due Diligence','EDD').replace('Basic Customer Due Diligence','CDD')}</td>
                            <td class="chq-mono" style="font-size:10px;color:${p.kyc_expiry_date&&frappe.datetime.get_diff(p.kyc_expiry_date,frappe.datetime.get_today())<30?'var(--chq-red)':'var(--chq-tx2)'}">${p.kyc_expiry_date||'—'}</td>
                            <td>${p.is_pep?this.B('PEP','pri'):'—'}</td>
                            <td>${p.sanctions_match?this.B('MATCH','red'):'—'}</td>
                        </tr>`),
                        'No high-risk parties ✅'
                    )}
                </div>
                `;
            }
        });
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW: LABOUR
    // ═══════════════════════════════════════════════════════════════════════════
    _renderLabour() {
        const d = this.v3data.labour || {};
        frappe.call({
            method: 'ecclesia.ecclesia.page.compliance_dashboard.compliance_dashboard.get_labour_tab',
            args: { company: this.company },
            callback: r => {
                const data = r.message || {};
                const permits = data.expiring_permits || [];

                document.getElementById('chq-panel-labour').innerHTML = `
                <div class="chq-kpis">
                    ${this.KPI('👷','Latest Status',d.latest_status||'No Data',d.latest_period||'—','','var(--chq-pri)')}
                    ${this.KPI('💰','Min Wage Compliant',d.wage_compliant===null?'—':d.wage_compliant?'✅ Yes':'❌ No','see tracker','','var(--chq-grn)')}
                    ${this.KPI('🏦','PenCom Registered',d.pencom_compliant===null?'—':d.pencom_compliant?'✅ All':'❌ Issues','employees','','var(--chq-pri)')}
                    ${this.KPI('🛂','Total Permits',d.total_permits||0,'expatriate permits','List/Expatriate Permit Register')}
                    ${this.KPI('🔴','Expired Permits',d.expired_permits||0,'immediate renewal','','var(--chq-red)')}
                    ${this.KPI('⚠️','Expiring Permits',d.expiring_permits||0,'within 90 days','','var(--chq-amb)')}
                </div>

                <div class="chq-card">
                    <div class="chq-card-head">
                        <div class="chq-card-title">🛂 Expiring Expatriate Permits (90 days)</div>
                        <button class="chq-btn chq-btn-solid chq-btn-sm" onclick="frappe.new_doc('Expatriate Permit Register')">+ New Permit</button>
                    </div>
                    ${this.TBL(
                        ['Permit','Employee','Type','Expiry','Days Left','Status'],
                        permits.map(p => `<tr onclick="frappe.set_route('Form','Expatriate Permit Register','${p.name}')">
                            <td style="font-weight:600;color:var(--chq-tx1)">${p.permit_title||p.name}</td>
                            <td style="font-size:10px">${p.employee||'—'}</td>
                            <td style="font-size:10px">${p.permit_type||'—'}</td>
                            <td class="chq-mono" style="font-size:10px">${p.expiry_date||'—'}</td>
                            <td class="chq-mono" style="font-weight:700;color:${(p.days_to_expiry||0)<=30?'var(--chq-red)':'var(--chq-amb)'}">${p.days_to_expiry!=null?p.days_to_expiry+'d':'—'}</td>
                            <td>${this.SB(p.status)}</td>
                        </tr>`),
                        'No permits expiring in 90 days ✅'
                    )}
                </div>
                `;
            }
        });
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW: ENVIRONMENTAL
    // ═══════════════════════════════════════════════════════════════════════════
    _renderEnvironmental() {
        const d = this.v3data.environmental || {};
        frappe.call({
            method: 'ecclesia.ecclesia.page.compliance_dashboard.compliance_dashboard.get_environmental_tab',
            args: { company: this.company },
            callback: r => {
                const data = r.message || {};
                const expiring = data.expiring_90_days || [];

                document.getElementById('chq-panel-environmental').innerHTML = `
                <div class="chq-kpis">
                    ${this.KPI('🌿','Total Permits',d.total||0,'environmental & HSE permits','List/Environmental Compliance Record')}
                    ${this.KPI('✅','Active',d.active||0,'valid permits','','var(--chq-grn)')}
                    ${this.KPI('⚠️','Expiring Soon',d.expiring_soon||0,'within alert period','','var(--chq-amb)')}
                    ${this.KPI('🔴','Expired',d.expired||0,'operating risk','','var(--chq-red)')}
                    ${this.KPI('📋','Actions Pending',d.pending_actions||0,'corrective actions','','var(--chq-amb)')}
                    ${this.KPI('🚨','Major Non-Compliance',d.major_non_compliance||0,'inspection findings','','var(--chq-red)')}
                </div>
                ${d.expired>0 ? `
                    <div style="padding:12px 16px;background:var(--chq-red_x);border:2px solid var(--chq-red);border-radius:12px;margin-bottom:16px;font-size:13px;font-weight:700;color:var(--chq-red)">
                        🚨 ${d.expired} environmental permit${d.expired>1?'s have':' has'} EXPIRED.
                    </div>` : ''}

                <div class="chq-card">
                    <div class="chq-card-head">
                        <div class="chq-card-title">🌿 Permits Expiring within 90 Days</div>
                        <button class="chq-btn chq-btn-solid chq-btn-sm" onclick="frappe.new_doc('Environmental Compliance Record')">+ New</button>
                    </div>
                    ${this.TBL(
                        ['Permit','Type','Authority','Expiry','Days Left','Status'],
                        expiring.map(e => `<tr onclick="frappe.set_route('Form','Environmental Compliance Record','${e.name}')">
                            <td style="font-weight:600;color:var(--chq-tx1)">${e.permit_title}</td>
                            <td style="font-size:10px;color:var(--chq-tx2)">${(e.permit_type||'').split('(')[0].trim()}</td>
                            <td style="font-size:10px">${e.issuing_authority||'—'}</td>
                            <td class="chq-mono" style="font-size:10px">${e.expiry_date||'—'}</td>
                            <td class="chq-mono" style="font-weight:700;color:${(e.days_to_expiry||0)<=30?'var(--chq-red)':'var(--chq-amb)'}">${e.days_to_expiry!=null?e.days_to_expiry+'d':'—'}</td>
                            <td>${this.SB(e.status)}</td>
                        </tr>`),
                        'No permits expiring in 90 days ✅'
                    )}
                </div>
                `;
            }
        });
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW: INDUSTRY REGULATORY
    // ═══════════════════════════════════════════════════════════════════════════
    _renderIndustry() {
        const d = this.v3data.industry || {};
        frappe.call({
            method: 'ecclesia.ecclesia.page.compliance_dashboard.compliance_dashboard.get_industry_tab',
            args: { company: this.company },
            callback: r => {
                const data = r.message || {};
                const overdue = data.overdue_returns || [];

                document.getElementById('chq-panel-industry').innerHTML = `
                <div class="chq-kpis">
                    ${this.KPI('🏭','Total Returns',d.total||0,'regulatory returns','List/Regulatory Return')}
                    ${this.KPI('🔴','Overdue',d.overdue||0,'immediate action','','var(--chq-red)')}
                    ${this.KPI('⚠️','Late Submissions',d.late||0,'with penalty','','var(--chq-amb)')}
                    ${this.KPI('⏳','Pending',d.pending||0,'not yet submitted','','var(--chq-sky)')}
                    ${this.KPI('✅','Submitted',d.submitted||0,'on time','','var(--chq-grn)')}
                    ${this.KPI('💰','Total Penalties',this.F(d.total_penalty||0),'incurred','','var(--chq-red)')}
                </div>

                <div class="chq-card">
                    <div class="chq-card-head">
                        <div class="chq-card-title">🏭 Overdue & Pending Regulatory Returns</div>
                        <button class="chq-btn chq-btn-solid chq-btn-sm" onclick="frappe.new_doc('Regulatory Return')">+ New Return</button>
                    </div>
                    ${this.TBL(
                        ['Return','Authority','Period','Due Date','Late','Penalty Risk','Status'],
                        overdue.map(ret => `<tr onclick="frappe.set_route('Form','Regulatory Return','${ret.name}')">
                            <td style="font-weight:600;color:var(--chq-tx1)">${ret.return_title||ret.name}</td>
                            <td style="font-size:10px">${ret.authority||'—'}</td>
                            <td style="font-size:10px;color:var(--chq-tx3)">${ret.period_covered||'—'}</td>
                            <td class="chq-mono" style="font-size:10px;color:var(--chq-red)">${ret.due_date||'—'}</td>
                            <td>${ret.late_flag?this.B('LATE','red'):'—'}</td>
                            <td class="chq-mono" style="color:var(--chq-red)">${ret.penalty_for_non_filing?this.F(ret.penalty_for_non_filing):'—'}</td>
                            <td>${this.SB(ret.status)}</td>
                        </tr>`),
                        'No overdue returns ✅'
                    )}
                </div>
                `;
            }
        });
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW: FRAUD / INTEGRITY
    // ═══════════════════════════════════════════════════════════════════════════
    _renderFraud() {
        const d = this.v3data.fraud || {};
        frappe.call({
            method: 'ecclesia.ecclesia.page.compliance_dashboard.compliance_dashboard.get_fraud_tab',
            args: { company: this.company },
            callback: r => {
                const data = r.message || {};
                const rpts = data.open_reports || [];

                document.getElementById('chq-panel-fraud').innerHTML = `
                <div class="chq-kpis">
                    ${this.KPI('🔒','Whistleblower Reports',d.total_wb_reports||0,'total received','List/Whistleblower Report')}
                    ${this.KPI('🔍','Under Investigation',d.under_investigation||0,'active investigations','','var(--chq-amb)')}
                    ${this.KPI('📋','Escalated',d.escalated||0,'to board','','var(--chq-red)')}
                    ${this.KPI('✅','Substantiated',d.substantiated||0,'action taken','','var(--chq-grn)')}
                    ${this.KPI('📝','COI Declarations',d.total_coi||0,'total','List/Conflict of Interest Declaration')}
                    ${this.KPI('⚠️','COI Pending Review',d.coi_pending_review||0,'awaiting acknowledgement','','var(--chq-amb)')}
                </div>

                <div class="chq-card">
                    <div class="chq-card-head">
                        <div class="chq-card-title">🔒 Open Whistleblower Reports</div>
                        <button class="chq-btn chq-btn-solid chq-btn-sm" onclick="frappe.new_doc('Whistleblower Report')">+ Report</button>
                    </div>
                    ${this.TBL(
                        ['Code','Date','Channel','Category','Severity','Status'],
                        rpts.map(rep => `<tr onclick="frappe.set_route('Form','Whistleblower Report','${rep.name}')">
                            <td class="chq-mono" style="font-weight:700;color:var(--chq-pri)">${rep.report_code||rep.name}</td>
                            <td class="chq-mono" style="font-size:10px">${rep.received_date||'—'}</td>
                            <td style="font-size:10px">${rep.channel||'—'}</td>
                            <td style="font-size:10px">${rep.report_category||'—'}</td>
                            <td>${this.SB(rep.severity)}</td>
                            <td>${this.SB(rep.status)}</td>
                        </tr>`),
                        'No open reports ✅'
                    )}
                </div>
                `;
            }
        });
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW: TRAINING
    // ═══════════════════════════════════════════════════════════════════════════
    _renderTraining() {
        const d = this.v3data.training || {};
        frappe.call({
            method: 'ecclesia.ecclesia.page.compliance_dashboard.compliance_dashboard.get_training_tab',
            args: { company: this.company },
            callback: r => {
                const data = r.message || {};
                const byCat = data.by_category || [];

                document.getElementById('chq-panel-training').innerHTML = `
                <div class="chq-kpis">
                    ${this.KPI('🎓','Total Training Records',d.total_records||0,'all employees','List/Compliance Training Record')}
                    ${this.KPI('📊','Mandatory Completion',Math.round(d.mandatory_pct||0)+'%',d.mandatory_completed+' / '+d.mandatory_total,'','var(--chq-grn)')}
                    ${this.KPI('❌','Failed',d.failed||0,'need retraining','','var(--chq-red)')}
                    ${this.KPI('👥','Employees Trained',d.unique_employees||0,'unique employees','','var(--chq-sky)')}
                    ${this.KPI('📅','Upcoming Sessions',d.upcoming_sessions||0,'planned / scheduled','List/Compliance Training Calendar')}
                    ${this.KPI('⚠️','Below Target',d.below_target||0,'calendars not on track','','var(--chq-amb)')}
                </div>

                <div class="chq-card">
                    <div class="chq-card-head">
                        <div class="chq-card-title">📊 Mandatory Training Completion by Category</div>
                        <button class="chq-btn chq-btn-solid chq-btn-sm" onclick="frappe.new_doc('Compliance Training Calendar')">+ Schedule</button>
                    </div>
                    <div class="chq-card-body">
                        ${byCat.map(cat => {
                            const pct = cat.mandatory > 0 ? Math.round(cat.completed / cat.mandatory * 100) : 100;
                            const col = pct >= 80 ? 'var(--chq-grn)' : pct >= 60 ? 'var(--chq-amb)' : 'var(--chq-red)';
                            return `
                            <div class="chq-bar-row" onclick="frappe.set_route('List','Compliance Training Record',{training_category:'${cat.training_category}'})" style="cursor:pointer">
                                <div class="chq-bar-label">${cat.training_category}</div>
                                <div class="chq-bar"><div class="chq-bar-fill" style="width:${pct}%;background:${col}"></div></div>
                                <div class="chq-bar-value" style="color:${col}">${pct}%</div>
                                <div style="font-size:9px;color:var(--chq-tx3);margin-left:4px">${cat.completed}/${cat.mandatory}</div>
                                ${cat.failed>0 ? `<div style="font-size:9px;color:var(--chq-red);margin-left:4px">${cat.failed}❌</div>` : ''}
                            </div>`;
                        }).join('') || '<div class="chq-empty">No training records yet</div>'}
                    </div>
                </div>
                `;
            }
        });
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW: AI ANALYSIS
    // ═══════════════════════════════════════════════════════════════════════════
    _renderAI() {
        const sc = this.scores;
        const ds = sc.domain_scores || {};
        const overall = sc.overall_v3 || 0;

        const domainBars = Object.entries(ds).map(([k, v]) => {
            const icons = { corporate: '🏢', contracts: '📄', ndpr: '🔒', aml: '🕵️', labour: '👷', environmental: '🌿', industry: '🏭', fraud: '🚨', training: '🎓' };
            const labels = { corporate: 'Governance', contracts: 'Contracts', ndpr: 'NDPR', aml: 'AML', labour: 'Labour', environmental: 'Environmental', industry: 'Regulatory', fraud: 'Integrity', training: 'Training' };
            const score = Math.round(v || 0);
            const col = score >= 80 ? 'var(--chq-grn)' : score >= 60 ? 'var(--chq-amb)' : 'var(--chq-red)';
            return `
            <div class="chq-bar-row">
                <div class="chq-bar-label">${icons[k]||''} ${labels[k]||k}</div>
                <div class="chq-bar"><div class="chq-bar-fill" style="width:${score}%;background:${col}"></div></div>
                <div class="chq-bar-value" style="color:${col}">${score}%</div>
            </div>`;
        }).join('');

        document.getElementById('chq-panel-ai').innerHTML = `
        <div class="chq-g2">
            <div class="chq-card">
                <div class="chq-card-head">
                    <div class="chq-card-title">📊 GRC Score Breakdown — All 11 Domains</div>
                </div>
                <div class="chq-card-body">
                    <div style="display:flex;align-items:center;gap:16px;margin-bottom:20px">
                        <div style="width:80px;height:80px;border-radius:50%;border:6px solid ${overall>=80?'var(--chq-grn)':overall>=60?'var(--chq-amb)':'var(--chq-red)'};display:flex;flex-direction:column;align-items:center;justify-content:center;flex-shrink:0">
                            <div style="font-size:24px;font-weight:800;color:${overall>=80?'var(--chq-grn)':overall>=60?'var(--chq-amb)':'var(--chq-red)'}">${Math.round(overall)}</div>
                            <div style="font-size:9px;color:var(--chq-tx3)">/ 100</div>
                        </div>
                        <div style="flex:1">
                            <div style="height:10px;background:var(--chq-brd);border-radius:10px;overflow:hidden;margin-bottom:8px">
                                <div style="height:100%;width:${overall}%;background:${overall>=80?'var(--chq-grn)':overall>=60?'var(--chq-amb)':'var(--chq-red)'};transition:width .8s"></div>
                            </div>
                            <div style="font-size:11px;color:var(--chq-tx3)">Weighted GRC score across all 11 compliance domains</div>
                        </div>
                    </div>
                    ${domainBars}
                </div>
            </div>

            <div class="chq-card">
                <div class="chq-card-head">
                    <div class="chq-card-title">🤖 AI Compliance Analyst</div>
                    <span id="chq-ai-status" style="font-size:10px;color:var(--chq-tx3)">Ready</span>
                </div>
                <div class="chq-card-body">
                    <div style="display:flex;flex-direction:column;gap:8px;margin-bottom:16px">
                        <button class="chq-btn chq-btn-solid" id="chq-ai-btn" onclick="window.__chq3._runAI()" style="justify-content:center">✨ Run Full AI GRC Analysis</button>
                        <button class="chq-btn chq-btn-ghost" onclick="window.__chq3._genLiabilities()" style="justify-content:center">⚡ Generate Liabilities</button>
                        <button class="chq-btn chq-btn-ghost" onclick="window.__chq3._reconcile()" style="justify-content:center">🔁 Reconcile CLL</button>
                    </div>
                    <div id="chq-ai-out">
                        <div style="padding:16px;background:var(--chq-bg2);border-radius:12px;font-size:12px;color:var(--chq-tx2);line-height:1.6">
                            Click <b>Run Full AI GRC Analysis</b> to send live data from all 11 compliance domains to the AI API for risk assessment.
                        </div>
                    </div>
                </div>
            </div>
        </div>
        `;
    }

    async _runAI() {
        const btn = document.getElementById('chq-ai-btn');
        const out = document.getElementById('chq-ai-out');
        const stat = document.getElementById('chq-ai-status');

        if (btn) btn.textContent = '⟳ Analysing…';
        if (stat) stat.textContent = 'Calling AI…';
        if (out) {
            out.innerHTML = `
            <div style="text-align:center;padding:24px;color:var(--chq-tx3)">
                <span class="chq-spin" style="font-size:28px">⟳</span>
                <div style="margin-top:10px;font-size:12px">Sending all domain data for analysis…</div>
            </div>`;
        }

        try {
            const r = await frappe.call({
                method: 'ecclesia.ecclesia.page.compliance_dashboard.compliance_dashboard.get_ai_compliance_analysis',
                args: { company: this.company, fiscal_month: this.fiscalMonth }
            });

            if (r.message?.success) {
                let parsed = {};
                try {
                    const raw = r.message.analysis?.response || r.message.analysis || '';
                    const match = (typeof raw === 'string' ? raw : JSON.stringify(raw)).match(/\{[\s\S]*\}/);
                    if (match) parsed = JSON.parse(match[0]);
                } catch (e) {
                    parsed = { summary: String(r.message.analysis || '').substring(0, 600) };
                }

                const riskCol = { Critical: 'var(--chq-red)', High: 'var(--chq-amb)', Medium: 'var(--chq-sky)', Low: 'var(--chq-grn)' }[parsed.risk_level] || 'var(--chq-tx2)';
                const actsHTML = (parsed.actions || []).map((a, i) => `
                    <div style="display:flex;align-items:flex-start;gap:10px;padding:10px 12px;background:var(--chq-bg2);border-radius:10px;margin-bottom:8px">
                        <div style="background:${riskCol};color:#fff;font-size:10px;font-weight:800;width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0">${i+1}</div>
                        <div>
                            <div style="font-size:12px;font-weight:700;color:var(--chq-tx1)">${a.action||''}</div>
                            <div style="font-size:10px;color:var(--chq-tx3);margin-top:2px">Deadline: ${a.deadline||'—'} · Authority: ${a.authority||'—'}</div>
                        </div>
                    </div>`).join('');

                if (out) {
                    out.innerHTML = `
                    <div style="padding:14px;background:${riskCol==='var(--chq-red)'?'var(--chq-red_x)':'var(--chq-pri_x)'};border-left:4px solid ${riskCol};border-radius:10px;margin-bottom:14px">
                        <div style="font-size:14px;font-weight:700;color:var(--chq-tx1)">${parsed.risk_level ? `[${parsed.risk_level} Risk] ` : ''}${parsed.summary || 'AI analysis complete'}</div>
                        ${parsed.penalty_exposure ? `<div style="font-size:12px;color:var(--chq-red);margin-top:4px;font-weight:700">Penalty exposure: ${parsed.penalty_exposure}</div>` : ''}
                    </div>
                    ${actsHTML ? `<div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--chq-tx3);margin-bottom:8px">Priority Actions</div>${actsHTML}` : ''}
                    ${parsed.strategic_recommendation ? `
                        <div style="padding:12px;background:var(--chq-grn_x);border-radius:10px;font-size:12px;color:var(--chq-tx1);border-left:3px solid var(--chq-grn)">
                            <b>Strategic Recommendation:</b> ${parsed.strategic_recommendation}
                        </div>` : ''}
                    <div style="font-size:10px;color:var(--chq-tx3);margin-top:10px">Analysis completed at ${new Date().toLocaleTimeString('en-NG', { hour12: true })}</div>
                    `;
                }
                if (stat) stat.textContent = 'Done';
            } else {
                if (out) {
                    out.innerHTML = `
                    <div style="padding:14px;background:var(--chq-red_x);border-radius:10px;font-size:12px;color:var(--chq-red)">
                        AI analysis failed: ${r.message?.error || 'Unknown error'}
                    </div>`;
                }
            }
        } catch (e) {
            if (out) {
                out.innerHTML = `
                <div style="padding:14px;background:var(--chq-red_x);border-radius:10px;font-size:12px;color:var(--chq-red)">
                    Error: ${e.message}
                </div>`;
            }
        }

        if (btn) btn.textContent = '✨ Run Full AI GRC Analysis';
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW: CALENDAR
    // ═══════════════════════════════════════════════════════════════════════════
    _renderCalendar() {
        const cal = this.data.calendar || {};
        const entries = cal.entries || [];

        document.getElementById('chq-panel-calendar').innerHTML = `
        <div class="chq-card">
            <div class="chq-card-head">
                <div class="chq-card-title">📅 Compliance Calendar — ${this.fiscalMonth}</div>
                <div style="display:flex;gap:8px">
                    <button class="chq-btn chq-btn-ghost chq-btn-sm" onclick="frappe.new_doc('Compliance Calendar')">+ New Calendar</button>
                </div>
            </div>
            <div class="chq-card-body">
                ${this.TBL(
                    ['Obligation Type','Domain','Period','Due Date','Status','Assigned To'],
                    entries.map(e => `
                        <tr onclick="frappe.set_route('Form','Compliance Calendar Line','${e.name}')">
                            <td style="font-weight:600;color:var(--chq-tx1)">${e.obligation_type||e.compliance_rule}</td>
                            <td style="font-size:10px;color:var(--chq-tx2)">${e.compliance_domain||'—'}</td>
                            <td style="font-size:10px">${e.period_label||'—'}</td>
                            <td class="chq-mono" style="font-size:10px;color:${new Date(e.due_date) < new Date() ? 'var(--chq-red)' : 'var(--chq-tx2)'}">${e.due_date}</td>
                            <td>${this.SB(e.status)}</td>
                            <td style="font-size:10px">${e.assigned_to||'—'}</td>
                        </tr>
                    `),
                    'No calendar entries for this period'
                )}
            </div>
        </div>
        `;
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW: REPORTS (with Excel Export)
    // ═══════════════════════════════════════════════════════════════════════════
    _renderReports() {
        const sc = this.scores;
        const overall = sc.overall_v3 || 0;
        const v3 = this.v3data;
        const tax = this.data.tax || {};
        const lic = this.data.licenses || {};

        document.getElementById('chq-panel-reports').innerHTML = `
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px">
            <div>
                <h3 style="font-size:18px;font-weight:800;color:var(--chq-tx1);margin:0 0 4px">📊 Executive Reports</h3>
                <div style="font-size:12px;color:var(--chq-tx3)">Export comprehensive compliance reports for stakeholders</div>
            </div>
            <div class="chq-btns">
                <button class="chq-btn chq-btn-solid" onclick="window.__chq3._exportExcel()">
                    <i class="fa-solid fa-file-excel"></i> Export Excel
                </button>
                <button class="chq-btn chq-btn-ghost" onclick="window.__chq3._exportReport('pdf')">
                    <i class="fa-solid fa-file-pdf"></i> Export PDF
                </button>
                <button class="chq-btn chq-btn-ghost" onclick="window.__chq3._exportReport('csv')">
                    <i class="fa-solid fa-file-csv"></i> Export CSV
                </button>
            </div>
        </div>

        <div class="chq-g2">
            <div class="chq-report-card" style="border-color:var(--chq-pri)">
                <h4>🏛️ Compliance Health Summary</h4>
                <p>
                    Overall compliance score: <strong style="color:${overall>=80?'var(--chq-grn)':overall>=60?'var(--chq-amb)':'var(--chq-red)'}">${Math.round(overall)}%</strong>.
                    ${overall>=80 ? 'Excellent compliance posture across all domains.' :
                      overall>=60 ? 'Good compliance posture with some areas requiring attention.' :
                      'Compliance risks identified — immediate action recommended.'}
                    ${v3.corporate?.non_compliant||0} governance issues,
                    ${v3.ndpr?.open_breaches||0} data breaches,
                    ${lic.expired||0} expired licenses.
                </p>
            </div>

            <div class="chq-report-card" style="border-color:var(--chq-amb)">
                <h4>⚠️ Risk Exposure</h4>
                <p>
                    ${this.F(this.data.total_liability||0)} total liability outstanding.
                    ${v3.industry?.overdue||0} regulatory returns overdue,
                    ${v3.environmental?.expired||0} environmental permits expired,
                    ${v3.aml?.sanctions_match||0} sanctions matches detected.
                    ${v3.fraud?.under_investigation||0} whistleblower reports under investigation.
                </p>
            </div>
        </div>

        <div class="chq-card">
            <div class="chq-card-head">
                <div class="chq-card-title">📋 Domain Score Report</div>
            </div>
            <div class="chq-card-body">
                <div style="height:260px;position:relative"><canvas id="chq-ch-report"></canvas></div>
            </div>
        </div>

        <div class="chq-card">
            <div class="chq-card-head">
                <div class="chq-card-title">📋 Detailed Domain Breakdown</div>
            </div>
            <div class="chq-card-body">
                ${this.TBL(
                    ['Domain','Score','Status','Issues'],
                    Object.entries(sc.domain_scores||{}).map(([k,v]) => {
                        const labels = { corporate:'Governance', contracts:'Contracts', ndpr:'NDPR', aml:'AML', labour:'Labour', environmental:'Environmental', industry:'Regulatory', fraud:'Integrity', training:'Training' };
                        const icons = { corporate:'🏢', contracts:'📄', ndpr:'🔒', aml:'🕵️', labour:'👷', environmental:'🌿', industry:'🏭', fraud:'🚨', training:'🎓' };
                        const score = Math.round(v||0);
                        const col = score>=80?'var(--chq-grn)':score>=60?'var(--chq-amb)':'var(--chq-red)';
                        const issues = {
                            corporate: v3.corporate?.non_compliant||0,
                            contracts: v3.contracts?.material_breach||0,
                            ndpr: v3.ndpr?.open_breaches||0,
                            aml: v3.aml?.high_risk||0,
                            labour: v3.labour?.expired_permits||0,
                            environmental: v3.environmental?.expired||0,
                            industry: v3.industry?.overdue||0,
                            fraud: v3.fraud?.under_investigation||0,
                            training: Math.max(0,100-(v3.training?.mandatory_pct||100))>20?1:0,
                        };
                        return `
                        <tr>
                            <td style="font-weight:600;color:var(--chq-tx1)">${icons[k]||''} ${labels[k]||k}</td>
                            <td style="font-weight:700;color:${col}">${score}%</td>
                            <td>${this.SB(score>=80?'Compliant':score>=60?'Minor Issues':'Major Issues')}</td>
                            <td style="color:${issues[k]>0?'var(--chq-red)':'var(--chq-grn)'}">${issues[k]||0}</td>
                        </tr>`;
                    })
                )}
            </div>
        </div>
        `;

        setTimeout(() => {
            const ds = sc.domain_scores || {};
            const labels = ['Governance', 'Contracts', 'NDPR', 'AML', 'Labour', 'Environmental', 'Regulatory', 'Integrity', 'Training'];
            const data = [ds.corporate, ds.contracts, ds.ndpr, ds.aml, ds.labour, ds.environmental, ds.industry, ds.fraud, ds.training].map(v => Math.round(v || 0));

            this.MC('chq-ch-report', {
                type: 'radar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Compliance Score',
                        data: data,
                        backgroundColor: 'rgba(14,165,233,.15)',
                        borderColor: '#0EA5E9',
                        borderWidth: 2,
                        pointBackgroundColor: '#0EA5E9',
                        pointRadius: 5,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { labels: { color: 'var(--chq-tx2)', font: { size: 10 } } }
                    },
                    scales: {
                        r: {
                            grid: { color: 'rgba(148,163,184,.1)' },
                            ticks: { color: 'var(--chq-tx3)', font: { size: 9 }, backdropColor: 'transparent' },
                            pointLabels: { color: 'var(--chq-tx2)', font: { size: 10 } },
                            min: 0,
                            max: 100,
                        }
                    }
                }
            });
        }, 100);
    }

    // ─── EXPORT EXCEL ─────────────────────────────────────────────────────────
    _exportExcel() {
        frappe.call({
            method: 'ecclesia.ecclesia.page.compliance_dashboard.compliance_dashboard.export_compliance_report',
            args: {
                company: this.company,
                fiscal_month: this.fiscalMonth,
                format: 'xlsx'
            },
            callback: (r) => {
                if (r.message && r.message.success) {
                    // Download the file
                    const link = document.createElement('a');
                    link.href = 'data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,' + r.message.file_data;
                    link.download = r.message.file_name;
                    link.click();
                    frappe.show_alert({
                        message: '📊 Excel report downloaded successfully!',
                        indicator: 'green'
                    });
                } else {
                    frappe.show_alert({
                        message: '❌ Failed to generate report: ' + (r.message?.error || 'Unknown error'),
                        indicator: 'red'
                    });
                }
            },
            freeze: true,
            freeze_message: '📊 Generating Excel report...'
        });
    }

    _exportReport(format) {
        const sc = this.scores;
        const v3 = this.v3data;
        const overall = sc.overall_v3 || 0;

        const reportData = {
            company: this.company,
            period: this.fiscalMonth,
            generated: new Date().toISOString(),
            overall_score: overall,
            domain_scores: sc.domain_scores || {},
            summary: {
                total_liability: this.data.total_liability || 0,
                expired_licenses: (this.data.licenses||{}).expired || 0,
                open_breaches: v3.ndpr?.open_breaches || 0,
                overdue_returns: v3.industry?.overdue || 0,
                expired_permits: v3.environmental?.expired || 0,
                sanctions_matches: v3.aml?.sanctions_match || 0,
            }
        };

        if (format === 'pdf') {
            const html = `
            <html><head><style>
                body { font-family: 'Inter', system-ui, sans-serif; padding: 40px; max-width: 800px; margin: 0 auto; }
                h1 { font-size: 24px; font-weight: 800; }
                .score { font-size: 48px; font-weight: 800; color: ${overall>=80?'#10B981':overall>=60?'#F59E0B':'#EF4444'}; }
                .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 20px 0; }
                .card { border: 1px solid #E2E8F0; border-radius: 12px; padding: 16px; }
                .card h4 { margin: 0 0 4px; font-size: 12px; color: #64748B; text-transform: uppercase; }
                .card .val { font-size: 24px; font-weight: 700; }
                table { width: 100%; border-collapse: collapse; margin: 16px 0; }
                th { text-align: left; padding: 8px 12px; background: #F8FAFC; font-size: 11px; text-transform: uppercase; color: #64748B; }
                td { padding: 8px 12px; border-bottom: 1px solid #E2E8F0; }
            </style></head><body>
                <h1>🏛️ ComplianceHQ Executive Report</h1>
                <p>Company: ${this.company} · Period: ${this.fiscalMonth} · Generated: ${new Date().toLocaleString()}</p>

                <div style="text-align:center;padding:20px;background:#F8FAFC;border-radius:12px;margin:20px 0">
                    <div class="score">${Math.round(overall)}%</div>
                    <div style="font-size:14px;color:#64748B">Overall GRC Score</div>
                </div>

                <div class="grid">
                    <div class="card"><h4>Total Liability</h4><div class="val">${this.F(reportData.summary.total_liability)}</div></div>
                    <div class="card"><h4>Expired Licenses</h4><div class="val">${reportData.summary.expired_licenses}</div></div>
                    <div class="card"><h4>Open Data Breaches</h4><div class="val">${reportData.summary.open_breaches}</div></div>
                    <div class="card"><h4>Sanctions Matches</h4><div class="val">${reportData.summary.sanctions_matches}</div></div>
                </div>

                <h3>Domain Scores</h3>
                <table>
                    <thead><tr><th>Domain</th><th>Score</th><th>Status</th></tr></thead>
                    <tbody>
                        ${Object.entries(reportData.domain_scores).map(([k,v]) => {
                            const labels = { corporate:'Governance', contracts:'Contracts', ndpr:'NDPR', aml:'AML', labour:'Labour', environmental:'Environmental', industry:'Regulatory', fraud:'Integrity', training:'Training' };
                            const score = Math.round(v||0);
                            const status = score>=80?'Compliant':score>=60?'Minor Issues':'Major Issues';
                            return `<tr><td>${labels[k]||k}</td><td>${score}%</td><td>${status}</td></tr>`;
                        }).join('')}
                    </tbody>
                </table>

                <p style="font-size:12px;color:#94A3B8;margin-top:40px">Generated by ComplianceHQ v3 · ${new Date().toISOString()}</p>
            </body></html>`;

            const win = window.open('', '_blank');
            if (win) {
                win.document.write(html);
                win.document.close();
                win.print();
            }
        } else {
            // CSV export
            let csv = 'Domain,Score,Status\n';
            Object.entries(reportData.domain_scores).forEach(([k, v]) => {
                const labels = { corporate:'Governance', contracts:'Contracts', ndpr:'NDPR', aml:'AML', labour:'Labour', environmental:'Environmental', industry:'Regulatory', fraud:'Integrity', training:'Training' };
                const score = Math.round(v||0);
                const status = score>=80?'Compliant':score>=60?'Minor Issues':'Major Issues';
                csv += `${labels[k]||k},${score}%,${status}\n`;
            });

            const blob = new Blob([csv], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `compliance_report_${this.fiscalMonth}.csv`;
            a.click();
            URL.revokeObjectURL(url);
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  UTILITY ACTIONS
    // ═══════════════════════════════════════════════════════════════════════════
    _genLiabilities() {
        frappe.call({
            method: 'ecclesia.ecclesia.page.compliance_dashboard.compliance_dashboard.run_liability_generation_now',
            args: { company: this.company, fiscal_month: this.fiscalMonth },
            freeze: true,
            freeze_message: 'Generating liabilities…',
            callback: () => {
                frappe.show_alert({ message: 'Liability generation complete ✅', indicator: 'green' });
                this.refresh(true);
            }
        });
    }

    _reconcile() {
        frappe.call({
            method: 'ecclesia.ecclesia.page.compliance_dashboard.compliance_dashboard.run_reconciliation_now',
            args: { company: this.company },
            freeze: true,
            freeze_message: 'Reconciling CLL entries…',
            callback: r => {
                frappe.show_alert({
                    message: `Reconciled ${(r.message||{}).reconciled||0} CLL entries ✅`,
                    indicator: 'green'
                });
                this.refresh(true);
            }
        });
    }

    // ─── POST DETAIL / INLINE EDIT ─────────────────────────────────────────
    openPostDetail(name) {
        const post = this.state.posts?.find(p => p.name === name);
        if (post) {
            const d = new frappe.ui.Dialog({
                title: `📝 ${post.post_title}`,
                size: 'large',
                fields: [{
                    fieldtype: 'HTML',
                    fieldname: 'detail_html',
                    options: `
                    <div style="font-family:'Inter',system-ui,sans-serif">
                        <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:12px">
                            <span class="chq-badge ${post.status==='Published'?'chq-badge-grn':post.status==='Draft'?'chq-badge-grey':post.status==='Pending Approval'?'chq-badge-amb':'chq-badge-pri'}">
                                ${post.status}
                            </span>
                            <span style="font-size:12px;color:var(--chq-tx3)">${post.content_type||'—'}</span>
                            <span style="font-size:12px;color:var(--chq-tx3)">${post.global_schedule||'No schedule'}</span>
                        </div>
                        <div style="background:var(--chq-bg2);border-radius:10px;padding:14px;margin-bottom:12px">
                            <div style="font-size:12px;color:var(--chq-tx2);line-height:1.6;white-space:pre-wrap">${(post.content||'').replace(/<[^>]+>/g,'')}</div>
                        </div>
                        ${post.total_reach > 0 ? `
                        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:12px">
                            <div style="text-align:center;background:var(--chq-bg2);border-radius:8px;padding:10px">
                                <div style="font-size:18px;font-weight:800;color:var(--chq-pri)">${this.numK(post.total_reach)}</div>
                                <div style="font-size:9px;color:var(--chq-tx3)">Reach</div>
                            </div>
                            <div style="text-align:center;background:var(--chq-bg2);border-radius:8px;padding:10px">
                                <div style="font-size:18px;font-weight:800;color:var(--chq-acc)">${this.numK(post.total_likes)}</div>
                                <div style="font-size:9px;color:var(--chq-tx3)">Likes</div>
                            </div>
                            <div style="text-align:center;background:var(--chq-bg2);border-radius:8px;padding:10px">
                                <div style="font-size:18px;font-weight:800;color:var(--chq-sky)">${this.numK(post.total_comments)}</div>
                                <div style="font-size:9px;color:var(--chq-tx3)">Comments</div>
                            </div>
                            <div style="text-align:center;background:var(--chq-bg2);border-radius:8px;padding:10px">
                                <div style="font-size:18px;font-weight:800;color:var(--chq-grn)">${(post.total_engagement_rate||0).toFixed(1)}%</div>
                                <div style="font-size:9px;color:var(--chq-tx3)">Eng Rate</div>
                            </div>
                        </div>` : ''}
                        <div style="display:flex;gap:8px">
                            <button onclick="frappe.set_route('Form','Social Post','${post.name}')" class="chq-btn chq-btn-pri">Open Full Form →</button>
                            <button onclick="cur_dialog.hide()" class="chq-btn chq-btn-ghost">Close</button>
                        </div>
                    </div>
                    `
                }],
                primary_action_label: 'Close',
                primary_action(vals) { d.hide(); }
            });
            d.show();
        } else {
            frappe.set_route('Form', 'Social Post', name);
        }
    }

    numK(v) {
        const n = parseFloat(v) || 0;
        if (n >= 1e9) return (n/1e9).toFixed(1)+'B';
        if (n >= 1e6) return (n/1e6).toFixed(1)+'M';
        if (n >= 1e3) return (n/1e3).toFixed(1)+'K';
        return Math.round(n).toLocaleString('en-NG');
    }
}

// ─── FADE IN ANIMATION ──────────────────────────────────────────────────────
const fadeStyle = document.createElement('style');
fadeStyle.textContent = `
@keyframes fadeIn { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }
.chq-panel.active { animation:fadeIn .3s ease; }
`;
document.head.appendChild(fadeStyle);