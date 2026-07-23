// Copyright (c) 2026, Kunle Oduntan and contributors
// ecclesia/ecclesia/doctype/facility_maintenance_request/facility_maintenance_request.js
frappe.ui.form.on('Facility Maintenance Request', {
    onload: function(frm) {
        if (frm.is_new()) frm.set_value('report_date', frappe.datetime.get_today());
    },
    refresh: function(frm) {
        frm.trigger('setup_custom_buttons');
        frm.trigger('apply_priority_color');
    },
    priority: function(frm) { frm.trigger('apply_priority_color'); },
    setup_custom_buttons: function(frm) {
        frm.clear_custom_buttons();
        if (frm.is_new() || frm.doc.docstatus !== 1) return;
        if (!frm.doc.work_order) {
            frm.add_custom_button(__('Create Work Order'), function() {
                frappe.new_doc('Maintenance Work Order', {
                    maintenance_request: frm.doc.name,
                    facility: frm.doc.facility,
                    title: frm.doc.subject,
                    priority: frm.doc.priority,
                    vendor: frm.doc.vendor,
                    lead_technician: frm.doc.assigned_technician
                });
            }, __('Create'));
        } else {
            frm.add_custom_button(__('Work Order'), function() {
                frappe.set_route('Form', 'Maintenance Work Order', frm.doc.work_order);
            }, __('View'));
        }
    },
    apply_priority_color: function(frm) {
        const map = { 'Emergency': 'red', 'High': 'orange', 'Medium': 'blue', 'Low': 'gray' };
        frm.set_df_property('priority', 'description',
            `<span class="indicator ${map[frm.doc.priority] || 'gray'}"></span> <b>${frm.doc.priority || ''}</b>`);
    }
});
