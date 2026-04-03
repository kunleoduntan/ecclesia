// ecclesia/ecclesia/doctype/bank_statement_upload/bank_statement_upload.js

frappe.ui.form.on('Bank Statement Upload', {

    // ---------------------------------------------------------------- //
    //  Form setup                                                        //
    // ---------------------------------------------------------------- //

    refresh(frm) {
        frm._recode_selection = [];
        frm._setup_done = false;

        // Grid is editable — rows can be added, deleted, and cleared
        frm.set_df_property('import_items', 'cannot_add_rows',    false);
        frm.set_df_property('import_items', 'cannot_delete_rows', false);

        _render_action_buttons(frm);
        _render_action_panel(frm);
        _render_progress_html(frm);
        _setup_realtime_listener(frm);
        _colour_status_rows(frm);
    },

    onload(frm) {
        if (!frm.doc.company) {
            frappe.defaults.get_user_default('company').then(c => {
                frm.set_value('company', c);
            });
        }
    },

    // ---------------------------------------------------------------- //
    //  Field triggers                                                    //
    // ---------------------------------------------------------------- //

    upload_file(frm) {
        // File just attached — re-render buttons and action panel
        _render_action_buttons(frm);
        _render_action_panel(frm);
    },

    file_type(frm) {
        if (!['XLSX', 'XLS'].includes(frm.doc.file_type)) {
            frm.set_value('sheet_name', '');
        }
    },

    creation_mode(frm) {
        frm.set_df_property(
            'batch_size', 'hidden',
            frm.doc.creation_mode !== 'Batch'
        );
    },
});


// -------------------------------------------------------------------- //
//  Child table (import items) triggers                                   //
// -------------------------------------------------------------------- //

frappe.ui.form.on('Bank Statement Upload Item', {

    // WHT checkbox toggled by user → recalculate
    apply_wht(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.apply_wht) {
            frappe.model.set_value(cdt, cdn, 'wht_amount', 0);
            frappe.model.set_value(cdt, cdn, 'net_amount',
                flt(row.local_currency_amount));
        }
    },

    wht_rate(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.apply_wht || !row.wht_rate) return;
        const gross = flt(row.local_currency_amount);
        const wht   = flt(gross * row.wht_rate / 100, 2);
        frappe.model.set_value(cdt, cdn, 'wht_amount', wht);
        frappe.model.set_value(cdt, cdn, 'net_amount', flt(gross - wht, 2));
    },

    // Row-level checkbox for bulk selection
    form_render(frm, cdt, cdn) {
        // Colour individual row by status
        const row = locals[cdt][cdn];
        const $row = frm.fields_dict.import_items.grid
            .get_row(cdn)?.$row_index;
        if (!$row) return;
        const colours = {
            'Ready':   '#f0fff4',
            'Review':  '#fffbeb',
            'Failed':  '#fff0f0',
            'Skipped': '#f5f5f5',
            'Created': '#e6f7ff',
        };
        if (colours[row.row_status]) {
            $row.closest('tr').css('background', colours[row.row_status]);
        }
    },
});


// -------------------------------------------------------------------- //
//  Action button builders                                               //
// -------------------------------------------------------------------- //

function _render_action_buttons(frm) {
    frm.clear_custom_buttons();

    const status = frm.doc.import_status;

    // 1. Analyse File — always visible, primary action
    if (status !== 'Creating') {
        frm.add_custom_button(__('Analyse File'), () => {
            if (!frm.doc.upload_file) {
                frappe.msgprint(__('Please attach an Excel or CSV file first.'));
                return;
            }
            _do_parse(frm);
        }).css({'font-weight': '600', 'background': 'var(--primary)',
                'color': '#fff', 'border-color': 'var(--primary)'});
    }

    // 2. Create Receipts & Payments — only shown when staging is done and rows exist
    if (status === 'Staging' && (frm.doc.rows_ready || 0) > 0) {
        frm.add_custom_button(__('Create Receipts & Payments'), () => {
            _confirm_create(frm);
        }).css({'font-weight': '500', 'color': 'var(--primary)'});
    }

    // 3. Download full analysis as Excel
    if (['Staging', 'Completed with Errors', 'Completed'].includes(status)
        && (frm.doc.total_rows || 0) > 0) {
        frm.add_custom_button(__('Download Analysis'), () => {
            _export_staged(frm);
        }, __('Actions'));
    }

    // 4. Bulk Recode
    if (['Staging', 'Completed with Errors'].includes(status)) {
        frm.add_custom_button(__('Bulk Recode Selected'), () => {
            _open_recode_dialog(frm);
        }, __('Actions'));
    }

    // 4. Export Failed
    if (frm.doc.rows_failed > 0) {
        frm.add_custom_button(__('Export Failed Rows'), () => {
            _export_failed(frm);
        }, __('Actions'));
    }

    // 5. Refresh progress
    if (status === 'Creating') {
        frm.add_custom_button(__('Refresh Progress'), () => {
            _refresh_progress(frm);
        });
    }
}


