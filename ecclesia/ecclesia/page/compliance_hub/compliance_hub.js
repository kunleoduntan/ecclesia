// Copyright (c) 2026, Value Impacts Consulting
// ecclesia/ecclesia/page/compliance_hub/compliance_hub.js
//
// ╔══════════════════════════════════════════════════════════════════════════╗
// ║  ComplianceHQ v3 — Full Organisational GRC Command Centre               ║
// ║  9 Themes · 12 Tabs · 11 Compliance Domains · AI Analysis · Excel      ║
// ╚══════════════════════════════════════════════════════════════════════════╝

frappe.pages['compliance-hub'] = frappe.pages['compliance-hub'] || {};

frappe.pages['compliance-hub'].on_page_load = function(wrapper) {
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

frappe.pages['compliance-hub'].on_page_show = function(wrapper) {
    if (window.__chq3) window.__chq3.refresh(true);
};

// ── BACKEND PATH ─────────────────────────────────────────────────────────────
const API = 'ecclesia.ecclesia.page.compliance_hub.compliance_hub.';

// ── Theme Registry ────────────────────────────────────────────────────────────
const THEMES = {
    professional: { n: 'Professional', i: '⚖️', dark: false, p: '#1E3A5F', pd: '#152C47', px: 'rgba(30,58,95,.09)', a: '#2563EB', r: '#DC2626', rx: 'rgba(220,38,38,.09)', am: '#D97706', ax: 'rgba(217,119,6,.09)', g: '#059669', gx: 'rgba(5,150,105,.09)', s: '#0284C7', sx: 'rgba(2,132,199,.09)', v: '#7C3AED', vx: 'rgba(124,58,237,.09)', bg: '#F8FAFC', b2: '#F1F5F9', b3: '#E2E8F0', c: '#FFFFFF', bd: '#E2E8F0', b2d: '#CBD5E1', t1: '#0F172A', t2: '#475569', t3: '#94A3B8', bn: 'linear-gradient(135deg,#0F172A,#1E3A5F 50%,#2563EB 80%,#0284C7)' },
    midnight: { n: 'Midnight', i: '🌙', dark: true, p: '#818CF8', pd: '#6366F1', px: 'rgba(129,140,248,.12)', a: '#A5B4FC', r: '#F87171', rx: 'rgba(248,113,113,.12)', am: '#FCD34D', ax: 'rgba(252,211,77,.12)', g: '#34D399', gx: 'rgba(52,211,153,.12)', s: '#38BDF8', sx: 'rgba(56,189,248,.12)', v: '#C084FC', vx: 'rgba(192,132,252,.12)', bg: '#0F172A', b2: '#1E293B', b3: '#334155', c: '#1E293B', bd: 'rgba(255,255,255,.08)', b2d: 'rgba(255,255,255,.14)', t1: '#F1F5F9', t2: '#94A3B8', t3: '#475569', bn: 'linear-gradient(135deg,#020617,#0F172A 50%,#1E3A5F 70%,#312E81)' },
    verdant: { n: 'Verdant', i: '🌿', dark: false, p: '#059669', pd: '#047857', px: 'rgba(5,150,105,.09)', a: '#34D399', r: '#EF4444', rx: 'rgba(239,68,68,.09)', am: '#F59E0B', ax: 'rgba(245,158,11,.09)', g: '#10B981', gx: 'rgba(16,185,129,.09)', s: '#0EA5E9', sx: 'rgba(14,165,233,.09)', v: '#8B5CF6', vx: 'rgba(139,92,246,.09)', bg: '#ECFDF5', b2: '#D1FAE5', b3: '#A7F3D0', c: '#FFFFFF', bd: '#A7F3D0', b2d: '#6EE7B7', t1: '#022C22', t2: '#065F46', t3: '#6EE7B7', bn: 'linear-gradient(135deg,#022C22,#047857 40%,#059669 70%,#10B981)' },
    steel: { n: 'Steel', i: '🔩', dark: false, p: '#0284C7', pd: '#0369A1', px: 'rgba(2,132,199,.09)', a: '#38BDF8', r: '#EF4444', rx: 'rgba(239,68,68,.09)', am: '#F59E0B', ax: 'rgba(245,158,11,.09)', g: '#10B981', gx: 'rgba(16,185,129,.09)', s: '#06B6D4', sx: 'rgba(6,182,212,.09)', v: '#8B5CF6', vx: 'rgba(139,92,246,.09)', bg: '#F8FAFC', b2: '#F1F5F9', b3: '#E2E8F0', c: '#FFFFFF', bd: '#E2E8F0', b2d: '#CBD5E1', t1: '#0F172A', t2: '#475569', t3: '#94A3B8', bn: 'linear-gradient(135deg,#0F172A,#1E3A5F 40%,#0284C7 75%,#06B6D4)' },
    ember: { n: 'Ember', i: '🔥', dark: false, p: '#F97316', pd: '#EA580C', px: 'rgba(249,115,22,.09)', a: '#FB923C', r: '#EF4444', rx: 'rgba(239,68,68,.09)', am: '#EAB308', ax: 'rgba(234,179,8,.09)', g: '#22C55E', gx: 'rgba(34,197,94,.09)', s: '#0EA5E9', sx: 'rgba(14,165,233,.09)', v: '#A855F7', vx: 'rgba(168,85,247,.09)', bg: '#FFF7ED', b2: '#FFEDD5', b3: '#FED7AA', c: '#FFFFFF', bd: '#FED7AA', b2d: '#FDBA74', t1: '#431407', t2: '#9A3412', t3: '#FDBA74', bn: 'linear-gradient(135deg,#431407,#C2410C 40%,#F97316 70%,#EAB308)' },
    arctic: { n: 'Arctic', i: '❄️', dark: false, p: '#0EA5E9', pd: '#0284C7', px: 'rgba(14,165,233,.09)', a: '#7DD3FC', r: '#EF4444', rx: 'rgba(239,68,68,.09)', am: '#F59E0B', ax: 'rgba(245,158,11,.09)', g: '#10B981', gx: 'rgba(16,185,129,.09)', s: '#6366F1', sx: 'rgba(99,102,241,.09)', v: '#EC4899', vx: 'rgba(236,72,153,.09)', bg: '#F0F9FF', b2: '#E0F2FE', b3: '#BAE6FD', c: '#FFFFFF', bd: '#BAE6FD', b2d: '#7DD3FC', t1: '#0C4A6E', t2: '#075985', t3: '#7DD3FC', bn: 'linear-gradient(135deg,#0C4A6E,#0369A1 40%,#0EA5E9 70%,#06B6D4)' },
    nova: { n: 'Nova', i: '🌟', dark: false, p: '#7C3AED', pd: '#6D28D9', px: 'rgba(124,58,237,.09)', a: '#A78BFA', r: '#EF4444', rx: 'rgba(239,68,68,.09)', am: '#F59E0B', ax: 'rgba(245,158,11,.09)', g: '#10B981', gx: 'rgba(16,185,129,.09)', s: '#06B6D4', sx: 'rgba(6,182,212,.09)', v: '#EC4899', vx: 'rgba(236,72,153,.09)', bg: '#FAF5FF', b2: '#F5F3FF', b3: '#EDE9FE', c: '#FFFFFF', bd: '#E9D5FF', b2d: '#D8B4FE', t1: '#2E1065', t2: '#5B21B6', t3: '#A78BFA', bn: 'linear-gradient(135deg,#1E1B4B,#4C1D95 40%,#7C3AED 70%,#EC4899)' },
    executive: { n: 'Executive', i: '👔', dark: false, p: '#1E293B', pd: '#0F172A', px: 'rgba(30,41,59,.09)', a: '#475569', r: '#EF4444', rx: 'rgba(239,68,68,.09)', am: '#F59E0B', ax: 'rgba(245,158,11,.09)', g: '#10B981', gx: 'rgba(16,185,129,.09)', s: '#0284C7', sx: 'rgba(2,132,199,.09)', v: '#7C3AED', vx: 'rgba(124,58,237,.09)', bg: '#FAFAFA', b2: '#F4F4F5', b3: '#E4E4E7', c: '#FFFFFF', bd: '#E4E4E7', b2d: '#D4D4D8', t1: '#18181B', t2: '#3F3F46', t3: '#71717A', bn: 'linear-gradient(135deg,#09090B,#18181B 40%,#1E293B 70%,#334155)' },
    forest: { n: 'Forest', i: '🌲', dark: true, p: '#22C55E', pd: '#16A34A', px: 'rgba(34,197,94,.12)', a: '#4ADE80', r: '#F87171', rx: 'rgba(248,113,113,.12)', am: '#FBBF24', ax: 'rgba(251,191,36,.12)', g: '#22C55E', gx: 'rgba(34,197,94,.12)', s: '#38BDF8', sx: 'rgba(56,189,248,.12)', v: '#F472B6', vx: 'rgba(244,114,182,.12)', bg: '#052E16', b2: '#14532D', b3: '#166534', c: '#14532D', bd: 'rgba(187,247,208,.1)', b2d: 'rgba(134,239,172,.18)', t1: '#F0FDF4', t2: '#86EFAC', t3: '#4ADE80', bn: 'linear-gradient(135deg,#052E16,#14532D 40%,#166534 70%,#22C55E)' },
};

const DOMAINS = [
    { key: 'overview', icon: '🏠', label: 'Overview', badge: null },
    { key: 'statutory', icon: '💰', label: 'Statutory Tax', badge: 'vat_overdue' },
    { key: 'corporate', icon: '🏢', label: 'Governance', badge: 'corporate_issues' },
    { key: 'contracts', icon: '📄', label: 'Contracts', badge: 'contract_breaches' },
    { key: 'ndpr', icon: '🔒', label: 'NDPR', badge: 'breach_open' },
    { key: 'aml', icon: '🕵️', label: 'AML & KYC', badge: 'high_risk' },
    { key: 'labour', icon: '👷', label: 'Labour', badge: 'permit_expired' },
    { key: 'environmental', icon: '🌿', label: 'Environmental', badge: 'env_expired' },
    { key: 'industry', icon: '🏭', label: 'Regulatory', badge: 'reg_overdue' },
    { key: 'fraud', icon: '🚨', label: 'Integrity', badge: 'wb_open' },
    { key: 'training', icon: '🎓', label: 'Training', badge: 'training_gap' },
    { key: 'ai', icon: '🤖', label: 'AI Analysis', badge: null },
];

// ═══════════════════════════════════════════════════════════════════════════════
class ComplianceHQv3 {

    constructor(wrapper) {
        this.wrapper = wrapper;
        this.page = frappe.ui.make_app_page({ parent: wrapper, title: 'ComplianceHQ', single_column: true });
        this.charts = {};
        this.activeTab = 'overview';
        this.company = frappe.defaults.get_default('company') || '';
        this.fiscalMonth = _curMonth();
        this.data = {};
        this.v3data = {};
        this.scores = {};
        this.theme = _lsGet('chq3-theme', 'professional');
        window.__chq3 = this;
        this._init();
    }

    _init() {
        this._css();
        this._layout();
        this._applyTheme(this.theme, false);
        this._actions();
        this._bind();
        this._clock();
        // Load data after a small delay to ensure DOM is ready
        setTimeout(() => this.loadAll(false), 500);
        setInterval(() => this.refresh(true), 60000);
    }

    // ── Theme ─────────────────────────────────────────────────────────────────
    _applyTheme(key, save = true) {
        const t = THEMES[key] || THEMES.professional;
        this.theme = key;
        if (save) _lsSet('chq3-theme', key);
        const root = document.getElementById('chq3-root');
        if (!root) return;
        const map = { p: 'pri', pd: 'pri_d', px: 'pri_x', a: 'acc', r: 'red', rx: 'red_x', am: 'amb', ax: 'amb_x',
            g: 'grn', gx: 'grn_x', s: 'sky', sx: 'sky_x', v: 'pur', vx: 'pur_x',
            bg: 'bg', b2: 'bg2', b3: 'bg3', c: 'card', bd: 'brd', b2d: 'brd2',
            t1: 'tx1', t2: 'tx2', t3: 'tx3', bn: 'banner' };
        Object.entries(map).forEach(([k, v]) => { if (t[k]) root.style.setProperty(`--${v}`, t[k]); });
        if (t.dark) {
            root.classList.add('dark');
        } else {
            root.classList.remove('dark');
        }
        const lbl = document.getElementById('chq3-theme-lbl');
        if (lbl) lbl.textContent = t.i + ' ' + t.n;
        Object.values(this.charts).forEach(c => { try { c.update(); } catch (e) { } });
    }

    openThemePicker() {
        const cur = this.theme;
        const dialog = new frappe.ui.Dialog({
            title: '🎨 ComplianceHQ Theme',
            size: 'large',
            fields: [{
                fieldtype: 'HTML',
                options: `
                <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px">
                ${Object.entries(THEMES).map(([k,t]) => `
                  <div onclick="window.__chq3._applyTheme('${k}');if(window.__chq3_theme_dialog)window.__chq3_theme_dialog.hide();"
                    style="display:flex;align-items:center;gap:10px;padding:11px;border-radius:10px;
                           border:2px solid ${k===cur?t.p:t.b2d||'#CBD5E1'};
                           background:${t.c};cursor:pointer;transition:all 0.2s"
                    onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
                    <div style="font-size:20px;width:34px;height:34px;border-radius:8px;background:${t.px};
                                display:flex;align-items:center;justify-content:center">${t.i}</div>
                    <div>
                      <div style="font-size:12px;font-weight:700;color:${t.t1}">${t.n}</div>
                      <div style="font-size:10px;color:${t.t3}">${t.dark?'🌙 Dark':'☀️ Light'}</div>
                    </div>
                    ${k===cur?`<span style="margin-left:auto;color:${t.p};font-size:16px">✓</span>`:''}
                  </div>`).join('')}
                </div>
                <div style="margin-top:12px;text-align:center;font-size:11px;color:var(--tx3)">Click any theme to apply instantly</div>
                `
            }]
        });
        window.__chq3_theme_dialog = dialog;
        dialog.show();
    }

    // ── CSS ───────────────────────────────────────────────────────────────────
    _css() {
        if (document.getElementById('chq3-css')) return;
        const s = document.createElement('style');
        s.id = 'chq3-css';
        s.textContent = `
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600;700&display=swap');
        #chq3-root{--pri:#1E3A5F;--pri_x:rgba(30,58,95,.09);--red:#DC2626;--red_x:rgba(220,38,38,.09);--amb:#D97706;--amb_x:rgba(217,119,6,.09);--grn:#059669;--grn_x:rgba(5,150,105,.09);--sky:#0284C7;--sky_x:rgba(2,132,199,.09);--pur:#7C3AED;--pur_x:rgba(124,58,237,.09);--bg:#F8FAFC;--bg2:#F1F5F9;--bg3:#E2E8F0;--card:#FFFFFF;--brd:#E2E8F0;--brd2:#CBD5E1;--tx1:#0F172A;--tx2:#475569;--tx3:#94A3B8;--banner:linear-gradient(135deg,#0F172A,#1E3A5F,#2563EB);font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--tx1);min-height:100vh;transition:background .3s,color .3s}
        #chq3-root *{box-sizing:border-box}
        #chq3-root.dark{--bg:#0F172A;--bg2:#1E293B;--bg3:#334155;--card:#1E293B;--brd:rgba(255,255,255,.08);--brd2:rgba(255,255,255,.14);--tx1:#F1F5F9;--tx2:#94A3B8;--tx3:#475569}
        .c3-ban{background:var(--banner);padding:22px 28px 18px;margin:-15px -15px 18px;position:relative;overflow:hidden;color:#fff;border-radius:0 0 12px 12px;box-shadow:0 4px 20px rgba(0,0,0,.15)}
        .c3-ban::before{content:'';position:absolute;width:600px;height:600px;top:-60%;right:-10%;border-radius:50%;background:radial-gradient(circle,rgba(255,255,255,.05),transparent 65%)}
        .c3-ban::after{content:'';position:absolute;width:300px;height:300px;bottom:-40%;left:-5%;border-radius:50%;background:radial-gradient(circle,rgba(255,255,255,.03),transparent 65%)}
        .c3-bi{position:relative;z-index:1;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:14px}
        .c3-ban h1{font-size:22px;font-weight:900;letter-spacing:-.4px;margin:0 0 5px;display:flex;align-items:center;gap:10px}
        .c3-meta{display:flex;align-items:center;gap:12px;font-size:11px;opacity:.82;flex-wrap:wrap}
        .c3-live{display:inline-flex;align-items:center;gap:5px;background:rgba(5,150,105,.22);padding:3px 9px;border-radius:20px;font-size:10px;color:#34d399;border:1px solid rgba(5,150,105,.3);backdrop-filter:blur(4px)}
        .c3-dot{width:7px;height:7px;background:#34d399;border-radius:50%;animation:pulse 2s infinite}
        @keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(1.3)}}
        .c3-chip{background:rgba(255,255,255,.14);padding:3px 10px;border-radius:20px;font-size:10px;font-weight:600;backdrop-filter:blur(4px)}
        .c3-tbtn{display:inline-flex;align-items:center;gap:6px;padding:5px 13px;border-radius:20px;font-size:11px;font-weight:700;background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.25);color:#fff;cursor:pointer;transition:all .2s;font-family:inherit;backdrop-filter:blur(4px)}
        .c3-tbtn:hover{background:rgba(255,255,255,.3);transform:translateY(-1px)}
        .c3-tbtn select{background:transparent;border:none;color:#fff;font-weight:700;font-size:11px;cursor:pointer;outline:none}
        .c3-score{display:inline-flex;flex-direction:column;align-items:center;justify-content:center;width:76px;height:76px;border-radius:50%;border:3px solid rgba(255,255,255,.3);background:rgba(255,255,255,.1);backdrop-filter:blur(8px);transition:border-color .5s}
        .c3-sn{font-size:20px;font-weight:900;line-height:1}
        .c3-sl{font-size:9px;opacity:.7;margin-top:2px}
        .c3-alerts{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:14px}
        .c3-alert{display:flex;align-items:center;gap:6px;padding:5px 12px;border-radius:9px;font-size:11px;font-weight:600;cursor:pointer;border:1px solid transparent;transition:all .2s;text-decoration:none !important}
        .c3-alert:hover{transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,.1)}
        .ca-r{background:var(--red_x);border-color:rgba(220,38,38,.2);color:var(--red)}
        .ca-a{background:var(--amb_x);border-color:rgba(217,119,6,.2);color:var(--amb)}
        .ca-g{background:var(--grn_x);border-color:rgba(5,150,105,.2);color:var(--grn)}
        .ca-b{background:var(--pri_x);border-color:rgba(30,58,95,.2);color:var(--pri)}
        .c3-tabs{display:flex;gap:1px;background:var(--card);border:1px solid var(--brd);border-radius:12px;margin-bottom:16px;overflow-x:auto;scrollbar-width:none;box-shadow:0 2px 8px rgba(0,0,0,.04)}
        .c3-tabs::-webkit-scrollbar{display:none}
        .c3-tab{display:flex;align-items:center;gap:5px;padding:9px 14px;font-size:11px;font-weight:600;color:var(--tx2);cursor:pointer;border-bottom:3px solid transparent;transition:all .15s;white-space:nowrap;background:none;border-left:none;border-right:none;border-top:none;font-family:inherit}
        .c3-tab:hover{color:var(--pri);background:var(--pri_x)}
        .c3-tab.on{color:var(--pri);border-bottom-color:var(--pri);background:var(--pri_x)}
        .c3-n{background:var(--red);color:#fff;font-size:9px;font-weight:800;padding:1px 5px;border-radius:20px;min-width:15px;text-align:center;animation:pulse 2s infinite}
        .c3-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-bottom:16px}
        .c3-kpi{background:var(--card);border:1px solid var(--brd);border-radius:12px;padding:14px 16px;cursor:pointer;transition:all .2s;position:relative;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.04)}
        .c3-kpi::after{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--kc,var(--pri));opacity:0;transition:opacity .2s}
        .c3-kpi:hover{transform:translateY(-3px);box-shadow:0 8px 25px rgba(0,0,0,.1)}
        .c3-kpi:hover::after{opacity:1}
        .kp{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:var(--tx3);margin-bottom:4px}
        .kv{font-size:22px;font-weight:800;color:var(--tx1);line-height:1;margin-bottom:2px}
        .ks{font-size:10px;color:var(--tx3)}
        .c3-card{background:var(--card);border:1px solid var(--brd);border-radius:12px;overflow:hidden;transition:all .2s;margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,.04)}
        .c3-card:hover{box-shadow:0 4px 20px rgba(0,0,0,.08)}
        .c3-ch{padding:12px 17px;border-bottom:1px solid var(--brd);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px}
        .c3-ct{display:flex;align-items:center;gap:8px;font-size:13px;font-weight:700;color:var(--tx1)}
        .c3-cb{padding:14px 17px}
        .c3-g2{display:grid;grid-template-columns:1fr 1fr;gap:13px;margin-bottom:13px}
        .c3-g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:13px;margin-bottom:13px}
        .c3-g4{display:grid;grid-template-columns:repeat(4,1fr);gap:11px;margin-bottom:13px}
        .c3-g21{display:grid;grid-template-columns:2fr 1fr;gap:13px;margin-bottom:13px}
        .c3-btn{display:inline-flex;align-items:center;gap:5px;padding:5px 12px;border-radius:20px;font-size:11px;font-weight:700;cursor:pointer;border:1.5px solid transparent;font-family:inherit;transition:all .2s;text-decoration:none !important}
        .c3-btn:hover{transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,.1)}
        .cb-p{background:var(--pri_x);color:var(--pri);border-color:rgba(30,58,95,.2)}.cb-p:hover{background:var(--pri);color:#fff}
        .cb-g{background:var(--grn_x);color:var(--grn);border-color:rgba(5,150,105,.2)}.cb-g:hover{background:var(--grn);color:#fff}
        .cb-r{background:var(--red_x);color:var(--red);border-color:rgba(220,38,38,.2)}.cb-r:hover{background:var(--red);color:#fff}
        .cb-a{background:var(--amb_x);color:var(--amb);border-color:rgba(217,119,6,.2)}.cb-a:hover{background:var(--amb);color:#fff}
        .cb-s{background:var(--sky_x);color:var(--sky);border-color:rgba(2,132,199,.2)}.cb-s:hover{background:var(--sky);color:#fff}
        .cb-v{background:var(--pur_x);color:var(--pur);border-color:rgba(124,58,237,.2)}.cb-v:hover{background:var(--pur);color:#fff}
        .cb-solid{background:var(--pri);color:#fff}.cb-solid:hover{opacity:.85}
        .cb-ghost{background:transparent;color:var(--tx2);border-color:var(--brd2)}.cb-ghost:hover{background:var(--bg2)}
        .c3-bdg{display:inline-flex;align-items:center;gap:3px;padding:2px 7px;border-radius:20px;font-size:10px;font-weight:700;white-space:nowrap}
        .bg-g{background:var(--grn_x);color:var(--grn)}.bg-r{background:var(--red_x);color:var(--red)}.bg-a{background:var(--amb_x);color:var(--amb)}.bg-b{background:var(--pri_x);color:var(--pri)}.bg-s{background:var(--sky_x);color:var(--sky)}.bg-v{background:var(--pur_x);color:var(--pur)}.bg-gr{background:var(--bg3);color:var(--tx3)}
        .c3-tw{overflow-x:auto;max-height:480px;overflow-y:auto;scrollbar-width:thin;scrollbar-color:var(--brd2) transparent}
        .c3-tw::-webkit-scrollbar{width:4px;height:4px}.c3-tw::-webkit-scrollbar-thumb{background:var(--brd2);border-radius:10px}
        .c3-tbl{width:100%;border-collapse:collapse;font-size:12px}
        .c3-tbl thead th{padding:8px 12px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--tx3);background:var(--bg2);border-bottom:2px solid var(--brd);position:sticky;top:0;z-index:1;white-space:nowrap}
        .c3-tbl tbody td{padding:8px 12px;border-bottom:1px solid var(--brd);color:var(--tx2)}
        .c3-tbl tbody tr{transition:all .1s}.c3-tbl tbody tr:hover{background:var(--pri_x);transform:scale(1.005)}
        .c3-tbl tbody tr:hover td{color:var(--tx1)}
        .c3-tbl tbody tr:last-child td{border-bottom:none}
        .c3-dsg{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:9px;margin-bottom:16px}
        .c3-ds{background:var(--card);border:1px solid var(--brd);border-radius:11px;padding:12px;text-align:center;cursor:pointer;transition:all .2s;box-shadow:0 1px 3px rgba(0,0,0,.04)}
        .c3-ds:hover{transform:translateY(-3px);border-color:var(--pri);box-shadow:0 4px 16px rgba(0,0,0,.08)}
        .c3-ds-i{font-size:22px;margin-bottom:6px}
        .c3-ds-n{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:var(--tx3);margin-bottom:5px}
        .c3-ds-v{font-size:22px;font-weight:800;line-height:1}
        .c3-ds-b{height:4px;background:var(--brd);border-radius:10px;overflow:hidden;margin-top:7px}
        .c3-ds-bf{height:100%;border-radius:10px;transition:width .7s cubic-bezier(.4,0,.2,1)}
        .c3-hr{border:none;border-top:1px solid var(--brd);margin:12px 0}
        .c3-panel{display:none}.c3-panel.on{display:block}
        .c3-mono{font-family:'JetBrains Mono',monospace}
        .c3-empty{text-align:center;padding:32px;color:var(--tx3);font-size:13px}
        .c3-bar-row{display:flex;align-items:center;gap:8px;margin-bottom:7px}
        .c3-bar-lbl{font-size:11px;color:var(--tx2);width:140px;flex-shrink:0}
        .c3-bar{flex:1;height:5px;background:var(--brd);border-radius:40px;overflow:hidden}
        .c3-bar-f{height:100%;border-radius:40px;transition:width .6s cubic-bezier(.4,0,.2,1)}
        .c3-bar-val{font-size:10px;font-family:'JetBrains Mono',monospace;font-weight:700;width:50px;text-align:right;color:var(--tx1)}
        .c3-spin{animation:c3spin .8s linear infinite;display:inline-block}
        @keyframes c3spin{to{transform:rotate(360deg)}}
        .c3-loader{position:fixed;inset:0;background:rgba(10,15,30,.85);display:flex;align-items:center;justify-content:center;flex-direction:column;gap:13px;z-index:999;backdrop-filter:blur(8px)}
        .c3-spinner{width:36px;height:36px;border:3px solid var(--brd2);border-top-color:var(--pri);border-radius:50%;animation:c3spin .7s linear infinite}
        .c3-content{padding:0 16px 32px}
        @media(max-width:900px){.c3-g2,.c3-g3,.c3-g4,.c3-g21{grid-template-columns:1fr}}
        .c3-chart-container{position:relative;min-height:200px;width:100%}
        .c3-stat-badge{font-size:10px;font-weight:600;padding:2px 8px;border-radius:12px;display:inline-block}
        `;
        document.head.appendChild(s);
    }

    // ── Layout ────────────────────────────────────────────────────────────────
    _layout() {
        const main = this.page.main;
        $(main).empty();
        
        const tabButtons = DOMAINS.map(d =>
            `<button class="c3-tab${d.key === 'overview' ? ' on' : ''}" data-tab="${d.key}">
               ${d.icon} ${d.label}
               ${d.badge ? `<span class="c3-n" id="c3-n-${d.key}" style="display:none">0</span>` : ''}
             </button>`
        ).join('');
        
        const panels = DOMAINS.map(d =>
            `<div id="c3-p-${d.key}" class="c3-panel${d.key === 'overview' ? ' on' : ''}"></div>`
        ).join('');

        const html = `
        <div id="chq3-root">
          <div class="c3-ban">
            <div class="c3-bi">
              <div style="display:flex;align-items:center;gap:15px;flex-wrap:wrap">
                <div>
                  <h1>⚖️ ComplianceHQ <span style="font-size:13px;opacity:.7;font-weight:400">v3 · Full GRC</span></h1>
                  <div class="c3-meta">
                    <span>📅 <span id="c3-date"></span></span>
                    <span id="c3-clock" class="c3-mono"></span>
                    <span class="c3-live"><span class="c3-dot"></span> Live</span>
                    <span class="c3-chip" id="c3-c1">Loading…</span>
                    <span class="c3-chip" id="c3-c2">Loading…</span>
                  </div>
                </div>
                <div class="c3-score" id="c3-score-ring">
                  <div class="c3-sn" id="c3-score-n">—</div>
                  <div class="c3-sl">GRC Score</div>
                </div>
              </div>
              <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
                <select id="c3-co" class="c3-tbtn" style="cursor:pointer;outline:none;background:rgba(255,255,255,.18);color:#fff;border:1px solid rgba(255,255,255,.25);border-radius:20px;padding:5px 13px;font-size:11px;font-weight:700" onchange="window.__chq3._onCo(this.value)">
                  <option value="">Select Company</option>
                </select>
                <select id="c3-mo" class="c3-tbtn" style="cursor:pointer;outline:none;font-family:'JetBrains Mono',monospace;background:rgba(255,255,255,.18);color:#fff;border:1px solid rgba(255,255,255,.25);border-radius:20px;padding:5px 13px;font-size:11px;font-weight:700" onchange="window.__chq3._onMo(this.value)"></select>
                <button class="c3-tbtn" onclick="window.__chq3._exportExcel()">📊 Export Excel</button>
                <button class="c3-tbtn" onclick="window.__chq3.openThemePicker()">🎨 <span id="chq3-theme-lbl">⚖️ Professional</span></button>
                <span id="c3-ts" style="font-size:10px;opacity:.5"></span>
              </div>
            </div>
          </div>
          <div class="c3-content">
            <div class="c3-alerts" id="c3-alerts"></div>
            <div class="c3-tabs">${tabButtons}</div>
            ${panels}
          </div>
          <div class="c3-loader" id="c3-loader" style="display:none">
            <div class="c3-spinner"></div>
            <div style="font-weight:600;font-size:14px;color:#F1F5F9">Loading ComplianceHQ</div>
            <div style="font-size:12px;color:#94A3B8">Fetching all 11 compliance domains…</div>
          </div>
        </div>`;

        $(html).appendTo(main);
        this._populateCo();
        this._populateMo();
    }

    _populateCo() {
        const sel = document.getElementById('c3-co');
        if (!sel) return;
        
        frappe.db.get_list('Company', { filters: { is_group: 0 }, fields: ['name'], limit: 50 }).then(rows => {
            sel.innerHTML = '<option value="">Select Company</option>';
            if (rows && rows.length > 0) {
                rows.forEach(r => {
                    const o = document.createElement('option');
                    o.value = r.name;
                    o.text = r.name;
                    if (r.name === this.company) o.selected = true;
                    sel.appendChild(o);
                });
                if (!this.company) {
                    this.company = rows[0].name;
                    sel.value = this.company;
                    this.loadAll(false);
                }
            }
        }).catch(() => {
            // If no companies found, show message
            sel.innerHTML = '<option value="">No companies found</option>';
        });
    }

    _populateMo() {
        const sel = document.getElementById('c3-mo');
        if (!sel) return;
        const now = new Date();
        sel.innerHTML = '';
        for (let i = 0; i < 24; i++) {
            const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
            const val = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
            const o = document.createElement('option');
            o.value = val;
            o.text = d.toLocaleDateString('en-NG', { month: 'short', year: 'numeric' });
            if (val === this.fiscalMonth) o.selected = true;
            sel.appendChild(o);
        }
    }

    _onCo(v) {
        this.company = v;
        if (v) {
            this.loadAll(false);
        }
    }
    
    _onMo(v) {
        this.fiscalMonth = v;
        if (this.company) {
            this.loadAll(false);
        }
    }

    _actions() {
        this.page.add_inner_button('🔄 Refresh', () => this.loadAll(false));
        this.page.add_inner_button('⚡ Generate Liabilities', () => this._genLiabilities());
        this.page.add_inner_button('🔁 Reconcile CLL', () => this._reconcile());
        this.page.add_inner_button('📊 Download Excel Report', () => this._exportExcel());
        this.page.add_inner_button('📋 New Filing', () => frappe.new_doc('Compliance Filing'));
        this.page.add_inner_button('🎖 New License', () => frappe.new_doc('License Management'));
        this.page.add_menu_item('🏢 New Corporate Register', () => frappe.new_doc('Corporate Compliance Register'));
        this.page.add_menu_item('🔒 New Data Processing Record', () => frappe.new_doc('Data Processing Record'));
        this.page.add_menu_item('🕵️ New AML KYC Record', () => frappe.new_doc('AML KYC Record'));
        this.page.add_menu_item('🎨 Theme Picker', () => this.openThemePicker());
        this.page.add_menu_item('🖨️ Print', () => window.print());
    }

    _bind() {
        $(document).on('click', '.c3-tab', e => this._switchTab($(e.currentTarget).data('tab')));
    }

    _switchTab(name) {
        $('.c3-tab').removeClass('on');
        $(`.c3-tab[data-tab="${name}"]`).addClass('on');
        $('.c3-panel').removeClass('on');
        $(`#c3-p-${name}`).addClass('on');
        this.activeTab = name;
        if (Object.keys(this.data).length || Object.keys(this.v3data).length)
            this._render(name);
    }

    _clock() {
        const tick = () => {
            const clockEl = document.getElementById('c3-clock');
            if (clockEl) clockEl.textContent = new Date().toLocaleTimeString('en-NG', { hour12: true, hour: '2-digit', minute: '2-digit', second: '2-digit' });
            const dateEl = document.getElementById('c3-date');
            if (dateEl) dateEl.textContent = frappe.datetime.str_to_user(frappe.datetime.get_today());
        };
        tick();
        setInterval(tick, 1000);
    }

    // ── Data Load ─────────────────────────────────────────────────────────────
    async loadAll(silent = false) {
        if (!this.company) {
            $('#c3-loader').hide();
            const alertEl = document.getElementById('c3-alerts');
            if (alertEl) alertEl.innerHTML = '<div class="c3-alert ca-b">🏢 Please select a company from the dropdown above</div>';
            return;
        }
        if (!silent) $('#c3-loader').show();
        try {
            const [r1, r2, r3] = await Promise.all([
                frappe.call({ method: API + 'get_dashboard_summary',
                    args: { company: this.company, fiscal_month: this.fiscalMonth } }),
                frappe.call({ method: API + 'get_v3_domain_summary',
                    args: { company: this.company } }),
                frappe.call({ method: API + 'get_full_compliance_score',
                    args: { company: this.company } }),
            ]);
            this.data = r1.message || {};
            this.v3data = r2.message || {};
            this.scores = r3.message || {};
            this._updateBanner();
            this._buildAlerts();
            this._updateScoreRing();
            this._updateTabBadges();
            this._render(this.activeTab);
            const tsEl = document.getElementById('c3-ts');
            if (tsEl) tsEl.textContent = 'Updated ' + new Date().toLocaleTimeString('en-NG', { hour12: true });
        } catch (e) {
            console.error('ComplianceHQ v3 load error:', e);
            const alertEl = document.getElementById('c3-alerts');
            if (alertEl) alertEl.innerHTML = `<div class="c3-alert ca-r">❌ Failed to load compliance data: ${e.message || 'Unknown error'}</div>`;
            if (!silent) frappe.msgprint({ title: 'Load Error', indicator: 'red', message: 'Failed to load compliance data. Please check console for details.' });
        } finally {
            $('#c3-loader').hide();
        }
    }

    refresh(silent = false) { this.loadAll(silent); }

    _updateBanner() {
        const lic = this.data.licenses || {};
        const cal = this.data.calendar || {};
        const v3 = this.v3data;
        const total_issues = (lic.expired || 0) + (v3.corporate?.non_compliant || 0) + (v3.ndpr?.open_breaches || 0) + (v3.environmental?.expired || 0) + (v3.industry?.overdue || 0);
        const c1 = document.getElementById('c3-c1');
        const c2 = document.getElementById('c3-c2');
        if (c1) c1.textContent = `${total_issues} compliance issues · ${lic.expired || 0} expired licenses`;
        if (c2) c2.textContent = `${(v3.training?.mandatory_pct || 0).toFixed(0)}% training complete · ${cal.count || 0} obligations due`;
    }

    _updateScoreRing() {
        const s = this.scores.overall_v3 || 0;
        const ring = document.getElementById('c3-score-ring');
        const num = document.getElementById('c3-score-n');
        if (num) num.textContent = Math.round(s) + '%';
        if (ring) ring.style.borderColor = s >= 80 ? '#34d399' : s >= 60 ? '#fcd34d' : '#f87171';
    }

    _updateTabBadges() {
        const v3 = this.v3data;
        const tax = this.data.tax || {};
        const _b = (id, count) => {
            const el = document.getElementById(`c3-n-${id}`);
            if (el) {
                if (count > 0) {
                    el.textContent = count;
                    el.style.display = 'inline';
                } else {
                    el.style.display = 'none';
                }
            }
        };
        _b('statutory', ['VAT', 'WHT', 'PAYE'].filter(o => (tax[o] || {}).status === 'Overdue').length);
        _b('corporate', (v3.corporate?.non_compliant || 0) + (v3.corporate?.annual_return_overdue || 0));
        _b('contracts', (v3.contracts?.material_breach || 0) + (v3.contracts?.termination_risk || 0));
        _b('ndpr', (v3.ndpr?.open_breaches || 0));
        _b('aml', (v3.aml?.high_risk || 0) + (v3.aml?.sanctions_match || 0));
        _b('labour', (v3.labour?.expired_permits || 0));
        _b('environmental', (v3.environmental?.expired || 0));
        _b('industry', (v3.industry?.overdue || 0));
        _b('fraud', (v3.fraud?.under_investigation || 0) + (v3.fraud?.coi_pending_review || 0));
        _b('training', Math.max(0, 100 - (v3.training?.mandatory_pct || 100)) > 20 ? 1 : 0);
    }

    _buildAlerts() {
        const v3 = this.v3data, tax = this.data.tax || {}, lic = this.data.licenses || {};
        const alerts = [];
        const add = (cls, icon, text, tab) => alerts.push({ cls, icon, text, tab });
        if (lic.expired > 0) add('ca-r', '🎖', `${lic.expired} license${lic.expired > 1 ? 's' : ''} EXPIRED`, 'statutory');
        if ((tax.VAT || {}).status === 'Overdue') add('ca-r', '💼', `VAT ${this.fiscalMonth} OVERDUE`, 'statutory');
        if ((tax.PAYE || {}).status === 'Overdue') add('ca-r', '👤', `PAYE ${this.fiscalMonth} OVERDUE`, 'statutory');
        if (v3.corporate?.annual_return_overdue > 0) add('ca-r', '🏢', `${v3.corporate.annual_return_overdue} CAC return${v3.corporate.annual_return_overdue > 1 ? 's' : ''} OVERDUE`, 'corporate');
        if (v3.ndpr?.open_breaches > 0) add('ca-r', '🔒', `${v3.ndpr.open_breaches} open data breach${v3.ndpr.open_breaches > 1 ? 'es' : ''}`, 'ndpr');
        if (v3.aml?.sanctions_match > 0) add('ca-r', '⛔', `${v3.aml.sanctions_match} SANCTIONS MATCH — action required`, 'aml');
        if (v3.environmental?.expired > 0) add('ca-r', '🌿', `${v3.environmental.expired} environmental permit${v3.environmental.expired > 1 ? 's' : ''} EXPIRED`, 'environmental');
        if (v3.industry?.overdue > 0) add('ca-a', '🏭', `${v3.industry.overdue} regulatory return${v3.industry.overdue > 1 ? 's' : ''} OVERDUE`, 'industry');
        if (v3.contracts?.material_breach > 0) add('ca-a', '📄', `${v3.contracts.material_breach} contract material breach${v3.contracts.material_breach > 1 ? 'es' : ''}`, 'contracts');
        if (v3.fraud?.under_investigation > 0) add('ca-a', '🚨', `${v3.fraud.under_investigation} whistleblower report${v3.fraud.under_investigation > 1 ? 's' : ''} under investigation`, 'fraud');
        if (v3.ndpr?.dpia_missing > 0) add('ca-a', '📋', `${v3.ndpr.dpia_missing} DPIA${v3.ndpr.dpia_missing > 1 ? 's' : ''} missing`, 'ndpr');
        if (v3.aml?.strs_pending_nfiu > 0) add('ca-b', '📤', `${v3.aml.strs_pending_nfiu} STR${v3.aml.strs_pending_nfiu > 1 ? 's' : ''} pending NFIU`, 'aml');

        const alertEl = document.getElementById('c3-alerts');
        if (!alertEl) return;
        alertEl.innerHTML =
            alerts.length > 0 ?
            alerts.map(a => `<a class="c3-alert ${a.cls}" href="#" onclick="window.__chq3._switchTab('${a.tab}');return false">${a.icon} ${a.text}</a>`).join('') :
            '<div class="c3-alert ca-g">✅ No critical compliance alerts at this time</div>';
    }

    // ── Render dispatcher ─────────────────────────────────────────────────────
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
        };
        if (map[name]) map[name]();
    }

    // ── Helpers ───────────────────────────────────────────────────────────────
    F(v) {
        const n = parseFloat(v) || 0;
        if (n >= 1e9) return '₦' + (n / 1e9).toFixed(1) + 'B';
        if (n >= 1e6) return '₦' + (n / 1e6).toFixed(1) + 'M';
        if (n >= 1e3) return '₦' + (n / 1e3).toFixed(0) + 'k';
        return '₦' + Math.round(n).toLocaleString();
    }

    B(t, c) {
        return `<span class="c3-bdg ${c}">${t}</span>`;
    }

    SB(s) {
        const m = {
            'Compliant': 'bg-g', 'Non-Compliant': 'bg-r', 'Minor Issues': 'bg-a', 'Major Issues': 'bg-r',
            'Material Breach': 'bg-r', 'Termination Risk': 'bg-r', 'Minor Breach': 'bg-a',
            'Expired': 'bg-r', 'Active': 'bg-g', 'Expiring Soon': 'bg-a',
            'Open': 'bg-b', 'Closed': 'bg-gr', 'Overdue': 'bg-r',
            'Submitted': 'bg-g', 'Late Submitted': 'bg-a', 'Pending': 'bg-gr',
            'High': 'bg-r', 'Medium': 'bg-a', 'Low': 'bg-g', 'Critical': 'bg-r',
            'PEP — High': 'bg-v', 'Sanctioned — Blocked': 'bg-r',
            'Received': 'bg-b', 'Under Investigation': 'bg-a', 'Escalated': 'bg-r',
            'Satisfactory': 'bg-g', 'Not Generated': 'bg-gr',
            'Fully Paid': 'bg-g', 'Partially Paid': 'bg-a'
        };
        return this.B(s || '—', m[s] || 'bg-gr');
    }

    KPI(icon, label, val, sub, link, kc) {
        const onclick = link ? `onclick="frappe.set_route('${link}')"` : '';
        return `<div class="c3-kpi" style="--kc:${kc || 'var(--pri)'}" ${onclick}>
            ${icon ? `<div style="font-size:15px;margin-bottom:6px">${icon}</div>` : ''}
            <div class="kp">${label}</div>
            <div class="kv">${val || 0}</div>
            <div class="ks">${sub || ''}</div>
        </div>`;
    }

    DC(id) {
        if (this.charts[id]) {
            try { this.charts[id].destroy(); } catch (e) { }
            delete this.charts[id];
        }
    }

    MC(id, cfg) {
        this.DC(id);
        const el = document.getElementById(id);
        if (el) {
            try {
                const existing = Chart.getChart(id);
                if (existing) existing.destroy();
            } catch (e) { }
            this.charts[id] = new Chart(el, cfg);
        }
    }

    colors() {
        return ['#1E3A5F', '#059669', '#D97706', '#7C3AED', '#DC2626', '#0284C7', '#F97316', '#22C55E', '#EC4899', '#94A3B8'];
    }

    TBL(headers, rows, emptyMsg) {
        return `<div class="c3-tw"><table class="c3-tbl"><thead><tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.length ? rows.join('') : `<tr><td colspan="${headers.length}" class="c3-empty">${emptyMsg || 'No records found'}</td></tr>`}</tbody></table></div>`;
    }

    // ── OVERVIEW ──────────────────────────────────────────────────────────────
    _renderOverview() {
        const sc = this.scores.domain_scores || {}, v3 = this.v3data, tax = this.data.tax || {}, lic = this.data.licenses || {}, inc = this.data.incidents || {};
        const overall = this.scores.overall_v3 || 0;

        const domainCards = [
            { key: 'corporate', icon: '🏢', label: 'Governance', score: sc.corporate, issues: v3.corporate?.non_compliant || 0, tab: 'corporate' },
            { key: 'contracts', icon: '📄', label: 'Contracts', score: sc.contracts, issues: v3.contracts?.material_breach || 0, tab: 'contracts' },
            { key: 'ndpr', icon: '🔒', label: 'NDPR', score: sc.ndpr, issues: v3.ndpr?.open_breaches || 0, tab: 'ndpr' },
            { key: 'aml', icon: '🕵️', label: 'AML & KYC', score: sc.aml, issues: v3.aml?.high_risk || 0, tab: 'aml' },
            { key: 'labour', icon: '👷', label: 'Labour', score: sc.labour, issues: v3.labour?.expired_permits || 0, tab: 'labour' },
            { key: 'environmental', icon: '🌿', label: 'Environmental', score: sc.environmental, issues: v3.environmental?.expired || 0, tab: 'environmental' },
            { key: 'industry', icon: '🏭', label: 'Regulatory', score: sc.industry, issues: v3.industry?.overdue || 0, tab: 'industry' },
            { key: 'fraud', icon: '🚨', label: 'Integrity', score: sc.fraud, issues: v3.fraud?.under_investigation || 0, tab: 'fraud' },
            { key: 'training', icon: '🎓', label: 'Training', score: sc.training, issues: Math.max(0, 100 - (v3.training?.mandatory_pct || 100)) > 20 ? 1 : 0, tab: 'training' },
        ].map(d => {
            const s = d.score || 0, col = s >= 80 ? 'var(--grn)' : s >= 60 ? 'var(--amb)' : 'var(--red)';
            return `<div class="c3-ds" onclick="window.__chq3._switchTab('${d.tab}')">
                <div class="c3-ds-i">${d.icon}</div>
                <div class="c3-ds-n">${d.label}</div>
                <div class="c3-ds-v" style="color:${col}">${Math.round(s)}%</div>
                ${d.issues > 0 ? `<div style="font-size:9px;color:var(--red);font-weight:700;margin-top:2px">${d.issues} issue${d.issues > 1 ? 's' : ''}</div>` : '<div style="font-size:9px;color:var(--grn);margin-top:2px">✅ Clear</div>'}
                <div class="c3-ds-b"><div class="c3-ds-bf" style="width:${s}%;background:${col}"></div></div>
            </div>`;
        }).join('');

        const panel = document.getElementById('c3-p-overview');
        if (!panel) return;

        panel.innerHTML = `
            <div class="c3-card">
              <div class="c3-ch">
                <div class="c3-ct">📊 Compliance Health — All 11 Domains</div>
                <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
                  <div style="font-size:11px;color:var(--tx3)">Overall GRC Score</div>
                  <div style="font-size:22px;font-weight:900;color:${overall >= 80 ? 'var(--grn)' : overall >= 60 ? 'var(--amb)' : 'var(--red)'}">${Math.round(overall)}%</div>
                  <button class="c3-btn cb-g" onclick="window.__chq3._exportExcel()">📊 Export Report</button>
                </div>
              </div>
              <div class="c3-cb">
                <div style="height:8px;background:var(--brd);border-radius:10px;overflow:hidden;margin-bottom:14px">
                  <div style="height:100%;width:${overall}%;background:${overall >= 80 ? 'var(--grn)' : overall >= 60 ? 'var(--amb)' : 'var(--red)'};transition:width .8s"></div>
                </div>
                <div class="c3-dsg">${domainCards}</div>
              </div>
            </div>
            <div class="c3-kpis">
              ${this.KPI('💼', ((tax.VAT || {}).status || '—') === 'Not Generated' ? 'VAT: Not Generated' : 'VAT Status', (tax.VAT || {}).status || '—', '', '', (tax.VAT || {}).status === 'Fully Paid' ? 'var(--grn)' : 'var(--red)')}
              ${this.KPI('🎖', 'Expired Licenses', lic.expired || 0, 'need renewal', '', 'var(--red)')}
              ${this.KPI('⚠️', 'Open Incidents', inc.open || 0, 'active issues', '', 'var(--amb)')}
              ${this.KPI('🏢', 'CAC Returns Overdue', v3.corporate?.annual_return_overdue || 0, '', '', 'var(--red)')}
              ${this.KPI('🔒', 'Data Breaches Open', v3.ndpr?.open_breaches || 0, '', '', 'var(--red)')}
              ${this.KPI('🕵️', 'High-Risk KYC', v3.aml?.high_risk || 0, '', '', 'var(--amb)')}
              ${this.KPI('🌿', 'Env Permits Expired', v3.environmental?.expired || 0, '', '', 'var(--red)')}
              ${this.KPI('🎓', 'Mandatory Training', Math.round(v3.training?.mandatory_pct || 0) + '%', 'completion', '', (v3.training?.mandatory_pct || 0) >= 80 ? 'var(--grn)' : 'var(--amb)')}
            </div>
            <div class="c3-g2">
              <div class="c3-card">
                <div class="c3-ch"><div class="c3-ct">📊 Domain scores breakdown</div></div>
                <div class="c3-cb" style="height:220px"><canvas id="c3-ch-domains"></canvas></div>
              </div>
              <div class="c3-card">
                <div class="c3-ch"><div class="c3-ct">🚨 Incidents by type</div><button class="c3-btn cb-ghost" onclick="frappe.set_route('List','Compliance Incident')">All →</button></div>
                <div class="c3-cb" style="height:220px"><canvas id="c3-ch-incidents"></canvas></div>
              </div>
            </div>
        `;

        const ds = this.scores.domain_scores || {};
        this.MC('c3-ch-domains', {
            type: 'bar',
            data: {
                labels: ['Governance', 'Contracts', 'NDPR', 'AML', 'Labour', 'Environmental', 'Regulatory', 'Integrity', 'Training'],
                datasets: [{
                    data: [ds.corporate, ds.contracts, ds.ndpr, ds.aml, ds.labour, ds.environmental, ds.industry, ds.fraud, ds.training].map(v => Math.round(v || 0)),
                    backgroundColor: ['#1E3A5F', '#059669', '#D97706', '#7C3AED', '#DC2626', '#0284C7', '#F97316', '#22C55E', '#EC4899'],
                    borderRadius: 6,
                    barThickness: 28,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false }, ticks: { color: '#94A3B8', font: { size: 9 } } },
                    y: { max: 100, ticks: { color: '#94A3B8', font: { size: 9 }, callback: v => v + '%' }, grid: { color: 'rgba(148,163,184,.08)' } }
                }
            }
        });

        const by_type = (this.data.incidents || {}).by_type || [];
        this.MC('c3-ch-incidents', {
            type: 'doughnut',
            data: {
                labels: by_type.map(t => t.incident_type || 'Other'),
                datasets: [{ data: by_type.map(t => t.cnt), backgroundColor: this.colors(), borderWidth: 0 }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '60%',
                plugins: {
                    legend: { display: true, position: 'right', labels: { color: '#94A3B8', font: { size: 10 }, boxWidth: 10 } }
                }
            }
        });
    }

    // ── STATUTORY TAX ─────────────────────────────────────────────────────────
    _renderStatutory() {
        const tax = this.data.tax || {}, sta = this.data.statutory || {}, lic = this.data.licenses || {}, cal = this.data.calendar || {};
        const obCard = (ob, d) => {
            const liability = parseFloat(d?.liability || 0), paid = parseFloat(d?.paid || 0);
            const pct = liability > 0 ? Math.min(100, Math.round(paid / liability * 100)) : 0;
            const col = d?.status === 'Fully Paid' ? 'var(--grn)' : d?.status === 'Overdue' ? 'var(--red)' : d?.status === 'Partially Paid' ? 'var(--amb)' : 'var(--tx3)';
            return `<div class="c3-kpi" onclick="frappe.set_route('List','Compliance Liability Ledger',{obligation_type:'${ob}'})">
                <div class="kp">${ob}</div><div class="kv c3-mono">${this.F(liability)}</div>
                <div class="ks">Paid: ${this.F(paid)} · Bal: ${this.F(liability - paid)}</div>
                <div style="height:4px;background:var(--brd);border-radius:10px;overflow:hidden;margin:6px 0">
                  <div style="height:100%;width:${pct}%;background:${col};transition:width .7s"></div>
                </div>${this.SB(d?.status || 'Not Generated')}</div>`;
        };

        const panel = document.getElementById('c3-p-statutory');
        if (!panel) return;

        panel.innerHTML = `
            <div class="c3-g2">
              <div class="c3-card"><div class="c3-ch"><div class="c3-ct">💼 Tax obligations — ${this.fiscalMonth}</div>
                <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="c3-btn cb-solid" onclick="window.__chq3._genLiabilities()">⚡ Generate</button>
                <button class="c3-btn cb-g" onclick="window.__chq3._exportExcel()">📊 Export</button></div>
              </div><div class="c3-cb"><div class="c3-kpis" style="grid-template-columns:repeat(2,1fr)">
                ${obCard('VAT', tax.VAT)}${obCard('WHT', tax.WHT)}${obCard('PAYE', tax.PAYE)}${obCard('CIT', tax.CIT)}
              </div></div></div>
              <div class="c3-card"><div class="c3-ch"><div class="c3-ct">📋 Statutory obligations — ${this.fiscalMonth}</div>
                <button class="c3-btn cb-ghost" onclick="window.__chq3._reconcile()">🔁 Reconcile</button>
              </div><div class="c3-cb"><div class="c3-kpis" style="grid-template-columns:repeat(2,1fr)">
                ${obCard('Pension', sta.Pension)}${obCard('NHF', sta.NHF)}${obCard('NSITF', sta.NSITF)}${obCard('ITF', sta.ITF)}
              </div></div></div>
            </div>
            <div class="c3-g2">
              <div class="c3-card"><div class="c3-ch"><div class="c3-ct">🎖 License status</div><button class="c3-btn cb-ghost" onclick="frappe.set_route('List','License Management')">All →</button></div>
                <div class="c3-cb">
                  <div style="display:flex;gap:16px;margin-bottom:12px;flex-wrap:wrap">
                    ${[['✅', 'Valid', lic.valid || 0, 'var(--grn)'], ['⚠️', 'Expiring', lic.expiring || 0, 'var(--amb)'], ['🔴', 'Expired', lic.expired || 0, 'var(--red)']].map(([i, l, n, c]) =>
                      `<div style="text-align:center;flex:1;min-width:70px;padding:10px;background:var(--bg2);border-radius:10px">
                         <div>${i}</div><div style="font-size:18px;font-weight:800;color:${c}">${n}</div>
                         <div style="font-size:10px;color:var(--tx3)">${l}</div></div>`).join('')}
                  </div>
                  ${(lic.expiring_list || []).slice(0, 4).map(l => `
                  <div style="display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid var(--brd);cursor:pointer" onclick="frappe.set_route('Form','License Management','${l.name}')">
                    <div><div style="font-size:12px;font-weight:600;color:var(--tx1)">${l.license_name}</div>
                    <div style="font-size:10px;color:var(--tx3)">${l.license_type}</div></div>
                    ${this.B(l.days_to_expiry + 'd', l.days_to_expiry <= 7 ? 'bg-r' : l.days_to_expiry <= 30 ? 'bg-a' : 'bg-s')}
                  </div>`).join('')}
                </div>
              </div>
              <div class="c3-card"><div class="c3-ch"><div class="c3-ct">📅 Upcoming obligations</div></div>
                <div class="c3-cb">
                  ${(cal.upcoming || []).slice(0, 6).map(l => `
                  <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid var(--brd)">
                    <div><div style="font-size:12px;font-weight:600;color:var(--tx1)">${l.requirement_name || l.obligation_type}</div>
                    <div style="font-size:10px;color:var(--tx3)">${l.fiscal_month} · Due ${l.due_date}</div></div>
                    ${this.SB(l.status)}</div>`).join('') || '<div class="c3-empty">No upcoming obligations</div>'}
                </div>
              </div>
            </div>
        `;
    }

    // ── CORPORATE ─────────────────────────────────────────────────────────────
    _renderCorporate() {
        const d = this.v3data.corporate || {};
        const panel = document.getElementById('c3-p-corporate');
        if (!panel) return;

        frappe.call({ method: API + 'get_corporate_governance_tab', args: { company: this.company }, callback: r => {
            const data = r.message || {}, regs = data.registers || [], ress = data.pending_resolutions || [], entries = data.register_entries || [];
            panel.innerHTML = `
                <div class="c3-kpis">
                    ${this.KPI('🏢', 'Total Registers', d.total_registers || 0, 'fiscal years tracked', 'List/Corporate Compliance Register')}
                    ${this.KPI('🚨', 'Non-Compliant', d.non_compliant || 0, 'registers', '', 'var(--red)')}
                    ${this.KPI('📋', 'CAC Returns Overdue', d.annual_return_overdue || 0, 'immediate filing', '', 'var(--red)')}
                    ${this.KPI('📅', 'AGM Missed', d.agm_missed || 0, 'this fiscal year', '', 'var(--amb)')}
                    ${this.KPI('⚖️', 'CAC Filings Outstanding', d.cac_filings_outstanding || 0, 'board resolutions', '', 'var(--amb)')}
                    ${this.KPI('📝', 'Resolutions Pending', d.resolutions_pending || 0, 'implementation', '', 'var(--sky)')}
                </div>
                <div class="c3-g21"><div>
                    <div class="c3-card"><div class="c3-ch"><div class="c3-ct">🏢 Corporate Compliance Registers</div>
                        <button class="c3-btn cb-solid" onclick="frappe.new_doc('Corporate Compliance Register')">+ New</button></div>
                        ${this.TBL(['Company / FY', 'RC Number', 'CAC Return', 'AGM', 'Status'],
                            regs.map(r => `<tr onclick="frappe.set_route('Form','Corporate Compliance Register','${r.name}')">
                                <td><div style="font-weight:600;color:var(--tx1)">${r.company}</div><div style="font-size:10px;color:var(--tx3)">${r.fiscal_year}</div></td>
                                <td class="c3-mono" style="font-size:10px">${r.rc_number || '—'}</td>
                                <td>${this.SB(r.annual_return_status || '—')}</td>
                                <td style="color:${r.agm_held_on_time ? 'var(--grn)' : 'var(--red)'}">${r.agm_held_on_time ? '✅' : '❌'}</td>
                                <td>${this.SB(r.overall_status || '—')}</td></tr>`))}
                    </div>
                    <div class="c3-card"><div class="c3-ch"><div class="c3-ct">⚖️ Pending Board Resolutions</div>
                        <button class="c3-btn cb-solid" onclick="frappe.new_doc('Board Resolution')">+ New</button></div>
                        ${this.TBL(['Resolution', 'Meeting', 'CAC Required', 'Status'],
                            ress.map(r => `<tr onclick="frappe.set_route('Form','Board Resolution','${r.name}')">
                                <td style="font-weight:600;color:var(--tx1)">${r.resolution_number || r.name}</td>
                                <td style="font-size:10px">${r.meeting_type}<br><span style="color:var(--tx3)">${r.meeting_date}</span></td>
                                <td>${r.cac_filing_required ? (r.cac_filed ? this.B('Filed', 'bg-g') : this.B('OUTSTANDING', 'bg-r')) : this.B('N/A', 'bg-gr')}</td>
                                <td>${this.SB(r.implementation_status)}</td></tr>`))}
                    </div>
                </div><div>
                    <div class="c3-card"><div class="c3-ch"><div class="c3-ct">📖 Statutory Registers</div>
                        <button class="c3-btn cb-solid" onclick="frappe.new_doc('Statutory Register Entry')">+ Entry</button></div>
                        <div class="c3-cb">${entries.map(e => `
                            <div class="c3-bar-row" onclick="frappe.set_route('List','Statutory Register Entry',{register_type:'${e.register_type}'})" style="cursor:pointer">
                                <div class="c3-bar-lbl" style="font-size:10px">${e.register_type.replace('Register of ', '')}</div>
                                <div class="c3-bar"><div class="c3-bar-f" style="width:${e.count > 0 ? 100 : 0}%;background:var(--grn)"></div></div>
                                <div class="c3-bar-val">${e.count}</div></div>`).join('') || '<div class="c3-empty">No entries yet</div>'}
                        </div>
                    </div>
                </div></div>
            `;
        }});
    }

    // ── NDPR ──────────────────────────────────────────────────────────────────
    _renderNdpr() {
        const d = this.v3data.ndpr || {};
        const panel = document.getElementById('c3-p-ndpr');
        if (!panel) return;

        frappe.call({ method: API + 'get_ndpr_tab', args: { company: this.company }, callback: r => {
            const data = r.message || {}, breaches = data.open_breaches_detail || [], reviews = data.reviews_due_30_days || [];
            panel.innerHTML = `
                <div class="c3-kpis">
                    ${this.KPI('📋', 'Processing Records', d.processing_records || 0, 'active', 'List/Data Processing Record')}
                    ${this.KPI('🔒', 'Sensitive Data', d.sensitive_data_records || 0, 'require DPIA', '', 'var(--amb)')}
                    ${this.KPI('🚫', 'DPIAs Missing', d.dpia_missing || 0, 'for sensitive processing', '', 'var(--red)')}
                    ${this.KPI('🇳🇬', 'NITDA Registered', d.nitda_registered || 0, '', '', 'var(--grn)')}
                    ${this.KPI('🚨', 'Open Breaches', d.open_breaches || 0, 'incidents', '', 'var(--red)')}
                    ${this.KPI('⏰', 'Late Notifications', d.late_notifications || 0, '72h rule breached', '', 'var(--red)')}
                </div>
                <div class="c3-g21"><div>
                    <div class="c3-card"><div class="c3-ch"><div class="c3-ct">🚨 Open Data Breaches</div>
                        <button class="c3-btn cb-solid" onclick="frappe.new_doc('Data Breach Register')">+ Report</button></div>
                        ${this.TBL(['Breach', 'Severity', 'Subjects', 'NITDA', 'Late', 'Status'],
                            breaches.map(b => `<tr onclick="frappe.set_route('Form','Data Breach Register','${b.name}')">
                                <td style="font-weight:600;color:var(--tx1)">${b.breach_title}</td>
                                <td>${this.SB(b.severity)}</td>
                                <td class="c3-mono">${b.data_subjects_affected || '?'}</td>
                                <td style="color:${b.nitda_notified ? 'var(--grn)' : 'var(--red)'}">${b.nitda_notified ? '✅' : '❌'}</td>
                                <td>${b.late_notification_flag ? this.B('LATE', 'bg-r') : '—'}</td>
                                <td>${this.SB(b.status)}</td></tr>`),
                            'No open data breaches ✅')}
                    </div>
                    <div class="c3-card"><div class="c3-ch"><div class="c3-ct">📋 Reviews Due (30 days)</div>
                        <button class="c3-btn cb-solid" onclick="frappe.new_doc('Data Processing Record')">+ New</button></div>
                        ${this.TBL(['Activity', 'Legal Basis', 'Sensitive', 'DPIA', 'Review Due'],
                            reviews.map(rec => `<tr onclick="frappe.set_route('Form','Data Processing Record','${rec.name}')">
                                <td style="font-weight:600;color:var(--tx1)">${rec.processing_title}</td>
                                <td style="font-size:10px">${rec.legal_basis || '—'}</td>
                                <td>${rec.is_sensitive_data ? this.B('Sensitive', 'bg-a') : '—'}</td>
                                <td>${rec.privacy_impact_done ? this.B('Done', 'bg-g') : this.B('Missing', 'bg-r')}</td>
                                <td class="c3-mono" style="font-size:10px;color:var(--amb)">${rec.next_review_date || '—'}</td></tr>`),
                            'No reviews due ✅')}
                    </div>
                </div><div>
                    <div class="c3-card"><div class="c3-ch"><div class="c3-ct">📊 NDPR Summary</div></div>
                        <div class="c3-cb">
                            <div style="height:160px;position:relative;margin-bottom:14px"><canvas id="c3-ch-ndpr"></canvas></div>
                            ${[['Processing Records', d.processing_records, 'var(--pri)'], ['Sensitive Data', d.sensitive_data_records, 'var(--amb)'], ['DPIAs Done', (d.sensitive_data_records || 0) - (d.dpia_missing || 0), 'var(--grn)'], ['Open Breaches', d.open_breaches, 'var(--red)']].map(([l, v, c]) => `
                            <div class="c3-bar-row"><div class="c3-bar-lbl">${l}</div>
                            <div style="font-size:18px;font-weight:800;color:${c}">${v || 0}</div></div>`).join('')}
                        </div>
                    </div>
                </div></div>
            `;
            this.MC('c3-ch-ndpr', {
                type: 'doughnut',
                data: {
                    labels: ['Active', 'Sensitive', 'DPIA Done', 'Breaches'],
                    datasets: [{ data: [d.processing_records, d.sensitive_data_records, (d.sensitive_data_records || 0) - (d.dpia_missing || 0), d.open_breaches], backgroundColor: ['#1E3A5F', '#D97706', '#059669', '#DC2626'], borderWidth: 0 }]
                },
                options: { responsive: true, maintainAspectRatio: false, cutout: '60%', plugins: { legend: { display: false } } }
            });
        }});
    }

    // ── AML & KYC ─────────────────────────────────────────────────────────────
    _renderAml() {
        const d = this.v3data.aml || {};
        const panel = document.getElementById('c3-p-aml');
        if (!panel) return;

        frappe.call({ method: API + 'get_aml_tab', args: { company: this.company }, callback: r => {
            const data = r.message || {}, high = data.high_risk_parties || [], strs = data.pending_nfiu_strs || [];
            panel.innerHTML = `
                <div class="c3-kpis">
                    ${this.KPI('🆔', 'Total KYC Records', d.total_kyc || 0, '', 'List/AML KYC Record')}
                    ${this.KPI('🔴', 'High / PEP Risk', d.high_risk || 0, 'require EDD', '', 'var(--red)')}
                    ${this.KPI('🏛️', 'PEP Parties', d.pep_count || 0, 'politically exposed', '', 'var(--pur)')}
                    ${this.KPI('⛔', 'Sanctions Matches', d.sanctions_match || 0, 'IMMEDIATE action', '', 'var(--red)')}
                    ${this.KPI('⏰', 'KYC Expiring 30d', d.kyc_expiring_30d || 0, 'need renewal', '', 'var(--amb)')}
                    ${this.KPI('📤', 'STRs Pending NFIU', d.strs_pending_nfiu || 0, '', '', 'var(--amb)')}
                </div>
                ${d.sanctions_match > 0 ? `<div style="padding:12px 16px;background:var(--red_x);border:2px solid var(--red);border-radius:10px;margin-bottom:14px;font-size:13px;font-weight:700;color:var(--red)">⛔ SANCTIONS MATCH DETECTED — Do NOT proceed with any transaction. Contact AMLCO immediately.</div>` : ''}
                <div class="c3-g21"><div>
                    <div class="c3-card"><div class="c3-ch"><div class="c3-ct">🔴 High-Risk & PEP Parties</div>
                        <button class="c3-btn cb-solid" onclick="frappe.new_doc('AML KYC Record')">+ New KYC</button></div>
                        ${this.TBL(['Party', 'Type', 'Risk Rating', 'KYC Level', 'KYC Expiry', 'PEP', 'Sanction'],
                            high.map(p => `<tr onclick="frappe.set_route('Form','AML KYC Record','${p.name}')">
                                <td style="font-weight:600;color:var(--tx1)">${p.party_name_display}</td>
                                <td style="font-size:10px">${p.party_type}</td>
                                <td>${this.SB(p.risk_rating)}</td>
                                <td style="font-size:10px">${(p.kyc_level || '').replace('Enhanced Due Diligence', 'EDD').replace('Basic Customer Due Diligence', 'CDD')}</td>
                                <td class="c3-mono" style="font-size:10px;color:var(--amb)">${p.kyc_expiry_date || '—'}</td>
                                <td>${p.is_pep ? this.B('PEP', 'bg-v') : '—'}</td>
                                <td>${p.sanctions_match ? this.B('MATCH', 'bg-r') : '—'}</td></tr>`),
                            'No high-risk parties ✅')}
                    </div>
                    <div class="c3-card"><div class="c3-ch"><div class="c3-ct">🚨 STRs Pending NFIU</div>
                        <button class="c3-btn cb-solid" onclick="frappe.new_doc('Suspicious Transaction Report')">+ New STR</button></div>
                        ${this.TBL(['STR', 'Type', 'Date', 'Amount', 'Party', 'Status'],
                            strs.map(s => `<tr onclick="frappe.set_route('Form','Suspicious Transaction Report','${s.name}')">
                                <td style="font-weight:600;color:var(--tx1)">${s.str_title || s.name}</td>
                                <td style="font-size:10px">${s.report_type || '—'}</td>
                                <td class="c3-mono" style="font-size:10px">${s.transaction_date || '—'}</td>
                                <td class="c3-mono">${this.F(s.transaction_amount)}</td>
                                <td style="color:var(--tx2)">${s.party_name || 'Undisclosed'}</td>
                                <td>${this.SB(s.status)}</td></tr>`),
                            'No pending STRs ✅')}
                    </div>
                </div><div>
                    <div class="c3-card"><div class="c3-ch"><div class="c3-ct">📊 KYC Risk Distribution</div></div>
                        <div class="c3-cb" style="height:220px;position:relative"><canvas id="c3-ch-aml"></canvas></div>
                    </div>
                </div></div>
            `;
            const rdist = data.risk_distribution || [];
            this.MC('c3-ch-aml', {
                type: 'doughnut',
                data: {
                    labels: rdist.map(r => r.risk_rating),
                    datasets: [{
                        data: rdist.map(r => r.count),
                        backgroundColor: rdist.map(r => r.risk_rating.includes('High') || r.risk_rating.includes('Sanction') ? '#DC2626' : r.risk_rating.includes('PEP') ? '#7C3AED' : r.risk_rating === 'Medium' ? '#D97706' : '#059669'),
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '60%',
                    plugins: {
                        legend: { display: true, position: 'right', labels: { color: '#94A3B8', font: { size: 10 }, boxWidth: 10 } }
                    }
                }
            });
        }});
    }

    // ── LABOUR ────────────────────────────────────────────────────────────────
    _renderLabour() {
        const d = this.v3data.labour || {};
        const panel = document.getElementById('c3-p-labour');
        if (!panel) return;

        frappe.call({ method: API + 'get_labour_tab', args: { company: this.company }, callback: r => {
            const data = r.message || {}, permits = data.expiring_permits || [], trend = data.labour_trend || [];
            panel.innerHTML = `
                <div class="c3-kpis">
                    ${this.KPI('👷', 'Latest Status', d.latest_status || 'No Data', d.latest_period || '—', '', 'var(--pri)')}
                    ${this.KPI('💰', 'Min Wage Compliant', d.wage_compliant === null ? '—' : d.wage_compliant ? '✅ Yes' : '❌ No', '', '', 'var(--grn)')}
                    ${this.KPI('🏦', 'PenCom Registered', d.pencom_compliant === null ? '—' : d.pencom_compliant ? '✅ All' : '❌ Issues', '', '', 'var(--pri)')}
                    ${this.KPI('🛂', 'Total Permits', d.total_permits || 0, 'expatriate permits', 'List/Expatriate Permit Register')}
                    ${this.KPI('🔴', 'Expired Permits', d.expired_permits || 0, 'immediate renewal', '', 'var(--red)')}
                    ${this.KPI('⚠️', 'Expiring Permits', d.expiring_permits || 0, 'within 90 days', '', 'var(--amb)')}
                </div>
                <div class="c3-g21"><div>
                    <div class="c3-card"><div class="c3-ch"><div class="c3-ct">🛂 Expiring Permits (90 days)</div>
                        <button class="c3-btn cb-solid" onclick="frappe.new_doc('Expatriate Permit Register')">+ New</button></div>
                        ${this.TBL(['Permit', 'Employee', 'Type', 'Expiry', 'Days Left', 'Status'],
                            permits.map(p => `<tr onclick="frappe.set_route('Form','Expatriate Permit Register','${p.name}')">
                                <td style="font-weight:600;color:var(--tx1)">${p.permit_title || p.name}</td>
                                <td style="font-size:10px">${p.employee || '—'}</td>
                                <td style="font-size:10px">${p.permit_type || '—'}</td>
                                <td class="c3-mono" style="font-size:10px">${p.expiry_date || '—'}</td>
                                <td class="c3-mono" style="font-weight:700;color:${(p.days_to_expiry || 0) <= 30 ? 'var(--red)' : 'var(--amb)'}">${p.days_to_expiry != null ? p.days_to_expiry + 'd' : '—'}</td>
                                <td>${this.SB(p.status)}</td></tr>`),
                            'No permits expiring soon ✅')}
                    </div>
                    <div class="c3-card"><div class="c3-ch"><div class="c3-ct">📊 Labour Compliance Trend</div>
                        <button class="c3-btn cb-solid" onclick="frappe.new_doc('Labour Compliance Tracker')">+ New</button></div>
                        ${this.TBL(['Period', 'Status', 'Min Wage', 'Hours', 'PenCom'],
                            trend.map(t => `<tr>
                                <td class="c3-mono" style="font-weight:600">${t.period_label}</td>
                                <td>${this.SB(t.overall_status)}</td>
                                <td>${t.minimum_wage_compliant ? '✅' : '❌'}</td>
                                <td>${t.working_hours_compliant ? '✅' : '❌'}</td>
                                <td>${t.pencom_all_registered ? '✅' : '❌'}</td></tr>`))}
                    </div>
                </div><div>
                    <div class="c3-card"><div class="c3-ch"><div class="c3-ct">📈 Compliance Trend</div></div>
                        <div class="c3-cb" style="height:220px;position:relative"><canvas id="c3-ch-labour"></canvas></div>
                    </div>
                </div></div>
            `;
            const trendChart = trend.slice().reverse();
            const statusScore = s => s === 'Compliant' ? 100 : s === 'Minor Issues' ? 75 : s === 'Major Issues' ? 50 : 25;
            this.MC('c3-ch-labour', {
                type: 'line',
                data: {
                    labels: trendChart.map(t => t.period_label),
                    datasets: [{
                        label: 'Score',
                        data: trendChart.map(t => statusScore(t.overall_status)),
                        borderColor: '#059669',
                        backgroundColor: 'rgba(5,150,105,.1)',
                        fill: true,
                        tension: .4,
                        pointRadius: 4,
                        pointBackgroundColor: '#059669'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { display: false }, ticks: { color: '#94A3B8', font: { size: 9 } } },
                        y: { max: 100, ticks: { color: '#94A3B8', font: { size: 9 }, callback: v => v + '%' }, grid: { color: 'rgba(148,163,184,.08)' } }
                    }
                }
            });
        }});
    }

    // ── ENVIRONMENTAL ─────────────────────────────────────────────────────────
    _renderEnvironmental() {
        const d = this.v3data.environmental || {};
        const panel = document.getElementById('c3-p-environmental');
        if (!panel) return;

        frappe.call({ method: API + 'get_environmental_tab', args: { company: this.company }, callback: r => {
            const data = r.message || {}, expiring = data.expiring_90_days || [], byType = data.by_permit_type || [];
            panel.innerHTML = `
                <div class="c3-kpis">
                    ${this.KPI('🌿', 'Total Permits', d.total || 0, 'env & HSE', 'List/Environmental Compliance Record')}
                    ${this.KPI('✅', 'Active', d.active || 0, 'valid', '', 'var(--grn)')}
                    ${this.KPI('⚠️', 'Expiring Soon', d.expiring_soon || 0, 'alert period', '', 'var(--amb)')}
                    ${this.KPI('🔴', 'Expired', d.expired || 0, 'operating risk', '', 'var(--red)')}
                    ${this.KPI('📋', 'Actions Pending', d.pending_actions || 0, 'corrective actions', '', 'var(--amb)')}
                    ${this.KPI('🚨', 'Major Non-Compliance', d.major_non_compliance || 0, 'inspection findings', '', 'var(--red)')}
                </div>
                ${d.expired > 0 ? `<div style="padding:12px 16px;background:var(--red_x);border:2px solid var(--red);border-radius:10px;margin-bottom:14px;font-size:13px;font-weight:700;color:var(--red)">🚨 ${d.expired} environmental permit${d.expired > 1 ? 's have' : ' has'} EXPIRED.</div>` : ''}
                <div class="c3-g21"><div>
                    <div class="c3-card"><div class="c3-ch"><div class="c3-ct">🌿 Expiring within 90 Days</div>
                        <button class="c3-btn cb-solid" onclick="frappe.new_doc('Environmental Compliance Record')">+ New</button></div>
                        ${this.TBL(['Permit', 'Type', 'Authority', 'Expiry', 'Days Left', 'Status'],
                            expiring.map(e => `<tr onclick="frappe.set_route('Form','Environmental Compliance Record','${e.name}')">
                                <td style="font-weight:600;color:var(--tx1)">${e.permit_title}</td>
                                <td style="font-size:10px">${(e.permit_type || '').split('(')[0].trim()}</td>
                                <td style="font-size:10px">${e.issuing_authority || '—'}</td>
                                <td class="c3-mono" style="font-size:10px">${e.expiry_date || '—'}</td>
                                <td class="c3-mono" style="font-weight:700;color:${(e.days_to_expiry || 0) <= 30 ? 'var(--red)' : 'var(--amb)'}">${e.days_to_expiry != null ? e.days_to_expiry + 'd' : '—'}</td>
                                <td>${this.SB(e.status)}</td></tr>`),
                            'No permits expiring soon ✅')}
                    </div>
                </div><div>
                    <div class="c3-card"><div class="c3-ch"><div class="c3-ct">📊 Status breakdown</div></div>
                        <div class="c3-cb">
                            <div style="height:160px;position:relative;margin-bottom:14px"><canvas id="c3-ch-env"></canvas></div>
                            ${byType.map(t => `<div class="c3-bar-row">
                                <div class="c3-bar-lbl" style="font-size:9px">${t.permit_type.split('(')[0].trim()}</div>
                                <div class="c3-bar"><div class="c3-bar-f" style="width:${d.total > 0 ? Math.round(t.count / d.total * 100) : 0}%;background:${t.expired > 0 ? 'var(--red)' : 'var(--grn)'}"></div></div>
                                <div class="c3-bar-val">${t.count}</div></div>`).join('')}
                        </div>
                    </div>
                </div></div>
            `;
            this.MC('c3-ch-env', {
                type: 'doughnut',
                data: {
                    labels: ['Active', 'Expiring Soon', 'Expired'],
                    datasets: [{ data: [d.active, d.expiring_soon, d.expired], backgroundColor: ['#059669', '#D97706', '#DC2626'], borderWidth: 0 }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '60%',
                    plugins: {
                        legend: { display: true, position: 'bottom', labels: { color: '#94A3B8', font: { size: 9 }, boxWidth: 8 } }
                    }
                }
            });
        }});
    }

    // ── INDUSTRY REGULATORY ───────────────────────────────────────────────────
    _renderIndustry() {
        const d = this.v3data.industry || {};
        const panel = document.getElementById('c3-p-industry');
        if (!panel) return;

        frappe.call({ method: API + 'get_industry_tab', args: { company: this.company }, callback: r => {
            const data = r.message || {}, overdue = data.overdue_returns || [], byAuth = data.by_authority || [];
            panel.innerHTML = `
                <div class="c3-kpis">
                    ${this.KPI('🏭', 'Total Returns', d.total || 0, 'regulatory returns', 'List/Regulatory Return')}
                    ${this.KPI('🔴', 'Overdue', d.overdue || 0, 'immediate action', '', 'var(--red)')}
                    ${this.KPI('⚠️', 'Late', d.late || 0, 'with penalty', '', 'var(--amb)')}
                    ${this.KPI('⏳', 'Pending', d.pending || 0, 'not yet submitted', '', 'var(--sky)')}
                    ${this.KPI('✅', 'Submitted', d.submitted || 0, 'on time', '', 'var(--grn)')}
                    ${this.KPI('💰', 'Total Penalties', this.F(d.total_penalty || 0), 'incurred', '', 'var(--red)')}
                </div>
                <div class="c3-g21"><div>
                    <div class="c3-card"><div class="c3-ch"><div class="c3-ct">🏭 Overdue & Pending Returns</div>
                        <button class="c3-btn cb-solid" onclick="frappe.new_doc('Regulatory Return')">+ New</button></div>
                        ${this.TBL(['Return', 'Authority', 'Period', 'Due Date', 'Late', 'Penalty', 'Status'],
                            overdue.map(ret => `<tr onclick="frappe.set_route('Form','Regulatory Return','${ret.name}')">
                                <td style="font-weight:600;color:var(--tx1)">${ret.return_title || ret.name}</td>
                                <td style="font-size:10px">${ret.authority || '—'}</td>
                                <td style="font-size:10px;color:var(--tx3)">${ret.period_covered || '—'}</td>
                                <td class="c3-mono" style="font-size:10px;color:var(--red)">${ret.due_date || '—'}</td>
                                <td>${ret.late_flag ? this.B('LATE', 'bg-r') : '—'}</td>
                                <td class="c3-mono" style="color:var(--red)">${ret.penalty_for_non_filing ? this.F(ret.penalty_for_non_filing) : '—'}</td>
                                <td>${this.SB(ret.status)}</td></tr>`),
                            'No overdue returns ✅')}
                    </div>
                </div><div>
                    <div class="c3-card"><div class="c3-ch"><div class="c3-ct">📊 By Authority</div></div>
                        <div class="c3-cb">
                            ${byAuth.map(a => `<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--brd);cursor:pointer" onclick="frappe.set_route('List','Regulatory Return',{authority:'${a.authority}'})">
                                <div><div style="font-size:12px;font-weight:600;color:var(--tx1)">${a.authority}</div>
                                <div style="font-size:10px;color:var(--tx3)">${a.total} return${a.total > 1 ? 's' : ''}</div></div>
                                <div style="display:flex;gap:6px;flex-wrap:wrap">${a.overdue > 0 ? this.B(a.overdue + ' overdue', 'bg-r') : ''}${a.late > 0 ? this.B(a.late + ' late', 'bg-a') : ''}${a.overdue === 0 && a.late === 0 ? this.B('✅ On Track', 'bg-g') : ''}</div>
                            </div>`).join('') || '<div class="c3-empty">No returns yet</div>'}
                        </div>
                    </div>
                </div></div>
            `;
        }});
    }

    // ── FRAUD & INTEGRITY ─────────────────────────────────────────────────────
    _renderFraud() {
        const d = this.v3data.fraud || {};
        const panel = document.getElementById('c3-p-fraud');
        if (!panel) return;

        frappe.call({ method: API + 'get_fraud_tab', args: { company: this.company }, callback: r => {
            const data = r.message || {}, rpts = data.open_reports || [], coi = data.pending_coi_reviews || [], byCat = data.by_category || [];
            panel.innerHTML = `
                <div class="c3-kpis">
                    ${this.KPI('🔒', 'WB Reports', d.total_wb_reports || 0, 'total', 'List/Whistleblower Report')}
                    ${this.KPI('🔍', 'Under Investigation', d.under_investigation || 0, 'active', '', 'var(--amb)')}
                    ${this.KPI('📋', 'Escalated', d.escalated || 0, 'to board', '', 'var(--red)')}
                    ${this.KPI('✅', 'Substantiated', d.substantiated || 0, 'action taken', '', 'var(--grn)')}
                    ${this.KPI('📝', 'COI Declarations', d.total_coi || 0, 'total', 'List/Conflict of Interest Declaration')}
                    ${this.KPI('⚠️', 'COI Pending', d.coi_pending_review || 0, 'awaiting review', '', 'var(--amb)')}
                </div>
                <div class="c3-g21"><div>
                    <div class="c3-card"><div class="c3-ch"><div class="c3-ct">🔒 Open Whistleblower Reports</div>
                        <button class="c3-btn cb-solid" onclick="frappe.new_doc('Whistleblower Report')">+ Report</button></div>
                        ${this.TBL(['Code', 'Date', 'Category', 'Severity', 'Investigator', 'Status'],
                            rpts.map(rep => `<tr onclick="frappe.set_route('Form','Whistleblower Report','${rep.name}')">
                                <td class="c3-mono" style="font-weight:700;color:var(--pur)">${rep.report_code || rep.name}</td>
                                <td class="c3-mono" style="font-size:10px">${rep.received_date || '—'}</td>
                                <td style="font-size:10px">${rep.report_category || '—'}</td>
                                <td>${this.SB(rep.severity)}</td>
                                <td style="font-size:10px;color:var(--tx3)">${rep.assigned_investigator || 'Unassigned'}</td>
                                <td>${this.SB(rep.status)}</td></tr>`),
                            'No open reports ✅')}
                    </div>
                    <div class="c3-card"><div class="c3-ch"><div class="c3-ct">📝 COI Pending Review</div>
                        <button class="c3-btn cb-solid" onclick="frappe.new_doc('Conflict of Interest Declaration')">+ Declare</button></div>
                        ${this.TBL(['Employee', 'Type', 'Date', 'Conflict', 'Status'],
                            coi.map(c => `<tr onclick="frappe.set_route('Form','Conflict of Interest Declaration','${c.name}')">
                                <td style="font-weight:600;color:var(--tx1)">${c.employee}</td>
                                <td style="font-size:10px">${c.declaration_type}</td>
                                <td class="c3-mono" style="font-size:10px">${c.declaration_date}</td>
                                <td>${c.has_conflict ? this.B('DECLARED', 'bg-r') : this.B('None', 'bg-g')}</td>
                                <td>${this.SB(c.approval_status)}</td></tr>`),
                            'No pending COI reviews ✅')}
                    </div>
                </div><div>
                    <div class="c3-card"><div class="c3-ch"><div class="c3-ct">📊 Reports by Category</div></div>
                        <div class="c3-cb">
                            <div style="height:160px;position:relative;margin-bottom:14px"><canvas id="c3-ch-fraud"></canvas></div>
                            ${byCat.map(c => `<div class="c3-bar-row">
                                <div class="c3-bar-lbl" style="font-size:10px">${c.report_category}</div>
                                <div class="c3-bar"><div class="c3-bar-f" style="width:${d.total_wb_reports > 0 ? Math.round(c.count / d.total_wb_reports * 100) : 0}%;background:${c.open > 0 ? 'var(--red)' : 'var(--grn)'}"></div></div>
                                <div class="c3-bar-val">${c.count}</div></div>`).join('')}
                        </div>
                    </div>
                </div></div>
            `;
            this.MC('c3-ch-fraud', {
                type: 'doughnut',
                data: {
                    labels: byCat.map(c => c.report_category),
                    datasets: [{ data: byCat.map(c => c.count), backgroundColor: this.colors(), borderWidth: 0 }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '55%',
                    plugins: { legend: { display: false } }
                }
            });
        }});
    }

    // ── TRAINING ──────────────────────────────────────────────────────────────
    _renderTraining() {
        const d = this.v3data.training || {};
        const panel = document.getElementById('c3-p-training');
        if (!panel) return;

        frappe.call({ method: API + 'get_training_tab', args: { company: this.company }, callback: r => {
            const data = r.message || {}, byCat = data.by_category || [], upcoming = data.upcoming_sessions || [], overdue = data.overdue_employees || [];
            panel.innerHTML = `
                <div class="c3-kpis">
                    ${this.KPI('🎓', 'Total Records', d.total_records || 0, 'all employees', 'List/Compliance Training Record')}
                    ${this.KPI('📊', 'Mandatory Completion', Math.round(d.mandatory_pct || 0) + '%', d.mandatory_completed + ' / ' + d.mandatory_total, '', 'var(--grn)')}
                    ${this.KPI('❌', 'Failed', d.failed || 0, 'need retraining', '', 'var(--red)')}
                    ${this.KPI('👥', 'Employees Trained', d.unique_employees || 0, 'unique', '', 'var(--sky)')}
                    ${this.KPI('📅', 'Upcoming Sessions', d.upcoming_sessions || 0, 'planned', 'List/Compliance Training Calendar')}
                </div>
                <div class="c3-card"><div class="c3-ch"><div class="c3-ct">📊 Mandatory Completion by Category</div>
                    <button class="c3-btn cb-solid" onclick="frappe.new_doc('Compliance Training Calendar')">+ Schedule</button></div>
                    <div class="c3-cb">
                        ${byCat.map(cat => {
                            const pct = cat.mandatory > 0 ? Math.round(cat.completed / cat.mandatory * 100) : 100;
                            const col = pct >= 80 ? 'var(--grn)' : pct >= 60 ? 'var(--amb)' : 'var(--red)';
                            return `<div class="c3-bar-row" onclick="frappe.set_route('List','Compliance Training Record',{training_category:'${cat.training_category}'})" style="cursor:pointer">
                                <div class="c3-bar-lbl">${cat.training_category}</div>
                                <div class="c3-bar"><div class="c3-bar-f" style="width:${pct}%;background:${col}"></div></div>
                                <div class="c3-bar-val" style="color:${col}">${pct}%</div>
                                <div style="font-size:9px;color:var(--tx3);margin-left:4px">${cat.completed}/${cat.mandatory}</div>
                                ${cat.failed > 0 ? `<div style="font-size:9px;color:var(--red);margin-left:4px">${cat.failed}❌</div>` : ''}
                            </div>`;
                        }).join('') || '<div class="c3-empty">No training records yet</div>'}
                    </div>
                </div>
                <div class="c3-g2">
                    <div class="c3-card"><div class="c3-ch"><div class="c3-ct">📅 Upcoming Sessions</div></div>
                        ${this.TBL(['Title', 'Category', 'Date', 'Mandatory', 'Status'],
                            upcoming.map(s => `<tr onclick="frappe.set_route('Form','Compliance Training Calendar','${s.name}')">
                                <td style="font-weight:600;color:var(--tx1)">${s.calendar_title || s.name}</td>
                                <td style="font-size:10px">${s.training_category}</td>
                                <td class="c3-mono" style="font-size:10px">${s.scheduled_date}</td>
                                <td>${s.is_mandatory ? this.B('Mandatory', 'bg-r') : this.B('Optional', 'bg-gr')}</td>
                                <td>${this.SB(s.status)}</td></tr>`),
                            'No upcoming sessions')}
                    </div>
                    <div class="c3-card"><div class="c3-ch"><div class="c3-ct">⚠️ Overdue / Failed Employees</div></div>
                        ${this.TBL(['Employee', 'Dept', 'Category', 'Cert Expiry', 'Status'],
                            overdue.map(e => `<tr>
                                <td style="font-weight:600;color:var(--tx1)">${e.employee_name}</td>
                                <td style="font-size:10px">${e.department || '—'}</td>
                                <td style="font-size:10px">${e.training_category}</td>
                                <td class="c3-mono" style="font-size:10px;color:var(--red)">${e.certificate_expiry || '—'}</td>
                                <td>${this.SB(e.completion_status)}</td></tr>`),
                            'No overdue employees ✅')}
                    </div>
                </div>
            `;
        }});
    }

    // ── CONTRACTS ─────────────────────────────────────────────────────────────
    _renderContracts() {
        const d = this.v3data.contracts || {};
        const panel = document.getElementById('c3-p-contracts');
        if (!panel) return;

        frappe.call({ method: API + 'get_contracts_tab', args: { company: this.company }, callback: r => {
            const data = r.message || {}, records = data.records || [], expiring = data.expiring_60_days || [];
            panel.innerHTML = `
                <div class="c3-kpis">
                    ${this.KPI('📄', 'Total Contracts', d.total || 0, 'monitored', 'List/Contract Compliance Record')}
                    ${this.KPI('✅', 'Compliant', d.compliant || 0, 'all obligations met', '', 'var(--grn)')}
                    ${this.KPI('⚠️', 'Minor Breach', d.minor_breach || 0, 'resolve soon', '', 'var(--amb)')}
                    ${this.KPI('🔴', 'Material Breach', d.material_breach || 0, 'legal review', '', 'var(--red)')}
                    ${this.KPI('🚨', 'Termination Risk', d.termination_risk || 0, 'urgent', '', 'var(--red)')}
                    ${this.KPI('📊', 'Avg SLA', Math.round(d.avg_sla || 0) + '%', 'across all', '', 'var(--sky)')}
                </div>
                <div class="c3-g21"><div>
                    <div class="c3-card"><div class="c3-ch"><div class="c3-ct">📄 All Contract Records</div>
                        <button class="c3-btn cb-solid" onclick="frappe.new_doc('Contract Compliance Record')">+ New</button></div>
                        ${this.TBL(['Contract', 'Vendor', 'SLA %', 'Breaches', 'End Date', 'Status'],
                            records.slice(0, 15).map(c => `<tr onclick="frappe.set_route('Form','Contract Compliance Record','${c.name}')">
                                <td style="font-weight:600;color:var(--tx1)">${c.compliance_title || c.name}</td>
                                <td style="font-size:10px">${c.vendor || '—'}</td>
                                <td class="c3-mono" style="color:${(c.sla_compliance_pct || 0) >= 95 ? 'var(--grn)' : (c.sla_compliance_pct || 0) >= 80 ? 'var(--amb)' : 'var(--red)'}">${Math.round(c.sla_compliance_pct || 0)}%</td>
                                <td class="c3-mono" style="color:${(c.open_breaches || 0) > 0 ? 'var(--red)' : 'var(--grn)'}">${c.open_breaches || 0}</td>
                                <td class="c3-mono" style="font-size:10px">${c.contract_end || '—'}</td>
                                <td>${this.SB(c.compliance_status)}</td></tr>`))}
                    </div>
                </div><div>
                    <div class="c3-card"><div class="c3-ch"><div class="c3-ct">📅 Expiring in 60 Days</div></div>
                        <div class="c3-cb">
                            ${expiring.map(c => `<div style="padding:9px 0;border-bottom:1px solid var(--brd);cursor:pointer" onclick="frappe.set_route('Form','Contract Compliance Record','${c.name}')">
                                <div style="display:flex;justify-content:space-between">
                                    <div style="font-size:12px;font-weight:600;color:var(--tx1)">${c.compliance_title}</div>
                                    ${this.SB(c.compliance_status)}
                                </div>
                                <div style="font-size:10px;color:var(--tx3);margin-top:2px">${c.vendor || '—'} · Ends ${c.contract_end} · ${this.F(c.contract_value || 0)}</div>
                            </div>`).join('') || '<div class="c3-empty">No contracts expiring soon ✅</div>'}
                        </div>
                    </div>
                </div></div>
            `;
        }});
    }

    // ── AI ANALYSIS ───────────────────────────────────────────────────────────
    _renderAI() {
        const sc = this.scores, ds = sc.domain_scores || {}, overall = sc.overall_v3 || 0;
        const domainBars = Object.entries(ds).map(([k, v]) => {
            const icons = { corporate: '🏢', contracts: '📄', ndpr: '🔒', aml: '🕵️', labour: '👷', environmental: '🌿', industry: '🏭', fraud: '🚨', training: '🎓' };
            const labels = { corporate: 'Governance', contracts: 'Contracts', ndpr: 'NDPR', aml: 'AML', labour: 'Labour', environmental: 'Environmental', industry: 'Regulatory', fraud: 'Integrity', training: 'Training' };
            const score = Math.round(v || 0), col = score >= 80 ? 'var(--grn)' : score >= 60 ? 'var(--amb)' : 'var(--red)';
            return `<div class="c3-bar-row"><div class="c3-bar-lbl">${icons[k] || ''} ${labels[k] || k}</div>
                <div class="c3-bar"><div class="c3-bar-f" style="width:${score}%;background:${col}"></div></div>
                <div class="c3-bar-val" style="color:${col}">${score}%</div></div>`;
        }).join('');

        const panel = document.getElementById('c3-p-ai');
        if (!panel) return;
        panel.innerHTML = `
            <div class="c3-g2">
                <div class="c3-card"><div class="c3-ch"><div class="c3-ct">📊 GRC Score — All 11 Domains</div></div>
                    <div class="c3-cb">
                        <div style="display:flex;align-items:center;gap:14px;margin-bottom:18px;flex-wrap:wrap">
                            <div style="width:76px;height:76px;border-radius:50%;border:5px solid ${overall >= 80 ? 'var(--grn)' : overall >= 60 ? 'var(--amb)' : 'var(--red)'};display:flex;flex-direction:column;align-items:center;justify-content:center;flex-shrink:0">
                                <div style="font-size:20px;font-weight:900;color:${overall >= 80 ? 'var(--grn)' : overall >= 60 ? 'var(--amb)' : 'var(--red)'}">${Math.round(overall)}</div>
                                <div style="font-size:9px;color:var(--tx3)">/ 100</div>
                            </div>
                            <div style="flex:1;min-width:150px">
                                <div style="height:9px;background:var(--brd);border-radius:10px;overflow:hidden;margin-bottom:7px">
                                    <div style="height:100%;width:${overall}%;background:${overall >= 80 ? 'var(--grn)' : overall >= 60 ? 'var(--amb)' : 'var(--red)'};transition:width .8s"></div>
                                </div>
                                <div style="font-size:11px;color:var(--tx3)">Weighted GRC score across all 11 compliance domains</div>
                            </div>
                        </div>
                        ${domainBars}
                    </div>
                </div>
                <div class="c3-card"><div class="c3-ch"><div class="c3-ct">🤖 AI Compliance Analyst</div><span id="c3-ai-status" style="font-size:10px;color:var(--tx3)">Ready</span></div>
                    <div class="c3-cb">
                        <div style="display:flex;flex-direction:column;gap:8px;margin-bottom:14px">
                            <button class="c3-btn cb-solid" id="c3-ai-btn" onclick="window.__chq3._runAI()" style="justify-content:center">✨ Run Full AI GRC Analysis</button>
                            <button class="c3-btn cb-g" onclick="window.__chq3._exportExcel()" style="justify-content:center">📊 Download Excel Report</button>
                            <button class="c3-btn cb-ghost" onclick="window.__chq3._genLiabilities()" style="justify-content:center">⚡ Generate Liabilities</button>
                            <button class="c3-btn cb-ghost" onclick="window.__chq3._reconcile()" style="justify-content:center">🔁 Reconcile CLL</button>
                        </div>
                        <div id="c3-ai-out">
                            <div style="padding:14px;background:var(--bg2);border-radius:10px;font-size:12px;color:var(--tx2);line-height:1.6">
                                Click <b>Run Full AI GRC Analysis</b> to send live data from all 11 compliance domains to the Anthropic API for risk assessment, penalty estimation, and a prioritised action plan.
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    async _runAI() {
        if (!this.company) {
            frappe.msgprint('Please select a company first.');
            return;
        }
        const btn = document.getElementById('c3-ai-btn');
        const out = document.getElementById('c3-ai-out');
        const stat = document.getElementById('c3-ai-status');
        if (btn) { btn.textContent = '⟳ Analysing…'; btn.disabled = true; }
        if (stat) stat.textContent = 'Calling AI…';
        if (out) out.innerHTML = `<div style="text-align:center;padding:24px;color:var(--tx3)"><span class="c3-spin" style="font-size:24px">⟳</span><br><div style="margin-top:8px;font-size:12px">Sending all domain data to Anthropic…</div></div>`;
        try {
            const r = await frappe.call({
                method: API + 'get_ai_compliance_analysis',
                args: { company: this.company, fiscal_month: this.fiscalMonth }
            });
            if (r.message?.success) {
                let parsed = {};
                try {
                    const raw = r.message.analysis?.response || r.message.analysis || '';
                    const match = (typeof raw === 'string' ? raw : JSON.stringify(raw)).match(/\{[\s\S]*\}/);
                    if (match) parsed = JSON.parse(match[0]);
                } catch (e) {
                    parsed = { summary: String(r.message.analysis || '').substring(0, 800) };
                }
                const riskCol = { Critical: 'var(--red)', High: 'var(--amb)', Medium: 'var(--sky)', Low: 'var(--grn)' }[parsed.risk_level] || 'var(--tx2)';
                const actsHTML = (parsed.actions || []).map((a, i) => `
                    <div style="display:flex;align-items:flex-start;gap:9px;padding:9px 11px;background:var(--bg2);border-radius:8px;margin-bottom:7px">
                        <div style="background:${riskCol};color:#fff;font-size:10px;font-weight:800;width:20px;height:20px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0">${i + 1}</div>
                        <div><div style="font-size:12px;font-weight:700;color:var(--tx1)">${a.action || ''}</div>
                        <div style="font-size:10px;color:var(--tx3);margin-top:2px">Deadline: ${a.deadline || '—'} · Authority: ${a.authority || '—'}</div></div>
                    </div>`).join('');
                if (out) out.innerHTML = `
                    <div style="padding:13px;background:${riskCol === 'var(--red)' ? 'var(--red_x)' : 'var(--pri_x)'};border-left:4px solid ${riskCol};border-radius:8px;margin-bottom:13px">
                        <div style="font-size:14px;font-weight:700;color:var(--tx1)">${parsed.risk_level ? `[${parsed.risk_level} Risk] ` : ''}${parsed.summary || 'AI analysis complete'}</div>
                        ${parsed.penalty_exposure ? `<div style="font-size:12px;color:var(--red);margin-top:4px;font-weight:700">Penalty exposure: ${parsed.penalty_exposure}</div>` : ''}
                    </div>
                    ${actsHTML ? `<div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--tx3);margin-bottom:8px">Priority Actions</div>${actsHTML}` : ''}
                    ${parsed.strategic_recommendation ? `<div style="padding:11px;background:var(--grn_x);border-radius:8px;font-size:12px;color:var(--tx1);border-left:3px solid var(--grn)"><b>Strategic Recommendation:</b> ${parsed.strategic_recommendation}</div>` : ''}
                    <div style="font-size:10px;color:var(--tx3);margin-top:10px">Analysis at ${new Date().toLocaleTimeString('en-NG', { hour12: true })}</div>`;
                if (stat) stat.textContent = 'Done';
            } else {
                if (out) out.innerHTML = `<div style="padding:13px;background:var(--red_x);border-radius:8px;font-size:12px;color:var(--red)">AI analysis failed: ${r.message?.error || 'Unknown error'}</div>`;
            }
        } catch (e) {
            if (out) out.innerHTML = `<div style="padding:13px;background:var(--red_x);border-radius:8px;font-size:12px;color:var(--red)">Error: ${e.message}</div>`;
        }
        if (btn) { btn.textContent = '✨ Run Full AI GRC Analysis'; btn.disabled = false; }
    }

    // ── EXPORT EXCEL ──────────────────────────────────────────────────────────
    _exportExcel() {
        if (!this.company) {
            frappe.msgprint('Please select a company first.');
            return;
        }
        frappe.show_alert({ message: '📊 Generating Excel report…', indicator: 'blue' });
        frappe.call({
            method: API + 'export_compliance_report',
            args: { company: this.company, fiscal_month: this.fiscalMonth, format: 'xlsx' },
            freeze: true,
            freeze_message: 'Generating compliance report…',
            callback: r => {
                if (r.message?.success) {
                    const link = document.createElement('a');
                    link.href = 'data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,' + r.message.file_data;
                    link.download = r.message.file_name;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    frappe.show_alert({ message: `📊 ${r.message.file_name} downloaded ✅`, indicator: 'green' });
                } else {
                    frappe.show_alert({ message: '❌ Export failed: ' + (r.message?.error || 'Unknown error'), indicator: 'red' });
                }
            }
        });
    }

    // ── UTILITY ACTIONS ───────────────────────────────────────────────────────
    _genLiabilities() {
        if (!this.company) {
            frappe.msgprint('Please select a company first.');
            return;
        }
        frappe.call({
            method: API + 'run_liability_generation_now',
            args: { company: this.company, fiscal_month: this.fiscalMonth },
            freeze: true,
            freeze_message: 'Generating liabilities…',
            callback: () => {
                frappe.show_alert({ message: 'Liability generation complete ✅', indicator: 'green' });
                this.loadAll(true);
            }
        });
    }

    _reconcile() {
        if (!this.company) {
            frappe.msgprint('Please select a company first.');
            return;
        }
        frappe.call({
            method: API + 'run_reconciliation_now',
            args: { company: this.company },
            freeze: true,
            freeze_message: 'Reconciling CLL entries…',
            callback: r => {
                frappe.show_alert({ message: `Reconciled ${(r.message || {}).reconciled || 0} CLL entries ✅`, indicator: 'green' });
                this.loadAll(true);
            }
        });
    }
}

// ── Module helpers ────────────────────────────────────────────────────────────
function _lsGet(k, def) { try { return localStorage.getItem(k) || def; } catch (e) { return def; } }
function _lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { } }
function _curMonth() { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`; }