//frappe.pages['live-dashboard'].on_page_load = function(wrapper) {
//	var page = frappe.ui.make_app_page({
//		parent: wrapper,
//		title: 'Live Dashboard',
//		single_column: true
//	});
//}


/**
 * Live Dashboard — Page JS
 * Ecclesia Module
 * Path: ecclesia/page/live_dashboard/live_dashboard.js
 *
 * Shows ALL logged-in users (employee or not) in real time.
 * WFH and WFO sessions shown side by side.
 * Auto-refreshes every 30 seconds.
 */

frappe.pages["live-dashboard"].on_page_load = function (wrapper) {
    new LiveDashboard(wrapper);
};

class LiveDashboard {
    constructor(wrapper) {
        this.wrapper    = wrapper;
        this.data       = null;
        this._interval  = null;
        this._dept      = "";
        this._date      = frappe.datetime.get_today();
        this._tab       = "all";   // all | wfh | wfo | field

        this.page = frappe.ui.make_app_page({
            parent: wrapper,
            title: "Live Dashboard",
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
        if (document.getElementById("ld-styles")) return;
        const el = document.createElement("style");
        el.id = "ld-styles";
        el.textContent = `
.ld-page{padding:0;background:var(--bg-color)}
.ld-hero{background:linear-gradient(135deg,#534AB7 0%,#185FA5 100%);color:#fff;
         padding:24px 28px 20px;margin:-15px -15px 20px;border-radius:0 0 12px 12px}
.ld-hero h1{font-size:20px;font-weight:500;color:#fff;margin:0 0 5px;
            display:flex;align-items:center;gap:10px}
.ld-hero p{margin:0;font-size:12px;color:rgba(255,255,255,.8)}
.ld-live{width:8px;height:8px;border-radius:50%;background:#5DCAA5;
         display:inline-block;animation:ld-pulse 2s infinite}
@keyframes ld-pulse{0%,100%{opacity:1}50%{opacity:.3}}
.ld-badge{background:rgba(255,255,255,.2);color:#fff;font-size:10px;
          padding:2px 9px;border-radius:20px}
.ld-kgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));
          gap:10px;margin-bottom:18px}
.ld-kpi{background:var(--card-bg);border:0.5px solid var(--border-color);
        border-radius:10px;padding:13px 15px;position:relative;overflow:hidden}
.ld-kpi::after{content:'';position:absolute;left:0;top:0;bottom:0;width:3px}
.ld-kpi.p::after{background:#534AB7}.ld-kpi.t::after{background:#1D9E75}
.ld-kpi.b::after{background:#185FA5}.ld-kpi.a::after{background:#BA7517}
.ld-kpi.r::after{background:#D85A30}.ld-kpi.g::after{background:#639922}
.ld-klabel{font-size:10px;color:var(--text-muted);margin-bottom:4px;
           text-transform:uppercase;letter-spacing:.3px}
.ld-kval{font-size:20px;font-weight:500;line-height:1.1;margin-bottom:2px}
.ld-kpi.p .ld-kval{color:#534AB7}.ld-kpi.t .ld-kval{color:#0F6E56}
.ld-kpi.b .ld-kval{color:#185FA5}.ld-kpi.a .ld-kval{color:#633806}
.ld-kpi.r .ld-kval{color:#993C1D}.ld-kpi.g .ld-kval{color:#3B6D11}
.ld-ksub{font-size:10px;color:var(--text-muted)}
.ld-tabs{display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap}
.ld-tab{padding:6px 14px;border-radius:20px;font-size:12px;font-weight:500;
        cursor:pointer;border:0.5px solid var(--border-color);
        background:var(--card-bg);color:var(--text-muted);transition:all .2s}
.ld-tab:hover{background:var(--control-bg)}
.ld-tab.active{background:#534AB7;color:#fff;border-color:#534AB7}
.ld-tab.wfo-tab.active{background:#1D9E75;border-color:#1D9E75}
.ld-tab.field-tab.active{background:#BA7517;border-color:#BA7517}
.ld-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:12px;margin-bottom:18px}
.ld-card{background:var(--card-bg);border:0.5px solid var(--border-color);
         border-radius:12px;overflow:hidden;transition:box-shadow .2s;cursor:pointer}
.ld-card:hover{box-shadow:0 4px 16px rgba(0,0,0,.10)}
.ld-card.wfh .ld-card-top{border-left:3px solid #534AB7}
.ld-card.wfo .ld-card-top{border-left:3px solid #1D9E75}
.ld-card.hybrid .ld-card-top{border-left:3px solid #BA7517}
.ld-card.field .ld-card-top{border-left:3px solid #BA7517}
.ld-card.flagged{border-color:#f59e0b;box-shadow:0 0 0 1px #f59e0b}
.ld-card-top{display:flex;align-items:center;gap:10px;padding:12px 14px}
.ld-av{width:36px;height:36px;border-radius:50%;display:flex;align-items:center;
       justify-content:center;font-size:13px;font-weight:500;flex-shrink:0;
       background-size:cover;background-position:center}
.ld-card-name{font-size:13px;font-weight:500;white-space:nowrap;
              overflow:hidden;text-overflow:ellipsis}
.ld-card-sub{font-size:11px;color:var(--text-muted)}
.ld-card-body{padding:0 14px 12px}
.ld-stat-row{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:8px;font-size:12px}
.ld-stat-item{display:flex;flex-direction:column;gap:1px}
.ld-stat-label{font-size:10px;color:var(--text-muted)}
.ld-stat-val{font-weight:500;color:var(--text-primary)}
.ld-pill{display:inline-block;font-size:10px;font-weight:500;padding:2px 7px;border-radius:20px}
.ld-pill.g{background:#EAF3DE;color:#27500A}.ld-pill.b{background:#E6F1FB;color:#0C447C}
.ld-pill.p{background:#EEEDFE;color:#3C3489}.ld-pill.a{background:#FAEEDA;color:#633806}
.ld-pill.r{background:#FCEBEB;color:#791F1F}.ld-pill.t{background:#E1F5EE;color:#085041}
.ld-pill.gray{background:#F1EFE8;color:#444441}
.ld-pts-bar{height:3px;background:var(--border-color);border-radius:2px;
            overflow:hidden;margin-top:6px}
.ld-pts-fill{height:3px;border-radius:2px;transition:width .5s}
.ld-act-feed{padding:0 4px}
.ld-act-item{display:flex;align-items:center;gap:8px;padding:7px 0;
             border-bottom:0.5px solid var(--border-color);font-size:11px}
.ld-act-item:last-child{border-bottom:none}
.ld-act-dot{width:6px;height:6px;border-radius:50%;flex-shrink:0}
.ld-act-pts{margin-left:auto;font-weight:500;color:#0F6E56;font-size:11px}
.ld-not-in{background:var(--card-bg);border:0.5px dashed var(--border-color);
           border-radius:12px;padding:10px 14px;font-size:12px;color:var(--text-muted)}
.ld-section-title{font-size:12px;font-weight:500;color:var(--text-muted);
                  margin-bottom:8px;display:flex;align-items:center;gap:6px}
.ld-two-col{display:grid;grid-template-columns:2fr 1fr;gap:14px;margin-bottom:14px}
@media(max-width:900px){.ld-two-col{grid-template-columns:1fr}}
        `;
        document.head.appendChild(el);
    }

    // ── Page actions ────────────────────────────────────────────────────────────
    _setup_actions() {
        this.page.set_secondary_action("Refresh", () => this.load(), "octicon octicon-sync");
        this.page.add_menu_item("New Work Session",   () => frappe.new_doc("Work Session"));
        this.page.add_menu_item("New External Task",  () => frappe.new_doc("External Task"));
        this.page.add_menu_item("WFH Schedules",      () => frappe.set_route("List", "WFH Schedule"));
        this.page.add_menu_item("WFH Requests",       () => frappe.set_route("List", "WFH Request"));
        this.page.add_menu_item("Activity Logs",      () => frappe.set_route("List", "Work Activity Log"));
    }

    // ── Layout ─────────────────────────────────────────────────────────────────
    _build_layout() {
        $(this.page.main).html(`
<div class="ld-page">
  <div class="ld-hero">
    <h1><span class="ld-live" aria-hidden="true"></span> Live Dashboard
        <span class="ld-badge">Ecclesia</span></h1>
    <p id="ld-clock">Loading...</p>
  </div>
  <div style="padding:0 4px">
    <div style="display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap;align-items:flex-end">
      <div id="ld-filter-dept" style="min-width:180px"></div>
      <div id="ld-filter-date" style="min-width:140px"></div>
      <button class="btn btn-default btn-sm" id="ld-today-btn">Today</button>
    </div>
    <div class="ld-kgrid" id="ld-kpis"></div>
    <div class="ld-tabs" id="ld-tabs"></div>
    <div id="ld-main-content"></div>
    <div class="ld-two-col">
      <div>
        <div class="ld-section-title"><i class="ti ti-activity" aria-hidden="true"></i> Recent activity</div>
        <div id="ld-activity"></div>
      </div>
      <div>
        <div class="ld-section-title"><i class="ti ti-calendar-check" aria-hidden="true"></i> Not yet checked in</div>
        <div id="ld-not-in"></div>
      </div>
    </div>
  </div>
</div>`);
    }

    // ── Filters ─────────────────────────────────────────────────────────────────
    _init_filters() {
        this._ctrl_dept = frappe.ui.form.make_control({
            parent: $("#ld-filter-dept"),
            df: { fieldtype: "Link", options: "Department", label: "Department" },
            render_input: true,
        });
        this._ctrl_date = frappe.ui.form.make_control({
            parent: $("#ld-filter-date"),
            df: { fieldtype: "Date", label: "Date", default: frappe.datetime.get_today() },
            render_input: true,
        });
        this._ctrl_dept.$input.on("change", () => {
            this._dept = this._ctrl_dept.get_value();
            this.load();
        });
        this._ctrl_date.$input.on("change", () => {
            this._date = this._ctrl_date.get_value() || frappe.datetime.get_today();
            this.load();
        });
        $("#ld-today-btn").on("click", () => {
            this._date = frappe.datetime.get_today();
            this._ctrl_date?.set_value(this._date);
            this.load();
        });
    }

    // ── Load ───────────────────────────────────────────────────────────────────
    async load() {
        try {
            const r = await frappe.call({
                method: "ecclesia.ecclesia.page.live_dashboard.live_dashboard.get_live_data",
                args: { date: this._date, department: this._dept },
            });
            if (r.message) {
                this.data = r.message;
                this._render();
            }
        } catch (e) {
            console.error("Live Dashboard load error", e);
        }
    }

    // ── Render ─────────────────────────────────────────────────────────────────
    _render() {
        const d = this.data;
        this._render_kpis(d.kpis);
        this._render_tabs(d.kpis);
        this._render_user_grid();
        this._render_activity(d.recent_activity);
        this._render_not_in(d.schedule_today?.not_checked_in_wfh || []);
    }

    _render_kpis(k) {
        const cards = [
            { cls: "p", label: "Active now",     val: k.total_active,  sub: "All modes" },
            { cls: "p", label: "WFH",             val: k.wfh_count,    sub: "Working from home" },
            { cls: "t", label: "WFO",             val: k.wfo_count,    sub: "In office" },
            { cls: "a", label: "Field / Hybrid",  val: k.field_count,  sub: "Off-site" },
            { cls: "b", label: "Total hours",     val: `${k.total_hours}h`, sub: `Avg ${k.avg_hours}h/person` },
            { cls: "g", label: "Activity points", val: k.total_points, sub: `${k.total_actions} actions` },
            { cls: "r", label: "Flagged",         val: k.flagged_count, sub: "Idle > threshold" },
        ];
        $("#ld-kpis").html(cards.map(c => `
            <div class="ld-kpi ${c.cls}">
                <div class="ld-klabel">${c.label}</div>
                <div class="ld-kval">${c.val}</div>
                <div class="ld-ksub">${c.sub}</div>
            </div>`).join(""));
    }

    _render_tabs(k) {
        const tabs = [
            { key: "all",   label: `All (${k.total_active})`,   cls: "" },
            { key: "wfh",   label: `WFH (${k.wfh_count})`,      cls: "" },
            { key: "wfo",   label: `WFO (${k.wfo_count})`,      cls: "wfo-tab" },
            { key: "field", label: `Field (${k.field_count})`,   cls: "field-tab" },
        ];
        if (k.flagged_count) {
            tabs.push({ key: "flagged", label: `Flagged (${k.flagged_count})`, cls: "flag-tab" });
        }
        $("#ld-tabs").html(tabs.map(t => `
            <div class="ld-tab ${t.cls}${this._tab === t.key ? " active" : ""}"
                 data-tab="${t.key}">${t.label}</div>`).join(""));
        $("#ld-tabs").off("click").on("click", ".ld-tab", (e) => {
            this._tab = $(e.currentTarget).data("tab");
            this._render_tabs(k);
            this._render_user_grid();
        });
    }

    _render_user_grid() {
        const d = this.data;
        let users = d.users || [];
        if (this._tab === "wfh")    users = d.wfh_users;
        if (this._tab === "wfo")    users = d.wfo_users;
        if (this._tab === "field")  users = d.field_users;
        if (this._tab === "flagged") users = d.flagged;

        if (!users.length) {
            $("#ld-main-content").html(
                `<div style="text-align:center;padding:40px 20px;color:var(--text-muted);font-size:13px">
                    No active sessions for this filter.</div>`
            );
            return;
        }

        const maxPts = Math.max(...users.map(u => u.activity_points), 1);
        const modeColors = {
            WFH: "#534AB7", WFO: "#1D9E75",
            Hybrid: "#BA7517", Field: "#BA7517"
        };
        const modePills = {
            WFH: "p", WFO: "t", Hybrid: "a", Field: "a"
        };
        const AVA_BG   = ["#EEEDFE","#E1F5EE","#E6F1FB","#FAEEDA","#FAECE7"];
        const AVA_TEXT = ["#3C3489","#085041","#0C447C","#633806","#712B13"];

        $("#ld-main-content").html(`
            <div class="ld-grid">
                ${users.map((u, i) => {
                    const modeKey = u.work_mode?.replace(" ", "").toLowerCase();
                    const pct     = Math.round(u.activity_points / maxPts * 100);
                    const color   = modeColors[u.work_mode] || "#888780";
                    const pill    = modePills[u.work_mode] || "gray";
                    const flagBadge = u.inactivity_flag
                        ? `<span class="ld-pill a" style="font-size:9px">⚑ Idle</span>` : "";
                    const gpsIcon = u.gps_verified
                        ? `<i class="ti ti-map-pin" style="font-size:11px;color:#1D9E75" title="GPS verified"></i>`
                        : "";
                    const avBg = u.user_image
                        ? `background-image:url(${u.user_image});background-color:transparent`
                        : `background:${AVA_BG[i % 5]};color:${AVA_TEXT[i % 5]}`;
                    const avContent = u.user_image ? "" : u.initials;

                    return `
                    <div class="ld-card ${modeKey}${u.inactivity_flag ? " flagged" : ""}"
                         data-user="${u.user}" onclick="frappe.set_route('Form','Work Session','${u.session_name}')">
                        <div class="ld-card-top">
                            <div class="ld-av" style="${avBg}">${avContent}</div>
                            <div style="flex:1;min-width:0">
                                <div class="ld-card-name">${u.display_name}</div>
                                <div class="ld-card-sub">${u.department || u.user}${u.designation ? " · "+u.designation : ""}</div>
                            </div>
                            <div style="display:flex;flex-direction:column;align-items:flex-end;gap:3px">
                                <span class="ld-pill ${pill}">${u.work_mode}</span>
                                ${flagBadge}
                                ${gpsIcon}
                            </div>
                        </div>
                        <div class="ld-card-body">
                            <div class="ld-stat-row">
                                <div class="ld-stat-item">
                                    <span class="ld-stat-label">Check-in</span>
                                    <span class="ld-stat-val">${u.check_in_str}</span>
                                </div>
                                <div class="ld-stat-item">
                                    <span class="ld-stat-label">Check-out</span>
                                    <span class="ld-stat-val">${u.check_out_str}</span>
                                </div>
                                <div class="ld-stat-item">
                                    <span class="ld-stat-label">Hours</span>
                                    <span class="ld-stat-val" style="color:${color}">${u.total_hours}h</span>
                                </div>
                                <div class="ld-stat-item">
                                    <span class="ld-stat-label">Actions</span>
                                    <span class="ld-stat-val">${u.activity_count}</span>
                                </div>
                                <div class="ld-stat-item">
                                    <span class="ld-stat-label">Points</span>
                                    <span class="ld-stat-val" style="color:${color}">${u.activity_points}</span>
                                </div>
                            </div>
                            <div class="ld-pts-bar">
                                <div class="ld-pts-fill" style="width:${pct}%;background:${color}"></div>
                            </div>
                            ${u.location_label
                                ? `<div style="font-size:11px;color:var(--text-muted);margin-top:6px">
                                       <i class="ti ti-map-pin" aria-hidden="true"></i> ${u.location_label}</div>`
                                : ""}
                            <div style="font-size:10px;color:var(--text-muted);margin-top:5px">
                                Last active: ${u.last_active_str}
                                ${u.last_action_doc ? `· ${u.last_action_doc}` : ""}
                            </div>
                        </div>
                    </div>`;
                }).join("")}
            </div>`);
    }

    _render_activity(logs) {
        const mod_colors = {
            Sales: "#534AB7", Accounts: "#185FA5",
            CRM: "#D4537E", Buying: "#BA7517",
            Stock: "#1D9E75", Other: "#888780"
        };
        if (!logs?.length) {
            $("#ld-activity").html('<p style="color:var(--text-muted);font-size:12px">No activity yet today.</p>');
            return;
        }
        $("#ld-activity").html(`
            <div style="background:var(--card-bg);border:0.5px solid var(--border-color);border-radius:10px;padding:12px 14px">
                ${logs.map(l => `
                <div class="ld-act-item">
                    <div class="ld-act-dot" style="background:${mod_colors[l.module] || "#888780"}"></div>
                    <div style="flex:1;min-width:0;overflow:hidden">
                        <div style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
                            <span style="font-weight:500">${l.employee_name}</span>
                            → ${l.reference_doctype}
                        </div>
                        <div style="color:var(--text-muted)">${String(l.timestamp || "").slice(11,16)} · ${l.action}</div>
                    </div>
                    <span class="ld-act-pts">+${l.points}</span>
                </div>`).join("")}
            </div>`);
    }

    _render_not_in(employees) {
        if (!employees.length) {
            $("#ld-not-in").html(
                '<div class="ld-not-in">Everyone scheduled for WFH today has checked in ✓</div>'
            );
            return;
        }
        $("#ld-not-in").html(`
            <div style="background:var(--card-bg);border:0.5px solid #fde68a;border-radius:10px;padding:12px 14px">
                ${employees.map(e => `
                <div style="display:flex;align-items:center;gap:8px;padding:6px 0;
                            border-bottom:0.5px solid var(--border-color);font-size:12px">
                    <i class="ti ti-clock" style="color:#d97706" aria-hidden="true"></i>
                    <div>
                        <div style="font-weight:500">${e.employee_name}</div>
                        <div style="color:var(--text-muted)">${e.department || ""}</div>
                    </div>
                    <span class="ld-pill a" style="margin-left:auto">Not in</span>
                </div>`).join("")}
            </div>`);
    }

    // ── Clock & auto-refresh ────────────────────────────────────────────────────
    _start_clock() {
        const tick = () => {
            const n = new Date();
            const el = document.getElementById("ld-clock");
            if (el) {
                el.textContent = n.toLocaleDateString("en-GB", {
                    weekday: "long", day: "numeric", month: "long"
                }) + " · " + n.toLocaleTimeString("en-GB");
            }
        };
        tick();
        setInterval(tick, 1000);
    }

    _start_auto_refresh() {
        this._interval = setInterval(() => this.load(), 30000);
    }
}