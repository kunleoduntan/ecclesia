// Copyright (c) 2026, Value Impacts Consulting
// ecclesia/ecclesia/page/secretarial_hub/secretarial_hub.js
//
// ╔══════════════════════════════════════════════════════════════════════════╗
// ║  Secretarial HQ — Full Secretarial & Governance Command Centre          ║
// ║  9 Themes · 8 Tabs · 6 Secretarial Domains · AI Analysis · Excel        ║
// ╚══════════════════════════════════════════════════════════════════════════╝

frappe.pages['secretarial-hub'] = frappe.pages['secretarial-hub'] || {};

frappe.pages['secretarial-hub'].on_page_load = function (wrapper) {
	const boot = () => new SecretarialHQ(wrapper);
	if (typeof Chart === 'undefined') {
		const s = document.createElement('script');
		s.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
		s.onload = boot;
		document.head.appendChild(s);
	} else {
		boot();
	}
};

frappe.pages['secretarial-hub'].on_page_show = function () {
	if (window.__shq) window.__shq.refresh(true);
};

// ── BACKEND PATH ─────────────────────────────────────────────────────────────
const SHQ_API = 'ecclesia.ecclesia.page.secretarial_hub.secretarial_hub.';

// ── Theme Registry ────────────────────────────────────────────────────────────
const SHQ_THEMES = {
	professional: { n: 'Professional', i: '⚖️', dark: false, p: '#1E3A5F', pd: '#152C47', px: 'rgba(30,58,95,.09)', a: '#2563EB', r: '#DC2626', rx: 'rgba(220,38,38,.09)', am: '#D97706', ax: 'rgba(217,119,6,.09)', g: '#059669', gx: 'rgba(5,150,105,.09)', s: '#0284C7', sx: 'rgba(2,132,199,.09)', v: '#7C3AED', vx: 'rgba(124,58,237,.09)', bg: '#F8FAFC', b2: '#F1F5F9', b3: '#E2E8F0', c: '#FFFFFF', bd: '#E2E8F0', b2d: '#CBD5E1', t1: '#0F172A', t2: '#475569', t3: '#94A3B8', bn: 'linear-gradient(135deg,#0F172A,#1E3A5F 50%,#2563EB 80%,#0284C7)' },
	midnight: { n: 'Midnight', i: '🌙', dark: true, p: '#818CF8', pd: '#6366F1', px: 'rgba(129,140,248,.12)', a: '#A5B4FC', r: '#F87171', rx: 'rgba(248,113,113,.12)', am: '#FCD34D', ax: 'rgba(252,211,77,.12)', g: '#34D399', gx: 'rgba(52,211,153,.12)', s: '#38BDF8', sx: 'rgba(56,189,248,.12)', v: '#C084FC', vx: 'rgba(192,132,252,.12)', bg: '#0F172A', b2: '#1E293B', b3: '#334155', c: '#1E293B', bd: 'rgba(255,255,255,.08)', b2d: 'rgba(255,255,255,.14)', t1: '#F1F5F9', t2: '#94A3B8', t3: '#475569', bn: 'linear-gradient(135deg,#020617,#0F172A 50%,#1E3A5F 70%,#312E81)' },
	verdant: { n: 'Verdant', i: '🌿', dark: false, p: '#059669', pd: '#047857', px: 'rgba(5,150,105,.09)', a: '#34D399', r: '#EF4444', rx: 'rgba(239,68,68,.09)', am: '#F59E0B', ax: 'rgba(245,158,11,.09)', g: '#10B981', gx: 'rgba(16,185,129,.09)', s: '#0EA5E9', sx: 'rgba(14,165,233,.09)', v: '#8B5CF6', vx: 'rgba(139,92,246,.09)', bg: '#ECFDF5', b2: '#D1FAE5', b3: '#A7F3D0', c: '#FFFFFF', bd: '#A7F3D0', b2d: '#6EE7B7', t1: '#022C22', t2: '#065F46', t3: '#6EE7B7', bn: 'linear-gradient(135deg,#022C22,#047857 40%,#059669 70%,#10B981)' },
	sapphire: { n: 'Sapphire', i: '💎', dark: false, p: '#1E3A8A', pd: '#1E40AF', px: 'rgba(30,58,138,.09)', a: '#3B82F6', r: '#DC2626', rx: 'rgba(220,38,38,.09)', am: '#D97706', ax: 'rgba(217,119,6,.09)', g: '#059669', gx: 'rgba(5,150,105,.09)', s: '#0EA5E9', sx: 'rgba(14,165,233,.09)', v: '#7C3AED', vx: 'rgba(124,58,237,.09)', bg: '#EFF6FF', b2: '#DBEAFE', b3: '#BFDBFE', c: '#FFFFFF', bd: '#BFDBFE', b2d: '#93C5FD', t1: '#1E3A8A', t2: '#3B82F6', t3: '#60A5FA', bn: 'linear-gradient(135deg,#1E3A8A,#3B82F6 45%,#60A5FA 100%)' },
	ember: { n: 'Ember', i: '🔥', dark: false, p: '#F97316', pd: '#EA580C', px: 'rgba(249,115,22,.09)', a: '#FB923C', r: '#EF4444', rx: 'rgba(239,68,68,.09)', am: '#EAB308', ax: 'rgba(234,179,8,.09)', g: '#22C55E', gx: 'rgba(34,197,94,.09)', s: '#0EA5E9', sx: 'rgba(14,165,233,.09)', v: '#A855F7', vx: 'rgba(168,85,247,.09)', bg: '#FFF7ED', b2: '#FFEDD5', b3: '#FED7AA', c: '#FFFFFF', bd: '#FED7AA', b2d: '#FDBA74', t1: '#431407', t2: '#9A3412', t3: '#FDBA74', bn: 'linear-gradient(135deg,#431407,#C2410C 40%,#F97316 70%,#EAB308)' },
	arctic: { n: 'Arctic', i: '❄️', dark: false, p: '#0EA5E9', pd: '#0284C7', px: 'rgba(14,165,233,.09)', a: '#7DD3FC', r: '#EF4444', rx: 'rgba(239,68,68,.09)', am: '#F59E0B', ax: 'rgba(245,158,11,.09)', g: '#10B981', gx: 'rgba(16,185,129,.09)', s: '#6366F1', sx: 'rgba(99,102,241,.09)', v: '#EC4899', vx: 'rgba(236,72,153,.09)', bg: '#F0F9FF', b2: '#E0F2FE', b3: '#BAE6FD', c: '#FFFFFF', bd: '#BAE6FD', b2d: '#7DD3FC', t1: '#0C4A6E', t2: '#075985', t3: '#7DD3FC', bn: 'linear-gradient(135deg,#0C4A6E,#0369A1 40%,#0EA5E9 70%,#06B6D4)' },
	nova: { n: 'Nova', i: '🌟', dark: false, p: '#7C3AED', pd: '#6D28D9', px: 'rgba(124,58,237,.09)', a: '#A78BFA', r: '#EF4444', rx: 'rgba(239,68,68,.09)', am: '#F59E0B', ax: 'rgba(245,158,11,.09)', g: '#10B981', gx: 'rgba(16,185,129,.09)', s: '#06B6D4', sx: 'rgba(6,182,212,.09)', v: '#EC4899', vx: 'rgba(236,72,153,.09)', bg: '#FAF5FF', b2: '#F5F3FF', b3: '#EDE9FE', c: '#FFFFFF', bd: '#E9D5FF', b2d: '#D8B4FE', t1: '#2E1065', t2: '#5B21B6', t3: '#A78BFA', bn: 'linear-gradient(135deg,#1E1B4B,#4C1D95 40%,#7C3AED 70%,#EC4899)' },
	executive: { n: 'Executive', i: '👔', dark: false, p: '#1E293B', pd: '#0F172A', px: 'rgba(30,41,59,.09)', a: '#475569', r: '#EF4444', rx: 'rgba(239,68,68,.09)', am: '#F59E0B', ax: 'rgba(245,158,11,.09)', g: '#10B981', gx: 'rgba(16,185,129,.09)', s: '#0284C7', sx: 'rgba(2,132,199,.09)', v: '#7C3AED', vx: 'rgba(124,58,237,.09)', bg: '#FAFAFA', b2: '#F4F4F5', b3: '#E4E4E7', c: '#FFFFFF', bd: '#E4E4E7', b2d: '#D4D4D8', t1: '#18181B', t2: '#3F3F46', t3: '#71717A', bn: 'linear-gradient(135deg,#09090B,#18181B 40%,#1E293B 70%,#334155)' },
	forest: { n: 'Forest', i: '🌲', dark: true, p: '#22C55E', pd: '#16A34A', px: 'rgba(34,197,94,.12)', a: '#4ADE80', r: '#F87171', rx: 'rgba(248,113,113,.12)', am: '#FBBF24', ax: 'rgba(251,191,36,.12)', g: '#22C55E', gx: 'rgba(34,197,94,.12)', s: '#38BDF8', sx: 'rgba(56,189,248,.12)', v: '#F472B6', vx: 'rgba(244,114,182,.12)', bg: '#052E16', b2: '#14532D', b3: '#166534', c: '#14532D', bd: 'rgba(187,247,208,.1)', b2d: 'rgba(134,239,172,.18)', t1: '#F0FDF4', t2: '#86EFAC', t3: '#4ADE80', bn: 'linear-gradient(135deg,#052E16,#14532D 40%,#166534 70%,#22C55E)' },
};

