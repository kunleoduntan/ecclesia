// Copyright (c) 2026, Kunle Oduntan and contributors
// ecclesia/ecclesia/doctype/maintenance_work_order/maintenance_work_order.js
frappe.ui.form.on('Maintenance Work Order', {
    refresh: function(frm) {
        frm.trigger('setup_custom_buttons');
    },
    setup_custom_buttons: function(frm) {
        frm.clear_custom_buttons();
        if (frm.is_new()) return;
        if (frm.doc.maintenance_request) {
            frm.add_custom_button(__('Maintenance Request'), function() {
                frappe.set_route('Form', 'Facility Maintenance Request', frm.doc.maintenance_request);
            }, __('View'));
        }
        if (frm.doc.vendor) {
            frm.add_custom_button(__('Supplier'), function() {
                frappe.set_route('Form', 'Supplier', frm.doc.vendor);
            }, __('View'));
        }
    }
});
frappe.ui.form.on('Maintenance Task', {
    status: function(frm) {
        const tasks = frm.doc.tasks || [];
        const allDone = tasks.length > 0 && tasks.every(t => t.status === 'Completed');
        if (allDone) {
            frappe.show_alert({ message: __('All tasks completed! You may now mark the work order as Complete.'), indicator: 'green' });
        }
    }
});
