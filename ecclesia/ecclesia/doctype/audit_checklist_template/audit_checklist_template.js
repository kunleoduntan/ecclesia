// Copyright (c) 2026, kunle Oduntan and contributors
// For license information, please see license.txt

// ╔══════════════════════════════════════════════════════════════════════╗
// ║  AUDIT CHECKLIST TEMPLATE  ·  Ecclesia                               ║
// ╚══════════════════════════════════════════════════════════════════════╝

frappe.ui.form.on("Audit Checklist Template", {

	refresh(frm) {
		_header(frm);
		_breakdown(frm);
		_buttons(frm);
	},

	doctype_name(frm) {
		if (frm.doc.doctype_name && !frm.doc.template_name)
			frm.set_value("template_name", `Default — ${frm.doc.doctype_name}`);

		// Pull classification from registry
		frappe.db.get_value("Auditable DocType Registry",
			{ doctype_name: frm.doc.doctype_name }, "doctype_classification",
			v => {
				if (v?.doctype_classification && !frm.doc.classification)
					frm.set_value("classification", v.doctype_classification);
				frappe.show_alert({
					message:`✅ DocType linked — classification auto-populated`,
					indicator:"green"
				}, 3);
			});
	},
});


// ── Child Table: Audit Checklist Template Item ────────────────────────────────
frappe.ui.form.on("Audit Checklist Template Item", {

	control_area(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const COSO = {
			"Completeness":"Control Activities",    "Accuracy":"Control Activities",
			"GL Posting":"Control Activities",      "Authorization":"Control Environment",
			"Cutoff":"Control Activities",          "Valuation":"Control Activities",
			"Existence":"Control Activities",       "Segregation of Duties":"Control Environment",
			"Compliance":"Monitoring",              "Three-way Match":"Control Activities",
			"Duplicate Payments":"Control Activities","General Controls":"Control Environment",
			"Data Integrity":"Information & Communication","Other":"Control Activities",
		};
		const IIA = {
			"Completeness":"IIA 2320",   "Accuracy":"IIA 2320",      "GL Posting":"IIA 2310",
			"Authorization":"IIA 2330",  "Cutoff":"IIA 2320",        "Valuation":"IIA 2320",
			"Existence":"IIA 2310",      "Segregation of Duties":"IIA 2130",
			"Compliance":"IIA 2130.A1",  "Three-way Match":"IIA 2320",
			"Duplicate Payments":"IIA 2310","General Controls":"IIA 2130",
			"Data Integrity":"IIA 2130", "Other":"IIA 2300",
		};
		if (!row.coso_component && COSO[row.control_area])
			frappe.model.set_value(cdt, cdn, "coso_component", COSO[row.control_area]);
		if (!row.iia_standard && IIA[row.control_area])
			frappe.model.set_value(cdt, cdn, "iia_standard", IIA[row.control_area]);
	},
});


// ── Header ────────────────────────────────────────────────────────────────────
function _header(frm) {
	const cls_color = {
		Financial:"#3498db", "HR & Payroll":"#9b59b6", "Inventory & Stock":"#27ae60",
		Procurement:"#e67e22", Sales:"#1abc9c", "Approval & Workflow":"#f39c12", Custom:"#95a5a6",
	}[frm.doc.classification] || "#2c3e50";

	frm.dashboard.add_comment(`
		<div style="background:#f8f9fa;border-left:5px solid ${cls_color};
		            border-radius:0 8px 8px 0;padding:12px 16px;
		            display:flex;align-items:center;gap:14px;flex-wrap:wrap;">
			<span style="font-size:26px;">📋</span>
			<div style="flex:1;">
				<div style="font-weight:700;font-size:14px;color:#2c3e50;">
					${frm.doc.template_name || "Checklist Template"}
				</div>
				<div style="font-size:12px;color:#888;margin-top:3px;">
					${frm.doc.doctype_name ? `📦 ${frm.doc.doctype_name}` : "<em>No DocType linked</em>"}
					${frm.doc.classification
						? ` &nbsp;·&nbsp; <span style="color:${cls_color};font-weight:600;">${frm.doc.classification}</span>`
						: ""}
				</div>
			</div>
			${frm.doc.is_default
				? `<span style="background:#f0fdf4;border:1px solid #27ae60;color:#1e8449;
				               padding:4px 14px;border-radius:12px;font-size:12px;font-weight:600;">
					⭐ Default Template
				</span>` : ""}
		</div>`, "white", true);
}


