/**
 * ecclesia/public/js/telephone.js
 * Ecclesia Telephone System — complete frontend
 */

// =============================================================================
// DIALPAD WIDGET — builds + mounts the floating dialpad on every desk page
// =============================================================================

(function () {
    "use strict";

    // ── State ─────────────────────────────────────────────────────────────────
    var S = {
        IDLE: "IDLE", DIALING: "DIALING", RINGING: "RINGING",
        CONNECTED: "CONNECTED", INCOMING: "INCOMING",
        ENDED: "ENDED", FAILED: "FAILED"
    };

    var state = {
        current: S.IDLE,
        tcl_name: null,
        dial_buffer: "",
        call_start: null,
        timer_interval: null,
        peer_connection: null,
        local_stream: null,
        active_provider: null,
        target_user: null,
        settings: null,
        _fail_reason: ""
    };

    // ── Boot + Init ───────────────────────────────────────────────────────────
    // We cannot rely on frappe.after_ajax — instead we poll until frappe.boot
    // is populated, then build the widget. Works on all Frappe versions.

    function _try_init() {
        if (document.getElementById("ec-widget")) return; // already built

        var boot = (typeof frappe !== "undefined") && frappe.boot;
        if (!boot) { setTimeout(_try_init, 300); return; }

        // frappe.boot exists — even if telephone key is missing, build widget
        state.settings = (boot.telephone && boot.telephone.enabled !== false)
            ? boot.telephone
            : { enabled: true };  // sensible defaults if boot_session failed

        _build_widget();
        _bind_keys();
        _bind_realtime();
    }

    // Poll starting from DOMContentLoaded
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () { setTimeout(_try_init, 400); });
    } else {
        setTimeout(_try_init, 400);
    }

    // ── Build Widget DOM ──────────────────────────────────────────────────────
    function _build_widget() {
        var pos = (state.settings.dialpad_position || "Bottom Right");
        var positions = {
            "Bottom Right": "bottom:24px;right:24px;",
            "Bottom Left":  "bottom:24px;left:24px;",
            "Top Right":    "top:24px;right:24px;",
            "Top Left":     "top:24px;left:24px;"
        };
        var posCSS = positions[pos] || positions["Bottom Right"];

        var html = '<div id="ec-widget" style="position:fixed;' + posCSS + 'z-index:99999;font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',sans-serif;">'

            // Toggle button
            + '<button id="ec-toggle" onclick="window._ec_toggle()" title="Telephone (Alt+D)" '
            + 'style="width:52px;height:52px;border-radius:50%;background:#2490EF;border:none;'
            + 'color:#fff;font-size:22px;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,0.2);'
            + 'display:flex;align-items:center;justify-content:center;position:relative;">'
            + '<span id="ec-icon">📞</span>'
            + '<span id="ec-badge" style="display:none;position:absolute;top:0;right:0;'
            + 'background:red;color:#fff;border-radius:50%;width:18px;height:18px;'
            + 'font-size:10px;line-height:18px;text-align:center;"></span>'
            + '</button>'

            // Panel
            + '<div id="ec-panel" style="display:none;width:300px;background:#fff;'
            + 'border-radius:16px;box-shadow:0 8px 40px rgba(0,0,0,0.18);'
            + 'margin-bottom:8px;overflow:hidden;border:1px solid #e2e6ea;">'

            // Header
            + '<div style="background:#2490EF;padding:12px 14px;display:flex;'
            + 'justify-content:space-between;align-items:center;">'
            + '<span style="color:#fff;font-weight:700;font-size:14px;">📞 Telephone</span>'
            + '<button onclick="window._ec_toggle()" style="background:none;border:none;'
            + 'color:#fff;font-size:16px;cursor:pointer;padding:0;">✕</button>'
            + '</div>'

            // Number input
            + '<div style="padding:12px 12px 0;">'
            + '<div style="display:flex;gap:6px;margin-bottom:10px;">'
            + '<input id="ec-num" type="tel" placeholder="Enter number..." '
            + 'style="flex:1;padding:10px;border:1.5px solid #e2e6ea;border-radius:8px;'
            + 'font-size:16px;letter-spacing:1px;outline:none;" />'
            + '<button onclick="window._ec_backspace()" '
            + 'style="padding:8px 12px;border:1.5px solid #e2e6ea;border-radius:8px;'
            + 'background:#f5f7fa;cursor:pointer;font-size:14px;">⌫</button>'
            + '</div>'

            // Progress bar area
            + '<div id="ec-progress" style="display:none;margin-bottom:10px;">'
            + '<div style="display:flex;justify-content:space-between;margin-bottom:6px;font-size:10px;">'
            + '<span id="ec-step-dial" style="color:#aaa;">Dialing</span>'
            + '<span id="ec-step-ring" style="color:#aaa;">Ringing</span>'
            + '<span id="ec-step-conn" style="color:#aaa;">Connected</span>'
            + '</div>'
            + '<div style="height:6px;background:#e2e6ea;border-radius:3px;overflow:hidden;">'
            + '<div id="ec-bar" style="height:100%;width:0%;background:linear-gradient(90deg,#2490EF,#28a745);'
            + 'border-radius:3px;transition:width 0.6s ease;"></div>'
            + '</div>'
            + '<div id="ec-status-msg" style="text-align:center;font-size:11px;font-weight:600;'
            + 'margin-top:5px;min-height:16px;"></div>'
            + '</div>'

            // Timer
            + '<div id="ec-timer" style="display:none;text-align:center;font-size:22px;'
            + 'font-weight:700;color:#28a745;margin-bottom:8px;font-variant-numeric:tabular-nums;">00:00</div>'

            // Keypad
            + '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:10px;">'
            + ['1','2','3','4','5','6','7','8','9','*','0','#'].map(function(d) {
                return '<button onclick="window._ec_digit(\'' + d + '\')" '
                    + 'style="padding:12px 0;border:1.5px solid #e2e6ea;border-radius:8px;'
                    + 'background:#f5f7fa;cursor:pointer;font-size:16px;font-weight:700;">' + d + '</button>';
            }).join('')
            + '</div>'

            // Call controls
            + '<div id="ec-controls" style="display:flex;justify-content:center;gap:12px;margin-bottom:12px;">'
            + '<button id="ec-call-btn" onclick="window._ec_call()" '
            + 'style="width:52px;height:52px;border-radius:50%;background:#28a745;border:none;'
            + 'color:#fff;font-size:22px;cursor:pointer;box-shadow:0 2px 8px rgba(40,167,69,0.4);">📞</button>'
            + '<button id="ec-hangup-btn" onclick="window._ec_hangup()" '
            + 'style="display:none;width:52px;height:52px;border-radius:50%;background:#dc3545;border:none;'
            + 'color:#fff;font-size:22px;cursor:pointer;box-shadow:0 2px 8px rgba(220,53,69,0.4);">📵</button>'
            + '<button id="ec-mute-btn" onclick="window._ec_mute()" '
            + 'style="display:none;width:42px;height:42px;border-radius:50%;background:#f5f7fa;'
            + 'border:1.5px solid #e2e6ea;font-size:18px;cursor:pointer;">🎤</button>'
            + '</div>'

            // Notes
            + '<div id="ec-notes" style="display:none;padding-bottom:10px;">'
            + '<textarea id="ec-notes-txt" placeholder="Call notes..." rows="2" '
            + 'style="width:100%;box-sizing:border-box;border:1.5px solid #e2e6ea;border-radius:8px;'
            + 'padding:8px;font-size:12px;resize:none;"></textarea>'
            + '<button onclick="window._ec_save_notes()" '
            + 'style="background:none;border:none;color:#2490EF;cursor:pointer;font-size:12px;'
            + 'padding:2px 0;">💾 Save Notes</button>'
            + '</div>'

            + '</div>' // end padding div
            + '</div>' // end panel
            + '</div>'; // end widget

        var container = document.createElement("div");
        container.innerHTML = html;
        document.body.appendChild(container.firstChild);

        // Wire number input
        document.getElementById("ec-num").addEventListener("input", function(e) {
            state.dial_buffer = e.target.value;
        });
        document.getElementById("ec-num").addEventListener("keydown", function(e) {
            if (e.key === "Enter") window._ec_call();
        });

        _update_badge();
    }

    // ── Global helpers (called from inline onclick) ───────────────────────────
    window._ec_toggle = function() {
        var panel = document.getElementById("ec-panel");
        if (!panel) return;
        panel.style.display = (panel.style.display === "none") ? "block" : "none";
        if (panel.style.display === "block") {
            setTimeout(function() { document.getElementById("ec-num").focus(); }, 50);
        }
    };

    window._ec_digit = function(d) {
        state.dial_buffer += d;
        document.getElementById("ec-num").value = state.dial_buffer;
    };

    window._ec_backspace = function() {
        state.dial_buffer = state.dial_buffer.slice(0, -1);
        document.getElementById("ec-num").value = state.dial_buffer;
    };

    window._ec_call = function() {
        var num = state.dial_buffer || document.getElementById("ec-num").value.trim();
        if (!num) {
            frappe.show_alert({ message: "Please enter a number.", indicator: "orange" });
            return;
        }
        if (state.current !== S.IDLE && state.current !== S.ENDED) return;
        _do_call(num, null, null);
    };

    window._ec_hangup = function() {
        _hang_up();
    };

    var _muted = false;
    window._ec_mute = function() {
        _muted = !_muted;
        if (state.local_stream) {
            state.local_stream.getAudioTracks().forEach(function(t) { t.enabled = !_muted; });
        }
        document.getElementById("ec-mute-btn").textContent = _muted ? "🔇" : "🎤";
    };

    window._ec_save_notes = function() {
        if (!state.tcl_name) return;
        var notes = document.getElementById("ec-notes-txt").value;
        frappe.call({
            method: "ecclesia.api.telephone_api.save_call_notes",
            args: { tcl_name: state.tcl_name, call_notes: notes }
        });
        frappe.show_alert({ message: "Notes saved.", indicator: "green" });
    };

    // ── Keyboard shortcut (Alt+D) ─────────────────────────────────────────────
    function _bind_keys() {
        document.addEventListener("keydown", function(e) {
            if (e.altKey && e.key.toLowerCase() === "d") {
                e.preventDefault();
                window._ec_toggle();
            }
        });
    }

    // ── State transitions + progress UI ──────────────────────────────────────
    function _set_state(s, msg, bar_pct) {
        state.current = s;

        var progress  = document.getElementById("ec-progress");
        var bar       = document.getElementById("ec-bar");
        var statusMsg = document.getElementById("ec-status-msg");
        var callBtn   = document.getElementById("ec-call-btn");
        var hangupBtn = document.getElementById("ec-hangup-btn");
        var muteBtn   = document.getElementById("ec-mute-btn");
        var timer     = document.getElementById("ec-timer");
        var notes     = document.getElementById("ec-notes");
        var icon      = document.getElementById("ec-icon");

        // Step colours
        var steps = { "ec-step-dial": ["DIALING","RINGING","CONNECTED","FAILED"],
                      "ec-step-ring": ["RINGING","CONNECTED"],
                      "ec-step-conn": ["CONNECTED"] };
        Object.keys(steps).forEach(function(id) {
            var el = document.getElementById(id);
            if (!el) return;
            el.style.color = (steps[id].indexOf(s) >= 0) ? "#2490EF" : "#aaa";
            el.style.fontWeight = (steps[id].indexOf(s) >= 0) ? "700" : "400";
        });

        if (s === S.IDLE) {
            if (progress)  progress.style.display  = "none";
            if (timer)     timer.style.display      = "none";
            if (notes)     notes.style.display      = "none";
            if (callBtn)   callBtn.style.display    = "";
            if (hangupBtn) hangupBtn.style.display  = "none";
            if (muteBtn)   muteBtn.style.display    = "none";
            if (icon)      icon.textContent         = "📞";
            _stop_timer();
        } else {
            if (progress) progress.style.display = "block";
            if (bar)      bar.style.width = (bar_pct || 0) + "%";
            if (statusMsg) {
                statusMsg.textContent = msg || "";
                statusMsg.style.color = s === S.FAILED ? "#dc3545"
                    : s === S.CONNECTED ? "#28a745"
                    : s === S.ENDED     ? "#6c757d"
                    : "#2490EF";
            }

            if (s === S.DIALING || s === S.RINGING || s === S.INCOMING) {
                if (callBtn)   callBtn.style.display   = "none";
                if (hangupBtn) hangupBtn.style.display = "";
                if (muteBtn)   muteBtn.style.display   = "none";
                if (icon)      icon.textContent        = s === S.INCOMING ? "📲" : "🔴";
            } else if (s === S.CONNECTED) {
                if (callBtn)   callBtn.style.display   = "none";
                if (hangupBtn) hangupBtn.style.display = "";
                if (muteBtn)   muteBtn.style.display   = "";
                if (notes)     notes.style.display     = "block";
                if (timer)     timer.style.display     = "block";
                if (icon)      icon.textContent        = "🔴";
                _start_timer();
            } else if (s === S.ENDED || s === S.FAILED) {
                if (callBtn)   callBtn.style.display   = "";
                if (hangupBtn) hangupBtn.style.display = "none";
                if (muteBtn)   muteBtn.style.display   = "none";
                if (notes)     notes.style.display     = s === S.ENDED ? "block" : "none";
                if (icon)      icon.textContent        = "📞";
                _stop_timer();
                setTimeout(function() { _set_state(S.IDLE); }, 4000);
            }
        }

        // Also update floating overlay if visible
        _update_overlay(s, msg, bar_pct);
    }

    // ── Timer ─────────────────────────────────────────────────────────────────
    function _start_timer() {
        state.call_start = Date.now();
        state.timer_interval = setInterval(function() {
            var sec = Math.floor((Date.now() - state.call_start) / 1000);
            var m = Math.floor(sec / 60), s_val = sec % 60;
            var el = document.getElementById("ec-timer");
            if (el) el.textContent = (m < 10 ? "0" : "") + m + ":" + (s_val < 10 ? "0" : "") + s_val;
        }, 1000);
    }

    function _stop_timer() {
        if (state.timer_interval) { clearInterval(state.timer_interval); state.timer_interval = null; }
    }

    // ── Core call function ────────────────────────────────────────────────────
    function _do_call(number, source_doctype, source_docname) {
        _set_state(S.DIALING, "🔄 Connecting...", 15);
        _show_overlay(number);

        frappe.call({
            method: "ecclesia.api.telephone_api.initiate_call",
            args: { receiver_number: number, source_doctype: source_doctype, source_docname: source_docname },
            callback: function(r) {
                if (!r || !r.message) {
                    state._fail_reason = "❌ No response — check Telephone Settings";
                    _set_state(S.FAILED, state._fail_reason, 0);
                    return;
                }
                var resp = r.message;
                state.tcl_name = resp.tcl_name;

                if (resp.routing === "internal") {
                    _start_webrtc(resp.target_user);
                } else {
                    _start_external(resp);
                }
            },
            error: function(err) {
                var msg = (err && err.message) ? err.message : "unknown error";
                state._fail_reason = "❌ API error: " + msg;
                _set_state(S.FAILED, state._fail_reason, 0);
            }
        });
    }

    function _hang_up() {
        if (state.peer_connection) {
            _send_signal(state.target_user, "hang_up", {});
            _close_webrtc();
        }
        if (state.active_provider && state.active_provider.disconnect) {
            try { state.active_provider.disconnect(); } catch(e) {}
        }
        _update_call_status("Answered");
        _set_state(S.ENDED, "📵 Call ended", 100);
    }

    function _update_call_status(status) {
        if (!state.tcl_name) return;
        frappe.call({
            method: "ecclesia.api.telephone_api.update_call_status",
            args: { tcl_name: state.tcl_name, status: status }
        });
    }

    // ── WebRTC ────────────────────────────────────────────────────────────────
    function _start_webrtc(target_user) {
        state.target_user = target_user;
        _set_state(S.RINGING, "🔔 Ringing...", 55);

        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(function(stream) {
                state.local_stream = stream;
                var pc = _make_pc();
                stream.getTracks().forEach(function(t) { pc.addTrack(t, stream); });
                return pc.createOffer();
            })
            .then(function(offer) {
                return state.peer_connection.setLocalDescription(offer).then(function() {
                    _send_signal(target_user, "offer", { offer: offer });
                    _notify_incoming(target_user);
                });
            })
            .catch(function(e) {
                state._fail_reason = "❌ Microphone error: " + e.message;
                _set_state(S.FAILED, state._fail_reason, 0);
            });
    }

    function _answer_webrtc(from_user, offer) {
        state.target_user = from_user;
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(function(stream) {
                state.local_stream = stream;
                var pc = _make_pc();
                stream.getTracks().forEach(function(t) { pc.addTrack(t, stream); });
                return pc.setRemoteDescription(new RTCSessionDescription(offer))
                    .then(function() { return pc.createAnswer(); })
                    .then(function(ans) {
                        return pc.setLocalDescription(ans).then(function() {
                            _send_signal(from_user, "answer", { answer: ans });
                        });
                    });
            })
            .catch(function(e) {
                state._fail_reason = "❌ " + e.message;
                _set_state(S.FAILED, state._fail_reason, 0);
            });
    }

    function _make_pc() {
        var cfg = { iceServers: [{ urls: (state.settings.stun_server_url || "stun:stun.l.google.com:19302") }] };
        var pc = new RTCPeerConnection(cfg);
        state.peer_connection = pc;

        pc.onicecandidate = function(e) {
            if (e.candidate) _send_signal(state.target_user, "ice_candidate", { candidate: e.candidate });
        };
        pc.ontrack = function(e) {
            var audio = new Audio();
            audio.srcObject = e.streams[0];
            audio.play().catch(function(){});
        };
        pc.onconnectionstatechange = function() {
            if (pc.connectionState === "connected")    _set_state(S.CONNECTED, "✅ Connected", 100);
            if (pc.connectionState === "disconnected") { _close_webrtc(); _set_state(S.ENDED, "📵 Call ended", 100); }
            if (pc.connectionState === "failed")       { _close_webrtc(); _set_state(S.FAILED, "❌ Connection failed", 0); }
        };
        return pc;
    }

    function _close_webrtc() {
        if (state.peer_connection) { state.peer_connection.close(); state.peer_connection = null; }
        if (state.local_stream)    { state.local_stream.getTracks().forEach(function(t){t.stop();}); state.local_stream = null; }
    }

    function _send_signal(target, type, data) {
        frappe.call({
            method: "ecclesia.api.telephone_api.webrtc_signal",
            args: { target_user: target, signal_type: type, data: JSON.stringify(data) }
        });
    }

    function _notify_incoming(target) {
        frappe.call({
            method: "ecclesia.api.telephone_api.notify_incoming_call",
            args: {
                target_user: target,
                tcl_name: state.tcl_name,
                caller_number: frappe.session.user,
                caller_name: frappe.boot.user_info ? (frappe.boot.user_info[frappe.session.user] || {}).fullname || frappe.session.user : frappe.session.user
            }
        });
        // Also send offer via signal so receiver can answer immediately
        // The offer is already set as local description at this point
        if (state.peer_connection && state.peer_connection.localDescription) {
            _send_signal(target, "offer", { offer: state.peer_connection.localDescription });
        }
    }

    // ── External providers ────────────────────────────────────────────────────
    function _start_external(resp) {
        var provider = resp.provider;
        state.active_provider = null;
        _set_state(S.RINGING, "🔔 Connecting via " + provider + "...", 40);

        if (provider === "Twilio") {
            _load_sdk("https://sdk.twilio.com/js/client/v1.14/twilio.min.js", function() {
                var device = new Twilio.Device(resp.token, { codecPreferences: ["opus","pcmu"] });
                state.active_provider = device;
                device.on("ready", function() {
                    var conn = device.connect({ To: resp.receiver_number });
                    conn.on("accept",     function() { _set_state(S.CONNECTED, "✅ Connected via Twilio", 100); });
                    conn.on("disconnect", function() { _set_state(S.ENDED, "📵 Call ended", 100); _update_call_status("Answered"); });
                    conn.on("reject",     function() { _set_state(S.ENDED, "📵 Call declined", 100); _update_call_status("Declined"); });
                });
                device.on("error", function(e) {
                    state._fail_reason = "❌ Twilio error: " + e.message;
                    _set_state(S.FAILED, state._fail_reason, 0);
                });
            });
        } else if (provider === "Vonage") {
            _load_sdk("https://cdn.nexmo.com/conversations/v1/nexmo-client.min.js", function() {
                var client = new NexmoClient({ debug: false });
                client.login(resp.token).then(function(app) {
                    state.active_provider = { disconnect: function() { app.callServer("disconnect"); } };
                    return app.callServer(resp.receiver_number);
                }).then(function(call) {
                    _set_state(S.CONNECTED, "✅ Connected via Vonage", 100);
                    call.on("call:status:changed", function(c) {
                        if (c.status === "completed") { _set_state(S.ENDED, "📵 Call ended", 100); }
                    });
                }).catch(function(e) {
                    state._fail_reason = "❌ Vonage error: " + e.message;
                    _set_state(S.FAILED, state._fail_reason, 0);
                });
            });
        } else if (provider === "Plivo") {
            _load_sdk("https://cdn.plivo.com/sdk/browser/v2/plivo.min.js", function() {
                var phone = new Plivo.Phone();
                state.active_provider = phone;
                phone.setRingTone(false);
                phone.login(resp.username, resp.token);
                phone.onLoginSuccess = function() { phone.call(resp.receiver_number); };
                phone.onCallAnswered = function() { _set_state(S.CONNECTED, "✅ Connected via Plivo", 100); };
                phone.onCallTerminated = function() { _set_state(S.ENDED, "📵 Call ended", 100); _update_call_status("Answered"); };
                phone.onLoginFailed = function() {
                    state._fail_reason = "❌ Plivo login failed";
                    _set_state(S.FAILED, state._fail_reason, 0);
                };
            });
        } else if (provider === "Asterisk") {
            frappe.call({
                method: "ecclesia.api.telephone_api.asterisk_originate",
                args: { receiver_number: resp.receiver_number, tcl_name: state.tcl_name },
                callback: function(r) { if (r.message && r.message.status === "ok") _set_state(S.RINGING, "🔔 Ringing via Asterisk...", 55); },
                error: function() { _set_state(S.FAILED, "❌ Asterisk originate failed", 0); }
            });
        } else {
            state._fail_reason = "❌ No provider configured — check Telephone Settings";
            _set_state(S.FAILED, state._fail_reason, 0);
        }
    }

    function _load_sdk(url, cb) {
        if (document.querySelector('script[src="' + url + '"]')) { cb(); return; }
        var s = document.createElement("script");
        s.src = url;
        s.onload = cb;
        s.onerror = function() {
            state._fail_reason = "❌ Failed to load provider SDK";
            _set_state(S.FAILED, state._fail_reason, 0);
        };
        document.head.appendChild(s);
    }

    // ── Floating overlay (visible from any form page) ─────────────────────────
    function _show_overlay(number) {
        _remove_overlay();
        var div = document.createElement("div");
        div.id = "ec-overlay";
        div.innerHTML = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">'
            + '<strong style="font-size:16px;">' + number + '</strong>'
            + '<button onclick="window._ec_hangup()" style="background:#dc3545;color:#fff;border:none;'
            + 'border-radius:6px;padding:5px 12px;cursor:pointer;font-size:13px;">📵 Hang Up</button>'
            + '</div>'
            + '<div style="height:6px;background:#e2e6ea;border-radius:3px;overflow:hidden;margin-bottom:6px;">'
            + '<div id="ec-ov-bar" style="height:100%;width:10%;background:linear-gradient(90deg,#2490EF,#28a745);'
            + 'border-radius:3px;transition:width 0.6s ease;"></div>'
            + '</div>'
            + '<div id="ec-ov-msg" style="text-align:center;font-size:12px;font-weight:600;color:#2490EF;">'
            + '🔄 Connecting...</div>';
        div.style.cssText = "position:fixed;top:20px;left:50%;transform:translateX(-50%);"
            + "z-index:999999;background:#fff;border-radius:12px;padding:16px 20px;width:320px;"
            + "box-shadow:0 8px 32px rgba(0,0,0,0.18);border:2px solid #2490EF;"
            + "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;";
        document.body.appendChild(div);
    }

    function _update_overlay(s, msg, pct) {
        var bar = document.getElementById("ec-ov-bar");
        var msgEl = document.getElementById("ec-ov-msg");
        if (!bar || !msgEl) return;
        bar.style.width = (pct || 0) + "%";
        msgEl.textContent = msg || "";
        msgEl.style.color = s === S.FAILED ? "#dc3545" : s === S.CONNECTED ? "#28a745" : "#2490EF";
        if (s === S.IDLE || s === S.ENDED || s === S.FAILED) {
            setTimeout(_remove_overlay, 3500);
        }
    }

    function _remove_overlay() {
        var el = document.getElementById("ec-overlay");
        if (el) el.remove();
    }

    // ── Incoming call screen-pop ──────────────────────────────────────────────
    function _show_incoming(data) {
        var existing = document.getElementById("ec-incoming");
        if (existing) existing.remove();

        var div = document.createElement("div");
        div.id = "ec-incoming";
        div.style.cssText = "position:fixed;top:20px;right:20px;z-index:999999;background:#fff;"
            + "border-radius:12px;padding:16px;width:280px;"
            + "box-shadow:0 8px 32px rgba(0,0,0,0.18);border:2px solid #28a745;"
            + "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;"
            + "animation:ec_pulse 1s infinite alternate;";
        div.innerHTML = '<div style="font-weight:700;font-size:15px;margin-bottom:4px;">📲 Incoming Call</div>'
            + '<div style="color:#6c757d;font-size:13px;margin-bottom:12px;">'
            + (data.caller_name || data.caller_number || "Unknown") + '</div>'
            + '<div style="display:flex;gap:8px;">'
            + '<button id="ec-ans-btn" style="flex:1;background:#28a745;color:#fff;border:none;'
            + 'border-radius:8px;padding:9px;cursor:pointer;font-weight:600;">✅ Answer</button>'
            + '<button id="ec-dec-btn" style="flex:1;background:#dc3545;color:#fff;border:none;'
            + 'border-radius:8px;padding:9px;cursor:pointer;font-weight:600;">❌ Decline</button>'
            + '</div>';
        document.body.appendChild(div);

        div.querySelector("#ec-ans-btn").addEventListener("click", function() {
            div.remove();
            state.tcl_name = data.tcl_name;
            _update_call_status("Answered");
            // Use offer from data, or from the signal that arrived after the popup was shown
            var offer    = data._pending_offer || state._pending_offer;
            var fromUser = data.from_user      || state._pending_from_user;
            if (offer && fromUser) {
                _answer_webrtc(fromUser, offer);
            } else {
                // Offer not yet arrived — wait briefly then retry
                setTimeout(function() {
                    var o = state._pending_offer;
                    var f = state._pending_from_user;
                    if (o && f) { _answer_webrtc(f, o); }
                    else { _set_state(S.FAILED, "❌ No offer received", 0); }
                }, 2000);
            }
            if (state.settings.auto_open_record_on_inbound && data.lead)    frappe.set_route("Form","Lead", data.lead);
            if (state.settings.auto_open_record_on_inbound && data.contact) frappe.set_route("Form","Contact", data.contact);
        });
        div.querySelector("#ec-dec-btn").addEventListener("click", function() {
            div.remove();
            _send_signal(data.from_user || "", "reject", {});
            _update_call_status("Declined");
        });

        // Auto-dismiss after 30s
        setTimeout(function() { if (div.parentNode) { div.remove(); _update_call_status("Missed"); } }, 30000);
    }

    // ── Realtime listeners ────────────────────────────────────────────────────
    function _bind_realtime() {
        if (typeof frappe === "undefined" || !frappe.realtime) {
            setTimeout(_bind_realtime, 500);
            return;
        }
        frappe.realtime.on("ecclesia_incoming_call", function(data) {
            // Attach from_user (caller_number IS the user email for internal calls)
            data.from_user = data.from_user || data.caller_number;
            _show_incoming(data);
        });
        frappe.realtime.on("ecclesia_webrtc_signal", function(data) {
            // Server sends: { signal_type, from_user, payload: { offer/answer/candidate } }
            var type    = data.signal_type;
            var payload = data.payload || {};
            if (type === "offer") {
                // Store pending offer so Answer button can use it
                state._pending_offer     = payload.offer;
                state._pending_from_user = data.from_user;
                // If incoming popup already visible, attach offer to it; else show popup
                var existing = document.getElementById("ec-incoming");
                if (existing) {
                    existing._from_user     = data.from_user;
                    existing._pending_offer = payload.offer;
                } else {
                    _show_incoming({
                        tcl_name:      data.tcl_name,
                        caller_number: data.from_user,
                        caller_name:   data.from_user,
                        from_user:     data.from_user,
                        _pending_offer: payload.offer
                    });
                }
            } else if (type === "answer" && state.peer_connection) {
                state.peer_connection.setRemoteDescription(new RTCSessionDescription(payload.answer))
                    .then(function() { _set_state(S.CONNECTED, "✅ Connected", 100); })
                    .catch(function(e) { console.error("SRD answer error:", e); });
            } else if (type === "ice_candidate" && state.peer_connection) {
                state.peer_connection.addIceCandidate(new RTCIceCandidate(payload.candidate)).catch(function(){});
            } else if (type === "hang_up") {
                _close_webrtc();
                _set_state(S.ENDED, "📵 Call ended", 100);
            } else if (type === "reject") {
                _close_webrtc();
                _set_state(S.FAILED, "❌ Call rejected", 0);
            }
        });
        frappe.realtime.on("ecclesia_telephone_call_log_created", function() { _update_badge(); });
    }

    // ── Missed call badge ─────────────────────────────────────────────────────
    function _update_badge() {
        var badge = document.getElementById("ec-badge");
        if (!badge) return;
        frappe.call({
            method: "frappe.client.get_count",
            args: { doctype: "Telephone Call Log", filters: { caller_user: frappe.session.user, status: "Missed" } },
            callback: function(r) {
                if (r.message > 0) {
                    badge.textContent = r.message > 9 ? "9+" : r.message;
                    badge.style.display = "block";
                } else {
                    badge.style.display = "none";
                }
            }
        });
    }

    // ── Public API ────────────────────────────────────────────────────────────
    // call_number is called by CRM form buttons
    window.ecclesia_telephone = {
        call_number: function(number, doctype, docname) {
            // If widget not built yet, try init first then retry
            if (!document.getElementById("ec-widget")) {
                _try_init();
                setTimeout(function() { window.ecclesia_telephone.call_number(number, doctype, docname); }, 700);
                return;
            }
            state.dial_buffer = number;
            document.getElementById("ec-num").value = number;
            // Open panel so user sees progress
            var panel = document.getElementById("ec-panel");
            if (panel) panel.style.display = "block";
            _do_call(number, doctype, docname);
        }
    };

    // Inject pulse animation style
    var styleEl = document.createElement("style");
    styleEl.textContent = "@keyframes ec_pulse{from{box-shadow:0 0 0 0 rgba(40,167,69,0.4)}to{box-shadow:0 0 0 12px rgba(40,167,69,0)}}";
    document.head.appendChild(styleEl);

})();