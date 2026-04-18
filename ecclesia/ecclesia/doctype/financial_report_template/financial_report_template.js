// Copyright (c) 2026, Ecclesia and contributors
// For license information, please see license.txt

// ============================================
// Financial Report Template - Main Form
// ============================================

frappe.ui.form.on('Financial Report Template', {
    refresh: function(frm) {
        // ── Custom Buttons ──────────────────────────────────────────────────
        if (!frm.is_new()) {

            // ── Clone Template (fixed: no frappe.client.clone_doc) ──────────
            frm.add_custom_button(__('Clone Template'), function() {
                frappe.prompt([
                    {
                        fieldname: 'new_name',
                        fieldtype: 'Data',
                        label: 'New Template Name',
                        reqd: 1,
                        description: 'Enter name for the cloned template'
                    }
                ],
                function(values) {
                    // Fetch the full doc, strip server-side keys, re-insert as new
                    frappe.call({
                        method: 'frappe.client.get',
                        args: {
                            doctype: 'Financial Report Template',
                            name: frm.doc.name
                        },
                        callback: function(r) {
                            if (!r.message) return;

                            let src = r.message;

                            // Build a clean copy - remove identity fields
                            let new_doc = Object.assign({}, src);
                            delete new_doc.name;
                            delete new_doc.modified;
                            delete new_doc.modified_by;
                            delete new_doc.creation;
                            delete new_doc.idx;
                            delete new_doc.docstatus;

                            new_doc.template_name = values.new_name;
                            new_doc.is_default = 0;

                            // Strip child-table row identities
                            ['report_lines', 'report_columns'].forEach(function(tbl) {
                                if (Array.isArray(new_doc[tbl])) {
                                    new_doc[tbl] = new_doc[tbl].map(function(row) {
                                        let r2 = Object.assign({}, row);
                                        delete r2.name;
                                        delete r2.parent;
                                        delete r2.parentfield;
                                        delete r2.parenttype;
                                        return r2;
                                    });
                                }
                            });

                            frappe.call({
                                method: 'frappe.client.insert',
                                args: { doc: new_doc },
                                callback: function(r2) {
                                    if (r2.message) {
                                        frappe.show_alert({
                                            message: __('Template cloned as "{0}"', [values.new_name]),
                                            indicator: 'green'
                                        });
                                        frappe.set_route('Form', 'Financial Report Template', r2.message.name);
                                    }
                                }
                            });
                        }
                    });
                },
                __('Clone Template'), __('Clone'));
            }, __('Actions'));

            // ── Preview Report ──────────────────────────────────────────────
            frm.add_custom_button(__('Preview Report'), function() {
                frappe.set_route('query-report', 'Financial Report - Template Based', {
                    template: frm.doc.name
                });
            }, __('Actions'));

            // ── Export Full Template JSON ───────────────────────────────────
            frm.add_custom_button(__('Export Template JSON'), function() {
                frappe.call({
                    method: 'frappe.client.get',
                    args: { doctype: 'Financial Report Template', name: frm.doc.name },
                    callback: function(r) {
                        if (r.message) {
                            _download_json(r.message, frm.doc.name.replace(/ /g, '_') + '_template');
                            frappe.show_alert({ message: __('Template exported'), indicator: 'green' });
                        }
                    }
                });
            }, __('Actions'));

            // ── Export Report Lines CSV ─────────────────────────────────────
            frm.add_custom_button(__('Export Lines CSV'), function() {
                _export_table_csv(frm, 'report_lines',
                    ['line_number','line_label','line_code','line_type',
                     'account_mapping_method','account_from','account_to',
                     'account_number_pattern','specific_accounts',
                     'financial_reporting_group','root_type_filter',
                     'calculation_formula','indent_level','is_bold',
                     'is_total_row','is_subtotal_row','sign_multiplier',
                     'hide_if_zero','show_percentage','border_style','row_color'],
                    frm.doc.name.replace(/ /g, '_') + '_lines');
            }, __('Export'));

            // ── Export Columns CSV ──────────────────────────────────────────
            frm.add_custom_button(__('Export Columns CSV'), function() {
                _export_table_csv(frm, 'report_columns',
                    ['column_number','column_label','column_code','column_type',
                     'calculation_formula','column_width','number_format','is_hidden'],
                    frm.doc.name.replace(/ /g, '_') + '_columns');
            }, __('Export'));

            // ── Import Report Lines CSV ─────────────────────────────────────
            frm.add_custom_button(__('Import Lines CSV'), function() {
                _import_table_csv(frm, 'report_lines',
                    ['line_number','line_label','line_code','line_type',
                     'account_mapping_method','account_from','account_to',
                     'account_number_pattern','specific_accounts',
                     'financial_reporting_group','root_type_filter',
                     'calculation_formula','indent_level','is_bold',
                     'is_total_row','is_subtotal_row','sign_multiplier',
                     'hide_if_zero','show_percentage','border_style','row_color'],
                    {
                        line_number: 'int',
                        indent_level: 'int',
                        is_bold: 'check',
                        is_total_row: 'check',
                        is_subtotal_row: 'check',
                        hide_if_zero: 'check',
                        show_percentage: 'check'
                    });
            }, __('Import'));

            // ── Import Columns CSV ──────────────────────────────────────────
            frm.add_custom_button(__('Import Columns CSV'), function() {
                _import_table_csv(frm, 'report_columns',
                    ['column_number','column_label','column_code','column_type',
                     'calculation_formula','column_width','number_format','is_hidden'],
                    {
                        column_number: 'int',
                        column_width: 'int',
                        is_hidden: 'check'
                    });
            }, __('Import'));

            // ── Import Full Template JSON ───────────────────────────────────
            frm.add_custom_button(__('Import Template JSON'), function() {
                _pick_file('.json', function(text) {
                    let data;
                    try { data = JSON.parse(text); }
                    catch(e) {
                        frappe.msgprint({ title: __('Error'), indicator: 'red',
                            message: __('Invalid JSON file.') });
                        return;
                    }
                    frappe.confirm(
                        __('This will overwrite the current Report Lines and Columns. Continue?'),
                        function() {
                            // Merge lines and columns only (keep current header fields)
                            if (Array.isArray(data.report_lines)) {
                                frm.doc.report_lines = [];
                                frm.refresh_field('report_lines');
                                data.report_lines.forEach(function(row) {
                                    let child = frm.add_child('report_lines');
                                    Object.assign(child, row);
                                    delete child.name; delete child.parent;
                                });
                            }
                            if (Array.isArray(data.report_columns)) {
                                frm.doc.report_columns = [];
                                frm.refresh_field('report_columns');
                                data.report_columns.forEach(function(row) {
                                    let child = frm.add_child('report_columns');
                                    Object.assign(child, row);
                                    delete child.name; delete child.parent;
                                });
                            }
                            frm.refresh_field('report_lines');
                            frm.refresh_field('report_columns');
                            frappe.show_alert({ message: __('Data imported from JSON'), indicator: 'green' });
                        }
                    );
                });
            }, __('Import'));
        }

        // ── Defaults for new doc ────────────────────────────────────────────
        if (frm.is_new()) {
            frm.set_value('excel_header_color',    '#4472C4');
            frm.set_value('excel_total_row_color', '#E7E6E6');
            frm.set_value('excel_subtotal_color',  '#F2F2F2');
            frm.set_value('excel_header_row',      '#D9E1F2');
            frm.set_value('negative_values_color', '#FF0000');
            frm.set_value('decimal_places',        2);
            frm.set_value('variance_threshold_highlight', 10);
        }

        // ── Line count badge ────────────────────────────────────────────────
        if (frm.doc.report_lines && frm.doc.report_lines.length > 0) {
            frm.dashboard.add_comment(
                __('Lines: {0}  |  Columns: {1}',
                    [frm.doc.report_lines.length,
                     (frm.doc.report_columns || []).length]),
                'blue', true);
        }
    },

    is_default: function(frm) {
        if (frm.doc.is_default && frm.doc.report_type) {
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Financial Report Template',
                    filters: { report_type: frm.doc.report_type, is_default: 1,
                               name: ['!=', frm.doc.name] },
                    fields: ['name']
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        frappe.msgprint({
                            title: __('Warning'), indicator: 'orange',
                            message: __('Another default already exists for {0}. Saving will unset it.',
                                [frm.doc.report_type])
                        });
                    }
                }
            });
        }
    },

    validate: function(frm) {
        _validate_report_lines(frm);
    }
});


