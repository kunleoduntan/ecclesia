// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt


// ========================================
// WORLD-CLASS BANK RECONCILIATION SYSTEM
// Client Script - Complete Implementation
// ========================================

// ============ MAIN FORM EVENTS - SINGLE BLOCK ============

frappe.ui.form.on('Bank Reconciliation', {
    
    // -------- SETUP & REFRESH --------
    setup: function(frm) {
        // Set read-only properties
        const readonly_fields = [
            'total_unpresented_cheque',
            'total_uncredited_cheque', 'total_direct_withdrawal',
            'total_direct_lodgment', 'balance_per_cash_book',
            'total_debit', 'total_credit', 'balance_diff'
        ];
        
        readonly_fields.forEach(field => {
            frm.set_df_property(field, 'read_only', 1);
        });

        // Setup file upload filters
        frm.set_query('file', function() {
            return {
                filters: {
                    'file_url': ['like', '%.csv'],
                    'file_url': ['like', '%.xlsx']
                }
            };
        });
    },

    refresh: function(frm) {
        // Add custom CSS
        add_custom_styling(frm);
        
        // Add action buttons
        add_action_buttons(frm);
        
        // Add bulk selection buttons to child tables
        add_bulk_selection_buttons(frm);
        
        // Add visual indicators
        add_visual_indicators(frm);
        
        // Add keyboard shortcuts
        setup_keyboard_shortcuts(frm);
        
        // Show reconciliation dashboard
        show_reconciliation_dashboard(frm);
        
        // Add quick filters
        add_quick_filters_to_tables(frm);
    },

    // -------- CALCULATION TRIGGERS --------
    before_save: function(frm) {
        calculate_all_totals(frm);
        calculate_balance_per_cash_book(frm);
    },

    statement_ending_balance: function(frm) {
        calculate_balance_per_cash_book(frm);
    },

    total_unpresented_cheque: function(frm) {
        calculate_balance_per_cash_book(frm);
    },

    total_uncredited_cheque: function(frm) {
        calculate_balance_per_cash_book(frm);
    },

    total_direct_withdrawal: function(frm) {
        calculate_balance_per_cash_book(frm);
    },

    total_direct_lodgment: function(frm) {
        calculate_balance_per_cash_book(frm);
    },

    // -------- BUTTON CLICK HANDLERS --------
    get_unpre: function(frm) {
        get_unpresented_transactions(frm);
    },

    get_uncre: function(frm) {
        get_uncredited_transactions(frm);
    },

    get_dw: function(frm) {
        get_direct_withdrawals(frm);
    },

    get_dl: function(frm) {
        get_direct_lodgments(frm);
    },

    match: function(frm) {
        show_intelligent_matching_dialog(frm);
    }
});

// ============ HELPER FUNCTIONS ============

// Utility function for formatting currency
function format_currency(amount, currency) {
    if (!currency) currency = 'NGN';
    return frappe.format(amount, {fieldtype: 'Currency'}, {inline: true}, frappe.boot.sysdefaults.currency || currency);
}

// Utility function for float conversion
function flt(value, precision = 2) {
    let parsed = parseFloat(value);
    return isNaN(parsed) ? 0 : parseFloat(parsed.toFixed(precision));
}

// ============ CUSTOM STYLING ============

function add_custom_styling(frm) {
    // Button colors
    const button_styles = {
        'get_uncre': '#87CEEB',    // Sky Blue
        'get_unpre': '#90EE90',    // Light Green
        'get_dw': '#4169E1',       // Royal Blue
        'get_dl': '#1E90FF',       // Dodger Blue
        'match': '#32CD32'         // Lime Green
    };

    Object.keys(button_styles).forEach(btn => {
        if (frm.get_field(btn)) {
            frm.get_field(btn).$input.css({
                'background-color': button_styles[btn],
                'color': 'white',
                'font-weight': 'bold',
                'border': 'none',
                'box-shadow': '0 2px 4px rgba(0,0,0,0.2)',
                'transition': 'all 0.3s ease'
            });
        }
    });

    // Table row styling
    const tables = [
        { name: 'bank_account_entry', color1: '#ffffff', color2: '#fffacd' },
        { name: 'bank_statement', color1: '#ffffff', color2: '#FFEFF1' },
        { name: 'unpresented_cheques', color1: '#ffffff', color2: '#fdf5e6' },
        { name: 'uncredited_cheques', color1: '#ffffff', color2: '#e0ffff' },
        { name: 'direct_withdrawal', color1: '#ffffff', color2: '#e9ffdb' },
        { name: 'direct_lodgment', color1: '#ffffff', color2: '#e9ffdb' }
    ];

    tables.forEach(table => {
        if (frm.fields_dict[table.name]) {
            frm.fields_dict[table.name].grid.wrapper.find('.grid-row').each(function(i, row) {
                let row_data = frm.doc[table.name][i];
                
                // Default alternating colors
                let bg_color = i % 2 === 0 ? table.color1 : table.color2;
                
                // Highlight matched rows in green
                if (row_data && row_data.rec === 1) {
                    bg_color = '#d4edda';
                    $(row).css('font-weight', '500');
                }
                
                // Highlight suggested matches in yellow
                if (row_data && row_data.match_confidence > 50 && row_data.rec === 0) {
                    bg_color = '#fff3cd';
                }
                
                $(row).css({
                    'background-color': bg_color,
                    'transition': 'background-color 0.3s ease'
                });
                
                // Add hover effect
                $(row).hover(
                    function() { $(this).css('background-color', '#e3f2fd'); },
                    function() { $(this).css('background-color', bg_color); }
                );
            });
        }
    });

    // Add custom CSS to document (only once)
    if (!$('#bank-reco-custom-styles').length) {
        $('head').append(`
            <style id="bank-reco-custom-styles">
                .reconciliation-dashboard {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 10px;
                    margin-bottom: 20px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                }
                
                .dashboard-card {
                    background: rgba(255,255,255,0.15);
                    backdrop-filter: blur(10px);
                    border-radius: 10px;
                    padding: 15px;
                    text-align: center;
                    transition: transform 0.3s ease;
                }
                
                .dashboard-card:hover {
                    transform: translateY(-5px);
                    background: rgba(255,255,255,0.25);
                }
                
                .dashboard-value {
                    font-size: 28px;
                    font-weight: bold;
                    margin: 10px 0;
                }
                
                .dashboard-label {
                    font-size: 12px;
                    opacity: 0.9;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }
                
                .match-item {
                    border: 2px solid #e0e0e0;
                    border-radius: 8px;
                    padding: 15px;
                    margin-bottom: 15px;
                    background: white;
                    transition: all 0.3s ease;
                }
                
                .match-item:hover {
                    border-color: #667eea;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                }
                
                .match-confidence {
                    display: inline-block;
                    padding: 5px 15px;
                    border-radius: 20px;
                    font-weight: bold;
                    font-size: 14px;
                }
                
                .confidence-high {
                    background: #d4edda;
                    color: #155724;
                }
                
                .confidence-medium {
                    background: #fff3cd;
                    color: #856404;
                }
                
                .confidence-low {
                    background: #f8d7da;
                    color: #721c24;
                }
                
                .quick-filter-bar {
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 8px;
                    margin-bottom: 15px;
                    border: 1px solid #dee2e6;
                }
                
                .filter-badge {
                    display: inline-block;
                    padding: 5px 12px;
                    margin: 3px;
                    background: #667eea;
                    color: white;
                    border-radius: 15px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }
                
                .filter-badge:hover {
                    background: #764ba2;
                    transform: scale(1.05);
                }
                
                .filter-badge.active {
                    background: #28a745;
                }
                
                .transaction-card {
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    padding: 12px;
                    margin-bottom: 10px;
                    background: white;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }
                
                .transaction-card:hover {
                    border-color: #667eea;
                    box-shadow: 0 3px 10px rgba(0,0,0,0.1);
                }
                
                .transaction-card.selected {
                    border-color: #28a745;
                    background: #d4edda;
                }
                
                .bulk-action-bar {
                    background: #fff3cd;
                    padding: 10px 15px;
                    border-radius: 5px;
                    margin-bottom: 10px;
                    display: none;
                }
                
                .bulk-action-bar.show {
                    display: block;
                }

                .progress-ring {
                    transform: rotate(-90deg);
                }

                .progress-ring-circle {
                    transition: stroke-dashoffset 0.35s;
                    transform-origin: 50% 50%;
                }

                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }

                .unmatched-indicator {
                    animation: pulse 2s ease-in-out infinite;
                }
                
                .suggestion-card {
                    background: white;
                    border: 2px solid #e9ecef;
                    border-radius: 8px;
                    padding: 15px;
                    margin-bottom: 15px;
                    transition: all 0.3s ease;
                }
                
                .suggestion-card:hover {
                    border-color: #667eea;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                }
                
                .suggestion-type {
                    display: inline-block;
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-size: 9pt;
                    font-weight: 600;
                    margin-bottom: 10px;
                }
                
                .suggestion-type.critical {
                    background: #dc3545;
                    color: white;
                }
                
                .suggestion-type.warning {
                    background: #ffc107;
                    color: #212529;
                }
                
                .suggestion-type.info {
                    background: #17a2b8;
                    color: white;
                }
            </style>
        `);
    }
}

// ============ ACTION BUTTONS ============

function add_action_buttons(frm) {
    // Clear existing custom buttons to avoid duplicates
    frm.custom_buttons = {};
    frm.page.clear_custom_actions();
    
    // Import Statement button
    frm.add_custom_button(__('📥 Import Statement'), function() {
        show_import_dialog(frm);
    }, __('Actions'));

    // Manual Match button
    frm.add_custom_button(__('🔗 Manual Match'), function() {
        show_manual_match_dialog(frm);
    }, __('Actions'));
    
    // Duplicate Check button
    frm.add_custom_button(__('🔍 Check Duplicates'), function() {
        check_for_duplicates(frm);
    }, __('Actions'));

    // Clear All Tables
    frm.add_custom_button(__('🗑️ Clear Tables'), function() {
        frappe.confirm(
            __('Are you sure you want to clear all tables? This cannot be undone.'),
            function() {
                clear_all_tables(frm);
            }
        );
    }, __('Actions'));

    // Export Unmatched
    frm.add_custom_button(__('📤 Export Unmatched'), function() {
        export_unmatched_transactions(frm);
    }, __('Actions'));

    // Get Bank Entries
    frm.add_custom_button(__('📊 Get Bank Entries'), function() {
        frappe.call({
            method: "ecclesia.ecclesia.doctype.bank_reconciliation.bank_reconciliation.get_bank_reco_entries",
            args: { docname: frm.doc.name },
            freeze: true,
            freeze_message: __("Fetching bank entries..."),
            callback: function(r) {
                if (r.message) {
                    frm.reload_doc();
                    frappe.show_alert({
                        message: __("Appended {0} entries", [r.message.count]),
                        indicator: 'green'
                    });
                }
            }
        });
    }, __('Actions'));
    
    // Progress Tracker
    frm.add_custom_button(__('📈 Progress'), function() {
        show_reconciliation_progress(frm);
    }, __('Actions'));
    
    // Smart Suggestions
    frm.add_custom_button(__('💡 Suggestions'), function() {
        show_smart_suggestions(frm);
    }, __('Actions'));
    
    // Reconciliation Assistant
    frm.add_custom_button(__('🤖 Assistant'), function() {
        show_reconciliation_assistant(frm);
    }, __('Actions'));

    // Generate Report
    frm.add_custom_button(__('📄 Generate Report'), function() {
        generate_reconciliation_report(frm);
    }, __('Actions'));

    // Create Journal Entries
    if (frm.doc.docstatus === 0) {
        frm.add_custom_button(__('💰 Create Entries'), function() {
            frappe.confirm(
                __('This will create Payment/Receipt entries for Direct Withdrawals and Lodgments. Continue?'),
                function() {
                    frappe.call({
                        method: "ecclesia.ecclesia.doctype.bank_reconciliation.bank_reconciliation.create_payments_and_receipts_transactions",
                        args: { docname: frm.doc.name },
                        freeze: true,
                        freeze_message: __("Creating transactions..."),
                        callback: function(r) {
                            if (!r.exc) {
                                frm.reload_doc();
                            }
                        }
                    });
                }
            );
        }, __('Actions'));
    }

    // Print button - Fixed
    frm.add_custom_button(__('🖨️ Print Statement'), function() {
        // Open print view in new window
        window.open(frappe.urllib.get_full_url('/printview?'
            + 'doctype=' + encodeURIComponent(frm.doctype)
            + '&name=' + encodeURIComponent(frm.doc.name)
            + '&format=Standard'
            + '&no_letterhead=0'
            + '&letterhead=Standard'
            + '&settings=%7B%7D'
            + '&_lang=en'));
    }, __('Actions'));
}
// ============ BULK SELECTION BUTTONS ============

