// Copyright (c) 2026, Value Impacts Consulting
frappe.ui.form.on('Regulatory Return', {
    refresh: function(frm) {
        frm.trigger('setup_buttons');
        frm.trigger('apply_status_color');
        frm.trigger('show_deadline_banner');
    },
    submission_date: function(frm) { frm.trigger('check_late'); },
    due_date: function(frm)        { frm.trigger('check_late'); frm.trigger('show_deadline_banner'); },
    check_late: function(frm) {
        if (frm.doc.submission_date && frm.doc.due_date) {
            const late = frappe.datetime.str_to_obj(frm.doc.submission_date) >
                         frappe.datetime.str_to_obj(frm.doc.due_date);
            frm.set_value('late_flag', late ? 1 : 0);
            if (late) {
                frappe.show_alert({ message:'⚠️ Late submission — penalty may apply', indicator:'orange' });
                frm.set_value('status','Late Submitted');
            }
        }
    },
    show_deadline_banner: function(frm) {
        if (!frm.doc.due_date) return;
        const days = frappe.datetime.get_diff(frm.doc.due_date, frappe.datetime.get_today());
        const submitted = frm.doc.submission_date;
        if (submitted) return;
        const msg   = days < 0 ? `🚨 OVERDUE by ${Math.abs(days)} days` : days === 0 ? '🔴 Due TODAY' : `⏰ Due in ${days} days`;
        const bg    = days <= 0 ? '#FEE2E2' : days <= 7 ? '#FEF3C7' : '#F0F9FF';
        const fc    = days <= 0 ? '#991B1B' : days <= 7 ? '#92400E' : '#1E40AF';
        frm.set_df_property('due_date','description',
            `<div style="padding:8px 12px;background:${bg};border-radius:8px;color:${fc};font-weight:700;font-size:12px">${msg}</div>`);
    },
    apply_status_color: function(frm) {
        const m = {'Pending':'grey','Preparing':'blue','Submitted':'green','Late Submitted':'orange',
                   'Accepted':'green','Rejected':'red','Overdue':'red'};
        frm.page && frm.page.set_indicator(frm.doc.status||'Pending', m[frm.doc.status]||'grey');
    },
    setup_buttons: function(frm) {
        frm.clear_custom_buttons();
        if (frm.is_new()) return;
        if (!frm.doc.submission_date) {
            frm.add_custom_button(__('📤 Record Submission'), () => {
                frappe.prompt([
                    { label:'Submission Date', fieldname:'date', fieldtype:'Date', reqd:1, default:frappe.datetime.get_today() },
                    { label:'Regulatory Reference / Receipt', fieldname:'ref', fieldtype:'Data', reqd:1 },
                    { label:'Filing Evidence', fieldname:'attach', fieldtype:'Attach' }
                ], v => {
                    frm.set_value('submission_date', v.date);
                    frm.set_value('return_reference', v.ref);
                    if (v.attach) frm.set_value('attachment', v.attach);
                    frm.save().then(() => frappe.show_alert({ message:'Submission recorded ✅', indicator:'green' }));
                }, __('Record Return Submission'));
            }, __('Actions'));
        }
        frm.add_custom_button(__('📋 View CLL Entry'), () => {
            if (frm.doc.cll_entry) frappe.set_route('Form','Compliance Liability Ledger',frm.doc.cll_entry);
        }, __('Related'));
    }
});
