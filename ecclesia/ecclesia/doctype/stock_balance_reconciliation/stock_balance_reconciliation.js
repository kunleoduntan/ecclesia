frappe.ui.form.on('Stock Balance Reconciliation', {

    // ─── ON LOAD ──────────────────────────────────────────────────
    onload(frm) {
        frm.set_query('warehouse', () => ({
            filters: { is_group: 0 }
        }));

        frm.set_query('item_code', 'items', () => ({
            filters: { is_stock_item: 1, disabled: 0 }
        }));

        if (frm.is_new()) {
            frm.set_value('reconciliation_date', frappe.datetime.get_today());
            frm.set_value('prepared_by', frappe.session.user);
        }
    },

    // ─── REFRESH ──────────────────────────────────────────────────
    refresh(frm) {
        frm.page.clear_custom_actions();

        // create_stock_entry checkbox — only visible on Draft
        frm.set_df_property('create_stock_entry', 'hidden', frm.doc.docstatus !== 0 ? 1 : 0);

        if (frm.doc.docstatus === 0) {
            // ── Tools group ──────────────────────────────────────
            frm.add_custom_button(__('Fetch Stock Balance'), () => {
                frm.events.fetch_stock_balance(frm);
            }, __('Tools'));

            frm.add_custom_button(__('Import from CSV'), () => {
                frm.events.import_from_csv(frm);
            }, __('Tools'));

            frm.add_custom_button(__('Recalculate'), () => {
                frm.events.recalculate_all(frm);
            }, __('Tools'));

            frm.add_custom_button(__('Download Template'), () => {
                frm.events.download_template(frm);
            }, __('Tools'));
        }

        // View Stock Entry button — Draft or Submitted, if reference exists
        if (frm.doc.stock_entry_reference) {
            const btn_label = frm.doc.docstatus === 0
                ? __('View Draft Stock Entry')
                : __('View Stock Entry');

            frm.add_custom_button(btn_label, () => {
                frappe.set_route('Form', 'Stock Entry', frm.doc.stock_entry_reference);
            }).addClass('btn-success');
        }

        frm.events.render_summary_dashboard(frm);
    },

    // ─── DATE / WAREHOUSE CHANGE ─────────────────────────────────
    reconciliation_date(frm) {
        if (frm.doc.items && frm.doc.items.length > 0) {
            frappe.confirm(
                __('Date changed. Do you want to refresh stock balances from the ledger?'),
                () => frm.events.fetch_stock_balance(frm)
            );
        }
    },

    warehouse(frm) {
        if (frm.doc.items && frm.doc.items.length > 0) {
            frappe.confirm(
                __('Warehouse changed. Do you want to refresh stock balances?'),
                () => frm.events.fetch_stock_balance(frm)
            );
        }
    },

    // ─── CREATE STOCK ENTRY CHECKBOX CHANGE ──────────────────────
    create_stock_entry(frm) {
        const msg = frm.doc.create_stock_entry
            ? __('A draft Stock Entry (delta-based) will be created on Submit for you to review and post manually.')
            : __('Stock Reconciliation will be posted directly on Submit using the ERPNext stock engine.');

        const indicator = frm.doc.create_stock_entry ? 'blue' : 'green';

        frappe.show_alert({ message: msg, indicator: indicator }, 6);
    },

    // ─── FETCH STOCK BALANCE ─────────────────────────────────────
    fetch_stock_balance(frm) {
        if (!frm.doc.warehouse) {
            frappe.msgprint(__('Please select a Warehouse first.'));
            return;
        }
        if (!frm.doc.reconciliation_date) {
            frappe.msgprint(__('Please set a Reconciliation Date first.'));
            return;
        }
        if (!frm.doc.items || frm.doc.items.length === 0) {
            frappe.msgprint(__('No items in the table. Add items or import from CSV first.'));
            return;
        }

        frappe.show_progress(__('Fetching stock balances...'), 0, frm.doc.items.length);

        const promises = frm.doc.items.map((item, idx) =>
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.stock_balance_reconciliation.stock_balance_reconciliation.get_stock_balance',
                args: {
                    item_code: item.item_code,
                    warehouse: frm.doc.warehouse,
                    date: frm.doc.reconciliation_date
                }
            }).then(r => {
                if (r.message) {
                    frappe.model.set_value(item.doctype, item.name, 'current_qty',   r.message.qty);
                    frappe.model.set_value(item.doctype, item.name, 'current_price', r.message.rate);
                    if (!item.valuation_price) {
                        frappe.model.set_value(item.doctype, item.name, 'valuation_price', r.message.rate);
                    }
                    frappe.show_progress(__('Fetching stock balances...'), idx + 1, frm.doc.items.length);
                }
            })
        );

        Promise.all(promises).then(() => {
            frappe.hide_progress();
            frm.events.recalculate_all(frm);
            frappe.show_alert({ message: __('Stock balances updated from ledger'), indicator: 'green' });
        });
    },

    // ─── IMPORT FROM CSV ─────────────────────────────────────────
    import_from_csv(frm) {
        if (!frm.doc.warehouse) {
            frappe.msgprint(__('Please select a Warehouse before importing.'));
            return;
        }
        if (!frm.doc.upload_file) {
            frappe.msgprint(__('Please attach a CSV file in the Upload field first.'));
            return;
        }

        frappe.show_progress(__('Importing CSV...'), 0, 100);

        frappe.call({
            method: 'ecclesia.ecclesia.doctype.stock_balance_reconciliation.stock_balance_reconciliation.parse_and_import_csv',
            args: {
                file_url:  frm.doc.upload_file,
                warehouse: frm.doc.warehouse,
                date:      frm.doc.reconciliation_date || frappe.datetime.get_today()
            },
            callback(r) {
                frappe.hide_progress();
                if (!r.message || !r.message.length) {
                    frappe.msgprint(__('No valid rows found in the CSV file.'));
                    return;
                }

                frm.clear_table('items');
                r.message.forEach(row => {
                    const child = frm.add_child('items');
                    Object.assign(child, row);
                });

                frm.refresh_field('items');
                frm.events.recalculate_all(frm);
                frappe.show_alert({
                    message: __(`Imported ${r.message.length} items from CSV`),
                    indicator: 'green'
                });
            }
        });
    },

    // ─── RECALCULATE ALL ─────────────────────────────────────────
    recalculate_all(frm) {
        if (!frm.doc.items) return;

        frm.doc.items.forEach(item => {
            const curQty   = flt(item.current_qty);
            const curPrice = flt(item.current_price);
            const physQty  = flt(item.physical_count_qty);
            const valPrice = flt(item.valuation_price) || curPrice;
            const diffQty  = physQty - curQty;
            const netAdjAmt = diffQty * valPrice;

            frappe.model.set_value(item.doctype, item.name, 'system_valuation',    round2(curQty * curPrice));
            frappe.model.set_value(item.doctype, item.name, 'valuation_now',       round2(physQty * valPrice));
            frappe.model.set_value(item.doctype, item.name, 'difference_qty',      round2(diffQty));
            frappe.model.set_value(item.doctype, item.name, 'net_adjusted_qty',    round2(diffQty));
            frappe.model.set_value(item.doctype, item.name, 'net_adjusted_amount', round2(netAdjAmt));
            frappe.model.set_value(item.doctype, item.name, 'status',
                Math.abs(diffQty) < 0.001 ? 'OK' : diffQty > 0 ? 'Surplus' : 'Deficit'
            );
        });

        frm.refresh_field('items');
        frm.events.update_summary(frm);
    },

    // ─── UPDATE SUMMARY FIELDS ───────────────────────────────────
    update_summary(frm) {
        const items      = frm.doc.items || [];
        const totalSysVal = items.reduce((a, i) => a + flt(i.system_valuation), 0);
        const netAmt     = items.reduce((a, i) => a + flt(i.net_adjusted_amount), 0);
        const adjusted   = items.filter(i => i.status !== 'OK').length;
        const variancePct = totalSysVal ? round2((netAmt / totalSysVal) * 100) : 0;

        frm.set_value('total_items',           items.length);
        frm.set_value('total_adjusted_items',  adjusted);
        frm.set_value('net_adjustment_amount', round2(netAmt));
        frm.set_value('variance_percent',      variancePct);

        frm.events.render_summary_dashboard(frm);
    },

    // ─── SUMMARY DASHBOARD ───────────────────────────────────────
    render_summary_dashboard(frm) {
        frm.dashboard.reset();
        if (!frm.doc.items || !frm.doc.items.length) return;

        const items   = frm.doc.items;
        const surplus = items.filter(i => i.status === 'Surplus').length;
        const deficit = items.filter(i => i.status === 'Deficit').length;
        const netAmt  = flt(frm.doc.net_adjustment_amount);
        const varPct  = flt(frm.doc.variance_percent);

        frm.dashboard.add_indicator(__(`Total: ${items.length} items`), 'blue');
        frm.dashboard.add_indicator(__(`Surplus: ${surplus}`),          surplus > 0 ? 'green' : 'grey');
        frm.dashboard.add_indicator(__(`Deficit: ${deficit}`),          deficit > 0 ? 'red'   : 'grey');
        frm.dashboard.add_indicator(
            __(`Net Adj: ${format_currency(netAmt)}`),
            netAmt >= 0 ? 'green' : 'red'
        );
        frm.dashboard.add_indicator(
            __(`Variance: ${varPct}%`),
            Math.abs(varPct) > 5 ? 'red' : Math.abs(varPct) > 2 ? 'orange' : 'green'
        );

        // Mode indicator
        if (frm.doc.docstatus === 0) {
            frm.dashboard.add_indicator(
                frm.doc.create_stock_entry
                    ? __('Mode: Draft Stock Entry on Submit')
                    : __('Mode: Post Directly on Submit'),
                frm.doc.create_stock_entry ? 'blue' : 'green'
            );
        }

        if (frm.doc.stock_entry_reference) {
            frm.dashboard.add_indicator(
                __(`Stock Entry: ${frm.doc.stock_entry_reference}`),
                frm.doc.stock_entry_status === 'Submitted' ? 'green' : 'blue'
            );
        }
    },

    // ─── DOWNLOAD TEMPLATE ───────────────────────────────────────
    download_template(frm) {
        const csv = [
            'Item Code,Item Name,Current Qty,Current Price,Physical Count Qty,Valuation Price',
            'ITM-001,Sample Product A,100,1500,98,1500',
            'ITM-002,Sample Product B,50,2500,50,2600',
        ].join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const a    = document.createElement('a');
        a.href     = URL.createObjectURL(blob);
        a.download = 'stock_balance_recon_template.csv';
        a.click();
    },
});

