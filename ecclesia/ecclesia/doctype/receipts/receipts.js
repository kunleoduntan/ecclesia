/* ============================================================================
 * RECEIPTS - PRODUCTION CLIENT SCRIPT
 * ============================================================================
 *
 * Parent DocType:
 *     Receipts
 *
 * Child DocTypes:
 *     Receipts Reference
 *     Related Company Receipts
 *     Receipts Item Line
 *     Receipt Detail
 *
 * Main functionality:
 *     - Customer receipt processing
 *     - Opening / running customer balance
 *     - Invoice allocation
 *     - Outstanding invoice retrieval
 *     - Multi-line receipt totals
 *     - Related-company receipts
 *     - Foreign currency handling
 *     - Amortization
 *     - Deferred revenue schedule
 *     - AI Smart Allocation
 *     - Allocation preview
 *     - Receipt email notification
 *     - Allocation summary
 *     - Account / company queries
 *     - UI styling
 * ========================================================================== */


/* ============================================================================
 * PARENT DOCTYPE EVENTS
 * ========================================================================== */

frappe.ui.form.on("Receipts", {

    /* ------------------------------------------------------------------------
     * SETUP
     * ---------------------------------------------------------------------- */

    setup: function(frm) {

        // Amount in words should always be system-generated.
        frm.set_df_property(
            "amount_in_words",
            "read_only",
            1
        );

        set_account_queries(frm);
        set_cost_center_query(frm);
        setup_related_company_queries(frm);
    },


    /* ------------------------------------------------------------------------
     * ONLOAD
     * ---------------------------------------------------------------------- */

    onload: function(frm) {

        set_account_queries(frm);
        set_cost_center_query(frm);
        setup_related_company_queries(frm);

        // Initial calculations
        calculate_all_totals(frm);
        calculate_local_currency_amount(frm);

        // Update allocation summary
        update_allocation_summary(frm);

        // Opening balance
        if (
            frm.doc.customer_id &&
            frm.doc.transaction_date
        ) {
            frm.trigger("fetch_opening_balance");
        }
    },


    /* ------------------------------------------------------------------------
     * REFRESH
     * ---------------------------------------------------------------------- */

    refresh: function(frm) {

        // Re-apply queries
        set_account_queries(frm);
        set_cost_center_query(frm);
        setup_related_company_queries(frm);

        // Recalculate
        calculate_all_totals(frm);
        calculate_local_currency_amount(frm);
        update_allocation_summary(frm);

        // Amount in words is read-only
        frm.set_df_property(
            "amount_in_words",
            "read_only",
            1
        );

        // Apply UI styling after grid rendering
        setTimeout(function() {

            apply_zebra_striping(frm);
            style_buttons(frm);
            apply_field_styling(frm);

        }, 300);


        /* --------------------------------------------------------------------
         * SUBMITTED DOCUMENT
         * ------------------------------------------------------------------ */

        if (frm.doc.docstatus === 1) {

            // Submitted document is read-only by Frappe.
            // Do NOT manually change docstatus here.

            // Email button
            if (frm.doc.customer_id) {

                frm.add_custom_button(
                    __("Send Receipt Email"),
                    function() {
                        send_receipt_email(frm);
                    },
                    __("Actions")
                );

            }
        }


        /* --------------------------------------------------------------------
         * DRAFT DOCUMENT
         * ------------------------------------------------------------------ */

        if (frm.doc.docstatus === 0) {

            // Draft-specific functionality can be placed here.

        }


        /* --------------------------------------------------------------------
         * CANCELLED DOCUMENT
         * ------------------------------------------------------------------ */

        if (frm.doc.docstatus === 2) {

            // Cancelled document.
            // No editing or submission actions should be added here.

        }


        // Opening balance
        if (
            frm.doc.customer_id &&
            frm.doc.transaction_date
        ) {
            frm.trigger("fetch_opening_balance");
        }
    },


    /* ------------------------------------------------------------------------
     * TRANSACTION TYPE
     * ---------------------------------------------------------------------- */

    trans_type: function(frm) {

        handle_transaction_type_change(frm);

        calculate_all_totals(frm);
        frm.trigger("derive_balance");
    },


    /* ------------------------------------------------------------------------
     * CUSTOMER
     * ---------------------------------------------------------------------- */

    customer_id: function(frm) {

        if (frm.doc.customer_id) {

            // Clear one-off payer name
            frm.set_value("payer_name", "");

        }

        frm.trigger("fetch_opening_balance");
    },


    /* ------------------------------------------------------------------------
     * RECEIPT CURRENCY
     * ---------------------------------------------------------------------- */

    receipt_currency: function(frm) {

        handle_currency_change(frm);
        calculate_local_currency_amount(frm);
        frm.trigger("derive_balance");
    },


    /* ------------------------------------------------------------------------
     * COMPANY
     * ---------------------------------------------------------------------- */

    company: function(frm) {

        set_account_queries(frm);
        set_cost_center_query(frm);
        setup_related_company_queries(frm);

        handle_currency_change(frm);
        calculate_local_currency_amount(frm);

        if (
            frm.doc.customer_id &&
            frm.doc.transaction_date
        ) {
            frm.trigger("fetch_opening_balance");
        }
    },


    /* ------------------------------------------------------------------------
     * TRANSACTION DATE
     * ---------------------------------------------------------------------- */

    transaction_date: function(frm) {

        frm.trigger("fetch_opening_balance");
    },


    /* ------------------------------------------------------------------------
     * AMORTIZATION
     * ---------------------------------------------------------------------- */

    amortize: function(frm) {

        handle_amortization_toggle(frm);

        calculate_amortization_schedule(frm);
    },


    frequency: function(frm) {

        calculate_amortization_schedule(frm);
    },


    start_date: function(frm) {

        calculate_end_date(frm);
        calculate_amortization_schedule(frm);
    },


    no_of_days: function(frm) {

        calculate_end_date(frm);
        calculate_amortization_schedule(frm);
    },


    /* ------------------------------------------------------------------------
     * AMOUNTS
     * ---------------------------------------------------------------------- */

    amount_received: function(frm) {

        calculate_amortization_schedule(frm);
        calculate_local_currency_amount(frm);

        frm.trigger("derive_balance");
        update_allocation_summary(frm);
    },


    amount_received_in_fc: function(frm) {

        calculate_amortization_schedule(frm);
        calculate_local_currency_amount(frm);

        frm.trigger("derive_balance");
        update_allocation_summary(frm);
    },


    exchange_rate: function(frm) {

        calculate_amortization_schedule(frm);
        calculate_local_currency_amount(frm);

        frm.trigger("derive_balance");
        update_allocation_summary(frm);
    },


    /* ------------------------------------------------------------------------
     * ACCOUNT TO CREDIT
     * ---------------------------------------------------------------------- */

    account_to_credit: function(frm) {

        if (
            frm.doc.amortize &&
            frm.doc.account_to_credit
        ) {

            frm.set_value(
                "deferred_revenue_account",
                frm.doc.account_to_credit
            );
        }
    },


    /* ------------------------------------------------------------------------
     * BUTTONS
     * ---------------------------------------------------------------------- */

    get_outstanding_invoices: function(frm) {

        fetch_outstanding_invoices(frm);
    },


    ai_smart_allocation: function(frm) {

        run_ai_smart_allocation(frm);
    },


    preview_allocation: function(frm) {

        show_preview_allocation(frm);
    },


    /* ------------------------------------------------------------------------
     * BEFORE SAVE
     * ---------------------------------------------------------------------- */

    before_save: function(frm) {

        /*
         * IMPORTANT:
         * Do not change frm.doc.docstatus here.
         *
         * Frappe controls:
         *
         * 0 = Draft
         * 1 = Submitted
         * 2 = Cancelled
         */

        // Generate schedule only for draft documents.
        if (
            frm.doc.docstatus === 0 &&
            flt(frm.doc.charge_amount) > 0 &&
            cint(frm.doc.amortize) === 1
        ) {

            generate_amortization_schedule(frm);
        }

        // Totals
        calculate_all_totals(frm);

        // Balance
        frm.trigger("derive_balance");
    },


    /* ------------------------------------------------------------------------
     * BEFORE SUBMIT
     * ---------------------------------------------------------------------- */

    before_submit: function(frm) {

        /*
         * Recalculate all important values before submission.
         */

        calculate_all_totals(frm);
        calculate_local_currency_amount(frm);
        frm.trigger("derive_balance");

        if (
            cint(frm.doc.amortize) === 1 &&
            flt(frm.doc.charge_amount) > 0
        ) {

            generate_amortization_schedule(frm);
        }
    },


    /* ------------------------------------------------------------------------
     * AFTER SUBMIT
     * ---------------------------------------------------------------------- */

    on_submit: function(frm) {

        /*
         * DO NOT set docstatus manually.
         *
         * Frappe has already changed:
         *
         * frm.doc.docstatus = 1
         *
         * after successful server-side submission.
         */

        frm.reload_doc();
    },


    /* ------------------------------------------------------------------------
     * OPENING BALANCE
     * ---------------------------------------------------------------------- */

    fetch_opening_balance: function(frm) {

        if (
            !frm.doc.customer_id ||
            !frm.doc.transaction_date
        ) {
            return;
        }

        const company =
            frm.doc.company ||
            frappe.defaults.get_default("company");

        frappe.call({

            method:
                "ecclesia.api.customer_balance.get_customer_opening_balance",

            args: {

                customer: frm.doc.customer_id,

                company: company,

                transaction_date:
                    frm.doc.transaction_date,

                current_docname:
                    frm.doc.name || null
            },

            callback: function(r) {

                if (
                    r &&
                    r.message !== undefined &&
                    r.message !== null
                ) {

                    frm.set_value(
                        "opening_balance",
                        flt(r.message)
                    );

                    frm.trigger("derive_balance");
                }
            }
        });
    },


    /* ------------------------------------------------------------------------
     * DERIVE BALANCE
     * ---------------------------------------------------------------------- */

    derive_balance: function(frm) {

        let invoice_amount = 0;

        (frm.doc.receipt_detail || []).forEach(function(row) {

            invoice_amount += flt(row.total);

        });


        const opening_balance =
            flt(frm.doc.opening_balance);


        /*
         * Determine actual amount received in company/local currency.
         */

        let amount_paid = 0;

        if (
            frm.doc.amount_received !== undefined &&
            frm.doc.amount_received !== null &&
            frm.doc.amount_received !== ""
        ) {

            amount_paid =
                flt(frm.doc.amount_received);

        } else {

            amount_paid =
                flt(frm.doc.amount_received_in_fc) *
                flt(frm.doc.exchange_rate || 1);
        }


        /*
         * Customer statement style calculation:
         *
         * Opening Balance
         * + Current Invoice Amount
         * - Amount Received
         * = Balance Due
         */

        const balance_due =
            opening_balance +
            invoice_amount -
            amount_paid;


        frm.set_value(
            "invoice_amount",
            invoice_amount
        );

        frm.set_value(
            "balance_due",
            balance_due
        );
    }

});


