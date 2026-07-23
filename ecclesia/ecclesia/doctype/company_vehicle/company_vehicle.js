// Copyright (c) 2026, Kunle Oduntan and contributors
// ecclesia/ecclesia/doctype/company_vehicle/company_vehicle.js

frappe.ui.form.on('Company Vehicle', {

    refresh: function(frm) {
        frm.trigger('setup_custom_buttons');
        frm.trigger('apply_status_badge');
        if (!frm.is_new()) frm.trigger('load_vehicle_dashboard');
    },

    status: function(frm) { frm.trigger('apply_status_badge'); },

    setup_custom_buttons: function(frm) {
        frm.clear_custom_buttons();
        if (frm.is_new()) return;

        // ── Quick status buttons ────────────────────────────────────────
        if (frm.doc.status === 'Available') {
            frm.add_custom_button(__('Mark In Use'), function() {
                _set_status(frm, 'In Use');
            }, __('Status'));
            frm.add_custom_button(__('Ground Vehicle'), function() {
                _set_status(frm, 'Grounded');
            }, __('Status'));
        }
        if (frm.doc.status === 'In Use') {
            frm.add_custom_button(__('Mark Available'), function() {
                _set_status(frm, 'Available');
            }, __('Status'));
        }
        if (!['Under Maintenance', 'Sold', 'Written Off'].includes(frm.doc.status)) {
            frm.add_custom_button(__('Send for Maintenance'), function() {
                _set_status(frm, 'Under Maintenance');
            }, __('Status'));
        }

        // ── Navigation buttons ──────────────────────────────────────────
        frm.add_custom_button(__('Trip Logs'), function() {
            frappe.set_route('List', 'Vehicle Trip Log', { vehicle: frm.doc.name });
        }, __('View'));

        frm.add_custom_button(__('Fuel Issues'), function() {
            frappe.set_route('List', 'Fuel Issue', { vehicle: frm.doc.name });
        }, __('View'));

        frm.add_custom_button(__('New Trip Log'), function() {
            frappe.new_doc('Vehicle Trip Log', { vehicle: frm.doc.name });
        }, __('Create'));

        frm.add_custom_button(__('Refresh Analytics'), function() {
            frm.trigger('load_vehicle_dashboard');
        });
    },

    apply_status_badge: function(frm) {
        const map = {
            'Available':         'green',
            'In Use':            'blue',
            'Under Maintenance': 'orange',
            'Grounded':          'red',
            'Sold':              'gray',
            'Written Off':       'darkgray'
        };
        frm.set_df_property('status', 'description',
            `<span class="indicator ${map[frm.doc.status] || 'gray'}"></span> <b>${frm.doc.status || ''}</b>`
        );
    },

    load_vehicle_dashboard: function(frm) {
        if (frm.is_new()) return;
        frappe.call({
            method: 'ecclesia.ecclesia.doctype.company_vehicle.company_vehicle.get_vehicle_analytics',
            args: { vehicle: frm.doc.name },
            callback: function(r) {
                if (!r.message) return;
                const d = r.message;
                const fmt = v => frappe.format(v, { fieldtype: 'Currency' });
                const html = `
                <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;padding:8px 0">
                    <div style="background:#eaf4fb;border-radius:8px;padding:12px;text-align:center">
                        <div style="font-size:20px;font-weight:700;color:#2980b9">${fmt(d.fuel_cost_ytd)}</div>
                        <div style="font-size:11px;color:#666;margin-top:3px">Fuel Cost YTD</div>
                    </div>
                    <div style="background:#fef9e7;border-radius:8px;padding:12px;text-align:center">
                        <div style="font-size:20px;font-weight:700;color:#d4ac0d">${fmt(d.maintenance_cost_ytd)}</div>
                        <div style="font-size:11px;color:#666;margin-top:3px">Maintenance YTD</div>
                    </div>
                    <div style="background:#eafaf1;border-radius:8px;padding:12px;text-align:center">
                        <div style="font-size:20px;font-weight:700;color:#27ae60">${(d.total_km_ytd || 0).toLocaleString()} km</div>
                        <div style="font-size:11px;color:#666;margin-top:3px">Distance YTD</div>
                    </div>
                    <div style="background:#f9ebea;border-radius:8px;padding:12px;text-align:center">
                        <div style="font-size:20px;font-weight:700;color:#e74c3c">${d.trips_ytd}</div>
                        <div style="font-size:11px;color:#666;margin-top:3px">Trips YTD</div>
                    </div>
                    <div style="background:#f4ecf7;border-radius:8px;padding:12px;text-align:center">
                        <div style="font-size:20px;font-weight:700;color:#8e44ad">${fmt(d.cost_per_km)}</div>
                        <div style="font-size:11px;color:#666;margin-top:3px">Cost / KM</div>
                    </div>
                </div>`;
                frm.fields_dict.html_dashboard &&
                    frm.fields_dict.html_dashboard.$wrapper.find('.control-value').html(html);
            }
        });
    }
});

// ── Module-level helper ──────────────────────────────────────────────────────
function _set_status(frm, status) {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.company_vehicle.company_vehicle.set_vehicle_status',
        args: { vehicle: frm.doc.name, status: status },
        callback: function() { frm.reload_doc(); }
    });
}
