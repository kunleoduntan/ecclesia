// WFH Dashboard — Page JS (FIXED + MERGED)
// Ecclesia Module
// Path: ecclesia/ecclesia/page/wfh_dashboard/wfh_dashboard.js
//
// FIXES APPLIED:
//   1. frappe.pages key = "wfh-dashboard" (matches page_name in JSON, NOT underscore)
//   2. All method paths use ecclesia.ecclesia.page.wfh_dashboard.wfh_dashboard.*
//   3. last_active_str referenced consistently
//   4. Safe delegated click handlers (no inline onclick with special chars)
//   5. Works like Live Dashboard: real-time, all users, auto-refresh 30s

frappe.pages["wfh-dashboard"].on_page_load = function (wrapper) {
    new WFHDashboard(wrapper);
};

class WFHDashboard {
    constructor(wrapper) {
        this.wrapper   = wrapper;
        this.data      = null;
        this._interval = null;
        this._dept     = "";
        this._date     = frappe.datetime.get_today();
        this._tab      = "all";

        this.page = frappe.ui.make_app_page({
            parent: wrapper,
            title: "WFH Dashboard",
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
        if (document.getElementById("wfh-dash-styles")) return;
        const el = document.createElement("style");
        el.id = "wfh-dash-styles";
        el.textContent = `
.wfh-page{padding:0;background:var(--bg-color,#f8f9fa);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif}
.wfh-hero{background:linear-gradient(135deg,#534AB7 0%,#1a1a6e 30%,#185FA5 100%);color:#fff;padding:28px 32px 24px;margin:-16px -16px 24px;border-radius:0 0 16px 16px;position:relative;overflow:hidden;box-shadow:0 4px 24px rgba(83,74,183,.25)}
.wfh-hero h1{font-size:22px;font-weight:600;color:#fff;margin:0 0 6px;display:flex;align-items:center;gap:12px}
.wfh-hero p{margin:0;font-size:13px;color:rgba(255,255,255,.75)}
.wfh-live{width:9px;height:9px;border-radius:50%;background:#5DCAA5;display:inline-block;animation:wfh-pulse 2s infinite;box-shadow:0 0 12px rgba(93,202,165,.6)}
@keyframes wfh-pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(1.15)}}
.wfh-badge{background:rgba(255,255,255,.18);color:#fff;font-size:11px;padding:3px 12px;border-radius:20px;font-weight:500}
.wfh-kgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(135px,1fr));gap:12px;margin-bottom:20px}
.wfh-kpi{background:var(--card-bg,#fff);border:1px solid var(--border-color,#e0e0e0);border-radius:12px;padding:16px 18px;position:relative;overflow:hidden;transition:all .25s;cursor:default}
.wfh-kpi:hover{transform:translateY(-2px);box-shadow:0 6px 20px rgba(0,0,0,.08)}
.wfh-kpi::after{content:'';position:absolute;left:0;top:0;bottom:0;width:4px;border-radius:4px 0 0 4px}
.wfh-kpi.p::after{background:linear-gradient(180deg,#534AB7,#7C74D6)}
.wfh-kpi.t::after{background:linear-gradient(180deg,#1D9E75,#34C77B)}
.wfh-kpi.b::after{background:linear-gradient(180deg,#185FA5,#3B8BD6)}
.wfh-kpi.a::after{background:linear-gradient(180deg,#BA7517,#E69A2D)}
.wfh-kpi.r::after{background:linear-gradient(180deg,#D85A30,#F07650)}
.wfh-kpi.g::after{background:linear-gradient(180deg,#639922,#7FB832)}
.wfh-klabel{font-size:11px;color:var(--text-muted,#6c757d);margin-bottom:6px;text-transform:uppercase;letter-spacing:.5px;font-weight:500}
.wfh-kval{font-size:26px;font-weight:700;line-height:1.1;margin-bottom:4px;letter-spacing:-.5px}
.wfh-kpi.p .wfh-kval{color:#534AB7}.wfh-kpi.t .wfh-kval{color:#0F6E56}
.wfh-kpi.b .wfh-kval{color:#185FA5}.wfh-kpi.a .wfh-kval{color:#633806}
.wfh-kpi.r .wfh-kval{color:#993C1D}.wfh-kpi.g .wfh-kval{color:#3B6D11}
.wfh-ksub{font-size:11px;color:var(--text-muted,#6c757d)}
.wfh-tabs{display:flex;gap:6px;margin-bottom:16px;flex-wrap:wrap;padding:4px;background:var(--control-bg,#f0f0f0);border-radius:12px}
.wfh-tab{padding:7px 16px;border-radius:10px;font-size:12px;font-weight:500;cursor:pointer;border:none;background:transparent;color:var(--text-muted,#6c757d);transition:all .2s}
.wfh-tab:hover{background:var(--card-bg,#fff);color:var(--text-primary,#333)}
.wfh-tab.active{background:#534AB7;color:#fff;box-shadow:0 2px 8px rgba(83,74,183,.3);font-weight:600}
.wfh-tab.wfo-tab.active{background:#1D9E75;box-shadow:0 2px 8px rgba(29,158,117,.3)}
.wfh-tab.field-tab.active{background:#BA7517;box-shadow:0 2px 8px rgba(186,117,23,.3)}
.wfh-tab.flag-tab.active{background:#D85A30;box-shadow:0 2px 8px rgba(216,90,48,.3)}
.wfh-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(285px,1fr));gap:14px;margin-bottom:20px}
.wfh-card{background:var(--card-bg,#fff);border:1px solid var(--border-color,#e0e0e0);border-radius:14px;overflow:hidden;transition:all .25s;cursor:pointer}
.wfh-card:hover{box-shadow:0 8px 24px rgba(0,0,0,.10);transform:translateY(-2px)}
.wfh-card.wfh .wfh-card-top{border-left:4px solid #534AB7}
.wfh-card.wfo .wfh-card-top{border-left:4px solid #1D9E75}
.wfh-card.hybrid .wfh-card-top,.wfh-card.field .wfh-card-top{border-left:4px solid #BA7517}
.wfh-card.flagged{border-color:#fbbf24;animation:wfh-flag 2s ease-in-out infinite}
@keyframes wfh-flag{0%,100%{box-shadow:0 0 0 1px rgba(245,158,11,.3)}50%{box-shadow:0 0 0 3px rgba(245,158,11,.15)}}
.wfh-card-top{display:flex;align-items:center;gap:12px;padding:14px 16px}
.wfh-av{width:42px;height:42px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:600;flex-shrink:0;background-size:cover;background-position:center;border:2px solid rgba(0,0,0,.06)}
.wfh-card-name{font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--text-primary,#333)}
.wfh-card-sub{font-size:11px;color:var(--text-muted,#6c757d);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.wfh-card-body{padding:0 16px 14px}
.wfh-stat-row{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:10px;font-size:12px}
.wfh-stat-item{display:flex;flex-direction:column;gap:2px}
.wfh-stat-label{font-size:10px;color:var(--text-muted,#6c757d);text-transform:uppercase;letter-spacing:.3px;font-weight:500}
.wfh-stat-val{font-weight:600;color:var(--text-primary,#333);font-size:13px}
.wfh-pill{display:inline-block;font-size:10px;font-weight:600;padding:3px 8px;border-radius:20px;letter-spacing:.3px}
.wfh-pill.g{background:#EAF3DE;color:#27500A}.wfh-pill.b{background:#E6F1FB;color:#0C447C}
.wfh-pill.p{background:#EEEDFE;color:#3C3489}.wfh-pill.a{background:#FAEEDA;color:#633806}
.wfh-pill.r{background:#FCEBEB;color:#791F1F}.wfh-pill.t{background:#E1F5EE;color:#085041}
.wfh-pill.gray{background:#F1EFE8;color:#444441}
.wfh-pts-bar{height:4px;background:var(--border-color,#e0e0e0);border-radius:2px;overflow:hidden;margin-top:8px}
.wfh-pts-fill{height:4px;border-radius:2px;transition:width .6s}
.wfh-act-item{display:flex;align-items:center;gap:10px;padding:9px 0;border-bottom:.5px solid var(--border-color,#e0e0e0);font-size:12px}
.wfh-act-item:last-child{border-bottom:none}
.wfh-act-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.wfh-act-pts{margin-left:auto;font-weight:600;color:#0F6E56;font-size:12px}
.wfh-not-in{background:var(--card-bg,#fff);border:1px dashed #fbbf24;border-radius:12px;padding:12px 16px;font-size:12px;color:var(--text-muted,#6c757d)}
.wfh-section-title{font-size:13px;font-weight:600;color:var(--text-muted,#6c757d);margin-bottom:10px;display:flex;align-items:center;gap:8px;text-transform:uppercase;letter-spacing:.5px}
.wfh-two-col{display:grid;grid-template-columns:2fr 1fr;gap:18px;margin-bottom:16px}
.wfh-empty{text-align:center;padding:48px 20px;color:var(--text-muted,#6c757d);font-size:13px;background:var(--card-bg,#fff);border:1px dashed var(--border-color,#e0e0e0);border-radius:12px}
.wfh-filters{display:flex;gap:12px;margin-bottom:18px;flex-wrap:wrap;align-items:flex-end}
@media(max-width:900px){.wfh-two-col{grid-template-columns:1fr}}
        `;
        document.head.appendChild(el);
    }

    // ── Actions ─────────────────────────────────────────────────────────────────
    _setup_actions() {
        this.page.set_secondary_action("Refresh", () => this.load(), "octicon octicon-sync");
        this.page.add_menu_item("New Work Session",  () => frappe.new_doc("Work Session"));
        this.page.add_menu_item("New External Task", () => frappe.new_doc("External Task"));
        this.page.add_menu_item("WFH Schedules",     () => frappe.set_route("List", "WFH Schedule"));
        this.page.add_menu_item("WFH Requests",      () => frappe.set_route("List", "WFH Request"));
        this.page.add_menu_item("Activity Logs",     () => frappe.set_route("List", "Work Activity Log"));
        this.page.add_menu_item("Export CSV",        () => this._export_csv());
    }

    // ── Layout ──────────────────────────────────────────────────────────────────
    _build_layout() {
        $(this.page.main).html(`
<div class="wfh-page">
  <div class="wfh-hero">
    <h1><span class="wfh-live" aria-hidden="true"></span>
        WFH Dashboard <span class="wfh-badge">Remote Work System</span></h1>
    <p id="wfh-clock">Loading...</p>
  </div>
  <div style="padding:0 4px">
    <div class="wfh-filters">
      <div id="wfh-f-dept" style="min-width:180px"></div>
      <div id="wfh-f-date" style="min-width:140px"></div>
      <button class="btn btn-default btn-sm" id="wfh-today-btn">Today</button>
      <button class="btn btn-default btn-sm" id="wfh-week-btn">This Week</button>
    </div>
    <div class="wfh-kgrid" id="wfh-kpis"></div>
    <div class="wfh-tabs" id="wfh-tabs"></div>
    <div id="wfh-main-content"></div>
    <div class="wfh-two-col">
      <div>
        <div class="wfh-section-title">Recent Activity</div>
        <div id="wfh-activity"></div>
      </div>
      <div>
        <div class="wfh-section-title">Not Yet Checked In</div>
        <div id="wfh-not-in"></div>
      </div>
    </div>
  </div>
</div>`);
    }

    // ── Filters ─────────────────────────────────────────────────────────────────
    _init_filters() {
        this._ctrl_dept = frappe.ui.form.make_control({
            parent: $("#wfh-f-dept"),
            df: { fieldtype: "Link", options: "Department", label: "Department" },
            render_input: true,
        });
        this._ctrl_date = frappe.ui.form.make_control({
            parent: $("#wfh-f-date"),
            df: { fieldtype: "Date", label: "Date", default: frappe.datetime.get_today() },
            render_input: true,
        });
        this._ctrl_dept.$input.on("change", () => { this._dept = this._ctrl_dept.get_value(); this.load(); });
        this._ctrl_date.$input.on("change", () => { this._date = this._ctrl_date.get_value() || frappe.datetime.get_today(); this.load(); });
        $("#wfh-today-btn").on("click", () => { this._date = frappe.datetime.get_today(); this._ctrl_date?.set_value(this._date); this.load(); });
        $("#wfh-week-btn").on("click",  () => { this._ctrl_date?.set_value(frappe.datetime.week_start()); this._date = frappe.datetime.week_start(); this.load(); });
    }

    // ── Load ────────────────────────────────────────────────────────────────────
    async load() {
        try {
            const r = await frappe.call({
                // FIXED PATH ↓
                method: "ecclesia.ecclesia.page.wfh_dashboard.wfh_dashboard.get_live_data",
                args: { date: this._date, department: this._dept },
            });
            if (r.message) {
                this.data = r.message;
                this._render();
            }
        } catch (e) {
            console.error("WFH Dashboard error:", e);
            frappe.show_alert({ message: __("Failed to load dashboard"), indicator: "red" }, 4);
        }
    }

    // ── Render ───────────────────────────────────────────────────────────────────
    _render() {
        const d = this.data;
        this._render_kpis(d.kpis);
        this._render_tabs(d.kpis);
        this._render_grid();
        this._render_activity(d.recent_activity);
        this._render_not_in(d.schedule_today?.not_checked_in_wfh || []);
    }

    _render_kpis(k) {
        const cards = [
            { cls: "p", label: "Active Now",      val: k.total_active  || 0, sub: "All work modes" },
            { cls: "p", label: "WFH",              val: k.wfh_count     || 0, sub: "Working from home" },
            { cls: "t", label: "WFO",              val: k.wfo_count     || 0, sub: "In office" },
            { cls: "a", label: "Field / Hybrid",   val: k.field_count   || 0, sub: "Off-site" },
            { cls: "b", label: "Total Hours",      val: `${k.total_hours||0}h`, sub: `Avg ${k.avg_hours||0}h/person` },
            { cls: "g", label: "Activity Points",  val: k.total_points  || 0, sub: `${k.total_actions||0} actions` },
            { cls: "r", label: "Flagged",          val: k.flagged_count || 0, sub: "Idle > threshold" },
        ];
        $("#wfh-kpis").html(cards.map(c => `
            <div class="wfh-kpi ${c.cls}">
                <div class="wfh-klabel">${c.label}</div>
                <div class="wfh-kval">${c.val}</div>
                <div class="wfh-ksub">${c.sub}</div>
            </div>`).join(""));
    }

    _render_tabs(k) {
        const tabs = [
            { key: "all",     label: `All (${k.total_active||0})`,    cls: "" },
            { key: "wfh",     label: `WFH (${k.wfh_count||0})`,       cls: "" },
            { key: "wfo",     label: `WFO (${k.wfo_count||0})`,       cls: "wfo-tab" },
            { key: "field",   label: `Field (${k.field_count||0})`,   cls: "field-tab" },
        ];
        if (k.flagged_count) tabs.push({ key: "flagged", label: `Flagged (${k.flagged_count})`, cls: "flag-tab" });
        $("#wfh-tabs").html(tabs.map(t => `
            <div class="wfh-tab ${t.cls}${this._tab===t.key?" active":"}"}" data-tab="${t.key}">${t.label}</div>`).join(""));
        $("#wfh-tabs").off("click").on("click", ".wfh-tab", e => {
            this._tab = $(e.currentTarget).data("tab");
            this._render_tabs(k);
            this._render_grid();
        });
    }

    _render_grid() {
        const d = this.data;
        let users = d.users || [];
        if (this._tab === "wfh")     users = d.wfh_users   || [];
        if (this._tab === "wfo")     users = d.wfo_users   || [];
        if (this._tab === "field")   users = d.field_users || [];
        if (this._tab === "flagged") users = d.flagged     || [];

        if (!users.length) {
            $("#wfh-main-content").html(`<div class="wfh-empty"><div>No active sessions for this filter</div></div>`);
            return;
        }

        const maxPts = Math.max(...users.map(u => u.activity_points || 0), 1);
        const modeColors = { WFH: "#534AB7", WFO: "#1D9E75", Hybrid: "#BA7517", Field: "#BA7517" };
        const modePills  = { WFH: "p", WFO: "t", Hybrid: "a", Field: "a" };
        const AVA_BG   = ["#EEEDFE","#E1F5EE","#E6F1FB","#FAEEDA","#FAECE7","#FDE8F0","#E8F0FE","#F5F3EB"];
        const AVA_TEXT = ["#3C3489","#085041","#0C447C","#633806","#712B13","#7A1A3E","#1A3A7A","#5C4A1E"];

        $("#wfh-main-content").html(`
            <div class="wfh-grid">
                ${users.map((u, i) => {
                    const mk    = (u.work_mode||"").replace(/\s+/g,"").toLowerCase();
                    const pct   = Math.round((u.activity_points||0) / maxPts * 100);
                    const color = modeColors[u.work_mode] || "#888780";
                    const pill  = modePills[u.work_mode]  || "gray";
                    const flag  = u.inactivity_flag ? `<span class="wfh-pill r" style="font-size:9px">⚠ Idle</span>` : "";
                    const gps   = u.gps_verified   ? `<span title="GPS Verified" style="color:#1D9E75;font-size:13px">⊕</span>` : "";
                    const avBg  = u.user_image
                        ? `background-image:url(${u.user_image});background-color:transparent`
                        : `background:${AVA_BG[i%8]};color:${AVA_TEXT[i%8]}`;
                    const avTxt = u.user_image ? "" : (u.initials || "?");
                    // session_name stored in data-* — no special chars in onclick
                    return `
                    <div class="wfh-card ${mk}${u.inactivity_flag?" flagged":""}" data-session="${u.session_name||""}">
                        <div class="wfh-card-top">
                            <div class="wfh-av" style="${avBg}">${avTxt}</div>
                            <div style="flex:1;min-width:0">
                                <div class="wfh-card-name">${u.display_name||u.user||"Unknown"}</div>
                                <div class="wfh-card-sub">${u.department||""}${u.designation?" · "+u.designation:""}</div>
                            </div>
                            <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px">
                                <span class="wfh-pill ${pill}">${u.work_mode||"—"}</span>
                                ${flag}${gps}
                            </div>
                        </div>
                        <div class="wfh-card-body">
                            <div class="wfh-stat-row">
                                <div class="wfh-stat-item"><span class="wfh-stat-label">Check-in</span><span class="wfh-stat-val">${u.check_in_str||"—"}</span></div>
                                <div class="wfh-stat-item"><span class="wfh-stat-label">Check-out</span><span class="wfh-stat-val">${u.check_out_str||"—"}</span></div>
                                <div class="wfh-stat-item"><span class="wfh-stat-label">Hours</span><span class="wfh-stat-val" style="color:${color}">${u.total_hours||0}h</span></div>
                                <div class="wfh-stat-item"><span class="wfh-stat-label">Actions</span><span class="wfh-stat-val">${u.activity_count||0}</span></div>
                                <div class="wfh-stat-item"><span class="wfh-stat-label">Points</span><span class="wfh-stat-val" style="color:${color}">${u.activity_points||0}</span></div>
                            </div>
                            <div class="wfh-pts-bar"><div class="wfh-pts-fill" style="width:${pct}%;background:${color}"></div></div>
                            ${u.location_label?`<div style="font-size:11px;color:#6c757d;margin-top:8px">📍 ${u.location_label}</div>`:""}
                            <div style="font-size:10px;color:#6c757d;margin-top:6px">
                                Last active: ${u.last_active_str||"—"}${u.last_action_doc?" · "+u.last_action_doc:""}
                            </div>
                        </div>
                    </div>`;
                }).join("")}
            </div>`);

        // Delegated click — safe with any session name
        $("#wfh-main-content").off("click",".wfh-card").on("click", ".wfh-card", function () {
            const s = $(this).data("session");
            if (s) frappe.set_route("Form", "Work Session", s);
        });
    }

    _render_activity(logs) {
        const mc = { Sales:"#534AB7", Accounts:"#185FA5", CRM:"#D4537E", Buying:"#BA7517", Stock:"#1D9E75", Other:"#888780" };
        if (!logs?.length) {
            $("#wfh-activity").html(`<div class="wfh-not-in">No activity recorded yet today</div>`);
            return;
        }
        $("#wfh-activity").html(`
            <div style="background:var(--card-bg,#fff);border:1px solid var(--border-color,#e0e0e0);border-radius:14px;padding:12px 16px">
                ${logs.map(l => `
                <div class="wfh-act-item">
                    <div class="wfh-act-dot" style="background:${mc[l.module]||mc.Other}"></div>
                    <div style="flex:1;min-width:0;overflow:hidden">
                        <div style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
                            <b>${l.employee_name||"Unknown"}</b> → ${l.reference_doctype||""}
                        </div>
                        <div style="color:#6c757d;font-size:10px">${String(l.timestamp||"").slice(11,16)||"—"} · ${l.action||""}</div>
                    </div>
                    <span class="wfh-act-pts">+${l.points||0}</span>
                </div>`).join("")}
            </div>`);
    }

    _render_not_in(employees) {
        if (!employees.length) {
            $("#wfh-not-in").html(`
                <div class="wfh-not-in" style="border-color:#86efac">
                    ✓ Everyone scheduled for WFH has checked in
                </div>`);
            return;
        }
        $("#wfh-not-in").html(`
            <div style="background:var(--card-bg,#fff);border:1px solid #fde68a;border-radius:14px;padding:12px 16px">
                ${employees.map(e => `
                <div style="display:flex;align-items:center;gap:10px;padding:7px 0;border-bottom:.5px solid #e0e0e0;font-size:12px">
                    <div class="wfh-av" style="width:28px;height:28px;font-size:11px;background:#FEF3C7;color:#92400E">
                        ${(e.employee_name||"?")[0].toUpperCase()}
                    </div>
                    <div style="flex:1">
                        <div style="font-weight:600">${e.employee_name||"Unknown"}</div>
                        <div style="color:#6c757d;font-size:10px">${e.department||""}</div>
                    </div>
                    <span class="wfh-pill r">Not in</span>
                </div>`).join("")}
            </div>`);
    }

    _export_csv() {
        if (!this.data) return;
        let csv = "Name,Work Mode,Dept,Check-in,Check-out,Hours,Points,Actions,GPS\n";
        (this.data.users||[]).forEach(u => {
            csv += `"${u.display_name||""}","${u.work_mode||""}","${u.department||""}","${u.check_in_str||""}","${u.check_out_str||""}","${u.total_hours||0}","${u.activity_points||0}","${u.activity_count||0}","${u.gps_verified?"Yes":"No"}"\n`;
        });
        const a = Object.assign(document.createElement("a"), {
            href: URL.createObjectURL(new Blob([csv], {type:"text/csv"})),
            download: `wfh-dashboard-${this._date}.csv`
        });
        a.click();
    }

    _start_clock() {
        const tick = () => {
            const n = new Date(), el = document.getElementById("wfh-clock");
            if (el) el.innerHTML = `<span>${n.toLocaleDateString("en-GB",{weekday:"long",day:"numeric",month:"long",year:"numeric"})}</span> &middot; <span>${n.toLocaleTimeString("en-GB")}</span>`;
        };
        tick(); setInterval(tick, 1000);
    }

    _start_auto_refresh() {
        this._interval = setInterval(() => this.load(), 30000);
    }
}