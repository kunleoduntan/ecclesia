// Merge with the standard Employee list settings (status indicator, default
// filters, etc.) instead of overwriting them.
frappe.listview_settings['Employee'] = (function (base) {

return Object.assign({}, base, {
    onload: function (listview) {

        if (base.onload) {
            base.onload.call(this, listview);
        }

        // ------------------------------------------------------------
        // Button 1: Update Monthly Tax (selected employees)
        // ------------------------------------------------------------
        listview.page.add_inner_button(__('Update Monthly Tax'), function () {

            const selected = listview.get_checked_items();

            if (!selected.length) {
                frappe.msgprint(__('Please select at least one Employee.'));
                return;
            }

            get_active_employees(listview, selected.map(d => d.name), function (active, skipped) {

                if (!active.length) {
                    frappe.msgprint(__('None of the selected employees are Active.'));
                    return;
                }

                const names = active.map(e => e.name);

                let confirm_msg = __('Update Monthly Tax Payable for {0} Active employee(s)?', [names.length]);
                if (skipped) {
                    confirm_msg += '<br><br>' +
                        __('{0} selected employee(s) are not Active and will be skipped.', [skipped]);
                }

                frappe.confirm(confirm_msg, function () {
                    run_update(listview, names, skipped);
                });
            });
        });

        // ------------------------------------------------------------
        // Button 2: Check Missing Tax Computation
        // Uses selected employees; if none selected, uses every employee
        // matching the current list filters.
        // ------------------------------------------------------------
        listview.page.add_inner_button(__('Check Missing Tax Computation'), function () {

            const selected = listview.get_checked_items();
            const names = selected.length ? selected.map(d => d.name) : null;

            frappe.show_progress(__('Checking Tax Computation'), 0, 100, __('Loading Active employees...'));

            get_active_employees(listview, names, function (active, skipped) {
                frappe.hide_progress();
                check_missing(listview, active, skipped);
            });
        });
    }
});

})(frappe.listview_settings['Employee'] || {});

/* ==================================================================
   ACTIVE EMPLOYEES ONLY
   names = array of Employee IDs (selected), or null to use the current
   list filters. Callback receives (active_employees, skipped_count).
   ================================================================== */

function get_active_employees(listview, names, callback) {

    const base_filters = names
        ? [['Employee', 'name', 'in', names]]
        : listview.get_filters_for_args();

    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Employee',
            filters: base_filters.concat([['Employee', 'status', '=', 'Active']]),
            fields: ['name', 'employee_name'],
            limit_page_length: 0
        },
        callback: function (r) {
            const active = r.message || [];
            callback(active, names ? names.length - active.length : 0);
        },
        error: function () {
            frappe.hide_progress();
            frappe.msgprint({
                title: __('Error'),
                indicator: 'red',
                message: __('Could not fetch Employee records.')
            });
        }
    });
}

/* ==================================================================
   CHECK MISSING
   ================================================================== */

function check_missing(listview, employees, skipped) {

    if (!employees.length) {
        frappe.msgprint(__('No Active employees to check.'));
        return;
    }

    const names = employees.map(e => e.name);

    frappe.show_progress(__('Checking Tax Computation'), 50, 100, __('Comparing records...'));

    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Employee Tax Computation',
            filters: [
                ['Employee Tax Computation', 'employee', 'in', names],
                ['Employee Tax Computation', 'docstatus', '!=', 2]
            ],
            fields: ['employee'],
            limit_page_length: 0
        },
        callback: function (r) {
            frappe.hide_progress();

            const has_tax = new Set((r.message || []).map(row => row.employee));
            const missing = employees.filter(e => !has_tax.has(e.name));

            show_missing_dialog(listview, missing, employees.length, skipped || 0);
        },
        error: function () {
            frappe.hide_progress();
            frappe.msgprint({
                title: __('Error'),
                indicator: 'red',
                message: __('Could not fetch Employee Tax Computation records.')
            });
        }
    });
}

