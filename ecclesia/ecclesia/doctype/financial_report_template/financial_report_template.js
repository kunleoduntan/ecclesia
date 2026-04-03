// Copyright (c) 2026, Ecclesia and contributors
// For license information, please see license.txt

frappe.ui.form.on('Financial Report Template', {
    refresh: function(frm) {
        // Add custom buttons
        if (!frm.is_new()) {
            // Clone template button
            frm.add_custom_button(__('Clone Template'), function() {
                frappe.prompt([
                    {
                        'fieldname': 'new_name',
                        'fieldtype': 'Data',
                        'label': 'New Template Name',
                        'reqd': 1,
                        'description': 'Enter name for the cloned template'
                    }
                ],
                function(values) {
                    frappe.call({
                        method: 'frappe.client.clone_doc',
                        args: {
                            doctype: 'Financial Report Template',
                            name: frm.doc.name
                        },
                        callback: function(r) {
                            if (r.message) {
                                let new_doc = r.message;
                                new_doc.template_name = values.new_name;
                                new_doc.is_default = 0;
                                
                                frappe.call({
                                    method: 'frappe.client.insert',
                                    args: {
                                        doc: new_doc
                                    },
                                    callback: function(r) {
                                        if (r.message) {
                                            frappe.show_alert({
                                                message: __('Template cloned successfully'),
                                                indicator: 'green'
                                            });
                                            frappe.set_route('Form', 'Financial Report Template', r.message.name);
                                        }
                                    }
                                });
                            }
                        }
                    });
                },
                __('Clone Template'),
                __('Clone')
                );
            }, __('Actions'));
            
            // Preview report button
            frm.add_custom_button(__('Preview Report'), function() {
                frappe.set_route('query-report', 'Financial Report - Template Based', {
                    'template': frm.doc.name
                });
            }, __('Actions'));
            
            // Export template button (for backup/sharing)
            frm.add_custom_button(__('Export Template JSON'), function() {
                frappe.call({
                    method: 'frappe.client.get',
                    args: {
                        doctype: 'Financial Report Template',
                        name: frm.doc.name
                    },
                    callback: function(r) {
                        if (r.message) {
                            let json_str = JSON.stringify(r.message, null, 2);
                            let blob = new Blob([json_str], {type: 'application/json'});
                            let url = URL.createObjectURL(blob);
                            let a = document.createElement('a');
                            a.href = url;
                            a.download = frm.doc.name.replace(/ /g, '_') + '.json';
                            a.click();
                            
                            frappe.show_alert({
                                message: __('Template exported successfully'),
                                indicator: 'green'
                            });
                        }
                    }
                });
            }, __('Actions'));
        }
        
        // Set default colors if new
        if (frm.is_new()) {
            frm.set_value('excel_header_color', '#4472C4');
            frm.set_value('excel_total_row_color', '#E7E6E6');
            frm.set_value('excel_subtotal_color', '#F2F2F2');
            frm.set_value('excel_header_row', '#D9E1F2');
            frm.set_value('negative_values_color', '#FF0000');
            frm.set_value('decimal_places', 2);
            frm.set_value('variance_threshold_highlight', 10);
        }
        
        // Show line count
        if (frm.doc.report_lines && frm.doc.report_lines.length > 0) {
            frm.dashboard.add_comment(__('Total Lines: {0}', [frm.doc.report_lines.length]), 'blue', true);
        }
        
        // Validate template on save
        frm.trigger('validate_template');
    },
    
    is_default: function(frm) {
        // If setting as default, warn about other defaults
        if (frm.doc.is_default && frm.doc.report_type) {
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Financial Report Template',
                    filters: {
                        'report_type': frm.doc.report_type,
                        'is_default': 1,
                        'name': ['!=', frm.doc.name]
                    },
                    fields: ['name']
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        frappe.msgprint({
                            title: __('Warning'),
                            indicator: 'orange',
                            message: __('There is already a default template for {0}. Setting this as default will unset the other template.', [frm.doc.report_type])
                        });
                    }
                }
            });
        }
    },
    
    validate_template: function(frm) {
        // Basic validation
        if (!frm.doc.report_lines || frm.doc.report_lines.length === 0) {
            frappe.msgprint({
                title: __('Warning'),
                indicator: 'orange',
                message: __('Template has no report lines. Add lines to make this template functional.')
            });
            return;
        }
        
        // Check for duplicate line numbers
        let line_numbers = {};
        let duplicates = [];
        
        frm.doc.report_lines.forEach(function(line) {
            if (line_numbers[line.line_number]) {
                duplicates.push(line.line_number);
            }
            line_numbers[line.line_number] = true;
        });
        
        if (duplicates.length > 0) {
            frappe.msgprint({
                title: __('Warning'),
                indicator: 'red',
                message: __('Duplicate line numbers found: {0}. Please use unique line numbers.', [duplicates.join(', ')])
            });
        }
        
        // Check for line codes in formulas that don't exist
        let line_codes = {};
        frm.doc.report_lines.forEach(function(line) {
            if (line.line_code) {
                line_codes[line.line_code] = true;
            }
        });
        
        frm.doc.report_lines.forEach(function(line) {
            if (line.line_type === 'Calculated' && line.calculation_formula) {
                let formula = line.calculation_formula;
                let tokens = formula.match(/\b[A-Z_][A-Z0-9_]*\b/g) || [];
                
                tokens.forEach(function(token) {
                    if (!line_codes[token]) {
                        frappe.msgprint({
                            title: __('Warning'),
                            indicator: 'orange',
                            message: __('Line "{0}" references undefined code "{1}" in formula', [line.line_label, token])
                        });
                    }
                });
            }
        });
    }
});

