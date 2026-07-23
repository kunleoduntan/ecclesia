// ecclesia/public/js/data_breach_register_list.js

frappe.listview_settings['Data Breach Register'] = {
    add_fields: [
        "name", "breach_title", "breach_type", "severity", "breach_date",
        "data_subjects_affected", "status", "nitda_notified", "dpo_sign_off"
    ],

    get_indicator: function(doc) {
        if (doc.severity === "Critical")
            return [__("Critical"), "red", "severity,=,Critical"];
        if (doc.severity === "High")
            return [__("High"), "orange", "severity,=,High"];
        if (doc.severity === "Medium")
            return [__("Medium"), "yellow", "severity,=,Medium"];
        if (doc.severity === "Low")
            return [__("Low"), "green", "severity,=,Low"];
        if (doc.status === "Closed")
            return [__("Closed"), "grey", "status,=,Closed"];
        return [__("Data Breach"), "red", "status,=,"];
    },

    formatters: {
        breach_title: function(v, doc) {
            return v ? `<span style="font-weight:600;color:#7c3aed;">
                <i class="fa fa-shield" style="color:#7c3aed;margin-right:6px;"></i>${v}
            </span>` : '';
        },
        severity: function(v) {
            if (!v) return '';
            const colors = {
                'Low': { bg: '#DCFCE7', text: '#166534', icon: 'fa-check-circle' },
                'Medium': { bg: '#FEF3C7', text: '#92400E', icon: 'fa-exclamation-circle' },
                'High': { bg: '#FEE2E2', text: '#991B1B', icon: 'fa-exclamation-triangle' },
                'Critical': { bg: '#FEF2F2', text: '#7F1D1D', icon: 'fa-bolt' }
            };
            const style = colors[v] || { bg: '#E2E8F0', text: '#1E293B', icon: 'fa-info-circle' };
            return `<span style="background:${style.bg};color:${style.text};padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600;">
                <i class="fa ${style.icon}" style="margin-right:5px;"></i>${v}
            </span>`;
        },
        status: function(v) {
            if (!v) return '';
            const colors = {
                'Reported': { bg: '#FEF3C7', text: '#92400E', icon: 'fa-flag' },
                'Investigating': { bg: '#DBEAFE', text: '#1E40AF', icon: 'fa-search' },
                'Contained': { bg: '#F3E8FF', text: '#6B21A8', icon: 'fa-check-circle' },
                'Remediated': { bg: '#DCFCE7', text: '#166534', icon: 'fa-check-double' },
                'Closed': { bg: '#F1F5F9', text: '#475569', icon: 'fa-check' }
            };
            const style = colors[v] || { bg: '#E2E8F0', text: '#1E293B', icon: 'fa-info-circle' };
            return `<span style="background:${style.bg};color:${style.text};padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600;">
                <i class="fa ${style.icon}" style="margin-right:5px;"></i>${v}
            </span>`;
        },
        nitda_notified: function(v) {
            return v 
                ? `<span style="color:#16a34a;font-weight:600;">✅ Notified</span>`
                : `<span style="color:#dc2626;font-weight:600;">⚠️ Pending</span>`;
        },
        breach_date: function(v) {
            if (!v) return '';
            let today = frappe.datetime.get_today();
            let diff = frappe.datetime.get_diff(v, today);
            let color = diff < 0 ? '#dc2626' : '#475569';
            return `<span style="color:${color};">
                <i class="fa fa-calendar" style="margin-right:5px;"></i>${frappe.datetime.str_to_user(v)}
            </span>`;
        }
    },

    onload: function(listview) {
        window._breach_listview = listview;
        setTimeout(() => {
            add_breach_styles();
            add_breach_summary_cards(listview);
            add_breach_quick_filters(listview);
        }, 300);
        add_breach_export_options(listview);
    },

    refresh: function(listview) {
        window._breach_listview = listview;
        setTimeout(() => {
            update_breach_summary_cards(listview);
            update_breach_filter_counts();
        }, 200);
    },

    primary_action: () => frappe.new_doc("Data Breach Register"),

    button: {
        show: (doc) => doc.name,
        get_label: () => __('Actions'),
        get_description: () => __('Quick Actions'),
        action: (doc) => show_breach_row_actions(doc)
    },

    colwidths: {
        "breach_title": 200, "breach_type": 160, "severity": 120,
        "breach_date": 120, "data_subjects_affected": 120,
        "status": 140, "nitda_notified": 120, "dpo_sign_off": 150
    }
};

