// Copyright (c) 2026, kunle Oduntan and contributors
// For license information, please see license.txt

// ╔══════════════════════════════════════════════════════════════════════╗
// ║  GL AUDIT LOG  ·  Ecclesia  ·  IMMUTABLE RECORD                      ║
// ╚══════════════════════════════════════════════════════════════════════╝

frappe.ui.form.on("GL Audit Log", {

	refresh(frm) {
		// GL Audit Logs are immutable — disable the Save button
		frm.disable_save();

		_header(frm);
		_detail_panel(frm);
		_buttons(frm);
	},
});


// ── Event Header ──────────────────────────────────────────────────────────────
function _header(frm) {
	const ev = frm.doc.event_type;

	const ev_cfg = {
		"GL Entry Created":        { bg:"#f0f4ff", bd:"#3498db", tc:"#2980b9", ic:"📗" },
		"GL Entry Cancelled":      { bg:"#fdf2f2", bd:"#e74c3c", tc:"#c0392b", ic:"❌" },
		"GL Entry Amended":        { bg:"#fdf6ec", bd:"#e67e22", tc:"#d35400", ic:"✏️"  },
		"Journal Entry Submitted": { bg:"#f0fdf4", bd:"#27ae60", tc:"#1e8449", ic:"📒" },
		"Reconciliation Variance": { bg:"#fdf2f2", bd:"#e74c3c", tc:"#c0392b", ic:"⚖️"  },
		"Suspense Account Used":   { bg:"#fdf2f2", bd:"#e74c3c", tc:"#c0392b", ic:"🔴" },
	}[ev] || { bg:"#f8f9fa", bd:"#bdc3c7", tc:"#888", ic:"📋" };

	// Risk flag banner
	const risk_banner = frm.doc.risk_flag
		? `<div style="background:#fdf2f2;border-left:4px solid #e74c3c;padding:10px 14px;
		              border-radius:4px;margin-bottom:10px;">
			<div style="font-weight:700;font-size:14px;color:#c0392b;">🚩 RISK FLAGGED</div>
			<div style="font-size:12px;color:#888;margin-top:3px;">
				${frm.doc.flag_reason || "This GL event has been flagged for auditor review."}
			</div>
		</div>` : "";

	// Immutability notice
	const immutable_notice = `
		<div style="background:#f8f9fa;border:1px dashed #dee2e6;padding:6px 12px;
		            border-radius:4px;margin-bottom:10px;font-size:11px;color:#aaa;
		            display:flex;align-items:center;gap:6px;">
			🔐 <span>This record is <b>immutable</b> — GL Audit Logs cannot be edited after creation.</span>
		</div>`;

	const amounts = frm.doc.debit_amount || frm.doc.credit_amount
		? `<div style="display:flex;gap:10px;margin-top:6px;font-size:12px;">
			${frm.doc.debit_amount
				? `<span style="color:#e74c3c;">DR: <b>${frappe.format(frm.doc.debit_amount,{fieldtype:"Currency"})}</b></span>`
				: ""}
			${frm.doc.credit_amount
				? `<span style="color:#27ae60;">CR: <b>${frappe.format(frm.doc.credit_amount,{fieldtype:"Currency"})}</b></span>`
				: ""}
		</div>` : "";

	const who = frm.doc.event_user
		? `<div style="font-size:11px;color:#aaa;margin-top:4px;">
			👤 <b>${frm.doc.event_user}</b>
			${frm.doc.event_datetime
				? ` at ${frappe.datetime.str_to_user(frm.doc.event_datetime)}` : ""}
		</div>` : "";

	frm.dashboard.add_comment(`
		${immutable_notice}
		${risk_banner}
		<div style="background:${ev_cfg.bg};border-left:5px solid ${ev_cfg.bd};
		            border-radius:0 8px 8px 0;padding:12px 16px;">
			<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
				<span style="font-size:22px;">${ev_cfg.ic}</span>
				<div>
					<div style="font-weight:700;font-size:14px;color:${ev_cfg.tc};">${ev||"GL Event"}</div>
					<div style="font-size:12px;color:#888;margin-top:2px;">
						${frm.doc.voucher_type||""} · <b>${frm.doc.voucher_no||"—"}</b>
						· posting ${frm.doc.posting_date||"—"}
					</div>
				</div>
				${frm.doc.transaction_code
					? `<code style="background:#2c3e50;color:#ecf0f1;padding:3px 8px;
					              border-radius:4px;font-size:11px;">${frm.doc.transaction_code}</code>`
					: ""}
			</div>
			${amounts}${who}
		</div>`, "white", true);
}


// ── Detail Panel ──────────────────────────────────────────────────────────────
function _detail_panel(frm) {
	if (!frm.doc.gl_account) return;

	const net = (flt(frm.doc.debit_amount) - flt(frm.doc.credit_amount));
	const net_color = net > 0 ? "#e74c3c" : "#27ae60";
	const net_label = net > 0 ? "Net Debit" : "Net Credit";

	frm.dashboard.add_comment(`
		<div style="background:#f8f9fa;border-radius:8px;padding:12px 14px;font-size:12px;">
			<div style="font-size:10px;color:#aaa;font-weight:700;text-transform:uppercase;
			            letter-spacing:.5px;margin-bottom:8px;">GL Transaction Detail</div>
			<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;">
				<div>
					<div style="color:#aaa;font-size:10px;font-weight:600;text-transform:uppercase;">GL Account</div>
					<div style="font-weight:700;color:#2c3e50;margin-top:3px;">${frm.doc.gl_account||"—"}</div>
				</div>
				<div>
					<div style="color:#aaa;font-size:10px;font-weight:600;text-transform:uppercase;">Debit / Credit</div>
					<div style="margin-top:3px;">
						<span style="color:#e74c3c;font-weight:700;">
							DR ${frappe.format(frm.doc.debit_amount||0,{fieldtype:"Currency"})}
						</span>
						&nbsp;/&nbsp;
						<span style="color:#27ae60;font-weight:700;">
							CR ${frappe.format(frm.doc.credit_amount||0,{fieldtype:"Currency"})}
						</span>
					</div>
				</div>
				<div>
					<div style="color:#aaa;font-size:10px;font-weight:600;text-transform:uppercase;">${net_label}</div>
					<div style="font-size:16px;font-weight:800;color:${net_color};margin-top:3px;">
						${frappe.format(Math.abs(net),{fieldtype:"Currency"})}
					</div>
				</div>
			</div>
		</div>`, "white", true);
}


// ── Buttons ───────────────────────────────────────────────────────────────────
function _buttons(frm) {
	if (frm.is_new()) return;

	// Open source voucher
	if (frm.doc.voucher_type && frm.doc.voucher_no)
		frm.add_custom_button("📂 Open Source",
			() => frappe.set_route("Form",frm.doc.voucher_type,frm.doc.voucher_no), "View");

	// Open linked finding
	if (frm.doc.linked_finding)
		frm.add_custom_button("📌 View Finding",
			() => frappe.set_route("Form","Audit Finding",frm.doc.linked_finding), "View");

	// Raise finding if risk-flagged and none exists yet
	if (frm.doc.risk_flag && !frm.doc.linked_finding)
		frm.add_custom_button("🚨 Raise Finding", () => {
			frappe.new_doc("Audit Finding", {
				finding_title:     `GL Exception: ${frm.doc.event_type} — ${frm.doc.voucher_no}`,
				finding_type:      _event_to_finding_type(frm.doc.event_type),
				risk_rating:       "High",
				source:            "Continuous Monitoring",
				reference_doctype: frm.doc.voucher_type,
				reference_name:    frm.doc.voucher_no,
				transaction_code:  frm.doc.transaction_code,
				observation:       frm.doc.flag_reason,
				gl_entry_reference:frm.doc.voucher_no,
				transaction_amount:(frm.doc.debit_amount||frm.doc.credit_amount),
			});
		}, "Actions");

	// Dismiss flag (with confirmation)
	if (frm.doc.risk_flag && !frm.doc.linked_finding)
		frm.add_custom_button("✔ Dismiss Flag", () => {
			frappe.confirm(
				"Dismiss this risk flag without raising a finding? Document your reason first.",
				() => frappe.db.set_value("GL Audit Log", frm.doc.name, "risk_flag", 0)
				             .then(() => { frm.reload_doc();
				                 frappe.show_alert({ message:"Risk flag dismissed", indicator:"blue" }, 3);
				             })
			);
		}, "Actions");
}

// Map GL event types to Finding types
function _event_to_finding_type(ev) {
	return {
		"GL Entry Cancelled":      "GL Posting Error",
		"GL Entry Amended":        "GL Posting Error",
		"Reconciliation Variance": "GL Posting Error",
		"Suspense Account Used":   "Policy Non-Compliance",
		"Journal Entry Submitted": "Other",
	}[ev] || "Other";
}

function flt(v) { return parseFloat(v)||0; }