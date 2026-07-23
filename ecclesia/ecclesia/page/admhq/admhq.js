// Copyright (c) 2026, Value Impacts Consulting
// ecclesia/ecclesia/page/admhq/admhq.js
//
// ╔══════════════════════════════════════════════════════════════════════════════╗
// ║  AdminHQ — Ecclesia Administrative Command Centre                           ║
// ║  9 Themes · 11 Tabs · Full CRUD · Chart.js · AI Insights · Messaging       ║
// ║  Tabs: Overview · Requests · Fleet · Facilities · Utilities · Security      ║
// ║        Contracts · Compliance · HSE · Messaging · AI Intelligence           ║
// ║                                                                              ║
// ║  Admin Spend Breakdown sources (real DocTypes):                              ║
// ║    Utilities   → Utility Consumption (total_bill SUM) + Generator Log       ║
// ║    Fleet       → Fuel Issue (total_cost SUM) + Maintenance Work Order       ║
// ║    Maintenance → Maintenance Work Order (actual_cost SUM)                   ║
// ║    Contracts   → Service Contract (contract_value/12 × active count)        ║
// ║    Admin Requests → Administrative Request (actual_cost SUM, completed)     ║
// ╚══════════════════════════════════════════════════════════════════════════════╝

frappe.pages['admhq'] = frappe.pages['admhq'] || {};
frappe.pages['admhq'].on_page_load = function (wrapper) {
    const boot = () => new AdminHQ(wrapper);
    if (typeof Chart === 'undefined') {
        const s = document.createElement('script');
        s.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
        s.onload = boot;
        s.onerror = () => frappe.msgprint({ title: 'Chart.js Error', indicator: 'red', message: 'Failed to load Chart.js.' });
        document.head.appendChild(s);
    } else { boot(); }
};
frappe.pages['admhq'].on_page_show = function (wrapper) {
    if (window.__admhq) window.__admhq.loadData(true);
};

// ═══════════════════════════════════════════════════════════════════════════════
//  THEME REGISTRY
// ═══════════════════════════════════════════════════════════════════════════════
const HQ_THEMES = {
    steel:    { name:'Steel',    icon:'🔩', dark:false, pri:'#0284C7',pri_d:'#0369A1',pri_x:'rgba(2,132,199,.09)',acc:'#38BDF8',red:'#EF4444',red_x:'rgba(239,68,68,.09)',amb:'#F59E0B',amb_x:'rgba(245,158,11,.09)',grn:'#10B981',grn_x:'rgba(16,185,129,.09)',sky:'#06B6D4',sky_x:'rgba(6,182,212,.09)',pur:'#8B5CF6',pur_x:'rgba(139,92,246,.09)',bg:'#F8FAFC',bg2:'#F1F5F9',bg3:'#E2E8F0',card:'#FFFFFF',brd:'#E2E8F0',brd2:'#CBD5E1',tx1:'#0F172A',tx2:'#475569',tx3:'#94A3B8',banner:'linear-gradient(135deg,#0F172A 0%,#1E3A5F 40%,#0284C7 75%,#06B6D4 100%)' },
    midnight: { name:'Midnight', icon:'🌙', dark:true,  pri:'#818CF8',pri_d:'#6366F1',pri_x:'rgba(129,140,248,.12)',acc:'#A5B4FC',red:'#F87171',red_x:'rgba(248,113,113,.12)',amb:'#FCD34D',amb_x:'rgba(252,211,77,.12)',grn:'#34D399',grn_x:'rgba(52,211,153,.12)',sky:'#38BDF8',sky_x:'rgba(56,189,248,.12)',pur:'#C084FC',pur_x:'rgba(192,132,252,.12)',bg:'#0F172A',bg2:'#1E293B',bg3:'#334155',card:'#1E293B',brd:'rgba(255,255,255,.08)',brd2:'rgba(255,255,255,.14)',tx1:'#F1F5F9',tx2:'#94A3B8',tx3:'#475569',banner:'linear-gradient(135deg,#020617 0%,#0F172A 50%,#1E3A5F 70%,#312E81 100%)' },
    verdant:  { name:'Verdant',  icon:'🌿', dark:false, pri:'#059669',pri_d:'#047857',pri_x:'rgba(5,150,105,.09)',acc:'#34D399',red:'#EF4444',red_x:'rgba(239,68,68,.09)',amb:'#F59E0B',amb_x:'rgba(245,158,11,.09)',grn:'#10B981',grn_x:'rgba(16,185,129,.09)',sky:'#0EA5E9',sky_x:'rgba(14,165,233,.09)',pur:'#8B5CF6',pur_x:'rgba(139,92,246,.09)',bg:'#ECFDF5',bg2:'#D1FAE5',bg3:'#A7F3D0',card:'#FFFFFF',brd:'#A7F3D0',brd2:'#6EE7B7',tx1:'#022C22',tx2:'#065F46',tx3:'#6EE7B7',banner:'linear-gradient(135deg,#022C22 0%,#047857 40%,#059669 70%,#10B981 100%)' },
    ember:    { name:'Ember',    icon:'🔥', dark:false, pri:'#F97316',pri_d:'#EA580C',pri_x:'rgba(249,115,22,.09)',acc:'#FB923C',red:'#EF4444',red_x:'rgba(239,68,68,.09)',amb:'#EAB308',amb_x:'rgba(234,179,8,.09)',grn:'#22C55E',grn_x:'rgba(34,197,94,.09)',sky:'#0EA5E9',sky_x:'rgba(14,165,233,.09)',pur:'#A855F7',pur_x:'rgba(168,85,247,.09)',bg:'#FFF7ED',bg2:'#FFEDD5',bg3:'#FED7AA',card:'#FFFFFF',brd:'#FED7AA',brd2:'#FDBA74',tx1:'#431407',tx2:'#9A3412',tx3:'#FDBA74',banner:'linear-gradient(135deg,#431407 0%,#C2410C 40%,#F97316 70%,#EAB308 100%)' },
    nova:     { name:'Nova',     icon:'🌟', dark:false, pri:'#7C3AED',pri_d:'#6D28D9',pri_x:'rgba(124,58,237,.09)',acc:'#A78BFA',red:'#EF4444',red_x:'rgba(239,68,68,.09)',amb:'#F59E0B',amb_x:'rgba(245,158,11,.09)',grn:'#10B981',grn_x:'rgba(16,185,129,.09)',sky:'#06B6D4',sky_x:'rgba(6,182,212,.09)',pur:'#EC4899',pur_x:'rgba(236,72,153,.09)',bg:'#FAF5FF',bg2:'#F5F3FF',bg3:'#EDE9FE',card:'#FFFFFF',brd:'#E9D5FF',brd2:'#D8B4FE',tx1:'#2E1065',tx2:'#5B21B6',tx3:'#A78BFA',banner:'linear-gradient(135deg,#1E1B4B 0%,#4C1D95 40%,#7C3AED 70%,#EC4899 100%)' },
    arctic:   { name:'Arctic',   icon:'❄️', dark:false, pri:'#0EA5E9',pri_d:'#0284C7',pri_x:'rgba(14,165,233,.09)',acc:'#7DD3FC',red:'#EF4444',red_x:'rgba(239,68,68,.09)',amb:'#F59E0B',amb_x:'rgba(245,158,11,.09)',grn:'#10B981',grn_x:'rgba(16,185,129,.09)',sky:'#6366F1',sky_x:'rgba(99,102,241,.09)',pur:'#EC4899',pur_x:'rgba(236,72,153,.09)',bg:'#F0F9FF',bg2:'#E0F2FE',bg3:'#BAE6FD',card:'#FFFFFF',brd:'#BAE6FD',brd2:'#7DD3FC',tx1:'#0C4A6E',tx2:'#075985',tx3:'#7DD3FC',banner:'linear-gradient(135deg,#0C4A6E 0%,#0369A1 40%,#0EA5E9 70%,#06B6D4 100%)' },
    forest:   { name:'Forest',   icon:'🌲', dark:true,  pri:'#22C55E',pri_d:'#16A34A',pri_x:'rgba(34,197,94,.12)',acc:'#4ADE80',red:'#F87171',red_x:'rgba(248,113,113,.12)',amb:'#FBBF24',amb_x:'rgba(251,191,36,.12)',grn:'#22C55E',grn_x:'rgba(34,197,94,.12)',sky:'#38BDF8',sky_x:'rgba(56,189,248,.12)',pur:'#F472B6',pur_x:'rgba(244,114,182,.12)',bg:'#052E16',bg2:'#14532D',bg3:'#166534',card:'#14532D',brd:'rgba(187,247,208,.1)',brd2:'rgba(134,239,172,.18)',tx1:'#F0FDF4',tx2:'#86EFAC',tx3:'#4ADE80',banner:'linear-gradient(135deg,#052E16 0%,#14532D 40%,#166534 70%,#22C55E 100%)' },
    sunset:   { name:'Sunset',   icon:'🌅', dark:false, pri:'#DC2626',pri_d:'#B91C1C',pri_x:'rgba(220,38,38,.09)',acc:'#F87171',red:'#EF4444',red_x:'rgba(239,68,68,.09)',amb:'#F59E0B',amb_x:'rgba(245,158,11,.09)',grn:'#10B981',grn_x:'rgba(16,185,129,.09)',sky:'#06B6D4',sky_x:'rgba(6,182,212,.09)',pur:'#EC4899',pur_x:'rgba(236,72,153,.09)',bg:'#FFF1F2',bg2:'#FFE4E6',bg3:'#FECDD3',card:'#FFFFFF',brd:'#FECDD3',brd2:'#FDA4AF',tx1:'#4C0519',tx2:'#881337',tx3:'#FDA4AF',banner:'linear-gradient(135deg,#4C0519 0%,#881337 40%,#DC2626 70%,#F59E0B 100%)' },
    candy:    { name:'Candy',    icon:'🍬', dark:false, pri:'#DB2777',pri_d:'#BE185D',pri_x:'rgba(219,39,119,.09)',acc:'#F472B6',red:'#EF4444',red_x:'rgba(239,68,68,.09)',amb:'#F59E0B',amb_x:'rgba(245,158,11,.09)',grn:'#10B981',grn_x:'rgba(16,185,129,.09)',sky:'#06B6D4',sky_x:'rgba(6,182,212,.09)',pur:'#8B5CF6',pur_x:'rgba(139,92,246,.09)',bg:'#FDF2F8',bg2:'#FCE7F3',bg3:'#FBCFE8',card:'#FFFFFF',brd:'#FBCFE8',brd2:'#F9A8D4',tx1:'#500724',tx2:'#831843',tx3:'#F9A8D4',banner:'linear-gradient(135deg,#500724 0%,#831843 40%,#DB2777 70%,#EC4899 100%)' },
};

