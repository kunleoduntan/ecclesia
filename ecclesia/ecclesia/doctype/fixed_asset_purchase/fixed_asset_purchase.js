// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

frappe.ui.form.on('Fixed Asset Purchase', {
    refresh: function(frm) {
        // Add custom buttons
        add_custom_buttons(frm);
        
        // Set visual indicators
        set_status_indicators(frm);
        
        // Set field queries
        set_field_queries(frm);
        
        // Show summary statistics
        show_summary_stats(frm);
        
        // Handle purchase type changes
        frm.trigger('setup_purchase_type_ui');
    },
    
    setup: function(frm) {
        // Setup default values
        if (frm.is_new()) {
            frm.set_value('purchase_type', 'Supplier Purchase');
            frm.set_value('payment_type', 'On Credit');
            frm.set_value('create_gl_entry', 1);
        }
    },
    
    onload: function(frm) {
        // Show welcome message for new documents
        if (frm.is_new() && !frm.doc.__islocal) {
            show_welcome_message(frm);
        }
    },
    
    purchase_type: function(frm) {
        frm.trigger('setup_purchase_type_ui');
        frm.trigger('toggle_purchase_fields');
        
        // Clear related fields when switching types
        if (frm.doc.purchase_type === 'Cash Purchase') {
            frm.set_value('supplier', '');
            frm.set_value('supplier_account', '');
            frm.set_value('payment_status', 'Paid');
        } else {
            frm.set_value('bank_account', '');
            frm.set_value('payment_status', 'Unpaid');
        }
    },
    
    setup_purchase_type_ui: function(frm) {
        // Add visual indicator for purchase type
        if (frm.doc.purchase_type) {
            let color = frm.doc.purchase_type === 'Cash Purchase' ? 'green' : 'blue';
            let icon = frm.doc.purchase_type === 'Cash Purchase' ? '💵' : '🏢';
            
            frm.set_df_property('purchase_type', 'description',
                `<span style="color: ${color}; font-weight: bold; font-size: 14px;">
                    ${icon} ${frm.doc.purchase_type}
                </span>`
            );
        }
    },
    
    toggle_purchase_fields: function(frm) {
        let is_cash = frm.doc.purchase_type === 'Cash Purchase';
        
        // Toggle supplier section
        frm.toggle_display('supplier_section', !is_cash);
        frm.toggle_reqd('supplier', !is_cash);
        
        // Toggle cash section
        frm.toggle_display('cash_purchase_section', is_cash);
        frm.toggle_reqd('bank_account', is_cash);
        
        // Toggle payment tab
        frm.toggle_display('payment_tab', !is_cash && frm.doc.payment_type === 'On Credit');
    },
    
    payment_type: function(frm) {
        frm.trigger('toggle_purchase_fields');
        
        // Show info message
        if (frm.doc.payment_type === 'Immediate Payment') {
            frappe.show_alert({
                message: __('Purchase Invoice will be created and marked as paid'),
                indicator: 'blue'
            }, 5);
        }
    },
    
    company: function(frm) {
        if (frm.doc.company) {
            // Set default cost center
            frappe.db.get_value('Company', frm.doc.company, 'cost_center', (r) => {
                if (r && r.cost_center && !frm.doc.cost_center) {
                    frm.set_value('cost_center', r.cost_center);
                }
            });
        }
    },
    
    supplier: function(frm) {
        if (frm.doc.supplier && frm.doc.company) {
            // Fetch supplier details
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.fixed_asset_purchase.fixed_asset_purchase.get_supplier_account',
                args: {
                    supplier: frm.doc.supplier,
                    company: frm.doc.company
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('supplier_account', r.message);
                    }
                }
            });
            
            // Show supplier info
            show_supplier_info(frm);
        }
    },
    
    bank_account: function(frm) {
        if (frm.doc.bank_account) {
            // Show bank account balance
            frappe.call({
                method: 'erpnext.accounts.utils.get_balance_on',
                args: {
                    account: frm.doc.bank_account,
                    date: frm.doc.posting_date
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.show_alert({
                            message: __('Bank Balance: {0}', [format_currency(r.message)]),
                            indicator: 'blue'
                        }, 3);
                    }
                }
            });
        }
    },
    
    payment_terms_template: function(frm) {
        if (frm.doc.payment_terms_template && frm.doc.grand_total) {
            generate_payment_schedule(frm);
        }
    },
    
    grand_total: function(frm) {
        if (frm.doc.payment_terms_template) {
            generate_payment_schedule(frm);
        }
        
        // Show warning if grand total is high
        if (flt(frm.doc.grand_total) > 100000) {
            frappe.show_alert({
                message: __('⚠️ Large purchase amount. Please verify before submitting.'),
                indicator: 'orange'
            }, 5);
        }
    },
    
    before_save: function(frm) {
        // Validate before saving
        if (frm.doc.asset_purchase_details && frm.doc.asset_purchase_details.length > 0) {
            calculate_totals(frm);
        }
    }
});

