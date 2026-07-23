// Copyright (c) 2026, Value Impacts Consulting
frappe.ui.form.on("Executive Task", {
	refresh(frm) {
		if (frm.is_new()) return;

		if (frm.doc.status !== "Completed" && frm.doc.status !== "Cancelled") {
			frm.add_custom_button(__("Mark Completed"), function () {
				frappe.prompt(
					{ fieldname: "notes", label: __("Completion Notes"), fieldtype: "Small Text" },
					function (values) {
						frm.set_value("status", "Completed");
						frm.set_value("completion_notes", values.notes);
						frm.save();
					},
					__("Complete Task")
				);
			}, __("Actions"));
		}

		if (frm.doc.due_date && ["Open", "In Progress"].includes(frm.doc.status)) {
			const overdue = frappe.datetime.get_diff(frappe.datetime.get_today(), frm.doc.due_date) > 0;
			if (overdue) {
				frm.dashboard.add_indicator(__("Overdue"), "red");
			}
		}
		if (frm.doc.escalated) {
			frm.dashboard.add_indicator(__("Escalated"), "orange");
		}
	},
});