/* ============================================================================
 * RECEIPTS REFERENCE CHILD TABLE
 * ========================================================================== */

frappe.ui.form.on("Receipts Reference", {

    allocated_amount: function(frm, cdt, cdn) {

        calculate_total_outstanding(frm);
        update_allocation_summary(frm);
    },


    outstanding_amount: function(frm) {

        calculate_total_outstanding(frm);
        update_allocation_summary(frm);
    },


    receipts_reference_add: function(frm) {

        calculate_total_outstanding(frm);
        update_allocation_summary(frm);
    },


    receipts_reference_remove: function(frm) {

        calculate_total_outstanding(frm);
        update_allocation_summary(frm);
    }
});


/* ============================================================================
 * RELATED COMPANY RECEIPTS
 * ========================================================================== */

frappe.ui.form.on("Related Company Receipts", {

    party: function(frm, cdt, cdn) {

        const row = locals[cdt][cdn];

        if (
            row &&
            row.party &&
            row.party_type
        ) {

            fetch_party_name(
                frm,
                cdt,
                cdn,
                row
            );
        }
    },


    related_company: function(frm) {

        setup_related_company_queries(frm);
    },


    trans_type: function(frm, cdt, cdn) {

        const row = locals[cdt][cdn];

        if (!row) {
            return;
        }


        // Clear existing party
        frappe.model.set_value(
            cdt,
            cdn,
            "party",
            ""
        );

        frappe.model.set_value(
            cdt,
            cdn,
            "party_name",
            ""
        );


        if (
            row.trans_type ===
            "Customer Receipt"
        ) {

            frappe.model.set_value(
                cdt,
                cdn,
                "party_type",
                "Customer"
            );

        } else {

            frappe.model.set_value(
                cdt,
                cdn,
                "party_type",
                "Account"
            );
        }


        setup_related_company_queries(frm);
    },


    amount: function(frm) {

        calculate_related_company_total(frm);
    },


    related_company_receipts_remove: function(frm) {

        calculate_related_company_total(frm);
    },


    form_render: function(frm) {

        setup_related_company_queries(frm);
    }

});