function show_breach_row_actions(doc) {
    const actions = [
        { label: '📄 View Breach', action: () => frappe.set_route('Form', 'Data Breach Register', doc.name) },
        { label: '📤 Notify NITDA', action: () => notify_nitda(doc) },
        { label: '📋 View Incident', action: () => frappe.set_route('Form', 'Compliance Incident', doc.compliance_incident_ref) },
        { label: '🔍 View DPR', action: () => frappe.set_route('Form', 'Data Processing Record', doc.related_data_processing_record) }
    ];
    show_actions_menu(actions);
}

function notify_nitda(doc) {
    if (doc.nitda_notified) {
        frappe.msgprint(__('This breach has already been notified to NITDA.'));
        return;
    }
    
    const dialog = new frappe.ui.Dialog({
        title: __('Notify NITDA'),
        fields: [
            {
                fieldname: 'notification_date',
                label: __('Notification Date'),
                fieldtype: 'Date',
                default: frappe.datetime.get_today(),
                reqd: 1
            },
            {
                fieldname: 'notification_reference',
                label: __('NITDA Reference Number'),
                fieldtype: 'Data'
            }
        ],
        primary_action: function(values) {
            frappe.call({
                method: 'frappe.client.set_value',
                args: {
                    doctype: 'Data Breach Register',
                    name: doc.name,
                    fieldname: {
                        nitda_notified: 1,
                        nitda_notification_date: values.notification_date,
                        nitda_notification_reference: values.notification_reference
                    }
                },
                callback: function() {
                    dialog.hide();
                    frappe.show_alert({message: __('NITDA notified successfully'), indicator: 'green'});
                    window._breach_listview?.refresh();
                }
            });
        }
    });
    dialog.show();
}

function show_actions_menu(actions) {
    const menu_html = actions.map(a => 
        `<div class="action-item" style="padding:12px 16px;cursor:pointer;border-radius:8px;display:flex;align-items:center;gap:10px;transition:all .2s;font-size:13px;color:#374151;">
            <span>${a.label}</span>
        </div>`
    ).join('');
    
    const dialog = new frappe.ui.Dialog({
        title: __('Quick Actions'),
        fields: [{ fieldtype: 'HTML', fieldname: 'actions_html', options: `<div style="padding:8px;">${menu_html}</div>` }]
    });
    
    dialog.show();
    
    dialog.$wrapper.find('.action-item').each(function(i) {
        $(this).on('click', () => { actions[i].action(); dialog.hide(); });
        $(this).hover(
            function() { $(this).css('background', '#eff6ff').css('color', '#1e40af'); },
            function() { $(this).css('background', 'transparent').css('color', '#374151'); }
        );
    });
}

