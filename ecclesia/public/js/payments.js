// ============================================================
//  Auto Transaction Coding — Client Script (Enterprise Edition)
//  DocType : Payments
//  App     : ecclesia
// ============================================================
//
//  Place this in:
//    Customization > Client Script  (DocType = Payments)
//
//  Changes from v1:
//    - Passes `company` to the preview API so the server can
//      resolve accounts against the correct Chart of Accounts.
//    - Displays rule_scope (Global / Company-Specific) and
//      resolution_method in the result dialogs so finance staff
//      understand exactly how the account was determined.
//    - Company field validation before any API call.
//    - Richer status badge that distinguishes "Resolution Failed"
//      from "Unmatched".
// ============================================================

frappe.ui.form.on("Payments", {

    // ── refresh ──────────────────────────────────────────────
    refresh(frm) {
        _render_status_badge(frm);

        frm.add_custom_button(
            __("Auto Code Account"),
            () => _run_auto_coding(frm),
            __("Actions")
        );

        frm.add_custom_button(
            __("Preview Match"),
            () => _preview_match(frm),
            __("Actions")
        );

        if (["Matched", "Resolution Failed"].includes(frm.doc.auto_coding_status)) {
            frm.add_custom_button(
                __("Re-code on Next Run"),
                () => _flag_for_recode(frm),
                __("Actions")
            );
        }

        // Inform the user if account resolution previously failed
        if (frm.doc.auto_coding_status === "Resolution Failed") {
            frm.dashboard.set_headline_alert(
                __(
                    "⚠️ A rule matched this description but no account could be resolved " +
                    "for company <b>{0}</b>. Check that the account name in rule <b>{1}</b> " +
                    "exists in this company's Chart of Accounts.",
                    [frm.doc.company || "?", frm.doc.auto_coding_rule || "?"]
                ),
                "red"
            );
        }
    },

    // ── transaction_description change ───────────────────────
    transaction_description(frm) {
        if (!frm.doc.transaction_description) return;
        if (frm.doc.account_to_debit) {
            frappe.model.set_value(
                frm.doctype, frm.docname,
                "auto_coding_status", "Pending Re-code"
            );
            frm.dashboard.set_headline_alert(
                __("Description changed — coding will be re-evaluated on the next scheduled run."),
                "yellow"
            );
        }
    },

    // ── auto_coding_status change ─────────────────────────────
    auto_coding_status(frm) {
        _render_status_badge(frm);
    },
});


// ============================================================
//  Action handlers
// ============================================================

function _run_auto_coding(frm) {
    if (!frm.doc.transaction_description) {
        frappe.msgprint({
            title    : __("Cannot Code"),
            message  : __("Please enter a Transaction Description before running auto coding."),
            indicator: "orange",
        });
        return;
    }
    if (!frm.doc.company) {
        frappe.msgprint({
            title    : __("Cannot Code"),
            message  : __("This payment has no Company set. Auto coding requires a company to resolve accounts."),
            indicator: "orange",
        });
        return;
    }

    frappe.dom.freeze(__("Coding transaction…"));

    frappe.call({
        method  : "ecclesia.api.auto_transaction_coding.code_payment_api",
        args    : { payment_name: frm.docname },
        freeze  : false,
        callback(r) {
            frappe.dom.unfreeze();
            if (r.exc) {
                frappe.msgprint({ title: __("Error"), message: __("Check the Error Log for details."), indicator: "red" });
                return;
            }

            const res = r.message;

            if (res.status === "Matched") {
                frappe.show_alert({
                    message: __(
                        "✅ Account set: <b>{0}</b><br>" +
                        "Rule: {1} &nbsp;|&nbsp; Scope: {2} &nbsp;|&nbsp; Resolved by: {3}",
                        [res.account, res.rule, res.rule_scope || "—", res.resolution_method || "—"]
                    ),
                    indicator: "green",
                }, 8);
                frm.reload_doc();

            } else if (res.status === "Resolution Failed") {
                frappe.msgprint({
                    title  : __("⚠️ Rule Matched — Account Not Found"),
                    message: __(
                        "Rule <b>{0}</b> matched the description but the account " +
                        "<b>{1}</b> does not exist in company <b>{2}</b>'s Chart of Accounts.<br><br>" +
                        "Please either:<br>" +
                        "• Add the account to this company's Chart of Accounts, or<br>" +
                        "• Create a company-specific rule override for this company.",
                        [res.rule || "?",
                         frm.doc.auto_coding_rule || res.rule || "?",
                         frm.doc.company]
                    ),
                    indicator: "red",
                });
                frm.reload_doc();

            } else {
                frappe.show_alert({
                    message  : __("No matching rule found for this description."),
                    indicator: "orange",
                }, 6);
                frm.reload_doc();
            }
        },
    });
}