function add_bulk_selection_buttons(frm) {
    const tables = [
        { name: 'bank_account_entry', label: 'Bank Entries' },
        { name: 'bank_statement', label: 'Bank Statement' },
        { name: 'unpresented_cheques', label: 'Unpresented' },
        { name: 'uncredited_cheques', label: 'Uncredited' }
    ];

    tables.forEach(table => {
        if (frm.fields_dict[table.name]) {
            const grid = frm.fields_dict[table.name].grid;

            // Check All
            grid.add_custom_button(__('✓ Check All'), function() {
                (frm.doc[table.name] || []).forEach(row => {
                    frappe.model.set_value(row.doctype, row.name, 'rec', 1);
                });
                frm.refresh_field(table.name);
                frappe.show_alert({
                    message: __('All {0} items checked', [table.label]),
                    indicator: 'green'
                });
            }).addClass('btn-xs btn-success');

            // Uncheck All
            grid.add_custom_button(__('✗ Uncheck All'), function() {
                (frm.doc[table.name] || []).forEach(row => {
                    frappe.model.set_value(row.doctype, row.name, 'rec', 0);
                });
                frm.refresh_field(table.name);
                frappe.show_alert({
                    message: __('All {0} items unchecked', [table.label]),
                    indicator: 'orange'
                });
            }).addClass('btn-xs btn-default');

            // Invert Selection
            grid.add_custom_button(__('⇄ Invert'), function() {
                (frm.doc[table.name] || []).forEach(row => {
                    frappe.model.set_value(row.doctype, row.name, 'rec', row.rec === 1 ? 0 : 1);
                });
                frm.refresh_field(table.name);
                frappe.show_alert({
                    message: __('Selection inverted for {0}', [table.label]),
                    indicator: 'blue'
                });
            }).addClass('btn-xs btn-info');

            // Check Filtered (visible rows only)
            grid.add_custom_button(__('✓ Check Visible'), function() {
                let visible_rows = grid.get_data();
                visible_rows.forEach(row => {
                    frappe.model.set_value(row.doctype, row.name, 'rec', 1);
                });
                frm.refresh_field(table.name);
                frappe.show_alert({
                    message: __('Checked {0} visible items', [visible_rows.length]),
                    indicator: 'green'
                });
            }).addClass('btn-xs btn-primary');
        }
    });
}

// ============ VISUAL INDICATORS ============

function add_visual_indicators(frm) {
    // Add unmatched count badges
    const tables_to_track = [
        { name: 'bank_account_entry', section: 'transaction_section', label: 'Bank Entries' },
        { name: 'bank_statement', tab: 'statements_tab', label: 'Statements' }
    ];

    tables_to_track.forEach(table => {
        let unmatched = (frm.doc[table.name] || []).filter(r => r.rec === 0).length;
        
        if (unmatched > 0) {
            let selector = table.section ? 
                `[data-fieldname="${table.section}"]` : 
                `.form-tabs a[data-fieldname="${table.tab}"]`;
            
            $(selector).find('.badge').remove(); // Remove old badge
            $(selector).append(
                `<span class="badge badge-danger unmatched-indicator" style="margin-left: 5px;">${unmatched}</span>`
            );
        }
    });

    // Add reconciliation status indicator
    let status_html = '';
    if (frm.doc.balance_diff === 0) {
        status_html = `
            <div style="background: #d4edda; color: #155724; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold;">
                ✓ RECONCILIATION COMPLETE - BALANCED
            </div>
        `;
    } else if (frm.doc.balance_diff) {
        status_html = `
            <div style="background: #f8d7da; color: #721c24; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold;">
                ⚠ DIFFERENCE: ${format_currency(frm.doc.balance_diff, frm.doc.account_currency)}
            </div>
        `;
    }
    
    if (status_html) {
        frm.fields_dict['balance_diff'].$wrapper.before(status_html);
    }
}

// ============ RECONCILIATION DASHBOARD ============

function show_reconciliation_dashboard(frm) {
    try {
        let total_entries = (frm.doc.bank_account_entry || []).length;
        let matched_entries = (frm.doc.bank_account_entry || []).filter(r => r.rec === 1).length;
        let percent = total_entries > 0 ? Math.round((matched_entries / total_entries) * 100) : 0;
        
        let html = `
            <div class="reconciliation-dashboard" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; padding: 15px; border-radius: 8px; margin: 15px 0;">
                <div class="row">
                    <div class="col-md-4" style="text-align: center; padding: 10px;">
                        <h4 style="margin: 0; color: white;">${total_entries}</h4>
                        <small>Total Entries</small>
                    </div>
                    <div class="col-md-4" style="text-align: center; padding: 10px;">
                        <h4 style="margin: 0; color: white;">${matched_entries}</h4>
                        <small>Matched</small>
                    </div>
                    <div class="col-md-4" style="text-align: center; padding: 10px;">
                        <h4 style="margin: 0; color: white;">${percent}%</h4>
                        <small>Match Rate</small>
                    </div>
                </div>
            </div>
        `;
        
        // Remove old dashboard if exists
        $('.reconciliation-dashboard').remove();
        
        // Insert at top of form - most reliable method
        frm.$wrapper.find('.form-layout').first().prepend(html);
        
    } catch(e) {
        console.log("Dashboard error (non-critical):", e);
    }
}


// ============ IMPORT DIALOG ============

function show_import_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __('📥 Import Bank Statement'),
        size: 'extra-large',
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'import_help',
                options: `
                    <div class="alert alert-info">
                        <strong>Supported Formats:</strong> CSV, Excel (.xlsx, .xls)<br>
                        <strong>Steps:</strong> Upload file → Preview → Map columns → Import
                    </div>
                `
            },
            {
                fieldtype: 'Attach',
                fieldname: 'file',
                label: __('Upload File'),
                reqd: 1,
                onchange: function() {
                    preview_uploaded_file(d, frm);
                }
            },
            {
                fieldtype: 'Section Break',
                label: __('Preview')
            },
            {
                fieldtype: 'HTML',
                fieldname: 'preview_html'
            },
            {
                fieldtype: 'Section Break',
                label: __('Column Mapping'),
                depends_on: 'eval:doc.file'
            },
            {
                fieldtype: 'Select',
                fieldname: 'date_column',
                label: __('Date Column'),
                options: [''],
                reqd: 1
            },
            {
                fieldtype: 'Column Break'
            },
            {
                fieldtype: 'Select',
                fieldname: 'party_column',
                label: __('Party/Description Column'),
                options: ['']
            },
            {
                fieldtype: 'Column Break'
            },
            {
                fieldtype: 'Select',
                fieldname: 'debit_column',
                label: __('Debit Column'),
                options: ['']
            },
            {
                fieldtype: 'Column Break'
            },
            {
                fieldtype: 'Select',
                fieldname: 'credit_column',
                label: __('Credit Column'),
                options: ['']
            },
            {
                fieldtype: 'Section Break'
            },
            {
                fieldtype: 'Int',
                fieldname: 'header_row',
                label: __('Header Row Number'),
                default: 1,
                description: __('Row number containing column headers (usually 1)')
            },
            {
                fieldtype: 'Column Break'
            },
            {
                fieldtype: 'Check',
                fieldname: 'clear_existing',
                label: __('Clear Existing Statements'),
                default: 0,
                description: __('Remove all existing statement entries before import')
            },
            {
                fieldtype: 'Column Break'
            },
            {
                fieldtype: 'Check',
                fieldname: 'skip_duplicates',
                label: __('Skip Duplicate Entries'),
                default: 1
            }
        ],
        primary_action_label: __('Import'),
        primary_action: function(values) {
            if (!values.file) {
                frappe.msgprint(__('Please upload a file'));
                return;
            }

            frappe.call({
                method: 'ecclesia.ecclesia.doctype.bank_reconciliation.bank_reconciliation.import_bank_statement_with_mapping',
                args: {
                    docname: frm.doc.name,
                    file_url: values.file,
                    date_column: values.date_column,
                    party_column: values.party_column,
                    debit_column: values.debit_column,
                    credit_column: values.credit_column,
                    header_row: values.header_row,
                    clear_existing: values.clear_existing,
                    skip_duplicates: values.skip_duplicates
                },
                freeze: true,
                freeze_message: __('Importing...'),
                callback: function(r) {
                    if (r.message) {
                        frappe.show_alert({
                            message: __('Successfully imported {0} transactions', [r.message.count]),
                            indicator: 'green'
                        });
                        frm.refresh_field('bank_statement');
                        d.hide();
                    }
                }
            });
        }
    });

    d.show();
}