// ── Item Breakdown ────────────────────────────────────────────────────────────
function _breakdown(frm) {
	const items = frm.doc.checklist_items || [];
	if (!items.length) {
		frm.dashboard.add_comment(`
			<div style="text-align:center;padding:16px;color:#aaa;font-size:13px;">
				📭 No checklist items yet — add test procedures below.
			</div>`, "white", true);
		return;
	}

	// Risk counts
	const risk_cfg = {
		Critical:{ c:"#e74c3c", bg:"#fdf2f2" }, High:{ c:"#e67e22", bg:"#fdf6ec" },
		Medium:  { c:"#f39c12", bg:"#fefce8" }, Low: { c:"#27ae60", bg:"#f0fdf4" },
	};
	const by_risk = {};
	items.forEach(i => { by_risk[i.risk_level] = (by_risk[i.risk_level]||0) + 1; });

	const risk_badges = Object.entries(by_risk).map(([r, n]) => {
		const c = risk_cfg[r] || { c:"#aaa", bg:"#f8f9fa" };
		return `<span style="background:${c.bg};border:1px solid ${c.c};color:${c.c};
		               padding:4px 12px;border-radius:12px;font-size:12px;font-weight:600;">
			${r}: ${n}
		</span>`;
	}).join("");

	// COSO coverage
	const by_coso = {};
	items.forEach(i => { if (i.coso_component) by_coso[i.coso_component] = (by_coso[i.coso_component]||0)+1; });
	const coso_pills = Object.entries(by_coso).map(([c, n]) =>
		`<span style="background:#f0f4ff;border:1px solid #3498db40;color:#2980b9;
		             padding:2px 9px;border-radius:8px;font-size:11px;">${c} (${n})</span>`
	).join("");

	// Control areas
	const by_area = {};
	items.forEach(i => { if (i.control_area) by_area[i.control_area] = (by_area[i.control_area]||0)+1; });
	const area_pills = Object.entries(by_area).sort((a,b)=>b[1]-a[1]).slice(0,6).map(([a, n]) =>
		`<span style="background:#f8f9fa;border:1px solid #dee2e6;color:#666;
		             padding:2px 9px;border-radius:8px;font-size:11px;">${a} (${n})</span>`
	).join("");

	frm.dashboard.add_comment(`
		<div style="background:#f8f9fa;border-radius:8px;padding:12px 14px;">
			<div style="font-size:10px;color:#aaa;font-weight:700;text-transform:uppercase;
			            letter-spacing:.5px;margin-bottom:8px;">
				📊 ${items.length} items across ${Object.keys(by_area).length} control areas
			</div>
			<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px;">${risk_badges}</div>
			${coso_pills ? `<div style="font-size:10px;color:#aaa;margin-bottom:5px;font-weight:600;">COSO Coverage</div>
				<div style="display:flex;gap:5px;flex-wrap:wrap;margin-bottom:8px;">${coso_pills}</div>` : ""}
			${area_pills ? `<div style="font-size:10px;color:#aaa;margin-bottom:5px;font-weight:600;">Control Areas</div>
				<div style="display:flex;gap:5px;flex-wrap:wrap;">${area_pills}</div>` : ""}
		</div>`, "white", true);
}


// ── Buttons ───────────────────────────────────────────────────────────────────
function _buttons(frm) {
	if (frm.is_new()) return;

	if (!frm.doc.is_default)
		frm.add_custom_button("⭐ Set as Default", () => {
			frappe.db.set_value("Audit Checklist Template", frm.doc.name, "is_default", 1)
			         .then(() => { frm.reload_doc();
			             frappe.show_alert({ message:"Set as default template ⭐", indicator:"green" }, 3);
			         });
		}, "Actions");

	frm.add_custom_button("📄 Duplicate", () => {
		frappe.prompt([
			{ fieldtype:"Data", label:"New Template Name", fieldname:"name", reqd:1 },
		], vals => {
			frappe.call({
				method:"frappe.client.copy_doc",
				args:{ dt:"Audit Checklist Template", dn:frm.doc.name },
				callback(r) {
					if (!r.message) return;
					frappe.db.set_value("Audit Checklist Template", r.message.name, {
						template_name: vals.name, is_default: 0,
					}).then(() => {
						frappe.set_route("Form","Audit Checklist Template", r.message.name);
						frappe.show_alert({ message:`Duplicated as "${vals.name}" 📄`, indicator:"blue" }, 3);
					});
				}
			});
		}, "Duplicate Template", "Duplicate");
	}, "Actions");

	frm.add_custom_button("🔎 Preview Usage", () => {
		frappe.set_route("List","Audit Checklist",{ doctype_name: frm.doc.doctype_name });
	}, "View");
}