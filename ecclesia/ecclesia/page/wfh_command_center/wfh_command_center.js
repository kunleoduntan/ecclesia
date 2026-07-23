// WFH Command Center — Page JS (UPDATED)
// Enhanced with:
//   - Detailed check-out time display
//   - Individual user activity drill-down
//   - Work activity breakdown per user
//   - Session duration with visual progress

frappe.pages["wfh-command-center"].on_page_load = function (wrapper) {
    new WFHCommandCenter(wrapper);
};

class WFHCommandCenter {
    constructor(wrapper) {
        this.wrapper   = wrapper;
        this.data      = null;
        this._interval = null;
        this._dept     = "";
        this._date     = frappe.datetime.get_today();
        this._tab      = "overview";
        this._view     = "grid";
        this._selectedUser = null;

        this.page = frappe.ui.make_app_page({
            parent: wrapper,
            title: "WFH Command Center",
            single_column: true,
        });

        this._inject_styles();
        this._setup_actions();
        this._build_layout();
        this._init_filters();
        this.load();
        this._start_auto_refresh();
        this._start_clock();
    }

    // ── Styles ─────────────────────────────────────────────────────────────────
    _inject_styles() {
        if (document.getElementById("wfh-cc-styles")) return;
        const el = document.createElement("style");
        el.id = "wfh-cc-styles";
        el.textContent = `
.wfh-cc-page{padding:0;background:var(--bg-color,#f5f7fa);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;min-height:100vh}
.wfh-cc-hero{background:linear-gradient(135deg,#0f172a 0%,#1e293b 50%,#334155 100%);color:#fff;padding:32px 32px 28px;margin:-16px -16px 24px;border-radius:0 0 20px 20px;position:relative;overflow:hidden;box-shadow:0 8px 32px rgba(15,23,42,.3)}
.wfh-cc-hero::before{content:'';position:absolute;top:-50%;right:-20%;width:400px;height:400px;background:radial-gradient(circle,rgba(83,74,183,.15) 0%,transparent 70%);border-radius:50%}
.wfh-cc-hero h1{font-size:26px;font-weight:700;color:#fff;margin:0 0 8px;display:flex;align-items:center;gap:12px;position:relative;z-index:1}
.wfh-cc-hero p{margin:0;font-size:13px;color:#94a3b8;position:relative;z-index:1}
.wfh-cc-live{width:10px;height:10px;border-radius:50%;background:#22c55e;display:inline-block;animation:wfh-cc-pulse 2s infinite;box-shadow:0 0 16px rgba(34,197,94,.6)}
@keyframes wfh-cc-pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(1.2)}}
.wfh-cc-badge{background:rgba(255,255,255,.15);color:#e2e8f0;font-size:11px;padding:4px 14px;border-radius:20px;font-weight:500;backdrop-filter:blur(10px)}
.wfh-cc-hero-stats{display:flex;gap:32px;margin-top:20px;position:relative;z-index:1;flex-wrap:wrap}
.wfh-cc-hero-stat{display:flex;flex-direction:column;gap:2px}
.wfh-cc-hero-stat .val{font-size:20px;font-weight:700;color:#f1f5f9}
.wfh-cc-hero-stat .lbl{font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:.5px}
.wfh-cc-kgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:20px}
.wfh-cc-kpi{background:var(--card-bg,#fff);border:1px solid var(--border-color,#e2e8f0);border-radius:14px;padding:18px 20px;position:relative;overflow:hidden;transition:all .3s;cursor:pointer}
.wfh-cc-kpi:hover{transform:translateY(-3px);box-shadow:0 12px 28px rgba(0,0,0,.1);border-color:#cbd5e1}
.wfh-cc-kpi.p .wfh-cc-kval{color:#534AB7}.wfh-cc-kpi.s .wfh-cc-kval{color:#059669}
.wfh-cc-kpi.w .wfh-cc-kval{color:#d97706}.wfh-cc-kpi.d .wfh-cc-kval{color:#dc2626}
.wfh-cc-kpi.i .wfh-cc-kval{color:#0891b2}.wfh-cc-kpi.a .wfh-cc-kval{color:#7c3aed}
.wfh-cc-klabel{font-size:11px;color:#64748b;margin-bottom:8px;text-transform:uppercase;letter-spacing:.5px;font-weight:600}
.wfh-cc-kval{font-size:30px;font-weight:800;line-height:1.1;margin-bottom:4px;letter-spacing:-1px}
.wfh-cc-ksub{font-size:11px;color:#94a3b8}
.wfh-cc-trend{font-size:11px;font-weight:600;display:inline-flex;align-items:center;gap:4px}
.wfh-cc-trend.up{color:#059669}.wfh-cc-trend.down{color:#dc2626}
.wfh-cc-tabs{display:flex;gap:4px;margin-bottom:20px;flex-wrap:wrap;padding:4px;background:var(--control-bg,#e2e8f0);border-radius:14px}
.wfh-cc-tab{padding:8px 18px;border-radius:12px;font-size:12px;font-weight:500;cursor:pointer;border:none;background:transparent;color:#64748b;transition:all .2s;white-space:nowrap}
.wfh-cc-tab:hover{background:var(--card-bg,#fff);color:#334155}
.wfh-cc-tab.active{background:linear-gradient(135deg,#534AB7,#7C74D6);color:#fff;box-shadow:0 4px 12px rgba(83,74,183,.3);font-weight:600}
.wfh-cc-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px;margin-bottom:20px}
.wfh-cc-card{background:var(--card-bg,#fff);border:1px solid var(--border-color,#e2e8f0);border-radius:16px;overflow:hidden;transition:all .3s;cursor:pointer}
.wfh-cc-card:hover{box-shadow:0 8px 28px rgba(0,0,0,.1);transform:translateY(-2px)}
.wfh-cc-card.selected{border:2px solid #534AB7;box-shadow:0 8px 32px rgba(83,74,183,.2)}
.wfh-cc-card-top{display:flex;align-items:center;gap:14px;padding:16px 18px;background:linear-gradient(135deg,#f8fafc,#f1f5f9)}
.wfh-cc-card.wfh .wfh-cc-card-top{border-left:4px solid #534AB7}
.wfh-cc-card.wfo .wfh-cc-card-top{border-left:4px solid #059669}
.wfh-cc-card.field .wfh-cc-card-top,.wfh-cc-card.hybrid .wfh-cc-card-top{border-left:4px solid #d97706}
.wfh-cc-card.flagged{border-color:#fbbf24;animation:wfh-cc-flag 2s ease-in-out infinite}
@keyframes wfh-cc-flag{0%,100%{box-shadow:0 0 0 2px rgba(245,158,11,.2)}50%{box-shadow:0 0 0 5px rgba(245,158,11,.1)}}
.wfh-cc-av{width:44px;height:44px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:700;flex-shrink:0;background-size:cover;background-position:center;border:2px solid rgba(0,0,0,.06);box-shadow:0 2px 8px rgba(0,0,0,.08)}
.wfh-cc-card-body{padding:0 18px 16px}
.wfh-cc-name{font-size:15px;font-weight:600;color:#1e293b}
.wfh-cc-sub{font-size:11px;color:#64748b;margin-top:2px}
.wfh-cc-time-row{display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-top:1px solid #f1f5f9;border-bottom:1px solid #f1f5f9;margin:10px 0}
.wfh-cc-time-block{text-align:center;flex:1}
.wfh-cc-time-block .time-val{font-size:18px;font-weight:700;color:#1e293b}
.wfh-cc-time-block .time-lbl{font-size:10px;color:#94a3b8;text-transform:uppercase;margin-top:2px}
.wfh-cc-time-arrow{color:#cbd5e1;font-size:18px;padding:0 4px}
.wfh-cc-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;padding:10px 0}
.wfh-cc-stat{text-align:center}
.wfh-cc-stat .val{font-size:16px;font-weight:700;color:#1e293b}
.wfh-cc-stat .lbl{font-size:10px;color:#94a3b8;text-transform:uppercase;margin-top:2px}
.wfh-cc-pill{display:inline-block;font-size:10px;font-weight:600;padding:3px 10px;border-radius:20px;letter-spacing:.3px}
.wfh-cc-pill.p{background:#EEEDFE;color:#3C3489}.wfh-cc-pill.s{background:#D1FAE5;color:#065F46}
.wfh-cc-pill.w{background:#FEF3C7;color:#92400E}.wfh-cc-pill.d{background:#FEE2E2;color:#991B1B}
.wfh-cc-pill.i{background:#CFFAFE;color:#155E75}.wfh-cc-pill.gray{background:#F1F5F9;color:#475569}
.wfh-cc-progress{height:6px;background:#e2e8f0;border-radius:3px;overflow:hidden;margin-top:8px}
.wfh-cc-progress-fill{height:6px;border-radius:3px;transition:width .6s}
.wfh-cc-table{width:100%;border-collapse:collapse;font-size:13px}
.wfh-cc-table th{text-align:left;padding:10px 12px;background:#f8fafc;color:#475569;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.5px;border-bottom:2px solid #e2e8f0}
.wfh-cc-table td{padding:10px 12px;border-bottom:1px solid #f1f5f9;color:#334155}
.wfh-cc-table tr:hover td{background:#f8fafc}
.wfh-cc-leader{font-weight:700;color:#534AB7}
.wfh-cc-rank{width:28px;height:28px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-weight:700;font-size:12px}
.wfh-cc-rank.gold{background:#FEF3C7;color:#92400E}
.wfh-cc-rank.silver{background:#F1F5F9;color:#64748b}
.wfh-cc-rank.bronze{background:#FEE2E2;color:#991B1B}
.wfh-cc-section{background:var(--card-bg,#fff);border:1px solid var(--border-color,#e2e8f0);border-radius:16px;padding:18px 20px;margin-bottom:16px}
.wfh-cc-section-title{font-size:14px;font-weight:700;color:#1e293b;margin-bottom:14px;display:flex;align-items:center;gap:8px}
.wfh-cc-two-col{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.wfh-cc-three-col{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.wfh-cc-empty{text-align:center;padding:48px 20px;color:#94a3b8;font-size:13px;background:var(--card-bg,#fff);border:1px dashed #e2e8f0;border-radius:14px}
.wfh-cc-filters{display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap;align-items:flex-end}
.wfh-cc-anomaly{background:#FEF2F2;border:1px solid #FECACA;border-radius:12px;padding:12px 16px;margin-bottom:12px;font-size:12px;color:#991B1B;display:flex;align-items:center;gap:8px}
.wfh-cc-user-detail{background:var(--card-bg,#fff);border:1px solid var(--border-color,#e2e8f0);border-radius:16px;padding:20px;margin-bottom:16px}
.wfh-cc-activity-item{display:flex;align-items:flex-start;gap:12px;padding:10px 0;border-bottom:1px solid #f1f5f9;font-size:12px;transition:background .2s}
.wfh-cc-activity-item:hover{background:#f8fafc;margin:0 -12px;padding:10px 12px;border-radius:8px}
.wfh-cc-activity-icon{width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0}
.wfh-cc-activity-detail{flex:1;min-width:0}
.wfh-cc-activity-pts{font-weight:700;font-size:13px;flex-shrink:0}
.wfh-cc-back-btn{cursor:pointer;color:#534AB7;font-size:13px;display:inline-flex;align-items:center;gap:6px;margin-bottom:16px;font-weight:500}
.wfh-cc-back-btn:hover{color:#3C3489;text-decoration:underline}
.wfh-cc-duration-bar{height:8px;background:#e2e8f0;border-radius:4px;overflow:hidden;margin:8px 0}
.wfh-cc-duration-fill{height:8px;border-radius:4px;transition:width .6s}
.wfh-cc-active-indicator{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:6px}
.wfh-cc-active-indicator.on{background:#22c55e;box-shadow:0 0 8px rgba(34,197,94,.4)}
.wfh-cc-active-indicator.off{background:#94a3b8}
@media(max-width:1024px){.wfh-cc-two-col,.wfh-cc-three-col{grid-template-columns:1fr}}
@media(max-width:768px){.wfh-cc-hero-stats{flex-wrap:wrap;gap:16px}.wfh-cc-grid{grid-template-columns:1fr}}
        `;
        document.head.appendChild(el);
    }

