// Copyright (c) 2026, Value Impacts Consulting
// broker/broker/page/crm_dashboard/crm_dashboard.js
//
// ═══════════════════════════════════════════════════════════════════════════
//  CRM COMMAND CENTRE — World-Class Sales Intelligence Platform
//  Beats Salesforce on UX, HubSpot on financial integration
//
//  DocTypes (new CRM core):
//    CRM Lead · CRM Contact · CRM Account · CRM Deal · CRM Deal Stage
//    CRM Pipeline · CRM Activity · CRM Quota Target · CRM Territory · CRM Source
//    CRM Deal Note · CRM Deal Activity · CRM Deal Stakeholder · CRM Deal Product
//    CRM Stage History · CRM Deal Score · CRM Meeting
//
//  DocTypes (reused from Ecclesia — zero rebuild):
//    wa_conversation · wa_message · wa_template · telephone_call_log
//    external_task · external_task_item · journal_entry_voucher
// ═══════════════════════════════════════════════════════════════════════════

frappe.pages['crm-dashboard'].on_page_load = function (wrapper) {
    const load = () => new CRMDashboard(wrapper);
    if (typeof Chart === 'undefined') {
        const s = document.createElement('script');
        s.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
        s.onload = load; document.head.appendChild(s);
    } else { load(); }
};

// ─── THEME REGISTRY ──────────────────────────────────────────────────────────
const CRM_THEMES = {
    slate: {
        name: 'Slate Pro', icon: '🔷',
        '--cr-pri': '#2563EB', '--cr-pri-d': '#1D4ED8', '--cr-pri-x': 'rgba(37,99,235,.09)',
        '--cr-acc': '#60A5FA',
        '--cr-red': '#EF4444', '--cr-red-x': 'rgba(239,68,68,.09)',
        '--cr-amb': '#F59E0B', '--cr-amb-x': 'rgba(245,158,11,.09)',
        '--cr-grn': '#10B981', '--cr-grn-x': 'rgba(16,185,129,.09)',
        '--cr-sky': '#06B6D4', '--cr-sky-x': 'rgba(6,182,212,.09)',
        '--cr-pur': '#8B5CF6', '--cr-pur-x': 'rgba(139,92,246,.09)',
        '--cr-bg': '#F8FAFC', '--cr-card': '#FFFFFF',
        '--cr-brd': '#E2E8F0', '--cr-brd2': '#CBD5E1',
        '--cr-tx1': '#0F172A', '--cr-tx2': '#475569', '--cr-tx3': '#94A3B8',
        '--cr-banner': 'linear-gradient(135deg,#0F172A 0%,#1E3A5F 40%,#2563EB 75%,#06B6D4 100%)',
        '--cr-tab-h': '#EFF6FF',
    },
    midnight: {
        name: 'Midnight', icon: '🌙',
        '--cr-pri': '#818CF8', '--cr-pri-d': '#6366F1', '--cr-pri-x': 'rgba(129,140,248,.12)',
        '--cr-acc': '#A5B4FC',
        '--cr-red': '#F87171', '--cr-red-x': 'rgba(248,113,113,.12)',
        '--cr-amb': '#FCD34D', '--cr-amb-x': 'rgba(252,211,77,.12)',
        '--cr-grn': '#34D399', '--cr-grn-x': 'rgba(52,211,153,.12)',
        '--cr-sky': '#38BDF8', '--cr-sky-x': 'rgba(56,189,248,.12)',
        '--cr-pur': '#C084FC', '--cr-pur-x': 'rgba(192,132,252,.12)',
        '--cr-bg': '#0F172A', '--cr-card': '#1E293B',
        '--cr-brd': 'rgba(255,255,255,.08)', '--cr-brd2': 'rgba(255,255,255,.14)',
        '--cr-tx1': '#F1F5F9', '--cr-tx2': '#94A3B8', '--cr-tx3': '#475569',
        '--cr-banner': 'linear-gradient(135deg,#020617 0%,#0F172A 50%,#1E3A5F 70%,#312E81 100%)',
        '--cr-tab-h': 'rgba(129,140,248,.1)',
    },
    emerald: {
        name: 'Emerald', icon: '💚',
        '--cr-pri': '#059669', '--cr-pri-d': '#047857', '--cr-pri-x': 'rgba(5,150,105,.09)',
        '--cr-acc': '#34D399',
        '--cr-red': '#EF4444', '--cr-red-x': 'rgba(239,68,68,.09)',
        '--cr-amb': '#F59E0B', '--cr-amb-x': 'rgba(245,158,11,.09)',
        '--cr-grn': '#10B981', '--cr-grn-x': 'rgba(16,185,129,.09)',
        '--cr-sky': '#0EA5E9', '--cr-sky-x': 'rgba(14,165,233,.09)',
        '--cr-pur': '#8B5CF6', '--cr-pur-x': 'rgba(139,92,246,.09)',
        '--cr-bg': '#ECFDF5', '--cr-card': '#FFFFFF',
        '--cr-brd': '#A7F3D0', '--cr-brd2': '#6EE7B7',
        '--cr-tx1': '#022C22', '--cr-tx2': '#065F46', '--cr-tx3': '#6EE7B7',
        '--cr-banner': 'linear-gradient(135deg,#022C22 0%,#047857 40%,#059669 70%,#10B981 100%)',
        '--cr-tab-h': '#ECFDF5',
    },
    executive: {
        name: 'Executive', icon: '👔',
        '--cr-pri': '#7C3AED', '--cr-pri-d': '#6D28D9', '--cr-pri-x': 'rgba(124,58,237,.09)',
        '--cr-acc': '#A78BFA',
        '--cr-red': '#EF4444', '--cr-red-x': 'rgba(239,68,68,.09)',
        '--cr-amb': '#F59E0B', '--cr-amb-x': 'rgba(245,158,11,.09)',
        '--cr-grn': '#10B981', '--cr-grn-x': 'rgba(16,185,129,.09)',
        '--cr-sky': '#0EA5E9', '--cr-sky-x': 'rgba(14,165,233,.09)',
        '--cr-pur': '#EC4899', '--cr-pur-x': 'rgba(236,72,153,.09)',
        '--cr-bg': '#FAF5FF', '--cr-card': '#FFFFFF',
        '--cr-brd': '#E9D5FF', '--cr-brd2': '#D8B4FE',
        '--cr-tx1': '#2E1065', '--cr-tx2': '#5B21B6', '--cr-tx3': '#A78BFA',
        '--cr-banner': 'linear-gradient(135deg,#1E1B4B 0%,#4C1D95 35%,#7C3AED 65%,#EC4899 100%)',
        '--cr-tab-h': '#F5F3FF',
    },
};

// Deal stage colour map
const STAGE_COLORS = {
    'Lead In':        '#06B6D4',
    'Qualified':      '#8B5CF6',
    'Proposal Sent':  '#F59E0B',
    'Negotiation':    '#F97316',
    'Closed Won':     '#10B981',
    'Closed Lost':    '#EF4444',
};

// ─── MAIN CLASS ──────────────────────────────────────────────────────────────
class CRMDashboard {
    constructor(wrapper) {
        this.wrapper     = wrapper;
        this.page        = frappe.ui.make_app_page({ parent: wrapper, title: 'CRM Command Centre', single_column: true });
        this.charts      = {};
        this.leads       = [];
        this.opportunities = [];
        this.deals       = [];
        this.activities  = [];
        this.calls       = [];
        this.waConvos    = [];
        this.stages      = [];
        this.quotas      = [];
        this.contacts    = [];
        this.accounts    = [];
        this.timer       = null;
        this.activeTab   = 'myday';
        this.activeTheme = localStorage.getItem('crm-theme') || 'slate';
        this.kanbanDrag  = null;
        this.init();
    }

    init() {
        this.injectStyles();
        this.applyTheme(this.activeTheme, false);
        this.setupActions();
        this.buildLayout();
        this.setupFilters();
        this.bindEvents();
        this.loadData();
        this.startClock();
        this.startAutoRefresh();
    }

    // ─── THEME ENGINE ─────────────────────────────────────────────────────────
    applyTheme(key, save = true) {
        const t = CRM_THEMES[key] || CRM_THEMES.slate;
        this.activeTheme = key;
        if (save) localStorage.setItem('crm-theme', key);
        const root = document.getElementById('cr-root') || document.documentElement;
        Object.entries(t).forEach(([k, v]) => { if (k.startsWith('--')) root.style.setProperty(k, v); });
        if (document.getElementById('cr-theme-label')) {
            document.getElementById('cr-theme-label').textContent = t.icon + ' ' + t.name;
        }
        Object.values(this.charts).forEach(c => { try { c.update(); } catch(e){} });
    }

    openThemePicker() {
        const cur = this.activeTheme;
        frappe.msgprint({
            title: '🎨 Choose Dashboard Theme', indicator: 'blue',
            message: `<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:4px 0">
                ${Object.entries(CRM_THEMES).map(([key, t]) => `
                <div onclick="__crmDash.applyTheme('${key}');if(cur_dialog)cur_dialog.hide();"
                     style="display:flex;align-items:center;gap:10px;padding:12px 14px;border-radius:10px;
                            border:2px solid ${key===cur?'var(--cr-pri)':'var(--cr-brd)'};
                            background:var(--cr-card);cursor:pointer;transition:all .18s">
                    <div style="font-size:22px">${t.icon}</div>
                    <div>
                        <div style="font-size:13px;font-weight:700;color:var(--cr-tx1)">${t.name}</div>
                        <div style="font-size:10px;color:var(--cr-tx3)">Click to apply</div>
                    </div>
                    ${key===cur?'<span style="margin-left:auto;color:var(--cr-pri);font-size:18px">✓</span>':''}
                </div>`).join('')}
            </div>`
        });
    }

