// Copyright (c) 2026, kunle Oduntan and contributors
// For license information, please see license.txt



frappe.ui.form.on("Annual Audit Plan", {

	refresh(frm) {
		_header(frm);
		_materiality_panel(frm);
		_progress_panel(frm);
		_buttons(frm);
	},

	// Live materiality recalculation
	total_revenue(frm)     { _calc_materiality(frm); _materiality_panel(frm); },
	total_assets(frm)      { _calc_materiality(frm); _materiality_panel(frm); },
	profit_before_tax(frm) { _calc_materiality(frm); _materiality_panel(frm); },

	plan_year(frm) {
		if (frm.doc.plan_year && !frm.doc.plan_title)
			frm.set_value("plan_title", `Annual Audit Plan ${frm.doc.plan_year}`);
	},

	status(frm) { _header(frm); },
});

// ── Child table: status change updates parent progress panel ──────────────────
frappe.ui.form.on("Annual Plan Engagement Row", {
	status(frm) {
		setTimeout(() => _progress_panel(frm), 100);
	},
});


// ── Header banner ─────────────────────────────────────────────────────────────
function _header(frm) {
	const st = frm.doc.status || "Draft";
	const st_cfg = {
		Draft:       { bg:"#f8f9fa", bd:"#bdc3c7", tc:"#7f8c8d", ic:"📋" },
		Approved:    { bg:"#f0fdf4", bd:"#27ae60", tc:"#1e8449", ic:"✅" },
		"In Progress":{ bg:"#f0f4ff", bd:"#3498db", tc:"#2980b9", ic:"⚙️"  },
		Completed:   { bg:"#f0fdf4", bd:"#1abc9c", tc:"#16a085", ic:"🏁" },
		Cancelled:   { bg:"#fdf2f2", bd:"#e74c3c", tc:"#c0392b", ic:"❌" },
	}[st] || { bg:"#f8f9fa", bd:"#aaa", tc:"#888", ic:"📋" };

	const mat = frm.doc.organisation_materiality;
	const mat_badge = mat
		? `<span style="background:#f0f4ff;border:1px solid #3498db40;color:#2980b9;
		               padding:3px 12px;border-radius:12px;font-size:12px;font-weight:600;">
			Materiality: ${frappe.format(mat,{fieldtype:"Currency"})}
		</span>` : "";

	const ai_tag = frm.doc.ai_generated_on
		? `<span style="font-size:11px;color:#888;">
			🤖 AI: ${frappe.datetime.str_to_user(frm.doc.ai_generated_on)}
		</span>` : "";

	const cae = frm.doc.chief_audit_executive
		? `<span style="font-size:12px;color:#888;">👤 ${frm.doc.chief_audit_executive}</span>`
		: "";

	frm.dashboard.add_comment(`
		<div style="background:${st_cfg.bg};border-left:5px solid ${st_cfg.bd};
		            border-radius:0 8px 8px 0;padding:12px 18px;">
			<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
				<span style="font-size:22px;">${st_cfg.ic}</span>
				<div>
					<div style="font-weight:800;font-size:15px;color:${st_cfg.tc};">
						${frm.doc.plan_title || "Annual Audit Plan"}
					</div>
					<div style="font-size:12px;color:#888;margin-top:2px;">
						${frm.doc.plan_year ? `FY ${frm.doc.plan_year}` : ""}
						${frm.doc.fiscal_year ? ` · ${frm.doc.fiscal_year}` : ""}
						${frm.doc.total_audit_days ? ` · ${frm.doc.total_audit_days} audit days budgeted` : ""}
					</div>
				</div>
				${mat_badge}${cae}${ai_tag}
			</div>
		</div>`, "white", true);
}


