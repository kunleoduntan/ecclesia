// ecclesia/public/js/expatriate_permit_register_list.js

frappe.listview_settings['Expatriate Permit Register'] = {
    add_fields: [
        "name", "permit_title", "employee", "nationality", "permit_type",
        "permit_number", "expiry_date", "status", "days_to_expiry"
    ],

    get_indicator: function(doc) {
        if (doc.status === "Active")
            return [__("Active"), "green", "status,=,Active"];
        if (doc.status === "Expiring Soon")
            return [__("Expiring Soon"), "orange", "status,=,Expiring Soon"];
        if (doc.status === "Expired")
            return [__("Expired"), "red", "status,=,Expired"];
        if (doc.status === "Renewing")
            return [__("Renewing"), "blue", "status,=,Renewing"];
        if (doc.status === "Cancelled")
            return [__("Cancelled"), "grey", "status,=,Cancelled"];
        return [__("Expatriate Permit"), "blue", "status,=,"];
    },

    formatters: {
        permit_title: function(v, doc) {
            return v ? `<span style="font-weight:600;color:#2563eb;">
                <i class="fa fa-passport" style="color:#2563eb;margin-right:6px;"></i>${v}
            </span>` : '';
        },
        employee: function(v, doc) {
            return v ? `<span style="font-weight:500;">${v}</span>` : '';
        },
        status: function(v) {
            if (!v) return '';
            const colors = {
                'Active': { bg: '#DCFCE7', text: '#166534', icon: 'fa-check-circle' },
                'Expiring Soon': { bg: '#FEF3C7', text: '#92400E', icon: 'fa-hourglass-half' },
                'Expired': { bg: '#FEE2E2', text: '#991B1B', icon: 'fa-times-circle' },
                'Renewing': { bg: '#DBEAFE', text: '#1E40AF', icon: 'fa-refresh' },
                'Cancelled': { bg: '#F1F5F9', text: '#475569', icon: 'fa-ban' }
            };
            const style = colors[v] || { bg: '#E2E8F0', text: '#1E293B', icon: 'fa-info-circle' };
            return `<span style="background:${style.bg};color:${style.text};padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600;">
                <i class="fa ${style.icon}" style="margin-right:5px;"></i>${v}
            </span>`;
        },
        permit_type: function(v) {
            if (!v) return '';
            const colors = {
                'Expatriate Quota': '#3b82f6',
                'CERPAC': '#10b981',
                'Short-Term Residence': '#f59e0b',
                'Visit Visa': '#8b5cf6',
                'Work Permit': '#ec4899',
                'Business Permit': '#f97316'
            };
            return `<span style="color:${colors[v] || '#475569'};font-weight:500;font-size:11px;">${v}</span>`;
        },
        days_to_expiry: function(v) {
            if (v === null || v === undefined) return '';
            let color = v < 0 ? '#dc2626' : (v < 30 ? '#f59e0b' : '#16a34a');
            return `<span style="color:${color};font-weight:600;">${v} days</span>`;
        }
    },

    onload: function(listview) {
        window._epr_listview = listview;
        setTimeout(() => {
            add_epr_styles();
            add_epr_summary_cards(listview);
            add_epr_quick_filters(listview);
        }, 300);
        add_epr_export_options(listview);
    },

    refresh: function(listview) {
        window._epr_listview = listview;
        setTimeout(() => {
            update_epr_summary_cards(listview);
            update_epr_filter_counts();
        }, 200);
    },

    primary_action: () => frappe.new_doc("Expatriate Permit Register"),

    button: {
        show: (doc) => doc.name,
        get_label: () => __('Actions'),
        get_description: () => __('Quick Actions'),
        action: (doc) => show_epr_row_actions(doc)
    },

    colwidths: {
        "permit_title": 200, "employee": 160, "nationality": 120,
        "permit_type": 160, "permit_number": 140, "expiry_date": 120,
        "status": 130, "days_to_expiry": 100
    }
};

function show_epr_row_actions(doc) {
    const actions = [
        { label: '📄 View Permit', action: () => frappe.set_route('Form', 'Expatriate Permit Register', doc.name) },
        { label: '🔄 Renew Permit', action: () => renew_epr(doc) },
        { label: '👤 View Employee', action: () => frappe.set_route('Form', 'Employee', doc.employee) },
        { label: '📊 View CLL', action: () => frappe.set_route('Form', 'Compliance Liability Ledger', doc.compliance_liability_link) }
    ];
    show_actions_menu(actions);
}

