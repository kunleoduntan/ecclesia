// Copyright (c) 2026, Kunle Oduntan and contributors
// ecclesia/ecclesia/doctype/generator_log/generator_log.js

frappe.ui.form.on('Generator Log', {
    onload: function(frm) {
        if (frm.is_new()) frm.set_value('log_date', frappe.datetime.get_today());
    },
    opening_fuel_litres:    function(frm) { frm.trigger('compute_all'); },
    fuel_added_litres:      function(frm) { frm.trigger('compute_all'); },
    closing_fuel_litres:    function(frm) { frm.trigger('compute_all'); },
    diesel_rate_per_litre:  function(frm) { frm.trigger('compute_all'); },

    compute_all: function(frm) {
        const consumed = (flt(frm.doc.opening_fuel_litres) + flt(frm.doc.fuel_added_litres))
                       - flt(frm.doc.closing_fuel_litres);
        if (consumed >= 0) {
            frm.set_value('fuel_consumed_litres', Math.round(consumed * 100) / 100);
            const cost = consumed * flt(frm.doc.diesel_rate_per_litre);
            frm.set_value('fuel_cost', Math.round(cost * 100) / 100);
        }
    }
});
