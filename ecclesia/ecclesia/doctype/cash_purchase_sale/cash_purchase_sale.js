// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

// ============================================================================
// CASH PURCHASE SALE - CLIENT SCRIPT
// ============================================================================

frappe.ui.form.on('Cash Purchase Sale', {

    onload: function(frm) {
        if (frm.is_new()) {
            frm.set_value('transaction_date', frappe.datetime.get_today());
        }
    },

    refresh: function(frm) {
        recalculate_purchase_totals(frm);
        recalculate_sales_totals(frm);
    },

    transaction_type: function(frm) {
        // Nothing to compute here — visibility is handled by depends_on.
        // Just make sure totals reflect whichever tab is now active.
        recalculate_purchase_totals(frm);
        recalculate_sales_totals(frm);
    },

    // ------------------------------------------------------------------
    // PURCHASE TAB
    // ------------------------------------------------------------------

    apply_withholding_tax_purchase: function(frm) {
        if (!frm.doc.apply_withholding_tax_purchase) {
            frm.set_value('wht_rate_purchase', 0);
            frm.set_value('wht_amount_purchase', 0);
        }
        recalculate_purchase_totals(frm);
    },

    apply_vat_deduction_purchase: function(frm) {
        if (!frm.doc.apply_vat_deduction_purchase) {
            frm.set_value('vat_rate_purchase', 0);
            frm.set_value('vat_amount_purchase', 0);
        }
        recalculate_purchase_totals(frm);
    },

    wht_rate_purchase: function(frm) {
        recalculate_purchase_totals(frm);
    },

    vat_rate_purchase: function(frm) {
        recalculate_purchase_totals(frm);
    },

    // ------------------------------------------------------------------
    // SALES TAB
    // ------------------------------------------------------------------

    apply_withholding_tax_sales: function(frm) {
        if (!frm.doc.apply_withholding_tax_sales) {
            frm.set_value('wht_rate_sales', 0);
            frm.set_value('wht_amount_sales', 0);
        }
        recalculate_sales_totals(frm);
    },

    apply_vat_deduction_sales: function(frm) {
        if (!frm.doc.apply_vat_deduction_sales) {
            frm.set_value('vat_rate_sales', 0);
            frm.set_value('vat_amount_sales', 0);
        }
        recalculate_sales_totals(frm);
    },

    wht_rate_sales: function(frm) {
        recalculate_sales_totals(frm);
    },

    vat_rate_sales: function(frm) {
        recalculate_sales_totals(frm);
    },

    // ------------------------------------------------------------------
    // VALIDATE
    // ------------------------------------------------------------------

    validate: function(frm) {
        if (frm.doc.transaction_type === 'Cash Purchase') {
            if (!frm.doc.purchase_items || frm.doc.purchase_items.length === 0) {
                frappe.msgprint({
                    title: __('Validation Error'),
                    indicator: 'red',
                    message: __('Please add at least one item under Items Purchased')
                });
                frappe.validated = false;
                return false;
            }
        }

        if (frm.doc.transaction_type === 'Cash Sale') {
            if (!frm.doc.sales_items || frm.doc.sales_items.length === 0) {
                frappe.msgprint({
                    title: __('Validation Error'),
                    indicator: 'red',
                    message: __('Please add at least one item under Items Sold')
                });
                frappe.validated = false;
                return false;
            }
        }

        return true;
    },

    before_save: function(frm) {
        recalculate_purchase_totals(frm);
        recalculate_sales_totals(frm);
    },

    purchase_items_remove: function(frm) {
        recalculate_purchase_totals(frm);
    },

    sales_items_remove: function(frm) {
        recalculate_sales_totals(frm);
    }
});

// ============================================================================
// PURCHASE / SALES ITEM TABLE (shared child doctype)
// ============================================================================

frappe.ui.form.on('Cash Transaction Item', {
    qty: function(frm, cdt, cdn) {
        calculate_item_amount(frm, cdt, cdn);
    },
    rate: function(frm, cdt, cdn) {
        calculate_item_amount(frm, cdt, cdn);
    }
});

function calculate_item_amount(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    const amount = flt(row.qty) * flt(row.rate);
    frappe.model.set_value(cdt, cdn, 'amount', amount);

    if (row.parentfield === 'purchase_items') {
        recalculate_purchase_totals(frm);
    } else if (row.parentfield === 'sales_items') {
        recalculate_sales_totals(frm);
    }
}

// ============================================================================
// TOTALS + TAX CALCULATION
// ============================================================================

function recalculate_purchase_totals(frm) {
    let total = 0;
    (frm.doc.purchase_items || []).forEach(row => {
        total += flt(row.amount);
    });
    frm.set_value('purchase_total', total);

    let wht = 0;
    let vat = 0;

    if (frm.doc.apply_withholding_tax_purchase && frm.doc.wht_rate_purchase) {
        wht = total * (flt(frm.doc.wht_rate_purchase) / 100);
    }
    frm.set_value('wht_amount_purchase', wht);

    if (frm.doc.apply_vat_deduction_purchase && frm.doc.vat_rate_purchase) {
        vat = total * (flt(frm.doc.vat_rate_purchase) / 100);
    }
    frm.set_value('vat_amount_purchase', vat);

    frm.set_value('net_payable', total - wht - vat);
}

function recalculate_sales_totals(frm) {
    let total = 0;
    (frm.doc.sales_items || []).forEach(row => {
        total += flt(row.amount);
    });
    frm.set_value('sales_total', total);

    let wht = 0;
    let vat = 0;

    if (frm.doc.apply_withholding_tax_sales && frm.doc.wht_rate_sales) {
        wht = total * (flt(frm.doc.wht_rate_sales) / 100);
    }
    frm.set_value('wht_amount_sales', wht);

    if (frm.doc.apply_vat_deduction_sales && frm.doc.vat_rate_sales) {
        vat = total * (flt(frm.doc.vat_rate_sales) / 100);
    }
    frm.set_value('vat_amount_sales', vat);

    frm.set_value('net_receivable', total - wht - vat);
}