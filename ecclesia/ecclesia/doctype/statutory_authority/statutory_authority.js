// statutory_authority.js
// Client script for Statutory Authority DocType
// ecclesia/ecclesia/doctype/statutory_authority/statutory_authority.js

frappe.ui.form.on('Statutory Authority', {

    refresh(frm) {
        _set_authority_indicators(frm);
        _add_quick_actions(frm);
    },

    obligation_type(frm) {
        _auto_fill_defaults(frm);
    },

    authority_type(frm) {
        _auto_fill_defaults(frm);
    },

    remittance_channel(frm) {
        // Show/hide Remita fields
        const is_remita = frm.doc.remittance_channel === 'Remita';
        frm.toggle_display('remita_rrr_prefix', is_remita);
    },

    contribution_basis(frm) {
        // Hide fixed_amount unless basis = Fixed Amount
        frm.toggle_display('fixed_amount', frm.doc.contribution_basis === 'Fixed Amount');
    },
});

// ── Auto-fill known Nigerian statutory defaults ───────────────────────────────
function _auto_fill_defaults(frm) {
    const OBL = frm.doc.obligation_type;
    const TYPE = frm.doc.authority_type;

    const DEFAULTS = {
        'Pension (PenCom)': {
            employee_rate: 8, employer_rate: 10,
            contribution_basis: 'Basic + Housing + Transport',
            remittance_due_day: 7, penalty_rate_pa: 2,
            frequency: 'Monthly',
            remittance_file_format: 'Excel',
            schedule_template: 'Pension Remittance (PenCom)',
            state_jurisdiction: 'Federal (All States)',
            remittance_channel: 'Bank Transfer',
        },
        'NSITF': {
            employee_rate: 0, employer_rate: 1,
            contribution_basis: 'Gross Pay',
            remittance_due_day: 7, penalty_rate_pa: 2,
            frequency: 'Monthly',
            remittance_file_format: 'Excel',
            schedule_template: 'NSITF Remittance Schedule',
            state_jurisdiction: 'Federal (All States)',
            remittance_channel: 'Bank Transfer',
        },
        'NHF': {
            employee_rate: 2.5, employer_rate: 0,
            contribution_basis: 'Basic Salary',
            remittance_due_day: 7, penalty_rate_pa: 2,
            frequency: 'Monthly',
            remittance_file_format: 'Excel',
            schedule_template: 'NHF Remittance Schedule',
            state_jurisdiction: 'Federal (All States)',
            remittance_channel: 'Bank Transfer',
        },
        'NHIS': {
            employee_rate: 1.75, employer_rate: 10,
            contribution_basis: 'Basic Salary',
            remittance_due_day: 7, penalty_rate_pa: 0,
            frequency: 'Monthly',
            remittance_file_format: 'Excel',
            schedule_template: 'NHIS Remittance Schedule',
            state_jurisdiction: 'Federal (All States)',
        },
        'ITF': {
            employee_rate: 0, employer_rate: 1,
            contribution_basis: 'Annual Payroll',
            penalty_rate_pa: 0,
            frequency: 'Annually',
            remittance_file_format: 'Excel',
            schedule_template: 'ITF Assessment Schedule',
            state_jurisdiction: 'Federal (All States)',
        },
        'PAYE': {
            employee_rate: 0, employer_rate: 0,
            contribution_basis: 'Gross Pay',
            remittance_due_day: 10, frequency: 'Monthly',
            remittance_file_format: 'Excel',
            schedule_template: 'PAYE Deduction Schedule',
            remittance_channel: 'Bank Transfer',
        },
        'Value Added Tax (VAT)': {
            frequency: 'Monthly',
            remittance_file_format: 'Excel',
            state_jurisdiction: 'Federal (All States)',
            remittance_channel: 'Remita',
        },
        'Withholding Tax (WHT)': {
            frequency: 'Monthly',
            remittance_file_format: 'Excel',
            remittance_channel: 'Remita',
        },
    };

    const defaults = DEFAULTS[OBL] || {};
    if (!Object.keys(defaults).length) return;

    Object.entries(defaults).forEach(([field, val]) => {
        if (!frm.doc[field]) {
            frm.set_value(field, val);
        }
    });

    frappe.show_alert({
        message: __('Default values applied for {0}', [OBL]),
        indicator: 'blue'
    }, 3);
}

// ── Indicators ────────────────────────────────────────────────────────────────
function _set_authority_indicators(frm) {
    if (!frm.doc.name) return;

    const STATUS_COLOR = {
        'Active': 'green', 'Inactive': 'grey', 'Suspended': 'red'
    };
    const color = STATUS_COLOR[frm.doc.status] || 'grey';
    frm.page.set_indicator(frm.doc.status || 'Unknown', color);

    // Warn if no bank account configured
    if (frm.doc.docstatus === 0 && !frm.doc.bank_account_number) {
        frm.dashboard.add_comment(
            '⚠️ No bank account number set — required to generate remittance payment instructions.',
            'yellow'
        );
    }
    // Warn if no schedule template
    if (!frm.doc.schedule_template) {
        frm.dashboard.add_comment(
            '⚠️ No schedule template selected — required for remittance file generation from Payroll Entry.',
            'yellow'
        );
    }
}

// ── Quick Actions ─────────────────────────────────────────────────────────────
function _add_quick_actions(frm) {
    if (!frm.doc.name || frm.is_new()) return;

    // View all remittance batches for this authority
    frm.add_custom_button(__('View Remittance History'), function () {
        const map = {
            'Pension (PenCom)': 'Pension Remittance Batch',
            'NHF':              'NHF Remittance Batch',
            'NSITF':            'NSITF Assessment',
        };
        const doctype = map[frm.doc.obligation_type];
        if (doctype) {
            frappe.set_route('List', doctype, {
                company: frm.doc.company
            });
        } else {
            frappe.msgprint(__('No dedicated batch list for this obligation type yet.'));
        }
    }, __('Quick Actions'));

    // Copy registration details to clipboard
    frm.add_custom_button(__('Copy Reg. Details'), function () {
        const lines = [
            `Authority: ${frm.doc.authority_name}`,
            `Code: ${frm.doc.authority_code}`,
            `TIN: ${frm.doc.company_tin || '—'}`,
            `Reg No: ${frm.doc.company_reg_number || '—'}`,
            `PAYE Code: ${frm.doc.company_paye_code || '—'}`,
            `PenCom Code: ${frm.doc.pencom_employer_code || '—'}`,
            `NSITF Code: ${frm.doc.nsitf_employer_code || '—'}`,
            `NHF Code: ${frm.doc.nhf_employer_code || '—'}`,
            `Bank Account: ${frm.doc.bank_account_number || '—'} (${frm.doc.account_name || ''})`,
        ].join('\n');
        navigator.clipboard.writeText(lines).then(() => {
            frappe.show_alert({ message: __('Registration details copied'), indicator: 'green' }, 3);
        });
    }, __('Quick Actions'));
}