// -------------------------------------------------------------------- //
//  Parse & Stage                                                        //
// -------------------------------------------------------------------- //

function _do_parse(frm) {
    // Reload the doc first to get the latest modified timestamp.
    // File attachment auto-saves the doc and bumps modified,
    // causing TimestampMismatchError if we call without refreshing.
    frm.reload_doc().then(() => {
    frappe.show_progress(__('Parsing file…'), 0, 100, __('Analysing rows with AI'));

    frm.call({
        method: 'ecclesia.ecclesia.doctype.bank_statement_upload.bank_statement_upload.parse_and_stage',
        args: { doc_name: frm.doc.name },
        freeze: true,
        freeze_message: __('AI is reading and coding your transactions…'),
        callback(r) {
            frappe.hide_progress();
            if (!r.message) return;
            const msg = r.message;

            if (msg.queued) {
                // Large file — analysis running in background
                frappe.show_alert({
                    message: __(msg.message || `${msg.total} rows queued for background analysis. Refreshing…`),
                    indicator: 'blue'
                }, 8);
                // Poll every 3 seconds until status changes from Parsing
                let polls = 0;
                const poll = setInterval(() => {
                    polls++;
                    frappe.db.get_value('Bank Statement Upload', frm.doc.name, 'import_status')
                        .then(r2 => {
                            const st = r2.message?.import_status;
                            if (st === 'Staging' || st === 'Completed with Errors' || polls > 60) {
                                clearInterval(poll);
                                frm.reload_doc();
                            }
                        });
                }, 3000);
            } else {
                const { total, ready, review, failed } = msg;
                frappe.show_alert({
                    message: __(`Staged ${total} rows: ${ready} ready, ${review} need review`),
                    indicator: ready > 0 ? 'green' : 'orange'
                }, 6);
                frm.reload_doc();
            }
        },
    });
    }); // end frm.reload_doc().then()
}


// -------------------------------------------------------------------- //
//  Create Transactions                                                  //
// -------------------------------------------------------------------- //

function _confirm_create(frm) {
    const ready   = frm.doc.rows_ready  || 0;
    const review  = frm.doc.rows_review || 0;
    const mode    = frm.doc.creation_mode || 'Batch';
    const total   = ready + review;

    frappe.confirm(
        __(`Create transactions for <b>${total}</b> rows (`
            + `${ready} ready + ${review} need review)?<br><br>`
            + `Mode: <b>${mode}</b>`),
        () => {
            frm.call({
                method: 'ecclesia.ecclesia.doctype.bank_statement_upload.bank_statement_upload.create_transactions',
                args: { doc_name: frm.doc.name },
                freeze: mode === 'Immediate',
                freeze_message: __('Creating documents…'),
                callback(r) {
                    if (r.message) {
                        if (r.message.queued) {
                            frappe.show_alert({
                                message: __('Batch job queued. Watch progress bar below.'),
                                indicator: 'blue'
                            }, 5);
                        } else {
                            const { created, failed } = r.message;
                            frappe.show_alert({
                                message: __(
                                    `Done. Created: ${created}. Failed: ${failed}`
                                ),
                                indicator: failed > 0 ? 'orange' : 'green'
                            }, 6);
                        }
                        frm.reload_doc();
                    }
                }
            });
        }
    );
}


// -------------------------------------------------------------------- //
//  Bulk Recode Dialog                                                   //
// -------------------------------------------------------------------- //