// Child Table: Asset Purchase Details
frappe.ui.form.on('Asset Purchase Details', {
    asset_purchase_details_add: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, 'qty', 1);
    },
    
    qty: function(frm, cdt, cdn) {
        calculate_item_amount(frm, cdt, cdn);
    },
    
    rate: function(frm, cdt, cdn) {
        calculate_item_amount(frm, cdt, cdn);
    },
    
    asset_category: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.asset_category) {
            // Fetch category defaults
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.fixed_asset_purchase.fixed_asset_purchase.get_category_defaults',
                args: {
                    category: row.asset_category
                },
                callback: function(r) {
                    if (r.message) {
                        // Set defaults from category
                        frappe.model.set_value(cdt, cdn, 'depreciation_method', r.message.depreciation_method);
                        frappe.model.set_value(cdt, cdn, 'useful_life_months', r.message.total_number_of_depreciations);
                        
                        // Show category info as alert
                        frappe.show_alert({
                            message: __('Category loaded: {0}', [row.asset_category]),
                            indicator: 'green'
                        }, 2);
                    }
                }
            });
        }
    },
    
    asset_purchase_details_remove: function(frm) {
        calculate_totals(frm);
    }
});

// Child Table: Additional Costs
frappe.ui.form.on('Additional Cost Details', {
    amount: function(frm) {
        calculate_totals(frm);
    },
    
    additional_costs_remove: function(frm) {
        calculate_totals(frm);
    }
});

// Child Table: Taxes
frappe.ui.form.on('Purchase Taxes and Charges', {
    rate: function(frm, cdt, cdn) {
        calculate_tax_amount(frm, cdt, cdn);
    },
    
    tax_amount: function(frm) {
        calculate_totals(frm);
    },
    
    taxes_and_charges_table_remove: function(frm) {
        calculate_totals(frm);
    }
});

// ============================================================================
// CALCULATION FUNCTIONS
// ============================================================================

function calculate_item_amount(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let amount = flt(row.qty) * flt(row.rate);
    frappe.model.set_value(cdt, cdn, 'amount', amount);
    
    // Show per-unit cost
    if (flt(row.qty) > 1) {
        frappe.show_alert({
            message: __('Unit Cost: {0} × {1} = {2}', [
                row.qty, 
                format_currency(row.rate),
                format_currency(amount)
            ]),
            indicator: 'blue'
        }, 2);
    }
    
    // Recalculate totals
    calculate_totals(frm);
}

function calculate_tax_amount(frm, cdt, cdn) {
    let tax = locals[cdt][cdn];
    
    if (tax.charge_type === 'On Net Total') {
        let tax_amount = flt(frm.doc.total) * flt(tax.rate) / 100;
        frappe.model.set_value(cdt, cdn, 'tax_amount', tax_amount);
    }
    
    calculate_totals(frm);
}

function calculate_totals(frm) {
    let total = 0;
    let total_qty = 0;
    let total_additional_costs = 0;
    let total_taxes = 0;
    
    // Calculate items total
    $.each(frm.doc.asset_purchase_details || [], function(i, item) {
        total += flt(item.amount);
        total_qty += flt(item.qty);
    });
    
    // Calculate additional costs
    $.each(frm.doc.additional_costs || [], function(i, cost) {
        total_additional_costs += flt(cost.amount);
    });
    
    // Calculate taxes
    $.each(frm.doc.taxes_and_charges_table || [], function(i, tax) {
        if (tax.charge_type === 'On Net Total') {
            tax.tax_amount = flt(total) * flt(tax.rate) / 100;
        }
        total_taxes += flt(tax.tax_amount);
    });
    
    // Set totals
    frm.set_value('total_qty', total_qty);
    frm.set_value('total', total);
    frm.set_value('total_additional_costs', total_additional_costs);
    frm.set_value('total_taxes_and_charges', total_taxes);
    frm.set_value('grand_total', total + total_additional_costs + total_taxes);
    
    // Refresh fields
    frm.refresh_field('taxes_and_charges_table');
}

// ============================================================================
// CUSTOM BUTTONS
// ============================================================================

function add_custom_buttons(frm) {
    // Draft state buttons
    if (frm.doc.docstatus === 0) {
        add_draft_buttons(frm);
    }
    
    // Submitted state buttons
    if (frm.doc.docstatus === 1) {
        add_submitted_buttons(frm);
    }
}