function preview_uploaded_file(dialog, frm) {
    let file_url = dialog.get_value('file');
    
    if (!file_url) return;

    frappe.call({
        method: 'ecclesia.ecclesia.doctype.bank_reconciliation.bank_reconciliation.preview_statement_file',
        args: { 
            file_url: file_url,
            docname: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                let data = r.message;
                
                // Populate column dropdowns
                let columns = [''].concat(data.columns);
                ['date_column', 'party_column', 'debit_column', 'credit_column'].forEach(field => {
                    dialog.set_df_property(field, 'options', columns);
                });

                // Auto-detect columns
                auto_detect_columns(dialog, data.columns);

                // Show preview table
                let preview_html = `
                    <div style="max-height: 300px; overflow: auto;">
                        <table class="table table-bordered table-hover">
                            <thead style="position: sticky; top: 0; background: white;">
                                <tr>
                                    ${data.columns.map(col => `<th>${col}</th>`).join('')}
                                </tr>
                            </thead>
                            <tbody>
                                ${data.preview_rows.map(row => `
                                    <tr>
                                        ${row.map(cell => `<td>${cell || ''}</td>`).join('')}
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                    <div class="text-muted" style="margin-top: 10px;">
                        <small>Showing first ${data.preview_rows.length} rows of ${data.total_rows} total rows</small>
                    </div>
                `;

                dialog.fields_dict.preview_html.$wrapper.html(preview_html);
            }
        }
    });
}

function auto_detect_columns(dialog, columns) {
    // Auto-detect date column
    const date_patterns = ['date', 'posting', 'transaction', 'trans date'];
    let date_col = columns.find(col => 
        date_patterns.some(pattern => col.toLowerCase().includes(pattern))
    );
    if (date_col) dialog.set_value('date_column', date_col);

    // Auto-detect party column
    const party_patterns = ['party', 'description', 'narration', 'remarks', 'detail'];
    let party_col = columns.find(col => 
        party_patterns.some(pattern => col.toLowerCase().includes(pattern))
    );
    if (party_col) dialog.set_value('party_column', party_col);

    // Auto-detect debit column
    const debit_patterns = ['debit', 'withdrawal', 'payment', 'dr'];
    let debit_col = columns.find(col => 
        debit_patterns.some(pattern => col.toLowerCase().includes(pattern))
    );
    if (debit_col) dialog.set_value('debit_column', debit_col);

    // Auto-detect credit column
    const credit_patterns = ['credit', 'deposit', 'receipt', 'cr'];
    let credit_col = columns.find(col => 
        credit_patterns.some(pattern => col.toLowerCase().includes(pattern))
    );
    if (credit_col) dialog.set_value('credit_column', credit_col);
}

// ============ INTELLIGENT MATCHING DIALOG ============

function show_intelligent_matching_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __('🎯 Intelligent Transaction Matching'),
        size: 'large',
        fields: [
            {
                fieldtype: 'HTML',
                options: `
                    <div class="alert alert-info">
                        <strong>Advanced Matching Engine</strong><br>
                        Uses multiple algorithms: Exact matching, Fuzzy matching, Amount tolerance, Date proximity, and ML-based suggestions
                    </div>
                `
            },
            {
                fieldtype: 'Section Break',
                label: __('Matching Parameters')
            },
            {
                fieldtype: 'Float',
                fieldname: 'amount_tolerance',
                label: __('Amount Tolerance'),
                default: 1.00,
                description: __('Maximum difference in amounts to consider as match')
            },
            {
                fieldtype: 'Column Break'
            },
            {
                fieldtype: 'Int',
                fieldname: 'date_range',
                label: __('Date Range (±days)'),
                default: 5,
                description: __('Number of days before/after to search for matches')
            },
            {
                fieldtype: 'Section Break'
            },
            {
                fieldtype: 'Check',
                fieldname: 'cross_match',
                label: __('Enable Cross Matching'),
                default: 1,
                description: __('Match debit in one with credit in another')
            },
            {
                fieldtype: 'Column Break'
            },
            {
                fieldtype: 'Check',
                fieldname: 'fuzzy_party',
                label: __('Fuzzy Party Name Matching'),
                default: 1,
                description: __('Use intelligent party name comparison')
            },
            {
                fieldtype: 'Section Break'
            },
            {
                fieldtype: 'Int',
                fieldname: 'min_confidence',
                label: __('Minimum Confidence (%)'),
                default: 60,
                description: __('Minimum confidence score for auto-matching (60-100)')
            },
            {
                fieldtype: 'Column Break'
            },
            {
                fieldtype: 'Check',
                fieldname: 'auto_match_high_confidence',
                label: __('Auto-match High Confidence (>90%)'),
                default: 1
            }
        ],
        primary_action_label: __('Start Matching'),
        primary_action: function(values) {
            run_intelligent_matching(frm, values, d);
        }
    });

    d.show();
}

function run_intelligent_matching(frm, params, dialog) {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.bank_reconciliation.bank_reconciliation.advanced_auto_match',
        args: {
            docname: frm.doc.name,
            match_tolerance: params.amount_tolerance,
            date_range: params.date_range,
            cross_match: params.cross_match,
            fuzzy_party: params.fuzzy_party,
            min_confidence: params.min_confidence,
            auto_match_high: params.auto_match_high_confidence
        },
        freeze: true,
        freeze_message: __('Running intelligent matching algorithm...'),
        callback: function(r) {
            if (r.message) {
                dialog.hide();
                show_matching_results(frm, r.message);
            }
        }
    });
}

function show_matching_results(frm, results) {
    let d = new frappe.ui.Dialog({
        title: __('🎯 Matching Results'),
        size: 'extra-large',
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'results_summary'
            },
            {
                fieldtype: 'Section Break',
                label: __('Suggested Matches for Review'),
                depends_on: 'eval:doc.has_suggestions'
            },
            {
                fieldtype: 'HTML',
                fieldname: 'suggestions_html'
            }
        ],
        primary_action_label: __('Apply Selected Matches'),
        primary_action: function() {
            apply_selected_matches(frm, d);
        }
    });

    // Summary
    let summary_html = `
        <div class="row" style="margin-bottom: 20px;">
            <div class="col-md-12">
                <table class="table table-bordered">
                    <thead>
                        <tr style="background: #f8f9fa;">
                            <th>Match Type</th>
                            <th class="text-right">Count</th>
                            <th class="text-right">Percentage</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>✓ Auto-Matched (High Confidence)</td>
                            <td class="text-right"><strong>${results.auto_matched}</strong></td>
                            <td class="text-right">${results.auto_matched_pct}%</td>
                        </tr>
                        <tr>
                            <td>⚡ Suggested for Review</td>
                            <td class="text-right"><strong>${results.suggested}</strong></td>
                            <td class="text-right">${results.suggested_pct}%</td>
                        </tr>
                        <tr>
                            <td>⚠ Unmatched</td>
                            <td class="text-right"><strong>${results.unmatched}</strong></td>
                            <td class="text-right">${results.unmatched_pct}%</td>
                        </tr>
                        <tr style="background: #e3f2fd; font-weight: bold;">
                            <td>Total Transactions</td>
                            <td class="text-right">${results.total}</td>
                            <td class="text-right">100%</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
        ${results.auto_matched > 0 ? `
            <div class="alert alert-success">
                <strong>Success!</strong> ${results.auto_matched} transactions auto-matched with high confidence.
            </div>
        ` : ''}
    `;

    d.fields_dict.results_summary.$wrapper.html(summary_html);

    // Suggestions
    if (results.review_items && results.review_items.length > 0) {
        d.set_value('has_suggestions', 1);
        
        let suggestions_html = '<div class="suggestions-container">';
        
        results.review_items.forEach((item, idx) => {
            let confidence_class = item.confidence > 0.8 ? 'confidence-high' : 
                                 item.confidence > 0.6 ? 'confidence-medium' : 'confidence-low';
            
            suggestions_html += `
                <div class="match-item" data-index="${idx}">
                    <div class="row">
                        <div class="col-md-1 text-center">
                            <input type="checkbox" class="match-checkbox" data-index="${idx}" 
                                   ${item.confidence > 0.8 ? 'checked' : ''}>
                        </div>
                        <div class="col-md-4">
                            <h6>Bank Entry</h6>
                            <strong>${item.entry.party || 'N/A'}</strong><br>
                            <small class="text-muted">${item.entry.date}</small><br>
                            Amount: <strong>${format_currency(item.entry.amount, frm.doc.account_currency)}</strong>
                        </div>
                        <div class="col-md-2 text-center">
                            <span class="match-confidence ${confidence_class}">
                                ${Math.round(item.confidence * 100)}% Match
                            </span>
                            <br><br>
                            <small class="text-muted">${item.match_type}</small>
                        </div>
                        <div class="col-md-4">
                            <h6>Bank Statement</h6>
                            <strong>${item.statement.party || 'N/A'}</strong><br>
                            <small class="text-muted">${item.statement.date}</small><br>
                            Amount: <strong>${format_currency(item.statement.amount, frm.doc.account_currency)}</strong>
                        </div>
                        <div class="col-md-1 text-center">
                            <button class="btn btn-sm btn-default view-details" data-index="${idx}">
                                Details
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });
        
        suggestions_html += '</div>';
        
        d.fields_dict.suggestions_html.$wrapper.html(suggestions_html);
        
        // Add click handlers
        d.fields_dict.suggestions_html.$wrapper.find('.view-details').click(function() {
            let idx = $(this).data('index');
            show_match_details(results.review_items[idx], frm);
        });
    }

    d.show();
    
    // Refresh form to show auto-matched items
    frm.reload_doc();
}

function show_match_details(match_item, frm) {
    let html = `
        <div style="padding: 20px;">
            <h5>Match Analysis</h5>
            <hr>
            <div class="row">
                <div class="col-md-6">
                    <h6>Bank Entry</h6>
                    <table class="table table-bordered">
                        <tr><th>Party:</th><td>${match_item.entry.party || 'N/A'}</td></tr>
                        <tr><th>Date:</th><td>${match_item.entry.date}</td></tr>
                        <tr><th>Amount:</th><td>${format_currency(match_item.entry.amount, frm.doc.account_currency)}</td></tr>
                        <tr><th>Voucher:</th><td>${match_item.entry.voucher || 'N/A'}</td></tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6>Bank Statement</h6>
                    <table class="table table-bordered">
                        <tr><th>Party:</th><td>${match_item.statement.party || 'N/A'}</td></tr>
                        <tr><th>Date:</th><td>${match_item.statement.date}</td></tr>
                        <tr><th>Amount:</th><td>${format_currency(match_item.statement.amount, frm.doc.account_currency)}</td></tr>
                        <tr><th>Voucher:</th><td>${match_item.statement.voucher || 'N/A'}</td></tr>
                    </table>
                </div>
            </div>
            <hr>
            <div class="alert alert-info">
                <strong>Match Type:</strong> ${match_item.match_type}<br>
                <strong>Confidence Score:</strong> ${Math.round(match_item.confidence * 100)}%
            </div>
        </div>
    `;
    
    frappe.msgprint({
        title: __('Match Details'),
        message: html,
        wide: true
    });
}

function apply_selected_matches(frm, dialog) {
    let selected = [];
    dialog.$wrapper.find('.match-checkbox:checked').each(function() {
        selected.push($(this).data('index'));
    });

    if (selected.length === 0) {
        frappe.msgprint(__('No matches selected'));
        return;
    }

    frappe.call({
        method: 'ecclesia.ecclesia.doctype.bank_reconciliation.bank_reconciliation.apply_suggested_matches',
        args: {
            docname: frm.doc.name,
            selected_indices: selected
        },
        callback: function(r) {
            if (r.message) {
                frappe.show_alert({
                    message: __('Applied {0} matches', [selected.length]),
                    indicator: 'green'
                });
                dialog.hide();
                frm.reload_doc();
            }
        }
    });
}

// ============ MANUAL MATCHING DIALOG ============

