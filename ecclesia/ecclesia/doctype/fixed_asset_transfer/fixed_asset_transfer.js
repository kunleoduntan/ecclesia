// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt

// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

frappe.ui.form.on('Fixed Asset Transfer', {
    refresh: function(frm) {
        add_transfer_buttons(frm);
        set_transfer_indicators(frm);
        setup_transfer_workflow(frm);
        show_transfer_summary(frm);
        setup_filters(frm);
    },
    
    onload: function(frm) {
        setup_filters(frm);
        
        if (frm.is_new() && !frm.doc.transfer_date) {
            frm.set_value('transfer_date', frappe.datetime.get_today());
        }
    },
    
    company: function(frm) {
        frm.set_value('transfer_items', []);
    },
    
    transfer_type: function(frm) {
        update_required_fields(frm);
        show_transfer_type_guidance(frm);
    },
    
    from_location: function(frm) {
        validate_same_source_destination(frm);
    },
    
    to_location: function(frm) {
        validate_same_source_destination(frm);
    },
    
    from_department: function(frm) {
        validate_same_source_destination(frm);
    },
    
    to_department: function(frm) {
        validate_same_source_destination(frm);
    },
    
    transfer_items: function(frm) {
        calculate_totals(frm);
    }
});

// Child table events
frappe.ui.form.on('Fixed Asset Transfer Item', {
    asset: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        if (row.asset) {
            fetch_asset_details(frm, cdt, cdn, row.asset);
        }
    },
    
    transfer_items_add: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, 'condition_at_transfer', 'Good');
    },
    
    transfer_items_remove: function(frm) {
        calculate_totals(frm);
    },
    
    current_book_value: function(frm) {
        calculate_totals(frm);
    }
});

function add_transfer_buttons(frm) {
    if (frm.doc.docstatus === 1) {
        // Status workflow buttons
        if (frm.doc.status === 'Approved') {
            frm.add_custom_button(__('Mark as In Transit'), function() {
                update_transfer_status(frm, 'In Transit', 'mark_in_transit');
            }, __('Actions')).addClass('btn-warning');
        }
        
        if (frm.doc.status === 'In Transit') {
            frm.add_custom_button(__('Mark as Delivered'), function() {
                mark_as_delivered(frm);
            }, __('Actions')).addClass('btn-primary');
        }
        
        if (frm.doc.status === 'Delivered') {
            frm.add_custom_button(__('Confirm Receipt'), function() {
                confirm_receipt_dialog(frm);
            }, __('Actions')).addClass('btn-success');
        }
        
        // View links
        frm.add_custom_button(__('Transfer History'), function() {
            show_asset_transfer_history(frm);
        }, __('View'));
        
        // Print options
        frm.add_custom_button(__('Print Transfer Note'), function() {
            print_transfer_note(frm);
        }, __('Print'));
        
        frm.add_custom_button(__('Print Delivery Receipt'), function() {
            print_delivery_receipt(frm);
        }, __('Print'));
    }
    
    // Add assets button
    if (frm.doc.docstatus === 0) {
        frm.add_custom_button(__('Add Multiple Assets'), function() {
            add_multiple_assets_dialog(frm);
        }, __('Tools')).addClass('btn-primary');
        
        frm.add_custom_button(__('Scan QR Code'), function() {
            scan_asset_qr_code(frm);
        }, __('Tools'));
    }
    
    // Export button
    frm.add_custom_button(__('Export to Excel'), function() {
        export_transfer_to_excel(frm);
    }, __('Tools'));
}

function set_transfer_indicators(frm) {
    const status_config = {
        'Draft': { color: 'gray', icon: '📝' },
        'Pending Approval': { color: 'orange', icon: '⏳' },
        'Approved': { color: 'blue', icon: '✅' },
        'In Transit': { color: 'yellow', icon: '🚚' },
        'Delivered': { color: 'light-blue', icon: '📦' },
        'Received': { color: 'green', icon: '✅' },
        'Cancelled': { color: 'red', icon: '❌' }
    };
    
    if (frm.doc.status && status_config[frm.doc.status]) {
        let config = status_config[frm.doc.status];
        frm.page.set_indicator(
            `${config.icon} ${frm.doc.status}`, 
            config.color
        );
    }
}

