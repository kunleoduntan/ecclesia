/* VIC THEME — switcher, page-menu integration, List View extras. */

frappe.provide("vic_theme");

/* `ink` (optional) = a darker shade used for the check mark so very bright
   colours (e.g. Electric #00F0FF) stay visible on a white card. */
vic_theme.THEMES = [
	{ key: "violet",    label: "Violet (Default)", color: "#6c5ce7", icon: "🔮" },
	{ key: "farepoint", label: "FarePoint",        color: "#e91e8c", icon: "✈️" },
	{ key: "emerald",   label: "Emerald",          color: "#0f766e", icon: "💎" },
	{ key: "sunset",    label: "Sunset",           color: "#d97706", icon: "🌅" },
	{ key: "ocean",     label: "Ocean",            color: "#2563eb", icon: "🌊" },
	{ key: "nova",      label: "Nova",             color: "#7c3aed", icon: "🌟" },
	{ key: "ember",     label: "Ember",            color: "#f97316", icon: "🔥" },
	{ key: "midnight",  label: "Midnight",         color: "#818cf8", icon: "🌙" },
	{ key: "verdant",   label: "Verdant",          color: "#059669", icon: "🌿" },
	{ key: "arctic",    label: "Arctic",           color: "#0284c7", icon: "❄️" },
	{ key: "forest",    label: "Forest",           color: "#22c55e", icon: "🌲" },
	{ key: "candy",     label: "Candy",            color: "#db2777", icon: "🍬" },
	{ key: "cyan",      label: "Cyan",             color: "#0891b2", icon: "🧊" },
	{ key: "mint",      label: "Mint Blue",        color: "#0fa3a0", icon: "🍃" },
	{ key: "electric",  label: "Electric Blue",    color: "#00F0FF", ink: "#007c89", icon: "⚡" },
];

vic_theme.STORAGE_KEY = "vic_theme_preset";

vic_theme._esc = function (s) {
	return String(s == null ? "" : s)
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#39;");
};

vic_theme.apply = function (key) {
	if (!vic_theme.THEMES.find((t) => t.key === key)) key = "violet";
	document.documentElement.setAttribute("data-vic-theme", key);
	try { localStorage.setItem(vic_theme.STORAGE_KEY, key); } catch (e) {}
};

vic_theme.get_current = function () {
	try { return localStorage.getItem(vic_theme.STORAGE_KEY) || "violet"; }
	catch (e) { return "violet"; }
};

/* -------------------------------------------------------------------------
   Theme picker dialog — card grid with icon, name, swatch, checkmark.
   ------------------------------------------------------------------------- */
vic_theme.open_picker = function () {
	const current = vic_theme.get_current();

	const cards_html = vic_theme.THEMES.map((t) => {
		const is_active = t.key === current;
		const check_color = t.ink || t.color;
		return `
			<div class="vic-picker-card ${is_active ? "active" : ""}" data-key="${t.key}"
				style="border-color:${is_active ? t.color : "var(--vic-border)"};">
				<div class="vic-picker-icon" style="background:${t.color}22;">${t.icon}</div>
				<div class="vic-picker-info">
					<div class="vic-picker-name">${vic_theme._esc(t.label)}</div>
					<div class="vic-picker-swatch" style="background:${t.color};"></div>
				</div>
				<span class="vic-picker-check" style="color:${check_color};">
					${is_active ? "&#10003;" : ""}
				</span>
			</div>
		`;
	}).join("");

	const dialog = new frappe.ui.Dialog({
		title: __("🎨 VIC Theme"),
		size: "large",
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "vic_theme_grid",
				options: `
					<p style="font-size:12px;color:var(--vic-text-muted);margin:0 0 14px;">
						${__("Applies instantly across forms and list views. Stored in your browser only.")}
					</p>
					<div class="vic-picker-grid">${cards_html}</div>
				`,
			},
		],
	});

	dialog.show();

	/* Bind on the dialog's wrapper AFTER show() so the DOM exists. */
	dialog.$wrapper.on("click", ".vic-picker-card", function () {
		const key = $(this).data("key");
		vic_theme.apply(key);
		dialog.hide();
		frappe.show_alert({ message: __("Theme changed"), indicator: "green" });
	});

	return dialog;
};

/* -------------------------------------------------------------------------
   Navbar dot
   ------------------------------------------------------------------------- */