function _open_recode_dialog(frm) {
    // Collect selected rows from child table checkboxes
    const selected = frm.fields_dict.import_items.grid.get_selected_children();

    if (!selected.length) {
        frappe.msgprint(__(
            'Please select rows in the Staged Transactions table first '
            + '(use the checkboxes on the left of each row).'
        ));
        return;
    }

    const summary = _selection_summary(selected);

    const d = new frappe.ui.Dialog({
        title: __('Bulk Recode — {0} rows selected', [selected.length]),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'summary_html',
                options: `<div style="background:var(--bg-color);border:1px solid var(--border-color);
                    border-radius:6px;padding:10px 14px;margin-bottom:10px;font-size:13px">
                    ${summary}
                    <div style="font-size:11px;color:var(--text-muted);margin-top:4px">
                    Fields left blank are <b>not changed</b>.
                    </div></div>`
            },
            { fieldtype: 'Column Break' },
            {
                label: __('Transaction Type'),
                fieldname: 'trans_type',
                fieldtype: 'Select',
                options: [
                    '',
                    'Supplier Payment', 'Expense Payment', 'Transfer Out',
                    'Supplier Refunds', 'Customer Receipt', 'Receive from One-Off',
                    'Revenue Receipt', 'Member Tithe', 'Pledges',
                    'Customer Refund', 'Transfer In'
                ].join('\n'),
            },
            {
                label: __('Account to Debit / Credit'),
                fieldname: 'account_to_debit',
                fieldtype: 'Link',
                options: 'Account',
                get_query: () => ({
                    filters: {
                        company: frm.doc.company,
                        is_group: 0,
                        disabled: 0,
                    }
                }),
            },
            { fieldtype: 'Column Break' },
            {
                label: __('Cost Center'),
                fieldname: 'cost_center',
                fieldtype: 'Link',
                options: 'Cost Center',
                get_query: () => ({
                    filters: { company: frm.doc.company }
                }),
            },
            {
                label: __('Department'),
                fieldname: 'department',
                fieldtype: 'Link',
                options: 'Department',
            },
            { fieldtype: 'Column Break' },
            {
                label: __('Cash Flow Classification'),
                fieldname: 'cashflow_type',
                fieldtype: 'Select',
                options: [
                    '',
                    'Supplier payments', 'Salary payments', 'Rent & utilities',
                    'Office expenses', 'Operating costs', 'Tax Payment',
                    'Equipment purchases', 'Loan repayments', 'Dividend payments',
                    'Customer payments for goods/services', 'Interest received',
                    'Rental income', 'Service fees', 'Capital contributions'
                ].join('\n'),
            },
            {
                label: __('Remittance Bank Account'),
                fieldname: 'bank_account',
                fieldtype: 'Link',
                options: 'Bank Account',
            },
            { fieldtype: 'Column Break' },
            {
                label: __('Withholding Tax'),
                fieldname: 'wht_action',
                fieldtype: 'Select',
                options: '\nApply WHT (set rate per row after)\nRemove WHT',
            },
            {
                label: __('Project'),
                fieldname: 'project',
                fieldtype: 'Link',
                options: 'Project',
            },
            { fieldtype: 'Section Break' },
            {
                label: __('Override Description (leave blank to keep AI description)'),
                fieldname: 'cleaned_description',
                fieldtype: 'Data',
            },
        ],
        primary_action_label: __('Apply Recode'),
        primary_action(values) {
            // Build recode_values — exclude empty strings
            const recode = {};
            ['trans_type', 'account_to_debit', 'cost_center', 'department',
             'cashflow_type', 'bank_account', 'project', 'cleaned_description'
            ].forEach(f => {
                if (values[f]) recode[f] = values[f];
            });

            if (values.wht_action === 'Apply WHT (set rate per row after)') {
                recode.apply_wht = 1;
            } else if (values.wht_action === 'Remove WHT') {
                recode.apply_wht  = 0;
                recode.wht_rate   = 0;
                recode.wht_amount = 0;
            }

            if (!Object.keys(recode).length) {
                frappe.msgprint(__('No changes specified.'));
                return;
            }

            d.hide();
            frm.call({
                method: 'ecclesia.ecclesia.doctype.bank_statement_upload.bank_statement_upload.bulk_recode',
                args: {
                    doc_name:      frm.doc.name,
                    row_names:     JSON.stringify(selected.map(r => r.name)),
                    recode_values: JSON.stringify(recode),
                },
                freeze: true,
                freeze_message: __('Applying recode…'),
                callback(r) {
                    if (r.message) {
                        frappe.show_alert({
                            message: __(`Recoded ${r.message.updated} rows.`),
                            indicator: 'green'
                        }, 4);
                        frm.reload_doc();
                    }
                }
            });
        },
    });

    d.show();
}

