// Copyright (c) 2026, Kunle Oduntan and contributors
// ecclesia/ecclesia/doctype/administrative_request/administrative_request.js

frappe.ui.form.on('Administrative Request', {

    onload: function(frm) {
        if (frm.is_new()) {
            frm.set_value('request_date', frappe.datetime.get_today());
        }
    },

    refresh: function(frm) {
        frm.trigger('setup_custom_buttons');
        frm.trigger('apply_priority_badge');
        frm.trigger('apply_status_color');
    },

    employee: function(frm) {
        if (frm.doc.employee) {
            frappe.db.get_value('Employee', frm.doc.employee, 'department', function(d) {
                frm.set_value('department', d.department);
            });
        }
    },

    priority: function(frm) { frm.trigger('apply_priority_badge'); },
    status:   function(frm) { frm.trigger('apply_status_color'); },

    // ── Custom buttons ──────────────────────────────────────────────────────

    setup_custom_buttons: function(frm) {
        frm.clear_custom_buttons();
        if (frm.is_new() || frm.doc.docstatus === 0) return;

        const status = frm.doc.status;

        if (status === 'Submitted') {
            frm.add_custom_button(__('Approve'), function() {
                frappe.prompt({
                    label: __('Approved Cost (₦)'), fieldname: 'approved_cost',
                    fieldtype: 'Currency', description: __('Leave blank to keep estimated cost')
                }, function(values) {
                    _call_status(frm, 'approve_request',
                        { request_name: frm.doc.name, approved_cost: values.approved_cost });
                }, __('Approve Request'));
            }, __('Actions'));

            frm.add_custom_button(__('Reject'), function() {
                frappe.prompt({
                    label: __('Rejection Reason'), fieldname: 'rejection_reason',
                    fieldtype: 'Small Text', reqd: 1
                }, function(values) {
                    _call_status(frm, 'reject_request',
                        { request_name: frm.doc.name, rejection_reason: values.rejection_reason });
                }, __('Reject Request'));
            }, __('Actions'));
        }

        if (status === 'Approved') {
            frm.add_custom_button(__('Mark In Progress'), function() {
                _call_status(frm, 'mark_in_progress', { request_name: frm.doc.name });
            }, __('Actions'));
        }

        if (status === 'In Progress') {
            frm.add_custom_button(__('Mark Completed'), function() {
                frappe.prompt({
                    label: __('Actual Cost (₦)'), fieldname: 'actual_cost',
                    fieldtype: 'Currency'
                }, function(values) {
                    _call_status(frm, 'complete_request',
                        { request_name: frm.doc.name, actual_cost: values.actual_cost });
                }, __('Complete Request'));
            }, __('Actions'));
        }
    },

    apply_priority_badge: function(frm) {
        const map = { 'Urgent': 'red', 'High': 'orange', 'Medium': 'blue', 'Low': 'gray' };
        frm.set_df_property('priority', 'description',
            `<span class="indicator ${map[frm.doc.priority] || 'gray'}"></span> <b>${frm.doc.priority || ''}</b>`
        );
    },

    apply_status_color: function(frm) {
        const map = {
            'Draft': 'gray', 'Submitted': 'blue', 'Approved': 'green',
            'In Progress': 'orange', 'Completed': 'teal', 'Rejected': 'red', 'Closed': 'dark'
        };
        frm.set_df_property('status', 'description',
            `<span class="indicator ${map[frm.doc.status] || 'gray'}"></span> <b>${frm.doc.status || ''}</b>`
        );
    }
});

function _call_status(frm, method, args) {
    frappe.call({
        method: `ecclesia.ecclesia.doctype.administrative_request.administrative_request.${method}`,
        args: args,
        callback: function() { frm.reload_doc(); }
    });
}
