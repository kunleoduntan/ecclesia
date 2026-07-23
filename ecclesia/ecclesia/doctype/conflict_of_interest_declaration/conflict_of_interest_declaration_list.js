// ecclesia/public/js/conflict_of_interest_declaration_list.js

frappe.listview_settings['Conflict of Interest Declaration'] = {
    add_fields: [
        "name", "declaration_title", "employee", "declaration_date", "declaration_type",
        "has_conflict", "approval_status", "department", "company"
    ],

    get_indicator: function(doc) {
        if (doc.approval_status === "Approved — No Further Action")
            return [__("Approved"), "green", "approval_status,=,Approved — No Further Action"];
        if (doc.approval_status === "Approved with Conditions")
            return [__("Approved w/ Cond"), "orange", "approval_status,=,Approved with Conditions"];
        if (doc.approval_status === "Escalated to Board")
            return [__("Escalated"), "red", "approval_status,=,Escalated to Board"];
        if (doc.approval_status === "Pending")
            return [__("Pending"), "yellow", "approval_status,=,Pending"];
        if (doc.has_conflict)
            return [__("Conflict Declared"), "red", "has_conflict,=,1"];
        return [__("No Conflict"), "green", "has_conflict,=,0"];
    },

    formatters: {
        declaration_title: function(v, doc) {
            return v ? `<span style="font-weight:600;color:#f59e0b;">
                <i class="fa fa-handshake-o" style="color:#f59e0b;margin-right:6px;"></i>${v}
            </span>` : '';
        },
        approval_status: function(v) {
            if (!v) return '';
            const colors = {
                'Pending': { bg: '#FEF3C7', text: '#92400E', icon: 'fa-clock-o' },
                'Approved — No Further Action': { bg: '#DCFCE7', text: '#166534', icon: 'fa-check-circle' },
                'Approved with Conditions': { bg: '#DBEAFE', text: '#1E40AF', icon: 'fa-check-circle' },
                'Escalated to Board': { bg: '#FEE2E2', text: '#991B1B', icon: 'fa-arrow-up' }
            };
            const style = colors[v] || { bg: '#E2E8F0', text: '#1E293B', icon: 'fa-info-circle' };
            return `<span style="background:${style.bg};color:${style.text};padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600;">
                <i class="fa ${style.icon}" style="margin-right:5px;"></i>${v}
            </span>`;
        },
        has_conflict: function(v) {
            return v 
                ? `<span style="color:#dc2626;font-weight:700;">⚠️ Conflict</span>`
                : `<span style="color:#16a34a;font-weight:600;">✅ No Conflict</span>`;
        },
        declaration_type: function(v) {
            if (!v) return '';
            const colors = {
                'Annual Declaration': '#3b82f6',
                'Event-Triggered': '#f59e0b',
                'Appointment Declaration': '#10b981',
                'Onboarding': '#8b5cf6'
            };
            return `<span style="color:${colors[v] || '#475569'};font-weight:500;font-size:11px;">${v}</span>`;
        },
        declaration_date: function(v) {
            if (!v) return '';
            return `<span><i class="fa fa-calendar" style="margin-right:5px;"></i>${frappe.datetime.str_to_user(v)}</span>`;
        }
    },

    onload: function(listview) {
        window._coi_listview = listview;
        setTimeout(() => {
            add_coi_styles();
            add_coi_summary_cards(listview);
            add_coi_quick_filters(listview);
        }, 300);
        add_coi_export_options(listview);
    },

    refresh: function(listview) {
        window._coi_listview = listview;
        setTimeout(() => {
            update_coi_summary_cards(listview);
            update_coi_filter_counts();
        }, 200);
    },

    primary_action: () => frappe.new_doc("Conflict of Interest Declaration"),

    button: {
        show: (doc) => doc.name,
        get_label: () => __('Actions'),
        get_description: () => __('Quick Actions'),
        action: (doc) => show_coi_row_actions(doc)
    },

    colwidths: {
        "declaration_title": 220, "employee": 160, "declaration_date": 120,
        "declaration_type": 150, "has_conflict": 120, "approval_status": 180,
        "department": 150
    }
};

