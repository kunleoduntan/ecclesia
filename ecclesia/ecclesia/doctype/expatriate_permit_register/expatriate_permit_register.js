// Copyright (c) 2026, Value Impacts Consulting
frappe.ui.form.on('Expatriate Permit Register', {
    refresh: function(frm) {
        frm.trigger('show_expiry_indicator');
        frm.trigger('setup_buttons');
        frm.trigger('apply_status_color');
    },
    expiry_date: function(frm) { frm.trigger('show_expiry_indicator'); },
    employee: function(frm) {
        if (frm.doc.employee) {
            frappe.db.get_value('Employee', frm.doc.employee, ['nationality','employee_name'], r => {
                if (r.nationality && !frm.doc.nationality) frm.set_value('nationality', r.nationality);
            });
        }
    },
    show_expiry_indicator: function(frm) {
        if (!frm.doc.expiry_date) return;
        const days = frappe.datetime.get_diff(frm.doc.expiry_date, frappe.datetime.get_today());
        frm.set_value('days_to_expiry', days);
        const color = days < 0 ? 'red' : days <= 30 ? 'red' : days <= 90 ? 'orange' : 'green';
        const msg   = days < 0
            ? `🚨 EXPIRED ${Math.abs(days)} days ago — Immediate renewal required`
            : `${days} days remaining until expiry`;
        frm.set_df_property('expiry_date','description',
            `<div style="padding:8px 12px;background:${days<0?'#FEE2E2':days<=90?'#FEF3C7':'#D1FAE5'};
             border-radius:8px;color:${days<0?'#991B1B':days<=90?'#92400E':'#065F46'};
             font-weight:700;font-size:12px">⏰ ${msg}</div>`);
        frm.page && frm.page.set_indicator(frm.doc.status||'—', color);
    },
    apply_status_color: function(frm) {
        const m = {'Active':'green','Expiring Soon':'orange','Expired':'red','Renewing':'blue','Cancelled':'grey'};
        frm.page && frm.page.set_indicator(frm.doc.status||'—', m[frm.doc.status]||'grey');
    },
    setup_buttons: function(frm) {
        frm.clear_custom_buttons();
        if (frm.is_new()) return;
        frm.add_custom_button(__('🔄 Renew Permit'), () => {
            frappe.prompt([
                { label:'New Expiry Date', fieldname:'expiry', fieldtype:'Date', reqd:1 },
                { label:'New Permit Number', fieldname:'permit_no', fieldtype:'Data' },
                { label:'Renewal Cost (₦)', fieldname:'cost', fieldtype:'Currency' }
            ], v => {
                frm.set_value('expiry_date', v.expiry);
                frm.set_value('status','Renewing');
                if (v.permit_no) frm.set_value('permit_number', v.permit_no);
                if (v.cost) frm.set_value('renewal_cost', v.cost);
                frm.save().then(() => frappe.show_alert({ message:'Renewal recorded ✅', indicator:'green' }));
            }, __('Renew Permit'));
        }, __('Actions'));
    }
});
