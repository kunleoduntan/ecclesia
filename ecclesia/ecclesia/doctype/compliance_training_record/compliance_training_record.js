// Copyright (c) 2026, Value Impacts Consulting
frappe.ui.form.on('Compliance Training Record', {
    refresh: function(frm) {
        frm.trigger('apply_status_color');
        frm.trigger('setup_buttons');
        frm.trigger('show_score_indicator');
    },
    score: function(frm) {
        frm.trigger('show_score_indicator');
        if (frm.doc.score !== null && frm.doc.score !== undefined) {
            const passed = frm.doc.score >= 70;
            frm.set_value('passed', passed ? 1 : 0);
            if (frm.doc.completion_status !== 'Completed') return;
            frm.set_value('completion_status', 'Completed');
            frappe.show_alert({
                message: passed ? `✅ Passed with ${frm.doc.score}%` : `❌ Failed — ${frm.doc.score}% (70% required)`,
                indicator: passed ? 'green' : 'red'
            });
        }
    },
    completion_status: function(frm) {
        frm.trigger('apply_status_color');
        if (frm.doc.completion_status === 'Completed' && frm.doc.score >= 70) {
            frm.set_value('passed', 1);
        }
        if (frm.doc.completion_status === 'Failed') frm.set_value('passed', 0);
    },
    show_score_indicator: function(frm) {
        if (frm.doc.score == null) return;
        const s = frm.doc.score, p = s >= 70;
        const bar = `<div style="display:flex;align-items:center;gap:10px;margin-top:5px">
          <div style="flex:1;height:8px;background:#E2E8F0;border-radius:10px;overflow:hidden">
            <div style="height:100%;width:${s}%;background:${p?'#059669':s>=50?'#D97706':'#DC2626'};transition:width .6s"></div>
          </div>
          <span style="font-size:13px;font-weight:800;color:${p?'#059669':'#DC2626'}">${s}%</span>
          <span style="font-size:18px">${p?'✅':'❌'}</span>
        </div><div style="font-size:11px;color:#94A3B8;margin-top:3px">Pass mark: 70%</div>`;
        frm.set_df_property('score','description', bar);
    },
    apply_status_color: function(frm) {
        const m = {'Enrolled':'blue','In Progress':'orange','Completed':'green','Failed':'red','Exempted':'grey'};
        frm.page && frm.page.set_indicator(frm.doc.completion_status||'Enrolled', m[frm.doc.completion_status]||'grey');
    },
    setup_buttons: function(frm) {
        frm.clear_custom_buttons();
        if (!frm.doc.docstatus) return;
        if (frm.doc.training_calendar) {
            frm.add_custom_button(__('📅 Training Calendar'), () =>
                frappe.set_route('Form','Compliance Training Calendar',frm.doc.training_calendar), __('Related'));
        }
        if (frm.doc.linked_policy) {
            frm.add_custom_button(__('📋 Related Policy'), () =>
                frappe.set_route('Form','Company Policy',frm.doc.linked_policy), __('Related'));
        }
    }
});