function setup_transfer_workflow(frm) {
    if (frm.doc.docstatus === 1) {
        // Create beautiful workflow progress bar
        let workflow_html = get_workflow_html(frm);
        frm.dashboard.add_section(workflow_html, __('Transfer Progress'));
        
        // Add timeline info
        add_timeline_info(frm);
    }
}

function get_workflow_html(frm) {
    const steps = [
        { 
            label: 'Approved', 
            status: 'Approved', 
            field: 'approval_date',
            user: 'approved_by',
            completed: true 
        },
        { 
            label: 'In Transit', 
            status: 'In Transit', 
            field: null,
            user: null,
            completed: ['In Transit', 'Delivered', 'Received'].includes(frm.doc.status) 
        },
        { 
            label: 'Delivered', 
            status: 'Delivered', 
            field: 'delivery_date',
            user: 'delivered_by',
            completed: ['Delivered', 'Received'].includes(frm.doc.status) 
        },
        { 
            label: 'Received', 
            status: 'Received', 
            field: 'receipt_date',
            user: 'received_by',
            completed: frm.doc.status === 'Received' 
        }
    ];
    
    let html = `
    <div class="transfer-workflow" style="margin: 20px 0;">
        <style>
            .workflow-container {
                display: flex;
                justify-content: space-between;
                align-items: center;
                position: relative;
                margin: 30px 0;
            }
            .workflow-step {
                flex: 1;
                text-align: center;
                position: relative;
                z-index: 2;
            }
            .step-circle {
                width: 50px;
                height: 50px;
                margin: 0 auto;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 20px;
                font-weight: bold;
                transition: all 0.3s ease;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            .step-circle.completed {
                background: linear-gradient(135deg, #00a82d 0%, #00d437 100%);
                color: white;
            }
            .step-circle.active {
                background: linear-gradient(135deg, #2e86de 0%, #54a0ff 100%);
                color: white;
                animation: pulse 2s infinite;
            }
            .step-circle.pending {
                background: #e9ecef;
                color: #6c757d;
                border: 2px solid #dee2e6;
            }
            @keyframes pulse {
                0%, 100% { box-shadow: 0 0 0 0 rgba(46, 134, 222, 0.7); }
                50% { box-shadow: 0 0 0 10px rgba(46, 134, 222, 0); }
            }
            .step-label {
                margin-top: 12px;
                font-size: 13px;
                font-weight: 600;
                color: #495057;
            }
            .step-info {
                margin-top: 8px;
                font-size: 11px;
                color: #6c757d;
                line-height: 1.4;
            }
            .workflow-line {
                position: absolute;
                top: 25px;
                left: 0;
                right: 0;
                height: 3px;
                background: #e9ecef;
                z-index: 1;
            }
            .workflow-line-progress {
                height: 100%;
                background: linear-gradient(90deg, #00a82d 0%, #00d437 100%);
                transition: width 0.5s ease;
            }
        </style>
        
        <div class="workflow-container">
            <div class="workflow-line">
                <div class="workflow-line-progress" style="width: ${get_progress_percentage(frm)}%"></div>
            </div>
    `;
    
    steps.forEach((step, index) => {
        let circle_class = 'pending';
        let icon = index + 1;
        
        if (step.completed) {
            circle_class = 'completed';
            icon = '✓';
        } else if (frm.doc.status === step.status) {
            circle_class = 'active';
            icon = '●';
        }
        
        let step_info = '';
        if (step.completed && step.field && frm.doc[step.field]) {
            step_info += `<div>${frappe.datetime.str_to_user(frm.doc[step.field])}</div>`;
        }
        if (step.completed && step.user && frm.doc[step.user]) {
            step_info += `<div>by ${frm.doc[step.user]}</div>`;
        }
        
        html += `
            <div class="workflow-step">
                <div class="step-circle ${circle_class}">${icon}</div>
                <div class="step-label">${step.label}</div>
                <div class="step-info">${step_info}</div>
            </div>
        `;
    });
    
    html += '</div></div>';
    
    return html;
}

function get_progress_percentage(frm) {
    const status_progress = {
        'Approved': 25,
        'In Transit': 50,
        'Delivered': 75,
        'Received': 100
    };
    
    return status_progress[frm.doc.status] || 0;
}

