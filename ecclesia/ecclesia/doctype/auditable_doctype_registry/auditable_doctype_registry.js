// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt



// Fields auto-populated by the registration engine — protect from edits
const AUTO_FIELDS = [
	"transaction_code","module_code","type_code","doctype_classification",
	"risk_level","is_gl_posting","amount_fields","date_fields","approval_fields",
	"party_fields","account_fields","cost_center_fields","status_fields","user_fields",
	"ai_risk_summary","ai_key_controls","ai_red_flags","recommended_sample_size",
	"sampling_method","materiality_benchmark","account_class","financial_statement_line",
	"last_ai_refresh","total_transactions_ytd","last_audit_date","open_findings_count",
	"cumulative_findings","avg_risk_score","last_audit_opinion","registration_date",
];

frappe.ui.form.on("Auditable DocType Registry", {

	refresh(frm) {
		// Mark auto-populated fields read-only
		AUTO_FIELDS.forEach(f => frm.set_df_property(f, "read_only", 1));

		if (frm.doc.transaction_code) {
			_registered_header(frm);
			_ai_profile_panel(frm);
			_stats_panel(frm);
		} else {
			_registration_guide(frm);
		}
		_buttons(frm);
	},

	doctype_json(frm) {
		// Live JSON validation feedback
		if (!frm.doc.doctype_json) return;
		try {
			const dt         = JSON.parse(frm.doc.doctype_json);
			const n_fields   = (dt.fields || []).length;
			const has_amount = (dt.fields||[]).some(f =>
				["Currency","Float","Int"].includes(f.fieldtype) && /amount|total|value/i.test(f.fieldname));
			const has_date   = (dt.fields||[]).some(f => f.fieldtype === "Date");

			frappe.show_alert({
				message:`✅ Valid JSON — <b>${dt.name}</b>, ${n_fields} fields
				         ${has_amount?"· 💰 amount fields detected":""}
				         ${has_date?"· 📅 date fields detected":""}.
				         <br><small>Save to register and auto-classify.</small>`,
				indicator:"green",
			}, 7);
		} catch (e) {
			frappe.show_alert({
				message:`❌ Invalid JSON — ${e.message}`,
				indicator:"red",
			}, 6);
		}
	},
});


// ── Registration Guide (new / unregistered) ───────────────────────────────────
function _registration_guide(frm) {
	frm.dashboard.add_comment(`
		<div style="background:#f0f4ff;border-left:5px solid #3498db;
		            border-radius:0 8px 8px 0;padding:16px 20px;">
			<div style="font-size:16px;font-weight:700;color:#2980b9;margin-bottom:10px;">
				🚀 Register a DocType for Audit Coverage
			</div>
			<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin-bottom:12px;">
				${[
					["1️⃣","Go to Setup","DocType → choose your DocType"],
					["2️⃣","Export JSON","Menu → Export → copy the JSON"],
					["3️⃣","Paste below","Into the DocType JSON field"],
					["4️⃣","Save","The system auto-classifies everything"],
				].map(([ic,h,t]) => `
					<div style="background:#fff;border:1px solid #d6e4ff;border-radius:8px;padding:10px 12px;">
						<div style="font-size:18px;">${ic}</div>
						<div style="font-weight:700;font-size:12px;color:#2c3e50;margin-top:4px;">${h}</div>
						<div style="font-size:11px;color:#888;margin-top:2px;">${t}</div>
					</div>`).join("")}
			</div>
			<div style="font-size:12px;color:#888;">
				The engine will auto-assign a transaction code, classify the DocType,
				detect GL posting, map fields, and generate the AI risk profile.
				<b>You only need to do this once per DocType.</b>
			</div>
		</div>`, "white", true);
}


