// ecclesia/public/js/data_processing_record_list.js

frappe.listview_settings['Data Processing Record'] = {
    add_fields: [
        "name", "processing_title", "company", "department", "legal_basis",
        "status", "nitda_registered", "next_review_date", "is_sensitive_data"
    ],

    get_indicator: function(doc) {
        if (doc.status === "Active")
            return [__("Active"), "green", "status,=,Active"];
        if (doc.status === "Under Review")
            return [__("Under Review"), "orange", "status,=,Under Review"];
        if (doc.status === "Discontinued")
            return [__("Discontinued"), "grey", "status,=,Discontinued"];
        return [__("DPR"), "blue", "status,=,"];
    },

    formatters: {
        processing_title: function(v, doc) {
            return v ? `<span style="font-weight:600;color:#2563eb;">
                <i class="fa fa-database" style="color:#2563eb;margin-right:6px;"></i>${v}
            </span>` : '';
        },
        status: function(v) {
            if (!v) return '';
            const colors = {
                'Active': { bg: '#DCFCE7', text: '#166534', icon: 'fa-play-circle' },
                'Under Review': { bg: '#FEF3C7', text: '#92400E', icon: 'fa-search' },
                'Discontinued': { bg: '#F1F5F9', text: '#475569', icon: 'fa-stop-circle' }
            };
            const style = colors[v] || { bg: '#E2E8F0', text: '#1E293B', icon: 'fa-info-circle' };
            return `<span style="background:${style.bg};color:${style.text};padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600;">
                <i class="fa ${style.icon}" style="margin-right:5px;"></i>${v}
            </span>`;
        },
        legal_basis: function(v) {
            if (!v) return '';
            const colors = {
                'Consent': '#8b5cf6',
                'Contract': '#3b82f6',
                'Legal Obligation': '#dc2626',
                'Vital Interest': '#ec4899',
                'Public Task': '#f59e0b',
                'Legitimate Interest': '#10b981'
            };
            return `<span style="color:${colors[v] || '#475569'};font-weight:500;font-size:11px;">${v}</span>`;
        },
        nitda_registered: function(v) {
            return v 
                ? `<span style="color:#16a34a;font-weight:600;">✅ Registered</span>`
                : `<span style="color:#dc2626;font-weight:600;">⚠️ Not Registered</span>`;
        },
        next_review_date: function(v) {
            if (!v) return '';
            let today = frappe.datetime.get_today();
            let diff = frappe.datetime.get_diff(v, today);
            let color = diff < 0 ? '#dc2626' : (diff < 30 ? '#f59e0b' : '#475569');
            return `<span style="color:${color};">
                <i class="fa fa-calendar" style="margin-right:5px;"></i>${frappe.datetime.str_to_user(v)}
            </span>`;
        },
        is_sensitive_data: function(v) {
            return v 
                ? `<span style="color:#dc2626;font-weight:600;">🔴 Sensitive</span>`
                : `<span style="color:#64748b;">Standard</span>`;
        }
    },

    onload: function(listview) {
        window._dpr_listview = listview;
        setTimeout(() => {
            add_dpr_styles();
            add_dpr_summary_cards(listview);
            add_dpr_quick_filters(listview);
        }, 300);
        add_dpr_export_options(listview);
    },

    refresh: function(listview) {
        window._dpr_listview = listview;
        setTimeout(() => {
            update_dpr_summary_cards(listview);
            update_dpr_filter_counts();
        }, 200);
    },

    primary_action: () => frappe.new_doc("Data Processing Record"),

    button: {
        show: (doc) => doc.name,
        get_label: () => __('Actions'),
        get_description: () => __('Quick Actions'),
        action: (doc) => show_dpr_row_actions(doc)
    },

    colwidths: {
        "processing_title": 220, "company": 160, "department": 150,
        "legal_basis": 150, "status": 130, "nitda_registered": 130,
        "next_review_date": 130, "is_sensitive_data": 100
    }
};

function show_dpr_row_actions(doc) {
    const actions = [
        { label: '📄 View DPR', action: () => frappe.set_route('Form', 'Data Processing Record', doc.name) },
        { label: '📋 View Activities', action: () => frappe.set_route('Form', 'Data Processing Record', doc.name, {'tab': 'tab_data_section'}) },
        { label: '🔐 View Breaches', action: () => frappe.set_route('List', 'Data Breach Register', {'related_data_processing_record': doc.name}) },
        { label: '🔄 Request Review', action: () => request_dpr_review(doc) }
    ];
    show_actions_menu(actions);
}

