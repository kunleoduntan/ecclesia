// ecclesia/biometric_attendance/doctype/biometric_device/biometric_device.js
// Loaded automatically by Frappe for the Biometric Device form

const BRAND_CONFIG = {
    "ZKTeco":    {
        protocol: "SDK",
        port:     4370,
        hint:     "Uses pyzk over UDP/TCP. Set Communication Key to the device password (0 if none set).",
        show:     ["communication_key"],
        hide:     ["biostar_server_url", "cloudclox_device_id", "cloudclox_api_url", "api_key"],
    },
    "eSSL":      {
        protocol: "SDK",
        port:     4370,
        hint:     "eSSL devices use the ZKTeco-compatible SDK. Same settings as ZKTeco.",
        show:     ["communication_key"],
        hide:     ["biostar_server_url", "cloudclox_device_id", "cloudclox_api_url", "api_key"],
    },
    "TAMS":      {
        protocol: "SDK",
        port:     4370,
        hint:     "TAMS Chrome is ZKTeco-protocol compatible. For real-time attendance, set Sync Mode to 'Push (Real-time)' below and point the device's Comm > Server IP/Port at this server instead of TAMS's own cloud — see Device Serial No field, which must match what the device reports.",
        show:     ["communication_key", "device_serial"],
        hide:     ["biostar_server_url", "cloudclox_device_id", "cloudclox_api_url", "api_key"],
    },
    "Realand":   {
        protocol: "SDK",
        port:     4370,
        hint:     "Realand devices use the ZKTeco-compatible binary SDK (pyzk, force_udp=True).",
        show:     ["communication_key"],
        hide:     ["biostar_server_url", "cloudclox_device_id", "cloudclox_api_url", "api_key"],
    },
    "Hikvision": {
        protocol: "ISAPI / REST",
        port:     80,
        hint:     "Uses Hikvision ISAPI over HTTP/HTTPS. Enter admin username + password. Use port 443 if SSL is enabled.",
        show:     ["username", "password", "use_https"],
        hide:     ["communication_key", "biostar_server_url", "cloudclox_device_id", "cloudclox_api_url", "api_key"],
    },
    "Dahua":     {
        protocol: "HTTP CGI",
        port:     80,
        hint:     "Uses Dahua CGI HTTP API with Digest auth. Enter admin username + password.",
        show:     ["username", "password"],
        hide:     ["communication_key", "biostar_server_url", "cloudclox_device_id", "cloudclox_api_url", "api_key"],
    },
    "Suprema":   {
        protocol: "BioStar2 API",
        port:     443,
        hint:     "Requires a running BioStar2 server. Enter the server URL below, plus your BioStar2 login credentials.",
        show:     ["username", "password", "biostar_server_url"],
        hide:     ["communication_key", "cloudclox_device_id", "cloudclox_api_url", "api_key"],
    },
    "Anviz":     {
        protocol: "CloudClox API",
        port:     null,
        hint:     "Cloud-based — no direct IP needed. Enter your CloudClox Device ID, API URL, and API Key below.",
        show:     ["api_key", "cloudclox_device_id", "cloudclox_api_url"],
        hide:     ["communication_key", "biostar_server_url", "username", "password", "ip_address", "port"],
    },
    "Virdi":     {
        protocol: "REST API",
        port:     80,
        hint:     "Enter Virdi admin username + password, or put a pre-generated Bearer token in the API Key field.",
        show:     ["username", "password", "api_key"],
        hide:     ["communication_key", "biostar_server_url", "cloudclox_device_id", "cloudclox_api_url"],
    },
};


frappe.ui.form.on("Biometric Device", {

    // ── Triggers ──────────────────────────────────────────────────────────────

    device_brand(frm) {
        const cfg = BRAND_CONFIG[frm.doc.device_brand];
        if (!cfg) return;

        // Auto-set protocol
        frm.set_value("protocol", cfg.protocol);

        // Auto-set port only if the user hasn't already customised it
        if (cfg.port && (!frm.doc.port || frm.doc.port === 4370 || frm.doc.port === 80)) {
            frm.set_value("port", cfg.port);
        }

        // Show/hide fields
        _apply_brand_fields(frm, cfg);

        // Friendly hint
        frappe.show_alert({ message: cfg.hint, indicator: "blue" }, 10);
    },

    sync_mode(frm) {
        if (frm.doc.device_brand === "TAMS" && frm.doc.sync_mode === "Push (Real-time)") {
            frappe.show_alert({
                message: __(
                    "Remember: on the physical device, set Comm > Server Settings > Server IP/Port to this Frappe server's address (not TAMS's cloud), and enter this device's exact Serial No in Device Serial No above so pushes can be matched."
                ),
                indicator: "orange"
            }, 12);
        }
    },

    refresh(frm) {
        // Re-apply field visibility whenever the form loads or refreshes
        const cfg = BRAND_CONFIG[frm.doc.device_brand];
        if (cfg) _apply_brand_fields(frm, cfg);

        if (frm.is_new()) return;

        // ── Custom action buttons ─────────────────────────────────────────────
        frm.add_custom_button(__("Ping Device"), () => _ping(frm), __("Actions"));
        frm.add_custom_button(__("Sync Now"),    () => _sync(frm), __("Actions"));
        frm.add_custom_button(__("Enrolled Users"), () => _get_users(frm), __("Actions"));
        frm.add_custom_button(__("View Sync Logs"), () => {
            frappe.route_options = { biometric_device: frm.doc.name };
            frappe.set_route("List", "Biometric Sync Log");
        }, __("Actions"));
        frm.add_custom_button(__("View Attendance Logs"), () => {
            frappe.route_options = { device: frm.doc.name };
            frappe.set_route("List", "Biometric Attendance Log");
        }, __("Actions"));

        // Show last sync status as a colour-coded indicator
        _show_sync_indicator(frm);
    }
});


