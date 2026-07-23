// ecclesia/public/js/sales_invoice_payment.js
// Loaded on the Sales Invoice form via hooks.py → doctype_js

frappe.ui.form.on("Sales Invoice", {

    refresh(frm) {
        // Only show payment buttons on submitted invoices with outstanding balance
        if (frm.doc.docstatus !== 1) return;

        if (frm.doc.outstanding_amount > 0) {
            frm.add_custom_button(__("Generate Payment Link"), () => {
                _generate_payment_link(frm);
            }, __("Ecclesia"));
        }

        frm.add_custom_button(__("View Payment Logs"), () => {
            frappe.route_options = {
                reference_doctype: "Sales Invoice",
                reference_docname: frm.doc.name
            };
            frappe.set_route("List", "Payment Gateway Log");
        }, __("Ecclesia"));

        // Show a green indicator if this invoice has been paid via Ecclesia
        _show_payment_indicator(frm);
    }
});


function _generate_payment_link(frm) {
    // Step 1: Let user pick which gateway to use
    frappe.prompt([
        {
            label:     __("Payment Gateway"),
            fieldname: "gateway_name",
            fieldtype: "Link",
            options:   "Payment Gateway Settings",
            reqd:      1,
            filters:   { enabled: 1 },
            description: "Select the gateway to generate the payment link from"
        }
    ],
    function (values) {
        // Step 2: Call ecclesia.api.payment.initiate
        frappe.call({
            method:        "ecclesia.api.payment.initiate",
            args: {
                reference_doctype: "Sales Invoice",
                reference_docname: frm.doc.name,
                gateway_name:      values.gateway_name
            },
            freeze:         true,
            freeze_message: __("Generating payment link..."),
            callback(r) {
                if (!r.message) return;

                const url = r.message.payment_url;
                if (!url) {
                    frappe.msgprint({
                        title:     __("Error"),
                        message:   __("Gateway did not return a payment URL. Check Payment Gateway Settings."),
                        indicator: "red"
                    });
                    return;
                }

                // Step 3: Show the URL with a copy button
                frappe.msgprint({
                    title:   __("Payment Link Generated"),
                    message: `
                        <p>Share this link with your customer:</p>
                        <div style="
                            background: #f4f5f6;
                            border: 1px solid #d1d8dd;
                            border-radius: 4px;
                            padding: 10px 14px;
                            word-break: break-all;
                            margin-bottom: 10px;
                        ">
                            <a href="${url}" target="_blank">${url}</a>
                        </div>
                        <button
                            class="btn btn-sm btn-primary"
                            onclick="navigator.clipboard.writeText('${url}').then(() =>
                                frappe.show_alert({ message: 'Copied!', indicator: 'green' }, 2)
                            )">
                            📋 Copy Link
                        </button>
                    `,
                    indicator: "green"
                });

                frm.reload_doc();
            }
        });
    },
    __("Select Payment Gateway"),
    __("Generate Link")
    );
}


function _show_payment_indicator(frm) {
    frappe.db.count("Payment Gateway Log", {
        reference_doctype: "Sales Invoice",
        reference_docname: frm.doc.name,
        status:            "Success"
    }).then(count => {
        if (count > 0) {
            frm.dashboard.add_indicator(
                __(`${count} Ecclesia Payment${count > 1 ? "s" : ""} Received`),
                "green"
            );
        }
    });
}

