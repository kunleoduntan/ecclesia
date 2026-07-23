// -*- coding: utf-8 -*-
// Copyright (c) 2026, kunle Oduntan and contributors
// Payments List View Script
//
// Consolidated from payments_list.js / payments_import_list.js (identical
// duplicate files) — this is now the single canonical list-view script.
//
// All server calls point at payments.py, since payments_import_handler.py
// and payments_dashboard.py were merged into it (see CHANGELOG.md).
// Uses the same confirmed-correct path convention as payments.js:
//   ecclesia.ecclesia.doctype.payments.payments.<method>

const PAYMENTS_PY_PATH = 'ecclesia.ecclesia.doctype.payments.payments';

frappe.listview_settings['Payments'] = {
    onload: function(listview) {
        listview.page.add_menu_item(__('Import Payments'), function() {
            show_import_dialog(listview);
        }, true);

        listview.page.add_action_item(__('Import Payments'), function() {
            show_import_dialog(listview);
        });

        listview.page.add_menu_item(__('Payments Dashboard'), function() {
            show_dashboard_dialog(listview);
        }, true);
    },

    // Per-row action button — only shown for Draft payments. Previously
    // just showed a msgprint stub ("Processing payment: X") with no
    // actual effect; now genuinely opens the document so the user can
    // review and submit it, which is what "Process" implies.
    button: {
        show(doc) {
            return doc.payment_status === 'Draft';
        },
        get_label() {
            return __('Process Payment');
        },
        get_description(doc) {
            return __('Open this payment to review and submit');
        },
        action(doc) {
            frappe.set_route('Form', 'Payments', doc.name);
        }
    }
};

// ==================== Import Dialog ====================

function show_import_dialog(listview) {
    let d = new frappe.ui.Dialog({
        title: __('Import Payments'),
        size: 'large',
        fields: [
            { label: __('Step 1: Download Template'), fieldtype: 'Section Break' },
            {
                fieldtype: 'HTML',
                options: `
                    <div class="alert alert-info" style="margin-bottom: 15px;">
                        <strong><i class="fa fa-info-circle"></i> Instructions:</strong>
                        <ol style="margin-top: 10px; margin-bottom: 0;">
                            <li>Download the CSV template below</li>
                            <li>Fill in your payment data (mandatory fields marked with *)</li>
                            <li>For "Amount Paid (Local Currency)" vs "Amount Paid (Foreign Currency)":
                                use Local Currency when Payment Currency matches that row's Company's
                                default currency, otherwise use Foreign Currency + Exchange Rate.</li>
                            <li>Upload the completed file</li>
                            <li>Review validation results</li>
                            <li>Import valid records (they land as Drafts for review)</li>
                        </ol>
                    </div>
                    <button class="btn btn-primary btn-sm" id="download-template-btn">
                        <i class="fa fa-download"></i> Download Template
                    </button>
                `
            },
            { label: __('Step 2: Upload Filled Template'), fieldtype: 'Section Break' },
            {
                label: __('Import File'),
                fieldname: 'import_file',
                fieldtype: 'Attach',
                reqd: 1,
                description: __('Upload a CSV file with payment data')
            },
            {
                label: __('Step 3: Validation Results'),
                fieldtype: 'Section Break',
                depends_on: 'eval:doc.import_file'
            },
            { fieldname: 'validation_results', fieldtype: 'HTML' }
        ],
        primary_action_label: __('Validate Data'),
        primary_action(values) {
            if (!values.import_file) {
                frappe.msgprint(__('Please upload a file first'));
                return;
            }
            validate_import_file(values.import_file, d);
        }
    });

    d.show();

    d.$wrapper.find('#download-template-btn').on('click', function() {
        download_template();
    });
}