    // ─── STYLES ───────────────────────────────────────────────────────────────
    injectStyles() {
        if (document.getElementById('cr-styles')) return;
        const el = document.createElement('style');
        el.id = 'cr-styles';
        el.textContent = `
/* ════════════════════════════════════════════════════════
   CRM COMMAND CENTRE — Value Impacts / PortfolioOne
   World-class Sales Intelligence Platform on Frappe
═════════════════════════════════════════════════════════ */
#cr-root * { box-sizing:border-box; }
#cr-root {
    background:var(--cr-bg); min-height:100vh;
    font-family:-apple-system,'Segoe UI',system-ui,sans-serif;
    color:var(--cr-tx1); transition:background .3s,color .3s;
}
/* BANNER */
.cr-banner { background:var(--cr-banner);padding:22px 28px 18px;margin:-15px -15px 20px;position:relative;overflow:hidden;color:#fff; }
.cr-banner::before { content:'';position:absolute;width:500px;height:500px;top:-60%;right:-5%;border-radius:50%;background:radial-gradient(circle,rgba(255,255,255,.06) 0%,transparent 70%); }
.cr-banner-inner { position:relative;z-index:1;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px; }
.cr-banner h1   { font-size:23px;font-weight:800;letter-spacing:-.4px;margin:0 0 6px;display:flex;align-items:center;gap:10px; }
.cr-banner-meta { display:flex;align-items:center;gap:14px;font-size:12px;opacity:.82;flex-wrap:wrap; }
.cr-live  { display:inline-flex;align-items:center;gap:5px;background:rgba(16,185,129,.22);padding:3px 10px;border-radius:20px;font-size:11px;color:#34d399;border:1px solid rgba(16,185,129,.3); }
.cr-dot   { width:7px;height:7px;background:#34d399;border-radius:50%;animation:cr-pulse 2s infinite; }
@keyframes cr-pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.4;transform:scale(1.3)} }
.cr-chip  { display:inline-flex;align-items:center;gap:5px;background:rgba(255,255,255,.14);padding:4px 11px;border-radius:20px;font-size:11px;font-weight:600; }
.cr-theme-btn { display:inline-flex;align-items:center;gap:6px;padding:5px 13px;border-radius:20px;font-size:11px;font-weight:700;background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.25);color:#fff;cursor:pointer;transition:all .18s;font-family:inherit; }
.cr-theme-btn:hover { background:rgba(255,255,255,.3); }
/* ALERTS */
.cr-alerts { display:flex;gap:10px;flex-wrap:wrap;margin-bottom:18px; }
.cr-alert  { display:flex;align-items:center;gap:7px;padding:8px 14px;border-radius:10px;font-size:12px;font-weight:600;cursor:pointer;transition:all .18s;text-decoration:none !important; }
.cr-alert:hover { transform:translateY(-1px); }
.cr-a-red  { background:var(--cr-red-x);border:1px solid rgba(239,68,68,.2);color:var(--cr-red); }
.cr-a-amb  { background:var(--cr-amb-x);border:1px solid rgba(245,158,11,.2);color:var(--cr-amb); }
.cr-a-pri  { background:var(--cr-pri-x);border:1px solid rgba(37,99,235,.2);color:var(--cr-pri); }
.cr-a-grn  { background:var(--cr-grn-x);border:1px solid rgba(16,185,129,.2);color:var(--cr-grn); }
.cr-a-pur  { background:var(--cr-pur-x);border:1px solid rgba(139,92,246,.2);color:var(--cr-pur); }
/* FILTERS */
.cr-filters { background:var(--cr-card);border:1px solid var(--cr-brd);border-radius:14px;padding:14px 20px;margin-bottom:18px;display:flex;gap:16px;flex-wrap:wrap;align-items:flex-end; }
.cr-fg { flex:1;min-width:120px; }
.cr-fg label { display:block;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.7px;color:var(--cr-tx3);margin-bottom:5px; }
/* TABS */
.cr-tabs { display:flex;gap:2px;background:var(--cr-card);border:1px solid var(--cr-brd);border-radius:12px;margin-bottom:18px;overflow-x:auto;scrollbar-width:none; }
.cr-tabs::-webkit-scrollbar { display:none; }
.cr-tab { display:flex;align-items:center;gap:7px;padding:11px 16px;font-size:12px;font-weight:600;color:var(--cr-tx2);cursor:pointer;border-bottom:3px solid transparent;transition:all .18s;white-space:nowrap;background:none;border-left:none;border-right:none;border-top:none; }
.cr-tab:hover  { color:var(--cr-pri);background:var(--cr-tab-h,var(--cr-pri-x)); }
.cr-tab.active { color:var(--cr-pri);border-bottom-color:var(--cr-pri);background:var(--cr-pri-x); }
.cr-tab-n { background:var(--cr-red);color:#fff;font-size:9px;font-weight:800;padding:1px 6px;border-radius:20px;min-width:16px;text-align:center; }
/* KPI STRIP */
.cr-kpis { display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:14px;margin-bottom:18px; }
.cr-kpi  { background:var(--cr-card);border:1px solid var(--cr-brd);border-radius:14px;padding:18px 20px;cursor:pointer;transition:all .2s;position:relative;overflow:hidden; }
.cr-kpi::after { content:'';position:absolute;top:0;left:0;right:0;height:3px;opacity:0;transition:opacity .2s; }
.cr-kpi:hover { transform:translateY(-3px);box-shadow:0 8px 24px rgba(0,0,0,.12); }
.cr-kpi:hover::after { opacity:1; }
.kc-pri::after{background:var(--cr-pri)} .kc-grn::after{background:var(--cr-grn)} .kc-red::after{background:var(--cr-red)} .kc-amb::after{background:var(--cr-amb)} .kc-sky::after{background:var(--cr-sky)} .kc-pur::after{background:var(--cr-pur)}
.cr-kpi-icon { font-size:18px;margin-bottom:10px; }
.cr-kpi-lbl  { font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:var(--cr-tx3);margin-bottom:6px; }
.cr-kpi-val  { font-size:26px;font-weight:800;color:var(--cr-tx1);line-height:1;margin-bottom:4px; }
.cr-kpi-sub  { font-size:11px;color:var(--cr-tx3); }
/* CARDS */
.cr-card { background:var(--cr-card);border:1px solid var(--cr-brd);border-radius:14px;overflow:hidden;transition:box-shadow .2s; }
.cr-card:hover { box-shadow:0 4px 20px rgba(0,0,0,.1); }
.cr-card-head { padding:13px 18px;border-bottom:1px solid var(--cr-brd);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px; }
.cr-card-title { display:flex;align-items:center;gap:9px;font-size:13px;font-weight:700;color:var(--cr-tx1); }
.cr-title-icon { width:26px;height:26px;border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:12px; }
.cr-card-body { padding:16px 18px; }
/* GRIDS */
.cr-g2  { display:grid;grid-template-columns:1fr 1fr;    gap:16px;margin-bottom:16px; }
.cr-g3  { display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-bottom:16px; }
.cr-g21 { display:grid;grid-template-columns:2fr 1fr;    gap:16px;margin-bottom:16px; }
.cr-g31 { display:grid;grid-template-columns:3fr 1fr;    gap:16px;margin-bottom:16px; }
.cr-row { margin-bottom:16px; }
/* BUTTONS */
.cr-acts { display:flex;gap:7px;flex-wrap:wrap; }
.cr-btn { display:inline-flex;align-items:center;gap:6px;padding:6px 13px;border-radius:20px;font-size:11px;font-weight:700;cursor:pointer;border:1.5px solid transparent;text-decoration:none !important;font-family:inherit;transition:all .18s;line-height:1.4; }
.cr-btn:hover { transform:translateY(-1px); }
.cb-pri  { background:var(--cr-pri-x);color:var(--cr-pri);border-color:rgba(37,99,235,.2); }
.cb-pri:hover  { background:var(--cr-pri);color:#fff; }
.cb-grn  { background:var(--cr-grn-x);color:var(--cr-grn);border-color:rgba(16,185,129,.2); }
.cb-grn:hover  { background:var(--cr-grn);color:#fff; }
.cb-red  { background:var(--cr-red-x);color:var(--cr-red);border-color:rgba(239,68,68,.2); }
.cb-red:hover  { background:var(--cr-red);color:#fff; }
.cb-amb  { background:var(--cr-amb-x);color:var(--cr-amb);border-color:rgba(245,158,11,.2); }
.cb-amb:hover  { background:var(--cr-amb);color:#fff; }
.cb-pur  { background:var(--cr-pur-x);color:var(--cr-pur);border-color:rgba(139,92,246,.2); }
.cb-pur:hover  { background:var(--cr-pur);color:#fff; }
.cb-ghost { background:transparent;color:var(--cr-tx2);border-color:var(--cr-brd2); }
.cb-ghost:hover { background:var(--cr-bg);color:var(--cr-tx1); }
.cb-solid { background:var(--cr-pri);color:#fff;border-color:var(--cr-pri); }
.cb-solid:hover { background:var(--cr-pri-d); }
/* TABLE */
.cr-tbl-wrap { overflow-x:auto;max-height:440px;overflow-y:auto; }
.cr-tbl { width:100%;border-collapse:collapse;font-size:12px; }
.cr-tbl thead th { padding:10px 14px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--cr-tx3);background:var(--cr-bg);border-bottom:2px solid var(--cr-brd);position:sticky;top:0;white-space:nowrap;z-index:1; }
.cr-tbl tbody td { padding:10px 14px;border-bottom:1px solid var(--cr-brd);color:var(--cr-tx2); }
.cr-tbl tbody tr { cursor:pointer;transition:background .12s; }
.cr-tbl tbody tr:hover { background:var(--cr-pri-x); }
.cr-tbl tbody tr:hover td { color:var(--cr-tx1); }
.cr-tbl tbody tr:last-child td { border-bottom:none; }
/* BADGE */
.cr-badge { display:inline-flex;align-items:center;gap:3px;padding:3px 8px;border-radius:20px;font-size:10px;font-weight:700;white-space:nowrap; }
.bd-grn  { background:var(--cr-grn-x);color:var(--cr-grn); }
.bd-red  { background:var(--cr-red-x);color:var(--cr-red); }
.bd-amb  { background:var(--cr-amb-x);color:var(--cr-amb); }
.bd-pri  { background:var(--cr-pri-x);color:var(--cr-pri); }
.bd-sky  { background:var(--cr-sky-x);color:var(--cr-sky); }
.bd-pur  { background:var(--cr-pur-x);color:var(--cr-pur); }
.bd-grey { background:var(--cr-bg);color:var(--cr-tx3);border:1px solid var(--cr-brd); }
/* PROGRESS */
.cr-bar-row { display:flex;align-items:center;gap:10px;margin-bottom:9px; }
.cr-bar-lbl { font-size:11px;color:var(--cr-tx2);width:140px;flex-shrink:0; }
.cr-bar     { flex:1;height:6px;background:var(--cr-brd);border-radius:40px;overflow:hidden; }
.cr-bar-fill{ height:100%;border-radius:40px;transition:width .6s cubic-bezier(.4,0,.2,1); }
.cr-bar-val { font-size:11px;font-family:monospace;font-weight:700;width:50px;text-align:right;color:var(--cr-tx1); }
/* SCORE RING */
.cr-score-ring { position:relative;width:76px;height:76px;flex-shrink:0; }
.cr-score-ring svg { width:76px;height:76px; }
.cr-score-label { position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:800;color:var(--cr-tx1); }
/* KANBAN */
.cr-kanban { display:flex;gap:14px;overflow-x:auto;padding-bottom:12px;scrollbar-width:thin; }
.cr-kanban::-webkit-scrollbar { height:5px; }
.cr-kanban::-webkit-scrollbar-track { background:transparent; }
.cr-kanban::-webkit-scrollbar-thumb { background:var(--cr-brd2);border-radius:10px; }
.cr-kb-col { min-width:240px;max-width:260px;flex-shrink:0;display:flex;flex-direction:column;gap:0; }
.cr-kb-head { padding:10px 14px;border-radius:10px 10px 0 0;display:flex;align-items:center;justify-content:space-between;font-size:12px;font-weight:700;color:#fff;cursor:pointer; }
.cr-kb-body { flex:1;min-height:200px;background:var(--cr-bg);border:1px solid var(--cr-brd);border-top:none;border-radius:0 0 10px 10px;padding:8px;overflow-y:auto;max-height:500px; }
.cr-kb-body.drag-over { background:var(--cr-pri-x);border-color:var(--cr-pri); }
.cr-kb-card {
    background:var(--cr-card);border:1px solid var(--cr-brd);border-radius:10px;
    padding:12px 13px;margin-bottom:8px;cursor:grab;transition:all .18s;
    position:relative;
}
.cr-kb-card:hover { box-shadow:0 4px 16px rgba(0,0,0,.12);transform:translateY(-1px); }
.cr-kb-card.dragging { opacity:.4;cursor:grabbing; }
.cr-kb-card::before { content:'';position:absolute;left:0;top:0;bottom:0;width:3px;border-radius:10px 0 0 10px; }
.cr-kb-title { font-size:12px;font-weight:700;color:var(--cr-tx1);margin-bottom:6px;line-height:1.3; }
.cr-kb-meta  { font-size:10px;color:var(--cr-tx3);margin-bottom:6px; }
.cr-kb-value { font-size:13px;font-weight:800;color:var(--cr-pri);margin-bottom:6px; }
.cr-kb-footer { display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:4px; }
.cr-kb-avatar { width:20px;height:20px;border-radius:50%;background:var(--cr-pri);color:#fff;font-size:9px;font-weight:700;display:flex;align-items:center;justify-content:center; }
.cr-kb-days { font-size:9px;padding:2px 6px;border-radius:10px;font-weight:700; }
.cr-kb-count { font-size:10px;font-weight:700;color:var(--cr-tx3);padding:4px 10px;border-radius:20px;background:rgba(255,255,255,.2); }
/* AI CARD */
.cr-ai-card { background:var(--cr-pur-x);border:1px solid rgba(139,92,246,.2);border-radius:12px;padding:14px 16px;margin-bottom:12px; }
.cr-ai-card h4 { font-size:12px;font-weight:700;color:var(--cr-pur);margin:0 0 8px; }
.cr-ai-item { display:flex;align-items:flex-start;gap:8px;margin-bottom:7px;font-size:12px;color:var(--cr-tx1); }
.cr-ai-bullet { width:6px;height:6px;background:var(--cr-pur);border-radius:50%;margin-top:5px;flex-shrink:0; }
/* ACTIVITY FEED */
.cr-activity { padding:11px 16px;border-bottom:1px solid var(--cr-brd);display:flex;align-items:flex-start;gap:10px;transition:background .12s;cursor:pointer; }
.cr-activity:hover { background:var(--cr-pri-x); }
.cr-activity:last-child { border-bottom:none; }
.cr-act-icon { width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:13px;flex-shrink:0; }
.cr-act-body { flex:1;min-width:0; }
.cr-act-title { font-size:12px;font-weight:600;color:var(--cr-tx1);margin-bottom:2px; }
.cr-act-meta  { font-size:10px;color:var(--cr-tx3);display:flex;gap:8px;flex-wrap:wrap; }
/* TIMELINE */
.cr-timeline { padding:0 18px; }
.cr-tl-item  { display:flex;gap:12px;padding-bottom:18px;position:relative; }
.cr-tl-item::before { content:'';position:absolute;left:15px;top:30px;bottom:0;width:1px;background:var(--cr-brd); }
.cr-tl-item:last-child::before { display:none; }
.cr-tl-dot   { width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:13px;flex-shrink:0;border:2px solid var(--cr-brd); }
.cr-tl-body  { flex:1;padding-top:4px; }
.cr-tl-title { font-size:12px;font-weight:600;color:var(--cr-tx1); }
.cr-tl-meta  { font-size:10px;color:var(--cr-tx3);margin-top:2px; }
.cr-tl-note  { font-size:11px;color:var(--cr-tx2);margin-top:5px;background:var(--cr-bg);border-radius:8px;padding:8px 10px;border-left:2px solid var(--cr-pri); }
/* QUOTA GAUGE */
.cr-quota-wrap { display:flex;align-items:center;gap:16px;padding:14px 0; }
.cr-quota-ring { position:relative;flex-shrink:0; }
.cr-quota-ring svg { display:block; }
.cr-quota-label { position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center; }
.cr-quota-pct   { font-size:20px;font-weight:800;color:var(--cr-tx1); }
.cr-quota-sub   { font-size:9px;color:var(--cr-tx3);text-align:center; }
.cr-quota-stats { flex:1; }
.cr-quota-row { display:flex;justify-content:space-between;font-size:12px;margin-bottom:6px; }
/* QUICK ACTIONS */
.cr-qlinks { display:grid;grid-template-columns:repeat(auto-fill,minmax(148px,1fr));gap:10px; }
.cr-qlink { display:flex;align-items:center;gap:11px;padding:12px 14px;border-radius:12px;background:var(--cr-card);border:1px solid var(--cr-brd);text-decoration:none !important;color:var(--cr-tx1);transition:all .18s; }
.cr-qlink:hover { transform:translateY(-2px);box-shadow:0 6px 20px rgba(0,0,0,.12);border-color:var(--cr-pri); }
.cr-ql-icon  { width:34px;height:34px;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:14px;color:#fff;flex-shrink:0; }
.cr-ql-title { font-size:12px;font-weight:600;color:var(--cr-tx1);line-height:1.3; }
.cr-ql-desc  { font-size:10px;color:var(--cr-tx3); }
/* LEAD SCORE CARD */
.cr-score-card { background:var(--cr-card);border:1px solid var(--cr-brd);border-radius:12px;padding:12px 14px;margin-bottom:8px;display:flex;align-items:center;gap:12px;cursor:pointer;transition:all .15s; }
.cr-score-card:hover { border-color:var(--cr-pri);background:var(--cr-pri-x); }
.cr-score-num { width:40px;height:40px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:800;color:#fff;flex-shrink:0; }
.cr-score-body { flex:1;min-width:0; }
.cr-score-name { font-size:12px;font-weight:700;color:var(--cr-tx1);white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
.cr-score-meta { font-size:10px;color:var(--cr-tx3);display:flex;gap:8px;margin-top:2px; }
/* NBA CARD (Next Best Action) */
.cr-nba { background:var(--cr-pri);border-radius:12px;padding:14px 16px;margin-bottom:10px;color:#fff; }
.cr-nba h4 { font-size:12px;font-weight:700;opacity:.8;margin:0 0 6px; }
.cr-nba-title { font-size:14px;font-weight:700;margin-bottom:4px; }
.cr-nba-meta  { font-size:11px;opacity:.75; }
.cr-nba-btn   { margin-top:10px;display:inline-flex;align-items:center;gap:6px;background:rgba(255,255,255,.2);border:1px solid rgba(255,255,255,.3);color:#fff;padding:5px 12px;border-radius:20px;font-size:11px;font-weight:700;cursor:pointer;transition:background .15s; }
.cr-nba-btn:hover { background:rgba(255,255,255,.35); }
/* LOADER */
.cr-loader { position:fixed;inset:0;background:rgba(255,255,255,.9);display:flex;align-items:center;justify-content:center;flex-direction:column;gap:16px;z-index:9999; }
.cr-loader-spinner { width:44px;height:44px;border:3px solid #E2E8F0;border-top-color:var(--cr-pri);border-radius:50%;animation:cr-spin .7s linear infinite; }
@keyframes cr-spin { to{transform:rotate(360deg)} }
.cr-empty { text-align:center;padding:36px;color:var(--cr-tx3);font-size:12px; }
.cr-sched-slot { display:flex;align-items:center;gap:10px;padding:10px 14px;border-radius:10px;background:var(--cr-bg);border:1px solid var(--cr-brd);margin-bottom:8px;cursor:pointer;transition:all .15s; }
.cr-sched-slot:hover { border-color:var(--cr-pri);background:var(--cr-pri-x); }
.cr-sched-time { font-size:11px;font-weight:700;color:var(--cr-tx3);width:52px;flex-shrink:0; }
.cr-sched-body { flex:1;min-width:0; }
.cr-sched-title { font-size:12px;font-weight:600;color:var(--cr-tx1);margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
.cr-sched-meta  { font-size:10px;color:var(--cr-tx3);display:flex;align-items:center;gap:8px; }
.tr { text-align:right; }
@media(max-width:1100px){ .cr-g21,.cr-g31{grid-template-columns:1fr} }
@media(max-width:800px) { .cr-g2,.cr-g3{grid-template-columns:1fr} }
@media print { .cr-filters,.cr-acts,.cr-qlinks,.page-actions,.cr-theme-btn{display:none !important} }
        `;
        document.head.appendChild(el);
    }

    // ─── PAGE ACTIONS ─────────────────────────────────────────────────────────
    setupActions() {
        this.page.set_primary_action('✚ New Lead', () => frappe.new_doc('CRM Lead'), null);
        this.page.set_secondary_action('↺ Refresh', () => this.loadData());
        this.page.add_menu_item('✚ New Deal',           () => frappe.new_doc('CRM Deal'));
        this.page.add_menu_item('✚ New Contact',        () => frappe.new_doc('CRM Contact'));
        this.page.add_menu_item('✚ New Account',        () => frappe.new_doc('CRM Account'));
        this.page.add_menu_item('📞 Log a Call',        () => this.logCallDialog());
        this.page.add_menu_item('📝 Log Activity',      () => this.logActivityDialog());
        this.page.add_menu_item('🎨 Change Theme',       () => this.openThemePicker());
        this.page.add_menu_item('⏸ Pause Auto-Refresh', () => this.stopAutoRefresh());
        this.page.add_menu_item('▶ Resume Auto-Refresh',() => this.startAutoRefresh());
        this.page.add_menu_item('📊 Export Pipeline',   () => this.exportPipeline());
        this.page.add_menu_item('🖨️ Print Dashboard',   () => window.print());
    }

    // ─── LAYOUT ───────────────────────────────────────────────────────────────
    buildLayout() {
        window.__crmDash = this;
        this.$root = $(`
            <div id="cr-root">
                <div class="cr-banner">
                    <div class="cr-banner-inner">
                        <div>
                            <h1>🎯 CRM Command Centre</h1>
                            <div class="cr-banner-meta">
                                <span><i class="fa fa-calendar"></i>&nbsp;<span id="cr-date"></span></span>
                                <span id="cr-clock" style="font-family:monospace"></span>
                                <span class="cr-live"><span class="cr-dot"></span> Live</span>
                                <span class="cr-chip" id="cr-chip-pipe">— Pipeline</span>
                                <span class="cr-chip" id="cr-chip-leads">— Leads</span>
                            </div>
                        </div>
                        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
                            <button class="cr-theme-btn" onclick="__crmDash.openThemePicker()">
                                <i class="fa fa-paint-brush"></i>
                                <span id="cr-theme-label">🔷 Slate Pro</span>
                            </button>
                            <span id="cr-ts" style="font-size:11px;opacity:.6"></span>
                        </div>
                    </div>
                </div>

                <div style="padding:0 16px 32px">
                    <div class="cr-alerts" id="cr-alerts"></div>
                    <div id="cr-filters"></div>

                    <div class="cr-tabs">
                        <button class="cr-tab active" data-tab="myday">🌅 My Day</button>
                        <button class="cr-tab" data-tab="pipeline">🔀 Pipeline<span class="cr-tab-n" id="cr-n-hot" style="display:none">0</span></button>
                        <button class="cr-tab" data-tab="leads">🎯 Leads<span class="cr-tab-n" id="cr-n-new" style="display:none">0</span></button>
                        <button class="cr-tab" data-tab="opportunities">💼 Opportunities<span class="cr-tab-n" id="cr-n-opp" style="display:none">0</span></button>
                        <button class="cr-tab" data-tab="contacts">👥 Contacts</button>
                        <button class="cr-tab" data-tab="accounts">🏢 Accounts</button>
                        <button class="cr-tab" data-tab="activities">📋 Activities</button>
                        <button class="cr-tab" data-tab="messaging">💬 Messaging</button>
                        <button class="cr-tab" data-tab="ai">🤖 AI Studio</button>
                        <button class="cr-tab" data-tab="reports">📈 Reports</button>
                        <button class="cr-tab" data-tab="actions">⚡ Quick Actions</button>
                    </div>

                    <div id="cr-panel-myday"        class="cr-panel-wrap"></div>
                    <div id="cr-panel-pipeline"     class="cr-panel-wrap" style="display:none"></div>
                    <div id="cr-panel-leads"        class="cr-panel-wrap" style="display:none"></div>
                    <div id="cr-panel-opportunities"class="cr-panel-wrap" style="display:none"></div>
                    <div id="cr-panel-contacts"     class="cr-panel-wrap" style="display:none"></div>
                    <div id="cr-panel-accounts"     class="cr-panel-wrap" style="display:none"></div>
                    <div id="cr-panel-activities"   class="cr-panel-wrap" style="display:none"></div>
                    <div id="cr-panel-messaging"    class="cr-panel-wrap" style="display:none"></div>
                    <div id="cr-panel-ai"           class="cr-panel-wrap" style="display:none"></div>
                    <div id="cr-panel-reports"      class="cr-panel-wrap" style="display:none"></div>
                    <div id="cr-panel-actions"      class="cr-panel-wrap" style="display:none"></div>
                </div>

                <div class="cr-loader" id="cr-loader" style="display:none">
                    <div class="cr-loader-spinner"></div>
                    <div style="font-weight:600;color:#475569">Loading CRM Intelligence...</div>
                    <div style="font-size:12px;color:#94A3B8">Fetching leads, deals, activities & AI scores</div>
                </div>
            </div>
        `).appendTo(this.page.main);

        this.applyTheme(this.activeTheme, false);
    }

