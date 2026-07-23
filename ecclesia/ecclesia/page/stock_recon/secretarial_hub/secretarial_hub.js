// Copyright (c) 2026, Value Impacts Consulting
// ecclesia/ecclesia/page/secretarial_hub/secretarial_hub.js
//
// ╔══════════════════════════════════════════════════════════════════════════╗
// ║   SECRETARIAL HUB — World-Class Corporate Governance Desktop             ║
// ║   9 Themes (localStorage only) · 3 Tabs · Full CRUD · Live data         ║
// ╚══════════════════════════════════════════════════════════════════════════╝

frappe.pages['secretarial-hub'].on_page_load = function(wrapper) {
    // Ensure the page object exists
    frappe.pages['secretarial-hub'] = frappe.pages['secretarial-hub'] || {};
    
    const boot = function() {
        if (typeof SecretarialHub === 'undefined') {
            // If class not defined yet, define it
            initSecretarialHub(wrapper);
        } else {
            new SecretarialHub(wrapper);
        }
    };

    // Load Font Awesome if not present
    if (!document.getElementById('fa-sh')) {
        const fa = document.createElement('link');
        fa.id = 'fa-sh';
        fa.rel = 'stylesheet';
        fa.href = 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css';
        fa.onload = boot;
        fa.onerror = boot;
        document.head.appendChild(fa);
    } else {
        boot();
    }
};

