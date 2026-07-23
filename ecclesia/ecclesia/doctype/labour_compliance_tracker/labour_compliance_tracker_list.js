// ecclesia/public/js/labour_compliance_tracker_list.js

frappe.listview_settings['Labour Compliance Tracker'] = {
    add_fields: [
        "name", "tracker_title", "company", "period_label", "overall_status",
        "review_date", "minimum_wage_compliant", "working_hours_compliant"
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
        return [__("Labour Tracker"), "blue", "overall_status,=,"];
    },

    formatters: {
        tracker_title: function(v, doc) {
            return v ? `<span style="font-weight:600;color:#f97316;">
                <i class="fa fa-users" style="color:#f97316;margin-right:6px;"></i>${v}
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
        review_date: function(v) {
            if (!v) return '';
            return `<span><i class="fa fa-calendar" style="margin-right:5px;"></i>${frappe.datetime.str_to_user(v)}</span>`;
        },
        period_label: function(v) {
            if (!v) return '';
            return `<span style="font-weight:500;color:#475569;">${v}</span>`;
        },
        minimum_wage_compliant: function(v) {
            return v 
                ? `<span style="color:#16a34a;">✅</span>`
                : `<span style="color:#dc2626;">⚠️</span>`;
        }
    },

    onload: function(listview) {
        window._lct_listview = listview;
        setTimeout(() => {
            add_lct_styles();
            add_lct_summary_cards(listview);
            add_lct_quick_filters(listview);
        }, 300);
        add_lct_export_options(listview);
    },

    refresh: function(listview) {
        window._lct_listview = listview;
        setTimeout(() => {
            update_lct_summary_cards(listview);
            update_lct_filter_counts();
        }, 200);
    },

    primary_action: () => frappe.new_doc("Labour Compliance Tracker"),

    button: {
        show: (doc) => doc.name,
        get_label: () => __('Actions'),
        get_description: () => __('Quick Actions'),
        action: (doc) => show_lct_row_actions(doc)
    },

    colwidths: {
        "tracker_title": 200, "company": 160, "period_label": 120,
        "overall_status": 150, "review_date": 120,
        "minimum_wage_compliant": 100, "working_hours_compliant": 100
    }
};

function show_lct_row_actions(doc) {
    const actions = [
        { label: '📄 View Tracker', action: () => frappe.set_route('Form', 'Labour Compliance Tracker', doc.name) },
        { label: '📋 View CLL', action: () => frappe.set_route('Form', 'Compliance Liability Ledger', doc.cll_entry) },
        { label: '📊 View Inspection', action: () => frappe.set_route('Form', 'Labour Compliance Tracker', doc.name, {'tab': 'tab_inspection_section'}) },
        { label: '🔄 Generate Report', action: () => generate_lct_report(doc) }
    ];
    show_actions_menu(actions);
}

function generate_lct_report(doc) {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.labour_compliance_tracker.labour_compliance_tracker.generate_report',
        args: { docname: doc.name },
        callback: function(r) {
            if (r.message) {
                frappe.msgprint({
                    title: __('Report Generated'),
                    message: __('Report generated successfully. Download from attachments.'),
                    indicator: 'green'
                });
                window._lct_listview?.refresh();
            }
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

function add_lct_styles() {
    if ($('#lct-styles').length) return;
    $('head').append(`
        <style id="lct-styles">
        .list-row {
            transition: all .25s ease !important;
            border-left: 4px solid transparent !important;
            border-radius: 8px !important;
            margin: 2px 0 !important;
        }
        .list-row:hover {
            background: linear-gradient(90deg, #fef3c7, #fde68a) !important;
            border-left-color: #f97316 !important;
            transform: translateX(3px);
        }
        .list-headers {
            background: linear-gradient(135deg, #EA580C, #F97316) !important;
            color: #fff !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            font-size: 11px !important;
            letter-spacing: .8px !important;
            padding: 14px 16px !important;
            border-radius: 12px !important;
        }
        .lct-summary {
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
        .summary-card.compliant {
            background: linear-gradient(135deg, #ecfdf5, #d1fae5);
            border-color: #6ee7b7;
        }
        .summary-card.compliant .summary-card-label { color: #047857; }
        .summary-card.compliant .summary-card-value { color: #065f46; }
        .summary-card.issues {
            background: linear-gradient(135deg, #fef3c7, #fde68a);
            border-color: #fcd34d;
        }
        .summary-card.issues .summary-card-label { color: #b45309; }
        .summary-card.issues .summary-card-value { color: #92400e; }
        .summary-card.noncompliant {
            background: linear-gradient(135deg, #fef2f2, #fee2e2);
            border-color: #fca5a5;
        }
        .summary-card.noncompliant .summary-card-label { color: #b91c1c; }
        .summary-card.noncompliant .summary-card-value { color: #991b1b; }
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
        .lct-filters {
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
            border-color: #f97316;
            background: #fef3c7;
            transform: translateY(-2px);
        }
        .filter-chip.active {
            background: linear-gradient(135deg, #EA580C, #F97316);
            color: #fff;
            border-color: #F97316;
            box-shadow: 0 4px 14px rgba(249,115,22,.3);
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

function add_lct_summary_cards(listview) {
    $('.lct-summary').remove();
    const pageContent = listview.page.wrapper.find('.page-content');
    if (!pageContent.length) return;
    
    pageContent.prepend(`
        <div class="lct-summary">
            <div class="summary-card total">
                <div class="summary-card-label">📋 Total Trackers</div>
                <div class="summary-card-value" id="lct-total">0</div>
            </div>
            <div class="summary-card compliant">
                <div class="summary-card-label">✅ Compliant</div>
                <div class="summary-card-value" id="lct-compliant">0</div>
            </div>
            <div class="summary-card issues">
                <div class="summary-card-label">⚠️ Issues</div>
                <div class="summary-card-value" id="lct-issues">0</div>
            </div>
            <div class="summary-card noncompliant">
                <div class="summary-card-label">🚨 Non-Compliant</div>
                <div class="summary-card-value" id="lct-noncompliant">0</div>
            </div>
        </div>
    `);
    update_lct_summary_cards(listview);
}

function update_lct_summary_cards(listview) {
    let filters = {};
    try {
        const current = listview.filter_area?.get() || [];
        current.forEach(f => { if (f[0] === 'Labour Compliance Tracker') filters[f[1]] = f[3]; });
    } catch (e) {}
    
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.labour_compliance_tracker.labour_compliance_tracker_list.get_lct_summary',
        args: { filters: filters },
        callback(r) {
            if (!r.message) return;
            const d = r.message;
            $('#lct-total').text(d.total_count || 0);
            $('#lct-compliant').text(d.compliant_count || 0);
            $('#lct-issues').text(d.issues_count || 0);
            $('#lct-noncompliant').text(d.noncompliant_count || 0);
        }
    });
}

function add_lct_quick_filters(listview) {
    $('.lct-filters').remove();
    
    const filters = [
        ['all', 'fa-list', 'All'],
        ['compliant', 'fa-check-circle', 'Compliant'],
        ['issues', 'fa-exclamation-circle', 'Issues'],
        ['noncompliant', 'fa-times-circle', 'Non-Compliant'],
        ['wage', 'fa-money', 'Min Wage']
    ];
    
    const chips = filters.map(([id, icon, label]) => `
        <div class="filter-chip ${id === 'all' ? 'active' : ''}"
            data-filter="${id}"
            onclick="applyLCTFilter('${id}', this)">
            <i class="fa ${icon}"></i> ${label}
            <span class="count">0</span>
        </div>
    `).join('');
    
    const pageContent = listview.page.wrapper.find('.page-content');
    pageContent.prepend(`<div class="lct-filters">${chips}</div>`);
    update_lct_filter_counts();
}

window.applyLCTFilter = function(filter, el) {
    const listview = window._lct_listview || cur_list;
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
        listview.filter_area.add('Labour Compliance Tracker', 'overall_status', '=', 'Compliant');
    } else if (filter === 'issues') {
        listview.filter_area.add('Labour Compliance Tracker', 'overall_status', '=', 'Minor Issues');
    } else if (filter === 'noncompliant') {
        listview.filter_area.add('Labour Compliance Tracker', 'overall_status', 'in', ['Major Issues', 'Non-Compliant']);
    } else if (filter === 'wage') {
        listview.filter_area.add('Labour Compliance Tracker', 'minimum_wage_compliant', '=', '0');
    }
    
    listview.refresh();
};

function update_lct_filter_counts() {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.labour_compliance_tracker.labour_compliance_tracker_list.get_lct_summary',
        callback(r) {
            if (!r.message) return;
            const d = r.message;
            document.querySelector('.filter-chip[data-filter="all"] .count').textContent = d.total_count || 0;
            document.querySelector('.filter-chip[data-filter="compliant"] .count').textContent = d.compliant_count || 0;
            document.querySelector('.filter-chip[data-filter="issues"] .count').textContent = d.issues_count || 0;
            document.querySelector('.filter-chip[data-filter="noncompliant"] .count').textContent = d.noncompliant_count || 0;
            document.querySelector('.filter-chip[data-filter="wage"] .count').textContent = d.wage_issue_count || 0;
        }
    });
}

function add_lct_export_options(listview) {
    listview.page.add_menu_item(__('📊 Export to Excel'), () => {
        let filters = {};
        try {
            const current = listview.filter_area?.get() || [];
            current.forEach(f => { if (f[0] === 'Labour Compliance Tracker') filters[f[1]] = f[3]; });
        } catch (e) {}
        const url = '/api/method/ecclesia.ecclesia.doctype.labour_compliance_tracker.labour_compliance_tracker_list.export_lct_excel';
        window.open(url + '?filters=' + encodeURIComponent(JSON.stringify(filters)), '_blank');
    });
}