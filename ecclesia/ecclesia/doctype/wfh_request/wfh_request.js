// WFH Request — Client Script
// Ecclesia Module

frappe.ui.form.on("WFH Request", {

    onload(frm) {
        frm.set_query("employee", () => {
            if (frappe.session.user !== "Administrator") {
                return { filters: { user_id: frappe.session.user } };
            }
        });
    },

    refresh(frm) {
        frm.trigger("_setup_buttons");
        frm.trigger("_set_status_indicator");
    },

    employee(frm) {
        if (frm.doc.employee) {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Employee",
                    filters: { name: frm.doc.employee },
                    fieldname: ["employee_name", "department", "designation", "reports_to"]
                },
                callback(r) {
                    if (r.message) {
                        frm.set_value("employee_name", r.message.employee_name);
                        frm.set_value("department", r.message.department);
                        frm.set_value("designation", r.message.designation);
                    }
                }
            });
        }
    },

    from_date(frm) { 
        frm.trigger("_calc_days"); 
        frm.trigger("_check_overlap"); 
    },
    
    to_date(frm) {   
        frm.trigger("_calc_days"); 
        frm.trigger("_check_overlap"); 
    },

    _calc_days(frm) {
        if (frm.doc.from_date && frm.doc.to_date) {
            const days = frappe.datetime.get_day_diff(frm.doc.to_date, frm.doc.from_date) + 1;
            if (days < 0) {
                frappe.msgprint(__("To Date must be after From Date."));
                frm.set_value("to_date", frm.doc.from_date);
                return;
            }
            frm.set_value("total_days", days);
        }
    },

    _check_overlap(frm) {
        if (!frm.doc.employee || !frm.doc.from_date || !frm.doc.to_date) return;
        frappe.call({
            method: "ecclesia.doctype.wfh_request.wfh_request.get_active_wfh_request",
            args: { employee: frm.doc.employee, date: frm.doc.from_date },
            callback(r) {
                if (r.message && r.message.name !== frm.doc.name) {
                    frappe.msgprint({
                        title: __("Overlap Warning"),
                        message: __("An active WFH Request ({0}) already exists for this period.", [r.message.name]),
                        indicator: "orange"
                    });
                }
            }
        });
    },

    _setup_buttons(frm) {
        const s = frm.doc.status;

        if (s === "Draft" && !frm.is_new()) {
            frm.add_custom_button(__("Submit for Approval"), () => {
                frm.call("request_approval").then(() => frm.reload_doc());
            }, __("Actions")).addClass("btn-primary");
        }

        if (s === "Pending Approval") {
            frm.add_custom_button(__("Approve"), () => {
                frm.call("approve").then(() => frm.reload_doc());
            }, __("Actions")).addClass("btn-success");

            frm.add_custom_button(__("Reject"), () => {
                frappe.prompt(
                    [{ label: __("Rejection Reason"), fieldname: "reason", fieldtype: "Small Text", reqd: 1 }],
                    (values) => {
                        frm.call({ method: "reject", args: { reason: values.reason } })
                            .then(() => frm.reload_doc());
                    },
                    __("Reject WFH Request"),
                    __("Reject")
                );
            }, __("Actions")).addClass("btn-danger");
        }

        if (s === "Approved") {
            frm.add_custom_button(__("View Sessions"), () => {
                frappe.route_options = { wfh_request: frm.doc.name };
                frappe.set_route("List", "WFH Session");
            });
        }
    },

    _set_status_indicator(frm) {
        const colors = {
            "Draft": "gray",
            "Pending Approval": "yellow",
            "Approved": "green",
            "Rejected": "red",
            "Cancelled": "gray"
        };
        if (frm.page && frm.page.set_indicator) {
            frm.page.set_indicator(frm.doc.status, colors[frm.doc.status] || "gray");
        }
    }
});