function show_missing_dialog(listview, missing, checked_count, skipped) {

    const skipped_note = skipped
        ? `<p class="text-muted">${__('{0} selected employee(s) skipped (not Active).', [skipped])}</p>`
        : '';

    if (!missing.length) {
        frappe.msgprint({
            title: __('Check Completed'),
            indicator: 'green',
            message: __('All {0} Active employee(s) checked have an Employee Tax Computation.', [checked_count]) +
                skipped_note
        });
        return;
    }

    const rows = missing.map((e, i) =>
        `<tr>
            <td>${i + 1}</td>
            <td>${frappe.utils.escape_html(e.name)}</td>
            <td>${frappe.utils.escape_html(e.employee_name || '')}</td>
        </tr>`
    ).join('');

    const d = new frappe.ui.Dialog({
        title: __('Missing Employee Tax Computation'),
        fields: [{
            fieldtype: 'HTML',
            fieldname: 'result',
            options: `
                <p>
                    <b>${missing.length}</b> of ${checked_count} Active employee(s) checked
                    have no Employee Tax Computation.
                </p>
                ${skipped_note}
                <div style="max-height: 400px; overflow-y: auto;">
                    <table class="table table-bordered table-sm">
                        <thead>
                            <tr><th>#</th><th>${__('Employee')}</th><th>${__('Employee Name')}</th></tr>
                        </thead>
                        <tbody>${rows}</tbody>
                    </table>
                </div>`
        }],
        primary_action_label: __('Create Tax Computation ({0})', [missing.length]),
        primary_action: function () {
            d.hide();
            create_missing(listview, missing);
        },
        secondary_action_label: __('Copy IDs'),
        secondary_action: function () {
            frappe.utils.copy_to_clipboard(missing.map(e => e.name).join('\n'));
        }
    });

    d.add_custom_action(__('Filter List to These'), function () {
        listview.filter_area.add([
            ['Employee', 'name', 'in', missing.map(e => e.name)]
        ]);
        d.hide();
    });

    d.show();
}

/* ==================================================================
   CREATE MISSING
   ================================================================== */

function create_missing(listview, missing) {
    const total = missing.length;
    const title = __('Creating Tax Computation');

    const result = {
        created: [],
        exists: [],
        skipped: [],
        failed: []
    };

    frappe.show_progress(title, 0, total, __('Starting...'));

    create_next(0, missing, result, total, title, listview);
}

function create_next(index, missing, result, total, title, listview) {

    if (index >= total) {
        finish_create(result, total, listview);
        return;
    }

    const emp = missing[index];

    const next = function () {
        frappe.show_progress(title, index + 1, total, emp.name);
        create_next(index + 1, missing, result, total, title, listview);
    };

    frappe.call({
        method: 'ecclesia.employee_events.create_tax_computation_for',
        args: { employee: emp.name },
        callback: function (r) {
            const res = r.message || {};

            if (res.status === 'created') {
                result.created.push({ employee: emp.name, name: res.name });
            } else if (res.status === 'exists') {
                result.exists.push(emp.name);
            } else if (res.status === 'skipped') {
                result.skipped.push(emp.name);
            } else {
                result.failed.push({ employee: emp.name, error: res.error || '' });
            }

            next();
        },
        error: function () {
            result.failed.push({ employee: emp.name, error: __('Server error') });
            next();
        }
    });
}

function finish_create(result, total, listview) {
    frappe.hide_progress();

    let msg = `<b>${result.created.length}</b> of ${total} Employee Tax Computation(s) created (Draft).<br>`;

    if (result.exists.length) {
        msg += `<b>${result.exists.length}</b> already existed.<br>`;
    }

    if (result.skipped.length) {
        msg += `<b>${result.skipped.length}</b> skipped (not Active).<br>`;
    }

    if (result.created.length) {
        const filter = encodeURIComponent(
            JSON.stringify(['in', result.created.map(c => c.employee)])
        );

        msg += `<br><b>Next step:</b> open each record and update the Annual Gross Income, ` +
            `Statutory Deductions and Benefits in Kind so that it reflects the employee's ` +
            `correct tax position.<br>` +
            `<a href="/app/employee-tax-computation?employee=${filter}">` +
            `${__('Open the created records')}</a><br>`;
    }

    if (result.failed.length) {
        msg += `<br><b>${result.failed.length}</b> failed (see Error Log):<br>` +
            result.failed.map(f =>
                frappe.utils.escape_html(f.employee) +
                (f.error ? ' - ' + frappe.utils.escape_html(f.error) : '')
            ).join('<br>');
    }

    frappe.msgprint({
        title: __('Tax Computation Creation Completed'),
        indicator: result.failed.length ? 'red' : 'green',
        message: msg
    });

    listview.refresh();
}