function _preview_match(frm) {
    if (!frm.doc.company) {
        frappe.msgprint({
            title    : __("Company Required"),
            message  : __("Set a Company on this Payment before previewing — account resolution is company-specific."),
            indicator: "orange",
        });
        return;
    }

    const d = new frappe.ui.Dialog({
        title : __("Preview Auto Coding — {0}", [frm.doc.company]),
        fields: [
            {
                label    : __("Transaction Description to Test"),
                fieldname: "description",
                fieldtype: "Small Text",
                default  : frm.doc.transaction_description || "",
                reqd     : 1,
            },
            {
                label    : __("Company"),
                fieldname: "company",
                fieldtype: "Link",
                options  : "Company",
                default  : frm.doc.company,
                reqd     : 1,
                description: __("Change to test how this description would be coded for a different company."),
            },
        ],
        primary_action_label: __("Test"),
        primary_action(values) {
            d.hide();
            frappe.dom.freeze(__("Checking rules…"));

            frappe.call({
                method  : "ecclesia.api.auto_transaction_coding.preview_match",
                args    : { description: values.description, company: values.company },
                freeze  : false,
                callback(r) {
                    frappe.dom.unfreeze();
                    if (r.exc) { frappe.msgprint(__("Error running preview.")); return; }

                    const res = r.message;

                    if (res.status === "matched") {
                        frappe.msgprint({
                            title  : __("✅ Match Found"),
                            message: __(
                                "<b>Account:</b> {0}<br>" +
                                "<b>Rule:</b> {1}<br>" +
                                "<b>Scope:</b> {2}<br>" +
                                "<b>Resolved by:</b> {3}",
                                [res.account, res.rule,
                                 res.rule_scope || "—",
                                 res.resolution_method || "—"]
                            ),
                            indicator: "green",
                        });
                    } else {
                        frappe.msgprint({
                            title    : __("⚠️ No Match"),
                            message  : __(
                                "No active rule matched this description for company <b>{0}</b>.<br><br>" +
                                "Tip: Go to <b>Auto Transaction Coding Rule</b> to add or adjust rules.",
                                [values.company]
                            ),
                            indicator: "orange",
                        });
                    }
                },
            });
        },
    });
    d.show();
}


function _flag_for_recode(frm) {
    frappe.confirm(
        __("Clear the current account coding and queue for re-evaluation on the next scheduled run?"),
        () => {
            frm.set_value("account_to_debit", "");
            frm.set_value("auto_coding_rule", "");
            frm.set_value("auto_coding_status", "Pending Re-code");
            frm.save().then(() => {
                frappe.show_alert({ message: __("Payment queued for re-coding."), indicator: "blue" });
            });
        }
    );
}


// ============================================================
//  UI helpers
// ============================================================

function _render_status_badge(frm) {
    const status = frm.doc.auto_coding_status;
    if (!status) return;

    const colour_map = {
        "Matched"           : "green",
        "Unmatched"         : "orange",
        "Resolution Failed" : "red",
        "Pending Re-code"   : "yellow",
        "Not Processed"     : "grey",
    };
    const colour = colour_map[status] || "grey";

    const field = frm.get_field("auto_coding_status");
    if (field && field.$wrapper) {
        field.$wrapper.find(".control-value").html(
            `<span class="indicator ${colour}">${__(status)}</span>`
        );
    }
}



// ============================================================
//  PATCH: Auto-code account_to_debit before submit validation
//  Merge this into your existing Payments client script.
//
//  Strategy
//  ─────────
//  before_submit fires BEFORE the mandatory-field validation.
//  We intercept it, check if account_to_debit is missing AND
//  the conditions that would trigger the throw are true, then:
//    1. Call the auto-coding API synchronously (await).
//    2. If a match is found  → let submit proceed.
//    3. If Resolution Failed → stop submit, show actionable error.
//    4. If Unmatched         → stop submit, open the manual picker.
//    5. If trans_type is NOT 'Expense Payment' or
//       create_accounting_entries is false → skip entirely.
//
//  This keeps the existing before_submit validation intact and
//  unchanged — we simply ensure account_to_debit is populated
//  before it runs.
// ============================================================