function show_coi_row_actions(doc) {
    const actions = [
        { label: '📄 View Declaration', action: () => frappe.set_route('Form', 'Conflict of Interest Declaration', doc.name) },
        { label: '✅ Approve Declaration', action: () => approve_coi(doc) },
        { label: '📋 View Employee', action: () => frappe.set_route('Form', 'Employee', doc.employee) },
        { label: '📜 View Policy', action: () => frappe.set_route('Form', 'Company Policy', doc.company_policy) }
    ];
    show_actions_menu(actions);
}

function approve_coi(doc) {
    if (doc.approval_status !== "Pending") {
        frappe.msgprint(__('This declaration has already been processed.'));
        return;
    }
    
    const dialog = new frappe.ui.Dialog({
        title: __('Approve Declaration'),
        fields: [
            {
                fieldname: 'approval_status',
                label: __('Approval Status'),
                fieldtype: 'Select',
                options: ['Approved — No Further Action', 'Approved with Conditions', 'Escalated to Board'],
                reqd: 1
            },
            {
                fieldname: 'mitigation',
                label: __('Mitigation Details'),
                fieldtype: 'Small Text',
                depends_on: 'eval:doc.approval_status == "Approved with Conditions"'
            }
        ],
        primary_action: function(values) {
            var update_fields = {
                approval_status: values.approval_status
            };
            if (values.mitigation) {
                update_fields.mitigation = values.mitigation;
            }
            frappe.call({
                method: 'frappe.client.set_value',
                args: {
                    doctype: 'Conflict of Interest Declaration',
                    name: doc.name,
                    fieldname: update_fields
                },
                callback: function() {
                    dialog.hide();
                    frappe.show_alert({message: __('Declaration approved'), indicator: 'green'});
                    window._coi_listview?.refresh();
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

function add_coi_styles() {
    if ($('#coi-styles').length) return;
    $('head').append(`
        <style id="coi-styles">
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
        .coi-summary {
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
        .summary-card.conflict {
            background: linear-gradient(135deg, #fef2f2, #fee2e2);
            border-color: #fca5a5;
        }
        .summary-card.conflict .summary-card-label { color: #b91c1c; }
        .summary-card.conflict .summary-card-value { color: #991b1b; }
        .summary-card.approved {
            background: linear-gradient(135deg, #ecfdf5, #d1fae5);
            border-color: #6ee7b7;
        }
        .summary-card.approved .summary-card-label { color: #047857; }
        .summary-card.approved .summary-card-value { color: #065f46; }
        .summary-card.pending {
            background: linear-gradient(135deg, #fef3c7, #fde68a);
            border-color: #fcd34d;
        }
        .summary-card.pending .summary-card-label { color: #b45309; }
        .summary-card.pending .summary-card-value { color: #92400e; }
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
        .coi-filters {
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

function add_coi_summary_cards(listview) {
    $('.coi-summary').remove();
    const pageContent = listview.page.wrapper.find('.page-content');
    if (!pageContent.length) return;
    
    pageContent.prepend(`
        <div class="coi-summary">
            <div class="summary-card total">
                <div class="summary-card-label">📋 Total Declarations</div>
                <div class="summary-card-value" id="coi-total">0</div>
            </div>
            <div class="summary-card conflict">
                <div class="summary-card-label">⚠️ Conflicts Declared</div>
                <div class="summary-card-value" id="coi-conflict">0</div>
            </div>
            <div class="summary-card approved">
                <div class="summary-card-label">✅ Approved</div>
                <div class="summary-card-value" id="coi-approved">0</div>
            </div>
            <div class="summary-card pending">
                <div class="summary-card-label">⏳ Pending</div>
                <div class="summary-card-value" id="coi-pending">0</div>
            </div>
        </div>
    `);
    update_coi_summary_cards(listview);
}

function update_coi_summary_cards(listview) {
    let filters = {};
    try {
        const current = listview.filter_area?.get() || [];
        current.forEach(f => { if (f[0] === 'Conflict of Interest Declaration') filters[f[1]] = f[3]; });
    } catch (e) {}
    
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.conflict_of_interest_declaration.conflict_of_interest_declaration_list.get_coi_summary',
        args: { filters: filters },
        callback(r) {
            if (!r.message) return;
            const d = r.message;
            $('#coi-total').text(d.total_count || 0);
            $('#coi-conflict').text(d.conflict_count || 0);
            $('#coi-approved').text(d.approved_count || 0);
            $('#coi-pending').text(d.pending_count || 0);
        }
    });
}

function add_coi_quick_filters(listview) {
    $('.coi-filters').remove();
    
    const filters = [
        ['all', 'fa-list', 'All'],
        ['conflict', 'fa-exclamation-triangle', 'Conflict'],
        ['approved', 'fa-check-circle', 'Approved'],
        ['pending', 'fa-clock-o', 'Pending'],
        ['annual', 'fa-calendar', 'Annual']
    ];
    
    const chips = filters.map(([id, icon, label]) => `
        <div class="filter-chip ${id === 'all' ? 'active' : ''}"
            data-filter="${id}"
            onclick="applyCOIFilter('${id}', this)">
            <i class="fa ${icon}"></i> ${label}
            <span class="count">0</span>
        </div>
    `).join('');
    
    const pageContent = listview.page.wrapper.find('.page-content');
    pageContent.prepend(`<div class="coi-filters">${chips}</div>`);
    update_coi_filter_counts();
}

window.applyCOIFilter = function(filter, el) {
    const listview = window._coi_listview || cur_list;
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
    
    if (filter === 'conflict') {
        listview.filter_area.add('Conflict of Interest Declaration', 'has_conflict', '=', '1');
    } else if (filter === 'approved') {
        listview.filter_area.add('Conflict of Interest Declaration', 'approval_status', 'in', ['Approved — No Further Action', 'Approved with Conditions']);
    } else if (filter === 'pending') {
        listview.filter_area.add('Conflict of Interest Declaration', 'approval_status', '=', 'Pending');
    } else if (filter === 'annual') {
        listview.filter_area.add('Conflict of Interest Declaration', 'declaration_type', '=', 'Annual Declaration');
    }
    
    listview.refresh();
};

function update_coi_filter_counts() {
    frappe.call({
        method: 'ecclesia.ecclesia.doctype.conflict_of_interest_declaration.conflict_of_interest_declaration_list.get_coi_summary',
        callback(r) {
            if (!r.message) return;
            const d = r.message;
            document.querySelector('.filter-chip[data-filter="all"] .count').textContent = d.total_count || 0;
            document.querySelector('.filter-chip[data-filter="conflict"] .count').textContent = d.conflict_count || 0;
            document.querySelector('.filter-chip[data-filter="approved"] .count').textContent = d.approved_count || 0;
            document.querySelector('.filter-chip[data-filter="pending"] .count').textContent = d.pending_count || 0;
            document.querySelector('.filter-chip[data-filter="annual"] .count').textContent = d.annual_count || 0;
        }
    });
}

function add_coi_export_options(listview) {
    listview.page.add_menu_item(__('📊 Export to Excel'), () => {
        let filters = {};
        try {
            const current = listview.filter_area?.get() || [];
            current.forEach(f => { if (f[0] === 'Conflict of Interest Declaration') filters[f[1]] = f[3]; });
        } catch (e) {}
        const url = '/api/method/ecclesia.ecclesia.doctype.conflict_of_interest_declaration.conflict_of_interest_declaration_list.export_coi_excel';
        window.open(url + '?filters=' + encodeURIComponent(JSON.stringify(filters)), '_blank');
    });
}