frappe.provide('ecclesia.item_filter');

ecclesia.item_filter = {
    company_settings_cache: {},

    get_company_settings: async function (company) {
        if (!company) return {};
        if (this.company_settings_cache[company]) {
            return this.company_settings_cache[company];
        }
        const settings = await frappe.db.get_value('Company', company, ['hide_disabled_items']);
        this.company_settings_cache[company] = settings.message || {};
        return this.company_settings_cache[company];
    },

    apply_filter: async function (frm) {
        if (!frm || !frm.meta) return;

        const company = frm.doc.company || frappe.defaults.get_default('company');
        if (!company) return;

        const settings = await this.get_company_settings(company);
        if (!settings.hide_disabled_items) return;

        // ── Direct item_code on the form ──
        const has_direct_item = frm.meta.fields.find(
            f => f.fieldname === 'item_code' && f.fieldtype === 'Link' && f.options === 'Item'
        );
        if (has_direct_item) {
            frm.set_query('item_code', () => ({ filters: { disabled: 0 } }));
        }

        // ── Child tables with item_code ──
        frm.meta.fields
            .filter(f => f.fieldtype === 'Table')
            .forEach(table_field => {
                const grid = frm.fields_dict[table_field.fieldname];
                if (!grid || !grid.grid || !grid.grid.meta) return;

                const has_item_code = grid.grid.meta.fields.some(
                    cf => cf.fieldname === 'item_code' && cf.fieldtype === 'Link' && cf.options === 'Item'
                );

                if (has_item_code) {
                    frm.set_query('item_code', table_field.fieldname, () => ({
                        filters: { disabled: 0 }
                    }));
                }
            });
    },

    on_company_change: function (frm) {
        // Clear cache so fresh settings are fetched
        delete this.company_settings_cache[frm.doc.company];
        this.apply_filter(frm);
    }
};

// ── Apply on every form refresh globally ──
$(document).on('form-refresh', function (event, frm) {
    ecclesia.item_filter.apply_filter(frm);
});

// ── Re-apply when company field changes on any doctype ──
frappe.ui.form.on('*', {
    company: function (frm) {
        ecclesia.item_filter.on_company_change(frm);
    }
});
