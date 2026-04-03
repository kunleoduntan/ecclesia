// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt

// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

frappe.ui.form.on('Fixed Asset Maintenance', {
    refresh: function(frm) {
        add_maintenance_buttons(frm);
        set_maintenance_indicators(frm);
        show_maintenance_history(frm);
        setup_maintenance_filters(frm);
    },
    
    onload: function(frm) {
        setup_maintenance_filters(frm);
        
        if (frm.is_new() && !frm.doc.status) {
            frm.set_value('status', 'Scheduled');
        }
    },
    
    asset: function(frm) {
        if (frm.doc.asset) {
            fetch_asset_details(frm);
        }
    },
    
    maintenance_cost: function(frm) {
        calculate_total_cost(frm);
    },
    
    parts_cost: function(frm) {
        calculate_total_cost(frm);
    },
    
    labor_cost: function(frm) {
        calculate_total_cost(frm);
    },
    
    is_scheduled: function(frm) {
        toggle_scheduling_fields(frm);
        if (frm.doc.is_scheduled && !frm.doc.next_maintenance_date) {
            calculate_next_maintenance_date(frm);
        }
    },
    
    frequency: function(frm) {
        if (frm.doc.is_scheduled) {
            calculate_next_maintenance_date(frm);
        }
    },
    
    maintenance_date: function(frm) {
        if (frm.doc.is_scheduled) {
            calculate_next_maintenance_date(frm);
        }
    },
    
    completion_date: function(frm) {
        if (frm.doc.completion_date && frm.doc.is_scheduled) {
            calculate_next_maintenance_date(frm);
        }
    },
    
    status: function(frm) {
        if (frm.doc.status === 'Completed' && !frm.doc.completion_date) {
            frm.set_value('completion_date', frappe.datetime.now_datetime());
        }
        
        if (frm.doc.status === 'Completed' && !frm.doc.completed_by) {
            frm.set_value('completed_by', frappe.session.user);
        }
    }
});

function add_maintenance_buttons(frm) {
    if (frm.doc.docstatus === 1) {
        // Mark as complete
        if (frm.doc.status === 'In Progress' || frm.doc.status === 'Scheduled') {
            frm.add_custom_button(__('Mark as Completed'), function() {
                mark_maintenance_completed(frm);
            }, __('Actions')).addClass('btn-primary');
        }
        
        // Create journal entry
        if (!frm.doc.journal_entry && frm.doc.total_cost > 0 && frm.doc.create_journal_entry) {
            frm.add_custom_button(__('Create Payment Entry'), function() {
                create_maintenance_payment(frm);
            }, __('Create'));
        }
        
        // View asset
        frm.add_custom_button(__('View Asset'), function() {
            frappe.set_route('Form', 'Fixed Asset', frm.doc.asset);
        }, __('View'));
        
        // Schedule next maintenance
        if (frm.doc.is_scheduled && frm.doc.status === 'Completed') {
            frm.add_custom_button(__('Schedule Next Maintenance'), function() {
                schedule_next_maintenance_manual(frm);
            }, __('Create'));
        }
    }
    
    // Maintenance history
    if (frm.doc.asset) {
        frm.add_custom_button(__('Maintenance History'), function() {
            show_maintenance_history_dialog(frm);
        }, __('View'));
    }
}

function set_maintenance_indicators(frm) {
    let indicators = {
        'Scheduled': 'blue',
        'In Progress': 'orange',
        'Completed': 'green',
        'Pending Parts': 'yellow',
        'Cancelled': 'red'
    };
    
    if (frm.doc.status) {
        frm.page.set_indicator(frm.doc.status, indicators[frm.doc.status] || 'gray');
    }
    
    // Add deadline warning
    if (frm.doc.next_maintenance_date && frm.doc.is_scheduled) {
        let days_until = frappe.datetime.get_day_diff(frm.doc.next_maintenance_date, frappe.datetime.get_today());
        
        if (days_until <= 7 && days_until >= 0) {
            frm.dashboard.add_comment(
                __('Next maintenance due in {0} days', [days_until]),
                'orange',
                true
            );
        } else if (days_until < 0) {
            frm.dashboard.add_comment(
                __('Maintenance overdue by {0} days', [Math.abs(days_until)]),
                'red',
                true
            );
        }
    }
}

