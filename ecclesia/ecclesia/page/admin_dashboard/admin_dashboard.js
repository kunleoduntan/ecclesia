// Copyright (c) 2026, Value Impacts Consulting
// ecclesia/ecclesia/page/admin_dashboard/admin_dashboard.js
//
// ╔══════════════════════════════════════════════════════════════════════════════╗
// ║  ADMIN 360° POWER DASHBOARD — Ecclesia Administrative Management            ║
// ║  9 Themes · 10 Tabs · Full CRUD · Chart.js · AI Insights · localStorage    ║
// ║  Tabs: Overview · Requests · Fleet · Facilities · Utilities · Security      ║
// ║        Contracts · Compliance · HSE · AI Intelligence                       ║
// ╚══════════════════════════════════════════════════════════════════════════════╝

frappe.pages['admin-dashboard'] = frappe.pages['admin-dashboard'] || {};
frappe.pages['admin-dashboard'].on_page_load = function (wrapper) {
    const boot = () => new AdminDashboard(wrapper);
    if (typeof Chart === 'undefined') {
        const s = document.createElement('script');
        s.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
        s.onload = boot;
        s.onerror = () => frappe.msgprint({ title: 'Chart.js Error', indicator: 'red', message: 'Failed to load Chart.js. Check internet connection.' });
        document.head.appendChild(s);
    } else { boot(); }
};

frappe.pages['admin-dashboard'].on_page_show = function (wrapper) {
    if (window.__adminDash) window.__adminDash.loadData(true);
};

// ═══════════════════════════════════════════════════════════════════════════════
//  THEME REGISTRY — 9 Themes, pure localStorage
// ═══════════════════════════════════════════════════════════════════════════════
const ADMIN_THEMES = {
    steel: {
        name: 'Steel', icon: '🔩', isDark: false,
        '--ad-pri': '#0284C7', '--ad-pri-d': '#0369A1', '--ad-pri-x': 'rgba(2,132,199,.09)',
        '--ad-acc': '#38BDF8',
        '--ad-red': '#EF4444', '--ad-red-x': 'rgba(239,68,68,.09)',
        '--ad-amb': '#F59E0B', '--ad-amb-x': 'rgba(245,158,11,.09)',
        '--ad-grn': '#10B981', '--ad-grn-x': 'rgba(16,185,129,.09)',
        '--ad-sky': '#06B6D4', '--ad-sky-x': 'rgba(6,182,212,.09)',
        '--ad-pur': '#8B5CF6', '--ad-pur-x': 'rgba(139,92,246,.09)',
        '--ad-bg': '#F8FAFC', '--ad-bg2': '#F1F5F9', '--ad-bg3': '#E2E8F0',
        '--ad-card': '#FFFFFF', '--ad-brd': '#E2E8F0', '--ad-brd2': '#CBD5E1',
        '--ad-tx1': '#0F172A', '--ad-tx2': '#475569', '--ad-tx3': '#94A3B8',
        '--ad-banner': 'linear-gradient(135deg,#0F172A 0%,#1E3A5F 40%,#0284C7 75%,#06B6D4 100%)',
    },
    midnight: {
        name: 'Midnight', icon: '🌙', isDark: true,
        '--ad-pri': '#818CF8', '--ad-pri-d': '#6366F1', '--ad-pri-x': 'rgba(129,140,248,.12)',
        '--ad-acc': '#A5B4FC',
        '--ad-red': '#F87171', '--ad-red-x': 'rgba(248,113,113,.12)',
        '--ad-amb': '#FCD34D', '--ad-amb-x': 'rgba(252,211,77,.12)',
        '--ad-grn': '#34D399', '--ad-grn-x': 'rgba(52,211,153,.12)',
        '--ad-sky': '#38BDF8', '--ad-sky-x': 'rgba(56,189,248,.12)',
        '--ad-pur': '#C084FC', '--ad-pur-x': 'rgba(192,132,252,.12)',
        '--ad-bg': '#0F172A', '--ad-bg2': '#1E293B', '--ad-bg3': '#334155',
        '--ad-card': '#1E293B', '--ad-brd': 'rgba(255,255,255,.08)', '--ad-brd2': 'rgba(255,255,255,.14)',
        '--ad-tx1': '#F1F5F9', '--ad-tx2': '#94A3B8', '--ad-tx3': '#475569',
        '--ad-banner': 'linear-gradient(135deg,#020617 0%,#0F172A 50%,#1E3A5F 70%,#312E81 100%)',
    },
    verdant: {
        name: 'Verdant', icon: '🌿', isDark: false,
        '--ad-pri': '#059669', '--ad-pri-d': '#047857', '--ad-pri-x': 'rgba(5,150,105,.09)',
        '--ad-acc': '#34D399',
        '--ad-red': '#EF4444', '--ad-red-x': 'rgba(239,68,68,.09)',
        '--ad-amb': '#F59E0B', '--ad-amb-x': 'rgba(245,158,11,.09)',
        '--ad-grn': '#10B981', '--ad-grn-x': 'rgba(16,185,129,.09)',
        '--ad-sky': '#0EA5E9', '--ad-sky-x': 'rgba(14,165,233,.09)',
        '--ad-pur': '#8B5CF6', '--ad-pur-x': 'rgba(139,92,246,.09)',
        '--ad-bg': '#ECFDF5', '--ad-bg2': '#D1FAE5', '--ad-bg3': '#A7F3D0',
        '--ad-card': '#FFFFFF', '--ad-brd': '#A7F3D0', '--ad-brd2': '#6EE7B7',
        '--ad-tx1': '#022C22', '--ad-tx2': '#065F46', '--ad-tx3': '#6EE7B7',
        '--ad-banner': 'linear-gradient(135deg,#022C22 0%,#047857 40%,#059669 70%,#10B981 100%)',
    },
    ember: {
        name: 'Ember', icon: '🔥', isDark: false,
        '--ad-pri': '#F97316', '--ad-pri-d': '#EA580C', '--ad-pri-x': 'rgba(249,115,22,.09)',
        '--ad-acc': '#FB923C',
        '--ad-red': '#EF4444', '--ad-red-x': 'rgba(239,68,68,.09)',
        '--ad-amb': '#EAB308', '--ad-amb-x': 'rgba(234,179,8,.09)',
        '--ad-grn': '#22C55E', '--ad-grn-x': 'rgba(34,197,94,.09)',
        '--ad-sky': '#0EA5E9', '--ad-sky-x': 'rgba(14,165,233,.09)',
        '--ad-pur': '#A855F7', '--ad-pur-x': 'rgba(168,85,247,.09)',
        '--ad-bg': '#FFF7ED', '--ad-bg2': '#FFEDD5', '--ad-bg3': '#FED7AA',
        '--ad-card': '#FFFFFF', '--ad-brd': '#FED7AA', '--ad-brd2': '#FDBA74',
        '--ad-tx1': '#431407', '--ad-tx2': '#9A3412', '--ad-tx3': '#FDBA74',
        '--ad-banner': 'linear-gradient(135deg,#431407 0%,#C2410C 40%,#F97316 70%,#EAB308 100%)',
    },
    nova: {
        name: 'Nova', icon: '🌟', isDark: false,
        '--ad-pri': '#7C3AED', '--ad-pri-d': '#6D28D9', '--ad-pri-x': 'rgba(124,58,237,.09)',
        '--ad-acc': '#A78BFA',
        '--ad-red': '#EF4444', '--ad-red-x': 'rgba(239,68,68,.09)',
        '--ad-amb': '#F59E0B', '--ad-amb-x': 'rgba(245,158,11,.09)',
        '--ad-grn': '#10B981', '--ad-grn-x': 'rgba(16,185,129,.09)',
        '--ad-sky': '#06B6D4', '--ad-sky-x': 'rgba(6,182,212,.09)',
        '--ad-pur': '#EC4899', '--ad-pur-x': 'rgba(236,72,153,.09)',
        '--ad-bg': '#FAF5FF', '--ad-bg2': '#F5F3FF', '--ad-bg3': '#EDE9FE',
        '--ad-card': '#FFFFFF', '--ad-brd': '#E9D5FF', '--ad-brd2': '#D8B4FE',
        '--ad-tx1': '#2E1065', '--ad-tx2': '#5B21B6', '--ad-tx3': '#A78BFA',
        '--ad-banner': 'linear-gradient(135deg,#1E1B4B 0%,#4C1D95 40%,#7C3AED 70%,#EC4899 100%)',
    },
    arctic: {
        name: 'Arctic', icon: '❄️', isDark: false,
        '--ad-pri': '#0EA5E9', '--ad-pri-d': '#0284C7', '--ad-pri-x': 'rgba(14,165,233,.09)',
        '--ad-acc': '#7DD3FC',
        '--ad-red': '#EF4444', '--ad-red-x': 'rgba(239,68,68,.09)',
        '--ad-amb': '#F59E0B', '--ad-amb-x': 'rgba(245,158,11,.09)',
        '--ad-grn': '#10B981', '--ad-grn-x': 'rgba(16,185,129,.09)',
        '--ad-sky': '#6366F1', '--ad-sky-x': 'rgba(99,102,241,.09)',
        '--ad-pur': '#EC4899', '--ad-pur-x': 'rgba(236,72,153,.09)',
        '--ad-bg': '#F0F9FF', '--ad-bg2': '#E0F2FE', '--ad-bg3': '#BAE6FD',
        '--ad-card': '#FFFFFF', '--ad-brd': '#BAE6FD', '--ad-brd2': '#7DD3FC',
        '--ad-tx1': '#0C4A6E', '--ad-tx2': '#075985', '--ad-tx3': '#7DD3FC',
        '--ad-banner': 'linear-gradient(135deg,#0C4A6E 0%,#0369A1 40%,#0EA5E9 70%,#06B6D4 100%)',
    },
    forest: {
        name: 'Forest', icon: '🌲', isDark: true,
        '--ad-pri': '#22C55E', '--ad-pri-d': '#16A34A', '--ad-pri-x': 'rgba(34,197,94,.12)',
        '--ad-acc': '#4ADE80',
        '--ad-red': '#F87171', '--ad-red-x': 'rgba(248,113,113,.12)',
        '--ad-amb': '#FBBF24', '--ad-amb-x': 'rgba(251,191,36,.12)',
        '--ad-grn': '#22C55E', '--ad-grn-x': 'rgba(34,197,94,.12)',
        '--ad-sky': '#38BDF8', '--ad-sky-x': 'rgba(56,189,248,.12)',
        '--ad-pur': '#F472B6', '--ad-pur-x': 'rgba(244,114,182,.12)',
        '--ad-bg': '#052E16', '--ad-bg2': '#14532D', '--ad-bg3': '#166534',
        '--ad-card': '#14532D', '--ad-brd': 'rgba(187,247,208,.1)', '--ad-brd2': 'rgba(134,239,172,.18)',
        '--ad-tx1': '#F0FDF4', '--ad-tx2': '#86EFAC', '--ad-tx3': '#4ADE80',
        '--ad-banner': 'linear-gradient(135deg,#052E16 0%,#14532D 40%,#166534 70%,#22C55E 100%)',
    },
    sunset: {
        name: 'Sunset', icon: '🌅', isDark: false,
        '--ad-pri': '#DC2626', '--ad-pri-d': '#B91C1C', '--ad-pri-x': 'rgba(220,38,38,.09)',
        '--ad-acc': '#F87171',
        '--ad-red': '#EF4444', '--ad-red-x': 'rgba(239,68,68,.09)',
        '--ad-amb': '#F59E0B', '--ad-amb-x': 'rgba(245,158,11,.09)',
        '--ad-grn': '#10B981', '--ad-grn-x': 'rgba(16,185,129,.09)',
        '--ad-sky': '#06B6D4', '--ad-sky-x': 'rgba(6,182,212,.09)',
        '--ad-pur': '#EC4899', '--ad-pur-x': 'rgba(236,72,153,.09)',
        '--ad-bg': '#FFF1F2', '--ad-bg2': '#FFE4E6', '--ad-bg3': '#FECDD3',
        '--ad-card': '#FFFFFF', '--ad-brd': '#FECDD3', '--ad-brd2': '#FDA4AF',
        '--ad-tx1': '#4C0519', '--ad-tx2': '#881337', '--ad-tx3': '#FDA4AF',
        '--ad-banner': 'linear-gradient(135deg,#4C0519 0%,#881337 40%,#DC2626 70%,#F59E0B 100%)',
    },
    candy: {
        name: 'Candy', icon: '🍬', isDark: false,
        '--ad-pri': '#DB2777', '--ad-pri-d': '#BE185D', '--ad-pri-x': 'rgba(219,39,119,.09)',
        '--ad-acc': '#F472B6',
        '--ad-red': '#EF4444', '--ad-red-x': 'rgba(239,68,68,.09)',
        '--ad-amb': '#F59E0B', '--ad-amb-x': 'rgba(245,158,11,.09)',
        '--ad-grn': '#10B981', '--ad-grn-x': 'rgba(16,185,129,.09)',
        '--ad-sky': '#06B6D4', '--ad-sky-x': 'rgba(6,182,212,.09)',
        '--ad-pur': '#8B5CF6', '--ad-pur-x': 'rgba(139,92,246,.09)',
        '--ad-bg': '#FDF2F8', '--ad-bg2': '#FCE7F3', '--ad-bg3': '#FBCFE8',
        '--ad-card': '#FFFFFF', '--ad-brd': '#FBCFE8', '--ad-brd2': '#F9A8D4',
        '--ad-tx1': '#500724', '--ad-tx2': '#831843', '--ad-tx3': '#F9A8D4',
        '--ad-banner': 'linear-gradient(135deg,#500724 0%,#831843 40%,#DB2777 70%,#EC4899 100%)',
    },
};

// ═══════════════════════════════════════════════════════════════════════════════
//  MAIN CLASS
// ═══════════════════════════════════════════════════════════════════════════════
class AdminDashboard {
    constructor(wrapper) {
        this.wrapper     = wrapper;
        this.page        = frappe.ui.make_app_page({
            parent: wrapper,
            title: 'Admin 360° Dashboard',
            single_column: true
        });
        this.charts      = {};
        this.activeTab   = 'overview';
        this.activeTheme = (() => {
            try { return localStorage.getItem('admin-dash-theme') || 'midnight'; } catch(e) { return 'midnight'; }
        })();
        // Data stores
        this.requests    = [];
        this.vehicles    = [];
        this.tripLogs    = [];
        this.fuelIssues  = [];
        this.facilities  = [];
        this.maintenanceRequests = [];
        this.workOrders  = [];
        this.utilMeters  = [];
        this.utilConsumed= [];
        this.genLogs     = [];
        this.visitors    = [];
        this.incidents   = [];
        this.contracts   = [];
        this.providers   = [];
        this.compliance  = [];
        this.assetInspections = [];
        this.hseInspections   = [];
        this.meetingBookings  = [];
        this.timer       = null;

        window.__adminDash = this;
        this.init();
    }

    init() {
        this.injectCSS();
        this.buildLayout();
        this.applyTheme(this.activeTheme, false);
        this.setupActions();
        this.bindEvents();
        this.startClock();
        this.loadData();
        this.startAutoRefresh();
    }

    // ─── THEME ENGINE ──────────────────────────────────────────────────────────
    applyTheme(key, save = true) {
        const t = ADMIN_THEMES[key] || ADMIN_THEMES.midnight;
        this.activeTheme = key;
        if (save) { try { localStorage.setItem('admin-dash-theme', key); } catch(e) {} }
        const root = document.getElementById('ad-root');
        if (!root) return;
        Object.entries(t).forEach(([k, v]) => { if (k.startsWith('--')) root.style.setProperty(k, v); });
        if (t.isDark) root.classList.add('ad-dark'); else root.classList.remove('ad-dark');
        const lbl = document.getElementById('ad-theme-label');
        if (lbl) lbl.textContent = t.icon + ' ' + t.name;
        Object.values(this.charts).forEach(c => { try { c.update(); } catch(e) {} });
    }

    openThemePicker() {
        const cur = this.activeTheme;
        const html = Object.entries(ADMIN_THEMES).map(([key, t]) => `
            <div onclick="window.__adminDash.applyTheme('${key}');if(cur_dialog)cur_dialog.hide();"
                 style="display:flex;align-items:center;gap:12px;padding:12px 14px;border-radius:10px;
                        border:2px solid ${key===cur?t['--ad-pri']:(t['--ad-brd2']||'#CBD5E1')};
                        background:${t['--ad-card']||'#fff'};cursor:pointer;transition:all .18s">
                <div style="font-size:24px;width:38px;height:38px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:${t['--ad-pri-x']||'rgba(0,0,0,.05)'}">
                    ${t.icon}
                </div>
                <div style="flex:1">
                    <div style="font-size:13px;font-weight:700;color:${t['--ad-tx1']||'#0F172A'}">${t.name}</div>
                    <div style="font-size:10px;color:${t['--ad-tx3']||'#94A3B8'}">${t.isDark ? '🌙 Dark' : '☀️ Light'}</div>
                </div>
                ${key===cur ? `<span style="color:${t['--ad-pri']||'#0284C7'};font-size:18px">✓</span>` : ''}
            </div>`).join('');

        const d = new frappe.ui.Dialog({
            title: '🎨 Dashboard Theme',
            size: 'large',
            fields: [{ fieldtype: 'HTML', options: `
                <p style="font-size:12px;color:var(--ad-tx3);margin:0 0 12px">Stored in browser only. Applies instantly to all charts and panels.</p>
                <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px">${html}</div>`
            }]
        });
        d.show();
    }