// Child table: Report Lines
frappe.ui.form.on('Financial Report Line', {
    line_type: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        // Clear fields based on type
        if (row.line_type === 'Blank Line' || row.line_type === 'Header') {
            frappe.model.set_value(cdt, cdn, 'account_mapping_method', '');
            frappe.model.set_value(cdt, cdn, 'calculation_formula', '');
        }
        
        // Set defaults for calculated lines
        if (row.line_type === 'Calculated') {
            frappe.model.set_value(cdt, cdn, 'is_bold', 1);
        }
        
        // Refresh form to show/hide fields
        frm.refresh_field('report_lines');
    },
    
    line_number: function(frm, cdt, cdn) {
        // Auto-sort lines by line number
        frm.doc.report_lines.sort((a, b) => (a.line_number || 0) - (b.line_number || 0));
        frm.refresh_field('report_lines');
    },
    
    line_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        // Convert to uppercase automatically
        if (row.line_code) {
            frappe.model.set_value(cdt, cdn, 'line_code', row.line_code.toUpperCase());
        }
    },
    
    calculation_formula: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        if (row.calculation_formula) {
            // Extract line codes from formula
            let tokens = row.calculation_formula.match(/\b[A-Z_][A-Z0-9_]*\b/g) || [];
            
            // Build list of available codes
            let available_codes = [];
            frm.doc.report_lines.forEach(function(line) {
                if (line.line_code && line.line_number < row.line_number) {
                    available_codes.push(line.line_code);
                }
            });
            
            // Check for undefined codes
            let undefined_codes = [];
            tokens.forEach(function(token) {
                if (!available_codes.includes(token)) {
                    undefined_codes.push(token);
                }
            });
            
            if (undefined_codes.length > 0) {
                frappe.msgprint({
                    title: __('Warning'),
                    indicator: 'orange',
                    message: __('Formula references undefined codes: {0}<br><br>Available codes: {1}', 
                        [undefined_codes.join(', '), available_codes.join(', ')])
                });
            }
        }
    },
    
    is_total_row: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        // If total row, make it bold
        if (row.is_total_row) {
            frappe.model.set_value(cdt, cdn, 'is_bold', 1);
            frappe.model.set_value(cdt, cdn, 'is_subtotal_row', 0);
        }
    },
    
    is_subtotal_row: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        // If subtotal row, make it bold and unset total row
        if (row.is_subtotal_row) {
            frappe.model.set_value(cdt, cdn, 'is_bold', 1);
            frappe.model.set_value(cdt, cdn, 'is_total_row', 0);
        }
    },
    
    report_lines_add: function(frm, cdt, cdn) {
        // Auto-increment line number
        let row = locals[cdt][cdn];
        let max_line_number = 0;
        
        frm.doc.report_lines.forEach(function(line) {
            if (line.name !== cdn && line.line_number > max_line_number) {
                max_line_number = line.line_number;
            }
        });
        
        frappe.model.set_value(cdt, cdn, 'line_number', max_line_number + 10);
        frappe.model.set_value(cdt, cdn, 'sign_multiplier', '1');
    }
});

