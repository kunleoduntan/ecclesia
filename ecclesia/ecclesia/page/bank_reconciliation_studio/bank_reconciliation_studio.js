// Copyright (c) 2026, Value Impacts Consulting
// ecclesia/ecclesia/page/bank_reconciliation_studio/bank_reconciliation_studio.js
//
// ╔══════════════════════════════════════════════════════════════════════════════╗
// ║   BANK RECONCILIATION STUDIO — Ecclesia · Value Impacts Consulting          ║
// ║   9 Themes · 6 Views · AI Fuzzy Matching · 5,000-line Excel Import          ║
// ║   Transfer-aware: name + date + amount multi-algo matching engine            ║
// ╚══════════════════════════════════════════════════════════════════════════════╝

frappe.pages['bank-reconciliation-studio'] = frappe.pages['bank-reconciliation-studio'] || {};
frappe.pages['bank-reconciliation-studio'].on_page_load = function (wrapper) {
    const boot = () => {
        if (typeof XLSX === 'undefined') {
            const xs = document.createElement('script');
            xs.src = 'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js';
            xs.onload = () => new BRStudio(wrapper);
            xs.onerror = () => frappe.msgprint({ title: 'SheetJS Error', indicator: 'red', message: 'Failed to load Excel library. Check internet connection.' });
            document.head.appendChild(xs);
        } else { new BRStudio(wrapper); }
    };
    if (!document.getElementById('fa-brs')) {
        const fa = document.createElement('link');
        fa.id = 'fa-brs'; fa.rel = 'stylesheet';
        fa.href = 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css';
        fa.onload = boot; fa.onerror = boot;
        document.head.appendChild(fa);
    } else { boot(); }
};

// ═══════════════════════════════════════════════════════════════════════════════
//  THEME REGISTRY — 9 Themes, pure localStorage
// ═══════════════════════════════════════════════════════════════════════════════
const BRS_THEMES = {
    midnight: {
        name: 'Midnight', icon: '🌙', isDark: true,
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
            banner: 'linear-gradient(135deg,#020617 0%,#0F172A 50%,#1E3A5F 70%,#312E81 100%)'
        }
    },
    nova: {
        name: 'Nova', icon: '🌟', isDark: false,
        colors: {
            bg: '#FAF5FF', bg2: '#F5F3FF', bg3: '#EDE9FE', card: '#FFFFFF',
            brd: '#E9D5FF', brd2: '#D8B4FE', tx1: '#2E1065', tx2: '#5B21B6', tx3: '#A78BFA',
            pri: '#7C3AED', pri_d: '#6D28D9', pri2: '#A78BFA', pri_x: 'rgba(124,58,237,.09)',
            acc: '#A78BFA', acc_x: 'rgba(167,139,250,.12)',
            grn: '#10B981', grn_x: 'rgba(16,185,129,.09)',
            red: '#EF4444', red_x: 'rgba(239,68,68,.09)',
            amb: '#F59E0B', amb_x: 'rgba(245,158,11,.09)',
            sky: '#06B6D4', sky_x: 'rgba(6,182,212,.09)',
            banner: 'linear-gradient(135deg,#1E1B4B 0%,#4C1D95 40%,#7C3AED 70%,#EC4899 100%)'
        }
    },
    ocean: {
        name: 'Ocean', icon: '🌊', isDark: false,
        colors: {
            bg: '#F0F9FF', bg2: '#E0F2FE', bg3: '#BAE6FD', card: '#FFFFFF',
            brd: '#BAE6FD', brd2: '#7DD3FC', tx1: '#0C4A6E', tx2: '#075985', tx3: '#7DD3FC',
            pri: '#0EA5E9', pri_d: '#0284C7', pri2: '#38BDF8', pri_x: 'rgba(14,165,233,.09)',
            acc: '#38BDF8', acc_x: 'rgba(56,189,248,.12)',
            grn: '#10B981', grn_x: 'rgba(16,185,129,.09)',
            red: '#F43F5E', red_x: 'rgba(244,63,94,.09)',
            amb: '#F59E0B', amb_x: 'rgba(245,158,11,.09)',
            sky: '#06B6D4', sky_x: 'rgba(6,182,212,.09)',
            banner: 'linear-gradient(135deg,#0C4A6E 0%,#0369A1 40%,#0EA5E9 70%,#06B6D4 100%)'
        }
    },
    ember: {
        name: 'Ember', icon: '🔥', isDark: false,
        colors: {
            bg: '#FFF7ED', bg2: '#FFEDD5', bg3: '#FED7AA', card: '#FFFFFF',
            brd: '#FED7AA', brd2: '#FDBA74', tx1: '#431407', tx2: '#9A3412', tx3: '#FDBA74',
            pri: '#F97316', pri_d: '#EA580C', pri2: '#FB923C', pri_x: 'rgba(249,115,22,.09)',
            acc: '#FB923C', acc_x: 'rgba(251,146,60,.12)',
            grn: '#22C55E', grn_x: 'rgba(34,197,94,.09)',
            red: '#EF4444', red_x: 'rgba(239,68,68,.09)',
            amb: '#EAB308', amb_x: 'rgba(234,179,8,.09)',
            sky: '#0EA5E9', sky_x: 'rgba(14,165,233,.09)',
            banner: 'linear-gradient(135deg,#431407 0%,#C2410C 40%,#F97316 70%,#EAB308 100%)'
        }
    },
    verdant: {
        name: 'Verdant', icon: '🌿', isDark: false,
        colors: {
            bg: '#ECFDF5', bg2: '#D1FAE5', bg3: '#A7F3D0', card: '#FFFFFF',
            brd: '#A7F3D0', brd2: '#6EE7B7', tx1: '#022C22', tx2: '#065F46', tx3: '#6EE7B7',
            pri: '#059669', pri_d: '#047857', pri2: '#34D399', pri_x: 'rgba(5,150,105,.09)',
            acc: '#34D399', acc_x: 'rgba(52,211,153,.12)',
            grn: '#10B981', grn_x: 'rgba(16,185,129,.09)',
            red: '#EF4444', red_x: 'rgba(239,68,68,.09)',
            amb: '#F59E0B', amb_x: 'rgba(245,158,11,.09)',
            sky: '#0EA5E9', sky_x: 'rgba(14,165,233,.09)',
            banner: 'linear-gradient(135deg,#022C22 0%,#047857 40%,#059669 70%,#10B981 100%)'
        }
    },
    arctic: {
        name: 'Arctic', icon: '❄️', isDark: false,
        colors: {
            bg: '#F8FAFC', bg2: '#F1F5F9', bg3: '#E2E8F0', card: '#FFFFFF',
            brd: '#E2E8F0', brd2: '#CBD5E1', tx1: '#0F172A', tx2: '#334155', tx3: '#94A3B8',
            pri: '#0284C7', pri_d: '#0369A1', pri2: '#7DD3FC', pri_x: 'rgba(2,132,199,.09)',
            acc: '#7DD3FC', acc_x: 'rgba(125,211,252,.12)',
            grn: '#10B981', grn_x: 'rgba(16,185,129,.09)',
            red: '#EF4444', red_x: 'rgba(239,68,68,.09)',
            amb: '#F59E0B', amb_x: 'rgba(245,158,11,.09)',
            sky: '#06B6D4', sky_x: 'rgba(6,182,212,.09)',
            banner: 'linear-gradient(135deg,#0F172A 0%,#1E3A5F 40%,#0284C7 70%,#06B6D4 100%)'
        }
    },
    forest: {
        name: 'Forest', icon: '🌲', isDark: true,
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
            banner: 'linear-gradient(135deg,#052E16 0%,#14532D 40%,#166534 70%,#22C55E 100%)'
        }
    },
    sunset: {
        name: 'Sunset', icon: '🌅', isDark: false,
        colors: {
            bg: '#FFF1F2', bg2: '#FFE4E6', bg3: '#FECDD3', card: '#FFFFFF',
            brd: '#FECDD3', brd2: '#FDA4AF', tx1: '#4C0519', tx2: '#881337', tx3: '#FDA4AF',
            pri: '#DC2626', pri_d: '#B91C1C', pri2: '#F87171', pri_x: 'rgba(220,38,38,.09)',
            acc: '#F87171', acc_x: 'rgba(248,113,113,.12)',
            grn: '#10B981', grn_x: 'rgba(16,185,129,.09)',
            red: '#EF4444', red_x: 'rgba(239,68,68,.09)',
            amb: '#F59E0B', amb_x: 'rgba(245,158,11,.09)',
            sky: '#06B6D4', sky_x: 'rgba(6,182,212,.09)',
            banner: 'linear-gradient(135deg,#4C0519 0%,#881337 40%,#DC2626 70%,#F59E0B 100%)'
        }
    },
    candy: {
        name: 'Candy', icon: '🍬', isDark: false,
        colors: {
            bg: '#FDF2F8', bg2: '#FCE7F3', bg3: '#FBCFE8', card: '#FFFFFF',
            brd: '#FBCFE8', brd2: '#F9A8D4', tx1: '#500724', tx2: '#831843', tx3: '#F9A8D4',
            pri: '#DB2777', pri_d: '#BE185D', pri2: '#F472B6', pri_x: 'rgba(219,39,119,.09)',
            acc: '#F472B6', acc_x: 'rgba(244,114,182,.12)',
            grn: '#10B981', grn_x: 'rgba(16,185,129,.09)',
            red: '#EF4444', red_x: 'rgba(239,68,68,.09)',
            amb: '#F59E0B', amb_x: 'rgba(245,158,11,.09)',
            sky: '#06B6D4', sky_x: 'rgba(6,182,212,.09)',
            banner: 'linear-gradient(135deg,#500724 0%,#831843 40%,#DB2777 70%,#EC4899 100%)'
        }
    }
};

// ═══════════════════════════════════════════════════════════════════════════════
//  NIGERIAN BANK ABBREVIATION DICTIONARY
// ═══════════════════════════════════════════════════════════════════════════════
const BRS_ABBREV = {
    'GTB': 'GUARANTY TRUST BANK', 'GT BANK': 'GUARANTY TRUST BANK', 'GUARANTY': 'GUARANTY TRUST BANK',
    'FBN': 'FIRST BANK NIGERIA', '1ST BANK': 'FIRST BANK NIGERIA', 'FIRSTBANK': 'FIRST BANK NIGERIA',
    'UBA': 'UNITED BANK AFRICA', 'ACCESS': 'ACCESS BANK', 'ZENITH': 'ZENITH BANK',
    'STERLING': 'STERLING BANK', 'FIDELITY': 'FIDELITY BANK', 'UNION': 'UNION BANK',
    'WEMA': 'WEMA BANK', 'FCMB': 'FIRST CITY MONUMENT BANK', 'POLARIS': 'POLARIS BANK',
    'KEYSTONE': 'KEYSTONE BANK', 'HERITAGE': 'HERITAGE BANK', 'JAIZ': 'JAIZ BANK',
    'FLUTTERWAVE': 'FLUTTERWAVE COLLECTIONS', 'PAYSTACK': 'PAYSTACK PAYMENTS',
    'INTERSWITCH': 'INTERSWITCH PAYMENT', 'NIP': 'NIP TRANSFER', 'TRF': 'TRANSFER',
    'INWARD TRF': 'INWARD TRANSFER', 'OUTWARD TRF': 'OUTWARD TRANSFER',
    'CHG': 'CHARGE', 'COMM': 'COMMISSION', 'VAT': 'VALUE ADDED TAX',
    'WHT': 'WITHHOLDING TAX', 'PENCOM': 'PENSION COMMISSION', 'FIRS': 'FEDERAL INLAND REVENUE',
    'AFRIC': 'AFRICA', 'NIG': 'NIGERIA', 'COMMS': 'COMMUNICATIONS',
    'PLC': '', 'LTD': '', 'LIMITED': '', 'CO': '', 'AND': '', 'THE': '', 'OF': '',
    'COMPANY': '', 'NIGERIA': '', 'NIGERIAN': '', 'ASSOCIATES': '', 'ENTERPRISE': ''
};

const BRS_STOPWORDS = new Set([
    'LTD','PLC','LIMITED','NIG','NIGERIA','NIGERIAN','AND','THE','OF','CO','COMPANY',
    'COMM','COMMS','COMMUNICATIONS','PETROLEUM','DEVELOPMENT','ASSOCIATES','ENTERPRISE',
    'GROUP','INTERNATIONAL','GLOBAL','SERVICES','SOLUTIONS','RESOURCES','HOLDINGS'
]);

// ─── MAIN CLASS ───────────────────────────────────────────────────────────────
class BRStudio {
    constructor(wrapper) {
        this.wrapper    = wrapper;
        this.page       = frappe.ui.make_app_page({
            parent: wrapper,
            title: 'Bank Reconciliation Studio',
            single_column: true
        });
        this.activeTheme = (() => {
            try { return localStorage.getItem('brs-theme') || 'midnight'; }
            catch(e) { return 'midnight'; }
        })();
        this.state = {
            activeView:     'dashboard',
            brsDoc:         null,          // current Bank Reconciliation Statement doc
            allDocs:        [],            // list of existing BRS docs
            bankRows:       [],            // parsed bank statement rows
            cashRows:       [],            // parsed cashbook rows
            matches:        [],            // computed match pairs
            accepted:       new Set(),
            rejected:       new Set(),
            filters:        { conf: 'all', search: '' },
            config: {
                dateTol:       3,
                nameTol:       70,
                amtTol:        0,
                hiConf:        85,
                amtFormat:     'drcr',     // bank statement: 'single','single_inv','drcr','drcr_flag'
                cashAmtFormat: 'drcr',     // cashbook/GL:    'single','single_inv','drcr','drcr_flag'
            },
            progress:       0,
            company:        '',
            bankAccount:    '',
            fromDate:       '',
            toDate:         ''
        };
        window.__brs = this;
        this.boot();
    }

