// Copyright (c) 2026, kunle Oduntan and contributors
// For license information, please see license.txt

// ╔══════════════════════════════════════════════════════════════════════╗
// ║  AUDIT REPORT  ·  Ecclesia                                           ║
// ╚══════════════════════════════════════════════════════════════════════╝

frappe.ui.form.on("Audit Report", {

	refresh(frm) {
		_opinion_banner(frm);
		_findings_bars(frm);
		_cap_status(frm);
		_buttons(frm);
	},

	audit_opinion(frm) { _opinion_banner(frm); },

	audit_engagement(frm) {
		if (!frm.doc.audit_engagement) return;
		frappe.db.get_value("Audit Engagement", frm.doc.audit_engagement,
			["from_date","to_date","engagement_title","lead_auditor","overall_materiality"], v => {
				if (!v) return;
				if (!frm.doc.report_title)
					frm.set_value("report_title", `Audit Report — ${v.engagement_title}`);
				if (!frm.doc.report_date)
					frm.set_value("report_date", frappe.datetime.get_today());
				if (!frm.doc.issued_by)
					frm.set_value("issued_by", frappe.session.user);
				frappe.show_alert({ message:"Engagement linked ✅ — report details auto-filled", indicator:"green" }, 3);
			});
	},
});


// ── Opinion Banner ────────────────────────────────────────────────────────────
function _opinion_banner(frm) {
	const op = frm.doc.audit_opinion;

	if (!op) {
		frm.dashboard.add_comment(`
			<div style="background:#f0f4ff;border-left:5px solid #3498db;
			            border-radius:0 8px 8px 0;padding:14px 18px;
			            display:flex;align-items:center;gap:12px;">
				<span style="font-size:24px;">📄</span>
				<div>
					<div style="font-weight:700;color:#2980b9;">Report in Draft</div>
					<div style="font-size:12px;color:#888;margin-top:2px;">
						Select an <b>Audit Opinion</b> to finalise this report.
					</div>
				</div>
			</div>`, "white", true);
		return;
	}

	const op_cfg = {
		Unqualified: { bg:"#f0fdf4", bd:"#27ae60", tc:"#1e8449", ic:"✅",
		               tag:"Clean opinion — controls operating effectively." },
		Qualified:   { bg:"#fdf6ec", bd:"#e67e22", tc:"#d35400", ic:"⚠️",
		               tag:"Qualified — specific matters require attention." },
		Adverse:     { bg:"#fdf2f2", bd:"#e74c3c", tc:"#c0392b", ic:"❌",
		               tag:"Adverse — significant control deficiencies identified." },
		Disclaimer:  { bg:"#f8f9fa", bd:"#7f8c8d", tc:"#555",   ic:"❓",
		               tag:"Disclaimer — insufficient evidence to form an opinion." },
	}[op];

	const impact = frm.doc.total_financial_impact
		? `<span style="background:${op_cfg.bg};border:1px solid ${op_cfg.bd}40;color:${op_cfg.tc};
		               padding:3px 12px;border-radius:12px;font-size:12px;font-weight:600;">
			💰 ${frappe.format(frm.doc.total_financial_impact,{fieldtype:"Currency"})}
		</span>` : "";

	const period = frm.doc.audit_period_from
		? `<span style="font-size:12px;color:#888;">📅 ${frm.doc.audit_period_from} → ${frm.doc.audit_period_to||"—"}</span>`
		: "";

	const stats = [
		frm.doc.total_findings ? `<span>📊 <b>${frm.doc.total_findings}</b> findings</span>` : "",
		frm.doc.critical_count ? `<span style="color:#e74c3c;">🔴 <b>${frm.doc.critical_count}</b> critical</span>` : "",
		frm.doc.high_count     ? `<span style="color:#e67e22;">🟠 <b>${frm.doc.high_count}</b> high</span>` : "",
		frm.doc.open_caps_count    ? `<span style="color:#9b59b6;">📋 <b>${frm.doc.open_caps_count}</b> open CAPs</span>` : "",
		frm.doc.overdue_caps_count ? `<span style="color:#e74c3c;">⏰ <b>${frm.doc.overdue_caps_count}</b> overdue</span>` : "",
	].filter(Boolean).join("  ·  ");

	frm.dashboard.add_comment(`
		<div style="background:${op_cfg.bg};border-left:5px solid ${op_cfg.bd};
		            border-radius:0 8px 8px 0;padding:14px 18px;">
			<div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:8px;">
				<span style="font-size:32px;">${op_cfg.ic}</span>
				<div>
					<div style="font-size:17px;font-weight:800;color:${op_cfg.tc};">
						${op} Opinion
					</div>
					<div style="font-size:12px;color:#888;margin-top:2px;">${op_cfg.tag}</div>
				</div>
				${impact}${period}
			</div>
			<div style="font-size:12px;color:#666;display:flex;gap:12px;flex-wrap:wrap;">${stats}</div>
		</div>`, "white", true);
}