const SHQ_DOMAINS = [
	{ key: 'overview', icon: '🏠', label: 'Overview', badge: null },
	{ key: 'meetings', icon: '📋', label: 'Meetings', badge: 'meetings_overdue' },
	{ key: 'agm', icon: '🏛️', label: 'AGM', badge: 'agm_overdue' },
	{ key: 'board', icon: '⚖️', label: 'Board', badge: 'board_issues' },
	{ key: 'correspondence', icon: '📧', label: 'Correspondence', badge: 'correspondence_overdue' },
	{ key: 'documents', icon: '📁', label: 'Documents & Legal', badge: 'documents_expiring' },
	{ key: 'executive', icon: '💼', label: 'Executive', badge: 'executive_overdue' },
	{ key: 'ai', icon: '🤖', label: 'AI Analysis', badge: null },
];

// ═══════════════════════════════════════════════════════════════════════════════
class SecretarialHQ {

	constructor(wrapper) {
		this.wrapper = wrapper;
		this.page = frappe.ui.make_app_page({ parent: wrapper, title: 'Secretarial HQ', single_column: true });
		this.charts = {};
		this.activeTab = 'overview';
		this.company = frappe.defaults.get_default('company') || '';
		this.domain = {};
		this.score = {};
		this.tabCache = {};
		this.theme = _shqLsGet('shq-theme', 'professional');
		window.__shq = this;
		this._init();
	}

	_init() {
		this._css();
		this._layout();
		this._applyTheme(this.theme, false);
		this._actions();
		this._bind();
		this._clock();
		setTimeout(() => this.loadAll(false), 400);
		setInterval(() => this.refresh(true), 90000);
	}

	// ── Theme ─────────────────────────────────────────────────────────────────
	_applyTheme(key, save = true) {
		const t = SHQ_THEMES[key] || SHQ_THEMES.professional;
		this.theme = key;
		if (save) _shqLsSet('shq-theme', key);
		const root = document.getElementById('shq-root');
		if (!root) return;
		const map = { p: 'pri', pd: 'pri_d', px: 'pri_x', a: 'acc', r: 'red', rx: 'red_x', am: 'amb', ax: 'amb_x',
			g: 'grn', gx: 'grn_x', s: 'sky', sx: 'sky_x', v: 'pur', vx: 'pur_x',
			bg: 'bg', b2: 'bg2', b3: 'bg3', c: 'card', bd: 'brd', b2d: 'brd2',
			t1: 'tx1', t2: 'tx2', t3: 'tx3', bn: 'banner' };
		Object.entries(map).forEach(([k, v]) => { if (t[k]) root.style.setProperty(`--${v}`, t[k]); });
		root.classList.toggle('dark', !!t.dark);
		const lbl = document.getElementById('shq-theme-lbl');
		if (lbl) lbl.textContent = t.i + ' ' + t.n;
		Object.values(this.charts).forEach(c => { try { c.update(); } catch (e) { } });
	}

	openThemePicker() {
		const cur = this.theme;
		const dialog = new frappe.ui.Dialog({
			title: '🎨 Secretarial HQ Theme',
			size: 'large',
			fields: [{
				fieldtype: 'HTML',
				options: `
				<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px">
				${Object.entries(SHQ_THEMES).map(([k, t]) => `
				  <div onclick="window.__shq._applyTheme('${k}');if(window.__shq_theme_dialog)window.__shq_theme_dialog.hide();"
					style="display:flex;align-items:center;gap:10px;padding:11px;border-radius:10px;
						   border:2px solid ${k === cur ? t.p : t.b2d || '#CBD5E1'};
						   background:${t.c};cursor:pointer;transition:all 0.2s"
					onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
					<div style="font-size:20px;width:34px;height:34px;border-radius:8px;background:${t.px};
								display:flex;align-items:center;justify-content:center">${t.i}</div>
					<div>
					  <div style="font-size:12px;font-weight:700;color:${t.t1}">${t.n}</div>
					  <div style="font-size:10px;color:${t.t3}">${t.dark ? '🌙 Dark' : '☀️ Light'}</div>
					</div>
					${k === cur ? `<span style="margin-left:auto;color:${t.p};font-size:16px">✓</span>` : ''}
				  </div>`).join('')}
				</div>
				<div style="margin-top:12px;text-align:center;font-size:11px;color:var(--tx3)">Click any theme to apply instantly</div>
				`
			}]
		});
		window.__shq_theme_dialog = dialog;
		dialog.show();
	}

