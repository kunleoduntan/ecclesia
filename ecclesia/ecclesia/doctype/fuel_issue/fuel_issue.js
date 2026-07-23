// Copyright (c) 2026, Kunle Oduntan and contributors
// ecclesia/ecclesia/doctype/fuel_issue/fuel_issue.js

frappe.ui.form.on('Fuel Issue', {
    onload: function(frm) {
        if (frm.is_new()) frm.set_value('issue_date', frappe.datetime.get_today());
    },
    litres_issued:    function(frm) { frm.trigger('compute_total'); },
    rate_per_litre:   function(frm) { frm.trigger('compute_total'); },
    compute_total: function(frm) {
        const total = flt(frm.doc.litres_issued) * flt(frm.doc.rate_per_litre);
        frm.set_value('total_cost', total);
    },
    vehicle: function(frm) {
        if (!frm.doc.vehicle) return;
        frappe.db.get_value('Company Vehicle', frm.doc.vehicle,
            ['assigned_driver', 'fuel_type', 'odometer_reading'],
            function(d) {
                if (d.assigned_driver && !frm.doc.driver) frm.set_value('driver', d.assigned_driver);
                if (d.fuel_type) frm.set_value('fuel_type', d.fuel_type);
                if (d.odometer_reading) frm.set_value('odometer_at_issue', d.odometer_reading);
            }
        );
    }
});