// ============================================
// Financial Report Column (Child Table)
// ============================================

frappe.ui.form.on('Financial Report Column', {
    column_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        // Only auto-fill if label is empty or looks auto-generated
        if (!row.column_label || is_auto_generated_label(row.column_label)) {
            let auto_label = generate_label_from_code(row.column_code);
            frappe.model.set_value(cdt, cdn, 'column_label', auto_label);
        }
        
        // Auto-detect column type
        let auto_type = detect_column_type(row.column_code);
        if (auto_type) {
            frappe.model.set_value(cdt, cdn, 'column_type', auto_type);
        }
        
        // Convert to uppercase
        if (row.column_code) {
            frappe.model.set_value(cdt, cdn, 'column_code', row.column_code.toUpperCase());
        }
    },
    
    report_columns_add: function(frm, cdt, cdn) {
        // Auto-increment column number
        let row = locals[cdt][cdn];
        let max_column_number = 0;
        
        if (frm.doc.report_columns) {
            frm.doc.report_columns.forEach(function(col) {
                if (col.name !== cdn && col.column_number > max_column_number) {
                    max_column_number = col.column_number;
                }
            });
        }
        
        frappe.model.set_value(cdt, cdn, 'column_number', max_column_number + 10);
    }
});

// ============================================
// Helper Functions for Column Auto-Labeling
// ============================================

function generate_label_from_code(column_code) {
    /**
     * Auto-generate clean labels without year
     * M1 → "Jan"
     * -M1 → "Jan LY"
     * M1_BUD → "Jan Bud"
     * Q1 → "Q1"
     * Y1 → "FY"
     * -Y1 → "FY LY"
     * -Y2 → "FY -2Y"
     * M1:M3 → "Jan-Mar"
     */
    if (!column_code) return '';
    
    let code = column_code.toUpperCase().trim();
    let is_last_year = false;
    let is_budget = false;
    let year_offset = 0;
    
    // Parse year offset (-Y1, -Y2, -Y3, etc.)
    let year_match = code.match(/^-Y(\d+)$/);
    if (year_match) {
        year_offset = parseInt(year_match[1]);
        if (year_offset === 1) {
            return 'FY LY';
        } else {
            return `FY -${year_offset}Y`;
        }
    }
    
    // Parse modifiers
    if (code.startsWith('-')) {
        is_last_year = true;
        code = code.substring(1);
    } else if (code.endsWith('_LY')) {
        is_last_year = true;
        code = code.replace('_LY', '');
    } else if (code.endsWith('_BUD')) {
        is_budget = true;
        code = code.replace('_BUD', '');
    }
    
    // Range syntax (M1:M3, Q1:Q2)
    if (code.includes(':')) {
        let parts = code.split(':');
        if (parts.length === 2) {
            let start_label = generate_simple_label(parts[0]);
            let end_label = generate_simple_label(parts[1]);
            let label = `${start_label}-${end_label}`;
            if (is_budget) return label + ' Bud';
            if (is_last_year) return label + ' LY';
            return label;
        }
    }
    
    // Month codes (M1-M12)
    if (code.match(/^M(\d+)$/)) {
        let month_num = parseInt(code.substring(1));
        let months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        if (month_num >= 1 && month_num <= 12) {
            let label = months[month_num - 1];
            if (is_budget) return label + ' Bud';
            if (is_last_year) return label + ' LY';
            return label;
        }
    }
    
    // Quarter codes (Q1-Q4)
    if (code.match(/^Q[1-4]$/)) {
        if (is_budget) return code + ' Bud';
        if (is_last_year) return code + ' LY';
        return code;
    }
    
    // Half-year codes (H1-H2)
    if (code.match(/^H[1-2]$/)) {
        if (is_budget) return code + ' Bud';
        if (is_last_year) return code + ' LY';
        return code;
    }
    
    // YTD
    if (code === 'YTD') {
        if (is_budget) return 'YTD Bud';
        if (is_last_year) return 'YTD LY';
        return 'YTD';
    }
    
    // FY / Y1
    if (code === 'FY' || code === 'Y1') {
        if (is_budget) return 'FY Bud';
        if (is_last_year) return 'FY LY';
        return 'FY';
    }
    
    // Variance patterns
    if (code.includes('VAR')) {
        if (code.includes('%') || code.includes('PCT')) {
            return 'Var %';
        }
        return 'Var';
    }
    
    // Default: return code as-is
    return column_code;
}

