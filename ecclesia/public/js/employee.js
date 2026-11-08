frappe.ui.form.on("Employee", {

    refresh(frm) {
        // ── Tax sync button ─────────────────────────────────────────
        // Moved first and wrapped so a failure elsewhere can never
        // suppress this button.
        try {
            frm.add_custom_button(__("Sync Monthly Tax Payable"), function () {
                sync_tax(frm);
            }, __("Actions"));
        } catch (e) {
            console.error("[Ecclesia] Failed to add Sync Tax button", e);
        }

        // ── HR manual reassign button ────────────────────────────────
        try {
            frm.trigger("add_leave_policy_button");
        } catch (e) {
            console.error("[Ecclesia] add_leave_policy_button failed", e);
        }

        // ── Leave policy checks (dialog only, no buttons) ─────────────
        try {
            frm.trigger("check_pending_leave_policy");
        } catch (e) {
            console.error("[Ecclesia] check_pending_leave_policy failed", e);
        }
    },

    status(frm) {
        if (frm.doc.status === "Active" && !frm.is_new()) {
            setTimeout(() => {
                try {
                    frm.trigger("check_pending_leave_policy");
                } catch (e) {
                    console.error("[Ecclesia] check_pending_leave_policy (status) failed", e);
                }
            }, 400);
        }
    },

    after_save(frm) {
        sync_tax(frm);
    },

    check_pending_leave_policy(frm) {
        if (frm.is_new()) return;
        if (!frm.doc.custom_pending_leave_policy_assignment) return;
        if (frm.doc.status !== "Active") return;

        setTimeout(() => _show_policy_assignment_dialog(frm), 700);
    },

    add_leave_policy_button(frm) {
        if (frm.is_new()) return;

        let has_role = false;
        try {
            has_role = frappe.user.has_role(["HR Manager", "System Manager"]);
        } catch (e) {
            console.error("[Ecclesia] has_role check failed", e);
            return;
        }
        if (!has_role) return;

        frm.add_custom_button("Assign Leave Policy", () => {
            _show_manual_assign_dialog(frm);
        }, "HR Actions");
    },
});


// ── New-employee confirmation dialog ─────────────────────────────────

async function _show_policy_assignment_dialog(frm) {
    let preview;
    try {
        const r = await frappe.call({
            method: "ecclesia.api.leave_policy.assign_policy_for_new_employee",
            args:   { employee: frm.doc.name, confirmed: 0 },
        });
        preview = r.message;
    } catch (e) {
        console.error("[Ecclesia] Leave policy preview failed", e);
        return;
    }

    if (!preview || preview.message === "already_assigned") return;

    if (!preview.policy) {
        frappe.show_alert({
            message: `No leave policy matched for ${frm.doc.employee_name}. ` +
                     `Use HR Actions → Assign Leave Policy to assign manually.`,
            indicator: "orange"
        }, 8);
        return;
    }

    const leave_rows = (preview.leave_types || []).map(lt => `
        <tr>
            <td style="padding:8px 12px;font-size:13px;
                       color:var(--text-color)">${lt.leave_type}</td>
            <td style="padding:8px 12px;font-size:13px;font-weight:500;
                       text-align:right;color:var(--text-color)">
                ${lt.annual_allocation} days
            </td>
        </tr>
    `).join("");

    const dialog = new frappe.ui.Dialog({
        title:  "Assign leave policy",
        size:   "large",
        fields: [
            {
                fieldtype: "HTML",
                fieldname: "preview_html",
                options: `
                    <div style="padding:4px 0 16px">

                        <div style="display:flex;align-items:center;gap:12px;
                                    margin-bottom:20px">
                            <div style="width:40px;height:40px;border-radius:50%;
                                        background:var(--bg-green);
                                        display:flex;align-items:center;
                                        justify-content:center">
                                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                                    <path d="M3 8.5l3.5 3.5 6.5-7"
                                          stroke="var(--green)"
                                          stroke-width="1.5"
                                          stroke-linecap="round"
                                          stroke-linejoin="round"/>
                                </svg>
                            </div>
                            <div>
                                <p style="font-size:14px;font-weight:500;margin:0">
                                    ${frm.doc.employee_name}
                                </p>
                                <p style="font-size:12px;color:var(--text-muted);margin:2px 0 0">
                                    ${frm.doc.gender || "—"} &nbsp;·&nbsp;
                                    ${frm.doc.department || "—"} &nbsp;·&nbsp;
                                    ${frm.doc.designation || "—"}
                                </p>
                            </div>
                        </div>

                        <div style="background:var(--control-bg);border-radius:6px;
                                    padding:12px 16px;margin-bottom:16px">
                            <p style="font-size:11px;font-weight:500;
                                       text-transform:uppercase;letter-spacing:.05em;
                                       color:var(--text-muted);margin:0 0 4px">
                                Matched policy
                            </p>
                            <p style="font-size:15px;font-weight:500;margin:0">
                                ${preview.policy_label}
                            </p>
                        </div>

                        <p style="font-size:11px;font-weight:500;text-transform:uppercase;
                                   letter-spacing:.05em;color:var(--text-muted);margin:0 0 8px">
                            Leave entitlements that will be created
                        </p>
                        <table style="width:100%;border-collapse:collapse;
                                      border:1px solid var(--border-color);
                                      border-radius:6px;overflow:hidden">
                            <thead>
                                <tr style="background:var(--control-bg)">
                                    <th style="padding:8px 12px;font-size:11px;font-weight:500;
                                               text-align:left;color:var(--text-muted);
                                               text-transform:uppercase;letter-spacing:.04em;
                                               border-bottom:1px solid var(--border-color)">
                                        Leave type
                                    </th>
                                    <th style="padding:8px 12px;font-size:11px;font-weight:500;
                                               text-align:right;color:var(--text-muted);
                                               text-transform:uppercase;letter-spacing:.04em;
                                               border-bottom:1px solid var(--border-color)">
                                        Days / year
                                    </th>
                                </tr>
                            </thead>
                            <tbody>${leave_rows}</tbody>
                        </table>

                        <p style="font-size:12px;color:var(--text-muted);margin:12px 0 0">
                            Allocations will be valid from today through
                            31 Dec ${new Date().getFullYear()}.
                        </p>
                    </div>
                `
            }
        ],
        primary_action_label: "Confirm & assign",
        primary_action() {
            dialog.hide();
            _execute_new_employee_assignment(frm, preview.policy, preview.policy_label);
        },
        secondary_action_label: "Assign later",
        secondary_action() {
            dialog.hide();
            frappe.show_alert({
                message: "Leave policy not assigned yet. " +
                         "Use HR Actions → Assign Leave Policy when ready.",
                indicator: "orange"
            }, 6);
        }
    });

    dialog.show();
}


