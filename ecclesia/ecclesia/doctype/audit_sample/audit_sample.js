// Copyright (c) 2026, kunle Oduntan and contributors
// For license information, please see license.txt



frappe.ui.form.on("Audit Sample", {

	refresh(frm) {
		_header(frm);
		_buttons(frm);
	},

	status(frm)       { _header(frm); },
	is_ai_flagged(frm){ _header(frm); },

	reference_doctype(frm) {
		// Auto-fill transaction code from registry when DocType is selected
		if (!frm.doc.reference_doctype) return;
		frappe.db.get_value("Auditable DocType Registry",
			{ doctype_name: frm.doc.reference_doctype },
			["transaction_code","risk_level","sampling_method"],
			v => {
				if (!v) return;
				if (!frm.doc.transaction_code)
					frm.set_value("transaction_code", v.transaction_code);
				frappe.show_alert({
					message:`DocType info loaded — <b>${v.risk_level}</b> risk, ${v.sampling_method} sampling`,
					indicator:"blue",
				}, 4);
			});
	},
});


// ── Header ────────────────────────────────────────────────────────────────────
function _header(frm) {
	const st = frm.doc.status || "Pending Review";
	const ai = frm.doc.is_ai_flagged;

	const st_cfg = {
		"Pending Review":   { bg:"#f0f4ff", bd:"#3498db", tc:"#2980b9", ic:"🔍" },
		"Under Review":     { bg:"#f3e5f5", bd:"#9b59b6", tc:"#8e44ad", ic:"⚙️" },
		"Exception Raised": { bg:"#fdf2f2", bd:"#e74c3c", tc:"#c0392b", ic:"🚨" },
		"Cleared":          { bg:"#f0fdf4", bd:"#27ae60", tc:"#1e8449", ic:"✅" },
		"Not Applicable":   { bg:"#f8f9fa", bd:"#95a5a6", tc:"#7f8c8d", ic:"➖" },
	}[st] || { bg:"#f8f9fa", bd:"#bdc3c7", tc:"#888", ic:"📋" };

	const ai_banner = ai
		? `<div style="background:#fdf2f2;border-left:4px solid #e74c3c;padding:8px 14px;
		              border-radius:4px;margin-bottom:8px;font-weight:700;color:#c0392b;font-size:13px;">
			🤖 AI FLAGGED — This sample was auto-selected due to an anomaly.
			<div style="font-size:11px;font-weight:400;color:#888;margin-top:3px;">
				Selection basis: <b>${frm.doc.selection_basis||"Algorithmic flag"}</b>
			</div>
		</div>` : "";

	const amount = frm.doc.sample_amount
		? `<span style="background:#f0f4ff;border:1px solid #3498db40;color:#2980b9;
		               padding:3px 10px;border-radius:12px;font-size:12px;">
			💰 ${frappe.format(frm.doc.sample_amount,{fieldtype:"Currency"})}
		</span>` : "";

	const code = frm.doc.transaction_code
		? `<code style="background:#2c3e50;color:#ecf0f1;padding:3px 8px;border-radius:4px;font-size:11px;">
			${frm.doc.transaction_code}
		</code>` : "";

	frm.dashboard.add_comment(`
		${ai_banner}
		<div style="background:${st_cfg.bg};border-left:5px solid ${st_cfg.bd};
		            border-radius:0 8px 8px 0;padding:12px 16px;">
			<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
				<span style="font-size:20px;">${st_cfg.ic}</span>
				<span style="font-weight:700;font-size:14px;color:${st_cfg.tc};">${st}</span>
				${amount}${code}
			</div>
			<div style="margin-top:5px;font-size:12px;color:#aaa;">
				${frm.doc.reference_doctype ? `📦 <b>${frm.doc.reference_doctype}</b>` : ""}
				${frm.doc.reference_name ? ` → ${frm.doc.reference_name}` : ""}
				${frm.doc.selection_basis && !ai
					? ` &nbsp;·&nbsp; Selection: <b>${frm.doc.selection_basis}</b>` : ""}
			</div>
		</div>`, "white", true);
}


