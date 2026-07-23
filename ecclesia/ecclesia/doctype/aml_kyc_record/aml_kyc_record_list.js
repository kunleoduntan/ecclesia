// ecclesia/public/js/aml_kyc_record_list.js

frappe.listview_settings['AML KYC Record'] = {
    add_fields: [
        "name", "party_name_display", "party_type", "kyc_level", "risk_rating",
        "kyc_date", "kyc_expiry_date", "identity_verified", "address_verified",
        "pep_check_done", "sanctions_check_done", "is_pep", "sanctions_match"
    ],

    get_indicator: function(doc) {
        if (doc.risk_rating === "Sanctioned — Blocked")
            return [__("Blocked"), "red", "risk_rating,=,Sanctioned — Blocked"];
        if (doc.risk_rating === "PEP — High")
            return [__("PEP High"), "red", "risk_rating,=,PEP — High"];
        if (doc.risk_rating === "High")
            return [__("High Risk"), "orange", "risk_rating,=,High"];
        if (doc.risk_rating === "Medium")
            return [__("Medium Risk"), "yellow", "risk_rating,=,Medium"];
        if (doc.risk_rating === "Low")
            return [__("Low Risk"), "green", "risk_rating,=,Low"];
        return [__("KYC Record"), "blue", "status,=,"];
    },

    formatters: {
        party_name_display: function(v, doc) {
            return v ? `<span style="font-weight:600;color:#1e3a5f;">
                <i class="fa fa-user" style="color:#3b82f6;margin-right:6px;"></i>${v}
            </span>` : '';
        },
        risk_rating: function(v) {
            if (!v) return '';
            const colors = {
                'Low': { bg: '#DCFCE7', text: '#166534', icon: 'fa-check-circle' },
                'Medium': { bg: '#FEF3C7', text: '#92400E', icon: 'fa-exclamation-circle' },
                'High': { bg: '#FEE2E2', text: '#991B1B', icon: 'fa-exclamation-triangle' },
                'PEP — High': { bg: '#FEF2F2', text: '#991B1B', icon: 'fa-user-secret' },
                'Sanctioned — Blocked': { bg: '#FEE2E2', text: '#7F1D1D', icon: 'fa-ban' }
            };
            const style = colors[v] || { bg: '#E2E8F0', text: '#1E293B', icon: 'fa-info-circle' };
            return `<span style="background:${style.bg};color:${style.text};padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600;">
                <i class="fa ${style.icon}" style="margin-right:5px;"></i>${v}
            </span>`;
        },
        kyc_level: function(v) {
            if (!v) return '';
            const colors = {
                'Simplified Due Diligence (SDD)': '#10b981',
                'Basic Customer Due Diligence (CDD)': '#3b82f6',
                'Enhanced Due Diligence (EDD)': '#8b5cf6'
            };
            return `<span style="color:${colors[v] || '#475569'};font-weight:500;">${v}</span>`;
        },
        identity_verified: function(v) {
            return v ? '✅' : '⬜';
        },
        kyc_expiry_date: function(v) {
            if (!v) return '';
            let today = frappe.datetime.get_today();
            let diff = frappe.datetime.get_diff(v, today);
            let color = diff < 0 ? '#dc2626' : (diff < 30 ? '#f59e0b' : '#475569');
            let icon = diff < 0 ? 'fa-hourglass-end' : 'fa-calendar';
            return `<span style="color:${color};">
                <i class="fa ${icon}" style="margin-right:5px;"></i>${frappe.datetime.str_to_user(v)}
            </span>`;
        }
    },

    onload: function(listview) {
        window._aml_listview = listview;
        setTimeout(() => {
            add_aml_styles();
            add_aml_summary_cards(listview);
            add_aml_quick_filters(listview);
        }, 300);
        add_aml_export_options(listview);
    },

    refresh: function(listview) {
        window._aml_listview = listview;
        setTimeout(() => {
            update_aml_summary_cards(listview);
            update_aml_filter_counts();
        }, 200);
    },

    primary_action: () => frappe.new_doc("AML KYC Record"),

    button: {
        show: (doc) => doc.name,
        get_label: () => __('Actions'),
        get_description: () => __('Quick Actions'),
        action: (doc) => show_aml_row_actions(doc)
    },

    colwidths: {
        "party_name_display": 180, "party_type": 120, "kyc_level": 220,
        "risk_rating": 140, "kyc_date": 120, "kyc_expiry_date": 140,
        "identity_verified": 80, "address_verified": 80
    }
};