    // ── Actions ─────────────────────────────────────────────────────────────────
    _setup_actions() {
        this.page.set_secondary_action("Refresh", () => this.load(), "octicon octicon-sync");
        this.page.add_menu_item("New Work Session",  () => frappe.new_doc("Work Session"));
        this.page.add_menu_item("WFH Schedules",     () => frappe.set_route("List", "WFH Schedule"));
        this.page.add_menu_item("Activity Logs",     () => frappe.set_route("List", "Work Activity Log"));
        this.page.add_menu_item("Export CSV",        () => this._export_csv());
    }

    // ── Layout ──────────────────────────────────────────────────────────────────
    _build_layout() {
        $(this.page.main).html(`
<div class="wfh-cc-page">
  <div class="wfh-cc-hero">
    <h1><span class="wfh-cc-live" aria-hidden="true"></span>
        WFH Command Center <span class="wfh-cc-badge">Workforce Analytics</span></h1>
    <p id="wfh-cc-clock">Loading...</p>
    <div class="wfh-cc-hero-stats" id="wfh-cc-hero-stats"></div>
  </div>
  <div style="padding:0 4px">
    <div class="wfh-cc-filters">
      <div id="wfh-cc-f-dept" style="min-width:200px"></div>
      <div id="wfh-cc-f-date" style="min-width:140px"></div>
      <button class="btn btn-default btn-sm" id="wfh-cc-today">Today</button>
      <div style="flex:1"></div>
      <button class="btn btn-sm" id="wfh-cc-view-grid" title="Grid View">⊞ Grid</button>
      <button class="btn btn-sm btn-default" id="wfh-cc-view-list" title="List View">☰ List</button>
    </div>
    <div class="wfh-cc-kgrid" id="wfh-cc-kpis"></div>
    <div class="wfh-cc-tabs" id="wfh-cc-tabs"></div>
    <div id="wfh-cc-anomalies"></div>
    <div id="wfh-cc-user-detail" style="display:none"></div>
    <div id="wfh-cc-main-content"></div>
    <div class="wfh-cc-two-col" style="margin-top:20px">
      <div class="wfh-cc-section">
        <div class="wfh-cc-section-title">🏆 Top Performers</div>
        <div id="wfh-cc-leaderboard"></div>
      </div>
      <div class="wfh-cc-section">
        <div class="wfh-cc-section-title">📊 Department Breakdown</div>
        <div id="wfh-cc-dept-breakdown"></div>
      </div>
    </div>
  </div>
</div>`);
    }