    // ─── FILTERS ──────────────────────────────────────────────────────────────
    setupFilters() {
        $('#cr-filters').html(`
            <div class="cr-filters">
                <div class="cr-fg"><label>🗺 Territory</label><div id="cr-flt-territory"></div></div>
                <div class="cr-fg"><label>📊 Stage</label><div id="cr-flt-stage"></div></div>
                <div class="cr-fg"><label>👤 Assigned Rep</label><div id="cr-flt-rep"></div></div>
                <div class="cr-fg"><label>🏭 Source</label><div id="cr-flt-source"></div></div>
                <div style="display:flex;gap:8px;align-items:flex-end">
                    <button class="btn btn-primary btn-sm" id="cr-apply"><i class="fa fa-filter"></i> Apply</button>
                    <button class="btn btn-default btn-sm" id="cr-reset"><i class="fa fa-undo"></i> Reset</button>
                    <button class="btn btn-success btn-sm" id="cr-export-btn"><i class="fa fa-download"></i> Export</button>
                </div>
            </div>
        `);
        this.f = {};
        this.f.territory = frappe.ui.form.make_control({ parent: $('#cr-flt-territory'), render_input: true, df: { fieldtype: 'Link', options: 'CRM Territory', placeholder: 'All Territories' } });
        this.f.stage     = frappe.ui.form.make_control({ parent: $('#cr-flt-stage'),     render_input: true, df: { fieldtype: 'Select', options: '\nLead In\nQualified\nProposal Sent\nNegotiation\nClosed Won\nClosed Lost', placeholder: 'All Stages' } });
        this.f.rep       = frappe.ui.form.make_control({ parent: $('#cr-flt-rep'),       render_input: true, df: { fieldtype: 'Link', options: 'User', placeholder: 'All Reps' } });
        this.f.source    = frappe.ui.form.make_control({ parent: $('#cr-flt-source'),    render_input: true, df: { fieldtype: 'Link', options: 'CRM Source', placeholder: 'All Sources' } });
    }

    getFilters() {
        const filters = [];
        const s = this.f.stage?.get_value();
        const r = this.f.rep?.get_value();
        if (s) filters.push(['stage', '=', s]);
        if (r) filters.push(['assigned_to', '=', r]);
        return filters;
    }

    // ─── EVENTS ───────────────────────────────────────────────────────────────
    bindEvents() {
        $(document).on('click', '#cr-apply',     () => this.loadData());
        $(document).on('click', '#cr-reset',     () => { Object.values(this.f).forEach(f => f?.set_value?.('')); this.loadData(); });
        $(document).on('click', '#cr-export-btn',() => this.exportPipeline());
        $(document).on('click', '.cr-tab',       (e) => this.switchTab($(e.currentTarget).data('tab')));
    }

    switchTab(name) {
        $('.cr-tab').removeClass('active');
        $(`.cr-tab[data-tab="${name}"]`).addClass('active');
        $('.cr-panel-wrap').hide();
        $(`#cr-panel-${name}`).show();
        this.activeTab = name;
        if (this.leads.length || this.deals.length) this.renderTab(name);
    }

    startClock() {
        const tick = () => {
            $('#cr-clock').text(new Date().toLocaleTimeString('en-NG', { hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:true }));
            $('#cr-date').text(frappe.datetime.str_to_user(frappe.datetime.get_today()));
        };
        tick(); setInterval(tick, 1000);
    }

    startAutoRefresh() { this.stopAutoRefresh(); this.timer = setInterval(() => this.loadData(true), 30000); }
    stopAutoRefresh()  { if (this.timer) { clearInterval(this.timer); this.timer = null; } }

    // ─── DATA LOAD ────────────────────────────────────────────────────────────
    async loadData(silent = false) {
        if (!silent) $('#cr-loader').show();
        try {
            const [leadsR, oppsR, dealsR, activR, callsR, waR, quotaR, contactsR, accountsR] = await Promise.all([
                frappe.call({ method:'frappe.client.get_list', args: {
                    doctype:'CRM Lead',
                    fields:['name','lead_name','company_name','email','mobile_no','status','lead_source',
                            'territory','assigned_to','lead_score','icp_fit_score','priority',
                            'annual_revenue','industry','no_of_employees','job_title','creation','modified'],
                    limit_page_length:500, order_by:'modified desc'
                }}),
                frappe.call({ method:'frappe.client.get_list', args: {
                    doctype:'CRM Opportunity',
                    fields:['name','opportunity_title','lead','contact','account','status','opportunity_value',
                            'probability','expected_close_date','assigned_to','territory','source',
                            'opportunity_score','predicted_close_prob','days_in_status',
                            'last_activity_date','creation','modified'],
                    limit_page_length:500, order_by:'modified desc'
                }}),
                frappe.call({ method:'frappe.client.get_list', args: {
                    doctype:'CRM Deal',
                    fields:['name','deal_title','contact','account','stage','deal_value','probability',
                            'assigned_to','close_date','deal_health_score','days_in_stage',
                            'last_activity_date','pipeline','currency','territory','creation','modified'],
                    filters: this.getFilters(),
                    limit_page_length:500, order_by:'modified desc'
                }}),
                frappe.call({ method:'frappe.client.get_list', args: {
                    doctype:'CRM Activity',
                    fields:['name','activity_type','subject','status','due_date','contact',
                            'deal','lead','opportunity','assigned_to','outcome','duration_minutes','creation'],
                    limit_page_length:300, order_by:'due_date asc'
                }}),
                frappe.call({ method:'frappe.client.get_list', args: {
                    doctype:'Telephone Call Log',
                    fields:['name','caller_name','receiver_name','direction','status','started_at',
                            'duration','outcome_notes','caller_user'],
                    limit_page_length:100, order_by:'started_at desc'
                }}),
                frappe.call({ method:'frappe.client.get_list', args: {
                    doctype:'WA Conversation',
                    fields:['name','contact_display_name','phone_number','status','last_message_at',
                            'last_message_preview','assigned_to','lead'],
                    limit_page_length:100, order_by:'last_message_at desc'
                }}),
                frappe.call({ method:'frappe.client.get_list', args: {
                    doctype:'CRM Quota Target',
                    fields:['name','rep','period','target_value','achieved_value','period_start','period_end'],
                    limit_page_length:50, order_by:'period_start desc'
                }}),
                frappe.call({ method:'frappe.client.get_list', args: {
                    doctype:'CRM Contact',
                    fields:['name','full_name','email','mobile_no','company_name','job_title','account','assigned_to','creation','modified'],
                    limit_page_length:300, order_by:'modified desc'
                }}),
                frappe.call({ method:'frappe.client.get_list', args: {
                    doctype:'CRM Account',
                    fields:['name','account_name','industry','annual_revenue','territory','assigned_to','erpnext_customer','creation','modified'],
                    limit_page_length:200, order_by:'modified desc'
                }}),
            ]);

            this.leads        = leadsR.message      || [];
            this.opportunities= oppsR.message       || [];
            this.deals        = dealsR.message      || [];
            this.activities   = activR.message      || [];
            this.calls        = callsR.message      || [];
            this.waConvos     = waR.message         || [];
            this.quotas       = quotaR.message      || [];
            this.contacts     = contactsR.message   || [];
            this.accounts     = accountsR.message   || [];

            this.renderAll();
            $('#cr-ts').text('Updated ' + new Date().toLocaleTimeString());

            // AI score calculation (client-side heuristic)
            this.calcAIScores();

        } catch(e) {
            console.error(e);
            if (!silent) frappe.msgprint({ title:'Error', indicator:'red', message:'Failed to load CRM data. Check DocTypes are installed.' });
        } finally { $('#cr-loader').hide(); }
    }

    // ─── AI SCORING (client-side heuristic) ─────────────────────────────────
    calcAIScores() {
        const today = new Date();

        // Score deals
        this.deals = this.deals.map(d => {
            const daysToClose = d.close_date ? Math.ceil((new Date(d.close_date) - today) / 86400000) : 30;
            const lastAct     = d.last_activity_date ? Math.ceil((today - new Date(d.last_activity_date)) / 86400000) : 99;
            const stageWeight = { 'Lead In':5, 'Qualified':20, 'Proposal Sent':40, 'Negotiation':65, 'Closed Won':100, 'Closed Lost':0 };
            const base     = stageWeight[d.stage] || 20;
            const actPen   = Math.min(30, lastAct * 2);
            const datePen  = daysToClose < 0 ? 25 : daysToClose < 7 ? 5 : 0;
            const prob     = flt(d.probability);
            const health   = Math.max(0, Math.min(100, base + (prob * 0.3) - actPen - datePen));
            d._health      = Math.round(health);
            d._urgency     = daysToClose < 7 ? 'high' : daysToClose < 14 ? 'med' : 'low';
            d._lastActDays = lastAct;
            return d;
        });

        // Score leads using multi-factor ICP model
        this.leads = this.leads.map(l => {
            const base    = flt(l.lead_score) || 30;
            const icp     = flt(l.icp_fit_score) || 50;
            const rev     = flt(l.annual_revenue) > 5000000 ? 20 : flt(l.annual_revenue) > 1000000 ? 12 : flt(l.annual_revenue) > 100000 ? 6 : 0;
            // Industry fit boost
            const indBoost = ['Technology','Financial Services','Insurance','Oil & Gas','Manufacturing'].includes(l.industry) ? 8 : 0;
            // Seniority boost
            const roleBoost = l.job_title && /ceo|cfo|cto|director|vp|head|manager/i.test(l.job_title) ? 10 : 0;
            // Engagement recency penalty
            const ageDays  = l.modified ? Math.ceil((today - new Date(l.modified)) / 86400000) : 30;
            const agePen   = ageDays > 14 ? 10 : ageDays > 7 ? 5 : 0;
            const score    = Math.min(100, Math.max(0, Math.round((base * 0.35) + (icp * 0.35) + rev + indBoost + roleBoost - agePen)));
            l._score       = score;
            l._grade       = score >= 80 ? 'A' : score >= 60 ? 'B' : score >= 40 ? 'C' : 'D';
            l._scoreColor  = score >= 80 ? 'var(--cr-grn)' : score >= 60 ? 'var(--cr-amb)' : score >= 40 ? 'var(--cr-sky)' : 'var(--cr-tx3)';
            return l;
        });

        // Score opportunities: velocity + value + probability ML simulation
        this.opportunities = this.opportunities.map(o => {
            const lastAct    = o.last_activity_date ? Math.ceil((today - new Date(o.last_activity_date)) / 86400000) : 99;
            const daysToClose= o.expected_close_date ? Math.ceil((new Date(o.expected_close_date) - today) / 86400000) : 30;
            const prob       = flt(o.probability);
            const value      = flt(o.opportunity_value);
            // Opportunity score: weighted probability + recency + value signal
            const recencyScore  = Math.max(0, 30 - (lastAct * 2));
            const probScore     = prob * 0.40;
            const valueScore    = value >= 5000000 ? 20 : value >= 1000000 ? 12 : value >= 100000 ? 6 : 2;
            const closePenalty  = daysToClose < 0 ? 15 : 0;
            const oScore        = Math.min(100, Math.max(0, Math.round(recencyScore + probScore + valueScore - closePenalty)));
            // Predicted close probability (Bayesian-style: prior=status-based, updated by recency)
            const statusPrior   = { 'New':0.20,'Prospecting':0.25,'Needs Analysis':0.35,'Value Proposition':0.45,'Identified Decision Makers':0.50,'Perception Analysis':0.55,'Proposal/Price Quote':0.65,'Negotiation/Review':0.75,'Won':1.0,'Lost':0.0,'Closed':1.0,'Suspended':0.05 };
            const prior         = statusPrior[o.status] || 0.30;
            const recencyLift   = lastAct <= 2 ? 0.08 : lastAct <= 7 ? 0 : lastAct <= 14 ? -0.05 : -0.15;
            const predictedProb = Math.min(0.99, Math.max(0.01, prior + recencyLift));
            o._score            = oScore;
            o._predictedProb    = Math.round(predictedProb * 100);
            o._urgency          = daysToClose < 7 ? 'high' : daysToClose < 14 ? 'med' : 'low';
            o._lastActDays      = lastAct;
            o._daysToClose      = daysToClose;
            o._grade            = oScore >= 75 ? 'A' : oScore >= 55 ? 'B' : oScore >= 35 ? 'C' : 'D';
            o._scoreColor       = oScore >= 75 ? 'var(--cr-grn)' : oScore >= 55 ? 'var(--cr-amb)' : oScore >= 35 ? 'var(--cr-sky)' : 'var(--cr-tx3)';
            return o;
        });
    }

    renderAll() {
        const newLeads   = this.leads.filter(l => l.status === 'New' || l.status === 'Open').length;
        const hotDeals   = this.deals.filter(d => d._urgency === 'high' || d._health >= 70).length;
        const openOpps   = this.opportunities.filter(o => !['Won','Lost','Closed','Suspended'].includes(o.status)).length;
        $('#cr-n-new').text(newLeads).toggle(newLeads > 0);
        $('#cr-n-hot').text(hotDeals).toggle(hotDeals > 0);
        $('#cr-n-opp').text(openOpps).toggle(openOpps > 0);

        const pipelineVal = this.deals.filter(d => d.stage !== 'Closed Won' && d.stage !== 'Closed Lost').reduce((s, d) => s + flt(d.deal_value), 0);
        $('#cr-chip-pipe').text(`${this.fmt(pipelineVal)} pipeline`);
        $('#cr-chip-leads').text(`${this.leads.length} leads`);

        // Alerts
        const alerts = [];
        const stale    = this.deals.filter(d => flt(d._lastActDays) > 7 && d.stage !== 'Closed Won' && d.stage !== 'Closed Lost').length;
        const overdue  = this.activities.filter(a => a.status !== 'Completed' && a.due_date && a.due_date < frappe.datetime.get_today()).length;
        const closing  = this.deals.filter(d => { const dDays = d.close_date ? Math.ceil((new Date(d.close_date) - new Date()) / 86400000) : 99; return dDays >= 0 && dDays <= 7 && d.stage !== 'Closed Won' && d.stage !== 'Closed Lost'; }).length;
        const expiring = this.leads.filter(l => l.status === 'New' && Math.ceil((new Date() - new Date(l.creation)) / 86400000) > 3).length;

        if (stale > 0)    alerts.push({ cls:'cr-a-amb', icon:'fa-clock-o',            label:`${stale} stale deal${stale>1?'s':''} — no activity 7+ days`, link:'/app/crm-deal' });
        if (overdue > 0)  alerts.push({ cls:'cr-a-red', icon:'fa-exclamation-circle',  label:`${overdue} overdue activit${overdue>1?'ies':'y'}`, link:'/app/crm-activity' });
        if (closing > 0)  alerts.push({ cls:'cr-a-grn', icon:'fa-trophy',              label:`${closing} deal${closing>1?'s':''} closing this week`, link:'/app/crm-deal' });
        if (expiring > 0) alerts.push({ cls:'cr-a-pur', icon:'fa-user',                label:`${expiring} new lead${expiring>1?'s':''} need first contact`, link:'/app/crm-lead' });

        $('#cr-alerts').html(alerts.map(a => `
            <a class="cr-alert ${a.cls}" href="${a.link}" target="_blank">
                <i class="fa ${a.icon}"></i> ${a.label}
            </a>`).join('') || '<div style="height:0"></div>');

        this.renderTab(this.activeTab);
    }

    renderTab(name) {
        const map = {
            myday:         () => this.renderMyDay(),
            pipeline:      () => this.renderPipeline(),
            leads:         () => this.renderLeads(),
            opportunities: () => this.renderOpportunities(),
            contacts:      () => this.renderContacts(),
            accounts:      () => this.renderAccounts(),
            activities:    () => this.renderActivities(),
            messaging:     () => this.renderMessaging(),
            ai:            () => this.renderAI(),
            reports:       () => this.renderReports(),
            actions:       () => this.renderActions(),
        };
        if (map[name]) map[name]();
    }

