// Copyright (c) 2026, Kunle Oduntan and contributors
// ecclesia/ecclesia/doctype/service_contract/service_contract.js

frappe.ui.form.on('Service Contract', {

    refresh: function(frm) {
        frm.trigger('setup_custom_buttons');
        frm.trigger('apply_expiry_indicator');
    },

    end_date: function(frm) { frm.trigger('apply_expiry_indicator'); },

    setup_custom_buttons: function(frm) {
        frm.clear_custom_buttons();
        if (frm.is_new()) return;

        if (frm.doc.docstatus === 1 && ['Active', 'Expiring Soon'].includes(frm.doc.status)) {
            frm.add_custom_button(__('Renew Contract'), function() {
                frappe.prompt([
                    { label: __('New End Date'), fieldname: 'new_end_date', fieldtype: 'Date', reqd: 1 },
                    { label: __('New Contract Value (₦)'), fieldname: 'new_contract_value', fieldtype: 'Currency' }
                ], function(values) {
                    frappe.call({
                        method: 'ecclesia.ecclesia.doctype.service_contract.service_contract.renew_contract',
                        args: {
                            contract_name: frm.doc.name,
                            new_end_date: values.new_end_date,
                            new_contract_value: values.new_contract_value
                        },
                        callback: function(r) {
                            if (r.message) {
                                frappe.show_alert({ message: __('Contract renewed: {0}', [r.message]), indicator: 'green' });
                                frappe.set_route('Form', 'Service Contract', r.message);
                            }
                        }
                    });
                }, __('Renew Contract'));
            }, __('Actions'));
        }

        if (frm.doc.vendor) {
            frm.add_custom_button(__('View Supplier'), function() {
                frappe.set_route('Form', 'Supplier', frm.doc.vendor);
            }, __('Links'));
        }
        if (frm.doc.service_provider) {
            frm.add_custom_button(__('Service Provider'), function() {
                frappe.set_route('Form', 'Service Provider', frm.doc.service_provider);
            }, __('Links'));
        }
    },

    apply_expiry_indicator: function(frm) {
        if (!frm.doc.end_date) return;
        const today = frappe.datetime.get_today();
        const daysLeft = frappe.datetime.get_diff(frm.doc.end_date, today);
        let color = 'green', label = `${daysLeft} days remaining`;
        if (daysLeft < 0)       { color = 'red';    label = `EXPIRED ${Math.abs(daysLeft)} days ago`; }
        else if (daysLeft <= 30) { color = 'red';    label = `Expiring in ${daysLeft} days — URGENT`; }
        else if (daysLeft <= 60) { color = 'orange'; label = `Expiring in ${daysLeft} days`; }

        frm.set_df_property('days_to_expiry', 'description',
            `<span class="indicator ${color}"></span> <b>${label}</b>`
        );
    }
});
