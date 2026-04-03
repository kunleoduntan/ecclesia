// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt


frappe.ui.form.on('Financial Reporting Group', {
    refresh: function(frm) {
        // Add custom button to view linked accounts
        if (!frm.is_new()) {
            frm.add_custom_button(__('View Linked Accounts'), function() {
                frappe.set_route('List', 'Account', {
                    'custom_financial_reporting_group': frm.doc.name
                });
            });
            
            // Show count of linked accounts
            frappe.call({
                method: 'frappe.client.get_count',
                args: {
                    doctype: 'Account',
                    filters: {
                        'custom_financial_reporting_group': frm.doc.name
                    }
                },
                callback: function(r) {
                    if (r.message !== undefined) {
                        frm.dashboard.add_comment(
                            __('Linked Accounts: {0}', [r.message]), 
                            r.message > 0 ? 'blue' : 'orange',
                            true
                        );
                    }
                }
            });
        }
        
        // Set default sort order if new
        if (frm.is_new()) {
            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'Financial Reporting Group',
                    filters: {
                        'report_type': frm.doc.report_type || 'Income Statement'
                    },
                    fieldname: 'sort_order',
                    order_by: 'sort_order desc',
                    limit: 1
                },
                callback: function(r) {
                    if (r.message && r.message.sort_order) {
                        frm.set_value('sort_order', r.message.sort_order + 10);
                    } else {
                        frm.set_value('sort_order', 10);
                    }
                }
            });
        }
    },
    
    is_group: function(frm) {
        if (frm.doc.is_group) {
            frappe.msgprint({
                title: __('Info'),
                indicator: 'blue',
                message: __('This group can contain sub-groups. Accounts cannot be directly linked to a parent group.')
            });
        }
    }
});