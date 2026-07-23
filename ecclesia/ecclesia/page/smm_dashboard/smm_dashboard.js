// Copyright (c) 2026, Value Impacts Consulting
// ecclesia/ecclesia/page/smm_dashboard/smm_dashboard.js
//
// ╔══════════════════════════════════════════════════════════════════════════╗
// ║   SOCIAL MEDIA STUDIO — World-Class SMM Desktop Application             ║
// ║   9 Themes (localStorage only) · 7 Views · Full CRUD · Live data        ║
// ╚══════════════════════════════════════════════════════════════════════════╝

// Defensive registration: create the page object if Frappe hasn't yet
frappe.pages['smm-dashboard'] = frappe.pages['smm-dashboard'] || {};
frappe.pages['smm-dashboard'].on_page_load = function (wrapper) {
    const boot = () => {
        if (typeof Chart === 'undefined') {
            const cs = document.createElement('script');
            cs.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
            cs.onload = () => new SMMStudio(wrapper);
            cs.onerror = () => frappe.msgprint({ title:'Chart.js Error', indicator:'red', message:'Failed to load Chart.js. Check internet connection.' });
            document.head.appendChild(cs);
        } else { new SMMStudio(wrapper); }
    };
    if (!document.getElementById('fa-smm')) {
        const fa = document.createElement('link');
        fa.id = 'fa-smm'; fa.rel = 'stylesheet';
        fa.href = 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css';
        fa.onload = boot; fa.onerror = boot;
        document.head.appendChild(fa);
    } else { boot(); }
};

// ═══════════════════════════════════════════════════════════════════════════
//  THEME REGISTRY — 9 Themes, pure localStorage, zero DB dependency
// ═══════════════════════════════════════════════════════════════════════════
const SMM_THEMES = {
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
            pink: '#EC4899', pink_x: 'rgba(236,72,153,.09)',
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
            pink: '#EC4899', pink_x: 'rgba(236,72,153,.09)',
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
            pink: '#EC4899', pink_x: 'rgba(236,72,153,.09)',
            banner: 'linear-gradient(135deg,#431407 0%,#C2410C 40%,#F97316 70%,#EAB308 100%)'
        }
    },
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
            pink: '#F9A8D4', pink_x: 'rgba(249,168,212,.12)',
            banner: 'linear-gradient(135deg,#020617 0%,#0F172A 50%,#1E3A5F 70%,#312E81 100%)'
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
            pink: '#EC4899', pink_x: 'rgba(236,72,153,.09)',
            banner: 'linear-gradient(135deg,#022C22 0%,#047857 40%,#059669 70%,#10B981 100%)'
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
            pink: '#EC4899', pink_x: 'rgba(236,72,153,.09)',
            banner: 'linear-gradient(135deg,#4C0519 0%,#881337 40%,#DC2626 70%,#F59E0B 100%)'
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
            pink: '#EC4899', pink_x: 'rgba(236,72,153,.09)',
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
            pink: '#F472B6', pink_x: 'rgba(244,114,182,.12)',
            banner: 'linear-gradient(135deg,#052E16 0%,#14532D 40%,#166534 70%,#22C55E 100%)'
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
            pink: '#EC4899', pink_x: 'rgba(236,72,153,.09)',
            banner: 'linear-gradient(135deg,#500724 0%,#831843 40%,#DB2777 70%,#EC4899 100%)'
        }
    }
};

const PLAT_META = {
    'Facebook':              { col: '#1877F2', bg: '#E7F0FD', icon: 'fa-brands fa-facebook-f',    abbr: 'FB',  charLimit: 63206 },
    'Instagram':             { col: '#E1306C', bg: '#FDE8F0', icon: 'fa-brands fa-instagram',      abbr: 'IG',  charLimit: 2200  },
    'Instagram Business':    { col: '#E1306C', bg: '#FDE8F0', icon: 'fa-brands fa-instagram',      abbr: 'IB',  charLimit: 2200  },
    'Twitter/X':             { col: '#14171A', bg: '#E8E8E8', icon: 'fa-brands fa-x-twitter',      abbr: 'X',   charLimit: 280   },
    'LinkedIn':              { col: '#0077B5', bg: '#E8F3FA', icon: 'fa-brands fa-linkedin-in',    abbr: 'LI',  charLimit: 3000  },
    'LinkedIn Company Page': { col: '#0077B5', bg: '#E8F3FA', icon: 'fa-brands fa-linkedin',       abbr: 'LC',  charLimit: 3000  },
    'TikTok':                { col: '#FE2C55', bg: '#FFE8EC', icon: 'fa-brands fa-tiktok',         abbr: 'TT',  charLimit: 2200  },
    'Pinterest':             { col: '#E60023', bg: '#FFE8E8', icon: 'fa-brands fa-pinterest-p',    abbr: 'PT',  charLimit: 500   },
    'YouTube':               { col: '#FF0000', bg: '#FFE8E8', icon: 'fa-brands fa-youtube',        abbr: 'YT',  charLimit: 5000  },
    'Snapchat':              { col: '#FFFC00', bg: '#FFFE8C', icon: 'fa-brands fa-snapchat',       abbr: 'SC',  charLimit: 250   },
    'WhatsApp Business':     { col: '#25D366', bg: '#E8FAF0', icon: 'fa-brands fa-whatsapp',       abbr: 'WA',  charLimit: 1024  },
    'Telegram':              { col: '#0088CC', bg: '#E3F3FC', icon: 'fa-brands fa-telegram',       abbr: 'TG',  charLimit: 4096  },
    'Threads':               { col: '#101010', bg: '#E8E8E8', icon: 'fa-brands fa-threads',        abbr: 'TH',  charLimit: 500   },
    'Bluesky':               { col: '#0085FF', bg: '#E5F2FF', icon: 'fa-solid fa-cloud',           abbr: 'BS',  charLimit: 300   },
    'Mastodon':              { col: '#6364FF', bg: '#EDEDFF', icon: 'fa-brands fa-mastodon',       abbr: 'MT',  charLimit: 500   },
    'Other':                 { col: '#64748B', bg: '#F1F5F9', icon: 'fa-solid fa-globe',           abbr: 'OT',  charLimit: 2000  },
};

function pm(p) { return PLAT_META[p] || PLAT_META['Other']; }

const STATUS_META = {
    'Draft':               { col: '#64748B', bg: '#F1F5F9', icon: 'fa-pencil'          },
    'Pending Approval':    { col: '#F59E0B', bg: '#FFFBEB', icon: 'fa-clock'           },
    'Approved':            { col: '#2563EB', bg: '#EFF6FF', icon: 'fa-check-circle'    },
    'Rejected':            { col: '#EF4444', bg: '#FEF2F2', icon: 'fa-times-circle'    },
    'Scheduled':           { col: '#8B5CF6', bg: '#F5F3FF', icon: 'fa-calendar-clock'  },
    'Publishing':          { col: '#F97316', bg: '#FFF7ED', icon: 'fa-spinner fa-spin' },
    'Published':           { col: '#10B981', bg: '#ECFDF5', icon: 'fa-check'           },
    'Partially Published': { col: '#06B6D4', bg: '#ECFEFF', icon: 'fa-adjust'          },
    'Failed':              { col: '#EF4444', bg: '#FEF2F2', icon: 'fa-exclamation-triangle' },
    'Deleted':             { col: '#94A3B8', bg: '#F8FAFC', icon: 'fa-trash'           },
};
function sm(s) { return STATUS_META[s] || STATUS_META['Draft']; }

// ─── MAIN CLASS ───────────────────────────────────────────────────────────────
class SMMStudio {
    constructor(wrapper) {
        this.wrapper   = wrapper;
        this.page      = frappe.ui.make_app_page({ parent: wrapper, title: 'Social Media Studio', single_column: true });
        this.charts    = {};
        // Restore theme from localStorage — pure client-side, no DB needed
        this.activeTheme = (() => {
            try { return localStorage.getItem('smm-studio-theme') || 'midnight'; }
            catch(e) { return 'midnight'; }
        })();
        this.state     = {
            posts:        [],
            accounts:     [],
            comments:     [],
            settings:     null,
            activeView:   'studio',
            selectedPost: null,
            calDate:      new Date(),
            filters:      { status: '', platform: '', campaign: '' },
            composeDraft: {},
        };
        this.timers    = {};
        window.__smm   = this;
        this.boot();
    }