vic_theme.init_switcher = function () {
	if (document.querySelector(".vic-theme-switcher")) return;

	const wrap = document.createElement("div");
	wrap.className = "vic-theme-switcher";
	wrap.title = "Change theme";

	const dot = document.createElement("div");
	dot.className = "vic-theme-dot";
	wrap.appendChild(dot);

	dot.addEventListener("click", function (e) {
		e.stopPropagation();
		vic_theme.open_picker();
	});

	const target =
		document.querySelector(".navbar .navbar-right") ||
		document.querySelector(".navbar .dropdown-help") ||
		document.querySelector(".navbar .nav-item.dropdown") ||
		document.querySelector(".navbar-nav") ||
		document.querySelector(".navbar");

	if (target) {
		target.insertBefore(wrap, target.firstChild);
	} else {
		wrap.style.position = "fixed";
		wrap.style.top = "8px";
		wrap.style.right = "16px";
		wrap.style.zIndex = "1050";
		document.body.appendChild(wrap);
	}

	vic_theme.apply(vic_theme.get_current());
};

/* -------------------------------------------------------------------------
   "•••" page-menu integration
   ------------------------------------------------------------------------- */
vic_theme.inject_menu_items = function () {
	const targets = [];
	if (window.cur_frm && cur_frm.page) targets.push({ page: cur_frm.page, is_list: false });
	if (window.cur_list && cur_list.page) targets.push({ page: cur_list.page, is_list: true });

	targets.forEach(({ page, is_list }) => {
		if (page.__vic_theme_menu_added) return;
		try {
			page.add_menu_item(__("🎨 VIC Theme"), () => vic_theme.open_picker(), true);
			if (is_list) {
				page.add_menu_item(__("📊 Export to Excel"),
					() => vic_theme.export_current_listview(), true);
			}
			page.__vic_theme_menu_added = true;
		} catch (e) { /* not available on this page type — navbar dot is fallback */ }
	});
};

if (frappe.router && frappe.router.on) {
	frappe.router.on("change", () => {
		setTimeout(vic_theme.inject_menu_items, 400);
		setTimeout(vic_theme.inject_menu_items, 1200);
	});
}
$(document).on("page-change", () => setTimeout(vic_theme.inject_menu_items, 400));

/* -------------------------------------------------------------------------
   Export current list view to Excel
   ------------------------------------------------------------------------- */
vic_theme.export_current_listview = function () {
	const listview = window.cur_list;
	if (!listview) {
		frappe.show_alert({ message: __("Open a list view first"), indicator: "orange" });
		return;
	}

	const doctype = listview.doctype;
	let fields = [];
	try { fields = (listview.columns || []).map((c) => c.df && c.df.fieldname).filter(Boolean); }
	catch (e) { fields = []; }

	let filters = [];
	try { filters = listview.filter_area ? listview.filter_area.get() : []; }
	catch (e) { filters = []; }

	const accent =
		getComputedStyle(document.documentElement).getPropertyValue("--vic-accent").trim() || "#6c5ce7";

	const url =
		"/api/method/vic_theme.api.export_listview_excel" +
		"?doctype=" + encodeURIComponent(doctype) +
		"&filters=" + encodeURIComponent(JSON.stringify(filters)) +
		"&fields=" + encodeURIComponent(JSON.stringify(fields)) +
		"&accent_color=" + encodeURIComponent(accent);

	window.open(url, "_blank");
};

/* -------------------------------------------------------------------------
   Opt-in summary cards
   ------------------------------------------------------------------------- */
vic_theme.render_summary_cards = function (listview, cards) {
	const $page_content = listview.page.wrapper.find(".page-content");
	if (!$page_content.length) return;
	$page_content.find(".vic-summary-row").remove();

	const cards_html = cards.map((c) => `
		<div class="vic-summary-card ${c.variant || ""}" data-key="${c.key || ""}">
			<div class="vic-summary-card-label">${vic_theme._esc(c.label)}</div>
			<div class="vic-summary-card-value">${vic_theme._esc(String(c.value))}</div>
		</div>
	`).join("");

	$page_content.prepend(`<div class="vic-summary-row">${cards_html}</div>`);
};

/* -------------------------------------------------------------------------
   Boot
   ------------------------------------------------------------------------- */
$(document).on("app_ready", function () {
	vic_theme.init_switcher();
});
$(function () {
	setTimeout(() => {
		if (!document.querySelector(".vic-theme-switcher")) vic_theme.init_switcher();
		vic_theme.inject_menu_items();
	}, 1500);
});