async function _execute_new_employee_assignment(frm, policy, policy_label) {
    frappe.show_alert({ message: "Assigning leave policy…", indicator: "blue" });

    try {
        const r = await frappe.call({
            method: "ecclesia.api.leave_policy.assign_policy_for_new_employee",
            args:   { employee: frm.doc.name, confirmed: 1 },
        });

        const result = r.message;

        if (result.message === "already_assigned") {
            frappe.show_alert({
                message: "Leave policy already assigned for this year.",
                indicator: "orange"
            });
            return;
        }

        if (result.message === "assigned") {
            await frappe.db.set_value(
                "Employee", frm.doc.name,
                "custom_pending_leave_policy_assignment", 0
            );
            frm.reload_doc();
            frappe.show_alert({
                message: `Leave policy assigned: ${policy_label}`,
                indicator: "green"
            }, 5);
        }

    } catch (e) {
        frappe.msgprint({
            title:     "Assignment failed",
            message:   e.message || "An unexpected error occurred.",
            indicator: "red"
        });
    }
}


// ── HR manual reassign dialog ─────────────────────────────────────────

function _show_manual_assign_dialog(frm) {
    const dialog = new frappe.ui.Dialog({
        title: "Assign leave policy manually",
        fields: [
            {
                label:     "Leave Policy",
                fieldname: "leave_policy",
                fieldtype: "Link",
                options:   "Leave Policy",
                reqd:      1,
                onchange() {
                    const policy = dialog.get_value("leave_policy");
                    if (!policy) return;
                    frappe.db.get_doc("Leave Policy", policy).then(doc => {
                        const rows = (doc.leave_policy_details || []).map(lt =>
                            `<div style="display:flex;justify-content:space-between;
                                         padding:5px 0;font-size:13px;
                                         border-bottom:1px solid var(--border-color)">
                                <span>${lt.leave_type}</span>
                                <span style="font-weight:500">
                                    ${lt.annual_allocation} days
                                </span>
                            </div>`
                        ).join("");
                        dialog.fields_dict.policy_preview.$wrapper.html(
                            rows ||
                            `<p style="font-size:12px;color:var(--text-muted)">
                                No leave types configured on this policy.
                            </p>`
                        );
                    });
                }
            },
            { fieldtype: "Column Break" },
            {
                label:     "Effective From",
                fieldname: "effective_from",
                fieldtype: "Date",
                reqd:      1,
                default:   frappe.datetime.get_today(),
            },
            {
                label:     "Effective To",
                fieldname: "effective_to",
                fieldtype: "Date",
                reqd:      1,
                default:   `${new Date().getFullYear()}-12-31`,
            },
            {
                fieldtype: "Section Break",
                label:     "Entitlements preview"
            },
            {
                fieldname: "policy_preview",
                fieldtype: "HTML",
                options:   `<p style="font-size:12px;color:var(--text-muted)">
                                Select a policy above to preview entitlements.
                            </p>`
            },
            { fieldtype: "Section Break" },
            {
                label:     "Carry forward unused leaves",
                fieldname: "carry_forward",
                fieldtype: "Check",
                default:   0,
            },
        ],
        primary_action_label: "Assign",
        primary_action(values) {
            if (!values.leave_policy) {
                frappe.msgprint("Please select a leave policy.");
                return;
            }
            dialog.hide();
            frappe.call({
                method: "ecclesia.api.leave_policy.manual_reassign",
                args: {
                    employee:       frm.doc.name,
                    policy:         values.leave_policy,
                    effective_from: values.effective_from,
                    effective_to:   values.effective_to,
                    carry_forward:  values.carry_forward ? 1 : 0,
                },
                callback({ message }) {
                    if (message?.assignment) {
                        frappe.show_alert({
                            message:   `Policy assigned. Allocation: ${message.assignment}`,
                            indicator: "green"
                        }, 5);
                        frm.reload_doc();
                    }
                }
            });
        }
    });

    dialog.show();
}