    // ─── CSS INJECTION ─────────────────────────────────────────────────────────
    injectCSS() {
        if (document.getElementById('ad-css')) return;
        const s = document.createElement('style');
        s.id = 'ad-css';
        s.textContent = `
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap');

#ad-root {
    --ad-pri:#0284C7; --ad-pri-d:#0369A1; --ad-pri-x:rgba(2,132,199,.09); --ad-acc:#38BDF8;
    --ad-red:#EF4444; --ad-red-x:rgba(239,68,68,.09);
    --ad-amb:#F59E0B; --ad-amb-x:rgba(245,158,11,.09);
    --ad-grn:#10B981; --ad-grn-x:rgba(16,185,129,.09);
    --ad-sky:#06B6D4; --ad-sky-x:rgba(6,182,212,.09);
    --ad-pur:#8B5CF6; --ad-pur-x:rgba(139,92,246,.09);
    --ad-bg:#F8FAFC; --ad-bg2:#F1F5F9; --ad-bg3:#E2E8F0;
    --ad-card:#FFFFFF; --ad-brd:#E2E8F0; --ad-brd2:#CBD5E1;
    --ad-tx1:#0F172A; --ad-tx2:#475569; --ad-tx3:#94A3B8;
    --ad-banner:linear-gradient(135deg,#0F172A 0%,#1E3A5F 40%,#0284C7 75%,#06B6D4 100%);
    font-family:'Inter',system-ui,sans-serif;
    background:var(--ad-bg); color:var(--ad-tx1);
    min-height:100vh; transition:background .3s,color .3s;
}
#ad-root * { box-sizing:border-box; }
#ad-root.ad-dark input,#ad-root.ad-dark select,#ad-root.ad-dark textarea { color-scheme:dark; }

/* BANNER */
.ad-banner { background:var(--ad-banner);padding:20px 24px 16px;margin:-15px -15px 20px;position:relative;overflow:hidden;color:#fff; }
.ad-banner::before { content:'';position:absolute;width:600px;height:600px;top:-50%;right:-8%;border-radius:50%;background:radial-gradient(circle,rgba(255,255,255,.05) 0%,transparent 65%); }
.ad-banner-inner { position:relative;z-index:1;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px; }
.ad-banner h1 { font-size:22px;font-weight:800;letter-spacing:-.5px;margin:0 0 6px;display:flex;align-items:center;gap:10px; }
.ad-banner-meta { display:flex;align-items:center;gap:14px;font-size:12px;opacity:.82;flex-wrap:wrap; }
.ad-live { display:inline-flex;align-items:center;gap:5px;background:rgba(16,185,129,.22);padding:3px 10px;border-radius:20px;font-size:11px;color:#34d399;border:1px solid rgba(16,185,129,.3); }
.ad-dot  { width:7px;height:7px;background:#34d399;border-radius:50%;animation:ad-pulse 2s infinite; }
@keyframes ad-pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.4;transform:scale(1.3)} }
.ad-chip { display:inline-flex;align-items:center;gap:5px;background:rgba(255,255,255,.14);padding:4px 11px;border-radius:20px;font-size:11px;font-weight:600; }
.ad-theme-btn { display:inline-flex;align-items:center;gap:6px;padding:5px 13px;border-radius:20px;font-size:11px;font-weight:700;background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.25);color:#fff;cursor:pointer;transition:all .18s;font-family:inherit; }
.ad-theme-btn:hover { background:rgba(255,255,255,.3); }

/* ALERTS STRIP */
.ad-alerts { display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px; }
.ad-alert  { display:flex;align-items:center;gap:7px;padding:7px 13px;border-radius:9px;font-size:11px;font-weight:600;cursor:pointer;transition:all .18s;text-decoration:none !important;border:1px solid transparent; }
.ad-alert:hover { transform:translateY(-1px); }
.aa-red { background:var(--ad-red-x);border-color:rgba(239,68,68,.2);color:var(--ad-red); }
.aa-amb { background:var(--ad-amb-x);border-color:rgba(245,158,11,.2);color:var(--ad-amb); }
.aa-pri { background:var(--ad-pri-x);border-color:rgba(2,132,199,.2);color:var(--ad-pri); }
.aa-grn { background:var(--ad-grn-x);border-color:rgba(16,185,129,.2);color:var(--ad-grn); }
.aa-pur { background:var(--ad-pur-x);border-color:rgba(139,92,246,.2);color:var(--ad-pur); }

/* TABS */
.ad-tabs { display:flex;gap:2px;background:var(--ad-card);border:1px solid var(--ad-brd);border-radius:12px;margin-bottom:18px;overflow-x:auto;scrollbar-width:none; }
.ad-tabs::-webkit-scrollbar { display:none; }
.ad-tab { display:flex;align-items:center;gap:6px;padding:10px 14px;font-size:12px;font-weight:600;color:var(--ad-tx2);cursor:pointer;border-bottom:3px solid transparent;transition:all .18s;white-space:nowrap;background:none;border-left:none;border-right:none;border-top:none;font-family:inherit; }
.ad-tab:hover  { color:var(--ad-pri);background:var(--ad-pri-x); }
.ad-tab.active { color:var(--ad-pri);border-bottom-color:var(--ad-pri);background:var(--ad-pri-x); }
.ad-tab-n { background:var(--ad-red);color:#fff;font-size:9px;font-weight:800;padding:1px 6px;border-radius:20px;min-width:16px;text-align:center; }

/* KPI STRIP */
.ad-kpis { display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:18px; }
.ad-kpi  { background:var(--ad-card);border:1px solid var(--ad-brd);border-radius:14px;padding:16px 18px;cursor:pointer;transition:all .2s;position:relative;overflow:hidden; }
.ad-kpi::after { content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--kc,var(--ad-pri));opacity:0;transition:opacity .2s; }
.ad-kpi:hover { transform:translateY(-3px);box-shadow:0 8px 24px rgba(0,0,0,.12); }
.ad-kpi:hover::after { opacity:1; }
.kc-pri::after{background:var(--ad-pri)} .kc-grn::after{background:var(--ad-grn)} .kc-red::after{background:var(--ad-red)} .kc-amb::after{background:var(--ad-amb)} .kc-sky::after{background:var(--ad-sky)} .kc-pur::after{background:var(--ad-pur)}
.ad-kpi-icon { font-size:17px;margin-bottom:8px; }
.ad-kpi-lbl  { font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:var(--ad-tx3);margin-bottom:5px; }
.ad-kpi-val  { font-size:26px;font-weight:800;color:var(--ad-tx1);line-height:1;margin-bottom:3px; }
.ad-kpi-sub  { font-size:11px;color:var(--ad-tx3); }

/* CARDS */
.ad-card { background:var(--ad-card);border:1px solid var(--ad-brd);border-radius:14px;overflow:hidden;transition:box-shadow .2s; }
.ad-card:hover { box-shadow:0 4px 20px rgba(0,0,0,.08); }
.ad-ch { padding:13px 18px;border-bottom:1px solid var(--ad-brd);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px; }
.ad-ct { display:flex;align-items:center;gap:9px;font-size:13px;font-weight:700;color:var(--ad-tx1); }
.ad-ci { width:26px;height:26px;border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:12px; }
.ad-cb { padding:14px 18px; }

/* GRIDS */
.ad-g2  { display:grid;grid-template-columns:1fr 1fr;    gap:14px;margin-bottom:14px; }
.ad-g3  { display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;margin-bottom:14px; }
.ad-g4  { display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:14px; }
.ad-g21 { display:grid;grid-template-columns:2fr 1fr;    gap:14px;margin-bottom:14px; }
.ad-g31 { display:grid;grid-template-columns:3fr 1fr;    gap:14px;margin-bottom:14px; }
.ad-row { margin-bottom:14px; }

/* BUTTONS */
.ad-acts { display:flex;gap:7px;flex-wrap:wrap;align-items:center; }
.ad-btn { display:inline-flex;align-items:center;gap:6px;padding:6px 13px;border-radius:20px;font-size:11px;font-weight:700;cursor:pointer;border:1.5px solid transparent;font-family:inherit;transition:all .18s;line-height:1.4;text-decoration:none !important; }
.ad-btn:hover { transform:translateY(-1px); }
.ab-pri  { background:var(--ad-pri-x);color:var(--ad-pri);border-color:rgba(2,132,199,.2); }
.ab-pri:hover  { background:var(--ad-pri);color:#fff; }
.ab-grn  { background:var(--ad-grn-x);color:var(--ad-grn);border-color:rgba(16,185,129,.2); }
.ab-grn:hover  { background:var(--ad-grn);color:#fff; }
.ab-red  { background:var(--ad-red-x);color:var(--ad-red);border-color:rgba(239,68,68,.2); }
.ab-red:hover  { background:var(--ad-red);color:#fff; }
.ab-amb  { background:var(--ad-amb-x);color:var(--ad-amb);border-color:rgba(245,158,11,.2); }
.ab-amb:hover  { background:var(--ad-amb);color:#fff; }
.ab-sky  { background:var(--ad-sky-x);color:var(--ad-sky);border-color:rgba(6,182,212,.2); }
.ab-sky:hover  { background:var(--ad-sky);color:#fff; }
.ab-pur  { background:var(--ad-pur-x);color:var(--ad-pur);border-color:rgba(139,92,246,.2); }
.ab-pur:hover  { background:var(--ad-pur);color:#fff; }
.ab-ghost { background:transparent;color:var(--ad-tx2);border-color:var(--ad-brd2); }
.ab-ghost:hover { background:var(--ad-bg2);color:var(--ad-tx1); }
.ab-solid { background:var(--ad-pri);color:#fff;border-color:var(--ad-pri); }
.ab-solid:hover { background:var(--ad-pri-d); }

/* BADGE */
.ad-badge { display:inline-flex;align-items:center;gap:3px;padding:3px 8px;border-radius:20px;font-size:10px;font-weight:700;white-space:nowrap; }
.bg-grn  { background:var(--ad-grn-x);color:var(--ad-grn); }
.bg-red  { background:var(--ad-red-x);color:var(--ad-red); }
.bg-amb  { background:var(--ad-amb-x);color:var(--ad-amb); }
.bg-pri  { background:var(--ad-pri-x);color:var(--ad-pri); }
.bg-sky  { background:var(--ad-sky-x);color:var(--ad-sky); }
.bg-pur  { background:var(--ad-pur-x);color:var(--ad-pur); }
.bg-grey { background:var(--ad-bg3);color:var(--ad-tx3);border:1px solid var(--ad-brd2); }

/* TABLE */
.ad-tbl-wrap { overflow-x:auto;max-height:460px;overflow-y:auto;scrollbar-width:thin;scrollbar-color:var(--ad-brd2) transparent; }
.ad-tbl { width:100%;border-collapse:collapse;font-size:12px; }
.ad-tbl thead th { padding:9px 13px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--ad-tx3);background:var(--ad-bg2);border-bottom:2px solid var(--ad-brd);position:sticky;top:0;white-space:nowrap;z-index:1; }
.ad-tbl tbody td { padding:9px 13px;border-bottom:1px solid var(--ad-brd);color:var(--ad-tx2); }
.ad-tbl tbody tr { cursor:pointer;transition:background .1s; }
.ad-tbl tbody tr:hover { background:var(--ad-pri-x); }
.ad-tbl tbody tr:hover td { color:var(--ad-tx1); }
.ad-tbl tbody tr:last-child td { border-bottom:none; }

/* PROGRESS BAR */
.ad-bar-row { display:flex;align-items:center;gap:10px;margin-bottom:8px; }
.ad-bar-lbl { font-size:11px;color:var(--ad-tx2);width:150px;flex-shrink:0; }
.ad-bar     { flex:1;height:5px;background:var(--ad-brd);border-radius:40px;overflow:hidden; }
.ad-bar-fill{ height:100%;border-radius:40px;transition:width .6s cubic-bezier(.4,0,.2,1); }
.ad-bar-val { font-size:11px;font-family:'JetBrains Mono',monospace;font-weight:700;width:50px;text-align:right;color:var(--ad-tx1); }

/* LIST ITEM */
.ad-li { display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--ad-brd);font-size:12px;gap:10px; }
.ad-li:last-child { border-bottom:none; }
.ad-li-l { flex:1;min-width:0; }
.ad-li-title { font-weight:600;color:var(--ad-tx1);white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
.ad-li-sub   { font-size:10px;color:var(--ad-tx3);margin-top:1px; }

/* ALERT BOX (inline) */
.ad-alert-box { display:flex;align-items:flex-start;gap:9px;padding:9px 12px;border-radius:10px;margin-bottom:7px;font-size:12px; }
.ad-alert-box:last-child { margin-bottom:0; }
.aab-r { background:var(--ad-red-x);border:1px solid rgba(239,68,68,.2); }
.aab-a { background:var(--ad-amb-x);border:1px solid rgba(245,158,11,.2); }
.aab-g { background:var(--ad-grn-x);border:1px solid rgba(16,185,129,.2); }
.aab-b { background:var(--ad-pri-x);border:1px solid rgba(2,132,199,.2); }
.ad-alert-box .ait { font-weight:700;color:var(--ad-tx1); }
.ad-alert-box .ais { color:var(--ad-tx2);margin-top:2px; }

/* VEHICLE CARD */
.ad-veh { display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid var(--ad-brd); }
.ad-veh:last-child { border-bottom:none; }
.ad-veh-icon { width:30px;height:30px;border-radius:8px;background:var(--ad-bg2);display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0; }
.ad-veh-name { font-size:12px;font-weight:600;color:var(--ad-tx1); }
.ad-veh-sub  { font-size:10px;color:var(--ad-tx3); }

/* UTIL ROW */
.ad-util-row { display:flex;align-items:center;gap:10px;padding:7px 0;border-bottom:1px solid var(--ad-brd); }
.ad-util-row:last-child { border-bottom:none; }
.ad-util-icon { width:26px;height:26px;border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:12px;flex-shrink:0; }
.ad-util-lbl { flex:1;font-size:12px;color:var(--ad-tx1); }
.ad-util-val { font-size:12px;font-weight:700;color:var(--ad-tx1); }

/* AI PANEL */
.ad-ai-box { background:var(--ad-bg2);border:1px solid var(--ad-brd);border-radius:10px;padding:12px;margin-top:10px; }
.ad-ai-hdr { display:flex;align-items:center;gap:7px;font-size:11px;font-weight:700;color:var(--ad-pri);margin-bottom:8px; }
.ad-ai-item { display:flex;gap:8px;margin-bottom:7px;font-size:12px;color:var(--ad-tx2);line-height:1.5; }
.ad-ai-item:last-child { margin-bottom:0; }
.ad-ai-dot { width:5px;height:5px;border-radius:50%;background:var(--ad-pri);flex-shrink:0;margin-top:5px; }
.ad-ai-spin { animation:ad-spin .8s linear infinite; }
@keyframes ad-spin { to { transform:rotate(360deg); } }

/* STAT GRID */
.ad-stat-grid { display:grid;grid-template-columns:repeat(auto-fit,minmax(90px,1fr));gap:8px; }
.ad-stat { background:var(--ad-bg2);border-radius:10px;padding:10px;text-align:center; }
.ad-stat-val { font-size:18px;font-weight:800;color:var(--ad-tx1); }
.ad-stat-lbl { font-size:9px;text-transform:uppercase;letter-spacing:.5px;color:var(--ad-tx3);margin-top:2px; }

/* FORM FIELD */
.ad-fg { display:flex;flex-direction:column;gap:4px; }
.ad-fg label { font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:var(--ad-tx3); }
.ad-inp,.ad-sel { background:var(--ad-bg3);border:1.5px solid var(--ad-brd2);border-radius:8px;color:var(--ad-tx1);font-family:'Inter',system-ui;font-size:12px;padding:8px 12px;outline:none;width:100%;transition:border-color .15s; }
.ad-inp:focus,.ad-sel:focus { border-color:var(--ad-pri);box-shadow:0 0 0 3px var(--ad-pri-x); }
.ad-sel { cursor:pointer; }

/* LOADER */
.ad-loader { position:fixed;inset:0;background:rgba(10,15,30,.8);display:flex;align-items:center;justify-content:center;flex-direction:column;gap:14px;z-index:999; }
.ad-spinner { width:38px;height:38px;border:3px solid var(--ad-brd2);border-top-color:var(--ad-pri);border-radius:50%;animation:ad-spin .7s linear infinite; }

/* DIVIDER */
.ad-hr { border:none;border-top:1px solid var(--ad-brd);margin:16px 0; }

/* CONTENT */
.ad-content { padding:0 16px 32px; }

/* PANEL WRAP */
.ad-panel { display:none; }
.ad-panel.active { display:block; }

/* SCROLLBAR */
.ad-tbl-wrap::-webkit-scrollbar { width:4px;height:4px; }
.ad-tbl-wrap::-webkit-scrollbar-thumb { background:var(--ad-brd2);border-radius:10px; }

/* RESPONSIVE */
@media(max-width:1100px) { .ad-g21,.ad-g31 { grid-template-columns:1fr; } }
@media(max-width:800px)  { .ad-g2,.ad-g3,.ad-g4 { grid-template-columns:1fr; } }
@media print { .ad-banner .ad-theme-btn,.ad-acts,.ad-tabs { display:none !important; } }
        `;
        document.head.appendChild(s);
    }

