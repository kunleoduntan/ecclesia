// Copyright (c) 2026, Kunle Oduntan and contributors
// ecclesia/ecclesia/doctype/meeting_room_booking/meeting_room_booking.js
frappe.ui.form.on('Meeting Room Booking', {
    onload: function(frm) {
        if (frm.is_new()) frm.set_value('booking_date', frappe.datetime.get_today());
        frm.set_query('facility', function() {
            return { filters: { facility_type: 'Conference Room', status: 'Active' } };
        });
    },
    refresh: function(frm) {
        frm.trigger('setup_custom_buttons');
    },
    setup_custom_buttons: function(frm) {
        frm.clear_custom_buttons();
        if (frm.is_new() || frm.doc.docstatus !== 1) return;
        if (frm.doc.status === 'Confirmed') {
            frm.add_custom_button(__('Mark In Use'), function() {
                frappe.db.set_value('Meeting Room Booking', frm.doc.name, 'status', 'In Use');
                frm.reload_doc();
            }, __('Status'));
            frm.add_custom_button(__('Cancel Booking'), function() {
                frappe.confirm(__('Cancel this booking?'), function() {
                    frappe.db.set_value('Meeting Room Booking', frm.doc.name, 'status', 'Cancelled');
                    frm.reload_doc();
                });
            }, __('Status'));
        }
        if (frm.doc.status === 'In Use') {
            frm.add_custom_button(__('Mark Completed'), function() {
                frappe.db.set_value('Meeting Room Booking', frm.doc.name, 'status', 'Completed');
                frm.reload_doc();
            }, __('Status'));
        }
    }
});
