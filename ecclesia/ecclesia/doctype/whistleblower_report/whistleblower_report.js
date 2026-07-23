// Copyright (c) 2026, Value Impacts Consulting
frappe.ui.form.on('Whistleblower Report', {
    onload: function(frm) {
        if (frm.is_new()) {
            frappe.msgprint({ title:'🔒 Whistleblower Confidentiality Protocol', indicator:'blue',
                message:`<div style="font-size:13px;line-height:1.7">
                  <b>This form is confidential.</b><br>
                  • Never disclose the identity of the whistleblower<br>
                  • Do not discuss this report with unauthorised persons<br>
                  • Victimisation of whistleblowers is prohibited<br>
                  • A masked report code will be auto-generated
                </div>` });
        }
    },
    refresh: function(frm) {
        frm.trigger('setup_buttons');
        frm.trigger('apply_status_color');
        frm.trigger('show_confidentiality_banner');
    },
    is_anonymous: function(frm) {
        if (frm.doc.is_anonymous) {
            frm.set_df_property('alleged_parties','description',
                '<span style="color:#D97706;font-size:11px">⚠️ Do not include identifying details of the reporter in this field.</span>');
        }
    },
    severity: function(frm) {
        frm.trigger('apply_status_color');
        if (['High','Critical'].includes(frm.doc.severity)) {
            frappe.show_alert({ message:'🚨 High/Critical severity — will be escalated to Compliance Officer', indicator:'red' });
        }
    },
    apply_status_color: function(frm) {
        const m = {'Received':'blue','Under Investigation':'orange','Escalated':'red',
                   'Closed — Substantiated':'green','Closed — Unsubstantiated':'grey'};
        const sc= {'Low':'grey','Medium':'orange','High':'red','Critical':'red'};
        const c = m[frm.doc.status]||'grey';
        frm.page && frm.page.set_indicator(frm.doc.status||'New', c);
    },
    show_confidentiality_banner: function(frm) {
        frm.set_df_property('confidentiality_note','description',
            `<div style="padding:10px 14px;background:#FEE2E2;border-left:4px solid #DC2626;
             border-radius:6px;font-size:12px;color:#991B1B;font-weight:600">
             🔒 STRICTLY CONFIDENTIAL — Authorised persons only. Report Code: <b>${frm.doc.report_code || 'Auto-generated on save'}</b>
             </div>`);
    },
    setup_buttons: function(frm) {
        frm.clear_custom_buttons();
        if (!frm.doc.docstatus) return;
        frm.add_custom_button(__('🔍 Assign Investigator'), () => {
            frappe.prompt({ label:'Investigator', fieldname:'inv', fieldtype:'Link', options:'Employee', reqd:1 }, v => {
                frappe.db.set_value('Whistleblower Report', frm.doc.name, {
                    assigned_investigator: v.inv, status:'Under Investigation', investigation_start: frappe.datetime.get_today()
                }).then(() => { frm.reload_doc(); frappe.show_alert({ message:'Investigator assigned', indicator:'blue' }); });
            });
        }, __('Actions'));
        frm.add_custom_button(__('📋 Close Investigation'), () => {
            frappe.prompt([
                { label:'Outcome', fieldname:'outcome', fieldtype:'Select', reqd:1,
                  options:'Substantiated — Action Taken\nSubstantiated — No Action\nUnsubstantiated\nReferred to Authority' },
                { label:'Close Date', fieldname:'date', fieldtype:'Date', default:frappe.datetime.get_today() }
            ], v => {
                frappe.db.set_value('Whistleblower Report', frm.doc.name, {
                    outcome: v.outcome, investigation_close: v.date,
                    status: v.outcome.includes('Substantiated') ? 'Closed — Substantiated' : 'Closed — Unsubstantiated'
                }).then(() => { frm.reload_doc(); frappe.show_alert({ message:'Investigation closed', indicator:'green' }); });
            }, __('Close Investigation'));
        }, __('Actions'));
        if (frm.doc.compliance_incident_ref) {
            frm.add_custom_button(__('⚠️ View Incident'), () =>
                frappe.set_route('Form','Compliance Incident',frm.doc.compliance_incident_ref), __('Related'));
        }
    }
});