// ── Materiality Panel ─────────────────────────────────────────────────────────
function _materiality_panel(frm) {
	const mat = frm.doc.organisation_materiality;
	if (!mat) return;

	const perf_mat  = mat * 0.75;
	const trivial   = mat * 0.05;
	const basis     = frm.doc.materiality_basis_used || "—";
	const pct       = frm.doc.materiality_percentage_used || "—";

	const fmt = v => frappe.format(v, {fieldtype:"Currency"});

	frm.dashboard.add_comment(`
		<div style="background:#f8f9fa;border-radius:8px;padding:12px 14px;">
			<div style="font-size:10px;color:#aaa;font-weight:700;text-transform:uppercase;
			            letter-spacing:.5px;margin-bottom:10px;">
				📐 Organisation Materiality — ${basis} @ ${pct}%
			</div>
			<div style="display:flex;gap:10px;flex-wrap:wrap;">
				${[
					{ l:"Planning Materiality",     v:mat,      c:"#e74c3c" },
					{ l:"Performance Materiality",  v:perf_mat, c:"#e67e22", sub:"75%" },
					{ l:"Trivial Threshold",        v:trivial,  c:"#27ae60", sub:"5%"  },
				].map(m => `
					<div style="background:#fff;border:1px solid #ecf0f1;border-radius:8px;
					            padding:10px 14px;flex:1;min-width:130px;">
						<div style="font-size:18px;font-weight:800;color:${m.c};">${fmt(m.v)}</div>
						<div style="font-size:11px;color:#aaa;margin-top:3px;">
							${m.l}${m.sub ? ` <span style="color:#ccc;">(${m.sub})</span>` : ""}
						</div>
					</div>`).join("")}
			</div>
		</div>`, "white", true);
}


// ── Execution Progress Panel ──────────────────────────────────────────────────
function _progress_panel(frm) {
	const rows = frm.doc.planned_engagements || [];
	const total = rows.length;
	if (!total) return;

	const completed   = rows.filter(r => r.status === "Completed").length;
	const in_progress = rows.filter(r => r.status === "In Progress").length;
	const planned     = rows.filter(r => r.status === "Planned").length;
	const pct         = Math.round(completed / total * 100);

	const bar_segs = [
		{ n:completed,   c:"#27ae60", t:"Completed"   },
		{ n:in_progress, c:"#3498db", t:"In Progress"  },
		{ n:planned,     c:"#bdc3c7", t:"Planned"      },
	].filter(s => s.n > 0).map((s, i, arr) => {
		const w = (s.n / total * 100).toFixed(1);
		const r = i === 0 && arr.length > 1 ? "5px 0 0 5px"
		        : i === arr.length - 1       ? "0 5px 5px 0" : "0";
		return `<div title="${s.t}: ${s.n}" style="flex:${w};background:${s.c};
		             height:12px;border-radius:${r};"></div>`;
	}).join("");

	const stat_pills = [
		{ l:"Completed",   n:completed,   c:"#27ae60" },
		{ l:"In Progress", n:in_progress, c:"#3498db"  },
		{ l:"Planned",     n:planned,     c:"#95a5a6"  },
	].map(p => `<span style="font-size:12px;color:${p.c};">
		<b>${p.n}</b> ${p.l}
	</span>`).join("  ·  ");

	const findings_strip = frm.doc.total_findings_raised
		? `<div style="margin-top:8px;font-size:12px;color:#555;">
			Findings YTD: <b>${frm.doc.total_findings_raised}</b>
			${frm.doc.critical_findings_ytd
				? ` · <span style="color:#e74c3c;"><b>${frm.doc.critical_findings_ytd}</b> critical</span>`
				: ""}
			${frm.doc.open_caps
				? ` · <span style="color:#e67e22;"><b>${frm.doc.open_caps}</b> open CAPs</span>`
				: ""}
		</div>` : "";

	frm.dashboard.add_comment(`
		<div style="background:#f8f9fa;border-radius:8px;padding:12px 14px;">
			<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
				<span style="font-size:13px;font-weight:600;color:#2c3e50;">
					Execution Progress — ${total} engagements
				</span>
				<span style="font-size:15px;font-weight:800;
				             color:${pct===100?"#27ae60":"#3498db"};">${pct}%</span>
			</div>
			<div style="display:flex;border-radius:5px;overflow:hidden;
			            background:#ecf0f1;height:12px;margin-bottom:10px;">
				${bar_segs}
			</div>
			<div style="display:flex;gap:14px;flex-wrap:wrap;">${stat_pills}</div>
			${findings_strip}
		</div>`, "white", true);
}


// ── Client-side materiality calculation ───────────────────────────────────────
function _calc_materiality(frm) {
	const rev = flt(frm.doc.total_revenue);
	const ast = flt(frm.doc.total_assets);
	const pbt = flt(frm.doc.profit_before_tax);

	// Priority: Revenue → Assets → PBT  (conservative, not highest)
	let mat = 0, basis = "", pct = 0;
	if (rev > 0)                      { mat = rev * 0.0075; basis = "Total Revenue";       pct = 0.75; }
	else if (ast > 0)                 { mat = ast * 0.005;  basis = "Total Assets";        pct = 0.50; }
	else if (pbt > 0)                 { mat = pbt * 0.07;   basis = "Profit Before Tax";   pct = 7.00; }

	if (mat > 0) {
		frm.set_value("organisation_materiality",    mat);
		frm.set_value("materiality_basis_used",      basis);
		frm.set_value("materiality_percentage_used", pct);
	}
}