    // ── Filters ─────────────────────────────────────────────────────────────────
    _init_filters() {
        this._ctrl_dept = frappe.ui.form.make_control({
            parent: $("#wfh-cc-f-dept"),
            df: { fieldtype: "Link", options: "Department", label: "Department", placeholder: "All Departments" },
            render_input: true,
        });
        this._ctrl_date = frappe.ui.form.make_control({
            parent: $("#wfh-cc-f-date"),
            df: { fieldtype: "Date", label: "Date", default: frappe.datetime.get_today() },
            render_input: true,
        });
        this._ctrl_dept.$input.on("change", () => { this._dept = this._ctrl_dept.get_value(); this._selectedUser = null; this.load(); });
        this._ctrl_date.$input.on("change", () => { this._date = this._ctrl_date.get_value() || frappe.datetime.get_today(); this._selectedUser = null; this.load(); });
        $("#wfh-cc-today").on("click", () => { this._date = frappe.datetime.get_today(); this._ctrl_date?.set_value(this._date); this._selectedUser = null; this.load(); });
        $("#wfh-cc-view-grid").on("click", () => { this._view = "grid"; this._render_grid(); });
        $("#wfh-cc-view-list").on("click", () => { this._view = "list"; this._render_grid(); });
    }

    // ── Load ────────────────────────────────────────────────────────────────────
    async load() {
        try {
            const r = await frappe.call({
                method: "ecclesia.ecclesia.page.wfh_command_center.wfh_command_center.get_command_center_data",
                args: { date: this._date, department: this._dept },
            });
            if (r.message) {
                this.data = r.message;
                this._render();
            }
        } catch (e) {
            console.error("Command Center error:", e);
            frappe.show_alert({ message: __("Failed to load data"), indicator: "red" }, 4);
        }
    }

