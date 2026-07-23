// Copyright (c) 2026, Kunle Oduntan and contributors
// ecclesia/ecclesia/doctype/compliance_register/compliance_register.js
frappe.ui.form.on('Compliance Register', {
    refresh: function(frm) {
        frm.trigger('apply_expiry_indicator');
    },
    expiry_date: function(frm) { frm.trigger('apply_expiry_indicator'); },
    apply_expiry_indicator: function(frm) {
        if (!frm.doc.expiry_date) return;
        const today = frappe.datetime.get_today();
        const daysLeft = frappe.datetime.get_diff(frm.doc.expiry_date, today);
        let color = 'green';
        if (daysLeft < 0) color = 'red';
        else if (daysLeft <= 30) color = 'red';
        else if (daysLeft <= 60) color = 'orange';
        frm.set_df_property('expiry_date', 'description',
            `<span class="indicator ${color}"></span> <b>${daysLeft >= 0 ? daysLeft + ' days remaining' : 'EXPIRED ' + Math.abs(daysLeft) + ' days ago'}</b>`);
    }
});
