// ecclesia/public/js/suspicious_transaction_report_list.js

frappe.listview_settings['Suspicious Transaction Report'] = {
    add_fields: [
        "name", "str_title", "report_type", "party_name", "transaction_amount",
        "transaction_date", "suspicious_indicators", "status", "nfiu_submitted",
        "nfiu_submission_date", "amlco_sign_off", "report_date"
    ],

    get_indicator: function(doc) {
        if (doc.status === "Referred to Enforcement")
            return [__("Referred"), "red", "status,=,Referred to Enforcement"];
        if (doc.status === "Submitted to NFIU")
            return [__("Submitted NFIU"), "blue", "status,=,Submitted to NFIU"];
        if (doc.status === "Under Review")
            return [__("Under Review"), "orange", "status,=,Under Review"];
        if (doc.status === "Closed — No Action")
            return [__("Closed"), "green", "status,=,Closed — No Action"];
        return [__("Draft"), "grey", "status,=,Draft"];
    },

    formatters: {
        str_title: function(v, doc) {
            return v ? `<span style="font-weight:600;color:#b91c1c;">
                <i class="fa fa-flag" style="color:#dc2626;margin-right:6px;"></i>${v}
            </span>` : '';
        },
        status: function(v) {
            if (!v) return '';
            const colors = {
                'Draft': { bg: '#F1F5F9', text: '#475569', icon: 'fa-pencil' },
                'Under Review': { bg: '#FEF3C7', text: '#92400E', icon: 'fa-search' },
                'Submitted to NFIU': { bg: '#DBEAFE', text: '#1E40AF', icon: 'fa-send-o' },
                'Closed — No Action': { bg: '#DCFCE7', text: '#166534', icon: 'fa-check' },
                'Referred to Enforcement': { bg: '#FEE2E2', text: '#991B1B', icon: 'fa-gavel' }
            };
            const style = colors[v] || { bg: '#E2E8F0', text: '#1E293B', icon: 'fa-info-circle' };
            return `<span style="background:${style.bg};color:${style.text};padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600;">
                <i class="fa ${style.icon}" style="margin-right:5px;"></i>${v}
            </span>`;
        },
        transaction_amount: function(v) {
            if (!v) return '';
            let color = v > 10000000 ? '#dc2626' : (v > 5000000 ? '#f59e0b' : '#059669');
            return `<span style="color:${color};font-weight:600;">${frappe.format(v, {fieldtype: 'Currency'})}</span>`;
        },
        suspicious_indicators: function(v) {
            if (!v) return '';
            const icons = {
                'Structuring / Smurfing': 'fa-money',
                'Unusual Cash Pattern': 'fa-cash',
                'Inconsistent with Profile': 'fa-user-times',
                'Sanctioned Party': 'fa-ban',
                'PEP Transaction': 'fa-user-secret',
                'Complex Structure': 'fa-sitemap',
                'Unexplained Wealth': 'fa-question-circle',
                'Geographic Risk': 'fa-globe',
                'No Apparent Business Purpose': 'fa-briefcase'
            };
            let icon = icons[v] || 'fa-exclamation-circle';
            return `<span style="color:#92400e;font-size:11px;">
                <i class="fa ${icon}" style="margin-right:5px;"></i>${v}
            </span>`;
        },
        nfiu_submitted: function(v) {
            return v 
                ? `<span style="color:#16a34a;font-weight:600;">✅ Submitted</span>`
                : `<span style="color:#94a3b8;">⬜ Pending</span>`;
        }
    },

    onload: function(listview) {
        window._str_listview = listview;
        setTimeout(() => {
            add_str_styles();
            add_str_summary_cards(listview);
            add_str_quick_filters(listview);
        }, 300);
        add_str_export_options(listview);
    },

    refresh: function(listview) {
        window._str_listview = listview;
        setTimeout(() => {
            update_str_summary_cards(listview);
            update_str_filter_counts();
        }, 200);
    },

    primary_action: () => frappe.new_doc("Suspicious Transaction Report"),

    button: {
        show: (doc) => doc.name,
        get_label: () => __('Actions'),
        get_description: () => __('Quick Actions'),
        action: (doc) => show_str_row_actions(doc)
    },

    colwidths: {
        "str_title": 200, "report_type": 180, "party_name": 160,
        "transaction_amount": 130, "transaction_date": 120,
        "suspicious_indicators": 180, "status": 150, "nfiu_submitted": 120
    }
};

