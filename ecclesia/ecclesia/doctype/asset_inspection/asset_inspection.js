// Copyright (c) 2026, Kunle Oduntan and contributors
// ecclesia/ecclesia/doctype/asset_inspection/asset_inspection.js
frappe.ui.form.on('Asset Inspection', {
    onload: function(frm) {
        if (frm.is_new()) frm.set_value('inspection_date', frappe.datetime.get_today());
        frm.set_query('asset', function() {
            return { filters: { docstatus: 1 } };
        });
    },
    refresh: function(frm) {
        frm.trigger('setup_custom_buttons');
        frm.trigger('apply_condition_color');
    },
    overall_condition: function(frm) { frm.trigger('apply_condition_color'); },
    setup_custom_buttons: function(frm) {
        frm.clear_custom_buttons();
        if (!frm.is_new() && frm.doc.maintenance_request) {
            frm.add_custom_button(__('Maintenance Request'), function() {
                frappe.set_route('Form', 'Facility Maintenance Request', frm.doc.maintenance_request);
            }, __('View'));
        }
    },
    apply_condition_color: function(frm) {
        const map = { 'Excellent': 'green', 'Good': 'teal', 'Fair': 'orange', 'Poor': 'red', 'Critical - Action Required': 'darkred' };
        frm.set_df_property('overall_condition', 'description',
            `<span class="indicator ${map[frm.doc.overall_condition] || 'gray'}"></span>`);
    }
});
