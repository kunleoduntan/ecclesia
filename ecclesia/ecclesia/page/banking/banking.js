// Copyright (c) 2026, Value Impacts Consulting
// ecclesia/ecclesia/page/banking/banking.js
//
// ╔══════════════════════════════════════════════════════════════════════════╗
// ║   BANKING STUDIO — Multi-Theme Receipts & Payments Command Center        ║
// ║   9 Light Themes · AI Intelligence · Invoice Matching · GL Preview       ║
// ╚══════════════════════════════════════════════════════════════════════════╝

frappe.pages['banking'] = frappe.pages['banking'] || {};
frappe.pages['banking'].on_page_load = function (wrapper) {
    const boot = () => {
        try {
            new BankingStudio(wrapper);
        } catch (e) {
            console.error('Banking Studio init error:', e);
            $(wrapper).html(`
                <div style="padding:60px;text-align:center;color:#EF4444;font-family:system-ui">
                    <div style="font-size:32px;margin-bottom:12px">⚠️</div>
                    <div style="font-size:16px;font-weight:700">Banking Studio failed to load</div>
                    <div style="font-size:12px;color:#6B7280;margin-top:8px;font-family:monospace">${e.message||e}</div>
                    <button onclick="location.reload()" style="margin-top:20px;padding:8px 20px;background:#6366F1;color:#fff;border:none;border-radius:8px;cursor:pointer;font-weight:700">Reload</button>
                </div>
            `);
        }
    };
    
    if (!document.getElementById('fa-banking')) {
        const fa = document.createElement('link');
        fa.id = 'fa-banking'; 
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
//  9 LIGHT THEMES — Pure localStorage, zero DB dependency
// ═══════════════════════════════════════════════════════════════════════════
const BNK_THEMES = {
    crystal: {
        name: 'Crystal', icon: '💎', isDark: false,
        colors: {
            bg: '#F8FAFC', bg2: '#F1F5F9', bg3: '#E2E8F0', card: '#FFFFFF',
            brd: '#E2E8F0', brd2: '#CBD5E1', tx1: '#0F172A', tx2: '#475569', tx3: '#94A3B8',
            pri: '#6366F1', pri_d: '#4F46E5', pri2: '#818CF8', pri_x: 'rgba(99,102,241,.08)',
            acc: '#8B5CF6', acc_x: 'rgba(139,92,246,.08)',
            grn: '#10B981', grn_x: 'rgba(16,185,129,.08)',
            red: '#EF4444', red_x: 'rgba(239,68,68,.08)',
            amb: '#F59E0B', amb_x: 'rgba(245,158,11,.08)',
            vio: '#A78BFA', vio_x: 'rgba(167,139,250,.08)',
            banner_r: 'linear-gradient(135deg,#059669 0%,#10B981 50%,#34D399 100%)',
            banner_p: 'linear-gradient(135deg,#4F46E5 0%,#6366F1 50%,#818CF8 100%)'
        }
    },
    mint: {
        name: 'Mint', icon: '🌿', isDark: false,
        colors: {
            bg: '#ECFDF5', bg2: '#D1FAE5', bg3: '#A7F3D0', card: '#FFFFFF',
            brd: '#A7F3D0', brd2: '#6EE7B7', tx1: '#022C22', tx2: '#065F46', tx3: '#34D399',
            pri: '#059669', pri_d: '#047857', pri2: '#34D399', pri_x: 'rgba(5,150,105,.08)',
            acc: '#10B981', acc_x: 'rgba(16,185,129,.08)',
            grn: '#059669', grn_x: 'rgba(5,150,105,.08)',
            red: '#EF4444', red_x: 'rgba(239,68,68,.08)',
            amb: '#F59E0B', amb_x: 'rgba(245,158,11,.08)',
            vio: '#8B5CF6', vio_x: 'rgba(139,92,246,.08)',
            banner_r: 'linear-gradient(135deg,#022C22 0%,#059669 50%,#10B981 100%)',
            banner_p: 'linear-gradient(135deg,#064E3B 0%,#047857 50%,#059669 100%)'
        }
    },
    ocean: {
        name: 'Ocean', icon: '🌊', isDark: false,
        colors: {
            bg: '#F0F9FF', bg2: '#E0F2FE', bg3: '#BAE6FD', card: '#FFFFFF',
            brd: '#BAE6FD', brd2: '#7DD3FC', tx1: '#0C4A6E', tx2: '#075985', tx3: '#38BDF8',
            pri: '#0EA5E9', pri_d: '#0284C7', pri2: '#38BDF8', pri_x: 'rgba(14,165,233,.08)',
            acc: '#06B6D4', acc_x: 'rgba(6,182,212,.08)',
            grn: '#10B981', grn_x: 'rgba(16,185,129,.08)',
            red: '#EF4444', red_x: 'rgba(239,68,68,.08)',
            amb: '#F59E0B', amb_x: 'rgba(245,158,11,.08)',
            vio: '#8B5CF6', vio_x: 'rgba(139,92,246,.08)',
            banner_r: 'linear-gradient(135deg,#0C4A6E 0%,#0284C7 50%,#0EA5E9 100%)',
            banner_p: 'linear-gradient(135deg,#0C4A6E 0%,#0284C7 50%,#0EA5E9 100%)'
        }
    },
    rose: {
        name: 'Rose', icon: '🌹', isDark: false,
        colors: {
            bg: '#FFF1F2', bg2: '#FFE4E6', bg3: '#FECDD3', card: '#FFFFFF',
            brd: '#FECDD3', brd2: '#FDA4AF', tx1: '#4C0519', tx2: '#881337', tx3: '#FB7185',
            pri: '#E11D48', pri_d: '#BE123C', pri2: '#FB7185', pri_x: 'rgba(225,29,72,.08)',
            acc: '#EC4899', acc_x: 'rgba(236,72,153,.08)',
            grn: '#10B981', grn_x: 'rgba(16,185,129,.08)',
            red: '#EF4444', red_x: 'rgba(239,68,68,.08)',
            amb: '#F59E0B', amb_x: 'rgba(245,158,11,.08)',
            vio: '#8B5CF6', vio_x: 'rgba(139,92,246,.08)',
            banner_r: 'linear-gradient(135deg,#4C0519 0%,#BE123C 50%,#E11D48 100%)',
            banner_p: 'linear-gradient(135deg,#4C0519 0%,#BE123C 50%,#E11D48 100%)'
        }
    },
    amber: {
        name: 'Amber', icon: '🔥', isDark: false,
        colors: {
            bg: '#FFFBEB', bg2: '#FEF3C7', bg3: '#FDE68A', card: '#FFFFFF',
            brd: '#FDE68A', brd2: '#FCD34D', tx1: '#451A03', tx2: '#78350F', tx3: '#FBBF24',
            pri: '#D97706', pri_d: '#B45309', pri2: '#FBBF24', pri_x: 'rgba(217,119,6,.08)',
            acc: '#F59E0B', acc_x: 'rgba(245,158,11,.08)',
            grn: '#10B981', grn_x: 'rgba(16,185,129,.08)',
            red: '#EF4444', red_x: 'rgba(239,68,68,.08)',
            amb: '#D97706', amb_x: 'rgba(217,119,6,.08)',
            vio: '#8B5CF6', vio_x: 'rgba(139,92,246,.08)',
            banner_r: 'linear-gradient(135deg,#451A03 0%,#B45309 50%,#D97706 100%)',
            banner_p: 'linear-gradient(135deg,#451A03 0%,#B45309 50%,#D97706 100%)'
        }
    },
    lavender: {
        name: 'Lavender', icon: '🪻', isDark: false,
        colors: {
            bg: '#F5F3FF', bg2: '#EDE9FE', bg3: '#DDD6FE', card: '#FFFFFF',
            brd: '#DDD6FE', brd2: '#C4B5FD', tx1: '#2E1065', tx2: '#5B21B6', tx3: '#A78BFA',
            pri: '#7C3AED', pri_d: '#6D28D9', pri2: '#A78BFA', pri_x: 'rgba(124,58,237,.08)',
            acc: '#8B5CF6', acc_x: 'rgba(139,92,246,.08)',
            grn: '#10B981', grn_x: 'rgba(16,185,129,.08)',
            red: '#EF4444', red_x: 'rgba(239,68,68,.08)',
            amb: '#F59E0B', amb_x: 'rgba(245,158,11,.08)',
            vio: '#7C3AED', vio_x: 'rgba(124,58,237,.08)',
            banner_r: 'linear-gradient(135deg,#2E1065 0%,#6D28D9 50%,#7C3AED 100%)',
            banner_p: 'linear-gradient(135deg,#2E1065 0%,#6D28D9 50%,#7C3AED 100%)'
        }
    },
    sage: {
        name: 'Sage', icon: '🍃', isDark: false,
        colors: {
            bg: '#F7FEE7', bg2: '#ECFCCB', bg3: '#D9F99D', card: '#FFFFFF',
            brd: '#D9F99D', brd2: '#BEF264', tx1: '#1A2E05', tx2: '#3F6212', tx3: '#84CC16',
            pri: '#65A30D', pri_d: '#4D7C0F', pri2: '#84CC16', pri_x: 'rgba(101,163,13,.08)',
            acc: '#A3E635', acc_x: 'rgba(163,230,53,.08)',
            grn: '#10B981', grn_x: 'rgba(16,185,129,.08)',
            red: '#EF4444', red_x: 'rgba(239,68,68,.08)',
            amb: '#F59E0B', amb_x: 'rgba(245,158,11,.08)',
            vio: '#8B5CF6', vio_x: 'rgba(139,92,246,.08)',
            banner_r: 'linear-gradient(135deg,#1A2E05 0%,#4D7C0F 50%,#65A30D 100%)',
            banner_p: 'linear-gradient(135deg,#1A2E05 0%,#4D7C0F 50%,#65A30D 100%)'
        }
    },
    sky: {
        name: 'Sky', icon: '☁️', isDark: false,
        colors: {
            bg: '#F0F9FF', bg2: '#E0F2FE', bg3: '#BAE6FD', card: '#FFFFFF',
            brd: '#BAE6FD', brd2: '#7DD3FC', tx1: '#082F49', tx2: '#0369A1', tx3: '#0EA5E9',
            pri: '#0284C7', pri_d: '#0369A1', pri2: '#38BDF8', pri_x: 'rgba(2,132,199,.08)',
            acc: '#06B6D4', acc_x: 'rgba(6,182,212,.08)',
            grn: '#10B981', grn_x: 'rgba(16,185,129,.08)',
            red: '#EF4444', red_x: 'rgba(239,68,68,.08)',
            amb: '#F59E0B', amb_x: 'rgba(245,158,11,.08)',
            vio: '#8B5CF6', vio_x: 'rgba(139,92,246,.08)',
            banner_r: 'linear-gradient(135deg,#082F49 0%,#0369A1 50%,#0284C7 100%)',
            banner_p: 'linear-gradient(135deg,#082F49 0%,#0369A1 50%,#0284C7 100%)'
        }
    },
    coral: {
        name: 'Coral', icon: '🪸', isDark: false,
        colors: {
            bg: '#FFF7ED', bg2: '#FFEDD5', bg3: '#FED7AA', card: '#FFFFFF',
            brd: '#FED7AA', brd2: '#FDBA74', tx1: '#431407', tx2: '#9A3412', tx3: '#FB923C',
            pri: '#EA580C', pri_d: '#C2410C', pri2: '#FB923C', pri_x: 'rgba(234,88,12,.08)',
            acc: '#F97316', acc_x: 'rgba(249,115,22,.08)',
            grn: '#10B981', grn_x: 'rgba(16,185,129,.08)',
            red: '#EF4444', red_x: 'rgba(239,68,68,.08)',
            amb: '#F59E0B', amb_x: 'rgba(245,158,11,.08)',
            vio: '#8B5CF6', vio_x: 'rgba(139,92,246,.08)',
            banner_r: 'linear-gradient(135deg,#431407 0%,#C2410C 50%,#EA580C 100%)',
            banner_p: 'linear-gradient(135deg,#431407 0%,#C2410C 50%,#EA580C 100%)'
        }
    }
};

const DEFAULT_THEME = 'crystal';

const STATUS_COLOR = {
    Draft: { c: '#94A3B8', bg: 'rgba(148,163,184,.12)' },
    Pending: { c: '#F59E0B', bg: 'rgba(245,158,11,.12)' },
    'Pending Approval': { c: '#F59E0B', bg: 'rgba(245,158,11,.12)' },
    Approved: { c: '#10B981', bg: 'rgba(16,185,129,.12)' },
    Processing: { c: '#8B5CF6', bg: 'rgba(139,92,246,.12)' },
    Completed: { c: '#10B981', bg: 'rgba(16,185,129,.12)' },
    Failed: { c: '#EF4444', bg: 'rgba(239,68,68,.12)' },
    Cancelled: { c: '#EF4444', bg: 'rgba(239,68,68,.12)' },
    Rejected: { c: '#EF4444', bg: 'rgba(239,68,68,.12)' },
    'Cancel': { c: '#EF4444', bg: 'rgba(239,68,68,.12)' },
};

const TXN_TYPE_ICON = {
    'Supplier Payment': '🏭',
    'Expense Payment':  '🧾',
    'Transfer Out':     '↗️',
    'Supplier Refunds': '↩️',
    'Payment Request':  '📋',
    'Customer Receipt': '💵',
    'Receive from One-Off': '🤝',
    'Revenue Receipt':  '📈',
};

class BankingStudio {
    constructor(wrapper) {
        this.wrapper = wrapper;
        
        this.page = frappe.ui.make_app_page({
            parent: wrapper,
            title: 'Banking Studio',
            single_column: true
        });
        
        this.activeTheme = (() => {
            try { return localStorage.getItem('banking-studio-theme') || DEFAULT_THEME; }
            catch(e) { return DEFAULT_THEME; }
        })();
        
        this.state = {
            activeTab: 'receipts',
            receipts: [],
            payments: [],
            filters: { company: '', bank: '', status: '', from_date: '', to_date: '', search: '' },
            loading: false,
            companies: [],
            banks: [],
            currencies: [],
            suppliers: [],
            customers: [],
            modes_of_payment: [],
            cost_centers: [],
            aiInsights: null,
            fraudAlerts: [],
            cashFlowForecast: [],
            aiRecommendations: []
        };
        
        this.currentDialog = null;
        window.__bnk = this;
        
        requestAnimationFrame(() => this.boot());
    }

    async boot() {
        try {
            this.injectCSS();
            this.buildShell();
            this.applyTheme(this.activeTheme);
            await this.loadMasterData();
            await this.fetchData();
            this.runAIAnalysis();
            this.renderContent();
            this.startAutoRefresh();
        } catch (e) {
            console.error('Banking Studio boot error:', e);
            const content = document.getElementById('bnk-content');
            if (content) {
                content.innerHTML = `
                    <div style="padding:60px;text-align:center;color:#EF4444;font-family:system-ui">
                        <div style="font-size:32px;margin-bottom:12px">⚠️</div>
                        <div style="font-size:16px;font-weight:700">Banking Studio failed to load</div>
                        <div style="font-size:12px;color:#6B7280;margin-top:8px;font-family:monospace">${e.message||e}</div>
                        <button onclick="location.reload()" style="margin-top:20px;padding:8px 20px;background:#6366F1;color:#fff;border:none;border-radius:8px;cursor:pointer;font-weight:700">Reload</button>
                    </div>`;
            }
        }
    }

    applyTheme(key) {
        const theme = BNK_THEMES[key] || BNK_THEMES[DEFAULT_THEME];
        this.activeTheme = key;
        try { localStorage.setItem('banking-studio-theme', key); } catch(e) {}
        const root = document.getElementById('bnk-root');
        if (!root) return;
        Object.entries(theme.colors).forEach(([k, v]) => root.style.setProperty('--' + k, v));
        const label = document.getElementById('bnk-theme-label');
        if (label) label.innerHTML = theme.icon + ' ' + theme.name;
    }

    openThemePicker() {
        const cur = this.activeTheme;
        const cardsHTML = Object.entries(BNK_THEMES).map(([key, theme]) => {
            const isActive = key === cur;
            const dots = ['pri', 'acc', 'grn', 'sky', 'vio'].map(k => `<div style="width:11px;height:11px;border-radius:3px;background:${theme.colors[k]}"></div>`).join('');
            return `
            <div onclick="window.__bnk.applyTheme('${key}');if(window.__bnk_td)window.__bnk_td.hide();"
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
                    <div style="font-size:10px;color:${theme.colors.tx3}">${theme.isDark ? '🌙 Dark' : '☀️ Light'} · localStorage</div>
                </div>
                ${isActive ? `<span style="font-size:18px;color:${theme.colors.pri};flex-shrink:0">✓</span>` : ''}
            </div>`;
        }).join('');
        const d = new frappe.ui.Dialog({
            title: '🎨 Banking Studio Theme',
            size: 'large',
            fields: [{
                fieldtype: 'HTML', fieldname: 'themes',
                options: `<p style="font-size:12px;color:var(--tx3);margin:0 0 14px">Choose from 9 light themes. Changes apply instantly and are stored in your browser.</p>
                <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">${cardsHTML}</div>`
            }]
        });
        window.__bnk_td = d;
        d.show();
    }

    getToday() {
        try {
            if (frappe.datetime && frappe.datetime.get_today) return frappe.datetime.get_today();
        } catch (e) {}
        return new Date().toISOString().split('T')[0];
    }

    getNowDateTime() {
        try {
            if (frappe.datetime && frappe.datetime.now_datetime) return frappe.datetime.now_datetime();
        } catch (e) {}
        return new Date().toISOString();
    }

    injectCSS() {
        if (document.getElementById('bnk-css')) return;
        const s = document.createElement('style');
        s.id = 'bnk-css';
        s.textContent = `
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap');
            #bnk-root {
              --bg: #F8FAFC; --bg2: #F1F5F9; --bg3: #E2E8F0; --card: #FFFFFF;
              --brd: #E2E8F0; --brd2: #CBD5E1; --tx1: #0F172A; --tx2: #475569; --tx3: #94A3B8;
              --pri: #6366F1; --pri_d: #4F46E5; --pri2: #818CF8; --pri_x: rgba(99,102,241,.08);
              --acc: #8B5CF6; --acc_x: rgba(139,92,246,.08);
              --grn: #10B981; --grn_x: rgba(16,185,129,.08);
              --red: #EF4444; --red_x: rgba(239,68,68,.08);
              --amb: #F59E0B; --amb_x: rgba(245,158,11,.08);
              --vio: #A78BFA; --vio_x: rgba(167,139,250,.08);
              font-family: 'Inter', system-ui, sans-serif;
              background: var(--bg);
              color: var(--tx1);
              min-height: 100vh;
              transition: background 0.2s ease, color 0.2s ease;
            }
            #bnk-root * { box-sizing: border-box; }
            .bnk-header {
              background: var(--card);
              border-bottom: 1px solid var(--brd);
              padding: 0 28px;
              display: flex; align-items: stretch; gap: 0;
              height: 60px; position: sticky; top: 0; z-index: 100;
              backdrop-filter: blur(10px);
            }
            .bnk-logo {
              display: flex; align-items: center; gap: 12px;
              font-family: 'Inter', sans-serif; font-size: 16px; font-weight: 800;
              color: var(--tx1); margin-right: 32px; letter-spacing: -.5px;
            }
            .bnk-logo-icon {
              width: 34px; height: 34px; border-radius: 10px;
              background: linear-gradient(135deg,var(--pri),var(--acc));
              display: flex; align-items: center; justify-content: center;
              font-size: 17px; box-shadow: 0 4px 12px rgba(99,102,241,.2);
            }
            .bnk-tabs { display: flex; align-items: stretch; gap: 0; }
            .bnk-tab {
              display: flex; align-items: center; gap: 9px;
              padding: 0 24px; font-size: 13px; font-weight: 600;
              color: var(--tx3); cursor: pointer; border: none; background: none;
              border-bottom: 3px solid transparent; margin-bottom: -1px;
              transition: all .18s; font-family: inherit;
            }
            .bnk-tab:hover { color: var(--tx2); }
            .bnk-tab.active-r { color: var(--grn); border-bottom-color: var(--grn); }
            .bnk-tab.active-p { color: var(--pri2); border-bottom-color: var(--pri2); }
            .bnk-tab-badge {
              font-size: 10px; font-weight: 700; padding: 1px 6px;
              border-radius: 10px; background: var(--bg3); color: var(--tx2);
            }
            .bnk-header-right { display: flex; align-items: center; gap: 10px; margin-left: auto; }
            .bnk-clock { font-family: 'DM Mono', monospace; font-size: 11px; color: var(--tx3); }
            .bnk-filters {
              background: var(--bg2); border-bottom: 1px solid var(--brd);
              padding: 12px 28px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
            }
            .bnk-search-wrap {
              position: relative; flex: 1; min-width: 220px; max-width: 320px;
            }
            .bnk-search {
              width: 100%;
              background: var(--card); border: 1.5px solid var(--brd2); border-radius: 10px;
              color: var(--tx1); font-family: inherit; font-size: 13px; padding: 8px 14px 8px 38px;
              outline: none; transition: border-color .15s;
            }
            .bnk-search:focus { border-color: var(--pri); box-shadow: 0 0 0 3px var(--pri_x); }
            .bnk-search-icon { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--tx3); font-size: 12px; }
            .bnk-sel {
              background: var(--card); border: 1.5px solid var(--brd2); border-radius: 10px;
              color: var(--tx1); font-family: inherit; font-size: 12px; padding: 8px 12px;
              outline: none; cursor: pointer; min-width: 120px;
            }
            .bnk-sel:focus { border-color: var(--pri); }
            .bnk-date-inp {
              background: var(--card); border: 1.5px solid var(--brd2); border-radius: 10px;
              color: var(--tx1); font-family: 'DM Mono', monospace; font-size: 12px; padding: 8px 12px;
              outline: none; width: 130px;
            }
            .bnk-date-inp:focus { border-color: var(--pri); }
            .bnk-content { padding: 24px 28px; max-width: 1800px; }
            .bnk-kpis { display: grid; grid-template-columns: repeat(auto-fit,minmax(150px,1fr)); gap: 12px; margin-bottom: 20px; }
            .bnk-kpi {
              background: var(--card); border: 1px solid var(--brd);
              border-radius: 14px; padding: 16px 18px; position: relative; overflow: hidden;
              box-shadow: 0 1px 2px rgba(0,0,0,.02);
            }
            .bnk-kpi::before { content:''; position:absolute; top:0;left:0;right:0;height:2px;background:var(--kc,var(--pri)); }
            .bnk-kpi:hover { border-color: var(--brd2); transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,.05); }
            .bnk-kpi-lbl { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .8px; color: var(--tx3); margin-bottom: 6px; }
            .bnk-kpi-val { font-family: 'DM Mono', monospace; font-size: 22px; font-weight: 700; color: var(--tx1); line-height: 1; margin-bottom: 3px; }
            .bnk-kpi-sub { font-size: 11px; color: var(--tx3); }
            .bnk-table-wrap {
              background: var(--card); border: 1px solid var(--brd); border-radius: 16px; overflow: hidden;
            }
            .bnk-table-head {
              padding: 14px 20px; border-bottom: 1px solid var(--brd);
              display: flex; align-items: center; justify-content: space-between; gap: 12px;
            }
            .bnk-table-title {
              display: flex; align-items: center; gap: 10px;
              font-family: 'Inter', sans-serif; font-size: 14px; font-weight: 700; color: var(--tx1);
            }
            .bnk-table-icon { width: 30px; height: 30px; border-radius: 9px; display:flex; align-items:center; justify-content:center; font-size:14px; }
            .bnk-tbl { width: 100%; border-collapse: collapse; }
            .bnk-tbl th {
              padding: 10px 14px; text-align: left;
              font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .8px;
              color: var(--tx3); border-bottom: 1px solid var(--brd); background: var(--bg2);
            }
            .bnk-tbl td {
              padding: 12px 14px; border-bottom: 1px solid var(--brd);
              font-size: 12px; color: var(--tx2); vertical-align: middle;
            }
            .bnk-tbl tr:last-child td { border-bottom: none; }
            .bnk-tbl tbody tr { transition: background .12s; cursor: pointer; }
            .bnk-tbl tbody tr:hover td { background: var(--bg3); color: var(--tx1); }
            .bnk-tbl .mono { font-family: 'DM Mono', monospace; }
            .bnk-tbl .amt { font-family: 'DM Mono', monospace; font-weight: 600; text-align: right; }
            .bnk-badge {
              display: inline-flex; align-items: center; gap: 4px;
              padding: 3px 9px; border-radius: 20px; font-size: 10px; font-weight: 700;
            }
            .bnk-btn {
              display: inline-flex; align-items: center; gap: 7px;
              padding: 8px 16px; border-radius: 10px;
              font-size: 12px; font-weight: 600; cursor: pointer;
              border: 1.5px solid transparent;
              font-family: 'Inter', system-ui, sans-serif;
              transition: all .15s;
            }
            .bnk-btn:hover { transform: translateY(-1px); }
            .btn-pri { background: var(--pri); color: #fff; border-color: var(--pri); box-shadow: 0 2px 8px rgba(99,102,241,.25); }
            .btn-pri:hover { background: var(--pri_d); }
            .btn-grn { background: var(--grn_x); color: var(--grn); border-color: rgba(16,185,129,.25); }
            .btn-grn:hover { background: var(--grn); color: #fff; }
            .btn-amb { background: var(--amb_x); color: var(--amb); border-color: rgba(245,158,11,.25); }
            .btn-amb:hover { background: var(--amb); color: #fff; }
            .btn-vio { background: var(--vio_x); color: var(--vio); border-color: rgba(167,139,250,.25); }
            .btn-vio:hover { background: var(--vio); color: #fff; }
            .btn-ghost { background: transparent; color: var(--tx2); border-color: var(--brd2); }
            .btn-ghost:hover { background: var(--bg3); color: var(--tx1); border-color: var(--pri); }
            .btn-red { background: var(--red_x); color: var(--red); border-color: rgba(239,68,68,.25); }
            .btn-red:hover { background: var(--red); color: #fff; }
            .btn-sm { padding: 5px 11px; font-size: 11px; }
            .btn-xs { padding: 3px 8px; font-size: 10px; border-radius: 7px; }
            .bnk-ai-tab-container {
              background: var(--card);
              border: 1px solid var(--brd);
              border-radius: 16px;
              margin-top: 20px;
              overflow: hidden;
            }
            .bnk-ai-tab-header {
              display: flex;
              border-bottom: 1px solid var(--brd);
              background: var(--bg2);
              flex-wrap: wrap;
            }
            .bnk-ai-tab-btn {
              padding: 12px 20px;
              font-size: 12px;
              font-weight: 600;
              color: var(--tx3);
              cursor: pointer;
              border: none;
              background: none;
              transition: all .15s;
              border-bottom: 2px solid transparent;
            }
            .bnk-ai-tab-btn.active {
              color: var(--pri);
              border-bottom-color: var(--pri);
            }
            .bnk-ai-tab-content {
              padding: 20px;
              display: none;
            }
            .bnk-ai-tab-content.active {
              display: block;
            }
            .bnk-ai-card {
              background: var(--bg3);
              border: 1px solid var(--brd2);
              border-radius: 14px;
              padding: 16px 18px;
              margin-bottom: 16px;
            }
            .bnk-ai-title {
              font-size: 11px;
              font-weight: 700;
              text-transform: uppercase;
              letter-spacing: 1px;
              color: var(--pri2);
              margin-bottom: 12px;
              display: flex;
              align-items: center;
              gap: 8px;
            }
            .bnk-ai-insight {
              font-size: 13px;
              line-height: 1.6;
              color: var(--tx1);
              margin-bottom: 8px;
            }
            .bnk-ai-meta {
              font-size: 10px;
              color: var(--tx3);
              margin-top: 8px;
            }
            
            /* Enhanced Dialog Styles */
            .bnk-dialog-modern {
                font-family: 'Inter', system-ui, sans-serif;
            }
            .bnk-dialog-modern .modal-content {
                border-radius: 24px;
                border: none;
                box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
                overflow: hidden;
            }
            .bnk-dialog-modern .modal-header {
                padding: 20px 28px;
                background: linear-gradient(135deg, var(--pri) 0%, var(--acc) 100%);
                border-bottom: none;
            }
            .bnk-dialog-modern .modal-header .modal-title {
                color: white;
                font-weight: 700;
                font-size: 18px;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .bnk-dialog-modern .modal-header .close {
                color: white;
                opacity: 0.8;
                text-shadow: none;
            }
            .bnk-dialog-modern .modal-header .close:hover { opacity: 1; }
            .bnk-dialog-modern .modal-body { padding: 28px; background: var(--bg); max-height: 70vh; overflow-y: auto; }
            .bnk-dialog-modern .modal-footer { padding: 20px 28px; background: var(--card); border-top: 1px solid var(--brd); }
            
            .bnk-form-card {
                background: var(--card);
                border-radius: 20px;
                margin-bottom: 24px;
                overflow: hidden;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                border: 1px solid var(--brd);
            }
            .bnk-form-card-header {
                padding: 16px 20px;
                background: var(--bg2);
                border-bottom: 1px solid var(--brd);
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .bnk-form-card-header i {
                font-size: 18px;
                color: var(--pri);
            }
            .bnk-form-card-header h4 {
                margin: 0;
                font-size: 14px;
                font-weight: 700;
                color: var(--tx1);
                letter-spacing: -0.3px;
            }
            .bnk-form-card-body {
                padding: 20px;
            }
            
            .bnk-form-grid {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 16px;
            }
            .bnk-form-grid-full {
                grid-column: span 2;
            }
            .bnk-field-group {
                display: flex;
                flex-direction: column;
                gap: 6px;
            }
            .bnk-field-label {
                font-size: 11px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                color: var(--tx3);
            }
            .bnk-field-label .required {
                color: var(--red);
                margin-left: 4px;
            }
            .bnk-field-input, .bnk-field-select, .bnk-field-textarea {
                background: var(--card);
                border: 1.5px solid var(--brd2);
                border-radius: 12px;
                padding: 10px 14px;
                font-size: 13px;
                font-family: 'Inter', system-ui;
                color: var(--tx1);
                transition: all 0.2s;
                outline: none;
            }
            .bnk-field-input:focus, .bnk-field-select:focus, .bnk-field-textarea:focus {
                border-color: var(--pri);
                box-shadow: 0 0 0 3px var(--pri_x);
            }
            .bnk-field-textarea { resize: vertical; min-height: 70px; }
            
            .bnk-alloc-table {
                width: 100%;
                border-collapse: collapse;
                font-size: 12px;
            }
            .bnk-alloc-table th {
                padding: 10px 12px;
                text-align: left;
                font-size: 10px;
                font-weight: 700;
                text-transform: uppercase;
                color: var(--tx3);
                background: var(--bg2);
                border-bottom: 1px solid var(--brd);
            }
            .bnk-alloc-table td {
                padding: 12px;
                border-bottom: 1px solid var(--brd);
                color: var(--tx2);
            }
            .bnk-alloc-table tr:last-child td { border-bottom: none; }
            
            .bnk-alloc-summary {
                background: var(--bg2);
                border-radius: 12px;
                padding: 12px 16px;
                margin-top: 12px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
                gap: 10px;
            }
            
            .bnk-options-grid {
                display: flex;
                gap: 20px;
                flex-wrap: wrap;
            }
            .bnk-option-check {
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .bnk-option-check input {
                width: 16px;
                height: 16px;
                margin: 0;
                cursor: pointer;
            }
            .bnk-option-check label {
                font-size: 12px;
                color: var(--tx2);
                cursor: pointer;
            }
            
            @media (max-width: 768px) {
                .bnk-content { padding: 16px; }
                .bnk-filters { padding: 10px 16px; }
                .bnk-header { padding: 0 16px; }
                .bnk-kpis { grid-template-columns: repeat(2,1fr); }
                .bnk-form-grid { grid-template-columns: 1fr; }
                .bnk-form-grid-full { grid-column: span 1; }
            }
        `;
        document.head.appendChild(s);
    }

    buildShell() {
        const pageBody = this.page.body || $(this.wrapper).find('.page-content');
        const root = document.createElement('div');
        root.id = 'bnk-root';
        root.innerHTML = `
            <div class="bnk-header">
                <div class="bnk-logo">
                    <div class="bnk-logo-icon">🏦</div>
                    Banking Studio
                </div>
                <div class="bnk-tabs">
                    <button class="bnk-tab active-r" id="tab-receipts" onclick="__bnk.switchTab('receipts')">
                        <i class="fa fa-arrow-down"></i> Receipts
                        <span class="bnk-tab-badge" id="badge-receipts">—</span>
                    </button>
                    <button class="bnk-tab" id="tab-payments" onclick="__bnk.switchTab('payments')">
                        <i class="fa fa-arrow-up"></i> Payments
                        <span class="bnk-tab-badge" id="badge-payments">—</span>
                    </button>
                </div>
                <div class="bnk-header-right">
                    <button class="bnk-theme-btn" onclick="__bnk.openThemePicker()" style="display:flex;align-items:center;gap:6px;padding:5px 11px;border-radius:8px;font-size:11px;font-weight:600;color:var(--tx2);background:var(--bg3);border:1px solid var(--brd2);cursor:pointer;">
                        <i class="fa-solid fa-palette"></i>
                        <span id="bnk-theme-label">💎 Crystal</span>
                    </button>
                    <button class="bnk-btn btn-amb btn-sm" onclick="__bnk.openMatchDialog()">
                        <i class="fa fa-link"></i> Match Invoices
                    </button>
                    <button class="bnk-btn btn-pri btn-sm" onclick="__bnk.openNewForm()">
                        <i class="fa fa-plus"></i> New
                    </button>
                    <span class="bnk-clock" id="bnk-clock"></span>
                </div>
            </div>
            <div class="bnk-filters">
                <div class="bnk-search-wrap">
                    <i class="fa fa-search bnk-search-icon"></i>
                    <input class="bnk-search" id="bnk-search" type="text" placeholder="Search transactions…" oninput="__bnk.applyFilter('search', this.value)">
                </div>
                <select class="bnk-sel" id="filter-company" onchange="__bnk.applyFilter('company', this.value)">
                    <option value="">All Companies</option>
                </select>
                <select class="bnk-sel" id="filter-bank" onchange="__bnk.applyFilter('bank', this.value)">
                    <option value="">All Banks</option>
                </select>
                <select class="bnk-sel" id="filter-status" onchange="__bnk.applyFilter('status', this.value)">
                    <option value="">All Statuses</option>
                    <option>Draft</option><option>Pending Approval</option>
                    <option>Approved</option><option>Processing</option>
                    <option>Completed</option><option>Failed</option><option>Cancelled</option>
                </select>
                <input type="date" class="bnk-date-inp" id="filter-from" placeholder="From" onchange="__bnk.applyFilter('from_date', this.value)">
                <input type="date" class="bnk-date-inp" id="filter-to" placeholder="To" onchange="__bnk.applyFilter('to_date', this.value)">
                <button class="bnk-btn btn-ghost btn-sm" onclick="__bnk.clearFilters()">
                    <i class="fa fa-times"></i> Clear
                </button>
                <button class="bnk-btn btn-ghost btn-sm" onclick="__bnk.fetchData(true)">
                    <i class="fa fa-sync-alt"></i> Refresh
                </button>
            </div>
            <div class="bnk-content" id="bnk-content">
                <div class="bnk-spinner"><div class="bnk-spinner-icon"></div>Loading banking data…</div>
            </div>
        `;
        if (pageBody) {
            if (typeof pageBody.html === 'function') pageBody.html(root);
            else if (pageBody.appendChild) { pageBody.innerHTML = ''; pageBody.appendChild(root); }
            else $(pageBody).html(root);
        } else $(this.wrapper).html(root);
        this.startClock();
    }

    startClock() {
        const tick = () => {
            const el = document.getElementById('bnk-clock');
            if (el) el.textContent = this.getNowDateTime().substring(0, 16).replace('T', ' ');
        };
        tick();
        this.clockInterval = setInterval(tick, 60000);
    }

    startAutoRefresh() {
        setInterval(() => { this.fetchData(true); this.runAIAnalysis(); }, 60000);
    }

    async runAIAnalysis() {
        try {
            const receipts = this.state.receipts;
            const payments = this.state.payments;
            const totalReceipts = receipts.reduce((s, r) => s + (parseFloat(r.amount_received) || 0), 0);
            const totalPayments = payments.reduce((s, p) => s + (parseFloat(p.amount_paid) || 0), 0);
            const netCashFlow = totalReceipts - totalPayments;
            const weeklyData = this.computeWeeklyTrend(receipts, payments);
            
            this.state.aiInsights = {
                cashFlowHealth: netCashFlow > 0 ? 'Positive' : netCashFlow < 0 ? 'Negative' : 'Neutral',
                netCashFlow: netCashFlow,
                totalReceipts: totalReceipts,
                totalPayments: totalPayments,
                avgTransactionValue: (totalReceipts + totalPayments) / Math.max(1, receipts.length + payments.length),
                pendingApprovals: [...receipts, ...payments].filter(t => (t.receipt_status === 'Pending Approval' || t.payment_status === 'Pending Approval')).length,
                completionRate: receipts.filter(r => r.receipt_status === 'Completed').length + payments.filter(p => p.payment_status === 'Completed').length
            };
            
            this.state.fraudAlerts = [];
            const suspiciousTxns = [...receipts, ...payments].filter(t => {
                const amt = parseFloat(t.amount_received || t.amount_paid) || 0;
                return (amt > 5000000 || (amt % 1000000 === 0 && amt > 500000));
            }).slice(0, 5);
            suspiciousTxns.forEach(t => {
                this.state.fraudAlerts.push({
                    transaction: t.name,
                    amount: parseFloat(t.amount_received || t.amount_paid) || 0,
                    reason: 'Unusually large or round-number transaction',
                    severity: 'Medium',
                    party: t.customer_name || t.supplier_name || t.payer_name || t.payee_name || 'Unknown'
                });
            });
            
            this.state.cashFlowForecast = [];
            const last3WeeksReceipts = weeklyData.slice(-3).map(w => w.receipts);
            const last3WeeksPayments = weeklyData.slice(-3).map(w => w.payments);
            const avgWeeklyReceipts = last3WeeksReceipts.reduce((a,b) => a+b, 0) / Math.max(1, last3WeeksReceipts.length);
            const avgWeeklyPayments = last3WeeksPayments.reduce((a,b) => a+b, 0) / Math.max(1, last3WeeksPayments.length);
            for (let i = 1; i <= 4; i++) {
                this.state.cashFlowForecast.push({
                    week: i,
                    receipts: avgWeeklyReceipts * (1 + (i * 0.02)),
                    payments: avgWeeklyPayments * (1 + (i * 0.015)),
                    net: (avgWeeklyReceipts * (1 + (i * 0.02))) - (avgWeeklyPayments * (1 + (i * 0.015)))
                });
            }
            
            this.state.aiRecommendations = [];
            if (netCashFlow < 0) {
                this.state.aiRecommendations.push({
                    title: '🚨 Negative Cash Flow Detected',
                    description: `Your net cash flow is ₦${Math.abs(netCashFlow).toLocaleString()} negative. Consider accelerating receivables or delaying non-critical payments.`,
                    priority: 'High', action: 'Review outstanding invoices'
                });
            }
            if (this.state.aiInsights.pendingApprovals > 5) {
                this.state.aiRecommendations.push({
                    title: '⏳ Pending Approvals Backlog',
                    description: `${this.state.aiInsights.pendingApprovals} transactions awaiting approval.`,
                    priority: 'Medium', action: 'Review approvals'
                });
            }
            if (totalReceipts > 0 && totalPayments > 0 && (totalReceipts / totalPayments) > 1.5) {
                this.state.aiRecommendations.push({
                    title: '💰 Strong Cash Position',
                    description: `Your receipts are ${Math.round(totalReceipts/totalPayments*100)}% of payments. Consider investing surplus cash.`,
                    priority: 'Low', action: 'Review investment options'
                });
            }
            this.updateAIPanel();
        } catch (e) { console.error('AI Analysis error:', e); }
    }
    
    computeWeeklyTrend(receipts, payments) {
        const weeks = [];
        const now = new Date();
        for (let i = 3; i >= 0; i--) {
            const weekStart = new Date(now);
            weekStart.setDate(now.getDate() - (i * 7));
            const weekEnd = new Date(weekStart);
            weekEnd.setDate(weekStart.getDate() + 7);
            const weekReceipts = receipts.filter(r => { const d = new Date(r.transaction_date); return d >= weekStart && d < weekEnd; }).reduce((s, r) => s + (parseFloat(r.amount_received) || 0), 0);
            const weekPayments = payments.filter(p => { const d = new Date(p.transaction_date); return d >= weekStart && d < weekEnd; }).reduce((s, p) => s + (parseFloat(p.amount_paid) || 0), 0);
            weeks.push({ label: i === 0 ? 'This Week' : i === 1 ? 'Last Week' : i === 2 ? '2 Weeks Ago' : '3 Weeks Ago', receipts: weekReceipts, payments: weekPayments, net: weekReceipts - weekPayments });
        }
        return weeks;
    }
    
    updateAIPanel() {
        const container = document.getElementById('bnk-ai-panel-container');
        if (!container) return;
        const insights = this.state.aiInsights;
        if (!insights) return;
        const weekly = this.computeWeeklyTrend(this.state.receipts, this.state.payments);
        const netCash = insights.netCashFlow || 0;
        container.innerHTML = `
            <div class="bnk-ai-tab-container">
                <div class="bnk-ai-tab-header">
                    <button class="bnk-ai-tab-btn active" data-tab="health" onclick="__bnk.switchAITab('health')"><i class="fa fa-chart-line"></i> Cash Flow Health</button>
                    <button class="bnk-ai-tab-btn" data-tab="fraud" onclick="__bnk.switchAITab('fraud')"><i class="fa fa-shield-alt"></i> Fraud Alerts (${this.state.fraudAlerts.length})</button>
                    <button class="bnk-ai-tab-btn" data-tab="trend" onclick="__bnk.switchAITab('trend')"><i class="fa fa-chart-simple"></i> Weekly Trend</button>
                    <button class="bnk-ai-tab-btn" data-tab="recommend" onclick="__bnk.switchAITab('recommend')"><i class="fa fa-lightbulb"></i> Recommendations</button>
                    <button class="bnk-ai-tab-btn" data-tab="forecast" onclick="__bnk.switchAITab('forecast')"><i class="fa fa-chart-line"></i> 4-Week Forecast</button>
                </div>
                <div id="bnk-ai-tab-health" class="bnk-ai-tab-content active">
                    <div class="bnk-ai-card"><div class="bnk-ai-title"><i class="fa fa-chart-line"></i> Cash Flow Health</div>
                    <div class="bnk-ai-insight"><strong style="color:${netCash >= 0 ? 'var(--grn)' : 'var(--red)'}">${netCash >= 0 ? 'Positive' : 'Negative'} Cash Flow</strong>: ₦${Math.abs(netCash).toLocaleString()} ${netCash >= 0 ? 'surplus' : 'deficit'}</div>
                    <div class="bnk-ai-meta">Receipts: ₦${insights.totalReceipts.toLocaleString()} | Payments: ₦${insights.totalPayments.toLocaleString()}</div></div>
                </div>
                <div id="bnk-ai-tab-fraud" class="bnk-ai-tab-content">
                    ${this.state.fraudAlerts.length > 0 ? `<div class="bnk-ai-card"><div class="bnk-ai-title"><i class="fa fa-shield-alt"></i> Fraud Alerts</div>
                    ${this.state.fraudAlerts.map(alert => `<div class="bnk-ai-insight" style="margin-bottom:12px;border-left:2px solid var(--red);padding-left:10px"><strong>⚠️ ${alert.party}</strong> — ₦${alert.amount.toLocaleString()}<br><span style="font-size:10px;color:var(--tx3)">${alert.reason}</span></div>`).join('')}</div>` : 
                    `<div class="bnk-ai-card"><div class="bnk-ai-title"><i class="fa fa-shield-alt"></i> Fraud Alerts</div><div class="bnk-ai-insight" style="color:var(--tx3)">No unusual transactions detected.</div></div>`}
                </div>
                <div id="bnk-ai-tab-trend" class="bnk-ai-tab-content">
                    <div class="bnk-ai-card"><div class="bnk-ai-title"><i class="fa fa-chart-simple"></i> Weekly Trend</div>
                    ${weekly.map(w => `<div style="display:flex;justify-content:space-between;margin-bottom:8px;font-size:12px"><span>${w.label}</span><span style="color:${w.net >= 0 ? 'var(--grn)' : 'var(--red)'}">${w.net >= 0 ? '+' : ''}₦${w.net.toLocaleString()}</span></div>`).join('')}</div>
                </div>
                <div id="bnk-ai-tab-recommend" class="bnk-ai-tab-content">
                    ${this.state.aiRecommendations.length > 0 ? `<div class="bnk-ai-card"><div class="bnk-ai-title"><i class="fa fa-lightbulb"></i> AI Recommendations</div>
                    ${this.state.aiRecommendations.map(rec => `<div class="bnk-ai-insight" style="margin-bottom:12px"><strong>${rec.title}</strong><br>${rec.description}<div class="bnk-ai-meta">Priority: ${rec.priority}</div></div>`).join('')}</div>` :
                    `<div class="bnk-ai-card"><div class="bnk-ai-title"><i class="fa fa-lightbulb"></i> AI Recommendations</div><div class="bnk-ai-insight" style="color:var(--tx3)">All systems healthy. No recommendations at this time.</div></div>`}
                </div>
                <div id="bnk-ai-tab-forecast" class="bnk-ai-tab-content">
                    <div class="bnk-ai-card"><div class="bnk-ai-title"><i class="fa fa-chart-line"></i> 4-Week Forecast</div>
                    ${this.state.cashFlowForecast.map(f => `<div style="display:flex;justify-content:space-between;margin-bottom:8px;font-size:12px"><span>Week ${f.week}</span><span style="color:${f.net >= 0 ? 'var(--grn)' : 'var(--red)'}">${f.net >= 0 ? '+' : ''}₦${Math.round(f.net).toLocaleString()}</span></div>`).join('')}
                    <div class="bnk-ai-meta" style="margin-top:12px">Based on 3-week moving average</div></div>
                </div>
            </div>
        `;
    }
    
    switchAITab(tabId) {
        document.querySelectorAll('.bnk-ai-tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelector(`.bnk-ai-tab-btn[data-tab="${tabId}"]`).classList.add('active');
        document.querySelectorAll('.bnk-ai-tab-content').forEach(content => content.classList.remove('active'));
        document.getElementById(`bnk-ai-tab-${tabId}`).classList.add('active');
    }

    async loadMasterData() {
        try {
            const [coR, baR, moR, ccR] = await Promise.all([
                frappe.call({ method: 'frappe.client.get_list', args: { doctype: 'Company', fields: ['name'], limit: 50 } }),
                frappe.call({ method: 'frappe.client.get_list', args: { doctype: 'Bank Account', fields: ['name', 'account_currency'], limit: 100 } }),
                frappe.call({ method: 'frappe.client.get_list', args: { doctype: 'Mode of Payment', fields: ['name'], limit: 50 } }),
                frappe.call({ method: 'frappe.client.get_list', args: { doctype: 'Cost Center', fields: ['name'], limit: 100 } })
            ]);
            this.state.companies = (coR.message || []).map(r => r.name);
            this.state.banks = (baR.message || []).map(r => r.name);
            this.state.modes_of_payment = (moR.message || []).map(r => r.name);
            this.state.cost_centers = (ccR.message || []).map(r => r.name);
            const compSel = document.getElementById('filter-company');
            const bankSel = document.getElementById('filter-bank');
            if (compSel) this.state.companies.forEach(c => { compSel.innerHTML += `<option value="${c}">${c}</option>`; });
            if (bankSel) this.state.banks.forEach(b => { bankSel.innerHTML += `<option value="${b}">${b}</option>`; });
        } catch (e) { console.error('Error loading master data:', e); }
    }

    async fetchData(showToast = false) {
        try {
            const f = this.state.filters;
            const baseFields_r = ['name','transaction_date','trans_type','customer_name','payer_name','amount_received','receipt_currency','receipt_status','remittance_bank','mode_of_payment','reference_no','company','create_accounting_entries'];
            const baseFields_p = ['name','transaction_date','trans_type','payee_name','supplier_name','amount_paid','payment_currency','payment_status','remittance_bank','mode_of_payment','reference_no','company','create_accounting_entries'];
            const filters_r = [], filters_p = [];
            if (f.company) { filters_r.push(['company','=',f.company]); filters_p.push(['company','=',f.company]); }
            if (f.bank) { filters_r.push(['remittance_bank','=',f.bank]); filters_p.push(['remittance_bank','=',f.bank]); }
            if (f.status) { filters_r.push(['receipt_status','=',f.status]); filters_p.push(['payment_status','=',f.status]); }
            if (f.from_date) { filters_r.push(['transaction_date','>=',f.from_date]); filters_p.push(['transaction_date','>=',f.from_date]); }
            if (f.to_date) { filters_r.push(['transaction_date','<=',f.to_date]); filters_p.push(['transaction_date','<=',f.to_date]); }
            if (f.search) { filters_r.push(['name','like',`%${f.search}%`]); filters_p.push(['name','like',`%${f.search}%`]); }
            const [rR, pR] = await Promise.all([
                frappe.call({ method: 'frappe.client.get_list', args: { doctype: 'Receipts', fields: baseFields_r, filters: filters_r, limit: 200, order_by: 'transaction_date desc' } }),
                frappe.call({ method: 'frappe.client.get_list', args: { doctype: 'Payments', fields: baseFields_p, filters: filters_p, limit: 200, order_by: 'transaction_date desc' } })
            ]);
            this.state.receipts = rR.message || [];
            this.state.payments = pR.message || [];
            const br = document.getElementById('badge-receipts');
            const bp = document.getElementById('badge-payments');
            if (br) br.textContent = this.state.receipts.length;
            if (bp) bp.textContent = this.state.payments.length;
            if (showToast) frappe.show_alert({ message: 'Data refreshed', indicator: 'green' });
            this.renderContent();
            await this.runAIAnalysis();
        } catch (e) { console.error('Error fetching data:', e); if (showToast) frappe.show_alert({ message: 'Error fetching data: ' + e.message, indicator: 'red' }); }
    }

    switchTab(tab) {
        this.state.activeTab = tab;
        const tabR = document.getElementById('tab-receipts');
        const tabP = document.getElementById('tab-payments');
        if (tabR) tabR.className = 'bnk-tab' + (tab === 'receipts' ? ' active-r' : '');
        if (tabP) tabP.className = 'bnk-tab' + (tab === 'payments' ? ' active-p' : '');
        this.renderContent();
    }

    applyFilter(key, val) { this.state.filters[key] = val; this.fetchData(); }

    clearFilters() {
        this.state.filters = { company: '', bank: '', status: '', from_date: '', to_date: '', search: '' };
        const search = document.getElementById('bnk-search');
        const company = document.getElementById('filter-company');
        const bank = document.getElementById('filter-bank');
        const status = document.getElementById('filter-status');
        const from = document.getElementById('filter-from');
        const to = document.getElementById('filter-to');
        if (search) search.value = '';
        if (company) company.value = '';
        if (bank) bank.value = '';
        if (status) status.value = '';
        if (from) from.value = '';
        if (to) to.value = '';
        this.fetchData();
    }

    renderContent() {
        const content = document.getElementById('bnk-content');
        if (!content) return;
        if (this.state.activeTab === 'receipts') content.innerHTML = this.renderReceiptsView();
        else content.innerHTML = this.renderPaymentsView();
        const aiContainer = document.createElement('div');
        aiContainer.id = 'bnk-ai-panel-container';
        const mainContent = content.querySelector('.bnk-kpis');
        if (mainContent && mainContent.parentNode) mainContent.parentNode.insertBefore(aiContainer, mainContent.nextSibling);
        else if (content.firstChild) content.appendChild(aiContainer);
        this.updateAIPanel();
    }

    fmtCurr(val, curr = 'NGN') {
        if (!val || isNaN(val)) return '₦0.00';
        const sym = curr === 'USD' ? '$' : curr === 'EUR' ? '€' : curr === 'GBP' ? '£' : '₦';
        try { return sym + parseFloat(val).toLocaleString('en-NG', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
        catch (e) { return sym + '0.00'; }
    }

    fmtDate(d) { return d ? d.substring(0, 10) : '—'; }

    statusBadge(status) {
        const s = STATUS_COLOR[status] || { c: '#94A3B8', bg: 'rgba(148,163,184,.12)' };
        return `<span class="bnk-badge" style="background:${s.bg};color:${s.c}">${status || 'Draft'}</span>`;
    }

    renderKPIs(data, amtField, currField) {
        const total = data.reduce((s, r) => s + (parseFloat(r[amtField]) || 0), 0);
        const completed = data.filter(r => ['Completed', 'Approved'].includes(r[currField === 'receipt_currency' ? 'receipt_status' : 'payment_status']));
        const pending = data.filter(r => ['Draft', 'Pending', 'Pending Approval'].includes(r[currField === 'receipt_currency' ? 'receipt_status' : 'payment_status']));
        const totalCompleted = completed.reduce((s, r) => s + (parseFloat(r[amtField]) || 0), 0);
        const isR = currField === 'receipt_currency';
        return `
        <div class="bnk-kpis">
            <div class="bnk-kpi" style="--kc:${isR ? 'var(--grn)' : 'var(--pri)'}">
                <div class="bnk-kpi-lbl">Total ${isR ? 'Receipts' : 'Payments'}</div>
                <div class="bnk-kpi-val">${data.length}</div><div class="bnk-kpi-sub">transactions</div>
            </div>
            <div class="bnk-kpi" style="--kc:${isR ? 'var(--grn)' : 'var(--pri)'}">
                <div class="bnk-kpi-lbl">Total Amount</div>
                <div class="bnk-kpi-val" style="font-size:16px">${this.fmtCurr(total)}</div><div class="bnk-kpi-sub">all records</div>
            </div>
            <div class="bnk-kpi" style="--kc:var(--grn)">
                <div class="bnk-kpi-lbl">Completed</div>
                <div class="bnk-kpi-val">${completed.length}</div><div class="bnk-kpi-sub">${this.fmtCurr(totalCompleted)}</div>
            </div>
            <div class="bnk-kpi" style="--kc:var(--amb)">
                <div class="bnk-kpi-lbl">Pending</div><div class="bnk-kpi-val">${pending.length}</div><div class="bnk-kpi-sub">awaiting action</div>
            </div>
            <div class="bnk-kpi" style="--kc:var(--vio)">
                <div class="bnk-kpi-lbl">With Accounting</div>
                <div class="bnk-kpi-val">${data.filter(r => r.create_accounting_entries).length}</div><div class="bnk-kpi-sub">GL entries created</div>
            </div>
        </div>`;
    }

    renderReceiptsView() {
        const data = this.state.receipts;
        const kpis = this.renderKPIs(data, 'amount_received', 'receipt_currency');
        if (!data.length) return kpis + `<div class="bnk-table-wrap"><div class="bnk-empty"><div class="bnk-empty-icon">📥</div><div class="bnk-empty-title">No Receipts Found</div><div class="bnk-empty-sub">Adjust your filters or create a new receipt</div></div></div>`;
        const rows = data.map(r => `
            <tr onclick="__bnk.openDocForm('Receipts','${r.name}')">
                <td class="mono doc-link">${r.name || '—'}</td>
                <td>${this.fmtDate(r.transaction_date)}</td>
                <td><span class="bnk-badge" style="background:var(--bg3);color:var(--tx2)">${TXN_TYPE_ICON[r.trans_type] || '💵'} ${r.trans_type || '—'}</span></td>
                <td>${r.customer_name || r.payer_name || '—'}</td>
                <td class="amt" style="color:var(--grn)">${this.fmtCurr(r.amount_received, r.receipt_currency)}</td>
                <td>${r.remittance_bank || '—'}</td>
                <td class="mono">${r.reference_no || '—'}</td>
                <td>${this.statusBadge(r.receipt_status)}</td>
                <td><div style="display:flex;gap:6px"><button class="bnk-btn btn-ghost btn-xs" onclick="event.stopPropagation();__bnk.openDocForm('Receipts','${r.name}')"><i class="fa fa-pencil"></i></button><button class="bnk-btn btn-amb btn-xs" onclick="event.stopPropagation();__bnk.openMatchForDoc('Receipts','${r.name}','${r.customer_name||''}')"><i class="fa fa-link"></i></button></div></td>
            </tr>`).join('');
        return kpis + `<div class="bnk-table-wrap"><div class="bnk-table-head"><div class="bnk-table-title"><div class="bnk-table-icon" style="background:rgba(16,185,129,.12);color:var(--grn)">📥</div>Receipts — <span style="color:var(--tx3);font-size:12px">${data.length} records</span></div><div class="bnk-action-row"><button class="bnk-btn btn-grn btn-sm" onclick="__bnk.openNewReceiptForm()"><i class="fa fa-plus"></i> New Receipt</button></div></div><div style="overflow-x:auto"><table class="bnk-tbl"><thead><tr><th>Reference</th><th>Date</th><th>Type</th><th>From</th><th style="text-align:right">Amount</th><th>Bank</th><th>Ref No</th><th>Status</th><th>Actions</th></tr></thead><tbody>${rows}</tbody></table></div></div>`;
    }

    renderPaymentsView() {
        const data = this.state.payments;
        const kpis = this.renderKPIs(data, 'amount_paid', 'payment_currency');
        if (!data.length) return kpis + `<div class="bnk-table-wrap"><div class="bnk-empty"><div class="bnk-empty-icon">📤</div><div class="bnk-empty-title">No Payments Found</div><div class="bnk-empty-sub">Adjust your filters or create a new payment</div></div></div>`;
        const rows = data.map(r => `
            <tr onclick="__bnk.openDocForm('Payments','${r.name}')">
                <td class="mono doc-link">${r.name || '—'}</td>
                <td>${this.fmtDate(r.transaction_date)}</td>
                <td><span class="bnk-badge" style="background:var(--bg3);color:var(--tx2)">${TXN_TYPE_ICON[r.trans_type] || '📤'} ${r.trans_type || '—'}</span></td>
                <td>${r.payee_name || r.supplier_name || '—'}</td>
                <td class="amt" style="color:var(--red)">${this.fmtCurr(r.amount_paid, r.payment_currency)}</td>
                <td>${r.remittance_bank || '—'}</td>
                <td class="mono">${r.reference_no || '—'}</td>
                <td>${this.statusBadge(r.payment_status)}</td>
                <td><div style="display:flex;gap:6px"><button class="bnk-btn btn-ghost btn-xs" onclick="event.stopPropagation();__bnk.openDocForm('Payments','${r.name}')"><i class="fa fa-pencil"></i></button><button class="bnk-btn btn-amb btn-xs" onclick="event.stopPropagation();__bnk.openMatchForDoc('Payments','${r.name}','${r.payee_name||r.supplier_name||''}')"><i class="fa fa-link"></i></button></div></td>
            </tr>`).join('');
        return kpis + `<div class="bnk-table-wrap"><div class="bnk-table-head"><div class="bnk-table-title"><div class="bnk-table-icon" style="background:rgba(99,102,241,.12);color:var(--pri2)">📤</div>Payments — <span style="color:var(--tx3);font-size:12px">${data.length} records</span></div><div class="bnk-action-row"><button class="bnk-btn btn-pri btn-sm" onclick="__bnk.openNewPaymentForm()"><i class="fa fa-plus"></i> New Payment</button></div></div><div style="overflow-x:auto"><table class="bnk-tbl"><thead><tr><th>Reference</th><th>Date</th><th>Type</th><th>To</th><th style="text-align:right">Amount</th><th>Bank</th><th>Ref No</th><th>Status</th><th>Actions</th></tr></thead><tbody>${rows}</tbody></table></div></div>`;
    }

    openDocForm(doctype, name) { if (name) frappe.set_route('Form', doctype, name); }

    openNewForm() {
        if (this.state.activeTab === 'receipts') this.openNewReceiptForm();
        else this.openNewPaymentForm();
    }

    openNewReceiptForm() {
        const mopOptions = this.state.modes_of_payment.map(m => `<option value="${m}">${m}</option>`).join('');
        const companyOptions = this.state.companies.map(c => `<option value="${c}">${c}</option>`).join('');
        const bankOptions = this.state.banks.map(b => `<option value="${b}">${b}</option>`).join('');
        const today = this.getToday();
        
        const dialog = new frappe.ui.Dialog({
            title: 'New Receipt',
            size: 'large',
            css_class: 'bnk-dialog-modern',
            fields: [{ fieldtype: 'HTML', fieldname: 'form_html', options: `
                <div id="rcp-form-container">
                    <!-- Transaction Details Card -->
                    <div class="bnk-form-card">
                        <div class="bnk-form-card-header">
                            <i class="fa fa-info-circle"></i>
                            <h4>Transaction Details</h4>
                        </div>
                        <div class="bnk-form-card-body">
                            <div class="bnk-form-grid">
                                <div class="bnk-field-group">
                                    <label class="bnk-field-label">Date <span class="required">*</span></label>
                                    <input type="date" class="bnk-field-input" id="rcp-date" value="${today}">
                                </div>
                                <div class="bnk-field-group">
                                    <label class="bnk-field-label">Transaction Type</label>
                                    <select class="bnk-field-select" id="rcp-type">
                                        <option value="Customer Receipt">💵 Customer Receipt</option>
                                        <option value="Receive from One-Off">🤝 Receive from One-Off</option>
                                        <option value="Revenue Receipt">📈 Revenue Receipt</option>
                                    </select>
                                </div>
                                <div class="bnk-field-group">
                                    <label class="bnk-field-label">Company <span class="required">*</span></label>
                                    <select class="bnk-field-select" id="rcp-company">${companyOptions}</select>
                                </div>
                                <div class="bnk-field-group">
                                    <label class="bnk-field-label">Customer / Payer Name</label>
                                    <input type="text" class="bnk-field-input" id="rcp-payer" placeholder="Search customer or enter payer name">
                                </div>
                                <div class="bnk-field-group bnk-form-grid-full">
                                    <label class="bnk-field-label">Payer Name (Free Text)</label>
                                    <input type="text" class="bnk-field-input" id="rcp-payer-name" placeholder="Beneficiary name if no customer">
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Amount & Payment Card -->
                    <div class="bnk-form-card">
                        <div class="bnk-form-card-header">
                            <i class="fa fa-money-bill-wave"></i>
                            <h4>Amount & Payment</h4>
                        </div>
                        <div class="bnk-form-card-body">
                            <div class="bnk-form-grid">
                                <div class="bnk-field-group">
                                    <label class="bnk-field-label">Amount Received <span class="required">*</span></label>
                                    <input type="number" class="bnk-field-input" id="rcp-amount" placeholder="0.00" step="0.01" oninput="__bnk.updateRcpGL()">
                                </div>
                                <div class="bnk-field-group">
                                    <label class="bnk-field-label">Mode of Payment</label>
                                    <select class="bnk-field-select" id="rcp-mop"><option value="">— Select —</option>${mopOptions}</select>
                                </div>
                                <div class="bnk-field-group">
                                    <label class="bnk-field-label">Cheque / Ref No <span class="required">*</span></label>
                                    <input type="text" class="bnk-field-input" id="rcp-ref" placeholder="Bank reference / cheque no">
                                </div>
                                <div class="bnk-field-group">
                                    <label class="bnk-field-label">Bank Account <span class="required">*</span></label>
                                    <select class="bnk-field-select" id="rcp-bank">${bankOptions}</select>
                                </div>
                                <div class="bnk-field-group bnk-form-grid-full">
                                    <label class="bnk-field-label">Account to Credit</label>
                                    <input type="text" class="bnk-field-input" id="rcp-credit-acct" placeholder="GL account to credit (income/debtor)">
                                </div>
                                <div class="bnk-field-group bnk-form-grid-full">
                                    <label class="bnk-field-label">Transaction Purpose</label>
                                    <textarea class="bnk-field-textarea" id="rcp-purpose" placeholder="Describe the reason for this receipt…" rows="2"></textarea>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Invoice Allocation Card -->
                    <div class="bnk-form-card">
                        <div class="bnk-form-card-header">
                            <i class="fa fa-link"></i>
                            <h4>Invoice Allocation (Optional)</h4>
                        </div>
                        <div class="bnk-form-card-body">
                            <div style="margin-bottom:12px;font-size:11px;color:var(--tx3);">
                                Allocate this receipt against outstanding sales invoices. The total allocated amount will be applied to the selected invoices.
                            </div>
                            <div class="bnk-match-tbl-wrap">
                                <table class="bnk-alloc-table">
                                    <thead><tr><th>Sales Invoice</th><th style="text-align:right">Outstanding</th><th style="text-align:right">Allocate</th><th style="width:40px"></th></tr></thead>
                                    <tbody id="rcp-alloc-body"><tr id="rcp-alloc-empty"><td colspan="4" style="text-align:center;color:var(--tx3);padding:30px;">No invoices added. Click "Load Outstanding" to fetch.</td></tr></tbody>
                                </table>
                            </div>
                            <div style="display:flex;gap:10px;margin-top:12px;">
                                <button type="button" class="bnk-btn btn-ghost btn-sm" onclick="__bnk.loadOutstandingSales()"><i class="fa fa-download"></i> Load Outstanding</button>
                                <button type="button" class="bnk-btn btn-amb btn-sm" onclick="__bnk.addManualRcpRow()"><i class="fa fa-plus"></i> Add Row</button>
                            </div>
                            <div id="rcp-alloc-summary" class="bnk-alloc-summary" style="margin-top:12px;"></div>
                        </div>
                    </div>
                    
                    <!-- Options Card -->
                    <div class="bnk-form-card">
                        <div class="bnk-form-card-header">
                            <i class="fa fa-sliders-h"></i>
                            <h4>Options</h4>
                        </div>
                        <div class="bnk-form-card-body">
                            <div class="bnk-options-grid">
                                <div class="bnk-option-check"><input type="checkbox" id="rcp-create-gl" checked><label for="rcp-create-gl">Create Accounting Entries</label></div>
                                <div class="bnk-option-check"><input type="checkbox" id="rcp-deduct-wht"><label for="rcp-deduct-wht">Deduct WHT (5%)</label></div>
                                <div class="bnk-option-check"><input type="checkbox" id="rcp-is-multi"><label for="rcp-is-multi">Multi-Line Items</label></div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- GL Preview Card -->
                    <div class="bnk-form-card" id="rcp-gl-card" style="display:none;">
                        <div class="bnk-form-card-header">
                            <i class="fa fa-book"></i>
                            <h4>GL Entry Preview</h4>
                        </div>
                        <div class="bnk-form-card-body">
                            <table class="bnk-alloc-table">
                                <thead><tr><th>Account</th><th style="text-align:right">Debit</th><th style="text-align:right">Credit</th><th>Remark</th></tr></thead>
                                <tbody id="rcp-gl-body"></tbody>
                            </table>
                        </div>
                    </div>
                </div>
            ` }],
            primary_action_label: '<i class="fa fa-check"></i> Save & Submit',
            primary_action: () => this.saveReceipt(true),
            secondary_action_label: '<i class="fa fa-save"></i> Save Draft',
            secondary_action: () => this.saveReceipt(false)
        });
        
        dialog.show();
        this.currentDialog = dialog;
        
        setTimeout(() => {
            const $footer = dialog.$wrapper.find('.modal-footer');
            $footer.prepend('<button type="button" class="btn btn-sm btn-default" onclick="__bnk.previewRcpGL()" style="margin-right:10px"><i class="fa fa-eye"></i> Preview GL</button>');
        }, 100);
    }

    openNewPaymentForm() {
        const mopOptions = this.state.modes_of_payment.map(m => `<option value="${m}">${m}</option>`).join('');
        const companyOptions = this.state.companies.map(c => `<option value="${c}">${c}</option>`).join('');
        const bankOptions = this.state.banks.map(b => `<option value="${b}">${b}</option>`).join('');
        const today = this.getToday();
        
        const dialog = new frappe.ui.Dialog({
            title: 'New Payment',
            size: 'large',
            css_class: 'bnk-dialog-modern',
            fields: [{ fieldtype: 'HTML', fieldname: 'form_html', options: `
                <div id="pmt-form-container">
                    <!-- Transaction Details Card -->
                    <div class="bnk-form-card">
                        <div class="bnk-form-card-header">
                            <i class="fa fa-info-circle"></i>
                            <h4>Transaction Details</h4>
                        </div>
                        <div class="bnk-form-card-body">
                            <div class="bnk-form-grid">
                                <div class="bnk-field-group">
                                    <label class="bnk-field-label">Date <span class="required">*</span></label>
                                    <input type="date" class="bnk-field-input" id="pmt-date" value="${today}">
                                </div>
                                <div class="bnk-field-group">
                                    <label class="bnk-field-label">Transaction Type</label>
                                    <select class="bnk-field-select" id="pmt-type">
                                        <option value="Supplier Payment">🏭 Supplier Payment</option>
                                        <option value="Expense Payment">🧾 Expense Payment</option>
                                        <option value="Transfer Out">↗️ Transfer Out</option>
                                        <option value="Supplier Refunds">↩️ Supplier Refunds</option>
                                        <option value="Payment Request">📋 Payment Request</option>
                                    </select>
                                </div>
                                <div class="bnk-field-group">
                                    <label class="bnk-field-label">Company <span class="required">*</span></label>
                                    <select class="bnk-field-select" id="pmt-company">${companyOptions}</select>
                                </div>
                                <div class="bnk-field-group">
                                    <label class="bnk-field-label">Supplier / Payee</label>
                                    <input type="text" class="bnk-field-input" id="pmt-payee" placeholder="Supplier name or payee">
                                </div>
                                <div class="bnk-field-group bnk-form-grid-full">
                                    <label class="bnk-field-label">Beneficiary Name (Free Text)</label>
                                    <input type="text" class="bnk-field-input" id="pmt-payee-name" placeholder="Override beneficiary display name">
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Amount & Payment Card -->
                    <div class="bnk-form-card">
                        <div class="bnk-form-card-header">
                            <i class="fa fa-money-bill-wave"></i>
                            <h4>Amount & Payment</h4>
                        </div>
                        <div class="bnk-form-card-body">
                            <div class="bnk-form-grid">
                                <div class="bnk-field-group">
                                    <label class="bnk-field-label">Amount Paid <span class="required">*</span></label>
                                    <input type="number" class="bnk-field-input" id="pmt-amount" placeholder="0.00" step="0.01" oninput="__bnk.updatePmtGL()">
                                </div>
                                <div class="bnk-field-group">
                                    <label class="bnk-field-label">Mode of Payment</label>
                                    <select class="bnk-field-select" id="pmt-mop"><option value="">— Select —</option>${mopOptions}</select>
                                </div>
                                <div class="bnk-field-group">
                                    <label class="bnk-field-label">Cheque / Ref No <span class="required">*</span></label>
                                    <input type="text" class="bnk-field-input" id="pmt-ref" placeholder="Bank reference / cheque no">
                                </div>
                                <div class="bnk-field-group">
                                    <label class="bnk-field-label">Bank Account <span class="required">*</span></label>
                                    <select class="bnk-field-select" id="pmt-bank">${bankOptions}</select>
                                </div>
                                <div class="bnk-field-group">
                                    <label class="bnk-field-label">Account to Debit</label>
                                    <input type="text" class="bnk-field-input" id="pmt-debit-acct" placeholder="Expense / payable GL account">
                                </div>
                                <div class="bnk-field-group">
                                    <label class="bnk-field-label">WHT Rate (%)</label>
                                    <input type="number" class="bnk-field-input" id="pmt-wht-rate" placeholder="0" min="0" max="100" step="0.01">
                                </div>
                                <div class="bnk-field-group bnk-form-grid-full">
                                    <label class="bnk-field-label">Transaction Purpose</label>
                                    <textarea class="bnk-field-textarea" id="pmt-purpose" placeholder="Describe the purpose of this payment…" rows="2"></textarea>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Invoice Allocation Card -->
                    <div class="bnk-form-card">
                        <div class="bnk-form-card-header">
                            <i class="fa fa-link"></i>
                            <h4>Invoice Allocation (Optional)</h4>
                        </div>
                        <div class="bnk-form-card-body">
                            <div style="margin-bottom:12px;font-size:11px;color:var(--tx3);">
                                Allocate this payment against outstanding purchase invoices.
                            </div>
                            <div class="bnk-match-tbl-wrap">
                                <table class="bnk-alloc-table">
                                    <thead><tr><th>Purchase Invoice</th><th style="text-align:right">Outstanding</th><th style="text-align:right">Allocate</th><th style="width:40px"></th></tr></thead>
                                    <tbody id="pmt-alloc-body"><tr id="pmt-alloc-empty"><td colspan="4" style="text-align:center;color:var(--tx3);padding:30px;">No invoices added. Click "Load Outstanding" to fetch.</td></tr></tbody>
                                </table>
                            </div>
                            <div style="display:flex;gap:10px;margin-top:12px;">
                                <button type="button" class="bnk-btn btn-ghost btn-sm" onclick="__bnk.loadOutstandingPurchase()"><i class="fa fa-download"></i> Load Outstanding</button>
                                <button type="button" class="bnk-btn btn-amb btn-sm" onclick="__bnk.addManualPmtRow()"><i class="fa fa-plus"></i> Add Row</button>
                            </div>
                            <div id="pmt-alloc-summary" class="bnk-alloc-summary" style="margin-top:12px;"></div>
                        </div>
                    </div>
                    
                    <!-- Options Card -->
                    <div class="bnk-form-card">
                        <div class="bnk-form-card-header">
                            <i class="fa fa-sliders-h"></i>
                            <h4>Options</h4>
                        </div>
                        <div class="bnk-form-card-body">
                            <div class="bnk-options-grid">
                                <div class="bnk-option-check"><input type="checkbox" id="pmt-create-gl" checked><label for="pmt-create-gl">Create Accounting Entries</label></div>
                                <div class="bnk-option-check"><input type="checkbox" id="pmt-deduct-wht"><label for="pmt-deduct-wht">Deduct WHT</label></div>
                                <div class="bnk-option-check"><input type="checkbox" id="pmt-is-multi"><label for="pmt-is-multi">Multi-Line Items</label></div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- GL Preview Card -->
                    <div class="bnk-form-card" id="pmt-gl-card" style="display:none;">
                        <div class="bnk-form-card-header">
                            <i class="fa fa-book"></i>
                            <h4>GL Entry Preview</h4>
                        </div>
                        <div class="bnk-form-card-body">
                            <table class="bnk-alloc-table">
                                <thead><tr><th>Account</th><th style="text-align:right">Debit</th><th style="text-align:right">Credit</th><th>Remark</th></tr></thead>
                                <tbody id="pmt-gl-body"></tbody>
                            </table>
                        </div>
                    </div>
                </div>
            ` }],
            primary_action_label: '<i class="fa fa-check"></i> Save & Submit',
            primary_action: () => this.savePayment(true),
            secondary_action_label: '<i class="fa fa-save"></i> Save Draft',
            secondary_action: () => this.savePayment(false)
        });
        
        dialog.show();
        this.currentDialog = dialog;
        
        setTimeout(() => {
            const $footer = dialog.$wrapper.find('.modal-footer');
            $footer.prepend('<button type="button" class="btn btn-sm btn-default" onclick="__bnk.previewPmtGL()" style="margin-right:10px"><i class="fa fa-eye"></i> Preview GL</button>');
        }, 100);
    }

    previewRcpGL() {
        const amt = parseFloat(document.getElementById('rcp-amount')?.value) || 0;
        const bank = document.getElementById('rcp-bank')?.value || 'Bank Account';
        const creditAcct = document.getElementById('rcp-credit-acct')?.value || 'Debtors Account';
        const whtEl = document.getElementById('rcp-deduct-wht');
        const whtAmt = whtEl?.checked ? amt * 0.05 : 0;
        const netAmt = amt - whtAmt;
        const glCard = document.getElementById('rcp-gl-card');
        const body = document.getElementById('rcp-gl-body');
        if (!glCard || !body) return;
        let rows = `<tr><td class="acct">${bank}</td><td style="text-align:right;color:var(--grn)">${this.fmtCurr(amt)}</td><td style="text-align:right">—</td><td>Bank receipt</td></tr>
                    <tr><td class="acct">${creditAcct}</td><td style="text-align:right">—</td><td style="text-align:right;color:var(--red)">${this.fmtCurr(netAmt)}</td><td>Customer receipt credit</td></tr>`;
        if (whtAmt > 0) rows += `<tr><td class="acct">WHT Payable</td><td style="text-align:right">—</td><td style="text-align:right;color:var(--red)">${this.fmtCurr(whtAmt)}</td><td>WHT @ 5%</td></tr>`;
        body.innerHTML = rows;
        glCard.style.display = 'block';
    }

    updateRcpGL() { const glCard = document.getElementById('rcp-gl-card'); if (glCard && glCard.style.display !== 'none') this.previewRcpGL(); }

    previewPmtGL() {
        const amt = parseFloat(document.getElementById('pmt-amount')?.value) || 0;
        const bank = document.getElementById('pmt-bank')?.value || 'Bank Account';
        const debitAcct = document.getElementById('pmt-debit-acct')?.value || 'Expense / Payable Account';
        const whtRate = parseFloat(document.getElementById('pmt-wht-rate')?.value) || 0;
        const whtAmt = amt * (whtRate / 100);
        const netAmt = amt - whtAmt;
        const glCard = document.getElementById('pmt-gl-card');
        const body = document.getElementById('pmt-gl-body');
        if (!glCard || !body) return;
        let rows = `<tr><td class="acct">${debitAcct}</td><td style="text-align:right;color:var(--grn)">${this.fmtCurr(amt)}</td><td style="text-align:right">—</td><td>Expense / Payable</td></tr>
                    <tr><td class="acct">${bank}</td><td style="text-align:right">—</td><td style="text-align:right;color:var(--red)">${this.fmtCurr(netAmt)}</td><td>Bank payment</td></tr>`;
        if (whtAmt > 0) rows += `<tr><td class="acct">WHT Payable</td><td style="text-align:right">—</td><td style="text-align:right;color:var(--red)">${this.fmtCurr(whtAmt)}</td><td>WHT @ ${whtRate}%</td></tr>`;
        body.innerHTML = rows;
        glCard.style.display = 'block';
    }

    updatePmtGL() { const glCard = document.getElementById('pmt-gl-card'); if (glCard && glCard.style.display !== 'none') this.previewPmtGL(); }

    async loadOutstandingSales() {
        const party = document.getElementById('rcp-payer')?.value.trim() || '';
        frappe.show_alert({ message: 'Fetching outstanding invoices…', indicator: 'blue' });
        try {
            const filters = [['docstatus', '=', 1], ['outstanding_amount', '>', 0]];
            if (party) filters.push(['customer_name', 'like', `%${party}%`]);
            const r = await frappe.call({ method: 'frappe.client.get_list', args: { doctype: 'Sales Invoice', fields: ['name', 'customer_name', 'outstanding_amount'], filters, limit: 50, order_by: 'due_date asc' } });
            const invoices = r.message || [];
            const body = document.getElementById('rcp-alloc-body');
            if (!body) return;
            if (!invoices.length) { body.innerHTML = `<tr id="rcp-alloc-empty"><td colspan="4" style="text-align:center;color:var(--tx3);padding:30px;">No outstanding sales invoices found</td></tr>`; return; }
            body.innerHTML = invoices.map(inv => `<tr id="rcp-row-${inv.name.replace(/[^a-zA-Z0-9]/g, '_')}"><td><div style="font-weight:600;color:var(--pri2)">${inv.name}</div><div style="font-size:10px;color:var(--tx3)">${inv.customer_name || '—'}</div></td><td style="text-align:right;font-family:monospace;color:var(--amb)">${this.fmtCurr(inv.outstanding_amount)}</td><td style="text-align:right"><input type="number" value="${inv.outstanding_amount}" max="${inv.outstanding_amount}" oninput="__bnk.recalcRcpAlloc()" id="rcp-alloc-${inv.name.replace(/[^a-zA-Z0-9]/g, '_')}" style="width:130px;background:var(--card);border:1px solid var(--brd2);border-radius:8px;padding:6px 10px;text-align:right;font-family:monospace;"></td><td><button type="button" class="del-row-btn" onclick="__bnk.removeAllocRow('rcp-row-${inv.name.replace(/[^a-zA-Z0-9]/g, '_')}','rcp')">✕</button></td></tr>`).join('');
            this.recalcRcpAlloc();
        } catch (e) { console.error(e); frappe.show_alert({ message: 'Error loading invoices: ' + e.message, indicator: 'red' }); }
    }

    async loadOutstandingPurchase() {
        const party = document.getElementById('pmt-payee')?.value.trim() || '';
        frappe.show_alert({ message: 'Fetching outstanding invoices…', indicator: 'blue' });
        try {
            const filters = [['docstatus', '=', 1], ['outstanding_amount', '>', 0]];
            if (party) filters.push(['supplier_name', 'like', `%${party}%`]);
            const r = await frappe.call({ method: 'frappe.client.get_list', args: { doctype: 'Purchase Invoice', fields: ['name', 'supplier_name', 'outstanding_amount'], filters, limit: 50, order_by: 'due_date asc' } });
            const invoices = r.message || [];
            const body = document.getElementById('pmt-alloc-body');
            if (!body) return;
            if (!invoices.length) { body.innerHTML = `<tr id="pmt-alloc-empty"><td colspan="4" style="text-align:center;color:var(--tx3);padding:30px;">No outstanding purchase invoices found</td></tr>`; return; }
            body.innerHTML = invoices.map(inv => `<tr id="pmt-row-${inv.name.replace(/[^a-zA-Z0-9]/g, '_')}"><td><div style="font-weight:600;color:var(--pri2)">${inv.name}</div><div style="font-size:10px;color:var(--tx3)">${inv.supplier_name || '—'}</div></td><td style="text-align:right;font-family:monospace;color:var(--amb)">${this.fmtCurr(inv.outstanding_amount)}</td><td style="text-align:right"><input type="number" value="${inv.outstanding_amount}" max="${inv.outstanding_amount}" oninput="__bnk.recalcPmtAlloc()" id="pmt-alloc-${inv.name.replace(/[^a-zA-Z0-9]/g, '_')}" style="width:130px;background:var(--card);border:1px solid var(--brd2);border-radius:8px;padding:6px 10px;text-align:right;font-family:monospace;"></td><td><button type="button" class="del-row-btn" onclick="__bnk.removeAllocRow('pmt-row-${inv.name.replace(/[^a-zA-Z0-9]/g, '_')}','pmt')">✕</button></td></tr>`).join('');
            this.recalcPmtAlloc();
        } catch (e) { console.error(e); frappe.show_alert({ message: 'Error loading invoices: ' + e.message, indicator: 'red' }); }
    }

    addManualRcpRow() {
        const body = document.getElementById('rcp-alloc-body');
        if (!body) return;
        const id = 'manual-' + Date.now();
        const empty = document.getElementById('rcp-alloc-empty');
        if (empty) empty.remove();
        body.insertAdjacentHTML('beforeend', `<tr id="rcp-row-${id}"><td><input type="text" placeholder="Invoice name…" id="rcp-inv-${id}" style="width:100%;background:var(--card);border:1px solid var(--brd2);border-radius:8px;padding:6px 10px;font-size:12px;"></td><td style="text-align:right">—</td><td style="text-align:right"><input type="number" placeholder="0.00" oninput="__bnk.recalcRcpAlloc()" id="rcp-alloc-${id}" style="width:130px;background:var(--card);border:1px solid var(--brd2);border-radius:8px;padding:6px 10px;text-align:right;font-family:monospace;"></td><td><button type="button" class="del-row-btn" onclick="__bnk.removeAllocRow('rcp-row-${id}','rcp')">✕</button></td></tr>`);
    }

    addManualPmtRow() {
        const body = document.getElementById('pmt-alloc-body');
        if (!body) return;
        const id = 'manual-' + Date.now();
        const empty = document.getElementById('pmt-alloc-empty');
        if (empty) empty.remove();
        body.insertAdjacentHTML('beforeend', `<tr id="pmt-row-${id}"><td><input type="text" placeholder="Invoice name…" id="pmt-inv-${id}" style="width:100%;background:var(--card);border:1px solid var(--brd2);border-radius:8px;padding:6px 10px;font-size:12px;"></td><td style="text-align:right">—</td><td style="text-align:right"><input type="number" placeholder="0.00" oninput="__bnk.recalcPmtAlloc()" id="pmt-alloc-${id}" style="width:130px;background:var(--card);border:1px solid var(--brd2);border-radius:8px;padding:6px 10px;text-align:right;font-family:monospace;"></td><td><button type="button" class="del-row-btn" onclick="__bnk.removeAllocRow('pmt-row-${id}','pmt')">✕</button></td></tr>`);
    }

    removeAllocRow(rowId, prefix) {
        const row = document.getElementById(rowId);
        if (row) row.remove();
        if (prefix === 'rcp') { const body = document.getElementById('rcp-alloc-body'); if (body && body.querySelectorAll('tr:not(#rcp-alloc-empty)').length === 0) body.innerHTML = `<tr id="rcp-alloc-empty"><td colspan="4" style="text-align:center;color:var(--tx3);padding:30px;">No invoices added. Click "Load Outstanding" to fetch.</td></tr>`; this.recalcRcpAlloc(); }
        else { const body = document.getElementById('pmt-alloc-body'); if (body && body.querySelectorAll('tr:not(#pmt-alloc-empty)').length === 0) body.innerHTML = `<tr id="pmt-alloc-empty"><td colspan="4" style="text-align:center;color:var(--tx3);padding:30px;">No invoices added. Click "Load Outstanding" to fetch.</td></tr>`; this.recalcPmtAlloc(); }
    }

    recalcRcpAlloc() {
        const inputs = document.querySelectorAll('[id^="rcp-alloc-"]');
        let total = 0;
        inputs.forEach(inp => { total += parseFloat(inp.value) || 0; });
        const amtPaid = parseFloat(document.getElementById('rcp-amount')?.value) || 0;
        const diff = amtPaid - total;
        const sumEl = document.getElementById('rcp-alloc-summary');
        if (sumEl) sumEl.innerHTML = this._allocSummary(total, amtPaid, diff, 'grn');
    }

    recalcPmtAlloc() {
        const inputs = document.querySelectorAll('[id^="pmt-alloc-"]');
        let total = 0;
        inputs.forEach(inp => { total += parseFloat(inp.value) || 0; });
        const amtPaid = parseFloat(document.getElementById('pmt-amount')?.value) || 0;
        const diff = amtPaid - total;
        const sumEl = document.getElementById('pmt-alloc-summary');
        if (sumEl) sumEl.innerHTML = this._allocSummary(total, amtPaid, diff, 'pri2');
    }

    _allocSummary(total, amtPaid, diff, col) {
        const diffColor = Math.abs(diff) < 0.01 ? 'var(--grn)' : diff > 0 ? 'var(--amb)' : 'var(--red)';
        const status = diff > 0.01 ? '(unallocated)' : diff < -0.01 ? '(over-allocated)' : '✓ balanced';
        return `<div><span style="color:var(--tx3)">Total Allocated:</span> <strong style="color:var(--${col})">${this.fmtCurr(total)}</strong></div>
                <div><span style="color:var(--tx3)">Amount:</span> <strong>${this.fmtCurr(amtPaid)}</strong></div>
                <div><span style="color:var(--tx3)">Difference:</span> <strong style="color:${diffColor}">${this.fmtCurr(Math.abs(diff))} ${status}</strong></div>`;
    }

    async saveReceipt(submit = false) {
        const date = document.getElementById('rcp-date')?.value;
        const amount = parseFloat(document.getElementById('rcp-amount')?.value);
        const ref = document.getElementById('rcp-ref')?.value;
        const company = document.getElementById('rcp-company')?.value;
        const bank = document.getElementById('rcp-bank')?.value;
        if (!date || !amount || !ref || !company || !bank) {
            frappe.msgprint({ title: 'Validation Error', indicator: 'red', message: 'Please fill in Date, Amount, Reference No, Company, and Bank Account.' });
            return;
        }
        const refs = [];
        document.querySelectorAll('[id^="rcp-alloc-"]').forEach(inp => {
            const fullId = inp.id.replace('rcp-alloc-', '');
            const allocAmt = parseFloat(inp.value) || 0;
            if (allocAmt > 0) {
                let invName;
                if (fullId.startsWith('manual-')) invName = document.getElementById('rcp-inv-' + fullId)?.value || '';
                else invName = fullId.replace(/_/g, '/');
                if (invName) refs.push({ reference_doctype: 'Sales Invoice', reference_name: invName, allocated_amount: allocAmt });
            }
        });
        const doc = {
            doctype: 'Receipts', transaction_date: date, trans_type: document.getElementById('rcp-type')?.value,
            company: company, payer_name: document.getElementById('rcp-payer-name')?.value || document.getElementById('rcp-payer')?.value,
            amount_received: amount, mode_of_payment: document.getElementById('rcp-mop')?.value, reference_no: ref,
            remittance_bank: bank, account_to_credit: document.getElementById('rcp-credit-acct')?.value,
            transaction_purposes: document.getElementById('rcp-purpose')?.value,
            create_accounting_entries: document.getElementById('rcp-create-gl')?.checked ? 1 : 0,
            deduct_wht: document.getElementById('rcp-deduct-wht')?.checked ? 1 : 0,
            is_multi_line: document.getElementById('rcp-is-multi')?.checked ? 1 : 0,
            receipts_reference: refs
        };
        try {
            frappe.show_alert({ message: 'Saving receipt…', indicator: 'blue' });
            const r = await frappe.call({ method: 'frappe.client.insert', args: { doc } });
            const saved = r.message;
            if (submit && saved) { await frappe.call({ method: 'frappe.client.submit', args: { doc: saved } }); frappe.show_alert({ message: `Receipt ${saved.name} saved & submitted`, indicator: 'green' }); }
            else if (saved) frappe.show_alert({ message: `Receipt ${saved.name} saved as draft`, indicator: 'green' });
            if (this.currentDialog) this.currentDialog.hide();
            await this.fetchData();
            this.runAIAnalysis();
        } catch (e) { frappe.msgprint({ title: 'Save Error', indicator: 'red', message: e.message || String(e) }); }
    }

    async savePayment(submit = false) {
        const date = document.getElementById('pmt-date')?.value;
        const amount = parseFloat(document.getElementById('pmt-amount')?.value);
        const ref = document.getElementById('pmt-ref')?.value;
        const company = document.getElementById('pmt-company')?.value;
        const bank = document.getElementById('pmt-bank')?.value;
        if (!date || !amount || !ref || !company || !bank) {
            frappe.msgprint({ title: 'Validation Error', indicator: 'red', message: 'Please fill in Date, Amount, Reference No, Company, and Bank Account.' });
            return;
        }
        const refs = [];
        document.querySelectorAll('[id^="pmt-alloc-"]').forEach(inp => {
            const fullId = inp.id.replace('pmt-alloc-', '');
            const allocAmt = parseFloat(inp.value) || 0;
            if (allocAmt > 0) {
                let invName;
                if (fullId.startsWith('manual-')) invName = document.getElementById('pmt-inv-' + fullId)?.value || '';
                else invName = fullId.replace(/_/g, '/');
                if (invName) refs.push({ reference_doctype: 'Purchase Invoice', reference_name: invName, allocated_amount: allocAmt });
            }
        });
        const whtRate = parseFloat(document.getElementById('pmt-wht-rate')?.value) || 0;
        const whtAmt = amount * (whtRate / 100);
        const doc = {
            doctype: 'Payments', transaction_date: date, trans_type: document.getElementById('pmt-type')?.value,
            company: company, payee_name: document.getElementById('pmt-payee-name')?.value || document.getElementById('pmt-payee')?.value,
            amount_paid: amount, mode_of_payment: document.getElementById('pmt-mop')?.value, reference_no: ref,
            remittance_bank: bank, account_to_debit: document.getElementById('pmt-debit-acct')?.value,
            transaction_purposes: document.getElementById('pmt-purpose')?.value,
            create_accounting_entries: document.getElementById('pmt-create-gl')?.checked ? 1 : 0,
            deduct_wht: document.getElementById('pmt-deduct-wht')?.checked ? 1 : 0,
            is_multi_line: document.getElementById('pmt-is-multi')?.checked ? 1 : 0,
            whtax_rate: whtRate, wht_amount: whtAmt, net_amount: amount - whtAmt,
            payments_reference: refs
        };
        try {
            frappe.show_alert({ message: 'Saving payment…', indicator: 'blue' });
            const r = await frappe.call({ method: 'frappe.client.insert', args: { doc } });
            const saved = r.message;
            if (submit && saved) { await frappe.call({ method: 'frappe.client.submit', args: { doc: saved } }); frappe.show_alert({ message: `Payment ${saved.name} saved & submitted`, indicator: 'green' }); }
            else if (saved) frappe.show_alert({ message: `Payment ${saved.name} saved as draft`, indicator: 'green' });
            if (this.currentDialog) this.currentDialog.hide();
            await this.fetchData();
            this.runAIAnalysis();
        } catch (e) { frappe.msgprint({ title: 'Save Error', indicator: 'red', message: e.message || String(e) }); }
    }

    openMatchDialog() {
        const dialog = new frappe.ui.Dialog({
            title: 'Invoice Matching',
            size: 'large',
            css_class: 'bnk-dialog-modern',
            fields: [{ fieldtype: 'HTML', fieldname: 'match_html', options: `
                <div style="margin-bottom:16px;padding:12px 16px;background:var(--bg2);border-radius:12px;font-size:13px;color:var(--tx2);">
                    <i class="fa fa-info-circle" style="color:var(--pri2);margin-right:8px;"></i>
                    Match unallocated receipts and payments against outstanding invoices.
                    <strong style="color:var(--pri2)">AI-powered batch reconciliation</strong> available via the Payment Invoice Match DocType.
                </div>
                <div class="bnk-form-card">
                    <div class="bnk-form-card-header"><i class="fa fa-search"></i><h4>Quick Match</h4></div>
                    <div class="bnk-form-card-body">
                        <div class="bnk-form-grid">
                            <div class="bnk-field-group"><label class="bnk-field-label">Party Type</label><select class="bnk-field-select" id="match-party-type" onchange="__bnk.loadMatchPayments()"><option value="Customer">Customer</option><option value="Supplier">Supplier</option></select></div>
                            <div class="bnk-field-group"><label class="bnk-field-label">Company</label><select class="bnk-field-select" id="match-company">${this.state.companies.map(c => `<option>${c}</option>`).join('')}</select></div>
                            <div class="bnk-field-group"><label class="bnk-field-label">Date From</label><input type="date" class="bnk-field-input" id="match-from-date"></div>
                        </div>
                        <div style="margin-top:16px;"><button type="button" class="bnk-btn btn-amb" onclick="__bnk.loadMatchPayments()"><i class="fa fa-search"></i> Fetch Unmatched</button></div>
                    </div>
                </div>
                <div id="match-results" style="margin-top:16px;"><div style="padding:40px;text-align:center;color:var(--tx3);">Click "Fetch Unmatched" to load transactions</div></div>
            ` }],
            primary_action_label: 'Close',
            primary_action: () => dialog.hide()
        });
        dialog.show();
        this.currentDialog = dialog;
        setTimeout(() => {
            const $footer = dialog.$wrapper.find('.modal-footer');
            $footer.prepend('<button type="button" class="btn btn-sm btn-vio" onclick="frappe.set_route(\'List\',\'Payment Invoice Match\');__bnk.closeMatchDialog()" style="margin-right:10px"><i class="fa fa-magic"></i> Open AI Match DocType</button>');
        }, 100);
    }
    
    closeMatchDialog() { if (this.currentDialog) this.currentDialog.hide(); }

    openMatchForDoc(doctype, name, party) { this.openMatchDialog(); }

    async loadMatchPayments() {
        const partyType = document.getElementById('match-party-type')?.value;
        const isReceipt = partyType === 'Customer';
        const resultsEl = document.getElementById('match-results');
        if (!resultsEl) return;
        resultsEl.innerHTML = `<div class="bnk-spinner"><div class="bnk-spinner-icon"></div>Loading…</div>`;
        try {
            const [txnR, invR] = await Promise.all([
                frappe.call({ method: 'frappe.client.get_list', args: { doctype: isReceipt ? 'Receipts' : 'Payments', fields: ['name', 'transaction_date', isReceipt ? 'customer_name' : 'payee_name', isReceipt ? 'amount_received' : 'amount_paid'], filters: [['docstatus', '=', 1]], limit: 50, order_by: 'transaction_date desc' } }),
                frappe.call({ method: 'frappe.client.get_list', args: { doctype: isReceipt ? 'Sales Invoice' : 'Purchase Invoice', fields: ['name', isReceipt ? 'customer_name' : 'supplier_name', 'outstanding_amount', 'due_date'], filters: [['docstatus', '=', 1], ['outstanding_amount', '>', 0]], limit: 100, order_by: 'due_date asc' } })
            ]);
            const txns = txnR.message || [];
            const invs = invR.message || [];
            const amtField = isReceipt ? 'amount_received' : 'amount_paid';
            const partyField = isReceipt ? 'customer_name' : 'payee_name';
            const invParty = isReceipt ? 'customer_name' : 'supplier_name';
            if (!txns.length && !invs.length) { resultsEl.innerHTML = `<div style="padding:40px;text-align:center;color:var(--tx3);">No unmatched transactions found</div>`; return; }
            resultsEl.innerHTML = `<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px"><div class="bnk-match-tbl-wrap"><div style="padding:12px 16px;font-size:11px;font-weight:700;text-transform:uppercase;background:var(--bg3);border-bottom:1px solid var(--brd)">${isReceipt ? '📥 Receipts' : '📤 Payments'} (${txns.length})</div><table class="bnk-alloc-table"><thead><tr><th>Reference</th><th>Party</th><th style="text-align:right">Amount</th></tr></thead><tbody>${txns.map(t => `<td><td style="color:var(--pri2);font-weight:600">${t.name}</td><td style="font-size:12px">${t[partyField] || '—'}</td><td style="text-align:right;font-family:monospace;color:${isReceipt ? 'var(--grn)' : 'var(--red)'}">${this.fmtCurr(t[amtField])}</td></tr>`).join('')}</tbody></table></div><div class="bnk-match-tbl-wrap"><div style="padding:12px 16px;font-size:11px;font-weight:700;text-transform:uppercase;background:var(--bg3);border-bottom:1px solid var(--brd)">📄 Outstanding ${isReceipt ? 'Sales' : 'Purchase'} Invoices (${invs.length})</div><table class="bnk-alloc-table"><thead><tr><th>Invoice</th><th>Party</th><th style="text-align:right">Outstanding</th></tr></thead><tbody>${invs.map(i => `<td><td style="color:var(--pri2);font-weight:600">${i.name}</td><td style="font-size:12px">${i[invParty] || '—'}</td><td style="text-align:right;font-family:monospace;color:var(--amb)">${this.fmtCurr(i.outstanding_amount)}</td></tr>`).join('')}</tbody></table></div></div><div style="margin-top:16px;padding:12px 16px;background:var(--bg2);border-radius:12px;font-size:12px;color:var(--tx3)"><i class="fa fa-info-circle" style="color:var(--pri2);margin-right:8px;"></i>For AI-driven matching with confidence scoring, use the <strong style="color:var(--pri2)">Payment Invoice Match</strong> DocType.</div>`;
        } catch (e) { resultsEl.innerHTML = `<div style="padding:20px;color:var(--red);font-size:12px">Error: ${e.message}</div>`; }
    }
}