    // ─── LAYOUT ────────────────────────────────────────────────────────────────
    buildLayout() {
        $(this.page.main).empty();
        $(`
        <div id="ad-root">
            <div class="ad-banner">
                <div class="ad-banner-inner">
                    <div>
                        <h1>🏢 Admin 360° Power Dashboard</h1>
                        <div class="ad-banner-meta">
                            <span>📅 <span id="ad-date"></span></span>
                            <span id="ad-clock" style="font-family:'JetBrains Mono',monospace"></span>
                            <span class="ad-live"><span class="ad-dot"></span> Live · auto-refresh 30s</span>
                            <span class="ad-chip" id="ad-chip-requests">— Requests</span>
                            <span class="ad-chip" id="ad-chip-fleet">— Fleet</span>
                            <span class="ad-chip" id="ad-chip-contracts">— Contracts</span>
                        </div>
                    </div>
                    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
                        <button class="ad-theme-btn" onclick="window.__adminDash.openThemePicker()">
                            🎨 <span id="ad-theme-label">🌙 Midnight</span>
                        </button>
                        <span id="ad-ts" style="font-size:11px;opacity:.6"></span>
                    </div>
                </div>
            </div>

            <div class="ad-content">
                <div class="ad-alerts" id="ad-alerts"></div>

                <div class="ad-tabs" id="ad-tabs">
                    <button class="ad-tab active" data-tab="overview">🏠 Overview</button>
                    <button class="ad-tab" data-tab="requests">📋 Requests<span class="ad-tab-n" id="ad-n-req" style="display:none">0</span></button>
                    <button class="ad-tab" data-tab="fleet">🚗 Fleet<span class="ad-tab-n" id="ad-n-fleet" style="display:none">0</span></button>
                    <button class="ad-tab" data-tab="facilities">🏗 Facilities<span class="ad-tab-n" id="ad-n-fac" style="display:none">0</span></button>
                    <button class="ad-tab" data-tab="utilities">⚡ Utilities</button>
                    <button class="ad-tab" data-tab="security">🛡 Security<span class="ad-tab-n" id="ad-n-sec" style="display:none">0</span></button>
                    <button class="ad-tab" data-tab="contracts">📑 Contracts<span class="ad-tab-n" id="ad-n-con" style="display:none">0</span></button>
                    <button class="ad-tab" data-tab="compliance">🎖 Compliance<span class="ad-tab-n" id="ad-n-comp" style="display:none">0</span></button>
                    <button class="ad-tab" data-tab="hse">⚠️ HSE</button>
                    <button class="ad-tab" data-tab="intelligence">🤖 AI Intelligence</button>
                </div>

                <div id="ad-panel-overview"     class="ad-panel active"></div>
                <div id="ad-panel-requests"     class="ad-panel"></div>
                <div id="ad-panel-fleet"        class="ad-panel"></div>
                <div id="ad-panel-facilities"   class="ad-panel"></div>
                <div id="ad-panel-utilities"    class="ad-panel"></div>
                <div id="ad-panel-security"     class="ad-panel"></div>
                <div id="ad-panel-contracts"    class="ad-panel"></div>
                <div id="ad-panel-compliance"   class="ad-panel"></div>
                <div id="ad-panel-hse"          class="ad-panel"></div>
                <div id="ad-panel-intelligence" class="ad-panel"></div>
            </div>

            <div class="ad-loader" id="ad-loader" style="display:none">
                <div class="ad-spinner"></div>
                <div style="font-weight:600;font-size:14px;color:#F1F5F9">Loading Admin Dashboard</div>
                <div style="font-size:12px;color:#94A3B8">Fetching requests, fleet, facilities, utilities & compliance…</div>
            </div>
        </div>
        `).appendTo(this.page.main);
    }

    setupActions() {
        this.page.add_inner_button('🔄 Refresh', () => this.loadData());
        this.page.add_inner_button('📋 New Request', () => frappe.new_doc('Administrative Request'));
        this.page.add_inner_button('🚗 New Trip Log', () => frappe.new_doc('Vehicle Trip Log'));
        this.page.add_inner_button('👤 Visitor Check-In', () => frappe.new_doc('Visitor Register'));
        this.page.add_menu_item('🎨 Theme Picker', () => this.openThemePicker());
        this.page.add_menu_item('🖨️ Print Dashboard', () => window.print());
        this.page.add_menu_item('📊 Export to Excel', () => this.exportData());
    }

    bindEvents() {
        $(document).on('click', '.ad-tab', (e) => {
            const tab = $(e.currentTarget).data('tab');
            this.switchTab(tab);
        });
    }

    switchTab(name) {
        $('.ad-tab').removeClass('active');
        $(`.ad-tab[data-tab="${name}"]`).addClass('active');
        $('.ad-panel').removeClass('active');
        $(`#ad-panel-${name}`).addClass('active');
        this.activeTab = name;
        if (this.requests.length || this.vehicles.length) this.renderTab(name);
    }

    startClock() {
        const tick = () => {
            $('#ad-clock').text(new Date().toLocaleTimeString('en-NG', { hour12: true, hour: '2-digit', minute: '2-digit', second: '2-digit' }));
            $('#ad-date').text(frappe.datetime.str_to_user(frappe.datetime.get_today()));
        };
        tick(); setInterval(tick, 1000);
    }

    startAutoRefresh() {
        this.stopAutoRefresh();
        this.timer = setInterval(() => this.loadData(true), 30000);
    }
    stopAutoRefresh() { if (this.timer) { clearInterval(this.timer); this.timer = null; } }

    // ─── DATA LOAD ─────────────────────────────────────────────────────────────
    async loadData(silent = false) {
        if (!silent) $('#ad-loader').show();
        try {
            const safe = async (method, args) => {
                try { const r = await frappe.call({ method, args }); return r.message || []; }
                catch(e) { console.warn(`Admin dash: ${args.doctype || 'unknown'} fetch failed:`, e.message); return []; }
            };
            const safeGet = async (doctype, name) => {
                try { const r = await frappe.call({ method:'frappe.client.get', args:{ doctype, name } }); return r.message || null; }
                catch(e) { return null; }
            };

            const gl = 'frappe.client.get_list';
            const F  = ['name'];

            [
                this.requests, this.vehicles, this.tripLogs, this.fuelIssues,
                this.facilities, this.maintenanceRequests, this.workOrders,
                this.utilMeters, this.utilConsumed, this.genLogs,
                this.visitors, this.incidents, this.contracts,
                this.providers, this.compliance, this.assetInspections,
                this.hseInspections, this.meetingBookings
            ] = await Promise.all([
                safe(gl, { doctype:'Administrative Request',
                    fields:['name','request_title','request_type','priority','status','employee','department',
                            'request_date','required_by_date','estimated_cost','actual_cost','sla_breached',
                            'request_age_days','company','completion_days'],
                    limit_page_length:500, order_by:'modified desc' }),

                safe(gl, { doctype:'Company Vehicle',
                    fields:['name','vehicle_name','plate_number','vehicle_type','brand','model','status',
                            'department','assigned_driver','fuel_type','odometer_reading',
                            'insurance_expiry','license_expiry','road_worthiness_expiry',
                            'fuel_cost_ytd','maintenance_cost_ytd','total_km_ytd','cost_per_km','trips_ytd'],
                    limit_page_length:200, order_by:'vehicle_name asc' }),

                safe(gl, { doctype:'Vehicle Trip Log',
                    fields:['name','vehicle','driver','trip_date','purpose','destination',
                            'distance_km','total_fuel_cost','odometer_start','odometer_end'],
                    limit_page_length:300, order_by:'trip_date desc' }),

                safe(gl, { doctype:'Fuel Issue',
                    fields:['name','vehicle','driver','issue_date','fuel_type','litres_issued','total_cost','issue_method'],
                    limit_page_length:200, order_by:'issue_date desc' }),

                safe(gl, { doctype:'Facility',
                    fields:['name','facility_name','facility_type','status','company','branch',
                            'department','open_maintenance_requests','maintenance_cost_ytd',
                            'utility_cost_ytd','capacity','floor_area_sqm','lease_expiry_date'],
                    limit_page_length:100, order_by:'facility_name asc' }),

                safe(gl, { doctype:'Facility Maintenance Request',
                    fields:['name','subject','facility','maintenance_category','priority','status',
                            'reported_by','report_date','estimated_cost','actual_cost','vendor'],
                    limit_page_length:300, order_by:'modified desc' }),

                safe(gl, { doctype:'Maintenance Work Order',
                    fields:['name','title','facility','work_type','status','priority',
                            'start_date','end_date','estimated_cost','actual_cost','lead_technician'],
                    limit_page_length:200, order_by:'modified desc' }),

                safe(gl, { doctype:'Utility Meter',
                    fields:['name','meter_name','utility_type','facility','status','unit_of_measure','rate_per_unit'],
                    limit_page_length:100 }),

                safe(gl, { doctype:'Utility Consumption',
                    fields:['name','utility_meter','facility','utility_type','period_month','period_year',
                            'consumption','total_bill','variance_pct','avg_daily_consumption','reading_date'],
                    limit_page_length:300, order_by:'reading_date desc' }),

                safe(gl, { doctype:'Generator Log',
                    fields:['name','facility','log_date','run_hours','fuel_consumed_litres','fuel_cost',
                            'reason_for_running','diesel_rate_per_litre'],
                    limit_page_length:200, order_by:'log_date desc' }),

                safe(gl, { doctype:'Visitor Register',
                    fields:['name','visitor_name','visitor_company','host_employee','visit_date',
                            'check_in_time','check_out_time','status','purpose_of_visit','facility'],
                    limit_page_length:300, order_by:'visit_date desc' }),

                safe(gl, { doctype:'Security Incident',
                    fields:['name','incident_title','incident_type','severity','status','facility',
                            'incident_date','reported_by','estimated_loss','police_report_no'],
                    limit_page_length:200, order_by:'incident_date desc' }),

                safe(gl, { doctype:'Service Contract',
                    fields:['name','contract_title','contract_type','vendor','service_provider',
                            'start_date','end_date','contract_value','status','days_to_expiry',
                            'renewal_reminder_days','sla_response_hours'],
                    limit_page_length:200, order_by:'end_date asc' }),

                safe(gl, { doctype:'Service Provider',
                    fields:['name','provider_name','service_category','status','supplier',
                            'performance_score','active_contracts','phone','email'],
                    limit_page_length:100, order_by:'provider_name asc' }),

                safe(gl, { doctype:'Compliance Register',
                    fields:['name','compliance_item','compliance_type','issuing_authority','facility',
                            'expiry_date','status','renewal_cost','certificate_no'],
                    limit_page_length:200, order_by:'expiry_date asc' }),

                safe(gl, { doctype:'Asset Inspection',
                    fields:['name','asset','facility','inspection_date','inspection_type',
                            'overall_condition','status','inspector'],
                    limit_page_length:200, order_by:'inspection_date desc' }),

                safe(gl, { doctype:'HSE Inspection',
                    fields:['name','facility','inspection_date','inspection_type','overall_score',
                            'pass_fail','status','inspector'],
                    limit_page_length:200, order_by:'inspection_date desc' }),

                safe(gl, { doctype:'Meeting Room Booking',
                    fields:['name','meeting_title','facility','booking_date','start_time','end_time',
                            'booked_by','status','attendees_count'],
                    limit_page_length:200, order_by:'booking_date desc' }),
            ]);

            this.renderAll();
            $('#ad-ts').text('Updated ' + new Date().toLocaleTimeString('en-NG', { hour12:true }));

        } catch(e) {
            console.error('Admin Dashboard loadData error:', e);
            if (!silent) frappe.msgprint({ title:'Load Error', indicator:'red', message:'Failed to load admin data. Ensure DocTypes are installed.' });
        } finally {
            $('#ad-loader').hide();
        }
    }

    // ─── HELPERS ───────────────────────────────────────────────────────────────
    fmt(v, dp=0) {
        const n = parseFloat(v) || 0;
        if (n >= 1e9) return '₦' + (n/1e9).toFixed(1) + 'B';
        if (n >= 1e6) return '₦' + (n/1e6).toFixed(1) + 'M';
        if (n >= 1e3) return '₦' + (n/1e3).toFixed(0) + 'k';
        return '₦' + n.toFixed(dp);
    }
    flt(v) { return parseFloat(v) || 0; }
    n(v)   { return parseInt(v) || 0; }

    kpi(icon, cls, label, val, sub, link='#') {
        return `<div class="ad-kpi ${cls}" onclick="frappe.set_route('${link}')" style="--kc:var(--ad-pri)">
            <div class="ad-kpi-icon">${icon}</div>
            <div class="ad-kpi-lbl">${label}</div>
            <div class="ad-kpi-val">${val}</div>
            <div class="ad-kpi-sub">${sub}</div>
        </div>`;
    }

    badge(text, cls) { return `<span class="ad-badge ${cls}">${text}</span>`; }

    statusBadge(status) {
        const map = {
            'Draft':'bg-grey','Submitted':'bg-pri','Approved':'bg-sky','In Progress':'bg-amb',
            'Completed':'bg-grn','Rejected':'bg-red','Closed':'bg-grey','Cancelled':'bg-grey',
            'Open':'bg-pri','Active':'bg-grn','Expired':'bg-red','Expiring Soon':'bg-amb',
            'Valid':'bg-grn','Under Investigation':'bg-pur','Resolved':'bg-grn',
            'Escalated to Police':'bg-red','Available':'bg-grn','In Use':'bg-pri',
            'Under Maintenance':'bg-amb','Grounded':'bg-red','Sold':'bg-grey',
            'Confirmed':'bg-grn','Pending':'bg-amb','Pass':'bg-grn','Fail':'bg-red',
            'Conditional Pass':'bg-amb','Reported':'bg-pri',
        };
        return this.badge(status, map[status] || 'bg-grey');
    }

    severityBadge(sev) {
        const m = { 'Minor':'bg-sky','Moderate':'bg-amb','Severe':'bg-red','Critical':'bg-red','Emergency':'bg-red','High':'bg-red','Medium':'bg-amb','Low':'bg-grn','Urgent':'bg-red' };
        return this.badge(sev, m[sev] || 'bg-grey');
    }

    daysLeft(dateStr) {
        if (!dateStr) return null;
        return Math.ceil((new Date(dateStr) - new Date()) / 86400000);
    }

    daysLeftBadge(dateStr) {
        const d = this.daysLeft(dateStr);
        if (d === null) return '';
        if (d < 0)  return this.badge(`Expired ${Math.abs(d)}d`, 'bg-red');
        if (d <= 14) return this.badge(`${d}d left`, 'bg-red');
        if (d <= 30) return this.badge(`${d}d left`, 'bg-amb');
        if (d <= 60) return this.badge(`${d}d left`, 'bg-sky');
        return this.badge(`${d}d`, 'bg-grn');
    }

    chartColors() {
        return ['#0284C7','#10B981','#F59E0B','#8B5CF6','#EF4444','#06B6D4','#EC4899','#F97316','#22C55E','#94A3B8'];
    }

    destroyChart(id) {
        if (this.charts[id]) { try { this.charts[id].destroy(); } catch(e) {} delete this.charts[id]; }
    }

    makeChart(id, config) {
        this.destroyChart(id);
        const el = document.getElementById(id);
        if (!el) return;
        this.charts[id] = new Chart(el, config);
    }

    // ─── RENDER ALL ────────────────────────────────────────────────────────────
    renderAll() {
        // Badge counts
        const openReqs   = this.requests.filter(r => !['Completed','Closed','Rejected','Cancelled'].includes(r.status)).length;
        const breachedSLA= this.requests.filter(r => r.sla_breached == 1).length;
        const groundedVeh= this.vehicles.filter(v => v.status === 'Grounded').length;
        const openMaint  = this.maintenanceRequests.filter(m => !['Completed','Closed','Cancelled'].includes(m.status)).length;
        const openInc    = this.incidents.filter(i => !['Resolved','Closed'].includes(i.status)).length;
        const expiringCon= this.contracts.filter(c => { const d=this.daysLeft(c.end_date); return d !== null && d <= 60 && d >= 0; }).length;
        const expiredComp= this.compliance.filter(c => c.status === 'Expired').length;
        const expiringComp= this.compliance.filter(c => c.status === 'Expiring Soon').length;

        $('#ad-n-req').text(breachedSLA + openReqs).toggle(openReqs > 0);
        $('#ad-n-fleet').text(groundedVeh).toggle(groundedVeh > 0);
        $('#ad-n-fac').text(openMaint).toggle(openMaint > 0);
        $('#ad-n-sec').text(openInc).toggle(openInc > 0);
        $('#ad-n-con').text(expiringCon).toggle(expiringCon > 0);
        $('#ad-n-comp').text(expiredComp + expiringComp).toggle((expiredComp + expiringComp) > 0);

        // Banner chips
        $('#ad-chip-requests').text(`${openReqs} open requests`);
        $('#ad-chip-fleet').text(`${this.vehicles.filter(v=>v.status==='Available').length}/${this.vehicles.length} vehicles available`);
        $('#ad-chip-contracts').text(`${this.contracts.filter(c=>c.status==='Active').length} active contracts`);

        // Alerts
        const alerts = [];
        if (expiredComp > 0) alerts.push({ cls:'aa-red', icon:'🎖', label:`${expiredComp} compliance item${expiredComp>1?'s':''} EXPIRED`, link:'compliance' });
        if (breachedSLA > 0) alerts.push({ cls:'aa-red', icon:'⏱', label:`${breachedSLA} request${breachedSLA>1?'s':''} breached SLA`, link:'requests' });
        if (groundedVeh > 0) alerts.push({ cls:'aa-red', icon:'🚗', label:`${groundedVeh} vehicle${groundedVeh>1?'s':''} grounded`, link:'fleet' });
        if (openInc > 0)     alerts.push({ cls:'aa-amb', icon:'🛡', label:`${openInc} security incident${openInc>1?'s':''} open`, link:'security' });
        if (expiringCon > 0) alerts.push({ cls:'aa-amb', icon:'📑', label:`${expiringCon} contract${expiringCon>1?'s':''} expiring within 60 days`, link:'contracts' });
        if (expiringComp > 0)alerts.push({ cls:'aa-amb', icon:'⚠️', label:`${expiringComp} compliance item${expiringComp>1?'s':''} expiring soon`, link:'compliance' });
        if (openMaint > 0)   alerts.push({ cls:'aa-pri', icon:'🔧', label:`${openMaint} open maintenance request${openMaint>1?'s':''}`, link:'facilities' });

        const poorHSE = this.hseInspections.filter(h => h.pass_fail === 'Fail').length;
        if (poorHSE > 0) alerts.push({ cls:'aa-pur', icon:'⚠️', label:`${poorHSE} facility failed HSE inspection`, link:'hse' });

        $('#ad-alerts').html(
            alerts.map(a => `<a class="ad-alert ${a.cls}" onclick="window.__adminDash.switchTab('${a.link}');return false;" href="#">${a.icon} ${a.label}</a>`).join('') ||
            '<div class="ad-alert aa-grn">✅ All systems normal — no critical alerts</div>'
        );

        this.renderTab(this.activeTab);
    }