/* ============================================================================
 * RECEIPTS ITEM LINE
 * ========================================================================== */

frappe.ui.form.on("Receipts Item Line", {

    amount: function(frm) {

        calculate_multi_line_total(frm);
    },


    receipts_item_line_add: function(frm) {

        calculate_multi_line_total(frm);
    },


    receipts_item_line_remove: function(frm) {

        calculate_multi_line_total(frm);
    }

});


/* ============================================================================
 * RECEIPT DETAIL
 *
 * IMPORTANT:
 * This must be the ACTUAL CHILD DOCTYPE NAME.
 * If your child DocType is named differently, change it here.
 * ========================================================================== */

frappe.ui.form.on("Receipt Detail", {

    qty: function(frm, cdt, cdn) {

        calculate_row_total(
            frm,
            cdt,
            cdn
        );
    },


    unit_price: function(frm, cdt, cdn) {

        calculate_row_total(
            frm,
            cdt,
            cdn
        );
    },


    total: function(frm) {

        frm.trigger("derive_balance");
    },


    receipt_detail_add: function(frm) {

        frm.trigger("derive_balance");
    },


    receipt_detail_remove: function(frm) {

        frm.trigger("derive_balance");
    }

});


/* ============================================================================
 * UI STYLING
 * ========================================================================== */

function apply_zebra_striping(frm) {

    const tables = [

        "receipts_reference",

        "related_company_receipts",

        "receipts_item_line",

        "receipt_detail",

        "schedule_of_deferred_revenue"

    ];


    tables.forEach(function(table) {

        try {

            if (
                frm.fields_dict[table] &&
                frm.fields_dict[table].grid &&
                frm.fields_dict[table].grid.wrapper
            ) {

                frm.fields_dict[table]
                    .grid
                    .wrapper
                    .find(".grid-row")
                    .each(function(i, row) {

                        $(row).css(
                            "background-color",
                            i % 2 === 0
                                ? "#ffffff"
                                : "#f0f8ff"
                        );

                    });
            }

        } catch (e) {

            console.warn(
                "Zebra striping skipped:",
                table,
                e
            );

        }

    });

}


/* ============================================================================
 * BUTTON STYLING
 * ========================================================================== */

function style_buttons(frm) {

    style_form_button(
        frm,
        "ai_smart_allocation",
        "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
    );


    style_form_button(
        frm,
        "preview_allocation",
        "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)"
    );


    style_form_button(
        frm,
        "get_outstanding_invoices",
        "linear-gradient(135deg, #FA8BFF 0%, #2BD2FF 90%)"
    );

}


function style_form_button(frm, fieldname, background) {

    try {

        const field =
            frm.fields_dict[fieldname];

        if (
            !field ||
            !field.$input
        ) {
            return;
        }


        field.$input.css({

            background: background,

            color: "white",

            "font-weight": "bold",

            border: "none",

            padding: "10px 20px",

            "border-radius": "5px",

            cursor: "pointer",

            "font-size": "14px",

            transition: "all 0.3s ease",

            "box-shadow":
                "0 4px 6px rgba(0,0,0,0.1)"

        });


        field.$input.hover(

            function() {

                $(this).css({

                    transform:
                        "translateY(-2px)",

                    "box-shadow":
                        "0 6px 8px rgba(0,0,0,0.15)"

                });

            },

            function() {

                $(this).css({

                    transform:
                        "translateY(0)",

                    "box-shadow":
                        "0 4px 6px rgba(0,0,0,0.1)"

                });

            }

        );

    } catch (e) {

        console.warn(
            "Button styling skipped:",
            fieldname,
            e
        );

    }

}


