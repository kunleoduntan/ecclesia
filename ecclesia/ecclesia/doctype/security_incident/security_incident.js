// Copyright (c) 2026, Kunle Oduntan and contributors
// ecclesia/ecclesia/doctype/security_incident/security_incident.js
frappe.ui.form.on('Security Incident', {
    onload: function(frm) {
        if (frm.is_new()) frm.set_value('report_date', frappe.datetime.get_today());
    },
    refresh: function(frm) {
        frm.trigger('setup_custom_buttons');
        frm.trigger('apply_severity_color');
    },
    severity: function(frm) { frm.trigger('apply_severity_color'); },
    setup_custom_buttons: function(frm) {
        frm.clear_custom_buttons();
        if (frm.is_new() || frm.doc.docstatus !== 1) return;
        frm.add_custom_button(__('Escalate to Police'), function() {
            frappe.confirm(__('Confirm escalation to police?'), function() {
                frappe.db.set_value('Security Incident', frm.doc.name, 'status', 'Escalated to Police');
                frm.reload_doc();
            });
        }, __('Actions'));
        frm.add_custom_button(__('Resolve'), function() {
            frappe.db.set_value('Security Incident', frm.doc.name, 'status', 'Resolved');
            frm.reload_doc();
        }, __('Actions'));
    },
    apply_severity_color: function(frm) {
        const map = { 'Minor': 'gray', 'Moderate': 'orange', 'Severe': 'red', 'Critical': 'darkred' };
        frm.set_df_property('severity', 'description',
            `<span class="indicator ${map[frm.doc.severity] || 'gray'}"></span> <b>${frm.doc.severity || ''}</b>`);
    }
});
