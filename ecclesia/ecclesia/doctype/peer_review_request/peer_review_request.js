// ecclesia/doctype/peer_review_request/peer_review_request.js
frappe.ui.form.on("Peer Review Request", {

    refresh(frm) {
        frm.trigger("_status_badge");
        if (frm.doc.docstatus === 1) {
            frm.trigger("_show_progress");
            frm.add_custom_button(__("Send Reminder"), () => {
                frm.trigger("_send_reminders");
            }, __("Actions"));
        }
    },

    _status_badge(frm) {
        const completed = (frm.doc.peers || []).filter(r => r.status === "Completed").length;
        const total = (frm.doc.peers || []).length;
        if (total) {
            frm.set_intro(
                __("{0} of {1} peers have submitted their review.", [completed, total]),
                completed === total ? "green" : "blue"
            );
        }
    },

    _show_progress(frm) {
        const peers = frm.doc.peers || [];
        const done = peers.filter(r => r.status === "Completed").length;
        frm.dashboard.add_progress(__("Review Completion"), (done / Math.max(1, peers.length)) * 100);
    },

    _send_reminders(frm) {
        frappe.confirm(__("Send reminder emails to all pending peer reviewers?"), () => {
            frappe.call({
                method: "ecclesia.api.recruitment_auto_screen.send_peer_review_reminders",
                args: { request_name: frm.doc.name },
                callback(r) {
                    frappe.show_alert({ message: __("Reminders sent!"), indicator: "green" });
                }
            });
        });
    },

    reviewee(frm) {
        if (frm.doc.reviewee) {
            // Auto-suggest direct reports and same-department colleagues
            frappe.db.get_value("Employee", frm.doc.reviewee, ["department", "employee_name"])
                .then(r => {
                    if (r?.message?.employee_name) {
                        frm.set_intro(__("Requesting reviews for: {0}", [r.message.employee_name]));
                    }
                });
        }
    }
});

frappe.ui.form.on("Peer Review Request Peer", {
    peer(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.peer === frm.doc.reviewee) {
            frappe.model.set_value(cdt, cdn, "peer", "");
            frappe.show_alert({ message: __("An employee cannot review themselves."), indicator: "red" });
        }
    }
});