function show_manual_match_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __('🔗 Manual Transaction Matching'),
        size: 'extra-large',
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'manual_match_interface'
            }
        ],
        primary_action_label: __('Save Matches'),
        primary_action: function() {
            save_manual_matches(frm, d);
        }
    });

    let unmatched_entries = (frm.doc.bank_account_entry || []).filter(r => r.rec === 0);
    let unmatched_statements = (frm.doc.bank_statement || []).filter(r => r.rec === 0);

    let html = `
        <div class="manual-match-container">
            <div class="row">
                <div class="col-md-5">
                    <h5>Bank Entries <span class="badge badge-info">${unmatched_entries.length}</span></h5>
                    <input type="text" class="form-control mb-2" id="search-entries" placeholder="Search entries...">
                    <div id="entries-list" style="max-height: 500px; overflow-y: auto;">
                        ${unmatched_entries.map((entry, idx) => `
                            <div class="transaction-card" data-type="entry" data-idx="${entry.idx}">
                                <div><strong>${entry.party || 'N/A'}</strong></div>
                                <div class="text-muted"><small>${entry.posting_date}</small></div>
                                <div>
                                    ${entry.debit_amount ? `Debit: ${format_currency(entry.debit_amount, frm.doc.account_currency)}` : ''}
                                    ${entry.credit_amount ? `Credit: ${format_currency(entry.credit_amount, frm.doc.account_currency)}` : ''}
                                </div>
                                ${entry.remarks ? `<div class="text-muted"><small>${entry.remarks}</small></div>` : ''}
                            </div>
                        `).join('')}
                    </div>
                </div>
                <div class="col-md-2 text-center">
                    <div style="margin-top: 200px;">
                        <button class="btn btn-primary btn-match" id="btn-match" disabled>
                            Match →
                        </button>
                        <br><br>
                        <button class="btn btn-default btn-clear-selection" id="btn-clear">
                            Clear
                        </button>
                    </div>
                </div>
                <div class="col-md-5">
                    <h5>Bank Statements <span class="badge badge-info">${unmatched_statements.length}</span></h5>
                    <input type="text" class="form-control mb-2" id="search-statements" placeholder="Search statements...">
                    <div id="statements-list" style="max-height: 500px; overflow-y: auto;">
                        ${unmatched_statements.map((stmt, idx) => `
                            <div class="transaction-card" data-type="statement" data-idx="${stmt.idx}">
                                <div><strong>${stmt.party || 'N/A'}</strong></div>
                                <div class="text-muted"><small>${stmt.posting_date}</small></div>
                                <div>
                                    ${stmt.debit_amount ? `Debit: ${format_currency(stmt.debit_amount, frm.doc.account_currency)}` : ''}
                                    ${stmt.credit_amount ? `Credit: ${format_currency(stmt.credit_amount, frm.doc.account_currency)}` : ''}
                                </div>
                                ${stmt.remarks ? `<div class="text-muted"><small>${stmt.remarks}</small></div>` : ''}
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
            <hr>
            <div class="matched-pairs-section">
                <h5>Manually Matched Pairs <span class="badge badge-success" id="matched-count">0</span></h5>
                <div id="matched-pairs-list"></div>
            </div>
        </div>
    `;

    d.fields_dict.manual_match_interface.$wrapper.html(html);

    // Enable selection logic
    let selected_entry = null;
    let selected_statement = null;
    let manual_matches = [];

    d.$wrapper.find('.transaction-card').click(function() {
        let type = $(this).data('type');
        let idx = $(this).data('idx');

        // Remove previous selection of same type
        d.$wrapper.find(`.transaction-card[data-type="${type}"]`).removeClass('selected');
        
        // Select this card
        $(this).addClass('selected');

        if (type === 'entry') {
            selected_entry = idx;
        } else {
            selected_statement = idx;
        }

        // Enable match button if both selected
        if (selected_entry && selected_statement) {
            d.$wrapper.find('#btn-match').prop('disabled', false);
        }
    });

    // Match button click
    d.$wrapper.find('#btn-match').click(function() {
        if (selected_entry && selected_statement) {
            // Add to matched pairs
            manual_matches.push({
                entry_idx: selected_entry,
                statement_idx: selected_statement
            });

            // Remove from lists
            d.$wrapper.find(`.transaction-card[data-type="entry"][data-idx="${selected_entry}"]`).fadeOut();
            d.$wrapper.find(`.transaction-card[data-type="statement"][data-idx="${selected_statement}"]`).fadeOut();

            // Show in matched pairs
            let entry = frm.doc.bank_account_entry.find(e => e.idx === selected_entry);
            let stmt = frm.doc.bank_statement.find(s => s.idx === selected_statement);

            d.$wrapper.find('#matched-pairs-list').append(`
                <div class="alert alert-success" data-match-idx="${manual_matches.length - 1}">
                    <button class="close" data-match-idx="${manual_matches.length - 1}">&times;</button>
                    <strong>Entry:</strong> ${entry.party} - ${format_currency(entry.debit_amount || entry.credit_amount, frm.doc.account_currency)}
                    <strong>⇄ Statement:</strong> ${stmt.party} - ${format_currency(stmt.debit_amount || stmt.credit_amount, frm.doc.account_currency)}
                </div>
            `);

            // Update count
            d.$wrapper.find('#matched-count').text(manual_matches.length);

            // Clear selection
            selected_entry = null;
            selected_statement = null;
            d.$wrapper.find('.transaction-card').removeClass('selected');
            d.$wrapper.find('#btn-match').prop('disabled', true);
        }
    });

    // Clear button
    d.$wrapper.find('#btn-clear').click(function() {
        selected_entry = null;
        selected_statement = null;
        d.$wrapper.find('.transaction-card').removeClass('selected');
        d.$wrapper.find('#btn-match').prop('disabled', true);
    });

    // Remove matched pair
    d.$wrapper.on('click', '.close', function() {
        let idx = $(this).data('match-idx');
        manual_matches.splice(idx, 1);
        $(this).parent().remove();
        d.$wrapper.find('#matched-count').text(manual_matches.length);
    });

    // Search functionality
    d.$wrapper.find('#search-entries').on('keyup', function() {
        let search = $(this).val().toLowerCase();
        d.$wrapper.find('#entries-list .transaction-card').each(function() {
            let text = $(this).text().toLowerCase();
            $(this).toggle(text.includes(search));
        });
    });

    d.$wrapper.find('#search-statements').on('keyup', function() {
        let search = $(this).val().toLowerCase();
        d.$wrapper.find('#statements-list .transaction-card').each(function() {
            let text = $(this).text().toLowerCase();
            $(this).toggle(text.includes(search));
        });
    });

    // Store matches in dialog
    d.manual_matches = manual_matches;

    d.show();
}

function save_manual_matches(frm, dialog) {
    let matches = dialog.manual_matches;

    if (matches.length === 0) {
        frappe.msgprint(__('No manual matches created'));
        return;
    }

    frappe.call({
        method: 'ecclesia.ecclesia.doctype.bank_reconciliation.bank_reconciliation.save_manual_matches',
        args: {
            docname: frm.doc.name,
            matches: matches
        },
        callback: function(r) {
            if (r.message) {
                frappe.show_alert({
                    message: __('Saved {0} manual matches', [matches.length]),
                    indicator: 'green'
                });
                dialog.hide();
                frm.reload_doc();
            }
        }
    });
}

// ============ DUPLICATE DETECTION ============

function check_for_duplicates(frm) {
    let duplicates = [];
    let seen = new Map();
    
    // Check in bank_account_entry
    (frm.doc.bank_account_entry || []).forEach((entry, idx) => {
        let key = `${entry.posting_date}_${entry.party}_${entry.debit_amount || entry.credit_amount}`;
        
        if (seen.has(key)) {
            duplicates.push({
                type: 'Bank Entry',
                original: seen.get(key),
                duplicate: idx + 1,
                party: entry.party,
                amount: entry.debit_amount || entry.credit_amount,
                date: entry.posting_date
            });
        } else {
            seen.set(key, idx + 1);
        }
    });
    
    // Check in bank_statement
    seen.clear();
    (frm.doc.bank_statement || []).forEach((stmt, idx) => {
        let key = `${stmt.posting_date}_${stmt.party}_${stmt.debit_amount || stmt.credit_amount}`;
        
        if (seen.has(key)) {
            duplicates.push({
                type: 'Bank Statement',
                original: seen.get(key),
                duplicate: idx + 1,
                party: stmt.party,
                amount: stmt.debit_amount || stmt.credit_amount,
                date: stmt.posting_date
            });
        } else {
            seen.set(key, idx + 1);
        }
    });
    
    if (duplicates.length > 0) {
        show_duplicates_dialog(duplicates, frm);
    } else {
        frappe.msgprint({
            title: __('No Duplicates Found'),
            message: __('No duplicate entries detected.'),
            indicator: 'green'
        });
    }
}

function show_duplicates_dialog(duplicates, frm) {
    let html = `
        <div class="duplicate-results">
            <div class="alert alert-warning">
                Found ${duplicates.length} potential duplicate(s)
            </div>
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>Row</th>
                        <th>Party</th>
                        <th>Date</th>
                        <th>Amount</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    ${duplicates.map(dup => `
                        <tr>
                            <td>${dup.type}</td>
                            <td>Original: Row ${dup.original}<br>Duplicate: Row ${dup.duplicate}</td>
                            <td>${dup.party || 'N/A'}</td>
                            <td>${dup.date}</td>
                            <td>${format_currency(dup.amount, frm.doc.account_currency)}</td>
                            <td>
                                <button class="btn btn-xs btn-danger remove-duplicate" 
                                        data-type="${dup.type}" 
                                        data-row="${dup.duplicate}">
                                    Remove
                                </button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
    
    let d = new frappe.ui.Dialog({
        title: __('Duplicate Detection Results'),
        fields: [{
            fieldtype: 'HTML',
            fieldname: 'duplicates',
            options: html
        }],
        size: 'large'
    });
    
    d.show();
    
    // Remove duplicate handler
    d.$wrapper.find('.remove-duplicate').click(function() {
        let type = $(this).data('type');
        let row = $(this).data('row') - 1; // Convert to 0-based index
        
        if (type === 'Bank Entry') {
            frm.doc.bank_account_entry.splice(row, 1);
            frm.refresh_field('bank_account_entry');
        } else {
            frm.doc.bank_statement.splice(row, 1);
            frm.refresh_field('bank_statement');
        }
        
        $(this).closest('tr').fadeOut();
        frappe.show_alert({
            message: __('Duplicate removed'),
            indicator: 'green'
        });
    });
}

// ============ PROGRESS TRACKING ============

function show_reconciliation_progress(frm) {
    let total_entries = (frm.doc.bank_account_entry || []).length;
    let matched_entries = (frm.doc.bank_account_entry || []).filter(r => r.rec === 1).length;
    let total_statements = (frm.doc.bank_statement || []).length;
    let matched_statements = (frm.doc.bank_statement || []).filter(r => r.rec === 1).length;
    
    let entry_progress = total_entries > 0 ? (matched_entries / total_entries * 100) : 0;
    let stmt_progress = total_statements > 0 ? (matched_statements / total_statements * 100) : 0;
    let overall_progress = ((entry_progress + stmt_progress) / 2).toFixed(1);
    
    let html = `
        <div style="padding: 20px;">
            <h4 style="text-align: center; margin-bottom: 30px;">Reconciliation Progress</h4>
            
            <!-- Overall Progress -->
            <div style="margin-bottom: 40px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <strong>Overall Progress</strong>
                    <strong>${overall_progress}%</strong>
                </div>
                <div style="background: #e9ecef; height: 30px; border-radius: 15px; overflow: hidden;">
                    <div style="background: linear-gradient(90deg, #667eea, #764ba2); 
                                width: ${overall_progress}%; height: 100%; 
                                transition: width 0.5s ease;"></div>
                </div>
            </div>
            
            <!-- Bank Entries Progress -->
            <div style="margin-bottom: 30px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <span>Bank Entries</span>
                    <span>${matched_entries} / ${total_entries}</span>
                </div>
                <div style="background: #e9ecef; height: 20px; border-radius: 10px; overflow: hidden;">
                    <div style="background: #28a745; width: ${entry_progress}%; 
                                height: 100%; transition: width 0.5s ease;"></div>
                </div>
            </div>
            
            <!-- Bank Statements Progress -->
            <div style="margin-bottom: 30px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <span>Bank Statements</span>
                    <span>${matched_statements} / ${total_statements}</span>
                </div>
                <div style="background: #e9ecef; height: 20px; border-radius: 10px; overflow: hidden;">
                    <div style="background: #17a2b8; width: ${stmt_progress}%; 
                                height: 100%; transition: width 0.5s ease;"></div>
                </div>
            </div>
            
            <!-- Statistics Grid -->
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-top: 30px;">
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 24pt; font-weight: bold; color: #dc3545;">
                        ${total_entries - matched_entries}
                    </div>
                    <div style="color: #6c757d;">Unmatched Entries</div>
                </div>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 24pt; font-weight: bold; color: #ffc107;">
                        ${total_statements - matched_statements}
                    </div>
                    <div style="color: #6c757d;">Unmatched Statements</div>
                </div>
            </div>
            
            ${overall_progress >= 100 ? `
                <div style="margin-top: 30px; padding: 20px; background: #d4edda; 
                            border-radius: 8px; text-align: center; color: #155724;">
                    <h3>🎉 Congratulations!</h3>
                    <p>All transactions have been matched!</p>
                </div>
            ` : ''}
        </div>
    `;
    
    frappe.msgprint({
        title: __('Progress Tracker'),
        message: html,
        wide: true
    });
}

// ============ SMART SUGGESTIONS ============

function show_smart_suggestions(frm) {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.bank_reconciliation.bank_reconciliation.get_smart_suggestions',
        args: { docname: frm.doc.name },
        callback: function(r) {
            if (r.message) {
                display_suggestions(r.message, frm);
            }
        }
    });
}

function display_suggestions(suggestions, frm) {
    let html = `
        <div class="suggestions-panel">
            ${suggestions.map(sugg => `
                <div class="suggestion-card">
                    <div class="suggestion-type ${sugg.priority}">${sugg.type}</div>
                    <div style="font-weight: 600; margin-bottom: 8px;">${sugg.title}</div>
                    <div style="color: #6c757d; margin-bottom: 10px;">${sugg.description}</div>
                    ${sugg.action ? `
                        <button class="btn btn-sm btn-primary suggestion-action" 
                                data-action="${sugg.action}">
                            ${sugg.action_label}
                        </button>
                    ` : ''}
                </div>
            `).join('')}
        </div>
    `;
    
    let d = new frappe.ui.Dialog({
        title: __('💡 Smart Suggestions'),
        fields: [{
            fieldtype: 'HTML',
            options: html
        }],
        size: 'large'
    });
    
    d.show();
}

// ============ RECONCILIATION ASSISTANT ============

function show_reconciliation_assistant(frm) {
    let d = new frappe.ui.Dialog({
        title: __('🤖 Reconciliation Assistant'),
        size: 'large',
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'chat_container',
                options: `
                    <div id="chat-messages" style="height: 400px; overflow-y: auto; 
                         background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 15px;">
                    </div>
                `
            },
            {
                fieldtype: 'Section Break'
            },
            {
                fieldtype: 'Data',
                fieldname: 'user_message',
                label: __('Ask me anything'),
                placeholder: __('e.g., How many transactions are unmatched?')
            }
        ],
        primary_action_label: __('Send'),
        primary_action: function(values) {
            if (values.user_message) {
                process_assistant_query(values.user_message, frm, d);
                d.set_value('user_message', '');
            }
        }
    });
    
    // Welcome message
    add_assistant_message(d, "Hello! I'm your reconciliation assistant. I can help you with:\n\n" +
        "• Checking unmatched transactions\n" +
        "• Finding specific entries\n" +
        "• Explaining reconciliation status\n" +
        "• Running automated tasks\n\n" +
        "What would you like to know?", 'assistant');
    
    d.show();
}

function process_assistant_query(query, frm, dialog) {
    add_assistant_message(dialog, query, 'user');
    
    let response = generate_assistant_response(query, frm);
    
    setTimeout(() => {
        add_assistant_message(dialog, response, 'assistant');
    }, 500);
}

function generate_assistant_response(query, frm) {
    query = query.toLowerCase();
    
    // Unmatched count
    if (query.includes('unmatched') || query.includes('how many')) {
        let unmatched = (frm.doc.bank_account_entry || []).filter(r => r.rec === 0).length;
        return `You have ${unmatched} unmatched bank entries. Would you like me to run auto-matching to help reduce this number?`;
    }
    
    // Balance status
    if (query.includes('balance') || query.includes('difference')) {
        if (Math.abs(flt(frm.doc.balance_diff)) < 0.01) {
            return "Great news! Your accounts are balanced. The difference is NIL.";
        } else {
            return `There's a difference of ${format_currency(Math.abs(frm.doc.balance_diff), frm.doc.account_currency)}. ` +
                   `This could be due to unrecorded transactions. Check Direct Withdrawals and Lodgments tabs.`;
        }
    }
    
    // Progress
    if (query.includes('progress') || query.includes('status')) {
        let total = (frm.doc.bank_account_entry || []).length;
        let matched = (frm.doc.bank_account_entry || []).filter(r => r.rec === 1).length;
        let percentage = total > 0 ? (matched / total * 100).toFixed(1) : 0;
        
        return `You've matched ${matched} out of ${total} transactions (${percentage}%). ` +
               `${percentage < 50 ? 'Keep going!' : percentage < 90 ? 'Almost there!' : 'Excellent work!'}`;
    }
    
    // Help with matching
    if (query.includes('match') || query.includes('help')) {
        return "I can help you match transactions! Here are your options:\n\n" +
               "1. **Auto Match** - Uses AI to find matches automatically\n" +
               "2. **Manual Match** - Drag and drop to match manually\n" +
               "3. **Smart Suggestions** - Get hints on potential matches\n\n" +
               "Which would you like to try?";
    }
    
    // Default
    return "I'm not sure I understand. You can ask me about:\n" +
           "• Number of unmatched transactions\n" +
           "• Balance status\n" +
           "• Reconciliation progress\n" +
           "• How to match transactions";
}