function download_template() {
    frappe.call({
        method: `${PAYMENTS_PY_PATH}.get_payments_import_template`,
        callback: function(r) {
            if (r.message) {
                let csv_content = r.message.columns.join(',') + '\n';
                csv_content += r.message.sample_data.map(item => {
                    if (typeof item === 'string' && (item.includes(',') || item.includes('"'))) {
                        return '"' + item.replace(/"/g, '""') + '"';
                    }
                    return item;
                }).join(',');

                let blob = new Blob([csv_content], { type: 'text/csv;charset=utf-8;' });
                let url = window.URL.createObjectURL(blob);
                let a = document.createElement('a');
                a.href = url;
                a.download = 'payments_import_template_' + frappe.datetime.now_date() + '.csv';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);

                frappe.show_alert({ message: __('Template downloaded successfully'), indicator: 'green' }, 3);
            }
        },
        error: function(r) {
            frappe.msgprint(__('Error downloading template. Please check console for details.'));
            console.error('Template download error:', r);
        }
    });
}

function validate_import_file(file_url, dialog) {
    frappe.show_alert({ message: __('Reading and validating file...'), indicator: 'blue' });

    fetch(file_url)
        .then(response => response.text())
        .then(content => {
            let data = parse_csv(content);

            if (data.length === 0) {
                frappe.msgprint(__('No data found in file'));
                return;
            }

            frappe.call({
                method: `${PAYMENTS_PY_PATH}.validate_payments_import`,
                args: { data: data },
                callback: function(r) {
                    if (r.message) {
                        display_validation_results(r.message, dialog, data);
                    }
                },
                error: function(r) {
                    frappe.msgprint(__('Validation error. Please check console for details.'));
                    console.error('Validation error:', r);
                }
            });
        })
        .catch(error => {
            frappe.msgprint(__('Error reading file: {0}', [error.message]));
            console.error('File read error:', error);
        });
}

function display_validation_results(results, dialog, data) {
    let html = '';

    if (results.success) {
        html = `
            <div class="alert alert-success">
                <strong><i class="fa fa-check-circle"></i> Validation Successful!</strong><br>
                <p style="margin-top: 10px; margin-bottom: 0;">
                    ${results.validated_count} record(s) ready for import.
                </p>
            </div>
        `;

        dialog.set_primary_action(__('Import Data'), function() {
            import_validated_data(data, dialog);
        });
        dialog.$wrapper.find('.btn-primary').removeClass('btn-primary').addClass('btn-success');
    } else {
        html = `
            <div class="alert alert-danger">
                <strong><i class="fa fa-exclamation-triangle"></i> Validation Failed!</strong><br>
                <p style="margin-top: 10px;">
                    ${results.error_count} error(s) found in ${results.validated_count} record(s).
                    Please fix the following:
                </p>
                <div style="max-height: 300px; overflow-y: auto; margin-top: 10px; padding: 10px; background: #f8f9fa; border-radius: 4px;">
                    <ul style="margin-bottom: 0;">
                        ${results.errors.map(err => `<li>${err}</li>`).join('')}
                    </ul>
                </div>
            </div>
        `;
    }

    dialog.fields_dict.validation_results.$wrapper.html(html);
    dialog.fields_dict.validation_results.$wrapper.show();
}

function import_validated_data(data, dialog) {
    frappe.confirm(
        __('Are you sure you want to import {0} payment record(s)?', [data.length]),
        function() {
            frappe.show_alert({ message: __('Importing payments...'), indicator: 'blue' });

            frappe.call({
                method: `${PAYMENTS_PY_PATH}.import_payments`,
                args: { data: data },
                freeze: true,
                freeze_message: __('Importing {0} payment(s)...', [data.length]),
                callback: function(r) {
                    if (r.message) {
                        display_import_results(r.message);
                        dialog.hide();
                        if (cur_list) {
                            cur_list.refresh();
                        }
                    }
                },
                error: function(r) {
                    frappe.msgprint(__('Import error. Please check console for details.'));
                    console.error('Import error:', r);
                }
            });
        }
    );
}

