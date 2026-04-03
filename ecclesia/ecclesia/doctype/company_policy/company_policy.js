// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

frappe.ui.form.on("Company Policy", {

    refresh(frm) {
        frm.trigger("set_status_indicator");
        frm.trigger("add_custom_buttons");
        frm.trigger("render_ack_summary");
    },

    set_status_indicator(frm) {
        const colors = {
            "Draft":        "gray",
            "Under Review": "orange",
            "Approved":     "blue",
            "Published":    "green",
            "Superseded":   "darkgrey",
            "Retired":      "red",
        };
        frm.page.set_indicator(frm.doc.status, colors[frm.doc.status] || "gray");
    },

    add_custom_buttons(frm) {
        if (frm.doc.status === "Draft" && !frm.is_new()) {
            frm.add_custom_button("Submit for Review", () => {
                frappe.confirm(
                    "Submit this policy for review?",
                    () => frm.set_value("status", "Under Review").then(() => frm.save())
                );
            }, "Actions");
        }

        if (frm.doc.status === "Approved" && frappe.user.has_role(["System Manager", "HR Manager"])) {
            frm.add_custom_button("Publish & Distribute", () => {
                frappe.confirm(
                    `Publish Version ${frm.doc.version} and send acknowledgement requests to all scoped employees?`,
                    () => frm.call("publish_new_version").then(() => frm.reload_doc())
                );
            }, "Actions").addClass("btn-primary");
        }

        if (frm.doc.status === "Published") {
            frm.add_custom_button("View Acknowledgement Status", () => {
                frappe.set_route("List", "Policy Acknowledgement", {
                    policy: frm.doc.name,
                    policy_version: frm.doc.version
                });
            }, "Reports");

            frm.add_custom_button("Export Ack Report", () => {
                const url = `/api/method/your_app.api.export_ack_report?policy=${frm.doc.name}`;
                window.open(url);
            }, "Reports");
        }
    },

    render_ack_summary(frm) {
        if (frm.doc.status !== "Published" || frm.is_new()) return;

        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Policy Acknowledgement",
                filters: { policy: frm.doc.name, policy_version: frm.doc.version },
                fields: ["status"],
                limit_page_length: 0
            },
            callback({ message }) {
                if (!message?.length) return;
                const total      = message.length;
                const acked      = message.filter(r => r.status === "Acknowledged").length;
                const pct        = Math.round((acked / total) * 100);
                const color      = pct === 100 ? "green" : pct >= 60 ? "orange" : "red";

                frm.dashboard.add_indicator(
                    `Acknowledged: ${acked}/${total} (${pct}%)`, color
                );

                // Progress bar in the form
                frm.fields_dict.content.$wrapper.before(`
                    <div style="margin:12px 0 20px;padding:12px 16px;background:var(--bg-color);
                                border:1px solid var(--border-color);border-radius:8px">
                        <div style="display:flex;justify-content:space-between;
                                    font-size:13px;margin-bottom:6px">
                            <span style="color:var(--text-muted)">Acknowledgement progress</span>
                            <span style="font-weight:500;color:var(--text-color)">${acked}/${total}</span>
                        </div>
                        <div style="height:6px;background:var(--border-color);border-radius:3px">
                            <div style="height:6px;width:${pct}%;background:var(--${color}-indicator-color);
                                        border-radius:3px;transition:width .4s"></div>
                        </div>
                    </div>
                `);
            }
        });
    },

    applicable_to(frm) {
        if (frm.doc.applicable_to === "All Employees") {
            frm.clear_table("scope");
            frm.refresh_field("scope");
        }
    }
});