// ── Buttons ───────────────────────────────────────────────────────────────────
function _buttons(frm) {
	if (frm.is_new()) return;

	// Navigation
	frm.add_custom_button("🌐 Audit Universe",
		() => frappe.set_route("List", "Audit Universe"), "View");
	frm.add_custom_button("📋 Registry",
		() => frappe.set_route("List", "Auditable DocType Registry"), "View");
	frm.add_custom_button("🔗 Engagements",
		() => frappe.set_route("List", "Audit Engagement",
			{ annual_audit_plan: frm.doc.name }), "View");

	if (frm.doc.docstatus === 1) {
		// ── AI Prioritisation ─────────────────────────────────────────────
		frm.add_custom_button("🤖 Refresh AI Prioritisation", () => {
			frappe.confirm(
				"Re-score all registered DocTypes and regenerate the prioritisation table?",
				() => frappe.call({
					method: "ecclesia.doctype.annual_audit_plan.annual_audit_plan.run_ai_prioritisation",
					args:   { plan_name: frm.doc.name },
					freeze: true, freeze_message: "Scoring audit universe…",
					callback(r) {
						frm.reload_doc();
						const d = r.message;
						frappe.show_alert({
							message: `🤖 AI complete — ${d.registries_scored} DocTypes scored`,
							indicator: "green",
						}, 5);
					},
				})
			);
		}, "Actions");

		// ── Create Engagement from planned row ────────────────────────────
		frm.add_custom_button("➕ Create Engagement", () =>
			_create_engagement_dialog(frm), "Actions");
	}

	if (frm.doc.docstatus === 0) {
		// ── Preview AI scoring before submit ─────────────────────────────
		frm.add_custom_button("🤖 Preview AI Scoring", () => {
			frappe.call({
				method: "ecclesia.doctype.annual_audit_plan.annual_audit_plan.run_ai_prioritisation",
				args:   { plan_name: frm.doc.name },
				freeze: true, freeze_message: "Scoring audit universe…",
				callback(r) {
					frm.reload_doc();
					frappe.show_alert({ message:"Preview generated — review below", indicator:"blue" }, 4);
				},
			});
		}, "Actions");
	}
}


// ── Create Engagement Dialog ──────────────────────────────────────────────────
function _create_engagement_dialog(frm) {
	const rows = (frm.doc.planned_engagements || [])
		.filter(r => r.status === "Planned" && !r.linked_engagement);

	if (!rows.length) {
		frappe.msgprint({
			title:     "No available rows",
			message:   "All planned engagements already have linked engagements, or none are in 'Planned' status.",
			indicator: "orange",
		});
		return;
	}

	const d = new frappe.ui.Dialog({
		title: "➕ Create Audit Engagement",
		fields: [
			{
				fieldtype: "Select", label: "Planned Engagement", fieldname: "row_name",
				reqd: 1,
				options: rows.map(r => ({ label: r.engagement_title, value: r.name })),
			},
			{ fieldtype: "Column Break" },
			{ fieldtype: "Date",   label: "From Date", fieldname: "from_date", reqd: 1 },
			{ fieldtype: "Date",   label: "To Date",   fieldname: "to_date",   reqd: 1 },
		],
	});

	d.set_primary_action("Create", () => {
		const v = d.get_values();
		if (!v) return;
		frappe.call({
			method: "ecclesia.doctype.annual_audit_plan.annual_audit_plan.create_engagement_from_row",
			args:   {
				plan_name: frm.doc.name,
				row_name:  v.row_name,
				from_date: v.from_date,
				to_date:   v.to_date,
			},
			freeze: true, freeze_message: "Creating engagement…",
			callback(r) {
				d.hide();
				frm.reload_doc();
				frappe.show_alert({ message:"Engagement created ✅", indicator:"green" }, 4);
				frappe.set_route("Form", "Audit Engagement", r.message);
			},
		});
	});
	d.get_primary_btn().css({ background:"#27ae60", color:"#fff", border:"none" });
	d.show();
}


function flt(v) { return parseFloat(v) || 0; }