function _selection_summary(rows) {
    const payments  = rows.filter(r => r.doc_type === 'Payments').length;
    const receipts  = rows.filter(r => r.doc_type === 'Receipts').length;
    const review    = rows.filter(r => r.row_status === 'Review').length;
    const failed    = rows.filter(r => r.row_status === 'Failed').length;
    return `
        <b>${rows.length} rows selected</b> &nbsp;·&nbsp;
        ${payments} Payments &nbsp;·&nbsp;
        ${receipts} Receipts &nbsp;·&nbsp;
        <span style="color:orange">${review} needs review</span> &nbsp;·&nbsp;
        <span style="color:red">${failed} failed</span>
    `;
}


// -------------------------------------------------------------------- //
//  Export Failed                                                        //
// -------------------------------------------------------------------- //

function _export_staged(frm) {
    frappe.show_alert({ message: __('Preparing analysis export…'), indicator: 'blue' }, 3);
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.bank_statement_upload.bank_statement_upload.export_staged',
        args: { doc_name: frm.doc.name },
        callback(r) {
            if (r.message && r.message.file_url) {
                const url = r.message.file_url;
                frappe.show_alert({
                    message: __('Analysis ready. <a href="{0}" target="_blank">Download Excel</a>', [url]),
                    indicator: 'green'
                }, 15);
                window.open(url, '_blank');
            }
        }
    });
}


function _export_failed(frm) {
    frappe.show_alert({ message: __('Preparing export…'), indicator: 'blue' }, 3);

    frm.call({
        method: 'ecclesia.ecclesia.doctype.bank_statement_upload.bank_statement_upload.export_failed_rows',
        args: { doc_name: frm.doc.name },
        callback(r) {
            if (r.message && r.message.file_url) {
                const url = r.message.file_url;
                frappe.show_alert({
                    message: __('Export ready. <a href="{0}" target="_blank">Download</a>', [url]),
                    indicator: 'green'
                }, 10);
                window.open(url, '_blank');
            }
        }
    });
}


// -------------------------------------------------------------------- //
//  Inline action panel — prominent guidance shown on the form body    //
// -------------------------------------------------------------------- //