function fetch_asset_details(frm) {
    frappe.call({
        method: 'frappe.client.get_value',
        args: {
            doctype: 'Fixed Asset',
            filters: {name: frm.doc.asset},
            fieldname: ['asset_name', 'asset_code', 'asset_category', 'current_location', 'cost_center']
        },
        callback: function(r) {
            if (r.message) {
                frm.set_value('asset_name', r.message.asset_name);
                
                if (!frm.doc.cost_center && r.message.cost_center) {
                    frm.set_value('cost_center', r.message.cost_center);
                }
                
                frappe.show_alert({
                    message: __('Asset details loaded'),
                    indicator: 'green'
                });
            }
        }
    });
}

function calculate_total_cost(frm) {
    let total = flt(frm.doc.maintenance_cost) + flt(frm.doc.parts_cost) + flt(frm.doc.labor_cost);
    frm.set_value('total_cost', total);
}

function toggle_scheduling_fields(frm) {
    let show = frm.doc.is_scheduled ? 1 : 0;
    
    frm.toggle_display('frequency', show);
    frm.toggle_display('next_maintenance_date', show);
    frm.toggle_display('maintenance_reminder_days', show);
    
    frm.set_df_property('frequency', 'reqd', show);
}

function calculate_next_maintenance_date(frm) {
    if (!frm.doc.frequency) return;
    
    let base_date = frm.doc.completion_date || frm.doc.maintenance_date;
    
    if (!base_date) return;
    
    let frequency_days = {
        'Weekly': 7,
        'Bi-Weekly': 14,
        'Monthly': 30,
        'Quarterly': 90,
        'Half-Yearly': 180,
        'Annual': 365,
        'Bi-Annual': 730
    };
    
    let days = frequency_days[frm.doc.frequency] || 30;
    let next_date = frappe.datetime.add_days(base_date, days);
    
    frm.set_value('next_maintenance_date', next_date);
}

function mark_maintenance_completed(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Complete Maintenance'),
        fields: [
            {
                fieldname: 'completion_date',
                fieldtype: 'Datetime',
                label: __('Completion Date'),
                reqd: 1,
                default: frappe.datetime.now_datetime()
            },
            {
                fieldname: 'completed_by',
                fieldtype: 'Link',
                label: __('Completed By'),
                options: 'User',
                reqd: 1,
                default: frappe.session.user
            },
            {
                fieldname: 'work_performed',
                fieldtype: 'Text',
                label: __('Work Performed'),
                reqd: 1
            },
            {
                fieldname: 'parts_replaced',
                fieldtype: 'Text',
                label: __('Parts Replaced')
            },
            {
                fieldname: 'post_maintenance_condition',
                fieldtype: 'Select',
                label: __('Asset Condition After Maintenance'),
                options: 'Excellent\nGood\nFair\nRequires Further Attention',
                reqd: 1,
                default: 'Good'
            },
            {
                fieldname: 'downtime_hours',
                fieldtype: 'Float',
                label: __('Downtime (Hours)'),
                precision: 2
            }
        ],
        primary_action_label: __('Complete'),
        primary_action: function(values) {
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.fixed_asset_maintenance.fixed_asset_maintenance.mark_maintenance_completed',
                args: {
                    maintenance_name: frm.doc.name,
                    completion_details: values
                },
                callback: function(r) {
                    if (r.message) {
                        frm.reload_doc();
                        frappe.show_alert({
                            message: __('Maintenance marked as completed'),
                            indicator: 'green'
                        });
                    }
                }
            });
            d.hide();
        }
    });
    d.show();
}

function create_maintenance_payment(frm) {
    frappe.confirm(
        __('Create Journal Entry for maintenance cost of {0}?', [format_currency(frm.doc.total_cost)]),
        function() {
            frm.save().then(() => {
                frm.call('create_maintenance_journal_entry').then(() => {
                    frm.reload_doc();
                });
            });
        }
    );
}