function add_assistant_message(dialog, message, type) {
    let chat_container = dialog.$wrapper.find('#chat-messages');
    
    let message_html = `
        <div class="chat-message ${type}" style="margin-bottom: 15px; 
             ${type === 'user' ? 'text-align: right;' : ''}">
            <div style="display: inline-block; max-width: 70%; 
                 background: ${type === 'user' ? '#667eea' : 'white'}; 
                 color: ${type === 'user' ? 'white' : '#212529'};
                 padding: 12px 16px; border-radius: 18px; 
                 box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                 ${type === 'assistant' ? 'border: 1px solid #e9ecef;' : ''}">
                ${message.replace(/\n/g, '<br>')}
            </div>
            <div style="font-size: 8pt; color: #6c757d; margin-top: 5px;">
                ${frappe.datetime.now_time()}
            </div>
        </div>
    `;
    
    chat_container.append(message_html);
    chat_container.scrollTop(chat_container[0].scrollHeight);
}

// ============ UTILITY FUNCTIONS ============

function calculate_all_totals(frm) {
    let doc = frm.doc;
    
    let totals = {
        debit: 0,
        credit: 0,
        unpresented: 0,
        uncredited: 0,
        direct_withdrawal: 0,
        direct_lodgment: 0
    };
    
    (doc.bank_account_entry || []).forEach(row => {
        totals.debit += flt(row.debit_amount);
        totals.credit += flt(row.credit_amount);
    });
    
    (doc.unpresented_cheques || []).forEach(row => {
        totals.unpresented += flt(row.credit_amount);
    });
    
    (doc.uncredited_cheques || []).forEach(row => {
        totals.uncredited += flt(row.debit_amount);
    });
    
    (doc.direct_withdrawal || []).forEach(row => {
        totals.direct_withdrawal += flt(row.debit_amount);
    });
    
    (doc.direct_lodgment || []).forEach(row => {
        totals.direct_lodgment += flt(row.credit_amount);
    });
    
    frm.set_value('total_debit', totals.debit);
    frm.set_value('total_credit', totals.credit);
    frm.set_value('total_unpresented_cheque', totals.unpresented);
    frm.set_value('total_uncredited_cheque', totals.uncredited);
    frm.set_value('total_direct_withdrawal', totals.direct_withdrawal);
    frm.set_value('total_direct_lodgment', totals.direct_lodgment);
}

function calculate_balance_per_cash_book(frm) {
    let doc = frm.doc;

    let statement_ending_balance = flt(doc.statement_ending_balance);
    let total_unpresented_cheque = flt(doc.total_unpresented_cheque);
    let total_uncredited_cheque = flt(doc.total_uncredited_cheque);
    let total_direct_withdrawal = flt(doc.total_direct_withdrawal);
    let total_direct_lodgment = flt(doc.total_direct_lodgment);
    let cash_book_balance = flt(doc.cashbook_ending_balance);

    let balance_per_cb = 
        statement_ending_balance + 
        total_unpresented_cheque - 
        total_uncredited_cheque + 
        total_direct_withdrawal - 
        total_direct_lodgment;

    let balance_diff = cash_book_balance - balance_per_cb;

    frm.set_value("balance_per_cash_book", balance_per_cb);
    frm.set_value("balance_diff", balance_diff);

    if (Math.abs(balance_diff) < 0.01) {  // Allow for rounding errors
        frm.set_value("status", "Reconciled");
    } else {
        frm.set_value("status", "Not Reconciled");
    }

    frm.set_df_property('status', 'read_only', 1);
}

function get_unpresented_transactions(frm) {
    let doc = frm.doc;
    let bank_entries = doc.bank_account_entry || [];

    let entries_to_copy = bank_entries.filter(entry => {
        return entry.rec === 0 && flt(entry.credit_amount) !== 0;
    });

    if (entries_to_copy.length > 0) {
        let added = 0;
        entries_to_copy.forEach(bank_entry => {
            let existing = doc.unpresented_cheques.find(existing_entry => {
                return (
                    (existing_entry.voucher_no && existing_entry.voucher_no === bank_entry.voucher_no) ||
                    (existing_entry.cheque_no && existing_entry.cheque_no === bank_entry.cheque_no)
                );
            });

            if (!existing) {
                frm.add_child('unpresented_cheques', {
                    posting_date: bank_entry.posting_date,
                    cheque_no: bank_entry.cheque_no,
                    party: bank_entry.party,
                    debit_amount: bank_entry.debit_amount,
                    credit_amount: bank_entry.credit_amount,
                    account_currency: bank_entry.account_currency,
                    voucher_no: bank_entry.voucher_no,
                    remarks: bank_entry.remarks
                });
                added++;
            }
        });

        frm.refresh_field('unpresented_cheques');
        
        if (added > 0) {
            frappe.show_alert({
                message: __('Added {0} unpresented transactions', [added]),
                indicator: 'green'
            });
        } else {
            frappe.msgprint(__('All eligible entries already exist in Unpresented Cheques'));
        }
    } else {
        frappe.msgprint(__('No unreconciled credit entries found'));
    }
}