function _render_action_panel(frm) {
    const wrapper = frm.fields_dict.progress_html?.$wrapper;
    if (!wrapper) return;

    const status   = frm.doc.import_status;
    const hasFile  = !!frm.doc.upload_file;
    const total    = frm.doc.total_rows    || 0;
    const ready    = frm.doc.rows_ready    || 0;
    const review   = frm.doc.rows_review   || 0;
    const failed   = frm.doc.rows_failed   || 0;
    const created  = frm.doc.rows_created  || 0;
    const skipped  = frm.doc.rows_skipped  || 0;

    // ── Step indicators ──────────────────────────────────────────── //
    const steps = [
        { label: 'Attach file',         done: hasFile,              active: !hasFile },
        { label: 'Analyse',             done: total > 0,            active: hasFile && total === 0 },
        { label: 'Review & recode',     done: created > 0,          active: total > 0 && created === 0 },
        { label: 'Create documents',    done: status === 'Completed', active: created > 0 && status !== 'Completed' },
    ];

    const stepsHtml = steps.map((s, i) => `
        <div style="display:flex;align-items:center;gap:6px;font-size:13px;
                    color:${s.done ? 'var(--green-600,#16a34a)' : s.active ? 'var(--color-text-primary)' : 'var(--color-text-muted)'}">
            <div style="width:22px;height:22px;border-radius:50%;display:flex;align-items:center;
                        justify-content:center;font-size:11px;font-weight:600;flex-shrink:0;
                        background:${s.done ? 'var(--green-600,#16a34a)' : s.active ? 'var(--primary)' : 'var(--border-color)'};
                        color:${s.done || s.active ? '#fff' : 'var(--color-text-muted)'}">
                ${s.done ? '&#10003;' : i + 1}
            </div>
            <span style="font-weight:${s.active ? '600' : '400'}">${s.label}</span>
            ${i < steps.length - 1 ? '<div style="flex:1;height:1px;background:var(--border-color);margin:0 4px"></div>' : ''}
        </div>
    `).join('');

    // ── Main CTA ─────────────────────────────────────────────────── //
    let ctaHtml = '';

    if (!hasFile) {
        ctaHtml = `
            <div style="text-align:center;padding:24px 0 8px">
                <div style="font-size:14px;color:var(--color-text-muted);margin-bottom:8px">
                    Attach your bank statement Excel or CSV file above, then click:
                </div>
                <button class="btn btn-primary btn-sm" disabled style="opacity:.5;cursor:not-allowed">
                    Analyse File
                </button>
            </div>`;
    } else if (!total) {
        ctaHtml = `
            <div style="text-align:center;padding:24px 0 8px">
                <div style="font-size:14px;color:var(--color-text-muted);margin-bottom:12px">
                    File attached: <strong>${(frm.doc.upload_file || '').split('/').pop()}</strong>
                    &nbsp;&mdash;&nbsp;Click to read, code and stage all transactions automatically.
                </div>
                <button class="btn btn-primary" onclick="frappe.ui.form.get_open_form().trigger_action('analyse')">
                    &#128269;&nbsp; Analyse File
                </button>
            </div>`;
    } else if (status === 'Staging') {
        const pct = total ? Math.round(ready / total * 100) : 0;
        ctaHtml = `
            <div style="padding:16px 0 8px">
                <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:16px">
                    ${_stat('Total',   total,   '#6366f1')}
                    ${_stat('Ready',   ready,   '#16a34a')}
                    ${_stat('Review',  review,  '#d97706')}
                    ${_stat('Failed',  failed,  '#dc2626')}
                    ${_stat('Skipped', skipped, '#9ca3af')}
                </div>
                ${ready > 0 ? `
                <div style="text-align:center">
                    <button class="btn btn-primary btn-lg"
                        onclick="frappe.ui.form.get_open_form().trigger_action('create')">
                        &#10003;&nbsp; Create Receipts &amp; Payments (${ready} ready)
                    </button>
                    ${review > 0 ? `<div style="font-size:12px;color:var(--color-text-muted);margin-top:6px">
                        ${review} row(s) need review — recode them above or create now and fix later.
                    </div>` : ''}
                </div>` : `
                <div style="text-align:center;color:var(--color-text-muted);font-size:13px">
                    No rows are Ready yet. Review and recode the staged rows above.
                </div>`}
            </div>`;
    } else if (status === 'Completed' || status === 'Completed with Errors') {
        ctaHtml = `
            <div style="padding:16px 0 8px">
                <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px">
                    ${_stat('Total',   total,   '#6366f1')}
                    ${_stat('Created', created, '#16a34a')}
                    ${_stat('Review',  review,  '#d97706')}
                    ${_stat('Failed',  failed,  '#dc2626')}
                    ${_stat('Skipped', skipped, '#9ca3af')}
                </div>
                ${failed > 0 ? `<div style="margin-top:12px;text-align:center">
                    <button class="btn btn-default btn-sm"
                        onclick="frappe.ui.form.get_open_form().trigger_action('export_failed')">
                        Download Failed Rows (${failed})
                    </button>
                </div>` : ''}
            </div>`;
    } else if (status === 'Creating') {
        const pct = total ? Math.round(created / total * 100) : 0;
        ctaHtml = `
            <div style="padding:16px 0 8px">
                <div style="font-size:13px;margin-bottom:6px">
                    Creating documents&hellip; ${created} of ${total}
                </div>
                <div style="height:8px;background:var(--border-color);border-radius:4px;overflow:hidden">
                    <div style="height:100%;width:${pct}%;background:var(--primary);
                                border-radius:4px;transition:width .4s"></div>
                </div>
            </div>`;
    }

    wrapper.html(`
        <div style="border:1px solid var(--border-color);border-radius:8px;
                    padding:16px 20px;margin:8px 0;background:var(--card-bg)">
            <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:14px">
                ${stepsHtml}
            </div>
            ${ctaHtml}
        </div>
    `);

    // Wire inline buttons to actual actions
    wrapper.find('button[onclick]').each(function() {
        // onclick is set via attribute — works fine
    });

    // Override trigger_action to dispatch to our functions
    const form = frm;
    frappe.ui.form.get_open_form = () => ({
        trigger_action: (action) => {
            if (action === 'analyse')       _do_parse(form);
            if (action === 'create')        _confirm_create(form);
            if (action === 'download')      _export_staged(form);
            if (action === 'export_failed') _export_failed(form);
        }
    });
}