/* ============================================================================
 * FIELD STYLING
 * ========================================================================== */

function apply_field_styling(frm) {

    const field_colors = {

        cost_center: "#90ee90",

        trans_type: "#87ceeb",

        transaction_date: "#fffacd",

        account_to_credit: "#90ee90",

        reference_no: "#87ceeb",

        amount_received: "#fffacd",

        amount_received_in_fc: "#fffacd",

        frequency: "#90ee90",

        end_date: "#87ceeb",

        charge_amount: "#fffacd",

        customer_id: "#90ee90",

        payer_name: "#87ceeb",

        mode_of_payment: "#fffacd"

    };


    Object.keys(field_colors).forEach(function(field) {

        try {

            if (
                frm.fields_dict[field] &&
                frm.fields_dict[field].$input
            ) {

                frm.fields_dict[field]
                    .$input
                    .css(
                        "background-color",
                        field_colors[field]
                    );
            }

        } catch (e) {

            console.warn(
                "Field styling skipped:",
                field
            );

        }

    });

}


/* ============================================================================
 * ACCOUNT QUERIES
 * ========================================================================== */

function set_account_queries(frm) {

    const account_fields = [

        "account_to_credit",

        "deferred_revenue_account",

        "revenue_account"

    ];


    account_fields.forEach(function(field) {

        if (!frm.fields_dict[field]) {
            return;
        }


        frm.set_query(field, function() {

            return {

                filters: {

                    is_group: 0,

                    company: frm.doc.company

                }

            };

        });

    });

}


/* ============================================================================
 * COST CENTER QUERY
 * ========================================================================== */

function set_cost_center_query(frm) {

    if (!frm.fields_dict.cost_center) {
        return;
    }


    frm.set_query(
        "cost_center",
        function() {

            return {

                filters: {

                    is_group: 0,

                    company: frm.doc.company

                }

            };

        }
    );

}


/* ============================================================================
 * TRANSACTION TYPE
 * ========================================================================== */

function handle_transaction_type_change(frm) {

    if (
        [
            "Customer Receipt",
            "Receive from One-Off"
        ].includes(frm.doc.trans_type)
    ) {

        frm.set_value(
            "account_to_credit",
            ""
        );

        if (
            frm.doc.trans_type ===
            "Receive from One-Off"
        ) {

            /*
             * WARNING:
             * This hardcoded customer should ideally be
             * moved to configuration.
             */

            frm.set_value(
                "customer_id",
                "CUST-2023-00001"
            );

        } else {

            frm.set_value(
                "payer_name",
                ""
            );

        }


        frm.set_df_property(
            "account_to_credit",
            "read_only",
            0
        );


    } else if (
        frm.doc.trans_type ===
        "Transfer In"
    ) {

        if (!frm.doc.company) {
            return;
        }


        frappe.db.get_value(
            "Company",
            frm.doc.company,
            "custom_default_interbank_transfer"
        ).then(function(r) {

            if (
                r.message &&
                r.message.custom_default_interbank_transfer
            ) {

                frm.set_value(
                    "account_to_credit",
                    r.message.custom_default_interbank_transfer
                );

                frm.set_df_property(
                    "account_to_credit",
                    "read_only",
                    1
                );

            }

        });


    } else {

        frm.set_df_property(
            "account_to_credit",
            "read_only",
            0
        );

    }

}


/* ============================================================================
 * CURRENCY
 * ========================================================================== */

function handle_currency_change(frm) {

    if (!frm.doc.company) {
        return;
    }


    frappe.db.get_value(
        "Company",
        frm.doc.company,
        "default_currency"
    ).then(function(r) {

        if (
            !r.message ||
            !r.message.default_currency
        ) {
            return;
        }


        const company_currency =
            r.message.default_currency;


        const is_foreign =
            frm.doc.receipt_currency !==
            company_currency;


        frm.toggle_display(
            "amount_received",
            !is_foreign
        );

        frm.toggle_display(
            "amount_received_in_fc",
            is_foreign
        );

        frm.toggle_display(
            "exchange_rate",
            is_foreign
        );

        frm.toggle_reqd(
            "exchange_rate",
            is_foreign
        );

    });

}


/* ============================================================================
 * AMORTIZATION TOGGLE
 * ========================================================================== */

function handle_amortization_toggle(frm) {

    if (
        cint(frm.doc.amortize) === 0
    ) {

        frm.set_value(
            "frequency",
            ""
        );

        frm.set_value(
            "start_date",
            ""
        );

        frm.set_value(
            "end_date",
            ""
        );

        frm.set_value(
            "deferred_revenue_account",
            ""
        );

        frm.set_value(
            "revenue_account",
            ""
        );

        frm.set_value(
            "no_of_days",
            ""
        );

        frm.set_value(
            "charge_amount",
            0
        );

        frm.clear_table(
            "schedule_of_deferred_revenue"
        );

        frm.refresh_field(
            "schedule_of_deferred_revenue"
        );

    }

}


/* ============================================================================
 * END DATE
 * ========================================================================== */

function calculate_end_date(frm) {

    if (
        frm.doc.start_date &&
        flt(frm.doc.no_of_days) > 0
    ) {

        const end_date =
            frappe.datetime.add_days(
                frm.doc.start_date,
                cint(frm.doc.no_of_days)
            );


        frm.set_value(
            "end_date",
            end_date
        );

    }

}


/* ============================================================================
 * AMORTIZATION CALCULATION
 * ========================================================================== */