	// ── CSS ───────────────────────────────────────────────────────────────────
	_css() {
		if (document.getElementById('shq-css')) return;
		const s = document.createElement('style');
		s.id = 'shq-css';
		s.textContent = `
		@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600;700&display=swap');
		#shq-root{--pri:#1E3A5F;--pri_x:rgba(30,58,95,.09);--red:#DC2626;--red_x:rgba(220,38,38,.09);--amb:#D97706;--amb_x:rgba(217,119,6,.09);--grn:#059669;--grn_x:rgba(5,150,105,.09);--sky:#0284C7;--sky_x:rgba(2,132,199,.09);--pur:#7C3AED;--pur_x:rgba(124,58,237,.09);--bg:#F8FAFC;--bg2:#F1F5F9;--bg3:#E2E8F0;--card:#FFFFFF;--brd:#E2E8F0;--brd2:#CBD5E1;--tx1:#0F172A;--tx2:#475569;--tx3:#94A3B8;--banner:linear-gradient(135deg,#0F172A,#1E3A5F,#2563EB);font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--tx1);min-height:100vh;transition:background .3s,color .3s}
		#shq-root *{box-sizing:border-box}
		#shq-root.dark{--bg:#0F172A;--bg2:#1E293B;--bg3:#334155;--card:#1E293B;--brd:rgba(255,255,255,.08);--brd2:rgba(255,255,255,.14);--tx1:#F1F5F9;--tx2:#94A3B8;--tx3:#475569}
		.s3-ban{background:var(--banner);padding:22px 28px 18px;margin:-15px -15px 18px;position:relative;overflow:hidden;color:#fff;border-radius:0 0 12px 12px;box-shadow:0 4px 20px rgba(0,0,0,.15)}
		.s3-ban::before{content:'';position:absolute;width:600px;height:600px;top:-60%;right:-10%;border-radius:50%;background:radial-gradient(circle,rgba(255,255,255,.05),transparent 65%)}
		.s3-ban::after{content:'';position:absolute;width:300px;height:300px;bottom:-40%;left:-5%;border-radius:50%;background:radial-gradient(circle,rgba(255,255,255,.03),transparent 65%)}
		.s3-bi{position:relative;z-index:1;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:14px}
		.s3-ban h1{font-size:22px;font-weight:900;letter-spacing:-.4px;margin:0 0 5px;display:flex;align-items:center;gap:10px}
		.s3-meta{display:flex;align-items:center;gap:12px;font-size:11px;opacity:.82;flex-wrap:wrap}
		.s3-live{display:inline-flex;align-items:center;gap:5px;background:rgba(5,150,105,.22);padding:3px 9px;border-radius:20px;font-size:10px;color:#34d399;border:1px solid rgba(5,150,105,.3);backdrop-filter:blur(4px)}
		.s3-dot{width:7px;height:7px;background:#34d399;border-radius:50%;animation:pulse 2s infinite}
		@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(1.3)}}
		.s3-chip{background:rgba(255,255,255,.14);padding:3px 10px;border-radius:20px;font-size:10px;font-weight:600;backdrop-filter:blur(4px)}
		.s3-tbtn{display:inline-flex;align-items:center;gap:6px;padding:5px 13px;border-radius:20px;font-size:11px;font-weight:700;background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.25);color:#fff;cursor:pointer;transition:all .2s;font-family:inherit;backdrop-filter:blur(4px)}
		.s3-tbtn:hover{background:rgba(255,255,255,.3);transform:translateY(-1px)}
		.s3-score{display:inline-flex;flex-direction:column;align-items:center;justify-content:center;width:76px;height:76px;border-radius:50%;border:3px solid rgba(255,255,255,.3);background:rgba(255,255,255,.1);backdrop-filter:blur(8px);transition:border-color .5s}
		.s3-sn{font-size:20px;font-weight:900;line-height:1}
		.s3-sl{font-size:9px;opacity:.7;margin-top:2px}
		.s3-alerts{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:14px}
		.s3-alert{display:flex;align-items:center;gap:6px;padding:5px 12px;border-radius:9px;font-size:11px;font-weight:600;cursor:pointer;border:1px solid transparent;transition:all .2s;text-decoration:none !important}
		.s3-alert:hover{transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,.1)}
		.sa-r{background:var(--red_x);border-color:rgba(220,38,38,.2);color:var(--red)}
		.sa-a{background:var(--amb_x);border-color:rgba(217,119,6,.2);color:var(--amb)}
		.sa-g{background:var(--grn_x);border-color:rgba(5,150,105,.2);color:var(--grn)}
		.sa-b{background:var(--pri_x);border-color:rgba(30,58,95,.2);color:var(--pri)}
		.s3-tabs{display:flex;gap:1px;background:var(--card);border:1px solid var(--brd);border-radius:12px;margin-bottom:16px;overflow-x:auto;scrollbar-width:none;box-shadow:0 2px 8px rgba(0,0,0,.04)}
		.s3-tabs::-webkit-scrollbar{display:none}
		.s3-tab{display:flex;align-items:center;gap:5px;padding:9px 14px;font-size:11px;font-weight:600;color:var(--tx2);cursor:pointer;border-bottom:3px solid transparent;transition:all .15s;white-space:nowrap;background:none;border-left:none;border-right:none;border-top:none;font-family:inherit}
		.s3-tab:hover{color:var(--pri);background:var(--pri_x)}
		.s3-tab.on{color:var(--pri);border-bottom-color:var(--pri);background:var(--pri_x)}
		.s3-n{background:var(--red);color:#fff;font-size:9px;font-weight:800;padding:1px 5px;border-radius:20px;min-width:15px;text-align:center;animation:pulse 2s infinite}
		.s3-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-bottom:16px}
		.s3-kpi{background:var(--card);border:1px solid var(--brd);border-radius:12px;padding:14px 16px;cursor:pointer;transition:all .2s;position:relative;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.04)}
		.s3-kpi::after{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--kc,var(--pri));opacity:0;transition:opacity .2s}
		.s3-kpi:hover{transform:translateY(-3px);box-shadow:0 8px 25px rgba(0,0,0,.1)}
		.s3-kpi:hover::after{opacity:1}
		.kp{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:var(--tx3);margin-bottom:4px}
		.kv{font-size:22px;font-weight:800;color:var(--tx1);line-height:1;margin-bottom:2px}
		.ks{font-size:10px;color:var(--tx3)}
		.s3-card{background:var(--card);border:1px solid var(--brd);border-radius:12px;overflow:hidden;transition:all .2s;margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,.04)}
		.s3-card:hover{box-shadow:0 4px 20px rgba(0,0,0,.08)}
		.s3-ch{padding:12px 17px;border-bottom:1px solid var(--brd);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px}
		.s3-ct{display:flex;align-items:center;gap:8px;font-size:13px;font-weight:700;color:var(--tx1)}
		.s3-cb{padding:14px 17px}
		.s3-g2{display:grid;grid-template-columns:1fr 1fr;gap:13px;margin-bottom:13px}
		.s3-g21{display:grid;grid-template-columns:2fr 1fr;gap:13px;margin-bottom:13px}
		.s3-btn{display:inline-flex;align-items:center;gap:5px;padding:5px 12px;border-radius:20px;font-size:11px;font-weight:700;cursor:pointer;border:1.5px solid transparent;font-family:inherit;transition:all .2s;text-decoration:none !important}
		.s3-btn:hover{transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,.1)}
		.sb-p{background:var(--pri_x);color:var(--pri);border-color:rgba(30,58,95,.2)}.sb-p:hover{background:var(--pri);color:#fff}
		.sb-g{background:var(--grn_x);color:var(--grn);border-color:rgba(5,150,105,.2)}.sb-g:hover{background:var(--grn);color:#fff}
		.sb-r{background:var(--red_x);color:var(--red);border-color:rgba(220,38,38,.2)}.sb-r:hover{background:var(--red);color:#fff}
		.sb-solid{background:var(--pri);color:#fff}.sb-solid:hover{opacity:.85}
		.sb-ghost{background:transparent;color:var(--tx2);border-color:var(--brd2)}.sb-ghost:hover{background:var(--bg2)}
		.s3-bdg{display:inline-flex;align-items:center;gap:3px;padding:2px 7px;border-radius:20px;font-size:10px;font-weight:700;white-space:nowrap}
		.bg-g{background:var(--grn_x);color:var(--grn)}.bg-r{background:var(--red_x);color:var(--red)}.bg-a{background:var(--amb_x);color:var(--amb)}.bg-b{background:var(--pri_x);color:var(--pri)}.bg-s{background:var(--sky_x);color:var(--sky)}.bg-v{background:var(--pur_x);color:var(--pur)}.bg-gr{background:var(--bg3);color:var(--tx3)}
		.s3-tw{overflow-x:auto;max-height:480px;overflow-y:auto;scrollbar-width:thin;scrollbar-color:var(--brd2) transparent}
		.s3-tw::-webkit-scrollbar{width:4px;height:4px}.s3-tw::-webkit-scrollbar-thumb{background:var(--brd2);border-radius:10px}
		.s3-tbl{width:100%;border-collapse:collapse;font-size:12px}
		.s3-tbl thead th{padding:8px 12px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--tx3);background:var(--bg2);border-bottom:2px solid var(--brd);position:sticky;top:0;z-index:1;white-space:nowrap}
		.s3-tbl tbody td{padding:8px 12px;border-bottom:1px solid var(--brd);color:var(--tx2)}
		.s3-tbl tbody tr{transition:all .1s;cursor:pointer}.s3-tbl tbody tr:hover{background:var(--pri_x)}
		.s3-tbl tbody tr:hover td{color:var(--tx1)}
		.s3-tbl tbody tr:last-child td{border-bottom:none}
		.s3-dsg{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:9px;margin-bottom:16px}
		.s3-ds{background:var(--card);border:1px solid var(--brd);border-radius:11px;padding:12px;text-align:center;cursor:pointer;transition:all .2s;box-shadow:0 1px 3px rgba(0,0,0,.04)}
		.s3-ds:hover{transform:translateY(-3px);border-color:var(--pri);box-shadow:0 4px 16px rgba(0,0,0,.08)}
		.s3-ds-i{font-size:22px;margin-bottom:6px}
		.s3-ds-n{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:var(--tx3);margin-bottom:5px}
		.s3-ds-v{font-size:22px;font-weight:800;line-height:1}
		.s3-ds-b{height:4px;background:var(--brd);border-radius:10px;overflow:hidden;margin-top:7px}
		.s3-ds-bf{height:100%;border-radius:10px;transition:width .7s cubic-bezier(.4,0,.2,1)}
		.s3-panel{display:none}.s3-panel.on{display:block}
		.s3-mono{font-family:'JetBrains Mono',monospace}
		.s3-empty{text-align:center;padding:32px;color:var(--tx3);font-size:13px}
		.s3-bar-row{display:flex;align-items:center;gap:8px;margin-bottom:7px}
		.s3-bar-lbl{font-size:11px;color:var(--tx2);width:140px;flex-shrink:0}
		.s3-bar{flex:1;height:5px;background:var(--brd);border-radius:40px;overflow:hidden}
		.s3-bar-f{height:100%;border-radius:40px;transition:width .6s cubic-bezier(.4,0,.2,1)}
		.s3-bar-val{font-size:10px;font-family:'JetBrains Mono',monospace;font-weight:700;width:50px;text-align:right;color:var(--tx1)}
		.s3-spin{animation:s3spin .8s linear infinite;display:inline-block}
		@keyframes s3spin{to{transform:rotate(360deg)}}
		.s3-loader{position:fixed;inset:0;background:rgba(10,15,30,.85);display:flex;align-items:center;justify-content:center;flex-direction:column;gap:13px;z-index:999;backdrop-filter:blur(8px)}
		.s3-spinner{width:36px;height:36px;border:3px solid var(--brd2);border-top-color:var(--pri);border-radius:50%;animation:s3spin .7s linear infinite}
		.s3-content{padding:0 16px 32px}
		@media(max-width:900px){.s3-g2,.s3-g21{grid-template-columns:1fr}}
		`;
		document.head.appendChild(s);
	}

	// ── Layout ────────────────────────────────────────────────────────────────
	_layout() {
		const main = this.page.main;
		$(main).empty();

		const tabButtons = SHQ_DOMAINS.map(d =>
			`<button class="s3-tab${d.key === 'overview' ? ' on' : ''}" data-tab="${d.key}">
			   ${d.icon} ${d.label}
			   ${d.badge ? `<span class="s3-n" id="s3-n-${d.key}" style="display:none">0</span>` : ''}
			 </button>`
		).join('');

		const panels = SHQ_DOMAINS.map(d =>
			`<div id="s3-p-${d.key}" class="s3-panel${d.key === 'overview' ? ' on' : ''}"></div>`
		).join('');

		const html = `
		<div id="shq-root">
		  <div class="s3-ban">
			<div class="s3-bi">
			  <div style="display:flex;align-items:center;gap:15px;flex-wrap:wrap">
				<div>
				  <h1>📋 Secretarial HQ <span style="font-size:13px;opacity:.7;font-weight:400">Governance Command Centre</span></h1>
				  <div class="s3-meta">
					<span>📅 <span id="s3-date"></span></span>
					<span id="s3-clock" class="s3-mono"></span>
					<span class="s3-live"><span class="s3-dot"></span> Live</span>
					<span class="s3-chip" id="s3-c1">Loading…</span>
					<span class="s3-chip" id="s3-c2">Loading…</span>
				  </div>
				</div>
				<div class="s3-score" id="s3-score-ring">
				  <div class="s3-sn" id="s3-score-n">—</div>
				  <div class="s3-sl">Gov. Score</div>
				</div>
			  </div>
			  <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
				<select id="s3-co" class="s3-tbtn" style="cursor:pointer;outline:none;background:rgba(255,255,255,.18);color:#fff;border:1px solid rgba(255,255,255,.25);border-radius:20px;padding:5px 13px;font-size:11px;font-weight:700" onchange="window.__shq._onCo(this.value)">
				  <option value="">Select Company</option>
				</select>
				<button class="s3-tbtn" onclick="window.__shq._exportExcel()">📊 Export Excel</button>
				<button class="s3-tbtn" onclick="window.__shq.openThemePicker()">🎨 <span id="shq-theme-lbl">⚖️ Professional</span></button>
				<span id="s3-ts" style="font-size:10px;opacity:.5"></span>
			  </div>
			</div>
		  </div>
		  <div class="s3-content">
			<div class="s3-alerts" id="s3-alerts"></div>
			<div class="s3-tabs">${tabButtons}</div>
			${panels}
		  </div>
		  <div class="s3-loader" id="s3-loader" style="display:none">
			<div class="s3-spinner"></div>
			<div style="font-weight:600;font-size:14px;color:#F1F5F9">Loading Secretarial HQ</div>
			<div style="font-size:12px;color:#94A3B8">Fetching all secretarial domains…</div>
		  </div>
		</div>`;

		$(html).appendTo(main);
		this._populateCo();
	}