function add_timeline_info(frm) {
    frm.dashboard.clear_comment();
    
    if (frm.doc.status === 'Delivered') {
        frm.dashboard.add_comment(
            __('⚠️ Assets have been delivered. Awaiting confirmation of receipt from {0}.', 
                [frm.doc.to_custodian || 'receiving party']),
            'orange',
            true
        );
    } else if (frm.doc.status === 'In Transit') {
        frm.dashboard.add_comment(
            __('🚚 Assets are currently in transit to {0}.', 
                [frm.doc.to_location || 'destination']),
            'blue',
            true
        );
    }
}

function show_transfer_summary(frm) {
    if (!frm.doc.docstatus) return;
    
    frm.dashboard.clear_headline();
    
    // Show asset count
    if (frm.doc.total_assets) {
        frm.dashboard.add_indicator(
            __('Total Assets: {0}', [frm.doc.total_assets]), 
            'blue'
        );
    }
    
    // Show total value
    if (frm.doc.total_book_value) {
        frm.dashboard.add_indicator(
            __('Total Value: {0}', [format_currency(frm.doc.total_book_value)]), 
            'green'
        );
    }
    
    // Show transfer route
    if (frm.doc.from_location && frm.doc.to_location) {
        frm.dashboard.add_indicator(
            __('Route: {0} → {1}', [frm.doc.from_location, frm.doc.to_location]), 
            'orange'
        );
    }
}

function fetch_asset_details(frm, cdt, cdn, asset) {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.fixed_asset_transfer.fixed_asset_transfer.get_asset_transfer_details',
        args: { asset: asset },
        callback: function(r) {
            if (r.message) {
                frappe.model.set_value(cdt, cdn, 'asset_code', r.message.asset_code);
                frappe.model.set_value(cdt, cdn, 'asset_name', r.message.asset_name);
                frappe.model.set_value(cdt, cdn, 'current_location', r.message.current_location);
                frappe.model.set_value(cdt, cdn, 'current_custodian', r.message.current_custodian);
                frappe.model.set_value(cdt, cdn, 'current_book_value', r.message.current_book_value);
                
                // Auto-populate from fields from first asset
                if (!frm.doc.from_location && r.message.current_location) {
                    frm.set_value('from_location', r.message.current_location);
                }
                if (!frm.doc.from_cost_center && r.message.cost_center) {
                    frm.set_value('from_cost_center', r.message.cost_center);
                }
                if (!frm.doc.from_department && r.message.department) {
                    frm.set_value('from_department', r.message.department);
                }
                
                frappe.show_alert({
                    message: __('✓ Asset details loaded'),
                    indicator: 'green'
                }, 2);
            }
        }
    });
}

function calculate_totals(frm) {
    if (!frm.doc.transfer_items) return;
    
    let total_assets = frm.doc.transfer_items.length;
    let total_value = 0;
    
    frm.doc.transfer_items.forEach(function(item) {
        total_value += flt(item.current_book_value);
    });
    
    frm.set_value('total_assets', total_assets);
    frm.set_value('total_book_value', total_value);
}

function update_required_fields(frm) {
    let type = frm.doc.transfer_type;
    
    // Reset all requirements
    frm.set_df_property('to_location', 'reqd', 0);
    frm.set_df_property('to_department', 'reqd', 0);
    frm.set_df_property('to_custodian', 'reqd', 0);
    frm.set_df_property('to_cost_center', 'reqd', 0);
    
    // Set based on type
    if (type === 'Complete Transfer') {
        frm.set_df_property('to_location', 'reqd', 1);
        frm.set_df_property('to_department', 'reqd', 1);
        frm.set_df_property('to_cost_center', 'reqd', 1);
    } else if (type === 'Location Change') {
        frm.set_df_property('to_location', 'reqd', 1);
    } else if (type === 'Department Change') {
        frm.set_df_property('to_department', 'reqd', 1);
    } else if (type === 'Custodian Change') {
        frm.set_df_property('to_custodian', 'reqd', 1);
    } else if (type === 'Cost Center Change') {
        frm.set_df_property('to_cost_center', 'reqd', 1);
    }
}