function add_draft_buttons(frm) {
    // Import from Excel
    frm.add_custom_button(__('📥 Import from Excel'), function() {
        show_import_dialog(frm);
    }, __('Tools'));
    
    // Add Quick Asset
    frm.add_custom_button(__('➕ Quick Add Asset'), function() {
        show_quick_add_dialog(frm);
    }, __('Tools'));
    
    // Get from Template
    frm.add_custom_button(__('📋 Load Template'), function() {
        show_template_dialog(frm);
    }, __('Tools'));
}

function add_submitted_buttons(frm) {
    // View Assets
    if (frm.doc.assets_created) {
        frm.add_custom_button(__('🔍 View Assets'), function() {
            view_created_assets(frm);
        }, __('View'));
    }
    
    // View Journal Entry
    if (frm.doc.journal_entry) {
        frm.add_custom_button(__('📒 View Journal Entry'), function() {
            frappe.set_route('Form', 'Journal Entry', frm.doc.journal_entry);
        }, __('View'));
    }
    
    // View Purchase Invoice
    if (frm.doc.purchase_invoice) {
        frm.add_custom_button(__('📄 View Purchase Invoice'), function() {
            frappe.set_route('Form', 'Purchase Invoice', frm.doc.purchase_invoice);
        }, __('View'));
    }
    
    // Print QR Labels
    if (frm.doc.assets_created) {
        frm.add_custom_button(__('🏷️ Print Asset Labels'), function() {
            print_asset_labels(frm);
        }, __('Tools'));
    }
    
    // Export Report
    frm.add_custom_button(__('📊 Export Report'), function() {
        export_purchase_report(frm);
    }, __('Tools'));
}

// ============================================================================
// VISUAL INDICATORS & STATS
// ============================================================================

function set_status_indicators(frm) {
    if (!frm.doc.docstatus) return;
    
    // Payment status indicator
    const payment_colors = {
        'Unpaid': 'red',
        'Partially Paid': 'orange',
        'Paid': 'green'
    };
    
    if (frm.doc.payment_status) {
        frm.dashboard.add_indicator(
            __('Payment: {0}', [frm.doc.payment_status]),
            payment_colors[frm.doc.payment_status] || 'gray'
        );
    }
    
    // Purchase type indicator
    if (frm.doc.purchase_type) {
        let color = frm.doc.purchase_type === 'Cash Purchase' ? 'green' : 'blue';
        frm.dashboard.add_indicator(
            frm.doc.purchase_type,
            color
        );
    }
    
    // Assets created indicator
    if (frm.doc.assets_created) {
        frm.dashboard.add_indicator(__('Assets Created'), 'green');
    }
    
    // Accounting entry indicator
    if (frm.doc.journal_entry || frm.doc.purchase_invoice) {
        frm.dashboard.add_indicator(__('Accounting Posted'), 'green');
    }
}

function show_summary_stats(frm) {
    if (!frm.doc.docstatus || !frm.doc.asset_purchase_details) return;
    
    let stats_html = `
        <div class="row" style="margin-top: 15px; margin-bottom: 15px;">
            <div class="col-md-12">
                <div class="alert alert-info" style="margin-bottom: 0;">
                    <h4 style="margin-top: 0;">📊 Purchase Summary</h4>
                    <table class="table table-borderless" style="margin-bottom: 0;">
                        <tr>
                            <td width="50%"><strong>Total Assets:</strong></td>
                            <td><span class="badge badge-primary" style="font-size: 14px;">${frm.doc.total_qty || 0}</span></td>
                        </tr>
                        <tr>
                            <td><strong>Total Value:</strong></td>
                            <td><strong>${format_currency(frm.doc.grand_total)}</strong></td>
                        </tr>
                        ${frm.doc.supplier ? `
                        <tr>
                            <td><strong>Supplier:</strong></td>
                            <td>${frm.doc.supplier_name || frm.doc.supplier}</td>
                        </tr>` : ''}
                        ${frm.doc.bank_account ? `
                        <tr>
                            <td><strong>Paid From:</strong></td>
                            <td>${frm.doc.bank_account}</td>
                        </tr>` : ''}
                        ${frm.doc.outstanding_amount > 0 ? `
                        <tr>
                            <td><strong>Outstanding:</strong></td>
                            <td><span style="color: red;">${format_currency(frm.doc.outstanding_amount)}</span></td>
                        </tr>` : ''}
                    </table>
                </div>
            </div>
        </div>
    `;
    
    frm.dashboard.add_comment(stats_html, null, true);
    
    // Category breakdown
    if (frm.doc.asset_purchase_details.length > 0) {
        show_category_breakdown(frm);
    }
}

