// Copyright (c) 2026, Value Impacts Consulting
frappe.ui.form.on('Contract Compliance Record', {
    refresh: function(frm) {
        frm.trigger('setup_buttons');
        frm.trigger('apply_status_color');
        frm.trigger('show_sla_gauge');
    },
    service_contract: function(frm) {
        if (!frm.doc.service_contract) return;
        frappe.db.get_value('Service Contract', frm.doc.service_contract,
            ['vendor','contract_start_date','contract_end_date','contract_value'], r => {
                if (!frm.doc.vendor)          frm.set_value('vendor', r.vendor || '');
                if (!frm.doc.contract_start)  frm.set_value('contract_start', r.contract_start_date);
                if (!frm.doc.contract_end)    frm.set_value('contract_end', r.contract_end_date);
                if (!frm.doc.contract_value)  frm.set_value('contract_value', r.contract_value || 0);
            });
    },
    sla_compliance_pct: function(frm) { frm.trigger('show_sla_gauge'); },
    apply_status_color: function(frm) {
        const m = {'Compliant':'green','Minor Breach':'orange','Material Breach':'red','Termination Risk':'red','Expired':'grey'};
        frm.page && frm.page.set_indicator(frm.doc.compliance_status || 'Draft', m[frm.doc.compliance_status]||'grey');
    },
    show_sla_gauge: function(frm) {
        const pct = frm.doc.sla_compliance_pct || 0;
        const col = pct >= 95 ? '#059669' : pct >= 80 ? '#D97706' : '#DC2626';
        frm.set_df_property('sla_compliance_pct','description',
            `<div style="height:6px;background:#E2E8F0;border-radius:10px;overflow:hidden;margin-top:4px">
              <div style="height:100%;width:${pct}%;background:${col};border-radius:10px;transition:width .6s"></div>
             </div><span style="font-size:11px;color:${col};font-weight:700">${pct}% SLA</span>`
        );
    },
    setup_buttons: function(frm) {
        frm.clear_custom_buttons();
        if (frm.is_new()) return;
        frm.add_custom_button(__('🔄 Record Review'), () => {
            frappe.prompt([
                { label:'Review Date', fieldname:'date', fieldtype:'Date', reqd:1, default: frappe.datetime.get_today() },
                { label:'SLA Compliance %', fieldname:'sla', fieldtype:'Percent', reqd:1 },
                { label:'Open Breaches', fieldname:'breaches', fieldtype:'Int', default:0 },
                { label:'Obligations Met?', fieldname:'met', fieldtype:'Check', default:1 }
            ], v => {
                frm.set_value('last_review_date', v.date);
                frm.set_value('sla_compliance_pct', v.sla);
                frm.set_value('open_breaches', v.breaches);
                frm.set_value('obligations_met', v.met);
                frm.save().then(() => frappe.show_alert({ message:'Review recorded ✅', indicator:'green' }));
            }, __('Record Compliance Review'));
        }, __('Actions'));
        frm.add_custom_button(__('📄 View Service Contract'), () => {
            if (frm.doc.service_contract)
                frappe.set_route('Form','Service Contract', frm.doc.service_contract);
        }, __('Related'));
    }
});
