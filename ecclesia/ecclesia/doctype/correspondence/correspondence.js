// Copyright (c) 2026, Value Impacts Consulting
frappe.ui.form.on("Correspondence", {
	refresh(frm) {
		add_routing_button(frm);
		add_acknowledgement_button(frm);
		add_overdue_button(frm);
		add_status_indicators(frm);
	},

	correspondence_category(frm) {
		frm.set_value("_priority_manually_set", 0);
	},

	priority(frm) {
		frm.doc._priority_manually_set = 1;
	},
});

function add_routing_button(frm) {
	if (frm.is_new()) return;
	if (["Closed", "Responded", "Dispatched"].includes(frm.doc.status)) return;

	frm.add_custom_button(__("Route To..."), function () {
		frappe.prompt(
			[
				{
					fieldname: "employee",
					label: __("Route To (Employee)"),
					fieldtype: "Link",
					options: "Employee",
					reqd: 1,
				},
				{
					fieldname: "instruction",
					label: __("Instruction"),
					fieldtype: "Small Text",
				},
			],
			function (values) {
				frappe.call({
					method: "ecclesia.api.correspondence_api.route_correspondence",
					args: {
						correspondence_name: frm.doc.name,
						employee: values.employee,
						instruction: values.instruction,
					},
					freeze: true,
					freeze_message: __("Routing..."),
					callback: function (r) {
						if (r.message) {
							frappe.show_alert({ message: r.message.message, indicator: "green" });
							frm.reload_doc();
						}
					},
				});
			},
			__("Route Correspondence"),
			__("Route")
		);
	}, __("Actions"));
}

function add_acknowledgement_button(frm) {
	if (frm.is_new()) return;
	if (frm.doc.correspondence_type !== "Incoming Mail") return;

	frm.add_custom_button(__("Send Acknowledgement"), function () {
		frappe.call({
			method: "ecclesia.api.correspondence_api.send_acknowledgement_receipt",
			args: { correspondence_name: frm.doc.name },
			freeze: true,
			freeze_message: __("Sending acknowledgement..."),
			callback: function (r) {
				if (r.message) {
					frappe.show_alert({ message: r.message.message, indicator: "green" });
					frm.reload_doc();
				}
			},
		});
	}, __("Actions"));
}

function add_overdue_button(frm) {
	if (frm.is_new()) return;
	if (!frm.doc.is_overdue && frm.doc.response_status !== "Overdue") return;

	frm.add_custom_button(__("Send Overdue Alert"), function () {
		frappe.call({
			method: "ecclesia.api.correspondence_api.send_response_overdue_alert",
			args: { correspondence_name: frm.doc.name },
			freeze: true,
			callback: function (r) {
				if (r.message) {
					frappe.show_alert({ message: r.message.message, indicator: "orange" });
				}
			},
		});
	}, __("Actions"));
}

function add_status_indicators(frm) {
	if (frm.is_new()) return;

	if (frm.doc.confidential) {
		frm.dashboard.add_indicator(__("Confidential"), "red");
	}
	if (frm.doc.is_overdue) {
		frm.dashboard.add_indicator(__("Overdue"), "red");
	}
	if (frm.doc.response_status === "Pending") {
		frm.dashboard.add_indicator(__("Response Pending"), "orange");
	}
	if (frm.doc.priority === "Urgent") {
		frm.dashboard.add_indicator(__("Urgent"), "red");
	}
}