function _stat(label, val, colour) {
    return `<div style="background:var(--control-bg);border-radius:6px;padding:10px;text-align:center;
                        border:1px solid var(--border-color)">
        <div style="font-size:20px;font-weight:600;color:${colour}">${val}</div>
        <div style="font-size:11px;color:var(--color-text-muted)">${label}</div>
    </div>`;
}

// -------------------------------------------------------------------- //
//  Progress bar HTML                                                    //
// -------------------------------------------------------------------- //

function _render_progress_html(frm) {
    // Stats and CTA are handled by _render_action_panel.
    // This function only updates the action panel with fresh data.
    _render_action_panel(frm);
}

function _stat_card(label, val, colour) {
    return `<div style="background:var(--bg-color);border:1px solid var(--border-color);
        border-radius:6px;padding:8px;text-align:center">
        <div style="font-size:18px;font-weight:500;color:${colour}">${val}</div>
        <div style="font-size:11px;color:var(--text-muted)">${label}</div>
    </div>`;
}


// -------------------------------------------------------------------- //
//  Realtime progress listener                                           //
// -------------------------------------------------------------------- //

function _setup_realtime_listener(frm) {
    if (frm._rt_listener_set) return;
    frm._rt_listener_set = true;

    frappe.realtime.on('bsu_analysis_complete', (data) => {
        if (data.import_name !== frm.doc.name) return;
        frappe.show_alert({
            message: __(`Analysis complete: ${data.total} rows staged, ${data.ready} ready`),
            indicator: 'green'
        }, 6);
        frm.reload_doc();
    });

    frappe.realtime.on('bsu_progress', (data) => {
        if (data.import_name !== frm.doc.name) return;

        // Update counters without full reload
        frm.doc.rows_created = data.created;
        frm.doc.rows_failed  = data.failed;
        _render_progress_html(frm);

        if (data.done) {
            frappe.show_alert({
                message: __(
                    `Batch complete. Created: ${data.created}, Failed: ${data.failed}`
                ),
                indicator: data.failed > 0 ? 'orange' : 'green'
            }, 8);
            frm.reload_doc();
        }
    });
}


// -------------------------------------------------------------------- //
//  Row colouring in child table                                         //
// -------------------------------------------------------------------- //

function _colour_status_rows(frm) {
    const grid = frm.fields_dict?.import_items?.grid;
    if (!grid) return;

    const COLOURS = {
        Ready:   '#f0fff4',
        Review:  '#fffde7',
        Failed:  '#fff1f0',
        Skipped: '#fafafa',
        Created: '#e6f7ff',
    };

    (frm.doc.import_items || []).forEach((row, i) => {
        const $tr = grid.grid_rows[i]?.$row;
        if ($tr && COLOURS[row.row_status]) {
            $tr.css('background-color', COLOURS[row.row_status]);
        }
    });
}

function _refresh_progress(frm) {
    frm.call({
        method: 'ecclesia.ecclesia.doctype.bank_statement_upload.bank_statement_upload.get_progress',
        args: { doc_name: frm.doc.name },
        callback(r) {
            if (!r.message) return;
            const d = r.message;
            frm.doc.rows_created = d.created;
            frm.doc.rows_failed  = d.failed;
            frm.doc.rows_review  = d.review;
            frm.doc.rows_skipped = d.skipped;
            frm.doc.import_status = d.status;
            _render_action_panel(frm);
            _render_action_buttons(frm);
        }
    });
}