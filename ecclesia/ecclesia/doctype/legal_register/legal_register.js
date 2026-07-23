// Copyright (c) 2026, Value Impacts Consulting
frappe.ui.form.on("Legal Register", {
	refresh(frm) {
		if (frm.is_new()) return;

		if (!["Renewed"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Record Renewal"), function () {
				frappe.prompt(
					[
						{ fieldname: "renewal_date", label: __("Renewal Date"), fieldtype: "Date",
						  reqd: 1, default: frappe.datetime.get_today() },
						{ fieldname: "new_expiry_date", label: __("New Expiry Date"), fieldtype: "Date", reqd: 1 },
						{ fieldname: "renewed_by", label: __("Renewed By"), fieldtype: "Link", options: "Employee" },
						{ fieldname: "cost", label: __("Renewal Cost (₦)"), fieldtype: "Currency" },
					],
					function (values) {
						frappe.call({
							method: "ecclesia.api.documents_api.record_legal_register_renewal",
							args: {
								legal_register_name: frm.doc.name,
								renewal_date: values.renewal_date,
								new_expiry_date: values.new_expiry_date,
								renewed_by: values.renewed_by,
								cost: values.cost,
							},
							freeze: true,
							freeze_message: __("Recording renewal..."),
							callback: function (r) {
								if (r.message) {
									frappe.show_alert({ message: r.message.message, indicator: "green" });
									frm.reload_doc();
								}
							},
						});
					},
					__("Record Renewal"),
					__("Save")
				);
			}, __("Actions"));
		}

		if (frm.doc.is_expiring_soon || frm.doc.is_expired) {
			frm.add_custom_button(__("Send Expiry Alert"), function () {
				frappe.call({
					method: "ecclesia.api.documents_api.send_expiry_alert",
					args: { doctype_name: frm.doc.name, doctype: "Legal Register" },
					freeze: true,
					callback: function (r) {
						if (r.message) {
							frappe.show_alert({ message: r.message.message, indicator: "orange" });
						}
					},
				});
			}, __("Actions"));
		}

		if (frm.doc.is_expired) {
			frm.dashboard.add_indicator(__("Expired"), "red");
		} else if (frm.doc.is_expiring_soon) {
			frm.dashboard.add_indicator(__("Expiring Soon"), "orange");
		}
		if (frm.doc.compliance_status === "Non-Compliant") {
			frm.dashboard.add_indicator(__("Non-Compliant"), "red");
		}
	},
});