function show_transfer_type_guidance(frm) {
    if (!frm.doc.transfer_type) return;
    
    const guidance = {
        'Location Change': '📍 Only the physical location will change. Department, custodian, and cost center remain the same.',
        'Department Change': '🏢 Only the department will change. Location, custodian, and cost center remain the same.',
        'Custodian Change': '👤 Only the custodian will change. Location, department, and cost center remain the same.',
        'Cost Center Change': '💼 Only the cost center will change. Location, department, and custodian remain the same.',
        'Complete Transfer': '🔄 All fields will be updated: Location, Department, Custodian, and Cost Center.'
    };
    
    frm.set_df_property('transfer_type', 'description', guidance[frm.doc.transfer_type] || '');
}

function validate_same_source_destination(frm) {
    if (frm.doc.transfer_type === 'Location Change') {
        if (frm.doc.from_location && frm.doc.to_location && 
            frm.doc.from_location === frm.doc.to_location) {
            frappe.msgprint({
                title: __('Invalid Transfer'),
                message: __('From Location and To Location cannot be the same'),
                indicator: 'red'
            });
            frm.set_value('to_location', '');
        }
    }
    
    if (frm.doc.transfer_type === 'Department Change') {
        if (frm.doc.from_department && frm.doc.to_department && 
            frm.doc.from_department === frm.doc.to_department) {
            frappe.msgprint({
                title: __('Invalid Transfer'),
                message: __('From Department and To Department cannot be the same'),
                indicator: 'red'
            });
            frm.set_value('to_department', '');
        }
    }
}

function update_transfer_status(frm, status, method) {
    frappe.confirm(
        __('Update transfer status to <strong>{0}</strong>?', [status]),
        function() {
            frappe.call({
                method: `ecclesia.ecclesia.doctype.fixed_asset_transfer.fixed_asset_transfer.${method}`,
                args: { transfer_name: frm.doc.name },
                freeze: true,
                freeze_message: __('Updating status...'),
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frm.reload_doc();
                        frappe.show_alert({
                            message: __('✓ {0}', [r.message.message]),
                            indicator: 'green'
                        }, 5);
                    }
                }
            });
        }
    );
}

function mark_as_delivered(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Mark as Delivered'),
        fields: [
            {
                fieldname: 'delivered_by',
                fieldtype: 'Link',
                label: __('Delivered By'),
                options: 'User',
                reqd: 1,
                default: frappe.session.user
            },
            {
                fieldname: 'delivery_notes',
                fieldtype: 'Small Text',
                label: __('Delivery Notes')
            }
        ],
        primary_action_label: __('Mark as Delivered'),
        primary_action: function(values) {
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.fixed_asset_transfer.fixed_asset_transfer.mark_delivered',
                args: {
                    transfer_name: frm.doc.name,
                    delivered_by: values.delivered_by
                },
                freeze: true,
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frm.reload_doc();
                        d.hide();
                        frappe.show_alert({
                            message: __('✓ Transfer marked as delivered. Email sent to receiver.'),
                            indicator: 'green'
                        }, 7);
                    }
                }
            });
        }
    });
    d.show();
}

function confirm_receipt_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Confirm Receipt of Assets'),
        fields: [
            {
                fieldname: 'received_by',
                fieldtype: 'Link',
                label: __('Received By'),
                options: 'User',
                reqd: 1,
                default: frappe.session.user
            },
            {
                fieldname: 'receipt_condition',
                fieldtype: 'Select',
                label: __('Asset Condition on Receipt'),
                options: 'Excellent\nGood\nFair\nDamaged',
                default: 'Good',
                reqd: 1
            },
            {
                fieldname: 'all_assets_received',
                fieldtype: 'Check',
                label: __('All assets received in good order'),
                default: 1
            },
            {
                fieldname: 'receipt_remarks',
                fieldtype: 'Text',
                label: __('Receipt Remarks'),
                description: __('Note any issues, damages, or missing items')
            }
        ],
        primary_action_label: __('Confirm Receipt'),
        primary_action: function(values) {
            if (!values.all_assets_received && !values.receipt_remarks) {
                frappe.msgprint(__('Please provide remarks if not all assets received in good order'));
                return;
            }
            
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.fixed_asset_transfer.fixed_asset_transfer.mark_received',
                args: {
                    transfer_name: frm.doc.name,
                    received_by: values.received_by,
                    receipt_remarks: values.receipt_remarks
                },
                freeze: true,
                freeze_message: __('Confirming receipt...'),
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frm.reload_doc();
                        d.hide();
                        
                        // Show success message with confetti effect
                        show_success_animation();
                        
                        frappe.show_alert({
                            message: __('🎉 Transfer completed successfully! All stakeholders notified.'),
                            indicator: 'green'
                        }, 10);
                    }
                }
            });
        }
    });
    d.show();
}