function calculate_amortization_schedule(frm) {

    if (
        !frm.doc.start_date ||
        !frm.doc.end_date ||
        !frm.doc.frequency
    ) {
        return;
    }


    const days_diff =
        frappe.datetime.get_day_diff(
            frm.doc.end_date,
            frm.doc.start_date
        );


    if (days_diff <= 0) {
        return;
    }


    const amount =
        flt(frm.doc.amount_received) ||
        (
            flt(frm.doc.amount_received_in_fc) *
            flt(frm.doc.exchange_rate || 1)
        );


    if (
        amount <= 0
    ) {
        return;
    }


    let period_days = 30;


    if (
        frm.doc.frequency === "Quarterly"
    ) {

        period_days = 90;

    }


    const no_of_periods =
        Math.ceil(
            days_diff / period_days
        );


    if (no_of_periods <= 0) {
        return;
    }


    const charge_amount =
        amount / no_of_periods;


    frm.set_value(
        "charge_amount",
        charge_amount
    );

}


/* ============================================================================
 * GENERATE AMORTIZATION SCHEDULE
 * ========================================================================== */

function generate_amortization_schedule(frm) {

    if (
        !frm.doc.start_date ||
        !frm.doc.end_date ||
        !frm.doc.frequency ||
        flt(frm.doc.charge_amount) <= 0
    ) {
        return;
    }


    const period_months =
        frm.doc.frequency === "Monthly"
            ? 1
            : 3;


    const days_diff =
        frappe.datetime.get_day_diff(
            frm.doc.end_date,
            frm.doc.start_date
        );


    if (days_diff <= 0) {
        return;
    }


    const no_of_periods =
        Math.ceil(
            days_diff /
            (30 * period_months)
        );


    if (no_of_periods <= 0) {
        return;
    }


    frm.clear_table(
        "schedule_of_deferred_revenue"
    );


    for (
        let i = 0;
        i < no_of_periods;
        i++
    ) {

        const posting_date =
            frappe.datetime.add_months(
                frm.doc.start_date,
                i * period_months
            );


        /*
         * Do not create entries after end date.
         */

        if (
            frappe.datetime.get_day_diff(
                posting_date,
                frm.doc.end_date
            ) > 0
        ) {
            break;
        }


        const row =
            frm.add_child(
                "schedule_of_deferred_revenue"
            );


        row.date =
            posting_date;


        row.title =
            frm.doc.payer_name ||
            frm.doc.customer_name ||
            frm.doc.customer_id ||
            "";


        row.amount =
            frm.doc.charge_amount;


        row.transaction_description =
            `${frm.doc.frequency} amortization entry`;


        row.frequency =
            frm.doc.frequency;


        row.period =
            no_of_periods;


        row.account_to_debit =
            frm.doc.deferred_revenue_account;


        row.account_to_credit =
            frm.doc.revenue_account;

    }


    frm.refresh_field(
        "schedule_of_deferred_revenue"
    );

}


/* ============================================================================
 * OUTSTANDING INVOICES
 * ========================================================================== */

function fetch_outstanding_invoices(frm) {

    if (!frm.doc.customer_id) {

        frappe.msgprint({
            title: __("Customer Required"),
            message:
                __("Please select a customer first."),
            indicator: "orange"
        });

        return;
    }


    frappe.call({

        method:
            "frappe.client.get_list",

        args: {

            doctype:
                "Sales Invoice",

            fields: [

                "posting_date",

                "customer",

                "customer_name",

                "due_date",

                "currency",

                "total",

                "name",

                "outstanding_amount",

                "grand_total",

                "project",

                "payment_terms_template",

                "base_total",

                "docstatus"

            ],

            filters: [

                [
                    "customer",
                    "=",
                    frm.doc.customer_id
                ],

                [
                    "docstatus",
                    "=",
                    1
                ],

                [
                    "outstanding_amount",
                    ">",
                    0
                ]

            ],

            limit_page_length:
                1000,

            order_by:
                "due_date asc, posting_date asc"

        },


        freeze: true,

        freeze_message:
            __("Loading outstanding invoices..."),


        callback: function(response) {

            const invoices =
                response.message || [];


            if (
                invoices.length === 0
            ) {

                frappe.msgprint({
                    title:
                        __("No Outstanding Invoices"),
                    message:
                        __("No outstanding invoices were found for this customer."),
                    indicator:
                        "orange"
                });

                return;
            }


            frm.clear_table(
                "receipts_reference"
            );


            invoices.forEach(
                function(invoice) {

                    const row =
                        frm.add_child(
                            "receipts_reference"
                        );


                    row.date =
                        invoice.posting_date;


                    row.reference_doctype =
                        "Sales Invoice";


                    row.reference_name =
                        invoice.name;


                    row.due_date =
                        invoice.due_date;


                    row.bill_no =
                        invoice.name;


                    row.payment_term =
                        invoice.payment_terms_template ||
                        "";


                    row.total_amount =
                        invoice.grand_total;


                    row.outstanding_amount =
                        invoice.outstanding_amount;


                    row.allocated_amount =
                        0;


                    row.exchange_rate =
                        1;


                    row.exchange_gain_loss =
                        0;

                }
            );


            frm.refresh_field(
                "receipts_reference"
            );


            calculate_total_outstanding(frm);
            update_allocation_summary(frm);


            frappe.show_alert({

                message:
                    __(
                        "Loaded {0} outstanding invoices",
                        [invoices.length]
                    ),

                indicator:
                    "green"

            }, 5);

        }

    });

}


