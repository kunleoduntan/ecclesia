// Copyright (c) 2026, Value Impacts Consulting
frappe.ui.form.on('Labour Compliance Tracker', {
    refresh: function(frm) {
        frm.trigger('render_compliance_scorecard');
        frm.trigger('apply_status_color');
    },
    lowest_gross_paid: function(frm) { frm.trigger('check_minimum_wage'); },
    current_min_wage:  function(frm) { frm.trigger('check_minimum_wage'); },
    check_minimum_wage: function(frm) {
        const lowest = frm.doc.lowest_gross_paid || 0;
        const min    = frm.doc.current_min_wage  || 70000;
        if (lowest > 0 && lowest < min) {
            frm.set_value('minimum_wage_compliant', 0);
            const shortfall = min - lowest;
            frm.set_df_property('lowest_gross_paid','description',
                `<span style="color:#DC2626;font-weight:700">❌ Below minimum wage by ₦${shortfall.toLocaleString()}</span>`);
        } else if (lowest >= min && min > 0) {
            frm.set_value('minimum_wage_compliant', 1);
            frm.set_df_property('lowest_gross_paid','description',
                '<span style="color:#059669;font-weight:700">✅ Above minimum wage</span>');
        }
    },
    apply_status_color: function(frm) {
        const m = {'Compliant':'green','Minor Issues':'orange','Major Issues':'red','Non-Compliant':'red'};
        frm.page && frm.page.set_indicator(frm.doc.overall_status||'Draft', m[frm.doc.overall_status]||'grey');
    },
    render_compliance_scorecard: function(frm) {
        if (frm.is_new()) return;
        const items = [
            { label:'Min Wage', ok: frm.doc.minimum_wage_compliant, critical:true },
            { label:'Hours',    ok: frm.doc.working_hours_compliant, critical:false },
            { label:'Leave',    ok: frm.doc.statutory_leave_compliant, critical:false },
            { label:'Contracts',ok: frm.doc.employment_contracts_compliant, critical:false },
            { label:'Discipline',ok: frm.doc.disciplinary_procedure_current, critical:false },
            { label:'PenCom',   ok: frm.doc.pencom_all_registered, critical:true },
            { label:'NHF',      ok: frm.doc.nhf_all_registered, critical:false },
            { label:'Maternity',ok: frm.doc.maternity_leave_compliant, critical:false },
        ];
        const score = items.filter(i => i.ok).length;
        const pct   = Math.round(score / items.length * 100);
        const cards = items.map(i =>
            `<div style="text-align:center;padding:10px 8px;background:${i.ok?'#D1FAE5':'#FEE2E2'};
              border-radius:10px;min-width:70px">
               <div style="font-size:18px">${i.ok?'✅':'❌'}</div>
               <div style="font-size:10px;font-weight:700;color:${i.ok?'#065F46':'#991B1B'};margin-top:4px">${i.label}</div>
               ${i.critical && !i.ok ? '<div style="font-size:9px;color:#DC2626">CRITICAL</div>' : ''}
             </div>`
        ).join('');
        const html = `<div style="margin:16px 0">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
            <span style="font-size:13px;font-weight:700;color:#334155">Labour Compliance Score</span>
            <span style="font-size:20px;font-weight:800;color:${pct>=80?'#059669':pct>=60?'#D97706':'#DC2626'}">${pct}%</span>
          </div>
          <div style="height:8px;background:#E2E8F0;border-radius:10px;overflow:hidden;margin-bottom:16px">
            <div style="height:100%;width:${pct}%;background:${pct>=80?'#059669':pct>=60?'#D97706':'#DC2626'};transition:width .7s"></div>
          </div>
          <div style="display:flex;gap:8px;flex-wrap:wrap">${cards}</div>
        </div>`;
        frm.set_df_property('overall_status','description', html);
    }
});
