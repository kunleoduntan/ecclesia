// Copyright (c) 2026, Value Impacts Consulting
frappe.ui.form.on("Executive Communication", {
	refresh(frm) {
		if (frm.is_new()) return;

		if (frm.doc.docstatus === 0 && frm.doc.audience_type !== "Specific Employees") {
			frm.add_custom_button(__("Load Recipients"), function () {
				frappe.call({
					method: "ecclesia.api.executive_api.load_recipients",
					args: { communication_name: frm.doc.name },
					freeze: true,
					freeze_message: __("Loading recipients..."),
					callback: function (r) {
						if (r.message) {
							frappe.show_alert({ message: r.message.message, indicator: "green" });
							frm.reload_doc();
						}
					},
				});
			}, __("Actions"));
		}

		if (frm.doc.docstatus === 1 && (frm.doc.recipients || []).some((r) => !r.sent_date)) {
			frm.add_custom_button(__("Dispatch"), function () {
				frappe.confirm(
					__("Send this communication to all pending recipients?"),
					function () {
						frappe.call({
							method: "ecclesia.api.executive_api.dispatch_communication",
							args: { communication_name: frm.doc.name },
							freeze: true,
							freeze_message: __("Dispatching..."),
							callback: function (r) {
								if (r.message) {
									frappe.show_alert({ message: r.message.message, indicator: "green" });
									frm.reload_doc();
								}
							},
						});
					}
				);
			}, __("Actions"));
		}

		if (frm.doc.requires_acknowledgement && frm.doc.status === "Sent"
			&& (frm.doc.total_acknowledged || 0) < (frm.doc.total_recipients || 0)) {
			frm.add_custom_button(__("Send Acknowledgement Reminder"), function () {
				frappe.call({
					method: "ecclesia.api.executive_api.send_acknowledgement_reminder",
					args: { communication_name: frm.doc.name },
					freeze: true,
					callback: function (r) {
						if (r.message) {
							frappe.show_alert({ message: r.message.message, indicator: "orange" });
						}
					},
				});
			}, __("Actions"));

			frm.dashboard.add_indicator(
				__("{0}/{1} acknowledged", [frm.doc.total_acknowledged || 0, frm.doc.total_recipients || 0]),
				"orange"
			);
		}
	},
});