function show_success_animation() {
    // Simple confetti-like effect
    let confetti_html = `
        <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
                    pointer-events: none; z-index: 9999;">
            <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
                        font-size: 100px; animation: fadeOut 2s;">
                ✅
            </div>
        </div>
        <style>
            @keyframes fadeOut {
                0% { opacity: 1; transform: translate(-50%, -50%) scale(0.5); }
                50% { opacity: 1; transform: translate(-50%, -50%) scale(1.2); }
                100% { opacity: 0; transform: translate(-50%, -50%) scale(1); }
            }
        </style>
    `;
    
    $('body').append(confetti_html);
    setTimeout(() => { $('body > div:last').remove(); }, 2000);
}

function add_multiple_assets_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Add Multiple Assets'),
        size: 'large',
        fields: [
            {
                fieldname: 'filters_section',
                fieldtype: 'Section Break',
                label: __('Filter Assets')
            },
            {
                fieldname: 'asset_category',
                fieldtype: 'Link',
                label: __('Asset Category'),
                options: 'Fixed Asset Category'
            },
            {
                fieldname: 'location',
                fieldtype: 'Link',
                label: __('Current Location'),
                options: 'Warehouse'
            },
            {
                fieldname: 'col_break',
                fieldtype: 'Column Break'
            },
            {
                fieldname: 'department',
                fieldtype: 'Link',
                label: __('Department'),
                options: 'Department'
            },
            {
                fieldname: 'custodian',
                fieldtype: 'Link',
                label: __('Custodian'),
                options: 'User'
            },
            {
                fieldname: 'button_section',
                fieldtype: 'Section Break'
            },
            {
                fieldname: 'get_assets',
                fieldtype: 'Button',
                label: __('🔍 Search Assets'),
                click: function() {
                    get_assets_for_transfer(d, frm);
                }
            },
            {
                fieldname: 'assets_section',
                fieldtype: 'Section Break',
                label: __('Available Assets')
            },
            {
                fieldname: 'assets_html',
                fieldtype: 'HTML'
            }
        ],
        primary_action_label: __('Add Selected Assets'),
        primary_action: function(values) {
            add_selected_assets_to_transfer(frm, d);
        }
    });
    d.show();
}

function get_assets_for_transfer(dialog, frm) {
    let values = dialog.get_values();
    
    let filters = {
        'docstatus': 1,
        'asset_status': ['not in', ['Disposed', 'Sold', 'Scrapped', 'Cancelled']],
        'company': frm.doc.company
    };
    
    if (values.asset_category) filters['asset_category'] = values.asset_category;
    if (values.location) filters['current_location'] = values.location;
    if (values.department) filters['department'] = values.department;
    if (values.custodian) filters['custodian'] = values.custodian;
    
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Fixed Asset',
            filters: filters,
            fields: ['name', 'asset_code', 'asset_name', 'current_location', 
                     'current_gross_value', 'asset_category', 'custodian'],
            limit_page_length: 100
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                display_assets_for_selection(dialog, r.message);
            } else {
                frappe.msgprint(__('No assets found matching the criteria'));
                dialog.fields_dict.assets_html.$wrapper.html(
                    '<div class="text-muted text-center" style="padding: 40px;">No assets found</div>'
                );
            }
        }
    });
}