/* ============================================================================
 * PARTY NAME
 * ========================================================================== */

function fetch_party_name(
    frm,
    cdt,
    cdn,
    row
) {

    let doctype;
    let fieldname;


    if (
        row.party_type ===
        "Supplier"
    ) {

        doctype =
            "Supplier";

        fieldname =
            "supplier_name";

    } else {

        doctype =
            "Customer";

        fieldname =
            "customer_name";
    }


    frappe.db.get_value(
        doctype,
        row.party,
        fieldname
    ).then(function(r) {

        if (
            r.message &&
            r.message[fieldname]
        ) {

            frappe.model.set_value(
                cdt,
                cdn,
                "party_name",
                r.message[fieldname]
            );

        }

    });

}


/* ============================================================================
 * RELATED COMPANY QUERIES
 * ========================================================================== */

function setup_related_company_queries(frm) {

    const field =
        frm.fields_dict[
            "related_company_receipts"
        ];


    if (
        !field ||
        !field.grid
    ) {
        return;
    }


    /* ------------------------------------------------------------------------
     * RELATED COMPANY ACCOUNT
     * ---------------------------------------------------------------------- */

    const account_field =
        field.grid.get_field(
            "related_company_account"
        );


    if (account_field) {

        account_field.get_query =
            function(doc, cdt, cdn) {

                const row =
                    locals[cdt] &&
                    locals[cdt][cdn];


                if (!row) {
                    return {
                        filters: {}
                    };
                }


                if (
                    !row.related_company
                ) {

                    frappe.msgprint(
                        __(
                            "Please select Related Company first."
                        )
                    );

                    return {
                        filters: {}
                    };
                }


                return {

                    filters: {

                        company:
                            row.related_company,

                        is_group:
                            0,

                        root_type:
                            "Asset"

                    }

                };

            };

    }


    /* ------------------------------------------------------------------------
     * PARTY
     * ---------------------------------------------------------------------- */

    const party_field =
        field.grid.get_field(
            "party"
        );


    if (party_field) {

        party_field.get_query =
            function(doc, cdt, cdn) {

                const row =
                    locals[cdt] &&
                    locals[cdt][cdn];


                if (!row) {
                    return {
                        filters: {}
                    };
                }


                if (
                    !row.related_company
                ) {

                    return {
                        filters: {}
                    };

                }


                if (
                    row.trans_type ===
                    "Customer Receipt"
                ) {

                    return {

                        filters: {

                            disabled:
                                0

                        }

                    };

                }


                return {

                    filters: {

                        company:
                            row.related_company,

                        is_group:
                            0

                    }

                };

            };

    }


    /* ------------------------------------------------------------------------
     * COST CENTER
     * ---------------------------------------------------------------------- */

    const cost_center_field =
        field.grid.get_field(
            "cost_center"
        );


    if (cost_center_field) {

        cost_center_field.get_query =
            function(doc, cdt, cdn) {

                const row =
                    locals[cdt] &&
                    locals[cdt][cdn];


                if (
                    !row ||
                    !row.related_company
                ) {

                    return {
                        filters: {}
                    };

                }


                return {

                    filters: {

                        company:
                            row.related_company,

                        is_group:
                            0

                    }

                };

            };

    }

}


/* ============================================================================
 * TOTAL CALCULATIONS
 * ========================================================================== */

function calculate_all_totals(frm) {

    calculate_total_outstanding(frm);

    calculate_related_company_total(frm);

    calculate_multi_line_total(frm);

    update_allocation_summary(frm);

}


/* ---------------------------------------------------------------------------
 * RECEIPTS REFERENCE TOTAL
 * ------------------------------------------------------------------------- */

function calculate_total_outstanding(frm) {

    let total = 0;


    (frm.doc.receipts_reference || [])
        .forEach(function(row) {

            total +=
                flt(row.allocated_amount);

        });


    frm.set_value(
        "total_outstanding_invoice",
        total
    );

}


/* ---------------------------------------------------------------------------
 * RELATED COMPANY TOTAL
 * ------------------------------------------------------------------------- */

function calculate_related_company_total(frm) {

    let total = 0;


    (frm.doc.related_company_receipts || [])
        .forEach(function(row) {

            total +=
                flt(row.amount);

        });


    frm.set_value(
        "total_rcoy",
        total
    );

}


/* ---------------------------------------------------------------------------
 * MULTI-LINE TOTAL
 * ------------------------------------------------------------------------- */

function calculate_multi_line_total(frm) {

    let total = 0;


    (frm.doc.receipts_item_line || [])
        .forEach(function(row) {

            total +=
                flt(row.amount);

        });


    frm.set_value(
        "total",
        total
    );

}


/* ============================================================================
 * LOCAL CURRENCY
 * ========================================================================== */

function calculate_local_currency_amount(frm) {

    if (!frm.doc.company) {
        return;
    }


    frappe.db.get_value(
        "Company",
        frm.doc.company,
        "default_currency"
    ).then(function(r) {

        if (
            !r.message ||
            !r.message.default_currency
        ) {
            return;
        }


        const company_currency =
            r.message.default_currency;


        if (
            frm.doc.receipt_currency ===
            company_currency
        ) {

            frm.set_value(
                "local_currency_amount",
                flt(frm.doc.amount_received)
            );

        } else {

            const exchange_rate =
                flt(
                    frm.doc.exchange_rate
                ) || 1;


            const amount_fc =
                flt(
                    frm.doc.amount_received_in_fc
                );


            frm.set_value(
                "local_currency_amount",
                amount_fc * exchange_rate
            );

        }

    });

}


