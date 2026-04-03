// Copyright (c) 2026, kunle Oduntan and contributors
// For license information, please see license.txt

frappe.ui.form.on("Telephone Call Log", {

    // ─── On Refresh ────────────────────────────────────────────────────────
    refresh(frm) {
        frm.trigger("set_status_color");
        frm.trigger("add_call_log_actions");
        frm.trigger("render_duration_badge");

        // Make call_notes editable during an active call
        const active = ["Initiated", "Ringing", "Answered"].includes(frm.doc.status);
        frm.set_df_property("call_notes", "read_only", active ? 0 : 0);
    },

    // ─── Status Colour ─────────────────────────────────────────────────────
    set_status_color(frm) {
        const color_map = {
            "Answered":  "green",
            "Missed":    "gray",
            "Failed":    "red",
            "Busy":      "orange",
            "Declined":  "gray",
            "Initiated": "blue",
            "Ringing":   "yellow",
        };
        const color = color_map[frm.doc.status] || "blue";
        frm.page.set_indicator(frm.doc.status, color);
    },

    // ─── Duration Badge ────────────────────────────────────────────────────
    render_duration_badge(frm) {
        if (frm.doc.duration_formatted) {
            frm.set_intro(
                `⏱ Call Duration: <strong>${frm.doc.duration_formatted}</strong>`,
                frm.doc.status === "Answered" ? "green" : "gray"
            );
        }
    },

    // ─── Action Buttons ────────────────────────────────────────────────────
    add_call_log_actions(frm) {
        // Open linked CRM record
        const crm_links = [
            { label: "Open Lead",        field: "lead",        doctype: "Lead"        },
            { label: "Open Contact",     field: "contact",     doctype: "Contact"     },
            { label: "Open Customer",    field: "customer",    doctype: "Customer"    },
            { label: "Open Opportunity", field: "opportunity", doctype: "Opportunity" },
            { label: "Open Employee",    field: "employee",    doctype: "Employee"    },
        ];

        crm_links.forEach(({ label, field, doctype }) => {
            if (frm.doc[field]) {
                frm.add_custom_button(__(label), () => {
                    frappe.set_route("Form", doctype, frm.doc[field]);
                }, __("Open Record"));
            }
        });

        // Play recording
        if (frm.doc.recording_url) {
            frm.add_custom_button(__("▶ Play Recording"), () => {
                ecclesia_telephone.play_recording(frm.doc.recording_url);
            }, __("Recording"));
        }

        // Schedule follow-up
        if (!frm.doc.follow_up_date) {
            frm.add_custom_button(__("Schedule Follow-up"), () => {
                frappe.prompt(
                    [
                        { fieldname: "follow_up_date", fieldtype: "Date",       label: "Date",  reqd: 1 },
                        { fieldname: "follow_up_note", fieldtype: "Small Text", label: "Note"           },
                    ],
                    ({ follow_up_date, follow_up_note }) => {
                        frm.set_value("follow_up_date", follow_up_date);
                        frm.set_value("follow_up_note", follow_up_note);
                        frm.save();
                    },
                    __("Schedule Follow-up"),
                    __("Save")
                );
            });
        }
    },

    // ─── Follow-up Alert ───────────────────────────────────────────────────
    follow_up_date(frm) {
        if (frm.doc.follow_up_date) {
            const today = frappe.datetime.get_today();
            if (frm.doc.follow_up_date <= today) {
                frm.set_df_property(
                    "follow_up_date", "description",
                    "⚠️ This follow-up is due today or overdue."
                );
            }
        }
    },
});
