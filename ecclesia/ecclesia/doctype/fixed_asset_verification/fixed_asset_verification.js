// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt

// Copyright (c) 2026, Ecclesia and contributors
// For license information, please see license.txt

frappe.ui.form.on('Fixed Asset Verification', {
    refresh: function(frm) {
        add_verification_buttons(frm);
        setup_qr_scanner(frm);
        update_verification_progress(frm);
    },
    
    onload: function(frm) {
        setup_filters(frm);
    }
});

frappe.ui.form.on('Asset Verification Details', {
    verified: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        // Auto-check if location matches
        if (row.verified && row.actual_location === row.expected_location) {
            frappe.model.set_value(cdt, cdn, 'discrepancy', 0);
        }
        
        update_verification_progress(frm);
    },
    
    actual_location: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        // Check for location mismatch
        if (row.actual_location && row.expected_location && 
            row.actual_location !== row.expected_location) {
            frappe.model.set_value(cdt, cdn, 'discrepancy', 1);
            frappe.model.set_value(cdt, cdn, 'discrepancy_type', 'Location Mismatch');
        }
    },
    
    physical_condition: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        // Flag issues based on condition
        if (['Missing', 'Damaged', 'Poor'].includes(row.physical_condition)) {
            frappe.model.set_value(cdt, cdn, 'discrepancy', 1);
            
            if (row.physical_condition === 'Missing') {
                frappe.model.set_value(cdt, cdn, 'discrepancy_type', 'Missing');
            } else if (row.physical_condition === 'Damaged') {
                frappe.model.set_value(cdt, cdn, 'discrepancy_type', 'Damaged');
            }
        }
    }
});

function add_verification_buttons(frm) {
    if (frm.doc.docstatus === 0) {
        // Get Assets button
        frm.add_custom_button(__('Get Assets'), function() {
            get_assets_for_verification(frm);
        }).addClass('btn-primary');
        
        // QR Scanner button
        frm.add_custom_button(__('Scan QR Code'), function() {
            open_qr_scanner(frm);
        }, __('Tools'));
        
        // Bulk verify button
        if (frm.doc.verification_details && frm.doc.verification_details.length > 0) {
            frm.add_custom_button(__('Bulk Verify Selected'), function() {
                bulk_verify_assets(frm);
            }, __('Actions'));
        }
    }
    
    if (frm.doc.docstatus === 1) {
        // Generate report
        frm.add_custom_button(__('Download Report'), function() {
            download_verification_report(frm);
        }, __('Reports'));
        
        // View discrepancies
        if (frm.doc.assets_with_discrepancies > 0) {
            frm.add_custom_button(__('View Discrepancies'), function() {
                show_discrepancies(frm);
            }, __('View'));
        }
    }
    
    // Export to Excel
    frm.add_custom_button(__('Export to Excel'), function() {
        export_verification_to_excel(frm);
    }, __('Tools'));
}

function get_assets_for_verification(frm) {
    if (!frm.doc.company) {
        frappe.msgprint(__('Please select Company first'));
        return;
    }
    
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.fixed_asset_verification.fixed_asset_verification.get_assets_for_verification',
        args: {
            company: frm.doc.company,
            asset_category: frm.doc.asset_category,
            location: frm.doc.location,
            department: frm.doc.department,
            cost_center: frm.doc.cost_center
        },
        callback: function(r) {
            if (r.message) {
                frm.clear_table('verification_details');
                
                $.each(r.message, function(i, asset) {
                    let row = frm.add_child('verification_details');
                    $.extend(row, asset);
                });
                
                frm.refresh_field('verification_details');
                update_verification_progress(frm);
                
                frappe.show_alert({
                    message: __('Loaded {0} assets for verification', [r.message.length]),
                    indicator: 'green'
                });
            }
        }
    });
}

function setup_qr_scanner(frm) {
    // Initialize QR scanner if available
    if (frm.doc.docstatus === 0) {
        // QR scanner setup would go here
        // This would typically use a library like jsQR or html5-qrcode
    }
}

function open_qr_scanner(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Scan QR Code'),
        fields: [
            {
                fieldname: 'scanner',
                fieldtype: 'HTML',
                options: `
                    <div class="qr-scanner-container">
                        <div id="qr-reader" style="width: 100%; max-width: 500px; margin: 0 auto;"></div>
                        <div id="qr-result" class="text-center" style="margin-top: 20px;"></div>
                    </div>
                `
            },
            {
                fieldname: 'manual_entry',
                fieldtype: 'Section Break',
                label: __('Or Enter Asset Code Manually')
            },
            {
                fieldname: 'asset_code',
                fieldtype: 'Data',
                label: __('Asset Code')
            }
        ],
        primary_action_label: __('Verify'),
        primary_action: function(values) {
            if (values.asset_code) {
                mark_asset_verified(frm, values.asset_code);
                d.hide();
            }
        }
    });
    
    d.show();
    
    // Initialize QR scanner
    initialize_qr_scanner(frm);
}

function initialize_qr_scanner(frm) {
    // QR scanner initialization
    // This would use html5-qrcode library
    // Implementation placeholder
}