function show_category_breakdown(frm) {
    let category_stats = {};
    
    frm.doc.asset_purchase_details.forEach(item => {
        if (!category_stats[item.asset_category]) {
            category_stats[item.asset_category] = {
                qty: 0,
                amount: 0
            };
        }
        category_stats[item.asset_category].qty += flt(item.qty);
        category_stats[item.asset_category].amount += flt(item.amount);
    });
    
    let breakdown_html = `
        <div class="row" style="margin-top: 10px;">
            <div class="col-md-12">
                <h5>📁 Category Breakdown</h5>
                <table class="table table-bordered table-sm">
                    <thead style="background-color: #f5f5f5;">
                        <tr>
                            <th>Category</th>
                            <th style="text-align: right;">Quantity</th>
                            <th style="text-align: right;">Amount</th>
                        </tr>
                    </thead>
                    <tbody>
    `;
    
    Object.keys(category_stats).forEach(category => {
        let stat = category_stats[category];
        breakdown_html += `
            <tr>
                <td><strong>${category}</strong></td>
                <td style="text-align: right;">${stat.qty}</td>
                <td style="text-align: right;">${format_currency(stat.amount)}</td>
            </tr>
        `;
    });
    
    breakdown_html += `
                    </tbody>
                </table>
            </div>
        </div>
    `;
    
    frm.dashboard.add_comment(breakdown_html, null, true);
}

function show_supplier_info(frm) {
    if (!frm.doc.supplier) return;
    
    frappe.call({
        method: 'frappe.client.get',
        args: {
            doctype: 'Supplier',
            name: frm.doc.supplier
        },
        callback: function(r) {
            if (r.message) {
                let supplier = r.message;
                let info_html = `
                    <div class="alert alert-primary" style="margin-top: 10px;">
                        <strong>📞 Supplier Contact:</strong><br>
                        ${supplier.email_id ? `Email: ${supplier.email_id}<br>` : ''}
                        ${supplier.mobile_no ? `Phone: ${supplier.mobile_no}<br>` : ''}
                        ${supplier.supplier_group ? `Group: ${supplier.supplier_group}` : ''}
                    </div>
                `;
                
                frm.dashboard.add_comment(info_html, null, true);
            }
        }
    });
}

// ============================================================================
// DIALOG FUNCTIONS
// ============================================================================

function show_quick_add_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __('➕ Quick Add Asset'),
        fields: [
            {
                fieldname: 'asset_category',
                fieldtype: 'Link',
                label: __('Asset Category'),
                options: 'Fixed Asset Category',
                reqd: 1
            },
            {
                fieldname: 'col_break_1',
                fieldtype: 'Column Break'
            },
            {
                fieldname: 'qty',
                fieldtype: 'Int',
                label: __('Quantity'),
                reqd: 1,
                default: 1
            },
            {
                fieldname: 'sec_break_1',
                fieldtype: 'Section Break'
            },
            {
                fieldname: 'asset_name',
                fieldtype: 'Data',
                label: __('Asset Name'),
                reqd: 1
            },
            {
                fieldname: 'description',
                fieldtype: 'Small Text',
                label: __('Description')
            },
            {
                fieldname: 'sec_break_2',
                fieldtype: 'Section Break'
            },
            {
                fieldname: 'rate',
                fieldtype: 'Currency',
                label: __('Rate'),
                reqd: 1
            },
            {
                fieldname: 'col_break_2',
                fieldtype: 'Column Break'
            },
            {
                fieldname: 'location',
                fieldtype: 'Link',
                label: __('Location'),
                options: 'Warehouse'
            }
        ],
        primary_action_label: __('Add Asset'),
        primary_action: function(values) {
            let row = frm.add_child('asset_purchase_details');
            row.asset_category = values.asset_category;
            row.asset_name = values.asset_name;
            row.description = values.description;
            row.qty = values.qty;
            row.rate = values.rate;
            row.amount = values.qty * values.rate;
            row.location = values.location;
            
            frm.refresh_field('asset_purchase_details');
            calculate_totals(frm);
            
            d.hide();
            frappe.show_alert({
                message: __('Asset added successfully'),
                indicator: 'green'
            });
        }
    });
    
    d.show();
}

