// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

// Work Session — Client Script
// Ecclesia Module
//
// KEY DESIGN:
//   Check-in Time = ERPNext login time (auto-captured via on_login hook).
//   The field is READ-ONLY to users — they cannot manually enter it.
//   This prevents time fraud. The only way to get a check-in time is
//   to have actually logged into ERPNext that day.
//
//   Work mode is auto-detected from WFH Schedule.
//   GPS is optional — denial never blocks the session.

frappe.ui.form.on("Work Session", {

    // ── On load ───────────────────────────────────────────────────────────────
    onload(frm) {
        // Lock check-in time — never editable by user
        frm.set_df_property("check_in_time", "read_only", 1);
        frm.set_df_property("check_out_time", "read_only", 0); // checkout is manual

        // Restrict user field to self unless HR/Manager
        if (!frappe.user.has_role(["HR Manager", "System Manager", "Line Manager"])) {
            frm.set_query("user", () => ({ filters: { name: frappe.session.user } }));
        }

        if (frm.is_new()) {
            frm.set_value("user",  frappe.session.user);
            frm.set_value("date",  frappe.datetime.get_today());
            // Auto-detect work mode from schedule
            frm.trigger("_detect_work_mode");
        }
    },

    // ── Refresh ───────────────────────────────────────────────────────────────
    refresh(frm) {
        frm.trigger("_set_indicator");
        frm.trigger("_setup_buttons");
        frm.trigger("_render_time_badge");
        frm.trigger("_show_gps_status");

        // Show read-only notice on check_in_time
        const $field = frm.get_field("check_in_time");
        if ($field && $field.$wrapper) {
            $field.$wrapper.find(".ld-login-note").remove();
            $field.$wrapper.append(
                `<div class="ld-login-note" style="font-size:11px;color:var(--text-muted);
                    margin-top:3px;padding:3px 6px;background:var(--control-bg);
                    border-radius:4px;border-left:2px solid #534AB7">
                    <i class="ti ti-lock" aria-hidden="true"></i>
                    Captured automatically at ERPNext login — not editable.
                </div>`
            );
        }
    },

    user(frm) {
        if (frm.doc.user) frm.trigger("_detect_work_mode");
    },

    date(frm) {
        if (frm.doc.user && frm.doc.date) frm.trigger("_detect_work_mode");
    },

    // ── Auto-detect work mode from WFH Schedule ───────────────────────────────
    _detect_work_mode(frm) {
        if (!frm.is_new()) return;
        frappe.call({
            method: "ecclesia.ecclesia.doctype.wfh_schedule.wfh_schedule.get_employee_schedule",
            args: { date: frm.doc.date || frappe.datetime.get_today() },
            callback(r) {
                if (!r.message) return;
                const m = r.message;
                if (m.work_mode && m.work_mode !== "Unknown") {
                    frm.set_value("work_mode", m.work_mode);
                    if (m.schedule) {
                        frm.set_value("wfh_schedule", m.schedule.name || "");
                    }
                    frappe.show_alert({
                        message: __("Work mode auto-detected: {0}", [m.work_mode]),
                        indicator: m.is_wfh ? "green" : "blue"
                    }, 4);
                }
            }
        });
    },

    // ── Live time badge ───────────────────────────────────────────────────────
    _render_time_badge(frm) {
        frm.$wrapper.find(".ws-time-badge").remove();
        if (!frm.doc.check_in_time) return;

        const cin = new Date(frm.doc.check_in_time);
        const now = new Date();
        const hrs = ((now - cin) / 3600000).toFixed(1);
        const modeColors = {
            WFH: "#534AB7", WFO: "#1D9E75", Hybrid: "#BA7517", Field: "#BA7517"
        };
        const color = modeColors[frm.doc.work_mode] || "#534AB7";
        const badge = `
            <div class="ws-time-badge" style="display:flex;gap:12px;flex-wrap:wrap;
                padding:12px 16px;background:var(--control-bg);border-radius:8px;
                border:0.5px solid var(--border-color);margin:8px 0;">
                <div style="text-align:center">
                    <div style="font-size:20px;font-weight:500;color:${color}">
                        ${frm.doc.check_in_time ? frm.doc.check_in_time.slice(11,16) : "—"}
                    </div>
                    <div style="font-size:11px;color:var(--text-muted)">Login time</div>
                </div>
                <div style="text-align:center">
                    <div style="font-size:20px;font-weight:500;color:${color}">
                        ${frm.doc.check_out_time ? frm.doc.check_out_time.slice(11,16) : "—"}
                    </div>
                    <div style="font-size:11px;color:var(--text-muted)">Check-out</div>
                </div>
                <div style="text-align:center">
                    <div style="font-size:20px;font-weight:500;color:${color}">${hrs}h</div>
                    <div style="font-size:11px;color:var(--text-muted)">
                        ${frm.doc.status === "Open" ? "Running" : "Total"}
                    </div>
                </div>
                <div style="text-align:center">
                    <div style="font-size:16px;font-weight:500;color:${color}">
                        ${frm.doc.work_mode || "—"}
                    </div>
                    <div style="font-size:11px;color:var(--text-muted)">Mode</div>
                </div>
                ${frm.doc.location_label ? `
                <div style="text-align:center">
                    <div style="font-size:13px;font-weight:500;color:var(--text-primary)">
                        <i class="ti ti-map-pin" aria-hidden="true"></i> ${frm.doc.location_label}
                    </div>
                    <div style="font-size:11px;color:var(--text-muted)">Location</div>
                </div>` : ""}
            </div>`;

        frm.layout.wrapper.find(".form-page").find(".ws-time-badge").remove();
        frm.fields_dict.check_in_time.$wrapper.closest(".form-section").after(badge);

        // Live update if open
        if (frm.doc.status === "Open" && !frm._timer) {
            frm._timer = setInterval(() => frm.trigger("_render_time_badge"), 60000);
        }
    },

    // ── GPS (optional) ────────────────────────────────────────────────────────
    _show_gps_status(frm) {
        frm.dashboard.clear_comment();
        if (frm.doc.gps_verified) {
            frm.dashboard.add_comment(
                `<i class="ti ti-map-pin"></i> GPS: ${(frm.doc.latitude||0).toFixed(4)}, ` +
                `${(frm.doc.longitude||0).toFixed(4)} (±${frm.doc.gps_accuracy||"?"}m)`,
                "green", true
            );
        }
    },

    _try_gps(frm) {
        if (!navigator.geolocation) {
            frappe.show_alert({ message: __("Geolocation not supported."), indicator: "gray" }, 4);
            return;
        }
        frappe.show_alert({ message: __("Requesting location..."), indicator: "blue" }, 3);
        navigator.geolocation.getCurrentPosition(
            pos => {
                frappe.call({
                    method: "ecclesia.ecclesia.doctype.work_session.work_session.update_gps",
                    args: {
                        session_name: frm.doc.name,
                        latitude:  pos.coords.latitude,
                        longitude: pos.coords.longitude,
                        accuracy:  pos.coords.accuracy,
                    },
                    callback() {
                        frappe.show_alert({ message: __("GPS location saved."), indicator: "green" }, 4);
                        frm.reload_doc();
                    }
                });
            },
            err => {
                const msgs = {
                    1: "Location permission denied — session continues normally.",
                    2: "Location unavailable — session continues normally.",
                    3: "Location timed out — session continues normally.",
                };
                frappe.show_alert({ message: __(msgs[err.code] || "GPS error."), indicator: "gray" }, 5);
            },
            { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
        );
    },

    // ── Buttons ───────────────────────────────────────────────────────────────
    _setup_buttons(frm) {
        frm.clear_custom_buttons();

        if (frm.doc.status === "Open" && !frm.is_new()) {
            frm.add_custom_button(__("Check Out Now"), () => {
                frappe.confirm(
                    __("Record check-out at {0}?", [frappe.datetime.now_datetime().slice(11,16)]),
                    () => {
                        frappe.call({
                            method: "ecclesia.ecclesia.doctype.work_session.work_session.check_out",
                            args: { session_name: frm.doc.name },
                            callback() { frm.reload_doc(); }
                        });
                    }
                );
            }).addClass("btn-primary");
        }

        if (frm.doc.status === "Open" && !frm.doc.gps_verified && !frm.is_new()) {
            if (navigator.geolocation) {
                frm.add_custom_button(__("Add GPS"), () => frm.trigger("_try_gps"));
            }
        }

        if (!frm.is_new()) {
            frm.add_custom_button(__("Activity Logs"), () => {
                frappe.route_options = { session: frm.doc.name };
                frappe.set_route("List", "Work Activity Log");
            });
            frm.add_custom_button(__("External Tasks"), () => {
                frappe.route_options = { work_session: frm.doc.name };
                frappe.set_route("List", "External Task");
            });
            frm.add_custom_button(__("Daily Summary"), () => {
                frappe.route_options = {
                    employee: frm.doc.employee,
                    date: frm.doc.date
                };
                frappe.set_route("List", "WFH Daily Summary");
            });
        }
    },

    _set_indicator(frm) {
        const map = {
            Open:      ["Open",      "blue"],
            Closed:    ["Closed",    "green"],
            Flagged:   ["Flagged",   "orange"],
            Cancelled: ["Cancelled", "gray"],
        };
        const [label, color] = map[frm.doc.status] || ["Draft", "gray"];
        frm.page.set_indicator(label, color);
    }
});

// ── List view ─────────────────────────────────────────────────────────────────
frappe.listview_settings["Work Session"] = {
    get_indicator(doc) {
        const map = {
            Open:      ["Open",    "blue"],
            Closed:    ["Closed",  "green"],
            Flagged:   ["Flagged", "orange"],
        };
        return map[doc.status] || [doc.status, "gray"];
    },
    formatters: {
        work_mode(val) {
            const colors = {
                WFH: "#534AB7", WFO: "#1D9E75", Hybrid: "#BA7517", Field: "#BA7517"
            };
            const pills = {
                WFH: "#EEEDFE", WFO: "#E1F5EE", Hybrid: "#FAEEDA", Field: "#FAEEDA"
            };
            return val ? `<span style="background:${pills[val]||"#F1EFE8"};
                color:${colors[val]||"#444"};padding:2px 8px;border-radius:12px;
                font-size:11px;font-weight:500">${val}</span>` : "—";
        },
        total_hours(val) {
            const h = parseFloat(val||0);
            const c = h>=7?"#16a34a":h>=4?"#d97706":"#dc2626";
            return `<span style="color:${c};font-weight:500">${h}h</span>`;
        }
    },
    onload(listview) {
        listview.page.add_inner_button(__("My Session Today"), () => {
            frappe.call({
                method: "ecclesia.ecclesia.doctype.work_session.work_session.get_my_session",
                callback(r) {
                    if (r.message) {
                        frappe.set_route("Form", "Work Session", r.message.name);
                    } else {
                        frappe.msgprint(__("No session found for today. You will be checked in automatically on next login."));
                    }
                }
            });
        });
    }
};