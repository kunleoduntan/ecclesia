// payments_list.js
frappe.listview_settings['Payments'] = {
    onload: function(listview) {
        // Add Import Payments button to the menu
        listview.page.add_menu_item(__('Import Payments'), function() {
            show_import_dialog(listview);
        }, true);
        
        // OR add as action button in the toolbar
        listview.page.add_action_item(__('Import Payments'), function() {
            show_import_dialog(listview);
        });
    },
    
    // Optional: Add button for each row
    button: {
        show(doc) {
            return doc.payment_status === 'Draft';
        },
        get_label() {
            return __('Process Payment');
        },
        get_description(doc) {
            return __('Process this payment');
        },
        action(doc) {
            frappe.msgprint(__('Processing payment: {0}', [doc.name]));
        }
    }
};

function show_import_dialog(listview) {
    let d = new frappe.ui.Dialog({
        title: __('Import Payments'),
        size: 'large',
        fields: [
            {
                label: __('Step 1: Download Template'),
                fieldtype: 'Section Break'
            },
            {
                fieldtype: 'HTML',
                options: `
                    <div class="alert alert-info" style="margin-bottom: 15px;">
                        <strong><i class="fa fa-info-circle"></i> Instructions:</strong>
                        <ol style="margin-top: 10px; margin-bottom: 0;">
                            <li>Download the Excel/CSV template below</li>
                            <li>Fill in your payment data (mandatory fields marked with *)</li>
                            <li>Upload the completed file</li>
                            <li>Review validation results</li>
                            <li>Import valid records</li>
                        </ol>
                    </div>
                    <button class="btn btn-primary btn-sm" id="download-template-btn">
                        <i class="fa fa-download"></i> Download Template
                    </button>
                `
            },
            {
                label: __('Step 2: Upload Filled Template'),
                fieldtype: 'Section Break'
            },
            {
                label: __('Import File'),
                fieldname: 'import_file',
                fieldtype: 'Attach',
                reqd: 1,
                description: __('Upload CSV or Excel file with payment data')
            },
            {
                label: __('Step 3: Validation Results'),
                fieldtype: 'Section Break',
                depends_on: 'eval:doc.import_file'
            },
            {
                fieldname: 'validation_results',
                fieldtype: 'HTML'
            }
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
    
    // Add click handler for download button
    d.$wrapper.find('#download-template-btn').on('click', function() {
        download_template();
    });
}

function download_template() {
    frappe.call({
        method: 'general.general_biz_apps.doctype.payments.payments_import_handler.get_payments_import_template',
        callback: function(r) {
            if (r.message) {
                // Create CSV content
                let csv_content = r.message.columns.join(',') + '\n';
                csv_content += r.message.sample_data.map(item => {
                    // Escape commas and quotes in data
                    if (typeof item === 'string' && (item.includes(',') || item.includes('"'))) {
                        return '"' + item.replace(/"/g, '""') + '"';
                    }
                    return item;
                }).join(',');
                
                // Download CSV
                let blob = new Blob([csv_content], { type: 'text/csv;charset=utf-8;' });
                let url = window.URL.createObjectURL(blob);
                let a = document.createElement('a');
                a.href = url;
                a.download = 'payments_import_template_' + frappe.datetime.now_date() + '.csv';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                frappe.show_alert({
                    message: __('Template downloaded successfully'),
                    indicator: 'green'
                }, 3);
            }
        },
        error: function(r) {
            frappe.msgprint(__('Error downloading template. Please check console for details.'));
            console.error('Template download error:', r);
        }
    });
}

function validate_import_file(file_url, dialog) {
    frappe.show_alert({
        message: __('Reading and validating file...'),
        indicator: 'blue'
    });
    
    // Get file content
    fetch(file_url)
        .then(response => response.text())
        .then(content => {
            let data = parse_csv(content);
            
            if (data.length === 0) {
                frappe.msgprint(__('No data found in file'));
                return;
            }
            
            frappe.call({
                method: 'general.general_biz_apps.doctype.payments.payments_import_handler.validate_payments_import',
                args: {
                    data: data
                },
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
        
        // Change dialog primary action to Import
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
            frappe.show_alert({
                message: __('Importing payments...'),
                indicator: 'blue'
            });
            
            frappe.call({
                method: 'general.general_biz_apps.doctype.payments.payments_import_handler.import_payments',
                args: {
                    data: data
                },
                freeze: true,
                freeze_message: __('Importing {0} payment(s)...', [data.length]),
                callback: function(r) {
                    if (r.message) {
                        display_import_results(r.message);
                        dialog.hide();
                        
                        // Refresh list view
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
        
        frappe.show_alert({
            message: message,
            indicator: indicator
        }, 5);
        
    } else {
        message = __('Imported {0} payment(s), {1} failed', 
            [results.imported_count, results.failed_count]);
        indicator = 'orange';
        
        // Show detailed results in a dialog
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
    // Split by newline, handling different line endings
    let lines = content.split(/\r\n|\n|\r/);
    
    if (lines.length < 2) {
        frappe.msgprint(__('File appears to be empty or invalid'));
        return [];
    }
    
    // Parse header line
    let headers = parse_csv_line(lines[0]);
    let data = [];
    
    // Parse data lines
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
    // Simple CSV parser that handles quoted fields with commas
    let result = [];
    let current = '';
    let inQuotes = false;
    
    for (let i = 0; i < line.length; i++) {
        let char = line[i];
        
        if (char === '"') {
            if (inQuotes && line[i + 1] === '"') {
                // Escaped quote
                current += '"';
                i++;
            } else {
                // Toggle quote state
                inQuotes = !inQuotes;
            }
        } else if (char === ',' && !inQuotes) {
            // Field separator
            result.push(current);
            current = '';
        } else {
            current += char;
        }
    }
    
    // Add last field
    result.push(current);
    
    return result;
}