function display_assets_for_selection(dialog, assets) {
    let html = `
        <div class="asset-selection-container">
            <div style="margin-bottom: 15px; padding: 10px; background-color: #e7f3ff; border-radius: 5px;">
                <label>
                    <input type="checkbox" id="select-all-assets" style="margin-right: 5px;">
                    <strong>Select All ({0} assets)</strong>
                </label>
            </div>
            <div class="asset-selection-list" style="max-height: 400px; overflow-y: auto; border: 1px solid #d1d8dd; border-radius: 5px;">
                <table class="table table-hover" style="margin: 0;">
                    <thead style="position: sticky; top: 0; background: #f8f9fa; z-index: 1;">
                        <tr>
                            <th style="width: 50px;">Select</th>
                            <th>Asset Code</th>
                            <th>Asset Name</th>
                            <th>Category</th>
                            <th>Location</th>
                            <th>Custodian</th>
                            <th style="text-align: right;">Value</th>
                        </tr>
                    </thead>
                    <tbody>
    `.replace('{0}', assets.length);
    
    assets.forEach(function(asset) {
        html += `
            <tr style="cursor: pointer;" onclick="$(this).find('input').click();">
                <td>
                    <input type="checkbox" class="asset-checkbox" 
                           data-asset="${asset.name}" 
                           data-code="${asset.asset_code}"
                           data-name="${asset.asset_name}"
                           onclick="event.stopPropagation();">
                </td>
                <td><strong>${asset.asset_code}</strong></td>
                <td>${asset.asset_name}</td>
                <td><span class="badge badge-info">${asset.asset_category}</span></td>
                <td>${asset.current_location || '-'}</td>
                <td>${asset.custodian || '-'}</td>
                <td style="text-align: right;">${format_currency(asset.current_gross_value)}</td>
            </tr>
        `;
    });
    
    html += `
                    </tbody>
                </table>
            </div>
            <div style="margin-top: 15px; padding: 10px; background-color: #f8f9fa; border-radius: 5px;">
                <span id="selected-count">0 assets selected</span>
            </div>
        </div>
    `;
    
    dialog.fields_dict.assets_html.$wrapper.html(html);
    
    // Select all functionality
    $('#select-all-assets').on('change', function() {
        $('.asset-checkbox').prop('checked', $(this).prop('checked'));
        update_selected_count();
    });
    
    // Update count on individual selection
    $('.asset-checkbox').on('change', function() {
        update_selected_count();
    });
    
    function update_selected_count() {
        let count = $('.asset-checkbox:checked').length;
        $('#selected-count').text(`${count} asset(s) selected`);
    }
}

function add_selected_assets_to_transfer(frm, dialog) {
    let selected = [];
    
    $('.asset-checkbox:checked').each(function() {
        selected.push($(this).data('asset'));
    });
    
    if (selected.length === 0) {
        frappe.msgprint(__('Please select at least one asset'));
        return;
    }
    
    let added_count = 0;
    
    selected.forEach(function(asset_name) {
        frappe.call({
            method: 'ecclesia.ecclesia.doctype.fixed_asset_transfer.fixed_asset_transfer.get_asset_transfer_details',
            args: { asset: asset_name },
            async: false,
            callback: function(r) {
                if (r.message) {
                    let row = frm.add_child('transfer_items');
                    row.asset = asset_name;
                    row.asset_code = r.message.asset_code;
                    row.asset_name = r.message.asset_name;
                    row.current_location = r.message.current_location;
                    row.current_custodian = r.message.current_custodian;
                    row.current_book_value = r.message.current_book_value;
                    row.condition_at_transfer = 'Good';
                    added_count++;
                }
            }
        });
    });
    
    frm.refresh_field('transfer_items');
    calculate_totals(frm);
    
    dialog.hide();
    
    frappe.show_alert({
        message: __('✓ Added {0} asset(s) to transfer', [added_count]),
        indicator: 'green'
    }, 5);
}

function scan_asset_qr_code(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Scan Asset QR Code'),
        fields: [
            {
                fieldname: 'scan_method',
                fieldtype: 'Select',
                label: __('Scan Method'),
                options: 'Camera\nManual Entry',
                default: 'Manual Entry',
                reqd: 1,
                onchange: function() {
                    let method = d.get_value('scan_method');
                    d.fields_dict.camera_section.$wrapper.toggle(method === 'Camera');
                    d.fields_dict.manual_section.$wrapper.toggle(method === 'Manual Entry');
                }
            },
            {
                fieldname: 'camera_section',
                fieldtype: 'Section Break',
                label: __('Camera Scan'),
                hidden: 1
            },
            {
                fieldname: 'camera_feed',
                fieldtype: 'HTML'
            },
            {
                fieldname: 'manual_section',
                fieldtype: 'Section Break',
                label: __('Manual Entry')
            },
            {
                fieldname: 'qr_code',
                fieldtype: 'Data',
                label: __('QR Code / Asset Code'),
                description: __('Enter or scan QR code'),
                reqd: 1
            },
            {
                fieldname: 'scan_button',
                fieldtype: 'Button',
                label: __('🔍 Find Asset'),
                click: function() {
                    let qr_code = d.get_value('qr_code');
                    if (qr_code) {
                        scan_and_add_asset(frm, qr_code, d);
                    }
                }
            },
            {
                fieldname: 'result_section',
                fieldtype: 'Section Break',
                label: __('Scan Results')
            },
            {
                fieldname: 'result_html',
                fieldtype: 'HTML'
            }
        ],
        primary_action_label: __('Close'),
        primary_action: function() {
            stop_camera();
            d.hide();
        }
    });
    
    d.show();
    
    // Initialize camera section
    d.fields_dict.camera_feed.$wrapper.html(`
        <div style="text-align: center; padding: 20px;">
            <video id="qr-video" style="max-width: 100%; border: 2px solid #ddd; border-radius: 5px;"></video>
            <div style="margin-top: 10px;">
                <button class="btn btn-primary btn-sm" onclick="start_camera_scan()">
                    📷 Start Camera
                </button>
                <button class="btn btn-secondary btn-sm" onclick="stop_camera()">
                    ⏹️ Stop
                </button>
            </div>
            <div id="scan-status" style="margin-top: 10px; color: #666;"></div>
        </div>
    `);
    
    // Store dialog reference globally for camera functions
    window.current_qr_dialog = d;
    window.current_qr_frm = frm;
}