// ── Tax sync ────────────────────────────────────────────────────────────

function sync_tax(frm) {
    if (frm.is_new()) return;

    frappe.call({
        method: "ecclesia.api.employee_tax_sync.sync_employee_tax",
        args: { employee: frm.doc.name },
        freeze: true,
        freeze_message: __("Syncing tax data..."),
        callback: function (r) {
            frappe.show_alert({
                message: __("Tax sync completed"),
                indicator: "green"
            });
            frm.reload_doc();
        },
        error: function (r) {
            frappe.show_alert({
                message: __("Tax sync failed: ") + (r.message || ""),
                indicator: "red"
            });
        }
    });
}



// Client Script — DocType: Employee
// Computes monthly_gross_pay and ctc from annual_gross_salary,
// using per-Company rates instead of hardcoded 30/30/30/10.
//
// Prerequisite Custom Fields on Company (all Percent type):
//   custom_basic_salary_rate       (default 30)
//   custom_transport_allowance_rate (default 30)
//   custom_housing_allowance_rate   (default 30)
//   custom_employer_pension_rate    (default 10)
//
// Prerequisite Custom Fields on Employee:
//   annual_gross_salary  (Currency)
//   monthly_gross_pay    (Currency, read-only)
//   ctc                  (Currency, read-only)

frappe.ui.form.on('Employee', {
	refresh: function (frm) {
		calculate_salary_breakdown(frm);
	},

	annual_gross_salary: function (frm) {
		calculate_salary_breakdown(frm);
	},

	company: function (frm) {
		calculate_salary_breakdown(frm);
	},

	validate: function (frm) {
		calculate_salary_breakdown(frm);
	}
});

function calculate_salary_breakdown(frm) {
	if (!frm.doc.annual_gross_salary || !frm.doc.company) {
		return;
	}

	frappe.db.get_value(
		'Company',
		frm.doc.company,
		[
			'custom_basic_salary_rate',
			'custom_transport_allowance_rate',
			'custom_housing_allowance_rate',
			'custom_employer_pension_rate'
		],
		function (r) {
			if (!r) {
				frappe.msgprint(__('Salary rates not configured on Company {0}', [frm.doc.company]));
				return;
			}

			// Fall back to 30/30/30/10 only if the Company fields are blank
			const basic_rate = flt(r.custom_basic_salary_rate) || 30;
			const transport_rate = flt(r.custom_transport_allowance_rate) || 30;
			const housing_rate = flt(r.custom_housing_allowance_rate) || 30;
			const pension_rate = flt(r.custom_employer_pension_rate) || 10;

			const annual_gross = flt(frm.doc.annual_gross_salary);

			// Monthly Gross Pay = (Basic% + Transport% + Housing%) of annual gross, spread over 12 months
			const combined_rate = (basic_rate + transport_rate + housing_rate) / 100;
			const monthly_gross_pay = (annual_gross * combined_rate) / 12;

			// CTC = Annual Gross + Employer Pension Contribution (pension_rate% of annual gross)
			const ctc = annual_gross + (annual_gross * pension_rate) / 100;

			frm.set_value('monthly_gross_pay', monthly_gross_pay);
			frm.set_value('ctc', ctc);
		}
	);
}