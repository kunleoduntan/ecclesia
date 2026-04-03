// Copyright (c) 2026, Kunle Oduntan and contributors
// License: MIT

frappe.ui.form.on("Doctype Export", {

	// ── Lifecycle ────────────────────────────────────────────────────────

	refresh: function (frm) {
		frm.events.rebuild_buttons(frm);
	},

	module: function (frm) {
		if (!frm.doc.module || frm.is_new()) return;

		frappe.confirm(
			__("Populate the DocTypes table with all DocTypes from module <b>{0}</b>?", [frm.doc.module]),
			function () {
				frm.events.run_populate(frm);
			}
		);
	},

	// ── Button builder ───────────────────────────────────────────────────

	rebuild_buttons: function (frm) {
		if (frm.is_new()) return;

		// ── Primary: Download JSON ──────────────────────────────────────
		frm.add_custom_button(__("Download JSON"), function () {
			frm.events.run_download(frm);
		}).addClass("btn-primary");

		// ── Secondary: Validate ─────────────────────────────────────────
		frm.add_custom_button(__("Validate"), function () {
			frm.events.run_validate(frm);
		});

		// ── Secondary: Populate from Module (only when module is set) ───
		if (frm.doc.module) {
			frm.add_custom_button(__("Populate from Module"), function () {
				frm.events.run_populate(frm);
			});
		}
	},

	// ── Actions ──────────────────────────────────────────────────────────

	run_download: function (frm) {
        frappe.call({
            method: "ecclesia.ecclesia.doctype.doctype_export.doctype_export.get_doctype_fields_json",
            args: { docname: frm.doc.name },
            freeze: true,
            freeze_message: __("Building export…"),
            callback: function (r) {
                if (!r.message || r.message.status !== "ok") {
                    frappe.msgprint({
                        title: __("Export Failed"),
                        message: __("Server did not return a valid payload. Check the error log."),
                        indicator: "red",
                    });
                    return;
                }
    
                const result = r.message;
    
                // ── Decode payload based on mode ────────────────────────────
                let blob;
                if (result.mode === "zip") {
                    // base64-encoded ZIP
                    const binary = atob(result.data);
                    const bytes  = new Uint8Array(binary.length);
                    for (let i = 0; i < binary.length; i++) {
                        bytes[i] = binary.charCodeAt(i);
                    }
                    blob = new Blob([bytes], { type: "application/zip" });
                } else {
                    blob = new Blob([result.data], { type: "application/json;charset=utf-8;" });
                }
    
                // ── Trigger browser download ────────────────────────────────
                const url  = URL.createObjectURL(blob);
                const link = document.createElement("a");
                link.href          = url;
                link.download      = result.filename;
                link.style.display = "none";
                document.body.appendChild(link);
                link.click();
                setTimeout(function () {
                    document.body.removeChild(link);
                    URL.revokeObjectURL(url);
                }, 500);
    
                // ── Summary alert ───────────────────────────────────────────
                const summary  = result.summary || {};
                const exported = (summary.exported || []).length;
                const failed   = summary.failed   || [];
    
                if (failed.length) {
                    frappe.msgprint({
                        title: __("Export Completed with Warnings"),
                        message: (
                            "<b>" + exported + " DocType(s) exported successfully.</b>" +
                            "<br><br>Failed:<ul style='color:var(--red);'>" +
                            failed.map(function (f) { return "<li>" + f + "</li>"; }).join("") +
                            "</ul>"
                        ),
                        indicator: "orange",
                    });
                } else {
                    frappe.show_alert({
                        message: __("Downloaded {0} — {1} DocType(s)", [result.filename, exported]),
                        indicator: "green",
                    });
                }
            },
        });
    },
    
	run_validate: function (frm) {
		frappe.call({
			method: "ecclesia.ecclesia.doctype.doctype_export.doctype_export.validate_export",
			args: { docname: frm.doc.name },
			freeze: true,
			freeze_message: __("Validating…"),
			callback: function (r) {
				if (!r.message) return;

				const msg = r.message;
				if (msg.valid) {
					frappe.show_alert({ message: msg.message, indicator: "green" });
				} else {
					frappe.msgprint({
						title: __("Validation Failed"),
						message: msg.message +
							(msg.missing
								? "<br><br><b>Missing:</b><ul><li>" +
								  msg.missing.join("</li><li>") +
								  "</li></ul>"
								: ""),
						indicator: "red",
					});
				}
			},
		});
	},
    	run_download: function (frm) {
        frappe.call({
            method: "ecclesia.ecclesia.doctype.doctype_export.doctype_export.get_doctype_fields_json",
            args: { docname: frm.doc.name },
            freeze: true,
            freeze_message: __("Building export…"),
            callback: function (r) {
                if (!r.message || r.message.status !== "ok") {
                    frappe.msgprint({
                        title: __("Export Failed"),
                        message: __("Server did not return a valid payload. Check the error log."),
                        indicator: "red",
                    });
                    return;
                }
    
                const result = r.message;
    
                // ── Decode payload based on mode ────────────────────────────
                let blob;
                if (result.mode === "zip") {
                    // base64-encoded ZIP
                    const binary = atob(result.data);
                    const bytes  = new Uint8Array(binary.length);
                    for (let i = 0; i < binary.length; i++) {
                        bytes[i] = binary.charCodeAt(i);
                    }
                    blob = new Blob([bytes], { type: "application/zip" });
                } else {
                    blob = new Blob([result.data], { type: "application/json;charset=utf-8;" });
                }
    
                // ── Trigger browser download ────────────────────────────────
                const url  = URL.createObjectURL(blob);
                const link = document.createElement("a");
                link.href          = url;
                link.download      = result.filename;
                link.style.display = "none";
                document.body.appendChild(link);
                link.click();
                setTimeout(function () {
                    document.body.removeChild(link);
                    URL.revokeObjectURL(url);
                }, 500);
    
                // ── Summary alert ───────────────────────────────────────────
                const summary  = result.summary || {};
                const exported = (summary.exported || []).length;
                const failed   = summary.failed   || [];
    
                if (failed.length) {
                    frappe.msgprint({
                        title: __("Export Completed with Warnings"),
                        message: (
                            "<b>" + exported + " DocType(s) exported successfully.</b>" +
                            "<br><br>Failed:<ul style='color:var(--red);'>" +
                            failed.map(function (f) { return "<li>" + f + "</li>"; }).join("") +
                            "</ul>"
                        ),
                        indicator: "orange",
                    });
                } else {
                    frappe.show_alert({
                        message: __("Downloaded {0} — {1} DocType(s)", [result.filename, exported]),
                        indicator: "green",
                    });
                }
            },
        });
    },

	run_populate: function (frm) {
		frappe.call({
			method: "ecclesia.ecclesia.doctype.doctype_export.doctype_export.populate_from_module",
			args: { docname: frm.doc.name },
			freeze: true,
			freeze_message: __("Fetching DocTypes from module…"),
			callback: function (r) {
				if (r.message && r.message.status === "ok") {
					frappe.show_alert({ message: r.message.message, indicator: "green" });
					frm.reload_doc();
				}
			},
		});
	},
});