function request_dpr_review(doc) {
    frappe.call({
        method: 'frappe.client.set_value',
        args: {
            doctype: 'Data Processing Record',
            name: doc.name,
            fieldname: {
                status: 'Under Review',
                last_reviewed: frappe.datetime.get_today()
            }
        },
        callback: function() {
            frappe.show_alert({message: __('DPR marked for review'), indicator: 'green'});
            window._dpr_listview?.refresh();
        }
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

function add_dpr_styles() {
    if ($('#dpr-styles').length) return;
    $('head').append(`
        <style id="dpr-styles">
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
        .dpr-summary {
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
        .summary-card.review {
            background: linear-gradient(135deg, #fef3c7, #fde68a);
            border-color: #fcd34d;
        }
        .summary-card.review .summary-card-label { color: #b45309; }
        .summary-card.review .summary-card-value { color: #92400e; }
        .summary-card.nitda {
            background: linear-gradient(135deg, #f5f3ff, #ede9fe);
            border-color: #c4b5fd;
        }
        .summary-card.nitda .summary-card-label { color: #5b21b6; }
        .summary-card.nitda .summary-card-value { color: #5b21b6; }
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
        .dpr-filters {
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

function add_dpr_summary_cards(listview) {
    $('.dpr-summary').remove();
    const pageContent = listview.page.wrapper.find('.page-content');
    if (!pageContent.length) return;
    
    pageContent.prepend(`
        <div class="dpr-summary">
            <div class="summary-card total">
                <div class="summary-card-label">📋 Total DPRs</div>
                <div class="summary-card-value" id="dpr-total">0</div>
            </div>
            <div class="summary-card active">
                <div class="summary-card-label">✅ Active</div>
                <div class="summary-card-value" id="dpr-active">0</div>
            </div>
            <div class="summary-card review">
                <div class="summary-card-label">🔍 Under Review</div>
                <div class="summary-card-value" id="dpr-review">0</div>
            </div>
            <div class="summary-card nitda">
                <div class="summary-card-label">✅ NITDA Registered</div>
                <div class="summary-card-value" id="dpr-nitda">0</div>
            </div>
        </div>
    `);
    update_dpr_summary_cards(listview);
}

function update_dpr_summary_cards(listview) {
    let filters = {};
    try {
        const current = listview.filter_area?.get() || [];
        current.forEach(f => { if (f[0] === 'Data Processing Record') filters[f[1]] = f[3]; });
    } catch (e) {}
    
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.data_processing_record.data_processing_record_list.get_dpr_summary',
        args: { filters: filters },
        callback(r) {
            if (!r.message) return;
            const d = r.message;
            $('#dpr-total').text(d.total_count || 0);
            $('#dpr-active').text(d.active_count || 0);
            $('#dpr-review').text(d.review_count || 0);
            $('#dpr-nitda').text(d.nitda_count || 0);
        }
    });
}

function add_dpr_quick_filters(listview) {
    $('.dpr-filters').remove();
    
    const filters = [
        ['all', 'fa-list', 'All'],
        ['active', 'fa-play-circle', 'Active'],
        ['review', 'fa-search', 'Review'],
        ['nitda', 'fa-check-circle', 'NITDA'],
        ['sensitive', 'fa-shield', 'Sensitive']
    ];
    
    const chips = filters.map(([id, icon, label]) => `
        <div class="filter-chip ${id === 'all' ? 'active' : ''}"
            data-filter="${id}"
            onclick="applyDPRFilter('${id}', this)">
            <i class="fa ${icon}"></i> ${label}
            <span class="count">0</span>
        </div>
    `).join('');
    
    const pageContent = listview.page.wrapper.find('.page-content');
    pageContent.prepend(`<div class="dpr-filters">${chips}</div>`);
    update_dpr_filter_counts();
}

window.applyDPRFilter = function(filter, el) {
    const listview = window._dpr_listview || cur_list;
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
        listview.filter_area.add('Data Processing Record', 'status', '=', 'Active');
    } else if (filter === 'review') {
        listview.filter_area.add('Data Processing Record', 'status', '=', 'Under Review');
    } else if (filter === 'nitda') {
        listview.filter_area.add('Data Processing Record', 'nitda_registered', '=', '1');
    } else if (filter === 'sensitive') {
        listview.filter_area.add('Data Processing Record', 'is_sensitive_data', '=', '1');
    }
    
    listview.refresh();
};

function update_dpr_filter_counts() {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.data_processing_record.data_processing_record_list.get_dpr_summary',
        callback(r) {
            if (!r.message) return;
            const d = r.message;
            document.querySelector('.filter-chip[data-filter="all"] .count').textContent = d.total_count || 0;
            document.querySelector('.filter-chip[data-filter="active"] .count').textContent = d.active_count || 0;
            document.querySelector('.filter-chip[data-filter="review"] .count').textContent = d.review_count || 0;
            document.querySelector('.filter-chip[data-filter="nitda"] .count').textContent = d.nitda_count || 0;
            document.querySelector('.filter-chip[data-filter="sensitive"] .count').textContent = d.sensitive_count || 0;
        }
    });
}

function add_dpr_export_options(listview) {
    listview.page.add_menu_item(__('📊 Export to Excel'), () => {
        let filters = {};
        try {
            const current = listview.filter_area?.get() || [];
            current.forEach(f => { if (f[0] === 'Data Processing Record') filters[f[1]] = f[3]; });
        } catch (e) {}
        const url = '/api/method/ecclesia.ecclesia.doctype.data_processing_record.data_processing_record_list.export_dpr_excel';
        window.open(url + '?filters=' + encodeURIComponent(JSON.stringify(filters)), '_blank');
    });
}