// Copyright (c) 2026, Kunle Oduntan and contributors
// ecclesia/ecclesia/doctype/visitor_register/visitor_register.js
frappe.ui.form.on('Visitor Register', {
    onload: function(frm) {
        if (frm.is_new()) frm.set_value('visit_date', frappe.datetime.get_today());
    },
    refresh: function(frm) {
        frm.trigger('setup_custom_buttons');
    },
    setup_custom_buttons: function(frm) {
        frm.clear_custom_buttons();
        if (frm.is_new()) return;
        if (frm.doc.status === 'Expected') {
            frm.add_custom_button(__('Check In'), function() {
                frappe.call({
                    method: 'ecclesia.ecclesia.doctype.visitor_register.visitor_register.check_in_visitor',
                    args: { visitor_name: frm.doc.name },
                    callback: function() { frm.reload_doc(); }
                });
            });
        }
        if (frm.doc.status === 'Checked In') {
            frm.add_custom_button(__('Check Out'), function() {
                frappe.call({
                    method: 'ecclesia.ecclesia.doctype.visitor_register.visitor_register.check_out_visitor',
                    args: { visitor_name: frm.doc.name },
                    callback: function() { frm.reload_doc(); }
                });
            });
        }
    }
});
