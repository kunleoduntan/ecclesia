/**
 * ecclesia/public/js/internal_chat.js
 * Internal Chat Widget — floating, world-class UI for ERPNext desk
 * Architecture mirrors ecclesia/telephone.js pattern
 *
 * Features:
 *  - Floating toggle button with unread badge
 *  - Conversation list (DMs + Groups) with search
 *  - Full chat window: messages, reactions, replies, typing, media
 *  - New DM / New Group creation flows
 *  - Realtime via frappe.realtime (Socket.io)
 *  - Persists open conversation across page navigations
 */

(function () {
    "use strict";

    // =========================================================================
    // CONSTANTS & STATE
    // =========================================================================

    var WIDGET_ID      = "ic-widget";
    var PANEL_ID       = "ic-panel";
    var EMOJI_LIST     = ["👍","❤️","😂","😮","😢","🔥","🎉","👏","💯","✅"];
    var MAX_FILE_MB    = 25;

    // Typing debounce handles
    var _typing_timer  = null;
    var _is_typing     = false;

    // In-memory state
    var S = {
        conversations : [],   // [{name, chat_name, chat_type, last_message_preview, last_message_at, unread_count, members}]
        active_conv   : null, // currently open conversation doc
        messages      : [],   // messages for active_conv
        search_query  : "",
        total_unread  : 0,
        settings      : null,
        current_user  : null,
        current_name  : null,
        users_online  : {},   // { email: bool }
        new_group_step: 0,    // 0=idle, 1=pick members, 2=set name
        new_group_members: [],
        reply_to      : null, // { name, sender_name, body }
        _msg_page     : 0,
        _loading_more : false,
        _search_users_cache: []
    };

    // =========================================================================
    // BOOT — same polling pattern as telephone.js
    // =========================================================================

    function _try_init() {
        if (document.getElementById(WIDGET_ID)) return;
        var boot = (typeof frappe !== "undefined") && frappe.boot;
        if (!boot) { setTimeout(_try_init, 350); return; }

        S.settings    = boot.internal_chat || { enabled: true };
        S.current_user= frappe.session && frappe.session.user;
        S.current_name= (boot.user_info && boot.user_info[S.current_user])
                        ? (boot.user_info[S.current_user].fullname || S.current_user)
                        : S.current_user;

        if (!S.settings.enabled) return;

        _inject_styles();
        _build_widget();
        _bind_global_keys();
        _bind_realtime();
        _load_conversations();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () { setTimeout(_try_init, 500); });
    } else {
        setTimeout(_try_init, 500);
    }

    // =========================================================================
    // STYLES — injected once into <head>
    // =========================================================================

    function _inject_styles() {
        if (document.getElementById("ic-styles")) return;
        var css = `
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

        :root {
            --ic-bg:          #0f1117;
            --ic-surface:     #191d27;
            --ic-surface2:    #20263a;
            --ic-surface3:    #252c40;
            --ic-border:      rgba(255,255,255,0.07);
            --ic-accent:      #4f8ef7;
            --ic-accent2:     #7c5cfc;
            --ic-green:       #23d18b;
            --ic-red:         #f25f5c;
            --ic-amber:       #f4c542;
            --ic-text:        #e8eaf0;
            --ic-muted:       #6b7498;
            --ic-bubble-out:  linear-gradient(135deg,#4f8ef7 0%,#7c5cfc 100%);
            --ic-bubble-in:   #20263a;
            --ic-font:        'DM Sans', -apple-system, sans-serif;
            --ic-mono:        'DM Mono', monospace;
            --ic-radius:      16px;
            --ic-shadow:      0 24px 80px rgba(0,0,0,0.6), 0 4px 24px rgba(79,142,247,0.08);
            --ic-glow:        0 0 0 1px rgba(79,142,247,0.3);
        }

        #ic-widget * { box-sizing: border-box; font-family: var(--ic-font); }

        /* ── Toggle Button ── */
        #ic-toggle {
            width: 54px; height: 54px; border-radius: 50%;
            background: linear-gradient(135deg, #4f8ef7, #7c5cfc);
            border: none; cursor: pointer; position: relative;
            box-shadow: 0 4px 20px rgba(79,142,247,0.45), 0 0 0 0 rgba(79,142,247,0.3);
            transition: transform 0.2s, box-shadow 0.2s;
            display: flex; align-items: center; justify-content: center;
        }
        #ic-toggle:hover { transform: scale(1.08); box-shadow: 0 6px 28px rgba(79,142,247,0.6); }
        #ic-toggle svg { pointer-events: none; }

        #ic-badge {
            position: absolute; top: -2px; right: -2px;
            background: var(--ic-red); color: #fff;
            border-radius: 50%; min-width: 18px; height: 18px;
            font-size: 10px; font-weight: 700; line-height: 18px;
            text-align: center; display: none; padding: 0 3px;
            border: 2px solid transparent;
            background-clip: padding-box;
            box-shadow: 0 0 0 2px var(--ic-bg);
        }

        /* ── Panel ── */
        #ic-panel {
            display: none;
            width: 380px; height: 580px;
            background: var(--ic-bg);
            border-radius: var(--ic-radius);
            box-shadow: var(--ic-shadow);
            border: 1px solid var(--ic-border);
            margin-bottom: 10px;
            overflow: hidden;
            flex-direction: column;
        }
        #ic-panel.open { display: flex; }

        /* ── Panel Header ── */
        .ic-header {
            background: var(--ic-surface);
            padding: 14px 16px;
            display: flex; align-items: center; gap: 10px;
            border-bottom: 1px solid var(--ic-border);
            flex-shrink: 0;
        }
        .ic-header-title {
            flex: 1; font-size: 14px; font-weight: 700;
            color: var(--ic-text); letter-spacing: -0.2px;
        }
        .ic-header-sub {
            font-size: 11px; color: var(--ic-muted); font-weight: 400;
        }
        .ic-hbtn {
            width: 32px; height: 32px; border-radius: 8px;
            background: var(--ic-surface2); border: 1px solid var(--ic-border);
            color: var(--ic-muted); cursor: pointer; display: flex;
            align-items: center; justify-content: center;
            transition: background 0.15s, color 0.15s;
            flex-shrink: 0;
        }
        .ic-hbtn:hover { background: var(--ic-surface3); color: var(--ic-text); }
        .ic-hbtn.active { background: var(--ic-accent); color: #fff; border-color: transparent; }

        /* ── Avatar ── */
        .ic-avatar {
            border-radius: 50%; object-fit: cover; flex-shrink: 0;
            display: flex; align-items: center; justify-content: center;
            font-weight: 700; color: #fff; font-size: 12px;
            background: linear-gradient(135deg, #4f8ef7, #7c5cfc);
            position: relative; overflow: visible !important;
        }
        .ic-avatar .ic-dot {
            position: absolute; bottom: 0; right: 0;
            width: 9px; height: 9px; border-radius: 50%;
            background: var(--ic-muted);
            border: 2px solid var(--ic-bg);
        }
        .ic-avatar .ic-dot.online { background: var(--ic-green); }

        /* ── Conversation List ── */
        #ic-conv-list { flex: 1; overflow-y: auto; }
        #ic-conv-list::-webkit-scrollbar { width: 4px; }
        #ic-conv-list::-webkit-scrollbar-track { background: transparent; }
        #ic-conv-list::-webkit-scrollbar-thumb { background: var(--ic-surface3); border-radius: 2px; }

        .ic-conv-item {
            display: flex; align-items: center; gap: 12px;
            padding: 10px 14px; cursor: pointer;
            transition: background 0.12s;
            border-bottom: 1px solid rgba(255,255,255,0.03);
            position: relative;
        }
        .ic-conv-item:hover { background: var(--ic-surface); }
        .ic-conv-item.active { background: var(--ic-surface2); }
        .ic-conv-item .ic-conv-body { flex: 1; min-width: 0; }
        .ic-conv-item .ic-conv-name {
            font-size: 13px; font-weight: 600; color: var(--ic-text);
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .ic-conv-item .ic-conv-preview {
            font-size: 11.5px; color: var(--ic-muted);
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
            margin-top: 2px;
        }
        .ic-conv-item .ic-conv-meta {
            display: flex; flex-direction: column; align-items: flex-end; gap: 4px;
            flex-shrink: 0;
        }
        .ic-conv-time { font-size: 10px; color: var(--ic-muted); }
        .ic-unread-badge {
            background: var(--ic-accent); color: #fff;
            border-radius: 10px; min-width: 18px; height: 18px;
            font-size: 10px; font-weight: 700; line-height: 18px;
            text-align: center; padding: 0 4px;
        }
        .ic-conv-type-tag {
            font-size: 9px; font-weight: 700; letter-spacing: 0.5px;
            padding: 1px 6px; border-radius: 4px; text-transform: uppercase;
        }
        .ic-conv-type-tag.group { background: rgba(124,92,252,0.2); color: #7c5cfc; }
        .ic-conv-type-tag.dm    { background: rgba(79,142,247,0.15); color: #4f8ef7; }
        .ic-conv-type-tag.doc   { background: rgba(35,209,139,0.15); color: #23d18b; }

        /* ── Search ── */
        .ic-search-wrap {
            padding: 10px 12px; border-bottom: 1px solid var(--ic-border);
            flex-shrink: 0; position: relative;
        }
        .ic-search-wrap svg {
            position: absolute; left: 22px; top: 50%; transform: translateY(-50%);
            pointer-events: none;
        }
        #ic-search {
            width: 100%; background: var(--ic-surface2);
            border: 1px solid var(--ic-border); border-radius: 10px;
            padding: 8px 10px 8px 34px;
            color: var(--ic-text); font-size: 12.5px; outline: none;
            transition: border-color 0.15s;
        }
        #ic-search:focus { border-color: var(--ic-accent); }
        #ic-search::placeholder { color: var(--ic-muted); }

        /* ── Chat View ── */
        #ic-chat-view {
            display: none; flex-direction: column;
            height: 100%;
        }
        #ic-chat-view.open { display: flex; }

        #ic-messages {
            flex: 1; overflow-y: auto; padding: 14px 14px 6px;
            display: flex; flex-direction: column; gap: 2px;
        }
        #ic-messages::-webkit-scrollbar { width: 3px; }
        #ic-messages::-webkit-scrollbar-thumb { background: var(--ic-surface3); border-radius: 2px; }

        /* ── Message Bubbles ── */
        .ic-msg-group { display: flex; flex-direction: column; margin-bottom: 10px; }
        .ic-msg-row {
            display: flex; align-items: flex-end; gap: 8px;
            margin-bottom: 2px;
        }
        .ic-msg-row.out { flex-direction: row-reverse; }
        .ic-msg-row .ic-avatar { width: 26px; height: 26px; font-size: 10px; flex-shrink: 0; }

        .ic-bubble {
            max-width: 70%; padding: 9px 13px; border-radius: 14px;
            font-size: 13px; line-height: 1.5; color: var(--ic-text);
            position: relative; word-break: break-word;
            cursor: default;
        }
        .ic-bubble.in {
            background: var(--ic-bubble-in);
            border-bottom-left-radius: 4px;
        }
        .ic-bubble.out {
            background: var(--ic-bubble-out);
            border-bottom-right-radius: 4px;
            color: #fff;
        }
        .ic-bubble.out .ic-msg-time { color: rgba(255,255,255,0.6); }

        .ic-sender-name {
            font-size: 10.5px; font-weight: 700; color: var(--ic-accent);
            margin-bottom: 2px; margin-left: 34px;
        }

        .ic-msg-time {
            font-size: 10px; color: var(--ic-muted);
            display: inline-block; margin-left: 6px; vertical-align: bottom;
        }
        .ic-msg-tick { font-size: 10px; margin-left: 2px; }

        /* Reply preview inside bubble */
        .ic-reply-preview {
            border-left: 3px solid rgba(255,255,255,0.3);
            padding: 4px 8px; border-radius: 6px;
            margin-bottom: 6px; font-size: 11px;
            background: rgba(0,0,0,0.15);
        }
        .ic-bubble.out .ic-reply-preview { border-color: rgba(255,255,255,0.5); }
        .ic-reply-preview .ic-reply-from { font-weight: 700; margin-bottom: 2px; }
        .ic-reply-preview .ic-reply-body { color: rgba(255,255,255,0.8); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

        /* Reactions */
        .ic-reactions {
            display: flex; flex-wrap: wrap; gap: 3px; margin-top: 4px;
        }
        .ic-reaction-chip {
            background: var(--ic-surface3); border: 1px solid var(--ic-border);
            border-radius: 20px; padding: 2px 7px; font-size: 12px; cursor: pointer;
            transition: background 0.1s; display: flex; align-items: center; gap: 3px;
        }
        .ic-reaction-chip:hover { background: var(--ic-surface2); }
        .ic-reaction-chip .ic-r-count { font-size: 10px; color: var(--ic-muted); }
        .ic-reaction-chip.mine { border-color: var(--ic-accent); background: rgba(79,142,247,0.12); }

        /* Hover actions toolbar */
        .ic-msg-actions {
            display: none; position: absolute; top: -30px;
            background: var(--ic-surface2); border: 1px solid var(--ic-border);
            border-radius: 10px; padding: 4px 6px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.4);
            gap: 2px; z-index: 10; white-space: nowrap;
        }
        .ic-bubble:hover .ic-msg-actions { display: flex; }
        .ic-msg-row.out .ic-msg-actions { right: 0; left: auto; }
        .ic-msg-actions button {
            background: none; border: none; cursor: pointer;
            padding: 3px 5px; border-radius: 6px; font-size: 13px;
            color: var(--ic-muted); transition: background 0.1s, color 0.1s;
        }
        .ic-msg-actions button:hover { background: var(--ic-surface3); color: var(--ic-text); }

        /* Media messages */
        .ic-media-img { max-width: 200px; border-radius: 10px; cursor: pointer; display: block; margin-top: 4px; }
        .ic-media-doc {
            display: flex; align-items: center; gap: 8px;
            background: rgba(0,0,0,0.15); border-radius: 8px; padding: 8px 10px;
            margin-top: 4px; cursor: pointer; text-decoration: none; color: inherit;
        }
        .ic-media-doc:hover { background: rgba(0,0,0,0.25); }
        .ic-media-doc .ic-doc-icon { font-size: 22px; }
        .ic-media-doc .ic-doc-name { font-size: 12px; font-weight: 600; }
        .ic-media-doc .ic-doc-size { font-size: 10px; color: var(--ic-muted); }

        /* Audio player */
        .ic-audio-wrap { display: flex; align-items: center; gap: 8px; margin-top: 4px; min-width: 160px; }
        .ic-audio-wrap button { background: none; border: none; cursor: pointer; font-size: 18px; color: inherit; }
        .ic-audio-progress {
            flex: 1; height: 3px; background: rgba(255,255,255,0.2); border-radius: 2px; cursor: pointer;
        }
        .ic-audio-fill { height: 100%; background: rgba(255,255,255,0.7); border-radius: 2px; width: 0%; transition: width 0.1s; }
        .ic-audio-dur { font-size: 10px; color: rgba(255,255,255,0.6); min-width: 28px; }

        /* Date separator */
        .ic-date-sep {
            text-align: center; font-size: 10.5px; color: var(--ic-muted);
            margin: 10px 0; position: relative;
        }
        .ic-date-sep::before, .ic-date-sep::after {
            content: ''; position: absolute; top: 50%;
            height: 1px; width: 35%; background: var(--ic-border);
        }
        .ic-date-sep::before { left: 0; }
        .ic-date-sep::after  { right: 0; }

        /* System message */
        .ic-sys-msg {
            text-align: center; font-size: 11px; color: var(--ic-muted);
            margin: 4px 0; font-style: italic;
        }

        /* Typing indicator */
        #ic-typing-bar {
            height: 22px; padding: 0 14px; font-size: 11px; color: var(--ic-muted);
            display: none; align-items: center; gap: 6px; flex-shrink: 0;
        }
        #ic-typing-bar.visible { display: flex; }
        .ic-typing-dots { display: flex; gap: 3px; }
        .ic-typing-dots span {
            width: 5px; height: 5px; border-radius: 50%;
            background: var(--ic-muted); display: inline-block;
            animation: ic_bounce 1.2s infinite ease-in-out;
        }
        .ic-typing-dots span:nth-child(2) { animation-delay: 0.2s; }
        .ic-typing-dots span:nth-child(3) { animation-delay: 0.4s; }

        /* Reply bar (reply-to toolbar above input) */
        #ic-reply-bar {
            display: none; padding: 8px 14px; background: var(--ic-surface);
            border-top: 1px solid var(--ic-border);
            flex-direction: row; align-items: center; gap: 8px; flex-shrink: 0;
        }
        #ic-reply-bar.visible { display: flex; }
        #ic-reply-bar .ic-rbar-from { font-size: 11px; font-weight: 700; color: var(--ic-accent); }
        #ic-reply-bar .ic-rbar-body { font-size: 11px; color: var(--ic-muted); flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        #ic-reply-bar button { background: none; border: none; cursor: pointer; color: var(--ic-muted); font-size: 14px; }

        /* Input area */
        #ic-input-area {
            padding: 10px 12px; border-top: 1px solid var(--ic-border);
            background: var(--ic-surface); display: flex; align-items: flex-end;
            gap: 8px; flex-shrink: 0;
        }
        #ic-input {
            flex: 1; background: var(--ic-surface2); border: 1px solid var(--ic-border);
            border-radius: 12px; padding: 10px 12px;
            color: var(--ic-text); font-size: 13px; outline: none;
            resize: none; min-height: 40px; max-height: 100px;
            line-height: 1.5; transition: border-color 0.15s;
            font-family: var(--ic-font);
        }
        #ic-input:focus { border-color: var(--ic-accent); }
        #ic-input::placeholder { color: var(--ic-muted); }

        .ic-input-btn {
            width: 36px; height: 36px; border-radius: 10px;
            background: var(--ic-surface2); border: 1px solid var(--ic-border);
            color: var(--ic-muted); cursor: pointer; display: flex;
            align-items: center; justify-content: center; flex-shrink: 0;
            transition: background 0.12s, color 0.12s, border-color 0.12s;
            font-size: 16px;
        }
        .ic-input-btn:hover { background: var(--ic-surface3); color: var(--ic-text); }
        #ic-send-btn {
            background: linear-gradient(135deg, #4f8ef7, #7c5cfc);
            border-color: transparent; color: #fff;
        }
        #ic-send-btn:hover { opacity: 0.9; }

        /* Emoji picker */
        #ic-emoji-picker {
            display: none; position: absolute; bottom: 60px; right: 12px;
            background: var(--ic-surface2); border: 1px solid var(--ic-border);
            border-radius: 12px; padding: 10px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.5);
            display: none; gap: 6px; flex-wrap: wrap; width: 220px;
        }
        #ic-emoji-picker.open { display: flex; }
        #ic-emoji-picker span {
            font-size: 20px; cursor: pointer; border-radius: 6px; padding: 4px;
            transition: background 0.1s;
        }
        #ic-emoji-picker span:hover { background: var(--ic-surface3); }

        /* Reaction picker (appears above message) */
        .ic-react-picker {
            display: none; position: absolute; top: -46px;
            background: var(--ic-surface2); border: 1px solid var(--ic-border);
            border-radius: 24px; padding: 6px 10px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
            gap: 4px; z-index: 20; white-space: nowrap;
        }
        .ic-react-picker.open { display: flex; }
        .ic-react-picker span { font-size: 18px; cursor: pointer; border-radius: 6px; padding: 2px 4px; transition: transform 0.1s; }
        .ic-react-picker span:hover { transform: scale(1.4); }

        /* New conversation sheet */
        #ic-new-sheet {
            display: none; flex-direction: column;
            position: absolute; inset: 0;
            background: var(--ic-bg); z-index: 30;
            border-radius: var(--ic-radius); overflow: hidden;
        }
        #ic-new-sheet.open { display: flex; }

        .ic-user-row {
            display: flex; align-items: center; gap: 10px;
            padding: 8px 14px; cursor: pointer; border-radius: 8px;
            transition: background 0.1s;
        }
        .ic-user-row:hover { background: var(--ic-surface); }
        .ic-user-row .ic-check {
            width: 18px; height: 18px; border-radius: 50%;
            border: 2px solid var(--ic-border); margin-left: auto;
            display: flex; align-items: center; justify-content: center;
            font-size: 11px; transition: background 0.1s, border-color 0.1s;
        }
        .ic-user-row.selected .ic-check { background: var(--ic-accent); border-color: var(--ic-accent); color: #fff; }

        /* Selected member chips */
        #ic-selected-chips {
            display: flex; flex-wrap: wrap; gap: 6px;
            padding: 8px 14px; min-height: 0;
        }
        .ic-chip {
            background: rgba(79,142,247,0.15); border: 1px solid rgba(79,142,247,0.3);
            border-radius: 20px; padding: 4px 10px 4px 8px;
            display: flex; align-items: center; gap: 6px;
            font-size: 12px; color: var(--ic-accent);
        }
        .ic-chip button { background: none; border: none; cursor: pointer; color: var(--ic-muted); font-size: 12px; padding: 0; line-height: 1; }

        /* Scrollbar generic */
        .ic-scroll::-webkit-scrollbar { width: 4px; }
        .ic-scroll::-webkit-scrollbar-thumb { background: var(--ic-surface3); border-radius: 2px; }

        /* Load earlier */
        #ic-load-earlier {
            text-align: center; padding: 6px;
            font-size: 11px; color: var(--ic-muted); cursor: pointer;
            display: none;
        }
        #ic-load-earlier:hover { color: var(--ic-accent); }

        /* Empty state */
        .ic-empty {
            flex: 1; display: flex; flex-direction: column;
            align-items: center; justify-content: center; gap: 10px;
            color: var(--ic-muted); text-align: center; padding: 20px;
        }
        .ic-empty svg { opacity: 0.2; }
        .ic-empty p { font-size: 13px; line-height: 1.6; }

        /* Animations */
        @keyframes ic_bounce {
            0%,80%,100% { transform: translateY(0); }
            40% { transform: translateY(-5px); }
        }
        @keyframes ic_fade_up {
            from { opacity: 0; transform: translateY(8px); }
            to   { opacity: 1; transform: translateY(0); }
        }
        .ic-msg-group { animation: ic_fade_up 0.2s ease; }

        @keyframes ic_panel_in {
            from { opacity: 0; transform: translateY(12px) scale(0.97); }
            to   { opacity: 1; transform: translateY(0) scale(1); }
        }
        #ic-panel.open { animation: ic_panel_in 0.22s cubic-bezier(0.34,1.56,0.64,1); }

        /* File input hidden */
        #ic-file-input { display: none; }

        /* Image lightbox */
        #ic-lightbox {
            display: none; position: fixed; inset: 0; z-index: 999999;
            background: rgba(0,0,0,0.9); align-items: center; justify-content: center;
            cursor: zoom-out;
        }
        #ic-lightbox.open { display: flex; }
        #ic-lightbox img { max-width: 90vw; max-height: 90vh; border-radius: 8px; }
        `;
        var el = document.createElement("style");
        el.id = "ic-styles";
        el.textContent = css;
        document.head.appendChild(el);
    }

    // =========================================================================
    // BUILD WIDGET
    // =========================================================================

    function _build_widget() {
        // Position mirrors telephone.js
        var pos = (S.settings.chat_position || "Bottom Right");
        var posMap = {
            "Bottom Right": "bottom:90px;right:24px;",
            "Bottom Left":  "bottom:90px;left:24px;",
            "Top Right":    "top:90px;right:24px;",
            "Top Left":     "top:90px;left:24px;"
        };
        var posCSS = posMap[pos] || posMap["Bottom Right"];

        var wrap = document.createElement("div");
        wrap.id = WIDGET_ID;
        wrap.style.cssText = "position:fixed;" + posCSS + "z-index:99998;display:flex;flex-direction:column;align-items:flex-end;";

        wrap.innerHTML = _tpl_panel() + _tpl_toggle();

        document.body.appendChild(wrap);

        // Wire events
        _wire_events();
        _update_badge_count();
    }

    // ── Templates ─────────────────────────────────────────────────────────────

    function _tpl_toggle() {
        return `
        <button id="ic-toggle" onclick="window._ic_toggle()" title="Team Chat (Alt+C)">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
            </svg>
            <span id="ic-badge"></span>
        </button>`;
    }

    function _tpl_panel() {
        return `
        <div id="ic-panel">

            <!-- LIST VIEW -->
            <div id="ic-list-view" style="display:flex;flex-direction:column;height:100%;">
                <!-- Header -->
                <div class="ic-header">
                    <div style="flex:1;">
                        <div class="ic-header-title">Team Chat</div>
                        <div class="ic-header-sub" id="ic-online-count">Loading...</div>
                    </div>
                    <button class="ic-hbtn" id="ic-new-dm-btn" title="New Direct Message" onclick="window._ic_open_new('dm')">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                    </button>
                    <button class="ic-hbtn" id="ic-new-grp-btn" title="New Group" onclick="window._ic_open_new('group')">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 00-3-3.87M9 3.13a4 4 0 010 7.75M23 21v-2a4 4 0 00-3-3.87"/><circle cx="9" cy="7" r="4"/></svg>
                    </button>
                    <button class="ic-hbtn" onclick="window._ic_toggle()" title="Close">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                </div>

                <!-- Search -->
                <div class="ic-search-wrap">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#6b7498" stroke-width="2.5" stroke-linecap="round">
                        <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                    </svg>
                    <input id="ic-search" type="text" placeholder="Search conversations..." />
                </div>

                <!-- Conversation List -->
                <div id="ic-conv-list" class="ic-scroll">
                    <div class="ic-empty">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
                        <p>No conversations yet.<br/>Start a chat or create a group.</p>
                    </div>
                </div>
            </div>

            <!-- CHAT VIEW -->
            <div id="ic-chat-view">
                <!-- Chat header -->
                <div class="ic-header" id="ic-chat-header">
                    <button class="ic-hbtn" onclick="window._ic_back()" title="Back">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
                    </button>
                    <div id="ic-chat-avatar" class="ic-avatar" style="width:34px;height:34px;font-size:13px;"></div>
                    <div style="flex:1;min-width:0;">
                        <div class="ic-header-title" id="ic-chat-name" style="font-size:13px;"></div>
                        <div class="ic-header-sub" id="ic-chat-sub"></div>
                    </div>
                    <button class="ic-hbtn" onclick="window._ic_toggle_info()" title="Info">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                    </button>
                    <button class="ic-hbtn" onclick="window._ic_toggle()" title="Close">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                </div>

                <!-- Messages -->
                <div id="ic-messages" class="ic-scroll">
                    <div id="ic-load-earlier" onclick="window._ic_load_more()">↑ Load earlier messages</div>
                </div>

                <!-- Typing indicator -->
                <div id="ic-typing-bar">
                    <div class="ic-typing-dots"><span></span><span></span><span></span></div>
                    <span id="ic-typing-text"></span>
                </div>

                <!-- Reply bar -->
                <div id="ic-reply-bar">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#4f8ef7" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 14 4 9 9 4"/><path d="M20 20v-7a4 4 0 00-4-4H4"/></svg>
                    <div style="flex:1;min-width:0;">
                        <div class="ic-rbar-from" id="ic-rbar-from"></div>
                        <div class="ic-rbar-body" id="ic-rbar-body"></div>
                    </div>
                    <button onclick="window._ic_cancel_reply()">✕</button>
                </div>

                <!-- Input area -->
                <div id="ic-input-area">
                    <input type="file" id="ic-file-input" accept="*/*" />
                    <button class="ic-input-btn" onclick="window._ic_attach()" title="Attach file">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/></svg>
                    </button>
                    <button class="ic-input-btn" id="ic-emoji-btn" onclick="window._ic_toggle_emoji()" title="Emoji">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg>
                    </button>
                    <textarea id="ic-input" rows="1" placeholder="Message..."></textarea>
                    <button class="ic-input-btn" id="ic-send-btn" onclick="window._ic_send()" title="Send (Enter)">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
                    </button>
                </div>

                <!-- Emoji picker (for new messages) -->
                <div id="ic-emoji-picker">
                    ${EMOJI_LIST.map(e => `<span onclick="window._ic_insert_emoji('${e}')">${e}</span>`).join('')}
                </div>
            </div>

            <!-- NEW CONVERSATION SHEET (overlays panel) -->
            <div id="ic-new-sheet" style="position:absolute;inset:0;z-index:30;background:var(--ic-bg);border-radius:var(--ic-radius);overflow:hidden;display:none;flex-direction:column;">
                <div class="ic-header">
                    <button class="ic-hbtn" onclick="window._ic_close_new()">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="15 18 9 12 15 6"/></svg>
                    </button>
                    <div class="ic-header-title" id="ic-new-title">New Message</div>
                </div>
                <div style="padding:10px 12px;border-bottom:1px solid var(--ic-border);">
                    <input id="ic-user-search" type="text" placeholder="Search people..."
                        style="width:100%;background:var(--ic-surface2);border:1px solid var(--ic-border);border-radius:10px;padding:9px 12px;color:var(--ic-text);font-size:13px;outline:none;font-family:var(--ic-font);" />
                </div>
                <div id="ic-selected-chips"></div>
                <div id="ic-user-list" class="ic-scroll" style="flex:1;overflow-y:auto;padding:6px 8px;"></div>
                <div style="padding:10px 12px;border-top:1px solid var(--ic-border);" id="ic-new-group-name-wrap" style="display:none;">
                    <input id="ic-group-name" type="text" placeholder="Group name..."
                        style="width:100%;background:var(--ic-surface2);border:1px solid var(--ic-border);border-radius:10px;padding:9px 12px;color:var(--ic-text);font-size:13px;outline:none;font-family:var(--ic-font);margin-bottom:8px;" />
                </div>
                <div style="padding:10px 12px;border-top:1px solid var(--ic-border);">
                    <button id="ic-new-confirm" onclick="window._ic_confirm_new()"
                        style="width:100%;padding:11px;border-radius:10px;background:linear-gradient(135deg,#4f8ef7,#7c5cfc);border:none;color:#fff;font-size:13px;font-weight:700;cursor:pointer;font-family:var(--ic-font);">
                        Start Chat
                    </button>
                </div>
            </div>

        </div>

        <!-- Lightbox -->
        <div id="ic-lightbox" onclick="document.getElementById('ic-lightbox').classList.remove('open')">
            <img id="ic-lightbox-img" src="" alt="" />
        </div>
        `;
    }

    // =========================================================================
    // WIRE EVENTS
    // =========================================================================

    function _wire_events() {
        // Search conversations
        var searchEl = document.getElementById("ic-search");
        if (searchEl) {
            searchEl.addEventListener("input", function(e) {
                S.search_query = e.target.value.toLowerCase();
                _render_conv_list();
            });
        }

        // Message input — Enter to send, Shift+Enter newline
        var inputEl = document.getElementById("ic-input");
        if (inputEl) {
            inputEl.addEventListener("keydown", function(e) {
                if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); window._ic_send(); }
            });
            inputEl.addEventListener("input", function() {
                // Auto-resize
                this.style.height = "auto";
                this.style.height = Math.min(this.scrollHeight, 100) + "px";
                // Typing indicator
                _on_typing();
            });
        }

        // User search in new sheet
        var userSearchEl = document.getElementById("ic-user-search");
        if (userSearchEl) {
            userSearchEl.addEventListener("input", function(e) { _search_users(e.target.value); });
        }

        // File input
        var fileEl = document.getElementById("ic-file-input");
        if (fileEl) {
            fileEl.addEventListener("change", function() {
                if (this.files.length) _send_file(this.files[0]);
                this.value = "";
            });
        }

        // Close emoji picker on outside click
        document.addEventListener("click", function(e) {
            var picker = document.getElementById("ic-emoji-picker");
            var btn    = document.getElementById("ic-emoji-btn");
            if (picker && !picker.contains(e.target) && e.target !== btn) {
                picker.classList.remove("open");
            }
        });
    }

    // =========================================================================
    // GLOBAL HANDLERS (inline onclick compatible)
    // =========================================================================

    window._ic_toggle = function() {
        var panel = document.getElementById(PANEL_ID);
        if (!panel) return;
        var isOpen = panel.classList.contains("open");
        if (isOpen) {
            panel.classList.remove("open");
        } else {
            panel.classList.add("open");
            if (S.active_conv) {
                _open_chat_view();
            }
        }
    };

    window._ic_back = function() {
        S.active_conv = null;
        S.reply_to    = null;
        document.getElementById("ic-chat-view").classList.remove("open");
        document.getElementById("ic-list-view").style.display = "flex";
        _load_conversations();
    };

    window._ic_open_conv = function(conv_name) {
        var conv = S.conversations.find(function(c) { return c.name === conv_name; });
        if (!conv) return;
        S.active_conv = conv;
        S.messages    = [];
        S._msg_page   = 0;
        _open_chat_view();
        _load_messages(conv_name);
    };

    window._ic_send = function() {
        var input = document.getElementById("ic-input");
        if (!input) return;
        var body = input.value.trim();
        if (!body || !S.active_conv) return;
        _send_message("text", body, null);
        input.value = "";
        input.style.height = "auto";
        S.reply_to = null;
        _hide_reply_bar();
    };

    window._ic_attach = function() {
        document.getElementById("ic-file-input").click();
    };

    window._ic_toggle_emoji = function() {
        document.getElementById("ic-emoji-picker").classList.toggle("open");
    };

    window._ic_insert_emoji = function(e) {
        var input = document.getElementById("ic-input");
        if (!input) return;
        input.value += e;
        input.focus();
        document.getElementById("ic-emoji-picker").classList.remove("open");
    };

    window._ic_reply_to = function(msg_name) {
        var msg = S.messages.find(function(m){ return m.name === msg_name; });
        if (!msg) return;
        S.reply_to = msg;
        document.getElementById("ic-rbar-from").textContent = msg.sender_name || msg.sender;
        document.getElementById("ic-rbar-body").textContent = msg.body || "[media]";
        document.getElementById("ic-reply-bar").classList.add("visible");
        document.getElementById("ic-input").focus();
    };

    window._ic_cancel_reply = function() {
        S.reply_to = null;
        _hide_reply_bar();
    };

    window._ic_react = function(msg_name, emoji) {
        // Close all pickers
        document.querySelectorAll(".ic-react-picker.open").forEach(function(el){ el.classList.remove("open"); });
        frappe.call({
            method: "ecclesia.api.internal_chat.react_to_message",
            args: { message_name: msg_name, emoji: emoji },
            callback: function(r) {
                if (r.message) {
                    // Update message in state
                    var msg = S.messages.find(function(m){ return m.name === msg_name; });
                    if (msg) { msg.reactions = r.message.reactions; _re_render_reactions(msg_name, msg.reactions); }
                }
            }
        });
    };

    window._ic_open_react_picker = function(msg_name) {
        document.querySelectorAll(".ic-react-picker.open").forEach(function(el){ el.classList.remove("open"); });
        var picker = document.getElementById("ic-rp-" + msg_name);
        if (picker) picker.classList.toggle("open");
    };

    window._ic_open_new = function(type) {
        S.new_group_step    = 0;
        S.new_group_members = [];
        S._new_type         = type;

        document.getElementById("ic-new-title").textContent = type === "group" ? "New Group" : "New Message";
        document.getElementById("ic-selected-chips").innerHTML = "";
        document.getElementById("ic-user-search").value = "";
        document.getElementById("ic-new-confirm").textContent = type === "group" ? "Next" : "Start Chat";

        var gnWrap = document.getElementById("ic-new-group-name-wrap");
        if (gnWrap) gnWrap.style.display = "none";

        document.getElementById("ic-new-sheet").classList.add("open");
        _search_users("");
        setTimeout(function(){ document.getElementById("ic-user-search").focus(); }, 100);
    };

    window._ic_close_new = function() {
        document.getElementById("ic-new-sheet").classList.remove("open");
    };

    window._ic_toggle_user = function(email, name) {
        var idx = S.new_group_members.findIndex(function(m){ return m.email === email; });
        if (idx >= 0) {
            S.new_group_members.splice(idx, 1);
        } else {
            if (S._new_type === "dm" && S.new_group_members.length >= 1) return; // DM = 1 user
            S.new_group_members.push({ email: email, name: name });
        }
        _render_user_chips();
        _search_users(document.getElementById("ic-user-search").value);
    };

    window._ic_remove_member = function(email) {
        S.new_group_members = S.new_group_members.filter(function(m){ return m.email !== email; });
        _render_user_chips();
        _search_users(document.getElementById("ic-user-search").value);
    };

    window._ic_confirm_new = function() {
        if (!S.new_group_members.length) {
            frappe.show_alert({ message: "Select at least one person.", indicator: "orange" });
            return;
        }
        if (S._new_type === "group" && S.new_group_step === 0) {
            // Show group name field
            S.new_group_step = 1;
            var gnWrap = document.getElementById("ic-new-group-name-wrap");
            if (gnWrap) gnWrap.style.display = "block";
            document.getElementById("ic-new-confirm").textContent = "Create Group";
            document.getElementById("ic-group-name").focus();
            return;
        }
        _create_conversation();
    };

    window._ic_load_more = function() {
        if (S._loading_more || !S.active_conv) return;
        S._msg_page++;
        _load_messages(S.active_conv.name, true);
    };

    window._ic_toggle_info = function() {
        // TODO: slide-in members panel
        if (!S.active_conv) return;
        var members = (S.active_conv.members || []).map(function(m){ return m.full_name || m.user; }).join(", ");
        frappe.show_alert({ message: "Members: " + members, indicator: "blue" });
    };

    // =========================================================================
    // DATA — conversations
    // =========================================================================

    function _load_conversations() {
        frappe.call({
            method: "ecclesia.api.internal_chat.get_my_conversations",
            callback: function(r) {
                if (r && r.message) {
                    S.conversations = r.message;
                    _render_conv_list();
                    _compute_total_unread();
                }
            }
        });
    }

    function _render_conv_list() {
        var el = document.getElementById("ic-conv-list");
        if (!el) return;

        var list = S.conversations;
        if (S.search_query) {
            list = list.filter(function(c){
                return (c.chat_name || "").toLowerCase().includes(S.search_query);
            });
        }

        if (!list.length) {
            el.innerHTML = `<div class="ic-empty">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
                <p>${S.search_query ? "No results" : "No conversations yet."}</p></div>`;
            return;
        }

        el.innerHTML = list.map(function(c) {
            var initials = _initials(c.chat_name || "?");
            var time     = _format_time(c.last_message_at);
            var typeTag  = c.chat_type === "Direct Message" ? "dm"
                         : c.chat_type === "Document Channel" ? "doc" : "group";
            var typeName = c.chat_type === "Direct Message" ? "DM"
                         : c.chat_type === "Document Channel" ? "DOC" : "GRP";
            var isActive = S.active_conv && S.active_conv.name === c.name;
            var online   = c.chat_type === "Direct Message" && c._other_user && S.users_online[c._other_user];

            return `<div class="ic-conv-item${isActive ? " active" : ""}" onclick="window._ic_open_conv('${c.name}')">
                <div class="ic-avatar" style="width:38px;height:38px;font-size:13px;">
                    ${initials}
                    <span class="ic-dot${online ? " online" : ""}"></span>
                </div>
                <div class="ic-conv-body">
                    <div style="display:flex;align-items:center;gap:6px;">
                        <span class="ic-conv-name">${_esc(c.chat_name || "Unnamed")}</span>
                        <span class="ic-conv-type-tag ${typeTag}">${typeName}</span>
                    </div>
                    <div class="ic-conv-preview">${_esc(c.last_message_preview || "No messages yet")}</div>
                </div>
                <div class="ic-conv-meta">
                    <span class="ic-conv-time">${time}</span>
                    ${c.unread_count ? `<span class="ic-unread-badge">${c.unread_count > 99 ? "99+" : c.unread_count}</span>` : ""}
                </div>
            </div>`;
        }).join("");
    }

    // =========================================================================
    // DATA — messages
    // =========================================================================

    function _load_messages(conv_name, prepend) {
        if (S._loading_more) return;
        S._loading_more = true;

        frappe.call({
            method: "ecclesia.api.internal_chat.get_messages",
            args: { chat_name: conv_name, page: S._msg_page, page_size: 30 },
            callback: function(r) {
                S._loading_more = false;
                if (!r || !r.message) return;
                var msgs = r.message.messages || [];
                var has_more = r.message.has_more;

                document.getElementById("ic-load-earlier").style.display = has_more ? "block" : "none";

                if (prepend) {
                    S.messages = msgs.concat(S.messages);
                    _render_messages(true);
                } else {
                    S.messages = msgs;
                    _render_messages(false);
                    _scroll_to_bottom();
                }

                // Mark as read
                frappe.call({
                    method: "ecclesia.api.internal_chat.mark_as_read",
                    args: { chat_name: conv_name }
                });
            }
        });
    }

    function _render_messages(preserve_scroll) {
        var el = document.getElementById("ic-messages");
        if (!el || !S.active_conv) return;

        var scrollTop = el.scrollTop;
        var scrollH   = el.scrollHeight;

        if (!S.messages.length) {
            el.innerHTML = `<div id="ic-load-earlier" onclick="window._ic_load_more()" style="display:none;text-align:center;padding:6px;font-size:11px;color:var(--ic-muted);cursor:pointer;">↑ Load earlier messages</div>
            <div class="ic-empty" style="margin-top:40px;">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
                <p>No messages yet.<br/>Say hello! 👋</p>
            </div>`;
            return;
        }

        var html = `<div id="ic-load-earlier" onclick="window._ic_load_more()" style="${S._msg_page > 0 || S.messages.length >= 30 ? "" : "display:none;"}text-align:center;padding:6px;font-size:11px;color:var(--ic-muted);cursor:pointer;">↑ Load earlier messages</div>`;

        var last_date = null;
        var last_sender = null;

        S.messages.forEach(function(msg) {
            var date_str = _format_date(msg.timestamp || msg.creation);
            if (date_str !== last_date) {
                html += `<div class="ic-date-sep">${date_str}</div>`;
                last_date   = date_str;
                last_sender = null;
            }

            var is_out     = msg.sender === S.current_user;
            var show_name  = !is_out && S.active_conv.chat_type !== "Direct Message" && msg.sender !== last_sender;
            last_sender    = msg.sender;

            if (msg.message_type === "system") {
                html += `<div class="ic-sys-msg">${_esc(msg.body || "")}</div>`;
                return;
            }

            html += `<div class="ic-msg-group">`;
            if (show_name) {
                html += `<div class="ic-sender-name">${_esc(msg.sender_name || msg.sender)}</div>`;
            }

            html += `<div class="ic-msg-row${is_out ? " out" : ""}">`;
            if (!is_out) {
                html += `<div class="ic-avatar" style="width:26px;height:26px;font-size:10px;">${_initials(msg.sender_name || msg.sender)}</div>`;
            }
            html += `<div class="ic-bubble ${is_out ? "out" : "in"}" id="ic-bubble-${msg.name}">`;

            // Reaction picker
            html += `<div class="ic-react-picker" id="ic-rp-${msg.name}">
                ${EMOJI_LIST.slice(0,8).map(e => `<span onclick="window._ic_react('${msg.name}','${e}')">${e}</span>`).join("")}
            </div>`;

            // Hover actions
            html += `<div class="ic-msg-actions">
                <button onclick="window._ic_open_react_picker('${msg.name}')" title="React">😊</button>
                <button onclick="window._ic_reply_to('${msg.name}')" title="Reply">↩️</button>
                ${is_out ? `<button onclick="window._ic_delete_msg('${msg.name}')" title="Delete">🗑️</button>` : ""}
            </div>`;

            // Reply preview
            if (msg.reply_to) {
                var replyMsg = S.messages.find(function(m){ return m.name === msg.reply_to; });
                html += `<div class="ic-reply-preview">
                    <div class="ic-reply-from">${_esc(replyMsg ? (replyMsg.sender_name || replyMsg.sender) : "Unknown")}</div>
                    <div class="ic-reply-body">${_esc(replyMsg ? (replyMsg.body || "[media]") : "[deleted]")}</div>
                </div>`;
            }

            // Content
            html += _render_msg_content(msg);

            // Time + tick
            var tick = is_out ? (msg.read_by_all ? "✓✓" : "✓") : "";
            html += `<span class="ic-msg-time">${_format_msg_time(msg.timestamp || msg.creation)}</span>`;
            if (tick) html += `<span class="ic-msg-tick" style="color:${msg.read_by_all ? "var(--ic-accent)" : "rgba(255,255,255,0.5)"}">${tick}</span>`;

            html += `</div>`; // bubble

            // Reactions row
            var reactions = _parse_reactions(msg.reactions);
            if (Object.keys(reactions).length) {
                html += `<div class="ic-reactions" id="ic-reactions-${msg.name}">`;
                Object.keys(reactions).forEach(function(emoji) {
                    var users  = reactions[emoji];
                    var isMine = users.indexOf(S.current_user) >= 0;
                    html += `<span class="ic-reaction-chip${isMine ? " mine" : ""}" onclick="window._ic_react('${msg.name}','${emoji}')">
                        ${emoji} <span class="ic-r-count">${users.length}</span>
                    </span>`;
                });
                html += `</div>`;
            }

            html += `</div></div>`; // msg-row, msg-group
        });

        el.innerHTML = html;

        if (preserve_scroll) {
            el.scrollTop = scrollTop + (el.scrollHeight - scrollH);
        }
    }

    function _render_msg_content(msg) {
        var type = msg.message_type;
        if (type === "text") {
            return `<span>${_linkify(_esc(msg.body || ""))}</span>`;
        }
        if (type === "image") {
            return `<img class="ic-media-img" src="${_esc(msg.media_url || msg.file || "")}"
                onclick="window._ic_lightbox('${_esc(msg.media_url || msg.file || "")}')"
                alt="${_esc(msg.caption || "Image")}" />${msg.caption ? `<div style="font-size:11px;margin-top:4px;opacity:0.8;">${_esc(msg.caption)}</div>` : ""}`;
        }
        if (type === "audio") {
            return `<div class="ic-audio-wrap">
                <button onclick="window._ic_play_audio('${msg.name}','${_esc(msg.media_url || msg.file || "")}')">▶</button>
                <div class="ic-audio-progress" id="ic-ap-${msg.name}"><div class="ic-audio-fill" id="ic-af-${msg.name}"></div></div>
                <span class="ic-audio-dur" id="ic-ad-${msg.name}">0:00</span>
            </div>`;
        }
        if (type === "video") {
            return `<video style="max-width:200px;border-radius:10px;margin-top:4px;" controls src="${_esc(msg.media_url || msg.file || "")}"></video>`;
        }
        // document / other
        var icon = _file_icon(msg.media_filename || msg.file || "");
        return `<a class="ic-media-doc" href="${_esc(msg.media_url || msg.file || "")}" target="_blank" rel="noopener">
            <span class="ic-doc-icon">${icon}</span>
            <div>
                <div class="ic-doc-name">${_esc(msg.media_filename || "File")}</div>
                <div class="ic-doc-size">${msg.media_file_size ? _fmt_size(msg.media_file_size) : ""}</div>
            </div>
        </a>`;
    }

    // =========================================================================
    // OPEN CHAT VIEW
    // =========================================================================

    function _open_chat_view() {
        var conv = S.active_conv;
        if (!conv) return;

        // Determine display name (for DM, show the other person's name)
        var name = conv.chat_name || "Chat";

        document.getElementById("ic-list-view").style.display = "none";
        document.getElementById("ic-chat-view").classList.add("open");

        // Avatar
        var avatarEl = document.getElementById("ic-chat-avatar");
        avatarEl.textContent = _initials(name);

        // Header
        document.getElementById("ic-chat-name").textContent = name;

        var sub = "";
        if (conv.chat_type === "Direct Message") {
            var otherUser = conv._other_user;
            sub = S.users_online[otherUser] ? "● Online" : "Offline";
            document.getElementById("ic-chat-sub").style.color = S.users_online[otherUser] ? "var(--ic-green)" : "var(--ic-muted)";
        } else {
            sub = (conv.members || []).length + " members";
        }
        document.getElementById("ic-chat-sub").textContent = sub;

        document.getElementById("ic-input").focus();
    }

    // =========================================================================
    // SEND MESSAGE
    // =========================================================================

    function _send_message(type, body, media_data) {
        if (!S.active_conv) return;

        var args = {
            chat_name:    S.active_conv.name,
            message_type: type,
            body:         body,
            reply_to:     S.reply_to ? S.reply_to.name : null
        };
        if (media_data) {
            args.media_url      = media_data.url;
            args.media_filename = media_data.filename;
            args.media_file_size= media_data.size;
            args.mime_type      = media_data.mime_type;
        }

        // Optimistic local append
        var temp = {
            name:        "temp-" + Date.now(),
            sender:      S.current_user,
            sender_name: S.current_name,
            message_type: type,
            body:         body,
            timestamp:   new Date().toISOString(),
            reply_to:    S.reply_to ? S.reply_to.name : null,
            reactions:   null,
            _optimistic: true
        };
        S.messages.push(temp);
        _render_messages(false);
        _scroll_to_bottom();

        frappe.call({
            method: "ecclesia.api.internal_chat.send_message",
            args: args,
            callback: function(r) {
                if (r && r.message) {
                    // Replace temp
                    var idx = S.messages.findIndex(function(m){ return m.name === temp.name; });
                    if (idx >= 0) S.messages[idx] = r.message;
                    _render_messages(false);
                    _scroll_to_bottom();
                    // Update conv list preview
                    _update_conv_preview(S.active_conv.name, body || "[media]");
                }
            }
        });
    }

    function _send_file(file) {
        if (file.size > MAX_FILE_MB * 1024 * 1024) {
            frappe.show_alert({ message: "File too large. Max " + MAX_FILE_MB + "MB.", indicator: "red" });
            return;
        }
        frappe.show_alert({ message: "Uploading…", indicator: "blue" });

        var reader = new FileReader();
        reader.onload = function(e) {
            var mime = file.type;
            var type = mime.startsWith("image/") ? "image"
                     : mime.startsWith("video/") ? "video"
                     : mime.startsWith("audio/") ? "audio"
                     : "document";

            // Upload via Frappe upload
            frappe.call({
                method: "ecclesia.api.internal_chat.upload_chat_file",
                args: {
                    chat_name: S.active_conv.name,
                    filename:  file.name,
                    file_data: e.target.result.split(",")[1],
                    mime_type: mime
                },
                callback: function(r) {
                    if (r && r.message) {
                        _send_message(type, null, {
                            url:       r.message.file_url,
                            filename:  file.name,
                            size:      file.size,
                            mime_type: mime
                        });
                    }
                }
            });
        };
        reader.readAsDataURL(file);
    }

    // =========================================================================
    // CREATE CONVERSATION
    // =========================================================================

    function _create_conversation() {
        var is_group = S._new_type === "group";
        var members  = S.new_group_members.map(function(m){ return m.email; });
        var name     = is_group ? (document.getElementById("ic-group-name").value.trim() || "New Group") : null;

        if (!members.length) {
            frappe.show_alert({ message: "Select at least one person.", indicator: "orange" });
            return;
        }

        frappe.call({
            method: "ecclesia.api.internal_chat.get_or_create_conversation",
            args: {
                chat_type: is_group ? "Group" : "Direct Message",
                members:   members,
                chat_name: name
            },
            callback: function(r) {
                if (r && r.message) {
                    window._ic_close_new();
                    S.active_conv = r.message;
                    S.messages    = [];
                    S._msg_page   = 0;
                    _open_chat_view();
                    _load_messages(r.message.name);
                }
            }
        });
    }

    // =========================================================================
    // USER SEARCH (for new conversation)
    // =========================================================================

    function _search_users(query) {
        frappe.call({
            method: "ecclesia.api.internal_chat.search_users",
            args: { query: query, exclude: [S.current_user] },
            callback: function(r) {
                if (!r || !r.message) return;
                S._search_users_cache = r.message;
                _render_user_list(r.message);
            }
        });
    }

    function _render_user_list(users) {
        var el = document.getElementById("ic-user-list");
        if (!el) return;
        if (!users.length) {
            el.innerHTML = `<div style="text-align:center;padding:20px;font-size:12px;color:var(--ic-muted);">No users found</div>`;
            return;
        }
        el.innerHTML = users.map(function(u) {
            var selected = S.new_group_members.findIndex(function(m){ return m.email === u.email; }) >= 0;
            var online   = S.users_online[u.email];
            return `<div class="ic-user-row${selected ? " selected" : ""}" onclick="window._ic_toggle_user('${u.email}','${_esc(u.full_name || u.email)}')">
                <div class="ic-avatar" style="width:32px;height:32px;font-size:12px;position:relative;">
                    ${_initials(u.full_name || u.email)}
                    <span class="ic-dot${online ? " online" : ""}" style="width:8px;height:8px;bottom:-1px;right:-1px;"></span>
                </div>
                <div>
                    <div style="font-size:13px;font-weight:600;color:var(--ic-text);">${_esc(u.full_name || u.email)}</div>
                    <div style="font-size:11px;color:var(--ic-muted);">${_esc(u.email)}</div>
                </div>
                <div class="ic-check">${selected ? "✓" : ""}</div>
            </div>`;
        }).join("");
    }

    function _render_user_chips() {
        var el = document.getElementById("ic-selected-chips");
        if (!el) return;
        el.innerHTML = S.new_group_members.map(function(m) {
            return `<div class="ic-chip">
                <div class="ic-avatar" style="width:18px;height:18px;font-size:8px;">${_initials(m.name)}</div>
                ${_esc(m.name)}
                <button onclick="window._ic_remove_member('${m.email}')">✕</button>
            </div>`;
        }).join("");
    }

    // =========================================================================
    // TYPING INDICATOR
    // =========================================================================

    function _on_typing() {
        if (!S.active_conv) return;
        if (!_is_typing) {
            _is_typing = true;
            frappe.call({
                method: "ecclesia.api.internal_chat.broadcast_typing",
                args: { chat_name: S.active_conv.name, is_typing: true }
            });
        }
        clearTimeout(_typing_timer);
        _typing_timer = setTimeout(function() {
            _is_typing = false;
            frappe.call({
                method: "ecclesia.api.internal_chat.broadcast_typing",
                args: { chat_name: S.active_conv.name, is_typing: false }
            });
        }, 2000);
    }

    // =========================================================================
    // REALTIME
    // =========================================================================

    function _bind_realtime() {
        if (typeof frappe === "undefined" || !frappe.realtime) {
            setTimeout(_bind_realtime, 500);
            return;
        }

        // New message in any of my conversations
        frappe.realtime.on("ic_new_message", function(data) {
            // Update unread badge in list
            var conv = S.conversations.find(function(c){ return c.name === data.chat_name; });
            if (conv) {
                conv.last_message_preview = data.body || "[media]";
                conv.last_message_at      = data.timestamp;
                if (!S.active_conv || S.active_conv.name !== data.chat_name) {
                    conv.unread_count = (conv.unread_count || 0) + 1;
                }
                // Bubble up to top
                S.conversations = [conv].concat(S.conversations.filter(function(c){ return c.name !== conv.name; }));
                _render_conv_list();
            }

            // If active conv, push message
            if (S.active_conv && S.active_conv.name === data.chat_name && data.sender !== S.current_user) {
                S.messages.push(data);
                _render_messages(false);
                _scroll_to_bottom();
                frappe.call({ method: "ecclesia.api.internal_chat.mark_as_read", args: { chat_name: data.chat_name } });
            }

            _compute_total_unread();
        });

        // Typing
        frappe.realtime.on("ic_typing", function(data) {
            if (!S.active_conv || S.active_conv.name !== data.chat_name) return;
            if (data.user === S.current_user) return;
            var bar  = document.getElementById("ic-typing-bar");
            var text = document.getElementById("ic-typing-text");
            if (data.is_typing) {
                text.textContent = (data.user_name || data.user) + " is typing...";
                bar.classList.add("visible");
            } else {
                bar.classList.remove("visible");
            }
        });

        // Reaction update
        frappe.realtime.on("ic_message_reaction", function(data) {
            var msg = S.messages.find(function(m){ return m.name === data.message_name; });
            if (msg) {
                msg.reactions = data.reactions;
                _re_render_reactions(data.message_name, data.reactions);
            }
        });

        // Read receipts
        frappe.realtime.on("ic_message_read", function(data) {
            // Mark relevant messages as read_by_all
            if (S.active_conv && S.active_conv.name === data.chat_name) {
                S.messages.forEach(function(m) {
                    if (m.sender === S.current_user) m.read_by_all = true;
                });
                _render_messages(true);
            }
        });

        // Online status
        frappe.realtime.on("ic_user_online", function(data) {
            S.users_online[data.user] = data.online;
            _update_online_status();
            if (S.active_conv && S.active_conv.chat_type === "Direct Message" && S.active_conv._other_user === data.user) {
                document.getElementById("ic-chat-sub").textContent = data.online ? "● Online" : "Offline";
                document.getElementById("ic-chat-sub").style.color = data.online ? "var(--ic-green)" : "var(--ic-muted)";
            }
        });

        // Message deleted
        frappe.realtime.on("ic_message_deleted", function(data) {
            var idx = S.messages.findIndex(function(m){ return m.name === data.message_name; });
            if (idx >= 0) {
                S.messages[idx].is_deleted = true;
                S.messages[idx].body = "This message was deleted";
                S.messages[idx].message_type = "text";
                _render_messages(true);
            }
        });

        // Broadcast online presence
        _set_online(true);
        window.addEventListener("beforeunload", function() { _set_online(false); });
        setInterval(function() { _set_online(true); }, 30000);
    }

    function _set_online(online) {
        if (!frappe || !frappe.call) return;
        frappe.call({ method: "ecclesia.api.internal_chat.set_online_status", args: { online: online } });
    }

    // =========================================================================
    // HELPERS
    // =========================================================================

    function _hide_reply_bar() { document.getElementById("ic-reply-bar").classList.remove("visible"); }
    function _scroll_to_bottom() {
        var el = document.getElementById("ic-messages");
        if (el) setTimeout(function(){ el.scrollTop = el.scrollHeight; }, 30);
    }
    function _update_conv_preview(conv_name, text) {
        var conv = S.conversations.find(function(c){ return c.name === conv_name; });
        if (conv) { conv.last_message_preview = text; conv.last_message_at = new Date().toISOString(); _render_conv_list(); }
    }
    function _compute_total_unread() {
        S.total_unread = S.conversations.reduce(function(acc, c){ return acc + (c.unread_count || 0); }, 0);
        _update_badge_count();
    }
    function _update_badge_count() {
        var badge = document.getElementById("ic-badge");
        if (!badge) return;
        if (S.total_unread > 0) {
            badge.textContent = S.total_unread > 99 ? "99+" : S.total_unread;
            badge.style.display = "block";
        } else {
            badge.style.display = "none";
        }
    }
    function _update_online_status() {
        var count = Object.values(S.users_online).filter(Boolean).length;
        var el = document.getElementById("ic-online-count");
        if (el) el.textContent = count + " online";
    }
    function _re_render_reactions(msg_name, raw_reactions) {
        var el = document.getElementById("ic-reactions-" + msg_name);
        var reactions = _parse_reactions(raw_reactions);
        if (!el) {
            // Create new reactions div after bubble
            var bubble = document.getElementById("ic-bubble-" + msg_name);
            if (!bubble) return;
            var wrap = bubble.closest(".ic-msg-group");
            if (!wrap) return;
            var div = document.createElement("div");
            div.className = "ic-reactions";
            div.id = "ic-reactions-" + msg_name;
            wrap.appendChild(div);
            el = div;
        }
        if (!Object.keys(reactions).length) { el.innerHTML = ""; return; }
        el.innerHTML = Object.keys(reactions).map(function(emoji) {
            var users = reactions[emoji];
            var isMine = users.indexOf(S.current_user) >= 0;
            return `<span class="ic-reaction-chip${isMine ? " mine" : ""}" onclick="window._ic_react('${msg_name}','${emoji}')">${emoji} <span class="ic-r-count">${users.length}</span></span>`;
        }).join("");
    }
    function _parse_reactions(raw) {
        if (!raw) return {};
        try { return typeof raw === "string" ? JSON.parse(raw) : raw; } catch(e) { return {}; }
    }

    window._ic_delete_msg = function(msg_name) {
        frappe.confirm("Delete this message?", function() {
            frappe.call({
                method: "ecclesia.api.internal_chat.delete_message",
                args: { message_name: msg_name },
                callback: function() {
                    var idx = S.messages.findIndex(function(m){ return m.name === msg_name; });
                    if (idx >= 0) { S.messages[idx].body = "This message was deleted"; S.messages[idx].message_type = "text"; _render_messages(true); }
                }
            });
        });
    };

    window._ic_lightbox = function(src) {
        document.getElementById("ic-lightbox-img").src = src;
        document.getElementById("ic-lightbox").classList.add("open");
    };

    var _audio_players = {};
    window._ic_play_audio = function(msg_name, url) {
        var btn = document.querySelector("#ic-bubble-" + msg_name + " .ic-audio-wrap button");
        if (_audio_players[msg_name]) {
            var p = _audio_players[msg_name];
            if (!p.paused) { p.pause(); if (btn) btn.textContent = "▶"; }
            else { p.play(); if (btn) btn.textContent = "⏸"; }
            return;
        }
        var audio = new Audio(url);
        _audio_players[msg_name] = audio;
        audio.addEventListener("timeupdate", function() {
            var pct = audio.duration ? (audio.currentTime / audio.duration * 100) : 0;
            var fill = document.getElementById("ic-af-" + msg_name);
            var dur  = document.getElementById("ic-ad-" + msg_name);
            if (fill) fill.style.width = pct + "%";
            if (dur) dur.textContent = _fmt_dur(audio.currentTime);
        });
        audio.addEventListener("ended", function() { if (btn) btn.textContent = "▶"; });
        audio.play();
        if (btn) btn.textContent = "⏸";
    };

    // Utilities
    function _initials(name) {
        if (!name) return "?";
        var parts = name.trim().split(/\s+/);
        return (parts[0][0] + (parts[1] ? parts[1][0] : "")).toUpperCase();
    }
    function _esc(s) {
        if (s == null) return "";
        return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
    }
    function _linkify(text) {
        return text.replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" style="color:var(--ic-accent);text-decoration:underline;">$1</a>');
    }
    function _format_time(dt) {
        if (!dt) return "";
        var d = new Date(dt);
        var now = new Date();
        var diff = (now - d) / 1000;
        if (diff < 60) return "now";
        if (diff < 3600) return Math.floor(diff/60) + "m";
        if (diff < 86400) return d.getHours() + ":" + String(d.getMinutes()).padStart(2,"0");
        if (diff < 7 * 86400) return ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"][d.getDay()];
        return (d.getMonth()+1) + "/" + d.getDate();
    }
    function _format_msg_time(dt) {
        if (!dt) return "";
        var d = new Date(dt);
        return d.getHours() + ":" + String(d.getMinutes()).padStart(2,"0");
    }
    function _format_date(dt) {
        if (!dt) return "";
        var d = new Date(dt);
        var now = new Date();
        if (d.toDateString() === now.toDateString()) return "Today";
        var y = new Date(now); y.setDate(y.getDate()-1);
        if (d.toDateString() === y.toDateString()) return "Yesterday";
        return d.toLocaleDateString("en-US", { weekday:"long", month:"short", day:"numeric" });
    }
    function _fmt_size(bytes) {
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024*1024) return (bytes/1024).toFixed(1) + " KB";
        return (bytes/1024/1024).toFixed(1) + " MB";
    }
    function _fmt_dur(sec) {
        var m = Math.floor(sec/60), s = Math.floor(sec%60);
        return m + ":" + String(s).padStart(2,"0");
    }
    function _file_icon(filename) {
        var ext = (filename.split(".").pop() || "").toLowerCase();
        var map = { pdf:"📄", doc:"📝", docx:"📝", xls:"📊", xlsx:"📊", ppt:"📊", pptx:"📊",
                    zip:"📦", rar:"📦", mp3:"🎵", mp4:"🎬", mov:"🎬", png:"🖼️", jpg:"🖼️", jpeg:"🖼️" };
        return map[ext] || "📎";
    }

    // =========================================================================
    // KEYBOARD SHORTCUT
    // =========================================================================

    function _bind_global_keys() {
        document.addEventListener("keydown", function(e) {
            if (e.altKey && e.key.toLowerCase() === "c") {
                e.preventDefault();
                window._ic_toggle();
            }
        });
    }

    // =========================================================================
    // PUBLIC API
    // =========================================================================
    window.ecclesia_internal_chat = {
        open_conv: function(conv_name) {
            if (!document.getElementById(WIDGET_ID)) { _try_init(); setTimeout(function(){ window.ecclesia_internal_chat.open_conv(conv_name); }, 700); return; }
            var panel = document.getElementById(PANEL_ID);
            if (panel) panel.classList.add("open");
            window._ic_open_conv(conv_name);
        },
        open_dm: function(user_email) {
            window._ic_open_new("dm");
            // Pre-select user
            setTimeout(function(){
                window._ic_toggle_user(user_email, user_email);
                window._ic_confirm_new();
            }, 300);
        },
        get_unread_count: function() { return S.total_unread; }
    };

})();
