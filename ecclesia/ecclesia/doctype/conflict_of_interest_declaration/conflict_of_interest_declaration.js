// Copyright (c) 2026, Value Impacts Consulting
frappe.ui.form.on('Conflict of Interest Declaration', {
    refresh: function(frm) {
        frm.trigger('setup_buttons');
        frm.trigger('apply_status_color');
        frm.trigger('show_conflict_banner');
    },
    has_conflict: function(frm) {
        frm.trigger('show_conflict_banner');
        if (frm.doc.has_conflict) {
            frm.set_df_property('conflict_description','reqd',1);
            frm.set_df_property('conflict_type','reqd',1);
            frappe.show_alert({ message:'A conflict has been declared — please complete all required fields', indicator:'orange' });
        } else {
            frm.set_df_property('conflict_description','reqd',0);
            frm.set_df_property('conflict_type','reqd',0);
        }
    },
    financial_interest: function(frm) {
        frm.set_df_property('financial_value','reqd', frm.doc.financial_interest ? 1 : 0);
    },
    employee: function(frm) {
        if (frm.doc.employee) {
            frappe.db.get_value('Employee', frm.doc.employee,
                ['employee_name','designation','department','company','reports_to'], r => {
                    if (!frm.doc.designation && r.designation) frm.set_value('designation', r.designation);
                    if (!frm.doc.department  && r.department)  frm.set_value('department', r.department);
                    if (!frm.doc.company     && r.company)     frm.set_value('company', r.company);
                    if (!frm.doc.acknowledged_by && r.reports_to) frm.set_value('acknowledged_by', r.reports_to);
                });
        }
    },
    show_conflict_banner: function(frm) {
        const banner = frm.doc.has_conflict
            ? `<div style="padding:10px 14px;background:#FEF3C7;border-left:4px solid #D97706;border-radius:6px;
               font-size:12px;color:#92400E;font-weight:600">
               ⚠️ CONFLICT DECLARED — Line manager and Compliance Officer will be notified. 
               ${frm.doc.recusal_required ? '<br>🚫 Recusal from relevant decisions is required.' : ''}
               </div>`
            : `<div style="padding:10px 14px;background:#D1FAE5;border-left:4px solid #059669;border-radius:6px;
               font-size:12px;color:#065F46;font-weight:600">✅ No conflict declared for this period.</div>`;
        frm.set_df_property('has_conflict','description', banner);
    },
    apply_status_color: function(frm) {
        const m = {'Pending':'orange','Approved — No Further Action':'green',
                   'Approved with Conditions':'blue','Escalated to Board':'red'};
        frm.page && frm.page.set_indicator(frm.doc.approval_status||'Pending', m[frm.doc.approval_status]||'grey');
    },
    setup_buttons: function(frm) {
        frm.clear_custom_buttons();
        if (!frm.doc.docstatus) return;
        if (!frm.doc.line_manager_acknowledged) {
            frm.add_custom_button(__('✅ Acknowledge (Line Manager)'), () => {
                frm.set_value('line_manager_acknowledged',1);
                frm.set_value('approval_status',
                    frm.doc.has_conflict ? 'Approved with Conditions' : 'Approved — No Further Action');
                frm.save().then(() => frappe.show_alert({ message:'Acknowledged ✅', indicator:'green' }));
            }, __('Actions'));
        }
        if (frm.doc.has_conflict) {
            frm.add_custom_button(__('📋 Escalate to Board'), () => {
                frm.set_value('approval_status','Escalated to Board');
                frm.save().then(() => frappe.show_alert({ message:'Escalated to Board ✅', indicator:'orange' }));
            }, __('Actions'));
        }
    }
});