// ═══════════════════════════════════════════════════════════════════════════
//  THEME REGISTRY — 9 Themes, pure localStorage, zero DB dependency
// ═══════════════════════════════════════════════════════════════════════════
const SH_THEMES = {
    corporate: {
        name: 'Corporate', icon: '🏛️', isDark: false,
        colors: {
            bg: '#F8FAFC', bg2: '#F1F5F9', bg3: '#E2E8F0', card: '#FFFFFF',
            brd: '#E2E8F0', brd2: '#CBD5E1', tx1: '#0F172A', tx2: '#475569', tx3: '#94A3B8',
            pri: '#1E3A5F', pri_d: '#0F2A45', pri2: '#4A6A8F', pri_x: 'rgba(30,58,95,.08)',
            acc: '#2563EB', acc_x: 'rgba(37,99,235,.10)',
            grn: '#059669', grn_x: 'rgba(5,150,105,.08)',
            red: '#DC2626', red_x: 'rgba(220,38,38,.08)',
            amb: '#D97706', amb_x: 'rgba(217,119,6,.08)',
            sky: '#0EA5E9', sky_x: 'rgba(14,165,233,.08)',
            pink: '#EC4899', pink_x: 'rgba(236,72,153,.08)',
            banner: 'linear-gradient(135deg,#0F172A 0%,#1E3A5F 40%,#2563EB 70%,#0EA5E9 100%)'
        }
    },
    navy: {
        name: 'Navy', icon: '⚓', isDark: false,
        colors: {
            bg: '#F0F4F8', bg2: '#E2E8F0', bg3: '#CBD5E1', card: '#FFFFFF',
            brd: '#CBD5E1', brd2: '#94A3B8', tx1: '#0F172A', tx2: '#334155', tx3: '#64748B',
            pri: '#1E293B', pri_d: '#0F172A', pri2: '#475569', pri_x: 'rgba(30,41,59,.08)',
            acc: '#3B82F6', acc_x: 'rgba(59,130,246,.10)',
            grn: '#10B981', grn_x: 'rgba(16,185,129,.08)',
            red: '#EF4444', red_x: 'rgba(239,68,68,.08)',
            amb: '#F59E0B', amb_x: 'rgba(245,158,11,.08)',
            sky: '#06B6D4', sky_x: 'rgba(6,182,212,.08)',
            pink: '#EC4899', pink_x: 'rgba(236,72,153,.08)',
            banner: 'linear-gradient(135deg,#0F172A 0%,#1E293B 40%,#3B82F6 70%,#06B6D4 100%)'
        }
    },
    emerald: {
        name: 'Emerald', icon: '💎', isDark: false,
        colors: {
            bg: '#ECFDF5', bg2: '#D1FAE5', bg3: '#A7F3D0', card: '#FFFFFF',
            brd: '#A7F3D0', brd2: '#6EE7B7', tx1: '#022C22', tx2: '#065F46', tx3: '#34D399',
            pri: '#059669', pri_d: '#047857', pri2: '#34D399', pri_x: 'rgba(5,150,105,.08)',
            acc: '#0D9488', acc_x: 'rgba(13,148,136,.10)',
            grn: '#10B981', grn_x: 'rgba(16,185,129,.08)',
            red: '#EF4444', red_x: 'rgba(239,68,68,.08)',
            amb: '#F59E0B', amb_x: 'rgba(245,158,11,.08)',
            sky: '#0EA5E9', sky_x: 'rgba(14,165,233,.08)',
            pink: '#EC4899', pink_x: 'rgba(236,72,153,.08)',
            banner: 'linear-gradient(135deg,#022C22 0%,#047857 40%,#059669 70%,#0D9488 100%)'
        }
    },
    midnight: {
        name: 'Midnight', icon: '🌙', isDark: true,
        colors: {
            bg: '#0F172A', bg2: '#1E293B', bg3: '#334155', card: '#1E293B',
            brd: 'rgba(255,255,255,.08)', brd2: 'rgba(255,255,255,.14)',
            tx1: '#F1F5F9', tx2: '#94A3B8', tx3: '#64748B',
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
    rose: {
        name: 'Rose', icon: '🌹', isDark: false,
        colors: {
            bg: '#FFF1F2', bg2: '#FFE4E6', bg3: '#FECDD3', card: '#FFFFFF',
            brd: '#FECDD3', brd2: '#FDA4AF', tx1: '#4C0519', tx2: '#881337', tx3: '#FB7185',
            pri: '#BE123C', pri_d: '#881337', pri2: '#F43F5E', pri_x: 'rgba(190,18,60,.08)',
            acc: '#EC4899', acc_x: 'rgba(236,72,153,.10)',
            grn: '#10B981', grn_x: 'rgba(16,185,129,.08)',
            red: '#EF4444', red_x: 'rgba(239,68,68,.08)',
            amb: '#F59E0B', amb_x: 'rgba(245,158,11,.08)',
            sky: '#0EA5E9', sky_x: 'rgba(14,165,233,.08)',
            pink: '#EC4899', pink_x: 'rgba(236,72,153,.08)',
            banner: 'linear-gradient(135deg,#4C0519 0%,#881337 40%,#BE123C 70%,#EC4899 100%)'
        }
    },
    aurora: {
        name: 'Aurora', icon: '🌌', isDark: true,
        colors: {
            bg: '#0F172A', bg2: '#1E1B4B', bg3: '#312E81', card: '#1E1B4B',
            brd: 'rgba(255,255,255,.08)', brd2: 'rgba(255,255,255,.14)',
            tx1: '#F1F5F9', tx2: '#A5B4FC', tx3: '#818CF8',
            pri: '#7C3AED', pri_d: '#6D28D9', pri2: '#A78BFA', pri_x: 'rgba(124,58,237,.12)',
            acc: '#8B5CF6', acc_x: 'rgba(139,92,246,.12)',
            grn: '#34D399', grn_x: 'rgba(52,211,153,.12)',
            red: '#F87171', red_x: 'rgba(248,113,113,.12)',
            amb: '#FCD34D', amb_x: 'rgba(252,211,77,.12)',
            sky: '#38BDF8', sky_x: 'rgba(56,189,248,.12)',
            pink: '#F9A8D4', pink_x: 'rgba(249,168,212,.12)',
            banner: 'linear-gradient(135deg,#0F172A 0%,#1E1B4B 40%,#7C3AED 70%,#8B5CF6 100%)'
        }
    },
    gold: {
        name: 'Gold', icon: '👑', isDark: false,
        colors: {
            bg: '#FFFBEB', bg2: '#FEF3C7', bg3: '#FDE68A', card: '#FFFFFF',
            brd: '#FDE68A', brd2: '#FCD34D', tx1: '#451A03', tx2: '#78350F', tx3: '#D97706',
            pri: '#B45309', pri_d: '#92400E', pri2: '#D97706', pri_x: 'rgba(180,83,9,.08)',
            acc: '#F59E0B', acc_x: 'rgba(245,158,11,.10)',
            grn: '#059669', grn_x: 'rgba(5,150,105,.08)',
            red: '#DC2626', red_x: 'rgba(220,38,38,.08)',
            amb: '#D97706', amb_x: 'rgba(217,119,6,.08)',
            sky: '#0EA5E9', sky_x: 'rgba(14,165,233,.08)',
            pink: '#EC4899', pink_x: 'rgba(236,72,153,.08)',
            banner: 'linear-gradient(135deg,#451A03 0%,#78350F 40%,#B45309 70%,#F59E0B 100%)'
        }
    },
    slate: {
        name: 'Slate', icon: '🪨', isDark: true,
        colors: {
            bg: '#0F172A', bg2: '#1E293B', bg3: '#334155', card: '#0F172A',
            brd: 'rgba(255,255,255,.06)', brd2: 'rgba(255,255,255,.10)',
            tx1: '#F8FAFC', tx2: '#94A3B8', tx3: '#475569',
            pri: '#64748B', pri_d: '#475569', pri2: '#94A3B8', pri_x: 'rgba(100,116,139,.12)',
            acc: '#94A3B8', acc_x: 'rgba(148,163,184,.12)',
            grn: '#34D399', grn_x: 'rgba(52,211,153,.12)',
            red: '#F87171', red_x: 'rgba(248,113,113,.12)',
            amb: '#FCD34D', amb_x: 'rgba(252,211,77,.12)',
            sky: '#38BDF8', sky_x: 'rgba(56,189,248,.12)',
            pink: '#F9A8D4', pink_x: 'rgba(249,168,212,.12)',
            banner: 'linear-gradient(135deg,#020617 0%,#0F172A 50%,#1E293B 70%,#334155 100%)'
        }
    },
    ocean: {
        name: 'Ocean', icon: '🌊', isDark: false,
        colors: {
            bg: '#F0F9FF', bg2: '#E0F2FE', bg3: '#BAE6FD', card: '#FFFFFF',
            brd: '#BAE6FD', brd2: '#7DD3FC', tx1: '#0C4A6E', tx2: '#075985', tx3: '#38BDF8',
            pri: '#0EA5E9', pri_d: '#0284C7', pri2: '#38BDF8', pri_x: 'rgba(14,165,233,.08)',
            acc: '#38BDF8', acc_x: 'rgba(56,189,248,.10)',
            grn: '#10B981', grn_x: 'rgba(16,185,129,.08)',
            red: '#EF4444', red_x: 'rgba(239,68,68,.08)',
            amb: '#F59E0B', amb_x: 'rgba(245,158,11,.08)',
            sky: '#06B6D4', sky_x: 'rgba(6,182,212,.08)',
            pink: '#EC4899', pink_x: 'rgba(236,72,153,.08)',
            banner: 'linear-gradient(135deg,#0C4A6E 0%,#0369A1 40%,#0EA5E9 70%,#06B6D4 100%)'
        }
    }
};

// ═══════════════════════════════════════════════════════════════════════════
//  MAIN CLASS DEFINITION
// ═══════════════════════════════════════════════════════════════════════════
function initSecretarialHub(wrapper) {
    class SecretarialHub {
        constructor(wrapper) {
            this.wrapper = wrapper;
            this.page = wrapper.page;
            this.company = frappe.defaults.get_default('company') || '';
            this.active_tab = 'secretary';
            this.data = {};
            this.timers = {};

            // Restore theme from localStorage
            this.activeTheme = (() => {
                try { return localStorage.getItem('sh-studio-theme') || 'corporate'; }
                catch(e) { return 'corporate'; }
            })();

            window.__sh = this;
            this.boot();
        }

        boot() {
            this.injectCSS();
            this.buildShell();
            this.applyTheme(this.activeTheme);
            this.bindEvents();
            this.load_tab('secretary');
            this.startClock();
            this.startAutoRefresh();
        }

        // ═══════════════════════════════════════════════════════════════════════════
        //  CSS INJECTION
        // ═══════════════════════════════════════════════════════════════════════════
        injectCSS() {
            if (document.getElementById('sh-css')) return;
            const s = document.createElement('style');
            s.id = 'sh-css';
            s.textContent = `
        /* ═══════════════════════════════════════════════════════════
           SECRETARIAL HUB — Value Impacts / Ecclesia
           Craft-quality design · 3 Tabs · Live data
        ═══════════════════════════════════════════════════════════ */
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700;800&family=Space+Mono:wght@400;700&display=swap');

        #sh-root {
          --bg:      #F8FAFC;
          --bg2:     #F1F5F9;
          --bg3:     #E2E8F0;
          --card:    #FFFFFF;
          --brd:     #E2E8F0;
          --brd2:    #CBD5E1;
          --tx1:     #0F172A;
          --tx2:     #475569;
          --tx3:     #94A3B8;
          --pri:     #1E3A5F;
          --pri_d:   #0F2A45;
          --pri2:    #4A6A8F;
          --pri_x:   rgba(30,58,95,.08);
          --acc:     #2563EB;
          --acc_x:   rgba(37,99,235,.10);
          --grn:     #059669;
          --grn_x:   rgba(5,150,105,.08);
          --red:     #DC2626;
          --red_x:   rgba(220,38,38,.08);
          --amb:     #D97706;
          --amb_x:   rgba(217,119,6,.08);
          --sky:     #0EA5E9;
          --sky_x:   rgba(14,165,233,.08);
          --pink:    #EC4899;
          --pink_x:  rgba(236,72,153,.08);
          font-family: 'DM Sans', system-ui, sans-serif;
          background: var(--bg);
          color: var(--tx1);
          min-height: 100vh;
          transition: background 0.3s ease, color 0.3s ease;
        }

        #sh-root.dark-mode input,
        #sh-root.dark-mode select,
        #sh-root.dark-mode textarea {
          color-scheme: dark;
        }

        #sh-root * { box-sizing: border-box; }

        /* ── TOPBAR ── */
        .sh-topbar {
          position: sticky; top: 0; z-index: 100;
          background: var(--card); opacity: 0.97;
          backdrop-filter: blur(20px);
          border-bottom: 1px solid var(--brd);
          display: flex; align-items: center; gap: 0;
          height: 56px; padding: 0 24px;
        }
        .sh-logo {
          display: flex; align-items: center; gap: 10px;
          font-family: 'Space Mono', monospace; font-size: 14px; font-weight: 700;
          color: var(--tx1); letter-spacing: -.5px; margin-right: 28px;
        }
        .sh-logo-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--pri); animation: sh-pulse 2s infinite; }
        @keyframes sh-pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.5;transform:scale(1.4)} }

        .sh-nav { display: flex; align-items: center; gap: 2px; flex: 1; }
        .sh-nav-btn {
          display: flex; align-items: center; gap: 7px;
          padding: 6px 14px; border-radius: 8px;
          font-size: 12px; font-weight: 600; color: var(--tx2);
          cursor: pointer; transition: all .15s; border: none; background: none;
          white-space: nowrap; font-family: inherit;
        }
        .sh-nav-btn:hover    { color: var(--tx1); background: var(--bg3); }
        .sh-nav-btn.active   { color: var(--pri2); background: var(--pri_x); }

        .sh-topbar-right { display: flex; align-items: center; gap: 10px; margin-left: auto; }
        .sh-clock { font-family: 'Space Mono', monospace; font-size: 11px; color: var(--tx3); }
        .sh-theme-btn {
          display: inline-flex; align-items: center; gap: 6px;
          padding: 5px 11px; border-radius: 8px; font-size: 11px; font-weight: 600;
          color: var(--tx2); background: var(--bg3); border: 1px solid var(--brd2);
          cursor: pointer; transition: all 0.15s ease; font-family: inherit; white-space: nowrap;
        }
        .sh-theme-btn:hover { background: var(--pri_x); color: var(--pri2); border-color: var(--pri); }
        .sh-sync-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--grn); animation: sh-pulse 3s infinite; }

        /* ── CONTENT AREA ── */
        .sh-content-wrap { padding: 24px; max-width: 1600px; margin: 0 auto; }

        /* ── TABS ── */
        .sh-tabs {
          display: flex; gap: 4px;
          border-bottom: 2px solid var(--brd);
          margin-bottom: 24px;
          padding-bottom: 2px;
        }
        .sh-tab {
          padding: 10px 20px;
          font-size: 13px; font-weight: 700;
          color: var(--tx3);
          background: none; border: none;
          border-bottom: 3px solid transparent;
          cursor: pointer;
          transition: all .15s;
          font-family: 'DM Sans', system-ui, sans-serif;
          display: flex; align-items: center; gap: 8px;
        }
        .sh-tab:hover { color: var(--tx1); background: var(--bg2); border-radius: 8px 8px 0 0; }
        .sh-tab.on { color: var(--pri); border-bottom-color: var(--pri); background: var(--pri_x); border-radius: 8px 8px 0 0; }
        .sh-tab-badge {
          background: var(--red); color: #fff;
          font-size: 9px; font-weight: 800;
          padding: 1px 6px; border-radius: 10px;
          min-width: 16px; text-align: center;
        }

        /* ── KPI ROW ── */
        .sh-kpis { display: grid; grid-template-columns: repeat(auto-fit,minmax(160px,1fr)); gap: 14px; margin-bottom: 22px; }
        .sh-kpi {
          background: var(--card); border: 1px solid var(--brd);
          border-radius: 14px; padding: 18px 20px;
          cursor: pointer; transition: all .2s; position: relative; overflow: hidden;
        }
        .sh-kpi::after { content:''; position:absolute; top:0; left:0; right:0; height:3px; background:var(--kc,var(--pri)); }
        .sh-kpi:hover { transform: translateY(-2px); border-color: var(--brd2); background: var(--bg3); }
        .sh-kpi-icon { font-size: 18px; margin-bottom: 10px; }
        .sh-kpi-lbl  { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .8px; color: var(--tx3); margin-bottom: 6px; }
        .sh-kpi-val  { font-size: 28px; font-weight: 800; color: var(--tx1); line-height: 1; margin-bottom: 3px; }
        .sh-kpi-sub  { font-size: 11px; color: var(--tx3); }

        /* ── CARD ── */
        .sh-card {
          background: var(--card); border: 1px solid var(--brd);
          border-radius: 16px; overflow: hidden;
          transition: box-shadow .2s;
          margin-bottom: 18px;
        }
        .sh-card:hover { box-shadow: 0 4px 30px rgba(0,0,0,.08); border-color: var(--brd2); }
        .sh-card-head {
          padding: 14px 20px; border-bottom: 1px solid var(--brd);
          display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;
          background: var(--bg2);
        }
        .sh-card-title { display: flex; align-items: center; gap: 10px; font-size: 13px; font-weight: 700; color: var(--tx1); }
        .sh-title-icon { width: 28px; height: 28px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 13px; }
        .sh-card-body  { padding: 18px 20px; }

        /* ── TABLE ── */
        .sh-tbl-wrap { overflow-x: auto; max-height: 480px; overflow-y: auto;
          scrollbar-width: thin; scrollbar-color: var(--brd2) transparent; }
        .sh-tbl { width: 100%; border-collapse: collapse; font-size: 12px; }
        .sh-tbl thead th {
          padding: 10px 14px; text-align: left;
          font-size: 10px; font-weight: 700; text-transform: uppercase;
          letter-spacing: .5px; color: var(--tx3);
          background: var(--bg2); border-bottom: 1px solid var(--brd2);
          position: sticky; top: 0; z-index: 2; white-space: nowrap;
        }
        .sh-tbl tbody td { padding: 10px 14px; border-bottom: 1px solid var(--brd); color: var(--tx2); }
        .sh-tbl tbody tr { cursor: pointer; transition: background .1s; }
        .sh-tbl tbody tr:hover { background: var(--pri_x); }
        .sh-tbl tbody tr:hover td { color: var(--tx1); }
        .sh-tbl tbody tr:last-child td { border-bottom: none; }

        /* ── BADGES ── */
        .sh-badge {
          display: inline-flex; align-items: center; gap: 4px;
          padding: 3px 9px; border-radius: 20px;
          font-size: 10px; font-weight: 700; white-space: nowrap;
        }
        .bd-pri  { background: var(--pri_x);   color: var(--pri2); }
        .bd-grn  { background: var(--grn_x);   color: var(--grn);  }
        .bd-red  { background: var(--red_x);   color: var(--red);  }
        .bd-amb  { background: var(--amb_x);   color: var(--amb);  }
        .bd-sky  { background: var(--sky_x);   color: var(--sky);  }
        .bd-acc  { background: var(--acc_x);   color: var(--acc);  }
        .bd-grey { background: var(--bg3);     color: var(--tx3); border: 1px solid var(--brd2); }

        /* ── EMPTY STATE ── */
        .sh-empty {
          text-align: center; padding: 32px 24px; color: var(--tx3);
        }
        .sh-empty-icon { font-size: 36px; margin-bottom: 12px; }
        .sh-empty h4 { font-size: 14px; font-weight: 700; color: var(--tx2); margin: 0 0 6px; }
        .sh-empty p  { font-size: 12px; margin: 0 0 16px; }

        /* ── LOADER ── */
        .sh-loader {
          position: relative; padding: 60px 24px;
          display: flex; align-items: center; justify-content: center; flex-direction: column; gap: 16px;
        }
        .sh-spinner {
          width: 40px; height: 40px; border: 3px solid var(--brd2);
          border-top-color: var(--pri); border-radius: 50%;
          animation: sh-spin .7s linear infinite;
        }
        @keyframes sh-spin { to { transform: rotate(360deg); } }

        /* ── ALERT / MODULE MISSING ── */
        .sh-module-missing {
          background: var(--amb_x); border: 1px solid var(--amb);
          color: var(--amb); padding: 12px 18px;
          border-radius: 12px; font-size: 13px;
          display: flex; align-items: center; gap: 10px;
          margin-top: 12px;
        }
        .sh-error {
          background: var(--red_x); border: 1px solid var(--red);
          color: var(--red); padding: 16px 20px;
          border-radius: 12px; font-size: 13px;
          text-align: center;
        }

        /* ── GRID ── */
        .sh-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
        .sh-grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 18px; }

        /* ── LISTS ── */
        .sh-list { padding-left: 20px; margin: 6px 0; color: var(--tx2); font-size: 12px; line-height: 1.8; }
        .sh-list li { padding: 2px 0; }

        /* ── STATUS INDICATOR ── */
        .sh-status-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; margin-right: 6px; }
        .sh-status-dot.green { background: var(--grn); }
        .sh-status-dot.amber { background: var(--amb); }
        .sh-status-dot.red   { background: var(--red); }
        .sh-status-dot.grey  { background: var(--tx3); }

        /* ── PROGRESS ── */
        .sh-bar-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
        .sh-bar-lbl { font-size: 11px; color: var(--tx2); width: 140px; flex-shrink: 0; }
        .sh-bar     { flex: 1; height: 5px; background: var(--brd2); border-radius: 40px; overflow: hidden; }
        .sh-bar-fill { height: 100%; border-radius: 40px; transition: width .7s cubic-bezier(.4,0,.2,1); }
        .sh-bar-val { font-size: 11px; font-family: 'Space Mono', monospace; font-weight: 700; width: 44px; text-align: right; color: var(--tx1); }

        /* ── RESPONSIVE ── */
        @media(max-width:900px) { .sh-grid-2,.sh-grid-3 { grid-template-columns: 1fr; } }
        @media(max-width:600px) { .sh-topbar { flex-wrap: wrap; height: auto; padding: 10px 16px; gap: 8px; } .sh-logo { margin-right: 0; } }
        @media print { .sh-topbar { display: none !important; } }

        /* ── FADE IN ── */
        @keyframes fadeIn { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
        .sh-fade { animation: fadeIn .3s ease; }
            `;
            document.head.appendChild(s);
        }

        // ═══════════════════════════════════════════════════════════════════════════
        //  THEME ENGINE
        // ═══════════════════════════════════════════════════════════════════════════
        applyTheme(key) {
            const theme = SH_THEMES[key] || SH_THEMES['corporate'];
            this.activeTheme = key;

            try { localStorage.setItem('sh-studio-theme', key); }
            catch(e) { console.warn('localStorage unavailable'); }

            const root = document.getElementById('sh-root');
            if (!root) return;
            Object.entries(theme.colors).forEach(([k, v]) => {
                root.style.setProperty('--' + k, v);
            });

            if (theme.isDark) root.classList.add('dark-mode');
            else root.classList.remove('dark-mode');

            const label = document.getElementById('sh-theme-label');
            if (label) label.innerHTML = theme.icon + ' ' + theme.name;
        }

        openThemePicker() {
            const cur = this.activeTheme;
            const cardsHTML = Object.entries(SH_THEMES).map(([key, theme]) => {
                const isActive = key === cur;
                const dots = ['pri','acc','grn','sky','pink']
                    .map(k => `<div style="width:11px;height:11px;border-radius:3px;background:${theme.colors[k]}"></div>`)
                    .join('');
                return `
                <div onclick="window.__sh.applyTheme('${key}');if(window.__sh_td)window.__sh_td.hide();"
                     style="display:flex;align-items:center;gap:12px;padding:12px 16px;border-radius:12px;
                            border:2px solid ${isActive ? theme.colors.pri : theme.colors.brd2};
                            background:${theme.colors.card};cursor:pointer;transition:all .18s;color:${theme.colors.tx1}">
                    <div style="font-size:22px;width:36px;height:36px;border-radius:10px;
                                background:${theme.colors.pri_x};display:flex;align-items:center;justify-content:center;flex-shrink:0">
                        ${theme.icon}
                    </div>
                    <div style="flex:1;min-width:0">
                        <div style="font-size:13px;font-weight:700;margin-bottom:3px">${theme.name}</div>
                        <div style="display:flex;gap:4px;margin-bottom:3px">${dots}</div>
                        <div style="font-size:10px;color:${theme.colors.tx3}">${theme.isDark ? '🌙 Dark' : '☀️ Light'}</div>
                    </div>
                    ${isActive ? `<span style="font-size:18px;color:${theme.colors.pri};flex-shrink:0">✓</span>` : ''}
                </div>`;
            }).join('');

            const d = new frappe.ui.Dialog({
                title: '🎨 Secretarial Hub Theme',
                size: 'large',
                fields: [{
                    fieldtype: 'HTML', fieldname: 'themes',
                    options: `
                    <p style="font-size:12px;color:var(--tx3);margin:0 0 14px">
                        Themes are stored in your browser only — no database writes.
                    </p>
                    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px">
                        ${cardsHTML}
                    </div>`
                }]
            });
            window.__sh_td = d;
            d.show();
        }

        // ═══════════════════════════════════════════════════════════════════════════
        //  SHELL LAYOUT
        // ═══════════════════════════════════════════════════════════════════════════
        buildShell() {
            $(this.page.main).empty();
            this.$root = $(`
                <div id="sh-root">
                    <div class="sh-topbar">
                        <div class="sh-logo">
                            <div class="sh-logo-dot"></div>
                            Secretarial Hub
                        </div>
                        <nav class="sh-nav" id="sh-nav"></nav>
                        <div class="sh-topbar-right">
                            <button class="sh-theme-btn" onclick="window.__sh.openThemePicker()" title="Change Theme">
                                <i class="fa-solid fa-palette" style="font-size:11px"></i>
                                <span id="sh-theme-label">🏛️ Corporate</span>
                            </button>
                            <div class="sh-sync-dot" title="Auto-refreshing"></div>
                            <div class="sh-clock" id="sh-clock"></div>
                        </div>
                    </div>
                    <div class="sh-content-wrap" id="sh-content">
                        <div class="sh-loader" id="sh-loader">
                            <div class="sh-spinner"></div>
                            <div style="font-weight:600;font-size:14px;color:var(--tx1)">Loading Secretarial Hub</div>
                            <div style="font-size:12px;color:var(--tx3)">Fetching corporate governance data…</div>
                        </div>
                    </div>
                </div>
            `).appendTo(this.page.main);

            this.buildNav();
        }

        buildNav() {
            const tabs = [
                { id: 'secretary', icon: 'fa-solid fa-folder-open', label: 'Secretary', badge: 'tasks' },
                { id: 'board', icon: 'fa-solid fa-building-columns', label: 'Board', badge: 'board' },
                { id: 'executive', icon: 'fa-solid fa-suitcase', label: 'Executive', badge: 'exec' },
            ];
            const nav = tabs.map(v => `
                <button class="sh-nav-btn ${v.id === this.active_tab ? 'active' : ''}" data-tab="${v.id}">
                    <i class="${v.icon}"></i> ${v.label}
                    ${v.badge ? `<span class="sh-tab-badge" id="sh-badge-${v.badge}" style="display:none">0</span>` : ''}
                </button>
            `).join('');
            $('#sh-nav').html(nav);
        }

        bindEvents() {
            $(document).on('click', '.sh-nav-btn', (e) => {
                const tab = $(e.currentTarget).data('tab');
                this.switchTab(tab);
            });
        }

        switchTab(tab) {
            this.active_tab = tab;
            $('.sh-nav-btn').removeClass('active');
            $(`.sh-nav-btn[data-tab="${tab}"]`).addClass('active');
            this.load_tab(tab);
        }

        // ═══════════════════════════════════════════════════════════════════════════
        //  DATA LOADING
        // ═══════════════════════════════════════════════════════════════════════════
        load_tab(tab, force = false) {
            const $content = $('#sh-content');

            if (this.data[tab] && !force) {
                this.render(tab, this.data[tab]);
                return;
            }

            $content.html(`
                <div class="sh-loader">
                    <div class="sh-spinner"></div>
                    <div style="font-weight:600;font-size:14px;color:var(--tx1)">Loading ${tab.charAt(0).toUpperCase() + tab.slice(1)} data…</div>
                </div>
            `);

            const method_map = {
                secretary: 'ecclesia.api.hub_api.get_secretary_dashboard',
                board: 'ecclesia.api.hub_api.get_board_dashboard',
                executive: 'ecclesia.api.hub_api.get_executive_dashboard',
            };

            frappe.call({
                method: method_map[tab],
                args: { company: this.company },
                callback: (r) => {
                    if (!r.message) {
                        $content.html(`<div class="sh-error">${__('No data returned.')}</div>`);
                        return;
                    }
                    this.data[tab] = r.message;
                    this.render(tab, r.message);
                    this.updateBadges(tab, r.message);
                },
                error: (err) => {
                    $content.html(`
                        <div class="sh-error">
                            <div style="font-weight:700;margin-bottom:6px">⚠️ Failed to load</div>
                            <div style="font-size:12px;color:var(--tx3)">${err.message || 'Check browser console and server logs.'}</div>
                            <button class="sh-btn sh-btn-primary" style="margin-top:12px;padding:8px 16px;background:var(--pri);color:#fff;border:none;border-radius:8px;cursor:pointer" onclick="window.__sh.load_tab('${tab}',true)">Retry</button>
                        </div>
                    `);
                }
            });
        }

        updateBadges(tab, data) {
            if (tab === 'secretary') {
                const k = data.kpis || {};
                const count = (k.agm && k.agm.cac_overdue || 0) + (k.correspondence && k.correspondence.overdue_response || 0);
                $('#sh-badge-tasks').text(count).toggle(count > 0);
            }
            if (tab === 'board') {
                const k = data.kpis || {};
                const count = (k.resolutions_pending_implementation || 0) + (k.cac_filings_outstanding || 0);
                $('#sh-badge-board').text(count).toggle(count > 0);
            }
            if (tab === 'executive') {
                const k = data.kpis || {};
                const count = (k.overdue_tasks || 0) + (k.communications_awaiting_ack || 0);
                $('#sh-badge-exec').text(count).toggle(count > 0);
            }
        }

        // ═══════════════════════════════════════════════════════════════════════════
        //  RENDER DISPATCH
        // ═══════════════════════════════════════════════════════════════════════════
        render(tab, data) {
            const $content = $('#sh-content');
            let html = '';
            if (tab === 'secretary') html = this.renderSecretary(data);
            else if (tab === 'board') html = this.renderBoard(data);
            else if (tab === 'executive') html = this.renderExecutive(data);
            else html = `<div class="sh-error">Unknown tab: ${tab}</div>`;
            $content.html(`<div class="sh-fade">${html}</div>`);
        }

        // ═══════════════════════════════════════════════════════════════════════════
        //  RENDER: SECRETARY
        // ═══════════════════════════════════════════════════════════════════════════
        renderSecretary(data) {
            const k = data.kpis || {};
            const avail = data.modules_available || {};

            const cards = [];
            if (avail.agm) {
                cards.push(this.kpi('AGMs Upcoming (90d)', k.agm && k.agm.upcoming_90_days || 0, 'var(--sky)', 'fa-regular fa-calendar'));
                cards.push(this.kpi('CAC Overdue', k.agm && k.agm.cac_overdue || 0, 'var(--red)', 'fa-regular fa-clock'));
            }
            if (avail.meeting) {
                cards.push(this.kpi('Meetings This Year', k.meeting && k.meeting.held_this_year || 0, 'var(--pri)', 'fa-regular fa-circle-check'));
                cards.push(this.kpi('Open Action Items', k.meeting && k.meeting.open_action_items || 0, 'var(--amb)', 'fa-regular fa-list-check'));
            }
            if (avail.correspondence) {
                cards.push(this.kpi('Correspondence Overdue', k.correspondence && k.correspondence.overdue_response || 0, 'var(--red)', 'fa-regular fa-envelope'));
                cards.push(this.kpi('Urgent Open', k.correspondence && k.correspondence.urgent_open || 0, 'var(--amb)', 'fa-regular fa-bell'));
            }
            if (avail.documents) {
                cards.push(this.kpi('Licenses Expiring Soon', k.documents && k.documents.legal_expiring_soon || 0, 'var(--amb)', 'fa-regular fa-file-lines'));
                cards.push(this.kpi('Licenses Expired', k.documents && k.documents.legal_expired || 0, 'var(--red)', 'fa-regular fa-file-circle-exclamation'));
            }

            const upcoming = data.upcoming || [];
            let upcomingHtml;
            if (!upcoming.length) {
                upcomingHtml = this.empty('fa-regular fa-circle-check', 'Nothing due — clean sheet.');
            } else {
                const rows = upcoming.map((u) => `
                    <tr>
                        <td><span class="sh-badge bd-grey">${this.esc(u.source || '')}</span></td>
                        <td style="font-weight:600;color:var(--tx1)">${this.esc(u.title || '')}</td>
                        <td>${u.due_date ? frappe.datetime.str_to_user(u.due_date) : (u.date ? frappe.datetime.str_to_user(u.date) : '—')}</td>
                        <td><span style="color:${this.alertColour(u.alert_level)};font-weight:700">${u.days_to || '—'}</span></td>
                    </tr>`).join('');
                upcomingHtml = `
                    <div class="sh-tbl-wrap">
                        <table class="sh-tbl">
                            <thead><tr><th>${__('Source')}</th><th>${__('Title')}</th><th>${__('Due')}</th><th>${__('Days')}</th></tr></thead>
                            <tbody>${rows}</tbody>
                        </table>
                    </div>`;
            }

            const missingHtml = this.missingModulesHtml(avail);

            return `
                ${cards.length ? `<div class="sh-kpis">${cards.join('')}</div>` : ''}
                <div class="sh-card">
                    <div class="sh-card-head">
                        <div class="sh-card-title">
                            <div class="sh-title-icon" style="background:var(--sky_x);color:var(--sky)"><i class="fa-regular fa-calendar-circle-plus"></i></div>
                            📅 Upcoming & Overdue (Next 60 Days)
                        </div>
                        <span style="font-size:11px;color:var(--tx3)">${upcoming.length} items</span>
                    </div>
                    <div class="sh-card-body">${upcomingHtml}</div>
                </div>
                ${missingHtml}
            `;
        }

        // ═══════════════════════════════════════════════════════════════════════════
        //  RENDER: BOARD
        // ═══════════════════════════════════════════════════════════════════════════
        renderBoard(data) {
            const k = data.kpis || {};
            const avail = data.modules_available || {};

            const cards = [
                this.kpi('Board Resolutions', k.resolutions_total || 0, 'var(--pri)', 'fa-regular fa-file-lines'),
                this.kpi('Pending Implementation', k.resolutions_pending_implementation || 0, 'var(--amb)', 'fa-regular fa-hourglass-half'),
                this.kpi('CAC Filings Outstanding', k.cac_filings_outstanding || 0, 'var(--red)', 'fa-regular fa-file-circle-exclamation'),
                this.kpi('Active Board Members', k.active_board_members || 0, 'var(--grn)', 'fa-regular fa-users'),
                this.kpi('Independent Directors', k.independent_directors || 0, 'var(--grn)', 'fa-regular fa-user-tie'),
                this.kpi('Active Committees', k.active_committees || 0, 'var(--sky)', 'fa-regular fa-people-group'),
            ];

            const meetings = data.upcoming_board_meetings || [];
            let meetingsHtml;
            if (!meetings.length) {
                meetingsHtml = this.empty('fa-regular fa-calendar', 'No meetings scheduled.');
            } else {
                const rows = meetings.map((m) => `
                    <tr>
                        <td style="font-weight:600;color:var(--tx1)">${this.esc(m.meeting_title || '')}</td>
                        <td>${m.meeting_date ? frappe.datetime.str_to_user(m.meeting_date) : '—'}</td>
                        <td><span class="sh-badge ${m.status === 'Scheduled' ? 'bd-sky' : m.status === 'Held' ? 'bd-grn' : 'bd-amb'}">${this.esc(m.status || '')}</span></td>
                    </tr>`).join('');
                meetingsHtml = `
                    <div class="sh-tbl-wrap">
                        <table class="sh-tbl">
                            <thead><tr><th>${__('Meeting')}</th><th>${__('Date')}</th><th>${__('Status')}</th></tr></thead>
                            <tbody>${rows}</tbody>
                        </table>
                    </div>`;
            }

            const sigs = data.pending_signatures || [];
            let signaturesHtml = '';
            if (sigs.length) {
                const rows = sigs.map((s) => `
                    <tr>
                        <td style="font-weight:600;color:var(--tx1)">${this.esc(s.resolution_title || '')}</td>
                        <td>${s.signing_deadline ? frappe.datetime.str_to_user(s.signing_deadline) : '—'}</td>
                        <td><span class="sh-status-dot red"></span> Awaiting</td>
                    </tr>`).join('');
                signaturesHtml = `
                    <div class="sh-card">
                        <div class="sh-card-head">
                            <div class="sh-card-title">
                                <div class="sh-title-icon" style="background:var(--acc_x);color:var(--acc)"><i class="fa-regular fa-pen-to-square"></i></div>
                                ✍️ Written Resolutions Awaiting Signature (${sigs.length})
                            </div>
                        </div>
                        <div class="sh-card-body">
                            <div class="sh-tbl-wrap">
                                <table class="sh-tbl">
                                    <thead><tr><th>${__('Resolution')}</th><th>${__('Signing Deadline')}</th><th>${__('Status')}</th></tr></thead>
                                    <tbody>${rows}</tbody>
                                </table>
                            </div>
                        </div>
                    </div>`;
            }

            const missingHtml = this.missingModulesHtml(avail);

            return `
                <div class="sh-kpis">${cards.join('')}</div>
                <div class="sh-card">
                    <div class="sh-card-head">
                        <div class="sh-card-title">
                            <div class="sh-title-icon" style="background:var(--grn_x);color:var(--grn)"><i class="fa-regular fa-calendar-plus"></i></div>
                            📅 Upcoming Board Meetings
                        </div>
                        <span style="font-size:11px;color:var(--tx3)">${meetings.length} meetings</span>
                    </div>
                    <div class="sh-card-body">${meetingsHtml}</div>
                </div>
                ${signaturesHtml}
                ${missingHtml}
            `;
        }

        // ═══════════════════════════════════════════════════════════════════════════
        //  RENDER: EXECUTIVE
        // ═══════════════════════════════════════════════════════════════════════════
        renderExecutive(data) {
            const avail = data.modules_available || {};
            if (!avail.executive_support) {
                return `
                    <div class="sh-module-missing">
                        <i class="fa-regular fa-triangle-exclamation" style="font-size:18px"></i>
                        ⚠️ Executive Support module not yet deployed on this bench.
                    </div>`;
            }

            const k = data.kpis || {};
            const cards = [
                this.kpi('Appointments Today', k.appointments_today || 0, 'var(--sky)', 'fa-regular fa-calendar-day'),
                this.kpi('This Week', k.appointments_this_week || 0, 'var(--pri)', 'fa-regular fa-calendar-week'),
                this.kpi('Open Tasks', k.open_tasks || 0, 'var(--amb)', 'fa-regular fa-list-check'),
                this.kpi('Overdue Tasks', k.overdue_tasks || 0, 'var(--red)', 'fa-regular fa-clock'),
                this.kpi('Awaiting Acknowledgement', k.communications_awaiting_ack || 0, 'var(--amb)', 'fa-regular fa-envelope-open'),
            ];

            const appts = data.todays_appointments || [];
            let apptHtml;
            if (!appts.length) {
                apptHtml = this.empty('fa-regular fa-calendar-check', 'Nothing scheduled today.');
            } else {
                const rows = appts.map((a) => `
                    <tr>
                        <td style="font-family:'Space Mono',monospace;font-size:11px;color:var(--tx3)">${this.esc(a.start_time || '')}</td>
                        <td style="font-weight:600;color:var(--tx1)">${this.esc(a.appointment_title || '')}</td>
                        <td><span class="sh-badge bd-sky">${this.esc(a.appointment_type || '')}</span></td>
                        <td>${this.esc(a.meeting_with || '—')}</td>
                    </tr>`).join('');
                apptHtml = `
                    <div class="sh-tbl-wrap">
                        <table class="sh-tbl">
                            <thead><tr><th>${__('Time')}</th><th>${__('Title')}</th><th>${__('Type')}</th><th>${__('With')}</th></tr></thead>
                            <tbody>${rows}</tbody>
                        </table>
                    </div>`;
            }

            const birthdays = data.birthdays || [];
            const anniversaries = data.anniversaries || [];
            let bdayHtml = '';
            if (birthdays.length || anniversaries.length) {
                const bdayList = birthdays.map((b) =>
                    `<li><span style="font-weight:600">${this.esc(b.employee_name)}</span> — ${b.next_birthday ? frappe.datetime.str_to_user(b.next_birthday) : '—'}</li>`
                ).join('');
                const annivList = anniversaries.map((a) =>
                    `<li><span style="font-weight:600">${this.esc(a.employee_name)}</span> — ${a.years || 0} ${__('yr(s)')} (${a.next_anniversary ? frappe.datetime.str_to_user(a.next_anniversary) : '—'})</li>`
                ).join('');
                bdayHtml = `
                    <div class="sh-card">
                        <div class="sh-card-head">
                            <div class="sh-card-title">
                                <div class="sh-title-icon" style="background:var(--pink_x);color:var(--pink)"><i class="fa-regular fa-cake-candles"></i></div>
                                🎂 Upcoming Birthdays & Anniversaries
                            </div>
                        </div>
                        <div class="sh-grid-2" style="padding:18px 20px">
                            <div>
                                <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--tx3);margin-bottom:8px">🎂 ${__('Birthdays')}</div>
                                <ul class="sh-list">${bdayList || '<li>—</li>'}</ul>
                            </div>
                            <div>
                                <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--tx3);margin-bottom:8px">🏅 ${__('Work Anniversaries')}</div>
                                <ul class="sh-list">${annivList || '<li>—</li>'}</ul>
                            </div>
                        </div>
                    </div>`;
            }

            return `
                <div class="sh-kpis">${cards.join('')}</div>
                <div class="sh-card">
                    <div class="sh-card-head">
                        <div class="sh-card-title">
                            <div class="sh-title-icon" style="background:var(--sky_x);color:var(--sky)"><i class="fa-regular fa-calendar-day"></i></div>
                            📅 Today's Appointments
                        </div>
                        <span style="font-size:11px;color:var(--tx3)">${appts.length} appointments</span>
                    </div>
                    <div class="sh-card-body">${apptHtml}</div>
                </div>
                ${bdayHtml}
            `;
        }

        // ═══════════════════════════════════════════════════════════════════════════
        //  HELPERS
        // ═══════════════════════════════════════════════════════════════════════════
        kpi(label, value, colour, icon) {
            return `
                <div class="sh-kpi" style="--kc:${colour || 'var(--pri)'}">
                    ${icon ? `<div class="sh-kpi-icon"><i class="${icon}"></i></div>` : ''}
                    <div class="sh-kpi-val">${value != null ? value.toLocaleString() : 0}</div>
                    <div class="sh-kpi-lbl">${this.esc(label)}</div>
                </div>`;
        }

        empty(icon, msg) {
            return `
                <div class="sh-empty">
                    <div class="sh-empty-icon"><i class="${icon || 'fa-regular fa-circle-check'}"></i></div>
                    <h4>${this.esc(msg)}</h4>
                </div>`;
        }

        alertColour(level) {
            const map = { red: 'var(--red)', amber: 'var(--amb)', green: 'var(--grn)' };
            return map[level] || 'var(--tx3)';
        }

        missingModulesHtml(avail) {
            const missing = Object.entries(avail || {})
                .filter(([mod, available]) => !available)
                .map(([mod]) => mod);
            if (!missing.length) return '';
            return missing.map((mod) => `
                <div class="sh-module-missing">
                    <i class="fa-regular fa-triangle-exclamation"></i>
                    ${this.esc(mod)} module not yet deployed on this bench.
                </div>
            `).join('');
        }

        esc(str) {
            if (!str) return '';
            return String(str)
                .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
        }

        startClock() {
            const tick = () => {
                $('#sh-clock').text(new Date().toLocaleTimeString('en-NG', { hour12: true }));
            };
            tick();
            setInterval(tick, 1000);
        }

        startAutoRefresh() {
            this.timers.refresh = setInterval(() => {
                this.load_tab(this.active_tab, true);
            }, 45000);
        }

        // ── Company field sync ──
        setCompany(company) {
            this.company = company;
            this.load_tab(this.active_tab, true);
        }
    }

    // Instantiate the class
    new SecretarialHub(wrapper);
}

// ─── GLOBAL CSS ANIMATION ────────────────────────────────────────────────────
const fadeStyle = document.createElement('style');
fadeStyle.textContent = `
@keyframes fadeIn { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }
`;
document.head.appendChild(fadeStyle);