frappe.ui.form.on("Payments", {

    // ── existing hooks (keep all your other hooks as-is) ─────

    // ── NEW: intercept submit to auto-code if needed ──────────
    before_submit(frm) {
        // Only intercept when the validation would fire
        const needsAccount = (
            frm.doc.create_accounting_entries &&
            frm.doc.trans_type === "Expense Payment" &&
            !frm.doc.account_to_debit
        );

        if (!needsAccount) {
            // Nothing to do — let the existing before_submit logic run
            return;
        }

        if (!frm.doc.transaction_description) {
            // No description to match on — fall through to the existing
            // throw("Account to Debit is required") naturally
            return;
        }

        if (!frm.doc.company) {
            frappe.throw(__(
                "Cannot auto-code account: this Payment has no Company set."
            ));
            return;
        }

        // ── Return a Promise so ERPNext waits for resolution ──
        // ERPNext's submit pipeline respects a returned Promise
        // from before_submit and will not proceed until it resolves.
        return new Promise((resolve, reject) => {

            frappe.dom.freeze(__("Auto-coding account before submit…"));

            frappe.call({
                method : "ecclesia.api.auto_transaction_coding.code_payment_api",
                args   : { payment_name: frm.docname },
                freeze : false,  // we manage the freeze ourselves
                callback(r) {
                    frappe.dom.unfreeze();

                    if (r.exc) {
                        frappe.msgprint({
                            title    : __("Auto-Coding Error"),
                            message  : __(
                                "An error occurred while auto-coding the account. " +
                                "Please assign <b>Account to Debit</b> manually and retry."
                            ),
                            indicator: "red",
                        });
                        reject();   // abort submit
                        return;
                    }

                    const res = r.message;

                    // ── Matched → reload field value then allow submit ──
                    if (res.status === "Matched") {
                        frappe.show_alert({
                            message  : __(
                                "✅ Account auto-coded: <b>{0}</b> (Rule: {1})",
                                [res.account, res.rule]
                            ),
                            indicator: "green",
                        }, 5);

                        // Reload the doc so the newly written account_to_debit
                        // is visible to the subsequent before_submit validation
                        frm.reload_doc().then(() => resolve());
                        return;
                    }

                    // ── Resolution Failed → account name not in this company ──
                    if (res.status === "Resolution Failed") {
                        frappe.msgprint({
                            title    : __("⚠️ Account Not Found in Chart of Accounts"),
                            message  : __(
                                "A rule matched this payment (<b>{0}</b>) but the mapped " +
                                "account does not exist in <b>{1}</b>'s Chart of Accounts.<br><br>" +
                                "Options:<br>" +
                                "• Add the account to this company's Chart of Accounts, <i>or</i><br>" +
                                "• Create a company-specific rule override, <i>or</i><br>" +
                                "• Select <b>Account to Debit</b> manually below.",
                                [res.rule || "unknown rule", frm.doc.company]
                            ),
                            indicator: "red",
                        });
                        _open_manual_account_picker(frm, reject);
                        return;
                    }

                    // ── Unmatched → no rule found, let user pick manually ──
                    frappe.msgprint({
                        title    : __("⚠️ No Matching Rule Found"),
                        message  : __(
                            "Auto-coding could not determine the correct account for:<br>" +
                            "<i>\"{0}\"</i><br><br>" +
                            "Please select the <b>Account to Debit</b> manually to continue.",
                            [frm.doc.transaction_description]
                        ),
                        indicator: "orange",
                    });
                    _open_manual_account_picker(frm, reject);
                },
            });
        });
    },
});


// ============================================================
//  Helper: open a quick account picker dialog so the user
//  can resolve manually without leaving the form.
//  Calls reject() on the Promise if the user cancels,
//  which aborts the submit.
// ============================================================
function _open_manual_account_picker(frm, reject) {
    const d = new frappe.ui.Dialog({
        title              : __("Select Account to Debit"),
        primary_action_label: __("Apply & Submit"),
        fields: [
            {
                label      : __("Account to Debit"),
                fieldname  : "account_to_debit",
                fieldtype  : "Link",
                options    : "Account",
                reqd       : 1,
                get_query  : () => ({
                    filters: {
                        company : frm.doc.company,
                        is_group: 0,
                    },
                }),
            },
        ],
        primary_action(values) {
            d.hide();

            // Write the value directly to the doc and the DB field,
            // then re-trigger submit now that the field is populated.
            frappe.db.set_value(
                "Payments",
                frm.docname,
                "account_to_debit",
                values.account_to_debit
            ).then(() => {
                frm.set_value("account_to_debit", values.account_to_debit);
                frm.set_value("auto_coding_status", "Unmatched");
                frm.set_value("auto_assigned_account_to_debit", values.account_to_debit);

                frappe.show_alert({
                    message  : __("Account set manually. Resubmitting…"),
                    indicator: "blue",
                }, 3);

                // Small delay so the alert is visible, then re-submit
                setTimeout(() => frm.savesubmit(), 800);
            });
        },
        onhide() {
            // User closed the dialog without picking — abort submit
            reject();
            frappe.show_alert({
                message  : __("Submit cancelled. Please set Account to Debit before submitting."),
                indicator: "orange",
            }, 5);
        },
    });

    d.show();
}