    // ── Render ───────────────────────────────────────────────────────────────────
    _render() {
        const d = this.data;
        this._render_hero_stats(d);
        this._render_kpis(d.kpis);
        this._render_tabs(d.kpis);
        if (this._selectedUser) {
            this._render_user_detail(this._selectedUser);
        } else {
            $("#wfh-cc-user-detail").hide();
            this._render_grid();
        }
        this._render_anomalies(d.anomalies);
        this._render_leaderboard(d.leaderboard);
        this._render_dept_breakdown(d.dept_breakdown);
    }

    _render_hero_stats(d) {
        const k = d.kpis;
        $("#wfh-cc-hero-stats").html(`
            <div class="wfh-cc-hero-stat"><div class="val">${k.total_active||0}</div><div class="lbl">Active Now</div></div>
            <div class="wfh-cc-hero-stat"><div class="val">${(k.productivity_score||0).toFixed(1)}%</div><div class="lbl">Productivity</div></div>
            <div class="wfh-cc-hero-stat"><div class="val">${k.total_points||0}</div><div class="lbl">Points Today</div></div>
            <div class="wfh-cc-hero-stat"><div class="val">${k.avg_hours||0}h</div><div class="lbl">Avg Hours</div></div>
            <div class="wfh-cc-hero-stat"><div class="val">${k.compliance_rate||0}%</div><div class="lbl">Compliance</div></div>
        `);
    }

    _render_kpis(k) {
        const cards = [
            { cls: "p", label: "WFH", val: k.wfh_count||0, sub: `${k.wfh_pct||0}%` },
            { cls: "s", label: "WFO", val: k.wfo_count||0, sub: `${k.wfo_pct||0}%` },
            { cls: "w", label: "Field", val: k.field_count||0, sub: "Off-site" },
            { cls: "d", label: "Flagged", val: k.flagged_count||0, sub: "Needs review" },
            { cls: "i", label: "GPS OK", val: k.gps_verified_count||0, sub: `${k.gps_pct||0}%` },
            { cls: "a", label: "Actions", val: k.total_actions||0, sub: `${k.actions_per_person||0}/person` },
        ];
        $("#wfh-cc-kpis").html(cards.map(c => `
            <div class="wfh-cc-kpi ${c.cls}">
                <div class="wfh-cc-klabel">${c.label}</div>
                <div class="wfh-cc-kval">${c.val}</div>
                <div class="wfh-cc-ksub">${c.sub}</div>
            </div>`).join(""));
    }

    _render_tabs(k) {
        const tabs = [
            { key: "overview", label: `📊 All (${k.total_active||0})` },
            { key: "wfh",      label: `🏠 WFH (${k.wfh_count||0})` },
            { key: "wfo",      label: `🏢 WFO (${k.wfo_count||0})` },
            { key: "field",    label: `🌍 Field (${k.field_count||0})` },
            { key: "flagged",  label: `⚠ Flagged (${k.flagged_count||0})` },
        ];
        if (this._selectedUser) tabs.push({ key: "detail", label: `👤 ${this._selectedUser.display_name}` });
        
        $("#wfh-cc-tabs").html(tabs.map(t => `
            <div class="wfh-cc-tab${this._tab===t.key?" active":""}" data-tab="${t.key}">${t.label}</div>`).join(""));
        $("#wfh-cc-tabs").off("click").on("click", ".wfh-cc-tab", e => {
            this._tab = $(e.currentTarget).data("tab");
            if (this._tab !== "detail") this._selectedUser = null;
            this._render_tabs(k);
            if (this._selectedUser) {
                this._render_user_detail(this._selectedUser);
            } else {
                $("#wfh-cc-user-detail").hide();
                this._render_grid();
            }
        });
    }