function show_str_row_actions(doc) {
    const actions = [
        { label: '📄 View Report', action: () => frappe.set_route('Form', 'Suspicious Transaction Report', doc.name) },
        { label: '📤 Submit to NFIU', action: () => submit_str_to_nfiu(doc) },
        { label: '📋 View KYC', action: () => frappe.set_route('Form', 'AML KYC Record', doc.kyc_record) },
        { label: '🔄 Update Status', action: () => update_str_status(doc) }
    ];
    show_actions_menu(actions);
}

function submit_str_to_nfiu(doc) {
    frappe.confirm(__('Submit this STR to NFIU?'), () => {
        frappe.call({
            method: 'ecclesia.ecclesia.doctype.suspicious_transaction_report.suspicious_transaction_report.submit_to_nfiu',
            args: { docname: doc.name },
            callback: function(r) {
                frappe.show_alert({message: __('STR submitted to NFIU'), indicator: 'green'});
                window._str_listview?.refresh();
            }
        });
    });
}

function update_str_status(doc) {
    const dialog = new frappe.ui.Dialog({
        title: __('Update STR Status'),
        fields: [
            {
                fieldname: 'status',
                label: __('Status'),
                fieldtype: 'Select',
                options: ['Draft', 'Under Review', 'Submitted to NFIU', 'Closed — No Action', 'Referred to Enforcement'],
                default: doc.status
            }
        ],
        primary_action: function(values) {
            frappe.call({
                method: 'frappe.client.set_value',
                args: {
                    doctype: 'Suspicious Transaction Report',
                    name: doc.name,
                    fieldname: 'status',
                    value: values.status
                },
                callback: function() {
                    dialog.hide();
                    frappe.show_alert({message: __('Status updated'), indicator: 'green'});
                    window._str_listview?.refresh();
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

function add_str_styles() {
    if ($('#str-styles').length) return;
    $('head').append(`
        <style id="str-styles">
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
        .str-summary {
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
        .summary-card.submitted {
            background: linear-gradient(135deg, #dbeafe, #bfdbfe);
            border-color: #60a5fa;
        }
        .summary-card.submitted .summary-card-label { color: #1d4ed8; }
        .summary-card.submitted .summary-card-value { color: #1e40af; }
        .summary-card.review {
            background: linear-gradient(135deg, #fef3c7, #fde68a);
            border-color: #fcd34d;
        }
        .summary-card.review .summary-card-label { color: #b45309; }
        .summary-card.review .summary-card-value { color: #92400e; }
        .summary-card.referred {
            background: linear-gradient(135deg, #fef2f2, #fee2e2);
            border-color: #fca5a5;
        }
        .summary-card.referred .summary-card-label { color: #b91c1c; }
        .summary-card.referred .summary-card-value { color: #991b1b; }
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
        .str-filters {
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

function add_str_summary_cards(listview) {
    $('.str-summary').remove();
    const pageContent = listview.page.wrapper.find('.page-content');
    if (!pageContent.length) return;
    
    pageContent.prepend(`
        <div class="str-summary">
            <div class="summary-card total">
                <div class="summary-card-label">📋 Total Reports</div>
                <div class="summary-card-value" id="str-total">0</div>
            </div>
            <div class="summary-card submitted">
                <div class="summary-card-label">📤 Submitted NFIU</div>
                <div class="summary-card-value" id="str-submitted">0</div>
            </div>
            <div class="summary-card review">
                <div class="summary-card-label">🔍 Under Review</div>
                <div class="summary-card-value" id="str-review">0</div>
            </div>
            <div class="summary-card referred">
                <div class="summary-card-label">🚨 Referred</div>
                <div class="summary-card-value" id="str-referred">0</div>
            </div>
        </div>
    `);
    update_str_summary_cards(listview);
}

function update_str_summary_cards(listview) {
    let filters = {};
    try {
        const current = listview.filter_area?.get() || [];
        current.forEach(f => { if (f[0] === 'Suspicious Transaction Report') filters[f[1]] = f[3]; });
    } catch (e) {}
    
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.suspicious_transaction_report.suspicious_transaction_report_list.get_str_summary',
        args: { filters: filters },
        callback(r) {
            if (!r.message) return;
            const d = r.message;
            $('#str-total').text(d.total_count || 0);
            $('#str-submitted').text(d.submitted_count || 0);
            $('#str-review').text(d.review_count || 0);
            $('#str-referred').text(d.referred_count || 0);
        }
    });
}

function add_str_quick_filters(listview) {
    $('.str-filters').remove();
    
    const filters = [
        ['all', 'fa-list', 'All'],
        ['submitted', 'fa-send-o', 'Submitted'],
        ['review', 'fa-search', 'Review'],
        ['referred', 'fa-gavel', 'Referred'],
        ['draft', 'fa-pencil', 'Draft'],
        ['nfiu', 'fa-check-circle', 'NFIU Done']
    ];
    
    const chips = filters.map(([id, icon, label]) => `
        <div class="filter-chip ${id === 'all' ? 'active' : ''}"
            data-filter="${id}"
            onclick="applySTRFilter('${id}', this)">
            <i class="fa ${icon}"></i> ${label}
            <span class="count">0</span>
        </div>
    `).join('');
    
    const pageContent = listview.page.wrapper.find('.page-content');
    pageContent.prepend(`<div class="str-filters">${chips}</div>`);
    update_str_filter_counts();
}

window.applySTRFilter = function(filter, el) {
    const listview = window._str_listview || cur_list;
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
    
    if (filter === 'submitted') {
        listview.filter_area.add('Suspicious Transaction Report', 'status', '=', 'Submitted to NFIU');
    } else if (filter === 'review') {
        listview.filter_area.add('Suspicious Transaction Report', 'status', '=', 'Under Review');
    } else if (filter === 'referred') {
        listview.filter_area.add('Suspicious Transaction Report', 'status', '=', 'Referred to Enforcement');
    } else if (filter === 'draft') {
        listview.filter_area.add('Suspicious Transaction Report', 'status', '=', 'Draft');
    } else if (filter === 'nfiu') {
        listview.filter_area.add('Suspicious Transaction Report', 'nfiu_submitted', '=', '1');
    }
    
    listview.refresh();
};

function update_str_filter_counts() {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.suspicious_transaction_report.suspicious_transaction_report_list.get_str_summary',
        callback(r) {
            if (!r.message) return;
            const d = r.message;
            document.querySelector('.filter-chip[data-filter="all"] .count').textContent = d.total_count || 0;
            document.querySelector('.filter-chip[data-filter="submitted"] .count').textContent = d.submitted_count || 0;
            document.querySelector('.filter-chip[data-filter="review"] .count').textContent = d.review_count || 0;
            document.querySelector('.filter-chip[data-filter="referred"] .count').textContent = d.referred_count || 0;
            document.querySelector('.filter-chip[data-filter="draft"] .count').textContent = d.draft_count || 0;
            document.querySelector('.filter-chip[data-filter="nfiu"] .count').textContent = d.nfiu_submitted_count || 0;
        }
    });
}

function add_str_export_options(listview) {
    listview.page.add_menu_item(__('📊 Export to Excel'), () => {
        let filters = {};
        try {
            const current = listview.filter_area?.get() || [];
            current.forEach(f => { if (f[0] === 'Suspicious Transaction Report') filters[f[1]] = f[3]; });
        } catch (e) {}
        const url = '/api/method/ecclesia.ecclesia.doctype.suspicious_transaction_report.suspicious_transaction_report_list.export_str_excel';
        window.open(url + '?filters=' + encodeURIComponent(JSON.stringify(filters)), '_blank');
    });
}