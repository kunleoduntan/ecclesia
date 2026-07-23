// Copyright (c) 2026, Value Impacts Consulting
frappe.ui.form.on('Compliance Training Calendar', {
    refresh: function(frm) {
        frm.trigger('apply_status_color');
        frm.trigger('setup_buttons');
        frm.trigger('show_completion_gauge');
    },
    actual_attendees: function(frm) { frm.trigger('show_completion_gauge'); },
    target_headcount: function(frm) { frm.trigger('show_completion_gauge'); },
    show_completion_gauge: function(frm) {
        const target = frm.doc.target_headcount || 0;
        const actual = frm.doc.actual_attendees || 0;
        const pct    = target > 0 ? Math.round(actual / target * 100) : 0;
        const target_pct = frm.doc.completion_target_pct || 100;
        const on_track  = pct >= target_pct;
        const color = on_track ? '#059669' : pct >= 50 ? '#D97706' : '#DC2626';
        frm.set_df_property('actual_completion_pct','description',
            `<div style="margin-top:6px">
               <div style="display:flex;justify-content:space-between;font-size:11px;color:#64748B;margin-bottom:4px">
                 <span>Completion: ${actual} / ${target}</span>
                 <span style="font-weight:700;color:${color}">${pct}%</span>
               </div>
               <div style="height:10px;background:#E2E8F0;border-radius:10px;overflow:hidden;position:relative">
                 <div style="position:absolute;top:0;left:${Math.min(target_pct,100)}%;width:2px;height:100%;background:#94A3B8;z-index:1" title="Target: ${target_pct}%"></div>
                 <div style="height:100%;width:${Math.min(pct,100)}%;background:${color};transition:width .7s"></div>
               </div>
               <div style="font-size:10px;color:#94A3B8;margin-top:3px">Target: ${target_pct}%  ${on_track?'✅ On track':'⚠️ Below target'}</div>
             </div>`
        );
        if (frm.doc.actual_completion_pct !== undefined) {
            frm.set_value('actual_completion_pct', pct);
        }
    },
    apply_status_color: function(frm) {
        const m = {'Planned':'grey','Scheduled':'blue','Completed':'green','Cancelled':'red','Postponed':'orange'};
        frm.page && frm.page.set_indicator(frm.doc.status||'Planned', m[frm.doc.status]||'grey');
    },
    setup_buttons: function(frm) {
        frm.clear_custom_buttons();
        if (frm.is_new()) return;
        frm.add_custom_button(__('👥 Add Participants'), () => {
            frappe.prompt([
                { label:'Department (leave blank for all)', fieldname:'dept', fieldtype:'Link', options:'Department' },
                { label:'Add All Active Employees?', fieldname:'all', fieldtype:'Check', default:0 }
            ], v => {
                frappe.call({
                    method: 'frappe.client.get_list',
                    args: {
                        doctype:'Employee', filters:{ status:'Active', ...(v.dept?{department:v.dept}:{}) },
                        fields:['name','employee_name','department'], limit:500
                    },
                    callback: r => {
                        if (!r.message) return;
                        let added = 0;
                        const existing = new Set((frm.doc.participants||[]).map(p=>p.employee));
                        r.message.forEach(emp => {
                            if (!existing.has(emp.name)) {
                                frm.add_child('participants', {
                                    employee: emp.name,
                                    employee_name: emp.employee_name,
                                    department: emp.department,
                                    completion_status:'Enrolled'
                                });
                                added++;
                            }
                        });
                        frm.refresh_field('participants');
                        frappe.show_alert({ message:`${added} participants added ✅`, indicator:'green' });
                    }
                });
            }, __('Add Participants'));
        }, __('Actions'));
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('✅ Mark Completed'), () => {
                frappe.confirm(__('Mark this training session as Completed?'), () => {
                    frappe.db.set_value('Compliance Training Calendar', frm.doc.name, 'status','Completed');
                    frm.reload_doc();
                });
            }, __('Actions'));
        }
        frm.add_custom_button(__('📊 Training Records'), () =>
            frappe.set_route('List','Compliance Training Record',{training_calendar:frm.doc.name}), __('Related'));
    }
});

frappe.ui.form.on('Training Participant Line', {
    completion_status: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.completion_status === 'Passed') {
            row.completion_date = frappe.datetime.get_today();
        }
        frm.refresh_field('participants');
        frm.trigger('show_completion_gauge');
    }
});