function show_import_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __('📥 Import Items from Excel'),
        size: 'large',
        fields: [
            {
                fieldname: 'import_info',
                fieldtype: 'HTML',
                options: `
                    <div class="alert alert-info">
                        <h5><i class="fa fa-info-circle"></i> Import Instructions</h5>
                        <ol>
                            <li>Download the Excel template below</li>
                            <li>Fill in your asset details</li>
                            <li>Upload the completed file</li>
                            <li>Click Import to add items</li>
                        </ol>
                    </div>
                `
            },
            {
                fieldname: 'template_section',
                fieldtype: 'Section Break',
                label: __('Step 1: Download Template')
            },
            {
                fieldname: 'download_template',
                fieldtype: 'HTML',
                options: `
                    <div class="text-center" style="padding: 20px;">
                        <button class="btn btn-primary btn-lg" onclick="download_purchase_template()">
                            <i class="fa fa-download"></i> Download Excel Template
                        </button>
                    </div>
                `
            },
            {
                fieldname: 'upload_section',
                fieldtype: 'Section Break',
                label: __('Step 2: Upload Completed File')
            },
            {
                fieldname: 'import_file',
                fieldtype: 'Attach',
                label: __('Excel File'),
                reqd: 1
            }
        ],
        primary_action_label: __('Import'),
        primary_action: function(values) {
            import_items_from_excel(frm, values.import_file);
            d.hide();
        }
    });
    
    d.show();
}

function show_template_dialog(frm) {
    frappe.msgprint({
        title: __('Coming Soon'),
        message: __('Template loading feature will be available in the next update'),
        indicator: 'blue'
    });
}

function generate_payment_schedule(frm) {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.fixed_asset_purchase.fixed_asset_purchase.get_payment_schedule',
        args: {
            doc: frm.doc
        },
        callback: function(r) {
            if (r.message) {
                frm.clear_table('payment_schedule');
                
                $.each(r.message, function(i, payment) {
                    let row = frm.add_child('payment_schedule');
                    $.extend(row, payment);
                });
                
                frm.refresh_field('payment_schedule');
                
                frappe.show_alert({
                    message: __('Payment schedule generated'),
                    indicator: 'green'
                }, 3);
            }
        }
    });
}

// ============================================================================
// ACTION FUNCTIONS
// ============================================================================

function view_created_assets(frm) {
    frappe.route_options = {
        "purchase_document": frm.doc.name
    };
    frappe.set_route("List", "Fixed Asset");
}

function print_asset_labels(frm) {
    if (!frm.doc.assets_created) {
        frappe.msgprint(__('Please create assets first'));
        return;
    }
    
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Fixed Asset',
            filters: {
                purchase_document: frm.doc.name
            },
            fields: ['name', 'asset_code', 'asset_name', 'qr_code_image', 'asset_category']
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                // Generate label print view with QR codes
                let assets = r.message;
                let label_html = generate_label_html(assets);
                
                // Open print window
                let print_window = window.open('', '_blank');
                print_window.document.write(label_html);
                print_window.document.close();
                
                frappe.show_alert({
                    message: __('Opening {0} asset labels for printing', [assets.length]),
                    indicator: 'green'
                });
            } else {
                frappe.msgprint(__('No assets found to print'));
            }
        }
    });
}

function generate_label_html(assets) {
    let html = `
        <!DOCTYPE html>
        <html>
        <head>
            <title>Asset Labels - ${assets.length} Items</title>
            <style>
                @page {
                    size: A4;
                    margin: 10mm;
                }
                @media print {
                    .page-break { page-break-after: always; }
                    .no-print { display: none; }
                }
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                }
                .print-header {
                    text-align: center;
                    margin-bottom: 20px;
                    border-bottom: 2px solid #333;
                    padding-bottom: 10px;
                }
                .label-container {
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: space-around;
                }
                .label {
                    width: 8cm;
                    height: 5cm;
                    border: 2px solid #333;
                    padding: 10px;
                    margin: 5px;
                    display: inline-block;
                    page-break-inside: avoid;
                    position: relative;
                    box-sizing: border-box;
                }
                .label h3 {
                    margin: 0 0 5px 0;
                    font-size: 14px;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }
                .label .code {
                    font-family: 'Courier New', monospace;
                    font-weight: bold;
                    font-size: 16px;
                    margin: 5px 0;
                }
                .label .category {
                    font-size: 11px;
                    color: #666;
                    margin: 3px 0;
                }
                .label .qr {
                    position: absolute;
                    right: 10px;
                    top: 10px;
                    width: 70px;
                    height: 70px;
                    border: 1px solid #ddd;
                }
                .label .info {
                    font-size: 10px;
                    color: #333;
                    margin-top: 5px;
                }
                .print-controls {
                    text-align: center;
                    margin: 20px 0;
                    padding: 15px;
                    background: #f0f0f0;
                    border-radius: 5px;
                }
                .print-controls button {
                    padding: 10px 30px;
                    font-size: 16px;
                    margin: 0 10px;
                    cursor: pointer;
                }
            </style>
        </head>
        <body>
            <div class="print-header no-print">
                <h2>Fixed Asset Labels</h2>
                <p>Total Assets: ${assets.length}</p>
            </div>
            
            <div class="print-controls no-print">
                <button onclick="window.print()" class="btn-primary">🖨️ Print Labels</button>
                <button onclick="window.close()" class="btn-secondary">✖️ Close</button>
            </div>
            
            <div class="label-container">
    `;
    
    assets.forEach((asset, index) => {
        html += `
            <div class="label">
                ${asset.qr_code_image ? `<img src="${asset.qr_code_image}" class="qr" alt="QR Code" />` : ''}
                <h3>${asset.asset_name || 'Unnamed Asset'}</h3>
                <div class="code">${asset.asset_code}</div>
                <div class="category">${asset.asset_category || ''}</div>
                <div class="info">${asset.name}</div>
            </div>
        `;
        
        // Add page break every 8 labels (2 rows of 4)
        if ((index + 1) % 8 === 0 && index < assets.length - 1) {
            html += '<div class="page-break"></div>';
        }
    });
    
    html += `
            </div>
            
            <script>
                // Auto-print on load (optional)
                // window.onload = function() { window.print(); }
            </script>
        </body>
        </html>
    `;
    
    return html;
}