    _render_grid() {
        const d = this.data;
        let users = d.users || [];
        
        if (this._tab === "wfh")     users = d.wfh_users || [];
        if (this._tab === "wfo")     users = d.wfo_users || [];
        if (this._tab === "field")   users = d.field_users || [];
        if (this._tab === "flagged") users = d.flagged || [];

        if (!users.length) {
            $("#wfh-cc-main-content").html(`<div class="wfh-cc-empty">📭 No data for this filter</div>`);
            return;
        }

        if (this._view === "list") {
            this._render_list_view(users);
        } else {
            this._render_grid_view(users);
        }
    }

    _render_grid_view(users) {
        const maxPts = Math.max(...users.map(u => u.activity_points || 0), 1);
        const colors = { WFH: "#534AB7", WFO: "#059669", Hybrid: "#d97706", Field: "#d97706" };
        const pills  = { WFH: "p", WFO: "s", Hybrid: "w", Field: "w" };
        const avBg   = ["#EEEDFE","#D1FAE5","#DBEAFE","#FEF3C7","#FEE2E2","#FCE7F3","#E0E7FF","#F1F5F9"];
        const avText = ["#3C3489","#065F46","#1E40AF","#92400E","#991B1B","#9D174D","#3730A3","#475569"];

        $("#wfh-cc-main-content").html(`
            <div class="wfh-cc-grid">
                ${users.map((u, i) => {
                    const pct   = Math.round((u.activity_points||0) / maxPts * 100);
                    const color = colors[u.work_mode] || "#64748b";
                    const pill  = pills[u.work_mode] || "gray";
                    const flag  = u.inactivity_flag ? `<span class="wfh-cc-pill d" style="font-size:9px">⚠</span>` : "";
                    const gps   = u.gps_verified ? `<span title="GPS Verified" style="color:#059669">📍</span>` : "";
                    const bg    = u.user_image ? `background-image:url(${u.user_image})` : `background:${avBg[i%8]};color:${avText[i%8]}`;
                    const txt   = u.user_image ? "" : (u.initials || "?");
                    const isActive = u.status === "Open";
                    const checkoutDisplay = u.check_out_str !== "—" ? u.check_out_str : `<span style="color:#22c55e">Active</span>`;
                    
                    return `
                    <div class="wfh-cc-card ${(u.work_mode||'').toLowerCase()}${u.inactivity_flag?' flagged':''}" 
                         data-session="${u.session_name||''}" data-employee="${u.employee||''}">
                        <div class="wfh-cc-card-top">
                            <div class="wfh-cc-av" style="${bg}">${txt}</div>
                            <div style="flex:1;min-width:0">
                                <div class="wfh-cc-name">${u.display_name||"Unknown"}</div>
                                <div class="wfh-cc-sub">${u.department||""}${u.designation?' · '+u.designation:''}</div>
                            </div>
                            <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px">
                                <span class="wfh-cc-pill ${pill}">${u.work_mode||"—"}</span>
                                ${flag}${gps}
                            </div>
                        </div>
                        <div class="wfh-cc-card-body">
                            <div class="wfh-cc-time-row">
                                <div class="wfh-cc-time-block">
                                    <div class="time-lbl">Check-in</div>
                                    <div class="time-val">${u.check_in_time_display||u.check_in_str||"—"}</div>
                                </div>
                                <div class="wfh-cc-time-arrow">→</div>
                                <div class="wfh-cc-time-block">
                                    <div class="time-lbl">Check-out</div>
                                    <div class="time-val" style="color:${u.status==='Open'?'#22c55e':'#64748b'}">${u.check_out_time_display||checkoutDisplay}</div>
                                </div>
                            </div>
                            <div class="wfh-cc-duration-bar">
                                <div class="wfh-cc-duration-fill" style="width:${Math.min((u.total_hours||0)/10*100,100)}%;background:${color}"></div>
                            </div>
                            <div style="text-align:center;font-size:11px;color:#64748b;margin-bottom:8px">Duration: ${u.duration_display||u.total_hours+'h'}</div>
                            <div class="wfh-cc-stats">
                                <div class="wfh-cc-stat"><div class="val">${u.activity_count||0}</div><div class="lbl">Actions</div></div>
                                <div class="wfh-cc-stat"><div class="val" style="color:${color}">${u.activity_points||0}</div><div class="lbl">Points</div></div>
                                <div class="wfh-cc-stat"><div class="val">${u.actions_last_hour||0}</div><div class="lbl">Last Hour</div></div>
                            </div>
                            ${u.last_active_str !== '—' ? `<div style="font-size:10px;color:#94a3b8;margin-top:6px">Last active: ${u.last_active_str}${u.last_action_doc?' · '+u.last_action_doc:''}</div>` : ''}
                            <button class="btn btn-xs btn-default" style="margin-top:8px;width:100%" data-action="view-activity" data-employee="${u.employee||''}">📋 View Activity Details</button>
                        </div>
                    </div>`;
                }).join("")}
            </div>`);

        // Click handlers
        $("#wfh-cc-main-content").off("click").on("click", ".wfh-cc-card", function(e) {
            const session = $(this).data("session");
            if (session && !$(e.target).closest('button').length) {
                frappe.set_route("Form", "Work Session", session);
            }
        });

        $("#wfh-cc-main-content").off("click", "[data-action='view-activity']").on("click", "[data-action='view-activity']", async (e) => {
            e.stopPropagation();
            const employee = $(e.currentTarget).data("employee");
            if (employee) {
                await this._load_user_activity(employee);
            }
        });
    }

