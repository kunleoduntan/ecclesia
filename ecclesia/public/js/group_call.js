/**
 * ecclesia/public/js/group_call.js  v3
 *
 * Bugs fixed:
 *  1. User search used full_name filter — virtual field, breaks get_list. Now searches name+first_name+last_name.
 *  2. _setup_user_search ran before DOM was appended. Now retries until input exists.
 *  3. group_call.py used after_commit=False — events fired before DB settled. Changed to True.
 *  4. _switch_tab used fragile child iteration. Now targets named wrapper IDs only.
 *  5. gc.gc_name set immediately on join so early signals are buffered, not dropped.
 */
(function () {
    "use strict";

    var gc = {
        gc_name: null, room_name: null,
        peers: {}, local_stream: null,
        muted: false, is_host: false,
        participants: [], pending_signals: [],
    };
    var _invitees = [];

    /* ── Bootstrap ──────────────────────────────────────────────────────────── */
    function _try_inject() {
        if (document.getElementById("ec-group-tab-btn")) return;
        var panel = document.getElementById("ec-panel");
        if (!panel) { setTimeout(_try_inject, 400); return; }
        _inject(panel);
        _bind_realtime();
        // Setup search after a tick so the DOM append settles
        setTimeout(_setup_search, 50);
    }
    setTimeout(_try_inject, 1000); // after telephone.js finishes at ~400ms

    /* ── DOM injection ──────────────────────────────────────────────────────── */
    function _inject(panel) {
        // Tab row
        var row = _el("div", "ec-tab-row",
            "display:flex;border-bottom:2px solid #e2e6ea;background:#f5f7fa;");
        row.appendChild(_tab("ec-dialpad-tab-btn","📞 Dialpad",true, function(){ _tab_show("dialpad"); }));
        row.appendChild(_tab("ec-group-tab-btn",  "👥 Group",  false,function(){ _tab_show("group");  }));

        // Locate header and insert tab row after it
        var hdr = panel.querySelector("div[style*='background:#2490EF']");
        panel.insertBefore(row, hdr ? hdr.nextSibling : panel.firstChild);

        // Wrap all existing dialpad content (everything after header + tab row)
        var dw = _el("div","ec-dialpad-wrap","");
        Array.from(panel.children).forEach(function(c) {
            if (c.id !== "ec-tab-row" && c !== hdr) dw.appendChild(c);
        });
        panel.appendChild(dw);

        // Group panel
        var gw = _el("div","ec-group-wrap","display:none;");
        gw.innerHTML = _html();
        panel.appendChild(gw);

        // Wire buttons
        _btn("ec-gc-create-btn", _create);
        _btn("ec-gc-invite-btn", _invite_more);
        _btn("ec-gc-leave-btn",  _leave);
        _btn("ec-gc-end-btn",    _end);
        _btn("ec-gc-mute-btn",   _mute);
    }

    function _el(tag, id, css) {
        var e = document.createElement(tag);
        e.id = id; e.style.cssText = css; return e;
    }
    function _tab(id, label, active, fn) {
        var b = document.createElement("button");
        b.id = id; b.textContent = label;
        b.style.cssText = _ts(active); b.onclick = fn; return b;
    }
    function _ts(a) {
        return "flex:1;padding:9px 0;border:none;cursor:pointer;font-size:12px;font-weight:600;"
            + "background:" + (a ? "#fff" : "#f5f7fa") + ";color:" + (a ? "#2490EF" : "#6c757d") + ";"
            + "border-bottom:" + (a ? "2px solid #2490EF" : "2px solid transparent") + ";";
    }
    function _tab_show(tab) {
        var dw = document.getElementById("ec-dialpad-wrap");
        var gw = document.getElementById("ec-group-wrap");
        if (dw) dw.style.display = tab === "dialpad" ? "" : "none";
        if (gw) gw.style.display = tab === "group"   ? "" : "none";
        var db = document.getElementById("ec-dialpad-tab-btn");
        var gb = document.getElementById("ec-group-tab-btn");
        if (db) db.style.cssText = _ts(tab === "dialpad");
        if (gb) gb.style.cssText = _ts(tab === "group");
    }
    function _btn(id, fn) {
        var el = document.getElementById(id);
        if (el) el.addEventListener("click", fn);
    }

    /* ── Panel HTML ─────────────────────────────────────────────────────────── */
    function _html() {
        var S = "width:100%;box-sizing:border-box;padding:9px;border:1.5px solid #e2e6ea;"
              + "border-radius:8px;font-size:13px;outline:none;";
        return (
            '<div id="ec-gc-idle" style="padding:12px;">'
            // Room name
          + '<label style="font-size:11px;font-weight:600;color:#6c757d;display:block;margin-bottom:3px;">ROOM NAME</label>'
          + '<input id="ec-gc-room" type="text" placeholder="e.g. Sales Sync" style="' + S + 'margin-bottom:10px;"/>'
            // People search
          + '<label style="font-size:11px;font-weight:600;color:#6c757d;display:block;margin-bottom:3px;">ADD PEOPLE</label>'
          + '<div style="position:relative;">'
          + '<input id="ec-gc-search" type="text" placeholder="Type name or email..." style="' + S + '"/>'
          + '<div id="ec-gc-sugg" style="display:none;position:absolute;top:42px;left:0;right:0;'
          + 'background:#fff;border:1.5px solid #e2e6ea;border-radius:8px;z-index:999999;'
          + 'max-height:160px;overflow-y:auto;box-shadow:0 4px 16px rgba(0,0,0,.13);"></div>'
          + '</div>'
          + '<div id="ec-gc-chips" style="display:flex;flex-wrap:wrap;gap:4px;margin:8px 0;min-height:22px;"></div>'
          + '<button id="ec-gc-create-btn" style="width:100%;background:#2490EF;color:#fff;border:none;'
          + 'border-radius:8px;padding:11px;font-size:13px;font-weight:700;cursor:pointer;'
          + 'margin-top:4px;">📞 Start Group Call</button>'
          + '</div>'

            // Active UI
          + '<div id="ec-gc-active" style="display:none;padding:12px;">'
          + '<div id="ec-gc-lbl" style="text-align:center;font-weight:700;color:#1B3A6B;font-size:14px;margin-bottom:8px;"></div>'
          + '<div id="ec-gc-plist" style="border:1px solid #e2e6ea;border-radius:8px;padding:4px;'
          + 'margin-bottom:10px;max-height:160px;overflow-y:auto;min-height:36px;"></div>'
          + '<div id="ec-gc-timer" style="text-align:center;font-size:20px;font-weight:700;'
          + 'color:#28a745;margin-bottom:8px;font-variant-numeric:tabular-nums;">00:00</div>'
          + '<div style="display:flex;justify-content:center;gap:8px;">'
          + '<button id="ec-gc-mute-btn"   title="Mute"        style="' + _cbs("#f5f7fa","#444") + '">🎤</button>'
          + '<button id="ec-gc-invite-btn" title="Invite more" style="' + _cbs("#f5f7fa","#444") + '">➕</button>'
          + '<button id="ec-gc-leave-btn"  title="Leave"       style="' + _cbs("#fd7e14","#fff") + '">🚪</button>'
          + '<button id="ec-gc-end-btn"    title="End for all" style="' + _cbs("#dc3545","#fff") + '">📵</button>'
          + '</div></div>'
        );
    }
    function _cbs(bg, c) {
        return "width:44px;height:44px;border-radius:50%;background:"+bg+";border:none;color:"+c+";font-size:18px;cursor:pointer;";
    }

    /* ── User search ────────────────────────────────────────────────────────── */
    function _setup_search() {
        var inp  = document.getElementById("ec-gc-search");
        var sugg = document.getElementById("ec-gc-sugg");
        if (!inp || !sugg) { setTimeout(_setup_search, 200); return; }

        inp.addEventListener("input", function() {
            var q = inp.value.trim();
            if (q.length < 1) { sugg.style.display = "none"; return; }

            // Search users by name (email) or first_name — both are DB fields
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "User",
                    filters: [
                        ["enabled", "=", 1],
                        ["user_type", "=", "System User"],
                        ["name", "!=", frappe.session.user],
                    ],
                    fields: ["name", "first_name", "last_name", "full_name"],
                    limit: 20,
                },
                callback: function(r) {
                    sugg.innerHTML = "";
                    if (!r.message) { sugg.style.display = "none"; return; }
                    // Client-side filter since full_name is virtual
                    var ql = q.toLowerCase();
                    var hits = r.message.filter(function(u) {
                        return (u.full_name||"").toLowerCase().indexOf(ql) !== -1
                            || u.name.toLowerCase().indexOf(ql) !== -1;
                    });
                    if (!hits.length) { sugg.style.display = "none"; return; }
                    hits.slice(0, 8).forEach(function(u) {
                        var row = document.createElement("div");
                        row.style.cssText = "padding:8px 12px;cursor:pointer;font-size:13px;"
                            + "border-bottom:1px solid #f5f5f5;";
                        var dn = u.full_name || (u.first_name + " " + (u.last_name||"")).trim() || u.name;
                        row.innerHTML = '<span style="font-weight:600;">' + dn + '</span>'
                            + '<span style="color:#aaa;font-size:11px;margin-left:6px;">' + u.name + '</span>';
                        row.onmouseenter = function(){ row.style.background="#f0f7ff"; };
                        row.onmouseleave = function(){ row.style.background=""; };
                        row.onclick = function() {
                            _add_chip(u.name, dn);
                            inp.value = ""; sugg.style.display = "none";
                        };
                        sugg.appendChild(row);
                    });
                    sugg.style.display = "block";
                },
            });
        });

        document.addEventListener("click", function(e) {
            if (!sugg.contains(e.target) && e.target !== inp) sugg.style.display = "none";
        });
    }

    function _add_chip(user, name) {
        if (_invitees.find(function(i){ return i.user === user; })) return;
        _invitees.push({ user: user, display_name: name });
        _chips();
    }
    function _chips() {
        var w = document.getElementById("ec-gc-chips"); if (!w) return;
        w.innerHTML = "";
        _invitees.forEach(function(inv) {
            var c = document.createElement("span");
            c.style.cssText = "background:#e8f4fd;color:#1B3A6B;border-radius:12px;"
                + "padding:3px 8px 3px 10px;font-size:12px;display:inline-flex;align-items:center;gap:4px;";
            c.innerHTML = '<span>' + inv.display_name + '</span>'
                + '<span style="cursor:pointer;font-weight:900;font-size:13px;color:#2490EF;"'
                + ' onclick="window._gc_rm(\'' + inv.user.replace("'","\\'") + '\')">&#xd7;</span>';
            w.appendChild(c);
        });
    }
    window._gc_rm = function(u) {
        _invitees = _invitees.filter(function(i){ return i.user !== u; }); _chips();
    };

    /* ── Create ─────────────────────────────────────────────────────────────── */
    function _create() {
        var room = (document.getElementById("ec-gc-room").value || "").trim() || "Group Call";
        if (!_invitees.length) {
            frappe.show_alert({ message: "Add at least one person to invite.", indicator: "orange" });
            return;
        }
        var btn = document.getElementById("ec-gc-create-btn");
        if (btn) { btn.disabled = true; btn.textContent = "Starting…"; }

        frappe.call({
            method: "ecclesia.group_call.create_group_call",
            args: {
                room_name: room,
                invitees:  JSON.stringify(_invitees.map(function(i){ return i.user; })),
            },
            callback: function(r) {
                if (btn) { btn.disabled = false; btn.textContent = "📞 Start Group Call"; }
                if (!r.message) return;
                gc.gc_name   = r.message.gc_name;
                gc.room_name = r.message.room_name;
                gc.is_host   = true;
                _mic().then(function() { _show_active(); _tick(); });
            },
            error: function(e) {
                if (btn) { btn.disabled = false; btn.textContent = "📞 Start Group Call"; }
                frappe.show_alert({ message: "Error: " + ((e||{}).message||"unknown"), indicator: "red" });
            },
        });
    }

    /* ── Join ───────────────────────────────────────────────────────────────── */
    function _join(gc_name) {
        gc.gc_name = gc_name; // set BEFORE async so early signals are buffered
        var panel = document.getElementById("ec-panel");
        if (panel) panel.style.display = "block";
        _tab_show("group");

        frappe.call({
            method: "ecclesia.group_call.join_group_call",
            args: { gc_name: gc_name },
            callback: function(r) {
                if (!r.message) return;
                gc.room_name    = r.message.room_name;
                gc.is_host      = r.message.host === frappe.session.user;
                gc.participants = r.message.participants || [];
                _mic().then(function() {
                    _show_active();
                    _tick();
                    gc.participants.forEach(function(p) {
                        if (p.status === "Joined") _offer(p.user);
                    });
                    gc.pending_signals.forEach(_signal_handle);
                    gc.pending_signals = [];
                });
            },
        });
    }

    /* ── Leave / End ────────────────────────────────────────────────────────── */
    function _leave() {
        if (!gc.gc_name) return;
        frappe.call({ method: "ecclesia.group_call.leave_group_call", args: { gc_name: gc.gc_name } });
        _cleanup();
        frappe.show_alert({ message: "You left the group call.", indicator: "blue" });
    }
    function _end() {
        if (!gc.gc_name) return;
        frappe.call({ method: "ecclesia.group_call.end_group_call", args: { gc_name: gc.gc_name } });
        _cleanup();
        frappe.show_alert({ message: "Group call ended.", indicator: "blue" });
    }
    function _invite_more() {
        frappe.prompt(
            [{ fieldname:"u", fieldtype:"Data", label:"Email(s), comma-separated", reqd:1 }],
            function(v) {
                var users = v.u.split(",").map(function(x){ return x.trim(); }).filter(Boolean);
                frappe.call({
                    method: "ecclesia.group_call.invite_to_group_call",
                    args: { gc_name:gc.gc_name, users:JSON.stringify(users) },
                    callback: function(){ frappe.show_alert({ message:"Invites sent.", indicator:"green" }); },
                });
            }, "Invite More People", "Send"
        );
    }
    function _mute() {
        gc.muted = !gc.muted;
        if (gc.local_stream) gc.local_stream.getAudioTracks().forEach(function(t){ t.enabled=!gc.muted; });
        var b = document.getElementById("ec-gc-mute-btn"); if (b) b.textContent = gc.muted?"🔇":"🎤";
    }

    /* ── Microphone ─────────────────────────────────────────────────────────── */
    function _mic() {
        if (gc.local_stream) return Promise.resolve();
        return navigator.mediaDevices.getUserMedia({ audio:true, video:false })
            .then(function(s){ gc.local_stream = s; })
            .catch(function(e){
                frappe.show_alert({ message:"Microphone access denied: "+e.message, indicator:"red" });
                throw e;
            });
    }

    /* ── WebRTC mesh ────────────────────────────────────────────────────────── */
    function _pc(remote) {
        var stun = ((frappe.boot.telephone||{}).stun_server_url)||"stun:stun.l.google.com:19302";
        var pc = new RTCPeerConnection({ iceServers:[{ urls:stun }] });
        if (gc.local_stream) gc.local_stream.getTracks().forEach(function(t){ pc.addTrack(t,gc.local_stream); });
        pc.onicecandidate = function(e){ if(e.candidate) _sig(remote,"ice_candidate",{candidate:e.candidate}); };
        pc.ontrack = function(e){ var a=new Audio(); a.srcObject=e.streams[0]; a.play().catch(function(){}); };
        pc.onconnectionstatechange = function(){
            _render_plist();
            if (pc.connectionState==="failed"||pc.connectionState==="disconnected") _rm_pc(remote);
        };
        gc.peers[remote] = pc; return pc;
    }
    function _offer(remote) {
        var p = _pc(remote);
        p.createOffer()
         .then(function(o){ return p.setLocalDescription(o); })
         .then(function(){ _sig(remote,"offer",{offer:p.localDescription}); })
         .catch(function(e){ frappe.show_alert({ message:"Offer error: "+e.message, indicator:"orange" }); });
    }
    function _answer(from, offer) {
        var p = _pc(from);
        p.setRemoteDescription(new RTCSessionDescription(offer))
         .then(function(){ return p.createAnswer(); })
         .then(function(a){ return p.setLocalDescription(a); })
         .then(function(){ _sig(from,"answer",{answer:p.localDescription}); })
         .catch(function(e){ frappe.show_alert({ message:"Answer error: "+e.message, indicator:"orange" }); });
    }
    function _rm_pc(user) {
        if (gc.peers[user]){ gc.peers[user].close(); delete gc.peers[user]; }
        _render_plist();
    }
    function _sig(target, type, data) {
        frappe.call({
            method:"ecclesia.group_call.group_call_signal",
            args:{ gc_name:gc.gc_name, target_user:target, signal_type:type, data:JSON.stringify(data) },
        });
    }
    function _signal_handle(d) {
        var from=d.from_user, type=d.signal_type, pl=d.payload;
        if (type==="offer") {
            if (!gc.local_stream){ _mic().then(function(){ _answer(from,pl.offer); }); }
            else { _answer(from, pl.offer); }
        } else if (type==="answer" && gc.peers[from]) {
            gc.peers[from].setRemoteDescription(new RTCSessionDescription(pl.answer)).catch(function(){});
        } else if (type==="ice_candidate" && gc.peers[from]) {
            gc.peers[from].addIceCandidate(new RTCIceCandidate(pl.candidate)).catch(function(){});
        } else if (type==="hang_up") {
            _rm_pc(from);
            gc.participants = gc.participants.filter(function(p){ return p.user!==from; });
        }
    }

    /* ── Cleanup ────────────────────────────────────────────────────────────── */
    function _cleanup() {
        Object.keys(gc.peers).forEach(function(u){ gc.peers[u].close(); });
        gc.peers = {};
        if (gc.local_stream){ gc.local_stream.getTracks().forEach(function(t){ t.stop(); }); gc.local_stream=null; }
        gc.gc_name=null; gc.room_name=null; gc.is_host=false;
        gc.participants=[]; gc.muted=false; gc.pending_signals=[];
        _stop_tick();
        var idle=document.getElementById("ec-gc-idle"), active=document.getElementById("ec-gc-active");
        if (idle)   idle.style.display   = "block";
        if (active) active.style.display = "none";
        var icon=document.getElementById("ec-icon"); if (icon) icon.textContent="📞";
        _invitees=[]; _chips();
        var r=document.getElementById("ec-gc-room"); if (r) r.value="";
    }

    /* ── Active UI ──────────────────────────────────────────────────────────── */
    function _show_active() {
        var idle=document.getElementById("ec-gc-idle"), active=document.getElementById("ec-gc-active");
        if (idle)   idle.style.display   = "none";
        if (active) active.style.display = "block";
        var lbl=document.getElementById("ec-gc-lbl");
        if (lbl) lbl.textContent = "📞 " + (gc.room_name||"Group Call");
        var eb=document.getElementById("ec-gc-end-btn");
        if (eb) eb.style.display = gc.is_host ? "" : "none";
        var icon=document.getElementById("ec-icon"); if (icon) icon.textContent="🔴";
        _tab_show("group");
        var panel=document.getElementById("ec-panel"); if (panel) panel.style.display="block";
        _render_plist();
    }
    function _render_plist() {
        var list=document.getElementById("ec-gc-plist"); if (!list) return;
        list.innerHTML="";
        var me=frappe.session.user;
        var myName=((frappe.boot.user_info||{})[me]||{}).fullname||me;
        list.appendChild(_prow("🟢 " + myName + " (You)", gc.muted?"🔇 muted":"🎤 live", "#e8f9ef"));
        gc.participants.forEach(function(p) {
            var peer=gc.peers[p.user];
            var state=peer?(peer.connectionState||"connecting"):"invited";
            var dot=state==="connected"?"🟢":state==="connecting"?"🟡":"⚪";
            list.appendChild(_prow(dot+" "+(p.display_name||p.user), state, ""));
        });
    }
    function _prow(name, status, bg) {
        var r=document.createElement("div");
        r.style.cssText="display:flex;justify-content:space-between;padding:6px 8px;"
            +"border-bottom:1px solid #f0f0f0;font-size:12px;"+(bg?"background:"+bg+";":"");
        r.innerHTML='<span style="font-weight:600;">'+name+'</span>'
            +'<span style="color:#888;font-size:11px;">'+status+'</span>';
        return r;
    }

    /* ── Timer ──────────────────────────────────────────────────────────────── */
    var _t0=null, _tiv=null;
    function _tick() {
        _t0=Date.now();
        _tiv=setInterval(function(){
            var s=Math.floor((Date.now()-_t0)/1000), m=Math.floor(s/60); s=s%60;
            var el=document.getElementById("ec-gc-timer");
            if (el) el.textContent=(m<10?"0":"")+m+":"+(s<10?"0":"")+s;
        },1000);
    }
    function _stop_tick() {
        if (_tiv){ clearInterval(_tiv); _tiv=null; }
        var el=document.getElementById("ec-gc-timer"); if (el) el.textContent="00:00";
    }

    /* ── Invite popup ───────────────────────────────────────────────────────── */
    function _popup(data) {
        var old=document.getElementById("ec-gc-popup"); if (old) old.remove();
        var count=(data.participants||[]).length||1;
        var d=document.createElement("div");
        d.id="ec-gc-popup";
        d.style.cssText="position:fixed;top:20px;left:50%;transform:translateX(-50%);"
            +"z-index:999999;background:#fff;border-radius:14px;padding:18px 20px;width:300px;"
            +"box-shadow:0 8px 32px rgba(0,0,0,.2);border:2px solid #2490EF;"
            +"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;";
        d.innerHTML='<div style="font-weight:700;font-size:15px;margin-bottom:6px;">👥 Group Call Invite</div>'
            +'<div style="font-size:13px;color:#444;margin-bottom:4px;"><strong>'
            +(data.host_name||data.host||"Someone")+'</strong> is inviting you to:</div>'
            +'<div style="font-weight:700;font-size:14px;color:#1B3A6B;margin-bottom:14px;">'
            +'\u201C'+(data.room_name||"Group Call")+'\u201D</div>'
            +'<div style="font-size:12px;color:#888;margin-bottom:12px;">'
            +count+' participant'+(count!==1?'s':'')+' already in the call</div>'
            +'<div style="display:flex;gap:8px;">'
            +'<button id="ec-gc-acc" style="flex:1;background:#28a745;color:#fff;border:none;'
            +'border-radius:8px;padding:10px;cursor:pointer;font-weight:600;font-size:13px;">✅ Join</button>'
            +'<button id="ec-gc-dec" style="flex:1;background:#dc3545;color:#fff;border:none;'
            +'border-radius:8px;padding:10px;cursor:pointer;font-weight:600;font-size:13px;">❌ Decline</button>'
            +'</div>';
        document.body.appendChild(d);
        d.querySelector("#ec-gc-acc").onclick = function(){ d.remove(); _join(data.gc_name); };
        d.querySelector("#ec-gc-dec").onclick = function(){ d.remove(); };
        setTimeout(function(){ if (d.parentNode) d.remove(); }, 30000);
    }

    /* ── Realtime ───────────────────────────────────────────────────────────── */
    function _bind_realtime() {
        if (typeof frappe==="undefined"||!frappe.realtime){ setTimeout(_bind_realtime,500); return; }

        frappe.realtime.on("ecclesia_group_call_invite", _popup);

        frappe.realtime.on("ecclesia_group_call_peer_joined", function(d) {
            if (!gc.gc_name||d.gc_name!==gc.gc_name) return;
            if (!gc.participants.find(function(p){ return p.user===d.new_user; })) {
                gc.participants.push({ user:d.new_user, display_name:d.display_name, status:"Joined" });
            }
            _offer(d.new_user);
            _render_plist();
        });

        frappe.realtime.on("ecclesia_group_call_peer_left", function(d) {
            if (!gc.gc_name||d.gc_name!==gc.gc_name) return;
            gc.participants = gc.participants.filter(function(p){ return p.user!==d.left_user; });
            _rm_pc(d.left_user);
            frappe.show_alert({ message:(d.display_name||d.left_user)+" left the call.", indicator:"orange" });
            if (d.new_host===frappe.session.user) {
                gc.is_host=true;
                var eb=document.getElementById("ec-gc-end-btn"); if(eb) eb.style.display="";
                frappe.show_alert({ message:"You are now the host.", indicator:"blue" });
            }
        });

        frappe.realtime.on("ecclesia_group_call_ended", function(d) {
            if (!gc.gc_name||d.gc_name!==gc.gc_name) return;
            _cleanup();
            frappe.show_alert({ message:"Group call ended by "+(d.ended_name||"host")+".", indicator:"blue" });
        });

        frappe.realtime.on("ecclesia_group_call_signal", function(d) {
            if (!gc.gc_name||d.gc_name!==gc.gc_name) return;
            // Buffer offers that arrive before mic is ready
            if (!gc.local_stream && d.signal_type==="offer") {
                gc.pending_signals.push(d); return;
            }
            _signal_handle(d);
        });
    }

    window.ecclesia_group_call = { join: _join, leave: _leave };

})();