    // ─── TAB: MY DAY ─────────────────────────────────────────────────────────
    renderMyDay() {
        const today   = frappe.datetime.get_today();
        const todayActs = this.activities.filter(a => a.due_date === today && a.status !== 'Completed');
        const openDeals = this.deals.filter(d => d.stage !== 'Closed Won' && d.stage !== 'Closed Lost');
        const wonDeals  = this.deals.filter(d => d.stage === 'Closed Won');
        const pipeVal   = openDeals.reduce((s, d) => s + flt(d.deal_value), 0);
        const wonVal    = wonDeals.reduce((s, d) => s + flt(d.deal_value), 0);
        const myQuota   = this.quotas[0];
        const quotaPct  = myQuota ? Math.min(100, Math.round(flt(myQuota.achieved_value) / flt(myQuota.target_value) * 100)) : 0;

        // Next Best Action: find deal needing most urgent action
        const nbaDeals = openDeals.filter(d => flt(d._lastActDays) > 3).sort((a, b) => flt(b.deal_value) - flt(a.deal_value));
        const nbaDeal  = nbaDeals[0];

        $('#cr-panel-myday').html(`
            <div class="cr-kpis">
                ${this.kpi('🔀','kc-pri','Open Pipeline',   this.fmt(pipeVal),           `${openDeals.length} deals`, '/app/crm-deal')}
                ${this.kpi('✅','kc-grn','Closed Won',       this.fmt(wonVal),            `${wonDeals.length} deals`, '/app/crm-deal')}
                ${this.kpi('📋','kc-amb','Today\'s Tasks',  todayActs.length,             'Due today', '/app/crm-activity')}
                ${this.kpi('🎯','kc-sky','Leads',            this.leads.length,           `${this.leads.filter(l=>l.status==='New').length} new`, '/app/crm-lead')}
                ${this.kpi('💬','kc-pur','WA Threads',       this.waConvos.filter(w=>w.status==='Open').length, 'Open conversations', '/app/wa-conversation')}
                ${this.kpi('📞','kc-red','Calls Today',     this.calls.filter(c=>c.started_at&&c.started_at.startsWith(today)).length, 'Logged today', '/app/telephone-call-log')}
            </div>

            <div class="cr-g21">
                <div>
                    ${nbaDeal ? `
                    <div class="cr-nba">
                        <h4>🤖 NEXT BEST ACTION</h4>
                        <div class="cr-nba-title">${nbaDeal.deal_title || nbaDeal.name}</div>
                        <div class="cr-nba-meta">${this.fmt(nbaDeal.deal_value)} · ${nbaDeal.stage} · No activity for ${nbaDeal._lastActDays} days</div>
                        <button class="cr-nba-btn" onclick="frappe.set_route('Form','CRM Deal','${nbaDeal.name}')">Open Deal →</button>
                        <button class="cr-nba-btn" style="margin-left:6px" onclick="__crmDash.logCallDialog('${nbaDeal.name}')">📞 Log Call</button>
                    </div>` : ''}

                    <div class="cr-card cr-row">
                        <div class="cr-card-head">
                            <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-amb-x);color:var(--cr-amb)">📋</div> Today's Activities (${todayActs.length})</div>
                            <button class="cr-btn cb-solid" onclick="__crmDash.logActivityDialog()">+ Log Activity</button>
                        </div>
                        <div style="max-height:260px;overflow-y:auto">
                            ${todayActs.map(a => `
                            <div class="cr-activity" onclick="frappe.set_route('Form','CRM Activity','${a.name}')">
                                <div class="cr-act-icon" style="background:${this.actTypeColor(a.activity_type)}22;color:${this.actTypeColor(a.activity_type)}">${this.actTypeIcon(a.activity_type)}</div>
                                <div class="cr-act-body">
                                    <div class="cr-act-title">${a.subject || a.activity_type}</div>
                                    <div class="cr-act-meta">
                                        <span>${a.activity_type}</span>
                                        <span>${a.contact || a.lead || '—'}</span>
                                        ${a.due_date?`<span>${frappe.datetime.str_to_user(a.due_date)}</span>`:''}
                                        ${this.actStatusBadge(a.status)}
                                    </div>
                                </div>
                                <button class="cr-btn cb-ghost" style="padding:3px 9px;font-size:10px" onclick="event.stopPropagation();__crmDash.completeActivity('${a.name}')">Done</button>
                            </div>`).join('') || '<div class="cr-empty">No activities due today</div>'}
                        </div>
                    </div>

                    <div class="cr-card cr-row">
                        <div class="cr-card-head">
                            <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-red-x);color:var(--cr-red)">⚡</div> Deals Needing Action</div>
                            <button class="cr-btn cb-ghost" onclick="__crmDash.switchTab('pipeline')">Pipeline →</button>
                        </div>
                        <div style="max-height:240px;overflow-y:auto">
                            ${openDeals.filter(d => flt(d._lastActDays) > 5).slice(0, 6).map(d => `
                            <div class="cr-sched-slot" onclick="frappe.set_route('Form','CRM Deal','${d.name}')">
                                <div class="cr-sched-time" style="color:${d._urgency==='high'?'var(--cr-red)':'var(--cr-amb)'}">${d._lastActDays}d ago</div>
                                <div class="cr-sched-body">
                                    <div class="cr-sched-title">${d.deal_title||d.name}</div>
                                    <div class="cr-sched-meta">
                                        ${this.stageBadge(d.stage)}
                                        <span>${this.fmt(d.deal_value)}</span>
                                        <span>Health: <b>${d._health}</b></span>
                                    </div>
                                </div>
                                <button class="cr-btn cb-pri" style="font-size:10px;padding:4px 10px" onclick="event.stopPropagation();__crmDash.logCallDialog('${d.name}')">📞</button>
                            </div>`).join('') || '<div class="cr-empty">All deals have recent activity</div>'}
                        </div>
                    </div>
                </div>

                <div>
                    <div class="cr-card cr-row">
                        <div class="cr-card-head">
                            <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-grn-x);color:var(--cr-grn)">🎯</div> Quota Progress</div>
                        </div>
                        <div class="cr-card-body">
                            ${myQuota ? `
                            <div class="cr-quota-wrap">
                                <div class="cr-quota-ring">
                                    <svg width="100" height="100" viewBox="0 0 100 100">
                                        <circle cx="50" cy="50" r="42" fill="none" stroke="var(--cr-brd)" stroke-width="10"/>
                                        <circle cx="50" cy="50" r="42" fill="none"
                                            stroke="${quotaPct>=100?'var(--cr-grn)':quotaPct>=70?'var(--cr-pri)':'var(--cr-amb)'}"
                                            stroke-width="10"
                                            stroke-dasharray="${Math.round(quotaPct * 2.638)} 264"
                                            stroke-dashoffset="66"
                                            stroke-linecap="round"
                                            transform="rotate(-90 50 50)"/>
                                    </svg>
                                    <div class="cr-quota-label">
                                        <div class="cr-quota-pct">${quotaPct}%</div>
                                        <div class="cr-quota-sub">of target</div>
                                    </div>
                                </div>
                                <div class="cr-quota-stats">
                                    <div class="cr-quota-row"><span style="color:var(--cr-tx3)">Target</span><span style="font-weight:700">${this.fmt(myQuota.target_value)}</span></div>
                                    <div class="cr-quota-row"><span style="color:var(--cr-tx3)">Achieved</span><span style="font-weight:700;color:var(--cr-grn)">${this.fmt(myQuota.achieved_value)}</span></div>
                                    <div class="cr-quota-row"><span style="color:var(--cr-tx3)">Gap</span><span style="font-weight:700;color:var(--cr-amb)">${this.fmt(Math.max(0, flt(myQuota.target_value) - flt(myQuota.achieved_value)))}</span></div>
                                    <div class="cr-quota-row"><span style="color:var(--cr-tx3)">Period</span><span>${myQuota.period||'Q1'}</span></div>
                                </div>
                            </div>` : '<div class="cr-empty">No quota target set<br><a onclick="frappe.new_doc(\'CRM Quota Target\')" style="color:var(--cr-pri);cursor:pointer">Create quota target →</a></div>'}
                        </div>
                    </div>

                    <div class="cr-card cr-row">
                        <div class="cr-card-head">
                            <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-pur-x);color:var(--cr-pur)">🔥</div> Top Scored Leads</div>
                            <button class="cr-btn cb-ghost" onclick="__crmDash.switchTab('leads')">All Leads →</button>
                        </div>
                        <div class="cr-card-body" style="padding:10px">
                            ${this.leads.sort((a,b)=>b._score-a._score).slice(0,5).map(l=>`
                            <div class="cr-score-card" onclick="frappe.set_route('Form','CRM Lead','${l.name}')">
                                <div class="cr-score-num" style="background:${l._scoreColor}">${l._score}</div>
                                <div class="cr-score-body">
                                    <div class="cr-score-name">${l.lead_name || l.company_name || l.name}</div>
                                    <div class="cr-score-meta">
                                        <span>${l.industry||'—'}</span>
                                        <span>${this.leadStatusBadge(l.status)}</span>
                                        <span class="cr-badge bd-grey">ICP ${l._grade}</span>
                                    </div>
                                </div>
                            </div>`).join('') || '<div class="cr-empty">No leads yet</div>'}
                        </div>
                    </div>

                    <div class="cr-card">
                        <div class="cr-card-head">
                            <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-sky-x);color:var(--cr-sky)">💬</div> Recent WA Messages</div>
                            <button class="cr-btn cb-ghost" onclick="__crmDash.switchTab('messaging')">Inbox →</button>
                        </div>
                        <div style="max-height:220px;overflow-y:auto">
                            ${this.waConvos.slice(0,4).map(c=>`
                            <div class="cr-activity" onclick="frappe.set_route('Form','WA Conversation','${c.name}')">
                                <div class="cr-act-icon" style="background:#25D36622;color:#25D366">💬</div>
                                <div class="cr-act-body">
                                    <div class="cr-act-title">${c.contact_display_name||c.phone_number}</div>
                                    <div class="cr-act-meta">
                                        <span>${(c.last_message_preview||'').substring(0,50)}</span>
                                        <span>${c.last_message_at?frappe.datetime.prettyDate(c.last_message_at):''}</span>
                                        ${this.waBadge(c.status)}
                                    </div>
                                </div>
                            </div>`).join('') || '<div class="cr-empty">No WA conversations</div>'}
                        </div>
                    </div>
                </div>
            </div>
        `);
    }

    // ─── TAB: PIPELINE (Kanban) ───────────────────────────────────────────────
    renderPipeline() {
        const stages = ['Lead In','Qualified','Proposal Sent','Negotiation','Closed Won','Closed Lost'];

        const kanbanHTML = stages.map(stage => {
            const stageDeals = this.deals.filter(d => d.stage === stage);
            const stageVal   = stageDeals.reduce((s,d) => s + flt(d.deal_value), 0);
            const col        = STAGE_COLORS[stage] || 'var(--cr-pri)';
            return `
            <div class="cr-kb-col">
                <div class="cr-kb-head" style="background:${col}" onclick="frappe.set_route('List','CRM Deal','List',null,null,{stage:'${stage}'})">
                    <span>${stage}</span>
                    <span class="cr-kb-count">${stageDeals.length} · ${this.fmtK(stageVal)}</span>
                </div>
                <div class="cr-kb-body" data-stage="${stage}"
                    ondragover="event.preventDefault();this.classList.add('drag-over')"
                    ondragleave="this.classList.remove('drag-over')"
                    ondrop="__crmDash.handleDrop(event,'${stage}')">
                    ${stageDeals.map(d => this.kanbanCard(d, col)).join('')}
                    <div style="padding:6px 4px">
                        <button class="cr-btn cb-ghost" style="width:100%;justify-content:center;font-size:10px" onclick="frappe.new_doc('CRM Deal',{stage:'${stage}'})">+ Add Deal</button>
                    </div>
                </div>
            </div>`;
        }).join('');

        const pipeVal = this.deals.filter(d => !['Closed Won','Closed Lost'].includes(d.stage)).reduce((s,d)=>s+flt(d.deal_value),0);
        const wonVal  = this.deals.filter(d => d.stage==='Closed Won').reduce((s,d)=>s+flt(d.deal_value),0);
        const winRate = this.deals.filter(d=>['Closed Won','Closed Lost'].includes(d.stage)).length
            ? Math.round(this.deals.filter(d=>d.stage==='Closed Won').length / this.deals.filter(d=>['Closed Won','Closed Lost'].includes(d.stage)).length * 100)
            : 0;

        $('#cr-panel-pipeline').html(`
            <div class="cr-kpis" style="grid-template-columns:repeat(auto-fit,minmax(140px,1fr))">
                ${this.kpi('💼','kc-pri','Total Pipeline', this.fmt(pipeVal),       `${this.deals.filter(d=>!['Closed Won','Closed Lost'].includes(d.stage)).length} active`)}
                ${this.kpi('🏆','kc-grn','Won This Period',this.fmt(wonVal),        `${this.deals.filter(d=>d.stage==='Closed Won').length} deals`)}
                ${this.kpi('📊','kc-sky','Win Rate',       winRate+'%',             'Closed Won / (Won+Lost)')}
                ${this.kpi('⚡','kc-amb','Avg Deal Size',  this.fmt(pipeVal / Math.max(1, this.deals.filter(d=>!['Closed Won','Closed Lost'].includes(d.stage)).length)), 'Open deals')}
            </div>

            <div class="cr-card cr-row">
                <div class="cr-card-head">
                    <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-pri-x);color:var(--cr-pri)">🔀</div> Deal Pipeline — Drag to Move Stages</div>
                    <div class="cr-acts">
                        <button class="cr-btn cb-solid" onclick="frappe.new_doc('CRM Deal')">+ New Deal</button>
                        <button class="cr-btn cb-ghost" onclick="frappe.set_route('List','CRM Deal')">List View →</button>
                    </div>
                </div>
                <div class="cr-card-body" style="padding:14px;overflow-x:auto">
                    <div class="cr-kanban">${kanbanHTML}</div>
                </div>
            </div>
        `);
    }

    kanbanCard(d, stageColor) {
        const urgClass = d._urgency==='high' ? 'var(--cr-red)' : d._urgency==='med' ? 'var(--cr-amb)' : stageColor;
        const initials = (d.assigned_to||'?').split('@')[0].substring(0,2).toUpperCase();
        const healthColor = d._health>=70?'var(--cr-grn)':d._health>=40?'var(--cr-amb)':'var(--cr-red)';
        return `
        <div class="cr-kb-card" draggable="true"
            style="border-left:3px solid ${stageColor}"
            ondragstart="__crmDash.dragStart(event,'${d.name}')"
            ondragend="__crmDash.dragEnd(event)"
            onclick="frappe.set_route('Form','CRM Deal','${d.name}')">
            <div class="cr-kb-title">${d.deal_title||d.name}</div>
            <div class="cr-kb-meta">${d.account||d.contact||'—'}</div>
            <div class="cr-kb-value">${this.fmt(d.deal_value)}</div>
            <div class="cr-kb-footer">
                <div class="cr-kb-avatar" title="${d.assigned_to||'Unassigned'}">${initials}</div>
                <span style="font-size:10px;color:var(--cr-tx3)">${d.close_date?frappe.datetime.str_to_user(d.close_date):'No close date'}</span>
                <div style="display:flex;align-items:center;gap:4px">
                    <div style="width:28px;height:4px;background:var(--cr-brd);border-radius:4px;overflow:hidden">
                        <div style="width:${d._health}%;height:100%;background:${healthColor};transition:width .4s"></div>
                    </div>
                    <span style="font-size:9px;color:${healthColor};font-weight:700">${d._health}</span>
                </div>
            </div>
            ${d._urgency==='high'?`<div style="position:absolute;top:8px;right:8px;font-size:10px">🔥</div>`:''}
        </div>`;
    }

    dragStart(e, name)  { e.dataTransfer.setData('text/plain', name); e.target.classList.add('dragging'); }
    dragEnd(e)          { e.target.classList.remove('dragging'); document.querySelectorAll('.cr-kb-body').forEach(b=>b.classList.remove('drag-over')); }

    handleDrop(e, newStage) {
        e.preventDefault();
        e.currentTarget.classList.remove('drag-over');
        const name = e.dataTransfer.getData('text/plain');
        if (!name) return;
        frappe.call({
            method: 'frappe.client.set_value',
            args:   { doctype: 'CRM Deal', name, fieldname: { stage: newStage } },
            callback: () => {
                frappe.show_alert({ message: `Deal moved to ${newStage}`, indicator: 'green' });
                this.loadData(true);
            }
        });
    }

