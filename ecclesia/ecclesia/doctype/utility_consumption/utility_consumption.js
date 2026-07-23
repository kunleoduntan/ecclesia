// Copyright (c) 2026, Kunle Oduntan and contributors
// ecclesia/ecclesia/doctype/utility_consumption/utility_consumption.js

frappe.ui.form.on('Utility Consumption', {
    onload: function(frm) {
        if (frm.is_new()) frm.set_value('reading_date', frappe.datetime.get_today());
    },
    opening_reading: function(frm) { frm.trigger('compute_all'); },
    closing_reading: function(frm) { frm.trigger('compute_all'); },
    rate_per_unit:   function(frm) { frm.trigger('compute_all'); },
    fixed_charges:   function(frm) { frm.trigger('compute_all'); },
    vat_amount:      function(frm) { frm.trigger('compute_all'); },

    compute_all: function(frm) {
        const consumption = flt(frm.doc.closing_reading) - flt(frm.doc.opening_reading);
        if (consumption < 0) {
            frappe.show_alert({ message: __('Closing reading must exceed opening reading.'), indicator: 'red' });
            return;
        }
        const cost    = consumption * flt(frm.doc.rate_per_unit);
        const total   = cost + flt(frm.doc.fixed_charges) + flt(frm.doc.vat_amount);
        frm.set_value('consumption',       consumption);
        frm.set_value('consumption_cost',  cost);
        frm.set_value('total_bill',        total);
    },

    utility_meter: function(frm) {
        if (!frm.doc.utility_meter) return;
        frappe.db.get_value('Utility Meter', frm.doc.utility_meter,
            ['rate_per_unit', 'unit_of_measure', 'facility'],
            function(d) {
                if (d.rate_per_unit && !frm.doc.rate_per_unit) frm.set_value('rate_per_unit', d.rate_per_unit);
            }
        );
    }
});