	_populateCo() {
		const sel = document.getElementById('s3-co');
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
		}).catch(() => { sel.innerHTML = '<option value="">No companies found</option>'; });
	}

	_onCo(v) {
		this.company = v;
		this.tabCache = {};
		if (v) this.loadAll(false);
	}

	_actions() {
		this.page.add_inner_button('🔄 Refresh', () => this.loadAll(false));
		this.page.add_inner_button('📊 Download Excel Report', () => this._exportExcel());
		this.page.add_inner_button('📋 New Meeting', () => frappe.new_doc('Meeting'));
		this.page.add_inner_button('📧 New Correspondence', () => frappe.new_doc('Correspondence'));
		this.page.add_menu_item('⚖️ New Board Resolution', () => frappe.new_doc('Board Resolution'));
		this.page.add_menu_item('📁 New Corporate Document', () => frappe.new_doc('Corporate Document'));
		this.page.add_menu_item('🏛️ New AGM', () => frappe.new_doc('Annual General Meeting'));
		this.page.add_menu_item('🎨 Theme Picker', () => this.openThemePicker());
		this.page.add_menu_item('🖨️ Print', () => window.print());
	}

	_bind() {
		$(document).on('click', '.s3-tab', e => this._switchTab($(e.currentTarget).data('tab')));
	}

	_switchTab(name) {
		$('.s3-tab').removeClass('on');
		$(`.s3-tab[data-tab="${name}"]`).addClass('on');
		$('.s3-panel').removeClass('on');
		$(`#s3-p-${name}`).addClass('on');
		this.activeTab = name;
		this._render(name);
	}

	_clock() {
		const tick = () => {
			const clockEl = document.getElementById('s3-clock');
			if (clockEl) clockEl.textContent = new Date().toLocaleTimeString('en-NG', { hour12: true, hour: '2-digit', minute: '2-digit', second: '2-digit' });
			const dateEl = document.getElementById('s3-date');
			if (dateEl) dateEl.textContent = frappe.datetime.str_to_user(frappe.datetime.get_today());
		};
		tick();
		setInterval(tick, 1000);
	}

	// ── Data Load ─────────────────────────────────────────────────────────────
	async loadAll(silent = false) {
		if (!this.company) {
			$('#s3-loader').hide();
			const alertEl = document.getElementById('s3-alerts');
			if (alertEl) alertEl.innerHTML = '<div class="s3-alert sa-b">🏢 Please select a company from the dropdown above</div>';
			return;
		}
		if (!silent) $('#s3-loader').show();
		try {
			const [r1, r2] = await Promise.all([
				frappe.call({ method: SHQ_API + 'get_domain_summary', args: { company: this.company } }),
				frappe.call({ method: SHQ_API + 'get_full_secretarial_score', args: { company: this.company } }),
			]);
			this.domain = r1.message || {};
			this.score = r2.message || {};
			this._updateBanner();
			this._buildAlerts();
			this._updateScoreRing();
			this._updateTabBadges();
			this._render(this.activeTab);
			const tsEl = document.getElementById('s3-ts');
			if (tsEl) tsEl.textContent = 'Updated ' + new Date().toLocaleTimeString('en-NG', { hour12: true });
		} catch (e) {
			console.error('Secretarial HQ load error:', e);
			const alertEl = document.getElementById('s3-alerts');
			if (alertEl) alertEl.innerHTML = `<div class="s3-alert sa-r">❌ Failed to load secretarial data: ${e.message || 'Unknown error'}</div>`;
			if (!silent) frappe.msgprint({ title: 'Load Error', indicator: 'red', message: 'Failed to load secretarial data. Please check console for details.' });
		} finally {
			$('#s3-loader').hide();
		}
	}

	refresh(silent = false) { this.loadAll(silent); }

	_updateBanner() {
		const dm = this.domain, avail = dm.modules_available || {};
		const overdueTotal = (avail.correspondence ? (dm.correspondence.overdue_response || 0) : 0)
			+ (avail.agm ? (dm.agm.cac_overdue || 0) : 0)
			+ (avail.documents ? (dm.documents.legal_expired || 0) : 0)
			+ (avail.executive ? (dm.executive.overdue_tasks || 0) : 0);
		const meetingsThisYear = avail.meetings ? (dm.meetings.held_this_year || 0) : 0;
		const c1 = document.getElementById('s3-c1');
		const c2 = document.getElementById('s3-c2');
		if (c1) c1.textContent = `${overdueTotal} item(s) overdue across all domains`;
		if (c2) c2.textContent = `${meetingsThisYear} meeting(s) held this year`;
	}

	_updateScoreRing() {
		const s = this.score.overall || 0;
		const ring = document.getElementById('s3-score-ring');
		const num = document.getElementById('s3-score-n');
		if (num) num.textContent = Math.round(s) + '%';
		if (ring) ring.style.borderColor = s >= 80 ? '#34d399' : s >= 60 ? '#fcd34d' : '#f87171';
	}

	_updateTabBadges() {
		const dm = this.domain, avail = dm.modules_available || {};
		const _b = (id, count) => {
			const el = document.getElementById(`s3-n-${id}`);
			if (!el) return;
			if (count > 0) { el.textContent = count; el.style.display = 'inline'; }
			else { el.style.display = 'none'; }
		};
		_b('meetings', avail.meetings ? (dm.meetings.open_action_items || 0) : 0);
		_b('agm', avail.agm ? (dm.agm.cac_overdue || 0) + (dm.agm.overdue_agm || 0) : 0);
		_b('board', avail.board ? (dm.board.cac_filings_outstanding || 0) : 0);
		_b('correspondence', avail.correspondence ? (dm.correspondence.overdue_response || 0) : 0);
		_b('documents', avail.documents ? (dm.documents.legal_expired || 0) + (dm.documents.legal_expiring_soon || 0) : 0);
		_b('executive', avail.executive ? (dm.executive.overdue_tasks || 0) : 0);
	}

	_buildAlerts() {
		const dm = this.domain, avail = dm.modules_available || {};
		const alerts = [];
		const add = (cls, icon, text, tab) => alerts.push({ cls, icon, text, tab });

		if (avail.agm && dm.agm.cac_overdue > 0) add('sa-r', '🚨', `${dm.agm.cac_overdue} CAC filing(s) OVERDUE`, 'agm');
		if (avail.agm && dm.agm.overdue_agm > 0) add('sa-r', '🏛️', `${dm.agm.overdue_agm} AGM overdue`, 'agm');
		if (avail.board && dm.board.cac_filings_outstanding > 0) add('sa-r', '⚖️', `${dm.board.cac_filings_outstanding} board resolution CAC filing(s) outstanding`, 'board');
		if (avail.correspondence && dm.correspondence.overdue_response > 0) add('sa-a', '📧', `${dm.correspondence.overdue_response} correspondence response(s) overdue`, 'correspondence');
		if (avail.correspondence && dm.correspondence.confidential_open > 0) add('sa-b', '🔒', `${dm.correspondence.confidential_open} confidential item(s) open`, 'correspondence');
		if (avail.documents && dm.documents.legal_expired > 0) add('sa-r', '📁', `${dm.documents.legal_expired} license/permit EXPIRED`, 'documents');
		if (avail.documents && dm.documents.legal_expiring_soon > 0) add('sa-a', '⏰', `${dm.documents.legal_expiring_soon} license/permit expiring soon`, 'documents');
		if (avail.executive && dm.executive.overdue_tasks > 0) add('sa-a', '💼', `${dm.executive.overdue_tasks} executive task(s) overdue`, 'executive');
		if (avail.meetings && dm.meetings.open_action_items > 0) add('sa-b', '📋', `${dm.meetings.open_action_items} meeting action item(s) open`, 'meetings');

		const alertEl = document.getElementById('s3-alerts');
		if (!alertEl) return;
		alertEl.innerHTML = alerts.length > 0
			? alerts.map(a => `<a class="s3-alert ${a.cls}" href="#" onclick="window.__shq._switchTab('${a.tab}');return false">${a.icon} ${a.text}</a>`).join('')
			: '<div class="s3-alert sa-g">✅ No critical secretarial alerts at this time</div>';
	}

	// ── Render dispatcher ─────────────────────────────────────────────────────
	_render(name) {
		const map = {
			overview: () => this._renderOverview(),
			meetings: () => this._renderMeetings(),
			agm: () => this._renderAgm(),
			board: () => this._renderBoard(),
			correspondence: () => this._renderCorrespondence(),
			documents: () => this._renderDocuments(),
			executive: () => this._renderExecutive(),
			ai: () => this._renderAI(),
		};
		if (map[name]) map[name]();
	}

	_fetchTab(key, method, cb) {
		if (this.tabCache[key]) { cb(this.tabCache[key]); return; }
		frappe.call({ method: SHQ_API + method, args: { company: this.company }, callback: r => {
			this.tabCache[key] = r.message || {};
			cb(this.tabCache[key]);
		}});
	}

	// ── Helpers ───────────────────────────────────────────────────────────────
	F(v) {
		const n = parseFloat(v) || 0;
		if (n >= 1e9) return '₦' + (n / 1e9).toFixed(1) + 'B';
		if (n >= 1e6) return '₦' + (n / 1e6).toFixed(1) + 'M';
		if (n >= 1e3) return '₦' + (n / 1e3).toFixed(0) + 'k';
		return '₦' + Math.round(n).toLocaleString();
	}

	B(t, c) { return `<span class="s3-bdg ${c}">${t}</span>`; }

	SB(s) {
		const m = {
			'Compliant': 'bg-g', 'Non-Compliant': 'bg-r', 'Active': 'bg-g', 'Draft': 'bg-gr',
			'Scheduled': 'bg-s', 'Held': 'bg-g', 'Cancelled': 'bg-gr', 'Notice Sent': 'bg-b',
			'Minutes Approved': 'bg-g', 'Closed': 'bg-gr', 'Sent': 'bg-b', 'Responded': 'bg-g',
			'Overdue': 'bg-r', 'Pending': 'bg-gr', 'Pending Response': 'bg-a', 'Routed': 'bg-b',
			'Expired': 'bg-r', 'Pending Renewal': 'bg-a', 'Renewed': 'bg-g', 'Lapsed': 'bg-r',
			'High': 'bg-r', 'Medium': 'bg-a', 'Low': 'bg-g', 'Urgent': 'bg-r',
			'Implemented': 'bg-g', 'In Progress': 'bg-s', 'Not Applicable': 'bg-gr',
			'Requested': 'bg-a', 'Approved': 'bg-g', 'Used': 'bg-b', 'Rejected': 'bg-r',
		};
		return this.B(s || '—', m[s] || 'bg-gr');
	}

	KPI(icon, label, val, sub, link, kc) {
		const onclick = link ? `onclick="frappe.set_route('${link}')"` : '';
		return `<div class="s3-kpi" style="--kc:${kc || 'var(--pri)'}" ${onclick}>
			${icon ? `<div style="font-size:15px;margin-bottom:6px">${icon}</div>` : ''}
			<div class="kp">${label}</div>
			<div class="kv">${val != null ? val : 0}</div>
			<div class="ks">${sub || ''}</div>
		</div>`;
	}

	DC(id) { if (this.charts[id]) { try { this.charts[id].destroy(); } catch (e) { } delete this.charts[id]; } }

	MC(id, cfg) {
		this.DC(id);
		const el = document.getElementById(id);
		if (el) {
			try { const existing = Chart.getChart(id); if (existing) existing.destroy(); } catch (e) { }
			this.charts[id] = new Chart(el, cfg);
		}
	}

	colors() { return ['#1E3A5F', '#059669', '#D97706', '#7C3AED', '#DC2626', '#0284C7', '#F97316', '#22C55E', '#EC4899', '#94A3B8']; }

	TBL(headers, rows, emptyMsg) {
		return `<div class="s3-tw"><table class="s3-tbl"><thead><tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.length ? rows.join('') : `<tr><td colspan="${headers.length}" class="s3-empty">${emptyMsg || 'No records found'}</td></tr>`}</tbody></table></div>`;
	}

	esc(v) { return frappe.utils.escape_html(v == null ? '' : String(v)); }

	// ── OVERVIEW ──────────────────────────────────────────────────────────────
	_renderOverview() {
		const dm = this.domain, avail = dm.modules_available || {};
		const ds = this.score.domain_scores || {};
		const overall = this.score.overall || 0;

		const domainCards = [
			{ key: 'meetings', icon: '📋', label: 'Meetings', avail: avail.meetings, score: ds.meetings, issues: avail.meetings ? (dm.meetings.open_action_items || 0) : 0, tab: 'meetings' },
			{ key: 'agm', icon: '🏛️', label: 'AGM', avail: avail.agm, score: ds.agm, issues: avail.agm ? (dm.agm.cac_overdue || 0) + (dm.agm.overdue_agm || 0) : 0, tab: 'agm' },
			{ key: 'board', icon: '⚖️', label: 'Board', avail: avail.board, score: ds.board, issues: avail.board ? (dm.board.cac_filings_outstanding || 0) : 0, tab: 'board' },
			{ key: 'correspondence', icon: '📧', label: 'Correspondence', avail: avail.correspondence, score: ds.correspondence, issues: avail.correspondence ? (dm.correspondence.overdue_response || 0) : 0, tab: 'correspondence' },
			{ key: 'documents', icon: '📁', label: 'Documents', avail: avail.documents, score: ds.documents, issues: avail.documents ? (dm.documents.legal_expired || 0) : 0, tab: 'documents' },
			{ key: 'executive', icon: '💼', label: 'Executive', avail: avail.executive, score: ds.executive, issues: avail.executive ? (dm.executive.overdue_tasks || 0) : 0, tab: 'executive' },
		].map(d => {
			if (!d.avail) {
				return `<div class="s3-ds" style="opacity:.5" onclick="window.__shq._switchTab('${d.tab}')">
					<div class="s3-ds-i">${d.icon}</div>
					<div class="s3-ds-n">${d.label}</div>
					<div style="font-size:10px;color:var(--tx3);margin-top:4px">Not deployed</div>
				</div>`;
			}
			const s = d.score || 0, col = s >= 80 ? 'var(--grn)' : s >= 60 ? 'var(--amb)' : 'var(--red)';
			return `<div class="s3-ds" onclick="window.__shq._switchTab('${d.tab}')">
				<div class="s3-ds-i">${d.icon}</div>
				<div class="s3-ds-n">${d.label}</div>
				<div class="s3-ds-v" style="color:${col}">${Math.round(s)}%</div>
				${d.issues > 0 ? `<div style="font-size:9px;color:var(--red);font-weight:700;margin-top:2px">${d.issues} issue${d.issues > 1 ? 's' : ''}</div>` : '<div style="font-size:9px;color:var(--grn);margin-top:2px">✅ Clear</div>'}
				<div class="s3-ds-b"><div class="s3-ds-bf" style="width:${s}%;background:${col}"></div></div>
			</div>`;
		}).join('');

		const panel = document.getElementById('s3-p-overview');
		if (!panel) return;

		panel.innerHTML = `
			<div class="s3-card">
			  <div class="s3-ch">
				<div class="s3-ct">📊 Governance Health — All Domains</div>
				<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
				  <div style="font-size:11px;color:var(--tx3)">Overall Governance Score</div>
				  <div style="font-size:22px;font-weight:900;color:${overall >= 80 ? 'var(--grn)' : overall >= 60 ? 'var(--amb)' : 'var(--red)'}">${Math.round(overall)}%</div>
				  <button class="s3-btn sb-g" onclick="window.__shq._exportExcel()">📊 Export Report</button>
				</div>
			  </div>
			  <div class="s3-cb">
				<div style="height:8px;background:var(--brd);border-radius:10px;overflow:hidden;margin-bottom:14px">
				  <div style="height:100%;width:${overall}%;background:${overall >= 80 ? 'var(--grn)' : overall >= 60 ? 'var(--amb)' : 'var(--red)'};transition:width .8s"></div>
				</div>
				<div class="s3-dsg">${domainCards}</div>
			  </div>
			</div>
			<div class="s3-kpis">
			  ${avail.meetings ? this.KPI('📋', 'Meetings This Year', dm.meetings.held_this_year, '', '', 'var(--pri)') : ''}
			  ${avail.agm ? this.KPI('🏛️', 'AGMs Upcoming (90d)', dm.agm.upcoming_90_days, '', '', 'var(--sky)') : ''}
			  ${avail.board ? this.KPI('⚖️', 'Board Resolutions', dm.board.resolutions_total, '', '', 'var(--pri)') : ''}
			  ${avail.correspondence ? this.KPI('📧', 'Correspondence Overdue', dm.correspondence.overdue_response, '', '', 'var(--red)') : ''}
			  ${avail.documents ? this.KPI('📁', 'Licenses Expiring', dm.documents.legal_expiring_soon, '', '', 'var(--amb)') : ''}
			  ${avail.executive ? this.KPI('💼', 'Open Executive Tasks', dm.executive.open_tasks, '', '', 'var(--sky)') : ''}
			</div>
			<div class="s3-card">
				<div class="s3-ch"><div class="s3-ct">📊 Domain Scores</div></div>
				<div class="s3-cb" style="height:240px"><canvas id="s3-ch-domains"></canvas></div>
			</div>
		`;

		this.MC('s3-ch-domains', {
			type: 'bar',
			data: {
				labels: ['Meetings', 'AGM', 'Board', 'Correspondence', 'Documents', 'Executive'],
				datasets: [{
					data: ['meetings', 'agm', 'board', 'correspondence', 'documents', 'executive'].map(k => Math.round(ds[k] || 0)),
					backgroundColor: ['#1E3A5F', '#059669', '#D97706', '#7C3AED', '#DC2626', '#0284C7'],
					borderRadius: 6, barThickness: 32,
				}]
			},
			options: {
				responsive: true, maintainAspectRatio: false,
				plugins: { legend: { display: false } },
				scales: {
					x: { grid: { display: false }, ticks: { color: '#94A3B8', font: { size: 10 } } },
					y: { max: 100, ticks: { color: '#94A3B8', font: { size: 9 }, callback: v => v + '%' }, grid: { color: 'rgba(148,163,184,.08)' } }
				}
			}
		});
	}

	// ── MEETINGS ──────────────────────────────────────────────────────────────
	_renderMeetings() {
		const panel = document.getElementById('s3-p-meetings');
		if (!panel) return;
		if (!this.domain.modules_available?.meetings) {
			panel.innerHTML = `<div class="s3-empty">⚠️ Meeting module not yet deployed on this bench.</div>`;
			return;
		}
		this._fetchTab('meetings', 'get_meetings_tab', data => {
			const s = data.stats || {}, upcoming = data.upcoming || [], recent = data.recent || [];
			panel.innerHTML = `
				<div class="s3-kpis">
					${this.KPI('📋', 'Total Meetings', s.total, '', 'List/Meeting')}
					${this.KPI('✅', 'Held This Year', s.held_this_year, '', '', 'var(--grn)')}
					${this.KPI('⚖️', 'Board Meetings', s.board_meetings, '', '', 'var(--pri)')}
					${this.KPI('🏢', 'Committee Meetings', s.committee_meetings, '', '', 'var(--sky)')}
					${this.KPI('📝', 'Open Action Items', s.open_action_items, '', '', 'var(--amb)')}
					${this.KPI('📊', 'Resolutions Passed', s.total_resolutions_passed, '', '', 'var(--grn)')}
				</div>
				<div class="s3-g21"><div>
					<div class="s3-card"><div class="s3-ch"><div class="s3-ct">📅 Upcoming Meetings (30 days)</div>
						<button class="s3-btn sb-solid" onclick="frappe.new_doc('Meeting')">+ New</button></div>
						${this.TBL(['Meeting', 'Category', 'Date', 'Days', 'Status'],
							upcoming.map(m => `<tr onclick="frappe.set_route('Form','Meeting','${m.name}')">
								<td style="font-weight:600;color:var(--tx1)">${this.esc(m.meeting_title)}</td>
								<td style="font-size:10px">${this.esc(m.meeting_category)}</td>
								<td class="s3-mono" style="font-size:10px">${this.esc(m.meeting_date)}</td>
								<td style="font-weight:700;color:${m.days_to < 0 ? 'var(--red)' : m.days_to <= 2 ? 'var(--amb)' : 'var(--grn)'}">${m.days_to}</td>
								<td>${this.SB(m.status)}</td></tr>`),
							'No upcoming meetings')}
					</div>
					<div class="s3-card"><div class="s3-ch"><div class="s3-ct">📋 Recent Meetings</div></div>
						${this.TBL(['Meeting', 'Category', 'Date', 'Quorum', 'Resolutions', 'Open Actions'],
							recent.map(m => `<tr onclick="frappe.set_route('Form','Meeting','${m.name}')">
								<td style="font-weight:600;color:var(--tx1)">${this.esc(m.meeting_title)}</td>
								<td style="font-size:10px">${this.esc(m.meeting_category)}</td>
								<td class="s3-mono" style="font-size:10px">${this.esc(m.meeting_date)}</td>
								<td>${m.quorum_met ? '✅' : '❌'}</td>
								<td class="s3-mono">${m.resolutions_passed || 0}</td>
								<td class="s3-mono" style="color:${(m.open_action_items || 0) > 0 ? 'var(--red)' : 'var(--grn)'}">${m.open_action_items || 0}</td></tr>`),
							'No meetings recorded yet')}
					</div>
				</div><div>
					<div class="s3-card"><div class="s3-ch"><div class="s3-ct">📊 By Category</div></div>
						<div class="s3-cb">
							${(data.by_category || []).map(c => `<div class="s3-bar-row">
								<div class="s3-bar-lbl">${this.esc(c.meeting_category || 'Other')}</div>
								<div class="s3-bar"><div class="s3-bar-f" style="width:${s.total ? Math.round(c.cnt / s.total * 100) : 0}%;background:var(--pri)"></div></div>
								<div class="s3-bar-val">${c.cnt}</div></div>`).join('') || '<div class="s3-empty">No data</div>'}
						</div>
					</div>
				</div></div>
			`;
		});
	}

	// ── AGM ───────────────────────────────────────────────────────────────────
	_renderAgm() {
		const panel = document.getElementById('s3-p-agm');
		if (!panel) return;
		if (!this.domain.modules_available?.agm) {
			panel.innerHTML = `<div class="s3-empty">⚠️ AGM module not yet deployed on this bench.</div>`;
			return;
		}
		this._fetchTab('agm', 'get_agm_tab', data => {
			const s = data.stats || {}, upcoming = data.upcoming || [], recent = data.recent || [];
			panel.innerHTML = `
				<div class="s3-kpis">
					${this.KPI('🏛️', 'Total AGMs', s.total, '', 'List/Annual General Meeting')}
					${this.KPI('✅', 'Held This Year', s.held_this_year, '', '', 'var(--grn)')}
					${this.KPI('📤', 'CAC Filed', s.cac_filed, '', '', 'var(--grn)')}
					${this.KPI('🚨', 'CAC Overdue', s.cac_overdue, '', '', 'var(--red)')}
					${this.KPI('📋', 'Notice Compliant', s.notice_compliant, '', '', 'var(--sky)')}
					${this.KPI('🔴', 'AGMs Overdue', s.overdue_agm, '', '', 'var(--red)')}
				</div>
				<div class="s3-g21"><div>
					<div class="s3-card"><div class="s3-ch"><div class="s3-ct">📅 Upcoming Obligations (90 days)</div>
						<button class="s3-btn sb-solid" onclick="frappe.new_doc('Annual General Meeting')">+ New AGM</button></div>
						${this.TBL(['Type', 'Title', 'Due', 'Days', 'Status'],
							upcoming.map(o => `<tr onclick="frappe.set_route('Form','Annual General Meeting','${o.doc_name}')">
								<td>${this.B(o.type, o.type === 'AGM' ? 'bg-b' : 'bg-a')}</td>
								<td style="font-weight:600;color:var(--tx1)">${this.esc(o.title)}</td>
								<td class="s3-mono" style="font-size:10px">${this.esc(o.due_date)}</td>
								<td style="font-weight:700;color:${o.overdue ? 'var(--red)' : 'var(--grn)'}">${o.days_to}</td>
								<td>${this.SB(o.status)}</td></tr>`),
							'No upcoming obligations')}
					</div>
					<div class="s3-card"><div class="s3-ch"><div class="s3-ct">📋 Recent AGMs</div></div>
						${this.TBL(['AGM', 'Type', 'Date', 'CAC Filed', 'Quorum', 'Status'],
							recent.map(a => `<tr onclick="frappe.set_route('Form','Annual General Meeting','${a.name}')">
								<td style="font-weight:600;color:var(--tx1)">${this.esc(a.agm_title)}</td>
								<td style="font-size:10px">${this.esc(a.agm_type)}</td>
								<td class="s3-mono" style="font-size:10px">${this.esc(a.agm_date)}</td>
								<td>${a.cac_filed ? '✅' : '❌'}</td>
								<td>${a.quorum_met ? '✅' : '❌'}</td>
								<td>${this.SB(a.status)}</td></tr>`),
							'No AGMs recorded yet')}
					</div>
				</div><div>
					<div class="s3-card"><div class="s3-ch"><div class="s3-ct">📊 CAC Compliance</div></div>
						<div class="s3-cb" style="height:200px;position:relative"><canvas id="s3-ch-agm"></canvas></div>
					</div>
				</div></div>
			`;
			this.MC('s3-ch-agm', {
				type: 'doughnut',
				data: { labels: ['Filed', 'Overdue', 'Other'], datasets: [{ data: [s.cac_filed || 0, s.cac_overdue || 0, Math.max(0, (s.total || 0) - (s.cac_filed || 0) - (s.cac_overdue || 0))], backgroundColor: ['#059669', '#DC2626', '#94A3B8'], borderWidth: 0 }] },
				options: { responsive: true, maintainAspectRatio: false, cutout: '60%', plugins: { legend: { display: true, position: 'bottom', labels: { color: '#94A3B8', font: { size: 9 }, boxWidth: 8 } } } }
			});
		});
	}

	// ── BOARD ─────────────────────────────────────────────────────────────────
	_renderBoard() {
		const panel = document.getElementById('s3-p-board');
		if (!panel) return;
		if (!this.domain.modules_available?.board) {
			panel.innerHTML = `<div class="s3-empty">⚠️ Board Resolution module not yet deployed on this bench.</div>`;
			return;
		}
		this._fetchTab('board', 'get_board_tab', data => {
			panel.innerHTML = `
				<div class="s3-kpis">
					${this.KPI('⚖️', 'Board Resolutions', data.resolutions_total, '', 'List/Board Resolution')}
					${this.KPI('⏳', 'Pending Implementation', data.resolutions_pending_implementation, '', '', 'var(--amb)')}
					${this.KPI('📤', 'CAC Filings Outstanding', data.cac_filings_outstanding, '', '', 'var(--red)')}
					${this.KPI('👥', 'Active Board Members', data.active_board_members, '', '', 'var(--grn)')}
					${this.KPI('⚖️', 'Independent Directors', data.independent_directors, '', '', 'var(--grn)')}
					${this.KPI('🏢', 'Active Committees', data.active_committees, '', '', 'var(--sky)')}
				</div>
				<div class="s3-g21"><div>
					<div class="s3-card"><div class="s3-ch"><div class="s3-ct">⚖️ Board Resolutions</div>
						<button class="s3-btn sb-solid" onclick="frappe.new_doc('Board Resolution')">+ New</button></div>
						${this.TBL(['Resolution', 'Type', 'Date', 'CAC', 'Status'],
							(data.resolutions || []).map(r => `<tr onclick="frappe.set_route('Form','Board Resolution','${r.name}')">
								<td style="font-weight:600;color:var(--tx1)">${this.esc(r.resolution_title)}</td>
								<td style="font-size:10px">${this.esc(r.meeting_type)}</td>
								<td class="s3-mono" style="font-size:10px">${this.esc(r.meeting_date)}</td>
								<td>${r.cac_filing_required ? (r.cac_filed ? this.B('Filed', 'bg-g') : this.B('OUTSTANDING', 'bg-r')) : this.B('N/A', 'bg-gr')}</td>
								<td>${this.SB(r.implementation_status)}</td></tr>`),
							'No board resolutions yet')}
					</div>
					<div class="s3-card" ${(data.pending_signatures || []).length ? '' : 'style="display:none"'}>
						<div class="s3-ch"><div class="s3-ct">✍️ Written Resolutions Awaiting Signature</div></div>
						${this.TBL(['Resolution', 'Deadline'],
							(data.pending_signatures || []).map(s => `<tr onclick="frappe.set_route('Form','Board Resolution','${s.name}')">
								<td style="font-weight:600;color:var(--tx1)">${this.esc(s.resolution_title)}</td>
								<td class="s3-mono" style="font-size:10px">${s.signing_deadline ? this.esc(s.signing_deadline) : '—'}</td></tr>`))}
					</div>
				</div><div>
					<div class="s3-card"><div class="s3-ch"><div class="s3-ct">👥 Active Board Members</div></div>
						<div class="s3-cb">
							${(data.members || []).map(m => `<div style="display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid var(--brd)">
								<div style="font-size:12px;font-weight:600;color:var(--tx1)">${this.esc(m.board_member_name)}</div>
								<div style="display:flex;gap:5px">${m.is_independent ? this.B('Independent', 'bg-g') : ''}<span style="font-size:10px;color:var(--tx3)">${this.esc(m.designation)}</span></div>
							</div>`).join('') || '<div class="s3-empty">No board members recorded</div>'}
						</div>
					</div>
				</div></div>
			`;
		});
	}

	// ── CORRESPONDENCE ────────────────────────────────────────────────────────
	_renderCorrespondence() {
		const panel = document.getElementById('s3-p-correspondence');
		if (!panel) return;
		if (!this.domain.modules_available?.correspondence) {
			panel.innerHTML = `<div class="s3-empty">⚠️ Correspondence module not yet deployed on this bench.</div>`;
			return;
		}
		this._fetchTab('correspondence', 'get_correspondence_tab', data => {
			const s = data.stats || {};
			panel.innerHTML = `
				<div class="s3-kpis">
					${this.KPI('📧', 'Total', s.total, '', 'List/Correspondence')}
					${this.KPI('📥', 'Incoming', s.incoming, '', '', 'var(--sky)')}
					${this.KPI('📤', 'Outgoing', s.outgoing, '', '', 'var(--pri)')}
					${this.KPI('⏳', 'Pending Response', s.pending_response, '', '', 'var(--amb)')}
					${this.KPI('🚨', 'Overdue Response', s.overdue_response, '', '', 'var(--red)')}
					${this.KPI('🔴', 'Urgent Open', s.urgent_open, '', '', 'var(--red)')}
				</div>
				<div class="s3-g21"><div>
					<div class="s3-card"><div class="s3-ch"><div class="s3-ct">🚨 Overdue Items</div>
						<button class="s3-btn sb-solid" onclick="frappe.new_doc('Correspondence')">+ New</button></div>
						${this.TBL(['Subject', 'Type', 'Due', 'Days', 'Status'],
							(data.overdue || []).map(c => `<tr onclick="frappe.set_route('Form','Correspondence','${c.name}')">
								<td style="font-weight:600;color:var(--tx1)">${this.esc(c.subject)}</td>
								<td style="font-size:10px">${this.esc(c.correspondence_type)}</td>
								<td class="s3-mono" style="font-size:10px">${this.esc(c.due_date || c.response_due_date)}</td>
								<td style="font-weight:700;color:${c.overdue ? 'var(--red)' : 'var(--amb)'}">${c.days_to}</td>
								<td>${this.SB(c.status)}</td></tr>`),
							'Nothing overdue ✅')}
					</div>
					<div class="s3-card"><div class="s3-ch"><div class="s3-ct">📋 Recent Correspondence</div></div>
						${this.TBL(['Subject', 'Type', 'Priority', 'Response Status'],
							(data.recent || []).map(c => `<tr onclick="frappe.set_route('Form','Correspondence','${c.name}')">
								<td style="font-weight:600;color:var(--tx1)">${this.esc(c.subject)}</td>
								<td style="font-size:10px">${this.esc(c.correspondence_type)}</td>
								<td>${this.SB(c.priority)}</td>
								<td>${this.SB(c.response_status)}</td></tr>`),
							'No correspondence recorded yet')}
					</div>
				</div><div>
					<div class="s3-card"><div class="s3-ch"><div class="s3-ct">📊 By Type</div></div>
						<div class="s3-cb" style="height:200px;position:relative"><canvas id="s3-ch-corr"></canvas></div>
					</div>
				</div></div>
			`;
			const byType = data.by_type || [];
			this.MC('s3-ch-corr', {
				type: 'doughnut',
				data: { labels: byType.map(t => t.correspondence_type || 'Other'), datasets: [{ data: byType.map(t => t.cnt), backgroundColor: this.colors(), borderWidth: 0 }] },
				options: { responsive: true, maintainAspectRatio: false, cutout: '60%', plugins: { legend: { display: true, position: 'bottom', labels: { color: '#94A3B8', font: { size: 9 }, boxWidth: 8 } } } }
			});
		});
	}

	// ── DOCUMENTS & LEGAL ─────────────────────────────────────────────────────
	_renderDocuments() {
		const panel = document.getElementById('s3-p-documents');
		if (!panel) return;
		if (!this.domain.modules_available?.documents) {
			panel.innerHTML = `<div class="s3-empty">⚠️ Legal Register module not yet deployed on this bench.</div>`;
			return;
		}
		this._fetchTab('documents', 'get_documents_tab', data => {
			const s = data.stats || {};
			panel.innerHTML = `
				<div class="s3-kpis">
					${this.KPI('📁', 'Legal Instruments', s.legal_total, '', 'List/Legal Register')}
					${this.KPI('✅', 'Active', s.legal_active, '', '', 'var(--grn)')}
					${this.KPI('⚠️', 'Expiring Soon', s.legal_expiring_soon, '', '', 'var(--amb)')}
					${this.KPI('🔴', 'Expired', s.legal_expired, '', '', 'var(--red)')}
					${this.KPI('📄', 'Corporate Documents', s.documents_total, '', '', 'var(--pri)')}
					${this.KPI('🔏', 'Seal Requests Pending', s.seal_requests_pending, '', '', 'var(--amb)')}
				</div>
				${(s.legal_expired || 0) > 0 ? `<div style="padding:12px 16px;background:var(--red_x);border:2px solid var(--red);border-radius:10px;margin-bottom:14px;font-size:13px;font-weight:700;color:var(--red)">🚨 ${s.legal_expired} legal instrument(s) EXPIRED — renew immediately.</div>` : ''}
				<div class="s3-g21"><div>
					<div class="s3-card"><div class="s3-ch"><div class="s3-ct">📁 Legal Register — Expiring/Expired</div>
						<button class="s3-btn sb-solid" onclick="frappe.new_doc('Legal Register')">+ New</button></div>
						${this.TBL(['Instrument', 'Authority', 'Expiry', 'Compliance', 'Status'],
							(data.legal || []).map(l => `<tr onclick="frappe.set_route('Form','Legal Register','${l.name}')">
								<td style="font-weight:600;color:var(--tx1)">${this.esc(l.instrument_title)}</td>
								<td style="font-size:10px">${this.esc(l.issuing_authority)}</td>
								<td class="s3-mono" style="font-size:10px">${this.esc(l.expiry_date)}</td>
								<td>${this.SB(l.compliance_status)}</td>
								<td>${this.SB(l.status)}</td></tr>`),
							'No legal instruments recorded')}
					</div>
					<div class="s3-card"><div class="s3-ch"><div class="s3-ct">📄 Corporate Documents</div>
						<button class="s3-btn sb-solid" onclick="frappe.new_doc('Corporate Document')">+ New</button></div>
						${this.TBL(['Document', 'Type', 'Expiry', 'Status'],
							(data.documents || []).map(d => `<tr onclick="frappe.set_route('Form','Corporate Document','${d.name}')">
								<td style="font-weight:600;color:var(--tx1)">${this.esc(d.document_title)}</td>
								<td style="font-size:10px">${this.esc(d.document_type)}</td>
								<td class="s3-mono" style="font-size:10px">${d.expiry_date ? this.esc(d.expiry_date) : '—'}</td>
								<td>${this.SB(d.status)}</td></tr>`),
							'No corporate documents recorded')}
					</div>
				</div><div>
					<div class="s3-card"><div class="s3-ch"><div class="s3-ct">🔏 Pending Seal Requests</div></div>
						<div class="s3-cb">
							${(data.pending_seals || []).map(sr => `<div style="padding:8px 0;border-bottom:1px solid var(--brd);cursor:pointer" onclick="frappe.set_route('Form','Company Seal Register','${sr.name}')">
								<div style="font-size:12px;font-weight:600;color:var(--tx1)">${this.esc(sr.seal_request_title)}</div>
								<div style="font-size:10px;color:var(--tx3)">${this.esc(sr.requested_by)} · ${this.esc(sr.request_date)}</div>
							</div>`).join('') || '<div class="s3-empty">No pending requests ✅</div>'}
						</div>
					</div>
				</div></div>
			`;
		});
	}

	// ── EXECUTIVE ─────────────────────────────────────────────────────────────
	_renderExecutive() {
		const panel = document.getElementById('s3-p-executive');
		if (!panel) return;
		if (!this.domain.modules_available?.executive) {
			panel.innerHTML = `<div class="s3-empty">⚠️ Executive Support module not yet deployed on this bench.</div>`;
			return;
		}
		this._fetchTab('executive', 'get_executive_tab', data => {
			const s = data.stats || {};
			panel.innerHTML = `
				<div class="s3-kpis">
					${this.KPI('📅', 'Appointments Today', s.appointments_today, '', '', 'var(--pri)')}
					${this.KPI('📆', 'This Week', s.appointments_this_week, '', '', 'var(--sky)')}
					${this.KPI('📝', 'Open Tasks', s.open_tasks, '', '', 'var(--amb)')}
					${this.KPI('🚨', 'Overdue Tasks', s.overdue_tasks, '', '', 'var(--red)')}
					${this.KPI('📨', 'Awaiting Acknowledgement', s.communications_awaiting_ack, '', '', 'var(--amb)')}
				</div>
				<div class="s3-g21"><div>
					<div class="s3-card"><div class="s3-ch"><div class="s3-ct">📅 Today's Appointments</div></div>
						${this.TBL(['Time', 'Title', 'Type', 'With'],
							(data.todays_appointments || []).map(a => `<tr onclick="frappe.set_route('Form','Executive Appointment','${a.name}')">
								<td class="s3-mono" style="font-size:10px">${this.esc(a.start_time)}</td>
								<td style="font-weight:600;color:var(--tx1)">${this.esc(a.appointment_title)}</td>
								<td style="font-size:10px">${this.esc(a.appointment_type)}</td>
								<td style="font-size:10px">${a.meeting_with ? this.esc(a.meeting_with) : '—'}</td></tr>`),
							'Nothing scheduled today')}
					</div>
					<div class="s3-card"><div class="s3-ch"><div class="s3-ct">📝 Open Executive Tasks</div>
						<button class="s3-btn sb-solid" onclick="frappe.new_doc('Executive Task')">+ New</button></div>
						${this.TBL(['Task', 'Assigned To', 'Due', 'Priority', 'Status'],
							(data.open_tasks || []).map(t => `<tr onclick="frappe.set_route('Form','Executive Task','${t.name}')">
								<td style="font-weight:600;color:var(--tx1)">${this.esc(t.task_title)}</td>
								<td style="font-size:10px">${this.esc(t.assigned_to)}</td>
								<td class="s3-mono" style="font-size:10px">${t.due_date ? this.esc(t.due_date) : '—'}</td>
								<td>${this.SB(t.priority)}</td>
								<td>${this.SB(t.status)}</td></tr>`),
							'No open tasks ✅')}
					</div>
				</div><div>
					<div class="s3-card"><div class="s3-ch"><div class="s3-ct">🎂 Birthdays & Anniversaries</div></div>
						<div class="s3-cb">
							${(data.birthdays || []).map(b => `<div style="padding:6px 0;border-bottom:1px solid var(--brd);font-size:12px">🎂 ${this.esc(b.employee_name)} — ${this.esc(b.next_birthday)}</div>`).join('')}
							${(data.anniversaries || []).map(a => `<div style="padding:6px 0;border-bottom:1px solid var(--brd);font-size:12px">🏅 ${this.esc(a.employee_name)} — ${a.years} yr(s)</div>`).join('')}
							${(!(data.birthdays || []).length && !(data.anniversaries || []).length) ? '<div class="s3-empty">Nothing in the next 14 days</div>' : ''}
						</div>
					</div>
				</div></div>
			`;
		});
	}

	// ── AI ANALYSIS ───────────────────────────────────────────────────────────
	_renderAI() {
		const ds = this.score.domain_scores || {}, overall = this.score.overall || 0;
		const labels = { meetings: '📋 Meetings', agm: '🏛️ AGM', board: '⚖️ Board', correspondence: '📧 Correspondence', documents: '📁 Documents', executive: '💼 Executive' };
		const domainBars = Object.entries(ds).map(([k, v]) => {
			const score = Math.round(v || 0), col = score >= 80 ? 'var(--grn)' : score >= 60 ? 'var(--amb)' : 'var(--red)';
			return `<div class="s3-bar-row"><div class="s3-bar-lbl">${labels[k] || k}</div>
				<div class="s3-bar"><div class="s3-bar-f" style="width:${score}%;background:${col}"></div></div>
				<div class="s3-bar-val" style="color:${col}">${score}%</div></div>`;
		}).join('');

		const panel = document.getElementById('s3-p-ai');
		if (!panel) return;
		panel.innerHTML = `
			<div class="s3-g2">
				<div class="s3-card"><div class="s3-ch"><div class="s3-ct">📊 Governance Score — All Domains</div></div>
					<div class="s3-cb">
						<div style="display:flex;align-items:center;gap:14px;margin-bottom:18px;flex-wrap:wrap">
							<div style="width:76px;height:76px;border-radius:50%;border:5px solid ${overall >= 80 ? 'var(--grn)' : overall >= 60 ? 'var(--amb)' : 'var(--red)'};display:flex;flex-direction:column;align-items:center;justify-content:center;flex-shrink:0">
								<div style="font-size:20px;font-weight:900;color:${overall >= 80 ? 'var(--grn)' : overall >= 60 ? 'var(--amb)' : 'var(--red)'}">${Math.round(overall)}</div>
								<div style="font-size:9px;color:var(--tx3)">/ 100</div>
							</div>
							<div style="flex:1;min-width:150px">
								<div style="height:9px;background:var(--brd);border-radius:10px;overflow:hidden;margin-bottom:7px">
									<div style="height:100%;width:${overall}%;background:${overall >= 80 ? 'var(--grn)' : overall >= 60 ? 'var(--amb)' : 'var(--red)'};transition:width .8s"></div>
								</div>
								<div style="font-size:11px;color:var(--tx3)">Weighted governance score across all deployed secretarial domains</div>
							</div>
						</div>
						${domainBars || '<div class="s3-empty">No domain data yet</div>'}
					</div>
				</div>
				<div class="s3-card"><div class="s3-ch"><div class="s3-ct">🤖 AI Governance Analyst</div><span id="s3-ai-status" style="font-size:10px;color:var(--tx3)">Ready</span></div>
					<div class="s3-cb">
						<div style="display:flex;flex-direction:column;gap:8px;margin-bottom:14px">
							<button class="s3-btn sb-solid" id="s3-ai-btn" onclick="window.__shq._runAI()" style="justify-content:center">✨ Run Full AI Governance Analysis</button>
							<button class="s3-btn sb-g" onclick="window.__shq._exportExcel()" style="justify-content:center">📊 Download Excel Report</button>
						</div>
						<div id="s3-ai-out">
							<div style="padding:14px;background:var(--bg2);border-radius:10px;font-size:12px;color:var(--tx2);line-height:1.6">
								Click <b>Run Full AI Governance Analysis</b> to send live data from every secretarial domain for risk assessment and a prioritised action plan.
								<br><br>
								<span style="color:var(--amb)">⚠️ Requires your AI provider integration to be wired into <code>ai_assistant_api._call_ai()</code> first — see the notes in that file.</span>
							</div>
						</div>
					</div>
				</div>
			</div>
		`;
	}

	async _runAI() {
		if (!this.company) { frappe.msgprint('Please select a company first.'); return; }
		const btn = document.getElementById('s3-ai-btn');
		const out = document.getElementById('s3-ai-out');
		const stat = document.getElementById('s3-ai-status');
		if (btn) { btn.textContent = '⟳ Analysing…'; btn.disabled = true; }
		if (stat) stat.textContent = 'Calling AI…';
		if (out) out.innerHTML = `<div style="text-align:center;padding:24px;color:var(--tx3)"><span class="s3-spin" style="font-size:24px">⟳</span><br><div style="margin-top:8px;font-size:12px">Sending all domain data to the AI provider…</div></div>`;
		try {
			const r = await frappe.call({ method: SHQ_API + 'get_ai_secretarial_analysis', args: { company: this.company } });
			if (r.message?.success) {
				let parsed = {};
				try {
					const raw = r.message.analysis || '';
					const match = (typeof raw === 'string' ? raw : JSON.stringify(raw)).match(/\{[\s\S]*\}/);
					if (match) parsed = JSON.parse(match[0]);
				} catch (e) {
					parsed = { summary: String(r.message.analysis || '').substring(0, 800) };
				}
				const riskCol = { Critical: 'var(--red)', High: 'var(--amb)', Medium: 'var(--sky)', Low: 'var(--grn)' }[parsed.risk_level] || 'var(--tx2)';
				const actsHTML = (parsed.actions || []).map((a, i) => `
					<div style="display:flex;align-items:flex-start;gap:9px;padding:9px 11px;background:var(--bg2);border-radius:8px;margin-bottom:7px">
						<div style="background:${riskCol};color:#fff;font-size:10px;font-weight:800;width:20px;height:20px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0">${i + 1}</div>
						<div><div style="font-size:12px;font-weight:700;color:var(--tx1)">${this.esc(a.action || '')}</div>
						<div style="font-size:10px;color:var(--tx3);margin-top:2px">Deadline: ${this.esc(a.deadline || '—')} · Authority: ${this.esc(a.authority || '—')}</div></div>
					</div>`).join('');
				if (out) out.innerHTML = `
					<div style="padding:13px;background:${riskCol === 'var(--red)' ? 'var(--red_x)' : 'var(--pri_x)'};border-left:4px solid ${riskCol};border-radius:8px;margin-bottom:13px">
						<div style="font-size:14px;font-weight:700;color:var(--tx1)">${parsed.risk_level ? `[${this.esc(parsed.risk_level)} Risk] ` : ''}${this.esc(parsed.summary || 'AI analysis complete')}</div>
					</div>
					${actsHTML ? `<div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--tx3);margin-bottom:8px">Priority Actions</div>${actsHTML}` : ''}
					${parsed.strategic_recommendation ? `<div style="padding:11px;background:var(--grn_x);border-radius:8px;font-size:12px;color:var(--tx1);border-left:3px solid var(--grn)"><b>Strategic Recommendation:</b> ${this.esc(parsed.strategic_recommendation)}</div>` : ''}
					<div style="font-size:10px;color:var(--tx3);margin-top:10px">Analysis at ${new Date().toLocaleTimeString('en-NG', { hour12: true })}</div>`;
				if (stat) stat.textContent = 'Done';
			} else {
				if (out) out.innerHTML = `<div style="padding:13px;background:var(--red_x);border-radius:8px;font-size:12px;color:var(--red)">AI analysis failed: ${this.esc(r.message?.error || 'Unknown error')}</div>`;
				if (stat) stat.textContent = 'Failed';
			}
		} catch (e) {
			if (out) out.innerHTML = `<div style="padding:13px;background:var(--red_x);border-radius:8px;font-size:12px;color:var(--red)">Error: ${this.esc(e.message)}</div>`;
		}
		if (btn) { btn.textContent = '✨ Run Full AI Governance Analysis'; btn.disabled = false; }
	}

	// ── EXPORT EXCEL ──────────────────────────────────────────────────────────
	_exportExcel() {
		if (!this.company) { frappe.msgprint('Please select a company first.'); return; }
		frappe.show_alert({ message: '📊 Generating Excel report…', indicator: 'blue' });
		frappe.call({
			method: SHQ_API + 'export_secretarial_report',
			args: { company: this.company, format: 'xlsx' },
			freeze: true,
			freeze_message: 'Generating secretarial report…',
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
}

// ── Module helpers ────────────────────────────────────────────────────────────
function _shqLsGet(k, def) { try { return localStorage.getItem(k) || def; } catch (e) { return def; } }
function _shqLsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { } }
