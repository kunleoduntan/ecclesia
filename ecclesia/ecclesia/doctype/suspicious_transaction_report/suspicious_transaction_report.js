// Copyright (c) 2026, Value Impacts Consulting
frappe.ui.form.on('Suspicious Transaction Report', {
    onload: function(frm) {
        if (frm.is_new()) {
            frappe.msgprint({ title:'🔐 Confidentiality Reminder', indicator:'red',
                message:'Tipping off is a criminal offence under the Money Laundering (Prevention and Prohibition) Act 2022. Keep this report strictly confidential.' });
        }
    },
    refresh: function(frm) {
        frm.trigger('setup_buttons');
        frm.trigger('apply_status_color');
        frm.trigger('show_nfiu_status');
    },
    transaction_amount: function(frm) {
        // CTR threshold for Nigeria (typically ₦5M+)
        if (frm.doc.transaction_amount >= 5000000 && frm.doc.report_type !== 'Currency Transaction Report (CTR)') {
            frm.set_df_property('report_type','description',
                '<span style="color:#D97706;font-weight:700">⚠️ Transaction ≥ ₦5M may require a Currency Transaction Report (CTR)</span>');
        }
    },
    show_nfiu_status: function(frm) {
        if (frm.doc.nfiu_submitted) {
            frm.set_df_property('nfiu_submitted','description',
                `<span style="color:#059669;font-weight:700">✅ Submitted to NFIU${frm.doc.nfiu_reference ? ' — Ref: '+frm.doc.nfiu_reference : ''}</span>`);
        } else if (frm.doc.docstatus === 1) {
            frm.set_df_property('nfiu_submitted','description',
                '<span style="color:#DC2626;font-weight:700">⚠️ NOT YET SUBMITTED to NFIU via goAML — ACTION REQUIRED</span>');
        }
    },
    apply_status_color: function(frm) {
        const m = {'Draft':'grey','Under Review':'orange','Submitted to NFIU':'green',
                   'Closed — No Action':'grey','Referred to Enforcement':'red'};
        frm.page && frm.page.set_indicator(frm.doc.status||'Draft', m[frm.doc.status]||'grey');
    },
    setup_buttons: function(frm) {
        frm.clear_custom_buttons();
        if (!frm.doc.docstatus) return;
        if (!frm.doc.nfiu_submitted) {
            frm.add_custom_button(__('📤 Mark Submitted to NFIU'), () => {
                frappe.prompt([
                    { label:'NFIU Submission Date', fieldname:'date', fieldtype:'Date', reqd:1, default: frappe.datetime.get_today() },
                    { label:'NFIU goAML Reference', fieldname:'ref', fieldtype:'Data', reqd:1 }
                ], v => {
                    frappe.db.set_value('Suspicious Transaction Report', frm.doc.name, {
                        nfiu_submitted:1, nfiu_submission_date:v.date, nfiu_reference:v.ref, status:'Submitted to NFIU'
                    }).then(() => { frm.reload_doc(); frappe.show_alert({ message:'NFIU submission recorded ✅', indicator:'green' }); });
                }, __('Record NFIU Submission'));
            }, __('Actions'));
        }
        frm.add_custom_button(__('🔍 View KYC Record'), () => {
            if (frm.doc.kyc_record) frappe.set_route('Form','AML KYC Record',frm.doc.kyc_record);
        }, __('Related'));
    }
});
