// Copyright (c) 2026, Kunle Oduntan and contributors
// ecclesia/ecclesia/doctype/facility/facility.js

frappe.ui.form.on('Facility', {

    refresh: function(frm) {
        frm.trigger('setup_custom_buttons');
        frm.trigger('apply_status_color');
        if (!frm.is_new()) frm.trigger('load_kpi_dashboard');
    },

    status: function(frm) { frm.trigger('apply_status_color'); },

    setup_custom_buttons: function(frm) {
        frm.clear_custom_buttons();
        if (frm.is_new()) return;

        frm.add_custom_button(__('Maintenance Requests'), function() {
            frappe.set_route('List', 'Facility Maintenance Request', { facility: frm.doc.name });
        }, __('View'));

        frm.add_custom_button(__('Utility Readings'), function() {
            frappe.set_route('List', 'Utility Consumption', { facility: frm.doc.name });
        }, __('View'));

        frm.add_custom_button(__('Room Bookings'), function() {
            frappe.set_route('List', 'Meeting Room Booking', { facility: frm.doc.name });
        }, __('View'));

        frm.add_custom_button(__('Refresh KPIs'), function() {
            frm.trigger('load_kpi_dashboard');
        });
    },

    apply_status_color: function(frm) {
        const map = { 'Active': 'green', 'Under Maintenance': 'orange',
                      'Inactive': 'gray', 'Decommissioned': 'red' };
        frm.set_df_property('status', 'description',
            `<span class="indicator ${map[frm.doc.status] || 'gray'}"></span> <b>${frm.doc.status || ''}</b>`);
    },

    load_kpi_dashboard: function(frm) {
        if (frm.is_new()) return;
        frappe.call({
            method: 'ecclesia.ecclesia.doctype.facility.facility.get_facility_kpis',
            args: { facility: frm.doc.name },
            callback: function(r) {
                if (!r.message) return;
                const d = r.message;
                const fmt = v => frappe.format(v, { fieldtype: 'Currency' });
                const html = `
                <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;padding:8px 0">
                    <div style="background:#eafaf1;border-radius:8px;padding:14px;text-align:center">
                        <div style="font-size:24px;font-weight:700;color:${d.open_maintenance_requests > 0 ? '#e74c3c' : '#27ae60'}">${d.open_maintenance_requests}</div>
                        <div style="font-size:11px;color:#555;margin-top:4px">Open Maintenance Requests</div>
                    </div>
                    <div style="background:#eaf4fb;border-radius:8px;padding:14px;text-align:center">
                        <div style="font-size:18px;font-weight:700;color:#2980b9">${fmt(d.maintenance_cost_ytd)}</div>
                        <div style="font-size:11px;color:#555;margin-top:4px">Maintenance Cost YTD</div>
                    </div>
                    <div style="background:#fef9e7;border-radius:8px;padding:14px;text-align:center">
                        <div style="font-size:18px;font-weight:700;color:#d4ac0d">${fmt(d.utility_cost_ytd)}</div>
                        <div style="font-size:11px;color:#555;margin-top:4px">Utility Cost YTD</div>
                    </div>
                </div>`;
                frm.fields_dict.html_dashboard &&
                    frm.fields_dict.html_dashboard.$wrapper.find('.control-value').html(html);
            }
        });
    }
});
