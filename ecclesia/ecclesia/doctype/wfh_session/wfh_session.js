// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

// WFH Session — Client Script
// Ecclesia Module
//
// GPS is OPTIONAL throughout.
// Check-in works with or without location permission.
// If the browser does not support geolocation, or the user
// denies permission, check-in proceeds normally — no error,
// no block. GPS coordinates are a bonus, not a requirement.

frappe.ui.form.on("WFH Session", {

    onload(frm) {
        // Safe user check with fallback
        try {
            const user = frappe.session.user || "Guest";
            
            frm.set_query("employee", () => {
                if (user !== "Administrator" && user !== "Guest") {
                    return { filters: { user_id: user } };
                }
                // For Administrator or invalid session, show all employees
                return {};
            });
        } catch (e) {
            console.error("Error in WFH Session onload:", e);
        }
    },

    refresh(frm) {
        frm.trigger("_setup_buttons");
        frm.trigger("_live_timer");
        frm.trigger("_set_indicator");
        frm.trigger("_show_gps_status");
    },

    check_in_time(frm) { frm.trigger("_calc_hours"); },
    check_out_time(frm) { frm.trigger("_calc_hours"); },

    _calc_hours(frm) {
        try {
            if (frm.doc.check_in_time && frm.doc.check_out_time) {
                const diff = frappe.datetime.get_diff(
                    frm.doc.check_out_time, frm.doc.check_in_time, "hours"
                );
                const hours = Math.max(parseFloat(diff.toFixed(2)), 0);
                frm.set_value("total_hours", hours);
            }
        } catch (e) {
            console.error("Error calculating hours:", e);
        }
    },

    // ── GPS status banner (informational only) ────────────────────────────────
    _show_gps_status(frm) {
        try {
            if (frm.doc.gps_verified) {
                frm.dashboard.add_comment(
                    `<i class="ti ti-map-pin"></i> GPS location captured: ` +
                    `${(frm.doc.latitude || 0).toFixed(4)}, ` +
                    `${(frm.doc.longitude || 0).toFixed(4)} ` +
                    `(±${frm.doc.gps_accuracy || "?"} m)`,
                    "green",
                    true
                );
            } else if (!frm.is_new() && frm.doc.status !== "Cancelled") {
                // Informational only — not an error indicator
                frm.dashboard.add_comment(
                    "GPS location not captured for this session. " +
                    "All functionality works normally without it.",
                    "gray",
                    true
                );
            }
        } catch (e) {
            console.error("Error showing GPS status:", e);
        }
    },

    // ── Buttons ───────────────────────────────────────────────────────────────
    _setup_buttons(frm) {
        try {
            if (frm.doc.status === "Open" && !frm.is_new()) {
                frm.add_custom_button(__("Check Out Now"), () => {
                    frappe.call({
                        method: "ecclesia.ecclesia.doctype.wfh_session.wfh_session.check_out",
                        args: { session_name: frm.doc.name },
                        freeze: true,
                        freeze_message: __("Checking out..."),
                        callback(response) {
                            if (response && response.message) {
                                frm.reload_doc();
                            }
                        },
                        error(err) {
                            frappe.msgprint({
                                title: __("Error"),
                                message: __("Could not check out. Please try again."),
                                indicator: "red"
                            });
                        }
                    });
                }).addClass("btn-primary");
            }

            // GPS update button — only shown when GPS not yet captured and session is open
            if (frm.doc.status === "Open" && !frm.doc.gps_verified && !frm.is_new()) {
                if (navigator && navigator.geolocation) {
                    frm.add_custom_button(__("Add GPS location"), () => {
                        frm.trigger("_try_capture_gps");
                    });
                }
            }

            if (frm.doc.status === "Closed" || frm.doc.status === "Flagged") {
                frm.add_custom_button(__("View Activities"), () => {
                    frappe.route_options = { session: frm.doc.name };
                    frappe.set_route("List", "Work Activity Log");
                });
                frm.add_custom_button(__("View Summary"), () => {
                    frappe.route_options = { session: frm.doc.name };
                    frappe.set_route("List", "WFH Daily Summary");
                });
            }
        } catch (e) {
            console.error("Error setting up buttons:", e);
        }
    },

    // ── Optional GPS capture (called from button, never blocking) ─────────────
    _try_capture_gps(frm) {
        if (!navigator || !navigator.geolocation) {
            frappe.show_alert({
                message: __("This browser does not support geolocation."),
                indicator: "gray"
            }, 5);
            return;
        }

        frappe.show_alert({ 
            message: __("Requesting location..."), 
            indicator: "blue" 
        }, 3);

        navigator.geolocation.getCurrentPosition(
            // SUCCESS — store coordinates
            (pos) => {
                if (!pos || !pos.coords) {
                    frappe.show_alert({
                        message: __("Could not get valid location data."),
                        indicator: "gray"
                    }, 5);
                    return;
                }

                frappe.call({
                    method: "ecclesia.ecclesia.doctype.wfh_session.wfh_session.check_in",
                    args: {
                        employee:  frm.doc.employee,
                        latitude:  pos.coords.latitude,
                        longitude: pos.coords.longitude,
                        accuracy:  pos.coords.accuracy || null,
                    },
                    freeze: true,
                    freeze_message: __("Saving location..."),
                    callback(response) {
                        if (response && response.message) {
                            frappe.show_alert({ 
                                message: __("GPS location saved."), 
                                indicator: "green" 
                            }, 4);
                            frm.reload_doc();
                        }
                    },
                    error(err) {
                        frappe.show_alert({
                            message: __("Failed to save GPS location."),
                            indicator: "red"
                        }, 5);
                    }
                });
            },
            // DENIED / ERROR — silent, no error shown to user
            (err) => {
                const msgs = {
                    1: "Location permission denied — session continues normally.",
                    2: "Location unavailable — session continues normally.",
                    3: "Location request timed out — session continues normally.",
                };
                frappe.show_alert({
                    message: __(msgs[err.code] || "Could not get location."),
                    indicator: "gray"
                }, 5);
            },
            { 
                enableHighAccuracy: true, 
                timeout: 10000, 
                maximumAge: 0 
            }
        );
    },

    // ── Live running-hours display ─────────────────────────────────────────────
    _live_timer(frm) {
        try {
            if (frm.doc.status !== "Open" || !frm.doc.check_in_time) return;
            
            // Clear existing interval if any
            if (frm._timer_interval) {
                clearInterval(frm._timer_interval);
            }
            
            frm._timer_interval = setInterval(() => {
                try {
                    const cin  = new Date(frm.doc.check_in_time);
                    const now  = new Date();
                    const diff = ((now - cin) / 3600000).toFixed(2);
                    const $inp = frm.fields_dict.total_hours && frm.fields_dict.total_hours.$input;
                    if ($inp) $inp.val(diff);
                } catch (e) {
                    // Silently handle any timer errors
                    clearInterval(frm._timer_interval);
                }
            }, 60000);
        } catch (e) {
            console.error("Error setting up live timer:", e);
        }
    },

    _set_indicator(frm) {
        try {
            const colors = { 
                Open: "blue", 
                Closed: "green", 
                Flagged: "orange", 
                Cancelled: "gray" 
            };
            const color = colors[frm.doc.status] || "gray";
            frm.page.set_indicator(frm.doc.status, color);
        } catch (e) {
            console.error("Error setting indicator:", e);
        }
    }
});

// Clean up timer when form is closed
frappe.ui.form.off("WFH Session", "on_close");
frappe.ui.form.on("WFH Session", "on_close", function(frm) {
    if (frm && frm._timer_interval) {
        clearInterval(frm._timer_interval);
    }
});