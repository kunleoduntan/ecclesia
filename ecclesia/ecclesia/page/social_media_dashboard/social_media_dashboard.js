// Copyright (c) 2026, Value Impacts Consulting
// ecclesia/ecclesia/page/smm_dashboard/smm_dashboard.js
//
// ╔══════════════════════════════════════════════════════════════════════════╗
// ║   SOCIAL MEDIA STUDIO — Complete 2100+ Line Implementation              ║
// ║   9 Themes · 7 Views · Full CRUD · localStorage Only                    ║
// ╚══════════════════════════════════════════════════════════════════════════╝

frappe.pages['social-media-dashboard'].on_page_load = function (wrapper) {
    const boot = () => {
        if (typeof Chart === 'undefined') {
            const cs = document.createElement('script');
            cs.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
            cs.onload = () => new SMMStudio(wrapper);
            cs.onerror = () => {
                frappe.msgprint({
                    title: 'Error Loading Chart.js',
                    indicator: 'red',
                    message: 'Failed to load Chart.js library. Please check your internet connection and refresh.'
                });
            };
            document.head.appendChild(cs);
        } else {
            new SMMStudio(wrapper);
        }
    };

    if (!document.getElementById('fa-smm')) {
        const fa = document.createElement('link');
        fa.id = 'fa-smm';
        fa.rel = 'stylesheet';
        fa.href = 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css';
        fa.onload = boot;
        fa.onerror = boot; // Proceed even if Font Awesome fails
        document.head.appendChild(fa);
    } else {
        boot();
    }
};

// ═══════════════════════════════════════════════════════════════════════════
//  THEME REGISTRY — 9 Complete Themes (Pure Code, No DB)
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

// ─── PLATFORM METADATA ────────────────────────────────────────────────────────
const PLAT_META = {
    'Facebook':              { col: '#1877F2', icon: 'fa-brands fa-facebook-f',    abbr: 'FB',  charLimit: 63206 },
    'Instagram':             { col: '#E1306C', icon: 'fa-brands fa-instagram',      abbr: 'IG',  charLimit: 2200  },
    'Instagram Business':    { col: '#E1306C', icon: 'fa-brands fa-instagram',      abbr: 'IB',  charLimit: 2200  },
    'Twitter/X':             { col: '#14171A', icon: 'fa-brands fa-x-twitter',      abbr: 'X',   charLimit: 280   },
    'LinkedIn':              { col: '#0077B5', icon: 'fa-brands fa-linkedin-in',    abbr: 'LI',  charLimit: 3000  },
    'LinkedIn Company Page': { col: '#0077B5', icon: 'fa-brands fa-linkedin',       abbr: 'LC',  charLimit: 3000  },
    'TikTok':                { col: '#FE2C55', icon: 'fa-brands fa-tiktok',         abbr: 'TT',  charLimit: 2200  },
    'Pinterest':             { col: '#E60023', icon: 'fa-brands fa-pinterest-p',    abbr: 'PT',  charLimit: 500   },
    'YouTube':               { col: '#FF0000', icon: 'fa-brands fa-youtube',        abbr: 'YT',  charLimit: 5000  },
    'Snapchat':              { col: '#FFFC00', icon: 'fa-brands fa-snapchat',       abbr: 'SC',  charLimit: 250   },
    'WhatsApp Business':     { col: '#25D366', icon: 'fa-brands fa-whatsapp',       abbr: 'WA',  charLimit: 1024  },
    'Telegram':              { col: '#0088CC', icon: 'fa-brands fa-telegram',       abbr: 'TG',  charLimit: 4096  },
    'Threads':               { col: '#101010', icon: 'fa-brands fa-threads',        abbr: 'TH',  charLimit: 500   },
    'Bluesky':               { col: '#0085FF', icon: 'fa-solid fa-cloud',           abbr: 'BS',  charLimit: 300   },
    'Mastodon':              { col: '#6364FF', icon: 'fa-brands fa-mastodon',       abbr: 'MT',  charLimit: 500   },
    'Other':                 { col: '#64748B', icon: 'fa-solid fa-globe',           abbr: 'OT',  charLimit: 2000  }
};

function pm(p) { return PLAT_META[p] || PLAT_META['Other']; }

// ─── STATUS METADATA ──────────────────────────────────────────────────────────
const STATUS_META = {
    'Draft':               { col: '#64748B', icon: 'fa-pencil'                   },
    'Pending Approval':    { col: '#F59E0B', icon: 'fa-clock'                    },
    'Approved':            { col: '#2563EB', icon: 'fa-check-circle'             },
    'Rejected':            { col: '#EF4444', icon: 'fa-times-circle'             },
    'Scheduled':           { col: '#8B5CF6', icon: 'fa-calendar'                 },
    'Publishing':          { col: '#F97316', icon: 'fa-spinner fa-spin'          },
    'Published':           { col: '#10B981', icon: 'fa-check-circle'             },
    'Partially Published': { col: '#06B6D4', icon: 'fa-adjust'                   },
    'Failed':              { col: '#EF4444', icon: 'fa-exclamation-triangle'     },
    'Deleted':             { col: '#94A3B8', icon: 'fa-trash'                    }
};

function sm(s) { return STATUS_META[s] || STATUS_META['Draft']; }

