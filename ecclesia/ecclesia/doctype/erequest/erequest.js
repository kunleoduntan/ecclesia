// Copyright (c) 2026, Ecclesia and contributors
// For license information, please see license.txt

/**
 * eRequest Desk Client Script
 *
 * Workflow states are NOT hardcoded — buttons are shown based on whatever
 * workflow state the document is currently in, and Frappe's Workflow engine
 * drives transitions.  This script only:
 *   1. Toggles field visibility / requirements
 *   2. Calculates amounts
 *   3. Auto-fills payee details from Supplier / Employee
 *   4. Renders the status indicator pill
 *   5. Renders the approval timeline
 *   6. Provides custom desk buttons for approval stamping + payment creation
 */

frappe.ui.form.on('eRequest', {

    // ── Setup ─────────────────────────────────────────────────────────────────
    setup(frm) {
        frm.set_query('department', () => ({ filters: { is_group: 0 } }));
        frm.set_query('cost_center', () => ({
            filters: { company: frm.doc.company, is_group: 0 }
        }));
        frm.set_query('asset', () => ({ filters: { docstatus: 1 } }));
    },

    // ── Refresh ───────────────────────────────────────────────────────────────
    refresh(frm) {
        frm.trigger('toggle_type_fields');
        frm.trigger('render_status_pill');
        frm.trigger('render_approval_timeline');
        frm.trigger('render_action_buttons');
    },

    // ── Field triggers ────────────────────────────────────────────────────────
    request_type(frm) {
        frm.trigger('toggle_type_fields');

        // Clear irrelevant fields when switching type
        if (frm.doc.request_type === 'Maintenance Request') {
            ['payment_amount','tax_amount','total_amount','amount_in_words'].forEach(f => {
                frm.set_value(f, f.includes('amount') ? 0 : '');
            });
        }
    },

    payment_amount(frm) { frm.trigger('calc_total'); },
    tax_amount(frm)     { frm.trigger('calc_total'); },

    calc_total(frm) {
        if (frm.doc.request_type !== 'Payment Request') return;
        const total = flt(frm.doc.payment_amount) + flt(frm.doc.tax_amount);
        frm.set_value('total_amount', total);
    },

    payee_type(frm) {
        // Clear linked party when type changes
        frm.set_value('supplier', '');
        frm.set_value('employee', '');
        frm.set_value('payee_name', '');
    },

    supplier(frm) {
        if (!frm.doc.supplier) return;
        frappe.call({
            method: 'ecclesia_erequest.doctype.erequest.erequest.get_supplier_details',
            args: { supplier: frm.doc.supplier },
            callback(r) {
                if (r.message && r.message.supplier_name)
                    frm.set_value('payee_name', r.message.supplier_name);
            }
        });
    },

    employee(frm) {
        if (!frm.doc.employee) return;
        frappe.call({
            method: 'ecclesia_erequest.doctype.erequest.erequest.get_employee_details',
            args: { employee: frm.doc.employee },
            callback(r) {
                if (!r.message) return;
                if (r.message.employee_name) frm.set_value('payee_name',  r.message.employee_name);
                if (r.message.department)    frm.set_value('department',  r.message.department);
            }
        });
    },

    priority(frm)        { frm.trigger('render_status_pill'); },
    workflow_state(frm)  { frm.trigger('render_status_pill'); frm.trigger('render_action_buttons'); },

    // ── Toggle fields by request type ─────────────────────────────────────────
    toggle_type_fields(frm) {
        const isPay   = frm.doc.request_type === 'Payment Request';
        const isMaint = frm.doc.request_type === 'Maintenance Request';

        // Tab visibility
        frm.toggle_display('amount_tab',      isPay);
        frm.toggle_display('beneficiary_tab', isPay);
        frm.toggle_display('maintenance_tab', isMaint);

        // Payment mandatory
        ['payment_due_date','payment_amount','payee_type',
         'payee_name','payee_account_number','payee_account_name',
         'payee_bank_name'].forEach(f => frm.toggle_reqd(f, isPay));

        // Maintenance mandatory
        ['maintenance_type','maintenance_category','location','issue_description']
            .forEach(f => frm.toggle_reqd(f, isMaint));
    },

    // ── Status pill ───────────────────────────────────────────────────────────
    render_status_pill(frm) {
        const colorMap = {
            'Draft':                    'grey',
            'Pending Manager Approval': 'orange',
            'Pending Finance Approval': 'orange',
            'Pending Final Approval':   'orange',
            'Approved':                 'green',
            'Rejected':                 'red',
            'Cancelled':                'darkgrey',
        };
        const priorityIcon = { Low:'🟢', Medium:'🟡', High:'🟠', Urgent:'🔴' };
        const state  = frm.doc.workflow_state || 'Draft';
        const color  = colorMap[state] || 'grey';
        const icon   = priorityIcon[frm.doc.priority] || '';

        frm.fields_dict.status_indicator.$wrapper.html(`
            <div class="indicator-pill ${color}"
                 style="font-size:13px;padding:6px 16px;border-radius:20px;
                        display:inline-block;font-weight:600;">
                ${icon} ${state}
            </div>`);
    },

    // ── Approval timeline ─────────────────────────────────────────────────────
    render_approval_timeline(frm) {
        const doc = frm.doc;
        const state = doc.workflow_state || '';

        const steps = [
            { label: 'Submitted',       user: doc.created_by,       date: doc.created_date,           done: !!doc.created_date },
            { label: 'Manager Review',  user: doc.manager_approval,  date: doc.manager_approval_date,  comment: doc.manager_comments, done: !!doc.manager_approval,  pending: state.includes('Manager') },
            { label: 'Finance Review',  user: doc.finance_approval,  date: doc.finance_approval_date,  comment: doc.finance_comments, done: !!doc.finance_approval,  pending: state.includes('Finance') },
            { label: 'Final Approval',  user: doc.final_approval,    date: doc.final_approval_date,    comment: doc.final_comments,   done: !!doc.final_approval,    pending: state.includes('Final') },
        ];

        const stepsHtml = steps.map((s, i) => {
            const cls  = s.done ? 'done' : s.pending ? 'pending' : 'waiting';
            const icon = s.done ? '✓'   : s.pending ? '●'       : String(i + 1);
            const dot  = { done: '#22c55e', pending: '#f59e0b', waiting: '#e5e7eb' }[cls];
            const dotColor = cls === 'waiting' ? '#9ca3af' : 'white';
            return `
            <div style="display:flex;gap:12px;align-items:flex-start;padding:8px 0;position:relative;">
                ${i < steps.length - 1
                    ? `<div style="position:absolute;left:14px;top:38px;width:2px;height:calc(100% - 16px);background:#e5e7eb;"></div>`
                    : ''}
                <div style="width:30px;height:30px;border-radius:50%;background:${dot};color:${dotColor};
                            display:flex;align-items:center;justify-content:center;font-size:12px;
                            font-weight:700;flex-shrink:0;z-index:1;
                            ${s.pending ? 'animation:er-pulse 1.5s infinite;' : ''}">
                    ${icon}
                </div>
                <div style="padding-top:4px;">
                    <div style="font-weight:600;font-size:13px;color:#111827;">${s.label}</div>
                    ${s.user    ? `<div style="font-size:12px;color:#6b7280;">${s.user}</div>` : ''}
                    ${s.date    ? `<div style="font-size:11px;color:#9ca3af;">${frappe.datetime.str_to_user(s.date)}</div>` : ''}
                    ${s.comment ? `<div style="font-size:12px;color:#374151;font-style:italic;margin-top:2px;">"${s.comment}"</div>` : ''}
                </div>
            </div>`;
        }).join('');

        frm.fields_dict.timeline_html.$wrapper.html(`
            <style>
                @keyframes er-pulse{0%,100%{opacity:1;}50%{opacity:.55;}}
            </style>
            <div style="padding:8px 0;">${stepsHtml}</div>`);
    },

    // ── Action buttons ────────────────────────────────────────────────────────
    render_action_buttons(frm) {
        frm.clear_custom_buttons();
        if (frm.doc.__islocal) return;

        const state = frm.doc.workflow_state || '';
        const roles = frappe.user_roles;

        // ── Print
        frm.add_custom_button(__('Print'), () => {
            frappe.utils.print(frm.doctype, frm.docname, frm.doc.print_format || 'Standard');
        });

        // ── View existing payment entry
        if (frm.doc.payment_reference) {
            frm.add_custom_button(__('View Payments Document'), () => {
                frappe.set_route('Form', 'Payments', frm.doc.payment_reference);
            });
        }

        // ── Approval stamping buttons
        // These only record who approved — the actual state transition is done
        // by the Workflow Action button that Frappe renders automatically.
        // We show them alongside the workflow buttons for convenience.

        if (state.toLowerCase().includes('manager') &&
            roles.some(r => ['eRequest Manager','System Manager'].includes(r))) {
            frm.add_custom_button(__('Record Manager Approval'), () => {
                frm.trigger('_prompt_approval', 'manager');
            }, __('Approval')).addClass('btn-success');

            frm.add_custom_button(__('Record Rejection'), () => {
                frm.trigger('_prompt_rejection');
            }, __('Approval')).addClass('btn-danger');
        }

        if (state.toLowerCase().includes('finance') &&
            roles.some(r => ['eRequest Finance','System Manager'].includes(r))) {
            frm.add_custom_button(__('Record Finance Approval'), () => {
                frm.trigger('_prompt_approval', 'finance');
            }, __('Approval')).addClass('btn-success');

            frm.add_custom_button(__('Record Rejection'), () => {
                frm.trigger('_prompt_rejection');
            }, __('Approval')).addClass('btn-danger');
        }

        if (state.toLowerCase().includes('final') &&
            roles.some(r => ['eRequest Admin','System Manager'].includes(r))) {
            frm.add_custom_button(__('Record Final Approval'), () => {
                frm.trigger('_prompt_approval', 'final');
            }, __('Approval')).addClass('btn-success');

            frm.add_custom_button(__('Record Rejection'), () => {
                frm.trigger('_prompt_rejection');
            }, __('Approval')).addClass('btn-danger');
        }

        // ── Create Payment Entry (Finance/Admin, approved payment requests only)
        if (frm.doc.request_type === 'Payment Request' &&
            state === 'Approved' &&
            !frm.doc.payment_document_created &&
            roles.some(r => ['eRequest Finance','eRequest Admin','System Manager'].includes(r))) {
            frm.add_custom_button(__('Create Payment Document'), () => {
                frappe.confirm(__('Create a Payments document for this approved request?'), () => {
                    frappe.call({
                        method: 'create_payment_document',
                        doc:    frm.doc,
                        freeze: true,
                        freeze_message: __('Creating Payments Document…'),
                        callback(r) {
                            if (!r.exc && r.message) {
                                frappe.show_alert({
                                    message: __('Payments Document {0} created ({1} attachment(s) transferred)', [r.message.payment_doc, r.message.attachments_transferred || 0]),
                                    indicator: 'green',
                                });
                                frm.reload_doc();
                            }
                        }
                    });
                });
            }).addClass('btn-primary');
        }
    },

    // ── Approval prompt helpers ───────────────────────────────────────────────
    _prompt_approval(frm, level) {
        const labels = { manager: 'Manager', finance: 'Finance', final: 'Final' };
        const d = new frappe.ui.Dialog({
            title: `Record ${labels[level] || ''} Approval`,
            fields: [{ fieldname: 'comments', fieldtype: 'Small Text', label: 'Comments (optional)' }],
            primary_action_label: __('Record Approval'),
            primary_action({ comments }) {
                frappe.call({
                    method: 'record_approval',
                    doc:    frm.doc,
                    args:   { level, comments: comments || '' },
                    callback(r) {
                        if (!r.exc) {
                            frappe.show_alert({ message: __('Approval recorded'), indicator: 'green' });
                            frm.reload_doc();
                        }
                    }
                });
                d.hide();
            }
        });
        d.show();
    },

    _prompt_rejection(frm) {
        const d = new frappe.ui.Dialog({
            title: __('Record Rejection'),
            fields: [{ fieldname: 'reason', fieldtype: 'Text', label: __('Rejection Reason'), reqd: 1 }],
            primary_action_label: __('Record Rejection'),
            primary_action({ reason }) {
                frappe.call({
                    method: 'record_rejection',
                    doc:    frm.doc,
                    args:   { reason },
                    callback(r) {
                        if (!r.exc) {
                            frappe.show_alert({ message: __('Rejection recorded'), indicator: 'red' });
                            frm.reload_doc();
                        }
                    }
                });
                d.hide();
            }
        });
        d.show();
    },
});
