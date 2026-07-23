// Copyright (c) 2026, Value Impacts Consulting
frappe.ui.form.on('AML KYC Record', {
    refresh: function(frm) {
        frm.trigger('setup_buttons');
        frm.trigger('apply_risk_color');
        frm.trigger('show_kyc_dashboard');
    },
    risk_rating: function(frm) {
        frm.trigger('apply_risk_color');
        const edd_required = ['High','PEP — High'];
        if (edd_required.includes(frm.doc.risk_rating)) {
            frm.set_value('kyc_level','Enhanced Due Diligence (EDD)');
            frappe.show_alert({ message:'🔴 EDD is mandatory for this risk rating', indicator:'red' });
        }
        if (frm.doc.risk_rating === 'Sanctioned — Blocked') {
            frappe.msgprint({ title:'⛔ SANCTIONED PARTY', indicator:'red',
                message:'This party is sanctioned. DO NOT create transactions. Contact AMLCO and legal counsel immediately.' });
        }
    },
    apply_risk_color: function(frm) {
        const m = {'Low':'green','Medium':'orange','High':'red','PEP — High':'purple','Sanctioned — Blocked':'red'};
        frm.page && frm.page.set_indicator(frm.doc.risk_rating || 'Unrated', m[frm.doc.risk_rating]||'grey');
    },
    show_kyc_dashboard: function(frm) {
        if (frm.is_new()) return;
        const checks = [
            { label:'Identity', ok: frm.doc.identity_verified },
            { label:'Address',  ok: frm.doc.address_verified },
            { label:'Beneficial Owner', ok: frm.doc.beneficial_owner_identified },
            { label:'PEP Check', ok: frm.doc.pep_check_done },
            { label:'Sanctions', ok: frm.doc.sanctions_check_done },
        ];
        const done = checks.filter(c => c.ok).length;
        const pct  = Math.round(done / checks.length * 100);
        const dots = checks.map(c =>
            `<span title="${c.label}" style="display:inline-block;width:28px;height:28px;border-radius:50%;
             background:${c.ok?'#059669':'#E2E8F0'};color:${c.ok?'#fff':'#94A3B8'};
             font-size:10px;text-align:center;line-height:28px;margin:2px">${c.label[0]}</span>`
        ).join('');
        frm.set_df_property('kyc_level','description',
            `<div style="margin-top:8px">
               <div style="display:flex;gap:4px;align-items:center;margin-bottom:6px">${dots}
                 <span style="font-size:12px;color:#64748B;margin-left:6px">KYC ${pct}% complete</span>
               </div>
               <div style="height:4px;background:#E2E8F0;border-radius:10px;overflow:hidden">
                 <div style="height:100%;width:${pct}%;background:${pct===100?'#059669':pct>60?'#D97706':'#DC2626'};transition:width .5s"></div>
               </div>
             </div>`
        );
    },
    setup_buttons: function(frm) {
        frm.clear_custom_buttons();
        if (frm.is_new()) return;
        frm.add_custom_button(__('🔍 Add Screening Result'), () => {
            const d = new frappe.ui.Dialog({ title:'Add Screening Result', fields:[
                { label:'Screening Type', fieldname:'type', fieldtype:'Select',
                  options:'PEP Check\nSanctions\nAdverse Media\nCDD\nEDD\nOngoing Monitoring', reqd:1 },
                { label:'Source / Database', fieldname:'source', fieldtype:'Data', reqd:1 },
                { label:'Result', fieldname:'result', fieldtype:'Select',
                  options:'Clear\nPotential Match\nConfirmed Match\nFalse Positive', reqd:1 },
                { label:'Match Detail', fieldname:'detail', fieldtype:'Small Text' }
            ], primary_action_label:'Add', primary_action(v) {
                frm.add_child('screening_results', {
                    screen_date: frappe.datetime.get_today(),
                    screening_type: v.type,
                    source_checked: v.source,
                    result: v.result,
                    match_detail: v.detail
                });
                frm.refresh_field('screening_results');
                d.hide();
                frappe.show_alert({ message:'Screening result added', indicator:'blue' });
            }});
            d.show();
        }, __('Actions'));
        frm.add_custom_button(__('📋 Related STRs'), () =>
            frappe.set_route('List','Suspicious Transaction Report',{kyc_record:frm.doc.name})
        , __('Related'));
    }
});