function display_import_results(results) {
    let message = '';
    let indicator = 'green';

    if (results.success) {
        message = __('Successfully imported {0} payment(s)', [results.imported_count]);
        frappe.show_alert({ message: message, indicator: indicator }, 5);
    } else {
        message = __('Imported {0} payment(s), {1} failed',
            [results.imported_count, results.failed_count]);
        indicator = 'orange';

        let details_html = `
            <div>
                <div class="alert alert-${results.imported_count > 0 ? 'warning' : 'danger'}">
                    <strong>Import Summary:</strong><br>
                    ✓ Successful: ${results.imported_count}<br>
                    ✗ Failed: ${results.failed_count}
                </div>
        `;

        if (results.imported.length > 0) {
            details_html += `
                <div style="margin-top: 15px;">
                    <strong>Successfully Imported:</strong>
                    <ul>
                        ${results.imported.map(item =>
                            `<li>Row ${item.row}: <a href="/app/payments/${item.name}">${item.name}</a></li>`
                        ).join('')}
                    </ul>
                </div>
            `;
        }

        if (results.failed.length > 0) {
            details_html += `
                <div style="margin-top: 15px;">
                    <strong>Failed Records:</strong>
                    <div style="max-height: 300px; overflow-y: auto; padding: 10px; background: #f8f9fa; border-radius: 4px;">
                        <ul>
                            ${results.failed.map(f =>
                                `<li><strong>Row ${f.row}:</strong> ${f.error}</li>`
                            ).join('')}
                        </ul>
                    </div>
                </div>
            `;
        }

        details_html += '</div>';

        frappe.msgprint({
            title: __('Import Results'),
            message: details_html,
            indicator: indicator,
            primary_action: {
                label: __('Download Error Report'),
                action: function() {
                    download_error_report(results.failed);
                }
            }
        });
    }
}

