// Copyright (c) 2026, Kunle Oduntan / Value Impacts Consulting
// general/general_biz_apps/page/ap_ar_check/ap_ar_check.js
//
// ╔══════════════════════════════════════════════════════════════════════════════╗
// ║  AP / AR / STOCK CHECK  —  Three-Level Reconciliation Intelligence          ║
// ║                                                                              ║
// ║  Level 1  · Control Total   ─ Are aggregate debits/credits equal?           ║
// ║  Level 2  · Party Variance  ─ Which customer/supplier is causing the gap?   ║
// ║  Level 3  · Orphan Scan     ─ Which exact vouchers exist on one side only?  ║
// ║             (VLOOKUP-engine on voucher_type + voucher_no + party)            ║
// ║                                                                              ║
// ║  Secondary checks (AR · AP · Stock) run alongside the core engine           ║
// ╚══════════════════════════════════════════════════════════════════════════════╝

(function () {
    'use strict';

    if (!window.APARCheckNS) {
        window.APARCheckNS = {};
        _define();
    }

    frappe.pages['ap-ar-check'].on_page_load = function (wrapper) {
        _boot(wrapper);
    };
    frappe.pages['ap-ar-check'].on_page_show = function (wrapper) {
        if (!wrapper._apar) _boot(wrapper);
    };

    function _boot(wrapper) {
        const fa = document.getElementById('fa-apar');
        if (!fa) {
            const el = document.createElement('link');
            el.id = 'fa-apar'; el.rel = 'stylesheet';
            el.href = 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css';
            el.onload = el.onerror = () => _mount(wrapper);
            document.head.appendChild(el);
        } else {
            _mount(wrapper);
        }
    }

    function _mount(wrapper) {
        wrapper._apar = new window.APARCheckNS.APARCheck(wrapper);
    }

    // ─────────────────────────────────────────────────────────────────────────
    function _define() {

// ── THEMES ────────────────────────────────────────────────────────────────────
const THEMES = {
    ledger: {
        name:'Ledger', icon:'📒', dark:false,
        bg:'#F4F7FB', bg2:'#E8EEF7', bg3:'#D5E0F0', card:'#FFFFFF',
        brd:'#C5D4E8', brd2:'#A8BFD8', tx1:'#1A2B45', tx2:'#3D5A80', tx3:'#7A96B2',
        pri:'#2563EB', pri_d:'#1D4ED8', grn:'#10B981', red:'#EF4444', amb:'#F59E0B',
        banner:'linear-gradient(135deg,#0F172A 0%,#1D3461 45%,#2563EB 75%,#10B981 100%)',
    },
    sakura: {
        name:'Sakura', icon:'🌸', dark:false,
        bg:'#FFF5F8', bg2:'#FFE4EC', bg3:'#FFCDE0', card:'#FFFFFF',
        brd:'#FFB8D0', brd2:'#FF9EBF', tx1:'#5C1A3A', tx2:'#9B4D6E', tx3:'#D4A5BC',
        pri:'#FF69B4', pri_d:'#E855A0', grn:'#90EE90', red:'#FF6B6B', amb:'#FFB347',
        banner:'linear-gradient(135deg,#5C1A3A 0%,#9B4D6E 40%,#FF69B4 70%,#FFB347 100%)',
    },
    cosmic: {
        name:'Cosmic', icon:'✨', dark:true,
        bg:'#0F0F23', bg2:'#1A1A35', bg3:'#25254A', card:'#1A1A35',
        brd:'rgba(157,108,244,0.2)', brd2:'rgba(157,108,244,0.4)',
        tx1:'#E8E8FF', tx2:'#B8B8E8', tx3:'#8888C8',
        pri:'#9D6CF4', pri_d:'#7D4CD4', grn:'#6FCF97', red:'#EB5757', amb:'#F2994A',
        banner:'linear-gradient(135deg,#0F0F23 0%,#1A1A35 40%,#9D6CF4 70%,#6FCF97 100%)',
    },
    minty: {
        name:'Minty', icon:'🌱', dark:false,
        bg:'#F0FFF4', bg2:'#DCFFE8', bg3:'#C0F0D0', card:'#FFFFFF',
        brd:'#A8E6B0', brd2:'#7DD48C', tx1:'#1A4D2A', tx2:'#2E7D5A', tx3:'#7DCFA6',
        pri:'#48C9B0', pri_d:'#3BA99F', grn:'#52D78B', red:'#FF6B8B', amb:'#FFB347',
        banner:'linear-gradient(135deg,#1A4D2A 0%,#2E7D5A 40%,#48C9B0 70%,#52D78B 100%)',
    },
    starlight: {
        name:'Starlight', icon:'⭐', dark:true,
        bg:'#121826', bg2:'#1A2235', bg3:'#222D45', card:'#1A2235',
        brd:'rgba(255,215,0,0.15)', brd2:'rgba(255,215,0,0.3)',
        tx1:'#FFD700', tx2:'#FFC107', tx3:'#D4A017',
        pri:'#FFD700', pri_d:'#FFC000', grn:'#98FB98', red:'#FF6B6B', amb:'#FFA500',
        banner:'linear-gradient(135deg,#121826 0%,#1A2235 40%,#FFD700 70%,#FFA500 100%)',
    },
};

// ── ORPHAN CLASS CONFIG ───────────────────────────────────────────────────────
const ORPHAN = {
    GL_ONLY:       { icon:'🔴', label:'GL Only',        color:'#EF4444', bg:'#FEF2F2', tip:'In control account — missing from subledger' },
    SL_ONLY:       { icon:'🟣', label:'Subledger Only', color:'#8B5CF6', bg:'#F5F3FF', tip:'In subledger — missing from control account' },
    MISMATCH:      { icon:'🟡', label:'Mismatch',       color:'#F59E0B', bg:'#FFFBEB', tip:'Present in both — amounts differ' },
    PARTY_MISSING: { icon:'⚫', label:'No Party Tag',   color:'#1F2937', bg:'#F9FAFB', tip:'Control account entry with no customer/supplier assigned' },
};

const SEV = {
    Critical: { color:'#EF4444', bg:'#FEF2F2', icon:'🚨', order:1 },
    High:     { color:'#F59E0B', bg:'#FFFBEB', icon:'⚠️', order:2 },
    Medium:   { color:'#3B82F6', bg:'#EFF6FF', icon:'🔵', order:3 },
    Low:      { color:'#10B981', bg:'#ECFDF5', icon:'💚', order:4 },
};

const TYPE = {
    AR:    { color:'#0EA5E9', bg:'#F0F9FF', icon:'📤', label:'AR' },
    AP:    { color:'#8B5CF6', bg:'#F5F3FF', icon:'📥', label:'AP' },
    Stock: { color:'#10B981', bg:'#ECFDF5', icon:'📦', label:'Stock' },
};

const LEVEL = {
    L2:  { color:'#F59E0B', label:'Party',  icon:'👤' },
    L3:  { color:'#EF4444', label:'Orphan', icon:'🔍' },
    SEC: { color:'#6B7280', label:'Sec',    icon:'📋' },
};

// ── UTILS ────────────────────────────────────────────────────────────────────
const flt  = v => { const n = parseFloat(v); return isNaN(n) ? 0 : n; };
const fmt  = (v, d=2) => flt(v).toLocaleString('en-NG', {minimumFractionDigits:d, maximumFractionDigits:d});
const abbr = v => { const n = flt(v); return n >= 1e9 ? '₦'+(n/1e9).toFixed(2)+'B' : n >= 1e6 ? '₦'+(n/1e6).toFixed(2)+'M' : n >= 1e3 ? '₦'+(n/1e3).toFixed(0)+'K' : '₦'+Math.round(n).toLocaleString(); };
const esc  = s => String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');


// ═════════════════════════════════════════════════════════════════════════════
//  MAIN CLASS
// ═════════════════════════════════════════════════════════════════════════════
window.APARCheckNS.APARCheck = class APARCheck {
    constructor(wrapper) {
        this.wrapper     = wrapper;
        this.theme       = THEMES.ledger;
        this.rows        = [];
        this.filtered    = [];
        this.level1      = {};
        this.summary     = {};
        this.aiResult    = null;
        this.sortCol     = 'row_number';
        this.sortAsc     = true;
        this.page        = 1;
        this.pageSize    = 25;
        this.running     = false;
        this.activeTab   = 'orphan';   // 'orphan' | 'party' | 'secondary' | 'all'
        this._build();
    }

    // ── DOM INIT ─────────────────────────────────────────────────────────────
    _build() {
        this._css();
        this.wrapper.innerHTML = '';
        const root = document.createElement('div');
        root.id = 'apar-root';
        root.innerHTML = this._skeleton();
        this.wrapper.appendChild(root);
        this._theme();
        this._bind();
        this._defaultDates();
    }

    $(id) { return document.getElementById(id); }

    _skeleton() {
        const themeBtns = Object.entries(THEMES).map(([k,t]) =>
            `<button class="ap-theme-btn" data-t="${k}" title="${t.name}">${t.icon}</button>`
        ).join('');

        return `
<!-- BANNER -->
<div class="ap-banner" id="ap-banner">
    <div class="ap-banner-l">
        <div class="ap-banner-icon">⚖️</div>
        <div>
            <div class="ap-banner-title">Subledger Reconciliation Engine</div>
            <div class="ap-banner-sub">Three-Level AP · AR · Stock Intelligence — VLOOKUP-style voucher matching</div>
        </div>
    </div>
    <div class="ap-banner-r">
        <div class="ap-themes">${themeBtns}</div>
        <div id="ap-health" class="ap-health" style="display:none"></div>
    </div>
</div>

<!-- LEVEL EXPLAINER (shown before first run) -->
<div id="ap-explainer" class="ap-explainer">
    <div class="ap-expl-grid">
        <div class="ap-expl-card" style="border-color:#10B981">
            <div class="ap-expl-num" style="background:#10B981">L1</div>
            <div class="ap-expl-title">Control Total</div>
            <div class="ap-expl-desc">Are the aggregate debits and credits on the GL control account equal to the sum of all party-tagged entries on the same account?</div>
            <div class="ap-expl-tag">Runs automatically</div>
        </div>
        <div class="ap-expl-card" style="border-color:#F59E0B">
            <div class="ap-expl-num" style="background:#F59E0B">L2</div>
            <div class="ap-expl-title">Party Variance</div>
            <div class="ap-expl-desc">Group both sides by customer or supplier. Which specific party has a GL balance that does not match their subledger balance?</div>
            <div class="ap-expl-tag">Who is affected?</div>
        </div>
        <div class="ap-expl-card" style="border-color:#EF4444">
            <div class="ap-expl-num" style="background:#EF4444">L3</div>
            <div class="ap-expl-title">Orphan Scan</div>
            <div class="ap-expl-desc">VLOOKUP every voucher across both sides using voucher_type + voucher_no + party. Flag vouchers that exist on one side only, or where amounts differ.</div>
            <div class="ap-expl-tag" style="background:#EF444420;color:#EF4444">Core engine — most critical</div>
        </div>
    </div>
    <div class="ap-expl-orphan-legend">
        ${Object.entries(ORPHAN).map(([k,v]) => `
        <div class="ap-legend-chip">
            <span>${v.icon}</span>
            <span style="font-weight:700;color:${v.color}">${v.label}</span>
            <span style="color:#6B7280;font-size:11px">— ${v.tip}</span>
        </div>`).join('')}
    </div>
</div>

<!-- CONTROLS -->
<div class="ap-controls" id="ap-controls">
    <div class="ap-ctrl-row">
        <div class="ap-ctrl-g">
            <label class="ap-lbl">📅 From Date</label>
            <input type="date" id="ap-from" class="ap-input" />
        </div>
        <div class="ap-ctrl-g">
            <label class="ap-lbl">📅 To Date</label>
            <input type="date" id="ap-to" class="ap-input" />
        </div>
        <div class="ap-ctrl-g">
            <label class="ap-lbl">🏢 Company</label>
            <input type="text" id="ap-company" class="ap-input" placeholder="All companies" style="width:200px" />
        </div>
        <div class="ap-ctrl-g">
            <label class="ap-lbl">🎯 Scope</label>
            <select id="ap-scope" class="ap-select">
                <option value="Both">AR + AP + Stock</option>
                <option value="AR Only">AR Only</option>
                <option value="AP Only">AP Only</option>
            </select>
        </div>
        <div class="ap-ctrl-g">
            <label class="ap-lbl">👤 Party Filter</label>
            <input type="text" id="ap-party" class="ap-input" placeholder="Customer / Supplier" style="width:180px" />
        </div>
        <div class="ap-ctrl-g">
            <label class="ap-lbl">⚠️ Min Severity</label>
            <select id="ap-sev" class="ap-select">
                <option value="All">All</option>
                <option value="Critical">Critical only</option>
                <option value="High">High+</option>
                <option value="Medium">Medium+</option>
            </select>
        </div>
    </div>
    <div class="ap-ctrl-actions">
        <button id="ap-run" class="ap-btn ap-btn-primary">
            <i class="fa fa-play"></i> Run Full Check
        </button>
        <button id="ap-l3-only" class="ap-btn ap-btn-l3">
            <i class="fa fa-search"></i> L3 Orphan Scan Only
        </button>
        <button id="ap-ai" class="ap-btn ap-btn-ai" style="display:none">
            <i class="fa fa-robot"></i> AI Analysis
        </button>
        <button id="ap-export" class="ap-btn ap-btn-ghost" style="display:none">
            <i class="fa fa-download"></i> Export CSV
        </button>
        <div id="ap-spin" class="ap-spin-wrap" style="display:none">
            <div class="ap-spinner"></div>
            <span id="ap-spin-msg">Running...</span>
        </div>
    </div>
</div>

<!-- LEVEL 1: CONTROL TOTAL PANEL -->
<div id="ap-l1" class="ap-l1-panel" style="display:none"></div>

<!-- KPI STRIP -->
<div id="ap-kpis" class="ap-kpis" style="display:none"></div>

<!-- AI PANEL -->
<div id="ap-ai-panel" class="ap-ai-panel" style="display:none"></div>

<!-- VIEW TABS -->
<div id="ap-tabs" class="ap-tabs" style="display:none">
    <button class="ap-tab active" data-tab="orphan">
        🔍 L3 Orphan Scan <span id="ap-tab-l3-count" class="ap-tab-badge"></span>
    </button>
    <button class="ap-tab" data-tab="party">
        👤 L2 Party Variance <span id="ap-tab-l2-count" class="ap-tab-badge"></span>
    </button>
    <button class="ap-tab" data-tab="pivot">
        📊 Recon Pivot <span id="ap-tab-pivot-count" class="ap-tab-badge ap-tab-badge-pivot">NEW</span>
    </button>
    <button class="ap-tab" data-tab="secondary">
        📋 Secondary Checks <span id="ap-tab-sec-count" class="ap-tab-badge"></span>
    </button>
    <button class="ap-tab" data-tab="all">
        🗂 All Issues <span id="ap-tab-all-count" class="ap-tab-badge"></span>
    </button>
</div>

<!-- PIVOT PANEL (separate from main table, shown only on pivot tab) -->
<div id="ap-pivot-panel" style="display:none"></div>

<!-- FILTER BAR -->
<div id="ap-fbar" class="ap-fbar" style="display:none">
    <div class="ap-fbar-l">
        <input type="text" id="ap-search" class="ap-input" placeholder="🔍 Search voucher, party, description..." style="width:300px" />
        <select id="ap-type-f" class="ap-select">
            <option value="">All Types</option>
            <option value="AR">📤 AR</option>
            <option value="AP">📥 AP</option>
            <option value="Stock">📦 Stock</option>
        </select>
        <select id="ap-orphan-f" class="ap-select" id="ap-orphan-f">
            <option value="">All Orphan Classes</option>
            <option value="GL_ONLY">🔴 GL Only</option>
            <option value="SL_ONLY">🟣 Subledger Only</option>
            <option value="MISMATCH">🟡 Mismatch</option>
            <option value="PARTY_MISSING">⚫ No Party Tag</option>
        </select>
        <select id="ap-sev-f" class="ap-select">
            <option value="">All Severities</option>
            <option value="Critical">🚨 Critical</option>
            <option value="High">⚠️ High</option>
            <option value="Medium">🔵 Medium</option>
            <option value="Low">💚 Low</option>
        </select>
    </div>
    <div class="ap-fbar-r">
        <span id="ap-count" class="ap-count-label"></span>
        <select id="ap-pgsize" class="ap-select" style="width:100px">
            <option value="25">25 / page</option>
            <option value="50">50 / page</option>
            <option value="100">100 / page</option>
        </select>
    </div>
</div>

<!-- TABLE -->
<div id="ap-table-wrap" style="display:none">
    <table class="ap-table" id="ap-table">
        <thead id="ap-thead"></thead>
        <tbody id="ap-tbody"></tbody>
    </table>
    <div id="ap-paging" class="ap-paging"></div>
</div>

<!-- EMPTY -->
<div id="ap-empty" class="ap-empty" style="display:none">
    <div style="font-size:48px">✨</div>
    <div class="ap-empty-title">All Clear</div>
    <div class="ap-empty-sub">No issues found for the selected filters.</div>
</div>
`;
    }

    // ── BIND ─────────────────────────────────────────────────────────────────
    _bind() {
        this.$('ap-run').addEventListener('click',     () => this._run(false));
        this.$('ap-l3-only').addEventListener('click', () => this._run(true));
        this.$('ap-ai').addEventListener('click',      () => this._ai());
        this.$('ap-export').addEventListener('click',  () => this._csv());

        ['ap-search','ap-type-f','ap-orphan-f','ap-sev-f'].forEach(id => {
            const el = this.$(id);
            if (el) el.addEventListener(el.tagName === 'INPUT' ? 'input' : 'change',
                () => { this.page = 1; this._filter(); });
        });

        this.$('ap-pgsize').addEventListener('change', e => {
            this.pageSize = +e.target.value; this.page = 1; this._table();
        });

        document.querySelectorAll('.ap-theme-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.theme = THEMES[btn.dataset.t] || THEMES.ledger;
                this._theme();
                document.querySelectorAll('.ap-theme-btn').forEach(b =>
                    b.classList.toggle('active', b.dataset.t === btn.dataset.t));
            });
        });

        document.querySelectorAll('.ap-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.ap-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                this.activeTab = tab.dataset.tab;
                this.page = 1;
                if (this.activeTab === 'pivot') {
                    this._pivotVisibility(true);
                    this._runPivot();
                } else {
                    this._pivotVisibility(false);
                    this._filter();
                }
            });
        });
    }

    _defaultDates() {
        const now = new Date();
        const pad = n => String(n).padStart(2,'0');
        const fmt = d => `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
        this.$('ap-from').value = fmt(new Date(now.getFullYear(), now.getMonth(), 1));
        this.$('ap-to').value   = fmt(now);
    }

    _theme() {
        const t = this.theme;
        const root = document.getElementById('apar-root');
        if (!root) return;
        const vars = {
            '--bg':t.bg,'--bg2':t.bg2,'--bg3':t.bg3,'--card':t.card,
            '--brd':t.brd,'--brd2':t.brd2,'--tx1':t.tx1,'--tx2':t.tx2,'--tx3':t.tx3,
            '--pri':t.pri,'--pri_d':t.pri_d,'--grn':t.grn,'--red':t.red,'--amb':t.amb,
        };
        Object.assign(root.style, vars);
        const banner = this.$('ap-banner');
        if (banner) banner.style.background = t.banner;
    }

    // ── RUN ──────────────────────────────────────────────────────────────────
    _run(l3Only = false) {
        if (this.running) return;
        const from    = this.$('ap-from').value;
        const to      = this.$('ap-to').value;
        if (!from || !to) {
            frappe.msgprint({title:'Missing Dates', indicator:'orange', message:'Select both From and To dates.'});
            return;
        }
        const company = this.$('ap-company').value.trim() || null;
        const scope   = this.$('ap-scope').value;
        const sev     = this.$('ap-sev').value;
        const party   = this.$('ap-party').value.trim() || null;

        this.running = true;
        ['ap-explainer','ap-l1','ap-kpis','ap-tabs','ap-fbar',
         'ap-table-wrap','ap-empty','ap-ai-panel'].forEach(id => {
            const el = this.$(id);
            if (el) el.style.display = 'none';
        });
        this.$('ap-ai').style.display     = 'none';
        this.$('ap-export').style.display = 'none';
        this.$('ap-health').style.display = 'none';

        const msg = l3Only
            ? 'Running L3 Orphan Scan (VLOOKUP engine)...'
            : 'Running all three levels + secondary checks...';
        this._spin(msg);

        frappe.call({
            method: 'ecclesia.ecclesia.page.ap_ar_check.ap_ar_check.run_check',
            args: {
                from_date:         from,
                to_date:           to,
                company,
                check_scope:       scope,
                run_level1:        true,
                run_level2:        !l3Only,
                run_level3:        true,
                include_secondary: !l3Only,
                include_stock:     !l3Only,
                severity_filter:   sev,
                party_filter:      party,
            },
            callback: r => {
                this.running = false;
                this._unspin();
                if (!r.message) return;
                const d = r.message;
                this.rows    = d.rows    || [];
                this.level1  = d.level1  || {};
                this.summary = d.summary || {};
                this.meta    = d.meta    || {};
                this.aiResult = null;
                this._renderAll();
            },
            error: () => {
                this.running = false;
                this._unspin();
                frappe.msgprint({title:'Check Failed', indicator:'red',
                    message:'An error occurred. Check the Error Log.'});
            },
        });
    }

    _renderAll() {
        this._l1Panel();
        this._kpis();
        this._tabs();
        this._codeFilter();
        this._filter();
        this.$('ap-ai').style.display     = 'inline-flex';
        this.$('ap-export').style.display = 'inline-flex';
        this.$('ap-explainer').style.display = 'none';
    }

    // ── LEVEL 1 PANEL ────────────────────────────────────────────────────────
    _l1Panel() {
        const l1  = this.level1;
        if (!l1 || !Object.keys(l1).length) return;

        const sides = Object.entries(l1).map(([side, d]) => {
            const gl   = d.gl   || {};
            const sl   = d.sl   || {};
            const diff = d.difference || {};
            const clean = diff.is_clean;
            const color = clean ? '#10B981' : '#EF4444';
            const icon  = clean ? '✅' : '🚨';

            return `
<div class="ap-l1-side" style="border-color:${color}40">
    <div class="ap-l1-side-header" style="background:${color}15;color:${color}">
        ${icon} ${side} Control Total — ${clean ? 'BALANCED' : 'IMBALANCE DETECTED'}
    </div>
    <table class="ap-l1-table">
        <thead><tr>
            <th>Metric</th><th>GL Control Account</th><th>Party Subledger</th><th>Variance</th>
        </tr></thead>
        <tbody>
            <tr>
                <td class="ap-l1-metric">Total Debit</td>
                <td class="ap-l1-num">₦${fmt(gl.total_debit)}</td>
                <td class="ap-l1-num">₦${fmt(sl.total_debit)}</td>
                <td class="ap-l1-num ${Math.abs(diff.debit||0)>1?'ap-l1-bad':'ap-l1-ok'}">
                    ${Math.abs(diff.debit||0)>0.01 ? '₦'+fmt(Math.abs(diff.debit)) : '✓'}
                </td>
            </tr>
            <tr>
                <td class="ap-l1-metric">Total Credit</td>
                <td class="ap-l1-num">₦${fmt(gl.total_credit)}</td>
                <td class="ap-l1-num">₦${fmt(sl.total_credit)}</td>
                <td class="ap-l1-num ${Math.abs(diff.credit||0)>1?'ap-l1-bad':'ap-l1-ok'}">
                    ${Math.abs(diff.credit||0)>0.01 ? '₦'+fmt(Math.abs(diff.credit)) : '✓'}
                </td>
            </tr>
            <tr>
                <td class="ap-l1-metric">Voucher Count</td>
                <td class="ap-l1-num">${(gl.voucher_count||0).toLocaleString()}</td>
                <td class="ap-l1-num">${(sl.voucher_count||0).toLocaleString()}</td>
                <td class="ap-l1-num">${((gl.voucher_count||0)-(sl.voucher_count||0)).toLocaleString()}</td>
            </tr>
        </tbody>
    </table>
    ${!clean ? `<div class="ap-l1-warning">
        Net imbalance ₦${fmt(Math.abs(diff.net||0))} — run L3 Orphan Scan to identify the exact vouchers.
    </div>` : ''}
    <div class="ap-l1-accounts">Control accounts: ${(d.accounts||[]).join(', ') || '—'}</div>
</div>`;
        });

        const panel = this.$('ap-l1');
        panel.innerHTML = `
<div class="ap-l1-header">
    <span class="ap-l1-title">⚖️ Level 1 — Control Total Reconciliation</span>
    <span class="ap-l1-sub">Aggregate debit/credit comparison: GL control account vs party-tagged subledger entries</span>
</div>
<div class="ap-l1-sides">${sides.join('')}</div>`;
        panel.style.display = 'block';
    }

    // ── KPI STRIP ────────────────────────────────────────────────────────────
    _kpis() {
        const s = this.summary;
        const m = this.meta || {};
        const t = this.theme;

        const health = s.total === 0 ? 'Clean'
            : s.critical === 0 && s.high < 3 ? 'Good'
            : s.critical < 2 ? 'Fair'
            : s.critical < 5 ? 'Poor' : 'Critical';

        const hColor = {Clean:'#10B981',Good:'#0EA5E9',Fair:'#F59E0B',Poor:'#F97316',Critical:'#EF4444'}[health];
        const hIcon  = {Clean:'✨',Good:'✅',Fair:'🟡',Poor:'🟠',Critical:'🚨'}[health];

        const badge = this.$('ap-health');
        badge.style.cssText = `display:flex;background:${hColor}20;color:${hColor};border:2px solid ${hColor};`;
        badge.innerHTML = `<span style="font-size:18px">${hIcon}</span> ${health}`;

        // Orphan breakdown chips
        const orphanChips = [
            ['GL_ONLY',       s.orphan_gl_only   || 0],
            ['SL_ONLY',       s.orphan_sl_only   || 0],
            ['PARTY_MISSING', s.orphan_missing   || 0],
            ['MISMATCH',      s.orphan_mismatch  || 0],
        ].map(([k,n]) => {
            const o = ORPHAN[k];
            return `<div class="ap-orphan-chip" style="background:${o.bg};border-color:${o.color}40" title="${o.tip}">
                <span>${o.icon}</span>
                <span style="font-weight:800;color:${o.color}">${n}</span>
                <span style="font-size:10px;color:${o.color}">${o.label}</span>
            </div>`;
        }).join('');

        const kpis = [
            {label:'Total Issues',    val:s.total,                color:s.total===0?t.grn:t.red,  icon:'🔍', sub:`${m.duration_ms||0}ms`},
            {label:'🚨 Critical',     val:s.critical,             color:'#EF4444',                 icon:'🚨', sub:`High: ${s.high}`},
            {label:'L3 Orphan Issues',val:s.l3_count||0,          color:'#EF4444',                 icon:'🔍', sub:`Impact: ${abbr(s.l3_impact||0)}`},
            {label:'L2 Party Gaps',   val:s.l2_count||0,          color:'#F59E0B',                 icon:'👤', sub:'Customer/Supplier'},
            {label:'📤 AR',           val:s.ar_count||0,          color:'#0EA5E9',                 icon:'📤', sub:`${abbr(s.ar_impact||0)}`},
            {label:'📥 AP',           val:s.ap_count||0,          color:'#8B5CF6',                 icon:'📥', sub:`${abbr(s.ap_impact||0)}`},
            {label:'💰 Total Impact', val:abbr(s.total_impact||0),color:t.amb,                     icon:'💎', sub:'Financial exposure', str:true},
        ];

        const kpiHtml = kpis.map(k => `
<div class="ap-kpi" style="border-top:3px solid ${k.color}">
    <div class="ap-kpi-icon" style="color:${k.color}">${k.icon}</div>
    <div class="ap-kpi-val" style="color:${k.color}">${k.str ? k.val : (+(k.val||0)).toLocaleString()}</div>
    <div class="ap-kpi-lbl">${k.label}</div>
    <div class="ap-kpi-sub">${k.sub}</div>
</div>`).join('');

        const kpiEl = this.$('ap-kpis');
        kpiEl.innerHTML = `
<div class="ap-kpi-row">${kpiHtml}</div>
<div class="ap-orphan-strip">
    <span class="ap-orphan-strip-label">L3 Orphan Breakdown:</span>
    ${orphanChips}
</div>`;
        kpiEl.style.display = 'block';
    }

    // ── TABS ─────────────────────────────────────────────────────────────────
    _tabs() {
        const s = this.summary;
        this.$('ap-tab-l3-count').textContent  = s.l3_count  || 0;
        this.$('ap-tab-l2-count').textContent  = s.l2_count  || 0;
        this.$('ap-tab-sec-count').textContent = s.sec_count || 0;
        this.$('ap-tab-all-count').textContent = s.total     || 0;
        this.$('ap-tabs').style.display = 'flex';
    }

    // ── PIVOT TAB VISIBILITY TOGGLE ──────────────────────────────────────────
    _pivotVisibility(show) {
        const panel  = this.$('ap-pivot-panel');
        const fbar   = this.$('ap-fbar');
        const tWrap  = this.$('ap-table-wrap');
        const empty  = this.$('ap-empty');
        if (show) {
            if (panel)  panel.style.display  = 'block';
            if (fbar)   fbar.style.display   = 'none';
            if (tWrap)  tWrap.style.display  = 'none';
            if (empty)  empty.style.display  = 'none';
        } else {
            if (panel)  panel.style.display  = 'none';
        }
    }

    _codeFilter() {
        // no code filter select in new design — orphan filter replaces it
    }

    // ── FILTER & SORT ────────────────────────────────────────────────────────
    _filter() {
        // hide pivot panel if we're on a non-pivot tab
        this._pivotVisibility(false);
        const q       = (this.$('ap-search')?.value  || '').toLowerCase();
        const typeF   = this.$('ap-type-f')?.value   || '';
        const orphanF = this.$('ap-orphan-f')?.value || '';
        const sevF    = this.$('ap-sev-f')?.value    || '';

        let base = this.rows;

        // Tab filter
        if (this.activeTab === 'orphan')    base = base.filter(r => r.check_level === 'L3');
        if (this.activeTab === 'party')     base = base.filter(r => r.check_level === 'L2');
        if (this.activeTab === 'secondary') base = base.filter(r => r.check_level === 'SEC');

        this.filtered = base.filter(r => {
            if (typeF   && r.check_type  !== typeF)   return false;
            if (orphanF && r.orphan_side !== orphanF)  return false;
            if (sevF    && r.severity    !== sevF)     return false;
            if (q) {
                const blob = `${r.description} ${r.document} ${r.party} ${r.check_name} ${r.check_code} ${r.orphan_side}`.toLowerCase();
                if (!blob.includes(q)) return false;
            }
            return true;
        });

        // Sort
        const SEV_ORD = {Critical:1,High:2,Medium:3,Low:4};
        this.filtered.sort((a,b) => {
            let av = a[this.sortCol], bv = b[this.sortCol];
            if (this.sortCol === 'severity') { av = SEV_ORD[av]||9; bv = SEV_ORD[bv]||9; }
            if (typeof av === 'string') { av = av.toLowerCase(); bv = (bv||'').toLowerCase(); }
            return this.sortAsc ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1);
        });

        this.$('ap-count').textContent =
            `${this.filtered.length.toLocaleString()} result${this.filtered.length !== 1 ? 's' : ''}`;
        this.$('ap-fbar').style.display = 'flex';
        this._table();
    }

    // ── TABLE ────────────────────────────────────────────────────────────────
    _table() {
        const total = this.filtered.length;
        const pages = Math.ceil(total / this.pageSize) || 1;
        this.page   = Math.min(this.page, pages);
        const start = (this.page - 1) * this.pageSize;
        const slice = this.filtered.slice(start, start + this.pageSize);

        if (total === 0) {
            this.$('ap-table-wrap').style.display = 'none';
            this.$('ap-empty').style.display = this.rows.length > 0 ? 'none' : 'flex';
            if (this.rows.length > 0) {
                this.$('ap-empty').style.display = 'flex';
                this.$('ap-empty').querySelector('.ap-empty-title').textContent = 'No matches';
                this.$('ap-empty').querySelector('.ap-empty-sub').textContent = 'Try adjusting your filters.';
            }
            return;
        }

        this.$('ap-empty').style.display      = 'none';
        this.$('ap-table-wrap').style.display = 'block';

        // Columns — L3 Orphan view shows GL/SL debit/credit columns; others simpler
        const isOrphanTab = this.activeTab === 'orphan';

        const cols = [
            {key:'row_number',   label:'#',          w:'44px'},
            {key:'check_code',   label:'Check',       w:'130px'},
            {key:'orphan_side',  label:'Class',       w:'120px'},
            {key:'severity',     label:'Severity',    w:'90px'},
            {key:'document',     label:'Voucher',     w:'150px'},
            {key:'party',        label:'Party',       w:'160px'},
            {key:'posting_date', label:'Date',        w:'100px'},
            ...(isOrphanTab ? [
                {key:'gl_debit',  label:'GL Dr (₦)',  w:'120px'},
                {key:'gl_credit', label:'GL Cr (₦)',  w:'120px'},
                {key:'sl_debit',  label:'SL Dr (₦)',  w:'120px'},
                {key:'sl_credit', label:'SL Cr (₦)',  w:'120px'},
            ] : []),
            {key:'description',  label:'Description', w:'auto'},
            {key:'impact_amount',label:'Impact (₦)',  w:'120px'},
        ];

        const thead = cols.map(c => {
            const arrow = this.sortCol === c.key ? (this.sortAsc ? ' ▲' : ' ▼') : '';
            return `<th class="ap-th" data-col="${c.key}" style="width:${c.w};min-width:${c.w}">${c.label}${arrow}</th>`;
        }).join('');

        const tbody = slice.map(r => {
            const sev     = SEV[r.severity]   || SEV.Medium;
            const typ     = TYPE[r.check_type] || TYPE.AR;
            const orphan  = ORPHAN[r.orphan_side] || {};
            const lvl     = LEVEL[r.check_level]  || LEVEL.SEC;
            const impact  = flt(r.impact_amount);
            const glDr    = flt(r.gl_debit);
            const glCr    = flt(r.gl_credit);
            const slDr    = flt(r.sl_debit);
            const slCr    = flt(r.sl_credit);

            const orphanBadge = orphan.icon
                ? `<span class="ap-orphan-badge" style="color:${orphan.color};background:${orphan.bg}" title="${esc(orphan.tip||'')}">${orphan.icon} ${orphan.label}</span>`
                : `<span class="ap-orphan-badge" style="color:#6B7280;background:#F3F4F6">${lvl.icon} ${lvl.label}</span>`;

            const glDrCell  = `<td class="ap-td ap-td-num ${glDr > 0 && slDr === 0 ? 'ap-cell-gl-only' : glDr !== slDr && slDr > 0 ? 'ap-cell-mismatch' : ''}">₦${glDr > 0 ? fmt(glDr) : '—'}</td>`;
            const glCrCell  = `<td class="ap-td ap-td-num ${glCr > 0 && slCr === 0 ? 'ap-cell-gl-only' : ''}">₦${glCr > 0 ? fmt(glCr) : '—'}</td>`;
            const slDrCell  = `<td class="ap-td ap-td-num ${slDr > 0 && glDr === 0 ? 'ap-cell-sl-only' : slDr !== glDr && glDr > 0 ? 'ap-cell-mismatch' : ''}">₦${slDr > 0 ? fmt(slDr) : '—'}</td>`;
            const slCrCell  = `<td class="ap-td ap-td-num ${slCr > 0 && glCr === 0 ? 'ap-cell-sl-only' : ''}">₦${slCr > 0 ? fmt(slCr) : '—'}</td>`;

            return `
<tr class="ap-tr" data-rn="${r.row_number}" title="${esc(r.recommendation)}">
    <td class="ap-td ap-td-n">${r.row_number}</td>
    <td class="ap-td">
        <span class="ap-code" style="color:${typ.color};background:${typ.bg}">${typ.icon} ${esc(r.check_code)}</span>
    </td>
    <td class="ap-td">${orphanBadge}</td>
    <td class="ap-td">
        <span class="ap-sev-badge" style="color:${sev.color};background:${sev.bg}">${sev.icon} ${r.severity}</span>
    </td>
    <td class="ap-td">
        <a href="#" onclick="frappe.set_route('Form','${esc(r.document_type)}','${esc(r.document)}');return false;" class="ap-link">${esc(r.document)}</a>
        <div style="font-size:10px;color:#6B7280">${esc(r.document_type)}</div>
    </td>
    <td class="ap-td ap-td-party">${esc(r.party || '—')}</td>
    <td class="ap-td ap-td-date">${r.posting_date || '—'}</td>
    ${isOrphanTab ? glDrCell + glCrCell + slDrCell + slCrCell : ''}
    <td class="ap-td ap-td-desc" title="${esc(r.description)}">${esc(r.description)}</td>
    <td class="ap-td ap-td-num" style="color:${impact>0?'#EF4444':'inherit'};font-weight:${impact>0?700:400}">
        ${impact > 0 ? '₦'+fmt(impact) : '—'}
    </td>
</tr>
<tr class="ap-tr-exp" id="ap-exp-${r.row_number}" style="display:none">
    <td colspan="${cols.length}" class="ap-td-exp">
        <div class="ap-exp-box">
            <div class="ap-exp-head">
                <span>💡 Recommendation</span>
                ${orphan.icon ? `<span class="ap-exp-class" style="color:${orphan.color}">${orphan.icon} ${orphan.label}: ${orphan.tip||''}</span>` : ''}
            </div>
            <div class="ap-exp-rec">${esc(r.recommendation)}</div>
            ${isOrphanTab ? `
            <div class="ap-exp-amounts">
                <div class="ap-exp-side" style="border-color:#0EA5E940">
                    <div class="ap-exp-side-label" style="color:#0EA5E9">GL Control Account</div>
                    <div>Dr: <strong>₦${fmt(glDr)}</strong> &nbsp; Cr: <strong>₦${fmt(glCr)}</strong></div>
                </div>
                <div class="ap-exp-vs">vs</div>
                <div class="ap-exp-side" style="border-color:#8B5CF640">
                    <div class="ap-exp-side-label" style="color:#8B5CF6">${r.party_type} Subledger</div>
                    <div>Dr: <strong>₦${fmt(slDr)}</strong> &nbsp; Cr: <strong>₦${fmt(slCr)}</strong></div>
                </div>
                <div class="ap-exp-vs">⟹</div>
                <div class="ap-exp-side" style="border-color:#EF444440">
                    <div class="ap-exp-side-label" style="color:#EF4444">Variance</div>
                    <div>Dr: <strong>₦${fmt(Math.abs(glDr-slDr))}</strong> &nbsp; Cr: <strong>₦${fmt(Math.abs(glCr-slCr))}</strong></div>
                </div>
            </div>` : ''}
            <div class="ap-exp-meta">
                Check: <strong>${esc(r.check_name)}</strong> &nbsp;|&nbsp;
                Party Type: <strong>${esc(r.party_type)}</strong> &nbsp;|&nbsp;
                Level: <strong>${r.check_level}</strong>
            </div>
        </div>
    </td>
</tr>`;
        }).join('');

        this.$('ap-thead').innerHTML = `<tr>${thead}</tr>`;
        this.$('ap-tbody').innerHTML = tbody;

        // Sort clicks
        this.$('ap-thead').querySelectorAll('.ap-th').forEach(th => {
            th.addEventListener('click', () => {
                if (this.sortCol === th.dataset.col) this.sortAsc = !this.sortAsc;
                else { this.sortCol = th.dataset.col; this.sortAsc = true; }
                this._filter();
            });
        });

        // Row expand
        this.$('ap-tbody').querySelectorAll('.ap-tr').forEach(tr => {
            tr.addEventListener('click', e => {
                if (e.target.tagName === 'A') return;
                const exp = document.getElementById(`ap-exp-${tr.dataset.rn}`);
                if (exp) exp.style.display = exp.style.display === 'none' ? 'table-row' : 'none';
            });
        });

        this._paging(pages);
    }

    _paging(pages) {
        if (pages <= 1) { this.$('ap-paging').innerHTML = ''; return; }
        const cp = this.page;
        let html = '';
        const btn = (p, label, disabled=false, active=false) =>
            `<button class="ap-pg${disabled?' ap-pg-dis':''}${active?' ap-pg-act':''}" data-p="${p}">${label}</button>`;

        html += btn(1,'«',cp===1) + btn(cp-1,'‹',cp===1);
        for (let p=Math.max(1,cp-2); p<=Math.min(pages,cp+2); p++)
            html += btn(p, p, false, p===cp);
        html += btn(cp+1,'›',cp===pages) + btn(pages,'»',cp===pages);
        html += `<span class="ap-pg-info">Page ${cp} of ${pages} · ${this.filtered.length.toLocaleString()} records</span>`;

        const pag = this.$('ap-paging');
        pag.innerHTML = html;
        pag.querySelectorAll('.ap-pg:not(.ap-pg-dis)').forEach(b =>
            b.addEventListener('click', () => {
                const p = +b.dataset.p;
                if (p>=1 && p<=pages) { this.page = p; this._table(); }
            })
        );
    }

    // ── AI ───────────────────────────────────────────────────────────────────
    _ai() {
        const btn = this.$('ap-ai');
        btn.disabled = true;
        btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Analysing...';
        this._spin('AI is analysing your reconciliation results...');

        frappe.call({
            method: 'ecclesia.ecclesia.page.ap_ar_check.ap_ar_check.run_ai_analysis',
            args: {
                check_results_json: JSON.stringify({rows:this.rows, summary:this.summary, level1:this.level1}),
                company:    this.$('ap-company').value.trim() || null,
                from_date:  this.$('ap-from').value,
                to_date:    this.$('ap-to').value,
            },
            callback: r => {
                btn.disabled = false;
                btn.innerHTML = '<i class="fa fa-robot"></i> AI Analysis';
                this._unspin();
                if (r.message) { this.aiResult = r.message; this._aiPanel(r.message); }
            },
            error: () => {
                btn.disabled = false;
                btn.innerHTML = '<i class="fa fa-robot"></i> AI Analysis';
                this._unspin();
                frappe.msgprint({title:'AI Error', indicator:'red', message:'AI analysis failed.'});
            },
        });
    }

    _aiPanel(d) {
        const health = d.overall_health || 'Fair';
        const score  = d.health_score   || 50;
        const hColor = {Clean:'#10B981',Good:'#0EA5E9',Fair:'#F59E0B',Poor:'#F97316',Critical:'#EF4444'}[health]||'#F59E0B';
        const hIcon  = {Clean:'✨',Good:'✅',Fair:'🟡',Poor:'🟠',Critical:'🚨'}[health]||'🟡';
        const src    = d.source === 'claude-ai' ? '🧠 Claude AI' : '📊 Rule Engine';

        const panel = this.$('ap-ai-panel');
        panel.innerHTML = `
<div class="ap-ai-hdr" style="border-color:${hColor}40;background:${hColor}08">
    <div class="ap-ai-src">${src}</div>
    <div class="ap-ai-verdict">
        <span style="font-size:36px">${hIcon}</span>
        <div>
            <div style="font-size:22px;font-weight:800;color:${hColor}">${health}</div>
            <div style="font-size:12px;color:var(--tx3)">${score}/100 Health Score</div>
        </div>
        <div class="ap-ai-exec">${esc(d.executive_summary||'')}</div>
    </div>
</div>
<div class="ap-ai-body">
    <div class="ap-ai-col">
        <div class="ap-ai-sec"><div class="ap-ai-sec-t">📤 AR</div><div class="ap-ai-text">${esc(d.ar_assessment||'—')}</div></div>
        <div class="ap-ai-sec"><div class="ap-ai-sec-t">📥 AP</div><div class="ap-ai-text">${esc(d.ap_assessment||'—')}</div></div>
        <div class="ap-ai-sec">
            <div class="ap-ai-sec-t">🚨 Top Risks</div>
            ${(d.top_risks||[]).map(r=>`
            <div class="ap-ai-risk">
                <div style="font-weight:700">${esc(r.risk)}</div>
                <div style="font-size:11px;color:var(--tx3)">${esc(r.impact)}</div>
            </div>`).join('')||'<div class="ap-ai-text">No critical risks</div>'}
        </div>
    </div>
    <div class="ap-ai-col">
        <div class="ap-ai-sec">
            <div class="ap-ai-sec-t">📋 Action Plan</div>
            ${(d.action_plan||[]).map(a=>`
            <div class="ap-ai-action">
                <div style="font-weight:700">${a.priority}. ${esc(a.action)}</div>
                <div style="font-size:11px;color:var(--tx3)">👤 ${esc(a.owner||'—')} &nbsp;|&nbsp; 📅 ${esc(a.deadline||'—')}</div>
            </div>`).join('')||'<div class="ap-ai-text">No immediate actions</div>'}
        </div>
        ${(d.process_improvements||[]).length?`
        <div class="ap-ai-sec">
            <div class="ap-ai-sec-t">⚙️ Process Improvements</div>
            ${d.process_improvements.map(i=>`<div class="ap-ai-text" style="padding:4px 0;border-bottom:1px solid var(--brd)">• ${esc(i)}</div>`).join('')}
        </div>`:''}
        ${(d.compliance_flags||[]).length?`
        <div class="ap-ai-sec">
            <div class="ap-ai-sec-t" style="color:#EF4444">⚑ Compliance Flags</div>
            ${d.compliance_flags.map(f=>`<div style="color:#EF4444;font-size:12px;padding:4px 0">• ${esc(f)}</div>`).join('')}
        </div>`:''}
    </div>
</div>`;
        panel.style.display = 'block';
        panel.scrollIntoView({behavior:'smooth',block:'start'});
    }

    // ═════════════════════════════════════════════════════════════════════════
    //  PIVOT RECONCILIATION TAB
    // ═════════════════════════════════════════════════════════════════════════

    _runPivot(forceReload = false) {
        const panel = this.$('ap-pivot-panel');
        if (!panel) return;

        // If we already have pivot data and filters haven't changed, just re-render
        if (this._pivotData && !forceReload) {
            this._renderPivot(this._pivotData);
            return;
        }

        const from    = this.$('ap-from').value;
        const to      = this.$('ap-to').value;
        const company = this.$('ap-company').value.trim() || null;
        const party   = this.$('ap-party').value.trim() || null;
        const scope   = this.$('ap-scope').value;

        // Map scope selector to pivot scope param
        const pivotScope = scope === 'AR Only' ? 'AR' : scope === 'AP Only' ? 'AP' : 'All';

        panel.innerHTML = `
<div class="ap-pivot-loading">
    <div class="ap-spinner" style="width:28px;height:28px;border-width:3px"></div>
    <div style="font-size:13px;color:var(--tx2)">Building reconciliation pivot…</div>
</div>`;

        frappe.call({
            method: 'ecclesia.ecclesia.page.ap_ar_check.ap_ar_check.run_pivot_reconciliation',
            args: {
                from_date:         from,
                to_date:           to,
                company:           company,
                scope:             pivotScope,
                party_filter:      party,
                show_clean:        this._pivotShowClean ? '1' : '0',
                include_drilldown: '1',
            },
            callback: r => {
                if (!r.message) return;
                this._pivotData = r.message;
                // Update tab badge with problem count
                const s   = r.message.summary || {};
                const tot = (s.ar_problem_count||0) + (s.ap_problem_count||0) + (s.stk_problem_count||0);
                const badge = this.$('ap-tab-pivot-count');
                if (badge) {
                    badge.textContent = tot > 0 ? tot : '✓';
                    badge.style.background = tot > 0 ? '#EF4444' : '#10B981';
                    badge.style.color = '#fff';
                }
                this._renderPivot(r.message);
            },
            error: () => {
                panel.innerHTML = `<div class="ap-pivot-err">⚠️ Pivot failed — check Error Log.</div>`;
            },
        });
    }

    _renderPivot(data) {
        const panel = this.$('ap-pivot-panel');
        if (!panel) return;

        const s   = data.summary || {};
        const ar  = data.ar_rows  || [];
        const ap  = data.ap_rows  || [];
        const stk = data.stock_rows || [];

        const totalProblems = (s.ar_problem_count||0) + (s.ap_problem_count||0) + (s.stk_problem_count||0);
        const allClean = totalProblems === 0;

        // ── Summary totals bar
        const summaryBar = `
<div class="ap-pv-summary-bar">
    <div class="ap-pv-sum-chip" style="border-color:#0EA5E940">
        <div class="ap-pv-sum-label">📤 AR</div>
        <div class="ap-pv-sum-row"><span>GL Total</span><strong>₦${fmt(s.ar_total_gl||0)}</strong></div>
        <div class="ap-pv-sum-row"><span>SL Total</span><strong>₦${fmt(s.ar_total_sl||0)}</strong></div>
        <div class="ap-pv-sum-row ap-pv-sum-var" style="color:${Math.abs(s.ar_variance||0)>1?'#EF4444':'#10B981'}">
            <span>Variance</span><strong>${Math.abs(s.ar_variance||0)>1 ? '₦'+fmt(Math.abs(s.ar_variance||0)) : '✓ Balanced'}</strong>
        </div>
        <div class="ap-pv-sum-row"><span>Affected</span><strong>${s.ar_problem_count||0} / ${s.ar_party_count||0} customers</strong></div>
    </div>
    <div class="ap-pv-sum-chip" style="border-color:#8B5CF640">
        <div class="ap-pv-sum-label">📥 AP</div>
        <div class="ap-pv-sum-row"><span>GL Total</span><strong>₦${fmt(s.ap_total_gl||0)}</strong></div>
        <div class="ap-pv-sum-row"><span>SL Total</span><strong>₦${fmt(s.ap_total_sl||0)}</strong></div>
        <div class="ap-pv-sum-row ap-pv-sum-var" style="color:${Math.abs(s.ap_variance||0)>1?'#EF4444':'#10B981'}">
            <span>Variance</span><strong>${Math.abs(s.ap_variance||0)>1 ? '₦'+fmt(Math.abs(s.ap_variance||0)) : '✓ Balanced'}</strong>
        </div>
        <div class="ap-pv-sum-row"><span>Affected</span><strong>${s.ap_problem_count||0} / ${s.ap_party_count||0} suppliers</strong></div>
    </div>
    <div class="ap-pv-sum-chip" style="border-color:#10B98140">
        <div class="ap-pv-sum-label">📦 Stock</div>
        <div class="ap-pv-sum-row"><span>SLE Value</span><strong>₦${fmt(s.stk_total_gl||0)}</strong></div>
        <div class="ap-pv-sum-row"><span>Bin Value</span><strong>₦${fmt(s.stk_total_sl||0)}</strong></div>
        <div class="ap-pv-sum-row ap-pv-sum-var" style="color:${Math.abs(s.stk_variance||0)>1?'#EF4444':'#10B981'}">
            <span>Variance</span><strong>${Math.abs(s.stk_variance||0)>1 ? '₦'+fmt(Math.abs(s.stk_variance||0)) : '✓ Balanced'}</strong>
        </div>
        <div class="ap-pv-sum-row"><span>Affected</span><strong>${s.stk_problem_count||0} / ${s.stk_item_count||0} items</strong></div>
    </div>
    <div class="ap-pv-sum-total" style="background:${allClean?'#10B98115':'#EF444415'};border-color:${allClean?'#10B981':'#EF4444'}40">
        <div style="font-size:32px">${allClean?'✅':'🚨'}</div>
        <div style="font-size:20px;font-weight:800;color:${allClean?'#10B981':'#EF4444'}">${allClean?'All Clean':totalProblems+' Issues'}</div>
        <div style="font-size:11px;color:var(--tx3)">across AR · AP · Stock</div>
    </div>
</div>`;

        // ── Pivot controls
        const controls = `
<div class="ap-pv-controls">
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
        <label class="ap-pv-toggle">
            <input type="checkbox" id="ap-pv-show-clean" ${this._pivotShowClean?'checked':''} />
            Show clean (zero variance) rows
        </label>
        <input type="text" id="ap-pv-search" class="ap-input" placeholder="🔍 Filter by party name…" style="width:240px" value="${this._pivotSearch||''}" />
        <button class="ap-btn ap-btn-ghost" id="ap-pv-refresh" style="padding:7px 14px">
            <i class="fa fa-refresh"></i> Refresh
        </button>
        <button class="ap-btn ap-btn-ghost" id="ap-pv-export" style="padding:7px 14px">
            <i class="fa fa-download"></i> Export Pivot CSV
        </button>
    </div>
    <div class="ap-pv-legend">
        <span class="ap-pv-leg-chip" style="background:#EF444415;border-color:#EF444440;color:#EF4444">🚨 Critical (&gt;₦100k)</span>
        <span class="ap-pv-leg-chip" style="background:#F59E0B15;border-color:#F59E0B40;color:#D97706">⚠️ Warning (&gt;₦10k)</span>
        <span class="ap-pv-leg-chip" style="background:#3B82F615;border-color:#3B82F640;color:#2563EB">🔵 Minor (&lt;₦10k)</span>
        <span class="ap-pv-leg-chip" style="background:#10B98115;border-color:#10B98140;color:#10B981">✅ Clean</span>
    </div>
</div>`;

        const arSection  = this._renderPivotSection('AR',    ar,  '📤', '#0EA5E9', data);
        const apSection  = this._renderPivotSection('AP',    ap,  '📥', '#8B5CF6', data);
        const stkSection = this._renderPivotSection('Stock', stk, '📦', '#10B981', data);

        panel.innerHTML = `
<div class="ap-pv-root">
    <div class="ap-pv-header">
        <div class="ap-pv-title">📊 Subledger Reconciliation Pivot</div>
        <div class="ap-pv-subtitle">
            Party-level VLOOKUP: GL Control Account balance vs Subledger balance, per customer · supplier · item/warehouse.
            Click any row to see voucher-level drilldown.
        </div>
    </div>
    ${summaryBar}
    ${controls}
    <div id="ap-pv-sections">
        ${arSection}
        ${apSection}
        ${stkSection}
    </div>
</div>`;

        // Bind controls
        const showCleanCb = document.getElementById('ap-pv-show-clean');
        if (showCleanCb) showCleanCb.addEventListener('change', e => {
            this._pivotShowClean = e.target.checked;
            this._pivotData = null;
            this._runPivot(true);
        });

        const pvSearch = document.getElementById('ap-pv-search');
        if (pvSearch) pvSearch.addEventListener('input', e => {
            this._pivotSearch = e.target.value.toLowerCase();
            this._filterPivotRows();
        });

        const pvRefresh = document.getElementById('ap-pv-refresh');
        if (pvRefresh) pvRefresh.addEventListener('click', () => {
            this._pivotData = null;
            this._runPivot(true);
        });

        const pvExport = document.getElementById('ap-pv-export');
        if (pvExport) pvExport.addEventListener('click', () => this._exportPivotCSV(data));

        // Bind row expand (drilldown)
        document.querySelectorAll('.ap-pv-party-row').forEach(row => {
            row.addEventListener('click', () => {
                const key    = row.dataset.key;
                const detail = document.getElementById(`ap-pv-drill-${key}`);
                if (!detail) return;
                const isOpen = detail.style.display !== 'none';
                detail.style.display = isOpen ? 'none' : 'table-row';
                row.querySelector('.ap-pv-expand-icon').textContent = isOpen ? '▶' : '▼';
            });
        });

        // Apply search filter if already set
        if (this._pivotSearch) this._filterPivotRows();
    }

    _renderPivotSection(section, rows, icon, color, data) {
        if (!rows || rows.length === 0) {
            return `
<div class="ap-pv-section" style="border-color:${color}30">
    <div class="ap-pv-sec-header" style="border-color:${color}40">
        <span style="color:${color}">${icon} ${section}</span>
        <span class="ap-pv-sec-count" style="background:${color}20;color:${color}">No variance rows</span>
    </div>
</div>`;
        }

        const isStock   = section === 'Stock';
        const problems  = rows.filter(r => r.status !== 'Clean');
        const totalVar  = rows.reduce((s, r) => s + Math.abs(flt(r.abs_variance)), 0);

        // Column headers
        const colsHtml = isStock ? `
<th class="ap-pv-th">Item / Warehouse</th>
<th class="ap-pv-th">Code</th>
<th class="ap-pv-th ap-pv-th-r">SLE Value (₦)</th>
<th class="ap-pv-th ap-pv-th-r">Bin Value (₦)</th>
<th class="ap-pv-th ap-pv-th-r">Value Variance (₦)</th>
<th class="ap-pv-th ap-pv-th-r">Qty Variance</th>
<th class="ap-pv-th ap-pv-th-r">Var %</th>
<th class="ap-pv-th">Status</th>
<th class="ap-pv-th">Vouchers</th>
<th class="ap-pv-th">Latest Date</th>
<th class="ap-pv-th" style="width:30px"></th>` : `
<th class="ap-pv-th">${section === 'AR' ? 'Customer' : 'Supplier'}</th>
<th class="ap-pv-th">Code</th>
<th class="ap-pv-th ap-pv-th-r">GL Balance (₦)</th>
<th class="ap-pv-th ap-pv-th-r">SL Outstanding (₦)</th>
<th class="ap-pv-th ap-pv-th-r">Unallocated (₦)</th>
<th class="ap-pv-th ap-pv-th-r">SL Net Balance (₦)</th>
<th class="ap-pv-th ap-pv-th-r">Variance (₦)</th>
<th class="ap-pv-th ap-pv-th-r">Var %</th>
<th class="ap-pv-th">Status</th>
<th class="ap-pv-th">Vouchers</th>
<th class="ap-pv-th">Date Range</th>
<th class="ap-pv-th" style="width:30px"></th>`;

        // Data rows
        const rowsHtml = rows.map((r, idx) => {
            const key        = `${section}-${idx}`;
            const absVar     = flt(r.abs_variance);
            const varPct     = flt(r.variance_pct);
            const status     = r.status || 'Clean';
            const statusConf = {
                Critical: {color:'#EF4444', bg:'#FEF2F2', icon:'🚨'},
                Warning:  {color:'#F59E0B', bg:'#FFFBEB', icon:'⚠️'},
                Minor:    {color:'#3B82F6', bg:'#EFF6FF', icon:'🔵'},
                Clean:    {color:'#10B981', bg:'#ECFDF5', icon:'✅'},
            }[status] || {color:'#6B7280', bg:'#F9FAFB', icon:'—'};

            const varCell = absVar < 1
                ? `<td class="ap-pv-td ap-pv-td-r" style="color:#10B981;font-weight:700">✓</td>`
                : `<td class="ap-pv-td ap-pv-td-r ap-pv-var-cell" style="color:${statusConf.color};font-weight:700">
                    ₦${fmt(absVar)}${flt(r.variance) < 0 ? ' <span title="SL exceeds GL" style="font-size:10px">(SL&gt;GL)</span>' : ' <span title="GL exceeds SL" style="font-size:10px">(GL&gt;SL)</span>'}
                   </td>`;

            const dataRow = isStock ? `
<tr class="ap-pv-party-row" data-key="${key}" data-section="${section}" style="background:${statusConf.bg}08">
    <td class="ap-pv-td ap-pv-td-party">
        <span class="ap-pv-expand-icon" style="color:${color};margin-right:6px">▶</span>
        <span style="font-weight:700">${esc(r.item_code||'')}</span>
        <div style="font-size:10px;color:var(--tx3)">${esc(r.warehouse||'')}</div>
    </td>
    <td class="ap-pv-td"><span class="ap-code" style="color:${color};background:${color}15">${esc(r.check_code)}</span></td>
    <td class="ap-pv-td ap-pv-td-r" style="font-weight:600">₦${fmt(r.gl_balance||0)}</td>
    <td class="ap-pv-td ap-pv-td-r" style="font-weight:600">₦${fmt(r.sl_balance||0)}</td>
    ${varCell}
    <td class="ap-pv-td ap-pv-td-r" style="color:${Math.abs(flt(r.qty_variance))>0.001?'#EF4444':'#10B981'};font-weight:600">
        ${Math.abs(flt(r.qty_variance))>0.001 ? flt(r.qty_variance).toFixed(3) : '✓'}
    </td>
    <td class="ap-pv-td ap-pv-td-r" style="color:${varPct>0?statusConf.color:'#10B981'}">${varPct > 0 ? varPct.toFixed(1)+'%' : '—'}</td>
    <td class="ap-pv-td">
        <span class="ap-sev-badge" style="color:${statusConf.color};background:${statusConf.bg}">${statusConf.icon} ${status}</span>
    </td>
    <td class="ap-pv-td ap-pv-td-r">${(r.voucher_count||0).toLocaleString()}</td>
    <td class="ap-pv-td" style="font-size:11px;color:var(--tx3)">${r.latest_date||'—'}</td>
    <td class="ap-pv-td" style="text-align:center;color:var(--tx3);font-size:11px">▶</td>
</tr>` : `
<tr class="ap-pv-party-row" data-key="${key}" data-section="${section}" style="background:${statusConf.bg}08">
    <td class="ap-pv-td ap-pv-td-party">
        <span class="ap-pv-expand-icon" style="color:${color};margin-right:6px">▶</span>
        <a href="#" onclick="frappe.set_route('Form','${section==='AR'?'Customer':'Supplier'}','${esc(r.party)}');return false;" class="ap-link">${esc(r.party)}</a>
    </td>
    <td class="ap-pv-td"><span class="ap-code" style="color:${color};background:${color}15">${esc(r.check_code)}</span></td>
    <td class="ap-pv-td ap-pv-td-r" style="font-weight:600">₦${fmt(r.gl_balance||0)}</td>
    <td class="ap-pv-td ap-pv-td-r">₦${fmt(r.sl_outstanding||0)}</td>
    <td class="ap-pv-td ap-pv-td-r" style="color:${flt(r.sl_unallocated)>0?'#F59E0B':'inherit'}">
        ${flt(r.sl_unallocated)>0 ? '₦'+fmt(r.sl_unallocated) : '—'}
    </td>
    <td class="ap-pv-td ap-pv-td-r" style="font-weight:600">₦${fmt(r.sl_balance||0)}</td>
    ${varCell}
    <td class="ap-pv-td ap-pv-td-r" style="color:${varPct>0?statusConf.color:'#10B981'}">${varPct > 0 ? varPct.toFixed(1)+'%' : '—'}</td>
    <td class="ap-pv-td">
        <span class="ap-sev-badge" style="color:${statusConf.color};background:${statusConf.bg}">${statusConf.icon} ${status}</span>
    </td>
    <td class="ap-pv-td ap-pv-td-r">${(r.voucher_count||0).toLocaleString()}</td>
    <td class="ap-pv-td" style="font-size:11px;color:var(--tx3)">${r.earliest_date||'—'} → ${r.latest_date||'—'}</td>
    <td class="ap-pv-td" style="text-align:center;color:var(--tx3);font-size:11px">▶</td>
</tr>`;

            // Drilldown row (hidden, expands on click)
            const drillHtml = this._renderDrilldown(key, r, section, color);

            return dataRow + drillHtml;
        }).join('');

        // Totals footer row
        const totalGl  = rows.reduce((s,r) => s + flt(r.gl_balance), 0);
        const totalSl  = rows.reduce((s,r) => s + flt(r.sl_balance), 0);
        const totalVar2 = totalGl - totalSl;

        const footerHtml = isStock ? `
<tr class="ap-pv-footer">
    <td class="ap-pv-td" colspan="2" style="font-weight:800;color:${color}">TOTAL (${rows.length} items)</td>
    <td class="ap-pv-td ap-pv-td-r" style="font-weight:800">₦${fmt(totalGl)}</td>
    <td class="ap-pv-td ap-pv-td-r" style="font-weight:800">₦${fmt(totalSl)}</td>
    <td class="ap-pv-td ap-pv-td-r" style="font-weight:800;color:${Math.abs(totalVar2)>1?'#EF4444':'#10B981'}">
        ${Math.abs(totalVar2)>1 ? '₦'+fmt(Math.abs(totalVar2)) : '✓'}
    </td>
    <td colspan="5" class="ap-pv-td"></td>
</tr>` : `
<tr class="ap-pv-footer">
    <td class="ap-pv-td" colspan="2" style="font-weight:800;color:${color}">TOTAL (${rows.length} ${section==='AR'?'customers':'suppliers'})</td>
    <td class="ap-pv-td ap-pv-td-r" style="font-weight:800">₦${fmt(totalGl)}</td>
    <td class="ap-pv-td ap-pv-td-r" style="font-weight:800">₦${fmt(totalSl - rows.reduce((s,r)=>s+flt(r.sl_unallocated),0))}</td>
    <td class="ap-pv-td ap-pv-td-r" style="font-weight:800;color:#F59E0B">₦${fmt(rows.reduce((s,r)=>s+flt(r.sl_unallocated),0))}</td>
    <td class="ap-pv-td ap-pv-td-r" style="font-weight:800">₦${fmt(totalSl)}</td>
    <td class="ap-pv-td ap-pv-td-r" style="font-weight:800;color:${Math.abs(totalVar2)>1?'#EF4444':'#10B981'}">
        ${Math.abs(totalVar2)>1 ? '₦'+fmt(Math.abs(totalVar2)) : '✓'}
    </td>
    <td colspan="4" class="ap-pv-td"></td>
</tr>`;

        return `
<div class="ap-pv-section ap-pv-section-${section.toLowerCase()}" style="border-color:${color}30">
    <div class="ap-pv-sec-header" style="border-color:${color}40;background:${color}08">
        <div style="display:flex;align-items:center;gap:12px">
            <span style="font-size:22px">${icon}</span>
            <div>
                <div style="font-size:14px;font-weight:800;color:${color}">${section} Subledger Reconciliation</div>
                <div style="font-size:11px;color:var(--tx3)">
                    ${isStock ? 'SLE (Stock Ledger Entry) vs Bin cached balance per item/warehouse'
                             : `GL control account vs ${section==='AR'?'Sales Invoice outstanding − unallocated receipts':'Purchase Invoice outstanding − unallocated payments'}`}
                </div>
            </div>
        </div>
        <div style="display:flex;align-items:center;gap:10px">
            <span class="ap-pv-sec-count" style="background:${color}20;color:${color}">
                ${problems.length} issue${problems.length!==1?'s':''} of ${rows.length}
            </span>
            <span class="ap-pv-sec-count" style="background:#EF444420;color:#EF4444">
                Total variance: ₦${fmt(totalVar)}
            </span>
        </div>
    </div>
    <div style="overflow-x:auto">
        <table class="ap-pv-table">
            <thead><tr>${colsHtml}</tr></thead>
            <tbody>${rowsHtml}</tbody>
            <tfoot>${footerHtml}</tfoot>
        </table>
    </div>
</div>`;
    }

    _renderDrilldown(key, row, section, color) {
        const drill = row.drilldown;
        if (!drill || drill.length === 0) {
            return `<tr id="ap-pv-drill-${key}" style="display:none">
                <td colspan="12" class="ap-pv-drill-cell">
                    <div class="ap-pv-drill-empty">No voucher-level detail available.</div>
                </td>
            </tr>`;
        }

        const MATCH_CONF = {
            matched:  {color:'#10B981', bg:'#ECFDF5', icon:'✅', label:'Matched'},
            mismatch: {color:'#F59E0B', bg:'#FFFBEB', icon:'🟡', label:'Mismatch'},
            gl_only:  {color:'#EF4444', bg:'#FEF2F2', icon:'🔴', label:'GL Only'},
            sl_only:  {color:'#8B5CF6', bg:'#F5F3FF', icon:'🟣', label:'SL Only'},
        };

        const drillRows = drill.map(v => {
            const mc = MATCH_CONF[v.match_status] || MATCH_CONF.gl_only;
            const variance = flt(v.variance);
            return `
<tr class="ap-pv-drill-row">
    <td class="ap-pv-drill-td">
        <a href="#" onclick="frappe.set_route('Form','${esc(v.voucher_type||'')}','${esc(v.voucher_no||'')}');return false;" class="ap-link" style="font-size:12px">${esc(v.voucher_no||'—')}</a>
        <div style="font-size:10px;color:var(--tx3)">${esc(v.voucher_type||'')}</div>
    </td>
    <td class="ap-pv-drill-td" style="font-size:11px;color:var(--tx3)">${v.posting_date||'—'}</td>
    <td class="ap-pv-drill-td ap-pv-td-r" style="font-size:12px;color:#0EA5E9;font-weight:600">
        ${flt(v.gl_debit)>0 ? '₦'+fmt(v.gl_debit) : '—'}
    </td>
    <td class="ap-pv-drill-td ap-pv-td-r" style="font-size:12px;color:#8B5CF6;font-weight:600">
        ${flt(v.gl_credit)>0 ? '₦'+fmt(v.gl_credit) : '—'}
    </td>
    <td class="ap-pv-drill-td ap-pv-td-r" style="font-size:12px;font-weight:700;color:#0F172A">
        ${flt(v.gl_net)>0 ? '₦'+fmt(v.gl_net) : '—'}
    </td>
    <td class="ap-pv-drill-td ap-pv-td-r" style="font-size:12px;font-weight:600;color:var(--tx2)">
        ${flt(v.sl_amount)>0 ? '₦'+fmt(v.sl_amount) : v.match_status==='sl_only'?'₦'+fmt(v.sl_amount):'—'}
    </td>
    <td class="ap-pv-drill-td ap-pv-td-r" style="font-size:12px;font-weight:700;color:${Math.abs(variance)>1?mc.color:'#10B981'}">
        ${Math.abs(variance)>1 ? '₦'+fmt(Math.abs(variance)) : '✓'}
    </td>
    <td class="ap-pv-drill-td">
        <span style="padding:2px 9px;border-radius:20px;font-size:11px;font-weight:700;color:${mc.color};background:${mc.bg}">${mc.icon} ${mc.label}</span>
    </td>
    <td class="ap-pv-drill-td" style="font-size:10px;color:var(--tx3)">${esc(v.sl_type||'—')}</td>
</tr>`;
        }).join('');

        const totalGlNet  = drill.reduce((s,v) => s + flt(v.gl_net),  0);
        const totalSlAmt  = drill.reduce((s,v) => s + flt(v.sl_amount), 0);
        const totalVarDr  = flt(totalGlNet - totalSlAmt);

        return `
<tr id="ap-pv-drill-${key}" style="display:none">
    <td colspan="12" class="ap-pv-drill-cell">
        <div class="ap-pv-drill-wrap">
            <div class="ap-pv-drill-header">
                <span style="font-weight:800;color:${color}">🔍 Voucher-Level VLOOKUP — ${esc(row.party||row.item_code||'')}</span>
                <span style="font-size:11px;color:var(--tx3)">Matched on voucher_no · ${drill.length} vouchers</span>
                <div class="ap-pv-drill-legend">
                    ${Object.entries(MATCH_CONF).map(([k,v])=>`<span style="color:${v.color};font-size:11px">${v.icon} ${v.label}</span>`).join('')}
                </div>
            </div>
            <div style="overflow-x:auto">
                <table class="ap-pv-drill-table">
                    <thead>
                        <tr>
                            <th class="ap-pv-drill-th">Voucher No</th>
                            <th class="ap-pv-drill-th">Date</th>
                            <th class="ap-pv-drill-th ap-pv-td-r">GL Debit (₦)</th>
                            <th class="ap-pv-drill-th ap-pv-td-r">GL Credit (₦)</th>
                            <th class="ap-pv-drill-th ap-pv-td-r">GL Net (₦)</th>
                            <th class="ap-pv-drill-th ap-pv-td-r">SL Amount (₦)</th>
                            <th class="ap-pv-drill-th ap-pv-td-r">Variance (₦)</th>
                            <th class="ap-pv-drill-th">Match</th>
                            <th class="ap-pv-drill-th">SL Type</th>
                        </tr>
                    </thead>
                    <tbody>${drillRows}</tbody>
                    <tfoot>
                        <tr>
                            <td class="ap-pv-drill-td" colspan="4" style="font-weight:800">TOTAL — ${drill.length} vouchers</td>
                            <td class="ap-pv-drill-td ap-pv-td-r" style="font-weight:800">₦${fmt(totalGlNet)}</td>
                            <td class="ap-pv-drill-td ap-pv-td-r" style="font-weight:800">₦${fmt(totalSlAmt)}</td>
                            <td class="ap-pv-drill-td ap-pv-td-r" style="font-weight:800;color:${Math.abs(totalVarDr)>1?'#EF4444':'#10B981'}">
                                ${Math.abs(totalVarDr)>1 ? '₦'+fmt(Math.abs(totalVarDr)) : '✓'}
                            </td>
                            <td colspan="2" class="ap-pv-drill-td"></td>
                        </tr>
                    </tfoot>
                </table>
            </div>
        </div>
    </td>
</tr>`;
    }

    _filterPivotRows() {
        const q = (this._pivotSearch || '').toLowerCase();
        document.querySelectorAll('.ap-pv-party-row').forEach(row => {
            const text = row.textContent.toLowerCase();
            const show = !q || text.includes(q);
            row.style.display = show ? '' : 'none';
            // Also hide the drilldown when row is hidden
            const key   = row.dataset.key;
            const drill = document.getElementById(`ap-pv-drill-${key}`);
            if (drill && !show) drill.style.display = 'none';
        });
    }

    _exportPivotCSV(data) {
        const sections = [
            ...( data.ar_rows    || []).map(r => ({...r, section:'AR'})),
            ...( data.ap_rows    || []).map(r => ({...r, section:'AP'})),
            ...( data.stock_rows || []).map(r => ({...r, section:'Stock'})),
        ];
        const cols = ['section','party','check_code','gl_balance','sl_balance',
                      'sl_outstanding','sl_unallocated','variance','variance_pct','status',
                      'voucher_count','earliest_date','latest_date'];
        const hdr  = cols.join(',');
        const body = sections.map(r =>
            cols.map(c => `"${String(r[c]||'').replace(/"/g,'""')}"`).join(',')
        );
        const csv = [hdr,...body].join('\n');
        const a   = Object.assign(document.createElement('a'),{
            href: URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8;'})),
            download: `Recon_Pivot_${this.$('ap-from').value}_${this.$('ap-to').value}.csv`,
        });
        a.click();
    }

    // ── EXPORT ───────────────────────────────────────────────────────────────
    _csv() {
        const cols = ['row_number','check_level','check_code','check_type','check_name',
                      'severity','orphan_side','document_type','document','party_type','party',
                      'posting_date','gl_debit','gl_credit','sl_debit','sl_credit',
                      'impact_amount','description','recommendation','status'];
        const hdr  = cols.map(c => `"${c}"`).join(',');
        const body = this.filtered.map(r =>
            cols.map(c => `"${String(r[c]||'').replace(/"/g,'""')}"`).join(',')
        );
        const csv  = [hdr,...body].join('\n');
        const url  = URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8;'}));
        const a    = Object.assign(document.createElement('a'), {
            href: url,
            download: `Subledger_Recon_${this.$('ap-from').value}_${this.$('ap-to').value}.csv`,
        });
        a.click();
        URL.revokeObjectURL(url);
    }

    // ── SPINNER ──────────────────────────────────────────────────────────────
    _spin(msg)   { this.$('ap-spin').style.display='flex'; this.$('ap-spin-msg').textContent=msg; this.$('ap-run').disabled=true; this.$('ap-l3-only').disabled=true; }
    _unspin()    { this.$('ap-spin').style.display='none'; this.$('ap-run').disabled=false; this.$('ap-l3-only').disabled=false; }

    // ── CSS ──────────────────────────────────────────────────────────────────
    _css() {
        if (document.getElementById('apar-css')) return;
        const s = document.createElement('style');
        s.id = 'apar-css';
        s.textContent = `
#apar-root {
    --bg:#F4F7FB;--bg2:#E8EEF7;--bg3:#D5E0F0;--card:#FFF;
    --brd:#C5D4E8;--brd2:#A8BFD8;--tx1:#1A2B45;--tx2:#3D5A80;--tx3:#7A96B2;
    --pri:#2563EB;--pri_d:#1D4ED8;--grn:#10B981;--red:#EF4444;--amb:#F59E0B;
    background:var(--bg);min-height:100vh;padding:0 0 48px;
    font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;
    transition:background 0.3s,color 0.3s;
}
/* BANNER */
.ap-banner{padding:22px 28px;display:flex;align-items:center;justify-content:space-between;border-radius:0 0 24px 24px;margin-bottom:0}
.ap-banner-l{display:flex;align-items:center;gap:16px}
.ap-banner-icon{font-size:44px;filter:drop-shadow(0 4px 12px rgba(0,0,0,0.25))}
.ap-banner-title{font-size:22px;font-weight:800;color:#fff;letter-spacing:-0.5px}
.ap-banner-sub{font-size:11px;color:rgba(255,255,255,0.8);margin-top:3px}
.ap-banner-r{display:flex;align-items:center;gap:12px}
.ap-themes{display:flex;gap:5px;background:rgba(255,255,255,0.1);padding:4px 10px;border-radius:40px;backdrop-filter:blur(8px)}
.ap-theme-btn{background:rgba(255,255,255,0.15);border:none;border-radius:50%;width:32px;height:32px;cursor:pointer;font-size:15px;transition:all 0.2s}
.ap-theme-btn:hover,.ap-theme-btn.active{background:rgba(255,255,255,0.35);transform:scale(1.1)}
.ap-health{padding:6px 16px;border-radius:40px;font-size:13px;font-weight:700;display:flex;align-items:center;gap:6px;backdrop-filter:blur(8px)}
/* EXPLAINER */
.ap-explainer{padding:24px 24px 12px;background:var(--card);border-bottom:1px solid var(--brd)}
.ap-expl-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:20px}
.ap-expl-card{border:2px solid var(--brd);border-radius:16px;padding:18px;position:relative}
.ap-expl-num{display:inline-block;color:#fff;font-weight:900;font-size:13px;padding:4px 10px;border-radius:20px;margin-bottom:10px}
.ap-expl-title{font-size:15px;font-weight:800;color:var(--tx1);margin-bottom:6px}
.ap-expl-desc{font-size:12px;color:var(--tx2);line-height:1.6;margin-bottom:10px}
.ap-expl-tag{display:inline-block;background:var(--bg2);color:var(--tx3);font-size:10px;font-weight:700;padding:3px 10px;border-radius:20px;letter-spacing:0.5px;text-transform:uppercase}
.ap-expl-orphan-legend{display:flex;flex-wrap:wrap;gap:12px;padding-top:12px;border-top:1px solid var(--brd)}
.ap-legend-chip{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--tx2)}
/* CONTROLS */
.ap-controls{background:rgba(255,255,255,0.92);backdrop-filter:blur(10px);border:1px solid var(--brd);border-radius:20px;padding:18px 22px;margin:14px 20px;box-shadow:0 2px 16px rgba(0,0,0,0.05)}
.ap-ctrl-row{display:flex;flex-wrap:wrap;gap:14px;margin-bottom:14px;align-items:flex-end}
.ap-ctrl-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.ap-ctrl-g{display:flex;flex-direction:column;gap:4px}
.ap-lbl{font-size:10px;font-weight:700;color:var(--tx3);text-transform:uppercase;letter-spacing:0.8px}
.ap-input,.ap-select{background:var(--bg2);border:1.5px solid var(--brd);border-radius:10px;padding:7px 13px;font-size:13px;color:var(--tx1);outline:none;transition:border-color 0.2s,box-shadow 0.2s}
.ap-input:focus,.ap-select:focus{border-color:var(--pri);box-shadow:0 0 0 3px color-mix(in srgb,var(--pri) 20%,transparent)}
.ap-btn{display:inline-flex;align-items:center;gap:8px;padding:9px 18px;border-radius:40px;font-size:13px;font-weight:700;cursor:pointer;border:none;transition:all 0.2s;white-space:nowrap}
.ap-btn:disabled{opacity:0.5;cursor:not-allowed}
.ap-btn-primary{background:linear-gradient(135deg,var(--pri),var(--pri_d));color:#fff;box-shadow:0 3px 10px color-mix(in srgb,var(--pri) 35%,transparent)}
.ap-btn-primary:hover:not(:disabled){transform:translateY(-2px);box-shadow:0 5px 14px color-mix(in srgb,var(--pri) 45%,transparent)}
.ap-btn-l3{background:linear-gradient(135deg,#EF4444,#DC2626);color:#fff}
.ap-btn-l3:hover:not(:disabled){transform:translateY(-2px)}
.ap-btn-ai{background:linear-gradient(135deg,#8B5CF6,#6D28D9);color:#fff}
.ap-btn-ghost{background:var(--bg2);color:var(--tx2);border:1.5px solid var(--brd2)}
.ap-spin-wrap{display:flex;align-items:center;gap:10px;font-size:13px;color:var(--tx2)}
.ap-spinner{width:18px;height:18px;border:2.5px solid var(--brd2);border-top-color:var(--pri);border-radius:50%;animation:ap-spin 0.7s linear infinite}
@keyframes ap-spin{to{transform:rotate(360deg)}}
/* LEVEL 1 PANEL */
.ap-l1-panel{margin:14px 20px;border-radius:20px;border:1px solid var(--brd);overflow:hidden;background:var(--card)}
.ap-l1-header{padding:14px 20px;border-bottom:1px solid var(--brd);display:flex;flex-direction:column;gap:3px}
.ap-l1-title{font-size:14px;font-weight:800;color:var(--tx1)}
.ap-l1-sub{font-size:11px;color:var(--tx3)}
.ap-l1-sides{display:grid;grid-template-columns:repeat(auto-fit,minmax(400px,1fr));gap:0}
.ap-l1-side{padding:16px 20px;border:none;border-top:1px solid var(--brd);border-right:1px solid var(--brd)}
.ap-l1-side:last-child{border-right:none}
.ap-l1-side-header{font-size:12px;font-weight:800;padding:8px 14px;border-radius:10px;margin-bottom:12px;letter-spacing:0.5px;text-transform:uppercase}
.ap-l1-table{width:100%;border-collapse:collapse;font-size:12px}
.ap-l1-table th{background:var(--bg2);padding:7px 12px;text-align:right;font-size:10px;font-weight:700;color:var(--tx3);text-transform:uppercase}
.ap-l1-table th:first-child{text-align:left}
.ap-l1-table td{padding:7px 12px;border-bottom:1px solid var(--brd)}
.ap-l1-metric{color:var(--tx2);font-weight:600}
.ap-l1-num{text-align:right;font-weight:600;color:var(--tx1);font-variant-numeric:tabular-nums}
.ap-l1-ok{color:#10B981;font-weight:800}
.ap-l1-bad{color:#EF4444;font-weight:800}
.ap-l1-warning{margin-top:10px;padding:8px 14px;background:#FEF2F2;border-left:3px solid #EF4444;border-radius:8px;font-size:12px;color:#EF4444;font-weight:600}
.ap-l1-accounts{margin-top:8px;font-size:10px;color:var(--tx3);padding:4px 0}
/* KPIs */
.ap-kpis{padding:0 20px;margin-top:14px}
.ap-kpi-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-bottom:10px}
.ap-kpi{background:rgba(255,255,255,0.9);backdrop-filter:blur(8px);border:1px solid var(--brd);border-radius:18px;padding:14px;text-align:center;transition:transform 0.2s,box-shadow 0.2s;cursor:pointer}
.ap-kpi:hover{transform:translateY(-2px);box-shadow:0 6px 20px rgba(0,0,0,0.08)}
.ap-kpi-icon{font-size:22px;margin-bottom:6px}
.ap-kpi-val{font-size:22px;font-weight:800;line-height:1.2;margin-bottom:4px}
.ap-kpi-lbl{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;color:var(--tx2)}
.ap-kpi-sub{font-size:10px;color:var(--tx3);margin-top:3px}
/* Orphan strip */
.ap-orphan-strip{display:flex;align-items:center;gap:10px;flex-wrap:wrap;background:var(--card);border:1px solid var(--brd);border-radius:16px;padding:10px 18px}
.ap-orphan-strip-label{font-size:11px;font-weight:700;color:var(--tx3);text-transform:uppercase;letter-spacing:0.5px;margin-right:6px}
.ap-orphan-chip{display:flex;align-items:center;gap:6px;padding:5px 12px;border-radius:20px;border:1px solid;font-size:12px;transition:transform 0.15s}
.ap-orphan-chip:hover{transform:scale(1.03)}
/* TABS */
.ap-tabs{display:flex;gap:0;border-bottom:2px solid var(--brd);margin:14px 20px 0;padding:0;overflow-x:auto}
.ap-tab{background:none;border:none;border-bottom:3px solid transparent;padding:10px 20px;font-size:13px;font-weight:700;color:var(--tx3);cursor:pointer;white-space:nowrap;transition:all 0.2s;margin-bottom:-2px}
.ap-tab:hover{color:var(--tx2)}
.ap-tab.active{color:var(--pri);border-bottom-color:var(--pri)}
.ap-tab-badge{background:var(--bg2);color:var(--tx2);border-radius:20px;padding:1px 8px;font-size:11px;margin-left:6px}
.ap-tab.active .ap-tab-badge{background:var(--pri);color:#fff}
/* FILTER BAR */
.ap-fbar{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;padding:10px 20px;background:rgba(255,255,255,0.85);border-bottom:1px solid var(--brd)}
.ap-fbar-l,.ap-fbar-r{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.ap-count-label{font-size:12px;color:var(--tx3);font-weight:600}
/* TABLE */
.ap-table{width:100%;border-collapse:collapse;font-size:12.5px}
.ap-th{background:var(--bg2);padding:11px 13px;text-align:left;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:0.8px;color:var(--tx3);cursor:pointer;white-space:nowrap;border-bottom:2px solid var(--brd2);transition:background 0.1s}
.ap-th:hover{background:var(--bg3);color:var(--tx1)}
.ap-tr{cursor:pointer;transition:background 0.1s}
.ap-tr:hover td{background:var(--bg2)!important}
.ap-tr:nth-child(4n+1) td,.ap-tr:nth-child(4n+2) td{background:var(--card)}
.ap-tr:nth-child(4n+3) td,.ap-tr:nth-child(4n+4) td{background:var(--bg2)}
.ap-td{padding:9px 13px;border-bottom:1px solid var(--brd);color:var(--tx1);vertical-align:middle}
.ap-td-n{color:var(--tx3);font-size:11px;text-align:center}
.ap-td-num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.ap-td-party{max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ap-td-date{white-space:nowrap;font-size:11px;color:var(--tx3)}
.ap-td-desc{max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
/* Orphan cell highlights */
.ap-cell-gl-only{background:#EF444412!important;color:#EF4444;font-weight:700}
.ap-cell-sl-only{background:#8B5CF612!important;color:#8B5CF6;font-weight:700}
.ap-cell-mismatch{background:#F59E0B12!important;color:#D97706;font-weight:700}
/* Badges */
.ap-code{display:inline-block;padding:2px 9px;border-radius:8px;font-size:11px;font-weight:700;font-family:monospace}
.ap-sev-badge,.ap-orphan-badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;white-space:nowrap}
.ap-link{color:var(--pri);text-decoration:none;font-weight:700}
.ap-link:hover{text-decoration:underline}
/* Row expand */
.ap-td-exp{padding:0!important}
.ap-exp-box{background:color-mix(in srgb,var(--amb) 8%,var(--card));border-left:4px solid var(--amb);padding:14px 20px;margin:3px 6px 6px;border-radius:12px}
.ap-exp-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:0.8px;color:var(--amb)}
.ap-exp-class{font-size:11px;padding:2px 10px;border-radius:20px;background:var(--bg2)}
.ap-exp-rec{font-size:13px;color:var(--tx1);line-height:1.6;margin-bottom:12px}
.ap-exp-amounts{display:flex;align-items:center;gap:12px;margin-bottom:12px;flex-wrap:wrap}
.ap-exp-side{flex:1;min-width:140px;padding:10px 14px;border:2px solid;border-radius:12px;font-size:12px;color:var(--tx2)}
.ap-exp-side-label{font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:5px}
.ap-exp-vs{font-size:18px;color:var(--tx3);font-weight:700}
.ap-exp-meta{font-size:11px;color:var(--tx3)}
/* Pagination */
.ap-paging{display:flex;align-items:center;gap:5px;padding:12px 20px;background:var(--card);border-top:1px solid var(--brd)}
.ap-pg{background:var(--bg2);border:1.5px solid var(--brd2);border-radius:8px;padding:5px 11px;font-size:12px;cursor:pointer;color:var(--tx2);transition:all 0.15s}
.ap-pg:hover{background:var(--bg3)}
.ap-pg-act{background:var(--pri);color:#fff;border-color:var(--pri)}
.ap-pg-dis{opacity:0.4;cursor:not-allowed}
.ap-pg-info{font-size:11px;color:var(--tx3);margin-left:8px}
/* AI PANEL */
.ap-ai-panel{margin:14px 20px;border-radius:20px;border:1px solid var(--brd);overflow:hidden;background:var(--card)}
.ap-ai-hdr{padding:20px 24px;border-bottom:1px solid var(--brd);border-left:4px solid}
.ap-ai-src{font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:1.5px;color:var(--tx3);background:var(--bg2);padding:3px 10px;border-radius:20px;display:inline-block;margin-bottom:10px}
.ap-ai-verdict{display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.ap-ai-exec{flex:1;font-size:13px;line-height:1.7;color:var(--tx1);min-width:200px}
.ap-ai-body{display:grid;grid-template-columns:1fr 1fr}
.ap-ai-col{padding:18px 22px;border-right:1px solid var(--brd)}
.ap-ai-col:last-child{border-right:none}
.ap-ai-sec{margin-bottom:20px}
.ap-ai-sec-t{font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:1px;color:var(--tx3);margin-bottom:10px;padding-bottom:6px;border-bottom:2px solid var(--brd)}
.ap-ai-text{font-size:13px;color:var(--tx2);line-height:1.6}
.ap-ai-risk,.ap-ai-action{padding:8px 0;border-bottom:1px solid var(--brd)}
/* EMPTY */
.ap-empty{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:250px;text-align:center;padding:40px}
.ap-empty-title{font-size:20px;font-weight:800;color:var(--tx1);margin:12px 0 6px}
.ap-empty-sub{font-size:13px;color:var(--tx3)}
/* Animations */
@keyframes ap-fadein{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.ap-kpi,.ap-l1-panel,.ap-ai-panel,.ap-expl-card{animation:ap-fadein 0.35s ease}
/* PIVOT TAB */
.ap-tab-badge-pivot{background:#EF4444;color:#fff;font-size:10px}
.ap-pv-root{padding:0 0 40px}
.ap-pv-header{padding:18px 24px 10px;border-bottom:1px solid var(--brd)}
.ap-pv-title{font-size:16px;font-weight:800;color:var(--tx1);margin-bottom:4px}
.ap-pv-subtitle{font-size:12px;color:var(--tx3);line-height:1.6}
/* Summary bar */
.ap-pv-summary-bar{display:grid;grid-template-columns:repeat(3,1fr) 160px;gap:12px;padding:16px 20px;background:var(--card);border-bottom:1px solid var(--brd)}
.ap-pv-sum-chip{border:1px solid;border-radius:14px;padding:14px 16px;background:var(--bg2)}
.ap-pv-sum-label{font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:0.8px;color:var(--tx3);margin-bottom:10px}
.ap-pv-sum-row{display:flex;justify-content:space-between;align-items:center;font-size:12px;color:var(--tx2);padding:3px 0;border-bottom:1px solid var(--brd)}
.ap-pv-sum-row:last-child{border-bottom:none}
.ap-pv-sum-var{font-weight:700}
.ap-pv-sum-total{border-radius:14px;padding:18px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;text-align:center;border:2px solid}
/* Controls */
.ap-pv-controls{padding:12px 20px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;border-bottom:1px solid var(--brd);background:var(--bg2)}
.ap-pv-toggle{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--tx2);cursor:pointer;user-select:none}
.ap-pv-legend{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.ap-pv-leg-chip{padding:3px 10px;border-radius:20px;border:1px solid;font-size:11px;font-weight:600}
/* Sections */
.ap-pv-section{border-top:3px solid;margin:0;border-left:none;border-right:none;border-bottom:1px solid var(--brd)}
.ap-pv-sec-header{display:flex;align-items:center;justify-content:space-between;padding:14px 20px;border-bottom:2px solid}
.ap-pv-sec-count{font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px}
/* Pivot table */
.ap-pv-table{width:100%;border-collapse:collapse;font-size:12.5px}
.ap-pv-th{background:var(--bg2);padding:10px 13px;text-align:left;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:0.7px;color:var(--tx3);border-bottom:2px solid var(--brd2);white-space:nowrap}
.ap-pv-th-r{text-align:right}
.ap-pv-td{padding:10px 13px;border-bottom:1px solid var(--brd);color:var(--tx1);vertical-align:middle}
.ap-pv-td-r{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.ap-pv-td-party{font-weight:600;cursor:pointer}
.ap-pv-party-row{cursor:pointer;transition:background 0.1s}
.ap-pv-party-row:hover td{background:var(--bg3)!important}
.ap-pv-expand-icon{font-size:10px;transition:transform 0.15s;display:inline-block}
.ap-pv-var-cell{position:relative}
.ap-pv-footer td{background:var(--bg2);font-size:12px;border-top:2px solid var(--brd2);padding:10px 13px}
/* Drilldown */
.ap-pv-drill-cell{padding:0!important;background:var(--bg2)!important}
.ap-pv-drill-wrap{margin:4px 8px 8px;border:2px solid var(--brd2);border-radius:14px;overflow:hidden;background:var(--card)}
.ap-pv-drill-empty{padding:20px;text-align:center;font-size:12px;color:var(--tx3)}
.ap-pv-drill-header{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;padding:10px 16px;background:var(--bg2);border-bottom:1px solid var(--brd)}
.ap-pv-drill-legend{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.ap-pv-drill-table{width:100%;border-collapse:collapse;font-size:12px}
.ap-pv-drill-th{background:var(--bg3);padding:8px 12px;text-align:left;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:0.7px;color:var(--tx3);border-bottom:1px solid var(--brd2);white-space:nowrap}
.ap-pv-drill-td{padding:8px 12px;border-bottom:1px solid var(--brd);color:var(--tx1);vertical-align:middle}
.ap-pv-drill-row:hover td{background:var(--bg2)}
.ap-pv-drill-row:last-child td{border-bottom:none}
/* Loading / error */
.ap-pivot-loading{display:flex;align-items:center;justify-content:center;gap:14px;padding:60px;flex-direction:column}
.ap-pivot-err{padding:40px;text-align:center;color:#EF4444;font-weight:700}
@media(max-width:768px){
    .ap-expl-grid{grid-template-columns:1fr}
    .ap-l1-sides{grid-template-columns:1fr}
    .ap-ai-body{grid-template-columns:1fr}
    .ap-ai-col{border-right:none}
    .ap-ctrl-row{flex-direction:column}
    .ap-pv-summary-bar{grid-template-columns:1fr 1fr}
}
`;
        document.head.appendChild(s);
    }
}

console.log('AP/AR/Stock Reconciliation Engine v3.0 — Three-Level Subledger VLOOKUP loaded');

    } // end _define
}());