    async boot() {
        try {
            this.injectCSS();
            this.buildShell();
            this.applyTheme(this.activeTheme);
            this.bindTopBar();
            this.startClock();
            await this.fetchDocs();
            this.renderView('dashboard');
        } catch(e) {
            console.error('BRS boot error:', e);
            const c = document.getElementById('brs-content');
            if (c) c.innerHTML = `
            <div style="padding:48px;text-align:center">
                <div style="font-size:36px;margin-bottom:12px">⚠️</div>
                <div style="font-size:16px;font-weight:700;color:var(--red);margin-bottom:8px">Bank Reconciliation Studio failed to load</div>
                <div style="font-size:12px;color:var(--tx3);font-family:monospace;background:var(--bg2);padding:12px;border-radius:8px;max-width:600px;margin:0 auto 16px;text-align:left">
                    ${esc(e && e.message ? e.message : String(e))}
                </div>
                <button class="brs-btn btn-primary btn-sm" onclick="location.reload()">Reload</button>
            </div>`;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  CSS
    // ═══════════════════════════════════════════════════════════════════════════
    injectCSS() {
        if (document.getElementById('brs-css')) return;
        const s = document.createElement('style');
        s.id = 'brs-css';
        s.textContent = `
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700;800&display=swap');

#brs-root {
  --bg:#0F172A; --bg2:#1E293B; --bg3:#334155; --card:#1E293B;
  --brd:rgba(255,255,255,.08); --brd2:rgba(255,255,255,.14);
  --tx1:#F1F5F9; --tx2:#94A3B8; --tx3:#475569;
  --pri:#818CF8; --pri_d:#6366F1; --pri2:#A5B4FC; --pri_x:rgba(129,140,248,.12);
  --acc:#A5B4FC; --acc_x:rgba(165,180,252,.12);
  --grn:#34D399; --grn_x:rgba(52,211,153,.12);
  --red:#F87171; --red_x:rgba(248,113,113,.12);
  --amb:#FCD34D; --amb_x:rgba(252,211,77,.12);
  --sky:#38BDF8; --sky_x:rgba(56,189,248,.12);
  font-family:'DM Sans',system-ui,sans-serif;
  background:var(--bg); color:var(--tx1); min-height:100vh;
}
/* ── TOPBAR ── */
.brs-topbar {
  display:flex; align-items:center; gap:12px; padding:0 20px;
  height:52px; background:var(--bg2); border-bottom:1px solid var(--brd);
  position:sticky; top:0; z-index:100; flex-shrink:0;
}
.brs-logo {
  display:flex; align-items:center; gap:8px;
  font-size:14px; font-weight:800; color:var(--pri2); white-space:nowrap;
}
.brs-logo-dot {
  width:8px; height:8px; border-radius:50%; background:var(--grn);
  box-shadow:0 0 6px var(--grn); animation:brs-pulse 2s infinite;
}
@keyframes brs-pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.6;transform:scale(1.25)} }
.brs-nav { display:flex; gap:2px; flex:1; overflow-x:auto; }
.brs-nav-btn {
  display:flex; align-items:center; gap:7px; padding:7px 13px;
  border:none; background:transparent; color:var(--tx2); cursor:pointer;
  border-radius:8px; font-size:12px; font-weight:600; white-space:nowrap;
  transition:all .15s; font-family:inherit;
}
.brs-nav-btn:hover { background:var(--bg3); color:var(--tx1); }
.brs-nav-btn.active { background:var(--pri_x); color:var(--pri2); }
.brs-nav-badge {
  background:var(--red); color:#fff; border-radius:10px;
  padding:1px 6px; font-size:9px; font-weight:800;
}
.brs-topbar-right { display:flex; align-items:center; gap:8px; margin-left:auto; }
.brs-theme-btn {
  display:flex; align-items:center; gap:6px; padding:6px 11px;
  border:1px solid var(--brd2); border-radius:8px; background:var(--bg3);
  color:var(--tx2); cursor:pointer; font-size:11px; font-weight:600;
  font-family:inherit; transition:all .15s; white-space:nowrap;
}
.brs-theme-btn:hover { color:var(--tx1); }
.brs-clock { font-size:11px; color:var(--tx3); font-family:monospace; }
/* ── CONTENT ── */
.brs-content { padding:20px; max-width:1400px; margin:0 auto; }
/* ── CARDS ── */
.brs-card {
  background:var(--card); border:1px solid var(--brd);
  border-radius:14px; padding:18px 20px;
}
.brs-card-sm { padding:12px 14px; border-radius:10px; }
/* ── BANNER ── */
.brs-banner {
  background:var(--banner,var(--bg2));
  border-radius:16px; padding:22px 24px; margin-bottom:18px;
  display:flex; align-items:center; justify-content:space-between; gap:16px;
}
.brs-banner-title { font-size:20px; font-weight:800; color:#fff; margin-bottom:3px; }
.brs-banner-sub   { font-size:12px; color:rgba(255,255,255,.7); }
/* ── STAT GRID ── */
.brs-stat-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); gap:10px; margin-bottom:18px; }
.brs-stat {
  background:var(--bg2); border:1px solid var(--brd); border-radius:12px;
  padding:14px; text-align:center;
}
.brs-stat-val { font-size:22px; font-weight:800; color:var(--tx1); }
.brs-stat-lbl { font-size:10px; text-transform:uppercase; letter-spacing:.5px; color:var(--tx3); margin-top:2px; }
/* ── GRIDS ── */
.brs-g2  { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
.brs-g3  { display:grid; grid-template-columns:1fr 1fr 1fr; gap:14px; }
.brs-g21 { display:grid; grid-template-columns:1fr 360px; gap:14px; }
/* ── BUTTONS ── */
.brs-btn {
  display:inline-flex; align-items:center; gap:7px; padding:8px 16px;
  border-radius:9px; font-size:12px; font-weight:700; cursor:pointer;
  border:1px solid var(--brd2); background:var(--bg3); color:var(--tx1);
  transition:all .15s; font-family:inherit;
}
.brs-btn:hover { border-color:var(--pri); color:var(--pri2); }
.btn-primary { background:var(--pri_d); border-color:var(--pri); color:#fff; }
.btn-primary:hover { background:var(--pri); color:#fff; }
.btn-green  { background:var(--grn_x); border-color:var(--grn); color:var(--grn); }
.btn-green:hover { background:var(--grn); color:#fff; }
.btn-red    { background:var(--red_x); border-color:var(--red); color:var(--red); }
.btn-red:hover { background:var(--red); color:#fff; }
.btn-amber  { background:var(--amb_x); border-color:var(--amb); color:var(--amb); }
.btn-sm { padding:5px 11px; font-size:11px; border-radius:7px; }
.btn-xs { padding:3px 8px; font-size:10px; border-radius:6px; }
.brs-btn-row { display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
/* ── TABLE ── */
.brs-tbl-wrap { overflow-x:auto; border:1px solid var(--brd); border-radius:12px; }
.brs-tbl { width:100%; border-collapse:collapse; font-size:12px; }
.brs-tbl th {
  padding:9px 11px; text-align:left; font-size:10px; font-weight:700;
  text-transform:uppercase; letter-spacing:.5px; color:var(--tx3);
  background:var(--bg2); border-bottom:1px solid var(--brd); white-space:nowrap;
}
.brs-tbl td { padding:8px 11px; border-bottom:1px solid var(--brd); vertical-align:middle; }
.brs-tbl tr:last-child td { border-bottom:none; }
.brs-tbl tr:hover td { background:var(--bg3); }
.brs-tbl tr.row-matched td { background:rgba(52,211,153,.05); }
.brs-tbl tr.row-unmatched td { background:rgba(248,113,113,.04); }
/* ── BADGES ── */
.brs-badge {
  display:inline-flex; align-items:center; gap:4px;
  padding:2px 8px; border-radius:20px; font-size:10px; font-weight:700;
}
.bd-green  { background:var(--grn_x); color:var(--grn); border:1px solid rgba(52,211,153,.2); }
.bd-red    { background:var(--red_x); color:var(--red); border:1px solid rgba(248,113,113,.2); }
.bd-amber  { background:var(--amb_x); color:var(--amb); border:1px solid rgba(252,211,77,.2); }
.bd-sky    { background:var(--sky_x); color:var(--sky); border:1px solid rgba(56,189,248,.2); }
.bd-pri    { background:var(--pri_x); color:var(--pri2); border:1px solid rgba(129,140,248,.2); }
.bd-grey   { background:var(--bg3); color:var(--tx2); border:1px solid var(--brd2); }
/* ── MATCH CARDS ── */
.brs-match-card {
  display:grid; grid-template-columns:1fr 80px 1fr 120px;
  gap:12px; align-items:center;
  background:var(--card); border:1px solid var(--brd); border-radius:12px;
  padding:13px 16px; margin-bottom:8px; transition:border-color .15s;
}
.brs-match-card.conf-high   { border-left:3px solid var(--grn); }
.brs-match-card.conf-medium { border-left:3px solid var(--amb); }
.brs-match-card.conf-low    { border-left:3px solid var(--red); }
.brs-match-card.accepted    { opacity:.55; }
.brs-txn-box .mn { font-size:12px; font-weight:700; color:var(--tx1); margin-bottom:2px; line-height:1.3; }
.brs-txn-box .md { font-size:10px; color:var(--tx3); }
.brs-txn-box .ma { font-size:13px; font-weight:800; margin-top:4px; }
.brs-arrow-box { text-align:center; }
.brs-conf-score { font-size:18px; font-weight:800; }
.brs-conf-lbl   { font-size:9px; color:var(--tx3); text-transform:uppercase; letter-spacing:.4px; }
.brs-action-box { display:flex; flex-direction:column; gap:5px; }
/* ── UPLOAD ZONE ── */
.brs-upload {
  border:2px dashed var(--brd2); border-radius:12px;
  padding:28px 20px; text-align:center; cursor:pointer; transition:all .2s;
  background:var(--bg2);
}
.brs-upload:hover { border-color:var(--pri); background:var(--pri_x); }
.brs-upload.loaded { border-style:solid; border-color:var(--grn); background:var(--grn_x); }
.brs-upload i { font-size:26px; color:var(--tx3); display:block; margin-bottom:8px; }
.brs-upload.loaded i { color:var(--grn); }
.brs-upload p { font-size:12px; color:var(--tx2); margin:0; }
/* ── PROGRESS BAR ── */
.brs-prog-wrap { height:5px; background:var(--bg3); border-radius:5px; overflow:hidden; margin:10px 0; }
.brs-prog-fill { height:100%; border-radius:5px; background:var(--grn); transition:width .4s ease; }
/* ── SETTINGS ── */
.brs-setting-row {
  display:flex; align-items:center; gap:12px; padding:10px 0;
  border-bottom:1px solid var(--brd);
}
.brs-setting-row:last-child { border-bottom:none; }
.brs-setting-row label { font-size:12px; color:var(--tx1); min-width:200px; }
.brs-setting-row input[type=range] { flex:1; }
.brs-setting-row span.val { font-size:12px; font-weight:700; min-width:50px; text-align:right; color:var(--pri2); }
/* ── SECTION HEADER ── */
.brs-section-hdr {
  display:flex; align-items:center; justify-content:space-between;
  margin-bottom:12px;
}
.brs-section-title {
  font-size:12px; font-weight:700; text-transform:uppercase;
  letter-spacing:.7px; color:var(--tx3);
}
/* ── LOADER ── */
.brs-loader {
  text-align:center; padding:48px 24px; color:var(--tx3);
}
.brs-spinner {
  width:36px; height:36px; border:3px solid var(--brd2);
  border-top-color:var(--pri); border-radius:50%;
  animation:brs-spin .7s linear infinite; margin:0 auto 14px;
}
@keyframes brs-spin { to { transform:rotate(360deg); } }
/* ── RECON STATEMENT ── */
.brs-recon-stmt { background:var(--bg2); border:1px solid var(--brd); border-radius:14px; overflow:hidden; }
.brs-recon-stmt table { width:100%; border-collapse:collapse; font-size:13px; }
.brs-recon-stmt td { padding:9px 16px; border-bottom:1px solid var(--brd); }
.brs-recon-stmt .row-sub { padding-left:32px; color:var(--tx2); }
.brs-recon-stmt .row-total td { font-weight:800; font-size:14px; border-top:2px solid var(--brd2); }
.brs-recon-stmt .row-reconciled td { color:var(--grn); }
.brs-recon-stmt .row-diff td { color:var(--red); }
/* ── INPUT / SELECT ── */
.brs-input, .brs-select {
  background:var(--bg2); border:1px solid var(--brd2); border-radius:8px;
  padding:7px 10px; font-size:12px; color:var(--tx1); font-family:inherit;
  transition:border-color .15s; width:100%;
}
.brs-input:focus, .brs-select:focus { outline:none; border-color:var(--pri); }
/* ── DIVIDER ── */
.brs-divider { border:none; border-top:1px solid var(--brd); margin:18px 0; }
/* ── EMPTY ── */
.brs-empty { text-align:center; padding:48px 24px; color:var(--tx3); }
.brs-empty i { font-size:36px; display:block; margin-bottom:12px; }
.brs-empty h4 { font-size:14px; font-weight:700; color:var(--tx2); margin:0 0 6px; }
.brs-empty p  { font-size:12px; margin:0 0 16px; }
/* ── DOC LIST ── */
.brs-doc-item {
  display:flex; align-items:center; justify-content:space-between;
  padding:11px 14px; border-bottom:1px solid var(--brd); cursor:pointer; transition:.12s;
}
.brs-doc-item:hover { background:var(--bg3); }
.brs-doc-item:last-child { border-bottom:none; }
/* ── RESPONSIVE ── */
@media(max-width:1100px) { .brs-g21 { grid-template-columns:1fr; } }
@media(max-width:800px)  { .brs-g2,.brs-g3 { grid-template-columns:1fr; } .brs-match-card { grid-template-columns:1fr; } }
@keyframes fadeIn { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
.brs-fade { animation:fadeIn .25s ease; }
        `;
        document.head.appendChild(s);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  THEME
    // ═══════════════════════════════════════════════════════════════════════════
    applyTheme(key) {
        const theme = BRS_THEMES[key] || BRS_THEMES['midnight'];
        this.activeTheme = key;
        try { localStorage.setItem('brs-theme', key); } catch(e) {}
        const root = document.getElementById('brs-root');
        if (!root) return;
        Object.entries(theme.colors).forEach(([k, v]) => root.style.setProperty('--' + k, v));
        if (theme.isDark) root.classList.add('dark-mode'); else root.classList.remove('dark-mode');
        const lbl = document.getElementById('brs-theme-label');
        if (lbl) lbl.innerHTML = theme.icon + ' ' + theme.name;
    }

    openThemePicker() {
        const cur = this.activeTheme;
        const cardsHTML = Object.entries(BRS_THEMES).map(([key, t]) => {
            const isActive = key === cur;
            const dots = ['pri','acc','grn','sky','amb']
                .map(k => `<div style="width:11px;height:11px;border-radius:3px;background:${t.colors[k]}"></div>`)
                .join('');
            return `
            <div onclick="window.__brs.applyTheme('${key}');if(window.__brs_td)window.__brs_td.hide();"
                 style="display:flex;align-items:center;gap:12px;padding:14px;border-radius:12px;
                 border:2px solid ${isActive ? t.colors.pri : t.colors.brd2};
                 background:${t.colors.card};cursor:pointer;color:${t.colors.tx1}">
                <div style="font-size:22px;width:38px;height:38px;border-radius:10px;
                    background:${t.colors.pri_x};display:flex;align-items:center;justify-content:center;flex-shrink:0">
                    ${t.icon}</div>
                <div style="flex:1">
                    <div style="font-size:13px;font-weight:700;margin-bottom:4px">${t.name}</div>
                    <div style="display:flex;gap:4px;margin-bottom:4px">${dots}</div>
                    <div style="font-size:10px;color:${t.colors.tx3}">${t.isDark ? '🌙 Dark' : '☀️ Light'}</div>
                </div>
                ${isActive ? `<span style="font-size:18px;color:${t.colors.pri}">✓</span>` : ''}
            </div>`;
        }).join('');
        const d = new frappe.ui.Dialog({
            title: '🎨 Studio Theme',
            size: 'large',
            fields: [{ fieldtype: 'HTML', fieldname: 'themes',
                options: `<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">${cardsHTML}</div>` }]
        });
        window.__brs_td = d;
        d.show();
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  SHELL
    // ═══════════════════════════════════════════════════════════════════════════
    buildShell() {
        $(this.page.main).empty();
        this.$root = $(`
        <div id="brs-root">
            <div class="brs-topbar">
                <div class="brs-logo">
                    <div class="brs-logo-dot"></div>
                    Recon Studio
                </div>
                <nav class="brs-nav" id="brs-nav"></nav>
                <div class="brs-topbar-right">
                    <button class="brs-theme-btn" onclick="window.__brs.openThemePicker()">
                        <i class="fa-solid fa-palette" style="font-size:10px"></i>
                        <span id="brs-theme-label">🌙 Midnight</span>
                    </button>
                    <div class="brs-clock" id="brs-clock"></div>
                </div>
            </div>
            <div class="brs-content brs-fade" id="brs-content">
                <div class="brs-loader"><div class="brs-spinner"></div>Loading Bank Reconciliation Studio…</div>
            </div>
        </div>`).appendTo(this.page.main);
        this.buildNav();
    }

    buildNav() {
        const views = [
            { id: 'dashboard', icon: 'fa-solid fa-gauge-high',          label: 'Dashboard'        },
            { id: 'import',    icon: 'fa-solid fa-file-excel',           label: 'Import'           },
            { id: 'matching',  icon: 'fa-solid fa-code-branch',          label: 'AI Matching', badge: 'matching' },
            { id: 'tables',    icon: 'fa-solid fa-table-columns',        label: 'Recon Tables'     },
            { id: 'statement', icon: 'fa-solid fa-scroll',               label: 'Statement'        },
            { id: 'config',    icon: 'fa-solid fa-sliders',              label: 'Settings'         },
        ];
        const html = views.map(v => `
        <button class="brs-nav-btn ${v.id === this.state.activeView ? 'active' : ''}" data-view="${v.id}">
            <i class="${v.icon}"></i> ${v.label}
            ${v.badge ? `<span class="brs-nav-badge" id="brs-badge-${v.badge}" style="display:none">0</span>` : ''}
        </button>`).join('');
        $('#brs-nav').html(html);
    }

    bindTopBar() {
        $(document).on('click', '.brs-nav-btn', (e) => {
            const view = $(e.currentTarget).data('view');
            this.switchView(view);
        });
    }

    switchView(view) {
        this.state.activeView = view;
        $('.brs-nav-btn').removeClass('active');
        $(`.brs-nav-btn[data-view="${view}"]`).addClass('active');
        this.renderView(view);
    }

    startClock() {
        const tick = () => $('#brs-clock').text(new Date().toLocaleTimeString('en-NG', { hour12: true }));
        tick(); setInterval(tick, 1000);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  DATA
    // ═══════════════════════════════════════════════════════════════════════════
    async fetchDocs() {
        try {
            const r = await frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Bank Reconciliation Statement',
                    fields: ['name', 'bank_account', 'from_date', 'to_date', 'status',
                             'variance', 'is_reconciled', 'auto_accepted_count',
                             'manually_matched_count', 'company'],
                    limit_page_length: 100,
                    order_by: 'modified desc'
                }
            });
            this.state.allDocs = (r && r.message) ? r.message : [];
        } catch(e) {
            this.state.allDocs = [];
        }
    }

    async loadDoc(name) {
        try {
            const r = await frappe.call({
                method: 'frappe.client.get',
                args: { doctype: 'Bank Reconciliation Statement', name }
            });
            if (r && r.message) {
                this.state.brsDoc  = r.message;
                this.state.bankRows = r.message.bank_statement_entries || [];
                this.state.cashRows = r.message.cashbook_entries || [];
            }
        } catch(e) {
            frappe.show_alert({ message: 'Could not load document: ' + e.message, indicator: 'red' });
        }
    }

    async saveDoc() {
        const doc = this.state.brsDoc;
        if (!doc) return;
        doc.bank_statement_entries = this.state.bankRows;
        doc.cashbook_entries       = this.state.cashRows;

        // Unpresented = cashbook GL CR unmatched (payment not yet cleared by bank)
        doc.unpresented_cheques = this.state.matches
            .filter(m => !m.bank && m.cash && flt(m.cash.credit_amount) > 0)
            .map(m => this._matchToChildRow(m.cash));

        // Uncredited = cashbook GL DR unmatched (receipt not yet credited by bank)
        doc.uncredited_cheques  = this.state.matches
            .filter(m => !m.bank && m.cash && flt(m.cash.debit_amount) > 0)
            .map(m => this._matchToChildRow(m.cash));

        // Direct Withdrawals = bank DR unmatched (not yet posted to GL → create Payment)
        doc.direct_withdrawals  = this.state.matches
            .filter(m => m.bank && !m.cash && flt(m.bank.debit_amount) > 0)
            .map(m => this._matchToChildRow(m.bank));

        // Direct Lodgments = bank CR unmatched (not yet posted to GL → create Receipt)
        doc.direct_lodgments    = this.state.matches
            .filter(m => m.bank && !m.cash && flt(m.bank.credit_amount) > 0)
            .map(m => this._matchToChildRow(m.bank));

        const adjBank = this._calcAdjustedBank();
        doc.adjusted_bank_balance = adjBank;
        doc.variance              = adjBank - flt(doc.cashbook_closing_balance);
        doc.is_reconciled         = Math.abs(doc.variance) < 1 ? 1 : 0;
        doc.status                = doc.is_reconciled ? 'Reconciled' : 'In Progress';
        doc.auto_accepted_count   = this.state.accepted.size;
        doc.ai_match_summary      = this._buildMatchSummary();
        try {
            await frappe.call({ method: 'frappe.client.save', args: { doc }, freeze: true, freeze_message: 'Saving…' });
            frappe.show_alert({ message: 'Saved successfully', indicator: 'green' });
            await this.fetchDocs();
        } catch(e) {
            frappe.show_alert({ message: 'Save error: ' + e.message, indicator: 'red' });
        }
    }

    _matchToChildRow(txn) {
        // Amounts are already stored in the correct debit_amount / credit_amount fields;
        // no type flag needed — read them directly.
        return {
            posting_date:     txn.posting_date || '',
            party:            txn.party || '',
            voucher_no:       txn.voucher_no || '',
            debit_amount:     flt(txn.debit_amount),
            credit_amount:    flt(txn.credit_amount),
            amount:           flt(txn.debit_amount || txn.credit_amount),
            account_currency: txn.account_currency || 'NGN',
            cheque_no:        txn.cheque_no || '',
            rec:              0,
            remarks:          txn.remarks || '',
        };
    }

    _calcAdjustedBank() {
        const bankBal = flt(this.state.brsDoc && this.state.brsDoc.bank_statement_closing_balance);

        // Uncredited = cashbook GL DR unmatched → receipts in transit → ADD to bank
        const uncredited  = this.state.matches
            .filter(m => !m.bank && m.cash && flt(m.cash.debit_amount) > 0)
            .reduce((s, m) => s + flt(m.cash.debit_amount), 0);

        // Unpresented = cashbook GL CR unmatched → payments outstanding → DEDUCT from bank
        const unpresented = this.state.matches
            .filter(m => !m.bank && m.cash && flt(m.cash.credit_amount) > 0)
            .reduce((s, m) => s + flt(m.cash.credit_amount), 0);

        // Direct Lodgments = bank CR unmatched → ADD to GL (not yet posted)
        const directLgmt  = this.state.matches
            .filter(m => m.bank && !m.cash && flt(m.bank.credit_amount) > 0)
            .reduce((s, m) => s + flt(m.bank.credit_amount), 0);

        // Direct Withdrawals = bank DR unmatched → DEDUCT from GL (not yet posted)
        const directWD    = this.state.matches
            .filter(m => m.bank && !m.cash && flt(m.bank.debit_amount) > 0)
            .reduce((s, m) => s + flt(m.bank.debit_amount), 0);

        // Formula: Bank + Uncredited − Unpresented + Direct Lodgments − Direct Withdrawals
        return bankBal + uncredited - unpresented + directLgmt - directWD;
    }

    _buildMatchSummary() {
        const total  = this.state.matches.filter(m => m.bank && m.cash).length;
        const high   = this.state.matches.filter(m => m.conf === 'high'   && m.bank && m.cash).length;
        const med    = this.state.matches.filter(m => m.conf === 'medium' && m.bank && m.cash).length;
        const dw     = this.state.matches.filter(m => m.bank && !m.cash && flt(m.bank.debit_amount)  > 0).length;
        const dl     = this.state.matches.filter(m => m.bank && !m.cash && flt(m.bank.credit_amount) > 0).length;
        const unp    = this.state.matches.filter(m => !m.bank && m.cash && flt(m.cash.credit_amount) > 0).length;
        const unc    = this.state.matches.filter(m => !m.bank && m.cash && flt(m.cash.debit_amount)  > 0).length;
        return `Matched: ${total} pairs (${high} high, ${med} medium). Direct W/D: ${dw} | Direct Lgmt: ${dl}. Unpresented: ${unp} | Uncredited: ${unc}. Auto-accepted: ${this.state.accepted.size}.`;
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW ROUTER
    // ═══════════════════════════════════════════════════════════════════════════
    renderView(name) {
        const map = {
            dashboard: () => this.renderDashboard(),
            import:    () => this.renderImport(),
            matching:  () => this.renderMatching(),
            tables:    () => this.renderTables(),
            statement: () => this.renderStatement(),
            config:    () => this.renderConfig(),
        };
        if (!map[name]) return;
        try { map[name](); }
        catch(e) {
            console.error('BRS renderView error:', e);
            this.setContent(`<div class="brs-empty">
                <i class="fa-solid fa-triangle-exclamation" style="color:var(--red)"></i>
                <h4>Error in ${name} view</h4>
                <p style="font-family:monospace;font-size:11px;color:var(--red)">${esc(e.message || String(e))}</p>
                <button class="brs-btn btn-sm" onclick="window.__brs.switchView('dashboard')">← Dashboard</button>
            </div>`);
        }
    }

    setContent(html) { $('#brs-content').html('<div class="brs-fade">' + html + '</div>'); }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW: DASHBOARD
    // ═══════════════════════════════════════════════════════════════════════════
    renderDashboard() {
        const docs  = this.state.allDocs;
        const recon = docs.filter(d => d.is_reconciled).length;
        const pend  = docs.filter(d => !d.is_reconciled).length;
        const matched = this.state.matches.filter(m => m.bank && m.cash).length;
        const rate    = this.state.bankRows.length ?
            Math.round(matched / this.state.bankRows.length * 100) : 0;

        const docsHTML = docs.slice(0, 10).map(d => `
        <div class="brs-doc-item" onclick="window.__brs.openDoc('${d.name}')">
            <div>
                <div style="font-size:12px;font-weight:700;color:var(--tx1)">${esc(d.bank_account || d.name)}</div>
                <div style="font-size:10px;color:var(--tx3)">${d.from_date} → ${d.to_date} · ${d.company||''}</div>
            </div>
            <div style="display:flex;align-items:center;gap:8px">
                <span class="brs-badge ${d.is_reconciled ? 'bd-green' : 'bd-amber'}">
                    ${d.is_reconciled ? '✓ Reconciled' : 'In Progress'}
                </span>
                <span style="font-size:10px;color:var(--tx3)">${d.name}</span>
            </div>
        </div>`).join('') || `<div class="brs-empty"><i class="fa-solid fa-inbox"></i><h4>No reconciliations yet</h4>
            <p>Create your first reconciliation below</p></div>`;

        this.setContent(`
        <div class="brs-banner">
            <div>
                <div class="brs-banner-title">🏦 Bank Reconciliation Studio</div>
                <div class="brs-banner-sub">AI-powered fuzzy matching · Transfer-aware · Nigerian banks optimised</div>
            </div>
            <div class="brs-btn-row">
                <button class="brs-btn btn-primary" onclick="window.__brs.newReconciliation()">
                    <i class="fa-solid fa-plus"></i> New Reconciliation
                </button>
                <button class="brs-btn" onclick="window.__brs.switchView('import')">
                    <i class="fa-solid fa-file-excel"></i> Import Excel
                </button>
            </div>
        </div>

        <div class="brs-stat-grid">
            <div class="brs-stat"><div class="brs-stat-val" style="color:var(--pri2)">${docs.length}</div><div class="brs-stat-lbl">Total Reconciliations</div></div>
            <div class="brs-stat"><div class="brs-stat-val" style="color:var(--grn)">${recon}</div><div class="brs-stat-lbl">Fully Reconciled</div></div>
            <div class="brs-stat"><div class="brs-stat-val" style="color:var(--amb)">${pend}</div><div class="brs-stat-lbl">Pending</div></div>
            <div class="brs-stat"><div class="brs-stat-val">${this.state.bankRows.length}</div><div class="brs-stat-lbl">Bank Rows Loaded</div></div>
            <div class="brs-stat"><div class="brs-stat-val">${matched}</div><div class="brs-stat-lbl">Pairs Matched</div></div>
            <div class="brs-stat"><div class="brs-stat-val" style="color:${rate >= 90 ? 'var(--grn)' : rate >= 70 ? 'var(--amb)' : 'var(--red)'}">${rate}%</div><div class="brs-stat-lbl">Match Rate</div></div>
        </div>

        <div class="brs-g21">
            <div class="brs-card">
                <div class="brs-section-hdr">
                    <div class="brs-section-title">Recent Reconciliations</div>
                    <button class="brs-btn btn-sm" onclick="window.__brs.newReconciliation()">
                        <i class="fa-solid fa-plus"></i> New
                    </button>
                </div>
                <div class="brs-tbl-wrap" style="border:none">
                    ${docsHTML}
                </div>
            </div>
            <div style="display:flex;flex-direction:column;gap:14px">
                <div class="brs-card">
                    <div class="brs-section-title" style="margin-bottom:12px">Quick Actions</div>
                    <div style="display:flex;flex-direction:column;gap:8px">
                        <button class="brs-btn" onclick="window.__brs.switchView('import')" style="justify-content:flex-start">
                            <i class="fa-solid fa-file-excel" style="color:var(--grn)"></i> Import Bank Statement (Excel)
                        </button>
                        <button class="brs-btn" onclick="window.__brs.switchView('import')" style="justify-content:flex-start">
                            <i class="fa-solid fa-book" style="color:var(--sky)"></i> Import Cashbook / GL
                        </button>
                        <button class="brs-btn ${this.state.bankRows.length ? '' : 'btn-red'}"
                            onclick="window.__brs.switchView('matching')" style="justify-content:flex-start">
                            <i class="fa-solid fa-cpu" style="color:var(--pri2)"></i> Run AI Matching Engine
                        </button>
                        <button class="brs-btn" onclick="window.__brs.switchView('statement')" style="justify-content:flex-start">
                            <i class="fa-solid fa-scroll" style="color:var(--amb)"></i> View Reconciliation Statement
                        </button>
                        <button class="brs-btn" onclick="window.__brs.saveDoc()" style="justify-content:flex-start">
                            <i class="fa-solid fa-floppy-disk" style="color:var(--grn)"></i> Save to ERPNext
                        </button>
                    </div>
                </div>
                <div class="brs-card" style="background:var(--pri_x);border-color:rgba(129,140,248,.2)">
                    <div style="font-size:11px;font-weight:700;color:var(--pri2);margin-bottom:8px">
                        <i class="fa-solid fa-brain"></i> AI Engine Status
                    </div>
                    <div style="font-size:11px;color:var(--tx2);line-height:1.7">
                        ✓ Levenshtein fuzzy match<br>
                        ✓ Token sort + Jaccard overlap<br>
                        ✓ Partial name containment<br>
                        ✓ Nigerian bank abbreviation dict<br>
                        ✓ Stop-word removal (LTD, PLC…)<br>
                        ✓ Date ±${this.state.config.dateTol} day tolerance<br>
                        ✓ Single ± column OR Dr/Cr columns<br>
                        ✓ Up to 5,000+ Excel rows
                    </div>
                </div>
            </div>
        </div>`);
    }

    newReconciliation() {
        const d = new frappe.ui.Dialog({
            title: 'New Bank Reconciliation',
            fields: [
                { fieldtype: 'Link',   fieldname: 'company',      label: 'Company',     options: 'Company',      reqd: 1 },
                { fieldtype: 'Link',   fieldname: 'bank_account', label: 'Bank Account',options: 'Bank Account',  reqd: 1 },
                { fieldtype: 'Column Break' },
                { fieldtype: 'Date',   fieldname: 'from_date',    label: 'From Date',   reqd: 1 },
                { fieldtype: 'Date',   fieldname: 'to_date',      label: 'To Date',     reqd: 1 },
                { fieldtype: 'Section Break', label: 'Opening Balances' },
                { fieldtype: 'Currency', fieldname: 'bank_statement_opening_balance', label: 'Bank Statement Opening Balance' },
                { fieldtype: 'Currency', fieldname: 'bank_statement_closing_balance', label: 'Bank Statement Closing Balance' },
                { fieldtype: 'Column Break' },
                { fieldtype: 'Currency', fieldname: 'cashbook_opening_balance', label: 'Cashbook Opening Balance' },
                { fieldtype: 'Currency', fieldname: 'cashbook_closing_balance', label: 'Cashbook Closing Balance' },
            ],
            primary_action_label: 'Create & Open',
            primary_action: async (vals) => {
                try {
                    const doc = {
                        doctype:    'Bank Reconciliation Statement',
                        company:    vals.company,
                        bank_account: vals.bank_account,
                        from_date:  vals.from_date,
                        to_date:    vals.to_date,
                        bank_statement_opening_balance: vals.bank_statement_opening_balance || 0,
                        bank_statement_closing_balance: vals.bank_statement_closing_balance || 0,
                        cashbook_opening_balance: vals.cashbook_opening_balance || 0,
                        cashbook_closing_balance: vals.cashbook_closing_balance || 0,
                        status: 'Draft',
                        account_currency: 'NGN',
                        date_tolerance_days: 3,
                        name_similarity_threshold: 70,
                        amount_tolerance_pct: 0
                    };
                    const r = await frappe.call({ method: 'frappe.client.insert', args: { doc } });
                    if (r && r.message) {
                        this.state.brsDoc = r.message;
                        d.hide();
                        frappe.show_alert({ message: 'Created: ' + r.message.name, indicator: 'green' });
                        await this.fetchDocs();
                        this.switchView('import');
                    }
                } catch(e) {
                    frappe.show_alert({ message: e.message, indicator: 'red' });
                }
            }
        });
        d.show();
    }

    async openDoc(name) {
        frappe.show_alert({ message: 'Loading ' + name + '…', indicator: 'blue' });
        await this.loadDoc(name);
        if (this.state.brsDoc) {
            // Compute matches from loaded rows if available
            if (this.state.bankRows.length && this.state.cashRows.length) {
                this.state.matches = this._computeMatches();
            }
            this.switchView('dashboard');
            frappe.show_alert({ message: 'Loaded ' + name, indicator: 'green' });
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW: IMPORT
    // ═══════════════════════════════════════════════════════════════════════════
    renderImport() {
        const bankLoaded = this.state.bankRows.length;
        const cashLoaded = this.state.cashRows.length;
        const fmt = this.state.config.amtFormat;

        this.setContent(`
        <div class="brs-section-hdr">
            <div class="brs-section-title"><i class="fa-solid fa-file-excel" style="color:var(--grn)"></i> Import Statements</div>
            <div class="brs-btn-row">
                <button class="brs-btn btn-sm" onclick="window.__brs.loadDemoData()">
                    <i class="fa-solid fa-database"></i> Load Demo (50 txns)
                </button>
            </div>
        </div>

        <div class="brs-g2" style="margin-bottom:18px">
            <div>
                <div style="font-size:11px;font-weight:700;color:var(--tx3);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px">
                    <i class="fa-solid fa-building-columns"></i> Bank Statement
                </div>
                <div class="brs-upload ${bankLoaded ? 'loaded' : ''}" id="zone-bank"
                     onclick="document.getElementById('file-bank').click()">
                    <i class="fa-solid ${bankLoaded ? 'fa-circle-check' : 'fa-cloud-arrow-up'}"></i>
                    <p><strong>${bankLoaded ? bankLoaded + ' rows loaded' : 'Click or drop .xlsx / .xls / .csv'}</strong></p>
                    <p>${bankLoaded ? 'Click to replace' : 'Supports up to 5,000+ rows · Auto-detects columns'}</p>
                </div>
                <input type="file" id="file-bank" accept=".xlsx,.xls,.csv" style="display:none"
                    onchange="window.__brs.handleExcel(event,'bank')">
                <div style="margin-top:10px">
                    <div style="font-size:11px;color:var(--tx3);margin-bottom:6px">Amount column format:</div>
                    <select class="brs-select" id="bank-fmt-sel" onchange="window.__brs.state.config.amtFormat=this.value">
                        <option value="drcr"       ${fmt==='drcr'       ?'selected':''}>Separate Debit / Credit columns</option>
                        <option value="single"     ${fmt==='single'     ?'selected':''}>Single column (positive = credit, negative = debit)</option>
                        <option value="single_inv" ${fmt==='single_inv' ?'selected':''}>Single column (positive = debit, negative = credit)</option>
                        <option value="drcr_flag"  ${fmt==='drcr_flag'  ?'selected':''}>Amount + Dr/Cr flag column</option>
                    </select>
                </div>
                ${bankLoaded ? `
                <div class="brs-tbl-wrap" style="margin-top:12px;max-height:220px;overflow-y:auto">
                    <table class="brs-tbl">
                        <thead><tr><th>Date</th><th>Narration / Party</th><th>Bank Dr (Payment)</th><th>Bank Cr (Receipt)</th></tr></thead>
                        <tbody>${this.state.bankRows.slice(0,10).map(r => `
                        <tr>
                            <td>${r.posting_date||''}</td>
                            <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(r.party||r.remarks||'')}</td>
                            <td style="text-align:right;color:var(--red)">${r.debit_amount ? fmtN(r.debit_amount) : ''}</td>
                            <td style="text-align:right;color:var(--grn)">${r.credit_amount ? fmtN(r.credit_amount) : ''}</td>
                        </tr>`).join('')}
                        ${bankLoaded > 10 ? `<tr><td colspan="4" style="text-align:center;font-size:10px;color:var(--tx3)">… and ${bankLoaded - 10} more rows</td></tr>` : ''}
                        </tbody>
                    </table>
                </div>` : ''}
            </div>

            <div>
                <div style="font-size:11px;font-weight:700;color:var(--tx3);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px">
                    <i class="fa-solid fa-book"></i> Cashbook / GL Ledger
                </div>
                <div class="brs-upload ${cashLoaded ? 'loaded' : ''}" id="zone-cash"
                     onclick="document.getElementById('file-cash').click()">
                    <i class="fa-solid ${cashLoaded ? 'fa-circle-check' : 'fa-cloud-arrow-up'}"></i>
                    <p><strong>${cashLoaded ? cashLoaded + ' rows loaded' : 'Click or drop .xlsx / .xls / .csv'}</strong></p>
                    <p>${cashLoaded ? 'Click to replace' : 'Payee name · Date · Debit · Credit · Reference'}</p>
                </div>
                <input type="file" id="file-cash" accept=".xlsx,.xls,.csv" style="display:none"
                    onchange="window.__brs.handleExcel(event,'cash')">
                <div style="margin-top:10px">
                    <div style="font-size:11px;color:var(--tx3);margin-bottom:6px">Cashbook amount column format:</div>
                    <select class="brs-select" id="cash-fmt-sel"
                        onchange="window.__brs.state.config.cashAmtFormat=this.value">
                        <option value="drcr"       ${(this.state.config.cashAmtFormat||'drcr')==='drcr'       ?'selected':''}>Separate Debit / Credit columns (ERPNext GL default)</option>
                        <option value="single"     ${(this.state.config.cashAmtFormat||'drcr')==='single'     ?'selected':''}>Single column (positive = credit/receipt, negative = debit/payment)</option>
                        <option value="single_inv" ${(this.state.config.cashAmtFormat||'drcr')==='single_inv' ?'selected':''}>Single column (positive = debit/payment, negative = credit/receipt)</option>
                        <option value="drcr_flag"  ${(this.state.config.cashAmtFormat||'drcr')==='drcr_flag'  ?'selected':''}>Amount + Dr/Cr flag column</option>
                    </select>
                    <div style="font-size:10px;color:var(--tx3);margin-top:5px">
                        <strong>Reminder:</strong> GL DR = Receipt (asset up) · GL CR = Payment (asset out)
                    </div>
                </div>
                ${cashLoaded ? `
                <div class="brs-tbl-wrap" style="margin-top:12px;max-height:220px;overflow-y:auto">
                    <table class="brs-tbl">
                        <thead><tr><th>Date</th><th>Payee / Narration</th><th>GL Dr (Receipt)</th><th>GL Cr (Payment)</th><th>Ref</th></tr></thead>
                        <tbody>${this.state.cashRows.slice(0,10).map(r => `
                        <tr>
                            <td>${r.posting_date||''}</td>
                            <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(r.party||r.remarks||'')}</td>
                            <td style="text-align:right;color:var(--grn)">${r.debit_amount ? fmtN(r.debit_amount) : ''}</td>
                            <td style="text-align:right;color:var(--red)">${r.credit_amount ? fmtN(r.credit_amount) : ''}</td>
                            <td style="font-size:10px;color:var(--tx3)">${esc(r.voucher_no||'')}</td>
                        </tr>`).join('')}
                        ${cashLoaded > 10 ? `<tr><td colspan="5" style="text-align:center;font-size:10px;color:var(--tx3)">… and ${cashLoaded - 10} more rows</td></tr>` : ''}
                        </tbody>
                    </table>
                </div>` : ''}
            </div>
        </div>

        <div class="brs-card" style="margin-bottom:18px">
            <div style="font-size:11px;font-weight:700;color:var(--tx3);text-transform:uppercase;letter-spacing:.5px;margin-bottom:12px">
                Column Mapping Guide
            </div>
            <div class="brs-g3" style="font-size:11px;color:var(--tx2);line-height:1.8">
                <div>
                    <strong style="color:var(--tx1)">Bank Statement expects:</strong><br>
                    • Column: <code style="color:var(--pri2)">date</code> or <code style="color:var(--pri2)">posting_date</code><br>
                    • Column: <code style="color:var(--pri2)">description</code>, <code style="color:var(--pri2)">narration</code>, or <code style="color:var(--pri2)">party</code><br>
                    • Column: <code style="color:var(--pri2)">debit</code>/<code style="color:var(--pri2)">credit</code> OR <code style="color:var(--pri2)">amount</code> (single ±)
                </div>
                <div>
                    <strong style="color:var(--tx1)">Cashbook expects:</strong><br>
                    • Column: <code style="color:var(--pri2)">date</code> or <code style="color:var(--pri2)">posting_date</code><br>
                    • Column: <code style="color:var(--pri2)">payee</code>, <code style="color:var(--pri2)">party</code>, or <code style="color:var(--pri2)">narration</code><br>
                    • Column: <code style="color:var(--pri2)">reference</code> or <code style="color:var(--pri2)">voucher_no</code>
                </div>
                <div>
                    <strong style="color:var(--tx1)">Nigerian bank dates:</strong><br>
                    • Auto-detects DD/MM/YYYY, YYYY-MM-DD, MM/DD/YYYY<br>
                    • Handles Excel serial date numbers<br>
                    • Column headers are case-insensitive
                </div>
            </div>
        </div>

        <div class="brs-btn-row">
            <button class="brs-btn btn-primary" onclick="window.__brs.runAIMatching()"
                ${bankLoaded && cashLoaded ? '' : 'disabled style="opacity:.5;cursor:not-allowed"'}>
                <i class="fa-solid fa-cpu"></i>
                ${bankLoaded && cashLoaded ? 'Run AI Matching →' : 'Load both files first'}
            </button>
        </div>`);
    }

    handleExcel(event, target) {
        const file = event.target.files[0];
        if (!file) return;
        const label = target === 'bank' ? 'bank statement' : 'cashbook';
        frappe.show_alert({ message: 'Parsing ' + file.name + '…', indicator: 'blue' });
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const wb   = XLSX.read(e.target.result, { type: 'binary', cellDates: true });
                const ws   = wb.Sheets[wb.SheetNames[0]];
                const raw  = XLSX.utils.sheet_to_json(ws, { defval: '' });
                const rows = this._normaliseRows(raw, target);

                if (rows.length === 0) {
                    // Zero rows — give the user a diagnostic message
                    const hint = target === 'bank'
                        ? 'Check that your file has date, debit/credit columns and the correct Amount Format selected above.'
                        : 'Check that your file has date, debit/credit columns and the correct Cashbook Amount Format selected.';
                    frappe.msgprint({
                        title: `No rows loaded from ${label}`,
                        indicator: 'orange',
                        message:
                            `<strong>${raw.length} raw rows</strong> were read from <em>${file.name}</em> ` +
                            `but 0 passed the filter (need a parseable date + non-zero debit or credit).<br><br>` +
                            `<strong>Common causes:</strong><br>` +
                            `• Column headers don't match expected aliases (date, debit, credit, party, reference)<br>` +
                            `• Wrong Amount Format selected (try switching to "Separate Debit / Credit columns")<br>` +
                            `• Date column contains text that cannot be parsed<br>` +
                            `• All amount values are zero or blank<br><br>` +
                            hint + `<br><br>` +
                            `<strong>First row headers detected:</strong> ` +
                            (raw.length ? Object.keys(raw[0]).join(', ') : 'none')
                    });
                    return;
                }

                if (target === 'bank') {
                    this.state.bankRows = rows;
                    frappe.show_alert({
                        message: `${rows.length} bank statement rows loaded from ${file.name}`,
                        indicator: 'green'
                    });
                } else {
                    this.state.cashRows = rows;
                    frappe.show_alert({
                        message: `${rows.length} cashbook rows loaded from ${file.name}`,
                        indicator: 'green'
                    });
                }

                // Sync into doc tables if a BRS document is open
                if (this.state.brsDoc) {
                    if (target === 'bank') this.state.brsDoc.bank_statement_entries = rows;
                    else                   this.state.brsDoc.cashbook_entries        = rows;
                }

                this.renderImport();

            } catch(err) {
                frappe.msgprint({
                    title:     `Error parsing ${label}`,
                    indicator: 'red',
                    message:   `<strong>${err.message}</strong><br><br>` +
                               `Ensure the file is a valid .xlsx, .xls or .csv and is not password-protected.`
                });
                console.error('BRS handleExcel error:', err);
            }
        };
        reader.readAsBinaryString(file);
    }

    _normaliseRows(raw, target) {
        // Column aliases — case-insensitive, trims whitespace.
        // NOTE: We read debit/credit columns literally for both bank and cashbook.
        // The CROSS-POLARITY matching engine handles interpretation:
        //   Bank DR (payment out) matches Cashbook GL CR (payment out)
        //   Bank CR (receipt in)  matches Cashbook GL DR (receipt in)
        const aliases = {
            date:       ['date','posting_date','txn_date','transaction_date',
                         'value_date','trans date','value date','tran date',
                         'transaction date','entry date','doc date'],
            party:      ['party','payee','description','narration','particulars',
                         'details','beneficiary','name','counterpart','account name',
                         'party name','supplier','customer','vendor'],
            debit:      ['debit','debit_amount','dr','withdrawal','payment',
                         'debit amount','withdrawals','dr amount','paid out',
                         'debitamount','debitamt'],
            credit:     ['credit','credit_amount','cr','deposit','receipt',
                         'credit amount','deposits','cr amount','paid in',
                         'creditamount','creditamt'],
            amount:     ['amount','net_amount','net amount','transaction amount',
                         'txn amount','value','tran amount'],
            voucher_no: ['voucher_no','reference','ref','cheque_no','cheque no',
                         'trans ref','trans_ref','transaction ref','ref no',
                         'doc no','document no','voucher','journal no',
                         'payment ref','receipt ref','reference no','folio'],
            type_flag:  ['type','dr/cr','transaction_type','txn type','entry type'],
            remarks:    ['remarks','memo','note','notes','comment','narration2',
                         'description2','additional info']
        };

        const pick = (row, keys) => {
            for (const k of keys) {
                const found = Object.keys(row).find(
                    rk => rk.toString().toLowerCase().trim() === k
                );
                if (found !== undefined &&
                    row[found] !== '' &&
                    row[found] !== null &&
                    row[found] !== undefined) {
                    return row[found];
                }
            }
            return '';
        };

        const parseDate = (v) => {
            if (!v) return '';
            if (v instanceof Date) return v.toISOString().split('T')[0];
            const s = String(v).trim();
            // Excel serial (integer in plausible date range)
            if (/^\d{4,5}$/.test(s) && parseInt(s) > 30000) {
                const d = new Date(Math.round((parseInt(s) - 25569) * 86400 * 1000));
                return isNaN(d) ? '' : d.toISOString().split('T')[0];
            }
            // DD/MM/YYYY or DD-MM-YYYY
            const dmy = s.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})$/);
            if (dmy) {
                const dt = new Date(parseInt(dmy[3]), parseInt(dmy[2])-1, parseInt(dmy[1]));
                return isNaN(dt) ? '' : dt.toISOString().split('T')[0];
            }
            // YYYY-MM-DD or YYYY/MM/DD
            const ymd = s.match(/^(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})/);
            if (ymd) return `${ymd[1]}-${ymd[2].padStart(2,'0')}-${ymd[3].padStart(2,'0')}`;
            // Native fallback
            const dt = new Date(s);
            return isNaN(dt) ? '' : dt.toISOString().split('T')[0];
        };

