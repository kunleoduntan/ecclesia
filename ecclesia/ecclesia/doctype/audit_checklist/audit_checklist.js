// Copyright (c) 2026, kunle Oduntan and contributors
// For license information, please see license.txt

// ╔══════════════════════════════════════════════════════════════════════╗
// ║  AUDIT CHECKLIST  ·  Ecclesia                                        ║
// ╚══════════════════════════════════════════════════════════════════════╝

frappe.ui.form.on("Audit Checklist", {

	refresh(frm) {
		_header(frm);
		_progress(frm);
		_buttons(frm);
	},

	status(frm) { _header(frm); },
});


// ── Child table: Audit Checklist Item ─────────────────────────────────────────
frappe.ui.form.on("Audit Checklist Item", {

	result(frm, cdt, cdn) {
		const row = locals[cdt][cdn];

		// Auto-stamp tester / date
		if (row.result && row.result !== "Not Tested") {
			if (!row.tested_by)
				frappe.model.set_value(cdt, cdn, "tested_by", frappe.session.user);
			if (!row.test_date)
				frappe.model.set_value(cdt, cdn, "test_date", frappe.datetime.get_today());
		}

		// Feedback alerts
		const alerts = {
			"Pass":      { msg:`✅ Item #${row.item_number||""} — <b>Passed</b>`,                     ind:"green"  },
			"Fail":      { msg:`❌ Item #${row.item_number||""} — <b>Failed</b> — document exception`, ind:"red"    },
			"Exception": { msg:`⚠️ Item #${row.item_number||""} — <b>Exception</b> — add detail`,     ind:"orange" },
			"N/A":       { msg:`➖ Item #${row.item_number||""} — marked <b>N/A</b>`,                  ind:"blue"   },
		};
		if (alerts[row.result])
			frappe.show_alert({ message: alerts[row.result].msg, indicator: alerts[row.result].ind }, 4);

		// Re-render progress panel live
		frm.dirty();
		setTimeout(() => _progress(frm), 80);
	},
});


// ── Header ────────────────────────────────────────────────────────────────────
function _header(frm) {
	const st = frm.doc.status || "Not Started";
	const sc = {
		"Not Started":    { bg:"#f8f9fa", bd:"#bdc3c7", tc:"#7f8c8d", ic:"📋" },
		"In Progress":    { bg:"#f0f4ff", bd:"#3498db", tc:"#2980b9", ic:"⚙️"  },
		"Completed":      { bg:"#f0fdf4", bd:"#27ae60", tc:"#1e8449", ic:"✅"  },
		"Review Pending": { bg:"#fef9ec", bd:"#f39c12", tc:"#e67e22", ic:"🔍"  },
	}[st] || { bg:"#f8f9fa", bd:"#bdc3c7", tc:"#888", ic:"📋" };

	const or = frm.doc.overall_result;
	const or_c = { Satisfactory:"#27ae60", "Needs Improvement":"#e67e22", Unsatisfactory:"#e74c3c" }[or];
	const or_b = or
		? `<span style="background:${or_c};color:#fff;padding:3px 12px;border-radius:12px;font-size:12px;font-weight:600;">${or}</span>`
		: "";

	const code = frm.doc.transaction_code
		? `<code style="background:#2c3e50;color:#ecf0f1;padding:3px 8px;border-radius:4px;font-size:11px;">${frm.doc.transaction_code}</code>`
		: "";

	frm.dashboard.add_comment(`
		<div style="background:${sc.bg};border-left:5px solid ${sc.bd};border-radius:0 8px 8px 0;padding:12px 16px;">
			<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
				<span style="font-size:20px;">${sc.ic}</span>
				<span style="font-weight:700;font-size:14px;color:${sc.tc};">${st}</span>
				${or_b}${code}
				${frm.doc.doctype_name
					? `<span style="font-size:12px;color:#888;">📦 ${frm.doc.doctype_name}</span>` : ""}
			</div>
			<div style="margin-top:5px;font-size:12px;color:#aaa;">
				Period: <b>${frm.doc.from_date||"—"}</b> → <b>${frm.doc.to_date||"—"}</b>
				${frm.doc.assigned_to ? ` &nbsp;·&nbsp; 👤 ${frm.doc.assigned_to}` : ""}
				${frm.doc.reviewed_by ? ` &nbsp;·&nbsp; 🔍 ${frm.doc.reviewed_by}` : ""}
			</div>
		</div>`, "white", true);
}