/* ==================================================================
   UPDATE MONTHLY TAX
   ================================================================== */

function run_update(listview, names, skipped) {
    const total = names.length;
    const title = __('Updating Monthly Tax');

    const result = {
        updated: 0,
        unchanged: 0,
        skipped: skipped || 0,
        not_found: [],
        failed: []
    };

    frappe.show_progress(title, 0, total, __('Fetching tax computations...'));

    // 1. Fetch all tax computations for the selected employees in ONE call.
    //    Latest record first, so the first hit per employee is the most recent.
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Employee Tax Computation',
            filters: [
                ['Employee Tax Computation', 'employee', 'in', names],
                ['Employee Tax Computation', 'docstatus', '!=', 2]
            ],
            fields: ['name', 'employee', 'monthly_tax_payable'],
            order_by: 'modified desc',
            limit_page_length: 0
        },
        callback: function (r) {
            const tax_map = {};
            (r.message || []).forEach(row => {
                if (!(row.employee in tax_map)) {
                    tax_map[row.employee] = row.monthly_tax_payable || 0;
                }
            });

            // 2. Fetch current Employee values so unchanged ones can be skipped.
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Employee',
                    filters: [['Employee', 'name', 'in', names]],
                    fields: ['name', 'monthly_tax_payable'],
                    limit_page_length: 0
                },
                callback: function (er) {
                    const current_map = {};
                    (er.message || []).forEach(row => {
                        current_map[row.name] = flt(row.monthly_tax_payable);
                    });

                    process_employee(0, names, tax_map, current_map, result, total, title, listview);
                },
                error: function () {
                    frappe.hide_progress();
                    frappe.msgprint({
                        title: __('Error'),
                        indicator: 'red',
                        message: __('Could not fetch Employee records.')
                    });
                }
            });
        },
        error: function () {
            frappe.hide_progress();
            frappe.msgprint({
                title: __('Error'),
                indicator: 'red',
                message: __('Could not fetch Employee Tax Computation records.')
            });
        }
    });
}

function process_employee(index, names, tax_map, current_map, result, total, title, listview) {

    if (index >= names.length) {
        finish(result, total, listview);
        return;
    }

    const emp = names[index];
    const next = function () {
        frappe.show_progress(title, index + 1, total, emp);
        process_employee(index + 1, names, tax_map, current_map, result, total, title, listview);
    };

    if (!(emp in tax_map)) {
        result.not_found.push(emp);
        next();
        return;
    }

    const new_value = flt(tax_map[emp]);

    if (current_map[emp] === new_value) {
        result.unchanged++;
        next();
        return;
    }

    frappe.call({
        method: 'frappe.client.set_value',
        args: {
            doctype: 'Employee',
            name: emp,
            fieldname: 'monthly_tax_payable',
            value: new_value
        },
        callback: function () {
            result.updated++;
            next();
        },
        error: function () {
            result.failed.push(emp);
            next();
        }
    });
}

function finish(result, total, listview) {
    frappe.hide_progress();

    let msg = `<b>${result.updated}</b> of ${total} employee(s) updated.<br>`;

    if (result.unchanged) {
        msg += `<b>${result.unchanged}</b> already up to date.<br>`;
    }

    if (result.skipped) {
        msg += `<b>${result.skipped}</b> skipped (not Active).<br>`;
    }

    if (result.not_found.length) {
        msg += `<br><b>${result.not_found.length}</b> with no Employee Tax Computation:<br>` +
            result.not_found.join(', ') + '<br>';
    }

    if (result.failed.length) {
        msg += `<br><b>${result.failed.length}</b> failed to update:<br>` +
            result.failed.join(', ');
    }

    frappe.msgprint({
        title: __('Update Completed'),
        indicator: result.failed.length ? 'red' : (result.not_found.length ? 'orange' : 'green'),
        message: msg
    });

    listview.refresh();
}
