// Copyright (c) 2026, Kunle Oduntan and contributors
// ecclesia/ecclesia/doctype/vehicle_trip_log/vehicle_trip_log.js

frappe.ui.form.on('Vehicle Trip Log', {

    onload: function(frm) {
        if (frm.is_new()) {
            frm.set_value('trip_date', frappe.datetime.get_today());
        }
    },

    refresh: function(frm) {
        frm.trigger('setup_custom_buttons');
    },

    vehicle: function(frm) {
        if (!frm.doc.vehicle) return;
        frappe.db.get_value('Company Vehicle', frm.doc.vehicle,
            ['odometer_reading', 'assigned_driver', 'fuel_type'],
            function(d) {
                if (d.odometer_reading) frm.set_value('odometer_start', d.odometer_reading);
                if (d.assigned_driver && !frm.doc.driver) frm.set_value('driver', d.assigned_driver);
            }
        );
    },

    odometer_start: function(frm) { frm.trigger('compute_distance'); },
    odometer_end:   function(frm) { frm.trigger('compute_distance'); },

    compute_distance: function(frm) {
        const start = flt(frm.doc.odometer_start);
        const end   = flt(frm.doc.odometer_end);
        if (start && end && end > start) {
            frm.set_value('distance_km', end - start);
        }
    },

    setup_custom_buttons: function(frm) {
        frm.clear_custom_buttons();
        if (frm.is_new()) return;
        if (frm.doc.vehicle) {
            frm.add_custom_button(__('Vehicle Record'), function() {
                frappe.set_route('Form', 'Company Vehicle', frm.doc.vehicle);
            }, __('View'));
        }
        if (frm.doc.vehicle_request) {
            frm.add_custom_button(__('Vehicle Request'), function() {
                frappe.set_route('Form', 'Vehicle Request', frm.doc.vehicle_request);
            }, __('View'));
        }
    }
});

// ── Fuel Detail child table ──────────────────────────────────────────────────
frappe.ui.form.on('Vehicle Fuel Detail', {
    litres: function(frm, cdt, cdn) { _calc_fuel_row(frm, cdt, cdn); },
    rate_per_litre: function(frm, cdt, cdn) { _calc_fuel_row(frm, cdt, cdn); },
});

function _calc_fuel_row(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    const amount = flt(row.litres) * flt(row.rate_per_litre);
    frappe.model.set_value(cdt, cdn, 'amount', amount);

    // Recompute total
    let total = 0;
    (frm.doc.fuel_details || []).forEach(r => { total += flt(r.amount); });
    frm.set_value('total_fuel_cost', total);
}
