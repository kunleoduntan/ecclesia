// ecclesia/public/js/license_management_list.js

frappe.listview_settings['License Management'] = {
    add_fields: [
        "name", "license_name", "license_number", "license_type", "issuing_authority",
        "company", "current_expiry_date", "status", "assigned_to", "days_to_expiry"
    ],

    get_indicator: function(doc) {
        if (doc.status === "Active")
            return [__("Active"), "green", "status,=,Active"];
        if (doc.status === "Expiring Soon")
            return [__("Expiring Soon"), "orange", "status,=,Expiring Soon"];
        if (doc.status === "Expired")
            return [__("Expired"), "red", "status,=,Expired"];
        if (doc.status === "Under Renewal")
            return [__("Under Renewal"), "blue", "status,=,Under Renewal"];
        if (doc.status === "Suspended")
            return [__("Suspended"), "grey", "status,=,Suspended"];
        if (doc.status === "Revoked")
            return [__("Revoked"), "red", "status,=,Revoked"];
        return [__("License"), "blue", "status,=,"];
    },

    formatters: {
        license_name: function(v, doc) {
            return v ? `<span style="font-weight:600;color:#f59e0b;">
                <i class="fa fa-certificate" style="color:#f59e0b;margin-right:6px;"></i>${v}
            </span>` : '';
        },
        license_type: function(v) {
            if (!v) return '';
            const colors = {
                'Operating': '#3b82f6',
                'Environmental': '#10b981',
                'Health & Safety': '#f59e0b',
                'Professional': '#8b5cf6',
                'Business Permit': '#ec4899',
                'Factory License': '#f97316',
                'NAFDAC License': '#14b8a6',
                'NSITF Certificate': '#6366f1',
                'ITF Certificate': '#f472b6',
                'SON Registration': '#06b6d4',
                'Fire Certificate': '#ef4444',
                'AML License': '#8b5cf6'
            };
            return `<span style="color:${colors[v] || '#475569'};font-weight:500;font-size:11px;">${v}</span>`;
        },
        status: function(v) {
            if (!v) return '';
            const colors = {
                'Active': { bg: '#DCFCE7', text: '#166534', icon: 'fa-check-circle' },
                'Expiring Soon': { bg: '#FEF3C7', text: '#92400E', icon: 'fa-hourglass-half' },
                'Expired': { bg: '#FEE2E2', text: '#991B1B', icon: 'fa-times-circle' },
                'Under Renewal': { bg: '#DBEAFE', text: '#1E40AF', icon: 'fa-refresh' },
                'Suspended': { bg: '#F1F5F9', text: '#475569', icon: 'fa-pause-circle' },
                'Revoked': { bg: '#FEE2E2', text: '#7F1D1D', icon: 'fa-ban' }
            };
            const style = colors[v] || { bg: '#E2E8F0', text: '#1E293B', icon: 'fa-info-circle' };
            return `<span style="background:${style.bg};color:${style.text};padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600;">
                <i class="fa ${style.icon}" style="margin-right:5px;"></i>${v}
            </span>`;
        },
        current_expiry_date: function(v) {
            if (!v) return '';
            let today = frappe.datetime.get_today();
            let diff = frappe.datetime.get_diff(v, today);
            let color = diff < 0 ? '#dc2626' : (diff < 30 ? '#f59e0b' : (diff < 90 ? '#f59e0b' : '#475569'));
            let icon = diff < 0 ? 'fa-hourglass-end' : 'fa-calendar';
            return `<span style="color:${color};">
                <i class="fa ${icon}" style="margin-right:5px;"></i>${frappe.datetime.str_to_user(v)}
                ${diff < 0 ? ' <span style="color:#dc2626;font-weight:700;">(Expired)</span>' : ''}
            </span>`;
        },
        days_to_expiry: function(v) {
            if (v === null || v === undefined) return '';
            let color = v < 0 ? '#dc2626' : (v < 30 ? '#f59e0b' : (v < 90 ? '#f59e0b' : '#16a34a'));
            return `<span style="color:${color};font-weight:600;">${v} days</span>`;
        }
    },

    onload: function(listview) {
        window._license_listview = listview;
        setTimeout(() => {
            add_license_styles();
            add_license_summary_cards(listview);
            add_license_quick_filters(listview);
        }, 300);
        add_license_export_options(listview);
    },

    refresh: function(listview) {
        window._license_listview = listview;
        setTimeout(() => {
            update_license_summary_cards(listview);
            update_license_filter_counts();
        }, 200);
    },

    primary_action: () => frappe.new_doc("License Management"),

    button: {
        show: (doc) => doc.name,
        get_label: () => __('Actions'),
        get_description: () => __('Quick Actions'),
        action: (doc) => show_license_row_actions(doc)
    },

    colwidths: {
        "license_name": 200, "license_number": 160, "license_type": 150,
        "issuing_authority": 160, "company": 160, "current_expiry_date": 140,
        "status": 130, "assigned_to": 150, "days_to_expiry": 100
    }
};

