// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt



frappe.ui.form.on('Doctype Creator', {
    refresh: function(frm) {
        console.log("REFRESH called");
        
        // Add custom buttons
        if (frm.doc.doctype_field_json) {
            frm.add_custom_button(__('Preview Structure'), function() {
                preview_json_structure(frm);
            }, __('Actions'));
            
            frm.add_custom_button(__('Clear JSON'), function() {
                frm.set_value('doctype_field_json', '');
                frm.set_value('create_document', 0);
            }, __('Actions'));
        }
        
        // Show status
        if (frm.doc.create_document) {
            frm.set_intro(__('✅ Ready to create! Just save the document.'), 'green');
        } else {
            frm.set_intro(__('Paste JSON, check "Create Document" and save'), 'blue');
        }
    },
    
    create_document: function(frm) {
        console.log("create_document changed to:", frm.doc.create_document);
        
        if (frm.doc.create_document) {
            if (!frm.doc.doctype_field_json) {
                frappe.msgprint({
                    title: __('No JSON'),
                    message: __('Please paste your DocType JSON before checking this box'),
                    indicator: 'red'
                });
                frm.set_value('create_document', 0);
                return;
            }
            
            frappe.show_alert({
                message: __('✅ Ready! Save the document to create DocTypes'),
                indicator: 'green'
            }, 5);
            
            frm.set_intro(__('✅ Ready to create! Just save the document.'), 'green');
        } else {
            frm.set_intro(__('Paste JSON, check "Create Document" and save'), 'blue');
        }
    },
    
    before_save: function(frm) {
        console.log("BEFORE_SAVE called");
        console.log("create_document value:", frm.doc.create_document);
        console.log("Has JSON:", !!frm.doc.doctype_field_json);
        
        if (frm.doc.create_document && !frm.doc.doctype_field_json) {
            console.log("ERROR: No JSON but checkbox is checked");
            frappe.throw(__('DocType Field JSON is required'));
        }
        
        if (frm.doc.create_document) {
            console.log("Will create doctypes on save");
            frappe.show_alert({
                message: __('Creating DocTypes...'),
                indicator: 'blue'
            });
        }
    },
    
    after_save: function(frm) {
        console.log("AFTER_SAVE called");
        
        // Reload to see the unchecked box and any messages
        setTimeout(() => {
            console.log("Reloading document...");
            frm.reload_doc();
        }, 2000);
    }
});

// Preview JSON structure  
function preview_json_structure(frm) {
    if (!frm.doc.doctype_field_json) {
        frappe.msgprint(__('No JSON to preview'));
        return;
    }
    
    // IMPORTANT: Replace YOUR_APP.YOUR_APP with your actual app name
    frappe.call({
        method: 'apple.apple.doctype.doctype_creator.doctype_creator.preview_json_structure',
        args: {
            json_str: frm.doc.doctype_field_json
        },
        callback: function(r) {
            console.log("Preview response:", r);
            if (r.message) {
                if (r.message.valid) {
                    show_preview_dialog(r.message);
                } else {
                    frappe.msgprint({
                        title: __('Invalid JSON'),
                        message: r.message.error || __('Unable to parse JSON structure'),
                        indicator: 'red'
                    });
                }
            }
        },
        error: function(r) {
            console.error("Preview error:", r);
            frappe.msgprint({
                title: __('Error'),
                message: __('Failed to preview. Check console for details.'),
                indicator: 'red'
            });
        }
    });
}

// Show preview dialog
function show_preview_dialog(preview_data) {
    let html = '<div style="padding: 10px;">';
    
    html += `<h4>Structure Type: <span class="badge badge-info">${preview_data.structure_type}</span></h4>`;
    
    if (preview_data.structure_type === 'multiple_doctypes') {
        html += `<p><strong>DocTypes to create:</strong> ${preview_data.doctype_count}</p>`;
        html += `<p><strong>Total Fields:</strong> ${preview_data.total_fields}</p>`;
        html += `<p><strong>Modules:</strong> ${preview_data.modules.join(', ')}</p>`;
        
        html += '<h5>DocTypes:</h5><ul>';
        preview_data.doctype_names.forEach(name => {
            let badge = preview_data.child_tables.includes(name) ? 
                '<span class="badge badge-warning">Child Table</span>' : 
                '<span class="badge badge-success">DocType</span>';
            html += `<li>${name} ${badge}</li>`;
        });
        html += '</ul>';
        
        if (preview_data.child_tables.length > 0) {
            html += `<p class="text-muted"><small>Note: Child tables will be created first</small></p>`;
        }
        
    } else if (preview_data.structure_type === 'single_doctype') {
        html += `<p><strong>DocType Name:</strong> ${preview_data.doctype_name}</p>`;
        html += `<p><strong>Module:</strong> ${preview_data.module}</p>`;
        html += `<p><strong>Fields:</strong> ${preview_data.field_count}</p>`;
        
        if (preview_data.is_child) {
            html += '<p><span class="badge badge-warning">Child Table</span></p>';
        }
        if (preview_data.is_submittable) {
            html += '<p><span class="badge badge-info">Submittable</span></p>';
        }
        
    } else if (preview_data.structure_type === 'fields_only') {
        html += `<p><strong>Fields:</strong> ${preview_data.field_count}</p>`;
        html += `<p class="text-warning">${preview_data.message}</p>`;
    }
    
    html += '</div>';
    
    frappe.msgprint({
        title: __('JSON Preview'),
        message: html,
        indicator: 'blue',
        wide: true
    });
}