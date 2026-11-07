// Copyright (c) 2026, Value Impacts Consulting
// For license information, please see license.txt
//
// ecclesia/public/js/erequest_pending.js
// "My Pending Approvals" – navbar badge + popup with one-click Approve / Reject.
// Loaded on every desk page via app_include_js. Shows nothing for users who are
// not approvers.
//
// Built for Frappe v15/v16. Design rules so it can never disturb the desk:
//   • nothing here can throw inside the "startup" event (a throw there stops
//     every later startup handler and breaks the desk)
//   • realtime is bound only if the socket exists (it is absent when
//     socketio is not running) and never crashes when it does not
//   • background polling is silent: no spinner, no overlapping calls,
//     paused while the tab is hidden

(() => {
	"use strict";

	if (window.__erequest_pending_loaded) return; // guard against double include
	window.__erequest_pending_loaded = true;

	const DOCTYPE = "eRequest";
	// Dotted path of erequest_pending.py (same folder as erequest.py).
	// If your app package is named differently, change ONLY this line.
	const API = "ecclesia.ecclesia.doctype.erequest.erequest_pending";
	const EVENT = "erequest_pending_refresh";

	const BTN_ID = "erequest-pending-btn";
	const BADGE_ID = "erq-badge";
	const POLL_MS = 3 * 60 * 1000;
	const BRAND = "#154734";
	// Open the popup by itself once per browser session when something is pending
	const AUTO_OPEN = false;

	const S = {
		items: [],
		last_count: null,
		last_fetch: 0,
		dialog: null,
		timer: null,
		debounce: null,
		booted: false,
		loading: false,
		is_approver: null,
		nav_tries: 0,
		rt_tries: 0,
	};

	// ------------------------------------------------------------------ //
	// Utilities
	// ------------------------------------------------------------------ //
	const log = (msg, e) => console.error("[eRequest Approvals] " + msg, e || "");

	const safe = (fn) =>
		function () {
			try {
				return fn.apply(this, arguments);
			} catch (e) {
				log("error", e);
			}
		};

	const esc = (v) => frappe.utils.escape_html(v == null ? "" : String(v));

	const call = (method, args, opts) =>
		frappe.call({ method: `${API}.${method}`, args: args || {}, ...(opts || {}) });

	const seen_this_session = () => {
		try {
			if (sessionStorage.getItem("erq_auto_opened")) return true;
			sessionStorage.setItem("erq_auto_opened", "1");
		} catch (e) {
			/* storage blocked: fall through */
		}
		return false;
	};

	// ------------------------------------------------------------------ //
	// Navbar button + badge
	// ------------------------------------------------------------------ //
	function ensure_button() {
		if (S.is_approver !== true || $("#" + BTN_ID).length) return;

		const $li = $(`
			<li class="nav-item" id="${BTN_ID}">
				<a class="nav-link" href="#" title="${__("eRequests awaiting my approval")}"
				   style="position:relative;display:flex;align-items:center;">
					<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
					     stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
						<path d="M9 11l3 3L22 4"></path>
						<path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
					</svg>
					<span id="${BADGE_ID}" style="display:none;position:absolute;top:2px;right:-2px;
						background:#D93025;color:#fff;border-radius:10px;font-size:10px;
						font-weight:700;line-height:1;padding:3px 5px;min-width:16px;text-align:center;">0</span>
				</a>
			</li>`);

		$li.find("a").on("click", (e) => {
			e.preventDefault();
			open_dialog();
		});

		const $anchor = $(".navbar .dropdown-notifications").first();
		const $nav = $(".navbar .navbar-nav").last();

		if ($anchor.length) {
			$anchor.before($li);
		} else if ($nav.length) {
			$nav.prepend($li);
		} else if (S.nav_tries < 10) {
			// navbar not rendered yet: try again shortly
			S.nav_tries += 1;
			setTimeout(safe(ensure_button), 1000);
			return;
		} else {
			// navbar not found: float the button so it is never invisible
			$("body").append(
				$(
					'<ul class="list-unstyled" style="position:fixed;top:10px;right:190px;z-index:1050;margin:0;"></ul>'
				).append($li)
			);
		}
		update_badge(S.items.length);
	}

	function update_badge(n) {
		const $b = $("#" + BADGE_ID);
		if (!$b.length) return;
		$b.text(n > 99 ? "99+" : n).toggle(n > 0);
	}

	// ------------------------------------------------------------------ //
	// Data
	// ------------------------------------------------------------------ //
	function refresh(opts) {
		opts = opts || {};
		if (S.loading) return Promise.resolve(); // never overlap calls
		S.loading = true;

		return call("get_pending", {}, { silent: true, no_spinner: true })
			.then((r) => {
				S.loading = false;
				S.last_fetch = Date.now();

				const d = (r && r.message) || {};
				S.is_approver = !!d.is_approver;

				if (!S.is_approver) {
					stop();
					$("#" + BTN_ID).remove();
					return;
				}

				ensure_button();
				S.items = d.items || [];
				const n = S.items.length;
				update_badge(n);

				const dialog_open = S.dialog && S.dialog.$wrapper.is(":visible");
				if (dialog_open) render_list();

				let auto_opened = false;
				if (opts.first && AUTO_OPEN && n > 0 && !dialog_open && !seen_this_session()) {
					auto_opened = true;
					open_dialog();
				}

				if (!opts.silent && !dialog_open && !auto_opened) {
					if (S.last_count === null && n > 0) {
						toast(
							n === 1
								? __("You have 1 eRequest awaiting your approval")
								: __("You have {0} eRequests awaiting your approval", [n])
						);
					} else if (S.last_count !== null && n > S.last_count) {
						toast(__("New eRequest awaiting your approval"));
					}
				}
				S.last_count = n;
			})
			.catch((e) => {
				// silent:true hides server errors, so log them here
				S.loading = false;
				log("get_pending failed (check the API path at the top of the file)", e);
			});
	}

	function toast(message) {
		frappe.show_alert({ message, indicator: "orange" }, 12, {
			[__("Review")]: open_dialog,
		});
	}

	function start() {
		if (S.timer) return;
		S.timer = setInterval(
			safe(() => {
				if (!document.hidden) refresh();
			}),
			POLL_MS
		);
	}

	function stop() {
		clearInterval(S.timer);
		S.timer = null;
	}

	// ------------------------------------------------------------------ //
	// Dialog
	// ------------------------------------------------------------------ //
	function open_dialog() {
		if (!S.dialog) build_dialog();
		S.dialog.show();
		render_list();
		refresh({ silent: true });
	}

	function build_dialog() {
		S.dialog = new frappe.ui.Dialog({
			title: __("My Pending Approvals"),
			size: "large",
			fields: [{ fieldtype: "HTML", fieldname: "list" }],
			primary_action_label: __("Approve Selected"),
			primary_action: approve_selected,
		});

		const $w = S.dialog.fields_dict.list.$wrapper;

		$w.on("click", "[data-act]", function (e) {
			const act = $(this).data("act");
			const $card = $(this).closest(".erq-card");
			const name = $card.data("name");

			if (act === "open") {
				e.preventDefault();
				S.dialog.hide();
				frappe.set_route("Form", DOCTYPE, name);
			} else if (act === "approve") {
				const it = S.items.find((x) => x.name === name);
				const verb = it && it.approve_label ? it.approve_label : __("Approve");
				frappe.confirm(
					it && it.amount
						? __("{0} {1} for {2}?", [verb, name, it.amount])
						: __("{0} {1}?", [verb, name]),
					() => run("approve", { name }, $card)
				);
			} else if (act === "reject") {
				frappe.prompt(
					[
						{
							fieldname: "reason",
							fieldtype: "Small Text",
							label: __("Reason for Rejection"),
							reqd: 1,
						},
					],
					(v) => run("reject", { name, reason: v.reason }, $card),
					__("Reject {0}", [name]),
					__("Confirm Rejection")
				);
			} else if (act === "refresh") {
				refresh({ silent: true });
			}
		});

		$w.on("change", ".erq-sel", update_primary);
	}

	function update_primary() {
		const n = S.dialog.fields_dict.list.$wrapper.find(".erq-sel:checked").length;
		S.dialog.get_primary_btn().text(
			n ? __("Approve Selected ({0})", [n]) : __("Approve Selected")
		);
	}

	function card(it) {
		const muted = "color:var(--text-muted);font-size:12px;";
		const btn = (act, label, bg, show) =>
			show
				? `<button class="btn btn-xs" data-act="${act}"
					style="background:${bg};color:#fff;border:none;padding:5px 14px;border-radius:6px;font-weight:600;">${esc(label)}</button>`
				: "";

		const sub = [it.request_type, it.category, it.beneficiary, it.priority]
			.filter(Boolean)
			.map(esc)
			.join(" · ");

		return `
		<div class="erq-card" data-name="${esc(it.name)}"
		     style="border:1px solid var(--border-color);border-left:4px solid ${BRAND};
		            border-radius:8px;padding:12px 14px;margin-bottom:10px;background:var(--card-bg);">
			<div style="display:flex;gap:10px;align-items:flex-start;">
				<input type="checkbox" class="erq-sel" ${it.can_approve ? "" : "disabled"} style="margin-top:5px;">
				<div style="flex:1;min-width:0;">
					<div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;">
						<a href="#" data-act="open" style="font-weight:600;">${esc(it.name)}${it.title ? " – " + esc(it.title) : ""}</a>
						<span style="font-weight:700;">${esc(it.amount)}</span>
					</div>
					<div style="${muted}margin-top:2px;">${sub}</div>
					${it.purpose ? `<div style="margin-top:6px;font-size:13px;">${esc(it.purpose)}</div>` : ""}
					<div style="${muted}margin-top:6px;">
						${__("By")} ${esc(it.requester)} · ${esc(it.waiting)} ·
						<span style="color:#B45309;font-weight:600;">${esc(it.workflow_state)}</span>
					</div>
				</div>
			</div>
			<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:10px;">
				<button class="btn btn-xs btn-default" data-act="open">${__("Open")}</button>
				${btn("reject", it.reject_label || __("Reject"), "#D93025", it.can_reject)}
				${btn("approve", it.approve_label || __("Approve"), "#1E8E3E", it.can_approve)}
			</div>
		</div>`;
	}

	function render_list() {
		if (!S.dialog) return;
		const $w = S.dialog.fields_dict.list.$wrapper;
		const header = `
			<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
				<span style="color:var(--text-muted);font-size:12px;">
					${__("{0} awaiting your approval", [S.items.length])}
				</span>
				<button class="btn btn-xs btn-default" data-act="refresh">${__("Refresh")}</button>
			</div>`;

		const body = S.items.length
			? S.items.map(card).join("")
			: `<div style="text-align:center;padding:40px 0;color:var(--text-muted);">
					<div style="font-size:28px;">✓</div>${__("You're all caught up")}
			   </div>`;

		$w.html(header + `<div style="max-height:60vh;overflow-y:auto;padding-right:4px;">${body}</div>`);
		S.dialog.get_primary_btn().toggle(S.items.some((x) => x.can_approve));
		update_primary();
	}

	// ------------------------------------------------------------------ //
	// Actions
	// ------------------------------------------------------------------ //
	function reload_open_form(name) {
		try {
			if (window.cur_frm && cur_frm.doctype === DOCTYPE && cur_frm.docname === name) {
				cur_frm.reload_doc();
			}
		} catch (e) {
			/* ignore */
		}
	}

	function run(method, args, $card) {
		$card.css("opacity", 0.5).find("button").prop("disabled", true);
		return call(method, args)
			.then(() => {
				frappe.show_alert({
					message:
						method === "approve"
							? __("{0} approved", [args.name])
							: __("{0} rejected", [args.name]),
					indicator: method === "approve" ? "green" : "red",
				});
				reload_open_form(args.name);
				return refresh({ silent: true });
			})
			.catch(() => {
				$card.css("opacity", 1).find("button").prop("disabled", false);
				refresh({ silent: true });
			});
	}

	function approve_selected() {
		const names = S.dialog.fields_dict.list.$wrapper
			.find(".erq-sel:checked")
			.map(function () {
				return $(this).closest(".erq-card").data("name");
			})
			.get();

		if (!names.length) {
			frappe.show_alert({ message: __("Tick the requests you want to approve"), indicator: "orange" });
			return;
		}

		frappe.confirm(__("Approve {0} selected request(s)?", [names.length]), () => {
			call("approve_many", { names: JSON.stringify(names) }, { freeze: true, freeze_message: __("Approving...") })
				.then((r) => {
					const res = (r && r.message) || { done: [], failed: [] };
					if (res.done && res.done.length) {
						frappe.show_alert({
							message: __("{0} request(s) approved", [res.done.length]),
							indicator: "green",
						});
						res.done.forEach(reload_open_form);
					}
					if (res.failed && res.failed.length) {
						frappe.msgprint({
							title: __("Some requests could not be approved"),
							indicator: "red",
							message: res.failed
								.map((f) => `<b>${esc(f.name)}</b>: ${esc(f.error)}`)
								.join("<br>"),
						});
					}
					return refresh({ silent: true });
				});
		});
	}

	// ------------------------------------------------------------------ //
	// Realtime (optional: only if the socket exists)
	// ------------------------------------------------------------------ //
	function on_nudge() {
		clearTimeout(S.debounce);
		S.debounce = setTimeout(safe(() => refresh()), 1500);
	}

	function bind_realtime() {
		const rt = window.frappe && frappe.realtime;
		if (rt && rt.socket && typeof rt.on === "function") {
			rt.on(EVENT, on_nudge);
			return;
		}
		// socket not ready (or socketio not running): retry a few times, then
		// rely on polling alone
		if (S.rt_tries < 5) {
			S.rt_tries += 1;
			setTimeout(safe(bind_realtime), 4000);
		}
	}

	// ------------------------------------------------------------------ //
	// Boot
	// ------------------------------------------------------------------ //
	function boot() {
		if (S.booted) return;
		if (!window.frappe || !frappe.session || !frappe.session.user || frappe.session.user === "Guest") return;
		S.booted = true;

		refresh({ first: true }).then(() => {
			if (S.is_approver) start();
		});

		bind_realtime();

		// the navbar can be re-rendered on route changes: put the icon back if it vanished
		try {
			if (frappe.router && typeof frappe.router.on === "function") {
				frappe.router.on("change", safe(ensure_button));
			}
		} catch (e) {
			/* ignore */
		}

		// refresh when the user comes back to the tab after a while
		document.addEventListener(
			"visibilitychange",
			safe(() => {
				if (!document.hidden && S.is_approver && Date.now() - S.last_fetch > POLL_MS) {
					refresh();
				}
			})
		);
	}

	// safe(): an error here must never stop other apps' startup handlers
	$(document).on("startup", safe(boot));
	// fallback: this file may load after the "startup" event has already fired
	$(safe(() => setTimeout(safe(boot), 1500)));

	// console helpers: erequest_pending.open(), erequest_pending.refresh(), erequest_pending.state
	window.erequest_pending = { open: safe(open_dialog), refresh: () => refresh(), state: S };
})();