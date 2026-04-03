// Copyright (c) 2026, kunle Oduntan and contributors
//For license information, please see license.txt

// ╔══════════════════════════════════════════════════════════════════════╗
// ║  AUDIT SCOPE DOCTYPE  (child table)  ·  Ecclesia                     ║
// ╚══════════════════════════════════════════════════════════════════════╝

frappe.ui.form.on("Audit Scope DocType", {

	doctype_name(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.doctype_name) return;

		frappe.db.get_value(
			"Auditable DocType Registry",
			{ doctype_name: row.doctype_name },
			[
				"transaction_code", "risk_level", "sampling_method",
				"is_gl_posting", "is_active", "open_findings_count",
				"last_audit_date", "total_transactions_ytd",
				"recommended_sample_size", "audit_frequency",
			],
			val => {
				if (!val || !val.transaction_code) {
					// Not registered — clear the row and warn
					frappe.model.set_value(cdt, cdn, "doctype_name", "");
					frappe.msgprint({
						title:   "DocType Not Registered",
						message: `<b>${row.doctype_name}</b> is not in the Audit Universe yet.
						          <br><br>Go to <b>Auditable DocType Registry → New</b>, paste the
						          DocType's JSON, and Save. The system will register it automatically.`,
						indicator: "orange",
					});
					return;
				}

				if (!val.is_active) {
					frappe.show_alert({
						message: `⚠️ <b>${row.doctype_name}</b> is registered but marked <b>Inactive</b>.`,
						indicator: "orange",
					}, 6);
				}

				// Auto-populate scope row from registry
				frappe.model.set_value(cdt, cdn, "transaction_code", val.transaction_code);
				frappe.model.set_value(cdt, cdn, "risk_level",        val.risk_level);
				frappe.model.set_value(cdt, cdn, "sampling_method",   val.sampling_method);

				// Rich info alert
				const risk_icons = { Critical:"🔴", High:"🟠", Medium:"🟡", Low:"🟢" };
				const icon       = risk_icons[val.risk_level] || "📌";
				const gl_tag     = val.is_gl_posting ? " · 💳 GL-posting" : "";
				const last_tag   = val.last_audit_date
					? ` · Last audit: <b>${val.last_audit_date}</b>`
					: " · <b style='color:#e67e22;'>⚠️ Never audited</b>";
				const open_tag   = val.open_findings_count
					? ` · <span style="color:#e74c3c;">${val.open_findings_count} open finding(s)</span>`
					: "";
				const txn_tag    = val.total_transactions_ytd
					? ` · ${val.total_transactions_ytd.toLocaleString()} txns YTD` : "";

				frappe.show_alert({
					message: `${icon} <b>${row.doctype_name}</b> added — ${val.risk_level} risk${gl_tag}${last_tag}${open_tag}${txn_tag}`,
					indicator: val.risk_level === "Critical" ? "red"
					         : val.risk_level === "High"     ? "orange" : "blue",
				}, 7);
			}
		);
	},
});