/* ============================================================================
 * AI SMART ALLOCATION
 * ========================================================================== */

function run_ai_smart_allocation(frm) {

    if (!frm.doc.customer_id) {

        frappe.msgprint({

            title:
                __("Customer Required"),

            message:
                __(
                    "Please select a customer before running Smart Allocation."
                ),

            indicator:
                "orange"

        });

        return;
    }


    const receipt_amount =
        flt(
            frm.doc.local_currency_amount
        ) ||
        flt(
            frm.doc.amount_received
        ) ||
        (
            flt(
                frm.doc.amount_received_in_fc
            ) *
            flt(
                frm.doc.exchange_rate || 1
            )
        );


    if (receipt_amount <= 0) {

        frappe.msgprint({

            title:
                __("Amount Required"),

            message:
                __(
                    "Please enter the receipt amount before running Smart Allocation."
                ),

            indicator:
                "orange"

        });

        return;
    }


    frappe.call({

        method:
            "ecclesia.ecclesia.doctype.receipts.receipts.ai_smart_allocation",

        args: {

            doc_name:
                frm.doc.name

        },

        freeze:
            true,

        freeze_message:
            __(
                "AI is analyzing invoices and allocating payments..."
            ),


        callback:
            function(r) {

                if (
                    r.exc ||
                    !r.message
                ) {
                    return;
                }


                const result =
                    r.message;


                frm.reload_doc()
                    .then(function() {

                        const remaining =
                            flt(
                                result.remaining_amount
                            );


                        const message = `

                            <div
                                style="
                                    padding:15px;
                                    font-family:Arial,sans-serif;
                                "
                            >

                                <h4
                                    style="
                                        color:#27ae60;
                                        margin-bottom:15px;
                                    "
                                >

                                    <i
                                        class="fa fa-check-circle"
                                    ></i>

                                    AI Allocation Completed Successfully

                                </h4>


                                <table
                                    style="
                                        width:100%;
                                        border-collapse:collapse;
                                    "
                                >

                                    <tr>

                                        <td
                                            style="
                                                padding:8px;
                                                border-bottom:1px solid #ddd;
                                            "
                                        >
                                            <strong>
                                                Invoices Matched:
                                            </strong>
                                        </td>

                                        <td
                                            style="
                                                padding:8px;
                                                border-bottom:1px solid #ddd;
                                            "
                                        >
                                            ${result.invoices_matched || 0}
                                        </td>

                                    </tr>


                                    <tr>

                                        <td
                                            style="
                                                padding:8px;
                                                border-bottom:1px solid #ddd;
                                            "
                                        >
                                            <strong>
                                                Total Allocated:
                                            </strong>
                                        </td>

                                        <td
                                            style="
                                                padding:8px;
                                                border-bottom:1px solid #ddd;
                                                color:#27ae60;
                                                font-weight:bold;
                                            "
                                        >
                                            ${format_currency(
                                                result.total_allocated || 0,
                                                frm.doc.receipt_currency
                                            )}
                                        </td>

                                    </tr>


                                    <tr>

                                        <td
                                            style="
                                                padding:8px;
                                            "
                                        >
                                            <strong>
                                                Remaining Amount:
                                            </strong>
                                        </td>

                                        <td
                                            style="
                                                padding:8px;
                                                color:${remaining > 0
                                                    ? "#f39c12"
                                                    : "#27ae60"};
                                                font-weight:bold;
                                            "
                                        >
                                            ${format_currency(
                                                remaining,
                                                frm.doc.receipt_currency
                                            )}
                                        </td>

                                    </tr>

                                </table>

                            </div>

                        `;


                        frappe.msgprint({

                            title:
                                __(
                                    "AI Smart Allocation Results"
                                ),

                            message:
                                message,

                            indicator:
                                "green",

                            primary_action: {

                                label:
                                    __(
                                        "Preview Allocation"
                                    ),

                                action:
                                    function() {

                                        show_preview_allocation(
                                            frm
                                        );

                                    }

                            }

                        });

                    });

            }

    });

}


/* ============================================================================
 * PREVIEW ALLOCATION
 * ========================================================================== */

function show_preview_allocation(frm) {

    if (
        !frm.doc.receipts_reference ||
        frm.doc.receipts_reference.length === 0
    ) {

        frappe.msgprint({

            title:
                __("No Allocations"),

            message:
                __(
                    "No invoice allocations found. Please run AI Smart Allocation or add invoices manually."
                ),

            indicator:
                "orange"

        });

        return;
    }


    /*
     * For a NEW unsaved document, the server may not be able
     * to retrieve the document by name.
     */

    if (
        !frm.doc.name ||
        frm.is_new()
    ) {

        frappe.msgprint({

            title:
                __("Save Required"),

            message:
                __(
                    "Please save the receipt before opening the allocation preview."
                ),

            indicator:
                "orange"

        });

        return;
    }


    frappe.call({

        method:
            "ecclesia.ecclesia.doctype.receipts.receipts.preview_allocation",

        args: {

            doc_name:
                frm.doc.name

        },

        freeze:
            true,

        freeze_message:
            __(
                "Preparing allocation preview..."
            ),


        callback:
            function(r) {

                if (
                    r.exc ||
                    !r.message
                ) {
                    return;
                }


                const dialog =
                    new frappe.ui.Dialog({

                        title:
                            __(
                                "Invoice Allocation Preview"
                            ),

                        size:
                            "extra-large",

                        fields: [

                            {

                                fieldtype:
                                    "HTML",

                                fieldname:
                                    "preview_html"

                            }

                        ],

                        primary_action_label:
                            __("Close"),

                        primary_action:
                            function() {

                                dialog.hide();

                            }

                    });


                dialog.fields_dict
                    .preview_html
                    .$wrapper
                    .html(r.message);


                dialog.show();

            }

    });

}


