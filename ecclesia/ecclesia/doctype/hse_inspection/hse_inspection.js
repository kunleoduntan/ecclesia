// Copyright (c) 2026, Kunle Oduntan and contributors
// ecclesia/ecclesia/doctype/hse_inspection/hse_inspection.js
frappe.ui.form.on('HSE Inspection', {
    onload: function(frm) {
        if (frm.is_new()) frm.set_value('inspection_date', frappe.datetime.get_today());
    },
    refresh: function(frm) {
        frm.trigger('apply_score_badge');
    },
    overall_score: function(frm) { frm.trigger('apply_score_badge'); },
    apply_score_badge: function(frm) {
        const score = frm.doc.overall_score || 0;
        const color = score >= 80 ? 'green' : score >= 60 ? 'orange' : 'red';
        frm.set_df_property('overall_score', 'description',
            `<span class="indicator ${color}"></span> <b>${frm.doc.pass_fail || ''}</b>`);
    }
});
frappe.ui.form.on('HSE Checklist Item', {
    compliant: function(frm) {
        let yes = 0, total = 0;
        (frm.doc.checklist || []).forEach(r => {
            if (r.compliant !== 'N/A') { total++; if (r.compliant === 'Yes') yes++; }
        });
        if (total > 0) {
            const score = Math.round(yes / total * 100 * 10) / 10;
            frm.set_value('overall_score', score);
            frm.set_value('pass_fail', score >= 80 ? 'Pass' : score >= 60 ? 'Conditional Pass' : 'Fail');
            frm.trigger('apply_score_badge');
        }
    }
});