function export_purchase_report(frm) {
    if (!frm.doc.asset_purchase_details || frm.doc.asset_purchase_details.length === 0) {
        frappe.msgprint(__('No items to export'));
        return;
    }
    
    // Create CSV data
    let csv_data = [];
    csv_data.push([
        'Asset Category',
        'Asset Name',
        'Description',
        'Quantity',
        'Rate',
        'Amount',
        'Location',
        'Serial Number',
        'Manufacturer',
        'Model Number'
    ]);
    
    frm.doc.asset_purchase_details.forEach(item => {
        csv_data.push([
            item.asset_category || '',
            item.asset_name || '',
            item.description || '',
            item.qty || 0,
            item.rate || 0,
            item.amount || 0,
            item.location || '',
            item.serial_number || '',
            item.manufacturer || '',
            item.model_number || ''
        ]);
    });
    
    // Add summary
    csv_data.push([]);
    csv_data.push(['Summary']);
    csv_data.push(['Total Quantity', frm.doc.total_qty]);
    csv_data.push(['Total Amount', frm.doc.total]);
    csv_data.push(['Additional Costs', frm.doc.total_additional_costs]);
    csv_data.push(['Taxes', frm.doc.total_taxes_and_charges]);
    csv_data.push(['Grand Total', frm.doc.grand_total]);
    
    // Convert to CSV string
    let csv_string = csv_data.map(row => row.join(',')).join('\n');
    
    // Download
    let blob = new Blob([csv_string], { type: 'text/csv' });
    let url = window.URL.createObjectURL(blob);
    let a = document.createElement('a');
    a.href = url;
    a.download = `Fixed_Asset_Purchase_${frm.doc.name}.csv`;
    a.click();
    
    frappe.show_alert({
        message: __('Report exported successfully'),
        indicator: 'green'
    });
}

function download_purchase_template() {
    // Create template CSV
    let template_data = [
        ['Asset Category*', 'Asset Name*', 'Description', 'Quantity*', 'Rate*', 'Location', 'Serial Number', 'Manufacturer', 'Model Number'],
        ['Computers', 'Dell Laptop', 'Dell Inspiron 15 with 8GB RAM', '5', '50000', 'Main Store', 'SN12345', 'Dell', 'Inspiron 15'],
        ['Furniture & Fittings', 'Office Desk', 'Executive desk with drawers', '10', '15000', 'Office', '', 'XYZ Furniture', 'ED-2024']
    ];
    
    let csv_string = template_data.map(row => row.join(',')).join('\n');
    let blob = new Blob([csv_string], { type: 'text/csv' });
    let url = window.URL.createObjectURL(blob);
    let a = document.createElement('a');
    a.href = url;
    a.download = 'Fixed_Asset_Purchase_Template.csv';
    a.click();
    
    frappe.show_alert({
        message: __('Template downloaded'),
        indicator: 'green'
    });
}

function import_items_from_excel(frm, file_url) {
    frappe.show_alert({
        message: __('Processing import...'),
        indicator: 'blue'
    });
    
    frappe.call({
        method: 'frappe.client.get_value',
        args: {
            doctype: 'File',
            filters: { file_url: file_url },
            fieldname: 'file_url'
        },
        callback: function(r) {
            // Here you would parse the CSV/Excel file
            frappe.msgprint({
                title: __('Import Status'),
                message: __('Excel import functionality will parse the file and add items to the table. Feature coming soon.'),
                indicator: 'blue'
            });
        }
    });
}