// ─── CHILD TABLE EVENTS ───────────────────────────────────────────
frappe.ui.form.on('Stock Reconciliation Item Line', {
    physical_count_qty(frm, cdt, cdn) {
        recalc_row(frm, cdt, cdn);
    },
    valuation_price(frm, cdt, cdn) {
        recalc_row(frm, cdt, cdn);
    },
    current_qty(frm, cdt, cdn) {
        recalc_row(frm, cdt, cdn);
    },
    current_price(frm, cdt, cdn) {
        recalc_row(frm, cdt, cdn);
    },
    item_code(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.item_code && frm.doc.warehouse && frm.doc.reconciliation_date) {
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.stock_balance_reconciliation.stock_balance_reconciliation.get_stock_balance',
                args: {
                    item_code: row.item_code,
                    warehouse: frm.doc.warehouse,
                    date:      frm.doc.reconciliation_date
                },
                callback(r) {
                    if (r.message) {
                        frappe.model.set_value(cdt, cdn, 'current_qty',    r.message.qty);
                        frappe.model.set_value(cdt, cdn, 'current_price',  r.message.rate);
                        frappe.model.set_value(cdt, cdn, 'valuation_price', r.message.rate);
                        recalc_row(frm, cdt, cdn);
                    }
                }
            });
        }
    }
});

