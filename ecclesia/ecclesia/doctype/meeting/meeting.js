// Copyright (c) 2026, Value Impacts Consulting
frappe.ui.form.on("Meeting", {
	refresh(frm) {
		add_roster_buttons(frm);
		add_notification_buttons(frm);
		add_status_indicator(frm);
	},

	meeting_category(frm) {
		if (frm.doc.meeting_category !== "Committee Meeting") {
			frm.set_value("committee", "");
		}
	},
});

function add_roster_buttons(frm) {
	if (frm.is_new()) return;

	if (frm.doc.meeting_category === "Board Meeting") {
		frm.add_custom_button(__("Load Board Members"), function () {
			frappe.call({
				method: "ecclesia.api.meeting_api.load_board_members",
				args: { meeting_name: frm.doc.name },
				freeze: true,
				freeze_message: __("Loading board members..."),
				callback: function (r) {
					if (r.message) {
						frappe.show_alert({ message: r.message.message, indicator: "green" });
						frm.reload_doc();
					}
				},
			});
		}, __("Attendance"));
	}

	if (frm.doc.meeting_category === "Committee Meeting") {
		frm.add_custom_button(__("Load Committee Members"), function () {
			if (!frm.doc.committee) {
				frappe.msgprint(__("Please set the Committee field first."));
				return;
			}
			frappe.call({
				method: "ecclesia.api.meeting_api.load_committee_members",
				args: { meeting_name: frm.doc.name },
				freeze: true,
				freeze_message: __("Loading committee members..."),
				callback: function (r) {
					if (r.message) {
						frappe.show_alert({ message: r.message.message, indicator: "green" });
						frm.reload_doc();
					}
				},
			});
		}, __("Attendance"));
	}
}

function add_notification_buttons(frm) {
	if (frm.is_new()) return;

	if (frm.doc.status !== "Minutes Approved" && frm.doc.status !== "Cancelled") {
		frm.add_custom_button(__("Send Meeting Notice"), function () {
			frappe.confirm(
				__("Send the meeting notice and agenda to everyone in the Notice Delivery Log?"),
				function () {
					frappe.call({
						method: "ecclesia.api.meeting_api.send_meeting_notice",
						args: { meeting_name: frm.doc.name },
						freeze: true,
						freeze_message: __("Sending notices..."),
						callback: function (r) {
							if (r.message) {
								frappe.show_alert({ message: r.message.message, indicator: "green" });
								frm.reload_doc();
							}
						},
					});
				}
			);
		}, __("Notify"));

		frm.add_custom_button(__("Send Reminder"), function () {
			frappe.call({
				method: "ecclesia.api.meeting_api.send_meeting_reminder",
				args: { meeting_name: frm.doc.name, reminder_type: "24_hour" },
				freeze: true,
				freeze_message: __("Sending reminders..."),
				callback: function (r) {
					if (r.message) {
						frappe.show_alert({ message: r.message.message, indicator: "green" });
					}
				},
			});
		}, __("Notify"));
	}

	if (frm.doc.status === "Minutes Approved") {
		frm.add_custom_button(__("Send Minutes Notification"), function () {
			frappe.call({
				method: "ecclesia.api.meeting_api.send_minutes_notification",
				args: { meeting_name: frm.doc.name },
				freeze: true,
				freeze_message: __("Sending minutes notification..."),
				callback: function (r) {
					if (r.message) {
						frappe.show_alert({ message: r.message.message, indicator: "green" });
					}
				},
			});
		}, __("Notify"));
	}

	if ((frm.doc.action_items || []).length) {
		frm.add_custom_button(__("Send Action Item Alerts"), function () {
			frappe.call({
				method: "ecclesia.api.meeting_api.send_action_item_alert",
				args: { meeting_name: frm.doc.name },
				freeze: true,
				freeze_message: __("Sending action item alerts..."),
				callback: function (r) {
					if (r.message) {
						frappe.show_alert({ message: r.message.message, indicator: "green" });
					}
				},
			});
		}, __("Notify"));
	}
}

function add_status_indicator(frm) {
	if (frm.is_new()) return;

	if (frm.doc.notice_compliant === 0 && frm.doc.notice_date) {
		frm.dashboard.add_indicator(__("Notice period below Meeting Type minimum"), "orange");
	}
	if (frm.doc.quorum_met === 0 && frm.doc.status === "Held") {
		frm.dashboard.add_indicator(__("Quorum not met"), "red");
	}
	if (frm.doc.open_action_items > 0) {
		frm.dashboard.add_indicator(
			__("{0} open action item(s)", [frm.doc.open_action_items]), "blue"
		);
	}
}