function get_uncredited_transactions(frm) {
    let doc = frm.doc;
    let bank_entries = doc.bank_account_entry || [];

    let entries_to_copy = bank_entries.filter(entry => {
        return entry.rec === 0 && flt(entry.debit_amount) !== 0;
    });

    if (entries_to_copy.length > 0) {
        let added = 0;
        entries_to_copy.forEach(bank_entry => {
            let existing = doc.uncredited_cheques.find(existing_entry => {
                return (
                    (existing_entry.voucher_no && existing_entry.voucher_no === bank_entry.voucher_no) ||
                    (existing_entry.cheque_no && existing_entry.cheque_no === bank_entry.cheque_no)
                );
            });

            if (!existing) {
                frm.add_child('uncredited_cheques', {
                    posting_date: bank_entry.posting_date,
                    cheque_no: bank_entry.cheque_no,
                    party: bank_entry.party,
                    debit_amount: bank_entry.debit_amount,
                    credit_amount: bank_entry.credit_amount,
                    account_currency: bank_entry.account_currency,
                    voucher_no: bank_entry.voucher_no,
                    remarks: bank_entry.remarks
                });
                added++;
            }
        });

        frm.refresh_field('uncredited_cheques');
        
        if (added > 0) {
            frappe.show_alert({
                message: __('Added {0} uncredited transactions', [added]),
                indicator: 'green'
            });
        } else {
            frappe.msgprint(__('All eligible entries already exist in Uncredited Cheques'));
        }
    } else {
        frappe.msgprint(__('No unreconciled debit entries found'));
    }
}

function get_direct_withdrawals(frm) {
    let doc = frm.doc;
    let statements = doc.bank_statement || [];

    let entries_to_copy = statements.filter(stmt => {
        return stmt.rec === 0 && flt(stmt.debit_amount) !== 0;
    });

    if (entries_to_copy.length > 0) {
        let added = 0;
        entries_to_copy.forEach(stmt => {
            let existing = doc.direct_withdrawal.find(e => e.voucher_no === stmt.voucher_no);

            if (!existing) {
                frm.add_child('direct_withdrawal', {
                    posting_date: stmt.posting_date,
                    cheque_no: stmt.cheque_no,
                    party: stmt.party,
                    debit_amount: stmt.debit_amount,
                    credit_amount: stmt.credit_amount,
                    account_currency: stmt.account_currency,
                    voucher_no: stmt.voucher_no,
                    remarks: stmt.remarks
                });
                added++;
            }
        });

        frm.refresh_field('direct_withdrawal');
        
        if (added > 0) {
            frappe.show_alert({
                message: __('Added {0} direct withdrawals', [added]),
                indicator: 'green'
            });
        } else {
            frappe.msgprint(__('All eligible entries already exist'));
        }
    } else {
        frappe.msgprint(__('No unreconciled debit statements found'));
    }
}

function get_direct_lodgments(frm) {
    let doc = frm.doc;
    let statements = doc.bank_statement || [];

    let entries_to_copy = statements.filter(stmt => {
        return stmt.rec === 0 && flt(stmt.credit_amount) !== 0;
    });

    if (entries_to_copy.length > 0) {
        let added = 0;
        entries_to_copy.forEach(stmt => {
            let existing = doc.direct_lodgment.find(e => e.voucher_no === stmt.voucher_no);

            if (!existing) {
                frm.add_child('direct_lodgment', {
                    posting_date: stmt.posting_date,
                    cheque_no: stmt.cheque_no,
                    party: stmt.party,
                    debit_amount: stmt.debit_amount,
                    credit_amount: stmt.credit_amount,
                    account_currency: stmt.account_currency,
                    voucher_no: stmt.voucher_no,
                    remarks: stmt.remarks
                });
                added++;
            }
        });

        frm.refresh_field('direct_lodgment');
        
        if (added > 0) {
            frappe.show_alert({
                message: __('Added {0} direct lodgments', [added]),
                indicator: 'green'
            });
        } else {
            frappe.msgprint(__('All eligible entries already exist'));
        }
    } else {
        frappe.msgprint(__('No unreconciled credit statements found'));
    }
}

function clear_all_tables(frm) {
    frm.clear_table('bank_account_entry');
    frm.clear_table('bank_statement');
    frm.clear_table('unpresented_cheques');
    frm.clear_table('uncredited_cheques');
    frm.clear_table('direct_withdrawal');
    frm.clear_table('direct_lodgment');

    frm.set_value("total_debit", 0);
    frm.set_value("total_credit", 0);
    frm.set_value("total_unpresented_cheque", 0);
    frm.set_value("total_uncredited_cheque", 0);
    frm.set_value("total_direct_withdrawal", 0);
    frm.set_value("total_direct_lodgment", 0);
    frm.set_value("balance_per_cash_book", 0);

    frm.refresh_fields();

    frappe.show_alert({
        message: __('All tables cleared'),
        indicator: 'orange'
    });
}

function export_unmatched_transactions(frm) {
    let unmatched_entries = (frm.doc.bank_account_entry || []).filter(r => r.rec === 0);
    let unmatched_statements = (frm.doc.bank_statement || []).filter(r => r.rec === 0);

    if (unmatched_entries.length === 0 && unmatched_statements.length === 0) {
        frappe.msgprint(__('No unmatched transactions to export'));
        return;
    }

    // Create CSV content
    let csv_content = "Type,Date,Party,Voucher No,Debit,Credit,Remarks\n";

    unmatched_entries.forEach(entry => {
        csv_content += `Bank Entry,${entry.posting_date},${entry.party || ''},${entry.voucher_no || ''},${entry.debit_amount || 0},${entry.credit_amount || 0},"${(entry.remarks || '').replace(/"/g, '""')}"\n`;
    });

    unmatched_statements.forEach(stmt => {
        csv_content += `Bank Statement,${stmt.posting_date},${stmt.party || ''},${stmt.voucher_no || ''},${stmt.debit_amount || 0},${stmt.credit_amount || 0},"${(stmt.remarks || '').replace(/"/g, '""')}"\n`;
    });

    // Download CSV
    let blob = new Blob([csv_content], { type: 'text/csv;charset=utf-8;' });
    let link = document.createElement("a");
    let url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", `unmatched_transactions_${frm.doc.name}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    frappe.show_alert({
        message: __('Exported {0} unmatched transactions', [unmatched_entries.length + unmatched_statements.length]),
        indicator: 'blue'
    });
}

function generate_reconciliation_report(frm) {
    frappe.set_route('query-report', 'Bank Reconciliation Report', {
        bank_reconciliation: frm.doc.name
    });
}

function add_quick_filters_to_tables(frm) {
    // Quick filters for bank_account_entry and bank_statement
    ['bank_account_entry', 'bank_statement'].forEach(tablename => {
        if (frm.fields_dict[tablename]) {
            let wrapper = frm.fields_dict[tablename].grid.wrapper;
            
            // Check if filter already added
            if (wrapper.find('.quick-filter-bar').length > 0) return;

            let filter_html = `
                <div class="quick-filter-bar">
                    <span class="filter-badge" data-filter="all">All</span>
                    <span class="filter-badge" data-filter="matched">Matched</span>
                    <span class="filter-badge" data-filter="unmatched">Unmatched</span>
                    <span class="filter-badge" data-filter="debit">Debit Only</span>
                    <span class="filter-badge" data-filter="credit">Credit Only</span>
                    <input type="text" class="form-control form-control-sm" 
                           style="display:inline-block; width: 200px; margin-left: 10px;" 
                           placeholder="Search...">
                </div>
            `;

            wrapper.find('.grid-heading-row').after(filter_html);

            // Filter click handlers
            wrapper.find('.filter-badge').click(function() {
                let filter = $(this).data('filter');
                $(this).siblings('.filter-badge').removeClass('active');
                $(this).addClass('active');

                wrapper.find('.grid-row').each(function(i) {
                    let row_data = frm.doc[tablename][i];
                    let show = true;

                    if (filter === 'matched') {
                        show = row_data && row_data.rec === 1;
                    } else if (filter === 'unmatched') {
                        show = row_data && row_data.rec === 0;
                    } else if (filter === 'debit') {
                        show = row_data && flt(row_data.debit_amount) > 0;
                    } else if (filter === 'credit') {
                        show = row_data && flt(row_data.credit_amount) > 0;
                    }

                    $(this).toggle(show);
                });
            });

            // Search handler
            wrapper.find('input[type="text"]').on('keyup', function() {
                let search = $(this).val().toLowerCase();
                wrapper.find('.grid-row').each(function(i) {
                    let row_data = frm.doc[tablename][i];
                    let text = JSON.stringify(row_data).toLowerCase();
                    $(this).toggle(text.includes(search));
                });
            });
        }
    });
}

function setup_keyboard_shortcuts(frm) {
    // Remove existing handlers first
    $(document).off('keydown.bank_reco');
    
    // Ctrl/Cmd + M for Match
    $(document).on('keydown.bank_reco', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'm') {
            e.preventDefault();
            frm.trigger('match');
        }
    });

    // Ctrl/Cmd + I for Import
    $(document).on('keydown.bank_reco', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'i') {
            e.preventDefault();
            show_import_dialog(frm);
        }
    });

    // Ctrl/Cmd + P for Print
    $(document).on('keydown.bank_reco', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'p') {
            e.preventDefault();
            frappe.set_route('print', frm.doctype, frm.doc.name, 'Bank Reconciliation Statement');
        }
    });
}



//==========================================================


// ============================================================
// USER MANUAL - STANDALONE MODULE
// Paste this at the end of bank_reconciliation.js
// ============================================================

frappe.ui.form.on('Bank Reconciliation', {
    onload_post_render: function(frm) {
        // Populate user manual HTML field on form load
        if (frm.fields_dict.user_manual_html) {
            render_user_manual(frm);
        }
    }
});

function render_user_manual(frm) {
    // Get the complete manual HTML
    let manual_html = get_complete_manual_html();
    
    // Set the HTML in the field
    frm.set_df_property('user_manual_html', 'options', manual_html);
    
    // Add interactive functionality after a short delay
    setTimeout(function() {
        setup_manual_interactivity(frm);
    }, 500);
}

function setup_manual_interactivity(frm) {
    let $wrapper = frm.fields_dict.user_manual_html.$wrapper;
    
    if (!$wrapper.length) return;
    
    // Navigation click handlers
    $wrapper.find('.manual-nav-item').click(function() {
        let section = $(this).data('section');
        $wrapper.find('.manual-nav-item').removeClass('active');
        $(this).addClass('active');
        $wrapper.find('.manual-section').hide();
        $wrapper.find(`#${section}`).show();
        $wrapper.find('.manual-content').scrollTop(0);
    });
    
    // Search functionality
    $wrapper.find('#manual-search').on('keyup', function() {
        let search = $(this).val().toLowerCase();
        if (search === '') {
            $wrapper.find('.manual-section').show();
        } else {
            $wrapper.find('.manual-section').each(function() {
                let text = $(this).text().toLowerCase();
                $(this).toggle(text.includes(search));
            });
        }
    });
}