function renew_epr(doc) {
    const dialog = new frappe.ui.Dialog({
        title: __('Renew Permit'),
        fields: [
            {
                fieldname: 'renewal_date',
                label: __('Renewal Date'),
                fieldtype: 'Date',
                default: frappe.datetime.get_today(),
                reqd: 1
            },
            {
                fieldname: 'new_expiry_date',
                label: __('New Expiry Date'),
                fieldtype: 'Date',
                reqd: 1
            },
            {
                fieldname: 'renewal_cost',
                label: __('Renewal Cost (₦)'),
                fieldtype: 'Currency',
                default: doc.renewal_cost || 0
            }
        ],
        primary_action: function(values) {
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.expatriate_permit_register.expatriate_permit_register.renew_permit',
                args: {
                    docname: doc.name,
                    renewal_date: values.renewal_date,
                    new_expiry_date: values.new_expiry_date,
                    renewal_cost: values.renewal_cost
                },
                callback: function() {
                    dialog.hide();
                    frappe.show_alert({message: __('Permit renewed successfully'), indicator: 'green'});
                    window._epr_listview?.refresh();
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

function add_epr_styles() {
    if ($('#epr-styles').length) return;
    $('head').append(`
        <style id="epr-styles">
        .list-row {
            transition: all .25s ease !important;
            border-left: 4px solid transparent !important;
            border-radius: 8px !important;
            margin: 2px 0 !important;
        }
        .list-row:hover {
            background: linear-gradient(90deg, #eff6ff, #dbeafe) !important;
            border-left-color: #2563eb !important;
            transform: translateX(3px);
        }
        .list-headers {
            background: linear-gradient(135deg, #1D4ED8, #3B82F6) !important;
            color: #fff !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            font-size: 11px !important;
            letter-spacing: .8px !important;
            padding: 14px 16px !important;
            border-radius: 12px !important;
        }
        .epr-summary {
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
            background: linear-gradient(135deg, #eff6ff, #dbeafe);
            border-color: #93c5fd;
        }
        .summary-card.total .summary-card-label { color: #1d4ed8; }
        .summary-card.total .summary-card-value { color: #1e3a8a; }
        .summary-card.active {
            background: linear-gradient(135deg, #ecfdf5, #d1fae5);
            border-color: #6ee7b7;
        }
        .summary-card.active .summary-card-label { color: #047857; }
        .summary-card.active .summary-card-value { color: #065f46; }
        .summary-card.expiring {
            background: linear-gradient(135deg, #fef3c7, #fde68a);
            border-color: #fcd34d;
        }
        .summary-card.expiring .summary-card-label { color: #b45309; }
        .summary-card.expiring .summary-card-value { color: #92400e; }
        .summary-card.expired {
            background: linear-gradient(135deg, #fef2f2, #fee2e2);
            border-color: #fca5a5;
        }
        .summary-card.expired .summary-card-label { color: #b91c1c; }
        .summary-card.expired .summary-card-value { color: #991b1b; }
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
        .epr-filters {
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
            border-color: #3b82f6;
            background: #eff6ff;
            transform: translateY(-2px);
        }
        .filter-chip.active {
            background: linear-gradient(135deg, #1D4ED8, #3B82F6);
            color: #fff;
            border-color: #3B82F6;
            box-shadow: 0 4px 14px rgba(59,130,246,.3);
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

function add_epr_summary_cards(listview) {
    $('.epr-summary').remove();
    const pageContent = listview.page.wrapper.find('.page-content');
    if (!pageContent.length) return;
    
    pageContent.prepend(`
        <div class="epr-summary">
            <div class="summary-card total">
                <div class="summary-card-label">📋 Total Permits</div>
                <div class="summary-card-value" id="epr-total">0</div>
            </div>
            <div class="summary-card active">
                <div class="summary-card-label">✅ Active</div>
                <div class="summary-card-value" id="epr-active">0</div>
            </div>
            <div class="summary-card expiring">
                <div class="summary-card-label">⚠️ Expiring Soon</div>
                <div class="summary-card-value" id="epr-expiring">0</div>
            </div>
            <div class="summary-card expired">
                <div class="summary-card-label">🚨 Expired</div>
                <div class="summary-card-value" id="epr-expired">0</div>
            </div>
        </div>
    `);
    update_epr_summary_cards(listview);
}

function update_epr_summary_cards(listview) {
    let filters = {};
    try {
        const current = listview.filter_area?.get() || [];
        current.forEach(f => { if (f[0] === 'Expatriate Permit Register') filters[f[1]] = f[3]; });
    } catch (e) {}
    
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.expatriate_permit_register.expatriate_permit_register_list.get_epr_summary',
        args: { filters: filters },
        callback(r) {
            if (!r.message) return;
            const d = r.message;
            $('#epr-total').text(d.total_count || 0);
            $('#epr-active').text(d.active_count || 0);
            $('#epr-expiring').text(d.expiring_count || 0);
            $('#epr-expired').text(d.expired_count || 0);
        }
    });
}

function add_epr_quick_filters(listview) {
    $('.epr-filters').remove();
    
    const filters = [
        ['all', 'fa-list', 'All'],
        ['active', 'fa-check-circle', 'Active'],
        ['expiring', 'fa-hourglass-half', 'Expiring'],
        ['expired', 'fa-times-circle', 'Expired'],
        ['quota', 'fa-file-text-o', 'Quota'],
        ['cerpac', 'fa-id-card', 'CERPAC']
    ];
    
    const chips = filters.map(([id, icon, label]) => `
        <div class="filter-chip ${id === 'all' ? 'active' : ''}"
            data-filter="${id}"
            onclick="applyEPRFilter('${id}', this)">
            <i class="fa ${icon}"></i> ${label}
            <span class="count">0</span>
        </div>
    `).join('');
    
    const pageContent = listview.page.wrapper.find('.page-content');
    pageContent.prepend(`<div class="epr-filters">${chips}</div>`);
    update_epr_filter_counts();
}

window.applyEPRFilter = function(filter, el) {
    const listview = window._epr_listview || cur_list;
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
    
    if (filter === 'active') {
        listview.filter_area.add('Expatriate Permit Register', 'status', '=', 'Active');
    } else if (filter === 'expiring') {
        listview.filter_area.add('Expatriate Permit Register', 'status', '=', 'Expiring Soon');
    } else if (filter === 'expired') {
        listview.filter_area.add('Expatriate Permit Register', 'status', '=', 'Expired');
    } else if (filter === 'quota') {
        listview.filter_area.add('Expatriate Permit Register', 'permit_type', '=', 'Expatriate Quota');
    } else if (filter === 'cerpac') {
        listview.filter_area.add('Expatriate Permit Register', 'permit_type', '=', 'Combined Expatriate Residence Permit & Alien Card (CERPAC)');
    }
    
    listview.refresh();
};

function update_epr_filter_counts() {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.expatriate_permit_register.expatriate_permit_register_list.get_epr_summary',
        callback(r) {
            if (!r.message) return;
            const d = r.message;
            document.querySelector('.filter-chip[data-filter="all"] .count').textContent = d.total_count || 0;
            document.querySelector('.filter-chip[data-filter="active"] .count').textContent = d.active_count || 0;
            document.querySelector('.filter-chip[data-filter="expiring"] .count').textContent = d.expiring_count || 0;
            document.querySelector('.filter-chip[data-filter="expired"] .count').textContent = d.expired_count || 0;
            document.querySelector('.filter-chip[data-filter="quota"] .count').textContent = d.quota_count || 0;
            document.querySelector('.filter-chip[data-filter="cerpac"] .count').textContent = d.cerpac_count || 0;
        }
    });
}

function add_epr_export_options(listview) {
    listview.page.add_menu_item(__('📊 Export to Excel'), () => {
        let filters = {};
        try {
            const current = listview.filter_area?.get() || [];
            current.forEach(f => { if (f[0] === 'Expatriate Permit Register') filters[f[1]] = f[3]; });
        } catch (e) {}
        const url = '/api/method/ecclesia.ecclesia.doctype.expatriate_permit_register.expatriate_permit_register_list.export_epr_excel';
        window.open(url + '?filters=' + encodeURIComponent(JSON.stringify(filters)), '_blank');
    });
}