function show_license_row_actions(doc) {
    const actions = [
        { label: '📄 View License', action: () => frappe.set_route('Form', 'License Management', doc.name) },
        { label: '🔄 Renew License', action: () => renew_license(doc) },
        { label: '📋 View History', action: () => frappe.set_route('Form', 'License Management', doc.name, {'tab': 'tab_renewal_history'}) },
        { label: '📊 View CLL', action: () => frappe.set_route('Form', 'Compliance Liability Ledger', doc.compliance_liability_link) }
    ];
    show_actions_menu(actions);
}

function renew_license(doc) {
    const dialog = new frappe.ui.Dialog({
        title: __('Renew License'),
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
            },
            {
                fieldname: 'payment_reference',
                label: __('Payment Reference'),
                fieldtype: 'Data'
            }
        ],
        primary_action: function(values) {
            frappe.call({
                method: 'ecclesia.ecclesia.doctype.license_management.license_management.renew_license',
                args: {
                    docname: doc.name,
                    renewal_date: values.renewal_date,
                    new_expiry_date: values.new_expiry_date,
                    renewal_cost: values.renewal_cost,
                    payment_reference: values.payment_reference
                },
                callback: function() {
                    dialog.hide();
                    frappe.show_alert({message: __('License renewed successfully'), indicator: 'green'});
                    window._license_listview?.refresh();
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

function add_license_styles() {
    if ($('#license-styles').length) return;
    $('head').append(`
        <style id="license-styles">
        .list-row {
            transition: all .25s ease !important;
            border-left: 4px solid transparent !important;
            border-radius: 8px !important;
            margin: 2px 0 !important;
        }
        .list-row:hover {
            background: linear-gradient(90deg, #fef3c7, #fde68a) !important;
            border-left-color: #f59e0b !important;
            transform: translateX(3px);
        }
        .list-headers {
            background: linear-gradient(135deg, #D97706, #F59E0B) !important;
            color: #fff !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            font-size: 11px !important;
            letter-spacing: .8px !important;
            padding: 14px 16px !important;
            border-radius: 12px !important;
        }
        .license-summary {
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
            background: linear-gradient(135deg, #fef3c7, #fde68a);
            border-color: #fcd34d;
        }
        .summary-card.total .summary-card-label { color: #b45309; }
        .summary-card.total .summary-card-value { color: #92400e; }
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
        .license-filters {
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
            border-color: #f59e0b;
            background: #fef3c7;
            transform: translateY(-2px);
        }
        .filter-chip.active {
            background: linear-gradient(135deg, #D97706, #F59E0B);
            color: #fff;
            border-color: #F59E0B;
            box-shadow: 0 4px 14px rgba(245,158,11,.3);
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

function add_license_summary_cards(listview) {
    $('.license-summary').remove();
    const pageContent = listview.page.wrapper.find('.page-content');
    if (!pageContent.length) return;
    
    pageContent.prepend(`
        <div class="license-summary">
            <div class="summary-card total">
                <div class="summary-card-label">📋 Total Licenses</div>
                <div class="summary-card-value" id="license-total">0</div>
            </div>
            <div class="summary-card active">
                <div class="summary-card-label">✅ Active</div>
                <div class="summary-card-value" id="license-active">0</div>
            </div>
            <div class="summary-card expiring">
                <div class="summary-card-label">⚠️ Expiring Soon</div>
                <div class="summary-card-value" id="license-expiring">0</div>
            </div>
            <div class="summary-card expired">
                <div class="summary-card-label">🚨 Expired</div>
                <div class="summary-card-value" id="license-expired">0</div>
            </div>
        </div>
    `);
    update_license_summary_cards(listview);
}

function update_license_summary_cards(listview) {
    let filters = {};
    try {
        const current = listview.filter_area?.get() || [];
        current.forEach(f => { if (f[0] === 'License Management') filters[f[1]] = f[3]; });
    } catch (e) {}
    
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.license_management.license_management_list.get_license_summary',
        args: { filters: filters },
        callback(r) {
            if (!r.message) return;
            const d = r.message;
            $('#license-total').text(d.total_count || 0);
            $('#license-active').text(d.active_count || 0);
            $('#license-expiring').text(d.expiring_count || 0);
            $('#license-expired').text(d.expired_count || 0);
        }
    });
}

function add_license_quick_filters(listview) {
    $('.license-filters').remove();
    
    const filters = [
        ['all', 'fa-list', 'All'],
        ['active', 'fa-check-circle', 'Active'],
        ['expiring', 'fa-hourglass-half', 'Expiring'],
        ['expired', 'fa-times-circle', 'Expired'],
        ['operating', 'fa-building', 'Operating'],
        ['environmental', 'fa-leaf', 'Environmental']
    ];
    
    const chips = filters.map(([id, icon, label]) => `
        <div class="filter-chip ${id === 'all' ? 'active' : ''}"
            data-filter="${id}"
            onclick="applyLicenseFilter('${id}', this)">
            <i class="fa ${icon}"></i> ${label}
            <span class="count">0</span>
        </div>
    `).join('');
    
    const pageContent = listview.page.wrapper.find('.page-content');
    pageContent.prepend(`<div class="license-filters">${chips}</div>`);
    update_license_filter_counts();
}

window.applyLicenseFilter = function(filter, el) {
    const listview = window._license_listview || cur_list;
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
        listview.filter_area.add('License Management', 'status', '=', 'Active');
    } else if (filter === 'expiring') {
        listview.filter_area.add('License Management', 'status', '=', 'Expiring Soon');
    } else if (filter === 'expired') {
        listview.filter_area.add('License Management', 'status', '=', 'Expired');
    } else if (filter === 'operating') {
        listview.filter_area.add('License Management', 'license_type', '=', 'Operating');
    } else if (filter === 'environmental') {
        listview.filter_area.add('License Management', 'license_type', '=', 'Environmental');
    }
    
    listview.refresh();
};

function update_license_filter_counts() {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.license_management.license_management_list.get_license_summary',
        callback(r) {
            if (!r.message) return;
            const d = r.message;
            document.querySelector('.filter-chip[data-filter="all"] .count').textContent = d.total_count || 0;
            document.querySelector('.filter-chip[data-filter="active"] .count').textContent = d.active_count || 0;
            document.querySelector('.filter-chip[data-filter="expiring"] .count').textContent = d.expiring_count || 0;
            document.querySelector('.filter-chip[data-filter="expired"] .count').textContent = d.expired_count || 0;
            document.querySelector('.filter-chip[data-filter="operating"] .count').textContent = d.operating_count || 0;
            document.querySelector('.filter-chip[data-filter="environmental"] .count').textContent = d.environmental_count || 0;
        }
    });
}

function add_license_export_options(listview) {
    listview.page.add_menu_item(__('📊 Export to Excel'), () => {
        let filters = {};
        try {
            const current = listview.filter_area?.get() || [];
            current.forEach(f => { if (f[0] === 'License Management') filters[f[1]] = f[3]; });
        } catch (e) {}
        const url = '/api/method/ecclesia.ecclesia.doctype.license_management.license_management_list.export_license_excel';
        window.open(url + '?filters=' + encodeURIComponent(JSON.stringify(filters)), '_blank');
    });
}