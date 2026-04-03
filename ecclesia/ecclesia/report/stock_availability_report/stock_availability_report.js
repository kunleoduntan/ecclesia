// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt
/* eslint-disable */


frappe.query_reports["Stock Availability Report"] = {
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
            "fieldname": "warehouse",
            "label": __("Warehouse"),
            "fieldtype": "Link",
            "options": "Warehouse",
            "reqd": 1,
            "get_query": function() {
                let company = frappe.query_report.get_filter_value('company');
                return {
                    filters: {
                        'company': company,
                        'is_group': 0,
                        'disabled': 0
                    }
                };
            }
        },
        {
            "fieldname": "report_date",
            "label": __("Report Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname": "criterion",
            "label": __("Criterion"),
            "fieldtype": "Select",
            "options": "Availability\nReorder Level",
            "default": "Availability",
            "reqd": 1,
            "description": __("<b>Availability:</b> Show all items in stock | <b>Reorder Level:</b> Show only items below reorder level")
        },
        {
            "fieldname": "item_group",
            "label": __("Item Group"),
            "fieldtype": "Link",
            "options": "Item Group"
        }
    ],

    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        // Color code Stock Status
        if (column.fieldname == "stock_status") {
            if (value && value.includes("Critical")) {
                value = `<span style="color: #DC2626; font-weight: 600;">⚠️ ${value}</span>`;
            } else if (value && value.includes("Below Reorder")) {
                value = `<span style="color: #F59E0B; font-weight: 600;">⚡ ${value}</span>`;
            } else if (value && value.includes("Adequate")) {
                value = `<span style="color: #10B981; font-weight: 600;">✓ ${value}</span>`;
            }
        }

        // Color code Urgency
        if (column.fieldname == "urgency") {
            if (value && value.includes("High")) {
                value = `<span style="color: #DC2626; font-weight: 600; background: #FEE2E2; padding: 3px 8px; border-radius: 4px;">🔴 ${value}</span>`;
            } else if (value && value.includes("Medium")) {
                value = `<span style="color: #F59E0B; font-weight: 600; background: #FEF3C7; padding: 3px 8px; border-radius: 4px;">🟡 ${value}</span>`;
            } else if (value && value.includes("Low")) {
                value = `<span style="color: #10B981; font-weight: 600; background: #D1FAE5; padding: 3px 8px; border-radius: 4px;">🟢 ${value}</span>`;
            }
        }

        // Highlight reorder quantities
        if (column.fieldname == "reorder_qty" && data && data.reorder_qty > 0) {
            value = `<span style="color: #DC2626; font-weight: 600;">${value}</span>`;
        }

        // Highlight reorder amounts
        if (column.fieldname == "reorder_amount" && data && data.reorder_amount > 0) {
            value = `<span style="color: #DC2626; font-weight: 600;">${value}</span>`;
        }

        // Color code quantities based on reorder level
        if (column.fieldname == "qty" && data) {
            let qty = parseFloat(data.qty || 0);
            let reorder_level = parseFloat(data.reorder_level || 0);
            let safety_stock = parseFloat(data.safety_stock || 0);

            if (safety_stock > 0 && qty <= safety_stock) {
                value = `<span style="color: #DC2626; font-weight: 600;">${value}</span>`;
            } else if (reorder_level > 0 && qty < reorder_level) {
                value = `<span style="color: #F59E0B; font-weight: 600;">${value}</span>`;
            }
        }

        return value;
    },

    "onload": function(report) {
        // Add custom buttons
        report.page.add_inner_button(__('Create Material Request'), function() {
            create_material_request_from_report();
        }, __('Actions'));

        report.page.add_inner_button(__('Export to Excel'), function() {
            export_report_to_excel();
        }, __('Actions'));

        report.page.add_inner_button(__('Email Report'), function() {
            email_report();
        }, __('Actions'));
    }
};


// Custom functions

function create_material_request_from_report() {
    let filters = frappe.query_report.get_filter_values();
    let data = frappe.query_report.data;

    if (!data || data.length === 0) {
        frappe.msgprint({
            title: __('No Data'),
            message: __('No items to create Material Request'),
            indicator: 'orange'
        });
        return;
    }

    // Count items that need reordering
    let items_to_reorder = data.filter(d => {
        return parseFloat(d.reorder_qty || 0) > 0;
    });

    if (items_to_reorder.length === 0) {
        frappe.msgprint({
            title: __('No Items to Reorder'),
            message: __('All items are at or above their reorder levels'),
            indicator: 'blue'
        });
        return;
    }

    frappe.confirm(
        __('Create Material Request for <b>{0} item(s)</b> below reorder level?', [items_to_reorder.length]),
        function() {
            // Create Material Request
            let mr = frappe.model.get_new_doc('Material Request');
            mr.material_request_type = 'Purchase';
            mr.company = filters.company;
            mr.schedule_date = frappe.datetime.add_days(frappe.datetime.get_today(), 7);

            items_to_reorder.forEach(function(item) {
                let reorder_qty = parseFloat(item.reorder_qty || 0);
                if (item.minimum_order_qty && reorder_qty > 0) {
                    reorder_qty = Math.max(reorder_qty, parseFloat(item.minimum_order_qty));
                }

                if (reorder_qty > 0) {
                    let child = frappe.model.add_child(mr, 'items');
                    child.item_code = item.item_code;
                    child.qty = reorder_qty;
                    child.warehouse = filters.warehouse;
                    child.schedule_date = mr.schedule_date;
                    child.uom = item.uom;
                }
            });

            frappe.set_route('Form', 'Material Request', mr.name);
            frappe.show_alert({
                message: __('Material Request created with {0} items', [items_to_reorder.length]),
                indicator: 'green'
            }, 5);
        }
    );
}


function export_report_to_excel() {
    let filters = frappe.query_report.get_filter_values();

    if (!filters.company || !filters.warehouse) {
        frappe.msgprint({
            title: __('Missing Filters'),
            message: __('Please select Company and Warehouse'),
            indicator: 'orange'
        });
        return;
    }

    frappe.msgprint({
        title: __('Coming Soon'),
        message: __('Excel export functionality will be available in the next update'),
        indicator: 'blue'
    });
}


function email_report() {
    let filters = frappe.query_report.get_filter_values();
    let data = frappe.query_report.data;

    if (!data || data.length === 0) {
        frappe.msgprint({
            title: __('No Data'),
            message: __('No data to email'),
            indicator: 'orange'
        });
        return;
    }

    let d = new frappe.ui.Dialog({
        title: __('Email Stock Availability Report'),
        fields: [
            {
                label: __('Recipients'),
                fieldname: 'recipients',
                fieldtype: 'Small Text',
                reqd: 1,
                description: __('Email addresses separated by commas')
            },
            {
                label: __('CC'),
                fieldname: 'cc',
                fieldtype: 'Small Text',
                description: __('CC email addresses separated by commas')
            },
            {
                label: __('Subject'),
                fieldname: 'subject',
                fieldtype: 'Data',
                reqd: 1,
                default: `Stock Availability Report - ${filters.warehouse} (${filters.report_date})`
            },
            {
                label: __('Message'),
                fieldname: 'message',
                fieldtype: 'Text Editor',
                reqd: 1,
                default: `<p>Please find attached the Stock Availability Report for ${filters.warehouse} as of ${filters.report_date}.</p>`
            }
        ],
        primary_action_label: __('Send Email'),
        primary_action(values) {
            frappe.msgprint({
                title: __('Coming Soon'),
                message: __('Email functionality will be available in the next update'),
                indicator: 'blue'
            });
            d.hide();
        }
    });

    d.show();
}