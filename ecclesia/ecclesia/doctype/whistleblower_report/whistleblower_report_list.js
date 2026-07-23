// ecclesia/public/js/whistleblower_report_list.js

frappe.listview_settings['Whistleblower Report'] = {
    add_fields: [
        "name", "report_code", "report_category", "severity", "received_date",
        "status", "is_anonymous", "assigned_investigator", "outcome"
    ],

    get_indicator: function(doc) {
        if (doc.status === "Closed — Substantiated")
            return [__("Substantiated"), "red", "status,=,Closed — Substantiated"];
        if (doc.status === "Closed — Unsubstantiated")
            return [__("Unsubstantiated"), "green", "status,=,Closed — Unsubstantiated"];
        if (doc.status === "Escalated")
            return [__("Escalated"), "red", "status,=,Escalated"];
        if (doc.status === "Under Investigation")
            return [__("Investigating"), "orange", "status,=,Under Investigation"];
        if (doc.status === "Received")
            return [__("Received"), "blue", "status,=,Received"];
        return [__("Whistleblower"), "grey", "status,=,"];
    },

    formatters: {
        report_code: function(v, doc) {
            return v ? `<span style="font-weight:600;color:#dc2626;">
                <i class="fa fa-shield" style="color:#dc2626;margin-right:6px;"></i>${v}
            </span>` : '';
        },
        status: function(v) {
            if (!v) return '';
            const colors = {
                'Received': { bg: '#DBEAFE', text: '#1E40AF', icon: 'fa-inbox' },
                'Under Investigation': { bg: '#FEF3C7', text: '#92400E', icon: 'fa-search' },
                'Escalated': { bg: '#FEE2E2', text: '#991B1B', icon: 'fa-arrow-up' },
                'Closed — Substantiated': { bg: '#FEE2E2', text: '#7F1D1D', icon: 'fa-check-circle' },
                'Closed — Unsubstantiated': { bg: '#DCFCE7', text: '#166534', icon: 'fa-check-circle' }
            };
            const style = colors[v] || { bg: '#E2E8F0', text: '#1E293B', icon: 'fa-info-circle' };
            return `<span style="background:${style.bg};color:${style.text};padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600;">
                <i class="fa ${style.icon}" style="margin-right:5px;"></i>${v}
            </span>`;
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
        is_anonymous: function(v) {
            return v 
                ? `<span style="color:#7c3aed;font-weight:600;">🔒 Anonymous</span>`
                : `<span style="color:#64748b;">Identified</span>`;
        },
        received_date: function(v) {
            if (!v) return '';
            return `<span><i class="fa fa-calendar" style="margin-right:5px;"></i>${frappe.datetime.str_to_user(v)}</span>`;
        }
    },

    onload: function(listview) {
        window._wb_listview = listview;
        setTimeout(() => {
            add_wb_styles();
            add_wb_summary_cards(listview);
            add_wb_quick_filters(listview);
        }, 300);
        add_wb_export_options(listview);
    },

    refresh: function(listview) {
        window._wb_listview = listview;
        setTimeout(() => {
            update_wb_summary_cards(listview);
            update_wb_filter_counts();
        }, 200);
    },

    primary_action: () => frappe.new_doc("Whistleblower Report"),

    button: {
        show: (doc) => doc.name,
        get_label: () => __('Actions'),
        get_description: () => __('Quick Actions'),
        action: (doc) => show_wb_row_actions(doc)
    },

    colwidths: {
        "report_code": 140, "report_category": 160, "severity": 120,
        "received_date": 120, "status": 160, "is_anonymous": 120,
        "assigned_investigator": 150, "outcome": 150
    }
};

function show_wb_row_actions(doc) {
    const actions = [
        { label: '🔍 View Report', action: () => frappe.set_route('Form', 'Whistleblower Report', doc.name) },
        { label: '👤 Assign Investigator', action: () => assign_investigator(doc) },
        { label: '📋 View Incident', action: () => frappe.set_route('Form', 'Compliance Incident', doc.compliance_incident_ref) },
        { label: '📊 Update Status', action: () => update_wb_status(doc) }
    ];
    show_actions_menu(actions);
}

function assign_investigator(doc) {
    const dialog = new frappe.ui.Dialog({
        title: __('Assign Investigator'),
        fields: [
            {
                fieldname: 'investigator',
                label: __('Investigator'),
                fieldtype: 'Link',
                options: 'Employee',
                reqd: 1
            },
            {
                fieldname: 'investigation_start',
                label: __('Start Date'),
                fieldtype: 'Date',
                default: frappe.datetime.get_today()
            }
        ],
        primary_action: function(values) {
            frappe.call({
                method: 'frappe.client.set_value',
                args: {
                    doctype: 'Whistleblower Report',
                    name: doc.name,
                    fieldname: {
                        assigned_investigator: values.investigator,
                        investigation_start: values.investigation_start,
                        status: 'Under Investigation'
                    }
                },
                callback: function() {
                    dialog.hide();
                    frappe.show_alert({message: __('Investigator assigned'), indicator: 'green'});
                    window._wb_listview?.refresh();
                }
            });
        }
    });
    dialog.show();
}

function update_wb_status(doc) {
    const dialog = new frappe.ui.Dialog({
        title: __('Update Report Status'),
        fields: [
            {
                fieldname: 'status',
                label: __('Status'),
                fieldtype: 'Select',
                options: ['Received', 'Under Investigation', 'Escalated', 'Closed — Substantiated', 'Closed — Unsubstantiated'],
                default: doc.status
            },
            {
                fieldname: 'outcome',
                label: __('Outcome'),
                fieldtype: 'Select',
                options: ['', 'Pending', 'Substantiated — Action Taken', 'Substantiated — No Action', 'Unsubstantiated', 'Referred to Authority'],
                default: doc.outcome
            }
        ],
        primary_action: function(values) {
            frappe.call({
                method: 'frappe.client.set_value',
                args: {
                    doctype: 'Whistleblower Report',
                    name: doc.name,
                    fieldname: {
                        status: values.status,
                        outcome: values.outcome
                    }
                },
                callback: function() {
                    dialog.hide();
                    frappe.show_alert({message: __('Status updated'), indicator: 'green'});
                    window._wb_listview?.refresh();
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

function add_wb_styles() {
    if ($('#wb-styles').length) return;
    $('head').append(`
        <style id="wb-styles">
        .list-row {
            transition: all .25s ease !important;
            border-left: 4px solid transparent !important;
            border-radius: 8px !important;
            margin: 2px 0 !important;
        }
        .list-row:hover {
            background: linear-gradient(90deg, #fef2f2, #fee2e2) !important;
            border-left-color: #dc2626 !important;
            transform: translateX(3px);
        }
        .list-headers {
            background: linear-gradient(135deg, #991B1B, #DC2626) !important;
            color: #fff !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            font-size: 11px !important;
            letter-spacing: .8px !important;
            padding: 14px 16px !important;
            border-radius: 12px !important;
        }
        .wb-summary {
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
            background: linear-gradient(135deg, #fef2f2, #fee2e2);
            border-color: #fca5a5;
        }
        .summary-card.total .summary-card-label { color: #b91c1c; }
        .summary-card.total .summary-card-value { color: #991b1b; }
        .summary-card.investigating {
            background: linear-gradient(135deg, #fef3c7, #fde68a);
            border-color: #fcd34d;
        }
        .summary-card.investigating .summary-card-label { color: #b45309; }
        .summary-card.investigating .summary-card-value { color: #92400e; }
        .summary-card.substantiated {
            background: linear-gradient(135deg, #fef2f2, #fee2e2);
            border-color: #fca5a5;
        }
        .summary-card.substantiated .summary-card-label { color: #b91c1c; }
        .summary-card.substantiated .summary-card-value { color: #991b1b; }
        .summary-card.anonymous {
            background: linear-gradient(135deg, #f5f3ff, #ede9fe);
            border-color: #c4b5fd;
        }
        .summary-card.anonymous .summary-card-label { color: #5b21b6; }
        .summary-card.anonymous .summary-card-value { color: #5b21b6; }
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
        .wb-filters {
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
            border-color: #dc2626;
            background: #fef2f2;
            transform: translateY(-2px);
        }
        .filter-chip.active {
            background: linear-gradient(135deg, #991B1B, #DC2626);
            color: #fff;
            border-color: #DC2626;
            box-shadow: 0 4px 14px rgba(220,38,38,.3);
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

function add_wb_summary_cards(listview) {
    $('.wb-summary').remove();
    const pageContent = listview.page.wrapper.find('.page-content');
    if (!pageContent.length) return;
    
    pageContent.prepend(`
        <div class="wb-summary">
            <div class="summary-card total">
                <div class="summary-card-label">📋 Total Reports</div>
                <div class="summary-card-value" id="wb-total">0</div>
            </div>
            <div class="summary-card investigating">
                <div class="summary-card-label">🔍 Investigating</div>
                <div class="summary-card-value" id="wb-investigating">0</div>
            </div>
            <div class="summary-card substantiated">
                <div class="summary-card-label">🚨 Substantiated</div>
                <div class="summary-card-value" id="wb-substantiated">0</div>
            </div>
            <div class="summary-card anonymous">
                <div class="summary-card-label">🔒 Anonymous</div>
                <div class="summary-card-value" id="wb-anonymous">0</div>
            </div>
        </div>
    `);
    update_wb_summary_cards(listview);
}

function update_wb_summary_cards(listview) {
    let filters = {};
    try {
        const current = listview.filter_area?.get() || [];
        current.forEach(f => { if (f[0] === 'Whistleblower Report') filters[f[1]] = f[3]; });
    } catch (e) {}
    
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.whistleblower_report.whistleblower_report_list.get_wb_summary',
        args: { filters: filters },
        callback(r) {
            if (!r.message) return;
            const d = r.message;
            $('#wb-total').text(d.total_count || 0);
            $('#wb-investigating').text(d.investigating_count || 0);
            $('#wb-substantiated').text(d.substantiated_count || 0);
            $('#wb-anonymous').text(d.anonymous_count || 0);
        }
    });
}

function add_wb_quick_filters(listview) {
    $('.wb-filters').remove();
    
    const filters = [
        ['all', 'fa-list', 'All'],
        ['investigating', 'fa-search', 'Investigating'],
        ['substantiated', 'fa-check-circle', 'Substantiated'],
        ['anonymous', 'fa-user-secret', 'Anonymous'],
        ['high', 'fa-exclamation-triangle', 'High']
    ];
    
    const chips = filters.map(([id, icon, label]) => `
        <div class="filter-chip ${id === 'all' ? 'active' : ''}"
            data-filter="${id}"
            onclick="applyWBFilter('${id}', this)">
            <i class="fa ${icon}"></i> ${label}
            <span class="count">0</span>
        </div>
    `).join('');
    
    const pageContent = listview.page.wrapper.find('.page-content');
    pageContent.prepend(`<div class="wb-filters">${chips}</div>`);
    update_wb_filter_counts();
}

window.applyWBFilter = function(filter, el) {
    const listview = window._wb_listview || cur_list;
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
    
    if (filter === 'investigating') {
        listview.filter_area.add('Whistleblower Report', 'status', '=', 'Under Investigation');
    } else if (filter === 'substantiated') {
        listview.filter_area.add('Whistleblower Report', 'status', '=', 'Closed — Substantiated');
    } else if (filter === 'anonymous') {
        listview.filter_area.add('Whistleblower Report', 'is_anonymous', '=', '1');
    } else if (filter === 'high') {
        listview.filter_area.add('Whistleblower Report', 'severity', 'in', ['High', 'Critical']);
    }
    
    listview.refresh();
};

function update_wb_filter_counts() {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.whistleblower_report.whistleblower_report_list.get_wb_summary',
        callback(r) {
            if (!r.message) return;
            const d = r.message;
            document.querySelector('.filter-chip[data-filter="all"] .count').textContent = d.total_count || 0;
            document.querySelector('.filter-chip[data-filter="investigating"] .count').textContent = d.investigating_count || 0;
            document.querySelector('.filter-chip[data-filter="substantiated"] .count').textContent = d.substantiated_count || 0;
            document.querySelector('.filter-chip[data-filter="anonymous"] .count').textContent = d.anonymous_count || 0;
            document.querySelector('.filter-chip[data-filter="high"] .count').textContent = d.high_count || 0;
        }
    });
}

function add_wb_export_options(listview) {
    listview.page.add_menu_item(__('📊 Export to Excel'), () => {
        let filters = {};
        try {
            const current = listview.filter_area?.get() || [];
            current.forEach(f => { if (f[0] === 'Whistleblower Report') filters[f[1]] = f[3]; });
        } catch (e) {}
        const url = '/api/method/ecclesia.ecclesia.doctype.whistleblower_report.whistleblower_report_list.export_wb_excel';
        window.open(url + '?filters=' + encodeURIComponent(JSON.stringify(filters)), '_blank');
    });
}