// ─── HELPERS ─────────────────────────────────────────────────────
function recalc_row(frm, cdt, cdn) {
    const row      = locals[cdt][cdn];
    const curQty   = flt(row.current_qty);
    const curPrice = flt(row.current_price);
    const physQty  = flt(row.physical_count_qty);
    const valPrice = flt(row.valuation_price) || curPrice;
    const diffQty  = physQty - curQty;
    const netAdjAmt = diffQty * valPrice;

    frappe.model.set_value(cdt, cdn, 'system_valuation',    round2(curQty * curPrice));
    frappe.model.set_value(cdt, cdn, 'valuation_now',       round2(physQty * valPrice));
    frappe.model.set_value(cdt, cdn, 'difference_qty',      round2(diffQty));
    frappe.model.set_value(cdt, cdn, 'net_adjusted_qty',    round2(diffQty));
    frappe.model.set_value(cdt, cdn, 'net_adjusted_amount', round2(netAdjAmt));
    frappe.model.set_value(cdt, cdn, 'status',
        Math.abs(diffQty) < 0.001 ? 'OK' : diffQty > 0 ? 'Surplus' : 'Deficit'
    );

    frm.events.update_summary(frm);
}

function round2(n) {
    return Math.round(flt(n) * 100) / 100;
}

function format_currency(n) {
    return new Intl.NumberFormat('en-NG', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(n);
}