/* ============================================================================
 * SEND RECEIPT EMAIL
 * ========================================================================== */

function send_receipt_email(frm) {

    if (
        !frm.doc.name ||
        frm.doc.docstatus !== 1
    ) {

        frappe.msgprint({

            title:
                __("Submission Required"),

            message:
                __(
                    "Only submitted receipts can be emailed."
                ),

            indicator:
                "orange"

        });

        return;
    }


    frappe.call({

        method:
            "ecclesia.ecclesia.doctype.receipts.receipts.send_internal_receipt_notification",

        args: {

            doc_name:
                frm.doc.name

        },

        freeze:
            true,

        freeze_message:
            __(
                "Sending receipt email..."
            ),


        callback:
            function(r) {

                if (
                    !r.exc
                ) {

                    frappe.show_alert({

                        message:
                            __(
                                "Receipt email sent successfully."
                            ),

                        indicator:
                            "green"

                    }, 5);

                }

            }

    });

}


/* ============================================================================
 * ALLOCATION SUMMARY
 * ========================================================================== */

function update_allocation_summary(frm) {

    if (
        !frm.fields_dict.allocation_summary_html
    ) {
        return;
    }


    const rows =
        frm.doc.receipts_reference || [];


    if (
        rows.length === 0
    ) {

        frm.fields_dict
            .allocation_summary_html
            .$wrapper
            .html(
                `
                    <div class="alert alert-info">
                        No invoice allocations yet.
                    </div>
                `
            );

        return;
    }


    let total_allocated = 0;

    let total_outstanding = 0;

    let fully_paid_count = 0;


    rows.forEach(function(row) {

        const allocated =
            flt(
                row.allocated_amount
            );


        const outstanding =
            flt(
                row.outstanding_amount
            );


        total_allocated +=
            allocated;


        total_outstanding +=
            outstanding;


        if (
            outstanding > 0 &&
            allocated >= outstanding
        ) {

            fully_paid_count++;

        }

    });


    const amount_received =
        flt(
            frm.doc.local_currency_amount
        ) ||
        flt(
            frm.doc.amount_received
        ) ||
        (
            flt(
                frm.doc.amount_received_in_fc
            ) *
            flt(
                frm.doc.exchange_rate || 1
            )
        );


    const remaining =
        amount_received -
        total_allocated;


    const remaining_color =
        remaining > 0
            ? "#ffe066"
            : "#a5d8ff";


    const html = `

        <div
            style="
                background:
                    linear-gradient(
                        135deg,
                        #667eea 0%,
                        #764ba2 100%
                    );

                color:white;

                padding:20px;

                border-radius:10px;

                margin:10px 0;
            "
        >

            <h4
                style="
                    margin:0 0 15px 0;
                    font-size:18px;
                "
            >
                Allocation Summary
            </h4>


            <div
                style="
                    display:grid;
                    grid-template-columns:
                        repeat(4,1fr);
                    gap:15px;
                "
            >

                <div style="text-align:center;">

                    <div
                        style="
                            font-size:12px;
                            opacity:.9;
                        "
                    >
                        Invoices
                    </div>

                    <div
                        style="
                            font-size:24px;
                            font-weight:bold;
                            margin-top:5px;
                        "
                    >
                        ${rows.length}
                    </div>

                </div>


                <div style="text-align:center;">

                    <div
                        style="
                            font-size:12px;
                            opacity:.9;
                        "
                    >
                        Fully Paid
                    </div>

                    <div
                        style="
                            font-size:24px;
                            font-weight:bold;
                            margin-top:5px;
                        "
                    >
                        ${fully_paid_count}
                    </div>

                </div>


                <div style="text-align:center;">

                    <div
                        style="
                            font-size:12px;
                            opacity:.9;
                        "
                    >
                        Allocated
                    </div>

                    <div
                        style="
                            font-size:24px;
                            font-weight:bold;
                            margin-top:5px;
                        "
                    >
                        ${format_currency(
                            total_allocated,
                            frm.doc.receipt_currency
                        )}
                    </div>

                </div>


                <div style="text-align:center;">

                    <div
                        style="
                            font-size:12px;
                            opacity:.9;
                        "
                    >
                        Remaining
                    </div>

                    <div
                        style="
                            font-size:24px;
                            font-weight:bold;
                            margin-top:5px;
                            color:${remaining_color};
                        "
                    >
                        ${format_currency(
                            remaining,
                            frm.doc.receipt_currency
                        )}
                    </div>

                </div>

            </div>

        </div>

    `;


    frm.fields_dict
        .allocation_summary_html
        .$wrapper
        .html(html);

}


/* ============================================================================
 * FORMAT CURRENCY
 * ========================================================================== */

function format_currency(
    value,
    currency
) {

    return (
        format_number(
            flt(value),
            null,
            2
        ) +
        " " +
        (currency || "")
    );

}


/* ============================================================================
 * RECEIPT DETAIL ROW TOTAL
 * ========================================================================== */

function calculate_row_total(
    frm,
    cdt,
    cdn
) {

    const row =
        locals[cdt] &&
        locals[cdt][cdn];


    if (!row) {
        return;
    }


    const total =
        flt(row.qty) *
        flt(row.unit_price);


    frappe.model.set_value(
        cdt,
        cdn,
        "total",
        total
    ).then(function() {

        frm.trigger(
            "derive_balance"
        );

    });

}