        // Bank uses state.config.amtFormat; cashbook uses state.config.cashAmtFormat.
        // Both default to 'drcr' (separate Debit / Credit columns).
        const fmt = target === 'cash'
            ? (this.state.config.cashAmtFormat || 'drcr')
            : (this.state.config.amtFormat      || 'drcr');

        const rows = raw.map((row, idx) => {
            const rawDate    = pick(row, aliases.date);
            const rawParty   = String(pick(row, aliases.party)      || '').trim();
            const rawVoucher = String(pick(row, aliases.voucher_no) || '').trim();
            const rawRemark  = String(pick(row, aliases.remarks)    || '').trim();

            let debit = 0, credit = 0;

            if (fmt === 'drcr' || !pick(row, aliases.amount)) {
                debit  = flt(pick(row, aliases.debit));
                credit = flt(pick(row, aliases.credit));
            } else if (fmt === 'single') {
                // positive = credit/receipt, negative = debit/payment
                const amt = flt(pick(row, aliases.amount));
                if (amt >= 0) credit = amt; else debit = Math.abs(amt);
            } else if (fmt === 'single_inv') {
                // positive = debit/payment, negative = credit/receipt
                const amt = flt(pick(row, aliases.amount));
                if (amt >= 0) debit = amt; else credit = Math.abs(amt);
            } else if (fmt === 'drcr_flag') {
                const amt  = Math.abs(flt(pick(row, aliases.amount)));
                const flag = String(pick(row, aliases.type_flag) || '').toUpperCase().trim();
                if (flag === 'CR' || flag === 'C' || flag === 'CREDIT') credit = amt;
                else debit = amt;
            }

            return {
                idx,
                posting_date:    parseDate(rawDate),
                party:           rawParty,
                voucher_no:      rawVoucher,
                debit_amount:    debit,
                credit_amount:   credit,
                amount:          debit > 0 ? -debit : credit,
                account_currency:'NGN',
                cheque_no:       rawVoucher,
                remarks:         rawRemark,
                rec:             0,
            };
        });