    // ─── TAB: LEADS ───────────────────────────────────────────────────────────
    renderLeads() {
        const leads = this.leads;
        const byStatus = {};
        leads.forEach(l => { byStatus[l.status] = (byStatus[l.status]||0)+1; });

        $('#cr-panel-leads').html(`
            <div class="cr-g21">
                <div>
                    <div class="cr-card cr-row">
                        <div class="cr-card-head">
                            <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-pri-x);color:var(--cr-pri)">🎯</div> All Leads (${leads.length})</div>
                            <div class="cr-acts">
                                <button class="cr-btn cb-solid" onclick="frappe.new_doc('CRM Lead')">+ New Lead</button>
                                <button class="cr-btn cb-pur" onclick="frappe.set_route('List','CRM Lead','List',null,null,{status:'New'})">📥 New Only</button>
                                <button class="cr-btn cb-ghost" onclick="frappe.set_route('List','CRM Lead')">List View →</button>
                            </div>
                        </div>
                        <div class="cr-tbl-wrap">
                            <table class="cr-tbl">
                                <thead><tr>
                                    <th>AI Score</th><th>Name</th><th>Company</th><th>Status</th>
                                    <th>Source</th><th>Industry</th>
                                    <th class="tr">Revenue</th><th>Assigned</th><th>Age</th><th>Action</th>
                                </tr></thead>
                                <tbody>
                                    ${leads.map(l => {
                                        const ageDays = l.creation ? Math.ceil((new Date()-new Date(l.creation))/86400000) : 0;
                                        const ageColor = ageDays > 14 ? 'var(--cr-red)' : ageDays > 7 ? 'var(--cr-amb)' : 'var(--cr-tx3)';
                                        return `
                                        <tr onclick="frappe.set_route('Form','CRM Lead','${l.name}')">
                                            <td>
                                                <div style="display:flex;align-items:center;gap:6px">
                                                    <div style="width:32px;height:32px;border-radius:8px;background:${l._scoreColor};display:flex;align-items:center;justify-content:center;color:#fff;font-size:11px;font-weight:800">${l._score}</div>
                                                    <span class="cr-badge bd-grey">${l._grade}</span>
                                                </div>
                                            </td>
                                            <td style="font-weight:600;color:var(--cr-tx1)">
                                                <div>${l.lead_name||'—'}</div>
                                                <div style="font-size:10px;color:var(--cr-tx3)">${l.email||l.mobile_no||''}</div>
                                            </td>
                                            <td>
                                                <div>${l.company_name||'—'}</div>
                                                <div style="font-size:10px;color:var(--cr-tx3)">${l.job_title||''}</div>
                                            </td>
                                            <td>${this.leadStatusBadge(l.status)}</td>
                                            <td style="font-size:11px">${l.lead_source||'—'}</td>
                                            <td style="font-size:11px">${l.industry||'—'}</td>
                                            <td class="tr">${flt(l.annual_revenue)>0?this.fmtK(l.annual_revenue):'—'}</td>
                                            <td style="font-size:11px">${(l.assigned_to||'').split('@')[0]||'—'}</td>
                                            <td style="font-size:11px;color:${ageColor};font-weight:700">${ageDays}d</td>
                                            <td onclick="event.stopPropagation()">
                                                ${l.status!=='Converted' ? `
                                                <button class="cr-btn cb-pri" style="font-size:10px;padding:3px 8px;white-space:nowrap"
                                                    onclick="__crmDash.convertLeadToOpp('${l.name}','${(l.lead_name||'').replace(/'/g,"\\'")}','${(l.company_name||'').replace(/'/g,"\\'")}')">
                                                    → Opportunity
                                                </button>` : '<span class="cr-badge bd-grn">Converted</span>'}
                                            </td>
                                        </tr>`;
                                    }).join('')}
                                </tbody>
                            </table>
                            ${!leads.length?'<div class="cr-empty">No leads found. Create your first lead with the button above.</div>':''}
                        </div>
                    </div>
                </div>
                <div>
                    <div class="cr-card cr-row">
                        <div class="cr-card-head">
                            <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-pur-x);color:var(--cr-pur)">📊</div> Lead Status Mix</div>
                        </div>
                        <div class="cr-card-body">
                            ${Object.entries(byStatus).map(([s,n])=>`
                            <div class="cr-bar-row">
                                <div class="cr-bar-lbl">${this.leadStatusBadge(s)}</div>
                                <div class="cr-bar"><div class="cr-bar-fill" style="width:${Math.round(n/leads.length*100)||0}%;background:var(--cr-pri)"></div></div>
                                <div class="cr-bar-val">${n}</div>
                            </div>`).join('') || '<div class="cr-empty">No data</div>'}
                        </div>
                    </div>
                    <div class="cr-card cr-row">
                        <div class="cr-card-head">
                            <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-grn-x);color:var(--cr-grn)">🏆</div> Top Scored Leads</div>
                        </div>
                        <div class="cr-card-body" style="padding:10px">
                            ${this.leads.sort((a,b)=>b._score-a._score).slice(0,6).map(l=>`
                            <div class="cr-score-card" onclick="frappe.set_route('Form','CRM Lead','${l.name}')">
                                <div class="cr-score-num" style="background:${l._scoreColor}">${l._score}</div>
                                <div class="cr-score-body">
                                    <div class="cr-score-name">${l.lead_name||l.company_name||'—'}</div>
                                    <div class="cr-score-meta">
                                        <span>${l.industry||'—'}</span>
                                        <span class="cr-badge bd-grey">ICP ${l._grade}</span>
                                        ${flt(l.annual_revenue)>0?`<span>${this.fmtK(l.annual_revenue)}</span>`:''}
                                    </div>
                                </div>
                            </div>`).join('')}
                        </div>
                    </div>
                    <div class="cr-card">
                        <div class="cr-card-head">
                            <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-sky-x);color:var(--cr-sky)">🌐</div> By Source</div>
                        </div>
                        <div class="cr-card-body">
                            <div style="height:160px;position:relative"><canvas id="cr-ch-lead-source"></canvas></div>
                        </div>
                    </div>
                </div>
            </div>
        `);

        // Source doughnut
        const srcData = {};
        leads.forEach(l=>{ srcData[l.lead_source||'Unknown']=(srcData[l.lead_source||'Unknown']||0)+1; });
        const srcE = Object.entries(srcData).sort((a,b)=>b[1]-a[1]).slice(0,6);
        this.mkChart('cr-ch-lead-source', {
            type:'doughnut',
            data:{ labels:srcE.map(([s])=>s), datasets:[{ data:srcE.map(([,n])=>n), backgroundColor:['#2563EB','#10B981','#F59E0B','#8B5CF6','#06B6D4','#EF4444'], borderWidth:0 }] },
            options:{ cutout:'60%', responsive:true, maintainAspectRatio:false, plugins:{ legend:{ position:'right', labels:{ boxWidth:10, font:{ size:10 } } } } }
        });
    }

    // ─── CONVERT LEAD → OPPORTUNITY DIALOG ───────────────────────────────────
    convertLeadToOpp(leadName, leadNameText, company) {
        const d = new frappe.ui.Dialog({
            title: '💼 Convert Lead to Opportunity',
            size: 'large',
            fields: [
                { fieldtype:'Section Break', label:'Opportunity Details' },
                { fieldtype:'Data',     fieldname:'opportunity_title',  label:'Opportunity Title', reqd:1,
                  default: `${company||leadNameText} — Opportunity` },
                { fieldtype:'Currency', fieldname:'opportunity_value',  label:'Estimated Value (₦)', reqd:1 },
                { fieldtype:'Column Break' },
                { fieldtype:'Select',   fieldname:'status',             label:'Initial Status', default:'Needs Analysis',
                  options:'Prospecting\nNeeds Analysis\nValue Proposition\nIdentified Decision Makers\nPerception Analysis\nProposal/Price Quote\nNegotiation/Review' },
                { fieldtype:'Percent',  fieldname:'probability',        label:'Win Probability %', default:30 },
                { fieldtype:'Date',     fieldname:'expected_close_date',label:'Expected Close Date', reqd:1 },
                { fieldtype:'Section Break', label:'Assignment' },
                { fieldtype:'Link',     fieldname:'assigned_to',        label:'Assign To', options:'User' },
                { fieldtype:'Link',     fieldname:'territory',          label:'Territory',  options:'CRM Territory' },
                { fieldtype:'Link',     fieldname:'source',             label:'Source',     options:'CRM Source' },
                { fieldtype:'Section Break', label:'Notes' },
                { fieldtype:'Small Text', fieldname:'next_step',        label:'Agreed Next Step' },
            ],
            primary_action_label: '✅ Create Opportunity',
            primary_action: (vals) => {
                frappe.call({
                    method: 'broker.broker.page.crm_dashboard.crm_dashboard.convert_lead_to_opportunity',
                    args:   { lead_name: leadName, ...vals },
                    callback: (r) => {
                        d.hide();
                        if (r.message && r.message.opportunity) {
                            frappe.show_alert({ message:`Opportunity created: ${r.message.opportunity}`, indicator:'green' });
                            frappe.set_route('Form', 'CRM Opportunity', r.message.opportunity);
                            this.loadData(true);
                        }
                    }
                });
            }
        });
        d.show();
    }

    // ─── OPPORTUNITY → DEAL CONVERSION DIALOG ────────────────────────────────
    oppToDealDialog(oppName, oppTitle, oppValue) {
        const d = new frappe.ui.Dialog({
            title: '🔀 Promote Opportunity to Deal',
            fields: [
                { fieldtype:'Data',     fieldname:'deal_title', label:'Deal Title', reqd:1, default: oppTitle },
                { fieldtype:'Currency', fieldname:'deal_value', label:'Deal Value (₦)', reqd:1, default: oppValue },
                { fieldtype:'Column Break' },
                { fieldtype:'Select',   fieldname:'stage', label:'Initial Stage', default:'Qualified',
                  options:'Lead In\nQualified\nProposal Sent\nNegotiation' },
                { fieldtype:'Date',     fieldname:'close_date', label:'Close Date', reqd:1 },
                { fieldtype:'Link',     fieldname:'pipeline',   label:'Pipeline', options:'CRM Pipeline' },
            ],
            primary_action_label: '🔀 Create Deal',
            primary_action: (vals) => {
                frappe.call({
                    method: 'broker.broker.page.crm_dashboard.crm_dashboard.promote_opportunity_to_deal',
                    args:   { opportunity_name: oppName, ...vals },
                    callback: (r) => {
                        d.hide();
                        if (r.message && r.message.deal) {
                            frappe.show_alert({ message:`Deal created!`, indicator:'green' });
                            frappe.set_route('Form', 'CRM Deal', r.message.deal);
                            this.loadData(true);
                        }
                    }
                });
            }
        });
        d.show();
    }

    // ─── TAB: OPPORTUNITIES ───────────────────────────────────────────────────
    renderOpportunities() {
        const opps = this.opportunities;
        const open = opps.filter(o => !['Won','Lost','Closed','Suspended'].includes(o.status));
        const wonOpps = opps.filter(o => o.status === 'Won');
        const totalPipeline = open.reduce((s,o)=>s+flt(o.opportunity_value),0);
        const weightedPipe  = open.reduce((s,o)=>s+flt(o.opportunity_value)*flt(o._predictedProb)/100,0);

        $('#cr-panel-opportunities').html(`
            <div class="cr-kpis">
                ${this.kpi('💼','kc-pri','Open Opportunities', open.length, `${this.fmt(totalPipeline)} pipeline`)}
                ${this.kpi('🎯','kc-pur','Weighted Pipeline',  this.fmt(weightedPipe), 'AI predicted value')}
                ${this.kpi('🏆','kc-grn','Won',                wonOpps.length, this.fmt(wonOpps.reduce((s,o)=>s+flt(o.opportunity_value),0)))}
                ${this.kpi('⚡','kc-amb','High Urgency',        open.filter(o=>o._urgency==='high').length, 'Closing < 7 days')}
            </div>

            <div class="cr-g21">
                <div class="cr-card cr-row">
                    <div class="cr-card-head">
                        <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-pur-x);color:var(--cr-pur)">💼</div> All Opportunities (${opps.length})</div>
                        <div class="cr-acts">
                            <button class="cr-btn cb-solid" onclick="frappe.new_doc('CRM Opportunity')">+ New Opportunity</button>
                            <button class="cr-btn cb-ghost" onclick="frappe.set_route('List','CRM Opportunity')">List View →</button>
                        </div>
                    </div>
                    <div class="cr-tbl-wrap">
                        <table class="cr-tbl">
                            <thead><tr>
                                <th>AI Score</th><th>Title</th><th>Account</th><th>Status</th>
                                <th class="tr">Value</th><th>AI Win%</th><th>Close Date</th>
                                <th>Rep</th><th>Action</th>
                            </tr></thead>
                            <tbody>
                                ${opps.map(o => {
                                    const urgColor = o._urgency==='high'?'var(--cr-red)':o._urgency==='med'?'var(--cr-amb)':'var(--cr-tx3)';
                                    return `
                                    <tr onclick="frappe.set_route('Form','CRM Opportunity','${o.name}')">
                                        <td>
                                            <div style="display:flex;align-items:center;gap:6px">
                                                <div style="width:32px;height:32px;border-radius:8px;background:${o._scoreColor};display:flex;align-items:center;justify-content:center;color:#fff;font-size:11px;font-weight:800">${o._score}</div>
                                                <span class="cr-badge bd-grey">${o._grade}</span>
                                            </div>
                                        </td>
                                        <td style="font-weight:600;color:var(--cr-tx1)">
                                            <div>${o.opportunity_title||o.name}</div>
                                            <div style="font-size:10px;color:var(--cr-tx3)">${o.contact||o.account||''}</div>
                                        </td>
                                        <td style="font-size:11px">${o.account||'—'}</td>
                                        <td>${this.oppStatusBadge(o.status)}</td>
                                        <td class="tr" style="font-weight:700">${this.fmt(o.opportunity_value)}</td>
                                        <td class="tr">
                                            <div style="display:flex;align-items:center;gap:6px;justify-content:flex-end">
                                                <div style="width:36px;height:4px;background:var(--cr-brd);border-radius:4px;overflow:hidden">
                                                    <div style="width:${o._predictedProb}%;height:100%;background:${o._scoreColor}"></div>
                                                </div>
                                                <span style="font-size:11px;font-weight:700;color:${o._scoreColor}">${o._predictedProb}%</span>
                                            </div>
                                        </td>
                                        <td style="font-size:11px;color:${urgColor}">
                                            ${o.expected_close_date?frappe.datetime.str_to_user(o.expected_close_date):'—'}
                                            ${o._urgency==='high'?'🔥':o._urgency==='med'?'⚡':''}
                                        </td>
                                        <td style="font-size:11px">${(o.assigned_to||'').split('@')[0]||'—'}</td>
                                        <td onclick="event.stopPropagation()">
                                            ${!['Won','Lost','Closed'].includes(o.status) ? `
                                            <button class="cr-btn cb-grn" style="font-size:10px;padding:3px 8px;white-space:nowrap"
                                                onclick="__crmDash.oppToDealDialog('${o.name}','${(o.opportunity_title||'').replace(/'/g,"\\'")}',${flt(o.opportunity_value)})">
                                                → Deal
                                            </button>` : ''}
                                        </td>
                                    </tr>`;
                                }).join('')}
                            </tbody>
                        </table>
                        ${!opps.length?'<div class="cr-empty">No opportunities yet. Convert a Lead to create your first opportunity.</div>':''}
                    </div>
                </div>
                <div>
                    <div class="cr-card cr-row">
                        <div class="cr-card-head">
                            <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-sky-x);color:var(--cr-sky)">📊</div> Status Breakdown</div>
                        </div>
                        <div class="cr-card-body">
                            <div style="height:160px;position:relative"><canvas id="cr-ch-opp-status"></canvas></div>
                        </div>
                    </div>
                    <div class="cr-card cr-row">
                        <div class="cr-card-head">
                            <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-amb-x);color:var(--cr-amb)">⚡</div> Urgent — Closing Soon</div>
                        </div>
                        <div class="cr-card-body" style="padding:0">
                            ${open.filter(o=>o._urgency!=='low').sort((a,b)=>flt(b.opportunity_value)-flt(a.opportunity_value)).slice(0,5).map(o=>`
                            <div class="cr-sched-slot" onclick="frappe.set_route('Form','CRM Opportunity','${o.name}')">
                                <div class="cr-sched-time" style="color:${o._urgency==='high'?'var(--cr-red)':'var(--cr-amb)'}">${o._daysToClose<0?'Overdue':o._daysToClose+'d'}</div>
                                <div class="cr-sched-body">
                                    <div class="cr-sched-title">${o.opportunity_title||o.name}</div>
                                    <div class="cr-sched-meta">
                                        <span style="font-weight:700">${this.fmt(o.opportunity_value)}</span>
                                        <span>${o._predictedProb}% AI win prob</span>
                                    </div>
                                </div>
                                <button class="cr-btn cb-grn" style="font-size:10px;padding:3px 8px" onclick="event.stopPropagation();__crmDash.oppToDealDialog('${o.name}','${(o.opportunity_title||'').replace(/'/g,"\\'")}',${flt(o.opportunity_value)})">→ Deal</button>
                            </div>`).join('') || '<div class="cr-empty" style="padding:14px">No urgent opportunities</div>'}
                        </div>
                    </div>
                    <div class="cr-card">
                        <div class="cr-card-head">
                            <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-pur-x);color:var(--cr-pur)">🤖</div> AI Insight</div>
                        </div>
                        <div class="cr-card-body">
                            <div class="cr-ai-card">
                                <h4>Predicted Win Probability Model</h4>
                                <div class="cr-ai-item"><div class="cr-ai-bullet"></div>Based on status stage prior + activity recency lift/penalty (Bayesian update)</div>
                                <div class="cr-ai-item"><div class="cr-ai-bullet"></div>Weighted pipeline = ₦${this.fmtK(weightedPipe)} of ₦${this.fmtK(totalPipeline)} total</div>
                                <div class="cr-ai-item"><div class="cr-ai-bullet"></div>${open.filter(o=>o._lastActDays>7).length} opportunities have gone silent — engage before they go cold</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `);

