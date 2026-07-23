// Copyright (c) 2026, Value Impacts Consulting
frappe.ui.form.on('Data Breach Register', {
    refresh: function(frm) {
        frm.trigger('setup_buttons');
        frm.trigger('show_notification_timer');
        frm.trigger('apply_severity_color');
    },
    breach_date: function(frm) { frm.trigger('show_notification_timer'); },
    nitda_notification_date: function(frm) { frm.trigger('compute_hours'); frm.trigger('show_notification_timer'); },
    severity: function(frm) {
        frm.trigger('apply_severity_color');
        if (['Medium','High','Critical'].includes(frm.doc.severity)) {
            frm.set_value('nitda_notification_required', 1);
            frappe.show_alert({ message:'⚠️ NITDA notification required within 72 hours for this severity level', indicator:'orange' });
        }
    },
    data_subjects_affected: function(frm) {
        if (frm.doc.data_subjects_affected > 1000) {
            frm.set_df_property('data_subjects_affected','description',
                '<span style="color:#DC2626;font-weight:700">🚨 Large-scale breach. Board notification and enhanced NITDA reporting may apply.</span>');
        }
    },
    compute_hours: function(frm) {
        if (frm.doc.breach_date && frm.doc.nitda_notification_date) {
            const breach = frappe.datetime.str_to_obj(frm.doc.breach_date);
            const notif  = frappe.datetime.str_to_obj(frm.doc.nitda_notification_date);
            const hours  = (notif - breach) / 3600000;
            frm.set_value('hours_to_notification', Math.round(hours * 10) / 10);
            frm.set_value('late_notification_flag', hours > 72 ? 1 : 0);
        }
    },
    show_notification_timer: function(frm) {
        if (!frm.doc.breach_date) return;
        const breach = frappe.datetime.str_to_obj(frm.doc.breach_date);
        const now    = new Date();
        const hours  = (now - breach) / 3600000;
        const remaining = Math.max(0, 72 - hours);
        const color = remaining < 12 ? '#DC2626' : remaining < 24 ? '#D97706' : '#059669';
        const msg   = frm.doc.nitda_notified
            ? '✅ NITDA already notified'
            : remaining <= 0
                ? `🚨 72-hour window EXPIRED (${Math.abs(Math.round(72 - hours))} hours overdue)`
                : `⏰ ${Math.round(remaining)} hours remaining to notify NITDA`;
        frm.set_df_property('nitda_notification_required','description',
            `<div style="padding:8px 12px;background:${remaining<=0?'#FEE2E2':remaining<24?'#FEF3C7':'#D1FAE5'};
             border-radius:8px;color:${color};font-weight:700;font-size:12px">${msg}</div>`);
    },
    apply_severity_color: function(frm) {
        const m = {'Low':'green','Medium':'orange','High':'red','Critical':'red'};
        frm.page && frm.page.set_indicator(frm.doc.severity || 'Draft', m[frm.doc.severity]||'grey');
    },
    setup_buttons: function(frm) {
        frm.clear_custom_buttons();
        if (frm.is_new()) return;
        if (!frm.doc.nitda_notified) {
            frm.add_custom_button(__('📤 Mark NITDA Notified'), () => {
                frappe.prompt([
                    { label:'NITDA Notification Date', fieldname:'date', fieldtype:'Date', reqd:1, default: frappe.datetime.get_today() },
                    { label:'NITDA Reference Number', fieldname:'ref', fieldtype:'Data', reqd:1 }
                ], v => {
                    frm.set_value('nitda_notified', 1);
                    frm.set_value('nitda_notification_date', v.date);
                    frm.set_value('nitda_notification_reference', v.ref);
                    frm.save().then(() => frappe.show_alert({ message:'NITDA notification recorded ✅', indicator:'green' }));
                }, __('Record NITDA Notification'));
            }, __('Actions'));
        }
        frm.add_custom_button(__('⚠️ View Compliance Incident'), () => {
            if (frm.doc.compliance_incident_ref)
                frappe.set_route('Form','Compliance Incident',frm.doc.compliance_incident_ref);
        }, __('Related'));
    }
});