function generate_simple_label(code) {
    /**
     * Helper to generate label for range parts
     */
    code = code.toUpperCase().trim();
    
    // Month
    if (code.match(/^M(\d+)$/)) {
        let month_num = parseInt(code.substring(1));
        let months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        if (month_num >= 1 && month_num <= 12) {
            return months[month_num - 1];
        }
    }
    
    // Quarter
    if (code.match(/^Q[1-4]$/)) {
        return code;
    }
    
    return code;
}

function detect_column_type(column_code) {
    /**
     * Auto-detect column type from code
     */
    if (!column_code) return null;
    
    let code = column_code.toUpperCase().trim();
    
    // Budget columns
    if (code.endsWith('_BUD')) {
        if (code.includes('YTD')) return 'YTD Budget';
        return 'Period Budget';
    }
    
    // Last year columns
    if (code.startsWith('-') || code.endsWith('_LY')) {
        if (code.includes('YTD')) return 'YTD Last Year';
        return 'Period Last Year';
    }
    
    // YTD columns
    if (code.includes('YTD')) {
        return 'YTD Actual';
    }
    
    // Calculated columns (contains operators)
    if (code.includes('+') || code.includes('-') || code.includes('*') || code.includes('/') || 
        code.includes('VAR') || code.includes('PCT')) {
        return 'Calculated';
    }
    
    // Period columns (M1-M12, Q1-Q4, H1-H2, Y1, FY)
    if (code.match(/^M\d+$/) || code.match(/^Q[1-4]$/) || code.match(/^H[1-2]$/) || 
        code === 'Y1' || code === 'FY' || code.includes(':')) {
        return 'Period Actual';
    }
    
    return 'Period Actual'; // Default
}

function is_auto_generated_label(label) {
    /**
     * Check if label looks auto-generated
     */
    if (!label) return true;
    
    // Common auto-generated patterns
    return label.match(/^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)( (LY|Bud))?$/) ||
           label.match(/^Q[1-4]( (LY|Bud))?$/) ||
           label.match(/^H[1-2]( (LY|Bud))?$/) ||
           label.match(/^(FY|YTD)( (LY|Bud))?$/) ||
           label.match(/^FY -\d+Y$/) ||
           label.match(/^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Q[1-4])-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Q[1-4])( (LY|Bud))?$/) ||
           label.match(/^(Var|Var %)$/);
}