function scan_and_add_asset(frm, qr_code, dialog) {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.fixed_asset_transfer.fixed_asset_transfer.scan_asset_qr',
        args: { qr_code: qr_code },
        freeze: true,
        freeze_message: __('Scanning...'),
        callback: function(r) {
            if (r.message && r.message.success) {
                // Check if asset already added
                let already_added = false;
                if (frm.doc.transfer_items) {
                    already_added = frm.doc.transfer_items.some(item => item.asset === r.message.asset);
                }
                
                if (already_added) {
                    show_scan_result(dialog, false, __('Asset already added to this transfer'));
                    return;
                }
                
                // Add asset to transfer
                let row = frm.add_child('transfer_items');
                row.asset = r.message.asset;
                row.asset_code = r.message.details.asset_code;
                row.asset_name = r.message.details.asset_name;
                row.current_location = r.message.details.current_location;
                row.current_custodian = r.message.details.current_custodian;
                row.current_book_value = r.message.details.current_book_value;
                row.condition_at_transfer = 'Good';
                
                frm.refresh_field('transfer_items');
                calculate_totals(frm);
                
                show_scan_result(dialog, true, r.message.message, r.message.details);
                
                // Clear input for next scan
                dialog.set_value('qr_code', '');
                
                // Auto-focus input for continuous scanning
                setTimeout(() => {
                    dialog.fields_dict.qr_code.$input.focus();
                }, 500);
                
            } else {
                show_scan_result(dialog, false, r.message.message);
            }
        }
    });
}

function show_scan_result(dialog, success, message, details) {
    let icon = success ? '✅' : '❌';
    let color = success ? '#00a82d' : '#d63939';
    
    let html = `
        <div style="padding: 15px; border-left: 4px solid ${color}; background-color: ${success ? '#e7f9ed' : '#fee'}; border-radius: 5px; margin: 10px 0;">
            <div style="font-size: 16px; margin-bottom: 10px;">
                <strong>${icon} ${message}</strong>
            </div>
    `;
    
    if (success && details) {
        html += `
            <div style="font-size: 13px; color: #666;">
                <div><strong>Code:</strong> ${details.asset_code}</div>
                <div><strong>Name:</strong> ${details.asset_name}</div>
                <div><strong>Location:</strong> ${details.current_location || 'N/A'}</div>
                <div><strong>Value:</strong> ${frappe.format(details.current_book_value, {fieldtype: 'Currency'})}</div>
            </div>
        `;
    }
    
    html += '</div>';
    
    dialog.fields_dict.result_html.$wrapper.html(html);
    
    // Show notification
    frappe.show_alert({
        message: message,
        indicator: success ? 'green' : 'red'
    }, 5);
}

// Camera scanning functions (basic implementation)
window.start_camera_scan = function() {
    $('#scan-status').html('<span style="color: #2e86de;">📷 Camera feature requires QR scanner library. Please use Manual Entry for now.</span>');
    
    frappe.msgprint({
        title: __('Camera Scanning'),
        message: __('QR code camera scanning requires additional libraries. For now, please:<br><br>1. Use a QR scanner app on your phone<br>2. Enter the scanned code in the Manual Entry field<br>3. Click "Find Asset"'),
        indicator: 'blue'
    });
}