function show_aml_row_actions(doc) {
    const actions = [
        { label: '🔍 View Record', action: () => frappe.set_route('Form', 'AML KYC Record', doc.name) },
        { label: '🔄 Refresh Screening', action: () => refresh_aml_screening(doc) },
        { label: '📋 View Screening', action: () => frappe.set_route('Form', 'AML KYC Record', doc.name, {'tab': 'tab_screening_section'}) },
        { label: '📊 Generate STR', action: () => generate_str_from_aml(doc) }
    ];
    show_actions_menu(actions);
}

function refresh_aml_screening(doc) {
    frappe.confirm(__('Refresh screening for {0}?', [doc.party_name_display]), () => {
        frappe.call({
            method: 'ecclesia.ecclesia.doctype.aml_kyc_record.aml_kyc_record.refresh_screening',
            args: { docname: doc.name },
            callback: function(r) {
                frappe.show_alert({message: __('Screening refreshed'), indicator: 'green'});
                window._aml_listview?.refresh();
            }
        });
    });
}

function generate_str_from_aml(doc) {
    frappe.new_doc('Suspicious Transaction Report', {
        party_name: doc.party_name_display,
        kyc_record: doc.name
    });
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

function add_aml_styles() {
    if ($('#aml-styles').length) return;
    $('head').append(`
        <style id="aml-styles">
        .list-row {
            transition: all .25s ease !important;
            border-left: 4px solid transparent !important;
            border-radius: 8px !important;
            margin: 2px 0 !important;
        }
        .list-row:hover {
            background: linear-gradient(90deg, #e0f2fe, #bae6fd) !important;
            border-left-color: #8b5cf6 !important;
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
        .aml-summary {
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
        .summary-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(0,0,0,.12);
        }
        .summary-card.total {
            background: linear-gradient(135deg, #f5f3ff, #ede9fe);
            border-color: #c4b5fd;
        }
        .summary-card.total .summary-card-label { color: #5b21b6; }
        .summary-card.total .summary-card-value { color: #5b21b6; }
        .summary-card.low {
            background: linear-gradient(135deg, #ecfdf5, #d1fae5);
            border-color: #6ee7b7;
        }
        .summary-card.low .summary-card-label { color: #047857; }
        .summary-card.low .summary-card-value { color: #065f46; }
        .summary-card.medium {
            background: linear-gradient(135deg, #fef3c7, #fde68a);
            border-color: #fcd34d;
        }
        .summary-card.medium .summary-card-label { color: #b45309; }
        .summary-card.medium .summary-card-value { color: #92400e; }
        .summary-card.high {
            background: linear-gradient(135deg, #fef2f2, #fee2e2);
            border-color: #fca5a5;
        }
        .summary-card.high .summary-card-label { color: #b91c1c; }
        .summary-card.high .summary-card-value { color: #991b1b; }
        .summary-card.label {
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
        .aml-filters {
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
            border-color: #818cf8;
            background: #eef2ff;
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

function add_aml_summary_cards(listview) {
    $('.aml-summary').remove();
    const pageContent = listview.page.wrapper.find('.page-content');
    if (!pageContent.length) return;
    
    pageContent.prepend(`
        <div class="aml-summary">
            <div class="summary-card total">
                <div class="summary-card-label">📋 Total Records</div>
                <div class="summary-card-value" id="aml-total">0</div>
            </div>
            <div class="summary-card low">
                <div class="summary-card-label">✅ Low Risk</div>
                <div class="summary-card-value" id="aml-low">0</div>
            </div>
            <div class="summary-card medium">
                <div class="summary-card-label">⚠️ Medium Risk</div>
                <div class="summary-card-value" id="aml-medium">0</div>
            </div>
            <div class="summary-card high">
                <div class="summary-card-label">🚨 High Risk</div>
                <div class="summary-card-value" id="aml-high">0</div>
            </div>
        </div>
    `);
    update_aml_summary_cards(listview);
}

function update_aml_summary_cards(listview) {
    let filters = {};
    try {
        const current = listview.filter_area?.get() || [];
        current.forEach(f => { if (f[0] === 'AML KYC Record') filters[f[1]] = f[3]; });
    } catch (e) {}
    
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.aml_kyc_record.aml_kyc_record_list.get_aml_summary',
        args: { filters: filters },
        callback(r) {
            if (!r.message) return;
            const d = r.message;
            $('#aml-total').text(d.total_count || 0);
            $('#aml-low').text(d.low_count || 0);
            $('#aml-medium').text(d.medium_count || 0);
            $('#aml-high').text(d.high_count || 0);
        }
    });
}

function add_aml_quick_filters(listview) {
    $('.aml-filters').remove();
    
    const filters = [
        ['all', 'fa-list', 'All'],
        ['low', 'fa-check-circle', 'Low'],
        ['medium', 'fa-exclamation-circle', 'Medium'],
        ['high', 'fa-exclamation-triangle', 'High'],
        ['pep', 'fa-user-secret', 'PEP'],
        ['sanctioned', 'fa-ban', 'Sanctioned']
    ];
    
    const chips = filters.map(([id, icon, label]) => `
        <div class="filter-chip ${id === 'all' ? 'active' : ''}"
            data-filter="${id}"
            onclick="applyAMLFilter('${id}', this)">
            <i class="fa ${icon}"></i> ${label}
            <span class="count">0</span>
        </div>
    `).join('');
    
    const pageContent = listview.page.wrapper.find('.page-content');
    pageContent.prepend(`<div class="aml-filters">${chips}</div>`);
    update_aml_filter_counts();
}

window.applyAMLFilter = function(filter, el) {
    const listview = window._aml_listview || cur_list;
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
    
    if (filter === 'low') {
        listview.filter_area.add('AML KYC Record', 'risk_rating', '=', 'Low');
    } else if (filter === 'medium') {
        listview.filter_area.add('AML KYC Record', 'risk_rating', '=', 'Medium');
    } else if (filter === 'high') {
        listview.filter_area.add('AML KYC Record', 'risk_rating', 'in', ['High', 'PEP — High']);
    } else if (filter === 'pep') {
        listview.filter_area.add('AML KYC Record', 'is_pep', '=', '1');
    } else if (filter === 'sanctioned') {
        listview.filter_area.add('AML KYC Record', 'sanctions_match', '=', '1');
    }
    
    listview.refresh();
};

function update_aml_filter_counts() {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.aml_kyc_record.aml_kyc_record_list.get_aml_summary',
        callback(r) {
            if (!r.message) return;
            const d = r.message;
            document.querySelector('.filter-chip[data-filter="all"] .count').textContent = d.total_count || 0;
            document.querySelector('.filter-chip[data-filter="low"] .count').textContent = d.low_count || 0;
            document.querySelector('.filter-chip[data-filter="medium"] .count').textContent = d.medium_count || 0;
            document.querySelector('.filter-chip[data-filter="high"] .count').textContent = d.high_count || 0;
            document.querySelector('.filter-chip[data-filter="pep"] .count').textContent = d.pep_count || 0;
            document.querySelector('.filter-chip[data-filter="sanctioned"] .count').textContent = d.sanctioned_count || 0;
        }
    });
}

function add_aml_export_options(listview) {
    listview.page.add_menu_item(__('📊 Export to Excel'), () => {
        let filters = {};
        try {
            const current = listview.filter_area?.get() || [];
            current.forEach(f => { if (f[0] === 'AML KYC Record') filters[f[1]] = f[3]; });
        } catch (e) {}
        const url = '/api/method/ecclesia.ecclesia.doctype.aml_kyc_record.aml_kyc_record_list.export_aml_excel';
        window.open(url + '?filters=' + encodeURIComponent(JSON.stringify(filters)), '_blank');
    });
}