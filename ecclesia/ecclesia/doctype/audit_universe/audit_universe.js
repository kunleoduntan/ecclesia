// Copyright (c) 2026, kunle Oduntan and contributors
// For license information, please see license.txt

// Audit Universe — Client Script

frappe.ui.form.on("Audit Universe", {

    refresh(frm) {
        const risk_colors = { Critical: "red", High: "orange", Medium: "yellow", Low: "green" };
        if (frm.doc.risk_level) {
            frm.page.set_indicator(frm.doc.risk_level, risk_colors[frm.doc.risk_level] || "grey");
        }

        if (!frm.is_new()) {
            // Open registry record
            if (frm.doc.registry_ref) {
                frm.add_custom_button(__("Open Registry"), function () {
                    frappe.set_route("Form", "Auditable DocType Registry", frm.doc.registry_ref);
                }, __("View"));
            }

            // View all findings for this DocType
            frm.add_custom_button(__("View Findings"), function () {
                frappe.set_route("List", "Audit Finding", {
                    reference_doctype: frm.doc.doctype_name
                });
            }, __("View"));

            // View risk dashboard
            frm.add_custom_button(__("Risk Dashboard"), function () {
                frappe.set_route("audit-dashboard");
            }, __("View"));

            // Sync universe
            frm.add_custom_button(__("Sync All"), function () {
                frappe.call({
                    method: "ecclesia.doctype.audit_universe.audit_universe.sync_audit_universe_from_ui",
                    freeze: true,
                    freeze_message: "Syncing Audit Universe...",
                    callback(r) {
                        frm.reload_doc();
                        frappe.show_alert({ message: r.message, indicator: "green" });
                    }
                });
            }, __("Actions"));

            // Risk score badge
            if (frm.doc.risk_score) {
                const score = frm.doc.risk_score;
                const score_color = score >= 70 ? "#c0392b" : score >= 40 ? "#e67e22" : "#27ae60";
                frm.dashboard.set_headline_alert(
                    `<span>AI Risk Score: <b style="color:${score_color}; font-size:16px;">${score}/100</b>
                     &nbsp;|&nbsp; Code: <b>${frm.doc.transaction_code || "—"}</b>
                     &nbsp;|&nbsp; ${frm.doc.is_gl_posting ? "🔗 GL-posting" : "No GL"}</span>`
                );
            }
        }
    }
});