// ── Registered Header ─────────────────────────────────────────────────────────
function _registered_header(frm) {
	const risk_c = {
		Critical:"#e74c3c", High:"#e67e22", Medium:"#f39c12", Low:"#27ae60"
	}[frm.doc.risk_level] || "#aaa";
	const freq_c = {
		Monthly:"#e74c3c", Quarterly:"#e67e22", "Semi-Annual":"#f39c12",
		Annual:"#27ae60", "As Required":"#3498db"
	}[frm.doc.audit_frequency] || "#888";

	const opinion_ic = {
		Unqualified:"✅", Qualified:"⚠️", Adverse:"❌", Disclaimer:"❓"
	}[frm.doc.last_audit_opinion] || "";

	frm.dashboard.add_comment(`
		<div style="background:#f0fdf4;border-left:5px solid #27ae60;
		            border-radius:0 8px 8px 0;padding:12px 18px;">
			<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:8px;">
				<span style="font-size:22px;">✅</span>
				<div>
					<div style="font-weight:700;font-size:14px;color:#1e8449;">
						Registered — ${frm.doc.doctype_classification||"Classified"}
					</div>
					<div style="font-size:12px;color:#888;margin-top:2px;">
						Since: ${frm.doc.registration_date
							? frappe.datetime.str_to_user(frm.doc.registration_date) : "—"}
					</div>
				</div>
				<code style="background:#2c3e50;color:#ecf0f1;padding:4px 10px;
				             border-radius:4px;font-size:13px;font-weight:700;">
					${frm.doc.transaction_code}
				</code>
			</div>
			<div style="display:flex;gap:10px;flex-wrap:wrap;font-size:12px;">
				<span style="background:${risk_c}20;border:1px solid ${risk_c};color:${risk_c};
				             padding:2px 10px;border-radius:10px;font-weight:600;">
					${frm.doc.risk_level||"—"} Risk
				</span>
				<span style="background:#f0f4ff;border:1px solid #3498db40;color:#2980b9;
				             padding:2px 10px;border-radius:10px;">
					${frm.doc.is_gl_posting ? "💳 GL-posting" : "No GL posting"}
				</span>
				<span style="background:${freq_c}20;border:1px solid ${freq_c}60;color:${freq_c};
				             padding:2px 10px;border-radius:10px;">
					📅 ${frm.doc.audit_frequency||"—"}
				</span>
				${frm.doc.last_audit_opinion
					? `<span style="background:#f8f9fa;border:1px solid #dee2e6;color:#555;
					               padding:2px 10px;border-radius:10px;">
						Last opinion: ${opinion_ic} ${frm.doc.last_audit_opinion}
					</span>` : ""}
				${!frm.doc.is_active
					? `<span style="background:#fdf2f2;border:1px solid #e74c3c;color:#e74c3c;
					               padding:2px 10px;border-radius:10px;font-weight:600;">
						⚠️ Inactive
					</span>` : ""}
			</div>
		</div>`, "white", true);
}


// ── AI Profile Panel ──────────────────────────────────────────────────────────
function _ai_profile_panel(frm) {
	if (!frm.doc.ai_risk_summary) return;

	const score     = frm.doc.avg_risk_score ? Math.round(frm.doc.avg_risk_score) : null;
	const score_c   = score >= 70 ? "#e74c3c" : score >= 40 ? "#e67e22" : "#27ae60";
	const score_html = score !== null
		? `<div style="text-align:center;margin-bottom:10px;">
			<div style="font-size:38px;font-weight:800;color:${score_c};">${score}</div>
			<div style="font-size:11px;color:#aaa;font-weight:600;text-transform:uppercase;">AI Risk Score /100</div>
			<div style="background:#f0f0f0;border-radius:10px;height:8px;overflow:hidden;margin-top:6px;">
				<div style="background:linear-gradient(90deg,${score_c}88,${score_c});
				            width:${score}%;height:8px;border-radius:10px;"></div>
			</div>
		</div>` : "";

	frm.dashboard.add_comment(`
		<div style="background:#f8f9fa;border-radius:8px;padding:12px 14px;">
			<div style="font-size:10px;color:#aaa;font-weight:700;text-transform:uppercase;
			            letter-spacing:.5px;margin-bottom:10px;">🤖 AI Intelligence Profile</div>
			${score_html}
			<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;font-size:12px;">
				<div>
					<div style="font-weight:700;color:#2c3e50;margin-bottom:4px;">Risk Summary</div>
					<div style="color:#555;line-height:1.5;">${(frm.doc.ai_risk_summary||"").substring(0,200)}${(frm.doc.ai_risk_summary||"").length>200?"…":""}</div>
				</div>
				<div>
					<div style="font-weight:700;color:#e74c3c;margin-bottom:4px;">🚩 Red Flags</div>
					<div style="color:#555;line-height:1.5;">${(frm.doc.ai_red_flags||"<em>None identified</em>").substring(0,200)}</div>
				</div>
			</div>
			<div style="margin-top:8px;font-size:11px;color:#aaa;">
				Last AI refresh: ${frm.doc.last_ai_refresh
					? frappe.datetime.str_to_user(frm.doc.last_ai_refresh) : "Never"}
			</div>
		</div>`, "white", true);
}