function mark_asset_verified(frm, asset_code) {
    let found = false;
    
    $.each(frm.doc.verification_details || [], function(i, row) {
        if (row.asset_code === asset_code) {
            frappe.model.set_value(row.doctype, row.name, 'qr_code_scanned', 1);
            frappe.model.set_value(row.doctype, row.name, 'scan_timestamp', frappe.datetime.now_datetime());
            frappe.model.set_value(row.doctype, row.name, 'verified', 1);
            frappe.model.set_value(row.doctype, row.name, 'verified_by', frappe.session.user);
            
            found = true;
            
            frappe.show_alert({
                message: __('Asset {0} marked as verified', [asset_code]),
                indicator: 'green'
            });
            
            return false; // break loop
        }
    });
    
    if (!found) {
        frappe.msgprint(__('Asset {0} not found in verification list', [asset_code]));
    }
    
    update_verification_progress(frm);
}

function bulk_verify_assets(frm) {
    let selected = [];
    
    // Get selected rows
    $.each(frm.fields_dict.verification_details.grid.get_selected_children() || [], function(i, row) {
        selected.push(row.name);
    });
    
    if (selected.length === 0) {
        frappe.msgprint(__('Please select assets to verify'));
        return;
    }
    
    let d = new frappe.ui.Dialog({
        title: __('Bulk Verify Assets'),
        fields: [
            {
                fieldname: 'physical_condition',
                fieldtype: 'Select',
                label: __('Physical Condition'),
                options: 'Excellent\nGood\nFair\nPoor\nMissing\nDamaged',
                default: 'Good',
                reqd: 1
            },
            {
                fieldname: 'remarks',
                fieldtype: 'Small Text',
                label: __('Remarks')
            }
        ],
        primary_action_label: __('Verify'),
        primary_action: function(values) {
            $.each(selected, function(i, name) {
                frappe.model.set_value('Asset Verification Details', name, 'verified', 1);
                frappe.model.set_value('Asset Verification Details', name, 'physical_condition', values.physical_condition);
                frappe.model.set_value('Asset Verification Details', name, 'remarks', values.remarks);
                frappe.model.set_value('Asset Verification Details', name, 'verified_by', frappe.session.user);
            });
            
            update_verification_progress(frm);
            
            frappe.show_alert({
                message: __('Verified {0} assets', [selected.length]),
                indicator: 'green'
            });
            
            d.hide();
        }
    });
    
    d.show();
}

function update_verification_progress(frm) {
    if (!frm.doc.verification_details) return;
    
    let total = frm.doc.verification_details.length;
    let verified = 0;
    let missing = 0;
    let discrepancies = 0;
    
    $.each(frm.doc.verification_details, function(i, row) {
        if (row.verified) verified++;
        if (row.physical_condition === 'Missing') missing++;
        if (row.discrepancy) discrepancies++;
    });
    
    frm.set_value('total_assets_to_verify', total);
    frm.set_value('assets_verified', verified);
    frm.set_value('assets_missing', missing);
    frm.set_value('assets_with_discrepancies', discrepancies);
    
    if (total > 0) {
        let percentage = (verified / total) * 100;
        frm.set_value('verification_completion_percentage', percentage);
        
        // Add progress bar
        update_progress_bar(frm, percentage);
    }
}

function update_progress_bar(frm, percentage) {
    let color = 'green';
    if (percentage < 50) color = 'red';
    else if (percentage < 80) color = 'orange';
    
    frm.dashboard.add_progress(__('Verification Progress'), percentage, 
        __('Verified {0} of {1} assets', [frm.doc.assets_verified, frm.doc.total_assets_to_verify]));
}

function show_discrepancies(frm) {
    let discrepancies = [];
    
    $.each(frm.doc.verification_details || [], function(i, row) {
        if (row.discrepancy) {
            discrepancies.push(row);
        }
    });
    
    if (discrepancies.length === 0) {
        frappe.msgprint(__('No discrepancies found'));
        return;
    }
    
    let html = '<table class="table table-bordered"><thead><tr>' +
               '<th>Asset Code</th><th>Asset Name</th><th>Discrepancy Type</th><th>Remarks</th>' +
               '</tr></thead><tbody>';
    
    $.each(discrepancies, function(i, disc) {
        html += `<tr>
            <td>${disc.asset_code}</td>
            <td>${disc.asset_name}</td>
            <td>${disc.discrepancy_type || ''}</td>
            <td>${disc.remarks || ''}</td>
        </tr>`;
    });
    
    html += '</tbody></table>';
    
    frappe.msgprint({
        title: __('Assets with Discrepancies'),
        message: html,
        wide: true
    });
}

function download_verification_report(frm) {
    frappe.call({
        method: 'ecclesia.ecclesia.utils.excel_utils.export_to_excel',
        args: {
            doctype: 'Fixed Asset Verification',
            filters: {name: frm.doc.name}
        }
    });
}

function export_verification_to_excel(frm) {
    frappe.call({
        method: 'ecclesia.ecclesia.utils.excel_utils.export_to_excel',
        args: {
            doctype: 'Fixed Asset Verification',
            filters: {name: frm.doc.name}
        }
    });
}

function setup_filters(frm) {
    // Set filters for asset category multiselect
    frm.set_query('asset_category', function() {
        return {
            filters: {
                'disabled': 0
            }
        };
    });
    
    // Set filters for location
    frm.set_query('location', function() {
        return {
            filters: {
                'is_group': 0,
                'disabled': 0
            }
        };
    });
}