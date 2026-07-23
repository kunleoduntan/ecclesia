// Copyright (c) 2026, Kunle Oduntan and contributors
// ecclesia/ecclesia/doctype/vehicle_request/vehicle_request.js
frappe.ui.form.on('Vehicle Request', {
    onload: function(frm) {
        if (frm.is_new()) frm.set_value('departure_date', frappe.datetime.get_today());
        frm.set_query('vehicle', function() {
            return { filters: { status: 'Available', company: frm.doc.company } };
        });
    },
    refresh: function(frm) {
        frm.trigger('setup_custom_buttons');
    },
    employee: function(frm) {
        if (frm.doc.employee) {
            frappe.db.get_value('Employee', frm.doc.employee, 'department', d => {
                frm.set_value('department', d.department);
            });
        }
    },
    setup_custom_buttons: function(frm) {
        frm.clear_custom_buttons();
        if (frm.is_new() || frm.doc.docstatus !== 1) return;
        if (frm.doc.status === 'Submitted' || frm.doc.status === 'Approved') {
            frm.add_custom_button(__('Assign Vehicle & Driver'), function() {
                frappe.prompt([
                    { label: __('Vehicle'), fieldname: 'vehicle', fieldtype: 'Link', options: 'Company Vehicle', reqd: 1 },
                    { label: __('Driver'), fieldname: 'driver', fieldtype: 'Link', options: 'Employee', reqd: 1 }
                ], function(values) {
                    frappe.call({
                        method: 'ecclesia.ecclesia.doctype.vehicle_request.vehicle_request.assign_vehicle',
                        args: { request_name: frm.doc.name, vehicle: values.vehicle, driver: values.driver },
                        callback: function() { frm.reload_doc(); }
                    });
                }, __('Assign Vehicle'));
            }, __('Actions'));
        }
        if (frm.doc.status === 'Vehicle Assigned') {
            frm.add_custom_button(__('Create Trip Log'), function() {
                frappe.new_doc('Vehicle Trip Log', {
                    vehicle: frm.doc.vehicle,
                    driver: frm.doc.driver,
                    vehicle_request: frm.doc.name,
                    purpose: frm.doc.purpose,
                    trip_date: frm.doc.departure_date
                });
            }, __('Create'));
        }
        if (frm.doc.trip_log) {
            frm.add_custom_button(__('Trip Log'), function() {
                frappe.set_route('Form', 'Vehicle Trip Log', frm.doc.trip_log);
            }, __('View'));
        }
    }
});