function download_error_report(failed_records) {
    let csv_content = 'Row Number,Error Message\n';
    csv_content += failed_records.map(f =>
        `${f.row},"${f.error.replace(/"/g, '""')}"`
    ).join('\n');

    let blob = new Blob([csv_content], { type: 'text/csv;charset=utf-8;' });
    let url = window.URL.createObjectURL(blob);
    let a = document.createElement('a');
    a.href = url;
    a.download = 'payment_import_errors_' + frappe.datetime.now_datetime() + '.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

function parse_csv(content) {
    let lines = content.split(/\r\n|\n|\r/);

    if (lines.length < 2) {
        frappe.msgprint(__('File appears to be empty or invalid'));
        return [];
    }

    let headers = parse_csv_line(lines[0]);
    let data = [];

    for (let i = 1; i < lines.length; i++) {
        if (lines[i].trim()) {
            let values = parse_csv_line(lines[i]);
            let row = {};

            for (let j = 0; j < headers.length; j++) {
                row[headers[j].trim()] = values[j] ? values[j].trim() : '';
            }

            data.push(row);
        }
    }

    return data;
}

function parse_csv_line(line) {
    let result = [];
    let current = '';
    let inQuotes = false;

    for (let i = 0; i < line.length; i++) {
        let char = line[i];

        if (char === '"') {
            if (inQuotes && line[i + 1] === '"') {
                current += '"';
                i++;
            } else {
                inQuotes = !inQuotes;
            }
        } else if (char === ',' && !inQuotes) {
            result.push(current);
            current = '';
        } else {
            current += char;
        }
    }

    result.push(current);
    return result;
}

// ==================== Dashboard Dialog ====================
// New — previously payments_dashboard.py had whitelisted endpoints but no
// consuming UI in anything you'd shared, so the dashboard logic was dead
// code from the list view's perspective. This wires it up minimally.

function show_dashboard_dialog(listview) {
    let d = new frappe.ui.Dialog({
        title: __('Payments Dashboard'),
        size: 'extra-large',
        fields: [
            {
                fieldname: 'company',
                fieldtype: 'Link',
                options: 'Company',
                label: __('Company'),
                default: frappe.defaults.get_user_default('Company'),
                reqd: 1
            },
            { fieldname: 'col_break_dash1', fieldtype: 'Column Break' },
            {
                fieldname: 'from_date',
                fieldtype: 'Date',
                label: __('From Date'),
                default: frappe.datetime.add_days(frappe.datetime.now_date(), -30)
            },
            { fieldname: 'col_break_dash2', fieldtype: 'Column Break' },
            {
                fieldname: 'to_date',
                fieldtype: 'Date',
                label: __('To Date'),
                default: frappe.datetime.now_date()
            },
            { fieldname: 'section_dash_results', fieldtype: 'Section Break' },
            { fieldname: 'dashboard_results', fieldtype: 'HTML' }
        ],
        primary_action_label: __('Refresh'),
        primary_action(values) {
            load_dashboard_data(values, d);
        }
    });

    d.show();
    load_dashboard_data(d.get_values() || {
        company: frappe.defaults.get_user_default('Company'),
        from_date: frappe.datetime.add_days(frappe.datetime.now_date(), -30),
        to_date: frappe.datetime.now_date()
    }, d);
}

function load_dashboard_data(values, dialog) {
    if (!values.company) return;

    dialog.fields_dict.dashboard_results.$wrapper.html(
        '<div class="text-muted" style="padding: 20px;">Loading...</div>');

    frappe.call({
        method: `${PAYMENTS_PY_PATH}.get_payment_dashboard_data`,
        args: {
            company: values.company,
            from_date: values.from_date,
            to_date: values.to_date
        },
        callback: function(r) {
            if (r.message) {
                dialog.fields_dict.dashboard_results.$wrapper.html(render_dashboard_html(r.message));
            }
        },
        error: function(r) {
            dialog.fields_dict.dashboard_results.$wrapper.html(
                '<div class="alert alert-danger">Failed to load dashboard data.</div>');
            console.error('Dashboard load error:', r);
        }
    });
}

function render_dashboard_html(data) {
    let cards = data.summary_cards || {};
    let ifrs = data.cashflow_ifrs_summary || {};

    let card = (label, value, sub) => `
        <div style="flex: 1; min-width: 150px; background: #f8f9fa; border-radius: 8px; padding: 15px; margin: 5px;">
            <div style="font-size: 12px; color: #6c757d;">${label}</div>
            <div style="font-size: 22px; font-weight: bold;">${value}</div>
            ${sub ? `<div style="font-size: 11px; color: #6c757d;">${sub}</div>` : ''}
        </div>
    `;

    let html = `
        <div style="display: flex; flex-wrap: wrap; margin-bottom: 15px;">
            ${card(__('Total Payments'), cards.total_payments ? cards.total_payments.value : 0)}
            ${card(__('Total Amount'), format_currency(cards.total_amount ? cards.total_amount.value : 0))}
            ${card(__('Avg Payment'), format_currency(cards.avg_payment ? cards.avg_payment.value : 0))}
            ${card(__('Total WHT'), format_currency(cards.total_wht ? cards.total_wht.value : 0))}
            ${card(__('Completed'), cards.completed || 0)}
            ${card(__('Pending'), cards.pending || 0)}
            ${card(__('Failed'), cards.failed || 0)}
        </div>

        <h5>${__('Cashflow — IFRS Summary')}</h5>
        <div style="display: flex; flex-wrap: wrap; margin-bottom: 15px;">
            ${Object.keys(ifrs).map(k => card(
                k, format_currency(ifrs[k].amount), ifrs[k].percentage + '%'
            )).join('')}
        </div>

        <h5>${__('By Transaction Type')}</h5>
        ${render_simple_table(data.transaction_type_summary, ['trans_type', 'count', 'amount'])}

        <h5>${__('By Cash Flow Classification')}</h5>
        ${render_simple_table(data.cashflow_breakdown, ['cashflow_type', 'count', 'amount'])}

        <h5>${__('Top Payees')}</h5>
        ${render_simple_table(data.top_payees, ['payee', 'payment_count', 'total_amount'])}
    `;

    return html;
}

function render_simple_table(rows, columns) {
    if (!rows || rows.length === 0) {
        return '<div class="text-muted" style="margin-bottom: 15px;">No data</div>';
    }

    let is_currency_col = (col) => /amount/i.test(col);

    let html = '<table class="table table-bordered table-sm" style="margin-bottom: 15px;"><tbody>';
    rows.forEach(row => {
        html += '<tr>';
        columns.forEach(col => {
            let val = row[col];
            if (is_currency_col(col)) val = format_currency(val || 0);
            html += `<td>${val != null ? val : ''}</td>`;
        });
        html += '</tr>';
    });
    html += '</tbody></table>';

    return html;
}
