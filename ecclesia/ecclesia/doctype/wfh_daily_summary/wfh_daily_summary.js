// WFH Daily Summary — Client JS
// Ecclesia Module

frappe.ui.form.on("WFH Daily Summary", {

    onload(frm) {
        // Lock employee to current user (unless HR/Manager)
        if (!frappe.user.has_role(["HR Manager", "System Manager", "Line Manager"])) {
            frm.set_query("employee", () => ({
                filters: { user_id: frappe.session.user }
            }));
        }
        frm.set_query("session", () => {
            const emp = frm.doc.employee;
            return emp
                ? { filters: { employee: emp, status: ["in", ["Open", "Closed", "Flagged"]] } }
                : {};
        });
    },

    refresh(frm) {
        frm.trigger("_set_indicator");
        frm.trigger("_setup_buttons");
        frm.trigger("_render_score_card");

        // Show flag notes prominently if flagged
        if (frm.doc.status === "Flagged" && frm.doc.flag_notes) {
            frm.dashboard.add_comment(
                `⚑ <b>Flagged:</b> ${frm.doc.flag_notes}`, "orange", true
            );
        }
    },

    employee(frm) {
        if (frm.doc.employee && frm.doc.date) {
            frm.trigger("_auto_link_session");
        }
    },

    date(frm) {
        if (frm.doc.employee && frm.doc.date) {
            frm.trigger("_auto_link_session");
        }
    },

    session(frm) {
        if (frm.doc.session) {
            // Pull hours and wfh_request from session
            frappe.db.get_value("WFH Session", frm.doc.session,
                ["total_hours", "wfh_request", "check_in_time", "check_out_time", "status"],
                (r) => {
                    if (r) {
                        frm.set_value("hours_logged", r.total_hours || 0);
                        frm.set_value("wfh_request",  r.wfh_request || "");

                        if (r.status === "Open") {
                            frappe.show_alert({
                                message: __("Your session is still open. Don't forget to check out."),
                                indicator: "orange"
                            }, 6);
                        }
                    }
                }
            );
            // Pull today's activity score
            frm.trigger("_pull_activity_score");
        }
    },

    self_rating(frm) {
        frm.trigger("_preview_composite");
    },

    // ── Private ─────────────────────────────────────────────────────────────

    _auto_link_session(frm) {
        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "WFH Session",
                filters: {
                    employee: frm.doc.employee,
                    date:     frm.doc.date,
                    status:   ["in", ["Open", "Closed", "Flagged"]],
                    docstatus: ["!=", 2]
                },
                fieldname: "name"
            },
            callback(r) {
                if (r.message && r.message.name) {
                    frm.set_value("session", r.message.name);
                    frappe.show_alert({
                        message: __("Session auto-linked: {0}", [r.message.name]),
                        indicator: "green"
                    }, 4);
                } else {
                    frappe.msgprint({
                        title: __("No Session Found"),
                        message: __("No WFH Session found for {0} on {1}. Please check in first.", [
                            frm.doc.employee, frm.doc.date
                        ]),
                        indicator: "orange"
                    });
                }
            }
        });
    },

    _pull_activity_score(frm) {
        if (!frm.doc.employee || !frm.doc.date) return;
        frappe.db.sql ? null :  // frappe.db.sql not available client-side; use API
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Work Activity Log",
                filters: { employee: frm.doc.employee, date: frm.doc.date },
                fields:  ["sum(points) as total_points", "sum(business_value) as total_value"],
                limit_page_length: 1
            },
            callback(r) {
                if (r.message && r.message[0]) {
                    frm.set_value("activity_score",  r.message[0].total_points || 0);
                    frm.set_value("value_generated", r.message[0].total_value  || 0);
                    frm.trigger("_preview_composite");
                }
            }
        });
    },

    _preview_composite(frm) {
        const activity_norm = Math.min(flt(frm.doc.activity_score), 200) / 200 * 100;
        const hours_norm    = Math.min(flt(frm.doc.hours_logged),   8)   / 8   * 100;
        const rating_norm   = (flt(frm.doc.self_rating) / 5) * 100;
        const composite     = ((activity_norm * 0.5) + (hours_norm * 0.3) + (rating_norm * 0.2)).toFixed(1);
        // Render preview in score card area
        frm.trigger("_render_score_card");
        frm.doc._composite_preview = composite;
    },

    _render_score_card(frm) {
        const pts = flt(frm.doc.activity_score);
        const hrs = flt(frm.doc.hours_logged);
        const comp = flt(frm.doc.composite_score);
        const val  = flt(frm.doc.value_generated);

        if (!frm.fields_dict.composite_score) return;

        const color = comp >= 75 ? "#16a34a" : comp >= 50 ? "#d97706" : "#dc2626";
        const html = `
            <div style="display:flex;gap:16px;flex-wrap:wrap;padding:8px 0;">
                <div style="text-align:center;min-width:80px;">
                    <div style="font-size:24px;font-weight:700;color:#4f46e5;">${pts}</div>
                    <div style="font-size:11px;color:#6b7280;">Points</div>
                </div>
                <div style="text-align:center;min-width:80px;">
                    <div style="font-size:24px;font-weight:700;color:#0ea5e9;">${hrs}</div>
                    <div style="font-size:11px;color:#6b7280;">Hours</div>
                </div>
                <div style="text-align:center;min-width:80px;">
                    <div style="font-size:24px;font-weight:700;color:${color};">${comp}</div>
                    <div style="font-size:11px;color:#6b7280;">Composite</div>
                </div>
            </div>`;
        frm.get_field("composite_score").$wrapper.after(
            $(`<div class="wfh-score-card">${html}</div>`).css("margin", "0 0 12px 0")
        );
        // Avoid duplicating
        frm.$wrapper.find(".wfh-score-card + .wfh-score-card").remove();
    },

    _setup_buttons(frm) {
        if (frm.doc.status === "Submitted" && frappe.user.has_role(["HR Manager", "Line Manager"])) {
            frm.add_custom_button(__("Mark as Reviewed"), () => {
                frm.set_value("status", "Reviewed");
                frm.save().then(() => {
                    frappe.show_alert({ message: __("Marked as Reviewed"), indicator: "green" }, 4);
                });
            }).addClass("btn-success");
        }

        if (!frm.is_new() && frm.doc.session) {
            frm.add_custom_button(__("View Session"), () => {
                frappe.set_route("Form", "WFH Session", frm.doc.session);
            });
        }

        if (!frm.is_new()) {
            frm.add_custom_button(__("View Activity Logs"), () => {
                frappe.route_options = {
                    employee: frm.doc.employee,
                    date:     frm.doc.date
                };
                frappe.set_route("List", "Work Activity Log");
            });
        }
    },

    _set_indicator(frm) {
        const map = {
            Draft:     "gray",
            Submitted: "blue",
            Reviewed:  "green",
            Flagged:   "orange"
        };
        frm.page.set_indicator(frm.doc.status, map[frm.doc.status] || "gray");
    }
});

function flt(val) { return parseFloat(val) || 0; }