    _render_list_view(users) {
        $("#wfh-cc-main-content").html(`
            <div class="wfh-cc-section" style="padding:0;overflow:auto">
                <table class="wfh-cc-table">
                    <thead>
                        <tr>
                            <th>Employee</th><th>Mode</th><th>Dept</th>
                            <th>Check-in</th><th>Check-out</th><th>Duration</th>
                            <th>Points</th><th>Actions</th><th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${users.map(u => `
                        <tr data-session="${u.session_name||''}" style="cursor:pointer">
                            <td><b>${u.display_name||"?"}</b></td>
                            <td><span class="wfh-cc-pill ${u.work_mode==='WFH'?'p':u.work_mode==='WFO'?'s':'w'}">${u.work_mode||"—"}</span></td>
                            <td>${u.department||"—"}</td>
                            <td>${u.check_in_time_display||u.check_in_str||"—"}</td>
                            <td>${u.status==='Open'?'<span style="color:#22c55e">Active</span>':(u.check_out_time_display||u.check_out_str||"—")}</td>
                            <td><b>${u.duration_display||u.total_hours+'h'}</b></td>
                            <td><b>${u.activity_points||0}</b></td>
                            <td>${u.activity_count||0} (${u.actions_last_hour||0}/hr)</td>
                            <td>${u.inactivity_flag?'<span class="wfh-cc-pill d">Idle</span>':u.status==='Open'?'<span class="wfh-cc-pill s">Active</span>':'<span class="wfh-cc-pill gray">Closed</span>'}</td>
                        </tr>`).join("")}
                    </tbody>
                </table>
            </div>`);

        $("#wfh-cc-main-content").off("click","tr").on("click", "tr", function() {
            const s = $(this).data("session");
            if (s) frappe.set_route("Form", "Work Session", s);
        });
    }

    // ── User Activity Detail ───────────────────────────────────────────────────
    async _load_user_activity(employee) {
        try {
            const r = await frappe.call({
                method: "ecclesia.ecclesia.page.wfh_command_center.wfh_command_center.get_user_activity_detail",
                args: { employee: employee, date: this._date },
            });
            if (r.message) {
                this._selectedUser = r.message;
                this._tab = "detail";
                this._render_tabs(this.data.kpis);
                this._render_user_detail(this._selectedUser);
            }
        } catch (e) {
            frappe.show_alert("Failed to load user activity", "red");
        }
    }