        const valid   = rows.filter(r => r.posting_date && (r.debit_amount > 0 || r.credit_amount > 0));
        const dropped = rows.length - valid.length;
        if (dropped > 0) {
            console.warn(
                `BRS _normaliseRows [${target}]: dropped ${dropped} of ${rows.length} rows ` +
                `(missing date or zero amounts). Check column mapping and format selector.`
            );
        }
        return valid;
    }

    loadDemoData() {
        // ── BANK STATEMENT rows (bank's perspective) ──────────────────────────
        // Bank DR = money LEAVING  your account = a payment made by you
        // Bank CR = money ENTERING your account = a receipt received by you
        this.state.bankRows = [
            { idx:0,  posting_date:'2026-06-01', party:'TRF FROM DANGOTE CEM LTD',         debit_amount:0,       credit_amount:2500000, voucher_no:'', amount:2500000,  account_currency:'NGN', cheque_no:'', remarks:'', rec:0 },
            // Bank CR = receipt (Dangote paid us)
            { idx:1,  posting_date:'2026-06-01', party:'TRF TO ACCESS BANK/SHELL PETROL',  debit_amount:450000,  credit_amount:0,       voucher_no:'', amount:-450000,  account_currency:'NGN', cheque_no:'', remarks:'', rec:0 },
            // Bank DR = payment (we paid Shell)
            { idx:2,  posting_date:'2026-06-02', party:'CHG COMMISSION ON TURNOVER',        debit_amount:12500,   credit_amount:0,       voucher_no:'', amount:-12500,   account_currency:'NGN', cheque_no:'', remarks:'Bank Charge', rec:0 },
            // Bank DR = payment (bank charge — no cashbook entry yet → Direct Withdrawal)
            { idx:3,  posting_date:'2026-06-02', party:'INWARD TRF FLUTTERWAVE/PAYSTACK',  debit_amount:0,       credit_amount:875000,  voucher_no:'', amount:875000,   account_currency:'NGN', cheque_no:'', remarks:'', rec:0 },
            // Bank CR = receipt (Flutterwave collection)
            { idx:4,  posting_date:'2026-06-03', party:'NIP OUTWARD TRF-OLATUNDE ADEYEMI', debit_amount:320000,  credit_amount:0,       voucher_no:'', amount:-320000,  account_currency:'NGN', cheque_no:'', remarks:'', rec:0 },
            // Bank DR = payment (we paid Adeyemi)
            { idx:5,  posting_date:'2026-06-03', party:'STAMP DUTY CHARGE FGN',             debit_amount:50,      credit_amount:0,       voucher_no:'', amount:-50,      account_currency:'NGN', cheque_no:'', remarks:'Stamp Duty', rec:0 },
            // Bank DR = payment (stamp duty — no cashbook entry → Direct Withdrawal)
            { idx:6,  posting_date:'2026-06-04', party:'TRF FROM MTN NIG COMMS PLC',        debit_amount:0,       credit_amount:1200000, voucher_no:'', amount:1200000,  account_currency:'NGN', cheque_no:'', remarks:'', rec:0 },
            // Bank CR = receipt (MTN paid us)
            { idx:7,  posting_date:'2026-06-05', party:'INTERSWITCH PAYMENT-NNPC LTD',     debit_amount:680000,  credit_amount:0,       voucher_no:'', amount:-680000,  account_currency:'NGN', cheque_no:'', remarks:'', rec:0 },
            // Bank DR = payment (we paid NNPC)
            { idx:8,  posting_date:'2026-06-06', party:'INWARD TRF/ZENITH-CONOIL PLC',     debit_amount:0,       credit_amount:340000,  voucher_no:'', amount:340000,   account_currency:'NGN', cheque_no:'', remarks:'', rec:0 },
            // Bank CR = receipt (Conoil paid us)
            { idx:9,  posting_date:'2026-06-07', party:'VALUE ADDED TAX REMITTANCE',        debit_amount:125000,  credit_amount:0,       voucher_no:'', amount:-125000,  account_currency:'NGN', cheque_no:'', remarks:'VAT', rec:0 },
            // Bank DR = payment (VAT remittance — no cashbook entry → Direct Withdrawal)
            { idx:10, posting_date:'2026-06-08', party:'TRF FROM VALUE IMPACTS CONSULTING', debit_amount:0,       credit_amount:500000,  voucher_no:'', amount:500000,   account_currency:'NGN', cheque_no:'', remarks:'', rec:0 },
            // Bank CR = receipt (inter-company receipt)
            { idx:11, posting_date:'2026-06-09', party:'SALARY PAYMENT JUN-STAFF',          debit_amount:2100000, credit_amount:0,       voucher_no:'', amount:-2100000, account_currency:'NGN', cheque_no:'', remarks:'Payroll', rec:0 },
            // Bank DR = payment (salaries paid)
            { idx:12, posting_date:'2026-06-09', party:'PENCOM REMITTANCE',                 debit_amount:210000,  credit_amount:0,       voucher_no:'', amount:-210000,  account_currency:'NGN', cheque_no:'', remarks:'Pension', rec:0 },
            // Bank DR = payment (pension contribution)
            { idx:13, posting_date:'2026-06-10', party:'TRF FROM LAFARGE AFRIC CEMENT',     debit_amount:0,       credit_amount:3750000, voucher_no:'', amount:3750000,  account_currency:'NGN', cheque_no:'', remarks:'', rec:0 },
            // Bank CR = receipt (Lafarge paid us)
            { idx:14, posting_date:'2026-06-11', party:'FIRS WHT REMITTANCE',               debit_amount:87500,   credit_amount:0,       voucher_no:'', amount:-87500,   account_currency:'NGN', cheque_no:'', remarks:'WHT', rec:0 },
            // Bank DR = payment (WHT remittance — no cashbook entry → Direct Withdrawal)
        ];

        // ── CASHBOOK / GL rows (entity's perspective — MIRROR OPPOSITE) ───────
        // GL DR = bank asset INCREASING = a RECEIPT (money came in)
        // GL CR = bank asset DECREASING = a PAYMENT (money went out)
        //
        // Cross-polarity matching:
        //   Bank CR (receipt in) matches GL DR (receipt in)   ← same economic event
        //   Bank DR (payment out) matches GL CR (payment out) ← same economic event
        this.state.cashRows = [
            { idx:0,  posting_date:'2026-06-01', party:'Dangote Cement Company Limited',  voucher_no:'INV-2026-0441', debit_amount:2500000, credit_amount:0,       amount:2500000,  account_currency:'NGN', cheque_no:'', remarks:'Sales Invoice', rec:0 },
            // GL DR = receipt (Dangote paid us — matches Bank idx:0 CR)
            { idx:1,  posting_date:'2026-06-01', party:'Shell Petroleum Dev Co Nigeria',  voucher_no:'PV-001',        debit_amount:0,       credit_amount:450000,  amount:-450000,  account_currency:'NGN', cheque_no:'', remarks:'Payment Voucher', rec:0 },
            // GL CR = payment (we paid Shell — matches Bank idx:1 DR)
            { idx:2,  posting_date:'2026-06-02', party:'Flutterwave Collections Nigeria', voucher_no:'FW-88234',      debit_amount:875000,  credit_amount:0,       amount:875000,   account_currency:'NGN', cheque_no:'', remarks:'Online Receipt', rec:0 },
            // GL DR = receipt (Flutterwave — matches Bank idx:3 CR)
            { idx:3,  posting_date:'2026-06-03', party:'Olatunde Adeyemi and Associates', voucher_no:'PV-002',        debit_amount:0,       credit_amount:320000,  amount:-320000,  account_currency:'NGN', cheque_no:'', remarks:'Consultant Fee', rec:0 },
            // GL CR = payment (we paid Adeyemi — matches Bank idx:4 DR)
            { idx:4,  posting_date:'2026-06-04', party:'MTN Nigeria Communications Plc',  voucher_no:'INV-2026-0442', debit_amount:1200000, credit_amount:0,       amount:1200000,  account_currency:'NGN', cheque_no:'', remarks:'', rec:0 },
            // GL DR = receipt (MTN paid us — matches Bank idx:6 CR)
            { idx:5,  posting_date:'2026-06-05', party:'NNPC Limited',                    voucher_no:'PV-003',        debit_amount:0,       credit_amount:680000,  amount:-680000,  account_currency:'NGN', cheque_no:'', remarks:'', rec:0 },
            // GL CR = payment (we paid NNPC — matches Bank idx:7 DR)
            { idx:6,  posting_date:'2026-06-06', party:'Conoil Plc',                      voucher_no:'INV-2026-0443', debit_amount:340000,  credit_amount:0,       amount:340000,   account_currency:'NGN', cheque_no:'', remarks:'', rec:0 },
            // GL DR = receipt (Conoil paid us — matches Bank idx:8 CR)
            { idx:7,  posting_date:'2026-06-08', party:'Value Impacts Consulting Limited', voucher_no:'JV-001',        debit_amount:500000,  credit_amount:0,       amount:500000,   account_currency:'NGN', cheque_no:'', remarks:'Journal Voucher', rec:0 },
            // GL DR = receipt (inter-company — matches Bank idx:10 CR)
            { idx:8,  posting_date:'2026-06-09', party:'Staff Salaries June 2026',         voucher_no:'SAL-JUN26',     debit_amount:0,       credit_amount:2100000, amount:-2100000, account_currency:'NGN', cheque_no:'', remarks:'Payroll', rec:0 },
            // GL CR = payment (salaries — matches Bank idx:11 DR)
            { idx:9,  posting_date:'2026-06-09', party:'PENCOM Retirement Savings',        voucher_no:'PEN-JUN26',     debit_amount:0,       credit_amount:210000,  amount:-210000,  account_currency:'NGN', cheque_no:'', remarks:'Pension', rec:0 },
            // GL CR = payment (pension — matches Bank idx:12 DR)
            { idx:10, posting_date:'2026-06-10', party:'Lafarge Africa Plc',               voucher_no:'INV-2026-0444', debit_amount:3750000, credit_amount:0,       amount:3750000,  account_currency:'NGN', cheque_no:'', remarks:'', rec:0 },
            // GL DR = receipt (Lafarge paid us — matches Bank idx:13 CR)
            { idx:11, posting_date:'2026-06-12', party:'Office Furniture Unposted',        voucher_no:'PV-004',        debit_amount:0,       credit_amount:95000,   amount:-95000,   account_currency:'NGN', cheque_no:'', remarks:'Capital Expense — Not Yet In Bank', rec:0 },
            // GL CR = payment (furniture — not yet in bank → Unpresented Transfer)
        ];
        frappe.show_alert({ message: 'Demo data loaded: 15 bank + 12 cashbook rows', indicator: 'green' });
        this.renderImport();
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  AI MATCHING ENGINE
    // ═══════════════════════════════════════════════════════════════════════════
    _levenshtein(a, b) {
        a = a.toUpperCase(); b = b.toUpperCase();
        const m = a.length, n = b.length;
        if (!m) return n; if (!n) return m;
        const dp = Array.from({ length: m + 1 }, (_, i) => [i]);
        for (let j = 1; j <= n; j++) dp[0][j] = j;
        for (let i = 1; i <= m; i++) {
            for (let j = 1; j <= n; j++) {
                dp[i][j] = a[i-1] === b[j-1] ? dp[i-1][j-1] :
                    1 + Math.min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1]);
            }
        }
        return dp[m][n];
    }

    _normaliseText(s) {
        s = String(s || '').toUpperCase();
        // Expand abbreviations
        for (const [k, v] of Object.entries(BRS_ABBREV)) {
            s = s.replace(new RegExp('\\b' + k.replace(/[.*+?^${}()|[\]\\]/g,'\\$&') + '\\b', 'g'), v || '');
        }
        // Remove non-alpha, filter stop-words
        return s.replace(/[^A-Z0-9 ]/g, ' ')
            .split(/\s+/)
            .filter(w => w.length > 0 && !BRS_STOPWORDS.has(w))
            .join(' ')
            .trim();
    }

    _nameSimilarity(a, b) {
        const na = this._normaliseText(a);
        const nb = this._normaliseText(b);
        if (!na || !nb) return 0;
        // Levenshtein ratio
        const maxLen = Math.max(na.length, nb.length);
        const lev = 1 - this._levenshtein(na, nb) / maxLen;
        // Token overlap (Jaccard)
        const setA = new Set(na.split(' '));
        const setB = new Set(nb.split(' '));
        let inter = 0;
        for (const w of setA) if (setB.has(w)) inter++;
        const union = setA.size + setB.size - inter;
        const jaccard = union > 0 ? inter / union : 0;
        // Partial containment
        const partial = na.includes(nb) || nb.includes(na) ? 1 : 0;
        // Max of all three algorithms
        return Math.max(lev, jaccard * 0.9, partial);
    }

    _dateDiff(a, b) {
        return Math.abs((new Date(a) - new Date(b)) / (1000 * 60 * 60 * 24));
    }

    _computeMatches() {
        const { dateTol, nameTol, amtTol, hiConf } = this.state.config;
        const nameTolFrac = nameTol / 100;
        const amtTolFrac  = amtTol  / 100;
        const hiConfFrac  = hiConf  / 100;

        const usedCash = new Set();
        const pairs    = [];

        for (const b of this.state.bankRows) {
            // ── Bank polarity ────────────────────────────────────────────────
            // Bank DR = payment leaving account
            // Bank CR = receipt entering account
            const bIsDR = flt(b.debit_amount) > 0;
            const bAmt  = bIsDR ? flt(b.debit_amount) : flt(b.credit_amount);

            let best = null, bestScore = 0;

            for (const c of this.state.cashRows) {
                if (usedCash.has(c.idx)) continue;

                // ── Cross-polarity rule ──────────────────────────────────────
                // GL DR = receipt (asset up);  GL CR = payment (asset down)
                // Bank DR (payment out) must match GL CR (payment out)
                // Bank CR (receipt in)  must match GL DR (receipt in)
                const cIsDR = flt(c.debit_amount) > 0;
                const cAmt  = cIsDR ? flt(c.debit_amount) : flt(c.credit_amount);

                // Bank DR pairs with GL CR; Bank CR pairs with GL DR
                if (bIsDR !== !cIsDR) continue;   // bIsDR XOR cIsDR must be true

                // ── Amount score (50%) ───────────────────────────────────────
                if (bAmt === 0 && cAmt === 0) continue;
                const amtDiff = Math.abs(bAmt - cAmt) / Math.max(bAmt, cAmt, 0.01);
                let amtScore;
                if (amtDiff === 0)               amtScore = 1.0;
                else if (amtDiff <= amtTolFrac)  amtScore = 0.92;
                else if (amtDiff <= 0.001)        amtScore = 0.88;
                else continue;

                // ── Date score (25%) ─────────────────────────────────────────
                const dd = this._dateDiff(b.posting_date, c.posting_date);
                if (dd > dateTol) continue;
                const dateScore = dd === 0 ? 1.0 : 1.0 - (dd / (dateTol + 1)) * 0.20;

                // ── Name score (25%) ─────────────────────────────────────────
                const ns = this._nameSimilarity(b.party || b.remarks, c.party || c.remarks);

                const total = amtScore * 0.50 + dateScore * 0.25 + ns * 0.25;
                if (total > bestScore && ns >= nameTolFrac * 0.40) {
                    bestScore = total; best = c;
                }
            }

            let conf = 'low', confClass = 'conf-low';
            if (bestScore >= hiConfFrac)   { conf = 'high';   confClass = 'conf-high';   }
            else if (bestScore >= 0.55)    { conf = 'medium'; confClass = 'conf-medium'; }

            if (best) usedCash.add(best.idx);

            // Unmatched bank row category:
            // Bank DR with no GL match → Direct Withdrawal (bank paid, not in GL yet)
            // Bank CR with no GL match → Direct Lodgment   (bank received, not in GL yet)
            pairs.push({
                bank:              b,
                cash:              best,
                score:             Math.round(bestScore * 100),
                conf,
                confClass,
                bankIsDR:          bIsDR,
                unmatchedCategory: !best ? (bIsDR ? 'direct_withdrawal' : 'direct_lodgment') : null,
            });
        }

        // Cashbook-only rows — no bank match found
        // GL CR unmatched → Unpresented Transfer (payment in GL, not yet in bank)
        // GL DR unmatched → Uncredited Transfer  (receipt in GL, not yet in bank)
        for (const c of this.state.cashRows) {
            if (!pairs.find(p => p.cash && p.cash.idx === c.idx)) {
                const cIsDR = flt(c.debit_amount) > 0;
                pairs.push({
                    bank:              null,
                    cash:              c,
                    score:             0,
                    conf:              'unmatched',
                    confClass:         'conf-low',
                    cashIsDR:          cIsDR,
                    // GL CR = payment not yet cleared → Unpresented
                    // GL DR = receipt not yet credited → Uncredited
                    unmatchedCategory: cIsDR ? 'uncredited_cheque' : 'unpresented_cheque',
                });
            }
        }

        return pairs;
    }

    runAIMatching() {
        if (!this.state.bankRows.length || !this.state.cashRows.length) {
            frappe.show_alert({ message: 'Load both bank statement and cashbook first', indicator: 'orange' });
            return;
        }
        this.switchView('matching');
        this._doMatch();
    }

    _doMatch() {
        const steps = [
            'Normalising bank descriptions…',
            'Expanding Nigerian bank abbreviations…',
            'Removing stop-words (LTD, PLC, NIG…)…',
            'Running Levenshtein fuzzy matching…',
            'Computing Jaccard token overlap…',
            'Partial containment scoring…',
            'Applying date ±' + this.state.config.dateTol + ' day tolerance…',
            'Computing composite confidence scores…',
            'Sorting by confidence level…',
            'Auto-accepting high-confidence pairs…',
            'Building reconciliation tables…',
            'Done!'
        ];
        let step = 0;
        const progBar = document.getElementById('brs-prog-fill');
        const progMsg = document.getElementById('brs-prog-msg');

        const tick = () => {
            if (progMsg) progMsg.textContent = steps[step] || steps[steps.length - 1];
            if (progBar) progBar.style.width = Math.min(100, Math.round((step + 1) / steps.length * 100)) + '%';
            step++;
            if (step >= steps.length) {
                // Actually compute
                this.state.matches  = this._computeMatches();
                this.state.accepted = new Set();
                // Auto-accept high confidence
                this.state.matches.forEach((m, i) => {
                    if (m.conf === 'high' && m.bank && m.cash) this.state.accepted.add(i);
                });
                // Update badge
                const unmatched = this.state.matches.filter(m => !m.bank || !m.cash).length;
                $('#brs-badge-matching').text(unmatched).toggle(unmatched > 0);
                this._renderMatchContent();
            } else {
                setTimeout(tick, 280);
            }
        };
        tick();
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW: MATCHING
    // ═══════════════════════════════════════════════════════════════════════════
    renderMatching() {
        const hasMatches = this.state.matches.length > 0;
        if (!hasMatches) {
            if (!this.state.bankRows.length || !this.state.cashRows.length) {
                this.setContent(`<div class="brs-empty">
                    <i class="fa-solid fa-file-import"></i>
                    <h4>No data loaded</h4>
                    <p>Go to Import tab and load your bank statement and cashbook first.</p>
                    <button class="brs-btn btn-primary btn-sm" onclick="window.__brs.switchView('import')">
                        <i class="fa-solid fa-file-excel"></i> Import Statements
                    </button>
                </div>`);
                return;
            }
            // Show loader and run
            this.setContent(`
            <div class="brs-loader" id="brs-match-loader">
                <div class="brs-spinner"></div>
                <div style="font-weight:700;font-size:14px;color:var(--tx1);margin-bottom:6px">Running AI Matching Engine</div>
                <div id="brs-prog-msg" style="font-size:12px;color:var(--tx3);margin-bottom:12px">Initialising…</div>
                <div class="brs-prog-wrap" style="max-width:320px;margin:0 auto">
                    <div class="brs-prog-fill" id="brs-prog-fill" style="width:0%"></div>
                </div>
            </div>`);
            this._doMatch();
        } else {
            this._renderMatchContent();
        }
    }

    _renderMatchContent() {
        const matches = this.state.matches;
        const paired  = matches.filter(m => m.bank && m.cash);
        const high    = paired.filter(m => m.conf === 'high').length;
        const med     = paired.filter(m => m.conf === 'medium').length;
        const unbank  = matches.filter(m => m.bank && !m.cash).length;
        const uncash  = matches.filter(m => !m.bank && m.cash).length;
        const total   = this.state.bankRows.length;
        const rate    = total ? Math.round(paired.length / total * 100) : 0;

        const filtered = this._applyMatchFilter(matches);
        const cardsHTML = filtered.map((m, i) => this._matchCard(m, i)).join('');

        this.setContent(`
        <div class="brs-section-hdr">
            <div class="brs-section-title"><i class="fa-solid fa-cpu" style="color:var(--pri2)"></i> AI Match Results</div>
            <div class="brs-btn-row">
                <button class="brs-btn btn-green btn-sm" onclick="window.__brs.acceptAllHigh()">
                    <i class="fa-solid fa-check-double"></i> Accept All High
                </button>
                <button class="brs-btn btn-sm" onclick="window.__brs.runAIMatching()">
                    <i class="fa-solid fa-rotate"></i> Re-run
                </button>
                <button class="brs-btn btn-sm" onclick="window.__brs.saveDoc()">
                    <i class="fa-solid fa-floppy-disk"></i> Save to ERPNext
                </button>
            </div>
        </div>

        <div class="brs-stat-grid" style="margin-bottom:14px">
            <div class="brs-stat"><div class="brs-stat-val" style="color:var(--grn)">${high}</div><div class="brs-stat-lbl">High Confidence</div></div>
            <div class="brs-stat"><div class="brs-stat-val" style="color:var(--amb)">${med}</div><div class="brs-stat-lbl">Medium Confidence</div></div>
            <div class="brs-stat"><div class="brs-stat-val" style="color:var(--red)">${unbank}</div><div class="brs-stat-lbl">Bank Only (Direct W/L)</div></div>
            <div class="brs-stat"><div class="brs-stat-val" style="color:var(--sky)">${uncash}</div><div class="brs-stat-lbl">Cashbook Only</div></div>
            <div class="brs-stat"><div class="brs-stat-val" style="color:${rate>=90?'var(--grn)':rate>=70?'var(--amb)':'var(--red)'}">${rate}%</div><div class="brs-stat-lbl">Match Rate</div></div>
            <div class="brs-stat"><div class="brs-stat-val" style="color:var(--pri2)">${this.state.accepted.size}</div><div class="brs-stat-lbl">Accepted</div></div>
        </div>

        <div class="brs-btn-row" style="margin-bottom:12px">
            <button class="brs-btn btn-sm ${this.state.filters.conf==='all'    ?'btn-primary':''}" onclick="window.__brs.setFilter('all')">All (${matches.length})</button>
            <button class="brs-btn btn-sm ${this.state.filters.conf==='high'   ?'btn-primary':''}" onclick="window.__brs.setFilter('high')">High (${high})</button>
            <button class="brs-btn btn-sm ${this.state.filters.conf==='medium' ?'btn-primary':''}" onclick="window.__brs.setFilter('medium')">Medium (${med})</button>
            <button class="brs-btn btn-sm ${this.state.filters.conf==='unmatched'?'btn-primary':''}" onclick="window.__brs.setFilter('unmatched')">Unmatched (${unbank+uncash})</button>
            <input class="brs-input" style="width:200px;padding:5px 10px;font-size:11px" placeholder="Search narration…"
                id="brs-search" value="${esc(this.state.filters.search)}"
                oninput="window.__brs.state.filters.search=this.value;window.__brs._renderMatchContent()">
        </div>

        <div id="brs-match-list" style="max-height:600px;overflow-y:auto">
            ${cardsHTML || '<div class="brs-empty"><i class="fa-solid fa-filter"></i><h4>No items match filter</h4></div>'}
        </div>`);
    }

    _applyMatchFilter(matches) {
        const f = this.state.filters;
        return matches.filter(m => {
            if (f.conf === 'high')      return m.conf === 'high'   && m.bank && m.cash;
            if (f.conf === 'medium')    return m.conf === 'medium'  && m.bank && m.cash;
            if (f.conf === 'unmatched') return !m.bank || !m.cash;
            return true;
        }).filter(m => {
            if (!f.search) return true;
            const q = f.search.toLowerCase();
            return (m.bank && (m.bank.party||'').toLowerCase().includes(q)) ||
                   (m.cash && (m.cash.party||'').toLowerCase().includes(q));
        });
    }

    _matchCard(m, i) {
        const realIdx    = this.state.matches.indexOf(m);
        const isAccepted = this.state.accepted.has(realIdx);

        if (m.bank && m.cash) {
            // ── Matched pair ─────────────────────────────────────────────────
            // Bank DR (payment) ↔ GL CR (payment)  |  Bank CR (receipt) ↔ GL DR (receipt)
            const bIsDR   = flt(m.bank.debit_amount) > 0;
            const bAmt    = bIsDR ? flt(m.bank.debit_amount) : flt(m.bank.credit_amount);
            const cIsDR   = flt(m.cash.debit_amount) > 0;
            const cAmt    = cIsDR ? flt(m.cash.debit_amount) : flt(m.cash.credit_amount);
            const bLabel  = bIsDR ? 'DR — Payment out' : 'CR — Receipt in';
            const cLabel  = cIsDR ? 'DR — Receipt in'  : 'CR — Payment out';
            const bColour = bIsDR ? 'var(--red)' : 'var(--grn)';
            const cColour = cIsDR ? 'var(--grn)' : 'var(--red)';
            return `
            <div class="brs-match-card ${m.confClass} ${isAccepted ? 'accepted' : ''}">
                <div class="brs-txn-box">
                    <div class="mn">${esc(m.bank.party || m.bank.remarks || '—')}</div>
                    <div class="md">${m.bank.posting_date} · Bank Statement</div>
                    <div class="ma" style="color:${bColour}">
                        ${fmtN(bAmt)}
                        <span class="brs-badge ${bIsDR?'bd-red':'bd-green'}">${bLabel}</span>
                    </div>
                </div>
                <div class="brs-arrow-box">
                    <i class="fa-solid fa-arrows-left-right" style="font-size:18px;color:var(--tx3)"></i><br>
                    <div class="brs-conf-score" style="color:${m.conf==='high'?'var(--grn)':m.conf==='medium'?'var(--amb)':'var(--red)'}">${m.score}%</div>
                    <div class="brs-conf-lbl">${m.conf}</div>
                </div>
                <div class="brs-txn-box">
                    <div class="mn">${esc(m.cash.party || m.cash.remarks || '—')}</div>
                    <div class="md">${m.cash.posting_date} · ${esc(m.cash.voucher_no||'Cashbook')}</div>
                    <div class="ma" style="color:${cColour}">
                        ${fmtN(cAmt)}
                        <span class="brs-badge ${cIsDR?'bd-green':'bd-red'}">${cLabel}</span>
                    </div>
                </div>
                <div class="brs-action-box">
                    ${isAccepted
                        ? `<button class="brs-btn btn-green btn-xs" disabled>
                               <i class="fa-solid fa-check"></i> Matched
                           </button>`
                        : `<button class="brs-btn btn-green btn-xs" onclick="window.__brs.acceptMatch(${realIdx})">
                               <i class="fa-solid fa-check"></i> Accept
                           </button>
                           <button class="brs-btn btn-red btn-xs" onclick="window.__brs.rejectMatch(${realIdx})">
                               <i class="fa-solid fa-xmark"></i> Reject
                           </button>`
                    }
                </div>
            </div>`;

        } else if (m.bank && !m.cash) {
            // ── Bank-only row ────────────────────────────────────────────────
            // Bank DR unmatched → Direct Withdrawal (not yet posted to GL) → create Payment
            // Bank CR unmatched → Direct Lodgment   (not yet posted to GL) → create Receipt
            const bIsDR   = flt(m.bank.debit_amount) > 0;
            const bAmt    = bIsDR ? flt(m.bank.debit_amount) : flt(m.bank.credit_amount);
            const isDW    = bIsDR;
            const catLabel= isDW
                ? 'Direct Withdrawal — Bank DR not in GL → create Payment'
                : 'Direct Lodgment — Bank CR not in GL → create Receipt';
            return `
            <div class="brs-match-card conf-low">
                <div class="brs-txn-box">
                    <div class="mn">${esc(m.bank.party || m.bank.remarks || '—')}</div>
                    <div class="md">${m.bank.posting_date} · Bank Statement</div>
                    <div class="ma" style="color:${isDW?'var(--red)':'var(--grn)'}">
                        ${fmtN(bAmt)}
                        <span class="brs-badge ${isDW?'bd-red':'bd-green'}">${isDW?'DR — Payment out':'CR — Receipt in'}</span>
                    </div>
                </div>
                <div class="brs-arrow-box">
                    <i class="fa-solid fa-question" style="font-size:18px;color:var(--amb)"></i><br>
                    <span class="brs-badge ${isDW?'bd-amber':'bd-green'}" style="margin-top:4px;font-size:9px">
                        ${isDW?'Direct W/D':'Direct Lgmt'}
                    </span>
                </div>
                <div class="brs-txn-box" style="color:var(--tx3);font-size:11px">
                    <em>${catLabel}</em>
                </div>
                <div class="brs-action-box">
                    <button class="brs-btn btn-sm btn-xs" onclick="window.__brs.manualMatchBank(${m.bank.idx})">
                        <i class="fa-solid fa-link"></i> Link
                    </button>
                </div>
            </div>`;

        } else {
            // ── Cashbook-only row ────────────────────────────────────────────
            // GL CR unmatched → Unpresented Transfer (payment in GL, not yet cleared by bank)
            // GL DR unmatched → Uncredited Transfer  (receipt in GL, not yet credited by bank)
            const cIsDR   = flt(m.cash.debit_amount) > 0;
            const cAmt    = cIsDR ? flt(m.cash.debit_amount) : flt(m.cash.credit_amount);
            const isUnp   = !cIsDR;  // GL CR = payment = Unpresented
            const catLabel= isUnp
                ? 'Unpresented Transfer — GL CR (payment) not yet cleared by bank'
                : 'Uncredited Transfer — GL DR (receipt) not yet credited by bank';
            return `
            <div class="brs-match-card conf-low">
                <div class="brs-txn-box" style="color:var(--tx3);font-size:11px">
                    <em>${catLabel}</em>
                </div>
                <div class="brs-arrow-box">
                    <i class="fa-solid fa-clock" style="font-size:18px;color:var(--amb)"></i><br>
                    <span class="brs-badge bd-amber" style="margin-top:4px;font-size:9px">
                        ${isUnp?'Unpresented':'Uncredited'}
                    </span>
                </div>
                <div class="brs-txn-box">
                    <div class="mn">${esc(m.cash.party || m.cash.remarks || '—')}</div>
                    <div class="md">${m.cash.posting_date} · ${esc(m.cash.voucher_no||'Cashbook')}</div>
                    <div class="ma" style="color:${cIsDR?'var(--grn)':'var(--red)'}">
                        ${fmtN(cAmt)}
                        <span class="brs-badge ${cIsDR?'bd-green':'bd-red'}">${cIsDR?'DR — Receipt in':'CR — Payment out'}</span>
                    </div>
                </div>
                <div class="brs-action-box">
                    <button class="brs-btn btn-sm btn-xs" onclick="window.__brs.manualMatchCash(${m.cash.idx})">
                        <i class="fa-solid fa-link"></i> Link
                    </button>
                </div>
            </div>`;
        }
    }


    setFilter(f) {
        this.state.filters.conf = f;
        this._renderMatchContent();
    }

    acceptMatch(i) {
        this.state.accepted.add(i);
        this._renderMatchContent();
    }

    rejectMatch(i) {
        this.state.accepted.delete(i);
        this.state.matches[i].conf = 'low';
        this.state.matches[i].confClass = 'conf-low';
        this.state.matches[i].score = 0;
        this.state.matches[i].cash = null;
        this._renderMatchContent();
    }

    acceptAllHigh() {
        this.state.matches.forEach((m, i) => {
            if (m.conf === 'high' && m.bank && m.cash) this.state.accepted.add(i);
        });
        frappe.show_alert({ message: this.state.accepted.size + ' high-confidence pairs accepted', indicator: 'green' });
        this._renderMatchContent();
    }

    manualMatchBank(bankIdx) {
        const cashOptions = this.state.cashRows
            .filter(c => !this.state.matches.find(m => m.cash && m.cash.idx === c.idx && m.bank))
            .map(c => {
                const amt   = flt(c.debit_amount) || flt(c.credit_amount);
                const label = flt(c.debit_amount) > 0 ? 'GL DR (Receipt in)' : 'GL CR (Payment out)';
                return `<option value="${c.idx}">[${c.posting_date}] ${esc(c.party)} — ${fmtN(amt)} ${label}</option>`;
            })
            .join('');
        const d = new frappe.ui.Dialog({
            title: 'Manual Match — Select Cashbook Entry',
            fields: [
                { fieldtype: 'HTML', fieldname: 'info',
                  options: `<p style="font-size:12px;color:#64748B">Select the cashbook entry to match with the bank transaction</p>` },
                { fieldtype: 'HTML', fieldname: 'sel',
                  options: `<select id="manual-cash-sel" style="width:100%;padding:8px;border-radius:8px;border:1px solid #CBD5E1">
                    <option value="">— Select cashbook entry —</option>
                    ${cashOptions}
                  </select>` }
            ],
            primary_action_label: 'Confirm Match',
            primary_action: () => {
                const cashIdx = parseInt(document.getElementById('manual-cash-sel').value);
                if (isNaN(cashIdx)) { frappe.show_alert({ message: 'Select a cashbook entry', indicator: 'orange' }); return; }
                const bankRow = this.state.bankRows.find(b => b.idx === bankIdx);
                const cashRow = this.state.cashRows.find(c => c.idx === cashIdx);
                const existIdx = this.state.matches.findIndex(m => m.bank && m.bank.idx === bankIdx);
                if (existIdx >= 0) {
                    this.state.matches[existIdx].cash      = cashRow;
                    this.state.matches[existIdx].score     = 100;
                    this.state.matches[existIdx].conf      = 'high';
                    this.state.matches[existIdx].confClass = 'conf-high';
                    this.state.accepted.add(existIdx);
                }
                d.hide();
                frappe.show_alert({ message: 'Manual match applied', indicator: 'green' });
                this._renderMatchContent();
            }
        });
        d.show();
    }

    manualMatchCash(cashIdx) {
        const bankOptions = this.state.bankRows
            .filter(b => !this.state.matches.find(m => m.bank && m.bank.idx === b.idx && m.cash))
            .map(b => {
                const amt   = flt(b.debit_amount) || flt(b.credit_amount);
                const label = flt(b.debit_amount) > 0 ? 'Bank DR (Payment out)' : 'Bank CR (Receipt in)';
                return `<option value="${b.idx}">[${b.posting_date}] ${esc(b.party)} — ${fmtN(amt)} ${label}</option>`;
            })
            .join('');
        const d = new frappe.ui.Dialog({
            title: 'Manual Match — Select Bank Statement Entry',
            fields: [
                { fieldtype: 'HTML', fieldname: 'sel',
                  options: `<select id="manual-bank-sel" style="width:100%;padding:8px;border-radius:8px;border:1px solid #CBD5E1">
                    <option value="">— Select bank entry —</option>
                    ${bankOptions}
                  </select>` }
            ],
            primary_action_label: 'Confirm Match',
            primary_action: () => {
                const bankIdx2 = parseInt(document.getElementById('manual-bank-sel').value);
                if (isNaN(bankIdx2)) { frappe.show_alert({ message: 'Select a bank entry', indicator: 'orange' }); return; }
                const bankRow = this.state.bankRows.find(b => b.idx === bankIdx2);
                const cashRow = this.state.cashRows.find(c => c.idx === cashIdx);
                // Remove standalone cash entry
                const cIdx = this.state.matches.findIndex(m => !m.bank && m.cash && m.cash.idx === cashIdx);
                if (cIdx >= 0) this.state.matches.splice(cIdx, 1);
                // Find bank-only and attach cash
                const bIdx = this.state.matches.findIndex(m => m.bank && m.bank.idx === bankIdx2 && !m.cash);
                if (bIdx >= 0) {
                    this.state.matches[bIdx].cash      = cashRow;
                    this.state.matches[bIdx].score     = 100;
                    this.state.matches[bIdx].conf      = 'high';
                    this.state.matches[bIdx].confClass = 'conf-high';
                    this.state.accepted.add(bIdx);
                }
                d.hide();
                frappe.show_alert({ message: 'Manual match applied', indicator: 'green' });
                this._renderMatchContent();
            }
        });
        d.show();
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW: TABLES (Unpresented / Uncredited / Direct W/L)
    // ═══════════════════════════════════════════════════════════════════════════
    renderTables() {
        const matches = this.state.matches;

        // Unpresented = cashbook GL CR unmatched (payment recorded, not yet cleared by bank)
        const unpresented = matches.filter(m => !m.bank && m.cash && flt(m.cash.credit_amount) > 0);
        // Uncredited = cashbook GL DR unmatched (receipt recorded, not yet credited by bank)
        const uncredited  = matches.filter(m => !m.bank && m.cash && flt(m.cash.debit_amount)  > 0);
        // Direct Withdrawals = bank DR unmatched (bank debited, not yet posted to GL)
        const directWD    = matches.filter(m => m.bank && !m.cash && flt(m.bank.debit_amount)  > 0);
        // Direct Lodgments = bank CR unmatched (bank credited, not yet posted to GL)
        const directLgmt  = matches.filter(m => m.bank && !m.cash && flt(m.bank.credit_amount) > 0);

        const tbl = (rows, getAmt, colour) => {
            if (!rows.length) return `<div class="brs-empty" style="padding:20px">
                <i class="fa-solid fa-check" style="color:var(--grn)"></i>
                <h4 style="font-size:12px">None</h4></div>`;
            const total = rows.reduce((s, m) => s + flt(getAmt(m)), 0);
            return `<div class="brs-tbl-wrap">
                <table class="brs-tbl">
                    <thead><tr>
                        <th>Date</th><th>Payee / Narration</th>
                        <th>Ref / Voucher</th>
                        <th style="text-align:right">Amount (₦)</th>
                        <th>Status</th>
                    </tr></thead>
                    <tbody>
                    ${rows.map(m => {
                        const row = m.bank || m.cash;
                        return `<tr>
                            <td>${row.posting_date||''}</td>
                            <td>${esc(row.party||row.remarks||'')}</td>
                            <td style="font-size:10px;color:var(--tx3)">${esc(row.voucher_no||'')}</td>
                            <td style="text-align:right;font-weight:700;color:${colour}">${fmtN(flt(getAmt(m)))}</td>
                            <td><span class="brs-badge bd-amber">Pending</span></td>
                        </tr>`;
                    }).join('')}
                    <tr style="background:var(--bg2)">
                        <td colspan="3" style="font-weight:700">Total</td>
                        <td style="text-align:right;font-weight:800;color:${colour}">${fmtN(total)}</td>
                        <td></td>
                    </tr>
                    </tbody>
                </table>
            </div>`;
        };

        this.setContent(`
        <div class="brs-section-hdr">
            <div class="brs-section-title"><i class="fa-solid fa-table-columns"></i> Reconciliation Tables</div>
            <button class="brs-btn btn-sm" onclick="window.__brs.saveDoc()">
                <i class="fa-solid fa-floppy-disk"></i> Save All to ERPNext
            </button>
        </div>

        <div class="brs-g2" style="margin-bottom:16px">
            <div class="brs-card">
                <div class="brs-section-hdr" style="margin-bottom:10px">
                    <div style="display:flex;align-items:center;gap:8px">
                        <span class="brs-badge bd-red"><i class="fa-solid fa-arrow-right-from-bracket"></i></span>
                        <span style="font-size:12px;font-weight:700;color:var(--tx1)">Unpresented Cheques / Transfers</span>
                    </div>
                    <span class="brs-badge bd-red">${unpresented.length}</span>
                </div>
                <div style="font-size:10px;color:var(--tx3);margin-bottom:8px">
                    Cashbook GL CR not yet cleared by bank — payment recorded in books, bank hasn't debited yet
                </div>
                ${tbl(unpresented, m => flt(m.cash.credit_amount), 'var(--red)')}
            </div>
            <div class="brs-card">
                <div class="brs-section-hdr" style="margin-bottom:10px">
                    <div style="display:flex;align-items:center;gap:8px">
                        <span class="brs-badge bd-sky"><i class="fa-solid fa-arrow-right-to-bracket"></i></span>
                        <span style="font-size:12px;font-weight:700;color:var(--tx1)">Uncredited Cheques / Transfers</span>
                    </div>
                    <span class="brs-badge bd-sky">${uncredited.length}</span>
                </div>
                <div style="font-size:10px;color:var(--tx3);margin-bottom:8px">
                    Cashbook GL DR not yet credited by bank — receipt recorded in books, bank hasn't credited yet
                </div>
                ${tbl(uncredited, m => flt(m.cash.debit_amount), 'var(--sky)')}
            </div>
        </div>

        <div class="brs-g2">
            <div class="brs-card">
                <div class="brs-section-hdr" style="margin-bottom:10px">
                    <div style="display:flex;align-items:center;gap:8px">
                        <span class="brs-badge bd-amber"><i class="fa-solid fa-building-columns"></i></span>
                        <span style="font-size:12px;font-weight:700;color:var(--tx1)">Direct Withdrawals</span>
                    </div>
                    <span class="brs-badge bd-amber">${directWD.length}</span>
                </div>
                <div style="font-size:10px;color:var(--tx3);margin-bottom:8px">
                    Bank DR not yet in cashbook — bank debited your account; post a <strong>Payment</strong> to the GL
                </div>
                ${tbl(directWD, m => flt(m.bank.debit_amount), 'var(--amb)')}
            </div>
            <div class="brs-card">
                <div class="brs-section-hdr" style="margin-bottom:10px">
                    <div style="display:flex;align-items:center;gap:8px">
                        <span class="brs-badge bd-green"><i class="fa-solid fa-hand-holding-dollar"></i></span>
                        <span style="font-size:12px;font-weight:700;color:var(--tx1)">Direct Lodgments</span>
                    </div>
                    <span class="brs-badge bd-green">${directLgmt.length}</span>
                </div>
                <div style="font-size:10px;color:var(--tx3);margin-bottom:8px">
                    Bank CR not yet in cashbook — bank credited your account; post a <strong>Receipt</strong> to the GL
                </div>
                ${tbl(directLgmt, m => flt(m.bank.credit_amount), 'var(--grn)')}
            </div>
        </div>`);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW: STATEMENT
    // ═══════════════════════════════════════════════════════════════════════════
    renderStatement() {
        const doc = this.state.brsDoc;
        const matches = this.state.matches;

        const bankBal   = doc ? flt(doc.bank_statement_closing_balance) : 0;
        const cashBal   = doc ? flt(doc.cashbook_closing_balance)         : 0;

        // Unpresented = cashbook GL CR unmatched — payment not yet cleared by bank
        const unpresented = matches
            .filter(m => !m.bank && m.cash && flt(m.cash.credit_amount) > 0)
            .reduce((s, m) => s + flt(m.cash.credit_amount), 0);
        // Uncredited = cashbook GL DR unmatched — receipt not yet credited by bank
        const uncredited  = matches
            .filter(m => !m.bank && m.cash && flt(m.cash.debit_amount) > 0)
            .reduce((s, m) => s + flt(m.cash.debit_amount), 0);
        // Direct Withdrawals = bank DR unmatched — not yet posted to GL
        const directWD    = matches
            .filter(m => m.bank && !m.cash && flt(m.bank.debit_amount) > 0)
            .reduce((s, m) => s + flt(m.bank.debit_amount), 0);
        // Direct Lodgments = bank CR unmatched — not yet posted to GL
        const directLgmt  = matches
            .filter(m => m.bank && !m.cash && flt(m.bank.credit_amount) > 0)
            .reduce((s, m) => s + flt(m.bank.credit_amount), 0);

        // Formula:
        // Adjusted Bank Balance =
        //   Bank Closing
        //   + Uncredited  (cashbook DR not in bank — receipts in transit)
        //   − Unpresented (cashbook CR not in bank — payments outstanding)
        //   + Direct Lodgments  (bank CR not in GL — add to GL)
        //   − Direct Withdrawals (bank DR not in GL — deduct from GL)
        const adjBank = bankBal + uncredited - unpresented + directLgmt - directWD;
        const variance = adjBank - cashBal;
        const isRecon  = Math.abs(variance) < 1;

        const now = new Date().toLocaleDateString('en-NG', { day:'2-digit', month:'long', year:'numeric' });
        const period = doc ? `${doc.from_date} to ${doc.to_date}` : '(No document loaded)';

        this.setContent(`
        <div class="brs-section-hdr">
            <div class="brs-section-title"><i class="fa-solid fa-scroll"></i> Reconciliation Statement</div>
            <div class="brs-btn-row">
                <button class="brs-btn btn-sm" onclick="window.print()"><i class="fa-solid fa-print"></i> Print</button>
                <button class="brs-btn btn-sm" onclick="window.__brs.saveDoc()"><i class="fa-solid fa-floppy-disk"></i> Save</button>
                <button class="brs-btn btn-sm ${isRecon?'btn-green':''}" disabled>
                    ${isRecon ? '<i class="fa-solid fa-circle-check"></i> FULLY RECONCILED' : '<i class="fa-solid fa-triangle-exclamation"></i> VARIANCE EXISTS'}
                </button>
            </div>
        </div>

        <div class="brs-recon-stmt">
            <div style="padding:18px 20px;background:var(--bg2);border-bottom:1px solid var(--brd);text-align:center">
                <div style="font-size:16px;font-weight:800;color:var(--tx1);margin-bottom:2px">
                    BANK RECONCILIATION STATEMENT
                </div>
                <div style="font-size:12px;color:var(--tx2)">
                    ${doc ? esc(doc.bank_account) + ' · ' : ''}Period: ${period}
                </div>
                <div style="font-size:11px;color:var(--tx3);margin-top:4px">
                    ${doc ? esc(doc.company) + ' · ' : ''}Prepared: ${now}
                </div>
            </div>
            <table>
                <tbody>
                    <tr><td style="font-weight:700;color:var(--tx1)">Balance per Bank Statement (Closing)</td>
                        <td style="text-align:right;font-weight:700">${fmtN(bankBal)}</td></tr>

                    <tr class="row-sub"><td>Add: Uncredited transfers (Cashbook GL DR not yet in bank — receipts in transit)</td>
                        <td style="text-align:right;color:var(--grn)">${fmtN(uncredited)}</td></tr>

                    <tr class="row-sub"><td>Less: Unpresented transfers (Cashbook GL CR not yet in bank — payments outstanding)</td>
                        <td style="text-align:right;color:var(--red)">(${fmtN(unpresented)})</td></tr>

                    <tr class="row-sub"><td>Add: Direct lodgments (Bank CR not yet in GL — post Receipts)</td>
                        <td style="text-align:right;color:var(--grn)">${fmtN(directLgmt)}</td></tr>

                    <tr class="row-sub"><td>Less: Direct withdrawals (Bank DR not yet in GL — post Payments)</td>
                        <td style="text-align:right;color:var(--red)">(${fmtN(directWD)})</td></tr>

                    <tr class="row-total"><td>Adjusted Bank Balance</td>
                        <td style="text-align:right">${fmtN(adjBank)}</td></tr>

                    <tr><td style="padding:14px 20px"></td><td></td></tr>

                    <tr><td style="font-weight:700;color:var(--tx1)">Balance per Cashbook / GL</td>
                        <td style="text-align:right;font-weight:700">${fmtN(cashBal)}</td></tr>

                    <tr class="${isRecon ? 'row-reconciled' : 'row-diff'} row-total">
                        <td>${isRecon ? '✓ Reconciled — Difference is NIL' : '⚠ Unexplained Variance'}</td>
                        <td style="text-align:right">${isRecon ? '₦ 0.00' : fmtN(Math.abs(variance)) + ' (' + (variance > 0 ? 'Bank > Cashbook' : 'Cashbook > Bank') + ')'}</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="brs-g2" style="margin-top:16px">
            <div class="brs-card">
                <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--tx3);margin-bottom:10px">Match Summary</div>
                <div style="font-size:12px;color:var(--tx2);line-height:2">
                    Matched pairs: <strong style="color:var(--tx1)">${matches.filter(m=>m.bank&&m.cash).length}</strong><br>
                    High confidence: <strong style="color:var(--grn)">${matches.filter(m=>m.conf==='high'&&m.bank&&m.cash).length}</strong><br>
                    Medium confidence: <strong style="color:var(--amb)">${matches.filter(m=>m.conf==='medium'&&m.bank&&m.cash).length}</strong><br>
                    Manually matched: <strong style="color:var(--sky)">${matches.filter(m=>m.score===100&&m.bank&&m.cash).length}</strong><br>
                    Unreconciled items: <strong style="color:var(--red)">${matches.filter(m=>!m.bank||!m.cash).length}</strong>
                </div>
            </div>
            <div class="brs-card">
                <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--tx3);margin-bottom:10px">Unreconciled Summary</div>
                <div style="font-size:12px;color:var(--tx2);line-height:2">
                    Unpresented cheques/TRF: <strong style="color:var(--red)">${fmtN(unpresented)}</strong><br>
                    Uncredited cheques/TRF: <strong style="color:var(--sky)">${fmtN(uncredited)}</strong><br>
                    Direct withdrawals: <strong style="color:var(--amb)">${fmtN(directWD)}</strong><br>
                    Direct lodgments: <strong style="color:var(--grn)">${fmtN(directLgmt)}</strong>
                </div>
            </div>
        </div>`);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW: CONFIG
    // ═══════════════════════════════════════════════════════════════════════════
    renderConfig() {
        const c = this.state.config;
        this.setContent(`
        <div class="brs-section-hdr">
            <div class="brs-section-title"><i class="fa-solid fa-sliders"></i> Matching Configuration</div>
            <button class="brs-btn btn-primary btn-sm" onclick="window.__brs.saveConfig()">
                <i class="fa-solid fa-floppy-disk"></i> Save & Re-run
            </button>
        </div>

        <div class="brs-g21">
            <div style="display:flex;flex-direction:column;gap:14px">
                <div class="brs-card">
                    <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--tx3);margin-bottom:14px">Tolerance Settings</div>
                    <div class="brs-setting-row">
                        <label>Date tolerance (±days)</label>
                        <input type="range" min="0" max="10" step="1" value="${c.dateTol}" id="cfg-date"
                            oninput="document.getElementById('v-date').textContent=this.value">
                        <span class="val" id="v-date">${c.dateTol}</span>
                    </div>
                    <div class="brs-setting-row">
                        <label>Name similarity threshold (%)</label>
                        <input type="range" min="40" max="100" step="5" value="${c.nameTol}" id="cfg-name"
                            oninput="document.getElementById('v-name').textContent=this.value+'%'">
                        <span class="val" id="v-name">${c.nameTol}%</span>
                    </div>
                    <div class="brs-setting-row">
                        <label>Amount tolerance (%)</label>
                        <input type="range" min="0" max="5" step="0.1" value="${c.amtTol}" id="cfg-amt"
                            oninput="document.getElementById('v-amt').textContent=parseFloat(this.value).toFixed(1)+'%'">
                        <span class="val" id="v-amt">${c.amtTol.toFixed(1)}%</span>
                    </div>
                    <div class="brs-setting-row">
                        <label>High confidence cutoff (%)</label>
                        <input type="range" min="70" max="100" step="5" value="${c.hiConf}" id="cfg-hi"
                            oninput="document.getElementById('v-hi').textContent=this.value+'%'">
                        <span class="val" id="v-hi">${c.hiConf}%</span>
                    </div>
                </div>

                <div class="brs-card">
                    <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--tx3);margin-bottom:14px">Matching Priority Cascade</div>
                    <div style="font-size:12px;line-height:2;color:var(--tx2)">
                        <span class="brs-badge bd-pri" style="margin-right:6px">Tier 1</span> Exact reference/voucher number → 100%<br>
                        <span class="brs-badge bd-green" style="margin-right:6px">Tier 2</span> Amount + exact date + partial name → 95%<br>
                        <span class="brs-badge bd-sky" style="margin-right:6px">Tier 3</span> Amount + date (±tol) + Levenshtein + Jaccard<br>
                        <span class="brs-badge bd-amber" style="margin-right:6px">Tier 4</span> Amount only + date range + token overlap<br>
                        <span class="brs-badge bd-red" style="margin-right:6px">No Match</span> → Unreconciled / Direct W/D / Lodgment
                    </div>
                </div>
            </div>

            <div style="display:flex;flex-direction:column;gap:14px">
                <div class="brs-card">
                    <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--tx3);margin-bottom:14px">Nigerian Bank Abbreviations</div>
                    <div style="font-size:11px;color:var(--tx2);line-height:1.9">
                        ${Object.entries(BRS_ABBREV).slice(0, 18).map(([k,v]) =>
                            v ? `<span style="font-family:monospace;color:var(--pri2)">${k}</span> → ${v}<br>` : ''
                        ).join('')}
                    </div>
                    <div style="font-size:10px;color:var(--tx3);margin-top:8px">
                        <i class="fa-solid fa-circle-info"></i> Stop-words removed: ${[...BRS_STOPWORDS].slice(0,8).join(', ')}…
                    </div>
                </div>

                <div class="brs-card" style="background:var(--grn_x);border-color:rgba(52,211,153,.2)">
                    <div style="font-size:11px;font-weight:700;color:var(--grn);margin-bottom:8px">
                        <i class="fa-solid fa-lightbulb"></i> How Transfer Matching Works
                    </div>
                    <div style="font-size:11px;color:var(--tx2);line-height:1.8">
                        Banks truncate names: <em>"DANGOTE CEM LTD"</em><br>
                        Cashbook has full name: <em>"Dangote Cement Company Limited"</em><br><br>
                        The engine:<br>
                        1. Removes LTD, PLC, NIGERIA etc.<br>
                        2. Expands abbreviations (CEM → CEMENT)<br>
                        3. Computes Levenshtein distance<br>
                        4. Checks token word overlap (Jaccard)<br>
                        5. Checks if one name contains the other<br>
                        6. Takes the highest score of all three<br><br>
                        A score of 70%+ qualifies as a candidate; the best-scoring cashbook entry for each bank row wins.
                    </div>
                </div>
            </div>
        </div>`);
    }

    saveConfig() {
        this.state.config.dateTol = parseInt(document.getElementById('cfg-date').value);
        this.state.config.nameTol = parseInt(document.getElementById('cfg-name').value);
        this.state.config.amtTol  = parseFloat(document.getElementById('cfg-amt').value);
        this.state.config.hiConf  = parseInt(document.getElementById('cfg-hi').value);
        if (this.state.bankRows.length && this.state.cashRows.length) {
            this.state.matches  = [];
            this.state.accepted = new Set();
            this.switchView('matching');
        } else {
            frappe.show_alert({ message: 'Configuration saved. Load data and run matching.', indicator: 'green' });
        }
    }
}

// ─── GLOBAL HELPERS ───────────────────────────────────────────────────────────
function esc(str) {
    return (str || '').toString()
        .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
        .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function flt(v) { return parseFloat(v) || 0; }

function fmtN(v) {
    return '₦' + flt(v).toLocaleString('en-NG', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// CSS animation
if (!document.getElementById('brs-fade-style')) {
    const fs = document.createElement('style');
    fs.id = 'brs-fade-style';
    fs.textContent = '@keyframes fadeIn { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }';
    document.head.appendChild(fs);
}