// ── Findings Horizontal Bars ──────────────────────────────────────────────────
function _findings_bars(frm) {
	const t = frm.doc.total_findings || 0;
	if (!t) return;

	const data = [
		{ l:"Critical", n:frm.doc.critical_count||0, c:"#e74c3c" },
		{ l:"High",     n:frm.doc.high_count||0,     c:"#e67e22" },
		{ l:"Medium",   n:frm.doc.medium_count||0,   c:"#f39c12" },
		{ l:"Low",      n:frm.doc.low_count||0,      c:"#27ae60" },
	];
	const max = Math.max(...data.map(d=>d.n), 1);
	const rows = data.map(d => `
		<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
			<div style="width:64px;text-align:right;font-size:12px;color:#666;">${d.l}</div>
			<div style="flex:1;background:#f0f0f0;border-radius:5px;height:14px;overflow:hidden;">
				<div style="background:${d.c};width:${d.n/max*100}%;height:14px;border-radius:5px;
				            transition:width .4s ease;"></div>
			</div>
			<div style="width:28px;font-size:12px;font-weight:700;color:${d.c};">${d.n}</div>
		</div>`).join("");

	frm.dashboard.add_comment(`
		<div style="background:#f8f9fa;border-radius:8px;padding:12px 14px;">
			<div style="font-size:10px;color:#aaa;font-weight:700;text-transform:uppercase;
			            letter-spacing:.5px;margin-bottom:10px;">
				Findings Distribution — ${t} total
				${frm.doc.material_findings
					? ` · <span style="color:#e74c3c;">${frm.doc.material_findings} material</span>` : ""}
			</div>
			${rows}
		</div>`, "white", true);
}


// ── CAP Status Panel ──────────────────────────────────────────────────────────
function _cap_status(frm) {
	const open    = frm.doc.open_caps_count    || 0;
	const overdue = frm.doc.overdue_caps_count || 0;
	if (!open && !overdue) return;

	frm.dashboard.add_comment(`
		<div style="background:${overdue?"#fdf2f2":"#fef9ec"};border-left:4px solid ${overdue?"#e74c3c":"#f39c12"};
		            padding:10px 14px;border-radius:4px;">
			<div style="font-weight:700;color:${overdue?"#c0392b":"#e67e22"};margin-bottom:4px;">
				${overdue ? "⏰" : "📋"} CAP Status Alert
			</div>
			<div style="font-size:13px;color:#555;">
				${open} open CAP(s)
				${overdue ? ` · <b style="color:#e74c3c;">${overdue} overdue</b>` : ""}
				— immediate follow-up recommended.
			</div>
		</div>`, "white", true);
}


// ── Buttons ───────────────────────────────────────────────────────────────────
function _buttons(frm) {
	if (frm.is_new()) return;

	if (frm.doc.audit_engagement)
		frm.add_custom_button("🔗 Engagement",
			() => frappe.set_route("Form","Audit Engagement",frm.doc.audit_engagement), "View");
	frm.add_custom_button("🔎 Findings",
		() => frappe.set_route("List","Audit Finding",{audit_engagement:frm.doc.audit_engagement}), "View");
	frm.add_custom_button("📋 CAPs",
		() => frappe.set_route("List","Corrective Action Plan"), "View");

	if (frm.doc.docstatus === 0) {
		frm.add_custom_button("🔄 Regenerate Content", () => {
			frappe.confirm(
				"Regenerate executive summary, findings table, and FS impact from current engagement data?",
				() => frm.save().then(() => {
					frm.reload_doc();
					frappe.show_alert({ message:"Report content regenerated ✅", indicator:"green" }, 4);
				})
			);
		}, "Actions");
	}

	if (frm.doc.docstatus === 1 && frm.doc.distribution_list) {
		frm.add_custom_button("📧 Send to Distribution", () => {
			const recipients = (frm.doc.distribution_list||"").split(/[\n,;]+/).map(s=>s.trim()).filter(Boolean);
			frappe.confirm(
				`Send this report to <b>${recipients.length}</b> recipient(s)?<br>
				 <small style="color:#888;">${recipients.slice(0,4).join(", ")}${recipients.length>4?"…":""}</small>`,
				() => frappe.call({
					method:"ecclesia.doctype.audit_report.audit_report.send_report_distribution",
					args:{ report_name:frm.doc.name },
					callback(r) {
						frappe.show_alert({ message:`Report sent to ${recipients.length} recipient(s) 📧`, indicator:"green" }, 5);
					}
				})
			);
		}, "Actions");
	}
}