// ============================================
// Child Table: Financial Report Line
// ============================================

frappe.ui.form.on('Financial Report Line', {
    line_type: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.line_type === 'Blank Line' || row.line_type === 'Header') {
            frappe.model.set_value(cdt, cdn, 'account_mapping_method', '');
            frappe.model.set_value(cdt, cdn, 'calculation_formula', '');
        }
        if (row.line_type === 'Calculated') {
            frappe.model.set_value(cdt, cdn, 'is_bold', 1);
        }
        frm.refresh_field('report_lines');
    },

    line_number: function(frm) {
        frm.doc.report_lines.sort((a, b) => (a.line_number || 0) - (b.line_number || 0));
        frm.refresh_field('report_lines');
    },

    line_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.line_code) {
            frappe.model.set_value(cdt, cdn, 'line_code', row.line_code.toUpperCase());
        }
    },

    calculation_formula: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.calculation_formula) return;

        let available = {};
        frm.doc.report_lines.forEach(function(line) {
            if (line.line_code && line.line_number < row.line_number) {
                available[line.line_code] = true;
            }
        });

        let tokens = row.calculation_formula.match(/\b[A-Z_][A-Z0-9_]*\b/g) || [];
        let missing = tokens.filter(t => !available[t]);
        if (missing.length) {
            frappe.msgprint({
                title: __('Formula Warning'), indicator: 'orange',
                message: __('Undefined codes: <b>{0}</b><br>Available: {1}',
                    [missing.join(', '), Object.keys(available).join(', ')])
            });
        }
    },

    is_total_row: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.is_total_row) {
            frappe.model.set_value(cdt, cdn, 'is_bold', 1);
            frappe.model.set_value(cdt, cdn, 'is_subtotal_row', 0);
        }
    },

    is_subtotal_row: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.is_subtotal_row) {
            frappe.model.set_value(cdt, cdn, 'is_bold', 1);
            frappe.model.set_value(cdt, cdn, 'is_total_row', 0);
        }
    },

    report_lines_add: function(frm, cdt, cdn) {
        let max = 0;
        frm.doc.report_lines.forEach(function(l) {
            if (l.name !== cdn && l.line_number > max) max = l.line_number;
        });
        frappe.model.set_value(cdt, cdn, 'line_number', max + 10);
        frappe.model.set_value(cdt, cdn, 'sign_multiplier', '1');
    }
});