function show_welcome_message(frm) {
    let welcome_html = `
        <div class="alert alert-success" style="margin: 15px 0;">
            <h4>👋 Welcome to Fixed Asset Purchase!</h4>
            <p>Choose your purchase type to get started:</p>
            <ul>
                <li><strong>💵 Cash Purchase:</strong> Pay immediately from bank account (creates Journal Entry)</li>
                <li><strong>🏢 Supplier Purchase:</strong> Buy on credit or immediate payment (creates Purchase Invoice)</li>
            </ul>
            <p style="margin-top: 10px; color: #666;">
                <strong>Features:</strong>
                ✅ Auto-generate asset codes | 
                ✅ Create QR codes | 
                ✅ Print asset labels | 
                ✅ Track depreciation
            </p>
        </div>
    `;
    
    frm.dashboard.add_comment(welcome_html, null, true);
}

// ============================================================================
// FIELD QUERIES
// ============================================================================

function set_field_queries(frm) {
    // Supplier Account
    frm.set_query('supplier_account', function() {
        return {
            filters: {
                'company': frm.doc.company,
                'account_type': 'Payable',
                'is_group': 0
            }
        };
    });
    
    // Bank Account
    frm.set_query('bank_account', function() {
        return {
            filters: {
                'company': frm.doc.company,
                'account_type': ['in', ['Bank', 'Cash']],
                'is_group': 0
            }
        };
    });
    
    // Cost Center
    frm.set_query('cost_center', function() {
        return {
            filters: {
                'company': frm.doc.company,
                'is_group': 0
            }
        };
    });
    
    // Department
    frm.set_query('department', function() {
        return {
            filters: {
                'company': frm.doc.company
            }
        };
    });
    
    // Child table queries
    frm.fields_dict['asset_purchase_details'].grid.get_field('location').get_query = function() {
        return {
            filters: {
                'company': frm.doc.company
            }
        };
    };
    
    frm.fields_dict['asset_purchase_details'].grid.get_field('cost_center').get_query = function() {
        return {
            filters: {
                'company': frm.doc.company,
                'is_group': 0
            }
        };
    };
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function format_currency(value, currency) {
    return frappe.format(value, {fieldtype: 'Currency', options: currency || frappe.defaults.get_default('currency')});
}

function flt(val, decimals = 2) {
    return parseFloat(parseFloat(val || 0).toFixed(decimals));
}








// Fixed Asset Purchase - Client Script
// Adds "Create Assets" button that appears only in draft (docstatus === 0)

frappe.ui.form.on('Fixed Asset Purchase', {
    refresh: function(frm) {
        // Show/hide item_linked_code based on purchase type
        if (frm.doc.purchase_type === 'Supplier Purchase') {
            frm.set_df_property('item_linked_code', 'reqd', 1);
            frm.set_df_property('item_linked_code', 'hidden', 0);
        } else {
            frm.set_df_property('item_linked_code', 'reqd', 0);
            frm.set_df_property('item_linked_code', 'hidden', 1);
        }
        
        // Add "Create Assets" button only in draft status
        if (frm.doc.docstatus === 0 && frm.doc.asset_purchase_details && frm.doc.asset_purchase_details.length > 0) {
            // Remove existing button if present to avoid duplicates
            frm.remove_custom_button(__('Create Assets'));
            
            // Add button based on creation status
            if (!frm.doc.assets_created) {
                frm.add_custom_button(__('🏗️ Create Assets'), function() {
                    create_assets_from_purchase(frm);
                }).css({
                    'background-color': '#28a745',
                    'color': 'white',
                    'font-weight': 'bold'
                });
            } else {
                // Show status button (non-clickable)
                frm.add_custom_button(__('✅ Assets Created'), function() {
                    show_created_assets(frm);
                }).css({
                    'background-color': '#17a2b8',
                    'color': 'white',
                    'font-weight': 'bold'
                });
            }
        }
        
        // Add indicator for asset creation status
        if (frm.doc.assets_created) {
            frm.dashboard.add_indicator(__('Assets Created: Yes'), 'green');
        } else if (frm.doc.docstatus === 0) {
            frm.dashboard.add_indicator(__('Assets Created: No'), 'orange');
        }
    },
    
    purchase_type: function(frm) {
        // Make item_linked_code mandatory for supplier purchase
        if (frm.doc.purchase_type === 'Supplier Purchase') {
            frm.set_df_property('item_linked_code', 'reqd', 1);
            frm.set_df_property('item_linked_code', 'hidden', 0);
        } else {
            frm.set_df_property('item_linked_code', 'reqd', 0);
            frm.set_df_property('item_linked_code', 'hidden', 1);
            frm.set_value('item_linked_code', '');
        }
    },
    
    item_linked_code: function(frm) {
        // Validate the selected item
        if (frm.doc.item_linked_code) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Item',
                    name: frm.doc.item_linked_code
                },
                callback: function(r) {
                    if (r.message) {
                        let item = r.message;
                        
                        // Check if disabled
                        if (item.disabled) {
                            frappe.msgprint({
                                title: __('Invalid Item'),
                                message: __('Item {0} is disabled', [frm.doc.item_linked_code]),
                                indicator: 'red'
                            });
                            frm.set_value('item_linked_code', '');
                            return;
                        }
                        
                        // Warn if stock item
                        if (item.is_stock_item) {
                            frappe.msgprint({
                                title: __('Warning'),
                                message: __('Item {0} is a stock item. Consider using a non-stock item for fixed asset purchases.', [frm.doc.item_linked_code]),
                                indicator: 'orange'
                            });
                        }
                    }
                }
            });
        }
    },
    
    before_submit: function(frm) {
        // Validate assets created before submission
        if (!frm.doc.assets_created) {
            frappe.msgprint({
                title: __('Assets Not Created'),
                message: __('Please create Fixed Assets using the "Create Assets" button before submitting this document.'),
                indicator: 'red'
            });
            frappe.validated = false;
        }
    }
});

