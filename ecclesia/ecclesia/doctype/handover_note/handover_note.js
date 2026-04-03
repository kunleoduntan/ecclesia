// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

frappe.ui.form.on("Handover Note", {

    refresh(frm) {
        frm.trigger("set_status_color");
        frm.trigger("add_action_buttons");
        frm.trigger("render_task_summary");
    },

    set_status_color(frm) {
        const colors = {
            "Draft":          "gray",
            "Pending Approval": "orange",
            "Approved":       "blue",
            "Active":         "green",
            "Return Pending": "orange",
            "Closed":         "darkgrey",
            "Rejected":       "red",
        };
        frm.page.set_indicator(frm.doc.status, colors[frm.doc.status] || "gray");
    },

    add_action_buttons(frm) {
        if (frm.is_new() || frm.doc.docstatus === 2) return;

        // Supervisor: approve / reject
        if (
            frm.doc.status === "Pending Approval" &&
            frappe.session.user === frappe.db.get_value("Employee", frm.doc.supervisor, "user_id")
        ) {
            frm.add_custom_button("Approve", () => {
                frappe.confirm(
                    "Approve this Handover Note? The leave application will be cleared for approval.",
                    () => {
                        frappe.db.set_value("Handover Note", frm.doc.name, "status", "Approved")
                            .then(() => frm.reload_doc());
                    }
                );
            }, "Actions").addClass("btn-success");

            frm.add_custom_button("Reject", () => {
                frappe.prompt(
                    { label: "Rejection Reason", fieldtype: "Small Text", reqd: 1 },
                    ({ value }) => {
                        frappe.db.set_value("Handover Note", frm.doc.name, {
                            status: "Rejected",
                            rejection_reason: value
                        }).then(() => frm.reload_doc());
                    },
                    "Reject Handover Note"
                );
            }, "Actions");
        }

        // Employee: process return
        if (frm.doc.status === "Active" && frm.doc.docstatus === 1) {
            frm.add_custom_button("Process My Return", () => {
                frappe.confirm(
                    "Confirm that you have returned from leave? Acting officer notifications will be sent.",
                    () => frm.call("process_return").then(({ message }) => {
                        frappe.msgprint(
                            `Return processed. ${message.open_task_count} task(s) need your review.`,
                            "Return Processed"
                        );
                        frm.reload_doc();
                    })
                );
            }, "Actions").addClass("btn-primary");
        }

        // Employee: close handover
        if (frm.doc.status === "Return Pending") {
            frm.add_custom_button("Close Handover", () => {
                frappe.confirm(
                    "Close this handover? Ensure all critical tasks are resolved or deferred.",
                    () => frm.call("close_handover").then(() => frm.reload_doc())
                );
            }, "Actions").addClass("btn-primary");
        }

        // HR: manual delegation controls
        if (
            frm.doc.delegations?.length &&
            frappe.user.has_role(["HR Manager", "System Manager"])
        ) {
            frm.add_custom_button("Activate Delegations", () => {
                frm.call("activate_delegations").then(() => {
                    frappe.msgprint("Delegations activated.", "Done");
                    frm.reload_doc();
                });
            }, "Delegations");

            frm.add_custom_button("Revoke Delegations", () => {
                frappe.confirm(
                    "Revoke all active delegations for this handover?",
                    () => frm.call("revoke_delegations").then(() => frm.reload_doc())
                );
            }, "Delegations");
        }
    },

    render_task_summary(frm) {
        if (!frm.doc.tasks?.length) return;

        const counts = frm.doc.tasks.reduce((acc, t) => {
            acc[t.status] = (acc[t.status] || 0) + 1;
            return acc;
        }, {});

        const total     = frm.doc.tasks.length;
        const completed = counts["Completed"] || 0;
        const pct       = Math.round((completed / total) * 100);
        const color     = pct === 100 ? "green" : completed > 0 ? "orange" : "gray";

        frm.dashboard.add_indicator(`Tasks: ${completed}/${total} completed (${pct}%)`, color);

        if (counts["Escalated"]) {
            frm.dashboard.add_indicator(`${counts["Escalated"]} escalated`, "red");
        }
        if (counts["Critical"]) {
            const critOpen = frm.doc.tasks.filter(
                t => t.priority === "Critical" && t.status !== "Completed"
            ).length;
            if (critOpen) frm.dashboard.add_indicator(`${critOpen} critical open`, "red");
        }
    },

    leave_application(frm) {
        if (!frm.doc.leave_application) return;
        frappe.db.get_value(
            "Leave Application",
            frm.doc.leave_application,
            ["from_date", "to_date", "employee", "leave_type"]
        ).then(({ message }) => {
            if (!message) return;
            if (message.employee !== frm.doc.employee) {
                frappe.msgprint("This leave application does not belong to the selected employee.");
                frm.set_value("leave_application", "");
                return;
            }
            frm.set_value("leave_from", message.from_date);
            frm.set_value("leave_to",   message.to_date);
        });
    },

    default_acting_officer(frm) {
        // Auto-fill acting officer on any tasks that have none
        frm.doc.tasks.forEach((task, idx) => {
            if (!task.acting_officer) {
                frappe.model.set_value(task.doctype, task.name,
                    "acting_officer", frm.doc.default_acting_officer);
            }
        });
        frm.refresh_field("tasks");
    }
});


// Child table: Handover Task
frappe.ui.form.on("Handover Task", {
    status(frm, cdt, cdn) {
        frm.trigger("render_task_summary");
    }
});