    renderTab(name) {
        const map = {
            overview:     () => this.renderOverview(),
            requests:     () => this.renderRequests(),
            fleet:        () => this.renderFleet(),
            facilities:   () => this.renderFacilities(),
            utilities:    () => this.renderUtilities(),
            security:     () => this.renderSecurity(),
            contracts:    () => this.renderContracts(),
            compliance:   () => this.renderCompliance(),
            hse:          () => this.renderHSE(),
            intelligence: () => this.renderIntelligence(),
        };
        if (map[name]) map[name]();
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  TAB: OVERVIEW
    // ═══════════════════════════════════════════════════════════════════════════
    renderOverview() {
        const today = frappe.datetime.get_today();
        const openReqs  = this.requests.filter(r => !['Completed','Closed','Rejected','Cancelled'].includes(r.status));
        const slaBreached = this.requests.filter(r => r.sla_breached == 1);
        const availVeh  = this.vehicles.filter(v => v.status === 'Available');
        const utilThisMonth = this.utilConsumed.filter(u => {
            const d = new Date(u.reading_date);
            const now = new Date();
            return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
        });
        const totalUtilCost = utilThisMonth.reduce((s,u) => s + this.flt(u.total_bill), 0);
        const genThisMonth  = this.genLogs.filter(g => g.log_date && g.log_date.substring(0,7) === today.substring(0,7));
        const totalGenCost  = genThisMonth.reduce((s,g) => s + this.flt(g.fuel_cost), 0);
        const totalGenHrs   = genThisMonth.reduce((s,g) => s + this.flt(g.run_hours), 0);
        const expiringCon   = this.contracts.filter(c => { const d=this.daysLeft(c.end_date); return d !== null && d >= 0 && d <= 60; });
        const openInc       = this.incidents.filter(i => !['Resolved','Closed'].includes(i.status));
        const expiredComp   = this.compliance.filter(c => c.status === 'Expired');
        const visitorsToday = this.visitors.filter(v => v.visit_date === today);

        const fuelYTD = this.vehicles.reduce((s,v) => s + this.flt(v.fuel_cost_ytd), 0);
        const maintYTD= this.maintenanceRequests.reduce((s,m) => s + this.flt(m.actual_cost), 0);

        // Spend by category for chart
        const spendData = [
            { label:'Utilities', v: totalUtilCost + totalGenCost },
            { label:'Fleet fuel', v: fuelYTD },
            { label:'Maintenance', v: maintYTD },
            { label:'Contracts', v: this.contracts.filter(c=>c.status==='Active').reduce((s,c)=>s+this.flt(c.contract_value)/12,0) },
        ].filter(x => x.v > 0);

        // Recent 7 days request activity
        const last7 = Array.from({length:7}, (_,i) => {
            const d = new Date(); d.setDate(d.getDate() - (6-i));
            return d.toISOString().substring(0,10);
        });
        const reqByDay = last7.map(d => this.requests.filter(r => r.request_date === d).length);

        $('#ad-panel-overview').html(`
            <div class="ad-kpis">
                ${this.kpi('📋','kc-pri','Open requests',    openReqs.length,    `${slaBreached.length} SLA breached`, '/app/administrative-request')}
                ${this.kpi('🚗','kc-sky','Available vehicles', availVeh.length,  `of ${this.vehicles.length} total`, '/app/company-vehicle')}
                ${this.kpi('⚡','kc-amb','Utility cost MTD',  this.fmt(totalUtilCost+totalGenCost), 'incl. generator diesel', '/app/utility-consumption')}
                ${this.kpi('⛽','kc-grn','Gen. runtime MTD', totalGenHrs.toFixed(0)+'h', this.fmt(totalGenCost) + ' diesel cost', '/app/generator-log')}
                ${this.kpi('📑','kc-red','Expiring contracts', expiringCon.length, 'within 60 days', '/app/service-contract')}
                ${this.kpi('🎖','kc-red','Compliance risk', expiredComp.length, 'items expired', '/app/compliance-register')}
                ${this.kpi('🛡','kc-pur','Open incidents', openInc.length, 'security incidents', '/app/security-incident')}
                ${this.kpi('👤','kc-sky','Visitors today', visitorsToday.length, `${visitorsToday.filter(v=>v.status==='Checked In').length} currently in`, '/app/visitor-register')}
            </div>

            <div class="ad-g21">
                <div class="ad-card">
                    <div class="ad-ch">
                        <div class="ad-ct"><span style="background:var(--ad-pri-x);padding:5px;border-radius:7px">📈</span> Request activity — last 7 days</div>
                        <div class="ad-acts">
                            <button class="ad-btn ab-pri" onclick="window.__adminDash.switchTab('requests')">View all</button>
                        </div>
                    </div>
                    <div class="ad-cb">
                        <div style="height:200px;position:relative"><canvas id="ad-ch-activity" aria-label="Request activity bar chart last 7 days">Daily admin request volumes over 7 days.</canvas></div>
                    </div>
                </div>
                <div class="ad-card">
                    <div class="ad-ch"><div class="ad-ct"><span style="background:var(--ad-amb-x);padding:5px;border-radius:7px">💰</span> Admin spend breakdown</div></div>
                    <div class="ad-cb">
                        <div style="height:200px;position:relative"><canvas id="ad-ch-spend" aria-label="Admin spend donut chart">Admin expenditure by category.</canvas></div>
                        <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:10px;font-size:11px;">
                            ${spendData.map((x,i) => `<span style="display:flex;align-items:center;gap:4px;color:var(--ad-tx2)"><span style="width:10px;height:10px;border-radius:2px;background:${this.chartColors()[i]};display:inline-block"></span>${x.label}: ${this.fmt(x.v)}</span>`).join('')}
                        </div>
                    </div>
                </div>
            </div>

            <div class="ad-g3">
                <div class="ad-card">
                    <div class="ad-ch"><div class="ad-ct">🚦 Fleet status snapshot</div><button class="ad-btn ab-ghost" onclick="window.__adminDash.switchTab('fleet')">Fleet tab →</button></div>
                    <div class="ad-cb">
                        ${this.vehicles.slice(0,5).map(v => `
                        <div class="ad-veh" onclick="frappe.set_route('Form','Company Vehicle','${v.name}')">
                            <div class="ad-veh-icon">${v.vehicle_type==='Bus'?'🚌':v.vehicle_type==='Truck'?'🚛':'🚗'}</div>
                            <div style="flex:1;min-width:0">
                                <div class="ad-veh-name">${v.vehicle_name||v.plate_number}</div>
                                <div class="ad-veh-sub">${v.plate_number} · ${v.vehicle_type}</div>
                            </div>
                            ${this.statusBadge(v.status)}
                        </div>`).join('')}
                        ${this.vehicles.length > 5 ? `<div style="font-size:11px;color:var(--ad-tx3);padding-top:8px">+${this.vehicles.length-5} more vehicles</div>` : ''}
                    </div>
                </div>

                <div class="ad-card">
                    <div class="ad-ch"><div class="ad-ct">🎖 Compliance radar</div><button class="ad-btn ab-ghost" onclick="window.__adminDash.switchTab('compliance')">Compliance tab →</button></div>
                    <div class="ad-cb">
                        ${this.compliance.slice(0,6).map(c => `
                        <div class="ad-li" onclick="frappe.set_route('Form','Compliance Register','${c.name}')">
                            <div class="ad-li-l">
                                <div class="ad-li-title">${c.compliance_item}</div>
                                <div class="ad-li-sub">${c.compliance_type}</div>
                            </div>
                            ${this.daysLeftBadge(c.expiry_date)}
                        </div>`).join('')}
                    </div>
                </div>

                <div class="ad-card">
                    <div class="ad-ch"><div class="ad-ct">📋 Urgent requests</div><button class="ad-btn ab-ghost" onclick="window.__adminDash.switchTab('requests')">Requests tab →</button></div>
                    <div class="ad-cb">
                        ${this.requests.filter(r => ['Urgent','High'].includes(r.priority) && !['Completed','Closed'].includes(r.status)).slice(0,5).map(r => `
                        <div class="ad-li" onclick="frappe.set_route('Form','Administrative Request','${r.name}')">
                            <div class="ad-li-l">
                                <div class="ad-li-title">${r.request_title||r.name}</div>
                                <div class="ad-li-sub">${r.request_type} · ${r.department||''} · ${r.request_age_days||0}d old</div>
                            </div>
                            ${this.severityBadge(r.priority)}
                        </div>`).join('') || '<div style="color:var(--ad-tx3);font-size:12px;padding:8px 0">No urgent open requests 🎉</div>'}
                    </div>
                </div>
            </div>

            <div class="ad-g2">
                <div class="ad-card">
                    <div class="ad-ch"><div class="ad-ct">📑 Contracts expiring — next 90 days</div></div>
                    <div class="ad-cb">
                        <div class="ad-tbl-wrap">
                            <table class="ad-tbl">
                                <thead><tr><th>Contract</th><th>Vendor</th><th>Value / yr</th><th>Expires</th><th>Status</th></tr></thead>
                                <tbody>
                                ${this.contracts.filter(c => { const d=this.daysLeft(c.end_date); return d!==null && d>=0 && d<=90; })
                                    .map(c => `<tr onclick="frappe.set_route('Form','Service Contract','${c.name}')">
                                        <td>${c.contract_title}</td>
                                        <td style="color:var(--ad-tx3)">${c.vendor||''}</td>
                                        <td>${this.fmt(c.contract_value)}</td>
                                        <td style="font-family:'JetBrains Mono',monospace;font-size:11px">${c.end_date||''}</td>
                                        <td>${this.daysLeftBadge(c.end_date)}</td>
                                    </tr>`).join('') || '<tr><td colspan="5" style="text-align:center;color:var(--ad-tx3);padding:20px">No contracts expiring in 90 days</td></tr>'}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <div class="ad-card">
                    <div class="ad-ch"><div class="ad-ct">🛡 Security & visitors today</div></div>
                    <div class="ad-cb">
                        <div class="ad-stat-grid" style="margin-bottom:14px">
                            <div class="ad-stat"><div class="ad-stat-val">${visitorsToday.length}</div><div class="ad-stat-lbl">Visitors</div></div>
                            <div class="ad-stat"><div class="ad-stat-val" style="color:var(--ad-grn)">${visitorsToday.filter(v=>v.status==='Checked In').length}</div><div class="ad-stat-lbl">In building</div></div>
                            <div class="ad-stat"><div class="ad-stat-val" style="color:var(--ad-red)">${openInc.length}</div><div class="ad-stat-lbl">Open incidents</div></div>
                        </div>
                        ${openInc.slice(0,4).map(i => `
                        <div class="ad-alert-box aab-${i.severity==='Minor'?'b':i.severity==='Moderate'?'a':'r'}" onclick="frappe.set_route('Form','Security Incident','${i.name}')">
                            <div style="flex:1">
                                <div class="ait">${i.incident_type} — ${i.facility||''}</div>
                                <div class="ais">${i.incident_date} · Severity: ${i.severity} · ${i.status}</div>
                            </div>
                            ${this.statusBadge(i.status)}
                        </div>`).join('') || '<div style="color:var(--ad-tx3);font-size:12px">No open security incidents ✅</div>'}
                    </div>
                </div>
            </div>
        `);

        // Chart: request activity
        this.makeChart('ad-ch-activity', {
            type: 'bar',
            data: {
                labels: last7.map(d => new Date(d).toLocaleDateString('en-NG', {weekday:'short',day:'numeric'})),
                datasets: [{ label:'Requests', data: reqByDay, backgroundColor: '#0284C7', borderRadius: 6 }]
            },
            options: { responsive:true, maintainAspectRatio:false, plugins:{ legend:{display:false} },
                scales:{ x:{ grid:{color:'rgba(255,255,255,.04)'}, ticks:{color:'#94A3B8',font:{size:10}} },
                         y:{ grid:{color:'rgba(255,255,255,.04)'}, ticks:{color:'#94A3B8',font:{size:10}} } } }
        });

        // Chart: spend donut
        if (spendData.length) {
            this.makeChart('ad-ch-spend', {
                type: 'doughnut',
                data: { labels: spendData.map(x=>x.label), datasets: [{ data: spendData.map(x=>x.v), backgroundColor: this.chartColors(), borderWidth:0 }] },
                options: { responsive:true, maintainAspectRatio:false, cutout:'70%', plugins:{ legend:{display:false} } }
            });
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  TAB: REQUESTS
    // ═══════════════════════════════════════════════════════════════════════════
    renderRequests() {
        const open      = this.requests.filter(r => !['Completed','Closed','Rejected','Cancelled'].includes(r.status));
        const breached  = this.requests.filter(r => r.sla_breached == 1);
        const completed = this.requests.filter(r => r.status === 'Completed');
        const urgentCount= this.requests.filter(r => r.priority === 'Urgent').length;

        // By type
        const byType = {};
        this.requests.forEach(r => { byType[r.request_type] = (byType[r.request_type]||0) + 1; });
        const typeKeys = Object.keys(byType).sort((a,b)=>byType[b]-byType[a]).slice(0,8);

        // By status
        const statusCounts = ['Draft','Submitted','Approved','In Progress','Completed','Rejected'];
        const byStatus = statusCounts.map(s => this.requests.filter(r=>r.status===s).length);

        // Cost summary
        const totalEstimated = this.requests.reduce((s,r)=>s+this.flt(r.estimated_cost),0);
        const totalActual    = this.requests.reduce((s,r)=>s+this.flt(r.actual_cost),0);

        $('#ad-panel-requests').html(`
            <div class="ad-kpis">
                ${this.kpi('📋','kc-pri','Total requests',   this.requests.length, 'all time', '/app/administrative-request')}
                ${this.kpi('🔓','kc-amb','Open requests',    open.length,          `${this.requests.filter(r=>r.status==='Submitted').length} awaiting approval`)}
                ${this.kpi('⏱','kc-red','SLA breaches',     breached.length,       'require immediate action')}
                ${this.kpi('🚨','kc-red','Urgent',           urgentCount,           'priority urgent')}
                ${this.kpi('✅','kc-grn','Completed',        completed.length,      'fully resolved')}
                ${this.kpi('💰','kc-sky','Est. cost',        this.fmt(totalEstimated), 'vs ' + this.fmt(totalActual) + ' actual')}
            </div>

            <div class="ad-g21">
                <div class="ad-card">
                    <div class="ad-ch">
                        <div class="ad-ct">📋 All administrative requests</div>
                        <div class="ad-acts">
                            <select class="ad-sel" id="ad-req-status-filter" style="width:130px;font-size:11px;padding:5px 8px" onchange="window.__adminDash.filterRequests()">
                                <option value="">All statuses</option>
                                ${statusCounts.map(s=>`<option value="${s}">${s}</option>`).join('')}
                            </select>
                            <select class="ad-sel" id="ad-req-type-filter" style="width:150px;font-size:11px;padding:5px 8px" onchange="window.__adminDash.filterRequests()">
                                <option value="">All types</option>
                                ${typeKeys.map(t=>`<option value="${t}">${t}</option>`).join('')}
                            </select>
                            <button class="ad-btn ab-solid" onclick="frappe.new_doc('Administrative Request')">+ New</button>
                        </div>
                    </div>
                    <div class="ad-tbl-wrap">
                        <table class="ad-tbl" id="ad-req-table">
                            <thead><tr><th>Title</th><th>Type</th><th>Employee</th><th>Department</th><th>Priority</th><th>Status</th><th>Age</th><th>Est. Cost</th><th>SLA</th></tr></thead>
                            <tbody id="ad-req-tbody">
                                ${this.requestRows(this.requests)}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div style="display:flex;flex-direction:column;gap:14px">
                    <div class="ad-card">
                        <div class="ad-ch"><div class="ad-ct">📊 By request type</div></div>
                        <div class="ad-cb">
                            <div style="height:220px;position:relative"><canvas id="ad-ch-req-type" aria-label="Request types bar chart">Requests by type.</canvas></div>
                        </div>
                    </div>
                    <div class="ad-card">
                        <div class="ad-ch"><div class="ad-ct">🔄 Status pipeline</div></div>
                        <div class="ad-cb">
                            ${statusCounts.map((s,i) => {
                                const cnt = byStatus[i];
                                const pct = this.requests.length ? Math.round(cnt/this.requests.length*100) : 0;
                                const cols = ['#94A3B8','#0284C7','#38BDF8','#F59E0B','#10B981','#EF4444'];
                                return `<div class="ad-bar-row">
                                    <div class="ad-bar-lbl">${s}</div>
                                    <div class="ad-bar"><div class="ad-bar-fill" style="width:${pct}%;background:${cols[i]}"></div></div>
                                    <div class="ad-bar-val">${cnt}</div>
                                </div>`;
                            }).join('')}
                        </div>
                    </div>
                </div>
            </div>
        `);

        this.makeChart('ad-ch-req-type', {
            type: 'bar',
            data: { labels: typeKeys, datasets: [{ label:'Requests', data: typeKeys.map(k=>byType[k]), backgroundColor:'#0284C7', borderRadius:4 }] },
            options: { indexAxis:'y', responsive:true, maintainAspectRatio:false,
                plugins:{ legend:{display:false} },
                scales:{ x:{ grid:{color:'rgba(255,255,255,.04)'}, ticks:{color:'#94A3B8',font:{size:10}} },
                         y:{ grid:{display:false}, ticks:{color:'#94A3B8',font:{size:10}} } } }
        });
    }

    requestRows(reqs) {
        return reqs.map(r => `
            <tr onclick="frappe.set_route('Form','Administrative Request','${r.name}')">
                <td style="font-weight:600;color:var(--ad-tx1);max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${r.request_title||r.name}</td>
                <td>${r.request_type||''}</td>
                <td style="color:var(--ad-tx3)">${r.employee||''}</td>
                <td style="color:var(--ad-tx3)">${r.department||''}</td>
                <td>${this.severityBadge(r.priority)}</td>
                <td>${this.statusBadge(r.status)}</td>
                <td style="font-family:'JetBrains Mono',monospace;font-size:10px">${r.request_age_days||0}d</td>
                <td>${r.estimated_cost ? this.fmt(r.estimated_cost) : '—'}</td>
                <td>${r.sla_breached==1 ? '<span class="ad-badge bg-red">Breached</span>' : '<span class="ad-badge bg-grn">OK</span>'}</td>
            </tr>`).join('') || '<tr><td colspan="9" style="text-align:center;color:var(--ad-tx3);padding:24px">No requests found</td></tr>';
    }

    filterRequests() {
        const statusF = document.getElementById('ad-req-status-filter')?.value || '';
        const typeF   = document.getElementById('ad-req-type-filter')?.value || '';
        let filtered  = this.requests;
        if (statusF) filtered = filtered.filter(r => r.status === statusF);
        if (typeF)   filtered = filtered.filter(r => r.request_type === typeF);
        document.getElementById('ad-req-tbody').innerHTML = this.requestRows(filtered);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  TAB: FLEET
    // ═══════════════════════════════════════════════════════════════════════════
    renderFleet() {
        const available   = this.vehicles.filter(v => v.status === 'Available');
        const inUse       = this.vehicles.filter(v => v.status === 'In Use');
        const maintenance = this.vehicles.filter(v => v.status === 'Under Maintenance');
        const grounded    = this.vehicles.filter(v => v.status === 'Grounded');

        const totalFuelYTD  = this.vehicles.reduce((s,v)=>s+this.flt(v.fuel_cost_ytd),0);
        const totalMaintYTD = this.vehicles.reduce((s,v)=>s+this.flt(v.maintenance_cost_ytd),0);
        const totalKmYTD    = this.vehicles.reduce((s,v)=>s+this.flt(v.total_km_ytd),0);
        const totalTripsYTD = this.vehicles.reduce((s,v)=>s+this.n(v.trips_ytd),0);

        // Recent trips
        const recentTrips = this.tripLogs.slice(0,10);

        // Fuel issues this month
        const today = frappe.datetime.get_today();
        const monthFuel = this.fuelIssues.filter(f => f.issue_date && f.issue_date.substring(0,7) === today.substring(0,7));
        const monthFuelCost = monthFuel.reduce((s,f)=>s+this.flt(f.total_cost),0);

        // Expiring vehicle docs
        const expiringVehicleDocs = this.vehicles.filter(v => {
            const dates = [v.insurance_expiry, v.license_expiry, v.road_worthiness_expiry].filter(Boolean);
            return dates.some(d => this.daysLeft(d) !== null && this.daysLeft(d) <= 30 && this.daysLeft(d) >= 0);
        });

        // Fuel by vehicle for chart (top 8)
        const topByFuel = [...this.vehicles].sort((a,b)=>this.flt(b.fuel_cost_ytd)-this.flt(a.fuel_cost_ytd)).slice(0,8);

        $('#ad-panel-fleet').html(`
            <div class="ad-kpis">
                ${this.kpi('🟢','kc-grn','Available',    available.length,   `of ${this.vehicles.length} vehicles`)}
                ${this.kpi('🔵','kc-pri','In use',       inUse.length,       'currently deployed')}
                ${this.kpi('🟠','kc-amb','Maintenance',  maintenance.length, 'under repair')}
                ${this.kpi('🔴','kc-red','Grounded',     grounded.length,    'insurance/licence issues')}
                ${this.kpi('⛽','kc-sky','Fuel cost YTD', this.fmt(totalFuelYTD), `${this.fmt(monthFuelCost)} this month`)}
                ${this.kpi('🔧','kc-pur','Maint. YTD',   this.fmt(totalMaintYTD), 'all vehicles')}
                ${this.kpi('🛣','kc-grn','Total KM YTD', Math.round(totalKmYTD).toLocaleString()+'km', 'all vehicles')}
                ${this.kpi('🚦','kc-sky','Trips YTD',    totalTripsYTD,      'total journeys')}
            </div>

            <div class="ad-g21">
                <div class="ad-card">
                    <div class="ad-ch">
                        <div class="ad-ct">🚗 Vehicle fleet</div>
                        <div class="ad-acts">
                            <select class="ad-sel" id="ad-veh-filter" style="width:130px;font-size:11px;padding:5px 8px" onchange="window.__adminDash.filterVehicles()">
                                <option value="">All statuses</option>
                                <option value="Available">Available</option>
                                <option value="In Use">In Use</option>
                                <option value="Under Maintenance">Maintenance</option>
                                <option value="Grounded">Grounded</option>
                            </select>
                            <button class="ad-btn ab-solid" onclick="frappe.new_doc('Company Vehicle')">+ Add Vehicle</button>
                        </div>
                    </div>
                    <div class="ad-tbl-wrap">
                        <table class="ad-tbl">
                            <thead><tr><th>Vehicle</th><th>Plate</th><th>Type</th><th>Driver</th><th>Status</th><th>Odometer</th><th>Fuel YTD</th><th>Cost/KM</th><th>Insurance</th></tr></thead>
                            <tbody id="ad-veh-tbody">
                                ${this.vehicleRows(this.vehicles)}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div style="display:flex;flex-direction:column;gap:14px">
                    <div class="ad-card">
                        <div class="ad-ch"><div class="ad-ct">⚠️ Document expiry alerts</div></div>
                        <div class="ad-cb">
                            ${expiringVehicleDocs.length ? expiringVehicleDocs.slice(0,5).map(v => {
                                const d = Math.min(
                                    ...([v.insurance_expiry,v.license_expiry,v.road_worthiness_expiry].filter(Boolean).map(x=>this.daysLeft(x)||999))
                                );
                                return `<div class="ad-alert-box ${d<=7?'aab-r':'aab-a'}" onclick="frappe.set_route('Form','Company Vehicle','${v.name}')">
                                    <div style="flex:1">
                                        <div class="ait">${v.vehicle_name||v.plate_number}</div>
                                        <div class="ais">Document expires in ${d} days</div>
                                    </div>
                                    ${this.badge(d+'d', d<=7?'bg-red':'bg-amb')}
                                </div>`;
                            }).join('') : '<div style="color:var(--ad-tx3);font-size:12px">All vehicle documents are current ✅</div>'}
                        </div>
                    </div>
                    <div class="ad-card">
                        <div class="ad-ch"><div class="ad-ct">⛽ Fuel cost YTD — top vehicles</div></div>
                        <div class="ad-cb">
                            <div style="height:180px;position:relative"><canvas id="ad-ch-fuel" aria-label="Fuel cost by vehicle bar chart">Fuel expenditure by vehicle.</canvas></div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="ad-g2">
                <div class="ad-card">
                    <div class="ad-ch"><div class="ad-ct">🗓 Recent trip logs</div><button class="ad-btn ab-solid" onclick="frappe.new_doc('Vehicle Trip Log')">+ Log Trip</button></div>
                    <div class="ad-tbl-wrap">
                        <table class="ad-tbl">
                            <thead><tr><th>Date</th><th>Vehicle</th><th>Driver</th><th>Purpose</th><th>Distance</th><th>Fuel Cost</th></tr></thead>
                            <tbody>
                                ${recentTrips.map(t => `<tr onclick="frappe.set_route('Form','Vehicle Trip Log','${t.name}')">
                                    <td style="font-family:'JetBrains Mono',monospace;font-size:10px">${t.trip_date||''}</td>
                                    <td style="font-weight:600">${t.vehicle||''}</td>
                                    <td style="color:var(--ad-tx3)">${t.driver||''}</td>
                                    <td>${t.purpose||''}</td>
                                    <td>${t.distance_km ? this.flt(t.distance_km).toFixed(0)+'km' : '—'}</td>
                                    <td>${t.total_fuel_cost ? this.fmt(t.total_fuel_cost) : '—'}</td>
                                </tr>`).join('') || '<tr><td colspan="6" style="text-align:center;color:var(--ad-tx3);padding:20px">No trip logs found</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
                <div class="ad-card">
                    <div class="ad-ch"><div class="ad-ct">⛽ Fuel issues — recent</div><button class="ad-btn ab-solid" onclick="frappe.new_doc('Fuel Issue')">+ Fuel Issue</button></div>
                    <div class="ad-tbl-wrap">
                        <table class="ad-tbl">
                            <thead><tr><th>Date</th><th>Vehicle</th><th>Litres</th><th>Method</th><th>Cost</th></tr></thead>
                            <tbody>
                                ${this.fuelIssues.slice(0,10).map(f => `<tr onclick="frappe.set_route('Form','Fuel Issue','${f.name}')">
                                    <td style="font-family:'JetBrains Mono',monospace;font-size:10px">${f.issue_date||''}</td>
                                    <td style="font-weight:600">${f.vehicle||''}</td>
                                    <td>${this.flt(f.litres_issued).toFixed(1)}L</td>
                                    <td style="color:var(--ad-tx3)">${f.issue_method||''}</td>
                                    <td>${this.fmt(f.total_cost)}</td>
                                </tr>`).join('') || '<tr><td colspan="5" style="text-align:center;color:var(--ad-tx3);padding:20px">No fuel issues found</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `);

        this.makeChart('ad-ch-fuel', {
            type: 'bar',
            data: { labels: topByFuel.map(v=>v.vehicle_name||v.plate_number),
                    datasets: [{ label:'Fuel Cost YTD', data: topByFuel.map(v=>this.flt(v.fuel_cost_ytd)), backgroundColor:'#F59E0B', borderRadius:4 }] },
            options: { responsive:true, maintainAspectRatio:false,
                plugins:{ legend:{display:false} },
                scales:{ x:{ grid:{display:false}, ticks:{color:'#94A3B8',font:{size:9}} },
                         y:{ grid:{color:'rgba(255,255,255,.04)'}, ticks:{color:'#94A3B8',font:{size:10}, callback:v=>'₦'+this.fmt(v).replace('₦','')} } } }
        });
    }

    vehicleRows(vehs) {
        return vehs.map(v => `<tr onclick="frappe.set_route('Form','Company Vehicle','${v.name}')">
            <td style="font-weight:600;color:var(--ad-tx1)">${v.vehicle_name||''}</td>
            <td style="font-family:'JetBrains Mono',monospace;font-size:10px">${v.plate_number}</td>
            <td style="color:var(--ad-tx3)">${v.vehicle_type||''}</td>
            <td style="color:var(--ad-tx3)">${v.assigned_driver||'—'}</td>
            <td>${this.statusBadge(v.status)}</td>
            <td style="font-family:'JetBrains Mono',monospace;font-size:10px">${v.odometer_reading ? this.flt(v.odometer_reading).toFixed(0)+'km' : '—'}</td>
            <td>${this.fmt(v.fuel_cost_ytd||0)}</td>
            <td style="font-family:'JetBrains Mono',monospace;font-size:10px">${v.cost_per_km ? this.fmt(v.cost_per_km)+'/km' : '—'}</td>
            <td>${this.daysLeftBadge(v.insurance_expiry)}</td>
        </tr>`).join('') || '<tr><td colspan="9" style="text-align:center;color:var(--ad-tx3);padding:24px">No vehicles found</td></tr>';
    }

    filterVehicles() {
        const f = document.getElementById('ad-veh-filter')?.value || '';
        const filtered = f ? this.vehicles.filter(v => v.status === f) : this.vehicles;
        document.getElementById('ad-veh-tbody').innerHTML = this.vehicleRows(filtered);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  TAB: FACILITIES
    // ═══════════════════════════════════════════════════════════════════════════
    renderFacilities() {
        const active    = this.facilities.filter(f=>f.status==='Active');
        const openMaint = this.maintenanceRequests.filter(m=>!['Completed','Closed','Cancelled'].includes(m.status));
        const openWO    = this.workOrders.filter(w=>!['Completed','Cancelled'].includes(w.status));
        const totalMaintCost = this.workOrders.reduce((s,w)=>s+this.flt(w.actual_cost),0);

        // By category for maint requests
        const byCat = {};
        this.maintenanceRequests.forEach(m => { byCat[m.maintenance_category]=(byCat[m.maintenance_category]||0)+1; });
        const catKeys = Object.keys(byCat).sort((a,b)=>byCat[b]-byCat[a]).slice(0,8);

        $('#ad-panel-facilities').html(`
            <div class="ad-kpis">
                ${this.kpi('🏗','kc-pri','Total facilities', this.facilities.length, `${active.length} active`)}
                ${this.kpi('🔧','kc-red','Open maintenance', openMaint.length, 'across all facilities')}
                ${this.kpi('📋','kc-amb','Work orders',     openWO.length,    'in progress')}
                ${this.kpi('💰','kc-sky','Maintenance cost', this.fmt(totalMaintCost), 'actual spend')}
                ${this.kpi('📅','kc-grn','Bookings today',  this.meetingBookings.filter(b=>b.booking_date===frappe.datetime.get_today()).length, 'room bookings')}
                ${this.kpi('⚠️','kc-pur','Emergencies', openMaint.filter(m=>m.priority==='Emergency').length, 'emergency requests')}
            </div>

            <div class="ad-g2">
                <div class="ad-card">
                    <div class="ad-ch"><div class="ad-ct">🏗 Facility overview</div><button class="ad-btn ab-solid" onclick="frappe.new_doc('Facility')">+ Add Facility</button></div>
                    <div class="ad-tbl-wrap">
                        <table class="ad-tbl">
                            <thead><tr><th>Facility</th><th>Type</th><th>Branch</th><th>Status</th><th>Open Reqs</th><th>Maint. Cost</th><th>Util. Cost</th></tr></thead>
                            <tbody>
                                ${this.facilities.map(f => `<tr onclick="frappe.set_route('Form','Facility','${f.name}')">
                                    <td style="font-weight:600;color:var(--ad-tx1)">${f.facility_name}</td>
                                    <td style="color:var(--ad-tx3)">${f.facility_type||''}</td>
                                    <td style="color:var(--ad-tx3)">${f.branch||'—'}</td>
                                    <td>${this.statusBadge(f.status)}</td>
                                    <td>${f.open_maintenance_requests||0 ? this.badge(f.open_maintenance_requests, f.open_maintenance_requests > 3 ? 'bg-red':'bg-amb') : this.badge('0','bg-grn')}</td>
                                    <td>${f.maintenance_cost_ytd ? this.fmt(f.maintenance_cost_ytd) : '—'}</td>
                                    <td>${f.utility_cost_ytd ? this.fmt(f.utility_cost_ytd) : '—'}</td>
                                </tr>`).join('') || '<tr><td colspan="7" style="text-align:center;color:var(--ad-tx3);padding:20px">No facilities found</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
                <div class="ad-card">
                    <div class="ad-ch"><div class="ad-ct">📊 Maintenance by category</div></div>
                    <div class="ad-cb">
                        <div style="height:240px;position:relative"><canvas id="ad-ch-maint-cat" aria-label="Maintenance requests by category">Maintenance request categories.</canvas></div>
                    </div>
                </div>
            </div>

            <div class="ad-g21">
                <div class="ad-card">
                    <div class="ad-ch"><div class="ad-ct">🔧 Maintenance requests</div><button class="ad-btn ab-solid" onclick="frappe.new_doc('Facility Maintenance Request')">+ New Request</button></div>
                    <div class="ad-tbl-wrap">
                        <table class="ad-tbl">
                            <thead><tr><th>Subject</th><th>Facility</th><th>Category</th><th>Priority</th><th>Status</th><th>Date</th><th>Est. Cost</th></tr></thead>
                            <tbody>
                                ${openMaint.map(m => `<tr onclick="frappe.set_route('Form','Facility Maintenance Request','${m.name}')">
                                    <td style="font-weight:600;color:var(--ad-tx1)">${m.subject||m.name}</td>
                                    <td style="color:var(--ad-tx3)">${m.facility||''}</td>
                                    <td>${m.maintenance_category||''}</td>
                                    <td>${this.severityBadge(m.priority)}</td>
                                    <td>${this.statusBadge(m.status)}</td>
                                    <td style="font-family:'JetBrains Mono',monospace;font-size:10px">${m.report_date||''}</td>
                                    <td>${m.estimated_cost ? this.fmt(m.estimated_cost) : '—'}</td>
                                </tr>`).join('') || '<tr><td colspan="7" style="text-align:center;color:var(--ad-tx3);padding:20px">No open maintenance requests 🎉</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
                <div style="display:flex;flex-direction:column;gap:14px">
                    <div class="ad-card">
                        <div class="ad-ch"><div class="ad-ct">🗓 Meeting room bookings today</div><button class="ad-btn ab-solid" onclick="frappe.new_doc('Meeting Room Booking')">+ Book</button></div>
                        <div class="ad-cb">
                            ${this.meetingBookings.filter(b=>b.booking_date===frappe.datetime.get_today()).slice(0,6).map(b => `
                            <div class="ad-li" onclick="frappe.set_route('Form','Meeting Room Booking','${b.name}')">
                                <div class="ad-li-l">
                                    <div class="ad-li-title">${b.meeting_title||b.name}</div>
                                    <div class="ad-li-sub">${b.facility||''} · ${b.start_time||''} – ${b.end_time||''} · ${b.attendees_count||0} pax</div>
                                </div>
                                ${this.statusBadge(b.status)}
                            </div>`).join('') || '<div style="color:var(--ad-tx3);font-size:12px;padding:8px 0">No bookings today</div>'}
                        </div>
                    </div>
                    <div class="ad-card">
                        <div class="ad-ch"><div class="ad-ct">🔨 Work orders</div></div>
                        <div class="ad-cb">
                            ${openWO.slice(0,5).map(w => `
                            <div class="ad-li" onclick="frappe.set_route('Form','Maintenance Work Order','${w.name}')">
                                <div class="ad-li-l">
                                    <div class="ad-li-title">${w.title||w.name}</div>
                                    <div class="ad-li-sub">${w.facility||''} · ${w.work_type||''}</div>
                                </div>
                                ${this.statusBadge(w.status)}
                            </div>`).join('') || '<div style="color:var(--ad-tx3);font-size:12px;padding:8px 0">No open work orders</div>'}
                        </div>
                    </div>
                </div>
            </div>
        `);

        this.makeChart('ad-ch-maint-cat', {
            type: 'doughnut',
            data: { labels: catKeys, datasets: [{ data: catKeys.map(k=>byCat[k]), backgroundColor: this.chartColors(), borderWidth:0 }] },
            options: { responsive:true, maintainAspectRatio:false, cutout:'65%',
                plugins:{ legend:{ display:true, position:'right', labels:{ color:'#94A3B8', font:{size:10}, boxWidth:10, padding:8 } } } }
        });
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  TAB: UTILITIES
    // ═══════════════════════════════════════════════════════════════════════════
    renderUtilities() {
        const today = frappe.datetime.get_today();
        const currentMonth = today.substring(0,7);

        const thisMon  = this.utilConsumed.filter(u => u.reading_date && u.reading_date.substring(0,7) === currentMonth);
        const totalBill= thisMon.reduce((s,u)=>s+this.flt(u.total_bill),0);

        // By utility type
        const byType = {};
        thisMon.forEach(u => { byType[u.utility_type] = (byType[u.utility_type]||0) + this.flt(u.total_bill); });

        // Last 6 months trend
        const months = Array.from({length:6},(_,i)=>{
            const d = new Date(); d.setMonth(d.getMonth()-5+i);
            return d.toISOString().substring(0,7);
        });
        const monthLabels = months.map(m => { const d=new Date(m+'-01'); return d.toLocaleDateString('en-NG',{month:'short',year:'2-digit'}); });
        const monthTotals = months.map(m => this.utilConsumed.filter(u=>u.reading_date&&u.reading_date.substring(0,7)===m).reduce((s,u)=>s+this.flt(u.total_bill),0));

        // Generator analysis
        const genThisMon = this.genLogs.filter(g=>g.log_date&&g.log_date.substring(0,7)===currentMonth);
        const totalGenHrs = genThisMon.reduce((s,g)=>s+this.flt(g.run_hours),0);
        const totalGenLtrs= genThisMon.reduce((s,g)=>s+this.flt(g.fuel_consumed_litres),0);
        const totalGenCost= genThisMon.reduce((s,g)=>s+this.flt(g.fuel_cost),0);
        const genByReason = {};
        genThisMon.forEach(g=>{ genByReason[g.reason_for_running]=(genByReason[g.reason_for_running]||0)+this.flt(g.run_hours); });

        // All meters
        const activeMeters = this.utilMeters.filter(m=>m.status==='Active');

        const utilIcons = { 'Electricity':'⚡','Water':'💧','Diesel':'🛢','Gas':'🔥','Internet Bandwidth':'📶' };

        $('#ad-panel-utilities').html(`
            <div class="ad-kpis">
                ${this.kpi('💡','kc-pri','Active meters',    activeMeters.length,         'utility meters')}
                ${this.kpi('💰','kc-amb','Total bill MTD',  this.fmt(totalBill),          'all utilities')}
                ${this.kpi('⏱','kc-red','Gen. hours MTD',  totalGenHrs.toFixed(1)+'h',   'generator runtime')}
                ${this.kpi('🛢','kc-sky','Diesel MTD',      totalGenLtrs.toFixed(0)+'L',  this.fmt(totalGenCost)+' cost')}
                ${this.kpi('📈','kc-pur','Variance avg',    (() => { const variances=thisMon.map(u=>this.flt(u.variance_pct)).filter(v=>v!==0); return variances.length ? (variances.reduce((a,b)=>a+b,0)/variances.length).toFixed(0)+'%' : 'N/A'; })(), 'vs prior month')}
                ${this.kpi('🔌','kc-grn','Readings logged', thisMon.length,               'this month')}
            </div>

            <div class="ad-g21">
                <div class="ad-card">
                    <div class="ad-ch"><div class="ad-ct">📈 Utility spend — last 6 months</div></div>
                    <div class="ad-cb">
                        <div style="height:220px;position:relative"><canvas id="ad-ch-util-trend" aria-label="Utility spend trend over 6 months">Monthly utility cost trend.</canvas></div>
                    </div>
                </div>
                <div class="ad-card">
                    <div class="ad-ch"><div class="ad-ct">📊 MTD breakdown by type</div></div>
                    <div class="ad-cb">
                        ${Object.entries(byType).map(([type,cost]) => {
                            const total = Object.values(byType).reduce((a,b)=>a+b,0)||1;
                            const pct = Math.round(cost/total*100);
                            const col = {Electricity:'#F59E0B',Water:'#0EA5E9',Diesel:'#EF4444',Gas:'#F97316','Internet Bandwidth':'#8B5CF6'}[type]||'#94A3B8';
                            return `<div class="ad-util-row">
                                <div class="ad-util-icon" style="background:${col}20">${utilIcons[type]||'⚡'}</div>
                                <div class="ad-util-lbl">${type}</div>
                                <div style="text-align:right">
                                    <div class="ad-util-val">${this.fmt(cost)}</div>
                                    <div style="font-size:10px;color:var(--ad-tx3)">${pct}%</div>
                                </div>
                            </div>`;
                        }).join('') || '<div style="color:var(--ad-tx3);font-size:12px">No utility consumption data this month</div>'}
                        <hr class="ad-hr">
                        <div style="display:flex;justify-content:space-between;font-size:12px;font-weight:700">
                            <span style="color:var(--ad-tx2)">Total MTD</span>
                            <span style="color:var(--ad-red)">${this.fmt(totalBill + totalGenCost)}</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="ad-g2">
                <div class="ad-card">
                    <div class="ad-ch"><div class="ad-ct">🛢 Generator log analysis</div><button class="ad-btn ab-solid" onclick="frappe.new_doc('Generator Log')">+ Log</button></div>
                    <div class="ad-cb">
                        <div class="ad-stat-grid" style="margin-bottom:14px">
                            <div class="ad-stat"><div class="ad-stat-val">${totalGenHrs.toFixed(1)}h</div><div class="ad-stat-lbl">Runtime MTD</div></div>
                            <div class="ad-stat"><div class="ad-stat-val">${totalGenLtrs.toFixed(0)}L</div><div class="ad-stat-lbl">Diesel MTD</div></div>
                            <div class="ad-stat"><div class="ad-stat-val" style="color:var(--ad-red)">${this.fmt(totalGenCost)}</div><div class="ad-stat-lbl">Cost MTD</div></div>
                            <div class="ad-stat"><div class="ad-stat-val">${totalGenHrs > 0 ? (totalGenLtrs/totalGenHrs).toFixed(1) : '—'}</div><div class="ad-stat-lbl">L/Hour</div></div>
                        </div>
                        <div style="font-size:11px;font-weight:700;color:var(--ad-tx3);margin-bottom:8px;text-transform:uppercase;letter-spacing:.5px">Runtime by reason</div>
                        ${Object.entries(genByReason).sort((a,b)=>b[1]-a[1]).map(([r,h]) => `
                        <div class="ad-bar-row">
                            <div class="ad-bar-lbl">${r||'Unknown'}</div>
                            <div class="ad-bar"><div class="ad-bar-fill" style="width:${Math.round(h/Math.max(totalGenHrs,1)*100)}%;background:#F59E0B"></div></div>
                            <div class="ad-bar-val">${h.toFixed(1)}h</div>
                        </div>`).join('') || '<div style="color:var(--ad-tx3);font-size:12px">No generator log data this month</div>'}
                    </div>
                </div>

                <div class="ad-card">
                    <div class="ad-ch"><div class="ad-ct">📋 Consumption readings — recent</div><button class="ad-btn ab-solid" onclick="frappe.new_doc('Utility Consumption')">+ Reading</button></div>
                    <div class="ad-tbl-wrap">
                        <table class="ad-tbl">
                            <thead><tr><th>Meter</th><th>Facility</th><th>Month</th><th>Consumption</th><th>Total Bill</th><th>Variance</th></tr></thead>
                            <tbody>
                                ${this.utilConsumed.slice(0,12).map(u => {
                                    const vp = this.flt(u.variance_pct);
                                    return `<tr onclick="frappe.set_route('Form','Utility Consumption','${u.name}')">
                                        <td style="font-weight:600">${u.utility_meter||u.utility_type||''}</td>
                                        <td style="color:var(--ad-tx3)">${u.facility||''}</td>
                                        <td style="color:var(--ad-tx3)">${u.period_month||''} ${u.period_year||''}</td>
                                        <td>${u.consumption ? this.flt(u.consumption).toFixed(0) + ' units' : '—'}</td>
                                        <td>${this.fmt(u.total_bill||0)}</td>
                                        <td>${vp ? this.badge((vp>0?'+':'')+vp.toFixed(0)+'%', vp>20?'bg-red':vp>5?'bg-amb':'bg-grn') : '—'}</td>
                                    </tr>`;
                                }).join('') || '<tr><td colspan="6" style="text-align:center;color:var(--ad-tx3);padding:20px">No readings found</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `);

        this.makeChart('ad-ch-util-trend', {
            type: 'line',
            data: { labels: monthLabels, datasets: [{
                label:'Total bill', data: monthTotals,
                borderColor:'#0284C7', backgroundColor:'rgba(2,132,199,.1)',
                fill:true, tension:.4, pointBackgroundColor:'#0284C7', pointRadius:4
            }] },
            options: { responsive:true, maintainAspectRatio:false,
                plugins:{ legend:{display:false} },
                scales:{ x:{ grid:{color:'rgba(255,255,255,.04)'}, ticks:{color:'#94A3B8',font:{size:10}} },
                         y:{ grid:{color:'rgba(255,255,255,.04)'}, ticks:{color:'#94A3B8',font:{size:10},callback:v=>'₦'+this.fmt(v).replace('₦','')} } } }
        });
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  TAB: SECURITY
    // ═══════════════════════════════════════════════════════════════════════════
    renderSecurity() {
        const today     = frappe.datetime.get_today();
        const openInc   = this.incidents.filter(i=>!['Resolved','Closed'].includes(i.status));
        const visitToday= this.visitors.filter(v=>v.visit_date===today);
        const visThisMon= this.visitors.filter(v=>v.visit_date&&v.visit_date.substring(0,7)===today.substring(0,7));

        // By type
        const byType = {};
        this.incidents.forEach(i=>{byType[i.incident_type]=(byType[i.incident_type]||0)+1;});

        // By severity
        const bySev = ['Minor','Moderate','Severe','Critical'].map(s=>({s,n:this.incidents.filter(i=>i.severity===s).length}));

        // Visitor trend last 7 days
        const last7 = Array.from({length:7},(_,i)=>{
            const d=new Date(); d.setDate(d.getDate()-(6-i)); return d.toISOString().substring(0,10);
        });
        const visPerDay = last7.map(d=>this.visitors.filter(v=>v.visit_date===d).length);

        const totalLoss = this.incidents.reduce((s,i)=>s+this.flt(i.estimated_loss),0);

        $('#ad-panel-security').html(`
            <div class="ad-kpis">
                ${this.kpi('🛡','kc-red','Open incidents',  openInc.length,      'require action')}
                ${this.kpi('⚠️','kc-pur','Severe+',        this.incidents.filter(i=>['Severe','Critical'].includes(i.severity)).length, 'severe or critical')}
                ${this.kpi('💰','kc-red','Estimated loss',  this.fmt(totalLoss), 'from all incidents')}
                ${this.kpi('👤','kc-pri','Visitors today',  visitToday.length,   `${visitToday.filter(v=>v.status==='Checked In').length} in building`)}
                ${this.kpi('📅','kc-sky','Visitors MTD',    visThisMon.length,   'this month')}
                ${this.kpi('✅','kc-grn','Resolved',        this.incidents.filter(i=>i.status==='Resolved').length, 'incidents resolved')}
            </div>

            <div class="ad-g21">
                <div class="ad-card">
                    <div class="ad-ch">
                        <div class="ad-ct">🛡 Security incidents</div>
                        <div class="ad-acts">
                            <button class="ad-btn ab-solid" onclick="frappe.new_doc('Security Incident')">+ Report Incident</button>
                        </div>
                    </div>
                    <div class="ad-tbl-wrap">
                        <table class="ad-tbl">
                            <thead><tr><th>Incident</th><th>Type</th><th>Facility</th><th>Date</th><th>Severity</th><th>Status</th><th>Est. Loss</th></tr></thead>
                            <tbody>
                                ${this.incidents.map(i=>`<tr onclick="frappe.set_route('Form','Security Incident','${i.name}')">
                                    <td style="font-weight:600;color:var(--ad-tx1);max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${i.incident_title||i.name}</td>
                                    <td>${i.incident_type||''}</td>
                                    <td style="color:var(--ad-tx3)">${i.facility||''}</td>
                                    <td style="font-family:'JetBrains Mono',monospace;font-size:10px">${i.incident_date||''}</td>
                                    <td>${this.severityBadge(i.severity)}</td>
                                    <td>${this.statusBadge(i.status)}</td>
                                    <td>${i.estimated_loss ? this.fmt(i.estimated_loss) : '—'}</td>
                                </tr>`).join('') || '<tr><td colspan="7" style="text-align:center;color:var(--ad-tx3);padding:20px">No incidents recorded ✅</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div style="display:flex;flex-direction:column;gap:14px">
                    <div class="ad-card">
                        <div class="ad-ch"><div class="ad-ct">📊 Incidents by type</div></div>
                        <div class="ad-cb">
                            ${Object.entries(byType).sort((a,b)=>b[1]-a[1]).map(([t,n])=>`
                            <div class="ad-bar-row">
                                <div class="ad-bar-lbl">${t}</div>
                                <div class="ad-bar"><div class="ad-bar-fill" style="width:${Math.round(n/Math.max(...Object.values(byType))*100)}%;background:var(--ad-red)"></div></div>
                                <div class="ad-bar-val">${n}</div>
                            </div>`).join('') || '<div style="color:var(--ad-tx3);font-size:12px">No incidents</div>'}
                        </div>
                    </div>
                    <div class="ad-card">
                        <div class="ad-ch"><div class="ad-ct">👤 Visitor trend — 7 days</div></div>
                        <div class="ad-cb">
                            <div style="height:140px;position:relative"><canvas id="ad-ch-visitors" aria-label="Visitor trend bar chart">Daily visitor count over 7 days.</canvas></div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="ad-g2">
                <div class="ad-card">
                    <div class="ad-ch"><div class="ad-ct">👤 Visitor register — today</div><button class="ad-btn ab-solid" onclick="frappe.new_doc('Visitor Register')">+ Check In</button></div>
                    <div class="ad-tbl-wrap">
                        <table class="ad-tbl">
                            <thead><tr><th>Visitor</th><th>Organisation</th><th>Host</th><th>Purpose</th><th>Check In</th><th>Status</th></tr></thead>
                            <tbody>
                                ${visitToday.map(v=>`<tr onclick="frappe.set_route('Form','Visitor Register','${v.name}')">
                                    <td style="font-weight:600;color:var(--ad-tx1)">${v.visitor_name}</td>
                                    <td style="color:var(--ad-tx3)">${v.visitor_company||'—'}</td>
                                    <td style="color:var(--ad-tx3)">${v.host_employee||''}</td>
                                    <td>${v.purpose_of_visit||''}</td>
                                    <td style="font-family:'JetBrains Mono',monospace;font-size:10px">${v.check_in_time||'—'}</td>
                                    <td>${this.statusBadge(v.status)}</td>
                                </tr>`).join('') || '<tr><td colspan="6" style="text-align:center;color:var(--ad-tx3);padding:20px">No visitors today</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
                <div class="ad-card">
                    <div class="ad-ch"><div class="ad-ct">📊 Severity distribution</div></div>
                    <div class="ad-cb">
                        <div style="height:200px;position:relative"><canvas id="ad-ch-sev" aria-label="Incident severity pie chart">Incident severity distribution.</canvas></div>
                        <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:10px;font-size:11px">
                            ${bySev.map((x,i)=>`<span style="display:flex;align-items:center;gap:4px;color:var(--ad-tx2)"><span style="width:10px;height:10px;border-radius:2px;background:${['#94A3B8','#F59E0B','#EF4444','#7C3AED'][i]};display:inline-block"></span>${x.s}: ${x.n}</span>`).join('')}
                        </div>
                    </div>
                </div>
            </div>
        `);

        this.makeChart('ad-ch-visitors', {
            type: 'bar',
            data: { labels: last7.map(d=>new Date(d).toLocaleDateString('en-NG',{weekday:'short'})), datasets:[{label:'Visitors',data:visPerDay,backgroundColor:'#0284C7',borderRadius:4}] },
            options: { responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}},
                scales:{x:{grid:{display:false},ticks:{color:'#94A3B8',font:{size:9}}},y:{grid:{color:'rgba(255,255,255,.04)'},ticks:{color:'#94A3B8',font:{size:9},stepSize:1}}} }
        });

        this.makeChart('ad-ch-sev', {
            type: 'pie',
            data: { labels: bySev.map(x=>x.s), datasets:[{data:bySev.map(x=>x.n),backgroundColor:['#94A3B8','#F59E0B','#EF4444','#7C3AED'],borderWidth:0}] },
            options: { responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}} }
        });
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  TAB: CONTRACTS
    // ═══════════════════════════════════════════════════════════════════════════
    renderContracts() {
        const active    = this.contracts.filter(c=>c.status==='Active');
        const expiring  = this.contracts.filter(c=>c.status==='Expiring Soon'||(()=>{const d=this.daysLeft(c.end_date);return d!==null&&d>=0&&d<=60;})());
        const expired   = this.contracts.filter(c=>c.status==='Expired'||(()=>{const d=this.daysLeft(c.end_date);return d!==null&&d<0;})());
        const totalValue= active.reduce((s,c)=>s+this.flt(c.contract_value),0);
        const annualCost= active.reduce((s,c)=>s+this.flt(c.contract_value)/12,0);

        // By type
        const byType = {};
        this.contracts.forEach(c=>{byType[c.contract_type]=(byType[c.contract_type]||0)+this.flt(c.contract_value);});

        $('#ad-panel-contracts').html(`
            <div class="ad-kpis">
                ${this.kpi('📑','kc-pri','Active contracts',  active.length,       'currently live')}
                ${this.kpi('💰','kc-sky','Total value',       this.fmt(totalValue),'all active contracts')}
                ${this.kpi('📅','kc-grn','Monthly cost',      this.fmt(annualCost),'amortised monthly')}
                ${this.kpi('⚠️','kc-amb','Expiring (60d)',    expiring.length,     'need renewal')}
                ${this.kpi('🔴','kc-red','Expired',           expired.length,      'overdue renewal')}
                ${this.kpi('🏢','kc-pur','Vendors',           this.providers.length,'service providers')}
            </div>

            <div class="ad-g21">
                <div class="ad-card">
                    <div class="ad-ch">
                        <div class="ad-ct">📑 All service contracts</div>
                        <div class="ad-acts">
                            <select class="ad-sel" id="ad-con-filter" style="width:130px;font-size:11px;padding:5px 8px" onchange="window.__adminDash.filterContracts()">
                                <option value="">All statuses</option>
                                <option value="Active">Active</option>
                                <option value="Expiring Soon">Expiring Soon</option>
                                <option value="Expired">Expired</option>
                                <option value="Draft">Draft</option>
                            </select>
                            <button class="ad-btn ab-solid" onclick="frappe.new_doc('Service Contract')">+ New Contract</button>
                        </div>
                    </div>
                    <div class="ad-tbl-wrap">
                        <table class="ad-tbl">
                            <thead><tr><th>Contract</th><th>Type</th><th>Vendor</th><th>Value</th><th>Expires</th><th>Status</th><th>SLA Hrs</th></tr></thead>
                            <tbody id="ad-con-tbody">
                                ${this.contractRows(this.contracts)}
                            </tbody>
                        </table>
                    </div>
                </div>
                <div style="display:flex;flex-direction:column;gap:14px">
                    <div class="ad-card">
                        <div class="ad-ch"><div class="ad-ct">📊 Spend by contract type</div></div>
                        <div class="ad-cb">
                            ${Object.entries(byType).sort((a,b)=>b[1]-a[1]).map(([t,v])=>{
                                const max = Math.max(...Object.values(byType))||1;
                                return `<div class="ad-bar-row">
                                    <div class="ad-bar-lbl" style="font-size:10px;width:120px">${t}</div>
                                    <div class="ad-bar"><div class="ad-bar-fill" style="width:${Math.round(v/max*100)}%;background:var(--ad-pri)"></div></div>
                                    <div class="ad-bar-val" style="width:60px;font-size:10px">${this.fmt(v)}</div>
                                </div>`;
                            }).join('') || '<div style="color:var(--ad-tx3);font-size:12px">No contract data</div>'}
                        </div>
                    </div>
                    <div class="ad-card">
                        <div class="ad-ch"><div class="ad-ct">🏢 Service providers</div><button class="ad-btn ab-solid" onclick="frappe.new_doc('Service Provider')">+ Add</button></div>
                        <div class="ad-cb">
                            ${this.providers.slice(0,6).map(p=>`
                            <div class="ad-li" onclick="frappe.set_route('Form','Service Provider','${p.name}')">
                                <div class="ad-li-l">
                                    <div class="ad-li-title">${p.provider_name}</div>
                                    <div class="ad-li-sub">${p.service_category||''} · Score: ${p.performance_score||0}/10</div>
                                </div>
                                <div style="display:flex;gap:6px;align-items:center">
                                    ${this.statusBadge(p.status)}
                                    ${p.supplier ? this.badge('Supplier','bg-grn') : ''}
                                </div>
                            </div>`).join('') || '<div style="color:var(--ad-tx3);font-size:12px">No service providers</div>'}
                        </div>
                    </div>
                </div>
            </div>
        `);
    }

    contractRows(contracts) {
        return contracts.map(c=>`<tr onclick="frappe.set_route('Form','Service Contract','${c.name}')">
            <td style="font-weight:600;color:var(--ad-tx1);max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${c.contract_title||c.name}</td>
            <td style="color:var(--ad-tx3)">${c.contract_type||''}</td>
            <td style="color:var(--ad-tx3)">${c.vendor||''}</td>
            <td>${this.fmt(c.contract_value||0)}</td>
            <td style="font-family:'JetBrains Mono',monospace;font-size:10px">${c.end_date||'—'}</td>
            <td>${this.daysLeftBadge(c.end_date)}</td>
            <td style="color:var(--ad-tx3)">${c.sla_response_hours ? c.sla_response_hours+'h' : '—'}</td>
        </tr>`).join('') || '<tr><td colspan="7" style="text-align:center;color:var(--ad-tx3);padding:24px">No contracts found</td></tr>';
    }

    filterContracts() {
        const f = document.getElementById('ad-con-filter')?.value || '';
        let filtered = this.contracts;
        if (f === 'Expiring Soon') filtered = filtered.filter(c=>{const d=this.daysLeft(c.end_date);return d!==null&&d>=0&&d<=60;});
        else if (f === 'Expired')  filtered = filtered.filter(c=>{const d=this.daysLeft(c.end_date);return d!==null&&d<0;});
        else if (f) filtered = filtered.filter(c=>c.status===f);
        document.getElementById('ad-con-tbody').innerHTML = this.contractRows(filtered);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  TAB: COMPLIANCE
    // ═══════════════════════════════════════════════════════════════════════════
    renderCompliance() {
        const expired  = this.compliance.filter(c=>c.status==='Expired');
        const expiring = this.compliance.filter(c=>c.status==='Expiring Soon');
        const valid    = this.compliance.filter(c=>c.status==='Valid');
        const totalRenewalCost = this.compliance.filter(c=>c.status!=='Valid').reduce((s,c)=>s+this.flt(c.renewal_cost),0);

        // By type for donut
        const byType = {};
        this.compliance.forEach(c=>{byType[c.compliance_type]=(byType[c.compliance_type]||0)+1;});

        $('#ad-panel-compliance').html(`
            <div class="ad-kpis">
                ${this.kpi('🎖','kc-pri','Total items',      this.compliance.length, 'licences & permits')}
                ${this.kpi('✅','kc-grn','Valid',            valid.length,           'in good standing')}
                ${this.kpi('⚠️','kc-amb','Expiring soon',   expiring.length,        'within reminder period')}
                ${this.kpi('🔴','kc-red','Expired',          expired.length,         'immediate action required')}
                ${this.kpi('💰','kc-sky','Renewal budget',   this.fmt(totalRenewalCost), 'estimated renewals')}
                ${this.kpi('🏢','kc-pur','Facilities covered', [...new Set(this.compliance.map(c=>c.facility).filter(Boolean))].length, 'locations')}
            </div>

            <div class="ad-g21">
                <div class="ad-card">
                    <div class="ad-ch">
                        <div class="ad-ct">🎖 Compliance register</div>
                        <div class="ad-acts">
                            <select class="ad-sel" id="ad-comp-filter" style="width:130px;font-size:11px;padding:5px 8px" onchange="window.__adminDash.filterCompliance()">
                                <option value="">All statuses</option>
                                <option value="Expired">Expired</option>
                                <option value="Expiring Soon">Expiring Soon</option>
                                <option value="Valid">Valid</option>
                            </select>
                            <button class="ad-btn ab-solid" onclick="frappe.new_doc('Compliance Register')">+ Add Item</button>
                        </div>
                    </div>
                    <div class="ad-tbl-wrap">
                        <table class="ad-tbl">
                            <thead><tr><th>Item</th><th>Type</th><th>Issuing Authority</th><th>Facility</th><th>Expiry</th><th>Status</th><th>Renewal Cost</th></tr></thead>
                            <tbody id="ad-comp-tbody">
                                ${this.complianceRows(this.compliance)}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div style="display:flex;flex-direction:column;gap:14px">
                    <div class="ad-card">
                        <div class="ad-ch"><div class="ad-ct">📊 Items by type</div></div>
                        <div class="ad-cb">
                            <div style="height:200px;position:relative"><canvas id="ad-ch-comp-type" aria-label="Compliance items by type donut">Compliance items by type.</canvas></div>
                        </div>
                    </div>
                    <div class="ad-card">
                        <div class="ad-ch"><div class="ad-ct">🚨 Action required NOW</div></div>
                        <div class="ad-cb">
                            ${expired.length ? expired.map(c=>`
                            <div class="ad-alert-box aab-r" onclick="frappe.set_route('Form','Compliance Register','${c.name}')">
                                <div style="flex:1">
                                    <div class="ait">${c.compliance_item}</div>
                                    <div class="ais">${c.compliance_type} · ${c.issuing_authority||''}</div>
                                </div>
                                ${c.renewal_cost ? this.badge(this.fmt(c.renewal_cost),'bg-sky') : ''}
                            </div>`).join('') : '<div style="color:var(--ad-tx3);font-size:12px">No expired items ✅</div>'}
                        </div>
                    </div>
                </div>
            </div>
        `);

        const typeKeys = Object.keys(byType);
        if (typeKeys.length) {
            this.makeChart('ad-ch-comp-type', {
                type: 'doughnut',
                data: { labels: typeKeys, datasets:[{data:typeKeys.map(k=>byType[k]),backgroundColor:this.chartColors(),borderWidth:0}] },
                options: { responsive:true, maintainAspectRatio:false, cutout:'65%', plugins:{legend:{display:true,position:'right',labels:{color:'#94A3B8',font:{size:9},boxWidth:9,padding:6}}} }
            });
        }
    }

    complianceRows(items) {
        return items.map(c=>`<tr onclick="frappe.set_route('Form','Compliance Register','${c.name}')">
            <td style="font-weight:600;color:var(--ad-tx1)">${c.compliance_item}</td>
            <td style="color:var(--ad-tx3)">${c.compliance_type||''}</td>
            <td style="color:var(--ad-tx3)">${c.issuing_authority||'—'}</td>
            <td style="color:var(--ad-tx3)">${c.facility||'—'}</td>
            <td style="font-family:'JetBrains Mono',monospace;font-size:10px">${c.expiry_date||'—'}</td>
            <td>${this.daysLeftBadge(c.expiry_date)}</td>
            <td>${c.renewal_cost ? this.fmt(c.renewal_cost) : '—'}</td>
        </tr>`).join('') || '<tr><td colspan="7" style="text-align:center;color:var(--ad-tx3);padding:24px">No compliance items found</td></tr>';
    }

    filterCompliance() {
        const f = document.getElementById('ad-comp-filter')?.value || '';
        const filtered = f ? this.compliance.filter(c=>c.status===f) : this.compliance;
        document.getElementById('ad-comp-tbody').innerHTML = this.complianceRows(filtered);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  TAB: HSE
    // ═══════════════════════════════════════════════════════════════════════════
    renderHSE() {
        const passCount    = this.hseInspections.filter(h=>h.pass_fail==='Pass').length;
        const failCount    = this.hseInspections.filter(h=>h.pass_fail==='Fail').length;
        const condPass     = this.hseInspections.filter(h=>h.pass_fail==='Conditional Pass').length;
        const avgScore     = this.hseInspections.length ? (this.hseInspections.reduce((s,h)=>s+this.flt(h.overall_score),0)/this.hseInspections.length).toFixed(1) : 'N/A';
        const poorAssets   = this.assetInspections.filter(a=>['Poor','Critical - Action Required'].includes(a.overall_condition));
        const pendingAction= this.assetInspections.filter(a=>a.status==='Failed - Action Pending');

        // HSE score trend (last 6 inspections per facility)
        const hseByFacility = {};
        this.hseInspections.forEach(h=>{
            if (!hseByFacility[h.facility]) hseByFacility[h.facility]=[];
            hseByFacility[h.facility].push(this.flt(h.overall_score));
        });

        const condColors = {'Excellent':'#10B981','Good':'#38BDF8','Fair':'#F59E0B','Poor':'#F97316','Critical - Action Required':'#EF4444'};

        $('#ad-panel-hse').html(`
            <div class="ad-kpis">
                ${this.kpi('✅','kc-grn','Pass',            passCount,       'inspections passed')}
                ${this.kpi('🔴','kc-red','Fail',            failCount,       'facilities failed')}
                ${this.kpi('🟠','kc-amb','Conditional',     condPass,        'conditional passes')}
                ${this.kpi('📊','kc-pri','Avg score',       avgScore+'%',    'all facilities')}
                ${this.kpi('⚠️','kc-red','Poor assets',     poorAssets.length,'condition: poor/critical')}
                ${this.kpi('🔧','kc-pur','Action pending',  pendingAction.length,'asset inspections')}
            </div>

            <div class="ad-g2">
                <div class="ad-card">
                    <div class="ad-ch"><div class="ad-ct">⚠️ HSE inspections</div><button class="ad-btn ab-solid" onclick="frappe.new_doc('HSE Inspection')">+ New Inspection</button></div>
                    <div class="ad-tbl-wrap">
                        <table class="ad-tbl">
                            <thead><tr><th>Facility</th><th>Date</th><th>Type</th><th>Score</th><th>Result</th><th>Status</th><th>Inspector</th></tr></thead>
                            <tbody>
                                ${this.hseInspections.map(h=>`<tr onclick="frappe.set_route('Form','HSE Inspection','${h.name}')">
                                    <td style="font-weight:600;color:var(--ad-tx1)">${h.facility||''}</td>
                                    <td style="font-family:'JetBrains Mono',monospace;font-size:10px">${h.inspection_date||''}</td>
                                    <td style="color:var(--ad-tx3)">${h.inspection_type||''}</td>
                                    <td>
                                        <div style="display:flex;align-items:center;gap:6px">
                                            <div style="flex:1;height:4px;background:var(--ad-brd);border-radius:10px;overflow:hidden;min-width:40px">
                                                <div style="height:100%;width:${h.overall_score||0}%;background:${this.flt(h.overall_score)>=80?'#10B981':this.flt(h.overall_score)>=60?'#F59E0B':'#EF4444'};border-radius:10px"></div>
                                            </div>
                                            <span style="font-size:11px;font-family:'JetBrains Mono',monospace">${h.overall_score||0}%</span>
                                        </div>
                                    </td>
                                    <td>${h.pass_fail ? this.badge(h.pass_fail, h.pass_fail==='Pass'?'bg-grn':h.pass_fail==='Fail'?'bg-red':'bg-amb') : '—'}</td>
                                    <td>${this.statusBadge(h.status)}</td>
                                    <td style="color:var(--ad-tx3)">${h.inspector||''}</td>
                                </tr>`).join('') || '<tr><td colspan="7" style="text-align:center;color:var(--ad-tx3);padding:20px">No HSE inspections found</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
                <div class="ad-card">
                    <div class="ad-ch"><div class="ad-ct">📊 Facility HSE scores</div></div>
                    <div class="ad-cb">
                        ${Object.entries(hseByFacility).map(([fac,scores])=>{
                            const avg = scores.reduce((a,b)=>a+b,0)/scores.length;
                            return `<div class="ad-bar-row">
                                <div class="ad-bar-lbl" style="font-size:10px;width:120px">${fac}</div>
                                <div class="ad-bar"><div class="ad-bar-fill" style="width:${avg}%;background:${avg>=80?'#10B981':avg>=60?'#F59E0B':'#EF4444'}"></div></div>
                                <div class="ad-bar-val">${avg.toFixed(0)}%</div>
                            </div>`;
                        }).join('') || '<div style="color:var(--ad-tx3);font-size:12px">No HSE data yet</div>'}
                    </div>
                </div>
            </div>

            <div class="ad-card ad-row">
                <div class="ad-ch"><div class="ad-ct">🔍 Asset inspections</div><button class="ad-btn ab-solid" onclick="frappe.new_doc('Asset Inspection')">+ Inspect Asset</button></div>
                <div class="ad-tbl-wrap">
                    <table class="ad-tbl">
                        <thead><tr><th>Asset</th><th>Facility</th><th>Date</th><th>Type</th><th>Condition</th><th>Status</th><th>Inspector</th></tr></thead>
                        <tbody>
                            ${this.assetInspections.map(a=>`<tr onclick="frappe.set_route('Form','Asset Inspection','${a.name}')">
                                <td style="font-weight:600;color:var(--ad-tx1)">${a.asset||''}</td>
                                <td style="color:var(--ad-tx3)">${a.facility||''}</td>
                                <td style="font-family:'JetBrains Mono',monospace;font-size:10px">${a.inspection_date||''}</td>
                                <td style="color:var(--ad-tx3)">${a.inspection_type||''}</td>
                                <td>${a.overall_condition ? `<span style="display:inline-flex;align-items:center;gap:4px"><span style="width:7px;height:7px;border-radius:50%;background:${condColors[a.overall_condition]||'#94A3B8'}"></span>${a.overall_condition}</span>` : '—'}</td>
                                <td>${this.statusBadge(a.status)}</td>
                                <td style="color:var(--ad-tx3)">${a.inspector||''}</td>
                            </tr>`).join('') || '<tr><td colspan="7" style="text-align:center;color:var(--ad-tx3);padding:20px">No asset inspections found</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        `);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  TAB: AI INTELLIGENCE
    // ═══════════════════════════════════════════════════════════════════════════
    renderIntelligence() {
        // Client-side AI insights based on patterns in data
        const insights = this._generateInsights();
        const today    = frappe.datetime.get_today();

        // Predictive maintenance candidates
        const maintCandidates = this.vehicles.filter(v => {
            const daysToService = v.next_service_date ? this.daysLeft(v.next_service_date) : null;
            return (daysToService !== null && daysToService <= 30) ||
                   (v.odometer_reading && v.next_service_km && this.flt(v.odometer_reading) >= this.flt(v.next_service_km) * 0.95);
        });

        // SLA risk requests
        const slaRisk = this.requests.filter(r => {
            const age = this.n(r.request_age_days);
            const thresholds = { 'Urgent':1,'High':3,'Medium':7,'Low':14 };
            const thresh = thresholds[r.priority] || 7;
            return !['Completed','Closed','Rejected'].includes(r.status) && age >= thresh * 0.8;
        });

        // Utility anomalies
        const utilAnomalies = this.utilConsumed.filter(u => this.flt(u.variance_pct) > 30);

        // Cost efficiency score (0-100)
        const fleetUtil = this.vehicles.length ? (this.vehicles.filter(v=>v.status==='In Use').length/this.vehicles.length*100) : 0;
        const maintResponse = this.maintenanceRequests.length ?
            (this.maintenanceRequests.filter(m=>m.status==='Completed').length/this.maintenanceRequests.length*100) : 100;
        const complianceHealth = this.compliance.length ?
            (this.compliance.filter(c=>c.status==='Valid').length/this.compliance.length*100) : 100;
        const overallScore = Math.round((fleetUtil*0.2 + maintResponse*0.3 + complianceHealth*0.5));

        $('#ad-panel-intelligence').html(`
            <div class="ad-g4" style="margin-bottom:14px">
                <div class="ad-card" style="text-align:center;padding:20px">
                    <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:var(--ad-tx3);margin-bottom:8px">Admin Health Score</div>
                    <div style="font-size:48px;font-weight:800;color:${overallScore>=80?'var(--ad-grn)':overallScore>=60?'var(--ad-amb)':'var(--ad-red)'};line-height:1">${overallScore}</div>
                    <div style="font-size:12px;color:var(--ad-tx3);margin-top:4px">out of 100</div>
                    <div style="height:4px;background:var(--ad-brd);border-radius:10px;overflow:hidden;margin-top:12px">
                        <div style="height:100%;width:${overallScore}%;background:${overallScore>=80?'var(--ad-grn)':overallScore>=60?'var(--ad-amb)':'var(--ad-red)'};border-radius:10px;transition:width .8s"></div>
                    </div>
                </div>
                <div class="ad-card" style="padding:20px">
                    <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:var(--ad-tx3);margin-bottom:12px">Component scores</div>
                    <div class="ad-bar-row"><div class="ad-bar-lbl">Fleet utilisation</div><div class="ad-bar"><div class="ad-bar-fill" style="width:${fleetUtil.toFixed(0)}%;background:var(--ad-pri)"></div></div><div class="ad-bar-val">${fleetUtil.toFixed(0)}%</div></div>
                    <div class="ad-bar-row"><div class="ad-bar-lbl">Maint. resolution</div><div class="ad-bar"><div class="ad-bar-fill" style="width:${maintResponse.toFixed(0)}%;background:var(--ad-sky)"></div></div><div class="ad-bar-val">${maintResponse.toFixed(0)}%</div></div>
                    <div class="ad-bar-row"><div class="ad-bar-lbl">Compliance health</div><div class="ad-bar"><div class="ad-bar-fill" style="width:${complianceHealth.toFixed(0)}%;background:var(--ad-grn)"></div></div><div class="ad-bar-val">${complianceHealth.toFixed(0)}%</div></div>
                </div>
                <div class="ad-card" style="padding:20px">
                    <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:var(--ad-tx3);margin-bottom:8px">SLA risk requests</div>
                    <div style="font-size:36px;font-weight:800;color:${slaRisk.length>0?'var(--ad-amb)':'var(--ad-grn)'};line-height:1">${slaRisk.length}</div>
                    <div style="font-size:11px;color:var(--ad-tx3);margin-top:4px">approaching SLA threshold</div>
                    <div style="margin-top:12px;font-size:11px;color:var(--ad-tx2)">${slaRisk.slice(0,2).map(r=>`<div>• ${r.request_title||r.name}</div>`).join('')}</div>
                </div>
                <div class="ad-card" style="padding:20px">
                    <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:var(--ad-tx3);margin-bottom:8px">Utility anomalies</div>
                    <div style="font-size:36px;font-weight:800;color:${utilAnomalies.length>0?'var(--ad-red)':'var(--ad-grn)'};line-height:1">${utilAnomalies.length}</div>
                    <div style="font-size:11px;color:var(--ad-tx3);margin-top:4px">readings >30% above average</div>
                    <div style="margin-top:12px;font-size:11px;color:var(--ad-tx2)">${utilAnomalies.slice(0,2).map(u=>`<div>• ${u.utility_meter||''}: +${this.flt(u.variance_pct).toFixed(0)}%</div>`).join('')}</div>
                </div>
            </div>

            <div class="ad-g21">
                <div class="ad-card">
                    <div class="ad-ch">
                        <div class="ad-ct" style="gap:8px">
                            <span style="background:var(--ad-pri-x);padding:5px 7px;border-radius:7px;font-size:14px">🤖</span>
                            AI-generated insights
                        </div>
                        <button class="ad-btn ab-pri" id="ad-ai-refresh" onclick="window.__adminDash.runAIAnalysis()">
                            ✨ Deep Analysis
                        </button>
                    </div>
                    <div class="ad-cb">
                        <div id="ad-ai-insights-area">
                            ${insights.map(ins=>`
                            <div class="ad-alert-box ${ins.cls}" style="cursor:default">
                                <div style="flex:1">
                                    <div class="ait">${ins.title}</div>
                                    <div class="ais">${ins.body}</div>
                                </div>
                                ${ins.action ? `<button class="ad-btn ab-ghost" onclick="${ins.action}">→</button>` : ''}
                            </div>`).join('')}
                        </div>
                    </div>
                </div>

                <div style="display:flex;flex-direction:column;gap:14px">
                    <div class="ad-card">
                        <div class="ad-ch"><div class="ad-ct">🔧 Predictive maintenance</div></div>
                        <div class="ad-cb">
                            ${maintCandidates.length ? maintCandidates.slice(0,5).map(v=>`
                            <div class="ad-alert-box aab-a" onclick="frappe.set_route('Form','Company Vehicle','${v.name}')">
                                <div style="flex:1">
                                    <div class="ait">${v.vehicle_name||v.plate_number}</div>
                                    <div class="ais">Service due ${v.next_service_date ? `on ${v.next_service_date}` : 'based on odometer'}</div>
                                </div>
                                <span class="ad-badge bg-amb">Service due</span>
                            </div>`).join('') : '<div style="color:var(--ad-tx3);font-size:12px">No vehicles approaching service 🎉</div>'}
                        </div>
                    </div>
                    <div class="ad-card">
                        <div class="ad-ch"><div class="ad-ct">⚡ Utility anomaly alerts</div></div>
                        <div class="ad-cb">
                            ${utilAnomalies.length ? utilAnomalies.slice(0,4).map(u=>`
                            <div class="ad-alert-box ${this.flt(u.variance_pct)>50?'aab-r':'aab-a'}" onclick="frappe.set_route('Form','Utility Consumption','${u.name}')">
                                <div style="flex:1">
                                    <div class="ait">${u.utility_meter||u.utility_type||''}</div>
                                    <div class="ais">${u.facility||''} · Variance: ${this.flt(u.variance_pct).toFixed(0)}% above avg · Bill: ${this.fmt(u.total_bill)}</div>
                                </div>
                                ${this.badge('+'+this.flt(u.variance_pct).toFixed(0)+'%', this.flt(u.variance_pct)>50?'bg-red':'bg-amb')}
                            </div>`).join('') : '<div style="color:var(--ad-tx3);font-size:12px">No utility anomalies detected ✅</div>'}
                        </div>
                    </div>
                </div>
            </div>

            <div class="ad-card ad-row">
                <div class="ad-ch"><div class="ad-ct">📊 Admin performance matrix</div></div>
                <div class="ad-cb">
                    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px">
                        ${[
                            { label:'Request SLA compliance', val: this.requests.length ? Math.round((this.requests.filter(r=>!r.sla_breached).length/this.requests.length)*100) : 100, unit:'%', col:'pri' },
                            { label:'Fleet availability rate', val: this.vehicles.length ? Math.round(this.vehicles.filter(v=>v.status==='Available').length/this.vehicles.length*100) : 0, unit:'%', col:'grn' },
                            { label:'Compliance validity rate', val: this.compliance.length ? Math.round(this.compliance.filter(c=>c.status==='Valid').length/this.compliance.length*100) : 100, unit:'%', col:'sky' },
                            { label:'Maint. request resolution', val: this.maintenanceRequests.length ? Math.round(this.maintenanceRequests.filter(m=>m.status==='Completed').length/this.maintenanceRequests.length*100) : 100, unit:'%', col:'amb' },
                            { label:'HSE pass rate', val: this.hseInspections.length ? Math.round(this.hseInspections.filter(h=>h.pass_fail==='Pass').length/this.hseInspections.length*100) : 100, unit:'%', col:'pur' },
                            { label:'Incident resolution rate', val: this.incidents.length ? Math.round(this.incidents.filter(i=>['Resolved','Closed'].includes(i.status)).length/this.incidents.length*100) : 100, unit:'%', col:'red' },
                        ].map(m=>`
                        <div style="background:var(--ad-bg2);border-radius:10px;padding:14px">
                            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--ad-tx3);margin-bottom:6px">${m.label}</div>
                            <div style="font-size:28px;font-weight:800;color:var(--ad-${m.col});line-height:1">${m.val}${m.unit}</div>
                            <div style="height:4px;background:var(--ad-brd);border-radius:10px;overflow:hidden;margin-top:8px">
                                <div style="height:100%;width:${m.val}%;background:var(--ad-${m.col});border-radius:10px;transition:width .8s"></div>
                            </div>
                        </div>`).join('')}
                    </div>
                </div>
            </div>
        `);
    }

    _generateInsights() {
        const insights = [];
        const slaBreached = this.requests.filter(r=>r.sla_breached==1);
        const expiredComp = this.compliance.filter(c=>c.status==='Expired');
        const groundedVeh = this.vehicles.filter(v=>v.status==='Grounded');
        const highGenHrs  = this.genLogs.slice(0,5).reduce((s,g)=>s+this.flt(g.run_hours),0);
        const openInc     = this.incidents.filter(i=>!['Resolved','Closed'].includes(i.status));
        const expiringCon = this.contracts.filter(c=>{const d=this.daysLeft(c.end_date);return d!==null&&d>=0&&d<=30;});

        if (slaBreached.length > 0) {
            const types = [...new Set(slaBreached.map(r=>r.request_type))].join(', ');
            insights.push({ cls:'aab-r', title:`${slaBreached.length} SLA breach${slaBreached.length>1?'es':''} detected`, body:`Request types affected: ${types}. Consider pre-approving recurring request budgets.`, action:`window.__adminDash.switchTab('requests')` });
        }
        if (expiredComp.length > 0) {
            insights.push({ cls:'aab-r', title:`${expiredComp.length} compliance item${expiredComp.length>1?'s':''} expired`, body:`${expiredComp.map(c=>c.compliance_item).join(', ')}. Non-compliance exposes the organisation to regulatory risk.`, action:`window.__adminDash.switchTab('compliance')` });
        }
        if (groundedVeh.length > 0) {
            insights.push({ cls:'aab-r', title:`${groundedVeh.length} vehicle${groundedVeh.length>1?'s':''} grounded`, body:`${groundedVeh.map(v=>v.vehicle_name||v.plate_number).join(', ')}. Review insurance and licence expiry. Fleet capacity is reduced.`, action:`window.__adminDash.switchTab('fleet')` });
        }
        if (highGenHrs > 80) {
            insights.push({ cls:'aab-a', title:'High generator runtime detected', body:`${highGenHrs.toFixed(0)} hours in recent period. This indicates persistent grid outages. Recommend ROI analysis for solar UPS installation.`, action:null });
        }
        if (expiringCon.length > 0) {
            insights.push({ cls:'aab-a', title:`${expiringCon.length} contract${expiringCon.length>1?'s':''} expiring within 30 days`, body:`${expiringCon.map(c=>c.contract_title||c.vendor).join(', ')}. Begin renewal negotiations now to avoid service gaps.`, action:`window.__adminDash.switchTab('contracts')` });
        }
        if (openInc.length > 0) {
            const severe = openInc.filter(i=>['Severe','Critical'].includes(i.severity));
            if (severe.length > 0) insights.push({ cls:'aab-r', title:`${severe.length} severe/critical incident${severe.length>1?'s':''} unresolved`, body:`${severe.map(i=>i.incident_title||i.incident_type).join(', ')}. Escalate to management.`, action:`window.__adminDash.switchTab('security')` });
        }
        if (insights.length === 0) {
            insights.push({ cls:'aab-g', title:'All systems performing within normal parameters', body:'No critical issues detected. Continue monitoring compliance expiry dates and fleet documents for proactive management.', action:null });
        }
        return insights;
    }

    async runAIAnalysis() {
        const btn = document.getElementById('ad-ai-refresh');
        if (btn) btn.innerHTML = '<span class="ad-ai-spin">⟳</span> Analysing…';

        const area = document.getElementById('ad-ai-insights-area');
        if (area) area.innerHTML = '<div style="color:var(--ad-tx3);font-size:12px;padding:16px;text-align:center"><span class="ad-ai-spin" style="display:inline-block">⟳</span> Calling AI for deep analysis…</div>';

        try {
            // Build context summary for AI
            const slaBreached = this.requests.filter(r=>r.sla_breached==1).length;
            const expiredComp = this.compliance.filter(c=>c.status==='Expired').length;
            const genHrsMTD   = this.genLogs.filter(g=>g.log_date&&g.log_date.substring(0,7)===frappe.datetime.get_today().substring(0,7)).reduce((s,g)=>s+this.flt(g.run_hours),0);
            const expiringCon = this.contracts.filter(c=>{const d=this.daysLeft(c.end_date);return d!==null&&d>=0&&d<=60;}).length;
            const fleetUtil   = this.vehicles.length ? (this.vehicles.filter(v=>v.status==='Available').length/this.vehicles.length*100).toFixed(0) : 0;
            const openMaint   = this.maintenanceRequests.filter(m=>!['Completed','Closed'].includes(m.status)).length;

            const prompt = `You are an expert administrative operations analyst for a Nigerian organisation. Analyse this admin dashboard data and provide 5 specific, actionable insights:

Data snapshot:
- Open admin requests: ${this.requests.filter(r=>!['Completed','Closed','Rejected'].includes(r.status)).length} (${slaBreached} SLA breaches)
- Fleet: ${this.vehicles.length} vehicles, ${this.vehicles.filter(v=>v.status==='Available').length} available, ${this.vehicles.filter(v=>v.status==='Grounded').length} grounded (${fleetUtil}% availability)
- Generator runtime MTD: ${genHrsMTD.toFixed(1)} hours (indicates EKEDC grid reliability issue)
- Open maintenance requests: ${openMaint} across ${this.facilities.length} facilities
- Compliance: ${expiredComp} expired items, ${this.compliance.filter(c=>c.status==='Expiring Soon').length} expiring soon
- Contracts: ${expiringCon} expiring within 60 days, total value ${this.fmt(this.contracts.filter(c=>c.status==='Active').reduce((s,c)=>s+this.flt(c.contract_value),0))}
- Security incidents: ${this.incidents.filter(i=>!['Resolved','Closed'].includes(i.status)).length} open
- HSE pass rate: ${this.hseInspections.length ? Math.round(this.hseInspections.filter(h=>h.pass_fail==='Pass').length/this.hseInspections.length*100) : 100}%

Provide 5 specific insights with: risk level (Critical/High/Medium), root cause analysis, and concrete next action. Format each as JSON: { "risk": "Critical|High|Medium", "title": "...", "body": "...", "action": "..." }. Return a JSON array only.`;

            const response = await fetch('/api/method/ecclesia.api.ai_diagnosis.get_ai_insight', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-Frappe-CSRF-Token': frappe.csrf_token },
                body: JSON.stringify({ prompt, context: 'admin_dashboard', max_tokens: 1200 })
            });

            if (!response.ok) throw new Error('AI API error');
            const data = await response.json();
            const text = data.message?.response || data.message || '';

            // Parse JSON from AI response
            let aiInsights = [];
            try {
                const match = text.match(/\[[\s\S]*\]/);
                if (match) aiInsights = JSON.parse(match[0]);
            } catch(e) {
                // Fallback: show raw text
                aiInsights = [{ risk:'Medium', title:'AI Analysis', body: text.substring(0,500), action:'' }];
            }

            const riskMap = { 'Critical':'aab-r', 'High':'aab-a', 'Medium':'aab-b' };
            if (area) area.innerHTML = aiInsights.map(ins=>`
                <div class="ad-alert-box ${riskMap[ins.risk]||'aab-b'}" style="cursor:default;margin-bottom:8px">
                    <div style="flex:1">
                        <div class="ait">${this.badge(ins.risk||'Medium', ins.risk==='Critical'?'bg-red':ins.risk==='High'?'bg-amb':'bg-pri')} &nbsp;${ins.title||''}</div>
                        <div class="ais" style="margin-top:4px">${ins.body||ins.action||''}</div>
                        ${ins.action && ins.action !== ins.body ? `<div style="font-size:11px;color:var(--ad-pri);margin-top:4px;font-weight:600">→ ${ins.action}</div>` : ''}
                    </div>
                </div>`).join('');

        } catch(e) {
            console.error('Admin AI analysis failed:', e);
            // Fall back to client-side insights
            const insights = this._generateInsights();
            if (area) area.innerHTML = insights.map(ins=>`
                <div class="ad-alert-box ${ins.cls}" style="cursor:default">
                    <div style="flex:1"><div class="ait">${ins.title}</div><div class="ais">${ins.body}</div></div>
                </div>`).join('');
        }

        if (btn) btn.innerHTML = '✨ Deep Analysis';
    }

    exportData() {
        const rows = [['Name','Type','Priority','Status','Employee','Department','Request Date','Est. Cost']];
        this.requests.forEach(r => rows.push([
            r.request_title||r.name, r.request_type, r.priority, r.status,
            r.employee, r.department, r.request_date, r.estimated_cost||0
        ]));
        const csv = rows.map(r => r.map(v => `"${(v||'').toString().replace(/"/g,'""')}"`).join(',')).join('\n');
        const blob = new Blob([csv], {type:'text/csv'});
        const url  = URL.createObjectURL(blob);
        const a    = document.createElement('a'); a.href=url; a.download='admin_dashboard_export.csv'; a.click();
        URL.revokeObjectURL(url);
        frappe.show_alert({ message:'Export downloaded', indicator:'green' });
    }
}