function get_complete_manual_html() {
    return `
        <style>
            .manual-container {
                display: flex;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                overflow: hidden;
                background: white;
                min-height: 600px;
                max-height: 800px;
            }
            
            .manual-sidebar {
                width: 250px;
                background: #f8f9fa;
                padding: 20px;
                overflow-y: auto;
                border-right: 2px solid #dee2e6;
                flex-shrink: 0;
            }
            
            .manual-content {
                flex: 1;
                padding: 30px;
                overflow-y: auto;
                background: white;
            }
            
            .manual-nav-item {
                padding: 10px 15px;
                margin-bottom: 5px;
                cursor: pointer;
                border-radius: 5px;
                transition: all 0.2s;
                font-size: 10pt;
                user-select: none;
            }
            
            .manual-nav-item:hover {
                background: #e9ecef;
            }
            
            .manual-nav-item.active {
                background: #667eea;
                color: white;
                font-weight: 600;
            }
            
            .manual-section {
                margin-bottom: 40px;
            }
            
            .manual-section h2 {
                color: #667eea;
                border-bottom: 3px solid #667eea;
                padding-bottom: 10px;
                margin-bottom: 20px;
                font-size: 24pt;
            }
            
            .manual-section h3 {
                color: #495057;
                margin-top: 25px;
                margin-bottom: 15px;
                font-size: 18pt;
            }
            
            .manual-section h4 {
                color: #6c757d;
                margin-top: 20px;
                margin-bottom: 10px;
                font-size: 14pt;
            }
            
            .manual-section p {
                line-height: 1.6;
                color: #212529;
            }
            
            .manual-section ul, .manual-section ol {
                line-height: 1.8;
                color: #212529;
            }
            
            .step-box {
                background: #f8f9fa;
                border-left: 4px solid #667eea;
                padding: 15px;
                margin: 15px 0;
                border-radius: 5px;
            }
            
            .step-number {
                display: inline-block;
                width: 30px;
                height: 30px;
                background: #667eea;
                color: white;
                border-radius: 50%;
                text-align: center;
                line-height: 30px;
                font-weight: bold;
                margin-right: 10px;
            }
            
            .info-box {
                background: #d1ecf1;
                border-left: 4px solid #17a2b8;
                padding: 15px;
                margin: 15px 0;
                border-radius: 5px;
            }
            
            .warning-box {
                background: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 15px;
                margin: 15px 0;
                border-radius: 5px;
            }
            
            .tip-box {
                background: #d4edda;
                border-left: 4px solid #28a745;
                padding: 15px;
                margin: 15px 0;
                border-radius: 5px;
            }
            
            .feature-grid {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
                margin: 20px 0;
            }
            
            .feature-card {
                background: white;
                border: 2px solid #e9ecef;
                padding: 15px;
                border-radius: 8px;
                transition: all 0.2s;
            }
            
            .feature-card:hover {
                border-color: #667eea;
                box-shadow: 0 3px 10px rgba(0,0,0,0.1);
            }
            
            .feature-icon {
                font-size: 24pt;
                margin-bottom: 10px;
            }
            
            .manual-section code {
                background: #f8f9fa;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                color: #e83e8c;
                font-size: 10pt;
            }
            
            .shortcut-key {
                display: inline-block;
                background: #343a40;
                color: white;
                padding: 3px 8px;
                border-radius: 3px;
                font-family: monospace;
                font-size: 9pt;
            }
            
            .manual-search {
                width: 100%;
                padding: 10px;
                border: 2px solid #dee2e6;
                border-radius: 5px;
                margin-bottom: 20px;
                font-size: 10pt;
            }
            
            .manual-search:focus {
                outline: none;
                border-color: #667eea;
            }
            
            table.manual-table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                font-size: 10pt;
            }
            
            table.manual-table th {
                background: #667eea;
                color: white;
                padding: 10px;
                text-align: left;
            }
            
            table.manual-table td {
                padding: 10px;
                border: 1px solid #dee2e6;
            }
            
            table.manual-table tr:nth-child(even) {
                background: #f8f9fa;
            }
            
            .checklist {
                list-style: none;
                padding-left: 0;
            }
            
            .checklist li {
                padding: 8px 0;
                padding-left: 30px;
                position: relative;
            }
            
            .checklist li:before {
                content: "✓";
                position: absolute;
                left: 0;
                color: #28a745;
                font-weight: bold;
                font-size: 14pt;
            }
            
            .manual-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                text-align: center;
                margin: -30px -30px 30px -30px;
            }
            
            .manual-header h1 {
                margin: 0;
                font-size: 28pt;
            }
            
            .manual-header p {
                margin: 10px 0 0 0;
                opacity: 0.9;
            }
            
            /* Scrollbar styling */
            .manual-sidebar::-webkit-scrollbar,
            .manual-content::-webkit-scrollbar {
                width: 8px;
            }
            
            .manual-sidebar::-webkit-scrollbar-track,
            .manual-content::-webkit-scrollbar-track {
                background: #f1f1f1;
            }
            
            .manual-sidebar::-webkit-scrollbar-thumb,
            .manual-content::-webkit-scrollbar-thumb {
                background: #888;
                border-radius: 4px;
            }
            
            .manual-sidebar::-webkit-scrollbar-thumb:hover,
            .manual-content::-webkit-scrollbar-thumb:hover {
                background: #555;
            }
        </style>
        
        <div class="manual-container">
            <!-- SIDEBAR NAVIGATION -->
            <div class="manual-sidebar">
                <input type="text" id="manual-search" class="manual-search" placeholder="🔍 Search manual...">
                
                <div class="manual-nav-item active" data-section="section-intro">
                    🏠 Introduction
                </div>
                <div class="manual-nav-item" data-section="section-getting-started">
                    🚀 Getting Started
                </div>
                <div class="manual-nav-item" data-section="section-features">
                    ⭐ Key Features
                </div>
                <div class="manual-nav-item" data-section="section-import">
                    📥 Import Statement
                </div>
                <div class="manual-nav-item" data-section="section-matching">
                    🎯 Transaction Matching
                </div>
                <div class="manual-nav-item" data-section="section-reconciliation">
                    💰 Reconciliation Process
                </div>
                <div class="manual-nav-item" data-section="section-transactions">
                    📝 Creating Transactions
                </div>
                <div class="manual-nav-item" data-section="section-reports">
                    📊 Reports & Printing
                </div>
                <div class="manual-nav-item" data-section="section-best-practices">
                    ⚡ Best Practices
                </div>
                <div class="manual-nav-item" data-section="section-troubleshooting">
                    🔧 Troubleshooting
                </div>
                <div class="manual-nav-item" data-section="section-faq">
                    ❓ FAQ
                </div>
            </div>
            
            <!-- MAIN CONTENT -->
            <div class="manual-content">
                <div class="manual-header">
                    <h1>📚 Bank Reconciliation</h1>
                    <p>Complete User Manual & Guide</p>
                </div>
            
                <!-- ============ INTRODUCTION ============ -->
                <div class="manual-section" id="section-intro">
                    <h2>🏠 Introduction</h2>
                    
                    <h3>What is Bank Reconciliation?</h3>
                    <p>
                        Bank Reconciliation is the process of matching the transactions in your company's accounting books 
                        (cashbook) with the transactions that appear on your bank statement. This ensures accuracy and 
                        helps identify any discrepancies.
                    </p>
                    
                    <h3>Why is it Important?</h3>
                    <div class="feature-grid">
                        <div class="feature-card">
                            <div class="feature-icon">✅</div>
                            <h4>Accuracy</h4>
                            <p>Ensures your financial records match bank records</p>
                        </div>
                        <div class="feature-card">
                            <div class="feature-icon">🔍</div>
                            <h4>Error Detection</h4>
                            <p>Identifies mistakes, missing entries, or fraud</p>
                        </div>
                        <div class="feature-card">
                            <div class="feature-icon">💼</div>
                            <h4>Cash Management</h4>
                            <p>Provides accurate cash position for decisions</p>
                        </div>
                        <div class="feature-card">
                            <div class="feature-icon">📈</div>
                            <h4>Audit Compliance</h4>
                            <p>Required for financial audits and reporting</p>
                        </div>
                    </div>
                    
                    <h3>System Overview</h3>
                    <p>
                        This Bank Reconciliation System is a world-class tool that automates and simplifies the 
                        reconciliation process. It includes:
                    </p>
                    <ul class="checklist">
                        <li>Automated bank statement import from CSV/Excel files</li>
                        <li>AI-powered intelligent transaction matching</li>
                        <li>Manual matching capabilities</li>
                        <li>Automatic creation of adjusting entries</li>
                        <li>Professional reconciliation reports</li>
                        <li>Real-time progress tracking</li>
                        <li>Smart suggestions and assistance</li>
                    </ul>
                </div>
                
                <!-- ============ GETTING STARTED ============ -->
                <div class="manual-section" id="section-getting-started" style="display: none;">
                    <h2>🚀 Getting Started</h2>
                    
                    <h3>Creating a New Bank Reconciliation</h3>
                    
                    <div class="step-box">
                        <span class="step-number">1</span>
                        <strong>Navigate to Bank Reconciliation</strong>
                        <p>Go to: <code>Accounting → Bank Reconciliation → New</code></p>
                    </div>
                    
                    <div class="step-box">
                        <span class="step-number">2</span>
                        <strong>Fill in Basic Details</strong>
                        <ul>
                            <li><strong>Company:</strong> Select your company</li>
                            <li><strong>Bank Account:</strong> Select the bank account to reconcile</li>
                            <li><strong>From Date:</strong> Start date of reconciliation period</li>
                            <li><strong>To Date:</strong> End date of reconciliation period</li>
                        </ul>
                    </div>
                    
                    <div class="step-box">
                        <span class="step-number">3</span>
                        <strong>Enter Statement Balance</strong>
                        <p>
                            Enter the <strong>Statement Ending Balance</strong> from your bank statement. 
                            This is the closing balance shown on the statement for the period.
                        </p>
                    </div>
                    
                    <div class="step-box">
                        <span class="step-number">4</span>
                        <strong>Get Bank Entries</strong>
                        <p>
                            Click <code>Actions → 📊 Get Bank Entries</code> to automatically load all 
                            transactions from your GL Entry for the selected period and bank account.
                        </p>
                    </div>
                    
                    <div class="info-box">
                        <strong>💡 Info:</strong> The system will automatically calculate the Cashbook Ending Balance 
                        from your GL Entry records. This should match your Statement Ending Balance after reconciliation.
                    </div>
                    
                    <div class="tip-box">
                        <strong>✨ Tip:</strong> Always reconcile at least monthly. More frequent reconciliations 
                        (weekly or even daily) make the process easier and help catch errors quickly.
                    </div>
                </div>
                
                <!-- ============ KEY FEATURES ============ -->
                <div class="manual-section" id="section-features" style="display: none;">
                    <h2>⭐ Key Features</h2>
                    
                    <h3>1. Smart Import</h3>
                    <p>Import bank statements directly from CSV or Excel files with automatic column detection.</p>
                    
                    <h3>2. Intelligent Matching</h3>
                    <p>AI-powered matching engine using:</p>
                    <ul>
                        <li><strong>Amount Matching:</strong> Finds transactions with matching amounts</li>
                        <li><strong>Date Proximity:</strong> Considers transactions within a date range</li>
                        <li><strong>Fuzzy Party Matching:</strong> Matches similar party names</li>
                        <li><strong>Cross Matching:</strong> Match debits with credits</li>
                        <li><strong>Confidence Scoring:</strong> 60-100% confidence levels</li>
                    </ul>
                    
                    <h3>3. Progress Tracking</h3>
                    <p>Real-time dashboards showing:</p>
                    <ul>
                        <li>Overall progress percentage</li>
                        <li>Matched vs unmatched transactions</li>
                        <li>Balance status indicators</li>
                    </ul>
                    
                    <h3>4. Smart Suggestions</h3>
                    <p>AI provides alerts for:</p>
                    <ul>
                        <li>Large unmatched transactions</li>
                        <li>Old unmatched items (>30 days)</li>
                        <li>Potential duplicates</li>
                        <li>Low match rates</li>
                        <li>Balance mismatches</li>
                    </ul>
                </div>
                
                <!-- ============ IMPORT STATEMENT ============ -->
                <div class="manual-section" id="section-import" style="display: none;">
                    <h2>📥 Import Bank Statement</h2>
                    
                    <div class="info-box">
                        <strong>✅ Supported Formats:</strong>
                        <ul>
                            <li>CSV (.csv)</li>
                            <li>Excel (.xlsx, .xls)</li>
                        </ul>
                    </div>
                    
                    <h3>Step-by-Step Import</h3>
                    
                    <div class="step-box">
                        <span class="step-number">1</span>
                        <strong>Open Import Dialog</strong>
                        <p>Click <code>Actions → 📥 Import Statement</code></p>
                    </div>
                    
                    <div class="step-box">
                        <span class="step-number">2</span>
                        <strong>Upload File</strong>
                        <p>Select your bank statement file. The system will preview it automatically.</p>
                    </div>
                    
                    <div class="step-box">
                        <span class="step-number">3</span>
                        <strong>Map Columns</strong>
                        <p>The system auto-detects columns, but verify:</p>
                        <ul>
                            <li>Date Column</li>
                            <li>Party/Description Column</li>
                            <li>Debit Column</li>
                            <li>Credit Column</li>
                        </ul>
                    </div>
                    
                    <div class="step-box">
                        <span class="step-number">4</span>
                        <strong>Import</strong>
                        <p>Click Import button. System shows confirmation with count.</p>
                    </div>
                    
                    <div class="tip-box">
                        <strong>💡 Pro Tip:</strong> System remembers your column mappings for future imports!
                    </div>
                </div>
                
                <!-- ============ MATCHING ============ -->
                <div class="manual-section" id="section-matching" style="display: none;">
                    <h2>🎯 Transaction Matching</h2>
                    
                    <h3>Automatic Matching</h3>
                    
                    <div class="step-box">
                        <span class="step-number">1</span>
                        <strong>Click Match Button</strong>
                        <p>Or press <span class="shortcut-key">Ctrl+M</span></p>
                    </div>
                    
                    <div class="step-box">
                        <span class="step-number">2</span>
                        <strong>Configure Parameters</strong>
                        <ul>
                            <li><strong>Amount Tolerance:</strong> Default 1.00</li>
                            <li><strong>Date Range:</strong> Default ±5 days</li>
                            <li><strong>Minimum Confidence:</strong> Default 60%</li>
                        </ul>
                    </div>
                    
                    <div class="step-box">
                        <span class="step-number">3</span>
                        <strong>Review Results</strong>
                        <p>System shows auto-matched, suggested, and unmatched items.</p>
                    </div>
                    
                    <div class="info-box">
                        <strong>🎨 Confidence Levels:</strong>
                        <ul>
                            <li><strong>Green (80-100%):</strong> High confidence</li>
                            <li><strong>Yellow (60-79%):</strong> Review carefully</li>
                            <li><strong>Red (<60%):</strong> Verify thoroughly</li>
                        </ul>
                    </div>
                    
                    <h3>Manual Matching</h3>
                    <p>For items not auto-matched, use <code>Actions → 🔗 Manual Match</code></p>
                    <ul>
                        <li>Select one item from each side</li>
                        <li>Click Match button in center</li>
                        <li>Repeat for other transactions</li>
                        <li>Save when complete</li>
                    </ul>
                </div>
                
                <!-- ============ RECONCILIATION ============ -->
                <div class="manual-section" id="section-reconciliation" style="display: none;">
                    <h2>💰 Reconciliation Process</h2>
                    
                    <h3>Understanding Reconciling Items</h3>
                    
                    <h4>1. Unpresented Cheques</h4>
                    <p>Cheques issued but not yet cashed by recipients.</p>
                    
                    <h4>2. Uncredited Cheques</h4>
                    <p>Deposits recorded but not yet processed by bank.</p>
                    
                    <h4>3. Direct Withdrawals</h4>
                    <p>Bank charges, fees not yet in your books.</p>
                    
                    <h4>4. Direct Lodgments</h4>
                    <p>Interest, deposits not yet in your books.</p>
                    
                    <h3>Getting Reconciling Items</h3>
                    
                    <div class="step-box">
                        <strong>Click these buttons:</strong>
                        <ul>
                            <li><code>Get Unpre</code> - Unpresented Cheques</li>
                            <li><code>Get Uncre</code> - Uncredited Cheques</li>
                            <li><code>Get DW</code> - Direct Withdrawals</li>
                            <li><code>Get DL</code> - Direct Lodgments</li>
                        </ul>
                    </div>
                    
                    <div class="info-box">
                        <strong>📐 Reconciliation Formula:</strong>
                        <p style="font-family: monospace; background: white; padding: 10px; margin-top: 10px; border-radius: 5px;">
                            Statement Balance<br>
                            + Unpresented Cheques<br>
                            - Uncredited Cheques<br>
                            + Direct Withdrawals<br>
                            - Direct Lodgments<br>
                            = Calculated Cash Book Balance
                        </p>
                    </div>
                    
                    <h3>Achieving Balance</h3>
                    <ul>
                        <li><strong>₦0.00:</strong> 🎉 Perfect! Balanced.</li>
                        <li><strong>< ₦1:</strong> Acceptable rounding difference</li>
                        <li><strong>Larger:</strong> Review for missing items</li>
                    </ul>
                </div>
                
                <!-- ============ TRANSACTIONS ============ -->
                <div class="manual-section" id="section-transactions" style="display: none;">
                    <h2>📝 Creating Transactions</h2>
                    
                    <h3>Why Create Transactions?</h3>
                    <p>
                        Direct Withdrawals and Lodgments represent items on bank statement 
                        not yet in your books. Create transactions to update your records.
                    </p>
                    
                    <h3>Automatic Creation</h3>
                    
                    <div class="step-box">
                        <span class="step-number">1</span>
                        <strong>Review Items</strong>
                        <p>Check Direct Withdrawals and Lodgments tables</p>
                    </div>
                    
                    <div class="step-box">
                        <span class="step-number">2</span>
                        <strong>Click Create Entries</strong>
                        <p><code>Actions → 💰 Create Entries</code></p>
                    </div>
                    
                    <div class="step-box">
                        <span class="step-number">3</span>
                        <strong>System Creates</strong>
                        <ul>
                            <li>Payments for Direct Withdrawals</li>
                            <li>Receipts for Direct Lodgments</li>
                        </ul>
                    </div>
                    
                    <div class="step-box">
                        <span class="step-number">4</span>
                        <strong>Review & Submit</strong>
                        <p>Transactions created in Draft. Review and submit to post to GL.</p>
                    </div>
                    
                    <div class="tip-box">
                        <strong>💡 Best Practice:</strong> Always review before submitting!
                    </div>
                </div>
                
                <!-- ============ REPORTS ============ -->
                <div class="manual-section" id="section-reports" style="display: none;">
                    <h2>📊 Reports & Printing</h2>
                    
                    <h3>Printing Statement</h3>
                    
                    <div class="step-box">
                        <span class="step-number">1</span>
                        <strong>Click Print</strong>
                        <p><code>Actions → 🖨️ Print</code> or <span class="shortcut-key">Ctrl+P</span></p>
                    </div>
                    
                    <div class="step-box">
                        <span class="step-number">2</span>
                        <strong>Review Preview</strong>
                        <p>Professional format with executive summary and details</p>
                    </div>
                    
                    <div class="step-box">
                        <span class="step-number">3</span>
                        <strong>Print or Save PDF</strong>
                        <p>Use browser's print function</p>
                    </div>
                    
                    <h3>Export Unmatched</h3>
                    <p>Click <code>Actions → 📤 Export</code> to download CSV of unmatched transactions.</p>
                </div>
                
                <!-- ============ BEST PRACTICES ============ -->
                <div class="manual-section" id="section-best-practices" style="display: none;">
                    <h2>⚡ Best Practices</h2>
                    
                    <h3>Frequency</h3>
                    <ul class="checklist">
                        <li>Reconcile at least monthly</li>
                        <li>Weekly for high-volume accounts</li>
                        <li>Daily for critical accounts</li>
                        <li>Don't wait until year-end</li>
                    </ul>
                    
                    <h3>During Reconciliation</h3>
                    <ul class="checklist">
                        <li>Start with auto-matching</li>
                        <li>Review suggested matches carefully</li>
                        <li>Use manual matching for remaining</li>
                        <li>Investigate large unmatched items</li>
                        <li>Don't ignore small differences</li>
                    </ul>
                    
                    <h3>Quality Control</h3>
                    <ul class="checklist">
                        <li>Use Duplicate Checker</li>
                        <li>Review Smart Suggestions</li>
                        <li>Aim for 95%+ match rate</li>
                        <li>Print for records</li>
                        <li>Have someone else review</li>
                    </ul>
                </div>
                
                <!-- ============ TROUBLESHOOTING ============ -->
                <div class="manual-section" id="section-troubleshooting" style="display: none;">
                    <h2>🔧 Troubleshooting</h2>
                    
                    <h3>Balance Won't Reconcile</h3>
                    <ul>
                        <li>Verify Statement Ending Balance</li>
                        <li>Check all GL entries loaded</li>
                        <li>Look for unmatched transactions</li>
                        <li>Use Duplicate Checker</li>
                        <li>Verify reconciling items</li>
                    </ul>
                    
                    <h3>Import Issues</h3>
                    <ul>
                        <li>Check file format (CSV/Excel only)</li>
                        <li>Verify column mappings</li>
                        <li>Ensure proper date format</li>
                        <li>Remove currency symbols</li>
                    </ul>
                    
                    <h3>No Matches Found</h3>
                    <ul>
                        <li>Increase Amount Tolerance</li>
                        <li>Increase Date Range</li>
                        <li>Enable Cross Matching</li>
                        <li>Lower Confidence threshold</li>
                        <li>Try manual matching</li>
                    </ul>
                    
                    <div class="tip-box">
                        <strong>💡 Need Help?</strong> Use the Assistant button or check FAQ section!
                    </div>
                </div>
                
                <!-- ============ FAQ ============ -->
                <div class="manual-section" id="section-faq" style="display: none;">
                    <h2>❓ Frequently Asked Questions</h2>
                    
                    <div class="step-box">
                        <strong>Q: How often should I reconcile?</strong>
                        <p>A: Monthly minimum, weekly recommended, daily ideal for critical accounts.</p>
                    </div>
                    
                    <div class="step-box">
                        <strong>Q: What if balances never match exactly?</strong>
                        <p>A: Normal! The reconciliation process identifies and documents the differences.</p>
                    </div>
                    
                    <div class="step-box">
                        <strong>Q: Can I reconcile multiple accounts?</strong>
                        <p>A: Yes! Create separate reconciliation for each account.</p>
                    </div>
                    
                    <div class="step-box">
                        <strong>Q: What formats can I import?</strong>
                        <p>A: CSV and Excel (.xlsx, .xls) files.</p>
                    </div>
                    
                    <div class="step-box">
                        <strong>Q: How does intelligent matching work?</strong>
                        <p>A: Uses AI algorithms considering amount, date, party name, and other factors.</p>
                    </div>
                    
                    <div class="step-box">
                        <strong>Q: Can I undo a match?</strong>
                        <p>A: Yes! Uncheck the "Rec" checkbox on matched transactions.</p>
                    </div>
                    
                    <div class="step-box">
                        <strong>Q: Why transactions created in Draft?</strong>
                        <p>A: For safety! Review and edit before submitting to GL.</p>
                    </div>
                </div>
                
            </div>
        </div>
    `;
}

// ============================================================
// END OF USER MANUAL MODULE
// ============================================================