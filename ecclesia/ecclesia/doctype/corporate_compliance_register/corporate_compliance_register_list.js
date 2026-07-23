// ecclesia/public/js/corporate_compliance_register_list.js

frappe.listview_settings['Corporate Compliance Register'] = {
    add_fields: [
        "name", "register_title", "company", "fiscal_year", "rc_number",
        "overall_status", "annual_return_status", "next_agm_due_date"
    ],

    get_indicator: function(doc) {
        if (doc.overall_status === "Compliant")
            return [__("Compliant"), "green", "overall_status,=,Compliant"];
        if (doc.overall_status === "Minor Issues")
            return [__("Minor Issues"), "orange", "overall_status,=,Minor Issues"];
        if (doc.overall_status === "Major Issues")
            return [__("Major Issues"), "red", "overall_status,=,Major Issues"];
        if (doc.overall_status === "Non-Compliant")
            return [__("Non-Compliant"), "red", "overall_status,=,Non-Compliant"];
        return [__("Corporate Register"), "blue", "overall_status,=,"];
    },

    formatters: {
        register_title: function(v, doc) {
            return v ? `<span style="font-weight:600;color:#0d9488;">
                <i class="fa fa-building" style="color:#0d9488;margin-right:6px;"></i>${v}
            </span>` : '';
        },
        overall_status: function(v) {
            if (!v) return '';
            const colors = {
                'Compliant': { bg: '#DCFCE7', text: '#166534', icon: 'fa-check-circle' },
                'Minor Issues': { bg: '#FEF3C7', text: '#92400E', icon: 'fa-exclamation-circle' },
                'Major Issues': { bg: '#FEE2E2', text: '#991B1B', icon: 'fa-exclamation-triangle' },
                'Non-Compliant': { bg: '#FEE2E2', text: '#7F1D1D', icon: 'fa-times-circle' }
            };
            const style = colors[v] || { bg: '#E2E8F0', text: '#1E293B', icon: 'fa-info-circle' };
            return `<span style="background:${style.bg};color:${style.text};padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600;">
                <i class="fa ${style.icon}" style="margin-right:5px;"></i>${v}
            </span>`;
        },
        annual_return_status: function(v) {
            if (!v) return '';
            const colors = {
                'Filed On Time': '#16a34a',
                'Late Filed': '#f59e0b',
                'Overdue': '#dc2626',
                'Not Due': '#64748b',
                'Due': '#f59e0b',
                'Exempt': '#64748b'
            };
            return `<span style="color:${colors[v] || '#475569'};font-weight:500;font-size:11px;">${v}</span>`;
        },
        next_agm_due_date: function(v) {
            if (!v) return '';
            let today = frappe.datetime.get_today();
            let diff = frappe.datetime.get_diff(v, today);
            let color = diff < 0 ? '#dc2626' : (diff < 30 ? '#f59e0b' : '#475569');
            return `<span style="color:${color};">
                <i class="fa fa-calendar" style="margin-right:5px;"></i>${frappe.datetime.str_to_user(v)}
            </span>`;
        }
    },

    onload: function(listview) {
        window._ccr_listview = listview;
        setTimeout(() => {
            add_ccr_styles();
            add_ccr_summary_cards(listview);
            add_ccr_quick_filters(listview);
        }, 300);
        add_ccr_export_options(listview);
    },

    refresh: function(listview) {
        window._ccr_listview = listview;
        setTimeout(() => {
            update_ccr_summary_cards(listview);
            update_ccr_filter_counts();
        }, 200);
    },

    primary_action: () => frappe.new_doc("Corporate Compliance Register"),

    button: {
        show: (doc) => doc.name,
        get_label: () => __('Actions'),
        get_description: () => __('Quick Actions'),
        action: (doc) => show_ccr_row_actions(doc)
    },

    colwidths: {
        "register_title": 220, "company": 160, "fiscal_year": 120,
        "rc_number": 140, "overall_status": 140, "annual_return_status": 140,
        "next_agm_due_date": 140
    }
};

