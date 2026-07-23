// Copyright (c) 2026, Value Impacts Consulting
frappe.ui.form.on('Environmental Compliance Record', {
    refresh: function(frm) {
        frm.trigger('show_expiry_status');
        frm.trigger('setup_buttons');
        frm.trigger('apply_status_color');
    },
    expiry_date: function(frm) { frm.trigger('show_expiry_status'); },
    apply_status_color: function(frm) {
        const m = {'Active':'green','Expiring Soon':'orange','Expired':'red','Under Renewal':'blue','Suspended':'red','Revoked':'red'};
        frm.page && frm.page.set_indicator(frm.doc.status||'—', m[frm.doc.status]||'grey');
    },
    show_expiry_status: function(frm) {
        if (!frm.doc.expiry_date) return;
        const days = frappe.datetime.get_diff(frm.doc.expiry_date, frappe.datetime.get_today());
        frm.set_value('days_to_expiry', days);
        const urgency = days < 0
            ? `🚨 EXPIRED — Operating without this permit is a regulatory offence`
            : days <= 30 ? `🔴 CRITICAL: Expires in ${days} days`
            : days <= 90 ? `🟠 ATTENTION: Expires in ${days} days`
            : `✅ Valid for ${days} more days`;
        const bg = days < 0 ? '#FEE2E2' : days <= 30 ? '#FEE2E2' : days <= 90 ? '#FEF3C7' : '#D1FAE5';
        const fc = days < 0 ? '#991B1B' : days <= 30 ? '#991B1B' : days <= 90 ? '#92400E' : '#065F46';
        frm.set_df_property('expiry_date','description',
            `<div style="padding:8px 12px;background:${bg};border-radius:8px;color:${fc};font-weight:700;font-size:12px">${urgency}</div>`);
    },
    setup_buttons: function(frm) {
        frm.clear_custom_buttons();
        if (frm.is_new()) return;
        frm.add_custom_button(__('🔄 Renew Permit'), () => {
            frappe.prompt([
                { label:'New Expiry Date', fieldname:'expiry', fieldtype:'Date', reqd:1 },
                { label:'New Permit Number', fieldname:'permit_no', fieldtype:'Data' },
                { label:'Renewal Cost (₦)', fieldname:'cost', fieldtype:'Currency' },
                { label:'New Permit Document', fieldname:'doc', fieldtype:'Attach' }
            ], v => {
                frm.set_value('expiry_date', v.expiry);
                frm.set_value('status','Active');
                if (v.permit_no) frm.set_value('permit_number', v.permit_no);
                if (v.cost) frm.set_value('renewal_cost', v.cost);
                if (v.doc) frm.set_value('permit_document', v.doc);
                frm.save().then(() => frappe.show_alert({ message:'Permit renewed ✅', indicator:'green' }));
            }, __('Renew Environmental Permit'));
        }, __('Actions'));
        if (frm.doc.hse_inspection_ref) {
            frm.add_custom_button(__('🔍 View HSE Inspection'), () =>
                frappe.set_route('Form','HSE Inspection',frm.doc.hse_inspection_ref), __('Related'));
        }
        frm.add_custom_button(__('📋 Record Inspection'), () => {
            frappe.prompt([
                { label:'Inspection Date', fieldname:'date', fieldtype:'Date', reqd:1, default:frappe.datetime.get_today() },
                { label:'Result', fieldname:'result', fieldtype:'Select', reqd:1,
                  options:'Satisfactory\nMinor Non-Compliance\nMajor Non-Compliance\nProsecution' },
                { label:'Corrective Actions Pending', fieldname:'actions', fieldtype:'Int', default:0 }
            ], v => {
                frm.set_value('last_inspection_date', v.date);
                frm.set_value('last_inspection_result', v.result);
                frm.set_value('corrective_actions_pending', v.actions);
                frm.save().then(() => frappe.show_alert({ message:'Inspection recorded', indicator:'blue' }));
            });
        }, __('Actions'));
    }
});
