// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bulk Creator", {
	refresh(frm) {
		frm.add_custom_button(__("Create DocTypes"), () => {
			if (!frm.doc.json_input || !frm.doc.json_input.trim()) {
				frappe.msgprint(__("Paste DocType JSON into the JSON field first."));
				return;
			}

			frm.save().then(() => {
				frappe.call({
					method: "ecclesia.ecclesia.doctype.bulk_creator.bulk_creator.create_doctypes_from_json",
					args: { name: frm.doc.name },
					freeze: true,
					freeze_message: __("Creating DocTypes…"),
					callback(r) {
						if (!r.message) return;

						const { created, skipped, failed } = r.message;
						let msg = "";

						if (created.length) {
							msg += `<b>${__("Created")}:</b> ${created.join(", ")}<br>`;
						}
						if (skipped.length) {
							msg += `<b>${__("Already existed")}:</b> ${skipped.join(", ")}<br>`;
						}
						if (failed.length) {
							msg += `<b>${__("Failed")}:</b><br>`;
							failed.forEach(([n, err]) => {
								msg += `&nbsp;&nbsp;${n}: ${frappe.utils.escape_html(err)}<br>`;
							});
						}

						frappe.msgprint({
							title: __("Bulk Creator Result"),
							message: msg || __("Nothing to do."),
							indicator: failed.length ? "orange" : "green",
						});

						frm.reload_doc();
					},
				});
			});
		}).addClass("btn-primary");
	},
});