function add_breach_styles() {
    if ($('#breach-styles').length) return;
    $('head').append(`
        <style id="breach-styles">
        .list-row {
            transition: all .25s ease !important;
            border-left: 4px solid transparent !important;
            border-radius: 8px !important;
            margin: 2px 0 !important;
        }
        .list-row:hover {
            background: linear-gradient(90deg, #f5f3ff, #ede9fe) !important;
            border-left-color: #7c3aed !important;
            transform: translateX(3px);
        }
        .list-headers {
            background: linear-gradient(135deg, #5B21B6, #8B5CF6) !important;
            color: #fff !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            font-size: 11px !important;
            letter-spacing: .8px !important;
            padding: 14px 16px !important;
            border-radius: 12px !important;
        }
        .breach-summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 12px;
            padding: 15px;
            margin: 15px;
            background: #fff;
            border-radius: 16px;
            box-shadow: 0 4px 16px rgba(0,0,0,.06);
        }
        .summary-card {
            padding: 16px 12px;
            border-radius: 12px;
            text-align: center;
            border: 2px solid transparent;
            transition: all .3s ease;
            cursor: default;
        }
        .summary-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,.12); }
        .summary-card.total {
            background: linear-gradient(135deg, #f5f3ff, #ede9fe);
            border-color: #c4b5fd;
        }
        .summary-card.total .summary-card-label { color: #5b21b6; }
        .summary-card.total .summary-card-value { color: #5b21b6; }
        .summary-card.critical {
            background: linear-gradient(135deg, #fef2f2, #fee2e2);
            border-color: #fca5a5;
        }
        .summary-card.critical .summary-card-label { color: #b91c1c; }
        .summary-card.critical .summary-card-value { color: #991b1b; }
        .summary-card.high {
            background: linear-gradient(135deg, #fef3c7, #fde68a);
            border-color: #fcd34d;
        }
        .summary-card.high .summary-card-label { color: #b45309; }
        .summary-card.high .summary-card-value { color: #92400e; }
        .summary-card.notified {
            background: linear-gradient(135deg, #ecfdf5, #d1fae5);
            border-color: #6ee7b7;
        }
        .summary-card.notified .summary-card-label { color: #047857; }
        .summary-card.notified .summary-card-value { color: #065f46; }
        .summary-card-label {
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: .8px;
            font-weight: 700;
            margin-bottom: 4px;
        }
        .summary-card-value {
            font-size: 22px;
            font-weight: 800;
        }
        .breach-filters {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            padding: 14px 16px;
            margin: 0 15px 12px;
            background: #fff;
            border-radius: 14px;
            box-shadow: 0 2px 8px rgba(0,0,0,.04);
        }
        .filter-chip {
            padding: 8px 16px;
            border-radius: 24px;
            border: 2px solid #e5e7eb;
            cursor: pointer;
            font-size: 12px;
            font-weight: 500;
            display: flex;
            gap: 7px;
            align-items: center;
            transition: all .25s ease;
            background: #fff;
            color: #475569;
        }
        .filter-chip:hover {
            border-color: #8b5cf6;
            background: #f5f3ff;
            transform: translateY(-2px);
        }
        .filter-chip.active {
            background: linear-gradient(135deg, #5B21B6, #8B5CF6);
            color: #fff;
            border-color: #8B5CF6;
            box-shadow: 0 4px 14px rgba(139,92,246,.3);
            font-weight: 600;
        }
        .filter-chip .count {
            background: rgba(255,255,255,.25);
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: 700;
        }
        .filter-chip.active .count {
            background: rgba(255,255,255,.35);
        }
        </style>
    `);
}

function add_breach_summary_cards(listview) {
    $('.breach-summary').remove();
    const pageContent = listview.page.wrapper.find('.page-content');
    if (!pageContent.length) return;
    
    pageContent.prepend(`
        <div class="breach-summary">
            <div class="summary-card total">
                <div class="summary-card-label">📋 Total Breaches</div>
                <div class="summary-card-value" id="breach-total">0</div>
            </div>
            <div class="summary-card critical">
                <div class="summary-card-label">🚨 Critical</div>
                <div class="summary-card-value" id="breach-critical">0</div>
            </div>
            <div class="summary-card high">
                <div class="summary-card-label">⚠️ High</div>
                <div class="summary-card-value" id="breach-high">0</div>
            </div>
            <div class="summary-card notified">
                <div class="summary-card-label">✅ NITDA Notified</div>
                <div class="summary-card-value" id="breach-notified">0</div>
            </div>
        </div>
    `);
    update_breach_summary_cards(listview);
}

