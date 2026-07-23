// Copyright (c) 2026, Value Impacts Consulting
frappe.ui.form.on('Statutory Register Entry', {
    refresh: function(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__('📖 All Register Entries'), () =>
                frappe.set_route('List','Statutory Register Entry',{company:frm.doc.company,register_type:frm.doc.register_type})
            );
        }
        frm.trigger('setup_cac_form_hint');
    },
    register_type: function(frm) { frm.trigger('setup_cac_form_hint'); },
    setup_cac_form_hint: function(frm) {
        const map = {
            'Register of Directors':        'CAC Form 7 — due within 14 days of change',
            'Register of Members':          'CAC Form 2.1 — Return of Allotment',
            'Register of Allotments':       'CAC Form 2.1 — within 1 month of allotment',
            'Register of Share Transfers':  'Instrument of Transfer + CAC 2.1',
            'Register of Charges':          'CAC Form 8C — within 42 days of creation',
            'Register of Secretaries':      'CAC Form 10 — within 14 days of change',
        };
        const hint = map[frm.doc.register_type] || '';
        frm.set_df_property('cac_form_type','description',
            hint ? `<span style="color:#0284C7;font-size:11px">📋 ${hint}</span>` : '');
    }
});
