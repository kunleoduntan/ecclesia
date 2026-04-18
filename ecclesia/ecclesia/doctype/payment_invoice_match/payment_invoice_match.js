// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

/**
 * Payment Invoice Match — Client Script
 * Drives the "Run AI Match" button and bridges to the custom UI page.
 */

const APP         = "ecclesia";
const MODULE_PATH = `${APP}.payment_invoice_match.payment_invoice_match.payment_invoice_match`;

frappe.ui.form.on("Payment Invoice Match", {

    refresh(frm) {
        frm.disable_save();

        if (frm.doc.status === "Draft" || frm.doc.status === "In Progress") {
            frm.add_custom_button(__("▶ Run AI Match"), () => {
                _run_ai_match(frm);
            }).css({
                "background": "linear-gradient(135deg, #DB1A1A 0%, #764ba2 100%)",
                "color":      "#fff",
                "font-weight": "bold",
                "border":     "none",
                "padding":    "6px 18px",
            });
        }

        if (frm.doc.matches_proposed > 0 && !frm.doc.__islocal) {
            frm.add_custom_button(__("🎯 Open Match Review UI"), () => {
                frappe.set_route("payment-match-review", frm.doc.name);
            });

            if (frm.doc.status === "In Progress") {
                frm.add_custom_button(__("✓ Apply All Approved"), () => {
                    _apply_approved(frm);
                }, __("Actions"));
            }
        }
    },

});

function _run_ai_match(frm) {
    if (!frm.doc.company)     { frappe.msgprint(__("Set Company first.")); return; }
    if (!frm.doc.party_type)  { frappe.msgprint(__("Set Party Type first.")); return; }
    if (!frm.doc.from_date)   { frappe.msgprint(__("Set From Date first.")); return; }
    if (!frm.doc.to_date)     { frappe.msgprint(__("Set To Date first.")); return; }

    if (frm.doc.__unsaved) {
        frappe.msgprint(__("Please save first.")); return;
    }

    frappe.confirm(
        __("Run AI matching for <b>{0}</b> payments between <b>{1}</b> and <b>{2}</b>?<br><br>"
           + "This will fetch all unmatched {0} payments and outstanding invoices, "
           + "then use Claude AI to propose matches.",
           [frm.doc.party_type, frm.doc.from_date, frm.doc.to_date]),
        () => {
            frappe.call({
                method:         `${MODULE_PATH}.run_ai_match`,
                args:           { doc_name: frm.doc.name },
                freeze:         true,
                freeze_message: __("🤖 AI is analysing payments and invoices..."),
                callback(r) {
                    if (!r.exc && r.message) {
                        frappe.show_alert({
                            message:   __(r.message.message),
                            indicator: "green",
                        }, 10);
                        frm.reload_doc();
                        setTimeout(() => {
                            frappe.set_route("payment-match-review", frm.doc.name);
                        }, 1500);
                    }
                },
            });
        }
    );
}

function _apply_approved(frm) {
    const approved = (frm.doc.match_lines || []).filter(
        l => l.match_status === "Approved" && !l.applied
    ).length;
    if (!approved) {
        frappe.msgprint(__("No approved matches to apply.")); return;
    }
    frappe.confirm(
        __("Apply <b>{0}</b> approved match(es) to ERPNext?<br>"
           + "This will update Payment Entries and mark invoices as paid.", [approved]),
        () => {
            frappe.call({
                method:         `${MODULE_PATH}.apply_approved`,
                args:           { doc_name: frm.doc.name },
                freeze:         true,
                freeze_message: __("Applying reconciliations..."),
                callback(r) {
                    if (!r.exc && r.message) {
                        frappe.show_alert({
                            message:   __(r.message.message),
                            indicator: r.message.errors > 0 ? "orange" : "green",
                        }, 8);
                        frm.reload_doc();
                    }
                },
            });
        }
    );
}