// ── Live Stats Panel ──────────────────────────────────────────────────────────
function _stats_panel(frm) {
	const t = frm.doc.total_transactions_ytd || 0;
	if (!t && !frm.doc.open_findings_count) return;

	const stat_cards = [
		{ l:"Transactions YTD", n: t.toLocaleString(),                   ic:"📊", c:"#3498db" },
		{ l:"Open Findings",    n: frm.doc.open_findings_count  || 0,    ic:"🔎", c:"#e74c3c" },
		{ l:"Total Findings",   n: frm.doc.cumulative_findings  || 0,    ic:"📈", c:"#e67e22" },
		{ l:"Sample Size",      n: `${frm.doc.recommended_sample_size||"—"}%`, ic:"🎯", c:"#9b59b6" },
	].map(s => `
		<div style="background:#fff;border:1px solid #ecf0f1;border-radius:8px;padding:10px 12px;flex:1;min-width:90px;">
			<div style="font-size:18px;margin-bottom:2px;">${s.ic}</div>
			<div style="font-size:18px;font-weight:800;color:${s.c};">${s.n}</div>
			<div style="font-size:10px;color:#aaa;font-weight:600;text-transform:uppercase;">${s.l}</div>
		</div>`).join("");

	frm.dashboard.add_comment(`
		<div>
			<div style="font-size:10px;color:#aaa;font-weight:700;text-transform:uppercase;
			            letter-spacing:.5px;margin-bottom:8px;">📊 Live Statistics</div>
			<div style="display:flex;gap:8px;flex-wrap:wrap;">${stat_cards}</div>
			${frm.doc.last_audit_date
				? `<div style="font-size:11px;color:#aaa;margin-top:8px;">
					Last audited: <b>${frm.doc.last_audit_date}</b>
				</div>` : ""}
		</div>`, "white", true);
}


// ── Buttons ───────────────────────────────────────────────────────────────────
function _buttons(frm) {
	if (frm.is_new()) return;

	if (frm.doc.transaction_code) {
		frm.add_custom_button("📋 Checklist Templates",
			() => frappe.set_route("List","Audit Checklist Template",{doctype_name:frm.doc.doctype_name}), "View");
		frm.add_custom_button("🔎 All Findings",
			() => frappe.set_route("List","Audit Finding",{reference_doctype:frm.doc.doctype_name}), "View");
		frm.add_custom_button("🌐 Audit Universe",
			() => frappe.set_route("List","Audit Universe"), "View");

		frm.add_custom_button("🤖 Refresh AI Profile", () => {
			frappe.confirm(`Re-run AI analysis for <b>${frm.doc.doctype_name}</b>?`, () => {
				frappe.call({
					method:"ecclesia.utils.ai_engine.refresh_single_doctype_stats",
					args:{ doctype_name: frm.doc.doctype_name },
					freeze:true, freeze_message:"Running AI analysis…",
					callback() {
						frm.reload_doc();
						frappe.show_alert({ message:"AI profile refreshed ✅", indicator:"green" }, 4);
					}
				});
			});
		}, "Actions");

		frm.add_custom_button("🔄 Sync Audit Universe", () => {
			frappe.call({
				method:"ecclesia.doctype.audit_universe.audit_universe.sync_audit_universe",
				freeze:true, freeze_message:"Syncing…",
				callback(r) {
					frappe.show_alert({ message:r.message||"Audit Universe synced ✅", indicator:"green" }, 4);
				}
			});
		}, "Actions");
	}
}