// ═══════════════════════════════════════════════════════════════════════════════
//  MAIN CLASS
// ═══════════════════════════════════════════════════════════════════════════════
class AdminHQ {
    constructor(wrapper) {
        this.wrapper   = wrapper;
        this.page      = frappe.ui.make_app_page({ parent: wrapper, title: 'AdminHQ', single_column: true });
        this.charts    = {};
        this.activeTab = 'overview';
        this.activeTheme = (() => { try { return localStorage.getItem('admhq-theme') || 'midnight'; } catch(e) { return 'midnight'; } })();

        // ── Data stores ──────────────────────────────────────────────────────
        this.requests = []; this.vehicles = []; this.tripLogs = []; this.fuelIssues = [];
        this.facilities = []; this.maintReqs = []; this.workOrders = [];
        this.utilMeters = []; this.utilConsumed = []; this.genLogs = [];
        this.visitors = []; this.incidents = [];
        this.contracts = []; this.providers = [];
        this.compliance = []; this.assetInspections = []; this.hseInspections = [];
        this.roomBookings = [];
        // Messaging
        this.waConvos = []; this.waMessages = []; this.internalChats = [];
        this.blasts = []; this.waTemplates = [];

        this.timer = null;
        this._msgThread = null; // active convo ID in messaging view
        window.__admhq = this;
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

    // ─── THEME ─────────────────────────────────────────────────────────────────
    applyTheme(key, save = true) {
        const t = HQ_THEMES[key] || HQ_THEMES.midnight;
        this.activeTheme = key;
        if (save) { try { localStorage.setItem('admhq-theme', key); } catch(e) {} }
        const root = document.getElementById('hq-root');
        if (!root) return;
        Object.entries(t).forEach(([k, v]) => {
            if (!['name','icon','dark'].includes(k)) root.style.setProperty('--' + k, v);
        });
        if (t.dark) root.classList.add('hq-dark'); else root.classList.remove('hq-dark');
        const lbl = document.getElementById('hq-theme-lbl');
        if (lbl) lbl.textContent = t.icon + ' ' + t.name;
        Object.values(this.charts).forEach(c => { try { c.update(); } catch(e) {} });
    }

    openThemePicker() {
        const cur = this.activeTheme;
        const html = Object.entries(HQ_THEMES).map(([key, t]) => `
            <div onclick="window.__admhq.applyTheme('${key}');if(cur_dialog)cur_dialog.hide();"
                 style="display:flex;align-items:center;gap:10px;padding:11px 13px;border-radius:10px;
                        border:2px solid ${key===cur?t.pri:(t.brd2||'#CBD5E1')};
                        background:${t.card};cursor:pointer;transition:border-color .18s">
                <div style="font-size:22px;width:36px;height:36px;border-radius:8px;background:${t.pri_x};display:flex;align-items:center;justify-content:center">${t.icon}</div>
                <div><div style="font-size:13px;font-weight:700;color:${t.tx1}">${t.name}</div>
                <div style="font-size:10px;color:${t.tx3}">${t.dark?'🌙 Dark':'☀️ Light'} · localStorage only</div></div>
                ${key===cur?`<span style="margin-left:auto;color:${t.pri};font-size:16px">✓</span>`:''}
            </div>`).join('');
        new frappe.ui.Dialog({ title:'🎨 AdminHQ Theme', size:'large', fields:[{ fieldtype:'HTML', options:`
            <p style="font-size:12px;color:var(--tx3);margin:0 0 12px">Stored in your browser. No database writes.</p>
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px">${html}</div>` }] }).show();
    }

    // ─── CSS ───────────────────────────────────────────────────────────────────
    injectCSS() {
        if (document.getElementById('hq-css')) return;
        const s = document.createElement('style');
        s.id = 'hq-css';
        s.textContent = `
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap');
#hq-root{--pri:#0284C7;--pri_d:#0369A1;--pri_x:rgba(2,132,199,.09);--acc:#38BDF8;--red:#EF4444;--red_x:rgba(239,68,68,.09);--amb:#F59E0B;--amb_x:rgba(245,158,11,.09);--grn:#10B981;--grn_x:rgba(16,185,129,.09);--sky:#06B6D4;--sky_x:rgba(6,182,212,.09);--pur:#8B5CF6;--pur_x:rgba(139,92,246,.09);--bg:#F8FAFC;--bg2:#F1F5F9;--bg3:#E2E8F0;--card:#FFFFFF;--brd:#E2E8F0;--brd2:#CBD5E1;--tx1:#0F172A;--tx2:#475569;--tx3:#94A3B8;--banner:linear-gradient(135deg,#0F172A,#0284C7);font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--tx1);min-height:100vh;transition:background .3s,color .3s}
#hq-root *{box-sizing:border-box}
#hq-root.hq-dark input,#hq-root.hq-dark select,#hq-root.hq-dark textarea{color-scheme:dark}
.hq-banner{background:var(--banner);padding:20px 24px 16px;margin:-15px -15px 20px;position:relative;overflow:hidden;color:#fff}
.hq-banner::before{content:'';position:absolute;width:500px;height:500px;top:-50%;right:-6%;border-radius:50%;background:radial-gradient(circle,rgba(255,255,255,.05) 0%,transparent 65%)}
.hq-bi{position:relative;z-index:1;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}
.hq-banner h1{font-size:21px;font-weight:800;letter-spacing:-.4px;margin:0 0 5px;display:flex;align-items:center;gap:9px}
.hq-meta{display:flex;align-items:center;gap:12px;font-size:12px;opacity:.82;flex-wrap:wrap}
.hq-live{display:inline-flex;align-items:center;gap:5px;background:rgba(16,185,129,.22);padding:3px 9px;border-radius:20px;font-size:11px;color:#34d399;border:1px solid rgba(16,185,129,.3)}
.hq-dot{width:7px;height:7px;background:#34d399;border-radius:50%;animation:hq-pulse 2s infinite}
@keyframes hq-pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(1.3)}}
.hq-chip{background:rgba(255,255,255,.14);padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600}
.hq-tbtn{display:inline-flex;align-items:center;gap:6px;padding:5px 12px;border-radius:20px;font-size:11px;font-weight:700;background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.25);color:#fff;cursor:pointer;transition:background .18s;font-family:inherit}
.hq-tbtn:hover{background:rgba(255,255,255,.3)}
.hq-alerts{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:14px}
.hq-alert{display:flex;align-items:center;gap:6px;padding:6px 12px;border-radius:9px;font-size:11px;font-weight:600;cursor:pointer;border:1px solid transparent;transition:transform .18s;text-decoration:none !important}
.hq-alert:hover{transform:translateY(-1px)}
.ha-r{background:var(--red_x);border-color:rgba(239,68,68,.2);color:var(--red)}
.ha-a{background:var(--amb_x);border-color:rgba(245,158,11,.2);color:var(--amb)}
.ha-p{background:var(--pri_x);border-color:rgba(2,132,199,.2);color:var(--pri)}
.ha-g{background:var(--grn_x);border-color:rgba(16,185,129,.2);color:var(--grn)}
.ha-v{background:var(--pur_x);border-color:rgba(139,92,246,.2);color:var(--pur)}
.hq-tabs{display:flex;gap:2px;background:var(--card);border:1px solid var(--brd);border-radius:12px;margin-bottom:16px;overflow-x:auto;scrollbar-width:none}
.hq-tabs::-webkit-scrollbar{display:none}
.hq-tab{display:flex;align-items:center;gap:6px;padding:9px 13px;font-size:12px;font-weight:600;color:var(--tx2);cursor:pointer;border-bottom:3px solid transparent;transition:all .18s;white-space:nowrap;background:none;border-left:none;border-right:none;border-top:none;font-family:inherit}
.hq-tab:hover{color:var(--pri);background:var(--pri_x)}
.hq-tab.active{color:var(--pri);border-bottom-color:var(--pri);background:var(--pri_x)}
.hq-tab-n{background:var(--red);color:#fff;font-size:9px;font-weight:800;padding:1px 5px;border-radius:20px;min-width:15px;text-align:center}
.hq-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:11px;margin-bottom:16px}
.hq-kpi{background:var(--card);border:1px solid var(--brd);border-radius:13px;padding:15px 17px;cursor:pointer;transition:all .2s;position:relative;overflow:hidden}
.hq-kpi::after{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--kc,var(--pri));opacity:0;transition:opacity .2s}
.hq-kpi:hover{transform:translateY(-3px);box-shadow:0 8px 24px rgba(0,0,0,.1)}
.hq-kpi:hover::after{opacity:1}
.kp{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:var(--tx3);margin-bottom:5px}
.kv{font-size:24px;font-weight:800;color:var(--tx1);line-height:1;margin-bottom:3px}
.ks{font-size:11px;color:var(--tx3)}
.hq-card{background:var(--card);border:1px solid var(--brd);border-radius:13px;overflow:hidden;transition:box-shadow .2s;margin-bottom:14px}
.hq-card:hover{box-shadow:0 4px 20px rgba(0,0,0,.07)}
.hq-ch{padding:12px 17px;border-bottom:1px solid var(--brd);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px}
.hq-ct{display:flex;align-items:center;gap:8px;font-size:13px;font-weight:700;color:var(--tx1)}
.hq-cb{padding:14px 17px}
.hq-g2{display:grid;grid-template-columns:1fr 1fr;gap:13px;margin-bottom:13px}
.hq-g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:13px;margin-bottom:13px}
.hq-g21{display:grid;grid-template-columns:2fr 1fr;gap:13px;margin-bottom:13px}
.hq-g31{display:grid;grid-template-columns:3fr 1fr;gap:13px;margin-bottom:13px}
.hq-g4{display:grid;grid-template-columns:repeat(4,1fr);gap:11px;margin-bottom:13px}
.hq-acts{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.hq-btn{display:inline-flex;align-items:center;gap:5px;padding:5px 12px;border-radius:20px;font-size:11px;font-weight:700;cursor:pointer;border:1.5px solid transparent;font-family:inherit;transition:all .18s;line-height:1.4;text-decoration:none !important}
.hq-btn:hover{transform:translateY(-1px)}
.hb-p{background:var(--pri_x);color:var(--pri);border-color:rgba(2,132,199,.2)}.hb-p:hover{background:var(--pri);color:#fff}
.hb-g{background:var(--grn_x);color:var(--grn);border-color:rgba(16,185,129,.2)}.hb-g:hover{background:var(--grn);color:#fff}
.hb-r{background:var(--red_x);color:var(--red);border-color:rgba(239,68,68,.2)}.hb-r:hover{background:var(--red);color:#fff}
.hb-a{background:var(--amb_x);color:var(--amb);border-color:rgba(245,158,11,.2)}.hb-a:hover{background:var(--amb);color:#fff}
.hb-v{background:var(--pur_x);color:var(--pur);border-color:rgba(139,92,246,.2)}.hb-v:hover{background:var(--pur);color:#fff}
.hb-s{background:var(--sky_x);color:var(--sky);border-color:rgba(6,182,212,.2)}.hb-s:hover{background:var(--sky);color:#fff}
.hb-solid{background:var(--pri);color:#fff;border-color:var(--pri)}.hb-solid:hover{background:var(--pri_d)}
.hb-ghost{background:transparent;color:var(--tx2);border-color:var(--brd2)}.hb-ghost:hover{background:var(--bg2);color:var(--tx1)}
.hq-badge{display:inline-flex;align-items:center;gap:3px;padding:2px 7px;border-radius:20px;font-size:10px;font-weight:700;white-space:nowrap}
.bg-g{background:var(--grn_x);color:var(--grn)}.bg-r{background:var(--red_x);color:var(--red)}.bg-a{background:var(--amb_x);color:var(--amb)}.bg-p{background:var(--pri_x);color:var(--pri)}.bg-s{background:var(--sky_x);color:var(--sky)}.bg-v{background:var(--pur_x);color:var(--pur)}.bg-gr{background:var(--bg3);color:var(--tx3);border:1px solid var(--brd2)}
.hq-tbl-w{overflow-x:auto;max-height:460px;overflow-y:auto;scrollbar-width:thin;scrollbar-color:var(--brd2) transparent}
.hq-tbl{width:100%;border-collapse:collapse;font-size:12px}
.hq-tbl thead th{padding:9px 12px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--tx3);background:var(--bg2);border-bottom:2px solid var(--brd);position:sticky;top:0;white-space:nowrap;z-index:1}
.hq-tbl tbody td{padding:9px 12px;border-bottom:1px solid var(--brd);color:var(--tx2)}
.hq-tbl tbody tr{cursor:pointer;transition:background .1s}
.hq-tbl tbody tr:hover{background:var(--pri_x)}
.hq-tbl tbody tr:hover td{color:var(--tx1)}
.hq-tbl tbody tr:last-child td{border-bottom:none}
.hq-bar-row{display:flex;align-items:center;gap:9px;margin-bottom:8px}
.hq-bar-lbl{font-size:11px;color:var(--tx2);width:140px;flex-shrink:0}
.hq-bar{flex:1;height:5px;background:var(--brd);border-radius:40px;overflow:hidden}
.hq-bar-fill{height:100%;border-radius:40px;transition:width .6s cubic-bezier(.4,0,.2,1)}
.hq-bar-val{font-size:11px;font-family:'JetBrains Mono',monospace;font-weight:700;width:55px;text-align:right;color:var(--tx1)}
.hq-li{display:flex;align-items:center;justify-content:space-between;padding:7px 0;border-bottom:1px solid var(--brd);font-size:12px;gap:8px}
.hq-li:last-child{border-bottom:none}
.hq-li-l{flex:1;min-width:0}
.hq-li-t{font-weight:600;color:var(--tx1);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hq-li-s{font-size:10px;color:var(--tx3);margin-top:1px}
.hq-abox{display:flex;align-items:flex-start;gap:8px;padding:9px 11px;border-radius:10px;margin-bottom:7px;font-size:12px;border:1px solid transparent}
.hq-abox:last-child{margin-bottom:0}
.ab-r{background:var(--red_x);border-color:rgba(239,68,68,.2)}.ab-a{background:var(--amb_x);border-color:rgba(245,158,11,.2)}.ab-g{background:var(--grn_x);border-color:rgba(16,185,129,.2)}.ab-b{background:var(--pri_x);border-color:rgba(2,132,199,.2)}
.hq-abox .at{font-weight:700;color:var(--tx1)}.hq-abox .as{color:var(--tx2);margin-top:2px}
.hq-stat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(85px,1fr));gap:8px}
.hq-stat{background:var(--bg2);border-radius:9px;padding:10px;text-align:center}
.hq-stat-v{font-size:18px;font-weight:800;color:var(--tx1)}
.hq-stat-l{font-size:9px;text-transform:uppercase;letter-spacing:.5px;color:var(--tx3);margin-top:2px}
.hq-loader{position:fixed;inset:0;background:rgba(10,15,30,.82);display:flex;align-items:center;justify-content:center;flex-direction:column;gap:13px;z-index:999}
.hq-spin{width:36px;height:36px;border:3px solid var(--brd2);border-top-color:var(--pri);border-radius:50%;animation:hq-spin .7s linear infinite}
@keyframes hq-spin{to{transform:rotate(360deg)}}
.hq-hr{border:none;border-top:1px solid var(--brd);margin:14px 0}
.hq-panel{display:none}.hq-panel.active{display:block}
.hq-content{padding:0 16px 32px}

/* ── MESSAGING SPECIFIC ────────────────────────────────── */
.hq-msg-layout{display:grid;grid-template-columns:280px 1fr;gap:0;height:580px;border:1px solid var(--brd);border-radius:13px;overflow:hidden;background:var(--card)}
.hq-convo-list{border-right:1px solid var(--brd);overflow-y:auto;background:var(--bg2);scrollbar-width:thin}
.hq-convo-list::-webkit-scrollbar{width:3px}.hq-convo-list::-webkit-scrollbar-thumb{background:var(--brd2)}
.hq-convo-item{padding:11px 14px;border-bottom:1px solid var(--brd);cursor:pointer;transition:background .12s}
.hq-convo-item:hover{background:var(--pri_x)}
.hq-convo-item.active{background:var(--pri_x);border-left:3px solid var(--pri)}
.hq-convo-name{font-size:12px;font-weight:700;color:var(--tx1);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hq-convo-preview{font-size:10px;color:var(--tx3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:2px}
.hq-convo-meta{display:flex;align-items:center;justify-content:space-between;gap:4px;margin-bottom:3px}
.hq-convo-time{font-size:9px;color:var(--tx3);font-family:'JetBrains Mono',monospace;flex-shrink:0}
.hq-unread{background:var(--pri);color:#fff;font-size:9px;font-weight:800;padding:1px 5px;border-radius:10px;flex-shrink:0}
.hq-msg-pane{display:flex;flex-direction:column;height:100%}
.hq-msg-header{padding:11px 16px;border-bottom:1px solid var(--brd);display:flex;align-items:center;gap:10px;background:var(--card);flex-shrink:0}
.hq-msg-title{font-size:13px;font-weight:700;color:var(--tx1)}
.hq-msg-sub{font-size:10px;color:var(--tx3)}
.hq-msg-body{flex:1;overflow-y:auto;padding:14px 16px;display:flex;flex-direction:column;gap:8px;scrollbar-width:thin;background:var(--bg)}
.hq-bubble-wrap{display:flex;gap:8px;align-items:flex-end}
.hq-bubble-wrap.out{flex-direction:row-reverse}
.hq-avatar-s{width:26px;height:26px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:#fff}
.hq-bubble{max-width:68%;padding:8px 11px;border-radius:12px;font-size:12px;line-height:1.5;color:var(--tx1)}
.hq-bubble.in{background:var(--card);border:1px solid var(--brd);border-radius:2px 12px 12px 12px}
.hq-bubble.out{background:var(--pri);color:#fff;border-radius:12px 2px 12px 12px}
.hq-bubble-time{font-size:9px;opacity:.6;margin-top:3px;font-family:'JetBrains Mono',monospace}
.hq-msg-footer{padding:10px 14px;border-top:1px solid var(--brd);background:var(--card);flex-shrink:0}
.hq-msg-input-row{display:flex;gap:8px;align-items:flex-end}
.hq-msg-ta{flex:1;background:var(--bg2);border:1.5px solid var(--brd2);border-radius:10px;color:var(--tx1);font-family:'Inter',system-ui;font-size:12px;padding:8px 12px;outline:none;resize:none;min-height:36px;max-height:100px;transition:border-color .15s;line-height:1.5}
.hq-msg-ta:focus{border-color:var(--pri);box-shadow:0 0 0 3px var(--pri_x)}
.hq-msg-send{width:34px;height:34px;border-radius:50%;background:var(--pri);border:none;color:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:14px;transition:all .18s;flex-shrink:0}
.hq-msg-send:hover{background:var(--pri_d);transform:scale(1.05)}
.hq-msg-empty{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;color:var(--tx3);text-align:center;gap:10px}
.hq-msg-empty-icon{font-size:40px;opacity:.4}
.hq-chan-pill{display:inline-flex;align-items:center;gap:4px;padding:2px 7px;border-radius:20px;font-size:9px;font-weight:700}
.chan-wa{background:#e8faf0;color:#128C7E}.chan-sms{background:#fef3c7;color:#92400e}.chan-email{background:#eff6ff;color:#1e40af}.chan-int{background:var(--pur_x);color:var(--pur)}

/* SPEND LEGEND */
.hq-spend-legend{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.hq-spend-dot{display:flex;align-items:center;gap:4px;font-size:11px;color:var(--tx2)}

/* BROADCAST */
.hq-blast-card{background:var(--bg2);border:1px solid var(--brd);border-radius:10px;padding:12px;margin-bottom:8px;cursor:pointer;transition:all .18s}
.hq-blast-card:hover{border-color:var(--pri);background:var(--pri_x)}
.hq-blast-title{font-size:12px;font-weight:700;color:var(--tx1);margin-bottom:4px}
.hq-blast-meta{font-size:10px;color:var(--tx3)}
.hq-blast-stats{display:flex;gap:10px;margin-top:6px;font-size:10px}
.hq-blast-stat{display:flex;align-items:center;gap:3px}

/* RESPONSIVE */
@media(max-width:1100px){.hq-g21,.hq-g31{grid-template-columns:1fr}.hq-msg-layout{grid-template-columns:1fr;height:auto}}
@media(max-width:800px){.hq-g2,.hq-g3,.hq-g4{grid-template-columns:1fr}}`;
        document.head.appendChild(s);
    }

    // ─── LAYOUT ────────────────────────────────────────────────────────────────
    buildLayout() {
        $(this.page.main).empty();
        $(`
        <div id="hq-root">
            <div class="hq-banner">
                <div class="hq-bi">
                    <div>
                        <h1>🏢 AdminHQ</h1>
                        <div class="hq-meta">
                            <span>📅 <span id="hq-date"></span></span>
                            <span id="hq-clock" style="font-family:'JetBrains Mono',monospace"></span>
                            <span class="hq-live"><span class="hq-dot"></span> Live</span>
                            <span class="hq-chip" id="hq-c1">— Requests</span>
                            <span class="hq-chip" id="hq-c2">— Fleet</span>
                            <span class="hq-chip" id="hq-c3">— Messages</span>
                        </div>
                    </div>
                    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
                        <button class="hq-tbtn" onclick="window.__admhq.openThemePicker()">🎨 <span id="hq-theme-lbl">🌙 Midnight</span></button>
                        <span id="hq-ts" style="font-size:11px;opacity:.6"></span>
                    </div>
                </div>
            </div>
            <div class="hq-content">
                <div class="hq-alerts" id="hq-alerts"></div>
                <div class="hq-tabs" id="hq-tabs">
                    <button class="hq-tab active" data-tab="overview">🏠 Overview</button>
                    <button class="hq-tab" data-tab="requests">📋 Requests<span class="hq-tab-n" id="hq-n-req" style="display:none">0</span></button>
                    <button class="hq-tab" data-tab="fleet">🚗 Fleet<span class="hq-tab-n" id="hq-n-flt" style="display:none">0</span></button>
                    <button class="hq-tab" data-tab="facilities">🏗 Facilities<span class="hq-tab-n" id="hq-n-fac" style="display:none">0</span></button>
                    <button class="hq-tab" data-tab="utilities">⚡ Utilities</button>
                    <button class="hq-tab" data-tab="security">🛡 Security<span class="hq-tab-n" id="hq-n-sec" style="display:none">0</span></button>
                    <button class="hq-tab" data-tab="contracts">📑 Contracts<span class="hq-tab-n" id="hq-n-con" style="display:none">0</span></button>
                    <button class="hq-tab" data-tab="compliance">🎖 Compliance<span class="hq-tab-n" id="hq-n-cmp" style="display:none">0</span></button>
                    <button class="hq-tab" data-tab="hse">⚠️ HSE</button>
                    <button class="hq-tab" data-tab="messaging">💬 Messaging<span class="hq-tab-n" id="hq-n-msg" style="display:none">0</span></button>
                    <button class="hq-tab" data-tab="intelligence">🤖 AI</button>
                </div>
                <div id="hq-panel-overview"     class="hq-panel active"></div>
                <div id="hq-panel-requests"     class="hq-panel"></div>
                <div id="hq-panel-fleet"        class="hq-panel"></div>
                <div id="hq-panel-facilities"   class="hq-panel"></div>
                <div id="hq-panel-utilities"    class="hq-panel"></div>
                <div id="hq-panel-security"     class="hq-panel"></div>
                <div id="hq-panel-contracts"    class="hq-panel"></div>
                <div id="hq-panel-compliance"   class="hq-panel"></div>
                <div id="hq-panel-hse"          class="hq-panel"></div>
                <div id="hq-panel-messaging"    class="hq-panel"></div>
                <div id="hq-panel-intelligence" class="hq-panel"></div>
            </div>
            <div class="hq-loader" id="hq-loader" style="display:none">
                <div class="hq-spin"></div>
                <div style="font-weight:600;font-size:14px;color:#F1F5F9">Loading AdminHQ</div>
                <div style="font-size:12px;color:#94A3B8">Fetching all admin data…</div>
            </div>
        </div>`).appendTo(this.page.main);
    }

    setupActions() {
        this.page.add_inner_button('🔄 Refresh', () => this.loadData());
        this.page.add_inner_button('📋 New Request', () => frappe.new_doc('Administrative Request'));
        this.page.add_inner_button('💬 New Message', () => this.switchTab('messaging'));
        this.page.add_inner_button('👤 Visitor In', () => frappe.new_doc('Visitor Register'));
        this.page.add_menu_item('🎨 Themes', () => this.openThemePicker());
        this.page.add_menu_item('🖨️ Print', () => window.print());
        this.page.add_menu_item('📊 Export CSV', () => this.exportCSV());
    }

    bindEvents() {
        $(document).on('click', '.hq-tab', e => this.switchTab($(e.currentTarget).data('tab')));
    }

    switchTab(name) {
        $('.hq-tab').removeClass('active');
        $(`.hq-tab[data-tab="${name}"]`).addClass('active');
        $('.hq-panel').removeClass('active');
        $(`#hq-panel-${name}`).addClass('active');
        this.activeTab = name;
        if (this.requests.length || this.vehicles.length || name === 'messaging') this.renderTab(name);
    }

    startClock() {
        const tick = () => {
            $('#hq-clock').text(new Date().toLocaleTimeString('en-NG', { hour12:true, hour:'2-digit', minute:'2-digit', second:'2-digit' }));
            $('#hq-date').text(frappe.datetime.str_to_user(frappe.datetime.get_today()));
        };
        tick(); setInterval(tick, 1000);
    }

    startAutoRefresh() { this.stopAutoRefresh(); this.timer = setInterval(() => this.loadData(true), 30000); }
    stopAutoRefresh()  { if (this.timer) { clearInterval(this.timer); this.timer = null; } }

    // ─── DATA LOAD ─────────────────────────────────────────────────────────────
    async loadData(silent = false) {
        if (!silent) $('#hq-loader').show();
        try {
            const gl = 'frappe.client.get_list';
            const safe = async (method, args) => {
                try { const r = await frappe.call({ method, args }); return r.message || []; }
                catch(e) { console.warn('AdminHQ fetch failed for', args.doctype, ':', e.message); return []; }
            };

            [
                this.requests, this.vehicles, this.tripLogs, this.fuelIssues,
                this.facilities, this.maintReqs, this.workOrders,
                this.utilMeters, this.utilConsumed, this.genLogs,
                this.visitors, this.incidents,
                this.contracts, this.providers, this.compliance,
                this.assetInspections, this.hseInspections, this.roomBookings,
                this.waConvos, this.waMessages, this.internalChats,
                this.blasts, this.waTemplates
            ] = await Promise.all([
                safe(gl, { doctype:'Administrative Request', fields:['name','request_title','request_type','priority','status','employee','department','request_date','required_by_date','estimated_cost','actual_cost','sla_breached','request_age_days','completion_days'], limit_page_length:500, order_by:'modified desc' }),
                safe(gl, { doctype:'Company Vehicle', fields:['name','vehicle_name','plate_number','vehicle_type','status','assigned_driver','fuel_type','odometer_reading','insurance_expiry','license_expiry','road_worthiness_expiry','fuel_cost_ytd','maintenance_cost_ytd','total_km_ytd','cost_per_km','trips_ytd'], limit_page_length:200 }),
                safe(gl, { doctype:'Vehicle Trip Log', fields:['name','vehicle','driver','trip_date','purpose','distance_km','total_fuel_cost'], limit_page_length:300, order_by:'trip_date desc' }),
                safe(gl, { doctype:'Fuel Issue', fields:['name','vehicle','driver','issue_date','fuel_type','litres_issued','total_cost','issue_method'], limit_page_length:200, order_by:'issue_date desc' }),
                safe(gl, { doctype:'Facility', fields:['name','facility_name','facility_type','status','branch','open_maintenance_requests','maintenance_cost_ytd','utility_cost_ytd','capacity'], limit_page_length:100 }),
                safe(gl, { doctype:'Facility Maintenance Request', fields:['name','subject','facility','maintenance_category','priority','status','report_date','estimated_cost','actual_cost'], limit_page_length:300, order_by:'modified desc' }),
                safe(gl, { doctype:'Maintenance Work Order', fields:['name','title','facility','work_type','status','priority','start_date','estimated_cost','actual_cost'], limit_page_length:200, order_by:'modified desc' }),
                safe(gl, { doctype:'Utility Meter', fields:['name','meter_name','utility_type','facility','status','rate_per_unit'], limit_page_length:100 }),
                safe(gl, { doctype:'Utility Consumption', fields:['name','utility_meter','facility','utility_type','period_month','period_year','consumption','total_bill','variance_pct','reading_date'], limit_page_length:300, order_by:'reading_date desc' }),
                safe(gl, { doctype:'Generator Log', fields:['name','facility','log_date','run_hours','fuel_consumed_litres','fuel_cost','reason_for_running'], limit_page_length:200, order_by:'log_date desc' }),
                safe(gl, { doctype:'Visitor Register', fields:['name','visitor_name','visitor_company','host_employee','visit_date','check_in_time','check_out_time','status','purpose_of_visit','facility'], limit_page_length:300, order_by:'visit_date desc' }),
                safe(gl, { doctype:'Security Incident', fields:['name','incident_title','incident_type','severity','status','facility','incident_date','reported_by','estimated_loss'], limit_page_length:200, order_by:'incident_date desc' }),
                safe(gl, { doctype:'Service Contract', fields:['name','contract_title','contract_type','vendor','start_date','end_date','contract_value','status','days_to_expiry','sla_response_hours'], limit_page_length:200, order_by:'end_date asc' }),
                safe(gl, { doctype:'Service Provider', fields:['name','provider_name','service_category','status','supplier','performance_score','active_contracts'], limit_page_length:100 }),
                safe(gl, { doctype:'Compliance Register', fields:['name','compliance_item','compliance_type','issuing_authority','facility','expiry_date','status','renewal_cost'], limit_page_length:200, order_by:'expiry_date asc' }),
                safe(gl, { doctype:'Asset Inspection', fields:['name','asset','facility','inspection_date','inspection_type','overall_condition','status','inspector'], limit_page_length:200, order_by:'inspection_date desc' }),
                safe(gl, { doctype:'HSE Inspection', fields:['name','facility','inspection_date','inspection_type','overall_score','pass_fail','status','inspector'], limit_page_length:200, order_by:'inspection_date desc' }),
                safe(gl, { doctype:'Meeting Room Booking', fields:['name','meeting_title','facility','booking_date','start_time','end_time','booked_by','status','attendees_count'], limit_page_length:200, order_by:'booking_date desc' }),
                // ── Messaging DocTypes ──────────────────────────────────────
                safe(gl, { doctype:'WA Conversation', fields:['name','phone_number','contact_display_name','status','assigned_to','channel_type','last_message_at','last_message_preview','unread_count','total_messages','contact','customer'], limit_page_length:100, order_by:'last_message_at desc' }),
                safe(gl, { doctype:'WA Message', fields:['name','conversation','direction','message_type','timestamp','sender_phone','delivery_status','body','wa_template'], limit_page_length:500, order_by:'timestamp desc' }),
                safe(gl, { doctype:'WA Internal Chat', fields:['name','chat_name','chat_type','is_active','last_message_at','last_message_preview','total_messages','member_count'], limit_page_length:50, order_by:'last_message_at desc' }),
                safe(gl, { doctype:'Message Blast', fields:['name','subject','status','message_type','date','audience_group','total_recipients','sent_count','failed_count','pending_count'], limit_page_length:50, order_by:'date desc' }),
                safe(gl, { doctype:'WA Template', fields:['name','template_name','channel','category','status','is_active'], limit_page_length:50 }),
            ]);

            this.renderAll();
            $('#hq-ts').text('Updated ' + new Date().toLocaleTimeString('en-NG', { hour12:true }));
        } catch(e) {
            console.error('AdminHQ loadData error:', e);
            if (!silent) frappe.msgprint({ title:'Load Error', indicator:'red', message:'Failed to load data. Verify DocTypes are installed.' });
        } finally { $('#hq-loader').hide(); }
    }

    // ─── HELPERS ───────────────────────────────────────────────────────────────
    flt(v)  { return parseFloat(v) || 0; }
    n(v)    { return parseInt(v) || 0; }

    fmt(v) {
        const n = this.flt(v);
        if (n >= 1e9) return '₦' + (n/1e9).toFixed(1) + 'B';
        if (n >= 1e6) return '₦' + (n/1e6).toFixed(1) + 'M';
        if (n >= 1e3) return '₦' + (n/1e3).toFixed(0) + 'k';
        return '₦' + n.toFixed(0);
    }

    kpi(icon, kc, lbl, val, sub, link) {
        const onclick = link ? `frappe.set_route('${link}')` : '';
        return `<div class="hq-kpi ${kc}" onclick="${onclick}">
            <div style="font-size:16px;margin-bottom:7px">${icon}</div>
            <div class="kp">${lbl}</div>
            <div class="kv">${val}</div>
            <div class="ks">${sub}</div>
        </div>`;
    }

    badge(t, c) { return `<span class="hq-badge ${c}">${t}</span>`; }

    sbadge(s) {
        const m = { 'Draft':'bg-gr','Submitted':'bg-p','Approved':'bg-s','In Progress':'bg-a','Completed':'bg-g','Rejected':'bg-r','Closed':'bg-gr','Cancelled':'bg-gr','Open':'bg-p','Active':'bg-g','Expired':'bg-r','Expiring Soon':'bg-a','Valid':'bg-g','Under Investigation':'bg-v','Resolved':'bg-g','Escalated to Police':'bg-r','Available':'bg-g','In Use':'bg-p','Under Maintenance':'bg-a','Grounded':'bg-r','Confirmed':'bg-g','Pending':'bg-a','Pass':'bg-g','Fail':'bg-r','Conditional Pass':'bg-a','Reported':'bg-p','Sent':'bg-g','Failed':'bg-r','Scheduled':'bg-s','Open':'bg-p','Resolved':'bg-g','Bot':'bg-gr','Spam':'bg-gr' };
        return this.badge(s, m[s] || 'bg-gr');
    }

    priB(p) {
        const m = { 'Urgent':'bg-r','High':'bg-a','Medium':'bg-p','Low':'bg-g','Emergency':'bg-r' };
        return this.badge(p, m[p] || 'bg-gr');
    }

    daysLeft(d) { return d ? Math.ceil((new Date(d) - new Date()) / 86400000) : null; }

    dlBadge(d) {
        const n = this.daysLeft(d);
        if (n === null) return '';
        if (n < 0)  return this.badge(`Expired ${Math.abs(n)}d`, 'bg-r');
        if (n <= 14) return this.badge(`${n}d`, 'bg-r');
        if (n <= 30) return this.badge(`${n}d`, 'bg-a');
        if (n <= 60) return this.badge(`${n}d`, 'bg-s');
        return this.badge(`${n}d`, 'bg-g');
    }

    colors() { return ['#0284C7','#10B981','#F59E0B','#8B5CF6','#EF4444','#06B6D4','#EC4899','#F97316','#22C55E','#94A3B8']; }

    destroyChart(id) { if (this.charts[id]) { try { this.charts[id].destroy(); } catch(e) {} delete this.charts[id]; } }
    makeChart(id, cfg) { this.destroyChart(id); const el = document.getElementById(id); if (el) this.charts[id] = new Chart(el, cfg); }

    // ─── SPEND BREAKDOWN — the real math ───────────────────────────────────────
    // Each figure is derived from actual DocType records:
    //   Utilities  = Utility Consumption (total_bill) + Generator Log (fuel_cost)
    //   Fleet fuel = Fuel Issue (total_cost) — fuel purchases
    //   Maintenance = Maintenance Work Order (actual_cost) — labour + materials
    //   Contracts  = Service Contract active annualised ÷ 12 (monthly portion)
    //   Admin ops  = Administrative Request (actual_cost) on Completed requests
    computeSpend() {
        const today = frappe.datetime.get_today();
        const month = today.substring(0, 7);
        const yearStart = today.substring(0, 4) + '-01-01';

        const utilCostMTD = this.utilConsumed
            .filter(u => u.reading_date && u.reading_date.substring(0, 7) === month)
            .reduce((s, u) => s + this.flt(u.total_bill), 0);

        const genCostMTD = this.genLogs
            .filter(g => g.log_date && g.log_date.substring(0, 7) === month)
            .reduce((s, g) => s + this.flt(g.fuel_cost), 0);

        const fleetFuelMTD = this.fuelIssues
            .filter(f => f.issue_date && f.issue_date.substring(0, 7) === month)
            .reduce((s, f) => s + this.flt(f.total_cost), 0);

        const maintCostMTD = this.workOrders
            .filter(w => w.start_date && w.start_date.substring(0, 7) === month)
            .reduce((s, w) => s + this.flt(w.actual_cost), 0);

        const activeContractMonthly = this.contracts
            .filter(c => c.status === 'Active')
            .reduce((s, c) => s + this.flt(c.contract_value) / 12, 0);

        const adminOpsMTD = this.requests
            .filter(r => r.status === 'Completed' && r.request_date && r.request_date.substring(0, 7) === month)
            .reduce((s, r) => s + this.flt(r.actual_cost), 0);

        return {
            utilCostMTD, genCostMTD, fleetFuelMTD, maintCostMTD,
            activeContractMonthly, adminOpsMTD,
            totalMTD: utilCostMTD + genCostMTD + fleetFuelMTD + maintCostMTD + activeContractMonthly + adminOpsMTD
        };
    }

    // ─── RENDER ALL ────────────────────────────────────────────────────────────
    renderAll() {
        const today = frappe.datetime.get_today();
        const openReqs    = this.requests.filter(r => !['Completed','Closed','Rejected','Cancelled'].includes(r.status));
        const slaBreached = this.requests.filter(r => r.sla_breached == 1);
        const groundedVeh = this.vehicles.filter(v => v.status === 'Grounded');
        const openMaint   = this.maintReqs.filter(m => !['Completed','Closed','Cancelled'].includes(m.status));
        const openInc     = this.incidents.filter(i => !['Resolved','Closed'].includes(i.status));
        const expiringCon = this.contracts.filter(c => { const d = this.daysLeft(c.end_date); return d !== null && d >= 0 && d <= 60; });
        const expiredComp = this.compliance.filter(c => c.status === 'Expired');
        const expiringComp= this.compliance.filter(c => c.status === 'Expiring Soon');
        const unreadMsg   = this.waConvos.reduce((s, c) => s + this.n(c.unread_count), 0);

        // Tab badges
        $('#hq-n-req').text(slaBreached.length + openReqs.length).toggle(openReqs.length > 0);
        $('#hq-n-flt').text(groundedVeh.length).toggle(groundedVeh.length > 0);
        $('#hq-n-fac').text(openMaint.length).toggle(openMaint.length > 0);
        $('#hq-n-sec').text(openInc.length).toggle(openInc.length > 0);
        $('#hq-n-con').text(expiringCon.length).toggle(expiringCon.length > 0);
        $('#hq-n-cmp').text(expiredComp.length + expiringComp.length).toggle((expiredComp.length + expiringComp.length) > 0);
        $('#hq-n-msg').text(unreadMsg).toggle(unreadMsg > 0);

        // Banner chips
        $('#hq-c1').text(`${openReqs.length} open requests`);
        $('#hq-c2').text(`${this.vehicles.filter(v=>v.status==='Available').length}/${this.vehicles.length} vehicles`);
        $('#hq-c3').text(`${unreadMsg} unread messages`);

        // Alert strip
        const alerts = [];
        if (expiredComp.length)  alerts.push({ cls:'ha-r', icon:'🎖', text:`${expiredComp.length} compliance item${expiredComp.length>1?'s':''} EXPIRED`, tab:'compliance' });
        if (slaBreached.length)  alerts.push({ cls:'ha-r', icon:'⏱', text:`${slaBreached.length} request${slaBreached.length>1?'s':''} breached SLA`, tab:'requests' });
        if (groundedVeh.length)  alerts.push({ cls:'ha-r', icon:'🚗', text:`${groundedVeh.length} vehicle${groundedVeh.length>1?'s':''} grounded`, tab:'fleet' });
        if (openInc.length)      alerts.push({ cls:'ha-a', icon:'🛡', text:`${openInc.length} open incident${openInc.length>1?'s':''}`, tab:'security' });
        if (expiringCon.length)  alerts.push({ cls:'ha-a', icon:'📑', text:`${expiringCon.length} contract${expiringCon.length>1?'s':''} expiring ≤60 days`, tab:'contracts' });
        if (unreadMsg > 0)       alerts.push({ cls:'ha-v', icon:'💬', text:`${unreadMsg} unread message${unreadMsg>1?'s':''}`, tab:'messaging' });
        if (openMaint.length)    alerts.push({ cls:'ha-p', icon:'🔧', text:`${openMaint.length} open maintenance request${openMaint.length>1?'s':''}`, tab:'facilities' });

        $('#hq-alerts').html(
            alerts.map(a => `<a class="hq-alert ${a.cls}" onclick="window.__admhq.switchTab('${a.tab}');return false;" href="#">${a.icon} ${a.text}</a>`).join('') ||
            '<div class="hq-alert ha-g">✅ All systems normal</div>'
        );

        this.renderTab(this.activeTab);
    }

    renderTab(n) {
        const m = {
            overview:     () => this.renderOverview(),
            requests:     () => this.renderRequests(),
            fleet:        () => this.renderFleet(),
            facilities:   () => this.renderFacilities(),
            utilities:    () => this.renderUtilities(),
            security:     () => this.renderSecurity(),
            contracts:    () => this.renderContracts(),
            compliance:   () => this.renderCompliance(),
            hse:          () => this.renderHSE(),
            messaging:    () => this.renderMessaging(),
            intelligence: () => this.renderIntelligence(),
        };
        if (m[n]) m[n]();
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  TAB: OVERVIEW — spend correctly sourced
    // ═══════════════════════════════════════════════════════════════════════════
    renderOverview() {
        const today   = frappe.datetime.get_today();
        const spend   = this.computeSpend();
        const openReqs= this.requests.filter(r => !['Completed','Closed','Rejected','Cancelled'].includes(r.status));
        const availVeh= this.vehicles.filter(v => v.status === 'Available');
        const visitToday = this.visitors.filter(v => v.visit_date === today);
        const openInc = this.incidents.filter(i => !['Resolved','Closed'].includes(i.status));
        const expiredComp= this.compliance.filter(c => c.status === 'Expired');
        const expiringCon= this.contracts.filter(c => { const d=this.daysLeft(c.end_date); return d!==null&&d>=0&&d<=60; });
        const unread  = this.waConvos.reduce((s,c)=>s+this.n(c.unread_count),0);
        const genHrsMTD = this.genLogs
            .filter(g=>g.log_date&&g.log_date.substring(0,7)===today.substring(0,7))
            .reduce((s,g)=>s+this.flt(g.run_hours),0);

        // Request activity last 7 days
        const last7 = Array.from({length:7},(_,i)=>{const d=new Date();d.setDate(d.getDate()-(6-i));return d.toISOString().substring(0,10);});
        const reqDay = last7.map(d=>this.requests.filter(r=>r.request_date===d).length);

        // SPEND BREAKDOWN — each slice = a specific DocType SUM
        const spendSlices = [
            { label:'Utilities (EKEDC/water/ISP)', v: spend.utilCostMTD,            src:'Utility Consumption · total_bill',  col:'#0284C7' },
            { label:'Generator diesel',             v: spend.genCostMTD,             src:'Generator Log · fuel_cost',         col:'#F59E0B' },
            { label:'Fleet fuel (pump/station)',     v: spend.fleetFuelMTD,           src:'Fuel Issue · total_cost',           col:'#F97316' },
            { label:'Facility maintenance',         v: spend.maintCostMTD,           src:'Maintenance Work Order · actual_cost',col:'#8B5CF6' },
            { label:'Vendor contracts (monthly)',   v: spend.activeContractMonthly,  src:'Service Contract · value÷12',       col:'#10B981' },
            { label:'Admin operations',             v: spend.adminOpsMTD,            src:'Admin Request · actual_cost',       col:'#06B6D4' },
        ].filter(x => x.v > 0);

        $('#hq-panel-overview').html(`
            <div class="hq-kpis">
                ${this.kpi('📋','','Open requests', openReqs.length, `${this.requests.filter(r=>r.sla_breached==1).length} SLA breached`, '/app/administrative-request')}
                ${this.kpi('🚗','','Available vehicles', `${availVeh.length}/${this.vehicles.length}`, 'fleet availability')}
                ${this.kpi('💰','','Total spend MTD', this.fmt(spend.totalMTD), '6 cost categories')}
                ${this.kpi('⛽','','Gen. runtime MTD', genHrsMTD.toFixed(0)+'h', this.fmt(spend.genCostMTD) + ' diesel')}
                ${this.kpi('📑','','Expiring contracts', expiringCon.length, 'within 60 days')}
                ${this.kpi('🎖','','Compliance risk', expiredComp.length, 'items expired')}
                ${this.kpi('🛡','','Open incidents', openInc.length, 'security incidents')}
                ${this.kpi('💬','','Unread messages', unread, `${visitToday.length} visitors today`)}
            </div>

            <div class="hq-g21">
                <div class="hq-card">
                    <div class="hq-ch"><div class="hq-ct">📈 Request activity — last 7 days</div></div>
                    <div class="hq-cb"><div style="height:200px;position:relative"><canvas id="hq-ch-act" aria-label="Request activity bar chart">Daily admin request volumes.</canvas></div></div>
                </div>
                <div class="hq-card">
                    <div class="hq-ch"><div class="hq-ct">💬 Messaging snapshot</div><button class="hq-btn hb-v" onclick="window.__admhq.switchTab('messaging')">Open inbox →</button></div>
                    <div class="hq-cb">
                        <div class="hq-stat-grid" style="margin-bottom:12px">
                            <div class="hq-stat"><div class="hq-stat-v">${this.waConvos.length}</div><div class="hq-stat-l">WA threads</div></div>
                            <div class="hq-stat"><div class="hq-stat-v" style="color:var(--red)">${unread}</div><div class="hq-stat-l">Unread</div></div>
                            <div class="hq-stat"><div class="hq-stat-v">${this.blasts.filter(b=>b.status==='Sent').length}</div><div class="hq-stat-l">Blasts sent</div></div>
                        </div>
                        ${this.waConvos.slice(0,4).map(c=>`
                        <div class="hq-li" onclick="window.__admhq.switchTab('messaging');window.__admhq._msgThread='${c.name}'">
                            <div class="hq-li-l">
                                <div class="hq-li-t">${c.contact_display_name||c.phone_number}</div>
                                <div class="hq-li-s">${c.last_message_preview||'—'}</div>
                            </div>
                            ${c.unread_count > 0 ? this.badge(c.unread_count,'bg-p') : this.sbadge(c.status)}
                        </div>`).join('') || '<div style="color:var(--tx3);font-size:12px">No WhatsApp conversations</div>'}
                    </div>
                </div>
            </div>

            <div class="hq-g2">
                <div class="hq-card">
                    <div class="hq-ch">
                        <div class="hq-ct">💰 Admin spend breakdown — MTD</div>
                        <span style="font-size:11px;color:var(--tx3)">Each slice = a real DocType SUM</span>
                    </div>
                    <div class="hq-cb">
                        <div class="hq-g2" style="margin-bottom:0">
                            <div style="position:relative;height:220px"><canvas id="hq-ch-spend" aria-label="Admin spend donut chart">Admin MTD expenditure by category.</canvas></div>
                            <div style="display:flex;flex-direction:column;justify-content:center;gap:6px">
                                ${spendSlices.map(x=>`
                                <div style="display:flex;align-items:center;gap:8px">
                                    <div style="width:10px;height:10px;border-radius:2px;background:${x.col};flex-shrink:0"></div>
                                    <div style="flex:1;min-width:0">
                                        <div style="font-size:11px;font-weight:600;color:var(--tx1);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${x.label}</div>
                                        <div style="font-size:10px;color:var(--tx3)">${x.src}</div>
                                    </div>
                                    <div style="font-size:12px;font-weight:700;color:var(--tx1);white-space:nowrap">${this.fmt(x.v)}</div>
                                </div>`).join('')}
                                <div style="border-top:1px solid var(--brd);padding-top:8px;margin-top:4px;display:flex;justify-content:space-between;font-size:12px">
                                    <span style="font-weight:700;color:var(--tx2)">Total MTD</span>
                                    <span style="font-weight:800;color:var(--pri)">${this.fmt(spend.totalMTD)}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="hq-card">
                    <div class="hq-ch"><div class="hq-ct">🎖 Compliance radar</div><button class="hq-btn hb-ghost" onclick="window.__admhq.switchTab('compliance')">→</button></div>
                    <div class="hq-cb">
                        ${this.compliance.slice(0,6).map(c=>`
                        <div class="hq-li" onclick="frappe.set_route('Form','Compliance Register','${c.name}')">
                            <div class="hq-li-l"><div class="hq-li-t">${c.compliance_item}</div><div class="hq-li-s">${c.compliance_type}</div></div>
                            ${this.dlBadge(c.expiry_date)}
                        </div>`).join('')}
                    </div>
                </div>
            </div>

            <div class="hq-g3">
                <div class="hq-card">
                    <div class="hq-ch"><div class="hq-ct">🚗 Fleet snapshot</div></div>
                    <div class="hq-cb">
                        ${this.vehicles.slice(0,5).map(v=>`
                        <div style="display:flex;align-items:center;gap:9px;padding:7px 0;border-bottom:1px solid var(--brd)" onclick="frappe.set_route('Form','Company Vehicle','${v.name}')">
                            <div style="width:28px;height:28px;border-radius:8px;background:var(--bg2);display:flex;align-items:center;justify-content:center;font-size:13px">${v.vehicle_type==='Bus'?'🚌':v.vehicle_type==='Truck'?'🚛':'🚗'}</div>
                            <div style="flex:1;min-width:0"><div style="font-size:12px;font-weight:600;color:var(--tx1);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${v.vehicle_name||v.plate_number}</div><div style="font-size:10px;color:var(--tx3)">${v.plate_number}</div></div>
                            ${this.sbadge(v.status)}
                        </div>`).join('')}
                    </div>
                </div>
                <div class="hq-card">
                    <div class="hq-ch"><div class="hq-ct">🔴 Urgent requests</div></div>
                    <div class="hq-cb">
                        ${this.requests.filter(r=>['Urgent','High'].includes(r.priority)&&!['Completed','Closed'].includes(r.status)).slice(0,5).map(r=>`
                        <div class="hq-li" onclick="frappe.set_route('Form','Administrative Request','${r.name}')">
                            <div class="hq-li-l"><div class="hq-li-t">${r.request_title||r.name}</div><div class="hq-li-s">${r.request_type} · ${r.request_age_days||0}d old</div></div>
                            ${this.priB(r.priority)}
                        </div>`).join('') || '<div style="color:var(--tx3);font-size:12px;padding:8px 0">No urgent open requests 🎉</div>'}
                    </div>
                </div>
                <div class="hq-card">
                    <div class="hq-ch"><div class="hq-ct">🛡 Security today</div></div>
                    <div class="hq-cb">
                        <div class="hq-stat-grid" style="margin-bottom:10px">
                            <div class="hq-stat"><div class="hq-stat-v">${this.visitors.filter(v=>v.visit_date===today).length}</div><div class="hq-stat-l">Visitors</div></div>
                            <div class="hq-stat"><div class="hq-stat-v" style="color:var(--red)">${this.incidents.filter(i=>!['Resolved','Closed'].includes(i.status)).length}</div><div class="hq-stat-l">Incidents</div></div>
                        </div>
                        ${this.incidents.filter(i=>!['Resolved','Closed'].includes(i.status)).slice(0,3).map(i=>`
                        <div class="hq-abox ${['Severe','Critical'].includes(i.severity)?'ab-r':'ab-a'}" onclick="frappe.set_route('Form','Security Incident','${i.name}')">
                            <div><div class="at">${i.incident_type}</div><div class="as">${i.facility||''} · ${i.severity}</div></div>
                        </div>`).join('') || '<div style="color:var(--tx3);font-size:12px">No open incidents ✅</div>'}
                    </div>
                </div>
            </div>
        `);

        // Activity chart
        this.makeChart('hq-ch-act', { type:'bar', data:{ labels:last7.map(d=>new Date(d).toLocaleDateString('en-NG',{weekday:'short',day:'numeric'})), datasets:[{label:'Requests',data:reqDay,backgroundColor:'#0284C7',borderRadius:5}] }, options:{ responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{color:'rgba(255,255,255,.04)'},ticks:{color:'#94A3B8',font:{size:10}}},y:{grid:{color:'rgba(255,255,255,.04)'},ticks:{color:'#94A3B8',font:{size:10},stepSize:1}}} } });

        // Spend donut
        if (spendSlices.length) {
            this.makeChart('hq-ch-spend', { type:'doughnut', data:{ labels:spendSlices.map(x=>x.label), datasets:[{data:spendSlices.map(x=>x.v),backgroundColor:spendSlices.map(x=>x.col),borderWidth:0}] }, options:{ responsive:true,maintainAspectRatio:false,cutout:'68%',plugins:{legend:{display:false}} } });
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  TAB: MESSAGING — the centrepiece new feature
    // ═══════════════════════════════════════════════════════════════════════════
    renderMessaging() {
        const unread      = this.waConvos.reduce((s,c)=>s+this.n(c.unread_count),0);
        const openConvos  = this.waConvos.filter(c=>c.status==='Open').length;
        const resolvedMTD = this.waConvos.filter(c=>c.status==='Resolved').length;
        const internalCount= this.internalChats.filter(c=>c.is_active).length;
        const blastsSent  = this.blasts.filter(b=>b.status==='Sent').length;
        const blastReach  = this.blasts.reduce((s,b)=>s+this.n(b.sent_count),0);

        // Channel distribution
        const chanCounts = {};
        this.waConvos.forEach(c=>{ chanCounts[c.channel_type||'WhatsApp']=(chanCounts[c.channel_type||'WhatsApp']||0)+1; });

        const chanIcon = { WhatsApp:'💬', SMS:'📱', Email:'📧' };
        const chanCls  = { WhatsApp:'chan-wa', SMS:'chan-sms', Email:'chan-email' };

        // Active thread — first unread or first in list
        const activeConvo = this._msgThread
            ? this.waConvos.find(c=>c.name===this._msgThread) || this.waConvos[0]
            : this.waConvos.find(c=>c.unread_count>0) || this.waConvos[0];

        const threadMsgs = activeConvo
            ? this.waMessages.filter(m=>m.conversation===activeConvo.name).reverse().slice(-30)
            : [];

        // Avatar color by name hash
        const avatarColor = (name='') => {
            const colors = ['#0284C7','#10B981','#F59E0B','#8B5CF6','#EF4444','#06B6D4','#EC4899'];
            let h = 0; for (let c of name) h = (h*31+c.charCodeAt(0))%colors.length;
            return colors[Math.abs(h)];
        };

        const initials = (name='') => name.split(' ').map(w=>w[0]||'').slice(0,2).join('').toUpperCase() || '?';

        $('#hq-panel-messaging').html(`
            <div class="hq-kpis">
                ${this.kpi('💬','','WA conversations', this.waConvos.length, `${openConvos} open`)}
                ${this.kpi('🔴','','Unread', unread, 'awaiting reply')}
                ${this.kpi('✅','','Resolved MTD', resolvedMTD, 'conversations closed')}
                ${this.kpi('🏠','','Internal chats', internalCount, 'active team chats')}
                ${this.kpi('📣','','Blasts sent', blastsSent, `${blastReach.toLocaleString()} total delivered`)}
                ${this.kpi('📋','','Templates', this.waTemplates.filter(t=>t.is_active).length, 'active templates')}
            </div>

            <!-- MAIN MESSAGING LAYOUT: conversation list + thread -->
            <div class="hq-card" style="margin-bottom:14px">
                <div class="hq-ch">
                    <div class="hq-ct">💬 WhatsApp Conversations</div>
                    <div class="hq-acts">
                        <select class="hq-btn hb-ghost" id="hq-msg-status-f" onchange="window.__admhq.filterConvos()" style="cursor:pointer">
                            <option value="">All statuses</option>
                            <option value="Open">Open</option>
                            <option value="Resolved">Resolved</option>
                            <option value="Pending">Pending</option>
                        </select>
                        <select class="hq-btn hb-ghost" id="hq-msg-chan-f" onchange="window.__admhq.filterConvos()" style="cursor:pointer">
                            <option value="">All channels</option>
                            <option value="WhatsApp">WhatsApp</option>
                            <option value="SMS">SMS</option>
                            <option value="Email">Email</option>
                        </select>
                        <button class="hq-btn hb-g" onclick="frappe.new_doc('WA Conversation')">+ New</button>
                    </div>
                </div>
                <div class="hq-msg-layout">
                    <!-- LEFT: conversation list -->
                    <div class="hq-convo-list" id="hq-convo-list">
                        ${this.convoListHTML(this.waConvos, activeConvo?.name)}
                    </div>
                    <!-- RIGHT: message thread -->
                    <div class="hq-msg-pane">
                        ${activeConvo ? `
                        <div class="hq-msg-header">
                            <div style="width:36px;height:36px;border-radius:50%;background:${avatarColor(activeConvo.contact_display_name||activeConvo.phone_number)};display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;color:#fff;flex-shrink:0">
                                ${initials(activeConvo.contact_display_name||activeConvo.phone_number)}
                            </div>
                            <div style="flex:1;min-width:0">
                                <div class="hq-msg-title">${activeConvo.contact_display_name||activeConvo.phone_number}</div>
                                <div class="hq-msg-sub">${activeConvo.phone_number||''} · ${activeConvo.channel_type||'WhatsApp'} · ${activeConvo.total_messages||0} messages</div>
                            </div>
                            <div class="hq-acts">
                                <span class="hq-chan-pill ${chanCls[activeConvo.channel_type||'WhatsApp']||'chan-wa'}">${chanIcon[activeConvo.channel_type||'WhatsApp']||'💬'} ${activeConvo.channel_type||'WhatsApp'}</span>
                                ${this.sbadge(activeConvo.status)}
                                <button class="hq-btn hb-ghost" onclick="frappe.set_route('Form','WA Conversation','${activeConvo.name}')">Open form →</button>
                            </div>
                        </div>
                        <div class="hq-msg-body" id="hq-msg-body">
                            ${threadMsgs.length ? threadMsgs.map(m => {
                                const isOut = m.direction === 'Outbound';
                                const ac = avatarColor(isOut ? 'Me' : (activeConvo.contact_display_name||activeConvo.phone_number));
                                const ini = initials(isOut ? 'Me' : (activeConvo.contact_display_name||activeConvo.phone_number));
                                const ts = m.timestamp ? new Date(m.timestamp).toLocaleTimeString('en-NG',{hour:'2-digit',minute:'2-digit',hour12:true}) : '';
                                return `<div class="hq-bubble-wrap ${isOut?'out':''}">
                                    <div class="hq-avatar-s" style="background:${ac}">${ini}</div>
                                    <div>
                                        <div class="hq-bubble ${isOut?'out':'in'}">${m.body||'[media]'}</div>
                                        <div class="hq-bubble-time ${isOut?'':''}">
                                            ${ts} ${isOut ? (m.delivery_status==='Read'?'✓✓':m.delivery_status==='Delivered'?'✓':'') : ''}
                                        </div>
                                    </div>
                                </div>`;
                            }).join('') : `<div class="hq-msg-empty"><div class="hq-msg-empty-icon">💬</div><div style="font-size:13px;font-weight:600;color:var(--tx2)">No messages loaded</div><div style="font-size:12px">Messages load from WA Message DocType</div></div>`}
                        </div>
                        <div class="hq-msg-footer">
                            <div class="hq-msg-input-row">
                                <textarea class="hq-msg-ta" id="hq-msg-input" placeholder="Type a message…" rows="1" onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();window.__admhq.sendMessage('${activeConvo.name}');}"></textarea>
                                <button class="hq-msg-send" onclick="window.__admhq.sendMessage('${activeConvo.name}')" title="Send">➤</button>
                            </div>
                            <div style="display:flex;gap:6px;margin-top:7px;flex-wrap:wrap">
                                <button class="hq-btn hb-ghost" onclick="window.__admhq.resolveConvo('${activeConvo.name}')">✅ Resolve</button>
                                <button class="hq-btn hb-ghost" onclick="frappe.new_doc('WA Message',{conversation:'${activeConvo.name}',direction:'Outbound'})">📎 Send Media</button>
                                ${this.waTemplates.filter(t=>t.is_active).length ? `<button class="hq-btn hb-v" onclick="window.__admhq.openTemplatePicker('${activeConvo.name}')">📋 Template</button>` : ''}
                            </div>
                        </div>
                        ` : `<div class="hq-msg-empty"><div class="hq-msg-empty-icon">💬</div><div style="font-size:13px;font-weight:600;color:var(--tx2)">No conversations yet</div><div style="font-size:12px">WA Conversations will appear here</div></div>`}
                    </div>
                </div>
            </div>

            <div class="hq-g3">
                <!-- Internal team chats -->
                <div class="hq-card">
                    <div class="hq-ch"><div class="hq-ct">🏠 Internal team chats</div><button class="hq-btn hb-solid" onclick="frappe.new_doc('WA Internal Chat')">+ New Chat</button></div>
                    <div class="hq-cb">
                        ${this.internalChats.slice(0,6).map(c=>`
                        <div class="hq-li" onclick="frappe.set_route('Form','WA Internal Chat','${c.name}')">
                            <div class="hq-li-l">
                                <div class="hq-li-t">${c.chat_name}</div>
                                <div class="hq-li-s">${c.last_message_preview||'No messages yet'} · ${c.member_count||0} members</div>
                            </div>
                            <span class="hq-chan-pill chan-int">${c.chat_type==='Group'?'👥':'💬'} ${c.chat_type||'Direct'}</span>
                        </div>`).join('') || '<div style="color:var(--tx3);font-size:12px">No internal chats found</div>'}
                    </div>
                </div>

                <!-- Message blasts -->
                <div class="hq-card">
                    <div class="hq-ch"><div class="hq-ct">📣 Message blasts</div><button class="hq-btn hb-solid" onclick="frappe.new_doc('Message Blast')">+ New Blast</button></div>
                    <div class="hq-cb" style="padding:10px 14px">
                        ${this.blasts.slice(0,5).map(b=>`
                        <div class="hq-blast-card" onclick="frappe.set_route('Form','Message Blast','${b.name}')">
                            <div class="hq-blast-title">${b.subject||b.name}</div>
                            <div class="hq-blast-meta">${b.message_type||''} · ${b.audience_group||''} · ${b.date||''}</div>
                            <div class="hq-blast-stats">
                                <div class="hq-blast-stat" style="color:var(--grn)">✓ ${b.sent_count||0} sent</div>
                                <div class="hq-blast-stat" style="color:var(--red)">✗ ${b.failed_count||0} failed</div>
                                <div class="hq-blast-stat" style="color:var(--tx3)">⏳ ${b.pending_count||0} pending</div>
                                <div class="hq-blast-stat" style="color:var(--tx3)">${b.total_recipients||0} total</div>
                            </div>
                        </div>`).join('') || '<div style="color:var(--tx3);font-size:12px">No message blasts</div>'}
                    </div>
                </div>

                <!-- Channel stats + templates -->
                <div class="hq-card">
                    <div class="hq-ch"><div class="hq-ct">📊 Channels &amp; templates</div></div>
                    <div class="hq-cb">
                        <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--tx3);margin-bottom:9px">Channel distribution</div>
                        ${Object.entries(chanCounts).map(([ch,n])=>`
                        <div class="hq-bar-row">
                            <div class="hq-bar-lbl"><span class="hq-chan-pill ${chanCls[ch]||'chan-wa'}">${chanIcon[ch]||'💬'} ${ch}</span></div>
                            <div class="hq-bar"><div class="hq-bar-fill" style="width:${Math.round(n/Math.max(...Object.values(chanCounts))*100)}%;background:var(--pri)"></div></div>
                            <div class="hq-bar-val">${n}</div>
                        </div>`).join('') || '<div style="color:var(--tx3);font-size:12px;margin-bottom:12px">No conversations yet</div>'}
                        <div class="hq-hr"></div>
                        <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--tx3);margin-bottom:9px">WA templates</div>
                        ${this.waTemplates.slice(0,5).map(t=>`
                        <div class="hq-li" onclick="frappe.set_route('Form','WA Template','${t.name}')">
                            <div class="hq-li-l"><div class="hq-li-t">${t.template_name}</div><div class="hq-li-s">${t.category||''} · ${t.language_code||''}</div></div>
                            ${this.sbadge(t.status||'Active')}
                        </div>`).join('') || '<div style="color:var(--tx3);font-size:12px">No templates</div>'}
                        <button class="hq-btn hb-solid" style="margin-top:10px;width:100%;justify-content:center" onclick="frappe.new_doc('WA Template')">+ New Template</button>
                    </div>
                </div>
            </div>
        `);

        // Auto-scroll chat to bottom
        setTimeout(() => {
            const body = document.getElementById('hq-msg-body');
            if (body) body.scrollTop = body.scrollHeight;
        }, 100);
    }

    convoListHTML(convos, activeId) {
        const chanCls = { WhatsApp:'chan-wa', SMS:'chan-sms', Email:'chan-email' };
        const chanIcon= { WhatsApp:'💬', SMS:'📱', Email:'📧' };
        if (!convos.length) return '<div style="padding:20px;text-align:center;color:var(--tx3);font-size:12px">No conversations found</div>';
        return convos.map(c => {
            const isActive = c.name === activeId;
            const ts = c.last_message_at ? new Date(c.last_message_at).toLocaleTimeString('en-NG',{hour:'2-digit',minute:'2-digit',hour12:true}) : '';
            return `<div class="hq-convo-item ${isActive?'active':''}" onclick="window.__admhq.openConvo('${c.name}')">
                <div class="hq-convo-meta">
                    <span class="hq-convo-name">${c.contact_display_name||c.phone_number}</span>
                    <span class="hq-convo-time">${ts}</span>
                </div>
                <div style="display:flex;align-items:center;gap:5px;margin-bottom:3px">
                    <span class="hq-chan-pill ${chanCls[c.channel_type||'WhatsApp']||'chan-wa'}" style="font-size:8px;padding:1px 5px">${chanIcon[c.channel_type||'WhatsApp']||'💬'} ${c.channel_type||'WA'}</span>
                    ${c.unread_count > 0 ? `<span class="hq-unread">${c.unread_count}</span>` : ''}
                </div>
                <div class="hq-convo-preview">${c.last_message_preview||'No messages'}</div>
            </div>`;
        }).join('');
    }

    openConvo(name) {
        this._msgThread = name;
        this.renderMessaging();
    }

    filterConvos() {
        const sF = document.getElementById('hq-msg-status-f')?.value || '';
        const cF = document.getElementById('hq-msg-chan-f')?.value || '';
        let filtered = this.waConvos;
        if (sF) filtered = filtered.filter(c => c.status === sF);
        if (cF) filtered = filtered.filter(c => (c.channel_type||'WhatsApp') === cF);
        const el = document.getElementById('hq-convo-list');
        if (el) el.innerHTML = this.convoListHTML(filtered, this._msgThread);
    }

    async sendMessage(convoName) {
        const input = document.getElementById('hq-msg-input');
        const body = (input?.value || '').trim();
        if (!body) return;

        input.value = '';
        input.style.height = '';

        // Create a WA Message record via frappe.client.insert
        try {
            await frappe.call({
                method: 'frappe.client.insert',
                args: {
                    doc: {
                        doctype: 'WA Message',
                        conversation: convoName,
                        direction: 'Outbound',
                        message_type: 'Text',
                        body: body,
                        timestamp: frappe.datetime.now_datetime(),
                        delivery_status: 'Sent',
                        sender_user: frappe.session.user,
                    }
                }
            });

            // Update local state optimistically and refresh thread
            this.waMessages.unshift({
                name: 'new-' + Date.now(),
                conversation: convoName,
                direction: 'Outbound',
                body: body,
                timestamp: frappe.datetime.now_datetime(),
                delivery_status: 'Sent',
            });
            this.renderMessaging();
            frappe.show_alert({ message: 'Message saved', indicator: 'green' });
        } catch(e) {
            frappe.show_alert({ message: 'Could not save message: ' + (e.message||e), indicator: 'red' });
        }
    }

    async resolveConvo(convoName) {
        try {
            await frappe.call({
                method: 'frappe.client.set_value',
                args: { doctype: 'WA Conversation', name: convoName, fieldname: 'status', value: 'Resolved' }
            });
            const c = this.waConvos.find(x => x.name === convoName);
            if (c) c.status = 'Resolved';
            this.renderMessaging();
            frappe.show_alert({ message: 'Conversation resolved', indicator: 'green' });
        } catch(e) {
            frappe.show_alert({ message: 'Could not resolve: ' + (e.message||e), indicator: 'red' });
        }
    }

    openTemplatePicker(convoName) {
        const active = this.waTemplates.filter(t=>t.is_active);
        if (!active.length) { frappe.msgprint('No active templates found.'); return; }
        const html = active.map(t=>`
            <div onclick="window.__admhq._useTemplate('${convoName}','${t.name}');if(cur_dialog)cur_dialog.hide();"
                 style="padding:10px 13px;border-radius:9px;border:1px solid var(--brd);cursor:pointer;margin-bottom:7px;transition:background .15s"
                 onmouseover="this.style.background='rgba(2,132,199,.08)'" onmouseout="this.style.background=''">
                <div style="font-size:12px;font-weight:700;color:var(--tx1)">${t.template_name}</div>
                <div style="font-size:10px;color:var(--tx3)">${t.category||''} · ${t.language_code||''}</div>
            </div>`).join('');
        new frappe.ui.Dialog({ title:'📋 Choose Template', fields:[{ fieldtype:'HTML', options: html }] }).show();
    }

    _useTemplate(convoName, templateName) {
        const input = document.getElementById('hq-msg-input');
        if (input) {
            input.value = `[Template: ${templateName}] `;
            input.focus();
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  TABS: REQUESTS (keep from previous — shortened for space)
    // ═══════════════════════════════════════════════════════════════════════════
    renderRequests() {
        const open = this.requests.filter(r=>!['Completed','Closed','Rejected','Cancelled'].includes(r.status));
        const breached = this.requests.filter(r=>r.sla_breached==1);
        const byType = {}; this.requests.forEach(r=>{byType[r.request_type]=(byType[r.request_type]||0)+1;});
        const typeKeys = Object.keys(byType).sort((a,b)=>byType[b]-byType[a]).slice(0,8);
        const statusCounts = ['Draft','Submitted','Approved','In Progress','Completed','Rejected'];

        $('#hq-panel-requests').html(`
            <div class="hq-kpis">
                ${this.kpi('📋','','Total',this.requests.length,'all requests')}
                ${this.kpi('🔓','','Open',open.length,`${this.requests.filter(r=>r.status==='Submitted').length} awaiting approval`)}
                ${this.kpi('⏱','','SLA breaches',breached.length,'require action')}
                ${this.kpi('🚨','','Urgent',this.requests.filter(r=>r.priority==='Urgent').length,'priority urgent')}
                ${this.kpi('✅','','Completed',this.requests.filter(r=>r.status==='Completed').length,'fully resolved')}
                ${this.kpi('💰','','Total actual cost',this.fmt(this.requests.reduce((s,r)=>s+this.flt(r.actual_cost),0)),'completed requests')}
            </div>
            <div class="hq-g21">
                <div class="hq-card">
                    <div class="hq-ch">
                        <div class="hq-ct">📋 All requests</div>
                        <div class="hq-acts">
                            <select class="hq-btn hb-ghost" id="hq-req-sf" onchange="window.__admhq.filterReqs()" style="cursor:pointer">
                                <option value="">All statuses</option>
                                ${statusCounts.map(s=>`<option>${s}</option>`).join('')}
                            </select>
                            <select class="hq-btn hb-ghost" id="hq-req-tf" onchange="window.__admhq.filterReqs()" style="cursor:pointer">
                                <option value="">All types</option>
                                ${typeKeys.map(t=>`<option>${t}</option>`).join('')}
                            </select>
                            <button class="hq-btn hb-solid" onclick="frappe.new_doc('Administrative Request')">+ New</button>
                        </div>
                    </div>
                    <div class="hq-tbl-w"><table class="hq-tbl"><thead><tr><th>Title</th><th>Type</th><th>Priority</th><th>Status</th><th>Age</th><th>Cost</th><th>SLA</th></tr></thead>
                    <tbody id="hq-req-tbody">${this.reqRows(this.requests)}</tbody></table></div>
                </div>
                <div>
                    <div class="hq-card">
                        <div class="hq-ch"><div class="hq-ct">📊 By type</div></div>
                        <div class="hq-cb"><div style="height:200px;position:relative"><canvas id="hq-ch-reqt" aria-label="Requests by type">Request types.</canvas></div></div>
                    </div>
                    <div class="hq-card" style="margin-top:13px">
                        <div class="hq-ch"><div class="hq-ct">🔄 Status pipeline</div></div>
                        <div class="hq-cb">
                            ${statusCounts.map((s,i)=>{ const c=this.requests.filter(r=>r.status===s).length; const pct=this.requests.length?Math.round(c/this.requests.length*100):0; const cols=['#94A3B8','#0284C7','#38BDF8','#F59E0B','#10B981','#EF4444']; return `<div class="hq-bar-row"><div class="hq-bar-lbl" style="width:100px">${s}</div><div class="hq-bar"><div class="hq-bar-fill" style="width:${pct}%;background:${cols[i]}"></div></div><div class="hq-bar-val">${c}</div></div>`; }).join('')}
                        </div>
                    </div>
                </div>
            </div>`);

        this.makeChart('hq-ch-reqt', { type:'bar', data:{ labels:typeKeys, datasets:[{label:'Requests',data:typeKeys.map(k=>byType[k]),backgroundColor:'#0284C7',borderRadius:4}] }, options:{ indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{color:'rgba(255,255,255,.04)'},ticks:{color:'#94A3B8',font:{size:10}}},y:{grid:{display:false},ticks:{color:'#94A3B8',font:{size:10}}}} } });
    }

    reqRows(reqs) {
        return reqs.map(r=>`<tr onclick="frappe.set_route('Form','Administrative Request','${r.name}')">
            <td style="font-weight:600;color:var(--tx1);max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${r.request_title||r.name}</td>
            <td>${r.request_type||''}</td>
            <td>${this.priB(r.priority)}</td>
            <td>${this.sbadge(r.status)}</td>
            <td style="font-family:'JetBrains Mono',monospace;font-size:10px">${r.request_age_days||0}d</td>
            <td>${r.actual_cost?this.fmt(r.actual_cost):'—'}</td>
            <td>${r.sla_breached==1?this.badge('Breached','bg-r'):this.badge('OK','bg-g')}</td>
        </tr>`).join('') || '<tr><td colspan="7" style="text-align:center;color:var(--tx3);padding:20px">No requests</td></tr>';
    }

    filterReqs() {
        const sf=document.getElementById('hq-req-sf')?.value||'';
        const tf=document.getElementById('hq-req-tf')?.value||'';
        let f=this.requests;
        if(sf) f=f.filter(r=>r.status===sf);
        if(tf) f=f.filter(r=>r.request_type===tf);
        document.getElementById('hq-req-tbody').innerHTML=this.reqRows(f);
    }

    // ── FLEET, FACILITIES, UTILITIES, SECURITY, CONTRACTS, COMPLIANCE, HSE ────
    // These are identical in logic to the previous admin_dashboard.js —
    // re-using the same patterns with hq- prefixes instead of ad-

    renderFleet() {
        const available=this.vehicles.filter(v=>v.status==='Available');
        const grounded =this.vehicles.filter(v=>v.status==='Grounded');
        const fuelYTD  =this.vehicles.reduce((s,v)=>s+this.flt(v.fuel_cost_ytd),0);
        const kmYTD    =this.vehicles.reduce((s,v)=>s+this.flt(v.total_km_ytd),0);
        const monthFuel=this.fuelIssues.filter(f=>f.issue_date&&f.issue_date.substring(0,7)===frappe.datetime.get_today().substring(0,7)).reduce((s,f)=>s+this.flt(f.total_cost),0);

        $('#hq-panel-fleet').html(`
            <div class="hq-kpis">
                ${this.kpi('🟢','','Available',available.length,`of ${this.vehicles.length}`)}
                ${this.kpi('🔵','','In Use',this.vehicles.filter(v=>v.status==='In Use').length,'deployed')}
                ${this.kpi('🟠','','Maintenance',this.vehicles.filter(v=>v.status==='Under Maintenance').length,'under repair')}
                ${this.kpi('🔴','','Grounded',grounded.length,'doc issues')}
                ${this.kpi('⛽','','Fuel YTD',this.fmt(fuelYTD),this.fmt(monthFuel)+' MTD')}
                ${this.kpi('🛣','','KM YTD',Math.round(kmYTD).toLocaleString()+'km','all vehicles')}
            </div>
            <div class="hq-card">
                <div class="hq-ch"><div class="hq-ct">🚗 Fleet register</div>
                    <div class="hq-acts">
                        <select class="hq-btn hb-ghost" id="hq-veh-f" onchange="window.__admhq.filterVehs()" style="cursor:pointer">
                            <option value="">All</option><option>Available</option><option>In Use</option><option>Under Maintenance</option><option>Grounded</option>
                        </select>
                        <button class="hq-btn hb-solid" onclick="frappe.new_doc('Company Vehicle')">+ Add</button>
                    </div>
                </div>
                <div class="hq-tbl-w"><table class="hq-tbl"><thead><tr><th>Vehicle</th><th>Plate</th><th>Type</th><th>Driver</th><th>Status</th><th>Odometer</th><th>Fuel YTD</th><th>Cost/KM</th><th>Insurance</th></tr></thead>
                <tbody id="hq-veh-tbody">${this.vehRows(this.vehicles)}</tbody></table></div>
            </div>
            <div class="hq-g2">
                <div class="hq-card">
                    <div class="hq-ch"><div class="hq-ct">🗓 Recent trips</div><button class="hq-btn hb-solid" onclick="frappe.new_doc('Vehicle Trip Log')">+ Log Trip</button></div>
                    <div class="hq-tbl-w"><table class="hq-tbl"><thead><tr><th>Date</th><th>Vehicle</th><th>Driver</th><th>Purpose</th><th>KM</th><th>Fuel Cost</th></tr></thead>
                    <tbody>${this.tripLogs.slice(0,10).map(t=>`<tr onclick="frappe.set_route('Form','Vehicle Trip Log','${t.name}')"><td style="font-family:'JetBrains Mono',monospace;font-size:10px">${t.trip_date}</td><td style="font-weight:600">${t.vehicle}</td><td style="color:var(--tx3)">${t.driver}</td><td>${t.purpose}</td><td>${this.flt(t.distance_km).toFixed(0)}km</td><td>${this.fmt(t.total_fuel_cost)}</td></tr>`).join('')||'<tr><td colspan="6" style="text-align:center;color:var(--tx3);padding:16px">No trips</td></tr>'}</tbody></table></div>
                </div>
                <div class="hq-card">
                    <div class="hq-ch"><div class="hq-ct">⛽ Fuel issues</div><button class="hq-btn hb-solid" onclick="frappe.new_doc('Fuel Issue')">+ Issue</button></div>
                    <div class="hq-tbl-w"><table class="hq-tbl"><thead><tr><th>Date</th><th>Vehicle</th><th>Litres</th><th>Cost</th></tr></thead>
                    <tbody>${this.fuelIssues.slice(0,10).map(f=>`<tr onclick="frappe.set_route('Form','Fuel Issue','${f.name}')"><td style="font-family:'JetBrains Mono',monospace;font-size:10px">${f.issue_date}</td><td style="font-weight:600">${f.vehicle}</td><td>${this.flt(f.litres_issued).toFixed(1)}L</td><td>${this.fmt(f.total_cost)}</td></tr>`).join('')||'<tr><td colspan="4" style="text-align:center;color:var(--tx3);padding:16px">No fuel issues</td></tr>'}</tbody></table></div>
                </div>
            </div>`);
    }

    vehRows(vehs) {
        return vehs.map(v=>`<tr onclick="frappe.set_route('Form','Company Vehicle','${v.name}')">
            <td style="font-weight:600;color:var(--tx1)">${v.vehicle_name||''}</td>
            <td style="font-family:'JetBrains Mono',monospace;font-size:10px">${v.plate_number}</td>
            <td style="color:var(--tx3)">${v.vehicle_type}</td>
            <td style="color:var(--tx3)">${v.assigned_driver||'—'}</td>
            <td>${this.sbadge(v.status)}</td>
            <td style="font-family:'JetBrains Mono',monospace;font-size:10px">${v.odometer_reading?this.flt(v.odometer_reading).toFixed(0)+'km':'—'}</td>
            <td>${this.fmt(v.fuel_cost_ytd||0)}</td>
            <td style="font-family:'JetBrains Mono',monospace;font-size:10px">${v.cost_per_km?this.fmt(v.cost_per_km)+'/km':'—'}</td>
            <td>${this.dlBadge(v.insurance_expiry)}</td>
        </tr>`).join('')||'<tr><td colspan="9" style="text-align:center;color:var(--tx3);padding:20px">No vehicles</td></tr>';
    }
    filterVehs() { const f=document.getElementById('hq-veh-f')?.value||''; document.getElementById('hq-veh-tbody').innerHTML=this.vehRows(f?this.vehicles.filter(v=>v.status===f):this.vehicles); }

    renderFacilities() {
        const openMaint=this.maintReqs.filter(m=>!['Completed','Closed','Cancelled'].includes(m.status));
        const byCat={}; this.maintReqs.forEach(m=>{byCat[m.maintenance_category]=(byCat[m.maintenance_category]||0)+1;});
        const catKeys=Object.keys(byCat).sort((a,b)=>byCat[b]-byCat[a]).slice(0,7);

        $('#hq-panel-facilities').html(`
            <div class="hq-kpis">
                ${this.kpi('🏗','','Facilities',this.facilities.length,`${this.facilities.filter(f=>f.status==='Active').length} active`)}
                ${this.kpi('🔧','','Open maintenance',openMaint.length,'requests')}
                ${this.kpi('📋','','Work orders',this.workOrders.filter(w=>!['Completed','Cancelled'].includes(w.status)).length,'in progress')}
                ${this.kpi('📅','','Bookings today',this.roomBookings.filter(b=>b.booking_date===frappe.datetime.get_today()).length,'room bookings')}
                ${this.kpi('🚨','','Emergency',openMaint.filter(m=>m.priority==='Emergency').length,'emergency priority')}
                ${this.kpi('💰','','Maint. cost',this.fmt(this.workOrders.reduce((s,w)=>s+this.flt(w.actual_cost),0)),'actual spend')}
            </div>
            <div class="hq-g21">
                <div class="hq-card">
                    <div class="hq-ch"><div class="hq-ct">🔧 Open maintenance requests</div><button class="hq-btn hb-solid" onclick="frappe.new_doc('Facility Maintenance Request')">+ New</button></div>
                    <div class="hq-tbl-w"><table class="hq-tbl"><thead><tr><th>Subject</th><th>Facility</th><th>Category</th><th>Priority</th><th>Status</th><th>Date</th></tr></thead>
                    <tbody>${openMaint.map(m=>`<tr onclick="frappe.set_route('Form','Facility Maintenance Request','${m.name}')"><td style="font-weight:600;color:var(--tx1)">${m.subject||m.name}</td><td style="color:var(--tx3)">${m.facility}</td><td>${m.maintenance_category}</td><td>${this.priB(m.priority)}</td><td>${this.sbadge(m.status)}</td><td style="font-family:'JetBrains Mono',monospace;font-size:10px">${m.report_date}</td></tr>`).join('')||'<tr><td colspan="6" style="text-align:center;color:var(--tx3);padding:20px">No open maintenance 🎉</td></tr>'}</tbody></table></div>
                </div>
                <div class="hq-card">
                    <div class="hq-ch"><div class="hq-ct">📊 By category</div></div>
                    <div class="hq-cb"><div style="height:240px;position:relative"><canvas id="hq-ch-mcat" aria-label="Maintenance by category donut">Maintenance categories.</canvas></div></div>
                </div>
            </div>
            <div class="hq-card">
                <div class="hq-ch"><div class="hq-ct">🏗 Facility overview</div><button class="hq-btn hb-solid" onclick="frappe.new_doc('Facility')">+ Add</button></div>
                <div class="hq-tbl-w"><table class="hq-tbl"><thead><tr><th>Facility</th><th>Type</th><th>Status</th><th>Open Requests</th><th>Maint. Cost</th><th>Util. Cost</th></tr></thead>
                <tbody>${this.facilities.map(f=>`<tr onclick="frappe.set_route('Form','Facility','${f.name}')"><td style="font-weight:600;color:var(--tx1)">${f.facility_name}</td><td style="color:var(--tx3)">${f.facility_type||''}</td><td>${this.sbadge(f.status)}</td><td>${this.n(f.open_maintenance_requests)?this.badge(f.open_maintenance_requests,this.n(f.open_maintenance_requests)>3?'bg-r':'bg-a'):this.badge('0','bg-g')}</td><td>${this.fmt(f.maintenance_cost_ytd||0)}</td><td>${this.fmt(f.utility_cost_ytd||0)}</td></tr>`).join('')||'<tr><td colspan="6" style="text-align:center;color:var(--tx3);padding:20px">No facilities</td></tr>'}</tbody></table></div>
            </div>`);

        if (catKeys.length) this.makeChart('hq-ch-mcat', { type:'doughnut', data:{ labels:catKeys, datasets:[{data:catKeys.map(k=>byCat[k]),backgroundColor:this.colors(),borderWidth:0}] }, options:{ responsive:true,maintainAspectRatio:false,cutout:'65%',plugins:{legend:{display:true,position:'right',labels:{color:'#94A3B8',font:{size:9},boxWidth:9,padding:6}}} } });
    }

    renderUtilities() {
        const today=frappe.datetime.get_today();
        const month=today.substring(0,7);
        const thisMon=this.utilConsumed.filter(u=>u.reading_date&&u.reading_date.substring(0,7)===month);
        const totalBill=thisMon.reduce((s,u)=>s+this.flt(u.total_bill),0);
        const byType={}; thisMon.forEach(u=>{byType[u.utility_type]=(byType[u.utility_type]||0)+this.flt(u.total_bill);});
        const genMon=this.genLogs.filter(g=>g.log_date&&g.log_date.substring(0,7)===month);
        const genHrs=genMon.reduce((s,g)=>s+this.flt(g.run_hours),0);
        const genCost=genMon.reduce((s,g)=>s+this.flt(g.fuel_cost),0);
        const months6=Array.from({length:6},(_,i)=>{const d=new Date();d.setMonth(d.getMonth()-5+i);return d.toISOString().substring(0,7);});
        const m6Totals=months6.map(m=>this.utilConsumed.filter(u=>u.reading_date&&u.reading_date.substring(0,7)===m).reduce((s,u)=>s+this.flt(u.total_bill),0));
        const m6Labels=months6.map(m=>{const d=new Date(m+'-01');return d.toLocaleDateString('en-NG',{month:'short',year:'2-digit'});});
        const utilIcons={'Electricity':'⚡','Water':'💧','Diesel':'🛢','Gas':'🔥','Internet Bandwidth':'📶'};

        $('#hq-panel-utilities').html(`
            <div class="hq-kpis">
                ${this.kpi('💡','','Active meters',this.utilMeters.filter(m=>m.status==='Active').length,'meters')}
                ${this.kpi('💰','','Bill MTD',this.fmt(totalBill+genCost),'utilities + gen')}
                ${this.kpi('⏱','','Gen. hours MTD',genHrs.toFixed(1)+'h','generator runtime')}
                ${this.kpi('🛢','','Gen. cost MTD',this.fmt(genCost),'diesel fuel')}
                ${this.kpi('📈','','Readings MTD',thisMon.length,'logged')}
                ${this.kpi('⚡','','Elec. bill MTD',this.fmt(byType['Electricity']||0),'EKEDC/IKEDC')}
            </div>
            <div class="hq-g21">
                <div class="hq-card">
                    <div class="hq-ch"><div class="hq-ct">📈 Spend trend — 6 months</div></div>
                    <div class="hq-cb"><div style="height:220px;position:relative"><canvas id="hq-ch-util" aria-label="Utility spend 6-month trend">Monthly utility costs.</canvas></div></div>
                </div>
                <div class="hq-card">
                    <div class="hq-ch"><div class="hq-ct">📊 MTD by utility type</div></div>
                    <div class="hq-cb">
                        ${Object.entries(byType).map(([t,v])=>{const tot=Object.values(byType).reduce((a,b)=>a+b,0)||1;const pct=Math.round(v/tot*100);const col={'Electricity':'#F59E0B','Water':'#0EA5E9','Diesel':'#EF4444','Gas':'#F97316','Internet Bandwidth':'#8B5CF6'}[t]||'#94A3B8'; return `<div class="hq-bar-row"><div class="hq-bar-lbl">${utilIcons[t]||'⚡'} ${t}</div><div class="hq-bar"><div class="hq-bar-fill" style="width:${pct}%;background:${col}"></div></div><div class="hq-bar-val">${this.fmt(v)}</div></div>`;}).join('')||'<div style="color:var(--tx3);font-size:12px">No readings this month</div>'}
                        <div class="hq-hr"></div>
                        <div style="display:flex;justify-content:space-between;font-size:12px;font-weight:700"><span style="color:var(--tx2)">Total + Gen diesel</span><span style="color:var(--red)">${this.fmt(totalBill+genCost)}</span></div>
                    </div>
                </div>
            </div>
            <div class="hq-card">
                <div class="hq-ch"><div class="hq-ct">🛢 Generator log — recent</div><button class="hq-btn hb-solid" onclick="frappe.new_doc('Generator Log')">+ Log</button></div>
                <div class="hq-tbl-w"><table class="hq-tbl"><thead><tr><th>Date</th><th>Facility</th><th>Hours</th><th>Fuel (L)</th><th>Reason</th><th>Diesel Cost</th></tr></thead>
                <tbody>${this.genLogs.slice(0,12).map(g=>`<tr onclick="frappe.set_route('Form','Generator Log','${g.name}')"><td style="font-family:'JetBrains Mono',monospace;font-size:10px">${g.log_date}</td><td>${g.facility}</td><td>${this.flt(g.run_hours).toFixed(1)}h</td><td>${this.flt(g.fuel_consumed_litres).toFixed(1)}L</td><td style="color:var(--tx3)">${g.reason_for_running||''}</td><td>${this.fmt(g.fuel_cost||0)}</td></tr>`).join('')||'<tr><td colspan="6" style="text-align:center;color:var(--tx3);padding:20px">No generator logs</td></tr>'}</tbody></table></div>
            </div>`);

        this.makeChart('hq-ch-util',{type:'line',data:{labels:m6Labels,datasets:[{label:'Total bill',data:m6Totals,borderColor:'#0284C7',backgroundColor:'rgba(2,132,199,.1)',fill:true,tension:.4,pointBackgroundColor:'#0284C7',pointRadius:4}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{color:'rgba(255,255,255,.04)'},ticks:{color:'#94A3B8',font:{size:10}}},y:{grid:{color:'rgba(255,255,255,.04)'},ticks:{color:'#94A3B8',font:{size:10}}}}}});
    }

