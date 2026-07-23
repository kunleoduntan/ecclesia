// ecclesia/page/talent-hub/talent-hub.js
// TalentPlex — Performance & Recruitment Command Centre
// Presentation-grade: live KPIs, animated counters, glassmorphism cards
// Multi-Theme System: 9 professional themes with localStorage persistence

frappe.pages['talent-hub'] = frappe.pages['talent-hub'] || {};

// ── THEME REGISTRY ──────────────────────────────────────────────────────────────
// 9 Professional Themes — pure localStorage, zero DB dependency
const TP_THEMES = {
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

frappe.pages['talent-hub'].on_page_load = function (wrapper) {

    const page = frappe.ui.make_app_page({
        parent:        wrapper,
        title:         '🎯 TalentPlex',
        single_column: true
    });

    // ── THEME STATE ──────────────────────────────────────────────────────────
    let currentTheme = 'midnight';
    // Restore theme from localStorage
    try {
        const saved = localStorage.getItem('tp-theme');
        if (saved && TP_THEMES[saved]) currentTheme = saved;
    } catch(e) { /* localStorage unavailable */ }

    // ── SHORTCUT GROUPS ──────────────────────────────────────────────────────
    const GROUPS = [
        {
            id: 'perf-setup', label: 'Performance Setup',
            icon: '⚙️', accent: '#7C3AED',
            items: [
                { name:'Performance Rating Scale',  icon:'⭐', color:'#7C3AED' },
                { name:'Performance Competency',    icon:'🧠', color:'#8B5CF6' },
                { name:'Performance Weight Config', icon:'⚖️', color:'#6D28D9' },
                { name:'Job Requirement Profile',   icon:'📋', color:'#5B21B6' },
            ]
        },
        {
            id: 'perf-cycle', label: 'Performance Cycles',
            icon: '🔄', accent: '#2563EB',
            items: [
                { name:'Performance Cycle',            icon:'🗓️', color:'#2563EB' },
                { name:'Performance Goal',             icon:'🎯', color:'#3B82F6' },
                { name:'Employee Performance Record',  icon:'🏆', color:'#1D4ED8' },
                { name:'Continuous Feedback',          icon:'💬', color:'#0EA5E9' },
            ]
        },
        {
            id: 'perf-reviews', label: 'Reviews & Appraisals',
            icon: '📝', accent: '#0D9488',
            items: [
                { name:'Self Appraisal',          icon:'🪞', color:'#0D9488' },
                { name:'Peer Review Request',     icon:'🤝', color:'#0F766E' },
                { name:'Peer Review',             icon:'👥', color:'#14B8A6' },
                { name:'Manager Review 360',      icon:'👔', color:'#059669' },
                { name:'Skip Level Review',       icon:'🔼', color:'#047857' },
                { name:'HR Calibration Session',  icon:'⚖️', color:'#065F46' },
                { name:'Performance Appeal',      icon:'📢', color:'#DC2626' },
            ]
        },
        {
            id: 'perf-develop', label: 'Development & PIPs',
            icon: '📈', accent: '#D97706',
            items: [
                { name:'Performance IDP',   icon:'🗺️', color:'#D97706' },
                { name:'Performance PIP',   icon:'⚠️', color:'#B45309' },
                { name:'Training Program',  icon:'📚', color:'#0EA5E9' },
                { name:'Training Event',    icon:'🎓', color:'#0284C7' },
                { name:'Training Result',   icon:'✅', color:'#16A34A' },
            ]
        },
        {
            id: 'recruit-pipeline', label: 'Recruitment Pipeline',
            icon: '🌸', accent: '#DB2777',
            items: [
                { name:'Job Opening',           icon:'📣', color:'#DB2777' },
                { name:'Staffing Plan',         icon:'🗺️', color:'#EC4899' },
                { name:'Job Applicant',         icon:'🙋', color:'#BE185D' },
                { name:'Interview Round',       icon:'🎙️', color:'#9D174D' },
                { name:'Interview',             icon:'🗣️', color:'#831843' },
                { name:'Job Offer',             icon:'🎉', color:'#FBBF24' },
                { name:'Employee Onboarding',   icon:'🌱', color:'#16A34A' },
            ]
        },
        {
            id: 'recruit-screen', label: 'AI Screening',
            icon: '🤖', accent: '#059669',
            items: [
                { name:'Resume',                      icon:'📄', color:'#059669' },
                { name:'Resume Screening Result',     icon:'🎯', color:'#047857' },
                { name:'Candidate Comparison Matrix', icon:'📊', color:'#065F46' },
            ]
        },
        {
            id: 'job-publish', label: 'Job Publishing',
            icon: '📣', accent: '#7C3AED',
            items: [
                { name:'Job Post',           icon:'🚀', color:'#7C3AED' },
                { name:'Job Board Platform', icon:'🌐', color:'#6D28D9' },
            ]
        },
        {
            id: 'reports', label: 'Reports & Analytics',
            icon: '📑', accent: '#F59E0B',
            items: [
                { name:'Cycle Completion Status',         icon:'📊', color:'#F59E0B', route:'/app/query-report/Cycle Completion Status' },
                { name:'Performance Rating Distribution', icon:'🔔', color:'#D97706', route:'/app/query-report/Performance Rating Distribution' },
                { name:'PIP Tracker',                     icon:'⚠️', color:'#DC2626', route:'/app/query-report/PIP Tracker' },
                { name:'Recruitment Funnel',              icon:'🔽', color:'#0EA5E9', route:'/app/query-report/Recruitment Funnel' },
                { name:'Diversity Report',                icon:'🌈', color:'#8B5CF6', route:'/app/query-report/Diversity Report' },
            ]
        },
        {
            id: 'portals', label: 'Portals',
            icon: '🌐', accent: '#0EA5E9',
            items: [
                { name:'Performance Hub',   icon:'📈', color:'#7C3AED', route:'/performance-hub' },
                { name:'Careers Portal',    icon:'💼', color:'#059669', route:'/apply' },
                { name:'ESS Portal',        icon:'💌', color:'#DB2777', route:'/ess-portal' },
            ]
        },
    ];

    const totalItems = GROUPS.reduce((a, g) => a + g.items.length, 0);

    // ── KPI CONFIG ───────────────────────────────────────────────────────────
    const KPIS = [
        { id:'kpi-employees', label:'Employees',        icon:'👥', color:'#7C3AED',
          method:'frappe.client.get_count', args:{ doctype:'Employee', filters:{status:'Active'} } },
        { id:'kpi-cycles',    label:'Active Cycles',    icon:'🔄', color:'#2563EB',
          method:'frappe.client.get_count', args:{ doctype:'Performance Cycle', filters:{status:'Active'} } },
        { id:'kpi-jobs',      label:'Open Roles',       icon:'📣', color:'#DB2777',
          method:'frappe.client.get_count', args:{ doctype:'Job Opening', filters:{status:'Open'} } },
        { id:'kpi-applicants',label:'New Applicants',   icon:'🙋', color:'#059669',
          method:'frappe.client.get_count', args:{ doctype:'Job Applicant', filters:{status:'Open'} } },
        { id:'kpi-pips',      label:'Active PIPs',      icon:'⚠️', color:'#D97706',
          method:'frappe.client.get_count', args:{ doctype:'Performance PIP', filters:{status:'Active'} } },
        { id:'kpi-goals',     label:'Goals In Progress',icon:'🎯', color:'#0D9488',
          method:'frappe.client.get_count', args:{ doctype:'Performance Goal', filters:{status:'In Progress'} } },
    ];

    // ── RENDER ──────────────────────────────────────────────────────────────
    const html = `
<div id="tp-root" data-theme="${currentTheme}">

    <!-- ── HEADER ── -->
    <div class="tp-header">
        <div class="tp-header-bg"></div>
        <div class="tp-header-content">
            <div class="tp-logo-row">
                <div class="tp-logo">🎯</div>
                <div>
                    <div class="tp-title">TalentPlex</div>
                    <div class="tp-subtitle">Performance &amp; Recruitment Command Centre</div>
                </div>
                <div class="tp-header-actions">
                    <div class="tp-search-wrap">
                        <span class="tp-search-ico">⌕</span>
                        <input id="tp-search" type="text" placeholder="Search shortcuts… (Ctrl+K)"/>
                    </div>
                    <button class="tp-action-btn" onclick="tpShowFavs()" id="tp-fav-toggle-btn">
                        ♡ Favourites
                    </button>
                    <div class="tp-theme-selector">
                        <button class="tp-theme-btn" onclick="tpCycleTheme()" id="tp-theme-btn" title="Switch Theme">
                            ${TP_THEMES[currentTheme].icon} <span id="tp-theme-name">${TP_THEMES[currentTheme].name}</span>
                        </button>
                    </div>
                </div>
            </div>

            <!-- KPI strip -->
            <div class="tp-kpi-strip">
                ${KPIS.map(k => `
                <div class="tp-kpi" style="--kc:${k.color}">
                    <div class="tp-kpi-icon">${k.icon}</div>
                    <div class="tp-kpi-body">
                        <div class="tp-kpi-num" id="${k.id}">
                            <span class="tp-spinner"></span>
                        </div>
                        <div class="tp-kpi-label">${k.label}</div>
                    </div>
                </div>`).join('')}
                <div class="tp-kpi" style="--kc:#64748B">
                    <div class="tp-kpi-icon">📋</div>
                    <div class="tp-kpi-body">
                        <div class="tp-kpi-num">${totalItems}</div>
                        <div class="tp-kpi-label">Shortcuts</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- ── QUICK ACTIONS ── -->
    <div class="tp-quick-row">
        <div class="tp-section-label">⚡ Quick Actions</div>
        <div class="tp-quick-btns">
            <button class="tp-qbtn tp-qbtn-purple"
                onclick="frappe.new_doc('Performance Cycle')">
                + New Cycle
            </button>
            <button class="tp-qbtn tp-qbtn-blue"
                onclick="frappe.new_doc('Performance Goal')">
                + New Goal
            </button>
            <button class="tp-qbtn tp-qbtn-pink"
                onclick="frappe.new_doc('Job Opening')">
                + Post a Job
            </button>
            <button class="tp-qbtn tp-qbtn-teal"
                onclick="frappe.new_doc('Job Post')">
                + Publish Job
            </button>
            <button class="tp-qbtn tp-qbtn-amber"
                onclick="frappe.new_doc('Performance PIP')">
                + New PIP
            </button>
            <button class="tp-qbtn tp-qbtn-green"
                onclick="window.open('/apply','_blank')">
                🌐 Apply Portal
            </button>
        </div>
    </div>

    <!-- ── SHORTCUT GRID ── -->
    <div class="tp-section-label" style="margin-top:8px">
        📂 All Shortcuts
        &nbsp;·&nbsp;
        <span style="font-weight:400;color:var(--mu)">${GROUPS.length} groups · ${totalItems} items</span>
        &nbsp;·&nbsp;
        <span style="font-weight:700;color:var(--purple)">⭐ <span id="tp-fav-count">0</span> favourites</span>
    </div>

    <div class="tp-grid" id="tp-grid">
        ${GROUPS.map((g, gi) => `
        <div class="tp-group anim-in" data-group="${g.id}"
             style="--gc:${g.accent};animation-delay:${gi * 40}ms">
            <div class="tp-group-hdr">
                <span class="tp-group-icon">${g.icon}</span>
                <span class="tp-group-name">${g.label}</span>
                <span class="tp-group-cnt">${g.items.length}</span>
            </div>
            <div class="tp-group-body">
                ${g.items.map(item => `
                <div class="tp-item"
                     data-name="${item.name}"
                     data-route="${item.route || ''}"
                     style="--ic:${item.color}">
                    <button class="tp-fav" data-name="${item.name}" title="Add to favourites">♡</button>
                    <div class="tp-ico">${item.icon}</div>
                    <span class="tp-name">${item.name}</span>
                    <span class="tp-arr">→</span>
                </div>`).join('')}
            </div>
        </div>`).join('')}
    </div>

    <div class="tp-empty" id="tp-empty" style="display:none">
        <div style="font-size:44px;margin-bottom:10px">🔍</div>
        <div class="tp-empty-title">No shortcuts match that</div>
        <div class="tp-empty-sub">Try a different keyword</div>
    </div>

    <div class="tp-footer">
        TalentPlex · Ecclesia HR Platform · Value Impacts Consulting
        &nbsp;·&nbsp; refreshed <span id="tp-refreshed"></span>
        &nbsp;·&nbsp; <span id="tp-theme-indicator">${TP_THEMES[currentTheme].name}</span>
    </div>
</div>

<style>
/* ═══════════════════════════════════════════════════════════════════════════
   TALENTPLEX — Professional Multi-Theme System
   Adapted from SMM Studio's theme architecture
═══════════════════════════════════════════════════════════════════════════ */

/* ── BASE THEME VARIABLES ── */
#tp-root {
    --purple:#7C3AED; --blue:#2563EB; --teal:#0D9488;
    --pink:#DB2777;   --amber:#D97706;--green:#059669;
    --navy:#0F172A;   --card:#1E293B; --glass:rgba(30,41,59,.75);
    --bdr:rgba(255,255,255,.10);
    --txt:#F1F5F9;    --mu:#94A3B8;
    --bg:linear-gradient(135deg,#0F172A 0%,#1E1B4B 40%,#0F172A 100%);
    font-family:'Inter','Segoe UI',system-ui,sans-serif;
    background:var(--bg);
    color:var(--txt);
    padding:0 0 48px;
    min-height:100vh;
    transition:all .4s cubic-bezier(.4,0,.2,1);
}

/* ── THEME PRESETS ── */
#tp-root[data-theme="midnight"] {
    --bg: linear-gradient(135deg,#0F172A 0%,#1E1B4B 40%,#0F172A 100%);
    --card: #1E293B;
    --glass: rgba(30,41,59,.75);
    --txt: #F1F5F9;
    --mu: #94A3B8;
    --bdr: rgba(255,255,255,.10);
    --brd2: rgba(255,255,255,.14);
    --pri: #818CF8;
    --pri_x: rgba(129,140,248,.12);
    --pri2: #A5B4FC;
    --acc: #A5B4FC;
    --grn: #34D399;
    --red: #F87171;
    --amb: #FCD34D;
    --sky: #38BDF8;
    --pink: #F9A8D4;
}

#tp-root[data-theme="nova"] {
    --bg: linear-gradient(135deg,#FAF5FF 0%,#F5F3FF 40%,#EDE9FE 100%);
    --card: #FFFFFF;
    --glass: rgba(255,255,255,.85);
    --txt: #2E1065;
    --mu: #5B21B6;
    --bdr: #E9D5FF;
    --brd2: #D8B4FE;
    --pri: #7C3AED;
    --pri_x: rgba(124,58,237,.09);
    --pri2: #A78BFA;
    --acc: #A78BFA;
    --grn: #10B981;
    --red: #EF4444;
    --amb: #F59E0B;
    --sky: #06B6D4;
    --pink: #EC4899;
}

#tp-root[data-theme="ocean"] {
    --bg: linear-gradient(135deg,#F0F9FF 0%,#E0F2FE 40%,#BAE6FD 100%);
    --card: #FFFFFF;
    --glass: rgba(255,255,255,.85);
    --txt: #0C4A6E;
    --mu: #075985;
    --bdr: #BAE6FD;
    --brd2: #7DD3FC;
    --pri: #0EA5E9;
    --pri_x: rgba(14,165,233,.09);
    --pri2: #38BDF8;
    --acc: #38BDF8;
    --grn: #10B981;
    --red: #F43F5E;
    --amb: #F59E0B;
    --sky: #06B6D4;
    --pink: #EC4899;
}

#tp-root[data-theme="ember"] {
    --bg: linear-gradient(135deg,#FFF7ED 0%,#FFEDD5 40%,#FED7AA 100%);
    --card: #FFFFFF;
    --glass: rgba(255,255,255,.85);
    --txt: #431407;
    --mu: #9A3412;
    --bdr: #FED7AA;
    --brd2: #FDBA74;
    --pri: #F97316;
    --pri_x: rgba(249,115,22,.09);
    --pri2: #FB923C;
    --acc: #FB923C;
    --grn: #22C55E;
    --red: #EF4444;
    --amb: #EAB308;
    --sky: #0EA5E9;
    --pink: #EC4899;
}

#tp-root[data-theme="verdant"] {
    --bg: linear-gradient(135deg,#ECFDF5 0%,#D1FAE5 40%,#A7F3D0 100%);
    --card: #FFFFFF;
    --glass: rgba(255,255,255,.85);
    --txt: #022C22;
    --mu: #065F46;
    --bdr: #A7F3D0;
    --brd2: #6EE7B7;
    --pri: #059669;
    --pri_x: rgba(5,150,105,.09);
    --pri2: #34D399;
    --acc: #34D399;
    --grn: #10B981;
    --red: #EF4444;
    --amb: #F59E0B;
    --sky: #0EA5E9;
    --pink: #EC4899;
}

#tp-root[data-theme="sunset"] {
    --bg: linear-gradient(135deg,#FFF1F2 0%,#FFE4E6 40%,#FECDD3 100%);
    --card: #FFFFFF;
    --glass: rgba(255,255,255,.85);
    --txt: #4C0519;
    --mu: #881337;
    --bdr: #FECDD3;
    --brd2: #FDA4AF;
    --pri: #DC2626;
    --pri_x: rgba(220,38,38,.09);
    --pri2: #F87171;
    --acc: #F87171;
    --grn: #10B981;
    --red: #EF4444;
    --amb: #F59E0B;
    --sky: #06B6D4;
    --pink: #EC4899;
}

#tp-root[data-theme="arctic"] {
    --bg: linear-gradient(135deg,#F8FAFC 0%,#F1F5F9 40%,#E2E8F0 100%);
    --card: #FFFFFF;
    --glass: rgba(255,255,255,.85);
    --txt: #0F172A;
    --mu: #334155;
    --bdr: #E2E8F0;
    --brd2: #CBD5E1;
    --pri: #0284C7;
    --pri_x: rgba(2,132,199,.09);
    --pri2: #7DD3FC;
    --acc: #7DD3FC;
    --grn: #10B981;
    --red: #EF4444;
    --amb: #F59E0B;
    --sky: #06B6D4;
    --pink: #EC4899;
}

#tp-root[data-theme="forest"] {
    --bg: linear-gradient(135deg,#052E16 0%,#14532D 40%,#166534 100%);
    --card: #14532D;
    --glass: rgba(20,83,45,.85);
    --txt: #F0FDF4;
    --mu: #86EFAC;
    --bdr: rgba(187,247,208,.1);
    --brd2: rgba(134,239,172,.18);
    --pri: #22C55E;
    --pri_x: rgba(34,197,94,.12);
    --pri2: #4ADE80;
    --acc: #4ADE80;
    --grn: #22C55E;
    --red: #F87171;
    --amb: #FBBF24;
    --sky: #38BDF8;
    --pink: #F472B6;
}

#tp-root[data-theme="candy"] {
    --bg: linear-gradient(135deg,#FDF2F8 0%,#FCE7F3 40%,#FBCFE8 100%);
    --card: #FFFFFF;
    --glass: rgba(255,255,255,.85);
    --txt: #500724;
    --mu: #831843;
    --bdr: #FBCFE8;
    --brd2: #F9A8D4;
    --pri: #DB2777;
    --pri_x: rgba(219,39,119,.09);
    --pri2: #F472B6;
    --acc: #F472B6;
    --grn: #10B981;
    --red: #EF4444;
    --amb: #F59E0B;
    --sky: #06B6D4;
    --pink: #EC4899;
}

* { box-sizing:border-box; }

/* ── HEADER ── */
.tp-header {
    position:relative;overflow:hidden;
    padding:28px 28px 0;
    margin-bottom:20px;
    transition:all .4s;
}
.tp-header-bg {
    position:absolute;inset:0;
    background:linear-gradient(135deg,#312E81 0%,#1E2D5A 40%,#0F766E 100%);
    opacity:.9;z-index:0;
    transition:all .4s;
}
#tp-root[data-theme="nova"] .tp-header-bg {
    background:linear-gradient(135deg,#1E1B4B 0%,#4C1D95 40%,#7C3AED 70%,#EC4899 100%);
    opacity:.9;
}
#tp-root[data-theme="ocean"] .tp-header-bg {
    background:linear-gradient(135deg,#0C4A6E 0%,#0369A1 40%,#0EA5E9 70%,#06B6D4 100%);
    opacity:.9;
}
#tp-root[data-theme="ember"] .tp-header-bg {
    background:linear-gradient(135deg,#431407 0%,#C2410C 40%,#F97316 70%,#EAB308 100%);
    opacity:.9;
}
#tp-root[data-theme="verdant"] .tp-header-bg {
    background:linear-gradient(135deg,#022C22 0%,#047857 40%,#059669 70%,#10B981 100%);
    opacity:.9;
}
#tp-root[data-theme="sunset"] .tp-header-bg {
    background:linear-gradient(135deg,#4C0519 0%,#881337 40%,#DC2626 70%,#F59E0B 100%);
    opacity:.9;
}
#tp-root[data-theme="arctic"] .tp-header-bg {
    background:linear-gradient(135deg,#0F172A 0%,#1E3A5F 40%,#0284C7 70%,#06B6D4 100%);
    opacity:.85;
}
#tp-root[data-theme="forest"] .tp-header-bg {
    background:linear-gradient(135deg,#052E16 0%,#14532D 40%,#166534 70%,#22C55E 100%);
    opacity:.95;
}
#tp-root[data-theme="candy"] .tp-header-bg {
    background:linear-gradient(135deg,#500724 0%,#831843 40%,#DB2777 70%,#EC4899 100%);
    opacity:.9;
}
.tp-header-bg::after {
    content:'';position:absolute;inset:0;
    background:radial-gradient(ellipse at 80% 0%,rgba(139,92,246,.4) 0%,transparent 60%),
               radial-gradient(ellipse at 20% 100%,rgba(13,148,136,.4) 0%,transparent 60%);
}
.tp-header-content { position:relative;z-index:1; }

.tp-logo-row {
    display:flex;align-items:center;gap:16px;
    margin-bottom:24px;flex-wrap:wrap;
}
.tp-logo {
    width:52px;height:52px;background:rgba(255,255,255,.12);
    border-radius:16px;display:flex;align-items:center;
    justify-content:center;font-size:26px;flex-shrink:0;
    border:1px solid rgba(255,255,255,.2);
    box-shadow:0 8px 24px rgba(0,0,0,.3);
    transition:all .4s;
}
#tp-root[data-theme="nova"] .tp-logo,
#tp-root[data-theme="ocean"] .tp-logo,
#tp-root[data-theme="ember"] .tp-logo,
#tp-root[data-theme="verdant"] .tp-logo,
#tp-root[data-theme="sunset"] .tp-logo,
#tp-root[data-theme="arctic"] .tp-logo,
#tp-root[data-theme="candy"] .tp-logo {
    background:rgba(255,255,255,.9);
    border-color:rgba(0,0,0,.1);
    box-shadow:0 8px 24px rgba(0,0,0,.1);
}
#tp-root[data-theme="forest"] .tp-logo {
    background:rgba(255,255,255,.15);
}
.tp-title {
    font-size:26px;font-weight:900;letter-spacing:-.5px;
    background:linear-gradient(135deg,#C4B5FD,#67E8F9,#6EE7B7);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
    background-clip:text;
}
#tp-root[data-theme="nova"] .tp-title {
    background:linear-gradient(135deg,#7C3AED,#A78BFA,#EC4899);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
}
#tp-root[data-theme="ocean"] .tp-title {
    background:linear-gradient(135deg,#0EA5E9,#38BDF8,#06B6D4);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
}
#tp-root[data-theme="ember"] .tp-title {
    background:linear-gradient(135deg,#F97316,#FB923C,#EAB308);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
}
#tp-root[data-theme="verdant"] .tp-title {
    background:linear-gradient(135deg,#059669,#34D399,#10B981);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
}
#tp-root[data-theme="sunset"] .tp-title {
    background:linear-gradient(135deg,#DC2626,#F87171,#F59E0B);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
}
#tp-root[data-theme="arctic"] .tp-title {
    background:linear-gradient(135deg,#0284C7,#7DD3FC,#0F172A);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
}
#tp-root[data-theme="forest"] .tp-title {
    background:linear-gradient(135deg,#22C55E,#4ADE80,#F0FDF4);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
}
#tp-root[data-theme="candy"] .tp-title {
    background:linear-gradient(135deg,#DB2777,#F472B6,#F9A8D4);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
}
.tp-subtitle { 
    font-size:12px;color:rgba(255,255,255,.6);margin-top:2px;font-weight:500;
    transition:color .4s;
}
#tp-root[data-theme="nova"] .tp-subtitle,
#tp-root[data-theme="ocean"] .tp-subtitle,
#tp-root[data-theme="ember"] .tp-subtitle,
#tp-root[data-theme="verdant"] .tp-subtitle,
#tp-root[data-theme="sunset"] .tp-subtitle,
#tp-root[data-theme="arctic"] .tp-subtitle,
#tp-root[data-theme="candy"] .tp-subtitle {
    color:rgba(0,0,0,.5);
}
#tp-root[data-theme="forest"] .tp-subtitle {
    color:rgba(255,255,255,.5);
}
.tp-header-actions {
    margin-left:auto;display:flex;align-items:center;gap:10px;flex-wrap:wrap;
}
.tp-search-wrap {
    background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.15);
    border-radius:10px;display:flex;align-items:center;gap:8px;
    padding:9px 14px;backdrop-filter:blur(12px);min-width:240px;
    transition:all .3s;
}
#tp-root[data-theme="nova"] .tp-search-wrap,
#tp-root[data-theme="ocean"] .tp-search-wrap,
#tp-root[data-theme="ember"] .tp-search-wrap,
#tp-root[data-theme="verdant"] .tp-search-wrap,
#tp-root[data-theme="sunset"] .tp-search-wrap,
#tp-root[data-theme="arctic"] .tp-search-wrap,
#tp-root[data-theme="candy"] .tp-search-wrap {
    background:rgba(255,255,255,.7);
    border-color:rgba(0,0,0,.1);
}
#tp-root[data-theme="forest"] .tp-search-wrap {
    background:rgba(255,255,255,.08);
    border-color:rgba(255,255,255,.15);
}
.tp-search-ico { font-size:16px;opacity:.5; }
.tp-search-wrap input {
    border:none;outline:none;background:transparent;
    font-size:13px;font-weight:500;color:var(--txt);width:100%;font-family:inherit;
}
.tp-search-wrap input::placeholder { 
    color:rgba(255,255,255,.35);
    transition:color .4s;
}
#tp-root[data-theme="nova"] .tp-search-wrap input::placeholder,
#tp-root[data-theme="ocean"] .tp-search-wrap input::placeholder,
#tp-root[data-theme="ember"] .tp-search-wrap input::placeholder,
#tp-root[data-theme="verdant"] .tp-search-wrap input::placeholder,
#tp-root[data-theme="sunset"] .tp-search-wrap input::placeholder,
#tp-root[data-theme="arctic"] .tp-search-wrap input::placeholder,
#tp-root[data-theme="candy"] .tp-search-wrap input::placeholder {
    color:rgba(0,0,0,.35);
}
.tp-action-btn {
    background:rgba(124,58,237,.25);border:1px solid rgba(139,92,246,.4);
    color:#C4B5FD;border-radius:10px;padding:9px 16px;font-size:13px;
    font-weight:700;cursor:pointer;font-family:inherit;
    transition:all .15s;backdrop-filter:blur(12px);
}
.tp-action-btn:hover,
.tp-action-btn.active {
    background:rgba(124,58,237,.5);border-color:rgba(139,92,246,.7);color:#fff;
}
#tp-root[data-theme="nova"] .tp-action-btn {
    background:rgba(124,58,237,.1);
    border-color:rgba(124,58,237,.3);
    color:#5B21B6;
}
#tp-root[data-theme="nova"] .tp-action-btn:hover,
#tp-root[data-theme="nova"] .tp-action-btn.active {
    background:rgba(124,58,237,.2);
    border-color:rgba(124,58,237,.5);
}
#tp-root[data-theme="ocean"] .tp-action-btn {
    background:rgba(14,165,233,.1);
    border-color:rgba(14,165,233,.3);
    color:#075985;
}
#tp-root[data-theme="ocean"] .tp-action-btn:hover,
#tp-root[data-theme="ocean"] .tp-action-btn.active {
    background:rgba(14,165,233,.2);
    border-color:rgba(14,165,233,.5);
}
#tp-root[data-theme="ember"] .tp-action-btn {
    background:rgba(249,115,22,.1);
    border-color:rgba(249,115,22,.3);
    color:#9A3412;
}
#tp-root[data-theme="ember"] .tp-action-btn:hover,
#tp-root[data-theme="ember"] .tp-action-btn.active {
    background:rgba(249,115,22,.2);
    border-color:rgba(249,115,22,.5);
}
#tp-root[data-theme="verdant"] .tp-action-btn {
    background:rgba(5,150,105,.1);
    border-color:rgba(5,150,105,.3);
    color:#065F46;
}
#tp-root[data-theme="verdant"] .tp-action-btn:hover,
#tp-root[data-theme="verdant"] .tp-action-btn.active {
    background:rgba(5,150,105,.2);
    border-color:rgba(5,150,105,.5);
}
#tp-root[data-theme="sunset"] .tp-action-btn {
    background:rgba(220,38,38,.1);
    border-color:rgba(220,38,38,.3);
    color:#881337;
}
#tp-root[data-theme="sunset"] .tp-action-btn:hover,
#tp-root[data-theme="sunset"] .tp-action-btn.active {
    background:rgba(220,38,38,.2);
    border-color:rgba(220,38,38,.5);
}
#tp-root[data-theme="arctic"] .tp-action-btn {
    background:rgba(2,132,199,.1);
    border-color:rgba(2,132,199,.3);
    color:#1E3A5F;
}
#tp-root[data-theme="arctic"] .tp-action-btn:hover,
#tp-root[data-theme="arctic"] .tp-action-btn.active {
    background:rgba(2,132,199,.2);
    border-color:rgba(2,132,199,.5);
}
#tp-root[data-theme="forest"] .tp-action-btn {
    background:rgba(34,197,94,.2);
    border-color:rgba(34,197,94,.4);
    color:#86EFAC;
}
#tp-root[data-theme="forest"] .tp-action-btn:hover,
#tp-root[data-theme="forest"] .tp-action-btn.active {
    background:rgba(34,197,94,.3);
    border-color:rgba(34,197,94,.6);
}
#tp-root[data-theme="candy"] .tp-action-btn {
    background:rgba(219,39,119,.1);
    border-color:rgba(219,39,119,.3);
    color:#831843;
}
#tp-root[data-theme="candy"] .tp-action-btn:hover,
#tp-root[data-theme="candy"] .tp-action-btn.active {
    background:rgba(219,39,119,.2);
    border-color:rgba(219,39,119,.5);
}

/* ── THEME SELECTOR ── */
.tp-theme-selector {
    display:inline-block;
}
.tp-theme-btn {
    background:rgba(255,255,255,.08);
    border:1px solid rgba(255,255,255,.15);
    color:var(--txt);
    border-radius:10px;
    padding:9px 14px;
    font-size:13px;
    font-weight:600;
    cursor:pointer;
    font-family:inherit;
    transition:all .3s;
    backdrop-filter:blur(12px);
    display:flex;
    align-items:center;
    gap:6px;
}
.tp-theme-btn:hover {
    background:rgba(255,255,255,.15);
    transform:scale(1.02);
}
#tp-root[data-theme="nova"] .tp-theme-btn,
#tp-root[data-theme="ocean"] .tp-theme-btn,
#tp-root[data-theme="ember"] .tp-theme-btn,
#tp-root[data-theme="verdant"] .tp-theme-btn,
#tp-root[data-theme="sunset"] .tp-theme-btn,
#tp-root[data-theme="arctic"] .tp-theme-btn,
#tp-root[data-theme="candy"] .tp-theme-btn {
    background:rgba(0,0,0,.05);
    border-color:rgba(0,0,0,.1);
    color:var(--txt);
}
#tp-root[data-theme="nova"] .tp-theme-btn:hover,
#tp-root[data-theme="ocean"] .tp-theme-btn:hover,
#tp-root[data-theme="ember"] .tp-theme-btn:hover,
#tp-root[data-theme="verdant"] .tp-theme-btn:hover,
#tp-root[data-theme="sunset"] .tp-theme-btn:hover,
#tp-root[data-theme="arctic"] .tp-theme-btn:hover,
#tp-root[data-theme="candy"] .tp-theme-btn:hover {
    background:rgba(0,0,0,.1);
}
#tp-root[data-theme="forest"] .tp-theme-btn {
    background:rgba(255,255,255,.08);
    border-color:rgba(255,255,255,.15);
}

/* ── KPI STRIP ── */
.tp-kpi-strip {
    display:flex;gap:12px;flex-wrap:wrap;
    padding:0 0 20px;border-bottom:1px solid var(--bdr);
    transition:border-color .4s;
}
.tp-kpi {
    background:rgba(255,255,255,.05);border:1px solid var(--bdr);
    border-left:3px solid var(--kc);
    border-radius:12px;padding:12px 16px;
    display:flex;align-items:center;gap:12px;flex:1;min-width:120px;
    backdrop-filter:blur(8px);transition:all .3s;
}
.tp-kpi:hover { 
    background:rgba(255,255,255,.09);
    transform:translateY(-2px);
    border-color:var(--kc);
}
#tp-root[data-theme="nova"] .tp-kpi,
#tp-root[data-theme="ocean"] .tp-kpi,
#tp-root[data-theme="ember"] .tp-kpi,
#tp-root[data-theme="verdant"] .tp-kpi,
#tp-root[data-theme="sunset"] .tp-kpi,
#tp-root[data-theme="arctic"] .tp-kpi,
#tp-root[data-theme="candy"] .tp-kpi {
    background:rgba(255,255,255,.7);
    border-color:rgba(0,0,0,.06);
}
#tp-root[data-theme="nova"] .tp-kpi:hover,
#tp-root[data-theme="ocean"] .tp-kpi:hover,
#tp-root[data-theme="ember"] .tp-kpi:hover,
#tp-root[data-theme="verdant"] .tp-kpi:hover,
#tp-root[data-theme="sunset"] .tp-kpi:hover,
#tp-root[data-theme="arctic"] .tp-kpi:hover,
#tp-root[data-theme="candy"] .tp-kpi:hover {
    background:rgba(255,255,255,.9);
}
#tp-root[data-theme="forest"] .tp-kpi {
    background:rgba(255,255,255,.06);
    border-color:rgba(255,255,255,.08);
}
.tp-kpi-icon { font-size:22px;flex-shrink:0; }
.tp-kpi-num {
    font-size:24px;font-weight:900;color:var(--txt);line-height:1;
    min-height:28px;display:flex;align-items:center;
    transition:color .4s;
}
.tp-kpi-label { 
    font-size:10px;color:var(--mu);font-weight:600;margin-top:2px;
    text-transform:uppercase;letter-spacing:.4px;
    transition:color .4s;
}
.tp-spinner {
    width:14px;height:14px;border:2px solid rgba(255,255,255,.15);
    border-top-color:var(--kc,#7C3AED);border-radius:50%;
    animation:spin .7s linear infinite;display:inline-block;
}
@keyframes spin { to { transform:rotate(360deg); } }

/* ── SECTION LABEL ── */
.tp-section-label {
    font-size:11px;font-weight:800;text-transform:uppercase;
    letter-spacing:.6px;color:var(--mu);
    padding:0 28px;margin-bottom:12px;
    transition:color .4s;
}

/* ── QUICK ACTIONS ── */
.tp-quick-row { padding:20px 28px 16px; }
.tp-quick-btns { display:flex;gap:8px;flex-wrap:wrap;margin-top:10px; }
.tp-qbtn {
    padding:9px 18px;border-radius:10px;font-size:13px;font-weight:700;
    cursor:pointer;border:none;font-family:inherit;transition:all .15s;
    letter-spacing:-.1px;
}
.tp-qbtn:hover { transform:translateY(-2px);box-shadow:0 6px 18px rgba(0,0,0,.3); }
.tp-qbtn-purple { background:rgba(124,58,237,.25);color:#C4B5FD;border:1px solid rgba(124,58,237,.4); }
.tp-qbtn-purple:hover { background:#7C3AED;color:#fff; }
#tp-root[data-theme="nova"] .tp-qbtn-purple { background:rgba(124,58,237,.1);color:#7C3AED;border-color:rgba(124,58,237,.3); }
#tp-root[data-theme="nova"] .tp-qbtn-purple:hover { background:#7C3AED;color:#fff; }
#tp-root[data-theme="ocean"] .tp-qbtn-purple { background:rgba(14,165,233,.1);color:#0EA5E9;border-color:rgba(14,165,233,.3); }
#tp-root[data-theme="ocean"] .tp-qbtn-purple:hover { background:#0EA5E9;color:#fff; }
#tp-root[data-theme="ember"] .tp-qbtn-purple { background:rgba(249,115,22,.1);color:#F97316;border-color:rgba(249,115,22,.3); }
#tp-root[data-theme="ember"] .tp-qbtn-purple:hover { background:#F97316;color:#fff; }
#tp-root[data-theme="verdant"] .tp-qbtn-purple { background:rgba(5,150,105,.1);color:#059669;border-color:rgba(5,150,105,.3); }
#tp-root[data-theme="verdant"] .tp-qbtn-purple:hover { background:#059669;color:#fff; }
#tp-root[data-theme="sunset"] .tp-qbtn-purple { background:rgba(220,38,38,.1);color:#DC2626;border-color:rgba(220,38,38,.3); }
#tp-root[data-theme="sunset"] .tp-qbtn-purple:hover { background:#DC2626;color:#fff; }
#tp-root[data-theme="arctic"] .tp-qbtn-purple { background:rgba(2,132,199,.1);color:#0284C7;border-color:rgba(2,132,199,.3); }
#tp-root[data-theme="arctic"] .tp-qbtn-purple:hover { background:#0284C7;color:#fff; }
#tp-root[data-theme="forest"] .tp-qbtn-purple { background:rgba(34,197,94,.2);color:#4ADE80;border-color:rgba(34,197,94,.4); }
#tp-root[data-theme="forest"] .tp-qbtn-purple:hover { background:#22C55E;color:#fff; }
#tp-root[data-theme="candy"] .tp-qbtn-purple { background:rgba(219,39,119,.1);color:#DB2777;border-color:rgba(219,39,119,.3); }
#tp-root[data-theme="candy"] .tp-qbtn-purple:hover { background:#DB2777;color:#fff; }

.tp-qbtn-blue   { background:rgba(37,99,235,.25);color:#93C5FD;border:1px solid rgba(37,99,235,.4); }
.tp-qbtn-blue:hover   { background:#2563EB;color:#fff; }
.tp-qbtn-pink   { background:rgba(219,39,119,.25);color:#F9A8D4;border:1px solid rgba(219,39,119,.4); }
.tp-qbtn-pink:hover   { background:#DB2777;color:#fff; }
.tp-qbtn-teal   { background:rgba(13,148,136,.25);color:#5EEAD4;border:1px solid rgba(13,148,136,.4); }
.tp-qbtn-teal:hover   { background:#0D9488;color:#fff; }
.tp-qbtn-amber  { background:rgba(217,119,6,.25);color:#FCD34D;border:1px solid rgba(217,119,6,.4); }
.tp-qbtn-amber:hover  { background:#D97706;color:#fff; }
.tp-qbtn-green  { background:rgba(5,150,105,.25);color:#6EE7B7;border:1px solid rgba(5,150,105,.4); }
.tp-qbtn-green:hover  { background:#059669;color:#fff; }

/* ── SHORTCUT GRID ── */
.tp-grid {
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:14px;padding:0 28px;
}

/* ── GROUP CARD ── */
.tp-group {
    background:var(--glass);
    border:1px solid var(--bdr);
    border-top:3px solid var(--gc);
    border-radius:16px;overflow:hidden;
    backdrop-filter:blur(10px);
    display:flex;flex-direction:column;
    transition:all .3s;
}
.tp-group:hover {
    transform:translateY(-3px);
    box-shadow:0 12px 36px rgba(0,0,0,.35),
               0 0 0 1px var(--gc);
    background:rgba(255,255,255,.09);
}
#tp-root[data-theme="nova"] .tp-group,
#tp-root[data-theme="ocean"] .tp-group,
#tp-root[data-theme="ember"] .tp-group,
#tp-root[data-theme="verdant"] .tp-group,
#tp-root[data-theme="sunset"] .tp-group,
#tp-root[data-theme="arctic"] .tp-group,
#tp-root[data-theme="candy"] .tp-group {
    background:rgba(255,255,255,.7);
    border-color:rgba(0,0,0,.06);
}
#tp-root[data-theme="nova"] .tp-group:hover,
#tp-root[data-theme="ocean"] .tp-group:hover,
#tp-root[data-theme="ember"] .tp-group:hover,
#tp-root[data-theme="verdant"] .tp-group:hover,
#tp-root[data-theme="sunset"] .tp-group:hover,
#tp-root[data-theme="arctic"] .tp-group:hover,
#tp-root[data-theme="candy"] .tp-group:hover {
    background:rgba(255,255,255,.9);
}
#tp-root[data-theme="forest"] .tp-group {
    background:rgba(20,83,45,.6);
    border-color:rgba(255,255,255,.08);
}
.tp-group-hdr {
    padding:11px 14px;
    background:linear-gradient(90deg,rgba(var(--gc-rgb),.12),transparent);
    display:flex;align-items:center;gap:8px;
    border-bottom:1px solid var(--bdr);
    transition:border-color .4s;
}
.tp-group-icon { font-size:16px; }
.tp-group-name { font-weight:700;font-size:12px;color:var(--txt);flex:1; }
.tp-group-cnt  {
    font-size:10px;font-weight:800;color:var(--gc);
    background:rgba(255,255,255,.06);padding:2px 9px;border-radius:99px;
    border:1px solid rgba(255,255,255,.1);
}
#tp-root[data-theme="nova"] .tp-group-cnt,
#tp-root[data-theme="ocean"] .tp-group-cnt,
#tp-root[data-theme="ember"] .tp-group-cnt,
#tp-root[data-theme="verdant"] .tp-group-cnt,
#tp-root[data-theme="sunset"] .tp-group-cnt,
#tp-root[data-theme="arctic"] .tp-group-cnt,
#tp-root[data-theme="candy"] .tp-group-cnt {
    background:rgba(0,0,0,.04);
}
.tp-group-body { padding:8px 10px 12px;display:flex;flex-direction:column;gap:3px;flex:1; }

/* ── SHORTCUT ITEM ── */
.tp-item {
    display:flex;align-items:center;gap:8px;
    padding:6px 9px;border-radius:10px;
    background:transparent;border:1px solid transparent;
    cursor:pointer;transition:all .13s;
}
.tp-item:hover {
    background:rgba(255,255,255,.06);
    border-color:rgba(255,255,255,.1);
    transform:translateX(4px);
}
#tp-root[data-theme="nova"] .tp-item:hover,
#tp-root[data-theme="ocean"] .tp-item:hover,
#tp-root[data-theme="ember"] .tp-item:hover,
#tp-root[data-theme="verdant"] .tp-item:hover,
#tp-root[data-theme="sunset"] .tp-item:hover,
#tp-root[data-theme="arctic"] .tp-item:hover,
#tp-root[data-theme="candy"] .tp-item:hover {
    background:rgba(0,0,0,.04);
    border-color:rgba(0,0,0,.08);
}
#tp-root[data-theme="forest"] .tp-item:hover {
    background:rgba(255,255,255,.06);
    border-color:rgba(255,255,255,.1);
}
.tp-fav {
    background:none;border:none;cursor:pointer;
    font-size:13px;opacity:.2;color:#A78BFA;
    transition:all .2s;padding:0 2px;flex-shrink:0;
    line-height:1;
}
.tp-fav:hover { opacity:1;transform:scale(1.3); }
.tp-fav.active { opacity:1;color:#F472B6; }
.tp-ico {
    width:24px;height:24px;border-radius:8px;
    background:rgba(255,255,255,.06);
    display:flex;align-items:center;justify-content:center;
    font-size:11px;flex-shrink:0;
    border:1px solid rgba(255,255,255,.08);
}
#tp-root[data-theme="nova"] .tp-ico,
#tp-root[data-theme="ocean"] .tp-ico,
#tp-root[data-theme="ember"] .tp-ico,
#tp-root[data-theme="verdant"] .tp-ico,
#tp-root[data-theme="sunset"] .tp-ico,
#tp-root[data-theme="arctic"] .tp-ico,
#tp-root[data-theme="candy"] .tp-ico {
    background:rgba(0,0,0,.04);
    border-color:rgba(0,0,0,.06);
}
.tp-name {
    font-size:11.5px;font-weight:500;color:var(--mu);line-height:1.3;flex:1;
    transition:color .2s;
}
.tp-item:hover .tp-name { color:var(--txt); }
.tp-arr { font-size:10px;color:var(--mu);opacity:0;transition:opacity .15s; }
.tp-item:hover .tp-arr { opacity:1;color:var(--ic,#7C3AED); }

/* ── EMPTY ── */
.tp-empty {
    text-align:center;padding:50px 20px;
    background:rgba(255,255,255,.03);
    border-radius:16px;margin:0 28px;
    border:1px dashed var(--bdr);
}
.tp-empty-title { font-size:16px;font-weight:700;color:var(--txt);margin-bottom:5px; }
.tp-empty-sub   { font-size:13px;color:var(--mu); }

/* ── FOOTER ── */
.tp-footer {
    text-align:center;margin-top:32px;padding:0 28px;
    font-size:11px;color:rgba(255,255,255,.2);font-weight:500;
    transition:color .4s;
}
#tp-root[data-theme="nova"] .tp-footer,
#tp-root[data-theme="ocean"] .tp-footer,
#tp-root[data-theme="ember"] .tp-footer,
#tp-root[data-theme="verdant"] .tp-footer,
#tp-root[data-theme="sunset"] .tp-footer,
#tp-root[data-theme="arctic"] .tp-footer,
#tp-root[data-theme="candy"] .tp-footer {
    color:rgba(0,0,0,.2);
}
#tp-root[data-theme="forest"] .tp-footer {
    color:rgba(255,255,255,.15);
}
#tp-theme-indicator { font-weight:700;color:var(--mu); }

/* ── LOAD ANIMATION ── */
@keyframes slideUp {
    from { opacity:0;transform:translateY(16px); }
    to   { opacity:1;transform:translateY(0); }
}
.anim-in { animation:slideUp .35s ease both; }

/* ── RESPONSIVE ── */
@media(max-width:1200px) { .tp-grid { grid-template-columns:repeat(2,1fr); } }
@media(max-width:768px) {
    .tp-grid { grid-template-columns:1fr;padding:0 14px; }
    .tp-quick-row,.tp-section-label { padding-left:14px;padding-right:14px; }
    .tp-header { padding:18px 14px 0; }
    .tp-header-actions { margin-left:0;width:100%; }
    .tp-search-wrap { min-width:100%; }
    .tp-title { font-size:20px; }
    .tp-kpi { min-width:40%; }
    .tp-theme-selector { width:100%; }
    .tp-theme-btn { width:100%;justify-content:center; }
}
</style>`;

    $(page.main).append(html);

    // ── THEME FUNCTIONS ────────────────────────────────────────────────────
    window.tpCycleTheme = function() {
        const keys = Object.keys(TP_THEMES);
        const idx = keys.indexOf(currentTheme);
        currentTheme = keys[(idx + 1) % keys.length];
        applyTheme(currentTheme);
    };

    function applyTheme(theme) {
        const root = document.getElementById('tp-root');
        root.dataset.theme = theme;
        document.getElementById('tp-theme-btn').innerHTML =
            `${TP_THEMES[theme].icon} <span id="tp-theme-name">${TP_THEMES[theme].name}</span>`;
        document.getElementById('tp-theme-indicator').textContent = TP_THEMES[theme].name;
        try { localStorage.setItem('tp-theme', theme); } catch(e) { /* silent */ }
    }

    // ── LOAD KPIs from ERPNext ────────────────────────────────────────────
    function animateCount(el, target) {
        let start = 0;
        const duration = 800;
        const step = Math.ceil(target / (duration / 16));
        const timer = setInterval(() => {
            start = Math.min(start + step, target);
            el.textContent = start.toLocaleString();
            if (start >= target) clearInterval(timer);
        }, 16);
    }

    KPIS.forEach(kpi => {
        frappe.call({
            method: kpi.method,
            args:   kpi.args,
            callback: function (r) {
                const el  = document.getElementById(kpi.id);
                const num = parseInt(r.message) || 0;
                if (el) {
                    el.innerHTML = '<span>0</span>';
                    animateCount(el.querySelector('span'), num);
                }
            }
        });
    });

    // Timestamp
    const ts = document.getElementById('tp-refreshed');
    if (ts) ts.textContent = new Date().toLocaleTimeString();

    // ── NAVIGATION ────────────────────────────────────────────────────────
    function tpOpen(route, name) {
        let url = route;
        if (!url) {
            const slug = name.toLowerCase().replace(/\s+/g, '-');
            url = '/app/' + slug;
        }
        const win = window.open(url, '_blank');
        if (win) win.focus(); else frappe.set_route(url.replace(/^\/app\//, ''));
    }

    // ── DELEGATED CLICK ──────────────────────────────────────────────────
    document.getElementById('tp-grid').addEventListener('click', function (e) {
        const favBtn = e.target.closest('.tp-fav');
        if (favBtn) { e.stopPropagation(); tpToggleFav(favBtn.dataset.name); return; }
        const item = e.target.closest('.tp-item');
        if (item) tpOpen(item.dataset.route, item.dataset.name);
    });

    // ── FAVOURITES ──────────────────────────────────────────────────────
    function tpGetFavs() { 
        try { return JSON.parse(localStorage.getItem('tp_favs') || '[]'); } 
        catch(e) { return []; } 
    }
    function tpSetFavs(f) { 
        try { localStorage.setItem('tp_favs', JSON.stringify(f)); } 
        catch(e) { /* silent */ } 
    }

    function tpToggleFav(name) {
        const favs = tpGetFavs();
        const idx  = favs.indexOf(name);
        if (idx > -1) favs.splice(idx, 1); else favs.push(name);
        tpSetFavs(favs);
        tpRenderFavBtns();
    }

    function tpRenderFavBtns() {
        const favs = tpGetFavs();
        document.querySelectorAll('.tp-fav').forEach(b => {
            const on = favs.includes(b.dataset.name);
            b.textContent = on ? '♥' : '♡';
            b.classList.toggle('active', on);
        });
        const count = document.getElementById('tp-fav-count');
        if (count) count.textContent = favs.length;
    }

    // ── FAVOURITES FILTER ──────────────────────────────────────────────
    let favMode = false;
    window.tpShowFavs = function () {
        favMode = !favMode;
        const btn = document.getElementById('tp-fav-toggle-btn');
        btn.classList.toggle('active', favMode);
        btn.textContent = favMode ? '♥ Show All' : '♡ Favourites';

        const favs = tpGetFavs();
        document.querySelectorAll('.tp-group').forEach(g => {
            let vis = false;
            g.querySelectorAll('.tp-item').forEach(item => {
                const show = !favMode || favs.includes(item.dataset.name);
                item.style.display = show ? 'flex' : 'none';
                if (show) vis = true;
            });
            g.style.display = vis ? 'flex' : 'none';
        });
    };

    // ── SEARCH ──────────────────────────────────────────────────────────
    const searchInput = document.getElementById('tp-search');

    if (searchInput) {
        searchInput.addEventListener('input', function () {
            const q = this.value.toLowerCase().trim();
            let n = 0;
            document.querySelectorAll('.tp-group').forEach(g => {
                let vis = false;
                g.querySelectorAll('.tp-item').forEach(item => {
                    const match = !q || item.dataset.name.toLowerCase().includes(q);
                    item.style.display = match ? 'flex' : 'none';
                    if (match) { vis = true; n++; }
                });
                g.style.display = vis ? 'flex' : 'none';
            });
            const empty = document.getElementById('tp-empty');
            const grid = document.getElementById('tp-grid');
            if (empty) empty.style.display = n ? 'none' : 'block';
            if (grid) grid.style.display  = n ? 'grid' : 'none';
        });
    }

    // Ctrl+K shortcut
    document.addEventListener('keydown', function (e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }
    });

    // ── APPLY SAVED THEME ──────────────────────────────────────────────
    applyTheme(currentTheme);

    // ── INIT ─────────────────────────────────────────────────────────────
    tpRenderFavBtns();
};