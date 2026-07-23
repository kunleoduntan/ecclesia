// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt
// ecclesia/ecclesia/doctype/service_provider/service_provider.js

frappe.ui.form.on('Service Provider', {

    // ── Lifecycle ───────────────────────────────────────────────────────────

    onload: function(frm) {
        frm.trigger('setup_field_queries');
    },

    refresh: function(frm) {
        frm.trigger('setup_custom_buttons');
        frm.trigger('apply_status_badge');
        frm.trigger('load_provider_dashboard');
    },

    // ── Field triggers ──────────────────────────────────────────────────────

    status: function(frm) {
        frm.trigger('apply_status_badge');
        frm.trigger('setup_custom_buttons');
    },

    supplier: function(frm) {
        if (frm.doc.supplier) {
            frappe.show_alert({
                message: __('Linked to Supplier: {0}', [frm.doc.supplier]),
                indicator: 'green'
            });
        }
    },

    // ── Setup helpers ───────────────────────────────────────────────────────

    setup_field_queries: function(frm) {
        // No custom link queries needed — all standard ERPNext links
    },

    setup_custom_buttons: function(frm) {
        frm.clear_custom_buttons();

        if (!frm.is_new()) {
            // ── Create Supplier (only if Active and not yet linked) ──────
            if (frm.doc.status === 'Active' && !frm.doc.supplier) {
                frm.add_custom_button(__('Create Supplier'), function() {
                    frappe.confirm(
                        __('Create an ERPNext Supplier record for <b>{0}</b>?', [frm.doc.provider_name]),
                        function() {
                            frappe.call({
                                method: 'ecclesia.ecclesia.doctype.service_provider.service_provider.create_supplier_from_provider',
                                args: { service_provider: frm.doc.name },
                                freeze: true,
                                freeze_message: __('Creating Supplier...'),
                                callback: function(r) {
                                    if (r.message) {
                                        frm.reload_doc();
                                        frappe.set_route('Form', 'Supplier', r.message);
                                    }
                                }
                            });
                        }
                    );
                }, __('Actions'));
            }

            // ── View linked Supplier ─────────────────────────────────────
            if (frm.doc.supplier) {
                frm.add_custom_button(__('View Supplier'), function() {
                    frappe.set_route('Form', 'Supplier', frm.doc.supplier);
                }, __('Links'));
            }

            // ── View Contracts ───────────────────────────────────────────
            frm.add_custom_button(__('Service Contracts'), function() {
                frappe.set_route('List', 'Service Contract', {
                    service_provider: frm.doc.name
                });
            }, __('Links'));

            // ── Refresh KPIs ─────────────────────────────────────────────
            frm.add_custom_button(__('Refresh KPIs'), function() {
                frm.trigger('load_provider_dashboard');
            });
        }
    },

    apply_status_badge: function(frm) {
        const color_map = {
            'Active':      'green',
            'Inactive':    'gray',
            'Blacklisted': 'red'
        };
        const color = color_map[frm.doc.status] || 'gray';
        frm.set_df_property('status', 'description',
            `<span class="indicator ${color}">&nbsp;</span> <b>${frm.doc.status || ''}</b>`
        );
    },

    load_provider_dashboard: function(frm) {
        if (frm.is_new() || !frm.doc.name) return;

        frappe.call({
            method: 'ecclesia.ecclesia.doctype.service_provider.service_provider.get_provider_summary',
            args: { service_provider: frm.doc.name },
            callback: function(r) {
                if (!r.message) return;
                const d = r.message;
                const fmt = v => frappe.format(v, { fieldtype: 'Currency' });

                const html = `
                <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding:8px 0">
                    <div style="background:#f4f5f7;border-radius:8px;padding:14px;text-align:center">
                        <div style="font-size:24px;font-weight:700;color:#2e86c1">${d.active_contracts}</div>
                        <div style="font-size:11px;color:#888;margin-top:4px">Active Contracts</div>
                    </div>
                    <div style="background:#f4f5f7;border-radius:8px;padding:14px;text-align:center">
                        <div style="font-size:24px;font-weight:700;color:${d.expiring_contracts > 0 ? '#e67e22' : '#27ae60'}">${d.expiring_contracts}</div>
                        <div style="font-size:11px;color:#888;margin-top:4px">Expiring Soon</div>
                    </div>
                    <div style="background:#f4f5f7;border-radius:8px;padding:14px;text-align:center">
                        <div style="font-size:18px;font-weight:700;color:#2e86c1">${fmt(d.total_contract_value)}</div>
                        <div style="font-size:11px;color:#888;margin-top:4px">Active Contract Value</div>
                    </div>
                    <div style="background:#f4f5f7;border-radius:8px;padding:14px;text-align:center">
                        <div style="font-size:24px;font-weight:700;color:#8e44ad">${d.avg_vendor_score}</div>
                        <div style="font-size:11px;color:#888;margin-top:4px">Avg Vendor Score</div>
                    </div>
                </div>`;

                frm.fields_dict.html_dashboard && frm.fields_dict.html_dashboard.$wrapper
                    .find('.control-value').html(html);
            }
        });
    }
});