    renderSecurity() {
        const today=frappe.datetime.get_today();
        const openInc=this.incidents.filter(i=>!['Resolved','Closed'].includes(i.status));
        const visitToday=this.visitors.filter(v=>v.visit_date===today);
        const last7=Array.from({length:7},(_,i)=>{const d=new Date();d.setDate(d.getDate()-(6-i));return d.toISOString().substring(0,10);});
        const visDay=last7.map(d=>this.visitors.filter(v=>v.visit_date===d).length);
        const bySev=['Minor','Moderate','Severe','Critical'].map(s=>({s,n:this.incidents.filter(i=>i.severity===s).length}));
        const byType={}; this.incidents.forEach(i=>{byType[i.incident_type]=(byType[i.incident_type]||0)+1;});

        $('#hq-panel-security').html(`
            <div class="hq-kpis">
                ${this.kpi('🛡','','Open incidents',openInc.length,'require action')}
                ${this.kpi('⚠️','','Severe+',this.incidents.filter(i=>['Severe','Critical'].includes(i.severity)).length,'severity')}
                ${this.kpi('💰','','Est. loss',this.fmt(this.incidents.reduce((s,i)=>s+this.flt(i.estimated_loss),0)),'all incidents')}
                ${this.kpi('👤','','Visitors today',visitToday.length,`${visitToday.filter(v=>v.status==='Checked In').length} inside`)}
                ${this.kpi('📅','','Visitors MTD',this.visitors.filter(v=>v.visit_date&&v.visit_date.substring(0,7)===today.substring(0,7)).length,'this month')}
                ${this.kpi('✅','','Resolved',this.incidents.filter(i=>i.status==='Resolved').length,'incidents')}
            </div>
            <div class="hq-g21">
                <div class="hq-card">
                    <div class="hq-ch"><div class="hq-ct">🛡 Security incidents</div><button class="hq-btn hb-solid" onclick="frappe.new_doc('Security Incident')">+ Report</button></div>
                    <div class="hq-tbl-w"><table class="hq-tbl"><thead><tr><th>Incident</th><th>Type</th><th>Facility</th><th>Date</th><th>Severity</th><th>Status</th></tr></thead>
                    <tbody>${this.incidents.map(i=>`<tr onclick="frappe.set_route('Form','Security Incident','${i.name}')"><td style="font-weight:600;color:var(--tx1)">${i.incident_title||i.name}</td><td>${i.incident_type}</td><td style="color:var(--tx3)">${i.facility}</td><td style="font-family:'JetBrains Mono',monospace;font-size:10px">${i.incident_date}</td><td>${this.priB(i.severity)}</td><td>${this.sbadge(i.status)}</td></tr>`).join('')||'<tr><td colspan="6" style="text-align:center;color:var(--tx3);padding:20px">No incidents ✅</td></tr>'}</tbody></table></div>
                </div>
                <div>
                    <div class="hq-card">
                        <div class="hq-ch"><div class="hq-ct">📊 By type</div></div>
                        <div class="hq-cb">${Object.entries(byType).sort((a,b)=>b[1]-a[1]).map(([t,n])=>`<div class="hq-bar-row"><div class="hq-bar-lbl" style="font-size:10px">${t}</div><div class="hq-bar"><div class="hq-bar-fill" style="width:${Math.round(n/Math.max(...Object.values(byType))*100)}%;background:var(--red)"></div></div><div class="hq-bar-val">${n}</div></div>`).join('')||'<div style="color:var(--tx3);font-size:12px">No incidents</div>'}</div>
                    </div>
                    <div class="hq-card" style="margin-top:13px">
                        <div class="hq-ch"><div class="hq-ct">👤 Visitor trend — 7d</div></div>
                        <div class="hq-cb"><div style="height:130px;position:relative"><canvas id="hq-ch-vis" aria-label="Visitor trend">Daily visitor count.</canvas></div></div>
                    </div>
                </div>
            </div>
            <div class="hq-g2">
                <div class="hq-card">
                    <div class="hq-ch"><div class="hq-ct">👤 Visitors today</div><button class="hq-btn hb-solid" onclick="frappe.new_doc('Visitor Register')">+ Check In</button></div>
                    <div class="hq-tbl-w"><table class="hq-tbl"><thead><tr><th>Visitor</th><th>Org</th><th>Host</th><th>Purpose</th><th>Check In</th><th>Status</th></tr></thead>
                    <tbody>${visitToday.map(v=>`<tr onclick="frappe.set_route('Form','Visitor Register','${v.name}')"><td style="font-weight:600;color:var(--tx1)">${v.visitor_name}</td><td style="color:var(--tx3)">${v.visitor_company||'—'}</td><td style="color:var(--tx3)">${v.host_employee||''}</td><td>${v.purpose_of_visit||''}</td><td style="font-family:'JetBrains Mono',monospace;font-size:10px">${v.check_in_time||'—'}</td><td>${this.sbadge(v.status)}</td></tr>`).join('')||'<tr><td colspan="6" style="text-align:center;color:var(--tx3);padding:20px">No visitors today</td></tr>'}</tbody></table></div>
                </div>
                <div class="hq-card">
                    <div class="hq-ch"><div class="hq-ct">📊 Severity distribution</div></div>
                    <div class="hq-cb"><div style="height:200px;position:relative"><canvas id="hq-ch-sev" aria-label="Severity pie chart">Incident severity distribution.</canvas></div>
                    <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:8px">${bySev.map((x,i)=>`<span style="display:flex;align-items:center;gap:4px;font-size:11px;color:var(--tx2)"><span style="width:10px;height:10px;border-radius:2px;background:${['#94A3B8','#F59E0B','#EF4444','#7C3AED'][i]};display:inline-block"></span>${x.s}: ${x.n}</span>`).join('')}</div></div>
                </div>
            </div>`);

        this.makeChart('hq-ch-vis',{type:'bar',data:{labels:last7.map(d=>new Date(d).toLocaleDateString('en-NG',{weekday:'short'})),datasets:[{label:'Visitors',data:visDay,backgroundColor:'#0284C7',borderRadius:4}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{display:false},ticks:{color:'#94A3B8',font:{size:9}}},y:{grid:{color:'rgba(255,255,255,.04)'},ticks:{color:'#94A3B8',font:{size:9},stepSize:1}}}}});
        this.makeChart('hq-ch-sev',{type:'pie',data:{labels:bySev.map(x=>x.s),datasets:[{data:bySev.map(x=>x.n),backgroundColor:['#94A3B8','#F59E0B','#EF4444','#7C3AED'],borderWidth:0}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}}}});
    }

    renderContracts() {
        const active=this.contracts.filter(c=>c.status==='Active');
        const expiringIn60=this.contracts.filter(c=>{const d=this.daysLeft(c.end_date);return d!==null&&d>=0&&d<=60;});
        const expired=this.contracts.filter(c=>{const d=this.daysLeft(c.end_date);return d!==null&&d<0;});
        const byType={}; this.contracts.forEach(c=>{byType[c.contract_type]=(byType[c.contract_type]||0)+this.flt(c.contract_value);});

        $('#hq-panel-contracts').html(`
            <div class="hq-kpis">
                ${this.kpi('📑','','Active',active.length,'contracts')}
                ${this.kpi('💰','','Total value',this.fmt(active.reduce((s,c)=>s+this.flt(c.contract_value),0)),'active')}
                ${this.kpi('📅','','Monthly cost',this.fmt(active.reduce((s,c)=>s+this.flt(c.contract_value)/12,0)),'amortised')}
                ${this.kpi('⚠️','','Expiring ≤60d',expiringIn60.length,'need renewal')}
                ${this.kpi('🔴','','Expired',expired.length,'overdue')}
                ${this.kpi('🏢','','Vendors',this.providers.length,'service providers')}
            </div>
            <div class="hq-g21">
                <div class="hq-card">
                    <div class="hq-ch"><div class="hq-ct">📑 Service contracts</div>
                        <div class="hq-acts">
                            <select class="hq-btn hb-ghost" id="hq-con-f" onchange="window.__admhq.filterCons()" style="cursor:pointer">
                                <option value="">All</option><option>Active</option><option>Expired</option><option>Draft</option>
                            </select>
                            <button class="hq-btn hb-solid" onclick="frappe.new_doc('Service Contract')">+ New</button>
                        </div>
                    </div>
                    <div class="hq-tbl-w"><table class="hq-tbl"><thead><tr><th>Contract</th><th>Type</th><th>Vendor</th><th>Value</th><th>Expires</th><th>Status</th></tr></thead>
                    <tbody id="hq-con-tbody">${this.conRows(this.contracts)}</tbody></table></div>
                </div>
                <div>
                    <div class="hq-card">
                        <div class="hq-ch"><div class="hq-ct">📊 Spend by type</div></div>
                        <div class="hq-cb">${Object.entries(byType).sort((a,b)=>b[1]-a[1]).map(([t,v])=>`<div class="hq-bar-row"><div class="hq-bar-lbl" style="font-size:10px;width:110px">${t}</div><div class="hq-bar"><div class="hq-bar-fill" style="width:${Math.round(v/Math.max(...Object.values(byType))*100)}%;background:var(--pri)"></div></div><div class="hq-bar-val" style="font-size:10px">${this.fmt(v)}</div></div>`).join('')||'<div style="color:var(--tx3);font-size:12px">No data</div>'}</div>
                    </div>
                    <div class="hq-card" style="margin-top:13px">
                        <div class="hq-ch"><div class="hq-ct">🏢 Service providers</div><button class="hq-btn hb-solid" onclick="frappe.new_doc('Service Provider')">+ Add</button></div>
                        <div class="hq-cb">${this.providers.slice(0,5).map(p=>`<div class="hq-li" onclick="frappe.set_route('Form','Service Provider','${p.name}')"><div class="hq-li-l"><div class="hq-li-t">${p.provider_name}</div><div class="hq-li-s">${p.service_category} · Score: ${p.performance_score||0}/10</div></div><div style="display:flex;gap:5px">${this.sbadge(p.status)}${p.supplier?this.badge('Supplier','bg-g'):''}</div></div>`).join('')||'<div style="color:var(--tx3);font-size:12px">None</div>'}</div>
                    </div>
                </div>
            </div>`);
    }
    conRows(c) { return c.map(x=>`<tr onclick="frappe.set_route('Form','Service Contract','${x.name}')"><td style="font-weight:600;color:var(--tx1)">${x.contract_title||x.name}</td><td style="color:var(--tx3)">${x.contract_type||''}</td><td style="color:var(--tx3)">${x.vendor||''}</td><td>${this.fmt(x.contract_value||0)}</td><td style="font-family:'JetBrains Mono',monospace;font-size:10px">${x.end_date||'—'}</td><td>${this.dlBadge(x.end_date)}</td></tr>`).join('')||'<tr><td colspan="6" style="text-align:center;color:var(--tx3);padding:20px">No contracts</td></tr>'; }
    filterCons() { const f=document.getElementById('hq-con-f')?.value||''; document.getElementById('hq-con-tbody').innerHTML=this.conRows(f?this.contracts.filter(c=>c.status===f):this.contracts); }

    renderCompliance() {
        const expired=this.compliance.filter(c=>c.status==='Expired');
        const byType={}; this.compliance.forEach(c=>{byType[c.compliance_type]=(byType[c.compliance_type]||0)+1;});
        const tk=Object.keys(byType);

        $('#hq-panel-compliance').html(`
            <div class="hq-kpis">
                ${this.kpi('🎖','','Total',this.compliance.length,'licences & permits')}
                ${this.kpi('✅','','Valid',this.compliance.filter(c=>c.status==='Valid').length,'good standing')}
                ${this.kpi('⚠️','','Expiring',this.compliance.filter(c=>c.status==='Expiring Soon').length,'within reminder')}
                ${this.kpi('🔴','','Expired',expired.length,'action required')}
                ${this.kpi('💰','','Renewal budget',this.fmt(this.compliance.filter(c=>c.status!=='Valid').reduce((s,c)=>s+this.flt(c.renewal_cost),0)),'estimated')}
            </div>
            <div class="hq-g21">
                <div class="hq-card">
                    <div class="hq-ch"><div class="hq-ct">🎖 Compliance register</div>
                        <div class="hq-acts">
                            <select class="hq-btn hb-ghost" id="hq-cmp-f" onchange="window.__admhq.filterComp()" style="cursor:pointer"><option value="">All</option><option>Expired</option><option>Expiring Soon</option><option>Valid</option></select>
                            <button class="hq-btn hb-solid" onclick="frappe.new_doc('Compliance Register')">+ Add</button>
                        </div>
                    </div>
                    <div class="hq-tbl-w"><table class="hq-tbl"><thead><tr><th>Item</th><th>Type</th><th>Authority</th><th>Expiry</th><th>Status</th><th>Renewal</th></tr></thead>
                    <tbody id="hq-cmp-tbody">${this.cmpRows(this.compliance)}</tbody></table></div>
                </div>
                <div>
                    <div class="hq-card">
                        <div class="hq-ch"><div class="hq-ct">📊 By type</div></div>
                        <div class="hq-cb"><div style="height:200px;position:relative"><canvas id="hq-ch-cmt" aria-label="Compliance by type donut">Compliance items by type.</canvas></div></div>
                    </div>
                    <div class="hq-card" style="margin-top:13px">
                        <div class="hq-ch"><div class="hq-ct">🚨 Action now</div></div>
                        <div class="hq-cb">${expired.length?expired.slice(0,4).map(c=>`<div class="hq-abox ab-r" onclick="frappe.set_route('Form','Compliance Register','${c.name}')"><div><div class="at">${c.compliance_item}</div><div class="as">${c.compliance_type} · ${c.issuing_authority||''}</div></div>${c.renewal_cost?this.badge(this.fmt(c.renewal_cost),'bg-s'):''}</div>`).join(''):'<div style="color:var(--tx3);font-size:12px">No expired items ✅</div>'}</div>
                    </div>
                </div>
            </div>`);
        if(tk.length) this.makeChart('hq-ch-cmt',{type:'doughnut',data:{labels:tk,datasets:[{data:tk.map(k=>byType[k]),backgroundColor:this.colors(),borderWidth:0}]},options:{responsive:true,maintainAspectRatio:false,cutout:'65%',plugins:{legend:{display:true,position:'right',labels:{color:'#94A3B8',font:{size:9},boxWidth:9,padding:5}}}}});
    }
    cmpRows(items) { return items.map(c=>`<tr onclick="frappe.set_route('Form','Compliance Register','${c.name}')"><td style="font-weight:600;color:var(--tx1)">${c.compliance_item}</td><td style="color:var(--tx3)">${c.compliance_type||''}</td><td style="color:var(--tx3)">${c.issuing_authority||'—'}</td><td style="font-family:'JetBrains Mono',monospace;font-size:10px">${c.expiry_date||'—'}</td><td>${this.dlBadge(c.expiry_date)}</td><td>${c.renewal_cost?this.fmt(c.renewal_cost):'—'}</td></tr>`).join('')||'<tr><td colspan="6" style="text-align:center;color:var(--tx3);padding:20px">No items</td></tr>'; }
    filterComp() { const f=document.getElementById('hq-cmp-f')?.value||''; document.getElementById('hq-cmp-tbody').innerHTML=this.cmpRows(f?this.compliance.filter(c=>c.status===f):this.compliance); }

    renderHSE() {
        const passCount=this.hseInspections.filter(h=>h.pass_fail==='Pass').length;
        const failCount=this.hseInspections.filter(h=>h.pass_fail==='Fail').length;
        const avgScore=this.hseInspections.length?(this.hseInspections.reduce((s,h)=>s+this.flt(h.overall_score),0)/this.hseInspections.length).toFixed(1):'N/A';
        const poorAssets=this.assetInspections.filter(a=>['Poor','Critical - Action Required'].includes(a.overall_condition));
        const byFac={}; this.hseInspections.forEach(h=>{if(!byFac[h.facility])byFac[h.facility]=[];byFac[h.facility].push(this.flt(h.overall_score));});
        const condCol={'Excellent':'#10B981','Good':'#38BDF8','Fair':'#F59E0B','Poor':'#F97316','Critical - Action Required':'#EF4444'};

        $('#hq-panel-hse').html(`
            <div class="hq-kpis">
                ${this.kpi('✅','','Pass',passCount,'inspections')}
                ${this.kpi('🔴','','Fail',failCount,'facilities')}
                ${this.kpi('🟠','','Conditional',this.hseInspections.filter(h=>h.pass_fail==='Conditional Pass').length,'passes')}
                ${this.kpi('📊','','Avg score',avgScore+'%','all facilities')}
                ${this.kpi('⚠️','','Poor assets',poorAssets.length,'condition poor/critical')}
                ${this.kpi('🔧','','Action pending',this.assetInspections.filter(a=>a.status==='Failed - Action Pending').length,'assets')}
            </div>
            <div class="hq-g2">
                <div class="hq-card">
                    <div class="hq-ch"><div class="hq-ct">⚠️ HSE inspections</div><button class="hq-btn hb-solid" onclick="frappe.new_doc('HSE Inspection')">+ Inspect</button></div>
                    <div class="hq-tbl-w"><table class="hq-tbl"><thead><tr><th>Facility</th><th>Date</th><th>Type</th><th>Score</th><th>Result</th><th>Status</th></tr></thead>
                    <tbody>${this.hseInspections.map(h=>`<tr onclick="frappe.set_route('Form','HSE Inspection','${h.name}')"><td style="font-weight:600">${h.facility}</td><td style="font-family:'JetBrains Mono',monospace;font-size:10px">${h.inspection_date}</td><td style="color:var(--tx3)">${h.inspection_type}</td><td><div style="display:flex;align-items:center;gap:5px"><div style="flex:1;height:4px;background:var(--brd);border-radius:10px;overflow:hidden;min-width:30px"><div style="height:100%;width:${h.overall_score||0}%;background:${this.flt(h.overall_score)>=80?'#10B981':this.flt(h.overall_score)>=60?'#F59E0B':'#EF4444'};border-radius:10px"></div></div><span style="font-size:10px;font-family:'JetBrains Mono',monospace">${h.overall_score||0}%</span></div></td><td>${h.pass_fail?this.badge(h.pass_fail,h.pass_fail==='Pass'?'bg-g':h.pass_fail==='Fail'?'bg-r':'bg-a'):'—'}</td><td>${this.sbadge(h.status)}</td></tr>`).join('')||'<tr><td colspan="6" style="text-align:center;color:var(--tx3);padding:20px">No HSE inspections</td></tr>'}</tbody></table></div>
                </div>
                <div class="hq-card">
                    <div class="hq-ch"><div class="hq-ct">📊 Facility HSE scores</div></div>
                    <div class="hq-cb">${Object.entries(byFac).map(([fac,scores])=>{const avg=scores.reduce((a,b)=>a+b,0)/scores.length;return `<div class="hq-bar-row"><div class="hq-bar-lbl" style="font-size:10px;width:110px">${fac}</div><div class="hq-bar"><div class="hq-bar-fill" style="width:${avg}%;background:${avg>=80?'#10B981':avg>=60?'#F59E0B':'#EF4444'}"></div></div><div class="hq-bar-val">${avg.toFixed(0)}%</div></div>`;}).join('')||'<div style="color:var(--tx3);font-size:12px">No HSE data</div>'}</div>
                </div>
            </div>
            <div class="hq-card">
                <div class="hq-ch"><div class="hq-ct">🔍 Asset inspections</div><button class="hq-btn hb-solid" onclick="frappe.new_doc('Asset Inspection')">+ Inspect</button></div>
                <div class="hq-tbl-w"><table class="hq-tbl"><thead><tr><th>Asset</th><th>Facility</th><th>Date</th><th>Type</th><th>Condition</th><th>Status</th></tr></thead>
                <tbody>${this.assetInspections.map(a=>`<tr onclick="frappe.set_route('Form','Asset Inspection','${a.name}')"><td style="font-weight:600;color:var(--tx1)">${a.asset}</td><td style="color:var(--tx3)">${a.facility}</td><td style="font-family:'JetBrains Mono',monospace;font-size:10px">${a.inspection_date}</td><td style="color:var(--tx3)">${a.inspection_type}</td><td>${a.overall_condition?`<span style="display:inline-flex;align-items:center;gap:3px"><span style="width:6px;height:6px;border-radius:50%;background:${condCol[a.overall_condition]||'#94A3B8'}"></span>${a.overall_condition}</span>`:'—'}</td><td>${this.sbadge(a.status)}</td></tr>`).join('')||'<tr><td colspan="6" style="text-align:center;color:var(--tx3);padding:20px">No asset inspections</td></tr>'}</tbody></table></div>
            </div>`);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  TAB: AI INTELLIGENCE
    // ═══════════════════════════════════════════════════════════════════════════
    renderIntelligence() {
        const spend=this.computeSpend();
        const fleetUtil=this.vehicles.length?(this.vehicles.filter(v=>v.status==='Available').length/this.vehicles.length*100).toFixed(0):0;
        const maintRes=this.maintReqs.length?Math.round(this.maintReqs.filter(m=>m.status==='Completed').length/this.maintReqs.length*100):100;
        const compHealth=this.compliance.length?Math.round(this.compliance.filter(c=>c.status==='Valid').length/this.compliance.length*100):100;
        const msgResp=this.waConvos.length?Math.round(this.waConvos.filter(c=>c.status==='Resolved').length/this.waConvos.length*100):100;
        const score=Math.round(fleetUtil*0.15+maintRes*0.25+compHealth*0.40+msgResp*0.20);
        const insights=this._insights();
        const slaRisk=this.requests.filter(r=>{const t={'Urgent':1,'High':3,'Medium':7,'Low':14};return !['Completed','Closed','Rejected'].includes(r.status)&&this.n(r.request_age_days)>=((t[r.priority]||7)*0.8);});
        const utilAnomaly=this.utilConsumed.filter(u=>this.flt(u.variance_pct)>30);
        const unreadMsg=this.waConvos.reduce((s,c)=>s+this.n(c.unread_count),0);

        $('#hq-panel-intelligence').html(`
            <div class="hq-g4">
                <div class="hq-card" style="text-align:center;padding:20px">
                    <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:var(--tx3);margin-bottom:8px">Admin health score</div>
                    <div style="font-size:44px;font-weight:800;color:${score>=80?'var(--grn)':score>=60?'var(--amb)':'var(--red)'};line-height:1">${score}</div>
                    <div style="font-size:11px;color:var(--tx3);margin-top:4px">/ 100</div>
                    <div style="height:4px;background:var(--brd);border-radius:10px;overflow:hidden;margin-top:10px"><div style="height:100%;width:${score}%;background:${score>=80?'var(--grn)':score>=60?'var(--amb)':'var(--red)'};border-radius:10px;transition:width .8s"></div></div>
                </div>
                <div class="hq-card" style="padding:18px">
                    <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--tx3);margin-bottom:10px">Component scores</div>
                    <div class="hq-bar-row"><div class="hq-bar-lbl">Fleet availability</div><div class="hq-bar"><div class="hq-bar-fill" style="width:${fleetUtil}%;background:var(--pri)"></div></div><div class="hq-bar-val">${fleetUtil}%</div></div>
                    <div class="hq-bar-row"><div class="hq-bar-lbl">Maint. resolution</div><div class="hq-bar"><div class="hq-bar-fill" style="width:${maintRes}%;background:var(--sky)"></div></div><div class="hq-bar-val">${maintRes}%</div></div>
                    <div class="hq-bar-row"><div class="hq-bar-lbl">Compliance health</div><div class="hq-bar"><div class="hq-bar-fill" style="width:${compHealth}%;background:var(--grn)"></div></div><div class="hq-bar-val">${compHealth}%</div></div>
                    <div class="hq-bar-row"><div class="hq-bar-lbl">Msg. resolution</div><div class="hq-bar"><div class="hq-bar-fill" style="width:${msgResp}%;background:var(--pur)"></div></div><div class="hq-bar-val">${msgResp}%</div></div>
                </div>
                <div class="hq-card" style="padding:18px">
                    <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--tx3);margin-bottom:8px">SLA risk requests</div>
                    <div style="font-size:36px;font-weight:800;color:${slaRisk.length>0?'var(--amb)':'var(--grn)'};line-height:1">${slaRisk.length}</div>
                    <div style="font-size:11px;color:var(--tx3);margin-top:4px">approaching breach</div>
                    <div style="margin-top:10px;font-size:11px;color:var(--tx2)">${slaRisk.slice(0,2).map(r=>`<div>• ${r.request_title||r.name}</div>`).join('')}</div>
                </div>
                <div class="hq-card" style="padding:18px">
                    <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--tx3);margin-bottom:8px">Unread messages</div>
                    <div style="font-size:36px;font-weight:800;color:${unreadMsg>0?'var(--pur)':'var(--grn)'};line-height:1">${unreadMsg}</div>
                    <div style="font-size:11px;color:var(--tx3);margin-top:4px">awaiting reply</div>
                    <div style="margin-top:10px;font-size:11px;color:var(--tx2)">${this.waConvos.filter(c=>c.unread_count>0).slice(0,2).map(c=>`<div>• ${c.contact_display_name||c.phone_number}</div>`).join('')}</div>
                </div>
            </div>
            <div class="hq-g21">
                <div class="hq-card">
                    <div class="hq-ch">
                        <div class="hq-ct">🤖 AI-generated insights</div>
                        <button class="hq-btn hb-solid" id="hq-ai-btn" onclick="window.__admhq.runAI()">✨ Deep analysis</button>
                    </div>
                    <div class="hq-cb" id="hq-ai-area">
                        ${insights.map(i=>`<div class="hq-abox ${i.cls}" style="cursor:default;margin-bottom:8px"><div style="flex:1"><div class="at">${i.title}</div><div class="as">${i.body}</div></div>${i.tab?`<button class="hq-btn hb-ghost" onclick="window.__admhq.switchTab('${i.tab}')">→</button>`:''}</div>`).join('')}
                    </div>
                </div>
                <div style="display:flex;flex-direction:column;gap:13px">
                    <div class="hq-card">
                        <div class="hq-ch"><div class="hq-ct">💬 Messaging health</div></div>
                        <div class="hq-cb">
                            <div class="hq-stat-grid">
                                <div class="hq-stat"><div class="hq-stat-v">${this.waConvos.length}</div><div class="hq-stat-l">Total threads</div></div>
                                <div class="hq-stat"><div class="hq-stat-v" style="color:var(--grn)">${this.waConvos.filter(c=>c.status==='Resolved').length}</div><div class="hq-stat-l">Resolved</div></div>
                                <div class="hq-stat"><div class="hq-stat-v" style="color:var(--red)">${unreadMsg}</div><div class="hq-stat-l">Unread</div></div>
                                <div class="hq-stat"><div class="hq-stat-v">${this.blasts.reduce((s,b)=>s+this.n(b.sent_count),0).toLocaleString()}</div><div class="hq-stat-l">Blast sent</div></div>
                            </div>
                        </div>
                    </div>
                    <div class="hq-card">
                        <div class="hq-ch"><div class="hq-ct">💰 Spend MTD summary</div></div>
                        <div class="hq-cb" style="font-size:12px">
                            ${[['Utilities','bg-p',spend.utilCostMTD,'Utility Consumption'],['Generator diesel','bg-a',spend.genCostMTD,'Generator Log'],['Fleet fuel','bg-a',spend.fleetFuelMTD,'Fuel Issue'],['Maintenance','bg-v',spend.maintCostMTD,'Work Order actual_cost'],['Contracts','bg-g',spend.activeContractMonthly,'Service Contract ÷12'],['Admin ops','bg-s',spend.adminOpsMTD,'Admin Request actual_cost']].map(([l,c,v,s])=>`<div style="display:flex;align-items:center;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--brd)"><div><div style="font-weight:600;color:var(--tx1)">${l}</div><div style="font-size:10px;color:var(--tx3)">${s}</div></div><span class="hq-badge ${c}">${this.fmt(v)}</span></div>`).join('')}
                            <div style="display:flex;justify-content:space-between;padding-top:8px;font-weight:700"><span>Total</span><span style="color:var(--pri)">${this.fmt(spend.totalMTD)}</span></div>
                        </div>
                    </div>
                </div>
            </div>
        `);
    }

    _insights() {
        const ins=[];
        const breached=this.requests.filter(r=>r.sla_breached==1);
        const expiredComp=this.compliance.filter(c=>c.status==='Expired');
        const groundedVeh=this.vehicles.filter(v=>v.status==='Grounded');
        const unread=this.waConvos.reduce((s,c)=>s+this.n(c.unread_count),0);
        const genHrsMTD=this.genLogs.filter(g=>g.log_date&&g.log_date.substring(0,7)===frappe.datetime.get_today().substring(0,7)).reduce((s,g)=>s+this.flt(g.run_hours),0);
        const expiringCon=this.contracts.filter(c=>{const d=this.daysLeft(c.end_date);return d!==null&&d>=0&&d<=30;});
        const openInc=this.incidents.filter(i=>!['Resolved','Closed'].includes(i.status));

        if(breached.length)   ins.push({cls:'ab-r',title:`${breached.length} SLA breach${breached.length>1?'es':''}`,body:`Types: ${[...new Set(breached.map(r=>r.request_type))].join(', ')}. Pre-approve recurring maintenance budgets.`,tab:'requests'});
        if(expiredComp.length)ins.push({cls:'ab-r',title:`${expiredComp.length} compliance item${expiredComp.length>1?'s':''} expired`,body:`${expiredComp.map(c=>c.compliance_item).slice(0,3).join(', ')}. Non-compliance exposes the organisation to regulatory penalties.`,tab:'compliance'});
        if(groundedVeh.length)ins.push({cls:'ab-r',title:`${groundedVeh.length} vehicle${groundedVeh.length>1?'s':''} grounded`,body:`${groundedVeh.map(v=>v.vehicle_name||v.plate_number).join(', ')}. Review insurance and licence renewals.`,tab:'fleet'});
        if(unread>0)          ins.push({cls:'ab-a',title:`${unread} unread message${unread>1?'s':''}`,body:`Unanswered WhatsApp conversations may impact stakeholder relationships. Assign to a team member.`,tab:'messaging'});
        if(genHrsMTD>80)      ins.push({cls:'ab-a',title:`${genHrsMTD.toFixed(0)}h generator runtime this month`,body:'Persistent grid outages detected. ROI analysis for solar UPS or captive power is recommended.',tab:null});
        if(expiringCon.length)ins.push({cls:'ab-a',title:`${expiringCon.length} contract${expiringCon.length>1?'s':''} expiring within 30 days`,body:`${expiringCon.map(c=>c.contract_title||c.vendor).slice(0,3).join(', ')}. Begin renewal negotiations immediately.`,tab:'contracts'});
        if(openInc.length)    ins.push({cls:'ab-b',title:`${openInc.length} open security incident${openInc.length>1?'s':''}`,body:`${openInc.filter(i=>['Severe','Critical'].includes(i.severity)).length} are severe or critical. Escalate to management.`,tab:'security'});
        if(!ins.length)       ins.push({cls:'ab-g',title:'All systems performing normally',body:'No critical issues detected. Continue monitoring compliance expiry dates and vehicle documents.',tab:null});
        return ins;
    }

    async runAI() {
        const btn=document.getElementById('hq-ai-btn');
        const area=document.getElementById('hq-ai-area');
        if(btn) btn.innerHTML='⟳ Analysing…';
        if(area) area.innerHTML='<div style="text-align:center;padding:20px;color:var(--tx3)">⟳ Calling Anthropic AI…</div>';

        const spend=this.computeSpend();
        const unread=this.waConvos.reduce((s,c)=>s+this.n(c.unread_count),0);

        const prompt=`You are an expert administrative operations analyst for a Nigerian organisation. Analyse and provide 5 actionable insights:

Key data:
- Open admin requests: ${this.requests.filter(r=>!['Completed','Closed','Rejected'].includes(r.status)).length} (${this.requests.filter(r=>r.sla_breached==1).length} SLA breaches)
- Fleet: ${this.vehicles.length} vehicles, ${this.vehicles.filter(v=>v.status==='Available').length} available, ${this.vehicles.filter(v=>v.status==='Grounded').length} grounded
- Utility spend MTD: ₦${(spend.utilCostMTD+spend.genCostMTD).toLocaleString()} (generator ran ${this.genLogs.filter(g=>g.log_date&&g.log_date.substring(0,7)===frappe.datetime.get_today().substring(0,7)).reduce((s,g)=>s+this.flt(g.run_hours),0).toFixed(0)} hours)
- Compliance: ${this.compliance.filter(c=>c.status==='Expired').length} expired, ${this.compliance.filter(c=>c.status==='Expiring Soon').length} expiring soon
- Contracts: ${this.contracts.filter(c=>{const d=this.daysLeft(c.end_date);return d!==null&&d>=0&&d<=60;}).length} expiring within 60 days
- Security: ${this.incidents.filter(i=>!['Resolved','Closed'].includes(i.status)).length} open incidents
- WhatsApp: ${this.waConvos.length} conversations, ${unread} unread, ${this.blasts.reduce((s,b)=>s+this.n(b.sent_count),0)} blast messages sent
- Total admin spend MTD: ₦${spend.totalMTD.toLocaleString()}

Return a JSON array of 5 objects: [{"risk":"Critical|High|Medium","title":"...","body":"...","action":"..."}]. JSON only, no markdown.`;

        try {
            const r=await fetch('/api/method/ecclesia.api.ai_diagnosis.get_ai_insight',{method:'POST',headers:{'Content-Type':'application/json','X-Frappe-CSRF-Token':frappe.csrf_token},body:JSON.stringify({prompt,context:'admhq',max_tokens:1200})});
            if(!r.ok) throw new Error('HTTP '+r.status);
            const d=await r.json();
            const text=d.message?.response||d.message||'';
            let items=[];
            try{const m=text.match(/\[[\s\S]*\]/);if(m)items=JSON.parse(m[0]);}catch(e){items=[{risk:'Medium',title:'AI analysis',body:text.substring(0,400),action:''}];}
            const rmap={'Critical':'ab-r','High':'ab-a','Medium':'ab-b'};
            if(area) area.innerHTML=items.map(i=>`<div class="hq-abox ${rmap[i.risk]||'ab-b'}" style="cursor:default;margin-bottom:8px"><div style="flex:1"><div class="at">${this.badge(i.risk||'Medium',i.risk==='Critical'?'bg-r':i.risk==='High'?'bg-a':'bg-p')} ${i.title||''}</div><div class="as" style="margin-top:4px">${i.body||''}</div>${i.action?`<div style="font-size:11px;color:var(--pri);margin-top:4px;font-weight:600">→ ${i.action}</div>`:''}</div></div>`).join('');
        }catch(e){
            if(area) area.innerHTML=this._insights().map(i=>`<div class="hq-abox ${i.cls}" style="cursor:default;margin-bottom:8px"><div><div class="at">${i.title}</div><div class="as">${i.body}</div></div></div>`).join('');
        }
        if(btn) btn.innerHTML='✨ Deep analysis';
    }

    exportCSV() {
        const rows=[['Name','Type','Priority','Status','Employee','Department','Age (days)','Actual Cost']];
        this.requests.forEach(r=>rows.push([r.request_title||r.name,r.request_type,r.priority,r.status,r.employee,r.department,r.request_age_days||0,r.actual_cost||0]));
        const csv=rows.map(r=>r.map(v=>`"${(v||'').toString().replace(/"/g,'""')}"`).join(',')).join('\n');
        const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));a.download='admhq_export.csv';a.click();
        frappe.show_alert({message:'Exported',indicator:'green'});
    }
}