function schedule_next_maintenance_manual(frm) {
    frappe.call({
        method: 'schedule_next_maintenance',
        doc: frm.doc,
        callback: function(r) {
            frm.reload_doc();
            frappe.show_alert({
                message: __('Next maintenance scheduled'),
                indicator: 'green'
            });
        }
    });
}

function show_maintenance_history(frm) {
    if (!frm.doc.asset || !frm.doc.docstatus) return;
    
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.fixed_asset_maintenance.fixed_asset_maintenance.get_asset_maintenance_history',
        args: {
            asset: frm.doc.asset
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                display_maintenance_history(frm, r.message);
            }
        }
    });
}

function display_maintenance_history(frm, history) {
    let html = '<div class="maintenance-history"><h5>' + __('Recent Maintenance (Last 5)') + '</h5>';
    html += '<table class="table table-bordered table-sm"><thead><tr>';
    html += '<th>' + __('Date') + '</th><th>' + __('Type') + '</th><th>' + __('Status') + '</th><th>' + __('Cost') + '</th>';
    html += '</tr></thead><tbody>';
    
    $.each(history.slice(0, 5), function(i, record) {
        let status_class = record.status === 'Completed' ? 'green' : 'orange';
        html += `<tr>
            <td><a href="/app/fixed-asset-maintenance/${record.name}">${frappe.datetime.str_to_user(record.maintenance_date)}</a></td>
            <td>${record.maintenance_type}</td>
            <td><span class="indicator ${status_class}">${record.status}</span></td>
            <td>${format_currency(record.total_cost)}</td>
        </tr>`;
    });
    
    html += '</tbody></table></div>';
    
    frm.dashboard.add_section(html, __('Maintenance History'));
}

function show_maintenance_history_dialog(frm) {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.fixed_asset_maintenance.fixed_asset_maintenance.get_asset_maintenance_history',
        args: {
            asset: frm.doc.asset
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                let html = '<div style="max-height: 500px; overflow-y: auto;">';
                html += '<table class="table table-bordered"><thead><tr>';
                html += '<th>Date</th><th>Type</th><th>Status</th><th>Cost</th><th>Condition</th><th>Work Done</th><th>Downtime</th>';
                html += '</tr></thead><tbody>';
                
                $.each(r.message, function(i, record) {
                    html += `<tr>
                        <td><a href="/app/fixed-asset-maintenance/${record.name}">${frappe.datetime.str_to_user(record.maintenance_date)}</a></td>
                        <td>${record.maintenance_type}</td>
                        <td>${record.status}</td>
                        <td>${format_currency(record.total_cost)}</td>
                        <td>${record.post_maintenance_condition || '-'}</td>
                        <td>${record.work_performed || '-'}</td>
                        <td>${record.downtime_hours ? record.downtime_hours + ' hrs' : '-'}</td>
                    </tr>`;
                });
                
                html += '</tbody></table></div>';
                
                frappe.msgprint({
                    title: __('Complete Maintenance History - {0}', [frm.doc.asset_name]),
                    message: html,
                    wide: true
                });
            } else {
                frappe.msgprint(__('No maintenance history found for this asset'));
            }
        }
    });
}

function setup_maintenance_filters(frm) {
    frm.set_query('asset', function() {
        return {
            filters: {
                'docstatus': 1,
                'asset_status': ['not in', ['Disposed', 'Cancelled']],
                'company': frm.doc.company
            }
        };
    });
    
    frm.set_query('maintenance_provider', function() {
        return {
            filters: {
                'supplier_type': 'Service Provider'
            }
        };
    });
    
    frm.set_query('expense_account', function() {
        return {
            filters: {
                'company': frm.doc.company,
                'account_type': 'Expense Account',
                'is_group': 0
            }
        };
    });
    
    frm.set_query('cost_center', function() {
        return {
            filters: {
                'company': frm.doc.company,
                'is_group': 0
            }
        };
    });
}

// Helper function
function format_currency(value) {
    return frappe.format(value, {fieldtype: 'Currency'});
}