// ── Progress Panel ────────────────────────────────────────────────────────────
function _progress(frm) {
	// Use server-computed fields when available, otherwise compute from child rows
	const items  = frm.doc.checklist_items || [];
	const total  = frm.doc.total_items  || items.length;
	const passed = frm.doc.items_passed || items.filter(i => i.result === "Pass").length;
	const failed = frm.doc.items_failed || items.filter(i => ["Fail","Exception"].includes(i.result)).length;
	const na     = items.filter(i => i.result === "N/A").length;
	const tested = frm.doc.items_tested || (passed + failed + na);
	const pct    = frm.doc.completion_percentage
	               || (total > 0 ? Math.round(tested / total * 100) : 0);

	if (!total) return;

	const remaining = total - tested;
	const pass_w  = total > 0 ? (passed  / total * 100).toFixed(1) : 0;
	const fail_w  = total > 0 ? (failed  / total * 100).toFixed(1) : 0;
	const na_w    = total > 0 ? (na      / total * 100).toFixed(1) : 0;
	const rem_w   = total > 0 ? (remaining / total * 100).toFixed(1) : 0;

	// Stacked bar segments
	const segs = [
		{ w: pass_w, c:"#27ae60", t:"Pass" },
		{ w: fail_w, c:"#e74c3c", t:"Fail/Exception" },
		{ w: na_w,   c:"#bdc3c7", t:"N/A" },
		{ w: rem_w,  c:"#ecf0f1", t:"Remaining" },
	].filter(s => parseFloat(s.w) > 0).map((s, i, arr) => {
		const radius = i === 0 && arr.length > 1 ? "6px 0 0 6px"
		             : i === arr.length - 1       ? "0 6px 6px 0"
		             : "0";
		return `<div title="${s.t}: ${s.w}%"
		             style="flex:${s.w};background:${s.c};height:12px;border-radius:${radius};"></div>`;
	}).join("");

	const stat_pills = [
		{ l:"✅ Passed",   n:passed,    c:"#27ae60" },
		{ l:"❌ Failed",   n:failed,    c:"#e74c3c" },
		{ l:"➖ N/A",      n:na,        c:"#95a5a6" },
		{ l:"⏳ Remaining",n:remaining, c:"#3498db" },
	].map(p => `<span style="font-size:12px;color:${p.c};">
		<b>${p.n}</b> ${p.l.replace(/^[^\s]+\s/,"")}
	</span>`).join("  ·  ");

	frm.dashboard.add_comment(`
		<div style="background:#f8f9fa;border-radius:8px;padding:12px 14px;">
			<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
				<span style="font-size:13px;font-weight:600;color:#2c3e50;">
					Testing Progress — ${tested}/${total} items
				</span>
				<span style="font-size:15px;font-weight:800;color:${pct===100?"#27ae60":failed>0?"#e74c3c":"#3498db"};">${pct}%</span>
			</div>
			<div style="display:flex;border-radius:6px;overflow:hidden;height:12px;background:#ecf0f1;margin-bottom:10px;">
				${segs}
			</div>
			<div style="display:flex;gap:12px;flex-wrap:wrap;">${stat_pills}</div>
		</div>`, "white", true);
}


// ── Buttons ───────────────────────────────────────────────────────────────────
function _buttons(frm) {
	if (frm.is_new()) return;

	// Navigation
	frm.add_custom_button("🔎 Findings", () =>
		frappe.set_route("List","Audit Finding",{
			audit_engagement: frm.doc.audit_engagement,
			reference_doctype: frm.doc.doctype_name,
		}), "View");
	frm.add_custom_button("📦 Samples", () =>
		frappe.set_route("List","Audit Sample",{
			audit_engagement: frm.doc.audit_engagement,
			reference_doctype: frm.doc.doctype_name,
		}), "View");

	const items    = frm.doc.checklist_items || [];
	const all_done = items.length && items.every(i => i.result !== "Not Tested");
	const none_done = !items.some(i => i.result !== "Not Tested");

	// Start Testing
	if (none_done && frm.doc.status === "Not Started")
		frm.add_custom_button("▶ Start Testing", () => {
			frappe.db.set_value("Audit Checklist", frm.doc.name, "status","In Progress")
			         .then(() => { frm.reload_doc();
			             frappe.show_alert({ message:"Testing started — work through each item below 🔍", indicator:"blue" }, 4);
			         });
		}, "Actions");

	// Mark Complete
	if (all_done && frm.doc.status !== "Completed" && frm.doc.status !== "Review Pending")
		frm.add_custom_button("✅ Mark Complete", () => {
			frappe.db.set_value("Audit Checklist", frm.doc.name, "status","Completed")
			         .then(() => { frm.reload_doc();
			             frappe.show_alert({ message:"Checklist complete! 🎉", indicator:"green" }, 4);
			         });
		}, "Actions");

	// Submit for Review
	if (frm.doc.status === "Completed" && !frm.doc.reviewed_by)
		frm.add_custom_button("🔍 Submit for Review", () =>
			frappe.db.set_value("Audit Checklist", frm.doc.name, "status","Review Pending")
			         .then(() => { frm.reload_doc();
			             frappe.show_alert({ message:"Submitted for review 🔍", indicator:"orange" }, 3);
			         }), "Actions");

	// Reviewer approve
	if (frm.doc.status === "Review Pending" && frappe.session.user !== frm.doc.assigned_to)
		frm.add_custom_button("✔ Approve Review", () => {
			frappe.db.set_value("Audit Checklist", frm.doc.name, {
				reviewed_by: frappe.session.user,
				status: "Completed",
			}).then(() => { frm.reload_doc();
			    frappe.show_alert({ message:"Checklist review approved ✔", indicator:"green" }, 4);
			});
		}, "Actions");
}