// Copyright (c) 2026, Value Impacts Consulting
frappe.ui.form.on('Data Processing Record', {
    refresh: function(frm) {
        frm.trigger('setup_buttons');
        frm.trigger('show_gdpr_hints');
    },
    is_sensitive_data: function(frm) { frm.trigger('show_gdpr_hints'); },
    legal_basis: function(frm) { frm.trigger('show_gdpr_hints'); },
    international_transfer: function(frm) {
        if (frm.doc.international_transfer) {
            frappe.show_alert({ message:'⚠️ International transfer requires documented safeguards under NDPR Art. 43', indicator:'orange' });
            frm.set_df_property('transfer_safeguards','reqd',1);
            frm.set_df_property('transfer_countries','reqd',1);
        } else {
            frm.set_df_property('transfer_safeguards','reqd',0);
            frm.set_df_property('transfer_countries','reqd',0);
        }
    },
    show_gdpr_hints: function(frm) {
        const hints = {
            'Consent':             'Consent must be freely given, specific, informed and unambiguous. Keep records of consent.',
            'Legal Obligation':    'Identify the specific legislation requiring this processing.',
            'Legitimate Interest': 'A Legitimate Interest Assessment (LIA) must be completed and documented.',
        };
        const hint = hints[frm.doc.legal_basis] || '';
        frm.set_df_property('legal_basis','description', hint
            ? `<span style="color:#0284C7;font-size:11px">ℹ️ ${hint}</span>` : '');

        if (frm.doc.is_sensitive_data && !frm.doc.privacy_impact_done) {
            frm.set_df_property('privacy_impact_done','description',
                '<span style="color:#DC2626;font-weight:700">🚨 DPIA is mandatory for sensitive data processing under NDPR.</span>');
        } else {
            frm.set_df_property('privacy_impact_done','description','');
        }
    },
    setup_buttons: function(frm) {
        frm.clear_custom_buttons();
        if (frm.is_new()) return;
        frm.add_custom_button(__('🔒 Related Breach Records'), () =>
            frappe.set_route('List','Data Breach Register',{related_data_processing_record:frm.doc.name})
        );
        frm.add_custom_button(__('📋 Mark Reviewed'), () => {
            frappe.prompt({ label:'Review Date', fieldname:'date', fieldtype:'Date', reqd:1,
                default: frappe.datetime.get_today() }, v => {
                frm.set_value('last_reviewed', v.date);
                frm.set_value('next_review_date',
                    frappe.datetime.add_days(v.date, 365));
                frm.save();
            });
        }, __('Actions'));
    }
});
