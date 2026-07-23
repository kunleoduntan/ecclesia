// Copyright (c) 2026, Value Impacts Consulting
frappe.ui.form.on("Corporate Document", {
	refresh(frm) {
		if (frm.is_new()) return;

		if (frm.doc.confidential) {
			frm.dashboard.add_indicator(__("Confidential"), "red");
		}
		if (frm.doc.is_expiring_soon) {
			frm.dashboard.add_indicator(__("Expiring Soon"), "orange");

			frm.add_custom_button(__("Send Expiry Alert"), function () {
				frappe.call({
					method: "ecclesia.api.documents_api.send_expiry_alert",
					args: { doctype_name: frm.doc.name, doctype: "Corporate Document" },
					freeze: true,
					callback: function (r) {
						if (r.message) {
							frappe.show_alert({ message: r.message.message, indicator: "orange" });
						}
					},
				});
			}, __("Actions"));
		}
		if (frm.doc.status === "Expired") {
			frm.dashboard.add_indicator(__("Expired"), "red");
		}
	},
});