function update_breach_summary_cards(listview) {
    let filters = {};
    try {
        const current = listview.filter_area?.get() || [];
        current.forEach(f => { if (f[0] === 'Data Breach Register') filters[f[1]] = f[3]; });
    } catch (e) {}
    
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.data_breach_register.data_breach_register_list.get_breach_summary',
        args: { filters: filters },
        callback(r) {
            if (!r.message) return;
            const d = r.message;
            $('#breach-total').text(d.total_count || 0);
            $('#breach-critical').text(d.critical_count || 0);
            $('#breach-high').text(d.high_count || 0);
            $('#breach-notified').text(d.notified_count || 0);
        }
    });
}

function add_breach_quick_filters(listview) {
    $('.breach-filters').remove();
    
    const filters = [
        ['all', 'fa-list', 'All'],
        ['critical', 'fa-bolt', 'Critical'],
        ['high', 'fa-exclamation-triangle', 'High'],
        ['notified', 'fa-check-circle', 'NITDA Done'],
        ['pending', 'fa-clock-o', 'Pending']
    ];
    
    const chips = filters.map(([id, icon, label]) => `
        <div class="filter-chip ${id === 'all' ? 'active' : ''}"
            data-filter="${id}"
            onclick="applyBreachFilter('${id}', this)">
            <i class="fa ${icon}"></i> ${label}
            <span class="count">0</span>
        </div>
    `).join('');
    
    const pageContent = listview.page.wrapper.find('.page-content');
    pageContent.prepend(`<div class="breach-filters">${chips}</div>`);
    update_breach_filter_counts();
}

window.applyBreachFilter = function(filter, el) {
    const listview = window._breach_listview || cur_list;
    if (!listview) return;
    
    $('.filter-chip').removeClass('active');
    $(el).addClass('active');
    
    try {
        listview.filter_area.clear();
    } catch(e) {
        if (listview.filter_area.filter_list) {
            listview.filter_area.filter_list.forEach(f => listview.filter_area.remove(f));
        }
    }
    
    if (filter === 'critical') {
        listview.filter_area.add('Data Breach Register', 'severity', '=', 'Critical');
    } else if (filter === 'high') {
        listview.filter_area.add('Data Breach Register', 'severity', '=', 'High');
    } else if (filter === 'notified') {
        listview.filter_area.add('Data Breach Register', 'nitda_notified', '=', '1');
    } else if (filter === 'pending') {
        listview.filter_area.add('Data Breach Register', 'nitda_notified', '=', '0');
    }
    
    listview.refresh();
};

function update_breach_filter_counts() {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.data_breach_register.data_breach_register_list.get_breach_summary',
        callback(r) {
            if (!r.message) return;
            const d = r.message;
            document.querySelector('.filter-chip[data-filter="all"] .count').textContent = d.total_count || 0;
            document.querySelector('.filter-chip[data-filter="critical"] .count').textContent = d.critical_count || 0;
            document.querySelector('.filter-chip[data-filter="high"] .count').textContent = d.high_count || 0;
            document.querySelector('.filter-chip[data-filter="notified"] .count').textContent = d.notified_count || 0;
            document.querySelector('.filter-chip[data-filter="pending"] .count').textContent = d.pending_count || 0;
        }
    });
}

function add_breach_export_options(listview) {
    listview.page.add_menu_item(__('📊 Export to Excel'), () => {
        let filters = {};
        try {
            const current = listview.filter_area?.get() || [];
            current.forEach(f => { if (f[0] === 'Data Breach Register') filters[f[1]] = f[3]; });
        } catch (e) {}
        const url = '/api/method/ecclesia.ecclesia.doctype.data_breach_register.data_breach_register_list.export_breach_excel';
        window.open(url + '?filters=' + encodeURIComponent(JSON.stringify(filters)), '_blank');
    });
}