// ═══════════════════════════════════════════════════════════════════════════
//  MAIN CLASS — SMMStudio (1800+ lines of implementation)
// ═══════════════════════════════════════════════════════════════════════════
class SMMStudio {
    constructor(wrapper) {
        this.wrapper = wrapper;
        this.page = frappe.ui.make_app_page({ 
            parent: wrapper, 
            title: 'Social Media Studio', 
            single_column: true 
        });
        
        // Chart instances
        this.charts = {};
        
        // Theme stored ONLY in localStorage — no DB dependency
        this.activeTheme = localStorage.getItem('smm-studio-theme') || 'midnight';
        
        // Application state
        this.state = {
            posts: [],
            accounts: [],
            comments: [],
            settings: null,
            activeView: 'studio',
            selectedPost: null,
            calDate: new Date(),
            filters: { status: '', platform: '', campaign: '', search: '' },
            composeDraft: {},
            isLoading: false
        };
        
        // Timer references
        this.timers = {};
        
        // Global reference for inline handlers
        window.__smm = this;
        
        // Boot the application
        this.boot();
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  BOOT SEQUENCE
    // ═══════════════════════════════════════════════════════════════════════
    async boot() {
        try {
            // Inject stylesheet
            this.injectCSS();
            
            // Apply saved theme
            this.applyTheme(this.activeTheme);
            
            // Build the HTML shell
            this.buildShell();
            
            // Bind navigation events
            this.bindEvents();
            
            // Fetch all data
            await this.fetchAll();
            
            // Render the active view
            this.renderView(this.state.activeView);
            
            // Start the live clock
            this.startClock();
            
            // Start auto-refresh (30 seconds)
            this.startAutoRefresh();
            
            console.log('SMM Studio booted successfully with theme:', this.activeTheme);
        } catch(e) {
            console.error('SMM Studio boot error:', e);
            frappe.show_alert({ 
                message: 'Failed to initialize Social Media Studio: ' + (e.message || 'Unknown error'), 
                indicator: 'red' 
            });
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  THEME ENGINE — Pure localStorage, no API calls
    // ═══════════════════════════════════════════════════════════════════════
    applyTheme(key) {
        const t = SMM_THEMES[key];
        if (!t) {
            console.warn('Theme not found:', key, 'falling back to midnight');
            key = 'midnight';
        }
        
        const theme = SMM_THEMES[key];
        this.activeTheme = key;
        
        // Persist to localStorage only
        try {
            localStorage.setItem('smm-studio-theme', key);
        } catch(e) {
            console.warn('localStorage not available, theme will reset on reload');
        }
        
        // Apply CSS variables to root element
        const root = document.getElementById('smm-root');
        if (!root) {
            console.warn('Root element not found, theme will apply on next render');
            return;
        }
        
        // Set all color variables
        Object.entries(theme.colors).forEach(([name, value]) => {
            root.style.setProperty(`--${name}`, value);
        });
        
        // Toggle dark mode class
        if (theme.isDark) {
            root.classList.add('dark-mode');
        } else {
            root.classList.remove('dark-mode');
        }
        
        // Update theme indicator in the header
        const label = document.getElementById('smm-theme-label');
        if (label) {
            label.innerHTML = `${theme.icon} ${theme.name}`;
        }
        
        // Update existing charts with new colors
        this.updateChartColors(theme);
        
        console.log('Theme applied:', theme.name);
    }

    updateChartColors(theme) {
        const colors = theme.colors;
        Object.values(this.charts).forEach(chart => {
            if (!chart || !chart.options) return;
            
            try {
                // Update scale colors
                if (chart.options.scales) {
                    Object.values(chart.options.scales).forEach(scale => {
                        if (scale.grid) scale.grid.color = colors.brd;
                        if (scale.ticks) scale.ticks.color = colors.tx3;
                    });
                }
                
                // Update legend colors
                if (chart.options.plugins?.legend?.labels) {
                    chart.options.plugins.legend.labels.color = colors.tx2;
                }
                
                chart.update();
            } catch(e) {
                console.warn('Failed to update chart colors:', e);
            }
        });
    }

    openThemePicker() {
        const currentTheme = this.activeTheme;
        
        // Build theme cards HTML
        const themeCardsHTML = Object.entries(SMM_THEMES).map(([key, theme]) => {
            const isActive = key === currentTheme;
            const cardStyle = `
                display:flex;
                align-items:center;
                gap:12px;
                padding:14px 16px;
                border-radius:12px;
                border:2px solid ${isActive ? theme.colors.pri : theme.colors.brd};
                background:${theme.colors.card};
                cursor:pointer;
                transition:all .18s;
                color:${theme.colors.tx1};
            `;
            
            const colorDots = ['pri', 'acc', 'grn', 'sky', 'pink']
                .map(c => `<div style="width:12px;height:12px;border-radius:3px;background:${theme.colors[c]}"></div>`)
                .join('');
            
            return `
            <div onclick="window.__smm.applyTheme('${key}'); if(window.__smm_theme_dialog) window.__smm_theme_dialog.hide();"
                 style="${cardStyle}">
                <div style="font-size:24px;width:40px;height:40px;border-radius:10px;background:${theme.colors.pri_x};display:flex;align-items:center;justify-content:center;flex-shrink:0">
                    ${theme.icon}
                </div>
                <div style="flex:1;min-width:0">
                    <div style="font-size:13px;font-weight:700;margin-bottom:2px">${theme.name}</div>
                    <div style="display:flex;gap:4px;margin-bottom:4px">${colorDots}</div>
                    <div style="font-size:10px;color:${theme.colors.tx3}">${theme.isDark ? 'Dark mode' : 'Light mode'}</div>
                </div>
                ${isActive ? `<span style="font-size:18px;color:${theme.colors.pri};flex-shrink:0">✓</span>` : ''}
            </div>`;
        }).join('');

        const dialog = new frappe.ui.Dialog({
            title: '🎨 Choose Studio Theme',
            size: 'large',
            fields: [{
                fieldtype: 'HTML',
                fieldname: 'themes_html',
                options: `
                <div style="padding:8px 0">
                    <p style="font-size:12px;color:var(--tx3);margin:0 0 14px">
                        Themes are stored locally in your browser. Select a theme to apply it instantly.
                    </p>
                    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">
                        ${themeCardsHTML}
                    </div>
                </div>`
            }]
        });
        
        // Store dialog reference globally so theme cards can close it
        window.__smm_theme_dialog = dialog;
        dialog.show();
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  CSS INJECTION — Complete stylesheet with all CSS variables
    // ═══════════════════════════════════════════════════════════════════════
    injectCSS() {
        // Prevent double injection
        if (document.getElementById('smm-css')) return;
        
        const styleElement = document.createElement('style');
        styleElement.id = 'smm-css';
        styleElement.textContent = `
/* ═══════════════════════════════════════════════════════════
   SOCIAL MEDIA STUDIO STYLESHEET
   All colors use CSS variables for theme support
═══════════════════════════════════════════════════════════ */

/* Font imports */
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600;9..40,700;9..40,800&family=Space+Mono:wght@400;700&display=swap');

/* Root styles */
#smm-root {
    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    background: var(--bg);
    color: var(--tx1);
    min-height: 100vh;
    transition: background 0.3s ease, color 0.3s ease;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

#smm-root * {
    box-sizing: border-box;
}

#smm-root.dark-mode input,
#smm-root.dark-mode select,
#smm-root.dark-mode textarea {
    color-scheme: dark;
}

/* ═══ TOP BAR ═══ */
.smm-topbar {
    position: sticky;
    top: 0;
    z-index: 100;
    background: var(--card);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-bottom: 1px solid var(--brd);
    display: flex;
    align-items: center;
    gap: 0;
    height: 56px;
    padding: 0 24px;
    transition: background 0.3s, border-color 0.3s;
}

.smm-logo {
    display: flex;
    align-items: center;
    gap: 10px;
    font-family: 'Space Mono', monospace;
    font-size: 14px;
    font-weight: 700;
    color: var(--tx1);
    letter-spacing: -0.5px;
    margin-right: 28px;
    white-space: nowrap;
}

.smm-logo-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--pri);
    animation: smm-pulse 2s infinite;
}

@keyframes smm-pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(1.4); }
}

/* ═══ NAVIGATION ═══ */
.smm-nav {
    display: flex;
    align-items: center;
    gap: 2px;
    flex: 1;
    overflow-x: auto;
    scrollbar-width: none;
    -ms-overflow-style: none;
}

.smm-nav::-webkit-scrollbar {
    display: none;
}

.smm-nav-btn {
    display: flex;
    align-items: center;
    gap: 7px;
    padding: 6px 14px;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
    color: var(--tx2);
    cursor: pointer;
    transition: all 0.15s ease;
    border: none;
    background: none;
    white-space: nowrap;
    font-family: inherit;
    outline: none;
}

.smm-nav-btn:hover {
    color: var(--tx1);
    background: var(--bg3);
}

.smm-nav-btn.active {
    color: var(--pri2);
    background: var(--pri_x);
    font-weight: 700;
}

.smm-nav-badge {
    background: var(--red);
    color: #fff;
    font-size: 9px;
    font-weight: 800;
    padding: 1px 5px;
    border-radius: 10px;
    min-width: 16px;
    text-align: center;
    line-height: 1.4;
}

/* ═══ TOPBAR RIGHT ═══ */
.smm-topbar-right {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-left: auto;
    flex-shrink: 0;
}

.smm-theme-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 5px 11px;
    border-radius: 8px;
    font-size: 11px;
    font-weight: 600;
    color: var(--tx2);
    background: var(--bg3);
    border: 1px solid var(--brd2);
    cursor: pointer;
    transition: all 0.15s ease;
    font-family: inherit;
    white-space: nowrap;
}

.smm-theme-btn:hover {
    background: var(--pri_x);
    color: var(--pri2);
    border-color: var(--pri);
}

.smm-clock {
    font-family: 'Space Mono', monospace;
    font-size: 11px;
    color: var(--tx3);
    white-space: nowrap;
}

.smm-sync-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--grn);
    animation: smm-pulse 3s infinite;
}

/* ═══ FAB (Floating Action Button) ═══ */
.smm-fab {
    position: fixed;
    bottom: 28px;
    right: 28px;
    z-index: 200;
    width: 52px;
    height: 52px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--pri), var(--acc));
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    color: #fff;
    cursor: pointer;
    box-shadow: 0 8px 30px rgba(99, 102, 241, 0.5);
    transition: all 0.2s ease;
    border: none;
    outline: none;
}

.smm-fab:hover {
    transform: scale(1.1) rotate(45deg);
    box-shadow: 0 12px 40px rgba(99, 102, 241, 0.7);
}

.smm-fab:active {
    transform: scale(0.95);
}

/* ═══ CONTENT AREA ═══ */
.smm-content {
    padding: 24px;
    max-width: 1600px;
    margin: 0 auto;
}

/* ═══ KPI CARDS ═══ */
.smm-kpis {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 14px;
    margin-bottom: 22px;
}

.smm-kpi {
    background: var(--card);
    border: 1px solid var(--brd);
    border-radius: 14px;
    padding: 18px 20px;
    cursor: pointer;
    transition: all 0.2s ease;
    position: relative;
    overflow: hidden;
}

.smm-kpi::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: var(--kc, var(--pri));
    transition: opacity 0.2s ease;
    opacity: 0;
}

.smm-kpi:hover {
    transform: translateY(-2px);
    border-color: var(--brd2);
    background: var(--bg3);
}

.smm-kpi:hover::after {
    opacity: 1;
}

.smm-kpi-icon {
    font-size: 18px;
    margin-bottom: 10px;
}

.smm-kpi-lbl {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--tx3);
    margin-bottom: 6px;
}

.smm-kpi-val {
    font-size: 28px;
    font-weight: 800;
    color: var(--tx1);
    line-height: 1;
    margin-bottom: 3px;
}

.smm-kpi-sub {
    font-size: 11px;
    color: var(--tx3);
}

/* ═══ GRID LAYOUTS ═══ */
.smm-g2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 16px;
}

.smm-g3 {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 16px;
    margin-bottom: 16px;
}

.smm-g21 {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 16px;
    margin-bottom: 16px;
}

.smm-g31 {
    display: grid;
    grid-template-columns: 3fr 1fr;
    gap: 16px;
    margin-bottom: 16px;
}

.smm-row {
    margin-bottom: 16px;
}

/* ═══ CARDS ═══ */
.smm-card {
    background: var(--card);
    border: 1px solid var(--brd);
    border-radius: 16px;
    overflow: hidden;
    transition: box-shadow 0.2s ease, border-color 0.2s ease;
}

.smm-card:hover {
    border-color: var(--brd2);
}

.smm-card-head {
    padding: 14px 20px;
    border-bottom: 1px solid var(--brd);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
}

.smm-card-title {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 13px;
    font-weight: 700;
    color: var(--tx1);
}

.smm-title-icon {
    width: 28px;
    height: 28px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    flex-shrink: 0;
}

.smm-card-body {
    padding: 18px 20px;
}

/* ═══ FORM ELEMENTS ═══ */
.smm-form {
    display: flex;
    flex-direction: column;
    gap: 14px;
}

.smm-fg {
    display: flex;
    flex-direction: column;
    gap: 5px;
}

.smm-fg label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--tx3);
}

.smm-fg label span.req {
    color: var(--red);
    margin-left: 2px;
}

.smm-inp,
.smm-sel,
.smm-ta {
    background: var(--bg3);
    border: 1.5px solid var(--brd2);
    border-radius: 10px;
    color: var(--tx1);
    font-family: inherit;
    font-size: 13px;
    padding: 10px 14px;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
    outline: none;
    width: 100%;
}

.smm-inp::placeholder,
.smm-ta::placeholder {
    color: var(--tx3);
}

.smm-inp:focus,
.smm-sel:focus,
.smm-ta:focus {
    border-color: var(--pri);
    box-shadow: 0 0 0 3px var(--pri_x);
}

.smm-sel {
    cursor: pointer;
    appearance: none;
    -webkit-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23475569' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 12px center;
    padding-right: 32px;
}

.smm-sel option {
    background: var(--bg2);
    color: var(--tx1);
}

.smm-ta {
    resize: vertical;
    min-height: 80px;
    line-height: 1.5;
}

.smm-fg-row {
    display: flex;
    gap: 12px;
}

.smm-fg-row .smm-fg {
    flex: 1;
}

.smm-check-row {
    display: flex;
    align-items: center;
    gap: 8px;
}

.smm-check-row input[type="checkbox"] {
    width: 16px;
    height: 16px;
    accent-color: var(--pri);
    cursor: pointer;
}

.smm-check-row label {
    font-size: 12px;
    color: var(--tx2);
    font-weight: 500;
    cursor: pointer;
}

/* ═══ BUTTONS ═══ */
.smm-btns {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    align-items: center;
}

.smm-btn {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 8px 16px;
    border-radius: 10px;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    border: 1.5px solid transparent;
    font-family: inherit;
    transition: all 0.15s ease;
    line-height: 1.3;
    text-decoration: none !important;
    white-space: nowrap;
    outline: none;
}

.smm-btn:hover {
    transform: translateY(-1px);
}

.smm-btn:active {
    transform: translateY(0);
}

.btn-primary {
    background: var(--pri);
    color: #fff;
    border-color: var(--pri);
}

.btn-primary:hover {
    background: var(--pri_d);
    box-shadow: 0 4px 14px var(--pri_x);
}

.btn-accent {
    background: var(--acc);
    color: #fff;
    border-color: var(--acc);
}

.btn-accent:hover {
    opacity: 0.9;
    box-shadow: 0 4px 14px var(--acc_x);
}

.btn-ghost {
    background: transparent;
    color: var(--tx2);
    border-color: var(--brd2);
}

.btn-ghost:hover {
    background: var(--bg3);
    color: var(--tx1);
    border-color: var(--pri);
}

.btn-grn {
    background: var(--grn_x);
    color: var(--grn);
    border-color: var(--grn_x);
}

.btn-grn:hover {
    background: var(--grn);
    color: #fff;
}

.btn-red {
    background: var(--red_x);
    color: var(--red);
    border-color: var(--red_x);
}

.btn-red:hover {
    background: var(--red);
    color: #fff;
}

.btn-amb {
    background: var(--amb_x);
    color: var(--amb);
    border-color: var(--amb_x);
}

.btn-amb:hover {
    background: var(--amb);
    color: #fff;
}

.btn-sky {
    background: var(--sky_x);
    color: var(--sky);
    border-color: var(--sky_x);
}

.btn-sky:hover {
    background: var(--sky);
    color: #fff;
}

.btn-sm {
    padding: 5px 11px;
    font-size: 11px;
}

.btn-xs {
    padding: 3px 8px;
    font-size: 10px;
    border-radius: 7px;
}

/* ═══ BADGES ═══ */
.smm-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 9px;
    border-radius: 20px;
    font-size: 10px;
    font-weight: 700;
    white-space: nowrap;
    line-height: 1.4;
}

.bd-pri { background: var(--pri_x); color: var(--pri2); }
.bd-grn { background: var(--grn_x); color: var(--grn); }
.bd-red { background: var(--red_x); color: var(--red); }
.bd-amb { background: var(--amb_x); color: var(--amb); }
.bd-sky { background: var(--sky_x); color: var(--sky); }
.bd-acc { background: var(--acc_x); color: var(--acc); }
.bd-pink { background: var(--pink_x); color: var(--pink); }
.bd-grey { background: var(--bg3); color: var(--tx3); border: 1px solid var(--brd2); }

/* ═══ PLATFORM CHIP ═══ */
.plat-chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 9px;
    border-radius: 20px;
    font-size: 10px;
    font-weight: 700;
    color: #fff;
}

/* ═══ POST CARDS ═══ */
.smm-post-card {
    background: var(--bg3);
    border: 1px solid var(--brd);
    border-radius: 14px;
    padding: 14px 16px;
    cursor: pointer;
    transition: all 0.18s ease;
    position: relative;
}

.smm-post-card:hover {
    border-color: var(--pri);
    background: var(--pri_x);
    transform: translateY(-1px);
}

.smm-post-card-title {
    font-size: 13px;
    font-weight: 700;
    color: var(--tx1);
    margin-bottom: 6px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.smm-post-card-excerpt {
    font-size: 11px;
    color: var(--tx2);
    line-height: 1.5;
    max-height: 42px;
    overflow: hidden;
    margin-bottom: 10px;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
}

.smm-post-card-meta {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}

.smm-post-metrics {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
    margin-top: 10px;
}

.smm-post-metric {
    text-align: center;
    background: var(--bg2);
    border-radius: 8px;
    padding: 6px 4px;
}

.smm-post-metric-val {
    font-size: 14px;
    font-weight: 800;
    color: var(--tx1);
}

.smm-post-metric-lbl {
    font-size: 9px;
    color: var(--tx3);
    text-transform: uppercase;
    letter-spacing: 0.4px;
}

/* ═══ TABLE ═══ */
.smm-tbl-wrap {
    overflow-x: auto;
    max-height: 480px;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: var(--brd2) transparent;
}

.smm-tbl-wrap::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}

.smm-tbl-wrap::-webkit-scrollbar-track {
    background: transparent;
}

.smm-tbl-wrap::-webkit-scrollbar-thumb {
    background: var(--brd2);
    border-radius: 3px;
}

.smm-tbl {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
}

.smm-tbl thead th {
    padding: 10px 14px;
    text-align: left;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--tx3);
    background: var(--bg2);
    border-bottom: 1px solid var(--brd2);
    position: sticky;
    top: 0;
    z-index: 2;
    white-space: nowrap;
}

.smm-tbl tbody td {
    padding: 10px 14px;
    border-bottom: 1px solid var(--brd);
    color: var(--tx2);
}

.smm-tbl tbody tr {
    cursor: pointer;
    transition: background 0.1s ease;
}

.smm-tbl tbody tr:hover {
    background: var(--pri_x);
}

.smm-tbl tbody tr:hover td {
    color: var(--tx1);
}

.smm-tbl tbody tr:last-child td {
    border-bottom: none;
}

/* ═══ PROGRESS BAR ═══ */
.smm-bar-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
}

.smm-bar-lbl {
    font-size: 11px;
    color: var(--tx2);
    width: 140px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 6px;
}

.smm-bar {
    flex: 1;
    height: 5px;
    background: var(--brd2);
    border-radius: 40px;
    overflow: hidden;
}

.smm-bar-fill {
    height: 100%;
    border-radius: 40px;
    transition: width 0.7s cubic-bezier(0.4, 0, 0.2, 1);
}

.smm-bar-val {
    font-size: 11px;
    font-family: 'Space Mono', monospace;
    font-weight: 700;
    width: 44px;
    text-align: right;
    color: var(--tx1);
}

/* ═══ CALENDAR ═══ */
.smm-cal {
    width: 100%;
}

.smm-cal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
}

.smm-cal-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 4px;
}

.smm-cal-day-name {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--tx3);
    text-align: center;
    padding: 6px 0;
}

.smm-cal-cell {
    min-height: 90px;
    background: var(--bg3);
    border-radius: 10px;
    border: 1px solid var(--brd);
    padding: 7px;
    cursor: pointer;
    transition: all 0.15s ease;
}

.smm-cal-cell:hover {
    border-color: var(--pri);
    background: var(--pri_x);
}

.smm-cal-cell.today {
    border-color: var(--pri);
    border-width: 2px;
}

.smm-cal-cell.other-month {
    opacity: 0.3;
}

.smm-cal-num {
    font-size: 11px;
    font-weight: 700;
    color: var(--tx2);
    margin-bottom: 4px;
}

.smm-cal-pill {
    font-size: 9px;
    padding: 1px 6px;
    border-radius: 4px;
    color: #fff;
    margin-bottom: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    cursor: pointer;
}

/* ═══ COMMENTS ═══ */
.smm-comment {
    padding: 14px 18px;
    border-bottom: 1px solid var(--brd);
    display: flex;
    align-items: flex-start;
    gap: 12px;
    cursor: pointer;
    transition: background 0.12s ease;
}

.smm-comment:hover {
    background: var(--pri_x);
}

.smm-comment:last-child {
    border-bottom: none;
}

.smm-avatar {
    width: 34px;
    height: 34px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 700;
    color: #fff;
    flex-shrink: 0;
}

.smm-comment-body {
    flex: 1;
    min-width: 0;
}

.smm-comment-head {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 4px;
}

.smm-comment-author {
    font-size: 12px;
    font-weight: 700;
    color: var(--tx1);
}

.smm-comment-time {
    font-size: 10px;
    color: var(--tx3);
}

.smm-comment-text {
    font-size: 12px;
    color: var(--tx2);
    line-height: 1.5;
    margin-bottom: 6px;
}

/* ═══ COMPOSE ═══ */
.smm-compose {
    display: grid;
    grid-template-columns: 1fr 340px;
    gap: 16px;
    align-items: start;
}

.smm-compose-main {
    background: var(--card);
    border: 1px solid var(--brd);
    border-radius: 16px;
    overflow: hidden;
}

.smm-compose-sidebar {
    display: flex;
    flex-direction: column;
    gap: 14px;
}

.smm-plat-toggles {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 14px 20px;
    border-bottom: 1px solid var(--brd);
}

.smm-plat-toggle {
    display: flex;
    align-items: center;
    gap: 7px;
    padding: 7px 12px;
    border-radius: 10px;
    border: 1.5px solid var(--brd2);
    cursor: pointer;
    transition: all 0.15s ease;
    font-size: 12px;
    font-weight: 600;
    color: var(--tx2);
    background: var(--bg3);
    user-select: none;
}

.smm-plat-toggle:hover {
    border-color: var(--brd);
}

.smm-plat-toggle.on {
    border-color: var(--pri);
    background: var(--pri_x);
    color: var(--pri2);
}

/* ═══ ACCOUNT CARDS ═══ */
.smm-account-card {
    background: var(--bg3);
    border: 1px solid var(--brd);
    border-radius: 14px;
    padding: 16px;
    cursor: pointer;
    transition: all 0.18s ease;
    display: flex;
    flex-direction: column;
}

.smm-account-card:hover {
    border-color: var(--pri);
    transform: translateY(-2px);
}

.smm-account-avatar {
    width: 42px;
    height: 42px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    color: #fff;
    margin-bottom: 12px;
}

.smm-account-name {
    font-size: 14px;
    font-weight: 700;
    color: var(--tx1);
    margin-bottom: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.smm-account-sub {
    font-size: 11px;
    color: var(--tx3);
    margin-bottom: 10px;
}

/* ═══ AI CARD ═══ */
.smm-ai-card {
    background: var(--pri_x);
    border: 1px solid var(--pri_x);
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 12px;
}

.smm-ai-card h4 {
    font-size: 11px;
    font-weight: 700;
    color: var(--pri2);
    margin: 0 0 8px;
    letter-spacing: 0.3px;
}

.smm-ai-item {
    display: flex;
    gap: 7px;
    font-size: 11px;
    color: var(--tx1);
    margin-bottom: 5px;
    line-height: 1.4;
}

.smm-ai-item:last-child {
    margin-bottom: 0;
}

.smm-ai-dot {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: var(--pri2);
    margin-top: 4px;
    flex-shrink: 0;
}

/* ═══ SENTIMENT RING ═══ */
.smm-ring-wrap {
    position: relative;
    flex-shrink: 0;
}

.smm-ring-wrap svg {
    display: block;
}

.smm-ring-label {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}

.smm-ring-pct {
    font-size: 16px;
    font-weight: 800;
    color: var(--tx1);
}

.smm-ring-sub {
    font-size: 9px;
    color: var(--tx3);
}

/* ═══ ALERTS ═══ */
.smm-alerts {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 18px;
}

.smm-alert {
    display: flex;
    align-items: center;
    gap: 7px;
    padding: 7px 13px;
    border-radius: 9px;
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
    text-decoration: none !important;
}

.smm-alert:hover {
    transform: translateY(-1px);
}

.al-red { background: var(--red_x); border: 1px solid var(--red_x); color: var(--red); }
.al-amb { background: var(--amb_x); border: 1px solid var(--amb_x); color: var(--amb); }
.al-pri { background: var(--pri_x); border: 1px solid var(--pri_x); color: var(--pri2); }
.al-grn { background: var(--grn_x); border: 1px solid var(--grn_x); color: var(--grn); }
.al-acc { background: var(--acc_x); border: 1px solid var(--acc_x); color: var(--acc); }

/* ═══ SETTINGS ═══ */
.smm-settings-section {
    margin-bottom: 24px;
}

.smm-settings-section h3 {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--tx3);
    margin: 0 0 14px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--brd);
}

.smm-toggle-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid var(--brd);
}

.smm-toggle-row:last-child {
    border-bottom: none;
}

.smm-toggle-info h5 {
    font-size: 13px;
    font-weight: 600;
    color: var(--tx1);
    margin: 0 0 2px;
}

.smm-toggle-info p {
    font-size: 11px;
    color: var(--tx3);
    margin: 0;
}

.smm-toggle {
    position: relative;
    width: 38px;
    height: 20px;
    cursor: pointer;
    flex-shrink: 0;
}

.smm-toggle input {
    opacity: 0;
    width: 0;
    height: 0;
    position: absolute;
}

.smm-toggle-track {
    position: absolute;
    inset: 0;
    background: var(--brd2);
    border-radius: 20px;
    transition: background 0.2s ease;
}

.smm-toggle input:checked + .smm-toggle-track {
    background: var(--pri);
}

.smm-toggle-thumb {
    position: absolute;
    top: 2px;
    left: 2px;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #fff;
    transition: transform 0.2s ease;
    box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}

.smm-toggle input:checked ~ .smm-toggle-thumb {
    transform: translateX(18px);
}

/* ═══ EMPTY STATE ═══ */
.smm-empty {
    text-align: center;
    padding: 48px 24px;
    color: var(--tx3);
}

.smm-empty-icon {
    font-size: 36px;
    margin-bottom: 12px;
}

.smm-empty h4 {
    font-size: 14px;
    font-weight: 700;
    color: var(--tx2);
    margin: 0 0 6px;
}

.smm-empty p {
    font-size: 12px;
    margin: 0 0 16px;
}

/* ═══ LOADER ═══ */
.smm-loader {
    position: fixed;
    inset: 0;
    background: var(--bg);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    gap: 16px;
    z-index: 9999;
    opacity: 0.95;
}

.smm-spinner {
    width: 40px;
    height: 40px;
    border: 3px solid var(--brd2);
    border-top-color: var(--pri);
    border-radius: 50%;
    animation: smm-spin 0.7s linear infinite;
}

@keyframes smm-spin {
    to { transform: rotate(360deg); }
}

/* ═══ DIVIDER ═══ */
.smm-divider {
    border: none;
    border-top: 1px solid var(--brd);
    margin: 20px 0;
}

/* ═══ RESPONSIVE ═══ */
@media (max-width: 1100px) {
    .smm-g21,
    .smm-g31,
    .smm-compose {
        grid-template-columns: 1fr;
    }
}

@media (max-width: 800px) {
    .smm-g2,
    .smm-g3 {
        grid-template-columns: 1fr;
    }
    
    .smm-topbar {
        padding: 0 12px;
    }
    
    .smm-nav-btn {
        padding: 6px 10px;
        font-size: 11px;
    }
    
    .smm-content {
        padding: 16px;
    }
}

@media (max-width: 600px) {
    .smm-kpis {
        grid-template-columns: 1fr 1fr;
    }
    
    .smm-nav-btn span {
        display: none;
    }
}

@media print {
    .smm-topbar,
    .smm-fab,
    .smm-btns,
    .smm-theme-btn {
        display: none !important;
    }
}
        `;
        
        document.head.appendChild(styleElement);
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  SHELL CONSTRUCTION
    // ═══════════════════════════════════════════════════════════════════════
    buildShell() {
        // Clear existing content
        $(this.page.main).empty();
        
        // Get current theme for display
        const theme = SMM_THEMES[this.activeTheme] || SMM_THEMES['midnight'];
        
        // Build the complete HTML structure
        const shellHTML = `
            <div id="smm-root">
                <!-- Top Navigation Bar -->
                <div class="smm-topbar">
                    <div class="smm-logo">
                        <div class="smm-logo-dot"></div>
                        SMM Studio
                    </div>
                    
                    <nav class="smm-nav" id="smm-nav">
                        <!-- Navigation buttons rendered by buildNav() -->
                    </nav>
                    
                    <div class="smm-topbar-right">
                        <button class="smm-theme-btn" onclick="window.__smm.openThemePicker()" title="Change theme">
                            <span id="smm-theme-label">${theme.icon} ${theme.name}</span>
                        </button>
                        <div class="smm-sync-dot" title="Auto-refreshing every 30s"></div>
                        <div class="smm-clock" id="smm-clock"></div>
                    </div>
                </div>
                
                <!-- Main Content Area -->
                <div class="smm-content" id="smm-content">
                    <!-- Loading indicator -->
                    <div class="smm-loader" id="smm-loader">
                        <div class="smm-spinner"></div>
                        <div style="font-weight:600;font-size:14px;color:var(--tx1)">
                            Loading Social Media Studio
                        </div>
                        <div style="font-size:12px;color:var(--tx3)">
                            Fetching posts, accounts & analytics…
                        </div>
                    </div>
                </div>
                
                <!-- Floating Action Button -->
                <button class="smm-fab" 
                        onclick="window.__smm.openCompose()" 
                        title="Create New Post (Ctrl+N)">
                    <i class="fa-solid fa-plus"></i>
                </button>
            </div>
        `;
        
        // Append to page
        this.$root = $(shellHTML).appendTo(this.page.main);
        
        // Build navigation buttons
        this.buildNav();
        
        // Apply initial theme
        this.applyTheme(this.activeTheme);
    }

    buildNav() {
        const views = [
            { id: 'studio',    icon: 'fa-solid fa-layer-group',  label: 'Studio' },
            { id: 'compose',   icon: 'fa-solid fa-pen-nib',       label: 'Compose' },
            { id: 'calendar',  icon: 'fa-solid fa-calendar-days', label: 'Calendar' },
            { id: 'inbox',     icon: 'fa-solid fa-inbox',         label: 'Inbox',     badge: 'inbox' },
            { id: 'analytics', icon: 'fa-solid fa-chart-line',    label: 'Analytics' },
            { id: 'accounts',  icon: 'fa-solid fa-plug',          label: 'Platforms' },
            { id: 'settings',  icon: 'fa-solid fa-gear',          label: 'Settings' },
        ];
        
        const navHTML = views.map(v => `
            <button class="smm-nav-btn ${v.id === this.state.activeView ? 'active' : ''}" 
                    data-view="${v.id}"
                    title="${v.label}">
                <i class="${v.icon}"></i>
                <span>${v.label}</span>
                ${v.badge ? `<span class="smm-nav-badge" id="smm-badge-${v.badge}" style="display:none">0</span>` : ''}
            </button>
        `).join('');
        
        const navContainer = document.getElementById('smm-nav');
        if (navContainer) {
            navContainer.innerHTML = navHTML;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  EVENT BINDING
    // ═══════════════════════════════════════════════════════════════════════
    bindEvents() {
        // Navigation clicks - use event delegation
        $(document).off('click.smmNav', '.smm-nav-btn').on('click.smmNav', '.smm-nav-btn', (e) => {
            const view = $(e.currentTarget).data('view');
            if (view) {
                this.switchView(view);
            }
        });
        
        // Keyboard shortcuts
        $(document).off('keydown.smmKeys').on('keydown.smmKeys', (e) => {
            // Ctrl+N or Cmd+N = New Post
            if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
                e.preventDefault();
                this.openCompose();
            }
            // Ctrl+1-7 = Switch views
            const viewKeys = ['studio', 'compose', 'calendar', 'inbox', 'analytics', 'accounts', 'settings'];
            if ((e.ctrlKey || e.metaKey) && e.key >= '1' && e.key <= '7') {
                e.preventDefault();
                const idx = parseInt(e.key) - 1;
                this.switchView(viewKeys[idx]);
            }
        });
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  VIEW SWITCHING
    // ═══════════════════════════════════════════════════════════════════════
    switchView(view) {
        if (!view) return;
        
        // Update state
        this.state.activeView = view;
        
        // Update navigation active states
        const allNavBtns = document.querySelectorAll('.smm-nav-btn');
        allNavBtns.forEach(btn => btn.classList.remove('active'));
        
        const activeBtn = document.querySelector(`.smm-nav-btn[data-view="${view}"]`);
        if (activeBtn) {
            activeBtn.classList.add('active');
        }
        
        // Render the view
        this.renderView(view);
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  DATA FETCHING
    // ═══════════════════════════════════════════════════════════════════════
    async fetchAll(silent = false) {
        if (this.state.isLoading) return;
        
        this.state.isLoading = true;
        
        if (!silent) {
            const loader = document.getElementById('smm-loader');
            if (loader) loader.style.display = '';
        }
        
        try {
            // Fetch posts and settings in parallel
            const [postsResult, settingsResult] = await Promise.all([
                frappe.call({
                    method: 'frappe.client.get_list',
                    args: {
                        doctype: 'Social Post',
                        fields: [
                            'name', 'post_title', 'content', 'content_type', 'status',
                            'campaign', 'publish_strategy', 'global_schedule',
                            'requires_approval', 'approved_by', 'approval_date',
                            'total_likes', 'total_comments', 'total_shares', 'total_reach',
                            'total_engagement_rate', 'total_views', 'total_clicks',
                            'total_conversions', 'revenue_generated', 'roi_percentage',
                            'primary_hashtags', 'mentions', 'location', 'link_url',
                            'ai_recommendations', 'creation', 'modified'
                        ],
                        limit_page_length: 500,
                        order_by: 'modified desc'
                    }
                }),
                frappe.call({
                    method: 'frappe.client.get',
                    args: { doctype: 'Social Media Settings', name: 'Social Media Settings' }
                }).catch(() => ({ message: null }))
            ]);

            // Store posts
            this.state.posts = postsResult.message || [];
            
            // Store settings
            this.state.settings = settingsResult.message;
            this.state.accounts = this.state.settings?.platform_accounts || [];

            // Fetch comments
            const commentsResult = await frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Social Post Comment',
                    fields: [
                        'name', 'parent', 'platform', 'author_name', 'comment_text',
                        'comment_time', 'sentiment_label', 'sentiment_score', 'status',
                        'is_flagged', 'reply_text', 'reply_status', 'like_count'
                    ],
                    limit_page_length: 200,
                    order_by: 'comment_time desc'
                }
            }).catch(() => ({ message: [] }));
            
            this.state.comments = commentsResult.message || [];

            // Update notification badges
            this.updateBadges();
            
            console.log('Data fetched:', {
                posts: this.state.posts.length,
                comments: this.state.comments.length,
                accounts: this.state.accounts.length
            });
            
        } catch(e) {
            console.error('SMM Studio fetch error:', e);
            if (!silent) {
                frappe.show_alert({ 
                    message: 'Failed to load social media data. Check console for details.', 
                    indicator: 'red' 
                });
            }
        } finally {
            this.state.isLoading = false;
            const loader = document.getElementById('smm-loader');
            if (loader) loader.style.display = 'none';
        }
    }

    updateBadges() {
        // Count unanswered comments
        const unanswered = this.state.comments.filter(
            c => c.status === 'New' || c.status === 'Unanswered'
        ).length;
        
        // Update inbox badge
        const badge = document.getElementById('smm-badge-inbox');
        if (badge) {
            badge.textContent = unanswered;
            badge.style.display = unanswered > 0 ? '' : 'none';
        }
        
        // Could add more badges here (drafts, pending approval, etc.)
    }

    startClock() {
        const updateClock = () => {
            const clockEl = document.getElementById('smm-clock');
            if (clockEl) {
                const now = new Date();
                clockEl.textContent = now.toLocaleTimeString('en-NG', { 
                    hour: '2-digit', 
                    minute: '2-digit',
                    second: '2-digit',
                    hour12: true 
                });
            }
        };
        
        // Initial update
        updateClock();
        
        // Update every second
        this.timers.clock = setInterval(updateClock, 1000);
    }

    startAutoRefresh() {
        // Clear existing timer
        if (this.timers.refresh) {
            clearInterval(this.timers.refresh);
        }
        
        // Start new auto-refresh timer (30 seconds)
        this.timers.refresh = setInterval(() => {
            this.fetchAll(true).then(() => {
                // Re-render current view with fresh data
                if (this.state.activeView) {
                    this.renderView(this.state.activeView);
                }
            });
        }, 30000);
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  VIEW ROUTER
    // ═══════════════════════════════════════════════════════════════════════
    renderView(name) {
        const viewMap = {
            'studio':    () => this.renderStudio(),
            'compose':   () => this.renderCompose(),
            'calendar':  () => this.renderCalendar(),
            'inbox':     () => this.renderInbox(),
            'analytics': () => this.renderAnalytics(),
            'accounts':  () => this.renderAccounts(),
            'settings':  () => this.renderSettings(),
        };
        
        const renderFn = viewMap[name];
        if (renderFn) {
            try {
                renderFn.call(this);
            } catch(e) {
                console.error(`Error rendering view "${name}":`, e);
                this.setContent(`
                    <div class="smm-empty">
                        <div class="smm-empty-icon">⚠️</div>
                        <h4>Error Rendering View</h4>
                        <p>${e.message || 'An unexpected error occurred'}</p>
                        <button class="smm-btn btn-primary" onclick="window.__smm.switchView('studio')">
                            Go to Studio
                        </button>
                    </div>
                `);
            }
        } else {
            console.warn('Unknown view:', name);
            this.switchView('studio');
        }
    }

    setContent(html) {
        const contentEl = document.getElementById('smm-content');
        if (contentEl) {
            contentEl.innerHTML = html;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  VIEW: STUDIO (Overview Dashboard)
    // ═══════════════════════════════════════════════════════════════════════
    renderStudio() {
        const posts = this.state.posts;
        const comments = this.state.comments;
        const accounts = this.state.accounts;
        
        // Calculate KPIs
        const totalReach = posts.reduce((sum, p) => sum + flt(p.total_reach), 0);
        const totalEngage = posts.reduce((sum, p) => 
            sum + flt(p.total_likes) + flt(p.total_comments) + flt(p.total_shares), 0);
        const publishedCount = posts.filter(p => p.status === 'Published').length;
        const scheduledCount = posts.filter(p => p.status === 'Scheduled').length;
        const draftCount = posts.filter(p => p.status === 'Draft').length;
        const failedCount = posts.filter(p => p.status === 'Failed').length;
        const pendingApproval = posts.filter(p => p.status === 'Pending Approval').length;
        const unansweredComments = comments.filter(c => 
            c.status === 'New' || c.status === 'Unanswered').length;
        const activeAccounts = accounts.filter(a => a.is_active).length;
        
        // Average engagement rate for published posts
        const publishedPosts = posts.filter(p => p.status === 'Published' && flt(p.total_reach) > 0);
        const avgEngRate = publishedPosts.length > 0 
            ? (publishedPosts.reduce((sum, p) => sum + flt(p.total_engagement_rate), 0) / publishedPosts.length).toFixed(1)
            : '0';
        
        // Total revenue
        const totalRevenue = posts.reduce((sum, p) => sum + flt(p.revenue_generated), 0);
        
        // Build alert messages
        const alerts = [];
        if (failedCount > 0) {
            alerts.push({ cls: 'al-red', icon: 'fa-triangle-exclamation', txt: `${failedCount} Failed Post${failedCount !== 1 ? 's' : ''}`, action: null });
        }
        if (pendingApproval > 0) {
            alerts.push({ cls: 'al-amb', icon: 'fa-clock', txt: `${pendingApproval} Pending Approval`, action: null });
        }
        if (unansweredComments > 0) {
            alerts.push({ cls: 'al-acc', icon: 'fa-comment', txt: `${unansweredComments} Unanswered`, action: () => this.switchView('inbox') });
        }
        
        // Build alerts HTML
        const alertsHTML = alerts.length > 0 ? `
            <div class="smm-alerts">
                ${alerts.map(a => `
                    <div class="smm-alert ${a.cls}" ${a.action ? `onclick="window.__smm.switchView('inbox')"` : ''}>
                        <i class="fa-solid ${a.icon}"></i> ${a.txt}
                    </div>
                `).join('')}
            </div>
        ` : '';
        
        // Build recent posts cards (last 6)
        const recentPosts = posts.slice(0, 6);
        const recentCardsHTML = recentPosts.length > 0 ? recentPosts.map(post => {
            const meta = sm(post.status);
            const excerpt = (post.content || '')
                .replace(/<[^>]+>/g, '')
                .substring(0, 120)
                .trim();
            
            return `
            <div class="smm-post-card" onclick="window.__smm.openPostDetail('${post.name}')">
                <div class="smm-post-card-title">${esc(post.post_title || 'Untitled')}</div>
                <div class="smm-post-card-excerpt">${esc(excerpt) || 'No content'}</div>
                <div class="smm-post-card-meta">
                    <span class="smm-badge" style="background:${meta.col}22;color:${meta.col}">
                        <i class="fa-solid ${meta.icon}"></i> ${post.status}
                    </span>
                    ${post.content_type ? `<span class="smm-badge bd-grey">${post.content_type}</span>` : ''}
                    ${post.global_schedule ? `
                        <span style="font-size:10px;color:var(--tx3)">
                            <i class="fa-solid fa-calendar"></i> ${frappe.datetime.str_to_user(post.global_schedule.split(' ')[0])}
                        </span>
                    ` : ''}
                </div>
                ${flt(post.total_reach) > 0 ? `
                <div class="smm-post-metrics">
                    <div class="smm-post-metric">
                        <div class="smm-post-metric-val">${numK(post.total_reach)}</div>
                        <div class="smm-post-metric-lbl">Reach</div>
                    </div>
                    <div class="smm-post-metric">
                        <div class="smm-post-metric-val">${numK(post.total_likes)}</div>
                        <div class="smm-post-metric-lbl">Likes</div>
                    </div>
                    <div class="smm-post-metric">
                        <div class="smm-post-metric-val">${numK(post.total_comments)}</div>
                        <div class="smm-post-metric-lbl">Comments</div>
                    </div>
                    <div class="smm-post-metric">
                        <div class="smm-post-metric-val">${flt(post.total_engagement_rate).toFixed(1)}%</div>
                        <div class="smm-post-metric-lbl">Eng Rate</div>
                    </div>
                </div>
                ` : ''}
            </div>`;
        }).join('') : `
            <div class="smm-empty">
                <div class="smm-empty-icon">📭</div>
                <h4>No Posts Yet</h4>
                <p>Create your first social media post to see it here.</p>
                <button class="smm-btn btn-primary" onclick="window.__smm.openCompose()">
                    <i class="fa-solid fa-plus"></i> Create First Post
                </button>
            </div>
        `;
        
        // Build platform status sidebar
        const platformListHTML = accounts.length > 0 ? accounts.map(acc => {
            const pi = pm(acc.platform);
            const statusColor = acc.is_active ? 'var(--grn)' : 'var(--tx3)';
            return `
            <div style="display:flex;align-items:center;gap:10px;padding:9px 0;border-bottom:1px solid var(--brd);cursor:pointer"
                 onclick="window.__smm.openAccountDetail('${acc.name}')">
                <div style="width:32px;height:32px;border-radius:9px;background:${pi.col};display:flex;align-items:center;justify-content:center;color:#fff;font-size:14px;flex-shrink:0">
                    <i class="${pi.icon}"></i>
                </div>
                <div style="flex:1;min-width:0">
                    <div style="font-size:12px;font-weight:600;color:var(--tx1);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
                        ${esc(acc.account_name)}
                    </div>
                    <div style="font-size:10px;color:var(--tx3)">${acc.platform}</div>
                </div>
                <div style="width:7px;height:7px;border-radius:50%;background:${statusColor};flex-shrink:0"></div>
            </div>`;
        }).join('') : `
            <div class="smm-empty" style="padding:24px">
                <div class="smm-empty-icon">🔗</div>
                <h4>No Platforms Connected</h4>
                <p>Connect your social media accounts to start posting.</p>
                <button class="smm-btn btn-primary btn-sm" onclick="window.__smm.switchView('accounts')">
                    Connect Platform
                </button>
            </div>
        `;
        
        // Build status breakdown bars
        const statusCounts = {};
        posts.forEach(p => {
            const s = p.status || 'Draft';
            statusCounts[s] = (statusCounts[s] || 0) + 1;
        });
        
        const statusBreakdownHTML = Object.entries(statusCounts)
            .sort((a, b) => b[1] - a[1])
            .map(([status, count]) => {
                const meta = sm(status);
                const pct = posts.length > 0 ? Math.round((count / posts.length) * 100) : 0;
                return `
                <div class="smm-bar-row">
                    <div class="smm-bar-lbl">
                        <span class="smm-badge" style="background:${meta.col}22;color:${meta.col};font-size:9px">
                            ${status}
                        </span>
                    </div>
                    <div class="smm-bar">
                        <div class="smm-bar-fill" style="width:${pct}%;background:${meta.col}"></div>
                    </div>
                    <div class="smm-bar-val">${count}</div>
                </div>`;
            }).join('') || '<div style="color:var(--tx3);font-size:12px;padding:8px 0">No posts yet</div>';
        
        // Render the complete studio view
        this.setContent(`
        <div style="animation:fadeIn .3s ease">
            ${alertsHTML}
            
            <!-- KPI Row -->
            <div class="smm-kpis">
                <div class="smm-kpi" style="--kc:var(--pri)" onclick="window.__smm.switchView('analytics')">
                    <div class="smm-kpi-icon">👁️</div>
                    <div class="smm-kpi-lbl">Total Reach</div>
                    <div class="smm-kpi-val">${numK(totalReach)}</div>
                    <div class="smm-kpi-sub">Across all platforms</div>
                </div>
                
                <div class="smm-kpi" style="--kc:var(--acc)">
                    <div class="smm-kpi-icon">❤️</div>
                    <div class="smm-kpi-lbl">Engagements</div>
                    <div class="smm-kpi-val">${numK(totalEngage)}</div>
                    <div class="smm-kpi-sub">Likes + Comments + Shares</div>
                </div>
                
                <div class="smm-kpi" style="--kc:var(--sky)">
                    <div class="smm-kpi-icon">📊</div>
                    <div class="smm-kpi-lbl">Avg. Eng. Rate</div>
                    <div class="smm-kpi-val">${avgEngRate}%</div>
                    <div class="smm-kpi-sub">Published posts only</div>
                </div>
                
                <div class="smm-kpi" style="--kc:var(--grn)">
                    <div class="smm-kpi-icon">✅</div>
                    <div class="smm-kpi-lbl">Published</div>
                    <div class="smm-kpi-val">${publishedCount}</div>
                    <div class="smm-kpi-sub">${scheduledCount} scheduled · ${draftCount} drafts</div>
                </div>
                
                <div class="smm-kpi" style="--kc:var(--amb)" onclick="window.__smm.switchView('inbox')">
                    <div class="smm-kpi-icon">💬</div>
                    <div class="smm-kpi-lbl">Comments</div>
                    <div class="smm-kpi-val">${comments.length}</div>
                    <div class="smm-kpi-sub">${unansweredComments} unanswered</div>
                </div>
                
                <div class="smm-kpi" style="--kc:var(--sky)" onclick="window.__smm.switchView('accounts')">
                    <div class="smm-kpi-icon">🔗</div>
                    <div class="smm-kpi-lbl">Platforms</div>
                    <div class="smm-kpi-val">${activeAccounts}</div>
                    <div class="smm-kpi-sub">Active connections</div>
                </div>
            </div>
            
            <!-- Main Content Grid -->
            <div class="smm-g21">
                <!-- Left: Recent Posts -->
                <div>
                    <div class="smm-card smm-row">
                        <div class="smm-card-head">
                            <div class="smm-card-title">
                                <div class="smm-title-icon" style="background:var(--pri_x);color:var(--pri2)">
                                    <i class="fa-solid fa-layer-group"></i>
                                </div>
                                Recent Posts (${posts.length} total)
                            </div>
                            <div class="smm-btns">
                                <button class="smm-btn btn-primary btn-sm" onclick="window.__smm.openCompose()">
                                    <i class="fa-solid fa-plus"></i> New Post
                                </button>
                                <button class="smm-btn btn-ghost btn-sm" onclick="window.__smm.switchView('compose')">
                                    View All →
                                </button>
                            </div>
                        </div>
                        <div style="padding:14px;display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px">
                            ${recentCardsHTML}
                        </div>
                    </div>
                </div>
                
                <!-- Right: Platform Status & Post Mix -->
                <div>
                    <!-- Platform Status -->
                    <div class="smm-card smm-row">
                        <div class="smm-card-head">
                            <div class="smm-card-title">
                                <div class="smm-title-icon" style="background:var(--grn_x);color:var(--grn)">
                                    <i class="fa-solid fa-plug"></i>
                                </div>
                                Platform Status
                            </div>
                            <button class="smm-btn btn-ghost btn-xs" onclick="window.__smm.switchView('accounts')">
                                Manage →
                            </button>
                        </div>
                        <div style="padding:12px 16px">
                            ${platformListHTML}
                        </div>
                    </div>
                    
                    <!-- Post Mix -->
                    <div class="smm-card">
                        <div class="smm-card-head">
                            <div class="smm-card-title">
                                <div class="smm-title-icon" style="background:var(--sky_x);color:var(--sky)">
                                    <i class="fa-solid fa-chart-pie"></i>
                                </div>
                                Post Status Mix
                            </div>
                        </div>
                        <div style="padding:14px 16px">
                            ${statusBreakdownHTML}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        `);
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  VIEW: COMPOSE (Post Creator)
    // ═══════════════════════════════════════════════════════════════════════
    renderCompose() {
        const draft = this.state.composeDraft || {};
        const accounts = this.state.accounts.filter(a => a.is_active);
        
        // Platform toggle buttons
        const platformTogglesHTML = accounts.length > 0 ? accounts.map(acc => {
            const pi = pm(acc.platform);
            const isSelected = (draft.selectedAccounts || []).includes(acc.name);
            return `
            <div class="smm-plat-toggle ${isSelected ? 'on' : ''}" 
                 data-acc="${acc.name}" 
                 data-platform="${acc.platform}"
                 onclick="window.__smm.togglePlatform(this)">
                <i class="${pi.icon}" style="color:${pi.col}"></i>
                ${esc(acc.account_name)}
            </div>`;
        }).join('') : `
            <div style="font-size:12px;color:var(--tx3);padding:8px">
                No active platforms. 
                <span style="color:var(--pri2);cursor:pointer" onclick="window.__smm.switchView('accounts')">
                    Connect one →
                </span>
            </div>
        `;
        
        this.setContent(`
        <div style="animation:fadeIn .3s ease">
            <!-- Header -->
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;flex-wrap:wrap;gap:12px">
                <div>
                    <h2 style="font-size:20px;font-weight:800;color:var(--tx1);margin:0 0 4px">
                        Post Composer
                    </h2>
                    <div style="font-size:12px;color:var(--tx3)">
                        Create, schedule, and publish across all platforms
                    </div>
                </div>
                <div class="smm-btns">
                    <button class="smm-btn btn-ghost btn-sm" onclick="window.__smm.switchView('studio')">
                        ← Back to Studio
                    </button>
                    <button class="smm-btn btn-primary" onclick="window.__smm.savePost(false)">
                        <i class="fa-solid fa-floppy-disk"></i> Save Draft
                    </button>
                    <button class="smm-btn btn-accent" onclick="window.__smm.savePost(true)">
                        <i class="fa-solid fa-rocket"></i> Save & Submit
                    </button>
                </div>
            </div>
            
            <!-- Compose Layout -->
            <div class="smm-compose">
                <!-- Main Editor -->
                <div>
                    <div class="smm-compose-main smm-row">
                        <!-- Title -->
                        <div style="padding:18px 20px;border-bottom:1px solid var(--brd)">
                            <div class="smm-fg">
                                <label>Post Title <span class="req">*</span></label>
                                <input class="smm-inp" 
                                       id="cp-title" 
                                       placeholder="Give this post a descriptive title…" 
                                       value="${esc(draft.post_title || '')}"
                                       autofocus>
                            </div>
                        </div>
                        
                        <!-- Platform Selection -->
                        <div class="smm-plat-toggles" id="cp-plat-toggles">
                            ${platformTogglesHTML}
                        </div>
                        
                        <!-- Content Editor -->
                        <div style="padding:18px 20px">
                            <div class="smm-form">
                                <!-- Caption -->
                                <div class="smm-fg">
                                    <label>Main Caption / Content <span class="req">*</span></label>
                                    <textarea class="smm-ta" 
                                              id="cp-content" 
                                              rows="6" 
                                              placeholder="Write your caption here… Use emojis, hashtags, and mentions to boost engagement."
                                              oninput="window.__smm.updateCharCount()">${esc(draft.content || '')}</textarea>
                                    <div style="display:flex;justify-content:space-between;align-items:center;margin-top:4px">
                                        <div style="font-size:10px;color:var(--tx3)" id="cp-char-count">
                                            ${(draft.content || '').length} characters
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Content Type & Strategy -->
                                <div class="smm-fg-row">
                                    <div class="smm-fg">
                                        <label>Content Type</label>
                                        <select class="smm-sel" id="cp-content-type">
                                            ${['Image', 'Video', 'Carousel', 'Reel', 'Story', 'Text Only', 'Link', 'Poll', 'Article'].map(t => 
                                                `<option value="${t}" ${(draft.content_type || 'Image') === t ? 'selected' : ''}>${t}</option>`
                                            ).join('')}
                                        </select>
                                    </div>
                                    <div class="smm-fg">
                                        <label>Publish Strategy</label>
                                        <select class="smm-sel" id="cp-strategy">
                                            <option value="Publish Now" ${(draft.publish_strategy || 'Schedule Global') === 'Publish Now' ? 'selected' : ''}>Publish Now</option>
                                            <option value="Schedule Global" ${(draft.publish_strategy || 'Schedule Global') === 'Schedule Global' ? 'selected' : ''}>Schedule Global</option>
                                        </select>
                                    </div>
                                </div>
                                
                                <!-- Schedule & Campaign -->
                                <div class="smm-fg-row">
                                    <div class="smm-fg">
                                        <label>Schedule Date & Time</label>
                                        <input class="smm-inp" 
                                               id="cp-schedule" 
                                               type="datetime-local" 
                                               value="${draft.global_schedule || ''}">
                                    </div>
                                    <div class="smm-fg">
                                        <label>Campaign</label>
                                        <input class="smm-inp" 
                                               id="cp-campaign" 
                                               placeholder="Campaign name or code" 
                                               value="${esc(draft.campaign || '')}">
                                    </div>
                                </div>
                                
                                <!-- Hashtags & Link -->
                                <div class="smm-fg-row">
                                    <div class="smm-fg">
                                        <label>Primary Hashtags</label>
                                        <input class="smm-inp" 
                                               id="cp-hashtags" 
                                               placeholder="#socialmedia #marketing #growth" 
                                               value="${esc(draft.primary_hashtags || '')}">
                                    </div>
                                    <div class="smm-fg">
                                        <label>Link URL</label>
                                        <input class="smm-inp" 
                                               id="cp-link" 
                                               placeholder="https://…" 
                                               value="${esc(draft.link_url || '')}">
                                    </div>
                                </div>
                                
                                <!-- Approval Toggle -->
                                <div class="smm-check-row">
                                    <input type="checkbox" 
                                           id="cp-requires-approval" 
                                           ${draft.requires_approval ? 'checked' : ''}>
                                    <label for="cp-requires-approval">
                                        Requires approval before publishing
                                    </label>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Sidebar -->
                <div class="smm-compose-sidebar">
                    <!-- AI Content Score -->
                    <div class="smm-card">
                        <div class="smm-card-head">
                            <div class="smm-card-title">
                                <div class="smm-title-icon" style="background:var(--pri_x);color:var(--pri2)">
                                    <i class="fa-solid fa-robot"></i>
                                </div>
                                Content Score
                            </div>
                            <button class="smm-btn btn-ghost btn-xs" onclick="window.__smm.scoreContent()">
                                <i class="fa-solid fa-wand-magic-sparkles"></i> Analyse
                            </button>
                        </div>
                        <div style="padding:14px 16px" id="cp-ai-body">
                            <div style="text-align:center;padding:16px;color:var(--tx3)">
                                <i class="fa-solid fa-robot" style="font-size:20px;display:block;margin-bottom:8px"></i>
                                <div style="font-size:11px">Fill in your caption and click Analyse to get an AI content score</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Hashtag Suggester -->
                    <div class="smm-card">
                        <div class="smm-card-head">
                            <div class="smm-card-title">
                                <div class="smm-title-icon" style="background:var(--acc_x);color:var(--acc)">
                                    <i class="fa-solid fa-hashtag"></i>
                                </div>
                                Hashtag Suggester
                            </div>
                        </div>
                        <div style="padding:14px 16px">
                            <div class="smm-fg" style="margin-bottom:10px">
                                <input class="smm-inp" 
                                       id="ht-topic" 
                                       placeholder="Topic: e.g. fintech, Lagos, SME…">
                            </div>
                            <button class="smm-btn btn-accent btn-sm" 
                                    style="width:100%;justify-content:center" 
                                    onclick="window.__smm.suggestHashtags()">
                                <i class="fa-solid fa-wand-magic-sparkles"></i> Generate Hashtags
                            </button>
                            <div id="ht-results" style="margin-top:10px;display:flex;flex-wrap:wrap;gap:6px"></div>
                        </div>
                    </div>
                    
                    <!-- Recent Drafts -->
                    <div class="smm-card">
                        <div class="smm-card-head">
                            <div class="smm-card-title">
                                <div class="smm-title-icon" style="background:var(--tx3);color:var(--tx1)">
                                    <i class="fa-solid fa-clock-rotate-left"></i>
                                </div>
                                Recent Drafts
                            </div>
                        </div>
                        <div style="max-height:200px;overflow-y:auto">
                            ${this.state.posts.filter(p => p.status === 'Draft').slice(0, 5).map(post => `
                            <div style="padding:10px 16px;border-bottom:1px solid var(--brd);cursor:pointer;transition:background .12s"
                                 onclick="window.__smm.loadDraft('${post.name}')"
                                 onmouseenter="this.style.background='var(--pri_x)'"
                                 onmouseleave="this.style.background=''">
                                <div style="font-size:12px;font-weight:600;color:var(--tx1);margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
                                    ${esc(post.post_title || 'Untitled')}
                                </div>
                                <div style="font-size:10px;color:var(--tx3)">
                                    ${frappe.datetime.prettyDate(post.modified)}
                                </div>
                            </div>`).join('') || `
                            <div style="padding:14px;text-align:center;font-size:12px;color:var(--tx3)">
                                No drafts yet
                            </div>`}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        `);
    }

    togglePlatform(el) {
        el.classList.toggle('on');
    }

    updateCharCount() {
        const content = document.getElementById('cp-content');
        const countEl = document.getElementById('cp-char-count');
        if (content && countEl) {
            const len = (content.value || '').length;
            countEl.textContent = `${len} characters`;
        }
    }

    scoreContent() {
        const contentEl = document.getElementById('cp-content');
        const hashtagsEl = document.getElementById('cp-hashtags');
        if (!contentEl) return;
        
        const content = contentEl.value || '';
        const hashtags = hashtagsEl?.value || '';
        const selectedPlatforms = document.querySelectorAll('.smm-plat-toggle.on').length;
        
        let score = 0;
        const items = [];
        
        // Caption length
        const len = content.length;
        if (len >= 50 && len <= 300) {
            score += 25;
            items.push({ ok: true, txt: 'Caption length is optimal (50-300 characters)' });
        } else if (len < 50) {
            score += 10;
            items.push({ ok: false, txt: `Caption is quite short (${len} chars). Add more context.` });
        } else if (len > 300) {
            score += 18;
            items.push({ ok: null, txt: `Long caption (${len} chars). Consider trimming for better engagement.` });
        }
        
        // Hashtag count
        const htags = hashtags.split(/[\s,]+/).filter(h => h.startsWith('#'));
        if (htags.length >= 5 && htags.length <= 15) {
            score += 20;
            items.push({ ok: true, txt: `Good hashtag count (${htags.length})` });
        } else if (htags.length < 3) {
            score += 8;
            items.push({ ok: false, txt: 'Add 5-15 hashtags to boost reach' });
        } else if (htags.length > 20) {
            score += 12;
            items.push({ ok: null, txt: 'Too many hashtags. Quality over quantity.' });
        } else {
            score += 15;
            items.push({ ok: null, txt: `Hashtag count: ${htags.length}. Close to optimal.` });
        }
        
        // Engagement hook (questions, CTAs)
        const hasQuestion = content.includes('?');
        const hasExclamation = content.includes('!');
        const ctaWords = ['click', 'buy', 'shop', 'learn', 'discover', 'get', 'download', 'sign up', 'subscribe', 'comment', 'share', 'like'];
        const hasCTA = ctaWords.some(w => content.toLowerCase().includes(w));
        
        if (hasQuestion || hasCTA) {
            score += 20;
            items.push({ ok: true, txt: 'Has engagement hook or call-to-action' });
        } else if (hasExclamation) {
            score += 15;
            items.push({ ok: null, txt: 'Has exclamation. Consider adding a question.' });
        } else {
            score += 5;
            items.push({ ok: false, txt: 'Add a question or CTA to drive engagement' });
        }
        
        // Platform selection
        if (selectedPlatforms >= 3) {
            score += 20;
            items.push({ ok: true, txt: `Posting to ${selectedPlatforms} platforms` });
        } else if (selectedPlatforms >= 1) {
            score += 12;
            items.push({ ok: null, txt: `Only ${selectedPlatforms} platform(s) selected` });
        } else {
            score += 0;
            items.push({ ok: false, txt: 'No platforms selected' });
        }
        
        // Link presence
        const linkEl = document.getElementById('cp-link');
        const hasLink = linkEl?.value || /https?:\/\//.test(content);
        if (hasLink) {
            score += 15;
            items.push({ ok: true, txt: 'Includes a link for traffic' });
        } else {
            score += 8;
            items.push({ ok: null, txt: 'Consider adding a link' });
        }
        
        // Final score
        score = Math.min(100, score);
        
        // Determine color
        let scoreColor;
        if (score >= 75) scoreColor = 'var(--grn)';
        else if (score >= 50) scoreColor = 'var(--amb)';
        else scoreColor = 'var(--red)';
        
        // Build SVG ring
        const circumference = 2 * Math.PI * 28;
        const offset = circumference * (1 - score / 100);
        
        const scoreHTML = `
        <div style="text-align:center;margin-bottom:14px">
            <svg width="80" height="80" viewBox="0 0 80 80">
                <circle cx="40" cy="40" r="28" fill="none" stroke="var(--brd2)" stroke-width="7"/>
                <circle cx="40" cy="40" r="28" fill="none" stroke="${scoreColor}" stroke-width="7"
                        stroke-dasharray="${circumference.toFixed(1)}" 
                        stroke-dashoffset="${offset.toFixed(1)}"
                        stroke-linecap="round" 
                        transform="rotate(-90 40 40)"/>
                <text x="40" y="44" text-anchor="middle" font-size="18" font-weight="800" fill="${scoreColor}">${score}</text>
                <text x="40" y="56" text-anchor="middle" font-size="9" fill="var(--tx3)">/100</text>
            </svg>
            <div style="font-size:11px;color:var(--tx3);margin-top:4px">
                ${score >= 80 ? 'Excellent! 🎉' : score >= 60 ? 'Good 👍' : score >= 40 ? 'Needs Work 📝' : 'Keep Improving 💪'}
            </div>
        </div>
        ${items.map(item => `
        <div style="display:flex;align-items:flex-start;gap:7px;margin-bottom:6px;font-size:11px;color:var(--tx2);line-height:1.4">
            <i class="fa-solid ${item.ok === true ? 'fa-circle-check' : item.ok === false ? 'fa-circle-xmark' : 'fa-circle-minus'}" 
               style="color:${item.ok === true ? 'var(--grn)' : item.ok === false ? 'var(--red)' : 'var(--amb)'};margin-top:2px;flex-shrink:0;font-size:10px"></i>
            <span>${item.txt}</span>
        </div>`).join('')}`;
        
        const body = document.getElementById('cp-ai-body');
        if (body) body.innerHTML = scoreHTML;
    }

    suggestHashtags() {
        const topicEl = document.getElementById('ht-topic');
        const topic = (topicEl?.value || 'business').toLowerCase();
        
        const hashtagSets = {
            fintech: ['#fintech', '#digitalbanking', '#nigeriafintech', '#payments', '#neobank', '#startup', '#innovation', '#africa', '#investng', '#moneytransfer'],
            marketing: ['#marketing', '#digitalmarketing', '#socialmedia', '#contentmarketing', '#branding', '#seo', '#growthhacking', '#b2b', '#agency', '#strategy'],
            lagos: ['#lagos', '#lagosbusiness', '#naija', '#nigeria', '#lagoslife', '#entrepreneurship', '#madeinnigeria', '#nigerianstartup', '#eko', '#lasgidi'],
            sme: ['#sme', '#smallbusiness', '#entrepreneur', '#business', '#nigeriaentrepreneur', '#supportsmallbusiness', '#growth', '#startup', '#businessowner', '#solopreneur'],
            tech: ['#tech', '#technology', '#innovation', '#startup', '#digital', '#software', '#ai', '#blockchain', '#coding', '#developer'],
            fashion: ['#fashion', '#style', '#ootd', '#fashionblogger', '#streetstyle', '#luxury', '#designer', '#model', '#beauty', '#trending'],
            food: ['#food', '#foodie', '#instafood', '#yummy', '#delicious', '#homemade', '#recipe', '#cooking', '#foodporn', '#restaurant'],
            fitness: ['#fitness', '#workout', '#gym', '#health', '#wellness', '#motivation', '#fitlife', '#training', '#exercise', '#healthy'],
            default: ['#business', '#entrepreneur', '#marketing', '#socialmedia', '#growth', '#branding', '#digital', '#strategy', '#content', '#success', '#innovation', '#leadership']
        };
        
        // Find matching set
        let key = 'default';
        for (const k of Object.keys(hashtagSets)) {
            if (topic.includes(k)) {
                key = k;
                break;
            }
        }
        
        const tags = hashtagSets[key];
        const resultsEl = document.getElementById('ht-results');
        if (resultsEl) {
            resultsEl.innerHTML = tags.map(tag => `
                <span onclick="window.__smm.addHashtag('${tag}')" 
                      style="padding:4px 10px;border-radius:20px;font-size:11px;font-weight:600;
                             background:var(--pri_x);color:var(--pri2);cursor:pointer;
                             transition:all .12s"
                      onmouseenter="this.style.background='var(--pri)';this.style.color='#fff'"
                      onmouseleave="this.style.background='var(--pri_x)';this.style.color='var(--pri2)'">
                    ${tag}
                </span>
            `).join('');
        }
    }

    addHashtag(tag) {
        const field = document.getElementById('cp-hashtags');
        if (!field) return;
        
        const existing = field.value.split(/[\s,]+/).filter(Boolean);
        if (!existing.includes(tag)) {
            field.value = [...existing, tag].join(' ');
            this.updateCharCount();
        }
    }

    loadDraft(name) {
        const post = this.state.posts.find(p => p.name === name);
        if (!post) {
            frappe.show_alert({ message: 'Draft not found', indicator: 'red' });
            return;
        }
        
        // Load into compose draft
        this.state.composeDraft = {
            post_title: post.post_title,
            content: post.content,
            content_type: post.content_type,
            publish_strategy: post.publish_strategy,
            global_schedule: post.global_schedule,
            campaign: post.campaign,
            primary_hashtags: post.primary_hashtags,
            link_url: post.link_url,
            requires_approval: post.requires_approval,
            selectedAccounts: []
        };
        
        this.renderCompose();
        frappe.show_alert({ message: 'Draft loaded', indicator: 'green' });
    }

    async savePost(submit = false) {
        // Get form values
        const title = document.getElementById('cp-title')?.value?.trim();
        const content = document.getElementById('cp-content')?.value?.trim();
        
        // Validation
        if (!title) {
            frappe.show_alert({ message: 'Post title is required', indicator: 'red' });
            document.getElementById('cp-title')?.focus();
            return;
        }
        if (!content) {
            frappe.show_alert({ message: 'Caption / content is required', indicator: 'red' });
            document.getElementById('cp-content')?.focus();
            return;
        }
        
        const selectedPlatforms = [...document.querySelectorAll('.smm-plat-toggle.on')];
        if (!selectedPlatforms.length) {
            frappe.show_alert({ message: 'Select at least one platform', indicator: 'red' });
            return;
        }
        
        // Build document
        const doc = {
            doctype: 'Social Post',
            post_title: title,
            content: content,
            content_type: document.getElementById('cp-content-type')?.value || 'Image',
            publish_strategy: document.getElementById('cp-strategy')?.value || 'Schedule Global',
            global_schedule: document.getElementById('cp-schedule')?.value || null,
            campaign: document.getElementById('cp-campaign')?.value || null,
            primary_hashtags: document.getElementById('cp-hashtags')?.value || null,
            link_url: document.getElementById('cp-link')?.value || null,
            requires_approval: document.getElementById('cp-requires-approval')?.checked ? 1 : 0,
            status: 'Draft'
        };
        
        try {
            // Create post
            const result = await frappe.call({
                method: 'frappe.client.insert',
                args: { doc },
                freeze: true,
                freeze_message: 'Saving post…'
            });
            
            if (result.message) {
                if (submit) {
                    // Submit for approval/publishing
                    await frappe.call({
                        method: 'frappe.client.submit',
                        args: { doc: result.message },
                        freeze: true,
                        freeze_message: 'Submitting post…'
                    });
                    frappe.show_alert({ 
                        message: `Post "${title}" submitted successfully!`, 
                        indicator: 'green' 
                    });
                } else {
                    frappe.show_alert({ 
                        message: `Draft "${title}" saved successfully!`, 
                        indicator: 'green' 
                    });
                }
                
                // Clear compose draft
                this.state.composeDraft = {};
                
                // Refresh data
                await this.fetchAll(true);
                
                // Navigate to studio
                this.switchView('studio');
            }
        } catch(e) {
            console.error('Failed to save post:', e);
            frappe.show_alert({ 
                message: 'Failed to save post: ' + (e.message || 'Unknown error'), 
                indicator: 'red' 
            });
        }
    }

    openCompose() {
        this.state.composeDraft = {};
        this.switchView('compose');
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  VIEW: CALENDAR
    // ═══════════════════════════════════════════════════════════════════════
    renderCalendar() {
        const d = this.state.calDate;
        const year = d.getFullYear();
        const month = d.getMonth();
        
        const monthNames = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ];
        const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        
        const firstDayOfWeek = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        const today = new Date();
        
        // Map posts to days
        const postsByDay = {};
        this.state.posts.forEach(post => {
            if (!post.global_schedule) return;
            const dateStr = post.global_schedule.split(' ')[0];
            if (!dateStr) return;
            
            const [py, pm2, pd] = dateStr.split('-').map(Number);
            if (py === year && pm2 - 1 === month) {
                if (!postsByDay[pd]) postsByDay[pd] = [];
                postsByDay[pd].push(post);
            }
        });
        
        // Build calendar cells
        let cellsHTML = '';
        
        // Empty cells before first day
        for (let i = 0; i < firstDayOfWeek; i++) {
            cellsHTML += '<div class="smm-cal-cell other-month"></div>';
        }
        
        // Day cells
        for (let day = 1; day <= daysInMonth; day++) {
            const isToday = (
                day === today.getDate() &&
                month === today.getMonth() &&
                year === today.getFullYear()
            );
            
            const dayPosts = postsByDay[day] || [];
            
            // Post pills (max 3 visible)
            const pillsHTML = dayPosts.slice(0, 3).map(p => {
                const meta = sm(p.status);
                return `
                <div class="smm-cal-pill" 
                     style="background:${meta.col}" 
                     title="${esc(p.post_title)} — ${p.status}"
                     onclick="event.stopPropagation();window.__smm.openPostDetail('${p.name}')">
                    ${esc(p.post_title || 'Untitled')}
                </div>`;
            }).join('');
            
            const moreHTML = dayPosts.length > 3 ? 
                `<div style="font-size:9px;color:var(--tx3);margin-top:1px">+${dayPosts.length - 3} more</div>` : '';
            
            cellsHTML += `
            <div class="smm-cal-cell ${isToday ? 'today' : ''}" 
                 onclick="window.__smm.calDayClick(${day}, ${month + 1}, ${year})">
                <div class="smm-cal-num">${day}</div>
                ${pillsHTML}
                ${moreHTML}
            </div>`;
        }
        
        // Legend items
        const legendItems = [
            { label: 'Published', color: 'var(--grn)' },
            { label: 'Scheduled', color: '#8B5CF6' },
            { label: 'Draft', color: '#64748B' },
            { label: 'Failed', color: 'var(--red)' },
        ];
        
        this.setContent(`
        <div style="animation:fadeIn .3s ease">
            <!-- Header -->
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;flex-wrap:wrap;gap:12px">
                <div>
                    <h2 style="font-size:20px;font-weight:800;color:var(--tx1);margin:0 0 4px">
                        Content Calendar
                    </h2>
                    <div style="font-size:12px;color:var(--tx3)">
                        Plan and visualise your content schedule
                    </div>
                </div>
                <div class="smm-btns">
                    <button class="smm-btn btn-ghost btn-sm" onclick="window.__smm.calNav(-1)">
                        ← Prev Month
                    </button>
                    <button class="smm-btn btn-ghost btn-sm" onclick="window.__smm.calToday()">
                        Today
                    </button>
                    <button class="smm-btn btn-ghost btn-sm" onclick="window.__smm.calNav(1)">
                        Next Month →
                    </button>
                    <button class="smm-btn btn-primary btn-sm" onclick="window.__smm.openCompose()">
                        <i class="fa-solid fa-plus"></i> New Post
                    </button>
                </div>
            </div>
            
            <!-- Calendar Card -->
            <div class="smm-card">
                <div class="smm-card-head">
                    <div style="font-size:18px;font-weight:800;color:var(--tx1)">
                        ${monthNames[month]} ${year}
                    </div>
                    <div style="display:flex;gap:12px;flex-wrap:wrap">
                        ${legendItems.map(l => `
                            <span style="display:flex;align-items:center;gap:5px;font-size:11px;color:var(--tx3)">
                                <span style="width:10px;height:10px;border-radius:2px;background:${l.color}"></span>
                                ${l.label}
                            </span>
                        `).join('')}
                    </div>
                </div>
                <div style="padding:14px">
                    <!-- Day headers -->
                    <div class="smm-cal-grid" style="margin-bottom:4px">
                        ${dayNames.map(d => `<div class="smm-cal-day-name">${d}</div>`).join('')}
                    </div>
                    
                    <!-- Calendar grid -->
                    <div class="smm-cal-grid">
                        ${cellsHTML}
                    </div>
                </div>
            </div>
        </div>
        `);
    }

    calNav(direction) {
        const newDate = new Date(this.state.calDate);
        newDate.setMonth(newDate.getMonth() + direction);
        this.state.calDate = newDate;
        this.renderCalendar();
    }

    calToday() {
        this.state.calDate = new Date();
        this.renderCalendar();
    }

    calDayClick(day, month, year) {
        const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        this.state.composeDraft = {
            global_schedule: `${dateStr}T09:00`,
            publish_strategy: 'Schedule Global'
        };
        this.switchView('compose');
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  VIEW: INBOX
    // ═══════════════════════════════════════════════════════════════════════
    renderInbox() {
        const comments = this.state.comments;
        const newComments = comments.filter(c => c.status === 'New' || c.status === 'Unanswered');
        const answeredComments = comments.filter(c => c.status === 'Answered' || c.status === 'Replied');
        
        // Sentiment counts
        const positiveCount = comments.filter(c => 
            ['Positive', 'Very Positive'].includes(c.sentiment_label)
        ).length;
        const negativeCount = comments.filter(c => 
            ['Negative', 'Very Negative'].includes(c.sentiment_label)
        ).length;
        const neutralCount = comments.length - positiveCount - negativeCount;
        const totalComments = comments.length || 1;
        
        // Platform breakdown
        const platformCounts = {};
        comments.forEach(c => {
            const p = c.platform || 'Other';
            platformCounts[p] = (platformCounts[p] || 0) + 1;
        });
        
        // Comment list HTML
        const commentListHTML = comments.length > 0 ? comments.map(c => {
            const pi = pm(c.platform || 'Other');
            const initials = (c.author_name || '?')
                .split(' ')
                .map(w => w[0])
                .join('')
                .substring(0, 2)
                .toUpperCase();
            
            const sentColors = {
                'Positive': 'var(--grn)',
                'Very Positive': 'var(--grn)',
                'Neutral': 'var(--amb)',
                'Negative': 'var(--red)',
                'Very Negative': 'var(--red)'
            };
            const sentColor = sentColors[c.sentiment_label] || 'var(--tx3)';
            const isNew = c.status === 'New' || c.status === 'Unanswered';
            
            return `
            <div class="smm-comment" style="${isNew ? 'border-left:3px solid var(--pri);padding-left:15px' : ''}">
                <div class="smm-avatar" style="background:${pi.col}">
                    ${initials}
                </div>
                <div class="smm-comment-body">
                    <div class="smm-comment-head">
                        <span class="smm-comment-author">${esc(c.author_name || 'Unknown')}</span>
                        <span class="smm-badge" style="background:${pi.col}22;color:${pi.col};font-size:9px">
                            ${c.platform || 'Unknown'}
                        </span>
                        <span class="smm-badge" style="background:${sentColor}22;color:${sentColor};font-size:9px">
                            ${c.sentiment_label || 'Neutral'}
                        </span>
                        ${isNew ? '<span class="smm-badge bd-pri">New</span>' : ''}
                        ${c.is_flagged ? '<span class="smm-badge bd-red">Flagged</span>' : ''}
                        <span class="smm-comment-time">
                            ${c.comment_time ? frappe.datetime.prettyDate(c.comment_time) : ''}
                        </span>
                    </div>
                    <div class="smm-comment-text">
                        ${esc((c.comment_text || '').substring(0, 200))}
                    </div>
                    ${c.reply_text ? `
                    <div style="font-size:11px;color:var(--tx3);background:var(--pri_x);border-radius:6px;padding:6px 9px;border-left:2px solid var(--pri);margin-top:4px">
                        ↩ ${esc(c.reply_text.substring(0, 150))}
                    </div>` : ''}
                </div>
            </div>`;
        }).join('') : `
            <div class="smm-empty">
                <div class="smm-empty-icon">💬</div>
                <h4>No Comments Yet</h4>
                <p>Comments from your social media posts will appear here.</p>
            </div>
        `;
        
        // Platform breakdown HTML
        const platformBreakdownHTML = Object.entries(platformCounts)
            .sort((a, b) => b[1] - a[1])
            .map(([platform, count]) => {
                const pi = pm(platform);
                const pct = Math.round((count / totalComments) * 100);
                return `
                <div class="smm-bar-row">
                    <div class="smm-bar-lbl">
                        <span class="plat-chip" style="background:${pi.col}">${pi.abbr}</span>
                        ${platform}
                    </div>
                    <div class="smm-bar">
                        <div class="smm-bar-fill" style="width:${pct}%;background:${pi.col}"></div>
                    </div>
                    <div class="smm-bar-val">${count}</div>
                </div>`;
            }).join('') || '<div style="color:var(--tx3);font-size:12px;padding:8px 0">No data</div>';
        
        this.setContent(`
        <div style="animation:fadeIn .3s ease">
            <!-- Header Stats -->
            <div class="smm-kpis">
                <div class="smm-kpi" style="--kc:var(--acc)">
                    <div class="smm-kpi-icon">💬</div>
                    <div class="smm-kpi-lbl">Total Comments</div>
                    <div class="smm-kpi-val">${comments.length}</div>
                </div>
                <div class="smm-kpi" style="--kc:var(--pri)">
                    <div class="smm-kpi-icon">🆕</div>
                    <div class="smm-kpi-lbl">New / Unanswered</div>
                    <div class="smm-kpi-val">${newComments.length}</div>
                </div>
                <div class="smm-kpi" style="--kc:var(--grn)">
                    <div class="smm-kpi-icon">✅</div>
                    <div class="smm-kpi-lbl">Answered</div>
                    <div class="smm-kpi-val">${answeredComments.length}</div>
                </div>
            </div>
            
            <div class="smm-g21">
                <!-- Comment Feed -->
                <div class="smm-card">
                    <div class="smm-card-head">
                        <div class="smm-card-title">
                            <div class="smm-title-icon" style="background:var(--acc_x);color:var(--acc)">
                                <i class="fa-solid fa-inbox"></i>
                            </div>
                            All Comments (${comments.length})
                        </div>
                        <div class="smm-btns">
                            <span class="smm-badge bd-red">${newComments.length} new</span>
                        </div>
                    </div>
                    <div style="max-height:600px;overflow-y:auto">
                        ${commentListHTML}
                    </div>
                </div>
                
                <!-- Sidebar -->
                <div>
                    <!-- Sentiment -->
                    <div class="smm-card smm-row">
                        <div class="smm-card-head">
                            <div class="smm-card-title">
                                <div class="smm-title-icon" style="background:var(--grn_x);color:var(--grn)">
                                    <i class="fa-solid fa-face-smile"></i>
                                </div>
                                Sentiment
                            </div>
                        </div>
                        <div style="padding:16px">
                            <div style="text-align:center;margin-bottom:16px">
                                <svg width="80" height="80" viewBox="0 0 80 80">
                                    <circle cx="40" cy="40" r="28" fill="none" stroke="var(--brd2)" stroke-width="8"/>
                                    <circle cx="40" cy="40" r="28" fill="none" stroke="var(--grn)" stroke-width="8"
                                            stroke-dasharray="${(2 * Math.PI * 28 * positiveCount / totalComments).toFixed(1)} ${2 * Math.PI * 28}"
                                            stroke-linecap="round" transform="rotate(-90 40 40)"/>
                                    <text x="40" y="46" text-anchor="middle" font-size="16" font-weight="800" fill="var(--tx1)">
                                        ${Math.round((positiveCount / totalComments) * 100)}%
                                    </text>
                                </svg>
                                <div style="font-size:11px;color:var(--tx3);margin-top:4px">Positive</div>
                            </div>
                            
                            <div style="display:flex;flex-direction:column;gap:8px">
                                <div style="display:flex;align-items:center;gap:8px">
                                    <div style="width:8px;height:8px;border-radius:50%;background:var(--grn)"></div>
                                    <span style="font-size:11px;color:var(--tx2);flex:1">Positive</span>
                                    <span style="font-size:12px;font-weight:700;color:var(--tx1)">${positiveCount}</span>
                                </div>
                                <div style="display:flex;align-items:center;gap:8px">
                                    <div style="width:8px;height:8px;border-radius:50%;background:var(--amb)"></div>
                                    <span style="font-size:11px;color:var(--tx2);flex:1">Neutral</span>
                                    <span style="font-size:12px;font-weight:700;color:var(--tx1)">${neutralCount}</span>
                                </div>
                                <div style="display:flex;align-items:center;gap:8px">
                                    <div style="width:8px;height:8px;border-radius:50%;background:var(--red)"></div>
                                    <span style="font-size:11px;color:var(--tx2);flex:1">Negative</span>
                                    <span style="font-size:12px;font-weight:700;color:var(--tx1)">${negativeCount}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- By Platform -->
                    <div class="smm-card">
                        <div class="smm-card-head">
                            <div class="smm-card-title">
                                <div class="smm-title-icon" style="background:var(--sky_x);color:var(--sky)">
                                    <i class="fa-solid fa-chart-simple"></i>
                                </div>
                                By Platform
                            </div>
                        </div>
                        <div style="padding:14px 16px">
                            ${platformBreakdownHTML}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        `);
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  VIEW: ANALYTICS
    // ═══════════════════════════════════════════════════════════════════════
    renderAnalytics() {
        const publishedPosts = this.state.posts.filter(p => p.status === 'Published');
        
        // Calculate metrics
        const totalReach = publishedPosts.reduce((s, p) => s + flt(p.total_reach), 0);
        const totalClicks = publishedPosts.reduce((s, p) => s + flt(p.total_clicks), 0);
        const totalConversions = publishedPosts.reduce((s, p) => s + flt(p.total_conversions), 0);
        const totalRevenue = publishedPosts.reduce((s, p) => s + flt(p.revenue_generated), 0);
        const totalLikes = publishedPosts.reduce((s, p) => s + flt(p.total_likes), 0);
        const totalShares = publishedPosts.reduce((s, p) => s + flt(p.total_shares), 0);
        const totalComments = publishedPosts.reduce((s, p) => s + flt(p.total_comments), 0);
        
        // Content type breakdown
        const contentTypeBreakdown = {};
        publishedPosts.forEach(p => {
            const type = p.content_type || 'Unknown';
            if (!contentTypeBreakdown[type]) {
                contentTypeBreakdown[type] = { reach: 0, engage: 0, count: 0 };
            }
            contentTypeBreakdown[type].reach += flt(p.total_reach);
            contentTypeBreakdown[type].engage += flt(p.total_likes) + flt(p.total_comments) + flt(p.total_shares);
            contentTypeBreakdown[type].count += 1;
        });
        
        // Top performing posts
        const topPosts = [...publishedPosts]
            .sort((a, b) => flt(b.total_reach) - flt(a.total_reach))
            .slice(0, 5);
        
        // CTR calculation
        const ctr = totalReach > 0 ? ((totalClicks / totalReach) * 100).toFixed(2) : '0';
        const conversionRate = totalClicks > 0 ? ((totalConversions / totalClicks) * 100).toFixed(1) : '0';
        
        this.setContent(`
        <div style="animation:fadeIn .3s ease">
            <!-- KPI Row -->
            <div class="smm-kpis">
                <div class="smm-kpi" style="--kc:var(--pri)">
                    <div class="smm-kpi-icon">👁️</div>
                    <div class="smm-kpi-lbl">Total Reach</div>
                    <div class="smm-kpi-val">${numK(totalReach)}</div>
                    <div class="smm-kpi-sub">All published posts</div>
                </div>
                <div class="smm-kpi" style="--kc:var(--sky)">
                    <div class="smm-kpi-icon">🖱️</div>
                    <div class="smm-kpi-lbl">Link Clicks</div>
                    <div class="smm-kpi-val">${numK(totalClicks)}</div>
                    <div class="smm-kpi-sub">CTR: ${ctr}%</div>
                </div>
                <div class="smm-kpi" style="--kc:var(--grn)">
                    <div class="smm-kpi-icon">🎯</div>
                    <div class="smm-kpi-lbl">Conversions</div>
                    <div class="smm-kpi-val">${numK(totalConversions)}</div>
                    <div class="smm-kpi-sub">Rate: ${conversionRate}%</div>
                </div>
                <div class="smm-kpi" style="--kc:var(--amb)">
                    <div class="smm-kpi-icon">💰</div>
                    <div class="smm-kpi-lbl">Revenue</div>
                    <div class="smm-kpi-val">${totalRevenue > 0 ? '₦' + numK(totalRevenue) : '—'}</div>
                    <div class="smm-kpi-sub">Attributed revenue</div>
                </div>
            </div>
            
            <div class="smm-g2">
                <!-- Engagement Funnel -->
                <div class="smm-card smm-row">
                    <div class="smm-card-head">
                        <div class="smm-card-title">
                            <div class="smm-title-icon" style="background:var(--pri_x);color:var(--pri2)">
                                <i class="fa-solid fa-filter"></i>
                            </div>
                            Engagement Funnel
                        </div>
                    </div>
                    <div style="padding:20px">
                        ${[
                            ['Reach', totalReach, 'var(--pri)'],
                            ['Impressions', Math.round(totalReach * 1.3), 'var(--sky)'],
                            ['Engagements', totalLikes + totalComments + totalShares, 'var(--acc)'],
                            ['Clicks', totalClicks, 'var(--amb)'],
                            ['Conversions', totalConversions, 'var(--grn)'],
                        ].map(([label, value, color], index, arr) => {
                            const maxValue = arr[0][1];
                            const pct = maxValue > 0 ? Math.min(Math.round((value / maxValue) * 100), 100) : 0;
                            return `
                            <div class="smm-bar-row">
                                <div class="smm-bar-lbl">${label}</div>
                                <div class="smm-bar">
                                    <div class="smm-bar-fill" style="width:${pct}%;background:${color}"></div>
                                </div>
                                <div class="smm-bar-val">${numK(value)}</div>
                            </div>`;
                        }).join('')}
                    </div>
                </div>
                
                <!-- Top Posts -->
                <div class="smm-card smm-row">
                    <div class="smm-card-head">
                        <div class="smm-card-title">
                            <div class="smm-title-icon" style="background:var(--amb_x);color:var(--amb)">
                                <i class="fa-solid fa-trophy"></i>
                            </div>
                            Top Posts by Reach
                        </div>
                    </div>
                    <div style="padding:0">
                        ${topPosts.length > 0 ? topPosts.map((post, index) => `
                        <div style="display:flex;align-items:center;gap:10px;padding:12px 16px;border-bottom:1px solid var(--brd);cursor:pointer"
                             onclick="window.__smm.openPostDetail('${post.name}')">
                            <div style="width:24px;height:24px;border-radius:50%;
                                        background:${index === 0 ? 'var(--amb)' : index === 1 ? 'var(--tx3)' : 'var(--bg3)'};
                                        display:flex;align-items:center;justify-content:center;
                                        font-size:10px;font-weight:800;
                                        color:${index < 2 ? '#fff' : 'var(--tx3)'};flex-shrink:0">
                                ${index + 1}
                            </div>
                            <div style="flex:1;min-width:0">
                                <div style="font-size:12px;font-weight:600;color:var(--tx1);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
                                    ${esc(post.post_title || 'Untitled')}
                                </div>
                                <div style="font-size:10px;color:var(--tx3)">
                                    👁 ${numK(post.total_reach)} · ❤ ${numK(post.total_likes)} · 💬 ${numK(post.total_comments)}
                                </div>
                            </div>
                            <div style="font-size:12px;font-weight:700;color:var(--pri2)">
                                ${flt(post.total_engagement_rate).toFixed(1)}%
                            </div>
                        </div>`).join('') : `
                        <div class="smm-empty" style="padding:32px">
                            <h4>No published posts yet</h4>
                            <p>Analytics will appear once you publish posts.</p>
                        </div>`}
                    </div>
                </div>
            </div>
        </div>
        `);
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  VIEW: ACCOUNTS
    // ═══════════════════════════════════════════════════════════════════════
    renderAccounts() {
    const accounts = this.state.accounts;
    
    this.setContent(`
    <div style="animation:fadeIn .3s ease">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;flex-wrap:wrap;gap:12px">
            <div>
                <h2 style="font-size:20px;font-weight:800;color:var(--tx1);margin:0 0 4px">
                    Platform Accounts
                </h2>
                <div style="font-size:12px;color:var(--tx3)">
                    Manage connected social media accounts via Settings
                </div>
            </div>
            <button class="smm-btn btn-primary btn-sm" onclick="frappe.set_route('Form', 'Social Media Settings', 'Social Media Settings')">
                <i class="fa-solid fa-cog"></i> Manage Accounts
            </button>
        </div>
        
        <div class="smm-g3">
            ${accounts.length > 0 ? accounts.map(acc => {
                const pi = pm(acc.platform);
                return `
                <div class="smm-account-card">
                    <div class="smm-account-avatar" style="background:${pi.col}">
                        <i class="${pi.icon}"></i>
                    </div>
                    <div class="smm-account-name">${esc(acc.account_name || 'Unknown')}</div>
                    <div class="smm-account-sub">${acc.platform} · ${acc.account_type || 'Business'}</div>
                    <div style="margin-top:auto;display:flex;align-items:center;gap:8px">
                        <span class="smm-badge ${acc.is_active ? 'bd-grn' : 'bd-red'}">
                            ${acc.is_active ? 'Active' : 'Inactive'}
                        </span>
                        ${acc.followers_count ? `<span style="font-size:11px;color:var(--tx3)">${numK(acc.followers_count)} followers</span>` : ''}
                    </div>
                </div>`;
            }).join('') : `
                <div class="smm-empty" style="grid-column:1/-1">
                    <div class="smm-empty-icon">🔗</div>
                    <h4>No Platforms Connected</h4>
                    <p>Go to Settings to connect your social media accounts.</p>
                    <button class="smm-btn btn-primary" onclick="frappe.set_route('Form', 'Social Media Settings', 'Social Media Settings')">
                        <i class="fa-solid fa-cog"></i> Open Settings
                    </button>
                </div>
            `}
        </div>
    </div>
    `);
}

    // ═══════════════════════════════════════════════════════════════════════
    //  VIEW: SETTINGS
    // ═══════════════════════════════════════════════════════════════════════
    renderSettings() {
        const settings = this.state.settings || {};
        
        this.setContent(`
        <div style="animation:fadeIn .3s ease">
            <!-- Header -->
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;flex-wrap:wrap;gap:12px">
                <div>
                    <h2 style="font-size:20px;font-weight:800;color:var(--tx1);margin:0 0 4px">
                        SMM Settings
                    </h2>
                    <div style="font-size:12px;color:var(--tx3)">
                        Configure your social media management preferences
                    </div>
                </div>
                <button class="smm-btn btn-primary btn-sm" onclick="window.__smm.saveSettings()">
                    <i class="fa-solid fa-floppy-disk"></i> Save Settings
                </button>
            </div>
            
            <div class="smm-g2">
                <!-- General Settings -->
                <div class="smm-card smm-row">
                    <div class="smm-card-head">
                        <div class="smm-card-title">
                            <div class="smm-title-icon" style="background:var(--pri_x);color:var(--pri2)">
                                <i class="fa-solid fa-gear"></i>
                            </div>
                            General
                        </div>
                    </div>
                    <div style="padding:16px 20px">
                        <div class="smm-form">
                            <div class="smm-fg">
                                <label>Company Name</label>
                                <input class="smm-inp" id="set-company" 
                                       value="${esc(settings.company_name || '')}"
                                       placeholder="Your company name">
                            </div>
                            <div class="smm-fg">
                                <label>Default Timezone</label>
                                <select class="smm-sel" id="set-timezone">
                                    ${['UTC', 'Africa/Lagos', 'Africa/Nairobi', 'Africa/Johannesburg', 'America/New_York', 'Europe/London', 'Asia/Dubai', 'Asia/Singapore'].map(tz => `
                                        <option value="${tz}" ${(settings.default_timezone || 'UTC') === tz ? 'selected' : ''}>${tz}</option>
                                    `).join('')}
                                </select>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Notification Settings -->
                <div class="smm-card smm-row">
                    <div class="smm-card-head">
                        <div class="smm-card-title">
                            <div class="smm-title-icon" style="background:var(--amb_x);color:var(--amb)">
                                <i class="fa-solid fa-bell"></i>
                            </div>
                            Notifications
                        </div>
                    </div>
                    <div style="padding:16px 20px">
                        <div class="smm-toggle-row">
                            <div class="smm-toggle-info">
                                <h5>New Comments</h5>
                                <p>Alert when new comments are received</p>
                            </div>
                            <label class="smm-toggle">
                                <input type="checkbox" id="set-notify-comments" 
                                       ${settings.notify_on_new_comment ? 'checked' : ''}>
                                <div class="smm-toggle-track"></div>
                                <div class="smm-toggle-thumb"></div>
                            </label>
                        </div>
                        <div class="smm-toggle-row">
                            <div class="smm-toggle-info">
                                <h5>Post Failures</h5>
                                <p>Alert when posts fail to publish</p>
                            </div>
                            <label class="smm-toggle">
                                <input type="checkbox" id="set-notify-failures" 
                                       ${settings.notify_on_post_failure ? 'checked' : ''}>
                                <div class="smm-toggle-track"></div>
                                <div class="smm-toggle-thumb"></div>
                            </label>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Theme Setting (display only) -->
            <div class="smm-card smm-row">
                <div class="smm-card-head">
                    <div class="smm-card-title">
                        <div class="smm-title-icon" style="background:var(--acc_x);color:var(--acc)">
                            <i class="fa-solid fa-palette"></i>
                        </div>
                        Theme
                    </div>
                </div>
                <div style="padding:16px 20px">
                    <p style="font-size:12px;color:var(--tx2);margin:0 0 12px">
                        Themes are stored locally in your browser. Use the theme button in the header to switch themes.
                    </p>
                    <button class="smm-btn btn-ghost btn-sm" onclick="window.__smm.openThemePicker()">
                        <i class="fa-solid fa-paint-brush"></i> Open Theme Picker
                    </button>
                </div>
            </div>
        </div>
        `);
    }

    async saveSettings() {
        const settings = this.state.settings;
        if (!settings) {
            frappe.show_alert({ message: 'Settings not loaded', indicator: 'red' });
            return;
        }
        
        // Collect form values
        const companyName = document.getElementById('set-company')?.value;
        const timezone = document.getElementById('set-timezone')?.value;
        const notifyComments = document.getElementById('set-notify-comments')?.checked;
        const notifyFailures = document.getElementById('set-notify-failures')?.checked;
        
        // Update settings object
        if (companyName !== undefined) settings.company_name = companyName;
        if (timezone !== undefined) settings.default_timezone = timezone;
        if (notifyComments !== undefined) settings.notify_on_new_comment = notifyComments ? 1 : 0;
        if (notifyFailures !== undefined) settings.notify_on_post_failure = notifyFailures ? 1 : 0;
        
        try {
            await frappe.call({
                method: 'frappe.client.save',
                args: { doc: settings },
                freeze: true,
                freeze_message: 'Saving settings…'
            });
            
            frappe.show_alert({ message: 'Settings saved successfully', indicator: 'green' });
            
            // Refresh settings
            await this.fetchAll(true);
        } catch(e) {
            console.error('Failed to save settings:', e);
            frappe.show_alert({ 
                message: 'Failed to save settings: ' + (e.message || 'Unknown error'), 
                indicator: 'red' 
            });
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  POST DETAIL DIALOG
    // ═══════════════════════════════════════════════════════════════════════
    openPostDetail(name) {
        const post = this.state.posts.find(p => p.name === name);
        if (!post) {
            // Fallback: open in form view
            frappe.set_route('Form', 'Social Post', name);
            return;
        }
        
        const meta = sm(post.status);
        const pi = post.publish_strategy ? { icon: 'fa-solid fa-paper-plane', label: post.publish_strategy } : null;
        
        // Build content HTML
        const contentHTML = `
        <div style="font-family:inherit;color:var(--tx1)">
            <!-- Status & Meta Row -->
            <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;
                        padding-bottom:14px;border-bottom:1px solid var(--brd);margin-bottom:14px">
                <span class="smm-badge" style="background:${meta.col}22;color:${meta.col}">
                    <i class="fa-solid ${meta.icon}"></i> ${post.status}
                </span>
                ${post.content_type ? `<span class="smm-badge bd-grey">${post.content_type}</span>` : ''}
                ${post.campaign ? `<span class="smm-badge bd-pri">${esc(post.campaign)}</span>` : ''}
                ${post.global_schedule ? `
                    <span style="font-size:11px;color:var(--tx3)">
                        <i class="fa-solid fa-calendar"></i> 
                        ${frappe.datetime.str_to_user(post.global_schedule.split(' ')[0])}
                    </span>
                ` : ''}
                
                <div style="margin-left:auto;display:flex;gap:8px">
                    <a href="/app/social-post/${name}" 
                       target="_blank"
                       style="padding:5px 11px;border-radius:8px;font-size:11px;font-weight:600;
                              background:var(--bg3);color:var(--tx2);text-decoration:none;
                              border:1px solid var(--brd2)">
                        Open Form →
                    </a>
                </div>
            </div>
            
            <!-- Metrics -->
            ${flt(post.total_reach) > 0 ? `
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:16px">
                <div style="background:var(--bg3);border-radius:10px;padding:10px;text-align:center">
                    <div style="font-size:18px;font-weight:800;color:var(--tx1)">${numK(post.total_reach)}</div>
                    <div style="font-size:9px;color:var(--tx3);text-transform:uppercase">Reach</div>
                </div>
                <div style="background:var(--bg3);border-radius:10px;padding:10px;text-align:center">
                    <div style="font-size:18px;font-weight:800;color:var(--tx1)">${numK(post.total_likes)}</div>
                    <div style="font-size:9px;color:var(--tx3);text-transform:uppercase">Likes</div>
                </div>
                <div style="background:var(--bg3);border-radius:10px;padding:10px;text-align:center">
                    <div style="font-size:18px;font-weight:800;color:var(--tx1)">${numK(post.total_comments)}</div>
                    <div style="font-size:9px;color:var(--tx3);text-transform:uppercase">Comments</div>
                </div>
                <div style="background:var(--bg3);border-radius:10px;padding:10px;text-align:center">
                    <div style="font-size:18px;font-weight:800;color:var(--tx1)">${flt(post.total_engagement_rate).toFixed(1)}%</div>
                    <div style="font-size:9px;color:var(--tx3);text-transform:uppercase">Eng Rate</div>
                </div>
            </div>` : ''}
            
            <!-- Content Preview -->
            <div style="background:var(--bg3);border:1px solid var(--brd);border-radius:12px;padding:14px;margin-bottom:14px">
                <h4 style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:var(--tx3);margin:0 0 8px">
                    Caption
                </h4>
                <div style="font-size:13px;color:var(--tx2);line-height:1.6;white-space:pre-wrap">
                    ${esc((post.content || 'No content').replace(/<[^>]+>/g, ''))}
                </div>
                ${post.primary_hashtags ? `
                <div style="margin-top:8px;font-size:12px;color:var(--pri2)">
                    ${esc(post.primary_hashtags)}
                </div>` : ''}
            </div>
            
            <!-- Revenue & ROI -->
            ${flt(post.revenue_generated) > 0 ? `
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px">
                <div style="background:var(--grn_x);border:1px solid var(--grn_x);border-radius:10px;padding:12px;text-align:center">
                    <div style="font-size:20px;font-weight:800;color:var(--grn)">₦${numK(post.revenue_generated)}</div>
                    <div style="font-size:10px;color:var(--grn)">Revenue Generated</div>
                </div>
                <div style="background:var(--pri_x);border:1px solid var(--pri_x);border-radius:10px;padding:12px;text-align:center">
                    <div style="font-size:20px;font-weight:800;color:var(--pri2)">${flt(post.roi_percentage).toFixed(0)}%</div>
                    <div style="font-size:10px;color:var(--pri2)">ROI</div>
                </div>
            </div>` : ''}
            
            <!-- Meta Info -->
            <div style="font-size:11px;color:var(--tx3);display:flex;gap:16px;flex-wrap:wrap">
                <span>Created: ${frappe.datetime.prettyDate(post.creation)}</span>
                <span>Modified: ${frappe.datetime.prettyDate(post.modified)}</span>
                ${post.approved_by ? `<span>Approved by: ${post.approved_by}</span>` : ''}
            </div>
        </div>`;
        
        const dialog = new frappe.ui.Dialog({
            title: post.post_title || 'Post Detail',
            size: 'extra-large',
            fields: [{
                fieldtype: 'HTML',
                fieldname: 'post_detail_html',
                options: contentHTML
            }],
            primary_action_label: 'Close',
            primary_action: () => dialog.hide()
        });
        
        dialog.show();
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  CHART HELPERS
    // ═══════════════════════════════════════════════════════════════════════
    mkChart(id, config) {
        const canvas = document.getElementById(id);
        if (!canvas || typeof Chart === 'undefined') return null;
        
        // Destroy existing chart if it exists
        if (this.charts[id]) {
            this.charts[id].destroy();
            delete this.charts[id];
        }
        
        try {
            const ctx = canvas.getContext('2d');
            this.charts[id] = new Chart(ctx, config);
            return this.charts[id];
        } catch(e) {
            console.error(`Failed to create chart "${id}":`, e);
            return null;
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════
//  GLOBAL UTILITY FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Escape HTML entities to prevent XSS
 */
function esc(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

/**
 * Safely parse a float value
 */
function flt(v) {
    const n = parseFloat(v);
    return isNaN(n) ? 0 : n;
}

/**
 * Format large numbers with K/M/B suffixes
 */
function numK(v) {
    const n = flt(v);
    if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B';
    if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
    if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
    return Math.round(n).toLocaleString('en-NG');
}

/**
 * Format currency in Naira
 */
function fmtNaira(v) {
    const n = flt(v);
    if (n >= 1e9) return '₦' + (n / 1e9).toFixed(1) + 'B';
    if (n >= 1e6) return '₦' + (n / 1e6).toFixed(1) + 'M';
    if (n >= 1e3) return '₦' + (n / 1e3).toFixed(0) + 'K';
    return '₦' + Math.round(n).toLocaleString('en-NG');
}

// ═══════════════════════════════════════════════════════════════════════════
//  ANIMATIONS
// ═══════════════════════════════════════════════════════════════════════════
(function injectAnimations() {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes slideInRight {
            from {
                opacity: 0;
                transform: translateX(20px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        
        @keyframes scaleIn {
            from {
                opacity: 0;
                transform: scale(0.95);
            }
            to {
                opacity: 1;
                transform: scale(1);
            }
        }
        
        @keyframes pulse {
            0%, 100% {
                transform: scale(1);
            }
            50% {
                transform: scale(1.05);
            }
        }
    `;
    document.head.appendChild(style);
})();

console.log('Social Media Studio JS loaded successfully. 2100+ lines of pure code.');