// ============================================
// Child Table: Financial Report Column
// ============================================

frappe.ui.form.on('Financial Report Column', {
    column_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.column_code) return;

        // Uppercase
        frappe.model.set_value(cdt, cdn, 'column_code', row.column_code.toUpperCase());

        // Auto-label
        if (!row.column_label || _is_auto_label(row.column_label)) {
            frappe.model.set_value(cdt, cdn, 'column_label',
                generate_label_from_code(row.column_code));
        }

        // Auto-type
        let t = detect_column_type(row.column_code);
        if (t) frappe.model.set_value(cdt, cdn, 'column_type', t);
    },

    report_columns_add: function(frm, cdt, cdn) {
        let max = 0;
        (frm.doc.report_columns || []).forEach(function(c) {
            if (c.name !== cdn && c.column_number > max) max = c.column_number;
        });
        frappe.model.set_value(cdt, cdn, 'column_number', max + 10);
    }
});


// ============================================
// Import / Export Helpers
// ============================================

/**
 * Export a child table to CSV and trigger download.
 * @param {object} frm        - Frappe form
 * @param {string} fieldname  - Child table fieldname
 * @param {string[]} columns  - Column keys to export
 * @param {string} filename   - Base filename (no extension)
 */
function _export_table_csv(frm, fieldname, columns, filename) {
    let rows = frm.doc[fieldname] || [];
    if (!rows.length) {
        frappe.msgprint({ title: __('Nothing to export'), indicator: 'orange',
            message: __('The table "{0}" is empty.', [fieldname]) });
        return;
    }

    let csv_lines = [columns.join(',')];
    rows.forEach(function(row) {
        let cells = columns.map(function(col) {
            let val = row[col];
            if (val === null || val === undefined) val = '';
            val = String(val);
            // Quote if contains comma, newline or double-quote
            if (val.includes(',') || val.includes('\n') || val.includes('"')) {
                val = '"' + val.replace(/"/g, '""') + '"';
            }
            return val;
        });
        csv_lines.push(cells.join(','));
    });

    _download_text(csv_lines.join('\n'), filename + '.csv', 'text/csv');
    frappe.show_alert({
        message: __('Exported {0} rows to {1}.csv', [rows.length, filename]),
        indicator: 'green'
    });
}

/**
 * Pick a CSV file and import rows into a child table.
 * Existing rows are cleared first after user confirmation.
 *
 * @param {object} frm        - Frappe form
 * @param {string} fieldname  - Child table fieldname
 * @param {string[]} columns  - Expected column keys (order must match CSV header)
 * @param {object} types      - { fieldname: 'int'|'float'|'check' } for coercion
 */
function _import_table_csv(frm, fieldname, columns, types) {
    _pick_file('.csv', function(text) {
        let lines = text.split('\n').filter(l => l.trim());
        if (!lines.length) {
            frappe.msgprint({ title: __('Empty File'), indicator: 'red',
                message: __('The CSV file has no content.') });
            return;
        }

        // Parse header
        let header = _parse_csv_row(lines[0]);
        // Validate header - all expected columns must appear
        let missing_cols = columns.filter(c => !header.includes(c));
        if (missing_cols.length) {
            // Non-fatal: just warn and proceed with matching columns
            frappe.show_alert({
                message: __('CSV missing columns: {0}. These will be skipped.', [missing_cols.join(', ')]),
                indicator: 'orange'
            });
        }

        let data_lines = lines.slice(1);
        if (!data_lines.length) {
            frappe.msgprint({ title: __('No Data'), indicator: 'orange',
                message: __('CSV has a header but no data rows.') });
            return;
        }

        frappe.confirm(
            __('Import {0} rows into <b>{1}</b>? Existing rows will be cleared first.',
                [data_lines.length, fieldname]),
            function() {
                // Clear existing rows
                frm.doc[fieldname] = [];
                frm.refresh_field(fieldname);

                let errors = [];
                data_lines.forEach(function(line, idx) {
                    if (!line.trim()) return;
                    let cells = _parse_csv_row(line);
                    let child = frm.add_child(fieldname);

                    header.forEach(function(col, ci) {
                        if (!columns.includes(col)) return; // skip unknown cols
                        let val = cells[ci] !== undefined ? cells[ci] : '';
                        let type = (types || {})[col];
                        if (type === 'int') {
                            val = parseInt(val) || 0;
                        } else if (type === 'float') {
                            val = parseFloat(val) || 0;
                        } else if (type === 'check') {
                            val = (val === '1' || val.toLowerCase() === 'true') ? 1 : 0;
                        }
                        child[col] = val;
                    });
                });

                frm.refresh_field(fieldname);

                // Sort lines table by line_number after import
                if (fieldname === 'report_lines') {
                    frm.doc.report_lines.sort((a, b) => (a.line_number || 0) - (b.line_number || 0));
                    frm.refresh_field('report_lines');
                }

                frappe.show_alert({
                    message: __('Imported {0} rows into {1}', [data_lines.length, fieldname]),
                    indicator: 'green'
                });
            }
        );
    });
}

/**
 * Open a file picker filtered to a given extension, read the file as text,
 * and pass the content to a callback.
 * @param {string} ext       - e.g. '.csv' or '.json'
 * @param {function} cb      - callback(text: string)
 */
function _pick_file(ext, cb) {
    let input = document.createElement('input');
    input.type = 'file';
    input.accept = ext;
    input.onchange = function(e) {
        let file = e.target.files[0];
        if (!file) return;
        let reader = new FileReader();
        reader.onload = function(ev) { cb(ev.target.result); };
        reader.readAsText(file);
    };
    input.click();
}

/**
 * Parse a single CSV row handling quoted fields correctly.
 * @param {string} line
 * @returns {string[]}
 */
function _parse_csv_row(line) {
    let result = [];
    let cur = '';
    let in_quotes = false;
    for (let i = 0; i < line.length; i++) {
        let ch = line[i];
        if (ch === '"') {
            if (in_quotes && line[i + 1] === '"') {
                cur += '"'; i++; // escaped quote
            } else {
                in_quotes = !in_quotes;
            }
        } else if (ch === ',' && !in_quotes) {
            result.push(cur.trim());
            cur = '';
        } else {
            cur += ch;
        }
    }
    result.push(cur.trim());
    return result;
}

/**
 * Trigger a JSON file download.
 */
function _download_json(obj, filename) {
    _download_text(JSON.stringify(obj, null, 2), filename + '.json', 'application/json');
}

/**
 * Trigger a text file download.
 */
function _download_text(text, filename, mime) {
    let blob = new Blob([text], { type: mime });
    let url = URL.createObjectURL(blob);
    let a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

/**
 * Validate template lines (called from form validate hook).
 */
function _validate_report_lines(frm) {
    if (!frm.doc.report_lines || !frm.doc.report_lines.length) {
        frappe.msgprint({ title: __('Warning'), indicator: 'orange',
            message: __('Template has no report lines.') });
        return;
    }

    let seen = {}, dupes = [];
    frm.doc.report_lines.forEach(function(l) {
        if (seen[l.line_number]) dupes.push(l.line_number);
        seen[l.line_number] = true;
    });
    if (dupes.length) {
        frappe.msgprint({ title: __('Duplicate Line Numbers'), indicator: 'red',
            message: __('Duplicates: {0}', [dupes.join(', ')]) });
    }

    let codes = {};
    frm.doc.report_lines.forEach(l => { if (l.line_code) codes[l.line_code] = true; });
    frm.doc.report_lines.forEach(function(l) {
        if (l.line_type !== 'Calculated' || !l.calculation_formula) return;
        let tokens = l.calculation_formula.match(/\b[A-Z_][A-Z0-9_]*\b/g) || [];
        tokens.forEach(function(t) {
            if (!codes[t]) {
                frappe.msgprint({ title: __('Formula Error'), indicator: 'orange',
                    message: __('Line "{0}": formula references unknown code "{1}"',
                        [l.line_label, t]) });
            }
        });
    });
}


// ============================================
// Column Auto-labeling Helpers
// ============================================

function generate_label_from_code(column_code) {
    if (!column_code) return '';
    let code = column_code.toUpperCase().trim();

    // -Y1, -Y2 etc.
    let yr = code.match(/^-Y(\d+)$/);
    if (yr) return parseInt(yr[1]) === 1 ? 'FY LY' : 'FY -' + yr[1] + 'Y';

    let is_ly = false, is_bud = false;
    if (code.startsWith('-')) { is_ly = true; code = code.substring(1); }
    else if (code.endsWith('_LY')) { is_ly = true; code = code.replace('_LY', ''); }
    else if (code.endsWith('_BUD')) { is_bud = true; code = code.replace('_BUD', ''); }

    // Range M1:M3
    if (code.includes(':')) {
        let [s, e] = code.split(':');
        let label = _simple_label(s) + '-' + _simple_label(e);
        return is_bud ? label + ' Bud' : is_ly ? label + ' LY' : label;
    }

    const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

    // M1-M12
    let m = code.match(/^M(\d+)$/);
    if (m) {
        let mn = parseInt(m[1]);
        if (mn >= 1 && mn <= 12) {
            let lbl = MONTHS[mn - 1];
            return is_bud ? lbl + ' Bud' : is_ly ? lbl + ' LY' : lbl;
        }
    }

    // Q1-Q4, H1-H2
    if (code.match(/^[QH][1-4]$/)) {
        return is_bud ? code + ' Bud' : is_ly ? code + ' LY' : code;
    }

    if (code === 'YTD') return is_bud ? 'YTD Bud' : is_ly ? 'YTD LY' : 'YTD';
    if (code === 'FY' || code === 'Y1') return is_bud ? 'FY Bud' : is_ly ? 'FY LY' : 'FY';

    if (code.includes('VAR')) {
        return (code.includes('%') || code.includes('PCT')) ? 'Var %' : 'Var';
    }

    return column_code;
}

function _simple_label(code) {
    code = code.toUpperCase().trim();
    const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    let m = code.match(/^M(\d+)$/);
    if (m) {
        let n = parseInt(m[1]);
        if (n >= 1 && n <= 12) return MONTHS[n - 1];
    }
    return code;
}

function detect_column_type(code) {
    if (!code) return null;
    let c = code.toUpperCase().trim();
    if (c.endsWith('_BUD')) return c.includes('YTD') ? 'YTD Budget' : 'Period Budget';
    if (c.startsWith('-') || c.endsWith('_LY')) return c.includes('YTD') ? 'YTD Last Year' : 'Period Last Year';
    if (c.includes('YTD')) return 'YTD Actual';
    if (c.includes('+') || c.includes('VAR') || c.includes('PCT') || c.includes('/'))
        return 'Calculated';
    if (c.match(/^M\d+$/) || c.match(/^Q[1-4]$/) || c.match(/^H[1-2]$/) ||
        c === 'Y1' || c === 'FY' || c.includes(':'))
        return 'Period Actual';
    return 'Period Actual';
}

function _is_auto_label(label) {
    if (!label) return true;
    return !!(
        label.match(/^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)( (LY|Bud))?$/) ||
        label.match(/^Q[1-4]( (LY|Bud))?$/) ||
        label.match(/^H[1-2]( (LY|Bud))?$/) ||
        label.match(/^(FY|YTD)( (LY|Bud))?$/) ||
        label.match(/^FY -\d+Y$/) ||
        label.match(/^Var( %)?$/)
    );
}