// ── Field visibility ──────────────────────────────────────────────────────────

function _apply_brand_fields(frm, cfg) {
    (cfg.show || []).forEach(f => frm.toggle_display(f, true));
    (cfg.hide || []).forEach(f => frm.toggle_display(f, false));
}


// ── Ping ──────────────────────────────────────────────────────────────────────

function _ping(frm) {
    const btn_label = __("Ping Device");
    frappe.show_alert({ message: __("Pinging device…"), indicator: "orange" });

    frappe.call({
        method:   "ecclesia.api.attendance.ping_device",
        args:     { device_name: frm.doc.name },
        callback(r) {
            if (!r.message) return;
            const online = r.message.online;
            frappe.show_alert({
                message:   __(`Device is ${r.message.status}`),
                indicator: online ? "green" : "red"
            }, 5);
            // Reload so device_status field reflects the updated value
            frm.reload_doc();
        }
    });
}


// ── Sync Now ──────────────────────────────────────────────────────────────────

function _sync(frm) {
    if (frm.doc.sync_mode === "Push (Real-time)") {
        frappe.msgprint({
            title: __("Push Mode Device"),
            message: __("This device pushes attendance in real time — there is nothing to manually pull. Use 'Ping Device' to check connectivity, or check View Attendance Logs to confirm recent pushes are arriving."),
            indicator: "blue"
        });
        return;
    }

    frappe.confirm(
        __(`Pull attendance logs from <b>${frm.doc.device_name || frm.doc.name}</b> now?`),
        () => {
            frappe.show_alert({ message: __("Syncing…"), indicator: "orange" });
            frappe.call({
                method:         "ecclesia.api.attendance.sync_device",
                args:           { device_name: frm.doc.name },
                freeze:         true,
                freeze_message: __("Pulling logs from device…"),
                callback(r) {
                    if (!r.message) return;
                    const m = r.message;
                    if (m.success === false) {
                        frappe.msgprint({
                            title:     __("Sync Failed"),
                            message:   m.error || __("Unknown error"),
                            indicator: "red"
                        });
                    } else {
                        frappe.show_alert({
                            message: __(
                                `Sync complete — ${m.total_fetched || 0} fetched, ` +
                                `${m.attendance_created || 0} attendance records created, ` +
                                `${m.skipped || 0} skipped.`
                            ),
                            indicator: "green"
                        }, 8);
                    }
                    frm.reload_doc();
                }
            });
        }
    );
}


// ── Enrolled Users ────────────────────────────────────────────────────────────

function _get_users(frm) {
    frappe.show_alert({ message: __("Fetching users from device…"), indicator: "orange" });

    frappe.call({
        method:   "ecclesia.api.attendance.get_device_users",
        args:     { device_name: frm.doc.name },
        callback(r) {
            const users = r.message;
            if (!users || !users.length) {
                frappe.msgprint(__("No enrolled users found on this device."));
                return;
            }

            const rows = users.map(u =>
                `<tr>
                    <td style="padding:6px 10px">${frappe.utils.escape_html(String(u.user_id || u.uid || ""))}</td>
                    <td style="padding:6px 10px">${frappe.utils.escape_html(u.name || "")}</td>
                    <td style="padding:6px 10px">${u.privilege == 14 ? "Admin" : "User"}</td>
                 </tr>`
            ).join("");

            frappe.msgprint({
                title:   __(`Enrolled Users — ${frm.doc.device_name || frm.doc.name} (${users.length})`),
                message: `
                    <table class="table table-bordered table-sm" style="margin-top:8px">
                        <thead style="background:#f4f5f6">
                            <tr>
                                <th style="padding:6px 10px">Biometric ID</th>
                                <th style="padding:6px 10px">Name on Device</th>
                                <th style="padding:6px 10px">Role</th>
                            </tr>
                        </thead>
                        <tbody>${rows}</tbody>
                    </table>`,
                wide: true
            });
        }
    });
}


// ── Status indicator ──────────────────────────────────────────────────────────

function _show_sync_indicator(frm) {
    const status = frm.doc.device_status || "Unknown";
    const colour = status === "Online" ? "green" : status === "Offline" ? "red" : "orange";

    if (frm.doc.sync_mode === "Push (Real-time)") {
        const heartbeat = frm.doc.last_heartbeat
            ? frappe.datetime.str_to_user(frm.doc.last_heartbeat)
            : __("never");
        const last_punch = frm.doc.last_sync
            ? frappe.datetime.str_to_user(frm.doc.last_sync)
            : __("no punches yet");
        frm.dashboard.add_indicator(
            __(`${status} — Last contact: ${heartbeat} · Last punch: ${last_punch}`),
            colour
        );
        return;
    }

    if (!frm.doc.last_sync) return;
    const last_sync = frappe.datetime.str_to_user(frm.doc.last_sync);
    frm.dashboard.add_indicator(
        __(`${status} — Last sync: ${last_sync}`),
        colour
    );
}