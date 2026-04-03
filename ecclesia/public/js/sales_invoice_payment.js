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

//======================================
// === Sales Invoice Custom Script ===

frappe.ui.form.on('Sales Invoice', {

    onload: function(frm) {
        frm.trigger('fetch_opening_balance');
    },

    refresh: function(frm) {
        frm.trigger('fetch_opening_balance');
    },

    customer: function(frm) {
        frm.trigger('fetch_opening_balance');
    },

    posting_date: function(frm) {
        frm.trigger('fetch_opening_balance');
    },

    fetch_opening_balance: function(frm) {
        if (!frm.doc.customer || !frm.doc.posting_date) return;

        let company = frm.doc.company || frappe.defaults.get_default('company');

        frappe.call({
            method: 'ecclesia.api.customer_balance.get_customer_opening_balance',   // Server Script name exactly
            args: {
                customer: frm.doc.customer,
                company: company,
                transaction_date: frm.doc.posting_date,
                current_docname: frm.doc.name || null
            },
            callback: function(r) {
                if (r.message !== undefined) {
                    frm.set_value('opening_balance', flt(r.message));
                    frm.trigger('derive_balance');
                }
            }
        });
    },

    derive_balance: function(frm) {
        let opening_balance  = flt(frm.doc.opening_balance);
        let total_sales      = flt(frm.doc.grand_total);
        let cum_paid_amount  = flt(frm.doc.custom_amount);

        // balance = opening_balance + total_sales - cum_paid_amount
        let balance = opening_balance + total_sales - cum_paid_amount;

        frm.set_value('total_sales', total_sales);
        frm.set_value('cum_paid_amount', cum_paid_amount);
        frm.set_value('balance', balance);
    }
});

// Recalculate when items change
frappe.ui.form.on('Sales Invoice Item', {
    qty: function(frm)    { frm.trigger('derive_balance'); },
    rate: function(frm)   { frm.trigger('derive_balance'); },
    amount: function(frm) { frm.trigger('derive_balance'); },
    items_add: function(frm)    { frm.trigger('derive_balance'); },
    items_remove: function(frm) { frm.trigger('derive_balance'); }
});


/*
// === Sales Invoice Custom Script ===

frappe.ui.form.on('Sales Invoice', {

    // Trigger on form load and refresh
    onload: function(frm) {
        frm.trigger('calculate_custom_fields');
    },

    refresh: function(frm) {
        frm.trigger('calculate_custom_fields');
    },

    // Trigger when customer changes
    customer: function(frm) {
        frm.trigger('calculate_custom_fields');
    },

    // Trigger when custom_amount changes
    custom_amount: function(frm) {
        frm.trigger('derive_balance');
    },

    // Main function to fetch opening balance and derive all fields
    calculate_custom_fields: function(frm) {
        if (!frm.doc.customer || !frm.doc.company) return;

        // Fetch the customer's ledger balance BEFORE this invoice
        frappe.call({
            method: 'frappe.client.get_value',
            args: {
                doctype: 'GL Entry',
                filters: {
                    party_type: 'Customer',
                    party: frm.doc.customer,
                    company: frm.doc.company,
                    is_cancelled: 0
                },
                fieldname: ['sum(debit) - sum(credit)']  // net balance
            },
            callback: function(r) {
                // Use the proper balance query below instead
            }
        });

        // Better approach: use get_balance_on from accounts utils
        frappe.call({
            method: 'erpnext.accounts.utils.get_balance_on',
            args: {
                party_type: 'Customer',
                party: frm.doc.customer,
                company: frm.doc.company,
                // Pass posting date to get balance BEFORE current invoice
                date: frm.doc.posting_date || frappe.datetime.get_today(),
                in_account_currency: false
            },
            callback: function(r) {
                if (r.message !== undefined) {
                    let opening_balance = flt(r.message);

                    // If this is an existing saved invoice, subtract its own grand total
                    // to avoid double-counting (balance already includes this doc)
                    if (!frm.doc.__islocal && frm.doc.docstatus !== 0) {
                        opening_balance = opening_balance - flt(frm.doc.grand_total);
                    }

                    frm.set_value('opening_balance', opening_balance);
                    frm.trigger('derive_balance');
                }
            }
        });
    },

    // Derive the remaining fields once opening_balance is set
    derive_balance: function(frm) {
        // total_sales = grand total of current invoice
        let total_sales = flt(frm.doc.grand_total);

        // cum_paid_amount = doc.custom_amount
        let cum_paid_amount = flt(frm.doc.custom_amount);

        // opening_balance already set above
        let opening_balance = flt(frm.doc.opening_balance);

        // balance = opening_balance + total_sales - cum_paid_amount
        let balance = opening_balance + total_sales - cum_paid_amount;

        frm.set_value('total_sales', total_sales);
        frm.set_value('cum_paid_amount', cum_paid_amount);
        frm.set_value('balance', balance);
    }
});


// Also recalculate when items table changes (grand_total updates)
frappe.ui.form.on('Sales Invoice Item', {
    items_add: function(frm) {
        frm.trigger('derive_balance');
    },
    items_remove: function(frm) {
        frm.trigger('derive_balance');
    },
    qty: function(frm) {
        frm.trigger('derive_balance');
    },
    rate: function(frm) {
        frm.trigger('derive_balance');
    },
    amount: function(frm) {
        frm.trigger('derive_balance');
    }
});
*/