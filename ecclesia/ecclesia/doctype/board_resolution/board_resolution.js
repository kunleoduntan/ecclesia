// Copyright (c) 2026, Value Impacts Consulting
frappe.ui.form.on('Board Resolution', {
    refresh: function(frm) {
        frm.trigger('setup_buttons');
        frm.trigger('apply_status_color');
        frm.trigger('show_cac_warning');
        frm.trigger('show_signatory_indicator');
    },
    meeting_type: function(frm) { frm.trigger('show_cac_warning'); },
    resolution_category: function(frm) { frm.trigger('show_cac_warning'); },
    show_cac_warning: function(frm) {
        const cac_cats = ['Appointment / Removal','Capital','Contracts'];
        if (cac_cats.includes(frm.doc.resolution_category)) {
            frm.set_df_property('cac_filing_required','description',
                '<span style="color:#D97706;font-weight:600">⚠️ This resolution category typically requires a CAC filing within 15 days.</span>');
        } else {
            frm.set_df_property('cac_filing_required','description','');
        }
    },
    apply_status_color: function(frm) {
        const m = {'Pending':'orange','In Progress':'blue','Implemented':'green','Not Applicable':'grey'};
        const c = m[frm.doc.implementation_status] || 'grey';
        frm.page && frm.page.set_indicator(frm.doc.implementation_status || 'Draft', c);
    },
    show_signatory_indicator: function(frm) {
        if (frm.doc.meeting_type !== 'Written Resolution') return;
        const unsigned = (frm.doc.signatories || []).filter((s) => !s.signed).length;
        if (unsigned) {
            frm.dashboard.add_indicator(__('{0} signature(s) pending', [unsigned]), 'orange');
        } else if ((frm.doc.signatories || []).length) {
            frm.dashboard.add_indicator(__('All signatories signed'), 'green');
        }
    },
    setup_buttons: function(frm) {
        frm.clear_custom_buttons();

        // ── Written Resolution signatory workflow (pre-submit only) ──────
        // Placed before the docstatus early-return below, since these
        // buttons are only relevant while the resolution is still Draft.
        if (frm.doc.meeting_type === 'Written Resolution' && frm.doc.docstatus === 0 && !frm.is_new()) {
            frm.add_custom_button(__('Load Board Members as Signatories'), () => {
                frappe.call({
                    method: 'ecclesia.api.board_resolution_api.load_signatories',
                    args: { resolution_name: frm.doc.name },
                    freeze: true,
                    freeze_message: __('Loading board members...'),
                    callback: (r) => {
                        if (r.message) {
                            frappe.show_alert({ message: r.message.message, indicator: 'green' });
                            frm.reload_doc();
                        }
                    },
                });
            }, __('Signatories'));

            if ((frm.doc.signatories || []).length) {
                frm.add_custom_button(__('Send Circulation Notice'), () => {
                    frappe.call({
                        method: 'ecclesia.api.board_resolution_api.send_circulation_notice',
                        args: { resolution_name: frm.doc.name },
                        freeze: true,
                        freeze_message: __('Sending circulation notice...'),
                        callback: (r) => {
                            if (r.message) {
                                frappe.show_alert({ message: r.message.message, indicator: 'green' });
                                frm.reload_doc();
                            }
                        },
                    });
                }, __('Signatories'));

                frm.add_custom_button(__('Send Signing Reminder'), () => {
                    frappe.call({
                        method: 'ecclesia.api.board_resolution_api.send_signing_reminder',
                        args: { resolution_name: frm.doc.name },
                        freeze: true,
                        callback: (r) => {
                            if (r.message) {
                                frappe.show_alert({ message: r.message.message, indicator: 'orange' });
                            }
                        },
                    });
                }, __('Signatories'));
            }
        }

        // ── Post-submit actions (unchanged from original) ──────
        if (!frm.doc.docstatus) return;
        frm.add_custom_button(__('✅ Mark Implemented'), () => {
            frappe.prompt({ label:'Implementation Date', fieldname:'date', fieldtype:'Date', reqd:1,
                default: frappe.datetime.get_today() }, v => {
                frm.set_value('implementation_date', v.date);
                frm.set_value('implementation_status','Implemented');
                frm.save();
            });
        }, __('Actions'));
        if (frm.doc.cac_filing_required && !frm.doc.cac_filed) {
            frm.add_custom_button(__('📋 Mark CAC Filed'), () => {
                frappe.prompt([
                    { label:'CAC Filing Reference', fieldname:'ref', fieldtype:'Data', reqd:1 },
                    { label:'Filing Date', fieldname:'date', fieldtype:'Date', default: frappe.datetime.get_today() }
                ], v => {
                    frappe.db.set_value('Board Resolution', frm.doc.name,
                        {'cac_filed':1,'cac_filing_reference':v.ref});
                    frm.reload_doc();
                    frappe.show_alert({ message:'CAC filing recorded ✅', indicator:'green' });
                });
            }, __('Actions'));
        }
    }
});