window.stop_camera = function() {
    $('#scan-status').html('');
}


function show_asset_transfer_history(frm) {
    if (!frm.doc.transfer_items || frm.doc.transfer_items.length === 0) {
        frappe.msgprint(__('No assets in this transfer'));
        return;
    }
    
    let asset = frm.doc.transfer_items[0].asset;
    
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.fixed_asset_transfer.fixed_asset_transfer.get_asset_transfer_history',
        args: { asset: asset },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                display_transfer_history_dialog(r.message, frm);
            } else {
                frappe.msgprint(__('No transfer history available'));
            }
        }
    });
}

function display_transfer_history_dialog(history, frm) {
    let html = `
        <div style="max-height: 500px; overflow-y: auto;">
            <table class="table table-bordered">
                <thead>
                    <tr style="background-color: #f8f9fa;">
                        <th>Transfer #</th>
                        <th>Date</th>
                        <th>Type</th>
                        <th>From</th>
                        <th>To</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    history.forEach(function(transfer) {
        let status_color = transfer.status === 'Received' ? 'success' : 
                          transfer.status === 'Delivered' ? 'info' : 
                          transfer.status === 'In Transit' ? 'warning' : 'primary';
        
        html += `
            <tr>
                <td><a href="/app/fixed-asset-transfer/${transfer.name}" target="_blank">${transfer.name}</a></td>
                <td>${frappe.datetime.str_to_user(transfer.transfer_date)}</td>
                <td><span class="badge badge-secondary">${transfer.transfer_type}</span></td>
                <td>${transfer.from_location || '-'}<br><small class="text-muted">${transfer.from_department || ''}</small></td>
                <td>${transfer.to_location || '-'}<br><small class="text-muted">${transfer.to_department || ''}</small></td>
                <td><span class="badge badge-${status_color}">${transfer.status}</span></td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    frappe.msgprint({
        title: __('Transfer History - {0}', [frm.doc.transfer_items[0].asset_name]),
        message: html,
        wide: true
    });
}

function print_transfer_note(frm) {
    frappe.utils.print(
        'Fixed Asset Transfer',
        frm.doc.name,
        'Transfer Note'
    );
}

function print_delivery_receipt(frm) {
    frappe.utils.print(
        'Fixed Asset Transfer',
        frm.doc.name,
        'Delivery Receipt'
    );
}

function export_transfer_to_excel(frm) {
    // Method 1: Export as CSV (Simple)
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.fixed_asset_transfer.fixed_asset_transfer.export_transfer_data',
        args: {
            transfer_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                // Download CSV
                download_csv(r.message, `Transfer_${frm.doc.name}.csv`);
            }
        }
    });
}

function download_csv(data, filename) {
    let csv = 'Asset Code,Asset Name,Location,Custodian,Book Value,Condition\n';
    
    data.forEach(function(row) {
        csv += `"${row.asset_code}","${row.asset_name}","${row.current_location || ''}","${row.current_custodian || ''}","${row.current_book_value}","${row.condition_at_transfer || 'Good'}"\n`;
    });
    
    let blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    let link = document.createElement('a');
    let url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function setup_filters(frm) {
    // Filter for assets in child table
    frm.set_query('asset', 'transfer_items', function() {
        return {
            filters: {
                'docstatus': 1,
                'asset_status': ['not in', ['Disposed', 'Sold', 'Scrapped', 'Cancelled']],
                'company': frm.doc.company
            }
        };
    });
    
    // Filters for locations
    frm.set_query('from_location', function() {
        return {
            filters: {
                'company': frm.doc.company,
                'is_group': 0
            }
        };
    });
    
    frm.set_query('to_location', function() {
        return {
            filters: {
                'company': frm.doc.company,
                'is_group': 0
            }
        };
    });
    
    // Filters for cost centers
    frm.set_query('from_cost_center', function() {
        return {
            filters: {
                'company': frm.doc.company,
                'is_group': 0
            }
        };
    });
    
    frm.set_query('to_cost_center', function() {
        return {
            filters: {
                'company': frm.doc.company,
                'is_group': 0
            }
        };
    });
}

// Helper function
function format_currency(value) {
    return frappe.format(value, { fieldtype: 'Currency' });
}