// Child table triggers
frappe.ui.form.on('Asset Purchase Details', {
    asset_purchase_details_add: function(frm) {
        // Refresh form when items are added to show/update button
        frm.refresh();
    },
    
    asset_purchase_details_remove: function(frm) {
        // Refresh form when items are removed
        frm.refresh();
    },
    
    qty: function(frm, cdt, cdn) {
        calculate_amount(frm, cdt, cdn);
    },
    
    rate: function(frm, cdt, cdn) {
        calculate_amount(frm, cdt, cdn);
    }
});

// Helper function to calculate amount
function calculate_amount(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.amount = flt(row.qty) * flt(row.rate);
    frm.refresh_field('asset_purchase_details');
}

// Function to create assets
function create_assets_from_purchase(frm) {
    // Validate document is saved
    if (!frm.doc.name || frm.doc.__islocal) {
        frappe.msgprint({
            title: __('Document Not Saved'),
            message: __('Please save the document before creating assets'),
            indicator: 'red'
        });
        return;
    }
    
    // Validate we have items
    if (!frm.doc.asset_purchase_details || frm.doc.asset_purchase_details.length === 0) {
        frappe.msgprint({
            title: __('No Items'),
            message: __('Please add asset purchase details before creating assets'),
            indicator: 'red'
        });
        return;
    }
    
    // Confirm with user
    frappe.confirm(
        __('This will create {0} Fixed Asset(s) based on the quantities in the purchase details. Continue?', 
            [get_total_asset_count(frm)]),
        function() {
            // User confirmed, proceed with asset creation
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.fixed_asset_purchase.fixed_asset_purchase.create_assets_from_purchase',
                args: {
                    purchase_name: frm.doc.name
                },
                freeze: true,
                freeze_message: __('Creating Fixed Assets...'),
                callback: function(r) {
                    if (r.message) {
                        if (r.message.success) {
                            // Success - show message with asset links
                            frappe.msgprint({
                                title: __('Assets Created Successfully'),
                                message: r.message.message,
                                indicator: 'green',
                                primary_action: {
                                    label: __('View Assets'),
                                    action: function() {
                                        show_created_assets(frm);
                                    }
                                }
                            });
                            
                            // Reload form to update status
                            frm.reload_doc();
                        } else {
                            // Failed - show error
                            frappe.msgprint({
                                title: __('Asset Creation Failed'),
                                message: r.message.message,
                                indicator: 'red'
                            });
                        }
                    }
                },
                error: function(r) {
                    frappe.msgprint({
                        title: __('Error'),
                        message: __('Failed to create assets. Please check Error Log for details.'),
                        indicator: 'red'
                    });
                }
            });
        }
    );
}

// Function to show created assets
function show_created_assets(frm) {
    frappe.route_options = {
        "purchase_document": frm.doc.name
    };
    frappe.set_route("List", "Fixed Asset");
}

// Helper to get total asset count from quantities
function get_total_asset_count(frm) {
    let total = 0;
    if (frm.doc.asset_purchase_details) {
        frm.doc.asset_purchase_details.forEach(function(item) {
            total += cint(item.qty);
        });
    }
    return total;
}

// Keyboard shortcut for quick asset creation (Ctrl+Shift+A)
$(document).on('keydown', function(e) {
    if (e.ctrlKey && e.shiftKey && e.key === 'A') {
        let frm = cur_frm;
        if (frm && frm.doctype === 'Fixed Asset Purchase' && frm.doc.docstatus === 0 && !frm.doc.assets_created) {
            create_assets_from_purchase(frm);
            e.preventDefault();
        }
    }
});