// ── Buttons ───────────────────────────────────────────────────────────────────
function _buttons(frm) {
	if (frm.is_new()) return;

	// Link to source document
	if (frm.doc.reference_doctype && frm.doc.reference_name)
		frm.add_custom_button("📂 Open Document",
			() => frappe.set_route("Form",frm.doc.reference_doctype,frm.doc.reference_name), "View");

	// Link to existing finding
	if (frm.doc.audit_finding)
		frm.add_custom_button("📌 View Finding",
			() => frappe.set_route("Form","Audit Finding",frm.doc.audit_finding), "View");

	// Start review
	if (frm.doc.status === "Pending Review")
		frm.add_custom_button("▶ Start Review", () => {
			frappe.db.set_value("Audit Sample", frm.doc.name, "status","Under Review")
			         .then(() => { frm.reload_doc();
			             frappe.show_alert({ message:"Sample under review 🔍", indicator:"blue" }, 3);
			         });
		}, "Actions");

	// Raise finding from this sample
	if (!frm.doc.audit_finding && frm.doc.status !== "Cleared")
		frm.add_custom_button("🚨 Raise Finding", () => _raise_finding_dialog(frm), "Actions");

	// Clear sample
	if (["Pending Review","Under Review"].includes(frm.doc.status) && !frm.doc.audit_finding)
		frm.add_custom_button("✅ Clear — No Exception", () => {
			frappe.confirm("Mark this sample as <b>Cleared</b> (no exception found)?", () =>
				frappe.db.set_value("Audit Sample", frm.doc.name, "status","Cleared")
				         .then(() => { frm.reload_doc();
				             frappe.show_alert({ message:"Sample cleared ✅", indicator:"green" }, 3);
				         })
			);
		}, "Actions");
}


// ── Raise Finding Dialog ──────────────────────────────────────────────────────
function _raise_finding_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: "🚨 Raise Audit Finding from Sample",
		size: "large",
		fields: [
			{ fieldtype:"HTML",   fieldname:"info" },
			{ fieldtype:"Data",   label:"Finding Title",  fieldname:"finding_title", reqd:1 },
			{ fieldtype:"Select", label:"Risk Rating",    fieldname:"risk_rating", reqd:1,
			  options:"Critical\nHigh\nMedium\nLow", default:"Medium" },
			{ fieldtype:"Select", label:"Finding Type",   fieldname:"finding_type",
			  options:"Control Deficiency\nSegregation of Duties\nUnauthorized Transaction\nPolicy Non-Compliance\nGL Posting Error\nCutoff Error\nDuplicate Transaction\nMissing Documentation\nApproval Bypass\nFraud Indicator\nStatistical Outlier\nOther" },
			{ fieldtype:"Column Break" },
			{ fieldtype:"Select", label:"COSO Component", fieldname:"coso_component",
			  options:"\nControl Environment\nRisk Assessment\nControl Activities\nInformation & Communication\nMonitoring" },
			{ fieldtype:"Text Editor", label:"Observation / Condition (What is)", fieldname:"condition", reqd:1 },
			{ fieldtype:"Currency",    label:"Financial Impact",  fieldname:"financial_impact" },
		]
	});

	d.fields_dict.info.$wrapper.html(`
		<div style="background:#fef9ec;border-left:4px solid #f39c12;padding:10px 14px;
		            border-radius:4px;margin-bottom:4px;font-size:13px;">
			Creating a finding from sample:
			<b>${frm.doc.reference_doctype} / ${frm.doc.reference_name}</b>
			${frm.doc.is_ai_flagged ? " · <span style='color:#e74c3c;'>🤖 AI Flagged</span>" : ""}
		</div>`);

	d.set_primary_action("🚨 Raise Finding", () => {
		const v = d.get_values(); if (!v) return;
		frappe.new_doc("Audit Finding", {
			finding_title:      v.finding_title,
			risk_rating:        v.risk_rating,
			finding_type:       v.finding_type,
			coso_component:     v.coso_component,
			condition:          v.condition,
			financial_impact:   v.financial_impact,
			audit_engagement:   frm.doc.audit_engagement,
			reference_doctype:  frm.doc.reference_doctype,
			reference_name:     frm.doc.reference_name,
			transaction_code:   frm.doc.transaction_code,
			source:             frm.doc.is_ai_flagged ? "AI Auto-Detection" : "Auditor",
			transaction_amount: frm.doc.sample_amount,
		});
		// Mark sample as exception raised
		frappe.db.set_value("Audit Sample", frm.doc.name, "status","Exception Raised");
		d.hide();
	});
	d.get_primary_btn().css({ background:"#e74c3c", color:"#fff", border:"none" });
	d.show();
}