function show_ccr_row_actions(doc) {
    const actions = [
        { label: '📄 View Register', action: () => frappe.set_route('Form', 'Corporate Compliance Register', doc.name) },
        { label: '📋 View CAC Return', action: () => frappe.set_route('Form', 'Corporate Compliance Register', doc.name, {'tab': 'tab_cac_section'}) },
        { label: '📜 View Board Resolutions', action: () => frappe.set_route('List', 'Board Resolution', {'corporate_register': doc.name}) },
        { label: '📊 View Statutory Entries', action: () => frappe.set_route('List', 'Statutory Register Entry', {'corporate_register': doc.name}) }
    ];
    show_actions_menu(actions);
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

function add_ccr_styles() {
    if ($('#ccr-styles').length) return;
    $('head').append(`
        <style id="ccr-styles">
        .list-row {
            transition: all .25s ease !important;
            border-left: 4px solid transparent !important;
            border-radius: 8px !important;
            margin: 2px 0 !important;
        }
        .list-row:hover {
            background: linear-gradient(90deg, #ecfdf5, #d1fae5) !important;
            border-left-color: #0d9488 !important;
            transform: translateX(3px);
        }
        .list-headers {
            background: linear-gradient(135deg, #0F766E, #14B8A6) !important;
            color: #fff !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            font-size: 11px !important;
            letter-spacing: .8px !important;
            padding: 14px 16px !important;
            border-radius: 12px !important;
        }
        .ccr-summary {
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
            background: linear-gradient(135deg, #ecfdf5, #d1fae5);
            border-color: #6ee7b7;
        }
        .summary-card.total .summary-card-label { color: #047857; }
        .summary-card.total .summary-card-value { color: #065f46; }
        .summary-card.compliant {
            background: linear-gradient(135deg, #ecfdf5, #d1fae5);
            border-color: #6ee7b7;
        }
        .summary-card.compliant .summary-card-label { color: #047857; }
        .summary-card.compliant .summary-card-value { color: #065f46; }
        .summary-card.minor {
            background: linear-gradient(135deg, #fef3c7, #fde68a);
            border-color: #fcd34d;
        }
        .summary-card.minor .summary-card-label { color: #b45309; }
        .summary-card.minor .summary-card-value { color: #92400e; }
        .summary-card.major {
            background: linear-gradient(135deg, #fef2f2, #fee2e2);
            border-color: #fca5a5;
        }
        .summary-card.major .summary-card-label { color: #b91c1c; }
        .summary-card.major .summary-card-value { color: #991b1b; }
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
        .ccr-filters {
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
            border-color: #14b8a6;
            background: #ecfdf5;
            transform: translateY(-2px);
        }
        .filter-chip.active {
            background: linear-gradient(135deg, #0F766E, #14B8A6);
            color: #fff;
            border-color: #14B8A6;
            box-shadow: 0 4px 14px rgba(20,184,166,.3);
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

function add_ccr_summary_cards(listview) {
    $('.ccr-summary').remove();
    const pageContent = listview.page.wrapper.find('.page-content');
    if (!pageContent.length) return;
    
    pageContent.prepend(`
        <div class="ccr-summary">
            <div class="summary-card total">
                <div class="summary-card-label">📋 Total Registers</div>
                <div class="summary-card-value" id="ccr-total">0</div>
            </div>
            <div class="summary-card compliant">
                <div class="summary-card-label">✅ Compliant</div>
                <div class="summary-card-value" id="ccr-compliant">0</div>
            </div>
            <div class="summary-card minor">
                <div class="summary-card-label">⚠️ Minor Issues</div>
                <div class="summary-card-value" id="ccr-minor">0</div>
            </div>
            <div class="summary-card major">
                <div class="summary-card-label">🚨 Non-Compliant</div>
                <div class="summary-card-value" id="ccr-major">0</div>
            </div>
        </div>
    `);
    update_ccr_summary_cards(listview);
}

function update_ccr_summary_cards(listview) {
    let filters = {};
    try {
        const current = listview.filter_area?.get() || [];
        current.forEach(f => { if (f[0] === 'Corporate Compliance Register') filters[f[1]] = f[3]; });
    } catch (e) {}
    
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.corporate_compliance_register.corporate_compliance_register_list.get_ccr_summary',
        args: { filters: filters },
        callback(r) {
            if (!r.message) return;
            const d = r.message;
            $('#ccr-total').text(d.total_count || 0);
            $('#ccr-compliant').text(d.compliant_count || 0);
            $('#ccr-minor').text(d.minor_count || 0);
            $('#ccr-major').text(d.major_count || 0);
        }
    });
}

function add_ccr_quick_filters(listview) {
    $('.ccr-filters').remove();
    
    const filters = [
        ['all', 'fa-list', 'All'],
        ['compliant', 'fa-check-circle', 'Compliant'],
        ['minor', 'fa-exclamation-circle', 'Minor'],
        ['major', 'fa-exclamation-triangle', 'Major'],
        ['cac_due', 'fa-file-text-o', 'CAC Due']
    ];
    
    const chips = filters.map(([id, icon, label]) => `
        <div class="filter-chip ${id === 'all' ? 'active' : ''}"
            data-filter="${id}"
            onclick="applyCCRFilter('${id}', this)">
            <i class="fa ${icon}"></i> ${label}
            <span class="count">0</span>
        </div>
    `).join('');
    
    const pageContent = listview.page.wrapper.find('.page-content');
    pageContent.prepend(`<div class="ccr-filters">${chips}</div>`);
    update_ccr_filter_counts();
}

window.applyCCRFilter = function(filter, el) {
    const listview = window._ccr_listview || cur_list;
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
    
    if (filter === 'compliant') {
        listview.filter_area.add('Corporate Compliance Register', 'overall_status', '=', 'Compliant');
    } else if (filter === 'minor') {
        listview.filter_area.add('Corporate Compliance Register', 'overall_status', '=', 'Minor Issues');
    } else if (filter === 'major') {
        listview.filter_area.add('Corporate Compliance Register', 'overall_status', 'in', ['Major Issues', 'Non-Compliant']);
    } else if (filter === 'cac_due') {
        listview.filter_area.add('Corporate Compliance Register', 'annual_return_status', '=', 'Due');
    }
    
    listview.refresh();
};

function update_ccr_filter_counts() {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.corporate_compliance_register.corporate_compliance_register_list.get_ccr_summary',
        callback(r) {
            if (!r.message) return;
            const d = r.message;
            document.querySelector('.filter-chip[data-filter="all"] .count').textContent = d.total_count || 0;
            document.querySelector('.filter-chip[data-filter="compliant"] .count').textContent = d.compliant_count || 0;
            document.querySelector('.filter-chip[data-filter="minor"] .count').textContent = d.minor_count || 0;
            document.querySelector('.filter-chip[data-filter="major"] .count').textContent = d.major_count || 0;
            document.querySelector('.filter-chip[data-filter="cac_due"] .count').textContent = d.cac_due_count || 0;
        }
    });
}

function add_ccr_export_options(listview) {
    listview.page.add_menu_item(__('📊 Export to Excel'), () => {
        let filters = {};
        try {
            const current = listview.filter_area?.get() || [];
            current.forEach(f => { if (f[0] === 'Corporate Compliance Register') filters[f[1]] = f[3]; });
        } catch (e) {}
        const url = '/api/method/ecclesia.ecclesia.doctype.corporate_compliance_register.corporate_compliance_register_list.export_ccr_excel';
        window.open(url + '?filters=' + encodeURIComponent(JSON.stringify(filters)), '_blank');
    });
}