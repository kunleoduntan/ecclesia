// Copyright (c) 2026, Value Impacts Consulting
// ecclesia/ecclesia/doctype/corporate_compliance_register/corporate_compliance_register.js

frappe.ui.form.on('Corporate Compliance Register', {

    onload: function(frm) {
        if (frm.is_new()) {
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.corporate_compliance_register.corporate_compliance_register.get_cac_due_date',
                args: { company: frm.doc.company || frappe.defaults.get_default('company'), fiscal_year: frm.doc.fiscal_year },
                callback: r => { if (r.message && !frm.doc.annual_return_due_date) frm.set_value('annual_return_due_date', r.message); }
            });
        }
        frm.trigger('apply_status_color');
    },

    refresh: function(frm) {
        frm.trigger('setup_indicators');
        frm.trigger('setup_buttons');
        frm.trigger('apply_status_color');
        frm.trigger('render_checklist_html');
    },

    company: function(frm) {
        if (frm.doc.company) {
            frappe.db.get_value('Company', frm.doc.company, 'cac_rc_number', r => {
                if (r && r.cac_rc_number && !frm.doc.rc_number)
                    frm.set_value('rc_number', r.cac_rc_number);
            });
        }
    },

    fiscal_year: function(frm) {
        if (frm.doc.company && frm.doc.fiscal_year) {
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.corporate_compliance_register.corporate_compliance_register.get_cac_due_date',
                args: { company: frm.doc.company, fiscal_year: frm.doc.fiscal_year },
                callback: r => { if (r.message) frm.set_value('annual_return_due_date', r.message); }
            });
            // Check if CCR already exists for this FY
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.corporate_compliance_register.corporate_compliance_register.get_company_register_for_year',
                args: { company: frm.doc.company, fiscal_year: frm.doc.fiscal_year },
                callback: r => {
                    if (r.message && r.message !== frm.doc.name) {
                        frappe.msgprint({ title: 'Duplicate Warning', indicator: 'orange',
                            message: `A Corporate Compliance Register already exists for ${frm.doc.company} / ${frm.doc.fiscal_year}: <a href="/Form/Corporate Compliance Register/${r.message}">${r.message}</a>` });
                    }
                }
            });
        }
    },

    annual_return_filed_date: function(frm) {
        if (frm.doc.annual_return_filed_date && frm.doc.annual_return_due_date) {
            const filed = frappe.datetime.str_to_obj(frm.doc.annual_return_filed_date);
            const due   = frappe.datetime.str_to_obj(frm.doc.annual_return_due_date);
            if (filed > due) {
                frm.set_value('annual_return_status', 'Late Filed');
                frappe.show_alert({ message: '⚠️ Filed after due date — marked as Late Filed', indicator: 'orange' });
            } else {
                frm.set_value('annual_return_status', 'Filed On Time');
                frappe.show_alert({ message: '✅ Filed on time', indicator: 'green' });
            }
        }
    },

    apply_status_color: function(frm) {
        const colors = { 'Compliant':'green','Minor Issues':'orange','Major Issues':'red','Non-Compliant':'red' };
        const color  = colors[frm.doc.overall_status] || 'grey';
        frm.set_indicator_formatter && frm.set_indicator_formatter('overall_status', () => color);
        frm.page && frm.page.set_indicator(frm.doc.overall_status || '—', color);
    },

    setup_indicators: function(frm) {
        if (!frm.is_new()) {
            const days = frappe.datetime.get_diff(frm.doc.annual_return_due_date, frappe.datetime.get_today());
            const desc = days >= 0 ? `${days} days until CAC annual return due` : `${Math.abs(days)} days OVERDUE`;
            const color = days < 0 ? 'red' : days < 30 ? 'orange' : 'green';
            frm.set_df_property('annual_return_due_date', 'description',
                `<span class="indicator ${color}"></span> <b>${desc}</b>`);
        }
    },

    render_checklist_html: function(frm) {
        const checks = [
            { label:'AGM Held On Time', field:'agm_held_on_time' },
            { label:'Director Changes Notified', field:'director_changes_notified' },
            { label:'Shareholder Changes Notified', field:'shareholder_changes_notified' },
            { label:'Registered Address Current', field:'registered_address_current' },
            { label:'Statutory Registers Up to Date', field:'statutory_registers_current' },
        ];
        const rows = checks.map(c => {
            const ok = frm.doc[c.field];
            return `<div style="display:flex;align-items:center;gap:10px;padding:7px 0;border-bottom:1px solid #F1F5F9">
                <span style="font-size:16px">${ok ? '✅' : '❌'}</span>
                <span style="font-size:13px;color:${ok?'#059669':'#DC2626'};font-weight:600">${c.label}</span>
            </div>`;
        }).join('');
        // Show in form description or a dedicated HTML field if available
        const wrapper = frm.get_field && frm.get_field('notes');
        if (wrapper && wrapper.$wrapper) {
            const score = checks.filter(c => frm.doc[c.field]).length;
            const pct   = Math.round(score / checks.length * 100);
            // Prepend visual score if notes is empty
        }
    },

    setup_buttons: function(frm) {
        frm.clear_custom_buttons();
        if (frm.is_new()) return;
        frm.add_custom_button(__('📋 View Board Resolutions'), () => {
            frappe.set_route('List','Board Resolution', { corporate_register: frm.doc.name });
        }, __('Related'));
        frm.add_custom_button(__('📖 View Register Entries'), () => {
            frappe.set_route('List','Statutory Register Entry', { corporate_register: frm.doc.name });
        }, __('Related'));
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('✅ Mark Return Filed'), () => {
                frappe.prompt([
                    { label:'Filing Date', fieldname:'date', fieldtype:'Date', reqd:1, default: frappe.datetime.get_today() },
                    { label:'CAC Receipt No', fieldname:'receipt', fieldtype:'Data', reqd:1 },
                    { label:'Attach Evidence', fieldname:'attach', fieldtype:'Attach' }
                ], v => {
                    frm.set_value('annual_return_filed_date', v.date);
                    frm.set_value('annual_return_receipt', v.receipt);
                    frm.save().then(() => frappe.show_alert({ message:'CAC Return filed! ✅', indicator:'green' }));
                }, __('Mark CAC Annual Return Filed'));
            }, __('Actions'));
        }
    }
});