    _render_user_detail(user) {
        if (!user) return;
        
        const d = user;
        const colors = { WFH: "#534AB7", WFO: "#059669", Hybrid: "#d97706", Field: "#d97706" };
        const color = colors[d.work_mode] || "#64748b";
        const isActive = d.status === "Open";
        const moduleColors = { Sales:"#534AB7", Accounts:"#0891b2", CRM:"#d97706", Buying:"#7c3aed", Stock:"#059669", Other:"#64748b" };
        const moduleIcons = { Sales:"💰", Accounts:"📊", CRM:"👥", Buying:"🛒", Stock:"📦", Other:"📋" };
        
        $("#wfh-cc-user-detail").show();
        $("#wfh-cc-main-content").hide();
        $("#wfh-cc-leaderboard").closest(".wfh-cc-section").hide();
        $("#wfh-cc-dept-breakdown").closest(".wfh-cc-section").hide();
        
        $("#wfh-cc-user-detail").html(`
            <div class="wfh-cc-back-btn" id="wfh-cc-back-btn">← Back to Dashboard</div>
            
            <div class="wfh-cc-user-detail">
                <div style="display:flex;align-items:center;gap:16px;margin-bottom:20px">
                    <div class="wfh-cc-av" style="width:56px;height:56px;font-size:20px;background:${color}22;color:${color}">
                        ${d.initials||"?"}
                    </div>
                    <div style="flex:1">
                        <div style="font-size:18px;font-weight:700;color:#1e293b">${d.display_name||"Unknown"}</div>
                        <div style="color:#64748b;font-size:13px">${d.department||""} · ${d.designation||""}</div>
                        <div style="margin-top:4px">
                            <span class="wfh-cc-pill ${d.work_mode==='WFH'?'p':d.work_mode==='WFO'?'s':'w'}">${d.work_mode||"—"}</span>
                            ${isActive?'<span class="wfh-cc-pill s">Active</span>':'<span class="wfh-cc-pill gray">Closed</span>'}
                            ${d.gps_verified?'<span class="wfh-cc-pill i">📍 GPS OK</span>':''}
                        </div>
                    </div>
                </div>
                
                <div class="wfh-cc-time-row" style="margin:16px 0">
                    <div class="wfh-cc-time-block">
                        <div class="time-lbl">Check-in</div>
                        <div class="time-val">${d.check_in_full||d.check_in_str||"—"}</div>
                        <div style="font-size:10px;color:#94a3b8">${d.check_in_relative||""}</div>
                    </div>
                    <div class="wfh-cc-time-arrow">→</div>
                    <div class="wfh-cc-time-block">
                        <div class="time-lbl">Check-out</div>
                        <div class="time-val" style="color:${isActive?'#22c55e':'#dc2626'}">
                            ${isActive? '<span class="wfh-cc-active-indicator on"></span>Active Now' : (d.check_out_full||d.check_out_str||"—")}
                        </div>
                        <div style="font-size:10px;color:#94a3b8">${isActive? 'Session in progress' : (d.check_out_relative||"")}</div>
                    </div>
                    <div class="wfh-cc-time-block">
                        <div class="time-lbl">Duration</div>
                        <div class="time-val" style="color:${color}">${d.duration_display||d.total_hours+'h'}</div>
                        <div style="font-size:10px;color:#94a3b8">${d.duration_minutes||0} minutes</div>
                    </div>
                </div>
                
                <div class="wfh-cc-duration-bar" style="height:10px;margin:16px 0">
                    <div class="wfh-cc-duration-fill" style="width:${Math.min((d.total_hours||0)/10*100,100)}%;background:linear-gradient(90deg,${color},${color}88)"></div>
                </div>
            </div>
            
            <div class="wfh-cc-three-col" style="margin-bottom:16px">
                <div class="wfh-cc-section" style="text-align:center">
                    <div style="font-size:28px;font-weight:800;color:${color}">${d.activity_points||0}</div>
                    <div style="font-size:11px;color:#64748b;text-transform:uppercase">Total Points</div>
                </div>
                <div class="wfh-cc-section" style="text-align:center">
                    <div style="font-size:28px;font-weight:800;color:#1e293b">${d.activity_count||0}</div>
                    <div style="font-size:11px;color:#64748b;text-transform:uppercase">Total Actions</div>
                </div>
                <div class="wfh-cc-section" style="text-align:center">
                    <div style="font-size:28px;font-weight:800;color:#059669">${d.points_per_hour||0}</div>
                    <div style="font-size:11px;color:#64748b;text-transform:uppercase">Points/Hour</div>
                </div>
            </div>
            
            <div class="wfh-cc-section">
                <div class="wfh-cc-section-title">📋 Activity Breakdown by DocType</div>
                <div id="wfh-cc-doctype-breakdown"></div>
            </div>
            
            <div class="wfh-cc-section">
                <div class="wfh-cc-section-title">🕐 Activity Timeline</div>
                <div id="wfh-cc-activity-timeline"></div>
            </div>
        `);
        
        // Doctype breakdown
        if (d.doctype_breakdown?.length) {
            const maxDocPts = Math.max(...d.doctype_breakdown.map(dt => dt.points || 0), 1);
            $("#wfh-cc-doctype-breakdown").html(d.doctype_breakdown.map(dt => `
                <div style="display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid #f1f5f9">
                    <div class="wfh-cc-activity-icon" style="background:${(moduleColors[dt.module]||'#64748b')}22;color:${moduleColors[dt.module]||'#64748b'}">
                        ${moduleIcons[dt.module]||'📋'}
                    </div>
                    <div style="flex:1">
                        <div style="font-weight:600;font-size:13px">${dt.doctype||"Unknown"}</div>
                        <div style="font-size:11px;color:#94a3b8">${dt.count||0} actions · ${dt.module||"Other"}</div>
                    </div>
                    <div style="text-align:right">
                        <div style="font-weight:700;font-size:14px;color:${color}">${dt.points||0} pts</div>
                        <div class="wfh-cc-progress" style="width:80px;margin-top:4px">
                            <div class="wfh-cc-progress-fill" style="width:${Math.round((dt.points||0)/maxDocPts*100)}%;background:${moduleColors[dt.module]||'#64748b'}"></div>
                        </div>
                    </div>
                </div>
            `).join(""));
        } else {
            $("#wfh-cc-doctype-breakdown").html(`<div style="color:#94a3b8;text-align:center;padding:20px">No activity recorded</div>`);
        }
        
        // Activity timeline
        if (d.activities?.length) {
            $("#wfh-cc-activity-timeline").html(d.activities.map(a => `
                <div class="wfh-cc-activity-item">
                    <div class="wfh-cc-activity-icon" style="background:${(moduleColors[a.module]||'#64748b')}22;color:${moduleColors[a.module]||'#64748b'}">
                        ${moduleIcons[a.module]||'📋'}
                    </div>
                    <div class="wfh-cc-activity-detail">
                        <div style="font-weight:600">${a.reference_doctype||""} · ${a.action||""}</div>
                        <div style="font-size:11px;color:#94a3b8">${a.reference_name||""}</div>
                        <div style="font-size:10px;color:#cbd5e1;margin-top:2px">${a.time_display||""}${a.business_value>0?` · Value: ${frappe.format(a.business_value,{fieldtype:'Currency'})}`:''}</div>
                    </div>
                    <div class="wfh-cc-activity-pts" style="color:${a.is_dampened?'#d97706':'#059669'}">
                        +${a.points||0}
                        ${a.is_dampened?'<span title="Dampened" style="font-size:9px">⚠</span>':''}
                    </div>
                </div>
            `).join(""));
        } else {
            $("#wfh-cc-activity-timeline").html(`<div style="color:#94a3b8;text-align:center;padding:20px">No activity yet today</div>`);
        }
        
        // Back button
        $("#wfh-cc-back-btn").off("click").on("click", () => {
            this._selectedUser = null;
            this._tab = "overview";
            $("#wfh-cc-user-detail").hide();
            $("#wfh-cc-main-content").show();
            $("#wfh-cc-leaderboard").closest(".wfh-cc-section").show();
            $("#wfh-cc-dept-breakdown").closest(".wfh-cc-section").show();
            this._render_tabs(this.data.kpis);
            this._render_grid();
        });
    }