        // Opp status doughnut
        const statData = {};
        opps.forEach(o=>{ statData[o.status||'Unknown']=(statData[o.status||'Unknown']||0)+1; });
        const statE = Object.entries(statData).sort((a,b)=>b[1]-a[1]);
        this.mkChart('cr-ch-opp-status', {
            type:'doughnut',
            data:{ labels:statE.map(([s])=>s), datasets:[{ data:statE.map(([,n])=>n), backgroundColor:['#8B5CF6','#2563EB','#06B6D4','#F59E0B','#10B981','#EF4444','#94A3B8'], borderWidth:0 }] },
            options:{ cutout:'60%', responsive:true, maintainAspectRatio:false, plugins:{ legend:{ position:'right', labels:{ boxWidth:10, font:{ size:10 } } } } }
        });
    }

    // ─── TAB: CONTACTS ────────────────────────────────────────────────────────
    renderContacts() {
        const contacts = this.contacts;
        $('#cr-panel-contacts').html(`
            <div class="cr-g21">
                <div class="cr-card cr-row">
                    <div class="cr-card-head">
                        <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-sky-x);color:var(--cr-sky)">👥</div> All Contacts (${contacts.length})</div>
                        <div class="cr-acts">
                            <button class="cr-btn cb-solid" onclick="frappe.new_doc('CRM Contact')">+ New Contact</button>
                            <button class="cr-btn cb-ghost" onclick="frappe.set_route('List','CRM Contact')">Open List →</button>
                        </div>
                    </div>
                    <div class="cr-tbl-wrap">
                        <table class="cr-tbl">
                            <thead><tr>
                                <th>Name</th><th>Company</th><th>Job Title</th>
                                <th>Email</th><th>Mobile</th><th>Account</th>
                                <th>Assigned</th><th>Added</th>
                            </tr></thead>
                            <tbody>
                                ${contacts.map(c=>`
                                <tr onclick="frappe.set_route('Form','CRM Contact','${c.name}')">
                                    <td>
                                        <div style="display:flex;align-items:center;gap:8px">
                                            <div style="width:28px;height:28px;border-radius:50%;background:var(--cr-pri);color:#fff;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;flex-shrink:0">${(c.full_name||'?').split(' ').map(w=>w[0]).join('').substring(0,2).toUpperCase()}</div>
                                            <span style="font-weight:600;color:var(--cr-tx1)">${c.full_name||'—'}</span>
                                        </div>
                                    </td>
                                    <td>${c.company_name||'—'}</td>
                                    <td style="font-size:11px">${c.job_title||'—'}</td>
                                    <td style="font-size:11px">${c.email||'—'}</td>
                                    <td style="font-size:11px">${c.mobile_no||'—'}</td>
                                    <td style="font-size:11px">${c.account||'—'}</td>
                                    <td style="font-size:11px">${(c.assigned_to||'').split('@')[0]||'—'}</td>
                                    <td style="font-size:11px;color:var(--cr-tx3)">${c.creation?frappe.datetime.prettyDate(c.creation):''}</td>
                                </tr>`).join('')}
                            </tbody>
                        </table>
                        ${!contacts.length?'<div class="cr-empty">No contacts yet. Contacts are created automatically when converting a Lead to an Opportunity.</div>':''}
                    </div>
                </div>
                <div>
                    <div class="cr-card cr-row">
                        <div class="cr-card-head">
                            <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-pur-x);color:var(--cr-pur)">🤖</div> AI Contact Intelligence</div>
                        </div>
                        <div class="cr-card-body">
                            <div class="cr-ai-card">
                                <h4>Engagement Scoring</h4>
                                <div class="cr-ai-item"><div class="cr-ai-bullet"></div>Contacts ranked by: call response rate, WA reply rate, email open rate, meeting attendance</div>
                                <div class="cr-ai-item"><div class="cr-ai-bullet"></div>Staleness alert: ${this.contacts.filter(c=>c.modified&&Math.ceil((new Date()-new Date(c.modified))/86400000)>30).length} contacts not touched in 30+ days</div>
                                <div class="cr-ai-item"><div class="cr-ai-bullet"></div>Duplicate risk: phone + email fuzzy matching on save prevents double entries</div>
                            </div>
                            <div class="cr-ai-card" style="background:var(--cr-grn-x);border-color:rgba(16,185,129,.2)">
                                <h4 style="color:var(--cr-grn)">360° Timeline</h4>
                                <div class="cr-ai-item"><div class="cr-ai-bullet" style="background:var(--cr-grn)"></div>Open any contact to see all their calls, WA messages, meetings, deals, and invoices in one timeline</div>
                                <div class="cr-ai-item"><div class="cr-ai-bullet" style="background:var(--cr-grn)"></div>LinkedIn enrichment: save LinkedIn URL on contact → auto-populate company size, industry, seniority</div>
                            </div>
                            <div style="display:flex;gap:8px;margin-top:12px">
                                <button class="cr-btn cb-solid" style="flex:1;justify-content:center" onclick="frappe.new_doc('CRM Contact')">+ New Contact</button>
                                <button class="cr-btn cb-ghost" style="flex:1;justify-content:center" onclick="frappe.set_route('List','CRM Contact')">View All →</button>
                            </div>
                        </div>
                    </div>
                    <div class="cr-card">
                        <div class="cr-card-head">
                            <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-sky-x);color:var(--cr-sky)">📊</div> By Company</div>
                        </div>
                        <div class="cr-card-body">
                            ${(() => {
                                const byComp = {};
                                contacts.forEach(c=>{ byComp[c.company_name||'Unknown']=(byComp[c.company_name||'Unknown']||0)+1; });
                                const entries = Object.entries(byComp).sort((a,b)=>b[1]-a[1]).slice(0,6);
                                return entries.map(([co,n])=>`
                                <div class="cr-bar-row">
                                    <div class="cr-bar-lbl" style="width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${co}</div>
                                    <div class="cr-bar"><div class="cr-bar-fill" style="width:${entries[0]?Math.round(n/entries[0][1]*100):0}%;background:var(--cr-sky)"></div></div>
                                    <div class="cr-bar-val">${n}</div>
                                </div>`).join('') || '<div class="cr-empty">No data</div>';
                            })()}
                        </div>
                    </div>
                </div>
            </div>
        `);
    }

    // ─── TAB: ACCOUNTS ────────────────────────────────────────────────────────
    renderAccounts() {
        const accounts = this.accounts;
        $('#cr-panel-accounts').html(`
            <div class="cr-g21">
                <div class="cr-card cr-row">
                    <div class="cr-card-head">
                        <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-grn-x);color:var(--cr-grn)">🏢</div> All Accounts (${accounts.length})</div>
                        <div class="cr-acts">
                            <button class="cr-btn cb-solid" onclick="frappe.new_doc('CRM Account')">+ New Account</button>
                            <button class="cr-btn cb-ghost" onclick="frappe.set_route('List','CRM Account')">Open List →</button>
                        </div>
                    </div>
                    <div class="cr-tbl-wrap">
                        <table class="cr-tbl">
                            <thead><tr>
                                <th>Account</th><th>Industry</th>
                                <th class="tr">Revenue</th><th>Territory</th>
                                <th>Manager</th><th>ERPNext Link</th><th>Open Deals</th>
                            </tr></thead>
                            <tbody>
                                ${accounts.map(a => {
                                    const accDeals = this.deals.filter(d => d.account===a.account_name && !['Closed Won','Closed Lost'].includes(d.stage));
                                    const accPipeline = accDeals.reduce((s,d)=>s+flt(d.deal_value),0);
                                    return `
                                    <tr onclick="frappe.set_route('Form','CRM Account','${a.name}')">
                                        <td>
                                            <div style="display:flex;align-items:center;gap:8px">
                                                <div style="width:30px;height:30px;border-radius:8px;background:var(--cr-grn-x);color:var(--cr-grn);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;flex-shrink:0">🏢</div>
                                                <span style="font-weight:600;color:var(--cr-tx1)">${a.account_name}</span>
                                            </div>
                                        </td>
                                        <td style="font-size:11px">${a.industry||'—'}</td>
                                        <td class="tr">${flt(a.annual_revenue)>0?this.fmtK(a.annual_revenue):'—'}</td>
                                        <td style="font-size:11px">${a.territory||'—'}</td>
                                        <td style="font-size:11px">${(a.assigned_to||'').split('@')[0]||'—'}</td>
                                        <td>
                                            ${a.erpnext_customer
                                                ? `<span class="cr-badge bd-grn">✓ Linked</span>`
                                                : `<span class="cr-badge bd-grey">Not linked</span>`}
                                        </td>
                                        <td class="tr">
                                            ${accDeals.length > 0
                                                ? `<span class="cr-badge bd-pri">${accDeals.length} · ${this.fmtK(accPipeline)}</span>`
                                                : `<span style="font-size:11px;color:var(--cr-tx3)">—</span>`}
                                        </td>
                                    </tr>`;
                                }).join('')}
                            </tbody>
                        </table>
                        ${!accounts.length?'<div class="cr-empty">No accounts yet. Accounts are linked to Deals and ERPNext Customers.</div>':''}
                    </div>
                </div>
                <div>
                    <div class="cr-card cr-row">
                        <div class="cr-card-head">
                            <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-grn-x);color:var(--cr-grn)">💡</div> Account Intelligence</div>
                        </div>
                        <div class="cr-card-body">
                            <div class="cr-ai-card" style="background:var(--cr-grn-x);border-color:rgba(16,185,129,.2)">
                                <h4 style="color:var(--cr-grn)">ERPNext Financial Bridge</h4>
                                <div class="cr-ai-item"><div class="cr-ai-bullet" style="background:var(--cr-grn)"></div>${accounts.filter(a=>a.erpnext_customer).length} of ${accounts.length} accounts linked to ERPNext customers — AR aging visible natively</div>
                                <div class="cr-ai-item"><div class="cr-ai-bullet" style="background:var(--cr-grn)"></div>Upsell signal: accounts with recent invoice payments and zero open deals = top expansion targets</div>
                                <div class="cr-ai-item"><div class="cr-ai-bullet" style="background:var(--cr-grn)"></div>This bridges Salesforce's biggest gap — your financial data and CRM are in the same database</div>
                            </div>
                            <div class="cr-ai-card">
                                <h4>Account Health Model</h4>
                                <div class="cr-ai-item"><div class="cr-ai-bullet"></div>Health = Deal pipeline + payment history + recency of last contact + no. of contacts on file</div>
                                <div class="cr-ai-item"><div class="cr-ai-bullet"></div>${this.deals.filter(d=>!['Closed Won','Closed Lost'].includes(d.stage)).length} open deals across ${[...new Set(this.deals.map(d=>d.account).filter(Boolean))].length} accounts</div>
                            </div>
                        </div>
                    </div>
                    <div class="cr-card">
                        <div class="cr-card-head">
                            <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-sky-x);color:var(--cr-sky)">📊</div> By Industry</div>
                        </div>
                        <div class="cr-card-body">
                            ${(() => {
                                const byInd = {};
                                accounts.forEach(a=>{ byInd[a.industry||'Unknown']=(byInd[a.industry||'Unknown']||0)+1; });
                                const entries = Object.entries(byInd).sort((a,b)=>b[1]-a[1]).slice(0,6);
                                return entries.map(([ind,n])=>`
                                <div class="cr-bar-row">
                                    <div class="cr-bar-lbl">${ind}</div>
                                    <div class="cr-bar"><div class="cr-bar-fill" style="width:${entries[0]?Math.round(n/entries[0][1]*100):0}%;background:var(--cr-grn)"></div></div>
                                    <div class="cr-bar-val">${n}</div>
                                </div>`).join('') || '<div class="cr-empty">No data</div>';
                            })()}
                        </div>
                    </div>
                </div>
            </div>
        `);
    }

    // ─── TAB: ACTIVITIES ──────────────────────────────────────────────────────
    renderActivities() {
        const today   = frappe.datetime.get_today();
        const overdue = this.activities.filter(a => a.status !== 'Completed' && a.due_date && a.due_date < today);
        const todayA  = this.activities.filter(a => a.due_date === today);
        const upcomingA = this.activities.filter(a => a.due_date > today);
        const recentCalls = this.calls.slice(0, 10);

        $('#cr-panel-activities').html(`
            <div class="cr-kpis">
                ${this.kpi('🔴','kc-red','Overdue',      overdue.length, 'Need attention', '/app/crm-activity')}
                ${this.kpi('📅','kc-amb','Due Today',    todayA.length,  'Today\'s tasks', '')}
                ${this.kpi('📋','kc-sky','Upcoming',     upcomingA.length,'Future activities','')}
                ${this.kpi('📞','kc-grn','Calls Logged', this.calls.length,'All calls','/app/telephone-call-log')}
            </div>

            <div class="cr-g21">
                <div class="cr-card cr-row">
                    <div class="cr-card-head">
                        <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-amb-x);color:var(--cr-amb)">📋</div> All Activities (${this.activities.length})</div>
                        <div class="cr-acts">
                            <button class="cr-btn cb-solid" onclick="__crmDash.logActivityDialog()">+ Log Activity</button>
                            <button class="cr-btn cb-ghost" onclick="frappe.set_route('List','CRM Activity')">List View →</button>
                        </div>
                    </div>
                    <div class="cr-tbl-wrap">
                        <table class="cr-tbl">
                            <thead><tr><th>Type</th><th>Subject</th><th>Contact / Lead</th><th>Deal</th><th>Due</th><th>Status</th><th>Outcome</th></tr></thead>
                            <tbody>
                                ${this.activities.slice(0,30).map(a=>`
                                <tr onclick="frappe.set_route('Form','CRM Activity','${a.name}')">
                                    <td><div style="display:flex;align-items:center;gap:5px"><span style="font-size:14px">${this.actTypeIcon(a.activity_type)}</span>${a.activity_type}</div></td>
                                    <td style="font-weight:600;max-width:180px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${a.subject||'—'}</td>
                                    <td>${a.contact||a.lead||'—'}</td>
                                    <td style="font-size:11px">${a.deal||'—'}</td>
                                    <td style="font-size:11px;color:${a.due_date<today&&a.status!=='Completed'?'var(--cr-red)':'var(--cr-tx3)'}">${a.due_date?frappe.datetime.str_to_user(a.due_date):'—'}</td>
                                    <td>${this.actStatusBadge(a.status)}</td>
                                    <td style="font-size:11px;max-width:140px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${a.outcome||'—'}</td>
                                </tr>`).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
                <div>
                    <div class="cr-card cr-row">
                        <div class="cr-card-head">
                            <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-grn-x);color:var(--cr-grn)">📞</div> Recent Calls</div>
                            <button class="cr-btn cb-ghost" onclick="__crmDash.logCallDialog()">+ Log Call</button>
                        </div>
                        <div style="max-height:300px;overflow-y:auto">
                            ${recentCalls.map(c=>`
                            <div class="cr-activity" onclick="frappe.set_route('Form','Telephone Call Log','${c.name}')">
                                <div class="cr-act-icon" style="background:${c.direction==='Inbound'?'var(--cr-grn-x)':'var(--cr-pri-x)'};color:${c.direction==='Inbound'?'var(--cr-grn)':'var(--cr-pri)'}">
                                    ${c.direction==='Inbound'?'📲':'📞'}
                                </div>
                                <div class="cr-act-body">
                                    <div class="cr-act-title">${c.direction} — ${c.caller_name||c.receiver_name||'Unknown'}</div>
                                    <div class="cr-act-meta">
                                        <span>${c.status}</span>
                                        ${c.duration_seconds?`<span>${Math.floor(flt(c.duration_seconds)/60)}min ${flt(c.duration_seconds)%60}s</span>`:''}
                                        <span>${c.started_at?frappe.datetime.prettyDate(c.started_at):''}</span>
                                    </div>
                                </div>
                            </div>`).join('') || '<div class="cr-empty">No calls logged yet</div>'}
                        </div>
                    </div>
                </div>
            </div>
        `);
    }

    // ─── TAB: MESSAGING ───────────────────────────────────────────────────────
    renderMessaging() {
        const open = this.waConvos.filter(w => w.status === 'Open');
        const pending = this.waConvos.filter(w => w.status === 'Pending');
        $('#cr-panel-messaging').html(`
            <div class="cr-g21">
                <div class="cr-card">
                    <div class="cr-card-head">
                        <div class="cr-card-title"><div class="cr-title-icon" style="background:#25D36622;color:#25D366">💬</div> WhatsApp Inbox (${this.waConvos.length})</div>
                        <div class="cr-acts">
                            <span class="cr-badge bd-red">${open.length} open</span>
                            <button class="cr-btn cb-ghost" onclick="frappe.set_route('List','WA Conversation')">Open List →</button>
                        </div>
                    </div>
                    <div style="max-height:500px;overflow-y:auto">
                        ${this.waConvos.slice(0,20).map(c=>{
                            const initials = (c.contact_display_name||c.phone_number||'?').substring(0,2).toUpperCase();
                            const isNew = c.status==='Open';
                            return `
                            <div class="cr-activity" style="${isNew?'border-left:3px solid var(--cr-grn)':''}" onclick="frappe.set_route('Form','WA Conversation','${c.name}')">
                                <div class="cr-act-icon" style="background:#25D36622;color:#25D366;border-radius:50%">${initials}</div>
                                <div class="cr-act-body">
                                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:2px">
                                        <span class="cr-act-title">${c.contact_display_name||c.phone_number}</span>
                                        ${this.waBadge(c.status)}
                                        ${c.lead?`<span class="cr-badge bd-pri">Lead linked</span>`:''}
                                    </div>
                                    <div style="font-size:11px;color:var(--cr-tx2)">${(c.last_message_preview||'').substring(0,80)}</div>
                                    <div class="cr-act-meta" style="margin-top:3px">
                                        <span>${c.last_message_at?frappe.datetime.prettyDate(c.last_message_at):''}</span>
                                        ${c.assigned_to?`<span>→ ${c.assigned_to.split('@')[0]}</span>`:''}
                                    </div>
                                </div>
                            </div>`;
                        }).join('') || '<div class="cr-empty">No WA conversations</div>'}
                    </div>
                </div>
                <div>
                    <div class="cr-card cr-row">
                        <div class="cr-card-head">
                            <div class="cr-card-title"><div class="cr-title-icon" style="background:#25D36622;color:#25D366">📊</div> WA Summary</div>
                        </div>
                        <div class="cr-card-body">
                            ${[['Open',open.length,'var(--cr-grn)'],['Pending',pending.length,'var(--cr-amb)'],['Resolved',this.waConvos.filter(w=>w.status==='Resolved').length,'var(--cr-sky)']].map(([lbl,n,col])=>`
                            <div class="cr-bar-row">
                                <div class="cr-bar-lbl">${lbl}</div>
                                <div class="cr-bar"><div class="cr-bar-fill" style="width:${this.waConvos.length>0?Math.round(n/this.waConvos.length*100):0}%;background:${col}"></div></div>
                                <div class="cr-bar-val">${n}</div>
                            </div>`).join('')}
                        </div>
                    </div>
                    <div class="cr-card cr-row">
                        <div class="cr-card-head">
                            <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-pri-x);color:var(--cr-pri)">✉️</div> Quick Send</div>
                        </div>
                        <div class="cr-card-body">
                            <div class="cr-ai-card">
                                <h4>💡 WA → CRM Integration</h4>
                                <div class="cr-ai-item"><div class="cr-ai-bullet"></div>WA Conversation already has a <code>lead</code> link field — link threads to leads with one click</div>
                                <div class="cr-ai-item"><div class="cr-ai-bullet"></div>Send WA message directly from a Lead or Deal record using wa_template</div>
                                <div class="cr-ai-item"><div class="cr-ai-bullet"></div>Auto-create CRM Activity when a WA thread is resolved</div>
                            </div>
                            <button class="cr-btn cb-solid" style="width:100%;justify-content:center" onclick="frappe.new_doc('WA Conversation')">+ New WA Conversation</button>
                        </div>
                    </div>
                </div>
            </div>
        `);
    }

    // ─── TAB: AI STUDIO ───────────────────────────────────────────────────────
    renderAI() {
        const topDeals = this.deals.sort((a,b)=>b._health-a._health).slice(0,5);
        const topLeads = this.leads.sort((a,b)=>b._score-a._score).slice(0,5);

        const stageDistData = ['Lead In','Qualified','Proposal Sent','Negotiation','Closed Won','Closed Lost'].map(s=>({
            stage:s, count:this.deals.filter(d=>d.stage===s).length, value:this.deals.filter(d=>d.stage===s).reduce((s,d)=>s+flt(d.deal_value),0)
        }));

        const sourceData = {};
        this.leads.forEach(l => { sourceData[l.lead_source||'Unknown'] = (sourceData[l.lead_source||'Unknown']||0)+1; });
        const sourceEntries = Object.entries(sourceData).sort((a,b)=>b[1]-a[1]).slice(0,6);

        $('#cr-panel-ai').html(`
            <div class="cr-g21">
                <div>
                    <div class="cr-card cr-row">
                        <div class="cr-card-head">
                            <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-pur-x);color:var(--cr-pur)">🤖</div> AI Deal Health Scores</div>
                            <button class="cr-btn cb-ghost" onclick="__crmDash.switchTab('pipeline')">View Pipeline →</button>
                        </div>
                        <div class="cr-card-body" style="padding:10px">
                            ${topDeals.map(d=>{
                                const hCol = d._health>=70?'var(--cr-grn)':d._health>=40?'var(--cr-amb)':'var(--cr-red)';
                                return `
                                <div class="cr-score-card" onclick="frappe.set_route('Form','CRM Deal','${d.name}')">
                                    <div style="width:44px;height:44px;border-radius:10px;background:${hCol}22;display:flex;align-items:center;justify-content:center;flex-direction:column">
                                        <div style="font-size:14px;font-weight:800;color:${hCol}">${d._health}</div>
                                        <div style="font-size:9px;color:${hCol}">health</div>
                                    </div>
                                    <div class="cr-score-body">
                                        <div class="cr-score-name">${d.deal_title||d.name}</div>
                                        <div class="cr-score-meta">
                                            ${this.stageBadge(d.stage)}
                                            <span>${this.fmt(d.deal_value)}</span>
                                            <span style="color:${d._urgency==='high'?'var(--cr-red)':d._urgency==='med'?'var(--cr-amb)':'var(--cr-grn)'}">
                                                ${d._urgency==='high'?'🔥 Urgent':d._urgency==='med'?'⚡ Watch':'✅ On track'}
                                            </span>
                                        </div>
                                    </div>
                                    <div style="width:40px;height:40px;border-radius:50%;border:3px solid ${hCol};display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;color:${hCol};flex-shrink:0">${d._health}%</div>
                                </div>`;
                            }).join('') || '<div class="cr-empty">No deals to score</div>'}
                        </div>
                    </div>

                    <div class="cr-card cr-row">
                        <div class="cr-card-head">
                            <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-grn-x);color:var(--cr-grn)">📊</div> Pipeline Stage Analysis</div>
                        </div>
                        <div class="cr-card-body">
                            <div style="height:200px;position:relative"><canvas id="cr-ch-stages"></canvas></div>
                        </div>
                    </div>

                    <div class="cr-card">
                        <div class="cr-card-head">
                            <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-sky-x);color:var(--cr-sky)">🌐</div> Lead Source Effectiveness</div>
                        </div>
                        <div class="cr-card-body">
                            ${sourceEntries.map(([src, n])=>`
                            <div class="cr-bar-row">
                                <div class="cr-bar-lbl">${src||'Unknown'}</div>
                                <div class="cr-bar"><div class="cr-bar-fill" style="width:${sourceEntries[0]?Math.round(n/sourceEntries[0][1]*100):0}%;background:var(--cr-pri)"></div></div>
                                <div class="cr-bar-val">${n}</div>
                            </div>`).join('') || '<div class="cr-empty">No source data</div>'}
                            <div style="height:180px;position:relative;margin-top:14px"><canvas id="cr-ch-source"></canvas></div>
                        </div>
                    </div>
                </div>
                <div>
                    <div class="cr-card cr-row">
                        <div class="cr-card-head">
                            <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-pur-x);color:var(--cr-pur)">🔮</div> AI Recommendations</div>
                        </div>
                        <div class="cr-card-body">
                            <div class="cr-ai-card">
                                <h4>🔥 Urgent Actions</h4>
                                ${this.deals.filter(d=>d._urgency==='high'&&d.stage!=='Closed Won'&&d.stage!=='Closed Lost').slice(0,3).map(d=>`
                                <div class="cr-ai-item"><div class="cr-ai-bullet"></div>Call ${d.deal_title||d.name} — ${d._lastActDays} days silent, closes ${d.close_date?frappe.datetime.str_to_user(d.close_date):'soon'}</div>`).join('') ||
                                '<div class="cr-ai-item"><div class="cr-ai-bullet"></div>No urgent deals right now — pipeline is healthy</div>'}
                            </div>
                            <div class="cr-ai-card">
                                <h4>📈 Growth Opportunities</h4>
                                ${topLeads.slice(0,3).map(l=>`
                                <div class="cr-ai-item"><div class="cr-ai-bullet"></div>${l.lead_name||l.company_name} — Score ${l._score}, Grade ${l._grade}. ${l.status==='New'?'Never contacted — reach out today':'Follow up to qualify'}</div>`).join('') ||
                                '<div class="cr-ai-item"><div class="cr-ai-bullet"></div>Import leads to see AI scoring</div>'}
                            </div>
                            <div class="cr-ai-card" style="background:var(--cr-grn-x);border-color:rgba(16,185,129,.2)">
                                <h4 style="color:var(--cr-grn)">💡 Pipeline Insights</h4>
                                <div class="cr-ai-item"><div class="cr-ai-bullet" style="background:var(--cr-grn)"></div>${this.deals.filter(d=>d.stage==='Proposal Sent').length} deals have proposals sent but no movement — send a personalised follow-up</div>
                                <div class="cr-ai-item"><div class="cr-ai-bullet" style="background:var(--cr-grn)"></div>Win rate is ${this.deals.filter(d=>['Closed Won','Closed Lost'].includes(d.stage)).length>0?Math.round(this.deals.filter(d=>d.stage==='Closed Won').length/this.deals.filter(d=>['Closed Won','Closed Lost'].includes(d.stage)).length*100):0}% — industry benchmark is 25–30%</div>
                                <div class="cr-ai-item"><div class="cr-ai-bullet" style="background:var(--cr-grn)"></div>Average deal value: ${this.fmt(this.deals.reduce((s,d)=>s+flt(d.deal_value),0)/Math.max(1,this.deals.length))}</div>
                            </div>
                            <button class="cr-btn cb-pur" style="width:100%;justify-content:center;margin-top:8px" onclick="__crmDash.aiEmailDraft()">✍️ AI Email Drafter ↗</button>
                            <button class="cr-btn cb-ghost" style="width:100%;justify-content:center;margin-top:8px" onclick="frappe.set_route('List','CRM Deal')">📋 Full Deal Analysis →</button>
                        </div>
                    </div>

                    <div class="cr-card">
                        <div class="cr-card-head">
                            <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-amb-x);color:var(--cr-amb)">🎯</div> Lead ICP Scoring</div>
                        </div>
                        <div class="cr-card-body">
                            <div style="height:180px;position:relative"><canvas id="cr-ch-leadscore"></canvas></div>
                            <div style="margin-top:12px">
                                ${[['A (80–100)','var(--cr-grn)',this.leads.filter(l=>l._score>=80).length],['B (60–79)','var(--cr-amb)',this.leads.filter(l=>l._score>=60&&l._score<80).length],['C (40–59)','var(--cr-sky)',this.leads.filter(l=>l._score>=40&&l._score<60).length],['D (0–39)','var(--cr-tx3)',this.leads.filter(l=>l._score<40).length]].map(([lbl,col,n])=>`
                                <div class="cr-bar-row">
                                    <div class="cr-bar-lbl"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${col};margin-right:6px"></span>${lbl}</div>
                                    <div class="cr-bar"><div class="cr-bar-fill" style="width:${this.leads.length>0?Math.round(n/this.leads.length*100):0}%;background:${col}"></div></div>
                                    <div class="cr-bar-val">${n}</div>
                                </div>`).join('')}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `);

        // Stage value chart
        this.mkChart('cr-ch-stages', {
            type:'bar',
            data:{
                labels:stageDistData.map(s=>s.stage),
                datasets:[
                    {label:'Deal Count',data:stageDistData.map(s=>s.count),backgroundColor:stageDistData.map(s=>STAGE_COLORS[s.stage]||'#64748B'),borderRadius:4,yAxisID:'y'},
                    {label:'Value (₦)',data:stageDistData.map(s=>s.value),type:'line',borderColor:this.cv('--cr-pur'),backgroundColor:'transparent',borderWidth:2.5,tension:.4,pointRadius:3,yAxisID:'y1'}
                ]
            },
            options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},
                plugins:{legend:{position:'bottom',labels:{boxWidth:10,font:{size:10}}}},
                scales:{
                    y:{position:'left',grid:{color:this.gc()},ticks:{color:this.tc(),font:{size:10}}},
                    y1:{position:'right',grid:{drawOnChartArea:false},ticks:{color:this.tc(),font:{size:10},callback:v=>this.fmtK(v)}}
                }
            }
        });

        // Source doughnut
        this.mkChart('cr-ch-source', {
            type:'doughnut',
            data:{ labels:sourceEntries.map(([s])=>s), datasets:[{ data:sourceEntries.map(([,n])=>n), backgroundColor:['#2563EB','#10B981','#F59E0B','#8B5CF6','#06B6D4','#EF4444'], borderWidth:0 }] },
            options:{ cutout:'60%', responsive:true, maintainAspectRatio:false, plugins:{ legend:{ position:'right', labels:{ boxWidth:10, font:{ size:10 } } } } }
        });

        // Lead score distribution
        const gradeData = [this.leads.filter(l=>l._score>=80).length, this.leads.filter(l=>l._score>=60&&l._score<80).length, this.leads.filter(l=>l._score>=40&&l._score<60).length, this.leads.filter(l=>l._score<40).length];
        this.mkChart('cr-ch-leadscore', {
            type:'bar',
            data:{ labels:['A (80+)','B (60–79)','C (40–59)','D (<40)'], datasets:[{ data:gradeData, backgroundColor:['var(--cr-grn)','var(--cr-amb)','var(--cr-sky)','#94A3B8'], borderRadius:6 }] },
            options:{ responsive:true, maintainAspectRatio:false, plugins:{ legend:{ display:false } }, scales:{ x:{ grid:{ color:this.gc() }, ticks:{ color:this.tc(), font:{ size:10 } } }, y:{ grid:{ color:this.gc() }, ticks:{ color:this.tc(), font:{ size:10 } } } } }
        });
    }

    // ─── TAB: REPORTS ─────────────────────────────────────────────────────────
    renderReports() {
        const byMonth = {};
        this.deals.filter(d=>d.stage==='Closed Won').forEach(d=>{
            const mo = (d.modified||d.creation||'').substring(0,7);
            if(mo) { byMonth[mo]=(byMonth[mo]||0)+flt(d.deal_value); }
        });
        const months = Object.keys(byMonth).sort().slice(-6);

        const repPerf = {};
        this.deals.forEach(d=>{
            const r = d.assigned_to||'Unassigned';
            if(!repPerf[r]) repPerf[r]={rep:r,deals:0,value:0,won:0};
            repPerf[r].deals++;
            repPerf[r].value += flt(d.deal_value);
            if(d.stage==='Closed Won') repPerf[r].won++;
        });
        const repRows = Object.values(repPerf).sort((a,b)=>b.won-a.won);

        $('#cr-panel-reports').html(`
            <div class="cr-g2">
                <div class="cr-card cr-row">
                    <div class="cr-card-head">
                        <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-grn-x);color:var(--cr-grn)">📈</div> Monthly Revenue (Won)</div>
                    </div>
                    <div class="cr-card-body">
                        <div style="height:220px;position:relative"><canvas id="cr-ch-monthly"></canvas></div>
                    </div>
                </div>
                <div class="cr-card cr-row">
                    <div class="cr-card-head">
                        <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-sky-x);color:var(--cr-sky)">🔽</div> Conversion Funnel</div>
                    </div>
                    <div class="cr-card-body">
                        ${['Lead In','Qualified','Proposal Sent','Negotiation','Closed Won'].map((stage,i,arr)=>{
                            const cnt = this.deals.filter(d=>d.stage===stage).length + (stage==='Lead In'?this.leads.length:0);
                            const pct = i===0?100:this.deals.filter(d=>d.stage===arr[0]).length>0?Math.round(this.deals.filter(d=>d.stage===stage).length/Math.max(1,this.deals.filter(d=>d.stage===arr[0]).length+this.leads.length)*100):0;
                            return `
                            <div style="margin-bottom:10px">
                                <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:4px">
                                    <span style="font-weight:600">${stage}</span>
                                    <span style="color:var(--cr-tx3)">${cnt} · ${pct}%</span>
                                </div>
                                <div style="height:20px;background:var(--cr-brd);border-radius:4px;overflow:hidden">
                                    <div style="height:100%;width:${pct}%;background:${STAGE_COLORS[stage]||'var(--cr-pri)'};border-radius:4px;transition:width .5s"></div>
                                </div>
                            </div>`;
                        }).join('')}
                    </div>
                </div>
            </div>

            <div class="cr-card cr-row">
                <div class="cr-card-head">
                    <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-amb-x);color:var(--cr-amb)">🏆</div> Rep Performance Leaderboard</div>
                    <button class="cr-btn cb-ghost" onclick="frappe.set_route('List','CRM Deal')">All Deals →</button>
                </div>
                <div class="cr-tbl-wrap">
                    <table class="cr-tbl">
                        <thead><tr><th>#</th><th>Rep</th><th class="tr">Deals</th><th class="tr">Won</th><th class="tr">Win Rate</th><th class="tr">Pipeline Value</th></tr></thead>
                        <tbody>
                            ${repRows.map((r,i)=>`
                            <tr>
                                <td><div style="width:22px;height:22px;border-radius:50%;background:${i===0?'var(--cr-amb)':i===1?'var(--cr-tx3)':i===2?'#CD7F32':'var(--cr-bg)'};color:${i<3?'#fff':'var(--cr-tx3)'};display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:800">${i+1}</div></td>
                                <td style="font-weight:600">${r.rep.split('@')[0]}</td>
                                <td class="tr">${r.deals}</td>
                                <td class="tr"><span class="cr-badge bd-grn">${r.won}</span></td>
                                <td class="tr">${r.deals>0?Math.round(r.won/r.deals*100):0}%</td>
                                <td class="tr">${this.fmt(r.value)}</td>
                            </tr>`).join('') || '<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--cr-tx3)">No deal data yet</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        `);

        this.mkChart('cr-ch-monthly', {
            type:'bar',
            data:{
                labels:months.map(m=>new Date(m+'-01').toLocaleDateString('en-NG',{month:'short',year:'2-digit'})),
                datasets:[{label:'Won Revenue (₦)',data:months.map(m=>byMonth[m]||0),backgroundColor:'rgba(16,185,129,.7)',borderRadius:6}]
            },
            options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},
                scales:{x:{grid:{color:this.gc()},ticks:{color:this.tc(),font:{size:10}}},y:{grid:{color:this.gc()},ticks:{color:this.tc(),font:{size:10},callback:v=>this.fmtK(v)}}}}
        });
    }

    // ─── TAB: QUICK ACTIONS ───────────────────────────────────────────────────
    renderActions() {
        $('#cr-panel-actions').html(`
            <div class="cr-card">
                <div class="cr-card-head">
                    <div class="cr-card-title"><div class="cr-title-icon" style="background:var(--cr-sky-x);color:var(--cr-sky)">⚡</div> Quick Actions — CRM Workflow</div>
                    <div class="cr-acts"><button class="cr-btn cb-ghost" onclick="__crmDash.openThemePicker()"><i class="fa fa-paint-brush"></i> Theme</button></div>
                </div>
                <div class="cr-card-body">
                    <div class="cr-qlinks">
                        <div class="cr-qlink" onclick="frappe.new_doc('CRM Lead')"><div class="cr-ql-icon" style="background:#2563EB"><i class="fa fa-user-plus"></i></div><div><div class="cr-ql-title">New Lead</div><div class="cr-ql-desc">Create a lead record</div></div></div>
                        <div class="cr-qlink" onclick="frappe.new_doc('CRM Opportunity')"><div class="cr-ql-icon" style="background:#8B5CF6"><i class="fa fa-briefcase"></i></div><div><div class="cr-ql-title">New Opportunity</div><div class="cr-ql-desc">Direct opportunity</div></div></div>
                        <div class="cr-qlink" onclick="frappe.new_doc('CRM Deal')"><div class="cr-ql-icon" style="background:#10B981"><i class="fa fa-handshake-o"></i></div><div><div class="cr-ql-title">New Deal</div><div class="cr-ql-desc">Open a deal</div></div></div>
                        <div class="cr-qlink" onclick="frappe.new_doc('CRM Contact')"><div class="cr-ql-icon" style="background:#06B6D4"><i class="fa fa-address-card"></i></div><div><div class="cr-ql-title">New Contact</div><div class="cr-ql-desc">Add contact</div></div></div>
                        <div class="cr-qlink" onclick="frappe.new_doc('CRM Account')"><div class="cr-ql-icon" style="background:#F59E0B"><i class="fa fa-building"></i></div><div><div class="cr-ql-title">New Account</div><div class="cr-ql-desc">Company account</div></div></div>
                        <div class="cr-qlink" onclick="__crmDash.logCallDialog()"><div class="cr-ql-icon" style="background:#06B6D4"><i class="fa fa-phone"></i></div><div><div class="cr-ql-title">Log Call</div><div class="cr-ql-desc">Record phone call</div></div></div>
                        <div class="cr-qlink" onclick="__crmDash.logActivityDialog()"><div class="cr-ql-icon" style="background:#F97316"><i class="fa fa-tasks"></i></div><div><div class="cr-ql-title">Log Activity</div><div class="cr-ql-desc">Task/note/meeting</div></div></div>
                        <div class="cr-qlink" onclick="frappe.new_doc('CRM Meeting')"><div class="cr-ql-icon" style="background:#EC4899"><i class="fa fa-calendar"></i></div><div><div class="cr-ql-title">New Meeting</div><div class="cr-ql-desc">Schedule meeting</div></div></div>
                        <div class="cr-qlink" onclick="frappe.new_doc('CRM Quota Target')"><div class="cr-ql-icon" style="background:#7C3AED"><i class="fa fa-trophy"></i></div><div><div class="cr-ql-title">Set Quota</div><div class="cr-ql-desc">Sales target</div></div></div>
                        <a class="cr-qlink" href="/app/crm-lead" target="_blank"><div class="cr-ql-icon" style="background:#0EA5E9"><i class="fa fa-list"></i></div><div><div class="cr-ql-title">All Leads</div><div class="cr-ql-desc">Lead list view</div></div></a>
                        <a class="cr-qlink" href="/app/crm-opportunity" target="_blank"><div class="cr-ql-icon" style="background:#8B5CF6"><i class="fa fa-th-large"></i></div><div><div class="cr-ql-title">All Opportunities</div><div class="cr-ql-desc">Opportunity list</div></div></a>
                        <a class="cr-qlink" href="/app/crm-deal" target="_blank"><div class="cr-ql-icon" style="background:#059669"><i class="fa fa-th-large"></i></div><div><div class="cr-ql-title">All Deals</div><div class="cr-ql-desc">Deal list view</div></div></a>
                        <a class="cr-qlink" href="/app/wa-conversation" target="_blank"><div class="cr-ql-icon" style="background:#25D366"><i class="fa fa-whatsapp"></i></div><div><div class="cr-ql-title">WA Inbox</div><div class="cr-ql-desc">WhatsApp threads</div></div></a>
                        <a class="cr-qlink" href="/app/telephone-call-log" target="_blank"><div class="cr-ql-icon" style="background:#64748B"><i class="fa fa-phone-square"></i></div><div><div class="cr-ql-title">Call Log</div><div class="cr-ql-desc">All call records</div></div></a>
                        <div class="cr-qlink" onclick="__crmDash.aiEmailDraft()"><div class="cr-ql-icon" style="background:var(--cr-pur)"><i class="fa fa-magic"></i></div><div><div class="cr-ql-title">AI Email Draft</div><div class="cr-ql-desc">AI-powered outreach</div></div></div>
                        <div class="cr-qlink" onclick="__crmDash.exportPipeline()"><div class="cr-ql-icon" style="background:#059669"><i class="fa fa-download"></i></div><div><div class="cr-ql-title">Export Pipeline</div><div class="cr-ql-desc">Download to Excel</div></div></div>
                        <div class="cr-qlink" onclick="__crmDash.openThemePicker()"><div class="cr-ql-icon" style="background:#EC4899"><i class="fa fa-paint-brush"></i></div><div><div class="cr-ql-title">Change Theme</div><div class="cr-ql-desc">Dashboard colours</div></div></div>
                    </div>
                </div>
            </div>
        `);
    }

    // ─── DIALOGS ──────────────────────────────────────────────────────────────
    logCallDialog(dealName) {
        const d = new frappe.ui.Dialog({
            title: '📞 Log Call',
            fields: [
                { fieldtype:'Data',     fieldname:'caller_name',     label:'Caller / Contact Name', reqd:1 },
                { fieldtype:'Column Break' },
                { fieldtype:'Select',   fieldname:'direction',        label:'Direction', default:'Outbound', options:'\nOutbound\nInbound', reqd:1 },
                { fieldtype:'Section Break' },
                { fieldtype:'Select',   fieldname:'status',           label:'Outcome', default:'Answered', options:'\nAnswered\nMissed\nBusy\nDeclined', reqd:1 },
                { fieldtype:'Duration', fieldname:'duration_seconds', label:'Duration (seconds)' },
                { fieldtype:'Column Break' },
                { fieldtype:'Link',     fieldname:'lead',             label:'Link to Lead', options:'CRM Lead' },
                { fieldtype:'Link',     fieldname:'deal',             label:'Link to Deal', options:'CRM Deal', default: dealName||'' },
                { fieldtype:'Section Break', label:'Notes' },
                { fieldtype:'Small Text', fieldname:'outcome_notes',  label:'Notes / Outcome' },
            ],
            primary_action_label: '💾 Save Call',
            primary_action(vals) {
                frappe.call({
                    method: 'frappe.client.insert',
                    args:   { doc:{ doctype:'Telephone Call Log', call_type:'External', ...vals } },
                    callback: (r) => { d.hide(); frappe.show_alert({ message:'Call logged', indicator:'green' }); }
                });
            }
        });
        d.show();
    }

    logActivityDialog(dealName) {
        const d = new frappe.ui.Dialog({
            title: '📋 Log Activity',
            fields: [
                { fieldtype:'Select', fieldname:'activity_type', label:'Activity Type', default:'Call', options:'\nCall\nEmail\nMeeting\nNote\nDemo\nProposal\nFollow-up\nTask', reqd:1 },
                { fieldtype:'Column Break' },
                { fieldtype:'Date', fieldname:'due_date', label:'Due Date', default: frappe.datetime.get_today(), reqd:1 },
                { fieldtype:'Section Break' },
                { fieldtype:'Data', fieldname:'subject', label:'Subject', reqd:1 },
                { fieldtype:'Link', fieldname:'deal',    label:'Deal',    options:'CRM Deal', default: dealName||'' },
                { fieldtype:'Column Break' },
                { fieldtype:'Link', fieldname:'lead',    label:'Lead',    options:'CRM Lead' },
                { fieldtype:'Link', fieldname:'contact', label:'Contact', options:'CRM Contact' },
                { fieldtype:'Section Break', label:'Notes' },
                { fieldtype:'Text',fieldname:'outcome',  label:'Outcome / Notes' },
            ],
            primary_action_label:'💾 Save',
            primary_action(vals) {
                frappe.call({
                    method:'frappe.client.insert',
                    args:  { doc:{ doctype:'CRM Activity', status:'Open', ...vals } },
                    callback:()=>{ d.hide(); frappe.show_alert({ message:'Activity logged', indicator:'green' }); }
                });
            }
        });
        d.show();
    }

    aiEmailDraft() {
        frappe.prompt([
            { fieldtype:'Link',   fieldname:'lead_deal',  label:'Lead or Deal Name', options:'CRM Lead' },
            { fieldtype:'Select', fieldname:'email_type', label:'Email Type', options:'\nFirst Outreach\nFollow-up\nProposal Cover\nNegotiation\nClosing Push\nRe-engagement', reqd:1 },
            { fieldtype:'Select', fieldname:'tone',       label:'Tone', default:'Professional', options:'\nProfessional\nFriendly\nUrgent\nCasual' },
            { fieldtype:'Data',   fieldname:'key_point',  label:'Key Message / Offer' },
        ], (vals) => {
            const template = `Subject: [AI Draft] ${vals.email_type} — ${vals.lead_deal||'Prospect'}\n\nDear [Contact Name],\n\n[${vals.tone} opening referencing their business context]\n\n${vals.key_point||'[Your key value proposition here]'}\n\n[Specific next step / CTA]\n\nBest regards,\n[Your Name]\n[Your Company]`;
            frappe.msgprint({
                title:'✍️ AI Email Draft',
                indicator:'purple',
                message:`<div style="font-family:monospace;font-size:12px;white-space:pre-wrap;background:var(--cr-bg);padding:14px;border-radius:10px;border:1px solid var(--cr-brd);color:var(--cr-tx1)">${template}</div><p style="font-size:11px;color:var(--cr-tx3);margin-top:10px">Copy this draft and personalise before sending. Connect an AI API in <code>crm_dashboard.py</code> for real generation.</p>`
            });
        }, '✍️ AI Email Drafter', 'Generate Draft');
    }

    completeActivity(name) {
        frappe.call({
            method:'frappe.client.set_value',
            args:{ doctype:'CRM Activity', name, fieldname:{ status:'Completed' } },
            callback:()=>{ frappe.show_alert({message:'Activity completed',indicator:'green'}); this.loadData(true); }
        });
    }

    // ─── EXPORT ───────────────────────────────────────────────────────────────
    exportPipeline() {
        frappe.msgprint({
            title:'📊 Export CRM Data', indicator:'green',
            message:`<div style="display:flex;flex-direction:column;gap:8px;padding:8px">
                <a class="btn btn-primary btn-sm" href="/app/crm-deal?export=1" target="_blank">📊 Export All Deals</a>
                <a class="btn btn-success btn-sm" href="/app/crm-lead?export=1" target="_blank">🎯 Export All Leads</a>
                <a class="btn btn-info btn-sm"    href="/app/crm-activity?export=1" target="_blank">📋 Export Activities</a>
                <a class="btn btn-warning btn-sm" href="/app/crm-contact?export=1" target="_blank">👥 Export Contacts</a>
            </div>`
        });
    }

    // ─── HELPERS ──────────────────────────────────────────────────────────────
    mkChart(id, cfg) {
        const c = document.getElementById(id);
        if (!c) return null;
        if (this.charts[id]) { this.charts[id].destroy(); }
        this.charts[id] = new Chart(c.getContext('2d'), cfg);
        return this.charts[id];
    }

    cv(v)  { return getComputedStyle(document.getElementById('cr-root')||document.body).getPropertyValue(v).trim(); }
    gc()   { return this.cv('--cr-brd') || '#E2E8F0'; }
    tc()   { return this.cv('--cr-tx3') || '#94A3B8'; }

    kpi(icon, klass, label, value, sub, link) {
        const click = link ? `onclick="window.open('${link}','_blank')"` : '';
        return `<div class="cr-kpi ${klass}" ${click} style="${link?'cursor:pointer':''}">
            <div class="cr-kpi-icon">${icon}</div>
            <div class="cr-kpi-lbl">${label}</div>
            <div class="cr-kpi-val">${value}</div>
            ${sub?`<div class="cr-kpi-sub">${sub}</div>`:''}
        </div>`;
    }

    oppStatusBadge(s) {
        const map = { 'Prospecting':'bd-sky','Needs Analysis':'bd-pri','Value Proposition':'bd-pri','Identified Decision Makers':'bd-pur','Perception Analysis':'bd-pur','Proposal/Price Quote':'bd-amb','Negotiation/Review':'bd-amb','Won':'bd-grn','Lost':'bd-red','Closed':'bd-grn','Suspended':'bd-grey' };
        return `<span class="cr-badge ${map[s]||'bd-grey'}">${s||'—'}</span>`;
    }

    stageBadge(s) {
        const map = { 'Lead In':'bd-sky','Qualified':'bd-pur','Proposal Sent':'bd-amb','Negotiation':'bd-amb','Closed Won':'bd-grn','Closed Lost':'bd-red' };
        return `<span class="cr-badge ${map[s]||'bd-grey'}">${s||'—'}</span>`;
    }

    leadStatusBadge(s) {
        const map = { 'New':'bd-pri','Open':'bd-sky','Replied':'bd-pur','Opportunity':'bd-amb','Qualified':'bd-grn','Unqualified':'bd-grey','Junk':'bd-red','Do Not Contact':'bd-red','Converted':'bd-grn' };
        return `<span class="cr-badge ${map[s]||'bd-grey'}">${s||'—'}</span>`;
    }

    actStatusBadge(s) {
        const map = { 'Open':'bd-pri','In Progress':'bd-sky','Completed':'bd-grn','Cancelled':'bd-red','Deferred':'bd-grey' };
        return `<span class="cr-badge ${map[s]||'bd-grey'}">${s||'—'}</span>`;
    }

    waBadge(s) {
        const map = { 'Open':'bd-grn','Pending':'bd-amb','Resolved':'bd-sky','Spam':'bd-red' };
        return `<span class="cr-badge ${map[s]||'bd-grey'}">${s||'—'}</span>`;
    }

    actTypeIcon(t) {
        const map = { 'Call':'📞','Email':'✉️','Meeting':'👥','Note':'📝','Demo':'🖥','Proposal':'📄','Follow-up':'🔄','Task':'✅','WhatsApp':'💬' };
        return map[t] || '📋';
    }

    actTypeColor(t) {
        const map = { 'Call':'var(--cr-grn)','Email':'var(--cr-pri)','Meeting':'var(--cr-pur)','Note':'var(--cr-amb)','Demo':'var(--cr-sky)','Proposal':'var(--cr-red)','Follow-up':'#F97316','Task':'var(--cr-sky)' };
        return map[t] || 'var(--cr-tx3)';
    }

    fmt(v) {
        const n = parseFloat(v) || 0;
        if(n>=1e9) return '₦'+(n/1e9).toFixed(1)+'B';
        if(n>=1e6) return '₦'+(n/1e6).toFixed(1)+'M';
        if(n>=1e3) return '₦'+(n/1e3).toFixed(0)+'K';
        return '₦'+Math.round(n).toLocaleString('en-NG');
    }

    fmtK(v) {
        const n = parseFloat(v)||0;
        if(n>=1e9) return '₦'+(n/1e9).toFixed(1)+'B';
        if(n>=1e6) return '₦'+(n/1e6).toFixed(1)+'M';
        if(n>=1e3) return '₦'+(n/1e3).toFixed(0)+'K';
        return '₦'+Math.round(n).toLocaleString('en-NG');
    }

    num(v) {
        const n = parseFloat(v)||0;
        if(n>=1e6) return (n/1e6).toFixed(1)+'M';
        if(n>=1e3) return (n/1e3).toFixed(1)+'K';
        return Math.round(n).toLocaleString('en-NG');
    }
}

function flt(v) { return parseFloat(v) || 0; }