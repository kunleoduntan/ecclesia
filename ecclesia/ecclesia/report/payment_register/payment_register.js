// Copyright (c) 2025, Your Company and contributors
// For license information, please see license.txt

frappe.query_reports["Payment Register"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 1
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname": "trans_type",
            "label": __("Transaction Type"),
            "fieldtype": "Select",
            "options": "\nSupplier Payment\nExpense Payment\nTransfer Out\nSupplier Refunds\nPayment Request\nMaintenance Request"
        },
        {
            "fieldname": "payment_status",
            "label": __("Payment Status"),
            "fieldtype": "Select",
            "options": "\nDraft\nPending Approval\nApproved\nProcessing\nCompleted\nCancelled\nRejected"
        },
        {
            "fieldname": "payee_id",
            "label": __("Supplier"),
            "fieldtype": "Link",
            "options": "Supplier"
        },
        {
            "fieldname": "mode_of_payment",
            "label": __("Mode of Payment"),
            "fieldtype": "Link",
            "options": "Mode of Payment"
        },
        {
            "fieldname": "remittance_bank",
            "label": __("Bank Account"),
            "fieldtype": "Link",
            "options": "Bank Account",
            "get_query": function() {
                return {
                    filters: {
                        "company": frappe.query_report.get_filter_value('company')
                    }
                };
            }
        },
        {
            "fieldname": "payment_currency",
            "label": __("Currency"),
            "fieldtype": "Link",
            "options": "Currency"
        },
        {
            "fieldname": "cost_center",
            "label": __("Cost Center"),
            "fieldtype": "Link",
            "options": "Cost Center",
            "get_query": function() {
                return {
                    filters: {
                        "company": frappe.query_report.get_filter_value('company'),
                        "is_group": 0
                    }
                };
            }
        },
        {
            "fieldname": "project",
            "label": __("Project"),
            "fieldtype": "Link",
            "options": "Project"
        },
        {
            "fieldname": "min_amount",
            "label": __("Min Amount"),
            "fieldtype": "Currency"
        },
        {
            "fieldname": "max_amount",
            "label": __("Max Amount"),
            "fieldtype": "Currency"
        }
    ],
    
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        // Color code payment status
        if (column.fieldname == "payment_status") {
            if (value && value.includes("Completed")) {
                value = `<span class="indicator-pill green">${value}</span>`;
            } else if (value && value.includes("Pending")) {
                value = `<span class="indicator-pill orange">${value}</span>`;
            } else if (value && value.includes("Cancelled") || value && value.includes("Rejected")) {
                value = `<span class="indicator-pill red">${value}</span>`;
            } else if (value && value.includes("Approved")) {
                value = `<span class="indicator-pill blue">${value}</span>`;
            }
        }
        
        // Highlight large amounts
        if (column.fieldname == "local_currency_amount" || column.fieldname == "amount") {
            if (data && data.local_currency_amount > 1000000) {
                value = `<span style="color: #d32f2f; font-weight: bold;">${value}</span>`;
            }
        }
        
        return value;
    },
    
    "onload": function(report) {
        // Add custom buttons
        report.page.add_inner_button(__("Export to Excel"), function() {
            export_to_excel(report);
        });
        
        report.page.add_inner_button(__("Send Notifications"), function() {
            send_bulk_notifications(report);
        });
        
        report.page.add_inner_button(__("Print Vouchers"), function() {
            print_bulk_vouchers(report);
        });
    }
};


function export_to_excel(report) {
    let filters = report.get_filter_values();
    
    frappe.call({
        method: 'general.general_biz_apps.doctype.payments.payment_utils.export_payments_report',
        args: {
            filters: filters
        },
        callback: function(r) {
            frappe.show_alert({
                message: __('Export started. Download will begin shortly.'),
                indicator: 'green'
            }, 3);
        }
    });
}


function send_bulk_notifications(report) {
    let selected = report.get_checked_items();
    
    if (selected.length === 0) {
        frappe.msgprint(__('Please select payments to notify'));
        return;
    }
    
    let d = new frappe.ui.Dialog({
        title: __('Send Notifications'),
        fields: [
            {
                fieldname: 'notification_type',
                label: __('Notification Type'),
                fieldtype: 'Select',
                options: ['Confirmation', 'Reminder', 'Status Update'],
                reqd: 1
            },
            {
                fieldname: 'message',
                label: __('Additional Message'),
                fieldtype: 'Text'
            }
        ],
        primary_action_label: __('Send'),
        primary_action: function(values) {
            frappe.call({
                method: 'general.general_biz_apps.doctype.payments.payment_utils.send_bulk_notifications',
                args: {
                    payment_names: selected.map(x => x.name),
                    notification_type: values.notification_type,
                    message: values.message
                },
                callback: function() {
                    frappe.show_alert(__('Notifications sent successfully'), 3);
                    d.hide();
                }
            });
        }
    });
    
    d.show();
}


function print_bulk_vouchers(report) {
    let selected = report.get_checked_items();
    
    if (selected.length === 0) {
        frappe.msgprint(__('Please select payments to print'));
        return;
    }
    
    frappe.confirm(
        __('Print {0} payment vouchers?', [selected.length]),
        function() {
            selected.forEach(function(item) {
                let w = window.open(
                    frappe.urllib.get_full_url(
                        `/api/method/frappe.utils.print_format.download_pdf?
                        doctype=Payments&name=${item.name}&format=Standard&no_letterhead=0`
                    )
                );
            });
        }
    );
}