    _render_anomalies(anomalies) {
        if (!anomalies?.length) { $("#wfh-cc-anomalies").html(""); return; }
        $("#wfh-cc-anomalies").html(anomalies.map(a => `
            <div class="wfh-cc-anomaly">
                <span>⚠</span>
                <span><b>${a.title}</b>: ${a.description}</span>
            </div>`).join(""));
    }

    _render_leaderboard(leaders) {
        if (!leaders?.length) {
            $("#wfh-cc-leaderboard").html(`<div class="wfh-cc-empty" style="padding:24px">No data yet</div>`);
            return;
        }
        const medals = ["gold","silver","bronze"];
        $("#wfh-cc-leaderboard").html(`
            <table class="wfh-cc-table">
                <thead><tr><th>#</th><th>Employee</th><th>Dept</th><th>Points</th><th>Actions</th></tr></thead>
                <tbody>
                    ${leaders.slice(0,10).map((l, i) => `
                    <tr style="cursor:pointer" data-employee="${l.employee||''}">
                        <td><span class="wfh-cc-rank ${i<3?medals[i]:''}">${i+1}</span></td>
                        <td class="${i<3?'wfh-cc-leader':''}">${l.employee_name||"?"}</td>
                        <td>${l.department||"—"}</td>
                        <td><b>${l.total_points||0}</b></td>
                        <td>${l.total_actions||0}</td>
                    </tr>`).join("")}
                </tbody>
            </table>`);
            
        $("#wfh-cc-leaderboard").off("click","tr").on("click", "tr", async (e) => {
            const employee = $(e.currentTarget).data("employee");
            if (employee) await this._load_user_activity(employee);
        });
    }

    _render_dept_breakdown(depts) {
        if (!depts?.length) {
            $("#wfh-cc-dept-breakdown").html(`<div class="wfh-cc-empty" style="padding:24px">No data yet</div>`);
            return;
        }
        const maxVal = Math.max(...depts.map(d => d.total_points || 0), 1);
        $("#wfh-cc-dept-breakdown").html(depts.map(d => `
            <div style="margin-bottom:12px">
                <div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px">
                    <span><b>${d.department||"—"}</b> (${d.count||0})</span>
                    <span>${d.total_points||0} pts · ${d.avg_points||0} avg</span>
                </div>
                <div class="wfh-cc-progress">
                    <div class="wfh-cc-progress-fill" style="width:${Math.round((d.total_points||0)/maxVal*100)}%;background:linear-gradient(90deg,#534AB7,#7C74D6)"></div>
                </div>
            </div>`).join(""));
    }

    _export_csv() {
        if (!this.data?.users) return;
        let csv = "Name,Mode,Dept,Check-in,Check-out,Duration,Points,Actions,GPS,Status\n";
        this.data.users.forEach(u => {
            csv += `"${u.display_name||''}","${u.work_mode||''}","${u.department||''}","${u.check_in_time_display||u.check_in_str||''}","${u.check_out_time_display||u.check_out_str||''}","${u.duration_display||''}","${u.activity_points||0}","${u.activity_count||0}","${u.gps_verified?'Yes':'No'}","${u.status||''}"\n`;
        });
        const a = Object.assign(document.createElement("a"), {
            href: URL.createObjectURL(new Blob([csv], {type:"text/csv"})),
            download: `wfh-command-center-${this._date}.csv`
        });
        a.click();
    }

    _start_clock() {
        const tick = () => {
            const n = new Date(), el = document.getElementById("wfh-cc-clock");
            if (el) el.innerHTML = `<span style="color:#e2e8f0">${n.toLocaleDateString("en-GB",{weekday:"long",day:"numeric",month:"long",year:"numeric"})}</span> · <span style="color:#94a3b8">${n.toLocaleTimeString("en-GB")}</span>`;
        };
        tick(); setInterval(tick, 1000);
    }

    _start_auto_refresh() {
        this._interval = setInterval(() => {
            if (!this._selectedUser) this.load();
        }, 30000);
    }
}