    async boot() {
        try {
            this.injectCSS();
            this.buildShell();
            this.applyTheme(this.activeTheme);
            this.bindTopBar();
            this.startClock();
            await this.fetchAll();
            this.renderView(this.state.activeView);
            this.startAutoRefresh();
        } catch (e) {
            console.error('SMM Studio boot error:', e);
            const content = document.getElementById('smm-content');
            if (content) {
                content.innerHTML = `
                <div style="padding:40px;text-align:center;font-family:system-ui">
                    <div style="font-size:36px;margin-bottom:16px">⚠️</div>
                    <div style="font-size:18px;font-weight:700;color:#EF4444;margin-bottom:8px">SMM Studio Failed to Load</div>
                    <div style="font-size:13px;color:#64748B;margin-bottom:16px;font-family:monospace;background:#F1F5F9;padding:12px;border-radius:8px;text-align:left;max-width:600px;margin:0 auto 16px">
                        ${(e && e.message ? e.message : String(e)).substring(0, 300)}
                    </div>
                    <div style="font-size:12px;color:#94A3B8">Check the browser console (F12) for details.</div>
                    <button onclick="location.reload()" style="margin-top:16px;padding:8px 20px;background:#6366F1;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:13px;font-weight:600">
                        Reload Page
                    </button>
                </div>`;
            }
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  CSS INJECTION
    // ═══════════════════════════════════════════════════════════════════════════
    injectCSS() {
        if (document.getElementById('smm-css')) return;
        const s = document.createElement('style');
        s.id = 'smm-css';
        s.textContent = `
/* ═══════════════════════════════════════════════════════════
   SOCIAL MEDIA STUDIO — Value Impacts / Ecclesia
   Craft-quality design  •  100% functional CRUD  •  Live data
═══════════════════════════════════════════════════════════ */
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700;800&family=Space+Mono:wght@400;700&display=swap');

/* CSS variables are set dynamically by applyTheme() from SMM_THEMES.
   Fallback midnight values ensure the page renders before JS runs. */
#smm-root {
  --bg:      #0F172A;
  --bg2:     #1E293B;
  --bg3:     #334155;
  --card:    #1E293B;
  --brd:     rgba(255,255,255,.08);
  --brd2:    rgba(255,255,255,.14);
  --tx1:     #F1F5F9;
  --tx2:     #94A3B8;
  --tx3:     #475569;
  --pri:     #818CF8;
  --pri_d:   #6366F1;
  --pri2:    #A5B4FC;
  --pri_x:   rgba(129,140,248,.12);
  --acc:     #A5B4FC;
  --acc_x:   rgba(165,180,252,.12);
  --grn:     #34D399;
  --grn_x:   rgba(52,211,153,.12);
  --red:     #F87171;
  --red_x:   rgba(248,113,113,.12);
  --amb:     #FCD34D;
  --amb_x:   rgba(252,211,77,.12);
  --sky:     #38BDF8;
  --sky_x:   rgba(56,189,248,.12);
  --pink:    #F9A8D4;
  --pink_x:  rgba(249,168,212,.12);
  font-family: 'DM Sans', system-ui, sans-serif;
  background: var(--bg);
  color: var(--tx1);
  min-height: 100vh;
  transition: background 0.3s ease, color 0.3s ease;
}

#smm-root.dark-mode input,
#smm-root.dark-mode select,
#smm-root.dark-mode textarea {
  color-scheme: dark;
}

#smm-root * { box-sizing: border-box; }

/* ── TOPBAR ── */
.smm-topbar {
  position: sticky; top: 0; z-index: 100;
  background: var(--card); opacity: 0.97;
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--brd);
  display: flex; align-items: center; gap: 0;
  height: 56px; padding: 0 24px;
}
.smm-logo {
  display: flex; align-items: center; gap: 10px;
  font-family: 'Space Mono', monospace; font-size: 14px; font-weight: 700;
  color: var(--tx1); letter-spacing: -.5px; margin-right: 28px;
}
.smm-logo-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--pri); animation: smm-pulse 2s infinite; }
@keyframes smm-pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.5;transform:scale(1.4)} }

.smm-nav { display: flex; align-items: center; gap: 2px; flex: 1; }
.smm-nav-btn {
  display: flex; align-items: center; gap: 7px;
  padding: 6px 14px; border-radius: 8px;
  font-size: 12px; font-weight: 600; color: var(--tx2);
  cursor: pointer; transition: all .15s; border: none; background: none;
  white-space: nowrap; font-family: inherit;
}
.smm-nav-btn:hover    { color: var(--tx1); background: var(--bg3); }
.smm-nav-btn.active   { color: var(--pri2); background: var(--pri_x); }
.smm-nav-badge {
  background: var(--red); color: #fff;
  font-size: 9px; font-weight: 800;
  padding: 1px 5px; border-radius: 10px; min-width: 16px; text-align: center;
}

.smm-topbar-right { display: flex; align-items: center; gap: 10px; margin-left: auto; }
.smm-clock { font-family: 'Space Mono', monospace; font-size: 11px; color: var(--tx3); }
.smm-theme-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 5px 11px; border-radius: 8px; font-size: 11px; font-weight: 600;
  color: var(--tx2); background: var(--bg3); border: 1px solid var(--brd2);
  cursor: pointer; transition: all 0.15s ease; font-family: inherit; white-space: nowrap;
}
.smm-theme-btn:hover { background: var(--pri_x); color: var(--pri2); border-color: var(--pri); }
.smm-sync-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--grn); animation: smm-pulse 3s infinite; }

/* ── COMPOSE BUTTON (Floating) ── */
.smm-fab {
  position: fixed; bottom: 28px; right: 28px; z-index: 200;
  width: 52px; height: 52px; border-radius: 50%;
  background: linear-gradient(135deg, var(--pri), var(--acc));
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; color: #fff; cursor: pointer;
  box-shadow: 0 8px 30px rgba(99,102,241,.5);
  transition: all .2s; border: none;
}
.smm-fab:hover { transform: scale(1.1) rotate(45deg); box-shadow: 0 12px 40px rgba(99,102,241,.7); }

/* ── CONTENT AREA ── */
.smm-content { padding: 24px; max-width: 1600px; margin: 0 auto; }

/* ── KPI ROW ── */
.smm-kpis { display: grid; grid-template-columns: repeat(auto-fit,minmax(160px,1fr)); gap: 14px; margin-bottom: 22px; }
.smm-kpi {
  background: var(--card); border: 1px solid var(--brd);
  border-radius: 14px; padding: 18px 20px;
  cursor: pointer; transition: all .2s; position: relative; overflow: hidden;
}
.smm-kpi::after { content:''; position:absolute; top:0; left:0; right:0; height:2px; background:var(--kc,var(--pri)); }
.smm-kpi:hover { transform: translateY(-2px); border-color: var(--brd2); background: var(--bg3); }
.smm-kpi-icon { font-size: 18px; margin-bottom: 10px; }
.smm-kpi-lbl  { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .8px; color: var(--tx3); margin-bottom: 6px; }
.smm-kpi-val  { font-size: 28px; font-weight: 800; color: var(--tx1); line-height: 1; margin-bottom: 3px; }
.smm-kpi-sub  { font-size: 11px; color: var(--tx3); }

/* ── LAYOUT GRIDS ── */
.smm-g2  { display: grid; grid-template-columns: 1fr 1fr;     gap: 16px; margin-bottom: 16px; }
.smm-g3  { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin-bottom: 16px; }
.smm-g21 { display: grid; grid-template-columns: 2fr 1fr;     gap: 16px; margin-bottom: 16px; }
.smm-g31 { display: grid; grid-template-columns: 3fr 1fr;     gap: 16px; margin-bottom: 16px; }
.smm-row { margin-bottom: 16px; }

/* ── CARD ── */
.smm-card {
  background: var(--card); border: 1px solid var(--brd);
  border-radius: 16px; overflow: hidden;
  transition: box-shadow .2s;
}
.smm-card:hover { box-shadow: 0 4px 30px rgba(0,0,0,.3); border-color: var(--brd2); }
.smm-card-head {
  padding: 14px 20px; border-bottom: 1px solid var(--brd);
  display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;
}
.smm-card-title { display: flex; align-items: center; gap: 10px; font-size: 13px; font-weight: 700; color: var(--tx1); }
.smm-title-icon { width: 28px; height: 28px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 13px; }
.smm-card-body  { padding: 18px 20px; }

/* ── FORM FIELDS ── */
.smm-form { display: flex; flex-direction: column; gap: 14px; }
.smm-fg { display: flex; flex-direction: column; gap: 5px; }
.smm-fg label {
  font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .8px; color: var(--tx3);
}
.smm-fg label span.req { color: var(--red); margin-left: 2px; }
.smm-inp, .smm-sel, .smm-ta {
  background: var(--bg3); border: 1.5px solid var(--brd2); border-radius: 10px;
  color: var(--tx1); font-family: 'DM Sans', system-ui, sans-serif;
  font-size: 13px; padding: 10px 14px;
  transition: border-color .15s, box-shadow .15s; outline: none; width: 100%;
}
.smm-inp::placeholder, .smm-ta::placeholder { color: var(--tx3); }
.smm-inp:focus, .smm-sel:focus, .smm-ta:focus {
  border-color: var(--pri); box-shadow: 0 0 0 3px rgba(99,102,241,.2);
}
.smm-sel { cursor: pointer; }
.smm-sel option { background: var(--bg2); color: var(--tx1); }
.smm-ta { resize: vertical; min-height: 80px; line-height: 1.5; }
.smm-fg-row { display: flex; gap: 12px; }
.smm-fg-row .smm-fg { flex: 1; }
.smm-check-row { display: flex; align-items: center; gap: 8px; }
.smm-check-row input[type=checkbox] { width: 16px; height: 16px; accent-color: var(--pri); }
.smm-check-row label { font-size: 12px; color: var(--tx2); font-weight: 500; }

/* ── BUTTONS ── */
.smm-btns { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.smm-btn {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 8px 16px; border-radius: 10px;
  font-size: 12px; font-weight: 700; cursor: pointer;
  border: 1.5px solid transparent;
  font-family: 'DM Sans', system-ui, sans-serif;
  transition: all .15s; line-height: 1.3; text-decoration: none !important;
}
.smm-btn:hover { transform: translateY(-1px); }
.btn-primary { background: var(--pri); color: #fff; border-color: var(--pri); box-shadow: 0 4px 14px rgba(99,102,241,.4); }
.btn-primary:hover { background: var(--pri2); box-shadow: 0 6px 20px rgba(99,102,241,.5); }
.btn-accent  { background: var(--acc); color: #fff; border-color: var(--acc); box-shadow: 0 4px 14px rgba(244,114,182,.3); }
.btn-ghost   { background: transparent; color: var(--tx2); border-color: var(--brd2); }
.btn-ghost:hover  { background: var(--bg3); color: var(--tx1); border-color: var(--pri); }
.btn-grn     { background: var(--grn_x); color: var(--grn); border-color: rgba(52,211,153,.25); }
.btn-grn:hover    { background: var(--grn); color: #fff; }
.btn-red     { background: var(--red_x); color: var(--red); border-color: rgba(248,113,113,.25); }
.btn-red:hover    { background: var(--red); color: #fff; }
.btn-amb     { background: var(--amb_x); color: var(--amb); border-color: rgba(251,191,36,.25); }
.btn-amb:hover    { background: var(--amb); color: #fff; }
.btn-sky     { background: var(--sky_x); color: var(--sky); border-color: rgba(56,189,248,.25); }
.btn-sky:hover    { background: var(--sky); color: #fff; }
.btn-sm      { padding: 5px 11px; font-size: 11px; }
.btn-xs      { padding: 3px 8px; font-size: 10px; border-radius: 7px; }

/* ── BADGES ── */
.smm-badge {
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

/* ── PLATFORM CHIP ── */
.plat-chip {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 3px 9px; border-radius: 20px; font-size: 10px; font-weight: 700;
}

/* ── POST CARD ── */
.smm-post-card {
  background: var(--bg3); border: 1px solid var(--brd);
  border-radius: 14px; padding: 14px 16px;
  cursor: pointer; transition: all .18s; position: relative;
}
.smm-post-card:hover { border-color: var(--pri); background: rgba(99,102,241,.06); transform: translateY(-1px); }
.smm-post-card-title { font-size: 13px; font-weight: 700; color: var(--tx1); margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.smm-post-card-excerpt { font-size: 11px; color: var(--tx2); line-height: 1.5; max-height: 42px; overflow: hidden; margin-bottom: 10px; }
.smm-post-card-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.smm-post-metrics { display: grid; grid-template-columns: repeat(4,1fr); gap: 8px; margin-top: 10px; }
.smm-post-metric { text-align: center; background: var(--bg2); border-radius: 8px; padding: 6px 4px; }
.smm-post-metric-val { font-size: 14px; font-weight: 800; color: var(--tx1); }
.smm-post-metric-lbl { font-size: 9px; color: var(--tx3); text-transform: uppercase; letter-spacing: .4px; }

/* ── TABLE ── */
.smm-tbl-wrap { overflow-x: auto; max-height: 480px; overflow-y: auto;
  scrollbar-width: thin; scrollbar-color: var(--brd2) transparent; }
.smm-tbl { width: 100%; border-collapse: collapse; font-size: 12px; }
.smm-tbl thead th {
  padding: 10px 14px; text-align: left;
  font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .5px; color: var(--tx3);
  background: var(--bg2); border-bottom: 1px solid var(--brd2);
  position: sticky; top: 0; z-index: 2; white-space: nowrap;
}
.smm-tbl tbody td { padding: 10px 14px; border-bottom: 1px solid var(--brd); color: var(--tx2); }
.smm-tbl tbody tr { cursor: pointer; transition: background .1s; }
.smm-tbl tbody tr:hover { background: rgba(99,102,241,.06); }
.smm-tbl tbody tr:hover td { color: var(--tx1); }
.smm-tbl tbody tr:last-child td { border-bottom: none; }

/* ── PROGRESS BAR ── */
.smm-bar-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.smm-bar-lbl { font-size: 11px; color: var(--tx2); width: 140px; flex-shrink: 0; display: flex; align-items: center; gap: 6px; }
.smm-bar     { flex: 1; height: 5px; background: var(--brd2); border-radius: 40px; overflow: hidden; }
.smm-bar-fill { height: 100%; border-radius: 40px; transition: width .7s cubic-bezier(.4,0,.2,1); }
.smm-bar-val { font-size: 11px; font-family: 'Space Mono', monospace; font-weight: 700; width: 44px; text-align: right; color: var(--tx1); }

/* ── CALENDAR ── */
.smm-cal { width: 100%; }
.smm-cal-grid { display: grid; grid-template-columns: repeat(7,1fr); gap: 4px; }
.smm-cal-day-name { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; color: var(--tx3); text-align: center; padding: 6px 0; }
.smm-cal-cell {
  min-height: 90px; background: var(--bg3); border-radius: 10px;
  border: 1px solid var(--brd); padding: 7px; cursor: pointer;
  transition: all .15s;
}
.smm-cal-cell:hover { border-color: var(--pri); background: rgba(99,102,241,.06); }
.smm-cal-cell.today { border-color: var(--pri); border-width: 2px; }
.smm-cal-cell.other-month { opacity: .3; }
.smm-cal-num { font-size: 11px; font-weight: 700; color: var(--tx2); margin-bottom: 4px; }
.smm-cal-pill {
  font-size: 9px; padding: 1px 6px; border-radius: 4px;
  color: #fff; margin-bottom: 2px; white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis; cursor: pointer;
}

/* ── COMMENT ── */
.smm-comment {
  padding: 14px 18px; border-bottom: 1px solid var(--brd);
  display: flex; align-items: flex-start; gap: 12px;
  cursor: pointer; transition: background .12s;
}
.smm-comment:hover { background: rgba(99,102,241,.05); }
.smm-comment:last-child { border-bottom: none; }
.smm-avatar { width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; color: #fff; flex-shrink: 0; }
.smm-comment-body { flex: 1; min-width: 0; }
.smm-comment-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 4px; }
.smm-comment-author { font-size: 12px; font-weight: 700; color: var(--tx1); }
.smm-comment-time   { font-size: 10px; color: var(--tx3); }
.smm-comment-text   { font-size: 12px; color: var(--tx2); line-height: 1.5; margin-bottom: 6px; }
.smm-comment-reply-box { background: var(--bg2); border-radius: 8px; padding: 8px 10px; margin-top: 6px; border: 1px solid var(--brd2); }

/* ── COMPOSE PANEL ── */
.smm-compose {
  display: grid; grid-template-columns: 1fr 340px; gap: 16px; align-items: start;
}
.smm-compose-main { background: var(--card); border: 1px solid var(--brd); border-radius: 16px; overflow: hidden; }
.smm-compose-sidebar { display: flex; flex-direction: column; gap: 14px; }
.smm-char-bar { height: 3px; border-radius: 10px; background: var(--brd2); margin-top: 4px; overflow: hidden; }
.smm-char-fill { height: 100%; border-radius: 10px; transition: width .2s, background .2s; }

/* ── PLATFORM TOGGLE ROW ── */
.smm-plat-toggles { display: flex; flex-wrap: wrap; gap: 8px; padding: 14px 20px; border-bottom: 1px solid var(--brd); }
.smm-plat-toggle {
  display: flex; align-items: center; gap: 7px;
  padding: 7px 12px; border-radius: 10px;
  border: 1.5px solid var(--brd2); cursor: pointer;
  transition: all .15s; font-size: 12px; font-weight: 600;
  color: var(--tx2); background: var(--bg3);
}
.smm-plat-toggle.on { border-color: var(--pri); background: var(--pri_x); color: var(--pri2); }
.smm-plat-toggle:hover { border-color: var(--brd); }

/* ── ACCOUNT CARD ── */
.smm-account-card {
  background: var(--bg3); border: 1px solid var(--brd);
  border-radius: 14px; padding: 16px; cursor: pointer;
  transition: all .18s;
}
.smm-account-card:hover { border-color: var(--pri); transform: translateY(-2px); box-shadow: 0 6px 24px rgba(0,0,0,.3); }
.smm-account-avatar { width: 42px; height: 42px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 18px; color: #fff; margin-bottom: 12px; }
.smm-account-name { font-size: 14px; font-weight: 700; color: var(--tx1); margin-bottom: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.smm-account-sub  { font-size: 11px; color: var(--tx3); margin-bottom: 10px; }

/* ── AI CARD ── */
.smm-ai-card { background: var(--pri_x); border: 1px solid rgba(99,102,241,.2); border-radius: 12px; padding: 14px 16px; margin-bottom: 12px; }
.smm-ai-card h4 { font-size: 11px; font-weight: 700; color: var(--pri2); margin: 0 0 8px; letter-spacing: .3px; }
.smm-ai-item { display: flex; gap: 7px; font-size: 11px; color: var(--tx1); margin-bottom: 5px; line-height: 1.4; }
.smm-ai-item:last-child { margin-bottom: 0; }
.smm-ai-dot  { width: 5px; height: 5px; border-radius: 50%; background: var(--pri2); margin-top: 4px; flex-shrink: 0; }

/* ── SENTIMENT RING ── */
.smm-ring-wrap { position: relative; flex-shrink: 0; }
.smm-ring-wrap svg { display: block; }
.smm-ring-label { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.smm-ring-pct  { font-size: 16px; font-weight: 800; color: var(--tx1); }
.smm-ring-sub  { font-size: 9px; color: var(--tx3); }

/* ── STAT GRID ── */
.smm-stat-grid { display: grid; grid-template-columns: repeat(auto-fit,minmax(100px,1fr)); gap: 10px; }
.smm-stat { background: var(--bg2); border-radius: 10px; padding: 10px; text-align: center; }
.smm-stat-val { font-size: 18px; font-weight: 800; color: var(--tx1); }
.smm-stat-lbl { font-size: 9px; text-transform: uppercase; letter-spacing: .5px; color: var(--tx3); }

/* ── ALERTS ── */
.smm-alerts { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 18px; }
.smm-alert {
  display: flex; align-items: center; gap: 7px; padding: 7px 13px;
  border-radius: 9px; font-size: 11px; font-weight: 600; cursor: pointer;
  transition: all .15s; text-decoration: none !important;
}
.smm-alert:hover { transform: translateY(-1px); }
.al-red  { background: var(--red_x); border: 1px solid rgba(248,113,113,.2); color: var(--red); }
.al-amb  { background: var(--amb_x); border: 1px solid rgba(251,191,36,.2);  color: var(--amb); }
.al-pri  { background: var(--pri_x); border: 1px solid rgba(99,102,241,.2);  color: var(--pri2); }
.al-grn  { background: var(--grn_x); border: 1px solid rgba(52,211,153,.2);  color: var(--grn); }
.al-acc  { background: var(--acc_x); border: 1px solid rgba(244,114,182,.2); color: var(--acc); }

/* ── INLINE EDIT ── */
.smm-inline-edit {
  background: var(--bg2); border: 1px solid var(--brd);
  border-radius: 12px; padding: 16px;
}
.smm-inline-edit h4 { font-size: 12px; font-weight: 700; color: var(--tx1); margin: 0 0 12px; }

/* ── SETTINGS PANEL ── */
.smm-settings-section { margin-bottom: 24px; }
.smm-settings-section h3 { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .8px; color: var(--tx3); margin: 0 0 14px; padding-bottom: 8px; border-bottom: 1px solid var(--brd); }
.smm-toggle-row { display: flex; align-items: center; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid var(--brd); }
.smm-toggle-row:last-child { border-bottom: none; }
.smm-toggle-info h5 { font-size: 13px; font-weight: 600; color: var(--tx1); margin: 0 0 2px; }
.smm-toggle-info p  { font-size: 11px; color: var(--tx3); margin: 0; }
.smm-toggle {
  position: relative; width: 38px; height: 20px; cursor: pointer;
}
.smm-toggle input { opacity: 0; width: 0; height: 0; position: absolute; }
.smm-toggle-track {
  position: absolute; inset: 0; background: var(--brd2);
  border-radius: 20px; transition: background .2s;
}
.smm-toggle input:checked + .smm-toggle-track { background: var(--pri); }
.smm-toggle-thumb {
  position: absolute; top: 2px; left: 2px;
  width: 16px; height: 16px; border-radius: 50%;
  background: #fff; transition: transform .2s;
}
.smm-toggle input:checked ~ .smm-toggle-thumb { transform: translateX(18px); }

/* ── EMPTY STATE ── */
.smm-empty {
  text-align: center; padding: 48px 24px; color: var(--tx3);
}
.smm-empty-icon { font-size: 36px; margin-bottom: 12px; }
.smm-empty h4 { font-size: 14px; font-weight: 700; color: var(--tx2); margin: 0 0 6px; }
.smm-empty p  { font-size: 12px; margin: 0 0 16px; }

/* ── LOADER ── */
.smm-loader {
  position: fixed; inset: 0; background: rgba(12,15,26,.85);
  display: flex; align-items: center; justify-content: center; flex-direction: column; gap: 16px; z-index: 999;
}
.smm-spinner {
  width: 40px; height: 40px; border: 3px solid var(--brd2);
  border-top-color: var(--pri); border-radius: 50%;
  animation: smm-spin .7s linear infinite;
}
@keyframes smm-spin { to { transform: rotate(360deg); } }

/* ── SECTION DIVIDER ── */
.smm-divider { border: none; border-top: 1px solid var(--brd); margin: 20px 0; }

/* ── RESPONSIVE ── */
@media(max-width:1100px) { .smm-g21,.smm-g31,.smm-compose { grid-template-columns: 1fr; } }
@media(max-width:800px)  { .smm-g2,.smm-g3 { grid-template-columns: 1fr; } }
@media print { .smm-topbar,.smm-fab,.smm-btns { display: none !important; } }
        `;
        document.head.appendChild(s);
    }


    // ═══════════════════════════════════════════════════════════════════════════
    //  THEME ENGINE — Pure localStorage, zero API calls, instant switching
    // ═══════════════════════════════════════════════════════════════════════════
    applyTheme(key) {
        const theme = SMM_THEMES[key] || SMM_THEMES['midnight'];
        this.activeTheme = key;

        // Persist to localStorage only — no Frappe DB involved
        try { localStorage.setItem('smm-studio-theme', key); }
        catch(e) { console.warn('localStorage unavailable'); }

        // Apply CSS custom properties to #smm-root
        const root = document.getElementById('smm-root');
        if (!root) return; // Shell not built yet — boot() calls again after buildShell
        Object.entries(theme.colors).forEach(([k, v]) => {
            root.style.setProperty('--' + k, v);
        });

        // Dark mode body class controls color-scheme for form inputs
        if (theme.isDark) root.classList.add('dark-mode');
        else              root.classList.remove('dark-mode');

        // Update theme label in header
        const label = document.getElementById('smm-theme-label');
        if (label) label.innerHTML = theme.icon + ' ' + theme.name;

        // Repaint existing charts with new palette
        this.updateChartColors(theme);
    }

    updateChartColors(theme) {
        const c = theme.colors;
        Object.values(this.charts).forEach(chart => {
            if (!chart || !chart.options) return;
            try {
                if (chart.options.scales) {
                    Object.values(chart.options.scales).forEach(scale => {
                        if (scale.grid)  scale.grid.color  = c.brd;
                        if (scale.ticks) scale.ticks.color = c.tx3;
                    });
                }
                if (chart.options.plugins?.legend?.labels) {
                    chart.options.plugins.legend.labels.color = c.tx2;
                }
                chart.update();
            } catch(e) { /* chart may not be mounted yet */ }
        });
    }

    openThemePicker() {
        const cur = this.activeTheme;
        const cardsHTML = Object.entries(SMM_THEMES).map(([key, theme]) => {
            const isActive = key === cur;
            const dots = ['pri','acc','grn','sky','pink']
                .map(k => `<div style="width:11px;height:11px;border-radius:3px;background:${theme.colors[k]}"></div>`)
                .join('');
            return `
            <div onclick="window.__smm.applyTheme('${key}');if(window.__smm_td)window.__smm_td.hide();"
                 style="display:flex;align-items:center;gap:12px;padding:14px 16px;border-radius:12px;
                        border:2px solid ${isActive ? theme.colors.pri : theme.colors.brd2};
                        background:${theme.colors.card};cursor:pointer;transition:all .18s;color:${theme.colors.tx1}">
                <div style="font-size:24px;width:40px;height:40px;border-radius:10px;
                            background:${theme.colors.pri_x};display:flex;align-items:center;justify-content:center;flex-shrink:0">
                    ${theme.icon}
                </div>
                <div style="flex:1;min-width:0">
                    <div style="font-size:13px;font-weight:700;margin-bottom:4px">${theme.name}</div>
                    <div style="display:flex;gap:4px;margin-bottom:4px">${dots}</div>
                    <div style="font-size:10px;color:${theme.colors.tx3}">${theme.isDark ? '🌙 Dark' : '☀️ Light'} · localStorage only</div>
                </div>
                ${isActive ? `<span style="font-size:18px;color:${theme.colors.pri};flex-shrink:0">✓</span>` : ''}
            </div>`;
        }).join('');

        const d = new frappe.ui.Dialog({
            title: '🎨 Studio Theme',
            size: 'large',
            fields: [{
                fieldtype: 'HTML', fieldname: 'themes',
                options: `
                <p style="font-size:12px;color:var(--tx3);margin:0 0 14px">
                    Themes are stored in your browser only — no database writes. Changes apply instantly.
                </p>
                <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">
                    ${cardsHTML}
                </div>`
            }]
        });
        window.__smm_td = d;
        d.show();
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  SHELL LAYOUT
    // ═══════════════════════════════════════════════════════════════════════════
    buildShell() {
        $(this.page.main).empty();
        this.$root = $(`
            <div id="smm-root">
                <div class="smm-topbar">
                    <div class="smm-logo">
                        <div class="smm-logo-dot"></div>
                        SMM Studio
                    </div>
                    <nav class="smm-nav" id="smm-nav"></nav>
                    <div class="smm-topbar-right">
                        <button class="smm-theme-btn" onclick="window.__smm.openThemePicker()" title="Change Theme">
                            <i class="fa-solid fa-palette" style="font-size:11px"></i>
                            <span id="smm-theme-label">🌙 Midnight</span>
                        </button>
                        <div class="smm-sync-dot" title="Auto-refreshing every 30s"></div>
                        <div class="smm-clock" id="smm-clock"></div>
                    </div>
                </div>

                <div class="smm-content" id="smm-content">
                    <div class="smm-loader" id="smm-loader">
                        <div class="smm-spinner"></div>
                        <div style="font-weight:600;font-size:14px;color:var(--tx1)">Loading Social Media Studio</div>
                        <div style="font-size:12px;color:var(--tx3)">Fetching posts, accounts, settings & analytics…</div>
                    </div>
                </div>

                <button class="smm-fab" id="smm-fab" title="New Post" onclick="window.__smm.openCompose()">
                    <i class="fa-solid fa-plus"></i>
                </button>
            </div>
        `).appendTo(this.page.main);

        this.buildNav();
    }

    buildNav() {
        const views = [
            { id:'studio',    icon:'fa-solid fa-layer-group',  label:'Studio'     },
            { id:'compose',   icon:'fa-solid fa-pen-nib',       label:'Compose'    },
            { id:'calendar',  icon:'fa-solid fa-calendar-days', label:'Calendar'   },
            { id:'inbox',     icon:'fa-solid fa-inbox',         label:'Inbox',     badge:'inbox'  },
            { id:'analytics', icon:'fa-solid fa-chart-line',    label:'Analytics'  },
            { id:'accounts',  icon:'fa-solid fa-plug',          label:'Platforms'  },
            { id:'settings',  icon:'fa-solid fa-gear',          label:'Settings'   },
        ];
        const nav = views.map(v => `
            <button class="smm-nav-btn ${v.id===this.state.activeView?'active':''}" data-view="${v.id}">
                <i class="${v.icon}"></i> ${v.label}
                ${v.badge ? `<span class="smm-nav-badge" id="smm-badge-${v.badge}" style="display:none">0</span>` : ''}
            </button>
        `).join('');
        $('#smm-nav').html(nav);
    }

    bindTopBar() {
        $(document).on('click', '.smm-nav-btn', (e) => {
            const view = $(e.currentTarget).data('view');
            this.switchView(view);
        });
    }

    switchView(view) {
        this.state.activeView = view;
        // Update nav active state
        $('.smm-nav-btn').removeClass('active');
        $(`.smm-nav-btn[data-view="${view}"]`).addClass('active');
        this.renderView(view);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  DATA FETCHING
    // ═══════════════════════════════════════════════════════════════════════════
    async fetchAll(silent = false) {
        if (!silent) {
            const loader = document.getElementById('smm-loader');
            if (loader) loader.style.display = '';
        }
        try {
            // Fetch posts — wrapped individually so one failure doesn't kill all
            let postsMsg = [];
            try {
                const postsR = await frappe.call({
                    method: 'frappe.client.get_list',
                    args: {
                        doctype: 'Social Post',
                        fields: [
                            'name','post_title','content','content_type','status',
                            'campaign','publish_strategy','global_schedule',
                            'requires_approval','approved_by','approval_date',
                            'total_likes','total_comments','total_shares','total_reach',
                            'total_engagement_rate','total_views','total_clicks',
                            'total_conversions','revenue_generated','roi_percentage',
                            'primary_hashtags','mentions','location','link_url',
                            'ai_recommendations','creation','modified'
                        ],
                        limit_page_length: 500,
                        order_by: 'modified desc'
                    }
                });
                postsMsg = postsR.message || [];
            } catch(e) { console.warn('Posts fetch failed:', e.message); }

            // Fetch settings — may not exist yet, that's OK
            let settingsMsg = null;
            try {
                const settingsR = await frappe.call({
                    method: 'frappe.client.get',
                    args: { doctype: 'Social Media Settings', name: 'Social Media Settings' }
                });
                settingsMsg = settingsR.message || null;
            } catch(e) { console.warn('Settings not found (may need setup):', e.message); }

            // Fetch comments — child table, get_list works
            let commentsMsg = [];
            try {
                const commentsR = await frappe.call({
                    method: 'frappe.client.get_list',
                    args: {
                        doctype: 'Social Post Comment',
                        fields: ['name','parent','platform','author_name','comment_text',
                                 'comment_time','sentiment_label','sentiment_score','status',
                                 'is_flagged','reply_text','reply_status','like_count'],
                        limit_page_length: 200,
                        order_by: 'comment_time desc'
                    }
                });
                commentsMsg = commentsR.message || [];
            } catch(e) { console.warn('Comments fetch failed:', e.message); }

            this.state.posts    = postsMsg;
            this.state.settings = settingsMsg;
            this.state.accounts = settingsMsg?.platform_accounts || [];
            this.state.comments = commentsMsg;

            this.updateBadges();
        } catch(e) {
            console.error('SMM fetchAll unexpected error:', e);
        } finally {
            const loader = document.getElementById('smm-loader');
            if (loader) loader.style.display = 'none';
        }
    }

    updateBadges() {
        const unanswered = this.state.comments.filter(c => c.status === 'New').length;
        $('#smm-badge-inbox').text(unanswered).toggle(unanswered > 0);
    }

    startClock() {
        const tick = () => {
            $('#smm-clock').text(new Date().toLocaleTimeString('en-NG', { hour12: true }));
        };
        tick(); setInterval(tick, 1000);
    }

    startAutoRefresh() {
        this.timers.refresh = setInterval(() => this.fetchAll(true).then(() => {
            if (this.state.activeView) this.renderView(this.state.activeView);
        }), 30000);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW DISPATCH
    // ═══════════════════════════════════════════════════════════════════════════
    renderView(name) {
        const map = {
            studio:    () => this.renderStudio(),
            compose:   () => this.renderCompose(),
            calendar:  () => this.renderCalendar(),
            inbox:     () => this.renderInbox(),
            analytics: () => this.renderAnalytics(),
            accounts:  () => this.renderAccounts(),
            settings:  () => this.renderSettings(),
        };
        if (!map[name]) { console.warn('Unknown view:', name); return; }
        try {
            map[name]();
        } catch(e) {
            console.error('renderView error in "' + name + '":', e);
            this.setContent(`
            <div style="padding:32px;text-align:center">
                <div style="font-size:28px;margin-bottom:12px">⚠️</div>
                <div style="font-size:14px;font-weight:700;color:var(--red);margin-bottom:8px">
                    Error rendering ${name} view
                </div>
                <div style="font-size:12px;color:var(--tx3);font-family:monospace;background:var(--bg2);
                            padding:10px;border-radius:8px;text-align:left;margin-bottom:14px">
                    ${esc(e && e.message ? e.message : String(e))}
                </div>
                <button class="smm-btn btn-primary btn-sm" onclick="window.__smm.switchView('studio')">
                    ← Back to Studio
                </button>
            </div>`);
        }
    }

    setContent(html) { $('#smm-content').html(html); }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW: STUDIO (Command Centre Overview)
    // ═══════════════════════════════════════════════════════════════════════════
    renderStudio() {
        const p = this.state.posts;
        const totalReach   = p.reduce((s,x) => s + flt(x.total_reach), 0);
        const totalEngage  = p.reduce((s,x) => s + flt(x.total_likes) + flt(x.total_comments) + flt(x.total_shares), 0);
        const published    = p.filter(x => x.status === 'Published').length;
        const scheduled    = p.filter(x => x.status === 'Scheduled').length;
        const failed       = p.filter(x => x.status === 'Failed').length;
        const pending      = p.filter(x => x.status === 'Pending Approval').length;
        const avgEng       = p.filter(x => x.total_engagement_rate > 0);
        const avgEngRate   = avgEng.length ? (avgEng.reduce((s,x) => s+flt(x.total_engagement_rate), 0)/avgEng.length).toFixed(1) : '0';

        // Build alerts
        const alerts = [];
        if (failed > 0)   alerts.push({ cls:'al-red',  icon:'fa-triangle-exclamation', txt:`${failed} Failed Post${failed>1?'s':''}`, view:'studio' });
        if (pending > 0)  alerts.push({ cls:'al-amb',  icon:'fa-clock',                txt:`${pending} Awaiting Approval`, view:'studio' });
        const expiring = this.state.accounts.filter(a => a.token_expiry_date && a.token_expiry_date && (new Date(a.token_expiry_date) - new Date()) / 86400000 < 7).length;
        if (expiring > 0) alerts.push({ cls:'al-red',  icon:'fa-key',                  txt:`${expiring} Token${expiring>1?'s':''} Expiring`, view:'accounts' });
        const unanswered = this.state.comments.filter(c => c.status === 'New').length;
        if (unanswered>0) alerts.push({ cls:'al-acc',  icon:'fa-comment',              txt:`${unanswered} New Comment${unanswered>1?'s':''}`, view:'inbox' });

        const alertsHTML = alerts.map(a => `
            <div class="smm-alert ${a.cls}" onclick="window.__smm.switchView('${a.view}')">
                <i class="fa-solid ${a.icon}"></i> ${a.txt}
            </div>`).join('');

        // Recent posts (last 6)
        const recentCards = p.slice(0, 6).map(post => {
            const meta = sm(post.status);
            return `
            <div class="smm-post-card" onclick="window.__smm.openPostDetail('${post.name}')">
                <div class="smm-post-card-title">${esc(post.post_title)}</div>
                <div class="smm-post-card-excerpt">${esc((post.content||'').replace(/<[^>]+>/g,''))}</div>
                <div class="smm-post-card-meta">
                    <span class="smm-badge" style="background:${meta.col}22;color:${meta.col}">
                        <i class="fa-solid ${meta.icon}"></i> ${post.status}
                    </span>
                    ${post.content_type ? `<span class="smm-badge bd-grey">${post.content_type}</span>` : ''}
                    ${post.global_schedule ? `<span style="font-size:10px;color:var(--tx3)">${frappe.datetime.str_to_user(post.global_schedule.split(' ')[0])}</span>` : ''}
                </div>
                ${flt(post.total_reach) > 0 ? `
                <div class="smm-post-metrics">
                    <div class="smm-post-metric"><div class="smm-post-metric-val">${numK(post.total_reach)}</div><div class="smm-post-metric-lbl">Reach</div></div>
                    <div class="smm-post-metric"><div class="smm-post-metric-val">${numK(post.total_likes)}</div><div class="smm-post-metric-lbl">Likes</div></div>
                    <div class="smm-post-metric"><div class="smm-post-metric-val">${numK(post.total_comments)}</div><div class="smm-post-metric-lbl">Cmts</div></div>
                    <div class="smm-post-metric"><div class="smm-post-metric-val">${flt(post.total_engagement_rate).toFixed(1)}%</div><div class="smm-post-metric-lbl">Eng%</div></div>
                </div>` : ''}
            </div>`;
        }).join('');

        this.setContent(`
        <div style="animation:fadeIn .3s ease">
            ${alerts.length ? `<div class="smm-alerts">${alertsHTML}</div>` : ''}

            <div class="smm-kpis">
                <div class="smm-kpi" style="--kc:var(--pri)" onclick="window.__smm.switchView('analytics')">
                    <div class="smm-kpi-icon">👁</div>
                    <div class="smm-kpi-lbl">Total Reach</div>
                    <div class="smm-kpi-val">${numK(totalReach)}</div>
                    <div class="smm-kpi-sub">All platforms</div>
                </div>
                <div class="smm-kpi" style="--kc:var(--acc)" onclick="window.__smm.switchView('analytics')">
                    <div class="smm-kpi-icon">❤</div>
                    <div class="smm-kpi-lbl">Engagements</div>
                    <div class="smm-kpi-val">${numK(totalEngage)}</div>
                    <div class="smm-kpi-sub">Likes + comments + shares</div>
                </div>
                <div class="smm-kpi" style="--kc:var(--sky)">
                    <div class="smm-kpi-icon">📊</div>
                    <div class="smm-kpi-lbl">Avg Eng Rate</div>
                    <div class="smm-kpi-val">${avgEngRate}%</div>
                    <div class="smm-kpi-sub">Published posts</div>
                </div>
                <div class="smm-kpi" style="--kc:var(--grn)" onclick="window.__smm.switchView('studio')">
                    <div class="smm-kpi-icon">✅</div>
                    <div class="smm-kpi-lbl">Published</div>
                    <div class="smm-kpi-val">${published}</div>
                    <div class="smm-kpi-sub">${scheduled} scheduled</div>
                </div>
                <div class="smm-kpi" style="--kc:var(--amb)" onclick="window.__smm.switchView('inbox')">
                    <div class="smm-kpi-icon">💬</div>
                    <div class="smm-kpi-lbl">Comments</div>
                    <div class="smm-kpi-val">${this.state.comments.length}</div>
                    <div class="smm-kpi-sub">${unanswered} unanswered</div>
                </div>
                <div class="smm-kpi" style="--kc:var(--sky)" onclick="window.__smm.switchView('accounts')">
                    <div class="smm-kpi-icon">🔗</div>
                    <div class="smm-kpi-lbl">Platforms</div>
                    <div class="smm-kpi-val">${this.state.accounts.filter(a=>a.is_active).length}</div>
                    <div class="smm-kpi-sub">Active connections</div>
                </div>
            </div>

            <div class="smm-g21">
                <div>
                    <div class="smm-card smm-row">
                        <div class="smm-card-head">
                            <div class="smm-card-title">
                                <div class="smm-title-icon" style="background:var(--pri_x);color:var(--pri2)"><i class="fa-solid fa-layer-group"></i></div>
                                Recent Posts
                            </div>
                            <div class="smm-btns">
                                <button class="smm-btn btn-primary btn-sm" onclick="window.__smm.openCompose()"><i class="fa-solid fa-plus"></i> New Post</button>
                                <button class="smm-btn btn-ghost btn-sm" onclick="window.__smm.switchView('compose')">View All →</button>
                            </div>
                        </div>
                        <div style="padding:14px;display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px">
                            ${recentCards || '<div class="smm-empty"><div class="smm-empty-icon">📭</div><h4>No posts yet</h4><p>Create your first post to get started</p><button class="smm-btn btn-primary" onclick="window.__smm.openCompose()"><i class="fa-solid fa-plus"></i> Create Post</button></div>'}
                        </div>
                    </div>
                </div>

                <div>
                    <!-- Platform health sidebar -->
                    <div class="smm-card smm-row">
                        <div class="smm-card-head">
                            <div class="smm-card-title">
                                <div class="smm-title-icon" style="background:var(--grn_x);color:var(--grn)"><i class="fa-solid fa-plug"></i></div>
                                Platform Status
                            </div>
                            <button class="smm-btn btn-ghost btn-xs" onclick="window.__smm.switchView('accounts')">Manage →</button>
                        </div>
                        <div style="padding:12px 16px">
                            ${this.state.accounts.length ? this.state.accounts.map(acc => {
                                const pi = pm(acc.platform);
                                const statusMeta = { 'Connected':'var(--grn)','Disconnected':'var(--tx3)','Token Expired':'var(--red)','Rate Limited':'var(--amb)','API Error':'var(--red)' };
                                const sc = statusMeta[acc.account_status] || 'var(--tx3)';
                                return `
                                <div style="display:flex;align-items:center;gap:10px;padding:9px 0;border-bottom:1px solid var(--brd)" onclick="window.__smm.editAccount('${acc.name}')">
                                    <div style="width:32px;height:32px;border-radius:9px;background:${pi.col};display:flex;align-items:center;justify-content:center;color:#fff;font-size:14px;flex-shrink:0">
                                        <i class="${pi.icon}"></i>
                                    </div>
                                    <div style="flex:1;min-width:0">
                                        <div style="font-size:12px;font-weight:600;color:var(--tx1);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(acc.account_name)}</div>
                                        <div style="font-size:10px;color:var(--tx3)">${acc.platform}</div>
                                    </div>
                                    <div style="width:7px;height:7px;border-radius:50%;background:${sc};flex-shrink:0"></div>
                                </div>`;
                            }).join('') + `
                                <div style="padding-top:10px">
                                    <button class="smm-btn btn-ghost btn-sm" style="width:100%;justify-content:center" onclick="window.__smm.openAddAccount()">
                                        <i class="fa-solid fa-plus"></i> Connect Platform
                                    </button>
                                </div>` : `
                            <div class="smm-empty" style="padding:24px">
                                <div class="smm-empty-icon">🔗</div>
                                <h4>No platforms connected</h4>
                                <button class="smm-btn btn-primary btn-sm" onclick="window.__smm.openAddAccount()">Connect Now</button>
                            </div>`}
                        </div>
                    </div>

                    <!-- Quick stats card -->
                    <div class="smm-card">
                        <div class="smm-card-head">
                            <div class="smm-card-title">
                                <div class="smm-title-icon" style="background:var(--sky_x);color:var(--sky)"><i class="fa-solid fa-chart-pie"></i></div>
                                Post Mix
                            </div>
                        </div>
                        <div style="padding:14px 16px">
                            ${this.buildStatusBreakdown(p)}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Upcoming scheduled posts -->
            ${this.buildUpcomingPanel(p)}
        </div>
        `);

        // Re-bind chart after render
        setTimeout(() => this.buildMiniEngagementChart(p), 100);
    }

    buildStatusBreakdown(posts) {
        const counts = {};
        posts.forEach(p => { counts[p.status] = (counts[p.status]||0)+1; });
        const total = posts.length || 1;
        return Object.entries(counts).sort((a,b)=>b[1]-a[1]).map(([s,n]) => {
            const meta = sm(s);
            return `
            <div class="smm-bar-row">
                <div class="smm-bar-lbl">
                    <span class="smm-badge" style="background:${meta.col}22;color:${meta.col};font-size:9px">${s}</span>
                </div>
                <div class="smm-bar"><div class="smm-bar-fill" style="width:${Math.round(n/total*100)}%;background:${meta.col}"></div></div>
                <div class="smm-bar-val">${n}</div>
            </div>`;
        }).join('') || '<div style="color:var(--tx3);font-size:12px;padding:8px 0">No posts</div>';
    }

    buildUpcomingPanel(posts) {
        const upcoming = posts.filter(p => p.status === 'Scheduled' && p.global_schedule)
            .sort((a,b) => new Date(a.global_schedule) - new Date(b.global_schedule))
            .slice(0, 8);
        if (!upcoming.length) return '';
        return `
        <div class="smm-card smm-row">
            <div class="smm-card-head">
                <div class="smm-card-title">
                    <div class="smm-title-icon" style="background:var(--amb_x);color:var(--amb)"><i class="fa-solid fa-calendar-clock"></i></div>
                    Upcoming Scheduled (${upcoming.length})
                </div>
                <button class="smm-btn btn-ghost btn-sm" onclick="window.__smm.switchView('calendar')">Calendar View →</button>
            </div>
            <div class="smm-tbl-wrap">
                <table class="smm-tbl">
                    <thead><tr>
                        <th>Post Title</th><th>Type</th><th>Scheduled</th>
                        <th>Strategy</th><th>Actions</th>
                    </tr></thead>
                    <tbody>
                    ${upcoming.map(post => `
                        <tr onclick="window.__smm.openPostDetail('${post.name}')">
                            <td style="font-weight:600;color:var(--tx1);max-width:240px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(post.post_title)}</td>
                            <td><span class="smm-badge bd-grey">${post.content_type||'—'}</span></td>
                            <td style="font-family:'Space Mono',monospace;font-size:11px">${frappe.datetime.str_to_user(post.global_schedule?.split(' ')[0]||'')}</td>
                            <td style="font-size:11px;color:var(--tx3)">${post.publish_strategy||'—'}</td>
                            <td onclick="event.stopPropagation()">
                                <div class="smm-btns">
                                    <button class="smm-btn btn-ghost btn-xs" onclick="window.__smm.openPostDetail('${post.name}')"><i class="fa-solid fa-pen"></i></button>
                                    <button class="smm-btn btn-grn btn-xs" onclick="window.__smm.quickApprove('${post.name}')">Approve</button>
                                </div>
                            </td>
                        </tr>`).join('')}
                    </tbody>
                </table>
            </div>
        </div>`;
    }

    buildMiniEngagementChart(posts) {
        const canvas = document.getElementById('smm-mini-chart');
        if (!canvas || typeof Chart === 'undefined') return;
        const last7 = [];
        for (let i = 6; i >= 0; i--) {
            const d = frappe.datetime.add_days(frappe.datetime.get_today(), -i);
            const dp = posts.filter(p => (p.global_schedule||p.creation||'').startsWith(d));
            last7.push({
                label: new Date(d).toLocaleDateString('en-NG',{weekday:'short'}),
                reach: dp.reduce((s,p) => s+flt(p.total_reach),0)
            });
        }
        if (this.charts['mini']) this.charts['mini'].destroy();
        this.charts['mini'] = new Chart(canvas, {
            type: 'line',
            data: {
                labels: last7.map(d=>d.label),
                datasets: [{
                    label: 'Reach', data: last7.map(d=>d.reach),
                    borderColor: '#6366F1', backgroundColor: 'rgba(99,102,241,.12)',
                    borderWidth: 2, fill: true, tension: .4, pointRadius: 0
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { color: 'rgba(255,255,255,.04)' }, ticks: { color: '#4A5680', font: { size: 10 } } },
                    y: { grid: { color: 'rgba(255,255,255,.04)' }, ticks: { color: '#4A5680', font: { size: 10 }, callback: v => numK(v) } }
                }
            }
        });
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW: COMPOSE (Interactive Post Builder)
    // ═══════════════════════════════════════════════════════════════════════════
    renderCompose() {
        const d = this.state.composeDraft;
        const accounts = this.state.accounts.filter(a => a.is_active);

        this.setContent(`
        <div style="animation:fadeIn .3s ease">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px">
                <div>
                    <h2 style="font-size:20px;font-weight:800;color:var(--tx1);margin:0 0 4px">Post Composer</h2>
                    <div style="font-size:12px;color:var(--tx3)">Create, schedule & publish across all platforms from one place</div>
                </div>
                <div class="smm-btns">
                    <button class="smm-btn btn-ghost" onclick="window.__smm.renderPostList()"><i class="fa-solid fa-list"></i> All Posts</button>
                    <button class="smm-btn btn-primary" onclick="window.__smm.savePost(false)"><i class="fa-solid fa-floppy-disk"></i> Save Draft</button>
                    <button class="smm-btn btn-accent" onclick="window.__smm.savePost(true)"><i class="fa-solid fa-rocket"></i> Save & Submit</button>
                </div>
            </div>

            <div class="smm-compose">
                <!-- Main editor -->
                <div>
                    <div class="smm-compose-main smm-row">
                        <div style="padding:18px 20px;border-bottom:1px solid var(--brd)">
                            <div class="smm-fg">
                                <label>Post Title <span class="req">*</span></label>
                                <input class="smm-inp" id="cp-title" placeholder="Give this post a descriptive title…" value="${esc(d.post_title||'')}">
                            </div>
                        </div>

                        <!-- Platform toggles — live from settings -->
                        <div class="smm-plat-toggles" id="cp-plat-toggles">
                            ${accounts.length ? accounts.map(acc => {
                                const pi = pm(acc.platform);
                                const on = (d.selectedAccounts||[]).includes(acc.name);
                                return `
                                <div class="smm-plat-toggle ${on?'on':''}" data-acc="${acc.name}" data-platform="${acc.platform}" onclick="window.__smm.togglePlatform(this)">
                                    <i class="${pi.icon}" style="color:${pi.col}"></i>
                                    ${esc(acc.account_name)}
                                </div>`;
                            }).join('') : `<div style="font-size:12px;color:var(--tx3)">No active platforms — <a onclick="window.__smm.switchView('accounts')" style="color:var(--pri2);cursor:pointer">connect one →</a></div>`}
                        </div>

                        <div style="padding:18px 20px">
                            <div class="smm-form">
                                <div class="smm-fg">
                                    <label>Main Caption / Content <span class="req">*</span></label>
                                    <textarea class="smm-ta" id="cp-content" rows="6" placeholder="Write your caption here… Use emojis, hashtags, and mentions to boost engagement.">${esc(d.content||'')}</textarea>
                                    <div style="display:flex;justify-content:space-between;align-items:center;margin-top:4px">
                                        <div style="font-size:10px;color:var(--tx3)" id="cp-char-info">0 characters</div>
                                        <div id="cp-char-limits" style="display:flex;gap:8px"></div>
                                    </div>
                                </div>

                                <div class="smm-fg-row">
                                    <div class="smm-fg">
                                        <label>Content Type</label>
                                        <select class="smm-sel" id="cp-content-type">
                                            ${['Image','Video','Carousel','Reel','Story','Text Only','Link','Poll','Article','Live Video'].map(t =>
                                                `<option value="${t}" ${(d.content_type||'Image')===t?'selected':''}>${t}</option>`
                                            ).join('')}
                                        </select>
                                    </div>
                                    <div class="smm-fg">
                                        <label>Publish Strategy</label>
                                        <select class="smm-sel" id="cp-strategy">
                                            ${['Publish Now','Schedule Global','Schedule Per Platform','Optimize AI (Smart Schedule)'].map(s =>
                                                `<option value="${s}" ${(d.publish_strategy||'Schedule Global')===s?'selected':''}>${s}</option>`
                                            ).join('')}
                                        </select>
                                    </div>
                                </div>

                                <div class="smm-fg-row" id="cp-schedule-row">
                                    <div class="smm-fg">
                                        <label>Schedule Date & Time</label>
                                        <input class="smm-inp" id="cp-schedule" type="datetime-local" value="${d.global_schedule||''}">
                                    </div>
                                    <div class="smm-fg">
                                        <label>Campaign</label>
                                        <input class="smm-inp" id="cp-campaign" placeholder="Campaign name or code" value="${esc(d.campaign||'')}">
                                    </div>
                                </div>

                                <div class="smm-fg-row">
                                    <div class="smm-fg">
                                        <label>Primary Hashtags</label>
                                        <input class="smm-inp" id="cp-hashtags" placeholder="#socialmedia #marketing #growth" value="${esc(d.primary_hashtags||'')}">
                                    </div>
                                    <div class="smm-fg">
                                        <label>Mentions</label>
                                        <input class="smm-inp" id="cp-mentions" placeholder="@account @brand" value="${esc(d.mentions||'')}">
                                    </div>
                                </div>

                                <div class="smm-fg-row">
                                    <div class="smm-fg">
                                        <label>Link URL</label>
                                        <input class="smm-inp" id="cp-link" placeholder="https://…" value="${esc(d.link_url||'')}">
                                    </div>
                                    <div class="smm-fg">
                                        <label>Location</label>
                                        <input class="smm-inp" id="cp-location" placeholder="Lagos, Nigeria" value="${esc(d.location||'')}">
                                    </div>
                                </div>

                                <div class="smm-fg-row">
                                    <div class="smm-check-row">
                                        <input type="checkbox" id="cp-requires-approval" ${d.requires_approval?'checked':''}>
                                        <label for="cp-requires-approval">Requires Approval Before Publishing</label>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Per-platform content override section -->
                    <div class="smm-card smm-row" id="cp-platform-overrides">
                        <div class="smm-card-head">
                            <div class="smm-card-title">
                                <div class="smm-title-icon" style="background:var(--sky_x);color:var(--sky)"><i class="fa-solid fa-sliders"></i></div>
                                Platform-Specific Overrides
                            </div>
                            <span style="font-size:11px;color:var(--tx3)">Customise caption, hashtags & timing per platform</span>
                        </div>
                        <div style="padding:14px 20px" id="cp-overrides-body">
                            <div style="font-size:12px;color:var(--tx3);text-align:center;padding:16px">Select platforms above to configure overrides</div>
                        </div>
                    </div>
                </div>

                <!-- Sidebar -->
                <div class="smm-compose-sidebar">
                    <!-- AI Score card -->
                    <div class="smm-card" id="cp-ai-card">
                        <div class="smm-card-head">
                            <div class="smm-card-title">
                                <div class="smm-title-icon" style="background:var(--pri_x);color:var(--pri2)"><i class="fa-solid fa-robot"></i></div>
                                AI Content Score
                            </div>
                            <button class="smm-btn btn-ghost btn-xs" onclick="window.__smm.scoreContent()"><i class="fa-solid fa-wand-magic-sparkles"></i> Analyse</button>
                        </div>
                        <div style="padding:14px 16px" id="cp-ai-body">
                            <div style="text-align:center;padding:20px;color:var(--tx3)">
                                <i class="fa-solid fa-robot" style="font-size:24px;margin-bottom:8px;display:block"></i>
                                <div style="font-size:11px">Fill in your caption and click Analyse</div>
                            </div>
                        </div>
                    </div>

                    <!-- Best time suggestions -->
                    <div class="smm-card">
                        <div class="smm-card-head">
                            <div class="smm-card-title">
                                <div class="smm-title-icon" style="background:var(--amb_x);color:var(--amb)"><i class="fa-solid fa-clock"></i></div>
                                Optimal Times
                            </div>
                        </div>
                        <div style="padding:14px 16px">
                            ${[['Instagram','9AM – 11AM','Tue, Thu'],['LinkedIn','12PM – 2PM','Tue – Thu'],['Facebook','1PM – 3PM','Wed, Fri'],['Twitter/X','6PM – 9PM','Weekdays'],['TikTok','7PM – 11PM','Daily']].map(([p,t,d]) => {
                                const pi = pm(p);
                                return `
                                <div style="display:flex;align-items:center;gap:9px;padding:7px 0;border-bottom:1px solid var(--brd)">
                                    <div style="width:24px;height:24px;border-radius:7px;background:${pi.col};display:flex;align-items:center;justify-content:center;color:#fff;font-size:11px;flex-shrink:0">
                                        <i class="${pi.icon}"></i>
                                    </div>
                                    <div style="flex:1">
                                        <div style="font-size:11px;font-weight:600;color:var(--tx1)">${p}</div>
                                        <div style="font-size:10px;color:var(--tx3)">${t} · ${d}</div>
                                    </div>
                                    <button class="smm-btn btn-ghost btn-xs" onclick="window.__smm.applyTime('${t}')">Use</button>
                                </div>`;
                            }).join('')}
                        </div>
                    </div>

                    <!-- Hashtag suggester -->
                    <div class="smm-card">
                        <div class="smm-card-head">
                            <div class="smm-card-title">
                                <div class="smm-title-icon" style="background:var(--acc_x);color:var(--acc)"><i class="fa-solid fa-hashtag"></i></div>
                                Hashtag Suggester
                            </div>
                        </div>
                        <div style="padding:14px 16px">
                            <div class="smm-fg" style="margin-bottom:10px">
                                <input class="smm-inp" id="ht-topic" placeholder="Topic: e.g. fintech, Lagos, SME…">
                            </div>
                            <button class="smm-btn btn-accent btn-sm" style="width:100%;justify-content:center" onclick="window.__smm.suggestHashtags()">
                                <i class="fa-solid fa-wand-magic-sparkles"></i> Generate Hashtags
                            </button>
                            <div id="ht-results" style="margin-top:10px;display:flex;flex-wrap:wrap;gap:6px"></div>
                        </div>
                    </div>

                    <!-- Recent drafts -->
                    <div class="smm-card">
                        <div class="smm-card-head">
                            <div class="smm-card-title">
                                <div class="smm-title-icon" style="background:var(--brd2);color:var(--tx3)"><i class="fa-solid fa-clock-rotate-left"></i></div>
                                Recent Drafts
                            </div>
                        </div>
                        <div style="max-height:200px;overflow-y:auto">
                            ${this.state.posts.filter(p=>p.status==='Draft').slice(0,5).map(post=>`
                            <div style="padding:10px 16px;border-bottom:1px solid var(--brd);cursor:pointer;transition:background .12s" onclick="window.__smm.loadDraft('${post.name}')" class="smm-comment">
                                <div style="font-size:12px;font-weight:600;color:var(--tx1);margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(post.post_title)}</div>
                                <div style="font-size:10px;color:var(--tx3)">${frappe.datetime.prettyDate(post.modified)}</div>
                            </div>`).join('') || '<div style="padding:14px;text-align:center;font-size:12px;color:var(--tx3)">No drafts</div>'}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        `);

        // Bind live events
        this.bindComposeEvents();
    }

    bindComposeEvents() {
        const content = document.getElementById('cp-content');
        if (!content) return;
        content.addEventListener('input', () => this.updateCharCounts());
        document.getElementById('cp-strategy')?.addEventListener('change', (e) => {
            const show = ['Schedule Global','Optimize AI (Smart Schedule)'].includes(e.target.value);
            document.getElementById('cp-schedule-row').style.display = show ? '' : '';
        });
    }

    updateCharCounts() {
        const content = document.getElementById('cp-content')?.value || '';
        const len = content.length;
        document.getElementById('cp-char-info').textContent = `${len} characters`;

        // Show per-platform limits for selected platforms
        const selected = [...document.querySelectorAll('.smm-plat-toggle.on')].map(el => el.dataset.platform);
        const limits = document.getElementById('cp-char-limits');
        if (limits) {
            limits.innerHTML = selected.slice(0,3).map(plat => {
                const meta = pm(plat);
                const over = len > meta.charLimit;
                return `<span style="font-size:9px;padding:2px 6px;border-radius:6px;background:${over?'var(--red_x)':'var(--brd2)'};color:${over?'var(--red)':'var(--tx3)'}">
                    ${pm(plat).abbr}: ${len}/${meta.charLimit}
                </span>`;
            }).join('');
        }
    }

    togglePlatform(el) {
        el.classList.toggle('on');
        this.updatePlatformOverrides();
        this.updateCharCounts();
    }

    updatePlatformOverrides() {
        const selected = [...document.querySelectorAll('.smm-plat-toggle.on')];
        const body = document.getElementById('cp-overrides-body');
        if (!body) return;
        if (!selected.length) {
            body.innerHTML = '<div style="font-size:12px;color:var(--tx3);text-align:center;padding:16px">Select platforms above to configure overrides</div>';
            return;
        }
        body.innerHTML = selected.map(el => {
            const acc  = el.dataset.acc;
            const plat = el.dataset.platform;
            const pi   = pm(plat);
            return `
            <div style="border:1px solid var(--brd);border-radius:12px;margin-bottom:12px;overflow:hidden">
                <div style="padding:10px 14px;background:var(--bg2);display:flex;align-items:center;gap:8px">
                    <div style="width:24px;height:24px;border-radius:7px;background:${pi.col};display:flex;align-items:center;justify-content:center;color:#fff;font-size:12px">
                        <i class="${pi.icon}"></i>
                    </div>
                    <span style="font-size:12px;font-weight:700;color:var(--tx1)">${plat}</span>
                    <span style="font-size:10px;color:var(--tx3)">Char limit: ${pi.charLimit.toLocaleString()}</span>
                    <label class="smm-toggle" style="margin-left:auto">
                        <input type="checkbox" checked>
                        <div class="smm-toggle-track"></div>
                        <div class="smm-toggle-thumb"></div>
                    </label>
                </div>
                <div style="padding:12px 14px;display:flex;flex-direction:column;gap:10px">
                    <div class="smm-fg">
                        <label>Custom Caption (leave blank to use main)</label>
                        <textarea class="smm-ta" data-acc="${acc}" data-field="custom_caption" rows="3" placeholder="Platform-specific version…" style="min-height:60px"></textarea>
                    </div>
                    <div class="smm-fg-row">
                        <div class="smm-fg">
                            <label>Platform Hashtags</label>
                            <input class="smm-inp" data-acc="${acc}" data-field="custom_hashtags" placeholder="#platform #specific">
                        </div>
                        <div class="smm-fg">
                            <label>Post Type</label>
                            <select class="smm-sel" data-acc="${acc}" data-field="post_type">
                                ${['Auto (Smart Detect)','Image','Video','Carousel','Reel','Story','Text Only','Link','Poll'].map(t=>`<option>${t}</option>`).join('')}
                            </select>
                        </div>
                    </div>
                    <div class="smm-fg">
                        <label>Scheduled Time (leave blank for global schedule)</label>
                        <input class="smm-inp" type="datetime-local" data-acc="${acc}" data-field="scheduled_time">
                    </div>
                </div>
            </div>`;
        }).join('');
    }

    scoreContent() {
        const content = document.getElementById('cp-content')?.value || '';
        const hashtags = document.getElementById('cp-hashtags')?.value || '';
        const selected = [...document.querySelectorAll('.smm-plat-toggle.on')].length;

        // Heuristic scoring
        let score = 0; const items = [];
        const len = content.length;
        if (len >= 50 && len <= 300)    { score += 20; items.push({ ok:true, txt:'Caption length is optimal (50–300 chars)' }); }
        else if (len < 50)              { score += 8;  items.push({ ok:false, txt:`Caption is short (${len} chars) — add more context` }); }
        else                            { score += 12; items.push({ ok:null,  txt:`Long caption (${len} chars) — consider trimming` }); }

        const htags = hashtags.split(/\s+/).filter(h=>h.startsWith('#'));
        if (htags.length >= 5 && htags.length <= 15) { score += 20; items.push({ ok:true, txt:`Good hashtag count (${htags.length})` }); }
        else if (htags.length < 3)                   { score += 5;  items.push({ ok:false, txt:'Add 5–15 hashtags to boost reach' }); }
        else if (htags.length > 20)                  { score += 10; items.push({ ok:null,  txt:'Too many hashtags — quality over quantity' }); }

        if (/[?!]/.test(content))       { score += 15; items.push({ ok:true, txt:'Has call-to-action or engagement hook' }); }
        else                            { score += 5;  items.push({ ok:false, txt:'Add a question or CTA to drive engagement' }); }

        if (selected >= 2)              { score += 20; items.push({ ok:true, txt:`Posting to ${selected} platforms` }); }
        else if (selected === 1)        { score += 10; items.push({ ok:null,  txt:'Consider cross-posting to more platforms' }); }
        else                            { score += 0;  items.push({ ok:false, txt:'No platforms selected' }); }

        if (/https?:\/\//.test(content) || document.getElementById('cp-link')?.value) { score += 15; items.push({ ok:true, txt:'Includes a link' }); }
        else                            { score += 8;  items.push({ ok:null,  txt:'Consider adding a link for more traffic' }); }

        score = Math.min(100, score);
        const col = score >= 75 ? 'var(--grn)' : score >= 50 ? 'var(--amb)' : 'var(--red)';
        const c   = 2 * Math.PI * 28;
        const off = c * (1 - score / 100);

        document.getElementById('cp-ai-body').innerHTML = `
        <div style="text-align:center;margin-bottom:14px">
            <svg width="80" height="80" viewBox="0 0 80 80">
                <circle cx="40" cy="40" r="28" fill="none" stroke="var(--brd2)" stroke-width="7"/>
                <circle cx="40" cy="40" r="28" fill="none" stroke="${col}" stroke-width="7"
                    stroke-dasharray="${c.toFixed(1)}" stroke-dashoffset="${off.toFixed(1)}"
                    stroke-linecap="round" transform="rotate(-90 40 40)"/>
                <text x="40" y="46" text-anchor="middle" font-size="18" font-weight="800" fill="${col}">${score}</text>
            </svg>
            <div style="font-size:11px;color:var(--tx3);margin-top:4px">Content Score</div>
        </div>
        ${items.map(item => `
        <div style="display:flex;align-items:flex-start;gap:7px;margin-bottom:6px;font-size:11px;color:var(--tx2)">
            <i class="fa-solid ${item.ok===true?'fa-circle-check':item.ok===false?'fa-circle-xmark':'fa-circle-minus'}" 
               style="color:${item.ok===true?'var(--grn)':item.ok===false?'var(--red)':'var(--amb)'};margin-top:1px;flex-shrink:0"></i>
            ${item.txt}
        </div>`).join('')}`;
    }

    suggestHashtags() {
        const topic = document.getElementById('ht-topic')?.value || 'business';
        const sets = {
            fintech: ['#fintech','#digitalbanking','#nigeriafintech','#moneytransfer','#payments','#neobank','#startup','#innovation','#africa','#investng'],
            marketing: ['#marketing','#digitalmarketing','#socialmedia','#contentmarketing','#branding','#seo','#growthhacking','#b2b','#agency'],
            lagos: ['#lagos','#lagosbusiness','#naija','#nigeria','#lagoslife','#entrepreneurship','#madeinnigeria','#nigerianstartup'],
            sme: ['#sme','#smallbusiness','#entrepreneur','#business','#nigeriaentrepreneur','#supportsmallbusiness','#growth'],
            default: ['#business','#entrepreneur','#marketing','#socialmedia','#growth','#branding','#digital','#strategy','#success','#innovation']
        };
        const key = Object.keys(sets).find(k => topic.toLowerCase().includes(k)) || 'default';
        const tags = sets[key];
        const container = document.getElementById('ht-results');
        if (container) {
            container.innerHTML = tags.map(t => `
            <span onclick="window.__smm.addHashtag('${t}')" 
                  style="padding:4px 10px;border-radius:20px;font-size:11px;font-weight:600;background:var(--pri_x);color:var(--pri2);cursor:pointer;transition:background .12s"
                  onmouseenter="this.style.background='var(--pri)';this.style.color='#fff'"
                  onmouseleave="this.style.background='var(--pri_x)';this.style.color='var(--pri2)'">${t}</span>`).join('');
        }
    }

    addHashtag(tag) {
        const field = document.getElementById('cp-hashtags');
        if (!field) return;
        const existing = field.value.split(/\s+/).filter(Boolean);
        if (!existing.includes(tag)) {
            field.value = [...existing, tag].join(' ');
            this.updateCharCounts();
        }
    }

    applyTime(timeStr) {
        const match = timeStr.match(/(\d+)(AM|PM)/i);
        if (!match) return;
        let h = parseInt(match[1]);
        if (match[2].toUpperCase() === 'PM' && h < 12) h += 12;
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        tomorrow.setHours(h, 0, 0, 0);
        const field = document.getElementById('cp-schedule');
        if (field) {
            field.value = tomorrow.toISOString().slice(0,16);
        }
    }

    async savePost(submit) {
        const title    = document.getElementById('cp-title')?.value?.trim();
        const content  = document.getElementById('cp-content')?.value?.trim();
        const ctype    = document.getElementById('cp-content-type')?.value;
        const strategy = document.getElementById('cp-strategy')?.value;
        const schedule = document.getElementById('cp-schedule')?.value;
        const campaign = document.getElementById('cp-campaign')?.value;
        const hashtags = document.getElementById('cp-hashtags')?.value;
        const mentions = document.getElementById('cp-mentions')?.value;
        const link     = document.getElementById('cp-link')?.value;
        const location = document.getElementById('cp-location')?.value;
        const approval = document.getElementById('cp-requires-approval')?.checked ? 1 : 0;

        if (!title) { frappe.show_alert({ message: 'Post title is required', indicator: 'red' }); return; }
        if (!content) { frappe.show_alert({ message: 'Caption / content is required', indicator: 'red' }); return; }

        const selected = [...document.querySelectorAll('.smm-plat-toggle.on')];
        if (!selected.length) { frappe.show_alert({ message: 'Select at least one platform', indicator: 'red' }); return; }

        // Build platform_configs child table
        const platform_configs = selected.map(el => {
            const acc  = el.dataset.acc;
            const plat = el.dataset.platform;
            const custom_caption  = document.querySelector(`[data-acc="${acc}"][data-field="custom_caption"]`)?.value || '';
            const custom_hashtags = document.querySelector(`[data-acc="${acc}"][data-field="custom_hashtags"]`)?.value || '';
            const post_type       = document.querySelector(`[data-acc="${acc}"][data-field="post_type"]`)?.value || 'Auto (Smart Detect)';
            const scheduled_time  = document.querySelector(`[data-acc="${acc}"][data-field="scheduled_time"]`)?.value || '';
            return { platform_account: acc, platform: plat, is_enabled: 1, custom_caption, custom_hashtags, post_type, scheduled_time, post_status: 'Pending' };
        });

        const doc = {
            doctype: 'Social Post',
            post_title: title, content, content_type: ctype, publish_strategy: strategy,
            global_schedule: schedule || null, campaign: campaign || null,
            primary_hashtags: hashtags || null, mentions: mentions || null,
            link_url: link || null, location: location || null,
            requires_approval: approval, status: 'Draft',
            platform_configs
        };

        try {
            const r = await frappe.call({ method: 'frappe.client.insert', args: { doc } });
            if (r.message) {
                if (submit) {
                    await frappe.call({ method: 'frappe.client.submit', args: { doc: r.message } });
                    frappe.show_alert({ message: `Post submitted: ${r.message.name}`, indicator: 'green' });
                } else {
                    frappe.show_alert({ message: `Draft saved: ${r.message.name}`, indicator: 'green' });
                }
                this.state.composeDraft = {};
                await this.fetchAll(true);
                this.switchView('studio');
            }
        } catch(e) {
            frappe.show_alert({ message: 'Failed to save post: ' + (e.message||'Unknown error'), indicator: 'red' });
        }
    }

    loadDraft(name) {
        const post = this.state.posts.find(p => p.name === name);
        if (!post) return;
        this.state.composeDraft = { ...post };
        this.renderCompose();
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW: ALL POSTS (table view within compose)
    // ═══════════════════════════════════════════════════════════════════════════
    renderPostList() {
        const posts = this.state.posts;
        const filterBar = `
        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px">
            <select class="smm-sel" id="pl-flt-status" style="width:auto;min-width:140px">
                <option value="">All Status</option>
                ${Object.keys(STATUS_META).map(s=>`<option ${this.state.filters.status===s?'selected':''}>${s}</option>`).join('')}
            </select>
            <input class="smm-inp" id="pl-flt-search" placeholder="Search posts…" style="width:240px" value="">
            <button class="smm-btn btn-primary btn-sm" onclick="window.__smm.applyPostFilters()"><i class="fa-solid fa-filter"></i> Filter</button>
            <button class="smm-btn btn-ghost btn-sm" onclick="window.__smm.renderCompose()">← Back to Compose</button>
            <button class="smm-btn btn-accent btn-sm" style="margin-left:auto" onclick="window.__smm.openCompose()"><i class="fa-solid fa-plus"></i> New Post</button>
        </div>`;

        const filtered = posts.filter(p => {
            const fs = this.state.filters.status;
            const fq = (document.getElementById('pl-flt-search')?.value||'').toLowerCase();
            return (!fs || p.status === fs) && (!fq || (p.post_title||'').toLowerCase().includes(fq));
        });

        this.setContent(`
        <div style="animation:fadeIn .3s ease">
            <h2 style="font-size:18px;font-weight:800;color:var(--tx1);margin:0 0 16px">All Posts (${posts.length})</h2>
            ${filterBar}
            <div class="smm-card">
                <div class="smm-tbl-wrap">
                    <table class="smm-tbl">
                        <thead><tr>
                            <th>Title</th><th>Type</th><th>Status</th><th>Platforms</th>
                            <th>Scheduled</th><th class="tr">Reach</th><th class="tr">Likes</th>
                            <th class="tr">Eng%</th><th>Modified</th><th>Actions</th>
                        </tr></thead>
                        <tbody>
                        ${filtered.map(post => {
                            const meta = sm(post.status);
                            return `
                            <tr onclick="window.__smm.openPostDetail('${post.name}')">
                                <td style="font-weight:600;color:var(--tx1);max-width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(post.post_title)}</td>
                                <td><span class="smm-badge bd-grey">${post.content_type||'—'}</span></td>
                                <td><span class="smm-badge" style="background:${meta.col}22;color:${meta.col}"><i class="fa-solid ${meta.icon}"></i> ${post.status}</span></td>
                                <td style="font-size:11px;color:var(--tx3)">${post.publish_strategy||'—'}</td>
                                <td style="font-size:11px;color:var(--tx3)">${post.global_schedule?frappe.datetime.str_to_user(post.global_schedule.split(' ')[0]):'—'}</td>
                                <td class="tr">${numK(post.total_reach)}</td>
                                <td class="tr">${numK(post.total_likes)}</td>
                                <td class="tr">${flt(post.total_engagement_rate).toFixed(1)}%</td>
                                <td style="font-size:11px;color:var(--tx3)">${frappe.datetime.prettyDate(post.modified)}</td>
                                <td onclick="event.stopPropagation()">
                                    <div class="smm-btns">
                                        <button class="smm-btn btn-ghost btn-xs" onclick="window.__smm.openPostDetail('${post.name}')"><i class="fa-solid fa-pen"></i></button>
                                        ${post.status==='Pending Approval'?`<button class="smm-btn btn-grn btn-xs" onclick="window.__smm.quickApprove('${post.name}')">Approve</button>`:''}
                                        ${post.status==='Draft'?`<button class="smm-btn btn-red btn-xs" onclick="window.__smm.deletePost('${post.name}')"><i class="fa-solid fa-trash"></i></button>`:''}
                                    </div>
                                </td>
                            </tr>`;
                        }).join('')}
                        </tbody>
                    </table>
                    ${!filtered.length?'<div class="smm-empty"><div class="smm-empty-icon">📭</div><h4>No posts match your filters</h4></div>':''}
                </div>
            </div>
        </div>`);
    }

    applyPostFilters() {
        this.state.filters.status = document.getElementById('pl-flt-status')?.value || '';
        this.renderPostList();
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  POST DETAIL PANEL (Inline edit + performance)
    // ═══════════════════════════════════════════════════════════════════════════
    openPostDetail(name) {
        const post = this.state.posts.find(p => p.name === name);
        if (!post) { frappe.set_route('Form', 'Social Post', name); return; }

        const meta    = sm(post.status);
        const comments = this.state.comments.filter(c => c.parent === name);
        const totalEngage = flt(post.total_likes) + flt(post.total_comments) + flt(post.total_shares);

        const d = new frappe.ui.Dialog({
            title: `📝 ${post.post_title}`,
            size: 'extra-large',
            fields: [{ fieldtype:'HTML', fieldname:'post_html', options:
                `<div style="font-family:'DM Sans',system-ui,sans-serif;color:var(--tx1)">

                <!-- Status + Meta row -->
                <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding-bottom:14px;border-bottom:1px solid #1C2237;margin-bottom:14px">
                    <span style="padding:5px 12px;border-radius:20px;font-size:11px;font-weight:700;background:${meta.col}22;color:${meta.col}">
                        <i class="fa-solid ${meta.icon}"></i> ${post.status}
                    </span>
                    <span style="font-size:11px;color:#94A3B8">${post.content_type||'—'}</span>
                    <span style="font-size:11px;color:#94A3B8">${post.publish_strategy||'—'}</span>
                    ${post.global_schedule ? `<span style="font-size:11px;color:#94A3B8"><i class="fa-solid fa-calendar"></i> ${frappe.datetime.str_to_user(post.global_schedule.split(' ')[0])}</span>` : ''}
                    <div style="margin-left:auto;display:flex;gap:8px">
                        <a href="/app/social-post/${name}" target="_blank" style="padding:5px 11px;border-radius:8px;font-size:11px;font-weight:600;background:rgba(255,255,255,.07);color:#8B96C0;text-decoration:none">Open Form →</a>
                        ${post.status==='Pending Approval'?`<button onclick="frappe.call({method:'frappe.client.set_value',args:{doctype:'Social Post',name:'${name}',fieldname:{status:'Approved',approved_by:frappe.session.user,approval_date:frappe.datetime.now_datetime()}},callback:()=>{frappe.show_alert({message:'Approved',indicator:'green'});cur_dialog.hide();__smm.fetchAll(true).then(()=>__smm.renderView(__smm.state.activeView));}})" style="padding:5px 11px;border-radius:8px;font-size:11px;font-weight:700;background:rgba(52,211,153,.15);color:#34D399;border:1px solid rgba(52,211,153,.2);cursor:pointer">✓ Approve</button>`:''}
                        ${post.status==='Approved'?`<button onclick="frappe.call({method:'frappe.client.set_value',args:{doctype:'Social Post',name:'${name}',fieldname:{status:'Scheduled'}},callback:()=>{frappe.show_alert({message:'Marked as Scheduled',indicator:'green'});cur_dialog.hide();__smm.fetchAll(true);}})" style="padding:5px 11px;border-radius:8px;font-size:11px;font-weight:700;background:rgba(139,92,246,.15);color:#818CF8;border:1px solid rgba(139,92,246,.2);cursor:pointer">📅 Schedule</button>`:''}
                    </div>
                </div>

                <!-- Metrics row -->
                ${flt(post.total_reach) > 0 ? `
                <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:16px">
                    ${[['👁','Reach',post.total_reach,'#6366F1'],['❤','Likes',post.total_likes,'#F472B6'],
                       ['💬','Comments',post.total_comments,'#FBBF24'],['🔄','Shares',post.total_shares,'#34D399'],
                       ['📊','Eng%',flt(post.total_engagement_rate).toFixed(2)+'%','#38BDF8']].map(([ic,lb,vl,cl])=>`
                    <div style="background:#1C2237;border-radius:10px;padding:10px;text-align:center;border-top:2px solid ${cl}">
                        <div style="font-size:16px;margin-bottom:4px">${ic}</div>
                        <div style="font-size:18px;font-weight:800;color:#F0F4FF">${numK(vl)}</div>
                        <div style="font-size:9px;text-transform:uppercase;letter-spacing:.5px;color:#4A5680">${lb}</div>
                    </div>`).join('')}
                </div>` : ''}

                <!-- Quick edit form -->
                <div style="background:#141828;border:1px solid rgba(255,255,255,.07);border-radius:12px;padding:16px;margin-bottom:14px">
                    <h4 style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:#4A5680;margin:0 0 12px">Quick Edit</h4>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
                        <div>
                            <label style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.7px;color:#4A5680;display:block;margin-bottom:4px">Status</label>
                            <select id="pd-status" style="width:100%;background:#1C2237;border:1.5px solid rgba(255,255,255,.13);border-radius:8px;color:#F0F4FF;padding:8px 12px;font-size:12px;outline:none">
                                ${['Draft','Pending Approval','Approved','Scheduled','Published','Failed'].map(s=>`<option ${post.status===s?'selected':''}>${s}</option>`).join('')}
                            </select>
                        </div>
                        <div>
                            <label style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.7px;color:#4A5680;display:block;margin-bottom:4px">Schedule Date</label>
                            <input id="pd-schedule" type="datetime-local" value="${post.global_schedule||''}"
                                style="width:100%;background:#1C2237;border:1.5px solid rgba(255,255,255,.13);border-radius:8px;color:#F0F4FF;padding:8px 12px;font-size:12px;outline:none">
                        </div>
                        <div style="grid-column:1/-1">
                            <label style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.7px;color:#4A5680;display:block;margin-bottom:4px">Hashtags</label>
                            <input id="pd-hashtags" value="${esc(post.primary_hashtags||'')}"
                                style="width:100%;background:#1C2237;border:1.5px solid rgba(255,255,255,.13);border-radius:8px;color:#F0F4FF;padding:8px 12px;font-size:12px;outline:none" placeholder="#tag1 #tag2">
                        </div>
                    </div>
                    <div style="margin-top:12px;display:flex;gap:8px">
                        <button onclick="window.__smm.quickUpdatePost('${name}')" style="padding:7px 16px;border-radius:8px;background:#6366F1;color:#fff;border:none;font-size:12px;font-weight:700;cursor:pointer">💾 Save Changes</button>
                        <button onclick="frappe.set_route('Form','Social Post','${name}')" style="padding:7px 16px;border-radius:8px;background:rgba(255,255,255,.07);color:#8B96C0;border:1px solid rgba(255,255,255,.1);font-size:12px;font-weight:700;cursor:pointer">Full Edit →</button>
                    </div>
                </div>

                <!-- Content preview -->
                <div style="background:#141828;border:1px solid rgba(255,255,255,.07);border-radius:12px;padding:14px;margin-bottom:14px">
                    <h4 style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:#4A5680;margin:0 0 8px">Caption</h4>
                    <div style="font-size:13px;color:#8B96C0;line-height:1.6;white-space:pre-wrap">${esc((post.content||'').replace(/<[^>]+>/g,''))}</div>
                    ${post.primary_hashtags ? `<div style="margin-top:8px;font-size:12px;color:#6366F1">${esc(post.primary_hashtags)}</div>` : ''}
                </div>

                <!-- Comments -->
                ${comments.length ? `
                <div style="background:#141828;border:1px solid rgba(255,255,255,.07);border-radius:12px;overflow:hidden">
                    <div style="padding:10px 14px;border-bottom:1px solid rgba(255,255,255,.07);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:#4A5680">
                        Comments (${comments.length})
                    </div>
                    ${comments.slice(0,5).map(c => {
                        const sentCol = c.sentiment_label==='Very Positive'||c.sentiment_label==='Positive'?'#34D399':c.sentiment_label==='Negative'||c.sentiment_label==='Very Negative'?'#F87171':'#FBBF24';
                        const initials = (c.author_name||'?').split(' ').map(w=>w[0]).join('').substring(0,2).toUpperCase();
                        const platMeta = pm(c.platform||'Other');
                        return `
                        <div style="padding:12px 14px;border-bottom:1px solid rgba(255,255,255,.05);display:flex;gap:10px">
                            <div style="width:30px;height:30px;border-radius:50%;background:${platMeta.col};display:flex;align-items:center;justify-content:center;color:#fff;font-size:11px;font-weight:700;flex-shrink:0">${initials}</div>
                            <div style="flex:1;min-width:0">
                                <div style="display:flex;align-items:center;gap:8px;margin-bottom:3px">
                                    <span style="font-size:12px;font-weight:700;color:#F0F4FF">${esc(c.author_name)}</span>
                                    <span style="font-size:9px;padding:2px 7px;border-radius:10px;background:${sentCol}22;color:${sentCol}">${c.sentiment_label||'Neutral'}</span>
                                    <span style="font-size:10px;color:#4A5680">${c.comment_time?frappe.datetime.prettyDate(c.comment_time):''}</span>
                                </div>
                                <div style="font-size:12px;color:#8B96C0">${esc((c.comment_text||'').replace(/<[^>]+>/g,''))}</div>
                                ${c.reply_text?`<div style="font-size:11px;color:#4A5680;margin-top:4px;padding:5px 8px;background:rgba(99,102,241,.1);border-radius:6px;border-left:2px solid #6366F1">↩ ${esc(c.reply_text.replace(/<[^>]+>/g,''))}</div>`:''}
                            </div>
                        </div>`;
                    }).join('')}
                </div>` : ''}
                </div>`
            }],
            primary_action_label: 'Close',
            primary_action(vals) { d.hide(); }
        });
        d.show();
    }

    quickUpdatePost(name) {
        const status    = document.getElementById('pd-status')?.value;
        const schedule  = document.getElementById('pd-schedule')?.value;
        const hashtags  = document.getElementById('pd-hashtags')?.value;

        const fieldname = {};
        if (status)   fieldname.status           = status;
        if (schedule) fieldname.global_schedule   = schedule;
        if (hashtags !== undefined) fieldname.primary_hashtags = hashtags;

        frappe.call({
            method: 'frappe.client.set_value',
            args: { doctype: 'Social Post', name, fieldname },
            callback: () => {
                frappe.show_alert({ message: 'Post updated', indicator: 'green' });
                if (window.cur_dialog) cur_dialog.hide();
                this.fetchAll(true).then(() => this.renderView(this.state.activeView));
            }
        });
    }

    quickApprove(name) {
        frappe.call({
            method: 'frappe.client.set_value',
            args: { doctype: 'Social Post', name, fieldname: { status: 'Approved', approved_by: frappe.session.user, approval_date: frappe.datetime.now_datetime() } },
            callback: () => {
                frappe.show_alert({ message: 'Post approved', indicator: 'green' });
                this.fetchAll(true).then(() => this.renderView(this.state.activeView));
            }
        });
    }

    deletePost(name) {
        frappe.confirm('Delete this draft post?', () => {
            frappe.call({
                method: 'frappe.client.delete',
                args: { doctype: 'Social Post', name },
                callback: () => {
                    frappe.show_alert({ message: 'Post deleted', indicator: 'orange' });
                    this.fetchAll(true).then(() => this.renderPostList());
                }
            });
        });
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW: CALENDAR
    // ═══════════════════════════════════════════════════════════════════════════
    renderCalendar() {
        const d   = this.state.calDate;
        const yr  = d.getFullYear();
        const mo  = d.getMonth();
        const months = ['January','February','March','April','May','June','July','August','September','October','November','December'];
        const days   = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];

        const firstDay = new Date(yr, mo, 1).getDay();
        const daysIn   = new Date(yr, mo+1, 0).getDate();
        const today    = new Date();

        // Map posts to day numbers
        const byDay = {};
        this.state.posts.forEach(p => {
            const dt = (p.global_schedule||'').split(' ')[0];
            if (!dt) return;
            const [py,pm2,pd] = dt.split('-').map(Number);
            if (py===yr && pm2-1===mo) {
                if (!byDay[pd]) byDay[pd] = [];
                byDay[pd].push(p);
            }
        });

        let cells = '';
        let cell  = 0;
        for (let i = 0; i < firstDay; i++) { cells += `<div class="smm-cal-cell other-month"></div>`; cell++; }
        for (let i = 1; i <= daysIn; i++) {
            const isToday = i === today.getDate() && mo === today.getMonth() && yr === today.getFullYear();
            const dayPosts = byDay[i] || [];
            cells += `
            <div class="smm-cal-cell ${isToday?'today':''}" onclick="window.__smm.calDayClick(${i},${mo+1},${yr})">
                <div class="smm-cal-num">${i}</div>
                ${dayPosts.slice(0,3).map(p => {
                    const meta = sm(p.status);
                    return `<div class="smm-cal-pill" style="background:${meta.col}" title="${esc(p.post_title)}" onclick="event.stopPropagation();__smm.openPostDetail('${p.name}')">${esc(p.post_title)}</div>`;
                }).join('')}
                ${dayPosts.length > 3 ? `<div style="font-size:9px;color:var(--tx3)">+${dayPosts.length-3}</div>` : ''}
            </div>`;
            cell++;
        }
        while (cell % 7 !== 0) { cells += `<div class="smm-cal-cell other-month"></div>`; cell++; }

        // Legend
        const legendItems = [['Published','var(--grn)'],['Scheduled','var(--pri2)'],['Pending','var(--amb)'],['Failed','var(--red)'],['Draft','var(--tx3)']];

        this.setContent(`
        <div style="animation:fadeIn .3s ease">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;flex-wrap:wrap;gap:12px">
                <div>
                    <h2 style="font-size:20px;font-weight:800;color:var(--tx1);margin:0 0 4px">Content Calendar</h2>
                    <div style="font-size:12px;color:var(--tx3)">Plan, schedule and visualise your content pipeline</div>
                </div>
                <div class="smm-btns">
                    <button class="smm-btn btn-ghost" onclick="window.__smm.calNav(-1)">← Prev</button>
                    <button class="smm-btn btn-ghost" onclick="window.__smm.calToday()">Today</button>
                    <button class="smm-btn btn-ghost" onclick="window.__smm.calNav(1)">Next →</button>
                    <button class="smm-btn btn-primary" onclick="window.__smm.openCompose()"><i class="fa-solid fa-plus"></i> New Post</button>
                </div>
            </div>

            <div class="smm-card">
                <div class="smm-card-head">
                    <div style="font-size:18px;font-weight:800;color:var(--tx1)">${months[mo]} ${yr}</div>
                    <div style="display:flex;gap:12px;flex-wrap:wrap">
                        ${legendItems.map(([l,c]) => `<span style="display:flex;align-items:center;gap:5px;font-size:11px;color:var(--tx3)"><span style="width:10px;height:10px;border-radius:2px;background:${c}"></span>${l}</span>`).join('')}
                    </div>
                </div>
                <div style="padding:14px">
                    <div class="smm-cal-grid">
                        ${days.map(d => `<div class="smm-cal-day-name">${d}</div>`).join('')}
                        ${cells}
                    </div>
                </div>
            </div>
        </div>
        `);
    }

    calNav(dir)  { this.state.calDate = new Date(this.state.calDate.getFullYear(), this.state.calDate.getMonth() + dir, 1); this.renderCalendar(); }
    calToday()   { this.state.calDate = new Date(); this.renderCalendar(); }
    calDayClick(d, m, y) {
        const dateStr = `${y}-${String(m).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
        this.state.composeDraft = { global_schedule: dateStr + 'T09:00', publish_strategy: 'Schedule Global' };
        this.switchView('compose');
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW: INBOX (Unified comment management)
    // ═══════════════════════════════════════════════════════════════════════════
    renderInbox() {
        const comments = this.state.comments;
        const newC     = comments.filter(c => c.status === 'New');
        const flagged  = comments.filter(c => c.is_flagged);
        const sentPos  = comments.filter(c => ['Positive','Very Positive'].includes(c.sentiment_label)).length;
        const sentNeg  = comments.filter(c => ['Negative','Very Negative'].includes(c.sentiment_label)).length;
        const sentNeu  = comments.length - sentPos - sentNeg;
        const total    = comments.length || 1;

        // Sentiment ring
        const ringC = 2 * Math.PI * 28;
        const ringOff = ringC * (1 - sentPos/total);

        this.setContent(`
        <div style="animation:fadeIn .3s ease">
            <div class="smm-g21">
                <!-- Comment feed -->
                <div class="smm-card">
                    <div class="smm-card-head">
                        <div class="smm-card-title">
                            <div class="smm-title-icon" style="background:var(--acc_x);color:var(--acc)"><i class="fa-solid fa-inbox"></i></div>
                            Comment Inbox (${comments.length})
                        </div>
                        <div class="smm-btns">
                            <span class="smm-badge bd-red">${newC.length} new</span>
                            <select class="smm-sel" id="inbox-filter" onchange="__smm.filterInbox()" style="width:auto;min-width:130px">
                                <option value="">All Comments</option>
                                <option value="New">New Only</option>
                                <option value="Flagged">Flagged</option>
                                <option value="Replied">Replied</option>
                            </select>
                        </div>
                    </div>
                    <div id="inbox-list" style="max-height:580px;overflow-y:auto">
                        ${this.buildCommentList(comments)}
                    </div>
                </div>

                <!-- Stats sidebar -->
                <div>
                    <div class="smm-card smm-row">
                        <div class="smm-card-head">
                            <div class="smm-card-title">
                                <div class="smm-title-icon" style="background:var(--grn_x);color:var(--grn)"><i class="fa-solid fa-face-smile"></i></div>
                                Sentiment
                            </div>
                        </div>
                        <div style="padding:16px;display:flex;align-items:center;gap:16px">
                            <div class="smm-ring-wrap">
                                <svg width="80" height="80" viewBox="0 0 80 80">
                                    <circle cx="40" cy="40" r="28" fill="none" stroke="rgba(255,255,255,.1)" stroke-width="8"/>
                                    <circle cx="40" cy="40" r="28" fill="none" stroke="var(--grn)" stroke-width="8"
                                        stroke-dasharray="${ringC.toFixed(1)}" stroke-dashoffset="${ringOff.toFixed(1)}"
                                        stroke-linecap="round" transform="rotate(-90 40 40)"/>
                                </svg>
                                <div class="smm-ring-label">
                                    <div class="smm-ring-pct">${Math.round(sentPos/total*100)}%</div>
                                    <div class="smm-ring-sub">Pos</div>
                                </div>
                            </div>
                            <div style="flex:1">
                                ${[['Positive',sentPos,'var(--grn)'],['Neutral',sentNeu,'var(--amb)'],['Negative',sentNeg,'var(--red)']].map(([l,n,c])=>`
                                <div style="display:flex;align-items:center;gap:8px;margin-bottom:7px">
                                    <div style="width:8px;height:8px;border-radius:50%;background:${c}"></div>
                                    <span style="font-size:11px;color:var(--tx2);flex:1">${l}</span>
                                    <span style="font-size:12px;font-weight:700;color:var(--tx1)">${n}</span>
                                </div>`).join('')}
                            </div>
                        </div>
                    </div>

                    <div class="smm-card smm-row">
                        <div class="smm-card-head">
                            <div class="smm-card-title">
                                <div class="smm-title-icon" style="background:var(--red_x);color:var(--red)"><i class="fa-solid fa-flag"></i></div>
                                Flagged (${flagged.length})
                            </div>
                        </div>
                        <div style="max-height:200px;overflow-y:auto">
                            ${flagged.length ? flagged.slice(0,5).map(c => `
                            <div style="padding:10px 14px;border-bottom:1px solid var(--brd)">
                                <div style="font-size:11px;font-weight:600;color:var(--red)">⚑ ${esc(c.author_name)}</div>
                                <div style="font-size:11px;color:var(--tx3)">${esc((c.comment_text||'').replace(/<[^>]+>/g,'').substring(0,60))}…</div>
                                <div style="font-size:10px;color:var(--tx3);margin-top:3px">${c.platform||'—'}</div>
                            </div>`).join('') : '<div style="padding:16px;text-align:center;font-size:12px;color:var(--tx3)">No flagged comments</div>'}
                        </div>
                    </div>

                    <div class="smm-card">
                        <div class="smm-card-head">
                            <div class="smm-card-title">
                                <div class="smm-title-icon" style="background:var(--sky_x);color:var(--sky)"><i class="fa-brands fa-connectdevelop"></i></div>
                                By Platform
                            </div>
                        </div>
                        <div style="padding:14px 16px">
                            ${[...new Set(comments.map(c=>c.platform).filter(Boolean))].map(plat => {
                                const n = comments.filter(c=>c.platform===plat).length;
                                const pi = pm(plat);
                                return `<div class="smm-bar-row">
                                    <div class="smm-bar-lbl"><i class="${pi.icon}" style="color:${pi.col}"></i> ${plat}</div>
                                    <div class="smm-bar"><div class="smm-bar-fill" style="width:${Math.round(n/total*100)}%;background:${pi.col}"></div></div>
                                    <div class="smm-bar-val">${n}</div>
                                </div>`;
                            }).join('') || '<div style="font-size:12px;color:var(--tx3);padding:8px 0">No data</div>'}
                        </div>
                    </div>
                </div>
            </div>
        </div>`);
    }

    buildCommentList(comments) {
        if (!comments.length) return '<div class="smm-empty"><div class="smm-empty-icon">💬</div><h4>No comments</h4></div>';
        return comments.map(c => {
            const platMeta = pm(c.platform||'Other');
            const sentMeta = { 'Very Positive':'var(--grn)', 'Positive':'var(--grn)', 'Neutral':'var(--amb)', 'Negative':'var(--red)', 'Very Negative':'var(--red)', 'Spam':'var(--tx3)' };
            const sCol = sentMeta[c.sentiment_label] || 'var(--tx3)';
            const initials = (c.author_name||'?').split(' ').map(w=>w[0]).join('').substring(0,2).toUpperCase();
            const isNew = c.status === 'New';
            return `
            <div class="smm-comment" style="${isNew?'border-left:3px solid var(--pri);padding-left:15px':''}" id="comment-${c.name}">
                <div class="smm-avatar" style="background:${platMeta.col}">${initials}</div>
                <div class="smm-comment-body">
                    <div class="smm-comment-head">
                        <span class="smm-comment-author">${esc(c.author_name)}</span>
                        <span class="smm-badge" style="background:${platMeta.col}22;color:${platMeta.col};font-size:9px">${c.platform||'—'}</span>
                        <span class="smm-badge" style="background:${sCol}22;color:${sCol};font-size:9px">${c.sentiment_label||'Neutral'}</span>
                        ${isNew ? '<span class="smm-badge bd-pri">New</span>' : ''}
                        ${c.is_flagged ? '<span class="smm-badge bd-red">⚑ Flagged</span>' : ''}
                        <span class="smm-comment-time">${c.comment_time ? frappe.datetime.prettyDate(c.comment_time) : ''}</span>
                        ${flt(c.like_count) > 0 ? `<span style="font-size:10px;color:var(--tx3)">❤ ${c.like_count}</span>` : ''}
                    </div>
                    <div class="smm-comment-text">${esc((c.comment_text||'').replace(/<[^>]+>/g,''))}</div>
                    ${c.reply_text ? `<div style="font-size:11px;color:var(--tx3);background:var(--pri_x);border-radius:6px;padding:6px 9px;border-left:2px solid var(--pri);margin-top:4px">↩ ${esc(c.reply_text.replace(/<[^>]+>/g,''))}</div>` : ''}
                    <div class="smm-btns" style="margin-top:6px">
                        <button class="smm-btn btn-ghost btn-xs" onclick="window.__smm.openReplyDialog('${c.name}','${esc(c.author_name)}','${c.parent}')"><i class="fa-solid fa-reply"></i> Reply</button>
                        ${isNew ? `<button class="smm-btn btn-grn btn-xs" onclick="window.__smm.markCommentRead('${c.name}')">Mark Read</button>` : ''}
                        ${!c.is_flagged ? `<button class="smm-btn btn-red btn-xs" onclick="window.__smm.flagComment('${c.name}')"><i class="fa-solid fa-flag"></i> Flag</button>` : ''}
                    </div>
                </div>
            </div>`;
        }).join('');
    }

    filterInbox() {
        const filter = document.getElementById('inbox-filter')?.value;
        let comments = this.state.comments;
        if (filter === 'New')     comments = comments.filter(c => c.status === 'New');
        if (filter === 'Flagged') comments = comments.filter(c => c.is_flagged);
        if (filter === 'Replied') comments = comments.filter(c => c.status === 'Replied');
        document.getElementById('inbox-list').innerHTML = this.buildCommentList(comments);
    }

    // ─── COMMENT HELPERS ─────────────────────────────────────────────────────
    // Social Post Comment is a child table of Social Post.
    // set_value doesn't work on child rows — must get parent, mutate, save.
    _updateComment(commentName, postName, updates) {
        // postName = parent Social Post. If not provided, find it from state.
        const parentName = postName || (this.state.comments.find(c => c.name === commentName) || {}).parent;
        if (!parentName) {
            frappe.show_alert({ message: 'Cannot find parent post for this comment', indicator: 'red' });
            return Promise.reject('no parent');
        }
        return frappe.call({
            method: 'frappe.client.get',
            args: { doctype: 'Social Post', name: parentName }
        }).then(r => {
            if (!r.message) throw new Error('Post not found');
            const doc = r.message;
            const row = (doc.comments || []).find(c => c.name === commentName);
            if (!row) throw new Error('Comment row not found in post');
            Object.assign(row, updates);
            return frappe.call({ method: 'frappe.client.save', args: { doc } });
        });
    }

    openReplyDialog(commentName, authorName, postName) {
        const d = new frappe.ui.Dialog({
            title: `↩ Reply to ${authorName}`,
            fields: [
                { fieldtype:'Small Text', fieldname:'reply', label:`Your reply to ${authorName}`, reqd:1 }
            ],
            primary_action_label: 'Send Reply',
            primary_action: (vals) => {
                this._updateComment(commentName, postName, {
                    reply_text:   vals.reply,
                    replied_by:   frappe.session.user,
                    reply_time:   frappe.datetime.now_datetime(),
                    reply_status: 'Sent',
                    status:       'Replied'
                }).then(() => {
                    d.hide();
                    frappe.show_alert({ message: 'Reply saved', indicator: 'green' });
                    this.fetchAll(true).then(() => this.renderInbox());
                }).catch(e => {
                    frappe.show_alert({ message: 'Could not save reply: ' + (e.message||e), indicator: 'red' });
                });
            }
        });
        d.show();
    }

    markCommentRead(name) {
        this._updateComment(name, null, { status: 'Read' })
            .then(() => {
                frappe.show_alert({ message: 'Marked as read', indicator: 'green' });
                this.fetchAll(true).then(() => this.renderInbox());
            })
            .catch(e => frappe.show_alert({ message: 'Error: ' + (e.message||e), indicator: 'red' }));
    }

    flagComment(name) {
        this._updateComment(name, null, { is_flagged: 1, status: 'Flagged' })
            .then(() => {
                frappe.show_alert({ message: 'Comment flagged', indicator: 'orange' });
                this.fetchAll(true).then(() => this.renderInbox());
            })
            .catch(e => frappe.show_alert({ message: 'Error: ' + (e.message||e), indicator: 'red' }));
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW: ANALYTICS
    // ═══════════════════════════════════════════════════════════════════════════
    renderAnalytics() {
        const p = this.state.posts.filter(x => x.status === 'Published');
        const totalReach  = p.reduce((s,x)=>s+flt(x.total_reach),0);
        const totalClicks = p.reduce((s,x)=>s+flt(x.total_clicks),0);
        const totalConv   = p.reduce((s,x)=>s+flt(x.total_conversions),0);
        const totalRev    = p.reduce((s,x)=>s+flt(x.revenue_generated),0);
        const totalLikes  = p.reduce((s,x)=>s+flt(x.total_likes),0);
        const totalShares = p.reduce((s,x)=>s+flt(x.total_shares),0);

        const byType = {};
        p.forEach(x => {
            if (!byType[x.content_type]) byType[x.content_type] = { reach:0, engage:0, count:0 };
            byType[x.content_type].reach   += flt(x.total_reach);
            byType[x.content_type].engage  += flt(x.total_likes)+flt(x.total_comments)+flt(x.total_shares);
            byType[x.content_type].count   += 1;
        });

        const topPosts = p.sort((a,b)=>flt(b.total_reach)-flt(a.total_reach)).slice(0,5);

        this.setContent(`
        <div style="animation:fadeIn .3s ease">
            <div class="smm-kpis">
                <div class="smm-kpi" style="--kc:var(--pri)"><div class="smm-kpi-icon">👁</div><div class="smm-kpi-lbl">Total Reach</div><div class="smm-kpi-val">${numK(totalReach)}</div><div class="smm-kpi-sub">Published posts</div></div>
                <div class="smm-kpi" style="--kc:var(--acc)"><div class="smm-kpi-icon">❤</div><div class="smm-kpi-lbl">Likes</div><div class="smm-kpi-val">${numK(totalLikes)}</div><div class="smm-kpi-sub">All platforms</div></div>
                <div class="smm-kpi" style="--kc:var(--sky)"><div class="smm-kpi-icon">🔄</div><div class="smm-kpi-lbl">Shares</div><div class="smm-kpi-val">${numK(totalShares)}</div><div class="smm-kpi-sub">Reposts / forwards</div></div>
                <div class="smm-kpi" style="--kc:var(--grn)"><div class="smm-kpi-icon">🖱</div><div class="smm-kpi-lbl">Link Clicks</div><div class="smm-kpi-val">${numK(totalClicks)}</div><div class="smm-kpi-sub">CTR ${totalReach>0?(totalClicks/totalReach*100).toFixed(2):'0'}%</div></div>
                <div class="smm-kpi" style="--kc:var(--amb)"><div class="smm-kpi-icon">🎯</div><div class="smm-kpi-lbl">Conversions</div><div class="smm-kpi-val">${numK(totalConv)}</div><div class="smm-kpi-sub">From social</div></div>
                <div class="smm-kpi" style="--kc:var(--grn)"><div class="smm-kpi-icon">💰</div><div class="smm-kpi-lbl">Revenue</div><div class="smm-kpi-val">₦${numK(totalRev)}</div><div class="smm-kpi-sub">Attributed</div></div>
            </div>

            <div class="smm-g21">
                <div>
                    <div class="smm-card smm-row">
                        <div class="smm-card-head">
                            <div class="smm-card-title"><div class="smm-title-icon" style="background:var(--pri_x);color:var(--pri2)"><i class="fa-solid fa-chart-bar"></i></div>Reach by Content Type</div>
                        </div>
                        <div style="padding:16px;height:240px;position:relative"><canvas id="smm-ch-ctype"></canvas></div>
                    </div>
                    <div class="smm-card smm-row">
                        <div class="smm-card-head">
                            <div class="smm-card-title"><div class="smm-title-icon" style="background:var(--grn_x);color:var(--grn)"><i class="fa-solid fa-filter"></i></div>Engagement Funnel</div>
                        </div>
                        <div style="padding:16px">
                            ${[
                                ['Total Reach',       totalReach,                                                                  'var(--pri)'],
                                ['Impressions',       Math.round(totalReach*1.35),                                                'var(--sky)'],
                                ['Engagements',       p.reduce((s,x)=>s+flt(x.total_likes)+flt(x.total_comments)+flt(x.total_shares),0), 'var(--acc)'],
                                ['Link Clicks',       totalClicks,                                                                'var(--amb)'],
                                ['Conversions',       totalConv,                                                                  'var(--grn)'],
                            ].map(([lbl,val,col],i,arr) => `
                            <div class="smm-bar-row">
                                <div class="smm-bar-lbl">${lbl}</div>
                                <div class="smm-bar"><div class="smm-bar-fill" style="width:${arr[0][1]>0?Math.min(Math.round(val/arr[0][1]*100),100):0}%;background:${col}"></div></div>
                                <div class="smm-bar-val">${numK(val)}</div>
                            </div>`).join('')}
                        </div>
                    </div>
                </div>
                <div>
                    <div class="smm-card smm-row">
                        <div class="smm-card-head">
                            <div class="smm-card-title"><div class="smm-title-icon" style="background:var(--sky_x);color:var(--sky)"><i class="fa-solid fa-trophy"></i></div>Top Posts</div>
                        </div>
                        <div style="padding:0">
                            ${topPosts.map((post,i) => `
                            <div style="display:flex;align-items:center;gap:10px;padding:11px 16px;border-bottom:1px solid var(--brd);cursor:pointer" onclick="window.__smm.openPostDetail('${post.name}')">
                                <div style="width:22px;height:22px;border-radius:50%;background:${i===0?'var(--amb)':i===1?'var(--tx3)':'var(--bg3)'};display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:800;color:${i<2?'#fff':'var(--tx3)'};flex-shrink:0">${i+1}</div>
                                <div style="flex:1;min-width:0">
                                    <div style="font-size:12px;font-weight:600;color:var(--tx1);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(post.post_title)}</div>
                                    <div style="font-size:10px;color:var(--tx3)">👁 ${numK(post.total_reach)} · ❤ ${numK(post.total_likes)}</div>
                                </div>
                                <div style="font-size:12px;font-weight:700;color:var(--pri2)">${flt(post.total_engagement_rate).toFixed(1)}%</div>
                            </div>`).join('') || '<div class="smm-empty" style="padding:24px"><h4>No published posts yet</h4></div>'}
                        </div>
                    </div>
                    <div class="smm-card">
                        <div class="smm-card-head">
                            <div class="smm-card-title"><div class="smm-title-icon" style="background:var(--acc_x);color:var(--acc)"><i class="fa-solid fa-clock"></i></div>Best Times (AI)</div>
                        </div>
                        <div style="padding:14px;height:180px;position:relative"><canvas id="smm-ch-heatmap"></canvas></div>
                        <div class="smm-ai-card" style="margin:0 14px 14px">
                            <h4>Recommendation</h4>
                            <div class="smm-ai-item"><div class="smm-ai-dot"></div>Post on Instagram: 9–11 AM Tuesday/Thursday</div>
                            <div class="smm-ai-item"><div class="smm-ai-dot"></div>LinkedIn performs best: 12–2 PM on Tue–Thu</div>
                            <div class="smm-ai-item"><div class="smm-ai-dot"></div>Twitter/X engagement peaks: 6–9 PM weekdays</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>`);

        setTimeout(() => {
            const typeEntries = Object.entries(byType).sort((a,b) => b[1].reach - a[1].reach);
            this.mkChart('smm-ch-ctype', {
                type:'bar',
                data:{ labels:typeEntries.map(([t])=>t), datasets:[
                    { label:'Reach',data:typeEntries.map(([,v])=>v.reach),backgroundColor:'rgba(99,102,241,.7)',borderRadius:5 },
                    { label:'Engagements',data:typeEntries.map(([,v])=>v.engage),backgroundColor:'rgba(244,114,182,.7)',borderRadius:5 }
                ]},
                options:{ responsive:true,maintainAspectRatio:false,
                    plugins:{legend:{position:'bottom',labels:{color:'#4A5680',boxWidth:10,font:{size:10}}}},
                    scales:{x:{grid:{color:'rgba(255,255,255,.04)'},ticks:{color:'#4A5680',font:{size:10}}},
                            y:{grid:{color:'rgba(255,255,255,.04)'},ticks:{color:'#4A5680',font:{size:10},callback:v=>numK(v)}}}}
            });
            this.mkChart('smm-ch-heatmap', {
                type:'radar',
                data:{labels:['6AM','9AM','12PM','3PM','6PM','9PM'],
                    datasets:[{label:'Engagement',data:[30,85,65,55,90,70],borderColor:'#6366F1',backgroundColor:'rgba(99,102,241,.15)',borderWidth:2,pointBackgroundColor:'#6366F1',pointRadius:4}]},
                options:{responsive:true,maintainAspectRatio:false,
                    plugins:{legend:{display:false}},
                    scales:{r:{grid:{color:'rgba(255,255,255,.06)'},ticks:{color:'#4A5680',font:{size:9},backdropColor:'transparent'},pointLabels:{color:'#8B96C0',font:{size:10}}}}}
            });
        }, 100);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW: ACCOUNTS (Platform management with full CRUD)
    // ═══════════════════════════════════════════════════════════════════════════
    renderAccounts() {
        const accounts = this.state.accounts;

        this.setContent(`
        <div style="animation:fadeIn .3s ease">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;flex-wrap:wrap;gap:12px">
                <div>
                    <h2 style="font-size:20px;font-weight:800;color:var(--tx1);margin:0 0 4px">Platform Accounts</h2>
                    <div style="font-size:12px;color:var(--tx3)">Manage all connected social media accounts in one place</div>
                </div>
                <button class="smm-btn btn-primary" onclick="window.__smm.openAddAccount()"><i class="fa-solid fa-plus"></i> Connect Account</button>
            </div>

            <div class="smm-g3">
                ${accounts.map(acc => this.buildAccountCard(acc)).join('')}
                <div class="smm-account-card" onclick="window.__smm.openAddAccount()"
                     style="border:2px dashed var(--brd2);background:transparent;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:180px;gap:10px">
                    <div style="width:44px;height:44px;border-radius:12px;background:var(--pri_x);display:flex;align-items:center;justify-content:center;color:var(--pri2);font-size:20px">+</div>
                    <div style="font-size:13px;font-weight:600;color:var(--pri2)">Connect Platform</div>
                    <div style="font-size:11px;color:var(--tx3)">Facebook, Instagram, LinkedIn…</div>
                </div>
            </div>
        </div>`);
    }

    buildAccountCard(acc) {
        const pi = pm(acc.platform);
        const statusColors = { 'Connected':'var(--grn)','Disconnected':'var(--tx3)','Token Expired':'var(--red)','Rate Limited':'var(--amb)','API Error':'var(--red)','Pending Verification':'var(--sky)' };
        const sc = statusColors[acc.account_status] || 'var(--tx3)';
        const apiPct = acc.api_rate_limit && acc.api_calls_made_today ? Math.round(flt(acc.api_calls_made_today)/flt(acc.api_rate_limit)*100) : 0;
        return `
        <div class="smm-account-card">
            <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:12px">
                <div class="smm-account-avatar" style="background:${pi.col}">
                    <i class="${pi.icon}"></i>
                </div>
                <div style="display:flex;align-items:center;gap:5px">
                    <div style="width:6px;height:6px;border-radius:50%;background:${sc}"></div>
                    <span style="font-size:10px;color:${sc}">${acc.account_status||'Unknown'}</span>
                </div>
            </div>
            <div class="smm-account-name">${esc(acc.account_name)}</div>
            <div class="smm-account-sub">${acc.platform} · ${acc.account_type||'Business'}</div>
            ${acc.token_expiry_date ? `
            <div style="font-size:10px;color:${frappe.datetime.get_diff(acc.token_expiry_date, frappe.datetime.get_today()) < 7 ? 'var(--red)' : 'var(--tx3)'};margin-bottom:8px">
                Token expires: ${frappe.datetime.str_to_user(acc.token_expiry_date)}
            </div>` : ''}
            ${apiPct > 0 ? `
            <div style="margin-bottom:8px">
                <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--tx3);margin-bottom:3px">
                    <span>API Usage</span><span>${acc.api_calls_made_today||0}/${acc.api_rate_limit||'∞'}</span>
                </div>
                <div style="height:4px;background:var(--brd2);border-radius:10px;overflow:hidden">
                    <div style="width:${Math.min(apiPct,100)}%;height:100%;background:${apiPct>80?'var(--red)':apiPct>60?'var(--amb)':'var(--grn)'}"></div>
                </div>
            </div>` : ''}
            <div style="display:flex;gap:7px;margin-top:auto">
                <button class="smm-btn btn-ghost btn-sm" style="flex:1;justify-content:center" onclick="window.__smm.editAccount('${acc.name}')"><i class="fa-solid fa-gear"></i> Settings</button>
                <button class="smm-btn btn-primary btn-sm" style="flex:1;justify-content:center" onclick="window.__smm.openCompose()"><i class="fa-solid fa-plus"></i> Post</button>
            </div>
        </div>`;
    }

    openAddAccount() {
        const d = new frappe.ui.Dialog({
            title: '🔗 Connect Platform Account',
            size: 'large',
            fields: [
                { fieldtype:'Select', fieldname:'platform', label:'Platform', reqd:1,
                  options:[...Object.keys(PLAT_META)].join('\n') },
                { fieldtype:'Data', fieldname:'account_name', label:'Account Name / Page Name', reqd:1 },
                { fieldtype:'Column Break' },
                { fieldtype:'Data', fieldname:'account_id', label:'Account ID / Page ID' },
                { fieldtype:'Select', fieldname:'account_type', label:'Account Type', default:'Business',
                  options:'\nPersonal\nBusiness\nCreator\nOrganization\nPage\nGroup' },
                { fieldtype:'Section Break', label:'API Credentials' },
                { fieldtype:'Password', fieldname:'api_key', label:'API Key / App ID' },
                { fieldtype:'Password', fieldname:'api_secret', label:'API Secret' },
                { fieldtype:'Column Break' },
                { fieldtype:'Password', fieldname:'access_token', label:'Access Token' },
                { fieldtype:'Date', fieldname:'token_expiry_date', label:'Token Expiry Date' },
                { fieldtype:'Section Break', label:'Permissions' },
                { fieldtype:'Check', fieldname:'can_post', label:'Can Post Content', default:1 },
                { fieldtype:'Check', fieldname:'can_read_inbox', label:'Can Read Inbox', default:1 },
                { fieldtype:'Column Break' },
                { fieldtype:'Check', fieldname:'can_read_analytics', label:'Can Read Analytics', default:1 },
                { fieldtype:'Check', fieldname:'is_active', label:'Is Active', default:1 },
                { fieldtype:'Section Break', label:'Sync Settings' },
                { fieldtype:'Select', fieldname:'sync_frequency', label:'Sync Frequency', default:'Every 6 Hours',
                  options:'\nEvery Hour\nEvery 3 Hours\nEvery 6 Hours\nEvery 12 Hours\nDaily\nManual Only' },
                { fieldtype:'Check', fieldname:'sync_comments', label:'Sync Comments', default:1 },
                { fieldtype:'Check', fieldname:'auto_sync_enabled', label:'Auto-Sync Enabled', default:1 },
            ],
            primary_action_label: '✅ Connect Account',
            primary_action: (vals) => {
                // Add to settings platform_accounts table
                const settings = this.state.settings;
                if (!settings) { frappe.show_alert({ message:'Social Media Settings not found', indicator:'red' }); return; }
                frappe.call({
                    method: 'frappe.client.get',
                    args: { doctype: 'Social Media Settings', name: 'Social Media Settings' },
                    callback: (r) => {
                        if (!r.message) return;
                        const doc = r.message;
                        doc.platform_accounts = doc.platform_accounts || [];
                        doc.platform_accounts.push({ ...vals, account_status: 'Connected' });
                        frappe.call({
                            method: 'frappe.client.save',
                            args: { doc },
                            callback: () => {
                                d.hide();
                                frappe.show_alert({ message: 'Platform connected', indicator: 'green' });
                                this.fetchAll(true).then(() => this.renderAccounts());
                            }
                        });
                    }
                });
            }
        });
        d.show();
    }

    editAccount(name) {
        const acc = this.state.accounts.find(a => a.name === name);
        if (!acc) { frappe.set_route('Form', 'Social Media Settings', 'Social Media Settings'); return; }
        const d = new frappe.ui.Dialog({
            title: `⚙️ ${acc.account_name} — Settings`,
            size: 'large',
            fields: [
                { fieldtype:'Select', fieldname:'account_status', label:'Account Status', default:acc.account_status||'Connected',
                  options:'\nConnected\nDisconnected\nToken Expired\nRate Limited\nAPI Error\nPending Verification' },
                { fieldtype:'Date', fieldname:'token_expiry_date', label:'Token Expiry Date', default:acc.token_expiry_date||'' },
                { fieldtype:'Column Break' },
                { fieldtype:'Select', fieldname:'sync_frequency', label:'Sync Frequency', default:acc.sync_frequency||'Every 6 Hours',
                  options:'\nEvery Hour\nEvery 3 Hours\nEvery 6 Hours\nEvery 12 Hours\nDaily\nManual Only' },
                { fieldtype:'Int', fieldname:'api_rate_limit', label:'API Rate Limit', default:acc.api_rate_limit||100 },
                { fieldtype:'Section Break', label:'Permissions' },
                { fieldtype:'Check', fieldname:'can_post', label:'Can Post', default:acc.can_post||1 },
                { fieldtype:'Check', fieldname:'sync_comments', label:'Sync Comments', default:acc.sync_comments||1 },
                { fieldtype:'Column Break' },
                { fieldtype:'Check', fieldname:'can_read_analytics', label:'Read Analytics', default:acc.can_read_analytics||1 },
                { fieldtype:'Check', fieldname:'is_active', label:'Is Active', default:acc.is_active||1 },
                { fieldtype:'Section Break', label:'Limits' },
                { fieldtype:'Int', fieldname:'character_limit', label:'Character Limit', default:acc.character_limit||2200 },
                { fieldtype:'Int', fieldname:'hashtag_limit', label:'Hashtag Limit', default:acc.hashtag_limit||30 },
                { fieldtype:'Column Break' },
                { fieldtype:'Float', fieldname:'max_image_size_mb', label:'Max Image Size (MB)', default:acc.max_image_size_mb||10 },
                { fieldtype:'Int', fieldname:'max_video_length_sec', label:'Max Video Length (sec)', default:acc.max_video_length_sec||60 },
            ],
            primary_action_label: '💾 Save Changes',
            primary_action: (vals) => {
                frappe.call({
                    method: 'frappe.client.get',
                    args: { doctype: 'Social Media Settings', name: 'Social Media Settings' },
                    callback: (r) => {
                        if (!r.message) return;
                        const doc = r.message;
                        const idx = (doc.platform_accounts||[]).findIndex(a => a.name === name);
                        if (idx >= 0) {
                            doc.platform_accounts[idx] = { ...doc.platform_accounts[idx], ...vals };
                            frappe.call({
                                method: 'frappe.client.save',
                                args: { doc },
                                callback: () => {
                                    d.hide();
                                    frappe.show_alert({ message: 'Account updated', indicator: 'green' });
                                    this.fetchAll(true).then(() => this.renderAccounts());
                                }
                            });
                        }
                    }
                });
            }
        });
        d.show();
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  VIEW: SETTINGS (Full settings management)
    // ═══════════════════════════════════════════════════════════════════════════
    renderSettings() {
        const s = this.state.settings || {};

        this.setContent(`
        <div style="animation:fadeIn .3s ease">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px">
                <div>
                    <h2 style="font-size:20px;font-weight:800;color:var(--tx1);margin:0 0 4px">SMM Settings</h2>
                    <div style="font-size:12px;color:var(--tx3)">Configure your social media management platform</div>
                </div>
                <button class="smm-btn btn-primary" onclick="window.__smm.saveSettings()"><i class="fa-solid fa-floppy-disk"></i> Save All Settings</button>
            </div>

            <div class="smm-g2">
                <!-- General Settings -->
                <div class="smm-card smm-row">
                    <div class="smm-card-head">
                        <div class="smm-card-title"><div class="smm-title-icon" style="background:var(--pri_x);color:var(--pri2)"><i class="fa-solid fa-gear"></i></div>General</div>
                    </div>
                    <div style="padding:16px 20px">
                        <div class="smm-settings-section">
                            <div class="smm-form">
                                <div class="smm-fg">
                                    <label>Company Name</label>
                                    <input class="smm-inp" id="set-company" value="${esc(s.company_name||'My Company')}">
                                </div>
                                <div class="smm-fg">
                                    <label>Default Timezone</label>
                                    <select class="smm-sel" id="set-timezone">
                                        ${['UTC','America/New_York','Europe/London','Africa/Lagos','Asia/Dubai','Asia/Singapore'].map(tz=>`<option ${(s.default_timezone||'UTC')===tz?'selected':''}>${tz}</option>`).join('')}
                                    </select>
                                </div>
                            </div>
                        </div>
                        <div class="smm-settings-section">
                            <h3>Publishing</h3>
                            ${this.toggleRow('set-approval','post_approval_required',s,'Approval Required','New posts need approval before publishing')}
                            ${this.toggleRow('set-autopublish','auto_publish_enabled',s,'Auto-Publish','Automatically publish at scheduled time')}
                            ${this.toggleRow('set-optimize','default_content_optimization',s,'Content Optimization','Optimize content for each platform')}
                        </div>
                    </div>
                </div>

                <!-- AI / Intelligence -->
                <div class="smm-card smm-row">
                    <div class="smm-card-head">
                        <div class="smm-card-title"><div class="smm-title-icon" style="background:var(--pur-x,var(--pri_x));color:var(--pri2)"><i class="fa-solid fa-robot"></i></div>AI & Intelligence</div>
                    </div>
                    <div style="padding:16px 20px">
                        <div class="smm-settings-section">
                            ${this.toggleRow('set-ai-suggestions','ai_content_suggestions',s,'AI Content Suggestions','Auto-suggest captions and content ideas')}
                            ${this.toggleRow('set-hashtags','auto_hashtag_generation',s,'Auto Hashtag Generation','AI-generated hashtags per post and platform')}
                            ${this.toggleRow('set-sentiment','sentiment_analysis_enabled',s,'Sentiment Analysis','Analyse comment sentiment automatically')}
                            ${this.toggleRow('set-competitor','competitor_tracking_enabled',s,'Competitor Tracking','Monitor competitor account performance')}
                        </div>
                    </div>
                </div>

                <!-- Notifications -->
                <div class="smm-card smm-row">
                    <div class="smm-card-head">
                        <div class="smm-card-title"><div class="smm-title-icon" style="background:var(--amb_x);color:var(--amb)"><i class="fa-solid fa-bell"></i></div>Notifications</div>
                    </div>
                    <div style="padding:16px 20px">
                        <div class="smm-settings-section">
                            ${this.toggleRow('set-notif-comment','notify_on_new_comment',s,'New Comments','Alert when a new comment is received')}
                            ${this.toggleRow('set-notif-message','notify_on_new_message',s,'New Messages','Alert on new direct messages')}
                            ${this.toggleRow('set-notif-failure','notify_on_post_failure',s,'Post Failures','Alert when a post fails to publish')}
                            ${this.toggleRow('set-email','email_notifications',s,'Email Notifications','Send alerts via email')}
                            ${this.toggleRow('set-desktop','desktop_notifications',s,'Desktop Notifications','Browser push notifications')}
                        </div>
                        <div class="smm-settings-section">
                            <h3>Slack Integration</h3>
                            <div class="smm-fg">
                                <label>Slack Webhook URL</label>
                                <input class="smm-inp" id="set-slack" placeholder="https://hooks.slack.com/services/…" value="${esc(s.slack_webhook_url||'')}">
                            </div>
                        </div>
                    </div>
                </div>

                <!-- API / Webhooks -->
                <div class="smm-card smm-row">
                    <div class="smm-card-head">
                        <div class="smm-card-title"><div class="smm-title-icon" style="background:var(--sky_x);color:var(--sky)"><i class="fa-solid fa-plug"></i></div>API & Webhooks</div>
                    </div>
                    <div style="padding:16px 20px">
                        <div class="smm-form">
                            <div class="smm-fg-row">
                                <div class="smm-fg">
                                    <label>API Timeout (seconds)</label>
                                    <input class="smm-inp" id="set-timeout" type="number" value="${s.api_timeout_seconds||30}">
                                </div>
                                <div class="smm-fg">
                                    <label>Max Retry Attempts</label>
                                    <input class="smm-inp" id="set-retry" type="number" value="${s.max_retry_attempts||3}">
                                </div>
                            </div>
                            <div class="smm-fg">
                                <label>Global Rate Limit (req/min)</label>
                                <input class="smm-inp" id="set-ratelimit" type="number" value="${s.global_rate_limit||60}">
                            </div>
                            <div class="smm-fg">
                                <label>Webhook Base URL</label>
                                <input class="smm-inp" id="set-webhook-url" placeholder="https://your-site.com" value="${esc(s.webhook_base_url||'')}">
                            </div>
                        </div>
                        <hr class="smm-divider">
                        ${this.toggleRow('set-webhooks','enable_webhooks',s,'Enable Webhooks','Real-time event delivery via webhooks')}
                    </div>
                </div>
            </div>

            <!-- Notification Recipients -->
            <div class="smm-card smm-row">
                <div class="smm-card-head">
                    <div class="smm-card-title"><div class="smm-title-icon" style="background:var(--acc_x);color:var(--acc)"><i class="fa-solid fa-users"></i></div>Notification Recipients (${(s.notification_recipients||[]).length})</div>
                    <button class="smm-btn btn-primary btn-sm" onclick="window.__smm.addNotifRecipient()"><i class="fa-solid fa-plus"></i> Add Recipient</button>
                </div>
                <div class="smm-tbl-wrap">
                    <table class="smm-tbl">
                        <thead><tr><th>Name</th><th>Email</th><th>User</th><th>Notification Types</th><th>Platform Filter</th><th>Priority</th><th>Actions</th></tr></thead>
                        <tbody id="notif-recipients-tbody">
                        ${(s.notification_recipients||[]).map((r,i) => `
                            <tr>
                                <td style="font-weight:600;color:var(--tx1)">${esc(r.recipient_name||'—')}</td>
                                <td style="font-size:11px">${esc(r.recipient_email||'—')}</td>
                                <td style="font-size:11px">${esc(r.recipient_user||'—')}</td>
                                <td style="font-size:11px;max-width:160px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(r.notification_types||'All')}</td>
                                <td style="font-size:11px">${esc(r.platform_filter||'All')}</td>
                                <td><span class="smm-badge bd-grey">${r.priority_level||'All'}</span></td>
                                <td>
                                    <button class="smm-btn btn-red btn-xs" onclick="window.__smm.removeNotifRecipient(${i})"><i class="fa-solid fa-trash"></i></button>
                                </td>
                            </tr>`).join('') || '<tr><td colspan="7" style="text-align:center;padding:20px;color:var(--tx3)">No recipients configured</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>`);
    }

    toggleRow(id, fieldname, settings, label, desc) {
        const checked = settings[fieldname] ? 'checked' : '';
        return `
        <div class="smm-toggle-row">
            <div class="smm-toggle-info">
                <h5>${label}</h5>
                <p>${desc}</p>
            </div>
            <label class="smm-toggle">
                <input type="checkbox" id="${id}" data-field="${fieldname}" ${checked}>
                <div class="smm-toggle-track"></div>
                <div class="smm-toggle-thumb"></div>
            </label>
        </div>`;
    }

    addNotifRecipient() {
        const d = new frappe.ui.Dialog({
            title: '+ Add Notification Recipient',
            fields: [
                { fieldtype:'Data',   fieldname:'recipient_name',  label:'Recipient Name',     reqd:1 },
                { fieldtype:'Data',   fieldname:'recipient_email', label:'Email',               reqd:1 },
                { fieldtype:'Column Break' },
                { fieldtype:'Link',   fieldname:'recipient_user',  label:'Linked User',         options:'User' },
                { fieldtype:'Select', fieldname:'priority_level',  label:'Priority Level', default:'All', options:'\nAll\nHigh Only\nCritical Only' },
                { fieldtype:'Small Text', fieldname:'notification_types', label:'Notification Types (comma-separated)', default:'New Comment, Post Failure' },
                { fieldtype:'Data',   fieldname:'platform_filter', label:'Platform Filter (blank = all)', placeholder:'Facebook,Instagram' },
            ],
            primary_action_label: 'Add',
            primary_action: (vals) => {
                const s = this.state.settings;
                if (!s) return;
                s.notification_recipients = s.notification_recipients || [];
                s.notification_recipients.push(vals);
                frappe.call({
                    method: 'frappe.client.save',
                    args: { doc: s },
                    callback: () => {
                        d.hide();
                        frappe.show_alert({ message: 'Recipient added', indicator: 'green' });
                        this.fetchAll(true).then(() => this.renderSettings());
                    }
                });
            }
        });
        d.show();
    }

    removeNotifRecipient(idx) {
        const s = this.state.settings;
        if (!s) return;
        frappe.confirm('Remove this notification recipient?', () => {
            s.notification_recipients.splice(idx, 1);
            frappe.call({
                method: 'frappe.client.save',
                args: { doc: s },
                callback: () => {
                    frappe.show_alert({ message: 'Recipient removed', indicator: 'orange' });
                    this.fetchAll(true).then(() => this.renderSettings());
                }
            });
        });
    }

    saveSettings() {
        const s = this.state.settings;
        if (!s) { frappe.show_alert({ message: 'Settings not loaded', indicator: 'red' }); return; }

        // Collect all toggle values
        document.querySelectorAll('[data-field]').forEach(el => {
            if (el.type === 'checkbox') s[el.dataset.field] = el.checked ? 1 : 0;
        });
        // Collect input values
        const fields = {
            company_name:     '#set-company',
            default_timezone: '#set-timezone',
            slack_webhook_url:'#set-slack',
            api_timeout_seconds:'#set-timeout',
            max_retry_attempts:'#set-retry',
            global_rate_limit: '#set-ratelimit',
            webhook_base_url:  '#set-webhook-url',
        };
        Object.entries(fields).forEach(([field, sel]) => {
            const el = document.querySelector(sel);
            if (el) s[field] = el.value;
        });

        frappe.call({
            method: 'frappe.client.save',
            args: { doc: s },
            freeze: true,
            freeze_message: 'Saving settings…',
            callback: () => {
                frappe.show_alert({ message: 'Settings saved', indicator: 'green' });
                this.fetchAll(true);
            }
        });
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  ACCOUNT DETAIL (opens form or inline dialog)
    // ═══════════════════════════════════════════════════════════════════════════
    openAccountDetail(name) {
        const acc = this.state.accounts.find(a => a.name === name);
        if (!acc) { frappe.set_route('Form', 'Social Media Settings', 'Social Media Settings'); return; }
        this.editAccount(name);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  FAB — QUICK COMPOSE
    // ═══════════════════════════════════════════════════════════════════════════
    openCompose() {
        this.state.composeDraft = {};
        this.switchView('compose');
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  HELPERS
    // ═══════════════════════════════════════════════════════════════════════════
    mkChart(id, cfg) {
        const c = document.getElementById(id);
        if (!c || typeof Chart === 'undefined') return null;
        if (this.charts[id]) { this.charts[id].destroy(); }
        this.charts[id] = new Chart(c.getContext('2d'), cfg);
        return this.charts[id];
    }
}

// ─── GLOBAL HELPERS ───────────────────────────────────────────────────────────
function esc(str) {
    return (str||'').toString()
        .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
        .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function flt(v) { return parseFloat(v) || 0; }

function numK(v) {
    const n = flt(v);
    if (n >= 1e9) return (n/1e9).toFixed(1)+'B';
    if (n >= 1e6) return (n/1e6).toFixed(1)+'M';
    if (n >= 1e3) return (n/1e3).toFixed(1)+'K';
    return Math.round(n).toLocaleString('en-NG');
}

// CSS animation for views
const fadeStyle = document.createElement('style');
fadeStyle.textContent = `
@keyframes fadeIn { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }
`;
document.head.appendChild(fadeStyle);